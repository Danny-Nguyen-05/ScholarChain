package edu.uic.cs441.scholarchain.entityresolution

import java.nio.file.{Files, LinkOption, Path}
import scala.util.Try

/** Local IO safety only. Physical filesystem paths are not scholarly identity evidence. */
object PathIsolation {
  private def physical(path: Path): Path = {
    val absolute = path.toAbsolutePath.normalize
    var ancestor = absolute
    while (!Files.exists(ancestor, LinkOption.NOFOLLOW_LINKS)) {
      ancestor = Option(ancestor.getParent).getOrElse(
        throw new IllegalArgumentException("path has no existing ancestor")
      )
    }
    ancestor.toRealPath().resolve(ancestor.relativize(absolute)).normalize
  }
  def disjoint(first: Path, second: Path): Either[String, Unit] = Try {
    val a = physical(first); val b = physical(second)
    require(
      !a.startsWith(b) && !b.startsWith(a),
      "input, output and cache paths must be disjoint; equal/nested paths are forbidden"
    )
    ()
  }.toEither.left.map(_.getMessage)
  def validate(input: Path, output: Path, cache: Option[Path]): Either[String, Unit] = for {
    _ <- disjoint(input, output)
    _ <- cache.map(c => disjoint(input, c)).getOrElse(Right(()))
    _ <- cache.map(c => disjoint(output, c)).getOrElse(Right(()))
  } yield ()
}

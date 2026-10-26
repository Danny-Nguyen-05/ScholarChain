package edu.uic.cs441.scholarchain.independent

import java.nio.file.Path
import scala.collection.mutable

/** Conservative source heuristic, not a Scala type checker or an IAM permission proof. */
object RuntimeGraphFence {
  final case class Finding(path: Path, capability: String)
  final case class Result(inspected: Set[Path], findings: Vector[Finding])
  private val identifiers = "[A-Za-z_$][A-Za-z0-9_$]*".r
  private val declarations = "\\b(?:class|object|trait|type)\\s+([A-Za-z_$][A-Za-z0-9_$]*)".r
  private val forbidden = Set(
    "GraphLoader",
    "NeptuneGraphLoader",
    "InMemoryGraphLoader",
    "NeptunedataClient",
    "StartLoaderJobRequest",
    "StorageLoadMain",
    "submitBulkLoad",
    "startLoaderJob",
    "executeOpenCypherQuery",
    "executeGremlinQuery",
    "executeGremlinProfileQuery"
  )

  /** Mask inert literals/comments, retaining executable interpolation expressions. This remains a
    * conservative source heuristic rather than a Scala parser.
    */
  def code(text: String): String = {
    val out = new StringBuilder
    var i = 0
    def blank(): Unit = {
      out.append(if (text(i) == '\n') '\n' else ' ')
      i += 1
    }
    def blanks(count: Int): Unit = (0 until count).foreach(_ => blank())
    def identifier(c: Char): Boolean = c.isLetterOrDigit || c == '_' || c == '$'
    def characterEnd(start: Int): Option[Int] = {
      var end = start + 1
      if (end >= text.length || text(end) == '\n' || text(end) == '\r') None
      else {
        if (text(end) == '\\') {
          end += 1
          if (end < text.length && text(end) == 'u') {
            while (end < text.length && text(end) == 'u') end += 1
            val digits = text.slice(end, end + 4)
            if (digits.length != 4 || !digits.forall(c => Character.digit(c, 16) >= 0))
              return None
            end += 4
          } else if (end < text.length) end += 1
        } else end += Character.charCount(text.codePointAt(end))
        Option.when(end < text.length && text(end) == '\'')(end + 1)
      }
    }
    def stringLiteral(interpolated: Boolean): Unit = {
      val width = if (text.startsWith("\"\"\"", i)) 3 else 1
      blanks(width)
      var ended = false
      while (i < text.length && !ended) {
        if (text.startsWith("\"" * width, i)) {
          blanks(width)
          ended = true
        } else if (interpolated && text.startsWith("$$", i)) blanks(2)
        else if (interpolated && text.startsWith("${", i)) {
          blank()
          out.append('{')
          i += 1
          scan(stopAtBrace = true)
        } else if (
          interpolated && text(i) == '$' && i + 1 < text.length &&
          (text(i + 1).isLetter || text(i + 1) == '_')
        ) {
          blank()
          while (i < text.length && identifier(text(i))) { out.append(text(i)); i += 1 }
        } else if (width == 1 && text(i) == '\\') {
          blank()
          if (i < text.length) blank()
        } else blank()
      }
    }
    def scan(stopAtBrace: Boolean): Unit = {
      var depth = 0
      var ended = false
      while (i < text.length && !ended) {
        if (text.startsWith("//", i)) {
          while (i < text.length && text(i) != '\n') blank()
        } else if (text.startsWith("/*", i)) {
          var comments = 1
          blanks(2)
          while (i < text.length && comments > 0) {
            if (text.startsWith("/*", i)) { comments += 1; blanks(2) }
            else if (text.startsWith("*/", i)) { comments -= 1; blanks(2) }
            else blank()
          }
        } else if (text(i) == '\'' && characterEnd(i).nonEmpty) {
          val end = characterEnd(i).get
          while (i < end) blank()
        } else if (text(i) == '\"') {
          val interpolated = i > 0 && (identifier(text(i - 1)) || text(i - 1) == '`')
          stringLiteral(interpolated)
        } else if (text(i) == '}' && stopAtBrace && depth == 0) {
          out.append('}')
          i += 1
          ended = true
        } else {
          if (text(i) == '{') depth += 1
          else if (text(i) == '}') depth -= 1
          out.append(text(i))
          i += 1
        }
      }
    }
    scan(stopAtBrace = false)
    out.toString
  }

  def scan(sources: Map[Path, String], runtimeRoots: Set[Path]): Result = {
    val masked = sources.view.mapValues(code).toMap
    // Port declarations are not composition; the trusted read adapter necessarily owns its SDK
    // client privately. Follow other referenced storage helpers, not their implementation internals.
    val trusted = Set("StoragePorts.scala", "NeptuneGraphReader.scala", "Phase7Configs.scala")
    val storage = masked.filter((path, _) =>
      path.toString.replace('\\', '/').contains("modules/storage/src/main/") &&
        !trusted(path.getFileName.toString)
    )
    val exports = storage.map((path, source) =>
      path -> declarations.findAllMatchIn(source).map(_.group(1)).toSet
    )
    val pending = mutable.Queue.from(runtimeRoots)
    val inspected = mutable.Set.empty[Path]
    val findings = Vector.newBuilder[Finding]
    while (pending.nonEmpty) {
      val path = pending.dequeue()
      if (inspected.add(path)) {
        val source = masked(path)
        val tokens = identifiers.findAllIn(source).toSet
        tokens.intersect(forbidden).toVector.sorted.foreach(name => findings += Finding(path, name))
        if (source.contains("services.neptunedata"))
          findings += Finding(path, "raw-neptune-sdk-package")
        exports.foreach { (candidate, names) =>
          if (!inspected(candidate) && tokens.intersect(names).nonEmpty) pending.enqueue(candidate)
        }
      }
    }
    Result(inspected.toSet, findings.result())
  }
}

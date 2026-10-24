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

  /** Mask comments and literals before scanning; nested block comments are supported. */
  def code(text: String): String = {
    val out = new StringBuilder
    var i = 0
    while (i < text.length) {
      if (text.startsWith("//", i)) {
        while (i < text.length && text(i) != '\n') { out.append(' '); i += 1 }
      } else if (text.startsWith("/*", i)) {
        var depth = 1
        i += 2
        while (i < text.length && depth > 0) {
          if (text.startsWith("/*", i)) { depth += 1; i += 2 }
          else if (text.startsWith("*/", i)) { depth -= 1; i += 2 }
          else { out.append(if (text(i) == '\n') '\n' else ' '); i += 1 }
        }
      } else if (text.startsWith("\"\"\"", i)) {
        i += 3
        while (i < text.length && !text.startsWith("\"\"\"", i)) { out.append(' '); i += 1 }
        i = math.min(i + 3, text.length)
      } else if (text(i) == '"') {
        i += 1
        var ended = false
        while (i < text.length && !ended) {
          if (text(i) == '\\') i = math.min(i + 2, text.length)
          else if (text(i) == '"') { ended = true; i += 1 }
          else { out.append(' '); i += 1 }
        }
      } else { out.append(text(i)); i += 1 }
    }
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

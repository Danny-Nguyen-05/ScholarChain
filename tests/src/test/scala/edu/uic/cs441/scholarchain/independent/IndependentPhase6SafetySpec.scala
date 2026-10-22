package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.{Phase6Main, Phase6EventLog}
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Textual guard, not a Scala parser or type checker. The few non-Spark receivers below are audited
  * exact expressions; a new receiver with the same method name is rejected by default.
  */
private[independent] object IndependentSparkSourceFence {
  val driverMethods: Vector[String] = Vector(
    "collectAsList",
    "collect",
    "toLocalIterator",
    "takeAsList",
    "take",
    "head",
    "first",
    "count",
    "isEmpty",
    "reduce",
    "show"
  )
  private val identifierTail = "[\\p{L}\\p{N}_$]"
  private val driver = ("\\.\\s*(" + driverMethods.mkString("|") + ")(?!" + identifierTail + ")").r
  private val graph =
    "\\.rdd\\b|\\bRDD\\b|\\bGraphX\\b|\\bGraphFrame[s]?\\b|org\\.apache\\.spark\\.graphx|spark\\.implicits|\\bEncoders\\b|\\.as\\s*\\[".r

  /** Preserve offsets/newlines while masking comments and quoted payloads. Handle comments inside
    * strings, escaped quotes, triple quotes and nested block comments before looking for methods.
    */
  private def codeOnly(text: String): String = {
    val out = text.toCharArray
    def blank(from: Int, end: Int): Unit = (from until end).foreach { index =>
      if (out(index) != '\n' && out(index) != '\r') out(index) = ' '
    }
    var index = 0
    while (index < text.length) {
      val start = index
      if (text.startsWith("//", index)) {
        while (index < text.length && text(index) != '\n') index += 1
        blank(start, index)
      } else if (text.startsWith("/*", index)) {
        var depth = 1
        index += 2
        while (index < text.length && depth > 0) {
          if (text.startsWith("/*", index)) { depth += 1; index += 2 }
          else if (text.startsWith("*/", index)) { depth -= 1; index += 2 }
          else index += 1
        }
        blank(start, index)
      } else if (text.startsWith("\"\"\"", index)) {
        index += 3
        while (index < text.length && !text.startsWith("\"\"\"", index)) index += 1
        index = math.min(text.length, index + 3)
        blank(start, index)
      } else if (text(index) == '"') {
        index += 1
        var complete = false
        while (index < text.length && !complete) {
          if (text(index) == '\\') index = math.min(text.length, index + 2)
          else if (text(index) == '"') { index += 1; complete = true }
          else index += 1
        }
        blank(start, index)
      } else index += 1
    }
    new String(out)
  }

  def violations(text: String, fileName: String = "Synthetic.scala"): Vector[String] = {
    val code = codeOnly(text)
    val safe = Vector.newBuilder[(Int, Int)]
    def exempt(pattern: String): Unit =
      pattern.r.findAllMatchIn(text).foreach(m => safe += ((m.start, m.end)))
    // This named helper is the sole production driver-action entry point.
    exempt("\\bBoundedActions\\s*\\.\\s*count(?!" + identifierTail + ")")
    fileName match {
      case "Phase6CMain.scala" | "Phase6Main.scala" =>
        // Both get calls return Option[String], never DataFrame/Dataset.
        exempt(
          "\\bsys\\s*\\.\\s*props\\s*\\.\\s*get\\s*\\(\\s*\"spark\\.master\"\\s*\\)\\s*\\.\\s*isEmpty(?!" + identifierTail + ")"
        )
        exempt(
          "\\bsys\\s*\\.\\s*env\\s*\\.\\s*get\\s*\\(\\s*\"SPARK_MASTER\"\\s*\\)\\s*\\.\\s*isEmpty(?!" + identifierTail + ")"
        )
      case "Phase6CReaders.scala" =>
        if ("\\bpaths\\s*:\\s*Vector\\s*\\[Path\\]".r.findFirstIn(code).nonEmpty)
          exempt("\\bpaths\\s*\\.\\s*isEmpty(?!" + identifierTail + ")")
        if (
          "\\brejectSink\\s*:\\s*Option\\s*\\[ArrayBuffer\\[DataFrame\\]\\]".r
            .findFirstIn(code)
            .nonEmpty
        )
          exempt("\\brejectSink\\s*\\.\\s*isEmpty(?!" + identifierTail + ")")
      case "Phase6DEJobs.scala" =>
        // SparkAnalyticsConfig.windows is a bounded Vector[SparkWindow].
        if ("\\bconfig\\s*:\\s*SparkAnalyticsConfig\\b".r.findFirstIn(code).nonEmpty)
          exempt("\\bconfig\\s*\\.\\s*windows\\s*\\.\\s*count(?!" + identifierTail + ")")
      case "Phase6Report.scala" =>
        // This local Seq contains SQL aggregate Column expressions, not graph rows.
        if ("\\bval\\s+expressions\\s*=\\s*Seq\\s*\\(\\s*count\\s*\\(".r.findFirstIn(code).nonEmpty)
          exempt("\\bexpressions\\s*\\.\\s*head(?!" + identifierTail + ")")
      case _ => ()
    }
    val safeSpans = safe.result()
    val graphErrors = graph
      .findAllMatchIn(code)
      .map(m => s"forbidden graph API ${m.matched} at ${m.start}")
      .toVector
    val driverErrors =
      if (fileName == "BoundedActions.scala") Vector.empty
      else
        driver
          .findAllMatchIn(code)
          .filterNot(m =>
            safeSpans.exists { case (from, until) => m.start >= from && m.end <= until }
          )
          .map(m => s"forbidden driver action ${m.group(1)} at ${m.start}")
          .toVector
    graphErrors ++ driverErrors
  }
}

/** No Spark session or provider is needed to verify the production API fence and output gate. */
class IndependentPhase6SafetySpec extends AnyFunSuite {
  test(
    "production Spark sources keep forbidden driver actions and graph APIs outside BoundedActions"
  ) {
    val sourceRoot = IndependentTestSupport.repoRoot.resolve("modules/spark/src/main")
    val walk = Files.walk(sourceRoot)
    val files =
      try walk.iterator().asScala.filter(p => p.toString.endsWith(".scala")).toVector
      finally walk.close()
    assert(files.nonEmpty)
    files.foreach { path =>
      val errors = IndependentSparkSourceFence.violations(
        Files.readString(path, UTF_8),
        path.getFileName.toString
      )
      assert(errors.isEmpty, s"forbidden Spark API/action in $path: ${errors.mkString(", ")}")
    }
  }

  test(
    "source fence catches every driver method with or without parentheses and respects identifier boundaries"
  ) {
    IndependentSparkSourceFence.driverMethods.foreach { method =>
      Vector(
        s"frame.$method",
        s"frame.$method()",
        s"frame . $method ( )",
        s"frame\n.$method",
        s"frame.$method _"
      ).foreach { source =>
        assert(
          IndependentSparkSourceFence
            .violations(source)
            .exists(_.contains(s"driver action $method at")),
          source
        )
      }
      Vector(s"frame.${method}Suffix", s"frame.${method}_metadata", s"frame.${method}$$suffix")
        .foreach { source =>
          assert(IndependentSparkSourceFence.violations(source).isEmpty, source)
        }
    }
    Vector(
      "frame.collect_set",
      "frame.headOption",
      "frame.firstName",
      "frame.countDistinct",
      "frame.reduceByKey"
    ).foreach { source =>
      assert(IndependentSparkSourceFence.violations(source).isEmpty, source)
    }
  }

  test(
    "source fence masks comments and string payloads without hiding adjacent executable actions"
  ) {
    val payload = IndependentSparkSourceFence.driverMethods.map(m => s"frame.$m").mkString("; ")
    val ordinary = "val message = \"" + payload + " // /* text */\""
    val triple = "val message = \"\"\"" + payload + " // /* text */\"\"\""
    Vector("// " + payload, "/* " + payload + " /* nested */ */", ordinary, triple).foreach {
      source =>
        assert(IndependentSparkSourceFence.violations(source).isEmpty, source)
    }
    assert(
      IndependentSparkSourceFence
        .violations(ordinary + "; frame.collect")
        .exists(_.contains("driver action collect at"))
    )
    assert(
      IndependentSparkSourceFence
        .violations("/* nested /* frame.count */ comment */ frame.isEmpty")
        .exists(_.contains("driver action isEmpty at"))
    )
    assert(
      IndependentSparkSourceFence
        .violations("val escaped = \"a \\\" quote\"; frame.reduce")
        .exists(_.contains("driver action reduce at"))
    )
  }

  test(
    "source fence permits only audited metadata receiver expressions and explicit BoundedActions calls"
  ) {
    val examples = Vector(
      "Phase6Main.scala" -> "sys.props.get(\"spark.master\").isEmpty; sys.env.get(\"SPARK_MASTER\").isEmpty",
      "Phase6CReaders.scala" -> "def read(paths: Vector[Path], rejectSink: Option[ArrayBuffer[DataFrame]]) = { paths.isEmpty; rejectSink.isEmpty }",
      "Phase6DEJobs.scala" -> "def run(config: SparkAnalyticsConfig) = config.windows.count(w => true)",
      "Phase6Report.scala" -> "val expressions = Seq(count(\"*\")); expressions.head",
      "Synthetic.scala" -> "BoundedActions.count(frame)"
    )
    examples.foreach { case (file, source) =>
      assert(IndependentSparkSourceFence.violations(source, file).isEmpty, s"$file: $source")
      Vector("count", "isEmpty", "head").foreach { method =>
        assert(
          IndependentSparkSourceFence
            .violations(source + s"; frame.$method", file)
            .exists(_.contains(s"driver action $method at"))
        )
      }
    }
    Vector(
      "paths.isEmpty",
      "rejectSink.isEmpty",
      "config.windows.count",
      "expressions.head",
      "otherBoundedActions.count(frame)"
    ).foreach { source =>
      assert(IndependentSparkSourceFence.violations(source).nonEmpty, source)
    }
  }

  test(
    "output gate refuses partial mismatched and tampered runs and reuses only the identical manifest"
  ) {
    val root = Files.createTempDirectory("independent-6fg-gate-")
    try {
      val metadata = ujson.Obj(
        "runId" -> "run:55555555-5555-4555-8555-555555555555",
        "codeVersion" -> "a" * 64,
        "hadoopManifestHash" -> "b" * 64,
        "entityResolutionManifestHash" -> "c" * 64,
        "logicalConfigFingerprint" -> "d" * 64
      )
      val manifest = "{\"syntheticGateFixture\":true}\n"
      Files.writeString(root.resolve("run-manifest.json"), manifest, UTF_8)
      val sidecar = metadata.render() + "\n"
      Files.writeString(root.resolve("run-metadata.json"), sidecar, UTF_8)
      assert(
        intercept[IllegalArgumentException](Phase6Main.requireReusable(root, metadata)).getMessage
          .contains("incomplete")
      )
      val completion = StableIds.sha256Hex(manifest + "\n" + sidecar) + "\n"
      Files.writeString(root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"), completion, UTF_8)
      Phase6Main.requireReusable(root, metadata)
      val different = ujson.read(sidecar).obj
      different("codeVersion") = ujson.Str("e" * 64)
      assert(
        intercept[IllegalArgumentException](
          Phase6Main.requireReusable(root, ujson.Obj.from(different))
        ).getMessage.contains("different run")
      )
      Files.writeString(root.resolve("run-manifest.json"), manifest + " ", UTF_8)
      assert(
        intercept[IllegalArgumentException](Phase6Main.requireReusable(root, metadata)).getMessage
          .contains("hash mismatch")
      )
    } finally {
      val walk = Files.walk(root)
      try walk.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists)
      finally walk.close()
    }
  }

  test("unknown Spark config schema is refused before any input or output work") {
    val resource = getClass.getResourceAsStream("/scholarchain.spark-analytics-config.v1.json")
    val source =
      try new String(resource.readAllBytes(), UTF_8)
      finally resource.close()
    val json = ujson.read(source)
    json("configSchemaVersion") = ujson.Str("scholarchain.spark-analytics-config.v999")
    assert(SparkAnalyticsConfigLoader.loadText(json.render()).isLeft)
    val root = Files.createTempDirectory("independent-6fg-bad-schema-")
    try {
      val file = root.resolve("bad.json")
      Files.writeString(file, json.render(), UTF_8)
      assert(Phase6Main.run(file).isLeft)
      val listing = Files.list(root)
      try assert(listing.count() == 1L)
      finally listing.close()
    } finally {
      Files.deleteIfExists(root.resolve("bad.json")); Files.deleteIfExists(root)
    }
  }

  test(
    "streaming event-log summary reports exact stage tasks partitions shuffle records and failures"
  ) {
    val root = Files.createTempDirectory("independent-6fg-events-")
    try {
      def task(
          finish: Int,
          failed: Boolean,
          runtime: Int,
          remote: Int,
          local: Int,
          records: Int,
          written: Int,
          writeRecords: Int
      ): ujson.Value = ujson.Obj(
        "Event" -> "SparkListenerTaskEnd",
        "Stage ID" -> 4,
        "Stage Attempt ID" -> 0,
        "Task Info" -> ujson.Obj("Launch Time" -> 100, "Finish Time" -> finish),
        "Task End Reason" -> ujson.Obj("Reason" -> (if (failed) "ExceptionFailure" else "Success")),
        "Task Metrics" -> ujson.Obj(
          "Executor Run Time" -> runtime,
          "Shuffle Read Metrics" -> ujson.Obj(
            "Remote Bytes Read" -> remote,
            "Local Bytes Read" -> local,
            "Total Records Read" -> records
          ),
          "Shuffle Write Metrics" -> ujson.Obj(
            "Shuffle Bytes Written" -> written,
            "Shuffle Records Written" -> writeRecords
          )
        )
      )
      val events = Vector(
        task(150, false, 20, 10, 5, 4, 7, 8),
        task(130, true, 15, 2, 3, 6, 9, 10),
        ujson.Obj(
          "Event" -> "SparkListenerStageCompleted",
          "Stage Info" -> ujson.Obj(
            "Stage ID" -> 4,
            "Stage Attempt ID" -> 0,
            "Number of Tasks" -> 3
          )
        )
      )
      Files.writeString(
        root.resolve("synthetic-events"),
        events.map(_.render()).mkString("", "\n", "\n"),
        UTF_8
      )
      val stages = Phase6EventLog.summarize(root)("stages").arr
      assert(stages.size == 1)
      val row = stages.head
      Map(
        "stageId" -> 4L,
        "attemptId" -> 0L,
        "tasks" -> 2L,
        "failedTasks" -> 1L,
        "partitionCount" -> 3L,
        "durationMs" -> 80L,
        "executorRunTimeMs" -> 35L,
        "shuffleReadBytes" -> 20L,
        "shuffleReadRecords" -> 10L,
        "shuffleWriteBytes" -> 16L,
        "shuffleWriteRecords" -> 18L
      ).foreach { case (key, expected) =>
        assert(row(key).num == expected.toDouble, key)
      }
    } finally { Files.deleteIfExists(root.resolve("synthetic-events")); Files.deleteIfExists(root) }
  }
}

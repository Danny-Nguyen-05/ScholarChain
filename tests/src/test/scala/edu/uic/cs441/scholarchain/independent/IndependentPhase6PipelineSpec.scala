package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.Phase5Main
import edu.uic.cs441.scholarchain.hadoop.HadoopPrepPipeline
import edu.uic.cs441.scholarchain.spark.{Phase6CReaders, Phase6Main}
import org.apache.spark.sql.SparkSession
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Real public CLI/pipeline interfaces, with committed synthetic inputs and disabled adjudication.
  */
class IndependentPhase6PipelineSpec extends AnyFunSuite {
  test("committed tiny fixture completes unchanged Hadoop then offline ER then all Spark jobs") {
    val root = Files.createTempDirectory("scholarchain-independent-full6-").toRealPath()
    try {
      val repo = IndependentTestSupport.repoRoot
      val xml = repo.resolve("tests/src/test/resources/phase6/tiny-pipeline.xml")
      val empty = repo.resolve("tests/src/test/resources/phase6/empty.jsonl")
      val request = IndependentTestSupport.pipelineRequest(
        root.resolve("hadoop"),
        xml,
        empty,
        empty,
        empty,
        team = 16,
        block = 100,
        pairs = 2000,
        runId = IndependentTestSupport.freshRunId()
      )
      val prepared = HadoopPrepPipeline.execute(request)
      assert(prepared.isRight, prepared.toString)
      val hadoop = prepared.toOption.get.directory
      val er = root.resolve("er")
      val resolved = Phase5Main.run(
        Array(
          "resolve",
          "--input",
          hadoop.toString,
          "--policy",
          repo
            .resolve("modules/entity-resolution/src/main/resources/phase5-policy.v1.json")
            .toString,
          "--config",
          repo
            .resolve("modules/entity-resolution/src/main/resources/phase5-config.v1.json")
            .toString,
          "--llm-mode",
          "disabled",
          "--output",
          er.toString
        )
      )
      assert(resolved.isRight, resolved.toString)
      assert(resolved.toOption.get.contains("live calls=0"))
      val resource = getClass.getResourceAsStream("/scholarchain.spark-analytics-config.v1.json")
      val loaded =
        try
          SparkAnalyticsConfigLoader
            .loadText(new String(resource.readAllBytes(), UTF_8))
            .toOption
            .get
        finally resource.close()
      val config = loaded.copy(
        hadoopRunRoot = hadoop.toString,
        entityResolutionRunRoot = er.toString,
        outputRoot = root.resolve("spark").toString,
        checkpointDirectory = root.resolve("checkpoints").toString,
        windows = IndependentPhase6G1.windows,
        communityMaxIterations = 3,
        sampledPathPairCount = 2,
        benchmarkPairs =
          Vector(BenchmarkPair("Independent Alpha", "Independent Gamma", "dblp-name"))
      )
      val configFile = root.resolve("spark-config.json")
      Files.writeString(configFile, CoreJson.compact(config), UTF_8)
      val completed = Phase6Main.run(configFile)
      assert(completed.isRight, completed.toString)
      val walk = Files.list(root.resolve("spark"))
      val output =
        try walk.iterator().asScala.find(_.getFileName.toString.startsWith("run:")).get
        finally walk.close()
      val manifestText = Files.readString(output.resolve("run-manifest.json"), UTF_8)
      val manifest = CoreJson.parse[RunManifest](manifestText).toOption.get
      assert(DomainValidation.check(manifest).isRight)
      val metadataText = Files.readString(output.resolve("run-metadata.json"), UTF_8)
      val metadata = ujson.read(metadataText)
      assert(metadata("tables").arr.size == 28)
      val counts =
        metadata("tables").arr.map(row => row("dataset").str -> row("rowCount").str.toLong).toMap
      assert(counts("nodes/type=researcher") == 4L)
      assert(counts("edges/type=coauthored_with") == 4L)
      assert(counts("metrics/type=researcher_collaboration") == 9L)
      assert(
        Files.readString(output.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"), UTF_8) == StableIds
          .sha256Hex(manifestText + "\n" + metadataText) + "\n"
      )
      assert(Files.isRegularFile(output.resolve("event-log-summary.json")))
      val stages =
        ujson.read(Files.readString(output.resolve("event-log-summary.json"), UTF_8))("stages").arr
      assert(stages.nonEmpty && stages.map(_("tasks").num).sum > 0.0)
      assert(Files.isRegularFile(output.resolve("counters.json")))
      val plans = Files.list(output.resolve("plans"))
      try assert(plans.findAny().isPresent)
      finally plans.close()
      Vector("neptune", "dynamodb", "s3vectors", "s3").foreach(target =>
        assert(Files.isRegularFile(output.resolve(s"load-manifests/$target.json")))
      )
      val reused = Phase6Main.run(configFile)
      assert(reused.isRight && reused.toOption.get.contains("Reused completed"), reused.toString)

      // A prepared completion with an unknown schema must be rejected before graph publication.
      val markerPath = hadoop.resolve("_SCHOLARCHAIN_COMPLETE")
      val originalMarker = Files.readString(markerPath, UTF_8)
      val invalidMarker = ujson.read(originalMarker)
      invalidMarker("hadoopPrepSchema") = ujson.Str("scholarchain.hadoop-prep.v999")
      Files.writeString(markerPath, invalidMarker.render(), UTF_8)
      val badSchema = Phase6Main.run(configFile)
      assert(
        badSchema.isLeft && badSchema.left.toOption.get
          .contains("unsupported Hadoop completion schema"),
        badSchema.toString
      )
      Files.writeString(markerPath, originalMarker, UTF_8)

      // A marker-free prepared run must be refused before any jobs publish new graph data.
      Files.delete(hadoop.resolve("_SCHOLARCHAIN_COMPLETE"))
      val refused = Phase6Main.run(configFile)
      assert(refused.isLeft, refused.toString)
      assert(refused.left.toOption.get.toLowerCase.contains("complet"), refused.toString)
    } finally {
      SparkSession.getActiveSession.foreach(_.stop())
      val walk = Files.walk(root)
      try walk.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists)
      finally walk.close()
    }
  }
}

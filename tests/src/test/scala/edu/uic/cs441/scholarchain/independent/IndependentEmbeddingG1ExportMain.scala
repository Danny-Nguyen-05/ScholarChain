package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.*
import org.apache.spark.sql.{Row, SparkSession}
import org.apache.spark.sql.types.StructType
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}

/** Reproducible test-owned G1 producer harness. Runs actual Phase 6 jobs/export on independently
  * transcribed G1 inputs; it does not claim Hadoop/ER execution or acquired real-world identities.
  * Usage: independentTests / Test / runMain ...IndependentEmbeddingG1ExportMain <new-output-root>
  */
object IndependentEmbeddingG1ExportMain {
  def main(args: Array[String]): Unit = {
    require(args.length == 1, "one output path required")
    val output = Path.of(args(0)).toAbsolutePath.normalize()
    require(!Files.exists(output), "output must be new; refusing overwrite")
    val resource = getClass.getResourceAsStream("/scholarchain.spark-analytics-config.v1.json")
    val loaded =
      try
        SparkAnalyticsConfigLoader.loadText(new String(resource.readAllBytes(), UTF_8)).toOption.get
      finally resource.close()
    val config = loaded.copy(
      windows = IndependentPhase6G1.windows,
      identityPolicyVersion = IndependentPhase6G1.identityPolicy,
      graphPolicyVersion = IndependentPhase6G1.graphPolicy,
      representativePolicyVersion = IndependentPhase6G1.representativePolicy,
      communityMaxIterations = 3,
      sampledPathPairCount = 2,
      pathSampleSourceCount = 32,
      benchmarkPairs =
        Vector(BenchmarkPair("A", "G", "dblp-name"), BenchmarkPair("A", "H", "dblp-name")),
      shufflePartitions = 4,
      checkpointDirectory =
        output.getParent.resolve(output.getFileName.toString + "-checkpoints").toString,
      outputRoot = output.getParent.toString
    )
    val run = IndependentPhase6G1.sparkRunId
    val lineage = SparkLineage(
      IndependentPhase6G1.hadoopRunId,
      IndependentPhase6G1.snapshot,
      IndependentPhase6G1.erRunId,
      IndependentPhase6G1.erPolicy,
      IndependentPhase6G1.erPolicyHash,
      Vector.empty,
      Vector.empty
    )
    val spark = SparkSession
      .builder()
      .master("local[2]")
      .appName("Independent computed G1 Phase8 export")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.ui.retainedExecutions", "4")
      .config("spark.ui.retainedJobs", "10")
      .config("spark.ui.retainedStages", "10")
      .config("spark.ui.retainedTasks", "100")
      .config("spark.sql.maxPlanStringLength", "65536")
      .config("spark.sql.shuffle.partitions", "4")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.jsonGenerator.ignoreNullFields", "false")
      .config("spark.sql.warehouse.dir", output.getParent.resolve("g1-warehouse").toString)
      .getOrCreate()
    spark.sparkContext.setCheckpointDir(config.checkpointDirectory)
    try {
      val canonical =
        Phase6CJobs.build(spark, config, IndependentPhase6FGFixtures.input(spark), lineage, run)
      val edges = canonical.edges.toJSON
        .collect()
        .toVector
        .map(CoreJson.parse[SparkCoauthorEdge](_).toOption.get)
      val actual = edges
        .map(e =>
          (
            e.context.windowId.get,
            Set(e.researcherA, e.researcherB),
            e.jointPublicationCount,
            e.firstCollaborationYear.get,
            e.lastCollaborationYear.get
          )
        )
        .toSet
      val expected = IndependentPhase6G1.expectedEdges
        .map(e =>
          (
            e.windowId,
            Set(
              IndependentPhase6G1.researcherId(e.left),
              IndependentPhase6G1.researcherId(e.right)
            ),
            e.weight,
            e.first,
            e.last
          )
        )
        .toSet
      require(
        edges.size == 18 && actual == expected,
        "G1's 18 exact windowed edges must match literal fixture expectations"
      )
      require(canonical.researchers.count() == 10, "G1 has ten canonical researchers")
      require(
        canonical.canonicalWorks.select("canonicalWorkId").distinct().count() == 9,
        "G1 has nine canonical works after the explicit w1 link"
      )
      val analytics = Phase6DEJobs.build(spark, config, canonical, lineage, run)
      val finalJobs = Phase6FGJobs.build(spark, config, canonical, analytics, lineage, run)
      val rejected = spark.createDataFrame(
        java.util.Collections.emptyList[Row](),
        new StructType()
          .add("sourceKind", "string")
          .add("sourcePath", "string")
          .add("rawLine", "string")
          .add("reason", "string")
      )
      val metadata = ujson.Obj(
        "runId" -> run,
        "hadoopRunId" -> lineage.hadoopRunId,
        "entityResolutionRunId" -> lineage.entityResolutionRunId,
        "entityResolutionPolicyVersion" -> lineage.entityResolutionPolicyVersion,
        "entityResolutionPolicyHash" -> lineage.entityResolutionPolicyHash,
        "logicalConfigFingerprint" -> config.logicalFingerprint,
        "physicalConfigFingerprint" -> config.fingerprint,
        "identityPolicyVersion" -> config.identityPolicyVersion,
        "representativePolicyVersion" -> config.representativePolicyVersion,
        "graphPolicyVersion" -> config.graphPolicyVersion,
        "windows" -> upickle.default.writeJs(config.windows),
        "seed" -> config.samplingSeed,
        "sparkVersion" -> spark.version,
        "javaVersion" -> System.getProperty("java.version"),
        "fixtureProvenance" -> "Computed through existing Phase6 public Spark jobs from IndependentPhase6G1 and IndependentPhase6FGFixtures. Synthetic direct input/link fixtures; not a Hadoop or ER execution, production code fingerprint, or acquired dataset."
      )
      val published = Phase6Export.publish(
        spark,
        config,
        canonical,
        analytics,
        finalJobs,
        rejected,
        lineage,
        run,
        metadata,
        output
      )
      require(published.size == 28, "complete Phase6 contract contains 28 tables")
      val provenance = Provenance(
        SchemaVersions.domain,
        SourceType.ScholarChain,
        "independent-g1-public-spark-harness",
        None,
        IndependentPhase6G1.snapshot,
        None,
        None,
        run,
        Vector(
          IndependentPhase6G1.note,
          "Direct synthetic source/link fixtures; upstream run IDs identify fixture lineage, not executed Hadoop/ER runs.",
          "Community iteration/convergence qualifications and approximate path statistics remain in actual computed exports."
        )
      )
      val manifest = RunManifest(
        run,
        SchemaVersions.domain,
        "independent-g1-spark-analytics",
        Vector(
          DatasetSnapshotRef(SourceType.Dblp, IndependentPhase6G1.snapshot, None),
          DatasetSnapshotRef(SourceType.Crossref, IndependentPhase6G1.snapshot, None)
        ),
        config.configSchemaVersion,
        config.fingerprint,
        provenance
      )
      require(DomainValidation.check(manifest).isRight, "G1 run manifest validation")
      val manifestText = CoreJson.compact(manifest) + "\n"
      val metadataText = metadata.render() + "\n"
      Files.writeString(output.resolve("run-manifest.json"), manifestText, UTF_8)
      Files.writeString(output.resolve("run-metadata.json"), metadataText, UTF_8)
      Files.writeString(
        output.resolve("fixture-config.json"),
        CoreJson.compact(config) + "\n",
        UTF_8
      )
      Files.writeString(
        output.resolve("g1-acceptance.json"),
        ujson
          .Obj(
            "fixture" -> "IndependentPhase6G1",
            "canonicalResearchers" -> 10,
            "canonicalWorks" -> 9,
            "windowedEdges" -> 18,
            "allExactEdgeExpectationsMatched" -> true,
            "publishedTables" -> 28,
            "sourceMode" -> "synthetic-direct-input-existing-public-Spark-jobs"
          )
          .render() + "\n",
        UTF_8
      )
      Files.writeString(
        output.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
        StableIds.sha256Hex(manifestText + "\n" + metadataText) + "\n",
        UTF_8
      )
      println(
        s"Computed G1 completed export: $output; researchers=10; works=9; edges=18; tables=28; runId=$run"
      )
    } finally spark.stop()
  }
}

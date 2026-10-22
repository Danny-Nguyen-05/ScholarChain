package edu.uic.cs441.scholarchain.core

import java.nio.file.{Files, Paths}
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.ReadWriter

/** G1 arithmetic where specified, with illustrative values for later-run output types. */
object SparkAnalyticsExamples {
  val a: String = StableIds.researcherIdFromDblpName("identity-v1", "A").toOption.get
  val b: String = StableIds.researcherIdFromDblpName("identity-v1", "B").toOption.get
  val c: String = StableIds.researcherIdFromDblpName("identity-v1", "C").toOption.get
  val d: String = StableIds.researcherIdFromDblpName("identity-v1", "D").toOption.get
  val minimumOfAG: String = Vector("A", "B", "C", "D", "E", "F", "G")
    .map(name => StableIds.researcherIdFromDblpName("identity-v1", name).toOption.get)
    .min
  val component: String =
    StableIds.sparkAnalyticsId("component", "graph-v1", "all-years", Seq(minimumOfAG)).toOption.get
  val communityA: String =
    StableIds.sparkAnalyticsId("community", "graph-v1", "all-years", Seq(a)).toOption.get
  val communityB: String =
    StableIds.sparkAnalyticsId("community", "graph-v1", "all-years", Seq(d)).toOption.get
  val edge: String = StableIds.sparkCoauthorEdgeId(a, b, "all-years", "graph-v1").toOption.get
  val work: String = "work:dblp:conf/example/w1"
  val lineage: SparkLineage = SparkLineage(
    Fixtures.runId,
    "dblp-2026-10-03",
    Fixtures.runId,
    "er-v1",
    "a" * 64,
    Vector(work),
    Vector.empty
  )
  val ctx: SparkRecordContext =
    SparkRecordContext(SchemaVersions.sparkAnalytics, Fixtures.runId, Some("all-years"), lineage)
  val bareCtx: SparkRecordContext = ctx.copy(windowId = None)
  val metrics: ResearcherMetricsDetail = ResearcherMetricsDetail(
    ctx,
    a,
    "graph-v1",
    3,
    2,
    4,
    4.0 / 3.0,
    2,
    Vector(work),
    1,
    4,
    component,
    Some(communityA),
    Some(2)
  )
  val bridge: ResearcherBridgeMetrics =
    ResearcherBridgeMetrics(ctx, c, "graph-v1", 1, 1, 1, 4.0 / 9.0)
  val componentMembership: ComponentMembership = ComponentMembership(ctx, a, component)
  val componentSummary: ComponentSummary =
    ComponentSummary(ctx, component, minimumOfAG, 7, true, 0.7, 1)
  val communityMembership: CommunityMembership =
    CommunityMembership(ctx, a, communityA, 4, true)
  val communitySummary: CommunitySummary = CommunitySummary(ctx, communityA, 3, 4, 0, true)
  val crossCommunityEdge: CrossCommunityEdge = {
    val ordered = Vector(communityA, communityB).sorted
    CrossCommunityEdge(ctx, ordered.head, ordered.last, 1, 1)
  }
  val support: CoauthorEdgeSupport = CoauthorEdgeSupport(ctx, edge, work, Some(2015))
  val edgeRecord: SparkCoauthorEdge = {
    val ordered = Vector(a, b).sorted
    SparkCoauthorEdge(
      ctx,
      edge,
      ordered.head,
      ordered.last,
      "graph-v1",
      3,
      Some(2015),
      Some(2016),
      Vector(work)
    )
  }
  val yearlessEdge: SparkCoauthorEdge =
    edgeRecord.copy(
      firstCollaborationYear = None,
      lastCollaborationYear = None,
      jointPublicationCount = 1,
      representativeWorkIds = Vector("work:dblp:conf/example/yearless")
    )
  val pathId: String =
    StableIds.sparkAnalyticsId("path-evidence", "graph-v1", "all-years", Seq(a, b)).toOption.get
  val path: PathEvidence = PathEvidence(
    ctx,
    pathId,
    a,
    b,
    PathStatus.Found,
    Some(1),
    Vector(a, b),
    Vector(PathHop(a, b, edge, 3, Vector(work))),
    6
  )
  val estimate: PathLengthEstimate =
    PathLengthEstimate(ctx, component, "seeded-multi-source-bfs", 2, 441, 1.5, 2.0, 4)
  val change: TemporalChange = TemporalChange(
    ctx.copy(windowId = Some("2020-2026")),
    a,
    "2015-2019",
    "2020-2026",
    true,
    true,
    Some(1),
    Some(0.5),
    Some(1),
    Some(2),
    true,
    false,
    Some(communityA),
    Some(communityB),
    Some(0.5),
    Some(1),
    Some(2),
    Some(1),
    Some(0.25)
  )
  val ref: SummarySourceRef =
    SummarySourceRef("metrics/researcher_collaboration", a, "publicationCount")
  val summaryId: String =
    StableIds
      .sparkSemanticSummaryId(a, "graph-v1", "all-years", "researcher-profile", "A has 3 works.")
      .toOption
      .get
  val summary: SemanticSummary =
    SemanticSummary(
      ctx,
      summaryId,
      "researcher-profile",
      a,
      "graph-v1",
      "A has 3 works.",
      Vector(ref),
      Vector.empty
    )
  val integrity: IntegrityViolation =
    IntegrityViolation(
      bareCtx,
      "selfPairsDropped",
      Some(a),
      "one collapsed pair",
      false,
      Vector(ref)
    )
  val load: LoadManifest = LoadManifest(
    bareCtx,
    "neptune",
    "researchers",
    Vector("nodes/type=researcher/run_id=example"),
    "parquet",
    10,
    Vector("researcherId"),
    Vector("type", "run_id"),
    "b" * 64,
    Vector("all-years"),
    "storage-engineer",
    Vector(NamedText("label", "Researcher"))
  )
  val counter: SparkCounter = SparkCounter(bareCtx, "selfPairsDropped", 1, None)

  val examples: Vector[(String, String)] = Vector(
    "spark-researcher-metrics-detail" -> CoreJson.pretty(metrics),
    "spark-researcher-bridge-metrics" -> CoreJson.pretty(bridge),
    "spark-component-membership" -> CoreJson.pretty(componentMembership),
    "spark-component-summary" -> CoreJson.pretty(componentSummary),
    "spark-community-membership" -> CoreJson.pretty(communityMembership),
    "spark-community-summary" -> CoreJson.pretty(communitySummary),
    "spark-cross-community-edge" -> CoreJson.pretty(crossCommunityEdge),
    "spark-coauthor-edge" -> CoreJson.pretty(edgeRecord),
    "spark-coauthor-edge-support" -> CoreJson.pretty(support),
    "spark-path-evidence" -> CoreJson.pretty(path),
    "spark-path-length-estimate" -> CoreJson.pretty(estimate),
    "spark-temporal-change" -> CoreJson.pretty(change),
    "spark-semantic-summary" -> CoreJson.pretty(summary),
    "spark-integrity-violation" -> CoreJson.pretty(integrity),
    "spark-load-manifest" -> CoreJson.pretty(load),
    "spark-counter" -> CoreJson.pretty(counter)
  )
}

/** Run explicitly when a deliberate wire snapshot update is required. */
object WriteSparkAnalyticsExamples {
  def main(args: Array[String]): Unit = {
    val root = Paths.get("modules/core/src/test/resources/wire")
    SparkAnalyticsExamples.examples.foreach { case (name, json) =>
      Files.writeString(root.resolve(s"$name.json"), json + "\n")
    }
  }
}

class SparkAnalyticsContractSpec extends AnyFunSuite {
  import SparkAnalyticsExamples.*

  private def frozen[A: ReadWriter](name: String, value: A)(
      validate: A => Either[ConfigError, A]
  ): Unit = {
    val resource = getClass.getResource(s"/wire/spark-$name.json")
    assert(resource != null, s"missing wire example for $name")
    val expected = scala.io.Source.fromURL(resource).mkString.trim
    assert(CoreJson.pretty(value) == expected)
    val parsed = CoreJson.parse[A](expected)
    assert(parsed.contains(value))
    assert(validate(parsed.toOption.get).isRight)
  }

  test("DBLP exact-name IDs preserve case and homonym suffix") {
    assert(StableIds.parseResearcherId(a).contains(a))
    assert(StableIds.researcherIdFromDblpName("identity-v1", " A ").contains(a))
    assert(StableIds.researcherIdFromDblpName("identity-v1", "a").toOption != Some(a))
    assert(StableIds.researcherIdFromDblpName("identity-v1", "A 0001").toOption != Some(a))
    assert(StableIds.researcherIdFromDblpName("bad policy", "A").isLeft)
    assert(StableIds.researcherIdFromDblpName("identity-v1", " \n ").isLeft)
    val precomposed = StableIds.researcherIdFromDblpName("identity-v1", "José")
    val decomposed = StableIds.researcherIdFromDblpName("identity-v1", "Jose\u0301")
    assert(precomposed == decomposed)
    val hash = a.stripPrefix("researcher:dblp:")
    assert(StableIds.parseResearcherId(s"researcher:dblp:${hash.dropRight(1)}").isLeft)
    assert(StableIds.parseResearcherId(s"researcher:dblp:${hash.toUpperCase}").isLeft)
    assert(StableIds.parseResearcherId(s"researcher:dblp:$hash:extra").isLeft)
  }

  test("analytics IDs reject LF-delimited collisions and invalid window labels") {
    val single = StableIds.sparkAnalyticsId("component", "graph-v1", "all-years", Seq("a\nb"))
    val split = StableIds.sparkAnalyticsId("component", "graph-v1", "all-years", Seq("a", "b"))
    assert(single.isLeft)
    assert(split.isRight)
    assert(StableIds.sparkAnalyticsId("component", "graph-v1", "all\nyears", Seq("a")).isLeft)
    assert(StableIds.sparkAnalyticsId("component", "graph-v1", " all-years", Seq("a")).isLeft)
    assert(StableIds.sparkAnalyticsId("unknown", "graph-v1", "all-years", Seq("a")).isLeft)
    assert(StableIds.sparkAnalyticsId("summary", "graph-v1", "all-years", Seq("a")).isLeft)
    assert(StableIds.sparkCoauthorEdgeId(a, b, "all\nyears", "graph-v1").isLeft)
    assert(StableIds.sparkCoauthorEdgeId(a, b, "all-years", "graph-v1").contains(edge))
  }

  test("summary IDs bind the policy and window and use citation-compatible text IDs") {
    val nextWindow = summary.copy(context = ctx.copy(windowId = Some("2020-2026")))
    val nextId = StableIds
      .sparkSemanticSummaryId(a, "graph-v1", "2020-2026", "researcher-profile", summary.text)
      .toOption
      .get
    assert(nextId != summaryId)
    assert(StableIds.parseChunkOrProfileId(nextId).contains(nextId))
    assert(SparkAnalyticsValidation.check(nextWindow).isLeft)
    assert(SparkAnalyticsValidation.check(nextWindow.copy(summaryId = nextId)).isRight)
    assert(SparkAnalyticsValidation.check(summary.copy(summaryId = "summary:" + "a" * 64)).isLeft)
    assert(SparkAnalyticsValidation.check(summary.copy(text = "A has 4 works.")).isLeft)
    assert(SparkAnalyticsValidation.check(summary.copy(policyVersion = "graph-v2")).isLeft)
  }

  test("metrics companion enforces the frozen arithmetic and max-team bounds") {
    val invalid = Vector(
      metrics.copy(averageCoauthorsPerPaper = -1.0) -> "averageCoauthorsPerPaper must be >= 0",
      metrics.copy(averageCoauthorsPerPaper = 99.0) ->
        "averageCoauthorsPerPaper must equal totalCoauthorOccurrences / publicationCount",
      metrics.copy(distinctCoauthorCount = 5) ->
        "distinctCoauthorCount cannot exceed totalCoauthorOccurrences",
      metrics.copy(maximumCoauthorsOnOnePaper = 3) ->
        "maximumCoauthorsOnOnePaper cannot exceed distinctCoauthorCount",
      metrics.copy(maximumCoauthorsOnOnePaper = 5) ->
        "maximumCoauthorsOnOnePaper cannot exceed totalCoauthorOccurrences",
      metrics.copy(
        totalCoauthorOccurrences = 0,
        weightedDegree = 0,
        maximumCoauthorsOnOnePaper = 0,
        averageCoauthorsPerPaper = 0.0
      ) ->
        "zero occurrences and zero distinct coauthors must agree",
      metrics.copy(
        totalCoauthorOccurrences = 0,
        weightedDegree = 0,
        distinctCoauthorCount = 0,
        averageCoauthorsPerPaper = 0.0
      ) ->
        "zero occurrences and zero maximum must agree",
      metrics.copy(
        totalCoauthorOccurrences = 0,
        weightedDegree = 0,
        distinctCoauthorCount = 0,
        maximumCoauthorsOnOnePaper = 0,
        averageCoauthorsPerPaper = 0.5
      ) ->
        "zero occurrences require exactly zero averageCoauthorsPerPaper",
      metrics.copy(publicationCount = 0) -> "zero publications require zero collaboration values",
      metrics.copy(publicationCount = 1, averageCoauthorsPerPaper = 4.0) ->
        "totalCoauthorOccurrences cannot exceed publicationCount times maximumCoauthorsOnOnePaper",
      metrics.copy(weightedDegree = 3) -> "weightedDegree must equal totalCoauthorOccurrences",
      metrics.copy(coreness = Some(3)) -> "coreness cannot exceed distinctCoauthorCount",
      metrics.copy(maxTeamWorkIds = Vector.empty) -> "positive publications require maxTeamWorkIds",
      metrics.copy(maxTeamWorkTieCount = 0) ->
        "maxTeamWorkTieCount must be between 1 and publicationCount",
      metrics.copy(maxTeamWorkTieCount = 4) ->
        "maxTeamWorkTieCount must be between 1 and publicationCount"
    )
    invalid.foreach { case (record, expected) =>
      assert(
        SparkAnalyticsValidation.check(record).left.exists(_.text.contains(expected)),
        expected
      )
    }
    val zero = metrics.copy(
      publicationCount = 0,
      distinctCoauthorCount = 0,
      totalCoauthorOccurrences = 0,
      averageCoauthorsPerPaper = 0.0,
      maximumCoauthorsOnOnePaper = 0,
      maxTeamWorkIds = Vector.empty,
      maxTeamWorkTieCount = 0,
      weightedDegree = 0,
      coreness = Some(0)
    )
    assert(SparkAnalyticsValidation.check(zero).isRight)
    assert(
      SparkAnalyticsValidation
        .check(zero.copy(maxTeamWorkIds = Vector(work), maxTeamWorkTieCount = 1))
        .isLeft
    )
  }

  test("G1 solo J and disconnected A-to-H are representable") {
    val j = StableIds.researcherIdFromDblpName("identity-v1", "J").toOption.get
    val h = StableIds.researcherIdFromDblpName("identity-v1", "H").toOption.get
    val work8 = "work:dblp:conf/example/w8"
    val singletonId =
      StableIds.sparkAnalyticsId("component", "graph-v1", "all-years", Seq(j)).toOption.get
    val solo = metrics.copy(
      context = ctx.copy(lineage = lineage.copy(sourceWorkIds = Vector(work8))),
      researcherId = j,
      publicationCount = 1,
      distinctCoauthorCount = 0,
      totalCoauthorOccurrences = 0,
      averageCoauthorsPerPaper = 0.0,
      maximumCoauthorsOnOnePaper = 0,
      maxTeamWorkIds = Vector(work8),
      maxTeamWorkTieCount = 1,
      weightedDegree = 0,
      componentId = singletonId,
      communityId = None,
      coreness = Some(0)
    )
    val singleton = ComponentSummary(solo.context, singletonId, j, 1, false, 0.1, 1)
    val noPathId =
      StableIds.sparkAnalyticsId("path-evidence", "graph-v1", "all-years", Seq(a, h)).toOption.get
    val noPath =
      PathEvidence(ctx, noPathId, a, h, PathStatus.NoPath, None, Vector.empty, Vector.empty, 6)
    assert(SparkAnalyticsValidation.check(solo).isRight)
    assert(SparkAnalyticsValidation.check(singleton).isRight)
    assert(SparkAnalyticsValidation.check(noPath).isRight)
  }

  test("Spark coauthor edge IDs can back cited edge evidence") {
    val evidenceId = StableIds.nonTextEvidenceId("edge", Seq(edge)).toOption.get
    val cited = Fixtures.edgeEvidence.copy(evidenceId = evidenceId, edgeLocatorId = Some(edge))
    assert(DomainValidation.check(cited).isRight)
    assert(DomainValidation.check(cited.copy(evidenceId = Fixtures.edgeEvidenceId)).isLeft)
  }

  test("all new wire examples round-trip and validate") {
    frozen("researcher-metrics-detail", metrics)(SparkAnalyticsValidation.check)
    frozen("researcher-bridge-metrics", bridge)(SparkAnalyticsValidation.check)
    frozen("component-membership", componentMembership)(SparkAnalyticsValidation.check)
    frozen("component-summary", componentSummary)(SparkAnalyticsValidation.check)
    frozen("community-membership", communityMembership)(SparkAnalyticsValidation.check)
    frozen("community-summary", communitySummary)(SparkAnalyticsValidation.check)
    frozen("cross-community-edge", crossCommunityEdge)(SparkAnalyticsValidation.check)
    frozen("coauthor-edge", edgeRecord)(SparkAnalyticsValidation.check)
    frozen("coauthor-edge-support", support)(SparkAnalyticsValidation.check)
    frozen("path-evidence", path)(SparkAnalyticsValidation.check)
    frozen("path-length-estimate", estimate)(SparkAnalyticsValidation.check)
    frozen("temporal-change", change)(SparkAnalyticsValidation.check)
    frozen("semantic-summary", summary)(SparkAnalyticsValidation.check)
    frozen("integrity-violation", integrity)(SparkAnalyticsValidation.check)
    frozen("load-manifest", load)(SparkAnalyticsValidation.check)
    frozen("counter", counter)(SparkAnalyticsValidation.check)
  }

  test("legacy edge and metrics wire examples still parse") {
    val edgeText =
      scala.io.Source.fromURL(getClass.getResource("/wire/coauthor-edge.json")).mkString
    val metricText =
      scala.io.Source.fromURL(getClass.getResource("/wire/researcher-metrics.json")).mkString
    assert(CoreJson.parse[CoauthorEdge](edgeText).isRight)
    assert(CoreJson.parse[ResearcherMetrics](metricText).isRight)
  }

  test("invalid analytics shapes fail validation") {
    assert(SparkAnalyticsValidation.check(metrics.copy(weightedDegree = 3)).isLeft)
    assert(SparkAnalyticsValidation.check(path.copy(hopCount = Some(2))).isLeft)
    assert(SparkAnalyticsValidation.check(bridge.copy(participationCoefficient = 2.0)).isLeft)
    assert(SparkAnalyticsValidation.check(support.copy(workId = "bad")).isLeft)
    assert(SparkAnalyticsValidation.check(yearlessEdge).isRight)
    assert(
      SparkAnalyticsValidation
        .check(
          support.copy(workId = "work:dblp:conf/example/yearless", year = None)
        )
        .isRight
    )
    val entrant = change.copy(
      fromPresent = false,
      previousCommunityId = None,
      communityJaccardOverlap = None,
      deltaDistinctCoauthors = None,
      deltaAverageCoauthorsPerPaper = None,
      deltaMaximumCoauthorsOnOnePaper = None,
      deltaComponentSize = None,
      deltaCrossCommunityDegree = None,
      deltaCrossCommunityWeight = None,
      deltaCommunitiesConnected = None,
      deltaParticipationCoefficient = None
    )
    assert(SparkAnalyticsValidation.check(entrant).isRight)
    assert(SparkAnalyticsValidation.check(change.copy(fromPresent = false)).isLeft)
  }

  test("versioned Spark config loads, fingerprints and validates approved defaults") {
    val resource = getClass.getResource("/scholarchain.spark-analytics-config.v1.json")
    val text = scala.io.Source.fromURL(resource).mkString
    val loaded = SparkAnalyticsConfigLoader.loadText(text).toOption.get
    assert(loaded.windows.size == 6)
    assert(loaded.windows.head.startYear.isEmpty && loaded.windows.head.endYear.isEmpty)
    assert(loaded.windows(1).endYear.contains(2009))
    assert(loaded.representativeWorkLimit == 5 && loaded.maxTeamWorkLimit == 20)
    assert(loaded.fingerprint == StableIds.sha256Hex(loaded.canonicalJson))
    val runManifest = Fixtures.manifest.copy(
      configSchemaVersion = SchemaVersions.sparkAnalyticsConfig,
      configFingerprint = loaded.fingerprint
    )
    assert(DomainValidation.check(runManifest).isRight)
    assert(SparkAnalyticsConfigLoader.loadText(loaded.canonicalJson).contains(loaded))
    assert(SparkAnalyticsConfigLoader.validate(loaded.copy(maxHops = 0)).isLeft)
    assert(SparkAnalyticsConfigLoader.validate(loaded.copy(windows = Vector.empty)).isLeft)
    assert(
      SparkAnalyticsConfigLoader
        .loadText(
          text.replace(
            "\"failOnHardInvariant\": true",
            "\"failOnHardInvariant\": true, \"unknown\": 1"
          )
        )
        .left
        .exists(_.text.contains("unsupported field"))
    )
    assert(
      SparkAnalyticsConfigLoader
        .validate(
          loaded.copy(
            benchmarkPairs = Vector(BenchmarkPair("A\nB", "C", "dblp-name"))
          )
        )
        .isLeft
    )
    assert(
      SparkAnalyticsConfigLoader
        .validate(
          loaded.copy(
            outputRoot = "${OUTPUT_ROOT}"
          )
        )
        .isLeft
    )
  }

  test("Spark config rejects duplicate, reversed and nonconsecutive comparison windows") {
    val resource = getClass.getResource("/scholarchain.spark-analytics-config.v1.json")
    val loaded =
      SparkAnalyticsConfigLoader.loadText(scala.io.Source.fromURL(resource).mkString).toOption.get
    def rejects(config: SparkAnalyticsConfig, message: String): Unit =
      assert(
        SparkAnalyticsConfigLoader.validate(config).left.exists(_.text.contains(message)),
        message
      )
    rejects(
      loaded.copy(windows = loaded.windows :+ loaded.windows(1)),
      "windowId values must be unique"
    )
    rejects(
      loaded.copy(windows =
        loaded.windows.updated(2, loaded.windows(2).copy(startYear = Some(2015)))
      ),
      "reversed window"
    )
    rejects(
      loaded.copy(windows =
        loaded.windows.updated(2, loaded.windows(2).copy(startYear = Some(2009)))
      ),
      "comparison windows must be consecutive and non-overlapping"
    )
    rejects(
      loaded.copy(windows =
        loaded.windows.updated(2, loaded.windows(2).copy(startYear = Some(2011)))
      ),
      "comparison windows must be consecutive and non-overlapping"
    )
    rejects(
      loaded.copy(windows = loaded.windows.updated(2, loaded.windows(2).copy(startYear = None))),
      "comparison windows must be consecutive and non-overlapping"
    )
    rejects(
      loaded.copy(windows =
        loaded.windows.updated(2, loaded.windows(2).copy(comparisonOrder = Some(0)))
      ),
      "comparisonOrder values must be unique"
    )
    rejects(
      loaded.copy(benchmarkPairs = Vector(BenchmarkPair("A", "B", "unknown"))),
      "benchmark pair has invalid endpoints or endpointKind"
    )
  }
}

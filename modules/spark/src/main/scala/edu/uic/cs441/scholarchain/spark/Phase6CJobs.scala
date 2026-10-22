package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import org.apache.spark.sql.{DataFrame, Row, RowFactory, SparkSession}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.types.*
import org.apache.spark.sql.api.java.{UDF1, UDF2, UDF4}
import scala.jdk.CollectionConverters.*

/** Normalized input columns are documented in modules/spark/README.md. */
final case class Phase6CInput(
    works: DataFrame,
    mentions: DataFrame,
    teams: DataFrame,
    pairs: DataFrame,
    researcherLinks: DataFrame,
    workLinks: DataFrame,
    researcherCannotLinks: DataFrame,
    workCannotLinks: DataFrame,
    researcherAuthority: DataFrame,
    workAuthority: DataFrame,
    venues: DataFrame = null,
    institutions: DataFrame = null,
    topics: DataFrame = null,
    enrichments: DataFrame = null,
    researcherUnresolved: DataFrame = null,
    researcherConflicts: DataFrame = null,
    workUnresolved: DataFrame = null,
    workConflicts: DataFrame = null
)

final case class Phase6CResult(
    researchers: DataFrame,
    mentions: DataFrame,
    works: DataFrame,
    canonicalWorks: DataFrame,
    memberships: DataFrame,
    edges: DataFrame,
    support: DataFrame,
    integrity: DataFrame,
    counters: DataFrame,
    graphNodes: DataFrame,
    graphEdges: DataFrame
)

object Phase6CJobs {
  private def emptyPairs(spark: SparkSession): DataFrame = {
    val schema = new StructType().add("leftId", StringType).add("rightId", StringType)
    spark.createDataFrame(java.util.Collections.emptyList[Row](), schema)
  }
  private def columns(df: DataFrame, names: String*): Unit =
    require(
      names.forall(df.columns.contains),
      s"missing input columns: ${names.filterNot(df.columns.contains).mkString(",")}"
    )

  /** Undirected link labels, with a bounded iteration guard and distributed joins at every hop. */
  private def components(vertices: DataFrame, links: DataFrame, maxIterations: Int): DataFrame = {
    val spark = vertices.sparkSession
    val base = vertices.select(col("id")).distinct().filter(col("id").isNotNull)
    val arcs = links
      .select(col("leftId").as("from"), col("rightId").as("to"))
      .unionByName(links.select(col("rightId").as("from"), col("leftId").as("to")))
      .filter(col("from").isNotNull && col("to").isNotNull && col("from") =!= col("to"))
      .distinct()
      .cache()
    var labels = base
      .select(col("id"), col("id").as("label"))
      .checkpoint(eager = true)
      .cache()
    var changed = true; var iteration = 0
    while (changed && iteration < maxIterations) {
      val propagated = arcs
        .join(labels.select(col("id").as("from"), col("label")), Seq("from"))
        .select(col("to").as("id"), col("label"))
      val next = labels
        .unionByName(propagated)
        .groupBy("id")
        .agg(min(col("label")).as("label"))
        .checkpoint(eager = true)
        .cache()
      changed = BoundedActions.exists(
        labels
          .as("old")
          .join(next.as("new"), Seq("id"))
          .filter(col("old.label") =!= col("new.label"))
      )
      labels.unpersist(); labels = next
      iteration += 1
    }
    arcs.unpersist()
    require(!changed, s"identity grouping did not converge in $maxIterations iterations")
    labels
  }

  def build(
      spark: SparkSession,
      config: SparkAnalyticsConfig,
      input: Phase6CInput,
      lineage: SparkLineage,
      runId: String
  ): Phase6CResult = {
    SparkAnalyticsConfigLoader
      .validate(config)
      .fold(e => throw new IllegalArgumentException(e.toString), identity)
    StableIds.parseRunId(runId).fold(e => throw new IllegalArgumentException(e.toString), identity)
    columns(
      input.works,
      "workId",
      "source",
      "sourceRecordId",
      "year",
      "title",
      "doi",
      "arxivId",
      "venueId",
      "snapshot"
    )
    columns(
      input.mentions,
      "mentionId",
      "source",
      "sourceRecordId",
      "nameText",
      "observedOrcid",
      "snapshot"
    )
    columns(input.teams, "workId", "source", "sourceRecordId", "memberMentionIds")
    columns(
      input.pairs,
      "workId",
      "source",
      "sourceRecordId",
      "leftMentionId",
      "rightMentionId",
      "year"
    )
    Seq(input.researcherLinks, input.workLinks, input.researcherCannotLinks, input.workCannotLinks)
      .foreach(columns(_, "leftId", "rightId"))
    Seq(input.researcherAuthority, input.workAuthority)
      .foreach(columns(_, "endpointId", "namespace", "value"))
    spark.sparkContext.setCheckpointDir(config.checkpointDirectory)
    spark.conf.set("spark.sql.shuffle.partitions", config.shufflePartitions)
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    spark.udf.register(
      "phase6DblpResearcherId",
      new UDF2[String, String, String] {
        def call(policy: String, name: String): String = StableIds
          .researcherIdFromDblpName(policy, name)
          .fold(e => throw new IllegalArgumentException(e.toString), identity)
      },
      StringType
    )
    spark.udf.register(
      "phase6EdgeId",
      new UDF4[String, String, String, String, String] {
        def call(a: String, b: String, windowId: String, policy: String): String = {
          val window = config.windows.find(_.windowId == windowId).get
          StableIds
            .sparkCoauthorEdgeId(a, b, window, policy)
            .fold(e => throw new IllegalArgumentException(e.toString), identity)
        }
      },
      StringType
    )
    spark.udf.register(
      "phase6Context",
      new UDF1[String, String] {
        def call(windowId: String): String = CoreJson.compact(
          SparkRecordContext(SchemaVersions.sparkAnalytics, runId, Option(windowId), lineage)
        )
      },
      StringType
    )
    spark.udf.register(
      "phase6GraphEdgeId",
      new UDF1[Row, String] {
        def call(fact: Row): String = {
          val kind = fact.getAs[String]("edgeType")
          val edgeType = GraphEdgeType.values
            .find(_.wire == kind)
            .getOrElse(throw new IllegalArgumentException(s"unsupported graph edge type $kind"))
          val work = fact.getAs[String]("evidenceWorkId")
          val evidence =
            if (work != null) GraphSourceEvidence.Work(work)
            else {
              val source = SourceType.values
                .find(_.wire == fact.getAs[String]("evidenceSource"))
                .getOrElse(throw new IllegalArgumentException("unknown graph evidence source"))
              GraphSourceEvidence.SourceRecord(
                source,
                fact.getAs[String]("evidenceSourceRecordId"),
                fact.getAs[String]("evidenceSnapshot")
              )
            }
          StableIds
            .graphEdgeId(
              edgeType,
              fact.getAs[String]("fromId"),
              fact.getAs[String]("toId"),
              config.graphPolicyVersion,
              evidence
            )
            .fold(e => throw new IllegalArgumentException(e.toString), identity)
        }
      },
      StringType
    )

    val works = input.works.dropDuplicates("source", "sourceRecordId", "snapshot").cache()
    val mentions = input.mentions.dropDuplicates("mentionId").cache()
    val dblp = mentions
      .filter(col("source") === "DBLP")
      .withColumn(
        "researcherId",
        expr(s"phase6DblpResearcherId('${config.identityPolicyVersion}', nameText)")
      )
      .cache()
    val researcherTargets = dblp.select(col("mentionId").as("id"), col("researcherId"))
    val linkEdges = input.researcherLinks.select("leftId", "rightId").distinct()
    val crossName = linkEdges
      .join(
        researcherTargets.select(col("id").as("leftId"), col("researcherId").as("leftResearcher")),
        Seq("leftId")
      )
      .join(
        researcherTargets
          .select(col("id").as("rightId"), col("researcherId").as("rightResearcher")),
        Seq("rightId")
      )
      .filter(col("leftResearcher") =!= col("rightResearcher"))
      .select("leftId", "rightId")
      .distinct()
      .cache()
    val safeResearcherLinks = linkEdges
      .join(crossName, Seq("leftId", "rightId"), "left_anti")
      .join(
        input.researcherCannotLinks.select("leftId", "rightId"),
        Seq("leftId", "rightId"),
        "left_anti"
      )
    val researcherVertices = mentions
      .select(col("mentionId").as("id"))
      .unionByName(safeResearcherLinks.select(col("leftId").as("id")))
      .unionByName(safeResearcherLinks.select(col("rightId").as("id")))
    val researcherGroups =
      components(researcherVertices, safeResearcherLinks, config.componentMaxIterations).cache()
    val researcherCannotGroups = input.researcherCannotLinks
      .join(
        researcherGroups.select(col("id").as("leftId"), col("label").as("leftLabel")),
        Seq("leftId")
      )
      .join(
        researcherGroups.select(col("id").as("rightId"), col("label").as("rightLabel")),
        Seq("rightId")
      )
      .filter(col("leftLabel") === col("rightLabel"))
      .select(col("leftLabel").as("label"))
    val researcherAuthorityGroups = researcherGroups
      .join(input.researcherAuthority, col("id") === col("endpointId"))
      .groupBy("label", "namespace")
      .agg(countDistinct("value").as("differentValues"))
      .filter(col("differentValues") > 1)
      .select("label")
    val blockedResearcherGroups = researcherCannotGroups
      .unionByName(researcherAuthorityGroups)
      .distinct()
      .cache()
    val groupTargets = researcherGroups
      .join(researcherTargets, Seq("id"))
      .groupBy("label")
      .agg(countDistinct("researcherId").as("targetCount"), min("researcherId").as("targetId"))
    val direct = dblp.select(col("mentionId"), col("researcherId"))
    val nonDblpTargets = researcherGroups
      .join(blockedResearcherGroups, Seq("label"), "left_anti")
      .join(groupTargets.filter(col("targetCount") === 1L), Seq("label"))
      .join(mentions.select(col("mentionId").as("id")), Seq("id"))
      .select(col("id").as("mentionId"), col("targetId").as("researcherId"))
    val mapping = nonDblpTargets
      .unionByName(direct)
      .groupBy("mentionId")
      .agg(min("researcherId").as("researcherId"))
      .cache()
    val researchers = dblp
      .groupBy("researcherId")
      .agg(
        min("nameText").as("displayName"),
        sort_array(collect_set("observedOrcid")).as("externalOrcids"),
        sort_array(collect_set("mentionId")).as("sourceMentionIds")
      )
      .withColumn("runId", lit(runId))
      .withColumn("schemaVersion", lit(SchemaVersions.domain))
    val conflictingDblpOrcids = dblp
      .filter(col("observedOrcid").isNotNull && trim(col("observedOrcid")) =!= "")
      .groupBy("researcherId")
      .agg(
        countDistinct("observedOrcid").as("distinctOrcids"),
        sort_array(collect_set("observedOrcid")).as("orcids")
      )
      .filter(col("distinctOrcids") > 1L)
      .cache()

    val workLinks = input.workLinks.select("leftId", "rightId").distinct()
    val workVertices = works
      .select(col("workId").as("id"))
      .unionByName(workLinks.select(col("leftId").as("id")))
      .unionByName(workLinks.select(col("rightId").as("id")))
    val candidateWorkGroups =
      components(workVertices, workLinks, config.componentMaxIterations).cache()
    val workCannot = candidateWorkGroups
      .select(col("id").as("leftId"), col("label").as("leftLabel"))
      .join(input.workCannotLinks, Seq("leftId"))
      .join(
        candidateWorkGroups.select(col("id").as("rightId"), col("label").as("rightLabel")),
        Seq("rightId")
      )
      .filter(col("leftLabel") === col("rightLabel"))
      .select(col("leftLabel").as("label"))
      .distinct()
    val conflictingAuthority = candidateWorkGroups
      .join(input.workAuthority, col("id") === col("endpointId"))
      .groupBy("label", "namespace")
      .agg(countDistinct("value").as("differentValues"))
      .filter(col("differentValues") > 1)
      .select("label")
      .distinct()
    val blockedGroups = workCannot.unionByName(conflictingAuthority).distinct().cache()
    val workMap = candidateWorkGroups
      .join(blockedGroups.withColumn("blocked", lit(true)), Seq("label"), "left")
      .withColumn("groupId", when(col("blocked") === true, col("id")).otherwise(col("label")))
      .select(col("id").as("workId"), col("groupId"))
      .cache()
    val workMembers = works.join(workMap, Seq("workId"))
    val groupRep = workMembers
      .groupBy("groupId")
      .agg(
        min(when(col("source") === "DBLP", col("workId"))).as("dblpWorkId"),
        min(when(col("doi").isNotNull, col("workId"))).as("doiWorkId"),
        min(when(col("arxivId").isNotNull, col("workId"))).as("arxivWorkId"),
        min("workId").as("minWorkId")
      )
      .withColumn(
        "canonicalWorkId",
        coalesce(col("doiWorkId"), col("arxivWorkId"), col("dblpWorkId"), col("minWorkId"))
      )
      .select("groupId", "canonicalWorkId")
    val dblpSource = workMembers
      .filter(col("source") === "DBLP")
      .withColumn(
        "sourceRank",
        row_number().over(
          Window
            .partitionBy("groupId")
            .orderBy(col("sourceRecordId"), col("workId"))
        )
      )
      .filter(col("sourceRank") === 1)
      .select(
        col("groupId"),
        col("sourceRecordId").as("authoritativeSourceRecordId"),
        col("year").as("dblpYear"),
        col("workId").as("authoritativeWorkId")
      )
    val canonicalWorks = workMembers
      .join(groupRep, Seq("groupId"))
      .join(dblpSource, Seq("groupId"), "left")
      .select(
        col("workId"),
        col("sourceRecordId"),
        col("canonicalWorkId"),
        col("authoritativeSourceRecordId"),
        col("dblpYear").as("year"),
        col("authoritativeSourceRecordId").isNotNull.as("hasDblp"),
        col("authoritativeWorkId"),
        col("groupId")
      )
      .dropDuplicates("workId", "sourceRecordId")
      .cache()
    val nonAuthoritativeDblpObservations = works
      .filter(col("source") === "DBLP")
      .join(
        canonicalWorks.select(
          "workId",
          "sourceRecordId",
          "authoritativeWorkId",
          "authoritativeSourceRecordId"
        ),
        Seq("workId", "sourceRecordId")
      )
      .filter(
        col("workId") =!= col("authoritativeWorkId") ||
          col("sourceRecordId") =!= col("authoritativeSourceRecordId")
      )
      .select("workId", "sourceRecordId")
      .distinct()
    val selectedTeam = input.teams
      .filter(col("source") === "DBLP")
      .join(canonicalWorks.filter(col("hasDblp")), Seq("workId", "sourceRecordId"))
      .filter(
        col("workId") === col("authoritativeWorkId") &&
          col("sourceRecordId") === col("authoritativeSourceRecordId")
      )
      .select("workId", "canonicalWorkId", "sourceRecordId", "memberMentionIds", "year")
      .dropDuplicates("canonicalWorkId", "sourceRecordId")
      .cache()
    val teamMembers = selectedTeam
      .select(
        col("canonicalWorkId"),
        col("workId"),
        col("sourceRecordId"),
        col("year"),
        explode(col("memberMentionIds")).as("mentionId")
      )
      .join(mapping, Seq("mentionId"), "left")
    val memberships = teamMembers
      .filter(col("researcherId").isNotNull)
      .select("canonicalWorkId", "workId", "mentionId", "researcherId", "year")
      .dropDuplicates("canonicalWorkId", "researcherId")
      .cache()
    val duplicateTeamMembers = teamMembers
      .filter(col("researcherId").isNotNull)
      .groupBy("canonicalWorkId")
      .agg(count("*").as("rawMembers"), countDistinct("researcherId").as("distinctMembers"))
      .select(sum(col("rawMembers") - col("distinctMembers")).as("duplicates"))
    val pairMapped = input.pairs
      .filter(col("source") === "DBLP")
      .join(
        selectedTeam
          .select("workId", "sourceRecordId", "canonicalWorkId", "year")
          .withColumnRenamed("year", "teamYear"),
        Seq("workId", "sourceRecordId")
      )
      .join(
        mapping
          .select(col("mentionId").as("leftMentionId"), col("researcherId").as("leftResearcher")),
        Seq("leftMentionId"),
        "left"
      )
      .join(
        mapping
          .select(col("mentionId").as("rightMentionId"), col("researcherId").as("rightResearcher")),
        Seq("rightMentionId"),
        "left"
      )
      .cache()
    val validPairs = pairMapped
      .filter(
        col("leftResearcher").isNotNull &&
          col("rightResearcher").isNotNull && col("leftResearcher") =!= col("rightResearcher")
      )
      .select(
        col("canonicalWorkId"),
        col("teamYear").as("year"),
        least(col("leftResearcher"), col("rightResearcher")).as("researcherA"),
        greatest(col("leftResearcher"), col("rightResearcher")).as("researcherB")
      )
      .dropDuplicates("canonicalWorkId", "researcherA", "researcherB")
      .cache()
    val expectedPairs = memberships
      .groupBy("canonicalWorkId")
      .agg(countDistinct("researcherId").as("teamSize"))
      .withColumn("expected", col("teamSize") * (col("teamSize") - lit(1L)) / lit(2L))
    val actualPairs = validPairs
      .groupBy("canonicalWorkId")
      .agg(count("*").as("actual"))
    val pairMismatch = expectedPairs
      .join(actualPairs, Seq("canonicalWorkId"), "left")
      .filter(coalesce(col("actual"), lit(0L)) =!= col("expected"))
    val windowDef = config.windows.map { w =>
      RowFactory.create(w.windowId, w.startYear.map(Int.box).orNull, w.endYear.map(Int.box).orNull)
    }.asJava
    val windowSchema = new StructType()
      .add("windowId", StringType)
      .add("windowStartYear", IntegerType)
      .add("windowEndYear", IntegerType)
    val windows = broadcast(spark.createDataFrame(windowDef, windowSchema))
    val expanded = validPairs
      .crossJoin(windows)
      .filter(
        (col("windowStartYear").isNull && col("windowEndYear").isNull) ||
          (col("year").isNotNull &&
            (col("windowStartYear").isNull || col("year") >= col("windowStartYear")) &&
            (col("windowEndYear").isNull || col("year") <= col("windowEndYear")))
      )
      .repartition(col("windowId"), col("researcherA"), col("researcherB"))
      .cache()
    val edgeMaterial = expanded
      .groupBy("windowId", "windowStartYear", "windowEndYear", "researcherA", "researcherB")
      .agg(
        countDistinct("canonicalWorkId").as("jointPublicationCount"),
        min("year").as("firstCollaborationYear"),
        max("year").as("lastCollaborationYear")
      )
      .withColumn("policyVersion", lit(config.graphPolicyVersion))
      .withColumn("edgeId", expr("phase6EdgeId(researcherA,researcherB,windowId,policyVersion)"))
      .cache()
    val edgeOrder = Window
      .partitionBy("windowId", "researcherA", "researcherB")
      .orderBy(col("year").desc_nulls_last, col("canonicalWorkId"))
    val reps = expanded
      .withColumn("rank", row_number().over(edgeOrder))
      .filter(col("rank") <= config.representativeWorkLimit)
      .groupBy("windowId", "researcherA", "researcherB")
      .agg(sort_array(collect_list(struct(col("rank"), col("canonicalWorkId")))).as("ordered"))
      .withColumn("representativeWorkIds", expr("transform(ordered, x -> x.canonicalWorkId)"))
      .drop("ordered")
    val contextSchema = new StructType()
      .add("schemaVersion", StringType)
      .add("runId", StringType)
      .add("windowId", StringType)
      .add(
        "lineage",
        new StructType()
          .add("hadoopRunId", StringType)
          .add("hadoopSnapshot", StringType)
          .add("entityResolutionRunId", StringType)
          .add("entityResolutionPolicyVersion", StringType)
          .add("entityResolutionPolicyHash", StringType)
          .add("sourceWorkIds", ArrayType(StringType))
          .add("sourceMentionIds", ArrayType(StringType))
      )
    def context(df: DataFrame): DataFrame =
      df.withColumn("context", from_json(expr("phase6Context(windowId)"), contextSchema))
    val edges =
      context(edgeMaterial.join(reps, Seq("windowId", "researcherA", "researcherB"))).cache()
    val support = context(
      expanded
        .join(
          edgeMaterial.select("windowId", "researcherA", "researcherB", "edgeId"),
          Seq("windowId", "researcherA", "researcherB")
        )
        .select(col("windowId"), col("edgeId"), col("canonicalWorkId").as("workId"), col("year"))
        .dropDuplicates("edgeId", "workId")
    ).cache()

    val counterValues = Vector(
      "crossDblpNameLinksNotApplied" -> BoundedActions.count(crossName),
      "erResearcherUnresolved" -> Option(input.researcherUnresolved)
        .fold(0L)(BoundedActions.count),
      "erResearcherConflicts" -> Option(input.researcherConflicts)
        .fold(0L)(BoundedActions.count),
      "erWorkUnresolved" -> Option(input.workUnresolved).fold(0L)(BoundedActions.count),
      "erWorkConflicts" -> Option(input.workConflicts).fold(0L)(BoundedActions.count),
      "conflictingDblpOrcidGroups" -> BoundedActions.count(conflictingDblpOrcids),
      "constraintBlockedResearcherGroups" -> BoundedActions.count(blockedResearcherGroups),
      "ambiguousNonDblpMentions" -> BoundedActions.count(
        groupTargets.filter(col("targetCount") > 1)
      ),
      "unresolvedMentions" -> BoundedActions.count(
        mentions.join(mapping, Seq("mentionId"), "left_anti")
      ),
      "constraintBlockedWorkLinks" -> BoundedActions.count(blockedGroups),
      "nonAuthoritativeDblpObservationsDropped" -> BoundedActions.count(
        nonAuthoritativeDblpObservations
      ),
      "enrichmentOnlyWorksExcluded" -> BoundedActions.count(
        canonicalWorks
          .filter(!col("hasDblp"))
          .select("canonicalWorkId")
          .distinct()
      ),
      "duplicateTeamMembersCollapsed" -> BoundedActions.scalarLong(
        duplicateTeamMembers
          .select(coalesce(col("duplicates"), lit(0L)).as("duplicates")),
        "duplicates"
      ),
      "selfPairsDropped" -> BoundedActions.count(
        pairMapped.filter(
          col("leftResearcher") ===
            col("rightResearcher") && col("leftResearcher").isNotNull
        )
      ),
      "unmappedPairsDropped" -> BoundedActions.count(
        pairMapped.filter(
          col("leftResearcher").isNull ||
            col("rightResearcher").isNull
        )
      ),
      "pairCountMismatches" -> BoundedActions.count(pairMismatch),
      "sourceWorks" -> BoundedActions.count(works),
      "canonicalWorks" -> BoundedActions.count(canonicalWorks.select("canonicalWorkId").distinct()),
      "canonicalResearchers" -> BoundedActions.count(researchers),
      "allYearsEdges" -> BoundedActions.count(edges.filter(col("windowId") === "all-years"))
    ) ++ config.windows.filter(w => w.startYear.nonEmpty || w.endYear.nonEmpty).map { w =>
      s"missingYearExcluded.${w.windowId}" -> BoundedActions.count(
        validPairs
          .filter(col("year").isNull)
          .select("canonicalWorkId")
          .distinct()
      )
    } ++ Vector(
      "post2026WorksAllYearsOnly" -> BoundedActions.count(
        canonicalWorks
          .filter(col("hasDblp") && col("year") > 2026)
          .select("canonicalWorkId")
          .distinct()
      )
    )
    val counterSchema = new StructType()
      .add("context", contextSchema)
      .add("name", StringType)
      .add("value", LongType)
      .add("detail", StringType)
    val counterRows = counterValues.map { case (name, value) =>
      RowFactory.create(
        RowFactory.create(
          SchemaVersions.sparkAnalytics,
          runId,
          null,
          RowFactory.create(
            lineage.hadoopRunId,
            lineage.hadoopSnapshot,
            lineage.entityResolutionRunId,
            lineage.entityResolutionPolicyVersion,
            lineage.entityResolutionPolicyHash,
            lineage.sourceWorkIds.asJava,
            lineage.sourceMentionIds.asJava
          )
        ),
        name,
        Long.box(value),
        null
      )
    }.asJava
    val baseCounters = spark.createDataFrame(counterRows, counterSchema)
    val violations = pairMismatch
      .select(
        lit("pair-count-mismatch").as("code"),
        col("canonicalWorkId").as("entityId"),
        concat(lit("expected="), col("expected"), lit(" actual="), coalesce(col("actual"), lit(0L)))
          .as("detail"),
        lit(true).as("hardFailure")
      )
      .unionByName(
        blockedGroups.select(
          lit("constraint-blocked-work-group").as("code"),
          col("label").as("entityId"),
          lit("candidate group left unmerged").as("detail"),
          lit(false).as("hardFailure")
        )
      )
      .unionByName(
        conflictingDblpOrcids.select(
          lit("conflicting-dblp-orcid").as("code"),
          col("researcherId").as("entityId"),
          concat(lit("observed ORCIDs="), concat_ws(",", col("orcids"))).as("detail"),
          lit(false).as("hardFailure")
        )
      )
    val basicNodes = researchers
      .select(
        col("researcherId").as("nodeId"),
        lit("RESEARCHER").as("nodeClass"),
        col("displayName").as("label")
      )
      .unionByName(
        mentions.select(
          col("mentionId").as("nodeId"),
          lit("AUTHOR_MENTION").as("nodeClass"),
          col("nameText").as("label")
        )
      )
      .unionByName(
        works
          .select(col("workId").as("nodeId"), lit("WORK").as("nodeClass"), col("title").as("label"))
      )
    def optionalNodes(df: DataFrame, id: String, name: String, kind: String): DataFrame =
      if (df == null) basicNodes.limit(0)
      else df.select(col(id).as("nodeId"), lit(kind).as("nodeClass"), col(name).as("label"))
    val graphNodes = basicNodes
      .unionByName(optionalNodes(input.venues, "venueId", "name", "VENUE"))
      .unionByName(optionalNodes(input.institutions, "institutionId", "name", "INSTITUTION"))
      .unionByName(optionalNodes(input.topics, "topicId", "name", "TOPIC"))
      .groupBy("nodeId", "nodeClass")
      .agg(min("label").as("label"))
      .withColumn("runId", lit(runId))
      .withColumn("schemaVersion", lit(SchemaVersions.domain))
      .withColumn(
        "context",
        from_json(
          lit(
            CoreJson.compact(
              SparkRecordContext(SchemaVersions.sparkAnalytics, runId, None, lineage)
            )
          ),
          contextSchema
        )
      )
      .withColumn(
        "properties",
        array().cast(
          ArrayType(
            new StructType()
              .add("name", StringType)
              .add("value", StringType)
          )
        )
      )
      .withColumn(
        "provenance",
        struct(
          lit(SchemaVersions.domain).as("schemaVersion"),
          lit("SCHOLARCHAIN").as("source"),
          col("nodeId").as("sourceRecordId"),
          lit(null).cast(StringType).as("sourceUri"),
          lit("spark-analytics").as("datasetSnapshot"),
          lit(null).cast(StringType).as("retrievalDate"),
          lit(null).cast(StringType).as("licenseEvidenceUri"),
          lit(runId).as("runId"),
          array(lit("derived from completed Hadoop and ER inputs")).as("uncertaintyNotes")
        )
      )
      .checkpoint(eager = true)
    val mentionWorks = mentions
      .join(
        works.select("workId", "source", "sourceRecordId", "snapshot"),
        Seq("source", "sourceRecordId", "snapshot"),
        "left"
      )
      .select(col("mentionId"), col("workId").as("evidenceWorkId"))
    val resolveEdges = mapping
      .join(mentionWorks, Seq("mentionId"))
      .select(
        col("mentionId").as("fromId"),
        col("researcherId").as("toId"),
        lit("RESOLVES_TO").as("edgeType"),
        col("evidenceWorkId")
      )
    val authoredEdges = memberships.select(
      col("researcherId").as("fromId"),
      col("canonicalWorkId").as("toId"),
      lit("AUTHORED").as("edgeType"),
      col("canonicalWorkId").as("evidenceWorkId")
    )
    val venueEdges = works
      .filter(col("venueId").isNotNull)
      .select(
        col("workId").as("fromId"),
        col("venueId").as("toId"),
        lit("PUBLISHED_IN").as("edgeType"),
        col("workId").as("evidenceWorkId")
      )
    val enrichmentEdges =
      if (input.enrichments == null) resolveEdges.limit(0)
      else
        input.enrichments
          .filter(col("targetKind").isin("TOPIC", "INSTITUTION"))
          .join(mapping, Seq("mentionId"), "left")
          .join(
            mentionWorks.select(col("mentionId"), col("evidenceWorkId").as("mentionWorkId")),
            Seq("mentionId"),
            "left"
          )
          .withColumn(
            "fromId",
            when(col("targetKind") === "TOPIC", col("workId"))
              .otherwise(col("researcherId"))
          )
          .select(
            col("fromId"),
            col("targetId").as("toId"),
            when(col("targetKind") === "TOPIC", lit("HAS_TOPIC"))
              .otherwise(lit("AFFILIATED_WITH"))
              .as("edgeType"),
            coalesce(col("workId"), col("mentionWorkId")).as("evidenceWorkId")
          )
          .filter(col("fromId").isNotNull)
    val graphEdges = resolveEdges
      .unionByName(authoredEdges)
      .unionByName(venueEdges)
      .unionByName(enrichmentEdges)
      .filter(col("evidenceWorkId").isNotNull)
      .withColumn(
        "evidenceRank",
        row_number().over(
          Window.partitionBy("fromId", "toId", "edgeType").orderBy(col("evidenceWorkId"))
        )
      )
      .filter(col("evidenceRank") === 1)
      .drop("evidenceRank")
      .withColumn("runId", lit(runId))
      .withColumn("schemaVersion", lit(SchemaVersions.domain))
      .withColumn("policyVersion", lit(config.graphPolicyVersion))
      .withColumn("edgeId", expr("phase6GraphEdgeId(struct(edgeType,fromId,toId,evidenceWorkId))"))
      .withColumn(
        "sourceEvidence",
        struct(lit("Work").as("$type"), col("evidenceWorkId").as("workId"))
      )
      .withColumn(
        "properties",
        array().cast(
          ArrayType(
            new StructType()
              .add("name", StringType)
              .add("value", StringType)
          )
        )
      )
      .withColumn(
        "coauthorship",
        lit(null).cast(
          new StructType()
            .add("jointPublicationCount", LongType)
            .add("firstCollaborationYear", IntegerType)
            .add("lastCollaborationYear", IntegerType)
            .add("representativeWorkIds", ArrayType(StringType))
        )
      )
      .withColumn(
        "provenance",
        struct(
          lit(SchemaVersions.domain).as("schemaVersion"),
          lit("SCHOLARCHAIN").as("source"),
          col("edgeId").as("sourceRecordId"),
          lit(null).cast(StringType).as("sourceUri"),
          lit("spark-analytics").as("datasetSnapshot"),
          lit(null).cast(StringType).as("retrievalDate"),
          lit(null).cast(StringType).as("licenseEvidenceUri"),
          lit(runId).as("runId"),
          array(lit("derived from completed Hadoop and ER inputs")).as("uncertaintyNotes")
        )
      )
      .withColumn(
        "context",
        from_json(
          lit(
            CoreJson.compact(
              SparkRecordContext(SchemaVersions.sparkAnalytics, runId, None, lineage)
            )
          ),
          contextSchema
        )
      )
      .checkpoint(eager = true)
    val missingFromEndpoints = graphEdges
      .join(graphNodes.select(col("nodeId").as("fromId")), Seq("fromId"), "left_anti")
      .select(
        lit("missing-graph-endpoint").as("code"),
        col("edgeId").as("entityId"),
        concat(lit("missing fromId="), col("fromId")).as("detail"),
        lit(true).as("hardFailure")
      )
    val missingToEndpoints = graphEdges
      .join(graphNodes.select(col("nodeId").as("toId")), Seq("toId"), "left_anti")
      .select(
        lit("missing-graph-endpoint").as("code"),
        col("edgeId").as("entityId"),
        concat(lit("missing toId="), col("toId")).as("detail"),
        lit(true).as("hardFailure")
      )
    val missingGraphEndpoints = missingFromEndpoints.unionByName(missingToEndpoints).distinct()
    val integrity = violations.unionByName(missingGraphEndpoints).checkpoint(eager = true)
    if (config.failOnHardInvariant && BoundedActions.exists(integrity.filter(col("hardFailure"))))
      throw new IllegalStateException("Phase 6C hard graph integrity invariant failed")
    val counters = baseCounters.unionByName(
      baseCounters
        .limit(1)
        .withColumn("name", lit("missingGraphEndpoints"))
        .withColumn("value", lit(BoundedActions.count(missingGraphEndpoints)))
        .withColumn("detail", lit("missing fromId or toId references"))
    )
    val finalResearchers = researchers.checkpoint(eager = true)
    val finalMentions = mentions.checkpoint(eager = true)
    val finalWorks = works.checkpoint(eager = true)
    val finalCanonicalWorks = canonicalWorks.checkpoint(eager = true)
    val finalMemberships = memberships.checkpoint(eager = true)
    val finalEdges = edges.checkpoint(eager = true)
    val finalSupport = support.checkpoint(eager = true)
    Vector(
      works,
      mentions,
      dblp,
      conflictingDblpOrcids,
      crossName,
      researcherGroups,
      blockedResearcherGroups,
      mapping,
      candidateWorkGroups,
      blockedGroups,
      workMap,
      canonicalWorks,
      selectedTeam,
      memberships,
      pairMapped,
      validPairs,
      expanded,
      edgeMaterial,
      edges,
      support
    )
      .foreach(_.unpersist())
    Phase6CResult(
      finalResearchers,
      finalMentions,
      finalWorks,
      finalCanonicalWorks,
      finalMemberships,
      finalEdges,
      finalSupport,
      integrity,
      counters,
      graphNodes,
      graphEdges
    )
  }
}

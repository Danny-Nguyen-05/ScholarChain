package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.{SparkLineage, StableIds}
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.security.MessageDigest
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.*
import scala.collection.mutable.ArrayBuffer
import scala.jdk.CollectionConverters.*

/** Strict local completion and byte-inventory checks followed by explicit Spark JSON schemas. */
object Phase6CReaders {
  private val string = StringType
  private val integer = IntegerType
  private val strings = ArrayType(StringType, containsNull = false)
  private val provenance = new StructType()
    .add("schemaVersion", string)
    .add("source", string)
    .add("sourceRecordId", string)
    .add("sourceUri", string)
    .add("datasetSnapshot", string)
    .add("retrievalDate", string)
    .add("licenseEvidenceUri", string)
    .add("runId", string)
    .add("uncertaintyNotes", strings)
  private val mention = new StructType()
    .add("mentionId", string)
    .add("schemaVersion", string)
    .add("source", string)
    .add("sourceRecordId", string)
    .add("ordinal", integer)
    .add("nameText", string)
    .add("normalizedName", string)
    .add("observedOrcid", string)
    .add("observedOpenAlexAuthorId", string)
    .add("identityStatus", string)
    .add("resolvedResearcherId", string)
    .add("uncertainty", string)
    .add("provenance", provenance)
  private val namedText = new StructType().add("name", string).add("value", string)
  private val observedId = new StructType()
    .add("namespace", string)
    .add("value", string)
    .add("interpretation", string)
  private[spark] val work = new StructType()
    .add("schemaVersion", string)
    .add("workId", string)
    .add("source", string)
    .add("sourceRecordId", string)
    .add("sourceRecordType", string)
    .add("title", string)
    .add("normalizedTitle", string)
    .add("year", integer)
    .add("venueId", string)
    .add("doi", string)
    .add("arxivId", string)
    .add("pages", string)
    .add("externalUrl", string)
    .add("authors", ArrayType(mention))
    .add("abstractTextRef", string)
    .add("provenance", provenance)
    .add("observedIdentifiers", ArrayType(observedId))
    .add("sourceLinks", ArrayType(namedText))
  private val team = new StructType()
    .add("schemaVersion", string)
    .add("workId", string)
    .add("memberMentionIds", strings)
    .add("teamSize", integer)
    .add("uncertainty", string)
    .add("provenance", provenance)
  private val pair = new StructType()
    .add("schemaVersion", string)
    .add("workId", string)
    .add("doi", string)
    .add("arxivId", string)
    .add("leftMentionId", string)
    .add("rightMentionId", string)
    .add("leftOrdinal", integer)
    .add("rightOrdinal", integer)
    .add("year", integer)
    .add("uncertainty", string)
    .add("provenance", provenance)
  private val venue = new StructType()
    .add("venueId", string)
    .add("schemaVersion", string)
    .add("name", string)
    .add("sourceLabel", string)
    .add("issn", string)
    .add("uncertainty", string)
    .add("provenance", provenance)
  private val institution = new StructType()
    .add("institutionId", string)
    .add("schemaVersion", string)
    .add("name", string)
    .add("ror", string)
    .add("ringgold", string)
    .add("uncertainty", string)
    .add("provenance", provenance)
    .add("observedSourceIds", ArrayType(observedId))
  private val topic = new StructType()
    .add("topicId", string)
    .add("schemaVersion", string)
    .add("name", string)
    .add("sourceTopicId", string)
    .add("sourceScore", DoubleType)
    .add("uncertainty", string)
    .add("provenance", provenance)
  private val enrichment = new StructType()
    .add("schemaVersion", string)
    .add("source", string)
    .add("sourceRecordId", string)
    .add("datasetSnapshot", string)
    .add("workId", string)
    .add("mentionId", string)
    .add("targetKind", string)
    .add("targetId", string)
    .add("ror", string)
    .add("ringgold", string)
    .add("score", DoubleType)
    .add("uncertainty", string)
    .add("runId", string)
    .add("provenance", provenance)
  private val mentionAffiliation = new StructType()
    .add("schemaVersion", string)
    .add("mentionId", string)
    .add("source", string)
    .add("sourceRecordId", string)
    .add("datasetSnapshot", string)
    .add("organizationName", string)
    .add("ror", string)
    .add("ringgold", string)
    .add("institutionId", string)
    .add("uncertainty", string)
    .add("provenance", provenance)
  private val authorship = new StructType()
    .add("schemaVersion", string)
    .add("workId", string)
    .add("mentionId", string)
    .add("position", integer)
    .add("resolvedResearcherId", string)
    .add("uncertainty", string)
    .add("provenance", provenance)
  private val observation = new StructType()
    .add("source", string)
    .add("sourceRecordId", string)
    .add("datasetSnapshot", string)
  private val endpoint = new StructType()
    .add("$type", string)
    .add("observation", observation)
    .add("workId", string)
    .add("mentionId", string)
    .add("orcid", string)
    .add("observedWorkId", string)
  private val erPair = new StructType()
    .add("schemaVersion", string)
    .add("pairId", string)
    .add("entityType", string)
    .add("left", endpoint)
    .add("right", endpoint)
  private[spark] val link = new StructType()
    .add("schemaVersion", string)
    .add("pair", erPair)
    .add("decisionId", string)
    .add("policyVersion", string)
    .add("policyHash", string)
    .add("runId", string)
    .add("provenance", provenance)
  private val matchDecision = new StructType()
    .add("schemaVersion", string)
    .add("sourceId", string)
    .add("targetId", string)
    .add("features", ArrayType(new StructType().add("name", string).add("value", DoubleType)))
    .add("decision", string)
    .add("confidence", DoubleType)
    .add("reasonCodes", strings)
    .add("policyVersion", string)
    .add("runId", string)
    .add("uncertainty", string)
    .add("provenance", provenance)
  private val preAdjudication = new StructType()
    .add("score", DoubleType)
    .add("outcome", string)
    .add("decisionPath", string)
  private val adjudication = new StructType()
    .add("requestHash", string)
    .add("promptVersion", string)
    .add("promptHash", string)
    .add("responseSchemaVersion", string)
    .add("provider", string)
    .add("model", string)
    .add("modelVersion", string)
    .add("generationSettingsHash", string)
    .add("cacheKey", string)
    .add("mode", string)
    .add("cacheHit", BooleanType)
    .add("reportedConfidence", DoubleType)
    .add("evidenceRefs", strings)
    .add("preAdjudication", preAdjudication)
  private[spark] val resolutionDecision = new StructType()
    .add("schemaVersion", string)
    .add("decisionId", string)
    .add("pair", erPair)
    .add("decision", matchDecision)
    .add(
      "contributingCandidates",
      ArrayType(new StructType().add("candidateId", string).add("blockKey", string))
    )
    .add("featurePolicyVersion", string)
    .add(
      "featureEvidence",
      ArrayType(
        new StructType()
          .add("name", string)
          .add("value", DoubleType)
          .add("missingReason", string)
          .add("evidenceRefs", strings)
      )
    )
    .add("decisionPath", string)
    .add("confidenceSemantics", string)
    .add("scoreUnavailableReason", string)
    .add("policyHash", string)
    .add("configHash", string)
    .add("inputEvidenceHash", string)
    .add("evidenceRefs", strings)
    .add("decidedAtUtc", string)
    .add("adjudication", adjudication)
  private val cannot = new StructType()
    .add("pair", erPair)
    .add("reasonCode", string)
    .add("evidenceRefs", strings)
  private val assertion = new StructType()
    .add("endpoint", endpoint)
    .add("namespace", string)
    .add("value", string)
    .add("evidenceRefs", strings)
  private[spark] val constraints = new StructType()
    .add("schemaVersion", string)
    .add("entityType", string)
    .add("policyVersion", string)
    .add("policyHash", string)
    .add("coveredEndpoints", ArrayType(endpoint))
    .add("cannotLinks", ArrayType(cannot))
    .add("authoritativeIdentifiers", ArrayType(assertion))

  private def hash(path: Path): String = {
    val digest = MessageDigest.getInstance("SHA-256")
    val stream = Files.newInputStream(path)
    val buffer = Array.ofDim[Byte](65536)
    try {
      var length = stream.read(buffer)
      while (length >= 0) {
        if (length > 0) digest.update(buffer, 0, length)
        length = stream.read(buffer)
      }
    } finally stream.close()
    java.util.HexFormat.of().formatHex(digest.digest())
  }
  private def field(value: ujson.Value, key: String): String = value(key).str
  private[spark] def prepCompletionHash(markerText: String, manifestText: String): String =
    StableIds.sha256Hex(markerText + "\n" + manifestText)
  private[spark] def requireErPrepBinding(expectedHash: String, erManifest: ujson.Value): Unit =
    require(
      erManifest.obj.get("prepCompletionHash").exists(_.str == expectedHash),
      "ER prepCompletionHash does not match selected Hadoop completion and manifest"
    )
  private def safe(root: Path, name: String): Path = {
    require(!Path.of(name).isAbsolute && !name.split('/').contains(".."), s"unsafe path: $name")
    val path = root.resolve(name).normalize()
    require(
      path.startsWith(root) && Files.isRegularFile(path) && !Files.isSymbolicLink(path),
      s"missing or unsafe inventory path: $name"
    )
    path
  }
  private def actualFiles(root: Path, skip: Set[String]): Set[String] = {
    val walk = Files.walk(root)
    try
      walk
        .iterator()
        .asScala
        .filter(Files.isRegularFile(_))
        .map(root.relativize(_).toString)
        .filterNot(name =>
          name.split('/').last.startsWith(".") ||
            name.split('/').last.startsWith("_") || skip(name)
        )
        .toSet
    finally walk.close()
  }
  private[spark] def verifyHadoop(
      root: Path
  ): (String, String, String, ujson.Value, Map[String, Vector[Path]]) = {
    require(
      Files.isDirectory(root) && !Files.isSymbolicLink(root),
      "completed Hadoop root required"
    )
    val markerText = Files.readString(safe(root, "_SCHOLARCHAIN_COMPLETE"), UTF_8)
    val marker = ujson.read(markerText)
    val manifestPath = safe(root, "run-manifest.json")
    val manifestText = Files.readString(manifestPath, UTF_8)
    val manifest = ujson.read(manifestText)
    require(
      marker("complete").bool && field(marker, "runId") == field(manifest, "runId"),
      "Hadoop completion/manifest mismatch"
    )
    require(
      field(marker, "schemaVersion") == "scholarchain.domain.v1" &&
        field(marker, "hadoopPrepSchema") == "scholarchain.hadoop-prep.v1" &&
        field(marker, "configFingerprint") == field(manifest, "configFingerprint"),
      "unsupported Hadoop completion schema/config"
    )
    val exportRoot = root.resolve("export")
    require(Files.isRegularFile(safe(root, "export/_SUCCESS")), "Hadoop export incomplete")
    val parts = marker("exportParts").arr.toVector
    val names = parts.map(p => field(p, "path"))
    require(
      names.distinct.size == names.size && actualFiles(exportRoot, Set.empty) == names.toSet,
      "Hadoop export inventory mismatch"
    )
    val byKind = parts
      .map { part =>
        val name = field(part, "path")
        val path = safe(exportRoot, name)
        require(
          Files.size(path) == part("bytes").num.toLong && hash(path) == field(part, "sha256"),
          s"Hadoop export byte/hash mismatch: $name"
        )
        val tokens = name.split('/').toVector
        (if (tokens.size >= 4) tokens(tokens.size - 2) else "other") -> path
      }
      .groupMap(_._1)(_._2)
      .view
      .mapValues(_.toVector)
      .toMap
    (
      field(manifest, "runId"),
      hash(manifestPath),
      prepCompletionHash(markerText, manifestText),
      manifest,
      byKind
    )
  }
  private[spark] def verifyEr(root: Path): (String, String, ujson.Value) = {
    require(Files.isDirectory(root) && !Files.isSymbolicLink(root), "completed ER root required")
    val manifestPath = safe(root, "resolution-manifest.json")
    val manifestText = Files.readString(manifestPath, UTF_8)
    val marker = Files.readString(safe(root, "_SCHOLARCHAIN_RESOLUTION_COMPLETE"), UTF_8)
    require(marker == StableIds.sha256Hex(manifestText) + "\n", "ER completion hash mismatch")
    val manifest = ujson.read(manifestText)
    require(
      manifest("complete").bool && field(manifest, "schemaVersion") ==
        "scholarchain.resolution-export.v1",
      "unsupported ER manifest"
    )
    val files = manifest("files").arr.toVector
    val names = files.map(f => field(f, "path"))
    require(
      names.distinct.size == names.size &&
        actualFiles(
          root,
          Set("resolution-manifest.json", "_SCHOLARCHAIN_RESOLUTION_COMPLETE")
        ) == names.toSet,
      "ER inventory mismatch"
    )
    files.foreach { f =>
      val name = field(f, "path"); val path = safe(root, name)
      require(
        Files.size(path) == f("bytes").num.toLong && hash(path) == field(f, "sha256"),
        s"ER export byte/hash mismatch: $name"
      )
    }
    require(manifest("constraints").arr.size == 2, "both ER grouping constraints required")
    (field(manifest, "runId"), hash(manifestPath), manifest)
  }

  private[spark] def read(
      spark: SparkSession,
      paths: Vector[Path],
      shape: StructType,
      version: String,
      required: Seq[String],
      rejectSink: Option[ArrayBuffer[DataFrame]] = None,
      sourceKind: String = "unspecified"
  ): DataFrame = {
    val schema = shape.add("_corrupt_record", StringType)
    if (paths.isEmpty)
      spark.createDataFrame(java.util.Collections.emptyList[org.apache.spark.sql.Row](), schema)
    else {
      val rows = spark.read
        .schema(schema)
        .option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", "_corrupt_record")
        .json(paths.map(_.toString)*)
        .withColumn("_source_path", input_file_name())
        .cache()
      val corrupt = rows
        .filter(col("_corrupt_record").isNotNull)
        .select(
          lit(sourceKind).as("sourceKind"),
          col("_source_path").as("sourcePath"),
          col("_corrupt_record").as("rawLine"),
          lit("malformed JSON or incompatible field type").as("reason")
        )
        .checkpoint(eager = true)
      if (rejectSink.isEmpty && BoundedActions.exists(corrupt))
        throw new IllegalArgumentException("corrupt JSON line rejected; no reject sink supplied")
      rejectSink.foreach(_ += corrupt)
      val valid = rows.filter(col("_corrupt_record").isNull)
      if (
        BoundedActions.exists(
          valid.filter(
            col("schemaVersion").isNull ||
              col("schemaVersion") =!= lit(version)
          )
        )
      )
        throw new IllegalArgumentException(s"schema version mismatch; expected $version")
      required.foreach { key =>
        if (BoundedActions.exists(valid.filter(col(key).isNull)))
          throw new IllegalArgumentException(s"required JSON field missing: $key")
      }
      valid.drop("_corrupt_record", "_source_path")
    }
  }
  private def endpointId(c: org.apache.spark.sql.Column): org.apache.spark.sql.Column =
    when(c.getField("$type") === "Mention", c.getField("mentionId"))
      .when(c.getField("$type") === "Work", c.getField("workId"))
      .when(c.getField("$type") === "OrcidProfile", concat(lit("orcid:"), c.getField("orcid")))
      .when(c.getField("$type") === "OrcidWorkActivity", c.getField("observedWorkId"))
      .otherwise(lit(null).cast(StringType))

  private[spark] def readErDecision(
      spark: SparkSession,
      path: Path,
      entityType: String,
      outcome: String,
      rejected: ArrayBuffer[DataFrame]
  ): DataFrame = {
    val rows = read(
      spark,
      Vector(path),
      resolutionDecision,
      "scholarchain.resolution.v1",
      Seq("decisionId", "pair", "decision", "policyHash"),
      Some(rejected),
      s"ER/$entityType/$outcome"
    )
    require(
      !BoundedActions.exists(
        rows.filter(
          col("pair.entityType").isNull ||
            col("pair.entityType") =!= entityType ||
            col("decision.decision").isNull ||
            col("decision.decision") =!= outcome
        )
      ),
      s"ER $entityType $outcome file contains another entity or outcome"
    )
    rows.select(
      col("decisionId"),
      col("pair.pairId").as("pairId"),
      col("pair.entityType").as("entityType"),
      col("decision.decision").as("outcome"),
      col("decision.reasonCodes").as("reasonCodes"),
      col("policyHash")
    )
  }

  def load(spark: SparkSession, hadoopRoot: Path, erRoot: Path): VerifiedPhase6CInput = {
    val (hadoopRun, hadoopHash, prepHash, hadoopManifest, kinds) = verifyHadoop(hadoopRoot)
    val (erRun, erHash, erManifest) = verifyEr(erRoot)
    requireErPrepBinding(prepHash, erManifest)
    val domain = "scholarchain.domain.v1"; val resolution = "scholarchain.resolution.v1"
    val rejected = ArrayBuffer.empty[DataFrame]
    def source(kind: String, shape: StructType, required: Seq[String]): DataFrame =
      read(
        spark,
        kinds.getOrElse(kind, Vector.empty),
        shape,
        domain,
        required,
        Some(rejected),
        s"Hadoop/$kind"
      )
    val works = source("work", work, Seq("workId", "source", "sourceRecordId", "provenance"))
      .select(
        "workId",
        "source",
        "sourceRecordId",
        "year",
        "title",
        "abstractTextRef",
        "doi",
        "arxivId",
        "venueId",
        "provenance"
      )
      .withColumn("snapshot", col("provenance.datasetSnapshot"))
      .drop("provenance")
    val mentions = source(
      "author-mention",
      mention,
      Seq("mentionId", "source", "sourceRecordId", "nameText", "provenance")
    )
      .select("mentionId", "source", "sourceRecordId", "nameText", "observedOrcid", "provenance")
      .withColumn("snapshot", col("provenance.datasetSnapshot"))
      .drop("provenance")
    val teams = source("team", team, Seq("workId", "memberMentionIds", "provenance"))
      .select("workId", "memberMentionIds", "provenance")
      .withColumn("source", col("provenance.source"))
      .withColumn("sourceRecordId", col("provenance.sourceRecordId"))
      .drop("provenance")
    val pairs = source("pair", pair, Seq("workId", "leftMentionId", "rightMentionId", "provenance"))
      .select("workId", "leftMentionId", "rightMentionId", "year", "provenance")
      .withColumn("source", col("provenance.source"))
      .withColumn("sourceRecordId", col("provenance.sourceRecordId"))
      .drop("provenance")
    val venues = source("venue", venue, Seq("venueId", "name"))
      .select("venueId", "name")
      .dropDuplicates("venueId")
    val institutions = source("institution", institution, Seq("institutionId", "name"))
      .select("institutionId", "name")
      .dropDuplicates("institutionId")
    val topics = source("topic", topic, Seq("topicId", "name"))
      .select("topicId", "name")
      .dropDuplicates("topicId")
    val enrichments = source("enrichment", enrichment, Seq("targetKind", "targetId", "provenance"))
      .select(
        "workId",
        "mentionId",
        "targetKind",
        "targetId",
        "source",
        "sourceRecordId",
        "datasetSnapshot"
      )
      .withColumnRenamed("datasetSnapshot", "snapshot")
    // Read and validate the remaining required domain-v1 kinds even when jobs 1–2 do not
    // materialize a separate table for their unchanged source facts.
    source("authorship", authorship, Seq("workId", "mentionId", "provenance"))
    source("mention-affiliation", mentionAffiliation, Seq("mentionId", "provenance"))
    source(
      "graph-edge",
      new StructType()
        .add("edgeId", string)
        .add("schemaVersion", string)
        .add("fromId", string)
        .add("edgeType", string)
        .add("toId", string)
        .add("policyVersion", string)
        .add(
          "sourceEvidence",
          new StructType()
            .add("$type", string)
            .add("workId", string)
            .add("source", string)
            .add("sourceRecordId", string)
            .add("datasetSnapshot", string)
        )
        .add("properties", ArrayType(namedText))
        .add(
          "coauthorship",
          new StructType()
            .add("jointPublicationCount", LongType)
            .add("firstCollaborationYear", integer)
            .add("lastCollaborationYear", integer)
            .add("representativeWorkIds", strings)
        )
        .add("provenance", provenance),
      Seq("edgeId", "provenance")
    )
    def er(name: String, shape: StructType, required: Seq[String]): DataFrame =
      read(
        spark,
        Vector(safe(erRoot, name)),
        shape,
        resolution,
        required,
        Some(rejected),
        s"ER/$name"
      )
    def links(entity: String): DataFrame =
      er(s"$entity/accepted-links.jsonl", link, Seq("pair", "decisionId", "policyHash"))
        .select(
          endpointId(col("pair.left")).as("leftId"),
          endpointId(col("pair.right")).as("rightId")
        )
    def constraint(entity: String): DataFrame = er(
      s"$entity/grouping-constraints.json",
      constraints,
      Seq("entityType", "coveredEndpoints", "cannotLinks", "authoritativeIdentifiers")
    )
    val researcherConstraints = constraint("researcher")
    val workConstraints = constraint("work")
    def cannot(df: DataFrame): DataFrame = df
      .select(explode(col("cannotLinks")).as("item"))
      .select(
        endpointId(col("item.pair.left")).as("leftId"),
        endpointId(col("item.pair.right")).as("rightId")
      )
      .filter(col("leftId").isNotNull && col("rightId").isNotNull)
    def authority(df: DataFrame): DataFrame = df
      .select(explode(col("authoritativeIdentifiers")).as("item"))
      .select(
        endpointId(col("item.endpoint")).as("endpointId"),
        col("item.namespace").as("namespace"),
        col("item.value").as("value")
      )
      .filter(col("endpointId").isNotNull)
    // The exported constraints are complete: every accepted-link endpoint must be covered.
    def coverage(df: DataFrame, linkRows: DataFrame): Unit = {
      val covered = df
        .select(explode(col("coveredEndpoints")).as("endpoint"))
        .select(endpointId(col("endpoint")).as("id"))
        .filter(col("id").isNotNull)
        .distinct()
      val ends = linkRows
        .select(col("leftId").as("id"))
        .unionByName(linkRows.select(col("rightId").as("id")))
        .distinct()
      require(
        !BoundedActions.exists(ends.join(covered, Seq("id"), "left_anti")),
        "ER accepted link outside complete grouping constraints"
      )
    }
    val researcherLinks = links("researcher"); val workLinks = links("work")
    val researcherUnresolved = readErDecision(
      spark,
      safe(erRoot, "researcher/unresolved.jsonl"),
      "Researcher",
      "UNRESOLVED",
      rejected
    )
    val researcherConflicts = readErDecision(
      spark,
      safe(erRoot, "researcher/conflict.jsonl"),
      "Researcher",
      "CONFLICT",
      rejected
    )
    val workUnresolved = readErDecision(
      spark,
      safe(erRoot, "work/unresolved.jsonl"),
      "Work",
      "UNRESOLVED",
      rejected
    )
    val workConflicts = readErDecision(
      spark,
      safe(erRoot, "work/conflict.jsonl"),
      "Work",
      "CONFLICT",
      rejected
    )
    coverage(researcherConstraints, researcherLinks); coverage(workConstraints, workLinks)
    val lineage = SparkLineage(
      hadoopRun,
      hadoopManifest("datasetSnapshots").arr.map(v => v("snapshot").str).sorted.mkString(","),
      erRun,
      field(erManifest, "policyVersion"),
      field(erManifest, "policyHash"),
      Vector.empty,
      Vector.empty
    )
    VerifiedPhase6CInput(
      Phase6CInput(
        works,
        mentions,
        teams,
        pairs,
        researcherLinks,
        workLinks,
        cannot(researcherConstraints),
        cannot(workConstraints),
        authority(researcherConstraints),
        authority(workConstraints),
        venues,
        institutions,
        topics,
        enrichments,
        researcherUnresolved,
        researcherConflicts,
        workUnresolved,
        workConflicts
      ),
      lineage,
      hadoopRun,
      hadoopHash,
      erRun,
      erHash,
      rejected
        .reduceOption(_.unionByName(_))
        .getOrElse(
          spark.createDataFrame(
            java.util.Collections.emptyList[org.apache.spark.sql.Row](),
            new StructType()
              .add("sourceKind", StringType)
              .add("sourcePath", StringType)
              .add("rawLine", StringType)
              .add("reason", StringType)
          )
        )
    )
  }
}

final case class VerifiedPhase6CInput(
    input: Phase6CInput,
    lineage: SparkLineage,
    hadoopRunId: String,
    hadoopManifestHash: String,
    erRunId: String,
    erManifestHash: String,
    rejectedLines: DataFrame
)

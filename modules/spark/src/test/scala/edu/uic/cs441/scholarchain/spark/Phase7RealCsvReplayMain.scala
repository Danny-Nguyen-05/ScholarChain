package edu.uic.cs441.scholarchain.spark

import com.univocity.parsers.csv.{CsvParser, CsvParserSettings}
import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.*
import scala.jdk.CollectionConverters.*

/** Explicit local replay only; never discovered as a default test or used to modify a retained run.
  */
object Phase7RealCsvReplayMain {
  def main(args: Array[String]): Unit = {
    require(
      args.length == 5,
      "usage: Phase7RealCsvReplayMain <completed-source-root> <new-output-root> <max-coauthors> <max-graph-edges> <max-closure-rows>"
    )
    val source = Path.of(args(0)).toRealPath()
    val output = Path.of(args(1)).toAbsolutePath.normalize()
    val maxCoauthors = args(2).toInt
    val maxGraphEdges = args(3).toInt
    val maxRows = args(4).toInt
    require(
      maxCoauthors > 0 && maxGraphEdges > 0 && maxRows >= maxCoauthors * 4L,
      "positive limits and closure budget >= four rows per sampled coauthor required"
    )
    require(
      !Files.exists(output) && !output.startsWith(source),
      "fresh output outside source required"
    )
    val bindingNames =
      Vector("run-manifest.json", "run-metadata.json", "_SCHOLARCHAIN_SPARK_COMPLETE")
    val before = bindingNames.map(n => n -> Files.readString(source.resolve(n), UTF_8)).toMap
    require(
      before("_SCHOLARCHAIN_SPARK_COMPLETE") == StableIds.sha256Hex(
        before("run-manifest.json") + "\n" + before("run-metadata.json")
      ) + "\n",
      "source completion mismatch"
    )
    val manifest = CoreJson.parse[RunManifest](before("run-manifest.json")).toOption.get
    require(DomainValidation.check(manifest).isRight, "invalid source run manifest")
    val metadata = ujson.read(before("run-metadata.json"))
    val runId = metadata("runId").str
    require(runId == manifest.runId, "source run identity mismatch")
    val sourceTables = metadata("tables").arr.toVector
    val nodeNames = sourceTables
      .map(_("path").str)
      .filter(n => n.startsWith("nodes/") && n != "nodes/type=work_sources")
    val graphNames = sourceTables
      .map(_("path").str)
      .filter(n => n.startsWith("edges/") && !n.startsWith("edges/type=coauthored_with"))
    Files.createDirectories(output)
    val spark = SparkSession
      .builder()
      .master("local[2]")
      .appName("Bounded retained Phase6 CSV replay")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "4")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.warehouse.dir", output.resolve("warehouse").toString)
      .getOrCreate()
    try {
      def read(name: String): DataFrame =
        spark.read.parquet(source.resolve(name).toString).drop("run_id")
      def union(names: Vector[String]): DataFrame = names.map(read).reduce(_.unionByName(_))
      val perEdgeSupportBudget = maxRows / (maxCoauthors * 2L)
      val allCoauthors = read("edges/type=coauthored_with")
      val coauthors = allCoauthors
        .filter(col("jointPublicationCount") <= lit(perEdgeSupportBudget))
        .orderBy(
          col("firstCollaborationYear").asc_nulls_first,
          col("windowStartYear").asc_nulls_first,
          col("windowEndYear").asc_nulls_first,
          col("edgeId")
        )
        .limit(maxCoauthors)
        .cache()
      require(coauthors.count() > 0, "no coherent coauthor sample fits configured budget")
      val support = read(Phase7NeptuneExport.supportPath)
        .join(coauthors.select("edgeId"), Seq("edgeId"), "left_semi")
        .cache()
      val graphEdges = union(graphNames)
        .join(
          support.select(col("workId").as("selectedWorkId")).distinct(),
          col("sourceEvidence.workId") === col("selectedWorkId"),
          "left_semi"
        )
        .orderBy("edgeId")
        .limit(maxGraphEdges)
        .cache()
      val ids = coauthors
        .select(col("researcherA").as("nodeId"))
        .unionByName(coauthors.select(col("researcherB").as("nodeId")))
        .unionByName(support.select(col("workId").as("nodeId")))
        .unionByName(graphEdges.select(col("fromId").as("nodeId")))
        .unionByName(graphEdges.select(col("toId").as("nodeId")))
        .distinct()
      val nodes = union(nodeNames).join(ids, Seq("nodeId"), "left_semi").cache()
      val communities = read("metrics/type=communities")
        .join(
          nodes.filter(col("nodeClass") === "RESEARCHER").select(col("nodeId").as("researcherId")),
          Seq("researcherId"),
          "left_semi"
        )
        .join(
          coauthors.select(col("context.windowId").as("selectedWindow")).distinct(),
          col("window") === col("selectedWindow"),
          "left_semi"
        )
        .cache()
      Vector(
        "nodes" -> nodes,
        "graphEdges" -> graphEdges,
        "coauthors" -> coauthors,
        "support" -> support,
        "communities" -> communities
      ).foreach { case (name, data) =>
        require(data.limit(maxRows + 1).count() <= maxRows, s"$name exceeds closure budget")
      }
      val sampled = nodeNames.map(n =>
        (n, nodes.filter(col("nodeClass") === n.split("=").last.toUpperCase), Vector("nodeId"))
      ) ++
        graphNames.map(n =>
          (
            n,
            graphEdges.filter(col("edgeType") === n.split("=").last.toUpperCase),
            Vector("edgeId")
          )
        ) ++
        Vector(
          ("edges/type=coauthored_with", coauthors, Vector("edgeId")),
          (Phase7NeptuneExport.supportPath, support, Vector("edgeId", "workId")),
          ("metrics/type=communities", communities, Vector("researcherId"))
        )
      val published = sampled.map { case (name, data, keys) =>
        data.write.mode("errorifexists").parquet(output.resolve(name).toString)
        Phase6PublishedTable(
          name,
          name,
          data.count(),
          Phase6Export.logicalTableHash(data),
          keys,
          Vector.empty
        )
      }
      Phase7NeptuneExport.publish(output, nodes, graphEdges, coauthors, support, published, runId)
      // These files describe this bounded derivative only. Source identities/lineage remain intact;
      // original full-table counts/hashes and counters are never attached to sampled tables.
      val sampleNote =
        "Bounded Phase7 local CSV replay sample; not the original full analytics export"
      val sampleManifest = manifest.copy(provenance =
        manifest.provenance.copy(
          uncertaintyNotes = manifest.provenance.uncertaintyNotes :+ sampleNote
        )
      )
      val sampleMetadata = ujson.read(before("run-metadata.json"))
      sampleMetadata("tables") = ujson.Arr.from(
        published.map(t =>
          ujson.Obj(
            "dataset" -> t.name,
            "path" -> t.path,
            "rowCount" -> t.rowCount,
            "contentHash" -> t.contentHash,
            "keys" -> ujson.Arr.from(t.keys),
            "partitions" -> ujson.Arr()
          )
        )
      )
      sampleMetadata("boundedReplaySample") = ujson.Obj(
        "qualification" -> sampleNote,
        "sourceRoot" -> source.toString,
        "originalMetadataHash" -> StableIds.sha256Hex(before("run-metadata.json")),
        "exporterCodeVersion" -> Phase6Main.codeFingerprint,
        "maxCoauthors" -> maxCoauthors,
        "maxGraphEdges" -> maxGraphEdges,
        "maxClosureRows" -> maxRows
      )
      val sampleRunJson = CoreJson.compact(sampleManifest) + "\n"
      val sampleMetaJson = sampleMetadata.render() + "\n"
      Files.writeString(output.resolve("run-manifest.json"), sampleRunJson, UTF_8)
      Files.writeString(output.resolve("run-metadata.json"), sampleMetaJson, UTF_8)
      Files.writeString(output.resolve("counters.json"), "[]\n", UTF_8)
      val originalLoads = CoreJson
        .parse[Vector[LoadManifest]](
          Files.readString(source.resolve("load-manifests/s3.json"), UTF_8)
        )
        .toOption
        .get
      val sampleLoads = published.map { table =>
        originalLoads
          .find(_.logicalDataset == table.name)
          .get
          .copy(
            paths = Vector(table.path),
            rowCount = table.rowCount,
            keyColumns = table.keys,
            partitionColumns = Vector.empty,
            sortedRowsSha256 = table.contentHash,
            targetMapping = originalLoads.find(_.logicalDataset == table.name).get.targetMapping :+
              NamedText("boundedReplayQualification", sampleNote)
          )
      }
      Files.writeString(
        output.resolve("load-manifests/s3.json"),
        CoreJson.compact(sampleLoads) + "\n",
        UTF_8
      )
      val sidecar =
        ujson.read(Files.readString(output.resolve(Phase7NeptuneExport.sidecarPath), UTF_8))
      val expectedFrames = Phase7NeptuneExport.frames(nodes, graphEdges, coauthors, support).toMap
      def parseCsv(path: String): Vector[Map[String, String]] = {
        val listing = Files.list(output.resolve(path))
        val files =
          try listing.iterator().asScala.toVector
          finally listing.close()
        require(
          files.nonEmpty && files.forall(_.getFileName.toString.endsWith(".csv")),
          "non-CSV loader file"
        )
        val parsed = files.flatMap { file =>
          val settings = new CsvParserSettings()
          settings.getFormat.setLineSeparator("\r\n")
          settings.setHeaderExtractionEnabled(true)
          settings.setNormalizeLineEndingsWithinQuotes(false)
          settings.setMaxCharsPerColumn(1024 * 1024)
          val parser = new CsvParser(settings)
          val reader = Files.newBufferedReader(file, UTF_8)
          val rows = Vector.newBuilder[Map[String, String]]
          var count = 0
          try {
            parser.beginParsing(reader)
            var next = parser.parseNextRecord()
            while (next != null) {
              count += 1
              require(count <= maxRows, "CSV physical file exceeds configured row bound")
              rows += next.toFieldMap().asScala.toMap
              next = parser.parseNextRecord()
            }
            rows.result()
          } finally { parser.stopParsing(); reader.close() }
        }
        require(parsed.size <= maxRows, "CSV dataset exceeds configured row bound")
        parsed
      }
      val parsed = sidecar("datasets").arr.toVector.map { dataset =>
        val path = dataset("path").str
        val kind = path.split("/").last
        val rows = parseCsv(path)
        require(dataset("rowCount").str.toLong == rows.size, "CSV row count mismatch")
        val schema = expectedFrames(kind).schema
        val typed = rows.map { row =>
          Row.fromSeq(schema.fields.toVector.map { field =>
            Option(row(field.name)).map { value =>
              field.dataType match {
                case IntegerType => value.toInt
                case LongType    => value.toLong
                case StringType  => value
                case other => throw new IllegalArgumentException(s"unexpected CSV type $other")
              }
            }.orNull
          })
        }
        val reconstructed = spark.createDataFrame(typed.asJava, schema)
        require(
          Phase6Export.logicalTableHash(reconstructed) == dataset("contentHash").str,
          s"CSV content hash mismatch: $kind"
        )
        kind -> rows
      }.toMap
      def sourceIds(data: DataFrame, field: String): Set[String] =
        data.select(field).collect().map(_.getString(0)).toSet
      require(
        parsed("nodes").map(_(":ID")).toSet == sourceIds(nodes, "nodeId"),
        "node ID parity failed"
      )
      require(
        parsed("graph-edges").map(_(":ID")).toSet == sourceIds(graphEdges, "edgeId"),
        "graph edge ID parity failed"
      )
      require(
        parsed("coauthor-edges").map(_(":ID")).toSet == sourceIds(coauthors, "edgeId"),
        "coauthor ID parity failed"
      )
      val labels =
        nodes.select("nodeId", "label").collect().map(r => r.getString(0) -> r.getString(1)).toMap
      parsed("nodes").foreach(r =>
        require(r("label:String") == labels(r(":ID")), "source label changed")
      )
      val years = Vector(
        "firstCollaborationYear",
        "lastCollaborationYear",
        "windowStartYear",
        "windowEndYear"
      )
      val sourceYears = coauthors
        .select((Vector(col("edgeId")) ++ years.map(col))*)
        .collect()
        .map(r =>
          r.getString(0) -> years.indices
            .map(i => Option(r.get(i + 1)).map(_.toString).orNull)
            .toVector
        )
        .toMap
      parsed("coauthor-edges").foreach { row =>
        require(years.map(y => row(y + ":Int")) == sourceYears(row(":ID")), "year mapping changed")
        require(
          row("evidenceTable:String") == Phase7NeptuneExport.supportPath &&
            row("evidenceEdgeId:String") == row(":ID"),
          "support pointer changed"
        )
      }
      require(
        sidecar("supportTable")("keyColumns").arr.map(_.str).toVector == Vector("edgeId", "workId"),
        "support compound key changed"
      )
      sidecar("sourceTables").arr.foreach { binding =>
        val reread = spark.read.parquet(output.resolve(binding("path").str).toString)
        require(
          reread.count() == binding("rowCount").str.toLong &&
            Phase6Export.logicalTableHash(reread) == binding("contentHash").str,
          "sample source binding mismatch"
        )
      }
      bindingNames.foreach(n =>
        require(Files.readString(source.resolve(n), UTF_8) == before(n), "retained source modified")
      )
      val report = ujson.Obj(
        "scope" -> "bounded retained real-data sample; not a full analytics replay or live Neptune load",
        "sourceRoot" -> source.toString,
        "outputRoot" -> output.toString,
        "sourceRunId" -> runId,
        "limits" -> ujson.Obj(
          "maxCoauthors" -> maxCoauthors,
          "maxGraphEdges" -> maxGraphEdges,
          "maxRowsPerClosureTable" -> maxRows,
          "maxSupportPerSelectedEdge" -> perEdgeSupportBudget
        ),
        "counts" -> ujson.Obj(
          "nodes" -> nodes.count(),
          "graphEdges" -> graphEdges.count(),
          "coauthorEdges" -> coauthors.count(),
          "supportRows" -> support.count(),
          "communityMemberships" -> communities.count(),
          "unknownFirstYearEdges" -> coauthors.filter(col("firstCollaborationYear").isNull).count(),
          "unboundedStartEdges" -> coauthors.filter(col("windowStartYear").isNull).count(),
          "unboundedEndEdges" -> coauthors.filter(col("windowEndYear").isNull).count(),
          "unknownYearSupports" -> support.filter(col("year").isNull).count(),
          "labelsWithCsvSpecialCharacters" -> labels.values.count(v =>
            v.exists(c => ",\"\r\n".contains(c))
          )
        ),
        "checks" -> ujson.Arr(
          "completed source binding",
          "endpoint/support closure",
          "source ID parity both directions",
          "source labels and optional years unchanged",
          "typed CSV counts and logical hashes",
          "sample Parquet counts and hashes",
          "compound evidence keys",
          "source metadata/manifest/marker unchanged"
        ),
        "sourceBindingHashes" -> ujson.Obj.from(before.map { case (name, text) =>
          name -> ujson.Str(StableIds.sha256Hex(text))
        }),
        "sourceTables" -> ujson.Arr.from(sourceTables),
        "sampleTables" -> sidecar("sourceTables")
      )
      Files.writeString(output.resolve("replay-report.json"), report.render() + "\n", UTF_8)
      Files.writeString(
        output.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
        StableIds.sha256Hex(sampleRunJson + "\n" + sampleMetaJson) + "\n",
        UTF_8
      )
      println(report.render())
      println(
        "Bounded real-data CSV replay passed; no retained source writes, AWS/provider calls, or full-run claim."
      )
    } finally spark.stop()
  }
}

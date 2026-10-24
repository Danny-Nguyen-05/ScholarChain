package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.core.document.Document
import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.*
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import StorageResult.*

class NeptuneRepairSpec extends AnyFunSuite {
  private val run = "synthetic-repair-run"
  private val fingerprint = "a" * 64
  private val config = NeptuneLoaderConfig(
    "synthetic-bucket",
    "graph",
    "synthetic-region",
    "synthetic-role",
    pollIntervalMillis = 0,
    timeoutMillis = 100,
    maxPolls = 2,
    retry = RetryConfig(1, 0, 0)
  )
  private def documentStatus(state: String) = GetLoaderJobStatusResponse
    .builder()
    .payload(
      Document.fromMap(
        Map(
          "overallStatus" -> Document.fromMap(Map("status" -> Document.fromString(state)).asJava)
        ).asJava
      )
    )
    .build()
  private def stub(handler: PartialFunction[(String, Vector[AnyRef]), AnyRef]): NeptunedataClient =
    Proxy
      .newProxyInstance(
        classOf[NeptunedataClient].getClassLoader,
        Array(classOf[NeptunedataClient]),
        new InvocationHandler {
          def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = {
            val call = method.getName -> Option(args).map(_.toVector).getOrElse(Vector.empty);
            if (handler.isDefinedAt(call)) handler(call)
            else throw new AssertionError("unexpected SDK operation " + method.getName)
          }
        }
      )
      .asInstanceOf[NeptunedataClient]
  // Public validation is covered by independent Parquet/CSV tests. This package-private handle
  // exercises the identical load orchestration with a tiny already-validated synthetic upload.
  private def validated(root: Path): ValidatedNeptuneExport = {
    val scratch = Files.createTempDirectory("neptune-repair-handle-")
    Files.createDirectories(scratch.resolve("enriched-nodes"))
    Files.writeString(
      scratch.resolve("enriched-nodes/part-0.csv"),
      ":ID,:LABEL\r\nsynthetic,RESEARCHER\r\n",
      UTF_8
    )
    new ValidatedNeptuneExport(root, scratch, run, fingerprint, 1, 0, 0, Vector.empty, "support")
  }
  private def temporary(f: Path => Unit): Unit = {
    val root = Files.createTempDirectory("neptune-repair-");
    Files.createDirectory(root.resolve("support"));
    try f(root)
    finally ExportFiles.deleteTree(root)
  }
  private def loader(
      client: NeptunedataClient,
      objects: ObjectStore,
      ledger: RunLedger,
      registry: ArtifactRegistry
  ) = new NeptuneGraphLoader(
    client,
    objects,
    ledger,
    registry,
    config,
    new NeptuneExportValidator,
    sleep = _ => (),
    nowMillis = () => 0L
  )

  test("every non-pending non-success state terminates once and recovery appends NEW attempt") {
    Vector(
      "LOAD_FAILED",
      "LOAD_COMMITTED_W_WRITE_CONFLICTS",
      "LOAD_DATA_DEADLOCK",
      "UNRECOGNIZED_SYNTHETIC_STATE"
    ).foreach { failed =>
      temporary { root =>
        val starts = mutable.Buffer.empty[StartLoaderJobRequest];
        val polls = mutable.Buffer.empty[String]
        val client = stub {
          case ("startLoaderJob", Vector(request: StartLoaderJobRequest)) =>
            starts += request;
            StartLoaderJobResponse
              .builder()
              .payload(Map("loadId" -> ("job-" + starts.size)).asJava)
              .build()
          case ("getLoaderJobStatus", Vector(request: GetLoaderJobStatusRequest)) =>
            polls += request.loadId();
            documentStatus(if (request.loadId() == "job-1") failed else "LOAD_COMPLETED")
        }
        val objects = new InMemoryObjectStore; val ledger = new InMemoryRunLedger;
        val registry = new InMemoryArtifactRegistry
        val first = loader(client, objects, ledger, registry).loadValidated(validated(root))
        assert(first == Rejected("neptune-load-" + failed.toLowerCase(java.util.Locale.ROOT)))
        assert(polls.toVector == Vector("job-1"))
        val second = loader(client, objects, ledger, registry).loadValidated(validated(root))
        assert(second == Written(GraphLoadStatus("job-2", "LOAD_COMPLETED")))
        assert(starts.map(_.modeAsString()).toVector == Vector("AUTO", "NEW"))
        assert(polls.toVector == Vector("job-1", "job-2"))
        val record = StorageResult.value(ledger.getRun("neptune:" + run + ":" + fingerprint)).get
        assert(record.state == "complete")
        assert(
          record.failures == Vector(
            RunStage(
              "bulk-load",
              "failed",
              1,
              Some("neptune-load-" + failed.toLowerCase(java.util.Locale.ROOT))
            )
          )
        )
        assert(record.stages.head.retryCount == 1)
        val jobArtifact = "neptune-job:" + run + ":" + fingerprint
        assert(
          StorageResult
            .value(registry.get(jobArtifact, "attempt-00000000000000000001"))
            .get
            .uri == "job-1"
        )
        assert(
          StorageResult
            .value(registry.get(jobArtifact, "attempt-00000000000000000002"))
            .get
            .uri == "job-2"
        )
        assert(
          StorageResult
            .value(
              registry
                .get("neptune-failed:" + run + ":" + fingerprint, "attempt-00000000000000000001")
            )
            .get
            .uri == failed
        )
        val uploads = objects.writeOrder.toVector
        assert(
          loader(client, objects, ledger, registry).loadValidated(validated(root)) == Unchanged(
            GraphLoadStatus("job-2", "LOAD_COMPLETED")
          )
        )
        assert(starts.size == 2 && objects.writeOrder.toVector == uploads)
      }
    }
  }
  test("timeout keeps provider job active so rerun polls the same ID without submission") {
    temporary { root =>
      var starts = 0; var polls = 0
      val client = stub {
        case ("startLoaderJob", Vector(_: StartLoaderJobRequest)) =>
          starts += 1;
          StartLoaderJobResponse.builder().payload(Map("loadId" -> "pending-job").asJava).build()
        case ("getLoaderJobStatus", Vector(request: GetLoaderJobStatusRequest)) =>
          assert(request.loadId() == "pending-job"); polls += 1;
          documentStatus(if (polls <= 2) "LOAD_IN_PROGRESS" else "LOAD_COMPLETED")
      }
      val objects = new InMemoryObjectStore; val ledger = new InMemoryRunLedger;
      val registry = new InMemoryArtifactRegistry
      assert(
        loader(client, objects, ledger, registry).loadValidated(validated(root)) == Rejected(
          "neptune-load-timeout"
        )
      )
      assert(
        loader(client, objects, ledger, registry).loadValidated(validated(root)) == Written(
          GraphLoadStatus("pending-job", "LOAD_COMPLETED")
        )
      )
      assert(starts == 1 && polls == 3)
    }
  }
  test("legacy recorded failed job is marked and recovered without overwriting history") {
    temporary { root =>
      val registry = new InMemoryArtifactRegistry
      assert(
        StorageResult.successful(
          registry.register("neptune-job:" + run, fingerprint, "legacy-job", fingerprint)
        )
      )
      val starts = mutable.Buffer.empty[StartLoaderJobRequest];
      val polls = mutable.Buffer.empty[String]
      val client = stub {
        case ("startLoaderJob", Vector(request: StartLoaderJobRequest)) =>
          starts += request;
          StartLoaderJobResponse.builder().payload(Map("loadId" -> "recovery-job").asJava).build()
        case ("getLoaderJobStatus", Vector(request: GetLoaderJobStatusRequest)) =>
          polls += request.loadId();
          documentStatus(if (request.loadId() == "legacy-job") "LOAD_FAILED" else "LOAD_COMPLETED")
      }
      val objects = new InMemoryObjectStore; val ledger = new InMemoryRunLedger
      assert(
        loader(client, objects, ledger, registry).loadValidated(validated(root)) == Rejected(
          "neptune-load-load_failed"
        )
      )
      assert(starts.isEmpty)
      assert(
        loader(client, objects, ledger, registry).loadValidated(validated(root)) == Written(
          GraphLoadStatus("recovery-job", "LOAD_COMPLETED")
        )
      )
      assert(starts.size == 1 && starts.head.modeAsString() == "NEW")
      assert(polls.toVector == Vector("legacy-job", "recovery-job"))
      assert(
        StorageResult.value(registry.get("neptune-job:" + run, fingerprint)).get.uri == "legacy-job"
      )
      assert(
        StorageResult
          .value(registry.get("neptune-failed:" + run + ":" + fingerprint, "legacy"))
          .get
          .uri == "LOAD_FAILED"
      )
    }
  }
  test("only three explicitly pending states can consume the polling budget") {
    assert(
      NeptuneLoadStates.pending == Set("LOAD_NOT_STARTED", "LOAD_IN_QUEUE", "LOAD_IN_PROGRESS")
    )
    assert(
      NeptuneLoadStates
        .failureCode("unexpected\r\nsecret")
        .matches("neptune-load-unknown_[0-9a-f]{12}")
    )
  }
  test(
    "AWS Documents convert structurally with exact strings nested primitives and decimal values"
  ) {
    val text = "line1\r\nline2\t\"quoted\"\\path Ελληνικά 中文 😀"
    val nested = Document.fromMap(
      Map(
        "text" -> Document.fromString(text),
        "items" -> Document.fromList(
          Vector(
            Document.fromBoolean(true),
            Document.fromNull(),
            Document.fromNumber(7),
            Document.fromNumber(new java.math.BigDecimal("0.125"))
          ).asJava
        ),
        "large" -> Document.fromNumber("9007199254740993"),
        "precise" -> Document.fromNumber("0.12345678901234567890123456789")
      ).asJava
    )
    val result = AwsDocumentJson.value(nested)
    assert(result("text").str.getBytes(UTF_8).toVector == text.getBytes(UTF_8).toVector)
    assert(
      result("items").arr == Vector(
        AwsJson.BooleanValue(true),
        AwsJson.NullValue,
        AwsJson.NumberValue(new java.math.BigDecimal("7")),
        AwsJson.NumberValue(new java.math.BigDecimal("0.125"))
      )
    )
    assert(result("large") == AwsJson.NumberValue(new java.math.BigDecimal("9007199254740993")))
    assert(
      result("precise") == AwsJson.NumberValue(
        new java.math.BigDecimal("0.12345678901234567890123456789")
      )
    )
    assert(result("large").render == "9007199254740993")
    assert(result("precise").render == "0.12345678901234567890123456789")
    assert(AwsDocumentJson.value(Document.fromNull()) == AwsJson.NullValue)
  }
  test(
    "node labels and neighbor properties retain control characters quotes backslash and Unicode"
  ) {
    val text = "line1\r\nline2\t\"quoted\"\\path Ελληνικά 中文 😀"
    val runId = "run:00112233-4455-4677-8899-aabbccddeeff"
    val provenance = Provenance(
      SchemaVersions.domain,
      SourceType.Dblp,
      "synthetic-repair",
      None,
      "synthetic",
      None,
      None,
      runId,
      Vector("Synthetic module fixture")
    )
    val id = "researcher:dblp:" + "b" * 64
    val properties = Document.fromMap(
      Map(
        "schemaVersion" -> Document.fromString(SchemaVersions.domain),
        "label" -> Document.fromString(text),
        "propertiesJson" -> Document.fromString("[]"),
        "provenanceJson" -> Document.fromString(CoreJson.compact(provenance))
      ).asJava
    )
    val client = stub {
      case ("executeOpenCypherQuery", Vector(request: ExecuteOpenCypherQueryRequest)) =>
        val row =
          if (request.openCypherQuery().contains("labels(n)"))
            Document.fromMap(
              Map(
                "nodeId" -> Document.fromString(id),
                "labels" -> Document.fromList(Vector(Document.fromString("RESEARCHER")).asJava),
                "properties" -> properties
              ).asJava
            )
          else
            Document.fromMap(
              Map(
                "nodeId" -> Document.fromString(id),
                "edgeId" -> Document.fromString("synthetic-edge"),
                "edgeType" -> Document.fromString("COAUTHORED_WITH"),
                "properties" -> Document.fromMap(
                  Map(
                    "sourceText" -> Document.fromString(text),
                    "exactCount" -> Document.fromNumber("9007199254740993")
                  ).asJava
                )
              ).asJava
            )
        ExecuteOpenCypherQueryResponse
          .builder()
          .results(Document.fromList(Vector(row).asJava))
          .build()
    }
    val reader = new NeptuneGraphReader(client, GraphReaderConfig())
    assert(StorageResult.value(reader.node(id)).get.label == text)
    val neighbor = StorageResult.value(reader.directCoauthors(id, "all-years", 1)).get.items.head
    assert(neighbor.properties("sourceText") == text)
    assert(neighbor.properties("exactCount") == "9007199254740993")
  }
}

package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.core.document.Document
import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.{
  ExecuteOpenCypherQueryRequest,
  ExecuteOpenCypherQueryResponse
}
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.jdk.CollectionConverters.*

/** Offline SDK stubs only; this suite never calls the tagged live body or creates an AWS client. */
class AwsLiveGraphCleanupSpec extends AnyFunSuite {
  private val run = "run:00112233-4455-4677-8899-aabbccddeeff"
  private val nodes = Vector("a", "b", "c").map(s =>
    "researcher:dblp:" + StableIds.sha256Hex("synthetic-cleanup-" + s)
  )
  private val edge = "spark-coauthor-edge:" + "e" * 64
  private val endpoint = "https://synthetic.invalid:8182"
  private def settings(root: Path) = AwsLiveSettings(
    "synthetic",
    "synthetic-region",
    "synthetic-primary",
    "synthetic-reader",
    "synthetic-loader",
    "synthetic-cleanup",
    "synthetic-bucket",
    DynamoTables("runs", "links", "sessions", "evidence", "artifacts", "metrics", "idempotency"),
    "synthetic-vectors",
    "researcher-profile-v1",
    2,
    "cosine",
    endpoint,
    "synthetic-role",
    "synthetic-prefix",
    root,
    true,
    "synthetic-only-not-approval",
    5.0
  )
  private def withJournal(f: LiveRunManifest => Unit): Unit = {
    val root = Files.createTempDirectory("offline-cleanup-journal-")
    try {
      val journal = new LiveRunManifest(root, run, settings(root))
      (Vector(OwnedLiveItem("neptune-edge", endpoint, edge, expectedHash = run)) ++ nodes.map(id =>
        OwnedLiveItem("neptune-node", endpoint, id, expectedHash = run)
      )).foreach { item =>
        journal.plan(item); journal.record(item.copy(state = "created"))
      }
      f(journal)
    } finally ExportFiles.deleteTree(root)
  }
  private def stub(f: ExecuteOpenCypherQueryRequest => Document): NeptunedataClient = Proxy
    .newProxyInstance(
      classOf[NeptunedataClient].getClassLoader,
      Array(classOf[NeptunedataClient]),
      new InvocationHandler {
        def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = {
          assert(method.getName == "executeOpenCypherQuery", "unexpected SDK operation")
          ExecuteOpenCypherQueryResponse
            .builder()
            .results(f(args(0).asInstanceOf[ExecuteOpenCypherQueryRequest]))
            .build()
        }
      }
    )
    .asInstanceOf[NeptunedataClient]
  private def count(n: Document): Document =
    Document.fromList(Vector(Document.fromMap(Map("deleted" -> n).asJava)).asJava)
  private def empty: Document = Document.fromList(Vector.empty[Document].asJava)
  private def created(journal: LiveRunManifest): Unit = {
    assert(journal.all.forall(_.state == "created"))
    assert(
      ujson
        .read(Files.readString(journal.path, UTF_8))("items")
        .arr
        .forall(_("state").str == "created")
    )
  }
  private def writer(
      journal: LiveRunManifest,
      edgeCount: Document,
      nodeCount: Document,
      events: mutable.Buffer[String]
  ): NeptunedataClient = stub { request =>
    created(journal)
    val query = request.openCypherQuery(); val parameters = ujson.read(request.parameters())
    assert(query.contains("liveIntegrationRun = $run") && !query.contains("DETACH"))
    assert(
      query.endsWith("RETURN count(r) AS deleted") || query.endsWith("RETURN count(n) AS deleted")
    )
    assert(parameters("run").str == run)
    if (query.contains("DELETE r")) {
      assert(parameters("ids").arr.map(_.str).toVector == Vector(edge)); events += "delete-edge";
      count(edgeCount)
    } else {
      assert(parameters("ids").arr.map(_.str).toVector == nodes); events += "delete-nodes";
      count(nodeCount)
    }
  }
  private def readClient(
      journal: LiveRunManifest,
      events: mutable.Buffer[String],
      edgePresent: Boolean = false,
      nodePresent: Boolean = false,
      readFails: Boolean = false
  ): NeptunedataClient = stub { request =>
    created(journal)
    assert(!request.openCypherQuery().contains("DELETE"))
    if (readFails) throw new IllegalStateException("synthetic read failure")
    val id = ujson.read(request.parameters())("id").str
    if (request.openCypherQuery().contains("edgeId")) {
      assert(id == edge); events += "read-edge"
      if (edgePresent)
        Document.fromList(
          Vector(Document.fromMap(Map("edgeId" -> Document.fromString(edge)).asJava)).asJava
        )
      else empty
    } else {
      assert(nodes.contains(id)); events += "read-node"
      if (nodePresent) {
        val provenance = Provenance(
          SchemaVersions.domain,
          SourceType.ScholarChain,
          "synthetic-cleanup",
          None,
          "synthetic-fixture",
          None,
          None,
          run,
          Vector("Synthetic offline cleanup test")
        )
        val properties = Document.fromMap(
          Map(
            "schemaVersion" -> Document.fromString(SchemaVersions.domain),
            "label" -> Document.fromString("Synthetic remaining node"),
            "propertiesJson" -> Document.fromString("[]"),
            "provenanceJson" -> Document.fromString(CoreJson.compact(provenance))
          ).asJava
        )
        Document.fromList(
          Vector(
            Document.fromMap(
              Map(
                "nodeId" -> Document.fromString(id),
                "labels" -> Document.fromList(Vector(Document.fromString("RESEARCHER")).asJava),
                "properties" -> properties
              ).asJava
            )
          ).asJava
        )
      } else empty
    }
  }
  test("zero-matched edge or node DELETE never marks any graph item cleaned") {
    Vector((0, 3, Vector("delete-edge")), (1, 0, Vector("delete-edge", "delete-nodes"))).foreach {
      case (edgeCount, nodeCount, expected) =>
        withJournal { journal =>
          val events = mutable.Buffer.empty[String]
          val reads = readClient(journal, events)
          intercept[IllegalArgumentException](
            AwsLiveGraphCleanup.clean(
              writer(
                journal,
                Document.fromNumber(edgeCount),
                Document.fromNumber(nodeCount),
                events
              ),
              reads,
              new NeptuneGraphReader(reads, GraphReaderConfig()),
              run,
              journal
            )
          )
          assert(events.toVector == expected)
          created(journal)
        }
    }
  }
  test("mismatched or nonintegral numeric mutation counts are not successful cleanup") {
    Vector(Document.fromNumber(2), Document.fromNumber("1.5"), Document.fromString("1")).foreach {
      edgeCount =>
        withJournal { journal =>
          val events = mutable.Buffer.empty[String]; val reads = readClient(journal, events)
          intercept[Exception](
            AwsLiveGraphCleanup.clean(
              writer(journal, edgeCount, Document.fromNumber(3), events),
              reads,
              new NeptuneGraphReader(reads, GraphReaderConfig()),
              run,
              journal
            )
          )
          assert(events.toVector == Vector("delete-edge")); created(journal)
        }
    }
  }
  test("correct DELETE counts still require edge and node point reads to prove absence") {
    Vector((true, false), (false, true)).foreach { case (edgePresent, nodePresent) =>
      withJournal { journal =>
        val events = mutable.Buffer.empty[String];
        val reads = readClient(journal, events, edgePresent, nodePresent)
        intercept[IllegalArgumentException](
          AwsLiveGraphCleanup.clean(
            writer(journal, Document.fromNumber(1), Document.fromNumber(3), events),
            reads,
            new NeptuneGraphReader(reads, GraphReaderConfig()),
            run,
            journal
          )
        )
        assert(events.take(2).toVector == Vector("delete-edge", "delete-nodes"))
        assert(events.contains("read-edge")); if (nodePresent) assert(events.contains("read-node"))
        created(journal)
      }
    }
  }
  test("post-delete read failure retains created journal states for operator reconciliation") {
    withJournal { journal =>
      val events = mutable.Buffer.empty[String];
      val reads = readClient(journal, events, readFails = true)
      intercept[IllegalStateException](
        AwsLiveGraphCleanup.clean(
          writer(journal, Document.fromNumber(1), Document.fromNumber(3), events),
          reads,
          new NeptuneGraphReader(reads, GraphReaderConfig()),
          run,
          journal
        )
      )
      created(journal)
    }
  }
  test("exact mutation counts and independent absence checks precede every cleaned journal entry") {
    withJournal { journal =>
      val events = mutable.Buffer.empty[String]; val reads = readClient(journal, events)
      AwsLiveGraphCleanup.clean(
        writer(journal, Document.fromNumber(1), Document.fromNumber(3), events),
        reads,
        new NeptuneGraphReader(reads, GraphReaderConfig()),
        run,
        journal
      )
      assert(
        events.toVector == Vector(
          "delete-edge",
          "delete-nodes",
          "read-edge",
          "read-node",
          "read-node",
          "read-node"
        )
      )
      assert(journal.all.forall(_.state == "cleaned"))
      assert(
        ujson
          .read(Files.readString(journal.path, UTF_8))("items")
          .arr
          .forall(_("state").str == "cleaned")
      )
    }
  }
}

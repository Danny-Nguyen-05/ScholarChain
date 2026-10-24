package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient
import software.amazon.awssdk.services.bedrockruntime.model.{
  BedrockRuntimeException,
  InvokeModelRequest,
  InvokeModelResponse
}
import software.amazon.awssdk.core.SdkBytes
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable

/** Offline SDK stubs exercise the public adapter and runner; no client/credential construction. */
class IndependentEmbedding8BFailureSpec extends AnyFunSuite {
  import StorageResult.*
  private val model = EmbeddingModel("synthetic-offline-titan-shape", "v1", 256)
  private val config = EmbeddingIngestConfig("synthetic-failures", "graph", 256)
  private val document = new DocumentRenderer(RenderingConfig("test-v1", ChunkPolicy(1000, 0)))
    .render(
      RenderInput(
        "researcher-profile",
        "synthetic-person",
        "window",
        "source-run",
        Vector(
          SourceField(
            "title",
            "Synthetic profile",
            SummarySourceRef("synthetic-table", "row", "title")
          )
        )
      )
    )
    .toOption
    .get
    .head
  private def value[A](result: StorageResult[A]): A =
    StorageResult.value(result).getOrElse(fail(result.toString))
  private final class Ports {
    val objects = new InMemoryObjectStore()
    val vectors = new InMemoryVectorStore()
    val registry = new InMemoryArtifactRegistry()
    val ledger = new InMemoryRunLedger()
    assert(StorageResult.successful(vectors.ensureIndex("researcher-profile-v1", 256, "cosine")))
    def run(client: EmbeddingClient, execution: String, selectedModel: EmbeddingModel = model) =
      value(
        new EmbeddingManifestRunner(config, objects, vectors, registry, ledger, client)
          .run(
            EmbeddingManifest(Vector(EmbeddingManifests.item(document, selectedModel, config))),
            execution
          )
      )
  }
  private def response(dimension: Int = 256) = InvokeModelResponse
    .builder()
    .body(
      SdkBytes.fromUtf8String(
        ujson.Obj("embedding" -> ujson.Arr.from(Vector.fill(dimension)(1.0))).render()
      )
    )
    .build()

  test(
    "actual throttling retry succeeds and records exactly two calls one delay and one ledger retry"
  ) {
    var calls = 0
    val delays = mutable.Buffer.empty[Long]
    val sdk = IndependentStorage7BSupport.stub(classOf[BedrockRuntimeClient]) {
      case ("invokeModel", Vector(request: InvokeModelRequest)) =>
        calls += 1
        assert(request.modelId() == model.modelId)
        if (calls == 1)
          throw BedrockRuntimeException
            .builder()
            .statusCode(429)
            .message("synthetic throttling")
            .build()
        response()
    }
    val client = new BedrockEmbeddingClient(
      sdk,
      BedrockEmbeddingConfig(
        model,
        "us-east-2",
        maxConcurrentCalls = 1,
        maxAttempts = 2,
        baseDelayMillis = 5,
        maxDelayMillis = 5
      ),
      n => delays += n
    )
    val f = new Ports()
    val report = f.run(client, "retry-run")
    assert((report.written, report.retried, report.rejected, report.embeddingCalls) == (1, 1, 0, 2))
    assert(calls == 2 && delays.toVector == Vector(5L))
    assert(
      value(f.ledger.getRun("retry-run")).failures.map(_.detail) == Vector(Some("embedding-retry"))
    )
  }

  test(
    "permanent provider failure reaches the rejected object and ledger without exposing its message"
  ) {
    var calls = 0
    val sdk = IndependentStorage7BSupport.stub(classOf[BedrockRuntimeClient]) {
      case ("invokeModel", Vector(_: InvokeModelRequest)) =>
        calls += 1
        throw BedrockRuntimeException
          .builder()
          .statusCode(400)
          .message("SYNTHETIC-UNSAFE-PROVIDER-PAYLOAD")
          .build()
    }
    val client = new BedrockEmbeddingClient(
      sdk,
      BedrockEmbeddingConfig(model, "us-east-2", maxAttempts = 3),
      _ => fail("permanent failure must not sleep")
    )
    val f = new Ports()
    val report = f.run(client, "permanent-run")
    assert((report.written, report.rejected, report.embeddingCalls) == (0, 1, 1) && calls == 1)
    assert(report.rejections.map(_.reason) == Vector("embedding-provider-rejected"))
    val key = report.rejectedReportUri.get.stripPrefix("s3://synthetic-failures/")
    val body = new String(value(f.objects.get(key)).bytes.toArray, UTF_8)
    assert(
      body.contains("embedding-provider-rejected") && !body.contains(
        "SYNTHETIC-UNSAFE-PROVIDER-PAYLOAD"
      )
    )
    assert(
      value(f.ledger.getRun("permanent-run")).failures
        .exists(_.detail.contains("embedding-provider-rejected"))
    )
  }

  test(
    "wrong provider dimensions reject without vector publication and a stale manifest model never invokes the client"
  ) {
    var calls = 0
    val sdk = IndependentStorage7BSupport.stub(classOf[BedrockRuntimeClient]) {
      case ("invokeModel", Vector(_: InvokeModelRequest)) => calls += 1; response(255)
    }
    val f = new Ports()
    val client = new BedrockEmbeddingClient(sdk, BedrockEmbeddingConfig(model, "us-east-2"))
    val report = f.run(client, "bad-provider-dimension")
    assert(report.written == 0 && report.rejected == 1 && calls == 1)
    val key = EmbeddingManifests.item(document, model, config).vectorKey
    assert(value(f.vectors.get("researcher-profile-v1", Vector(key))).isEmpty)
    val stale = f.run(client, "stale-model", model.copy(version = "old-version"))
    assert(stale.written == 0 && stale.rejected == 1 && stale.embeddingCalls == 0)
    assert(calls == 1)
  }
}

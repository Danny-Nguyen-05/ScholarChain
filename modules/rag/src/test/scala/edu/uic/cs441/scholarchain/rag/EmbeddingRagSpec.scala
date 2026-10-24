package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.core.SdkBytes
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient
import software.amazon.awssdk.services.bedrockruntime.model.*
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.{Callable, CountDownLatch, Executors, TimeUnit}
import java.util.concurrent.atomic.AtomicInteger

class EmbeddingRagSpec extends AnyFunSuite {
  private val title = SummarySourceRef("synthetic-works", "fixture-work", "title")
  private val count = SummarySourceRef("synthetic-counts", "fixture-work", "publicationCount")
  private val fields =
    Vector(SourceField("title", "Synthetic graph", title), SourceField("papers", "7", count))
  private def input(kind: String = "paper") =
    RenderInput(kind, "fixture-entity", "fixture-window", "fixture-run", fields)
  private val rendering = RenderingConfig("template-v1", ChunkPolicy(1000, 0))
  private def rendered(i: RenderInput = input()): EmbeddingDocument =
    new DocumentRenderer(rendering).render(i).toOption.get.head
  private val model = EmbeddingModel("configured-titan-fixture", "version-1", 256)
  private def config =
    BedrockEmbeddingConfig(model, "fixture-region", baseDelayMillis = 2, maxDelayMillis = 8)
  private def sdk(handler: InvokeModelRequest => InvokeModelResponse): BedrockRuntimeClient =
    Proxy
      .newProxyInstance(
        classOf[BedrockRuntimeClient].getClassLoader,
        Array(classOf[BedrockRuntimeClient]),
        new InvocationHandler {
          def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef =
            method.getName match {
              case "invokeModel" => handler(args(0).asInstanceOf[InvokeModelRequest])
              case "serviceName" => "bedrock-fixture"
              case "close"       => null
              case other         => throw new UnsupportedOperationException(other)
            }
        }
      )
      .asInstanceOf[BedrockRuntimeClient]
  private def response(values: Vector[Double] = Vector.fill(256)(0.25)): InvokeModelResponse =
    InvokeModelResponse
      .builder()
      .body(SdkBytes.fromUtf8String(ujson.Obj("embedding" -> ujson.Arr.from(values)).render()))
      .build()
  private def providerError(status: Int) = BedrockRuntimeException
    .builder()
    .statusCode(status)
    .message("sensitive-provider-payload")
    .build()

  test(
    "all five templates copy exact source values and are byte deterministic across source ordering"
  ) {
    val headings = Map(
      "researcher-profile" -> "Researcher profile",
      "community" -> "Collaboration community",
      "paper" -> "Paper summary",
      "collaboration-path" -> "Collaboration path",
      "topic-institution-summary" -> "Topic and institution summary"
    )
    headings.foreach { (kind, header) =>
      val renderer = new DocumentRenderer(rendering)
      val first = renderer.render(input(kind)).toOption.get
      val second = renderer.render(input(kind).copy(fields = fields.reverse)).toOption.get
      assert(first == second)
      assert(
        first.head.text.getBytes(UTF_8).toVector ==
          (header + "\npapers: 7\ntitle: Synthetic graph").getBytes(UTF_8).toVector
      )
      assert(first.head.sourceReferences == Vector(count, title))
      assert(first.head.templateVersion == "template-v1")
    }
  }
  test(
    "abstract permission and source refs remain explicit; missing abstract uses paper fallback"
  ) {
    val renderer = new DocumentRenderer(rendering)
    val permission = SummarySourceRef("synthetic-licenses", "fixture-work", "usagePermission")
    val textRef = SummarySourceRef("synthetic-text", "fixture-work", "abstract")
    val permitted = PermittedAbstract("Source abstract.", textRef, permission)
    val doc = renderer.render(input(), Some(permitted)).toOption.get.head
    assert(doc.textSelection == "permitted-abstract")
    assert(
      doc.text == "Paper abstract\npapers: 7\ntitle: Synthetic graph\nabstract: Source abstract."
    )
    assert(doc.sourceReferences.toSet == Set(title, count, textRef, permission))
    assert(renderer.render(input()).toOption.get.head.textSelection == "paper-summary-fallback")
    assert(
      renderer
        .render(input(), Some(permitted.copy(text = " ")))
        .toOption
        .get
        .head
        .textSelection == "paper-summary-fallback"
    )
    assert(
      renderer
        .render(input(), Some(permitted.copy(permissionReference = permission.copy(field = ""))))
        .isLeft
    )
    assert(renderer.render(input("community"), Some(permitted)).isLeft)
  }
  test("chunking has hand-derived boundaries, exact overlap and Unicode codepoint safety") {
    assert(ChunkPolicy(6, 2).chunks("abcdefghij") == Right(Vector("abcdef", "efghij")))
    assert(ChunkPolicy(8, 0).chunks("one two three") == Right(Vector("one two ", "three")))
    assert(ChunkPolicy(4, 1).chunks("ab😀cd😀ef") == Right(Vector("ab😀c", "cd😀e", "ef")))
    assert(ChunkPolicy(4, 0, 1).chunks("abcde") == Left("chunk-count-limit"))
    assert(ChunkPolicy(4, 0).chunks(" ") == Left("empty-document-text"))
    intercept[IllegalArgumentException](ChunkPolicy(4, 4))
    val renderer = new DocumentRenderer(rendering.copy(maxDocumentCharacters = 4))
    assert(renderer.render(input()) == Left("document-character-limit"))
  }
  test("stable IDs bind text, window, template and chunk policy, preserving original entity IDs") {
    val first = rendered()
    assert(first.documentId.startsWith("chunk:"))
    assert(first.entityId == "fixture-entity")
    assert(rendered() == first)
    assert(
      new DocumentRenderer(rendering.copy(templateVersion = "template-v2"))
        .render(input())
        .toOption
        .get
        .head
        .documentId != first.documentId
    )
    assert(
      new DocumentRenderer(rendering.copy(chunkPolicy = ChunkPolicy(900, 0)))
        .render(input())
        .toOption
        .get
        .head
        .documentId != first.documentId
    )
    assert(rendered(input().copy(windowId = "other-window")).documentId != first.documentId)
  }
  test("rendering rejects unsupported labels, missing references and invented identity metadata") {
    val renderer = new DocumentRenderer(rendering)
    assert(renderer.render(input("unknown")).isLeft)
    assert(renderer.render(input().copy(fields = fields ++ fields)).isLeft)
    assert(
      renderer
        .render(input().copy(fields = Vector(SourceField("title", "x", title.copy(field = "")))))
        .isLeft
    )
    assert(renderer.render(input().copy(identityFields = Map("exactScore" -> "7"))).isLeft)
  }
  test("Phase6 summary rendering preserves actual source text qualifications and all source refs") {
    val lineage = SparkLineage(
      "synthetic-hadoop",
      "synthetic-snapshot",
      "synthetic-er",
      "policy-v1",
      "hash",
      Vector.empty,
      Vector.empty
    )
    val summary = SemanticSummary(
      SparkRecordContext("synthetic-schema", "synthetic-run", Some("window"), lineage),
      "synthetic-summary",
      "community",
      "synthetic-community",
      "policy-v1",
      "Approximate; did not converge.",
      Vector(title, count),
      Vector.empty
    )
    val result = new DocumentRenderer(rendering).fromSummary(summary).toOption.get.head
    assert(result.text == "Approximate; did not converge.")
    assert(result.sourceReferences.toSet == Set(title, count))
    assert(result.runId == "synthetic-run")
    assert(
      new DocumentRenderer(rendering)
        .fromSummary(summary.copy(context = summary.context.copy(windowId = None)))
        .isLeft
    )
  }
  test("stable vector slots reject actual rerendered changed text without re-embedding") {
    val renderer = new DocumentRenderer(rendering)
    val first = renderer.render(input()).toOption.get.head
    val changedInput =
      input().copy(fields = fields.map(f => if (f.name == "papers") f.copy(value = "8") else f))
    val changed = renderer.render(changedInput).toOption.get.head
    assert(first.documentId != changed.documentId && first.text != changed.text)
    assert(first.chunkOrdinal == 0 && changed.chunkOrdinal == 0)
    assert(first.chunkPolicyVersion == changed.chunkPolicyVersion)
    assert(
      EmbeddingContracts.vectorKey(first, model) == EmbeddingContracts.vectorKey(changed, model)
    )
    val ingest = EmbeddingIngestConfig("fixture-text", "rag", model.dimension)
    val vectors = new InMemoryVectorStore
    vectors.ensureIndex("paper-abstract-v1", model.dimension, "cosine")
    val runner = new EmbeddingManifestRunner(
      ingest,
      new InMemoryObjectStore,
      vectors,
      new InMemoryArtifactRegistry,
      new InMemoryRunLedger,
      new DeterministicHashedEmbeddingClient(model),
      logEvent = _ => ()
    )
    def run(doc: EmbeddingDocument, runId: String) = StorageResult
      .value(
        runner.run(EmbeddingManifest(Vector(EmbeddingManifests.item(doc, model, ingest))), runId)
      )
      .get
    assert(run(first, "fixture-first").written == 1)
    val conflict = run(changed, "fixture-changed")
    assert(
      conflict.vectorKeyTextConflict == 1 && conflict.written == 0 && conflict.embeddingCalls == 0
    )
    val unchanged = run(first, "fixture-unchanged")
    assert(unchanged.unchanged == 1 && unchanged.embeddingCalls == 0)
  }
  test(
    "slot keys bind chunk ordinal, model, template and policy while excluding text and source run"
  ) {
    val first = rendered()
    val key = EmbeddingContracts.vectorKey(first, model)
    assert(
      EmbeddingContracts.vectorKey(rendered(input().copy(runId = "other-source-run")), model) == key
    )
    assert(EmbeddingContracts.vectorKey(first, model.copy(version = "version-2")) != key)
    val newTemplate = new DocumentRenderer(rendering.copy(templateVersion = "template-v2"))
      .render(input())
      .toOption
      .get
      .head
    val newPolicy = new DocumentRenderer(rendering.copy(chunkPolicy = ChunkPolicy(900, 0)))
      .render(input())
      .toOption
      .get
      .head
    assert(EmbeddingContracts.vectorKey(newTemplate, model) != key)
    assert(EmbeddingContracts.vectorKey(newPolicy, model) != key)
    val chunks = new DocumentRenderer(rendering.copy(chunkPolicy = ChunkPolicy(16, 2)))
      .render(input())
      .toOption
      .get
    assert(chunks.size > 1 && chunks.map(_.chunkOrdinal) == chunks.indices.toVector)
    assert(chunks.map(d => EmbeddingContracts.vectorKey(d, model)).distinct.size == chunks.size)
  }
  test(
    "Phase6 summaries preserve Unicode and newline bytes and supplied filters through vector metadata"
  ) {
    val lineage = SparkLineage(
      "fixture-hadoop",
      "fixture-snapshot",
      "fixture-er",
      "policy-v1",
      "hash",
      Vector.empty,
      Vector.empty
    )
    val sourceText = "Qualified 😀 profile.\r\nCount is 7.\nApproximate; did not converge.\n"
    val summary = SemanticSummary(
      SparkRecordContext("synthetic-schema", "source-run", Some("window"), lineage),
      "summary-id",
      "researcher-profile",
      "fixture-researcher",
      "policy-v1",
      sourceText,
      Vector(title, count),
      Vector.empty
    )
    val identities = Map(
      "researcherId" -> "fixture-researcher",
      "communityId" -> "fixture-community",
      "topicId" -> "fixture-topic",
      "institutionId" -> "fixture-institution",
      "sourceDataset" -> "fixture-source"
    )
    val renderer = new DocumentRenderer(rendering)
    val doc = renderer.fromSummary(summary, identityFields = identities).toOption.get.head
    assert(doc.text.getBytes(UTF_8).toVector == sourceText.getBytes(UTF_8).toVector)
    assert(doc.sourceReferences.toSet == Set(title, count) && doc.identityFields == identities)
    val ingest = EmbeddingIngestConfig("fixture-text", "rag", model.dimension)
    val vectors = new InMemoryVectorStore
    vectors.ensureIndex("researcher-profile-v1", model.dimension, "cosine")
    val item = EmbeddingManifests.item(doc, model, ingest)
    val runner = new EmbeddingManifestRunner(
      ingest,
      new InMemoryObjectStore,
      vectors,
      new InMemoryArtifactRegistry,
      new InMemoryRunLedger,
      new DeterministicHashedEmbeddingClient(model),
      logEvent = _ => ()
    )
    assert(
      StorageResult
        .value(runner.run(EmbeddingManifest(Vector(item)), "fixture-ingest"))
        .get
        .written == 1
    )
    val metadata =
      StorageResult.value(vectors.get(item.indexName, Vector(item.vectorKey))).get.head.metadata
    identities.foreach { (name, value) => assert(metadata(name) == value) }
    assert(metadata("documentId") == doc.documentId)
    assert(
      metadata("chunkPolicyVersion") == doc.chunkPolicyVersion && metadata("chunkOrdinal") == "0"
    )
    assert(renderer.fromSummary(summary, identityFields = Map("inventedField" -> "7")).isLeft)
    assert(renderer.fromSummary(summary, identityFields = Map("topicId" -> ("x" * 257))).isLeft)
  }
  test(
    "explicit summary abstract composition preserves the exact summary prefix and actual permission evidence"
  ) {
    val lineage = SparkLineage(
      "fixture-hadoop",
      "fixture-snapshot",
      "fixture-er",
      "policy-v1",
      "hash",
      Vector.empty,
      Vector.empty
    )
    val summary = SemanticSummary(
      SparkRecordContext("synthetic-schema", "source-run", Some("window"), lineage),
      "summary-id",
      "paper",
      "fixture-work",
      "policy-v1",
      "Qualified source.\r\n",
      Vector(title, count),
      Vector.empty
    )
    val textRef = SummarySourceRef("fixture-text", "fixture-work", "abstract")
    val permissionRef = SummarySourceRef("fixture-permission", "fixture-work", "permission")
    val permitted = PermittedAbstract("Exact 😀 abstract.\n", textRef, permissionRef)
    val renderer = new DocumentRenderer(rendering)
    val doc = renderer.fromSummary(summary, Some(permitted)).toOption.get.head
    assert(doc.text == summary.text + "\n" + permitted.text)
    assert(doc.sourceReferences.toSet == Set(title, count, textRef, permissionRef))
    assert(doc.textSelection == "permitted-abstract")
    val blank = renderer.fromSummary(summary, Some(permitted.copy(text = " "))).toOption.get.head
    assert(blank.text == summary.text && blank.textSelection == "paper-summary-fallback")
    assert(
      renderer
        .fromSummary(
          summary,
          Some(permitted.copy(permissionReference = permissionRef.copy(field = "")))
        )
        .isLeft
    )
    assert(renderer.fromSummary(summary.copy(summaryType = "community"), Some(permitted)).isLeft)
  }
  test(
    "hashed bag of words is case/order invariant, normalized and has deterministic lexical neighbors"
  ) {
    val fake = new DeterministicHashedEmbeddingClient(EmbeddingModel("fixture-hashed", "v1", 256))
    val results =
      fake.embed(Seq("graph graph paper", "PAPER graph GRAPH", "institution physics", ""))
    val first = results.head.asInstanceOf[EmbeddingSuccess]
    assert(first == results(1))
    assert(math.abs(first.values.map(v => v.toDouble * v).sum - 1.0) < 0.000001)
    val other = results(2).asInstanceOf[EmbeddingSuccess]
    val sameScore = first.values.zip(first.values).map((a, b) => a.toDouble * b).sum
    val otherScore = first.values.zip(other.values).map((a, b) => a.toDouble * b).sum
    assert(sameScore > otherScore)
    assert(results(3) == EmbeddingFailure("empty-embedding-tokens", false, fake.model, 0))
  }
  test(
    "Bedrock request uses configured identity/dimension and bounded timeout without credential construction"
  ) {
    var requests = Vector.empty[InvokeModelRequest]
    val client = new BedrockEmbeddingClient(
      sdk { request =>
        requests :+= request; response()
      },
      config,
      _ => ()
    )
    val output = client.embed(Seq("fixture text"))
    assert(output == Seq(EmbeddingSuccess(Vector.fill(256)(0.25f), model, 1)))
    assert(requests.size == 1 && requests.head.modelId() == model.modelId)
    assert(
      requests.head.contentType() == "application/json" && requests.head
        .accept() == "application/json"
    )
    assert(
      ujson.read(requests.head.body().asUtf8String()) ==
        ujson.Obj("inputText" -> "fixture text", "dimensions" -> 256, "normalize" -> true)
    )
    assert(
      requests.head
        .overrideConfiguration()
        .get()
        .apiCallTimeout()
        .get()
        .toMillis == config.requestTimeoutMillis
    )
  }
  test("transient provider failures retry with bounded backoff and preserve observed attempts") {
    val calls = new AtomicInteger()
    var sleeps = Vector.empty[Long]
    val client = new BedrockEmbeddingClient(
      sdk { _ => if (calls.incrementAndGet() < 3) throw providerError(429) else response() },
      config,
      delay => sleeps :+= delay
    )
    assert(client.embed(Seq("fixture")).head == EmbeddingSuccess(Vector.fill(256)(0.25f), model, 3))
    assert(calls.get() == 3 && sleeps == Vector(2L, 4L))
  }
  test("permanent/exhausted failures are typed and never expose provider details") {
    val permanentCalls = new AtomicInteger()
    val permanent = new BedrockEmbeddingClient(
      sdk { _ =>
        permanentCalls.incrementAndGet(); throw providerError(400)
      },
      config,
      _ => ()
    )
    val result = permanent.embed(Seq("fixture")).head
    assert(result == EmbeddingFailure("embedding-provider-rejected", false, model, 1))
    assert(
      permanentCalls
        .get() == 1 && !upickle.default.write(result).contains("sensitive-provider-payload")
    )
    val exhaustedCalls = new AtomicInteger()
    val exhausted = new BedrockEmbeddingClient(
      sdk { _ =>
        exhaustedCalls.incrementAndGet(); throw providerError(503)
      },
      config,
      _ => ()
    )
    assert(
      exhausted.embed(Seq("fixture")).head == EmbeddingFailure(
        "embedding-retries-exhausted",
        true,
        model,
        3
      )
    )
    assert(exhaustedCalls.get() == 3)
  }
  test(
    "dimension/malformed-response errors fail permanently; empty/oversized text never invokes SDK"
  ) {
    val count = new AtomicInteger()
    val client = new BedrockEmbeddingClient(
      sdk { _ =>
        count.incrementAndGet(); response(Vector(0.5))
      },
      config,
      _ => ()
    )
    assert(
      client.embed(Seq("fixture")).head == EmbeddingFailure(
        "embedding-dimension-or-value-mismatch",
        false,
        model,
        1
      )
    )
    assert(client.embed(Seq("", "x" * 8193)).forall(_.isInstanceOf[EmbeddingFailure]))
    assert(count.get() == 1)
    val invalid = new BedrockEmbeddingClient(
      sdk(_ => InvokeModelResponse.builder().body(SdkBytes.fromUtf8String("{}")).build()),
      config,
      _ => ()
    )
    assert(
      invalid.embed(Seq("fixture")).head == EmbeddingFailure(
        "embedding-invalid-response",
        false,
        model,
        1
      )
    )
  }
  test(
    "concurrency remains bounded and output follows input ordering across independent invocations"
  ) {
    val active = new AtomicInteger()
    val maximum = new AtomicInteger()
    val barrier = new CountDownLatch(2)
    val client = new BedrockEmbeddingClient(
      sdk { request =>
        val current = active.incrementAndGet()
        maximum.accumulateAndGet(current, (a, b) => math.max(a, b))
        barrier.countDown()
        assert(barrier.await(5, TimeUnit.SECONDS))
        val text = ujson.read(request.body().asUtf8String())("inputText").str
        try response(Vector.fill(256)(text.toDouble))
        finally active.decrementAndGet()
      },
      config.copy(maxConcurrentCalls = 2),
      _ => ()
    )
    val callers = Executors.newFixedThreadPool(2)
    try {
      val a = callers.submit(new Callable[Seq[EmbeddingResult]] {
        def call() = client.embed(Seq("1", "2"))
      })
      val b = callers.submit(new Callable[Seq[EmbeddingResult]] {
        def call() = client.embed(Seq("3", "4"))
      })
      assert(
        a.get(10, TimeUnit.SECONDS).map(_.asInstanceOf[EmbeddingSuccess].values.head) == Seq(1f, 2f)
      )
      assert(
        b.get(10, TimeUnit.SECONDS).map(_.asInstanceOf[EmbeddingSuccess].values.head) == Seq(3f, 4f)
      )
      assert(maximum.get() == 2 && active.get() == 0)
    } finally callers.shutdownNow()
  }
  test("semantic excerpt limit counts Unicode codepoints consistently with core validation") {
    val text = "A😀BC"
    val original = rendered()
    val doc = original.copy(
      text = text,
      documentId = StableIds
        .chunkOrProfileId(
          original.entityId,
          "synthetic-emoji",
          original.documentType,
          Some(0),
          text
        )
        .toOption
        .get
    )
    val metadata = EmbeddingVectorMetadata(
      doc.documentType,
      doc.entityId,
      doc.windowId,
      doc.runId,
      "s3://fixture-text/text/emoji.json",
      EmbeddingContracts.textHash(doc.text),
      model,
      doc.templateVersion,
      doc.documentId,
      chunkPolicyVersion = doc.chunkPolicyVersion,
      chunkOrdinal = doc.chunkOrdinal
    ).compact
    val hit = VectorHit(EmbeddingContracts.vectorKey(doc, model), 0.0, metadata)
    val item = SemanticContexts.fromVerifiedText(hit, doc, 3).toOption.get
    assert(item.excerpt == "A😀B")
    assert(EmbeddingValidation.context(SemanticContext(Vector(item)), 3).isEmpty)
  }
  test(
    "semantic context follows ordinary-S3 envelope, hash and pointer, excluding metric authority"
  ) {
    val doc = rendered()
    val key = EmbeddingContracts.vectorKey(doc, model)
    val metadata = EmbeddingVectorMetadata(
      doc.documentType,
      doc.entityId,
      doc.windowId,
      doc.runId,
      "s3://fixture-text/text/document.json",
      EmbeddingContracts.textHash(doc.text),
      model,
      doc.templateVersion,
      doc.documentId,
      chunkPolicyVersion = doc.chunkPolicyVersion,
      chunkOrdinal = doc.chunkOrdinal
    ).compact
    val hit = VectorHit(key, 0.25, metadata)
    val bytes = EmbeddingManifests.textJson(doc).getBytes(UTF_8).toVector
    val stored = StoredObject(
      ObjectHead(
        "text/document.json",
        StorageKeys.sha256(bytes),
        bytes.size,
        "application/json",
        Map.empty
      ),
      bytes
    )
    val item = SemanticContexts.fromStoredObject(hit, stored, 12).toOption.get
    assert(
      item.excerpt == "Paper summar" && item.score == -0.25 && item.textS3Uri == metadata(
        "textS3Uri"
      )
    )
    val context = SemanticContext(Vector(item))
    assert(!context.exactMetricsAllowed && !context.graphClaimsAllowed)
    assert(context.usage == EmbeddingContracts.descriptiveOnly)
    assert(
      SemanticContexts
        .fromStoredObject(hit.copy(metadata = metadata.updated("textHash", "0" * 64)), stored)
        .isLeft
    )
    assert(
      SemanticContexts
        .fromStoredObject(
          hit.copy(metadata = metadata.updated("textS3Uri", "s3://fixture-text/other.json")),
          stored
        )
        .isLeft
    )
    assert(SemanticContexts.fromStoredObject(hit, stored.copy(bytes = bytes :+ 0.toByte)).isLeft)
    assert(SemanticContexts.fromVerifiedText(hit.copy(key = "wrong-key"), doc).isLeft)
    assert(
      SemanticContexts
        .fromVerifiedText(hit.copy(metadata = metadata.updated("chunkOrdinal", "1")), doc)
        .isLeft
    )
    assert(
      SemanticContexts
        .fromVerifiedText(
          hit.copy(metadata = metadata.updated("chunkPolicyVersion", "other-policy")),
          doc
        )
        .isLeft
    )
  }
}

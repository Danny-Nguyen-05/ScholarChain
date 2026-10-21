package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

/** Synthetic provider and approval fixtures only; no credentials, network or real labels. */
class LiveDemoExportSpec extends AnyFunSuite {
  private def value[A](r: Either[String, A]): A = r.fold(e => fail(e), identity)
  test("credential preflight captures once and uses the complete JDK header character set") {
    var reads = 0
    var supplied = Option("synthetic-owner-credential-DO-NOT-LOG")
    val transport = new OpenAIHttpTransport(() => { reads += 1; supplied })
    assert(reads == 0)
    val prepared = value(transport.prepare())
    assert(reads == 1)
    supplied = None
    assert(prepared.prepare().contains(prepared) && reads == 1)
    assert(!prepared.toString.contains("DO-NOT-LOG"))
    // Preflight builds a local header only. No test calls post or performs HTTP.
    (0 to 256).foreach { n =>
      val result =
        new OpenAIHttpTransport(() => Some("synthetic-" + n.toChar + "-credential")).prepare()
      val allowed = n == 9 || (n >= 32 && n <= 126) || (n >= 128 && n <= 255)
      assert(result.isRight == allowed, s"unexpected header character classification: $n")
      result.left.foreach(e => assert(e == "LIVE_CREDENTIAL_UNAVAILABLE_OR_INVALID"))
    }
  }
  test("explicit default response limits roundtrip strictly and metadata fails before dispatch") {
    val text = ResourceText.read("adjudication/openai-live.example.v1.json")
    val config = value(StrictJson.parse[LiveProviderConfig](text))
    assert(StrictJson.parse[LiveProviderConfig](write(config)).contains(config))
    val extra = ujson.read(text)
    extra("responseLimits")("unsupported") = true
    assert(StrictJson.parse[LiveProviderConfig](extra.render()).isLeft)
    val options = Vector(
      "--input",
      "--frozen-input",
      "--queue",
      "--split",
      "--policy",
      "--config",
      "--live-config",
      "--scope",
      "--code-revision",
      "--source-hash",
      "--output",
      "--runtime-binding",
      "--approval",
      "--enable-live"
    )
    val args = Array("adjudicate-demo") ++ options.flatMap(k => Vector(k, "INVALID-NOT-A-PATH"))
    assert(LiveDemoCommands.run(args).left.exists(_.contains("before live dispatch")))
  }
  private def setup = {
    val works = (0 until 2).toVector.flatMap(i =>
      Vector(
        ErTestData.work(s"conf/live/export/${i}L", title = s"alpha beta $i", names = Vector.empty),
        ErTestData.work(s"conf/live/export/${i}R", title = s"alpha gamma $i", names = Vector.empty)
      )
    )
    val input = value(ResolutionInput.create(works, Vector.empty, Vector.empty, Vector.empty))
    val pairs = works
      .grouped(2)
      .map { ws =>
        val pair = ResolutionIds
          .pair(ResolutionEntityType.Work, ErTestData.endpoint(ws.head), ErTestData.endpoint(ws(1)))
          .toOption
          .get
        DerivedPair(
          pair,
          Vector.empty,
          (input.refs(pair.left) ++ input.refs(pair.right)).distinct.sorted
        )
      }
      .toVector
    val population = CandidatePopulation(pairs, Vector.empty, Vector.empty)
    val source = ResolutionConfig.example
    val base = ResolutionPolicy.example
    val policy = base.copy(work =
      base.work.copy(
        weights = Map("title" -> 1.0, "yearCompatibility" -> 1.0),
        featureGroups = Map("title" -> "bibliography", "yearCompatibility" -> "chronology"),
        requiredGroups = Vector("bibliography", "chronology"),
        minimumIndependentGroupsForAccept = 2,
        supportiveFeatureMin = 0.3,
        rejectThreshold = 0.5,
        acceptThreshold = 0.9,
        llmBandMin = 0.6,
        llmBandMax = 0.8
      )
    )
    val live = value(
      StrictJson.parse[LiveProviderConfig](
        ResourceText.read("adjudication/openai-live.example.v1.json")
      )
    ).copy(approved = true, approvalId = "synthetic-owner-only")
    val binding = ReviewBinding(
      input.inputEvidenceHash,
      ReviewQueue.populationHash(population),
      policy.fingerprint,
      source.fingerprint,
      "a" * 64,
      "b" * 64,
      "fake/no-provider",
      "c" * 40,
      "d" * 64
    )
    val artifacts = value(
      ReviewQueue.build(
        input,
        population,
        ReviewSampling.standard
          .copy(development = 1, heldOut = 1, developmentReserve = 0, heldOutReserve = 0),
        binding
      )
    )
    (input, population, source, policy, live, artifacts)
  }
  test(
    "live demo export binds typed accepted links complete source constraints and all published files"
  ) {
    val (input, population, source, policy, live, artifacts) = setup
    val root = Files.createTempDirectory("scholarchain-live-export-owner-").toRealPath()
    var calls = 0
    val run = value(
      LiveDemo.run(
        input,
        population,
        input,
        artifacts.queue,
        artifacts.split,
        policy,
        source,
        live,
        root.resolve("budget.json"),
        None,
        ErTestData.run,
        true,
        live.approvalId,
        () =>
          new OpenAITransport {
            def post(body: String, timeoutMs: Int, maxResponseBytes: Int): ProviderHttpResponse = {
              calls += 1
              val request =
                value(StrictJson.parse[AdjudicationRequest](ujson.read(body)("input").str))
              val answer = AdjudicationResponse(
                Adjudication.responseSchema,
                request.requestHash,
                request.pairId,
                request.sourceId,
                request.targetId,
                request.inputEvidenceHash,
                request.policyHash,
                "accept",
                Vector("SUPPORTED_SAME_IDENTITY"),
                request.evidence.map(_.ref),
                "Synthetic owner provider fixture only.",
                0.7,
                Vector(request.evidence.head.ref + "#/title")
              )
              val envelope = ujson.Obj(
                "id" -> "resp_synthetic_owner",
                "model" -> "gpt-6-luna",
                "status" -> "completed",
                "output" -> ujson.Arr(
                  ujson.Obj(
                    "type" -> "message",
                    "content" -> ujson.Arr(
                      ujson.Obj("type" -> "output_text", "text" -> write(answer))
                    )
                  )
                ),
                "usage" -> ujson.Obj(
                  "input_tokens" -> 120,
                  "output_tokens" -> 40,
                  "total_tokens" -> 160,
                  "input_tokens_details" -> ujson.Obj("cached_tokens" -> 0),
                  "output_tokens_details" -> ujson.Obj("reasoning_tokens" -> 10)
                )
              )
              ProviderHttpResponse(200, envelope.render(), Some("req_synthetic_owner"))
            }
          }
      )
    )
    assert(calls == 1 && run.decisions.size == 1 && run.links.size == 1)
    val decision = run.decisions.head
    assert(decision.adjudication.exists(_.mode == ResolutionAdjudicationMode.Live))
    assert(ResolutionValidation.check(run.links.head, decision, input.context).isRight)
    assert(run.constraints.flatMap(_.coveredEndpoints).toSet == input.endpoints.toSet)
    val output = root.resolve("export")
    val manifest =
      value(LiveDemoExporter.writeNew(output, run, input, policy, source, live, "c" * 40, "d" * 64))
    assert(manifest.scope.startsWith("DEVELOPMENT_DEMO_ONLY") && manifest.liveAttemptsThisRun == 1)
    assert(
      Files.readString(output.resolve("_SCHOLARCHAIN_LIVE_DEMO_COMPLETE")) == StableIds.sha256Hex(
        Files.readString(output.resolve("live-demo-manifest.json"))
      ) + "\n"
    )
    manifest.files.foreach { file =>
      val bytes = Files.readAllBytes(output.resolve(file.path))
      assert(
        bytes.length.toLong == file.bytes && StableIds.sha256Hex(
          new String(bytes, java.nio.charset.StandardCharsets.UTF_8)
        ) == file.sha256
      )
    }
    assert(
      LiveDemoExporter.writeNew(output, run, input, policy, source, live, "c" * 40, "d" * 64).isLeft
    )
  }
  test("runtime binding refuses changed receipt paths and limits beyond the recorded approval") {
    val (_, _, _, _, live, _) = setup
    val root = Files.createTempDirectory("scholarchain-live-binding-owner-").toRealPath()
    Files.writeString(root.resolve("AGENTS.md"), "Synthetic test root only")
    Files.createDirectories(root.resolve("modules/entity-resolution"))
    val text =
      """{"schemaVersion":"scholarchain.phase5d-user-live-approval.v1","scope":{"status":"USER_APPROVED_NUMERICAL_LIMITS","provider":"openai","model":"gpt-6-luna","api":"https://api.openai.com/v1/responses","serviceTier":"default","reasoningEffort":"medium","credentialVariableName":"OPENAI_API_KEY","maxTotalAttemptsIncludingRetries":10,"maxRetriesPerPair":1,"maxConcurrentCalls":1,"maxInputTokensTotal":1000000,"maxOutputTokensTotal":40960,"maxOutputTokensPerAttempt":4096,"maxTimeoutMsPerAttempt":60000,"maxSpendUsd":"1.00"}}"""
    val receipt = root.resolve("synthetic-approval.json"); Files.writeString(receipt, text)
    val hash = StableIds.sha256Hex(text); val approvalId = "approval-" + hash.take(12)
    val config = live.copy(approvalId = approvalId)
    val state = root.resolve("docs/agent-runs/phase-05/evidence/5d/live-state").resolve(approvalId)
    val binding = LiveRuntimeBinding(
      "scholarchain.live-runtime-binding.v1",
      approvalId,
      hash,
      state.resolve("budget.json").toString,
      state.resolve("cache").toString,
      config.fingerprint
    )
    assert(LiveRuntimeBinding.verify(binding, receipt, config, root).isRight)
    assert(
      LiveRuntimeBinding
        .verify(
          binding.copy(absoluteLedgerPath = root.resolve("other-budget.json").toString),
          receipt,
          config,
          root
        )
        .isLeft
    )
    Files.writeString(receipt, text + "\n")
    assert(LiveRuntimeBinding.verify(binding, receipt, config, root).isLeft)
    Files.writeString(receipt, text)
    val excessive = config.copy(budget = config.budget.copy(maxAttempts = 11))
    assert(
      LiveRuntimeBinding
        .verify(binding.copy(configHash = excessive.fingerprint), receipt, excessive, root)
        .isLeft
    )
  }
}

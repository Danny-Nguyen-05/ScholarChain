package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardOpenOption}
import java.util.UUID
import scala.util.Try
import upickle.default.{ReadWriter, write}

final case class LiveRuntimeBinding(
    schemaVersion: String,
    approvalId: String,
    approvalReceiptSha256: String,
    absoluteLedgerPath: String,
    absoluteCachePath: String,
    configHash: String
) derives ReadWriter
final case class LiveDemoManifest(
    schemaVersion: String,
    scope: String,
    complete: Boolean,
    inputEvidenceHash: String,
    candidatePopulationHash: String,
    frozenInputHash: String,
    queueHash: String,
    splitHash: String,
    policyHash: String,
    sourceConfigHash: String,
    liveConfigHash: String,
    effectiveConfigHash: String,
    promptHash: String,
    responseSchemaHash: String,
    selectedModel: String,
    providerReportedModels: Vector[String],
    codeRevision: String,
    sourceTreeHash: String,
    createdAtUtc: String,
    eligiblePairs: Int,
    liveAttemptsThisRun: Int,
    cacheHitsThisRun: Int,
    files: Vector[ResolutionExportFile]
) derives ReadWriter

object LiveRuntimeBinding {
  def verify(
      binding: LiveRuntimeBinding,
      approval: Path,
      config: LiveProviderConfig,
      repository: Path
  ): Either[String, Unit] = Try {
    LiveProviderConfig
      .validate(config, requireApproval = true)
      .fold(e => throw new IllegalArgumentException(e), identity)
    val text =
      StrictJson.file(approval, 1048576).fold(e => throw new IllegalArgumentException(e), identity)
    val hash = StableIds.sha256Hex(text)
    require(
      binding.schemaVersion == "scholarchain.live-runtime-binding.v1" && binding.approvalReceiptSha256 == hash && binding.approvalId == "approval-" + hash
        .take(
          12
        ) && binding.approvalId == config.approvalId && binding.configHash == config.fingerprint,
      "live approval receipt/config binding mismatch"
    )
    val root = repository.toRealPath()
    require(
      Files.isRegularFile(root.resolve("AGENTS.md")) && Files.isDirectory(
        root.resolve("modules/entity-resolution")
      ),
      "run live demo from the ScholarChain repository root"
    )
    val state =
      root.resolve("docs/agent-runs/phase-05/evidence/5d/live-state").resolve(binding.approvalId)
    require(
      Path.of(binding.absoluteLedgerPath).isAbsolute && Path
        .of(binding.absoluteCachePath)
        .isAbsolute && Path.of(binding.absoluteLedgerPath).normalize == state.resolve(
        "budget.json"
      ) && Path.of(binding.absoluteCachePath).normalize == state.resolve("cache"),
      "live budget/cache paths must be canonical approval-scoped state paths"
    )
    val receipt = StrictJson
      .parse[ujson.Value](text)
      .fold(_ => throw new IllegalArgumentException("invalid live approval receipt"), identity)
    require(
      receipt("schemaVersion").str == "scholarchain.phase5d-user-live-approval.v1",
      "unsupported approval receipt"
    )
    val scope = receipt("scope"); val b = config.budget
    require(
      scope("status").str == "USER_APPROVED_NUMERICAL_LIMITS" && scope(
        "provider"
      ).str == config.provider && scope("model").str == config.model && scope(
        "api"
      ).str == OpenAIResponses.endpoint && scope("serviceTier").str == "default" && scope(
        "reasoningEffort"
      ).str == config.reasoningEffort && scope(
        "credentialVariableName"
      ).str == config.apiKeyEnvironment,
      "selected live provider/settings differ from recorded human approval"
    )
    require(
      b.maxAttempts <= scope("maxTotalAttemptsIncludingRetries").num && b.maxRetries <= scope(
        "maxRetriesPerPair"
      ).num && b.maxConcurrentCalls == scope("maxConcurrentCalls").num && b.maxInputTokens <= scope(
        "maxInputTokensTotal"
      ).num && b.maxOutputTokens <= scope(
        "maxOutputTokensTotal"
      ).num && b.maxOutputTokensPerCall <= scope(
        "maxOutputTokensPerAttempt"
      ).num && b.timeoutMs <= scope("maxTimeoutMsPerAttempt").num && BigDecimal(
        b.maxSpendMicrousd
      ) <= BigDecimal(scope("maxSpendUsd").str) * 1000000,
      "configured live limits exceed recorded human approval"
    )
    ()
  }.toEither.left.map(_ => "LIVE_APPROVAL_OR_CANONICAL_STATE_BINDING_INVALID")
}

object LiveDemoExporter {
  def writeNew(
      output: Path,
      run: LiveDemoRun,
      input: ResolutionInput,
      policy: ResolutionPolicy,
      source: ResolutionConfig,
      live: LiveProviderConfig,
      codeRevision: String,
      sourceTreeHash: String,
      previewRequests: Option[Vector[AdjudicationRequest]] = None
  ): Either[String, LiveDemoManifest] = Try {
    LinkExporter.ensureNew(output).fold(e => throw new IllegalArgumentException(e), identity)
    require(
      codeRevision.matches("[0-9a-f]{40}") && sourceTreeHash.matches("[0-9a-f]{64}"),
      "explicit code/source freeze metadata required"
    )
    require(
      run.admission.demoInputHash == input.inputEvidenceHash && run.policyHash == policy.fingerprint && run.sourceConfigHash == source.fingerprint && run.liveConfigHash == live.fingerprint && run.promptHash == StableIds
        .sha256Hex(OpenAIResponses.prompt) && run.responseSchemaHash == StableIds.sha256Hex(
        OpenAIResponses.schemaText
      ),
      "live demo export binding mismatch"
    )
    require(
      run.decisions
        .map(_.pair.pairId)
        .distinct
        .size == run.decisions.size && run.traces.map(_.pairId).distinct.size == run.traces.size,
      "duplicate live demo decisions/traces"
    )
    run.decisions.foreach(d =>
      require(
        ResolutionValidation
          .check(d, input.context)
          .isRight && d.inputEvidenceHash == input.inputEvidenceHash && d.policyHash == policy.fingerprint && d.configHash == OpenAIResponses
          .effectiveConfigHash(source, live) && run.admission.admittedPairIds.contains(
          d.pair.pairId
        ),
        "invalid protected live demo decision"
      )
    )
    val byDecision = run.decisions.map(d => d.decisionId -> d).toMap
    require(
      run.links.map(_.decisionId).toSet == run.decisions
        .filter(_.decision.decision == MatchOutcome.Accepted)
        .map(_.decisionId)
        .toSet,
      "live accepted decision/link inventory mismatch"
    )
    run.links.foreach(l =>
      require(
        byDecision
          .get(l.decisionId)
          .exists(d =>
            !ResolutionEngine.conflicts(l.pair.left, l.pair.right, input) && ResolutionValidation
              .check(l, d, input.context)
              .isRight
          ),
        "invalid live accepted link"
      )
    )
    require(
      run.constraints
        .map(_.entityType)
        .toSet == ResolutionEntityType.values.toSet && run.constraints.size == 2,
      "both complete demo source constraints required"
    )
    run.constraints.foreach { c =>
      require(
        ResolutionValidation
          .check(c, input.context)
          .isRight && c.policyHash == policy.fingerprint && c.coveredEndpoints.toSet == input.endpoints
          .filter(ResolutionIds.entityType(_) == c.entityType)
          .toSet,
        "demo constraint source coverage mismatch"
      )
      val expected =
        c.coveredEndpoints.flatMap(e => input.authority(e).map((ns, v) => (e, ns, v))).toSet
      require(
        c.authoritativeIdentifiers.map(a => (a.endpoint, a.namespace, a.value)).toSet == expected,
        "demo source assertions incomplete"
      )
    }
    val texts = Vector(
      "demo.json" -> (write(run) + "\n"),
      "admission.json" -> (write(run.admission) + "\n"),
      "live-config.json" -> (write(live) + "\n"),
      "effective-source-config.json" -> (write(source) + "\n"),
      "effective-policy.json" -> (write(policy) + "\n"),
      "decisions.jsonl" -> run.decisions
        .map(write(_))
        .mkString("", "\n", if (run.decisions.isEmpty) "" else "\n"),
      "accepted-links.jsonl" -> run.links
        .map(write(_))
        .mkString("", "\n", if (run.links.isEmpty) "" else "\n"),
      "constraints.json" -> (write(run.constraints) + "\n")
    ) ++ previewRequests.toVector.map(requests =>
      "PREVIEW-ONLY-NOT-EXECUTED-requests.json" -> (write(requests) + "\n")
    )
    val files = texts.map((name, text) =>
      ResolutionExportFile(
        name,
        text.getBytes(UTF_8).length.toLong,
        StableIds.sha256Hex(text),
        if (name == "decisions.jsonl") run.decisions.size
        else if (name == "accepted-links.jsonl") run.links.size
        else 1
      )
    )
    require(files.map(_.bytes).sum <= source.maxOutputBytes, "live demo export byte bound exceeded")
    val manifest = LiveDemoManifest(
      "scholarchain.live-demo-manifest.v1",
      "DEVELOPMENT_DEMO_ONLY_NOT_FULL_POPULATION_OR_FINAL_EVALUATION",
      true,
      input.inputEvidenceHash,
      run.admission.demoCandidateHash,
      run.admission.frozenInputHash,
      run.admission.queueHash,
      run.admission.splitHash,
      policy.fingerprint,
      source.fingerprint,
      live.fingerprint,
      OpenAIResponses.effectiveConfigHash(source, live),
      run.promptHash,
      run.responseSchemaHash,
      run.selectedModel,
      run.providerReportedModels,
      codeRevision,
      sourceTreeHash,
      java.time.Instant.now().toString,
      run.eligiblePairs,
      run.traces.map(_.attempts).sum,
      run.traces.count(_.cacheHit),
      files
    )
    input.sourceRootPath.foreach(root =>
      PathIsolation
        .disjoint(root, output)
        .fold(e => throw new IllegalArgumentException(e), identity)
    )
    Files.createDirectories(output.toAbsolutePath.getParent); Files.createDirectory(output)
    texts.foreach((name, text) =>
      Files.writeString(output.resolve(name), text, UTF_8, StandardOpenOption.CREATE_NEW)
    )
    val text = write(manifest) + "\n"
    Files.writeString(
      output.resolve("live-demo-manifest.json"),
      text,
      UTF_8,
      StandardOpenOption.CREATE_NEW
    )
    Files.writeString(
      output.resolve("_SCHOLARCHAIN_LIVE_DEMO_COMPLETE"),
      StableIds.sha256Hex(text) + "\n",
      UTF_8,
      StandardOpenOption.CREATE_NEW
    )
    manifest
  }.toEither.left.map(e => Option(e.getMessage).getOrElse("LIVE_DEMO_EXPORT_FAILED"))
}

object LiveDemoCommands {
  val help = """Phase 5D explicit development-only provider checkpoint:
  prepare-live-demo --input COMPLETED_DEMO_PHASE4_RUN --frozen-input FROZEN_REVIEW_PHASE4_RUN --queue QUEUE_JSON --split SPLIT_JSON --policy POLICY_JSON --config SOURCE_CONFIG_JSON --live-config LIVE_CONFIG_JSON --scope development|supplement --code-revision GIT_SHA40 --source-hash SOURCE_SHA256 --output NEW_DIRECTORY
  adjudicate-demo --input COMPLETED_DEMO_PHASE4_RUN --frozen-input FROZEN_REVIEW_PHASE4_RUN --queue QUEUE_JSON --split SPLIT_JSON --policy POLICY_JSON --config SOURCE_CONFIG_JSON --live-config APPROVED_LIVE_CONFIG_JSON --scope development|supplement --code-revision GIT_SHA40 --source-hash SOURCE_SHA256 --runtime-binding BINDING_JSON --approval USER_APPROVAL_RECEIPT_JSON --enable-live APPROVAL_ID --output NEW_DIRECTORY
prepare-live-demo never reads credentials or calls a provider. No eligible pair means zero calls.
The live command requires the exact recorded approval and fixed persistent approval-scoped state.
Existing resolve remains disabled/fake only. Human review and final frozen evaluation are separate gates.
"""
  private def value[A](r: Either[String, A]): A =
    r.fold(e => throw new IllegalArgumentException(e), identity)
  private def read[A: ReadWriter](path: String): A = value(
    StrictJson.file(Path.of(path), 67108864L).flatMap(StrictJson.parse[A])
  )
  def run(args: Array[String]): Either[String, String] = Try {
    val command =
      args.headOption.getOrElse(throw new IllegalArgumentException("subcommand required"))
    require(
      Set("prepare-live-demo", "adjudicate-demo")(command),
      "unsupported live demo subcommand"
    )
    val base = Set(
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
      "--output"
    )
    val required =
      if (command == "adjudicate-demo")
        base ++ Set("--runtime-binding", "--approval", "--enable-live")
      else base
    val rest = args.drop(1).toVector; require(rest.size % 2 == 0, "each option requires one value")
    val pairs = rest.grouped(2).map(v => v.head -> v(1)).toVector
    require(
      pairs.map(_._1).distinct.size == pairs.size && pairs.map(_._1).toSet == required,
      "unknown, duplicate or missing live demo options"
    )
    val options = pairs.toMap; val output = Path.of(options("--output"))
    require(
      options("--code-revision").matches("[0-9a-f]{40}") && options("--source-hash")
        .matches("[0-9a-f]{64}"),
      "explicit code/source freeze metadata required before live dispatch"
    )
    require(
      Set("development", "supplement")(options("--scope")),
      "explicit development or supplement scope required"
    )
    value(LinkExporter.ensureNew(output))
    Vector(
      "--input",
      "--frozen-input",
      "--queue",
      "--split",
      "--policy",
      "--config",
      "--live-config"
    ).foreach(k => value(PathIsolation.disjoint(Path.of(options(k)), output)))
    val source = value(ResolutionConfig.load(Path.of(options("--config"))))
    val live = value(LiveProviderConfig.load(Path.of(options("--live-config"))))
    val policy = value(ResolutionPolicy.load(Path.of(options("--policy"))))
    val input = value(InputLoader.load(Path.of(options("--input")), source))
    val frozen = value(InputLoader.load(Path.of(options("--frozen-input")), source))
    val queue =
      value(ReviewQueue.parseQueue(value(StrictJson.file(Path.of(options("--queue")), 67108864L))))
    val split = read[ReviewSplit](options("--split"))
    val population = value(CandidateBuilder.build(input, source))
    val enabled = command == "adjudicate-demo"
    val runtime = if (enabled) {
      val r = read[LiveRuntimeBinding](options("--runtime-binding"))
      value(LiveRuntimeBinding.verify(r, Path.of(options("--approval")), live, Path.of("")))
      require(
        options("--enable-live") == live.approvalId,
        "explicit live opt-in differs from approval"
      )
      Vector(
        r.absoluteLedgerPath,
        r.absoluteCachePath,
        options("--approval"),
        options("--runtime-binding")
      ).foreach(p => value(PathIsolation.disjoint(Path.of(p), output)))
      Some(r)
    } else None
    val result = value(
      LiveDemo.run(
        input,
        population,
        frozen,
        queue,
        split,
        policy,
        source,
        live,
        runtime
          .map(r => Path.of(r.absoluteLedgerPath))
          .getOrElse(output.resolve("UNUSED-budget.json")),
        runtime.map(r => Path.of(r.absoluteCachePath)),
        "run:" + UUID.randomUUID(),
        enabled,
        runtime.map(_.approvalId).getOrElse(""),
        () => new OpenAIHttpTransport(() => Option(System.getenv(live.apiKeyEnvironment))),
        supplemental = options("--scope") == "supplement"
      )
    )
    if (!enabled) {
      val previewEvidence = input.evidence ++ population.derivedEvidence.map(e => e.ref -> e)
      val selection = value(
        if (options("--scope") == "supplement")
          LiveDemo.selectSupplement(input, population, frozen, queue, split, policy)
        else LiveDemo.select(input, population, queue, split, policy)
      )
      val requests = selection.eligiblePairs.take(live.budget.maxAttempts).map { candidate =>
        val classified = value(ResolutionEngine.classify(candidate, input, policy))
        value(
          OpenAIResponses
            .request(candidate, input, policy, source, live, classified.features, previewEvidence)
        )
      }
      value(
        LiveDemoExporter.writeNew(
          output,
          result,
          input,
          policy,
          source,
          live,
          options("--code-revision"),
          options("--source-hash"),
          Some(requests)
        )
      )
      s"Development/demo readiness: admitted=${result.admission.admittedPairIds.size}, naturally eligible=${result.eligiblePairs}; provider calls=0. No held-out predictions or human labels read."
    } else {
      val manifest = value(
        LiveDemoExporter.writeNew(
          output,
          result,
          input,
          policy,
          source,
          live,
          options("--code-revision"),
          options("--source-hash")
        )
      )
      s"Development/demo checkpoint: eligible=${result.eligiblePairs}, live attempts=${manifest.liveAttemptsThisRun}, verified cache hits=${manifest.cacheHitsThisRun}. Human labels and final evaluation remain separate."
    }
  }.toEither.left.map(e =>
    Option(e.getMessage)
      .filter(m => !m.toLowerCase.contains("bearer"))
      .getOrElse("LIVE_DEMO_COMMAND_FAILED")
  )
}

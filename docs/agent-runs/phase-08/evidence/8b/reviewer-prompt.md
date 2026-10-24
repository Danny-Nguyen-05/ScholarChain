You are the independent, read-only code reviewer for ScholarChain Phase8, Subphase8B, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md and docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase8.md — Sections3–7, Subphase8B and Section10. Byte-identical snapshot: docs/agent-runs/phase-08/evidence/8b/phase8-plan.md (cmp0).
3. Course Phase8 specification: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-8-create-embeddings-and-populate-s3-vectors
4. docs/agent-runs/phase-08/prompt.md, owner-report.md and test-report.md (Subphase8B sections), repairs.md, prior user-supplied review in review.md, and evidence/8b/.

Checkpoint facts:
- Branch phase-8; base and current HEAD 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e. All8B changes are uncommitted. Earlier8A commit/push was separately authorized; no8B commit/push.
- Exact complete tracked/untracked inventory: docs/agent-runs/phase-08/evidence/8b/files.json. Source paths/hashes: source-files.json. Coordinator evidence changes are confined to docs/agent-runs/phase-08/; human-owned decisions are untouched.
- Changed tracked source/build/module-documentation files:
- build.sbt
- modules/core/README.md
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/EmbeddingContracts.scala
- modules/core/src/test/resources/wire/embedding-document.json
- modules/core/src/test/resources/wire/embedding-work-item.json
- modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/EmbeddingContractSpec.scala
- modules/rag/README.md
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/DocumentRendering.scala
- modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/EmbeddingRagSpec.scala
- modules/storage/README.md
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/EmbeddingManifest.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/InMemoryStorage.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/fakes/Fakes.scala
- modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/EmbeddingStorageSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingSlotRepairSpec.scala
- New untracked source/test/fixture files:
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/EmbeddingIngestMain.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingIngestMain.scala
- modules/rag/src/test/resources/embedding-smoke.json
- modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/EmbeddingRetrievalSpec.scala
- modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingGuardSpec.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/InMemoryGraphLoader.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/LocalEmbeddingState.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/Phase6EmbeddingSource.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/fakes/AdministrativeFakes.scala
- modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/EmbeddingGroupStateSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbedding8BFailureSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbedding8BGuardSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbedding8BSmokeSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingG1ExportMain.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingLocalReplayMain.scala
- Step0 question: repair chunk-group consistency now or disclose/test it? User answered “Repair chunk-group consistency now (recommended)”. Prior decisions persist: us-east-2; configured TitanV2 ID/version; provisional256/cosine; five types; permitted abstract or fallback; manifest runner+SQS/fake; core EmbeddingClient; stable slot excludes source run. No AWS account, no live/provider calls, no reviewer launch, no human-decision edits.
- Affected gates exit0: core13, storage19, RAG25, independent39. Exact commands and failed attempts in evidence/8b/commands.md and retained logs/excerpts.
- Full JDK17 command: /usr/bin/time -p sbt -batch check > /tmp/phase8b-final-check-1.txt 2>&1
  Environment: JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; PATH="$JAVA_HOME/bin:$PATH"; SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml".
  Exit0;756passed/0failed; module counts core157/Hadoop64/ER39/Spark38/storage51/RAG25/independent374/build8;678.84seconds real. Expected checkProbeInjectFailure is a passing build self-test.
  Raw log /tmp/phase8b-final-check-1.txt; 1381548 bytes; SHA256 91ef687108bcb2ec6083b1033197a6373477e49130bb68ec464659e34149ea59.
  Evidence: final-check.json, line-numbered final-check-excerpt.txt, final-audit.json. All254 frozen files match /tmp/phase8b-frozen-source.json; snapshot hash in frozen-source.json. All30 changed/new source hashes match source-files.json.
- Genuine G1 producer uses existing public Phase6 jobs over committed independent direct fixture/link inputs:10researchers,9canonical works,18literal windowed edges,28tables. It does not claim Hadoop/ER acquisition. Output target/phase8b-g1-export, run:55555555-5555-4555-8555-555555555555.
- Actual local CLI acceptance: G1 selected12 summaries, first12written, replay12unchanged/0calls; real selected12summaries+3topics+1institution, first16written, replay16unchanged/0calls across all5types. Fresh counters/manifest hashes match; all12/16 persisted pointers and qualification hashes verify. Clean separate forked directCLI confirms12/16skip0calls. See g1-/real-acceptance.json, first/replay/fresh reports, final-process reports, artifact inventories, local-acceptance-1.txt and cli-process-replay-3.txt. Generated full state/manifests/exports stay ignored under target.
- Six committed lexical smoke queries cover researcher/community/path/paper/topic/institution with distractors. Every stored hit resolves to ordinary text/hash; context denies exact metrics and graph authority.
- LiveEmbeddingIngestMain is authored but UNEXECUTED. Disabled live-config.template.json, live-approval.template.json and live-runbook.md are templates/instructions, never human approval. Tests only use pure preflight/refusal with zero client-factory construction; no approved execution even with fakes. No cloud provisioning or cleanup.

Findings/status to inspect:
- F1 and N1: independently FIXED in prior8A recheck; do not reopen merely because source run is excluded or summaries preserve exact bytes.
- R1: user-authorized8B repair, locally verified but awaits this review. Group key excludes ordinal/source run/text/count; immutable binding carries count+whole-text hash. Complete unique members/config preflight before payload/embed writes. Actual renderer shrink/grow tests reject whole group with no data writes except rejection report. New model namespace and unchanged replay remain valid. Existing per-item state lacking group binding fails closed; no silent migration. Group consistency is preflight protection, not vector transaction atomicity.
- N2–N8 and R2–R3 remain OPEN/nonblocking/deferred. R2 retains first filter metadata on unchanged text; R3 lacks pre-embedding filter-budget check. Preserve scope unless a new confirmed blocker is found.
- Runtime fence is unchanged. Storage extracted administrative fake class/alias to preserve the file-level scan; actual5 roots/20 inspected/no findings. Build change forks CLI and forwards only optional explicitly configured logback property, fixing observed Hadoop lifecycle/logging issues.
- Live compatibility, Titan quality, full10,000-vector ingestion, latency, costs and cleanup remain future8C gates after Phase14 deployment and human approval. Optional providers/OpenSearch/extra services/indexes/CI omitted. Dollar bounds are configured assumptions, not billing guarantees.

Review rules:
- Read-only: no edits, builds/tests, AWS/provider calls, data changes, commits/pushes or secret reads. Do not launch another reviewer.
- Inspect git diff 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e and all untracked implementation/evidence. Verify ownership, separate work orders, no hardcoded operational values without configuration/rationale, no secrets, honest retained commands/results, meaningful hand-derived tests, spend gates and lean scope.
- Check deterministic rendering/group/slot behavior, model versioning, failure/recovery, compact metadata, actual source qualifications, disk/process replay, retrieval/pointer/hash boundaries and authored/unexecuted live packet.
- Re-hash retained raw logs and source inventories rather than trusting summaries. Report all confirmed findings in one pass, distinguishing blockers, nonblocking observations and future/unverified gates. No self-approval or human/instructor acceptance claim.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase8B.
2. Findings with severity, path:line, evidence, impact, owning agent, acceptance check and blocking yes/no.
3. Exact report fields from docs/agent-runs/README.md.
4. A complete NEXT PROMPT in one fenced block:
   If REQUEST-CHANGES: record verdict verbatim, route blockers by ownership, preserve deferred items, rerun affected and full JDK17 gates with retained raw SHA/size/excerpt, return recheck prompt and stop. Do not start8C or launch reviewers.
   If APPROVE: record verdict verbatim, update dispositions and require the user commit gate.8C must NOT start without Phase14 deployment and actual human-written live approval/caps; the user currently has no AWS account. Explain missing live gates and stop unless the user supplies those prerequisites and a new8C prompt. No automatic commits/pushes, human decision edits or reviewer launch.
This review is not human acceptance or instructor approval.

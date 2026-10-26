You are the independent, read-only code reviewer for ScholarChain Phase 9, Subphase 9C, in /Users/danny/Documents/UIC/CS441/ScholarChain.

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md, docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase9.md — Sections 3–7, Subphase 9C in Section 8, Sections 9–10.
3. Course specification: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-9-implement-the-runtime-collaboration-analysis-agents
4. docs/agent-runs/phase-09/{prompt,owner-report,test-report,review,repairs}.md; evidence/9a/user-answers.md, evidence/9b/user-answers.md; all evidence/9c/, particularly handoff.md, user-answers.md, commands.md, coverage-and-limitations.md, specialist-reports.md, delegation.md and contract-gaps.md.

Checkpoint facts:
- Branch phase-9; base and HEAD 2527de01252286080e6db776b9cc0199a9353e1e. Initial tree clean; approved 9B committed blobs verified. 9C remains uncommitted.
- Plan SHA-256 8c16e8eeaf783ee47a484a0927cac372263335d664bac7ac0f5e470b33b5fcf8.
- Exact changed/untracked inventory: evidence/9c/files.json. All 38 source/test/module-doc hashes and owners: source-files.json; before/after hashes: change-files.json; prior-source integrity: source-audit.json.
- Changed tracked paths:
  docs/agent-runs/phase-09/owner-report.md
  docs/agent-runs/phase-09/prompt.md
  docs/agent-runs/phase-09/repairs.md
  docs/agent-runs/phase-09/test-report.md
  modules/core/README.md
  modules/core/src/main/resources/scholarchain.runtime-config.v1.json
  modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/RuntimeConfig.scala
  modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/RuntimeContracts.scala
  modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsValidation.scala
  modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/RuntimeContractSpec.scala
  modules/rag/README.md
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/CollaborationMetricsAgent.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/CommunityAnalystAgent.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/EvidenceBuilderAgent.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/PathFinderAgent.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/QueryPlannerAgent.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeLlm.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeRetrieval.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeSchemas.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/SemanticContextAgent.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/WorkflowRunner.scala
  modules/storage/README.md
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9BEvidenceSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9BWorkflowSpec.scala
- Untracked source/test/resource paths:
  modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/RuntimeAuditValidation.scala
  modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/Runtime9CContractSpec.scala
  modules/rag/src/main/resources/runtime-benchmark-v1.json
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/AnswerSynthesisAgent.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/ClaimVerificationAgent.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeAnswerWorkflow.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeOfflineFixture.scala
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeWorkflowMain.scala
  modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Runtime9CSpec.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/RuntimeAuditStore.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/fakes/InMemoryRuntimeAuditStore.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/RuntimeAuditStorageSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9CBenchmarkSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9CFixture.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9CSynthesisSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9CTrustSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9CVerificationSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9CWorkflowSpec.scala
- Also untracked: docs/agent-runs/phase-09/evidence/9c/ (entire lean packet, recursively inventoried in files.json). Raw full logs remain /tmp only.
- User approved all seven defaults: field-scoped convergence and approximate P90 sampling details; truthful source/request lineage and deterministic audit identity; named semantic filtering/text=None/status pairs; required fail-closed audit on existing infrastructure with rejected claims and evidence-only behavior; independent compatible byte caps; offline CLI/versioned hand-derived benchmark plus natural temporal/community grammar and synthetic-coverage disclosure; only necessary remaining fixes. Original ten decisions and 9B defaults remain binding verbatim in their user-answer files.

Observed commands and results:
Every sbt command used:
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version: Homebrew OpenJDK 17.0.20.1; saved java-version.txt.
- Core formatted target: exit 0, 50 passed; exact command in core-targeted-1-result.json.
- Final target 5: exit 0, 299 passed (storage 14/RAG 74/independent 211), zero failures, 16.31 seconds:
/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeAuditStorageSpec' 'rag/testOnly *Runtime9CSpec *Runtime9ASpec *Runtime9ARepairSpec *Runtime9BSpec' 'independentTests/testOnly *Runtime9C* *Runtime9B* *Runtime9APlannerSpec *Runtime9AResolverSpec *Runtime9ARepairPlannerSpec *Runtime9ARepairResolverSpec *Runtime9AEvidenceSpec'
  /tmp/phase9c-targeted-5.log SHA-256 03be3286d55e126145eb6b864216cb10042b17eaaaed84d13b5903cd159e7200.
- Actual CLI benchmark 2: exit 0, 15/15 literal cases passed, including both ambiguity candidates:
/usr/bin/time -p sbt -batch 'rag/runMain edu.uic.cs441.scholarchain.rag.RuntimeWorkflowMain --benchmark'
  /tmp/phase9c-cli-benchmark-2.log SHA-256 b08d7aa37c9dfcaa3ea6b278760e974b430b7f7baf01c3d82961082744b88986.
- /usr/bin/time -p sbt -batch check: exit 0, 1,131 passed, zero failed, 780.69 seconds. Counts core 207/Hadoop 64/entity-resolution 39/Spark 38/storage 80/RAG 107/independent 588/build 8. Final TestRunMarker ran; injected format-stage failure is the expected passing build self-test.
  /tmp/phase9c-check-2.log SHA-256 830bb94d47e4d122f44013f5a42f82fc45fed696df4020afba395511cbd0bc37.
- git diff --check exit 0; untracked whitespace checks clean. All 38 source hashes and 13 raw-log bindings verified. Plan, original user decisions and prior reviews unchanged. No active specialists/builds.
- All earlier attempts retained honestly. Full check 1 intentionally terminated, exit 143, after packet inspection found dropped ambiguity candidates. Owners repaired final result/CLI/hash and strengthened tests, then target 5, CLI 2 and full check 2 passed. Never count the interrupted run as a pass. Exact commands/exits/excerpts/hashes are in commands.md and *-result.json.

Review focus:
- Schema-shaped typed synthesis, bounded retry/bytes/deadlines; deterministic verifier and templates are the factual decider. Check IDs, exact decimals, windows, evidence kinds, contradictory citations, full hop support, total-author conversion, rejected-claim retention and regenerated text. ABSTAINED retained; no LLM verifier.
- O1/R1 qualifier scope and stored P90 sample details; O2 truthful stored-source provenance; O3 resolved/deterministic identities; O4/O8/O9 named semantic scope, deterministic text=None and path-status researcher pairs.
- Audit real/fake adapters on existing ObjectStore/QuerySessionStore: immutable content-bound objects, namespaced conditional pointer, integrity/replay/retry/readback, failed required audit closes response, attempted/rejected claims/versions/usage/hash retained, pre-plan failure without fabricated plan.
- Evidence-only skips synthesis; audit reservation fits 30,000 ms synchronous deadline. Context remains 4,096. Separate question/prompt/request/output/persisted caps preserve legacy maxInputBytes fallback.
- Hand-derived benchmark asserts component identity, B/C coauthors, ordered A-C-D-F-G route, both community sizes, exact values and ranking scope/truncation. Ambiguity returns both bounded canonical homonym records without synthesis or resolved audit identity selection.

Known limitations:
Offline scripted LLM and disclosed synthetic G1 community/metadata/temporal/homonym overlays only. No live smoke approval or provider/cloud calls. Live model/tool/region/temperature compatibility, quality/general injection resistance, latency and real enrichment coverage unverified. Conservative interpretation/planner grammar; larger atomic groups can abstain; strict missing metadata gives Unsupported. N2/N4–N7, O5/O6/O7/O10 and generic P90 evidence type retain disclosed limits; exact N/O/R dispositions are in coverage-and-limitations.md. Ports require interruption/own timeouts; failed audit pointer publication can leave an orphan object, identical retry repairs it, changed envelope at the same query ID conflicts. Broader fault/injection suites remain Phase 11B. Phase 8C stays deferred to 14C; no whole-Phase-8 acceptance. No Phase 10 work, infrastructure, secrets, human-gate edits, commits or pushes.

Review rules:
Read-only: no edits, builds/tests, AWS/provider calls, secrets, data changes, commits or pushes. Inspect git diff 2527de01252286080e6db776b9cc0199a9353e1e plus ALL untracked files. Report all confirmed findings in one pass. Check ownership/one writer, operational configuration, provenance, honest evidence/hash bindings, hand-derived tests, spend gates and recorded omissions. Also check allowlisted plans/parameterized queries, ambiguity candidates, deterministic claim decisions, evidence IDs, untrusted-data delimiters, vector-mode numeric prohibition, versioned prompts/schemas and no live calls. Distinguish blockers, nonblocking observations and unverified future gates. Do not require later-phase scope.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 9C.
2. Findings: severity, path:line, evidence/reasoning, impact, owner, acceptance check, blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A COMPLETE NEXT PROMPT in one fenced block:
   APPROVE: append this review verbatim under Subphase 9C, record nonblockers, confirm a user-authorized 9C commit (ask if missing; never commit/push without explicit instruction), and tell the user Phase 9 is ready for their human gate and Phase 10 is next. User owns human-gate/commit records. Do not start or prepare Phase 10; stop.
   REQUEST-CHANGES: append review verbatim and route only blockers to their native owning specialist, one writer/path and no nested delegation/reviewer. Preserve decisions; rerun affected targets and full JDK 17 check with retained evidence/hashes; return a complete repair recheck prompt and stop. Nonblockers are logged, not required unless requested. No next-phase work, live calls, human-gate edits or unauthorized commits/pushes.

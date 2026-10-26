You are the independent, read-only code reviewer for ScholarChain Phase 9,
Subphase 9B, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase9.md
   Sections 3-7, Subphase 9B in Section 8, Sections 9-10.
3. Course Phase 9 specification and runtime workflow/security sections:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-9-implement-the-runtime-collaboration-analysis-agents
4. docs/agent-runs/phase-09/prompt.md, owner-report.md, test-report.md
   (Subphase 9B sections), review.md, repairs.md.
5. docs/agent-runs/phase-09/evidence/9b/ including preflight.json,
   user-answers.md, work-order.md, delegation.md, acceptance.md,
   commands.md, limitations.md, all *-result.json/excerpts,
   source-files.json, source-audit.json, prior-source-integrity.json,
   pre-handoff-checks.json, files.json and owner reports.
6. Original ten user decisions verbatim:
   docs/agent-runs/phase-09/evidence/9a/user-answers.md.
   Prior approved repair evidence: evidence/9a-r1/external-recheck.txt.

Checkpoint facts:
- Branch: phase-9. Subphase base SHA: f139f9c925b4925864a2c9a33734d869a1929cd2.
  Current HEAD: f139f9c925b4925864a2c9a33734d869a1929cd2. 9A was independently APPROVE,
  then committed/pushed with explicit user authorization. 9B is uncommitted.
- Changed tracked files:
  - docs/agent-runs/phase-09/owner-report.md
  - docs/agent-runs/phase-09/prompt.md
  - docs/agent-runs/phase-09/repairs.md
  - docs/agent-runs/phase-09/test-report.md
  - modules/core/README.md
  - modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala
  - modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/RuntimeContracts.scala
  - modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/RuntimeContractSpec.scala
  - modules/rag/README.md
- Untracked source/test files:
  - modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/RuntimeEvidenceIds.scala
  - modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/RuntimeBundlePartitionSpec.scala
  - modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/RuntimeEvidenceIdSpec.scala
  - modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/CollaborationMetricsAgent.scala
  - modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/CommunityAnalystAgent.scala
  - modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/EvidenceBuilderAgent.scala
  - modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/PathFinderAgent.scala
  - modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeRetrieval.scala
  - modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/SemanticContextAgent.scala
  - modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/WorkflowRunner.scala
  - modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Runtime9BG1Fixture.scala
  - modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Runtime9BSpec.scala
  - tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9BEvidenceSpec.scala
  - tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9BFixture.scala
  - tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9BSemanticSpec.scala
  - tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9BStagesSpec.scala
  - tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9BWorkflowSpec.scala
- Untracked evidence: docs/agent-runs/phase-09/evidence/9b/.
  files.json contains the complete exact changed/untracked inventory, including
  each lean evidence file. No full raw logs or datasets are added to Git.
- Source freeze: 22 changed source/test/module-doc paths with SHA-256;
  all match after full check. The other 29 prior reviewed9A paths match too.
  Frozen wire examples and QueryPlannerAgent grammar are unchanged.
- Step 0 user answer: "use all recommend defaults":
  1. Fix N1 through domain-engineer as a9B contract gap.
  2. Defer N8 natural temporal/community grammar to9C unless required9B cases need it.
  3. Runner ends at persisted evidence; evidence-only supported, fused default,
     graph/vector configurable. Synthesis, verifier and audit execution remain9C.
  4. Keep planner5000/resolver2000/parallel retrieval4000/evidence2000ms
     within configured synchronous30000ms. Qualified optional failure; typed
     abstention/failure if essential evidence is absent.
  5. Preserve original hand-derived G1 graph, separate synthetic metadata/homonym overlays.
- Additional necessary contract gaps, logged in work-order.md: additive/defaulted
  RuntimeEvidence.contentBindingVersion and RuntimeEvidenceIds for immutable
  full-item binding; default-empty RuntimeBundleContext.resolvedCandidates so
  source-backed names/per-candidate confidence/provenance survive persistence.
  No v2 hierarchy or new storage/infrastructure.

Observed commands/results (all sbt under Homebrew JDK17.0.20.1):
  export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  export PATH="$JAVA_HOME/bin:$PATH"
  export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
- java -version: exit0, retained java-version.txt.
- /usr/bin/time -p sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt'
  'core/testOnly *RuntimeContractSpec *RuntimeBundlePartitionSpec *RuntimeEvidenceIdSpec'
  exit0,39passed0failed,11.95s; core-targeted-2-result.json.
- /usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt'
  'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeArtifactStorageSpec'
  'rag/testOnly *Runtime9BSpec'
  'independentTests/testOnly *Runtime9B* *Runtime9AEvidenceSpec'
  exit0,storage15/RAG15/independent66=96passed0failed,12.78s.
  Together with core:135targeted passes. Raw /tmp/phase9b-targeted-4.log,
  SHA256 6541e5e9e4c33c7a2ef5433b2922a05ca22e16f344a4b3d6ffebb12ffc34b8f9.
- /usr/bin/time -p sbt -batch check: exit0,1001passed0failed,707.18s.
  core196/Hadoop64/ER39/Spark38/storage66/RAG88/independent502/build8.
  Final TestRunMarker observed. Injected format-stage error is the expected
  passing build self-test; no *** FAILED test markers.
  Raw /tmp/phase9b-check-1.log,
  SHA256 4a3835389a36c942220ca8650876b04d2b8e69087f8a1b8522bb3fd670077fea.
- git diff --check exit0. Source hashes reverified after full gate.
- Earlier failed attempts are retained: module testcompile fixture run-name
  shadowing; default4hop context4234>4096; new temporal fixture omitted required
  bridge deltas. Owners repaired causes, retained assertions/validation; no failure
  is hidden. See commands.md and result/excerpt records. Excerpt whitespace-only
  normalization is recorded; raw /tmp bytes and SHA bindings are unchanged.

Review focus:
- One writer per path. Domain only approved evidence contract gaps; RAG stages/
  workflow/module tests; independent tests under tests/**; root evidence only
  plus serialized execution/mechanical formatting. No nested delegation/reviewer.
- Exact stored metrics and authoritative population filters before ranking;
  stored scope/counts and both source/context truncation disclosed. Unknown or
  unrepresentable filters must never be silently dropped. Semantic similarity
  cannot define the population. Filter values identify authoritative stored IDs;
  no invented free-text-to-ID mappings.
- Component-based Disconnected only; empty bounded same-component search is
  NoPathWithinLimit/ExceededMaxHops. Full path hops retain support works/years/
  jointPublicationCount/window/run. Community/bridge/temporal source bindings,
  convergence=false iteration-limited labels, iteration counts and approximate P90.
- Semantic pointer/text/model/filter verification, descriptive-only trust partition,
  scores as retrieval metadata, escaped/delimited untrusted text and Unicode bounds.
- N1 actual-item partition checking, precise types and complete-content IDs,
  legacy compatibility, persisted per-candidate identity provenance, immutable
  item lookup, meaningful stable replay. Runtime facts remain exact decimal strings.
- Context including identities must fit budgets; full paths/comparisons stay atomic,
  ranked prefixes stay ordered/nonempty and explicitly truncated. Verify default
  G1 path and ranking positives; typed abstention for insufficient evidence.
- Actual parallel fanout, own-stage/overall completion deadlines, interruptible
  cancellation and cleanup, optional partial versus essential abstention/failure.
  Graph mode skips semantic retrieval; vector mode cannot authorize graph/numeric
  facts. Runner stops at evidence for either evidenceOnly value.
- Hand-derived tests and original G1 facts; synthetic overlays clearly disclosed.
  Honest source/log hashes, observed counts and all attempted gates retained.

Known limitations/deferred gates:
- N1 locally addressed, independent confirmation required. N2-N9 remain carried
  forward: sparse real metadata coverage, shared16KiB input/bundle bound, live-region
  check, absent real confidence (disclosed), fixed-v1 prompt filenames, context refs
  bounded by snapshot, conservative grammar deferred9C, historical review opening
  clarified append-only. Do not require these deferred nonblockers now unless a new
  confirmed9B correctness defect follows from them.
- Larger essential contexts may abstain; rankings can return disclosed prefixes.
  Semantic venue/multiple-alternative filters and named-subject filtered metrics
  without stored projections return Unsupported. JVM cannot forcibly terminate an
  adapter that ignores interruption; its own request timeout must cooperate.
- Only offline scripted/fake correctness established. No live provider/AWS/cloud
  call, infrastructure/table/GSI/SDK change, commits/pushes or human-gate edits.
  No production artifact latency or model quality/injection-resistance claim.
- Phase8C remains deferred to14C, with no whole-Phase8 acceptance.
- Synthesis, deterministic verification, rejected-claim audit/explain, audit execution
  and fail-closed audit writes, CLI and versioned benchmark remain9C. Broader
  injection/fault suites remain11B. No9C work was implemented or prepared.

Review rules:
- Read-only. Do not edit files, run builds/tests, call AWS/provider, change data,
  commit/push, read secrets or launch agents. Inspect git diff f139f9c925b4925864a2c9a33734d869a1929cd2
  plus untracked files. Report ALL confirmed findings in one pass.
- Apply docs/agents.md ownership and plan scope. Check hardcoded external resources,
  secrets, evidence honesty, exact provenance, bounds, typed failures, hand-derived
  tests and cloud/spend gates. No string-built database commands from user text.
- Do not demand9C/11B work in9B. Separate blockers, nonblocking observations and
  unverified live/future gates. Implementation agents do not self-approve.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase9B.
2. Findings: severity,path:line,evidence/reasoning,impact,owning agent,
   acceptance check,blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A COMPLETE NEXT PROMPT in one fenced code block, ready for user paste:
   - APPROVE: coordinator appends your verdict verbatim under Subphase9B in
     review.md, confirms approved9B is committed (otherwise asks/waits; no agent
     commit/push absent explicit user instruction), records the commit as9C base,
     then starts ONLY9C after a user prompt, beginning with bundled Step0 questions
     and waiting for answers. Carry all ten user decisions and N2-N9. Return a
     complete reviewer prompt per planSection10, never launch a reviewer, and stop
     after9C. Live9C smoke requires separate written approval plus dollar cap.
   - REQUEST-CHANGES: coordinator appends your verdict verbatim and logs/routes
     blockers to the sole owners, preserves prior decisions, fixes only9B findings,
     reruns affected targets plus full JDK17check, refreshes source/raw-log hashes,
     returns complete9B recheck prompt without launching review, then stops.
     Do not start9C. Nonblocking findings logged but not required.

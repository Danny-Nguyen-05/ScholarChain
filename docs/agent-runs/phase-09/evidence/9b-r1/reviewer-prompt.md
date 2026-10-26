You are the independent, read-only code reviewer for ScholarChain Phase 9,
Subphase 9B repair round 1, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. Plan of record:
   /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase9.md
   Sections 3-7, Subphase 9B in Section 8, Sections 9-10.
3. Course Phase 9 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-9-implement-the-runtime-collaboration-analysis-agents
4. docs/agent-runs/phase-09/prompt.md, owner-report.md, test-report.md
   (9B repair round 1 sections), review.md, repairs.md.
5. docs/agent-runs/phase-09/evidence/9b-r1/: external-review.txt and its SHA,
   preflight.json, work-order.md, delegation.md, source-before.json,
   repair-files.json, source-files.json, source-audit.json, commands.md,
   targeted-1-result.json, check-1-result.json and excerpts, acceptance.md,
   prior-source-integrity.json, validation.json, files.json and owner reports.
6. Original ten user decisions verbatim in evidence/9a/user-answers.md;
   approved9B defaults in evidence/9b/user-answers.md and original9B packet.

Checkpoint facts:
- Branch phase-9; base SHA and current HEAD both:
  f139f9c925b4925864a2c9a33734d869a1929cd2.
- 9A was approved and committed. 9B and this repair remain uncommitted.
- User instruction: "fix all blocking bugs for me". Only B1 is blocking.
  No questions remained for this repair. O1-O10 are logged only, unchanged.
- Initial9B review: REQUEST-CHANGES, preserved verbatim INCLUDING its next
  prompt in review.md under Subphase9B and evidence/9b-r1/external-review.txt.
  SHA256 a558249e6a6b54c4fce45d15b78eb17a5b9deacb8a588dab76845248ce6ecfed.
- Four repaired paths relative to reviewed9B (before/after hashes in repair-files.json):
  modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/CollaborationMetricsAgent.scala
  modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Runtime9BSpec.scala
  modules/rag/README.md
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9BStagesSpec.scala
- All22cumulative9B source/test/module-doc hashes match after fullcheck.
  The18unrepaired reviewed9B paths match their prior hashes. The29untouched
  prior9A paths match approved9A hashes. Five prior9A paths already changed in
  initial9B are identified explicitly in prior-source-integrity.json, not
  falsely claimed unchanged. No core/storage/build/infra/builder change this round.

Changed tracked files relative to base:
- docs/agent-runs/phase-09/owner-report.md
- docs/agent-runs/phase-09/prompt.md
- docs/agent-runs/phase-09/repairs.md
- docs/agent-runs/phase-09/review.md
- docs/agent-runs/phase-09/test-report.md
- modules/core/README.md
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/RuntimeContracts.scala
- modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/RuntimeContractSpec.scala
- modules/rag/README.md

Untracked source/test files (initial9B files, still uncommitted):
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

Untracked evidence directories: docs/agent-runs/phase-09/evidence/9b/ and9b-r1/.
Exact complete inventory including each evidence file is in9b-r1/files.json.

B1 original defect:
When qualifications contained pathLengthEstimate, the named lookup combined
exact P/C/T/A/M/W/coreness with P90 then set the entire item's approximate=true.
Ranking kept the same researcher's exact values approximate=false. This leaked
an ambiguous qualifier into immutable evidence and context.

Repair to verify:
- Exact Metric evidence remains approximate=false and byte-for-byte identical
  with/without the estimate. Named and ranking exact values/window/run agree.
- Stored P90 is a separate kind=distance-estimate deterministic item:
  approximate=true, descriptive=false, component subject/componentId,
  effectiveDiameterP90=4.0, distanceMethod=sampled-bfs,
  distanceP90Approximate=true, source window/run, source refs to
  metrics/type=path_length_estimate component row fields effectiveDiameterP90
  and method. Existing RuntimeEvidenceIds.bind supplies full content binding.
- Existing non-ranking deterministic builder admission is unchanged/atomic.
  An exact-only context budget refuses the whole metric+estimate request
  before persistence; sufficient budget persists both with indexed lookup.
- Iteration-limited labels, source validation, N1 partitions, budgets and
  default four-hop/ranking workflows remain intact. No O-item repair or9C work.

Ownership/delegation:
- /root/rag_9b_r1: modules/rag/** only, production/module tests/README.
- /root/tests_9b_r1: tests/** only, independentP90case plus atomic regression.
- /root: evidence assembly and serialized formatting/gates.
No nested delegation/reviewer. Both specialists completed. No running builds/jobs.
No domain/storage owner was needed; no new contract or infrastructure.

Commands and observed results (Homebrew OpenJDK17.0.20.1):
Every sbt invocation used:
  export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  export PATH="$JAVA_HOME/bin:$PATH"
  export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
- java -version: exit0; retained java-version.txt.
- /usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt'
  'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeArtifactStorageSpec'
  'rag/testOnly *Runtime9BSpec'
  'independentTests/testOnly *Runtime9B* *Runtime9AEvidenceSpec'
  exit0,99passed0failed:storage15/RAG17/independent67,11.66seconds.
  Raw /tmp/phase9b-r1-targeted-1.log,
  SHA256 6ab60e10fbb8af910f580827ae3411b8c52bf2f75ea031170324146e0bbeec3d.
- /usr/bin/time -p sbt -batch check
  exit0,1004passed0failed,717.84seconds.
  Counts core196/Hadoop64/ER39/Spark38/storage66/RAG90/independent503/build8.
  Expected injected format-stage failure is the passing build self-test.
  Final TestRunMarker observed; zero *** FAILED markers.
  Raw /tmp/phase9b-r1-check-1.log,
  SHA256 6b4755d9be0c7449f27d1d4ace7c1942bd6728a0b39f7935823e5a8f373ef42a.
- git diff --check exit0. Cumulative22hashes and4repair after-hashes verified.
- No failed build/test attempt in this repair round. An evidence-only Python
  report helper had a syntax error before execution, wrote no files, and was
  corrected; recorded in commands.md. No source change or extra test resulted.
  Earlier initial9B failures remain honestly retained in their own packet.

Known nonblockers/future scope:
- O1-O10 logged OPEN only: convergence qualifier scope; mixed request/source
  provenance; semantic subjects in bundle researcherIds; named semantic scope;
  larger atomic context limits/scope duplication; prefix byte-bound behavior;
  adapter ExceededMaxHops reachability; deterministic text hardening;
  rendered path-status pair; filtered-ranking test discrimination.
  Do not demand these optional repairs unless a new confirmed B1 regression
  makes them blocking. N1 externally confirmed fixed; N2-N9 carried forward.
- Live provider/model/region/injection behavior, production latency,
  interruption-ignoring adapters and real enrichment coverage remain unverified.
- Phase8C deferred14C; no whole-Phase8 acceptance. Original ten decisions and
  approved9BStep0defaults preserved. No live/cloud/provider calls, secret reads,
  commits/pushes, human-gate edits, infrastructure or9C implementation/preparation.
- Synthesis/verifier/audit/CLI/benchmarks remain9C, broader injection/faults11B.

Review rules:
- Read-only. No edits, builds/tests, AWS/provider calls, data changes,
  commits/pushes, secret reads or agent launches. You may fetch course docs only
  if needed for read-only authority verification; never make service/provider calls.
- Inspect git diff f139f9c925b4925864a2c9a33734d869a1929cd2 plus untracked files, then focus repair
  using source-before.json and four before/after bindings. Report ALL confirmed
  findings in one pass. Verify findings against actual files.
- Check B1 acceptance completely, unchanged other9B behavior, meaningful hand-derived
  tests, exact values/provenance, ownership, configuration/bounds and evidence honesty.
- Do not demand9C/11B implementation or deferred nonblocking observations now.
  Distinguish blockers, nonblocking observations and unverified live/future gates.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase9B repair round1.
2. Findings with severity,path:line,evidence,impact,owner,acceptance,blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A COMPLETE NEXT PROMPT in one fenced block:
   APPROVE: append verdict verbatim to review.md under Subphase9B repair round1;
   confirm user has committed approved9B, otherwise ask/wait, no commit/push
   absent explicit user instruction. Record commit as9Cbase. Start ONLY9C on
   user's next prompt with bundled Step0questions and wait for answers. Preserve
   original ten decisions,9Bdefaults,N2-N9,O1-O10. Live9Csmoke needs separate
   written approval+dollarcap. Return complete reviewer prompt; never launch
   reviewer and stop after only that subphase.
   REQUEST-CHANGES: append verdict verbatim/log findings, route only blockers
   to owning specialist, rerun affected targets/fullJDK17check, retain exact
   logs/hashes/sourcebeforeafter, return complete9B repairround2 recheck prompt
   and stop. Do not start9C; nonblockers logged but not required.

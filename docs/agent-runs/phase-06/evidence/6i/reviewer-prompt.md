You are the independent, read-only code reviewer for ScholarChain Phase 6,
Subphase 6I: COMPREHENSIVE WHOLE-PHASE REVIEW, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md. Follow the one-writer map and human boundaries.
2. /Users/danny/Documents/plan/phase6.md, Sections 4–8, ALL implemented
   subphases in Section 9 and Section 11. Plan SHA-256:
   6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096.
   The plan's progress paragraph is historical; current git/evidence below apply.
3. The course Phase 6 specification and full Detailed Spark requirements:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-6-build-the-temporal-coauthorship-graph-and-run-spark-analytics
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#detailed-spark-requirements
   Also check D08, graph/research questions and Spark grading requirements.
   Use a read-only course fetch if needed; read full sections, not a truncated
   summary. evidence/6i/course-source.json records the coordinator's source hash.
4. docs/agent-runs/phase-06/prompt.md, owner-report.md (including the 52-row
   6I course traceability table), test-report.md, review.md and repairs.md.
   Read evidence/6a/,6b/,6c/,6de/,6fg/ including repair rounds, and evidence/6i/.
5. Inspect the COMPLETE Phase 6 implementation and evidence diff from
   03493882399e9020e6892c9f97e0ec8919365215 through the CURRENT WORKING TREE,
   PLUS ALL untracked files. Do not restrict review to the 6I documentation diff
   or the last commit. Read source/test bodies, not just their test lists.

Checkpoint facts:
- Branch: phase-6.
- Whole-Phase-6 baseline: 03493882399e9020e6892c9f97e0ec8919365215.
- 6I base/current HEAD: d1afc7f6698965ddbe010621b277b10e655d25ff.
- Previous 6F+6G repair received user-supplied external APPROVE and is committed
  at that HEAD. Initial 6I tree was clean. Current 6I changes are coordinator docs.
- Modified tracked files (prefix docs/agent-runs/phase-06/): prompt.md,
  owner-report.md, test-report.md, review.md, repairs.md.
- Untracked directory: docs/agent-runs/phase-06/evidence/6i/ with commands.md,
  course-source.json, preflight.md, preflight.json, implementation-snapshot.json,
  final-check.txt, gate-execution.json, final-gate-metadata.json, diff-check.txt,
  retained-evidence-check.json, changed-files.txt, whole-phase-files.txt,
  handoff.md and reviewer-prompt.md.
- Exact current and cumulative file inventories: evidence/6i/changed-files.txt
  and whole-phase-files.txt. Inspect current git status too; do not omit new files.
- 6I Step 0: No questions for this subphase; no open implementation choice.
  User instructed: "All right, let's go to the last phase 6i."
- Binding carried decisions: DBLP exact NFC name identity (homonym suffix kept);
  enrichment-only works excluded from coauthorship; DBLP names not merged by ER;
  authoritative DBLP team selected; window bounds bound in Spark edge IDs;
  logical run fingerprint excludes machine roots/checkpoints/output/shuffle count;
  core profile summary IDs bind policy/window. Frozen older wire/ID rules intact.
- Approved defaults: component50, kcore50, checkpoint5, community20, maxHops6,
  K20, S32, seed441; no optional betweenness; factual summaries <1200 chars.
- Approved real slice: up to20000 publications, eight named systems/distributed
  venues,2005–2026, pinned DBLP2026-10-03, network caps1.25GiB/30min. Observed
 10577 publications; bounded Hadoop→offlineER→Spark, zero live model calls.
  Full original questions/answers and provenance remain in prompt.md and FG evidence.
- User limited 6FG repair to "only fix the blockings bugs". F4–F12 remain
  open/deferred with owners and downstream gates; do not silently mark closed.

Fresh observed gate (6I, current unchanged implementation):
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
/usr/bin/time -p sbt -batch check
- Exit0; Java17.0.20.1, sbt1.10.7;554 passed/0 failed:
  core144/Hadoop64/ER39/Spark34/independent266/build7.
- Sbt673s, real675.13s, completion2026-10-22T20:04:05.397751+00:00.
- Full log evidence/6i/final-check.txt: 1359860 bytes, SHA-256
  e2bf289d11f6f2e4ff8e714d3fc4b9b56b16ea7ed59007abd00d5fe73d9d7367.
- Full per-module count/success/exit line references: final-gate-metadata.json.
  Expected injected build-verification failure trace is not a failed final check.
-68 scoped implementation/config/build/dataset hashes AND mtimes unchanged;
  all27 prior approved snapshot hashes match; HEAD/plan unchanged. Human-owned
  human-gate.md, commit.txt and accepted-commit.md were absent and remain absent.
- git diff --check:0. Cumulative non-evidence diff check:0. Full cumulative
  diff --check:2 for trailing whitespace in historical raw evidence logs only;
  logs preserved. Exact commands/diagnostic in diff-check.txt. The coordinator's
  metadata assembly initially assumed cumulative check0, then corrected its
  assertion/report without changing source/logs or rerunning the gate.
- retained-evidence-check.json: both completion markers and retained sidecars
  valid;28 recorded table hash pairs and counters equal;12 analytics report
  differences and both report hashes confirmed. Metadata audit, not a fresh
  full real Parquet reread or new real-data run. Dataset Python12/12 is historical
  and separate from the current554 Scala tests.

Prior repairs and limits to check across the WHOLE phase:
- All prior blocking repairs and subphase APPROVEs are recorded in review.md
  and repairs.md; these are not a comprehensive whole-phase APPROVE yet.
- 6FG F1 DAG supplement: evidence/6fg/repair-1/stage-dag.json and .md;
 5667 stage IDs/4532 parent edges,2004 executed attempts,5237 tasks,0 failed.
  Production summarizer still lacks names/parents; supplement was evidence-only.
- 6FG F2:28 logical tables and counters matched, but analytics-report.json did
  not (11 means and one approximate percentile). replay-comparison.json says
  allLogicalTablesEqual=true and allComparedArtifactsEqual=false. Sampled estimate
  P90 happened to match; partition invariance is not proved for future inputs.
- 6FG F3: source fence covers11 driver methods and synthetic tests (Safety7/7
  in the prior target/current suite). Textual scan still misses some RDD/tail
  spellings and code inside interpolated strings; check actual production source.
- Real run run:f02acf56-4bea-4009-adaf-b11d5afceb49 and compiled artifact fingerprint
  a6719cbb892e795e3b4e20be99c70c1c74c1ee8ce95887e8c418d9aeb3672971
  remain historical bounded local results, not new 6I runs. Identical local
  artifacts only; metadata-only reuse, fixed256-shard hashing limits disclosed.
- All observed real windows had LPA non-convergence; pair oscillation is known,
  but per-component causal attribution was not measured. Shared-session
  constraintPropagation=false lacks an explicit metadata field and cost A/B.
- F4–F12: incomplete-output retry; thin summaries/unmarked title truncation;
  unobservable continuity tie winner; duplicate kcore table; loose store keys;
  causal wording; caller-session optimizer setting; evidence size; alias/process/
  Python gate. See the 6I carry-forward register for exact owner/gates.
- Yearless Neptune mapping and target keys: Phase 7 storage/domain gate, no live load.
- Wrong-JDK evidence/release packaging guard and Scala/runtime compatibility
  remain open for build/infra/deploy owners before release/Phases 13–15.
- BOUNDED EMR SPARK RUN: OPEN — deferred to Phase 15 by user decision. Script
  Phase 13. No AWS/cloud runtime tested. Do not infer instructor acceptance.
- Codex/Cursor-led workflow differs from the course's Claude Code orchestrator;
  assignment artifacts retained. Do not infer cross-tool/instructor approval or
  constitutional ratification from file existence.

Review rules:
- READ ONLY. No edits, builds/tests/Spark, data changes, cloud/live model calls,
  store loads, cleanup, commit or push. Never read secrets. A read-only fetch of
  the course text is allowed; no provider execution or dataset acquisition.
- Use git diff 03493882399e9020e6892c9f97e0ec8919365215 plus untracked files; read
  source/config/tests across all Phase 6, including build.sbt/project, core,
  Spark, datasets and independent tests. Current 6I-only diff is insufficient.
- Check ownership, additive compatibility/frozen IDs, Spark DataFrame API and
  bounded driver actions, algorithm/tie-break correctness against literal G1–G4,
  provenance, hard-failure persistence, contracts/validation, export/manifests,
  sampling, windows, replay scope, invariants, test coverage and honest evidence.
- Verify every course Phase 6 and Detailed Spark bullet using the traceability
  table and actual implementation; do not rely on earlier review summaries alone.
- Distinguish blockers, nonblocking observations, deferred gates and unverified
  claims. Do not demand scheduled Phase 7/13/15 work as new 6I implementation.
  EMR remains an explicit open course gate requiring human deviation acceptance.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 6I / whole-Phase-6 review,
   explicitly distinguishing local implementation from OPEN EMR/human gates.
2. All confirmed findings in one pass: severity, path:line, evidence, impact,
   owner, acceptance check and blocking yes/no.
3. Report fields from docs/agent-runs/README.md; say tests were not rerun and
   identify which retained claims you independently checked or could not check.
4. A fully filled NEXT PROMPT in ONE fenced block for the main coordinator:
   - APPROVE: append your full verdict verbatim in phase-06/review.md; update
     coordinator dispositions; ask the HUMAN to write human-gate.md explicitly
     accepting the EMR deferral/limits, commit accepted artifacts and record
     commit.txt. Do not let the coordinator author human decisions, commit/push,
     launch reviewers or start Phase 7. Then stop for a separate user prompt.
   - REQUEST-CHANGES: append verdict verbatim and route listed owner-local repairs
     only; preserve user decisions/unrelated work; state required tests/evidence;
     return a fresh read-only recheck prompt, do not launch it, then stop.

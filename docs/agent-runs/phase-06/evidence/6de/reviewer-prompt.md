You are the independent, read-only code reviewer for ScholarChain Phase 6,
Subphase 6D+6E, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Documents/plan/phase6.md — Sections 4–8 and merged Subphase
   6D+6E in Section 9. Plan SHA-256:
   6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096.
3. The course Phase 6 specification and Detailed Spark requirements:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-6-build-the-temporal-coauthorship-graph-and-run-spark-analytics
4. docs/agent-runs/phase-06/{prompt,owner-report,test-report,repairs}.md,
   their 6D+6E sections, and evidence/6de/.

Checkpoint facts:
- Branch: phase-6. Base SHA and unchanged current HEAD:
  8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4. Work is uncommitted.
- Modified tracked files:
  docs/agent-runs/phase-06/{prompt,owner-report,test-report,repairs}.md;
  modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsConfigLoader.scala;
  modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsValidation.scala;
  modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsContractSpec.scala;
  modules/spark/README.md.
- Untracked implementation/test files:
  modules/spark/src/main/scala/edu/uic/cs441/scholarchain/spark/Phase6DEJobs.scala;
  modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase6DEJobsSpec.scala;
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentPhase6DEGraphSpec.scala.
  Untracked evidence is under docs/agent-runs/phase-06/evidence/6de/.
- User Step 0 decisions: CC/k-core maxIterations=50, checkpointInterval=5
  with hard failure; maxHops=6, K=20, S=32 and fixed seeds; omit optional
  betweenness; prioritize selected-pair BFS and defer the separate S-source
  estimate if it is not a small addition. LPA retains its plan limit 20 and
  reports non-convergence. Config values are explicit; fixtures override
  sample counts and iteration limits for their stated cases.
- Owners: Spark source/module tests/README by spark-engineer; tests/** by
  test-engineer; prior F5 core hardening by domain-engineer; evidence/reports
  by coordinator. Coordinator executed the test owner's requested automatic
  formatter for the last independent test addition; this is disclosed.

Commands and observed results:
- JDK 17 Spark targeted:
  sbt -batch 'sparkAnalytics/scalafmt' 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/testOnly *Phase6DEJobsSpec'
  exit 0, 9/9; module-predecessor-targeted.txt.
- JDK 17 independent targeted, with Phase 4 SBT_OPTS:
  sbt -batch 'independentTests/Test/scalafmt' 'independentTests/Test/scalafmtCheck' 'independentTests/testOnly *IndependentPhase6DEGraphSpec'
  exit 0, 10/10; independent-predecessor-targeted.txt.
- Final full gate environment:
  JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  PATH=$JAVA_HOME/bin:$PATH
  SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml
  /usr/bin/time -p sbt -batch check
  exit 0; 527/527 (core 143, Hadoop 64, ER 39, Spark 24, independent 250,
  build verification 7); sbt 565 s, real 567.12 s.
- Full log: evidence/6de/final-check.txt, 285463 bytes, SHA-256
  bd8b9a28348839769b5410364c3f7893fe37bb1c871eac27d7595fba75dbca34.
  Header: sbt 1.10.7, Homebrew Java 17.0.20.1; exit=0 at line 2793.
- git diff --check exited 0. source-check.txt retains source mtimes and API
  scans; only the two allowed BoundedActions collect sites matched.
- commands.md and test-report.md record exact commands and intermediate
  failures. The earlier full check was stopped (exit 143) after a BFS tie
  mismatch was found; superseded-check.txt is not a passing gate. The fix
  and separate module/independent distinguishing fixtures precede the final
  targeted and full gates. Expected injected build-probe errors are not
  gate failures.

Scope and limitations:
- Jobs 3–8 are distributed DataFrame builders over the committed 6C result.
  Publishing CLI/export, durable event-log summarizer, final physical-plan
  publication, persisted failures, bounded real-data run and replay belong
  to 6F+6G. Current module logs include fixture physical plans.
- pathLengthEstimates is empty by the approved schedule choice. No sampled
  distance or betweenness result is claimed. LPA can oscillate; bridges are
  partition-dependent.
- Prior 6B F5 bridge/community/path/config invariants were hardened now;
  semantic-summary entity-kind validation remains due before 6F Job 10.
- 6DE does not consume 6C diagnostic counters; prior 6C N findings remain
  routed to their named 6F+6G gates in repairs.md. Frozen wire fields and ID
  formulas were preserved. No build/Hadoop/ER behavior was changed.
- No AWS or live model calls, commit, push or reviewer launch occurred.
  EMR script/live gates moved to Phases 13/15 under the updated plan.

Review rules:
- Read-only: do not edit, build, test, run Spark, call AWS or model providers,
  change data, commit or push. Never read secrets.
- Inspect git diff 8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4 AND untracked files.
  Report all confirmed findings in one pass.
- Check ownership, DataFrame/API and bounded-driver rules, metric meanings
  and evidence caps, components/isolates, h-index coreness, BFS predecessor
  tie-breaking and support-backed hops, LPA votes/ties/convergence, bridge
  definitions, seeded sampling, provenance, invariants/counters, preserved
  contracts, hand-computed tests, README accuracy and retained evidence.
- Do not demand work assigned to 6F+6G, Phase 7, Phase 13 or Phase 15; list
  those as future gates. Distinguish blockers, observations and unverified
  gates. Do not approve implementation you authored.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 6D+6E.
2. Each finding: severity, path:line, evidence, impact, owner, acceptance
   check, blocking yes/no.
3. All report fields from docs/agent-runs/README.md.
4. One fenced, copyable NEXT PROMPT for the coordinator:
   - APPROVE: append this verdict verbatim under Subphase 6D+6E in review.md;
     confirm the user committed this subphase (ask if not); then start ONLY
     6F+6G with Step 0 questions, and finish with a Section 11 reviewer prompt.
   - REQUEST-CHANGES: append the verdict verbatim and register findings;
     route blockers to their named owners; rerun affected tests and the full
     JDK 17 check on a stable tree; return a read-only recheck prompt.
   In either case: no reviewer launch, no agent commit/push, no chaining into
   a further subphase. Stop and end the turn after the authorized work.

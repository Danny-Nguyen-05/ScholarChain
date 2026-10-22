# Phase 6 external reviews

## Subphase 6A — user-supplied external review

VERDICT: REQUEST-CHANGES for Subphase 6A

Most of 6A holds up against the code and the logs: the Java 17 guard, the Spark test fork, the smoke test, the job JAR, ownership and the reported test counts. One build-wiring gap blocks approval: independentTests can see Spark classes but cannot start Spark on JDK 17. That breaks the 6C–6F test-engineer lane.

Findings

F1 — High — BLOCKING — independentTests cannot run Spark on JDK 17
- Where: build.sbt:51-61; claim at docs/agent-runs/phase-06/owner-report.md:19.
- Evidence: Only sparkAnalytics sets Test / fork := true and the --add-opens options (build.sbt:79-80). independentTests gets Spark and scala-reflect on its classpath but sets neither option, so its tests run inside the sbt JVM. That JVM has only -Xmx2G -Xss4M from .sbtopts.
  - Spark 3.5 on JDK 17 needs those opens (for example java.base/sun.nio.ch) when a SparkContext starts.
  - The plan asks for this wiring in 6A so test-engineer can write independent Spark tests in 6C–6G.
  - The report says the build owner "observed Spark classes and spark-sql_2.13:3.5.4 on its test classpath", but no retained log shows this. Searching evidence/6a/*.txt finds no independentTests classpath output.
- Impact: The first independent Spark test in 6C will fail at session start or come back as BLOCKED-ON build-engineer. It also leaves a report claim with no retained evidence.
- Owner: build-engineer for the settings; coordinator for the evidence.
- Acceptance check:
  a. independentTests runs Spark tests in a forked JVM with ScholarChainBuild.sparkTestJavaOptions. Forking the whole project and forking only Spark suites through testGrouping are both acceptable.
  b. The 233 existing independent tests still pass. A forked test's working directory defaults to the project base (tests/), so relative paths may need Test / baseDirectory or a grouping approach.
  c. Retained output from show independentTests/Test/fork, show independentTests/Test/javaOptions, and a filtered export independentTests/Test/fullClasspath showing spark-sql_2.13-3.5.4 and scala-reflect-2.13.14.
  d. The full JDK 17 sbt -batch check passes.
  e. Optional: a minimal SparkSession start probe under tests/**, written by test-engineer, only if the user approves adding that owner to this repair round. Otherwise, disclose that the first real Spark run in independentTests happens in 6C.

F2 — Medium — nonblocking (recommended this round; required before 6H) — two SLF4J providers in Spark tests and in the job JAR
- Where:
  - project/ScholarChainBuild.scala:397 adds logbackClassic to every module, and :86-92 does not exclude it.
  - evidence/6a/final-check.txt:946-950: SLF4J(W): Class path contains multiple SLF4J providers ... Actual provider is ... LogbackServiceProvider.
  - evidence/6a/spark-job-jar-contents.txt:613-614,756: the JAR contains 667 ch/qos/** entries, META-INF/services/org.slf4j.spi.SLF4JServiceProvider and LogbackServletContainerInitializer.
- Impact:
  - Tests: the forked test JVM does not receive SBT_OPTS, so logback runs without a config and emits Spark and Hadoop DEBUG output. The smoke spec alone fills final-check.txt lines 945–13262, about 1.2 MB. This will grow quickly as 6C–6F add Spark tests.
  - Cluster: the JAR ships a provider that competes with Spark's log4j2 binding.
  - The 6A report's JAR summary does not mention logback.
- Owner: build-engineer. If a module-local modules/spark/src/test/resources/logback-test.xml is chosen instead, spark-engineer owns that file.
- Acceptance check: the forked Spark test output shows a single SLF4J provider and no DEBUG flood. The JAR listing has no ch/qos/logback/ entries and no org.slf4j.spi.SLF4JServiceProvider service file, or a recorded decision explains why they stay.

F3 — Medium — nonblocking (6H feasibility) — the bundled Scala stdlib may not match a Spark 2.13 runtime
- Where: spark-job-jar-contents.txt (3,549 scala/** entries; library.properties at line 1327); project/Versions.scala:27-28; emr-compatibility.md:9-17.
- Evidence: The JAR bundles scala-library 2.13.14 and the scala3-library. Any Spark-on-2.13 runtime ships its own scala-library. Spark 3.5's Scala 2.13 build profile uses an older 2.13 patch release; I did not verify this against a distribution. By default Spark's own jars are searched before the application JAR, so Spark's scala-library wins. Scala 2.13 is backward compatible across patch releases, not forward compatible. The memo covers only the 2.12-versus-2.13 mismatch.
- Impact: Even the custom-distribution or custom-image fallbacks can fail with linkage errors.
- Owner: infra-engineer (memo and 6H plan); build-engineer (packaging).
- Acceptance check: before 6H, the memo or 6H plan states how scala-library versions will be aligned (matching distribution, userClassPathFirst, or shading). The live check stays an open 6H gate.

F4 — Low — nonblocking — the wrong-JDK evidence was captured on an earlier tree
- Where: evidence/6a/jdk-guard.txt:11 shows build.sbt:127; the guard now sits at build.sbt:130-131.
- Evidence: The log is timestamped 20:59:55. That is before the 21:02 scala-reflect fix and the final check. The log contains neither the JDK 27 JAVA_HOME nor an exit-code line.
- Impact: The behavior is very likely unchanged (the guard is first in checkTask and markTestRun is last), but "exit 1" is not in the retained log.
- Owner: build-engineer reruns; coordinator retains.
- Acceptance check: rerun the wrong-JDK sbt -batch check on the repaired tree. Record the exact JAVA_HOME, echo exit=$?, and the .claude/.last-test-run modification time before and after (it must not change).

F5 — Low — nonblocking — work-order and model provenance
- Where: docs/agent-runs/phase-06/prompt.md:3-15; owner-report.md:7.
- Evidence: prompt.md cites the external plan by path only. The plan file's SHA-256 when I reviewed it was bd6ecba68004562a39338293e9e9c1ce9af094614b3efdb7ab8accb7229c2fa8. No tool name or version, and no coordinator model, is recorded. docs/agent-runs/README.md asks for the toolchain and model versions needed to replay a run.
- Owner: coordinator.
- Acceptance check: prompt.md records the plan hash and the tool and model information the coordinator can observe, and marks what is unavailable.

F6 — Low — nonblocking — packaging is not guarded by the JDK check
- Where: build.sbt:199-203.
- Evidence: sparkJobJar and packageJobs do not run checkJava17. A release JAR could be compiled on a newer JDK and link to APIs that do not exist on EMR's Corretto 17.
- Owner: build-engineer.
- Acceptance check: packaging runs the Java 17 guard, or the risk is documented.

F7 — Info — future scope (6C) — smoke-session settings differ from plan §7.12
- Where: SparkSmokeSpec.scala:23-29.
- Evidence: It uses shuffle.partitions=2 instead of 4 and sets no UTC session time zone. The warehouse path defaults to modules/spark/spark-warehouse (final-check.txt:1136).
- Impact: Fine for a 6A smoke test. The shared harness built in 6C must apply §7.12.
- Owner: spark-engineer.

F8 — Info — misleading wording
- Where: project/ScholarChainBuild.scala:37 says "with Spark classes"; SparkJobJarSpec.scala:10 says "Spark classes".
- Evidence: Both mean the sparkAnalytics project's own classes, but the wording reads like it contradicts the Spark exclusion.
- Owner: build-engineer.

F9 — Info — evidence size
- Where: final-check.txt (1.2 MB) and spark-reflect-targeted.txt (961 KB).
- Evidence: Both are mostly DEBUG output caused by F2. Plan §6.10 asks for lean evidence.
- Owner: coordinator. Keep the full final-gate log. Consider trimming intermediate logs to excerpts once F2 is fixed.

Verified (no finding)
- Ownership: every edit is inside its owner's paths (build files → build-engineer, smoke spec → spark-engineer, memo → infra-engineer, reports → coordinator). Nothing was touched in Phase 5, core, Hadoop, entity resolution, Terraform or .claude/**.
- Check ordering: checkJava17 runs first in checkTask (build.sbt:141) and markTestRun runs last (:185).
- Spark test fork: fork, -Xmx2g, the UI disabled, and the --add-opens set (ScholarChainBuild.scala:39-60). The log shows Java version 17.0.20.1 and Successfully stopped SparkContext (final-check.txt:13255).
- Smoke spec: it asserts exact hand-computed rows through join, groupBy, row_number over a window, a Parquet round trip and an eager checkpoint() to a temporary directory. The spec cleans up afterwards.
- Spark API rule: no RDDs, implicits, Encoders or GraphX. sparkContext is used only to set the checkpoint directory, in test code.
- Test counts: 129+64+39+1+233+7 = 473 (final-check.txt lines 151, 893, 943, 13265, 14424, 14466), real 424.08. The baseline count of 469 also matches its log.
- JAR: zero org/apache/{spark,hadoop}/ entries, 608 core entries, 57 under scala/reflect/, 5,467 entries in total. The SHA-256 I computed matches 10d4649b…a73a (11,120,444 bytes).
- git diff --check: exit 0.

Not verified by me: the EMR documentation citations in emr-compatibility.md (a read-only review cannot call any provider), and whether stock EMR can run this job (correctly disclosed as an open gate).

Report fields

STATUS: COMPLETE (review) — VERDICT REQUEST-CHANGES for Subphase 6A
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Independent read-only review of Subphase 6A, base/HEAD 03493882399e9020e6892c9f97e0ec8919365215, branch phase-6
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only only — git rev-parse HEAD; git status --short; git diff [--stat|--check] 0349388…; cat/sed/grep/awk/wc over the 6A diff, untracked files, reports and evidence/6a/*; find/ls/stat on modules/spark and tests; shasum -a 256 on /Users/danny/Documents/plan/phase6.md and modules/spark/target/spark-job_3-0.1.0-SNAPSHOT.jar. No sbt, Spark, AWS or provider calls.
TEST RESULTS: Not run by the reviewer. The retained logs support 469 baseline / 473 final passes (0 failed), the smoke test pass, build verification 7/7, and the wrong-JDK failure message.
VALIDATION RESULTS: JAR hash and listing counts match the report; diff --check exit 0. F1 (blocking): Spark cannot start in independentTests and the classpath claim has no retained evidence. F2–F6 nonblocking; F7–F9 informational.
ASSUMPTIONS: Spark 3.5 on JDK 17 requires Spark's --add-opens set when a SparkContext starts; in-process sbt tests do not get it. The Scala 2.13 patch level of Spark distributions is stated from Spark's build profile and was not verified here.
RISKS: The 6C independent-test lane is blocked without F1. Log volume grows with every Spark test (F2). EMR or custom-runtime linkage stays unproven (F3, memo).
MANUAL ACTION REQUIRED: User routes the repair round; decides whether test-engineer may add a minimal independent Spark probe in 6A; does not commit 6A until it is approved.
BLOCKED-ON OWNER: build-engineer (F1); coordinator (F1 evidence)
BLOCKED-ON EVIDENCE: build.sbt:51-61 has no Test/fork or javaOptions for independentTests; owner-report.md:19 classpath claim has no retained log
NEXT GATE: 6A repair round, full JDK 17 sbt check, then a user-run 6A recheck review

## Subphase 6A repair round 1 — user-supplied external review

VERDICT: APPROVE for Subphase 6A repair round 1

The three repairs hold up against the code and the retained logs. F1 is fixed and proven at runtime, and so is F2. F3's memo is accurate and keeps what was observed separate from what is proposed for 6H. No new blocking finding came up. The remaining items are nonblocking and deferred under the user's F1–F3 scope.

Disposition of F1–F9

F1 — High — CLOSED. independentTests can now start Spark on JDK 17.
- ScholarChainBuild.scala:408-415 defines sparkTestSettings, and build.sbt applies it to both independentTests and sparkAnalytics. The settings turn on a forked test JVM, add Spark's 15 --add-opens options plus -Xmx2g, set the test working directory to the repository root, and add the shared test logging resource.
- independent-classpath-proof.txt (21:40:39, after the last build edit at 21:40:24) shows true, all 15 options, the sparkAnalytics classes, spark-sql_2.13-3.5.4, scala-reflect-2.13.14 and log4j-slf4j2-impl.
- The new probe IndependentSparkSessionSpec.scala:7-20 starts local[1], checks range(3).filter("id > 0").count() == 2 and stops the session in finally. It passed (final-check.txt:1014-1018).
- The independent suite passed 234/234 (final-check.txt:2108-2110), so the 233 existing tests still pass with the new working directory.
- There is no IllegalAccessError or InaccessibleObjectException in the log.

F2 — Medium — CLOSED. One logging provider, and none bundled in the JAR.
- The Spark test projects drop Logback (ScholarChainBuild.scala:409) and share a WARN-level log4j2 resource (project/spark-test-resources/log4j2-test.properties).
- The packaging excludes the ch.qos.logback group and logback-* jars, and its merge rules discard the SLF4J provider service file (ScholarChainBuild.scala:63-71, 80-81).
- SparkJobJar.scala:12-17 rejects those paths, and SparkJobJarSpec tests all four rejection cases.
- The final log has 0 DEBUG lines and no SLF4J output at all, and shrank from 1.2 MB to 244,600 bytes.
- The JAR listing has 4,798 entries. None are under org/apache/{spark,hadoop}/ or ch/qos/logback/, and there are no META-INF entries. I hashed the JAR myself and got a30b9f1c…04d7e0, which matches the report.

F3 — Medium — CLOSED as research; the runtime check stays an open 6H gate.
- emr-compatibility.md:21-27 and f3-research.md keep three things separate: Spark's upstream Scala 2.13 build profile (2.13.8), the patch level observed in the local JAR (2.13.14), and the alignment, class-origin and bounded-runtime checks proposed for 6H.
- The memo corrects my original F3 wording. It cites Scala's policy that 2.13 patch releases are forward and backward binary compatible through 2.13.18, so the patch difference by itself is not a defect. I could not check that citation, because this review makes no provider calls, but the memo correctly calls the difference a validation risk rather than a failure.
- No runtime was selected or run.

F4 — Low — OPEN, nonblocking, deferred by the user. The wrong-JDK log still predates the final tree. Rerun it before any release, at the latest in 6H.

F5 — Low — OPEN, nonblocking, deferred. Work-order hash and model provenance are still missing. The coordinator can record the plan hash at the start of 6B.

F6 — Low — OPEN, nonblocking, deferred. sparkJobJar still skips the Java 17 guard. Close this before 6H packaging.

F7 — Info — moved to 6C. One addition: Spark tests now run with the repository root as the working directory. So the 6C shared harness must set spark.sql.warehouse.dir, along with the other §7.12 settings. Otherwise a default spark-warehouse/ lands at the repo root, and .gitignore does not cover it. None exists now.

F8 — Info — OPEN, deferred. The "Spark classes" wording is still at ScholarChainBuild.scala:37 and SparkJobJarSpec.scala:10.

F9 — Info — mostly resolved by F2. The new logs are lean. The old 6A logs (1.2 MB and 961 KB) are still retained.

New findings this round

R1 — Low — nonblocking — two classpath claims overstate the retained evidence.
- Where: test-report.md:68 and owner-report.md:49.
- Evidence: test-report.md:68 says there was "no Logback JAR in the retained full export". owner-report.md:49 says the test working directory "is the repository root". But repair-1/independent-classpath-proof.txt is a 24-line filtered excerpt. It has no command header, no full export, and no Test / baseDirectory output.
- Why it's minor: both claims are still supported indirectly. The setting is at ScholarChainBuild.scala:411, the final log has no SLF4J output, and the 233 tests that use relative paths pass.
- Owner: coordinator.
- Acceptance check: either reword the two sentences to "filtered excerpt; supported by build source and log", or retain the unfiltered export independentTests/Test/fullClasspath and show independentTests/Test/baseDirectory output with its command lines.

Verified, no finding:
- Ownership: every change stays with its owner. The build engineer owns project/** (including the shared test resource, which avoids a two-owner collision) and build.sbt. The test engineer owns the approved probe in tests/**. The infra engineer's research is read-only and recorded by the coordinator. No Phase 5, core or human-owned files changed.
- Check order: checkJava17 still runs first, and markTestRun updated .claude/.last-test-run at 21:48:25, when the check finished.
- Test totals: 129+64+39+1+234+7 = 474, with 0 failed and real 418.33. The injected-failure trace at final-check.txt:2120-2139 comes from the build-verification self-test that is expected to fail, not a gate failure.
- Stable tree: every implementation file was last changed by 21:40:24. The final check started at about 21:41:27.
- Spark API rule: the probe uses only SparkSession, range, filter and count.
- git diff --check: exit 0.

Not verified: the cited AWS, Scala and Spark documents (this review makes no provider calls). EMR or custom-runtime compatibility, and any live run, remain open 6H gates.

Report fields

STATUS: COMPLETE (review) — VERDICT APPROVE for Subphase 6A repair round 1
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Read-only recheck of 6A repair round 1 (F1–F3 per user scope), branch phase-6, base/HEAD 03493882399e9020e6892c9f97e0ec8919365215, 6A uncommitted
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only only — git rev-parse HEAD; git status --short; git diff 0349388… (build.sbt, project/*.scala); git stash list; git reflog -5; cat/sed/grep/wc/stat on new and changed sources, repair-1 evidence, reports, review.md, repairs.md, emr-compatibility.md; ls for spark-warehouse/metastore_db; ps; shasum -a 256 on modules/spark/target/spark-job_3-0.1.0-SNAPSHOT.jar. No sbt, Spark, AWS or provider calls.
TEST RESULTS: Not run by the reviewer. Retained logs show 474 passed / 0 failed (129/64/39/1/234/7), real 418.33, the independent Spark probe passing, and the smoke spec passing.
VALIDATION RESULTS: F1 and F2 closed with runtime evidence; F3 closed as research with the 6H gate open. JAR SHA-256 a30b9f1c373febf3b245911ae533d582d15fadf52074dda287b40d75b504d7e0 matches; listing clean. R1 (Low): two report claims overstate the filtered classpath excerpt.
ASSUMPTIONS: The Scala 2.13 patch compatibility citation is taken as stated in the memo, not verified by the reviewer.
RISKS: F4/F6 are open before any release packaging (6H). The F7 harness settings, including the warehouse dir now that the working directory is the repo root, are due in 6C. EMR/custom runtime linkage is unproven.
MANUAL ACTION REQUIRED: User commits approved 6A (implementation, reports and evidence) on phase-6 before 6B.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: User commit of 6A, then Subphase 6B Step 0

## Subphase 6B review — user-supplied external review

Subphase 6B review (read-only, independent)

1. VERDICT: REQUEST-CHANGES

There are three blocking findings. All are small, owner-local repairs in modules/core/** and modules/spark/README.md. Ownership, the additive wire compatibility, the yearless and entry/exit representation, provenance and the evidence claims check out.

2. Findings

F1 — High — BLOCKING — ResearcherMetricsDetail validation drops the frozen metric invariants

- Where: modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsValidation.scala:62-93, compared with DomainValidation.scala:1343-1395.
- Evidence: The companion check enforces only non-negativity, finiteness, W == T, the zero-publication rule, ID sorting and tie ≥ retained. Unlike the frozen ResearcherMetrics rules, it does not check:
  - A ≈ T/P (same tolerance)
  - C ≤ T, M ≤ C, M ≤ T
  - T == 0 ⇔ C == 0 ⇔ M == 0
  - T ≤ P·M (BigInt)
  - coreness ≤ C

  The new fields have no rules either: maxTeamWorkIds should be nonempty and maxTeamWorkTieCount between 1 and P whenever P > 0. With the current code, the example row with averageCoauthorsPerPaper = 99.0, distinctCoauthorCount = 5, coreness = Some(9) or maxTeamWorkIds = Vector() all pass. modules/core/README.md:166 says this method "validates each new record locally".
- Impact: The core Phase 6 metric contract is weaker than the frozen one it accompanies. Wrong P/C/T/A/M rows from 6D would pass the contract gate.
- Owner: domain-engineer
- Acceptance check: The companion check enforces every frozen consistency rule plus the tie and ID rules above. There is one negative test per rule. The existing wire example still validates.

F2 — Medium — BLOCKING — The summary-ID formula is inconsistent across plan, docs, example and validator

- Where:
  - Plan phase6.md:353: summaryId via StableIds.chunkOrProfileId
  - modules/core/README.md:168 and modules/spark/README.md:97: sparkAnalyticsId supplies summary IDs
  - SparkAnalyticsContractSpec.scala:124-128 and wire/spark-semantic-summary.json: use chunkOrProfileId (profile:20fe…)
  - SparkAnalyticsValidation.scala:311-314: accepts either form
- Impact: This misses the 6B Done-when "README design sections match the contracts", and there is no single deterministic summary-ID rule. There is a further issue: as called in the example, chunkOrProfileId(entity, "graph-v1", type, None, text) does not bind the window. The same entity with identical text in two windows gets the same summaryId. Downstream, EvidenceItem.chunkId (DomainValidation.scala:538) parses only chunk/profile IDs, which matters for Phase 8 citation.
- Owner: domain-engineer (contract, example, core README) and spark-engineer (modules/spark/README.md). The choice is the user's.
- Acceptance check: One formula is chosen and documented in both READMEs. The validator accepts only that form, and the example is regenerated. A test shows the same entity and text in two windows produces different IDs.
- Recommended default: Keep chunkOrProfileId (plan §7.10, Phase 8 compatible), with the policy and window bound into sourceVersion.

F3 — Medium — BLOCKING — Missing feature tests for the user-approved 6B-1 and 6B-2 behavior and G1 coverage

- Where: SparkAnalyticsContractSpec.scala:209-216 and 287-333.
- Evidence:
  - IDs: No test shows NFC equivalence (precomposed "é" vs "e\u0301" give the same ID). No negative tests for parseResearcherId on bad researcher:dblp: forms (63 hex digits, uppercase hex, an extra : segment), or for an unknown sparkAnalyticsId kind.
  - Config: Every rule at SparkAnalyticsConfigLoader.scala:115-161 is untested: duplicate windowId, reversed bounds, overlap, gap, an open bound mid-sequence, duplicate comparisonOrder, and a bad endpointKind. Only maxHops = 0, empty windows, an unknown field, an LF name and a ${…} root are tested.
  - G1: Only A's metrics, C's bridge and the A–G component are shown. J's solo row (P=1, C=T=M=W=0, maxTeamWorkIds=[w8], coreness 0, singleton component) and the A→H no-path row are not.
- Impact: This fails the definition of done ("every behavior change has feature tests") for the ID and window rules the user explicitly approved.
- Owner: domain-engineer
- Acceptance check: The tests above exist and pass inside the JDK 17 sbt -batch check.

F4 — Medium — non-blocking (record now; repair before 6E path evidence or Phase 7/8 consumers) — New edge IDs aren't accepted by existing consumers, and the plan deviation isn't recorded

- Where: StableIds.scala:308-328; DomainValidation.scala:1525-1530; Records.scala:238-243; plan phase6.md:254.
- Evidence:
  - EvidenceItem(CoauthorEdge).edgeLocatorId accepts only graph-edge: or coauthor-edge:, so spark-coauthor-edge: IDs from PathHop can't be cited.
  - CoauthorshipProperties requires integer years, so a yearless all-years edge has no GraphEdge (Neptune) form.
  - The plan said edgeId comes from StableIds.coauthorEdgeId. The change is justified and documented in modules/spark/README.md:25, but neither prompt.md nor owner-report.md lists it as a plan deviation.
- Owner: domain-engineer (additive locator acceptance and a test, or a documented open item); the coordinator records the deviation in repairs.md.
- Acceptance check: The deviation is recorded, and compatibility is either implemented with a test or routed with a named owner and gate.

F5 — Low — non-blocking — Other single-record invariants are missing

- Where: SparkAnalyticsValidation.scala:95-254; SparkAnalyticsConfigLoader.scala:146.
- Evidence:
  - Bridge (ResearcherBridgeMetrics):
    - crossCommunityDegree == 0 should imply participationCoefficient == 0.
    - crossCommunityWeight should be ≥ crossCommunityDegree.
  - Community records:
    - CrossCommunityEdge.summedWeight should be ≥ edgeCount.
    - A CommunitySummary with converged = true should have finalChangedCount == 0.
  - Path (PathEvidence with status Found): it accepts hopCount > maxHops, source == target and repeated nodes.
  - Config: benchmark self-pairs are compared as raw strings, so " A"/"A" passes even though both map to one researcher.
  - Context: windowId is only checked as non-blank, not against the config pattern.
- Owner: domain-engineer
- Acceptance check: Folded into the F1 repair with negative tests, or explicitly deferred in repairs.md.

F6 — Low — non-blocking — Window labels aren't bound to their bounds

- Where: StableIds.scala:250-265 and 308-324; SparkAnalyticsConfigLoader.scala:118-130.
- Evidence: Edge, component and community IDs hash only the windowId label. Config accepts "2015-2019" with bounds 2010–2014. The frozen coauthorEdgeId binds numeric bounds.
- Impact: Within a run this is safe, because the run ID includes the config fingerprint. Across runs, consumers keyed by window label could mix up differently defined windows.
- Owner: domain-engineer
- Acceptance check: Either bind the bounds into the ID material or validate label-to-bounds consistency, or document the limitation.

F7 — Low — non-blocking, future gate 6F — The deterministic run ID isn't representable yet

- Where: StableIds.scala:64-65; modules/spark/README.md:9; SparkAnalyticsConfig.scala:30-31.
- Evidence:
  - SparkRecordContext.runId must match run:<uuid-v4>. Hadoop uses random v4 IDs (HadoopPrepPipeline.scala:374). The README promises a deterministic hash, and no core helper defines how a hash becomes a valid run ID.
  - The config fingerprint covers roots, checkpointDirectory and shufflePartitions. A local run and an EMR run of the same logical inputs would get different run IDs, so every row's runId would differ. The plan only lets partition counts and part-file names differ.
- Owner: domain-engineer before 6F. The user decides which fields form the logical fingerprint.
- Acceptance check: A domain-owned deterministic run-ID helper with tests, plus a recorded decision on the fingerprint scope.

F8 — Info — non-blocking, risk notes for later owners

- LoadManifest.windows must be nonempty even for node tables that have no window. targetMapping is untyped and not checked per target. This goes to the Phase 7 storage-engineer proposal.
- The rule "a window includes yearless works only when both bounds are absent" is stated in prose only (modules/spark/README.md:11), not in the SparkWindow scaladoc.
- 2020-2026 and since-2015 end at 2026, so DBLP works dated 2027 (forthcoming volumes) fall into all-years only. 6C should count them.

Verified and acceptable

- Ownership: writes are confined to modules/core/** (domain), modules/spark/README.md (spark) and docs/agent-runs/phase-06/** (coordinator).
- Additive changes: the frozen CoauthorEdge, ResearcherMetrics and their ID formulas are unchanged. parseResearcherId and supportedManifestConfig are widened additively.
- DBLP IDs: the formula matches the Step 0 answer. CanonicalResearcher validation lets a DBLP ID carry a validated ORCID.
- Collision guards: the LF-collision guard is present.
- Config: a strict unknown-field check; the fingerprint follows the HadoopPrepConfig precedent.
- Yearless edges: represented with absent first/last years and an optional support year.
- Temporal entry/exit: handled with presence flags and absent deltas.
- Path status: wire values found, no-path, exceeded-maxHops.
- Provenance: carried in SparkRecordContext / SparkLineage on every new record.
- Wire snapshots: 16 exist; every new record type has one, compared byte for byte, and they pin the ID formulas.
- Evidence: final-check.txt lines 156/158, 898/900, 948/950, 958/960, 2113/2115, 2155/2157, 2160 and 2161 match the claimed 135 + 64 + 39 + 1 + 234 + 7 = 480 passed, 0 failed, and real 418.74. The [error] lines at 2125–2144 are the injected check-probe self-test. The log header shows Java 17.0.20.1.

3. Report fields

STATUS: COMPLETE (review) — VERDICT REQUEST-CHANGES for Subphase 6B
OWNER: code-reviewer (independent, user-launched, read-only)
WORK ORDER: Read-only review of Subphase 6B on phase-6, base/HEAD
  bc1e4a17fc879b7aac254b28d83e78dbdd34e367, against AGENTS.md, CLAUDE.md,
  docs/agents.md, code-reviewer.md, docs/agent-runs/README.md, plan §§4–8 and
  6B, course Phase 6 + Detailed Spark requirements, and 6B evidence.
FILES CREATED: None.
FILES MODIFIED: None.
COMMANDS RUN: Read-only: git rev-parse HEAD; git status --short; git diff --stat
  and git diff bc1e4a1… (modules/, docs/); cat/sed/grep/wc on the 6B
  untracked files, core sources (StableIds, DomainValidation, Records,
  HadoopPrepConfig, CoreJson), project/Versions.scala, plan phase6.md and
  evidence/6b/*; WebFetch of the course README (Phase 6 and Detailed Spark
  requirements). One read-only grep was refused by the PreToolUse guard because
  its text named a protected path; it was re-run without that path. No build,
  test, Spark, AWS, provider, edit, commit or push.
TEST RESULTS: Not run by reviewer (read-only). Observed in retained log:
  480 passed / 0 failed (core 135, Hadoop 64, ER 39, Spark smoke 1,
  independent 234, build 7), [success] 417 s, real 418.74, Java 17.0.20.1.
VALIDATION RESULTS: 3 blocking findings (F1 metrics-detail invariants, F2
  summary-ID inconsistency, F3 missing feature tests); 5 non-blocking
  (F4–F8). Ownership, additive compatibility, provenance and evidence line
  claims verified.
ASSUMPTIONS: The course README's "Detailed Spark requirements" were read via
  WebFetch summary, not verbatim. Plan phase6.md taken at the recorded SHA-256
  bd6ecba6… (not re-hashed by the reviewer).
RISKS: F4 and F7 affect 6E/6F and Phase 7/8 if not tracked. The run
  ID and fingerprint scope need a user decision before 6F.
MANUAL ACTION REQUIRED: User chooses the summary-ID formula (F2) and decides
  F4–F7 disposition (fix now or defer with owner). Do not commit 6B yet.
BLOCKED-ON OWNER: domain-engineer (F1, F2, F3; F4–F7 if accepted);
  spark-engineer (F2 README alignment); coordinator (repairs.md, F4 deviation).
BLOCKED-ON EVIDENCE: Paths and lines in findings F1–F3 above.
NEXT GATE: 6B repair round 1, then a new user-run read-only recheck.

4. NEXT PROMPT

You are the main coordinator for ScholarChain Phase 6, Subphase 6B REPAIR ROUND 1,
in /Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-6.
Base SHA and HEAD: bc1e4a17fc879b7aac254b28d83e78dbdd34e367. 6B is uncommitted;
do not reset or discard it.

The external 6B reviewer returned VERDICT: REQUEST-CHANGES. First append the
complete reviewer output verbatim to docs/agent-runs/phase-06/review.md under a
"Subphase 6B review" heading. Create or extend docs/agent-runs/phase-06/repairs.md
with one row per finding F1–F8 (disposition, owner, evidence).

Step 0 — ask the user these questions, each with a recommended default, and wait:
1. F2 summary-ID formula. Recommended: StableIds.chunkOrProfileId (plan §7.10,
   compatible with EvidenceItem.chunkId), with policy and windowId bound into
   sourceVersion so identical text in two windows yields different IDs; the
   validator accepts only that form. Alternative: sparkAnalyticsId("summary", …).
2. F4–F7: fix now in 6B, or defer with named owner/gate? Recommended: fold F5
   into the F1 repair; record F4 as a plan deviation and add additive
   EvidenceItem acceptance of spark-coauthor-edge IDs with a test; defer F6 and
   F7 to a domain-engineer task before 6F, with the logical-fingerprint scope
   as a user decision recorded then.
3. Any other question you have.

Repairs (after answers), routed by docs/agents.md:
- domain-engineer (modules/core/** only):
  F1: make SparkAnalyticsValidation.check(ResearcherMetricsDetail) enforce every
      frozen ResearcherMetrics consistency rule (DomainValidation.scala:1343-1395,
      same tolerance) plus: P>0 ⇒ maxTeamWorkIds nonempty and 1 ≤ tieCount ≤ P;
      coreness ≤ distinctCoauthorCount. One negative test per rule.
  F2: implement the chosen summary-ID formula; regenerate
      wire/spark-semantic-summary.json; update modules/core/README.md:168;
      test window binding.
  F3: add tests for NFC equivalence (precomposed vs combining é), malformed
      researcher:dblp: forms, unknown sparkAnalyticsId kind, every config window
      rule (duplicate id, reversed, overlap, gap, open bound mid-sequence,
      duplicate comparisonOrder), invalid endpointKind, and G1 representability
      of J's solo row and singleton component and the A→H no-path PathEvidence.
  F5/F4 only if the user approves them in Step 0.
- spark-engineer (modules/spark/README.md only): align Job 10 (line 97) and any
  other text with the F2 decision; no code.
Keep all changes additive. No existing wire field or ID formula may change, and
no Phase 5, build, Hadoop or ER files change.

Gate: JDK 17 env and the Phase 4 SBT_OPTS logging config, `sbt -batch check`
on the stable tree, plus `git diff --check`. Retain the log under
docs/agent-runs/phase-06/evidence/6b/ (e.g. repair1-final-check.txt). Update the
6B repair sections of owner-report.md and test-report.md with exact commands,
exit codes, counts and any intermediate failures.

Then return a handoff packet and a new copyable read-only RECHECK reviewer prompt
covering F1–F8 dispositions, the repair diff against the same base SHA, and the
new evidence. Do not launch a reviewer, commit, push, or start Subphase 6C.
End with: "Subphase 6B repair round 1 is ready for review. I have stopped and
will not start the next subphase until I receive the next prompt."

## Subphase 6B repair round 1 recheck — user-supplied external review

Subphase 6B repair round 1 recheck (read-only, independent)

1. VERDICT: APPROVE

All three blockers (F1–F3) are fixed and covered by tests. The F4 repair the user asked for is correct and additive. The retained logs match every claimed count, and every source file was last modified before the final gate started. Two low, nonblocking observations remain. One of them changes when F6 and F7 must be resolved: during 6C, not 6F.

2. Findings and dispositions

Prior findings

F1 — CLOSED. SparkAnalyticsValidation.scala:62-127 now covers every frozen ResearcherMetrics rule:
- C ≤ T, M ≤ C, M ≤ T
- zero-agreement between T, C and M; T = 0 requires A = 0
- A ≈ T/P, using the same max(1e-12, 4·ulp) tolerance as DomainValidation.scala:1339-1341
- T ≤ P·M using BigInt; W == T; coreness ≤ C
- P = 0 requires every collaboration value to be zero

It also adds the new rules: when P > 0, maxTeamWorkIds is nonempty and the tie count is between 1 and P; when P = 0, there are no IDs and the tie count is 0. SparkAnalyticsContractSpec.scala has one negative case per rule, each asserting its exact message, plus a valid all-zero row and an invalid zero row with IDs.

F2 — CLOSED.
- StableIds.sparkSemanticSummaryId (StableIds.scala:357-374) calls chunkOrProfileId(entity, s"$policy:$window", summaryType, None, text). A policy or window value can't contain : or LF, so the sourceVersion is unambiguous.
- SemanticSummary gained policyVersion (SparkAnalyticsContracts.scala:207). This record is new in 6B, so no frozen wire changed.
- The validator recomputes the exact ID (SparkAnalyticsValidation.scala:~348-360), and "summary" was removed from the sparkAnalyticsId kinds.
- The wire example has been regenerated (profile:6c6a…). modules/core/README.md:168 and modules/spark/README.md:97 agree with it.
- Tests show the same text gives different IDs in different windows, and that a changed text, a changed policy or a summary: ID is rejected.

F3 — CLOSED. The tests now cover:
- NFC: "José" and "Jose\u0301" give the same ID
- malformed DBLP IDs: 63 hex digits, uppercase hex, an extra : segment
- unknown and summary analytics kinds
- config windows: duplicate ID, reversed bounds, overlap (2009), gap (2011), an open lower bound mid-sequence, duplicate comparisonOrder
- an invalid endpointKind
- G1: J's solo row (P = 1, everything else 0, [w8], tie count 1, coreness 0) with a singleton ComponentSummary, and A→H no-path evidence

F4 — CLOSED (citation compatibility). StableIds.scala:826-829 and DomainValidation.scala:1525-1528 accept spark-coauthor-edge: as an edge locator, with positive and negative tests. repairs.md records the deviation from plan §7.3. Mapping yearless edges to Neptune GraphEdge records remains a Phase 7 gate, correctly routed.

F5 — Deferred; acceptable. The domain owner must add these before 6D–6E producers rely on them.

F6 and F7 — Deferred; acceptable for 6B, but the gate is wrong (see R2).

F8 — Future scope; acceptable. Counting 2027-dated works is assigned to 6C.

New observations

R1 — Low — non-blocking.
- Where: SparkAnalyticsValidation.scala (check(SemanticSummary)).
- Evidence: entityId is only checked for being non-blank. It isn't checked to be a researcher, community, path-evidence or work ID matching summaryType.
- Owner: domain-engineer
- Acceptance check: Fold this into the F5 hardening before 6F's Job 10 produces summaries.

R2 — Low — non-blocking: F6 and F7 are scheduled too late.
- Where: repairs.md 6B rows F6/F7; plan phase6.md Subphase 6C, task 2.
- Evidence: 6C task 2 is "the run-manifest and deterministic run-ID builder", and 6C Job 2 creates sparkCoauthorEdgeId values that bind window labels. Both F6 (label vs. bounds identity) and F7 (deterministic run ID and fingerprint scope) take effect in 6C. Their recorded "before 6F" gates come too late.
- Owner: coordinator, to reschedule them. domain-engineer builds the core helper; the user decides the fingerprint scope.
- Acceptance check: 6C Step 0 asks both questions, and any core helper is delivered by domain-engineer before spark-engineer uses it.

Verified

- Ownership: core edits by domain-engineer, the Spark README by spark-engineer, docs/agent-runs/** by the coordinator. No Phase 5, build, Hadoop, ER or human-owned files changed.
- Additive compatibility: frozen wire fields and ID formulas are unchanged; parser and locator acceptance only widened.
- Gate timing: the latest source mtime is 23:07:42, and the full check started at about 23:08:08 (completed 23:15:04, 416 s).
- Full log: lines 161/163, 903/905, 953/955, 963/965, 2118/2120 and 2160/2162 sum to 140 + 64 + 39 + 1 + 234 + 7 = 485 passed, 0 failed. [success] is at line 2165 and real 418.15 at line 2166. The header shows Java 17.0.20.1. The [error] lines are the injected check-probe self-test.
- Targeted log: 11/11 passed.
- Log integrity: the retained log's SHA-256 is 04242ca7…0ce9 and its size is 245,188 bytes, matching test-report.md.
- review.md: my 6B review was appended verbatim.

3. Report fields

STATUS: COMPLETE (review) — VERDICT APPROVE for Subphase 6B repair round 1
OWNER: code-reviewer (independent, user-launched, read-only)
WORK ORDER: Read-only recheck of 6B repair round 1 on phase-6, base/HEAD
  bc1e4a17fc879b7aac254b28d83e78dbdd34e367 (uncommitted tree), covering F1–F4
  repairs, F5–F8 dispositions, docs consistency and evidence claims.
FILES CREATED: None.
FILES MODIFIED: None.
COMMANDS RUN: Read-only: git rev-parse HEAD; git status --short; git diff
  bc1e4a1… for StableIds.scala, DomainValidation.scala, repairs.md, test-report.md,
  review.md, owner-report.md; sed/grep of SparkAnalyticsValidation.scala,
  SparkAnalyticsContracts.scala, SparkAnalyticsContractSpec.scala, the
  semantic-summary wire file and both READMEs; stat mtimes of sources and
  evidence; grep of evidence/6b/repair-1/{final-check,targeted-contract}.txt;
  shasum -a 256 and wc -c of final-check.txt; plan 6C and §11. No build, test,
  Spark, AWS, provider, edit, commit or push.
TEST RESULTS: Not run by reviewer. Retained logs: full sbt -batch check 485/485
  (core 140, Hadoop 64, ER 39, Spark 1, independent 234, build 7), 416 s,
  real 418.15, Java 17.0.20.1; targeted SparkAnalyticsContractSpec 11/11.
VALIDATION RESULTS: F1, F2, F3 closed; F4 closed for citation; F5–F8 deferred
  with owners; R1 and R2 low, nonblocking. Ownership, additivity, gate timing
  and log hash verified.
ASSUMPTIONS: The course spec was read via WebFetch summary in the prior pass and
  has not changed for this recheck. Owner-reported intermediate (stale snapshot)
  failure is not separately retained, as test-report.md discloses.
RISKS: F6/F7 affect 6C edge IDs and run IDs (R2). The yearless Neptune edge
  mapping is open for Phase 7.
MANUAL ACTION REQUIRED: User commits the approved 6B tree before 6C starts.
BLOCKED-ON OWNER: None for 6B.
BLOCKED-ON EVIDENCE: None for 6B.
NEXT GATE: User commit of 6B, then Subphase 6C Step 0.

## Subphase 6C review — user-supplied external review

The reviewer output arrived in two user messages. The findings message is followed by the separately supplied report fields; each is preserved below verbatim.

1. VERDICT: REQUEST-CHANGES for Subphase 6C

Most of 6C is solid. The checks against the retained evidence hold up:

- Final gate log: SHA-256 3e2fd545…82c4, 247,609 bytes. Per-module counts are at the cited lines (142/64/39/7/238/7 = 497) and [success] is at line 2195.
- Source scan: collect() appears only in BoundedActions. There are no RDD, GraphX, GraphFrames, implicits or typed encoders.
- F6/F7 core helpers: they are correct and tested, and the frozen ID formulas are unchanged.
- Input binding: the ER prepCompletionHash check binds the ER export to the selected Hadoop run.
- Independent G1 test: it checks all 18 edges, their years, edge IDs, support sets and representative order against literal hand-computed values.
- Real-data smoke: the evidence matches the claims.

Four parts of the plan's Job 1/2 rules and 6C tasks are wrong or missing, though, plus a test gap. Details follow.

2. Findings

Blocking

F1 — High — wrong DBLP team selected when a group has more than one DBLP observation
- Where: modules/spark/src/main/scala/edu/uic/cs441/scholarchain/spark/Phase6CJobs.scala:367-372 (and :392-399)
- Evidence: selectedTeam joins teams to canonicalWorks on the member's own (workId, sourceRecordId). Every DBLP member of the group passes hasDblp. The rank-1 authoritativeSourceRecordId (:335-351) is computed but never used to filter. This breaks plan §7.2 ("the team is the DBLP author list"), §7.3 step 1, and the module's own modules/spark/README.md:43 ("Keep pairs only from the selected authoritative DBLP team observation").
- Impact: A canonical group can hold two DBLP records: same DOI means same workId, or both are linked to one Crossref/OpenAlex/ORCID record. Their teams then get merged into memberships, and both records' pairs are kept.
  - If the author lists differ, the n(n−1)/2 check fails and the run aborts.
  - If failOnHardInvariant=false, the merged team is published.
- Owner: spark-engineer; test-engineer for the independent case.
- Acceptance: Keep only the team and pairs whose (workId, sourceRecordId) equals (authoritativeWorkId, authoritativeSourceRecordId). Count the dropped non-authoritative DBLP observations. Add module and independent tests: two DBLP observations in one group with different author lists produce only the rank-1 team's memberships and pairs, and pairCountMismatches stays 0.

F2 — Medium — conflicting ORCIDs are never flagged
- Where: Phase6CJobs.scala:281-289 and :588-603
- Evidence: Researchers just collect_set their observed ORCIDs. integrity only ever contains pair-count-mismatch and constraint-blocked-work-group. Plan §7.2 requires conflicting ORCIDs within one DBLP-name group to be reported as integrity warnings without splitting the group, and §10 lists "conflicting ORCIDs flagged".
- Impact: A required Job 1 integrity check is missing.
- Owner: spark-engineer (+ test-engineer).
- Acceptance: One non-hard integrity row per researcher with more than one distinct DBLP-observed ORCID, plus a counter. The researcher ID is unchanged and the group is not split. Add module and independent tests.

F3 — Medium — missing graph endpoints are thrown but never recorded
- Where: Phase6CJobs.scala:792-798
- Evidence: Edges whose endpoint node is missing throw only when failOnHardInvariant is set. They are never added to integrity. With the flag off they disappear silently. Plan §7.2 requires violations to be written to integrity/ and to fail the run when the flag is set. The course spec says "Validate that every canonical authorship edge points to existing nodes… Emit counts and invariant failures."
- Note: Persisting hard failures to disk before a run aborts is 6F scope, and you disclosed that. The flag-off path losing violations is a 6C defect.
- Owner: spark-engineer.
- Acceptance: Missing endpoints become hardFailure=true integrity rows plus a counter, and the run still fails when the flag is set. A test injects an edge with an orphan endpoint and runs with the flag off: the row is published and counted. A second test with the flag on: the run fails.

F4 — Medium — ER unresolved and conflict outputs are not read
- Where: Phase6CReaders.scala:477-533
- Evidence: Only accepted-links.jsonl and grouping-constraints.json are read. Plan §7.1 (6C task 1) also requires reading the unresolved and conflict outputs, and §12 requires unresolved and conflicting links to be counted. The smoke ER export has work/conflict.jsonl with 3 rows and researcher/unresolved.jsonl with 6, and neither shows up in the counters. unresolvedMentions is derived from Spark's own mapping, not from ER.
- Owner: spark-engineer.
- Acceptance: Read both files for each entity type with explicit schemas through the reject path, and emit per-entity counters. A test covers nonzero conflict and unresolved inputs.

F5 — Medium — module tests miss required cases
- Where: modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase6CJobsSpec.scala:190-206, 232-281
- Evidence:
  - Plan 6C task 7 lists module tests for "conflicting constraint not merged" and "cross-DBLP-name link not applied". The module fixture always passes empty cannot-link and authority tables, so neither is tested at module level. Only the independent suite covers them.
  - The §10 Inputs cases "partial Hadoop run (no marker) refused" and "ER export manifest mismatch refused" are untested. Only requireErPrepBinding has negative tests.
  - The module G1 test asserts only the edge counts (9/18) and the A–B weight. It does not check all edges "exactly", as Done-when requires for both suites.
- Owner: spark-engineer.
- Acceptance: Module tests for:
  - a cannot-link group;
  - an authority-conflict group;
  - a cross-DBLP link;
  - an ambiguous non-DBLP mention;
  - a missing Hadoop marker;
  - a Hadoop inventory/hash mismatch;
  - an ER marker/manifest mismatch;
  - the full G1 edge table with literal weights and years.

WORK ORDER: Independent review of Subphase 6C, branch phase-6, base/HEAD 01d204b531d3fc72a5c49f884980a5c7c8926b18, uncommitted tree
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only only — git rev-parse/status/diff 01d204b; cat/sed/grep/wc on sources, tests, docs and evidence; shasum -a 256 on evidence/6c/final-check.txt; python3 -I JSON inspection of target/phase6-inputs/6c-er-ccd26111-disabled and target/phase4-runs/ccd26111…/export work files; WebFetch of the course README. No sbt, tests, Spark, AWS or provider calls.
TEST RESULTS: Not run by reviewer. Retained final-check.txt verified: hash 3e2fd545…82c4, 247,609 bytes, 497/497 at cited lines, [success] line 2195, real 459.53.
VALIDATION RESULTS: Source scan clean. F6/F7 correct. Independent G1 assertions complete and literal. Blocking defects F1–F5 as listed.
ASSUMPTIONS: Course "Detailed Spark requirements" read via a WebFetch summary, partly truncated; plan §7 treated as binding.
RISKS: F1 can abort or distort real-scale runs where DBLP duplicates share a DOI or an ER link. N1 can cause silent stale reuse.
MANUAL ACTION REQUIRED: User pastes the NEXT PROMPT; do not commit 6C yet.
BLOCKED-ON OWNER: spark-engineer (F1–F5, N1–N5, N7); test-engineer (independent cases for F1, F2).
BLOCKED-ON EVIDENCE: Repaired module and independent tests plus a fresh full JDK 17 sbt -batch check.
NEXT GATE: 6C repair round 1, then a read-only recheck.

## Subphase 6C repair round 1 recheck — user-supplied external review

Only the following report fields and blocking summary were supplied for this recheck. The full finding text was not supplied; the supplied wording is preserved verbatim.

OWNER: code-reviewer (external, user-launched, read-only)
WORK ORDER: Recheck of Subphase 6C repair round 1; branch phase-6, base/HEAD 01d204b531d3fc72a5c49f884980a5c7c8926b18, uncommitted tree as of 2026-10-22 02:05 CDT
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only — git rev-parse/status/diff 01d204b; ls/stat for mtimes; cat/sed/grep on Spark sources, tests, README, phase-06 docs and evidence/6c/repair-1; python3 -I inspection of the ER export's unresolved/conflict files and the two smoke configs. No sbt, tests, Spark, AWS or provider calls.
TEST RESULTS: Not run by reviewer. Retained: repair-1 independent targeted 6/6 (01:05:14) and production compile (01:04:07), both predating later Readers/Main/spec edits. No module, smoke or full-check result exists for this round.
VALIDATION RESULTS: F1–F5 implemented and their tests are substantive. ER decision schema matches the real export. Blocking: R1-1 missing or stale evidence; R1-2 run-ID reuse across a semantic change.
ASSUMPTIONS: No repair agent was still writing at review time (last edit 01:41).
RISKS: Committing now would ship untested Main/reader/spec changes; R1-2 would mislabel post-repair outputs with the pre-repair run ID.
MANUAL ACTION REQUIRED: User pastes the NEXT PROMPT; do not commit 6C.
BLOCKED-ON OWNER: spark-engineer (R1-2, module test run); coordinator (evidence and reports, R1-5).
BLOCKED-ON EVIDENCE: Module 14/14, independent 6/6, repaired smoke with new run ID and ER counters, full JDK 17 sbt -batch check.
NEXT GATE: Finish 6C repair round 1, then a read-only recheck.

### Complete recheck text supplied subsequently — user-supplied external review

1. VERDICT: REQUEST-CHANGES (recheck of 6C repair round 1)

Your fixes for F1–F5 look correct in the code, but this round isn't finished. Nothing has run the current tree:

- The module tests have never run.
- The repaired smoke hasn't completed.
- The full JDK 17 check hasn't run.
- The reports still describe the pre-repair gate.

There's also one new blocking problem: the run ID doesn't change even though the output did. I reviewed the tree as of 02:05. If a repair agent is still running, this reflects its state at that time.

2. Findings

Closed in code (each still needs its tests to actually run, see R1-1)

Finding: F1
Evidence: Phase6CJobs.scala:397-406 now keeps only the team where workId = authoritativeWorkId and sourceRecordId = authoritativeSourceRecordId. The
pair join at :426-433 goes through selectedTeam. Dropped observations are counted at :380-396, :554. The module test
(Phase6CJobsSpec.scala:500-539) gives the second record a different team (A, D); the result keeps only {A, B, C}, with mismatch 0 and dropped 1.
The independent test (IndependentPhase6CGraphSpec, "linked DBLP observations…") keeps P–Q only, with R absent.
────────────────────────────────────────
Finding: F2
Evidence: :294-302 and :643-650 add a non-hard conflicting-dblp-orcid row and a counter; the researcher ID is unchanged. Module test :541-558 and an
independent test.
────────────────────────────────────────
Finding: F3
Evidence: :836-855 adds missing endpoints to integrity as hardFailure=true, throws only when the flag is set, and adds a counter at :856-862. Test
:560-584 covers flag off (row and count published) and flag on (the run throws).
────────────────────────────────────────
Finding: F4
Evidence: Phase6CReaders.scala:435-470, 630-656 reads all four decision files with an explicit schema through the reject path, refusing a file that
holds the wrong entity or outcome. Counters are at Phase6CJobs.scala:539-544. I checked the schema against the real export:
researcher/unresolved.jsonl has 6 rows (Researcher/UNRESOLVED) and work/conflict.jsonl has 3 (Work/CONFLICT), and the nested field types match.
────────────────────────────────────────
Finding: F5
Evidence: Phase6CJobsSpec.scala now covers a literal 18-edge G1 table with weights and years (:277-319), cannot-link plus authority conflict
(:586-613), the cross-DBLP and ambiguous-mention cases (:615-642), a missing Hadoop marker plus inventory and hash mismatches (:793-830), and an ER
 marker/manifest mismatch (:832-861).

Blocking

R1-1 — High — no test or gate evidence for the current tree (owner: coordinator for evidence and reports; spark-engineer for the module tests)
- Stale evidence: these files changed after the last retained log:
  - Phase6CReaders.scala (01:05:13)
  - Phase6CMain.scala (01:40:01)
  - Phase6CJobsSpec.scala (01:41:24)
  - modules/spark/README.md (01:41:28)

  The only repair-1 evidence is repair-1/production-compile.txt (01:04:07) and repair-1/independent-targeted.txt (6/6, 01:05:14).
- Nothing else has run:
  - No run of the 14-test Phase6CJobsSpec.
  - The repaired smoke's output root target/phase6-runs/6c-repair-1 (from 6c-spark-config-repair-1.json) doesn't exist.
  - No full sbt -batch check.
- Docs not updated: owner-report.md and test-report.md are unchanged since 00:24–00:25, and repairs.md still says "Repair in progress" for F1–F5.
- Gap the smoke must cover: the F4 module test calls readErDecision directly, so only the smoke proves load() wires the real files through.
- Acceptance:
  - Phase6CJobsSpec 14/14 and IndependentPhase6CGraphSpec 6/6, both on the final tree.
  - A completed smoke into a fresh root showing erResearcherUnresolved=6, erResearcherConflicts=0, erWorkUnresolved=0, erWorkConflicts=3 and missingGraphEndpoints=0.
  - One full JDK 17 sbt -batch check with an exit code, per-module counts, size and SHA-256.
  - owner-report.md, test-report.md and repairs.md updated with the real results.

R1-2 — Medium — the repaired code would reuse the pre-repair run ID (owner: spark-engineer)
- Evidence: Phase6CMain.scala:18 still has codeVersion = "spark-phase6c-jobs1-2-v1". The repair config differs from the provenance config only in outputRoot, which is excluded from the logical fingerprint.
- Impact: The repaired smoke will get the same run:50e1fc99-a22c-4993-9525-7772e6af1fac as the retained pre-repair evidence, yet it publishes different counters and integrity rows and, for multi-DBLP groups, different memberships. Two different outputs would share one run ID. Pointing the run at an existing root would silently reuse the pre-repair output.
- Acceptance:
  - Bump codeVersion to …-v2, or bind it to a build or git hash, which closes N1 too.
  - Update the reuse-gate test literal (Phase6CJobsSpec.scala:869).
  - The repaired smoke's run ID must differ from 50e1fc99….

Nonblocking

- R1-3 (Low) — README claim is wrong. modules/spark/README.md says "Work representative selection follows the core versioned authority rule". The code at Phase6CJobs.scala:335-347 still ranks by a non-null doi column, which is prior finding N2. Either fix the code or reword the line.
- R1-4 (Low) — ORCID check counts inconsistently. :295-298 filters on the trimmed ORCID but counts distinct untrimmed values. Two copies of one ORCID that differ only in whitespace would raise a false conflict unless Hadoop already normalizes them. Use trim consistently.
- R1-5 (Process) — review.md is missing part of my previous review. It records F1–F5 and the report fields but not the Nonblocking N1–N9 list or the "Later gates" list. repairs.md then says N1–N7 have no descriptions. Append the missing sections verbatim.
- Prior nonblocking items, still open as before: N1 (unless R1-2 binds a build hash), N2, N3, N4, N5, N7 and N8. N6 (SparkListener) stays acceptable.

3. Report fields

STATUS: COMPLETE (recheck); verdict REQUEST-CHANGES
OWNER: code-reviewer (external, user-launched, read-only)
WORK ORDER: Recheck of Subphase 6C repair round 1; branch phase-6, base/HEAD 01d204b531d3fc72a5c49f884980a5c7c8926b18, uncommitted tree as of 2026-10-22 02:05 CDT
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only — git rev-parse/status/diff 01d204b; ls/stat for mtimes; cat/sed/grep on Spark sources, tests, README, phase-06 docs and evidence/6c/repair-1; python3 -I inspection of the ER export's unresolved/conflict files and the two smoke configs. No sbt, tests, Spark, AWS or provider calls.
TEST RESULTS: Not run by reviewer. Retained: repair-1 independent targeted 6/6 (01:05:14) and production compile (01:04:07), both predating later Readers/Main/spec edits. No module, smoke or full-check result exists for this round.
VALIDATION RESULTS: F1–F5 implemented and their tests are substantive. ER decision schema matches the real export. Blocking: R1-1 missing or stale evidence; R1-2 run-ID reuse across a semantic change.
ASSUMPTIONS: No repair agent was still writing at review time (last edit 01:41).
RISKS: Committing now would ship untested Main/reader/spec changes; R1-2 would mislabel post-repair outputs with the pre-repair run ID.
MANUAL ACTION REQUIRED: User pastes the NEXT PROMPT; do not commit 6C.
BLOCKED-ON OWNER: spark-engineer (R1-2, module test run); coordinator (evidence and reports, R1-5).
BLOCKED-ON EVIDENCE: Module 14/14, independent 6/6, repaired smoke with new run ID and ER counters, full JDK 17 sbt -batch check.
NEXT GATE: Finish 6C repair round 1, then a read-only recheck.

## Subphase 6C repair round 1 approval — user-supplied external review

1. VERDICT: APPROVE for Subphase 6C repair round 1

Both recheck blockers are closed. Every claim I checked holds on the current tree:

R1-1: tests and gates now cover the final tree
- Timing: no production, test or README file is newer than final-check.txt (02:23:27). The last code edits were Phase6CMain.scala at 02:09:45 and Phase6CJobsSpec.scala at 02:09:54. Every log below came after that:
  - module targeted run, 14/14, finished 02:11:23;
  - independent targeted run, 6/6, finished 02:12:29;
  - smoke, finished 02:13:00;
  - full check, finished 02:23:27.
- Full check: repair-1/final-check.txt is 253,775 bytes with SHA-256 6c0fdf74…a7773, and starts on Homebrew Java 17.0.20.1. Counts at lines 165/907/957/1038/2212/2254 are 142/64/39/15/240/7 = 507, with zero failures. The log ends [success] Total time: 512 s and real 513.92. Spark's 15 is the 14 Phase6CJobsSpec tests plus SparkSmokeSpec. Independent's 240 is the earlier 238 plus the new F1 and F2 tests. The [error] lines at 2222–2241 are the expected injected check-probe failure, and the S3 rename warning at line 2175 is the existing Hadoop local test fixture.
- Real ER counters: counter-inspect-final.txt shows erResearcherUnresolved=6, erResearcherConflicts=0, erWorkUnresolved=0, erWorkConflicts=3, missingGraphEndpoints=0. Those match the row counts I took from the export files myself (researcher unresolved 6, researcher conflict 0, work unresolved 0, work conflict 3). The probe throws on any mismatch and exited 0.
- Published output: the manifest under target/phase6-runs/6c-repair-1/run:d56e56d9-… is byte-identical to the retained local-run-manifest.json. Its _SCHOLARCHAIN_SPARK_COMPLETE equals sha256(manifest) plus a newline. Integrity has 0 rows, input rejects have 0, and there are 28 counters.

R1-2: the repaired code gets a new run ID
- Phase6CMain.scala:18 is now spark-phase6c-jobs1-2-v2.
- The reuse test (Phase6CJobsSpec.scala, last test) checks two things. Run IDs differ between v1 and v2. requireReusable rejects a manifest whose only change is codeVersion being v1.
- The smoke produced run:d56e56d9-de03-4862-bc66-46fd5ad27b75, not 50e1fc99….

Other checks
- F1–F5: the code is unchanged since my last recheck, and the tests I reviewed then all passed on the final tree.
- Spark API rule: collect() still appears only in BoundedActions (lines 14 and 21). No RDD, GraphX, GraphFrames, implicits or encoders.
- Ownership: clean. Spark-owned code, tests/** from the test owner, docs and evidence from the coordinator. No changes to build, Hadoop, ER, .claude or human-owned files.
- Reports: repairs.md, owner-report.md and test-report.md are accurate. They disclose the sandbox lock and socket denials as environment problems rather than passing tests, and they don't invent the N-list text.

2. Findings

None of these block approval.

R1-3 — Low — README overstates the representative-work rule (spark-engineer)
- modules/spark/README.md says "Work representative selection follows the core versioned authority rule", but the code at Phase6CJobs.scala:335-347 ranks by a non-null doi column.
- Acceptance: fix N2, or reword the line. Do it before the 6F documentation pass.

R1-4 — Low — ORCID conflict check trims inconsistently (spark-engineer)
- Phase6CJobs.scala:295-298 filters on the trimmed ORCID but counts distinct untrimmed values.
- Acceptance: use countDistinct(trim(...)). Do it before 6F integrity output.

R1-5 — Process — nonblocking list not yet recorded (coordinator)
- The N1–N9 and "Later gates" text was never supplied, so nothing could be appended. It is restated below so it can be recorded now.

R2-1 — Low, new — evidence probe scripts live under docs/** (coordinator)
- repair-1/CounterInspect.java and inspect_counters.py sit under docs, outside the Stop-hook and formatter scope.
- They hardcode /private/tmp/phase6c-counter-inspect and an absolute Homebrew JDK path, and they depend on the retained test-classpath.txt, which holds absolute local paths. Others can't replay them as written.
- They are acceptable as local evidence.
- Acceptance (by 6F): read counters through a Spark-module test or a scripts/** tool with a proper owner.

Nonblocking register from the first 6C review, restated

- N1 (Medium): codeVersion is maintained by hand. v2 fixed this instance, but a future semantic change without a bump would bring the problem back. Bind a git SHA or JAR hash before the 6F/6G determinism replay.
- N2 (Medium): representative-work selection infers DOI authority from the doi column instead of the work:doi: ID authority, and ignores representativePolicyVersion. A Crossref record without doi loses to work:dblp:.
- N3 (Low): some rows are dropped without being counted:
  - accepted links with a null endpoint (Phase6CReaders.scala, the links() filter);
  - graph edges with no evidence work (Phase6CJobs.scala:773).
- N4 (Low): counter names and meanings don't match. ambiguousNonDblpMentions and constraintBlockedWorkLinks count groups. missingYearExcluded.* repeats one value for every window. post2026… hardcodes the year. Fix before 6D consumes the counters.
- N5 (Low): the formatted plans are captured after the eager checkpoints, so they show only checkpoint scans. Capture them before checkpointing (6F).
- N6 (Observation): the SparkListener is acceptable instrumentation. The real event log and summarizer are 6F work.
- N7 (Low): the UDF justification is not documented in the Spark README, and phase6Context could be built from literals.
- N8 (Low): nodes/researcher and the graph tables carry scholarchain.domain.v1 even though nodes/researcher isn't the domain Researcher shape. Resolve with the 6F layout.
- N9 (Process): in the original 6C round the coordinator ran scalafmt on Spark-owned files. It was disclosed and owner-confirmed.

Later gates (not 6C)

- Prior F5 and recheck-R1 domain hardening, before the 6D–6F producers.
- 6F: the Job 11 layout, content hashes, load manifests, persisting hard failures before an abort, and the event-log summarizer.
- Phase 7: Neptune mapping for yearless works.
- 6H: the JDK packaging guard and live EMR compatibility. No cloud runtime has been tested.

3. Report fields

STATUS: COMPLETE (recheck); verdict APPROVE for Subphase 6C repair round 1
OWNER: code-reviewer (external, user-launched, read-only)
WORK ORDER: Recheck of 6C repair round 1 completion; branch phase-6, base/HEAD 01d204b531d3fc72a5c49f884980a5c7c8926b18, uncommitted tree as of 2026-10-22 02:27 CDT
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only — git rev-parse/status; ls -laT and find -newer for timing; shasum -a 256 and wc -c on repair-1/final-check.txt; grep/sed/cat on Spark sources, tests, phase-06 docs and evidence/6c/repair-1; cmp of the published vs retained run manifest; marker hash comparison; python3 -I import probe (pyarrow absent, Parquet not read directly). No sbt, tests, Spark, AWS or provider calls.
TEST RESULTS: Not run by reviewer. Retained and verified: module 14/14 (02:11:23), independent 6/6 (02:12:29), full JDK 17 sbt -batch check 507/507 (142/64/39/15/240/7), exit success, real 513.92, 253,775 bytes, SHA-256 6c0fdf7494269c2ccb71a8cdbee35cb36b4c574b4d3d34928e2e37352c5a7773.
VALIDATION RESULTS: All logs postdate the last source edit. v2 run ID run:d56e56d9-… differs from 50e1fc99-…, and the reuse gate rejects v1. Real ER counters 6/0/0/3 match the export files; missingGraphEndpoints 0. Published manifest matches the retained one and the marker is valid. Spark API scan clean. F1–F5 and R1-1/R1-2 closed.
ASSUMPTIONS: Smoke counter values are taken from the retained probe output, because the reviewer could not read Parquet without pyarrow; the probe asserts the expected values and exited 0.
RISKS: N1 hand-bumped codeVersion; N2/R1-3 representative rule and README mismatch; N4 counter semantics before 6D; no cloud/EMR evidence.
MANUAL ACTION REQUIRED: User reviews and commits the 6C tree before 6D Step 0.
BLOCKED-ON OWNER: none for 6C.
BLOCKED-ON EVIDENCE: none for 6C.
NEXT GATE: User's 6C commit, then Subphase 6D Step 0.


## Subphase 6D+6E review — user-supplied external review

1. VERDICT: REQUEST-CHANGES for Subphase 6D+6E

The jobs 3–8 work itself is sound. The metrics, components, coreness, BFS predecessor rule, LPA and bridge formulas all match the plan, and the G1–G4 expected values are asserted exactly in the independent suite. The retained evidence matches what the reports claim. Three things block approval:
- Your approved 50/50/K=20 settings never made it into the shipped config.
- The "LPA reports non-convergence" behavior you decided on has no test.
- Two report and README statements overstate the test coverage.

All three are small fixes.

What I verified (read-only)

- Git state: HEAD is 8d5b9d4… and unchanged; the work is uncommitted. The plan SHA-256 matches. The diff covers every listed tracked file, and I read all three new Scala files in full.
- Final log: final-check.txt is 285,463 bytes and its SHA-256 bd8b9a28… matches.
  - Per-module counts are 143/64/39/24/250/7, at log lines 166, 908, 958, 1542, 2743 and 2785.
  - real 567.12 is at line 2789 and exit=0 at line 2793.
  - Both 6DE suites ran inside it (module 9, independent 10).
- Timestamps: every changed source, test and README file predates the final check (12:04–12:06 vs 12:17 local).
- Spark API and driver rules: Phase6DEJobs.scala has no RDD, implicits, Encoders, typed Datasets or GraphX. Every driver-side action goes through BoundedActions (count, exists, scalarLong or a capped call). The UDF4 has an explicit StringType and wraps the core StableIds function, the same pattern 6C was approved with.
- Correctness checked by hand:
  - k-core uses the h-index operator, starts from degree, and checks coreness ≤ degree.
  - Components use minimum-label propagation with a hard failure at the iteration limit.
  - Synchronous LPA breaks ties by the smallest label.
  - The participation coefficient includes the researcher's own community, so C and D get 4/9 and the star hub gets 0.8.
  - BFS keeps the smallest immediate predecessor, and both suites have a fixture where that rule and whole-route ordering disagree.
  - Cross-community edges are ordered so communityA < communityB.
- Contract compatibility: the core diff only adds validation rules; no wire field or ID formula changed. All DE output columns match the core records.
- Ownership: writes stayed inside each owner's paths. The coordinator ran the formatter on the test owner's file, which is disclosed.

2. Findings

Blocking

ID: F1
Severity: High
Location: modules/core/src/main/resources/scholarchain.spark-analytics-config.v1.json:17,19,24; modules/spark/README.md:134; owner-report.md:206
Evidence: Your Step 0 answers (prompt.md:73-74) set component/k-core limits to 50 and K=20. The only config file, unchanged since 6B (01d204b), still
has componentMaxIterations: 100, kCoreMaxIterations: 100, sampledPathPairCount: 32. README:134 says "the config carries these values explicitly",
but nothing in the repo carries them. The owner report calls them "intended". The core test "…validates approved defaults" never asserts these
fields.
Impact: The 6F+6G CLI will load this file and run 100/100/K=32 against your decision. The run fingerprint and run ID will then record values you
didn't approve.
Owner: domain-engineer for the resource and core test; spark-engineer for the README:134 wording
Acceptance check: Resource values become component 50, k-core 50, checkpoint 5, community 20, maxHops 6, K (sampledPathPairCount) 20, S
(pathSampleSourceCount) 32, seed fixed. The core default-config test asserts every one of them. Disclose that the config fingerprint changes; old
6C smoke run IDs stay historical. Or, instead, you record a decision keeping 100/100/32.
────────────────────────────────────────
ID: F2
Severity: Medium
Location: Phase6DEJobs.scala:343-404, 554-560; Phase6DEJobsSpec.scala and IndependentPhase6DEGraphSpec.scala (no such case); README.md:134
Evidence: You decided that LPA "reports non-convergence", and the plan's test matrix (§10, Communities) requires it. No test asserts converged=false,
a nonzero finalChangedCount, or counter communityConverged=0. The only LPA tests use graphs that converge, and the configs with a 1-iteration limit
 never check convergence. README:134 also says "module tests use smaller community limits where they deliberately inspect oscillation", which is
false.
Impact: The behavior you decided on is untested, and the README claims coverage that doesn't exist.
Owner: spark-engineer (module test and README); test-engineer may add an independent case
Acceptance check: A two-researcher pair (x<y, weight 1) swaps labels every iteration under synchronous LPA. With communityMaxIterations=3: every
member and summary row of that window has converged=false and finalChangedCount=2; the counters show communityConverged=0 and
communityFinalChangedCount=2; SparkAnalyticsValidation.check accepts the rows. Also fix the README sentence.
────────────────────────────────────────
ID: F3
Severity: Low (accuracy)
Location: test-report.md:293
Evidence: It says "Module and independent tests separately exercise the G1–G4 values". Phase6DEJobsSpec has no G1–G4 fixture; it uses an A–E graph, a
triangle and a tie graph. Only the independent suite covers G1–G4. Plan §8 expects both suites to use G1.
Impact: The evidence overstates coverage.
Owner: Coordinator (report text); spark-engineer only if you want G1 module tests
Acceptance check: The report states the coverage accurately. The independent G1–G4 coverage already meets "Done when".

Non-blocking observations

ID: N1
Location: Phase6DEJobs.scala:835-883
Observation: BFS only drops the target node from the frontier. A pair whose target was found keeps expanding its other frontier nodes up to maxHops,
while plan §7.6 says to stop at the target. Each frontier row also carries the full path and hop arrays, and it checkpoints every hop, while README
 job 5 says "at the configured interval". Output is correct, but the cost is roughly pairs × windows × component size.
Owner / when: spark-engineer; fix before the 6F+6G real-data run (remove found pairs from the frontier; consider rebuilding paths from predecessor
pointers)
────────────────────────────────────────
ID: N2
Location: :559, :571
Observation: LPA iterations is the global loop count. A window that converged at iteration 3 reports iterations=20, converged=true.
Owner / when: spark-engineer; fix or document
────────────────────────────────────────
ID: N3
Location: :365-396
Observation: LPA calls next.cache() only after the eager changes checkpoint, and drops the old labels before next is built. Each iteration then
rebuilds up to checkpointInterval−1 earlier iterations from lineage. This affects performance only; connected and kCore do it in the right order.
Owner / when: spark-engineer
────────────────────────────────────────
ID: N4 (plausible, not executed)
Location: :59-63 vs Phase6CJobs.scala:508-522
Observation: withContext infers the context schema with schema_of_json. Spark's JSON inference sorts struct fields by name, so the 6DE context field
order likely differs from 6C's explicit schema, despite the comment at line 62. Readers that match by name are unaffected.
Owner / when: spark-engineer; share one explicit StructType before the 6F+6G manifests and schema hashes
────────────────────────────────────────
ID: N5
Location: :806-813, :903, :681
Observation: A benchmark endpoint that is missing from a window, or whose ID is unknown, is reported as no-path, indistinguishable from a
cross-component pair. pathSeededSamplePairs counts pairs before deduplication against benchmark pairs.
Owner / when: spark-engineer; add a missing-endpoint counter and document it
────────────────────────────────────────
ID: N6
Location: IndependentPhase6DEGraphSpec.scala:634-646
Observation: The two-run replay compares only metrics, coreness and components; paths, seeded sampling, LPA and bridges aren't replayed.
Owner / when: 6F+6G full replay-hash gate
────────────────────────────────────────
ID: N7
Location: —
Observation: No test parses a DE output row into its core record and validates it. The columns match by inspection.
Owner / when: 6F+6G export tests
────────────────────────────────────────
ID: N8
Location: README.md jobs 3–6
Observation: The 6B design text doesn't match the code in places: "verify one membership per active researcher / size sums", "count discovered
nodes", "repartition frontier by (window, source, nodeId)", "no iteration checkpoint".
Owner / when: spark-engineer; final README in 6F+6G
────────────────────────────────────────
ID: N9
Location: commands.md
Observation: The coordinator ran the formatter on the test owner's file (disclosed, same as 6C N9).
Owner / when: Process note only

Future gates (not demanded now)
- Path-length estimate: the course requires an estimate of component-level path length or diameter "with a documented scalable method". pathLengthEstimates is empty under your 6DE-3 answer, and the reports don't record why it wasn't a small addition. It must be built in 6F+6G or accepted by you as a deviation in the 6I human-gate.md.
- LPA on real data: synchronous LPA oscillates forever on any two-person component (G1's H–I is one). Real-data windows will almost always report converged=false, which the 6F+6G report should state.
- Other 6F+6G work: publishing, the event-log summarizer, writing hard failures to integrity/, metrics per bounded window (only all-years is exercised here), and the real-data run and replay.
- Later items: the routed 6C N items and summary entity-kind validation stay assigned in repairs.md. EMR stays deferred to Phases 13 and 15.

3. Report fields

STATUS: COMPLETE (review) — VERDICT REQUEST-CHANGES
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Independent review of merged Subphase 6D+6E (jobs 3–8), branch phase-6, base/HEAD 8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4, plan SHA-256 6df6d856…c955096
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git rev-parse HEAD; git status --short; git diff --stat; git diff (core, README, phase-06 reports); shasum -a 256 (plan, final-check.txt); wc/stat/grep/sed reads of sources, tests, config, evidence; read-only WebFetch of the course README (raw.githubusercontent.com). No build, test, Spark, AWS or model-provider calls.
TEST RESULTS: None run by the reviewer. Retained final-check.txt matches its claims: 527/0 (143/64/39/24/250/7), exit 0, real 567.12 s, 285,463 bytes, SHA-256 bd8b9a28…dbca34; 6DE suites 9 module + 10 independent inside it.
VALIDATION RESULTS: API/driver rules met; G1–G4, bridge, BFS-predecessor and LPA-trace expectations checked by hand against code and tests; core diff is additive validation only; ownership respected. Blockers: F1 approved defaults absent from the shipped config; F2 LPA non-convergence reporting untested and README claim false; F3 test-report overstates module G1–G4 coverage.
ASSUMPTIONS: The Step 0 answers in prompt.md:72-76 are your authoritative decisions; no later decision changed the 6B config defaults. Spark JSON schema inference sorts fields by name (N4, not executed).
RISKS: Shipped config contradicts decisions (F1); path-length estimate still missing against a course item; LPA will rarely converge on real data; BFS cost (N1) before the 6F+6G real-data run.
MANUAL ACTION REQUIRED: User pastes the NEXT PROMPT into the main agent. For F1, the user may instead record a decision to keep 100/100/32.
BLOCKED-ON OWNER: domain-engineer (F1 config + test); spark-engineer (F1 README, F2 test + README); coordinator (F3 report text)
BLOCKED-ON EVIDENCE: config v1.json:17,19,24 vs prompt.md:73-74 and README.md:134; no non-convergence assertion in either 6DE spec; test-report.md:293
NEXT GATE: Repair round 1 for 6D+6E, fresh JDK 17 sbt check, user-run read-only recheck. 6F+6G does not start.


## Subphase 6D+6E repair round 1 approval — user-supplied external review

1. VERDICT: APPROVE for Subphase 6D+6E repair round 1

All three blockers are fixed. The repair touched only the config resource, the core contract test, the Spark module test, the README and the coordinator reports. Production code and the independent suite are byte-for-byte untouched: Phase6DEJobs.scala still has its 12:04:49 mtime and IndependentPhase6DEGraphSpec.scala its 12:06:42 mtime. The retained evidence matches every claim in the handoff. I found no new blockers.

2. Findings

F1–F3 dispositions

ID: F1 (High)
Disposition: Closed
Evidence: scholarchain.spark-analytics-config.v1.json changes only three values: componentMaxIterations 100→50, kCoreMaxIterations 100→50,
sampledPathPairCount 32→20. The others were already right (community 20, checkpoint 5, maxHops 6, S=32, seed 441). The core "approved defaults"
test asserts all eight values plus shufflePartitions 4. It also proves both the full and the logical fingerprint differ from the old 100/100/K=32
config. Full fingerprint a75347c8…→8f6fd8b7…; logical 49316f88…→f03c7950…. These match core-targeted.txt:21-22 and final-gate-metadata.json.
README:134 now matches the shipped file. README:136 and the reports say future run IDs change while the historical 6C outputs stay as they were.
Ownership: domain-engineer changed core, spark-engineer changed the README.
────────────────────────────────────────
ID: F2 (Medium)
Disposition: Closed
Evidence: Phase6DEJobsSpec.scala:311-359 uses a two-person, weight-1 graph with communityMax=3. The labels swap on every iteration, so after 3 rounds
there are two singleton communities. The test asserts:<br>- 2 member rows with iterations=3 and converged=false;<br>- 2 summary rows with size 1,
finalChangedCount=2 and converged=false;<br>- counters communityConverged=0 and communityFinalChangedCount=2.<br>The actual DataFrame rows are
converted to JSON and parsed with CoreJson.parse into CommunityMembership/CommunitySummary, and every row passes SparkAnalyticsValidation.check.
The false README sentence about oscillation tests is replaced with a description of this fixture. The test passed in both module-targeted.txt:515
and final-check.txt:1536.
────────────────────────────────────────
ID: F3 (Low)
Disposition: Closed
Evidence: test-report.md:293 now credits G1–G4 coverage to the independent suite only and lists the module suite's own fixtures. The correction is
disclosed in repairs.md.

Evidence I checked
- Repo state: HEAD is 8d5b9d4… and unchanged; the status matches handoff-check.txt. The plan SHA-256 matches.
- Full log: repair-1/final-check.txt is 286,117 bytes and its SHA-256 18d9858b…112f matches. Per-module counts are 143/64/39/25/250/7, at lines 168, 910, 960, 1546, 2748 and 2790, for 528 in total. Success is at line 2793 (12:47:16), real 563.44 at line 2794 and exit=0 at line 2798. The header shows sbt 1.10.7 on Java 17.0.20.1.
- Timing: every repaired file was last changed at 12:34:55–12:36:41, before the full gate.
- Targeted runs: the module run finished at 12:37:15. Its formatter step completed at 12:36:41, the same time as the test file's mtime, and the tests ran after it. Core targeted passed 14/14 at 12:35:26.
- Scans and attribution: the driver/API scan matches only the two BoundedActions collect sites, and git diff --check exited 0. The sandbox lock error and the coordinator re-running the owner's command are disclosed (module-sandbox-denial.txt, commands.md).
- Review records: review.md has the round-0 verdict appended under its own heading. repairs.md registers F1–F3, N1–N9 and the future gates. It records the missing path-length-estimate rationale honestly instead of inventing one.

Remaining non-blocking items (registered; nothing new is blocking)
- N1–N9 are unchanged and registered with owners. The new test partly addresses N7 (DE rows now parse into core records for communities). Items to settle before or during 6F+6G:
  - N1: BFS keeps expanding pairs whose target was already found, and checkpoints every hop.
  - N2: the LPA iterations field is the global loop count, not per window.
  - N3: LPA caches in the wrong order, causing extra recomputation.
  - N4: the context schema is inferred, so its field order may differ from 6C's.
  - N5: an endpoint missing from a window is reported as an ordinary no-path.
  - N6: the replay test covers only part of the output.
  - N8: some README design text has drifted from the code.
- R1-O1 (new observation, non-blocking): the README says LPA "can oscillate" and names the two-person fixture. It doesn't say what follows for real data: any two-person component (like G1's H–I) oscillates forever. Real-data windows will therefore almost always report converged=false. State this in the 6F+6G report and README. Owner: spark-engineer.

Later gates
- Build the S-source path-length/diameter estimate (a course requirement) in 6F+6G, or record your explicit acceptance of the deviation at 6I.
- Also in 6F+6G: publishing, the event-log summarizer, writing hard failures to integrity/, metrics for bounded windows, the real-data run and a full replay. 6C's N items and the summary entity-kind check are in the same 6F+6G batch.
- EMR stays deferred to Phases 13 and 15.

3. Report fields

STATUS: COMPLETE (review) — VERDICT APPROVE for 6D+6E repair round 1
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Recheck of 6D+6E F1–F3 on phase-6, base/HEAD 8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4, plan SHA-256 6df6d856…c955096; inspect base diff and untracked files
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git rev-parse HEAD; git status --short; git diff --stat; git diff (config resource, core spec, review.md, repairs.md, test-report.md); shasum -a 256 (plan, repair-1/final-check.txt); wc/stat/grep/sed/cat reads of Phase6DEJobsSpec.scala, README.md and repair-1 evidence. No build, test, format, Spark, AWS or model-provider calls.
TEST RESULTS: None run by reviewer. Retained logs verified: full gate 528/0 (143/64/39/25/250/7), exit 0, real 563.44 s, 286,117 bytes, SHA-256 18d9858b…112f; core targeted 14/14; Spark targeted 10/10, exit 0.
VALIDATION RESULTS: F1 closed (resource and assertions match decisions; fingerprint change disclosed); F2 closed (oscillating pair asserted through core parse and validation, and counters); F3 closed (report wording accurate). Production code and independent tests unchanged; ownership respected; API/driver scan clean.
ASSUMPTIONS: Step 0 answers in prompt.md remain the binding decisions; historical 6C run IDs are not rewritten.
RISKS: Path-length estimate still absent against a course item; LPA will rarely converge on real data (R1-O1); BFS and LPA cost (N1, N3) ahead of the real-data run; possible context-schema mismatch (N4) before manifests and schema hashes.
MANUAL ACTION REQUIRED: User commits the approved 6D+6E tree, then pastes the NEXT PROMPT.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: User commit of 6D+6E, then Subphase 6F+6G Step 0.

4. NEXT PROMPT

You are the ScholarChain Phase 6 coordinator in
/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-6.
Plan: /Users/danny/Documents/plan/phase6.md
(SHA-256 6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096).

(a) Append the external reviewer's "6D+6E repair round 1" verdict VERBATIM to
    docs/agent-runs/phase-06/review.md under "Subphase 6D+6E", marked
    "user-supplied external review". Record the F1–F3 closures and the new
    nonblocking observation R1-O1 in repairs.md. Do not rewrite prior human
    decisions.

(b) Confirm that the user has committed the approved 6D+6E tree (previous
    base 8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4). If the tree is still
    uncommitted, ask the user and wait. Record the new commit as the 6F+6G
    base SHA in preflight.

(c) Start ONLY Subphase 6F+6G of the plan (jobs 9–11, CLI, README
    completion, bounded real-data run, replay and independent hardening),
    beginning with Step 0. Ask all open questions at once, each with a
    recommended default: 6F-1, 6G-1, 6G-2, plus your own. Include these
    decisions carried over from 6D+6E:
    - S-source sampled path-length / 90th-percentile effective-diameter
      estimate: implement in 6F+6G (recommended; it is a course requirement)
      or record a deviation for explicit human acceptance at 6I.
    - Whether to fix N1 (stop expanding found BFS pairs; checkpoint at the
      configured interval), N3 (LPA cache order) and N4 (one explicit shared
      context StructType across 6C and 6DE tables) before the real-data run.
      Recommended: yes.
    - N2 (per-window LPA iteration count) and N5 (missing-endpoint counter
      for benchmark pairs): fix or document.
    - Disclose R1-O1 in the README and the 6F+6G report: synchronous LPA
      oscillates on two-person components, so real-data windows will rarely
      report converged=true.
    Also carry into the 6F+6G tests and gates: N6 (full replay over every
    table), N7 (exported rows parse and validate as core records), N8 (final
    README per-job list), the 6C N items and semantic-summary entity-kind
    validation routed in repairs.md, writing hard failures to integrity/, and
    per-bounded-window metric recompute. Wait for the user's answers before
    implementing. The dataset slice needs the user's 6G-1 approval and a
    stated download cap before any network access.

(d) Follow docs/agents.md ownership and the plan's 6F+6G internal order. Use
    the JDK 17 environment block for every sbt/Spark command. No AWS calls, no
    live LLM calls, ER with LLM adjudication disabled. Retain evidence under
    docs/agent-runs/phase-06/evidence/6fg/. Run one full sbt check on the
    stable tree at the end.

(e) Do not launch any reviewer, commit or push. At the end, return the
    Section 11 handoff packet and a complete 6F+6G reviewer prompt in one
    fenced block with every placeholder filled.

(f) Do ONLY 6F+6G, then stop and end the turn with: "Subphase 6F+6G is ready
    for review. I have stopped and will not start the next subphase until I
    receive the next prompt." Do not start 6I.


## Subphase 6F+6G — user-supplied external review

```text
VERDICT: REQUEST-CHANGES for Subphase 6F+6G. Three findings block, and none needs a change to production Spark code if the repair takes the evidence-only route.

I made no edits and ran no builds, tests or Spark jobs.

What checks out

- Tree state: HEAD is 6ae7378, the plan SHA-256 matches, and the inventories match (12 modified, 87 untracked). All 27 source snapshot hashes match the current files.
- Gate log: final-check.txt has the claimed size and SHA-256, ends with exit=0, and contains no FAILED lines.
- Ownership: every changed path maps to a single owner. Core went to domain, modules/spark to spark, datasets/** to dataset, tests/** to test, and docs/agent-runs to the coordinator. human-gate.md is untouched.
- Driver actions: the only collect calls are in BoundedActions.scala. There is no RDD, GraphX or implicits use.
- G1 hand-checks: I re-derived the expected deltas by hand and they match the independent test. That covers D's deltas, A leaving and G entering the largest component, the 10 temporal rows, and the 4 missing-endpoint count.
- Chain estimate: the three-node chain gives mean 4/3 and P90 2, matching the test.
- Dataset script: the script hash and slice hash match the manifest.

Blocking findings

F1 — Stage DAGs are not reported. Medium. Owner: coordinator for evidence, spark-engineer for any code. Blocking.
- Evidence: the course Phase 6 report list includes "stage DAGs", and the plan's Done-when says the report contains every item the course lists. real-data-report.md reports stage counts, partitions and shuffle only.
- Gap in the summarizer: the event-log-summary.json stage rows carry no parent IDs (Phase6EventLog.scala:74-80). The raw event log still has them, e.g. "Parent IDs":[3]. It is in ignored target/phase6-runs/6fg-spark-first-v2/.event-logs/.
- Accept when: a stage-DAG artifact (stage ID, name, parent IDs, partitions) exists for the successful run, is referenced from the real-data report, and the DAG gap is stated. Deriving it from the retained log needs no code change and no rerun. If instead the summarizer is changed, the run ID changes and the real run, replay and full gate must be redone.

F2 — The replay is not identical for analytics-report.json, and the evidence does not say so. Medium. Owner: spark-engineer for Phase6Report.scala, coordinator for the report. Blocking.
- Evidence: I diffed the first and replay reports. bridges[1].participationCoefficientP50P90[1] is 0.56 in one and 0.5595567867036011 in the other. Twelve *Mean values also differ in the last digits.
- Cause: percentile_approx (Phase6Report.scala:19) is partition-dependent, and the means sum floats in unordered aggregates.
- Impact: the 28 table hashes do match, but real-data-report.md quotes these distribution values and says the replay matches.
- Accept when: the report is added to replay-comparison.json and its differences are disclosed (approximate percentiles, float summation order), or exact percentiles are used. The same issue exists in the estimate P90 at Phase6DEJobs.scala:1040. It happened to match this time but is latent.

F3 — The source-scan test misses calls written without parentheses. Medium. Owner: test-engineer. Blocking, test-only fix.
- Evidence: the regex at IndependentPhase6SafetySpec.scala:29-30 requires ( after .collect, .head, .first, .toLocalIterator and .count. Scala 3 allows df.collect and df.head on Java and Scala 2 methods, so those evade the scan. .isEmpty and .reduce are not covered at all.
- Current state: no violation exists today, per my grep.
- Accept when: the scanner also flags the parenless and .isEmpty forms, with a self-test on synthetic source proving each is caught.

Non-blocking findings

- F4 — A failed run can't be retried. Low, spark-engineer or docs. Rerunning with the same config and code hits the existing root and fails with "incomplete; refusing overwrite" (Phase6Main.scala:49). The README line "a subsequent corrected run has a distinct ID" only holds if code or config changed. Document the manual cleanup step.
- F5 — Summary text is thin and one claim isn't grounded for long titles. Low, spark-engineer.
  - Researcher and path summaries carry no name, window or endpoints, which weakens embeddings in Phase 8.
  - Paper titles are cut at 900 characters with no marker (Phase6FGJobs.scala:364), so text can differ from the cited field. The test only covers G1.
- F6 — The continuity tie-break is not observable. Low. The README says ties go to the smaller community ID (README lines 99 and 164), but the row exposes only the overlap score. The test itself acknowledges this. Reword the README, or add a matched-community field in a later contract change.
- F7 — metrics/type=kcore is a byte-identical copy of researcher_collaboration. Low. Both have 62,757 rows and hash 9b185b97…. This is documented in the README, but the manifests propose loading both.
- F8 — Manifest proposals are loose. Low, spark-engineer.
  - The Neptune idProperty for coauthored_with_support is edgeId, which is not unique.
  - The DynamoDB partitionKey is the free-text string "researcherId or runId (dataset-dependent Phase 7 proposal)", although the README claims run-state keys.
  - Phase 7 validates these anyway.
- F9 — The LPA explanation is unverified. Low. The report attributes all non-convergence to two-person components, but 1,349 labels still changed in the last all-years iteration and no per-component convergence or pair count is retained. The workaround comment in Phase6DEJobs.scala:503 also states the Spark cause as fact, while the diagnosis file calls it an inference.
- F10 — The constraint-propagation workaround is not recorded and its cost is unmeasured.
  - spark.conf.set(...) at Phase6DEJobs.scala:506 changes the caller's shared session.
  - The setting is not in run-metadata.json, and its performance impact was not measured.
- F11 — Evidence is not lean. Low, human decision. It totals 5.0 MB, including a 1.36 MB final-check.txt and two ~424 KB event summaries. Plan rule 10 says to keep evidence lean.
- F12 — Minor housekeeping.
  - Two counters, ambiguousNonDblpMentions and ambiguousNonDblpMentionRows, have the same expression.
  - The coordinator ran scalafmt, which touches owner-owned files. This is disclosed.
  - The dataset Python tests (12/12) are not part of sbt check.

Unverified

- I did not reread the real Parquet. manifest-file-audit.json only checks that paths exist and that metadata matches.
- I did not read the bodies of Phase6CJobsSpec, Phase6DEJobsSpec, Phase6FGJobsSpec or the 6C/6D+6E test files beyond their test lists.
- I did not read all of Phase6CJobs.scala or Phase6CReaders.scala, only their diffs.
- I did not verify the Hadoop or ER outputs or the downloaded archive.
- The course "Detailed Spark requirements" section was cut off in my fetch, so the README per-job coverage is checked against the plan, not that section.

Report fields

STATUS: COMPLETE (review) — verdict REQUEST-CHANGES
OWNER: code-reviewer (independent, read-only)
WORK ORDER: Review Subphase 6F+6G, base/HEAD 6ae7378, plan SHA-256 6df6d856…5096
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git rev-parse/status/diff; shasum on plan, script, slice, final-check.txt and 27 snapshot files;
  grep for forbidden APIs; python3 -I JSON diffs of first vs replay reports; WebFetch of the course README
  (truncated); reads of the files named above. No build, test, Spark, AWS or model calls.
TEST RESULTS: Not rerun. Reported gate 551/0, exit 0, log hash and tail verified; no FAILED lines.
VALIDATION RESULTS: 27/27 source hashes match; replay-comparison 28/28 tables equal;
  analytics-report.json differs between runs (F2); counters identical.
ASSUMPTIONS: Scala 3 allows parenless calls to Java/Scala-2 methods (F3). Event-log Parent IDs read from the retained log.
RISKS: See F4–F12. Known limits (metadata-only reuse, fixed shards, local-artifact replay,
  LPA oscillation, sampled distances, store mappings as proposals) are disclosed accurately.
MANUAL ACTION REQUIRED: Route the repair round below. Do not commit as approved yet. 6I not started.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: F1 stage DAGs; F2 report replay comparison
NEXT GATE: Repair round, then a recheck review, then commit, then a separately requested 6I.

Next prompt

You are the main agent for ScholarChain Phase 6, Subphase 6F+6G repair round 1, in
/Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-6, base/HEAD 6ae7378cbef90a176fd1faecae0dee0615eba9e3, work uncommitted).
Plan: /Users/danny/Documents/plan/phase6.md (SHA-256 6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096). Use JDK 17 for every sbt/Spark command.
Do NOT start 6I. Do NOT launch a reviewer. Do NOT commit or push. Stop after this repair.

1. Append the external reviewer verdict (REQUEST-CHANGES, findings F1–F12) verbatim to docs/agent-runs/phase-06/review.md under
   "Subphase 6F+6G — user-supplied external review". Log the findings in repairs.md.
2. Route blocking findings to their owners:
   F1 (coordinator, spark-engineer only if code changes): produce a stage-DAG artifact (stageId, name, parentIds,
      partitionCount, per-stage task and shuffle totals) for the successful run from the retained raw event log under
      target/phase6-runs/6fg-spark-first-v2/.event-logs/. Save it under evidence/6fg/ and reference it from
      real-data-report.md. Preferred: evidence-only, no production change, so the run ID stays
      run:f02acf56-4bea-4009-adaf-b11d5afceb49. If Phase6EventLog is changed instead, the real run, replay and full
      gate must be redone and the run ID will change.
   F2 (spark-engineer for Phase6Report.scala, coordinator for evidence): add analytics-report.json to the replay comparison.
      Either compute exact percentiles or disclose that report percentiles and means are partition/float-order
      dependent and are excluded from the logical-identity claim. Correct real-data-report.md and
      replay-comparison.json so they no longer imply the report is identical. If production code changes, rerun and
      regate as above.
   F3 (test-engineer): harden IndependentPhase6SafetySpec so the scan also flags parenless .collect/.head/.first/
      .toLocalIterator/.count and .isEmpty/.reduce outside BoundedActions, with a synthetic self-test proving each is caught.
3. Nonblocking F4–F12: apply the cheap documentation fixes through the owning writer (README wording for F4, F6, F8;
   record the constraint-propagation setting and the LPA per-component caveat in the report for F9/F10). Record any
   item you leave open, with reasons. F11 is a human decision; list the evidence sizes and ask.
4. Rerun the affected tests and one full `sbt -batch check` on JDK 17 on a stable tree. Re-verify the source
   snapshot hashes, `git diff --check`, and that HEAD is unchanged. Report exact observed commands and results.
5. Update owner-report.md, test-report.md, repairs.md and evidence/6fg/handoff.md, and return a recheck reviewer prompt
   per plan Section 11 with every placeholder filled. Then end with: "Subphase 6F+6G repair round 1 is ready for
   review. I have stopped and will not start the next subphase until I receive the next prompt."
```

## Subphase 6F+6G repair round 1 — user-supplied external review

```text
VERDICT: APPROVE for Subphase 6F+6G repair round 1. The three blocking findings from the first review (F1–F3) are repaired. I found no new blocking issues.

I made no edits and ran no builds, tests or Spark jobs. Beyond reading the evidence, I recomputed the numbers from retained files.

Acceptance of the blocking findings

F1 — stage DAG: accepted.
- I re-parsed the retained raw event log (local-1792693895317, 24,040 records). It gives 5,667 stage IDs, 4,532 parent edges, no missing parents and no cycles. Every stage has a name and a partition count.
- The 2,004 executed attempts give 5,237 tasks, 0 failed, 12,020,965,863 shuffle-read bytes and 10,107,558,658 shuffle-write bytes, matching the original summary.
- stage-dag.json has 5,667 stage entries.
- stage-dag.md says plainly that its diagram is a subgraph, not the whole DAG.
- The report and the DAG file both state that the production summarizer still omits names and parents. This route needed no production change, as the review allowed.

F2 — replay scope: accepted.
- The two report hashes recorded in analytics-report-comparison.json match the actual files.
- My earlier diff also found 12 differences: 11 means and one percentile (0.56 vs 0.5595567867036011).
- replay-comparison.json now has allLogicalTablesEqual: true and allComparedArtifactsEqual: false, with a comparisonScope note.
- The top of real-data-report.md carries a "Replay scope correction", and the latent partition-dependence of the estimate's P90 is disclosed.
- The old "Completed replay" paragraph still says only that tables and counters match. That is true and sits under the correction.

F3 — source fence: accepted.
- Only IndependentPhase6SafetySpec.scala differs from the original 27-file snapshot. The other 26 hashes are identical, and all 27 current files match the repair snapshot.
- The scanner covers 11 driver methods, including isEmpty and reduce, with and without parentheses.
- Its identifier-boundary check lets collect_set, headOption and countDistinct through. It handles nested comments, escaped quotes and triple-quoted strings.
- The non-Spark exceptions are exact and tied to declarations. Three synthetic self-tests are added; the Safety target ran 7/7.

Gate integrity: accepted.
- final-check.txt is 1,358,928 bytes with SHA-256 3e665483…c5236, ends with exit=0, and has no FAILED lines.
- Counts are 144/64/39/34/266/7, which totals 554. Independent grew 263→266, matching the three new tests.
- HEAD and the plan hash are unchanged, and human-gate.md is untouched. review.md carries the verdict under "Subphase 6F+6G — user-supplied external review", and repairs.md logs F1–F12 with F4–F12 deferred.

New nonblocking observations

- Scanner gaps (Low, test-engineer). The scanner does not flag .tail, .toJavaRDD, .javaRDD or .toRdd. The existing \bRDD\b check misses toJavaRDD. Code inside s"${…}" interpolations is masked. Its doc comment already says it is a textual guard and not a parser.
- Handoff placeholder (trivial, coordinator). repair-1/handoff.md lines 22–23 contain an empty path, ``, where the evidence directory should be named.
- Evidence size (Low, human decision). repair-1 adds about 3.2 MB of evidence (stage-dag.json is 1.84 MB, final-check.txt 1.36 MB). The earlier F11 retention question was answered "blocking-only", so no cleanup was done.

Still open from the first review

F4–F12 are deferred by the user, so they remain open. Two of them matter for later phases:
- F4: rerunning with the same config after a failed run refuses to overwrite. The workaround is manual cleanup.
- F10: the Spark constraint-propagation setting is applied to the caller's session and is not recorded in run metadata.

Known limits, all disclosed accurately, are:
- reuse checks metadata only;
- fixed 256-shard hashing;
- replay on identical local artifacts only;
- LPA oscillation on isolated pairs;
- sampled distance estimates;
- store mappings as proposals;
- the yearless Neptune edge mapping;
- the EMR and packaging gates.

Report fields

STATUS: COMPLETE (recheck) — verdict APPROVE
OWNER: code-reviewer (independent, read-only)
WORK ORDER: Recheck 6F+6G repair round 1 (F1–F3); base/HEAD 6ae7378; plan SHA-256 6df6d856…5096
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git rev-parse/status/diff; shasum on plan and final-check.txt; python3 -I recomputation of the stage DAG
  from the raw event log, source-snapshot hash comparison, and report hash checks; reads of the files named above.
  No build, test, Spark, AWS or model calls.
TEST RESULTS: Not rerun. Reported 554/0, exit 0; log size/hash verified; Safety 7/7 per safety-targeted.txt.
VALIDATION RESULTS: F1 DAG numbers reproduced independently; F2 report hashes and 12 differences confirmed;
  F3 scanner and self-tests reviewed; 27/27 current files match the repair snapshot; only SafetySpec changed.
ASSUMPTIONS: Production fingerprint unchanged is inferred from identical production-source hashes and the metadata.
RISKS: F4–F12 deferred; the nonblocking items above; the known limits listed.
MANUAL ACTION REQUIRED: User commits Subphase 6F+6G. 6I only on a separate request.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: User commit, then a separately requested 6I close-out. Phase 6 closes only after the comprehensive
  review, `human-gate.md` and `commit.txt`.

Next prompt

You are the main agent for ScholarChain Phase 6 in /Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-6).
The independent reviewer returned APPROVE for Subphase 6F+6G repair round 1 (F1–F3 repaired and accepted; no new
blocking findings; base/HEAD 6ae7378cbef90a176fd1faecae0dee0615eba9e3, work uncommitted).

Do only this, then stop:
1. Append the reviewer's APPROVE verdict verbatim to docs/agent-runs/phase-06/review.md under
   "Subphase 6F+6G repair round 1 — user-supplied external review". Do not edit any human-owned file
   (human-gate.md, commit.txt).
2. Fix the empty path placeholder in evidence/6fg/repair-1/handoff.md lines 22–23. This is a coordinator-owned
   documentation edit and needs no gate.
3. Tell me the 6F+6G tree is approved and ask me to commit it. Do not commit or push yourself.
4. Do NOT start 6I, and do not run builds, tests or Spark.
End with: "Subphase 6F+6G is approved and awaiting the user's commit. I have stopped and will not start 6I until I receive a separate prompt."

After I commit, I will send a separate 6I prompt. It will cover: Step 0 questions, a fresh JDK 17 `sbt -batch check`,
the course-gate traceability table in owner-report.md with "bounded EMR Spark run" marked OPEN (deferred to
Phase 15), carrying F4–F12 forward as open or deferred items, and the comprehensive whole-Phase-6 reviewer prompt
covering 0349388 through the current tree including untracked files.
```

## Subphase 6I — comprehensive review pending

Coordinator status only; **not a reviewer verdict**. User started 6I after committing
approved 6F+6G as `d1afc7f6698965ddbe010621b277b10e655d25ff`. All received external
verdicts above remain verbatim. The comprehensive review must cover Phase-6 baseline
`03493882399e9020e6892c9f97e0ec8919365215` through the final working tree, including
untracked files. The coordinator does not launch that reviewer. Its copyable work
order will be retained at `evidence/6i/reviewer-prompt.md`. No whole-phase APPROVE,
human acceptance, EMR execution, or phase closure is claimed by this record.

## Subphase 6I — comprehensive whole-Phase-6 review — user-supplied external review

Recorded 2026-10-22. The earlier **comprehensive review pending** note is preserved as history and superseded by this external APPROVE on this date. Human acceptance and EMR execution remain open.

```text
Phase 6, Subphase 6I: whole-phase review

1. VERDICT: APPROVE for 6I and the comprehensive Phase 6 local implementation. I found no blocking defect.

- Local implementation: Jobs 1–11, the CLI, the Parquet export, the manifests, and the independent and module tests are consistent with the plan and the course Phase 6 / Detailed Spark text.
- Not covered by this APPROVE:
  - The bounded EMR Spark run is OPEN, deferred to Phase 15 by user decision, with the script in Phase 13. No cloud runtime has been tested.
  - The human gate is pending: human-gate.md, the commit, and commit.txt.
  - The Codex/Cursor workflow deviation is not instructor-approved.
- EMR fact for the human:
  - The 6a/emr-compatibility.md memo cites EMR 7.x Spark 3.5.x as Scala 2.12. This repo is Scala 3 against spark-sql_2.13.
  - No compatible runtime has been selected or tested. Phases 13 and 15 need a custom runtime, and I treat that as a real schedule and cost risk.
  - The course work order lists the bounded EMR run, although its Gate bullets do not. Accepting the deferral is therefore a human decision about a work-order item.

2. Findings. None is blocking. Items already registered in repairs.md:270-322 are re-confirmed as open and unchanged: 6FG F4–F12, the scanner blind spots, 6A F4/F6/F8, EMR alignment, and the yearless Neptune mapping.

#: N1
Sev: Med
Path:line: Phase6DEJobs.scala:335-406; real-data-report.md:72-79; README.md:79; Phase6DEJobsSpec.scala:311-359
Evidence: Final changed-label counts are 372/430/504/1349/793/524 (sum 3972 matches counters.json). Each isolated pair contributes exactly 2 changed
labels, but 1349 and 793 are odd. So oscillation is not confined to two-person components. The module test asserts that an isolated pair becomes
two singleton communities.
Impact: Real community, cross-community-edge, bridge and continuity outputs are iteration-limited. Each two-person component's only edge is reported
as cross-community. The report and README wording suggests pairs explain the non-convergence.
Owner: spark-engineer (tie rule or damping), coordinator (wording)
Acceptance: Either a converging rule on pair, bipartite and real windows, or per-component non-convergence counts (F9) plus a recorded rule that
Phase 7–9 consumers show Converged: false and do not present it as a result.
Block: No. Plan §7.7 allows documented non-convergence. The 6D+6E R1-O1 observation was accepted.
────────────────────────────────────────
#: N2
Sev: Low–Med
Path:line: Phase6DEJobs.scala:1040, :1055
Evidence: The distance P90 uses percentile_approx inside a hashed logical table, but the method string says "empirical P90". The distance domain is a
tiny integer set, so an exact percentile is cheap. The replay matched by observation only.
Impact: Latent partition dependence in a logical table.
Owner: spark-engineer
Acceptance: Exact P90 with a test at differing shuffle partitions, or an explicit "approximate" label. A code change alters the fingerprint, so it
needs a regate and a new run.
Block: No. This is the already-disclosed 6FG F2 latent risk, not silently closed.
────────────────────────────────────────
#: N3
Sev: Low
Path:line: er-resolution-manifest.json outcomeCounts; counters.json; real-data-report.md:29,149; traceability rows J1/J2
Evidence: The ER export had zero Researcher decisions of any kind and 1 accepted Work link (12,123 conflict, 1,627 unresolved). Real counters for
crossDblpNameLinksNotApplied, constraintBlockedWorkGroups, selfPairsDropped, duplicateTeamMembersCollapsed and
nonAuthoritativeDblpObservationsDropped are all 0.
Impact: The report says only "0/0 researcher unresolved/conflict", which could imply real researcher linking ran. Identity-merge and constraint
branches are exercised only by fixtures and the tiny pipeline.
Owner: coordinator
Acceptance: One sentence plus these counters in real-data-report.md and the J1 row.
Block: No
────────────────────────────────────────
#: N4
Sev: Low
Path:line: README.md:9, :35; Phase6CJobs.scala:477, :902-924
Evidence: The Job 1 plan says "repartition at canonical keys after grouping; cache only mapping and teams". The code has no such repartition (only
Job 2 at :477) and caches about 20 tables. README.md:9 still says "will own". Jobs 9 and 10 say "cache only as measured".
Impact: The course's per-job documentation must match the code. The D05–D08 rows rely on it.
Owner: spark-engineer
Acceptance: README reflects the actual joins, repartitions and caches.
Block: No
────────────────────────────────────────
#: N5
Sev: Low
Path:line: Phase6Report.scala:13; Phase6Main.scala:85; Phase6Export.scala:43, :296
Evidence: The driver caps (10,000 and 256) are call-site literals, not config. The plan §6.5 says "explicit config limit". Real runs had 61 counters,
so they are safe.
Impact: Minor drift from the plan rule.
Owner: spark-engineer
Acceptance: Name the caps as constants or config.
Block: No
────────────────────────────────────────
#: N6
Sev: Low
Path:line: Phase6Plans.scala:10-11
Evidence: The global var destination is not thread-safe.
Impact: Only a risk if suites ever run in parallel.
Owner: spark-engineer
Acceptance: Pass the path explicitly.
Block: No
────────────────────────────────────────
#: N7
Sev: Info
Path:line: git log (6ae7378, d1afc7f); diff-check.txt
Evidence: Commit titles say "spark-engineer" but include core, tests and datasets paths. Path ownership itself is intact. Full-diff --check exit 2
comes from 188 hits in 17 raw evidence logs (verified). Evidence is about 15.9 MB, with three 1.36 MB gate logs.
Impact: Process and retention only. Same as F11.
Owner: human
Acceptance: A human decision on retention.
Block: No

Scheduled later work (not new 6I scope):
- Store-key validation and yearless Neptune mapping (Phase 7).
- Summary richness and title-truncation marker (before Phase 8).
- Runtime Scala alignment and a JDK-guarded packaging path (Phases 13–15).
- Refreshing the wrong-JDK evidence.

3. Required report fields

STATUS: COMPLETE (review) — verdict APPROVE (local implementation); EMR gate and human gate open
OWNER: code-reviewer (independent, read-only)
WORK ORDER: Comprehensive Phase 6 review, baseline 0349388…, HEAD d1afc7f + working tree + untracked
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git rev-parse/status/diff/diff --name-status/diff --check/log/show; shasum on the plan and final-check.txt;
  curl of the raw course README (read-only, sha 6a0eddad… equals course-source.json);
  python3 -I read-only audits: 68 snapshot hashes vs files vs HEAD; snapshot vs diff set; mtimes vs gate start;
  retained run markers, 28-table hash equality, counters and analytics-report diff, event-log sums;
  diff-check path attribution; secret-pattern grep; git ls-files; Read of source, tests, evidence.
  One Bash call was blocked by the project guard hook (it names a .claude/ path in a read-only check);
  I did not retry it and removed that reference.
  No build, test, Spark, dataset, AWS, model or store command was run.
TEST RESULTS: NOT RERUN. Reported 554/0 (144/64/39/34/266/7), exit 0 — verified from final-check.txt:
  SHA e2bf289d…d7367, 1,359,860 bytes, per-module "Tests: succeeded" lines, [success] 673 s, real 675.13, exit=0;
  the injected-failure trace is the expected build self-test.
VALIDATION RESULTS:
  - Plan SHA 6df6d856… matches; HEAD is d1afc7f; tracked inventory is 241 (232 A + 9 M) and 14 untracked, as claimed.
  - The 68 non-evidence changes equal the snapshot set exactly. All hashes match, equal HEAD, and all mtimes precede the gate start (newest 19:16Z vs 19:52:50Z).
  - Nothing is changed under hadoop, entity-resolution, .claude, Phase 5 or other docs. Core changes are additive (IDs and versions); no frozen formula or wire field was altered.
  - Production driver actions: only the two `collect()` calls in BoundedActions; no RDD, GraphX, implicits or Encoders. `.limit` calls are bounded or row-limiting.
  - Retained real run: both completion markers verify. 28/28 row counts and content hashes match, 61/61 counters are identical, and the 12 analytics-report differences are reproduced exactly (11 means, 1 percentile).
  - Event-log sums reproduce 5,237 tasks, 0 failed, 12,020,965,863 B shuffle read and 10,107,558,658 B write.
  - Algorithms checked against plan §7: DBLP-name identity, cannot-link and authority blocking, rank-1 DBLP team, distinct-work weights, W==T, min-label components, h-index coreness, synchronous weighted LPA with smallest-label tie, bridge formulas, BFS smallest-immediate-predecessor, seeded estimate, adjacent-window deltas.
  - Independent G1 is a literal transcription of plan §8, and the summary test parses every number against its cited field.
  - `git diff --check` is 0 for the current tree and the non-evidence diff; the full diff gives 2 because of raw logs only.
  - No secret patterns found.
ASSUMPTIONS: The retained ignored target/phase6-runs data is the run the report describes; its metadata and counters were checked.
RISKS: N1–N7; registered F4–F12; scanner blind spots; metadata-only reuse; 256-shard executor buffering measured at bounded scale only;
  identical local build artifacts only; stock EMR is Scala 2.12 with no selected runtime; Codex workflow not instructor-approved.
MANUAL ACTION REQUIRED: Human writes human-gate.md, explicitly accepts the EMR deferral, commits and records commit.txt.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: Human acceptance (EMR deferral, workflow deviation, retention), commit, then Phase 7 only on a separate prompt.

Independently checked: gate log, hashes and mtimes, inventories, ownership, additive core changes, driver-action and Spark API rules, algorithm bodies, G1 and summary tests, and the retained run (markers, tables, counters, report diff, stage sums).

Not independently checked:
- Parquet content, because no reader was available and I ran no Spark.
- The Hadoop and ER output bytes, and the downloaded archive.
- The Python dataset tests.
- The full text of every earlier-subphase gate log and every module test body.

4. NEXT PROMPT

You are the coordinator for ScholarChain Phase 6, Subphase 6I close-out, in
/Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-6, HEAD d1afc7f6698965ddbe010621b277b10e655d25ff;
the working tree holds only uncommitted docs/agent-runs/phase-06 evidence).
Plan: /Users/danny/Documents/plan/phase6.md (SHA-256 6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096).

The user-supplied external comprehensive reviewer returned APPROVE for the local Phase 6 implementation:
no blocking findings; EMR and human gates open. Do ONLY the following, then stop.

1. Append the reviewer's verdict VERBATIM (verdict, findings N1–N7, report fields, this prompt) to
   docs/agent-runs/phase-06/review.md under "Subphase 6I — comprehensive whole-Phase-6 review — user-supplied external review".
   Replace nothing; keep the existing "comprehensive review pending" note as history and mark it superseded by date.
2. Update docs/agent-runs/phase-06/repairs.md dispositions only (no implementation):
   - Register N1–N7 as OPEN, nonblocking, with their named owners and gates:
     N1 LPA convergence/oscillation beyond isolated pairs (spark-engineer; before Phase 7–9 consumers);
     N2 distance P90 percentile_approx (spark-engineer; regate if code changes);
     N3 report/J1 clarity on zero real researcher ER links (coordinator);
     N4 README versus code drift in Job 1/9/10 (spark-engineer);
     N5 driver caps as literals (spark-engineer);
     N6 Phase6Plans global var (spark-engineer);
     N7 commit-title attribution and evidence retention (human).
   - Keep 6FG F4–F12, the scanner blind spots, 6A F4/F6/F8, the EMR/Scala alignment item and the yearless Neptune mapping OPEN and unchanged.
   - Mark "Comprehensive APPROVE" as received from the independent reviewer; mark "Human close-out" PENDING.
3. Optionally (docs only, your own territory): add a short N3 sentence to the 6I section of owner-report.md stating the ER outcome counts
   (Researcher decisions all 0; Work accepted 1, conflict 12,123, unresolved 1,627) and that identity-merge branches are fixture-evidenced.
   Do not edit retained evidence logs, source, tests, datasets, build files, or any human-owned file.
4. Do NOT write or edit human-gate.md, commit.txt or accepted-commit.md. Do NOT commit or push. Do NOT launch a reviewer.
   Do NOT run builds, tests or Spark jobs (docs-only edits; the 554/0 gate and implementation hashes remain valid).
   Do NOT start Phase 7.
5. Final message: summarize edits, then ask the HUMAN to do the following themselves:
   a. Write docs/agent-runs/phase-06/human-gate.md stating, in the human's own words:
      - the decision to accept Phase 6 local implementation, citing the 554/0 gate and the comprehensive APPROVE;
      - explicit acceptance (or rejection) of the open gate "bounded EMR Spark run — deferred to Phase 15, script in Phase 13",
        including the known risk that stock EMR 7.x Spark 3.5 is Scala 2.12 while this repo is Scala 3 / spark-sql_2.13 with no selected runtime,
        and that the course work order lists the bounded EMR run;
      - acceptance of the Codex/Cursor-led workflow deviation (no instructor approval is claimed);
      - the retention decision for evidence (about 15.9 MB; raw logs with trailing whitespace) and the open N1–N7 / F4–F12 register.
   b. Commit the accepted artifacts, then record the commit SHA in commit.txt (and accepted-commit.md if desired).
   c. Send a separate prompt before any Phase 7 work.
Then end with: "Subphase 6I close-out is ready for human acceptance. I have stopped and will not start Phase 7 until I receive a new prompt."
```

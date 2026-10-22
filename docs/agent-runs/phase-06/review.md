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

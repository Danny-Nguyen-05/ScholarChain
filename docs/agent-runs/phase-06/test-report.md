# Phase 6 test report

## Subphase 6A

STATUS: COMPLETE for the required 6A local gates; external review pending.

OWNER: Coordinator `/root`, assembling exact observed build and Spark owner results.

WORK ORDER: Establish baseline, test the Java 17 guard, compile and execute one Spark smoke test, verify package contents, and run a final JDK 17 `sbt check` on a stable 6A tree.

FILES CREATED: `docs/agent-runs/phase-06/evidence/6a/baseline-check.txt`, `first-final-check-format-failure.txt`, `second-final-check-format-failure.txt`, `third-final-check-compile-failure.txt`, `final-check.txt`, `build-targeted-first-failure.txt`, `build-targeted.txt`, `build-format.txt`, `spark-reflect-targeted.txt`, `jdk-guard.txt`, `final-package.txt`, `spark-job-jar-contents.txt`, `preflight.md`, and `emr-compatibility.md`.

FILES MODIFIED: None outside the new Phase 6 evidence/report directory by this report owner.

COMMANDS RUN: Exact coordinator full-gate command in the repository root, twice with exit 0 and three intermediate failed repair attempts:

```bash
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6a-baseline.txt 2>&1
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6a-final-check.txt 2>&1
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'sparkAnalytics/sparkJobJar' > /private/tmp/scholarchain-phase6a-package.txt 2>&1
```

The failed full-check attempts used the same second command and are retained separately before the output path was reused. Build and Spark owner commands and results are recorded in `owner-report.md` and their named evidence logs. The JDK 27 `sbt -batch check` guard probe exited 1 by design. `git diff --check` exited 0. `jar tf` on the final artifact exited 0 and populated `spark-job-jar-contents.txt`.

TEST RESULTS: Baseline log: 129 core + 64 Hadoop + 39 entity-resolution + 233 independent + 4 build-verification = **469 passed**, zero failed; `[success] Total time: 412 s`, `real 413.74`. Final log: 129 core + 64 Hadoop + 39 entity-resolution + 1 Spark + 233 independent + 7 build-verification = **473 passed**, zero failed; `[success] Total time: 422 s`, `real 424.08`. Targeted Spark smoke and build-verification rerun passed 1/1 and 7/7. Failed attempts stopped at Spark test formatting, build helper formatting, and missing Scala reflection types during Spark test compilation; each has a retained log. The expected injected format-stage failure is a passing build-verification self-test, not a failed final gate.

VALIDATION RESULTS: Java 17.0.20.1 was observed. Java 27 check stopped at `checkJava17` with a clear `requires Java 17; found Java 27` message before formatting or tests. Final package task logged `Verified Spark job JAR` and exited 0; archive listing has 5,467 entries and no Spark/Hadoop class paths. The new smoke test covers an explicit five-row schema, join, aggregation, window ranking, Parquet round trip and checkpoint with exact expected rows.

ASSUMPTIONS: Fixture-sized `collect()` in the Spark test is allowed by plan Section 6.5. This is a local JDK 17 smoke test, not a distributed graph or EMR validation.

RISKS: Full-gate success does not establish stock EMR runtime compatibility. The final package has no production Spark class in 6A. No later-subphase graph behavior has been exercised.

MANUAL ACTION REQUIRED: Independent user-run code review, then user commit if approved.

BLOCKED-ON OWNER: None for local 6A test gates.

BLOCKED-ON EVIDENCE: None; cloud runtime is unverified and documented separately.

NEXT GATE: Read-only 6A review; stop before 6B.

## Subphase 6A — repair round 1

STATUS: COMPLETE for F1–F3 local repair gates; external recheck pending.

OWNER: Coordinator `/root`, assembling build and test owner results. The test-engineer owns the new independent probe; the build-engineer owns JVM/packaging settings and their module-local verification.

WORK ORDER: Verify independent Spark startup on JDK 17, preserve all 233 prior independent tests, eliminate duplicate SLF4J providers and Logback from the Spark job JAR, record F3 runtime alignment research, and rerun the full gate. The user expressly limited repairs to F1–F3 and approved one new `tests/**` probe.

FILES CREATED: `evidence/6a/repair-1/preflight.md`, `f3-research.md`, `build-format.txt`, `targeted-before-log-config.txt`, `independent-before-log-config-excerpt.txt`, `targeted-final.txt`, `independent-classpath-proof.txt`, `final-check.txt`, `final-package.txt`, and `spark-job-jar-contents.txt`.

FILES MODIFIED: `test-report.md` and other coordinator-owned Phase 6 report/evidence files. Implementation ownership is detailed in `owner-report.md`.

COMMANDS RUN: The coordinator's final commands from repository root were:

```bash
/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java -version
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6a-repair1-final-check.txt 2>&1
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'sparkAnalytics/sparkJobJar' > /private/tmp/scholarchain-phase6a-repair1-package.txt 2>&1
/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/jar tf modules/spark/target/spark-job_3-0.1.0-SNAPSHOT.jar
shasum -a 256 modules/spark/target/spark-job_3-0.1.0-SNAPSHOT.jar
git diff --check
```

These exited 0. The `jar tf` output is retained in `repair-1/spark-job-jar-contents.txt`. `rg` checks against that listing found no Spark, Hadoop, Logback or SLF4J-provider paths (no matches, exit 1). `rg` against the final gate found no `SLF4J(W)` or `DEBUG` lines (no matches, exit 1). Build-owner targeted commands and output are summarized in `owner-report.md` and retained in `repair-1/targeted-final.txt`; an earlier `independentTests / Test / test` passed before the final logging resource and is represented by `repair-1/independent-before-log-config-excerpt.txt` rather than a 3.2 MB raw debug log.

TEST RESULTS: Targeted `SparkJobJarSpec` 2/2, independent Spark probe 1/1, Spark smoke 1/1. An intermediate independent suite passed 234/234, including the 233 existing tests. The final stable-tree `sbt -batch check` passed **474 tests**, zero failed: core 129, Hadoop 64, entity resolution 39, Spark smoke 1, independent 234, build verification 7. The sbt log reported 416 seconds; `/usr/bin/time` reported `real 418.33`. The new independent test asserts a three-row Spark range filtered to two rows and stops the session in `finally`.

VALIDATION RESULTS: `show independentTests / Test / fork` printed `true`. `show independentTests / Test / javaOptions` printed `-Xmx2g`, Spark UI disablement and all 15 required `--add-opens` options. The filtered classpath excerpt includes the sparkAnalytics project classes, `spark-sql_2.13-3.5.4.jar`, `scala-reflect-2.13.14.jar`, and a `log4j-slf4j2-impl` provider; the build source removes direct Logback from Spark test projects. Final `sbt check` output shrank to 244,600 bytes and had no duplicate-provider or DEBUG lines. Rebuilt JAR: 4,798 entries, 10,203,322 bytes, SHA-256 `a30b9f1c373febf3b245911ae533d582d15fadf52074dda287b40d75b504d7e0`; no forbidden Spark/Hadoop/Logback/provider paths.

ASSUMPTIONS: The dedicated WARN-level log4j2 test configuration keeps Spark test logs bounded without changing graph behavior. F3's Scala patch analysis relies on official published compatibility guidance and does not validate a specific cloud runtime.

RISKS: The earlier wrong-JDK probe was not rerun in this user-limited round (F4 deferred); packaging is not Java-17-guarded (F6 deferred). No EMR or custom runtime test was run. The final 6A package has no production Spark job class.

MANUAL ACTION REQUIRED: User-run independent repair recheck; do not commit or start 6B until approval.

BLOCKED-ON OWNER: None for the requested local repairs.

BLOCKED-ON EVIDENCE: None for F1–F3. F4–F9 dispositions appear in `repairs.md`.

NEXT GATE: Read-only 6A repair-round recheck, then user decision. Stop before 6B.

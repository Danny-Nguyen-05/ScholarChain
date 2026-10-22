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

## Subphase 6B

STATUS: COMPLETE for the observed local 6B gates; independent review pending.

OWNER: Coordinator `/root` for the full gate and retained log; `domain-engineer` for core-targeted tests; `spark-engineer` for README validation.

WORK ORDER: Validate the additive 6B contracts and wire examples, preserve existing examples, run the repository's full `sbt check` on JDK 17, and report only observed results.

FILES CREATED: `evidence/6b/preflight.md`, `evidence/6b/pre-hardening-check-excerpt.txt`, and `evidence/6b/final-check.txt`.

FILES MODIFIED: This `test-report.md` 6B section.

COMMANDS RUN: From repository root, the coordinator ran `/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java -version` (exit 0, OpenJDK `17.0.20.1`). It ran the following full-gate shell command twice before ID-helper hardening:

```bash
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6b-final-check.txt 2>&1
```

The first sandboxed attempt exited **1** before build startup with `java.io.FileNotFoundException: /Users/danny/.sbt/boot/sbt.boot.lock (Operation not permitted)` and `real 0.19`; it was not a test failure. An approved retry allowed the existing sbt cache lock and exited **0**, passing 479/479 before the final ID-helper hardening. Its test-count summary is retained in `pre-hardening-check-excerpt.txt`. After the domain owner hardened the ID helper and passed targeted 6/6, the coordinator ran the final stable-tree command:

```bash
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6b-final-check-stable.txt 2>&1
```

It exited **0**. `cp /private/tmp/scholarchain-phase6b-final-check-stable.txt docs/agent-runs/phase-06/evidence/6b/final-check.txt` exited 0; `wc -c` reported 244,815 bytes. `rg -n 'Total number of tests run:|Tests: succeeded|\[success\] Total time:|^real ' docs/agent-runs/phase-06/evidence/6b/final-check.txt` exited 0 and gave the counts below. `git diff --check` exited 0. The domain owner reported JDK 17 `sbt -batch 'core/Test/runMain edu.uic.cs441.scholarchain.core.WriteSparkAnalyticsExamples' 'core/scalafmt' 'core/Test/scalafmt' 'core/testOnly *SparkAnalyticsContractSpec'` (exit 0, targeted 5/5), `sbt -batch 'core/Test/scalafmt' 'core/scalafmtCheck' 'core/Test/scalafmtCheck' 'core/test'` (exit 0, core 134/134 before hardening), and `sbt -batch 'core/scalafmt' 'core/Test/scalafmt' 'core/scalafmtCheck' 'core/Test/scalafmtCheck' 'core/testOnly *SparkAnalyticsContractSpec'` (exit 0, targeted 6/6 after hardening). These targeted runs are owner-reported; the coordinator retained the complete final full-gate log.

TEST RESULTS: The retained final full gate shows core **135/135** (lines 156–158), Hadoop **64/64** (898–900), entity resolution **39/39** (948–950), Spark smoke **1/1** (958–960), independent **234/234** (2113–2115), build verification **7/7** (2155–2157): **480 passed, zero failed**. `[success] Total time: 417 s` at line 2160 and `real 418.74` at line 2161. Core-targeted Spark analytics contract tests were 6/6 after hardening. The domain owner's first core suite reported 133/134 due to an old two-version manifest assertion; it updated the assertion for the new Spark config version and the rerun plus final gate passed. The full log's deliberate injected failure traces belong to existing failure-path tests; the gate process exited 0.

VALIDATION RESULTS: Full check included formatting, compilation, all module and independent tests, and build verification. The new wire round-trip suite checks all 16 Spark examples, the legacy `CoauthorEdge`/`ResearcherMetrics` examples, DBLP-name IDs, G1 arithmetic values, config defaults/fingerprint/invalid inputs, yearless all-years edges, entering temporal rows with absent deltas, and rejection of LF-ambiguous ID inputs. The Spark owner confirmed all 11 README job sections and links to published core examples. No production Spark graph job or bounded data run was executed in 6B.

ASSUMPTIONS: The default config resource names illustrative local producer roots, not a completed run. Runtime graph invariants, physical plans and cloud linkage await later subphases.

RISKS: The initial sandbox lock failure leaves no separate retained raw log because the retry reused the same temporary path; its observed stack trace and exit are recorded above. The full retry log is retained. Existing 6H compatibility and live-run gates remain open.

MANUAL ACTION REQUIRED: User launches independent read-only 6B review, then commits an approved subphase. No agent commit or push.

BLOCKED-ON OWNER: None for the completed local gate.

BLOCKED-ON EVIDENCE: None for the completed local gate; production Spark behavior remains future scope.

NEXT GATE: Independent 6B review. Stop before 6C.

## Subphase 6B — repair round 1

STATUS: COMPLETE for F1–F4 local test and validation gates; external recheck pending.

OWNER: Coordinator `/root` ran and retained the final gate and affected targeted suite. `domain-engineer` `/root/domain_6b_r1` ran the owning core tests before handoff; `spark-engineer` `/root/spark_design_6b_r1` checked documentation.

WORK ORDER: Recheck the user-requested F1–F4 repairs on the stable uncommitted 6B tree under JDK 17, retain the full `sbt check` output, and record exact observed results. Base/current HEAD is `bc1e4a17fc879b7aac254b28d83e78dbdd34e367` on `phase-6`.

FILES CREATED: `evidence/6b/repair-1/final-check.txt` (245,188 bytes, SHA-256 `04242ca79489287144a656a20952ddba4b7b631b4efb4884b3bad634bacb0ce9`) and `evidence/6b/repair-1/targeted-contract.txt`.

FILES MODIFIED: This `test-report.md` section; the implementation and wire snapshot edits are itemized in `owner-report.md`.

COMMANDS RUN: From repository root, the coordinator ran:

```bash
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6b-repair1-final-check.txt 2>&1
cp /private/tmp/scholarchain-phase6b-repair1-final-check.txt docs/agent-runs/phase-06/evidence/6b/repair-1/final-check.txt
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'core/testOnly *SparkAnalyticsContractSpec' > docs/agent-runs/phase-06/evidence/6b/repair-1/targeted-contract.txt 2>&1
git diff --check
```

Each command exited **0**. The domain owner also reported a targeted 11/11 and full core 140/140 after regenerating the semantic-summary wire snapshot; the coordinator's retained targeted and full logs independently confirm those counts. The owner's first targeted run failed on the stale snapshot before it was updated; no raw intermediate output was retained by the coordinator. No later implementation edit followed the coordinator's final full gate.

TEST RESULTS: The full log shows core **140/140** (lines 161–163), Hadoop **64/64** (903–905), entity resolution **39/39** (953–955), Spark smoke **1/1** (963–965), independent **234/234** (2118–2120), build verification **7/7** (2160–2162): **485 passed, zero failed**. `[success] Total time: 416 s` is at line 2165; `real 418.15` is at line 2166. The log starts with `sbt 1.10.7 (Homebrew Java 17.0.20.1)`. The targeted contract log has 11/11 (lines 19–21) and exit 0. The injected `checkProbeInjectFailure` error lines are expected output of the build verification self-test; the full command exited 0.

VALIDATION RESULTS: The targeted suite exercises the added F1 negative metric cases, F2 window-bound citation-compatible summary ID, F3 ID/config/G1 cases and F4 cited Spark edge ID. The full check also includes formatting and unchanged suites. `git diff --check` found no whitespace errors. No Spark graph production job or cloud runtime was run in 6B.

ASSUMPTIONS: Core wire snapshots are contract examples. A passing contract gate does not prove later Spark producers emit the intended rows.

RISKS: F5–F8 are explicitly deferred with owners and gates in `repairs.md`; the yearless Neptune edge mapping remains a Phase 7 design item. The final log retains expected injected failure traces which are not a gate failure.

MANUAL ACTION REQUIRED: The user launches an independent read-only recheck and decides whether to approve and commit 6B.

BLOCKED-ON OWNER: None for F1–F4 local test gates.

BLOCKED-ON EVIDENCE: None for local gate; later producer/export/runtime behavior has not been tested in 6B.

NEXT GATE: User-run read-only 6B repair-round recheck. Stop before 6C.

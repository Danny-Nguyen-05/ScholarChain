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

## Subphase 6C — final local gate

STATUS: COMPLETE; final JDK 17 gate passed on the stable 6C tree, external review pending.

OWNER: Coordinator `/root` ran the final full check, local smoke and Spark module targeted checks. The domain, Spark and test owners ran their own targeted checks as described in `owner-report.md`.

WORK ORDER: Verify Subphase 6C jobs 1–2, the F6/F7 core helpers, independent G1 cases, real completed Hadoop/ER input smoke, source rules and the full repository gate. Branch `phase-6`, base/current HEAD `01d204b531d3fc72a5c49f884980a5c7c8926b18`.

FILES CREATED: Under `evidence/6c/`: `preflight.md`, `er-export.txt`, `independent-initial-failure.md`, `independent-targeted-final.txt`, `graph-wire-initial-failure.txt`, `module-targeted-compile-failure.txt`, `local-smoke-initial-classpath-failure.txt`, `local-smoke-checkpoint-failure.txt`, `publish-provenance-initial-failure.txt`, `interrupted-gate.md`, `module-targeted-final.txt`, `local-smoke-validated.txt`, `local-run-manifest.json`, `coauthored-with-plan.txt`, `input-rejects-plan.txt`, `event-log-summary.json`, and `final-check.txt`. The full final gate log is 247,609 bytes, SHA-256 `3e2fd5453af35cdf4b7e0f88c1ed4e3d273dd57325fe734cd7eb9e54538682c4`. Local input/output records are ignored under `target/`.

FILES MODIFIED: This `test-report.md`; implementation and other evidence-report edits are itemized in `owner-report.md`.

COMMANDS RUN: From the repository root, `JAVA_HOME` was `/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`, `PATH` prepended `$JAVA_HOME/bin`, and `SBT_OPTS` was `-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml` for each sbt command. The preflight `java -version` exited 0 and printed Homebrew OpenJDK 17.0.20.1. Exact coordinator final commands were:

```bash
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch 'sparkAnalytics/Compile/scalafmt' 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/Compile/scalafmtCheck' 'sparkAnalytics/Test/scalafmtCheck' 'sparkAnalytics/testOnly *Phase6CJobsSpec' > /private/tmp/scholarchain-phase6c-publish-provenance-targeted-retry.txt 2>&1
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch 'sparkAnalytics/Test/runMain edu.uic.cs441.scholarchain.spark.Phase6CMain target/phase6-inputs/6c-spark-config-provenance.json' > /private/tmp/scholarchain-phase6c-local-smoke-provenance.txt 2>&1
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6c-final-check-provenance.txt 2>&1
cp /private/tmp/scholarchain-phase6c-final-check-provenance.txt docs/agent-runs/phase-06/evidence/6c/final-check.txt
git diff --check
```

All five final commands exited **0**. The coordinator also ran the existing Phase 5 offline resolver with `--llm-mode disabled` against the approved Hadoop root; its exact invocation and exit-0 output are in `evidence/6c/er-export.txt`. It produced a completed ER export with 18 comparisons, 3 accepted researcher links, 6 accepted work links and zero fake/live LLM calls. The domain owner reported `core/testOnly *SparkAnalyticsContractSpec` 13/13 and `core/test` 142/142, exit 0. The test owner reported `independentTests/testOnly *IndependentPhase6CGraphSpec` 4/4, exit 0, retained in `independent-targeted-final.txt`. The coordinator's final module log has 6/6, exit 0, real 21.54 s; final smoke log has exit 0, real 20.05 s.

TEST RESULTS: In `final-check.txt`, core **142/142** (lines 163–165), Hadoop **64/64** (905–907), entity resolution **39/39** (955–957), Spark **7/7** (980–982), independent **238/238** (2148–2150), build verification **7/7** (2190–2192): **497 passed, zero failed**. `[success] Total time: 458 s` is line 2195 and `real 459.53` line 2196. The log header shows sbt 1.10.7 and Java 17.0.20.1. The build-verification injected failure and fake-S3 rename stack traces exercise expected failure paths; the full process exited 0.

VALIDATION RESULTS: The module suite checks G1 weighted edges and counters; yearless/2027 all-years behavior; malformed JSON rejection, retained source path and published provenance; schema mismatch; Hadoop/ER frozen-wire reads; ER `prepCompletionHash` binding to the selected Hadoop run; and completed-output reuse/mismatch gates. Independent tests assert literal G1 results and adversarial cross-DBLP, cannot-link and enrichment-only cases. The final smoke used `target/phase4-runs/ccd26111-d26d-4783-bc0f-e7106e4e617d` and matching disabled-mode ER export. It produced the deterministic `run:50e1fc99-a22c-4993-9525-7772e6af1fac` in a fresh ignored output root: 6 weighted edges, 6 support rows, 0 integrity rows, 0 input rejects and 21 counters. The 12 formatted plans and a bounded SparkListener task/stage summary were written locally; representative plans, manifest and summary are retained under `evidence/6c/`. Source scan: only `BoundedActions` contains production `collect()` calls, each capped; no RDD, GraphX, GraphFrames, Spark implicits or typed case-class encoder use was found. Final `git diff --check` exited 0. All implementation source mtimes preceded the final gate.

ASSUMPTIONS: The ER resolver's `prepCompletionHash` formula is SHA-256 of the exact Hadoop completion-marker text, a newline and the exact run-manifest text; the module positive/missing/mismatched tests and the real smoke validate the reader's implementation. The task summary is a local listener aggregate; the local Spark event file was disabled. Jobs 3–11 and cloud execution are outside 6C.

RISKS: Earlier attempts are disclosed rather than counted as final passes. The independent owner's first targeted attempt aborted with Java heap OOM, then a second attempt was canceled amid memory warnings; the final targeted and full suites passed after fixture-session and lineage changes. An earlier graph-wire test omitted null fields in its JSON projection; a compile attempt used a wrong `Success` import; a refreshed smoke checkpointed before setting the Spark checkpoint directory; and a reject-source test found an empty path after caching. Each was fixed and the final gates passed. The first full gate passed 496/496 on a prior tree. A second full gate was canceled (exit 130) after the coordinator found missing top-level provenance on published rows; its partial output is not treated as a result. `sparkAnalytics/runMain` lacks Provided Spark classes, so the local smoke used `sparkAnalytics/Test/runMain`. A hard failure before publish still lacks final persisted integrity/counters, assigned to Job 11 in 6F. No EMR or live cloud check was run.

MANUAL ACTION REQUIRED: User launches the separate independent 6C read-only review, then decides whether to approve and commit 6C. No agent committed or pushed.

BLOCKED-ON OWNER: None for the 6C local gate. Domain F5/R1 hardening, Phase 7 mapping and the 6A packaging guard retain their later owners.

BLOCKED-ON EVIDENCE: None for local jobs 1–2. Job 11 load manifests/content hashes, cloud compatibility and live runtime evidence remain later gates.

NEXT GATE: Independent user-run 6C review. Stop before 6D.

## Subphase 6C — repair round 1 final gate

STATUS: COMPLETE for the requested blocking repairs; external read-only recheck pending.

OWNER: Coordinator `/root` retained the final-tree independent, local smoke and full-gate results. Spark owner `/root/spark_6c_repair_finish` ran the final module suite after its v2 run-ID edit; test owner `/root/test_6c` ran the independent suite after its F1/F2 edits.

WORK ORDER: Verify F1–F5 and recheck blockers R1-1/R1-2 on branch `phase-6`, base/current HEAD `01d204b531d3fc72a5c49f884980a5c7c8926b18`; do not commit or start 6D.

FILES CREATED: `evidence/6c/repair-1/{production-compile,module-targeted,independent-targeted,independent-targeted-final,local-smoke,test-classpath,counter-inspect,counter-inspect-final,final-check}.txt`, `local-run-manifest.json`, `CounterInspect.java` and `inspect_counters.py`. The latter two are bounded local evidence tools. The smoke config `target/phase6-inputs/6c-spark-config-repair-1.json` and output root `target/phase6-runs/6c-repair-1/` are ignored local data.

FILES MODIFIED: This `test-report.md` section and the implementation/report paths itemized in `owner-report.md`.

COMMANDS RUN: From the repository root, every sbt command used JDK 17 `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`, `PATH=$JAVA_HOME/bin:$PATH`, and `SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml`. The coordinator's exact final-tree commands were:

```bash
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch 'independentTests/testOnly *IndependentPhase6CGraphSpec' > docs/agent-runs/phase-06/evidence/6c/repair-1/independent-targeted-final.txt 2>&1
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch 'sparkAnalytics/Test/runMain edu.uic.cs441.scholarchain.spark.Phase6CMain target/phase6-inputs/6c-spark-config-repair-1.json' > docs/agent-runs/phase-06/evidence/6c/repair-1/local-smoke.txt 2>&1
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'export sparkAnalytics/Test/fullClasspath' > docs/agent-runs/phase-06/evidence/6c/repair-1/test-classpath.txt 2>&1
python3 -I docs/agent-runs/phase-06/evidence/6c/repair-1/inspect_counters.py target/phase6-runs/6c-repair-1/run:d56e56d9-de03-4862-bc66-46fd5ad27b75/counters > docs/agent-runs/phase-06/evidence/6c/repair-1/counter-inspect-final.txt 2>&1
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > docs/agent-runs/phase-06/evidence/6c/repair-1/final-check.txt 2>&1
cp target/phase6-runs/6c-repair-1/run:d56e56d9-de03-4862-bc66-46fd5ad27b75/run-manifest.json docs/agent-runs/phase-06/evidence/6c/repair-1/local-run-manifest.json
git diff --check
```

All these final commands exited **0**. Spark owner ran `sbt -batch 'sparkAnalytics/Compile/scalafmt' 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/Compile/scalafmtCheck' 'sparkAnalytics/Test/scalafmtCheck' 'sparkAnalytics/testOnly *Phase6CJobsSpec'` (exit 0, 14/14) and `git diff --check -- modules/spark` (exit 0); its output is retained in `module-targeted.txt`. The test owner ran JDK 17 independent formatting/check (exit 0) and `independentTests/testOnly *IndependentPhase6CGraphSpec` (exit 0, 6/6), retained in `independent-targeted.txt`. The coordinator's early `sparkAnalytics/compile` ran on an intermediate tree and exited 0, retained in `production-compile.txt`; it is not counted as the final-tree gate.

INTERMEDIATE FAILURES: Initial sandboxed sbt attempts could not open `/Users/danny/.sbt/boot/sbt.boot.lock`; approved existing-cache retries passed. The first direct Java counter probe could not bind Spark's local socket inside the sandbox. The approved local retry and the final replayable `inspect_counters.py` command both exited 0. These are environment denials, not passing tests, and the earlier partial outputs are retained in `production-compile.txt` and `counter-inspect.txt` as applicable.

TEST RESULTS: `module-targeted.txt` shows **14/14**, `independent-targeted-final.txt` **6/6**, both zero failures. The full `final-check.txt` shows core **142/142** (lines 163–165), Hadoop **64/64** (905–907), entity resolution **39/39** (955–957), Spark **15/15** (1036–1038), independent **240/240** (2210–2212) and build verification **7/7** (2252–2254): **507 passed, zero failed**. The log begins with sbt 1.10.7 on Homebrew Java 17.0.20.1, records `[success] Total time: 512 s` at line 2257 and `real 513.92` at line 2258. It is **253,775 bytes**, SHA-256 `6c0fdf7494269c2ccb71a8cdbee35cb36b4c574b4d3d34928e2e37352c5a7773`. The build-verification failure trace is an injected expected self-test; the full process exited 0.

VALIDATION RESULTS: `local-smoke.txt` shows completed local jobs 1–2 with `run:d56e56d9-de03-4862-bc66-46fd5ad27b75`, six coauthored edges, six support rows, zero integrity rows, zero rejects and 28 counters; exit 0, real 21.26. The prior retained smoke used `run:50e1fc99-a22c-4993-9525-7772e6af1fac`. `local-run-manifest.json` records `codeVersion=spark-phase6c-jobs1-2-v2`. `counter-inspect-final.txt` reads the **published Parquet** and asserts `erResearcherUnresolved=6`, `erResearcherConflicts=0`, `erWorkUnresolved=0`, `erWorkConflicts=3` and `missingGraphEndpoints=0`; the probe exited 0. This verifies the real ER `load()` wiring as well as the module's schema fixture. The Spark module test also rejects a v1 completed-output manifest. All Spark and independent implementation source files were last edited before the full gate started. `git diff --check` exited 0.

ASSUMPTIONS: The previously approved `ccd26111…` Hadoop run and matching disabled-mode offline ER export remained unchanged for the fresh smoke. The probe reads 28 bounded counter rows and does not alter output. The full log is the final gate for the v2 repair tree.

RISKS: Only blocking findings were requested. R1-3, R1-4 and R1-5 and the original N observations are not claimed closed. A hard invariant that aborts before publication still needs persisted failure evidence in 6F; no AWS or EMR runtime was run.

MANUAL ACTION REQUIRED: User launches a read-only independent recheck, then decides whether to approve/commit this uncommitted 6C tree.

BLOCKED-ON OWNER: None for the requested local blockers.

BLOCKED-ON EVIDENCE: None for F1–F5 or R1-1/R1-2 local gates.

NEXT GATE: Independent 6C repair-round recheck. Stop before 6D.

### External recheck disposition

The user-supplied external reviewer **APPROVED** the 6C repair round and independently checked the retained log timing, byte count and SHA-256, per-module 507/507 counts, smoke run ID, ER counter evidence, published manifest and completion marker. Its report is retained in `review.md`. These checks are reviewer-reported read-only validation, not a new test run by the coordinator. The next gate is the user's commit of the approved 6C tree before 6D Step 0.


## Subphase 6D+6E — final corrected-tree validation

STATUS: COMPLETE for local validation; independent external review is pending.

OWNER: Coordinator `/root` retained the final gate and ran the final independent command; Spark and independent test owners authored their separate suites. Core owner supplied prerequisite F5 feature tests.

WORK ORDER: Validate jobs 3–8 against hand-computed fixtures on `phase-6`, base/unchanged HEAD `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4`, without commit, reviewer launch or later-subphase implementation.

FILES CREATED: `evidence/6de/{preflight,commands}.md`, final and intermediate `.txt` logs, `source-check.txt`, `final-gate-metadata.json`. The implementation/test file list is in the matching owner report.

FILES MODIFIED: This report, coordinator work order/repair/owner reports, and owner-scoped sources/tests/README listed in the owner report.

COMMANDS RUN: From the repository root, the coordinator used:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch 'independentTests/Test/scalafmt' 'independentTests/Test/scalafmtCheck' 'independentTests/testOnly *IndependentPhase6DEGraphSpec' > docs/agent-runs/phase-06/evidence/6de/independent-predecessor-targeted.txt 2>&1
/usr/bin/time -p sbt -batch check > docs/agent-runs/phase-06/evidence/6de/final-check.txt 2>&1
git diff --check
```

Each final sbt process exited **0**; the shell captured `$?`, appended `exit=0` to its log, and exited with that status. The complete command record, including the append/exit lines, is `evidence/6de/commands.md`. The coordinator executed the test owner's requested automatic formatter for the final test addition; the owner authored all test logic. Spark owner ran JDK 17 `sbt -batch 'sparkAnalytics/scalafmt' 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/testOnly *Phase6DEJobsSpec'`, exit 0; its retained log header verifies Java/sbt versions, while its exported environment was not separately captured. The final full gate checks all formatting again. Core owner's 14/14 targeted result and core formatting checks were observed but not retained separately; the full gate retains the final core result.

TEST RESULTS:

| Gate | Passed / failed | Evidence |
| --- | --- | --- |
| Final Spark module targeted | 9 / 0 | `module-predecessor-targeted.txt` (12:06:07) |
| Final independent targeted | 10 / 0 | `independent-predecessor-targeted.txt` (12:07:21), exit 0, sbt 39 s |
| Core in full check | 143 / 0 | `final-check.txt:164` / `:166` |
| Hadoop in full check | 64 / 0 | `final-check.txt:906` / `:908` |
| Entity resolution in full check | 39 / 0 | `final-check.txt:956` / `:958` |
| Spark in full check | 24 / 0 | `final-check.txt:1540` / `:1542` |
| Independent in full check | 250 / 0 | `final-check.txt:2741` / `:2743` |
| Build verification in full check | 7 / 0 | `final-check.txt:2783` / `:2785` |
| **Full check total** | **527 / 0** | success at `:2788`, exit 0 at `:2793` |

The full gate completed 2026-10-22 12:17:08 CDT, sbt **565 s**, `/usr/bin/time` real **567.12 s**. Header: **sbt 1.10.7, Homebrew Java 17.0.20.1**. File size **285,463 bytes**; SHA-256 **`bd8b9a28348839769b5410364c3f7893fe37bb1c871eac27d7595fba75dbca34`**. `final-gate-metadata.json` contains machine-readable counts/hash. Targeted counts are included in the full-suite counts and are not added again.

VALIDATION RESULTS: The independent suite exercises G1–G4 expected values, injected G1/G2 bridge partitions, hand-traced two-clique LPA, empty/single/yearless cases, and replay of metric/core/component rows. The module suite uses A–E, triangle and route-tie fixtures for metrics/components/coreness, paths, ties/caps/solo behavior, iteration guards, convergent LPA and seeded pair selection. This coverage wording was corrected in repair round 1 (F3); it does not claim module G1–G4 coverage. Both final targeted suites include an equal-length route fixture where smallest immediate predecessor differs from whole-route lexicographic order. Core feature checks preserve wire/ID compatibility while enforcing the prior F5 consistency rules. The source scan in `source-check.txt` matches only `BoundedActions.scala:14` and `:21`; no forbidden production graph APIs were found by that scan. Source/test/README mtimes precede this full gate. `git diff --check` exited 0. Build-verification `[error]` output is the expected injected check-probe self-test; all seven build tests passed. Hadoop/Spark fixture warnings remain in the full log.

INTERMEDIATE RESULTS AND FAILURES: `independent-compile-failure.txt` retains a test typo (`"A" to "G"`), corrected to a Char range. `independent-interrupted.txt` records the initial slow G1 run using 50 LPA iterations; the owner interrupted it and reduced the fixture's iteration limit to 4, since G1 does not prescribe LPA convergence and the convergent two-clique fixture settles by iteration 3. `independent-runtime-fixture-failure.txt` retains a 6/8 result caused by two test casts from Spark mutable ArraySeq to immutable Seq; the test owner corrected those casts. Earlier passing 8/8 module and 9/9 independent logs remain as provenance and are superseded by the final 9/9 and 10/10 logs. The coordinator stopped an earlier full check after finding the predecessor-rule mismatch; SIGINT did not stop sbt, so the exact running sbt process received SIGTERM, yielding exit **143**, real 180.61 s (`superseded-check.txt`). That stopped run is not a passing gate. Spark source/test owners fixed the rule and added distinguishing fixtures before the final targeted/full gates. Owners also reported initial sandbox lock permission denials; those are environment failures, not passing tests. Model-capacity interruptions delayed turns without changing test outcomes.

ASSUMPTIONS: Synthetic fixture tables are deliberately bounded. The final builder source was stable before targeted validation; the final full gate also postdates the last source, test and README change. The independent owner supplied the final fixture; coordinator formatting execution is disclosed above.

RISKS: No jobs 3–8 real-data export or cloud run is claimed. The S-source distance estimate is deferred by user choice, optional betweenness omitted, and final publishing/event-log/failure-persistence work belongs to 6F+6G. Existing later gates are retained in `repairs.md`.

MANUAL ACTION REQUIRED: User runs the separate read-only 6D+6E review, then decides on a commit after approval. No reviewer or commit was triggered by these tests.

BLOCKED-ON OWNER: None for the requested local gate.

BLOCKED-ON EVIDENCE: None for the targeted/full-check results above.

NEXT GATE: User-run read-only 6D+6E review. Stop before 6F+6G.


## Subphase 6D+6E — repair round 1 validation (F1–F3)

STATUS: COMPLETE for blocking repair validation; external recheck pending.

OWNER: Domain/Spark owners authored their changes and core/Spark fixtures. Coordinator retained logs, executed the Spark owner's supplied formatter/test command and the final full check, and corrected the F3 report attribution.

WORK ORDER: Validate F1 shipped defaults, F2 LPA non-convergence and F3 report accuracy on branch `phase-6`, base/unchanged HEAD `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4`. Preserve prior implementation/evidence; no commit, reviewer launch or 6F+6G work.

FILES CREATED: `evidence/6de/repair-1/{core-format,core-targeted,module-sandbox-denial,module-targeted,final-check,java-version,source-check}.txt`, `commands.md`, `final-gate-metadata.json` and handoff evidence.

FILES MODIFIED: Owner-authored config resource, core contract test, Spark module test and README; coordinator review/prompt/repair/owner/test reports. No independent-test source or production algorithm changed this round.

COMMANDS RUN: All successful sbt commands used:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Core owner commands (all exit 0, retained in `core-format.txt` and `core-targeted.txt`):

```bash
sbt -batch 'core/scalafmtAll' 'core/Compile/scalafmtCheck' 'core/Test/scalafmtCheck'
sbt -batch 'core/testOnly *SparkAnalyticsContractSpec'
```

Coordinator commands (all exit 0):

```bash
sbt -batch 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/Test/scalafmtCheck' 'sparkAnalytics/testOnly *Phase6DEJobsSpec' > docs/agent-runs/phase-06/evidence/6de/repair-1/module-targeted.txt 2>&1
/usr/bin/time -p sbt -batch check > docs/agent-runs/phase-06/evidence/6de/repair-1/final-check.txt 2>&1
git diff --check
```

The shell captured `$?`, appended the actual exit code to each coordinator sbt log, and returned that status; `commands.md` retains those exact lines. The Spark owner reported a sandbox lock-file denial before compilation (exit 1, `module-sandbox-denial.txt`). The coordinator then executed the owner's requested automatic formatter/check/test command on owner-authored test code. This environment failure is not a test failure or pass. The independent source was unchanged; the full check exercised all 250 independent tests, so no separate independent targeted rerun was needed this round.

TEST RESULTS:

| Gate | Passed / failed | Evidence |
| --- | --- | --- |
| Core targeted contract suite | 14 / 0 | `repair-1/core-targeted.txt`, 12:35:26 |
| Spark targeted module suite | 10 / 0 | `repair-1/module-targeted.txt`, 12:37:15, exit 0 |
| Core full suite | 143 / 0 | `repair-1/final-check.txt:166` / `:168` |
| Hadoop full suite | 64 / 0 | `repair-1/final-check.txt:908` / `:910` |
| ER full suite | 39 / 0 | `repair-1/final-check.txt:958` / `:960` |
| Spark full suite | 25 / 0 | `repair-1/final-check.txt:1544` / `:1546` |
| Independent full suite | 250 / 0 | `repair-1/final-check.txt:2746` / `:2748` |
| Build verification | 7 / 0 | `repair-1/final-check.txt:2788` / `:2790` |
| **Full gate total** | **528 / 0** | success `:2793`; real `:2794`; exit 0 `:2798` |

Full gate: sbt **561 s**, real **563.44 s**, completion **2026-10-22 12:47:16 CDT**. Header verifies **Homebrew Java 17.0.20.1** and **sbt 1.10.7**; direct `java -version` is retained. Size **286,117 bytes**; SHA-256 **`18d9858bc70337879054a388868dede84e19b2f568f12b2e5e50d2d1c833112f`**. The original 527-test log remains historical evidence at `evidence/6de/final-check.txt`; this repair's log is in `repair-1/`.

VALIDATION RESULTS: F1 asserts CC50, k-core50, checkpoint5, community20, maxHops6, K20, S32, seed441, plus the existing representative/shuffle settings. The test confirms both full and logical fingerprints differ from reconstructed prior 100/100/K32 settings. Exact hashes are retained in core output and metadata; no historical 6C output or run identity is rewritten. F2's two-person fixture asserts all memberships and summaries are non-converged after three iterations, both summaries have finalChangedCount=2, and the counters are 0/2. Actual DataFrame membership/summary JSON is parsed to the corresponding core records and every record passes `SparkAnalyticsValidation.check`. The module suite now has 10 tests; the new case also passes inside the 25-test full Spark suite. F3 is an editorial correction: only the independent suite claims G1–G4, while the module suite uses its separate A–E, triangle, ties/sampling and oscillating-pair fixtures. No fresh module G1–G4 result is claimed. Source/resource/test/README mtimes precede the final gate; API scans only match the bounded helper sites; `git diff --check` exits 0. The injected build-probe `[error]` trace is expected and all seven build-verification tests pass.

ASSUMPTIONS: Step 0 decisions are unchanged; old/new fingerprints printed here belong to the canonical config example, not to old smoke configs with different physical roots. Targeted counts are included in full totals and not added twice.

RISKS: Nonblocking and future findings are tracked in `repairs.md`, including complete replay/export/core parsing, performance and real-data limitations. This repair adds core parsing only for community membership/summary records. No cloud or real-data pipeline result is claimed.

MANUAL ACTION REQUIRED: User launches the separate read-only recheck; user decides on a commit after approval.

BLOCKED-ON OWNER: None for the requested blockers.

BLOCKED-ON EVIDENCE: None for the local repair gates.

NEXT GATE: External read-only 6D+6E repair-round-1 recheck. Stop before 6F+6G.


### External 6D+6E repair-round-1 approval

The user-supplied independent reviewer returned **APPROVE**, closing F1–F3 and verifying the retained 528/0 full-gate evidence, core 14/14 and Spark 10/10 targeted results. Its complete text is retained in `review.md`; R1-O1 is assigned in `repairs.md`. These are reviewer-reported checks, not a new test execution. The approved tree is still uncommitted at HEAD `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4`. The next gate is the user's commit, followed by 6F+6G Step 0. No next-subphase work, commit or push was performed by the coordinator.


## Subphase 6F+6G — final stable-tree test report

STATUS: COMPLETE for local deterministic gates; external review pending.

OWNER: Module owners authored module tests; independent test-engineer authored `tests/**`; dataset owner authored its Python tests. Coordinator retained evidence and ran the final gate. Coordinator executed requested formatters on owner-authored files; no ownership transfer or reviewer approval is claimed.

WORK ORDER: Merged 6F+6G, base/HEAD `6ae7378cbef90a176fd1faecae0dee0615eba9e3`, branch `phase-6`; exact plan hash and six user approvals are in `prompt.md` / `evidence/6fg/preflight.md`.

FILES CREATED/MODIFIED: C/DE/FG module feature coverage; four independent Scala files plus committed tiny XML/empty JSONL fixtures; core summary entity-kind cases; dataset acquisition/replay tests; retained logs, metadata and reports. Exact inventories are in `evidence/6fg/changed-files.txt`.

COMMANDS RUN: `evidence/6fg/commands.md` gives the exact Java17 environment and every compile/targeted/upstream/CLI/gate invocation. Final full command: `/usr/bin/time -p sbt -batch check`; exit **0**. Latest `git diff --check`: exit **0**. No production test source changed during the gate. See `stable-source-before-check.json` and `final-gate-metadata.json`.

### Observed full-gate results

| Suite | Passed / failed | Full log lines |
| --- | --- | --- |
| Core | 144 / 0 | 172 / 174 |
| Hadoop | 64 / 0 | 914 / 916 |
| ER | 39 / 0 | 964 / 966 |
| Spark | 34 / 0 | 2079 / 2081 |
| Independent | 263 / 0 | 6236 / 6238 |
| Build verification | 7 / 0 | 6278 / 6280 |
| **Total** | **551 / 0** | success 6283; real 6284; exit 0 at 6287 |

`evidence/6fg/final-check.txt`: **1,358,948 bytes**, SHA-256 **`6f48042efe332864661f5d8a73dfa8565fd257db53ff3bcc97371b724919844c`**. sbt **691 s**, real **692.82 s**, completion **2026-10-22 13:51:06 CDT**. Header records **Java 17.0.20.1**, **sbt 1.10.7**. The existing build marker updated only after passing all gates. Hadoop injected-failure cases and the expected build check-probe trace (6248–6266) test failure handling; they are not failed tests.

### Targeted and runtime sequence, including failures

1. Core target **15/15**, exit 0. Dataset Python tests **12/12**, separate from sbt totals; actual extraction/replay XML bytes match.
2. Initial Spark compile failed a missing constructor argument; corrected compile passed. Initial independent target **10/13** failed JSON-null/temp-symlink setup. Corrected second target passed 11 tests, failed 1 and aborted 1 suite after 2 GiB heap exhaustion in deep plan rendering; Hadoop's failure was secondary. Retention/plan caps and bounded found-path lineage fixed this without raising test heap. Next independent target **13/13**, exit 0, predates the final added assertions.
3. Initial module target **29/32**, exit 1: JSON optional-field serialization, changed counter semantics and a mutable collection cast. Corrected module **32/32**, exit 0.
4. Hadoop real prep passed, ER first output-bound failure exited 2; bound-only retry passed with fake/live calls 0/0. First full Spark attempt failed a Spark Union/checkpoint constraint rewrite, exit 1, with no completion marker. Its SQL stack and typed failure evidence are retained. Optimizer-only compatibility setting plus a multiwindow regression repaired it.
5. Latest combined target: module **33/33**, independent **12/13**, combined exit 1. A newly added assertion expected numeric sidecar rowCount, whose exact Long representation is a string. Owner changed only its decoder; tiny end-to-end target **1/1**, exit 0, real **52.35 s**. Final **263/263** independent suite above covers this latest assertion and all other final assertions together.
6. Fresh repaired real Spark run **180.45 s**, replay **158.07 s**, both exit 0; run ID `run:f02acf56-4bea-4009-adaf-b11d5afceb49`. Output/checkpoint roots differ; shuffle partitions 4→2. All 28 counts/hashes and counters match, markers verify, and four load manifests are byte-identical. `replay-comparison.json` / `manifest-file-audit.json` retain exact checks. The real hashes are computed by each fresh pipeline; full physical Parquet reread/hash equivalence is separately covered in module and independent tests.

Intermediate test logs are labeled excerpts with repeated timestamped WARN lines removed; original sizes/hashes and ignored full-copy paths are in `intermediate-log-retention.json`. The final full-gate and real-data CLI logs remain complete. No excerpt is described as a full export or full gate.

VALIDATION RESULTS: Exact G1 bounded-window D deltas and entry/exit flags; community Jaccard overlap; exact three-source chain mean 4/3/P90 2; empty window; 15-author/105-edge near-limit team; ORCID conflicts without splitting; four summary types with actual numeric/field references; applicable core parsing for all 28 exported tables and every counter row; four manifest arrays, path/count/hash consistency, actual two-export Parquet replay at 4→2 partitions; partial/different/tampered-marker refusal and reuse; forbidden API/driver-action scan; exact event aggregates; committed tiny Hadoop→disabled-ER→all-Spark pipeline with literal counts, reuse, unsupported schema and missing marker refusal. Module-specific tests pin ID authority with absent DOI, normalized ORCIDs/properties, yearless solo counting, per-window LPA iteration/context schema and multiwindow six-hop behavior across checkpoint interval 5. All these latest assertions pass inside the full gate.

ASSUMPTIONS: Expected values are literal fixture calculations, not implementation-derived comparison values. Counts of targeted suites are included in full totals and are not added again. Equal-Jaccard winning candidate IDs are not separately represented by the current TemporalChange wire record.

RISKS: The bounded run is a biased convenience slice; no identity accuracy, live-model quality, cloud runtime or store-loading result is claimed. Reuse is a metadata/identity gate rather than a deep audit of already completed Parquet. Stage durations mean summed task times; operational timing is excluded from deterministic hashes. Other limitations and future owners/gates are in `repairs.md` and `real-data-report.md`.

MANUAL ACTION REQUIRED: User launches the independent read-only review; no automatic reviewer, commit, push or 6I start.

BLOCKED-ON OWNER: None.

BLOCKED-ON EVIDENCE: None for 6F+6G local validation.

NEXT GATE: User-run 6F+6G review.


## Subphase 6F+6G repair round 1 — test/evidence report

STATUS: COMPLETE for F1–F3 local validation; external recheck pending.
OWNER: Independent test-engineer authored SafetySpec; coordinator executed requested formatter/target and final gate, derived F1/F2 evidence, and retained results.
WORK ORDER: User blocking-only scope; unchanged base/HEAD `6ae7378cbef90a176fd1faecae0dee0615eba9e3`. No production change or real-data rerun.
FILES MODIFIED: Only SafetySpec in implementation paths; coordinator report/evidence changes listed in `repair-1/changed-files.txt`.
COMMANDS RUN: Exact JDK17 environment and commands in `repair-1/commands.md`; safety target7/7 exit0 real5.79s; full check exit0; diff check exit0.

| Full suite | Passed / failed | Log total / result lines |
| --- | --- | --- |
| Core | 144 / 0 | 172 / 174 |
| Hadoop | 64 / 0 | 914 / 916 |
| ER | 39 / 0 | 964 / 966 |
| Spark | 34 / 0 | 2080 / 2082 |
| Independent | 266 / 0 | 6237 / 6239 |
| Build verification | 7 / 0 | 6279 / 6281 |
| **Total** | **554 / 0** | success6284 / real6285 / exit0:6288 |

TEST RESULTS: Full gate sbt674s, real676.42s, finished2026-10-22 14:29:32 CDT, Java17.0.20.1/sbt1.10.7. Full unfiltered log **1,358,928 bytes**, SHA-256 **`3e6654835296bab3be44efbdf0cd31c205dd4b34ff87b98848a4ba16623c5236`**. Expected injected Hadoop/build-probe failure traces are failure-handling tests, not gate failures. Three new scanner tests increase independent263→266 and total551→554. Python12/12 is unchanged prior evidence, not rerun or added to these totals.

VALIDATION RESULTS: Reusable scanner catches collect/collectAsList/toLocalIterator/take/takeAsList/head/first/count/isEmpty/reduce/show regardless of parentheses. Self-tests include five forbidden spellings per method, prefix negatives, nested/line comments, escaped/triple-quoted literals, adjacent executable calls and exact audited config/Option/Column-metadata/helper exceptions. Source scan passes against all production Spark files. It remains explicitly heuristic. All 27 repair snapshot contents/mtimes are unchanged during the gate; only SafetySpec's content differs from the original reviewed implementation snapshot. All production class bytes still fingerprint to the retained real runs.

F1 evidence validation independently resolves all parent IDs, checks acyclicity and metadata presence, and matches every executed stage's task/partition/shuffle totals to the original summary. F2 recursively compares retained reports and records12 exact numeric differences; all28 table hashes remain equal, while all-compared-artifact equality is false. See `repair-1/evidence-validation.json`, `stage-dag.json` and `analytics-report-comparison.json`. No retained report/output payload is rewritten; only disclosure/comparison evidence changes.

ASSUMPTIONS: Existing local real-data execution remains valid because no production source/class change occurred. P90 equality in this replay does not establish general partition invariance.
RISKS: F4–F12 deferred by the user; approximation and scanner limits remain disclosed.
MANUAL ACTION REQUIRED: User-run independent read-only recheck.
BLOCKED-ON OWNER: none. BLOCKED-ON EVIDENCE: none for F1–F3 local gates.
NEXT GATE: Repair-round recheck; no commit/push/reviewer/6I.

## Subphase 6I — fresh final JDK 17 gate

STATUS: COMPLETE for observed local validation; final independent review and
human acceptance pending.
OWNER: Coordinator execution/evidence; existing module and independent test
owners retain ownership. No source/test edits or new reviewers.
WORK ORDER: Evidence-only 6I, base/HEAD `d1afc7f6698965ddbe010621b277b10e655d25ff`, branch `phase-6`;
full Phase 6 reviewer scope starts at `03493882399e9020e6892c9f97e0ec8919365215`.
FILES CREATED: `evidence/6i/` gate, metadata, scoped snapshot and audits.
FILES MODIFIED: Coordinator reports only; exact inventory in `changed-files.txt`.
COMMANDS RUN: JDK 17 environment and Phase 4 logging from `commands.md`;
`java -version`; `/usr/bin/time -p sbt -batch check` exit 0; metadata/SHA audits;
`git diff --check` exit 0; cumulative non-evidence check exit 0. Full cumulative
check exit 2 solely for historical raw-log whitespace (`diff-check.txt`), left
unchanged. Metadata-assembly assertion initially rejected that historical result;
corrected audit records it, with no source/log edit or gate rerun.
TEST RESULTS: **554 passed / 0 failed**: core 144/Hadoop 64/ER 39/Spark 34/
independent 266/build 7. Java 17.0.20.1, sbt 1.10.7. Sbt 673s,
real **675.13s**, exit 0. Completed `2026-10-22T20:04:05.397751+00:00`.
Full log `evidence/6i/final-check.txt`, **1,359,860 bytes**, SHA-256
`e2bf289d11f6f2e4ff8e714d3fc4b9b56b16ea7ed59007abd00d5fe73d9d7367`. Exact count/success/exit lines and marker mtime:
`final-gate-metadata.json`. The build self-test intentionally logs an injected
error; final six module results and process exit are successful. No standalone
Python dataset test, real-data CLI or packaging run in 6I.
VALIDATION RESULTS: 68 scoped source/build/config/dataset hashes+mtimes and all 27
approved snapshot hashes unchanged, as are HEAD/plan. Human-owned records remain
absent. Metadata-only retained audit validates both markers, 28 table hash pairs,
identical counters and 12 operational-report differences. Current Scala export
and tiny Hadoop→offlineER→Spark integration cases ran in the full suite. Historical
real Parquet content was not independently reread by the 6I sidecar audit.
ASSUMPTIONS: Existing 554-test tree is unchanged. Dataset Python 12/12 and prior
real runtime/stage measurements remain historical, separate from these totals.
RISKS: F4–F12, scanner gaps, approximation/reuse/hash scale limits, yearless store
mapping and release/EMR gates remain disclosed; no cloud compatibility inferred.
MANUAL ACTION REQUIRED: User-run comprehensive review; then human acceptance
and commit records. Do not treat this test report as approval.
BLOCKED-ON OWNER: None for local tests. Reviewer/human own remaining close-out.
BLOCKED-ON EVIDENCE: Whole-phase APPROVE and human gate; EMR open until Phase 15.
NEXT GATE: Comprehensive Phase 6 review; stop after 6I.

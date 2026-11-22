<!-- Course-named copy of owner-report.md in this folder, added in Phase 17 (package 17D, docs/agent-runs/phase-17/prompt.md). The text below this note is identical to owner-report.md, which is unchanged. -->

# Phase 6 owner report

## Subphase 6A — toolchain, Spark harness and EMR feasibility

STATUS: COMPLETE for 6A implementation; independent review and human acceptance remain pending.

OWNER: Coordinator `/root` assembled this report. Delegated native tasks: `build-engineer` `/root/build_6a`, `spark-engineer` `/root/spark_6a`, `infra-engineer` `/root/infra_6a`. The user chose the current inherited model for each role; exact model IDs were not exposed to these agents. No reviewer was launched.

WORK ORDER: User request and three answers are recorded verbatim in `prompt.md`. Implement only Subphase 6A of `/Users/danny/Documents/plan/phase6.md` from base `03493882399e9020e6892c9f97e0ec8919365215`, on the user-authorized `phase-6` branch. Starting tracked/untracked diff was empty. Build and Spark work was sequential at the wiring boundary; EMR research was read-only in parallel.

FILES CREATED: `project/Java17Guard.scala`; `project/SparkJobJar.scala`; `project/verification/src/test/scala/scholarchain/build/Java17GuardSpec.scala`; `project/verification/src/test/scala/scholarchain/build/SparkJobJarSpec.scala` (build owner); `modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/SparkSmokeSpec.scala` (Spark owner); `docs/agent-runs/phase-06/prompt.md`, this report, `test-report.md`, and `evidence/6a/**` (coordinator).

FILES MODIFIED: `build.sbt`, `project/Dependencies.scala`, `project/ScholarChainBuild.scala`, `project/Versions.scala` (build owner). No Phase 5 files, human decisions, core contract, Hadoop implementation, entity-resolution policy, Terraform, or AWS resource was changed.

COMMANDS RUN: Coordinator: `git status --short --branch`, `git rev-parse HEAD`, `git switch -c phase-6` (approved retry exit 0), JDK 17 `java -version` (exit 0), baseline and final `sbt -batch check` with `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home` and `SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml` (both exit 0), final `sbt -batch 'sparkAnalytics/sparkJobJar'` (exit 0), JDK 17 `jar tf` (exit 0), `shasum -a 256` (exit 0), and `git diff --check` (exit 0). Exact captured commands, retry failures, and outputs are in `evidence/6a/preflight.md`, `baseline-check.txt`, `final-check.txt`, and `final-package.txt`. Build owner: JDK 17 `sbt -batch 'buildVerification/test' 'sparkAnalytics/sparkJobJar'` (exit 0 after one repaired package failure); JDK 27 `sbt -batch check` (exit 1 at `checkJava17` as intended); JDK 17 `sbt -batch 'buildVerification / Compile / scalafmt' 'buildVerification / Test / scalafmt' scalafmtSbt` (exit 0); and JDK 17 `sbt -batch 'sparkAnalytics / Test / compile' 'sparkAnalytics / Test / test' 'buildVerification / Test / test'` (exit 0). The build owner's first successful targeted run accidentally named a nonexistent logback configuration in `SBT_OPTS`; its subsequent targeted Spark test, the coordinator's full gate, and final packaging used the required existing configuration. Spark owner: JDK 17 `sbt -batch 'sparkAnalytics / Test / scalafmt'` (exit 0). Infra owner made read-only source and official-document reads; no AWS account call. The first sandboxed sbt attempts could not open `~/.sbt/boot/sbt.boot.lock`; approved retries succeeded.

TEST RESULTS: Baseline: 469 passed, zero failed, 413.74 seconds real time. Final: 473 passed, zero failed, 424.08 seconds real time, including Spark smoke 1/1 and build verification 7/7. The wrong-JDK probe failed promptly with `ScholarChain check requires Java 17; found Java 27`. Two format failures and a missing `scala-reflect` compile dependency were repaired by their respective owners before the final pass. The initial package attempt rejected a duplicate manifest and was repaired by the build owner. See `test-report.md` and retained logs; no unrun gate is reported as passed.

VALIDATION RESULTS: The smoke test asserts five exact rows through join, groupBy, window, Parquet write/read and checkpoint using a local SparkSession, and stops it. `independentTests` now depends on `sparkAnalytics`; the build owner observed Spark classes and `spark-sql_2.13:3.5.4` on its test classpath. The final 11 MB Spark job JAR at `modules/spark/target/spark-job_3-0.1.0-SNAPSHOT.jar` has SHA-256 `10d4649b107a7b81f5c8309a98798e1b864fc27dba2df926cec4557ccbc2a73a`, 5,467 entries, 608 under the core namespace, 57 under `scala/reflect/`, and zero under `org/apache/spark/` or `org/apache/hadoop/`. No Spark production classes exist in 6A. AWS documentation shows EMR 7.x Spark 3.5 uses Scala 2.12 while this repository compiles against `spark-sql_2.13`; the comparison and citations are in `evidence/6a/emr-compatibility.md`.

ASSUMPTIONS: `scala-reflect` 2.13.14 matches the Scala 2.13 library version used by this Scala 3.3.4 build and is needed at compile time for SparkSession signatures. Spark and Hadoop remain Provided. The published EMR version matrix describes available runtimes, not a tested deployment. A later runtime must prove linkage before any EMR compatibility claim.

RISKS: Stock EMR 7.x is not demonstrated binary-compatible with the current Scala 3 / Spark Scala-2.13 job. EMR Serverless/EKS custom images and an EMR EC2 custom Spark distribution have research and operational costs and remain unselected. The JAR has no Spark production entry point yet; that is later-subphase work. No live EMR run occurred and no deployment permission was inferred.

MANUAL ACTION REQUIRED: The user launches a separate read-only reviewer for 6A, decides on any findings, and commits an approved subphase before sending the next prompt. A future human budget/deployment gate is required for any live EMR run.

BLOCKED-ON OWNER: None for 6A. Runtime EMR compatibility and live execution remain later gates, not claimed successes.

BLOCKED-ON EVIDENCE: No current 6A blocker. The EMR mismatch and unverified cloud runtime are detailed in `evidence/6a/emr-compatibility.md`.

NEXT GATE: Independent user-run 6A read-only review using the copyable prompt in the coordinator's handoff. Stop before 6B.

## Subphase 6A — repair round 1 (user-requested F1, F2, F3)

STATUS: COMPLETE for the requested repairs; external recheck remains pending.

OWNER: Coordinator `/root` assembled evidence. Native delegated tasks: `build-engineer` `/root/build_6a_r1` (F1/F2), `test-engineer` `/root/test_6a_r1` (user-approved F1 probe), `infra-engineer` `/root/infra_6a_r1` (read-only F3 research). Each inherited the current model; exact child model IDs were not exposed. No reviewer was launched by the coordinator.

WORK ORDER: The user-supplied external review in `review.md` returned `REQUEST-CHANGES`, then the user instructed exactly: "Fix F1, F2, F3 please". In Step 0 the user approved a single independent SparkSession startup probe under `tests/**`. Repair F1–F3 only on branch `phase-6`, base and current HEAD `03493882399e9020e6892c9f97e0ec8919365215`; the earlier 6A tree remains uncommitted. F4–F9 dispositions are recorded in `repairs.md`.

FILES CREATED: `project/spark-test-resources/log4j2-test.properties` (build owner); `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentSparkSessionSpec.scala` (test owner); `docs/agent-runs/phase-06/review.md`, `repairs.md`, and `evidence/6a/repair-1/**` (coordinator).

FILES MODIFIED: `build.sbt`, `project/ScholarChainBuild.scala`, `project/SparkJobJar.scala`, `project/verification/src/test/scala/scholarchain/build/SparkJobJarSpec.scala` (build owner); `docs/agent-runs/phase-06/prompt.md`, `owner-report.md`, `test-report.md`, and `evidence/6a/emr-compatibility.md` (coordinator). No Phase 5 or human-owned file was edited.

COMMANDS RUN: Build owner with the plan's JDK 17 `JAVA_HOME`, `PATH` and `SBT_OPTS`: `sbt -batch scalafmtSbt 'buildVerification / Test / scalafmt'` (exit 0); `sbt -batch 'buildVerification / Test / testOnly scholarchain.build.SparkJobJarSpec' 'independentTests / Test / testOnly *IndependentSparkSessionSpec'` (exit 0); `sbt -batch 'independentTests / Test / test'` (exit 0); then `sbt -batch scalafmtSbt 'buildVerification / Test / scalafmt' 'show independentTests / Test / fork' 'show independentTests / Test / javaOptions' 'export independentTests / Test / fullClasspath' 'independentTests / Test / testOnly *IndependentSparkSessionSpec' 'sparkAnalytics / Test / testOnly *SparkSmokeSpec' 'sparkAnalytics / sparkJobJar'` (exit 0). The coordinator then ran `/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java -version` (exit 0), the full JDK 17 `sbt -batch check` (exit 0), `sbt -batch 'sparkAnalytics/sparkJobJar'` (exit 0), JDK 17 `jar tf` (exit 0), `shasum -a 256` (exit 0), archive/log forbidden-entry searches (no matches), and `git diff --check` (exit 0). Exact coordinator shell commands and retained output are in `test-report.md` and `evidence/6a/repair-1/`. Infra owner used read-only official sources and `unzip -p ... library.properties`; no AWS call.

TEST RESULTS: Targeted package tests 2/2, independent Spark probe 1/1, Spark smoke 1/1. The independent suite passed 234/234 (233 existing plus the new probe) before the final shared WARN-level test logging resource, then the full stable-tree gate passed **474/474**, zero failures, including 234 independent tests, after that resource was added. Full check wall time was 418.33 seconds. The prior 6A full gate had 473/473. No later-subphase tests were run.

VALIDATION RESULTS: `independentTests / Test / fork` is `true`, and its Java options include `-Xmx2g` and all 15 Spark JDK 17 module opens. The build source sets `independentTests / Test / baseDirectory` to the repository root; the 233 existing independent tests passed with that setting. The retained filtered classpath excerpt includes Spark project classes, `spark-sql_2.13-3.5.4.jar`, `scala-reflect-2.13.14.jar`, and a `log4j-slf4j2-impl` provider. The independent SparkSession probe started local Spark, checked a tiny DataFrame count, and stopped it. The final check log has no `SLF4J(W)` duplicate-provider warning or `DEBUG` line and is 244,600 bytes, versus 1,195,077 bytes before F2. The final 10,203,322-byte JAR has SHA-256 `a30b9f1c373febf3b245911ae533d582d15fadf52074dda287b40d75b504d7e0` and 4,798 entries; the listing has no `org/apache/spark/`, `org/apache/hadoop/`, `ch/qos/logback/`, or `META-INF/services/org.slf4j.spi.SLF4JServiceProvider` paths. The F3 memo records upstream Scala 2.13.8 versus local packaged 2.13.14 and the required 6H inventory/alignment/runtime proof.

ASSUMPTIONS: The shared log4j2 resource under `project/**` applies only to the two Spark test projects. The Scala 2.13 patch difference is a validation risk, not a demonstrated linkage failure under the cited Scala compatibility policy. The selected 6H runtime and its actual class origins are unknown.

RISKS: F4–F6 and F8–F9 remain unaddressed by the user's F1–F3 scope; F7 belongs to 6C. The prior wrong-JDK log is still from the earlier tree; packaging remains outside the Java 17 guard. No EMR/custom runtime or live cloud run was performed. The final package still has no Spark production job class, as planned for 6A.

MANUAL ACTION REQUIRED: The user runs an independent read-only recheck of 6A repair round 1. Do not commit or advance to 6B until the reviewer and user gates are met.

BLOCKED-ON OWNER: None for F1–F3 local repairs. External reviewer decision pending; 6H runtime compatibility remains an open future gate.

BLOCKED-ON EVIDENCE: No current F1–F3 blocker. Future cloud/runtime limits are in `evidence/6a/emr-compatibility.md`.

NEXT GATE: User-run read-only 6A repair-round recheck, with F1–F9 dispositions and retained evidence. Stop before 6B.

## Subphase 6B — contracts, IDs and configuration

STATUS: COMPLETE for 6B implementation and local gates; independent external review pending.

OWNER: Coordinator `/root` assembled evidence. Native `domain-engineer` `/root/domain_6b` owned `modules/core/**`; native `spark-engineer` `/root/spark_design_6b` owned only `modules/spark/README.md`. Both inherited the current model; exact child model IDs were unavailable. Both sessions briefly stopped on a tool usage limit, then resumed through follow-up tasks and completed their assigned files. No reviewer was launched.

WORK ORDER: Implement only plan Subphase 6B on `phase-6`, base/HEAD `bc1e4a17fc879b7aac254b28d83e78dbdd34e367`, from a clean tree. The user answered **"yes to all"** four Step 0 defaults, recorded in `prompt.md`. Domain work is additive core contracts, IDs, config/loader, validation and wire examples. Spark work is design documentation, no production Spark job. Preserve existing wire fields and ID formulas, run JDK 17 `sbt check`, then stop for user-run review.

FILES CREATED: Domain owner: `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsConfig.scala`, `SparkAnalyticsConfigLoader.scala`, `SparkAnalyticsContracts.scala`, `SparkAnalyticsValidation.scala`; `modules/core/src/main/resources/scholarchain.spark-analytics-config.v1.json`; `modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsContractSpec.scala`; 16 `modules/core/src/test/resources/wire/spark-*.json` examples. Spark owner: `modules/spark/README.md`. Coordinator: `evidence/6b/preflight.md`, `evidence/6b/pre-hardening-check-excerpt.txt`, `evidence/6b/final-check.txt`, and the 6B sections of this report and `test-report.md`.

FILES MODIFIED: Domain owner: `modules/core/README.md`, `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/SchemaVersions.scala` and `StableIds.scala`, and `modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/Phase4ContractSpec.scala` (manifest config-version assertion updated additively). Coordinator: `docs/agent-runs/phase-06/prompt.md`, `owner-report.md`, and `test-report.md`. No Phase 5, build, Hadoop, entity-resolution, Terraform or human-owned file changed.

COMMANDS RUN: Domain owner reported JDK 17 `sbt -batch 'core/Test/runMain edu.uic.cs441.scholarchain.core.WriteSparkAnalyticsExamples' 'core/scalafmt' 'core/Test/scalafmt' 'core/testOnly *SparkAnalyticsContractSpec'` (exit 0, targeted 5/5); then `sbt -batch 'core/Test/scalafmt' 'core/scalafmtCheck' 'core/Test/scalafmtCheck' 'core/test'` (exit 0, core 134/134). Its first `core/test` attempt was 133/134 because an older manifest-version assertion listed only two versions; the owner updated that assertion and reran successfully. After the coordinator found an LF-delimiter collision in the new ID helper, the domain owner ran JDK 17 `sbt -batch 'core/scalafmt' 'core/Test/scalafmt' 'core/scalafmtCheck' 'core/Test/scalafmtCheck' 'core/testOnly *SparkAnalyticsContractSpec'` (exit 0, targeted 6/6) and `git diff --check -- modules/core` (exit 0). Spark owner inspected the plan, published core source/examples and README, counted 11 job headings, checked referenced files, checked trailing whitespace (no matches), and ran `git diff --check` (exit 0); it ran no sbt. Coordinator ran the JDK 17 version probe (exit 0), `git status --short --branch`, `git rev-parse HEAD`, plan SHA-256, and the full `sbt -batch check` command captured exactly in `test-report.md`. First sandboxed check exited 1 before tests because `~/.sbt/boot/sbt.boot.lock` was denied; the approved retry passed 479/479 before ID hardening. The coordinator then ran a second full check on the final stable tree, copied its log, extracted test counts, and ran `git diff --check` (exit 0). All observed outputs are in `test-report.md` and `evidence/6b/`.

TEST RESULTS: Domain targeted contract suite 5/5 initially and 6/6 after final ID hardening; initial full core suite 134/134. Final stable-tree full `sbt check` passed **480/480**, zero failed: core 135, Hadoop 64, entity resolution 39, Spark smoke 1, independent 234, build verification 7. sbt reported 417 seconds; `/usr/bin/time` reported real 418.74 seconds. The injected format-stage failure and Hadoop failure traces in the log are expected failure-path self-tests; the final check exited 0.

VALIDATION RESULTS: New `researcher:dblp:<sha256>` IDs preserve case and homonym suffixes; `StableIds.parseResearcherId` accepts them. The new analytics ID helpers reject malformed window labels and LF-containing material that could otherwise collide under LF joining. Frozen `CoauthorEdge` and `ResearcherMetrics` examples still parse. `SparkCoauthorEdge` and `CoauthorEdgeSupport` represent all-years support from yearless DBLP works without fabricating year bounds. `TemporalChange` has presence flags and optional deltas so entering/leaving researchers do not acquire invented zero observations. New output records use `scholarchain.spark-analytics.v1` and context/lineage; config uses `scholarchain.spark-analytics-config.v1` with canonical JSON fingerprint, strict field checks, approved windows and caps. Sixteen new wire snapshots round-trip and validate. The Spark README designs jobs 1–11 with inputs/outputs, versions, partitioning, joins, shuffle/checkpoint, bounded driver behavior, invariants, provenance and layout, aligned to the final core examples. `git diff --check` exited 0.

ASSUMPTIONS: New example values labelled illustrative are contract examples, not observed Spark outputs; G1 arithmetic explicitly checked is hand-derived from the plan. Cross-row graph invariants, actual plans, counters and runtime output require the later Spark jobs. The default JSON contains local example run roots, not evidence of completed producer runs.

RISKS: No Phase 6 graph job, data run, physical plan or EMR runtime was executed in 6B. Existing F4/F6 release-preparation findings from 6A remain open for 6H. A selected Spark/Scala-compatible EMR runtime remains unverified. The 6C shared Spark harness must set the plan's UTC, shuffle partitions and temporary warehouse/checkpoint paths.

MANUAL ACTION REQUIRED: The user launches the separate read-only 6B reviewer and commits an approved 6B before starting 6C. No agent commits or pushes.

BLOCKED-ON OWNER: None for 6B.

BLOCKED-ON EVIDENCE: None for 6B; later runtime and cloud gates are explicitly unverified.

NEXT GATE: User-run independent Subphase 6B review using the Section 11 prompt in the coordinator handoff. Stop before 6C.

## Subphase 6B — repair round 1 (user-requested F1–F4)

STATUS: COMPLETE for the requested local repairs; independent external recheck pending.

OWNER: Coordinator `/root` assembled this report and evidence. Native `domain-engineer` `/root/domain_6b_r1` was the sole writer of `modules/core/**`; native `spark-engineer` `/root/spark_design_6b_r1` was the sole writer of `modules/spark/README.md`. Their exact deployed model IDs were unavailable. No reviewer was launched.

WORK ORDER: On `phase-6`, base/current HEAD `bc1e4a17fc879b7aac254b28d83e78dbdd34e367`, repair the external review's F1–F4 in the existing uncommitted 6B tree. The user instructed exactly “Fix F1, F2, F3, F4 for me” and chose exactly “yes, use chunkOrProfileId” for F2. F5–F8 are deferred with owner and gate in `repairs.md`. No 6C work, cloud call, commit or push was authorized.

FILES CREATED: Coordinator created `evidence/6b/repair-1/final-check.txt` and `targeted-contract.txt`. No new implementation path was needed; the new 6B source and wire files remain untracked until the user's commit.

FILES MODIFIED: Domain owner edited `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/StableIds.scala`, `DomainValidation.scala`, `SparkAnalyticsContracts.scala`, `SparkAnalyticsValidation.scala`, `modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsContractSpec.scala`, `modules/core/src/test/resources/wire/spark-semantic-summary.json`, and `modules/core/README.md`. Spark owner edited `modules/spark/README.md`. Coordinator appended the external review to `review.md` and edited `prompt.md`, `repairs.md`, this report and `test-report.md`. No Phase 5, build, Hadoop, ER, Terraform or human-owned file was changed.

COMMANDS RUN: The domain owner reported a JDK 17 targeted Spark analytics contract suite (11/11), full core suite (140/140) and `git diff --check` (exit 0). Its first targeted attempt failed only because the previous semantic-summary snapshot still held the old ID; the owner regenerated that snapshot and reran successfully. The coordinator independently ran `env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6b-repair1-final-check.txt 2>&1` (exit 0), copied the full log to `evidence/6b/repair-1/final-check.txt` (exit 0), and ran the same JDK 17 environment with `sbt -batch 'core/testOnly *SparkAnalyticsContractSpec' > evidence/6b/repair-1/targeted-contract.txt 2>&1` (exit 0). `git diff --check` exited 0. The Spark owner reviewed the updated Job 10 wording and 11 job headings; no sbt command was needed for its documentation-only edit. Exact coordinator commands and outputs are in `test-report.md` and the retained logs.

TEST RESULTS: The final full check passed **485/485**, zero failed: core 140, Hadoop 64, entity resolution 39, Spark smoke 1, independent 234, build verification 7. sbt reported 416 seconds and `/usr/bin/time` reported `real 418.15`. The targeted Spark analytics contract suite passed 11/11. The failure trace for `checkProbeInjectFailure` inside the final log is the expected failure-path self-test; the overall process exited 0.

VALIDATION RESULTS: F1 now applies the frozen metric arithmetic and zero consistency rules plus new max-team ID/tie bounds, with negative cases. F2 uses `StableIds.chunkOrProfileId` through `sparkSemanticSummaryId`, binding policy and window into `sourceVersion`; the validator accepts only that ID, the wire example was regenerated, and both READMEs agree. F3 feature tests cover NFC, malformed/unknown IDs, all reviewer-listed window configuration failures and G1 J solo/A-to-H no-path rows. F4 makes `spark-coauthor-edge:` an accepted `EvidenceItem` locator with tests. The different Spark edge ID is recorded as an additive plan deviation; legacy IDs are unchanged. `git diff --check` exited 0.

ASSUMPTIONS: The wire examples are illustrative contracts, not Spark computation output. `sourceVersion` uses the validated policy and window tokens separated by `:`. The future Neptune mapping for a yearless all-years edge needs domain/storage design before Phase 7 loading.

RISKS: F5–F8 remain deferred as recorded in `repairs.md`. No production Spark graph job, data run, EMR linkage or cloud execution occurred. The earlier 6A F4/F6 release-preparation findings remain open for 6H.

MANUAL ACTION REQUIRED: The user runs a separate read-only recheck of 6B repair round 1, then decides whether to approve and commit 6B. No agent commit or push was made.

BLOCKED-ON OWNER: None for the requested local F1–F4 repairs. `storage-engineer` and domain support are needed later for yearless Neptune mapping; `domain-engineer` owns deferred F5–F7 before their listed gates.

BLOCKED-ON EVIDENCE: None for the local gate. Runtime graph, export and cloud compatibility evidence belong to later subphases.

NEXT GATE: User-run independent read-only 6B repair-round recheck. Stop before 6C.

## Subphase 6C — inputs, canonical builder and graph (jobs 1–2)

STATUS: COMPLETE for the local 6C implementation and JDK 17 gate; independent external review pending.

OWNER: Coordinator `/root` assembled evidence and ran the final gate. Native `domain-engineer` `/root/domain_6c` was the sole author of `modules/core/**`; native `spark-engineer` `/root/spark_6c` authored `modules/spark/**`; native `test-engineer` `/root/test_6c` authored `tests/**`. At the Spark owner's request the coordinator invoked `scalafmt` on its files, then the owner finished and confirmed the source. Exact deployed specialist model IDs were unavailable to the coordinator; the user's prior choice was the current model for each role. No reviewer was launched.

WORK ORDER: On `phase-6`, base and current HEAD `01d204b531d3fc72a5c49f884980a5c7c8926b18`, implement only plan Subphase 6C. The user approved excluding enrichment-only works, preserving distinct DBLP names across accepted cross-name links, binding numeric bounds into new Spark edge IDs (prior F6), and using the logical config fingerprint for deterministic run identity (prior F7). After the initially approved `f22f1a12…` prepared root proved to lack a retained DBLP partition, the user approved completed DBLP-bearing Hadoop run `target/phase4-runs/ccd26111-d26d-4783-bc0f-e7106e4e617d`. No AWS, live LLM, 6D, reviewer, commit or push was authorized.

FILES CREATED: Spark owner created `BoundedActions.scala`, `Phase6CReaders.scala`, `Phase6CJobs.scala`, `Phase6CMain.scala` under `modules/spark/src/main/scala/edu/uic/cs441/scholarchain/spark/` and `Phase6CJobsSpec.scala` under Spark tests. Test owner created `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/{IndependentPhase6G1,IndependentPhase6CGraphSpec}.scala`. Coordinator created `evidence/6c/` logs and summaries. The offline ER input and local Spark outputs are ignored under `target/`, not tracked source.

FILES MODIFIED: Domain owner changed `modules/core/README.md`, `SparkAnalyticsConfig.scala`, `SparkAnalyticsContracts.scala`, `SparkAnalyticsValidation.scala`, `StableIds.scala`, `SparkAnalyticsContractSpec.scala`, and three new Spark wire snapshots. Spark owner changed `modules/spark/README.md`. Coordinator changed `docs/agent-runs/phase-06/{prompt.md,repairs.md,owner-report.md,test-report.md}`. No build, Hadoop, entity-resolution, Terraform, Phase 5, `.claude/**`, or human decision file changed.

COMMANDS RUN: JDK 17 preflight and exact offline ER-export command/output are in `evidence/6c/{preflight.md,er-export.txt}`; the export exited 0 with `--llm-mode disabled`. Domain owner ran JDK 17 core formatting, contract and full core tests (exit 0; 13/13 targeted, 142/142 core). Test owner ran JDK 17 independent formatting and `independentTests/testOnly *IndependentPhase6CGraphSpec` (exit 0; 4/4). Coordinator ran JDK 17 Spark formatting and `sparkAnalytics/testOnly *Phase6CJobsSpec` (exit 0; **6/6** after the input-binding and published-provenance repairs), then a fresh `sparkAnalytics/Test/runMain edu.uic.cs441.scholarchain.spark.Phase6CMain target/phase6-inputs/6c-spark-config-provenance.json` (exit 0; real 20.05 s). The first full `sbt -batch check` on an earlier tree exited 0 with 496/496; an intervening full gate was canceled at exit 130 when the coordinator found a published-row provenance gap. The **final** JDK 17 `sbt -batch check` exited 0 with 497/497, real 459.53 s. Exact environment, redirections and intermediate failed commands are in `test-report.md`. Final `git diff --check` exited 0. A source scan found production `collect()` calls only inside capped `BoundedActions`; no RDD, GraphX, GraphFrames or typed-encoder use.

TEST RESULTS: The retained final gate passed **497/497**, zero failed: core 142, Hadoop 64, entity resolution 39, Spark 7, independent 238, build verification 7. The log starts with sbt 1.10.7 on Homebrew Java 17.0.20.1 and ends `[success] Total time: 458 s`; `/usr/bin/time` reports real 459.53 s. `evidence/6c/final-check.txt` is 247,609 bytes with SHA-256 `3e2fd5453af35cdf4b7e0f88c1ed4e3d273dd57325fe734cd7eb9e54538682c4`. The injected failure trace in the build-verification self-test is expected; the full command exited 0.

VALIDATION RESULTS: The Hadoop and ER readers check completion, inventory/hash and explicit schemas. The reader also compares ER `prepCompletionHash` with SHA-256 of the selected Hadoop completion marker plus newline plus run manifest bytes before reading rows; one golden-hash positive and missing/mismatched negatives passed. Malformed JSON is retained in a reject DataFrame/table with a counter; mismatched schema versions and missing required fields fail. At publication, each table has top-level `runId` and `schemaVersion`; rejects also retain the captured source file path and Hadoop/ER lineage. Module tests check those schemas and a malformed reject row. Job 1 applies DBLP-name identity and complete grouping constraints, excludes enrichment-only works from graph/metrics, records unapplied cross-DBLP links, and emits typed graph nodes/edges. Job 2 derives distinct-work weighted, windowed coauthor edges and support, with pair-count and endpoint integrity checks. The deterministic run ID uses both input manifests and logical settings, while the completion gate refuses a partial or different existing output. Frozen GraphNode/GraphEdge JSON round trips and positive Hadoop/ER wire reads passed. Module and independent G1 tests assert hand-computed graph rows; independent adversarial tests include cross-DBLP links, cannot-links, yearless/2027 works and enrichment-only exclusion. The final local smoke used the approved Hadoop run and a completed matching offline ER export: run ID `run:50e1fc99-a22c-4993-9525-7772e6af1fac`, 6 weighted edges, 6 support rows, 0 integrity rows, 0 input rejects and 21 counters. It retained 12 formatted plans and a bounded SparkListener summary with 382 completed stages, 807 successful tasks, 0 failed tasks and no spills. The event summary explicitly states that the local Spark event file was disabled. Prior 6B F6/F7 are closed in `repairs.md` with core tests and local manifest evidence.

ASSUMPTIONS: The retained `ccd26111…` Hadoop run and the locally produced disabled-mode ER export are completed and match by the ER export's prep-completion hash; the smoke reader checks that binding, both manifests and inventories. The offline resolver made zero fake/live LLM calls. The SparkListener aggregate is operational evidence from local task/stage events, not a durable full event log or an EMR run. The 6C manifest and paths are intermediate jobs 1–2 output; Job 11's final partition layout, content hashes and load manifests remain 6F scope.

RISKS: The first independent Spark test attempt hit memory pressure; the test owner and Spark owner reduced lineage/session retention, and targeted and full gates passed without raising heap. An initial graph-wire test failed because test JSON omitted null provenance keys, a first compile failed on a wrong Spark `Success` import, and a first refreshed smoke failed because readers checkpointed before the checkpoint directory was set; each was repaired and rerun, with failures recorded. The published-reject test caught an empty file path after caching; the reader now captures the path before caching and the rerun passed. `sparkAnalytics/runMain` lacks Provided Spark classes, so the local smoke uses `sparkAnalytics/Test/runMain`; cluster packaging is a later gate. A hard failure before 6C publish does not yet retain integrity/counters; Job 11 in 6F must address final failure evidence. Prior F5 and R1 contract hardening, the yearless Neptune mapping and 6A JDK packaging guard remain assigned to their later gates. No live cloud or EMR compatibility result is claimed.

MANUAL ACTION REQUIRED: User launches a separate read-only 6C review and, only after approval, decides whether to commit this uncommitted 6C tree. No agent committed or pushed.

BLOCKED-ON OWNER: None for 6C. `domain-engineer` owns deferred F5/R1 before their producer gates; `storage-engineer` owns Phase 7 target/yearless mapping, with domain support; `build-engineer` owns the 6A release packaging guard before 6H.

BLOCKED-ON EVIDENCE: None for the local 6C gate. Final Job 11 content hashes/load manifests, EMR runtime linkage and live cloud evidence belong to their later gates.

NEXT GATE: User-run independent read-only Subphase 6C review using the Section 11 prompt in the handoff. Stop before 6D.

## Subphase 6C — repair round 1 completion (F1–F5, R1-1 and R1-2)

STATUS: COMPLETE for the requested blocking repairs and final local gate; independent external recheck pending.

OWNER: Coordinator `/root` owns this report and final evidence. `spark-engineer` `/root/spark_6c` authored the F1–F5 changes under `modules/spark/**`; successor Spark owner `/root/spark_6c_repair_finish` closed R1-2 and ran the module suite after the first Spark agent hit a usage limit. `test-engineer` `/root/test_6c` authored the independent F1/F2 cases under `tests/**`. No reviewer was launched by the coordinator.

WORK ORDER: The user supplied an external `REQUEST-CHANGES` review for 6C, asked to fix all blocking bugs F1–F5, then supplied a recheck blocking on R1-1 (missing final-tree evidence) and R1-2 (unchanged deterministic run ID). The user narrowed the final work to blocking bugs only. Branch `phase-6`, base/current HEAD `01d204b531d3fc72a5c49f884980a5c7c8926b18`; 6C remains uncommitted.

FILES CREATED: `docs/agent-runs/phase-06/evidence/6c/repair-1/**` including targeted, smoke, counter-inspection and full-gate logs; `CounterInspect.java` is a bounded local evidence probe and does not participate in the build. The fresh config and output root were created under ignored `target/phase6-inputs/` and `target/phase6-runs/`. The original 6C implementation files were untracked before the repair.

FILES MODIFIED: Spark owner changed `Phase6CJobs.scala`, `Phase6CReaders.scala`, `Phase6CMain.scala`, `Phase6CJobsSpec.scala` and `modules/spark/README.md`; test owner extended `IndependentPhase6CGraphSpec.scala`; coordinator changed `docs/agent-runs/phase-06/{prompt,review,repairs,owner-report,test-report}.md`. No core, build, Hadoop, ER, Terraform, Phase 5, `.claude/**` or human-owned file was changed by this repair round.

COMMANDS RUN: Spark owner ran JDK 17 `sbt -batch 'sparkAnalytics/Compile/scalafmt' 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/Compile/scalafmtCheck' 'sparkAnalytics/Test/scalafmtCheck' 'sparkAnalytics/testOnly *Phase6CJobsSpec'` (exit 0, 14/14) and `git diff --check -- modules/spark` (exit 0). Test owner ran JDK 17 independent formatting/check and `sbt -batch 'independentTests/testOnly *IndependentPhase6CGraphSpec'` (exit 0, 6/6). Coordinator independently reran the latter on the final tree (exit 0, 6/6), then a fresh JDK 17 `sparkAnalytics/Test/runMain` smoke (exit 0), exported the Spark test classpath and ran a bounded read-only Java/Spark counter probe (exit 0), and ran the full JDK 17 `sbt -batch check` (exit 0). `git diff --check` exited 0. Exact coordinator command lines, environment, intermediate sandbox retry and log paths are in the 6C repair section of `test-report.md`.

TEST RESULTS: Final-tree targeted Spark module **14/14**, independent **6/6**; full gate **507/507**, zero failed (core 142, Hadoop 64, entity resolution 39, Spark 15, independent 240, build verification 7). Full check reported 512 seconds; `/usr/bin/time` reported real 513.92. `repair-1/final-check.txt` is 253,775 bytes, SHA-256 `6c0fdf7494269c2ccb71a8cdbee35cb36b4c574b4d3d34928e2e37352c5a7773`. The injected build-verification failure trace is expected; the gate exited 0.

VALIDATION RESULTS: F1 keeps only the rank-1 DBLP team and pairs and counts dropped observations. F2 records one non-hard integrity row and counter for a DBLP-name group with conflicting observed ORCIDs without splitting its identity. F3 records missing graph endpoints as hard-failure integrity rows and a counter when the flag is off and throws when it is on. F4 reads and counts ER unresolved/conflict decisions for both entity types through explicit schemas and the reject path. F5 module cases cover grouping conflicts, ambiguous links, missing/mismatched markers and inventory, and literal 18-edge G1 weights/years. `Phase6CMain.codeVersion` is now `spark-phase6c-jobs1-2-v2`, and a module test rejects reuse of the prior v1 manifest. The fresh smoke emitted `run:d56e56d9-de03-4862-bc66-46fd5ad27b75`, distinct from the old `run:50e1fc99-a22c-4993-9525-7772e6af1fac`; its Parquet counters were researcher unresolved 6/conflict 0, work unresolved 0/conflict 3, and missing graph endpoints 0. The smoke published 6 weighted edges and 6 support rows with no integrity rows or input rejects. All implementation source mtimes preceded the final gate.

ASSUMPTIONS: The fresh smoke uses the previously approved completed DBLP-bearing Hadoop run `ccd26111…` and matching offline disabled-mode ER export. The bounded counter probe read 28 published counter rows locally; it is evidence code, not a production driver path.

RISKS: R1-3 (authority-rule README wording), R1-4 (ORCID whitespace normalization) and prior nonblocking N findings remain outside the user's blocking-only scope. The original N1–N9 and later-gates text was supplied with the external approval and is now retained in `review.md` and routed in `repairs.md`. Hard-failure persistence before abort remains a 6F gate; no AWS or live EMR runtime was tested.

MANUAL ACTION REQUIRED: User runs a separate read-only recheck and decides whether to approve and commit 6C. Do not commit or start 6D before that gate.

BLOCKED-ON OWNER: None for the requested blocking local repairs. External reviewer decision pending.

BLOCKED-ON EVIDENCE: None for F1–F5 or R1-1/R1-2 local acceptance; later cloud and 6F gates remain open.

NEXT GATE: User-run independent read-only 6C repair-round recheck. Stop before 6D.

### External 6C repair-round approval disposition

The user-supplied independent reviewer returned **APPROVE** for Subphase 6C repair round 1. The full verdict is appended verbatim in `review.md`. It verified the final-tree timing, 14/14 module and 6/6 independent targeted results, 507/507 full JDK 17 gate, real ER counters, v2 run ID, manifest marker and Spark API scan. It found no remaining 6C blocker. Its nonblocking register and later gates are recorded in `repairs.md`; no implementation change was made after the reviewed gate. The next gate is the **user's 6C commit**, then a new Subphase 6D Step 0 prompt. No agent commit or push is claimed.


## Subphase 6D+6E — jobs 3–8 implementation and handoff

STATUS: COMPLETE for implementation and local deterministic gates; external read-only review is pending.

OWNER: Spark owner `/root/spark_6de` wrote `modules/spark/**`; independent test owner `/root/test_6de` wrote `tests/**`; core owner `/root/domain_6de` wrote the prerequisite F5 contract hardening in `modules/core/**`. Coordinator `/root` assembled evidence, executed the final independent formatter/test command at the test owner's request, and ran the final full gate. This formatter execution is disclosed in `evidence/6de/commands.md`. No agent issued an approval verdict.

WORK ORDER: User requested the merged 6D+6E run of the updated external plan (SHA-256 `6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096`) and prohibited commits and reviewer launches. Branch `phase-6`, base and unchanged HEAD `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4`. The initial tree was clean. All four Step 0 answers and tool/model provenance are recorded in `prompt.md`.

FILES CREATED: `modules/spark/src/main/scala/edu/uic/cs441/scholarchain/spark/Phase6DEJobs.scala`; `modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase6DEJobsSpec.scala`; `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentPhase6DEGraphSpec.scala`; `docs/agent-runs/phase-06/evidence/6de/**` (preflight, exact commands, targeted/intermediate/full logs, source timing/scan, final-gate metadata).

FILES MODIFIED: Core `SparkAnalyticsConfigLoader.scala`, `SparkAnalyticsValidation.scala`, `SparkAnalyticsContractSpec.scala`; `modules/spark/README.md`; coordinator `prompt.md`, `repairs.md`, `owner-report.md`, `test-report.md`. No build, Hadoop, entity-resolution, Phase 5, dataset, Terraform, or tracked constitutional file changed. The full gate updates the ignored generated test marker through the existing build task.

COMMANDS RUN: Exact commands and environment are retained in `evidence/6de/commands.md` and the test report. Final Spark owner targeted command: JDK 17 `sbt -batch 'sparkAnalytics/scalafmt' 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/testOnly *Phase6DEJobsSpec'` (exit 0, 9/9). Final coordinator independent command: `sbt -batch 'independentTests/Test/scalafmt' 'independentTests/Test/scalafmtCheck' 'independentTests/testOnly *IndependentPhase6DEGraphSpec'` (exit 0, 10/10). Final coordinator `/usr/bin/time -p sbt -batch check` with JDK 17 and the Phase 4 SBT_OPTS config exited 0. `git diff --check` exited 0. The source scan matched only the two allowed `collect()` calls in `BoundedActions`. A read-only course README lookup checked scope; no AWS or live model calls were made.

TEST RESULTS: Full gate **527 passed / 0 failed**: core 143, Hadoop 64, entity resolution 39, Spark 24, independent 250, build verification 7. The new targeted suites are subsets of those totals. Full log: `evidence/6de/final-check.txt`, **285,463 bytes**, SHA-256 `bd8b9a28348839769b5410364c3f7893fe37bb1c871eac27d7595fba75dbca34`; sbt 565 s, real 567.12 s, Homebrew Java 17.0.20.1, sbt 1.10.7. All source/test/README modification times precede the final full gate; `source-check.txt` retains them.

VALIDATION RESULTS: `Phase6DEJobs.build` extends the committed 6C membership, edge and support tables with P/C/T/A/M/W metrics and capped maximum-team evidence, deterministic components and summaries, exact h-index coreness, selected-pair distributed BFS with support-backed hops and three statuses, seeded K-pair selection, synchronous weighted LPA with per-window convergence information, cross-community edges and the three required bridge measures. W==T and CC/k-core iteration guards have failure cases. Tests cover the full literal G1 metric table, components, coreness and unique path; G2 star, G3 K4, G4 path; injected G1/G2 bridges; hand-traced convergent LPA; no cross-component community; solo/tie/cap/empty/single/yearless cases; and replay determinism. Coordinator checks found and routed an immediate-predecessor BFS tie mismatch; module and independent fixtures now distinguish it from whole-route ordering and pass. Existing wire fields and ID formulas are unchanged. Core F5 local invariants are closed for these producers.

ASSUMPTIONS: The builder consumes valid completed 6C canonical tables and caller-supplied explicit config. Approved settings are CC/k-core limits 50, checkpoint 5, LPA limit 20 with disclosed non-convergence, maxHops 6, K=20 and S=32 with seed 441. The original gate did not establish these values in the shipped resource; repair round 1 (F1) corrects that mismatch and records the fingerprint change below. Fixture configs deliberately use smaller LPA limits and disable random-pair additions where exact benchmark counts are asserted. This is bounded synthetic-fixture validation, not a real-data performance claim.

RISKS: The user prioritized selected-pair BFS; the separate S-source distance estimate remains an empty typed table, with no estimate claimed. Optional betweenness was declined. Jobs 3–8 do not yet have a publishing CLI: final export, durable event logs/summarizer, publication-level plans, hard-failure persistence, a bounded real-data pipeline and replay belong to 6F+6G. The targeted module log includes an uncheckpointed metrics physical plan and checkpointed output plans. LPA can oscillate and bridge values depend on its partition. Prior 6C N items and semantic-summary entity-kind validation remain routed to their named later gates in `repairs.md`; jobs 3–8 do not consume the 6C diagnostic counters. EMR remains untested, with script/live work deferred to Phases 13/15 by the updated plan.

MANUAL ACTION REQUIRED: User launches the separate read-only 6D+6E reviewer using the handoff prompt. After approval, the user decides whether to commit this tree. No commit, push or reviewer was launched by an implementation agent.

BLOCKED-ON OWNER: None for the requested local implementation gate.

BLOCKED-ON EVIDENCE: None for the 6D+6E fixture and full-check gates; the later publication/real-data/cloud gates above remain open.

NEXT GATE: User-run independent read-only review of merged Subphase 6D+6E. Stop before 6F+6G.


## Subphase 6D+6E — repair round 1 completion (external F1–F3)

STATUS: COMPLETE for blocking repairs and local validation; user-run external recheck is pending.

OWNER: Domain owner `/root/domain_6de` changed the shipped config and core assertions (F1); Spark owner `/root/spark_6de` changed the module test and README (F1/F2); coordinator `/root` corrected report coverage (F3), retained the complete user-supplied review and evidence, and ran the final full gate. The coordinator executed the Spark owner's supplied formatter/check/test command after the owner's sandbox denied its sbt boot lock; all test logic remains owner-authored. No independent-test source changed this round.

WORK ORDER: User instructed "fix all of the blockings bugs for me" after the external 6D+6E `REQUEST-CHANGES` review. F1–F3 only; nonblocking N1–N9 and future gates are registered in `repairs.md`. Branch `phase-6`, base and unchanged HEAD `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4`; pre-existing uncommitted 6D+6E work was preserved. Existing Step 0 approval of 50/50/K20 supplied the F1 decision; no new decision was needed.

FILES CREATED: `docs/agent-runs/phase-06/evidence/6de/repair-1/**`: core format/targeted logs, module sandbox-denial and successful targeted logs, direct Java version, source timing/API/diff checks, exact commands, full-check log, final-gate metadata and reviewer handoff.

FILES MODIFIED: Domain owner: `modules/core/src/main/resources/scholarchain.spark-analytics-config.v1.json`, `modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsContractSpec.scala`. Spark owner: `modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase6DEJobsSpec.scala`, `modules/spark/README.md`. Coordinator: `docs/agent-runs/phase-06/{review,prompt,repairs,owner-report,test-report}.md`. No production Scala algorithm, existing wire field, ID formula, build, Hadoop, ER, dataset, infrastructure or human-decision file changed in this repair. The generated ignored test marker was updated by the existing full-gate build task.

COMMANDS RUN: JDK 17 with the Phase 4 SBT_OPTS logging config. Core owner ran `sbt -batch 'core/scalafmtAll' 'core/Compile/scalafmtCheck' 'core/Test/scalafmtCheck'` and `sbt -batch 'core/testOnly *SparkAnalyticsContractSpec'`, exit 0, 14/14. Coordinator ran `sbt -batch 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/Test/scalafmtCheck' 'sparkAnalytics/testOnly *Phase6DEJobsSpec'`, exit 0, 10/10; then `/usr/bin/time -p sbt -batch check`, exit 0. Exact environment, commands, log paths and failure handling are in `evidence/6de/repair-1/commands.md` and the repair test report. `git diff --check` exited 0; source scans still match only the two allowed BoundedActions collect sites. No commit, push, reviewer launch, AWS call or live model-provider call occurred.

TEST RESULTS: Fresh full gate **528 passed / 0 failed**: core 143, Hadoop 64, ER 39, Spark 25, independent 250, build verification 7. Core targeted **14/14**, Spark module targeted **10/10**; those tests are included in the full totals. Full log: `evidence/6de/repair-1/final-check.txt`, **286,117 bytes**, SHA-256 `18d9858bc70337879054a388868dede84e19b2f568f12b2e5e50d2d1c833112f`; sbt **561 s**, real **563.44 s**, Java **17.0.20.1**, sbt **1.10.7**. It finished 2026-10-22 12:47:16 CDT, after all repair source/resource/test/README edits.

VALIDATION RESULTS: F1 is repaired: the resource ships CC50/k-core50/checkpoint5/community20/maxHops6/K20/S32/seed441, and every value is asserted. Full and logical fingerprints change, with exact old/new hashes printed in `core-targeted.txt` and stored in metadata. These are canonical hashes of the config example, not the historical smoke config. Existing 6C manifests and run IDs remain unchanged history. F2 is repaired: the weight-1 two-person graph swaps labels for three synchronous iterations; all two memberships are non-converged at iteration 3, both singleton summaries have changed count 2 and non-converged status, counters are communityConverged=0/communityFinalChangedCount=2, and actual output rows parse to core records accepted by validation. The membership record has no changed-count field; its wire is preserved. F3 is repaired: the original inaccurate test-report sentence now attributes G1–G4 literal coverage to the independent suite, and describes the separate module fixtures accurately. README describes the new oscillation fixture and actual shipped settings.

ASSUMPTIONS: Existing approved default values remain authoritative. The fixed sampling seed is 441. All production algorithms are the same as the externally inspected 6D+6E implementation; this repair changes default config behavior, test evidence and documentation.

RISKS: Nonblocking N1–N9 remain routed to named owners/gates; F2 partially addresses N7 only for community membership/summary validation. Full export validation, BFS performance, LPA iteration/cache details, context schema order, missing-endpoint counters, bounded-window metrics and complete replay remain 6F+6G work. The sampled distance estimate must be built in 6F+6G or explicitly accepted as a deviation by the human at 6I. No such human acceptance is claimed. EMR work remains deferred to Phases 13/15. No real-data run was added in this repair.

MANUAL ACTION REQUIRED: User runs the separate read-only repair-round recheck, then decides whether to commit after approval. No agent starts 6F+6G or commits.

BLOCKED-ON OWNER: None for F1–F3 local repairs.

BLOCKED-ON EVIDENCE: None for F1–F3 targeted/full gates.

NEXT GATE: User-run independent read-only recheck of Subphase 6D+6E repair round 1. Stop before 6F+6G.


### External 6D+6E repair-round-1 approval

The user-supplied independent reviewer returned **APPROVE**, closing F1–F3 and verifying the retained 528/0 full-gate evidence, core 14/14 and Spark 10/10 targeted results. Its complete text is retained in `review.md`; R1-O1 is assigned in `repairs.md`. These are reviewer-reported checks, not a new test execution. The approved tree is still uncommitted at HEAD `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4`. The next gate is the user's commit, followed by 6F+6G Step 0. No next-subphase work, commit or push was performed by the coordinator.


## Subphase 6F+6G — implementation and local validation complete

STATUS: COMPLETE for implementation and local validation; independent user-launched review remains pending.

OWNER: `spark-engineer` `/root/spark_6fg` owns Spark production, module tests and README; `test-engineer` `/root/test_6fg` owns independent tests/fixtures; `dataset-engineer` `/root/dataset_6fg` owns acquisition, manifests and dataset tests; domain owner owns the core summary entity-kind validation/test. Coordinator `/root` assembles this phase's reports/evidence and executes the unchanged upstream CLIs, Spark runs and final gate. The coordinator executed owner-requested formatter commands while holding the sbt slot; owners authored the source/test logic. Capacity interruptions in owner turns were resumed without changing model assignment. Exact deployed model builds and native tool versions are unavailable; current inherited models, Java 17.0.20.1, sbt 1.10.7 and Python 3.14.5 are recorded. No reviewer role was launched.

WORK ORDER: Implement only merged 6F+6G under plan SHA-256 `6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096`. User committed the approved prior tree; branch `phase-6`, base and unchanged HEAD `6ae7378cbef90a176fd1faecae0dee0615eba9e3`. All six Step 0 answers are recorded in `prompt.md`: factual summaries under 1,200 characters; approved pinned venue/year slice capped at 20,000 publications and 1.25 GiB/30 minutes; unchanged local Hadoop→ER→Spark with LLM disabled; required S-source distance/P90 estimate; N1/N3/N4 repairs; N2/N5 implementation/documentation. No human decision is rewritten.

FILES CREATED: Five dataset acquisition/provenance/test files; seven Spark production helpers (`Phase6Context`, `Phase6EventLog`, `Phase6Export`, `Phase6FGJobs`, `Phase6Main`, `Phase6Plans`, `Phase6Report`) and `Phase6FGJobsSpec`; four independent Scala files and two tiny fixture resources; `evidence/6fg/**`. Exact paths are in `evidence/6fg/changed-files.txt` and the stable source snapshot.

FILES MODIFIED: Core `SparkAnalyticsValidation.scala` / `SparkAnalyticsContractSpec.scala`; Spark README, `Phase6CJobs.scala`, `Phase6CReaders.scala`, `Phase6DEJobs.scala`, C/DE module specs; coordinator `prompt.md`, `repairs.md`, `owner-report.md`, `test-report.md`. No build, Hadoop, ER, Phase 5, infrastructure or human-owned file changed. The existing successful build task updated only the ignored generated test marker.

COMMANDS RUN: Exact environment, arguments, exit codes and failure sequence are in `evidence/6fg/commands.md`. Every sbt/Spark command used JDK 17 and the Phase 4 logging SBT_OPTS. Dataset tests/extraction/replay passed. Hadoop CLI exited 0 (37.38 s). The first ER CLI failed its 256 MiB output bound (exit 2); raising only the ignored local output limit to 2 GiB yielded exit 0 (97.23 s), 20,000 comparisons, fake calls 0/live calls 0. Spark direct-Java command arrays retain its 4 GiB heap, all 15 opens and exact local test classpath. The first real Spark attempt failed a Union/checkpoint optimizer constraint rewrite (exit 1, 83.61 s); fresh repaired full runs exited 0 in 180.45 s and 158.07 s. The final `/usr/bin/time -p sbt -batch check` exited 0; `git diff --check` exited 0. No commit, push, AWS, store load, live model call or reviewer was triggered.

TEST RESULTS: Full stable-tree gate **551 passed / 0 failed**: core **144**, Hadoop **64**, ER **39**, Spark **34**, independent **263**, build verification **7**. sbt **691 s**, real **692.82 s**, finished **2026-10-22 13:51:06 CDT**. Full unfiltered log is **1,358,948 bytes**, SHA-256 **`6f48042efe332864661f5d8a73dfa8565fd257db53ff3bcc97371b724919844c`**. Dataset Python tests **12/12** are separate from the Scala total. Core target **15/15**; latest module targets **33/33** (15 C / 12 DE / 6 FG). The combined target then exposed a new independent assertion decoding the sidecar Long count as a number; correction `.str.toLong` passed the tiny pipeline **1/1**, and every latest assertion is included in the final **263/263** independent result. Earlier independent target **13/13** is retained with its pre-final-assertion scope explicitly disclosed. See `test-report.md` for all initial failures and exact line evidence. Expected injected Hadoop/build-probe failures are tests of failure handling, not gate failures.

VALIDATION RESULTS:

- Jobs 9–11 and one full CLI publish all 28 tables, four load-manifest arrays, a valid core RunManifest, operational sidecar, counters, plans, event summary and analytics report. Temporal rows represent entering/leaving researchers without fabricated zero deltas. Four summary types cite actual exported source fields; every stated number is traceable. Applicable rows validate on executors and are independently parsed; work-source projections and rejects have documented explicit schemas.
- Required seeded S32 complete BFS estimates now exist for every largest component. Exact three-node-chain expectation is mean 4/3 and empirical P90 2. Selected BFS stops complete found pairs, honors graph frontier/visited checkpoint intervals, and retains the smaller-immediate-predecessor rule. LPA uses corrected caching and per-window iteration reporting; a shared explicit context schema and missing benchmark endpoint counter are tested.
- Representative authority uses the work-ID prefix, ORCID normalization/graph properties are preserved, dropped-row counters are explicit, and yearless canonical DBLP counts include solos. A three-window eight-node-chain regression crosses checkpoint interval 5 and covers six-hop found/seven-hop exceeded outcomes with K20.
- The bounded slice contains **10,577** publications and **21,819** exact names, all eight venues/22 years. The one **1,107,081,001-byte** archive download took **244.720 s**, within approved caps; corrected extraction/replay used zero further network. Slice SHA-256 `c25a1e1a0d517abaadf370c88b3528039c50ad8ec3790c27381a3c2e2ecde522`. The original team lists were preserved; Hadoop counted 63 oversized teams and 21 authorless schema failures.
- Both actual Spark runs produced **`run:f02acf56-4bea-4009-adaf-b11d5afceb49`**, code fingerprint **`a6719cbb892e795e3b4e20be99c70c1c74c1ee8ce95887e8c418d9aeb3672971`**. Fresh roots/checkpoints and shuffle 4→2 produce **28/28 identical counts/content hashes and equal counters**. Both completion markers verify. The four load manifests are byte-identical; every path exists. Physical Parquet part counts differ (153/136), as allowed. Actual complete Parquet reread/hash checks are exercised independently for every table; the real-data replay comparison uses each fresh pipeline's logical hash computation, with filesystem/manifest consistency audited separately.
- Real all-years graph: **81,181** coauthor edges, **1,045** components, largest size **17,179**, fraction **0.81933515**, **178** singletons. There are **25 non-hard ORCID conflict warnings**, zero hard integrity failures, missing endpoints or pair mismatches. ER work unresolved/conflict counts **1,627/12,123** are read from the actual export. All six windows report LPA non-convergence at iteration 20, as expected where two-person components oscillate. `evidence/6fg/real-data-report.md` contains every window's graph/component/community results, metric min/median/P90/max, selected paths, distance estimates, rejection/integrity counts, stage/partition/shuffle summaries and output paths.
- All **27** source/config/test/manifest artifacts stayed unchanged during the final gate. The post-gate production class fingerprint still equals both real runs. The full log, source snapshot and `final-gate-metadata.json` prove timing and tree consistency. Only two production collect sites exist, both inside BoundedActions. The plan hash was recomputed unchanged.

ASSUMPTIONS: The convenience slice and existing small enrichment sources validate integration, not population statistics, identity accuracy or model calibration. The runtime measured is local Spark 3.5.4 / Java 17. The optimizer compatibility diagnosis is inferred from the observed Spark stack and primary source; no confirmed upstream issue is asserted.

RISKS: Synchronous LPA may not converge and final partitions are iteration-limited; bridge measures depend on that partition. Distance estimates cover sampled sources in largest components, not exact diameter. Fixed 256-shard row hashing holds each shard's sorted JSON on executors and needs measurement at larger scale. Reuse authenticates manifest/metadata identity but does not deeply audit completed Parquet files. Class-directory versus packaged-JAR fingerprints differ; cross-artifact/runtime replay is unverified. Representative policy is a version tag for the one implemented ordering rule, not alternate-policy dispatch. Temporal rows carry actual current communities and best overlap scores, not a separate matched-community identifier. Plans can be truncated by the documented memory cap. Load manifests remain Phase 7 proposals; yearless Neptune mapping and release packaging/runtime guards remain later gates. EMR is deferred to Phases 13/15. Codex-led execution does not imply instructor acceptance of a course-workflow deviation.

MANUAL ACTION REQUIRED: User launches the independent read-only 6F+6G review with the supplied prompt, then decides on a commit after approval. No 6I work has started.

BLOCKED-ON OWNER: None for implementation/local validation.

BLOCKED-ON EVIDENCE: None for this subphase's local gates; cloud/runtime gates remain explicitly deferred.

NEXT GATE: User-run independent read-only Subphase 6F+6G review. Stop before 6I.


## Subphase 6F+6G repair round 1 — blocking F1–F3

STATUS: COMPLETE for requested repairs and local validation; user-run independent recheck pending.

OWNER: Coordinator derived F1/F2 evidence and owns reports; test-engineer `/root/test_6fg` owns the sole implementation delta, `IndependentPhase6SafetySpec.scala`. The Spark owner reversed optional README changes after the user limited scope; README again has its original snapshot SHA `617b3af2b41e8b8100ed9b31ced5275ef22ae4829c780a2faa7cfc7341ef5f11`. No production or other source changed from the original reviewed tree.

WORK ORDER: Complete external review retained verbatim in `review.md` and `evidence/6fg/repair-1/external-review.txt`. User then instructed **"only fix the blockings bugs"**. Scope is F1–F3 only; F4–F12 are registered/deferred, including the evidence-retention choice. Base/unchanged HEAD `6ae7378cbef90a176fd1faecae0dee0615eba9e3`, branch `phase-6`; previous uncommitted work preserved.

FILES CREATED: `evidence/6fg/repair-1/` review copy, stage DAG/overview, report comparison, validation/command/source records, targeted/full logs, metadata, inventory and recheck prompt. FILES MODIFIED: SafetySpec plus coordinator review/prompt/repairs/reports, real-data report, replay comparison and handoff. Exact inventory is in `repair-1/changed-files.txt`. No retained raw event log, Parquet table, operational analytics report, counter array or run manifest was rewritten.

COMMANDS RUN: JDK17 and Phase4 logging environment in `repair-1/commands.md`. Coordinator executed owner-requested `sbt -batch 'independentTests/Test/scalafmt' 'independentTests/testOnly *IndependentPhase6SafetySpec'`: **7/7**, exit0, real5.79s. Then `/usr/bin/time -p sbt -batch check`: **554/554**, exit0, real**676.42s**, sbt674s, Java17.0.20.1/sbt1.10.7. `git diff --check` exit0. F1/F2 use streamed Python inspections of retained artifacts; no new real-data Spark execution. No AWS/live model/store call, reviewer, commit, push or6I.

TEST RESULTS: Core144/Hadoop64/ER39/Spark34/independent266/build7 = **554 passed / 0 failed**. Full log `repair-1/final-check.txt`: **1,358,928 bytes**, SHA-256 **`3e6654835296bab3be44efbdf0cd31c205dd4b34ff87b98848a4ba16623c5236`**, completed **2026-10-22 14:29:32 CDT**. All 27 repair source snapshot hashes/mtimes remained unchanged during the gate. Only SafetySpec differs from the original 27-file snapshot; all production, README, core and dataset contents match. Compiled production fingerprint remains `a6719cbb892e795e3b4e20be99c70c1c74c1ee8ce95887e8c418d9aeb3672971`, so retained real-data run `run:f02acf56-4bea-4009-adaf-b11d5afceb49` remains applicable.

VALIDATION RESULTS: F1 complete stage DAG has **5,667 stage IDs / 4,532 edges**, including referenced ancestor stages without tasks. Every name/partition count is present, all parents resolve and the graph is acyclic. All **2,004 executed stage-attempt** task/shuffle totals exactly match the existing summary. Raw successful log SHA/path and derivation are recorded; real-data report links the JSON and bounded actual subgraph and explicitly states the production summarizer gap. F2 comparison explicitly reports **28 logical tables equal** but **analytics report unequal**: **12 differing fields**, one approximate percentile and eleven means. First/replay file hashes and exact paths/values are retained. Distribution values quoted are from the first run; approximate-percentile and float-order dependence, including latent estimate-P90 risk, are disclosed. F3 detects eleven method names with/without parentheses, including isEmpty/reduce. Three synthetic tests cover 55 forbidden forms, identifier boundaries, comments/strings and audited bounded metadata exceptions. Targeted and full gates pass.

ASSUMPTIONS: DAG derivation is retained-event metadata inspection; no new application execution is implied. Logical-table equality is observed for the existing bounded replay, not a proof of partition-invariant approximation for all inputs.

RISKS: F4–F12 remain open under the user's narrowed scope. The scanner is a textual heuristic, not a Scala parser/type checker. Approximate reporting differences are disclosed rather than algorithmically eliminated. Existing evidence was preserved without optional cleanup; the required DAG and new full gate add evidence. Previous local-runtime/storage/EMR limitations remain.

MANUAL ACTION REQUIRED: User launches the independent read-only repair recheck, then decides on commit after approval. BLOCKED-ON OWNER: none. BLOCKED-ON EVIDENCE: none for F1–F3 local acceptance. NEXT GATE: User recheck; stop before6I.

## Subphase 6I — course-gate traceability (whole Phase 6)

This table maps the course Phase 6 jobs, operational/report requirements, gate
bullets, Detailed Spark requirements, and D08 deliverable to existing evidence.
**EVIDENCED** means local implementation/test or retained-run evidence is available;
it is not independent approval, instructor acceptance, or human ratification.
Fresh gate results are appended in the final 6I report below.

Sources: [course Phase 6](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-6-build-the-temporal-coauthorship-graph-and-run-spark-analytics),
[Detailed Spark requirements](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#detailed-spark-requirements),
and D08 in the same course README. `evidence/6i/course-source.json` records the
retrieved content hash/section line ranges; full relevant sections were read.
Plan SHA-256 `6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096`.

Evidence key (paths are repository-relative unless marked FG/6I):

- **README:** `modules/spark/README.md` (per-job sections).
- **C/M:** `modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase6CJobsSpec.scala`
  and `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentPhase6CGraphSpec.scala`.
- **D/E:** `modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase6DEJobsSpec.scala`
  and `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentPhase6DEGraphSpec.scala`.
- **F/I:** `modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase6FGJobsSpec.scala`
  and `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentPhase6FGSpec.scala`.
- **P:** `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentPhase6PipelineSpec.scala`.
- **Safety:** `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentPhase6SafetySpec.scala`.
- **Core:** `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/`,
  `modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/SparkAnalyticsContractSpec.scala`,
  `modules/core/src/test/resources/wire/spark-*.json` and
  `modules/core/src/main/resources/scholarchain.spark-analytics-config.v1.json`.
- **FG:** `docs/agent-runs/phase-06/evidence/6fg/`; **6I:** `docs/agent-runs/phase-06/evidence/6i/`.
  Historical targeted/full gates are retained in their subphase directories;
  the fresh 6I gate runs all current Scala suites together. Dataset Python 12/12
  is historical and separate from sbt totals.

| ID | Requirement | Current status | Evidence path(s) / key | Limits / later gate |
| --- | --- | --- | --- | --- |
| J1 | Canonical identities, works, authorship, venue/institution/topic nodes; accepted ER links; abstentions; endpoint checks | EVIDENCED LOCALLY | C/M/F tests; FG Hadoop/ER bindings, metadata and counters | DBLP exact-name identities; observed ORCIDs do not prove resolved identity; yearless Neptune mapping remains open. |
| J2 | Temporal undirected weighted edges; self/duplicate handling; years and complete work support; windows | EVIDENCED LOCALLY | C/M literal 18-edge G1 assertions; FG metadata/counters | Authoritative DBLP observation only; source exclusions and yearless policy are counted. |
| J3 | Per-window P, C, T, A, M, W and maximum-team evidence | EVIDENCED LOCALLY | D/E G1–G4 expectations; FG analytics-report.json and local-run-metadata.json | Metrics are separate; solo publications included. No opaque combined score. |
| J4 | Components, membership, sizes, largest fraction and singletons | EVIDENCED LOCALLY | D/E hand fixtures; FG real-data-report.md and analytics-report.json | Minimum-label DataFrame iteration; hard non-convergence guard. |
| J5 | Selected-pair shortest paths, bounded evidence and scalable distance estimate | EVIDENCED LOCALLY | D/E predecessor/path cases; F/I chain mean 4/3 and P90 2; FG real-data-report.md | K=20, maxHops=6, S=32, seed 441. Sampled largest-component distances, not exact diameter; approximate P90 has latent partition dependence. |
| J6 | Documented community method, memberships/sizes and cross-community edges | EVIDENCED LOCALLY WITH NON-CONVERGENCE | D oscillating-pair core parse/validation; E traced LPA; FG analytics-report.json | Synchronous LPA; all observed real windows stopped at 20 without convergence. Per-component causes unmeasured (F9). |
| J7 | Defined bridge measures, communities connected and limitations | EVIDENCED LOCALLY | D/E exact G1 injected partition and star; README Job7; FG distributions | Cross-community degree/weight, connected-community count, unweighted participation; no betweenness/articulation claim. |
| J8 | Coreness/dense-subgraph measure on hand-checkable graphs | EVIDENCED LOCALLY | D/E G1, star, K4, path and singleton; FG coreness distributions | DataFrame h-index iteration, coreness <= degree; duplicated export noted in F7. |
| J9 | Window recomputation; coauthor/team/component/community/bridge changes; compatible inclusion rules | EVIDENCED LOCALLY | F/I temporal tests; FG temporal table metadata and real-data-report.md | Only adjacent comparison windows have deltas; entry/exit use flags/absent deltas; tie winner is not exposed (F6). |
| J10 | Source-grounded researcher/community/path/paper context for later embeddings | EVIDENCED LOCALLY; LIMITS OPEN | F/I source/number/length/reference tests; core summary contracts; FG metadata | Deterministic templates < 1,200 characters; no live model. Thin context and unmarked title truncation are deferred F5. |
| J11 | Partitioned Parquet graph/analytics/path/summary outputs; four target load manifests | EVIDENCED LOCALLY; STORAGE PROPOSALS | F/I all-table export/reread tests; FG manifest-file-audit.json, load-manifest-*.json | 28 datasets. Neptune/DynamoDB/S3 Vectors/S3 are proposals, not loaded services. Key validation F8 due Phase 7. |
| O1 | Partition/shuffle boundaries and physical strategies | DOCUMENTED + MEASURED LOCALLY | README per-job sections; FG event-log-summary.json; FG repair-1/stage-dag.json | Physical timings/plans and part names are excluded from logical identity. |
| O2 | Keep graph-sized transformations distributed; bounded driver actions | EVIDENCED LOCALLY | Safety source fence; BoundedActions.scala; fresh 6I full gate | Textual fence has disclosed gaps; no proof for every possible syntax. No RDD/GraphX/GraphFrames/implicits rule changes. |
| O3 | Iterative persistence/checkpoints | DOCUMENTED + EXERCISED LOCALLY | README Jobs4–8; D/E/F multiwindow/long-chain regressions; FG diagnosis | Checkpoint interval 5; selected-path metadata has its own per-hop checkpoint. Caller-session optimizer setting/cost is deferred F10. |
| O4 | Counts, rejects and invariant failures | EVIDENCED LOCALLY | F hard-failure persistence test; C orphan flag cases; FG local-counters.json and real-data-report.md | 25 non-hard ORCID warnings ; 0 hard failures/reader rejects in successful real run. Historical failure has no marker. |
| O5 | Run-manifest reproducibility and input/provenance binding | EVIDENCED LOCALLY; SCOPED REPLAY | FG manifests/metadata; replay-comparison.json; 6I retained-evidence-check.json | Compiled Spark/core code fingerprint; logical config omits roots/shuffle. Metadata-only reuse; identical local build artifacts only. |
| R1 | Stage DAGs | EVIDENCED FROM RETAINED LOG | FG repair-1/stage-dag.json and stage-dag.md; real-data-report.md | 5,667 stage IDs,4,532 parent edges; diagram is a subgraph. Production summarizer still omits names/parents. |
| R2 | Partitions and shuffle metrics | EVIDENCED FROM RETAINED RUN | FG event-log-summary.json; repair-1/stage-dag.json | 2,004 executed attempts,5,237 tasks,0 failed; 12,020,965,863 read bytes/10,107,558,658 write bytes. Not new 6I measurements. |
| R3 | Graph, component and community counts | EVIDENCED FROM RETAINED RUN | FG real-data-report.md, analytics-report.json, local-run-metadata.json | Windowed row totals are not unique researchers across time; LPA partitions are iteration-limited. |
| R4 | Metric distributions | EVIDENCED WITH REPLAY DIFFERENCES | FG analytics-report.json; repair-1/analytics-report-comparison.json | First-run distributions;12 changed numeric fields (11 means/1 percentile). No identical-report claim. |
| R5 | Path-test results and estimates | EVIDENCED LOCALLY | D/E/F/I fixture tests; FG real-data-report.md | Real selected pairs: 72 found / 48 exceeded maxHops; no real benchmark query pairs. Fixture evidence covers no-path. |
| R6 | Explicit temporal windows | EVIDENCED LOCALLY | core config; FG local-run-metadata.json and real-data-report.md | all-years,through-2009,2010-2014,2015-2019,2020-2026,since-2015; cumulative window excluded from adjacent deltas. |
| R7 | Rejected integrity violations | EVIDENCED LOCALLY | FG local-counters.json, real-data-report.md; F failure-path test | Successful run:25 warnings,0 hard violations,0 input rejects; ER abstentions/conflicts are counted separately. |
| R8 | Output locations | RETAINED LOCAL PATHS | FG metadata/manifests and real-data-report.md | target/phase6-runs/6fg-spark-{first,replay}-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49; outputs ignored, not copied into git. |
| T1 | Fresh sbt check | SEE FINAL 6I GATE BELOW | 6I final-check.txt and final-gate-metadata.json | JDK 17 full definition of done; no change to implementation or expected test count. |
| T2 | Local/small-cluster Spark integration | EVIDENCED LOCALLY | P tiny unchanged Hadoop→offlineER→Spark pipeline; F/I exports; FG real-data-report.md | Local[2] execution and bounded real dataset, not an EMR or multi-machine measurement. |
| T3 | Bounded EMR Spark run | **OPEN — deferred to Phase 15 by user decision** | plan schedule change; 6A emr-compatibility.md; this register | EMR script Phase 13, live run Phase 15 under human budget/deployment approval. No cloud runtime tested. Human must explicitly accept this open gate. |
| G1 | Real distributed Spark transformations/analytics | EVIDENCED LOCALLY | C/DE/FG jobs; full pipeline tests; FG plans/stage DAG | Distributed DataFrame operators in local Spark; no claim of cluster execution. |
| G2 | No full-graph driver collection | EVIDENCED WITH TEXTUAL GUARD LIMITS | Safety tests/source fence; BoundedActions.scala; fresh gate | Source guard plus reviewed code; scanner blind spots carried forward. |
| G3 | Known-graph distinct degree and pair weights | EVIDENCED LOCALLY | C/M full literal G1 edge table; E G1 metric table | Module and independent C edges asserted; G1–G4 DE exact expectations belong to independent E suite, not all module fixtures. |
| G4 | Hand-checkable components/community/path/coreness | EVIDENCED LOCALLY | D/E fixtures, F/I chain and temporal cases; core parse checks | Traced LPA, explicit oscillation, BFS predecessor tie and max-hop checks; no all-pairs driver algorithm. |
| G5 | Bridge definitions and limitations | DOCUMENTED + TESTED | README Job7; D/E injected partitions/star; real-data-report.md | Community-dependent indicators; optional sampled betweenness intentionally omitted by user. |
| G6 | Time windows visible in outputs | EVIDENCED LOCALLY | core SparkRecordContext/contracts; F/I record parsing; FG metadata | Window labels/bounds bound in Spark edge IDs; old frozen ID formulas unchanged. |
| G7 | Partition/shuffle behavior documented | DOCUMENTED + RETAINED MEASUREMENTS | README Jobs1–11; FG plans/event summary; stage DAG | Review complete detailed job matrix below; retain limits instead of claiming unmeasured optimizer cost. |
| G8 | Code review returns APPROVE | **PENDING — comprehensive whole-Phase-6 review** | review.md; 6I reviewer-prompt.md | 6A–6FG approvals are retained; they do not substitute for final review of0349388 through current tree including untracked files. |
| D01 | Per-job inputs/schema versions | DOCUMENTED; FINAL REVIEW PENDING | README Shared rules and each Job1–11; core wire/schemas | Hadoop/ER outputs consumed; no independent raw reparse by Spark. |
| D02 | Per-job outputs/schema versions | DOCUMENTED; CONTRACT TESTS | README table and Jobs1–11; SparkAnalyticsContracts.scala; F/I parsing | Domain GraphNode/GraphEdge versus analytics v1 and explicit work_sources projection distinguished. |
| D03 | Per-job selected windows/snapshot | DOCUMENTED + PERSISTED | README Shared rules/Jobs1–11; FG manifests | Identity once, analytics by configured windows; each output carries core provenance/context. |
| D04 | Per-job partition columns | DOCUMENTED + EXPORTED | README Jobs1–11/Job11; FG load manifests and metadata | Layout is local analogue of recommended S3 layout; no S3 upload claim. |
| D05 | Repartition/coalesce choices | DOCUMENTED; PLAN EVIDENCE | README Jobs1–11; saved FG plans via output roots | Hash partition and sorted writes; no global one-partition export. |
| D06 | Join strategies | DOCUMENTED; PLAN EVIDENCE | README Jobs1–11; C/DE/FG DataFrame jobs; FG saved plans | Iterative joins remain distributed; physical plan rendering is capped and can truncate. |
| D07 | Broadcast assumptions | DOCUMENTED | README Shared rules and Jobs1–11; FG plans | Small config/window relations versus graph-sized data; final reviewer checks documentation against code. |
| D08 | Cache/persistence choices | DOCUMENTED + EXERCISED | README Jobs1–11; DE label-state ordering and regression tests | Eager materialization/cache ordering reviewed in 6FG; no new 6I performance measurement. |
| D09 | Checkpoint choices | DOCUMENTED + EXERCISED | README Jobs1–11; D/F long-chain tests; FG diagnosis | Explicit temp/test paths, configured production path/interval; hard failures retain evidence before abort. |
| D10 | Expected shuffle boundaries | DOCUMENTED + MEASURED | README Jobs1–11; FG event summary/stage DAG | Task shuffle totals retained; not a global scalability proof. |
| D11 | Driver memory assumptions | DOCUMENTED; BOUNDED RUN | README Shared rules/Jobs1–11; BoundedActions; FG commands.md | Tests 2 GiB, real CLI 4 GiB; 256 shard summaries bounded on driver; executor shard buffering remains scale limit. |
| D12 | Per-job invariants/counters | DOCUMENTED + TESTED | README Jobs1–11; C/DE/FG tests; FG local-counters.json | Counter aliases remain F12; rejected input/failure rows are distinct from normal tables. |
| D13 | Recommended graph/output layout | LOCAL ANALOGUE EVIDENCED | README Job11; FG metadata, four load manifests, manifest-file-audit.json | 28 tables; empty datasets keep schema; no live Neptune/DynamoDB/Vector/S3 loading. |
| D14 | A graph hand-checkable across all required measures | EVIDENCED LOCALLY | E literal G1–G4 values, C/M exact G1 edges; D/F/I smaller fixtures | Independent hand expectations are not implementation-derived replay assertions. |
| D08-package | Spark deliverable: builder, analytics, tests, schemas, bounded results | LOCAL DELIVERABLE EVIDENCED; CLOUD OPEN | modules/spark/**; core contracts/wire examples; tests/**; FG results; 6A package evidence | Historical6A job JAR inspection is not fresh 6I packaging or release/EMR verification. JDK packaging guard remains open. |
| S1 | Spark grading: actual analytics; graph not centralized | LOCAL EVIDENCE; NO GRADING CLAIM | C/DE/FG jobs; C/D/E/F/I tests; Safety; FG run/DAG | Coordinator cannot award course points or infer instructor acceptance of workflow/EMR deviations. |
| H1 | Human acceptance and accepted commit evidence | **PENDING — human-owned** | human-gate.md and commit.txt (absent at preflight) | Human writes after comprehensive APPROVE, including EMR deferral/limits; coordinator never authors these files. |

### Limits that remain part of the final handoff

The authoritative carry-forward table is the **Subphase 6I** section of
`repairs.md`. F4–F12 remain open/deferred by the user's blocking-only scope.
This includes incomplete-output retry, summary richness/truncation, continuity
observability, duplicate datasets, unvalidated store keys, causal wording,
caller-session optimizer setting and unmeasured cost, retention, and the separate
Python gate. New scanner blind spots remain nonblocking. The fixed empty handoff
path is already committed. No optional production fix, cleanup or new run is
claimed in 6I.

Observed replay equality covers 28 logical tables and counters from identical local
compiled artifacts at 4 versus 2 shuffle partitions. The analytics report differs
in 12 numeric fields, and sampled-estimate P90 is not proven partition invariant.
Metadata-only reuse does not rehash existing Parquet. Fixed 256-shard executor
buffering is validated at this bounded slice only. All real windows reported
LPA non-convergence; isolated pairs oscillate, but the full real change counts
have no per-component causal attribution. No cloud/store compatibility claim is
made. Bounded EMR remains **OPEN — deferred to Phase 15 by user decision**.

Comprehensive whole-phase APPROVE and the human's `human-gate.md`/`commit.txt`
remain pending. This evidence-only close-out does not close Phase 6 by itself.

## Subphase 6I — final close-out evidence packet

STATUS: COMPLETE for coordinator evidence and fresh local validation. Comprehensive
whole-Phase-6 review, human acceptance and final commit records remain pending;
Phase 6 is **not yet closed**.

OWNER: Coordinator; only `docs/agent-runs/phase-06/**` evidence. No specialist
writer or reviewer launched. Human-owned decisions remain untouched/absent.

WORK ORDER: User: "All right, let's go to the last phase 6i." Plan Section 9/6I;
Step 0 **No questions for this subphase** because no open 6I implementation choice
remains. Existing EMR deferral and F4–F12 blocking-only scope persist. Clean
preflight on `phase-6`, previous 6FG commit/base/current HEAD `d1afc7f6698965ddbe010621b277b10e655d25ff`.
Comprehensive review baseline `03493882399e9020e6892c9f97e0ec8919365215`.

FILES CREATED: `evidence/6i/` preflight, scoped source snapshot, course-source
provenance, full gate/execution metadata, retained-sidecar audit, diff diagnostic,
command log, changed/whole-phase inventories, handoff and reviewer prompt.
FILES MODIFIED: `prompt.md`, `owner-report.md`, `test-report.md`, `review.md`,
`repairs.md`. No source/build/dataset/test changes. Exact final inventories:
`evidence/6i/changed-files.txt` and `whole-phase-files.txt`.

COMMANDS RUN: Plan's JDK 17 JAVA_HOME/PATH and Phase 4 SBT_OPTS, `java -version`,
`/usr/bin/time -p sbt -batch check` (exit 0); exact command/environment and audit
scope in `evidence/6i/commands.md`. Git branch/HEAD/status/diff reads; SHA/JSON
sidecar audit; official course README read in full relevant sections.
`git diff --check`: exit 0. Whole-phase non-evidence diff check: exit 0.
Whole-phase diff including historical raw logs: exit 2 for retained trailing
whitespace, diagnostic preserved in `diff-check.txt`. No historical logs were
changed. Initial metadata assembly asserted cumulative whitespace cleanliness;
its audit assertion stopped and was corrected to record this historical result,
without a gate/source/log change. No rerun substituted for the passing full gate.

TEST RESULTS: **554 passed / 0 failed**. Core 144, Hadoop 64, ER 39, Spark 34,
independent 266, build 7 (144/64/39/34/266/7). Java 17.0.20.1, sbt 1.10.7; sbt
673s, real **675.13s**. Full unfiltered `evidence/6i/final-check.txt`:
**1,359,860 bytes**, SHA-256 **`e2bf289d11f6f2e4ff8e714d3fc4b9b56b16ea7ed59007abd00d5fe73d9d7367`**. Completed
`2026-10-22T20:04:05.397751+00:00`. Line references and generated test-marker mtime are in
`final-gate-metadata.json`. Expected injected build self-test error is not a gate
failure. No separate dataset Python or real-data CLI run was performed in 6I.

VALIDATION RESULTS: All 68 scoped Phase 6 implementation/config/build/dataset
hashes **and mtimes** unchanged across gate. All 27 prior approved 6FG snapshot
hashes still match. HEAD/plan unchanged; human-owned files remain absent as at
preflight. `retained-evidence-check.json` revalidates both published completion
markers and retained manifest/metadata bytes, 28 recorded table hash pairs and
counter-array equality, and both analytics-report hashes/all 12 differing paths.
This is metadata consistency, not a new full Parquet reread. The 52-row table
above maps jobs 1–11, every course operational/report/gate bullet, Detailed Spark
job documentation items, layout and D08. External 6FG approval remains verbatim;
F1–F3 are closed by that reviewer and F4–F12 explicitly stay deferred.

ASSUMPTIONS: Prior bounded real runs and dataset Python 12/12 remain historical
observations, not new 6I executions. Retained code fingerprint comparison is of
metadata, not a recomputation of the compiled fingerprint. Codex native tools;
observable model identity GPT-6; exact deployed model/tool build unavailable.
No hidden reasoning, secrets or full datasets stored in evidence.

RISKS: F4–F12 and new scanner gaps remain as listed in the 6I repairs register.
Reuse authenticates metadata only; fixed 256-shard memory measured at bounded
scale; report means/approximate percentiles and latent distance-P90 partition
risk disclosed. LPA non-convergence is measured, per-component causes are not.
Store mappings/yearless Neptune rows are proposals requiring Phase 7 validation.
Release JDK packaging guard, updated wrong-JDK evidence and exact Scala runtime
compatibility remain open. **Bounded EMR Spark run: OPEN — deferred to Phase 15
by user decision** (script Phase 13). A local pass is not EMR/course acceptance.
Historical raw-log whitespace is preserved; no evidence-retention decision is
inferred from prior blocking-only scope.

MANUAL ACTION REQUIRED: User launches the comprehensive independent read-only
review with `evidence/6i/reviewer-prompt.md`. After APPROVE and any required
repairs, the human writes `human-gate.md` with explicit EMR deferral and known
limits, commits accepted close-out artifacts, and records accepted commit in
human-owned `commit.txt` (repository generic accepted-commit convention may also
be used by the human). No coordinator-authored acceptance/commit SHA.

BLOCKED-ON OWNER: None for this evidence packet; comprehensive review and final
acceptance belong to the independent reviewer/user.
BLOCKED-ON EVIDENCE: No comprehensive whole-phase APPROVE or human close-out
record yet; live EMR evidence deferred to Phase 15.
NEXT GATE: User-run whole-Phase-6 review, then human acceptance/commit evidence.
Stop 6I; no Phase 7, reviewer launch, commit or push.

## Subphase 6I — comprehensive approval received (2026-10-22)

The independent user-launched whole-phase reviewer returned **APPROVE for 6I
and the comprehensive Phase 6 local implementation**, with no blocking defect.
The complete review is preserved verbatim in `review.md`; N1–N7 are OPEN and
nonblocking in `repairs.md`. This dated disposition supersedes earlier
pending-comprehensive-review wording and traceability G8. **Human close-out is
still PENDING**, as are the explicit EMR and later gates; no whole-phase human
acceptance, compatible cloud runtime or instructor approval is inferred.

**N3 real-data coverage clarification:** the real ER export has **zero Researcher
decisions of every outcome**; Work accepted **1**, conflict **12,123**, unresolved
**1,627**. The real counters `crossDblpNameLinksNotApplied`,
`constraintBlockedWorkGroups`, `selfPairsDropped`, `duplicateTeamMembersCollapsed`
and `nonAuthoritativeDblpObservationsDropped` are each **0**. Identity-merge and
constraint branches are evidenced by fixtures and the tiny pipeline, not by real
Researcher linking in this slice. This qualification applies to traceability
J1/J2; N3 remains open for the requested real-data report/J1 edits.

No builds, tests, Spark runs, implementation changes, retained-log edits, human
file edits, reviewer launch or commits were performed for this disposition-only
update. The existing fresh **554 passed / 0 failed** gate remains applicable.
Next action belongs to the human: acceptance record including EMR/workflow/
retention/open findings, accepted-artifact commit, then commit SHA record. Phase 7
starts only on a separate user prompt.

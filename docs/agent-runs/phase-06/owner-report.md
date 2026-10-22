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

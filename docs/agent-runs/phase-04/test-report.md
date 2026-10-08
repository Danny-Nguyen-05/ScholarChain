# Phase 4 test report

Current evidence is in “Final gate after cached-core repair — 2026-10-07” below: 220 tests pass, every current core entry matches the dependency/submit bundle, and two fresh samples compare equivalent. Earlier 218-pass/stale-package and interrupted attempts are historical.

STATUS: COMPLETE — final current gate passes 220 tests, exact packaging content verification and two fresh sample equivalence.

OWNER: Phase 4 orchestrator. Commands below were run in this session unless noted as an owner observation.

WORK ORDER: `docs/agent-runs/phase-04/prompt.md`

## Toolchain

- Java: Homebrew OpenJDK 17.0.20.1 (`JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`)
- sbt: 1.10.7
- Scala: 3.3.4 (`project/Versions.scala`)
- Hadoop client: 3.3.6, `Provided`
- `shellcheck`: not installed

## Final repository gate

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
sbt -batch check
```

Exit 0. Completed 2026-10-06 15:30:34 local. Total time 111 seconds. Log `/tmp/scholarchain-check3.log`.

- 93 tests passed, 0 failed
- Hadoop module: 15 passed, 0 failed
- Independent tests: 19 passed, 0 failed
- Build verification: 2 passed, 0 failed

The log contains `scholarchain check probe: injected format-stage failure`. That is the existing check-failure probe. The parent test passed and the command exited 0.

## Dataset inputs

```bash
/tmp/scholarchain-datasets-venv/bin/python datasets/scripts/validate_datasets.py
python3 -m unittest datasets/scripts/test_acquire_bounds.py
cd datasets && shasum -a 256 -c samples/SHA256SUMS
```

`validate_datasets.py` printed `OK: manifest (4 datasets), samples, and script bounds validated` after installing `PyYAML==6.0.2` into `/tmp/scholarchain-datasets-venv`. The default `python3` lacked PyYAML and exited 1 before that venv was used. Unittest: 6 tests, OK. Checksums: all four sample files OK. Samples were not modified.

## Final two-run pipeline

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
sbt -batch "hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"
```

Exit 0 after the join repair. `logicalRecordsEqual=true`. Both runs: INPUT 123, ACCEPTED 135, REJECTED 1, DUPLICATE 1, CONFLICT 0, OVERSIZE_BLOCK 0, OVERSIZE_TEAM 0, EMITTED_PAIR 11, MISSING_KEY 0, SCHEMA_FAILURE 0. Largest team 2. Largest coauthor pair expansion 1. Largest block 4. J05 `largestBlockPairs=6`.

Directories:

- `target/phase4-runs/9059f9e5-fe1c-4b68-8223-6ed5d4bde7cd`
- `target/phase4-runs/25aed095-7157-42f4-90be-1c7549c9b2bd`

Earlier runs that reported INPUT 81 were before the join repair and are not the final comparison.

## EMR script

`bash -n scripts/phase4-emr-smoke.sh` exit 0, observed by `infra-engineer`. A dummy dry-run exited 0 and included `--output-root`. A missing `--output-prefix` exited 1. No EMR step was submitted. AWS execution is unverified.

## Failed gate attempts

- `sbt check` failed on unformatted `IndependentDblpJsonSpec.scala`, then on `OrcidActivityRecord.doi`, then on two independent assertions (shared DOI work ids compared with `!=`, and a split test that assigned `PosStream.pos` without skipping bytes). Each was repaired by `test-engineer`.
- `hadoop/test` failed during the repair passes and the final owner run of that suite was exit 0 with 15 tests.
- The first `hadoopRunMain` attempt exited from sbt while the main threw `NoClassDefFoundError` for Hadoop `Configuration`. The foreground `fgRunMain` repair then completed a `--once` run with exit 0.

FILES CREATED: none by this report. Evidence files are the logs named above and `docs/agent-runs/phase-04/`.

FILES MODIFIED: this report.

COMMANDS RUN: the three gates in this file.

TEST RESULTS: as counted above.

VALIDATION RESULTS: two logical runs equal; four sample checksums match; manifest validation OK.

ASSUMPTIONS: The 93-test count is the first suite total printed by `sbt check` before the Hadoop, independent, and build-verification totals.

RISKS: `shellcheck` and AWS were not run.

MANUAL ACTION REQUIRED: Human acceptance.

BLOCKED-ON OWNER: none

NEXT GATE: Human review. Do not begin Phase 5.

## Repair gate, 2026-10-07

The independent review's repairs were rechecked by the orchestrator. `shellcheck` is still not installed. No EMR step was submitted.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export SBT_OPTS="-Dlogback.configurationFile=/tmp/scholarchain-logback-warn.xml"
sbt -batch check
```

Exit 0 at 2026-10-07 10:05:28 local. Total time 285 seconds. Java 17.0.20.1, sbt 1.10.7. Counts: core 96 passed, Hadoop 28 passed, independent 20 passed, build-verification 2 passed. The log contains `scholarchain check probe: injected format-stage failure`; that is the expected nested probe, and its parent test passed.

```bash
sbt -batch "hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"
```

Exit 0 at 2026-10-07 09:58:39 local. Total time 21 seconds. Two fresh runs, both `reused=false`, `logicalRecordsEqual=true`. Counters on both: INPUT 193, ACCEPTED 239, REJECTED 0, DUPLICATE 0, CONFLICT 0, EMITTED_PAIR 45. Directories: `target/phase4-runs/a9835bef-fbe4-448f-b5b7-da005025cadd` and `target/phase4-runs/0fff2513-640b-4b46-ac04-3b854ce45071`.

```bash
cd datasets && shasum -a 256 -c samples/SHA256SUMS
```

Exit 0. All four samples OK.

```bash
sbt -batch hadoopDependencyBundle
```

Exit 0 after the core-jar merge. Verification logged the bundle path `modules/hadoop/target/scala-3.3.4/hadoop-dependency-bundle_3-0.1.0-SNAPSHOT.jar`. A `jar tf` count after that was core 468, Hadoop module 0, `org/apache/hadoop` 0, upickle/ujson 453, scala 3549.

`scripts/phase4-emr-smoke.sh --dry-run` with placeholder S3 URIs exited 0. The step args include `-libjars`, `--execution-mode cluster`, and the four acquisition snapshot ids. No step was submitted.

Earlier failed attempts in this repair pass are listed in `repairs.md`. They are not the final result.


## Four XML repair gate — 2026-10-07

STATUS: COMPLETE — fresh local gate passed; independent review APPROVE. Human acceptance remains pending.

OWNER: Coordinator, executing gates sequentially and assembling owner results; `/root/test_engineer` owns independent tests.

WORK ORDER: Cover all four XML findings in `review.md:347` and rerun the repository definition of done.

FILES CREATED: `IndependentDblpXmlRepairSpec.scala` (17 independent cases), `DblpXmlRegressionSpec.scala` (4 module cases), and retained evidence files named below.

FILES MODIFIED: This report and owner-provided test fixtures after observed failures. Gate-triggered formatting stayed in the changed Hadoop/test source trees.

COMMANDS RUN:

```sh
# Hadoop owner: initial sandbox attempt, exit 1 before build startup.
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home sbt 'hadoop/scalafmt' 'hadoop/Test/scalafmt' 'hadoop/test'

# Coordinator: first allowed targeted run, exit 1 (two module fixture assertions failed).
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home sbt -batch 'hadoop/Compile/scalafmt' 'hadoop/Test/scalafmt' 'independentTests/Test/scalafmt' 'hadoop/testOnly *DblpXmlRegressionSpec' 'independentTests/testOnly *IndependentDblpXmlRepairSpec' > docs/agent-runs/phase-04/xml-repair-targeted-tests.txt 2>&1

# Coordinator: corrected targeted run, exit 0.
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/tmp/scholarchain-logback-warn.xml sbt -batch 'hadoop/Test/scalafmt' 'independentTests/Test/scalafmt' 'hadoop/testOnly *DblpXmlRegressionSpec' 'independentTests/testOnly *IndependentDblpXmlRepairSpec' > docs/agent-runs/phase-04/xml-repair-targeted-tests-final.txt 2>&1

# Coordinator: final sequential repository, packaging and two-run gates, exit 0.
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/tmp/scholarchain-logback-warn.xml sbt -batch check hadoopSubmitJar 'hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain' > docs/agent-runs/phase-04/xml-repair-full-gate.txt 2>&1

bash -n scripts/phase4-emr-smoke.sh
bash scripts/phase4-emr-smoke.sh --dry-run --cluster-id j-PHASE4-PLACEHOLDER --region us-east-1 --input-prefix s3://phase4-placeholder/input --output-prefix s3://phase4-placeholder/output --jar s3://phase4-placeholder/artifacts/hadoop-submit_3-0.1.0-SNAPSHOT.jar --libjars s3://phase4-placeholder/artifacts/hadoop-dependency-bundle_3-0.1.0-SNAPSHOT.jar --config s3://phase4-placeholder/artifacts/prep.json > docs/agent-runs/phase-04/xml-repair-emr-dry-run.txt 2>&1
# Working directory: datasets/
shasum -a 256 -c samples/SHA256SUMS
# Working directory: repository root
git diff --check
```

The logging XML was copied from `/tmp/scholarchain-logback-warn.xml` into `xml-repair-logback.xml`; for replay restore it with `cp docs/agent-runs/phase-04/xml-repair-logback.xml /tmp/scholarchain-logback-warn.xml` or omit the logging property. Toolchain: Java 17.0.20.1, sbt 1.10.7, Scala 3.3.4, Hadoop 3.3.6 Provided.

TEST RESULTS:

- Targeted final: 4 module + 17 independent tests, all passed, completed 15:17:44 America/Chicago.
- Full gate: core 96, Hadoop 46, independent 41, build verification 2 = **185 passed**, zero failed. `sbt check` completed 15:22:42, 287 seconds. The existing injected format-stage failure is an expected nested probe; its parent passed.
- Generated marker: `success=true`, timestamp `1791404562667`.
- Opening-name tests exercise `nextOpen`, actual InputFormat, `SampleBound.install`, true byte counts, diagnostics, and the next valid record. CDATA cases cover bare ampersands, reference-shaped literals, adjacent active references, author text, and combined bounds. Identifier cases cover single quotes, valid closing whitespace, retained ORCID, and invalid ORCID rejection. Closing-tag cases cover unmatched, mismatched, crossed, extra-name/attribute, slash, doubled-slash, empty-name syntax, direct parse, and actual job rejects.

Failed attempts are retained rather than counted as passes. The sandbox sbt attempt failed on `~/.sbt/boot/sbt.boot.lock`, retained in `xml-repair-sandbox-attempt.txt`. The Hadoop owner's escalated retry returned “aborted by user after 534.2s” when the coordinator interrupted the stalled call; no session ID or redirected output file was produced. The coordinator then ran an allowed command. First executable targeted run: 2 of 4 module tests failed because byte counts are encoded as JSON strings and the short expansion bound reached a long key before CDATA. Owners corrected fixture assertions and shortened only synthetic keys. A read-only precheck also caught a standalone-AuthorMention assertion against a direct Work return; test owner corrected it to `work.authors`. Final feature expectations remained unchanged.

VALIDATION RESULTS:

- `hadoopSubmitJar`: verified non-Hadoop dependency bundle and submit JAR with its lib entry; completed 15:22:43, 1 second. Reviewer also inspected nested byte equality, catalogue/main class/runtime dependencies, and absence of Hadoop classes.
- Standalone `HadoopPrepMain`: completed 15:23:04, 21 seconds; two fresh runs, both `reused=false`, `logicalRecordsEqual=true`. Both runs have 9 job `_SUCCESS` outputs and complete markers. Counter summaries, complete manifests, actual representative records, and statistics are retained in `xml-repair-sample-evidence.json`.
- Per run: INPUT 193, ACCEPTED 239, REJECTED 0, DUPLICATE 0, CONFLICT 0, OVERSIZE_BLOCK 0, OVERSIZE_TEAM 0, EMITTED_PAIR 45, MISSING_KEY 0, SCHEMA_FAILURE 0. Largest team 2, pair expansion 1, block 4; J05 largestBlockPairs 6.
- EMR script syntax and placeholder dry-run exit 0, no hadoop/AWS invocation. Dry-run output retained in `xml-repair-emr-dry-run.txt`.
- Four sample SHA-256 checks OK; sample bytes unchanged. `git diff --check` exit 0.

ASSUMPTIONS: Synthetic adversarial fixtures and local job execution authorized. Counts are tests, not cloud compatibility evidence.

RISKS: AWS and shellcheck unrun; scoped tests/review are not exhaustive XML verification.

MANUAL ACTION REQUIRED: Human architect reviews the complete Phase 4 diff and records acceptance.

BLOCKED-ON OWNER: None for the routed repairs.

BLOCKED-ON EVIDENCE: No remaining implementation blocker in final independent review.

NEXT GATE: Human Phase 4 acceptance; do not begin Phase 5.


## Seven-blocker repair recheck — 2026-10-07

STATUS: COMPLETE — evidence inspection and packaging/script checks complete; review REQUEST-CHANGES.

OWNER: Coordinator assembling fresh read-only `/root/phase4_seven_blocker_reviewer` report.

WORK ORDER: User requested another check of the latest Phase 4 tree.

FILES CREATED: `seven-blocker-recheck-test-summary.txt`, `seven-blocker-recheck-sample.txt`, `seven-blocker-recheck-evidence.json`, `seven-blocker-recheck-packaging.txt`, `seven-blocker-recheck-emr-dry-run.txt`.

FILES MODIFIED: Coordinator reports only; no production/test source edits.

COMMANDS RUN: Exact newly executed packaging/syntax/dry-run commands and read-only inspection provenance are in the matching latest review section. No test/sample execution during this recheck. Packaging used an approved cache-access escalation.

TEST RESULTS: Existing `/tmp/scholarchain-check10.log` ends successfully at 18:14:23, 340 seconds; current JUnit 97 core + 55 Hadoop + 48 independent + 2 build verification = 202 passed, zero failures/errors/skips. Marker success=true, timestamp 1791414863422. Compact status/test stdout and JUnit/report hashes retained in the files above. Original shell environment and process exit value were not observed in this turn.

VALIDATION RESULTS: Existing `/tmp/scholarchain-sample10.log` ends successfully at 18:14:58, 21 seconds; runs e9fd8b3b-2af3-4b65-909a-be0c8e4dee6b and 335c5a33-489b-4056-8ece-b3d8863eaef9 both reused=false, logicalRecordsEqual=true, complete, 9 success outputs each. Both INPUT 195, ACCEPTED 242, REJECTED 0, EMITTED_PAIR 45; actual manifests/counters/export counts retained in evidence JSON. New packaging exit 0 at 20:54:57; script syntax/dry-run exit 0. Reviewer inspected current archive and embedded smoke ceilings. 91 source/contract fingerprints unchanged during review; sources precede current gate marker; git diff --check exit0.

ASSUMPTIONS: Existing generated evidence applies to unchanged current sources; local execution authorized.

RISKS: Two static categories remain uncovered: overflow reject lineage and discarded OpenAlex DOI disagreement/DBLP electronic-edition links. No AWS actions; no exhaustive correctness claim.

MANUAL ACTION REQUIRED: Owner repairs, independent feature tests, relevant verification, fresh review.

BLOCKED-ON OWNER: hadoop-engineer; supporting domain-engineer/test-engineer.

BLOCKED-ON EVIDENCE: Latest review findings 1–2.

NEXT GATE: Repairs and verification, independent review, then human acceptance.


## Two evidence-preservation repairs — 2026-10-07

STATUS: IN PROGRESS.
OWNER: Coordinator executes all sbt commands sequentially. Module source tests by implementation owner; independent tests by separate test-engineer.
WORK ORDER: Verify the latest two blocker repairs against frozen current source, not historical 202-pass evidence.
FILES CREATED / MODIFIED: Source tests listed in current owner report; evidence-repair logs here.
COMMANDS RUN:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'independentTests/Test/scalafmt' 'core/testOnly edu.uic.cs441.scholarchain.core.WorkSourceEvidenceSpec' > docs/agent-runs/phase-04/evidence-repair-core-targeted.txt 2>&1
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'hadoop/Compile/scalafmt' 'hadoop/Test/scalafmt' 'hadoop/testOnly edu.uic.cs441.scholarchain.hadoop.SourceEvidenceRegressionSpec' 'independentTests/testOnly edu.uic.cs441.scholarchain.independent.IndependentPhase4EvidenceSpec' > docs/agent-runs/phase-04/evidence-repair-targeted.txt 2>&1
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch check hadoopSubmitJar 'hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain' > docs/agent-runs/phase-04/evidence-repair-full-gate.txt 2>&1
```

TEST RESULTS: Core targeted exit 0, 2 tests pass at 21:27:09 local. Hadoop targeted 5 pass at 21:31:51; independent targeted 5 pass at 21:32:13, combined command exit 0. All new tests zero failures. Full gate in progress. No sbt executed by subagents.
VALIDATION RESULTS: Dataset manifest/sample/script bound validation exit 0; acquisition unittest 6 pass; all 4 SHA256SUMS pass; bash -n EMR smoke script exit 0; placeholder remote dry-run exit 0 (evidence-repair-emr-dry-run.txt). No AWS execution.
ASSUMPTIONS: JDK17 installed, sbt1.10.7, Scala3.3.4, Hadoop3.3.6 Provided. Native sandbox escalation only for sbt cache access.
RISKS: Final gate/reviewer pending.
MANUAL ACTION REQUIRED: Human acceptance after final evidence/review.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Fresh full gate/package/sample results.
NEXT GATE: Complete sequential gate and independent verdict.


### Interrupted first full-gate attempt

The independent reviewer found that final-export unresolved-abstract-reference rejects were passed a privately framed intermediate key. This would name a partition `reject` followed by control metadata rather than `reject`. Routed to Hadoop owner for callback repair and actual J09 partition regression.

The coordinator interrupted the first full-gate command to repair before packaging/samples. `write_stdin` Ctrl-C did not end the process; exact process-pattern `pkill -INT -f 'sbt-launch.jar.*check.*hadoopSubmitJar'` returned 0. The gate then exited 1 (`Cancelled: checkTask`). A subsequent TERM attempt returned 1 because the matched process had ended. Sandbox read-only `ps` was unavailable (`operation not permitted`). All process operations used native escalation. The raw partial log is evidence-repair-interrupted-gate.txt. Core 99 tests completed successfully; two Hadoop tests report interruption exceptions caused by cancellation. This attempt is not a passing gate and is not evidence for final source. No package/sample results were produced by it.

NEXT GATE: Owner source-ready notice, focused export-partition feature test, then rerun the complete frozen-source gate/package/sample command.


### Second interrupted full-gate attempt: overflow determinism

After the final-export callback repair, SourceEvidenceRegressionSpec targeted command exited 0 at 21:37:37 local with all 6 tests passing (evidence-repair-export-targeted.txt). Exact command:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'hadoop/Compile/scalafmt' 'hadoop/Test/scalafmt' 'hadoop/testOnly edu.uic.cs441.scholarchain.hadoop.SourceEvidenceRegressionSpec' > docs/agent-runs/phase-04/evidence-repair-export-targeted.txt 2>&1
```

The same full-gate/package/two-sample command was restarted. Reviewer then identified that generated overflow sourceLocator includes a processing-run UUID (including its long-path digest), which logical comparison did not normalize. Default samples have no overflow rejects and do not exercise it. Routed stable generated-file identity and two-fresh-overflow-run regression to Hadoop owner, with independent two-run coverage to test owner.

Coordinator interrupted via exact `pkill -INT -f 'sbt-launch.jar.*check.*hadoopSubmitJar'`, exit 0, native escalation. Gate exited 1 after cancellation; raw log evidence-repair-interrupted-gate-2.txt. Core 99 and Hadoop 61 tests completed successfully before interruption; independent interruption failures are cancellation artifacts. This is not a passing final gate. Packaging and final sample executions remained unrun. Final source will be frozen and full command rerun after the determinism repair.


### Overflow determinism and exact source-value verification

COMMANDS RUN:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'hadoop/Compile/scalafmt' 'hadoop/Test/scalafmt' 'independentTests/Test/scalafmt' 'hadoop/testOnly edu.uic.cs441.scholarchain.hadoop.SourceEvidenceRegressionSpec' 'independentTests/testOnly edu.uic.cs441.scholarchain.independent.IndependentPhase4EvidenceSpec' > docs/agent-runs/phase-04/evidence-repair-determinism-targeted.txt 2>&1
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch 'hadoop/Compile/scalafmt' 'hadoop/Test/scalafmt' 'hadoop/testOnly edu.uic.cs441.scholarchain.hadoop.SourceEvidenceRegressionSpec' > docs/agent-runs/phase-04/evidence-repair-metadata-targeted.txt 2>&1
```

TEST RESULTS: Determinism targeted exit 0: module 8 tests pass at 21:49:27; independent 5 pass at 21:49:59. The real two-fresh-run valid600k-title overflow fixture now compares equivalent; independent perturbations of source, snapshot and native identifier remain unequal. Owner tests cover long path/native identifier digest bounds.

Reviewer also identified existing global scalar normalization that could erase a source value exactly equal to the invocation runId. Owner changed comparison to normalize only processing runId fields on root records/provenance/wrapped identifier entries. Exact titles, links, snapshots, source identities and unknown nested runId values remain evidence. Final metadata-targeted exit 0: all 9 module tests pass at 21:51:52.

VALIDATION RESULTS: Final source inspection has no remaining blocker; frozen complete gate/package/two sample command restarted (same exact replay command as above). No result claimed until it completes. Transformation version hadoop-prep-j01-j09-v3-stable-overflow-lineage prevents pre-companion output reuse.


## Final evidence-preservation repair gate — 2026-10-07

STATUS: COMPLETE.
OWNER: Coordinator executed all gates sequentially; module/core tests by implementation owner, independent tests by separate test-engineer.
WORK ORDER: Full frozen-source verification after both latest blockers and adjacent framing/comparison defects were repaired.
FILES CREATED: evidence-repair-full-gate.txt, evidence-repair-gate-summary.txt, evidence-repair-artifacts.json; targeted, interrupted and dry-run logs listed above.
FILES MODIFIED: Coordinator reports. Source changes listed in owner report.
COMMANDS RUN:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch check hadoopSubmitJar 'hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain' > docs/agent-runs/phase-04/evidence-repair-full-gate.txt 2>&1
```

TEST RESULTS: Command exit 0. sbt check completed 21:59:01 local in 397 seconds: core 99, Hadoop 64, independent 53, build verification 2; **218 tests passed**, zero failures/errors/skips. JUnit suite files and hashes retained in evidence-repair-artifacts.json. Expected nested checkProbeInjectFailure emitted format-stage errors; its parent failure-propagation tests passed. Marker success=true, timestamp=1791428341212. All 90 scoped source/config SHA256 values and mtimes match the final frozen gate snapshot.

VALIDATION RESULTS: hadoopSubmitJar completed 21:59:02, 1 second; verified thin module, dependency bundle and submit archive. Bundle has core 483, Scala 3549, upickle 346, ujson 107 entries; zero Hadoop-module and cluster-Hadoop entries. Exactly one embedded bundle matches external SHA256.

Two fresh default-sample runs completed 21:59:22, 21 seconds: target/phase4-runs/5713df68-5b95-4082-9077-1975681ba357 and target/phase4-runs/82bab667-6068-4f29-9921-09364f48933f. Both reused=false; logicalRecordsEqual=true; each has eight intermediate and one export _SUCCESS plus completion metadata. Counters each: INPUT195, ACCEPTED242, REJECTED0, DUPLICATE0, CONFLICT0, OVERSIZE_BLOCK0, OVERSIZE_TEAM0, EMITTED_PAIR45, MISSING_KEY0, SCHEMA_FAILURE0. Largest team2, pair expansion1, block4.

Matching export counts: works5, mentions10, teams5, authorships10, pairs5, candidates40, identifier entries27, graph edges18, enrichment links10, venues5, institutions2, topics3, ORCID profiles1, activities16. Complete manifests, counters, output hashes and representative declared evidence retained in evidence-repair-artifacts.json. Independent synthetic retention fixture has one completed run; overflow fixture has two fresh completed runs and asserts equivalence plus sensitivity to source/snapshot/native-identity changes. These synthetic fixtures are explicitly labeled.

Dataset validation, 6 acquisition-bound tests, all4 sample hashes, EMR script syntax and placeholder remote dry-run passed earlier in this repair pass. No AWS execution.

EVIDENCE AGGREGATION: Initial read-only collector assumed the generated marker was JSON; it is key=value properties. A second collector mixed relative/absolute paths while retaining synthetic examples. Both aborted before writing final JSON. Corrected collector parses properties and resolves paths; all assertions pass. No source, output or gate mutation resulted.

ASSUMPTIONS: JDK17.0.20.1, sbt1.10.7, Scala3.3.4, Hadoop3.3.6 Provided. Native escalation allowed sbt cache access; all pipeline execution local.
RISKS: AWS unverified. XML split prefix replay cost remains documented. Reviewer context reused due native thread limit, while review stays independent/read-only.
MANUAL ACTION REQUIRED: Human Phase4 acceptance after review of full diff/evidence.
BLOCKED-ON OWNER: None for local verification.
BLOCKED-ON EVIDENCE: Final independent verdict pending.
NEXT GATE: Final read-only verdict, then human Phase4 decision. No commits, pushes, deployments or Phase5.


### Packaging task success was insufficient for current-core equality

Independent reviewer observed stale WorkRecord.class bytes in dependency and submit bundles. Namespace and embedded-external equality checks in the successful21:59 gate passed but did not verify current core class content. Artifact JSON preserves those exact historical files/hashes; it must not be treated as final distributed packaging approval. Build owner is repairing cached overlay and adding stronger content verification/feature tests. Final full gate must run on the new build source.


### Cached-core merge verification — 2026-10-07

STATUS: Targeted complete; full final gate running.
OWNER: Coordinator executing gates for build-engineer source.
COMMANDS RUN:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch scalafmtSbt 'buildVerification/Compile/scalafmt' 'buildVerification/Test/scalafmt' 'buildVerification/testOnly scholarchain.build.HadoopBundleMergeSpec' hadoopSubmitJar hadoopSubmitJar > docs/agent-runs/phase-04/evidence-repair-packaging-targeted.txt 2>&1
```

TEST RESULTS: Exit0; two new build regressions pass at22:08:45; two consecutive cached packages pass at22:08:46. Root byte inspection confirms478 current core entries, no mismatches, no stale namespaceextras, current WorkRecord14386bytes/SHA2d4499e38b59488b4bb47aa6b12a682376d0fdad6887624e0e15c0ede4c1125e in current/core/bundle/embedded. Embedded bundle exactly matchesexternal; evidence-repair-packaging-byte-check.json retained.

Full same replay command restarted after user `continue`; frozen snapshot now92source/config paths. Final new expected count220 (two new build tests) remains unclaimed until observed. Historical pre-fix218gate/artifacts renamed pre-packaging; no stale archive evidence overwritten.


## Final gate after cached-core repair — 2026-10-07

STATUS: COMPLETE.
OWNER: Coordinator for execution/evidence; separate implementation work orders for source/domain/build, independent test owner, read-only reviewer.
WORK ORDER: Complete final gate after cached-core overlay repair, preserving all preceding repair evidence.
FILES CREATED: Final evidence-repair-full-gate.txt, evidence-repair-gate-summary.txt, evidence-repair-artifacts.json; cached-merge targeted log/byte-check JSON.
FILES MODIFIED: Evidence reports. Build files/tests listed in owner report.
COMMANDS RUN:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch check hadoopSubmitJar 'hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain' > docs/agent-runs/phase-04/evidence-repair-full-gate.txt 2>&1
```

TEST RESULTS: Exit0. sbtcheck completes22:19:10 local in399sec: core99,Hadoop64,independent53,build verification4; **220 tests pass**, zero failures/errors/skips. Expected nested format-stage failure probe passes its parent test. JUnit suite files/hashes and generated successful marker retained in final artifact JSON. All92 scoped source/config SHA256 values and mtimes unchanged during gate.

VALIDATION RESULTS: Packaging completes22:19:11/1sec and verifies all478 current core non-signature entries, exact core namespace, entry sizes/SHA and ownership inventory. Independent root ZIP comparison confirms zero mismatches/stale core extras, WorkRecord14386bytes/SHA2d4499e38b59488b4bb47aa6b12a682376d0fdad6887624e0e15c0ede4c1125e, and exactly one embedded bundle byte-identical to external. Core namespace now474 entries after stale entries removed; Scala3549/upickle346/ujson107; Hadoopmodule0 and ApacheHadoop0. Before fullgate, two cached packaging invocations and two merge regression tests passed.

Two fresh sample runs complete22:19:32/21sec: target/phase4-runs/fda6168a-d4e6-4c20-bf73-42a1c3724f7f and target/phase4-runs/ccd26111-d26d-4783-bc0f-e7106e4e617d. Both reused=false; logicalRecordsEqual=true. Each has8 intermediate+1export _SUCCESS and validated completion metadata. Matching export counts:5works,10mentions,5teams,10authorships,5pairs,40candidates,27index,18edges,10enrichment,5venues,2institutions,3topics,1ORCIDprofile,16activities. Each countersINPUT195,ACCEPTED242,REJECTED0,DUPLICATE0,CONFLICT0,OVERSIZE_BLOCK0,OVERSIZE_TEAM0,EMITTED_PAIR45,MISSING_KEY0,SCHEMA_FAILURE0; largestteam2,pairexpansion1,block4. Synthetic independent artifacts retain1 evidence fixture and2 fresh overflow runs. All source-evidence retention/negative-comparison feature tests pass in fullgate.

ASSUMPTIONS: Java17.0.20.1/sbt1.10.7/Scala3.3.4/Hadoop3.3.6Provided. Local only.
RISKS: AWS/largecorpus execution unverified; XMLprefix replay performance documented. Fresh source/artifact inspection uses existing read-only reviewer context due native thread limit.
MANUAL ACTION REQUIRED: HumanPhase4 decision after final independent verdict and complete diff review.
BLOCKED-ON OWNER: None for gate.
BLOCKED-ON EVIDENCE: Formal final independent verdict pending.
NEXT GATE: Final independent artifact recheck, then human acceptance. No commit/push/deployment/Phase5.


FINAL INDEPENDENT REVIEW: APPROVE. Reviewer independently verified220passingtests, all478currentcore entry content, two equivalent fresh sample runs, completion metadata/export hashes and60scopedsource fingerprints unchanged; coordinator92-path snapshot unchanged. Reviewer executed no tests/builds. No remaining implementation blocker in reviewedscope. HumanPhase4 acceptance remains pending.

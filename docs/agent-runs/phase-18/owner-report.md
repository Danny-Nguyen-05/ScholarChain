# Phase 18 owner reports (assembled by the coordinator)

Assembled on 2026-11-26 (America/Chicago) by the coordinator. Sources:
- each owner's final report as returned to the coordinator in chat;
- the commit that carried the owner's files;
- `test-report.md` (reviews and full checks) and `human-gate.md` (decisions).

The full chat reports were not stored in the repository when each package closed. Each section below restates the report fields from those sources. Where an owner's own count was not kept, the section says so; it does not substitute a coordinator figure. The work order is `work-order.md` (packages 18A and 18B). The Day 2 and Day 3 work was routed by the human's chat decisions recorded in `human-gate.md`.

The coordinator's own records are described in `test-report.md` and `human-gate.md`, not here:
- this folder;
- the Day 2 evidence under `evidence/day2/` (index `evidence/day2/INDEX.md`);
- the token redactions in `df299ea` and `b11afe9`.

## infra-engineer (18A)

STATUS: COMPLETE (initial fix; one relaunch for the infra/terraform pins, human decision of 2026-11-24 3:00 PM; review rounds 1 and 2 repairs)
OWNER: infra-engineer
WORK ORDER: `docs/agent-runs/phase-18/work-order.md`, package 18A
FILES CREATED: none
FILES MODIFIED: `scripts/emr/sc-step.sh` (the `spark-job` template fetch runs before `spark_env`; diagnostic fetch-environment log line), `scripts/tests/test_pipeline.py` (regression test that fails on the old order), `infra/terraform/emr-step-programs.json`, `infra/terraform/environments/course.local.tfvars.example`, `infra/terraform/tests/phase14a.tftest.hcl` (sha256 pins of `sc-step.sh`); commit `d5ba06c`
COMMANDS RUN: offline script tests under `scripts/tests/`; `step-manifest --check`; `shasum -a 256 scripts/emr/sc-step.sh`
TEST RESULTS: first launch, before the fix: 75 tests, 1 failure (the new regression test, on the old order); after the fix the regression test passes. The coordinator's full check `20261124T213555Z-18186` reached `RESULT: PASS gates=7` (`test-report.md`).
VALIDATION RESULTS: `sc-step.sh` sha256 `1edcf68d29481015da5675aad7fbe74d4af685f9d0c27a5378f23ffeab7c8eed` in all three pins; `step-manifest --check` ok
ASSUMPTIONS: the 2026-11-18 failure came from fetching the template after `spark_env` had cleared the EMR classpath (a hypothesis until a live run)
RISKS: the fix was not proven on EMR at commit time; the ignored local tfvars kept an old hash until the human updated it
MANUAL ACTION REQUIRED: the human updates the hash in the git-ignored `course.local.tfvars` before any live plan
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: a live EMR run (Day 2)
NEXT GATE: review, full check, human approval (granted 2026-11-24 5:05 PM)

## experiment-engineer (18B)

STATUS: COMPLETE (review round 1 repairs; round 2 APPROVE)
OWNER: experiment-engineer
WORK ORDER: human decision of 2026-11-24 5:40 PM, answers 2 and 3 (`human-gate.md`); coordinator routing in `test-report.md`, package 18B
FILES CREATED: none
FILES MODIFIED: `experiments/manifests/15a-emr-size-100.json` (S run 75 to 120 minutes, `max_usd` 0.84 to 1.25), `experiments/scripts/check_manifests.py` (ledger check models the Session 2 S attempt), `experiments/scripts/render_manifests.py`, `experiments/tests/test_experiments.py`, `experiments/README.md`, `experiments/manifests/16-evaluation.json` (`check_manifests.py` sha refreshed); commit `5c42378`
COMMANDS RUN: experiment tests and `check_manifests.py` (owner); `shasum -a 256 experiments/scripts/check_manifests.py` (coordinator)
TEST RESULTS: owner counts not kept; the coordinator's full check `20261125T013045Z-81496` reached `RESULT: PASS gates=7`
VALIDATION RESULTS: `check_manifests.py` sha256 `5240a76104ea9fb8aa7e9590e22d0d2bad873f989249a89d57e8396b3b67365e` equals the value in `16-evaluation.json` (coordinator); arithmetic 0.555 USD/h x 8,100 s = 1.24875, rounded up to 1.25
ASSUMPTIONS: the Session 2 S attempt cost (USD 0.37) is taken from its committed evidence
RISKS: a run 4 at its full estimate leaves USD 0.01 of ledger margin
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: review, full check, human approval (granted 2026-11-24 9:05 PM)

## infra-engineer (18B)

STATUS: COMPLETE (review round 1 repair M1; round 2 APPROVE)
OWNER: infra-engineer
WORK ORDER: human decision of 2026-11-24 5:40 PM, answer 3 (`human-gate.md`); `test-report.md`, package 18B
FILES CREATED: none
FILES MODIFIED: `scripts/config/release.conf` (`EMR_MAX_LIVE_RUNS` 4 to 5, `EMR_CUMULATIVE_CAP_USD` 3.53 to 4.70, `EMR_MAX_RUN_USD` 3 unchanged), `scripts/run-bounded-pipeline.sh` (help text), `scripts/README.md`, `scripts/tests/test_d3_emr_primary.py`, `scripts/tests/test_experiment.py`, `scripts/tests/test_phase15_pipeline_pins.py`, `scripts/tests/test_pipeline.py`, `scripts/tests/test_providers.py`; commit `c7d3368`
COMMANDS RUN: offline script tests under `scripts/tests/` (owner)
TEST RESULTS: owner counts not kept; full check `20261125T013045Z-81496` script-tests suites 1219/0, 494/0, 468/0, 78/0 failures
VALIDATION RESULTS: Phase 15 tests pinned to the historic caps; new Phase 18 boundary tests
ASSUMPTIONS: 4.70 is derived from the human's answers, not named by the human (recorded in `human-gate.md`)
RISKS: none recorded
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: review, full check, human approval (granted 2026-11-24 9:05 PM)

## test-engineer (18B)

STATUS: COMPLETE (review round 2 APPROVE)
OWNER: test-engineer
WORK ORDER: `docs/agent-runs/phase-18/work-order.md`, package 18B; `test-report.md`, package 18B
FILES CREATED: none
FILES MODIFIED: `tests/scripts/test_cap_pins_14b.py`, `tests/scripts/test_pipeline_refusals.py`, `tests/scripts/test_prespend_floors_14b.py`, `tests/scripts/test_record_actual_15.py`; commit `4e0831d`
COMMANDS RUN: tests under `tests/scripts/` (owner)
TEST RESULTS: owner counts not kept; full check `20261125T013045Z-81496` `RESULT: PASS gates=7`
VALIDATION RESULTS: live caps, the 1.25 estimate, the 1.26 / 1.27 retry boundary and the sixth-run refusal asserted; historic tests pinned to the 4 / 3.53 caps
ASSUMPTIONS: none recorded
RISKS: the frozen Phase 15 plan totals USD 24.07 with the new EMR allowance, above floor 2 (23.00) and below the 25.00 ceiling; a disclosed finding, not a gate
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: review, full check, human approval (granted 2026-11-24 9:05 PM)

## incident-responder (Day 2 records)

STATUS: COMPLETE (review round 2 APPROVE)
OWNER: incident-responder
WORK ORDER: coordinator routing after Day 2 (2026-11-25), human decision "Commit and push" of 2026-11-25 10:05 PM (`human-gate.md`)
FILES CREATED: `docs/incidents/2026-11-25-emr-hadoop-prep-intermediate-missing.md`
FILES MODIFIED: `docs/incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md` (resolved by the 18A fix, run 5), `docs/incidents/2026-11-18-console-permission-gaps.md`, `docs/incidents/2026-11-18-deployer-session-drops.md` (recurrence notes: EIP 403, budgets read, expired deployer sessions), `docs/incidents/README.md`; commit `8167a74`
COMMANDS RUN: none beyond reading the committed Day 2 evidence
TEST RESULTS: none run (records only)
VALIDATION RESULTS: references checked against `evidence/day2/` by review rounds 1 and 2
ASSUMPTIONS: none recorded
RISKS: the root cause of the run 4 `hadoop-prep` failure stays open; no EMR run remains to test it (ledger 5 of 5)
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: the private EMR step stderr (not read, not copied)
NEXT GATE: review, human commit decision (granted)

## experiment-engineer (Day 3, Phase 16 reproducibility evidence)

STATUS: COMPLETE (review APPROVE)
OWNER: experiment-engineer
WORK ORDER: human decision of 2026-11-26 about 11:00 AM CST, one-time exception (`human-gate.md`, Day 3 decisions)
FILES CREATED: none
FILES MODIFIED: `experiments/results/phase16/reproducibility/reproducibility-evidence.json`, `experiments/results/phase16/reproducibility/reproducibility-evidence.md` (regenerated after the redaction changed one input hash), `experiments/manifests/16-evaluation.json` (two pins); commit `b11afe9`
COMMANDS RUN: `python3 -I experiments/scripts/eval16_repro.py --verify`; `python3 -I experiments/scripts/check_manifests.py`; `python3 -I -m unittest discover -s experiments/tests`
TEST RESULTS: `REGENERATION: PASS pass=24 fail=0 skipped_scripts=0`; `RESULT: OK`, 106 file hashes verified; `Ran 260 tests`, `OK`
VALIDATION RESULTS: as above
ASSUMPTIONS: none recorded
RISKS: the old token values remain in git history
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: review, full check, human commit decision (granted)

## documentation-engineer (Day 3 docs update)

STATUS: COMPLETE (review round 1 REQUEST CHANGES, all findings repaired; round 2 APPROVE)
OWNER: documentation-engineer
WORK ORDER: Phase 18 docs update, human decision of 2026-11-26 ("Let's keep it for tomorrow lets do today first"; plan of record in `test-report.md`, Day 3)
FILES CREATED: none
FILES MODIFIED: `README.md`, `reports/final-report.md`, `reports/release-manifest.md`, `docs/architecture.md`, `docs/data-lineage.md`, `docs/demo-script.md`, `docs/evaluation.md`, `docs/report/evaluation.md`, `docs/runbook.md`, `docs/service-limits.md`, `docs/threat-model.md`; commit `5883b03`
COMMANDS RUN: link and evidence checks (owner); coordinator link check
TEST RESULTS: none run (documentation only); full check `20261126T192732Z-47531` `RESULT: PASS gates=7`
VALIDATION RESULTS: coordinator link check: 935 links in 11 files, 0 problems; release-manifest `16-evaluation.json` pin `9af12cec…` equal to the file (coordinator check reported in chat, not stored)
ASSUMPTIONS: none recorded
RISKS: four optional review nits left unchanged
MANUAL ACTION REQUIRED: the human adds the final video link after upload
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: release SHA and tag (set at the release)
NEXT GATE: review, full check, human commit decision (granted)

## experiment-engineer (Day 3 docs update)

STATUS: COMPLETE (review round 2 APPROVE)
OWNER: experiment-engineer
WORK ORDER: same as the documentation-engineer's Day 3 docs update
FILES CREATED: none
FILES MODIFIED: `experiments/README.md` (Phase 18 ledger: runs 4 and 5, 5 of 5, USD 2.65 of 4.70; the regenerated Phase 16 reproducibility evidence; 260 tests); commit `0a7d4af`
COMMANDS RUN: `python3 -I -m unittest discover -s experiments/tests` (owner)
TEST RESULTS: `Ran 260 tests`, `OK` (owner's chat report, not stored; `test-report.md` records 260 tests for `b11afe9`); full check `20261126T192732Z-47531` `RESULT: PASS gates=7`
VALIDATION RESULTS: cited lines checked against `evidence/day2/emr/emr-run-2.log` by review round 2 (review report in chat, not stored)
ASSUMPTIONS: none recorded
RISKS: none recorded
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: review, full check, human commit decision (granted)

## hadoop-engineer (Day 3, autograder fix HADOOP-PAIRS-WRONG)

STATUS: COMPLETE
OWNER: hadoop-engineer
WORK ORDER: human decision "Fix all three" of 2026-11-26 about 8:20 PM CST (`human-gate.md`); autograder V2 2.3.5 item HADOOP-PAIRS-WRONG (J08 skipped oversize teams without a reject or counter)
FILES CREATED: none
FILES MODIFIED: `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/DerivedRecords.scala` (lines 65-80: one `OversizeTeam` reject, stage `CoauthorPair`, per team above the limit; pairs within the limit unchanged), `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/PrepSupport.scala` (counter `OVERSIZE_TEAM_PAIR_STEP`, lines 23, 36, 585-589; J07 still counts `OVERSIZE_TEAM`), `modules/hadoop/README.md` (lines 40, 93; review round 1: lines 74-75 state that the transformation version label `hadoop-prep-j01-j09-v3-stable-overflow-lineage` covers the output before and after this change, human decision "Keep v3, document"), comment at `PrepSupport.scala:585-586` reworded (review n1), `modules/hadoop/src/test/scala/edu/uic/cs441/scholarchain/hadoop/CoauthorPairGenerationSpec.scala` (lines 213-258: three tests replace the old "yields nothing" test), `modules/hadoop/src/test/scala/edu/uic/cs441/scholarchain/hadoop/HadoopPrepSpec.scala` (lines 452-462: full J01-J09 pipeline asserts both counters and the exported reject)
COMMANDS RUN: `sbt -batch "hadoop/scalafmt" "hadoop/Test/scalafmt"`; `sbt -batch "hadoop/test" "hadoop/scalafmtCheck" "hadoop/Test/scalafmtCheck"` (JDK 17); read-only `git grep` for counter consumers and hash pins
TEST RESULTS: "Suites: completed 5, aborted 0"; "Tests: succeeded 103, failed 0, canceled 0, ignored 0, pending 0"; scalafmtCheck success for Compile and Test (owner; the same counts again after the review round 1 repairs, 8:38 PM CST)
VALIDATION RESULTS: no tracked file pins a hash of the Hadoop source; `counter-summary.json` readers use `getOrElse(name, 0)`
ASSUMPTIONS: a J08-specific counter, so `OVERSIZE_TEAM` keeps meaning J07 rejects; each oversize team now yields two rejects (J07 and J08, different stages)
RISKS: future runs report one more counter and a higher `REJECTED`; the EMR submit-JAR hashes recorded for past runs no longer match the current source (no EMR run used the changed code)
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: documentation-engineer for `docs/data-lineage.md` J08 statements and `reports/release-manifest.md` JAR note (routed)
BLOCKED-ON EVIDENCE: none
NEXT GATE: review, full check, autograder rerun, human commit decision

## dataset-engineer (Day 3, autograder fix DATA-05)

STATUS: COMPLETE
OWNER: dataset-engineer
WORK ORDER: human decision "Fix all three" of 2026-11-26 about 8:20 PM CST (`human-gate.md`); autograder V2 2.3.5 items DATA-05 (no schema-version statement) and the DATA-02 note (no schema version per manifest entry)
FILES CREATED: `datasets/scripts/test_schema_versions.py` (8 tests)
FILES MODIFIED: `datasets/schemas/dblp-xml.md`, `datasets/schemas/openalex-works.md`, `datasets/schemas/orcid-record.md`, `datasets/schemas/crossref-works.md` ("Schema version" and "Upstream version" statements; where the upstream version is not recorded the note says so and names the sample or provenance file), `datasets/dataset-manifest.yaml` (a `schema_version` per entry, lines 45, 98, 148, 197), `datasets/scripts/validate_datasets.py` (field required; `validate_schema_versions` checks the id pattern, that the note exists and that it states the same id)
COMMANDS RUN: `python3 datasets/scripts/validate_datasets.py` (before and after); `python3 -B -m unittest discover -s datasets/scripts -p 'test_*.py'` and the `phase6` and `phase15` subfolders; `shasum -a 256 -c samples/SHA256SUMS` in `datasets/`; a negative run on a scratch copy with a mismatched id
TEST RESULTS: validator `OK: manifest (4 datasets), samples, and script bounds validated`; 105 tests OK (8 new), 12 OK, 13 OK; four sample checksums OK; the negative run exited 1 with the mismatch message (owner)
VALIDATION RESULTS: the only live pin of a changed file is `reports/release-manifest.md:88` (dataset manifest sha256), routed to the documentation-engineer; old hashes in earlier phase evidence stay as historical records
ASSUMPTIONS: PyYAML was not installed for the system Python; the owner ran the validator with a pure-Python PyYAML 6.0.3 copied from another application's site-packages on this machine (exact path not recorded) on `PYTHONPATH`, instead of `python3 -I`. The coordinator then reran with the pinned PyYAML 6.0.2 in a throwaway virtual environment (`python -I -B`): `OK: manifest (4 datasets), samples, and script bounds validated` (exit 0); `datasets/scripts` `Ran 105 tests`, `OK`; `phase6` `Ran 12 tests`, `OK`; `phase15` `Ran 13 tests`, `OK`
RISKS: `scripts/check.sh` does not run `validate_datasets.py` or the `datasets/scripts` tests (it only byte-compiles `scripts/**/*.py`), so the dataset gate is run by hand, as above
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: documentation-engineer for `reports/release-manifest.md:88` (routed)
BLOCKED-ON EVIDENCE: none
NEXT GATE: review, full check, autograder rerun, human commit decision

## documentation-engineer (Day 3, autograder fixes)

STATUS: COMPLETE (review rounds 1 and 2 repairs)
OWNER: documentation-engineer
WORK ORDER: human decision "Fix all three" of 2026-11-26 about 8:20 PM CST and "Keep v3, document" about 8:35 PM CST (`human-gate.md`); BLOCKED-ON items routed from the hadoop-engineer and the dataset-engineer
FILES CREATED: none
FILES MODIFIED: `docs/data-lineage.md` (J08 reject and `OVERSIZE_TEAM_PAIR_STEP` counter at lines 52, 71, 80, 87-94, 102; dated historical-counter note after line 112; v3 note at line 56; shifted citations at lines 76 and 90), `docs/threat-model.md` (line 96, historical-counter note), `reports/final-report.md` (line 86, historical-counter note), `reports/release-manifest.md` (line 5 names the two pins changed on 2026-11-26 and section 5; line 88 dataset-manifest sha256 `137c6bde…`, earlier value kept for comparison; dated note that the EMR JAR hashes describe the JAR that ran and no EMR run used the changed Hadoop source; line 159 "two changed")
COMMANDS RUN: `shasum -a 256 datasets/dataset-manifest.yaml`; `git show HEAD:datasets/dataset-manifest.yaml | shasum -a 256`; `grep -n` and `sed -n` on the Hadoop sources and specs to verify every cited line; a relative-link and anchor check over the four changed files
TEST RESULTS: none run (documentation only)
VALIDATION RESULTS: link check `links 393 problems 0`; `137c6bdee9e35a7842c4f7f01b835b811ee8eae763fa817d6e550e15f6f7eabb` equals the current manifest; `cf1cba59…` is the manifest at `17b1cf1`; review round 2 re-checked the cited Hadoop line numbers
ASSUMPTIONS: none recorded
RISKS: `experiments/README.md:54` and three experiment JSON files keep historical counters without a note (experiment-engineer's files; left as historical records)
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: full check, autograder rerun, human commit decision

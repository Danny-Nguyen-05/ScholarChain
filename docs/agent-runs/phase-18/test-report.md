# Phase 18 test report: package 18A

Assembled by the coordinator from observed output, 2026-11-24 (America/Chicago). Offline only: no AWS call, no Terraform plan or apply.

## Review

- code-reviewer (Claude Opus 5.5, read-only), round 1: APPROVE with 3 minor findings (m1-m3) and 3 nits (n1-n3), all optional. The coordinator routed all six: m1, n2 to the coordinator records; m2, m3, n1, n3 to the infra-engineer.
- Round 2: APPROVE; all six repaired. One new optional nit (n4: `scripts/emr/sc-step.sh:332` says hadoop-prep runs "no environment change at all"; it exports `HADOOP_CLASSPATH` after its fetches). Deferred to any later change of `sc-step.sh`, to avoid another pin cycle.

## Full check after APPROVE

Command: `scripts/check.sh` (JDK 17), run id `20261124T213555Z-18186`, 3:35 PM to 4:59 PM CST. Logs: `target/check-logs/20261124T213555Z-18186/` (git-ignored).

| Gate | Result |
|---|---|
| constitution | PASS |
| hooks | PASS |
| shell | PASS |
| python | PASS |
| terraform | PASS |
| script-tests | PASS (suites: 1208/0, 487/0, 468/0, 78/0 failures) |
| sbt | PASS (1,810 succeeded, 0 failed, 2 canceled) |

`RESULT: PASS gates=7`. `.claude/.last-test-run` updated at 4:59:44 PM CST.

## Other owner-reported evidence

- `sc-step.sh` sha256 `1edcf68d29481015da5675aad7fbe74d4af685f9d0c27a5378f23ffeab7c8eed`, pinned in `infra/terraform/emr-step-programs.json`, `infra/terraform/environments/course.local.tfvars.example` and `infra/terraform/tests/phase14a.tftest.hcl`; `step-manifest --check` ok. The old hashes remain only in `docs/agent-runs/phase-15/**` (historical evidence, unchanged).
- The main regression test failed on the old order (first infra-engineer launch: 75 tests, 1 failure, the new test) and passes on the new order.

## Not verified

- The fix itself on EMR. The cause stays a hypothesis until a live run (Day 2), which needs the official extension and the human's gates.
- The ignored `course.local.tfvars` still holds an old hash; the human updates it before any live plan.

# Package 18B: S run 120 minutes, EMR ledger 5 runs / USD 4.70

Assembled by the coordinator from observed output and owner reports, 2026-11-24 (America/Chicago). Offline only: no AWS call, no Terraform plan. Human decisions: `human-gate.md`, 5:40 PM answers 2 and 3.

## Owners and changes

| Owner | Files | Change |
|---|---|---|
| experiment-engineer | `experiments/manifests/15a-emr-size-100.json`, `experiments/scripts/check_manifests.py`, `experiments/scripts/render_manifests.py`, `experiments/tests/test_experiments.py`, `experiments/README.md`, `experiments/manifests/16-evaluation.json` | S run 75 -> 120 minutes, `max_usd` 0.84 -> 1.25; the ledger check models Session 1 1.68 + the Session 2 S attempt 0.37 (guarded by its committed evidence) + S 1.25 + retry 1.25 = 4.55 over 5 runs, plus the stricter `budget.py` admission line; `check_manifests.py` sha refreshed |
| infra-engineer | `scripts/config/release.conf`, `scripts/run-bounded-pipeline.sh` (help text), `scripts/README.md`, five files under `scripts/tests/` | `EMR_MAX_LIVE_RUNS` 4 -> 5, `EMR_CUMULATIVE_CAP_USD` 3.53 -> 4.70, `EMR_MAX_RUN_USD` stays 3; Phase 15 tests pinned to the historic caps; new Phase 18 boundary tests |
| test-engineer | `tests/scripts/test_cap_pins_14b.py`, `test_record_actual_15.py`, `test_pipeline_refusals.py`, `test_prespend_floors_14b.py` | live caps, the 1.25 estimate, the 1.26 / 1.27 retry boundary and the sixth-run refusal asserted; historic tests pinned to the 4 / 3.53 caps |

Arithmetic: estimate 0.555 USD/h x 8,100 s = 1.24875, rounded up to 1.25. Step timeouts at 120 minutes: 6 / 24 / 24 / 6 / 48 / 12 minutes. With the recorded ledger (3 runs, USD 2.05, from the committed evidence `docs/agent-runs/phase-15/evidence/session-2/emr/emr-actual-1end.log`), run 5 is admitted iff run 4 measures at most USD 1.26 while its 0.14 idle tail is counted, or at most 1.40 once recorded after termination. A run 4 at its full estimate leaves USD 0.01.

## Review

- code-reviewer (Claude Opus 5.5, read-only), round 1: REQUEST CHANGES, no blocker. M1 (`scripts/README.md` still stated the 4-run / 3.53 caps), M2 (the ledger check omitted the Session 2 attempt and overstated the margin as 0.52 USD / 1 run), m1 (1.26 described as the recorded rather than the measured bound), m2 (the human-gate "Not covered" line contradicted the 5:40 PM answers), m3 (a test required the floor-2 breach to exist), m4 (stale live docs, deferred to the documentation-engineer), and nits. Routed to the owners; m2 repaired by the coordinator.
- Round 2: APPROVE, no blocker, major or minor findings. Three nits: the coordinator's (4.70 is derived, not named by the human) repaired in `human-gate.md`; `experiments/README.md:40` could also state the 1.40 bound; `scripts/README.md:317-328` present tense under the superseded note (accepted). The reviewer confirmed the Day 2 approval-file path: an `--approval` file under the git-ignored `target/` does not reach the dirty-tree check; it must name the final HEAD and is single-use.
- `shasum -a 256 experiments/scripts/check_manifests.py`, observed by the coordinator: `5240a76104ea9fb8aa7e9590e22d0d2bad873f989249a89d57e8396b3b67365e`, equal to the value in `experiments/manifests/16-evaluation.json`.

## Full check after APPROVE

Command: `scripts/check.sh` (JDK 17), run id `20261125T013045Z-81496`, 7:30 PM to 8:48 PM CST. Logs: `target/check-logs/20261125T013045Z-81496/` (git-ignored).

| Gate | Result |
|---|---|
| constitution | PASS |
| hooks | PASS |
| shell | PASS |
| python | PASS |
| terraform | PASS |
| script-tests | PASS (suites: 1219/0, 494/0, 468/0, 78/0 failures) |
| sbt | PASS (1,810 succeeded, 0 failed, 2 canceled) |

`RESULT: PASS gates=7`.

## Disclosed finding

The frozen Phase 15 project plan (2026-11-16) totals USD 24.07 with the new EMR allowance, above the floor-2 limit of 23.00 and below the firm 25.00 ceiling (`tests/scripts/test_cap_pins_14b.py`, a disclosed finding, not a gate). It uses frozen estimates, not today's spend. The live spend gate is the human pre-spend receipt.

## Not verified (18B)

- The S run on EMR at 120 minutes (Day 2).
- Stale live docs (`docs/service-limits.md`, `docs/runbook.md`, `reports/release-manifest.md`): documentation-engineer, Day 3.

# Day 2: live EMR proof and cleanup (2026-11-25)

Assembled by the coordinator from observed output after the session. Evidence: `evidence/day2/` (index `evidence/day2/INDEX.md`; redacted copies). Human decisions: `human-gate.md`, Day 2 section. HEAD `fe0b6cc` throughout; no sbt, packaging or commit during the session.

## Result

**The Phase 18 fix works on EMR.** In run 5 the `spark-job` step (`s-08041352ORZOW9X35U3M`) COMPLETED. The uploaded step program was `sc-step.sh` sha256 `1edcf68d…` (`evidence/day2/emr/emr-upload-manifest.json:162`; decision log 11:23 CST entry), equal to the committed file and the pin in `infra/terraform/emr-step-programs.json:7`; the run log masks the hash. This closes the 18A "Not verified" item on the fix, with two limits: one run, not repeated; and the cause is inferred from the ordering change, because the 2026-11-18 error was not reproduced and the kit's `template fetch environment:` log line is not in the copied evidence. The other 18A item, the old hash in the ignored `course.local.tfvars`, was updated by the human before the plan: kit block 7 counted the old hash 0 times.

## EMR runs, size S, cluster `j-05116692OZ06APLO3FMD`

| Run | Run id | Result | Evidence |
|---|---|---|---|
| 4 (attempt 1) | `15a-emr-size-100-20261125T173348Z-95764` | FAILED at `hadoop-prep` (`InvalidInputException`, job 2 input `intermediate/j02` not found on the shared mount), pipeline exit 4. Not the Phase 18 path. Incident `docs/incidents/2026-11-25-emr-hadoop-prep-intermediate-missing.md`, root cause open | `emr/emr-run-1.log` |
| 5 (retry) | `15a-emr-size-100-20261125T174034Z-99560` | PASS, 17:40:34Z-18:14:39Z: stage-in, hadoop-prep, entity-resolution, spark-class-origin, spark-job, copy-out all COMPLETED; exit 0 | `emr/emr-run-2.log` |

Step durations of run 5 from the EMR console Steps tab (human screenshot, not kept; clip 1): hadoop-prep 7m6s, entity-resolution 6m2s, spark-job 16m38s. Upper bounds from submit-to-result times in `emr/emr-run-2.log`: 7m42s, 6m43s and 17m29s.

Export `spark/run:30b3ef84-11dc-4c8c-b9c2-c632477d7282` with `_SCHOLARCHAIN_SPARK_COMPLETE`. Counters (`emr/spark-counters.json`): canonicalWorks 10578, canonicalResearchers 21819, allYearsEdges 81181, components 3942, communityIterations 20 (not converged), crossCommunityEdges 17589. Download: 468 objects, 0 error mentions (`emr/download-excerpt.log`); archive `day2-v1` written and verified, 30 entries (`emr/archive.log`).

EMR ledger after termination (`emr/emr-actual-2end.log`): 5 of 5 live runs, USD 2.65 of the 4.70 cap. Day 2 EMR ledger estimate USD 0.60 (run 4 0.09, run 5 0.51); these are ledger estimates (0.555 USD/h times the measured window), not billed amounts. No further run is possible without a new human decision.

## Other live gates

| Step | Result | Evidence |
|---|---|---|
| Deployer and operator roles (IAM window 1, 16:37:43Z-16:45:21Z) | 31 added | `stage-a/deployer-apply.log` |
| Stage-a base-apply | PASS, plan `IDENTICAL` to the reviewed list | `stage-a/stagea-base-plan.log`, `stage-a/stagea-base-apply.log` |
| Runtime archive upload | PASS, 321,876,735 bytes in about 84 s | `stage-a/stagea-upload.log` |
| EMR artifact upload | PASS, 17 files verified | `emr/emr-upload.log` |
| EMR enable | PASS, 13 creates, `IDENTICAL` | `emr/stagea-emr-plan.log`, `emr/stagea-emr-apply.log` |
| Cleanup-prepare | PASS (second plan attempt; the first stopped at `account-identity`, expired session, nothing ran) | `cleanup/cleanup-prepare-plan.log`, `cleanup/cleanup-prepare.log` |
| Destroy pass 1 | PARTIAL as expected at `aws_eip.nat` DisassociateAddress 403; 331 to 87 inventory entries | `cleanup/cleanup-pass-1.log` |
| Destroy pass 2 | PASS, only `aws_eip.nat`; 48 to 46 | `cleanup/cleanup-pass-2.log` |
| C4 (IAM window 2, 02:57:35Z-03:11:50Z on 2026-11-26) | 13 destroyed | `p39/deployer-c4.log` |
| P39 | 18 destroyed, deployer state empty, `get-role` NoSuchEntity, roles diff only `scholarchain-deployer` | `p39/p39-deployer-removal.log`, `p39/p39-roles-*.txt` |
| Final inventory (console; NAT, Elastic IPs and S3 in clip 5, the rest in clip 7) | No running EMR, NAT, Elastic IP, load balancer, Neptune, EFS, ECS cluster, course bucket or course secret; IAM roles only `scholarchain-billing-deployer` and AWS service-linked roles; KMS key pending deletion | `00-timeline/decision-log.md`, `recordings/clips.txt` |

The 46 inventory entries left after pass 2 are tag-index records: 35 ECS task-definition revisions, 7 terminated EMR clusters, the deleted ECS cluster, the KMS key (pending deletion) and 2 Terraform guard records. None is billable.

Between destroy pass 1 (ended 19:09:49Z) and pass 2 (02:44:38Z on 2026-11-26) about 7.6 hours passed, and the NAT Elastic IP stayed allocated (`cleanup/pass-1-after-inventory.txt`, `cleanup/pass-2-before-inventory.txt`), about USD 0.04 at the AWS list price for a public IPv4 address (USD 0.005 per hour; not from repository evidence). Pass 1 printed a `KEY-REVOCATION-REMINDER` for the two provider-key secret containers; the Day 2 kit has no step that stores a key value, so no Day 2 key needs revoking.

## Not verified (Day 2)

- The cause of the run 4 `hadoop-prep` failure (hypothesis: shared-mount visibility). No root-cause run; the ledger has no run left.
- The fix was proven by one run, not repeated.
- Why the inventory fell from 87 (end of pass 1) to 48 (start of pass 2); likely tag-index lag after deletions.
- Final cost: the console showed USD 19.26 of the USD 25 budget at about 9:12 PM CST; Cost Explorer lags, so the final Day 2 figure is not yet known.

# Day 3: token redaction (2026-11-26)

Records-only change: the used one-time destroy confirmation tokens were redacted in the Phase 18 Day 2 cleanup listings (`df299ea`) and, by the human's one-time exception, in the Phase 15 session-2 cleanup excerpt, with the Phase 16 reproducibility evidence regenerated (`b11afe9`). Decisions: `human-gate.md`, "Day 3 decisions". Reviews: `df299ea` review round 2 APPROVE; `b11afe9` review APPROVE.

## Owner-reported checks for `b11afe9`

- Phase 15 session-2 `INDEX.md`: 74 rows, 0 sha256 mismatches (coordinator).
- `python3 -I experiments/scripts/eval16_repro.py --verify`: `REGENERATION: PASS pass=24 fail=0 skipped_scripts=0` (experiment-engineer).
- `python3 -I experiments/scripts/check_manifests.py`: `RESULT: OK`, 106 file hashes verified (experiment-engineer).
- `python3 -I -m unittest discover -s experiments/tests`: `Ran 260 tests`, `OK` (experiment-engineer).

## Full check after APPROVE

Command: `scripts/check.sh` (JDK 17), run id `20261126T170301Z-26256`, 11:03 AM to 12:22 PM CST. Logs: `target/check-logs/20261126T170301Z-26256/` (git-ignored).

| Gate | Result |
|---|---|
| constitution | PASS (1s) |
| hooks | PASS (1s) |
| shell | PASS (7s) |
| python | PASS (1s) |
| terraform | FAIL (84s): `terraform fmt -check -recursive failed` on two git-ignored local files, `infra/terraform/deployer/deployer.local.tfvars` and `infra/terraform/environments/course.local.tfvars`, left unformatted by Day 2 edits; all Terraform test suites passed (largest: 333 passed, 0 failed) |
| script-tests | PASS (3853s) |
| sbt | PASS (822s); 9 sbt test summaries: 1,810 succeeded, 0 failed, 2 canceled |

`RESULT: FAIL failed: terraform`.

The coordinator then ran `terraform fmt` on the two ignored files at the human's request (whitespace only; only the file names were printed, contents not read), and `terraform fmt -check -recursive infra/terraform` exited 0. Rerun: `scripts/check.sh --only terraform`, run id `20261126T190048Z-32280`: `GATE: terraform PASS (63s)`, `RESULT: PARTIAL passed=1` (PARTIAL by design for `--only`). Together the two runs pass all 7 gates; no single run passed all 7 after the change.

# Day 3: Phase 18 docs update (2026-11-26)

Docs-only change: README, final report, release manifest, `docs/**` pages, `experiments/README.md` and the Day 3 section above, updated for the Phase 18 EMR proof and the token redaction. Owners: documentation-engineer and experiment-engineer; coordinator for this file. Review round 2 APPROVE (round 1 REQUEST CHANGES; all findings fixed by their owners; four optional nits left). The coordinator's link check over the 11 changed Markdown files found 935 links and 0 problems.

## Full check after APPROVE

Command: `scripts/check.sh` (JDK 17), run id `20261126T192732Z-47531`, 1:27 PM to 2:45 PM CST. Logs: `target/check-logs/20261126T192732Z-47531/` (git-ignored).

| Gate | Result |
|---|---|
| constitution | PASS (1s) |
| hooks | PASS (0s) |
| shell | PASS (8s) |
| python | PASS (0s) |
| terraform | PASS (62s); all Terraform test suites passed (largest: 333 passed, 0 failed) |
| script-tests | PASS (3790s) |
| sbt | PASS (820s); 9 sbt test summaries: 1,810 succeeded, 0 failed, 2 canceled |

`RESULT: PASS gates=7`. This run follows the `terraform fmt` of the two ignored local tfvars, so it is also the first single run after the token redaction to pass all 7 gates.

# Day 3: autograder fixes (2026-11-26)

Change: the Hadoop oversize-team pair step now writes one reject record and its own counter, `OVERSIZE_TEAM_PAIR_STEP` (hadoop-engineer); each dataset schema and manifest entry records a schema version, checked by `validate_datasets.py` (dataset-engineer); lineage, threat model, final report and release manifest updated to match (documentation-engineer); Phase 18 owner report and `commit.txt` added, and the Phase 17 owner report given its two missing fields under the human decision in `human-gate.md` (coordinator). Review round 3 APPROVE (rounds 1 and 2 REQUEST CHANGES; all findings fixed by their owners).

Owner checks before the full check (observed):

- `sbt hadoop/test`: 103 succeeded, 0 failed; `hadoop/scalafmtCheck` success (hadoop-engineer).
- Dataset validation with PyYAML 6.0.2: `OK`; dataset script tests 105, 12 and 13 tests `OK`, including the new `datasets/scripts/test_schema_versions.py` (coordinator rerun).
- Link check over the changed Markdown files: 393 links, 0 problems (coordinator).

## Full check after APPROVE

Command: `scripts/check.sh` (JDK 17), run id `20261127T024053Z-18142`, 8:40 PM to 10:11 PM CST. Logs: `target/check-logs/20261127T024053Z-18142/` (git-ignored).

| Gate | Result |
|---|---|
| constitution | PASS (1s) |
| hooks | PASS (0s) |
| shell | PASS (8s) |
| python | PASS (0s) |
| terraform | PASS (66s); all Terraform test suites passed (largest: 333 passed, 0 failed) |
| script-tests | PASS (4437s) |
| sbt | PASS (922s); 9 sbt test summaries: 1,812 succeeded, 0 failed, 2 canceled |

`RESULT: PASS gates=7`; the test marker was updated at 10:11 PM CST.

Limitation: the Phase 17 two-field amendment, the Phase 18 owner report and the human-gate entries were edited after this run started. They are Markdown records only, with no code, test or script change; the link check above covers them.

# Day 4: demo video v4 docs (2026-11-27)

Docs-only change: `README.md` (video bullet and D19 row), `docs/demo-script.md` (status, Phase 18 note, new video update block with the 26-chapter list) and the Demonstration row of `reports/final-report.md` now point to the replacement video `https://youtu.be/Bb6OzssRdWg` (documentation-engineer); Day 4 entries in `human-gate.md` (coordinator). Review round 2 APPROVE (round 1 REQUEST CHANGES, minor findings only; all fixed by their owners). The coordinator's link check over the 4 changed Markdown files found 431 relative links and 0 problems (3 external links not fetched).

## Full check after APPROVE

Command: `scripts/check.sh` (JDK 17), run id `20261127T220232Z-7744`, 4:02 PM to 5:27 PM CST. Logs: `target/check-logs/20261127T220232Z-7744/` (git-ignored).

| Gate | Result |
|---|---|
| constitution | PASS (0s) |
| hooks | PASS (1s) |
| shell | PASS (8s) |
| python | PASS (0s) |
| terraform | PASS (66s); all Terraform test suites passed (largest: 333 passed, 0 failed) |
| script-tests | PASS (4170s) |
| sbt | PASS (835s); 9 sbt test summaries: 1,812 succeeded, 0 failed, 2 canceled |

`RESULT: PASS gates=7`.

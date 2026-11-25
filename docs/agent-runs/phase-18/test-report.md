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

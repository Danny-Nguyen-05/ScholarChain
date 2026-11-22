# Phase 16 test report (coordinator)

All results below were observed by the coordinator on the final Phase 16 tree (branch `phase-15-q12`, uncommitted), JDK 17 (`openjdk version "17.0.20.1"`).

## Full check, round 1: FAIL

`scripts/check.sh`, run id `20261122T014945Z-29614` (started 2026-11-22T01:49Z): `RESULT: FAIL failed: script-tests`. Constitution, hooks, shell, python, terraform and sbt passed. One test failed in `tests/infra`: `test_billing_replan_14b.NoRealAccountIdIsAdded`, 4 findings (`account-id-literal`) at `experiments/tests/test_eval16_a.py:642,723` and `experiments/tests/test_eval16_b.py:281,282`. A digit-free classification showed all four were the AWS documentation example account ID, which the scanner allows only in `AwsTestSupport.scala` (human decision of 2026-11-09). Repair: see `repairs.md`, row "full check 1".

## Targeted checks after the repair

| Command | Observed result |
|---|---|
| `python3 -m unittest test_billing_replan_14b.NoRealAccountIdIsAdded` (in `tests/infra`) | Ran 2 tests, OK |
| `python3 -I experiments/scripts/check_manifests.py` | `CHECK-OK: 16-evaluation.json: offline scope (spend 0.00), policy clean, 106 file hashes verified`; `RESULT: OK` |
| `python3 -I -m unittest discover -s experiments/tests` | Ran 258 tests, OK (includes `test_eval16_a.py` 70 and `test_eval16_b.py` 44, as reported by the owners) |
| `python3 -I experiments/scripts/eval16_repro.py --verify` | `REGENERATION: PASS pass=24 fail=0 skipped_scripts=0` |

## Full check, round 2: PASS

`scripts/check.sh`, run id `20261122T032145Z-21920` (started 2026-11-22T03:21Z, 9:21 PM CST; finished 10:55 PM CST):

| Gate | Result |
|---|---|
| constitution | PASS (2071 JSON files parse) |
| hooks | PASS (4 scripts) |
| shell | PASS (27 scripts) |
| python | PASS (84 files compile) |
| terraform | PASS (6 roots; tests 12, 19, 114, 40, 6, 333 passed, 0 failed) |
| script-tests | PASS (`scripts/tests` 1200 OK, required classes executed; `scripts/phase12d-spike/tests` 78 OK; billing 121, 84, 39 OK; `tests/scripts` 487 OK; `tests/infra` 468 OK) |
| sbt | PASS (test blocks 194, 707, 30 succeeded, 0 failed; 1 canceled in the last block, as the build reports it) |

`RESULT: PASS gates=7`. The marker `.claude/.last-test-run` was updated at 2026-11-21T22:55:34 CST, after the sbt gate completed.

## Limits

- The `experiments/tests` suite is not one of the `check.sh` suites; its result above is the separate coordinator run.
- The full check proves the repository gates on this tree. It does not re-run any AWS or model step (Phase 16 is offline by decision).

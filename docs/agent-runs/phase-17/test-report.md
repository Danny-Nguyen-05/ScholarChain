# Phase 17 test report (coordinator)

All results below were observed by the coordinator on the final Phase 17 tree: branch `phase-17` at `55fb1b3` with the 43 uncommitted Phase 17 paths (owner files and coordinator records, after review round 2 APPROVE), JDK 17 (`openjdk version "17.0.20.1"`).

## Full check: PASS

`scripts/check.sh`, run id `20261122T174646Z-52571` (started 2026-11-22T17:46:46Z, 11:46 AM CST; sbt completed 1:08:42 PM CST):

| Gate | Result |
|---|---|
| constitution | PASS (2071 JSON files parse) |
| hooks | PASS (4 scripts, `bash -n` and shellcheck) |
| shell | PASS (27 scripts, `bash -n` and shellcheck) |
| python | PASS (84 files compile) |
| terraform | PASS (6 roots; tests 12, 19, 114, 40, 6, 333 passed, 0 failed) |
| script-tests | PASS (`scripts/tests` 1200 OK, required classes `test_terraform_state_binding.RealStateBindingTests` 7 and `test_terraform_r1.RouteOwnershipTest` 6 executed; `scripts/phase12d-spike/tests` 78 OK; billing 121, 84, 39 OK; `tests/scripts` 487 OK; `tests/infra` 468 OK) |
| sbt | PASS (`sbt -batch check`: test blocks 194, 707, 30 succeeded, 0 failed; 1 canceled in the last block, as the build reports it; total 814 s) |

`RESULT: PASS gates=7`, exit code 0. The marker `.claude/.last-test-run` was updated at 2026-11-22T13:08:42 CST, after the sbt gate completed.

## Targeted checks during Phase 17

| Command | Observed result |
|---|---|
| `python3 -m unittest test_billing_replan_14b.NoRealAccountIdIsAdded` (in `tests/infra`) | Ran 2 tests, OK (after 17D and after the B1 repair; also inside the full check's `tests/infra` suite above) |
| owners' link, number and privacy checks | see `owner-report.md` and `repairs.md` |

## Limits

- Phase 17 changed documentation and records only; no source, build, Terraform or test file changed. The full check proves the repository gates still pass on this tree.
- No AWS, model or network step ran except `terraform init` downloading providers (no AWS API call).
- This is not the course's final gate: `sbt clean check` from a fresh clone of `main`, the README command replay and the grading agents are package 17G, after the merge to `main`.

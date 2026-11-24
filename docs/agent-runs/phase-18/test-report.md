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

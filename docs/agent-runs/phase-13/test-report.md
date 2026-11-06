# Phase 13 test report

## Subphase 13A

All commands ran locally. No AWS call, no real Terraform plan/apply/destroy, no image push or registry login.

| Gate | Command | Observed result | Evidence |
|---|---|---|---|
| JDK | `java -version` (JDK 17 env) | `openjdk version "17.0.20.1" 2026-08-18` | `prompt.md` preflight |
| Shell syntax | `bash -n` + `shellcheck -x -P SCRIPTDIR` on 7 shell files | rc 0, zero findings (shellcheck 0.11.0) | `infra/syntax-shellcheck-r1.txt`, `orchestrator/syntax.txt` |
| Script tests | `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py'` | `Ran 148 tests` … `OK` (infra-engineer; orchestrator rerun 115 s) | `infra/scripts-tests-r1.txt`, `orchestrator/scripts-tests.txt` |
| Root Terraform tests | `terraform init -backend=false -input=false -lockfile=readonly && terraform test` | `40 passed, 0 failed` (before the R1 fix: 39 passed, 1 failed) | `infra/terraform-test-root-r1.txt` |
| check.sh full (first pass) | `scripts/check.sh` | exit 4; terraform gate FAIL (base R1 defect); the other 6 gates PASS | `infra/check-full.txt` |
| check.sh full (final tree) | `scripts/check.sh` | `RESULT: PASS gates=7`, `exit=0 elapsed=992s` | `infra/check-full-r1.txt` |
| check.sh partial | `scripts/check.sh --only shell,constitution,hooks,python` | exit 5, `RESULT: PARTIAL passed=4 skipped: script-tests sbt terraform` | `orchestrator/check-partial-exit5.txt` |
| check.sh clean copy | `--only constitution,hooks,shell,python,script-tests` in a temp copy | 5 gates PASS. The exit code was 0 at the time; it is 5 now, by design | `infra/clean-copy-fast-gates.txt` |
| sbt check (in check.sh) | `sbt -batch check` | PASS 758 s; tests 40, 667, 18 (+1 canceled), 0 failed | `infra/check-full-r1.txt` |
| sbt check (build-engineer) | `sbt -batch check` | exit 0, 759 s; per-module counts in `owner-report.md` | `build/check-jdk17-excerpt.txt` |
| Packaging JDK guard | `sbt -batch packageRelease` under JDK 27 | exit 1, "requires Java 17; found Java 27" | `build/neg-probe-jdk27-packageRelease.txt` |
| Guard spec (live) | `buildVerification/testOnly …PackagingJava17GuardSpec` with a non-17 home | succeeded 6, failed 0 | `build/live-probe-test.txt` |
| package.sh | `scripts/package.sh` | exit 0; 4 linux/amd64 images; arch gate PASS; G5 hash verified | `infra/package-real.txt`, `infra/release-manifest-real.json` |
| deploy dry run | synthetic clean repo with a matching record | `RESULT: DRY-RUN`, exit 0, no cloud command | `infra/dryrun-deploy.txt` |
| deploy refusal (real repo) | `scripts/deploy.sh --region us-east-2 --plan <empty file>` | exit 3, `RESULT: REFUSED step=clean-tree` | `orchestrator/deploy-dirty-refusal.txt` |
| plan, rollback, cleanup dry runs | see files | `RESULT: DRY-RUN`, exit 0 | `infra/dryrun-*.txt` |

### Test-matrix coverage (plan Section 9, 13A rows)

- **Syntax:** `test_syntax.py` (14 tests) asserts that `bash -n` and shellcheck are clean on every script.
- **Dry run:** fake `aws`, `terraform` and `docker` record their argv. Without `--execute`, no mutating command is recorded for plan, deploy, rollback or cleanup. Covered by `test_plan.py`, `test_deploy.py`, `test_rollback.py`, `test_cleanup.py` and `test_safety.py`.
- **Deploy refusals** (`test_deploy.py`, 27 tests): dirty tree; plan checksum mismatch; commit mismatch; missing record; malformed, duplicate or missing-key record; wrong region; wrong account; and a manifest that is dirty, has a commit mismatch, has the wrong architecture or has skipped images. Each case asserts exit 3, a `STEP:` marker naming the check, and no mutating call. The wrong-account case runs the `--execute` path with a fake STS: only the STS call happens and the raw ID never appears.
- **Cleanup:** listing comes before any deletion; a missing or wrong `--confirm` refuses with no destroy invoked.
- **Safety:** fake secret env values and a fake account ID never appear in any output; every step prints a `STEP:` marker; cloud calls are wrapped by the `timeout.py` helper.
- **Timeout helper:** a grandchild process group is killed and the call returns 124; exit codes propagate.
- **check.sh:**
  - A broken real gate (JSON, shellcheck, `bash -n`, hook, python) exits nonzero.
  - Fake sbt and fake Terraform failures propagate.
  - PARTIAL exits 5.
  - The final-tree full run exits 0.
- **Config pins:** environment overrides of the pinned keys are ignored (`CONFIG-IGNORED`). `SCHOLARCHAIN_CONFIG_FILE` is test-only and announced on stdout.
- **R1 negative tests** (`test_terraform_r1.py`, 4 tests): a stray route resource outside `modules/network/` and `spikes/` fails with the R1 message. The same resource under `spikes/`, or inside `modules/network/`, passes.

### Unverified

- Real `plan.sh --execute`.
- `deploy.sh`, `rollback.sh` and `cleanup.sh` `--execute` against AWS.
- `docker push` and ECR login.
- A real Docker-unreachable run (only the fake was exercised).
- The two-pass destroy and the live behaviour of `cleanup_mode` (Phase 14/15 under the human gate).

## Subphase 13A — repair round 1

| Gate | Command | Observed result | Evidence (`evidence/13a/repair-1/`) |
|---|---|---|---|
| Shell syntax | `bash -n` + `shellcheck -x -P SCRIPTDIR` on 18 shell files | rc 0, 0 findings | `shell-syntax-and-shellcheck.txt` |
| Script tests | `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v` | `Ran 281 tests` … `OK`, none skipped. An earlier iteration had 1 failure, since fixed | `unittest-scripts-tests-final.txt`, `unittest-scripts-tests-run1.txt` |
| check.sh partial | `scripts/check.sh --only constitution,hooks,shell,python,script-tests,terraform` | exit 5, `RESULT: PARTIAL passed=6 skipped: sbt` | `check-sh-partial-6-gates.txt` |
| **check.sh full, clean snapshot (F9)** | `scripts/check.sh` in a fresh copy of `git ls-files -co --exclude-standard` | `RESULT: PASS gates=7`, `exit=0` (details below) | `check-full-clean-snapshot.txt`, `clean-snapshot-manifest.txt` |
| Snapshot identity | `cmp` of every working-tree source outside `docs/agent-runs/phase-13` vs the snapshot | compared=5361, differing=0 | `clean-snapshot-manifest.txt` |
| sbt check, working tree | `sbt -batch check` (JDK 17.0.20.1) | exit 0, 725 s; 0 failed (counts below) | `sbt-check-worktree-excerpt.txt` |
| Dry runs | `dry-runs/dryruns-harness.py` (synthetic clean repo, fakes, synthetic receipts) | Every dry run exits 0 `RESULT: DRY-RUN`; both refusal cases exit 3 (details below) | `dry-runs/`, `dry-runs-summary.txt` |

Clean-snapshot gate details:
- script-tests: suites executed 281, 70, 69, 47 and 39 tests, 0 skipped.
- sbt: 40, 667, and 18 + 1 canceled; 0 failed.
- terraform: roots passed 7, 19, 29, 38, 6 and 40; 0 failed.

Working-tree sbt test counts: core 207, hadoop 64, ER 39, spark 50, storage 80, rag 107, services 40, independentTests 667, buildVerification 18 + 1 canceled.

Dry-run details:
- plan: 2 runs.
- deploy: the base-apply, push and runtime-apply stages.
- rollback: app and infra.
- cleanup: 1 run.
- Refused with exit 3: a stale pre-spend receipt, and a dirty tree.

The acceptance-check tests for each finding are listed in `repairs.md` ("Repair round 1 results") and `owner-report.md`.

### Unverified (repair round 1)

All `--execute` paths against real AWS remain unverified, as do:
- live Terraform planning and the targeted teardown (including its dependents and the two-pass sequence);
- ECR push digests and ECS responses;
- a real Docker-unreachable run;
- effective deployer permissions (the Phase 14 access gate).

## Subphase 13A — repair round 2

| Gate | Command | Observed result | Evidence (`evidence/13a/repair-2/`) |
|---|---|---|---|
| Shell syntax | `bash -n` + `shellcheck -x -P SCRIPTDIR` on the 7 release shell files | rc 0, 0 findings. The full shell gate in `check.sh` also passed | `shell-gates.txt` |
| Script tests (working tree) | `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v` | `Ran 434 tests in 641.6s`, `OK`, 0 skipped | `unittest-full.txt` |
| check.sh partial | `scripts/check.sh --only constitution,hooks,shell,python,script-tests,terraform` | exit 5, `RESULT: PARTIAL passed=6 skipped: sbt` | `check-partial.txt` |
| N3 | R1 tests with Terraform only via `TERRAFORM_BIN` | 10/10 executed, 0 skipped | `n3-terraform-bin-only.txt` |
| **check.sh full, clean snapshot** | `scripts/check.sh` in a fresh copy of `git ls-files -co --exclude-standard` (local commit `c93c376`) | `RESULT: PASS gates=7`, `exit=0` (details below) | `check-full-clean-snapshot.txt`, `clean-snapshot-manifest.txt` |
| State-binding tests in the snapshot | `python3 -I -m unittest discover -s . -p test_terraform_state_binding.py -v` (after the terraform gate provided providers) | `Ran 7 tests`, `OK`, 0 skipped | `state-binding-in-snapshot.txt` |
| Snapshot identity | `cmp` of the working tree vs the snapshot (outside `docs/agent-runs/phase-13`) | compared=5367, differing=0 | `clean-snapshot-manifest.txt` |
| sbt check, working tree | `sbt -batch check` (JDK 17.0.20.1) | exit 0, 742 s, 0 failed (counts below) | `sbt-check-worktree-excerpt.txt` |
| Dry runs | `dryruns-harness.py` (synthetic clean repo, fakes) | Every dry run calls only `terraform version`; inspection is printed as deferred; three refusals demonstrated (below) | `dryruns.txt` |

Clean-snapshot gate details:
- script-tests: suites ran 426 + 1 skipped (see the next row), 70, 69, 47 and 39 tests.
- sbt: 40, 667, and 18 + 1 canceled; 0 failed.
- terraform: roots passed 7, 19, 29, 38, 6 and 40; 0 failed.

The skipped item is the class-level skip of `test_terraform_state_binding` in a fresh snapshot, where providers do not exist until the later terraform-gate init. The state-binding row above shows it passing once providers exist.

Working-tree sbt test counts: core 207, hadoop 64, ER 39, spark 50, storage 80, rag 107, services 40, independentTests 667, buildVerification 18 + 1 canceled.

Refusals demonstrated in the dry runs:
- runtime-apply without a push record;
- a symlink at a derived output name;
- a missing live state.

The acceptance-check tests for each finding are listed in `repairs.md` ("Repair round 2 results").

### Unverified (repair round 2)

Every live path remains unverified: real AWS, real Terraform against a real state, ECR push/ECS responses, and the protection attribute names in a real state's `show -json`. Effective deployer permissions and the two-pass teardown are also still unverified.

## Subphase 13A — repair round 3

Verification scope (user decision): this round changed only `scripts/**`. The clean snapshot ran every gate except sbt. The sbt evidence is reused from repair round 2: the clean-snapshot sbt gate passed in 798 s, and the working-tree `sbt -batch check` exited 0 in 742 s with 0 failed. That reuse rests on proof that the inputs are unchanged. The full seven-gate run comes after reviewer approval.

| Gate | Command | Observed result | Evidence (`evidence/13a/repair-3/`) |
|---|---|---|---|
| sbt-input identity | `cmp` of `build.sbt`, `project`, `modules`, `.scalafmt.conf`, `.sbtopts`, `Dockerfile` and `tests` against the repair-2 snapshot | compared=459, differing=0, none missing | `sbt-input-identity.txt` |
| Shell syntax | `bash -n` + `shellcheck -x -P SCRIPTDIR` on all 14 `*.sh` under `scripts/` | 0 failures, 0 findings | `shell-checks.txt` |
| Script tests (working tree) | `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v` | `Ran 529 tests`, `OK`, 0 skipped | `unittest-full.txt` |
| check.sh partial (working tree) | `scripts/check.sh --only constitution,hooks,shell,python,terraform,script-tests` | exit 5 PARTIAL, 6/6 run gates PASS. Required classes executed 7 and 6 | `check-six-gates.txt` |
| **check.sh, clean snapshot** | `scripts/check.sh --skip sbt` in a fresh copy (local commit `eea862df`) | `RESULT: PARTIAL passed=6 skipped: sbt`, `exit=5`, which is expected for `--skip`. Gate and suite details below | `check-clean-snapshot-no-sbt.txt` |
| Snapshot identity | `cmp` of the working tree vs the snapshot (outside `docs/agent-runs/phase-13`) | compared=5371, differing=0 | (this table) |
| Dry runs | `dryruns-harness.py`, 11 transcripts | Each makes 0 calls beyond the Terraform version probe. A live runtime with no binding is refused at `runtime-state` (exit 3) | `dryruns.txt` |

Clean-snapshot gates:
- constitution, hooks, shell, python: PASS.
- terraform (132 s): roots passed 7, 19, 29, 38, 6 and 40.
- script-tests (956 s):
  - `scripts/tests`: Ran 529 (529 executed, 0 skipped tests, 0 skipped classes).
  - `SUITE-REQUIRED`: `RealStateBindingTests` executed 7, and `RouteOwnershipTest` executed 6.
  - Other suites: phase12d-spike 70, billing 69 / 47 / 39.

Because of the new N4 gate order, the real-Terraform classes now run in the clean snapshot (7 and 6 executed, 0 skipped).

### Post-handoff addition

After the handoff, the orchestrator ran the working-tree `sbt -batch check` on JDK 17.0.20.1 so the Claude Code Stop hook would stop blocking. It exited 0 in 752 s with 0 failed. Tests: core 207, hadoop 64, ER 39, spark 50, storage 80, rag 107, services 40, independentTests 667, buildVerification 18 + 1 canceled. Evidence: `evidence/13a/repair-3/sbt-check-worktree-excerpt.txt`.

### Not run this round (by user decision)

- The clean-snapshot sbt gate. The reuse is justified by input identity, and the working-tree run above also passed.
- The full seven-gate default `check.sh`, which is the only mode that enforces the N4 required-class failure. It is deferred until after reviewer approval and before the user's commit.

### Unverified

All live paths, unchanged from repair round 2. In addition: real S3 multipart `ChecksumSHA256` / `get-object-attributes` behaviour, and the runtime-live detection against a real state.

## Subphase 13A — repair round 4

| Gate | Command | Observed result | Evidence (`evidence/13a/repair-4/`) |
|---|---|---|---|
| Shell syntax | `bash -n` + `shellcheck -x -P SCRIPTDIR` on all 14 `*.sh` under `scripts/` | 0 failures, 0 findings | `shell-gates.txt` |
| Script tests (working tree) | `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v` | `Ran 560 tests in 895.486s`, `OK`, 0 skipped | `unittest-discover.txt` |
| sbt check (working tree) | `sbt -batch check` (JDK 17.0.20.1) | exit 0, 749 s; 0 failed (counts below) | `sbt-check-worktree-excerpt.txt` |
| **check.sh full, clean snapshot** | `scripts/check.sh`, the default seven-gate run with no `--only`/`--skip`, in a fresh copy (local commit `2734d34e`) | `RESULT: PASS gates=7`, `exit=0`, 05:16:49Z–05:48:47Z (2026-11-06 UTC); gate details below | `check-full-clean-snapshot.txt` |
| Snapshot identity | `cmp` of the working tree vs the snapshot (outside `docs/agent-runs/phase-13`) | compared=5372, differing=0 | `snapshot-identity.txt` (retained for N6) |
| Dry runs (T1 acceptance) | `dry-runs/dry-runs-harness.py`, 6 rollback dry runs on fixture states | Each makes 0 calls beyond the version probe; outcomes below | `dry-runs/` |

Working-tree sbt test counts: core 207, hadoop 64, ER 39, spark 50, storage 80, rag 107, services 40, independentTests 667, buildVerification 18 + 1 canceled.

Clean-snapshot gates:
- constitution, hooks, shell, python: PASS.
- terraform (128 s): roots passed 7, 19, 29, 38, 6 and 40.
- script-tests (974 s):
  - `scripts/tests`: Ran 560 (560 executed, 0 skipped tests, 0 skipped classes).
  - `SUITE-REQUIRED`: `RealStateBindingTests` executed 7, and `RouteOwnershipTest` executed 6. In this default full run, N4 enforcement was active.
  - Other suites: phase12d-spike 70, billing 69 / 47 / 39.
- sbt (806 s): 40, 667, 18 + 1 canceled; 0 failed.

Dry-run outcomes:
1. Post-base-apply state, no binding: accepted (DRY-RUN).
2. Post-base-apply state with a manifest binding: REFUSED at `runtime-state`, "would CREATE the runtime".
3. Post-base-apply state with a push-record binding: REFUSED at `runtime-state`, "would CREATE the runtime".
4. Partial state: REFUSED, `RUNTIME-LIVE-CHECK-FAILED`.
5. Live state with a manifest binding: DRY-RUN.
6. Live state with no binding: REFUSED.

### Unverified (repair round 4)

All live paths remain unverified, including the real state v4 layout used for runtime-live detection.

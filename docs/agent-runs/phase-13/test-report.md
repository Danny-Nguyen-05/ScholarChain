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

# Subphase 13B

The base SHA is `52c2e21`. Evidence is in `evidence/13b/{infra,test,orchestrator}/`. All commands ran locally. There was no AWS call, no EMR step, no real Terraform plan or apply, and no image push.

## Gates

| Gate | Command | Observed result | Evidence |
|---|---|---|---|
| Shell syntax | `bash -n` + `shellcheck -x -P SCRIPTDIR` on all 19 `*.sh` under `scripts/` (23 tracked or untracked repo-wide; none under `docs/`) | 0 failures, 0 findings | `infra/shell-gates-r1.txt` |
| scripts/tests (infra) | `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v` | `Ran 745`, 1 failure (see below) | `infra/unittest-scripts-tests-r1.txt`, `infra/unittest-test_check-fast-r1.txt` |
| tests/scripts (independent) | `python3 -I -m unittest discover -s tests/scripts -p 'test_*.py' -v` | `Ran 198 tests in 547.027s`, `OK`, 0 skips, 0 expected failures | `test/unittest-tests-scripts-v-r1.txt` |
| sbt check (working tree) | `sbt -batch check` (JDK 17) | exit 0, 792 s, 0 failed | `orchestrator/sbt-check-worktree-excerpt.txt` |
| **check.sh full, clean snapshot** | `scripts/check.sh` (default seven gates) in a fresh copy, local commit `0a5bd0d3` | see "Clean-snapshot result" below | `orchestrator/check-full-clean-snapshot.txt` |

### Clean-snapshot result

The full seven-gate `scripts/check.sh` in the clean snapshot ended `RESULT: PASS gates=7`, `exit=0`, 09:52:26Z–10:38:10Z (2026-11-06 UTC).

| Gate | Result |
|---|---|
| constitution, hooks, shell, python | PASS |
| terraform (116 s) | roots passed 7, 19, 29, 38, 6 and 40 |
| script-tests (1793 s) | `scripts/tests` 745, `phase12d-spike` 73, billing 69 / 47 / 39, `tests/scripts` 198 executed. Every suite had 0 skipped tests and 0 skipped classes. The required real-Terraform classes ran. |
| sbt (827 s) | 40, 667, 18 + 1 canceled; 0 failed |

Snapshot identity: 5409 files compared, 0 different (`orchestrator/snapshot-identity.txt`).

The one `scripts/tests` failure was `test_real_repository_fast_gates_pass`, caused by the orchestrator's evidence copy `retain_pipeline.sh` (SC2004). It was renamed to `.sh.txt`, and the re-run of `CheckFastGatesTests` was 11 OK.

## Behaviour evidence (infra-engineer, `evidence/13b/infra/`)

**Pipeline**
- Dry run (`pipeline-dry-run-full.txt`, exit 0):
  - 6 `aws emr add-steps` commands are printed, never run.
  - The Spark step carries every decision 12-10 setting, with the driver and executor class-origin step before it.
  - The YARN tag kill on timeout, the step timeouts and the auto-termination checks are all printed.
  - `ESTIMATE-USD: 1.08`.
- Refusals, each exit 3 with no cloud call (`guard-aws-calls.txt` is empty):
  - capacity;
  - the G6 per-run cap (5.76 > 3.00);
  - budget;
  - a Phase 4 ceiling;
  - `--execute` with unconfirmed pricing (`pipeline-execute-refused-unconfirmed-pricing.txt`).

**Experiment** (temp git repo)
- The committed fixture manifest dry-runs.
- Untracked, modified, missing-budget and missing-teardown manifests are each refused with exit 3.

**Smoke**
- Stub server: healthy and async pass. Readiness, evidence, idempotency and error-path failures each exit 4 with their own STEP marker.
- **Real local `query-api`** (offline-synthetic, throwaway key, only its sha256 passed to the service): all 6 checks PASS, and no key appears in the output (`smoke-local-real.txt`).

**Archive** (`archive-real-run.txt`, real run into a temp dir)
- 7 files copied, 2 indexed externally; the G5 tgz is indexed with sha256 `789a96…6de5`.
- The tar has 0 `._` members; S3 commands are printed only.

**Carried items**
- Item 31: the 3 new tests fail on the pre-fix script (`item31-before-fix.txt`) and pass after the fix.
- Item 1 (YARN kill by run tag on exit 124, 137 or 143) is proven against fakes. A mutation check (a no-op kill) makes the test fail.

## Test-matrix coverage (plan §9, 13B rows)

Independent `tests/scripts` (198 tests) covers every row:
- pipeline ceilings and G6 refusals (per-run cap, cumulative 9.50, 3 runs, unconfirmed or missing rates);
- each approval key mismatch, and the APPROVED_ACTION cross-use both ways;
- an unknown `APPROVED_*` key;
- pre-spend refusals, including expiry mid-run;
- cluster refusals;
- forced auto-termination and the runtime cap in the printed commands;
- YARN kill by tag;
- the Spark 12-10 settings and the class-origin gate;
- no `create-cluster` or `run-job-flow` (the Terraform-only rule);
- experiment manifest refusals and record fields;
- smoke pass/fail markers;
- archive thresholds (1 MiB inclusive), no `._`, no overwrite, redaction;
- usage errors with markers in all 11 scripts;
- no canary secret in any output;
- 13A regressions.

The full mapping table is in the test-engineer report, summarized in `owner-report.md`.

## Findings fixed inside 13B

The independent tests found D1, O1, O2, O3 and O4. All five were fixed by infra-engineer and their tests converted to normal tests. That left 0 expected failures (see `owner-report.md`).

## Unverified

- Every live path: an EMR step, HadoopPrepMain on EFS `file://`, real YARN `-appTags` list and kill, G2/G3/G4, the real class-origin probe output, and real ECS/S3 behaviour.
- Pricing has not been confirmed by the human (`EMR_PRICING_CONFIRMED_BY_HUMAN=false`).
- The ER step has no packaged JAR yet (build-engineer gap).

## Subphase 13C — final verification

Base `56144457f38e29b7c6211e040dd1fb15270a50bf`; all 13C work uncommitted at handoff. By user decision the clean-snapshot `check.sh` and the working-tree `sbt check` ran in parallel; both are full runs.

### Gates (orchestrator-observed)

| Gate | Result | Evidence |
|---|---|---|
| Full default seven-gate `scripts/check.sh` in a clean snapshot (local commit `919a3026a1185dad0f49e351c189c5e54b40d973`), 2026-11-06T18:13:15Z–19:10:35Z | `RESULT: PASS gates=7`, exit 0 | `evidence/13c/orchestrator/check-full-clean-snapshot.txt` |
| terraform gate (142 s) | 7 / 19 / 37 / 40 / 6 / 69 passed, 0 failed (deployer 37, spike 40, main 69) | same |
| script-tests gate (2515 s) | `scripts/tests` 831; `scripts/phase12d-spike/tests` 73; billing 69 / 47 / 39; `tests/scripts` 256; `tests/infra` 126. Every suite: all executed, 0 skipped tests, 0 skipped classes, 0 failures. SUITE-REQUIRED `RealStateBindingTests` executed=7, `RouteOwnershipTest` executed=6 | same |
| sbt gate (773 s) | 40 / 667 / 18 (+1 canceled), 0 failed | same |
| Snapshot identity (working tree vs snapshot, excluding `docs/agent-runs/phase-13/`) | compared=5430 differing=0 | `evidence/13c/orchestrator/snapshot-identity.txt` |
| Working-tree `sbt -batch check`, JDK 17.0.20.1 | exit 0, 764 s, 0 failed in every group | `evidence/13c/orchestrator/sbt-check-worktree-excerpt.txt` |

The `[error] (checkProbeInjectFailure)` line in the sbt output is the build's own injected-failure probe, as in 13A and 13B.

### Agent-observed results (raw logs in `evidence/13c/infra/` and `evidence/13c/test/`)

- infra-engineer: shellcheck 0 findings; terraform fmt/validate clean on every root; 37 + 3 mutations detected and reverted (`mutation-results.jsonl`, `followup-mutation-results.jsonl`).
- test-engineer: pass 1 (60 tests, 21 mutations), pass 2 (52 infra + 13 script mutations), pass 3 final `tests/infra` 126 and `tests/scripts` 256, 0 skips, 0 expected failures (`pass3-*`).

### Test-matrix coverage (plan §9 and 13C "Done when")

| Requirement | Covered by |
|---|---|
| Main EMR module matches decision 12-10 | `infra/terraform/tests/phase13c.tftest.hcl` (Hadoop only, emr-7.8.0, Spark settings equal `spark-12-10.conf`, TLS off/at-rest on, EFS, G3 defaults, G6 caps, idle ≤ 900); independent `tests/infra/test_emr_module_13c.py` |
| Item 17 and items 2, 5, 14, 16, each with a test that fails on the old policy | deployer/spike/phase13c runs plus `tests/infra/test_iam_items_13c.py`; mutations in both agents' evidence. Item 16 is a mitigation (no IAM condition key on the trust document) |
| Test gaps 6, 7, 10, 12, 20, 21 | `tests/infra/test_spike_hardening.py`, `test_deployer_hardening.py`, `test_guard_conditions.py`, `test_static_sources.py` |
| Bootstrap items 8, 28, 29 | `scripts/tests/test_emr_bootstrap.py`; independent `tests/scripts/test_bootstrap_13c.py` |
| 13B findings B1–B5 | `scripts/tests/test_13c_pipeline.py`, `test_budget.py`, `test_check.py`; independent `tests/scripts/test_pipeline_ledger_13c.py`, `test_pipeline_bodies.py`, `test_pipeline_refusals.py` |
| Fake-binary dry-run contract and refusals unchanged | full `scripts/tests` and `tests/scripts` suites |
| Nothing applied | no apply, plan with real credentials, upload or AWS call by any agent or the orchestrator |

### Findings fixed inside 13C

test-engineer pass 2 found three production defects; two were fixed by infra-engineer (copy-out with missing parts; TERM-ignoring grandchild after a step timeout). The third (task-group gp3 throughput) is a provider limitation: `aws_emr_instance_group.ebs_config` has no `throughput` in hashicorp/aws 6.44.0; it is documented and asserted by a schema test.

### Unverified (live)

The bootstrap on real EMR nodes (runtime install, Java resolution, EFS mount, `amazon-efs-utils` and S3 egress from the private subnet), the item 17 stack-tag condition against EMR-created ENIs, the process-group kill and EMR cancel-steps signalling on a node, the effective deployer permissions, G2/G3/G4. Pricing is still unconfirmed by the human. No real plan was run.

## Subphase 13C — repair round 1

Base `56144457f38e29b7c6211e040dd1fb15270a50bf`; all 13C and repair work uncommitted. Findings C1–C4 from 13C review 1 (`review.md`, `repairs.md`).

### Gates (orchestrator-observed)

Clean snapshot of `git ls-files -co --exclude-standard` (local commit `3093334fc04ebd5b3acef729bc5ded174bc16470`), JDK 17 environment, jobs in parallel (user decision 13C), 2026-11-06T21:24:10Z–21:47:56Z. Evidence: `evidence/13c/orchestrator/repair1-verification.txt`.

| Command (in the snapshot) | Exit | Result |
|---|---|---|
| `scripts/check.sh --skip sbt,script-tests` | 5 (PARTIAL by design: two gates skipped and run separately below) | constitution, hooks, shell, python, terraform PASS; terraform test 7 / 19 / 37 / 40 / 6 / 77 passed, 0 failed (main root 77 = 69 + 8 new) |
| `python3 -I scripts/lib/suite_run.py --start-dir scripts/tests --pattern 'test_*.py'` | 0 | ran=856 executed=856 skipped_tests=0 skipped_classes=0 failures=0 errors=0 (13C: 831; +25 `test_c1_step_args.py`) |
| `python3 -I scripts/lib/suite_run.py --start-dir tests/scripts --pattern 'test_*.py'` | 0 | ran=276 executed=276 skipped 0, failures=0 errors=0 (13C: 256; +20 `test_step_arg_limit_13c.py`) |
| `python3 -I scripts/lib/suite_run.py --start-dir tests/infra --pattern 'test_*.py'` (after the terraform gate) | 0 | ran=128 executed=128 skipped 0, failures=0 errors=0 (13C: 126) |
| `python3 -I scripts/lib/suite_run.py --start-dir scripts/phase12d-spike/tests --pattern 'test_*.py'` | 0 | ran=73 executed=73 skipped 0, failures=0 errors=0 |
| `python3 -I scripts/billing/tests/test_{budget_execution,budget_verification,publication_evidence}.py` (one process per file, as check.sh does) | 0 | 69 / 47 / 39 OK |
| Snapshot identity (working tree vs snapshot, excluding `docs/agent-runs/phase-13/`) | — | compared=5437 differing=0 (`evidence/13c/orchestrator/repair1-snapshot-identity.txt`) |

The snapshot is a committed git repository, so `RouteOwnershipTest` sees the untracked `efs.tf`, `emr-step-programs.json` and `phase13c.tftest.hcl` and passes there without `git add -N`.

**sbt gate: reused, not rerun.** No `build.sbt`, `project/**`, `modules/**` or `.scalafmt.conf` input changed in this round: 335 such paths compared against the 13C clean snapshot `919a3026…` whose sbt gate passed (40 / 667 / 18 (+1 canceled), 0 failed; `evidence/13c/orchestrator/check-full-clean-snapshot.txt`), 0 differing, none missing; `git status --porcelain` and `git diff 5614445` on those paths are empty (`evidence/13c/orchestrator/repair1-sbt-input-identity.txt`). This follows the user's recorded preference for repair rounds (skip sbt when its inputs are unchanged; one full `check.sh` after approval). The seven-gate default `check.sh` was therefore not rerun as one command in this round.

### Agent-observed results

- infra-engineer: `scripts/tests` 856 OK; shellcheck 0 findings; main root fmt/validate/test 77 passed; four mutations caught and restored byte-identically (`evidence/13c/infra/repair1-mutation-*.txt`); maximum-length dry run with per-argument lengths (`evidence/13c/infra/repair1-dry-run-arg-lengths.txt`).
- test-engineer: `tests/scripts` 276 OK, `tests/infra` 128 OK; arg-limit mutation caught and restored (`evidence/13c/test/repair1-*.txt`).

### Repair coverage

| Finding | Acceptance check | Covered by |
|---|---|---|
| C1 (High, blocking) | (a) refusal before any cloud call, dry run and execute | `STEP: arg-limit` before `g6-gate`, ledger and approval; `scripts/tests/test_c1_step_args.py` `OversizeRefusalTests`; independent `tests/scripts/test_step_arg_limit_13c.py` (10,281 refused with exit 3, empty fake-binary log; `--execute` leaves the ledger byte-identical and the approval unconsumed) |
| | (b) every step under the limit without weakening B1 or item 1 | longest argument 1,043 characters at maximum values; B1 wrapper and process-group kill, YARN kill by tag and class-origin fail-closed moved verbatim into `scripts/emr/sc-step.sh` and still exercised by `tests/scripts/test_pipeline_bodies.py` (31 tests) running the printed command against installed programs; launcher and program sha checks with tamper tests |
| | (c) maximum-length realistic fixture values | 63-character bucket, ~900-character keys, 64-character run id, `j-` + 32, 128-character dataset tokens; launcher and parameter boundaries at exactly 10,280 / 10,281 |
| | (d) retained dry run with per-step argument lengths | `evidence/13c/infra/repair1-dry-run-arg-lengths.txt` (`STEP-ARG-LENGTHS` lines and an old-vs-new table) |
| C2 (Low) | runtime hash must equal the 12-10 pin; negative test | root and module validations; `phase13c.tftest.hcl` negative + positive runs; `tests/infra/test_emr_module_13c.py` (three cases) |
| C3 (Trivial) | ledger comment corrected | `scripts/config/release.conf` comment names `~/.scholarchain/emr-ledger/runs.jsonl` |
| C4 (Low) | ~1 MB failing logs replaced by excerpts | `evidence/13c/infra/{pipeline-run1,pipeline-run2,tests-scripts-run,test_experiment-run3}.txt` excerpts with original size and sha256; directory 232K |

### Unverified (live)

Unchanged from 13C, plus: the bootstrap installing the four step programs on real nodes, the on-node launcher and runner under `command-runner.jar`, and AL2023 `sha256sum`/`python3` availability. The 10,280-character limit is taken from the review and AWS documentation, not observed live.

Addendum (after the handoff, to clear the Claude Code stale-marker Stop hook): working-tree `sbt -batch check` on JDK 17 with no source change since the snapshot: exit 0, 724 s; groups 207 / 64 / 39 / 50 / 80 / 107 / 40 / 667 / 18 (+1 canceled) succeeded, 0 failed; the only `[error]` line is the build's injected `checkProbeInjectFailure` probe. `evidence/13c/orchestrator/repair1-sbt-check-worktree-excerpt.txt`.

## Subphase 13C — final verification (after the repair round 1 APPROVE)

Base `56144457f38e29b7c6211e040dd1fb15270a50bf`; all 13C work uncommitted. Requested by the reviewer's next prompt (Review 2) and the user's recorded "one full check after approval"; satisfies plan Section 11 "fresh `sbt check` on JDK 17". No AWS credentials, no cloud call.

| Item | Result | Evidence |
|---|---|---|
| Command | `scripts/check.sh` (default seven gates, no `--only`/`--skip`) in a clean snapshot of `git ls-files -co --exclude-standard` (local commit `564f399a89182cee5a6941e9749d4b11ca90d83b`); JDK 17.0.20.1; 2026-11-06T22:16:29Z–23:18:03Z | `evidence/13c/orchestrator/final-check-full-clean-snapshot.txt` (ANSI stripped) |
| Exit / result | exit 0, `RESULT: PASS gates=7` | same |
| constitution, hooks, shell, python | PASS (1 s, 0 s, 7 s, 1 s) | same |
| terraform (114 s) | 7 / 19 / 37 / 40 / 6 / 77 passed, 0 failed | same |
| script-tests (2795 s) | `scripts/tests` 856; `scripts/phase12d-spike/tests` 73; billing 69 / 47 / 39; `tests/scripts` 276; `tests/infra` 128. Every suite all executed, 0 skipped tests, 0 skipped classes, OK. SUITE-REQUIRED `RealStateBindingTests` executed=7, `RouteOwnershipTest` executed=6 | same |
| sbt (776 s) | 40 / 667 / 18 (+1 canceled) succeeded, 0 failed; the `[error] (checkProbeInjectFailure)` line is the build's injected probe | same |
| Snapshot identity (working tree vs snapshot, excluding `docs/agent-runs/phase-13/`) | compared=5437 differing=0 | `evidence/13c/orchestrator/final-snapshot-identity.txt` |

R1 (nonblocking, Review 2): `evidence/13c/infra/repair1-tests-scripts-run.txt` and `repair1-tests-scripts-with-manifest-copied.txt` now start with a one-line "INTERMEDIATE … superseded" header.

### Plan Section 11 checklist (orchestrator status; the human gate is the user's)

| Item | Status | Evidence |
|---|---|---|
| Each subphase reviewed by a user-launched reviewer; verdicts in `review.md` | done | `review.md`: 13A Review 5 APPROVE, 13B Review 1 APPROVE, 13C Review 2 APPROVE |
| A clean checkout runs all non-cloud validation through `check.sh` | done | `evidence/13c/orchestrator/final-check-full-clean-snapshot.txt` |
| Terraform planning scripted; plan checksum archived by the script | done (offline; no real plan run) | `scripts/plan.sh`; `evidence/13a/infra/dryrun-plan.txt`; 13A test-report |
| Deployment refuses without the documented human approval (tested refusals) | done | `scripts/tests` deploy refusal tests; `evidence/13a/orchestrator/deploy-dirty-refusal.txt`, `evidence/13a/infra/dryrun-deploy.txt` |
| Smoke exercises a bounded collaboration query and an evidence fetch | done locally (offline-synthetic service); live smoke is Phase 14 | `evidence/13b/infra/smoke-local-real.txt`, `smoke-stub-*.txt` |
| Spark EMR step and Hadoop/ER steps in `run-bounded-pipeline.sh`; dry runs retained; live run is Phase 15 experiment A | done | `evidence/13b/infra/pipeline-dry-run-full.txt`, `evidence/13c/infra/repair1-dry-run-arg-lengths.txt` |
| Every cloud-touching script defaults to dry run; none executed live | done | fake-binary suites; no live call recorded in any owner report |
| Main EMR module matches decision 12-10; TLS decision; G1, G5, G6 recorded | done | `infra/terraform/tests/phase13c.tftest.hcl`; `prompt.md` Step 0 (13A, 13C) |
| Items 17, 2, 5, 14, 16 closed with negative tests; gaps 6, 7, 10, 12, 20, 21 and script items 1, 31 closed | done; 16 mitigated only (no IAM condition key on the trust document) | `evidence/13c/carried-findings-status.md` |
| `scripts/README.md` lists prerequisites, environment names, approval points, evidence and rollback | done | `scripts/README.md` |
| Fresh JDK 17 `sbt check` passes; reviewer APPROVE; human wrote `human-gate.md` and `commit.txt` | sbt and APPROVE done; **human gate open** | this section; `review.md` |
| Next action: Phase 14 pre-flight | not started (by instruction) | — |

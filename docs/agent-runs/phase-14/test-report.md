# Phase 14 test report

## Subphase 14A

The coordinator ran every command below and recorded the results as observed (D3). Agent-reported numbers are not used here. Everything ran offline: no AWS call, no Docker build, no real plan or apply.

- Base: `b2cd7ee99dcc136b5c8ec0667ca181cc5b3a87fd` on branch `phase-14`.
- Toolchain: JDK 17.0.20.1, Terraform v1.13.5, Python 3.14.5.
- AWS environment neutralized for every run:
  - `AWS_PROFILE` unset;
  - `AWS_EC2_METADATA_DISABLED=true`;
  - `AWS_CONFIG_FILE` and `AWS_SHARED_CREDENTIALS_FILE` set to `/dev/null`;
  - `check.sh` also redacts these itself.

### 1. Clean-snapshot procedure

1. `git clone` the repository into the session scratchpad.
2. `rsync` every file from `git ls-files -m -o --exclude-standard` into the clone.
3. Commit there with throwaway author `snapshot`.
4. Prove identity: `cmp` every file tracked in the snapshot against the live tree, and list live files missing from the snapshot.

| Snapshot | Commit | Identity at creation |
|---|---|---|
| 1 (before D6) | `e690b5054be5807a66cae01a8afe0ea0c5ba43d6` | 5652 files, 0 differing, 0 missing |
| 2 (after D6) | `ba2636c22bd7e4b9bf3e25a4223aa19597d53ac4` | 5658 files, 0 differing, 0 missing |

Identity re-proved after run 2 finished:
- Non-docs files: 5635 compared, 0 differing.
- Changed after the snapshot, both evidence-only text with no effect on any gate input:
  - `docs/agent-runs/phase-14/owner-report.md`;
  - `docs/agent-runs/phase-14/evidence/14a/carried-findings-status.md`.
- Added after the snapshot:
  - `evidence/14a/gates/check-full-run2.txt`;
  - `evidence/14a/gates/sbt-check-live-after-d6-summary.txt`;
  - this file and `approval-request-14a.md` Sections 3 and 7, also edited after the snapshot.

### 2. Full seven-gate check, run 1: FAIL (snapshot 1)

```text
cd <snapshot1> && env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

| Gate | State | Time |
|---|---|---|
| constitution | PASS | 1s |
| hooks | PASS | 0s |
| shell | PASS | 7s |
| python | PASS | 0s |
| terraform | PASS | 121s |
| script-tests | **FAIL** | 2907s |
| sbt | PASS | 775s |

The run ended `RESULT: FAIL failed: script-tests` with `EXIT: 4`.
- **Failure:** in `scripts/phase12d-spike/tests` (73 run, failures=1), the test `test_terraform_static.DefaultSecurityGroupTests.test_every_ec2_create_tags_has_a_create_action_condition` failed with `AssertionError: 'ec2:CreateAction' not found`. The match was the `ec2:CreateTags` statement on `security-group/*` in `infra/terraform/deployer/phase14_main.tf`, Sid `Ec2AdoptedDefaultSgFirstTags`.
- **Other suites in that gate all passed:** scripts/tests 856, billing 69/47/39, tests/scripts 276, tests/infra 223.
- **Cause:** neither agent ran this suite in rounds 1–2. infra-engineer ran `check.sh --only terraform`; test-engineer ran `tests/infra`.
- **Repair:** the user chose a named exception (D6 in `prompt.md`), and infra-engineer applied it in round 3 (`owner-report.md`).

Evidence: `evidence/14a/gates/check-full-run1.txt` and `check-full-run1-phase12d-spike-failure.txt`.

### 3. Full seven-gate check, run 2: PASS (snapshot 2, after D6)

```text
cd <snapshot2> && env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

The run took 2026-11-07T07:53:13Z to 08:56:53Z.
- `RESULT: PASS gates=7`.
- The wrapper exit code was 0.

| Gate | State | Time | Observed counts |
|---|---|---|---|
| constitution | PASS | 1s | — |
| hooks | PASS | 0s | — |
| shell | PASS | 7s | — |
| python | PASS | 0s | `python: 66 files compile` |
| terraform | PASS | 115s | `fmt -check -recursive` clean; init (`-backend=false -lockfile=readonly`), validate and test per root. Results below. |
| script-tests | PASS | 2921s | Suite results below. |
| sbt | PASS | 776s | `sbt -batch check` under JDK 17. Results below. |

Terraform test results per root:
- billing-bootstrap: 7 passed, 0 failed;
- billing-execution: 19 passed, 0 failed;
- **deployer: 61 passed, 0 failed**;
- spikes/emr-spark-isolated: 40 passed, 0 failed;
- spikes/emr-spark: 6 passed, 0 failed;
- **root: 106 passed, 0 failed**.

Script-test suite results:
- scripts/tests: 856 run, 856 executed, OK. Required classes:
  - `RealStateBindingTests` executed=7;
  - `RouteOwnershipTest` executed=6.
- **scripts/phase12d-spike/tests: 82 run, 82 executed, OK.**
- scripts/billing/tests:
  - `test_budget_execution`: 69 executed, OK;
  - `test_budget_verification`: 47 executed, OK;
  - `test_publication_evidence`: 39 executed, OK.
- tests/scripts: 276 run, 276 executed, OK.
- **tests/infra: 223 run, 223 executed, OK.**
- No test or class was skipped in any of these suites.

sbt results:
- The final aggregate lines read `Tests: succeeded 40`, `succeeded 667`, and `succeeded 18, canceled 1`, all with 0 failed.
- `[success] Total time: 770 s`.
- The `checkProbeInjectFailure ... injected format-stage failure` line is the build's expected self-test.

Evidence: `evidence/14a/gates/check-full-run2.txt`, sanitized (snapshot path and temp paths replaced; no account ID present). The raw log is at `target/phase14/evidence/14a-gates/check-full-clean-snapshot2.txt`.

### 4. sbt check in the live tree (test marker)

| Run | When it finished | Command | Result |
|---|---|---|---|
| Interim, before test-engineer and D6 | 2026-11-07 00:16:06 CST | `sbt -batch check` (JDK 17) | EXIT 0; succeeded 207/64/39/50/80/107/40/667/18, 0 failed, 1 canceled; `[success] Total time: 737 s` |
| After D6 | 2026-11-07 02:05:37 CST | `sbt -batch check` (JDK 17) | EXIT 0; succeeded 207/64/39/50/80/107/40/667/18, 0 failed, 1 canceled; `[success] Total time: 734 s` |

`.claude/.last-test-run` modification time after the second run: `2026-11-07T02:05:37-0600`. It was later than every source edit: the last one was the D6 test file, which was before snapshot 2.

Evidence: `evidence/14a/gates/sbt-check-live-after-d6-summary.txt`.

### 5. Dry runs (Q14), at preflight on the base tree

Every `scripts/plan.sh` and `scripts/deploy.sh` run used dry-run mode, with no `--execute`. The scripts have not changed since; the only `scripts/**` change in 14A is the D6 test file.

| Command | Result |
|---|---|
| `scripts/plan.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --expect-new-state` | `RESULT: DRY-RUN`, no aws or terraform command run, EXIT 0 |
| `scripts/plan.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --image-revision b2cd7ee…` | `RESULT: DRY-RUN`, EXIT 0 |
| `scripts/deploy.sh --stage base-apply --plan target/phase14/plans/base.tfplan --region us-east-2 --profile …`, no record | `REFUSED step=approval-record`, EXIT 3 |
| `scripts/deploy.sh --stage push …`, no record | `REFUSED step=approval-record`, EXIT 3 |
| `scripts/deploy.sh --stage runtime-apply --plan target/phase14/plans/runtime.tfplan …`, no record | `REFUSED step=approval-record`, EXIT 3 |
| `deploy.sh --stage base-apply`, synthetic record and receipt (`target/phase14/dryrun-synthetic/`) | passes the record checks; `REFUSED step=plan-checksum` (no plan file), EXIT 3 |
| `deploy.sh --stage push`, synthetic record | `REFUSED step=release-manifest` (run `package.sh` first), EXIT 3 |
| `deploy.sh --stage runtime-apply`, synthetic record | `REFUSED step=plan-checksum`, EXIT 3 |

The synthetic records exist only in git-ignored `target/` and are not approvals. Evidence: `evidence/14a/dryrun/*.txt`.

### 6. Other checks

- `git diff --check` on the final tree: exit 0.
- Pin drift (D3, Q12):
  - **Computation:** a Python stdlib comparison of `scripts/billing/reviewed-pins.json` `source_freeze` (size and sha256) against the final tree.
  - **Result:** 209 pinned, **20 drifted**. The list, with pinned and current values, is in `evidence/14a/pin-drift.txt`; the computation was repeated after D6 with the same 20 files.
  - **D6 file:** `scripts/phase12d-spike/tests/test_terraform_static.py` is not pinned.

### 7. What was not re-run by the coordinator

These are agent-reported and recorded in `owner-report.md` and `evidence/14a/infra|test/`:
- the mutation campaigns: infra deployer 34 (33 caught by the deployer suite, M32 by root), infra root 37/37, test-engineer infra 52/52, guard 11/11;
- the D6 exemption mutations (9 in-suite tests).

The in-suite mutation tests ran inside run 2: D6 is inside the 82, and the guard self-test is inside tests/infra and sbt. The separate scripted mutation campaigns were not repeated.

No live AWS behavior was observed. IAM authorization, quotas, model access, budgets, secrets and Cost Explorer are unverified offline.

## Subphase 14A — repair round 1 (review 1)

The coordinator ran every command below and recorded what it observed. Everything ran offline, with the AWS environment neutralized as in Subphase 14A.

### R1. Clean snapshot

| Snapshot | Commit | Identity |
|---|---|---|
| 3 (after F1, F2, F5 and the stale-test repair) | `c4dbd00ea8dbf2eaf1c5300836cb8dd8e5713751` | At creation: 5675 files, 0 differing, 0 missing, no deleted tracked files. After the run: 5647 non-docs files, 0 differing; nothing outside `docs/agent-runs/phase-14/` is missing. |

Only coordinator evidence and reports under `docs/agent-runs/phase-14/` changed after the snapshot.

### R2. Full seven-gate check: PASS (snapshot 3)

```text
cd <snapshot3> && env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

The run took 2026-11-07T18:36:44Z to 19:45:12Z.
- `RESULT: PASS gates=7`.
- The wrapper exit code was 0.

| Gate | State | Time | Observed counts |
|---|---|---|---|
| constitution | PASS | 1s | — |
| hooks | PASS | 0s | — |
| shell | PASS | 9s | — |
| python | PASS | 0s | `python: 66 files compile` |
| terraform | PASS | 139s | Per-root results below. |
| script-tests | PASS | 3158s | Per-suite results below. |
| sbt | PASS | 801s | `[success] Total time: 792 s`. Aggregate lines below. |

Terraform test results per root:
- billing-bootstrap: 7 passed, 0 failed;
- billing-execution: 19 passed, 0 failed;
- **deployer: 62 passed, 0 failed**;
- spikes/emr-spark-isolated: 40 passed, 0 failed;
- spikes/emr-spark: 6 passed, 0 failed;
- **root: 117 passed, 0 failed**.

Script-test suite results:
- scripts/tests: 856 OK. Required classes:
  - `RealStateBindingTests` executed=7;
  - `RouteOwnershipTest` executed=6.
- **scripts/phase12d-spike/tests: 78 OK.**
- billing: 69/47/39 OK.
- tests/scripts: 276 OK.
- **tests/infra: 246 OK.**
- No test or class was skipped.

sbt aggregate lines:
- `succeeded 90` (services);
- `succeeded 667`;
- `succeeded 18, canceled 1`;
- all with 0 failed.

Evidence: `evidence/14a/gates/check-full-r1.txt`, sanitized (snapshot and temp paths replaced; it contains no 12-digit number). The raw log is at `target/phase14/evidence/14a-gates/check-full-clean-snapshot3.txt`.

### R3. sbt check in the live tree

This ran in parallel with R2, on the same sources.

```text
JAVA_HOME=<JDK 17> env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null sbt -batch check
```

- EXIT 0.
- Succeeded 207/64/39/50/100/107/90/667/18, with 0 failed and 1 canceled.
- `[success] Total time: 741 s`.
- The test marker was updated at `2026-11-07T12:49:08-0600`.

Evidence: `evidence/14a/gates/sbt-check-live-r1-summary.txt`.

### R4. Other checks

- `git diff --check` on the final tree: exit 0.
- Pin drift: 209 pinned files, **23 drifted** (20 before repair round 1). The 3 new ones are `infra/terraform/modules/runtime/{compute,outputs,variables}.tf`. The full list is in `evidence/14a/pin-drift.txt`.
- None of the new or changed service, storage, `tests/infra` or `scripts/phase12d-spike` files is pinned.

### R5. Not re-run by the coordinator

- **Agent-reported mutation campaigns:**
  - infra deployer: 40 mutations, 39 caught by the deployer suite and M32 by root;
  - root F2: 46/46 caught;
  - root F1: 19/19 caught;
  - test-engineer: 113/113 caught.
- **Where the in-suite tests ran:** inside R2 and R3. The new services and storage specs are inside sbt, and `Phase14F2InMemory` is inside tests/infra.
- **Transient test-engineer failures:** test-engineer reported 5 failures in one run while infra files were mid-edit; R2 ran on a fixed snapshot and passed.
- **No live AWS behavior observed:** IAM and the key-policy lockout check, Neptune row shapes, Bedrock access, S3 HEAD under `Null s3:prefix` (P14-7), and readiness in ECS are all unverified.

## Final pre-commit check (after the pin update)

The user regenerated the 23 drifted `source_freeze` rows of `scripts/billing/reviewed-pins.json` on 2026-11-07.

- Diff: 46 changed lines, all `bytes` or `sha256` values; no other line changed.
- Pin drift after the edit: 209 pinned files, **0 drifted**.
- New `reviewed-pins.json` sha256: `9ac22d7e3839e5d2d00366deaafb5512ab5f93150c71a13bc657a29d72a89ef6`.
- Because `source_freeze` feeds billing `wrapper_files`, a later billing verify or readback needs a new billing gate.

### F1. Full seven-gate check in clean snapshot 4

- Snapshot 4: commit `bc59d8aa9c333f4f4d5a99baea16612b6822a8d6` (clone of HEAD plus the modified and untracked files, committed as user `snapshot`).
- Identity check against the working tree: 5682 files compared, 0 differing, 0 missing.

```text
env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

| Gate | State | Time | Counts |
|---|---|---|---|
| constitution | PASS | 0s | |
| hooks | PASS | 1s | |
| shell | PASS | 7s | |
| python | PASS | 0s | |
| terraform | PASS | 148s | 7, 19, 62, 40, 6, 117 passed; 0 failed |
| script-tests | PASS | 2815s | scripts/tests 856 OK (required classes RealStateBindingTests 7, RouteOwnershipTest 6); phase12d-spike 78 OK; billing 69, 47, 39 OK; tests/scripts 276 OK; tests/infra 246 OK; 0 skipped |
| sbt | PASS | 780s | JDK 17.0.20.1; succeeded 90, 667, 18 (1 canceled); 0 failed; `[success] Total time: 774 s` |

`RESULT: PASS gates=7`; `check.sh exit 0`.

Evidence: `evidence/14a/gates/check-full-final.txt`, sanitized (snapshot and temp paths replaced; it contains no 12-digit number). The raw log is at `target/phase14/evidence/14a-gates/check-full-clean-snapshot4-final.txt`.

### F2. Other checks

- `git diff --check` on the final tree: exit 0.
- No Scala source changed since R3, so the live-tree sbt marker from R3 still covers the Scala inputs.

### F3. Commit

`APPROVED_COMMIT ed9d2414de66083364bb5f6303d738049ae3d67e` (committed and pushed to `origin/phase-14` on 2026-11-07 at the user's request). It differs from snapshot 4 only in docs: this report, `evidence/14a/gates/check-full-final.txt`, and the plan path in `prompt.md` (email removed).

## Subphase 14B — Step 0 and the Q6 repair (review 2 N3)

No live command ran. Base SHA `e2f0b01ce9670c11ef9c4b3706bb52569f960a1d`.

### B1. Agent-run gates (agent-reported, observed by the agents)

- `infra-engineer` (in `infra/terraform`): `terraform init -backend=false -input=false -lockfile=readonly` exit 0; `terraform fmt -check -recursive` exit 0; `terraform validate` exit 0; `terraform test` "Success! 125 passed, 0 failed" (phase12a 13, phase12b 18, phase12c 9, phase13c 37, phase14a 40, phase14b 8). One temporary mutation (grace on every service) gave phase14b 5 passed / 3 failed, then the line was restored.
- `test-engineer`: `tests/infra/test_phase14b_grace.py` 13 tests OK; `tests/infra` 259 tests OK. 18 mutations on the fixture and 18 on the real text, applied in memory: 36/36 caught (two rows caught by one of their two acceptable check ids). Record: `evidence/14b/q6/test-engineer-mutations.jsonl`.

### B2. Full seven-gate check in clean snapshot 5

- Snapshot 5: commit `5189c3c27843ba916f9bf498c55ffd8299caa082`; identity against the working tree 5686 files compared, 0 differing. After the snapshot only `docs/agent-runs/phase-14/**` changed (non-docs identity re-checked after the run: 1569 files, 0 differing).

```text
env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

| Gate | State | Time | Counts |
|---|---|---|---|
| constitution | PASS | 0s | |
| hooks | PASS | 1s | |
| shell | PASS | 7s | |
| python | PASS | 1s | |
| terraform | PASS | 157s | 7, 19, 62, 40, 6, 125 passed; 0 failed |
| script-tests | PASS | 3083s | scripts/tests 856 OK (RealStateBindingTests 7, RouteOwnershipTest 6); phase12d-spike 78 OK; billing 69, 47, 39 OK; tests/scripts 276 OK; tests/infra 259 OK; 0 skipped |
| sbt | PASS | 797s | JDK 17.0.20.1; succeeded 90, 667, 18 (1 canceled); 0 failed; `[success] Total time: 791 s` |

`RESULT: PASS gates=7`; `check.sh exit 0`. Evidence: `evidence/14b/gates/check-full-q6.txt` (sanitized; no 12-digit number). Raw log: `target/phase14/evidence/14b/check-full-snapshot5.txt`.

### B3. sbt check in the live tree

`JAVA_HOME=<JDK 17> … sbt -batch check` with AWS neutralized: EXIT 0; succeeded 207/64/39/50/100/107/90/667/18, 0 failed, 1 canceled; `[success] Total time: 776 s`; marker `2026-11-07T22:07:00-0600`. Evidence: `evidence/14b/gates/sbt-check-live-q6-summary.txt`.

### B4. Other checks

- `git diff --check`: exit 0.
- Pin drift: 209 pinned, **4 drifted**: `infra/terraform/README.md`, `infra/terraform/modules/runtime/compute.tf`, `infra/terraform/modules/runtime/variables.tf`, `tests/infra/README.md` (`evidence/14b/q6/pin-drift.txt`). The three new test files are not pinned. The user refreshes them once before the commit; the gates do not read the pins.

### B5. Not verified

ECS acceptance of the grace period, readiness timing on a real start, the ALB listener (needs `https_certificate_arn`), and everything live.

## Subphase 14B — repair round 1 (14B review 1, B1)

No live command ran. Base SHA `e2f0b01ce9670c11ef9c4b3706bb52569f960a1d`; all 14B work uncommitted.

### R1. Agent-run gates (agent-reported)

- `infra-engineer` (in `infra/terraform`): `terraform fmt -check -recursive` exit 0; `terraform validate` success; `terraform test` "Success! 153 passed, 0 failed" (phase12a 13, phase12b 18, phase12c 9, phase13c 37, phase14a 40, phase14b 30, phase14b_root 6). Ten temporary mutations, each caught and restored: `evidence/14b/r1/infra-mutations.txt` (the M5 and M8 label lines say "forced true"; the file header states that a non-constant always-true expression was used, because Terraform rejects a literal `true` precondition).
- `test-engineer`: `test_phase14b_grace.py` 21 tests OK; `tests/infra` 267 tests OK, exit 0. 57 in-memory mutations × {fixture, real tree} = 114 results, 114 caught, each by its specific check id: `evidence/14b/r1/test-engineer-mutations.jsonl`.

### R2. Full seven-gate check in clean snapshot 6

- Snapshot 6: commit `2203d5e9d4f568cf2d45cbd53c4a3333f1fab01b`; 5692 files compared, 0 differing, 0 missing; after the run, 1570 non-docs files, 0 differing (`evidence/14b/r1/snapshot6-identity.txt`, review N4).

```text
env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

| Gate | State | Time | Counts |
|---|---|---|---|
| constitution | PASS | 0s | |
| hooks | PASS | 1s | |
| shell | PASS | 7s | |
| python | PASS | 0s | |
| terraform | PASS | 128s | 7, 19, 62, 40, 6, 153 passed; 0 failed |
| script-tests | PASS | 17579s | scripts/tests 856 OK (RealStateBindingTests 7, RouteOwnershipTest 6); phase12d-spike 78 OK; billing 69, 47, 39 OK; tests/scripts 276 OK; tests/infra 267 OK; 0 skipped |
| sbt | PASS | 4194s | JDK 17.0.20.1; succeeded 90, 667, 18 (1 canceled); 0 failed; `[success] Total time: 4188 s` |

`RESULT: PASS gates=7`; `check.sh exit 0`. The script-tests and sbt wall times are several times the earlier runs (3083 s and 797 s); the script suites' own times (1482, 50, 876 and 556 s) are close to the earlier run, so the gap is outside the suites; sbt's own total (4188 s) is also long. The run spanned the night, so host sleep is the likely cause; not confirmed. Evidence: `evidence/14b/r1/check-full-r1.txt` (sanitized; no 12-digit number). Raw log: `target/phase14/evidence/14b/r1/check-full-snapshot6.txt`.

### R3. sbt check in the live tree

JDK 17, AWS neutralized: EXIT 0; succeeded 207/64/39/50/100/107/90/667/18, 0 failed, 1 canceled; `[success] Total time: 739 s`; test marker `2026-11-08T00:16:24-0600`. Evidence: `evidence/14b/r1/sbt-check-live-r1-summary.txt`.

### R4. Other checks

- `git diff --check`: exit 0.
- Pin drift: 209 pinned, **7 drifted**: `infra/terraform/README.md`, `infra/terraform/main.tf`, `infra/terraform/modules/runtime/compute.tf`, `infra/terraform/modules/runtime/outputs.tf`, `infra/terraform/modules/runtime/variables.tf`, `infra/terraform/phase12b-variables.tf`, `tests/infra/README.md` (`evidence/14b/r1/pin-drift.txt`). The new test files and `course.local.tfvars.example` are not pinned.
- `infra/terraform/main.tf`: `git diff -w` shows one added line (the root grace variable passed to `module "runtime"`); the rest of its diff is `terraform fmt` column realignment.

### R5. Not verified

ECS and ELBv2 acceptance of the grace and explicit health-check timing, real peer readiness time, the ALB listener (needs `https_certificate_arn`), and everything live.

## Subphase 14B — replan under the USD 25 cap

No live command ran and no AWS call was made. Base SHA `e2f0b01ce9670c11ef9c4b3706bb52569f960a1d`; all 14B work is uncommitted on branch `phase-14`.

### P1. Agent-run gates (agent-reported)

Each owner ran its own module or suite gate before handing back; the coordinator did not re-observe those runs separately. The authoritative results are P2 and P3. The final test-engineer mutation pass caught 53 of 53 mutants (agent-reported).

### P2. Full seven-gate check in clean snapshot 7 (failed) and snapshot 8 (passed)

- Snapshot 7 (`af7140f1940c19c3c206a9e8ec3285226f5301f4`): `RESULT: FAIL failed: script-tests`, `check.sh exit 4`. Two failures:
  - the new-file account scan passed vacuously on a committed tree, so it now diffs against `git merge-base HEAD main` (or `origin/main`) and raises `BaseNotFound` otherwise;
  - the hung-copy timeout test raced at startup under load, so it now retries with `until_started` at 4, 12 and 30 s (5 of 5 passes under load).
  Evidence: `evidence/14b/replan/check-full-snapshot7-fail.txt`.
- Snapshot 8 (`12f06310657553a32eacd17d6916e9a937c5ffd7`): 5,774 files compared before the run, 0 differing, 0 missing; after the run, 1,639 non-docs files compared, 0 differing (`evidence/14b/replan/snapshot8-identity.txt`).

```text
env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

| Gate | State | Time | Counts |
|---|---|---|---|
| constitution | PASS | 0s | |
| hooks | PASS | 1s | |
| shell | PASS | 8s | |
| python | PASS | 1s | |
| terraform | PASS | 141s | 12, 19, 103, 40, 6, 246 passed; 0 failed |
| script-tests | PASS | 3555s | scripts/tests 1000 OK (RealStateBindingTests 7, RouteOwnershipTest 6); phase12d-spike 78 OK; billing 112, 61, 39 OK; tests/scripts 407 OK; tests/infra 421 OK; 0 skipped |
| sbt | PASS | 788s | JDK 17.0.20.1; last three suites succeeded 90, 675, 28 (1 canceled); 0 failed; `[success] Total time: 782 s` |

`RESULT: PASS gates=7`; `check.sh exit 0`. Evidence: `evidence/14b/replan/check-full-final.txt` (sanitized: snapshot, temp and home paths replaced and ANSI codes stripped; no 12-digit number). Raw log: `target/phase14/evidence/14b/replan/check-full-snapshot8.txt`.

### P3. sbt check in the live tree

JDK 17, AWS neutralized: EXIT 0; succeeded 207/64/39/53/141/118/90/675/28, 0 failed, 1 canceled; `[success] Total time: 755 s`, completed Nov 8, 2026, 11:51:46 PM; test marker updated. Evidence: `evidence/14b/replan/sbt-check-live-replan-summary.txt`.

### P4. Other checks

- Pin drift: 209 pinned, **24 drifted** (`evidence/14b/replan/pin-drift-final.txt`; list in `approval-request-14b-replan.md` §6). New files are not pinned.
- `git diff --check`: **exit 2**. These four files end with an extra blank line (whitespace only):
  - `infra/terraform/billing-execution/README.md:70` (infra-engineer)
  - `modules/storage/README.md:592` (storage-engineer)
  - `scripts/billing/PUBLICATION.md:60` (infra-engineer)
  - `tests/infra/README.md:260` (test-engineer)

  They were not fixed after the snapshot, so the snapshot identity still holds. Each must be routed to its owner before the pin refresh.
- Raw account ID: the snapshot 8 account scan covers new and changed files and passed. `AwsTestSupport.scala` keeps a file-scoped exception for the AWS documentation example account; it is pending user confirmation.

### P5. Not verified

Everything live, including:
- IAM completeness of the new grants;
- S3 `if-none-match` enforcement;
- ECS Exec port forwarding and SigV4 through the tunnel;
- `aws login` session length and the MFA flag;
- Fargate 0.25 vCPU / 1 GiB for the JVM services;
- ACM validation through Cloudflare;
- the 300 s grace period;
- EMR behaviour;
- Bedrock quotas (currently 0);
- actual costs.

The offline Anthropic fallback client in worktree `phase14-anthropic-fallback` is not part of snapshot 8 (agent-reported: 120 rag tests pass there).

## Subphase 14B — repair round 2 (14B review 2, B2; N1–N8)

No live command ran and no AWS call was made. Base SHA `e2f0b01ce9670c11ef9c4b3706bb52569f960a1d`; all 14B work is uncommitted. **The full seven-gate check on a fresh clean snapshot was not run in this round, by user decision 2026-11-09 (`prompt.md`, "Full-check timing").** It runs once after the recheck approves and the deferred whitespace fixes are made, before the pin refresh and the commit. Snapshot 8 (`12f0631…`) remains the last full-gate result, and it predates this round.

### Q1. Agent-run gates (agent-reported)

- **infra-engineer (B2):**
  - `bash -n` on `scripts/deploy.sh` and `scripts/lib/common.sh`: exit 0.
  - `python3 -I -m py_compile scripts/lib/verify.py`: exit 0.
  - `shellcheck -x -P SCRIPTDIR` on `deploy.sh` and `lib/common.sh`: exit 0.
  - `scripts/tests`: `test_verify_redact.py` 16 OK, `test_syntax.py` 20 OK, `test_deploy.py` 155 OK (after the final edits).
  - An earlier full `scripts/tests` run gave 1004 tests with 8 failures:
    - 1 was a bug in a new test, since fixed (the 12 cleanup-stage tests and the full 155 pass);
    - 7 were in `test_terraform_r1.RouteOwnershipTest`, explained below.
- **test-engineer:**
  - `test_billing_replan_14b.py`: 28 OK. It includes the five named-entry tests (i)–(v).
  - `tests/scripts/test_prespend_floors_14b.py`: 26 OK, rewritten for no cleanup floor.
  - `tests/scripts/test_pipeline_refusals.py`: 57 OK.
  - Full `tests/scripts`: 421 OK, exit 0.
  - Mutations, all caught:
    - exception entry: (a1), (a2), (b) and (c);
    - B2: m1 caught by 37 failed subtests, m2 by 29, m3 by 34, m4 by 16.
- **`test_terraform_r1` failures, coordinator re-run:** 7 of 10 fail in the live tree. Their fixture is built only from `git ls-files infra/terraform` (`scripts/tests/test_terraform_r1.py:8`), so the untracked `phase14b*.tf` files are missing and Terraform reports undeclared variables and locals. The same suite passed in clean snapshot 8, where every file is tracked (`RouteOwnershipTest executed=6 status=ok`). This is a live-tree artifact of uncommitted new files, not a regression. It is re-checked by the full gate after approval.

### Q2. Coordinator-run checks (observed)

| Check | Result | Evidence |
|---|---|---|
| Live `sbt -batch check`, JDK 17, AWS neutralized | EXIT 0; succeeded 207/64/39/53/141/118/90/675/28 (1,415), 0 failed, 1 canceled; `[success] Total time: 778 s`; test marker updated | `evidence/14b/r2/sbt-check-live-r2-summary.txt` |
| Full `tests/infra` (`suite_run.py`), after the docs placeholder fix | 426 tests OK, 0 skipped, EXIT 0; includes the real-tree account scan | `evidence/14b/r2/tests-infra-r2-summary.txt` |
| Pin drift | 209 pinned, 24 drifted; the same list as `replan/pin-drift-final.txt` (no script file is pinned) | `evidence/14b/r2/pin-drift-r2.txt` |
| `git diff --check` (tracked) | exit 2: the four deferred blank lines at EOF (`tests/infra/README.md` is now line 266) | `evidence/14b/r2/whitespace-r2.txt` |
| Untracked files, `git add -N` equivalent without touching the index, `evidence/**` excluded | runbook lines 432, 437 and 845 have trailing whitespace; `infra/terraform/tests/phase14b_root.tftest.hcl` has a blank line at EOF; nothing else | `evidence/14b/r2/whitespace-r2.txt` |

**The account scan briefly failed.** It flagged two docs lines where the coordinator had quoted the AWS documentation example account ID verbatim: `prompt.md:261` (the user decision) and `review.md:442` (the reviewer's follow-up prompt). Under the user's own rule that ID is allowed only in `AwsTestSupport.scala`. Both lines now read `<AWS documentation example account ID>`, each with a note that this is the only change to the quoted text, and the scan passes (the `tests/infra` run above).

### Q3. Not run in this round (user decision)

- **The full seven-gate `scripts/check.sh` on a fresh snapshot.** That covers the constitution, hooks, shell and python lint, the Terraform tests, all script suites and sbt.
- **Full `scripts/tests` after the last `common.sh` and docstring edits.** Only `test_deploy.py`, `test_syntax.py` and `test_verify_redact.py` were re-run.
- **The billing suites.** No billing file changed.

### Q4. Not verified

Everything live, as in P5.

## Subphase 14B — post-approval (review 3 APPROVE; F1–F3, whitespace, caps = planned use)

No live command and no AWS call; nothing committed. **The full seven-gate check on a fresh snapshot is deferred by user decision** (`prompt.md`, "Review and full-check order"). It runs once, after the delta review approves.

### S1. Agent-run gates (agent-reported)

- **Whitespace (infra-engineer, storage-engineer, test-engineer, documentation-engineer):** the six items are fixed, whitespace only. Each owner observed exit 0 from `git diff --check` on its tracked files. The runbook line count is unchanged (1462). `terraform fmt -check` on `phase14b_root.tftest.hcl` exits 0.
- **infra-engineer (`EMR_CUMULATIVE_CAP_USD` = 2.52):**
  - `bash -n` and shellcheck exit 0.
  - `scripts/tests`: `test_pipeline.py` 69 OK, `test_13c_pipeline.py` 30 OK, `test_syntax.py` 20 OK, `test_budget.py` 38 OK.
  - Ledger arithmetic is exact Decimal with an inclusive cap (`budget.py:215`, `total + estimate > cap` refuses). Three runs of 0.84 pass and a fourth is refused; a cumulative 2.53 is refused.
- **experiment-engineer (shared Haiku cap = 1.33):**
  - `load-tests/tests` 51 OK; `experiments/tests` 24 OK.
  - `check_manifests.py` exit 0: "15A total 2.52 USD over 3 runs <= cumulative cap 2.52" and "115 answers x 0.011550 = 1.328250 USD <= shared cap 1.33 USD (reserve 0.001750 USD)".
- **test-engineer:**
  - New `tests/scripts/test_cap_pins_14b.py` (12 tests): the pinned caps, both Haiku files agreeing, and the H0 receipt arithmetic, 19.43 × 1.11 + 0.34 = 21.9073 ≤ 22.00, with a negative control for the old caps (22.6288).
  - Full `tests/scripts` 433 OK, exit 0.
  - Full `tests/infra` 426 OK, exit 0.
  - In-memory mutations, all caught: m1, EMR back to 3.00 (2 tests); m2, Haiku back to 1.50 (3 tests); m2b, the two Haiku files disagreeing (3 tests).
- **documentation-engineer:** the runbook has the 37 h hard stop with cleanup by H35, R.1 with tax (× 1.11), the new caps, and the worked example at 3.09. No `1.50`, `3.00`, `H40`–`H42` or `42 h` left. No trailing whitespace.

### S2. Coordinator-run checks (observed)

| Check | Result | Evidence |
|---|---|---|
| Live `sbt -batch check`, JDK 17, AWS neutralized | EXIT 0; succeeded 207/64/39/53/141/118/90/675/28 (1,415), 0 failed, 1 canceled; `[success] Total time: 737 s`, 4:42:58 PM; test marker updated | `evidence/14b/post-approval/sbt-check-live-summary.txt` |
| `git diff --check`, tracked files | exit 0, no output | `evidence/14b/post-approval/whitespace.txt` |
| Untracked files, `git add -N` equivalent with the index untouched and `evidence/**` excluded | 0 findings | same |
| Pin drift | 209 pinned, 24 drifted, the same list as snapshot 8 | `evidence/14b/post-approval/pin-drift.txt` |
| `scripts/run-bounded-pipeline.sh:103` help text | shows `EMR_CUMULATIVE_CAP_USD (2.52)`; test-engineer's note that it still said 3.00 was out of date | — |
| Stale-cap grep (README.md, docs/** outside agent-runs, modules/**) | no 3.00 cumulative or 1.50 Haiku cap left | — |

### S3. Not run (user decision) or not verified

- **Not run:** the full seven-gate check on a fresh snapshot, including `test_terraform_r1.py`, which needs a tree where every file is tracked. It runs after the delta review.
- **Not verified:** everything live. The 11% tax rate is unconfirmed.

## Subphase 14B — post-approval delta repair (review 4: D1; N1–N5)

No live command, no AWS or provider call, nothing committed. The full seven-gate check is still deferred until the recheck approves (user decision).

### T1. Agent-run gates (agent-reported)

- **experiment-engineer, D1:**
  - `experiments/README.md:23` and `experiments/scripts/render_manifests.py:23` now say the cumulative cap is 2.52. The scale-out sentence reads "0.84 + 0.84 + 1.26 = 2.94 > 2.52 … needs a recorded human cap decision first".
  - `grep -rnE '\b3\.00\b' experiments/ load-tests/` finds nothing (exit 1).
  - `experiments/tests`: 24 OK, exit 0.
  - `check_manifests.py`: exit 0, including "15A total 2.52 USD over 3 runs <= cumulative cap 2.52 USD / 3 runs".
- **infra-engineer, N1:** the comment at `scripts/tests/test_pipeline.py:580` now says "would exceed". `test_pipeline.py`: 69 OK, rc=0.
- **documentation-engineer, N2 and N3:**
  - Runbook R.1 lines 614 and 615 use "USD 0.3096 (about 0.31)", matching the 11.15 example; the example numbers are unchanged.
  - Line 614 adds the N3 sentence: the margin is at least about USD 0.35 on every receipt after H0.
  - Line count is 1462, unchanged; no trailing whitespace.

### T2. Coordinator-run checks (observed)

| Check | Result |
|---|---|
| `git diff --check`, tracked files | exit 0 |
| Untracked files (`git add -N` equivalent; `evidence/**` excluded) | 0 findings |
| Stale-cap grep (README.md, docs/runbooks, modules, experiments, load-tests, scripts, infra; md/py/json/sh/conf/tf) | no 3.00 cumulative-cap or 1.50 Haiku-cap statement outside history notes |
| Live `sbt check` | run only to refresh the Stop-hook test marker. No Scala or build input changed in this repair, so it is not a gate for D1, N1 or N2. Result: see T3 |

### T3. Live sbt check (marker refresh only)

JDK 17, AWS neutralized: EXIT 0. Succeeded 207/64/39/53/141/118/90/675/28 (1,415 tests), 0 failed, 1 canceled. `[success] Total time: 756 s`, completed Nov 9, 2026, 6:15:49 PM. Test marker updated.

## Subphase 14B — final full check (snapshots 9 and 10)

Run after review 5 approved. No live command, no AWS or provider call, nothing committed.

### U1. Snapshot 9 (failed)

- Snapshot 9 (`20734a36b5ae4ab832056e4c964031b86054013f`): 5,786 files identical to the working tree.
- `RESULT: FAIL failed: script-tests`, `check.sh exit 4`. The other six gates passed.
- One failure in `tests/infra` (426 ran): `test_billing_replan_14b.NoRealAccountIdIsAdded` flagged `docs/agent-runs/phase-14/review.md:909` (`account-id-literal`). The verbatim review 5 text quoted the 12-digit synthetic placeholder from `scripts/tests/test_pipeline.py:438`.
- Repair (user decision 2026-11-09): the digits were replaced with `<placeholder from test_pipeline.py:438>`, with a note above review 5. No code changed. The live-tree `test_billing_replan_14b.py` then ran 28 tests OK.
- Evidence: `evidence/14b/final/check-full-snapshot9-fail.txt`.

### U2. Snapshot 10 (passed)

- Snapshot 10 (`07e1a83f36fb38889f6a6d48911333a16354c436`): 5,791 files identical before the run; 1,640 non-docs files identical after it (`evidence/14b/final/snapshot10-identity.txt`).

```text
env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

| Gate | State | Time | Counts |
|---|---|---|---|
| constitution | PASS | 1s | |
| hooks | PASS | 0s | |
| shell | PASS | 8s | |
| python | PASS | 0s | |
| terraform | PASS | 139s | 12, 19, 103, 40, 6, 246 passed; 0 failed |
| script-tests | PASS | 3682s | scripts/tests 1006 OK (RealStateBindingTests 7, RouteOwnershipTest 6); phase12d-spike 78 OK; billing 112, 61, 39 OK; tests/scripts 433 OK; tests/infra 426 OK; 0 skipped |
| sbt | PASS | 976s | JDK 17.0.20.1; last three suites succeeded 90, 675, 28 (1 canceled); 0 failed; `[success] Total time: 969 s` |

`RESULT: PASS gates=7`; `check.sh exit 0`. Evidence: `evidence/14b/final/check-full-final.txt` (sanitized: snapshot, temp and home paths replaced, ANSI codes stripped; no 12-digit number, no email). Raw log: `target/phase14/evidence/14b/post-approval/check-full-snapshot10.txt`.

### U3. Other final checks

- Live `sbt check` (JDK 17, AWS neutralized): EXIT 0; 1,415 tests, 0 failed, 1 canceled; 754 s (`evidence/14b/final/sbt-check-live-summary.txt`). No Scala or build input changed afterwards.
- `git diff --check` with untracked files added by `git add -N` (index restored): exit 0 (`evidence/14b/final/whitespace.txt`).
- Pin drift: 24 of 209 (`evidence/14b/final/pin-drift.txt`); refresh pending, by the user.

### U4. Pin refresh (after snapshot 10)

- The user ran `refresh_pins.py --apply`: 24 rows refreshed in `scripts/billing/reviewed-pins.json` (bytes and sha256 values only).
- Coordinator check after the refresh: 209 pinned, 0 drifted; JSON valid; `git diff --check` exit 0.
- Billing suites (the only readers of the pins): `test_budget_execution.py` 112 OK; `test_budget_verification.py` 61 OK; `test_publication_evidence.py` 39 OK.
- The pin file changed after snapshot 10, so the snapshot 10 run does not cover it; the three billing suites above do. Evidence: `evidence/14b/final/pin-refresh.txt`.

## Subphase 14B — repair round 3 (Anthropic API and Voyage AI switch)

Base SHA `f5490d3`, branch `phase-14`; all round-3 work is uncommitted. No live command; no AWS, Anthropic or Voyage call; no key value anywhere.

### V1. Agent-run gates (agent-reported)

See `owner-report.md`, "Subphase 14B — repair round 3". Highlights: rag 186, services 113, independentTests 693; terraform root 268, deployer 111; tests/infra 460, tests/scripts 462; load-tests 54, experiments 28.

### V2. Coordinator-run gates (observed)

Evidence: `evidence/14b/r3/gates-summary.txt`, `sbt-check-live-summary.txt`, `whitespace-and-r1.txt`, `pin-drift.txt`.

| Gate | Result |
|---|---|
| `sbt -batch check` (JDK 17) | first attempt EXIT 1 at `independentTests / Test / scalafmtCheck` (new spec unformatted; routed to test-engineer, formatting only); final EXIT 0, 1,524 succeeded, 0 failed, 1 canceled |
| `terraform test` root / deployer | 268 / 111 passed, 0 failed |
| `terraform fmt -check -recursive` | exit 0 |
| `scripts/tests` | 1,032 ran; 7 failures, all `test_terraform_r1.RouteOwnershipTest` (untracked new `.tf` files); 10/10 with them intent-added |
| `scripts/phase12d-spike/tests` | 78 OK |
| billing suites | 3 × OK |
| `tests/infra` | first run 8 failures + 1 error in `test_billing_replan_14b` (local provider cache in `/private/tmp` lost `LICENSE.txt`; restored; no repository change); rerun 460 OK |
| `tests/scripts` | 462 OK |
| `load-tests/tests`, `experiments/tests` | 54 OK, 28 OK |
| `check_manifests.py` | RESULT: OK |
| `git diff --check` (untracked intent-added, index restored) | exit 0 |
| Pin drift | 209 pinned, 10 drifted (all infra-engineer files this round); refresh after approval |

The full seven-gate check on a clean snapshot is deferred until the reviewer approves (user decision 2026-11-09), as in the previous rounds.

### V3. Not verified

Everything live: Anthropic and Voyage response shapes and model-id echo, tool-use acceptance by `claude-haiku-5-5`, refusal behavior, latency, real token counts and spend, Secrets Manager injection into ECS, egress to `api.anthropic.com` and `api.voyageai.com` through the NAT, the provider console steps in the runbook, and the key-entry method.

### V4. Review 6 repairs (B1, B2, N5)

- B1 (rag-engineer): `EmbeddingClientFactory.create` takes the Bedrock and Voyage configs by name; both live mains build the embedding client through a shared `embeddingClientFor`, so only the selected provider's config is evaluated. 3 new tests in `LiveEmbeddingProviderSpec` (Titan with no Voyage key builds a Bedrock client for document and query input; Voyage at 256 and 2048 never calls the Bedrock builder; missing Voyage key and invalid provider return closed codes). Agent-reported: rag 189, services 113, 0 failed.
- B2 and N5 (documentation-engineer): README, report §4 and runbook A0/A4 name `main_synthesis_provider` / `main_embedding_provider` in `infra/terraform/deployer/deployer.local.tfvars` and the deployer re-apply before the base plan; B3b.2 uses the Edit control and never retrieves an existing value; A4 counts marked "from before repair round 3, reference only".
- Coordinator: `sbt -batch check` (JDK 17) EXIT 0, 1,524 → 1,527 succeeded, 0 failed, 1 canceled; `git diff --check` exit 0. Evidence: `evidence/14b/r3/recheck-review6.txt`.
- Not routed (listed by the reviewer as nonblocking): N1–N4. Noted by the rag-engineer, outside B1: the smoke preflight reads the query-text limit from the Bedrock-shaped embedding config, which accepts 256/512/1024 only, so a Voyage run at 2048 dimensions would be refused there; the default 256 is unaffected.

### V5. Full seven-gate check on clean snapshot 11 (after review 7 APPROVE)

- Snapshot 11 (`3703e125e1e26603b9606037d12ddf00aef98852` on base `f5490d3`): 5,819 files identical to the working tree before the run; 1,658 non-docs files identical after it; snapshot tree clean (`evidence/14b/r3/snapshot11-identity.txt`).

```text
env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
```

| Gate | State | Time | Counts |
|---|---|---|---|
| constitution | PASS | 1s | |
| hooks | PASS | 0s | |
| shell | PASS | 8s | |
| python | PASS | 0s | |
| terraform | PASS | 182s | 12, 19, 111, 40, 6, 268 passed; 0 failed |
| script-tests | PASS | 3659s | scripts/tests 1032 OK (RealStateBindingTests 7, RouteOwnershipTest 6, status ok); phase12d-spike 78 OK; billing 112, 61, 39 OK; tests/scripts 462 OK; tests/infra 460 OK; 0 skipped |
| sbt | PASS | 802s | JDK 17; last three suites succeeded 113, 693, 28 (1 canceled); 0 failed; `[success] Total time: 795 s` |

`RESULT: PASS gates=7`; `check.sh exit 0`. `test_terraform_r1` passes here because the snapshot commits the new `.tf` files. Evidence: `evidence/14b/r3/check-full-final.txt` (sanitized: snapshot, temp and home paths replaced, ANSI codes and trailing spaces stripped; no 12-digit number, no email). Raw log: `target/phase14/evidence/14b/r3/check-full-snapshot11.txt`.

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

`APPROVED_COMMIT`: pending; the user commits this tree and supplies the SHA.

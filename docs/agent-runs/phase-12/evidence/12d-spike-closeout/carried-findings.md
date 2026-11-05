# 12D carried findings — final status at closeout (2026-11-04)

The source for every item is [../12d-spike-offline/review-findings.md](../12d-spike-offline/review-findings.md), items 1 to 31. All the blocking findings were closed by reviewed repairs: B1 to B4, R1 and L1. The items below are nonblocking. Under the human's rule they are listed once and carried, not rechecked.

The status column uses these terms:
- **closed-live:** live attempts 1 to 5 showed that the risk did not materialize;
- **superseded:** a later reviewed repair replaced the code the finding referred to;
- **fixed:** a coordinator correction is already in the evidence;
- **open:** still carried.

| # | Finding (short) | Status | Owner | Close by |
|---|---|---|---|---|
| 1 | `run-step.sh:21`: `timeout` kills only the client, not the YARN application | open | infra-engineer | Before the spike scripts are reused (Phase 13) |
| 2 | ENI delete and modify-attribute are not region-scoped | open (disclosed) | infra-engineer | Before Phase 14 |
| 3 | The inventory might always exit 3 because EFS describes are ARN-scoped | closed-live (the inventory exited 0 after every attempt) | — | — |
| 4 | `CreateFileSystem` might be denied | closed-live (EFS was created in attempts 1 to 5) | — | — |
| 5 | The service role's KMS CreateGrant lacks `kms:GrantIsForAWSResource` | open | infra-engineer | Before Phase 14 |
| 6 | Some mutations survived the tests: a 22/tcp ingress rule, a second KMS key, widened GetObject, extra SNS/SQS, unpinned gp3 IOPS | open | test-engineer | Phase 13 |
| 7 | The tag test checks `default_tags`, not each resource's `tags_all` | open | test-engineer | Phase 13 |
| 8 | The bootstrap does not check spark-defaults, the step scripts or the G1 config against sha256 | open | infra-engineer | When the bootstrap is ported to the main module |
| 9 | `aws:MultiFactorAuthPresent` might be missing on role-chained sessions | closed-live (the MFA role switch and preflight succeeded) | — | — |
| 10 | The guard does not inspect conditions | open | test-engineer | Phase 13 |
| 11 | Housekeeping (empty directory, attempt-1 count) | fixed | — | — |
| 12 | No test asserts that `aws_default_security_group` is absent | open | test-engineer | Phase 13 |
| 13 | `CreateAccessPoint` is not scoped to the spike's file system | superseded (by the L1 repair, reviewed APPROVE) | — | — |
| 14 | KMS `TagResource` is allowed on any key | open | infra-engineer | Before Phase 14 |
| 15 | The stale comment at `kms.tf:26-27` | open | infra-engineer | Next infra edit |
| 16 | Spike roles can be given trust policies that name other principals | open | infra-engineer | Before Phase 14 |
| **17** | **The boundary lets a passed spike role terminate or modify any EMR-tagged instance or ENI** | **open, must close first** | infra-engineer | **Before Phase 14 or any other EMR cluster in us-east-2** |
| 18 | `deployer/README.md:69` overstates the guarantees | open | infra-engineer | Next infra edit |
| 19 | Stale lines in the gates and report | fixed | — | — |
| 20 | The tag-condition test does not check that the value is `"true"` | open | test-engineer | Phase 13 |
| 21 | The login policy's attachment target is untested | open | test-engineer | Phase 13 |
| 22 | `gates.json` wording | fixed | — | — |
| 23 | Extra blank lines at EOF (`deployer.tftest.hcl:630`, `scripts/phase12d-spike/README.md:48`) | open | infra-engineer / test-engineer | Next edit |
| 24 | The `DisassociateAddress` grant does not fix the destroy (the 403 names `*/*`) | open; two-pass destroy confirmed in attempts 2 to 5 | infra-engineer | Keep the two-pass procedure; do not widen the grant |
| 25 | A passed spike role can launch any AMI or instance type, into the spike's tagged subnet only | open (optional tightening) | infra-engineer | Optional |
| 26 | `kms:ResourceAliases` on EC2 CreateGrant and EMR's security-group rule calls are unverified | closed-live (encrypted volumes attached and the cluster ran in attempts 3 to 5) | — | — |
| 27 | The reviewer's self-correction | no action | — | — |
| 28 | `bootstrap.sh:163`: the Java path is not validated for the properties format | open | infra-engineer | When the bootstrap is ported |
| 29 | `bootstrap.sh:162`: removing `JAVA_HOME` misses other separators | open | infra-engineer | When the bootstrap is ported |
| 30 | The spike README's Snappy explanation is wrong | open | infra-engineer | Next infra edit |
| 31 | `collect-evidence.sh` fails on macOS `tar` (`._` members) | open | infra-engineer | Before the script is reused |

The residual risks accepted at Step A also did not materialize live:
- **AddTags during RunJobFlow:** clusters were created in attempts 2 to 5.
- **Boundary tighter than v2:** this caused the attempt 2 failure. It was fixed by `V2ExistingLaunchDependencies`.

## Phase-level carries touched by 12D

- **N1** (EMRFS prefix-scoped delete and commit permissions): **still unverified.** The spike did no S3 output through Spark (gap G1 in [decision-12-10.md](decision-12-10.md)).
- **N9** (the EMR service role's KMS use for EBS encryption): proven in the **spike root only**, where encrypted gp3 volumes attached. The main module still needs the same grant.

## Open totals

- 22 items are open: 1, 2, 5 to 8, 10, 12, 14 to 18, 20, 21, 23 to 25 and 28 to 31.
- Item 17 is the only one with a hard precondition.
- 4 items are closed live: 3, 4, 9 and 26.
- 1 is superseded: 13.
- 3 items are fixed: 11, 19 and 22.
- 1 needs no action: 27.

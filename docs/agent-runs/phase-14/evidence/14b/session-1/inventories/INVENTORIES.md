# Session 1 resource inventories (before and after cleanup)

Assembled offline on 2026-11-15 by the orchestrator from local, git-ignored cleanup evidence. No AWS call was made to build this page. Each count below was taken from the copied files with `wc -l`, `grep -c` and `awk`.

## Files and source runs

| File | Source | Lines | sha256 |
|---|---|---|---|
| `before-cleanup-inventory.txt` | `target/cleanup-evidence/20261115T014213Z-74524/before-inventory.txt` (destroy pass 1, before the destroy; written 2026-11-15T01:47:31Z) | 309 | `e8ab1f36b9fa74d4a84d49a1776f43de54f50dac64e7931b38a70669dd844e08` |
| `after-cleanup-inventory.txt` | `target/cleanup-evidence/20261115T020725Z-78532/after-inventory.txt` (destroy pass 2, after the destroy; written 2026-11-15T02:07:45Z) | 60 | `52c3df033b9b44e764ed1d259836a0dcce457f7c4450b8e4947d1b27180f2657` |

Both files are byte-identical to their sources (sha256 of copy = sha256 of source; see `../INDEX.md`). The cleanup script (`scripts/cleanup.sh`) wrote them already masked: every account ID appears as `<acct>` (135 of 309 lines and 58 of 60 lines carry `<acct>`; no 12-digit account number appears in either file), and some names (service names and `for_each` keys) appear as `<redacted>`. Because the script de-duplicates after masking, one line can stand for several instances (for example `module.runtime.aws_ecs_service.service["<redacted>"]` stands for the four services). Line counts are therefore inventory entries, not resource instances. The pass 1 destroy plan had 213 actions (`../section-c/destroy-actions-pass-1.txt`).

Why these two runs: run `20261115T012727Z-69466` was refused at the destroy policy (nothing destroyed) and run `20261115T013510Z-72124` stopped at the confirmation step (nothing destroyed); their before inventories are earlier listings of the same estate. Run `20261115T014213Z-74524` is the first run that destroyed anything, so its before inventory is the true pre-cleanup view. Run `20261115T020109Z-77140` was the pass 2 listing (confirmation step). Run `20261115T020725Z-78532` is the last destroy, so its after inventory is the final view. The copy in `target/phase14/evidence/14b/cleanup-evidence/` comes from pass 2 (62 to 60) and is not the full before inventory.

## Counts

| Point | Entries | Source |
|---|---|---|
| Before pass 1 | 309 | run 74524 `before-inventory.txt` |
| After pass 1 (`RESULT: PARTIAL`, apply exit 1 on `aws_eip.nat` DisassociateAddress 403, carried item 24) | 62 | run 74524 `after-inventory.txt` (identical to run 78532 `before-inventory.txt`) |
| After pass 2 (`RESULT: PASS`) | 60 | run 78532 `after-inventory.txt` |

Pass 2 removed exactly two entries: the Elastic IP ARN and the Terraform address `module.network.aws_eip.nat` (`diff` of the pass 1 and pass 2 after inventories). Pass 2 had one destroy action, `delete module.network.aws_eip.nat` (`../section-c/destroy-actions-pass-2.txt`).

## What each inventory line is

The inventory merges two sources (`scripts/cleanup.sh`, steps `before-inventory` and `after-inventory`):

- `arn:...` lines: the Resource Groups Tagging API (`aws resourcegroupstaggingapi get-resources`, tag `project=scholarchain`, region us-east-2).
- `tf:infra/terraform:...` lines: Terraform state addresses (`terraform state list`) of the main stack.

### Before cleanup (309 entries)

135 tagging-API entries and 174 Terraform state entries.

| Tagging-API type | Entries |
|---|---|
| ec2 security-group-rule | 28 |
| ecs task-definition | 13 |
| ec2 security-group | 10 |
| s3 bucket | 7 |
| s3vectors vector bucket (1) and indexes (5) | 6 |
| ec2 subnet | 6 |
| dynamodb table | 6 |
| elasticmapreduce cluster | 5 |
| ecs task | 4 |
| ec2 network-interface | 4 |
| application-autoscaling scalable-target | 4 |
| servicediscovery service | 3 |
| ec2 route-table | 3 |
| cloudwatch alarm | 3 |
| secretsmanager secret | 2 |
| rds cluster | 2 |
| logs log-group | 2 |
| ec2 vpc-endpoint | 2 |
| ec2 instance | 2 |
| sqs queue | 2 |
| one each: states stateMachine, servicediscovery namespace, rds subgrp / pg / db / cluster-snapshot / cluster-pg, kms key, elasticloadbalancing targetgroup / loadbalancer / listener, elasticfilesystem file-system / access-point, ecs service, ecs cluster, ecr repository, ec2 vpc / natgateway / internet-gateway / elastic-ip, acm certificate | 21 |

| Terraform module (state addresses) | Entries |
|---|---|
| module.datalake | 49 |
| module.network | 49 |
| module.identity | 17 |
| module.runtime | 12 |
| module.emr | 11 |
| module.s3vectors | 7 |
| module.dynamodb | 6 |
| module.messaging, module.neptune, module.observability | 5 each |
| module.workflow | 3 |
| root (ACM certificate and validation, provider-key secrets, two `terraform_data` guards) | 5 |

### After cleanup (60 entries)

58 tagging-API entries and 2 Terraform state entries.

| Type | Entries | Notes |
|---|---|---|
| ec2 security-group-rule | 28 | The 10 security groups that held these rules are gone from the same inventory, and all security-group and rule resources were in the pass 1 destroy set |
| ecs task-definition | 13 | 7 service revisions (shown as `<redacted>`) and 6 `neptune-tunnel` revisions |
| elasticmapreduce cluster | 5 | `j-01471773SLN9SIKVTEUJ`, `j-0426641ATQVS0H3PIYY`, `j-03354448AO318DJHXVR`, `j-03354572RN3ACLOGKG91`, `j-05198553ABDUQT7HM2DM` |
| ecs task | 4 | |
| ec2 vpc-endpoint | 2 | |
| ec2 instance | 2 | |
| ecs service | 1 | |
| ecs cluster | 1 | |
| ec2 natgateway | 1 | `nat-0e1e7d1d42a4b6943` |
| kms key | 1 | `cb0a6f60-...` |
| Terraform `terraform_data.configuration_guard`, `terraform_data.provider_guard` | 2 | Root-level precondition guards; no AWS object and no cost |

No Terraform state address of any module remains in the after inventory: Terraform holds no managed AWS resource of the main stack after pass 2.

## Why the 60 entries are index leftovers, not live resources

The tagging API keeps listing resources for some time after they are deleted, terminated or made inactive. ECS task definitions stay listed as INACTIVE revisions (they have no cost), and stopped ECS tasks, terminated EC2 instances, terminated EMR clusters, deleted NAT gateways and VPC endpoints, and deleted security-group rules can still appear in the index. The decision log (`../00-timeline/decision-log.md`, C3 pass 2 entry) recorded this reading at the time and asked for a C8 console check.

Evidence that backs this reading:

- Terraform destroyed the managing resources: the pass 1 destroy set included `module.runtime.aws_ecs_cluster.course`, the 4 `aws_ecs_service.service` instances, the 5 current task definitions (4 services and the tunnel), `module.network.aws_nat_gateway.course`, both `aws_vpc_endpoint.gateway` instances, all 10 security groups and their rules, and `module.identity.aws_kms_key.data`; pass 2 removed the Elastic IP. After pass 2, no module address is left in Terraform state.
- C7 console check (root, read-only): KMS key `cb0a6f60...` is Pending deletion.
- C8 console checks (root, read-only, us-east-2): S3 general purpose buckets 0 (all regions); no Elastic IPs; no load balancers; NAT gateway `nat-0e1e7d1d42a4b6943` state Deleted; no VPC endpoints; Neptune database clusters 0.
- C4: the deployer stack teardown destroyed 13 resources (4 operator roles and 9 inline policies; `aws_iam_role.deployer` kept): `Apply complete! Resources: 0 added, 0 changed, 13 destroyed.` (`../section-c/deployer-cleanup-apply.log`).

## Console coverage of the after-inventory entries

C8 (decision log, no timestamp) and the C11 final console checks (decision log, 2026-11-15T18:04Z, user screenshots, us-east-2; summarized in `../section-c/c11-cost-report.md` §4) cover these entries:

- **ECS** (checked in C11): ECS Clusters (0), "No clusters". The ECS cluster entry, the ECS service entry and the 4 ECS task entries cannot belong to a live cluster. The 13 task-definition entries were not looked at one by one; INACTIVE revisions are the expected state and have no cost.
- **EMR clusters** (checked in C11): EMR on EC2 Clusters (0), "No Clusters to display", so no cluster is running or waiting. This covers the 5 cluster entries, including `j-05198553ABDUQT7HM2DM`, whose last read in the session was `WAITING` after run 4 (`../b9-emr/b9-results.txt`). `aws_emr_cluster.pipeline` was not in the pass 1 destroy set, so Terraform no longer tracked a cluster at cleanup time.

Still **not** separately checked:

- **EC2 instances**: the 2 instance entries (`i-0aa93421ea40ef4ab`, `i-0e6171b5a3a6bfb08`) were not looked up in the EC2 Instances console. C8 checked only Elastic IPs and load balancers under EC2. With no EMR cluster running or waiting, they are expected to be terminated EMR nodes, but that is not observed.
- **Security-group rules**: the 28 rule entries were not checked one by one. Their parent security groups are absent from the after inventory, and the VPC was destroyed in pass 1.

An optional read-only look at EC2 Instances in us-east-2 would close the first item.

## Final-cleanup items (left on purpose for Session 2)

The C4 deployer apply destroyed only the 4 operator roles and their 9 inline policies (`0 added, 0 changed, 13 destroyed`). It kept, on purpose for Session 2:

- the deployer role `scholarchain-deployer` (`aws_iam_role.deployer` untouched);
- its `phase14-main` policies, which the apply's outputs still list: `scholarchain-deployer-phase14-main--compute`, `--data`, `--emr-efs`, `--iam`, `--keys-obs`, `--network`, `--network-mod`;
- the two permissions-boundary policies named in the same outputs (`scholarchain-course-emr-service-boundary`, `scholarchain-course-permissions-boundary`).

These must be removed at the final cleanup after the last live session. The final cleanup must also cover the two `terraform_data` guards still in main state (no AWS object) and the billing stack, whose live budget differs from the billing-bootstrap code (`../section-c/c11-cost-report.md` §3).

## Masking check

- `grep -c` of the real account ID in both copied files: 0 (checked against the value held only in local scratch, never written to the repository).
- Lines with `<acct>`: 135 of 309 (before) and 58 of 60 (after).
- The only 12-digit digit run in either file is inside the ECS task ID `9153151700274500b8bd02a7522f0ff5` (32-hex task ID, line 51 of the after file and line 92 of the before file); it is not an account ID.

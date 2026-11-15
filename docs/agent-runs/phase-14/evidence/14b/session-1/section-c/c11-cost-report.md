# C11 cost report: Session 1 (Phase 14 live session)

Status: **provisional**. Read on 2026-11-15 (CST) from console screenshots supplied by the human; the November AWS bill is still *Pending* and Nov 15 billing may still be filling in. Re-read Cost Explorer after 2026-11-16 to confirm. Values are typed from the screenshots; the screenshots stay with the human (they show the account ID and e-mail, so they are not committed).

Session 1: H0 2026-11-13T17:44:01Z to cleanup end about 2026-11-15T03:00Z.

## 1. Totals against the USD 25 project cap

| Source | Amount (USD) | How it was read |
|---|---:|---|
| AWS usage, before credits | 15.75 | Cost Explorer, Nov 1 to 15 2026, daily, by service, charge types Credit and Refund excluded |
| AWS tax | 0.00 | Bills > November 2026 > Taxes by service: 0 taxed services, total tax 0.00 (credits cover all charges) |
| Anthropic | about 0.08 (0.075075) | LLM ledger estimate: 55 answers x 0.001365 (claude-haiku-5-5 at 0.10 / 0.50 per 1M tokens, pinned 2026-11-09). The console total cannot be separated because the key's workspace was shared with another project. |
| Voyage AI | 0.00 | Voyage dashboard, Usage: Cost, November 2026: monthly spend 0.00, voyage-4-lite 0.00 |
| **Combined** | **15.83** | |

Room left under the cap: 25 - 15.83 = 9.17; after the project's USD 3 safety floor, 6.17.

The AWS amount actually invoiced is USD 0.00 (Bills page: estimated grand total 0.00, net after credits). The cap is counted on usage before credits, as the runbook requires.

Cross-check: Bills page "highest Region spend" US East (Ohio) 15.25 + Route 53 (global) 0.50 = 15.75. The Budgets page shows the same 15.75.

## 2. AWS by service (USD, before credits, before tax)

| Service | Nov 1-15 | Nov 4 | Nov 13 | Nov 14 | Nov 15 |
|---|---:|---:|---:|---:|---:|
| Neptune | 9.05 | - | 1.30 | 7.12 | 0.63 |
| Elastic Container Service | 1.78 | - | 0.23 | 1.45 | 0.10 |
| EC2-Other (NAT, EBS) | 1.72 | 0.18 | 0.32 | 1.13 | 0.09 |
| EC2-Instances (EMR nodes) | 0.75 | 0.12 | 0.00 | 0.63 | 0.00 |
| Elastic Load Balancing | 0.68 | - | 0.09 | 0.54 | 0.05 |
| Route 53 (hosted zone) | 0.50 | - | - | 0.50 | - |
| VPC | 0.46 | 0.01 | 0.07 | 0.36 | 0.03 |
| DynamoDB | 0.22 | - | 0.21 | 0.01 | 0.00 |
| S3 | 0.22 | 0.00 | 0.03 | 0.17 | 0.01 |
| Secrets Manager | 0.15 | - | 0.06 | 0.08 | 0.01 |
| Elastic MapReduce | 0.14 | 0.01 | - | 0.13 | - |
| Key Management Service | 0.05 | 0.00 | 0.01 | 0.03 | 0.00 |
| Elastic File System | 0.03 | 0.02 | - | 0.00 | 0.00 |
| ECR | 0.01 | - | 0.00 | 0.00 | 0.00 |
| Glue, SNS, SQS, ACM, Step Functions, CloudWatch | 0.00 | | | | |
| **Daily total** | **15.75** | **0.35** | **2.31** | **12.16** | **0.92** |

Nov 12 shows 0.01 (Secrets Manager). Nov 4 is the earlier EMR smoke, about the USD 0.34 already spent before Session 1.

Observations:
- Neptune is 57% of the bill. Over the Nov 14 full day it ran about 0.30 per hour, against the 0.1608 modeled, because it scaled up during loads.
- Full-stack rate measured on Nov 14 (day total less Route 53 and the EMR lines): about 0.45 per hour before tax.
- EMR was cheap: service fee 0.14 plus about 0.63 of instance time over five cluster starts.

## 3. Budget monitoring (finding)

The live AWS Budget `scholarchain-project-budget` is a custom-period cost budget (2026-10-01 to 2027-01-01) set to **USD 200.00**, with three alerts at **actual cost above 50%, 80% and 100%** (USD 100 / 160 / 200) and one verified e-mail recipient. Current spend 15.75 (7.87%), status Healthy; no alert fired, and the human received no alert e-mail.

The billing-bootstrap Terraform (`infra/terraform/billing-bootstrap/main.tf`) defines USD 25 with absolute alerts at USD 10 / 15 / 20, but that update was never applied. Session 1 was protected by the pre-spend receipts and caps, not by the budget. Applying billing-bootstrap is a Session 2 prerequisite (human gate).

## 4. Nothing left running (C8 and C11 console checks, us-east-2)

S3 0 buckets; no Elastic IPs; no load balancers; NAT gateway Deleted; no VPC endpoints; Neptune 0 database clusters; KMS key Pending deletion; ECS Clusters (0); EMR on EC2 Clusters (0).

Source of record: the C11 entries (2026-11-15) of the tracked decision log `docs/agent-runs/phase-14/evidence/14b/session-1/00-timeline/decision-log.md`, a byte-identical copy of the git-ignored `target/phase14/evidence/14b/b8-3-graph-only-decision.md`.

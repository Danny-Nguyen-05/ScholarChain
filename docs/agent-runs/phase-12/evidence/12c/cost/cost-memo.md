# Phase 12C cost research — USD 200 shared project ceiling

Prepared from public AWS pricing on 2026-10-30. No account APIs, paid pricing/Cost Explorer calls or model calls were used in this research. Coordinator separately confirmed PAID/ACTIVE account status and supplied the sanitized real-plan summary. This memo is a planning model, not observed spending, deployment permission or a verified budget-fit pass.

## Date intervals

- Base: **2026-11-15 00:00 CST → 2026-11-24 23:00 CST**, 239 hours.
- Upper duration: **2026-11-11 00:00 CST → 2026-11-24 23:00 CST**, 335 hours.
- Both end before submission day. Exact human-approved live timestamps may differ; rerun the calculation when they do. A midnight November 24 endpoint would omit almost all cleanup day, so it is deliberately not used.

## Authored primary shape and later activation

The actual default plan creates 171 managed objects (169 AWS resources and two terraform_data objects), with no changes/deletes/replacements. It contains seven ordinary S3 buckets, six on-demand/PITR DynamoDB tables, one S3 Vectors bucket and five indexes, one NAT gateway/EIP, S3/DynamoDB gateway endpoints, one CMK, four ECR repositories, one empty ECS cluster, one Cloud Map private DNS namespace, SQS/DLQ, a Standard Step Functions dispatcher, five log groups, a dashboard and four alarms. Neptune, EMR, Fargate services/tasks/scaling, ALB and the budget resource are disabled. Four alarms use five metric-equivalents in the conservative pricing allowance because the error-percentage alarm references two source metrics. Confirm metric billing details before deployment.

Seven S3 buckets or six tables do not themselves imply seven/six fixed monthly storage charges: usage/PITR/request quantities matter. An empty vector bucket/index does not imply provisioned vector compute; vector storage and requests are charged. The disabled runtime still leaves the private DNS hosted zone, NAT/EIP and monitoring objects in the primary plan.

The later-activated comparison uses the selected defaults: one Neptune Serverless writer at **1–2.5 NCU**, four Linux/x86 Fargate services at **0.5 vCPU/1 GiB each**, minimum one task/service, HTTP maxima two each and worker maximum four (ten tasks total). The ALB scenario assumes one LCU average and at least two public IPv4 addresses, in addition to the NAT EIP. Private task ENIs have no public IPv4 charges. EMR remains disabled/unselected; no runtime/release choice is inferred by this estimate.

## Results before credits

| Window | Primary zero-workload allowance | Primary + illustrative store/API usage | Later active, minimum capacity + usage/reserves | Later active, sustained max task counts/NCU + usage/reserves |
|---|---:|---:|---:|---:|
| base (239 h) | $16.95 | $19.22 | $157.94 | $251.28 |
| upper_duration (335 h) | $21.75 | $24.17 | $194.91 | $325.62 |

**Interpretation:** the minimum-capacity activated base scenario leaves about **$42.06** below $200 under the stated assumptions. The upper-duration minimum scenario leaves only **$5.09**; it is too close to treat as a verified fit. Sustaining authored maxima exceeds $200 in both windows. Choose the base window, keep expensive capacity short-lived, and approve per-run limits only after actual baseline spend, requests/telemetry and runtime pricing are known. These figures do not authorize sustaining capacity at its maximum.

Primary zero-workload numbers reserve a full month of one key ($1), one dashboard ($3), five standard alarm-metric equivalents ($0.50), and one hosted zone ($0.50), plus actual NAT/EIP hours. This deliberately avoids promising monthly proration/free allowances. Dashboard/alarms/key may actually prorate or qualify for free allowances; the reservation is conservative. Usage/storage/custom metric comparisons use a 720-hour pricing month; actual calendar billing can differ. No signup credit or free usage is subtracted.

## Current Ohio retail rates and sources

The selected SKU records, attributes, units, catalog publication dates, fetched-source hashes and URLs are in `curated-price-evidence.json`.

| Component | Rate used |
|---|---:|
| Neptune Standard Serverless | $0.1608/NCU-hour |
| Neptune storage / I/O / extra backup | $0.10/GB-month; $0.20/million I/Os; $0.021/GB-month |
| Fargate Linux/x86 | $0.04048/vCPU-hour + $0.004445/GiB-hour |
| Extra Fargate ephemeral storage above included 20 GiB | $0.000111/GB-hour |
| NAT gateway / NAT processing | $0.045/hour + $0.045/GB |
| Public IPv4 | $0.005/address-hour |
| Interface endpoint | $0.01/AZ-hour, plus data |
| ALB / LCU | $0.0225/hour + $0.008/LCU-hour |
| KMS | $1/key-version-month + $0.03/10,000 symmetric requests |
| CloudWatch | $3/dashboard-month; $0.10/standard alarm-metric-month; $0.30/custom metric-month; $0.50/log-ingested GB; $0.03/log-stored GB-month |
| ECR | $0.10/GB-month |
| Secrets Manager | $0.40/secret-month + $0.05/10,000 API requests |
| DynamoDB Standard | $0.125/million read units; $0.625/million write units; $0.25/GB-month storage; $0.20/GB-month PITR |
| S3 Standard | $0.023/GB-month; $0.005/1,000 PUT/LIST; $0.0004/1,000 GET |
| S3 Vectors | $0.06/GB-month; $0.20/GB PUT; $2.50/million QueryVectors requests, plus processed/returned data and API tiers |
| SQS Standard / Step Functions Standard | $0.40/million requests; $0.025/1,000 transitions |
| Cloud Map / private hosted zone | $0.10/resource-month + $1/million discovery API calls; $0.50/zone-month |
| Titan Text Embeddings V2, Ohio on-demand | $0.02/million input tokens |
| EMR surcharge only, m5.xlarge / m5.2xlarge | $0.048 / $0.096 per node-hour, **in addition to EC2 and EBS** |

Official regional catalogs: [Neptune](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonNeptune/current/us-east-2/index.json), [ECS/Fargate](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/us-east-2/index.json), [ELB](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSELB/current/us-east-2/index.json), [VPC](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/current/us-east-2/index.json), [CloudWatch](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/us-east-2/index.json), [KMS](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/awskms/current/us-east-2/index.json), [S3 including Vectors](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-2/index.json), [DynamoDB](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonDynamoDB/current/us-east-2/index.json), [Bedrock](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrock/current/us-east-2/index.json), and [EMR](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/ElasticMapReduce/current/us-east-2/index.json). The [VPC pricing example](https://aws.amazon.com/vpc/pricing/) explicitly supplies Ohio NAT rates. All requested catalogs and failed URL attempts are listed in `fetch-manifest.json`; do not present failed lookups as pricing verification.

## Illustrative workload, reserves and sensitivities

These quantities are **modeling assumptions**, not approved manifests or observed workload. Detailed arithmetic is in `cost-calculations.json` and reproducible with `build_cost_evidence.py`.

- Primary usage: 10 GB NAT processing; 10 GB total versioned S3 storage; 20,000 S3 PUT/LIST and 100,000 GET; 4 GB ECR images; 1 GB total DynamoDB/GSI/PITR with 100,000 read and 100,000 write units; 1 GB log ingestion/storage; 100,000 symmetric KMS requests; 0.1 GB vector storage/PUT, 10,000 vector queries, 10,000 total processed GB, 1 returned GB and 1,000 tier-1 control requests; 100,000 SQS requests; 10,000 state transitions. Larger item/request payloads, batching, retries and versions change billable quantities.
- Later activation adds 80 total custom/Container-Insights metric equivalents (not per-request dimensions), four secrets, 10,000 secret/discovery API calls, 1 GB Neptune storage, one million I/Os, 1 GB extra backup and ten million Titan V2 input tokens ($0.20). Actual Container Insights/custom publisher cardinality must be bounded and priced; missing metrics do not imply zero cost.
- Each activated total includes **$15 provisional reserve for all EMR spikes/experiments**, **$20 for synthesis/optional 9C/evaluation**, **$20 for tax/unreported usage/other uncertainty**, and **$1.636 for one additional month of retained 10 GB S3 +0.1 GB vectors +one key +4 GB ECR**. These are planning allocations within $200, not execution approvals or verified actual charges. The synthesis model is unset, so its tokens cannot be priced honestly yet. The retained-state set must include any necessary access/KMS dependencies and can cost more than this illustrative set.
- For one additional interface service in two AZs, add **$4.78 base / $6.70 upper**, excluding processed data. Current `interface_endpoint_services=[]`; these are optional sensitivity figures, not resources in the real plan.
- Neptune 1 NCU compute alone costs **$38.4312 / $53.868**, while sustained 2.5 NCU is **$96.078 / $134.67**. Four Fargate tasks cost **$23.59886 / $33.0779**; ten default-shaped tasks cost **$58.99715 / $82.69475**. ALB/public IP counts and LCUs can scale beyond these assumptions.
- Underlying EC2 m5.xlarge/m5.2xlarge and EBS rates were **not independently revalidated**: attempted small public EC2 pricing-map paths returned 404; the huge EC2 catalog was deliberately not fetched. The priced EMR surcharge is verified, but the complete EMR formula remains `node-hours × (regional EC2 rate + EMR surcharge) + EBS + log/S3/network/KMS usage`. The $15 reserve is not proof that the eventual runtime/experiment plan fits. Price that exact shape before 12D/15 approval.

## Gates before live work

Coordinator reports PAID/ACTIVE account and read-only plan complete, but **zero current account budgets**, Cost Explorer activation unverified, no paid Cost Explorer calls and no model invocation. Establish the separately approved account-wide pre-spend budget before any paid spike/smoke. Ordinary budget monitoring/notifications are [free](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/); Cost Explorer primary-view API requests cost [$0.01 each/page](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/). Query sparingly with explicit approval and cached snapshots. Delayed reported costs must be supplemented by nonoverlapping estimates of unreported usage plus baseline/retention reserves; use runtime/capacity/request/token limits to enforce run caps.

No real-plan result proves future activation cost fit, paid model access, EMR Spark compatibility, live KMS behavior, telemetry publishing, sufficient unused quotas, or an approved archival location. Reconfirm the actual timestamps, selected runtime/model, bounded manifests, account cost-to-date and retention decisions before human live approval. Never silently replace Serverless with the rough provisioned-Neptune estimate or subtract unverified signup credits.

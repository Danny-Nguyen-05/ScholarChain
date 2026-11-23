# ScholarChain service limits and Region

This file records the limits the implementation was built against and the ones that were observed, with the Region used. Every row names its source. Three labels are used:

- **Observed**: a committed run record shows it.
- **Configured**: a value in a committed Terraform or source file; it is a limit we set, not a provider fact.
- **Documented**: copied from provider documentation as recorded in a committed README on the date given there; no account call was made to confirm it.

Where no committed evidence exists the row says **not verified**. Nothing in this file was re-checked against a live service in package 17A-1 (no network, no AWS, no model call).

## 1. Region

| Item | Value | Source |
|---|---|---|
| AWS Region for every resource | `us-east-2` (US East, Ohio) | [infra/terraform/README.md](../infra/terraform/README.md) (user-selected Ohio); `region=us-east-2` in the EMR run record ([emr-run-1.log](agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log)) and in [15a-emr-size-100.json](../experiments/manifests/15a-emr-size-100.json) |
| Account and AZ values | supplied privately, not recorded in the repository; the Terraform root enforces the allowed account | Terraform README, "Inputs and naming" |
| Services created and used in `us-east-2` | S3, KMS, DynamoDB, SQS, Secrets Manager, ECR, ECS Fargate, ALB with an ACM certificate, Neptune Serverless, S3 Vectors, EMR on EC2, EFS, CloudWatch, Step Functions resources | Observed: Session 1 and Session 2 applies and the 297-entry inventory ([phase-14 human gate](agent-runs/phase-14/human-gate.md), [cleanup-results.txt](agent-runs/phase-15/evidence/session-2/section-c/cleanup-results.txt), resource counts per module in the [decision log](agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md), block 38 listing) |
| Prior check of regional availability | not made from evidence before the first deploy: "Quotas and regional service access are not checked from evidence; confirm in the console: Neptune Serverless, Fargate vCPU, EIP, NAT, ALB and S3 Vectors in us-east-2" | [approval-request-14a.md](agent-runs/phase-14/approval-request-14a.md), row 1 |
| Availability confirmation | by use: Neptune, S3 Vectors, EMR and the ECS/ALB runtime were created and used in this Region in Session 1 (2026-11-13 to 2026-11-15) and Session 2 (2026-11-18) | the records above |
| Terraform, provider | Terraform 1.13.5, AWS provider 6.44.0, exact pins | Terraform README |
| Pricing basis | rates retrieved 2026-11-06 and confirmed by the human, Region `us-east-2` | `G6-CAPS` line in [emr-run-1.log](agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log) |

## 2. Amazon Bedrock restriction and the provider fallback

| Item | Value | Source |
|---|---|---|
| Bedrock quota for Claude Haiku 4.5, Titan Text Embeddings V2 and Amazon Nova Micro in `us-east-2` | 0 (an account-wide restriction); Titan V2 on-demand quotas were also "Not adjustable" | [docs/agent-runs/phase-14/prompt.md](agent-runs/phase-14/prompt.md), "Bedrock quotas (user, 2026-11-08)" and the update that follows it |
| Quota increase | requested through Service Quotas and an AWS Support case on 2026-11-08; the student reports AWS declined it; the AWS reply is not stored in the repository | [docs/report/provider-fallback.md](report/provider-fallback.md), section 1 |
| Instructor ruling | 2026-11-09: use the Anthropic API for synthesis and Voyage AI for embeddings, keep the rest on AWS, keep the Bedrock switch | same file, section 2 |
| Primary providers | synthesis `claude-haiku-5-5` (Anthropic API); embeddings `voyage-4-lite`, 256 dimensions (Voyage AI) | same file, section 3 |
| Retained fallback | Bedrock Haiku 4.5 through the inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0` and Titan V2; selectable by Terraform variables; never run live | same file, sections 3 and 4 |
| Cost of the primary route | `claude-haiku-5-5` USD 0.10 input and USD 0.50 output per million tokens for prompts under 100,000 tokens; `voyage-4-lite` USD 0.02 per million tokens, the first 200M account tokens free | Documented on 2026-11-09 ([provider-fallback.md](report/provider-fallback.md), section 3 and 7); the actual Anthropic charge for the Q12 key was USD 0.08 on the Console ([evaluation](report/evaluation.md), group 4) |
| Data leaves AWS | question text and evidence snippets go to Anthropic; document and query text go to Voyage AI | provider-fallback.md, section 6 |
| Anthropic request rules | the API client never sends `temperature`, `top_p` or `top_k`; output is therefore not deterministic; a prompt of 100,000 estimated tokens or more is refused before the call | [modules/rag/README.md](../modules/rag/README.md), "Anthropic path" |

## 3. Model rate limits

| Provider | Limit | Status |
|---|---|---|
| Anthropic API (`claude-haiku-5-5`) | requests per minute, tokens per minute, daily caps for the account or key | **not verified**: no committed record gives the account's provider-side rate limits. Client side: the client never retries; a refusal is a typed `llm-refusal`; the runtime config bounds concurrency, retries and stage deadlines (see section 7) |
| Voyage AI (`voyage-4-lite`) | request and token rate limits | **not verified** for the account. Client defaults, which are not provider limits: at most 1,000 texts and 1,000,000 estimated tokens per request, at most 32,000 estimated tokens per text; HTTP 429, 5xx and transport errors retry with backoff ([modules/rag/README.md](../modules/rag/README.md), "Voyage path"). Observed: 10,000 vectors ingested at concurrency 8 and about 3.6 vectors per second with 0 rejected in ingest 2 ([performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md)); the first attempt was rejected with HTTP 401 for an invalid key, not a rate limit ([incident](incidents/2026-11-18-vectors-ingest-1-voyage-401.md)) |
| Bedrock | see section 2 | quota 0 |
| ScholarChain public semantic route | 50 requests per second per API key, burst 100 | Configured (`RateLimitSettings`); in the aborted 15B load run no request was answered 429 (0 x 429 in the run record, [decision log](agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md), load entry); that run used the semantic route with the model disabled |

## 4. Data and compute services

| Service | Limit or setting | Label | Source |
|---|---|---|---|
| Neptune Serverless | capacity 1 to 2.5 NCU (`neptune_min_ncu`, `neptune_max_ncu`), backups kept 7 days, TLS on port 8182, deletion protection on until cleanup | Configured | [course.tfvars](../infra/terraform/environments/course.tfvars) |
| Neptune engine version | chosen in the private variables file; not read here | not verified in this file | `neptune_engine_version` has no default ([phase12b-variables.tf](../infra/terraform/phase12b-variables.tf)) |
| Neptune query timeout hint | needs engine 1.3.2.0 or later; the reader uses the hint plus SDK call timeouts | Documented | [modules/storage/README.md](../modules/storage/README.md) |
| Neptune bulk-load poll budget | default 300 s or 300 polls, overridable to 14,400 s and 20,000 polls | Configured | storage README, "Loader poll budget" |
| Neptune load observed | Session 1: the storage load failed once on a dropped tunnel and then reached `graphState=LOAD_COMPLETED` with `--graph-only` | Observed | [phase-14 human gate](agent-runs/phase-14/human-gate.md) |
| Neptune openCypher support | `shortestPath()` and `allShortestPaths()` and dynamic property access are unsupported, so paths use bounded templates | Documented | storage README |
| S3 Vectors | dimensions 1 to 4,096; metadata 40 KiB and 50 keys; filterable metadata 2 KiB; at most 10 non-filterable keys; request 20 MiB; PutVectors 500; GetVectors 100; top-K 10,000; query pages of 100 results | Documented | storage README (links to the S3 Vectors limits page; date of reading not stated) |
| S3 Vectors as used | 5 indexes, 256 dimensions, cosine, non-filterable key `textS3Uri`; 10,000 vectors written; 5 of 5 known-item queries found their neighbor, SDK call times 91 to 365 ms (n = 5) | Configured and Observed | [course.tfvars](../infra/terraform/environments/course.tfvars), [retrieval-metrics.md](../experiments/results/phase16/retrieval/retrieval-metrics.md), [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) |
| DynamoDB | six tables, on-demand billing, point-in-time recovery, deletion protection; a transaction holds at most 100 actions and 4 MiB (the code uses two or three) | Configured, Documented | [infra/terraform/README.md](../infra/terraform/README.md), storage README |
| S3 | seven buckets with versioning, KMS encryption and public access blocked; user metadata limited to 2 KiB, 70 bytes reserved for the sha256 | Configured, Documented | Terraform README, storage README |
| S3 upload as observed | a 321,876,735-byte archive upload hit `RequestTimeout` on UploadPart with default concurrency and succeeded with `s3.max_concurrent_requests` 2 in about 52 minutes on a slow uplink | Observed | decision log, base-apply 1 incident and recovery entries |
| SQS | visibility timeout 300 s, long poll 20 s, retention 4 days (DLQ 14 days), `maxReceiveCount` 3 | Configured | Terraform README |
| ECS Fargate services | query-api, graph-service, semantic-service 512 CPU units and 1,024 MiB, 1 to 2 tasks; embedding-worker 512 and 1,024, 1 to 4 tasks by default (Session 2 ran all four services with minimum 1 and maximum 2); CPU target 60 percent, scale-out cooldown 60 s, scale-in cooldown 300 s | Configured | [phase12b-variables.tf](../infra/terraform/phase12b-variables.tf), [compute.tf](../infra/terraform/modules/runtime/compute.tf), decision log block 8 |
| ECS behavior observed | one scale-out from 1 to 2 tasks and back during the aborted load run; the poll brackets give an upper bound of 61.0 s from desired=2 to running=2; stopping a task recovered in 113 s and 68 s | Observed | [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) (summarized in [evaluation](report/evaluation.md), group 5) |
| Fargate vCPU, EIP, NAT and ALB account quotas | not checked from evidence | **not verified** | approval-request-14a.md, row 1 |
| EMR | release `emr-7.8.0`; one primary `r5.xlarge` and one core `m5.xlarge`; no task nodes; idle auto-termination at most 900 s; at most 75 minutes per run; Spark 3.5.4 and Scala 2.13.14 expected on the nodes | Configured | [course.tfvars](../infra/terraform/environments/course.tfvars), [15a-emr-size-100.json](../experiments/manifests/15a-emr-size-100.json), `scripts/config/release.conf` |
| EMR price basis | hourly estimate USD 0.555 for the pair (EC2 plus EMR rate per instance), 5,400 billed seconds in the estimate, estimate USD 0.84 | Configured | `G6 estimate` line in [emr-run-1.log](agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log) |
| EMR run observed | cluster window 16:26:54 to 17:06:31 UTC on 2026-11-18, 2,377.157 s billed at USD 0.555 per hour, measured USD 0.37; Hadoop prep, entity resolution and the class-origin check completed; the Spark step failed; no EMR cluster size completed end to end | Observed | [emr-actual-1end.log](agent-runs/phase-15/evidence/session-2/emr/emr-actual-1end.log), [evaluation](report/evaluation.md), group 5 |
| IAM role chaining | a role session reached through another role is limited to 1 hour; the operator session is 4 hours after a switch from the IAM-user session; an operator's deployer login had to be refreshed during the 19-minute Neptune apply | Documented, Observed | storage README (operator console steps); decision log, "Deployer login refreshed" entry |
| IAM managed policies per role | quota 10; the deployer used 7 | Documented | [approval-request-14a.md](agent-runs/phase-14/approval-request-14a.md) |

## 5. Budgets

| Item | Value | Source |
|---|---|---|
| Project ceiling | USD 25 across AWS, Anthropic and Voyage together (the earlier Terraform authoring assumed USD 200, replaced on 2026-11-16) | [provider-fallback.md](report/provider-fallback.md), section 7; [incident record](incidents/2026-11-16-p0-budget-modify-backup-check.md) |
| AWS budget alerts | actual-cost alerts at USD 18, 20 and 22, credits and refunds excluded, period 2026-10-01 to 2027-01-01. A budget is an alert, not a spending stop | incident record, Summary; Terraform README |
| AWS spend observed | USD 17.88 for 2026-11-01 to 2026-11-20 (credits excluded); the Session 2 day was USD 2.13; Budgets showed 17.87 of 25.00 | [cost-report.log](agent-runs/phase-15/evidence/session-2/c11/cost-report.log) |
| Anthropic and Voyage spend | Anthropic USD 0.08 (earlier phases' ledger 0.075075); Voyage USD 0.00, token count not read, the Session 2 window not isolable: unverified | same file |
| Combined and remaining | USD 17.96 combined, USD 7.04 remaining as of 2026-11-20T15:48:56Z; the later Q12 Anthropic key has a separate Console figure of USD 0.08 (2026-11-20 and 2026-11-21) that this report does not include | same file; [evaluation](report/evaluation.md), group 4 |
| LLM answer caps | 160 answers in four buckets under a shared USD 1.33 cap; embeddings capped at USD 0.30 with a token counter | [llm-allocation.json](../experiments/manifests/llm-allocation.json), rag README |
| EMR ledger caps | per run USD 3 at most, 4 live runs, cumulative cap USD 3.53; 3 of 4 runs and USD 2.05 used after Session 2 | `G6-CAPS` line, [emr-actual-1end.log](agent-runs/phase-15/evidence/session-2/emr/emr-actual-1end.log) |
| Billing lag | billing reports lag; runtime and capacity limits, not a Cost Explorer query, enforce each run | Terraform README |

## 6. Limits of the API

The API's own bounds (request size, depth, queue, rate, graph caps) are listed once in [docs/api.md](api.md) and defended in [docs/threat-model.md](threat-model.md), section 5. Key defaults: body 65,536 bytes; question 8,192 characters; 4 worker threads; queue 64; synchronous wait 15 s; workflow timeout 60 s; graph depth 3, limit 200, scan cap 10,000 edges, node cap 2,000, graph timeout 5 s; path depth 6.

## 7. Runtime configuration caveat

The packaged `scholarchain.config.v1.conf` is a local-development placeholder (for example `maxConcurrentLlmCalls` 4 and `synchronousDeadlineMs` 30000); the service limits in `ServiceConfig` are read from environment variables (`ServiceConfig.fromEnvironment`), which Terraform sets in aws mode. Stage deadlines for the planner and synthesis (5 s in the packaged runtime config) "may need the optional overrides for real model latency" ([modules/services/README.md](../modules/services/README.md)). The end-to-end latency observed with the live model was a median of 2,582 to 3,396 ms and a 95th percentile of 4,732 to 7,077 ms across the three evaluated runs ([evaluation](report/evaluation.md), group 5). The effective values of the deployed task definitions are not in the committed evidence: not verified.

## 8. What was not verified

- Account-level service quotas for Fargate, EIP, NAT, ALB, Neptune and S3 Vectors (no quota readout was saved).
- Anthropic and Voyage provider rate limits.
- The Bedrock restriction after 2026-11-10 (the AWS reply is not stored).
- Neptune engine version in the deployed cluster.
- Commands in this file were not replayed in 17A. The 17G clean-checkout replay (fresh clone of `main` at `d1d4fe7`, offline, 2026-11-22) did not run them individually; it ran `sbt -batch clean check` (1,773 tests succeeded, 0 failed, 2 canceled) and `bash scripts/smoke-local.sh --build` (`RESULT: PASS`). Live service limits remain not verified.

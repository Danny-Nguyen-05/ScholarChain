# Subphase 12C — real plan summary

Base/HEAD: `3b0855b9657a72b30e8ac43bd484161a9b886c79`, branch `phase-12`. Target account was verified through named profile `scholarchain-planner`; region `us-east-2`, AZs `us-east-2a`/`us-east-2b`. Environment `course`. No credentials or personal notification address were inspected or retained.

## Observed plan

Terraform **1.13.5**, AWS provider **6.44.0**, native plan exit **2** (`-detailed-exitcode`: successful plan with proposed changes), 2026-10-30T17:35:01.643348Z–17:35:03.365136Z.

**171 creates / 0 changes / 0 destroys / 0 replacements**: 169 AWS-managed objects and two local `terraform_data` guards. These are resource instances, not 171 independently billed services.

| Module | Creates |
|---|---:|
| `module.datalake` | 49 |
| `module.dynamodb` | 6 |
| `module.identity` | 25 |
| `module.messaging` | 5 |
| `module.network` | 58 |
| `module.observability` | 10 |
| `module.runtime` | 6 |
| `module.s3vectors` | 7 |
| `module.workflow` | 3 |
| `root` | 2 |

Neptune, EMR, Fargate runtime/services/tasks/autoscaling/ALB, budget resource and remote-state bootstrap are not activated in this plan. It does include an empty ECS cluster, four ECR repositories, private DNS namespace, fixed-queue Standard state machine, vector bucket/five indexes, seven ordinary buckets, six DynamoDB tables, SQS/DLQ, one NAT/EIP, two gateway endpoints, networking, IAM/KMS and monitoring.

The plan used fresh local state. R2's route-address rename shows no replacement in this plan. This is not evidence that no unmanaged resources or other state exists elsewhere; recheck state/inventory before deployment. No unexplained destruction or stateful replacement occurred.

## Plan hygiene and input provenance

Plan binary: `/tmp/scholarchain-phase12c-infra/course.tfplan` (68,686 bytes).

SHA-256: **`1e0eb776c6bebe0aea4a0d7070dbc2328953d7cc001e921b9ac674eb8b6bbd34`**.

Raw stdout, plan JSON and private tfvars stay outside Git/evidence. The excluded-file metadata/hashes are listed in `infra/retention-manifest.json`; sanitized resource/IAM summary is `infra/plan-summary.json`. All 63 actual configuration/lock inputs and the private non-secret tfvars preceded the plan and match final source; only README changed after it. Tests and README are included in the later final gate freeze. Details: `infra/plan-input-provenance.json` and `source-freeze.json`.

Exact command (cwd `/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform`):

```bash
TF_CLI_CONFIG_FILE=/tmp/scholarchain-phase12b-repair1-infra/terraformrc /tmp/scholarchain-phase12b-repair1-infra/terraform plan -input=false -no-color -detailed-exitcode -lock-timeout=30s -var-file=environments/course.tfvars -var-file=/tmp/scholarchain-phase12c-infra/course-plan.inputs.tfvars -out=/tmp/scholarchain-phase12c-infra/course.tfplan
```

## IAM and key policies in the selected plan

All roles below are **new planned roles**. No live policy was changed. Role trust is not a grant of deployment permission. JSON involving new resource ARNs is unknown until creation; the resource dependencies, source statements and mock contracts are reviewable, but the report does not invent resolved future ARNs. The machine summary enumerates every planned IAM instance/profile/policy and known trust/key policy.

| Identity | Trust and attached scope |
|---|---|
| Four service task roles: query-api, graph-service, semantic-service, embedding-worker | ECS task service, exact account and regional ECS source constraint. Each has its own inline data policy. Table/object read maps are service-specific. Query-api alone writes QuerySession/EvidenceBundle; worker writes RunLedger/ArtifactRegistry and consumes only work queue/sends failure DLQ. |
| query-api task | Reads configured table/object set plus idempotency index; writes session/evidence and designated rag objects; key use scoped to project CMK. No synthesis grant because model is unset. |
| graph-service task | Reads EntityLinkCache/ResearcherMetricCache/ArtifactRegistry and graph/artifacts objects, project-key decrypt only. No write actions. Neptune read-only query/status grant is conditional on the later cluster and is absent in this disabled plan. |
| semantic-service task | ArtifactRegistry/rag reads, exact five index GetIndex/GetVectors/QueryVectors; configured Titan V2 InvokeModel ARN only; CMK decrypt. |
| embedding-worker task | RunLedger/ArtifactRegistry/rag/artifacts scope; five exact index reads and PutVectors; Titan V2 InvokeModel only; queue receive/delete/visibility/attributes/URL and DLQ send, project-key permissions. |
| Four service execution roles | Separate per-service inline bootstrap policies: ECR GetAuthorizationToken global-resource exception; download from each configured repository, log-stream writes and only configured secret ARNs/key. Empty secret binding inputs do not grant secret access. |
| Neptune loader | rds.amazonaws.com plus SourceAccount; inline graph-bucket object/list/location read and project-key decrypt. Does not grant a human caller StartLoaderJob (N16). |
| EMR EC2 + instance profile | ec2.amazonaws.com; pipeline S3 reads/outputs, delete only allowed output pipeline/* prefixes, scoped CMK data use. No DynamoDB actions (B1). |
| EMR service | elasticmapreduce.amazonaws.com + SourceAccount. With EMR disabled, no control/disk policy instance is planned. N9 source fix attaches EBS key-use and AWS-resource-conditioned CreateGrant to this role upon guarded activation; new mocks assert role binding. N10 rejects wildcard ARN service/region/account in supplied control policy, preserving concrete EC2 Describe global-resource exception. Runtime/policy selection remains gated. |
| Deployment | Trust-only exact principal arn:aws:iam::530332961125:user/scholarchain-planner; no permission policy is attached. Planner remains read-only; later human-approved deployment permissions must be separately scoped, never root. |
| Workflow embedding-producer | states.amazonaws.com with exact state-machine ARN and SourceAccount; inline SendMessage only to fixed work/DLQ, CMK grants restricted by SQS ViaService and exact workflow encryption context. Phase13 must name the authorized StartExecution caller (N16). |
| Project CMK | Original explicit account-root IAM delegation unchanged. B3/N17 indexing.s3vectors.amazonaws.com gets exactly kms:Decrypt on this key, SourceAccount, this bucket plus its index/* ARN path, and documented encryption-context keys. Resource=* in a key policy means this key. Rotation stays on; KMS effectiveness remains live-unverified. |

There are 13 planned IAM roles, 11 inline policies and one EMR instance profile. The original key-admin cosmetic N6 is unchanged. TLS universal-principal/action statements are Deny. Object/index/log suffix globs stay constrained to project resources; trust policies use service-specific source constraints. Native mocks and bounded static checks are not effective-permission proofs.

## Cost and human actions

The shared **USD200 before-credit** ceiling includes all phases, optional9C/spikes/experiments/evaluation/API/retention and uncertainty. Base Nov15 00:00CST–Nov24 23:00CST =239h; upper Nov11 00:00CST–sameend =335h. See `cost/cost-memo.md`, its curated official Ohio rates and replayable calculations.

| Estimate before credits | 239h base | 335h upper |
|---|---:|---:|
| Actual inactive plan, zero-workload allowances | $16.95 | $21.75 |
| Actual inactive plan, illustrative store/API usage | $19.22 | $24.17 |
| Later activated minimum with stated usage/reserves | $157.94 | $194.91 |
| Later activated sustained task/Neptune maxima with reserves | $251.28 | $325.62 |

These are modeled scenarios, not actual bills or verified budget fit. The longer minimum case has only $5.09 margin. The active cases include provisional $15 EMR/$20 synthesis/$20 uncertainty reserves and one month illustrative retention; EC2/EBS runtime and synthesis-model prices are not yet finalized. Sustained maxima exceed the ceiling. Prefer the base window and bounded expensive runs; require exact manifests, baseline spend and final runtime/model prices before live approval. No automatic change to provisioned Neptune was made.

Before any paid work: separately approve/establish account-wide pre-spend budget alerts (currently ZERO budgets), human-enable Cost Explorer (status unverified), confirm private subscriber input, conservative unreported-cost headroom and bounded runtime/capacity/request/token controls. No paid CE query was authorized or made.

Before Phase14: review/accept12C; finishPhase13 script and live service composition/metric-publisher work; select/prove EMR runtime via separately approved12D if used; select Neptune engine/family; provide actual immutable images, auth/cursor secret ARNs and certificate/ingress; scope real deployment permissions; replan the intended active shape from clean accepted source/state, verify checksum/quotas/estimated costs, and obtain human-written apply/deploy approval. Internal HTTP(N15), absent pipeline loader/writer/workflow-caller identities(N16), optionalN3/N4/N6 and informationalN13 remain disclosed. Cleanup/evidence archival require separate approvals and retained inventories.

No apply/deployment/destruction/import, credential inspection, paid model/CE API call, commit/push, reviewer launch or12D preparation occurred.

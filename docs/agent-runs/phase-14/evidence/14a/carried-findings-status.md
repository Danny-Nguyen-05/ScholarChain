# Phase 14 status of carried findings (Subphase 14A)

The source lists stay unchanged:
- `docs/agent-runs/phase-12/evidence/12d-spike-closeout/carried-findings.md`;
- the Phase 13 status in `docs/agent-runs/phase-13/evidence/13c/carried-findings-status.md`.

This file records what changed in Phase 14. All results here are offline: nothing was applied and no live behavior was observed.

| # | Short | Phase 14 status | Decision / owner |
|---|---|---|---|
| 16 | Spike roles' trust policies | unchanged (mitigated; no IAM condition key on the trust document). `phase14-main` denies `iam:UpdateAssumeRolePolicy` on main roles. | infra-engineer |
| 17 | Boundary vs EMR-tagged instances/ENIs; live ENI stack tags | **live check moved to the Phase 15 apply.** EMR stays disabled in both Phase 14 plans (`emr_config.enabled = false`), so no EMR-created ENI exists before Phase 15. | user, 2026-11-06 |
| 24 | `DisassociateAddress` does not fix destroy | unchanged by design; the two-pass destroy stays the procedure | — |
| 25 | Any AMI/instance type into the tagged subnet | open (optional tightening) | — |

## New in Phase 14

| ID | Finding | Status | Owner |
|---|---|---|---|
| P14-1 | `BedrockConverseLlmClient` always sends `temperature` and a forced `SpecificToolChoice`. Claude 5.x models, and possibly GPT-6 Luna, reject these. The selected Claude Haiku 4.5 accepts both. | **carried.** Any later synthesis-model switch needs a reviewed client change. | rag-engineer (when a switch is proposed) |
| P14-2 | The main roles carried no permissions boundary, so the `phase14-main` CreateRole condition would deny `base-apply`. | fixed offline in 14A (D1) | infra-engineer |
| P14-3 | The EMR v2 tag `for-use-with-amazon-emr-managed-policies=true` was missing on the application subnets and the EMR node security group, so EMR would be denied at launch. | fixed offline in 14A (D2) | infra-engineer |
| P14-4 | Broad honest-list statements. The Revoke statement on any security group and the first tags of an adopted default group went beyond scope; so did KMS tag adoption, because a tagged foreign key gained administration (review 1 F2). Route 53 private-zone actions are unscoped, for Cloud Map. | **narrowed in repair round 1 (F2).** The default-SG adoption is removed, and KMS administration, use and grants live in the key policy, which names the deployer. The remaining residuals are the unscoped Route 53 actions and the `kms:TagResource` on `key/*`, limited by request tags and tag keys (a foreign key's values for those 12 tag keys can be overwritten). D4 and D6 are superseded for the removed statements. | infra-engineer |
| P14-5 | Live authorization of `phase14-main` is unobserved. A missed action shows up as AccessDenied during `base-apply`; it is fixed by a routed infra-engineer repair, a new reviewed deployer apply and a new plan. | open until 14B | infra-engineer |
| P14-6 | Live composition (review 1 F1): the services had no AWS mode. | **repaired offline in repair round 1.** The aws mode, the storage reader and the task environment are in; live behavior is unverified until 14B and 14C. | service-engineer, storage-engineer, infra-engineer |
| P14-7 | The `Null s3:prefix` HEAD-of-absent-key statement (`HeadAbsentRagKeyAs404NotListing`) rests on undocumented S3 condition behavior. | open; check early in 14B (an absent evidence key must return 404, not 403) | infra-engineer |
| P14-8 | `embedding_model_version`, `embedding_text_prefix` and `semantic_index_name` must match the 14C ingest config. | human values before the runtime plan (approval request row 18) | user |

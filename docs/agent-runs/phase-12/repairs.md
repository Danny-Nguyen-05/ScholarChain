
## Subphase 12A repair round 1

Scope: user authorized B1/B2 only on the existing uncommitted 12A state. No questions. REQUEST-CHANGES is retained verbatim in review.md. No agent may approve its own repair.

| ID | Blocking | Owner | Disposition | Acceptance check |
| --- | --- | --- | --- | --- |
| B1 | yes | infra-engineer | ROUTED | Remove EMR DynamoDB grants or justify a narrow subset excluding QuerySession/EvidenceBundle; assert no DynamoDB writes (or distinct-table authorization) in mock plan; update README; fmt/validate/test pass. |
| B2 | yes | infra-engineer | ROUTED | Derive data isolation from actual aws_route resources, remove route=[] mock dependency; retain a negative scratch mutation that fails when data gets a default route; fmt/validate/test pass. |
| N1 | no | infra-engineer, 12B | RECORDED ONLY; no repair authorized | Select runtime, document minimal prefix-scoped EMRFS delete/commit permissions, verify in12D or12C review. |
| N2 | no | infra-engineer with producer owner, 12B/13 | RECORDED ONLY; no repair authorized | Identify producer, grant queue-only SendMessage and required CMK GenerateDataKey/Decrypt. |
| N3 | no | infra-engineer | RECORDED ONLY; no general mock-ARN cleanup authorized | Distinct per-table ARN tests if resource-scoped B1 alternative is used; no-DynamoDB assertion is allowed by B1. Bucket mock differentiation remains recommendation. |
| N4 | no | infra-engineer | RECORDED ONLY; no unrelated policy test expansion authorized | Extend wildcard checks to loader/emr/KMS in future; B1 adds only its necessary emr assertion now. |
| N5 | no | infra-engineer, 12B | RECORDED ONLY; no repair authorized | Use separate SSE-S3 access-log bucket or document ALB access logging off. |
| N6 | no | infra-engineer | RECORDED ONLY; no cleanup authorized | Optional future KMS CreateKey/duplicate action cleanup. |
| N7 | no | coordinator/build-engineer | RECORDED; required gate ordering applied, original evidence unchanged | Full repair-round sbt gate starts after final Terraform edits/source freeze; retain times/hashes. |
| N8 | no for12A | human architect | RECORDED ONLY; no scope change authorized | Human/instructor decision about omitted Step Functions before phase closure; operational scripts remain Phase13. |

Unverified gates retained: real plan, live IAM/KMS, quotas/regions, costs/budget filter, scanner, Neptune sizing, EMR runtime. AWS account/profile/region/budget remain unset; account reminder before12C or earlier approved12D.

### Implementation handoff — independent recheck pending

- B1: IMPLEMENTED, pending reviewer acceptance. All EMR DynamoDB permissions removed; explicit no-DynamoDB/no-wildcard assertion fails before removal and passes after.
- B2: IMPLEMENTED, pending reviewer acceptance. Actual route-resource control with distinct mock route-table IDs; mocked inline route list removed; canonical and standalone-new-file negative cases each fail12/1; repaired baseline13/0.
- Final Terraform init/fmt-check/validate/test0;29assertions/6expected-failure cases. Post-freeze JDK17 fullcheck0:1253tests/156fresh XML,0failures/errors/skips. Exactly5scoped source files changed.
- N1–N8 remain carried with no unrelated repairs. B1 necessarily covers EMR policy as noted under N4; required new gate addresses N7 ordering while leaving original evidence untouched. No finding is marked reviewer-accepted or CLOSED by implementation.
- Evidence: evidence/12a-repair-1/. Next: user-launched read-only recheck; no later subphase.

## Subphase 12A repair round 1 — independent recheck

User-supplied independent verdict: APPROVE for Subphase12A including repair round1. Complete returned review/work order appended verbatim to review.md. This records independent acceptance of source/evidence only, not human deployment approval.

| ID | Owner | Independent disposition / next acceptance check |
| --- | --- | --- |
| B1 | infra-engineer | ACCEPTED (closed). EMR DynamoDB grant removed; before/after regression accepted. |
| B2 | infra-engineer | ACCEPTED (closed). Actual-resource route isolation plus canonical guard and two negative cases accepted. |
| N1 | infra-engineer,12B | CARRIED. Resolve minimal prefix-scoped EMRFS s3:DeleteObject when EMR authored; verify in12C/12D. |
| N2 | infra-engineer,12B/13 | CARRIED. Identify queue producer and grant queue-only send/required CMK access. |
| N3 | infra-engineer | CARRIED (optional). B1 no-DynamoDB alternative accepted; general bucket ARN differentiation still recommended. |
| N4 | infra-engineer | CARRIED (optional). EMR assertion added through B1; loader/KMS coverage still optional/open. |
| N5 | infra-engineer,12B | CARRIED. Resolve access-log SSE-S3 requirement or document ALB access logs off. |
| N6 | infra-engineer | CARRIED (optional). KMS action-list cleanup. |
| N7 | coordinator/build-engineer | RESOLVED procedurally by independent reviewer. Post-freeze full gate,42 source files unchanged. |
| N8 | human architect/instructor | OPEN. Resolve Step Functions course discrepancy before full phase closure; no waiver implied. Scripts deferred13 per work order. |
| R1 | infra-engineer,12B | INFO. Keep every route/route-table resource within modules/network; extend guard before exporting route-table IDs. 12B reviewer verifies resource locations. |
| R2 | infra-engineer,12C | INFO. Address rename harmless without state; real12C plan must show no route replacements. No state inspection or migration performed here. |
| R3 | coordinator | INFO. Previous review wording preserved but rendered emphasis missing; no action required and prior record not rewritten. |

Next gate: human commit of approved12A source, repair and review records. Await commit SHA; never commit/push as agent. Do not begin12B or its implementation until commit confirmed and Step0 answers received. Account/profile/region/budget remain unset; AWS account reminder before12C or earlier approved12D. No human-owned gate/approval/commit file authored or modified.

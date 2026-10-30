
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


## Subphase 12B — carried findings and accepted direction

Coordinator routing record, not independent acceptance. User accepted all Step 0 recommendations (`evidence/12b/step-0-answers.md`).

| ID | Owner | 12B direction / acceptance check |
| --- | --- | --- |
| B1/B2 | infra-engineer | Previously accepted closed. Preserve EMR no-DynamoDB action assertion, resource-based data-route assertion and route declaration guard. |
| N1 | infra-engineer | Implement prefix-scoped delete only for EMR output commit/temporary cleanup. Runtime effectiveness remains for 12C/12D. |
| N2 | infra-engineer; Phase 13 caller owner | Add separate bounded-workflow/producer identity with queue-only send and required CMK access. Production caller remains explicitly deferred. |
| N3/N4/N6 | infra-engineer | Optional carry. No cosmetic or unrelated repair requested; any resource-test differentiation needed by new controls is within 12B. |
| N5 | infra-engineer | User selected ALB access logging off. Never direct S3 ALB access logs to the existing SSE-KMS logs bucket. |
| N7 | coordinator/build-engineer | Preserve procedural resolution: full JDK 17 gate after final Terraform/source freeze; compare source hashes across gate. |
| N8 | human architect; infra-engineer implementation | User selected addition of a minimal functional Step Functions state machine plus least-privilege role. Verify actual bounded workflow, retry/dead-letter behavior and IAM. Do not claim instructor approval or full course closure. |
| R1 | infra-engineer | Keep every route/route-table declaration in modules/network; no route-table ID export without extending guard. |
| R2 | infra-engineer, 12C | No known prior state; live plan must still show no unintended route replacements. No state read/migration authorized. |
| R3 | coordinator | Informational rendered-emphasis observation; no alteration of original review text. |

No source or report has been independently approved for 12B. OpenSearch, EventBridge and Glue remain omitted unless an implemented use requires them. Operational scripts remain Phase 13. AWS account/profile/region/budget pending; no cloud calls or spending authorized.

### Subphase 12B — implementation disposition (independent review pending)

- B1/B2 controls preserved; retained 12A mock runs remain green. R1 now also has a source guard against route declarations outside modules/network; coordinator found all seven route/route-table/association declarations there. No route-table ID is exported. R2 still needs the later real plan; R3 needs no repair.
- N1 implemented: EMR output-prefix delete permission, with no raw-bucket delete and no DynamoDB actions. Actual EMRFS commit behavior remains unverified.
- N2 implemented at infrastructure level: fixed-work-queue Step Functions producer role, exact work/DLQ send resources, separate scoped SQS and workflow CMK grants, bounded retries/failure routing. The authorized production caller remains Phase 13.
- N5 implemented as selected: ALB access logging off, SSE-KMS destination incompatibility documented. No extra access-log bucket added.
- N7 preserved procedurally: final Terraform source freeze precedes the full JDK 17 gate; final before/after verification is recorded separately.
- N8 selected source addition implemented: functional Step Functions state machine and role now present. Independent reviewer must assess course coverage; no waiver, instructor approval, live effectiveness or full-phase closure is claimed. Scripts remain deferred to Phase 13.
- N3/N4/N6 remain optional carry items. New assertions cover the new graph/vector/producer/workflow policies as needed; no cosmetic KMS action-list cleanup or general mock-bucket rewrite was requested.

New 12B contract fixes made during implementation: distinct workflow CMK encryption-context permission; S3 Vectors non-filterable textS3Uri metadata; supported DynamoDB throttle metric dimensions; CloudWatch metric-array shape; shared graph cursor-key ARN prerequisite for replicas. See evidence/12b/coordinator-dependency-routing.md and the 18 new native mock runs. These are owner implementation changes, not an independent reviewer acceptance.


## Subphase 12B repair round 1

Independent user-supplied review: REQUEST-CHANGES; one blocking finding. Full review/work order appended verbatim under Subphase 12B in review.md and retained in evidence/12b-repair-1/user-supplied-external-review.txt. No questions for this repair. Route ONLY B3 to infra-engineer; no reviewer invocation, commit/push, live AWS activity or paid call.

| ID | Severity / disposition | Owner | Acceptance / carry check |
| --- | --- | --- | --- |
| B3 | Medium; BLOCKING; OPEN, routed | infra-engineer | Add one S3 Vectors indexing service-principal key-policy Allow with Action exactly [kms:Decrypt], Resource meaning this key, exact account/project bucket SourceArn and documented encryption-context keys. Build ARN without module cycle; preserve root delegation. Add precise mock assertion; retain pre-fix red/fixed green and source-continuity proof; fmt/validate/test then full post-freeze JDK17 gate. README one control note only. |
| N9 | Low; NONBLOCKING, NOT REPAIRED | infra-engineer before EMR activation /12C or12D | EMR service role needs scoped EBS-encryption key use (or activation guard requires/asserts it). |
| N10 | Low; NONBLOCKING, NOT REPAIRED | infra-engineer /12C | Tighten wildcard service/region/account ARN checks or list for human security sign-off; negative case. |
| N11 | Low; PLAUSIBLE; NONBLOCKING, NOT REPAIRED | infra-engineer /12C | Omit disabled-resource widgets or verify empty metric arrays accepted. |
| N12 | Low; NONBLOCKING, NOT REPAIRED | infra-engineer native metrics; Phase13/14 publisher owner | Add native Neptune client/server errors and DDB conditional failures/latency coverage in later scope. |
| N13 | Info; NONBLOCKING, NOT REPAIRED | infra-engineer | HTTPS test currently inspects only the named HTTPS listener; current source has no HTTP listener. |
| N14 | Info; NONBLOCKING, NOT REPAIRED | infra-engineer | Consider IsPresent plus IsString for deliberate InvalidWork error on missing workItem. |
| N15 | Info; NONBLOCKING, NOT REPAIRED | infra-engineer /12C security self-review | Disclose internal ALB-to-query and query-to-services plain HTTP against encryption-in-transit requirement. |
| N16 | Info; NONBLOCKING, NOT REPAIRED | infra-engineer /12C, Phase13 loader owner | Record absent StartLoaderJob and pipeline DDB writer identities; caller/loader wiring deferred. |

Carried: B1/B2 preserved; N1/N2/N5 resolved as answered (live effectiveness remains unverified); N3/N4/N6 optional carry (B3 assertion overlaps only required KMS coverage); N7 procedural post-freeze gate; N8 addressed by authored Step Functions without instructor approval; R1 confirmed; R2 needs12C real plan; R3 no action. Do not change any N9–N16 implementation this round. AWS account/profile/region/budget remain pending; reminder before12C or an earlier separately approved12D. Human-owned records remain untouched.

### Subphase 12B repair round 1 — implementation result, recheck pending

B3 owner repair is complete: one scoped indexing-service decrypt statement, one exact native assertion and one README note. Red 30/1, then green 31/0; 52 assertions, 16 expected-failure cases. Full post-freeze JDK 17 gate passed; counts/timing/hash in repair owner/test sections. Exactly three infrastructure files changed; other 64 and original 12B evidence unchanged. N9–N16 remain NOT REPAIRED. Independent acceptance belongs to the user-launched recheck. No next subphase, commit, push or cloud call.


## Subphase 12B repair round 1 — independent recheck

User-supplied independent verdict: APPROVE for 12B including repair round 1. Complete review and next work order appended verbatim to review.md under Subphase 12B repair round 1. This records the external verdict; it is not an implementation-agent approval or a human cloud authorization.

| ID | Disposition | Owner / next check |
| --- | --- | --- |
| B3 | ACCEPTED (closed) by independent reviewer. Exact indexing service decrypt statement, strict mock assertion and genuine pre-fix red/fixed green accepted. | No remaining 12B blocker. Live effectiveness remains unverified. |
| N17 | NEW; Low; PLAUSIBLE; nonblocking. Exact bucket SourceArn may not cover background indexing requests using index ARNs. | infra-engineer; candidate 12C change to [bucket ARN, bucket ARN + "/index/*"] with assertion update, or verify actual source ARN in Phase 14 smoke. No source change authorized/performed at this commit checkpoint. |
| N18 | NEW; Info. Read-only terraform version call overlapped full gate; all 521 source snapshots remained unchanged. | No impact; no action. |
| N9 | CARRIED; nonblocking; EMR service-role KMS for EBS encryption. | infra-engineer before EMR activation /12C review or12D. |
| N10 | CARRIED; nonblocking; EMR control-policy wildcard service/region/account ARN guard. | infra-engineer /12C security review or before EMR activation. |
| N11 | CARRIED; PLAUSIBLE; nonblocking; empty disabled-resource dashboard arrays. | infra-engineer /12C confirmation or selected repair. |
| N12 | CARRIED; Low; native Neptune errors and DDB conditional-failure/latency panels missing. | infra-engineer for native panels; Phase13/14 publisher owner for application metrics. |
| N13 | CARRIED; Info; HTTPS test inspects named listener only. | infra-engineer; no current HTTP listener. |
| N14 | CARRIED; Info; workflow missing workItem should use IsPresent for intended error name. | infra-engineer; optional later selected scope. |
| N15 | CARRIED; Info; internal service traffic uses HTTP. | Disclose in12C security self-review against encryption in transit. |
| N16 | CARRIED; Info; loader/writer identities absent. | Record in12C; implementation deferred Phase13. |
| N1/N2/N5 | RESOLVED as answered; unchanged. | Live commit/producer/access-log behavior still subject to later gates. |
| N3/N4/N6 | OPTIONAL carry. B3 adds first key-policy assertion, partly addressing N4. | No unrelated repair. |
| N7 | PROCEDURAL resolution held; post-freeze full gate and source continuity confirmed. | Preserve later gate ordering. |
| N8 | ADDRESSED in source without instructor approval. | No full-course compliance or waiver claimed. |
| B1/B2/R1 | PRESERVED; assertions and route guard unchanged and green. | Keep invariants. |
| R2 | UNVERIFIED. | Requires12C real plan and no unexplained route replacements. |
| R3 | INFO; no action. | Prior review text remains untouched. |

Next gate: commit confirmation of approved12B source, repair, evidence and review records on phase-12. Current HEAD remains a83f62e9af56058a170075f98c4e027d039567ec with uncommitted work. Ask user for commit SHA and wait; never commit or push without a new explicit request. Do not begin12C questions/edits/account calls before the commit checkpoint. Account/profile/region/budget and explicit read-only planning authorization are required before12C account access. Account reminder is now due for12C; earlier12D would require its own written bounded approval. Human-owned gate/commit/approval files untouched.


## Subphase 12C — selected follow-ups

User accepted the remaining recommendations on 2026-10-30. Owner: infra-engineer for infra/terraform/** only. Verification is completed in the final12C report, not inferred from this routing record.

- N9 ROUTED: put scoped CMK EBS-use/grant permissions on the EMR service role; retain disabled activation and assert the service-role binding.
- N10 ROUTED: reject wildcard service/account/region components in write/control resource ARNs, preserving only the justified EC2 Describe global exception; add negative inputs.
- N11 ROUTED: omit EMR/Neptune widgets for inactive/null sources; prove default/active shapes.
- N12 ROUTED: chart native Neptune client/server errors and DynamoDB conditional failures/request latency with correct dimensions.
- N14 ROUTED: IsPresent + IsString for workflow workItem, safely choose InvalidWork for missing input.
- N17 ROUTED: service-principal CMK SourceArn includes only this vector bucket and its index/* path, retaining exact action/account/context conditions.

B1/B2/B3/R1 remain invariants; R2 requires the real plan replacement check. N13 remains information only. N15 internal HTTP and N16 Phase13 loader/writer identities remain disclosed, not repaired. Optional N3/N4/N6 are not expanded into unrelated work. N7 retains the post-freeze gate rule; N8 Step Functions remains authored without new instructor claims; N18 had no impact.

The independent static guard under tests/** is test-engineer-owned. Coordinator alone owns these reports. No reviewer is invoked; user launches review at handoff.

### Subphase 12C selected follow-ups — owner completion, review pending

Infra owner reports N9/N10/N11/N12/N14/N17 implemented with retained RED v2 and 40/0 GREEN. N9 binds the disk policy to the service role and project CMK; N10 rejects wildcard ARN segments; N11 omits disabled widgets; N12 adds native error/failure/latency panels; N14 guards missing input; N17 covers the project bucket and index SourceArn paths. This is an implementation disposition, not independent approval. See evidence/12c/infra/{owner-report.md,red-proof.json,delta.patch,coverage-counts.json}.

B1/B2/B3/R1 remain asserted. R2 has no address replacement in the fresh-state real plan. N13, N15/N16 and optional N3/N4/N6 were not repaired; N15/N16 are disclosed in security-self-review.md.


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


## Subphase12D — preparation dependencies

No new independent review was received. These are preparation dependencies, not reviewer defects or live execution results.

- Portable G1 CLI inputs and shared/distributed filesystem behavior: spark-engineer/infra-engineer; Phase6Main NIO metadata and Spark/Hadoop Parquet must address the same shared files. No application adaptation is authorized or applied by this preparation.
- Class-origin probe and baseline: spark-engineer/build owner; driver AND executor origins/versions, distributed DataFrame/Parquet proof, local/distributed row/hash comparison with the same assembledJAR and logical bindings. Hashes retain nestedcontext.runId, so historical differently packaged runs are not a valid comparison baseline.
- Independent deadline and cleanup: infra-engineer/deploy-engineer; two-hour total includes provisioning/retries/teardown. Idle termination does not enforce this clock. Future Terraform-authored deadline mechanism and exact reviewed execution plan required.
- Monitoring/access/human gate: human architect; live account-wide USD200 before-credit monitor, private subscriber and explicit project period, CostExplorer enabled, conservative remaining allowance, separate non-root temporary deployment identity and user-written exact live approval. Last12Cbudget count0; no new account check.
- PriorB1/B2/B3 and R1 preserved. N19/N20 and all other12Cnonblocking/open live gates are carried unchanged. No unrelated repairs this round.


## Subphase 12D preparation — repair round 1

- F1 Medium, blocking, OPEN; owner infra-engineer. Add and validate course/project/environment/owner/expiration_date tags, retention-aware expiration, exact mock assertion and genuine missing-tag RED; all three roots and static/build gates must pass with new freeze. Fold alert-threshold rationale into this repair.
- F2 Medium, nonblocking for preparation; coordinator discloses USD15−10=USD5 remaining all-EMR reserve, USD5.09 upper-window margin, later allocation decisions. Human decision on keeping/lowering spike cap is pending.
- F3 Low, nonblocking; infra-engineer README must disclose deprecated CostTypes and require credits/refunds exclusion readback or alternative routed for review.
- F4 Low, nonblocking; infra-engineer README must say zero-resource claim is based on source inspection. Optional test-engineer scope is not assigned.
- F5 Low, nonblocking; coordinator records historical environment omission as erratum and includes only selected non-secret environment in new command records; never reconstruct missing historical metadata as observed.
- F6 Low, nonblocking; coordinator restores spacing in untracked notes, preserving originals, and appends readable errata to tracked records. Do not rewrite prior record bytes.
- F7 Medium, carried/nonblocking; human decision pending on existing Gmail-bearing source paths. No redaction/history rewrite or changes to earlier human records. Future references use neutral repository plan copy.
- Info: document alert-threshold rationale; existing guard omits .tftest.hcl; disclose excluded stale TestRunMarkerSpec XML. B1/B2/B3/R1 and N19/N20 unchanged.
- Step0 answers are required before implementation. All live prerequisites remain unmet; no account calls, real plan/apply/destroy/import, paid calls, reviewers, commits/pushes or Phase13.


## Subphase 12D preparation repair round 1 — readable erratum

The earlier 12D preparation text is preserved byte-for-byte. Read its joined words as ordinary spaced prose: for example, “203 frozen files at 2026-10-30”, “main foundation budget”, “before inventory”, “assembled JAR” and “13 files”. These spacing corrections change no observed gate result.

The original preparation had 51 passing Terraform runs, 69 assertions, 26 expected-failure runs, a 203-file freeze and a full JDK 17 check with 1,255 tests in 157 fresh XML reports. One stale TestRunMarkerSpec report under project/verification/target was excluded. Those results describe the original source state; use the repair-round evidence for the repaired source and new gate results.

F2 allocation clarification: the original USD 15 reserve covers ALL EMR spikes and experiments. The former USD 10 spike proposal would leave USD 5 for later EMR. The user now chose a USD 5 proposed spike cap, leaving USD 10 if fully spent. The 12C upper-window margin remains USD 5.09. Later EMR runs require a new allocation decision and exact all-resource costing. Nothing increases the shared USD 200 before-credit ceiling or authorizes spending.

F5 metadata clarification: historical Terraform records omit their environment field. The original prose names TF_CLI_CONFIG_FILE, but the missing per-command observation is not reconstructed as fact. New repair records explicitly retain selected non-secret environment variables. Original logs and metadata remain unchanged.

F7 decision transcription: use neutral references in new material and preserve existing records/history. No historical redaction, human-record rewrite or history rewrite is authorized. The neutral authority reference is the repository copy at docs/agent-runs/phase-12/evidence/12c/phase12-plan-at-start.md.


## Subphase 12D preparation repair round 1 — implementation disposition

F1 is implemented and awaiting independent acceptance. F2–F6 corrections and disclosures are complete within the assigned offline scope. F7 is recorded as the user's decision to use neutral future references while preserving existing records/history. No reviewer acceptance or live approval is inferred. Native checks passed 53/0; the full post-freeze repository gate passed. See evidence/12d-preparation-repair-1/ for exact counts, timestamps and hashes.


## Subphase 12D preparation repair round 1 — independent recheck

- Independent user-launched recheck: APPROVE for preparation repair round 1 only. F1 is ACCEPTED by the external reviewer; F2–F7 dispositions verified. No live execution, plan, spending or apply approval.
- New N1 Low, NONBLOCKING, carried; owner infra-engineer. Billing-bootstrap README.md:30 says tag permissions “if used” although all five tags are mandatory. At the next billing-bootstrap or deployment-identity touch, state tagging actions are required and verify them against current AWS action documentation before policy review/apply. No source edit in this record-only turn.
- I1 Info: sensitive-value RED accepted by reviewer using sole-mutation, genuine assertion failure and matching GREEN evidence. No repair required.
- I2 Info: future build records should retain the JDK PATH prefix instead of the full inherited tool path. Preserve existing records unchanged.
- I3 Info: dollar cap is not an enforceable billing cutoff; the existing spike README retains that disclosure. No new live gate is passed.
- All live prerequisites retained unchanged: active monitor/recipient proof; usable cost data and conservative remaining allowance; separate non-root temporary deployment identity; portable G1; same-JAR baseline; actual driver/executor origins; shared-filesystem proof; independent elapsed deadline; genuine isolated plan/checksum/review; human-written exact execution and teardown approval.
- B1/B2/B3/R1 and N19/N20 carried unchanged; planner remains read-only. Continuation selection is pending. No AWS/paid calls, real plan/apply/destroy/import, private-input reads, human approval writes, reviewers, commits, pushes or Phase 13.


## Subphase 12D billing-monitor plan — N1 documentation disposition

The preparation recheck's N1 tagging-permissions wording is corrected in billing-bootstrap/README.md. Tagged creation requires budgets:ModifyBudget plus budgets:TagResource; reads/tag readback require budgets:ViewBudget and budgets:ListTagsForResource; removals use budgets:UntagResource. The official service authorization reference is cited. No IAM policy or grant was created. The authorized plan proposes one budget creation and nothing was applied. Independent review pending. All prior live blockers and B1/B2/B3/R1/N19/N20 remain unchanged.


## Subphase 12D billing-plan review — carried findings and decisions

- User-launched review verdict: APPROVE for the read-only billing plan ONLY. No execution, IAM grant, spending, apply or live 12D approval.
- Billing-plan review B1 — Low, NONBLOCKING, carried to infra-engineer. The reported IAM action list is incomplete and aws-portal actions may not support budget-ARN scoping. Resolve against current official action/resource documentation before any deployment-identity policy or execution plan. No IAM/source correction in this record-only turn. Distinct from the earlier 12A/12B B1 finding.
- Billing-plan review B2 — Low, NONBLOCKING, human retention decision PENDING. Protected /tmp/scholarchain-phase12d-billing-plan artifacts contain the plaintext recipient (directly or within plan/JSON/logs). Human chooses deletion or a stated retention location/purpose. The agent neither reads nor deletes them in this turn. Distinct from the earlier 12A B2 route-test finding.
- The supplied review contains the 14-field report and mentions Info in the work order; no additional detailed Info finding text was supplied. Record what was provided without inventing details.
- Saved plan remains bound to read-only scholarchain-planner, not an execution plan for another identity. A new execution identity requires its own fresh plan/checksum/review and human-written apply gate. Never elevate or repurpose planner.
- Budget is not active. CUSTOM/CostTypes/tag acceptance, accounting, alert delivery, usable cost data and remaining allowance unverified. USD 5 proposed spike cap and USD 10 remaining all-EMR reserve unchanged; no spending authorized.
- All EMR/G1/same-JAR/probe/filesystem/deadline/isolated-plan/teardown/human-approval prerequisites remain open. Earlier B1/B2/B3/R1 and N19/N20 remain carried unchanged.
- No source/infra edit, AWS/account/paid call, Terraform invocation, credential/state/private-input/raw-plan read, private-artifact deletion, human approval write, reviewer launch, commit, push or Phase 13 in this record-only task.


## Subphase 12D billing execution preparation

- Billing review B1: drafted exact-budget API permission audit and five-action policy, distinguishing current Budgets actions from legacy global aws-portal actions. Documentation/source work complete; independent review and live authorization remain open. This is not old 12A B1.
- Billing review B2: human reports deleting /tmp/scholarchain-phase12d-billing-plan; metadata-only check confirms absence. No private input recovered. Historical sanitized packet preserved; no execution artifact remains. This is not old 12A B2.
- Actual operator and bootstrap route remain human decisions. No root-run Terraform, planner elevation, console exception, IAM grant or apply inferred.
- Prior B1/B2/B3/R1 and N19/N20 unchanged. Other open items, live prerequisites and the USD 5 proposed cap/USD 10 remaining EMR reserve/USD 5.09 upper-window margin unchanged. No new repair outside billing policy preparation.


## Subphase 12D billing execution preparation — independent review dispositions

- User-launched verdict APPROVE for OFFLINE PREPARATION ONLY. No authorization for IAM identity/role/policy installation, console exception, real plan/apply, budget creation, spending or Phase 12D completion.
- Billing B1 RESOLVED by the reviewed exact-budget five-action policy and documented exclusion of legacy global aws-portal permissions. Live authorization remains unverified. This is distinct from earlier infrastructure B1.
- E1 — Low, NONBLOCKING, carried to infra-engineer at the next touch of billing-execution/variables.tf:31: compare the planner name case-insensitively using lower(...) and add a mixed-case planner rejection test. No repair this record-only turn.
- E2 — Info: the billing README audit-link insertion comprises two sentences; the prior handoff's one-sentence wording is imprecise. Preserve earlier records; no source change needed here.
- E3 — Info, pending human identity/credential-path decision: browser aws login MFA-context compatibility is unverified. Access-key/MFA AssumeRole conflicts with the no-long-lived-key stance; Identity Center would need a separately reviewed design. No fallback is selected or approved.
- Deployment identity, installed billing role/policy, execution plan, active monitor, recipient delivery, usable cost data and conservative remaining allowance remain absent or unverified by this work. Old planner-bound plan was deleted and is not reusable. Planner remains read-only, never trusted or elevated.
- Proposed USD 5 spike cap, USD 10 remaining all-EMR reserve and USD 5.09 upper-window margin unchanged and unapproved. Every G1/same-JAR/class-origin/filesystem/elapsed-deadline/isolated-plan/teardown gate open. Prior B1/B2/B3/R1 and N19/N20 carried unchanged.
- Human choices remain pending; answers will be recorded only as coordinator transcriptions, never as exception, IAM, plan, apply or spending approval. No source edit, AWS/IAM/Terraform/build call, secret/state/private-input read, console action, human-owned record edit, agent/reviewer launch, commit, push or Phase 13 in this continuation.


## Subphase 12D offline browser-login path evaluation

- E3 evaluation: the original IAM-user OAuth MFA-context inheritance remains unverified. Recommended next offline design is candidate B: operator console MFA → strict-MFA Switch Role → role-selected aws login → native provider login_session. This avoids reliance on inheritance or a second STS call; composition is not live-proven.
- New documented design dependency: login requires both signin:AuthorizeOAuth2Access and signin:CreateOAuth2Token. For B, propose a separate exact account/region/localhost statement on the billing role. No grant, policy-source amendment or install in this evaluation.
- Provider compatibility: CLI can prompt for explicit MFA, but the pinned provider's shared-profile MFA path lacks an interactive token callback. Candidate A therefore needs a separately reviewed credential-process bridge. It is an alternative, never an automatic fallback. GetSessionToken with temporary login credentials is not an accepted shortcut.
- E1 remains Low/nonblocking and untouched until the next billing-execution source edit; include lower(...) comparison and mixed-case planner negative then. E2 two-sentence wording correction remains append-only historical clarification. Billing B1 remains resolved; old B1/B2/B3/R1 and N19/N20 unchanged.
- User selected evaluation recommendations and proposed operator name only; no actual identity/ARN verified, human exception or live approval inferred. Planner remains read-only and never trusted/elevated. All live prerequisites and financial bounds unchanged.


## Subphase 12D offline login-path evaluation — independent review dispositions

- Verdict APPROVE for OFFLINE LOGIN-PATH EVALUATION ONLY. No setup, console exception, login, installed IAM grant, account plan/apply, spending or full 12D approval.
- L1 — Info, input for infra-engineer's next offline amendment: proposed exact-localhost scope follows AWS's managed-policy pattern, while the authorization reference also lists console resources. Live scope verification remains open; denial must stop for review with no automatic console/global widening. Ask whether to add exact signin:OAuthClientId same-device pin; recommended yes, disclosed as an additional possible live denial.
- L2 — Info, input for the human choice and infra-engineer documentation: specify bootstrap-assigned console password/MFA, forced-reset choice and any ChangePassword permission, and that no MFA self-management is included without separate review. Recommended no forced reset grant and bootstrap-assigned MFA; no answer inferred.
- L3 — Info, input for infra-engineer documentation: login/role/refresh lifetime remains unverified. Mid-plan expiry must fail closed, with separate re-login on the dedicated profile, never fallback to root/planner or silent permission widening.
- E1 remains carried until the authorized source amendment: lower(operator_user_arn) planner comparison and mixed-case rejection test. Candidate B remains inferred from documentation; A/permanent-key/Identity Center fallbacks not selected. Earlier B1/B2/B3/R1 and N19/N20 unchanged.
- Step 0 choices are PENDING; no amendment or source edit starts until the human answers. Answers will be coordinator transcriptions, not approval/exception records. Planner remains read-only. All billing/EMR live prerequisites and proposed USD 5 cap/USD 10 reserve/USD 5.09 margin unchanged.


## Subphase 12D offline billing-execution policy amendment

- E1 implementation completed, independent review pending: planner comparison case-folded with lower(operator_user_arn); mixed-case and mixed-case-under-path rejection tests pass. Old-guard RED catches first missing expected failure (14/1/4 skipped); no claim the skipped path case has individual RED proof.
- L1 addressed in offline draft: separate exact two-action localhost login policy with strict same-device OAuthClientId condition; full independent JSON/binding assertions and widening RED. Managed-policy scope inference/extra-condition denial risk retained; never automatically widen to console/global/remote. Live acceptance unverified.
- L2 documentation follows user-selected bootstrap-set password with no forced reset or ChangePassword grant; bootstrap-assigned MFA with no self-management grant. No password, device, identity or permission is created.
- L3 documented fail-closed mid-plan expiry and dedicated-profile re-login/fresh plan/checksum/review under later authorization; no root/planner/fallback or partial-plan reuse. Refresh-chain lifetime remains unverified.
- Budget/trust/caller bodies remain byte-identical, five-action budget scope/strict MFA unchanged. Billing B1 stays resolved; earlier B1/B2/B3/R1/N19/N20 and all unrelated source unchanged.
- User's defaults authorize this offline amendment only. No human gate/exception, actual operator/role, login grant, budget/monitor/delivery/cost-data or live EMR approval inferred. USD 5 proposed cap/USD 10 reserve/USD 5.09 margin unchanged and unapproved.


## Subphase 12D offline billing-execution policy amendment — independent review dispositions

- Verdict APPROVE for OFFLINE AMENDMENT ONLY. No identity setup, console exception, login/account/IAM call, real plan/apply, spending or Phase 12D completion authorized.
- E1 RESOLVED by the reviewed case-insensitive planner guard and mixed-case negative tests.
- L1–L3 ADDRESSED in README: scope/client-ID inference and denial stop without widening; bootstrap-set password without forced reset/ChangePassword grant and bootstrap-assigned MFA without self-management; session expiry fails closed with dedicated-profile re-login and a fresh reviewed plan. All live acceptance remains unverified.
- Info RED coverage carried OPTIONAL: the old-guard mutation proves the first mixed-case failure only, path variant was skipped; three region-rejection cases have no individual RED. No additional repair needed for this offline approval, and no skipped case is claimed as proof.
- Identity-establishment decision remains PENDING. Existing privileged non-root Terraform-first bootstrap is available if the human supplies an already-authorized identity/session method. Otherwise the proposed one-time human console bootstrap requires a personally recorded exception before any action. The agent neither writes an exception/approval nor infers one from a route/name/work-order choice.
- Proposed names remain scholarchain-billing-operator and scholarchain-billing-deployer; neither exists or is verified by this work. Candidate B remains inferred/live-unverified; scoped login denial stops for review, with no root/planner/A/permanent-key/Identity Center fallback. Old planner-bound plan remains deleted.
- No operator, role/login grant, budget/execution plan/active monitor/delivery/accounting acceptance/usable cost data/remaining allowance established or verified. Proposed USD 5 cap/USD 10 remaining EMR reserve/USD 5.09 margin unchanged and unapproved; every G1/same-JAR/class-origin/filesystem/elapsed-deadline/isolated-plan/teardown gate open. Earlier B1/B2/B3/R1 and N19/N20 unchanged.
- This continuation records the review and asks for choices only. No source/infra edit, AWS/login/IAM/paid call, console action, Terraform/build run, private/config/credential/cache/state read, human record write, reviewer launch, commit/push or Phase 13. Answers will be coordinator transcriptions only, never approvals or exception records.


## Subphase 12D — human identity-route choices (coordinator transcription)

The user answered the pending questions:

1. “Consider the limited human console-bootstrap route (Recommended if root and planner are your only identities)”.
2. “Keep both names (Recommended)”: proposed user scholarchain-billing-operator and role scholarchain-billing-deployer. These names are proposals, not verified identities.
3. “Post-exception read-only verification checklist for your manual setup (Recommended for the console route)”. This follow-up is conditional on the chosen route’s prerequisites.

This is a coordinator transcription of planning choices only. It is not an exception, security-change approval, IAM creation authorization, login authorization, budget/plan/apply approval or spending approval. The human-owned console exception has not been supplied or verified. Do not write human-gate.md, accepted-commit.md, approvals or exception records on the human’s behalf. No console or AWS action occurred.

Next gate: the human personally records the exact limited account-access exception before any action, then supplies a separately bounded checklist work order when prerequisites exist. The proposed scope remains the dedicated operator with bootstrap-set password/no forced reset, bootstrap-assigned MFA/no self-management, and the one billing role with reviewed exact trust/caller/execution/same-device login policies and required governance tags. No root access keys, AdministratorAccess, planner change, Organizations/Identity Center enablement, budget creation or unrelated resources. Actual operator ARN and live login chain remain unverified. No automatic setup or checklist execution starts from these answers.

All live billing/EMR gates remain open; old planner plan remains deleted; proposed USD 5 cap/USD 10 EMR reserve/USD 5.09 margin and B1/B2/B3/R1/N19/N20 unchanged.


## Subphase 12D — observed manual setup and role-first CLI authentication

- The dedicated operator/role, exact trust/caller/budget/login documents, required tags and one-hour role maximum were checked via user screenshots/pasted readbacks. Operator one-policy inventory and root logout are user-confirmed.
- E3 / candidate-B role-first CLI path: user-reported console login, role switch and browser CLI login now culminate in the expected billing-role GetCallerIdentity JSON. This closes the CLI identity check only; it does not prove native Terraform provider consumption, full refresh lifetime, a standalone MFA claim from STS or live budget effectiveness.
- The earlier console password-label inconsistency did not prevent the subsequently reported operator console sign-in; no password reset or MFA removal was performed by this work.
- Actual bootstrap timing/compliance with the proposed 60-minute session remains unverified. Do not backdate or infer times from screenshot creation timestamps. Manual IAM Terraform ownership/adoption remains a separate reviewed decision.
- B1/B2/B3/R1 (12B/12C), N19/N20, all live budget/accounting/delivery/cost gates and all EMR prerequisites are carried unchanged. No active monitor was verified and no budget creation, new plan/apply or spending was authorized in this authentication check.


## Subphase 12D — fresh billing execution-identity read-only plan

Planning now demonstrates pinned provider consumption of the dedicated login profile. Initial sandbox provider handshake failure is retained; identical pinned retry passed. No source repair or policy widening occurred. Exact provider ARN, refresh lifetime, live budget acceptance/delivery, remote ownership, manual IAM adoption and bootstrap timing remain limited/unverified. No active monitor or paid EMR readiness is claimed. B1/B2/B3/R1/N19/N20 and all live gates carry forward unchanged.


## Subphase 12D — fresh plan review findings P1–P3

- P1 Medium, blocks apply. Coordinator routes user-launched independent review of identity-decision, human-bootstrap and authentication packets. Human architect personally records actual setup timing or inability/reason. OPEN: timing clarification and external review pending. Human reported timing recorded, but file currently changes supervised window to9–10PM and still promises actual times afterward; creation screenshots display8:01/8:23PM. Agent will not edit the human record.
- P2 Medium, blocks apply. Human selected /Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/ and sibling billing-bootstrap-backups/, modes0700 directories/0600 sensitive files, outside Git/cloud sync. Keep state/backups until reviewed teardown and human-approved cleanup; plans until superseded/cleanup approval. Local backups do not protect against disk failure. OPEN: durable-path regeneration and independent checksum review await P1. Prior /tmp plan is historical read-only evidence, not an apply artifact. Infra-engineer/coordinator own preparation; human owns location/retention decisions.
- P3 Low, required before later apply. Coordinator prepares explicitly authorized in-window exact-role caller and exact-name budget absence checks. Stop on presence, wrong identity, denied/network/unknown result; no ad hoc import or policy widening. OPEN for later authorized execution; no live check now.

Prior plan APPROVE does not approve apply, IAM changes, spending or Phase12D completion. B1/B2/B3/R1/N19/N20 and all live EMR gates unchanged.


## Subphase 12D — human actual-timing clarification

P1 timing statement is now explicitly supplied by the human in chat:9–10PM Chicago October31. Stop asking for repeated saves. Screenshot creation times20:01/20:23UTC-05 remain earlier and unexplained; independent reviewer must assess this rather than coordinator inventing reconciliation. P1 remains OPEN pending external identity-review verdict; P2 remains OPEN pending later durable-path plan and review. No human-record bytes changed by agent.


## Subphase 12D — P1 identity review F1–F4

- F1 Medium BLOCKING P1. Human timing record contradicts AWS20:01/20:23 creation and20:33 retained setup evidence; exact duration and compliance unverified. Human now reports uncertain approximate8–9PM and explicitly requested its verbatim append; prior bytes preserved. OPEN: human must personally address the observed timestamps and accept/reject window/60-minute deviation (or supply consistent exact timing), followed by user-launched narrow recheck. No invented actual times or backdating.
- F2 Low. Prior exact-request provenance for original replacement paragraph is not retained verbatim in available context. Recorded honestly in append-provenance.json. OPEN until human affirms paragraph or original request is supplied. New explicit timing-append request and dictated text are retained separately; these do not establish old paragraph provenance.
- F3 Low. ADDED new evidence/12d-identity-decision-draft/evidence-manifest.json with hashes/bytes for the three existing files; no existing packet file changed. Independent recheck confirms closure.
- F4 Info. Technical identity scope, policies, tags, MFA/password discrepancy and inventory sufficiency verified by reviewer. Post-creation groups/managed policies and complete manual-IAM Terraform adoption belong to later adoption review. Full refresh lifetime remains unverified. No IAM rebuild/change needed.

P1 remains REQUEST-CHANGES. P2 durable regeneration and all apply/spending gates remain blocked; B1/B2/B3/R1/N19/N20 and all EMR gates unchanged. Coordinator never launches the recheck.


F1/F2 human response follow-up: human supplied uncertain approximate8–9PM estimate, then answered “accept” to the explicit retrospective deviation/AWS20:01–20:23 question and “yes it is mine” to paragraph attribution. Exact questions/replies appended under explicit user instruction, prior record prefixes preserved. F1/F2 evidence repairs are prepared for independent timing-only recheck; P1 remains REQUEST-CHANGES until that verdict. F3 new3-file manifest verified. No future plan/apply/IAM/spending authorized.


## Subphase 12D — P1 recheck APPROVE and durable-plan routing

Independent recheck APPROVES P1 timing/provenance: F1/F2/F3 CLOSED. The human accepted an uncertain timing deviation; historical window/60-minute compliance is not established. F4 inventory/adoption/refresh remains deferred.

G1 Low OPEN before apply: human personally confirms the abe3a50a…1334-byte record reflects their statements; future personal records should be typed directly by human. Does not block read-only plan. G2 Info remains: approximate8–9PM/“accept” is retrospective acknowledgment, not proof of cap compliance or prospective approval. P2 OPEN pending new durable plan and independent review. P3 pre-apply identity/exact-budget checks, live permissions/accounting/delivery/cost-data and all EMR gates remain open. B1/B2/B3/R1/N19/N20 and USD5 proposed spike/USD10 remaining EMR reserve/USD5.09 margin unchanged. No apply/IAM/spending authorized.


## Subphase 12D — operator password recovery proposal

New access blocker: operator password reportedly not saved. Proposed human-only password reset requires new recorded security gate; prior console setup exception does not authorize new recovery automatically. P1 historical APPROVE unchanged; recovery event must be separate. Preserve MFA/policies, do not force next-login password change or add revocation policy without separate scope. No actual reset occurred. Durable-plan prerequisites remain pending.


## Subphase 12D — durable-path read-only billing plan completion

P2 durable-path plan now generated successfully with selected state/data/config/toolchain and new checksum ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855. Independent durable-plan review still required; coordinator does not close P2. P1 F1/F2/F3 remain independently CLOSED. G1 pre-apply human affirmation, G2 accepted timing uncertainty, F4 inventory/adoption/refresh and P3 live checks remain. Password-recovery proposal was withdrawn; no reset performed by agent or reported by human. Old/tmp plan35e35914… remains untouched but superseded. Nothing applied; all live budget/EMR gates remain open.


## Subphase 12D — durable-plan APPROVE, D1–D3 and apply proposal routing

P2 SATISFIED AT PLAN STAGE by independent durable-plan APPROVE. State snapshot/consistent backup procedure after any future approved apply remains a condition; no apply authority inferred. D1 Low: append-only D1-sequencing-erratum.json records19:57:00.911190Z as coordinator JSON write time, not unknown user receipt/helper execution time. Logical session order retained without inventing timestamps; runner presence/regular/owner0600 guard recorded19:56:50.384782Z before plan. Erratum prepared for review, no prior evidence overwritten. D2 Info: prior reviewer independently scanned post-assembly additions; future exact-recipient scans should occur after final assembly under explicitly authorized private processing. This proposal-only scope forbids raw/private-plan access, so current new-doc scan is generic and its scope will be stated accurately. D3 Info: mirror signature skip/“unauthenticated” does not bypass pinned readonly lock checks; reviewed binary provenance retained, no action.

Keep G1 own-words human affirmation, G2 accepted timing uncertainty, F4 inventory/adoption/refresh, P3 in-window caller/exact-budget absence and live budget/accounting/delivery/cost/EMR gates open. B1/B2/B3/R1/N19/N20 and proposedUSD5spike/USD10reserve/USD5.09margin unchanged. Deploy-engineer role also requires clean tree/approved source-controlled execution; current uncommitted work is not silently exempt. Proposal only; no script/approval or exception invented.


## Subphase 12D — apply proposal APPROVE; wrapper routing

Independent apply-proposal review APPROVES proposal only and closes D1. A1 Low OPEN and execution-blocking: pinned1.13.5 credential-free scratch saved-plan apply must prove absolute state path with spaces, no default/config/workspace/TF_DATA_DIR resource state or initial .backup and lock removed. A2 Info OPEN: explicit opaque preservation and test of config/errored.tfstate. Infra-engineer owns scripts/billing/** and offline tests. D2/D3 information retained. G1/G2/F4/P3/B1/B2/B3/R1/N19/N20 and live billing/EMR gates remain open. No source-control/clean-checkout or approval exception.


## Subphase 12D — wrapper offline evidence prepared

D1 remains independently CLOSED. A1 and A2 repairs are prepared for independent acceptance, not self-closed: final37 feature tests passed; final pinned1.13.5 terraform_data scratch init/plan/saved-apply exits0/0/0 and all7 state/lock assertions passed against wrapper SHA81fe564942a9f53ccf40236f32569a0f3fbdba13119c1ca3a23305d64c0039f0. Explicit config/errored.tfstate preservation is tested. Earlier failed harness attempts retained. G1/G2/F4/P3/B1/B2/B3/R1/N19/N20, source-control/clean execution and all human/live gates remain open. No production wrapper mode was invoked.


## Subphase 12D — wrapper review REQUEST-CHANGES

A1/A2 independently ACCEPTED/CLOSED. W1 Medium blocking OPEN: immediate SIGKILL risks orphaned live budget; infra owner to implement SIGINT-first graceful shutdown, bounded grace and explicit forced escalation handling. W2 Low OPEN: dedicated apply timeout and unconditional local backup/preservation even if approval window closes after apply; no further live/readback after expiry. W3 Low EXECUTION-GATE OPEN: single packet scan does not cover later five-record appends; final execution handoff must require separate authorized post-assembly exact-recipient coverage for every published record suffix and artifact, or an independently reviewed code change. W4 Info carried, no detailed text supplied. G1/G2/F4/P3/B1/B2/B3/R1/N19/N20, source-control/clean-checkout and all human/live gates remain open. Bounded repair only, not live authorization.


## Subphase 12D — W1/W2 repair evidence prepared

W1/W2 repairs prepared for independent recheck, not self-closed: one parent-only SIGINT,60s grace before explicit forced escalation, separate300s apply/60s read timeout and80s window headroom; canonical local backup before expiry block.46offline tests passed; final isolated pinned A1 regression3calls0/0/0 and7checks passed. A1/A2 remain independently CLOSED. W3 final-publication suffix coverage remains execution-gate OPEN; W4 unspecifiedInfo carried. Earlier repository packets unchanged; two old/tmp public A1 metadata files overwritten by test output-path mistake, disclosed in new result/report; old/tmp manifest now stale, not claimed intact. No live execution.


## Subphase 12D — W1/W2 recheck APPROVE and execution-gate handoff

W1/W2 independently CLOSED; A1/A2 remain CLOSED. W3 execution-gate OPEN: freeze exact final public artifacts/five record suffix copies, verify destination/base/suffix equality and final scan-before-publication with explicit fixed-schema exclusions; any later change rescan. R1 Low execution-gate OPEN: human-supervised persistent foreground Terminal, residual wrapper-death risk, no retry if completion unknown; incident diagnosis separately reviewed. W4/R2/R3Info have no detailed text supplied; carry without invention. All G1/G2/F4/P3/B1/B2/B3/R1/N19/N20/live billing/EMR gates remain. Handoff prepared only, no human approval or source-control exception inferred.


## Subphase 12D — handoff APPROVE; human decisions pending

Independent review APPROVES HANDOFF PREPARATION ONLY. H1Low actor/mechanism and H2Low window/W3tooling resolve through explicit human choices before any gate; pending, not closed by recommendations. R3Info detailed text not supplied, no invention. W3/R1remain OPEN execution conditions; W1/W2/A1/A2closed. Proposed recommendation: human launches later approved wrapper commands in persistent foregroundTerminal with deploy-owner guidance; choose offline infra W3assembly/equality helper with tests/review before scheduling full60minwindow. Neither recommendation authorizes work. Human must choose sourcecontrol/clean canonical checkout, personally affirm G1, authorize local-only CLI version/hash check and accept/decline residual wrapper-death risk. All other live gates remain unchanged.


## Subphase 12D — G1 user confirmation received

Human replied verbatim “yes it is accurate” after the explicit request to read and affirm billing-bootstrap-exception.md. Statement transcribed in evidence/12d-billing-human-decisions/g1-user-confirmation.json and bound to unchanged1334byte/SHAabe3a50ad7167fa01227c73e15e92a422a50609f6313bdcc56404cb61765d71a record. G1 accuracy confirmation supplied; preserve personal provenance for the later gate. This does not authorize CLI preflight/helper authorship/commit/login/apply/AWS calls/spending or resolve the other human decisions. No live or dependent work performed.


## Subphase 12D — authorized local CLI preflight

Human answered “yes” to local-only version/resolved-executable hash check. Observed aws-cli/2.35.4 Python/3.14.5 Darwin/25.6.0 source/arm64; exit0; resolved /opt/homebrew/Cellar/awscli/2.35.4/libexec/bin/aws; SHA256a0124776b581826399171820e7812f2965486e79605c07fc3e86dbe798baf3f9. Exact argv/minimal environment/stability/observation times in evidence/12d-billing-human-decisions/cli-local-preflight.json; AWS_CONFIG_FILE/AWS_SHARED_CREDENTIALS_FILE=/dev/null, metadata disabled. No login/service request/credential-config inspection/wrapper invocation. This binds launcher bytes only, not installed dependencies/capability/effective permissions; later gate rechecks. Sourcecontrol/actor/window/tooling/R1risk/personal execution gate remain pending.


## Subphase 12D — H1 human Terminal actor choice

Human replied verbatim “yes” to personally running later approved commands with guidance and keeping Terminal open/computer awake until backup finishes. H1actor/mechanism choice supplied; exact context retained in evidence/12d-billing-human-decisions/h1-terminal-actor-confirmation.json. This preparation choice is not permission to execute/login/apply/AWS/helper/commit. Persistent-terminal supervision confirmed; residual wrapper-death risk acceptance not inferred. H2tooling/window, sourcecontrol/clean canonical checkout, R1risk and personal execution gate remain pending.


## Subphase 12D — H2 offline-tooling choice supplied

Human selected offline W3helper preparation/tests and independent review by answering “yes”; no actual window chosen, no private-input/execution permission. H2tooling choice supplied, window feasibility remains for later actualgate. W3 remains OPEN until approved helper plus actual finalassembly/freeze/private scan/publication equality evidence. R1residualrisk acceptance remains pending; H1humanTerminalactor chosen and G1accuracyconfirmation received; no effect on other live gates. W1/W2/A1/A2remain closed. Route only newpublichelpercode/tests/docs to infraowner, preserve budgetwrapper unchanged.


## Subphase 12D — W3helper evidence prepared

Three new public-helper files prepared;39offline tests passed. Existing five scripts unchanged. W3tooling prepared for independent acceptance, W3actualpublication gate still OPEN. All8script hashes now required in future personal gate. Separate assembly workspace/canonical frozen-packet transfer and postscan receipt ordering documented/tested; helper never appends records, invokes scanner or reads recipient. R1residualrisk/window/sourcecontrol/personal gate remain pending; W1/W2/A1/A2closed.


## Subphase 12D — publication helper APPROVE; execution decisions pending

Helper/offline tests independently APPROVED, no blocking repair before human decisions. W3actualfinalfreeze/private scan/publication equality remains OPEN; R1residualrisk/persistentTerminal condition, H2datedwindow feasibility and all live gates remain OPEN. Sourcecontrol must bind all8files and canonical checkout clean. Latest reviewer lists twoLow/threeInfo but only P1/P3/P5labels without detailed finding text; retain exact report, carry those helper-review labels into future execution workorder without inventing definitions or conflating with existing P3identitycheck. Receipt authenticity/freshness external; canonical verify-before/after and manual transfer/append mechanism still required. G1confirmation/H1actor/CLIpreflight/H2tooling choices already supplied; do not ask them again. W1/W2/A1/A2closed. No apply/spend/phasecompletion authorization.


## Subphase 12D — R1 residual-risk acceptance supplied

Human answered verbatim “yes” to remaining wrapper/Terminal crash risk under supervised-Terminal procedure and stop/review before recovery. Exact context in evidence/12d-billing-human-decisions/r1-residual-risk-confirmation.json. R1human risk acceptance supplied; actual uninterrupted execution/backup supervision is still future observed evidence, not proven or retrospectively closed. This is not apply/spend authority. Sourcecontrol/clean canonical all8release, datedwindow/personalgate/freshP3 and actualW3publication coverage remain pending. Original human bootstrap record untouched.


## Subphase 12D — human source-control actor selected

Human answered “yes” to personally making the Phase12commit with guidance. Exact context in evidence/12d-billing-human-decisions/source-control-choice.json. Agent prepares read-only file/hash checks and scoped commands only; user reviews staging and commits. No agent stage/commit/stash/reset; no actual releaseSHA/cleancheckout inferred until observed. All8billingfiles must be included. No execution/paidspike/Phase12completion authorized. Remaining personal datedwindow/exact-checksum gate and freshP3/W3actualevidence pending.


## Subphase 12D — P3 runtime format blocker

P3 stopped before apply with P3_NOT_EXACT_NOT_FOUND. Local metadata: p3started yes, no success/apply/readback/state/backup. Sanitized incident diagnosis confirms only fixed NotFoundException/DescribeBudget plus aws: [ERROR]: prefix and exact reached max retries: 0annotation, singleline/noANSI; no observed access-denied classification, effectivepermissions still not generally proven. This is unrecognized CLIheader, not a validated absence outcome. P3remainsunsuccessful, originalgate8222cf8e…/operationbilling-20261101-2030 immutable and cannotrerun. Infraowner preparing narrow offline source/test repair with no retries/IAM changes; independentreview/newsourcebinding/newpersonaloperationgate required before any laterP3/apply. W1/W2/A1/A2closed; W3/R1runtime evidence and all other live/EMR gates remain open.


## Subphase 12D — P3 format repair evidence prepared

Exact two-header parser repair prepared, not independently accepted yet. Final50offline wrapper features passed; final-wrapper-bound A1regression3calls0/0/0 and7checks passed. Existing real signal fixtures initially failed startup-readiness races (1then2failures); bounded test-only readiness handshake added, targeted2/full50thenpass, production timings/assertions unchanged. Failedtargeted individualexit unknown retained asnull, not invented. All8futuregate hashes recorded; onlywrapper/test/READMEmodified. No actualP3absence claim or newlivecall, oldgate/journal immutable; newreview/release/personalgate/operation required before anyfreshrequest. Other acceptedguards/helper and openW3/R1/F4/EMR gates unchanged.


## Subphase 12D — F1 evidence gap REQUEST-CHANGES

F1Medium blocking OPEN: finalparser has not been evaluated against exact savedstderr bytes/layout; fixedheaderdiagnostic flags and stubfixtures insufficient. Reviewer requires explicit human authorization for one exact in-memory absence(254,bempty,savedstderr) check returning only accepted/blockedcode/newlinecountbuckets/CRLFflag. No private reads performed this step; wait. F2Info keepsdisclosedtest-only readinessfix, no acceptanceaction. No oldP3absence/retry claim. W1/W2/A1/A2/helper accepted; all live gates remainopen. Conditionalrepairroute awaits humananswer andactualboolean, no productionchange assumed.


## Subphase 12D — F1 bounded check authorized

Human explicit “yes” authorizes only the saved-stderr in-memory check requested by reviewer. F1 remainsOPEN pendingresult andconditionalofflinefixture/fullsuite(andA1ifproductionchanges). No exactlayout/acceptance assumed, no P3absence/retry claim; oldoperation staysstopped. F2Info readinessfix disclosure retained.


## Subphase 12D — F1 authorized exact check result and false branch

Single incident-responder evaluation of oldfinal297830d4…absence() on original unstripped savedstderr returned accepted=false, P3_NOT_EXACT_NOT_FOUND, leadingnewline1/trailingnewline1/CRLFfalse. Exactprescribed5fieldresult plus publicsource showing no strip and one boundedosread retained in evidence/12d-billing-p3-layout-recheck/exact-check/. No further privatecheck performed or authorized. Route reviewerfalsebranch: optionaloneleadingLF only, keepstrictheader/body/exit/mixed/no-retry guards, layoutfixtures/fullsuite+A1. F1repairpendingindependentrecheck; originaloperationremainsfailed, no absenceclaim/newliveauthority.


## Subphase 12D — F1 false-branch repair evidence prepared

Allows exactly one optional leadingLF atbytezero, no strip or leadingCRLF/twoLF, existingtrailing0/1LF-CRLF and allheader/denial/exit/no-retry guards retained. Confirmed-layoutsyntheticstub/table fixtures added. Final51offlinefeatures/0fail/0error; pinnedA1regression3calls0/0/0and7checks onfinalwrapperSHAa31852d14e80d970e2338f8a5d94320ea3ca3b89ec759584689d8331d446080b. No secondrealstderrcheck or acceptedtrueclaim. F1preparedforindependentrecheck, F2Info disclosure retained. Existingfailedoperation staysstopped; newrelease/gate/operation/window required after review.


## Subphase 12D — F1 independently CLOSED; new human choices pending

Independent recheck APPROVES F1layout/offlineonly and CLOSES F1accepted=falsebranch. L1Low nonblocking: final mixed-error guard nottested on realbody; human chooses residualrisk or one more boundedfinala31852d4…savedstderrcheck publishingonlyaccepted/blockedcode. No check before authorization. I1Info optionalleadingLF-horizontalspace variant deferred, no codechange. F2Info readinessdisclosure retained. Human sourcecontrol/newall8release/cleancheckout, R1newattemptownwordsdecision, distinctoperation/datedwindow/personalgate pending. EarlierR1acceptance remainsrecorded but renewedcarryforward notinferred. Oldgate8222…/operation immutable/expired; no absence, commit, newgate, login or retry authority. W3/R1runtime/F4/live/EMR gates open.


## Subphase 12D — L1 bounded finalcompatibility evidence supplied

Authorized finalparsera31852d4…single savedstderr check returned exactly accepted=true/blocked_code=null. Safe diagnostic source/result/report retained in evidence/12d-billing-final-parser-check/incident/. No newlinecounts/inputhash/body/IDs/address/loginURL published. Source and originaloperation unchanged by incident. L1compatibility check option completed; this does not prove currentabsence/permission or successfulP3, nor reviveoldoperation. R1ownwordsnewattemptdecision/newrelease/cleancheckout/newpersonaloperation-windowgate and all liveconditions remain pending. No further code/test/actualprivatecheck necessary fromthisacceptedresult.


## Subphase 12D — fresh budget verification and frozen W3 publication

REPAIRS: Original COST_TYPES failure led to accepted legacy/modern cost-scope guards, B1 absence-only BillingViewArn and L1 dynamic/unknown-field rejection. M1 filename default removed; L1 typo checks and L2 canonical hash derivation accepted. Failed verify-billing-20261102-01 NOTIFICATION_DRIFT is preserved/consumed. Authorized single diagnostic led to missing-only ThresholdType compatibility and D1 pinned source citation588–594. Current fresh verify succeeded without modifying the AWS budget. Deferred N1b/N2 remain optional.

Packet: evidence/12d-publication-output-verify-billing-20261103-02/. Gate SHA256: 6e1e20c10049f6440f81d7aaccfb4e08600a3bd7d495027c7fa67b0af3062b84. Operation: verify-billing-20261103-02. Source: 1aa13d71489ebd605cee9b9931bf12de61c18bc3. Verification receipt SHA256: 42a74eee8a6202598b2175e67d8914d2cf4eeacefb000844e32f7df38438eb90. Delivery and Phase12D completion remain unverified/false. This suffix is published only after genuine zero-match same-window scan and verify-before, with verify-after proving exact final bytes.


## Subphase 12D — offline Spark readiness and same-JAR local proof

# Local runtime attempts and preserved failures

No AWS request, Terraform command, private billing read or spending was performed in this readiness work.

The first targeted sbt launch used unsupported launcher argument `-offline` and exited1 before compilation. The corrected launch used the sbt offline property and passed11 readiness tests. The first fullcheck then ran1253 current log-counted tests with one failure in the unchanged independent source fence. Spark owner added capped JavaRDD collection and replaced the new probe's Option emptiness spelling. Existing DataFrame helper methods and the independent guard were preserved. The repaired fast gate passed12 readiness tests and7 independent safety tests before packaging. The final fullcheck is recorded separately; the earlier failure is retained.

Root's first packaged baseline started under the default sandbox and exited1 on a denied local Spark socket bind. It created a partial output directory. The first escalated retry stopped at the runner's exclusive-output guard before launching Java, because that partial directory existed. Its observed Python AssertionError is `Refuse run reuse or overwrite`. The original failed command/stdout/stderr/result and original config are retained. A new output/checkpoint pair (`g1-a-attempt2`) preserved that partial run. The actual escalated retry succeeded with the same JAR, logical settings and immutable upstream manifests. This is a local sandbox correction, not a pipeline repair or an AWS retry.

The second baseline used separately relocated byte-identical upstream inputs and shufflePartitions2 instead of1. Both completed with exactly the same run ID and code fingerprint. The comparator read all28 completed Parquet datasets, recalculated counts and production logical hashes, compared schemas, and checked both full-row multiset differences. It did not normalize physical or nested provenance. Both runs reported zero integrity violations and rejects.

The separate-JVM probe's first reduced runtime lacked scala.xml for Spark's standalone master UI; it exited2 without a success report. The second, separately prepared cached-only runtime added the exact POM-declared Scala XML2.1.0 artifact, then exited2 because the synthetic SPARK_HOME launcher needed an explicit Scala binary version. The third attempt added SPARK_SCALA_VERSION=2.13 and disabled executor bootstrap restarts. It passed with actual distinct driver/executor PIDs and matching loaded class/source hashes. These probe-only runtime changes did not change the baseline classpath, JAR, application sources or build dependencies. Exact logs, public primary references and cached-POM proof are retained in the build evidence. No cloud compatibility follows from this local cluster.

The local threaded probe succeeded and truthfully reported externalExecutorVerified=false. Requiring a distributed executor under local[2] then exited2 as expected and created no success report. The positive separate-process probe proves same-machine file visibility only; a multi-host shared mount and EMR/YARN runtime still require later design, independent review and human execution gates.

After the final fullcheck had exited0, the build evidence finalizer's first overly broad assertion treated any `[error]` log line as an outer build failure. The repository's passing CheckFailurePathSpec intentionally injects a nested failure to test that the success marker cannot be written on a failed check. The corrected finalizer distinguishes this expected nested output from the actual outer exit0, current158 XML reports/1267 passing tests and fresh marker. Both finalization scripts and the erratum are retained. No tests were rerun or output changed to repair this metadata parser.

Raw sibling Spark event logs remain under ignored target directories. The evidence includes compressed raw driver logs, complete completed-export archives and byte inventories. No generated partial output, old attempt, event log or failed journal was deleted or overwritten.


## Subphase 12D — independent offline readiness APPROVE recorded

No blocking defects. The report references optional L1 without identified path/evidence/criteria; retain as unspecified follow-up. Optional test-coverage notes are preserved verbatim. No source repair or retest is required for acceptance.


## Subphase 12D — public EMR design and complete cost proposal

# Retained research attempts and calculation corrections

The public pricing fetch retrieved14 catalogs/pages successfully using bounded anonymous HTTPS requests. Additional Ohio SQS/SNS catalogs and the eventual EBS table also succeeded. All fetch records preserve URLs, times, hashes, status and bounds; the retained HTTP response file is a deterministic gzip of decoded bytes, with original wire/decoded hashes distinguished.

The first three guessed EBS URLs returned404. No rate was inferred from those failures. Reading AWS's pricing page identified token ec2/ebs; reading the linked official pricing JavaScript without executing it established the actual URL construction, ending current/ebs.json. That table returned200 and contains the exact Ohio gp3 rate. The failed URL records and loader bytes/hash are retained. Public web-reader requests to the guessed URLs were also inaccessible. No source or account state was changed by research.

The first cost-record attempt failed closed because SNS SMTP beginRange0 is a free tier. The selector requires a positive paid rate. It was corrected to beginRange1000 and rerun. Scheduler and SNS publish likewise use their positive marginal tiers, explicitly without claiming free entitlement. The first failed record attempt wrote no calculated output.

The arithmetic cross-check uses independent Fraction products/sums with a1e-22USD tolerance to accommodate Decimal rounding of repeating monthly fractions. It does not demand impossible exact equality after finite-precision division. Totals round upward, not downward, to cents.

The initial nominal model produced4.88USD while KMS request allowance was independent of the larger S3 request envelope. Coordinator review found that inconsistency before freezing any review packet. Prior script, selected rates and calculation bytes are retained under prior-cost-model/. The current model couples KMS allowance to all proposed S3 PUT/GET units plus20000 extra operations and raises the nominal result to5.30USD; all sensitivity cases and the explicit lower-request alternative are recalculated. Early commentary/preliminary agent figures are superseded by cost-calculations.json and cost-proposal.md. This correction supplies no account observation or spending authorization.

No full source/test/build suite was rerun for this public document/calculation proposal. The accepted1267-test readiness gate remains historical evidence. No AWS account API, login, recipient/state/plan/credential read, live guard, Terraform resource, actual cost measurement, deployment or cleanup was performed.


## Subphase 12D — EMR cost scenario L1 wording repair

L1: repaired with offered wording option, awaiting independent recheck. USD7.52 models24hours total,21hours beyond3hour nominal; no27hour/additional24hour scenario claimed. Rates, quantities and figures unchanged. Canary/certificates/explicit EBS review observations remain later implementation obligations. No review result is fabricated.


## Subphase12D — offline portable runtime and request inventory

Carried currentfindings: ordinaryportableclasspaths/G1 validated; authenticatedAES-GCM registration remains unresolved after two bounded tests. Missingsecret/unsupportedflag/nativebug/Sparkbug diagnoses are not established. Lower-requestcase unselected because service/log/control/KMSbounds notimplemented. No-extra-cluster canary, paidcertificate-service exclusion/protectedPEMmechanism and explicitEBSvolume configuration recorded for futurework. No source/live repair started beyond this bounded task.

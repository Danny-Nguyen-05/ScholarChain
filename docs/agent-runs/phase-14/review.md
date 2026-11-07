# Phase 14 reviews

## Subphase 14A

### Review 1 — user-supplied external review (pasted by the user on 2026-11-07; reproduced verbatim)

1. VERDICT: REQUEST-CHANGES for Subphase 14A
Most of 14A is sound:

* Bedrock grants: correct.
* EMR v2 tags: in the right places.
* Permissions boundaries: on all seven role blocks.
* Policy shape: every document is under 6,144 characters, statements are locked to us-east-2, MFA is required, sessions last 1 hour, and there is no `*:*`. Tests cover each of these.
* Templates: the approval keys and check order match scripts/deploy.sh.
* Cost math: the core arithmetic is correct.
* Evidence: the claimed counts match the retained logs.

Two problems block approval.
2. Findings
F1 — High, blocking. The approval request leaves out a missing prerequisite: the deployed services cannot become ready.

* Where:
   * docs/agent-runs/phase-14/approval-request-14a.md:84, step 8, says “enable the runtime variables”.
   * `approval-request-14a.md:89`, step 10, says `/readyz` “is expected to pass”.
   * The §1 checklist has no row for this.
* Evidence:
   * infra/terraform/modules/runtime/compute.tf:58 hardcodes `SCHOLARCHAIN_SERVICE_MODE=unconfigured`.
   * modules/services/.../ServiceMains.scala:42-44 accepts only `unconfigured` and `offline-synthetic`.
   * modules/services/README.md:53 says unconfigured mode means “liveness 200 and readiness 503”.
   * The ALB target group health check is `/readyz` with matcher 200 (`compute.tf:94-96`), and the ECS circuit breaker with rollback is on (`compute.tf:124-127`).
   * infra/terraform/phase12b-variables.tf:158-161 defines `runtime_composition_verified` as an acknowledgment “only after replacing/testing current unconfigured-only AWS composition”. `phase12b.tf:42` requires it to be `true` for the runtime plan.
   * infra/terraform/README.md:300 states: “Current service code cannot run a live AWS composition.”
   * The course Phase 14 gate requires services that are healthy and ready, and a smoke query with an evidence-backed response.
* Impact:
   * As written, the request tells the human to set a false acknowledgment and expect `/readyz` to pass.
   * The ALB targets will stay unhealthy, the ECS deployment will fail through the circuit breaker, and `smoke-readyz` will fail. The 14B and 14C “Done when” criteria cannot be met.
   * Meanwhile the stack bills about USD 9.20 a day.
   * Because `APPROVED_COMMIT` is the 14A commit and the repository is frozen until `runtime-apply` succeeds, the path has to be decided before the 14A commit.
* Owner:
   * The coordinator corrects the approval request.
   * The human decides the path.
   * Any code fix goes to `service-engineer`, plus `infra-engineer` for the task environment (including the profile ID passed as the synthesis model ID), and only if the human orders it.
* Acceptance check:
   * The checklist has a “Live service composition” row marked M, with this evidence and the owner as `BLOCKED-ON`.
   * Steps 8 and 10 are corrected, and the request never tells the human to set `runtime_composition_verified=true` before the composition is replaced and tested.
   * `prompt.md` records the human’s decision. The options are: repair before the 14A commit; limit 14B to `base-apply`; or a different option the human chooses.

F2 — Medium, blocking. Tag adoption widens the tag-scoped statements, and the disclosure understates it.

* KMS:
   * infra/terraform/deployer/phase14_main.tf:298-306 (`KmsTagWithProjectTags`) lets the role tag any `key/*` in the region with `project=scholarchain` and `environment=course`.
   * Once a key carries those tags, `:310-320` (`KmsManageProjectKeys`) allows `PutKeyPolicy`, `ScheduleKeyDeletion`, `DisableKeyRotation` and `UntagResource` on it. `:339-361` add key use and grants.
   * The honest-list row (deployer/README.md:109) gives only the reason “CreateKey needs it”.
   * The spike set kept key administration in the key policy (test `kms_administration_is_in_the_key_policy_not_iam`); phase14-main reverses that.
* Security groups:
   * `:158-166` (`Ec2AdoptedDefaultSgFirstTags`) lets any security group in the region be tagged into scope.
   * `:125-139` then grants `AuthorizeSecurityGroupIngress/Egress`, `DeleteSecurityGroup` and `ModifySecurityGroupRules` on it.
   * README `:108` calls this the “same residual” as the Revoke-only row, which understates it.
* Impact:
   * An MFA deployer session could schedule deletion of, or rewrite the policy of, any customer-managed key in us-east-2 whose key policy delegates to IAM.
   * It could also open ingress on any security group in the region.
   * The D4 and D6 acceptances were made against the narrower disclosure.
* Owner: `infra-engineer`; `test-engineer` if the `tests/infra` guard changes.
* Acceptance check, either of:
   * Narrow the statements, for example by moving key administration into the key policy, naming the deployer role, with a negative test showing a foreign tagged key or security group gains no mutation rights.
   * Or rewrite the honest-list rows to list exactly what an adopted key or group can have done to it, add a test that pins that reachable set, and have the human record a new acceptance.

F3 — Low, nonblocking. The record template is not safe to copy.

* At `approval-request-14a.md:99,105,106`, the lines carry trailing `# …` comments.
* `deploy.sh` (`_approval_value`, `^KEY=(.*)$`) captures the comment as part of the value and refuses the line as malformed.
* It fails closed, so nothing unsafe happens, but a literal copy is refused.
* Owner: coordinator. Fix it in the same edit as F1.

F4 — Low, nonblocking. Two cost lines are stale or inconsistent.

* `:159` still says “model unpriced until you give the ID”, but Haiku 4.5 was chosen.
* `:166` gives the authored maxima as 0.739 per hour. That figure leaves out the 0.0333 per hour for metrics; the correct figure is about 0.773 per hour, or about USD 18.55 a day.
* Everything else checks out: 0.3834 per hour, 9.20 a day, 91.63, 104.54, 159.04, 40.96 headroom, and 36.80 for the extra 96 h.
* Owner: coordinator.

F5 — Low, nonblocking. The deployer apply may briefly exceed the attachment quota.

* Terraform does not order the 7 new attachments after the 4 spike detachments, so for a moment 11 could exceed the quota of 10 and cause `LimitExceeded`.
* `deployer-apply-proposal.md` has no rule for a partial apply. It fails safe, since the human runs it with an admin profile.
* Add a rule: “on LimitExceeded, re-plan, expect only the remaining creates, re-apply.”
* Owner: `infra-engineer`.

F6 — Observation, nonblocking. The deny on reading secrets can be bypassed through a task.

* The runtime boundary allows `GetSecretValue` on `secret:*`.
* The deployer can `PutRolePolicy` on task roles, register a task definition with any image, and update the service. That gets around `DenyReadingSecretValues`.
* This is already disclosed as a ceiling. A later tightening could limit the boundary to `secret:scholarchain-course-*` and require that naming for the human-created secrets.

Unverified gates:

* The mutation campaigns are agent-reported.
* I did not check the Service Authorization Reference rows for `ec2:Vpc`.
* Live IAM, quotas, model access, budgets and Cost Explorer are unchecked (P14-5).
* I spot-checked refresh coverage for the 62 resource types and found no definite gap.

Checked with no finding:

* Ownership: `infra-engineer` stayed within `infra/terraform/**` and `scripts/**` (extended by D2 and D6), and `test-engineer` within `tests/**`.
* Human-owned files: none were written.
* Secrets and account IDs: no secret appears; the only account ID is AWS’s documentation placeholder `111122223333`.
* Live actions: none were taken.

Future scope: item 17 (Phase 15), the 14C data-plane grants, and the Phase 15 step actions.
3. Report fields

```
STATUS: COMPLETE (verdict REQUEST-CHANGES)
```

`OWNER: code-reviewer (read-only)`
`WORK ORDER: Phase 14 Subphase 14A review prompt; plan phase14.md handoff, §§3–8`
`FILES CREATED: none`
`FILES MODIFIED: none`
`COMMANDS RUN: git diff --stat / git diff b2cd7ee; cat/sed/grep over the diff, untracked files, evidence and scripts/deploy.sh; WebFetch of the course README (Phase 14, Cost controls). No build, test, AWS or provider call.`
`TEST RESULTS: not run by the reviewer; the counts in the retained logs (check-full-run2.txt, sbt-check-live-after-d6-summary.txt) match test-report.md.`
`VALIDATION RESULTS: F1, F2 blocking; F3–F6 nonblocking; cost arithmetic re-derived and correct apart from F4.`
`ASSUMPTIONS: the IAM evaluation of tag-adoption chains follows the AWS documentation; Terraform orders distinct for_each instances in parallel.`
`RISKS: F1 money spent with no reachable gate; F2 deployer reach beyond the stack; P14-5 live AccessDenied.`
`MANUAL ACTION REQUIRED: human decision on the F1 path; human acceptance (or a narrowing) for F2.`
`BLOCKED-ON OWNER: coordinator + human (F1); infra-engineer (F2)`
`BLOCKED-ON EVIDENCE: compute.tf:58,94-96; ServiceMains.scala:42-44; phase12b-variables.tf:158-161; phase14_main.tf:125-139,158-166,298-320`
`NEXT GATE: 14A repair round, then a user-launched recheck review`
4. NEXT PROMPT

```
You are the coordinator for ScholarChain Phase 14, Subphase 14A, REPAIR ROUND 1, in
```

`/Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-14, base b2cd7ee99dcc136b5c8ec0667ca181cc5b3a87fd,`
`14A uncommitted). Plan: /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase14.md.`
`(a) Append the external reviewer's 14A verdict below, verbatim, to docs/agent-runs/phase-14/review.md under`
`"Subphase 14A" marked "user-supplied external review", and log F1–F6 in docs/agent-runs/phase-14/repairs.md`
`(F1 and F2 blocking; F3–F6 nonblocking).`
`Step 0 (ask the user first, with recommended defaults, and wait for answers):`
`- F1: the deployed services run SCHOLARCHAIN_SERVICE_MODE=unconfigured (modules/runtime/compute.tf:58), so /readyz`
`  returns 503. The ALB health check is /readyz (compute.tf:94-96), runtime_composition_verified must not be true`
`  until the composition is replaced and tested (phase12b-variables.tf:158-161), and the course gate needs ready`
`  services plus an evidence-backed smoke answer. Ask the user to choose: (1) route a live-composition work order to`
`  service-engineer (and infra-engineer for the task environment, including passing the synthesis inference profile`
`  ID as the model ID) before the 14A commit; (2) limit 14B to base-apply and record that the gate is not reachable;`
`  or (3) another path. Recommend (1) if time allows, otherwise (2), and say so with the idle cost of USD 9.20 a day.`
`- F2: narrow or re-disclose the tag-adoption paths (recommended: narrow by moving key administration into the key`
`  policy and removing adopted-group mutation reach; otherwise an exact disclosure plus a human acceptance).`
`(b) Route each blocking finding:`
`- F1 to the coordinator: in approval-request-14a.md, add a §1 row "Live service composition" marked M (evidence and`
`  owner), correct step 8 (runtime_composition_verified) and step 10 (/readyz will be 503 in unconfigured mode), and`
`  record the user's decision in prompt.md. Any code work goes to service-engineer / infra-engineer only as the user`
`  decides.`
`- F2 to infra-engineer (infra/terraform/deployer/**): per the user's choice, narrow phase14_main.tf:125-139,`
`  158-166, 298-361, or rewrite the deployer README honest-list rows for kms:TagResource and the first-tags security`
`  group so they state exactly what an adopted key or group can have done to it. Add a test that a foreign key or`
`  security group tagged into scope gains no mutation rights (if narrowed), or that pins the reachable action set`
`  (if disclosed). test-engineer updates the tests/infra guard only if needed.`
`- Optional (nonblocking), in the same edits: F3 remove the inline comments from the record template;`
`  F4 correct the cost lines at approval-request-14a.md:159,166; F5 add a LimitExceeded rule to`
`  deployer-apply-proposal.md; F6 is a note only.`
`(c) Rerun the affected tests (deployer and root terraform test, tests/infra, scripts/phase12d-spike/tests, and any`
`module suite touched) and the full sbt check on JDK 17. Then run the full seven-gate scripts/check.sh in a clean`
`snapshot, and record exact commands, counts and exit codes in test-report.md.`
`(d) Do not start Subphase 14B.`
`(e) Return a recheck reviewer prompt per plan Section 10 ("Subphase 14A repair round 1", all placeholders filled,`
`prior findings F1–F6 with their repair evidence) without triggering any reviewer.`
`(f) Stop and end the turn after the repair.`

### Review 2 — user-supplied external review (repair round 1 recheck; pasted by the user on 2026-11-07; reproduced verbatim)

1. VERDICT: APPROVE for Subphase 14A (repair round 1)
All five prior findings meet their acceptance checks. I found no new blocker. Four nonblocking findings are below.

Prior findings checked against their acceptance checks

ID	Result	Evidence
F1	Met	Row 17 is honest: V (offline) / H (acknowledgment). Steps 8 and 10 are corrected, prompt.md records the user’s decision, and nothing tells the human to set runtime_composition_verified=true early. The task mode is aws only when the runtime is enabled and the acknowledgment is set (compute.tf:9), and the test for this exists (phase14a.tftest.hcl:941).
F2	Met (narrowed)	The deployer’s IAM policies keep only kms:CreateKey, kms:TagResource limited by request tags and aws:TagKeys, the alias actions on alias/scholarchain-course-* (a foreign key also needs its own key policy to allow them), and kms:ListAliases. Key administration is in the key policy (identity/main.tf:194-213). No security-group tagging works without ec2:CreateAction or an existing project tag. Negative tests: deployer.tftest.hcl:1269,1317 and phase14a.tftest.hcl:657,702.
F3	Met	The template lines carry no trailing comments.
F4	Met	0.4020 + 0.2468 + 0.0405 + 0.0500 + 0.0333 = 0.7726/h, which is USD 18.54/day.
F5	Met	The LimitExceeded rule is in the proposal and the deployer README.
F6	Noted	Unchanged.
What I checked with no finding

Services aws mode:
Configuration fails closed: refusals name only the variable, and the internal token is checked against its stored hash.
The aws path builds no in-memory or synthetic stand-ins.
Readiness is bounded (2 s by default), cached, single-flight, and logs only check names.
Every readiness probe uses an action the role is granted. For example, the worker’s QuerySession GetItem comes from the new grant, the queue check uses sqs:GetQueueAttributes, the vector check uses s3vectors:GetVectors, and the Neptune check uses openCypher ReadDataViaQuery.
The inference-profile ID is the Converse modelId (compute.tf:10, AwsComposition.scala:66).
Coauthor rows carry provenance null plus a stored evidence pointer. Rows with neither are refused.
The placeholder query vector reaches only RemoteVectorStore, which discards it.
Storage:
The three openCypher templates are parameterized.
limit and the allowed edge types are bounded.
connect makes no network call and turns SDK retries off.
An owned client is closed exactly once.
Services src/main contains no NeptunedataClient.
Task environment:
The variable names match AwsConfig. A hand-written test covers each role (phase14a.tftest.hcl:714).
Secrets are passed only as ARN bindings.
Ownership and evidence:
Every path was written by its single owner.
The only account IDs are placeholders (111122223333 and similar), and no secret appears anywhere.
The claimed counts match check-full-r1.txt and sbt-check-live-r1-summary.txt.
No source file changed after snapshot 3.
Two new task-role grants: both are within the runtime boundary. The Null s3:prefix statement is acceptable. In the worst case, a request with no prefix would let query-api and embedding-worker list key names in a bucket whose objects they can already read. Its live behavior is P14-7.
2. Findings (none blocking)
N1 — Low, nonblocking. The approval request names the wrong passing snapshot.

docs/agent-runs/phase-14/approval-request-14a.md:200 names snapshot ba2636c (before the repair) as the reviewed tree that passed.
The repaired tree actually passed in snapshot 3, c4dbd00… (test-report.md:163).
Owner: coordinator.
Acceptance check: the line names c4dbd00 and check-full-r1.txt.
N2 — Low, nonblocking, plausible (not run). The 14B smoke run will likely stop at smoke-query.

scripts/smoke-test.sh:19 requires an answer with claims, and by default it sends the offline-synthetic fixture question.
In aws mode, before the 14C data load, the run will probably stop at smoke-query.
Step 10 at :89 says only that the evidence-backed query is a 14C criterion.
Impact: a failure caused by missing data could be mistaken for a rollback trigger under plan §7.2 step 7.
Owner: coordinator and deploy-engineer, in 14B Step 0. This is 14B work.
Acceptance check: before runtime-apply, the 14B record says what 14B smoke result is expected (for example, healthz and readyz pass, and a smoke-query stop with no data is not a rollback trigger).
N3 — Low, nonblocking, plausible. No health-check grace period on the ECS services.

infra/terraform/modules/runtime/compute.tf:166-197 sets no health_check_grace_period_seconds.
query-api’s /readyz waits for both peer services, and all three start together. The ALB health checks use the defaults (30 s interval, 2 failures to mark unhealthy), and the circuit breaker rolls back.
Impact: the first runtime-apply could churn tasks, and the circuit breaker could roll back. This is unverified live.
Owner: infra-engineer, only through a routed repair with a recheck. Otherwise carry it to 14B as a watch item.
N4 — Observation. Three pieces of text are stale.

compute.tf:105 says the Neptune reader wiring was “still pending”.
phase12b.tf:43 says “Current artifacts remain unconfigured”.
phase12b-variables.tf:161 says “unconfigured-only”.
Owner: infra-engineer, the next time these files are touched.
Carried, no change asked: F6, Route 53 unscoped, kms:TagResource on key/*, the unmanaged default security group, the ENI actions, P14-1.

Unverified gates:

The mutation campaigns are agent-reported.
Not live-checked: IAM evaluation, the key-policy lockout check, the Neptune templates and row shapes, Bedrock access, P14-7 and ECS readiness.
Future scope: item 17, the 14C data-plane grants, the Phase 15 step actions, and the reviewed-pins.json refresh, which needs a new billing gate.

3. Report fields
STATUS: COMPLETE (verdict APPROVE)
OWNER: code-reviewer (read-only)
WORK ORDER: Phase 14 Subphase 14A repair round 1 review; plan phase14.md handoff, §§3–8
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git status/diff --stat; cat/sed/grep/find over the diff, untracked files, docs/agent-runs/phase-14/**, evidence/14a/{gates,r1}, scripts/smoke-test.sh and the plan. No build, test, AWS, provider or network call.
TEST RESULTS: not run by the reviewer. The retained logs match test-report.md R2/R3: terraform 7/19/62/40/6/117; scripts/tests 856; phase12d 78; tests/scripts 276; tests/infra 246; sbt 207/64/39/50/100/107/90/667/18 (0 failed, 1 canceled); RESULT: PASS gates=7; live sbt EXIT 0.
VALIDATION RESULTS: F1–F5 meet their acceptance checks; F6 noted; no blockers; N1–N4 nonblocking.
ASSUMPTIONS: IAM and KMS evaluation per the AWS documentation; S3 HEAD/ListBucket behavior as disclosed (P14-7).
RISKS: first-deploy readiness churn (N3); 14B smoke stopping at smoke-query before data (N2); live AccessDenied (P14-5).
MANUAL ACTION REQUIRED: the user refreshes reviewed-pins.json (23 rows), the full check.sh is re-run on the final tree, the user commits 14A (= APPROVED_COMMIT), and the user applies the deployer root with their admin profile.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: the user's 14A commit, then the Subphase 14B start conditions (deployer applied; not before Nov 11; base-apply record)
4. NEXT PROMPT
You are the coordinator for ScholarChain Phase 14 in /Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-14,
base b2cd7ee99dcc136b5c8ec0667ca181cc5b3a87fd). Plan:
/Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase14.md

(a) Append the external reviewer's verdict for Subphase 14A repair round 1 (APPROVE; nonblocking N1–N4), verbatim, to
    docs/agent-runs/phase-14/review.md under "Subphase 14A" as "Review 2 — user-supplied external review". You may fix
    N1 now (docs only): approval-request-14a.md:200 must name snapshot c4dbd00ea8dbf2eaf1c5300836cb8dd8e5713751 and
    evidence/14a/gates/check-full-r1.txt instead of ba2636c. Do not change any source, Terraform or script file
    (N3 and N4 stay carried unless the user orders a routed repair and a recheck review).

(b) Confirm the user has committed Subphase 14A. If not, ask the user and stop. Remind them of the pre-commit
    sequence in approval-request-14a.md §7:
    - edit the 23 drifted rows of scripts/billing/reviewed-pins.json (evidence/14a/pin-drift.txt);
    - re-run the full seven-gate scripts/check.sh on that final tree (the coordinator runs it in a clean snapshot
      with AWS neutralized, JDK 17, and records the commands, counts and exit code in test-report.md);
    - commit. That commit SHA is APPROVED_COMMIT <C>.
    Record <C> once the user gives it.

(c) Start Subphase 14B of the plan, beginning with Step 0 questions only. Check the start conditions and report each
    one: the deployer phase14-main apply is done by the user; the date is not before Nov 11 (today is before it, so
    say so); a base-apply record exists that matches its plan, receipt and commit. If any condition is unmet, do
    nothing live and tell the user.
    Step 0 must also settle:
    - the cost-to-date the user supplies privately;
    - the expected 14B smoke result. Before 14C data, smoke-test.sh will probably stop at smoke-query (it requires
      claims and defaults to the offline fixture question). State what counts as a 14B pass, and that a no-data
      smoke-query stop is not a rollback trigger (review N2).
    - a first-deploy readiness watch item: no ECS health-check grace period, and query-api readiness waits for both
      peer services (review N3).
    - P14-7, the S3 HEAD of an absent key under the Null s3:prefix grant, to be checked early.
    Commit freeze: from the base plan until runtime-apply succeeds, write nothing into the repository; use
    target/phase14/evidence/ instead. deploy-engineer prepares and verifies; the human runs every --execute.

(d) End with a new reviewer prompt per plan Section 10 for Subphase 14B, with every placeholder filled. Do not
    trigger any reviewer.

(e) Do ONLY Subphase 14B. Then stop and end the turn; do not start Subphase 14C.

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
`14A uncommitted). Plan: <plan path>.`
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
<plan path>

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

## Subphase 14B

### Review 1 — user-supplied external review (Step 0 and the Q6 repair; pasted by the user on 2026-11-07; reproduced verbatim)

1. VERDICT: REQUEST-CHANGES for Subphase 14B (Step 0 and the Q6 repair)
The code does what Q6 asked for. The grace period shares `local.load_balanced_service` with the `load_balancer` block, so it is set only on query-api and only when a certificate is set. It is `null` on the other three services. The value comes from a validated variable. Both test suites catch the obvious mutations, and the retained logs match the claimed counts. Nothing live ran: there is no `human-gate.md`, no `terraform.tfstate` and no `target/phase14/approvals/`.
The one blocker is the value itself. With the default target-group thresholds, 120 s is very unlikely to protect the case N3 is about. Because of the commit freeze, this is the last point at which it can change without a new commit.
2. Findings
B1. Medium, blocking, PLAUSIBLE (reasoned from documented defaults, not observed live). A 120 s grace does not cover a query-api target that has been marked unhealthy.

* Where: infra/terraform/modules/runtime/variables.tf:21-29 (default 120), `compute.tf:185`, and `compute.tf:152-155`. The target group’s `health_check` sets only `path` and `matcher`, so the interval and thresholds are defaults:
   * AWS API defaults: 30 s interval, 2 failures to mark unhealthy, 5 passes to mark healthy.
   * aws provider documentation: 30 s interval, 3 and 3.
* Reasoning:
   * A target is marked unhealthy after about 30–90 s of failing `/readyz`.
   * To recover it then needs 3–5 passes in a row, which is 90–150 s more. The earliest recovery is about 150–210 s after the task starts.
   * When the grace ends at 120 s, ECS replaces any target that is still unhealthy. That counts toward the circuit breaker, and on a first deployment there is nothing to roll back to.
   * A target whose peers are ready early is never marked unhealthy, so it never needed the grace.
   * So 120 s helps almost no real case. The grace needs to be at least the peers’ readiness time plus the healthy threshold × the interval, plus a margin. That is roughly 240–300 s.
* Made worse by: the variable is not wired from the root (`README.md` says “the module default is the single source”). Tuning it after the base plan therefore needs a source commit, which the freeze forbids.
* Owner: you decide first. Then infra-engineer changes `infra/terraform/**` and test-engineer updates `tests/infra/**`.
* Acceptance check: one of these:
   * (a), recommended: raise the default to 300, or derive it from target-group interval and threshold values set explicitly from configuration. Wire a validated root variable so you can tune it in the private tfvars without a commit. Update `phase14b.tftest.hcl` and `test_phase14b_grace.py` to the new decision, with the threshold arithmetic documented in the README.
   * (b): you record that you keep 120 after reading this.
In both cases: rerun `terraform test` and `tests/infra`, then the full `check.sh` on JDK 17.

N1. Medium, nonblocking now, but must be settled before the base-apply record. Nov 11 is allowed by date but does not fit the cost model.

* Where: `prompt.md:98-99`, and `approval-request-14a.md:153` and `:182-187`.
* Nov 11 is the earliest date decisions 14-1 and 14-10 allow.
* Under the 14A model, headroom is 40.96 − 36.80 (the extra 96 h) − 0.34 (cost-to-date) ≈ USD 3.82. That is below the USD 20 floor.
* `reserves_usd` must then cover Nov 11–24, not the Nov 15–24 that the template states.
* `verify.py` checks only the headroom number you type in, never the arithmetic, so the gate cannot catch this.
* Owner: the coordinator records the arithmetic now. You decide: either name which reserve to reduce in the record prose, or use Nov 15.
* Acceptance check: `prompt.md` states the computed headroom for Nov 11 and the option you chose.

N2. Medium, nonblocking now, but a start condition. The HTTPS certificate gap is correctly identified and needs a dated 14B addendum to the approval request. The coordinator should not rewrite the reviewed 14A text. Four things to add:

1. The two lines conflict on the deadline. `prompt.md:99` says the certificate must be settled before Nov 11; `:122` says before the runtime plan. It must be settled before base-apply and before the commit. Without it, spending on base-apply buys nothing that can pass Q5.
2. Per AGENTS.md, an ACM certificate requested or imported by console or CLI is a direct cloud mutation. Either infra-engineer authors it in Terraform before the commit, or you record a disclosed exception.
3. `aws_lb.query` (`compute.tf:133`) is created without a certificate. A runtime-apply with no certificate therefore pays for an ALB that has no listener.
4. A self-signed certificate has a hostname problem: the ALB DNS name is unknown until runtime-apply. The smoke client has no option to trust a custom CA.

The addendum should list `https_certificate_arn` and `public_ingress_cidrs` among the runtime-plan inputs, next to the Q8 values.
N3. Low, nonblocking. `prompt.md:88` and `:95` still say the deployer apply is Nov 12–14 (before Nov 15). The amendment moved it to Nov 8–10. Owner: coordinator.
N4. Low, observation. Two claims are only in prose, not in retained evidence:

* the snapshot-5 identity counts (5686/0 and 1569/0);
* infra-engineer’s temporary mutation result (5 passed / 3 failed).

N5. Observation. The leftover N4 stale text at `phase12b.tf:43` and `phase12b-variables.tf:161` will be frozen into the approved commit. It is recorded as deferred.
/healthz vs /readyz. I recommend no change for 14B. With `/readyz`, a healthy target means the peers are reachable, which is the Q5 pass signal. Keep the known risk on record: when a peer fails, query-api tasks are replaced even though restarting them cannot fix the peer. Revisit only if 14B shows churn.
Future scope (not required now): the deployer apply, base-apply, push, runtime-apply, smoke, P14-5, P14-7, ECS acceptance and timing of the grace, and 14C.
3. Report fields

```
STATUS: COMPLETE (review)
```

`OWNER: code-reviewer`
`WORK ORDER: Phase 14 Subphase 14B Step 0 and the Q6 repair (review 2 N3)`
`FILES CREATED: none`
`FILES MODIFIED: none`
`COMMANDS RUN: read-only only: git status/diff/rev-parse/check-ignore, grep, sed, cat, ls, wc, python3 -I to print the JSONL record`
`TEST RESULTS: not run by the reviewer. The retained logs match the claims: check-full-q6 RESULT PASS gates=7, terraform 7/19/62/40/6/125, script suites 856/78/69/47/39/276/259, sbt on JDK 17.0.20.1 90/667/18 (1 canceled); live sbt EXIT 0 207/64/39/50/100/107/90/667/18; mutations 36/36; pin drift 4 of 209`
`VALIDATION RESULTS: grace set only where load_balancer is; null elsewhere; validated variable; ownership OK; no secrets and no 12-digit IDs apart from the synthetic 111122223333; no live action`
`ASSUMPTIONS: default ALB health-check thresholds as documented (AWS API 2/5, provider 3/3, 30 s); not observed live`
`RISKS: B1 first-start rollback; N1 headroom below 20 for Nov 11; N2 no public endpoint without a certificate`
`MANUAL ACTION REQUIRED: user decisions on B1, N1 and N2 before the commit`
`BLOCKED-ON OWNER: user (B1 decision), then infra-engineer and test-engineer`
`BLOCKED-ON EVIDENCE: variables.tf:23, compute.tf:152-155 and :185`
`NEXT GATE: repair, then a recheck review, then the user's pin refresh and commit`
4. NEXT PROMPT

```
You are the ScholarChain Phase 14 coordinator, continuing Subphase 14B (Step 0 and the Q6 repair, repair round 1) in
```

`/Users/danny/Documents/UIC/CS441/ScholarChain, on branch phase-14 (base e2f0b01ce9670c11ef9c4b3706bb52569f960a1d; all 14B`
`work is uncommitted). Follow <plan path>.`
`(a) Append the external reviewer's verdict for "Subphase 14B — Step 0 and the Q6 repair" (REQUEST-CHANGES; blocking B1;`
`    nonblocking N1–N5), verbatim and marked "user-supplied external review", to docs/agent-runs/phase-14/review.md. Log B1`
`    and N1–N5 in docs/agent-runs/phase-14/repairs.md.`
`(b) Before routing anything, ask the user, each question with its recommended default:`
`    - B1: the default target-group thresholds (AWS API 30 s / 2 / 5, provider 30 s / 3 / 3) mean a 120 s grace cannot`
`      cover a query-api target once it is marked unhealthy. Recommended: grace default 300 s, wired as a validated root`
`      variable so it can be tuned in the private tfvars without a commit (option (a)); or keep 120 and record that (option (b)).`
`    - N2: how the HTTPS certificate is provided (recommended: an ACM certificate authored in Terraform, for a domain the`
`      user controls, if they have one; otherwise a disclosed exception, recorded by the user), and the public_ingress_cidrs`
`      source. It must be settled before the commit and before base-apply.`
`    - N1: for Nov 11, the 14A model gives about USD 3.82 headroom (below 20). Which reserve to reduce, by how much, or use`
`      Nov 15. Recommended: Nov 15, unless the user explicitly lowers a named reserve.`
`    Wait for the answers.`
`(c) Route by docs/agents.md:`
`    - B1 option (a): infra-engineer: infra/terraform/modules/runtime/**, the root variable and wiring, infra/terraform/tests/`
`      phase14b.tftest.hcl, infra/terraform/README.md (document the threshold arithmetic). Then test-engineer:`
`      tests/infra/phase14b_checks.py, test_phase14b_grace.py and README.md, hand-derived from the new decision, with the`
`      mutations repeated. For option (b), record the user's decision only.`
`    - N2: if the user chooses a Terraform-authored certificate, route it to infra-engineer with tests. This is a new`
`      routed repair, in scope only on the user's explicit instruction.`
`    - Coordinator (nonblocking, cheap): a dated 14B addendum to approval-request-14a.md listing https_certificate_arn,`
`      public_ingress_cidrs and the Q8 values as runtime-plan inputs, and that an ALB is billed even without a certificate;`
`      the N1 arithmetic and the user's choice in prompt.md; fix the stale Nov 12–14 at prompt.md:88 and :95 (N3).`
`      Do not rewrite reviewed 14A text or any human-owned file.`
`(d) Rerun the affected tests (terraform fmt, validate and test; tests/infra), then the full`
`    env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh`
`    in a fresh clean snapshot, and the full sbt check on JDK 17. Retain lean evidence under`
`    docs/agent-runs/phase-14/evidence/14b/, including the snapshot identity counts (N4). List the drifted pins again.`
`(e) Run no live command, write no approval record, make no commit. Do not start the deployer apply, base-apply, push,`
`    runtime-apply or Subphase 14C.`
`(f) Return a recheck reviewer prompt per Section 10 with every placeholder filled, without triggering any reviewer, then`
`    end with "Subphase 14B is ready for review. I have stopped and will not start the next subphase until I receive the`
`    next prompt." and stop.`

### Review 2 — user-supplied external review (repair round 1 recheck and replan; reviewer follow-up to the user's answers; pasted by the user on 2026-11-09; reproduced verbatim)

The reviewer's original verdict text ("Subphase 14B — repair round 1 recheck and replan": REQUEST-CHANGES; blocking B2; nonblocking N1–N8) was pasted after this follow-up and is reproduced verbatim in the next entry. The follow-up message below was pasted on 2026-11-09. It contains no plan path. Its only change is that the AWS documentation example account ID in the next-prompt step (a) is written as `<AWS documentation example account ID>`, because the account scan allows that ID only in `AwsTestSupport.scala` (user decision 2026-11-09).

````text
The verdict is still REQUEST-CHANGES on B2: cleanup is refused when spending has gone over USD 25. Your two answers don’t change that, but each changes the next prompt a little. I changed no files.
1. Blank-line fixes after the review. That works, with one caveat. The B2 repair changes the tree, so the recheck reviewer will see a new snapshot, not snapshot 8. The whitespace fixes therefore go after that recheck approves and before the pin refresh. Untracked files need fixing too: infra/terraform/tests/phase14b_root.tftest.hcl and three lines in the runbook.
2. The account-ID test exception. The scanner already meets your conditions:

* Named, exact, one file: the entry in tests/infra/account_scan.py is a single exact value tied to the full path of `AwsTestSupport.scala`. It is not a pattern.
* Other IDs in that file: any other 12-digit ID there is still flagged, because only that exact value is excused.
* Example ID elsewhere: it is still flagged in other files, and `test_scoped_synthetic_values_are_scoped_to_their_files` (`test_billing_replan_14b.py`) already tests this.

Two gaps remain:

* No test checks that a different 12-digit ID inside `AwsTestSupport.scala` is still flagged.
* The entry is named only by a code comment, not a label.

Updated NEXT PROMPT (it replaces the one in my verdict):

```
You are the ScholarChain Phase 14 coordinator, continuing Subphase 14B (repair round 2) in
/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-14 (base e2f0b01ce9670c11ef9c4b3706bb52569f960a1d; all 14B work
uncommitted). Follow the "Replan 2026-11-08" block of the phase14.md plan.

(a) Append the external reviewer's verdict "Subphase 14B — repair round 1 recheck and replan" (REQUEST-CHANGES; blocking B2;
    nonblocking N1–N8), verbatim and marked "user-supplied external review", to docs/agent-runs/phase-14/review.md, with the
    Google Drive plan path written as <plan path> (state that this is the only change). Log B2 and N1–N8 in repairs.md.
    Record the user's decisions: (1) the blank-line fixes are deferred until after the recheck review and done before the pin
    refresh; (2) the test exception is accepted only for AWS's documentation example account <AWS documentation example account ID>, only in
    modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/AwsTestSupport.scala, as a named, file-scoped
    allowlist entry, not a pattern.
(b) Ask the user, each with its recommended default, and wait for the answers:
    - B2: cleanup-prepare has no headroom floor (a negative headroom is accepted; the receipt must still exist, match its hash,
      be fresh, confirm monitoring and carry every numeric field). Recommended: yes.
    - N1: does sales tax count toward the USD 25 cap? Recommended: yes; add a tax line to approval request §3.2 at the user's
      rate, and say how Neptune scaling to 2.5 NCU would change the total.
(c) Route by docs/agents.md:
    - B2: infra-engineer (scripts/config/release.conf, scripts/deploy.sh, scripts/lib/verify.py, scripts/README.md);
      test-engineer (the cleanup-prepare tests: -5.00 accepted for cleanup-prepare, below 3 refused for every spending stage);
      documentation-engineer (runbook C2, line 1298); coordinator (approval request §4 and §7).
    - Test exception: test-engineer (tests/infra/account_scan.py and tests/infra/test_billing_replan_14b.py): give the
      SCOPED_SYNTHETIC entry an explicit name or label (exact value, exact path, no pattern), and add tests that (i) the
      example ID in AwsTestSupport.scala is allowed, (ii) another 12-digit ID in that same file is a finding, and (iii) the
      example ID in any other file is a finding (already covered; keep it).
    - Coordinator: N1 if the user says yes; N4 Titan wording (approval request §3.4); N5 wording (§5); N6 agent provenance in
      owner-report.md.
    - Do NOT route the blank-line or whitespace fixes in this round (user decision 1).
(d) Rerun the affected tests, then the full
    env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
    in a fresh clean snapshot with its identity file, and the full sbt check on JDK 17. Report git diff --check (expected to
    still fail on the deferred whitespace: the four tracked files, plus, once staged, infra/terraform/tests/phase14b_root.tftest.hcl
    and runbook lines 432, 437, 845). Recompute the pin drift.
(e) Run nothing live, make no commit, do not start the live session, and do not close the 10 pre-session items yet.
(f) Return a recheck reviewer prompt per Section 10 without triggering any reviewer. List the deferred whitespace fixes as a
    known item to be done after approval and before the pin refresh. Then end with "Subphase 14B is ready for review. I have
    stopped and will not start the next subphase until I receive the next prompt." and stop.
```
````

### Review 2 — user-supplied external review: the original verdict (repair round 1 recheck and replan; pasted by the user on 2026-11-09; reproduced verbatim)

This verdict contains no plan path, so it is reproduced unchanged. Separately, review N2 led the coordinator to replace the Google Drive plan path, which contains the user's email, with `<plan path>` in the 14B review 1 next-prompt above (line 378). That is the only change to any verbatim text. Lines 136 and 263 sit in the committed 14A reviews and still hold the path; they were left unchanged pending the user's decision.

````text
1. VERDICT: REQUEST-CHANGES for Subphase 14B (repair round 1 recheck and replan)
B1 is closed. The caps match across every source and the cost arithmetic adds up. One blocker remains: scripted cleanup is refused exactly when spending has gone over USD 25. Because of the commit freeze, this is the last point at which it can be fixed.
Confirmations you asked for:

* B1: closed.
   * The grace period defaults to 300 s and can be set from your private tfvars through the root variable `query_health_check_grace_period_seconds` (`phase12b-variables.tf:248`).
   * The target-group timing is now set explicitly to 30 s / 5 s / 3 / 3 (runtime/variables.tf).
   * A precondition on the service requires the grace to be at least healthy_threshold × interval (`compute.tf:282-286`). Tests cover 89 s refused, 90 s accepted, and timing overrides such as 5 × 60 = 300 s.
* Caps and pins match in every source:
   * `release.conf`: headroom 3, cleanup floor 0, EMR cumulative cap 3.00, pipeline sample ceiling 12000.
   * billing-bootstrap: USD 25, ACTUAL alerts at absolute 10/15/20, `include_credit = false`.
   * `llm-allocation.json`: cap 1.50, buckets 10/60/40/5.
   * `load-profile.v1.json`: Haiku 1.10 / 5.50 per 1M tokens, about 0.01155 per answer.
   * 14C templates: Titan 0.25 / 0.05.
* Marketplace: no `aws-marketplace` action appears anywhere in the Terraform.
* Account IDs, emails, domains: no new raw account ID or domain. There is one email, in `review.md` (N2 below).
* Cost arithmetic is correct:
   * Run rate: 0.1608 + 0.05 + 0.0405 + 0.0583 = 0.3096 USD/h.
   * Totals: 19.44 at 36 h and 21.32 at 42 h, leaving 5.56 and 3.68 of headroom.
   * EMR: 0.84 per run = 2 nodes × 0.24 USD/h × 1.75 h (90 min plus the 15 min idle tail).
   * Haiku buckets: 1.33 of 1.50.
   * It fits under USD 25 with at least USD 3 at 42 h before sales tax (N1).
* Evidence matches the claims:
   * Terraform tests: 12+19+103+40+6+246 = 426.
   * Script tests: 1000+78+112+61+39+407+421 = 2,118.
   * Live sbt: 1,415 tests, 0 failed.
   * Pin drift: I recomputed it independently and got the same 24 of 209.
   * No non-docs file changed after snapshot 8 was taken.
   * Real-slice counts add up: 78,104 nodes; 100,252 + 228,715 = 328,967 edges.
* Nothing live ran: there is no `human-gate.md`, no state file and no approvals directory.

Your two questions:

* Blank-line fixes: route them now, in this repair round. There are two more than the four reported (N3).
* Test exception for AWS’s documentation example account: accept it. It is AWS’s published example ID, it applies to one file only, and it was already committed in 14A.

2. Findings
B2. Medium, blocking. Cleanup is refused when spending has gone over the cap.

* Where: scripts/config/release.conf:61-66, scripts/lib/verify.py:191-192, the `HEADROOM_FLOOR` lines in scripts/deploy.sh, and runbook line 1298 (“a negative headroom is still refused”).
* Why it matters:
   * Cleanup-prepare’s floor is 0, so an honest receipt showing more than USD 25 spent is refused.
   * That is exactly the moment teardown is most urgent, and the stack keeps billing about USD 0.31/h while it is blocked.
   * `release.conf`’s own comment says cleanup “must never be blocked by a low or exhausted headroom”.
   * The only ways round it would be a false receipt or an unreviewed manual destroy.
* Owner: your decision first. The replan says “0 for the cleanup step only”, and the recommendation is no headroom floor at all for cleanup-prepare. Then:
   * infra-engineer: `release.conf`, `deploy.sh`, `verify.py`;
   * test-engineer: tests;
   * documentation-engineer: runbook C2;
   * coordinator: approval request §4 and §7.
* Acceptance check:
   * cleanup-prepare accepts a fresh, hash-matched receipt with headroom −5.00;
   * every spending stage still refuses below 3;
   * a missing or non-numeric field is still refused;
   * tests updated, then the full check.

N1. Medium, nonblocking, but decide before your approval record. The cost model leaves out sales tax.

* The budget counts tax (billing-bootstrap/main.tf:39, `include_tax = true`).
* The runbook’s Cost Explorer steps (line 601) also leave tax included.
* At 6–10% tax, the 42 h total becomes about 22.6–23.5, so headroom falls to about 1.5–2.4, below the USD 3 floor.
* The model also keeps Neptune flat at 1 NCU, although it can scale up to 2.5.
* Owner: you decide whether tax counts toward the cap. The coordinator then adds a tax line to approval request §3.2, plus a note on Neptune scaling.

N2. Low. Your personal email is in a changed file. docs/agent-runs/phase-14/review.md:378 adds the Google Drive plan path, which contains your email. It came from my earlier next-prompt, pasted verbatim. The coordinator should replace it with `<plan path>` and note that this is the only change to the verbatim text.
N3. Low. `git diff --check` misses untracked files.

* infra/terraform/tests/phase14b_root.tftest.hcl ends with an extra blank line (infra-engineer).
* `docs/runbooks/phase-14-live-session.md:432, 437, 845` have trailing whitespace (documentation-engineer).
* Fix these together with the four already listed. Acceptance: after `git add -N`, `git diff --check` exits 0, ignoring the raw logs in `evidence/**`.

N4. Low. The Titan split leaves nothing for later. 0.25 + 0.05 = 0.30, so nothing remains for the 15B and 16B query-time embeddings that approval request §3.4 (line 114) says come out of “the rest”. There is also no cap on Titan calls made by the deployed services. The cost is negligible; correct the wording, or record that you accept it.
N5. Low. The approval request overstates the billing change.

* §5 (line 144) says “account ID only as a hash or private render”.
* The billing executor still uses the pre-existing literal at scripts/billing/budget_execution.py:26, and the new modify path relies on it (`:1033`, `:1059`).
* This is allowed by your decision 3 (existing Phase 12 mentions stay), but the sentence should be reworded.

N6. Low. Agent provenance is inconsistent.

* `prompt.md:240` mentions a “deploy-engineer runbook draft”.
* The replan owner table does not list deploy-engineer, and `owner-report.md:14` says deploy-engineer was not used.
* Record whether it ran (role, model, read-only output) as plan Section 5 requires.

N7. Observation, future 14C scope. `scripts/upload-slice.sh --execute` checks no approval record by machine, unlike `upload-emr-artifacts.sh`. It is protected only by the MFA operator role and the prose 14C gate.
N8. Observation.

* The real-slice export ran from a dirty tree; this is disclosed. After the commit, confirm the committed Spark exporter matches `codeVersion b6d030eb`.
* Your plan file’s “≈170 answers” and “≈19.60” differ from the repository’s figures (about 130 answers at 0.01155 per answer, and 19.44). The repository figures are internally consistent.

Unverified until live (as listed in approval request §9): IAM completeness, `if-none-match` enforcement, the ECS Exec tunnel, `aws login` session length and its MFA flag, JVM start-up at 0.25 vCPU, the 300 s grace in practice, EMR behaviour and Bedrock quotas.
Future scope: the 10 open pre-session items (approval request §10), the pin refresh and the commit, then the live session.
3. Report fields

```
STATUS: COMPLETE (review)
```

`OWNER: code-reviewer`
`WORK ORDER: Phase 14 Subphase 14B repair round 1 recheck (B1) and the USD 25 replan`
`FILES CREATED: none`
`FILES MODIFIED: none`
`COMMANDS RUN: read-only only: git diff/status/ls-files/rev-parse, git diff --check (exit 2), grep, sed, cat, stat, python3 -I to recompute pin drift against reviewed-pins.json (24/209)`
`TEST RESULTS: not run by the reviewer; retained logs confirm 426 / 2,118 / sbt 0 failed; live sbt 1,415 tests, 0 failed; snapshot 7 FAIL disclosed`
`VALIDATION RESULTS: B1 closed; caps consistent; arithmetic correct before tax; no Marketplace grant; no new account ID or domain; one email (N2)`
`ASSUMPTIONS: sales tax may apply and is counted by the budget (include_tax = true)`
`RISKS: B2 cleanup blocked when over the cap; N1 headroom below 3 if tax counts`
`MANUAL ACTION REQUIRED: user decisions on B2 and N1; accept the test exception`
`BLOCKED-ON OWNER: user (B2 decision), then infra-engineer, test-engineer and documentation-engineer`
`BLOCKED-ON EVIDENCE: release.conf:61-66, verify.py:191-192, runbook line 1298`
`NEXT GATE: repair, then a recheck review, then the pre-session items, pin refresh and commit`
4. NEXT PROMPT

```
You are the ScholarChain Phase 14 coordinator, continuing Subphase 14B (repair round 2) in
```

`/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-14 (base e2f0b01ce9670c11ef9c4b3706bb52569f960a1d; all 14B work`
`uncommitted). Follow the "Replan 2026-11-08" block of the phase14.md plan.`
`(a) Append the external reviewer's verdict "Subphase 14B — repair round 1 recheck and replan" (REQUEST-CHANGES; blocking B2;`
`    nonblocking N1–N8), verbatim and marked "user-supplied external review", to docs/agent-runs/phase-14/review.md, with the`
`    Google Drive plan path written as <plan path> (state that this is the only change). Log B2 and N1–N8 in repairs.md.`
`(b) Ask the user, each with its recommended default, and wait for the answers:`
`    - B2: cleanup-prepare has no headroom floor (a negative headroom is accepted; the receipt must still exist, match its hash,`
`      be fresh, confirm monitoring and carry every numeric field). Recommended: yes.`
`    - N1: does sales tax count toward the USD 25 cap? Recommended: yes; add a tax line to approval request §3.2 at the user's`
`      rate, and say how Neptune scaling to 2.5 NCU would change the total.`
`    - Accept the file-scoped test exception for the AWS documentation example account in AwsTestSupport.scala? Recommended: yes.`
`(c) Route by docs/agents.md:`
`    - B2: infra-engineer (scripts/config/release.conf, scripts/deploy.sh, scripts/lib/verify.py, scripts/README.md);`
`      test-engineer (the cleanup-prepare tests: -5.00 accepted for cleanup-prepare, below 3 refused for every spending stage);`
`      documentation-engineer (runbook C2, line 1298); coordinator (approval request §4 and §7).`
`    - Whitespace: infra-engineer (infra/terraform/billing-execution/README.md, scripts/billing/PUBLICATION.md,`
`      infra/terraform/tests/phase14b_root.tftest.hcl); storage-engineer (modules/storage/README.md); test-engineer`
`      (tests/infra/README.md); documentation-engineer (runbook lines 432, 437, 845).`
`    - Coordinator: N1 if the user says yes; N4 Titan wording (approval request §3.4); N5 wording (§5); N6 agent provenance in`
`      owner-report.md; record the exception decision.`
`(d) Rerun the affected tests, then the full`
`    env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh`
`    in a fresh clean snapshot with its identity file, the full sbt check on JDK 17, and git diff --check after git add -N on the`
`    untracked files (excluding evidence/** logs). Recompute the pin drift.`
`(e) Run nothing live, make no commit, do not start the live session, and do not close the 10 pre-session items yet.`
`(f) Return a recheck reviewer prompt per Section 10 without triggering any reviewer, then end with "Subphase 14B is ready`
`    for review. I have stopped and will not start the next subphase until I receive the next prompt." and stop.`
````

### Review 3 — user-supplied external review (repair round 2 recheck; pasted by the user on 2026-11-09; reproduced verbatim)

The verdict contains no plan path (its next prompt already writes `<plan path>`), so it is reproduced unchanged.

````text
1. VERDICT: APPROVE for Subphase 14B (repair round 2 recheck)
B2 is closed.

The flag is mandatory: verify.py prespend now needs exactly one of --min-headroom or --no-headroom-floor (scripts/lib/verify.py:918-922). Giving both or neither is a usage error.
The no-floor mode still checks the number: it skips only the comparison (verify.py:192-197). The headroom must still be a finite number, so missing, null, true/false, NaN, infinite and text values are all refused (_number, verify.py:134-142). Every other receipt check still runs.
Only the stage chooses it: deploy.sh:296-300 selects the no-floor mode from STAGE alone. That stage also requires a plan receipt whose purpose is cleanup-prepare and the prepare policy (deploy.sh:556-615), so a spending plan cannot borrow the no-floor path.
Every other path keeps the floor of 3: the spending stages in deploy.sh, and run-bounded-pipeline.sh:437-438.
No config or environment path: the old key is gone from release.conf and SC_PINNED_KEYS.
Tests: tests/scripts/test_prespend_floors_14b.py covers each requirement:
−5.00 is accepted for cleanup-prepare and refused for every spending stage;
2.99 is refused and 3.00 accepted;
non-finite fields, a missing receipt, a hash mismatch, a stale snapshot and unconfirmed monitoring are refused;
setting the old key in the environment or the config has no effect;
static guards check that the flag appears only in deploy.sh and verify.py.
The exception meets decision 2. ScopedSynthetic("aws-documentation-example-account", …, path=<exact path>, pattern=None) matches the path by string equality (tests/infra/account_scan.py:34-55). Tests (i)–(v) cover:

the example ID is allowed in that exact file;
any other 12-digit ID in that file is flagged, including the other scoped values;
the example ID is flagged in 11 near-miss paths;
the entry carries no pattern;
the value is held by no other entry and is not in the global set.
The tax arithmetic in §3.2 is correct:

Case	Calculation	Total	Headroom
36 h	19.10 + 2.10 tax + 0.34	21.54	3.46
42 h	20.98 + 2.31 + 0.34	23.63	1.37
42 h, EMR at full cap	21.46 + 2.36 + 0.34	24.16	0.84
The supporting figures also check out:

hourly cost with tax: (0.3096 + 0.005) × 1.11 ≈ 0.35;
2.5 NCU: +0.2677/h with tax, giving 31.18 / 34.88 for a full session and about 5.1 h of absorption at 42 h;
about 37 h is the longest session that keeps USD 3;
cuts needed: 1.63, or 2.16 with EMR at its full cap;
per-cut savings: 0.93 for one EMR run and 0.19 for the Haiku change.
Account IDs, emails, domains: no added line holds a raw account ID, email or domain. The only 12-digit runs are the synthetic values, the scoped test value and UUID tails.

Evidence matches the claims:

live sbt EXIT 0 with 1,415 tests at 14:57;
tests/infra 426 OK at 14:58, after the last non-docs edit at 14:17;
pin drift 24 of 209, the same list;
the whitespace list matches the six deferred items.
Nothing live ran.

2. Findings (none blocking)
F1. Medium, nonblocking, but decide before the commit. With tax, the USD 3 floor fails at 42 h.

Where: approval-request-14b-replan.md §3.2 (floor check), §1 (hard stop 42 h), §11.
Why it matters: if the base-apply receipt’s reserves honestly cover the rest of the session plus tax, its headroom is 1.37. deploy.sh then refuses base-apply at the floor of 3.
The choice is yours:
option 1, a ~37 h hard stop: the runbook’s H40/H42 times and §1 change;
option 2, a lower floor: release.conf and tests change;
option 3, cost cuts. Capping Neptune at 1 NCU would need infra-engineer.
Any committed change must land before the base plan. §11 does not list this decision explicitly.

Owner: you decide. Then the coordinator updates §1, §3.2 and §11; documentation-engineer updates the runbook times; infra-engineer and test-engineer act only if a pin or Neptune changes.
Acceptance check: §11 records the option you chose, and a projected headroom of at least 3 at the chosen hard stop, with tax.
F2. Low, nonblocking. Approval request §5 and §8 are stale.

§5’s header “(all reviewed tests pass, section 8)” and §8 still show snapshot 8 and do not mention round 2 or the deferred full check.
§3.2’s line “Every hour … USD 0.31” is the pre-tax figure and should say so.
Owner: coordinator.
Acceptance check: §8 shows the final snapshot’s results after the post-approval check.
F3. Observation. review.md:136 and :263 still hold the plan path that contains your email, in text committed in 14A; your decision on this is pending. I recommend replacing it with <plan path> and noting that this is the only change. Owner: coordinator, on your yes.

Unverified gates (by your recorded decision, or agent-reported only):

the full seven-gate check on a fresh snapshot after round 2;
a full scripts/tests run after the round-2 edits to scripts/tests/test_deploy.py and test_pipeline.py and the reverted common.sh line;
tests/scripts 421 OK, which is agent-reported with no retained timestamp.
test_terraform_r1.py fails 7 of 10 in the live tree because its fixture reads only tracked files. It must pass in the fresh snapshot.

Future scope:

the six whitespace items;
the 10 pre-session items;
N4: accept the uncapped query-time Titan embeddings or set a reserve (§11.2);
N7 and N8;
the pin refresh, the commit, and everything live.
3. Report fields
STATUS: COMPLETE (review)
OWNER: code-reviewer
WORK ORDER: Phase 14 Subphase 14B repair round 2 recheck (B2; N1–N8)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only only: git diff/ls-files/rev-parse, grep, sed, cat, stat, ls; 12-digit and email scans over added lines and untracked files
TEST RESULTS: not run by the reviewer; retained: live sbt EXIT 0 (1,415 tests, 0 failed, 1 canceled), tests/infra 426 OK, pin drift 24/209, whitespace = the six deferred items
VALIDATION RESULTS: B2 closed; exception meets decision 2; tax arithmetic correct; no new account ID, email or domain
ASSUMPTIONS: about 11% tax until confirmed from the bill (user decision)
RISKS: F1 floor at 42 h; Neptune scaling uncapped by scripts (max 2.5 NCU)
MANUAL ACTION REQUIRED: choose the F1 option; decide F3; accept or set the Titan reserve (N4); whitespace, pre-session items, pin refresh, commit
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: whitespace fixes, fresh snapshot full check, F1 decision, pre-session items, pin refresh, user commit
4. NEXT PROMPT
You are the ScholarChain Phase 14 coordinator, continuing Subphase 14B (post-approval, pre-session) in
/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-14 (base e2f0b01ce9670c11ef9c4b3706bb52569f960a1d; all 14B work
uncommitted). Follow the "Replan 2026-11-08" block of <plan path>.

(a) Append the external reviewer's verdict "Subphase 14B — repair round 2 recheck" (APPROVE; nonblocking F1–F3), verbatim and
    marked "user-supplied external review", to docs/agent-runs/phase-14/review.md under "Subphase 14B", with any plan path
    written as <plan path> (state that this is the only change). Log F1–F3 in repairs.md as nonblocking.
(b) Route the six deferred whitespace fixes, whitespace only:
    - infra-engineer: infra/terraform/billing-execution/README.md, scripts/billing/PUBLICATION.md,
      infra/terraform/tests/phase14b_root.tftest.hcl;
    - storage-engineer: modules/storage/README.md;
    - test-engineer: tests/infra/README.md;
    - documentation-engineer: runbook lines 432, 437, 845.
(c) Ask the user, each with its recommended default, and wait for the answers:
    - F1 (USD 3 floor at 42 h with tax): recommended option 1, a hard stop of about 37 h with cleanup starting by H35, plus
      lowering the Haiku cap to the 1.33 the buckets need only if the user wants extra margin. Route the choice: coordinator
      (approval request §1, §3.2, §11), documentation-engineer (runbook session times); infra-engineer and test-engineer only
      if a pin or the Neptune maximum changes.
    - F3: redact the email-bearing plan path at review.md:136 and :263 to <plan path>, noted as the only change? Recommended: yes.
    - N4: accept the uncapped query-time Titan embeddings (about USD 0.001), or set ingest 0.24 / smoke 0.05 / query 0.01.
(d) Build a fresh clean snapshot with its identity file and run the full
    env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
    (test_terraform_r1.py must pass there), plus the live sbt check on JDK 17, git diff --check after git add -N (evidence/**
    excluded; it must exit 0) and the pin drift. Refresh approval request §8 (and the §5 header) with these results and label
    the USD 0.31/h line as pre-tax (F2). Retain lean evidence under docs/agent-runs/phase-14/evidence/14b/.
(e) Report the results, then help the user close the 10 pre-session items (approval request §10), refresh the pins and commit.
    Ask the user before any commit; never commit yourself.
(f) Start NO live step: the live session begins only after the user writes the approval record per
    approval-request-14b-replan.md and docs/runbooks/phase-14-live-session.md.
(g) End with a new reviewer prompt per Section 10 (plan path as <plan path>), without triggering any reviewer, then stop.
````

**Redaction note (review F3, user decision 2026-11-09).** In the committed 14A reviews above, at lines 136 and 263, the Google Drive plan path, which contains the user's email, is replaced with `<plan path>`. This is the only change to that verbatim text. Together with the line 378 change (review N2), no plan path remains in this file.

### Review 4 — user-supplied external review (post-approval delta review; pasted by the user on 2026-11-09; reproduced verbatim)

This verdict contains no plan path (its next prompt writes `<plan path>`), so it is reproduced unchanged.

````text
1. VERDICT: REQUEST-CHANGES (Subphase 14B post-approval delta)
There is one blocker, and it’s a small doc fix. The arithmetic, ledgers, runbook, F3 redaction, privacy and no-live checks all pass.
2. Findings
D1 — Low, BLOCKING. The EMR cumulative cap is still USD 3.00 in two experiment files.

* Where:
   * experiments/README.md:23 (a delta file) says “three runs USD 2.52 against the USD 3.00 cumulative cap”. It also says a scale-out of “3 nodes = USD 1.26, total 2.94 … still under 3.00”.
   * experiments/scripts/render_manifests.py:23 (docstring) says “2.52 USD against the 3.00 USD cumulative cap”.
* Why it matters: the pinned cap is now `EMR_CUMULATIVE_CAP_USD=2.52`. A 0.84 + 0.84 + 1.26 = 2.94 scale-out would be refused by `budget.py:215`. During the session the runbook links to this README for 15B, so a human might approve a scale-out the guard then refuses. That wastes paid session time but cannot overspend. It also fails this review’s “caps agree everywhere” check.
* How it was missed: the coordinator’s stale-cap grep covered `README.md`, `docs/**` and `modules/**`, not `experiments/**`.
* Owner: experiment-engineer.
* Acceptance:
   * Both lines say 2.52.
   * The scale-out sentence says 2.94 > 2.52, so a scale-out needs a recorded human cap decision first.
   * `grep -rnE '\b3\.00\b' experiments/` returns no cap statements.
   * `experiments/tests` and `check_manifests.py` still exit 0.

N1 — Nit, not blocking. The comment at scripts/tests/test_pipeline.py:580 reads backwards. It says “three runs of 1.26 (3.78) would pass the 2.52 USD cumulative cap”; it should say they would exceed it, which is why the test raises the cap to 9.50.

* Owner: infra-engineer.
* Acceptance: the comment says “exceed”; `test_pipeline.py` stays at 69 OK.

N2 — Nit, not blocking. In runbook R.1 (docs/runbooks/phase-14-live-session.md:615), the formula and its worked example disagree.

* The formula says “hours to H36 × USD 0.31”, which gives 11.16. The example at line 617 uses 11.15, which is 36 × 0.3096.
* Applied literally, the formula gives reserves of 21.02 and headroom of 3.08. That still clears the floor of 3, but the user’s check won’t match the coordinator’s numbers.
* Owner: documentation-engineer.
* Acceptance: the runbook either writes “0.3096 (about 0.31)” or shows 11.16 / 21.02 / 3.08.

N3 — Observation, not blocking. R.1 reserves only up to H36, but the hard stop is H37.

* At H0 the 0.50 allowance covers that last hour (about USD 0.34 with tax). The figures agree: 3.30 − 3.09 = 0.56 − 0.35.
* Later receipts are protected only if the “margin” term is at least about 0.35.
* This is not a change request. The coordinator should state that margin when giving values.

N4 — Observation, not blocking. The plan’s “Update 2026-11-09” block still says the synthesis cap is USD 1.50. The recorded decision in `prompt.md:285–288` sets 1.33. Repair round 3 (Anthropic Haiku 5.5 pricing) changes the per-answer unit, so 1.33 and the bucket arithmetic must be re-derived then.

* Owner: user (plan text) and coordinator (round 3).

N5 — Observation, outside the delta, not blocking. scripts/billing/budget_execution.py:26 holds a real-looking 12-digit account constant.

* It dates from Phase 12D (commit `8903ce0`) and this delta did not change it, but the file is in the 14B changed set.
* Owner: user, to confirm it is intentional.

Verified correct:

* Caps agree across `release.conf`, both Haiku files, the runbook, approval request §3.2/§3.3/§4/§11, and tests/scripts/test_cap_pins_14b.py.
* EMR ledger:
   * Each run’s estimate is exactly 0.84: 2 × (0.192 + 0.048) × 6,300 s / 3,600, rounded up to the cent. The 15A manifests set 90 min, core 1, task 0 and idle 900 s.
   * Both ledgers refuse only when the total goes above the cap, so exactly 2.52 is allowed.
* Haiku: 115 × 0.01155 = 1.32825 ≤ 1.33, leaving a 0.00175 reserve; a 116th answer is refused.
* Projections with ×1.11 tax:
   * 37 h: 19.24 → 21.70 total, headroom 3.30.
   * H0 receipt: 18.93 + 0.50 → 21.91 total, headroom 3.09.
   * Old caps: H0 headroom 2.37; 37 h headroom 3.11.
   * The R.2 example (0.56 / 21.01 / 3.09) matches.
* F3: only `review.md` lines 136 and 263 changed in the committed text. No email or Drive path remains in any changed or untracked file.
* Whitespace:
   * `git diff --check e2f0b01` exits 0.
   * The five whitespace files have no trailing whitespace and one final newline.
   * No untracked file has trailing whitespace or an extra blank line at the end.
* Nothing live ran: no `terraform.tfstate`, no `~/.scholarchain` ledger directory, no receipts.

Unverified gates:

* Whether the whitespace edits were whitespace-only within the delta: there’s no stored pre-delta tree, because snapshot 8 isn’t a git object here.
* All agent-reported test counts (I ran no tests).
* The full seven-gate check, including `test_terraform_r1.py` (pending by your decision).
* The 11% tax rate, and everything live.

3. Report fields

```
STATUS: COMPLETE (verdict REQUEST-CHANGES)
```

`OWNER: code-reviewer`
`WORK ORDER: Phase 14 Subphase 14B post-approval delta review (prompt.md "Subphase 14B — post-approval")`
`FILES CREATED: none`
`FILES MODIFIED: none`
`COMMANDS RUN: git rev-parse HEAD; git diff/--name-only/-U0/--check against e2f0b01; git ls-files --others; git log -S; grep/sed/awk/tail reads of the delta files, approval request, runbook, reports, evidence and the plan's replan block; ls of tfstate, ~/.scholarchain and target/phase14`
`TEST RESULTS: none run (read-only); agent- and coordinator-reported counts accepted as reported, not reproduced`
`VALIDATION RESULTS: D1 blocking; N1–N5 nonblocking; cap arithmetic, ledger inclusivity, tax projections, F3 redaction, privacy and no-live all confirmed`
`ASSUMPTIONS: 14B is uncommitted against e2f0b01, so the delta was identified from the named files and reports, not from a stored pre-delta tree`
`RISKS: zero slack under the new caps; R.1 leaves the H36–H37 hour unreserved after H0 (N3); tax rate unconfirmed`
`MANUAL ACTION REQUIRED: none for D1 (routed to an agent); the user may want to update the plan text (N4) and confirm N5`
`BLOCKED-ON OWNER: experiment-engineer (D1)`
`BLOCKED-ON EVIDENCE: experiments/README.md:23, experiments/scripts/render_manifests.py:23`
`NEXT GATE: D1 recheck, then the full seven-gate check on a fresh snapshot`
4. NEXT PROMPT

```
You are the coordinator for ScholarChain Phase 14, Subphase 14B, post-approval delta REPAIR, in
```

`/Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-14, base e2f0b01, all 14B work uncommitted).`
`Follow the "Replan 2026-11-08" block of <plan path>. Start nothing live, make no AWS or provider call, and do not commit.`
`(a) Append the reviewer verdict "Subphase 14B — post-approval delta review" (REQUEST-CHANGES; blocking D1;`
`    nonblocking N1–N5) verbatim to docs/agent-runs/phase-14/review.md under "Subphase 14B", with any plan path`
`    written as <plan path>. Log D1 and N1–N5 in repairs.md.`
`(b) Route:`
`    - D1 (blocking) to experiment-engineer: experiments/README.md:23 and experiments/scripts/render_manifests.py:23`
`      must say the cumulative cap is 2.52. The scale-out sentence must say 0.84 + 0.84 + 1.26 = 2.94 > 2.52, so a`
`      node-level scale-out needs a recorded human cap decision first. Then grep experiments/ for remaining 3.00 cap`
`      statements, and rerun experiments/tests and check_manifests.py.`
`    - N1 to infra-engineer: fix the test_pipeline.py:580 comment ("would exceed"). Rerun test_pipeline.py.`
`    - N2 (optional, same round) to documentation-engineer: make R.1 use 0.3096 (about 0.31), or show`
`      11.16 / 21.02 / 3.08. Keep line count and whitespace clean.`
`    - N3, N4, N5: record only. Ask the user about N4 (the plan text says 1.50) and N5 (the account constant from`
`      12D) without changing anything.`
`(c) Rerun git diff --check, the untracked whitespace check (evidence/** excluded) and the stale-cap grep, now`
`    including experiments/** and load-tests/**. Run the live sbt check (JDK 17, AWS neutralized) only if a Scala`
`    or build input changed; otherwise record that it was skipped and why.`
`(d) Update test-report.md and owner-report.md with the exact observed results. Do not run the full seven-gate check`
`    yet; it runs once after the recheck approves.`
`(e) End with a recheck prompt for the independent reviewer (Section 10; plan path as <plan path>) scoped to D1, N1`
`    and N2. Trigger no reviewer, then stop.`
````

### Review 5 — user-supplied external review (post-approval delta repair recheck; pasted by the user on 2026-11-09; reproduced verbatim)

The verdict contains no plan path (its next prompt writes `<plan path>`). Its only change is that the 12-digit synthetic placeholder it quotes from `scripts/tests/test_pipeline.py:438` is written as `<placeholder from test_pipeline.py:438>`, because the account scan allows that number only where it already was at base (snapshot 9 full check, 2026-11-09).

````text
1. VERDICT: APPROVE (Subphase 14B post-approval delta repair: D1, N1, N2, plus the N3 sentence)
There are no blocking findings.
2. Findings
D1: closed (was blocking).
experiments/README.md:23 now says the 15A runs total "USD 2.52 against the USD 2.52 cumulative cap (EMR_CUMULATIVE_CAP_USD=2.52 …)". It also says "0.84 + 0.84 + 1.26 = 2.94 > 2.52, so budget.py would refuse a node-level scale-out, which needs a recorded human cap decision first".
experiments/scripts/render_manifests.py:23 says "2.52 USD against the 2.52 USD cumulative cap".
Searching experiments/ and load-tests/ finds no 3.00 and no 9.50.
1.50 appears only in history notes ("lowered from 1.50") and in the fixture in load-tests/tests/test_llm_budget.py, which sets its own cap. Neither is a statement of the current cap.
N1: closed. scripts/tests/test_pipeline.py:580 now reads "would exceed the 2.52 USD cumulative cap". Only the comment changed; the code is unchanged.
N2: closed. Runbook R.1 (docs/runbooks/phase-14-live-session.md:614–615) uses "USD 0.3096 (about 0.31)".
36 × 0.3096 = 11.1456, which rounds to 11.15.
11.15 + 1.17 + 2.41 + 0.05 + 0.30 + 2.52 + 1.33 = 18.93.
18.93 × 1.11 = 21.0123, which rounds to 21.01.
0.50 × 1.11 = 0.555, which rounds to 0.56.
25 − 0.34 − 0.56 − 21.01 = 3.09.
The formula and the example now agree, and the R.2 JSON example matches.
O1: observation, not blocking, no change required. The N3 sentence at runbook line 614 is accurate and conservative.
The margin sits inside the "(…) times 1.11" bracket, so it is a before-tax amount.
Covering the unreserved H36–H37 hour needs a margin of only about 0.31 before tax (about 0.34 with tax). The stated "at least about USD 0.35" therefore reserves about 0.39 with tax, roughly 0.04 more than needed.
This errs on the safe side.
Owner: documentation-engineer, only if you want the wording exact.
Privacy, whitespace, scope and ownership:
No email address, Drive path or new account ID appears in any touched file. The only 12-digit number in test_pipeline.py:438 is the placeholder <placeholder from test_pipeline.py:438>, and it was already at base.
git diff --check e2f0b01 exits 0. The touched files have no trailing whitespace and end with a single newline. The runbook is still 1,462 lines.
Each file was edited by its owner: experiments by experiment-engineer, scripts/tests by infra-engineer, the runbook by documentation-engineer, and the phase records by the coordinator.
HEAD is still e2f0b01, with 89 tracked changes and 103 untracked files.
Unverified gates:
The test results for experiments/tests (24), check_manifests.py and test_pipeline.py (69) are agent-reported; I did not rerun them.
The live sbt run (1,415 tests, 0 failed, 756 s) is coordinator-reported. No Scala or build input changed.
Still pending by your decision:
the full seven-gate check on a fresh snapshot, including test_terraform_r1.py;
the pin refresh and the commit;
round 3: the Anthropic/Voyage switch, the synthesis cap re-derived per N4, the instructor ruling text and its screenshot;
the 10 pre-session items;
confirmation of the 11% tax rate;
everything live.
3. Report fields
STATUS: COMPLETE (verdict APPROVE)
OWNER: code-reviewer
WORK ORDER: Phase 14 Subphase 14B post-approval delta repair recheck (review 4: D1, N1, N2, N3 sentence)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git rev-parse HEAD; git diff --name-only/--check against e2f0b01; git ls-files --others; git show e2f0b01:scripts/tests/test_pipeline.py; sed/awk/grep/tail/wc reads of the repaired lines, review.md, repairs.md, prompt.md, test-report.md; stale-cap grep over experiments/ and load-tests/; email and account-ID scan of the touched files
TEST RESULTS: none run (read-only); agent- and coordinator-reported results accepted as reported
VALIDATION RESULTS: D1 closed; N1 closed; N2 closed, arithmetic re-derived exactly; N3 sentence accurate and conservative (O1); privacy and whitespace clean
ASSUMPTIONS: the delta was identified from the named files and records, because all 14B work is uncommitted against e2f0b01
RISKS: zero slack under the caps; tax rate unconfirmed; round 3 changes the synthesis provider and cap
MANUAL ACTION REQUIRED: after round 3, update the plan's "Update 2026-11-09" cap text (N4); supply the instructor ruling text and screenshot
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: full seven-gate check on a fresh clean snapshot, then pin refresh and commit
4. NEXT PROMPT
You are the coordinator for ScholarChain Phase 14, Subphase 14B, after the post-approval delta repair recheck
(APPROVE), in /Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-14, base e2f0b01, all 14B work
uncommitted). Follow the "Replan 2026-11-08" and "Update 2026-11-09" blocks of <plan path>. Start NO live step,
make no AWS or provider call, and never commit without the user's explicit yes.

(a) Append the reviewer verdict "Subphase 14B — post-approval delta repair recheck" (APPROVE; D1, N1 and N2
    closed; O1 nonblocking, no change required) verbatim to docs/agent-runs/phase-14/review.md under
    "Subphase 14B", with any plan path written as <plan path>. Log the closure and O1 in repairs.md.
(b) Build a fresh clean snapshot with its identity file, then run on it:
      env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh
    It must end RESULT: PASS gates=7, and test_terraform_r1.py must pass. Also run the live sbt check on JDK 17
    (AWS neutralized), git diff --check after git add -N (evidence/** excluded; restore the index afterwards), and
    the pin drift. Save the evidence under docs/agent-runs/phase-14/evidence/14b/, and replace approval request §8
    with the observed results.
(c) On any failure, report it with the exact output before changing anything, and stop.
(d) If everything passes, help the user refresh the pinned files (approval request §6) and prepare the commit.
    Show the user the file list and the message, and ask before committing. Never commit on your own.
(e) After the user's commit, start repair round 3 per the plan's "Update 2026-11-09" block (Anthropic/Voyage
    switch, synthesis cap re-derived near planned use per N4, instructor ruling text and screenshot from the user),
    beginning with its Step 0 questions.
(f) Start NO live step. Then stop.
````

### Review 6 — user-supplied external review (repair round 3; pasted by the user on 2026-11-10; reproduced verbatim)

Subphase 14B — review 6 (repair round 3): REQUEST-CHANGES. The verdict contains no plan path (its next prompt writes `<plan path>`), so it is reproduced unchanged.

````text
1. VERDICT: REQUEST-CHANGES (Subphase 14B repair round 3)
Two blocking findings, both on the retained Bedrock fallback. The primary Anthropic and Voyage path passed every check I could make offline.
2. Findings
Blocking
B1 (medium): the Bedrock embedding fallback crashes in the live ingest and query-smoke mains.

* Where: modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingIngestMain.scala:384 and `LiveEmbeddingSmokeMain.scala:284`.
* Evidence: both factories pass `Some(config.voyage(...))` as an eager argument for every provider. `VoyageEmbeddingConfig` requires `model.modelId.startsWith("voyage-")` (`VoyageEmbedding.scala:87`), so a Titan model throws before `EmbeddingClientFactory.create` runs. `run` then returns `live-input-or-execution-failed` / `smoke-input-or-execution-failed`.
* Why tests miss it: `LiveEmbeddingProviderSpec` checks Titan only at preflight (lines 128–130), never through `awsPorts`.
* Impact: a Bedrock embedding run cannot ingest or smoke-test in 14C. This contradicts “Retain the Bedrock switch as planned”, modules/rag/README.md (“build the Bedrock SDK client only when `bedrock` is selected”) and runbook B8.6.
* Owner: rag-engineer.
* Acceptance check: the Voyage config is built only on the Voyage branch (and the Bedrock config only on the Bedrock branch). A new test builds the embedding client through the same code path as `awsPorts` for a Titan config with no Voyage key and gets a Bedrock client; the mirror test covers Voyage. The rag suite passes.

B2 (medium): the Bedrock run instructions omit the deployer setting, so following them ends in AccessDenied.

* Where: `README.md:34–42`, docs/report/provider-fallback.md §4, docs/runbooks/phase-14-live-session.md:140 (A0) and `:317` (A4 tfvars).
* Evidence: the runtime boundary carries the Bedrock statement only when the deployer variables `main_synthesis_provider` / `main_embedding_provider` are `bedrock` (infra/terraform/deployer/phase14_main.tf:870, boundaries/runtime.json.tftpl:107). The loader’s Titan grant has the same condition (`operator_roles.tf:151`). Only the two Terraform READMEs say so; the root README and the report never mention the deployer, and the runbook never names the two variables.
* Impact: the instructor required “instructions for selecting and running each configuration” in the README and report. As written, a Bedrock run sets only the main-root variables and is denied at the boundary.
* Owner: documentation-engineer.
* Acceptance check: the README, the report section and runbook A0/A4 state that a Bedrock run also sets the matching deployer variable(s) in `deployer.local.tfvars` and re-applies the deployer before the base plan.

Nonblocking

* N1 (rag-engineer): `VoyageEmbedding.scala:214–238` releases the token reservation when a 200 response fails validation or a call times out. Those tokens may have been billed, so the local counter can under-count. Real money risk is nil inside the 200M free tokens.
* N2 (service-engineer): the startup check in `AwsComposition.scala` (`consistent`) compares the configuration with a client built from that same configuration, so it cannot detect an index filled by another model. The real protection is the `embeddingModel` tag filter (`SemanticContextAgent.scala:41`) and the ingest manifest check. The README wording “services refuse any difference” overstates the startup check.
* N3 (infra-engineer): `phase14b-providers.tf:26–28` fixes the model ids as locals that no variable can override, while the services take them from configuration. They are named, have a rationale and are mirrored in `release.conf`, so rule 6.7 is met; a variable with a default would be more consistent. Lines 70 and 78 repeat the ids as literals.
* N4 (experiment-engineer): load-tests/llm_budget.py `cost_report` hardcodes `"claude-haiku-5-5"` instead of reading the profile. With Bedrock synthesis the pinned unit (0.001365) under-states Haiku 4.5 (0.01155); spend stays bounded because 115 answers × 0.01155 = 1.328 ≤ 1.33.
* N5 (documentation-engineer): runbook B3b.2 step 2 says to click “Retrieve secret value”, which conflicts with the rule above it never to reveal a value. The A4 “Case B” plan counts were not re-derived after this round’s deployer changes.
* N6 (user decision): I recommend keeping `PRESPEND_PROJECT_CEILING_USD=25`. It matches the instructor’s “ceiling” wording, only checks receipt arithmetic, and never blocks cleanup.

Checks that passed

* Haiku 5.5 rules:
   * no `temperature`, `top_p` or `top_k`;
   * forced `tool_choice`;
   * a single user message, no prefill;
   * blocks read by type;
   * `llm-refusal` is not retried (the planner falls back, synthesis abstains);
   * `max_tokens` × 1.3;
   * top-level `$schema`, `$id` and `title` stripped;
   * no `strict`.
* Voyage: `output_dimension` 256, `document` for ingest and `query` for queries, 1,000 texts and 1M tokens per request.
* Secrets: two containers, created only when the provider is selected, no secret version, force delete. Each execution role reads only its own pattern. No secret value, key-shaped token, email, Drive path or new account ID in the delta.
* Grants and egress: Bedrock grants only for a Bedrock provider, no Marketplace action anywhere, existing NAT egress on 443 unchanged.
* Receipts and cleanup: receipts require Anthropic and Voyage spend; both secrets are teardown addresses; the revocation reminder prints on every final path.
* Arithmetic: (7,150 × 0.10 + 1,300 × 0.50) / 1e6 = 0.001365; × 115 = 0.156975.
* Docs: README and report cover the restriction, model ids, dimensions, temperature-0 limit, data leaving AWS and per-provider cost reporting. Superseded Bedrock-only steps are marked.
* Evidence and state:
   * the PNG sha256 matches and the image matches the recorded ruling;
   * `git diff --check` exits 0 and untracked files are clean;
   * the worktree is untouched (HEAD `e2f0b01`, files dated Nov 8) and no stash is left;
   * ownership is correct per docs/agents.md.

Unverified gates

* All test counts are coordinator- or agent-reported; I reran nothing.
* The full seven-gate check on a clean snapshot and the pin refresh (10 of 209) are deferred by your decision.
* Everything live, including whether the Anthropic API echoes `claude-haiku-5-5` exactly. `AnthropicLlm.scala:290` fails every answer with `llm-model-mismatch` if it returns a different id, so make that the first thing the 14C smoke checks.
* Future scope: the 10 pre-session items, the key-entry method, and the plan text still saying 1.50.

3. Report fields

```
STATUS: COMPLETE (verdict REQUEST-CHANGES)
```

`OWNER: code-reviewer`
`WORK ORDER: Phase 14 Subphase 14B repair round 3 review (Anthropic API and Voyage AI switch)`
`FILES CREATED: none in the repository (one scratch file outside it for the privacy scan)`
`FILES MODIFIED: none`
`COMMANDS RUN: git rev-parse/status/diff/diff --check/ls-files/worktree list against f5490d3; read-only git status in the fallback worktree; cat/sed/grep/awk/wc reads of the changed and untracked files, the plan, prompt.md, owner-report.md, test-report.md, repairs.md and evidence/14b/r3; shasum and file on the PNG; secret, email, account-ID and whitespace scans`
`TEST RESULTS: none run (read-only); reported results accepted as reported`
`VALIDATION RESULTS: B1 and B2 blocking; N1-N6 nonblocking; primary path, secrets, grants, receipts, cleanup, arithmetic, evidence hash, privacy, whitespace, ownership and worktree checks passed`
`ASSUMPTIONS: the delta is git diff f5490d3 plus the 24 untracked files; course specification not re-fetched (the plan and the instructor ruling were used)`
`RISKS: model-id echo and all provider behaviour unverified live; embedding counter can under-count (N1); zero slack under the caps`
`MANUAL ACTION REQUIRED: user decides the key-entry method and N6; user updates the plan's 1.50 cap text`
`BLOCKED-ON OWNER: rag-engineer (B1); documentation-engineer (B2)`
`BLOCKED-ON EVIDENCE: test showing a Titan config builds a Bedrock client through the live factory path; updated README, report and runbook text`
`NEXT GATE: repair B1 and B2, rerun the affected tests and the full sbt check on JDK 17, then a recheck review`
4. NEXT PROMPT

```
You are the coordinator for ScholarChain Phase 14, Subphase 14B repair round 3, after the round 3 review
```

`(REQUEST-CHANGES), in /Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-14, base and HEAD f5490d3,`
`round 3 uncommitted). Follow the "Update 2026-11-09" block of <plan path> and docs/agents.md. Offline only: no`
`live step, no AWS, Anthropic or Voyage call, no key value anywhere, no git stash, no commit.`
`(a) Append the reviewer verdict "Subphase 14B — review 6 (repair round 3): REQUEST-CHANGES" verbatim to`
`    docs/agent-runs/phase-14/review.md under "Subphase 14B" (any plan path written as <plan path>), and add`
`    findings B1, B2 and N1-N6 to repairs.md.`
`(b) Route each blocking finding to its owner:`
`    B1 -> rag-engineer (modules/rag/** only). LiveEmbeddingIngestMain.scala:384 and LiveEmbeddingSmokeMain.scala:284`
`       evaluate config.voyage(...) for every provider; VoyageEmbeddingConfig requires a voyage-* model`
`       (VoyageEmbedding.scala:87), so a Titan config throws and run returns live-input-or-execution-failed /`
`       smoke-input-or-execution-failed. Build the Voyage config only on the Voyage branch and the Bedrock config`
`       only on the Bedrock branch. Add tests that build the embedding client through the same code path as awsPorts`
`       for a Titan config with no Voyage key (Bedrock client returned) and for a Voyage config (fake key, no Bedrock`
`       client), with no network call.`
`    B2 -> documentation-engineer (README.md, docs/report/provider-fallback.md, docs/runbooks/phase-14-live-session.md`
`       A0 and A4). State that a Bedrock run also sets main_synthesis_provider and/or main_embedding_provider to`
`       "bedrock" in infra/terraform/deployer/deployer.local.tfvars and re-applies the deployer before the base plan;`
`       otherwise the runtime boundary and the loader role carry no Bedrock grant.`
`    Nonblocking, listed but not required: N1 rag-engineer (spend counter releases tokens on ambiguous outcomes);`
`    N2 service-engineer (startup consistency check is self-referential; fix the README wording); N3 infra-engineer`
`    (model ids as non-overridable locals in phase14b-providers.tf); N4 experiment-engineer (hardcoded model literal`
`    in llm_budget.cost_report; Bedrock unit note); N5 documentation-engineer (B3b.2 "Retrieve secret value" step;`
`    A4 Case B counts); N6 user decision on PRESPEND_PROJECT_CEILING_USD=25 (reviewer recommends keeping it).`
`(c) Rerun the affected tests (rag suite, plus any suite an optional fix touches) and the full sbt -batch check on`
`    JDK 17 with AWS neutralized. Record exact commands, exit codes and counts in test-report.md and under`
`    docs/agent-runs/phase-14/evidence/14b/r3/. On any failure, report it with the exact output before changing`
`    anything else.`
`(d) Do not start the next subphase, the full seven-gate snapshot check, the pin refresh, the commit or the 10`
`    pre-session items.`
`(e) Return a recheck reviewer prompt per Section 10 of the plan, limited to B1, B2 and any optional fixes made,`
`    without triggering any reviewer.`
`(f) Stop and end the turn after the repair.`

*
````

### Review 7 — user-supplied external review (repair round 3 recheck; pasted by the user on 2026-11-10; reproduced verbatim)

Subphase 14B — review 7 (repair round 3 recheck): APPROVE. The verdict contains no plan path (its next prompt writes `<plan path>`). Its only change is that the AWS documentation example account ID it quotes is written as `<AWS documentation example account ID>`, because the account scan allows a 12-digit number only where it already was at base (same rule as review 2, user decision 2026-11-09).

````text
1. VERDICT: APPROVE (Subphase 14B repair round 3, recheck after review 6)
There are no blocking findings. B1, B2 and N5 are closed. Two nonblocking observations follow.
2. Findings
B1: closed (was blocking)
Code

* `ProviderSelection.scala` (`EmbeddingClientFactory.create`) now takes `bedrockConfig` and `voyageConfig` by name (`=> Option[...]`).
   * The Bedrock branch evaluates only `bedrockConfig`.
   * The Voyage branch evaluates `voyageConfig` only inside its `try`, so an invalid Voyage config becomes a closed code.
* Both live mains now build their embedder through one shared method, `LiveEmbeddingIngestMain.embeddingClientFor` (`LiveEmbeddingIngestMain.scala:185`):
   * ingest calls it at `:398` with `Document`;
   * query smoke calls it at `LiveEmbeddingSmokeMain.scala:274` with `Query`.
* The Bedrock client is still a `lazy val` and is built only through the thunk.

Tests (`LiveEmbeddingProviderSpec.scala:299–370`)

* Titan config with no Voyage key: the result is a `BedrockEmbeddingClient` for both document and query input. The thunk is called exactly once, and the injected Bedrock client is a stub that fails if any method is called.
* The mirror test uses a Voyage config at 256 and at 2048 dimensions with a thunk that throws: the result is a `VoyageEmbeddingClient`. The 2048 case proves the Bedrock-shaped config is never evaluated, because the Bedrock config rejects 2048.
* A Voyage config with no key returns `voyage-api-key-missing`; an unknown provider returns `invalid-embedding-provider`.
* No network call is made.

Counts: 1,524 + 3 = 1,527 matches the coordinator’s run.
B2: closed (was blocking)
`README.md:37`, docs/report/provider-fallback.md:26 and runbook A0 (`:140`) and A4 (`:326`) now all say that a Bedrock run must:

* set `main_synthesis_provider` and/or `main_embedding_provider` to `"bedrock"` in infra/terraform/deployer/deployer.local.tfvars;
* re-apply the deployer before the base plan.

They also explain the AccessDenied failure that happens otherwise. The variable names match deployer/variables.tf.
N5: closed (optional)

* B3b.2 step 2 (`:819`) uses the Edit control. It allows Retrieve secret value only while the secret is still empty, and says never to use it once a value exists.
* The A4 counts (`:343`) are marked as from before repair round 3, not re-derived and for reference only. No new numbers were invented.

O1 (nonblocking): Voyage at 2048 dimensions is refused in both preflights

* Owner: rag-engineer.
* Where: `LiveEmbeddingIngestMain.scala:282` (`val embedding = config.embedding`) and `LiveEmbeddingSmokeMain.scala:133` (`config.live.embedding.maxInputTokens`).
* Why: both read the Bedrock-shaped config, which only accepts 256, 512 and 1024. A Voyage run at 2048 dimensions is therefore refused at preflight.
* Impact: none today. The default and the Terraform guard (`phase14b-providers.tf:101`) both pin 256. The coordinator already records this limit.
* Acceptance check, if pursued: the preflights read attempts and input limits from the provider-selected config, and a test preflights a Voyage 2048 config.

O2 (nonblocking): the A4 STOP rule still points at the stale lists

* Owner: documentation-engineer.
* Where: runbook `:345` still says “any address outside the lists above”, but those lists are now reference-only.
* Mitigation: the new text at `:343` says to read every address and decide with the coordinator.
* Acceptance check, if pursued: the STOP rule says “outside the re-derived list agreed with the coordinator”.

Scope, privacy and records

* Scope matches the claim. Files modified since review 6 are exactly the 3 rag sources, the spec, `README.md`, the report, the runbook, and the coordinator’s `review.md`, `repairs.md`, `test-report.md` and `recheck-review6.txt`.
* Ownership is correct. The rag-engineer edited `modules/rag/**`; the documentation-engineer edited `README.md` and `docs/**`; the coordinator edited `docs/agent-runs/**`.
* Whitespace is clean. `git diff --check f5490d3` exits 0, and every touched file has no trailing whitespace and ends with a newline.
* No private data in the touched files: no email address, Drive path or key-shaped token. The only 12-digit values are the earlier AWS documentation placeholder `<AWS documentation example account ID>` in `review.md` and a substring of a hash in the runbook.
* Review 6 is recorded verbatim in `review.md:962`, and its findings are in `repairs.md:134`.
* Live state: no live step was taken and nothing was spent live.

Unverified gates

* The rag 189 and services 113 counts are agent-reported.
* The coordinator’s `sbt check` (1,527 succeeded, 0 failed, 1 canceled) is observed by the coordinator; its raw log is git-ignored and I did not rerun it.
* Still deferred until after this approval:
   * the full seven-gate snapshot check, including `test_terraform_r1`;
   * the pin refresh (10 of 209 files drifted);
   * the commit.
* Still open with you: N6 (whether to keep `PRESPEND_PROJECT_CEILING_USD=25`) and the key-entry method.
* N1–N4 are listed but not routed.
* Everything live is unverified, especially whether the Anthropic API echoes the model id exactly as `claude-haiku-5-5`.

Future scope: the 10 pre-session items, and the plan text that still says the synthesis cap is 1.50.
3. Report fields

```
STATUS: COMPLETE (verdict APPROVE)
```

`OWNER: code-reviewer`
`WORK ORDER: Phase 14 Subphase 14B repair round 3 recheck after review 6 (B1, B2, N5)`
`FILES CREATED: none`
`FILES MODIFIED: none`
`COMMANDS RUN: git rev-parse/status/diff --stat/diff --check against f5490d3; stat over changed and untracked files; sed/grep/awk reads of ProviderSelection.scala, LiveEmbeddingIngestMain.scala, LiveEmbeddingSmokeMain.scala, LiveEmbeddingProviderSpec.scala, README.md, provider-fallback.md, the runbook (A0, A4, B3b.2), review.md, repairs.md, test-report.md V4, recheck-review6.txt; whitespace and privacy scans`
`TEST RESULTS: none run (read-only); agent- and coordinator-reported results accepted as reported`
`VALIDATION RESULTS: B1 closed (only the selected provider's config is evaluated; the shared path has Titan, Voyage and refusal tests); B2 closed; N5 closed; O1 and O2 nonblocking; scope, ownership, whitespace and privacy clean`
`ASSUMPTIONS: "no other file changed since review 6" verified by modification time; course specification not re-fetched`
`RISKS: provider behaviour and model-id echo unverified live; O1 (2048 dimensions) latent`
`MANUAL ACTION REQUIRED: user decides N6 and the key-entry method; user updates the plan's 1.50 cap text`
`BLOCKED-ON OWNER: none`
`BLOCKED-ON EVIDENCE: none`
`NEXT GATE: full seven-gate check on a fresh clean snapshot, pin refresh, then the user's commit`
4. NEXT PROMPT

```
You are the coordinator for ScholarChain Phase 14, Subphase 14B, after the repair round 3 recheck (review 7:
```

`APPROVE), in /Users/danny/Documents/UIC/CS441/ScholarChain (branch phase-14, base and HEAD f5490d3, round 3`
`uncommitted). Follow the "Update 2026-11-09" block of <plan path> and docs/agents.md. Start NO live step: no AWS,`
`Anthropic or Voyage call, no key value anywhere, no git stash, and never commit without the user's explicit yes.`
`(a) Append the reviewer verdict "Subphase 14B — review 7 (repair round 3 recheck): APPROVE" verbatim to`
`    docs/agent-runs/phase-14/review.md under "Subphase 14B" (any plan path written as <plan path>). Log B1, B2 and`
`    N5 as closed and O1 and O2 as nonblocking in repairs.md.`
`(b) Build a fresh clean snapshot with its identity file and run on it:`
`      env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null scripts/check.sh`
`    It must end RESULT: PASS gates=7, with test_terraform_r1.py passing (the snapshot commits the new .tf files).`
`    Save the evidence under docs/agent-runs/phase-14/evidence/14b/r3/ and update test-report.md. On any failure,`
`    report the exact output before changing anything, and stop.`
`    If it passes, refresh the 10 drifted pins (scripts/billing/reviewed-pins.json) with the user, re-check the pin`
`    drift (0), run git diff --check with untracked files intent-added (restore the index), then prepare the commit:`
`    show the user the file list and the proposed message and ask. Never commit without the user's yes.`
`    Also ask the user for the two open decisions: N6 (keep PRESPEND_PROJECT_CEILING_USD=25; reviewer recommends`
`    keeping it) and the key-entry method for runbook B3b.`
`(c) After the user's commit, close the 10 pre-session items in the replan approval request`
`    (docs/agent-runs/phase-14/approval-request-14b-replan.md), beginning with their Step 0 questions, each with a`
`    recommended default; wait for the answers.`
`(d) End with a new reviewer prompt per Section 10 of the plan, without triggering any reviewer.`
`(e) Start NO live step. Then stop and end the turn.`
````

## Subphase 14B — pre-session items

### Review 8 — user-supplied external review (pre-session items; pasted by the user on 2026-11-10; reproduced verbatim)

Subphase 14B pre-session items — review 8: REQUEST-CHANGES. Its only changes are that the plan file locations it names (the plan copy it used, the older local copy, and the full plan path in its next prompt, which contained a personal account address) are written as `<plan path>` and `<older plan copy>`, because no plan path or email address may appear in a repository file (user rule; same treatment as reviews 2 and 7).

````text
1. VERDICT: REQUEST-CHANGES (Subphase 14B, pre-session items)
Nine of the ten items are closed the way their accepted defaults say, and ownership is clean. Two problems block approval:

* B1: one of the 40 committed questions fails the planner's coverage check, so the "planner grammar" acceptance check fails.
* B2: the passing billing test results claimed after the changes have no retained raw output. The only retained log for the changed `test_budget_execution.py` shows failures.

Both are small fixes.
Plan source: `<plan path>`. That copy has the "Update 2026-11-09" block. The `<older plan copy>` is the older 2026-10-25 version.
2. Findings
B1. Medium, blocking: question 28 is refused by the planner

* Where:
   * experiments/inputs/14c/questions.txt:28
   * experiments/scripts/derive_14c_inputs.py:65
   * the test's grammar list at experiments/tests/test_derive_14c_inputs.py:251
   * the README claim at experiments/README.md:121 ("all in the planner fallback grammar")
* Evidence: the question is "Which researchers are the strongest bridges in window since-2015?". `QueryPlannerAgent.coveredQuestion` (`QueryPlannerAgent.scala:547-549`) looks for unquoted filters after `in`, and its lookahead stops at the next keyword. Here it stops at `since`, because the window ID itself starts with "since". So the matched filter text is just `window`. That is not a window ID, and no topic filter equals `window`, so `decode` returns `unrepresented-question-constraint` at line 354.
   * This happens on both the model path and the fallback path, so the question ends as `Unsupported`.
   * I replicated that regex over all 40 committed questions. Only this one fails; the `2020-2026` and `through-2009` variants pass.
   * The experiments test missed it because it only copies the fallback's first-stage regex. It never runs `decode` or the coverage check.
* Impact:
   * 16B spends 1 of its 40 answers, plus the planner's retry calls, on a question that is guaranteed to be unsupported.
   * 15B cycles through the same file, so it wastes calls the same way.
   * The 16B results would contradict the "40 supported questions" claim.
* Owners:
   * experiment-engineer: change the question. Example: "Which researchers are the strongest bridges since 2015?" passes both the intent and coverage checks.
   * rag-engineer: add a real-planner test (see the acceptance check).
* Acceptance check:
   * Regenerate all five files with the script. `include-ids.txt` must stay byte-identical (sha256 `5d4d99a0…`), which keeps the `RuntimeArtifactMain` check valid.
   * Update `provenance.json`, the test grammar and the README.
   * A new rag spec loads the committed `questions.txt` and asserts that all 40 come back `Planned` through the fallback (always-failing `LlmClient`, default runtime config).

B2. Medium, blocking: the billing pass claims are not in the retained evidence

* Where: evidence/14b/presession/gates-summary.txt §2 and `test-report.md` W2. The raw log target/phase14/evidence/14b/presession/gates.txt was checked against them.
* Evidence:
   * `gates.txt` holds only the `suite_run` run of `test_budget_execution.py`: `failures=17 errors=11`, EXIT=1.
   * The claimed per-file passes (113, 62 and 39 OK), the "identical on a clean clone of 13b886a" comparison, `terraform validate`, and the `git diff --check` and privacy-scan outputs appear in no presession raw log.
   * The only per-file billing logs are from r3 (112 and 61 tests), taken before this round added one test to each file.
   * The stated cause doesn't fit the observation. `check.sh:280` describes billing suites interfering when several are loaded together, but this failing run loaded one file only.
* Impact: the claimed pass for the modified test files is not backed by retained evidence (the rule is "claimed results match retained logs").
* Owner: the coordinator (evidence). Rerunning gates needs no other agent.
* Acceptance check:
   * Rerun the three billing files one process each, exactly as `check.sh` does, plus `terraform validate`, with `tee` into the presession raw-log folder.
   * Either retain the clean-clone comparison output or drop that claim.
   * Restate the cause as an observed harness difference whose cause has not been diagnosed.

Nonblocking observations

* N1. Low. load-tests/README.md:116 says "(16 tests, about 10 s)". The observed run was 70 tests in 49.7 s; 16 is only `test_eval16b`. Owner: experiment-engineer.
* N2. Low. `test_eval16b.py` never exercises `plan_state`'s shared-cap refusal (`eval16b.py`: `state["usd"] + total > cap`). Mid-run enforcement goes through `try_charge`, whose `ledger-cap` path is tested in `test_llm_budget.py:113`, and current bucket sizes can't reach USD 1.33. Owner: experiment-engineer.
* N3. Low. The pre-session owner and test reports never state cost-to-date. The round was offline, so they should say "no spend this round; cost-to-date unchanged at <last recorded figure>". Owner: coordinator.
* N4. Future scope. The planner coverage check fails any "in window since-…" phrasing, which is a real planner defect for user queries too. Changing the question (B1) avoids it for these inputs; the regex fix is a separate rag-engineer change.
* N5. Agreed, already recorded. The `archive.py` name filter doesn't catch `*.plan.txt`, and no runbook include reaches `target/phase14/private`. Future scope for infra-engineer.
* N6. Accepted deviation. Item 5 says "to be confirmed live in the session" instead of the default's "verified live". That is more honest, since nothing has been run.

Verified as correct

* Items 1–2: the hashes for the three committed config files match `config-sources.json` and the runbook.
   * The `include-ids.txt` sha equals the `fileSha256` in the retained selection report, which shows `rows=9643 bytes=9633173`.
   * The 14C files hold only IDs and question text, are sorted, fit the 2000-ID and row/byte caps, and are deterministic by design and by test.
* Item 3: `eval16b.py plan` reads only local files; its test blocks all sockets.
   * `run` charges bucket 16b under the ledger lock before every request and refuses up front when the bucket or the cap would be passed.
   * The run ID `16b-1` matches `RUN_ID`.
* Item 4: `emr_service_policy.py` really does print twelve `OK:` lines for a valid file, and masks the account ID.
* Items 5–8:
   * The 28 and 29 field counts are pinned by tests.
   * The new `vector_bucket_name` output is only an output, with a tftest.
   * The GSI name matches `variables.tf:156-160`, and there is a guard plus a 3-test spec.
* Item 9: the expected plan lists are clearly labelled "DERIVED OFFLINE … NOT a live plan … a match is not an approval". `normalize_actions` handles both replace orders.
* Item 10: the test proves that a directory with plan files is refused as a whole and that receipts are accepted one file at a time.
* Runbook: no "Gap" notes remain, and the paths and flags it cites exist (`--include-ids`, `--query-body`, `--node-ids-file`, and the A8 helper).
* Superseding notes: both are add-only at the top of the old records (10 and 2 lines, 0 deleted).
* Pin drift: I recomputed it: 2 of 209 rows (infra/terraform/README.md, infra/terraform/outputs.tf).
* sbt check: `sbt-check-4.txt` shows the claimed counts, Java 17.0.20.1 and `EXIT=0`.
* Privacy and gates: the privacy re-scan of added and untracked lines is clean. No approval record was touched and no live action was taken.

3. Report fields

```
STATUS: COMPLETE (review); verdict REQUEST-CHANGES
OWNER: code-reviewer (read-only)
WORK ORDER: Phase 14 Subphase 14B pre-session items (approval-request-14b-replan.md §10), base/HEAD 13b886a, uncommitted work
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only git diff/status, sed/grep/cat, shasum of committed inputs and config files; python3 -I one-liners in memory to (a) replicate the QueryPlannerAgent unquoted-filter regex over questions.txt and (b) recompute source_freeze pin drift; no build, test, AWS or provider call
TEST RESULTS: not run (reviewer). Retained logs confirm: sbt check EXIT=0, 1,530 succeeded/0 failed/1 canceled; experiments 50, load-tests 70, scripts/tests 27/9/15/20/54/54, tests/infra 460, terraform test 272. Not retained: billing per-file 113/62/39, terraform validate, clean-clone comparison
VALIDATION RESULTS: include-ids sha matches selection report; config-source hashes match; pin drift 2/209 confirmed; privacy scan clean; 1 of 40 questions fails planner coverage (B1)
ASSUMPTIONS: Java and Python regex semantics agree for the replicated pattern; Google Drive plan copy is authoritative
RISKS: B1 wastes paid planner calls in 15B/16B; B2 leaves the modified billing tests without retained passing evidence
MANUAL ACTION REQUIRED: user reviews regenerated questions.txt; pin refresh before commit; plan file cap text 1.50 -> 1.33 (extra D)
BLOCKED-ON OWNER: experiment-engineer + rag-engineer (B1); coordinator (B2)
BLOCKED-ON EVIDENCE: questions.txt:28 vs QueryPlannerAgent.scala:547-549,354; gates.txt billing section
NEXT GATE: recheck review of the repair, then the seven-gate check on a clean snapshot, pin refresh and the user's commit
```

4. NEXT PROMPT

```
You are the ScholarChain Phase 14 coordinator, Subphase 14B pre-session items, REPAIR ROUND (pre-session R1), in
/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-14, base 13b886ad3eddf684a43e9c92ba030f823a8c2cfd, pre-session work uncommitted.
Offline only: no AWS, Anthropic or Voyage call, no key value anywhere, no reading of *.local.tfvars, state, ~/.aws, .env or secret dirs, no git stash, no commit.

(a) Append the external reviewer's verdict verbatim to docs/agent-runs/phase-14/review.md under "Subphase 14B — pre-session items", marked "user-supplied external review". Log B1 and B2 (and N1–N6 as nonblocking) in docs/agent-runs/phase-14/repairs.md.

(b) Route the blocking findings:
 B1 (experiment-engineer, then rag-engineer):
   - experiment-engineer: in experiments/scripts/derive_14c_inputs.py GLOBAL_QUESTIONS replace
     "Which researchers are the strongest bridges in window since-2015?" with a phrase the planner coverage guard accepts
     (recommended: "Which researchers are the strongest bridges since 2015?"). Regenerate all five files in experiments/inputs/14c
     with the script from target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76 (--overwrite).
     include-ids.txt must remain byte-identical (sha256 5d4d99a0326292221a4414b8f5533c532287f8cbbd37a9bee94e7cf86b645552). Run twice; outputs byte-identical.
     Update experiments/tests/test_derive_14c_inputs.py (lines ~129 and GRAMMAR ~251), experiments/README.md:121, and fix N1 (load-tests/README.md:116 test count).
     Optional N2: a test for eval16b plan_state's shared-cap refusal.
   - rag-engineer: add a module-local spec under modules/rag/src/test that reads the committed experiments/inputs/14c/questions.txt
     and asserts that every one of the 40 lines is PlannerResult.Planned by QueryPlannerAgent with an always-failing LlmClient and the
     default runtime config (fallback path through decode/coveredQuestion), with expected operation and window for the 8 ranking lines
     (hand-derived). Do not change QueryPlannerAgent (N4 is future scope).
   - documentation-engineer: only if the runbook or the 16B manifest quotes the changed question, update that text.
 B2 (coordinator): rerun, with AWS neutralized as before and output tee'd under target/phase14/evidence/14b/presession/:
   the three billing files one process each exactly as scripts/check.sh runs them, terraform validate, git diff --check (intent-added, index restored)
   and the privacy scan. Either retain the clean-clone suite_run comparison output or remove that claim. Correct gates-summary.txt and test-report.md:
   the single-file suite_run failure is an observed harness difference, cause not diagnosed (check.sh:280 describes cross-file interference, which does
   not apply to a one-file run). Also state cost-to-date in owner-report.md (N3: no spend this round; last recorded figure).

(c) Rerun the affected tests and record exact output: experiments/tests, load-tests/tests, check_manifests.py, the derive script twice (diff -r clean),
   shasum of include-ids.txt, rag tests, and the full `sbt -batch check` on JDK 17 (environment block in Section 2 of the plan; report java -version).
   Update gates-summary.txt, owner-report.md and test-report.md with a "pre-session R1" section; do not rewrite earlier sections.

(d) Do not start the next subphase, do not run the seven-gate clean-snapshot check yet, do not refresh pins, do not commit.

(e) Return the handoff packet and a recheck reviewer prompt per Section 10 of
   <plan path> (Subphase 14B pre-session items, repair round R1,
   prior findings B1, B2, N1–N6 with repair evidence), all placeholders filled. Do not trigger any reviewer.

(f) Stop and end the turn after the repair: "Subphase 14B pre-session repair R1 is ready for review. I have stopped and will not start the next subphase until I receive the next prompt."
```
````

### Review 9 — user-supplied external review (pre-session repair R1 recheck; pasted by the user on 2026-11-10; reproduced verbatim)

Subphase 14B pre-session repair R1 — review 9: APPROVE. Its only change is that the full plan path in its next prompt, which contained a personal account address, is written as `<plan path>`, because no plan path or email address may appear in a repository file (user rule; same treatment as reviews 2, 7 and 8).

````text
1. VERDICT: APPROVE (Subphase 14B, pre-session repair R1)
Both blocking findings from review 8 are fixed, and the retained logs back every claim I checked. What’s left is one stale README line and one note about a test, neither blocking.
2. Findings
Review 8 findings, rechecked

* B1 (closed):
   * Question changed: question 28 now reads “Which researchers are the strongest bridges since 2015?” (`derive_14c_inputs.py:65`, `questions.txt:28`).
   * Inputs regenerated deterministically: `experiment-gates.txt` shows the script run twice with identical output. The committed files equal run 1.
   * Include list unchanged: `include-ids.txt` still has sha256 `5d4d99a0…`, so the earlier `RuntimeArtifactMain` check (9,643 rows) still holds. The questions sha in `provenance.json` matches the file (`e4b6d48b…`).
   * Test, provenance and docs updated: the test’s grammar list (`test_derive_14c_inputs.py:246-273`) and the provenance are updated, and the test now forbids “in window since-”.
   * Real planner test added: `Phase14QuestionSetPlannerSpec` loads the committed `questions.txt` with the default runtime config and an always-failing model client. It asserts that all 40 come back `Planned` through the fallback (attempts 1), and pins hand-derived operation, metric, measure and window for the 8 ranking lines. The raw sbt log lists its 4 tests passing.
   * My own recheck: my copy of the planner’s coverage regex now finds 0 failing lines out of 40.
* B2 (closed):
   * Billing per-file runs retained: r1/billing-per-file.txt shows 113, 62 and 39 OK, each EXIT 0, run as `check.sh` runs them.
   * Terraform retained: r1/terraform-validate.txt shows fmt exit 0 and validate valid.
   * Clean-clone comparison retained: r1/suite-run-comparison.txt shows the working tree (113 tests) and the clean clone (112) each failing 28 cases. I compared the two lists; they are the same 28 cases.
   * Cause restated: `gates-summary.txt` now calls the cause an undiagnosed harness difference and explicitly corrects its earlier text.
* N1 (fixed): load-tests/README.md:116 now says 71 tests, about 50 s.
* N2 (fixed): `test_eval16b.py:213` now covers the plan/run refusal when the shared USD 1.33 cap would be passed.
* N3 (fixed): `owner-report.md:565` states cost-to-date: USD 0.34 AWS, Anthropic 0, Voyage 0, combined 0.34 of the USD 25 ceiling.

New findings

* R1. Low, nonblocking: stale README line. experiments/README.md:121 says `questions.txt` is “not yet run through the real planner: the rag spec is to check all 40 against it once it exists”. The spec now exists and passes, per the R1 sbt log. Owner: experiment-engineer. Fix: reword it to cite `Phase14QuestionSetPlannerSpec`. It can be done before the commit freeze.
* O1. Info: one test pins the known planner defect.
   * `Phase14QuestionSetPlannerSpec` “regression (N4)” asserts that “in window since-2015” is refused. That records a known defect as expected behaviour, so it will fail on purpose when N4 is fixed.
   * It is labelled, so this is acceptable. Whoever fixes N4 (rag-engineer, future scope) should flip it.

Also verified

* Ownership: experiments and load-tests were edited by the experiment-engineer, the rag test by the rag-engineer, `docs/agent-runs` and evidence by the coordinator. `QueryPlannerAgent` is unchanged.
* Records are append-only: every `docs/agent-runs/phase-14` diff is additions only, and review 8 is reproduced verbatim.
* sbt check: the raw log target/.../r1/sbt-check-r1.txt ends `[success] … 12:09` with `EXIT=0`. The R1 summary counts add up to 1,534.
* Privacy: the R1 logs, the new spec and the questions file are clean (no home paths, emails, 12-digit numbers or key-shaped tokens).
* No live action and no approval record touched. Pin drift is still 2 of 209 and refreshes after approval.

Not verified yet

* The full seven-gate check on a clean snapshot.
* Everything live.
* Future scope: N4 (planner “in window since-” regex) and N5 (`*.plan.txt` archive filter).

3. Report fields

```
STATUS: COMPLETE (review); verdict APPROVE
OWNER: code-reviewer (read-only)
WORK ORDER: Phase 14 Subphase 14B pre-session items, repair round R1 (recheck of review 8), base/HEAD 13b886a, uncommitted
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only git status/diff, cat/grep/sed of evidence and sources; python3 -I in-memory checks: (a) the planner unquoted-filter regex over questions.txt (0 failures), (b) set comparison of the 28 suite_run failure lines in both trees (equal); no build, test, AWS or provider call
TEST RESULTS: not run (reviewer). Retained logs show: billing per-file 113/62/39 OK; terraform fmt 0, validate valid; experiments 51 OK; load-tests 71 OK; check_manifests OK; sbt check EXIT 0, 1,534 succeeded, 0 failed, 1 canceled (JDK 17.0.20.1), including Phase14QuestionSetPlannerSpec 4/4
VALIDATION RESULTS: include-ids sha unchanged (5d4d99a0…); questions sha matches provenance; git diff --check EXIT 0; privacy clean; records append-only
ASSUMPTIONS: Google Drive copy of phase14.md is the authoritative plan
RISKS: R1 stale README sentence; O1 test intentionally pins the N4 defect
MANUAL ACTION REQUIRED: user reviews questions.txt and real-query.json; pin refresh (2 of 209) before commit; plan file cap text 1.50 -> 1.33 (extra D); commit is the user's
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: seven-gate check on a fresh clean snapshot (RESULT: PASS gates=7), pin refresh, user's commit; then commit freeze and the live session per the runbook
```

4. NEXT PROMPT

```
You are the ScholarChain Phase 14 coordinator, Subphase 14B — pre-session items, after the R1 recheck (review 9: APPROVE), in
/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-14, base and HEAD 13b886ad3eddf684a43e9c92ba030f823a8c2cfd, pre-session work and R1 uncommitted.
Offline only: no AWS, Anthropic or Voyage call, no key value anywhere, no reading of *.local.tfvars, state, ~/.aws, .env or secret dirs, no git stash.

(a) Append the external reviewer's verdict (review 9) verbatim to docs/agent-runs/phase-14/review.md under "Subphase 14B — pre-session items",
    marked "user-supplied external review". Record R1 (nonblocking) and O1 (info) in repairs.md. Optionally route R1 to the experiment-engineer
    (experiments/README.md:121: say the 40 questions are checked by Phase14QuestionSetPlannerSpec); if it is fixed, rerun experiments/tests only.

(b) Run the full seven-gate scripts/check.sh on a fresh clean snapshot of the working tree (as in earlier rounds; AWS neutralized). Require
    RESULT: PASS gates=7 with test_terraform_r1 (RouteOwnershipTest) and RealStateBindingTests executing and passing; retain the log under
    target/phase14/evidence/14b/post-approval/ and summarize it in test-report.md. Then show the user the 2 drifted pins (infra/terraform/README.md,
    infra/terraform/outputs.tf in scripts/billing/reviewed-pins.json source_freeze) and refresh them only with the user's explicit yes; re-run the
    pin-drift check (0 of 209). Prepare the commit (file list, proposed message) and ASK the user; never commit without the user's yes.

(c) After the user's commit, state what remains before the commit freeze and the live session per docs/runbooks/phase-14-live-session.md
    (including check_manifests.py --final, the user's review of experiments/inputs/14c/questions.txt and real-query.json, the plan-file cap text 1.33,
    the approval records the user writes, and the A-steps), without doing any of them.

(d) If any work remains that needs review, end with a new reviewer prompt per Section 10 of
    <plan path>, all placeholders filled. Do not trigger any reviewer.

(e) Start NO live step (no billing modify, deployer apply, plan, base-apply, push or anything in the runbook's B section). Then stop and end the turn.
```
````

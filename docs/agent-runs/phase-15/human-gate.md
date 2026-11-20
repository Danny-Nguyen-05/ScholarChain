# Phase 15 human acceptance: live session 2

Drafted: 2026-11-18 (America/Chicago), by the orchestrator, after the end of Section C. Updated 2026-11-19 (P39) and 2026-11-20 (C11, the human's decision, and review repairs made after the decision, listed in the decision log).

## Decision and authority

**DECISION: ACCEPTED by the human, 2026-11-20, after the C11 billing check.** The agents assembled the evidence below; they do not decide. No earlier human decision is changed.

Approval wording, the human's own words, given in chat on 2026-11-20 and copied verbatim by the orchestrator:

> I accept Phase 15 live Session 2 and P39 as recorded in this file. Deviations 1–5 are accepted as disclosed. I confirm my e-mail may appear in the root-console clips REC19, REC20 and REC22; I will check them before using them. Open items: the EMR Spark step is a known limitation, fix only if time allows; the load-test 5xx burst is a known, documented limitation; the incidents and kit gaps are to be written up before Nov 25; the “not verified” items are accepted as listed. Danny Nguyen, 2026-11-20.

Scope of the session, on `phase-15` (not merged to `main`):

- Session HEAD `bd0b8180b919ed61f6234fa515f4c07d1137a641` (the Session 2 approval record, `session-2-approval.md`), frozen for the whole session; **no in-session commits.**
- Approval of record: `session-2-approval.md` (Procedure R), plus the human decisions quoted verbatim, with UTC times, in `evidence/session-2/00-timeline/decision-log.md`.
- The records commit that adds the Session 2 evidence will be the commit that adds this file. It is made only on the human's explicit yes.

## Session results (from the evidence)

Evidence index: `evidence/session-2/INDEX.md`. Timeline of record: `evidence/session-2/00-timeline/decision-log.md`. Times are UTC, on 2026-11-18 unless another date is stated. H0 = 14:44:25Z; C10 at 22:59Z.

- **Setup.** The deployer apply added 13 resources (the operator roles). The A5 login rehearsal passed for every role. The 4 `scholarchain/course/*` secrets were created on the third run, after a narrow `a7-secrets` policy was added (human decision). Run 1 was AccessDenied; run 2 failed parameter validation because a step was skipped. The provider keys were stored: a real Voyage key and a made-up Anthropic placeholder; no Anthropic key was created. The ACM certificate was issued.
- **Stage a.**
  - Plan attempt 1 stopped on a precondition: Session 1 runtime values were still in the private tfvars. Nothing was applied. Attempt 2 passed: 171 creates, plan IDENTICAL to the reviewed derivation.
  - Base-apply 1: Terraform applied all resources, then the 321 MB runtime-archive upload hit an S3 `RequestTimeout` (exit 5). It was not re-run.
  - Recovery (human decision "A"): a new plan with no changes, record serial 2, and base-apply 2 PASS. The upload took about 52 minutes on a slow uplink.
  - EMR enable: 13 creates, plan IDENTICAL, apply PASS.
- **EMR pipeline (run S, size 100).** Cluster `j-00663481CVHVEQEYZQ5L`, 16:26:54-17:06:31Z.
  - On EMR: stage-in, Hadoop prep (input 290,343; accepted 515,309; rejected 1,243), entity resolution and spark-class-origin all completed.
  - **The spark-job step failed** in its template fetch: `hadoop fs -copyToLocal` hit `ClassNotFoundException com.amazon.ws.emr.hadoop.fs.EmrFileSystem`, exit 255, so Spark never started. This is deterministic.
  - Human decision: no retry; use the step 7b fallback, the local P6 S export `run:ba7402d1-…` on the same HEAD.
  - EMR ledger: 3 of 4 runs used; cumulative USD 2.05 of 3.53; Session 2 part USD 0.37.
- **Vectors.**
  - Render-only from the P6 export: 10,000 documents.
  - Ingest 1 rejected all 10,000 items with HTTP 401, because an invalid Voyage key had been pasted. Nothing was written.
  - With a new key, ingest 2 (`run-20261118-ingest-2`) wrote 10,000 with 0 rejected.
  - Query smoke: 5/5 samples, 7 verified pointers.
- **Gate 1 (19:58:59Z).** X_a 0.80 <= 2.85 PASS; pre-R-b 20.20 <= 23.00 PASS. Human: "go neptune".
- **R-b deploy.** Neptune base-apply PASS (T_N0 20:01:44Z) and push PASS. Runtime plan: 25 add, 4 change (execution-role reads of today's secrets). Runtime-apply PASS at 20:28:16Z.
  - DNS: the `api` CNAME pointed at the ALB.
  - Checks: healthz 200, readyz 200 (`--checks healthz,readyz`, 2 of 6 by design); manual 401, 401 and 404.
  - The four services ran 1/1 and the target was healthy.
- **R-b load test (`rb-20261118`, semantic, no LLM).**
  - 26,962 requests; 0 × 429.
  - Scale-out: the ECS poll shows 1/1/0 at 20:51:54Z and desired 2 (1 running, 1 pending) at 20:52:55Z. The second task was running by 20:53:56Z, after the load had stopped. So the scale-out decision came during level 50 or hold-50, and the new task started after the abort. The scale-in back to 1 was seen on the dashboard at about 21:09-21:10Z.
  - **The run aborted at 20:52:49Z** on repeated 5xx (decision log line 62, read from the raw request file, which is outside the repository). In hold-50, 65 server errors (16 × 504, 49 × 503) all started within 0.3 s, plus 2 timeouts. The human accepted the aborted run as the R-b result ("A"), with no rerun.
  - Dashboard: CPU max 75.79%; requests peak about 4.21K per minute; p99 spike to 5 s.
- **Failure example (block 35).** stop-task on the query-api task.
  - Round 1: recovered automatically to 200/200 in about 1 min 53 s.
  - Round 2 (recorded): recovered in about 1 min.
- **Archive and downloads.** Archive `session2-v1` PASS. 15 files were downloaded, with SHA256SUMS (outside the repository).
- **Demo clips.** Ten clips are kept outside the repository; hashes are in `evidence/session-2/recordings/clips.txt`.
  - REC09 and REC10: one clip each instead of the kit's a/b pairs.
  - The rest: REC12, REC13, REC18a, REC18b, REC19, REC20, REC21 and REC22.
- **Section C cleanup.**
  - cleanup-prepare PASS: 20 protection-flag updates.
  - Listing 1 REFUSED by design: 201 deletes, none in `module.foundation`.
  - **Destroy pass 1 = Neptune destroy, issued 22:10:38Z** (T_N0 + 2 h 09 min). It ended PARTIAL as expected at the `aws_eip.nat` DisassociateAddress 403 (carried item 24; IAM not widened), with 297 → 65 inventory entries.
  - Pass 2 PASS: only `aws_eip.nat` deleted, 65 → 63 entries.
  - C4 (human: "yes apply c4"): 13 destroyed (operator roles off; deployer role kept for P39).
  - C5: 4 secrets force-deleted.
  - IAM window 2 was open 22:40:31-22:45:28Z, and the closed-window check is clean.
  - C5b: both Voyage keys (`scholarchain-session2`, `scholarchain-session2b`) revoked at 22:46:11Z.
  - C6: both Cloudflare records deleted.
  - C7: KMS key PendingDeletion.
  - C8:
    - the 7 data-lake buckets return 404;
    - the tagging API lists 83 entries; the orchestrator judges them all to be leftovers of deleted or inactive resources: inactive task definitions, rules of deleted security groups, terminated EMR clusters, 2 KMS keys (one confirmed PendingDeletion), ECS service/cluster/task entries, and NAT/endpoint/instance entries from inside the deleted VPC;
    - REC22 recorded the root console's NAT gateway, load balancer, Neptune, EMR and IAM-roles views (read-only). What those views showed is in the clip, not in the evidence files.
  - C9: LLM ledger unchanged at USD 0.075075.
  - C10: logout at 22:59Z.
- **P39, deployer role removal (Thu 2026-11-19).** Run by the human from the reviewed procedure in `infra/terraform/deployer/README.md` (infra-engineer; code-reviewer round 1 REQUEST-CHANGES, round 2 APPROVE). Evidence: `evidence/session-2/p39/` and the decision log. Two run-time adjustments by the orchestrator, from the review's low notes: `| mask` on the block 3 identity line, and the console fallback for the budget check after the expected AccessDenied.
  - IAM window 3 was open from 18:58:04Z (the first of two OPEN stamps in the P39 log, 18:58:04Z and 18:58:59Z; the stamp line was run twice, reason not recorded) to 19:09:33Z (root console: `IAMFullAccess` and the inline `scholarchain-operator-cli-login` on the admin IAM user).
  - Pre-checks PASS: the state held exactly the 18 expected resources; nothing but the deployer role used the 7 permission-set policies, and nothing used the 2 boundaries.
  - Plan `0 to add, 0 to change, 18 to destroy`, all 18 `delete` and equal to the expected list. Human decision, verbatim: "apply P39".
  - Apply 19:06:31-19:06:35Z: `Apply complete! Resources: 0 added, 0 changed, 18 destroyed.`; the deployer state is empty.
  - After: `get-role scholarchain-deployer` returns `NoSuchEntity`; only `scholarchain-billing-deployer` remains among the `scholarchain*` roles; no deployer policy or boundary remains.
  - The CLI close check could not run (the CLI login cannot refresh once the cli-login policy is removed). Root checked the user in the console, read-only: only the inline `scholarchain-assume-deployer` and `scholarchain-billing-assume-role`, no `IAMFullAccess`, no access key.
  - The budget call was AccessDenied for the admin user (expected). Root checked Budgets in the console, read-only: `scholarchain-project-budget`, USD 25.00, spent USD 17.87 (71.50%), Healthy.

## C11 billing check

**Done Friday 2026-11-20, read about 15:45Z** (human screenshots of the root console and the Voyage dashboard; totals in the decision log, per-service values and usage text in `evidence/session-2/c11/cost-report.log`):

- **AWS:** Cost Explorer, 2026-11-01 to 2026-11-20, daily by service, charge type Credit excluded: **USD 17.88**. The Session 2 day, Nov 18: **USD 2.13** (Neptune 0.49, EC2-Other 0.44, EC2-Instances 0.28, S3 0.26, DynamoDB 0.19, EFS 0.14, ECS 0.12, VPC 0.06, EMR 0.06, ELB 0.05, Secrets Manager 0.03, KMS 0.01). Nov 19 and Nov 20: USD 0.00 (Nov 19 shows S3, KMS and Glue lines at 0.00). As of the 15:45Z reading, no NAT gateway, Elastic IP, load balancer, Neptune, Fargate or EMR line accrues after Nov 18, and Route 53 shows no charge on Nov 18. Nov 20 was a partial day at the reading, and Cost Explorer can lag about a day.
- **Voyage AI:** dashboard, Cost tab, November 2026: USD 0.00 (voyage-4-lite 0.00, balance 0.00; inside the free tokens). The token count was not read. The R-b load-window figure (`docs/runbooks/session-2-plan.md:596-602`) cannot be isolated on the page: **unverified**.
- **Anthropic:** no Session 2 use. The project figure is the earlier phases' ledger, USD 0.075075 (0.08 on the receipt, human decision; deviation 4).
- **C11b cost report** (`scripts/lib/cost_report.py`, evidence `evidence/session-2/c11/cost-report.log`): AWS 17.88, Anthropic 0.08, Voyage AI 0.00, **combined USD 17.96**; ceiling USD 25.00, **remaining USD 7.04**. The project target of at most USD 23.00 is met.

The figures known at the session, kept for comparison:

| Item | Value |
|---|---|
| AWS before the session (Cost Explorer, credits excluded, data through Nov 15) | USD 15.75 |
| EMR ledger, Session 2 part | USD 0.37 (cumulative 2.05 of 3.53) |
| Voyage (upper bounds from the run reports) | ingest 2 USD 0.23 + query smoke USD 0.0232; ingest 1 was all HTTP 401 |
| Anthropic | no Session 2 use (ledger unchanged; placeholder key only) |
| Pre-R-b projection at Gate 1 | USD 20.20 against the 23.00 limit and the USD 25 ceiling |
| Root console reading, 2026-11-19 about 19:10Z (read-only; Nov 18 data still incomplete) | Cost Explorer Nov 1-19: USD 17.87; Budgets: USD 17.87 of 25.00 (71.50%) |

## Open items and deferrals

The items below are listed as found in the evidence. Their status (deferred, accepted or to fix) is for the human to set. The human set it in the decision of 2026-11-20 at the top of this file.

- **EMR Spark on EMR not proven:** the spark-job step fails at `hadoop fs -copyToLocal` (`EmrFileSystem` class not found). The vectors and graph come from the local P6 S export on the same HEAD, not from the EMR output. Route: spark-engineer / infra-engineer fix, then a fourth EMR ledger slot (1 left).
- **Load-test 5xx burst:** 65 × 5xx and 2 timeouts in under a second at about 50 concurrent users, during the scale-out. The cause is not diagnosed.
- **Incidents to write (incident-responder):**
  - the EMR copyToLocal failure;
  - ingest 1 with the invalid Voyage key;
  - the runtime-archive upload timeout;
  - the deployer role-session drops (credential gaps in the ECS poll at 20:42-20:50Z and later);
  - the load abort.
- **Kit and runbook gaps (documentation-engineer / infra-engineer):**
  - The kit omitted the narrow IAM policies that A7 and B3b need.
  - The admin profile cannot read Secrets Manager, ECS task lists or CloudWatch metrics.
  - Several kit read-checks were moved to the deployer profile during the session.
  - The deployer lacks `s3:ListAllMyBuckets`, `ecs:ListTasks`/`DescribeTasks` and `cloudwatch:GetMetricData`, so P37 running-task digests could not be read. The registry-digest check with immutable ECR tags was used instead.
- **Not verified:**
  - the IAM windows in CloudTrail (window 1 14:04:38-14:32:48Z, with the narrow b3b-keys and cli-login policies until 16:16:32Z; window 2 22:40:31-22:45:28Z; window 3 on 2026-11-19 18:58:04-19:09:33Z);
  - the window-1 closed check (its evidence file is empty; the close is in the decision log only);
  - console checks for EFS, ECR repositories and Elastic IPs (the Terraform destroy actions cover them);
  - deletion of the Route 53 zone behind the Cloud Map namespace (destroyed in pass 1, about 7.5 h after H0; console not checked);
  - the after-inventory EC2-instance entries;
  - the second KMS key in the inventory (`cb0a6f60`), whose state was not read;
  - the ECS cluster and service entries of the tagging inventory, which were not checked in the console (`aws_ecs_cluster.course` and the 4 services are in the pass-1 destroy actions);
  - the EMR cluster's TERMINATED state, which is only in the decision log (the saved state file reads TERMINATING; the ledger records the end at 17:06:31Z).
- **Known inert leftover (human decision 2026-11-19, verbatim):** "Keep scholarchain-assume-deployer for now. List it in the closeout as a known inert leftover (it points at a deleted role), to be removed from the root console after grading." The inline policy `scholarchain-assume-deployer` on the admin IAM user allows `sts:AssumeRole` only on `scholarchain-deployer`, which P39 deleted, so it grants nothing while no role of that name exists (re-applying `infra/terraform/deployer` would make it effective again, MFA required). The scope "only on `scholarchain-deployer`" is taken from the Phase 12D record; the policy document was not re-read in P39. Decision time: 2026-11-19T19:12:33Z. It was created by hand in Phase 12D and no Terraform root manages it. Removal: root console, after grading.
- **Deferred work:**
  - the Q12 run with clips 14-16;
  - video editing;
  - the Session 2 sections of `owner-report.md`, `test-report.md` and `repairs.md`.

## Deviations that need your decision

The human accepted deviations 1-5 in the decision of 2026-11-20 at the top of this file.

1. **Root console write to a secret value:** at 18:27Z, root replaced the `scholarchain-course/voyage-api-key` value with the working key in the console, instead of B3b `put-secret-value` from the CLI. Root was also used read-only, in a private window, for the dashboard clips (REC19, REC20) and REC22, and root removed the window policies at 16:16:32Z. At 18:05:56Z the human accepted that their e-mail may show in the root-console clips ("but accept to show my email"). This was recorded in the decision log after the fact; it replaces the earlier never-e-mail rule for those clips only. Check REC19, REC20 and REC22 before using them.
2. **IAM windows wider than the kit:**
   - `scholarchain-operator-a7-secrets`: decision "yes, add the a7 secrets policy";
   - `scholarchain-operator-b3b-keys` kept until 16:16:32Z: decision "A";
   - `scholarchain-operator-c5-secrets` in window 2.

   All were scoped to `scholarchain/course/*` or `scholarchain-course/*` and removed afterwards.
3. **Re-runs after a failure:**
   - the stage-a plan was re-run after an input fix (read-only);
   - base-apply was re-run as serial 2 after the upload timeout, on a new no-change plan (decision "A");
   - ingest was re-run under a new run id after the key fix.
4. **Anthropic figure in the receipts:** the console showed USD 0.60 on a key shared with another project. The human asked to use 0; the orchestrator recommended the project's own counted usage, USD 0.08; the human wrote 0.08 on the receipt.
5. **Smaller process slips, none of them with lasting effect:**
   - The operator and loader profiles were bound to the deployer session twice (blocks 15 and 25); both were corrected before use.
   - The orchestrator's first `put-user-policy` command was malformed (zsh `$ACCT:s`); nothing was added.
   - stop-task was run a second time on the already-stopped task in block 35, with no effect.
   - The block 16 and run-experiment dry runs used the pre-approved unredacted fallback (`env -u SCHOLARCHAIN_TF_PRIVATE_VARS`); the full logs stay private (only a STEP/RESULT excerpt of the run-experiment dry run is tracked).

## Closeout boundary

An approving decision recorded above, together with the human's separate explicit yes to the commit, authorizes committing the Session 2 records on `phase-15`, together with the reviewed P39 procedure and test (`infra/terraform/deployer/README.md`, `infra/terraform/deployer/tests/p39_inventory.tftest.hcl`), as the human asked on 2026-11-19 ("Commit the P39 procedure and test with the Session 2 records when you ask"). It does **not** authorize merging to `main`, any further AWS action (including removing `scholarchain-assume-deployer`), the Q12 run, or any spending.

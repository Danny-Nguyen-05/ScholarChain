# Incident 2026-11-18: permission gaps in the operator and deployer profiles, met through the root console or substitute checks

Status: closed for the session (every gap was worked around; no IAM was widened for them); kit and runbook follow-ups open. Severity: low (no unintended cloud change; some checks were replaced by weaker ones or moved to the root console).
Owner: incident-responder (record). Human decisions are quoted from the decision log and `../agent-runs/phase-15/human-gate.md`; this record does not alter them. The three narrow IAM policies that the kit omitted (a7, b3b, c5) have their own record: `2026-11-18-kit-missing-a7-b3b-c5-policies.md`.
Sources and limits: written offline from committed evidence; no cloud call. Times are UTC, with America/Chicago (CST, UTC-6) in brackets where useful. "Root console" means a read-only or explicitly approved use by the human in a private browser window. The caller identity in the raw AWS error texts was redacted by the evidence filter.

## Summary

Several Session 2 actions needed an AWS permission that the profile in use did not hold, by the design of the least-privilege roles: `s3:ListAllMyBuckets`, `ecs:ListTasks` and `DescribeTasks`, `cloudwatch:GetMetricData` and `secretsmanager:DescribeSecret` (loader) on the deployer or loader profiles; `ec2:DisassociateAddress` on the deployer; `budgets:ViewBudget` on the admin user; table listing for the reader role; and, after the window policy was removed, the CLI login refresh. The operator met each gap without widening IAM, by one of three routes: a substitute check on another profile, a read-only look in the root console, or a different command. The coordinator's rule for the EIP gap was explicit: do not widen IAM.

## Timeline

| Time (UTC) [CST] | Gap | How it was met | Source |
|---|---|---|---|
| 18:27:58 [12:27:58] | Loader role lacks `DescribeSecret`; the deployer session had expired | Check deferred to block 30, done with the deployer-tf profile at 20:22:44Z | decision log lines 43, 55 |
| 20:14:48 [14:14:48] | The reader role cannot list tables in the console (clip REC12) | Terminal view of the run-ledger item instead of a console table view | decision log line 51 |
| 20:32:44 [14:32:44] | No role holds `ecs:ListTasks` or `DescribeTasks` on the services, so P37 running-task digests were not readable | `deploy.sh verify-registry-images` checked registry digests against `push-record.json`; the ECR repositories are immutable, so the tag resolves to the pushed digest | decision log line 58 |
| 21:13:26 [15:13:26] | Deployer lacks `cloudwatch:GetMetricData` (elasticity dashboard) | Human decision (chat), verbatim: "I will do A" -- view the dashboard read-only as root in a private window for REC19 and REC20; no edits; sign out after; no `aws login` while root is signed in | decision log lines 64-65 |
| 22:27:36 [16:27:36] | Destroy pass 1: `aws_eip.nat` `DisassociateAddress` 403 (deployer role has no `ec2:DisassociateAddress`) | Kit rule: do not widen IAM. Pass 1 ended PARTIAL (297 to 65 inventory entries); pass 2 (22:33:17Z-22:34:13Z) destroyed only `aws_eip.nat` (65 to 63). Why pass 2 succeeded without the permission is not recorded | decision log lines 75-77; `../agent-runs/phase-15/evidence/session-2/section-c/cleanup-results.txt` |
| 22:47:15 [16:47:15] | `list-buckets` AccessDenied for the deployer (no `s3:ListAllMyBuckets`) | `head-bucket`: all 7 data-lake buckets returned 404. The trailing `EXISTS` lines in the log are a command artifact (the `echo EXISTS` fallback fired on the pipeline status, not on a bucket result) | decision log lines 85-86; `../agent-runs/phase-15/evidence/session-2/section-c/c8-inventory.log` |
| 2026-11-19 19:07:09 [13:07:09] | P39 block 7: `describe-budgets` AccessDeniedException for the admin user (no `budgets:ViewBudget`; expected) | Root console, read-only: budget USD 25.00, spent USD 17.87 (71.50%), thresholds OK, health Healthy (19:10:39Z) | decision log lines 97, 100; `../agent-runs/phase-15/evidence/session-2/p39/p39-budget-after.txt` |
| 2026-11-19 19:09:49 [13:09:49] | P39 window 3 close check: CLI login refresh refused (missing `signin:CreateOAuth2Token`, because the `cli-login` policy had been removed) | Root console, read-only, listed the user's permissions: two inline policies, no `IAMFullAccess`, no `cli-login` (19:10:18Z) | decision log lines 98-99; `../agent-runs/phase-15/evidence/session-2/p39/iam-window3-closed.txt` |

Other gaps listed in `../agent-runs/phase-15/human-gate.md` without a time: the admin profile cannot read Secrets Manager, ECS task lists or CloudWatch metrics; several kit read-checks were moved to the deployer profile during the session.

## Detection

Each gap showed up as an AccessDenied or 403 (or a refused login) from the AWS CLI or the console while a kit step ran, and was noted by the coordinator in the decision log. The destroy-pass failure was expected by the coordinator ("Expected failure", decision log line 75).

## Impact

- Verification quality: P37 (running-task digests) was replaced by a registry-digest check; the ECS cluster and service tag entries, the Route 53 zone, EFS, ECR and Elastic IP console checks, and the second KMS key were not checked and are listed as "not verified" in `../agent-runs/phase-15/human-gate.md`.
- Evidence: some results exist only as human readings of the root console (dashboard values, budget amount, window-3 policy list) and not as CLI output; the window-1 closed check file is empty (`../agent-runs/phase-15/evidence/session-2/a-setup/iam-window1-closed.txt`).
- Root use: the human used the root console for read-only checks and, once, for a write (below). The root-console clips REC19, REC20 and REC22 may show the human's e-mail address, accepted by the human at 18:05:56Z ("but accept to show my email") and confirmed on 2026-11-20.
- Cleanup: pass 1 ended PARTIAL at 22:27:36Z, which added a second listing (22:32:56Z) and a second pass (ended 22:34:13Z).
- Spend: none attributable.

## Root cause

By design of the least-privilege deployer, loader, reader and admin identities, plus kit read-checks and cleanup steps that assumed permissions those identities do not hold. Which gaps the kit authors knew in advance is not recorded in the evidence read; the closeout lists them as kit and runbook gaps for the documentation-engineer and infra-engineer (`../agent-runs/phase-15/human-gate.md`, "Kit and runbook gaps"). That the human wrote the root-console secret value instead of using a CLI `put-secret-value` (deviation 1, 18:27Z) belongs to the ingest and kit-policy records.

## Trace and run IDs

- Cleanup passes: pass 1 `20261118T221038Z-29957`, listing 2 `20261118T223224Z-34185`, pass 2 `20261118T223317Z-34981`.
- P39 window 3: 2026-11-19 18:58:04Z-19:09:33Z (from the first OPEN stamp).

## Recovery and the human decision behind it

Workarounds were chosen by the coordinator within the kit rule not to widen IAM; the human's own decisions are the root-console dashboard view ("I will do A", 21:13:26Z), the e-mail acceptance (18:05:56Z), and the acceptance of 2026-11-20, which lists the "not verified" items as accepted and calls for the kit gaps to be written up before 2026-11-25. No separate quoted human decision exists in the decision log for the other substitutions.

## What was not done

- No IAM change to close any of these gaps; no widening for `ec2:DisassociateAddress`, `ecs:ListTasks`, `cloudwatch:GetMetricData` or `s3:ListAllMyBuckets`.
- No console check of EFS, ECR, Elastic IPs, the Route 53 zone behind the Cloud Map namespace, the ECS cluster entries, or the second KMS key.
- No CloudTrail check of the three IAM windows.

## Follow-ups

Proposals for the owners; none is decided.

| Item | Owner | Status |
|---|---|---|
| For each read-check in the kit, name the profile that can run it and the fallback; remove checks that no profile can run | infra-engineer (kit), documentation-engineer (runbook) | Open (named in the closeout); whether done after the session is not recorded |
| Decide whether the destroy kit should list `aws_eip.nat` as an expected pass-1 403 and a pass 2 | infra-engineer | Proposed |
| Keep the "not verified" list in the final report | documentation-engineer | Not checked by this record |

## Evidence

- `../agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md` (lines 43, 51, 55, 58, 64-65, 75-77, 85-86, 90, 97-100)
- `../agent-runs/phase-15/evidence/session-2/section-c/cleanup-results.txt`
- `../agent-runs/phase-15/evidence/session-2/section-c/c8-inventory.log`
- `../agent-runs/phase-15/evidence/session-2/p39/p39-budget-after.txt`
- `../agent-runs/phase-15/evidence/session-2/p39/iam-window3-closed.txt`
- `../agent-runs/phase-15/evidence/session-2/a-setup/iam-window1-closed.txt`
- `../agent-runs/phase-15/human-gate.md` (open items, deviations 1 and 2)
- `../agent-runs/phase-15/evidence/session-2/INDEX.md`
- `2026-11-18-kit-missing-a7-b3b-c5-policies.md`

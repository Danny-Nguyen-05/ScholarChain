# Incident 2026-11-18: the live kit lacked the narrow a7, b3b and c5 IAM policies

Status: closed for the session (each policy was added by the human or the IAM user under a recorded decision and removed afterwards); the kit and runbook correction is open. Severity: low (one failed step, nothing created; IAM windows wider than the kit for a short time).
Owner: incident-responder (record). Human decisions are quoted from the decision log; this record does not alter them.
Sources and limits: written offline from committed evidence; no cloud call. Times are UTC on 2026-11-18, with America/Chicago (CST, UTC-6) in brackets where useful. Policy names and scopes come from the decision log; the policy documents themselves were not read. Whether the kit or runbook was corrected after the session is not recorded in the evidence read. The wider list of permission gaps is in `2026-11-18-console-permission-gaps.md`.

## Summary

The Session 2 kit's IAM windows did not include the narrow inline policies that the secret steps need for the IAM user `scholarchain-billing-operator`. At block 6 (A7) every `create-secret` and `describe-secret` call returned AccessDenied because the user had no Secrets Manager permission; the decision log says the kit omitted the narrow `scholarchain-operator-a7-secrets` inline policy used in Session 1. The human approved adding it ("yes, add the a7 secrets policy"). The B3b step (provider keys) needed `scholarchain-operator-b3b-keys`, added under the human's decision "A", and the cleanup step C5 (secret deletion) needed `scholarchain-operator-c5-secrets` in IAM window 2. `../agent-runs/phase-15/human-gate.md` records the omission for A7 and B3b ("The kit omitted the narrow IAM policies that A7 and B3b need") and lists the c5 policy among the "IAM windows wider than the kit" (deviation 2), which the human accepted on 2026-11-20.

## Timeline

| Time (UTC) [CST] | Event | Source |
|---|---|---|
| 14:04:38 [08:04:38] | IAM window 1 opens (root console): `IAMFullAccess` and inline `scholarchain-operator-cli-login` on the operator user | decision log line 1 |
| 14:25:01 [08:25:01] | Block 6 (A7) attempt 1: four `create-secret` and four `describe-secret` calls AccessDenied; nothing created; the smoke API key generated in the attempt is unused (the human replaces the password-manager entry) | decision log line 6; `../agent-runs/phase-15/evidence/session-2/a-setup/a7-secrets.log` |
| 14:25:01 | Human decision (chat), verbatim: "yes, add the a7 secrets policy" -- inline policy `scholarchain-operator-a7-secrets` (`secretsmanager:CreateSecret`, `DescribeSecret` on the `scholarchain/course/*` secret path in the account) added by the IAM user during window 1, removed right after A7 | decision log line 7 |
| 14:26:15 | The first `put-user-policy` attempt failed `MalformedPolicyDocument` (coordinator command: the zsh `:s` modifier on the account variable); nothing added | decision log line 8 |
| 14:27:11 | `scholarchain-operator-a7-secrets` added; inline list: assume-deployer, billing-assume-role, a7-secrets, cli-login | decision log line 8 |
| before 14:31:04 (time not recorded) | An A7 rerun failed parameter validation (the temp directory for the secret string file was missing; "step 2 skipped"); nothing created | decision log line 9; `../agent-runs/phase-15/evidence/session-2/a-setup/a7-secrets.log` |
| 14:31:04 [08:31:04] | A7 PASS: the four `scholarchain/course/*` secrets created; values never shown | decision log line 9 |
| 14:32:06 [08:32:06] | Human decision (chat), verbatim: "A" -- close IAM window 1 now (remove `scholarchain-operator-a7-secrets` and `IAMFullAccess`), add the narrow inline `scholarchain-operator-b3b-keys` (`secretsmanager:PutSecretValue`, `DescribeSecret` on `scholarchain-course/*`), keep `scholarchain-operator-cli-login` until block 15 (B3b) is done, then remove both | decision log line 10 |
| 14:32:48 [08:32:48] | Window 1 closed: `IAMFullAccess` detached, a7-secrets removed; inline now assume-deployer, billing-assume-role, b3b-keys, cli-login | decision log line 11 |
| 16:15:29 [10:15:29] | B3b PASS (`put-secret-value`; one AWSCURRENT version each) | decision log line 24; `../agent-runs/phase-15/evidence/session-2/a-setup/b3b-provider-keys.log` |
| 16:16:32 [10:16:32] | `b3b-keys` and `cli-login` removed by root in the console; the user keeps assume-deployer and billing-assume-role | decision log line 25 |
| 22:40:31 [16:40:31] | IAM window 2 opens (root console): `IAMFullAccess` and `cli-login` | decision log line 78 |
| 22:41:37 | `scholarchain-operator-c5-secrets` added by the IAM user (`secretsmanager:DeleteSecret`, `DescribeSecret` on `scholarchain/course/*`) | decision log line 79 |
| 22:44:34 | C5 PASS: the four secrets force-deleted | decision log line 83; `../agent-runs/phase-15/evidence/session-2/section-c/c5-secrets-delete.log` |
| 22:45:28 [16:45:28] | Window 2 closed (root removed `IAMFullAccess`, `cli-login`, `c5-secrets`); only the two inline policies remain | decision log line 84; `../agent-runs/phase-15/evidence/session-2/section-c/iam-window2-closed.txt` |

## Detection

A7: the AWS CLI's own AccessDenied output (`../agent-runs/phase-15/evidence/session-2/a-setup/a7-secrets.log`), read by the coordinator at 14:25:01Z. B3b and C5: the b3b policy first appears in the human's decision at 14:32:06Z and the c5 policy was added at 22:41:37Z. No b3b or c5 failure is recorded, so how those needs were identified (in advance or by an error) is not recorded.

## Impact

- One failed step: A7 attempt 1 (about 6 minutes from the failure to the pass, 14:25:01Z to 14:31:04Z, including a malformed command and a skipped-step rerun).
- IAM windows longer or wider than the kit: window 1 14:04:38Z-14:32:48Z with `IAMFullAccess`; `b3b-keys` 14:32:48Z-16:16:32Z and `cli-login` 14:04Z-16:16:32Z; window 2 22:40:31Z-22:45:28Z. All added policies were scoped to `scholarchain/course/*` or `scholarchain-course/*` (the b3b scope uses the second form) and removed afterwards.
- Secrets: no value was displayed. A smoke API key generated in the failed attempt was left unused (human replaced the password-manager entry).
- Root console use: root removed the window policies (16:16:32Z, 22:45:28Z); `../agent-runs/phase-15/human-gate.md` deviation 1 lists the root-console replacement of the secret value at 18:27Z separately (see the ingest record).
- Not verified: the IAM windows were not checked in CloudTrail (`../agent-runs/phase-15/human-gate.md`, "Not verified"); the window-1 closed check output file is empty (`../agent-runs/phase-15/evidence/session-2/a-setup/iam-window1-closed.txt`); the close is recorded only in the decision log.

## Root cause

The kit was written without the three narrow secret policies, although the decision log notes that Session 1 used the a7 policy. Why the policies were left out (a copy omission, a design decision to keep the windows minimal, or something else) is not recorded. The c5 policy is described only as a window wider than the kit; the log does not say whether a kit step for it existed.

## Trace and run IDs

- No run id. IAM windows: window 1 14:04:38Z-14:32:48Z (b3b-keys and cli-login to 16:16:32Z); window 2 22:40:31Z-22:45:28Z.
- Secret names: the four `scholarchain/course/*` secrets (api-key-sha256, internal-token-sha256, internal-token, graph-cursor-key) and the two provider-key containers under `scholarchain-course/` (voyage-api-key, anthropic-api-key). ARNs are in a private file and are not reproduced here.

## Recovery and the human decision behind it

- a7: "yes, add the a7 secrets policy" (14:25:01Z).
- b3b: "A" (14:32:06Z).
- c5: the decision log has no separate quoted decision for the c5 policy. The human opened window 2 at 22:40:31Z, the IAM user added the policy at 22:41:37Z, and the human approved the C4 apply ("yes apply c4", 22:43:53Z, which concerns the Terraform apply, not the policy). Deviation 2 in `../agent-runs/phase-15/human-gate.md` lists the policy, and the human accepted deviations 1-5 on 2026-11-20.

## What was not done

- No change to the kit or runbook during the session.
- No widening of any Terraform-managed role; the policies were inline on the user, added by hand in the console or CLI window, and removed.
- No CloudTrail verification of the windows.

## Follow-ups

| Item | Owner | Status |
|---|---|---|
| Add the three policies (name, actions, resource scope, add and remove time) as reviewed window steps to the kit and runbook, so that the windows match the steps | infra-engineer (kit), documentation-engineer (runbook) | Open; named in the closeout as "Kit and runbook gaps"; completion not recorded |
| Check the three windows in CloudTrail | human | Open (accepted as "not verified" on 2026-11-20) |
| Decide whether the user's inline policy `scholarchain-assume-deployer`, now pointing at a deleted role, is removed after grading | human | Recorded as a known inert leftover (decision 2026-11-19T19:12:33Z) |

## Evidence

- `../agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md` (lines 1, 6-11, 24-25, 78-84)
- `../agent-runs/phase-15/evidence/session-2/a-setup/a7-secrets.log`
- `../agent-runs/phase-15/evidence/session-2/a-setup/b3b-provider-keys.log`
- `../agent-runs/phase-15/evidence/session-2/a-setup/iam-window1-closed.txt`
- `../agent-runs/phase-15/evidence/session-2/section-c/c5-secrets-delete.log`
- `../agent-runs/phase-15/evidence/session-2/section-c/iam-window2-closed.txt`
- `../agent-runs/phase-15/human-gate.md` (open items, deviation 2)
- `../agent-runs/phase-15/evidence/session-2/INDEX.md` (a-setup section)
- `2026-11-18-console-permission-gaps.md`

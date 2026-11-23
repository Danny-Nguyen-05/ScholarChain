# Incident 2026-11-18: deployer role-session drops and profile mix-ups during the live session

Status: closed for the session (each drop was met by a fresh login); the cause of the later drops is not recorded and no durable fix is recorded. Severity: low (no change to cloud state; lost monitoring samples and some operator time).
Owner: incident-responder (record). Human decisions are quoted from the decision log; this record does not alter them.
Sources and limits: written offline from committed evidence; no cloud call. Times are UTC on 2026-11-18, with America/Chicago (CST, UTC-6) in brackets where useful. The session drops were not logged as events; they are visible as coordinator notes and as blank lines in the ECS poll file. The expiry limits come from the decision log's deployer verification (line 4: deployer 3,600 s, operator roles 14,400 s) and the plan's token-expiry row (`docs/runbooks/session-2-plan.md`: "Token expiry (deployer 1 h, operator roles 4 h): Fresh Switch Role and `aws login` before each step").

## Summary

The deployer role session is limited to 1 hour, and the operator roles to 4 hours. During Session 2 the operator renewed the deployer login several times. On at least three occasions the evidence shows a session that had expired or could not supply credentials: the 18:27Z secret check was deferred because the deployer session had expired; the ECS poll of the load test returned blank lines (credential_process failure) from its first sample at 20:37:23Z until a re-login at about 20:50Z, and again in later stretches. Separately, twice an AWS CLI profile was bound to the wrong role session (an operator profile held a deployer session at block 15, and the loader profile at block 25); both were corrected before use.

## Timeline

| Time (UTC) [CST] | Event | Source |
|---|---|---|
| 14:14:13 [08:14:13] | Deployer apply: deployer `max_session_duration` 3,600, operator roles 14,400 | decision log line 4 |
| about 14:49 | Fresh deployer login before base-apply 1 | decision log line 19 |
| about 15:12 | Fresh deployer login before the recovery plan | decision log line 22 |
| 16:15:29 [10:15:29] | Block 15: the operator profile had been bound to an assumed-role deployer session; the human overwrote it with the IAM user login before the secret write | decision log line 24 |
| 17:26:27 [11:26:27] | Block 25: the loader profile was first bound to the deployer session (human answered y while the console was on the deployer); corrected; both loader profiles resolved to the loader role (STS check 17:26Z) | decision log line 38 |
| 18:27:58 [12:27:58] | Coordinator `describe-secret` check deferred: the deployer session had expired, and the loader role lacks DescribeSecret; moved to block 30 | decision log line 43 |
| 20:16:45 [14:16:45] | Deployer login refreshed in terminal 2 during the Neptune base-apply, "to avoid the 1-h role-session expiry" (preventive) | decision log line 52 |
| 20:22:44 | Block 30 keys check done with the deployer-tf profile (the deferred check) | decision log line 55 |
| 20:37:23-20:50:52 | ECS poll lines blank (14 samples); the decision log names 20:42-20:50Z and "credential_process failure" | `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log`; decision log line 61 |
| about 20:50 [14:50] | Deployer re-login (terminal 2); first good poll line 20:51:54 | decision log line 61 |
| 21:01:03-21:14:32 | Blank poll lines (14 samples); data resumes 21:15:35 | `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log` |
| 21:25:46-21:34:03 | Blank poll lines (9 samples); data resumes 21:35:04 | same |
| 21:45:13-21:49:22 | Blank poll lines (5 samples); data resumes 21:50:24 | same |
| 22:00:33-22:09:52 | Blank poll lines (10 samples); data resumes 22:10:54 (last line 22:13:57) | same |
| 22:27:36 [16:27:36] | After destroy pass 1, the coordinator's next step is pass 2 with a "fresh login" | decision log line 75 |

The poll has 95 lines, 43 with data and 52 blank (`../../experiments/results/phase16/performance/performance-metrics.md`, section 3; the counts agree with a re-count of the committed file). The data stretches are 9, 10, 10, 10 and 4 samples long (from `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log`: 20:51:54-21:00:02, 21:15:35-21:24:45, 21:35:04-21:44:12, 21:50:24-21:59:32, 22:10:54-22:13:57); each of the first four is followed by a blank stretch, and the last runs to the end of the file.

## Detection

Operator observation and coordinator notes (the 18:27Z expiry, the 20:16:45Z preventive refresh), and the blank lines of the poll file, which the decision log attributes to a credential failure. The profile mix-ups were corrected before use; how the block 15 one was noticed is not recorded, and at block 25 the coordinator's STS check at 17:26Z confirmed the corrected profiles. The A5 rehearsal at 14:21:47Z had shown every profile resolving to its own role.

## Impact

- Monitoring: 52 of the 95 ECS poll samples are blank. The instant the desired count changed during the load test is unknown; scale-out and scale-in are given only as brackets from the poll grid (about 61 s), and no CloudWatch alarm history was saved (`../../experiments/results/phase16/performance/performance-metrics.md`, sections 3 and 9). See the load-test record.
- The 18:27Z secret check ran about 2 hours later (block 30, 20:22:44Z).
- Operator time for each re-login: not recorded.
- No cloud change was made under a wrong or stale identity: the mix-ups were corrected before use, and `../agent-runs/phase-15/human-gate.md` (deviation 5) says none had lasting effect.

## Root cause

Direct cause for the 18:27Z deferral and the 20:16:45Z preventive refresh: the 1-hour deployer role-session limit (decision log wording). For the 20:37-20:50Z blank stretch the decision log says credential_process failure; it does not say whether the session had expired or the login refresh had failed. For the three later blank stretches and the pattern of short data stretches between them, the cause is not recorded.

The profile mix-ups: the human or coordinator answered or ran a login while the console held a different role session (the log says the loader was first bound while "the console was on the deployer"); the exact commands are not recorded.

Contributing, from the plan: the session design put one short-lived deployer session under long operations (an upload of about 52 minutes, a 19-minute Neptune apply, a 3,570 s load plan) and a poll loop that does not renew its own credentials (that last point is an inference from the blank lines, not a recorded fact).

## Trace and run IDs

- No run id. Poll file `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log`; load run `rb-20261118`; base-apply and plan run ids are in the base-apply record.

## Recovery and the human decision behind it

Each drop was met by a fresh deployer login by the human, as the plan's token-expiry row prescribes. The decision log records no separate human decision for a login. The two profile mix-ups were corrected by the human before use; both are listed in deviation 5 of `../agent-runs/phase-15/human-gate.md`, which the human accepted on 2026-11-20.

## What was not done

- No change to session durations or to IAM.
- No renewal inside the poll loop, and no re-run to fill the poll gaps.
- No record of the cause of the 21:01-22:10Z blank stretches.

## Follow-ups

Proposals for the owners; none is decided.

| Item | Owner | Status |
|---|---|---|
| Have long-running monitor loops renew credentials, or fail loudly instead of writing a blank line | experiment-engineer / infra-engineer (scripts) | Proposed |
| Add an identity check (STS caller identity) before each login-sensitive step, and a note on binding profiles to the correct session | documentation-engineer (runbook) | Proposed; part of the A5 and block 25 checks already exists |
| Save a service-event or alarm export alongside the poll so that a poll gap does not lose the timing | experiment-engineer | Proposed |

## Evidence

- `../agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md` (lines 4, 19, 22, 24, 38, 43, 52, 55, 61, 75)
- `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log`
- `../agent-runs/phase-15/evidence/session-2/a-setup/a5-login-rehearsal.log`
- `../agent-runs/phase-15/human-gate.md` (open items, deviation 5)
- `../../experiments/results/phase16/performance/performance-metrics.md` (sections 3 and 9)
- `../runbooks/session-2-plan.md` (token-expiry row)

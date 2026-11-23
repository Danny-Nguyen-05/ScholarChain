# Incident 2026-11-18: R-b load test aborted on a 5xx burst during the elasticity run

Status: open as a known limitation (accepted by the human on 2026-11-20; cause not diagnosed; no rerun, and the stack was destroyed the same day). Severity: medium (the only AWS load evidence is an aborted run; the elasticity result is partial).
Owner: incident-responder (record). Human decisions are quoted from the decision log; this record does not alter them.
Sources and limits: written offline from committed evidence, including the frozen raw event log; no cloud call. Times are UTC on 2026-11-18, with America/Chicago (CST, UTC-6) in brackets where useful. The ECS poll for the run has blank lines (credential gaps, see the session-drop record), and no CloudWatch alarm history, ECS service-event export or ALB log was saved, so the sequence inside the burst is not reconstructable.

## Summary

Run `rb-20261118` (manifest `15b-ecs-scaling-semantic`, semantic route, LLM disabled, 7 planned phases, 3,570 s) started at 20:43:32.897Z against the deployed query-api. Phases warmup, baseline-1, level-5, level-25 and level-50 completed with no error and no 429. In `hold-50` (50 workers), 67 requests failed: 49 HTTP 503, 16 HTTP 504 and 2 transport timeouts. The load generator's guard aborted the run at 20:52:49.770Z (`repeated-5xx-or-transport-failures`; exit 4); the run ended at 20:52:54.484Z with 26,962 requests, 26,895 of them ok. The brief for this record gave "20:52:44Z" as the abort time; the decision log (line 62) gives 20:52:44.209Z as the start of the failed requests, and the raw events put the abort event at 20:52:49.770Z. The human accepted the aborted run as the R-b result and chose no rerun.

## Timeline

| Time (UTC) [CST] | Event | Source |
|---|---|---|
| 20:36:09 [14:36:09] | Block 32 smoke PASS (healthz and readyz 200); GO/NO-GO 3 GO; four services 1/1 | decision log line 59 |
| 20:43:32 [14:43:32] | Load start; `validate-manifest` MANIFEST-OK; plan PLAN-OK (7 phases, 3,570 s, LLM disabled) | decision log line 60; `../agent-runs/phase-15/evidence/session-2/b10-load/b10-plan.log`, `b10-validate.log` |
| 20:49:16.439 | Phase `level-50` starts (12,575 requests, all ok, ends 20:52:17.167) | raw `events.jsonl` |
| 20:51:54 | ECS poll: desired 1, running 1, pending 0 (first poll line with data after a blank run) | `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log` |
| 20:52:17.171 | Phase `hold-50` starts (planned 600 s) | raw `events.jsonl` |
| 20:52:44.209-.423 [14:52:44] | The 65 server errors (16 x 504, 49 x 503; about 5.5 s latency; 118-byte bodies) all start within 0.3 s | decision log line 62 |
| 20:52:49.770 | `abort` event: `repeated-5xx-or-transport-failures` | raw `events.jsonl` |
| 20:52:54.483-.484 | `hold-50` phase end (2,024 requests: 1,957 ok, 65 server_error, 2 timeout); `cooldown-observe` skipped; run end `aborted` | raw `events.jsonl` |
| 20:52:55 | ECS poll: desired 2, running 1, pending 1 (the scale-out decision is first seen here) | `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log` |
| 20:53:56 | ECS poll: desired 2, running 2, pending 0 | same |
| 20:54:37 [14:54:37] | Coordinator logs the abort and asks the human: accept as the R-b result, or rerun after scale-in | decision log line 62 |
| 20:55:16 [14:55:16] | Human decision (chat), verbatim: "A" - accept the aborted rb-20261118 load as the R-b result (scale-out shown; report the 0.25% error burst and the abort honestly); no rerun; observe scale-in with the ECS poll | decision log line 63 |
| about 20:54-20:55 | Dashboard reading: HealthyHostCount 1 to 2 | decision log line 65 (human reading) |
| 21:00:02 | Last poll with desired 2; the next poll with data is 21:15:35 (1/1/0) | `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log` |
| about 21:09-21:10 | Dashboard reading: HealthyHostCount 2 to 1 | decision log line 65 |
| 21:13:26 | Human decision (chat), verbatim: "I will do A" -- view the elasticity dashboard read-only as root in a private window for the clips; no edits | decision log line 64 |
| 21:33:01 | Clips REC19 and REC20 recorded: CPU max 75.79%, request peak about 4.21K per minute, p99 spike to 5 s at about 20:52Z | decision log line 65 |

## Detection

The load generator's own guard (aborts on repeated 5xx or transport failures: 20 of the last 40 requests; `load-tests/README.md`), console result `RESULT: ABORTED run=rb-20261118 requests=26962 llm_answers=0 reason=repeated-5xx-or-transport-failures`, exit 4.

## Impact

- The AWS load result is partial: `hold-50` ran about 32.6 s of a planned 600 s (20:52:17.171Z to 20:52:49.770Z); the 1,800 s `cooldown-observe` phase was skipped. The runbook estimated about 6.5 minutes to scale out and a 10-minute hold (`docs/runbooks/session-2-plan.md`, hold arithmetic; an estimate, not a measurement).
- No complete level was measured on 2 tasks (`../../experiments/results/phase16/performance/performance-metrics.md`, section 9). Throughput and latency at 2 tasks versus 1 are a recorded gap.
- Error burst: 67 of 26,962 requests failed (0.25% of the run; 3.31% of `hold-50`). `hold-50` p99 was 5,189.981 ms against 899.765 ms at `level-50`. No request was throttled (0 x 429 in every phase).
- Scale-out was observed after the burst: desired 2 first seen at 20:52:55Z, 2 running by 20:53:56Z, scale-in to 1 by the 21:15:35Z poll (dashboard about 21:09-21:10Z).
- Spend: LLM disabled; `llm_answers` 0; harness-estimated Anthropic and Voyage cost 0.000000. The AWS cost of the load cannot be separated from the rest of the day (`../../experiments/results/phase16/performance/performance-metrics.md`, section 8).

## Root cause

Not determined (`../agent-runs/phase-15/human-gate.md`: "The cause is not diagnosed"). Known: the burst began about 27 s into `hold-50` at 50 concurrent workers; all 65 server errors started within 0.3 s and carried about 5.5 s latency; the status codes were 503 and 504 (which layer produced each reply is not recorded); CPU peaked at 75.79% on the dashboard; the poll first shows the desired count at 2 after the burst (20:52:55Z); and every earlier phase, including level-25 and level-50, had 0 errors. Whether the burst was a capacity limit of the single task, a health-check or target-deregistration effect, or something else is not recorded: no service events, alarm history, ALB logs or task logs were saved, and the stack was destroyed (cleanup pass 1 at 22:10:38Z).

## Trace and run IDs

- Run id `rb-20261118`; manifest `15b-ecs-scaling-semantic`; commit `bd0b818`; raw sha256 `raw.sha256` and SHA256SUMS in the frozen raw directory.
- Raw files (frozen, scanned): `requests.jsonl`, `events.jsonl`, `run-record.json`, `summary.csv` under `experiments/results/phase16/performance/raw-rb-20261118/`.
- Runtime apply that created the stack: run `20261118T202540Z-14947`.

## Recovery and the human decision behind it

No recovery action was taken on the service side. The service scaled out; the clip REC18b recorded at 21:33:01Z shows the four services running equal to desired, the target healthy and healthz passing (decision log line 65). The human's decision "A" (quoted above) accepted the result, with the instruction to report the burst and the abort honestly. That decision was repeated in the acceptance of 2026-11-20: "the load-test 5xx burst is a known, documented limitation".

## What was not done

- No rerun of the load test (human decision).
- No diagnosis of the 503 and 504 replies.
- No cooldown observation phase; scale-in was seen only through the poll and the dashboard.
- No CloudWatch alarm history, ECS service events or ALB logs saved before teardown.
- No change to the load profile or the service in response.

## Follow-ups

Proposals for the owners; none is decided.

| Item | Owner | Status |
|---|---|---|
| Before any future live load, save service events, alarm history and ALB access logs with the run | experiment-engineer / documentation-engineer (runbook) | Proposed |
| Diagnose the 503 and 504 burst only if a new live session is approved; it cannot be reproduced offline | human decision | Open |
| Decide whether the load plan should pre-scale or ramp slower before `hold-50` | experiment-engineer | Proposed; not decided |
| Keep the abort and burst statement in the evaluation report | documentation-engineer | In `experiments/results/phase16/performance/performance-metrics.md`; final report not checked by this record |

## Evidence

- `../agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md` (lines 59-65)
- `../agent-runs/phase-15/evidence/session-2/b10-load/b10-loadgen.log`
- `../agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log`
- `../agent-runs/phase-15/evidence/session-2/b10-load/b10-plan.log` and `../agent-runs/phase-15/evidence/session-2/b10-load/b10-validate.log`
- `../../experiments/results/phase16/performance/performance-metrics.md` (sections 1, 3, 8, 9, 10)
- `../../experiments/results/phase16/performance/raw-rb-20261118/events.jsonl`
- `../../experiments/results/phase16/performance/raw-rb-20261118/run-record.json`
- `../../experiments/results/phase16/performance/raw-rb-20261118-freeze-note.json`
- `../../load-tests/README.md`
- `../runbooks/session-2-plan.md`
- `../agent-runs/phase-15/human-gate.md` (R-b load test, open items)

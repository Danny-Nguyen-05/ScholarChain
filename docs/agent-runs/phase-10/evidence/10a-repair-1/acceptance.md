# F1 repair acceptance evidence

| Required behavior | Test evidence | Pre-fix result | Post-fix result |
|---|---|---|---|
| Retried(1,Written(session)) owns creation, binds body, schedules exactly once | RetriedSessionCreationSpec: Retried Written owns creation, binds the body and executes exactly once across replay | FAIL: first response503 | PASS |
| First response200 or202with valid job; completed result persisted | Same creator test checks status, job ID if pending, backing SUCCEEDED record and literal synthetic answer | Creator assertion failed before result | PASS |
| Same-body replay returns stored result without rerun | Creator test compares identical persisted response and exactly one workflow call | Creator assertion failed | PASS |
| Different body409 with same key | Creator test checks409 and call count remains1 | Creator assertion failed | PASS |
| Retried Unchanged reconciles without starting work | Seeded session, independent new workflow counter0, stored response and changed-body409 | PASS | PASS |
| Retried Rejected reconciles without starting work | Seeded session, synthetic ambiguous rejected reply, counter0, stored response and changed-body409 | PASS | PASS |

The new test failed against old production code, then all3passed after the minimal branch normalization. Post-fix service gate19/19 and independent10A20/20 passed. Final fullcheck evidence is recorded separately when it completes.

F2–F5 remain nonblocking external findings and were not repaired. No10B work. Images were not rebuilt and predate this source repair.

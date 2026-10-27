
# Subphase 10A repair round 1

| Finding | Severity / disposition | Owner | Acceptance check |
|---|---|---|---|
| F1 | High, blocking, routed for repair | service-engineer | Retried(1,Written(s)) binds/schedules once; first200 or202 with valid job; same-body stored replay no rerun; different-body409; Retried Rejected/Unchanged reconcile without execution; module, independent10A and full JDK17 check pass. |
| F2 | Medium, nonblocking, listed only; not authorized for this repair | service-engineer | Terminal failure replay retryable:false or document/test new key required. |
| F3 | Low, nonblocking, listed only | service-engineer |202 reference reflects persisted state or documents QUEUED as accepted. |
| F4 | Low, nonblocking, listed only | service-engineer | Configuration failure exits nonzero. |
| F5 | Low, nonblocking, listed only | test-engineer / service-engineer | Test failed half-open probe reopening,429 queue-full and RESULT_TOO_LARGE. |

Only F1 is in scope. No10B work or reviewer invocation. Exact user-supplied verdict/findings in review.md and evidence/10a-repair-1/external-review.txt.

## F1 implementation/gate result (review pending)

Successful retried creation now shares the creator path; other retried results still reconcile without execution. Regression red3run/2pass/1fail reproduced503; post-fix services19/19,independent10A20/20,fullcheck1173/1173pass,exit0,JDK17. Final gate713s. Evidence: evidence/10a-repair-1/. F2–F5 untouched. Independent recheck must decide acceptance; this entry is not reviewer approval.


# Subphase 10A

user-supplied external review

VERDICT: REQUEST-CHANGES for Subphase 10A.
F1 (High, BLOCKING) — QueryService.scala:182-195 with StorageRows.scala:208 and
DynamoStorage.scala:161-171. DynamoRows.transact retries with a fixed ClientRequestToken; a
successful retry makes RowSessions.createIfAbsent return Retried(n, Written(session)), meaning
this caller created the reservation. QueryService.submit treats every Retried as a lost reply,
never binds the fingerprint or schedules the workflow, polls an unbound "{}" row and returns
503; all replays and GET /v1/jobs/{jobId} for that key then return 503 permanently. No test
covers Retried. Owner: service-engineer. Acceptance: a module test whose store returns
Retried(1, Written(s)) from createIfAbsent gives exactly one workflow run, a 200 (or 202 with
a valid jobId) first response, a same-body replay of the stored result without rerun, and 409
for a different body; Retried(n, Rejected(..)) and Retried(n, Unchanged(..)) still reconcile
without starting work; services/test, the 10A independent tests and full sbt -batch check on
JDK 17 pass.
F2 (Medium, nonblocking) — QueryService.scala:147-151,105-110: a queue-full 429 and exhausted
retryable 502/503/504 failures are persisted with retryable:true, so same-key retries can never
succeed. Replay stored terminal failures as retryable:false, or document/test that a new
Idempotency-Key is required. Owner: service-engineer.
F3 (Low, nonblocking) — QueryService.scala:118: the 202 job reference always reports status
QUEUED, even while RUNNING. Owner: service-engineer.
F4 (Low, nonblocking) — ServiceMains.scala:10: configuration failure exits the JVM with code 0;
it should exit nonzero. Owner: service-engineer.
F5 (Low, nonblocking) — no tests for a failed half-open probe reopening the breaker, the 429
queue-full path or RESULT_TOO_LARGE. Owners: test-engineer / service-engineer.
Future scope (10B): links.evidence in the sync response; DownstreamClient production wiring and
breaker gauges in the mains; graph/semantic/worker/explain/evidence routes; lifecycle test;
final OpenAPI.

# Subphase 10A repair round 1

user-supplied external review

VERDICT: APPROVE for Subphase 10A repair round 1.
F1 CLOSED: QueryService.scala:127-133 rewrites only Retried(_, Written(s)) to Written(s), which
then uses the same body-binding, revision CAS and scheduling path as a normal creation; all other
Retried outcomes still reconcile without execution. RetriedSessionCreationSpec failed before the
fix (3 tests/2 passed/1 failed, retried creator returned 503) and covers every acceptance
assertion: 200 or 202 with a valid jobId, stored same-body replay, 409 for a different body,
exactly one workflow run, persisted SUCCEEDED row, and zero runs for Retried Unchanged/Rejected.
Evidence verified: 23/23 source hashes match; only QueryService.scala and the services README
changed; full sbt check log SHA-256 964d6d80…b223f, 1173 passed/0 failed, 140 suites, exit 0,
JDK 17.0.20.1.
Nonblocking, carried: F2 (Medium) stored terminal failures keep retryable:true although a
same-key replay never reruns; F3 (Low) 202 reference always says QUEUED; F4 (Low) invalid
startup configuration exits 0; F5 (Low) missing tests for a failed half-open probe, the queue-full
429 path and RESULT_TOO_LARGE; O1 local Docker images predate F1 (rebuild in 10B task 7); O2 the
spec text from the failing pre-fix run was not hash-retained (line 63 vs current line 75 after
formatting).

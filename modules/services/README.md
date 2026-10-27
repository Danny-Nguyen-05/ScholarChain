# Services foundation (Phase 10A)

`ApiApplication` exposes the HTTP contract through Cask 0.10.2 / Undertow on Java 17.
Routes delegate to `QueryService`; retrieval and synthesis remain behind `QueryWorkflow`.
`RuntimeWorkflowAdapter` composes the real Phase 9 `RuntimeAnswerWorkflow` with an injected
plan resolver, using `runPlan` only after checking every explicit constraint against the plan.
The resolver must use configured corpus windows and return a typed rejection for unsupported
requests. The service never derives metrics, identities, paths or scores from model text.

The four packaged main classes are `QueryApiMain`, `GraphServiceMain`,
`SemanticServiceMain` and `EmbeddingWorkerMain`, all in
`edu.uic.cs441.scholarchain.services`. **Their 10A bootstrap has no configured runtime:**
`/healthz` is 200, `/readyz` is 503, and query work fails with typed 503. It constructs no
AWS SDK or model-provider client. Injection tests supply explicit fake workflows; a separate
module test runs the real retrieval, verification and audit composition against the versioned
synthetic Phase 9 fixture and proves truthful abstention when synthesis is unavailable.
Successful fake API responses are fixture observations, not deployed corpus answers.

## HTTP surface

| Service | Method/path | Behavior in 10A |
| --- | --- | --- |
| query-api | POST `/v1/query` | Validated synchronous answer or 202 job reference |
| query-api | GET `/v1/jobs/{jobId}` | Persisted state, public stage, timestamps, failure and result URL |
| query-api | GET `/v1/jobs/{jobId}/result` | Stored answer, pending 202 or stored typed failure |
| all | GET `/healthz` | Public process liveness |
| all | GET `/readyz` | Public injected dependency reachability check |
| all | GET `/metrics` | Authenticated Prometheus text |

`X-Request-Id` and `X-Trace-Id` are accepted when they match the bounded correlation-token
syntax; invalid or absent IDs are replaced. Both are returned on every application response
and passed to downstream operations. Error JSON is flat: `error`, `message`, `traceId`,
`retryable`. Status mapping is 400 malformed/invalid input; 401 missing/invalid bearer;
403 reserved for permission policy; 404 absent route/job; 409 idempotency conflict;
422 unsupported query/constraint; 429 bounded queue full; 500 internal; 502 dependency
failure; 503 dependency unavailable/not ready/open circuit; 504 dependency/workflow timeout.
Raw exception messages and stack traces never enter application errors or request logs.
HTTP parser failures occurring before a request reaches Cask remain the HTTP server's boundary.

`Idempotency-Key` is required for query POSTs. A deterministic opaque query ID is derived
from the key; only a hash-prefixed application reservation is sent to `QuerySessionStore`.
The store atomically reserves the ID/key, then a revision CAS binds a canonical-JSON body
fingerprint. Both `Written(session)` and `Retried(_, Written(session))` confirm creation by
this caller and use the same body-binding and scheduling path. Other retried outcomes reconcile
the authoritative session without starting work. Replays read the authoritative primary session, avoiding eventual-consistency
GSI assumptions. Same-body replays return a stored answer/error or job reference without
rerunning work; changed bodies return 409. Competing callers wait for the initial body binding
within the configured downstream timeout. Application sessions and runtime audit sessions use
separate namespaces. Query state, timestamps, stage, attempt count, trace IDs and bounded
terminal response are persisted in the session payload. `resultUrl` points to that stored result.

The synchronous wait and maximum workflow execution deadline are separate. Exceeding only
the synchronous wait returns 202 while the bounded local executor continues the same work.
Jobs progress through QUEUED, RUNNING, SUCCEEDED or FAILED. Retryable workflow failures
are retried at most `maxWorkflowRetries`; typed terminal outcomes replay without new work.
The real runtime adapter marks its failures nonretryable because Phase 9 already publishes
immutable terminal audits. Queue capacity, thread count, byte bounds and deadlines are enforced.

The real adapter retains verified core claim fields as additional public claim properties,
with course `claimId`, `text`, `evidenceIds`, `verificationStatus` and uncertainty fields.
Its `researchers` array is empty in 10A: the core answer does not supply authoritative display
names/complete row projections, so none are invented. An explicit `includeScores=true`
returns 422 until a supported score projection is supplied. `includeEvidence=false` and
`includeUncertainty=false` remove those fields from the public result; immutable audits remain
unchanged. True analysis inclusion flags require the relevant plan operation. False flags
permit the resolver to execute supporting operations and do not authorize invented claims.

## Authentication, observability and resilience

Every non-health route requires a bearer API key. `/internal/**` uses a distinct bearer
service token, even for currently unmatched routes; the external token cannot access them.
Only SHA-256 hashes are configured, compared with `MessageDigest.isEqual`. There are no
fallback credentials. Deploy-time Secrets Manager injection and TLS/ingress belong to later
infrastructure phases; the service never discovers or reads local credential files.
The shared course API key is one authorization domain; tenant-specific access is not claimed.

Request logs are JSON constructed from an allowlist of event, safe request/trace IDs,
route template, status and elapsed milliseconds. They never include request bodies, headers,
raw route IDs, bearer values or provider errors. Prometheus counters cover requests/statuses,
API timeouts, per-attempt downstream failures/timeouts, workflow verification and abstention.
Cumulative latency buckets (5 ms through 60 s and +Inf) are fixed instrumentation boundaries,
not execution limits; p50/p95/p99 are derivable with histogram queries. Registered dependency
breakers expose CLOSED/OPEN/HALF_OPEN gauge labels.

`DownstreamClient` uses an interruptible bounded pool, a timeout per attempt, bounded immediate
retries only for GET/HEAD transient failures and one circuit breaker per dependency. Other HTTP
methods attempt once. Open circuits refuse calls, then permit one half-open probe after reset;
a successful probe closes the circuit. Both HTTP correlation headers reach each attempt.
Adapters that ignore interruption can occupy their bounded executor slots; cancellation is
not claimed to forcibly terminate arbitrary provider code.

## Configuration

`ServiceConfig.fromEnvironment` reads the following entries. Defaults are small offline
foundation bounds, not measured production tuning. The API key and internal token hashes
are mandatory, distinct, lowercase 64-character SHA-256 strings. Hashes/keys are never logged.

| Environment suffix after `SCHOLARCHAIN_` | Default | Rationale |
| --- | --- | --- |
| `API_KEY_SHA256`, `INTERNAL_TOKEN_SHA256` | required | Separate external/internal authentication |
| `HTTP_HOST`, `HTTP_PORT` | `127.0.0.1`, `8080` | Local-only foundation listener; configure container bind explicitly |
| `SYNCHRONOUS_DEADLINE_MS` | 15000 | User-approved synchronous wait |
| `WORKFLOW_TIMEOUT_MS` | 60000 | Finite local asynchronous execution bound |
| `MAX_WORKFLOW_RETRIES` | 2 | User-approved bounded job retries |
| `WORKER_THREADS`, `QUEUE_CAPACITY` | 4, 64 | Bound active and queued local work |
| `MAX_REQUEST_BYTES`, `MAX_RESULT_BYTES` | 65536, 131072 | Bound JSON memory and inline session-result size |
| `MAX_QUESTION_CHARS` | 8192 | Bound user question |
| `MAX_GRAPH_LIMIT`, `MAX_VECTOR_LIMIT`, `MAX_PATH_DEPTH` | 100, 50, 6 | Match foundation runtime retrieval caps |
| `MAX_FILTER_ITEMS`, `MAX_FILTER_CHARS` | 100, 512 | Bound each filter list and string |
| `MAX_IDEMPOTENCY_KEY_CHARS` | 256 | Bound client key before hashing |
| `DOWNSTREAM_TIMEOUT_MS`, `DOWNSTREAM_MAX_ATTEMPTS` | 5000, 3 | Bound each downstream attempt and read retries |
| `BREAKER_FAILURE_THRESHOLD`, `BREAKER_RESET_MS` | 3, 30000 | Bound failures before opening and recovery interval |
| `SESSION_CAS_ATTEMPTS` | 8 | Bound optimistic session update retries |
| `SESSION_POLL_MS` | 50 | Bound local polling frequency; tune upward for remote stores |
| `REQUEST_READ_TIMEOUT_MS` | 5000 | Socket read inactivity bound, not an aggregate upload deadline |

OpenAPI gives default caps; changing configured public bounds requires publishing a matching
contract for the deployment. Year bounds 1–9999 are the versioned calendar schema, not corpus
coverage. All larger-work inputs must still match available configured corpus windows.

## Validation and remaining scope

Observed module validation: **16 tests passed** in two suites on Java 17 (`services / test`).
The independent owner reports wire/API and resilience validation separately; those counts and
full `sbt check` are retained by the coordinator in Phase 10 evidence.

10B owns evidence/explain/graph/semantic routes, graph proxy ingress through query-api,
embedding queue consumption/DLQ, the evidence-backed HTTP lifecycle and final contract/docs.
No OpenSearch, optional indexes, CI workflow, cloud deployment or paid provider call is added.

The local executor is not a durable distributed dispatcher. Completed outcomes survive a new
`QueryService` using the same injected store, but process termination can leave QUEUED/RUNNING
jobs pending. A crash between reservation and body binding leaves an unbound session; calls
fail 503 after bounded reconciliation instead of stealing it and risking a duplicate workflow.
The foundation does not automatically reset or recover these uncertain records. A permanent
store outage can also prevent terminal state persistence. Production recovery, remote-store
poll tuning and dispatcher/lease composition must be settled before live deployment.
The Phase 9 workflow uses its query ID as its internal audit trace; the adapter links that ID to
the HTTP request context, but a separate injected HTTP trace field inside every Phase 9 stage
is not part of the frozen runtime port. No live durability, throughput or cost claim is made.

# ScholarChain HTTP API reference

Route reference for the four service artifacts in `modules/services`. It was written from the source (`ApiApplication.scala`, `ApiContracts.scala`, `QueryService.scala`, `EvidenceApi.scala`, `GraphApi.scala`, `SemanticApi.scala`, `PublicSemanticRoute.scala`) and checked against the committed OpenAPI file and the route tests named at the end. The machine-readable contract is [scholarchain.v1.yaml](../modules/services/src/main/resources/openapi/scholarchain.v1.yaml); the module guide is [modules/services/README.md](../modules/services/README.md). The JSON examples under `modules/services/src/main/resources/openapi/examples/` are synthetic format examples, not answers about real researchers.

This file does not report any measured result. Latency, throughput and answer quality are in [docs/evaluation.md](evaluation.md) (written by the other Phase 17A package) and the frozen Phase 16 files it links.

## Service roles and where each route is served

One distribution builds four entry points. The role is chosen by the main class (`QueryApiMain`, `GraphServiceMain`, `SemanticServiceMain`, `EmbeddingWorkerMain`) and `SCHOLARCHAIN_SERVICE_MODE` is `unconfigured`, `offline-synthetic` or `aws` (`ServiceMains.scala`).

| Route | query-api | graph-service | semantic-service | Auth |
|---|---|---|---|---|
| `GET /healthz`, `GET /readyz` | yes | yes | yes | none |
| `GET /metrics` | yes | yes | yes | public API key |
| `POST /v1/query` | yes | no | no | public API key |
| `GET /v1/jobs/{jobId}`, `GET /v1/jobs/{jobId}/result` | yes | no | no | public API key |
| `GET /v1/evidence/{evidenceId}`, `GET /v1/queries/{queryId}/evidence`, `GET /v1/explain/{queryId}` | yes | no | no | public API key |
| `GET /v1/graph/nodes/{nodeId}`, `GET /v1/graph/nodes/{nodeId}/neighbors` | yes (proxy) | yes | no | public API key |
| `POST /v1/semantic/retrieve` | yes | no | no | public API key, rate limited |
| `GET /internal/v1/graph/nodes/{nodeId}` and `/neighbors` | no | yes | no | internal token |
| `GET /internal/v1/graph/metrics/{nodeId}` | no | yes | no | internal token |
| `GET /internal/v1/graph/paths` | no | yes | no | internal token |
| `GET /internal/v1/graph/communities/{communityId}/members` and `/cross-edges` | no | yes | no | internal token |
| `POST /internal/v1/semantic/retrieve` | yes | no | yes | internal token |

The embedding-worker serves `/healthz`, `/readyz` and `/metrics` only; its work is queue consumption. Source of the table: `routeExtended` and `handle` in `ApiApplication.scala`; the same layout is in the Route and dependency graph table of [modules/services/README.md](../modules/services/README.md).

## Common rules

- **Authentication.** `Authorization: Bearer <token>`. The service holds only the SHA-256 of each token (`SCHOLARCHAIN_API_KEY_SHA256`, `SCHOLARCHAIN_INTERNAL_TOKEN_SHA256`); the two must differ, and a public key is not accepted on `/internal/` paths nor the reverse. Paths starting `/internal/` use the internal token; every other path except `/healthz` and `/readyz` uses the public key. A missing or wrong token is `401 UNAUTHORIZED`.
- **Correlation headers.** `X-Request-Id` and `X-Trace-Id` are accepted if they match `[a-zA-Z0-9._:-]{1,128}`, otherwise generated. Both are returned on every response, with `Content-Type: application/json` and `Cache-Control: no-store` (`/metrics` is `text/plain; version=0.0.4`).
- **Query strings.** Parameters are decoded; a parameter without `=` or a repeated name is `400 INVALID_REQUEST`. A parameter not listed for a route is `400 INVALID_REQUEST`.
- **Bodies.** At most `SCHOLARCHAIN_MAX_REQUEST_BYTES` (default 65536) read with a 5000 ms read timeout (`requestReadTimeoutMs`); JSON nested deeper than 32 levels is refused before parsing (`RequestJson.MaxNestingDepth`).
- **Error body.** Every error is `{"error": CODE, "message": text, "traceId": id, "retryable": bool}`. Messages are fixed strings; they carry no provider text, stack trace, request body or internal URL.

### Typed errors

| HTTP | `error` | Retryable | When |
|---|---|---|---|
| 400 | `INVALID_REQUEST` | no | malformed JSON, wrong types, bad bounds, unknown parameter, nesting over 32, oversize body |
| 400 | `IDEMPOTENCY_KEY_REQUIRED` | no | `POST /v1/query` without a bounded `Idempotency-Key` |
| 401 | `UNAUTHORIZED` | no | missing or invalid bearer token |
| 404 | `NOT_FOUND` | no | unknown route, job, evidence id, audit record or graph node |
| 409 | `IDEMPOTENCY_CONFLICT` | no | same `Idempotency-Key` with a different body |
| 422 | `UNSUPPORTED_QUERY` | no | unknown field or section, unsupported ranking metric, cap above the configured maximum |
| 422 | `GRAPH_SCAN_CAP`, `GRAPH_NODE_CAP` | no | neighbor expansion exceeded 10000 scanned edges or 2000 visited nodes (defaults) |
| 422 | `COMMUNITY_UNSUPPORTED` | no | the loaded snapshot holds no community membership |
| 429 | `THROTTLED` | yes | the local workflow queue is full (terminal for that key) |
| 429 | `RATE_LIMITED` | yes | public semantic route rate limit; `Retry-After` header in seconds |
| 500 | `INTERNAL_ERROR` | no | closed internal error with trace id |
| 502 | `DOWNSTREAM_FAILURE` | yes | downstream dependency failed or answered a wrong shape |
| 502 | `RESULT_TOO_LARGE` | no | workflow result larger than `SCHOLARCHAIN_MAX_RESULT_BYTES` (default 131072) |
| 503 | `NOT_READY` | yes | `/readyz` while a dependency is unavailable |
| 503 | `MODEL_NOT_CONFIGURED` | no | local stack only (`LocalQueryStackMain`): no model provider key is configured, so the workflow cannot call a model (`LocalPortFactory.scala`); not returned by the deployed services |
| 503 | `SERVICE_UNAVAILABLE` | yes | session store unavailable or circuit open |
| 504 | `DOWNSTREAM_TIMEOUT` | yes | downstream or workflow timeout |
| 504 | `GRAPH_DEADLINE_EXCEEDED` | no | the graph request used up its execution deadline |

Source: `ApiError` in `ApiContracts.scala`, plus the codes constructed in `QueryService.scala`, `GraphApi.scala` and `PublicSemanticRoute.scala`. A workflow failure persisted for an idempotency key is stored as non-retryable, so replaying the same key returns the same terminal error; a new attempt needs a new key (`QueryService.fail`).

## Health and metrics

### `GET /healthz`

No auth. `200 {"status":"alive"}`.

### `GET /readyz`

No auth. `200 {"status":"ready"}` when the role's readiness check passes, else `503 NOT_READY`. In aws mode readiness is composed from dependency checks (`ReadinessGate.scala`); its semantics and the checks it does not make are in "Readiness semantics" of [modules/services/README.md](../modules/services/README.md).

### `GET /metrics`

Public API key. `200 text/plain` Prometheus text: `api_requests_total`, `api_status_total{status}`, `api_latency_seconds_*`, `api_timeouts_total`, `api_downstream_errors_total`, `downstream_timeouts_total`, `graph_request_deadlines_total`, `workflow_abstentions_total`, `api_rate_limited_total`, `api_route_requests_total{route,status}` (route labels come from a closed set), `workflow_verification_total{status}`, `downstream_circuit_state{dependency,state}`, and `embedding_cache_*` where a query-embedding cache exists. (`ApiApplication.scala`, `render`.)

## Query routes (query-api)

### `POST /v1/query`

Headers: `Authorization`, `Idempotency-Key` (required, non-empty, at most 256 characters, no control characters), optional `Content-Type: application/json`.

Request body, a JSON object with these keys only (others are `422 UNSUPPORTED_QUERY`):

| Key | Type and limits |
|---|---|
| `question` | string, required, non-blank, at most 8192 characters (`SCHOLARCHAIN_MAX_QUESTION_CHARS`) |
| `constraints` | object with `yearFrom`, `yearTo` (whole numbers, `yearFrom` not above `yearTo`), `topics`, `institutions`, `venues` (arrays of non-blank strings, at most 100 items of at most 512 characters) |
| `analysis` | object with `rankingMetric` (one of `DISTINCT_COAUTHOR_COUNT`, `PUBLICATION_COUNT`, `WEIGHTED_DEGREE`, `MAXIMUM_COAUTHORS_ON_ONE_PAPER`, `BRIDGE_SCORE`, `TOTAL_COAUTHOR_OCCURRENCES`, `AVERAGE_COAUTHORS_PER_PAPER`, `CORENESS`) and booleans `includeTeamSize`, `includeBridgeMetrics`, `includeCommunities`, `includePaths` |
| `retrieval` | object with whole numbers `graphLimit` (at most 100), `vectorLimit` (at most 50), `maxPathDepth` (at most 6); minimum 1 |
| `output` | object with booleans `includeEvidence`, `includeScores`, `includeUncertainty` |

Defaults and maxima are the `ServiceConfig` values in `ApiContracts.scala`; an environment override of those caps is read at start-up (`ServiceConfig.fromEnvironment`). Example (synthetic): [query-request.json](../modules/services/src/main/resources/openapi/examples/query-request.json).

Responses:

| Status | Body |
|---|---|
| 200 | `{"queryId", "mode":"synchronous", "answer", "claims":[...], "links":{"explain":"/v1/explain/{queryId}", "evidence":"/v1/queries/{queryId}/evidence", "result":"/v1/jobs/{jobId}/result"}}` when the workflow finished inside `SCHOLARCHAIN_SYNCHRONOUS_DEADLINE_MS` (default 15000) |
| 202 | `{"queryId", "mode":"asynchronous", "jobId", "status", "statusUrl":"/v1/jobs/{jobId}"}` when it did not; the work continues for at most `SCHOLARCHAIN_WORKFLOW_TIMEOUT_MS` (default 60000). Example: [job-reference.json](../modules/services/src/main/resources/openapi/examples/job-reference.json) |
| error | 400, 401, 409, 422, 429, 502, 503, 504 as in the table above |

`queryId` is `qry-` plus the SHA-256 of the idempotency key; `jobId` is `job-` plus the same hash (`QueryService.scala`). The same key and body returns the stored answer, terminal error or current job reference without a second workflow run; a different body under the same key is `409 IDEMPOTENCY_CONFLICT`. A retryable downstream status (502, 503, 504) is retried inside the workflow up to `SCHOLARCHAIN_MAX_WORKFLOW_RETRIES` (default 2). The `answer` and `claims` are produced by the runtime workflow (planner, retrieval, synthesis, deterministic claim verification, audit); the route does not compute them. Verified, partial, rejected and abstained outcomes all return HTTP 200 and are told apart by the answer and by `/v1/explain`.

### `GET /v1/jobs/{jobId}`

`200 {"jobId", "queryId", "state", "stage", "createdAt", "updatedAt", "resultUrl", "error"}`. `state` is `QUEUED`, `RUNNING`, `SUCCEEDED` or `FAILED`; `stage` is `QUEUED`, `WORKFLOW`, `PLANNING`, `RETRIEVAL`, `SYNTHESIS`, `CLAIM_VERIFICATION`, `AUDIT`, `COMPLETE` or `FAILED`. `resultUrl` is set only when `SUCCEEDED`; `error` is the typed error body only when `FAILED`, otherwise `null`. Errors: `404 NOT_FOUND` (unknown job id), `503 SERVICE_UNAVAILABLE`.

### `GET /v1/jobs/{jobId}/result`

`200` with the stored synchronous-style result when `SUCCEEDED`; `202` with the job reference while `QUEUED` or `RUNNING`; the stored typed error when `FAILED`; `404` for an unknown job.

### `GET /v1/evidence/{evidenceId}`

`200` with the persisted evidence item: `evidenceId`, `evidenceType`, `workId`, `sourceDataset`, `sourceRecordId`, `snapshot`, `sourceUri`, `text`, `textS3Uri`, `graphPath`, `chunkId`, `score`, `provenance`, `supportingContent` (`EvidenceApi.scala`). `404 NOT_FOUND` for an unknown id; `502` if the store answers a wrong shape. Evidence ids have the forms `evidence:graph-path:`, `evidence:edge:`, `evidence:metric:`, `profile:` and `chunk:` (see [docs/data-lineage.md](data-lineage.md)).

### `GET /v1/queries/{queryId}/evidence`

`200 {"queryId", "evidenceIds":[...]}` from the immutable audit record; `404` when no audit exists for that query.

### `GET /v1/explain/{queryId}`

`200` with the observable audit projection: `queryId`, `traceId`, `queryPlan`, `stagesExecuted`, `stageFailures`, `promptVersions`, `modelVersions`, `evidenceIds`, `scoreComponents`, `counters` (`latencyMillis`, `attemptedClaims`, `verifiedClaims`, `rejectedClaims`; `retries` and `cacheHits` are `null`, not measured), `verificationStatus`, `verification` (per-claim verdicts), `outcome`, `reason`, `metricVersions`, `graphRunIds`. It never returns hidden prompts, model reasoning or attempted model prose. `404` for an unknown query id.

## Graph routes

The public `GET /v1/graph/...` routes on query-api and graph-service and the internal `GET /internal/v1/graph/...` routes on graph-service share one implementation (`GraphApi.scala`). All accept an optional `timeoutMs` (1 up to the configured `SCHOLARCHAIN_GRAPH_TIMEOUT_MS`, default 5000). The default window is `all-years`. Windows in the exported graph are `all-years`, `through-2009`, `2010-2014`, `2015-2019`, `2020-2026` and `since-2015` ([modules/spark/README.md](../modules/spark/README.md)).

| Route | Parameters | Response |
|---|---|---|
| `GET .../graph/nodes/{nodeId}` | `timeoutMs` | `200 {"nodeId", "snapshot", "node"}`; `404` unknown node |
| `GET .../graph/nodes/{nodeId}/neighbors` | `direction` (`in`, `out`, `both`; default `both`), `depth` (1 to 3, default 1), `limit` (1 to 200, default 50), `edgeTypes` (comma list of `COAUTHORED_WITH`, `AUTHORED`, `HAS_TOPIC`, `AFFILIATED_WITH`, `PUBLISHED_IN`), `window`, `cursor`, `timeoutMs` | `200 {"nodeId", "snapshot", "direction", "depth", "items":[{nodeId, edgeId, edgeType, depth, fromId, toId, provenance, evidence?}], "cursor"}`; `cursor` is `null` on the last page; it is signed and bound to the other parameters, so a tampered cursor or one from a different query is `400` |
| `GET /internal/v1/graph/metrics/{nodeId}` | `window` (default `all-years`), `timeoutMs` | `200 {"researcherId", "window", "record", "qualifications", "metricVersion", "runId"}` |
| `GET /internal/v1/graph/paths` | `from`, `to` (node ids), `maxDepth` (default and maximum 6; a larger value is clamped, not refused), `window`, `timeoutMs` | `200 {"snapshot", "paths":[{"nodeIds","edgeIds"}] or [], "maxDepth", "clamped", "truncated", "truncationReason"}`; only `COAUTHORED_WITH` edges are walked; when the scan or node cap is hit first the reply is `200` with no path and `truncated: true`, so an empty result is not proof that no path exists |
| `GET /internal/v1/graph/communities/{communityId}/members` | `window`, `limit`, `timeoutMs` | `200 {"snapshot", "communityId", "window", "members":[...]}`; `422 COMMUNITY_UNSUPPORTED` if the snapshot has no membership |
| `GET /internal/v1/graph/communities/{communityId}/cross-edges` | `window`, `limit`, `timeoutMs` | `200 {"snapshot", "communityId", "window", "items":[{nodeId, edgeId, edgeType, properties}], "truncated"}` |

Defaults and caps: `SCHOLARCHAIN_GRAPH_*` variables read in `BootstrapConfig.graph` (`ServiceMains.scala`). Errors: `400`, `404`, `422 GRAPH_SCAN_CAP` / `GRAPH_NODE_CAP`, `504 DOWNSTREAM_TIMEOUT` or `GRAPH_DEADLINE_EXCEEDED`. Example page: [graph-page.json](../modules/services/src/main/resources/openapi/examples/graph-page.json). Coauthor items carry an `evidence` object (`evidenceTable`, `evidenceEdgeId`, `windowId`, `representativeWorkIds`) and `provenance: null`; clients read `evidence` for them (see "Limits and what is not verified live" in the services README).

## Semantic retrieval routes

### `POST /v1/semantic/retrieve` (public, query-api)

Public API key. A per-key token bucket runs before any validation (defaults 50 requests per second, burst 100, at most 1024 buckets per process; `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND`, `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST`); a refused request is `429 RATE_LIMITED` with `Retry-After`. No query-string parameters are allowed.

Body keys: `question` (required, non-blank, at most 1000 code points), `topK` (whole number 1 to 20, default 20), `filters` (object of string values, at most 16 entries, each value at most 1000 code points); the body is at most 8192 UTF-8 bytes. Anything else is `400 INVALID_REQUEST`. Example: [semantic-request.json](../modules/services/src/main/resources/openapi/examples/semantic-request.json).

Response `200 {"hits":[{"key","distance","metadata":{string: string}}], "model":{modelId, version, dimension}}`, at most `topK` hits in downstream order. A downstream body of another shape is `502 DOWNSTREAM_FAILURE`; nothing is forwarded unprojected. The question is not logged and is not used as a metric label. The route returns backend records only; it does not synthesize hits, scores or evidence.

### `POST /internal/v1/semantic/retrieve` (internal)

Internal token. Same body keys, with `topK` up to 50 (default 50), question up to 8192 characters and a body of up to 65536 bytes. Served by semantic-service, and by query-api where it forwards to the configured semantic service. Response shape as above.

## Tests that exercise these routes

Run state: these suites exist in the repository. They were not run in package 17A-1; the final test run is a separate Phase 17 gate.

- `modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/`: `ServiceFoundationSpec`, `PublicSemanticRouteSpec`, `GraphPathsAndCommunitiesSpec`, `RequestNestingSpec`, `GraphRequestDeadlineSpec`, `RetriedSessionCreationSpec`, `SessionBindingRecoverySpec`, `ReadinessGateSpec`.
- `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/`: `IndependentServices10ASpec` (auth separation, malformed JSON, idempotent replay, log redaction, typed error mapping), `AdversarialRuntimeHttpSpec` (HTTP injection, replay, credential canaries); the test names are listed in the Phase 11 test report ([docs/agent-runs/phase-11/test-report.md](agent-runs/phase-11/test-report.md)).
- Deployed-environment checks used in Session 2: `healthz` and `readyz` returned 200 and the manual checks returned 401 for a missing or invalid key and 404 for an unknown evidence id ([rb-runtime evidence](agent-runs/phase-15/evidence/session-2/rb-runtime/manual-401.log), [evidence 404](agent-runs/phase-15/evidence/session-2/rb-runtime/p14-7-evidence-404.log)). The full six-check smoke test was not run in Session 2: it ran 2 of 6 checks by design ([smoke-14b.log](agent-runs/phase-15/evidence/session-2/rb-runtime/smoke-14b.log)).

## Replay

Read-only commands replayed in package 17A-1 (Sunday 2026-11-22, no network, no build):

```bash
grep -n -E 'case \("(GET|POST)"' modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiApplication.scala
grep -n '^  /' modules/services/src/main/resources/openapi/scholarchain.v1.yaml
```

The first printed 12 extended-route `case` lines (evidence, explain, query evidence, two public graph routes, six internal graph routes, one internal semantic route). The second printed 19 path entries of the OpenAPI file (the 12 above plus `/healthz`, `/readyz`, `/metrics`, `/v1/query`, `/v1/jobs/{jobId}`, `/v1/jobs/{jobId}/result` and `/v1/semantic/retrieve`; `/v1/query`, the two job routes, the health, metrics and public semantic routes are matched in `handle` rather than `routeExtended`). Running the services (`scripts/smoke-local.sh`) was not replayed in 17A (replay in 17G).

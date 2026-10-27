# Subphase 10A acceptance and boundary

| Requirement | Assigned owner | Required observation |
|---|---|---|
| HTTP library, dependency cleanup, runtime packaging | build-engineer | Scala 3.3.4 compile; services runtime classpath; four main classes; local image build if daemon runs |
| Server/config/auth/IDs/errors/log redaction | service-engineer | Module feature tests plus independent HTTP tests |
| Query/jobs sync, async, persisted result | service-engineer | Fake workflow 200/202; job timestamps/stage/result/error |
| Conditional idempotency | service-engineer | Same body executes once; different body409; concurrent and new-instance replay tests |
| Timeout/read-only retry/breaker | service-engineer | 504/502 mappings; bounded retries; closed/open/half-open tests |
| Health/readiness/metrics | service-engineer | Open health probes; dependency failure readiness; authenticated metrics |
| Initial OpenAPI | service-engineer | 10A routes/request/response/error/ID/auth consistency |
| Independent 10A HTTP tests | test-engineer | Hand-authored fixtures and literal expected outcomes |
| Repository deterministic gate | root runs, owners repair within territory | Fresh sbt check on JDK17, exact logs/counts/exit |
| Handoff | root | Reports, file inventory, reviewer prompt, all jobs stopped |

## Deferred to 10B by the work order

Evidence fetch and explain routes; graph and semantic service routes and thin proxy clients; embedding-worker queue consumption/DLQ handling; query-to-evidence lifecycle test; complete OpenAPI/README contract and final four-artifact behavior. Foundation main classes and packaging may exist in10A, but no10B behavior is prepared or implemented.

## Omitted lean-scope optional components

No Cognito, optional OpenSearch, additional indexes/services, CI workflows, cloud resource mutations, deployment, image push or paid-model execution. These omissions follow the approved defaults and plan scope.

## Decision records

The user owns human-gate.md, commit.txt and acceptance/approval records. This implementation session does not create or rewrite them. No reviewer is invoked.

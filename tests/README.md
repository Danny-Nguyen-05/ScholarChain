# Independent tests (`tests/**`)

Owned by the test-engineer. The sbt project `independentTests` (`tests/src/test/scala/.../independent/`)
holds cross-module, contract, adversarial and end-to-end suites; it runs inside `sbt check`. The
Terraform source checks are described in [`infra/README.md`](infra/README.md).

Run one suite on JDK 17 from the repository root:

```bash
sbt -batch "independentTests/testOnly edu.uic.cs441.scholarchain.independent.<Suite>"
```

## Suites

| Suite | What it checks |
| --- | --- |
| `AdversarialPublicSemanticHttpSpec` (fixture `AdversarialPublicSemanticFixture`), P40-T | Black-box test of the public `POST /v1/semantic/retrieve` route against its published contract (`modules/services/README.md` "Public semantic retrieval" and the OpenAPI path). It starts real offline-synthetic services through `ServiceBootstrap.launch` over HTTP on loopback, with an AWS port factory that refuses and counts every call, and a local stub for semantic-service failures. Covered: authentication (the API key only, not the internal token; the key never opens the internal route); exact public limits (topK 1..20, 1,000 code points, 8,192 bytes, 16 filters, unknown fields, query strings, chunked and oversize bodies, deeply nested JSON); the per-key token bucket set through `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` / `_BURST` (exact admissions, typed retryable 429 with `Retry-After`, sequential and concurrent, other routes not limited, `api_rate_limited_total`); a reply projected to `{hits, model}`; typed downstream 503/504/429/502 errors; the question sentinel absent from captured logs (application loggers at all levels, others at the shipped INFO root), replies and `/metrics`; and the query-embedding cache (N distinct questions repeated M times give N misses, LRU eviction, and a two-process query-api to semantic-service topology). No AWS, Anthropic or Voyage call; all credentials are synthetic placeholders. |

# 14C templates and disclosures (from rag-engineer, 2026-11-08)

> **Superseded in part (coordinator note, 2026-11-10; user decision "accepts all by default", `prompt.md` pre-session items, extra A and item 8).** The text below is kept unchanged as the 2026-11-08 record; it was written for Titan. Use these replacements, taken from the rag-engineer's pre-session item 8 report (2026-11-10, read-only checks of the code and Terraform; nothing live):
>
> - `tables.idempotencyIndex` is the GSI **name**, not a table name: `"idempotencyIndex": "by-idempotency-key"` (default of `query_session_gsi_name`, `infra/terraform/variables.tf:156-160`; use the overridden value if that variable is ever set). The rag config now refuses a blank, malformed or table-equal value (`LiveEmbeddingIngestMain.scala`, `LiveEmbeddingIdempotencyIndexSpec`).
> - `tables`: `{"runLedger": "<table_names.RunLedger>", "entityLinks": "<table_names.EntityLinkCache>", "querySessions": "<table_names.QuerySession>", "evidence": "<table_names.EvidenceBundle>", "artifacts": "<table_names.ArtifactRegistry>", "metrics": "<table_names.ResearcherMetricCache>", "idempotencyIndex": "by-idempotency-key"}` (the `<prefix>-...` placeholders below do not match the Terraform names).
> - `model`: `{"modelId": "voyage-4-lite", "version": "voyage-4-lite", "dimension": 256}`; for a Bedrock run only, `amazon.titan-embed-text-v2:0` for both `modelId` and `version`, dimension 256.
> - Add `"embeddingProvider": "voyage"` (or `"bedrock"` for a Bedrock run) and `"embeddingCapUsd": 0.30` to `live-config.json`, also in the smoke config; a provider/model mismatch is refused (`embedding-provider-model-mismatch`).
> - `textBucket` = the `bucket_names.rag` output (prefix `embedding-text`; derived from Terraform, unverified live).
> - The "Titan split" bullet is replaced by: Voyage `voyage-4-lite` at USD 0.02 per 1M tokens; one embedding cap of USD 0.30 shared by ingest (0.25) and query smoke (0.05) through the token counter; the free 200M tokens are still counted; query vectors use the `query` input type with the same model, version tag and dimension 256, and a mismatch is refused.
> - The Voyage key is read only from env `SCHOLARCHAIN_VOYAGE_API_KEY` when the provider is `voyage`; it is never a config field. Approval JSON fields are unchanged.

The coordinator assembled this from the rag-engineer report. The templates hold placeholders only, and every `true` approval flag is set by the human; shipped templates carry `false`.

## Ingest live config (`live-config.json`)

```json
{
  "schemaVersion": "scholarchain.embedding-live.v1",
  "environment": "<environment-from-terraform>",
  "region": "us-east-2",
  "profile": "<approved-local-profile>",
  "model": {"modelId": "amazon.titan-embed-text-v2:0", "version": "amazon.titan-embed-text-v2:0", "dimension": 256},
  "textBucket": "<text-bucket-from-terraform-output>",
  "textPrefix": "embedding-text",
  "vectorBucket": "<vector-bucket-from-terraform-output>",
  "tables": {
    "runLedger": "<prefix>-runledger", "entityLinks": "<prefix>-entitylinks", "querySessions": "<prefix>-querysessions",
    "evidence": "<prefix>-evidence", "artifacts": "<prefix>-artifacts", "metrics": "<prefix>-metrics",
    "idempotencyIndex": "<prefix>-idempotencyindex"
  },
  "metric": "cosine",
  "maxVectors": 10000,
  "maxConcurrentCalls": 2,
  "maxEmbeddingAttempts": 2,
  "maxEmbeddingCalls": 20000,
  "dollarCapUsd": 0.25,
  "assumedMaxDollarsPerEmbeddingAttempt": 0.00001,
  "assumedMaxStorageDollarsPerVector": 0.000001,
  "fixedOverheadUsd": 0.02,
  "assumedUsdPerMillionEmbeddingTokens": 0.02,
  "minBytesPerEmbeddingToken": 1,
  "requestTimeoutMillis": 30000,
  "maxManifestBytes": 16777216,
  "batchSize": 100,
  "indexNames": {
    "researcher-profile": "researcher-profile-v1", "community": "collaboration-community-v1",
    "paper": "paper-abstract-v1", "collaboration-path": "collaboration-path-v1",
    "topic-institution-summary": "topic-institution-summary-v1"
  },
  "nonFilterableKeys": ["textS3Uri"]
}
```

- **Placeholders:** table and bucket names come from the real Terraform outputs; use `<acct>` wherever a real name contains the account ID.
- **Sizing at USD 0.25:**
  - Embedding: 10,000 × 2 × 1e-5 = 0.20.
  - Plus 0.01 storage and 0.02 overhead: 0.23 in total, within the cap.
- **The token bound passes** only if the average text is at most about 500 UTF-8 bytes (at 1 byte per token, 2 attempts, 10k vectors). Otherwise, lower `maxEmbeddingAttempts` or set a human-validated `minBytesPerEmbeddingToken` of 2 to 4.
- **Titan split:** USD 0.25 for the ingest and 0.05 for the query smoke. Query-time embeddings for 15B and 16B need headroom from the remaining Titan allowance, which is the user's decision.

## Ingest approval (`ingest-approval.json`)

```json
{
  "schemaVersion": "scholarchain.embedding-live-approval.v1",
  "executionApproved": false,
  "environment": "<environment-from-terraform>",
  "runId": "<run-prefix>-ingest",
  "configSha256": "<sha256 of live-config.json bytes>",
  "manifestSha256": "<sha256 of real-model-manifest.json bytes>",
  "phase14GateReference": "<absolute path>/docs/agent-runs/phase-14/approval-14c.md",
  "phase14GateSha256": "<sha256 of approval-14c.md bytes>",
  "vectorCap": 10000, "concurrencyCap": 2, "embeddingCallCap": 20000, "dollarCapUsd": 0.25,
  "pricingValidated": false, "budgetValidated": false,
  "expiresAtEpochSeconds": 0,
  "operation": "ingest",
  "queryRequestCap": 0, "queryEmbeddingCallCap": 0, "queryObjectReadCap": 0
}
```

## Query-smoke config (`smoke-config.json`)

The `live` block equals `live-config.json` except for these values:

| Field | Value |
|---|---|
| `maxConcurrentCalls` | 1 |
| `maxEmbeddingCalls` | 10 |
| `dollarCapUsd` | 0.05 |
| `assumedMaxDollarsPerEmbeddingAttempt` | 0.0002 |

The rest of the smoke config:

| Field | Value |
|---|---|
| `schemaVersion` | `scholarchain.embedding-live-smoke.v1` |
| `queries` | the five 8b queries (one per index, topK 1, real `expectedVectorKeys`) |
| `samplesPerQuery` | 1 |
| `maxQueryRequests` | 5 |
| `maxQueryEmbeddingCalls` | 10 |
| `maxTopK` | 5 |
| `maxObjectReads` | 5 |
| `assumedMaxDollarsPerQuery` | 0.0001 |
| `assumedMaxDollarsPerObjectRead` | 0.0001 |
| `dollarCapUsd` | 0.05 |
| `maxObjectBytes` | 1048576 |

Estimate: 10 × 0.0002 + 5 × 0.0001 + 5 × 0.0001 + 0.02 = 0.023, within 0.05. The query smoke makes no LLM call.

## Query-smoke approval (`smoke-approval.json`)

It matches the ingest approval except for these fields (finding N15: the smoke no longer needs ingest-sized caps):

| Field | Value |
|---|---|
| `runId` | `<run-prefix>-query-smoke` |
| `configSha256` | sha256 of `smoke-config.json` |
| `operation` | `query-smoke` |
| `vectorCap`, `concurrencyCap`, `embeddingCallCap` | 0 |
| `dollarCapUsd` | 0.05 |
| `queryRequestCap` | 5 |
| `queryEmbeddingCallCap` | 10 |
| `queryObjectReadCap` | 5 |

## Rules

- `approval-14c.md` must exist and stay unchanged after it is hashed. The mains read at most 65,536 bytes of it and compare its sha256.
- Following the deploy-engineer runbook draft, it is written and committed before the commit freeze, with caps and wording only.

## Disclosure for `approval-14c.md` (finding N11, the user includes it)

> "The researcher-profile, community, paper and collaboration-path vectors carry no `sourceDataset` metadata and no `sourceDataset` filter, because a mixed-export summary can reference several source datasets and none is guessed (finding N11, accepted in Phase 8); only topic-institution-summary node vectors carry `sourceDataset`. Source provenance for the other four types is in `sourceReferences` and the ordinary-S3 text object, so the course's compact 'source dataset' metadata field is not available as a vector filter for them."

## Phase 8 findings status

| Finding | Status | Owner and evidence |
|---|---|---|
| R3 | Fixed | storage-engineer: metadata budget checked before any embedding call; `EmbeddingMetadataBudgetSpec`, 5 tests |
| N15 | Fixed | rag-engineer: the query smoke has its own small caps; `LiveEmbeddingCapsSpec` |
| N11 | Disclosure only | The disclosure above |

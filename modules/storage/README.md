# Storage ports and Phase 7A adapters

Storage depends on core, the pinned AWS Java SDK v2, and Parquet/Hadoop readers; it never depends on Spark or service routes. `StoragePorts.scala` defines ten ports. `storage.fakes` exposes usable main-source fakes to downstream modules. Real graph loading/reading, S3 Vectors and the dry-run CLI are implemented in 7B as described below; the opt-in live suite belongs to 7C. No AWS resources, deployment, or live calls are performed in 7A.

## Configuration and table access

Construct `StorageConfig` and inject already configured SDK clients. Callers own client endpoint, region, credentials provider, connection and API timeouts; adapters never build clients or select environment resources. All bucket/table/index names are supplied. Terraform owns resource creation, on-demand capacity and TTL enablement. Distinct table names are required. `scholarchain.storage.v1` envelopes store typed records in a `payload` String; unsupported versions and malformed payloads return typed rejections. Hashes are lowercase SHA-256 hex.

| Table | Partition key attribute | Sort key attribute | Access pattern and conditions |
|---|---|---|---|
| RunLedger | `runId` | `stageKey` | `RUN` root plus `STAGE#<stage>` rows; consistent partition query. Start conditional absent; stage transitions atomically CAS root revision and stage payload, with immutable FAILURE rows retaining each reason/retry. No TTL. |
| EntityLinkCache | `entityType#normalizedKey` | `policyVersion#sourceId` | Exact name or external ID partition query; values length-frame the constituent strings. Names use core `TextNorm.personName`; observed external IDs remain distinct. Conditional absent immutable rows. No TTL. |
| QuerySession | `queryId` | `itemType` | `SESSION` lookup plus `RESERVATION` at `IDEMPOTENCY#<sha256(raw-key)>`. Create reserves both atomically. Configured GSI partition key `idempotencyKey`, projection ALL, provides eventual lookup; creation correctness uses the strong reservation row. |
| EvidenceBundle | `evidenceId` | `part` | `BUNDLE` inline JSON or hashed S3 pointer, consistent point lookup. Conditional absent. No TTL. |
| ArtifactRegistry | `artifactId` | `version` | Consistent exact get and descending lexical version query. Use sortable version tags. Conditional absent rejects changed text hash/URI. No TTL. |
| ResearcherMetricCache | `researcherId` | `windowId` | Exact immutable metric with metric version, source run, full payload and qualifications; consistent point/batch reads. No TTL. |

All absent conditions use `attribute_not_exists(#pk) AND attribute_not_exists(#sk)`. CAS compares the entire prior envelope via `#payload = :expected`. Exact repeated immutable content reports `Unchanged`; conflicting content reports `Rejected`. Query IDs cannot use the reserved `IDEMPOTENCY#` prefix. Reusing an idempotency key for a different query ID rejects; same query returns its current session. Updates require expected revision and preserve idempotency and expiration. Optional `disposableSessionTtlSeconds` sets numeric epoch-second `expiresAt` on the two disposable session rows only; default is no TTL. Expired rows may remain visible until DynamoDB removes them; TTL is eventual cleanup, not an immediate expiration guarantee.

Run state starts running. `recordStage` starts a stage or resumes a failed stage, `recordFailure` must advance retryCount by one and uses a bounded reason-code alphabet, and `completeStage` transitions running to complete. `completeRun` requires every existing stage complete and CASes the root revision, so a concurrent stage transition cannot be silently ignored. Terminal runs reject further stages/failures. Stages themselves do not automatically claim that work succeeded.

## Object and evidence integrity

Object keys must include `/versions/`; `StorageKeys.versioned` constructs those keys. `S3ObjectStore` uses `If-None-Match: *` and stores `sha256` metadata, validates metadata on HEAD, and verifies actual bounded streamed bytes and HEAD/GET agreement on read. HEAD cannot itself independently recompute a body hash. Existing keys are read and compared; changed bytes or metadata reject. The default 16 MiB object bound is an application memory cap, not the S3 maximum. `RunObjectPublisher` stops at the first failed upload and writes the manifest last; unchanged reloads issue no successful new object writes. Large evidence bundles exceed the default 256 KiB inline threshold and upload first under a content-versioned evidence key; the Dynamo row then records the hash/pointer. A rejected pointer write can leave an immutable orphan S3 object; cleanup requires the later human-approved lifecycle policy, not deletion in the adapter.

## Phase 6 cache loading

`LocalParquetManifestReader` reads completed local export roots through `ParquetReader[Group]` and validates the completion marker, run identity, manifest paths, table count/hash inventory and Hadoop/ER lineage binding. It restores the partition `window` column and removes physical `run_id`. It has no Spark session or provider calls. A caller supplies Phase 6 manifests, normally the S3 all-datasets manifest, because the historical DynamoDB proposal excludes researcher nodes. A caller can inject another `ManifestRowReader` for test fixtures.

`Phase6CacheLoader` stages relevant rows on temporary disk, verifies row counts and the exact Phase 6 `sha256-fixed-256-shard-sorted-row-json-merkle-v1` hash, and validates duplicate metric copies before cache writes. Each fixed SHA-prefix shard uses bounded chunk sorting and merge fan-in 64. Canonical hash JSON preserves Spark Double formatting (including integral `.0`) for the selected double fields. Memory holds one row, configured sort chunk (default 1,000 rows), bounded merge heads and scalar metadata rather than the dataset. Scratch disk grows with the selected tables and must be provisioned accordingly. Files are cleaned after success or failure. Metadata files are capped at 4 MiB, row JSON at 1 MiB, and per-researcher affiliations at 100 by default; these are configurable application bounds. Parquet INT64 values outside the exact JSON integer range +/-9,007,199,254,740,991 reject rather than silently round. Unsupported Parquet primitives reject.

Researcher labels and observed ORCIDs populate the cache without changing Spark IDs. Applied `RESOLVES_TO` edges connect exported AuthorMention aliases to canonical researchers. These edges represent the constrained Phase 6 use of Phase 5 links; raw Phase 5 accepted pairs are not an exported Phase 6 table and are never automatically treated as canonical identity. Missing endpoints reject. `AFFILIATED_WITH` rows retain observed institution IDs; absent affiliations remain empty, and absent confidence stays `None`. Cache entries retain source IDs, run IDs and evidence pointers; no identity confidence is invented.

`researcher_collaboration` and `kcore` duplicate copies must agree after decoding the core record. One canonical record is stored per `(researcherId, windowId)`; conflicting copies reject before any cache writes. Metric payloads retain the exact core values and policy/run. Qualifications retain a retrievable immutable source-run pointer plus actual `CommunityMembership` (including `converged`, iterations), and component/window `PathLengthEstimate` when exported. Missing membership is explicitly unknown. Approximate P90 applies to the preserved estimate record, not exact collaboration counts. Source run metadata, counters and original uncertainty notes are preserved. A store rejection after writes can leave a partial cache load; rerunning unchanged input fills remaining rows idempotently, with no claim of cross-table atomicity.

Coauthor support pointers use a length-framed composite `(edgeId, workId)`; neither Spark ID changes. Yearless collaboration years remain absent in core contracts and the separately owned Neptune CSV sidecar. No synthetic dates or IDs are introduced.

## Bounds, retries and sources

Checked 2026-10-22 against primary documentation:

- [DynamoDB constraints](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html): 400 KiB items, partition-key maximum 2,048 bytes and sort-key maximum 1,024 bytes. The default 380 KiB application cap reserves envelope/key overhead. All writes validate encoded size before SDK submission.
- [BatchGetItem](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_BatchGetItem.html): at most 100 keys and 16 MiB response. Configured batch size cannot exceed 100; duplicate keys deduplicate. Unprocessed keys retry with bounded full-jitter exponential backoff; exhausted keys return a typed rejection rather than a partial-success claim.
- [TransactWriteItems](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html): at most 100 actions, 4 MiB aggregate, atomic conditions. Current session operations use two actions; ledger failures use three (root, stage, immutable failure). The per-row application cap keeps these aggregates below this limit.
- [Condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html) define absent/CAS semantics. No BatchWriteItem path is used because it cannot supply per-item conditions.
- [DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html): numeric epoch seconds and deletion typically within a few days; only optional disposable sessions use it.
- [S3 PutObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html): `If-None-Match: *`, 412 existing-object conflict and 409 retryable conflict. [Object metadata](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingMetadata.html) limits user metadata to 2 KiB; the application reserves 70 bytes for SHA metadata.
- [Parquet logical types](https://parquet.apache.org/docs/file-format/types/logicaltypes/) define LIST/string mappings used by the producer-compatible Group reader.
- [Course Phase 7](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading) supplies the required storage scope. [Neptune bulk-load formats](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format.html) lists CSV/RDF inputs; Parquet is not a bulk-loader input. The Spark owner produces the additive `neptune-opencypher-csv` sidecar in 7A. The 7B loader below consumes the validated sidecar.

Default retry policy is at most three SDK attempts, 10 ms base delay and 1,000 ms cap with full jitter. Retryable service statuses are 409, 429 and 5xx; SDK transport errors also receive bounded retries. Expected conditional conflicts have dedicated typed handling. Permanent service errors return sanitized reason codes without provider exception messages. Dynamo partition queries use configured page size 100 and at most 100 pages; exceeding the bound returns a typed rejection, never silent truncation. The SDK clients' own retry/timeout policy must be chosen by runtime composition to bound total attempts/time; this module never configures a live client.

## Verification and remaining gates

Normal tests use main fakes, hand-derived synthetic fixtures and stubbed SDK interfaces; Docker is unnecessary. The build owner provides guarded `storage / AwsIntegration / test`, requiring `SCHOLARCHAIN_AWS_ITEST=1` plus explicit profile; no live suite is authored or run in 7A. 7C supplies the compiled live-suite cases, exact environment and cleanup/cost plan; Phase 14C remains the human live execution gate. The 7B sections below document the implemented Neptune/S3 Vectors limits, allowlisted queries, vector metadata validation, batching and rejection reports. Optional OpenSearch and extra indexes/services are omitted. No deployment or cleanup commands are run here.

## Phase 7B adapters and composition

`NeptuneExportValidator` accepts a completed local export root (or its sidecar path), reads the existing S3 manifests, and verifies completion/lineage bindings, source table inventories, all selected Parquet logical hashes, all three CSV logical hashes, byte-preserving RFC4180 parsing, complete ID/projection parity, node endpoints and distinct supporting works. Counts use the producer's exact decimal-string Long encoding. CSV integer types come from headers; absent years remain null, and quoted empty strings retain their distinction from null cells. Re-signing a changed CSV sidecar cannot authorize a row which differs from the verified source projection. Validation finishes before uploads or loader submission. File real paths must remain within the export root.

The validator adds only source-grounded properties to the existing node projection: `communityMembershipKeys`, `communityWindowKeys` and `communityQualificationsJson`. Each membership/window lookup token is a delimiter-framed SHA-256 of its exact source key; these are lookup properties, not new entity IDs. The full exported membership JSON retains `converged`, iterations, source run and lineage. Absent membership has no token. This supports community queries without assuming nonexistent node properties or unsupported dynamic property access. Enriched CSV parts are capped at 8 MiB by default with a header in every part. Source files still obey configured upload/object caps; oversized individual source parts reject and require an explicitly increased bound or producer repartitioning. Scratch disk holds bounded-sort intermediates and the enriched projection; no graph-sized driver collection is used. CSV cells are capped at the configured character bound, with at most 32 columns per record.

`NeptuneGraphLoader` uploads the validated CSV and ordinary support Parquet under a fingerprint-versioned export prefix. Support remains outside the CSV loader prefix. It publishes the storage load manifest last, submits `format=opencypher`, `userProvidedEdgeIds=true`, `failOnError=true`, `mode=AUTO` and configured region/IAM role, then polls within configured request, time and poll-count bounds. An append-only job registry records attempt versions separately for each run/fingerprint; a completed fingerprint returns `Unchanged` without new uploads/submission. The run ledger retains stage/retry/failure evidence. Initial submission uses AUTO for same-source resume behavior. After a recorded final failure the next invocation appends exactly one new attempt and requests NEW mode, preserving every prior job and failure marker; it never polls the failed ID again. A local timeout leaves the provider job active, so rerunning polls that same ID without submitting. Legacy single-fingerprint job rows are adopted and retained; terminal legacy jobs receive an append-only failure marker before recovery. Only LOAD_NOT_STARTED, LOAD_IN_QUEUE and LOAD_IN_PROGRESS are pending; LOAD_COMPLETED is success. Every other status, including write conflicts, deadlock and unknown states, terminates immediately and records a sanitized status-specific failure code in the ledger. No registry row is deleted. These records are not a cross-service transaction. A timeout or provider failure cannot undo data Neptune already loaded. No destructive recovery is implemented.

`NeptuneGraphReader` accepts only its read-only SDK client/config and emits fixed parameterized templates. User IDs, windows, filters and cursors remain parameter values. Path depth chooses a finite configured template; limits, pagination and timeouts are bounded. Shortest-path retrieval uses bounded path enumeration ordered by length because Neptune does not support `shortestPath()`/`allShortestPaths()`. Community lookups use the loaded static token properties, and cross-community results preserve source qualification JSON. Runtime composition must supply reader credentials restricted to `neptune-db:ReadDataViaQuery`; it must never pass a loader into runtime retrieval. The server timeout hint requires Neptune engine 1.3.2.0 or later, and SDK call timeouts also apply. Reader results and loader status Documents are converted structurally through maps, lists, strings, exact BigDecimal numbers, booleans and null. The SDK diagnostic `Document.toString` is never parsed as JSON. The internal JSON tree retains numeric types and decimal precision; graph-property string values render those exact decimals, while raw text preserves CR/LF, tabs, quotes, backslashes and Unicode.

`S3VectorStore` supports exactly the five course index names. Dimension and metric are supplied through `VectorAdapterConfig`; an existing index must match dimension, float32 type, metric and configured non-filterable keys. `VectorIndexes.key` length-frames document type, entity ID, window and model-version tag. Documents require compact identity/type/model/run/hash fields and an ordinary-S3 text pointer; full text metadata is rejected. Text-hash and complete payload bindings are reserved immutably before sending vectors, with completion recorded only after success. Identical completed documents return `Unchanged` with no PutVectors call. Failed reserved documents can retry their identical payload; changed text/payload cannot take over a key. Concurrent registry and vector writes are not a distributed transaction; a registry failure after SDK success is reported and replay reconciles the same immutable payload.

Vector puts split at configured count and conservative JSON byte bounds; gets deduplicate and split; queries follow the pinned SDK's `nextToken` with configured page and top-K caps. Equality filters use structured SDK Documents. Rejections include per-key reason codes and produce a content-addressed report in an explicitly injected ordinary ObjectStore. Registry and rejection-report ObjectStores must be supplied explicitly in production. `StorageResult.Retried` reports observed bounded put retries, while permanent/exhausted documents enter the rejected report rather than disappearing.

Run qualifications now live once in an ordinary-S3 immutable object keyed by source run and content hash, registered in `ArtifactRegistry`. Metric rows retain `SourceRunPointer` and their actual membership/path estimate. `SourceQualifications.get` verifies registry, object hash and body and retrieves the full original qualifications. `Phase6CacheLoader` requires explicit shared ObjectStore/ArtifactRegistry ports; a durable metric row cannot accidentally point into an inaccessible default fake store. Dynamo logical transactions now retain one `ClientRequestToken` across all SDK transport retries, preventing an ambiguous committed reply from appearing to create a second transaction.

### CLI

`StorageLoadMain` accepts `--manifest <completed-root-or-s3-manifest>` and `--config <json>`. Default dry-run validates graph and cache sources and prints proposed counts using ephemeral ports. `--execute-fake` traverses object/cache/ledger/registry/Neptune composition locally, including the real validation/upload/loader adapter with a main-source SDK fake. Neither mode constructs live AWS clients. `--execute-aws` additionally requires an explicit `--profile` and `--environment` matching both config `environment` and nonempty `approvedEnvironment`; otherwise it refuses before constructing credential providers. Authored live execution remains subject to the later human deployment/budget gate and has not been run.

Minimal local/fake configuration shape (values are placeholders, not deployed resources):

```json
{
  "schemaVersion": "scholarchain.storage-load.v1",
  "environment": "local",
  "approvedEnvironment": null,
  "region": "replace-with-approved-region",
  "bucket": "replace-with-ordinary-bucket",
  "graphPrefix": "graph",
  "tables": {
    "runLedger": "replace-runs",
    "entityLinks": "replace-links",
    "querySessions": "replace-sessions",
    "evidence": "replace-evidence",
    "artifacts": "replace-artifacts",
    "metrics": "replace-metrics",
    "idempotencyIndex": "replace-idempotency-index"
  },
  "neptune": {
    "endpoint": "https://replace-with-approved-neptune-endpoint:8182",
    "iamRoleArn": "replace-with-approved-loader-role-arn"
  }
}
```

Run all commands with the JDK 17 environment documented above. Example local invocation:

```text
sbt -batch 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --manifest /absolute/path/to/completed-export --config /absolute/path/to/storage-local.json'
```

### Additional primary sources checked 2026-10-22

- [Neptune StartLoaderJob](https://docs.aws.amazon.com/neptune/latest/data-api/API_StartLoaderJob.html): accepted formats, AUTO resume, role/region, user-provided edge IDs, fail-on-error and partial-load persistence.
- [Neptune openCypher CSV format](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format-opencypher.html): RFC4180 UTF-8 files, separate node/edge system headers and numeric types; every file beneath the source prefix is consumed.
- [Parameterized queries](https://docs.aws.amazon.com/neptune/latest/userguide/opencypher-parameterized-queries.html) and [ExecuteOpenCypherQuery](https://docs.aws.amazon.com/neptune/latest/data-api/API_ExecuteOpenCypherQuery.html): separate query/parameter JSON and read-only IAM action.
- [openCypher compliance](https://docs.aws.amazon.com/neptune/latest/userguide/feature-opencypher-compliance.html): dynamic property access and shortestPath/allShortestPaths are unsupported; static token properties and bounded path templates avoid these features.
- [Query timeout hint](https://docs.aws.amazon.com/neptune/latest/userguide/opencypher-query-hints-timeout-hint.html) and [query hints](https://docs.aws.amazon.com/neptune/latest/userguide/opencypher-query-hints.html): configured `USING QUERY:TIMEOUTMILLISECONDS` and minimum engine version.
- [S3 Vectors limits](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-limitations.html): dimensions 1–4,096; metadata 40 KiB/50 keys, filterable 2 KiB and at most 10 non-filterable keys; requests 20 MiB; PutVectors 500, GetVectors 100; top-K 10,000, query pages 100 results. Application caps cannot exceed these service limits.
- [QueryVectors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_S3VectorBuckets_QueryVectors.html): top-K, filters and continuation token. Pinned Java SDK 2.56.0 exposes nextToken for both request and response; pagination is implemented rather than silently truncating at the first 100 results.
- [DynamoDB TransactWriteItems](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html): a client token makes repeated identical transactions idempotent within its documented ten-minute window. The adapter fixes the token per logical invocation and its bounded retries.

7C's live integration suite, cleanup/cost instructions and independent hardening remain deferred. No live AWS operation, provider call, resource creation, deletion, deployment or reviewer was triggered in 7B.

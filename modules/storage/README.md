# Storage ports and Phase 7A adapters

## Phase 9A runtime prerequisites

`RuntimeArtifactStore` supplies read-only ranking, exact community summaries, qualified bridge
records, temporal changes, complete coauthor-edge support and bounded researcher context.
`Phase6RuntimeArtifacts.materialize(exportRoot, objects, versionedKey, config)` reads a completed
Phase 6 local export through the existing Parquet boundary. It checks selected table manifests,
producer logical hashes, source run/lineage, row contracts, duplicate keys and edge-support/bridge
bindings before publishing one immutable ordinary-S3 artifact through `ObjectStore`. No Spark
dependency, DynamoDB table, GSI, Terraform resource or live call is added. `publish` accepts an
injected manifest reader for producer contract fixtures; it applies the same checks.

The artifact is a **complete bounded snapshot of the selected source tables**, with configurable
row and byte caps. The defaults are 10,000 total rows, 16 MiB artifact bytes, 1 MiB per row, 4 MiB
source metadata and 100 returned records. These are application memory/request bounds, not cloud
limits. Declared row caps reject before opening source rows, actual row/byte overruns reject, and
no truncated snapshot is published. Larger exports require a future partitioned artifact design;
this implementation does not claim whole-corpus scalability. Memory retains this capped snapshot,
its row/relationship indexes, and at most the configured result count during top-K selection.

`ObjectStoreRuntimeArtifactStore` checks bytes, SHA-256, source run and table bindings on its first
successful load, then reuses the verified immutable snapshot and indexes for that instance and
pointer. Concurrent cold calls share a synchronized load. Warm mixed port calls do not issue
another object GET, parse JSON or validate tables again. Only success is cached: missing objects,
transport/provider rejections and corrupt first responses remain retryable on a later call; none
can turn into a cached success. A different source pointer requires a new reader instance. Metrics,
bridge/membership/community/temporal records, edges and supports have keyed indexes. Authorship
and association edges are indexed by their source subjects, avoiding whole-table scans per
researcher without expanding the potentially quadratic researcher/work/topic join in memory.
Binding validation groups supports by edge rather than scanning every support for every edge.
Ranking first filters the complete stored
researcher population by authoritative associations, then selects stored metric values. It never
uses semantic similarity to define an exact population and never recalculates collaboration
metrics. Within one filter dimension values are OR; topic, institution and venue dimensions are
AND. Associations are source-export associations across the export, while the ranked metric is
for the requested stored window. Absent association rows are unknown rather than proof of an
empty association set: a requested filter rejects if any population member lacks the necessary
authoritative coverage. Publication-subgraph metric requests reject. Responses retain the
population/match counts, result truncation, original metric records, source run and artifact hash;
numeric ranking values are decimal strings so stored Long values remain exact.

Community and bridge access retains `converged` and iteration counts; a false flag remains
iteration-limited, never inferred convergence. Bridge records include distinct degree beside the
separate stored bridge measures. Edge support retains every supporting work, optional year and
source context. Temporal records retain absent-side deltas and available membership qualifications.
The existing metric-store qualifications remain authoritative for approximate distance P90.
`storage.fakes.InMemoryRuntimeArtifactStore` builds the same bounded synthetic artifact without
network activity. A context request for an unknown declared window is rejected; a known researcher
with no metric row in a known stored window returns `Missing` context. The latter does not invalidate
the researcher's identity or eliminate an ambiguous-name candidate. Synthetic fixtures establish
offline correctness only.

For item-ID access, compose `IndexedEvidenceBundleStore(bundleStore, objectStore, indexPrefix)`.
Its automatic `put` writes the bundle and immutable item-ID-to-bundle pointers in the existing
object bucket; `getItem(evidenceId)` checks the pointer and exact item content hash before returning
the item. Phase 10's evidence route must use this wrapper. Existing bundle-only adapters keep
their API and return `evidence-item-index-required` for the additive default `getItem`; existing
bundles need an explicit replay through the wrapper to populate indexes. Frozen evidence ID
formats remain unchanged. Reusing one item ID for different content rejects; identical items may
be shared across bundles. There is no cross-store transaction: an interrupted index write may
leave a stored bundle, returns failure, and an unchanged retry can fill missing pointers. Corrupt
or dangling pointers fail closed. The matching offline fake is
`storage.fakes.InMemoryIndexedEvidenceBundleStore`.

`Phase6CacheLoader` also writes unsuffixed lookup aliases for DBLP researcher labels ending in
four numeric homonym digits. `Name 0001` and `Name 0002` keep distinct canonical IDs, exact-name
rows, source evidence and absent confidence; lookup of `Name` exposes both candidates. Existing
caches need an idempotent source reload to acquire these extra aliases. Aliases never merge IDs.


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

Loader poll budget (Phase 14C): the Neptune bulk-load poll budget defaults to 300 s / 300 polls at a 1 s interval and is unchanged unless overridden. `--load-timeout-seconds N` (1..14400) and `--load-max-polls N` (1..20000) apply only with `--execute-aws` or `--execute-fake` (the default dry-run refuses them). Giving only one derives the other at the 1 s interval and never goes below the defaults (`--load-timeout-seconds 1800` gives 1800 s / 1800 polls; `--load-max-polls 900` gives 900 s / 900 polls). When an override is applied the command prints `loader: timeoutMillis=... maxPolls=... (override)`. The effective limit is whichever of the two is reached first.

`--check-credentials --profile P` (no other option) resolves the named profile through the Java SDK and prints `CREDENTIALS-RESOLVED: profile=P sessionToken=true expiresAt=...` (or `CREDENTIALS-FAILED: profile=P reason=<ExceptionClass>`, exit 1). It makes no AWS API call, prints no key material and does not identify the caller; see "Operator credentials" below.

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

7C's authored live integration suite, cleanup/cost instructions and independent hardening are described below; execution remains deferred to Phase 14C. No live AWS operation, provider call, resource creation, deletion, deployment or reviewer was triggered in 7B.

## Phase 7C live suite: authored and compiled only

`AwsIntegrationSpec` contains one test tagged exactly `edu.uic.cs441.scholarchain.storage.AwsIntegration`. Its registration, companion tag and helper initialization read no environment/configuration, construct no credential providers or clients, and perform no I/O. Only the tagged test body checks the opt-in and loads the explicit configuration. Normal `Test` and `sbt check` exclude the tag; the separate `AwsIntegration` configuration selects it and requires its build guard. The suite was authored for later Phase 14C execution; **no live test has been run in Phase 7**.

The body exercises the real S3 ObjectStore, Dynamo ArtifactRegistry conditional writes, Neptune GraphLoader orchestration with real RunLedger/ArtifactRegistry and a separate GraphReader, and S3VectorStore put/query on a pre-existing index. Its synthetic fixture has three nodes (two researchers and one work), one stable Spark-shaped coauthor edge, one supporting Parquet row, unknown collaboration years and explicit synthetic provenance. It uses the package-private validated-handle seam to avoid constructing a complete producer export inside a live test. Therefore it tests live upload/submission/status/ledger/registry/query behavior, **not live execution of the public Parquet/sidecar validator**; public validation, logical hashes and ID parity remain covered by offline suites. The standalone support fixture is outside the CSV loader prefix. No fixture identity, collaboration or score represents an observed researcher or scientific result.

### Configuration and execution gate

Required environment variables for a future approved execution:

| Variable | Meaning |
|---|---|
| `SCHOLARCHAIN_AWS_ITEST` | Must equal `1`; absent by default. |
| `AWS_PROFILE` | Explicit nonblank profile for ordinary S3, DynamoDB and S3 Vectors. |
| `SCHOLARCHAIN_AWS_ITEST_CONFIG` | Absolute path to a non-secret JSON configuration, at most 64 KiB. |

The configuration must name a matching approved environment, a human Phase 14C gate reference, and explicitly validated execution/pricing/budget approvals. Reader, loader and cleanup clients are separate from one another. The reader profile must have read-only Neptune query permissions; the loader profile needs loader/status permissions and the configured cluster-attached S3 loader role. The cleanup profile needs only the approved, fixture-scoped Neptune cleanup permissions. Ordinary service cleanup uses the primary profile, whose future human-approved policy must be scoped to the fixture prefix/table keys/vector keys. Code separation does not prove an IAM profile's deployed policy; Terraform/IAM and network reachability are Phase 14C preflight checks.

The following is an intentionally disabled placeholder configuration, not an approval or deployed resource inventory:

```json
{
  "schemaVersion": "scholarchain.aws-integration.v1",
  "environment": "replace-approved-environment",
  "approvedEnvironment": "replace-approved-environment",
  "phase14cGateReference": "replace-with-recorded-human-gate",
  "executionApproved": false,
  "pricingValidated": false,
  "budgetValidated": false,
  "incrementalBudgetUsd": 5.0,
  "cleanupAuthorized": false,
  "region": "replace-approved-region",
  "readerProfile": "replace-read-only-neptune-profile",
  "loaderProfile": "replace-loader-neptune-profile",
  "cleanupProfile": "replace-fixture-cleanup-profile",
  "bucket": "replace-provisioned-ordinary-bucket",
  "tables": {
    "runLedger": "replace-provisioned-runs",
    "entityLinks": "replace-provisioned-links",
    "querySessions": "replace-provisioned-sessions",
    "evidence": "replace-provisioned-evidence",
    "artifacts": "replace-provisioned-artifacts",
    "metrics": "replace-provisioned-metrics",
    "idempotencyIndex": "replace-provisioned-idempotency-index"
  },
  "vectorBucket": "replace-provisioned-vector-bucket",
  "vectorIndex": "researcher-profile-v1",
  "dimension": 256,
  "metric": "cosine",
  "neptuneEndpoint": "https://replace-approved-neptune-endpoint:8182",
  "neptuneRoleArn": "replace-cluster-attached-loader-role-arn",
  "fixturePrefix": "approved-live-integration-prefix",
  "manifestDirectory": "/absolute/path/to/retained-live-run-manifests"
}
```

Only a course-named, already provisioned vector index is accepted; its float32 type, dimension and metric must match the config. `dimension` must be one of the Titan V2 widths 256, 512 or 1024 (the template previously said 2, which can never match a provisioned index); the provisioned course indexes are **256**, so keep 256 unless Terraform `vector_dimension` was changed. `AwsLiveSettings.parse` rejects any other value before a credential is resolved, and the live body still compares the value with `GetIndex` before any write. No `ensureIndex`/CreateIndex, bucket/table/cluster creation, schema mutation or infrastructure deletion is performed. All resources must already exist through approved Terraform. Credentials are obtained through the explicitly named profile providers only after the guards; credentials are never copied into the configuration or journal. The suite suppresses raw configuration/provider exception payloads in its failure message.

Safe compile-only command, used in this phase, with the exact JDK environment:

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch 'storage / AwsIntegration / compile'
```

The following command is **for the later human-approved Phase 14C run only**, after resource/network/IAM/pricing/budget and cleanup review. It has not been executed:

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
export SCHOLARCHAIN_AWS_ITEST=1
export AWS_PROFILE="replace-approved-primary-profile"
export SCHOLARCHAIN_AWS_ITEST_CONFIG="/absolute/path/to/approved-live-config.json"
sbt -batch 'storage / AwsIntegration / testOnly edu.uic.cs441.scholarchain.storage.AwsIntegrationSpec'
```

### Bounds, costs and retained ownership

One invocation uses a fresh UUID run. It creates one vector, three synthetic graph nodes/one edge, normally five ordinary-S3 objects (round-trip text, node CSV, edge CSV, support Parquet and storage load manifest), six artifact-registry rows, and two run-ledger rows; a failed stage can add one journaled failure row and a rejected vector can add one S3 rejection report. Each S3 object is capped at 64 KiB. Vector dimension is config-bound to 1–4,096, put/get batches and top-K are one, and vector visibility is checked at most ten times with 500 ms pauses. Loader polling is capped at 90 polls and a 90-second monotonic-time budget. Each SDK call has a 10-second call/attempt timeout; SDK retries are disabled and adapter attempts are one. The last in-flight call can extend a poll deadline. Request/data bounds limit workload; they are not a hard aggregate wall-clock or billing cutoff.

The user proposed a **USD 5 incremental run budget excluding already running infrastructure**. The configuration refuses a larger budget and requires pricing/budget validation, but the test cannot enforce an AWS billing ceiling. Region, provisioned/serverless capacity, baseline vector-index size, request/storage/transaction charges, data transfer, existing infrastructure time and retained artifacts affect actual cost. Revalidate the current [S3/S3 Vectors pricing](https://aws.amazon.com/s3/pricing/), [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/) and [Neptune pricing](https://aws.amazon.com/neptune/pricing/) before Phase 14C; these primary pricing pages were consulted on 2026-10-23. No dollar estimate or charge has been measured here. Existing infrastructure costs, later cleanup, and retained data until cleanup are outside a claimed measured run cost. The human gate must decide whether the proposed incremental budget is adequate for the selected environment.

A local `aws-integration-<UUID>.json` ownership journal is written before mutation, then updated atomically with each confirmed data item. It records run/environment/gate, exact bucket/key/version, Dynamo partition/sort keys and payload hashes, vector key/index/text hash, and exact graph IDs. Planned run-ledger root/stage/failure keys are recorded before loader execution. Successful ledger rows are read consistently and snapshotted for conditional cleanup. A planned record means a mutation might not have occurred, or might have committed with a lost reply; it is never an instruction to delete unverified data. Keep this journal with Phase 14C evidence.

### Cleanup procedure

The default is **retain** (`cleanupAuthorized=false`). Automatic cleanup exists only inside this tagged live body, only after all assertions pass, and only when the future human gate explicitly authorizes `cleanupAuthorized=true`. It never deletes infrastructure. It removes the exact journaled graph edge/nodes using their run property and IDs, without DETACH DELETE; removes the exact vector after checking both its run ID and text hash; conditionally deletes journaled Dynamo rows only if their entire payload still matches the recorded hash; and deletes only the exact owned S3 key/version after checking SHA metadata and the run ownership marker. For the graph batch, both ownership-filtered DELETE queries must return exact counts matching the journaled edge/node IDs. Independent read-side point checks must then find every edge and node absent before any graph entry transitions to `cleaned`. A zero/mismatched count, a remaining ID, or a read error leaves the entire graph batch journaled `created` for reconciliation; partial deletion is not reported as successful cleanup. The journal transitions each other confirmed item to `cleaned` after its existing checks. A failed or ambiguous run is retained for reconciliation, not automatically deleted.

For a retained or interrupted run, the Phase 14C operator must:

1. Read the local ownership journal and its human gate. Confirm the resource inventory and run UUID before using cleanup credentials. Resolve planned/uncertain entries with exact point reads; query only the journaled RunLedger partition with bounded pagination to find its exact failure rows. Check the loader job ID from the journaled job-registry row. If it is pending, wait for a final status before removing files that Neptune may still read. Cancellation or wider recovery needs its own human decision.
2. Compare graph IDs and `liveIntegrationRun`, vector metadata `runId`/`textHash`, Dynamo payload hashes, and S3 metadata/version IDs to the journal. If ownership or content differs, stop that item's cleanup and preserve evidence. Never infer ownership from a broad prefix or a table name alone.
3. Under the recorded data-cleanup approval, remove only that run's exact edge, then its three now-isolated nodes; its one vector; its exact registry/ledger rows; and its recorded S3 versions/objects. The authored successful-run cleanup follows this same order and refuses modified payloads. Do not delete buckets, tables, indexes, clusters, unrelated rows, or every version of a key.
4. Verify the exact point reads are absent, retain the journal and observed cleanup result, and record actual spend/runtime separately. The suite's failed-run journal is deliberately not a standalone generic cleanup command. No cleanup action has been executed in Phase 7.

### Remaining limitations and deferred findings

N6's additional S3 412 and ledger CAS/cancellation coverage belongs to the independent 7C test owner. The following accepted items remain deferred; this suite does not repair them: N4 session/reservation TTL divergence (TTL remains off by default), N5 raw idempotency GSI-key length validation, N7 configurable evidence prefix, N9 accepted leading-zero count parsing, N10 fail-closed invalid export without violation counts, N11 vector-registry failure reason/payload semantics, N12 validation/upload file re-read and memory cost, N13 CLI refusal exit/nested production retry composition, N14 full-scale path/community query cost, N15 NEW-mode recovery reloading an export, and N16 possible orphan load after submission before registry persistence. N8 remains a disclosed coordinator formatting process note. Live compatibility, deployed IAM/read-only permissions, actual cost, runtime, cleanup and full-scale behavior remain unverified gates; offline tests and compilation do not establish them.

## Phase 8A embedding queue and manifest composition

`EmbeddingWorkQueue` exposes bounded enqueue, receive, receipt acknowledgement and backlog reads.
`InMemoryEmbeddingWorkQueue` models capacity, visibility expiry, redelivery and rotating receipt
handles. `SqsEmbeddingWorkQueue` injects an existing SDK client and standard queue URL; it never
creates a queue, discovers credentials, or starts workers. Enqueue requests contain at most ten
validated work items, with configured per-message and aggregate byte limits (the latter at most
1 MiB). Receive bounds, visibility timeout, wait time and API timeout are configuration values.
Partial sends are explicit failures; successful entries may already be queued, so replay can
redeliver work. Malformed received bodies are rejected and left unacknowledged. A later deployment
must configure its DLQ/redrive policy through Terraform. FIFO-specific message groups and dedup
parameters are not implemented. SQS backlog is the sum of approximate visible, invisible and
delayed counts, not a transactional exact metric.

`EmbeddingManifestRunner` accepts the additive core `EmbeddingClient` and the existing ObjectStore,
VectorStore, ArtifactRegistry and RunLedger ports. There is no dependency on rag. Its configured
text bucket/prefix, document/manifest byte and item limits, vector dimension/metric and batch size
bound local work. It never calls `ensureIndex`: tests explicitly establish fake indexes, while
future live indexes must already exist through approved Terraform. Model IDs, region, resource
names and endpoint/client construction remain composition inputs. The agreed production target
is Ohio (`us-east-2`) with configured Titan V2 and provisional 256/cosine; the runner contains no
hardcoded production model or region.

`EmbeddingManifests.item` derives the vector key from a text-independent slot: document type,
entity ID, window, template version, chunk-policy version, chunk ordinal and model tag. Source run
ID and the content-addressed chunk/profile document ID are excluded from the key. The model tag
includes ID, version and dimension. The document ID remains in compact metadata alongside the
explicit policy/ordinal slot fields, so stored text keeps its exact content identity. Changing text
in the same slot and model reaches the existing text-hash conflict check instead of writing a
parallel stale vector. Distinct ordinals and new model versions use distinct keys; a deliberate
new template/chunk-policy version creates a new slot namespace. Changing source run alone does
not create another slot. Authoritative ordinary S3 JSON contains the full document and text hash. Its pointer addresses canonical full JSON bytes,
including provenance, with sorted object keys. The text hash separately covers exact UTF-8 text.
Thus a new source provenance or model can preserve old immutable source documents. Completed
same-key/text/model work is skipped before embedding and retains its original stored pointer and
provenance even when the new input would use another pointer. Incomplete changed-pointer payloads
reject rather than changing an immutable prepared payload. Compact vector metadata retains supplied
source/topic/institution/researcher/community IDs through the core allowlist; it contains no source
text or reference arrays. Input fields are not evidence that their referenced source exists: the
upstream producer and later bounded export composition retain that validation responsibility.

The runner reserves its own immutable text binding. A changed text for an existing key is rejected
as `vectorKeyTextConflict`; a reservation without completion is never treated as unchanged. Before
calling VectorStore it persists a content-addressed prepared vector and registry pointer. Ambiguous
vector writes, adapter payload reservations and completion-registry failures can then replay the
same finite vector values and metadata without another embedding. This is a replay checkpoint,
not a distributed transaction: failed concurrent workers can leave unreferenced ordinary S3 objects,
and external deletion of a completed vector is not detected by the unchanged shortcut.

Use a fresh ingestion execution ID for each observed rerun; source run IDs remain in documents.
A completed execution ID refuses further mutation. An incomplete execution can resume unchanged
stage transitions, but the normal replay contract uses a fresh execution ID and immutable artifact
bindings. First-run counters report writes; persistent replay reports unchanged items with zero
additional embedding calls and vector writes. `perIndex` counts observed writes. `embeddingCalls`
counts reported per-text provider attempts, and `retried` counts attempts beyond the first plus
reported VectorStore retries. Elapsed nanoseconds and vectors/second are observational, not
reproducible counters. Each retry/failure is recorded through RunLedger; terminal failed stages
remain failed and prevent complete-run claims. Rejection JSON retains keys/reason codes only.
Vector-write counters describe observed adapter outcomes; if its later completion registry write
fails, the item also appears as rejected and replay reconciles its prepared payload. Ledger or
rejection-report persistence failures make the whole runner result a typed rejection. Summary logs
contain execution ID and counters, not texts, source identities, SDK error payloads or credentials.

Module fixtures test text-pointer/hash round trips, immutable provenance across model versions,
dedup and reachable same-slot text conflicts using genuinely recomputed content IDs, distinct
chunk slots, retries and rejected records, dimension refusal, ambiguous-write replay, duplicate
batches, queue expiry and SDK request shapes. The independent suite owns the actual
DocumentRenderer → EmbeddingManifests.item → runner conflict acceptance path without introducing
a storage → rag dependency. All are synthetic and offline. Phase 8B
owns the CLI, Phase 6 fixture/real-slice ingestion and five-query retrieval smoke suite. The 8C live
command, actual ingestion, service compatibility, source corpus counts, performance, budget and
cleanup remain later gates. No AWS account, provider call or live execution was used for 8A.

## Phase 8B group consistency and local export replay

Before processing any chunk, the manifest runner validates every member of its document group,
including the configured model/dimension, text byte bound and ordinary-S3 pointer scope. Groups
must contain exactly one occurrence of every ordinal from zero through `chunkCount - 1`, with a
coherent count and whole-text hash. A count larger than the bounded manifest cannot allocate an
unbounded ordinal range. Identical duplicate ordinals are now rejected as incomplete group input;
replay is expressed as a separate execution with the complete manifest, not duplicate work entries.

An immutable ArtifactRegistry group binding covers document type, entity, window, template,
chunk policy and model, excluding ordinal, source run and text. Its hash binds the total chunk
count and the hash of the full rendered text before chunking. A changed count or whole-text hash
rejects every incoming member as `vectorKeyTextConflict` before embedding or ordinary text,
prepared-vector or vector writes. Only its rejection report is written to ObjectStore. This prevents
an unchanged prefix from hiding a shrink and prevents a growing document from writing its new tail
alongside old chunks. Rejected old groups retain their original vectors; the runner does not delete
or replace them. A deliberate model/template/chunk-policy namespace change remains explicit.
The group guard is a text-consistency preflight, not an atomic transaction across all vector writes.

Single ordinal-zero legacy documents may omit the new whole-text hash, in which case their exact
text hash is used. Multi-chunk input requires explicit count/hash from its renderer. Existing
individual artifact bindings without the new group binding fail closed as `group-binding-missing`;
they cannot silently bootstrap a potentially stale group. No 8A cloud ingestion occurred, so there
is no live corpus to migrate. An old local state or later exceptional migration needs an explicit
operator namespace/state decision; this adapter does not infer or rewrite historical group counts.

`Phase6EmbeddingSource.load` reads completed local Phase 6 exports plus their S3 Vectors work
proposal. It binds the completion marker, producer run/lineage, table declarations and work proposal.
The semantic-summary, topic-node and institution-node tables are streamed in full under configured
scan/row/metadata bounds; all three logical hashes and counts are checked before returning a batch.
Exceeding the scan bound rejects instead of labelling an incomplete scan verified. Selection holds
bounded candidates per summary type and chooses round robin in stable type/key order; it returns
actual summary-type counts so absent types remain absent. Topic/institution selections use actual
GraphNode labels, IDs, provenance and source references. Their aggregate count is the exported table
node total, not an invented per-node degree or a topic-to-institution relationship. Mixed dataset
exports do not acquire a guessed `sourceDataset` filter. The returned qualifications retain the
producer's convergence and approximation disclosures. Unselected table bodies are not revalidated
by this reader; source-reference existence and any later join beyond these selected tables retain
upstream or composition validation responsibilities.

`LocalEmbeddingState.open(path, config)` and `save(path)` provide explicit fake-only disk persistence
for the local CLI. Snapshots contain bounded ordinary objects, immutable registry bindings, fake
indexes/vectors and successful RunLedger operations. A SHA-256 envelope detects accidental
corruption; restore traverses the existing fake port validators. Bucket, prefix, dimension and metric
must match the state configuration. Save uses an atomic local file replacement; separate sequential
CLI processes can reopen state and observe real unchanged counters without invoking the embedder.
This is a local single-writer demonstration format with a 64 MiB encoded snapshot cap, not an AWS
adapter or concurrent database. Corrupt or incompatible state is rejected, never reset silently.
Failed stages and prepared checkpoints persist when composition saves after a partial run.

Module cases cover group shrink/grow, invalid/incomplete membership, legacy binding refusal,
separate-state reopen/replay and corruption, source completion and work-manifest binding. The
independent owner verifies real renderer shrink/grow, the actual G1 completed export and retrieval.
Deferred N3 (serial embedding invocation), N6 (whole SQS receive batch rejection), R2 (first filter
metadata retained on unchanged text) remain outside this repair. R3 was closed later (Phase 14 replan):
`EmbeddingManifestRunner` now checks the S3 Vectors metadata budget (50 keys, 40 KiB total, 2 KiB
filterable, `textS3Uri` non-filterable; `EmbeddingIngestConfig` mirrors the `VectorAdapterConfig` defaults
and cannot exceed the service caps) per embedding group before any text write, registry binding or
embedding call, rejecting with `metadata-limit`. The adapter keeps its own identical check through the
shared `VectorMetadataBudget`. Live compatibility, provider quality, counts and costs are not inferred
from local replay.

## Phase 9C terminal audit persistence

`RuntimeAuditStore.put(envelope)` and `get(queryId)` provide the required typed audit
boundary for answers, abstentions, unsupported requests, failures and evidence-only runs.
`ObjectStoreRuntimeAuditStore(objects, sessions, RuntimeAuditStoreConfig(prefix, ...))`
uses the existing ordinary object store and query-session table. It creates no table,
GSI or infrastructure. The injected `QuerySessionStore` must have TTL disabled so audit
pointers do not expire. Reserved, hashed audit primary/idempotency keys are distinct
from the application query ID and its client idempotency key; application query-session
state is never overwritten.

The complete envelope is immutable and addressed by its SHA-256 under the configured
versioned prefix. Only a small pointer is written with the session adapter's conditional
revision update. The default audit-envelope bound is one MiB, allowing bounded rejected
proposals and provenance without putting the payload in DynamoDB; the independent pointer
bound is sixteen KiB. Both limits are configurable application bounds. Reads bind pointer
schema, original query ID, object key, size, hash and decoded envelope validation. Public
errors are closed codes and never include provider messages or stored payloads.

A successful `put` verifies the object and authoritative pointer lookup before returning.
An identical terminal envelope replays as unchanged; a different envelope for the same
query ID is an immutable conflict. Object publication precedes the conditional pointer,
so a failed pointer write can leave an unreferenced immutable object and a pending session.
Retrying the identical envelope repairs that publication. Concurrent adapters use the
session compare-and-swap; a competing different terminal record cannot overwrite the
winner. This is not a cross-store transaction, and orphan-object cleanup is not performed
by the runtime. Audit validation deliberately retains unsupported or fabricated attempted
claims in the audit record for later explain/independent-checker use.

`storage.fakes.InMemoryRuntimeAuditStore` composes the same adapter with in-memory ports.
Module tests exercise real adapter composition, replay, application-session isolation,
invalid/oversize refusal, object/session failures and retry, lost replies, corruption,
TTL refusal, concurrent publication, and retention of malformed rejected proposals.
These are offline correctness checks; no live AWS or provider call is made.

## Phase 14A repair: storage-owned reader factory and directed edge read

`NeptuneGraphReader.connect(endpoint: java.net.URI, region: String, credentials:
software.amazon.awssdk.auth.credentials.AwsCredentialsProvider, config: GraphReaderConfig):
Either[String, NeptuneGraphReader]` builds the read-only Neptune data client inside storage so
runtime modules never name the SDK client type. The returned reader is `AutoCloseable`; `close()`
closes the client it owns (idempotent). A reader built with `new NeptuneGraphReader(client, config)`
never closes an injected client. The endpoint must be `https` with a host and an explicit port
(1-65535), no user info, query or fragment, and an empty or `/` path; the region must look like
`us-east-2`. Refusals are closed codes (`invalid-neptune-endpoint`, `invalid-neptune-region`,
`missing-credentials`). Construction makes no network call and requests no credentials (they are
resolved lazily by the SDK on the first query). SDK retries are disabled because the reader owns the
bounded `config.retry` policy; SDK call and attempt timeouts are `config.requestTimeoutMillis`
plus the one-second margin the per-request override already used. Query templates, the
`USING QUERY:TIMEOUTMILLISECONDS` hint, limits, allowed edge types and read-only behavior are those
of the existing reader.

`DirectedGraphReader extends GraphReader` adds
`directedEdges(id, window, direction: EdgeDirection, edgeTypes: Set[String], limit: Int, cursor:
Option[String]): StorageResult[DirectedEdgePage]`. `NeptuneGraphReader` and `InMemoryGraphReader`
implement it; `GraphReader` and `GraphNeighbor` are unchanged. `EdgeDirection` is `Out` (stored start
is the node), `In` (stored end is the node) or `Both` (union, a self-loop once). Rows are
`DirectedGraphEdge(fromId, toId, edgeId, edgeType, properties)`: stored start and end plus every
stored edge property, text-rendered. Graph edges carry `provenanceJson`, `sourceEvidenceJson`,
`policyVersion`; coauthor edges carry `evidenceTable`/`evidenceEdgeId` pointers and no
`provenanceJson`, so `DirectedGraphEdge.provenance` returns `Left("edge-provenance-absent")` for
them rather than inventing one. The stored start/end of an undirected type (COAUTHORED_WITH) is a
canonical order only; callers apply `GraphEdgeType.isUndirected`. Core `GraphEdge` is not returned
because the loaded coauthor rows do not contain the provenance and source evidence it requires.
Empty `edgeTypes` means the allowed set, a type outside it is `invalid-bound`, and `window`
constrains COAUTHORED_WITH only (as in `neighbors`). Order is edge ID within outgoing, then
incoming for `Both`. Cursors are opaque (`N` for one direction, `o:N`/`i:N` for `Both`), bound by
`maxCursorOffset`, and valid only for the same node, window, direction and types. Three fixed
parameterized templates (outgoing, incoming, incoming without self-loops) take `$id`, `$types`,
`$window`, `$offset`, `$limit`; no user value is interpolated, a page fetches at most `limit + 1`
rows, and a response row whose stored endpoint does not touch the requested node on the requested
side is rejected as `malformed-graph-response`. The in-memory reader pages with the same code and
applies the same window rule. Offline tests only; live Neptune engine behavior of the templates is
unverified until the Phase 14C gate.

## Phase 14C operator tools

### Operator credentials (`aws login`)

`StorageLoadMain` and `RuntimeArtifactMain` build their clients with `ProfileCredentialsProvider` for the profile given by `--profile`. The Java SDK v2 does **not** prompt for an MFA code, and a `login_session` profile (what `aws login` writes) is only readable by the SDK when the `software.amazon.awssdk:signin` module is on the classpath, which this module does not include. So pass the `credential_process` profile described below, never the `aws login` profile itself. The full, reviewed procedure is in `infra/terraform/deployer/README.md`, "Signing in with `aws login`"; this section only shows what these tools need from it. Placeholders: `<acct>` is the 12-digit account, `<iam-user>` is the IAM user that switches roles. No account ID, ARN or secret value belongs in a tracked file.

1. Browser: sign in to the console as `<iam-user>` (password and MFA code). Menu > **Switch role** > account `<acct>`, role `scholarchain-<env>-operator-loader` > **Switch Role**. Switch from the IAM-user session (use **Switch back** first if a role is shown); switching from another role is role chaining and is limited to 1 hour. The operator session ends 4 hours after the switch.
2. Terminal, then choose the active session that shows the loader role (not the IAM user):

```bash
aws login --profile scholarchain-loader --region us-east-2
```

3. `~/.aws/config` (human-edited; `aws login` writes the `login_session` line itself). The Java tools use a second profile whose name differs from the login profile and which asks the AWS CLI for the cached session:

```ini
[profile scholarchain-loader]
region = us-east-2
# after aws login: login_session = arn:aws:sts::<acct>:assumed-role/scholarchain-<env>-operator-loader/<iam-user>

# Java tools only (StorageLoadMain, RuntimeArtifactMain). Use the absolute path of aws (command -v aws).
[profile scholarchain-loader-java]
credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-loader --format process
region = us-east-2
```

Pass `--profile scholarchain-loader-java` to the Java tools. `export-credentials` needs AWS CLI v2.9 or newer and `aws login` needs 2.32.0 or newer. The credential process cannot ask for anything from inside the JVM, so sign in first; the CLI refreshes the cached session silently until the role session ends. A load that outlives it fails when the SDK asks for new credentials, so start long runs with the full session remaining. Never open or paste `~/.aws/login/cache`.

One-minute pre-check (no repository state is touched):

```bash
# 1. Terminal: prints the assumed-role ARN of the login session (needs no permission).
aws sts get-caller-identity --profile scholarchain-loader
# expect Arn: arn:aws:sts::<acct>:assumed-role/scholarchain-<env>-operator-loader/<iam-user>

# 2. The Java SDK resolves the credential_process profile (no API call; prints the expiry).
sbt -batch 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --check-credentials --profile scholarchain-loader-java'
# expect: CREDENTIALS-RESOLVED: profile=scholarchain-loader-java sessionToken=true expiresAt=<about 15 minutes ahead: the access credential, not the end of the session>
```

Step 1 proves who you are; step 2 proves the SDK path these tools use. Neither the `aws login` flow nor the `credential_process` form has been exercised against a live account in this repository (no AWS call was made when this was written); if step 2 fails, fix the profile before any load, and report only the printed class name.

### Bounded runtime artifact producer

`RuntimeArtifactMain` is the missing producer for `SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY` / `_SHA256` / `_SOURCE_RUN_ID` (see `modules/services/README.md`). The real Phase 6 slice (about 800 thousand rows) cannot fit the artifact caps, which this tool never raises: **10,000 rows and 16 MiB** (`RuntimeArtifactConfig`, 1 MiB per row). It verifies the whole completed local export against its manifest hashes, selects a bounded subset, writes the artifact locally and, only with `--execute-aws`, uploads the identical bytes.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
# Local only (default): reads the export, writes OUT/runtime-artifact.json, selection-report.json and
# runtime-artifact-pointer.json. A full-size source needs roughly 3-4 GiB of heap (about 23 s and
# a 3 GiB heap for 800 thousand synthetic rows).
SBT_OPTS="-Xmx4g" sbt -batch 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.RuntimeArtifactMain \
  --source /abs/path/to/completed-phase6-export --include-ids /abs/path/include-ids.txt --out-dir /abs/path/out'
# Upload (explicit AWS execution; a human gate applies): same command plus
#   --run-prefix <run_prefix> --execute-aws --profile scholarchain-loader-java --bucket <artifact bucket> --region us-east-2
```

Options: `--degree-window ID` (default `all-years`), `--run-prefix RUN`, `--key-prefix P` (default `runtime-artifacts`) or `--key K` (must contain `/versions/`), `--max-source-rows N` (reader bound, default 3,000,000, 1..20,000,000). `--run-prefix`, `--key-prefix` and `--key` are mutually exclusive.

**Upload key contract.** The operator-loader role holds a create-only `PutObject` grant on exactly `runtime-artifacts/<run_prefix>/` in the bucket the services read, where `<run_prefix>` is the human-chosen run folder (`operator_run_prefix` in `infra/terraform/deployer`). `--run-prefix RUN` makes the key follow it: `runtime-artifacts/<RUN>/versions/<run id with ':' replaced by '-'>/runtime-subset-<sha256>.json`. `RUN` must match `^run-[a-z0-9][a-z0-9-]{1,27}$` (for example `run-20261115`; 6 to 32 characters); anything else exits 2 before the source is read. `--execute-aws` refuses (exit 2) unless one of `--run-prefix`, `--key-prefix` or `--key` is given, and only `--run-prefix` produces a key inside the loader's grant. Without any of the three, a local-only run keeps the legacy key `runtime-artifacts/versions/<run>/runtime-subset-<sha256>.json`, which the loader role cannot write. The `/versions/` segment is required by the object store's immutable-key rule. A different selection never collides with an earlier object (the bucket write is create-only: identical bytes are `unchanged`, different bytes under the same key are refused). Exit codes: 0 success, 1 selection or upload refused (the report is still written), 2 invalid arguments.

The command prints the values to put in the private tfvars or task environment (the bucket line appears only with `--bucket`, i.e. with `--execute-aws`):

```text
SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET=<bucket the upload targets>
SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY=runtime-artifacts/<run_prefix>/versions/<run id>/runtime-subset-<sha256>.json
SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256=<sha256 of the artifact file>
SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID=<source run id>
```

The services read `SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET` (default: the RAG bucket), so upload to the bucket the service is configured to read; when that is the RAG bucket the bucket value is optional. The SHA-256 equals `shasum -a 256 runtime-artifact.json`. The variable names in the private tfvars are defined by the infrastructure owner; the values above are what the human copies.

**Selection rule** (the same text is stored in `selection-report.json` as `ruleText`):

1. *Include list (required, `--include-ids FILE`).* Every listed researcher, and every author of each listed work, is included with its complete closure. A listed ID that is unknown in the source, whose closure alone exceeds a cap (rows, estimated bytes, or one row over 1 MiB), or that cannot fit together with the other listed IDs refuses the whole run; nothing is written except the report.
2. *Fill.* Remaining researchers are ordered by `distinctCoauthorCount` in the degree window (default `all-years`) descending, ties by stable researcher ID ascending, and are added one at a time with their whole closure. The fill stops at the first researcher whose additional rows would exceed the row cap, the byte cap (including framing) or the per-row cap, so the included set is a prefix of that order after the listed IDs, and the cap-limited stop point is reported.
3. *Closure of a researcher.* Its node; its rows in `researcher_collaboration`, `communities`, `bridges` and `temporal_changes` for all windows; the summaries of its communities; every `coauthored_with` edge incident to it with all its support rows and both endpoint nodes; its `authored` edges and, for each authored work, the `has_topic` and `published_in` edges; its `affiliated_with` edges; and the topic, venue and institution nodes those edges reference. A closure is added whole or not at all, and rows shared with another closure are counted once.
4. The output is deterministic: rows are sorted by their key, each table manifest is recomputed (`rowCount`, `sortedRowsSha256`) and records `subset.rule`, `subset.sourceRowCount`, `subset.sourceSortedRowsSha256` and `subset.includeListSha256`, and the same inputs give the same bytes. The tool validates the artifact with the same checks the reader runs and loads it through `ObjectStoreRuntimeArtifactStore` before writing anything.

Consequences the reader and the evaluation must respect: the artifact is a subset, not the corpus. `rank` reports `populationCount` as the number of included researchers, the rankings are exact only within that population (a ranking by `distinctCoauthorCount` is exact for the top entries while they lie inside the fill prefix; other metrics are not), a researcher that appears only as an endpoint node answers `Missing`, and community summaries describe the source community although only some members are present. The report (`selection-report.json`) lists the included researchers with reason (`include-list`, `work-author:<id>`, `degree-fill`), their closure sizes, per-table counts, the total rows and bytes, the first researcher dropped by the caps with the rows it needed, and the count of candidates not reached.

**Include list format** (`--include-ids FILE`, at most 2000 IDs, 1 MiB): one stable ID per line, `researcher:...` or `work:...`; blank lines and lines starting with `#` are ignored; duplicates are removed. A sample with synthetic placeholder IDs is `modules/storage/src/test/resources/runtime-subset-include.example.txt`. As of 2026-11-08 no list of real smoke or evaluation entities exists in the repository: `scripts/smoke-test.sh` sends only the offline-synthetic default question (`Synthetic fixture: publication count for A`, no entity ID), and `experiments/` and `load-tests/` are empty. The include file is therefore authored later by the experiment owner or the human, from the real Phase 6 export IDs, before 14C.

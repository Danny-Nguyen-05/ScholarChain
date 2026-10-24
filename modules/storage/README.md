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
  "dimension": 2,
  "metric": "cosine",
  "neptuneEndpoint": "https://replace-approved-neptune-endpoint:8182",
  "neptuneRoleArn": "replace-cluster-attached-loader-role-arn",
  "fixturePrefix": "approved-live-integration-prefix",
  "manifestDirectory": "/absolute/path/to/retained-live-run-manifests"
}
```

Only a course-named, already provisioned vector index is accepted; its float32 type, dimension and metric must match the config. No `ensureIndex`/CreateIndex, bucket/table/cluster creation, schema mutation or infrastructure deletion is performed. All resources must already exist through approved Terraform. Credentials are obtained through the explicitly named profile providers only after the guards; credentials are never copied into the configuration or journal. The suite suppresses raw configuration/provider exception payloads in its failure message.

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

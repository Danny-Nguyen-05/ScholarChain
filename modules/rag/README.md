# Phase 8 rendering and embeddings

The shared `EmbeddingClient` contract lives in core. Storage accepts it by injection; RAG depends
on storage, and storage never imports RAG. This module provides deterministic rendering, a local
hashed bag-of-words fixture embedder, an injected Bedrock Titan V2 adapter and descriptive context.
The local entry point constructs no credentials or live SDK clients. The separately guarded live
entry point is authored for later 8C execution and has not been run. No provider call was made
for local 8A/8B validation.

`DocumentRenderer` accepts five document types. Fixed type headings precede source fields sorted
by unique field name. Each value is copied exactly, each field retains its `SummarySourceRef`, and
source references are sorted and deduplicated. The caller supplies actual producer rows, IDs and
counts; rendering does not infer relationships or calculate graph metrics. Topic/institution fields
must come from their actual nodes and aggregate tables; unrelated topic/institution rows must never
be presented as a joint relationship. `fromSummary(summary, abstractText, identityFields)` requires
an actual window and retains all original source references and qualifications. With no abstract
or blank paper abstract, it passes the exact Phase 6 text bytes to chunking without a generated
heading or `summary:` prefix. Newlines, Unicode and trailing whitespace are retained. Its supplied
identityFields map is validated against the core allowlist and preserved through documents,
manifest items and compact vector metadata; no identity/filter values are inferred. It does not
fetch abstract IDs. An explicit nonblank permitted paper abstract is a separate composition:
exact original summary bytes, one LF, then exact abstract bytes, with both text and permission
references added and `permitted-abstract` recorded. Non-paper abstract inputs and invalid permission
references are rejected. This explicit composition preserves the summary as a prefix; it is not
claimed to be byte-identical to the original summary as a whole.

Paper text uses a supplied permitted abstract only when nonblank, with both text and permission
source references. Missing/blank text uses the supplied compact paper fields and records
`paper-summary-fallback`; no text acquisition or permission discovery occurs here. Structural
references are not proof that the source exists or its license permits this usage; export adapters
must resolve those references. The normal fallback includes source-backed title, venue, year,
topics and team size when those fields exist, without fabricating missing values.

`ChunkPolicy` bounds Unicode code points, prefers the last whitespace boundary inside the limit,
retains whitespace and overlaps exact code points. It rejects blank text and excess chunks. Large
unbroken spans split at the hard boundary. IDs use `StableIds.chunkOrProfileId` and bind entity,
window, template version, boundary-policy version, chunk limits/overlap/count cap, ordinal and exact
text. This content-derived document ID remains in metadata and never supplies the vector slot.
The renderer also fills a text-independent `chunkPolicyVersion` (boundary rule, limits, overlap and
count cap) and zero-based `chunkOrdinal`. Vector keys length-frame document type, original entity
ID, window, template version, chunk-policy version, ordinal and model tag. Neither source run ID,
text, text hash nor document ID enters that slot. Changed text for the same slot therefore keeps
the same key and is rejected as `vectorKeyTextConflict` before embedding. Unchanged text skips;
new models/templates/policies and distinct chunk ordinals use distinct keys. Every renderer
output now includes the actual `chunkCount` and `wholeTextHash` of the exact pre-chunk text.
Storage binds the whole group before chunk writes, rejecting shrink, grow, missing/duplicate
ordinals and changed whole text even when some overlapping chunk text is unchanged. The source run remains
provenance in the authoritative document and metadata. This is an immutable slot, not automatic
replacement or an update-in-place policy.
The default million-codepoint document cap and 1,000-chunk cap are defensive local bounds and can
be configured down for the selected workload; they do not override provider request limits.

`DeterministicHashedEmbeddingClient` lowercases Unicode words, assigns each word to a SHA-256
bucket and normalizes counts. It returns stable lexical neighbors with no network or model call.
These results establish local test behavior only; they do not establish Titan retrieval quality.

`BedrockEmbeddingClient` takes an already constructed SDK client and `BedrockEmbeddingConfig`.
Model ID, explicit version, dimension and region are configuration. The approved planned settings
are Titan V2 (`amazon.titan-embed-text-v2:0`), explicit deployment version, 256 dimensions and Ohio
(`us-east-2`), with cosine configured in the vector index. These are provisional until the later
index-provisioning gate. Region is declarative; SDK composition must construct its client in that
same region. There is no hardcoded bucket, endpoint or account ID.

The adapter requests normalized vectors using `InvokeModel`, checks exact configured dimension
and finite float32 values, preserves input order/cardinality, and sanitizes all errors to typed
codes. It shares a concurrency semaphore across invocations. Defaults of two concurrent calls,
three total attempts, 25ms initial/1,000ms maximum backoff, 500 batch items and a 30-second per-call
timeout bound local work; all are explicit configuration entries. Only 429, server and SDK transport
failures retry. SDK composition must disable transport retries so attempts are not multiplied.
Titan's documented maxima are 50,000 characters and 8,192 tokens; the adapter additionally uses
UTF-8 byte length against its configured token budget as a conservative local screen. This is not
an exact Titan tokenizer, a throughput guarantee or a billing ceiling. Provider token-limit errors
remain typed permanent failures. Limits can reject valid longer text conservatively; callers should
chunk it. Supported Titan dimensions are 256, 512 and 1,024.

`SemanticContexts.fromStoredObject` checks the ordinary-S3 key, envelope-byte SHA and length,
text SHA, document identity, slot policy/ordinal metadata and model-bound stable-slot key before excerpting. It performs no I/O;
the caller resolves the pointer through its ObjectStore. Scores are negative vector distances, so
higher scores rank closer results without claiming a calibrated confidence. The format always
labels items descriptive context and disallows graph/metric authority. Counts, path hops, edges,
components and bridge metrics require Neptune, DynamoDB or Spark evidence. Its pointer check
binds the object key; bucket selection remains the caller's ObjectStore composition responsibility.

## Local ingestion and replay (8B)

`EmbeddingIngestMain` reads a completed Phase 6 export and its `load-manifests/s3vectors.json`
work declaration. It delegates completed-marker, declaration, row-count and logical-hash checks
to `Phase6EmbeddingSource`, preserving the source run and its qualifications. Selected summaries
are rendered without changing their original text. Topic and institution nodes become separate
fifth-index documents, with their actual labels, classes and explicitly named exported-table total
node counts. A table total is not presented as a per-node count or a topic/institution relationship.
No abstract is fetched; exported abstract IDs alone do not authorize copying abstract text.

The JSON `LocalEmbeddingConfig` requires `model`, `textBucket`, `textPrefix`, `templateVersion`,
`chunkMaxCharacters` and `chunkOverlapCharacters`. Optional bounds are shown by the case class:
100 summaries, 10 topic nodes, 10 institution nodes, 200,000 scanned rows, 1,000 chunks per document,
1,000,000 pre-chunk code points, 10,000 manifest items, 16 MiB manifest, 1 MiB text and batch size
100. Choose a model ID such as `local-hashed-bow` so fake vectors cannot be mistaken for Titan.
The configured bucket/prefix name ordinary-S3-shaped pointers in the persistent fake state; no
bucket or other cloud resource is created. All local vector indexes use cosine.

Example, using actual absolute paths for the selected completed export/config/output directory:

```text
sbt -batch 'rag / Compile / runMain edu.uic.cs441.scholarchain.rag.EmbeddingIngestMain --export /ABS/completed-export --work-manifest /ABS/completed-export/load-manifests/s3vectors.json --config /ABS/local-config.json --state /ABS/local-state.json --report /ABS/report.json --manifest-output /ABS/embedding-manifest.json --run-id local-ingest-1'
```

Every sbt invocation requires the repository's documented JDK 17 environment. The CLI has no live
mode. It records source/work/embedding-manifest hashes, counts, selected types, measured elapsed
runtime and vectors/second, model identity and rejection reasons. Original source qualifications
are retained in a sibling report file with a hash. The generated embedding manifest carries full
source references. Run IDs identify ingestion attempts and may differ across replay reports.

`LocalEmbeddingState` persists objects, immutable bindings, prepared vectors, vectors and ledger
operations to disk and reopens them in a new process. Replay with the same state writes zero new
vectors and reports unchanged items; a separate fresh state gives identical deterministic counters
and the same manifest hash. Runtime and throughput are measured values, not expected to be
identical. The CLI saves state after the runner returns even when ingestion rejects items. Corrupt
or incompatible state is rejected instead of silently reset. Snapshot publication is local; there
is no distributed transaction or claim that an OS crash preserves an unsaved in-memory mutation.
Keep generated state/manifests/data under ignored target or approved scratch paths, not Git.

`embedding-smoke.json` commits synthetic documents and six fixed queries/expected IDs covering
researcher, community, path, paper, topic and institution. `EmbeddingRetrievalSpec` runs those
queries against the deterministic embedder and fake vectors and follows every hit to its ordinary
text object, verifying envelope/text hashes and the descriptive-only authority boundary. These
synthetic identities, relationships and source references are test fixtures, never real findings.

## Authored live command (unexecuted)

`LiveEmbeddingIngestMain` is a separate future 8C entry point. It accepts a pre-rendered embedding
manifest, `LiveEmbeddingConfig`, a human-written `LiveEmbeddingApproval`, report path and run ID.
A local fake manifest must be reviewed and rendered for the approved real model before live use;
changing model identity changes keys and requires new manifest/config hashes in the approval.

```text
sbt -batch 'rag / Compile / runMain edu.uic.cs441.scholarchain.rag.LiveEmbeddingIngestMain --config /ABS/approved-live-config.json --manifest /ABS/approved-embedding-manifest.json --approval /ABS/human-written-approval.json --report /ABS/live-report.json --run-id APPROVED-RUN-ID'
```

Do not execute this command during 8B. Phase 14 must first provision ordinary/vector buckets,
all five indexes and Dynamo tables/IAM through approved Terraform. The approval binds exact
config/manifest/Phase-14-gate hashes, environment, run ID, expiry, vector/concurrency/request/dollar
caps and explicit execution/pricing/budget decisions. A disabled approval refuses before reading
the referenced gate or creating credential providers/clients. Offline tests exercise only pure
preflight and refused execution with a factory sentinel, never approved execution or AWS calls.
The retained disabled approval template is not an approval.

Preflight rejects invalid document/group identity, incomplete groups, a mismatched model/pointer,
wrong caps or an assumed cost above either configured or approved limits. It bounds embedding
requests by item count times maximum attempts and estimates dollars as that count times the
configured conservative per-attempt bound, plus a configured per-vector storage bound and fixed
overhead. These are operator-validated assumptions, not measured prices or an enforceable AWS
billing ceiling. They must cover retries, object/registry/vector requests and the approved retention
window; unrelated running infrastructure and costs after that window need separate accounting.

Only after every check passes does the live factory construct profile-based SDK clients in the
configured region, with SDK retries disabled. Storage adapters use one attempt; the Bedrock adapter
owns its configured retries. It checks existing index dimension, metric, float32 type and exact
non-filterable keys using `GetIndex`; it never calls `ensureIndex` or provisions resources. `runId`
and `textHash` must remain filterable. The runner retains its canonical text, registry/ledger and
prepared-vector recovery behavior. Live report runtime/counters and assumed bounds are not proof
of actual billing or a completed course corpus. No deletion or infrastructure cleanup is authored
in this entry point; the later operator gate/runbook owns any scoped cleanup authorization.

Real service execution, cost, full corpus size, query latency samples and real-model quality remain
later gates. Optional providers, OpenSearch and extra indexes remain omitted. Accepted N2-N8 and
other deferred findings are not repaired by 8B except the separately authorized group-binding R1.

Primary AWS references checked for this implementation:
- [Titan V2 request/response](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-text.html)
- [Titan limits and dimensions](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Titan regional support](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-titan-text-embeddings-v2.html)

## Render-only real-model handoff (8B N9)

`EmbeddingManifestMain` separates work preparation from fake ingestion. It reads the same completed
Phase 6 export/work declaration and rendering bounds through `LocalEmbeddingConfig`, but accepts
the configured real model identity. The class name of that shared configuration is historical;
this command neither embeds nor constructs/opens/writes fake state. It writes only a canonical
embedding manifest, its hash, a provenance/count/model report, and original source qualifications.
The report explicitly records `mode=render-only`, `embeddingCalls=0` and `stateWritten=false`.
Use the approved future ordinary-S3 bucket/prefix and model ID/version/dimension when preparing a
live manifest; do not edit a fake-ingestion manifest by hand.

```text
sbt -batch 'rag / Compile / runMain edu.uic.cs441.scholarchain.rag.EmbeddingManifestMain --export /ABS/completed-export --work-manifest /ABS/completed-export/load-manifests/s3vectors.json --config /ABS/render-real-model-config.json --manifest-output /ABS/real-model-manifest.json --report /ABS/render-report.json'
```

This local rendering command does not authorize live ingestion. A manifest can be checked by pure
`LiveEmbeddingIngestMain.preflight` using synthetic test approvals without invoking the approved
execution path. Actual execution still requires the human record and Phase 14 gate. The live
ingestion report now includes configured model ID/version/dimension, actual per-index write counts,
all retained rejection keys/reasons and `rejectedReportUri`, in addition to its counters and hashes.
Its formatting helper is pure and independently testable without calling live or fake ingestion.

## Authored bounded live retrieval/latency command (unexecuted)

The separate `LiveEmbeddingSmokeMain` command performs future approved retrieval only. It does not
write vectors, registry entries, text objects or infrastructure, and it has never been executed.

```text
sbt -batch 'rag / Compile / runMain edu.uic.cs441.scholarchain.rag.LiveEmbeddingSmokeMain --config /ABS/approved-query-config.json --manifest /ABS/real-model-manifest.json --approval /ABS/human-query-approval.json --report /ABS/query-report.json --run-id APPROVED-QUERY-RUN'
```

The smoke configuration contains a nested `LiveEmbeddingConfig` plus at least five named query
records spanning all five configured indexes. Each query specifies exact text, expected vector keys
that occur in the approved manifest/index, and top K. The operator supplies per-query sample count,
maximum query SDK requests, maximum query embedding attempts, maximum top K (at most 100), maximum
text-object reads and bytes, per-query/per-object-read price assumptions and a dollar cap. Exact
query config, manifest and Phase 14 gate bytes are hash-bound by an unexpired approval whose
`operation` is explicitly `query-smoke`. Its additional `queryRequestCap`, `queryEmbeddingCallCap`
and `queryObjectReadCap` must cover configured bounds. Ingest approvals require `operation=ingest`;
neither operation can reuse an approval for the other. Every content, identity, capability and cap
check completes before credential/client construction. A disabled approval refuses before reading
the referenced gate. Disabled templates and synthetic guard tests are not operator approvals.

Pure planning computes query calls as query count times samples per query, embeddings as query
count times configured maximum attempts, and object reads as the sum of top K times sample count.
The assumed dollar bound combines those embedding/query/object-read bounds with configured unit
assumptions and fixed overhead. All bounds must fit configured and approved caps. SDK retries are
disabled; vector query pagination is capped at one page and top K at 100. The expected-name and
manifest checks are planning assertions, not evidence that a real query will return those neighbors.

Future execution checks pre-existing index configuration with `GetIndex`, embeds each query once
(with bounded adapter retries), and takes the configured query samples using that vector. Queries
filter on the exact model tag. Every hit must resolve within the approved ordinary bucket/prefix,
pass the byte bound, match its text/document/model/slot hashes and yield descriptive semantic
context. Wrong pointers or corrupt/missing source objects fail closed. Query duration measurements
exclude embedding and text-object reads; the report labels this scope and uses nearest-rank p50/p95
per index, observed sample counts, expected-neighbor outcomes and verified-pointer counts. These
latencies, identities and outcomes cannot be reported as observed until the actual approved run.

The query command's price assumptions require human validation for current regional prices,
request/retention scope and existing infrastructure. It cannot enforce an AWS billing ceiling.
Pure tests cover content/operation/cap refusal, all-five-index query definitions, exact quantile
expectations and report fields; executable tests take only refusal branches with a factory sentinel.
No approved live execution, including an approved path with fake ports, is used in offline tests.

# Phase 8A rendering and embeddings

The shared `EmbeddingClient` contract lives in core. Storage accepts it by injection; RAG depends
on storage, and storage never imports RAG. This module provides deterministic rendering, a local
hashed bag-of-words fixture embedder, an injected Bedrock Titan V2 adapter and descriptive context.
No entry point constructs credentials or a live SDK client. No provider call was made for 8A.

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
new models/templates/policies and distinct chunk ordinals use distinct keys. The source run remains
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

Five-query retrieval smoke tests, Phase 6 local CLI runs and the unexecuted 8C command/approval
packet belong to 8B. Real service execution, cost, corpus size and real-model quality remain later
gates. Optional providers, OpenSearch and extra indexes are omitted.

Primary AWS references checked for this implementation:
- [Titan V2 request/response](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-text.html)
- [Titan limits and dimensions](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Titan regional support](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-titan-text-embeddings-v2.html)

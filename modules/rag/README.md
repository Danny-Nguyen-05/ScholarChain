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

### Phase 14 gap fixes (N15, embedding token bound, N11 disclosure)

- **N15 (query-smoke caps).** A `query-smoke` approval authorizes only `queryRequestCap`,
  `queryEmbeddingCallCap`, `queryObjectReadCap` and its `dollarCapUsd`. The smoke preflight no
  longer re-runs the ingest cap checks: the nested `live` block is used for model, pointer,
  group and manifest validation (`LiveEmbeddingIngestMain.validateManifest`) only. The approval's
  `vectorCap`, `concurrencyCap` and `embeddingCallCap` are not authorizations for a smoke (leave
  them 0; negative values are refused), and `live.maxEmbeddingCalls`/`live.dollarCapUsd` are not
  compared with the approval. `live.maxVectors` must still cover the manifest size. Identity
  (run ID, environment, expiry, gate hash), the smoke dollar cap and the three query caps remain
  mandatory. The smoke makes no synthesis (LLM) call; there is no synthesis cap to approve.
- **Token-derived embedding bound.** Ingest and smoke preflight also bound embedding spend by the
  content: tokens = sum over texts of ceil(UTF-8 bytes / `minBytesPerEmbeddingToken`) times
  `maxEmbeddingAttempts`, priced at `assumedUsdPerMillionEmbeddingTokens` (default 0.02). The
  dollar estimate takes the larger of that and the per-attempt bound, then adds storage and fixed
  overhead. Exceeding either the configured or the approved dollar cap refuses with
  `live-assumed-cost-or-request-bound` before any factory, credential or Titan call. At 0.02 per
  million tokens, 15,000,000 token-attempts cost exactly USD 0.30. `minBytesPerEmbeddingToken`
  defaults to 1 (a strict upper bound; raise it up to 4 only as a human-validated assumption).
  It remains an assumed bound, not a billing guarantee. Reports carry `embeddingTokenBound`.
- **N11 (disclosure only).** The four mixed-export summary types (researcher-profile, community,
  paper, collaboration-path) deliberately carry no `sourceDataset` identity field and no
  `sourceDataset` filter, because one summary can reference several source datasets and a
  dataset is not guessed from a mixed export (`Phase6EmbeddingSource`, owned by storage). Only
  `topic-institution-summary` node documents carry `sourceDataset`. The compact metadata that lists a
  source dataset is therefore unavailable as a filter for the other four types; their provenance
  is carried by `sourceReferences` and the ordinary-S3 text object.


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

## Phase 9A runtime planning and identity contracts

`QueryPlannerAgent` proposes only allowlisted `QueryOperation` values. It validates model JSON
against `prompts/schemas/query-plan-v1.json` using the explicit bounded JSON Schema subset in
`RuntimeJsonSchema`; unsupported schema keywords fail closed. `planner-v1` and `synthesis-v1`
prompts live in `prompts/runtime/`. Their schema IDs are `scholarchain.runtime.planner.v1` and
`scholarchain.runtime.synthesis.v1`. Assets are loaded from an explicitly supplied prompts
directory and checked against configured versions. The synthesis schema/prompt are contracts
only in 9A; synthesis, claim verification, workflow orchestration and benchmarks arrive later.

`LlmClient` has a deterministic, recording `ScriptedLlmClient` and an injected-client
`BedrockConverseLlmClient`. The adapter forces the named output tool with `toolChoice.tool`,
accepts exactly one correctly named tool-use block, rejects text substitutes and unsafe numeric
rounding, and retains configured model/version and optional token usage. All deterministic
claim numbers use decimal strings. The caller owns region/IAM/client lifecycle and disables SDK
retries so the planner's single configured malformed-output retry remains the effective bound.
No client, resource or live model call is created by normal tests. The configured placeholder
model has no verified deployed-model or regional compatibility; that remains a future live gate.

The planner preserves extracted names, stored window IDs, topic/institution/venue constraints,
the requested metric and configured retrieval mode (`fused` by default). Conservative coverage
validation rejects unrepresented words/clauses and checks common unquoted population filters.
Unknown constraints, unknown metrics, arbitrary Cypher/SQL/AWS requests and requests to recompute
unstored filtered metrics are unsupported. After at most one malformed-output retry, a small
anchored fallback handles quoted-name path/direct-coauthor/component requests, distinct-coauthor
ranking, maximum-team/bridge ranking and semantic topic explanations. Explicit filters use
`topic "..."`, `institution "..."`, `venue "..."`; stored windows use `window <id>` or a uniquely
mapped `since <year>`. Novel language can abstain even when a human could interpret it. Model
suggestions cannot remove a recognized constraint. Retries share one planner deadline. Factual
ranking/filter execution and authoritative metadata availability checks belong to 9B.

`ResearcherResolverAgent` groups cache rows by canonical researcher ID, preserves source IDs,
affiliations, evidence/run pointers and absent confidence, and abstains on zero or multiple
candidates. Different confidence values never break identity ties. It optionally obtains bounded
source-backed coauthor context through `RuntimeArtifactStore`; absent context stays absent.
`Name 0001` and `Name 0002` remain distinct. Unsuffixed base-name ambiguity depends on the storage
loader's source-backed base aliases; an older cache must be reloaded to acquire those aliases.
Source identifiers, source-row bindings and deadlines are checked before returning a result.

The runtime config classpath example is a local placeholder. It contains explicit model ID/version,
region, temperature, context/input/output bounds, prompt/schema versions, stored-window definitions,
retrieval mode and stage deadlines constrained by `operations.synchronousDeadlineMs`. Legacy numeric
window projections are compatibility fields; actual runtime selection uses stored `windowId`s.
Phase 8C remains deferred to Phase 14C. Offline correctness tests establish contract/control
behavior only; live model quality, injection resistance and provider compatibility are unverified.

The 9A repair binds each recognized ranking metric, bridge measure, required operation and
author-count conversion to deterministic request intent before accepting model output. An
unspecified bridge measure is the configured default; model-selected alternatives are rejected.
Stored window IDs and uniquely mapped cumulative `since`/bounded-period phrases must match the
complete requested period. A request naming no window uses the configured default, and cannot
acquire extra model-selected windows or comparison windows. Multiple incompatible metric intents
fail closed because the existing plan has one ranking metric. Model disagreements use the same
bounded retry and safe fallback/Unsupported policy as malformed output.

Identity bounds use `resolver.maxDistinctCandidates`, independently of graph-result limits and
raw cache-observation counts. Candidate source IDs, evidence refs, affiliations and run IDs have
separate configured caps. `provenanceSummary` reports their distinct totals before clipping and
whether any list was truncated. Confidence still uses all observations for that canonical identity.
An overflow result is `Ambiguous(name, candidates, totalCandidateCount, truncated)` with a bounded,
deterministically ordered candidate list. A candidate absent from a known stored window retains
its identity with absent context; this also preserves ambiguity when one homonym is absent.
An unknown window remains a typed failure. These repairs do not implement 9B retrieval stages.

## Phase 9B retrieval and persisted evidence

`CollaborationMetricsAgent`, `PathFinderAgent`, `CommunityAnalystAgent` and
`SemanticContextAgent` accept `RetrievalInput(plan, resolvedCandidates)` and return typed
`Ready`, `Missing`, `Unsupported` or `Failed` results. Their inputs are storage ports; runtime
code does not recompute Phase 6 collaboration metrics or choose a researcher by semantic similarity.
Rankings filter the authoritative stored population before selecting the requested stored metric,
and carry population, matched and returned counts plus top-K truncation. A missing authoritative
filter projection is unsupported. Named-researcher metric, path, community and temporal requests
with unsupported population filters fail closed rather than dropping those filters.

Path retrieval checks stored component IDs first. Different components produce `Disconnected`
with component evidence. An empty bounded template search produces `NoPathWithinLimit`, and an
explicit adapter depth-limit result produces `ExceededMaxHops`; neither claims disconnection.
Each returned hop is matched to the selected window/run and authoritative edge support, retaining
joint-publication count, supporting work IDs and known/unknown years. Direct coauthor lists carry
truncation. Repeated collaboration uses per-edge `jointPublicationCount`; weighted degree and total
coauthor occurrences remain the same stored invariant, not independent corroboration.

Community and bridge evidence carries convergence and iteration qualifications; `converged=false`
is explicitly `iteration-limited`. Selected members and neighboring communities are bounded, and
selected cross-community edge counts are labeled as selected. Bridge evidence includes cross-
community degree and weight, communities connected, participation coefficient and distinct degree.
Stored temporal deltas retain presence flags and separate source-window qualifications. A stored
P90 distance estimate is a separate deterministic evidence item marked approximate, bound to its
component, window, source run, method and source row. Exact researcher metric items remain
non-approximate with the same stored values whether the estimate exists or not. Both items are
admitted atomically for the metric request; a context budget that cannot retain both abstains.
The stored P90 is not an exact distance.

Semantic retrieval embeds the question through the injected port, queries the configured existing
index with supported metadata filters, verifies each ordinary-object pointer and Phase 8 document
hash, and emits descriptive `TextChunk` evidence. Query-model identity must match the hit metadata.
Venue filters and multiple values for one semantic filter are currently unsupported because that
metadata/query contract is unavailable. Similarity score remains retrieval metadata and never
becomes deterministic evidence. Excerpts render as JSON in an `untrusted_evidence_json` data block;
angle brackets in retrieved content are JSON escaped, preventing text from closing the block.

`EvidenceBuilderAgent` retains full source provenance in persisted items, partitions deterministic
and descriptive evidence, and uses `RuntimeEvidenceIds.bind` content-bound IDs. Thus a changed
run, window, payload or supporting work cannot silently reuse an immutable citation. Path and comparison output is atomic: a budget failure returns a typed missing-evidence result rather than keeping an incomplete path. Rankings retain the largest admitted top-K prefix with explicit source-fetched and context-retained counts and a truncation flag; an empty prefix abstains. Optional semantic excerpts are Unicode-safe truncated and rebound.
The context cost is a conservative UTF-8-byte upper bound on tokens, applied to a compact rendered
context with shared run/window/version lookup tables that omits repeated storage provenance and absent fields. Bounded resolved candidates, their names, source IDs, evidence references and individual confidence are retained in the bundle; identity context is included in the same token budget. Persisted bundle bytes are also
bounded by configured `maxInputBytes`; this shared limit remains the existing N3 configuration
limitation for later synthesis. The default 4,096 context / 16,384 bundle-byte limits retain the
complete G1 four-hop path with its four supporting edge items. Larger requests can abstain.
Persistence must support indexed item lookup; a bundle-only store fails closed.

`WorkflowRunner` composes planner, resolver, parallel retrieval and persisted evidence. It returns
evidence rather than a final answer for both values of `evidenceOnly`; synthesis, verification and
audit execution remain Phase 9C. Graph mode launches no semantic query; vector mode launches no
graph stages and abstains on deterministic graph/numeric requests. Fused mode can return a qualified
partial result when optional semantic retrieval fails and essential deterministic evidence survives.
An essential-stage failure abstains; evidence persistence/index failure is a typed workflow failure.
Each future has its own absolute stage deadline and completion timestamp within the synchronous
deadline, so collecting a slow sibling cannot invalidate a result that completed on time. Deadline
expiry cancels and interrupts the task; shutdown waits at most the smallest configured stage budget and the remaining overall deadline.
Injected adapters must honor interruption or their own request timeout: Java cannot forcibly stop
an uncooperative port. No production latency or live provider behavior is established by these tests.

The module fixture transcribes the ten original G1 identities, nine canonical works and nine
all-years edges with literal expected metric values. A→G is A→C→D→F→G (four hops); H/I form a
separate component, and J is solo. Declared community labels, venue/topic/institution metadata and
`Name 0001` / `Name 0002` aliases are synthetic overlays, not real enrichment or clustering.
The independent test fixture separately exercises complete authoritative metadata and real artifact
readers. Confidence remains absent when the real loader has no confidence; synthetic values do not
establish calibrated identity confidence. Phase 8C remains deferred to Phase 14C.

## Phase 9C synthesis, verification, audit and offline CLI

`RuntimeAnswerWorkflow` composes the existing retrieval runner with `AnswerSynthesisAgent`,
`ClaimVerificationAgent` and the injected `RuntimeAuditStore`. The retrieval-only API remains
available for experiments. Evidence-only full-workflow runs skip synthesis and verification calls
but still require an `EVIDENCE_ONLY` audit. A terminal result is returned only after the audit
payload and its indexed query lookup are readable. The adapter uses existing object/session ports;
there are no new tables, indexes or infrastructure. A required audit write/read failure returns a
typed failure, including after otherwise successful synthesis. Unsupported requests, ambiguous
identities, missing evidence and malformed synthesis are audited with their closed outcome/reason.
Ambiguous-name abstentions return the bounded candidate list with display names and source context;
the reason discloses total/truncation, and candidates are not recorded as resolved identities.
The abstention response hash includes this candidate list.
The audit retains proposed and rejected claims, per-claim verdicts/reasons, plan when available,
source run/version/evidence IDs, prompt/model versions, usage when supplied, latency and the hash
of the complete final answer. Pre-plan outcomes use an optional record rather than a fabricated plan.

Each synthesis request carries a `claimScaffold`: the exact verifiable claims (claimType, templateId,
subjectIds, windowIds, evidenceIds and typed values) for every deterministic evidence item,
computed from `ClaimContract`, the same field rules `ClaimVerificationAgent` applies, so the
two cannot drift. It is empty in vector mode, skips unrequested windows and descriptive evidence,
and is bounded separately from the evidence context: at most `retrieval.contextTokenBudget` bytes
and never more than the room left under `requestBytes`; whole claims are dropped, never cut. The
prompt tells the model to return only the relevant scaffold `claimId` values in the optional
`selectedClaimIds` (leaving `claims` empty, `narrativeClaimIds` the same ids, `interpretation`
empty); `AnswerSynthesisAgent` expands each id from that request's exact scaffold into the full
claim before the unchanged verifier runs. Own claims plus selected scaffold claims are
de-duplicated by `claimId` (the scaffold version wins when both appear), unknown ids are ignored
and counted in `SynthesisProposal.ignoredSelectedIds`, and an empty `narrativeClaimIds` defaults to
the selected ids. Verbatim copies in `claims` remain accepted. `synthesis-v1` was edited in place (the version is configured in core, not in this module).

Synthesis uses the versioned `synthesis-v1` prompt and `scholarchain.runtime.synthesis.v1` schema,
with forced `submit_answer` tool use through the same configured Bedrock Converse port. The stage
allows at most one malformed-output retry inside its total configured deadline. Tests and the CLI
use scripted clients; no Bedrock request is made. Model output supplies only typed proposals and
narrative claim IDs. Factual prose and model uncertainty text are never trusted as answer facts.
The deterministic verifier checks allowlisted claim fields and templates against evidence IDs,
subjects, windows and exact stored values. It rejects missing evidence, wrong values, fabricated
identities, unrelated evidence kinds and unrequested total-author conversions. Vector evidence
cannot authorize deterministic graph or numeric claims. Rejected proposals remain in the audit;
only fully verified claims are rendered. Mixed claim outcomes remain partially verified, while no
accepted claims yields `ABSTAINED`.

Factual templates render verified fields and source qualifications. Convergence/iteration labels
apply to community-derived fields, rather than exact publication/coauthor counts. A separate
component distance estimate remains approximate and carries stored sample count, seed, mean and
reached-pair count with source references. Maximum coauthors excludes the researcher; explicitly
requested total authors is labeled as coauthors plus one. Weighted degree equals total coauthor
occurrences and is not independent corroboration; repeated collaboration is the individual edge's
joint-publication count. Optional interpretation uses a deliberately narrow generic vocabulary;
numbers, identifiers, names and unknown words are rejected. Accepted interpretation is labeled.
This is a conservative coverage boundary, not evidence of general live-model injection resistance.

Stored evidence uses source-derived lineage/provenance, without copying request snapshot/date/
license values into facts. The request retains its own plan/audit provenance. Semantic source
provenance comes from the verified document/run/pointer; unknown dates/licenses remain absent.
Named semantic retrieval includes the resolved entity constraint; multiple resolved subjects without
an available multi-entity filter return Unsupported. Verified identities and audit resolved IDs use
resolver candidates and deterministic subjects, never subjects chosen only by semantic similarity.
Path-status context retains the researcher pair even when no path exists. Deterministic evidence
cannot contain a descriptive excerpt. The planner also recognizes natural temporal "change from"
phrasing and community comparisons while preserving exact window/metric/filter intent checks.

The runtime configuration separates question, prompt, total request, output and persisted-bundle
byte limits. Omitted `byteLimits` preserves the legacy shared `maxInputBytes` behavior. Context
remains bounded by its conservative UTF-8-byte token upper bound. Full workflow deadlines reserve
configured audit time inside the same synchronous deadline. Interruptible tasks are cancelled on
expiry; injected ports must honor interruption or their own timeout. Java cannot forcibly stop a
port that ignores interruption. Larger atomic evidence groups can still abstain, and strict missing
authoritative metadata can produce Unsupported. Live compatibility and production latency remain
unverified.

The offline CLI accepts only:

```sh
sbt -batch 'rag/runMain edu.uic.cs441.scholarchain.rag.RuntimeWorkflowMain --benchmark'
```

Use the prescribed JDK 17 environment from the phase plan for every sbt command. An optional
`--evidence-only` flag skips synthesis. The CLI never constructs provider clients or reads credentials.
Its scripted proposals are defined for the versioned benchmark questions; other safe questions may
abstain rather than fabricate a response. `runtime-benchmark-v1.json` contains the 12 required query
families plus institution, venue and disconnected-path cases. Numeric expected values are literal,
hand-derived G1 facts; only evidence IDs are bound dynamically. `RuntimeOfflineFixture` preserves
the original G1 graph and uses explicitly synthetic community, metadata and homonym overlays.
The temporal comparison uses declared stored fixture rows. These tests establish offline
correctness, not real metadata coverage, model quality or live injection behavior. Broader fault/
injection suites remain Phase 11B. Phase 8C remains deferred to Phase 14C.

## Phase 14 provider configurations (Anthropic and Voyage, Bedrock retained)

Bedrock quota restrictions blocked the planned Bedrock models. The instructor approved the
Anthropic API for synthesis and Voyage AI for embeddings; infrastructure and processing stay on
AWS. Both Bedrock paths remain selectable. Exactly one provider per capability is active at a time.

| Capability | Switch (env, read by `modules/services`) | Default | Alternative |
|---|---|---|---|
| Synthesis and planner LLM | `SCHOLARCHAIN_SYNTHESIS_PROVIDER` | `anthropic` | `bedrock` |
| Embeddings | `SCHOLARCHAIN_EMBEDDING_PROVIDER` | `voyage` | `bedrock` |

The model ids below are DEFAULTS, not pins (plan rule 6.7, configuration not constants). The
synthesis model id is `RuntimeConfig.model.modelId`; the embedding model id, version tag and
dimension are the configured `EmbeddingModel` (for ingest and smoke, `LiveEmbeddingConfig.model`).
Endpoints, limits, price and cap are constructor or config parameters. The defaults live in
exactly one object per provider, `AnthropicDefaults`, `VoyageDefaults` and `BedrockDefaults`
(`ProviderDefaults.scala`), each with a one-line rationale and source.

| Configuration | Default provider and model id | Default dimension | Key env (read by services) |
|---|---|---|---|
| Synthesis `anthropic` | Anthropic Messages API, `claude-haiku-5-5` | not applicable | `SCHOLARCHAIN_ANTHROPIC_API_KEY` |
| Synthesis `bedrock` | Bedrock Converse, the configured model id (Haiku 4.5 per the Bedrock plan) | not applicable | none (IAM) |
| Embeddings `voyage` | Voyage AI, `voyage-4-lite`, version tag `voyage-4-lite` | 256 | `SCHOLARCHAIN_VOYAGE_API_KEY` |
| Embeddings `bedrock` | Titan Text Embeddings V2, `amazon.titan-embed-text-v2:0` | 256, 512 or 1024 as configured | none (IAM) |

### Selecting a configuration (service wiring)

`SynthesisProvider.parse(Option[String])` and `EmbeddingProvider.parse(Option[String])` turn the env
values into a provider (unset or blank selects the default; an unknown value is a closed code that
does not echo it). Then:

- `SynthesisClients.runtimeConfigFor(provider, runtimeConfig, modelId)` returns the config to use
  for the client and every agent with the configured model id set; nothing is forced. The
  two-argument form returns the config as given.
- `SynthesisClients.create(provider, config, anthropicApiKey: Option[String], bedrock: () =>
  BedrockRuntimeClient, anthropic: AnthropicSettings = AnthropicSettings())` returns
  `Either[String, LlmClient]`. The Bedrock client is a thunk, so the Anthropic path never builds an
  AWS SDK client. `AnthropicSettings` holds the endpoint, API version, prompt-token limit,
  max_tokens factor and bytes-per-token estimate.
- `EmbeddingClientFactory.create(provider, inputType, voyageApiKey, bedrock, bedrockConfig,
  counter, voyageConfig: Option[VoyageEmbeddingConfig] = None)` returns
  `Either[String, ProviderEmbeddingClient]`. `VoyageEmbeddingConfig` holds the configured model,
  endpoint and per-request limits. Use `EmbeddingInputType.Document`
  for ingest and `EmbeddingInputType.Query` for queries, and share one `EmbeddingSpendCounter`
  (`EmbeddingPricing.newCounter(provider)`) between them.

API keys are constructor arguments. The services read the two env values; no key is read from a
file here. A key never appears in a log, `toString`, exception message, result or evidence:
`AnthropicApiKey` and `VoyageApiKey` print as `REDACTED`, reject unsafe values with a closed code and
are never echoed from provider responses.

### Anthropic path: `AnthropicMessagesLlmClient`

Posts to `https://api.anthropic.com/v1/messages` with the JDK `HttpClient` and ujson only (no
retries, no redirects, plain http only for loopback tests). The Haiku 5.5 request rules below are
implemented for whichever Anthropic model is configured; they are properties of the API calls, not
of one model id.

- The model id is `RuntimeConfig.model.modelId` (default `claude-haiku-5-5`) and the response
  `model` must equal it.
- It never sends `temperature`, `top_p` or `top_k`, even though the runtime config carries
  `temperature` 0.0. **The Anthropic path cannot use temperature 0**, so identical inputs can give
  different outputs; Bedrock keeps the configured temperature. Nothing here claims determinism.
- It forces the single named tool with `tool_choice`, sends no assistant prefill and never sets
  `strict`. Top-level `$schema`, `$id` and `title` are stripped from the tool schema.
- `max_tokens` is the configured output budget times `maxTokensFactor` (default 1.3: the tokenizer
  produces about 30% more tokens than Haiku 4.5).
- Content blocks are read by `type`. `thinking`, `redacted_thinking` and `text` blocks are ignored,
  any other type is refused, and exactly one `tool_use` block with the requested name is accepted.
- `stop_reason` `refusal` is the typed `llm-refusal` failure. It is not retried: the client never
  retries, the planner falls back and synthesis abstains.
- A prompt estimated at `promptTokenLimit` tokens or more (default 100,000, the price tier
  boundary; the estimate is one token per `bytesPerEstimatedToken` UTF-8 bytes, default 3, of
  system prompt, data and schema) is refused with `llm-prompt-too-large` before any call.
- A response `model` that differs from the configured id is refused (`llm-model-mismatch`).

**Data leaves AWS on this path.** The question text and the evidence snippets inside the prompt are
sent to Anthropic. Billing is outside AWS; AWS budgets do not cover it. Live tool-use acceptance,
model id spelling and latency are unverified until a human-gated live check.

### Voyage path: `VoyageEmbeddingClient`

Posts to `{baseUri}/v1/embeddings` (default `https://api.voyageai.com`) with the configured `model`
id and `output_dimension` (defaults `voyage-4-lite`, 256), `input_type` `document` (ingest) or `query` (queries) and `truncation`
false, so an over-long text is a typed failure and never a shortened vector. A request holds at
most `maxTextsPerRequest` texts and `maxTokensPerRequest` estimated tokens (defaults 1,000 and
1,000,000; one token per UTF-8 byte, a strict upper bound); larger inputs are split in order. One
text may be at most `maxInputTokens` estimated tokens (default 32,000). The model must be in the
`voyage-*` family and its dimension in `supportedDimensions`. HTTP 429, 5xx and
transport errors retry with backoff; other statuses are permanent. **Document text and query text
leave AWS on this path.**

### Vector consistency and re-embedding

Stored and query vectors must share provider, model, version tag and dimension.
`VectorConsistency` refuses any difference with a typed code (`vector-consistency-provider-mismatch`,
`-model-`, `-version-`, `-dimension-`), and `LiveEmbeddingIngestMain` and `LiveEmbeddingSmokeMain`
check the embedder against the configured model before any port is used. Changing the embedding
model requires a full re-embed and an index rebuild; Titan and Voyage vectors must never share an
index. 14C ingest and query smoke use the same configured values (defaults: model id
`voyage-4-lite`, version tag `voyage-4-lite`, dimension 256, from `LiveEmbeddingConfig.model`). `LiveEmbeddingConfig.embeddingProvider`
is optional: empty infers the provider from the model, and a provider whose naming family does not
own the model (`voyage-*` is Voyage) is refused with `embedding-provider-model-mismatch`. The live mains read `SCHOLARCHAIN_VOYAGE_API_KEY`
from the environment only when `voyage` is selected, and build the Bedrock SDK client only when
`bedrock` is selected.

### Embedding cost bound

The bound is provider-aware and configured. `LiveEmbeddingConfig.assumedUsdPerMillionEmbeddingTokens`
(default USD 0.02 from `VoyageDefaults`) prices the token bound, and `embeddingCapUsd` (default USD
0.30) is the cap: tokens times attempts at that price above the cap refuses with
`live-assumed-cost-or-request-bound`. At runtime `EmbeddingSpendCounter` (price and cap from the
config, or the provider defaults through `EmbeddingPricing.newCounter`) refuses a request that
would pass the cap, 15,000,000 tokens at the defaults, before it is sent. The first 200M Voyage
tokens per account are free, but the counter and every bound still price all tokens. The counter
is a local control and not the provider invoice.

### Query-embedding cache: `CachingEmbeddingClient` (P40)

Purpose (session-2 plan P40, finding F25): the semantic route embeds every question, and the
elasticity load repeats a fixed set of about 100-200 questions, so without a cache every request
calls Voyage. `CachingEmbeddingClient(underlying, maxEntries)` wraps the query client and calls it
once per distinct question while the entry stays cached. It is a decorator only; wiring, the size
setting and `/metrics` belong to the services.

- **Identity.** It reports the underlying `model` (id, version, dimension) and `provider` unchanged
  (a client without a declared provider gets the one `VectorConsistency.checkClient` would infer),
  so the startup consistency check gives the same answer with or without it.
- **Keying.** Underlying provider and model tag plus the SHA-256 of the exact text (no trimming or
  case folding). The clear text is never stored in a key. The `EmbeddingClient` interface has no
  query/document input type; it is fixed when the underlying client is built, and one cache wraps
  one client, so wrap the query client only.
- **Bounds.** In-memory LRU per process, `maxEntries` > 0 (default
  `CachingEmbeddingClient.DefaultMaxEntries` = 1,024), least recently used evicted first, no TTL.
  Memory is roughly entries x dimension boxed floats (about 5 MB at 1,024 x 256).
- **Calls.** One underlying call per `embed` with only the distinct misses, in first-occurrence
  order; none when every text hits. Results keep input order and cardinality.
- **Counters.** `stats: EmbeddingCacheStats(hits, misses, evictions, size, capacity)`, read under
  the cache lock. `misses` equals the number of texts sent to the underlying client; `hits` counts
  input texts answered without their own underlying request. The counters never decrease.
- **Not cached.** `EmbeddingFailure` results; a success with another model, wrong dimension or a non
  finite value (then nothing from that response is cached and it is returned unchanged); null
  texts (passed through each time). If the underlying client throws, the exception propagates
  unchanged and nothing is cached; a wrong-length or null-element response throws
  `IllegalStateException` with the closed code `embedding-cache-result-count-mismatch` or
  `embedding-cache-null-result`, and nothing is cached. A failed text is retried on the next call.
- **Concurrency.** Thread-safe; the underlying call runs outside the lock. Racing misses for the
  same text are not coalesced: each racing thread may call the underlying client once (each counts
  as a miss, the later insert replaces the earlier one), so warm-up can cost up to one extra call
  per concurrent request for a question. Cached results keep the original `attempts`.
- **No text in output.** Nothing logs; `toString` and `stats` show identity and numbers only.

`CachingEmbeddingClientSpec` covers these rules with a counting in-memory fake.

### Tests

`AnthropicLlmSpec`, `VoyageEmbeddingSpec`, `ProviderSelectionSpec` and `LiveEmbeddingProviderSpec`
use fake HTTP (an in-process loopback server) and synthetic placeholder keys only. No AWS, Anthropic
or Voyage call is made.

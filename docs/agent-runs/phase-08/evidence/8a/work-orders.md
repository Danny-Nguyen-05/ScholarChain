# 8A bounded delegated work orders and handoffs

Common constraints sent to every owner: read the phase plan, approved prompt, root instructions and role/map; one writer per owned class; no nested delegation, reviewer launch, secret access, live AWS/provider call, commit, push, or human decision edit. Coordinator alone assembles phase evidence. The shared sbt slot belongs to coordinator; owners request exact formatting/tests and do not launch builds concurrently. Native agents inherit parent model; exact deployed version is not exposed.

## Domain work order — /root/domain_engineer

Own modules/core/** only. Add embedding document/work item/metadata/model/result/context wire contracts, validation, wire snapshots and meaningful module tests, without existing schema or ID formula changes. Put shared EmbeddingClient port in core to avoid storage -> RAG cycle. Publish signatures before implementation completes; coordinate with storage/test. Model ID/version/dimension are identity. Preserve source refs/template/chunk/window/run/hash and ordinary S3 pointers. Context is descriptive and cannot authorize graph or metric claims.

Handoff: EmbeddingContracts.scala and fixed signatures sent to storage/test before their dependent implementation; optional closed identityFields appended without breaking positional signatures. Exact Phase7 length-framed key uses chunk/profile documentId, original entity retained metadata. Follow-up correction: codepoint excerpt limit and exact emoji boundary regression, same owner.

## Build work order — /root/build_engineer

Own build.sbt/project/** only. Add pinned-version SQS dependency to storage, Bedrock runtime to rag; independentTests depends on rag. Preserve check behavior/live exclusions; no version-only changes or unrelated build edits. Hand off requested scalafmtSbt/compilation commands, then free slot.

## Independent test work order — /root/test_engineer

Own tests/** only. FIRST repair7C-L2 character literals and executable string interpolation in RuntimeGraphFence with meaningful adversarial regressions. Wait for observed prerequisite gate before RAG production code. Then interface-first independent8A tests with hand-derived expectations/synthetic provenance for core/rendering/chunks/fake/queue/manifest. Do not author8B CLI/five-query smoke/live packet. Never edit production or module-local tests.

Handoff: prerequisite8/8 at0 runtime roots before RAG launch; independent23/23 later at3 runtime roots. Test owner requested coordinator formatting.

## Separate storage work order — /root/storage_engineer

Own modules/storage/** only, including module tests and README. Implement EmbeddingWorkQueue port/fake/SQS injected adapter with exact stubbed request tests; bounded manifest runner accepting core EmbeddingClient by injection. Write canonical authoritative JSON to ordinary S3; pre-embed hash/model unchanged skip and same-key changed-text conflict. Use Phase7 VectorStore.putBatch and immutable ArtifactRegistry semantics. Retain RunLedger failures/retry counts and bounded counters/per-index/throughput/calls/rejected report. No ensureIndex provisioning in runner. Prepared-vector checkpoint must prevent re-embedding after ambiguous success. Preserve supplied compact source/topic/institution identity metadata only. No8B CLI, five-query suite or live command/template.

Integration follow-ups routed to same owner: eliminate nonexhaustive guarded match; canonical full-JSON/provenance pointer addressing and stable map ordering; completed same-text/model replay retains first immutable provenance, while incomplete changed pointer rejects; enforce SQS1MiB aggregate bound before SDK; structured JSON count-only log and completion-registry failure replay. Owner requested all storage formatting/gates; no coordinator production authorship.

## Separate RAG work order — /root/rag_engineer

Own modules/rag/**, with prompts/runtime/** and prompts/schemas/** only if needed (none used). Launched AFTER prerequisite8/8 passed. Build deterministic five-type templates from source/computed rows, explicit permitted abstract/fallback selection/provenance, stable chunk policy/IDs. Implement normalized hashed bag-of-words fake and injected Bedrock TitanV2 adapter using configured ID/version/dimension/region/limits/concurrency/retries/backoff and typed per-item order/cardinality. Add semantic context construction/verification and meaningful module tests. Copy actual source fields/numbers; never infer IDs, edges or metrics. Shared core interface, no reverse module dependency. No8B five-query smoke/CLI/live packet.

Integration follow-ups routed to same owner: bind chunk policy/template/window into stable IDs; bound concurrency across concurrent embed calls; codepoint context limits coordinated with core; make score semantics explicit (negative distance). Tests use SDK proxies and fakes only. Region remains configured us-east-2, planned TitanV2/256/cosine provisional until provisioning.

All source owners returned final reports and froze edits before final full gate. No reviewer was launched.

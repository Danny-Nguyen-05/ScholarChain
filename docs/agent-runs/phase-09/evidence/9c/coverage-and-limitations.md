# Subphase 9C coverage and limitations

This packet reports offline correctness with scripted LLMs and fake stores. It is not live-model quality, injection-resistance, production-latency, or real-enrichment coverage evidence. Independent external review is pending. Phase 8C remains deferred to Phase 14C; Phase 8 is not accepted as a whole.

| Requirement | Implementation and meaningful coverage |
|---|---|
| Schema-shaped synthesis | AnswerSynthesisAgent validates the versioned synthesis schema, model identity, narrative references, independent byte caps, and a single bounded retry. Direct-entry question/prompt caps reject before any LLM call. |
| Deterministic decisions | ClaimVerificationAgent checks allowlisted types/templates/fields, evidence identity, subject/window, exact decimal values, conflicting cited facts, complete hop evidence, and explicitly requested conversions. No LLM verifier exists. |
| Safe factual rendering | Templates regenerate facts from accepted fields. Rejected proposals remain in verification/audit; mixed answers retain only supported factual sentences; no supported claim yields ABSTAINED. |
| Interpretation | A narrow generic vocabulary excludes numbers, identifiers, unknown names/words, and known researcher names even when they are also vocabulary words. Accepted text is labeled interpretation. |
| Qualification scope | Exact metric evidence remains approximate=false. Separate component P90 evidence is approximate and carries available sampling details. Iteration-limited labels qualify community-derived claims; exact publication/coauthor counts are not labeled iteration-limited. |
| Provenance and identity | Stored source context supplies source lineage separately from request provenance. Semantic similarity cannot add resolved audit identities or authorize deterministic facts. Named semantic requests retain the entity filter. |
| Evidence partition and context | Runtime deterministic items cannot contain descriptive text. Path status context retains both researchers. Context remains 4,096 by the conservative byte upper bound; persisted evidence has an independent configured cap. |
| Audit | RuntimeAuditStore has real ObjectStore/QuerySessionStore and fake adapters, immutable content-addressed data, conditional namespaced pointers, integrity checks, and retry tests. Required write/read failures fail closed. Attempted/rejected claims, versions/usage, source references, terminal reasons, and answer hashes are retained. Pre-plan outcomes have no fabricated plan. |
| Deadlines and failures | The full workflow reserves audit time inside the synchronous deadline. Tests cover absent evidence, malformed synthesis, unexpected port exceptions, audit failure, cancellation, and evidence-only runs skipping synthesis. |
| Ambiguity | The full terminal result and CLI retain the resolver's bounded candidate list, including both DBLP homonyms. Alternatives remain unselected and do not populate audit resolved IDs; synthesis is skipped. |
| Benchmark and CLI | Fifteen versioned, hand-derived cases run through the fake CLI. Assertions include component identity, B/C coauthors, ordered A-C-D-F-G route, both community sizes, exact ranking values, scope/truncation disclosure, authoritative filters, ambiguity, unsupported requests, injection, and disconnected components. |

The new core contract suite, storage audit suite, module 9C suite and independent 9C suites provide separate checks. Earlier 9A/9B behavior is rerun in the final targeted gate and the full check. Two older 9B stored-bundle byte assertions now use the approved effective persisted-byte cap; their complete-path and model-context assertions remain intact.

## Carried observations

| IDs | 9C disposition |
|---|---|
| N1 | Previously fixed actual-item deterministic/semantic partition; retained. |
| N2 | Strict authoritative metadata coverage remains intentional. Synthetic filter benchmarks are not representative of real enrichment coverage. |
| N3 | Addressed by separate backward-compatible question/prompt/request/output/persisted-bundle limits, including direct synthesis-entry checks. |
| N4 | Actual live SDK region/model/tool/temperature compatibility remains a live gate. |
| N5 | Real loader confidence may remain None; synthetic confidence is not a live confidence claim. |
| N6 | Fixed-v1 prompt asset naming remains a fail-closed coverage limitation. |
| N7 | Some researcher context references remain bounded only by the snapshot cap. |
| N8 | Approved natural temporal and community-comparison grammar added with independent positive coverage and prior intent-preservation regressions. |
| N9 | Historical opening-line clarification already recorded; prior human review text remains unchanged. |
| O1, O2, O3 | Addressed for verifier/audit consumption: field-scoped qualification, actual source lineage, and deterministic/resolved identity scope. |
| O4, O8, O9 | Addressed: named entity filtering, no deterministic excerpts, and researcher pairs in path-status context. |
| O5 | Large atomic groups may still abstain under the 4,096 context budget. Ranking prefixes disclose population and truncation; broader list-prefix redesign is deferred. |
| O6 | Ranking-prefix admission still selects on context before the final persisted-byte check; a small configured persisted cap may abstain instead of admitting a shorter prefix. |
| O7 | Shipped adapters still report same-component empty bounded searches as NoPathWithinLimit; no disconnection is inferred. |
| O10 | The broader independent filter-then-rank discrimination case remains deferred; authoritative population logic and filter benchmarks retain existing coverage. |
| R1 | Available P90 sample count/seed/mean/reached-pair values and references added. Evidence type remains RESEARCHER_PROFILE for the component subject; typed distance-estimate kind controls verification. No new type hierarchy introduced. |
| R2 | New final evidence uses normal spaces. Prior reviews and human decisions remain unedited. |

No live smoke was authorized or run. All provider compatibility, quality and general injection behavior remain unverified. Ports that ignore interruption require their own adapter timeouts; Java cannot forcibly terminate them. Audit storage can leave an unreferenced object after pointer publication fails; identical retry repairs the pointer. Exact-envelope replay is supported; a different envelope for an existing query ID conflicts. The CLI scripts versioned benchmark questions; other safe questions can abstain. Broader injection and fault suites remain Phase 11B. No Phase 10 work is included.

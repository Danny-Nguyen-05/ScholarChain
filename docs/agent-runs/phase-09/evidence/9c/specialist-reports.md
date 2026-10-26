# Subphase 9C specialist handoffs

Coordinator-assembled handoffs from native specialists. Final full-check results are recorded separately; these handoffs do not claim an unobserved pass.

## Domain contract gaps

STATUS: COMPLETE; source paths frozen.
OWNER: /root/domain_9c, domain-engineer.
WORK ORDER: Approved additive byte-limit, source-context, deterministic-text and audit-envelope contract gaps only.
FILES CREATED: RuntimeAuditValidation.scala and Runtime9CContractSpec.scala.
FILES MODIFIED: RuntimeConfig.scala, RuntimeContracts.scala, SparkAnalyticsValidation.scala, runtime config resource, RuntimeContractSpec.scala and core README. Exact eight paths are in source-files.json.
COMMANDS RUN: Owner inspected/edited its paths; coordinator serialized formatting and tests.
TEST RESULTS: Core targeted gate passed 50 tests, zero failed. Eleven new 9C contract cases; full gate pending at handoff.
VALIDATION RESULTS: Optional/defaulted contracts preserve legacy decoding and ABSTAINED. Independent caps fall back to legacy maxInputBytes. Audit validation preserves rejected/malformed proposals for observability. Existing wire examples unchanged.
ASSUMPTIONS: Domain contracts do not establish adapter durability or live model compatibility.
RISKS: Consumers must enforce runtime budgets and trust partitions.
MANUAL ACTION REQUIRED: Independent review.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Final full check and external review.
NEXT GATE: Coordinator gates and user-launched review.

## Storage contract gap

STATUS: COMPLETE; source paths frozen.
OWNER: /root/storage_9c, storage-engineer.
WORK ORDER: Missing typed audit port, real adapter, fake and tests using existing storage infrastructure.
FILES CREATED: RuntimeAuditStore.scala, fakes/InMemoryRuntimeAuditStore.scala and RuntimeAuditStorageSpec.scala.
FILES MODIFIED: Storage README. Exact four paths are in source-files.json.
COMMANDS RUN: Owner inspected/edited storage paths; coordinator serialized formatting and tests.
TEST RESULTS: Final targeted audit suite passed 14 tests. Initial 13/14 attempt had an incorrect test-only assumption about tiny-envelope versus pointer size; correction and raw log are retained.
VALIDATION RESULTS: Immutable content-bound object, namespaced conditional session pointer, key/hash/size validation, replay/conflict/corruption/readback and retry coverage. No new tables, GSIs or infrastructure.
ASSUMPTIONS: Existing ObjectStore and QuerySessionStore implement their documented durability/conditional-write semantics; audit pointers must not expire.
RISKS: Pointer failure can leave an orphaned object; identical retry repairs it. Replay requires the exact envelope; changed content at the same query ID conflicts. Live infrastructure behavior unverified.
MANUAL ACTION REQUIRED: Independent review.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Final full check and external review.
NEXT GATE: Coordinator gates and user-launched review.

## RAG runtime

STATUS: COMPLETE; source paths frozen after ambiguity correction.
OWNER: /root/rag_9c, rag-engineer.
WORK ORDER: Synthesis, deterministic verification/templates, audit workflow, offline CLI/benchmark and approved evidence-consumption fixes.
FILES CREATED: AnswerSynthesisAgent.scala, ClaimVerificationAgent.scala, RuntimeAnswerWorkflow.scala, RuntimeOfflineFixture.scala, RuntimeWorkflowMain.scala, runtime-benchmark-v1.json and Runtime9CSpec.scala.
FILES MODIFIED: Eleven existing RAG source/module-doc paths. Exact eighteen paths are in source-files.json.
COMMANDS RUN: Read-only inspection and owned-file edits; coordinator ran formatting/builds/CLI. No reviewer, live/provider calls, commits or pushes launched.
TEST RESULTS: Final targeted RAG selection passed 74 tests; offline CLI passed 15/15 with literal expected values and actual ambiguity candidates. Full check 2 was pending at owner handoff; terminated full check 1 retained as exit 143.
VALIDATION RESULTS: Typed proposals and bounded retry; independent entry byte guards; exact deterministic checks and templates; scoped qualifications/provenance/identity; required audit and reserved deadline; benchmark identity/route/list/community assertions; bounded ambiguity candidates retained and included in abstention hash without selecting audit identities. Existing retrieval APIs retained.
ASSUMPTIONS: Ports honor interruption or their own deadlines; synthetic fixture overlays are disclosed.
RISKS: Live compatibility/quality/injection resistance/latency/enrichment unverified; conservative grammar and large atomic groups can abstain. Phase 8C remains deferred to 14C.
MANUAL ACTION REQUIRED: Independent review after gates.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Final full check and external review.
NEXT GATE: Coordinator gates and user-launched review.

## Independent tests

STATUS: COMPLETE; test paths frozen.
OWNER: /root/tests_9c, test-engineer.
WORK ORDER: Independent feature tests and hand-derived benchmark assertions.
FILES CREATED: Six IndependentRuntime9C fixture/spec files under tests/**.
FILES MODIFIED: IndependentRuntime9BEvidenceSpec.scala and IndependentRuntime9BWorkflowSpec.scala use the approved effective persisted-bundle cap, preserving completeness/context assertions.
COMMANDS RUN: Source inspection and owned-test edits; git diff --check -- tests exited 0. No builds or production edits by owner.
TEST RESULTS: All 85 new 9C cases passed in the coordinator's final targeted selection; independent selection total 211. Full gate pending at owner handoff.
VALIDATION RESULTS: Literal exact facts, component ID, B/C coauthors, A-C-D-F-G route, C=3/D=4 community sizes, qualification/scope disclosures, interpretation/injection/byte/audit/partial/failure controls. Ambiguity tests retain both canonical homonyms, no synthesis, no resolved audit identity.
ASSUMPTIONS: Canonical IDs use the documented domain formula; expected counts/route are hand-derived rather than recomputed by production analytics.
RISKS: Offline scripted correctness only; broader injection/fault suites remain Phase 11B.
MANUAL ACTION REQUIRED: Independent review after gates.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Final full check and external review.
NEXT GATE: Coordinator gates and user-launched review.

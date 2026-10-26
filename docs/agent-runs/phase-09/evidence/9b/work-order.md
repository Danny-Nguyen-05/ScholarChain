# Subphase 9B work order

Base/HEAD f139f9c925b4925864a2c9a33734d869a1929cd2, branch phase-9, initially clean.
Implement only phase9.md Section 8 Subphase 9B: CollaborationMetricsAgent, PathFinderAgent, CommunityAnalystAgent, SemanticContextAgent, EvidenceBuilderAgent and WorkflowRunner; bounded offline G1 fixtures and required module/independent tests. Preserve prior approved planner/resolver behavior and exact numbers/provenance.

Domain owner fixes N1 actual-item partition validation as a contract gap. Storage owner may be invoked only for a concrete missing contract; no infrastructure additions. RAG owns stage/workflow implementations and module tests/fixtures. Test owner owns independent tests/**. Coordinator alone assembles this evidence tree. No nested delegation and no reviewer launch.

9B WorkflowRunner ends at persisted evidence. Do not implement, prepare or draft 9C synthesis, verifier, audit execution, CLI or benchmark suite. No commits/pushes, cloud/provider calls, secret reads or human-owned gate writes. N2-N9 remain deferred except required disclosure and the already appended N9 clarification; N8 may change only if required 9B cases need it.

Use all original ten user decisions and approved 9B defaults (user-answers.md). Read ports/Phase6 stored metric definitions, not fabricated facts. Preserve authoritative population filtering, cross-community-degree default, W==T invariant, jointPublicationCount repetition, coauthor terminology, iteration-limited community qualifiers, approximate P90, explicit component-based disconnection, and vector-only deterministic abstention.

All sbt commands use JDK17 exactly per plan Section2. Root serializes gates, records java-version, exact commands, failures, exits/counts/raw-log SHA256 and source hashes. Run targeted affected tests, touched-project scalafmt, full /usr/bin/time -p sbt -batch check, git diff --check. Stop with complete reviewer prompt; no reviewer is launched.

## Proven contract gap routed during implementation

Existing frozen path IDs bind only ordered researcher IDs; edge IDs bind only edge locator. Reusing those IDs for changed window/run/support/content conflicts with the immutable item-index contract. Domain-engineer owns a minimal additive `RuntimeEvidence.contentBindingVersion: Option[String] = None` and runtime content-bound ID helper/validation. RAG uses it for new precise GraphPath/Metric/CoauthorEdge items, keeping original locator policy versions. Frozen runtime=None and earlier unmarked9A runtime items retain legacy validation; marked new items must match a canonical complete-item hash excluding evidenceId. Unknown markers reject. This is a contract gap permitted by original decision4, not new infrastructure or a v2 hierarchy. Independent tests cover replay/change/tamper behavior.

The content-binding helper applies to all existing EvidenceTypes using their current ID parsers, so identity/community/profile/semantic items also bind complete content. N1 partition rules remain authoritative. Canonical object keys are sorted and array order retained; marker included in the hash. Earlier unmarked records stay compatible.


## Required evidence identity and bounded ranking composition

Persisted evidence must retain source-backed resolved names, per-candidate confidence and provenance, rather than only canonical IDs plus a minimum confidence. Domain owner adds default-empty RuntimeBundleContext.resolvedCandidates as an additive contract gap; builder retains bounded resolver output and includes compact identity data in its context accounting. Legacy wires remain valid. This supports later deterministic name checking without implementing9C.

Default G1 rankings may exceed the context bound at graphLimit25. Builder may retain a nonempty ordered prefix of a ranking with explicit context-returned count/top-K truncation and source scope, instead of dropping essential path/comparison groups or inventing a new population. All retained metrics remain exact and in stored rank order. Non-ranking deterministic groups stay atomic. If the essential minimum cannot fit, abstain typed. Tests cover ordinary default ranking Ready/truncated and complete default four-hop path persistence.

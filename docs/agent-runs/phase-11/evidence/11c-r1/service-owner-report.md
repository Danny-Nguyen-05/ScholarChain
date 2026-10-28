STATUS: COMPLETE (service-owned implementation; coordinator gates pending at handoff)
OWNER: service-engineer /root/service_engineer_11c_r1; inherited model, exact revision unavailable.
WORK ORDER: Phase11C repair round1 batch1 R11C-1/R11C-2 and user-approved R11C-5; no nested delegation.
FILES CREATED: modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/SessionBindingRecoverySpec.scala (4 tests).
FILES MODIFIED: modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala; modules/services/README.md.
COMMANDS RUN: Read-only cat/sed/rg/git inspection and owned apply_patch/Python edits; no specialist sbt/formatter.
TEST RESULTS: Coordinator red-2 executed4/failed4/exit1 on unchanged production and README. Earlier red gate compile-only0tests failed4 ambiguous fixture references; test-owner correction preceded actual reproduction. Passing repaired gates pending at this specialist handoff.
VALIDATION RESULTS: Revision-zero CAS chooses dispatcher; fresh UUID token plus fingerprint/requestId/traceId binds each attempt. Only Written(intended), recursively through Retried, or primary read of exact intended revision/payload schedules. Clean bind rejection leaves recoverable unbound reservation; losing binder replays current state or returns409. Existing retried-create suite unchanged. README distinguishes transient recovery from process-death dispatcher limits. STOPPED WRITING; coordinator may scalafmt owned service sources.
ASSUMPTIONS: QuerySessionStore primary-read and revision-CAS contracts. Token is opaque session payload, no shared/core/storage schema edit.
RISKS: Persistent outages and process death after successful binding remain outside batch guarantees; no live AWS/provider/scale/deployment evidence. Passing gates and external recheck still pending at this checkpoint.
MANUAL ACTION REQUIRED: Coordinator runs formatting/targeted/full JDK17 gates after sequential independent-test handoff, then user launches read-only recheck.
BLOCKED-ON OWNER: None for implementation.
BLOCKED-ON EVIDENCE: Passing affected/full gates and independent recheck.
NEXT GATE: Coordinator gates, handoff, then stop.

Mutation sensitivity (reasoning only, no production mutations):

1. Removing primary reconciliation breaks apply-then-reject completion.
2. Preventing revision-zero replay binding breaks clean-rejection recovery.
3. Losing CAS exclusivity breaks exact one applied binding.
4. Dropping binding-token ownership allows identical client IDs to claim another binder's queued write; concurrent lost-reply case detects a second workflow.
5. Removing fingerprint conflict handling breaks changed-body409.
6. Rescheduling stored-result replay breaks exact one invocation.

Exact module names:

- an applied body-binding write with a lost reply completes exactly once and replays its stored result
- one clean binding rejection leaves the same key recoverable by a replay rather than permanently retryable
- concurrent cross-instance replays with reused client IDs bind and execute once when winner reply is lost=false
- concurrent cross-instance replays with reused client IDs bind and execute once when winner reply is lost=true

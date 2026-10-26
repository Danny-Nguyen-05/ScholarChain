# Subphase 9A

STATUS: COMPLETE
OWNER: `/root` assembles observed execution; `/root/test_engineer` independently authored tests/**.
WORK ORDER: Offline9A only, with hand-derived synthetic expectations and actual fresh producer integration.
FILES CREATED: RuntimeContractSpec(12cases), RuntimeArtifactStorageSpec(11), Runtime9ASpec(20),
IndependentRuntime9APlannerSpec(11), IndependentRuntime9AResolverSpec(6),
IndependentRuntime9AEvidenceSpec(4), IndependentRuntime9AArtifactPipelineSpec(1).
FILES MODIFIED: IndependentStorageLoaderSpec.scala now expects4write/replay rows (approved
base-name alias) and explicitly asserts alias identity/confidence/provenance; existing checks retained.
Centralized mechanical formatting applied.
COMMANDS RUN: See evidence/9a/commands.md for exact environment, commands, attempts and exit codes.
TEST RESULTS: Final combined target exit0;core17/storage11/RAG20/independent22,70passed0failed.
Earlier failures retained and explained in repairs.md; no failing case was removed or weakened.
Full check1 exit1 after724.36s: modules425passed; independent397passed/1failed
on the stale3write count. Affected loader repair target5/5passed. Final full check2 exit0:
831passed0failed in705.87s (core169/Hadoop64/ER39/Spark38/storage62/RAG53/independent398/build8).
The injected format-stage failure is the passing build failure-path self-test, not a final failure.
VALIDATION RESULTS: Frozen byte-for-byte examples still pass; exact typed numbers, verdict/ABSTAINED
mapping, deadline sum, typed payload validation, schema/allowlist/constraint preservation, retry/fallback,
ambiguity/suffix/confidence, stubbed forced tool use, sanitized logging, bounded source artifacts,
filter-before-ranking, qualifications, evidence-index integrity and actual Phase6 producer compatibility.
ASSUMPTIONS: Scripted models/stubbed SDKs only. Actual G1 producer uses synthetic direct inputs;
it proves artifact compatibility, not real acquisition, provider quality or a cloud deployment.
RISKS: Independent review pending; no9B/C workflow/verifier/benchmark behavior claimed. Broader injection/fault
suites remain Phase11B; current tests prove deterministic controls only.
MANUAL ACTION REQUIRED: User launches independent read-only review after coordinator final gate.
BLOCKED-ON OWNER: None for targeted validation.
BLOCKED-ON EVIDENCE: None for local9A gates. Live model compatibility/quality deliberately unverified.
NEXT GATE: User-launched independent read-only9A review; source hashes and git diff --check verified
after the final gate. No further test run or next-subphase work is pending in this session.


# Subphase 9A repair round 1

STATUS: COMPLETE
OWNER: /root evidence/execution; module owners author module tests; /root/test_engineer authors tests/**.
WORK ORDER: Only B1–B4 blocking repairs; N1–N7 deferred. No9B preparation or live calls.
FILES CREATED: Runtime9ARepairSpec(20), IndependentRuntime9ARepairPlannerSpec(37),
IndependentRuntime9ARepairResolverSpec(5).
FILES MODIFIED: RuntimeContractSpec(+4), RuntimeArtifactStorageSpec(+4), Runtime9ASpec
ambiguity pattern; IndependentRuntime9AResolverSpec ambiguity pattern/disclosure assertions.
COMMANDS RUN: All exact JDK17 commands, failed attempt and exits in evidence/9a-r1/commands.md.
TEST RESULTS: Core21/storage15/RAG40/independent64=140passed0failed. First RAG target failed
compilation only (helper execute default getter collided with ScalaTest); renamed test helper,
no production change. Full check exit0,725.07s,901passed0failed after formatting/source freeze:
core173/Hadoop64/ER39/Spark38/storage66/RAG73/independent440/build8. Expected injected
format failure is the passing build failure-path self-test. All34frozen source hashes unchanged.
VALIDATION RESULTS: Hand-derived positive/negative metric/measure cases, configured defaults,
exact cumulative/explicit/default windows, conversion guard, canonical counting and bounded
provenance, candidate overflow disclosures, actual artifact stored-window absence, first-load
corruption refusal, retryable failed load, warm/concurrent mixed six-port reads with oneGET.
ASSUMPTIONS: Offline scripted LLM/stub SDK/fake stores; actual G1 producer direct synthetic inputs.
RISKS: Structural cache tests do not measure production latency. No real-model quality/injection
resistance, broader N1–N7 repairs,9B workflow or9C verifier/benchmark claim.
MANUAL ACTION REQUIRED: User launches independent read-only recheck after final gate.
BLOCKED-ON OWNER: None for targeted tests.
BLOCKED-ON EVIDENCE: None for local gates; user-launched independent recheck pending.
NEXT GATE: User-launched read-only repair recheck. Source integrity and git diff --check verified;
all jobs/specialists completed. No extra tests or next-subphase work are pending.


## 2026-10-26 — approval recording only

No tests rerun and no source edits. The user-supplied read-only reviewer returned APPROVE,
verified retained140targeted/901full results and hashes, and reported B1–B4 FIXED.
Coordinator reverified all34source hashes and git diff --check exit0 after evidence-only writes.
Next gate is the user's9A commit;9B remains unstarted.

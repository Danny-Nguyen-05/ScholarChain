STATUS: COMPLETE (independent test edits ready; coordinator gates pending at handoff)
OWNER: test-engineer /root/test_engineer_11c_r1; inherited model, exact revision unavailable.
WORK ORDER: Phase11C repair round1 batch1 independent HTTP regressions for R11C-1/R11C-2 only.
FILES CREATED: None.
FILES MODIFIED: tests/src/test/scala/edu/uic/cs441/scholarchain/independent/AdversarialRuntimeHttpSpec.scala only.
COMMANDS RUN: Read-only cat/sed/rg/git diff --check/git diff --stat/shasum and owned apply_patch. Owned whitespace check exit0. No sbt/formatter/production/docs edits.
TEST RESULTS: Not run by this specialist. Source counts HTTP7 (previous6), Runtime18 (Boundary3/Workflow8/HTTP7), net+1 independent test. Passing coordinator gates not yet observed at handoff.
VALIDATION RESULTS: Replaced permanent-503 expectation with reject-first-bind recovery; added apply-then-Retried conditional-conflict HTTP case. Actual HTTP→QueryService→runtime adapter/workflow; counters observe QueryWorkflow.run and LLM calls. Both require exact verified publicationCount3, ANSWERED audit, primary persisted SUCCEEDED/result, same-key stored replay equality/unchanged audit/no rerun, changed-body409 and exactly one applied binding. Initial clean rejection requires0 workflow/model calls and0 applied bindings; replay requires2 bind attempts/1 apply. Lost reply fake actually applies initial bind then returns Retried(1,Rejected("conditional-conflict")); requires1 bind attempt/1 apply. Supports200 directly or authenticated bounded202 job-result polling. STOPPED WRITING; coordinator may scalafmt owned source.
ASSUMPTIONS: Synthetic fixture's hand-derived count3; module tests supply deterministic cross-instance concurrency, so HTTP edit does not duplicate concurrency fixture.
RISKS: No live DynamoDB/provider/durable dispatcher evidence; coordinator compilation and affected/full gates remain pending at handoff.
MANUAL ACTION REQUIRED: Coordinator formats, runs requested gates, assembles evidence; user launches independent recheck.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Coordinator format/targeted/full JDK17 gates.
NEXT GATE: Frozen-source gates then external read-only review.

Names and coverage:

- Replaced historical name: Dynamo conditional body-binding conflict fails HTTP closed before any runtime execution
- Replacement: one rejected Dynamo body bind recovers through same-key HTTP replay and executes exactly once
- Added: an applied Dynamo body bind with a lost reply completes through HTTP and stored replay without rerunning
- Category16: existing2/new4/total6; category17: existing2/new5/total7; other mappings unchanged. Runtime selected21existing+18new=39; combined selected51existing+33new=84. Four module regression tests are additional coverage, listed separately.

Mutation thought checks (reasoning, not executed mutations):

1. Removing primary reconciliation makes applied-lost-reply completion fail503.
2. Refusing revision-zero replay binding makes clean-rejection recovery fail503 and misses2 bind attempts.
3. Executing after clean rejection violates initial zero invocation counters or final exact-one counters.
4. Rescheduling completed replay violates workflow/model counts and audit equality.
5. Removing fingerprint conflict handling misses required409.
6. Returning empty/unsupported answer fails exact verified count3.
7. Returning success without persisted terminal result fails primary SUCCEEDED/result equality.

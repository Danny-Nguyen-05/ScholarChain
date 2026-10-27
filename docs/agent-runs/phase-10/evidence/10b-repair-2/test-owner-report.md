STATUS: COMPLETE (owned tests and targeted gates; full gate separately reported)
OWNER: test-engineer /root/test_10b; centrally observed results assembled by orchestrator
WORK ORDER: Subphase10B repair round2 F6 residual equal-budget regression.
FILES CREATED: tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BEqualBudgetSpec.scala
FILES MODIFIED: Existing IndependentServices10BLifecycleSpec.scala and IndependentServices10BDeadlineSpec.scala, only GraphEndpoints test-double budget overload forwarding. Existing assertions/counters/correlation remain.
COMMANDS RUN: Owner inspected scope/review/source/hash/diff (exit0). Root ran every JDK17 formatting/red/green/full gate with pre-run source hashes. Exact command metadata retained separately.
TEST RESULTS: New3cases. Pre-fix3run/1pass/2fail, both omitted and explicit300ms budgets caused3snapshot executions for4requests. Cursorcasepassed. Post-fix3/3, complete independent44/44 in8suites, services36/36 in6suites, packaging passed,exit0,20.061s. New independent regression source identical to formatted red text. Fullcheck results reported separately.
VALIDATION RESULTS: Actual GraphApi with blocking interruptible snapshot behind real HTTP layers has equal graph/proxy300ms caps. Four-request bursts use no interleaved readiness, preservecallertrace,returnnonretryablemarker,onebackendexecutioneach,CLOSED beforeprobes,thenready200/normalsuccess. Explicit cap and omitted timeout both covered; cursor replay stable. Prior refusal/no-response/unready503 and1ms marker guards remain passing.
ASSUMPTIONS: User authorizedF6only and deterministic response reserve.
RISKS: Local behavior is not a live network/readiness guarantee; F16 remains carried.
MANUAL ACTION REQUIRED: User launches independent recheck after final root gate.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for targeted requirements; fullgate separately recorded.
NEXT GATE: Final JDK17 fullcheck, rebuilt-image evidence and user-launched recheck.

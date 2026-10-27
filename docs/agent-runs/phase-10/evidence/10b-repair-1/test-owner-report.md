STATUS: COMPLETE (owned test implementation and observed targeted gates)
OWNER: test-engineer /root/test_10b; central results assembled by orchestrator
WORK ORDER: Subphase10B repair round1, F6 independent HTTP acceptance/outage tests only.
FILES CREATED: tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BDeadlineSpec.scala
FILES MODIFIED: None outside the new file.
COMMANDS RUN: Owner read review and relevant sources, checked scoped diff and hashes. Root centrally ran JDK17 formatting, red, initial green and final strengthened targeted gates. Exact commands/results in *-result.json and commands.md.
TEST RESULTS: New4cases. Pre-fix4run/3pass/1fail. Initialgreen4/4; final strengthened gate services31/31 and independent10A/B41/41 across7suites,exit0,9.973s. Fullcheck separately reported by orchestrator. Original red source retained; final positive ordering strengthened after first green.
VALIDATION RESULTS: Four deadline HTTP requests execute once each and return typed504 GRAPH_DEADLINE_EXCEEDED retryable:false with caller trace. CLOSED is asserted before any readiness probe, then readiness200 and normal node/neighbors success. Refusal, silent-listener client timeout, and unready503 still open circuit and fail readiness without subsequent backend calls through the open breaker.
ASSUMPTIONS: Authenticated loopback stub represents the typed graph deadline; no live backend/provider.
RISKS: Local deterministic HTTP behavior only; existing nonblocking findings remain out of scope.
MANUAL ACTION REQUIRED: User launches independent recheck after root full gate.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Root final full-check evidence pending at report checkpoint.
NEXT GATE: Final JDK17 check, rebuilt-image evidence, then user-launched read-only recheck.

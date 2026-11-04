# Subphase 10B repair round 2 handoff

STATUS: COMPLETE — implementation and local gates; independent recheck pending.
OWNER: Orchestrator assembling service, independent-test and build owners.
WORK ORDER: F6 residual only, explicitly authorized by the user.
FILES CREATED: Two regression suites and this evidence subtree.
FILES MODIFIED: Seven service artifacts, two independent test doubles and phase reports.
Repair-only 11 source files; aggregate 35. Exact paths/owners/hashes: repair-files.json,
source-files.json, files.json and final-validation.json.
COMMANDS RUN: Exact commands/exits/times/hashes in commands.md and named gate result JSON.
TEST RESULTS: Targeted36/36 service tests,44/44 independent tests; full1216/1216 in149 suites,
exit0, JDK17.0.20.1, sbt721s/wall723.581s. Four images/eight startup cases and the three-main
remote/stop-graph checks passed. Genuine pre-fix red failures are retained.
VALIDATION RESULTS: Both omitted and explicit equal300ms budgets now produce one typed,
traced graph deadline per request, preserve CLOSED before readiness probes, then readiness200
and normal success. All four operation types consume deterministic forwarded work budgets.
Default transport5000ms forwards at most3750ms with the configured25percent response reserve.
All35 hashes match; only README final counts changed after the full-check snapshot.
ASSUMPTIONS: User confirmed F6 only. Branch phase-10; base/currentHEAD
c85da7365927a1f7d8ee5ab1f67c5c1a128391b3. All prior uncommitted work preserved.
RISKS: F7,F8,F10–F16 remain carried. Live backend/deployment/recovery work remains later scope.
MANUAL ACTION REQUIRED: User launches the complete read-only prompt below; user owns commit/human-gate.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for required local gates.
NEXT GATE: User-launched independent recheck; stop before Phase11.

No commit, push, provider/cloud call, reviewer invocation or human-decision edit occurred.
All specialist agents, builds, task containers and the temporary network have stopped.

Reviewer instructions removed at the user’s request; review prompts are provided in chat.

Subphase 10B repair round 2 is ready for review. I have stopped and will not start the next subphase until I receive the next prompt.

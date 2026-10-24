# Phase 8 test report

## Subphase 8A

STATUS: COMPLETE local affected and full deterministic gates; independent review pending.
OWNER: Coordinator assembling independent-test and module-owner evidence.
WORK ORDER: 8A meaningful feature/interface tests plus approved7C-L2 prerequisite.
FILES CREATED: Core contract/wire fixtures, RAG module suite, storage module suite, three independent embedding specs; exact inventory in evidence/8a/files.json.
FILES MODIFIED: RuntimeGraphFence.scala and IndependentStorageRuntimeFenceSpec.scala.
COMMANDS RUN: Exact commands and JDK17 environment in evidence/8a/commands.md; logs and exits in same directory.
TEST RESULTS: prerequisite2 8/8; interfaces1 core8/8; targeted1 storage11/11 independent23/23; final targeted2 core9/9 storage12/12; final targeted3 RAG14/14 independent23/23. Every listed successful gate exited0. First prerequisite startup failed exit1 due sandbox cache lock, then succeeded with native approval.
VALIDATION RESULTS: Fixed SHA/framing/rendered text/chunk/counter expectations; synthetic fixtures; no production metrics or researcher identity invented. Fake/SDK proxy tests cover replay/conflict/bounds/retry/permanent failure/dimension/queue requests/concurrency/S3 envelope/context authority. Only module owners edited their module-local tests; independent owner edited tests/**.
ASSUMPTIONS: SDK attempt counts describe observed adapter calls when SDK retries are disabled.
RISKS: Local stub/fake results do not prove live compatibility, real semantic quality, IAM, license permission, cost or minimum corpus count.
MANUAL ACTION REQUIRED: User-launched review; later 8B smoke/CLI and approved 8C live gates.
BLOCKED-ON OWNER: None for affected gates.
BLOCKED-ON EVIDENCE: None for local completion; external review and live gates pending.
NEXT GATE: User-launched read-only 8A review; implementation has stopped.

Full gate observed: exit0, 718 passed / 0 failed, real683.81 seconds. Module groups: core153, Hadoop64, entityResolution39, sparkAnalytics38, storage44, RAG14, independent358, buildVerification8. No failed test cases. Expected checkProbeInjectFailure proves failure-path behavior, not a failing full gate. Live-tagged suite remained excluded. Exact command, summaries, retained line-numbered excerpt, raw hash and final source audit are under evidence/8a/. All302 frozen inputs unchanged during gate.

## Subphase 8A — repair round 1

STATUS: COMPLETE affected and full deterministic gates; independent recheck pending.
OWNER: Coordinator /root collecting module-owner/independent evidence.
WORK ORDER: F1 and user-requested N1; actual renderer acceptance instead of forged ID/text conflict states.
FILES CREATED: tests/**/IndependentEmbeddingSlotRepairSpec.scala; repair evidence.
FILES MODIFIED: Core11-case, storage13-case, RAG18-case suites; independent contract/storage fixtures; four embedding wire snapshots.
COMMANDS RUN: Exact JDK17 commands and exits in evidence/8a-r1/commands.md; java-version.txt.
TEST RESULTS: targeted-1 core11/11/storage13/13 exit0; targeted-2 RAG18/18/independent29/29 exit0. Independent groups7 contracts/6 storage/4 rendering/4 repair/8 runtime fence. No failed affected attempts. Fresh full check passed 731 tests / 0 failures, exit0, real703.88 seconds, on303 unchanged frozen files; module groups155/64/39/38/45/18/364/8.
VALIDATION RESULTS: New real renderer->item->runner path with changed source field/source run, same slot/new content ID, pre-embed conflict/no new data puts except rejected report; unchanged no-write replay, newmodelkey, distinct actual chunks, fixed seven UTF8frame expectation and legacy slot reject. N1 exact Unicode/CRLF/trailing whitespace/qualification/ref preservation, all5 filters through actual vector metadata/invalid filters rejected; explicit permitted abstract composition/refs.
ASSUMPTIONS: Synthetic inputs; fakes/SDK proxies only; no paid/real-data quality claim.
RISKS: Local tests do not establish live compatibility, permissions, costs, corpus scale or semantic quality. Nonblocking N2-N8 unchanged.
MANUAL ACTION REQUIRED: User-launched independent recheck; no commit before approval.
BLOCKED-ON OWNER: None for affected tests.
BLOCKED-ON EVIDENCE: Independent recheck pending; local gates complete.
NEXT GATE: User-launched repair recheck; implementation stopped.

Final evidence: evidence/8a-r1/final-check.json, final-check-excerpt.txt, final-audit.json, repair-files.json and commands.md. Expected injected checkProbeInjectFailure self-test passed; no live suite ran. All specialist work and build sessions finished. Raw log /tmp/phase8a-r1-final-check-1.txt, 1378030 bytes, SHA256 ff4baf2ed391f587d1d3cd6a6b62b7bda652943fa353874f0c8182a487104a0b; retained line-numbered excerpt is portable evidence, raw temp file is not.

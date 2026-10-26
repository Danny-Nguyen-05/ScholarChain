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

## Subphase 8B

STATUS: COMPLETE local gates, independent review pending.
OWNER: /root gate coordinator, owner-requested commands; tests authored by module owners and /root/test_engineer.
WORK ORDER: Phase8B plus user-authorized R1 group repair, no live calls.
FILES CREATED: evidence/8b/ contains raw targeted logs or line-numbered excerpts, SHA/size records, source and output inventories, owner reports, disabled live templates, runbook and review handoff. Independent/module files listed in source-files.json.
FILES MODIFIED: Test files and source fixtures listed in source-files.json; this report and other coordinator phase evidence.
COMMANDS RUN: Exact JDK17 environment and all attempts in evidence/8b/commands.md. Full command `/usr/bin/time -p sbt -batch check > /tmp/phase8b-final-check-1.txt 2>&1` exit0. Raw /tmp/phase8b-final-check-1.txt, 1381548 bytes, SHA256 91ef687108bcb2ec6083b1033197a6373477e49130bb68ec464659e34149ea59.
TEST RESULTS: Affected13 core +19 storage +25 RAG +39 independent passed. Full 756 passed/0 failed,678.84s real:157/64/39/38/51/25/374/8 by core/Hadoop/ER/Spark/storage/RAG/independent/build. Expected injected check-probe error belongs to the successful build failure-path test. No skipped test is claimed passed; AWS integration remains disabled.
VALIDATION RESULTS: Actual G1 export and bounded real export CLI acceptances pass;12/16 first writes, identical fresh counters/manifests, all skipped on disk/process replay with0 embedding calls. All text/qualification hashes checked. Six neighbor expectations and exact-metric denial pass. Actual runtime fence5 roots/20 inspected/no findings, unchanged source.254 frozen files unchanged,30 source-file hashes verified; plan snapshot cmp0; source whitespace check0.
ASSUMPTIONS: Synthetic G1 and lexical smoke fixtures do not prove real identities or Titan quality. Source reader checks declared selected tables in full;12/16 documents are the bounded ingestion sample, not a10,000-vector live corpus.
RISKS: Full attempt1 passed; earlier affected attempts are honestly retained: sbt sandbox lock exit1; storage formatter syntax exit1; RAG ambiguous import compile exit1. Initial direct CLI returned correct results/exit0 but Hadoop shutdown exceptions; forked retry fixed lifecycle but lacked log configuration; final forked replay fixed both. N2–N8/R2–R3 deferred. Live/service/billing behavior unverified.
MANUAL ACTION REQUIRED: User starts independent read-only review; future live execution needs separate gates.
BLOCKED-ON OWNER: None for local validation.
BLOCKED-ON EVIDENCE: None for local gates; independent review and live gates open.
NEXT GATE: User-launched8B reviewer; no8C.

## Subphase 8B — repair round 1

STATUS: COMPLETE local repair gates; independent recheck pending.
OWNER: /root gate coordinator; tests authored by assigned RAG/test owners.
WORK ORDER: B1 plus user-authorized N9; no questions, no live execution.
FILES CREATED: New test suites and render/query commands in repair-files.json, and evidence/8b-r1/ artifacts.
FILES MODIFIED: Test refusal guard, pure live report/approval composition, module README and coordinator evidence; exact paths/hashes in repair-files.json and files.json.
COMMANDS RUN: Required JDK17 environment and all exact commands/failed attempts in commands.md. Full `/usr/bin/time -p sbt -batch check > /tmp/phase8b-r1-final-check-1.txt 2>&1` exit0. Raw /tmp/phase8b-r1-final-check-1.txt, 1520049bytes, SHA256 3b5abff12a025530e445a79ccddfe438a0f1df29f25c240078ebe4b81b46876f.
TEST RESULTS: Targeted-1 RAG7/independent11 passed. Targeted-2 RAG32passed1failed, source wire test expected lowercase; corrected literal to frozen OPENALEX. Targeted-3 RAG33/independent41 passed,0failures. Full766passed0failed,695.67s real:157/64/39/38/51/33/376/8. New G1 passing case present in full log; expected injected build failure self-test is intentional. AWS integration not enabled.
VALIDATION RESULTS: B1 passing path now runs in ordinary check without retainedtarget input. Actual producer10researchers9canonicalworks18literaledges28tables;12write/replay12skip0calls/fresh counters+hash identity; every pointer/qualifications hash verified; source bounds/roundrobin and exact fifth-type unit fields covered. N9 render-only12real-model items accepted by pure live preflight; no embedder/state. Pure live report fields and null/rejection cases pass. Five module query-smoke cases plus independent refusal verify operation/content/caps/pointer/hand-derived quantiles, zero client-factory calls on executable refusal.346frozen files and8repair/35cumulative hashes verified; plan cmp0; source diffcheck0.
ASSUMPTIONS: Synthetic pure grants/reports are fixtures, not real approval or latency results. SDK clients are never constructed through tested refusal paths.
RISKS: Actual approved live route remains unexecuted even with fakes; cloud compatibility, quality, billing and cleanup remain future gates. Other findings remain deferred.
MANUAL ACTION REQUIRED: User launches independent recheck; no commit until APPROVE.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for required local gates; independent review and live gates remain.
NEXT GATE: User-launched8B repair recheck; stop.

## Subphase 8B — independent recheck approval recorded

STATUS: COMPLETE evidence verification; no tests rerun.
OWNER: /root coordinator.
WORK ORDER: Record external APPROVE and prepare commit gate without source changes.
FILES CREATED: External-recheck copy/hash and commit proposal/inventory/audit under evidence/8b-r1/.
FILES MODIFIED: Coordinator review/disposition/prompt/report records only.
COMMANDS RUN: Read-only source/frozen hashing, git inventory and bounded credential-pattern/path checks; results in post-recheck-audit.json.
TEST RESULTS: Retained prior full JDK17 gate766passed0failed,exit0; independent reviewer verified all four new/changed suites and full evidence. No rebuild because implementation bytes are unchanged.
VALIDATION RESULTS: All35 source entries including sizes/base hashes and all346 frozen contents verified; approved inventory matches20tracked/119untracked before recording, plus only new coordinator evidence afterward. No runtime/credential files included.
ASSUMPTIONS: Approval is independent review, not human commit authorization or instructor approval.
RISKS: Deferred nonblocking findings and live8C behavior remain unverified.
MANUAL ACTION REQUIRED: User commit decision; no automatic action.
BLOCKED-ON OWNER: User for commit decision.
BLOCKED-ON EVIDENCE: None for local8B gates.
NEXT GATE: User-written commit instruction; no source edits or8C.

STATUS: COMPLETE for local F3/F4 repairs; external recheck pending.
REPOSITORY: /Users/danny/Documents/UIC/CS441/ScholarChain
BRANCH: phase-7
BASE/HEAD: 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276; all7B changes remain uncommitted.
SCOPE: Repair round1 only. No questions; user authorized F3/F4 on existing tree.
FILES: Five reviewed paths modified and three storage files added; exact list
in repair-source-changes.json. Coordinator reports appended; repair evidence
under docs/agent-runs/phase-07/evidence/7b/repair-1/. Cumulative files.json.
F3: Explicit state classification, sanitized final-state evidence, immutable
attempt/failure records, new job after terminal failure, timeout ID reuse,
completed unchanged, preserved legacy history. Module+independent tests pass.
F4: Shared structural Document converter, exact numeric JSON and control-text
preservation in reader/status. Node/neighbor special-character tests pass.
CHECKS: Exact JDK17 environment/commands/exits in repair-1/commands.md.
Affected23/54/4 passed exit0 real19.40s. Full `sbt -batch check` exit0:
636 passed/0failed, groups 144/64/39/38/23/320/8, real680.86s.
Java17.0.20.1/sbt1.10.7. Full raw SHA256 0d8fb3ecc98dddf264ccba022a7941e49fff44c21e404357fa580daf3f715ef1.
EVIDENCE: external-review.txt, targeted-1.txt/.json, final-check.txt/.json,
source snapshots, owner reports, final-audit.json, evidence-index.json.
LIMITS: No liveAWS/provider or full real-data load; N4–N14 OPEN/nonblocking:
N4 TTL divergence (storage); N5 GSI key byte validation (storage);
N6 SDK stub gaps (test,7C); N7 evidence prefix config (storage);
N8 formatter process note (coordinator); N9 leading-zero count acceptance (storage);
N10 fail-closed export without violation count (storage);
N11 vector registry reason/payload semantics (storage);
N12 validation/upload re-read and memory cost (storage);
N13 CLI exit/retry composition (storage);
N14 full-scale path/community cost (storage/later14C).
MANUAL ACTION: User launches read-only recheck below, then commits after
APPROVE. F1/F2/B1 stay CLOSED. No reviewer/stage/commit/push or7C started.
All specialists and builds finished.

RECHECK REVIEWER PROMPT

You are the independent, read-only code reviewer for ScholarChain Phase7,
Subphase7B REPAIR ROUND1, in /Users/danny/Documents/UIC/CS441/ScholarChain.

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. Accepted plan docs/agent-runs/phase-07/evidence/7a/phase7-plan.md,
   Sections3–7, Subphase7B in Section8, Sections9–10.
   Original /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
   SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb.
3. Course Phase7 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading
4. docs/agent-runs/phase-07/review.md (verbatim external7B REQUEST-CHANGES),
   prompt.md, repairs.md, owner-report.md and test-report.md repair1 sections.
5. evidence/7b/repair-1/external-review.txt, source-before.json,
   repair-source-changes.json, owner reports, commands.md, targeted-1.json,
   final-check.json and final-audit.json, plus the repair code/tests.

Checkpoint facts:
- Branch phase-7; base and HEAD 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276. Uncommitted7B tree explicitly authorized;
  no staging, commit or push. Prior review base remains this SHA.
- Repair-only modified paths:
  modules/storage/README.md
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/NeptuneGraphLoader.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/NeptuneGraphReader.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageGraphLoaderSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageGraphReaderSpec.scala
- Repair-only added paths:
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/AwsDocumentJson.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/NeptuneJobAttempts.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/NeptuneRepairSpec.scala
- Coordinator append-only changes: phase-07/review.md, prompt.md, repairs.md,
  owner-report.md, test-report.md; new evidence/7b/repair-1/**.
  Exact cumulative inventories: repair-1/files.json. Source-before.json binds
  reviewed untracked files as well as tracked files for repair comparison.
- Step0: No questions for this repair round. User authorized blockers only;
  no nonblocking fix, Spark/core/build/control/producer change or7C work.
- Affected commands used exact Section2 JDK17 exports and owner-requested
  formatting, storage/Test/test, independentTests/Test/testOnly
  edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec, and
  sparkAnalytics/Test/testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec.
  Exit0;23/54/4 passed, zero failures; real19.40s. Full commands in commands.md.
- Fresh `java -version; /usr/bin/time -p sbt -batch check`: exit0,
  636 passed/0failed, groups 144/64/39/38/23/320/8; Java17.0.20.1/sbt1.10.7,
  real680.86s. Expected injected build error belongs to passing self-test.
  Complete retained repair-1/final-check.txt: 1,366,798bytes,
  SHA256 0d8fb3ecc98dddf264ccba022a7941e49fff44c21e404357fa580daf3f715ef1.
- Source hashes/mtimes stable across full gate; protected prior source/evidence
  unchanged. No failed repair invocation; earlier7B failed logs preserved.
- F3 locally repaired: only LOAD_NOT_STARTED/LOAD_IN_QUEUE/LOAD_IN_PROGRESS
  poll; LOAD_COMPLETED succeeds; all other states fail immediately with
  sanitized status-specific evidence. Append-only terminal markers/numbered
  jobs allow a new job after final failure; timeout reuses pending ID;
  completed fingerprint returns Unchanged without upload/submission.
  Module+independent cases verify LOAD_FAILED, WRITE_CONFLICTS, DEADLOCK,
  unknown states, failure/retry ledger, timeout reuse, completion and legacy
  history. README explains recovery; no registry deletion.
- F4 locally repaired: AwsDocumentJson/AwsJson structurally preserve maps,
  lists, strings, exact BigDecimal numbers, booleans and null in reader and
  loader status. No Document.toString JSON. Module/independent cases cover
  actual CRLF, tab, quotes, backslash, Greek/CJK/emoji node/neighbor text;
  module covers large integer and precise decimal numeric values/types.
- F1/F2/B1 stay closed. N4–N14 remain OPEN/nonblocking:
N4 TTL divergence (storage); N5 GSI key byte validation (storage);
N6 SDK stub gaps (test,7C); N7 evidence prefix config (storage);
N8 formatter process note (coordinator); N9 leading-zero count acceptance (storage);
N10 fail-closed export without violation count (storage);
N11 vector registry reason/payload semantics (storage);
N12 validation/upload re-read and memory cost (storage);
N13 CLI exit/retry composition (storage);
N14 full-scale path/community cost (storage/later14C).
- No AWS/provider calls, full-data replay/cache load, reviewer or human record
  edit. Live-service behavior and concurrency/cross-service limits unverified.

Review rules:
- Read-only: do not edit, run builds/tests, call AWS/providers, change data,
  stage, commit, push or read secrets.
- Inspect git diff 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276 plus untracked files. Use repair-source-changes.json
  and source-before.json to distinguish this repair from reviewed7B.
- Recheck all F3/F4 acceptance checks and regressions. Confirm terminal recovery
  cannot remain pinned to a failed ID, pending timeout reuse works, status
  evidence is sanitized and durable, exact text/numbers survive structural
  conversion, and completed reload remains unchanged.
- Check ownership, provenance, configuration, honest evidence, excluded live
  tests and no unrelated repair. Report all confirmed findings in one pass.
- Nonblocking N4–N14 and later7C/live work are not required for this repair.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase7B repair round1.
2. Findings: severity, path:line, evidence, impact, owner, acceptance check,
   blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. Complete NEXT PROMPT in one code block:
   APPROVE: append verdict verbatim as user-supplied external recheck, record
   F3/F4 CLOSED and N4–N14 OPEN; confirm human committed approved7B on phase-7
   (ask and stop if absent). Only then begin7C Step0 with all questions and
   defaults, wait before edits, use exactJDK17, launch no reviewer, do not run
   liveAWS/providers or stage/commit/push. Return Section10 handoff and stop
   before Phase8.
   REQUEST-CHANGES: append verdict/findings, route only blockers to owners,
   rerun affected targets and fullJDK17check, return complete recheck prompt
   and stop. No7C, reviewer, cloud/provider or stage/commit/push operations.

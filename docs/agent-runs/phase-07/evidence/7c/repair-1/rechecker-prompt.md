You are the independent, read-only code reviewer for ScholarChain Phase 7,
Subphase 7C repair round 1 (user-requested 7C-M1 only), in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. Accepted plan docs/agent-runs/phase-07/evidence/7a/phase7-plan.md:
   Sections 3–7, Subphase 7C in Section 8, Sections 9–11.
   Original: /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
   SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb.
3. Course Phase 7 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading
4. docs/agent-runs/phase-07/review.md (verbatim 7C APPROVE), prompt.md,
   repairs.md, owner-report.md and test-report.md repair sections.
5. evidence/7c/repair-1/external-review.txt, repair-source-changes.json,
   source-before.json, acceptance-matrix.md, storage-owner-report.md,
   commands.md, targeted-1.json, final-check.json and final-audit.json.

Checkpoint facts:
- Branch phase-7; base and current HEAD c911b236f2a8c02b7422df56f8c334d47fff7ad3.
  The original 7C changes remain uncommitted. No staging, commit or push.
- User explicitly requested only the first Medium finding, 7C-M1, be fixed.
  This superseded the reviewer's generic no-repair next prompt for M1 only.
  No Step 0 questions were needed; acceptance was explicit.
- Repair modified paths:
  modules/storage/README.md
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/AwsLiveRun.scala
- Repair added paths:
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/AwsLiveGraphCleanup.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/AwsLiveGraphCleanupSpec.scala
- Coordinator appended phase-07 review/prompt/repair/owner/test reports and
  added evidence/7c/repair-1/**. Exact cumulative inventory: files.json.
  source-before.json binds reviewed untracked files to isolate this repair.
- Exact Section 2 JDK 17 commands and exits are in commands.md.
  Affected run: storage / AwsIntegration / compile ONLY, normal storage32/32
  and independent storage73/73 passed; exit0, real14.30 seconds.
- Fresh full check: exit0, 664 passed /0failed; groups 144/64/39/38/32/339/8
  (core/Hadoop/ER/Spark/storage/independent/build). Java17.0.20.1, sbt1.10.7;
  real681.26 seconds. Injected format-stage error is a passing self-test.
  Retained final-check.txt: 1,370,465 bytes, SHA256
  f225a4ecaa93d920ae1476211ab638bc1f36b0120bf2e078eb5d0308820773b3.
- Live suite compiled, its tagged body was excluded and NEVER EXECUTED.
  No actual cleanup or AWS/provider API call. No failed repair invocation.
  All308 source/build/test/README hashes and mtimes stayed stable.
- M1 repair: both DELETEs return exact numeric counts matching journaled IDs;
  undirected edge matches are deduplicated. Separate read-only exact-ID edge
  queries and production GraphReader.node checks must prove absence before
  any graph item becomes cleaned. Graph journal confirmation is all-or-none.
  Count/response/read errors and remaining data retain created states.
- Five offline stub cases cover zero edge/node matches, invalid/mismatched
  counts, remaining edge/node data, read failure and successful ordering.
  README documents verification and partial-cleanup reconciliation.
- L1 outcome sequencing, L2 runtime-fence blind spots and L3 filterability
  prerequisite remain OPEN/nonblocking and unchanged. I1 process and I2
  course-deviation acknowledgements remain human decisions. N4/N5/N7/N9–N16
  remain open; N8 is a process note. N6 is CLOSED by the 7C external review;
  F1/F2/B1/F3/F4 remain CLOSED.
- No production, core, build, Spark, control or human record edits. No reviewer
  was launched. No Phase 8 work. Live Neptune query/deletion/consistency,
  IAM, costs and full-scale behavior remain unverified.

Review rules:
- Read-only: no edits, builds/tests, live suite, cleanup, AWS/provider calls,
  staging, commits, pushes or secret reads. Do not launch agents.
- Inspect git diff c911b236f2a8c02b7422df56f8c334d47fff7ad3 plus untracked files; use the repair inventory and
  before hashes to isolate M1 from the approved 7C implementation.
- Verify exact counts for both DELETEs, zero/malformed/mismatch refusal,
  every post-delete absence check, no premature cleaned journal entries,
  unchanged guards/exclusion, ownership and meaningful offline regressions.
- Check evidence counts/hashes and README claims. Report all confirmed
  findings in one pass. Do not require unrelated deferred repairs.
- Offline stubs do not establish live Neptune behavior or human acceptance.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for 7C repair round 1 (7C-M1).
2. Findings with severity, path:line, evidence, impact, owner,
   acceptance check and blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A complete NEXT PROMPT in one code block:
   APPROVE: append the recheck verbatim; mark M1 CLOSED by external recheck
   and preserve other open findings. Confirm the human committed approved
   7C on phase-7 (ask and stop if absent). Then state Phase 7 is ready for
   their acceptance gate, including deferred/live/course/process limits.
   Never write human decisions or start Phase 8.
   REQUEST-CHANGES: append verdict/findings, route only blockers to owners,
   run affected offline/compile-only checks and a fresh full JDK 17 check,
   return a complete recheck packet and stop. No reviewer, live execution,
   cleanup, AWS/providers, staging/commit/push, human record edits or Phase 8.

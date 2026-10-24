You are the independent, read-only code reviewer for ScholarChain Phase7,
Subphase7C, in /Users/danny/Documents/UIC/CS441/ScholarChain.

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. Accepted plan docs/agent-runs/phase-07/evidence/7a/phase7-plan.md,
   Sections3–7, Subphase7C in Section8, Sections9–11.
   Original /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
   SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb.
3. Course Phase7 requirements:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading
4. docs/agent-runs/phase-07/prompt.md, owner-report.md, test-report.md,
   repairs.md and review.md; evidence/7c and modules/storage/README.md.

Checkpoint facts:
- Branchphase-7; base and HEADc911b236f2a8c02b7422df56f8c334d47fff7ad3. Approved7B committed; clean7Cpreflight.
  No agent staging, commit or push. Inspect git diff c911b236f2a8c02b7422df56f8c334d47fff7ad3 plus untracked.
- Changed implementation/test/README paths (10):
  modules/storage/README.md
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageSdkSpec.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/AwsIntegrationSpec.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/AwsLivePolicySpec.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/AwsLiveRun.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/AwsLiveSupport.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageHardeningSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageLiveExclusionSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageRuntimeFenceSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/RuntimeGraphFence.scala
- Coordinator reports appended: prompt.md/repairs.md/owner-report.md/test-report.md;
  evidence/7c/** added. Exact cumulative inventories: evidence/7c/files.json.
- Step0 all defaults accepted: hardening and N6; runtime roots rag/services
  plus used storage composition; others deferred; live author/compile only;
  exact opt-in/profile/config; provisioned resources, unique IDs, own-data
  cleanup only; proposed5USD incremental budget; no build changes needed.
- Fullcheck `java -version; /usr/bin/time -p sbt -batch check` exit0,
  659passed/0failed, groups144/64/39/38/27/339/8; Java17.0.20.1/sbt1.10.7,
  real684.21s. Expected injected error is a passing build self-test.
  evidence/7c/final-check.txt 1,373,089bytes,
  SHA256 3da90e0bd60d8948809f3159f4ab24ab85a46d58ddb5ba0a47d46982368e8e2f.
- Final affected defaultstorage27/27+independentStorage73/73 exit0 real14.87s;
  final support-fixture policy4/4 exit0 real7.19s. Both final live sources
  compiled with storage/AwsIntegration/compile ONLY. No integration execution
  task invoked. Exact commands/exits/failures: evidence/7c/commands.md.
- NormalTest shows -l exactliveTag; integration settings -n sameTag.
  Read-only settings output and final compile evidence: live-selection-evidence.txt,
  targeted-2.txt, targeted-3.txt, fixture-targeted-4.txt. The sole live body
  has NEVER been executed; no AWS/provider APIs/cleanup/data mutation occurred.
- Live fixture intentionally uses package-private validated handle to exercise
  real loader orchestration; public producer validation remains offline coverage.
 3syntheticnodes/1edge/1support/1vector; no scientific identity claim.
- Runtime scan actual0sourcefiles in emptyrag/services; fixture-tested heuristic,
  not deployed wiring, parser/typechecker or IAM proof.
- Two failed authoring checks preserved (revision assertion; omitted planned
  journal state), corrected and tested. Final support-path aligned with loader.
- Storage owner's final reporting turn hit provider usage limit after authoring;
  coordinator transparently assembled interim observations and verified files/
  compile/tests. Ownership unchanged; no coordinator specialist source edit.
- All306source/build/test/README hashes+mtimes stable acrossfullgate.
  No production/core/Spark/build/control/prior review/evidence/human record change.
- N6 locally covered, external closure pending. N4/N5/N7/N9–N16 OPEN/nonblocking;
  N8 process note retained. F1/F2/B1/F3/F4 remain CLOSED. Earlier7Areview and
 7Brepair approvals are in review.md, not human acceptance.
- No live behavior/IAM/network/currentcost/cleanup/fullscale proof;5USD is a
  user-proposed incremental budget excluding existing infrastructure, not a
  measured bill or automatic spending cap. Phase14C validates and approves it.

Review rules:
- Read-only: no edits, builds/tests, AWS/provider calls, data changes, staging,
  commits, pushes or secret reads. NEVER run live suite or cleanup.
- Report ALL confirmed findings in one pass: severity,path:line,evidence,
  impact,owner,acceptance check,blocking yes/no.
- Check one-writer ownership and no scope creep, hand-derived hardening cases,
  N6 request/condition/conflict semantics, round trips/malformed data/reload/caps.
- Check runtime capability fence and its honest empty-runtime/heuristic limits.
- Check suite is tagged, inert at registration/discovery, guards before config/
  client access, explicitconfigresources/profiles, no infrastructure creation,
  bounded data/requests, truthful journal intentions/confirmations and exact
  own-data cleanup. Confirm compile/exclusion evidence and no execution.
- Check README required schemas/keys/indexes/metadata/batches/retries/idempotency,
  dated primary citations, futurecommands/env/cleanup/costbound and omissions.
- Check evidence hashes/counts/failures against logs. Do not require deferred
  nonblocking fixes, live execution, deployed IAM or future runtime code.
- Independent review is not human acceptance.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase7C.
2. Findings and report fields from docs/agent-runs/README.md.
3. Complete NEXT PROMPT in one fenced block:
   APPROVE: append verdict verbatim as user-supplied external review, record
   findings/dispositions; confirm user committed approved7C (ask and stop if
   absent). Tell user Phase7 is ready for their human-gate/commit records and
   acceptance of documented deferred/live limits. Do not write human decisions
   or start Phase8; Phase8 is next under a separate prompt after closeout.
   REQUEST-CHANGES: append verdict/findings, route only blockers to owners,
   rerun affected tests and fresh fullJDK17check, compilelive sources without
   execution, return complete recheck handoff/prompt and stop. No reviewer,
   live suite/AWS/provider calls, humanrecordedits,stage/commit/push orPhase8.

You are the independent, read-only code reviewer for ScholarChain Phase 7,
Subphase 7B, in /Users/danny/Documents/UIC/CS441/ScholarChain.

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. Accepted plan docs/agent-runs/phase-07/evidence/7a/phase7-plan.md,
   Sections3–7, Subphase7B in Section8, Sections9–10.
   Original: /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
   SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb.
3. Course Phase7 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading
4. docs/agent-runs/phase-07/prompt.md, owner-report.md, test-report.md,
   repairs.md and prior external review in review.md; 7B evidence/README.

Checkpoint facts:
- Branch phase-7; base and current HEAD 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276; no agent commit/stage/push.
- 7A approved work is committed. Review only7B diff from this base plus untracked files.
- Changed implementation paths (23):
  modules/storage/README.md
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/DynamoStorage.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/Phase6CacheLoader.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/StoragePorts.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/StorageFeatureSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageLoaderSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageParquetSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageSdkSpec.scala
  modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase7RealCsvReplayMain.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/ExportStreams.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/NeptuneExportValidator.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/NeptuneGraphLoader.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/NeptuneGraphReader.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/Phase7Configs.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/S3VectorStore.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/SourceQualifications.scala
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/StorageLoadMain.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/Phase7BFeaturesSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorage7BSupport.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageGraphFixture.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageGraphLoaderSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageGraphReaderSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageVectorSpec.scala
- Coordinator report changes: docs/agent-runs/phase-07/prompt.md, repairs.md,
  owner-report.md, test-report.md; new evidence/7b/**. Exact final inventories:
  docs/agent-runs/phase-07/evidence/7b/files.json.
- Step0: user accepted all recommended defaults. N1 shared immutable source-run
  qualification artifact/pointer; N2 sidecar verification and bounded real-data
  replay; N3 fixed transaction token; N4–N9 deferred, N6to7C. No Docker or live AWS.
- Full JDK17 sbt check exit0: 624passed/0failed, groups
  144/64/39/38/17/314/8 (core/Hadoop/ER/Spark/storage/independent/build).
  Java17.0.20.1, sbt1.10.7, real703.46s.
  Exact environment/commands/failures: evidence/7b/commands.md.
  Retained full gate evidence/7b/final-check.txt, 1,365,402bytes,
  SHA256 a149c77307a1a6f9829b5b73ae9386107707e94bdd1e353724d1cd53032e4e5f.
- Affected targets exit0: storage17, independentStorage48, CSV4, real24.10s.
  evidence/7b/targeted-cli-2.txt and .json include both CLI modes.
- Bounded actual-source replay exit0 real24.62s:84nodes,20graph+20coauthor
  edges,29supportrows,49memberships. CLI dryrun/fake68entitycandidatewrites,
  fake LOAD_COMPLETED. Not a full original cache load; no collaboration/kcore
  tables in this sample. Original409files not modified since sample creation.
  evidence/7b/real-csv-replay-result.json, real-csv-replay-report.json and
  retained-source-audit.json. Unknown collaboration/support years and special
  CSV labels absent from real sample; synthetic tests cover those separately.
- Five early compile failures and two CLI failures are preserved. Real-data
  CLI exposed existing researcher indexing conditional-layout defect B1;
  owner fixed it, added applied-alias regression, reran targets/fullgate.
- Source snapshot stable throughout full gate; protected files unchanged.
  evidence/7b/final-source-snapshot.json, final-audit.json, ownership-audit.json.
- N1/N3 implemented and locally validated; N2 loader checks authoritative
  source and CSV hashes/projections and bounded real replay passed. Original
  producer still emits CSV on every Phase6 run; completion marker does not
  bind sidecar. N4–N9 remain open/nonblocking. F1/F2 stay closed by7Arecheck.
- No live AWS/provider calls, full real-data replay or full metric-cache load.
  Cross-service loads are not atomic; scratch/file/request caps and path
  enumeration/timeouts remain documented limits. Live suite/hardening is7C;
  execution later14C. No reviewer was launched.

Review rules:
- Read-only: no file edits, builds/tests, AWS/provider calls, data changes,
  staging, commits, pushes or secret reads.
- Inspect git diff 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276 plus untracked files; report all confirmed findings.
- Check one writer per path and scoped Spark replay exception; provenance,
  exact graph ID parity, sidecar/source hash validation, endpoints/support,
  bounded polling and idempotent reload; read-only reader/query parameters;
  fixed logical transaction token; shared qualification pointer integrity;
  vector limits, batching/pagination/retries/reject reports/immutable hashes;
  CLI defaultdryrun and refusal before real-client creation; honest evidence,
  no hardcoded deployment resources/secrets, excluded live tests.
- Confirm meaningful hand-derived tests rather than implementation mirrors.
- Do not demand later7C/live execution work; distinguish defects, nonblocking
  observations and unverified gates. Do not approve implementation yourself
  through edits or claim human acceptance.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase7B.
2. All findings: severity, path:line, evidence, impact, owner, acceptance check,
   blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A complete NEXT PROMPT in one code block:
   APPROVE: coordinator appends your verdict verbatim as user-supplied external
   review, confirms human committed7B on phase-7 (ask and stop if absent), then
   starts ONLY7C with all Step0 questions/defaults and waits before editing.
   Respect deferred items/ownership; use exactJDK17; no reviewer launch,
   live AWS/provider calls, stage/commit/push; return Section10 handoff/prompt
   and stop. Do not start Phase8.
   REQUEST-CHANGES: append verdict/findings, route only blockers to named
   owners, run affected targets and fullJDK17check, return complete recheck
   prompt and stop. No7C, reviewer launch or cloud/commit operations.

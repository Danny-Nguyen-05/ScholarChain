# Phase 7 external reviews

## Subphase 7A

No external review has been supplied. No reviewer was launched by the coordinator. The implementation and local gates do not constitute independent approval or human acceptance.

## Subphase 7A — user-supplied external review (repair round 1 input)

VERDICT: REQUEST-CHANGES for Subphase 7A.

Most of 7A holds up: ports and fakes, S3 integrity, the six DynamoDB tables, the cited AWS limits and the live-test exclusion. I'm not approving because of two blocking defects. The cache loader can't read a real Phase 6 export, and the retained .log evidence won't be included in the commit.

Findings

Blocking

F1 — High — The cache loader rejects every real Phase 6 export
- Where: modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/ManifestRows.scala:75 reads table("rowCount").num.toLong.
- Evidence:
  - The producer writes "rowCount" -> t.rowCount from a Long (modules/spark/src/main/scala/edu/uic/cs441/scholarchain/spark/Phase6Export.scala:321). ujson turns a Long into a JSON string.
  - The real 6FG export confirms this. In target/phase6-runs/6fg-spark-first-v2/run:f02acf56-…/run-metadata.json, tables[0].rowCount == "21819" is a Python str. That run's completion marker and the shape of load-manifests/s3.json otherwise match what the reader expects.
  - .num throws on a string, and line 146 catches it as Rejected("invalid-manifest-source"). So LocalParquetManifestReader.open fails for every real manifest.
  - Your own Spark test shows the encoding: Phase7NeptuneExportSpec.scala:190 asserts rowCount(...).str == "2" for the same kind of value.
- Why the tests missed it: both "actual Parquet" tests hand-write the metadata with a numeric rowCount (ParquetManifestSpec.scala:99, IndependentStorageParquetSpec.scala:128). The owner and test reports say "actual Spark-written Parquet passes through storage", but only the Parquet files came from Spark; the run metadata was synthetic.
- Impact: task 5 (loading the real manifests into EntityLinkCache and ResearcherMetricCache) doesn't work on real data, and 7B's CLI would inherit the failure.
- Owner: storage-engineer for the reader and module test; test-engineer for the independent fixture.
- Acceptance check:
  - The reader accepts the producer's string-encoded count (exact decimal digits only) and still rejects malformed counts.
  - Both the module and independent fixtures use the producer's encoding.
  - A new test covers it.
  - If the owner chooses, a local read-only smoke opens one real retained manifest (e.g. nodes/type=researcher).
- Blocking: yes.

F2 — Medium — The retained .log evidence is gitignored and will be missing from the commit
- Where: .gitignore:9 ignores *.log.
- Evidence:
  - All 23 .log files under docs/agent-runs/phase-07/evidence/7a/ are ignored, including build/phase7a-build-guard-*.log, build/phase7a-build-negative-*.log and targeted-*.log. git check-ignore -v confirms it.
  - build/log-index.json and build/owner-report.md describe these files as "retained".
  - The only proof that the live-test opt-in and profile guards refuse to run (with exit 1) is in those logs.
  - Phase 6 kept its logs as tracked .txt files.
- Impact: once committed, the evidence references point at files that aren't in the repo, so the claimed retained evidence can't be checked.
- Owner: the coordinator renames the files to .txt and updates the path references in log-index.json and targeted-*.json. Changing .gitignore instead would belong to build-engineer and isn't required.
- Acceptance check: git status --short -uall docs/agent-runs/phase-07 lists every retained log, every reference resolves, and the recorded SHA-256 values still match.
- Blocking: yes.

Nonblocking

N1 — Medium — Every metric item copies the whole source-run record
- Where: modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/Phase6CacheLoader.scala:324, with ManifestRows.scala:46-57.
- What happens: each ResearcherMetricCache item embeds the full run metadata, run manifest and counters. On the real 6FG run that's about 48 KB per item (8,029 + 1,151 + 39,020 bytes) across 62,757 rows: roughly 3 GB, at about 48 write units per item.
- Risk: counters can grow up to 10,000 rows (Phase6Export.scala:305), which could push items past the 380 KiB cap.
- Suggestion: store the source qualification once (an artifact or S3 pointer keyed by run ID and hash) and reference it from each item. Ideally do this before 7B's CLI.
- Owner: storage-engineer.

N2 — Medium — The Neptune CSV export runs on every Phase 6 job and is unproven on real data
- Where: Phase6Export.scala:278-286.
- What happens:
  - Every full Phase 6 run now runs the CSV export, with hard checks such as support count == jointPublicationCount. These have only been run on fixtures (no real-data CSV replay). If one fails, the whole Phase 6 pipeline stops before the completion marker.
  - The CSV files and sidecar aren't covered by the completion marker or run-metadata tables.
- Suggestion: do a bounded real-data replay before 7B relies on the export, and have the 7B loader verify the sidecar's hashes itself.
- Owner: spark-engineer, with storage-engineer for the 7B check.

N3 — Low — Transaction retries can misreport a committed write
- Where: DynamoStorage.scala:161-173.
- What happens: each application-level retry builds a new TransactWriteItemsRequest with no fixed ClientRequestToken. If a transaction commits but the reply is lost, the retry hits the condition check. A run-ledger transition then reports Retried(_, Rejected("conditional-conflict")) even though the state was written.
- Suggestion: use a fixed token per logical write.
- Owner: storage-engineer.

N4 — Low — Session TTL can cause a false conflict
- Where: StorageRows.scala:209-211.
- What happens: when TTL is enabled (it's off by default), the session row and the reservation row expire separately. If the reservation goes first, repeating the same create returns query-id-conflict.
- Owner: storage-engineer.

N5 — Low — The idempotency key's size isn't validated
- Where: StorageRows.scala:190; DynamoStorage.scala:30-44 only checks the base table's keys.
- What happens: the raw key becomes the index's partition key with no 2,048-byte check, so a long key fails with a generic provider-rejected.
- Owner: storage-engineer.

N6 — Low — Two real-SDK paths have no stub tests
- What's missing:
  - S3 put hitting an existing key (412, then compare to Unchanged or immutable-conflict).
  - Run-ledger compare-and-set / transaction-cancel handling against the stubbed Dynamo client.
- Where they belong: 7C hardening.
- Owner: test-engineer.

N7 — Info — Hardcoded evidence prefix
- Where: EvidenceStorage.scala:30 hardcodes the "evidence" key prefix.
- Suggestion: move it into config.
- Owner: storage-engineer.

N8 — Info — Coordinator ran the formatter on specialists' files
- What happened: the coordinator ran scalafmt, which rewrites specialists' source files. It was requested by the owners and disclosed, so it's only a process note.

Checks that passed (no finding)

- Ownership: each changed path has the right single writer.
- Ports and fakes: all ten ports and main fakes exist; the fakes package uses type aliases.
- S3: writes use If-None-Match:*, store SHA-256 metadata and verify it on a bounded streamed read; the manifest is written last.
- DynamoDB: all six tables match the key and access-pattern table, with condition text, configured index lookup, atomic reservation and session-only TTL.
- Duplicate metrics: conflicting duplicates are rejected before any write.
- Neptune CSV: IDs match in both directions on the fixture; unknown years are blank; text round-trips exactly (Unicode, quotes, CRLF); the sidecar and support table sit outside the loader prefix; the format matches current AWS docs.
- Cited limits: the S3 Vectors limits (500 per PutVectors, 100 per GetVectors, 40 KB / 2 KB / 50 / 10 metadata, top-K 10,000) and "Parquet is not a bulk-load format" match today's AWS docs.
- Live tests: excluded by default (-l tag plus a failing sentinel test).
- Secrets: none found.
- Full gate log: the raw log /tmp/phase7a-final-check-2.log matches its recorded SHA-256 and shows exit 0, 594 passed / 0 failed.

Report

STATUS: COMPLETE (review) — VERDICT REQUEST-CHANGES
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Independent review of Phase 7 Subphase 7A, diff from 98dd2a4458e3128d019af1c1d1dbd2bf1dfcbbd2 plus untracked files
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git diff/status/check-ignore/ls-files; cat/sed/grep/wc on repo files; shasum on plan snapshot (b54aa123…ebb, matches original) and /tmp/phase7a-final-check-2.log (a1ce196a…179b, matches); python3 -I JSON reads of retained real export target/phase6-runs/6fg-spark-first-v2/run:f02acf56-…; WebFetch of AWS docs (S3 Vectors limitations, Neptune bulk-load formats, openCypher CSV format). No sbt, no tests, no AWS/provider API, no writes.
TEST RESULTS: Not run by reviewer. Retained raw log confirms full check exit 0, 594/0 (final verification suite 8/8, expected injected-probe error).
VALIDATION RESULTS: F1 (blocking) real run-metadata rowCount is a string, reader requires a number; F2 (blocking) evidence .log files gitignored. N1–N8 nonblocking. Doc limits verified current 2026-10-22.
ASSUMPTIONS: The retained 6FG export is representative of the current Phase 6 metadata encoding (Phase6Export.scala:321 unchanged).
RISKS: No live AWS; no real-data CSV replay; the CSV checks now run on every Phase 6 job.
MANUAL ACTION REQUIRED: User routes repairs; no commit until recheck APPROVE.
BLOCKED-ON OWNER: storage-engineer, test-engineer (F1); coordinator (F2)
BLOCKED-ON EVIDENCE: ManifestRows.scala:75; Phase6Export.scala:321; real run-metadata rowCount "21819"; .gitignore:9
NEXT GATE: Repair round 1, affected tests + full JDK 17 sbt check, user-launched recheck review


## Subphase 7A — user-supplied external review (repair round 1 recheck): APPROVE

VERDICT: APPROVE for Subphase 7A, repair round 1.

Both blockers are fixed, and the evidence for each matches what I checked myself. No new blocking defects. This is an independent code review only; it isn't human acceptance, and nothing has been committed yet.

How the two blockers were fixed

F1 (cache loader rejected real exports): closed.
- ManifestRows.scala:151-160: the new ManifestMetadata.rowCount accepts only a JSON string of ASCII digits that fits in a Long. That's exactly how Phase6Export.scala:321 writes the count. Plain numbers, decimals, exponents, signs, spaces, overflow, non-ASCII digits and other JSON types are all rejected. Line 75 now uses it.
- Fixtures now match the producer. Both tests build the count from a Long and check that it comes out as a string: ParquetManifestSpec.scala:99,105 and IndependentStorageParquetSpec.scala:128,136.
- New tests reject bad counts after re-signing the completion marker, so they test the count itself rather than a stale marker: ParquetManifestSpec.scala:140-197 and IndependentStorageParquetSpec.scala:186+.
- Smoke run against the real export. The new Phase7ManifestSmokeMain (storage-engineer, test tree, not run by sbt check) read one row each from the real researcher, collaboration and kcore tables (21,819 / 62,757 / 62,757 rows) and exited 0. The evidence describes its scope accurately: one row per table, no cache load, no full count or hash. The failed first launch is kept.
- The export wasn't modified. No file under it is newer than 13:34; the smoke ran at 17:49.

F2 (evidence logs were gitignored): closed.
- I hashed the files myself. All 23 renamed .txt files have the same SHA-256 as recorded in evidence-migration.json. The 13 hashes in build/log-index.json that cover full logs match their current files. The classpath excerpt, which isn't a full log, exists.
- git check-ignore finds no match (exit 1). No .log files remain under phase-07. .gitignore is unchanged from the base.
- Every live evidence reference resolves. The remaining .log mentions are only raw /tmp command history, rename pairs and the verbatim review text, which is the right split.

Full gate: I hashed /tmp/phase7a-repair1-final-check.log and it matches 26f7ad07…2497 (1,362,175 bytes). The log shows 144/64/39/38/10/293/8, which is 596 passed and 0 failed, plus REPAIR1_EXIT_CODE=0. The build, project and Spark diffs are unchanged by the repair (still 6 files, +104/−3).

Findings in this round

- N9 — Info, not blocking. ManifestMetadata.rowCount accepts leading zeros ("0001" → 1, tested at ParquetManifestSpec.scala:172). The producer never writes leading zeros, so "exact" is slightly loose. No fix needed. Owner: storage-engineer.
- N1–N8 remain open and nonblocking, with the same owners as before. N1 (each metric item copies the whole source-run record), N2 (no real-data CSV replay; the CSV and sidecar aren't covered by the completion marker) and N3 (no fixed ClientRequestToken on transaction retries) bear directly on 7B's loader and CLI. They should come up in 7B Step 0.
- Not verified: any live AWS behaviour, a real-data Neptune CSV replay, and a full cache load from real data. I ran no builds or tests myself.

Report

STATUS: COMPLETE (review) — VERDICT APPROVE for Subphase 7A repair round 1
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Recheck blocking F1/F2 from the 7A external review; base 98dd2a4458e3128d019af1c1d1dbd2bf1dfcbbd2 plus untracked files
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git status/diff/check-ignore/log; sed/grep/cat on repair source and evidence; python3 -I hash and reference audit of 23 renamed files, build/log-index.json and evidence JSON references; shasum of /tmp/phase7a-repair1-final-check.log (matches 26f7ad07…2497); find/stat mtime check on the retained Phase 6 export. No sbt, tests, AWS/provider calls or writes.
TEST RESULTS: Not run by reviewer. Raw log confirms 596 passed / 0 failed, REPAIR1_EXIT_CODE=0; targeted storage 10/10, independent storage 27/27, CSV 4/4 per retained evidence.
VALIDATION RESULTS: F1 closed (strict string-count parser, producer-compatible fixtures, regressions, bounded real-export smoke with export unmodified). F2 closed (23 renames byte-identical, not ignored, references resolve, .gitignore unchanged). N9 info. N1–N8 open, nonblocking.
ASSUMPTIONS: The retained 6FG export represents the current Phase 6 metadata encoding.
RISKS: No live AWS; no real-data CSV replay; no full real-data cache load; N1–N3 affect the 7B loader and CLI.
MANUAL ACTION REQUIRED: Human reviews and commits Subphase 7A on phase-7 before 7B starts.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none for 7A
NEXT GATE: Human commit of 7A, then Subphase 7B Step 0


## Subphase 7B — user-supplied external review (repair round 1 input)

VERDICT: REQUEST-CHANGES for Subphase 7B.

Most of 7B holds up: ID and hash parity, endpoint and support checks, read-only parameterized templates, the vector key and text-hash handling, the N1 pointer, the N3 token, and the CLI gate. Two confirmed defects in the Neptune loader and reader block approval. Both show up only against real Neptune responses, so the stubs didn't catch them. Each is a small, local fix. This is an independent code review only; it isn't human acceptance.

Findings

Blocking

F3 — High — The loader can't recover from a failed Neptune load, and it misreads some final load states
- Where: modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/NeptuneGraphLoader.scala:111-145 and :162-167
- The job registry pins the first load ID forever. The loader registers one Neptune load ID per run ID and export fingerprint (neptune-job:<runId>), and every later rerun reuses it (case Found(record) => record.uri). When that job has failed, each rerun:
  - redoes validation, then gets Unchanged for every upload;
  - polls the same failed job and returns neptune-load-failed again;
  - never submits a new job.
- Recovery would need a human-approved deletion. Registry rows are immutable conditional puts, so the only way out is deleting a DynamoDB row. That is data destruction, which needs the human gate.
- The status check is a substring test. Only statuses containing FAILED, CANCELLED or ERROR count as failures. The AWS loader status list (https://docs.aws.amazon.com/neptune/latest/userguide/loader-message.html, read 2026-10-22) has two more final states:
  - LOAD_COMMITTED_W_WRITE_CONFLICTS. AWS says to "try resuming the load and it will likely succeed".
  - LOAD_DATA_DEADLOCK.

  The loader treats both as still running. It polls them until the timeout, and later reruns poll the same job again, so the resume AWS recommends never happens.
- No test covers a failed load or a rerun after one (searched for LOAD_FAILED and neptune-load-failed).
- Impact: This breaks plan §7.5 ("loaders are safe to rerun") and the course gate that loaders are idempotent. The most likely outcome of the first live run in Phase 14C (wrong IAM role, S3 access denied, a write conflict) would leave that export permanently unloadable without a human-approved deletion.
- Owner: storage-engineer (modules/storage/**), plus test-engineer (tests/**) for the independent case.
- Acceptance check:
  a. Classify statuses by explicit list:
     - LOAD_NOT_STARTED, LOAD_IN_QUEUE and LOAD_IN_PROGRESS keep polling.
     - LOAD_COMPLETED is success.
     - Every other status is a final failure, recorded with its sanitized status code.
  b. After a recorded final failure, a rerun submits exactly one new job (for example, a registry version keyed by fingerprint plus attempt number). It never reuses a failed load ID.
  c. After a timeout with the job still in progress, a rerun still reuses the same load ID and submits nothing.
  d. Tests cover:
     - LOAD_FAILED, then a rerun that submits a new job and completes, with the ledger showing the failure and the retry;
     - LOAD_COMMITTED_W_WRITE_CONFLICTS treated as final on the first poll and resumed on rerun;
     - the timeout rerun reusing its load ID;
     - a completed fingerprint still returning Unchanged.
  e. The README states the recovery behaviour.
- Blocking: yes.

F4 — Medium — The reader can't return a node whose text contains a line break or tab
- Where: NeptuneGraphReader.scala:39 (ujson.read(response.results().toString)); the same pattern is in NeptuneGraphLoader.scala:43.
- Evidence:
  - I disassembled the pinned SDK class, sdk-core-2.56.0.jar StringDocument.toString(). It escapes only \ and ". CR, LF, tab and other control characters come out raw.
  - ujson_3-4.0.2 CharParser contains the "control char (" error and rejects raw control characters inside strings.
  - So node() fails with malformed-graph-response for any node whose raw label contains CR, LF or tab. 7A deliberately preserves those labels end to end ("text round-trips exactly (Unicode, quotes, CRLF)"). Neighbour and community queries are affected the same way whenever a returned raw string holds a control character.
  - The stub tests build Documents from plain strings, so the problem never appears. The real-data sample had no special labels, as the owner report says.
- Impact: Runtime graph retrieval (Phase 9 and later) fails on valid stored data. The loader's status parsing relies on the same fragile serializer, though status strings are low-risk.
- Owner: storage-engineer; test-engineer for the independent case.
- Acceptance check:
  a. Convert the SDK Document into JSON structurally (map, list, string, exact number, boolean, null), never through toString. Use the converter in both the reader and the loader status.
  b. A reader test returns a node whose label contains \r\n, a tab, ", \ and non-ASCII Unicode exactly.
  c. A neighbour or edge property with the same characters also round-trips.
- Blocking: yes.

Nonblocking

- N10 — Low — An invalid edge rejects the whole export instead of being counted. NeptuneExportValidator.scala:211-215, :357-358. One missing endpoint or unsupported coauthor edge rejects the entire export, with no violation count. Plan 7B task 2 says "reject and count". Failing closed is defensible because the CSV is hash-bound, but the README should say so; reporting the number of violations is optional. Owner: storage-engineer.
- N11 — Low — Vector registry failures get misleading reason codes, and identical text with a changed payload is rejected.
  - Where: S3VectorStore.scala:149-153.
  - Any unsuccessful registry write, including a transient outage, is reported as text-hash-conflict or vector-payload-conflict.
  - The same key and text with a different payload (for example a new runId) is rejected rather than reported unchanged. Phase 8 must skip unchanged text before embedding, or it will produce rejections.
  - Owner: storage-engineer.
- N12 — Info — Uploaded files are re-read from disk after validation, not the validated bytes.
  - Where: NeptuneExportValidator.scala:31-56, NeptuneGraphLoader.scala:79.
  - A file changed between validation and upload would be uploaded unchecked. The risk is low because the files are local.
  - Whole-file Vector[Byte] uploads up to 16 MiB also cost a lot of memory.
  - Owner: storage-engineer.
- N13 — Info — Two small CLI composition issues.
  - StorageLoadMain.scala:253-257: main turns every non-zero result into an exception, so a refusal (code 2) exits like any other failure.
  - Real mode keeps the SDK's default retries underneath StorageRetry. Each call is still bounded by apiCallTimeout.
  - Owner: storage-engineer.
- N14 — Info — Some reader queries may be slow at full scale.
  - The shortest-path template lists every path up to the depth limit before sorting by length.
  - Community lookups use CONTAINS scans.
  - Both are capped only by the timeout. This is disclosed; full-scale cost is unverified and belongs to Phase 14C.
- Carried over: N4–N9 remain open as recorded (N6 is 7C). F1, F2 and B1 stay closed.

Checks that passed (no finding)

- Ownership:
  - Each path has one owner (storage, test, coordinator).
  - The Spark replay is confined to modules/spark/src/test/**. It writes only to a fresh target/ output with errorifexists, checks that the retained source is unchanged, and leaves production Spark untouched.
  - The plan snapshot hash matches the original (b54aa123…ebb).
- Validation:
  - Graph validation hashes every source table, the community table and all three CSV datasets.
  - Every CSV row must match its verified source row, so re-signing a changed sidecar cannot slip a different row through.
  - IDs match in both directions, with duplicates rejected.
  - Endpoints and support are checked: support count equals joint publication count, and the support endpoints must be a coauthor edge and a work.
  - Membership JSON keeps converged and iterations.
- Loader:
  - Polling is bounded by both poll count and a monotonic-clock timeout.
  - The run ledger allows a failed stage to restart.
  - A timeout rerun reuses the in-progress job.
  - Reloading an unchanged export submits nothing (tested).
- Reader:
  - The constructor takes only a read-only client and config.
  - All query templates are fixed, parameterized and allowlisted; only the configured depth number is spliced into the query text.
  - Depth, limit, cursor and edge type are checked before any request, the response size is capped, and a timeout hint plus an SDK call timeout apply.
  - The injection test asserts that user text never appears in the query.
- Vectors:
  - Only the five named indexes are accepted.
  - The metadata limits match the documented ones.
  - Batches split at 500 vectors and a byte bound; reads split at 100 keys; queries follow the page token up to a page limit.
  - Retries are bounded, and the rejection report is content-addressed and has no provider text.
  - Every row of the plan's §9 vector test matrix is covered.
- N1: the qualifications are written once and the pointer is checked against the registry, the object hash and the body. The tests show Converged: false and the approximate-P90 note are preserved.
- N3: the transaction token is fixed for the whole logical call, and the lost-reply regression test checks the same token and items.
- CLI:
  - Dry run is the default.
  - Refusal happens before any credential provider or client is built.
  - Profile and environment options are refused without --execute-aws, and conflicting flags are refused.
- Configuration and safety:
  - No hardcoded deployment resources outside tests and README placeholders.
  - The literal secret scan is clean.
  - No live suite yet (that is 7C).
- Evidence: I hashed final-check.txt myself: a149c773…4e5f, 1,365,402 bytes. It shows 144/64/39/38/17/314/8 = 624 passed, 0 failed, PHASE7B_EXIT_CODE=0. The affected targets show 17/48/4 with exit 0. The CLI outputs (84/40/29 nodes/edges/support, 68 cache writes, LOAD_COMPLETED) and the B1 failures match the retained evidence.

Report

STATUS: COMPLETE (review) — VERDICT REQUEST-CHANGES for Subphase 7B
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Independent review of Phase 7 Subphase 7B; git diff 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276 plus untracked files on phase-7
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: git rev-parse/branch/status/diff; shasum on plan snapshot+original (match b54aa123…ebb) and evidence/7b/final-check.txt (match a149c773…4e5f); grep/wc/cat on sources and evidence; javap -c on pinned sdk-core-2.56.0 StringDocument and ujson_3-4.0.2 CharParser (read-only inspection of cached library jars); WebFetch of the course README; aws-knowledge read of the Neptune loader-message doc. No sbt, tests, AWS/provider API calls or writes.
TEST RESULTS: Not run by reviewer. Retained log confirms full JDK 17 check exit 0, 624/0; targeted 17/48/4 exit 0.
VALIDATION RESULTS: F3 (blocking): failed-job reuse plus incomplete final-status classification. F4 (blocking): Document.toString JSON parsing fails on control characters. N10–N14 nonblocking. N4–N9 open as recorded; F1/F2/B1 closed.
ASSUMPTIONS: The pinned SDK's Document.toString and ujson behaviour as inspected apply at runtime; the AWS loader status list was current on 2026-10-22.
RISKS: No live AWS; no full real-data replay or metric-cache load; path/community query cost at scale unverified.
MANUAL ACTION REQUIRED: User routes F3/F4 repairs; no 7B commit until recheck APPROVE.
BLOCKED-ON OWNER: storage-engineer (F3, F4 implementation and module tests); test-engineer (F3, F4 independent tests)
BLOCKED-ON EVIDENCE: NeptuneGraphLoader.scala:111-145,162-167; NeptuneGraphReader.scala:39; NeptuneGraphLoader.scala:43; sdk-core-2.56.0 StringDocument.toString; AWS loader-message status table
NEXT GATE: 7B repair round 1, affected tests plus full JDK 17 sbt check, then user-launched recheck

Next prompt

You are the Phase 7 coordinator for /Users/danny/Documents/UIC/CS441/ScholarChain,
working from /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
(accepted snapshot docs/agent-runs/phase-07/evidence/7a/phase7-plan.md,
SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb).
This is Subphase 7B REPAIR ROUND 1. Do NOT start 7C.

0. Preflight: record branch (phase-7), HEAD (expected
   08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276) and git status --short. The
   uncommitted 7B changes stay in place; proceeding on them is authorized by
   this work order. Ask Step 0 questions only if something is ambiguous;
   otherwise say "No questions for this repair round" and proceed.

1. Append the external reviewer's complete response (which the user pastes
   with this prompt) VERBATIM to docs/agent-runs/phase-07/review.md under
   "Subphase 7B — user-supplied external review (repair round 1 input)".
   Log F3, F4 (blocking) and N10–N14 (nonblocking, listed, not required) with
   owners in docs/agent-runs/phase-07/repairs.md. Do not rewrite earlier
   records. N4–N9 stay open as recorded; F1/F2/B1 stay closed.

2. Fix ONLY the blocking findings, each through its named owner
   (storage-engineer: modules/storage/**; test-engineer: tests/**):

   F3 (High) NeptuneGraphLoader.scala:111-145,162-167. The job registry pins one
   loadId per run ID and export fingerprint, so after a final Neptune failure
   every rerun re-polls the failed job and returns neptune-load-failed; it never
   resubmits. Recovery would need deletion of an immutable registry row. The
   status check is a substring test, so LOAD_COMMITTED_W_WRITE_CONFLICTS and
   LOAD_DATA_DEADLOCK (final per
   https://docs.aws.amazon.com/neptune/latest/userguide/loader-message.html;
   AWS advises resuming after write conflicts) are polled until timeout.
   Acceptance:
   - LOAD_NOT_STARTED, LOAD_IN_QUEUE and LOAD_IN_PROGRESS keep polling;
     LOAD_COMPLETED is success; every other status is a recorded final failure
     with a sanitized code.
   - After a recorded final failure, a rerun submits exactly one new job (e.g.
     registry version keyed by fingerprint plus attempt) and never reuses a
     failed loadId.
   - A timeout rerun with the job still in progress reuses its loadId and
     submits nothing. A completed fingerprint still returns Unchanged with no
     uploads or submission.
   - Module and independent tests: LOAD_FAILED then rerun -> one new
     submission -> LOAD_COMPLETED, with ledger failure and retry evidence;
     LOAD_COMMITTED_W_WRITE_CONFLICTS final on the first poll, then resumed on
     rerun; the timeout rerun reuses its loadId.
   - The README documents the recovery behaviour. No destructive recovery and
     no registry deletes.

   F4 (Medium) NeptuneGraphReader.scala:39 and NeptuneGraphLoader.scala:43
   parse SDK Documents with ujson.read(document.toString). In pinned
   sdk-core 2.56.0, StringDocument.toString escapes only \ and ", and ujson
   rejects raw control characters, so a node label containing CR, LF or tab
   (preserved by 7A) makes node()/neighbors() fail with
   malformed-graph-response.
   Acceptance:
   - A structural Document-to-JSON converter (map, list, string, exact
     number, boolean, null) is used everywhere toString was. No toString-based
     JSON.
   - Tests: node() returns a label containing \r\n, a tab, ", \ and non-ASCII
     Unicode exactly; a neighbour/edge property with the same characters
     round-trips; loader status parsing uses the converter.

   No Spark, core, build or control-file changes. Do not change Phase 6 output,
   IDs or hashes.

3. Rerun the affected targets (storage tests, IndependentStorage*Spec,
   Phase7NeptuneExportSpec), then a fresh full check, using the exact Section 2
   JDK 17 environment:
     cd /Users/danny/Documents/UIC/CS441/ScholarChain
     export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
     export PATH="$JAVA_HOME/bin:$PATH"
     export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
     sbt -batch check
   Report java -version, exact commands and exits, per-group test counts and
   raw log SHA-256. Keep failed runs. Put evidence under
   docs/agent-runs/phase-07/evidence/7b/repair-1/ as Git-visible files (no
   *.log).

4. Do NOT launch any reviewer. No AWS/provider calls, no staging, commit or
   push. Do not edit human records. No 7C work.

5. Return the Section 10 handoff packet and a filled-in RECHECK reviewer prompt
   (Subphase 7B repair round 1) in one fenced code block. List F3/F4 with their
   repair evidence and N4–N14 as open nonblocking items. Then end with:
   "Subphase 7B repair round 1 is ready for review. I have stopped and will
   not start the next subphase until I receive the next prompt." and STOP.


## Subphase 7B — user-supplied external review (repair round 1 recheck): APPROVE

VERDICT: APPROVE for Subphase 7B, repair round 1.

  Both blockers are fixed and every acceptance point holds up in the code and the tests. No new blocking defects. This is an independent code review only; it isn't human acceptance, and nothing is committed yet.

  How the two blockers were fixed

  F3 (a failed Neptune load could never be retried): closed.
  - Status handling is now an explicit list. NeptuneJobAttempts.scala:5-11 defines exactly three pending states: LOAD_NOT_STARTED, LOAD_IN_QUEUE and LOAD_IN_PROGRESS.
    - NeptuneGraphLoader.scala:151-167 treats LOAD_COMPLETED as success and every other status (write conflicts, deadlock, unknown) as final on the first poll.
    - The failure code is sanitized: anything outside [A-Z0-9_]{1,80} becomes UNKNOWN_<hash>, which fits the ledger's reason-code format. The test "unexpected\r\nsecret" → neptune-load-unknown_<12 hex> proves it.
  - A failed job no longer stays pinned.
    - Job attempts are recorded append-only under zero-padded versions (attempt-00…01), with a separate failure marker per attempt.
    - On a rerun after a recorded failure, select() creates exactly one new attempt and submits it with mode=NEW. The failed load ID is never polled again, and no registry row is deleted or overwritten.
    - Picking the latest attempt relies on descending sort-key order. Both the in-memory fake (StorageRows.scala:41-42) and DynamoDB (scanIndexForward(!descending)) order the same way.
  - NEW is a sound recovery mode. The openCypher loader docs (load-api-reference-load, read 2026-10-23) say that reloading an existing node or relationship ID doesn't update its values; it only adds missing labels and properties. So a full reload of the same fingerprint converges on the same graph.
  - A timeout still reuses the running job. It writes no failure marker, so the rerun polls the same ID and submits nothing.
  - Completed loads are still Unchanged. The completion check runs before any upload or submission.
  - Older job records are kept. A job recorded under the previous format gets an append-only failure marker and is then recovered, and its original row is kept.
  - Tests:
    - NeptuneRepairSpec covers four final states, checking modes AUTO→NEW, the exact ledger failure and retry count, both attempt rows, the failure marker, and a third run that returns Unchanged with no new uploads.
    - It also has the timeout case (1 start, 3 polls) and the legacy-record case.
    - The independent IndependentStorageGraphLoaderSpec cases at lines 404-500 check the same behaviour through shared ports and a fresh adapter.
  - README: line 63 documents all of it.

  F4 (the reader failed on text containing control characters): closed.
  - AwsDocumentJson.scala converts SDK documents structurally: map, list, string, BigDecimal number, boolean, null.
    - Strings are escaped by ujson only when rendered back out.
    - It never interprets the SDK's toString output as JSON. That pattern is now gone from the reader, the loader status check and the vector store.
  - Both the reader (execute, node, decodeNeighbor) and the loader's status use the converter.
  - Tests:
    - A label containing \r\n, a tab, a quote, a backslash, Greek, CJK and an emoji round-trips byte for byte, both as a node label and as a neighbour property.
    - 9007199254740993, which is above 2^53, and a 29-digit decimal both keep their exact value and type.
    - The independent reader spec adds a structural node case and a multiline neighbour case.

  Evidence I checked myself

  - Full gate: I hashed repair-1/final-check.txt and got 0d8fb3ec…5ef1, matching the recorded value. The log shows 144/64/39/38/23/320/8 = 636 passed, 0 failed and REPAIR1_EXIT_CODE=0.
  - Affected targets: targeted-1.txt shows 23/54/4 passed and exit 0.
  - Repair scope:
    - The repair touched only the eight paths listed in repair-source-changes.json, all in storage-engineer or test-engineer territory.
    - There is no diff from the base in build.sbt, project/, .gitignore, modules/core or Spark production code.
    - No live suite was added (that is 7C).

  Findings in this round

  Nonblocking; no fix is needed for 7B:
  - N15 — Info — Recovery reloads everything. NeptuneGraphLoader.scala:129. Recovery uses NEW rather than RESUME, so after a failure the whole export is reloaded instead of only the failed files. The result is still correct, as the docs above confirm; the cost is extra load time. Owner: storage-engineer. Revisit only if Phase 14C load times matter.
  - N16 — Info — A lost registry write can leave an orphan job. NeptuneGraphLoader.scala:142-144. If a recovery job is submitted but recording it in the registry fails, the next rerun submits one more job. queueRequest=false stops two jobs running at once, but the first job is left unrecorded. Owner: storage-engineer.
  - Carried over: N4–N14 remain open as recorded, with N6 assigned to 7C. F1, F2, B1, F3 and F4 are closed.
  - Not verified: live Neptune or S3 Vectors behaviour, full-scale query cost, and a full real-data load. I ran no builds or tests.

  Report

  STATUS: COMPLETE (review) — VERDICT APPROVE for Subphase 7B repair round 1
  OWNER: code-reviewer (user-launched, read-only)
  WORK ORDER: Recheck blocking F3/F4 from the 7B external review; cumulative diff from 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276 plus untracked files, with the repair isolated via repair-source-changes.json
  FILES CREATED: none
  FILES MODIFIED: none
  COMMANDS RUN: git rev-parse/branch/status/diff --stat (protected paths: no diff); grep/sed/cat on repair source, tests, README and evidence; shasum of repair-1/final-check.txt (0d8fb3ec…5ef1, matches); aws-knowledge read of Neptune load-api-reference-load (mode semantics, openCypher duplicate-ID handling) and the openCypher format page. No sbt, tests, AWS/provider API calls or writes.
  TEST RESULTS: Not run by reviewer. Retained logs confirm full JDK 17 check 636/0, exit 0; affected targets 23/54/4, exit 0.
  VALIDATION RESULTS: F3 closed (explicit status list, sanitized durable failure markers, append-only attempts with exactly one NEW resubmission, timeout reuse, completed Unchanged, legacy records preserved, ledger history intact). F4 closed (structural Document conversion in reader and loader status; exact control-character text and decimal values tested). N15/N16 info. N4–N14 open, nonblocking.
  ASSUMPTIONS: The Neptune docs on NEW-mode and duplicate-ID handling read on 2026-10-23 describe live behaviour.
  RISKS: No live AWS; recovery reloads the full export; possible orphan job if registry recording fails after submission; full-scale query cost unverified.
  MANUAL ACTION REQUIRED: Human reviews and commits the approved 7B work on phase-7 before 7C starts.
  BLOCKED-ON OWNER: none
  BLOCKED-ON EVIDENCE: none for 7B
  NEXT GATE: Human commit of 7B, then Subphase 7C Step 0

  Next prompt

  You are the Phase 7 coordinator for /Users/danny/Documents/UIC/CS441/ScholarChain,
  working from /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
  (accepted snapshot docs/agent-runs/phase-07/evidence/7a/phase7-plan.md,
  SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb).

  1. Append the external reviewer's complete response (which the user pastes
     with this prompt) VERBATIM to docs/agent-runs/phase-07/review.md under
     "Subphase 7B — user-supplied external review (repair round 1 recheck):
     APPROVE". In repairs.md, append a disposition:
     - F3 and F4 CLOSED by external recheck.
     - N4–N14 OPEN/nonblocking with their recorded owners (N6 assigned to 7C).
     - New N15 (Info: recovery uses NEW, a full reload, not RESUME) and N16
       (Info: possible orphan job if registry recording fails after
       submission) OPEN/nonblocking, owner storage-engineer.
     - F1/F2/B1 remain CLOSED.
     Do not rewrite earlier records.

  2. Commit gate. Record branch, HEAD and git status --short. 7B is committed
     only if phase-7 HEAD is a new commit descending from
     08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276 that contains the approved 7B
     files (including evidence/7b/repair-1/), with a clean working tree apart
     from step 1's appends. If not, tell the user, ask them to commit approved
     7B, and STOP. Never stage, commit or push yourself.

  3. Only after the commit is confirmed, begin Subphase 7C ONLY (plan Section 8,
     Subphase 7C). Step 0: ask ALL questions at once, each with a recommended
     default, then WAIT for answers before any edit or agent launch. Include at
     least:
     - Independent suites (test-engineer, tests/**): confirm the scope in plan
       7C task 1, including the source scan proving runtime-facing code takes
       GraphReader and not GraphLoader. Which modules count as runtime-facing?
       Recommended: rag and services, plus any storage composition used by
       them.
     - N6 (S3 412 existing-key path; run-ledger compare-and-set and
       transaction-cancel stub tests): include in 7C? Recommended: yes,
       test-engineer.
     - N4, N5, N7, N9–N16: defer, or fix any now? Recommended: defer all, and
       record them in the README and owner report for the final report.
     - Live awsIntegration suite (storage-engineer): authored only, never run.
       It covers an S3 round trip, a DynamoDB conditional conflict, a tiny
       Neptune load and query, and a tiny vector write and query. Confirm:
       - the required environment variable names (SCHOLARCHAIN_AWS_ITEST=1 plus
         the explicit profile, as in 7A);
     Neptune load and query, and a tiny vector write and query. Confirm:
     - the required environment variable names (SCHOLARCHAIN_AWS_ITEST=1 plus
       the explicit profile, as in 7A);
     - that the live suite reads resource names from config;
     - a per-run cleanup procedure;
     - a cost bound to document for Phase 14C.
     Recommended: reuse the 7A guard, unique per-run prefixes and keys,
     deletion of only what the suite created, and a documented cost ceiling.
   - Does the build need any change (build-engineer, on demand only)?
     Recommended: none unless compiling the live suite requires it.
   - README completion (plan 7C task 3): schemas, keys, indexes, metadata
     fields, batch sizes, retry policy, idempotency, limits with citations,
     and live-suite cleanup.
   - Any question of your own.

4. Rules: route every edit to its owner per docs/agents.md and plan
   Section 5. Use the exact JDK 17 environment for every sbt command:
     cd /Users/danny/Documents/UIC/CS441/ScholarChain
     export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
     export PATH="$JAVA_HOME/bin:$PATH"
     export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
     sbt -batch check
   Report java -version. Keep failed runs. Evidence goes under
   evidence/7c/ as Git-visible files (no *.log). Never run the live suite.
   No live AWS or provider calls, no staging, commit or push. Do not launch
   any reviewer. Do not edit human records.

5. When 7C is done or blocked: confirm the live suite compiles, is excluded
   from sbt check and was not run, and that a fresh full sbt check passes.
   Return the Section 10 handoff packet and the filled-in 7C reviewer prompt
   in one fenced code block. End with "Subphase 7C is ready for review. I have
   stopped and will not start the next subphase until I receive the next
   prompt." and STOP. Do not start Phase 8.

Tip: Use /btw to ask a quick side question without interrupting Claude's current work

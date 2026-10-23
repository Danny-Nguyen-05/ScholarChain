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

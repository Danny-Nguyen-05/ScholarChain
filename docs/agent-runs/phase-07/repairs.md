# Phase 7 routed findings and carry-overs

## Subphase 7A — Step 0 disposition

The user accepted all coordinator defaults before implementation. This records routing rather than review closure. No reviewer has been launched. Earlier Phase 6 records remain immutable.

| Prior item | Owner / 7A route | Remaining gate |
|---|---|---|
| Yearless coauthor edges | storage-engineer / scoped spark-engineer CSV projection | Exact IDs/support retained, absent years omitted; no fabricated dates/frozen wire changes |
| 6FG F7 duplicated kcore/collaboration | storage-engineer | Verify equivalent views and load canonical rows once; reject conflicting duplicates |
| 6FG F8 loose target keys | storage-engineer | Concrete key/access-pattern and conditional transitions; support edgeId+workId; preserve original proposals |
| N1 non-converged LPA | storage-engineer contracts/docs; spark-engineer retains algorithm ownership | Carry false convergence and iteration limits through consumers; no upstream convergence repair in 7A |
| N2 approximate P90 | storage-engineer docs/contracts | Preserve approximation qualification; no stronger partition-invariant claim |
| 6FG F5 thin/truncated summaries | spark-engineer before Phase 8 | OPEN, not repaired by 7A acceptance |
| 6FG F4 failed same-ID retry | spark-engineer/operator | OPEN; no destructive cleanup authorized/performed |
| 6FG F6 continuity tie winner | spark/domain owners | OPEN before consumers infer selected matched community |
| 6FG F9/N3 scientific and ER coverage wording | spark-engineer/coordinator | OPEN; no real identity accuracy or measured LPA cause inferred |
| 6FG F10/N4/N5/N6 Spark setting/docs/caps/concurrency | spark-engineer | OPEN, outside storage work order |
| Scanner blind spots | test-engineer later source-fence work | OPEN; 7A contract tests do not silently repair Phase 6 scanner |
| 6A F4/F6/F8 wrong-JDK/package guards/docs | build-engineer later release scope | OPEN before release; supported JDK17 path alone not proof |
| EMR/Scala alignment | infra/deploy/build owners Phases 13–15 | OPEN; no cloud runtime selected/tested |
| 6FG F11/F12/N7 retention/counters/process | existing owners/human | Historical evidence retained unchanged; Python counts separate |

The plan has no Section 7.6; the above register is the disclosed interpretation approved through the ten Step 0 defaults. Any newly observed implementation failure will be recorded separately with owner and evidence, without claiming external review.

## Implementation validation — initial targets

- Build dependencyClasspath inspection reached in-progress storage code and failed on String vector indexing and lambda lexical syntax; routed storage owner. Not a completed target or final gate.
- Coordinator first combined targeted run exit1: Spark Neptune CSV suite2/3; sidecar rowCount is encoded Long string and test requested Num. Owner routed to spark-engineer; storage compile and independent targets were not reached. Formatting steps completed. Exact command/log in evidence/7a/targeted-1.json and evidence/7a/targeted-1.txt. Fixture ID fidelity follow-up also remains Spark-owned.

- Targeted2 exit1 at storage compilation: two formatted one-line match expressions failed Scala indentation parsing. No tests reached; routed storage owner. evidence/7a/targeted-2.txt.
- Separate Spark target2 exit1:2/3, revealed actual CSV embedded CRLF -> CRCRLF mutation. Routed Spark owner for lossless writer correction; expected text must remain intact. evidence/7a/spark-targeted-2.txt.
- Native specialist turns briefly errored due platform usage limit; user instructed “keep going”; coordinator resumed the same native owners. No ownership transfer or reviewer invocation occurred.

## Final targeted validation disposition

The named owners repaired the observed local failures; no external review is claimed. Final target5 exit0: storage9/9, independent26/26, Spark4/4; logs and metadata under evidence/7a/. This covers original byte expectations, complete Parquet handoff, duplicate handling and typed error fixes. New tests also cover immutable ledger failure history, same-query/different-idempotency conflict and bounded stream IO retries. Full repository gate remains separate. Nonlocal-return compiler warnings are disclosed, not a failed gate or a claimed repair. Phase6 deferred findings remain as routed above.

## Full gate 1 — source-fence compatibility

Fresh JDK 17 `sbt -batch check` exited 1 after 676.92 seconds. Observed 585 passed / 1 failed across 586 tests: core144, Hadoop64, ER39, Spark38, storage9, independent292 (291 passed/1failed). Build verification was not reached. The sole failure is `IndependentPhase6SafetySpec`: the textual fence flags a String `isEmpty` and two distributed grouped `count` transformations in the new `Phase7NeptuneExport.scala`. No graph collection or driver-count violation is inferred from those three expressions, but the deterministic gate must pass.

Routed to `spark-engineer` for three behavior-equivalent production expressions: String length check and explicit distributed aggregate counts. The test/scanner stays unchanged; its Phase 6 blind spots remain open. All 109 implementation/build/test hashes and mtimes were stable during this failed gate. See `evidence/7a/first-full-check.json` and excerpt. Raw log remains `/tmp/phase7a-final-check.log`, SHA-256 `5da3f4b666f4017c6667b02c245215db4be3670ada16757839ba45d28c2c0e98`.

Next: affected Spark/source-fence target, then a fresh full check. No independent approval or 7B work is implied.

### Source-fence repair target

Spark owner's three production-expression changes passed the unchanged source-fence suite7/7 and CSV suite4/4, exit0, real10.63s. Evidence: `evidence/7a/source-fence-targeted.txt` and `.json`. No scanner exemption or test expectation was added. A fresh full gate is running on the new frozen source snapshot. This is local validation, not external review closure.

### Final full-gate disposition

Fresh full check after the three-expression repair passed594/594, exit0, real680.62s. The unchanged source-safety suite passes inside the full independent292/292; build verification8/8, including the injected-failure probe and tag policy, also passes. Source hashes/mtimes are stable. See final-check.json/excerpt and final-audit.json. This completes local validation only; no external APPROVE or human acceptance is claimed. All Phase6 deferred findings keep their owners/gates; no7B starts.


## Subphase 7A — repair round 1, user-supplied REQUEST-CHANGES

The complete external review is appended verbatim to review.md and retained in evidence/7a/repair-1/external-review.txt. User scope: fix all blocking bugs only. No reviewer launched; no7B.

| Finding | Owner | Status / gate |
|---|---|---|
| F1 High: producer string rowCount rejected | storage-engineer modules/storage/**; test-engineer tests/** | Repair strict ASCII decimal Long parsing, both fixtures and regression; targeted/fullcheck plus optional bounded real-manifest smoke |
| F2 Medium: retained .log files ignored | coordinator phase-07/** | Rename to.txt, update authored references, verify byte hashes and Git visibility; .gitignore unchanged |
| N1 Medium: full qualification duplicated per metric item | storage-engineer | OPEN/nonblocking; no repair in this round; consider shared immutable pointer before7BCLI |
| N2 Medium: CSV always exported, no real-data replay/marker coverage | spark-engineer; storage-engineer7B | OPEN/nonblocking; bounded real CSV replay and sidecar hash verification later |
| N3 Low: transaction retry token missing | storage-engineer | OPEN/nonblocking; fixed logical ClientRequestToken later |
| N4 Low: independent session/reservation TTL expiration | storage-engineer | OPEN/nonblocking; defaultTTLoff unchanged |
| N5 Low: raw idempotency GSI key byte bound absent | storage-engineer | OPEN/nonblocking; validation later |
| N6 Low: S3 412 and ledger CAS/cancel stub gaps | test-engineer | OPEN/nonblocking;7Chardening |
| N7 Info: evidence prefix hardcoded | storage-engineer | OPEN/nonblocking; config later |
| N8 Info: coordinator owner-requested formatting | coordinator/process | OPEN/process note; disclosed, source owners unchanged |

Earlier test reports said actual Spark-written Parquet passed storage, but metadata was hand-written numeric JSON. Those retained results did not prove producer metadata compatibility. This round corrects both fixtures to Long-as-string and records a bounded real-source smoke separately; no earlier report or result is rewritten into a stronger historical claim.

### F2 evidence migration

Coordinator renamed all23 retained .log files under evidence/7a/ to.txt without changing bytes. Updated the build log index, authored references and targeted/Spark-targeted metadata; each now names its retained .txt and hash. All14 original build raw hashes reverified; the classpath excerpt has a separate explicit retained hash. All23 files appear in Git's nonignored file inventory and git check-ignore returns1/no matches. No staging/commit and no .gitignore change. Verbatim review text, original commands and raw/tmp .log references intentionally retain their historical spelling; evidence-migration.json maps the retired repository-local names. This repairs retention references without rewriting results.


### Repair round 1 — final observed gate and disposition

STATUS: COMPLETE for the blocking F1/F2 local repairs and required checks. Independent recheck and human acceptance remain pending.

The fresh JDK 17 `sbt -batch check` exited **0**: **596 passed / 0 failed**, core144 / Hadoop64 / ER39 / Spark38 / storage10 / independent293 / build8. Java17.0.20.1, sbt1.10.7; sbt679s, real681.20s; completed2026-10-22 18:02:48 America/Chicago. The injected format-stage probe error is a passing build self-test. No live integration suite ran.

F1 is repaired and locally validated: exact nonnegative decimal-string Long parsing, corrected module/independent metadata fixtures, malformed-count regressions and a clean forked read-only smoke against three real retained manifests. Earlier tests used actual Parquet with synthetic metadata; they did not prove the producer metadata encoding. The repair evidence makes that distinction explicit. The smoke sampled one row each from researcher/collaboration/kcore and did not load caches or recompute complete table counts/hashes.

F2 is repaired and locally validated: all23 retained logs renamed to Git-visible.txt without byte changes; references updated;23 renamed hashes,14 original build hashes and all live retained index/target references verified. The classpath excerpt has an explicit retained hash separate from its full raw-log hash. Raw/tmp execution history and verbatim review retain their historical.log spelling. .gitignore is unchanged. No files were staged or committed.

All110 scoped source/build/test/documentation hashes and mtimes stayed unchanged during the final gate. Only the four authorized F1 source/test files differ from the reviewed source snapshot. Protected Phase6/control files, real-source metadata hashes and verbatim review match. Tracked diff check exits0; repair source files have no trailing whitespace. All launched jobs and specialist turns ended.

Evidence: `evidence/7a/repair-1/final-check.json`, `final-check-excerpt.txt`, `final-audit.json`, `targeted-results.json`, `evidence-migration.json`, `git-visible-files.txt` and `commands.md`. Raw full gate `/tmp/phase7a-repair1-final-check.log`:1,362,175bytes, SHA256 `26f7ad074aa1db1028558326d8826e30fd6e07937ed8ad511a2d5870f12e2497`.

N1–N8 remain OPEN/nonblocking with their recorded owners. No nonblocking fix, Spark producer/ID/hash change, .gitignore/build change, reviewer launch, cloud/provider call, commit/push, human-gate edit or7B work occurred.

BLOCKED-ON OWNER: None for local repair completion; reviewer and human own acceptance.
BLOCKED-ON EVIDENCE: None for the required local repair gate. Live-service and broader real-data gates remain unverified.
NEXT GATE: User-launched read-only7A repair1 recheck using `evidence/7a/repair-1/rechecker-prompt.md`; no commit until recheck APPROVE. Stop before the next subphase.


## Subphase 7A repair round 1 — external recheck APPROVE disposition

The user-supplied independent reviewer returned **APPROVE** for Subphase 7A repair round 1. Its complete verdict is appended verbatim in review.md. This closes F1/F2 by external recheck; it is not human acceptance, a commit or permission to bypass the next commit gate. Historical records above are preserved.

| Finding | Status | Owner / next gate |
|---|---|---|
| F1: real export string rowCount rejected | **CLOSED by external recheck** | storage-engineer and test-engineer; producer-compatible fixtures, strict count parser, regressions and bounded real-source smoke verified |
| F2: retained .log evidence ignored | **CLOSED by external recheck** | coordinator; 23 byte-identical .txt renames, Git visibility and live references verified; .gitignore unchanged |
| N1: source-run qualifications copied per metric item | **OPEN / nonblocking** | storage-engineer; raise shared runId+hash pointer in 7B Step 0 |
| N2: no real-data CSV replay; sidecar/completion coverage | **OPEN / nonblocking** | spark-engineer and storage-engineer; raise bounded replay and loader sidecar hash verification in 7B Step 0 |
| N3: transaction retry lacks fixed ClientRequestToken | **OPEN / nonblocking** | storage-engineer; raise fixed logical transaction token in 7B Step 0 |
| N4: session/reservation TTL can diverge | **OPEN / nonblocking** | storage-engineer; confirm deferral in 7B Step 0 |
| N5: raw idempotency GSI key byte limit absent | **OPEN / nonblocking** | storage-engineer; confirm deferral in 7B Step 0 |
| N6: S3 412 and ledger CAS/cancel stub gaps | **OPEN / nonblocking** | test-engineer; 7C hardening, confirm in 7B Step 0 |
| N7: hardcoded evidence prefix | **OPEN / nonblocking** | storage-engineer; confirm deferral in 7B Step 0 |
| N8: coordinator ran owner-requested formatter | **OPEN / nonblocking process note** | coordinator; disclosed ownership/execution remains unchanged |
| N9: decimal parser accepts leading zeros | **OPEN / nonblocking informational** | storage-engineer; reviewer says no fix needed, confirm deferral in 7B Step 0 |

Commit gate observed after receiving approval: branch phase-7, HEAD still98dd2a4458e3128d019af1c1d1dbd2bf1dfcbbd2. Approved 7A files remain modified/untracked. Human commit is required before 7B begins. Coordinator has not staged, committed, pushed, launched a reviewer or started 7B; no 7B base/preflight is recorded. Existing 596/0 test evidence is retained; no build/test rerun for this documentation-only disposition.

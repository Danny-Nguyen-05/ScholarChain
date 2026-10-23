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


## Subphase 7B — accepted Step 0 carry-over routing

Human commit confirmed: phase-7 HEAD 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276, descendant of 7A base, clean working tree and approved 7A files tracked. This supersedes the earlier observed uncommitted status without rewriting it.

User accepted all recommended defaults. N1 source qualification pointer and N3 fixed logical transaction token routed to storage-engineer. N2 loader sidecar hash verification routed to storage-engineer and bounded real-data CSV replay to spark-engineer (scoped local test harness only; production exporter unchanged). N4–N9 remain OPEN/nonblocking and deferred, N6 to 7C. F1/F2 stay CLOSED. No live-service behavior is verified by this work.


### Subphase 7B integration repair B1 — researcher alias index sequencing

Observed during required bounded real-data CLI smoke, after fixture target passed: graph validator accepted84nodes40edges29support, cache rejected `missing-resolution-endpoint`. Both failing attempts retained under evidence/7b (raw/excerpt distinctions and hashes in cli-smoke-results.json). Storage owner confirmed the multiline invalid-node conditional had the subsequent researcher index write in its indented semicolon body, so valid nodes were not indexed for alias resolution. This was not exposed by earlier standalone name/metric fixtures. Owner repaired explicit conditional braces followed by unconditional valid-node indexing and added a positive mention→researcher RESOLVES_TO regression asserting canonical and alias cache entries/evidence. No producer, dataset, IDs or hashes changed. Rerun pending at this entry; later final results supersede pending status without rewriting the failures.


### Subphase 7B — final affected validation and carry-over disposition

The final affected invocation passed storage17/17, independent storage48/48 and CSV4/4, exit0 in24.10 seconds. Both actual-sample CLI modes then passed:84nodes40edges29supportrows,68 entity candidate writes; fake graph state LOAD_COMPLETED. B1 is repaired and locally validated by its positive alias regression and actual sample. Two added vector pagination cases cover101hits across pages and exact page-budget refusal. Evidence: `evidence/7b/targeted-cli-2.txt` and `.json`.

| Prior item | 7B disposition | Owner / remaining gate |
|---|---|---|
| F1 / F2 | Remain CLOSED by the 7A external recheck | No reopening or historical record rewrite |
| N1 | Implemented and locally validated: full qualifications once, shared retrievable runId+hash pointer; metric rows retain per-row qualifications | storage-engineer; external 7B review pending |
| N2 | Loader verifies authoritative source and CSV logical hashes/projections before upload. Bounded actual-data CSV replay and local CLI passed | storage-engineer / spark-engineer; original producer still exports CSV on every Phase6 run and its completion marker does not bind the sidecar. Full replay/live service remain unverified |
| N3 | Implemented and locally validated: fixed token per logical transaction retry, including committed-write/lost-reply regression | storage-engineer; external 7B review pending |
| N4 | OPEN / nonblocking; TTL divergence deferred, TTL off by default | storage-engineer |
| N5 | OPEN / nonblocking; idempotency GSI key length validation deferred | storage-engineer |
| N6 | OPEN / nonblocking; two additional SDK stub paths remain 7C | test-engineer |
| N7 | OPEN / informational; configurable evidence prefix deferred | storage-engineer |
| N8 | OPEN / process note; owner-requested coordinator formatting remains disclosed | coordinator |
| N9 | OPEN / informational; leading-zero count parsing remains accepted, no fix required | storage-engineer |

The source is frozen for the full check. This is implementation evidence, not independent approval or human acceptance. No reviewer, live service, stage/commit/push, source dataset rewrite or7C work occurred.


### Subphase 7B final full gate

Fresh full check passed **624/624**, exit0, real703.46s; groups 144/64/39/38/17/314/8. All291 source hashes and mtimes unchanged. This completes local validation for B1 and accepted N1–N3 work; external review is pending. N4–N9 remain OPEN/deferred. No7C or live service claim. Evidence: evidence/7b/final-check.json and final-check.txt, SHA256 `a149c77307a1a6f9829b5b73ae9386107707e94bdd1e353724d1cd53032e4e5f`.


## Subphase 7B repair round 1 — external REQUEST-CHANGES

Complete review and next prompt appended verbatim to review.md; duplicate original text in evidence/7b/repair-1/external-review.txt. Only blockers are in this repair scope.

| Finding | Owner | Disposition / acceptance |
|---|---|---|
| F3 High: failed load ID pinned; incomplete final-state classification | storage-engineer modules/storage/**; test-engineer tests/** | OPEN/blocking; explicit pending/success/final classification, sanitized status evidence, append-only recoverable attempts, pending-timeout reuse and completed unchanged; module/independent regressions and README |
| F4 Medium: Document.toString corrupts control-character JSON | storage-engineer; test-engineer | OPEN/blocking; structural typed Document conversion in reader/loader; exact special-text node/property regression and primitive/nested conversion tests |
| N10 Low: invalid export fails closed without violation count | storage-engineer | OPEN/nonblocking; listed only, no repair required |
| N11 Low: vector registry errors mislabeled and payload changes reject | storage-engineer | OPEN/nonblocking; future Phase8 caller/adapter handling |
| N12 Info: upload re-reads source after validation; memory bound | storage-engineer | OPEN/nonblocking; local mutation/time-of-check limitation remains |
| N13 Info: CLI refusal exit exception and nested SDK retries | storage-engineer | OPEN/nonblocking; no CLI or retry-policy change in this round |
| N14 Info: full-scale path enumeration and CONTAINS cost | storage-engineer; Phase14C measurement | OPEN/nonblocking; scale unverified |

N4–N9 remain OPEN/nonblocking with existing owners (N6 → 7C). F1/F2/B1 remain CLOSED. N1/N3 were verified by the reviewer; N2 producer-side sidecar binding and broader real-data limits remain disclosed. No historical result or human decision rewritten.


### Repair round 1 — affected validation

First repair invocation passed storage23/23, independentStorage54/54 and CSV4/4, exit0 in19.40 seconds. F3 recovery/status/timeout/completion/legacy cases and F4 structural primitive/numeric/text cases pass in module and independent tests. Five existing paths changed (README, loader, reader, two independent suites) and three storage paths were added (two helpers, one module suite). No Spark/core/build/control or prior evidence content changed. Full check is running on frozen sources; external closure remains pending. See evidence/7b/repair-1/targeted-1.txt/.json, repair-source-changes.json and owner reports.


### Repair round 1 — final local disposition

F3 and F4 are repaired and locally validated; independent recheck remains pending. Fresh full gate exit0: **636 passed /0failed**, groups 144/64/39/38/23/320/8, real680.86s. All298 source hashes/mtimes stable. Evidence: repair-1/targeted-1.txt/.json, final-check.txt/.json and final-audit.json. Full raw SHA256 `0d8fb3ecc98dddf264ccba022a7941e49fff44c21e404357fa580daf3f715ef1`. N4–N14 remain OPEN/nonblocking; F1/F2/B1 stay CLOSED. No nonblocking repair, reviewer, cloud/provider call, stage/commit/push or7C work.


## Subphase 7B repair round 1 — external recheck APPROVE disposition

The complete user-supplied independent recheck is appended verbatim to review.md. F3/F4 are CLOSED by external recheck; no new blocking finding. This is independent review, not human acceptance or a commit. Earlier records remain intact.

| Item | Status | Owner / next gate |
|---|---|---|
| F3: pinned failed load and final-status handling | CLOSED by external recheck | storage-engineer and test-engineer; append-only recovery/status/timeout/legacy/history acceptance verified |
| F4: Document.toString loses control-character JSON | CLOSED by external recheck | storage-engineer and test-engineer; structural exact-value conversion and node/property regressions verified |
| F1/F2/B1 | Remain CLOSED | Prior review dispositions preserved |
| N4: TTL divergence | OPEN/nonblocking | storage-engineer |
| N5: idempotency GSI key byte limit | OPEN/nonblocking | storage-engineer |
| N6: remaining SDK stub paths | OPEN/nonblocking | test-engineer, assigned to 7C |
| N7: evidence prefix configuration | OPEN/nonblocking | storage-engineer |
| N8: formatter process note | OPEN/nonblocking | coordinator |
| N9: leading-zero count parsing | OPEN/nonblocking | storage-engineer |
| N10: fail-closed export without violation count | OPEN/nonblocking | storage-engineer |
| N11: vector registry reason/payload semantics | OPEN/nonblocking | storage-engineer |
| N12: validation/upload re-read and memory cost | OPEN/nonblocking | storage-engineer |
| N13: CLI exit/retry composition | OPEN/nonblocking | storage-engineer |
| N14: full-scale path/community cost | OPEN/nonblocking | storage-engineer; Phase14C measurement |
| N15: NEW-mode recovery reloads the full export | OPEN/nonblocking, Info | storage-engineer; revisit if Phase14C load times matter |
| N16: possible orphan job after submission if registry write fails | OPEN/nonblocking, Info | storage-engineer |

Commit gate observed after approval: branch phase-7, HEAD still08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276 (the 7B base). Approved 7B code/evidence remains modified/untracked; the required human commit is absent. Full observed status and review-transcription hash are recorded in evidence/7b/repair-1/post-review-commit-check.json. Coordinator has not staged, committed, pushed, launched agents/reviewer or started 7C. No build/test rerun for these documentation-only appends; prior636/0 evidence remains the retained gate. User must commit approved7B before 7C Step0.


## Subphase 7C — commit gate and accepted carry-over scope

Approved7B is committed as c911b236f2a8c02b7422df56f8c334d47fff7ad3 on phase-7, descendant of08e3d212, including repair-1 evidence and external approval records; preflight tree clean. This supersedes the earlier observed uncommitted status without rewriting it. User accepted all7Cdefaults. N6 SDK stub gaps assigned to test-engineer for7C; N4,N5,N7,N9–N16 remain OPEN/nonblocking and deferred, N8 remains a process note. F1/F2/B1/F3/F4 stay CLOSED. Storage owner authors the guarded live suite and documentation only; its execution stays a later human-approved14Cgate.


### Subphase 7C authoring checks — first failures

Two affected checks caught local authoring issues, both retained. C1 (test-engineer): the new SDK ledger-CAS regression expected a string revision, but the stored RunRecord wire uses numeric5; assertion corrected, production format unchanged. First run27/28 passed, exit1. C2 (storage-engineer): offline live-journal test found the default planned state omitted by serialization; writer now emits explicit planned/created/cleaned states and all item fields. Live configuration compiled successfully, normal storage26/27 passed, exit1; live body excluded and independent target not reached. Evidence: evidence/7c/independent-targeted-1.txt/.json and targeted-2.txt/.json. Final affected rerun pending. These do not close deferred N4/N5/N7/N9–N16.


### Subphase7C final local disposition

C1 test revision assertion and C2 explicit journal serialization fixes pass; final support-prefix fixture consistency check passes. N6 S3412 and RunLedgerCAS/cancel paths are locally covered, external review closure pending. Other N4/N5/N7/N9–N16 remain OPEN/nonblocking, N8 remains a process note. Fresh full gate exit0: **659 passed/0failed**, groups144/64/39/38/27/339/8, real684.21s. Live suite compiled, excluded from normalcheck, never run. No production/build/core/Spark/control or human record edit. Evidence7c/final-check.txt/.json SHA256 `3da90e0bd60d8948809f3159f4ab24ab85a46d58ddb5ba0a47d46982368e8e2f`; all306frozen source hashes/mtimes unchanged. External review/human closeout remain pending; noPhase8.


## Subphase 7C — external review dispositions

The complete user-supplied verdict, findings, confirmation notes and report fields are appended verbatim to review.md. APPROVE is independent review, not human acceptance. Earlier records remain unchanged.

| Item | Status | Owner / next gate |
|---|---|---|
| N6: S3412 and ledgerCAS/cancel SDK paths | CLOSED by7C external review | test-engineer; coverage verified |
| 7C-M1 Medium: graph cleanup marks cleaned without DELETE counts/absence | OPEN/nonblocking for7C; REQUIRED beforePhase14C execution/cleanup | storage-engineer; user explicitly requests repair now |
| 7C-L1 Low: passed-retained before ledger snapshot | OPEN/nonblocking; not in this repair | storage-engineer |
| 7C-L2 Low: runtime fence character/interpolation masking blind spots | OPEN/nonblocking; repair before runtime modules gain code | test-engineer |
| 7C-L3 Low: live index runId/textHash filterability prerequisite absent | OPEN/nonblocking | storage-engineer; infra-engineer Phase12 |
| 7C-I1: coordinator-assembled owner report after usage limit | OPEN/process acknowledgement | human/coordinator; human Phase7 gate |
| 7C-I2: course live integration execution deferred to14C | OPEN/course-deviation acceptance | human Phase7 gate |

N4/N5/N7/N9–N16 remain OPEN/nonblocking with recorded owners; N8 process note retained. F1/F2/B1/F3/F4 remain CLOSED. No human acceptance inferred.

### User-authorized repair scope

User instruction after the reviewer prompt: “Fix the first medium bug for me”. This explicitly authorizes only7C-M1 repair now and supersedes the reviewer's generic documentation-only/no-repair next prompt for that finding. No questions are needed; acceptance is explicit. Existing uncommitted7C stays in place, HEAD remainsc911b236 onphase-7. The human commit is still absent; no agent will stage/commit/push. This repair will end with affected/full JDK17 checks and a user-launched recheck packet, before any Phase7 human gate/Phase8. No live suite/AWS/provider calls or actual cleanup. L1/L2/L3 and informational findings remain unchanged.


### 7C-M1 — affected repair validation

User-requested M1 repair now passes offline count/absence/journal-ordering regressions. Affected normalstorage32/32 and independentStorage73/73, exit0 in14.30s; live configuration compiles, sole live body and actual cleanup never run. Two test-owned module files added, AwsLiveRun wiring and README changed; no other finding repaired. Full check is running on frozen308-file source/build/test/README snapshot. External repair recheck remains pending. Evidence: evidence/7c/repair-1/targeted-1.txt/.json, acceptance-matrix.md and storage-owner-report.md. N6 stays CLOSED; L1/L2/L3 and other deferred items remain OPEN.


### 7C-M1 — final local repair disposition

M1 repaired and locally validated, external recheck pending. Count and separate read-side absence checks precede graphcleaned journal state. Fresh fullgate exit0 **664passed/0failed**, groups144/64/39/38/32/339/8, real681.26s; affected32/73passed. All308frozen source hashes/mtimes unchanged. Full raw SHA256 `f225a4ecaa93d920ae1476211ab638bc1f36b0120bf2e078eb5d0308820773b3`. Live suite compiled, notrun; actual cleanup notrun. NoL1/L2/L3repair; N6closed andallotherdeferreditemsretainowners/status. Evidence repair-1/targeted-1.txt/.json, final-check.txt/.json, acceptance-matrix.md andfinal-audit.json. Human commit remainsabsent; no agentstagecommitpush/humangate/Phase8.

# Phase 11 external review record

## Subphase 11A

No user-supplied external review has been received. No reviewer was launched by the coordinator or test specialist. Implementation evidence and passing gates do not constitute independent approval or human acceptance. Append the user-returned verdict verbatim here on the next authorized prompt.

### user-supplied external review

The earlier placeholder is historical. The user supplied the following external verdict and instructed that it be appended verbatim. This is independent review approval, not a human phase gate or commit authorization.

----- BEGIN VERBATIM 11A VERDICT -----
VERDICT: APPROVE for Subphase 11A (data-plane adversarial tests). No blocking findings.

Verified against files: HEAD equals base 0c5ee89994b5b738a3490ef5e8f032fdc67327b2; git diff to base empty; 33 untracked files match handoff-files.json/git-status.txt, only tests/** (three Adversarial* suites) and docs/agent-runs/phase-11/**; protected fingerprints 224 production / 19 build / 103 existing independent files match before and after. Ownership: test-engineer tests, coordinator evidence, no build-engineer needed, no reviewer launched, no human records. Hand oracles re-derived and correct: ring 2/2/2, B3/B4 3/5/2, K1 5/5/3, pendants 1/1/1, isolate 0/0/0; components 1/5/6/6; unique routes R1-R2-R3, B1-B3-B4-B6, P1-K1-P2; R1->B1 no-path; participation B3/B4 4/9, K1 14/25, P1/P2 0, isolate 0 (spark README:85, unweighted, isolate zero); 64C2=2016 with 63 per ordinal, 2015 rejected; 8C2=28 with 7 per member, 27 rejected; 257>8 OversizeBlock with Input=257; NFC hashing per core README:168; NFKC per ER README:341; U+0410 lowercases to U+0430. Counts: coverage.json 30 existing + 15 new = 45 distinct; per-category counts match test-report; JUnit 8+4+3 new; tests 632/83 -> 647/86; total 1216 -> 1231; four Adversarial XML reports 0 failures, written during the full check. /tmp/phase11a-final-check.log 1,717,764 bytes, SHA-256 07f515f3f51427dac4a730bf2ab0af39c3c7d005111b335b7c6c6a78fff32758 matches; targeted-1/2/3 hashes match development-runs.json. DataPlane last edit 14:34:56 precedes the full check (~14:38:29–14:50:37); excerpt line 9 "compiling 1 Scala source" shows it was compiled. ExposedDefect 0; nothing tagged, ignored or skipped; no cloud/provider calls; no hardcoded endpoints/accounts/buckets/models.

Findings (all nonblocking):
N1 Low (coordinator): owner-report.md:33 and test-report.md:33 say formatting "passed" on attempt 2, but evidence/11a/phase11a-targeted-2-excerpt.txt:7 shows "scalafmt: Reformatted 3 Scala sources" (test-engineer-owned files, rewritten at the owner's request). Precision only. Acceptance: in 11B, state formatter rewrites explicitly or use scalafmtCheck for coordinator gate runs. Blocking: no.
N2 Low (coordinator): evidence/11a/full-check-start.json start_epoch 19:35:39Z (14:35:39 local), file mtime 14:39:17, sbt launched ~14:38:29; the record was written after launch, and the test-engineer's last edit (14:34:56) landed during targeted attempt 3. The result still holds. Acceptance for 11B: write the start record once immediately before launch, never rewrite it, and confirm specialist writing has stopped before any gate. Blocking: no.
N3 Low (test-engineer): AdversarialDataPlaneSpec.scala:114-116 disjointness is implied by different work keys, and the two orders are never compared downstream; AdversarialBlockingReplaySpec.scala:156-161 hash equality follows from :155, and :161 is always true; test-report.md:72 "independent SHA256" overstates. Optional. Blocking: no.
N4 Info (11C lead; hadoop-engineer if confirmed): AdversarialDataPlaneSpec.scala:149 expects normalizedTitle to keep <i> markup, valid under TextNorm.scala:9-14 and HadoopPrepSpec.scala:59; but DerivedRecords.scala:342-345 builds title-year block keys from normalizedTitle while ER normalization strips markup (ER README:341-342), so a cross-source block may be missed. Unverified; review in 11C. If repaired, the test-engineer updates this assertion. Blocking: no.
N5 Info: disclosed limits accepted: scan-level reading of earlier reports (reading-ledger.json), exact model revision unavailable, raw logs only in /tmp (hash-verified, not reboot-durable), synthetic local fixtures only, Phase 5–10 carried limits. Blocking: no.

Unverified future gates: 11B runtime categories 12–20; 11C whole-repository review and repairs; live AWS (Phase 14); human gate and commit.
----- END VERBATIM 11A VERDICT -----


## Subphase 11B

No user-supplied external review of 11B has been received. No reviewer was launched. Passing implementation gates are not independent approval or a human gate. The user may return a verdict to append verbatim on a later prompt.

### user-supplied external review

Received 2026-10-28. The preceding placeholder is historical. The following verdict is retained verbatim from the user's supplied NEXT PROMPT. This records an independent external review, not a human phase gate. The reviewer reported read-only inspection, no builds/tests, no AWS/provider calls and no file edits.

```text
VERDICT: APPROVE for Subphase
11B, no blocking findings; nonblocking F11B-1 (Medium, service-engineer/test-engineer, 11C
input: QueryService.scala:152-156 + DynamoStorage.scala:137 — a lost reply on the
body-binding conditional write returns Retried(1, Rejected("conditional-conflict")); submit
returns 503 without scheduling while the row is bound QUEUED; same-key replay returns 202
QUEUED indefinitely until TTL; N04 covers only the clean-rejection variant), F11B-2 (Low,
test-engineer: AdversarialRuntimeHttpSpec.scala:138-140 pins replay-after-failed-bind 503
as current behavior rather than a stated requirement), F11B-3 (Low, test-engineer /
service-engineer: AdversarialRuntimeBoundarySpec.scala:77-98 exercises only
ServiceConfig.fromEnvironment despite "before composition", and the generic error does not
name the missing key), F11B-4 (Info: category-16 E11 mapping; weak summary "3" check backed
by exact claim values). Carried: 11A N3/N4/N5, /tmp raw-log durability, model revision
unavailable, Phase 9 NB1–NB10, Phase 10 F7, F8, F10–F17.
```

The reviewer cross-checked the five raw-log hashes, four current source hashes, five start-record hashes/mtimes, writing barriers, append-only tracked diff and 41-file untracked inventory. Reported counts reconcile: 1,231 + 17 = 1,248 tests; 152 + 3 = 155 reports; 647 + 17 = 664 independent tests. The reviewer found no hits for six synthetic canary strings in the full raw log. F11B-1 is a code-reading lead, not an executed reproduction. All four nonblocking findings are logged in repairs.md; no repair is authorized in this recording step.

Next gate: commit approved 11B on phase-11, then the first 11C stop point only. No 11C assembly has started.


## Subphase 11C

No 11C reviewer has been launched or selected. The coordinator assembled the first-stop-point packet only. The user-supplied 11A/11B APPROVE records above remain unchanged; 11B is committed as 2b0aee044f243f01bbb603170d09f5c507df8bb7. This is a pending-review checkpoint, not an approval or human gate. No independent 11C verdict has been received.


### user-supplied external review — initial 11C REQUEST_CHANGES

VERDICT: REQUEST_CHANGES for Subphase 11C, initial whole-repository review.

R11C-1 is a major correctness defect and is blocking. It is the F11B-1 lead, now confirmed by code reading. R11C-2 is coupled to it and is also blocking. Everything else is nonblocking, an accepted limitation, or a future gate. I did not run any builds or tests.

The user supplied the review and explicitly instructed “Fix all blocking bugs for me.” Findings are logged in repairs.md; only repair round 1, batch 1 is authorized. The reviewer edited nothing and ran no builds, tests, AWS or provider calls. Its code-derived confirmations were not executed reproductions.

Reviewer limitations: most of approximately 40k lines of main code were not read line-by-line; core, ER/Spark internals, RAG planner/retrieval, storage loaders/validators, dataset scripts and 726 ER dataset files were not read in full; earlier reports were grep-scanned; course README was read through a summarizing fetch. R11C-6 downstream impact was not traced. All prior limitations and human gates remain.


### Subphase 11C repair round 1 — pending independent recheck

Authorized batch 1 R11C-1/R11C-2 plus user-approved R11C-5 passed local affected/full gates. No recheck reviewer has been launched and no independent repair verdict received. The initial REQUEST_CHANGES above is retained verbatim; local passing tests do not supersede it with self-approval.


### user-supplied external review — 11C repair round 1, batch 1

VERDICT: APPROVE for Subphase 11C repair round 1, batch 1. No blocking findings remain.

2. Findings, in the 12-point order

1. Correctness and data loss

R11C-1 (High, was blocking): CLOSED.
- How the fix works now:
  - QueryService.scala:166-209: bind builds the exact intended revision-1 session. Its payload carries the fingerprint, request and trace IDs, and a fresh bindingToken (UUID, :181-182).
  - The caller dispatches only when the result is Written(s) with s == intended (:189-193), or when a primary read returns a row equal to intended (:197-205).
  - Because the token is random, a losing binder cannot claim another caller's write even when both reuse the same client IDs.
- Fault injection is genuine: InMemoryQuerySessionStore is the real RowSessions CAS running over MemoryRows (InMemoryStorage.scala:92-95). The fakes apply the write and then return Retried(1, Rejected("conditional-conflict")), at SessionBindingRecoverySpec.scala:91-103 and AdversarialRuntimeHttpSpec.scala (lost-reply test).
- The tests assert every acceptance item:
  - one applied binding and one workflow call
  - persisted SUCCEEDED with a matching result
  - a stored-result replay with no rerun, and 409 for a changed body
  - in the HTTP case, the literal verified publicationCount "3", audit ANSWERED, one workflow call and one LLM call
- Red evidence: before the repair, the red-2 run executed 4 tests and all 4 failed for the right reason (Left(ApiError(503,...)), from /tmp/phase11c-r1-red-2.log). They pass now.

R11C-2 (Medium, was blocking): CLOSED.
- How the fix works now: awaitBinding returns the unbound row (:89-105), and reconcile sends a "{}" reservation to bind, which competes in the revision-0 CAS (:215-218).
- Clean-rejection tests:
  - The module test asserts the first request gets 503 with 0 workflow calls, the replay completes, and the CAS ran twice.
  - The HTTP test asserts the initial 503 with zero workflow and model calls, 2 bind attempts with 1 applied, a stored replay without rerun, and a changed-body 409.
- Concurrency tests: both variants run two QueryService instances on one shared store with identical client IDs (:147-225). A rendezvous latch makes both contenders reach the CAS, and the loser reads the winner's QUEUED snapshot before the winner returns. The tests assert 3 bind attempts, 1 applied binding and 1 workflow call.
- Test sensitivity check: if the token comparison were removed, the lost-reply variant would dispatch twice, which calls.get() == 1 would catch.
- Old assertion removed: the test no longer requires a permanent 503.

R11C-7 (new): Low. Pre-existing, not a regression. Code-derived and unexecuted. Nonblocking.
- Where: QueryService.scala:57-61 and :215-226, with StorageRows.scala:221 and RowCodec.map at :78-86.
- Failure input: createIfAbsent's transaction exhausts its transport retries without writing anything, so it returns Retried(n, Rejected("transport-retry-exhausted")).
- Actual: reconcile reads a Missing row, so POST /v1/query returns 404 "The requested job was not found."
- Expected: 503 with retryable: true.
- Impact: a misleading terminal-looking status on the submit route. The pre-repair code behaved the same way.
- Owner: service-engineer.
- Acceptance: a module test where retried creation leaves no row expects 503 with retryable: true and no workflow run.

R11C-8 (new): Low. Code-derived, residual double fault. Nonblocking.
- Where: QueryService.scala:197-205 and README:301-304.
- Failure input: the binding write applies and its reply is lost, and the reconciling primary read then fails transiently.
- Actual: the request returns 503 and leaves the row bound QUEUED with no dispatcher. Later same-key replays get 202 QUEUED indefinitely, because the default TTL is None.
- Why it is nonblocking: it takes two consecutive store faults, each after its own retries. It falls under the disclosed limit that there is no durable dispatcher. The README says "a permanent store outage can prevent reconciliation", but a transient failure on the read is enough.
- Owner: service-engineer, at a deployment gate.
- Acceptance: a bounded retry of the reconcile read, or a lease/reclaim for stale QUEUED rows, or README wording that covers the transient double fault.

2. Contract and schema drift

No new findings. The binding payload adds a bindingToken field. The job and result views do not expose it, because job builds its response from an explicit field list (:283-308).

3. Artifact ownership violations

No new findings.
- service-engineer (/root/service_engineer_11c_r1) wrote modules/services/**: QueryService.scala, README.md and the new SessionBindingRecoverySpec.scala.
- test-engineer (/root/test_engineer_11c_r1) wrote only tests/**, specifically AdversarialRuntimeHttpSpec.scala.
- Coordinator wrote only under docs/agent-runs/phase-11/**, and the five reports are append-only (numstat shows 0 deletions).
- The 12 files in evidence/11c/ keep their 16:15Z mtimes, matching the original assembly.
- No other production path was changed, no human record exists, and no reviewer wrote anything.

R11C-3 is unchanged: it is still Medium, nonblocking and an orphan with no assigned writer, so it needs a separate human decision.

4. Security, secrets, IAM and injection

No new findings. The token is a random UUID stored with the session, and the HTTP canary/redaction test still passes in the fresh XML.

5–8. Hadoop/Spark, entity resolution, storage, RAG

No changes in this batch and no regressions. These keep their earlier dispositions:
- R11C-4 (Low, hadoop-engineer)
- R11C-6 (Low observation, storage-engineer; downstream impact still untraced)
- NB1, NB3 and NB8, which are still present and nonblocking

9. API behavior and failure handling

R11C-7 and R11C-8 above. Phase 10 F2 behavior (terminal failures stored as non-retryable) is unchanged and documented. F7, F8 and F10–F17 are carried.

10. Tests that would pass if the behavior were broken

- The new tests are hand-derived and sensitive; see the R11C-1 and R11C-2 notes above.
- F11B-3, F11B-4 and 11A N3 are carried unchanged.

11. Documentation claims

R11C-5 (Low): CLOSED. README:103-118 accurately describes:
- the winning binder of the revision-0 CAS
- the per-attempt ownership token and the reuse of client IDs
- exact-match reconciliation after a lost reply
- replay recovery of an unbound reservation

README:298-306 keeps the process-death limit and the permanent-outage limit, and makes no claim of a durable dispatcher. The wording precision issue is covered by R11C-8.

R11C-9 (new): Low. Coordinator evidence fidelity. Nonblocking.
- Where: docs/agent-runs/phase-11/review.md (appended initial 11C section).
- Issue: only the opening VERDICT paragraph is verbatim. The full findings and report fields are summarized, with the findings tabulated in repairs.md. Plan §10 requires the verdict verbatim.
- Owner: coordinator.
- Acceptance: when appending this verdict, include the complete returned text. Do not rewrite earlier content.

12. Cost and cleanup

No new findings. No cloud or provider calls were made.

Evidence I verified

- HEAD is 2b0aee0.
- Live status (8 modified, 65 untracked) matches handoff-files.json exactly, and git diff --check exits 0.
- Gate records: all 8 gates' raw logs exist and match their recorded bytes and SHA-256 hashes, including the full check at cd1d970f…. Every start-record hash matches its result record.
- Source freeze: the 25 frozen sources are identical across the start record, the after-run record and the current files.
- Fresh XML: 156 reports and 1,253 tests with 0 failures, errors or skips. No report predates the full-check start.
- Coverage: all 84 mapped cases are present. Category 16 is 2/4/6 and category 17 is 2/5/7, as claimed.
- Full-check log: it contains no FAILED *** lines. The only [error] lines come from the expected checkProbeInjectFailure self-test. The run ends with TestRunMarker and [success] Total time: 722 s.
- ExposedDefect: the count of 0 is consistent.

Unread scope

- The same main-code areas as in the initial review remain unread line by line.
- I only skimmed the coordinator scripts (collect-evidence.py, finish-round.py, run-gate.py).
- The project guard hook blocked one read-only command that named the test-marker path, so I did not inspect the marker file directly. I relied on the TestRunMarker line in the log.

3. Report fields

STATUS: COMPLETE (recheck returned; APPROVE for 11C repair round 1, batch 1)
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Phase 11 Subphase 11C repair round 1 batch 1 recheck; HEAD 2b0aee0 + working diff/untracked; whole-repo baseline 0349388
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only git (rev-parse, status, diff/--stat/--numstat/--check); cat/sed/grep/ls/tail; shasum on /tmp/phase11c-r1-*.log; python3 read-only JSON/XML/hash reconciliation. One read-only command was blocked by the project guard hook (no mutation attempted). No builds/tests, AWS/provider calls, subagents or file edits by the reviewer.
TEST RESULTS: none executed by reviewer. Retained: red-2 exit 1 (4/4 failed pre-repair); format-check exit 0; targeted exit 0 (40+18=58); full sbt -batch check exit 0, 1,253 tests/156 fresh reports, 0 failures/errors/skips
VALIDATION RESULTS: 8/8 raw-log and start-record hashes match; 25 sources frozen and unchanged; inventory 8/65 matches; 84/84 mapped cases present; append-only reports; R11C-1/R11C-2/R11C-5 acceptance met
ASSUMPTIONS: in-memory RowSessions faithfully models conditional CAS; synthetic tests do not establish live DynamoDB behavior
RISKS: R11C-7/R11C-8/R11C-9 Low nonblocking; R11C-3 orphan; R11C-4/R11C-6, F11B-3/F11B-4, N3, NB1–NB10, F7/F8/F10–F17 carried; raw logs only in /tmp; durable dispatch after process death unproven
MANUAL ACTION REQUIRED: user commits 11C and its repair; user decides R11C-3 ownership; user writes the human gate
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none for this batch
NEXT GATE: user commit of 11C, then the user's own Phase 11 human gate/commit records

4. NEXT PROMPT for the coordinator

You are the ScholarChain Phase 11 coordinator in /Users/danny/Documents/UIC/CS441/ScholarChain
(branch phase-11, HEAD 2b0aee0 plus uncommitted 11C and repair-round-1 work).

1. Append this reviewer's complete returned text VERBATIM (verdict, findings, report fields)
   under a new heading "### user-supplied external review — 11C repair round 1, batch 1" in
   docs/agent-runs/phase-11/review.md. Do not rewrite any earlier content.
2. Append to docs/agent-runs/phase-11/repairs.md a disposition table:
   R11C-1 CLOSED; R11C-2 CLOSED; R11C-5 CLOSED (independent recheck APPROVE).
   New nonblocking items, logged only, no repair authorized:
   R11C-7 Low service-engineer (POST returns 404 when retried creation leaves no row;
   expected 503 retryable);
   R11C-8 Low service-engineer (applied-bind lost reply plus failed reconcile read strands
   a bound QUEUED row; bounded retry, stale-QUEUED reclaim or README wording at a
   deployment gate);
   R11C-9 Low coordinator (full verdict text belongs in review.md verbatim; satisfied by
   step 1 going forward).
   Carried unchanged: R11C-3 Medium ORPHAN (needs a separate human writer assignment),
   R11C-4, R11C-6, F11B-3, F11B-4, 11A N3, Phase 9 NB1–NB10, Phase 10 F7/F8/F10–F17,
   earlier Phase 5–8 limits.
3. Ask the user whether Subphase 11C, including repair round 1, has been committed on
   phase-11. If not, wait. Do not commit or push yourself.
4. Tell the user that Phase 11 is ready for their own human-gate and commit records.
   Mention that R11C-3 ownership is still a pending human decision. Do not infer human
   acceptance. Do not write human-gate.md, commit.txt or any approval/ratification record.
5. Do not launch a reviewer, start another repair batch, or start or prepare Phase 12.
   Stop after this recording and handoff.

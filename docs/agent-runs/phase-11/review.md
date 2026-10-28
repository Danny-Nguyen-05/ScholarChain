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

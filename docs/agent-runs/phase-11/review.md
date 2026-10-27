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

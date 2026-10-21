# Limited Phase 5E evaluation — pending external review

This evaluates the unchanged deterministic/fake configuration against the frozen, human-reviewed AI-assisted labels. The user explicitly authorized proceeding while real-provider evidence remains open. It is not overall Phase 5 acceptance or real-provider validation.

| Held-out cohort/entity | Binary labels | Precision | Recall | F1 | Decisive coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Primary overall | 194 | 100.0% | 79.2% | 88.4% | 48.5% |
| Primary Work | 99 | 100.0% | 100.0% | 100.0% | 61.6% |
| Primary Researcher | 95 | 100.0% | 67.4% | 80.5% | 34.7% |
| Without 22 assisted overall | 181 | 100.0% | 86.4% | 92.7% | 48.6% |

Primary held-out matrix: TP 57, FP 0, FN 15, TN 122. Six uncertain labels remain outside the 194 binary denominator; all 200 initial held-out reviews are represented. Development: TP 7, FP 0, FN 4, TN 27, 38 binary + 2 uncertain. All 60 reserves remain untouched and outside initial metrics. Positive prediction means ACCEPTED; unresolved/conflict/rejected/missing/invalid are nonacceptance. Therefore true negatives include correctly withheld conflicts; they are not all explicit rejections. Decisive coverage counts only ACCEPTED/REJECTED.

All 15 held-out misses are Scored Researcher UNRESOLVED: 14 score-gap and 1 insufficient-independent-evidence case. Fifty-five of 57 true-positive accepts are ExactIdentifier; two are Scored Researcher accepts. There are zero observed false-positive accepts in this reviewed sample. This does not guarantee zero false merges generally. representative-errors.json contains all 4 development FN and 10 of 15 held-out FN, with actual evidence refs/features/reasons; no false positives were invented. queued-source-decisions.jsonl retains all 300 source-bound queued decisions.

The supplementary mask excludes exactly 22 self-attested externally assisted Researcher cases: 4 development, 18 held-out. Held-out then has 181 binary + 1 uncertain, TP 51/FP 0/FN 8/TN 122. Development has 34 binary + 2 uncertain. Original labels, queue and split remain unchanged. Excluding 22 does not remove the AI draft assistance from other labels and does not make the subset independent blind gold. External source-check evidence was not retained.

Policy remains er-offline-uncalibrated-v2, features er-features-v2. No matcher, features, policy, configuration, thresholds or source observations changed. Eight hypothetical cutoff points were computed on development only. This sensitivity ignores full production evidence-sufficiency gating, does not select a new threshold and is not calibration. No held-out sensitivity or tuning occurred.

Two fresh disabled full-population passes each emitted 11,412 decisions. All 17 export parts replay logically after only declared invocation metadata normalization; queue predictions are byte-identical. Fake-enabled run emitted identical queue predictions with zero fake calls. No LLM-adjudicated path has observations, so no LLM-path accuracy is claimed. Real-provider attempts 0, spend $0.00; credentials were not accessed by these offline commands.

See evaluation-manifest.json for input/candidate/split/label/prediction/source hashes, actual dirty source binding and toolchain; commands.json for exact argv/environment/timing/exits; replay-proof.json, protected-and-metrics-proof.json and source-delta.json for checks. Large full-population exports remain under target/phase5e; retained manifests, 300 queue predictions and source-bound decisions plus exact commands support regeneration. No giant implementation patch was created. The whole-phase source inventory and git baseline enable comprehensive diff review including untracked files.

Limits: convenience sample and unweighted strata; no blocking recall/global identity recall; common-name and unobserved leakage risk; OpenAlex identities/ORCIDs are provider hypotheses; AI-assisted, self-attested labels; 8 uncertain reviews; no real-provider compatibility, live LLM accuracy or calibration. Entity/path, source-pair and sampling-strata summaries are descriptive. No numerical accuracy acceptance target was invented.

Observed final gate: 441 tests, zero failures/errors/skips, 56 fresh JUnit reports; all 900 frozen files unchanged. Python 84/84; all 12 input integrity validators passed.

The initial targeted build was sandbox-blocked at the sbt lock. Subsequent independent CLI fixtures needed provenance/snapshot alignment, disjoint leakage anchors and order-independent complete-row comparison. All failed runs are retained; assertions and production split logic were not weakened. Final targeted 7 owner + 15 independent tests passed. A coordinator command-ledger snapshot preserves receipts from commands completed during the long full gate; final receipts are merged by name/start time rather than losing later entries.

Next gate: user launches an independent read-only comprehensive review using the chat prompt and returns its full verdict. No reviewer was launched, no commit/push occurred and Phase 6 has not started. Real-provider evidence remains a separate open requirement; no overall 5D/Phase 5 acceptance is inferred.

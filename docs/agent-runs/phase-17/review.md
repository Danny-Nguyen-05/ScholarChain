# Phase 17 independent review (code-reviewer, read-only)

Reviewer: `code-reviewer` (Claude Opus 5.5, effort high), launched by the coordinator, separate from every owner. Tools: Read, Grep, Glob only. The reviewer ran no commands; it could not check the `commit.txt` ranges or full byte identity of the copies with git.

## Round 1: REQUEST-CHANGES (1 blocker, 4 majors, 13 minors, 8 nits)

Blocker:
- B1 (coordinator): the 17D copy `docs/agent-runs/phase-12/agent-report.md` carried the AWS account ID from `phase-12/owner-report.md` into a new file. The reviewer also noted that the same ID is already in about 78 tracked files of the current tree, so a history rewrite alone would not remove it.

Majors:
- M1 (documentation-engineer): `reports/final-report.md` summary row gave the Q12 all-pass result as 15/27 then 23/27; the sources say 4/27 then 23/27.
- M2 (documentation-engineer): `reports/release-manifest.md` listed evidence-log file hashes as Terraform state hashes.
- M3 (documentation-engineer; human for the decision): `docs/demo-script.md` said the repository holds no account ID; `docs/threat-model.md` understated the account ID and e-mail addresses in tracked files.
- M4 (documentation-engineer): the README version record and the final report did not reflect the recorded change of the worker model.

Minors and nits: m1 Session 1 cost parts did not add up; m2 the 63 remaining inventory entries overclaimed; m3 67 failures were not all 5xx; m4 inconsistent replay status of `check_manifests.py`; m5 the 17A replay outputs were not committed (coordinator); m6 a demo command would fail; m7 REC14-16 durations exist in the repository; m8 registry digests can be cited; m9 no Terraform security scanner ran, and a secret-pattern scan did run in Phase 16; m10 the university e-mail also appears in the final report; m11 the 290,343 input figure is a summed counter; m12 an incident duration was miscomputed (incident-responder); m13 a chart hid one series; nits in links, wording and the API error table.

Verified by the reviewer: incident timelines against the decision log and logs; `docs/evaluation.md` against `docs/report/evaluation.md` with the cost scopes kept apart; API routes against the service source and the OpenAPI file; module graph; Hadoop configuration and counters; plan checksums, image IDs, dataset hashes, licenses, Terraform modules, EMR release, service capacity and cost report; Phase 14 figures; agent-report copies (same note, 2 lines longer than the original); ownership (no constitutional file or human record changed); course coverage (every required Phase 17 document and README item present); no text addressed to grading agents; no key or secret pattern.

Coordinator decisions on round 1: B1 redacted copy (see `repairs.md`); m10 kept, because the recorded human decision allows only the university address and the name is written "Danny Nguyen" by the human's instruction; M3's underlying question (the account ID and e-mail addresses already in tracked files and history) goes to the human with the Tuesday history decision.

## Round 2: APPROVE

Every round-1 finding was checked at its new text and found repaired, with no new error or overclaim. Remaining items, none blocking: (1) minor, the model note gave no time of day while Work order 3 on 2026-11-16 still ran Opus; the coordinator added the time to the addendum and the documentation-engineer aligned README and final report; (2) minor, `test-report.md` did not exist yet; it is written after the final full check; (3) nit, the source of the 166,088 cache-write figure; fixed by the documentation-engineer. The reviewer asks the human to confirm the B1 redaction default and to decide on the account ID and e-mail addresses already in tracked files and history (M3).

## Package 17I (work order 2): APPROVE

Round 1: APPROVE. Verified: the 24 files are J05/J07/J08 stats output of the two `runPipeline` tests in `HadoopPrepReviewSpec` (`:37`, `:98`); the cause through `HadoopPrepPipeline.scala:170-172`, `PrepJobs.scala:851-858`, `PrepSupport.scala:1061-1072` and `HadoopIO.scala:27-35`; an existing regression test (`HadoopPrepReviewSpec.scala:159-171`); no `file:` path left in the working tree; no script, test, manifest or ownership-audit entry depends on the deleted files (Phase 12 snapshot JSONs list them as history only); `human-decision-privacy.md` holds no account ID or personal address and matches `human-gate.md`. Findings: minor, `docs/threat-model.md:63,136` still called the decision pending (documentation-engineer); nit, the record's cross-reference to 17F (coordinator); nit, stale local agent worktree branches still hold the files (local only, not on `origin`; no action).

Re-check: APPROVE. Both repairs in place; threat-model.md has no account ID, e-mail address, user name or home path. One wording nit in `human-decision-privacy.md:3`, fixed by the coordinator.

## Package 17E (work order 3): APPROVE

Reviewer: code-reviewer, Claude Opus 5.5, effort high. Verdict: APPROVE. Findings: minor, `docs/threat-model.md:118` would go stale after ratification (documentation-engineer; updated before the full check); two nits, none blocking. Ratified by the human afterwards (`ratification-17e.md`); hook probes in `hook-probes-17e.md`.

## 17G close-out (HADOOP-10 tests, Hadoop documentation, replay notes, phase-15 split)

Reviewer: code-reviewer, Claude Opus 5.5, effort high, read-only (Read, Grep, Glob).

Round 1: REQUEST CHANGES. The hadoop-engineer's `CoauthorPairGenerationSpec.scala` was accepted as written: 37 tests, each expectation traced by hand against `DerivedRecords.scala`, `PrepSupport.scala`, `StableIds.scala`, `DomainValidation.scala` and `Enums.scala`; questionable current behaviour is labelled, not presented as correct; production code unchanged. The phase-15 `commit.txt` and `merged-subjects.md` were consistent (48 hashes). Findings, all text-only for the documentation-engineer unless noted:
- MAJOR, `docs/data-lineage.md:76`: said the Hadoop module never reaches S3 itself; in fact it writes through the Hadoop FileSystem API, which accepts `s3://`, `s3a://` and `s3n://` roots (`modules/hadoop/README.md:74`, `HadoopPrepReviewSpec.scala:200`, `:210`, `:237`, `HadoopPrepSpec.scala:731`).
- MINOR, `data-lineage.md:80`: "every reject adds to `REJECTED`" is false for two J09 paths (`PrepJobs.scala:1066-1078`, `:1145-1165`); an impossible J05/J06 example.
- MINOR, `data-lineage.md:92`: J09 rejects column incomplete (`OversizeRecord`).
- MINOR, `data-lineage.md:86`: a J03 fixture reference belonged to J07/J08/J09.
- MINOR: "five skipped tables" should be five skipped scripts (`evaluation.md:25`, `README.md:159`, `final-report.md:266`).
- MINOR, provenance: per-suite counts at `README.md:74` to be confirmed against the raw clone log (coordinator confirmed them and recorded them in `17g-replay.md`).
- MINOR, sequencing (coordinator): `17g-replay.md` must be committed in the same push.
- NITs: truncated quotes of the `plan.sh` and `smoke-local.sh` result lines; line references at `data-lineage.md:78`, `:102`, the `localize` scope; "14:56" (the sbt log says `Total time: 888 s (14:48)`; corrected everywhere).

Round 2: APPROVE. Every round-1 finding was found repaired at its new text with no new error or overclaim, and no added account ID, e-mail address, home path or grader-addressed text. One optional nit (the J09 fixture label for `HadoopPrepSpec.scala:549`) was applied by the documentation-engineer afterwards. The reviewer's observation that the two uncounted J09 reject paths may be a production defect is outside this work order and is left to the hadoop-engineer and the human.

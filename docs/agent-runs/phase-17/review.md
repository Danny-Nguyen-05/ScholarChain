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

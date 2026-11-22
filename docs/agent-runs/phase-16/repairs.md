# Phase 16 repairs

| Round | Finding | Owner | Repair | Verified by |
|---|---|---|---|---|
| pre-review | `eval16_repro.py --verify` FAIL 2 (answer-quality.json/.md embedded the output-directory path) | experiment-engineer A | record basenames only; path-independence tests | coordinator: `--verify` PASS 23/0 |
| 1 | A1 support cross-check false by construction | A | two real checks (rows = sum(joint); stored = sum(min(joint,5))); test with joint > 5 | reviewer round 2 |
| 1 | A2 self-reported claim rate | A | independent scorer re-check primary; runtime rate labelled not independent | reviewer round 2 |
| 1 | A3 environment labels | A | `environment`, `target_loopback` per run; LOCAL-LOOPBACK-LLM / AWS-ECS-LLM | reviewer round 2 |
| 1 | A4-A13 minors and nits | A | as listed in review.md | reviewer round 2 |
| 1 | B1 AWS load raw not frozen | B | frozen `performance/raw-rb-20261118/` (11 MB, scanned, SHA256SUMS); P35 local raw (83 MB) hash-only with a stated gap (coordinator decision) | reviewer round 2 |
| 1 | B2-B7 minors and nits | B | as listed in review.md | reviewer round 2 |
| 1 | D1-D8 report | documentation-engineer | report re-derived from the repaired results | reviewer round 2 |
| 2 | M1 regeneration overclaim | B, documentation-engineer | reworded | coordinator: grep, `--verify` PASS 24/0 |
| 2 | M2 no scan record for frozen rb raw | B | `raw-rb-20261118-freeze-note.json` | coordinator: manifest check 106 hashes |
| 2 | M3 home path in frozen run records | human | decision at the gate | human-gate.md |
| full check 1 | `tests/infra` `NoRealAccountIdIsAdded` FAIL: 4 lines held the AWS documentation example account ID (allowed only in `AwsTestSupport.scala`), `test_eval16_a.py:642,723`, `test_eval16_b.py:281,282` | B, then A | fixtures use the scanner's synthetic ID; A re-pinned the manifest (43/12/52) | coordinator: `NoRealAccountIdIsAdded` Ran 2 OK; `check_manifests.py` OK 106 hashes; full check 2 |

Coordinator decisions recorded in `target/phase15/session2/evidence/coordinator-notes.log` (git-ignored): A11 (instance A appended instance B's README paragraph at the coordinator's request, no collision); B1 scope (freeze the 11 MB AWS raw, not the 83 MB local raw); A7 cost scope (the CS441-key Console figure covers 2026-11-20 and 2026-11-21 UTC only; earlier-phase Anthropic spend is a separate scope in cost-report.log line 4).

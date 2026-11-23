# Phase 16 human gate: evaluation package

Drafted: 2026-11-21 (America/Chicago), by the coordinator, from the human's chat answer. The agents assembled the evidence; they do not decide.

## Decision

**DECISION: ACCEPTED by the human, 2026-11-21, after the passing full check.**

The coordinator asked two questions in chat:

1. May the five frozen run records (`experiments/results/phase16/q12-raw/*/run-record.json`) keep the local home-folder path in their `ledger_path` field (`/Users/<user>/.scholarchain/llm-ledger/haiku-ledger.jsonl`) when the repository is public? The coordinator explained that the field holds no key, password, account ID or e-mail, and that keeping it keeps the copies byte-identical to the originals (review finding M3).
2. May the coordinator commit and push the Phase 16 work?

The human's answer, verbatim:

> yes keep them, and you are good to commit and push it

## What the decision covers

- M3: the five frozen run records stay byte-identical, home-folder path included; `SHA256SUMS` and the manifest hashes stay as they are.
- Commit and push of the Phase 16 package on branch `phase-15-q12`, split by owner (experiment-engineer instance A, instance B, documentation-engineer, coordinator records). Not a merge to `main`.

## Evidence at the decision

- Independent review: round 2 APPROVE (`review.md`); repairs in `repairs.md`.
- Full check round 2, run id `20261122T032145Z-21920`: `RESULT: PASS gates=7` (`test-report.md`).
- Phase 16 is offline: no AWS step, no model call, spend 0.00 (manifest `16-evaluation.json`).

## Coordinator addendum 2026-11-22 (Phase 17, package 17G): commits made under this decision

Recorded by the coordinator; the human's decision above is unchanged. The commits made on the human's "yes ... commit and push" (listed in `commit.txt`): `0b422215743a11c31482fc4f876e9c43634ccdcf`, `fa908da6b797eca20283197068513b53d70d2134`, `b391bea7c038d3d54d1eeb181a626a8226df1d52`, and the coordinator records commit `a07971d4222e79ac64179be2754cdc55916815cd`; merged to `main` by pull request 13 at `55fb1b379e2408af0bbfa3a3bc9d2e69b613a84d`.

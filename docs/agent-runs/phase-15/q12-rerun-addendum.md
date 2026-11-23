# Phase 15 addendum: Q12 benchmark rerun (2026-11-21) and model note

Written 2026-11-22 by the coordinator (Phase 17 package 17C, `docs/agent-runs/phase-17/prompt.md`). This file adds facts recorded after the Phase 15 human acceptance (`human-gate.md`, 2026-11-20). It changes no earlier record. Times are UTC, with Chicago time (CST) in brackets.

## What ran

All runs were on the local loopback stack (`LocalQueryStackMain`, retrieval mode graph, model `claude-haiku-5-5`) against the P6 S export `run:ba7402d1-959a-4277-8c6e-e92878a38afa`. They ran from commit `827fcd5` with a clean tree. No AWS resource was used.

| Step | Time | Result |
|---|---|---|
| Human decision | 2026-11-21 16:45Z (10:45 AM) | "Yes, start now" (start the rerun) |
| Probe `q12-probe-2` (q06 shortest path) | 17:07Z | ANSWERED, verification VERIFIED 2/2, path Found, hop count 1 (the run-1 failure is fixed) |
| Run `q12-run-2` (33 questions) | 17:08:30Z to 17:11:05Z | `RESULT: COMPLETED asked=33 charged=33` |
| Demo clips | after the run; clip list written 17:38Z | REC14 API query (88.2 s), REC15 evidence explain (75.5 s), REC16 claim verification (109.8 s); kept outside the repository, sha256 listed in the git-ignored clip list |
| Cleanup | 17:43Z | Human reported "done": local key files removed, variables unset, the Anthropic key `scholarchain-q12` revoked |
| Cost of record | Console data as of 23:33Z | Anthropic Console, key `CS441-key` (the same key as `scholarchain-q12`, confirmed by the human): USD 0.08 (2026-11-20 USD 0.04, 2026-11-21 USD 0.04) |

## Scores (scorer with deep export checks)

From [`q12-run-2-scores.md`](../../../experiments/results/phase16/answers/q12-run-2-scores.md) (frozen raw: [`q12-raw/q12-benchmark-q12-run-2/`](../../../experiments/results/phase16/q12-raw/q12-benchmark-q12-run-2/)):

- 27 answer-expected questions: retrieval 23, claims 23, text 23, all three 23 of 27. Run 1 (2026-11-20, before the Q12 fixes) had all three in 4 of 27 ([`q12-run-1-scores.md`](../../../experiments/results/phase16/answers/q12-run-1-scores.md)). The runs used different code, so they are not repeats.
- 6 abstain-expected questions (topic, institution): 6 of 6 correct abstentions.
- Failures (kept as negative results):
  - q08 community: ABSTAINED;
  - q19 and q30 community: refused (HTTP 422 UNSUPPORTED_QUERY);
  - q14 max team size: error (HTTP 504 at about the 5000 ms synthesis deadline).

The Phase 16 analysis of these runs, with intervals and cost scopes, is in [`docs/report/evaluation.md`](../../report/evaluation.md), group 4.

## Ledger after the rerun

Bucket 16b: size 116, used 108, remaining 8. Bucket 17: size 10, used 6, remaining 4. Because the key is revoked, no further live answers are possible without a new human decision.

## Model note (subagent models from 2026-11-16)

On 2026-11-16 the human instructed, in chat: "from now on i want you to trigger subagent as sonnet 5.5 high, for the reviewer use opus 5.5 high". This replaced the 2026-11-14 rule (Opus high for every subagent). The instruction came in the afternoon of 2026-11-16 (Chicago time); the Work order 3 launches recorded earlier that day in `owner-report.md` (infra-engineer and documentation-engineer on Opus 5.5 high) came before it. From the instruction on, in Phases 15, 16 and 17, the coordinator launched every worker (owner) subagent on Claude Sonnet 5.5 with effort high and the code-reviewer on Claude Opus 5.5 with effort high. This includes the 2026-11-19 workers (infra-engineer, documentation-engineer). This record was missing from `owner-report.md`.

## Sources

The coordinator's git-ignored session log (`target/phase15/session2/evidence/coordinator-notes.log`, entries of 2026-11-21 and 2026-11-22T00:55Z), the frozen raw and scores linked above, and the human's chat answers quoted verbatim there.

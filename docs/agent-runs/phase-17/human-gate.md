# Phase 17 human gate: documentation, records and incidents package

Drafted: 2026-11-22 (America/Chicago), by the coordinator, from the human's chat answers. The agents assembled the evidence; they do not decide.

## Decision

**DECISION: ACCEPTED by the human, 2026-11-22, after the passing full check.**

The coordinator asked two questions in chat (options chosen by the human, verbatim):

1. "The Phase 17 full check passed (7 of 7 gates). In the new copy docs/agent-runs/phase-12/agent-report.md I replaced your AWS account ID with <acct>; the original owner-report.md is unchanged. Keep that redaction?" Answer: "Keep <acct> (Recommended)".
2. "May I commit Phase 17 on branch phase-17, as 3 commits split by owner (documentation-engineer files, incident-responder records, coordinator records), and push that branch to GitHub? It would not merge into main." Answer: "Commit and push (Recommended)".

## What the decision covers

- Review B1: `docs/agent-runs/phase-12/agent-report.md` stays a copy of `owner-report.md` with the AWS account ID replaced by `<acct>`; the original record is unchanged.
- Commit and push of the Phase 17 package on branch `phase-17`, split by owner (documentation-engineer, incident-responder, coordinator records). Not a merge to `main`.

## Not covered (still open)

- Review M3: the AWS account ID and e-mail addresses already in tracked files and in git history. Decision with the history question on Tuesday 2026-11-24, before the repository is made public.
- 17E (factory-engineer: `.claude/settings.json` hook paths, `.mcp.json` header): needs ratification and a fresh session.
- 17G clean-checkout replay and grading agents, after the merge to `main`.
- 17H video, its link in README, and making the repository public.

## Evidence at the decision

- Independent review: round 2 APPROVE (`review.md`); repairs in `repairs.md`.
- Full check run id `20261122T174646Z-52571`: `RESULT: PASS gates=7` (`test-report.md`).
- Phase 17 is offline: documentation and records only; no AWS step, no model call.

## Addendum 2026-11-22 (6:35 PM CST): work order 2 and the privacy decision

- Review M3 is decided: see `human-decision-privacy.md` (keep; no history rewrite).
- Package 17I (`work-order-2-stray-files.md`): review APPROVE, full check `20261122T230732Z-61812` `RESULT: PASS gates=7` (`test-report.md`). The coordinator asked: "May I commit these changes in 3 commits and push phase-17?" The human answered: "Commit and push". Covers the hadoop-engineer deletion commit, the documentation-engineer threat-model commit and the coordinator records commit on `phase-17`, and the push of that branch. Not a merge to `main`.

## Addendum 2026-11-22 (9:47 PM CST): package 17E commit

- Package 17E (`work-order-3-hooks-mcp.md`): review APPROVE (`review.md`), human ratification (`ratification-17e.md`), fresh-session hook probes (`hook-probes-17e.md`), full check `20261123T005912Z-79868` `RESULT: PASS gates=7` (`test-report.md`), then the documentation-engineer's text-only update of `docs/threat-model.md:118`. The coordinator asked: "Commit 17E split by owner (factory-engineer, documentation-engineer, coordinator records) and push phase-17? Yes, or not yet?" The human answered: "Commit and push". Covers the factory-engineer commit, the documentation-engineer commit and the coordinator records commit on `phase-17`, and the push of that branch. Not a merge to `main`.

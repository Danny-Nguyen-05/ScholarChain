# Phase 15 repairs

## Subphase 15A — P0 repair round 1 (from review 1, REQUEST-CHANGES)

Source: the user-supplied external review in `review.md` (Subphase 15A — P0 budget guard (offline), review 1). Severity, owner and acceptance checks are kept as the reviewer gave them.

| ID | Severity / blocking | Owner | Path named by the reviewer | Acceptance check (reviewer) | Repair status |
|---|---|---|---|---|---|
| F1 | Medium / yes | coordinator (assembling the infra-engineer, test-engineer and documentation-engineer reports) | `docs/agent-runs/phase-15/owner-report.md:1-20` | A table of native ID, role, model and effort, assigned paths and handoffs for all three agents, plus each agent's 14-field report (or a consolidated one quoting them). Nothing invented; an unrecorded ID is stated as not recorded. | fixed: table with all three IDs (taken from the session's Agent tool results; none missing), each agent's final report verbatim, and a consolidated 14-field report |
| F2 | Low / no, fix before the commit | documentation-engineer | `docs/runbooks/phase-14-live-session.md:264` | The link to `session-2-plan.md` becomes a code-span path (or the draft is committed); a link check on a worktree of `a576878` plus the P0 patch only shows 0 broken. | fixed by documentation-engineer `ab222e483909f6714`; clean-worktree check: 62 links, 0 broken |
| N1 | Low / no | coordinator | `docs/agent-runs/phase-15/test-report.md:7-10` | Keep the logs with hashes, or label each line "agent-reported; log not retained". | fixed: labelled; the infra-engineer's failed `check.sh --only terraform` run (exit 4) is now recorded too |
| N2 | Info / no | coordinator | plan §6.11 | Optional: commit short excerpts under `docs/agent-runs/phase-15/evidence/15a/`. | not done (optional); `test-report.md` carries the totals and log hashes. Can be added at the user's request before the commit. |
| N3 | Info / no | coordinator | `docs/agent-runs/phase-15/prompt.md:33` | "(answers pending)" becomes "(answered 2026-11-15, below)". | fixed |
| N4 | Info / no, existing before P0 | — | `scripts/billing/budget_execution.py:611-614` | In the 2026-11-17 checklist, record `notifications_visible` from the plan inspection in the receipt. | carried to the 2026-11-17 live-modify checklist (prepared after approval) |

### Coordinator observation from the repair verification

| ID | Severity / blocking | Owner | Path | Evidence | Status |
|---|---|---|---|---|---|
| O1 | Low / no, existing before P0 | infra-engineer (`scripts/**`) | `scripts/billing/README.md:38` | The link `[reviewed Terraform input](/Users/…/infra/terraform/billing-bootstrap/main.tf:28)` is an absolute local path with a line suffix, so it is broken in any checkout and shows a local home path. It is identical at `a576878` and is not in the P0 diff. | not fixed (outside the P0 findings); proposed for a later infra-engineer order: a relative link `../../infra/terraform/billing-bootstrap/main.tf` |

### Status after review 2 (recheck, APPROVE, 2026-11-15)

| ID | Status |
|---|---|
| F1, F2, N1, N3 | closed (review 2) |
| N2 | open, optional |
| N4 | deferred to the 2026-11-17 live-modify checklist |
| N5 (review 2, Info) | fixed: the review 1 heading in `review.md` now says "sections 1–3 verbatim as pasted … section 4 followed, see repairs.md" |
| O1 | future scope: infra-engineer, `scripts/billing/README.md:38` to the relative link `../../infra/terraform/billing-bootstrap/main.tf` |

### Repair evidence (round 1)

- Agent report: `owner-report.md`, "Work order 1: P0 repair round 1". Coordinator runs: `test-report.md`, "Work order 1: P0 repair round 1".
- New P0 patch sha256 `ede0052faf4f066eea436b67c5e75b76bff22807fa2ee27040d806123055d6fb`; with line 264 reverted it reproduces the round-0 hash `def2c281…76d4f`, so the round-1 tracked change is that line only.
- `sbt check` not rerun (no Scala, build or test input changed); the P0 evidence stands (log sha256 `6c2f5e7e…f4960`).
- No AWS, Anthropic or Voyage call; nothing committed; no reviewer launched.

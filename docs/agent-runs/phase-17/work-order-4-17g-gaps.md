# Phase 17 work order 4: record gaps found by the 17G grading-agent run

Assembled by the coordinator on 2026-11-22 (Sun, about 11:00 PM CST), on branch `phase-17` at `d95645c` (merged to `main` at `6cf5aa8`).

## Human decision

- After the coordinator explained the four gaps, the human answered: "yes pleased fix them, for the gap 4, you can kill the current check then fix gap 4 and run everything again to svae time". The coordinator stopped the running README replay; it is rerun from the start after these fixes.

## Findings (advisory self-check on a fresh clone of `main` at `6cf5aa8`, V1 1.0.3 and V3 3.0.0)

- V1 E01 FAIL: the Phase 3, 4 and 16 agent reports use combined labels ("COMMANDS RUN / TEST RESULTS", "COMMANDS RUN (observed ...)") that the checker does not read as the standard fields.
- V1 E06 FAIL: the Phase 12 human gate accepts the 12A commit `a83f62e`, while `commit.txt` names only the 12D closeout commit `fcbf761`; the Phase 16 human gate names no commit (WARN).
- V3 FACTORY-07 partial cited these record gaps; V3 FACTORY-01 partial: the rule that subagents never invoke one another is in the agent files and README but not in `CLAUDE.md` or `docs/agents.md`.
- Not changed, because a change would misquote or rewrite history: V1 G02 (an incident ID containing a date inside a quoted commit subject in `phase-15/commit.txt`), G03 and E03 (early phases committed without phase-named messages), E02 (free-text OWNER lines in copied reports).

## Work

| Gap | Work | Owner | Writes | Gate |
|---|---|---|---|---|
| 1 | Labeled index note (COMMANDS RUN, TEST RESULTS, VALIDATION RESULTS) appended to the Phase 3, 4 and 16 agent reports, pointing to the existing entries and `test-report.md`; marked as a Phase 17 addition, not part of the copied report | coordinator | `phase-03/agent-report.md`, `phase-04/agent-report.md`, `phase-16/agent-report.md` | V1 rerun |
| 2 | `phase-12/commit.txt` lists, in full, the package commits that `human-gate.md` accepts | coordinator | `phase-12/commit.txt` | V1 rerun |
| 3 | Coordinator addendum to `phase-16/human-gate.md` naming the commits made under the human's decision (the decision text is unchanged); the records commit and merge added to `phase-16/commit.txt` | coordinator | `phase-16/human-gate.md`, `phase-16/commit.txt` | V1 rerun |
| 4 | One sentence in `docs/agents.md:61`: subagents never invoke one another; only the orchestrator launches subagents | factory-engineer | `docs/agents.md` | review, **human ratification**, fresh-session probe |

V1 rerun on the working tree after gaps 1-3 (coordinator, 2026-11-22): E01 PASS, E06 PASS; 35 pass, 7 fail, 7 warn (S01 fails only in the working tree, because of local untracked links; it passed on the fresh clone).

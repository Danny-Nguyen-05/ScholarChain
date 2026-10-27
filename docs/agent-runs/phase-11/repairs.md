# Phase 11 routed defects and repairs

## Subphase 11A

STATUS: COMPLETE (11A defect accounting; external review pending)
OWNER: coordinator; future repairs routed by docs/agents.md.
WORK ORDER: Retain every exposed production defect without production edits during 11A.
FILES CREATED: evidence/11a/defects.json and this routing record.
FILES MODIFIED: No production files.
COMMANDS RUN: See evidence/11a/commands.json for exact targeted/full gates.
TEST RESULTS: Targeted 19/19; final full 1,231/1,231, zero failures/errors/skips.
VALIDATION RESULTS: Zero production defects exposed by these runs; ExposedDefect count: 0. No tag or build exclusion was necessary. A Scala indentation error in a new test was corrected by its test-engineer before successful targeted/full execution; it is not a production defect.
ASSUMPTIONS: Passing bounded tests do not prove the repository has no defects.
RISKS: Earlier-phase findings retain original owners/status; no closure or repair is inferred from 11A. Full review/production repairs belong to 11C.
MANUAL ACTION REQUIRED: User launches the 11A reviewer and returns its verdict.
BLOCKED-ON OWNER: None for current accounting; future findings route to named owners.
BLOCKED-ON EVIDENCE: External review pending.
NEXT GATE: Read-only 11A review; stop before 11B.

### Subphase 11A external review — nonblocking, no repair authorized

The user supplied APPROVE for 11A with no blocking findings. The verbatim verdict is appended in review.md. Earlier pending-review statements above are historical. No repairs were made in this recording step.

| ID | Owner | Disposition |
| --- | --- | --- |
| N1 | Coordinator | Logged; no 11A repair authorized. In 11B, report formatter rewrites explicitly or use scalafmtCheck for coordinator gates. |
| N2 | Coordinator | Logged; no 11A repair authorized. In 11B, confirm specialist writing has stopped before any gate and write each start record once immediately before launch, without rewriting it. |
| N3 | test-engineer | Logged; optional assertion/report-strengthening work, no repair authorized. |
| N4 | hadoop-engineer if confirmed; test-engineer for any resulting assertion update | Logged as an unverified 11C investigation lead concerning markup-sensitive title blocking; no investigation or repair now. |
| N5 | Coordinator | Disclosed limits accepted by the reviewer; retain the reading, model-revision, temporary-log and synthetic-fixture limitations. |

Next gate: user commits approved 11A on phase-11, then 11B Step 0. The coordinator will not commit, push, write human-owned records or begin 11B before the required commit gate.

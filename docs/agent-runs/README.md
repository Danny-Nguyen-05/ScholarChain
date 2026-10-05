# Phase evidence format

For every phase create `docs/agent-runs/phase-NN/` with `prompt.md` containing the exact work order, `owner-report.md` containing the owning agent's final report, `review.md` and `test-report.md` when required, `repairs.md` for routed findings, `human-gate.md` for the human's decision, and `accepted-commit.md` for the accepted commit SHA. Put exact commands and observed output in `owner-report.md` and, when applicable, `test-report.md`; include failed runs, manual interventions, and their provenance there. A separate `validation.md` is not required. The orchestrator assembles agent outputs; the human owns and writes the gate decision. No agent may change a prior human decision.

Report fields:

```text
STATUS: COMPLETE | BLOCKED-ON | FAILED
OWNER:
WORK ORDER:
FILES CREATED:
FILES MODIFIED:
COMMANDS RUN:
TEST RESULTS:
VALIDATION RESULTS:
ASSUMPTIONS:
RISKS:
MANUAL ACTION REQUIRED:
BLOCKED-ON OWNER:
BLOCKED-ON EVIDENCE:
NEXT GATE:
```

Store source diffs, command output, test and review findings, approvals and commit IDs. Store no hidden model reasoning, secrets, downloaded full datasets, or invented measurements. Unrun commands are listed as unverified, not successful. Record toolchain and model versions needed for replay, and distinguish each approved cloud action from a proposed one.

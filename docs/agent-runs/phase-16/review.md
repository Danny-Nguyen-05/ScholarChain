# Phase 16 independent review (code-reviewer, read-only)

Reviewer: `code-reviewer` (Claude Opus, effort high), launched by the coordinator, separate from every owner. Tools: Read, Grep, Glob only; the reviewer ran no commands and states that the test, manifest and regeneration results it cites are the coordinator's observations, not its own.

## Round 1: REQUEST-CHANGES (0 blockers, 6 majors)

Majors:
- A1 (instance A): the graph support cross-check "(edge, support work) pairs capped at 5 per edge: 267597 (equal: NO)" against 269753 support rows was false by construction (stored = sum of min(joint,5)); the real checks both pass.
- A2 (instance A): the 36/36 and 65/65 "claim support rate" came from the runtime's own `/v1/explain` verifier; the independent scorer re-check must be the primary figure.
- A3 (instance A): answer-quality gave no local/AWS label; the 16B run is AWS (loopback false), the Q12 runs are local loopback.
- B1 (instance B): the raw of the only AWS load run was not frozen in the repository.
- D1, D2, D3 (documentation-engineer): the report repeated A1 and A2, and called USD 0.08 the model cost "in total" although it covers one key on Nov 20-21 only.

Minors and nits: A4-A13 (wording of the run-1 name failures, accuracy counting withheld pairs, hard-coded interpretation sentences, cost scope and hard-coded rates, freeze timestamp, Spark test inventory and the full check's tree, manifest completeness, README wording, home path in frozen run records, bootstrap index asymmetry), B2-B7 (variability wording, a broken sentence, k=0 aggregation and the q03 tie, PARTIAL exit code, factory parser granularity, bootstrap question mix), D4-D8.

Verified by the reviewer: Wilson formula and hand values, F1 and accuracy arithmetic, run-1 and run-2 totals, token cost and Console ratio, AWS hold-50 arithmetic, retrieval sums, percentile method, metric definitions and tests, frozen-copy hash listings against the originals, privacy scan of the package, path independence, manifest count, ownership.

## Round 2: APPROVE

All round-1 blockers and majors fixed with no new major defect. Confirmed: two passing support checks (269753 = 269753; 267597 = 267597); independent claim re-check primary and the runtime rate labelled "not independent"; environment labels match the frozen run records; cost scopes kept apart and checked line by line against `docs/agent-runs/phase-15/evidence/session-2/c11/cost-report.log`; rb raw frozen with hash verification; manifest completeness rule; PASS/PARTIAL/FAIL exit codes 0/4/1; phase 03 hand audit spot-checked. The [small graph] count is 9 (instance A's report said 11; the files are right).

Open minors after round 2, all repaired before the full check (wording only, no re-review required by the reviewer):
- M1: "AWS rows regenerate from the repository" overclaimed (the performance script still needs git-ignored P35 and P6 inputs): reworded by instance B and the documentation-engineer.
- M2: no scan record for the frozen rb raw: instance B added `raw-rb-20261118-freeze-note.json` (11 patterns, 0 matches).
- M3: keeping the local home path in the five frozen run records is a human decision: put to the human at the gate.
- Nit: stray lower-case sentence in `factory-metrics.md`: fixed.

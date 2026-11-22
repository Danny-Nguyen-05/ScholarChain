# Phase 17 work order: final documentation, records, incidents and submission readiness

Assembled by the coordinator (Claude Code orchestrator) on 2026-11-22 (Sun Nov 22, about 10:15 AM CST), on branch `phase-17` from `main` at `55fb1b3` (full check `20261122T055838Z-17867`: `RESULT: PASS gates=7`).

## Human decisions

- 2026-11-22, the coordinator asked: "Should I start step 1, the `phase-17` branch and its work order?" The human answered: "Yes please".
- Standing decisions that still apply: commits only on the human's explicit yes; no AWS, no live model call and no spend unless the human approves it (the Q12 Anthropic key is revoked); negative results stay in the submission.
- Rubric priority (human, 2026-11-16, quoted in `docs/agent-runs/phase-15/prompt.md`): Phase 17 must include README commands replayed on a clean checkout, agent replay instructions, and all agent definitions submitted. Low-value polish gets the default without a question.
- Submission (human, recorded 2026-11-19): repository public and clonable without authentication at the deadline, Wed 2026-11-25 11:00 PM CST; the last commit on `main` before the deadline is graded; no text that instructs or manipulates the grading agents.

- 2026-11-22, the coordinator asked whether to start the offline Phase 17 work; the human answered: "Yes please do".
- 2026-11-22, README e-mail. Question: "The course says the README must show your name and university email. Your Gmail must stay out of the repo. Which address should go in the README?" Answer (option chosen): "cnguye69@uic.edu". Only this university address may appear; the personal address stays out.
- 2026-11-22, orphan path. Question: "Assign reports/** to the documentation-engineer?" Answer (option chosen): "Yes, documentation-engineer (Recommended)". `reports/final-report.md` and `reports/release-manifest.md` are the documentation-engineer's.

- 2026-11-22, the human, in chat: "For the name make sure you use Danny Nguyen". The student name is written "Danny Nguyen" everywhere.
- 2026-11-22, review B1 (coordinator decision, default): `phase-12/agent-report.md` is a copy of `owner-report.md` with the AWS account ID replaced by `<acct>`; the other 15 copies stay byte-identical. The account ID and e-mail addresses already in tracked files and history are the human's decision on Tuesday.

## Course requirement (source and its limit)

Read on 2026-11-22: the course README (`https://raw.githubusercontent.com/0x1DOCD00D/ScholarChain/main/README.md`, section "Phase 17: produce documentation, final review, and release"). Beyond the files below it requires: README with student name, university e-mail, summary, architecture, prerequisites, exact build, test and Terraform plan commands, deployment path, bounded data-run path, query examples, cleanup path, known limitations; an API specification or route reference; a complete deliverable index; replaying commands before documenting them; a final read-only review (code-reviewer) and final test run (test-engineer); and a release manifest (commit SHA, image digests, Terraform plan checksum, dataset snapshots, run IDs, prompt versions, model versions, test counts, artifact checksums). Its final gate: `sbt clean check` from a clean checkout, Terraform validates and the archived plan matches the documented final state, README commands replayed, bounded pipeline rerunnable, query and evidence examples work, final reviewer APPROVE, cleanup rehearsed safely, release manifest complete.

Earlier source:

The Phase 17 file list comes from the course grading agent's self-check (`target/autograder/final-20261120/selfcheck-cnguye69.csv`, check W01, run 2026-11-20 on Phase 15), which quotes the course README: "Phase 17 work order: README.md, docs/architecture.md, docs/data-lineage.md, docs/threat-model.md, docs/service-limits.md, docs/runbook.md, docs/evaluation.md, reports/final-report.md, docs/demo-script.md". W01 then reported all but README and the demo script as missing; W02 (README subsection "Reproducing the agentic workflow") would pass. The course README was not re-read for this order; the documentation-engineer reads it before writing.

## Work packages

| ID | Work | Owner | Writes | Gate |
|---|---|---|---|---|
| 17A-1 | `docs/architecture.md` (build-time and runtime diagrams), `docs/data-lineage.md`, `docs/threat-model.md`, `docs/service-limits.md`, `docs/runbook.md`, `docs/api.md` (route reference) | documentation-engineer (instance 1) | the listed paths | link check, number check against sources, review |
| 17A-2 | `docs/evaluation.md` (from `docs/report/evaluation.md`), `reports/final-report.md` (including the scale table and the fixture-versus-real section, P28), `reports/release-manifest.md`, README updates (name and university e-mail, the course's required sections, deliverable index), `docs/demo-script.md` updates | documentation-engineer (instance 2) | the listed paths | link check, number check against sources, review |
| 17B | Incident records for the known Session 2 failures: EMR spark-job step (`EmrFileSystem` ClassNotFound on `copyToLocal`), ingest 1 rejected with HTTP 401 (invalid Voyage key), runtime-archive upload `RequestTimeout`, load-test abort and 5xx burst, deployer session drops, console permission gaps, kit missing the a7/b3b/c5 policies | incident-responder | `docs/incidents/**` | evidence links resolve, review |
| 17C | Phase 15 records addendum for the Q12 rerun of 2026-11-21 (probe 2, run 2: 23/27 answer-expected all-pass, 6/6 abstentions; clips REC14-16; key revoked; Console USD 0.08) and the 2026-11-19 model note (workers sonnet/high, reviewer opus/high) | coordinator | new files under `docs/agent-runs/phase-15/` (existing human records are not rewritten) | review |
| 17D | Grading-agent format items that are records only: P01 (each phase folder needs a file the grader accepts as an agent report; `commit.txt` missing for phases 05, 08-11 and 15): add index files that point to the existing reports and list the phase's commits from `git log`. No existing record is edited | coordinator | new files under `docs/agent-runs/phase-NN/` | grader re-run |
| 17E | Constitutional format items: F05 (the grader cannot resolve the hook command paths in `.claude/settings.json`), F07 (`.mcp.json` `github-readonly` Authorization header read as a literal value) | factory-engineer | `.claude/settings.json`, `.mcp.json` | **human ratification and a fresh session** before it applies; hook probes |
| 17F | Disclosures for items that cannot be fixed without rewriting git history: G03 (older commit messages do not name a phase), K01/K02 (synthetic secret-shaped test fixtures in files and history). History rewrite is a separate human decision (Tuesday), together with the e-mail and account ID in old commits | documentation-engineer (text), human (decision) | README section | review |
| 17G | Clean-checkout replay: fresh clone of `main`, README commands, bounded local run, grading agents | coordinator (runs), human (gate) | results under `docs/agent-runs/phase-17/` | observed output only |
| 17H | Video editing and voice-over | human | outside the repository | human |

Order: 17C and 17D (records, today), 17B and 17A in parallel (disjoint paths), 17F with 17A, 17E only after the human's ratification decision, then review, one full `scripts/check.sh` (JDK 17), the human gate and commits; 17G after the merge to `main` on Tuesday.

## Ownership notes (coordinator reading of `docs/agents.md`)

- `reports/final-report.md` is a new top-level path. The map gives the "final report" to the documentation-engineer, so this order assigns `reports/**` to the documentation-engineer only; no other owner claims it.
- `docs/evaluation.md` is new; `docs/report/evaluation.md` stays as the Phase 16 record.
- `docs/agent-runs/**` index files are phase evidence assembled by the coordinator; human decisions and ratification records stay untouched.

# Phase 17 human ratification: work order 4, gap 4 (`docs/agents.md` line 61)

Recorded 2026-11-22 (Sun, 11:13 PM CST) by the coordinator from the human's chat answer. The agents drafted and reviewed the change; only the human ratifies.

## What was ratified

Uncommitted change on `phase-17` at `d95645c` (work order `work-order-4-17g-gaps.md`): `docs/agents.md:61` (factory-engineer), in "Escalation and gates", gains the sentence: "Subagents never invoke one another; only the orchestrator launches subagents, and a subagent returns any dependency or ownership question to the orchestrator as `BLOCKED-ON` with an exact path and required owner." No other line or file of the constitution changed.

## Evidence at the decision

- Factory-engineer: `git diff --stat` 1 line in `docs/agents.md`; `validate-agent-files.sh`: "Validated 18 unique agents, reviewer fence, 32 representative ownership paths and 18 routes", exit 0.
- Independent review (code-reviewer, Claude Opus 5.5, effort high): APPROVE, no blocker, major or minor; nit 1 ("launches agents" to "launches subagents", because the human starts orchestrator sessions) applied by the factory-engineer; nits 2 and 3 not applied; coverage note: the role line "Never invoke another subagent" is in 17 of the 18 agent files (not in `factory-engineer.md`, whose tool fence has no agent tool).
- Coordinator: `git diff --numstat` shows `docs/agents.md` 1 insertion, 1 deletion; the other changed files are the coordinator's gap 1-3 records.

## Question and answer (verbatim)

The coordinator asked: "The reviewer approved the gap-4 change (with the "subagents" wording fix applied). Do you ratify it? The change adds one sentence to docs/agents.md line 61, in "Escalation and gates": "Subagents never invoke one another; only the orchestrator launches subagents, and a subagent returns any dependency or ownership question to the orchestrator as `BLOCKED-ON` with an exact path and required owner." It states a rule already in the agent files and README; no tool, ownership or authority changes. After a yes, a fresh Claude Code session runs a quick hook probe before anything is committed."

The human answered (option chosen): "Ratify (Recommended)".

## Still required before commit

1. A fresh Claude Code session runs the hook probes and saves the prompts and results under `docs/agent-runs/phase-17/`.
2. A commit only on the human's explicit yes.

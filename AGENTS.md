# ScholarChain shared agent instructions

Codex and Cursor use this file as shared project guidance. Claude Code imports it from `CLAUDE.md`. The course specification remains authoritative; see `docs/agents.md` for the proposed one-writer map.

## Authority

- Phase 1 control files are proposals until the human architect reviews the complete diff, records ratification, and starts a fresh session. Do not claim Phase 0 or Phase 1 has been ratified from file existence alone. The ignored `.claude/.last-test-run` is generated test evidence, not a constitutional file.
- Use a fresh orchestrator session for each phase. Route work to the named owner; subagents do not invoke one another. No agent approves its own work.
- Codex and Cursor are the student's primary tools. The course README describes a Claude Code orchestrator and requires all `.claude/` artifacts. Do not claim cross-tool equivalence or instructor approval of a deviation.
- A reviewer reports findings without editing. Human decisions under `docs/agent-runs/**` are never rewritten by an implementation agent.

## Engineering floor

- One writer owns each artifact class. Return out-of-scope work as `BLOCKED-ON` with evidence and the required owner.
- Run the relevant deterministic gate and report only observed output. Every behavior change needs feature tests. `sbt check` is the repository definition of done once Phase 2 creates the build.
- Keep dataset and runtime claim provenance. An LLM cannot invent researcher identity, path, score, or source evidence.
- Secrets belong in AWS Secrets Manager or approved local placeholders, never tracked files. Never read or print `.env`, private keys, generated credentials, or secret directories.
- All AWS infrastructure is authored in Terraform. Live apply, deployment, costly scale changes, data destruction, security changes, and rollback require the human gate recorded in the phase evidence. No direct console mutation as an implementation path.
- `.claude/settings.json` and hooks protect Claude Code sessions. They are not enforcement for Codex or Cursor; use their native sandbox and approvals plus the same review gates.

## Reports

Use the fields in `docs/agent-runs/README.md`. Keep exact commands, results, limitations, owner, and next gate. Do not store hidden model reasoning.

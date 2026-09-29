# ScholarChain shared agent instructions

This root `AGENTS.md` is the shared instruction file for the active Codex and Cursor workflow. Cursor may also load `CLAUDE.md`; that file imports this one and scopes its Claude-specific instructions explicitly. The course specification remains authoritative; see `docs/agents.md` for the proposed one-writer map.

## Authority

- Phase 1 control files are proposals until the human architect reviews the complete diff, records ratification, and starts a fresh session. Do not claim Phase 0 or Phase 1 has been ratified from file existence alone. The ignored `.claude/.last-test-run` is generated test evidence, not a constitutional file.
- Use a fresh Codex or Cursor task/session for each phase. Route work by the named ownership map and keep implementation and review separate. No agent approves its own work.
- Codex and Cursor are the student's active tools; Claude Code is not part of the planned workflow. The course README describes a Claude Code orchestrator and requires all `.claude/` artifacts. Those role definitions are assignment/Claude artifacts, not automatically registered subagents or tool fences in Codex or Cursor. Do not claim cross-tool equivalence or instructor approval of this deviation.
- A reviewer reports findings without editing. Human decisions under `docs/agent-runs/**` are never rewritten by an implementation agent.

## Engineering floor

- One writer owns each artifact class. Return out-of-scope work as `BLOCKED-ON` with evidence and the required owner.
- Run the relevant deterministic gate and report only observed output. Every behavior change needs feature tests. `sbt check` is the repository definition of done once Phase 2 creates the build.
- Keep dataset and runtime claim provenance. An LLM cannot invent researcher identity, path, score, or source evidence.
- Secrets belong in AWS Secrets Manager or approved local placeholders, never tracked files. Never read or print `.env`, private keys, generated credentials, or secret directories.
- All AWS infrastructure is authored in Terraform. Live apply, deployment, costly scale changes, data destruction, security changes, and rollback require the human gate recorded in the phase evidence. No direct console mutation as an implementation path.
- `.claude/settings.json`, hooks, commands and `.claude/agents/*.md` apply to Claude Code only. They are not active enforcement or registered roles in Codex or Cursor. Use each active tool's native sandbox and approvals plus the same one-writer and human review gates.

## Reports

Use the fields in `docs/agent-runs/README.md`. Keep exact commands, results, limitations, owner, and next gate. Do not store hidden model reasoning.

# Phase 17 package 17G: post-ratification hook probes

Run by the fresh Claude Code probe session, as the main orchestrator. Change under test (uncommitted on `phase-17` at `d95645c`, ratified in `ratification-17g.md`): one sentence added to `docs/agents.md:61` ("Subagents never invoke one another; only the orchestrator launches subagents, ...").

- Session start: `TZ=America/Chicago date` returned `Sun Nov 22 23:27:43 CST 2026` (first probe command).
- Model: Claude Sonnet 5.5 (`claude-sonnet-5-5`), main orchestrator.
- Scope: safe probes only. No AWS, no network, no secret reads, no commit, no subagents launched.
- Step 0, instruction check: the new sentence is present in this session's loaded project instructions (the `docs/agents.md` block, "Escalation and gates" paragraph, line 61): "Subagents never invoke one another; only the orchestrator launches subagents, and a subagent returns any dependency or ownership question to the orchestrator as `BLOCKED-ON` with an exact path and required owner." The loaded `gitStatus` also lists `docs/agents.md` as modified, consistent with the uncommitted change. `grep -n "Subagents never invoke" docs/agents.md` matches line 61.

## Summary

| # | Probe | Decision | Verdict |
|---|---|---|---|
| 1 | `bash .claude/hooks/validate-agent-files.sh` | allowed, exit 0 | PASS |
| 2 | Bash `echo 'terraform destroy'` | blocked by PreToolUse guard | PASS |
| 3 | Read `probe-17g-tmp/.env` (nonexistent, safe form) | rejected by a permission deny rule | PASS |
| 4 | Edit `AGENTS.md` heading `shared` -> `common` (orchestrator) | blocked by PreToolUse guard; `git diff --stat AGENTS.md` empty | PASS |
| 5 | PostToolUse feedback on the Write of this file | none observed | no verdict (see below) |

Hooks load and fire in this fresh session after the `docs/agents.md` change: the PreToolUse guard ran twice with its own verbatim message (probes 2 and 4), and the permission deny rule rejected probe 3.

## Probe 1: validate-agent-files.sh

- Tool call: Bash `bash .claude/hooks/validate-agent-files.sh; echo "exit=$?"` from the repo root.
- Decision: allowed.
- Output verbatim: `Validated 18 unique agents, reviewer fence, 32 representative ownership paths and 18 routes` then `exit=0`.
- Verdict: PASS.

## Probe 2: terraform destroy

- Tool call: Bash `echo 'terraform destroy'`.
- Decision: blocked before Bash ran.
- Message verbatim: `PreToolUse:Bash hook error: [command hook]: Blocked: terraform apply or destroy. Route this action through the owning agent and recorded human gate.`
- Verdict: PASS.

## Probe 3: Read of a `.env` path (safe form)

- Tool call: Read `/Users/danny/Documents/UIC/CS441/ScholarChain/probe-17g-tmp/.env`. The directory does not exist. No real `.env` or secret file was read.
- Decision: rejected before the read.
- Message verbatim: `<tool_use_error>File is in a directory that is denied by your permission settings.</tool_use_error>`
- Verdict: PASS. The rejection came from the permission deny rule, not from a hook message.

## Probe 4: orchestrator edit of AGENTS.md

- Tool call: Edit `AGENTS.md`, `old_string` `# ScholarChain shared agent instructions`, `new_string` `# ScholarChain common agent instructions`.
- Decision: blocked.
- Message verbatim: `PreToolUse:Edit hook error: [command hook]: Blocked: constitutional file edit by main orchestrator; use factory-engineer after human approval. Route this action through the owning agent and recorded human gate.`
- Follow-up: `git diff --stat AGENTS.md` printed nothing (empty), exit 0.
- Verdict: PASS.

## Probe 5: PostToolUse on Write

- Tool call: Write of this file. PostToolUse feedback: none (the tool result was only "File created successfully"). `validate-agent-files.sh` is the PostToolUse hook for constitutional files and this file is not one, so no output is expected; absence of feedback does not prove the PostToolUse hooks loaded.

## Final `git status --porcelain`

Captured before this file was written (the only change this session makes is this new file, which will appear as `?? docs/agent-runs/phase-17/hook-probes-17g.md`):

```
 M docs/agent-runs/phase-03/agent-report.md
 M docs/agent-runs/phase-04/agent-report.md
 M docs/agent-runs/phase-12/commit.txt
 M docs/agent-runs/phase-16/agent-report.md
 M docs/agent-runs/phase-16/commit.txt
 M docs/agent-runs/phase-16/human-gate.md
 M docs/agents.md
?? docs/agent-runs/phase-17/ratification-17g.md
?? docs/agent-runs/phase-17/work-order-4-17g-gaps.md
```

All entries were already present at session start.

## Limits

- `/hooks` and `/mcp` listings: only the human can open them; not observed.
- The Stop hook (`verify-tests-ran.sh`) fires at the end of this turn and cannot be observed from inside it. This session changed no source under its watched paths.
- `format-scala.sh` was not exercised; no Scala file was edited.
- No subagent probe was run (not in scope); the subagent-side guard decision on a constitutional path was not observed here.
- The new sentence concerns orchestrator/subagent routing policy; no hook enforces it, so these probes show only that the control plane still loads and the guards still fire, not that the sentence is enforced.
- MCP: `aws-api-readonly` (ENOENT `uvx`), `terraform-registry` (CONNECTION_CLOSED) and `github-readonly` (400, Authorization header badly formatted; `GITHUB_MCP_AUTHORIZATION` is not set in this session) failed to connect; unrelated to 17G.

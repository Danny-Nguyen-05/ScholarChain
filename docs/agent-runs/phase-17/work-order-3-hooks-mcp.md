# Phase 17 work order 3: hook command paths and the MCP header (package 17E)

Assembled by the coordinator on 2026-11-22 (Sun, about 6:50 PM CST), on branch `phase-17` at `10f9bd4`.

## Human decision

- The coordinator asked: "Start the hook fixes (17E) now?" The human answered: "Yes, start 17E". This starts the draft only. The change is constitutional: it applies only after the human reviews the diff, records ratification, and a fresh session runs the hook probes (`docs/agents.md`, "Escalation and gates").

## Findings (grading agent self-check, `target/autograder/final-20261120/selfcheck-cnguye69.csv`, run on Phase 15)

- F05 FAIL: "PreToolUse: .claude/hooks/guard-dangerous.sh\" does not exist" and the same for `format-scala.sh`, `validate-agent-files.sh` and `verify-tests-ran.sh`. Cause (coordinator reading of the grader's `hook_script` parser, the same in its three published versions): each `command` in `.claude/settings.json` is `"$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.sh"` with the quotes around the whole path. The parser removes `"$CLAUDE_PROJECT_DIR/` and is left with `.claude/hooks/<name>.sh"`, a path with a trailing quote. Simulated with the parser's own rules: the form `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh` (quotes around the variable only, the form in the Claude Code hook documentation) resolves to `.claude/hooks/<name>.sh`.
- F07 FAIL: "server 'github-readonly', headers 'Authorization' looks secret but is a literal value". Cause: the grader accepts only a value that is exactly one `${VAR}` reference; `"Bearer ${GITHUB_MCP_TOKEN}"` has a literal prefix. Simulated: `"${GITHUB_MCP_AUTHORIZATION}"` passes. Observed in this Claude Code session: the server fails to connect with "Authorization header is badly formatted" (the variable is not set here).

## Work

| ID | Work | Owner | Writes | Gate |
|---|---|---|---|---|
| 17E | Change the four hook `command` values to the `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh` form; change the `github-readonly` `Authorization` header to a single variable reference (`${GITHUB_MCP_AUTHORIZATION}`, whose value is `Bearer <token>`); list every other file that names the old forms or `GITHUB_MCP_TOKEN` and its owner | factory-engineer | `.claude/settings.json`, `.mcp.json` | JSON parse, `bash -n`, the repository's own constitution and hook checks, review, **human ratification**, fresh-session hook probes |

Follow-ups from the factory-engineer's draft report (same package, same ratification): `.claude/MCP-TRUST.md:7` names `GITHUB_MCP_TOKEN` (factory-engineer); `README.md:57`, `:405` and `:417` name `GITHUB_MCP_TOKEN` (documentation-engineer). Both owners change only those lines to `GITHUB_MCP_AUTHORIZATION` (value `Bearer <token>`).

Not in scope: hook script bodies, other settings, README or docs text (documentation-engineer), tests under `tests/**` (test-engineer) and scripts (infra-engineer). References found there are returned as `BLOCKED-ON` with the owner.

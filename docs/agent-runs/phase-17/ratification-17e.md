# Phase 17 human ratification: package 17E (hook command paths and the MCP header)

Recorded 2026-11-22 (Sun, 6:53 PM CST) by the coordinator from the human's chat answer. The agents drafted and reviewed the change; only the human ratifies.

## What was ratified

Uncommitted diff on `phase-17` at `10f9bd4` (work order `work-order-3-hooks-mcp.md`):

- `.claude/settings.json` (factory-engineer): the four hook `command` values change from `"$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.sh"` to `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh` for `guard-dangerous.sh`, `format-scala.sh`, `validate-agent-files.sh` and `verify-tests-ran.sh`; events, matchers and order unchanged.
- `.mcp.json` (factory-engineer): `github-readonly` header `Authorization` changes from `Bearer ${GITHUB_MCP_TOKEN}` to `${GITHUB_MCP_AUTHORIZATION}` (the variable holds `Bearer <token>` and is set only in the shell).
- `.claude/MCP-TRUST.md:7` (factory-engineer) and `README.md:57`, `:405`, `:417` (documentation-engineer): name the new variable.

## Evidence at the decision

- Factory-engineer: JSON parse OK for both files; `bash -n` OK for the four hooks; `validate-agent-files.sh`: "Validated 18 unique agents, reviewer fence, 32 representative ownership paths and 18 routes", exit 0; `scripts/tests` `test_check.py`: Ran 54 tests, OK.
- Coordinator: `scripts/check.sh --only constitution,hooks`, run id `20261123T005204Z-77985`: constitution PASS (2071 JSON files parse), hooks PASS (4 scripts, `bash -n` and shellcheck).
- Independent review (code-reviewer, Claude Opus 5.5, effort high): APPROVE; one minor (`docs/threat-model.md:118` goes stale after ratification, documentation-engineer) and two nits.

## Question and answer (verbatim)

The coordinator asked: "The reviewer approved the 17E change. Do you ratify it? The change: (1) in .claude/settings.json, the 4 hook commands change from "$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.sh" (whole path quoted) to "$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh (only the variable quoted; same scripts, matchers and order); (2) in .mcp.json, the GitHub header changes from "Bearer ${GITHUB_MCP_TOKEN}" to "${GITHUB_MCP_AUTHORIZATION}", so locally you set GITHUB_MCP_AUTHORIZATION="Bearer <token>"; (3) .claude/MCP-TRUST.md and 3 README lines name the new variable. After a yes, a fresh Claude Code session tests the hooks before anything is committed."

The human answered (option chosen): "Ratify (Recommended)".

## Still required before commit

1. A fresh Claude Code session runs the hook probes and saves the exact prompts and results under `docs/agent-runs/phase-17/`.
2. The documentation-engineer updates `docs/threat-model.md:118`.
3. One full check, then a commit only on the human's explicit yes.

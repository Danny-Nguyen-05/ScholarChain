# Phase 1 hook test report

Only safe local probes were run; none executed Terraform, AWS mutation, deployment, or a real project build.

| Probe | Result |
|---|---|
| Destructive text in a Bash request | Blocked before the command ran (exit 2) |
| Read `.env` request | Blocked before the read (exit 2) |
| Non-factory Edit of `./CLAUDE.md` and `docs/../CLAUDE.md` | Both blocked (exit 2) |
| Factory Edit request for `./CLAUDE.md` | Allowed by the hook (exit 0); no file edit was performed |
| Stop hook, missing/fresh/stale test marker in temporary fixture | Exit 2/0/2; changed shell script also made the marker stale |
| Formatter fake `sbt` fixture | Invoked file-scoped `scalafmtOnly modules/core/Record.scala` |

Post-ratification Claude Code probes are specified in `.claude/PROBES.md`. A real `sbt check`, `markTestRun`, nested-project formatting, MCP connection, and Claude hook-loading test remain unverified because the build and accepted fresh session do not exist yet.

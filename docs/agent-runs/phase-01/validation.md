# Phase 1 validation

Run from the `ScholarChain` folder on 2026-09-29. These are shell-level checks, not a Claude Code integration result.

| Check | Observed result |
|---|---|
| `jq empty .claude/settings.json .mcp.json .claude/ownership-audit.json` | Exit 0 |
| `bash -n .claude/hooks/*.sh` | Exit 0 |
| `.claude/hooks/validate-agent-files.sh` | Exit 0: “Validated 18 unique agents, reviewer fence, 32 representative ownership paths and 18 routes” |
| `ls -l .claude/hooks` | All four scripts show executable bits (`-rwxr-xr-x`) |
| Guard JSON: Bash command `echo terraform destroy` | Exit 2: blocked Terraform apply/destroy |
| Guard JSON: Read path `.env` | Exit 2: blocked secret path access |
| Guard JSON: Bash command `aws sts get-caller-identity` | Exit 0; the command itself was not run |
| Guard JSON: `service-engineer` Edit path `./CLAUDE.md` | Exit 2: blocked constitutional edit |
| Guard JSON: main Edit path `docs/../CLAUDE.md` | Exit 2: blocked constitutional edit |
| Guard JSON: `factory-engineer` Edit path `./CLAUDE.md` | Exit 0; no file was edited |
| `git status --short --branch` | Exit 128: folder is not a Git repository |
| `command -v sbt`; `command -v uvx` | Both exit 1: unavailable locally |
| `shasum -a 256 -c docs/agent-runs/phase-01/proposal-manifest.sha256` | Exit 0: all 36 proposed control files match the review snapshot |

Factory-engineer's temporary fixture also observed Stop-hook exit 2 with no test marker, exit 0 with a fresh marker, exit 2 with a stale marker, and exit 2 on a repeated stale attempt. The revised fixture also checked a changed shell script. A fake `sbt` fixture observed the formatter invoke only `scalafmtOnly modules/core/Record.scala`. No real Scala build or `sbt check` exists yet. `.claude/PROBES.md` records the integration probes to run after ratification.

The proposal spans 36 control files before this phase evidence. `proposal-manifest.sha256` records the exact review snapshot. With no Git repository or prior Phase 0 commit, a trustworthy Git diff against the accepted baseline cannot be produced. Every proposed file is present in the folder for direct review.

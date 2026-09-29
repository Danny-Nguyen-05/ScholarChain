# ScholarChain agent ownership and routing

This is the proposed authoritative one-writer map for ScholarChain. It takes effect only after human ratification and a fresh active-tool session. The human architect owns phase gates and constitutional ratification. Codex and Cursor are the student's active tools; their orchestrator routes by this map, assembles reports, and keeps review independent. The `.claude/agents/` definitions are assignment/Claude artifacts and do not automatically create Codex or Cursor subagents or enforce their tool fields.

## Artifact ownership

| Agent | Creates and owns | Must not do | Primary gate |
|---|---|---|---|
| `factory-engineer` | `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `.claude/**` except `.claude/.last-test-run`, `.mcp.json`, and the Phase 1 template `docs/agent-runs/README.md` | Application, data, build, infrastructure or deployment work | Human constitutional ratification and code review |
| `build-engineer` | `build.sbt`, `project/**`, `.scalafmt.conf`, local compose files, packaging, `.gitignore`, and the ignored generated marker `.claude/.last-test-run` | Application source, version-only maintenance, Terraform or deployment | `sbt check` and code review |
| `domain-engineer` | `modules/core/**`, shared records, stable IDs, serialization and config contracts | Dataset retrieval, distributed jobs, storage adapters, routes or infrastructure | Contract tests, `sbt check`, review |
| `dataset-engineer` | `datasets/**`, manifests, bounded acquisition scripts, schemas, licenses | Hadoop or Spark analytics, match policy | Dataset validation and manifest review |
| `hadoop-engineer` | `modules/hadoop/**`, MapReduce jobs, counters, rejects and Hadoop tests | Spark, storage or services | Bounded sample and deterministic checks |
| `entity-resolution-engineer` | `modules/entity-resolution/**`, blocking, features, thresholds, calibration, match schemas | Graph analytics, API synthesis, infrastructure | Gold-set evaluation and policy review |
| `spark-engineer` | `modules/spark/**`, graph construction, analytics and path evidence | Hadoop parsing, runtime API, Terraform | Graph tests, bounded run, invariants |
| `storage-engineer` | `modules/storage/**`, S3, Neptune, DynamoDB, S3 Vectors and optional OpenSearch adapters | Terraform, synthesis, HTTP routes | Contract tests and bounded load |
| `rag-engineer` | `modules/rag/**`, `prompts/runtime/**`, `prompts/schemas/**`, evidence and claim verification | HTTP transport, cloud deployment, data acquisition | Retrieval and groundedness evaluation |
| `service-engineer` | `modules/services/**`, APIs, routes, health and runtime composition | Distributed algorithms, Terraform, constitution | API tests and `sbt check` |
| `test-engineer` | `tests/**` cross-module, contract, adversarial and end-to-end tests; module-local test trees only if later assigned by a ratified work order | Any production implementation | Exact pass/fail report; no production edits |
| `code-reviewer` | Review report text returned to orchestrator; no implementation files | Any write or edit | Read-only verdict with paths and lines |
| `infra-engineer` | `infra/terraform/**`, `scripts/**`, optional `.github/workflows/**` | Apply, live deploy, application source | Format, validate, plan, syntax and security review |
| `deploy-engineer` | Deployment execution and release evidence returned to orchestrator | Terraform or script authoring | Approved plan, clean tree, smoke and rollback gate |
| `experiment-engineer` | `experiments/**`, `load-tests/**`, raw result evidence | Production algorithm edits, invented results | Reproducible run and raw evidence |
| `documentation-engineer` | `README.md`, `docs/**` except the reserved subtrees below, final report, diagrams and demo | Implementation edits or invented results | Link check, command replay, evidence review |
| `incident-responder` | `docs/incidents/**`, diagnosis and approved bounded recovery evidence | Schema change, destructive repair, infra authorship | Human escalation for risky recovery |
| `dependency-updater` | Version values only in the build-engineer-approved dependency ledger, plus update report | Build structure, features, unapproved major upgrades | `sbt check`, vulnerability and code review |

**Precedence and exceptions.** Each module owner also owns that module's local `src/test/**` tree, including Hadoop integration tests. The test-engineer owns `tests/**` for independent cross-module, contract, adversarial and end-to-end tests. A later ratified work order may designate a specific module-local test subtree to the test-engineer by removing it from the module owner's territory first; none is designated now. A dependency-updater may edit only value tokens in a ratified ledger, even when the ledger lives under `project/**`; the build-engineer retains structural ownership. `.claude/.last-test-run` is an ignored build-generated marker owned by the build-engineer, not a constitutional control file; the factory owns the remaining `.claude/**` files. `docs/agents.md` and `docs/agent-runs/README.md` belong to the factory. `docs/agent-runs/**` phase evidence is assembled by the orchestrator from agent reports; human decisions and ratification records are human-owned and immutable to agents. `docs/incidents/**` belongs to the incident responder. `AGENTS.md` is supplementary cross-tool guidance and belongs to the factory.

An unlisted artifact is an orphan: stop and ask the human to assign exactly one writer before creation. Two claimed writers are a collision: stop, narrow paths, and ratify the changed map. No implied shared write ownership follows from read access.

The factory's `.claude/ownership-audit.json` lists representative paths and lifecycle routes for automated collision and orphan checks. It samples the approved classes; it does not automatically assign an unknown path. The Phase 2 build-engineer must implement `markTestRun` so that `sbt check` updates `.claude/.last-test-run` only after all required tests pass, and must add the local marker to `.gitignore`.

The Stop hook checks Scala, Java, shell and Python source under `modules/**`, `tests/**`, `scripts/**`, `datasets/scripts/**`, `experiments/scripts/**` and `load-tests/**`. Terraform plans, datasets, prompts and constitutional changes have their separate owner gates; do not treat the test marker as proof that those gates passed.

## Lifecycle routing

| Work | Owning agent | Required gate |
|---|---|---|
| Agent constitution, hooks, permissions, commands | `factory-engineer` | Human ratification and fresh session |
| Build and packaging | `build-engineer` | `sbt check`, reviewer |
| Domain schemas and stable IDs | `domain-engineer` | Contract tests, reviewer |
| Dataset manifests and bounded source samples | `dataset-engineer` | License, checksum and manifest review |
| Hadoop preparation | `hadoop-engineer` | Deterministic bounded run |
| Identity matching | `entity-resolution-engineer` | Gold-set evaluation |
| Spark graph and metrics | `spark-engineer` | Known-graph tests and bounded run |
| Storage adapters and loaders | `storage-engineer` | Contract and bounded load tests |
| Runtime retrieval and claim verification | `rag-engineer` | Groundedness and adversarial tests |
| HTTP services | `service-engineer` | API tests and `sbt check` |
| Cross-module tests | `test-engineer` | Exact pass/fail evidence |
| Independent code review | `code-reviewer` | Read-only findings and verdict |
| Terraform and automation authoring | `infra-engineer` | Format, validate, plan and human approval |
| Approved release execution | `deploy-engineer` | Approved plan, smoke and rollback gate |
| Evaluation and elasticity | `experiment-engineer` | Approved budget and raw results |
| README, report and runbook | `documentation-engineer` | Link, command and evidence checks |
| Diagnosis and bounded incident response | `incident-responder` | Human escalation for live risk |
| Pinned version changes | `dependency-updater` | Ledger approval, tests and review |

## Escalation and gates

Return `BLOCKED-ON` with exact path, evidence, required owner and requested decision when ownership is ambiguous, a contract is missing, or a gate is not met. The orchestrator routes the dependency and reruns the blocked agent in a fresh context after repair. Reviewers report defects to the owning agent through the orchestrator; they never fix them.

The human architect must approve constitutional changes, data destruction, security-sensitive changes, Terraform apply or destroy, deployment, expensive scale changes, destructive cleanup, ambiguous ownership, and any widening of tools or autonomy. A reviewed Terraform plan is not approval to apply. Record the decision in phase evidence before action. Ratified constitutional changes require a fresh session. No agent may ratify its own work, rewrite a human decision, or claim that a platform instruction is a hard sandbox.

Claude Code's PreToolUse guard rejects direct Write/Edit requests against constitutional paths from any agent other than `factory-engineer`, including the main orchestrator, and conservatively blocks common Bash mutations to those paths. The hook allows inspection and cannot identify every possible indirect shell write. Treat the one-writer map and human review as required controls alongside the hook.

The local hook prerequisites are Bash, `jq`, and Python 3. Their presence and the hook exit behavior must be checked in the post-ratification probe; a hook that cannot start may fail open in Claude Code.

## Platform boundary

Codex and Cursor use root `AGENTS.md` as their shared instruction file and are the active workflow. Cursor may also load `CLAUDE.md`, so its Claude-only directions are explicitly conditional. Neither tool automatically registers `.claude/agents/` roles or enforces `.claude/settings.json` hooks and tool fences. Route owners explicitly and use native approvals, sandboxing and human gates. If Claude Code is ever used, it can load `CLAUDE.md`, the agent definitions, project settings and hooks, and the Claude-specific probes apply then. The course README specifies a Claude Code orchestrator; the Codex/Cursor workflow is a disclosed deviation until the instructor accepts it. All required `.claude/` artifacts remain in the repository.

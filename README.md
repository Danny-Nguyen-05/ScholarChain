# ScholarChain

**Student:** Danny Nguyen
**University e-mail:** cnguye69@uic.edu
**Course project:** CS 441 ScholarChain, individual submission (no other team members)

## Summary

ScholarChain answers questions about scholarly collaboration (who works with whom, how strongly, how the network is structured and how it changes over time) from linked open bibliographic data, and checks every claim in an answer against stored evidence. A person-level coauthorship graph built from one source is unreliable because one researcher appears under several names and identifiers, and a language model asked about such a graph can invent a researcher, a path or a count. The system therefore computes every number in batch jobs and lets the runtime model only select claims that a deterministic verifier already accepts, each with evidence IDs that resolve to stored records.

ScholarChain is a Scala 3, Hadoop MapReduce, Spark, AWS and Graph-RAG system. Modules: `core` (stable IDs, records, configuration contracts), `hadoop` (distributed input preparation), `entity-resolution` (cross-dataset identity matching), `spark` (temporal graph and deterministic metrics), `storage` (S3, Neptune, DynamoDB, S3 Vectors adapters), `rag` (retrieval planning and evidence-checked claims) and `services` (typed APIs and runtime composition). All AWS infrastructure is authored in Terraform (`infra/terraform`).

What was actually run, in short (details and sources in the [final report](reports/final-report.md)): a 10,577-work DBLP slice went through Hadoop and entity resolution on EMR and through Spark locally (the Spark step failed on EMR); the graph was loaded into Neptune and the run ledger into DynamoDB in the first live session; 10,000 vectors were written to S3 Vectors in the second; the runtime answered a 33-question benchmark twice; one AWS load run was aborted by a 5xx burst. The AWS stack was destroyed on 2026-11-18, so no deployment is running (no deployed-application link exists). Known limitations are listed [below](#known-limitations).

- Final report: [reports/final-report.md](reports/final-report.md)
- Demonstration video: no link is recorded in the repository yet; the author adds it after upload (video editing is outside the repository). The script is [docs/demo-script.md](docs/demo-script.md).
- Release manifest: [reports/release-manifest.md](reports/release-manifest.md)
- Evaluation: [docs/evaluation.md](docs/evaluation.md) (the full Phase 16 record is [docs/report/evaluation.md](docs/report/evaluation.md))
- Every other deliverable: the [deliverable index](#deliverable-index)

## Architecture summary

Build time (left to right): DBLP XML and OpenAlex, Crossref and ORCID JSONL, then nine Hadoop MapReduce jobs (normalise, index, block, join, publication teams, coauthor pairs), then entity resolution (identity decisions per candidate pair), then Spark (temporal weighted coauthorship graph, components, communities, bridges, k-core, paths, semantic summaries), then loaders into S3, Neptune, DynamoDB and S3 Vectors (Voyage `voyage-4-lite` embeddings, 256 dimensions).

Runtime: a client calls `query-api` (API-key authenticated, on an HTTPS load balancer in front of ECS Fargate). A planner turns the question into an allowlisted typed plan, retrieval gathers graph evidence (a bounded S3 artifact built from the Spark export, and Neptune through `graph-service`) and semantic context (`semantic-service` over S3 Vectors), the model selects claims from a scaffold that the deterministic verifier accepts, and the answer carries evidence IDs that `GET /v1/evidence/{id}` and `GET /v1/explain/{queryId}` resolve. The fourth service is the `embedding-worker`.

Diagrams and component contracts: [docs/architecture.md](docs/architecture.md); source-to-answer lineage: [docs/data-lineage.md](docs/data-lineage.md); route reference: [docs/api.md](docs/api.md); verified limits and Region: [docs/service-limits.md](docs/service-limits.md); threats and controls: [docs/threat-model.md](docs/threat-model.md); operations: [docs/runbook.md](docs/runbook.md).

## Agentic workflow summary

The software was produced by a one-writer agent system: each artifact class has one owning subagent, an orchestrator routes every task, reviewers do not edit, and the human architect holds the phase and ratification gates. This README documents it in [Agentic workflow](#agentic-workflow): the [agent catalog](#agent-catalog) (all 18 agents), [hooks, commands and MCP servers](#hooks-commands-and-mcp-servers) and [Reproducing the agentic workflow](#reproducing-the-agentic-workflow). Authoritative files: [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md), [docs/agents.md](docs/agents.md), [.claude/agents/](.claude/agents/), [.claude/settings.json](.claude/settings.json), [.claude/hooks/](.claude/hooks/), [.claude/commands/](.claude/commands/), [.mcp.json](.mcp.json). Per-phase prompts, reports, reviews, test reports, repairs, human gates and commits: [docs/agent-runs/](docs/agent-runs/).

## Prerequisites

Commands are run from the repository root unless a step says otherwise. Replay status is stated for each command group; "not replayed in 17A (replay in 17G)" means the Phase 17 documentation pass did not run it, and the clean-checkout replay will.

### Local software

| Tool | Version | Needed for |
|---|---|---|
| JDK | 17 (`sbt check` and the packaging tasks refuse any other version) | all `sbt` commands |
| sbt | 1.10.7 (pinned in `project/build.properties`) | build, tests, packaging |
| Terraform | exactly 1.13.5 (AWS provider 6.44.0) | Terraform checks and plans |
| Python | 3 (standard library for most scripts; PyYAML only for `datasets/scripts/validate_datasets.py`) | scripts, experiments, evaluation |
| `bash`, `jq`, `shellcheck`, `git`, `shasum` | any recent | scripts, hooks, `scripts/check.sh` |
| Docker with buildx | any recent | `scripts/package.sh` (images) |
| Claude Code | optional | the agentic replay only; see the [version record](#version-record) |

The author's observed versions are in the [version record](#version-record). On the author's machine the default `java` is not 17, so `JAVA_HOME` must be set explicitly.

### AWS prerequisites (live, human-gated work only)

No local command in this README needs an AWS account. Live work needs: an AWS account with the approved deployer sign-in described in [infra/terraform/deployer/README.md](infra/terraform/deployer/README.md) (profile `scholarchain-deployer`, MFA), a private `infra/terraform/environments/course.local.tfvars` (copy of the `.example` file; git-ignored), provider keys entered by hand into Secrets Manager (see [Selecting a configuration](#selecting-a-configuration)), a recorded human approval and pre-spend receipt for every mutating stage ([scripts/README.md](scripts/README.md), "Human approval points"), and a Region (the project used `us-east-2`; [docs/service-limits.md](docs/service-limits.md)). Budget: USD 25 ceiling across AWS, Anthropic and Voyage AI.

### Environment variable names (no values)

`JAVA_HOME`, `SBT_BIN`, `TERRAFORM_BIN`, `SCHOLARCHAIN_AWS_REGION`, `AWS_PROFILE`, `SCHOLARCHAIN_TF_PRIVATE_VARS` (path of the private tfvars file), `SCHOLARCHAIN_RUNTIME_ARCHIVE`, `SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI`, `SCHOLARCHAIN_SMOKE_API_KEY` (the query-api key used by smoke tests; kept in the environment or a temporary header file, never on a command line), `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` and `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST` (optional, local smoke), `GITHUB_MCP_AUTHORIZATION` (the whole header value, `Bearer <token>`) and `SCHOLARCHAIN_AWS_READONLY_PROFILE` (optional MCP servers). The runtime service variables are listed under [Selecting a configuration](#selecting-a-configuration). Meaning of each script variable: [scripts/README.md](scripts/README.md), "Settings and environment variables". Never put a value in a tracked file.

## Build, format, test and package commands

```bash
export JAVA_HOME=<your JDK 17 home>          # for example /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home

sbt -batch fmt                                # format every module and the build (writes files)
sbt -batch compile                            # compile
sbt -batch core/test                          # one module's tests (observed 2026-11-19: 207 succeeded, 0 failed)
sbt -batch check                              # the repository definition of done: format check, compile, all tests, markTestRun
sbt -batch clean check                        # the same from a clean build (the course's final gate)
sbt -batch packageRelease                     # Hadoop submit JAR and bundle, Spark job JAR, ER job JAR, service distribution, manifest
bash scripts/check.sh                         # the seven gates: constitution, hooks, shell, python, terraform, script-tests, sbt
bash scripts/package.sh                       # packageRelease plus four linux/amd64 images and a release manifest under target/release/
```

Replay status: `sbt -batch core/test` was observed on 2026-11-19 (see exercise E2 below). The other commands in this block are not replayed in 17A (replay in 17G). The last full `scripts/check.sh` run on `main` at `55fb1b3` ended `RESULT: PASS gates=7`; counts are in [reports/release-manifest.md](reports/release-manifest.md). Expect more than ten minutes for a full check. Individual module tests: `sbt -batch <module>/test` for `core`, `hadoop`, `entityResolution`, `sparkAnalytics`, `storage`, `rag`, `services` and `independentTests`; script tests run inside `scripts/check.sh` (`python3 -I -m unittest discover -s scripts/tests`).

## Terraform format, validate, test and plan commands

```bash
cd infra/terraform
terraform init -backend=false -input=false    # downloads the pinned provider; no AWS call
terraform fmt -check -recursive
terraform validate
terraform test                                # offline tests with mocked providers
cd ../..

# Plan (read-only; never applies). Dry run is the default and prints the exact commands:
bash scripts/plan.sh --env course
# Real plan: needs the approved profile and the private variable file; the plan runs from a git archive of the commit
AWS_PROFILE=<approved profile> SCHOLARCHAIN_TF_PRIVATE_VARS=<private tfvars path> \
  bash scripts/plan.sh --env course --region us-east-2 --execute
```

The real plan prints the action list (`PLAN-ACTION:` lines), the plan checksum and a receipt, and writes private files under `target/plans/`. A reviewed plan is not approval to apply; the human records the approval first. Replay status: the first four commands are covered by the Terraform gate of `scripts/check.sh` (included in the full check above); the dry-run `plan.sh` and the real plan are not replayed in 17A (replay in 17G; the real plan needs AWS access and is a human-gated step). Plan checksums from the live session are in [reports/release-manifest.md](reports/release-manifest.md).

## Deployment path (human-gated)

Deployment was done once, in the second live session (2026-11-18), and destroyed afterwards. The path, with the script and the gate for each step (full procedure and rollback: [docs/runbook.md](docs/runbook.md) and [docs/runbooks/phase-14-live-session.md](docs/runbooks/phase-14-live-session.md)):

1. Package: `bash scripts/package.sh --require-images --require-runtime-archive` (local).
2. Plan: `bash scripts/plan.sh --env course ... --execute` (read-only; the human reviews the action list).
3. Approval record: the human writes the `APPROVED_*` lines naming the plan's sha256 ([scripts/README.md](scripts/README.md)).
4. Apply by stage: `bash scripts/deploy.sh --stage base-apply --plan <plan file> --execute`, then `--stage push`, then `--stage runtime-apply` (each stage needs its own approval and pre-spend receipt; without `--execute` each is a dry run).
5. Load: `scripts/upload-slice.sh` (curated slice to S3) and the storage loader steps in the live-session runbook.
6. Smoke test: `bash scripts/smoke-test.sh --url https://<api host> --api-key-env SCHOLARCHAIN_SMOKE_API_KEY` (six checks: `healthz`, `readyz`, query, evidence, idempotency, error path).
7. Rollback: `bash scripts/rollback.sh --env course ...` (dry run unless `--execute`; policy in [scripts/README.md](scripts/README.md)). Rollback was not exercised live.

Replay status: none of these steps was replayed in 17A (replay in 17G is limited to the offline parts; the live steps need the human gate and spend and are not repeated). Evidence of the live run: [docs/agent-runs/phase-15/evidence/session-2/INDEX.md](docs/agent-runs/phase-15/evidence/session-2/INDEX.md).

## Bounded data-run path

Three bounded paths, from cheapest to most expensive:

1. **Local runtime smoke (offline, no AWS, no model call):** `bash scripts/smoke-local.sh --build` starts the real `query-api` on loopback in `offline-synthetic` mode with a throwaway key, runs the smoke checks against the fixture question "Synthetic fixture: publication count for A" and stops the service. Recorded result: `RESULT: PASS local offline-synthetic query-api passed all smoke checks` (observed 2026-11-19, exercise E2). This is fixture data. Not replayed in 17A (replay in 17G).
2. **Local pipeline on the real S slice (no AWS):** the Phase 15 P6 local chain runs the exact EMR step chain (stage-in, Hadoop prep, entity resolution, class-origin check, Spark job, copy-out) on the 10,577-work DBLP slice:
   ```bash
   sbt -batch packageEmr
   python3 -I experiments/scripts/make_dblp_subsets.py        # writes target/experiment-inputs/15a/size-{25,50,100}/ (size-100 is the S slice)
   python3 -I scripts/lib/p6_local_chain.py run --size S --retain
   ```
   It also needs the Hadoop client classpath file and the pinned runtime archive described in `python3 -I scripts/lib/p6_local_chain.py --help` and [experiments/README.md](experiments/README.md). Recorded outcome: six passing local replays with identical logical outputs ([docs/evaluation.md](docs/evaluation.md), group 7). Not replayed in 17A (replay in 17G).
3. **Bounded EMR run (cloud, human-gated, costs money):** `scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-100.json --cluster-id <J-id> --execute` after the approval record and pre-spend receipt. In the live session this ran Hadoop and entity resolution to completion and failed at the Spark step ([incident record](docs/incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md)). Do not rerun it without a human decision.

Hadoop-only and module-level bounded runs with fixtures run inside `sbt -batch hadoop/test` and `sbt -batch sparkAnalytics/test`. The dataset samples can be verified without any network: `(cd datasets && shasum -a 256 -c samples/SHA256SUMS)`.

## Query examples

The API contract is [docs/api.md](docs/api.md) and `modules/services/src/main/resources/openapi/scholarchain.v1.yaml`. The examples below use a header file so the key never appears on a command line. `<host>` is the query-api URL: `http://127.0.0.1:<port>` for a local service, or the HTTPS API host of a deployed stack (none is deployed now).

```bash
H="$(mktemp)"; printf 'Authorization: Bearer %s\n' "$SCHOLARCHAIN_SMOKE_API_KEY" > "$H"

# 1. Ask a question. The Q12 benchmark questions are in experiments/inputs/q12/questions.txt
curl -sS -H @"$H" -H 'Content-Type: application/json' -H 'Idempotency-Key: readme-1' \
  -X POST "<host>/v1/query" \
  -d '{"question":"Which researchers have the most distinct coauthors?","output":{"includeScores":false}}'

# 2. Resolve one cited evidence id from the answer
curl -sS -H @"$H" "<host>/v1/evidence/<evidenceId>"

# 3. Explain the answer: stages, prompt and model versions, claim verdicts (attempted, verified, rejected)
curl -sS -H @"$H" "<host>/v1/explain/<queryId>"

# 4. Semantic retrieval only (no model call; embeds the question)
curl -sS -H @"$H" -H 'Content-Type: application/json' -X POST "<host>/v1/semantic/retrieve" -d '{"question":"graph analytics","topK":5}'
rm -f "$H"
```

Replay status: not replayed in 17A (replay in 17G). The local fixture service answers only the supported fixture question ("Synthetic fixture: publication count for A"); a real answer needs a deployed stack with a model key, which is not available now. Real recorded answers, with their evidence and explain records, are in the Q12 raw under [experiments/results/phase16/q12-raw/](experiments/results/phase16/q12-raw/) and are summarised in [docs/evaluation.md](docs/evaluation.md). The body of the `/v1/semantic/retrieve` call is `{question, topK 1..20, filters?}` as the smoke client sends it (`scripts/lib/smoke_client.py`).

## Experiment reproduction commands

```bash
python3 -I experiments/scripts/check_manifests.py                 # manifest validation
python3 -I experiments/scripts/eval16_repro.py --verify           # regenerate every Phase 16 table and compare byte for byte
python3 -I experiments/scripts/eval16_identity.py --out-dir <dir> # one table; the others are eval16_graph.py, eval16_answers.py, eval16_retrieval.py, eval16_perf.py, eval16_factory.py
```

Observed in 17A on 2026-11-22 (offline): `eval16_repro.py --verify` ended `REGENERATION: PASS pass=24 fail=0 skipped_scripts=0` with exit status 0; `check_manifests.py` is in the replay table of the [final report](reports/final-report.md). Tables whose inputs are git-ignored raw files regenerate only on the machine that holds them. Method notes and every experiment manifest: [experiments/README.md](experiments/README.md) and [load-tests/README.md](load-tests/README.md). Live experiments (the load test, EMR runs) need the human gate and spend; they are not part of any offline reproduction.

## Cleanup path

```bash
bash scripts/cleanup.sh --env course --region us-east-2 --profile <approved profile>             # dry run: classifies the state, lists nothing destructive
bash scripts/cleanup.sh --env course --region us-east-2 --profile <approved profile> --prepare   # plan the release of deletion protection
# then: list the exact destructive actions, and only with the printed confirmation token bound to that saved plan:
bash scripts/cleanup.sh --env course --region us-east-2 --profile <approved profile> --confirm <token> --plan <saved plan> --execute
```

The preserved item is the Terraform state; everything else is torn down in two passes after the evidence is archived (`bash scripts/archive-evidence.sh --phase NN --label LABEL --include CATEGORY=PATH`). Order, inventories, provider-key revocation and console checks: [docs/runbook.md](docs/runbook.md). Recorded run: inventory 297 entries before, 65 after pass 1, 63 after pass 2 ([inventories](docs/agent-runs/phase-15/evidence/session-2/inventories/), [Phase 15 human gate](docs/agent-runs/phase-15/human-gate.md)); what remains is two free `terraform_data` guards and tagging-index entries that the orchestrator judged to be leftovers of deleted or inactive resources (the state of the second KMS key in the inventory was not read). Replay status: cleanup was not re-run in 17A and was not rehearsed again (replay in 17G is limited to the dry run).

## Known limitations

Full list with sources: [reports/final-report.md](reports/final-report.md), "Limitations", and [docs/evaluation.md](docs/evaluation.md). In short:

- Scale: 10,577 DBLP works (the course asks for 100,000; about 10.5k and about 50k were approved) and 328,967 graph edges (the course target is 1,000,000, subject to budget).
- The Spark step failed on EMR; Spark results come from a local run on the same inputs. No EMR size was completed end to end. Size L ran locally only, with entity resolution bypassed for Spark.
- Elasticity: one AWS load run, aborted by a 5xx burst, with an empty graph and the semantic route only; the 5xx cause is not diagnosed.
- Answers: the Anthropic path is not deterministic (no `temperature`); all three community questions failed in both Q12 runs; 16B Session 1 abstained on every direct-coauthor and path question; there is no human-rated answer-usefulness score.
- Entity resolution: one reviewer; 15 of 72 true held-out matches withheld; no calibration.
- OpenAlex, Crossref and ORCID inputs are small committed samples that were not scaled with the DBLP slices.
- Vector-only and fused retrieval were not evaluated; the OpenSearch tier and CI workflows were not implemented.
- The AWS stack is destroyed; no live endpoint exists. Some Phase 16 tables regenerate only on the author's machine.
- Fresh-clone replay of the README commands is a separate Phase 17 gate (17G).

## Known repository-history limits

Two facts about the git history that cannot be changed without rewriting it. Facts only:

- Older commit messages do not name a phase (the course's recommended form is `phase-NN <agent>: ...`). Observed on 2026-11-22 with `git log --format=%s | grep -c '^phase-[0-9]'`: 37 of the 151 commit subjects start with `phase-NN`; the other 114 do not (merge commits, and messages written in other forms such as `Phase 15: ...`). The per-phase commit lists are in each phase's `commit.txt`, `accepted-commit.md` or `human-gate.md` where they exist under [docs/agent-runs/](docs/agent-runs/).
- Some test fixtures contain synthetic secret-shaped strings (fake keys, tokens and similar) so that negative tests can show that redaction and secret-pattern scans work. These strings are in tracked files and also in older commits. No real secret is in the repository. Secrets are kept in AWS Secrets Manager or approved local placeholders; real values were never committed (`.env`, `*.local.tfvars` and state files are git-ignored).

## Deliverable index

Every deliverable the course lists, and where it is. "Not in the repository" is stated where it applies.

| ID | Deliverable | Where |
|---|---|---|
| D01 | Git repository | this repository; commit history in `git log`; no git tag exists yet (the final tag and commit SHA are set at the release, see [reports/release-manifest.md](reports/release-manifest.md)) |
| D02 | Agentic constitution | [CLAUDE.md](CLAUDE.md), [AGENTS.md](AGENTS.md), [docs/agents.md](docs/agents.md), [.claude/agents/](.claude/agents/), [.claude/settings.json](.claude/settings.json), [.claude/hooks/](.claude/hooks/), [.claude/commands/](.claude/commands/), [.mcp.json](.mcp.json) with [.claude/MCP-TRUST.md](.claude/MCP-TRUST.md); tool versions in the [version record](#version-record); invoking every agent: the [agent catalog](#agent-catalog) |
| D03 | Agent run evidence | [docs/agent-runs/](docs/agent-runs/) (per phase: `prompt.md`, reports, `review.md`, `test-report.md`, `repairs.md`, `human-gate.md`, commit records); format in [docs/agent-runs/README.md](docs/agent-runs/README.md) |
| D04 | Deterministic build | [build.sbt](build.sbt), [project/](project/), [.scalafmt.conf](.scalafmt.conf); `sbt check` ([commands](#build-format-test-and-package-commands)) |
| D05 | Dataset package | [datasets/](datasets/): [manifest](datasets/dataset-manifest.yaml), [schemas](datasets/schemas/), [samples](datasets/samples/) with [checksums](datasets/samples/SHA256SUMS), [license notes](datasets/licenses/PORTFOLIO-NOTES.md), [acquisition scripts](datasets/scripts/README.md) |
| D06 | Hadoop package | [modules/hadoop/](modules/hadoop/) with job contracts, counters and rejects in [modules/hadoop/README.md](modules/hadoop/README.md); run scripts [scripts/run-bounded-pipeline.sh](scripts/run-bounded-pipeline.sh) |
| D07 | Entity-resolution package | [modules/entity-resolution/](modules/entity-resolution/), gold set and labels under [datasets/entity-resolution/](datasets/entity-resolution/), evaluation in [identity-metrics.md](experiments/results/phase16/identity/identity-metrics.md) |
| D08 | Spark package | [modules/spark/](modules/spark/) ([README](modules/spark/README.md): job, table and schema contracts); bounded run results in [docs/evaluation.md](docs/evaluation.md) |
| D09 | Storage package | [modules/storage/](modules/storage/) ([README](modules/storage/README.md)) |
| D10 | Runtime collaboration-analysis package | [modules/rag/](modules/rag/) ([README](modules/rag/README.md)), [prompts/runtime/](prompts/runtime/), [prompts/schemas/](prompts/schemas/) |
| D11 | Microservices package | [modules/services/](modules/services/) ([README](modules/services/README.md)), OpenAPI file `modules/services/src/main/resources/openapi/scholarchain.v1.yaml`, route reference [docs/api.md](docs/api.md) |
| D12 | Terraform package | [infra/terraform/](infra/terraform/) ([README](infra/terraform/README.md)); plan checksums in [reports/release-manifest.md](reports/release-manifest.md); plan receipts and the action lists in [Session 2 evidence](docs/agent-runs/phase-15/evidence/session-2/INDEX.md); no Terraform security scanner ran (Trivy and Checkov were not installed; a manual review plus Terraform schema checks was the approved fallback, not a scanner result: [infra/terraform/README.md](infra/terraform/README.md), the manual-review paragraph near line 250) |
| D13 | Reproducibility automation | [scripts/](scripts/) ([README](scripts/README.md)); no CI workflow (optional) was implemented |
| D14 | Deployment package | [reports/release-manifest.md](reports/release-manifest.md); smoke-test and rollback evidence listed in its section 10; [runbook](docs/runbook.md) |
| D15 | Experiment package | [experiments/](experiments/) ([README](experiments/README.md)), [load-tests/](load-tests/) ([README](load-tests/README.md)), raw and derived results in [experiments/results/phase16/](experiments/results/phase16/) |
| D16 | Evaluation package | [docs/evaluation.md](docs/evaluation.md), [docs/report/evaluation.md](docs/report/evaluation.md) |
| D17 | Documentation package | this README, [docs/architecture.md](docs/architecture.md), [docs/data-lineage.md](docs/data-lineage.md), [docs/threat-model.md](docs/threat-model.md), [docs/service-limits.md](docs/service-limits.md), [docs/runbook.md](docs/runbook.md), [docs/api.md](docs/api.md) |
| D18 | Final report | [reports/final-report.md](reports/final-report.md) |
| D19 | Demonstration video | not in the repository; the script is [docs/demo-script.md](docs/demo-script.md); the link is added by the author after upload |
| D20 | Cleanup evidence | [before and after inventories](docs/agent-runs/phase-15/evidence/session-2/inventories/), [cleanup results](docs/agent-runs/phase-15/evidence/session-2/section-c/cleanup-results.txt), [Phase 15 human gate](docs/agent-runs/phase-15/human-gate.md); Session 1 cleanup in [Phase 14 human gate](docs/agent-runs/phase-14/human-gate.md) |
| - | Cross-module and independent tests | [tests/](tests/) ([README](tests/README.md)) |
| - | Incident records | [docs/incidents/](docs/incidents/) (index [docs/incidents/README.md](docs/incidents/README.md)) |
| - | Runbooks and live-session plans | [docs/runbooks/phase-14-live-session.md](docs/runbooks/phase-14-live-session.md), [docs/runbooks/session-2-plan.md](docs/runbooks/session-2-plan.md) |
| - | Provider change (Bedrock quota) | [docs/report/provider-fallback.md](docs/report/provider-fallback.md) and the [provider sections](#model-providers-the-bedrock-restriction-and-the-fallback-configuration) below |
| - | Phase evidence (Session 1 and Session 2) | [Session 1 index](docs/agent-runs/phase-14/evidence/14b/session-1/INDEX.md), [Session 2 index](docs/agent-runs/phase-15/evidence/session-2/INDEX.md) |

The remaining sections of this README cover the model providers (first), the agentic workflow, and the note on test data that contains prompt-injection text. Other documents: the live-session runbook is [docs/runbooks/phase-14-live-session.md](docs/runbooks/phase-14-live-session.md); module and tool details are in [modules/rag/README.md](modules/rag/README.md), [infra/terraform/README.md](infra/terraform/README.md), [scripts/README.md](scripts/README.md), [load-tests/README.md](load-tests/README.md) and [experiments/README.md](experiments/README.md).

Status of the model-provider sections below: the provider configuration was authored and tested offline first (fake HTTP servers, Terraform tests, unit tests). Live calls to Anthropic and Voyage AI were made afterwards, in the first live session (2026-11-13 to 2026-11-15), the second (2026-11-18) and the Q12 benchmark runs (2026-11-20 and 2026-11-21); see "Verification status" at the end of the provider sections. No Bedrock call was made.

## Model providers, the Bedrock restriction and the fallback configuration

### The restriction

The planned models run on Amazon Bedrock (Claude Haiku 4.5 for answers, Titan Text Embeddings V2 for embeddings). The course AWS account had a Bedrock quota of 0 for these models (Haiku 4.5, Titan V2 and Nova Micro were all 0 in us-east-2; recorded in `docs/agent-runs/phase-14/prompt.md`). The student asked AWS to raise the quota and reports that AWS declined the increase (the AWS reply itself is not stored in the repository). On 2026-11-09 the instructor approved the fallback: the Anthropic API for synthesis and Voyage AI for embeddings, with all remaining infrastructure and processing staying on AWS. The ruling is recorded verbatim in `docs/agent-runs/phase-14/prompt.md` (section "Subphase 14B, repair round 3") with a screenshot at `docs/agent-runs/phase-14/evidence/14b/fallback/instructor-approval.png`. The Bedrock switch is retained.

### The two configurations

| | Primary (default) | Bedrock fallback |
|---|---|---|
| Synthesis provider | Anthropic API (`https://api.anthropic.com/v1/messages`) | Amazon Bedrock Converse |
| Synthesis model id | `claude-haiku-5-5` | Claude Haiku 4.5: `anthropic.claude-haiku-4-5-20251001-v1:0`, called through the inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0` (regions us-east-1, us-east-2, us-west-2) |
| Embedding provider | Voyage AI (`https://api.voyageai.com`) | Amazon Bedrock |
| Embedding model id | `voyage-4-lite` (model version tag `voyage-4-lite`) | Titan Text Embeddings V2: `amazon.titan-embed-text-v2:0` |
| Embedding dimension | 256 (`output_dimension` 256) | 256 (Titan also supports 512 and 1024; the index and `vector_dimension` are fixed at 256) |
| Credential | an API key in Secrets Manager (entered by hand) | AWS IAM only, no key |
| Temperature 0 | not possible: the Anthropic path never sends `temperature`, `top_p` or `top_k` (Haiku 5.5 rejects non-default values), so answers are not deterministic | kept as configured |
| Billing | Anthropic and Voyage, outside AWS | AWS |

The defaults live in one place per provider: `modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/ProviderDefaults.scala` (`AnthropicDefaults`, `VoyageDefaults`, `BedrockDefaults`) and `infra/terraform/phase14b-providers.tf`; `scripts/config/release.conf` mirrors them as data and `scripts/tests/test_providers.py` fails if they drift.

### Selecting a configuration

The two capabilities are chosen independently, so four combinations exist (primary, Bedrock for synthesis only, Bedrock for embeddings only, Bedrock for both).

1. **Terraform (the deployed choice).** In the private, git-ignored `infra/terraform/environments/course.local.tfvars` (copy of `course.local.tfvars.example`) set `synthesis_provider` (`anthropic` default or `bedrock`) and `embedding_provider` (`voyage` default or `bedrock`).
   - `anthropic`: leave `synthesis_model_id` and `synthesis_inference_profile_*` unset. `voyage`: leave `embedding_model_id`, `embedding_inference_profile_*` and `embedding_model_version` unset (or exactly `voyage-4-lite`) and keep `vector_dimension = 256`. A leftover Bedrock id is refused by `terraform_data.provider_guard`.
   - `bedrock` synthesis: set `synthesis_model_id` (and the inference profile id and regions above). `bedrock` embeddings: set `embedding_model_id` (default Titan V2) and `embedding_model_version`.
   - **A Bedrock run also needs the matching deployer variable(s), applied before the base plan.** The deployer stack (`infra/terraform/deployer`) writes the AWS permission limit (the "permissions boundary") that caps what the app and loader roles may ever do. By default that limit contains no Bedrock access. If you choose `bedrock` only in the main `course.local.tfvars` and not there, the roles are not allowed to call Bedrock and every Bedrock call fails with AccessDenied. So set, in the private, git-ignored `infra/terraform/deployer/deployer.local.tfvars`, `main_synthesis_provider = "bedrock"` for Bedrock answers and/or `main_embedding_provider = "bedrock"` for Bedrock embeddings (defaults `anthropic` and `voyage`; keep them equal to `synthesis_provider` and `embedding_provider` of the main file), then re-apply the deployer (runbook A4) before making the base plan. The Titan grant of the loader role depends on `main_embedding_provider`; the runtime boundary's Bedrock statement on either variable. See `infra/terraform/deployer/README.md` and `infra/terraform/README.md` ("Repair round 3"). The default configuration needs none of this.
2. **Runtime environment (set by Terraform for the aws service mode).** `SCHOLARCHAIN_SYNTHESIS_PROVIDER` (`anthropic` or `bedrock`), `SCHOLARCHAIN_EMBEDDING_PROVIDER` (`voyage` or `bedrock`), `SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL`, `SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION`, `SCHOLARCHAIN_MODELS_EMBEDDING_MODEL`, `SCHOLARCHAIN_EMBEDDING_MODEL_VERSION` and `SCHOLARCHAIN_EMBEDDING_DIMENSION`. Unset or blank selects the default; an unknown value is refused. The API keys are injected as `SCHOLARCHAIN_ANTHROPIC_API_KEY` and `SCHOLARCHAIN_VOYAGE_API_KEY` from Secrets Manager, never as plain environment settings.
3. **Keys.** Terraform creates only empty Secrets Manager containers `scholarchain-<environment>/anthropic-api-key` and `scholarchain-<environment>/voyage-api-key` (only for a selected provider). The human enters each value by hand; no key is ever in the repository, a variable file, the plan or the state. Steps: runbook section "Entering the Anthropic and Voyage API keys".

### Running each configuration

Follow [docs/runbooks/phase-14-live-session.md](docs/runbooks/phase-14-live-session.md). For the **primary** configuration leave both variables at their defaults, enter both keys after the base apply and before the runtime apply, then run the runtime apply, the 14C ingest (Voyage embeds the documents with `input_type` document) and the smoke queries (`input_type` query). For a **Bedrock** run set the variable to `bedrock`, complete the runbook's Bedrock preconditions (quota check, playground call, Marketplace subscription; kept in that section only for a Bedrock run) and skip the key container of that provider. Offline verification of either path needs no account: `cd infra/terraform && terraform init -backend=false && terraform test` and the module tests (`rag` provider specs use fake HTTP only).

### Re-embedding rule

Stored vectors and query vectors must use the same provider, model, version tag and dimension. The services refuse any difference with a typed error. **Changing the embedding model or provider is therefore not a toggle: it requires re-embedding every stored document and rebuilding the affected vector index** (Titan and Voyage vectors must never share an index). Do it with the 14C ingest, not with Terraform.

### Data leaves AWS

With the primary configuration the question text and the evidence snippets inside each prompt are sent to Anthropic, and document text and query text are sent to Voyage AI. Both providers bill outside AWS and AWS budgets and alerts do not cover them. The Anthropic path also accepts only prompts estimated under 100,000 tokens (a higher price tier starts above that).

### Cost and the USD 25 ceiling

The USD 25 project limit covers all three bills: AWS, Anthropic and Voyage AI. They are reported as separate items, followed by the combined total; a provider with no charge is listed as USD 0 with its usage documented (for example Voyage `voyage-4-lite` inside the free allowance of 200M tokens per account). Planned estimates (public prices of 2026-11-09, estimates not measurements):

| Item | Value |
|---|---|
| `claude-haiku-5-5` price | USD 0.10 input / 0.50 output per 1M tokens (prompts up to 100,000 tokens) |
| Estimated cost per answer | USD 0.001365 (tokens raised 30% for the new tokenizer) |
| Answer buckets | 14c 10, 15b 60, 16b 80, 17 10 = 160 answers = USD 0.2184 (raised from 115 answers = USD 0.156975 by the user decision of 2026-11-21, option A: a full Q12 benchmark rerun of 33 questions + 1 probe, and room for the Phase 17 demo) |
| Observed cost per answer | Not metered in full (planner tokens are not recorded). Synthesis call only, from local raw run evidence: 1 probe answer 27,359 in / 264 out, about USD 0.0029 (about 2.1 times the unit); 15 of 33 benchmark answers record usage, mean 8,664 in / 316 out, about USD 0.0010 (about 0.75 times). Varies with retrieval context; the Anthropic console is the cost of record |
| Synthesis cap | USD 1.33, a conservative upper bound; the bucket counts bind first |
| `voyage-4-lite` price and cap | USD 0.02 per 1M tokens; embedding cap USD 0.30 enforced with a token counter |

Report the real figures with `python3 -I scripts/lib/cost_report.py render --input <cost-report-input.json>` (input format in `scripts/README.md`, "Model providers and the cost report"). The pre-spend receipt also carries the human-entered Anthropic and Voyage spend to date. The USD 25 limit is a ceiling, not a target: monitor actual charges at AWS, Anthropic and Voyage and stop paid resources when the experiments finish. Revoke both provider keys in their consoles after cleanup. Observed figures after the live sessions are in "Verification status" below and in section 20 of the [final report](reports/final-report.md).

### Verification status

Verified live, with the evidence named:

- **Anthropic and Voyage calls were made.** First live session (2026-11-13 to 2026-11-15): 104 vectors written to S3 Vectors (95 written plus 9 unchanged in the second ingest), the real-model smoke passed all six checks after repairs, and the 40-question 16B run was asked; the project LLM ledger counts 55 answers ([Phase 14 human gate](docs/agent-runs/phase-14/human-gate.md), [Session 1 decision log](docs/agent-runs/phase-14/evidence/14b/session-1/00-timeline/decision-log.md)). Second live session (2026-11-18): 10,000 `voyage-4-lite` vectors at 256 dimensions, 0 rejected, after a first ingest in which an invalid pasted key produced HTTP 401 for all 10,000 items ([incident](docs/incidents/2026-11-18-vectors-ingest-1-voyage-401.md)). The Q12 benchmark runs of 2026-11-20 and 2026-11-21 used the live model ([docs/evaluation.md](docs/evaluation.md), group 4). Both Voyage keys of Session 2 were revoked on 2026-11-18, and the Q12 Anthropic key on 2026-11-21.
- **Cost, observed:** AWS USD 17.88, Anthropic USD 0.08 (earlier phases) and Voyage AI USD 0.00 as of 2026-11-20T15:48:56Z, combined USD 17.96 ([cost-report.log](docs/agent-runs/phase-15/evidence/session-2/c11/cost-report.log)); the Q12 Anthropic key shows USD 0.08 in the Console as a separate scope.

Not verified or not done: the Bedrock configuration was never run live; planner-call tokens are not recorded, so the real cost per answer is known only from the Console figure; answers are not deterministic because the Anthropic path sends no `temperature`.

## Agentic workflow

ScholarChain was built with a one-writer agent system: each artifact class has exactly one owning subagent, an orchestrator routes every task, and a human architect holds the phase and ratification gates. The authoritative sources are [AGENTS.md](AGENTS.md) (shared instructions), [CLAUDE.md](CLAUDE.md) (Claude Code project memory), [docs/agents.md](docs/agents.md) (ownership map, lifecycle routing, escalation and human gates), the 18 role files in [.claude/agents/](.claude/agents/), [.claude/settings.json](.claude/settings.json) with its four hooks in [.claude/hooks/](.claude/hooks/), the five commands in [.claude/commands/](.claude/commands/), [.mcp.json](.mcp.json) with its trust notes in [.claude/MCP-TRUST.md](.claude/MCP-TRUST.md), and the per-phase records in [docs/agent-runs/](docs/agent-runs/) (work order `prompt.md`, `owner-report.md`, `review.md`, `test-report.md`, `repairs.md`, `human-gate.md`, accepted commit). This section does not copy them; it points to them.

**Which tool was used.** `AGENTS.md` and `docs/agents.md` state that Codex and Cursor are the student's main tools and that Claude Code is optional and compatible. The `.claude/` files (agent definitions, `settings.json` fences, hooks, commands) take effect only in Claude Code; Codex and Cursor do not register them or enforce them, and no cross-tool equivalence is claimed. The course README specifies a Claude Code orchestrator; the Codex/Cursor-led workflow is a disclosed deviation and no instructor approval of it is claimed here. The tool and model used differ by phase and are stated in each phase's `prompt.md` where recorded. For example, the Phase 2 work order names the models `composer-2.5-fast` (build-engineer) and `grok-4.7-high-fast` (code-reviewer), the Phase 6 work order records Codex with a coordinator identified as GPT-6, and the Phase 13 to 15 work orders record a Claude Code orchestrator. The tool used in every phase is not established by a single record.

Roles in the hub-and-spoke model: the main session is the orchestrator; subagents never invoke one another; a subagent that cannot proceed inside its fence returns `BLOCKED-ON` with evidence and the owner, and the orchestrator routes it ([docs/agents.md](docs/agents.md), "Escalation and gates").

### Agent catalog

One row per submitted subagent (every file in `.claude/agents/`; the names equal the file names and are checked by `.claude/hooks/validate-agent-files.sh`). Owned paths follow the ownership table in [docs/agents.md](docs/agents.md), which is authoritative; each module owner also owns that module's `src/test/**`. The tool fence is the `tools:` line of the agent file. All 18 files set `permissionMode: default` and none sets a `model:` field, so the model is chosen when the orchestrator launches the agent.

**Expected final report.** Every agent returns the same 14 fields (the list in [docs/agent-runs/README.md](docs/agent-runs/README.md), repeated in each agent file's "Report contract"): `STATUS`, `OWNER`, `WORK ORDER`, `FILES CREATED`, `FILES MODIFIED`, `COMMANDS RUN`, `TEST RESULTS`, `VALIDATION RESULTS`, `ASSUMPTIONS`, `RISKS`, `MANUAL ACTION REQUIRED`, `BLOCKED-ON OWNER`, `BLOCKED-ON EVIDENCE`, `NEXT GATE`. `STATUS` is `COMPLETE`, `BLOCKED-ON` or `FAILED`. The last column of Part 2 names what that agent's report must additionally contain in `TEST RESULTS` or `VALIDATION RESULTS`.

**Part 1: purpose, ownership, tool fence, prerequisites**

| Agent | Purpose | Owned artifact paths | Tool fence (`tools:`) | Prerequisites |
|---|---|---|---|---|
| [`factory-engineer`](.claude/agents/factory-engineer.md) | Proposes and validates the agent-control files; never ratifies its own work | `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `docs/agent-runs/README.md`, `.claude/**` except `.claude/.last-test-run`, `.mcp.json` | Read, Grep, Glob, Write, Edit, Bash | Human-approved work order; `bash`, `jq`, Python 3 for the hooks; a change takes effect only after human ratification and a fresh session |
| [`build-engineer`](.claude/agents/build-engineer.md) | Scala 3 sbt build, pinned dependency ledger, packaging, formatter | `build.sbt`, `project/**`, `.scalafmt.conf`, local compose files, packaging files, `.gitignore`, generated marker `.claude/.last-test-run` | Read, Grep, Glob, Write, Edit, Bash | JDK 17 on `JAVA_HOME`; sbt (pinned 1.10.7); first run downloads dependencies |
| [`domain-engineer`](.claude/agents/domain-engineer.md) | Canonical records, stable researcher and work IDs, serialization and configuration contracts | `modules/core/**` | Read, Grep, Glob, Write, Edit, Bash | JDK 17, sbt |
| [`dataset-engineer`](.claude/agents/dataset-engineer.md) | Versions datasets, licenses, schemas, checksums, samples and bounded acquisition scripts | `datasets/**` | Read, Grep, Glob, Write, Edit, Bash | Python 3; PyYAML for `validate_datasets.py` (`datasets/scripts/requirements.txt`); network only for the explicit `--mode refresh` opt-in |
| [`hadoop-engineer`](.claude/agents/hadoop-engineer.md) | Hadoop MapReduce preparation, counters, rejects, coauthor-pair candidates | `modules/hadoop/**` | Read, Grep, Glob, Write, Edit, Bash | JDK 17, sbt; local tests need no AWS; an EMR bounded sample needs the human gate |
| [`entity-resolution-engineer`](.claude/agents/entity-resolution-engineer.md) | Identity blocking, match features, calibration, accepted/rejected/unresolved decisions | `modules/entity-resolution/**` | Read, Grep, Glob, Write, Edit, Bash | JDK 17, sbt |
| [`spark-engineer`](.claude/agents/spark-engineer.md) | Temporal weighted coauthorship graph, metrics, components, communities, bridges, k-core, path evidence | `modules/spark/**` | Read, Grep, Glob, Write, Edit, Bash | JDK 17, sbt (Spark 3.5.4 comes from the build) |
| [`storage-engineer`](.claude/agents/storage-engineer.md) | S3, Neptune, DynamoDB, S3 Vectors and optional OpenSearch adapters and loaders | `modules/storage/**` | Read, Grep, Glob, Write, Edit, Bash | JDK 17, sbt; contract tests are local; a bounded load test touches AWS and needs the human gate |
| [`rag-engineer`](.claude/agents/rag-engineer.md) | Typed query plans, retrieval fusion, evidence bundles, prompts, independent claim verification | `modules/rag/**`, `prompts/runtime/**`, `prompts/schemas/**` | Read, Grep, Glob, Write, Edit, Bash | JDK 17, sbt; the specs use fake HTTP only, no provider key |
| [`service-engineer`](.claude/agents/service-engineer.md) | Versioned REST APIs, typed errors, health checks, runtime composition | `modules/services/**` | Read, Grep, Glob, Write, Edit, Bash | JDK 17, sbt |
| [`test-engineer`](.claude/agents/test-engineer.md) | Independent adversarial, contract, integration and end-to-end tests; no production edits | `tests/**` (a module-local test tree only if a ratified work order designates it; none is designated) | Read, Grep, Glob, Write, Edit, Bash | JDK 17, sbt |
| [`code-reviewer`](.claude/agents/code-reviewer.md) | Independent read-only review of diffs, evidence, ownership and gate results | none (returns review text to the orchestrator) | Read, Grep, Glob | A diff or commit range to review; `validate-agent-files.sh` enforces exactly this fence |
| [`infra-engineer`](.claude/agents/infra-engineer.md) | Authors Terraform and the deployment, smoke, reproduction and cleanup scripts; never applies them | `infra/terraform/**`, `scripts/**`, `.github/workflows/**` | Read, Grep, Glob, Write, Edit, Bash, `mcp__aws-api-readonly__*`, `mcp__terraform-registry__*`, `mcp__aws-knowledge__*` | Terraform exactly 1.13.5, `bash`, `shellcheck`, Python 3; the three MCP servers in the requirements table below |
| [`deploy-engineer`](.claude/agents/deploy-engineer.md) | Executes human-approved release scripts and returns release and smoke evidence; authors nothing | none (returns evidence text to the orchestrator) | Read, Grep, Glob, Bash | Recorded human approval, reviewed plan, clean tree, rollback target (see [.claude/commands/deploy.md](.claude/commands/deploy.md)); no live deployment is part of any reproduction exercise |
| [`experiment-engineer`](.claude/agents/experiment-engineer.md) | Controlled elasticity, quality and cost experiments with raw evidence | `experiments/**`, `load-tests/**` | Read, Grep, Glob, Write, Edit, Bash | Python 3 run as `python3 -I`; an approved budget for any live run |
| [`documentation-engineer`](.claude/agents/documentation-engineer.md) | README, architecture, runbooks, report, diagrams and demo instructions from observed evidence | `README.md`, `docs/**` except `docs/agents.md`, `docs/agent-runs/**`, `docs/incidents/**` | Read, Grep, Glob, Write, Edit, Bash | The evidence it cites must already exist |
| [`incident-responder`](.claude/agents/incident-responder.md) | Diagnoses failures; timelines, impact, bounded recovery | `docs/incidents/**` | Read, Grep, Glob, Write, Edit, Bash | Read-only evidence first; human gate for live recovery, security change, destructive action or rollback |
| [`dependency-updater`](.claude/agents/dependency-updater.md) | Changes approved version values and reports compatibility and vulnerabilities | version values only in `project/Versions.scala` (the dependency ledger) | Read, Grep, Glob, Edit, Bash | JDK 17, sbt; major upgrades need approval |

**Part 2: example instruction, deterministic verification, report fields.** Row N of Part 2 continues row N of Part 1 for the same agent (same order; the agent name is repeated). Run the instruction from the repository root in a fresh Claude Code session, after the human has approved a work order (see step 7 below). "Observed" means the command was run on the author's machine on 2026-11-19 (details in the exercises below); the other commands are the documented gates of that agent and were not re-run for this README.

| Agent | Example orchestrator instruction | Deterministic verification command | Report fields |
|---|---|---|---|
| `factory-engineer` | "Use the factory-engineer agent to propose one added sentence for `.claude/commands/incident.md` as report text only (write nothing) and run `.claude/hooks/validate-agent-files.sh`; do not ratify." | `bash .claude/hooks/validate-agent-files.sh` (observed: exit 0, `Validated 18 unique agents, reviewer fence, 32 representative ownership paths and 18 routes`); `bash scripts/check.sh --only constitution,hooks` (observed: `RESULT: PARTIAL passed=2` and exit status 5 by design, because `--only` skips five gates and a partial run is never a pass; `scripts/check.sh` lines 49 and 77) | All 14 fields (`STATUS` to `NEXT GATE`); `VALIDATION RESULTS`: the validator output line and which checks ran; the ratification decision is left to the human |
| `build-engineer` | "Use the build-engineer agent to run `sbt check` under JDK 17 and report whether `.claude/.last-test-run` was updated; make no source edits." | `sbt check` (JDK 17 required). The archived run at `docs/agent-runs/phase-14/test-report.md` line 582 reads "EXIT 0; 1,415 tests, 0 failed, 1 canceled; 754 s"; not re-run for this README | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt check` exit code, per-module counts, total time, whether the marker was updated |
| `domain-engineer` | "Use the domain-engineer agent to run `sbt core/test` and report the serialization contract test results; edit only `modules/core/**`." | `sbt core/test` (observed: 207 succeeded, 0 failed) | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt core/test` succeeded and failed counts |
| `dataset-engineer` | "Use the dataset-engineer agent to verify the committed samples against `datasets/samples/SHA256SUMS`; do not run any refresh mode." | `cd datasets && shasum -a 256 -c samples/SHA256SUMS` (observed: every listed sample `OK`); `python3 datasets/scripts/validate_datasets.py` needs PyYAML (the system Python on the author's machine reported `PyYAML is required`; the venv recipe is in `datasets/scripts/README.md`) | All 14 fields (`STATUS` to `NEXT GATE`); `VALIDATION RESULTS`: the checksum lines and the manifest validation output |
| `hadoop-engineer` | "Use the hadoop-engineer agent to run `sbt hadoop/test` and report the counter and reject-path results." | `sbt hadoop/test` (not re-run for this README) | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt hadoop/test` counts; counters and rejects of any approved bounded run |
| `entity-resolution-engineer` | "Use the entity-resolution-engineer agent to run `sbt entityResolution/test` and report the match-decision results." | `sbt entityResolution/test` (not re-run for this README) | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt entityResolution/test` counts; gold-set evaluation if run |
| `spark-engineer` | "Use the spark-engineer agent to run `sbt sparkAnalytics/test` and report the known-graph test results; edit only `modules/spark/**`." | `sbt sparkAnalytics/test` (not re-run for this README) | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt sparkAnalytics/test` counts; output invariants of any bounded run |
| `storage-engineer` | "Use the storage-engineer agent to run `sbt storage/test` and report the contract test results; make no live AWS call." | `sbt storage/test` (not re-run for this README) | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt storage/test` counts; a bounded load test only if approved |
| `rag-engineer` | "Use the rag-engineer agent to run `sbt rag/test` and report the prompt-injection and groundedness test results." | `sbt rag/test` (not re-run for this README) | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt rag/test` counts; prompt-injection and groundedness results |
| `service-engineer` | "Use the service-engineer agent to run `sbt services/test` and `bash scripts/smoke-local.sh --build` and report both results." | `sbt services/test`; `bash scripts/smoke-local.sh --build` (observed: exit 0, `RESULT: PASS local offline-synthetic query-api passed all smoke checks`) | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt services/test` counts and the smoke `RESULT:` line |
| `test-engineer` | "Use the test-engineer agent to run `sbt independentTests/test` and report exact pass and fail counts; make no production edits." | `sbt independentTests/test` (not re-run for this README) | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: exact pass and fail counts of `sbt independentTests/test`; defects routed as `BLOCKED-ON` to the owner |
| `code-reviewer` | "Use the code-reviewer agent to review `git diff main..HEAD` for ownership violations and missing tests; report findings with file and line and edit nothing." | No command can prove a review; the checkable parts are the fence (`bash .claude/hooks/validate-agent-files.sh` fails if the tools are not exactly `Read, Grep, Glob`) and that the returned verdict cites file and line; "edited nothing" is checked with `git status --porcelain` (expect no output) | All 14 fields (`STATUS` to `NEXT GATE`); `VALIDATION RESULTS`: findings with file and line, and the verdict; `FILES CREATED` and `FILES MODIFIED` are `none` |
| `infra-engineer` | "Use the infra-engineer agent to run `bash scripts/check.sh --only terraform,shell,python` and report the gate table; do not run `terraform apply`." | `bash scripts/check.sh --only terraform,shell,python` (its `terraform init -backend=false` downloads the pinned provider, so it needs network; not re-run for this README) | All 14 fields (`STATUS` to `NEXT GATE`); `VALIDATION RESULTS`: the gate table lines and the `RESULT:` line; the plan is not applied |
| `deploy-engineer` | "Use the deploy-engineer agent to run `bash scripts/smoke-local.sh --build` and report the result; this is the local analog, not a deployment." A live release additionally needs the recorded approval in [.claude/commands/deploy.md](.claude/commands/deploy.md) | `bash scripts/smoke-local.sh --build` (observed, see `service-engineer`); live gate: approved plan, clean tree, smoke tests and rollback target (none exercised here); `git status --porcelain` expects no output after a read-only or local run | All 14 fields (`STATUS` to `NEXT GATE`); `VALIDATION RESULTS`: release ID, smoke result, rollback target; `FILES CREATED` and `FILES MODIFIED` are `none` |
| `experiment-engineer` | "Use the experiment-engineer agent to run `python3 -I experiments/scripts/check_manifests.py` and report the RESULT line; start no EMR run." | `python3 -I experiments/scripts/check_manifests.py` (observed: `RESULT: OK (placeholders allowed; run with --final before the commit freeze)`); `python3 -I -m unittest discover -s experiments/tests -v` (not re-run) | All 14 fields (`STATUS` to `NEXT GATE`); `VALIDATION RESULTS`: the `RESULT:` line and the raw-evidence location; no invented metrics |
| `documentation-engineer` | "Use the documentation-engineer agent to check every relative link in `README.md` and report the broken ones." | The link check below (observed on this README); no link checker exists as a repository script | All 14 fields (`STATUS` to `NEXT GATE`); `VALIDATION RESULTS`: the link-check output and the commands replayed |
| `incident-responder` | "Use the incident-responder agent to read `docs/incidents/2026-11-16-p0-budget-modify-backup-check.md` and report the timeline and the preventive test it names; read-only, write nothing." | No deterministic command: the gate is human escalation before any live recovery ([.claude/commands/incident.md](.claude/commands/incident.md)); `git status --porcelain` expects no output after the read-only instruction above | All 14 fields (`STATUS` to `NEXT GATE`); `VALIDATION RESULTS`: timeline, root cause, data-integrity assessment and a preventive test; files only under `docs/incidents/` |
| `dependency-updater` | "Use the dependency-updater agent to propose a version-value change for one entry in `project/Versions.scala` and run `sbt check`; make no structural edits." | `sbt check` (not re-run); the vulnerability-review step has no repository command that is known to the author | All 14 fields (`STATUS` to `NEXT GATE`); `TEST RESULTS`: `sbt check` result; the old and new version values |

Link check for this README (Python standard library only; checks that each relative file link exists and ignores web links and in-page anchors; prints `BROKEN` lines, otherwise `links ok`):

```bash
python3 -I - <<'PY'
import re, pathlib
t = pathlib.Path("README.md").read_text()
bad = [m for m in re.findall(r"\]\((?!https?:|#|mailto:)([^)\s#]+)", t) if not pathlib.Path(m).exists()]
print("\n".join("BROKEN " + b for b in bad) or "links ok")
PY
```

### Hooks, commands and MCP servers

- **Hooks** (wired in `.claude/settings.json`; they read the tool request as JSON on stdin and exit 2 to block): `guard-dangerous.sh` (PreToolUse on `Bash|Read|Write|Edit`) blocks secret and credential paths, edits to constitutional files by any agent other than `factory-engineer`, `terraform apply` and `destroy`, force push, S3 and other destructive AWS operations, unreviewed EMR and autoscaling changes, and destructive database statements; `format-scala.sh` (PostToolUse on `Write|Edit`) runs `scalafmtOnly` on a changed `.scala` file and exits 0 for any other file; `validate-agent-files.sh` (PostToolUse) validates the JSON files, the hook scripts, the frontmatter and the 18 names, the reviewer fence and the ownership audit; `verify-tests-ran.sh` (Stop) refuses to finish when source under `modules/**`, `tests/**`, `scripts/**`, `datasets/scripts/**`, `experiments/scripts/**` or `load-tests/**` is newer than the ignored marker `.claude/.last-test-run`, which only a successful `sbt check` writes. `permissions.deny` in the same file additionally denies reads of `.env*`, `secrets/` directories and key files, and the Bash forms of `terraform apply|destroy`, forced pushes and recursive S3 or `delete-*`/`terminate-*` AWS calls. Hooks run only in Claude Code.
- **Commands** (`.claude/commands/`): `/run-pipeline`, `/experiment`, `/deploy`, `/rollback`, `/incident`. Each routes to the owning agent and states its gate (for example `/deploy` requires a recorded human approval, a reviewed plan, a clean tree and a passing `sbt check`).
- **MCP servers** (`.mcp.json`, all read-only or documentation-only; see [.claude/MCP-TRUST.md](.claude/MCP-TRUST.md)): `github-readonly`, `aws-api-readonly`, `terraform-registry`, `aws-knowledge`.

### Reproducing the agentic workflow

#### Version record

Observed on the author's machine on 2026-11-19 with the commands shown, unless the source column names a file. "Pinned" means the repository fixes the value.

| Tool | Value | Source |
|---|---|---|
| Claude Code client | `2.1.329 (Claude Code)` | `claude --version`, observed. The phase records do not state a client version, so the version used for earlier phases is not known. Local Claude settings files such as `.claude/settings.local.json` are per-machine, are not read by this README and are not part of the reproduction |
| Model configuration | The agent files set no `model:` field; the model is chosen at launch. Recorded per phase: **Phase 13** workers `sonnet` (Sonnet 5.5), effort `high`, at the user's request (the default Opus 5.5 high was changed, `phase-13/prompt.md:99`); **Phase 14** workers `sonnet` high (`phase-14/prompt.md:4`); in Phases 13 and 14 no reviewer was launched by the orchestrator and the independent reviews were user-supplied external reviews (`phase-13/prompt.md:62`, `:112`; `phase-14/review.md:137`, `:265`, `:1322`); **Phase 15** workers `opus` (Opus 5.5) high from 2026-11-14 (`phase-15/prompt.md:5`; launches listed at `phase-15/owner-report.md:13-15`, `:383-388`), and from 2026-11-16 the orchestrator launches the `code-reviewer` subagent itself with Opus 5.5 high (`phase-15/prompt.md:167-169`). The human's instruction of 2026-11-16 ("from now on i want you to trigger subagent as sonnet 5.5 high, for the reviewer use opus 5.5 high") changed this. The instruction came in the afternoon of 2026-11-16 (Chicago time); the Work order 3 launches earlier that day (infra-engineer and documentation-engineer on Opus 5.5 high, `docs/agent-runs/phase-15/owner-report.md:1283-1284`) came before it. From the instruction on, in Phases 15, 16 and 17, the coordinator launched every worker on Sonnet 5.5 high and the code-reviewer on Opus 5.5 high, including the 2026-11-19 workers (source of record: the "Model note" in `docs/agent-runs/phase-15/q12-rerun-addendum.md`; also the decision log entry of 2026-11-20T03:19:12Z, `docs/agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md`). The older Phase 15 records name Opus for workers and were not edited. The orchestrator (main session) model is not recorded; the model of any session after the last recorded launch is not recorded | files cited; earlier phases name other models (see "Which tool was used") |
| JVM | JDK 17 is required: `sbt check` and the packaging tasks refuse any other Java version (`project/Java17Guard.scala`). Observed OpenJDK `17.0.20.1` (Homebrew `openjdk@17`) | `$JAVA_HOME/bin/java -version` with `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`. On the same machine the default `java -version` reports OpenJDK 27 and `/usr/libexec/java_home -v 17` found no JDK 17, so `JAVA_HOME` must be set explicitly |
| sbt | Pinned `1.10.7` (`project/build.properties`, `project/Versions.scala`). The installed launcher reported `2.0.10` (`sbt --script-version`); it runs the pinned 1.10.7, as the log line `welcome to sbt 1.10.7 (Homebrew Java 17.0.20.1)` shows | files and command output, observed |
| Scala | Pinned `3.3.4` | `project/Versions.scala` (`scala3`) |
| Other pinned build versions | Spark `3.5.4` (Scala 2.13 artifacts), Hadoop client `3.3.6`, AWS SDK for Java v2 `2.56.0`, scalafmt core `3.8.3`, sbt-assembly `2.3.0` | `project/Versions.scala` |
| Terraform | Pinned exactly `1.13.5`; AWS provider pinned `6.44.0`. Observed `Terraform v1.13.5` | `infra/terraform/versions.tf`; `terraform version` |
| AWS CLI | Not pinned by the repository (no pin found). Observed `aws-cli/2.35.4` | `aws --version` |
| Helper tools | `jq 1.7.1-apple`, `Python 3.14.5`, `GNU bash 3.2.57`, `shellcheck 0.11.0`, `Docker 29.5.3`. `uvx` was not installed. The minimum Python version is not known | `jq --version`, `python3 --version`, `bash --version`, `shellcheck --version`, `docker --version`, `command -v uvx` |

#### External requirements and how to check them

No exercise below needs AWS credentials, an Anthropic or Voyage key, or a cloud resource. Run them in a shell with no AWS variables set, for example: `env -i HOME="$HOME" PATH="$PATH" JAVA_HOME="<jdk17 home>" bash --noprofile --norc -c 'cd <repository root> && <command>'` (replace the three placeholders; `sbt` must be on `PATH`).

| Requirement | Needed by | How to check it is available |
|---|---|---|
| Claude Code (logged in with your own account) | Steps 4 to 11 (the agentic replay). Steps 1 to 3 and the deterministic exercises need no model | `claude --version` prints a version; Claude Code asks for its own login on first start. Nothing is logged in by this repository |
| JDK 17 | `sbt check` and every `sbt <module>/test` | `"$JAVA_HOME/bin/java" -version` reports 17 |
| sbt | all `sbt` commands | `sbt --script-version`; the project's `project/build.properties` selects 1.10.7 |
| `bash`, `jq`, Python 3 | the four hooks and `scripts/` | `jq --version && python3 --version`. A hook that cannot start may fail open in Claude Code ([docs/agents.md](docs/agents.md)), so check them before trusting a probe |
| Terraform 1.13.5 | `infra-engineer`, `scripts/check.sh` terraform gate | `terraform version` reports `v1.13.5` |
| `shellcheck` | `scripts/check.sh` hooks, shell gates | `shellcheck --version` |
| PyYAML (Python package) | `python3 datasets/scripts/validate_datasets.py` (`dataset-engineer`) | `python3 -c "import yaml"` exits 0; otherwise create the virtual environment described in `datasets/scripts/README.md` (`pip install -r datasets/scripts/requirements.txt`) |
| AWS deployer and operator credentials (live, human-gated phases only) | `infra-engineer` plans, `deploy-engineer` and the human's `terraform apply`; **not needed by any exercise here** | The sign-in procedure and the IAM roles are described in [infra/terraform/deployer/README.md](infra/terraform/deployer/README.md) (profile name `scholarchain-deployer`, `aws login`, MFA). Do not run a command that prints the account identity or ID into shared output; a live action also needs the recorded human gate in `docs/agent-runs/phase-NN/` |
| `GITHUB_MCP_AUTHORIZATION` (environment variable name only; its value is the whole header value and includes the `Bearer ` prefix) | MCP server `github-readonly` | `test -n "${GITHUB_MCP_AUTHORIZATION:-}" && echo set` (does not print the value); in a session `/mcp` shows the server status (the shell command `claude mcp list` also works but is optional: it health-checks the servers and may contact them). Optional: the deterministic exercises do not use it |
| `SCHOLARCHAIN_AWS_READONLY_PROFILE` (environment variable name only) and `uvx` | MCP server `aws-api-readonly` (pinned `awslabs.aws-api-mcp-server==1.5.5`) | `command -v uvx` and `aws configure list-profiles` listing the named read-only profile; optional, read access only |
| Docker | MCP server `terraform-registry` (image `hashicorp/terraform-mcp-server:1.3.0`) | `docker --version`; optional |
| Network access to `https://knowledge-mcp.global.api.aws` | MCP server `aws-knowledge` (no authentication) | optional; `/mcp` shows the connection status |
| `CLAUDE_PROJECT_DIR` | the hooks (Claude Code sets it; the hooks fall back to the current directory) | none needed for the exercises |

The MCP servers are used only by `infra-engineer` (the three `mcp__*` entries in its fence); no exercise below depends on them. Whether any MCP server connected in a given session is not recorded by the author for this README: it is not known.

#### The 11 steps for ScholarChain

1. **Clone and check out.** `git clone <repository URL given in the submission> ScholarChain && cd ScholarChain`, then check out the submitted commit. No git tag exists in the repository as of 2026-11-19 (`git tag` was empty), so use `main` at the commit given in the submission. The accepted commit of each phase is in `docs/agent-runs/phase-NN/accepted-commit.md` where that file exists (phases 01 to 04 and 07) and otherwise in the phase's `human-gate.md`.
2. **Install the toolchain.** Install Claude Code (record `claude --version`; the author's value is in the version record), JDK 17, sbt, Terraform 1.13.5, `jq`, Python 3 and `shellcheck` as listed above. Do not use JDK 27 for `sbt check`.
3. **Configure only what is needed.** For the deterministic exercises set `JAVA_HOME` to the JDK 17 home and nothing else. For the optional MCP servers export only `GITHUB_MCP_AUTHORIZATION` (its value includes the `Bearer ` prefix) and `SCHOLARCHAIN_AWS_READONLY_PROFILE` in your shell, never in a file in the repository. `.env`, `*.local.tfvars` and similar private files are git-ignored and are not part of the submission; do not create them for these steps.
4. **Start Claude Code from the repository root** (the directory that holds `CLAUDE.md`) by running `claude` there. Starting elsewhere does not load the project settings.
5. **Confirm what loaded.** In the session run `/memory` (should list `CLAUDE.md`, which imports `AGENTS.md` and `docs/agents.md`), `/agents` (should list the 18 agents of the catalog), `/hooks` (should show the PreToolUse, PostToolUse and Stop entries from `.claude/settings.json`) and `/mcp` (shows the four servers and whether each connected). From a shell, `ls .claude/agents | wc -l` should print `18` (macOS pads the number with leading spaces). The slash-command output was not captured for this README; the deterministic equivalent of the agent and hook check is step 6.
6. **Run the safe validation and the dangerous-command probe** (observed results are in exercise E1): `bash .claude/hooks/validate-agent-files.sh`, then pipe the probe requests into `guard-dangerous.sh` as shown in E1. Then run the seven integration probes in [.claude/PROBES.md](.claude/PROBES.md) in the fresh session (for example probe 1: ask for a `feature-implementer` to edit `build.sbt`; the orchestrator must route it to `build-engineer`; probe 3 proposes the destructive `echo 'terraform destroy'` Bash call, which the hook must reject before it runs). The Phase 1 records state that these Claude Code integration probes were not run at ratification (`docs/agent-runs/phase-01/codex-cursor-probes.md`); this README does not claim a later run, and whether one happened is not established by a record the author can cite.
7. **Replay a phase from its exact work order, one owner at a time.** Replay on a branch from the pre-phase commit, never on `main`, and open a new `claude` session (or run `/clear`) for each owner so no earlier conversation remains. A work order can hold several owner sections: paste only the section of the owner you invoke, together with the checkout line. Phase 3 is the worked example because its record set is complete; `docs/agent-runs/phase-03/prompt.md` has two owner sections.
   - Create the branch at the checkout named in `prompt.md:5`: `git switch -c replay-phase-03 61d1ebdf31e636d502343418ebdd6efdad95e3ed`. Then run `git status --porcelain --untracked-files=all` once and expect empty output as the baseline: leftovers from earlier runs (for example `scripts/lib/__pycache__/` after E2, since the `.gitignore` of that commit has no `__pycache__/` or `*.pyc` rule) would otherwise look like out-of-territory writes in step 8. `git clean -ndx` previews such leftovers without deleting anything; a separate fresh clone used only for the replay avoids the problem.
   - Session A: paste `prompt.md:5` and the `## Domain-engineer` section (`prompt.md:11-13`), and also paste the Phase 3 section ("Phase 3: define contracts, configuration, and dataset manifests") of the course README, because the Domain section says "the immutable Scala 3 records named in the course Phase 3 section" and that text is not in this repository. The course README is the source cited in `docs/agent-runs/phase-01/prompt.md:5` (https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md); its current text may differ from the version used when Phase 3 was originally run. The dataset-related parts of that pasted course section belong to Session B; the domain-engineer must not attempt them. Then instruct: "Use the domain-engineer agent to carry out the work order below. Edit only `modules/core/**` and return the 14-field report." Session A needs Claude Code service access and the course text, and on a cold cache Maven downloads for `sbt`; it needs no AWS and no cloud resource.
   - Session B (separate, fresh): paste `prompt.md:5` and the `## Dataset-engineer` section (`prompt.md:7-9`), then instruct: "Use the dataset-engineer agent to carry out the work order below. Edit only `datasets/**` and return the 14-field report." This section asks for real open datasets and bounded samples acquired from public sources, so Session B needs network access to those sources; skip it for a replay without source access and compare only the core work (the dataset checks in step 10 can still be run on the accepted tree).
   - Do not paste `prompt.md:15-27` (the later human repair orders and the repair delegation). The `/root/phase3_...` names in `prompt.md:23` and `:25` are Codex delegate identifiers from the original run; they are not agents of this repository and are not reproduced. The later review rounds in `review.md` (and the ninth-review follow-up, `test-report.md:82`) are not replayed either; only the first-pass owner work, one reviewer pass (step 8) and the comparison (step 10) are in scope.
   - The replay branch carries the agent files and `CLAUDE.md` of commit `61d1ebd` (the Phase 1 and Phase 2 versions), not those of the current tree, and its README is the old one; keep the current README open for these instructions.
   - The accepted commit of Phase 3 is `52c32063311d0c0eacea69ad311b44132f34f0c4`.
8. **Run the gates the phase record requires.** In Phase 3 the work order names the owners and then a read-only reviewer (`prompt.md:3`); the test gates were run by the coordinator and are recorded in `test-report.md`, so no `test-engineer` agent is needed for this replay. After the owners have returned, first run `git status --porcelain --untracked-files=all` and expect entries only under `modules/core/` and `datasets/`; any other path is a write outside the territory and a failure: record the failure, then commit everything on the replay branch yourself with `git add -A && git commit -m replay-phase-03` (the commit only preserves the evidence, and `..HEAD` then shows every path), then in a fresh session: "Use the code-reviewer agent to review `git diff 61d1ebdf31e636d502343418ebdd6efdad95e3ed..HEAD` for ownership violations, missing tests and unsupported claims; report findings with file and line and edit nothing." Check `git status --porcelain` shows no output afterwards. For a phase whose records include a separate test report from the `test-engineer`, the instruction is: "Use the test-engineer agent to run `sbt independentTests/test` and report exact results." The reviewer has only `Read, Grep, Glob`; no agent approves its own work.
9. **Route `BLOCKED-ON` through the orchestrator.** When an agent returns `STATUS: BLOCKED-ON` with `BLOCKED-ON OWNER` and `BLOCKED-ON EVIDENCE`, the orchestrator sends the finding to the owner named in [docs/agents.md](docs/agents.md) and reruns the blocked agent in a fresh context after the repair. Nobody edits another owner's files directly. Archived examples of routed repairs are in each phase's `repairs.md` (for example `docs/agent-runs/phase-03/repairs.md`).
10. **Compare with the archived evidence.** Wording differs between runs and the model is not deterministic, so a byte-identical diff is not expected. For the Phase 3 replay compare these concrete items with `docs/agent-runs/phase-03/` (`owner-report.md`, `test-report.md`, `review.md`, `human-gate.md`):
    - Territory: `git diff --name-only 61d1ebdf31e636d502343418ebdd6efdad95e3ed..HEAD` lists only paths under `modules/core/` and `datasets/` (nothing else); together with the pre-commit `git status --porcelain --untracked-files=all` listing of step 8 this is the territory evidence. The accepted run for comparison: `git diff --stat 61d1ebdf31e636d502343418ebdd6efdad95e3ed 52c32063311d0c0eacea69ad311b44132f34f0c4 -- modules/core datasets` (observed on 2026-11-19: `67 files changed, 7767 insertions(+)`).
    - Recorded validation at acceptance, quoted from `human-gate.md:11`: "81 core tests, 2 build-verification tests, 6 Python tests, four-dataset manifest validation, and all four sample checksums passed". Reproduce each: `sbt check` under JDK 17 (it reports the core and build-verification counts; `sbt core/test` alone reports the core count), `python3 -B -m unittest discover -s datasets/scripts -p 'test_*.py'` (recorded: 6 tests, `test-report.md:62`), `python3 datasets/scripts/validate_datasets.py` in a virtual environment with PyYAML (recorded: `OK: manifest (4 datasets), samples, and script bounds validated`, `test-report.md:63`), and `cd datasets && shasum -a 256 -c samples/SHA256SUMS` (recorded: four samples). A replay writes its own tests, so its core count may differ from 81; a different count is a difference to explain, not by itself a failure, while any failing test, a path outside the territory, or a missing safety gate is a failure.
    - Reference without a model (observed 2026-11-19 on the accepted commit's `datasets` tree, extracted with `git archive 52c32063311d0c0eacea69ad311b44132f34f0c4 datasets`): the four sample checksums reported `OK`, the unittest command ran `6 tests` and ended `OK` (re-run with `-v`: all six reported `ok`, none skipped; those tests do not import PyYAML, so the system Python without PyYAML was sufficient for them), and `python3 -B datasets/scripts/acquire_samples.py --mode regenerate` printed `verified 4 committed sample(s) against SHA256SUMS`. The Scala side (`sbt check` at the accepted commit) was not re-run.
    - Reviewer: the replayed review returns findings with file and line and a verdict and changes no file; compare its categories with `review.md`, whose rounds end with `STATUS: APPROVE`.
11. **Use a fresh session for the next phase.** Quit `claude` and start a new one (or `/clear`) before replaying another phase, so that the repository state, not stale conversation context, is the starting point. Constitutional changes (`docs/agents.md`, `.claude/**`, `AGENTS.md`, `CLAUDE.md`, `.mcp.json`) take effect only after human ratification and a fresh session; no replay step ratifies anything.

#### Bounded reproduction exercises

None of these rebuilds the cloud environment, creates a cloud resource or needs AWS credentials. Results below were observed on the author's machine on 2026-11-19 with `JAVA_HOME` set to the JDK 17 above and a warm sbt and dependency cache; a cold cache additionally downloads dependencies from Maven Central (not observed).

**E1: agent validation and dangerous-command probes (seconds, no model).**

```bash
# run from the repository root
bash .claude/hooks/validate-agent-files.sh
# observed: exit 0, "Validated 18 unique agents, reviewer fence, 32 representative ownership paths and 18 routes"
printf '%s' '{"tool_name":"Bash","agent_type":"","tool_input":{"command":"echo '\''terraform destroy'\''"}}' | bash .claude/hooks/guard-dangerous.sh; echo "exit=$?"
# observed: "Blocked: terraform apply or destroy. Route this action through the owning agent and recorded human gate." and exit=2
printf '%s' '{"tool_name":"Read","agent_type":"","tool_input":{"file_path":"./.env"}}' | bash .claude/hooks/guard-dangerous.sh; echo "exit=$?"
# observed: "Blocked: secret file or credential path access. ..." and exit=2 (the hook inspects the path text only; it never opens the file)
printf '%s' '{"tool_name":"Edit","agent_type":"service-engineer","tool_input":{"file_path":".claude/settings.json"}}' | bash .claude/hooks/guard-dangerous.sh; echo "exit=$?"
# observed: "Blocked: constitutional file edit by service-engineer; use factory-engineer after human approval. ..." and exit=2
printf '%s' '{"tool_name":"Bash","agent_type":"","tool_input":{"command":"ls modules"}}' | bash .claude/hooks/guard-dangerous.sh; echo "exit=$?"
# observed: no output, exit=0
```

The hook only reads the JSON on stdin and never runs the quoted command. The observed results for the destroy, `.env` and constitutional-edit probes were obtained by supplying the same JSON from a file on stdin (redirected with `<`), not by the inline `printf` pipes shown above; the safe `ls modules` request was also run through the inline form (exit 0), and the inline JSON was checked to parse with `jq`. If you paste a command containing the destroy string into a Claude Code Bash call instead of a plain shell, the same hook rejects the call before it runs, which is probe 3 of `.claude/PROBES.md`.

**E2: module tests, constitution gates and local smoke (seconds when the caches are warm).**

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home   # your JDK 17 home
sbt -batch core/test
# observed: "Tests: succeeded 207, failed 0, canceled 0, ignored 0, pending 0", "All tests passed.", "[success] Total time: 1 s" (warm cache)
bash scripts/check.sh --only constitution,hooks
# observed: "GATE: constitution PASS", "GATE: hooks PASS", "RESULT: PARTIAL passed=2 skipped: shell python terraform script-tests sbt"
# (--only always ends PARTIAL with exit status 5 by design, scripts/check.sh lines 49 and 77; it is never a pass)
(cd datasets && shasum -a 256 -c samples/SHA256SUMS)
# observed: each listed sample "OK" (the shasum lines of the committed samples)
python3 -I experiments/scripts/check_manifests.py
# observed: "CHECK-OK: ..." lines and "RESULT: OK (placeholders allowed; run with --final before the commit freeze)"
bash scripts/smoke-local.sh --build
# observed: smoke checks healthz, readyz, query, evidence, idempotency, error-path, semantic, semantic-cache all "CHECK-OK", then "RESULT: PASS local offline-synthetic query-api ..." and exit 0
```

`scripts/smoke-local.sh` starts the real query-api on loopback in `offline-synthetic` mode with a throwaway key and stops it; nothing leaves the machine. With `--build` it runs `sbt -batch packageServices` first only if the distribution is missing; in the observed run the distribution already existed, so the build time on a fresh clone is not known.

**E3: the full definition of done.** `sbt check` (format check of every module and test tree, compile, all module and independent tests, the build-verification contract tests, the `entityResolution / erJobJarCheck` step, then `markTestRun`; see `checkTask` in `build.sbt`). Archived passing runs are in the phase `test-report.md` files, for example `docs/agent-runs/phase-14/test-report.md` (line 582: "EXIT 0; 1,415 tests, 0 failed, 1 canceled; 754 s"). It was not re-run for this README; expect more than ten minutes. After a successful run the ignored marker `.claude/.last-test-run` is updated, which the Stop hook reads.

**E4: one agentic replay (needs a Claude Code login; model output varies).** For a full phase replay use step 7. For a short routing check, on a new branch in a fresh session, give the orchestrator: "Use the spark-engineer agent to add a comment line to `build.sbt`." The behavior the role file requires is a `BLOCKED-ON` report naming `build-engineer` as the owner with no file changed (`git status --short` empty), in the manner of probe 1 of `.claude/PROBES.md` and as the laws in `.claude/agents/spark-engineer.md` require. Then: "Use the code-reviewer agent to review `git show 52c32063311d0c0eacea69ad311b44132f34f0c4 --stat` for ownership violations" and compare its read-only findings with `docs/agent-runs/phase-03/review.md`. This exercise was not executed by the author for this README; the stated outcomes are what the role files require, not observed results.

#### Limits of this reproduction

The Claude Code integration probes, the slash-command checks in step 5 and the agentic replays in E4 and step 7 were not run while writing this section, so their outcomes are unverified here. The live cloud steps of the project (EMR, ECS, Neptune, provider calls) are not reproduced by any step above; they need the human-gated session recorded in `docs/agent-runs/phase-15/` and the runbooks. The live Anthropic and Voyage calls of the two live sessions and the Q12 runs are recorded, and no Bedrock call is (see "Verification status" above).

## Test data that contains prompt-injection text

Some test fixtures and evaluation data deliberately contain prompt-injection text, for example a sentence that tells the system to disregard its earlier instructions and run a Cypher query (the exact fixture text is in the test files named below) and similar strings inside question, evidence and request fields. They exist so that tests can show the system treats such text as untrusted data and rejects it or leaves it inert: for example `AdversarialRuntimeHttpSpec.scala`, `IndependentRuntime9BEvidenceSpec.scala`, `IndependentRuntime9BSemanticSpec.scala`, `IndependentRuntime9CBenchmarkSpec.scala` and `IndependentOfflineAdjudicationSpec.scala` under `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/`, `modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Runtime9CSpec.scala`, and the `injection` item of `modules/rag/src/main/resources/runtime-benchmark-v1.json`. Copies of such tests also appear in recorded diffs and test logs under `docs/agent-runs/phase-05/`. The listed tests assert that such text is rejected or left inert; the strings are test inputs only.

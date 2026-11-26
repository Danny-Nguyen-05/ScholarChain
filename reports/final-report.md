# ScholarChain final report

Author: Danny Nguyen (cnguye69@uic.edu), individual project, CS 441, University of Illinois Chicago.

Status of this document: written on 2026-11-22 by the documentation-engineer (instance 2, packages 17A-2 and 17F) from committed evidence. Every number has a source link. Where evidence is missing the text says "not recorded" or "GAP". No result was produced or re-run for this report; the only commands replayed for it are listed in [section 25](#25-reproduction-and-cleanup-instructions). The 17G clean-checkout replay ran later; its observed results are in the second table of section 25 and its record is `docs/agent-runs/phase-17/17g-replay.md`. **Phase 18 update (2026-11-26, documentation-engineer):** this report was updated on Day 3 of Phase 18 from the committed Phase 18 records. Where it described the Spark step on EMR as failed, it now states the Phase 18 result and keeps the 2026-11-18 failure as dated history; section 26 collects the Phase 18 facts, and the summary table, sections 6, 9, 15, 16, 20, 21, 23, 24 and 25 and the two tables at the end carry the changes. The tag `v1.0-final` (commit `ad86b07`) is the earlier submission; this version describes branch `phase-18`. Companion documents: [README](../README.md), [docs/architecture.md](../docs/architecture.md), [docs/data-lineage.md](../docs/data-lineage.md), [docs/threat-model.md](../docs/threat-model.md), [docs/service-limits.md](../docs/service-limits.md), [docs/runbook.md](../docs/runbook.md), [docs/api.md](../docs/api.md), [docs/evaluation.md](../docs/evaluation.md), [docs/demo-script.md](../docs/demo-script.md), [reports/release-manifest.md](release-manifest.md), [docs/incidents/README.md](../docs/incidents/README.md).

## Summary of outcome

ScholarChain was built and run end to end on a bounded slice, with several parts proven only in part. The honest status:

| Area | Outcome | Evidence |
|---|---|---|
| Hadoop MapReduce preparation (nine jobs) | Ran on EMR on a 10,577-work DBLP slice; counters summed over the nine jobs: INPUT 290,343, ACCEPTED 515,309, REJECTED 1,243 | [hadoop-prep-counters.txt](../docs/agent-runs/phase-15/evidence/session-2/emr/hadoop-prep-counters.txt) |
| Entity resolution | Ran on EMR; evaluated offline: held-out precision 100.0% (57/57), recall 79.2% (57/72) on 194 binary pairs | [identity-metrics.md](../experiments/results/phase16/identity/identity-metrics.md) |
| Spark graph and metrics on EMR | Session 2 (2026-11-18): **failed**, the `spark-job` step died in its template fetch (`EmrFileSystem` class not found). Phase 18: fixed in `scripts/emr/sc-step.sh`; on 2026-11-25 a size-S run completed all six steps, Spark included (one run, not repeated; the cause is inferred from the ordering change). The first attempt that day failed at `hadoop-prep` (root cause open) and passed on retry | [incident, resolved](../docs/incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md); [hadoop-prep incident, open](../docs/incidents/2026-11-25-emr-hadoop-prep-intermediate-missing.md); [Phase 18 test report](../docs/agent-runs/phase-18/test-report.md); [spark-counters.json](../docs/agent-runs/phase-18/evidence/day2/emr/spark-counters.json) |
| Spark graph (used for everything downstream; the 2026-11-25 EMR export is not used downstream) | Local P6 chain on the same inputs and commit: 78,104 nodes, 100,252 graph edges, 228,715 coauthor edges | [graph-correctness.md](../experiments/results/phase16/graph/graph-correctness.md) |
| Neptune, DynamoDB | Loaded in Session 1 (Neptune 78,104 nodes and 328,967 edges; DynamoDB 166,088 planned cache writes, the cache step completed). In Session 2 Neptune stayed empty and DynamoDB got run-ledger records only (REC12), with no cache reload | [Phase 14 human gate](../docs/agent-runs/phase-14/human-gate.md) (Neptune load); [real-slice-export.md](../docs/agent-runs/phase-14/evidence/14b/replan/real-slice-export.md) (nodes, edges, 166,088 cache writes in the load plan); [Session 1 decision log](../docs/agent-runs/phase-14/evidence/14b/session-1/00-timeline/decision-log.md) (cache step completed) |
| S3 Vectors | 10,000 `voyage-4-lite` vectors (256 dimensions) in Session 2; 104 in Session 1 | [ingest-2.log](../docs/agent-runs/phase-15/evidence/session-2/vectors/ingest-2.log) |
| Runtime answers | 33-question benchmark run twice: 4 of 27 (run-1; 15 were answered) then 23 of 27 (run-2) answer-expected questions passed all three scorer checks | [answer-quality.md](../experiments/results/phase16/answers/answer-quality.md) |
| Elasticity | One AWS load run, **aborted** by a 5xx burst; scale-out seen, scale-in seen at the dashboard | [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) |
| Cost | AWS USD 17.88 to 2026-11-20; combined project report USD 17.96 of USD 25.00 as of 2026-11-20. On the morning of 2026-11-25 the human's screenshots recorded Cost Explorer USD 17.88 (Nov 1-25 view), Anthropic Console USD 0.08 and Voyage USD 0. After the Phase 18 live day, the AWS Budgets console showed USD 19.26 of USD 25.00 at about 9:12 PM CST (not final, a different reading; not summed with the rows above) | [cost-report.log](../docs/agent-runs/phase-15/evidence/session-2/c11/cost-report.log); [decision-log.md](../docs/agent-runs/phase-18/evidence/day2/00-timeline/decision-log.md), lines 6 and 90; [Phase 18 test report](../docs/agent-runs/phase-18/test-report.md), line 127 |
| Not implemented | Optional OpenSearch tier; EMR managed scaling; Bedrock path was authored and tested offline but never run live | [section 23](#23-limitations) |

## 1. Problem and motivation

The question behind the project is who collaborates with whom, how strongly, and how that changes over time, answered from scholarly metadata. A coauthorship graph built from one source is wrong in predictable ways: the same person appears under several names and identifiers, and counts such as "most distinct coauthors" are only trustworthy if identity is resolved first. A language model can write a fluent answer about such a graph, but it can also invent a researcher, a path or a count. ScholarChain therefore separates the work: distributed batch jobs produce the graph and every number; a runtime retrieves evidence from stored results; the model may only choose among claims a deterministic verifier already accepts, and every claim carries evidence IDs that resolve to stored records.

The course framing adds a second goal: the software had to be produced through a controlled agent workflow with one writer per artifact class and human gates, and that workflow is part of what is evaluated.

## 2. Research questions and required metrics

The three collaboration questions the runtime answers, with the metrics the Spark job computes (windows `all-years`, `through-2009`, `2010-2014`, `2015-2019`, `2020-2026`, `since-2015`; [modules/spark/README.md](../modules/spark/README.md)):

1. **Who are a researcher's strongest collaborators, and how broad is their network?** Distinct coauthor count, weighted degree, team-size statistics, direct coauthors with supporting works.
2. **How is the network structured and how does it connect?** Connected components, communities, a bridge measure, k-core, and shortest coauthor paths with the supporting works on every edge.
3. **How does collaboration change over time?** The same metrics per window and the change between the four non-overlapping periods.

The 11 Q12 question types of the benchmark map onto these: bridge, coauthor_breadth, community, component, direct_collab, evidence, institution, max_team_size, shortest_path, temporal, topic ([questions.txt](../experiments/inputs/q12/questions.txt), [answer key](../experiments/inputs/q12/answer-key.json)). The institution and topic types are deliberate abstain tests, because the export has 3 TOPIC nodes and 1 INSTITUTION node ([experiments/README.md](../experiments/README.md)).

## 3. Dataset selection and licenses

The manifest [datasets/dataset-manifest.yaml](../datasets/dataset-manifest.yaml) lists four sources, with licenses and retrieval records:

| Source | Role | License (from the manifest) | Size actually used |
|---|---|---|---|
| DBLP XML, snapshot `dblp-2026-10-03` | seed publications, authors, venues, years | CC0 1.0 (metadata); ODC-BY 1.0 secondary | S slice 10,577 works; L slice 48,187 works (local only) |
| OpenAlex | canonical work and author IDs, authorships with institutions and topics | CC0 1.0 | small committed sample |
| Crossref | DOI-authoritative bibliographic metadata | site CC BY 4.0; metadata largely free of copyright | small committed sample |
| ORCID public registry | researcher identifiers and affiliation evidence | CC0 1.0 public data file; API terms apply | small committed sample |

Committed samples and checksums are in [datasets/samples/SHA256SUMS](../datasets/samples/SHA256SUMS); the DBLP snapshot provenance (Dagstuhl artifact, MD5, upstream size) is in [datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt](../datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt). The S slice is a convenience slice (8 systems venues, 2005-2026, at most 2,500 papers per venue, not random); the L slice adds 25 candidate venues (33 in total) and holds 48,187 inproceedings ([experiments/README.md](../experiments/README.md)). The OpenAlex, Crossref and ORCID inputs were not scaled with the DBLP slices; see [section 23](#23-limitations).

## 4. Agentic software factory architecture

The software was produced by a one-writer agent system: each artifact class has exactly one owning subagent, an orchestrator routes every task, reviewers report findings without editing, and the human architect holds the phase and ratification gates. Authoritative sources: [AGENTS.md](../AGENTS.md), [CLAUDE.md](../CLAUDE.md), [docs/agents.md](../docs/agents.md), the 18 role files in [.claude/agents/](../.claude/agents/), [.claude/settings.json](../.claude/settings.json) with its four hooks in [.claude/hooks/](../.claude/hooks/), the five commands in [.claude/commands/](../.claude/commands/), [.mcp.json](../.mcp.json). The README holds the agent catalog (purpose, owned paths, tool fence, example instruction, verification command and report fields for all 18 agents) and the replay instructions: [Agent catalog](../README.md#agent-catalog) and [Reproducing the agentic workflow](../README.md#reproducing-the-agentic-workflow).

Platform disclosure (also in the README): the course specifies a Claude Code orchestrator. `AGENTS.md` and `docs/agents.md` record that Codex and Cursor were the student's main tools and Claude Code an optional compatible one; the `.claude/` fences and hooks apply only in Claude Code, and no cross-tool equivalence or instructor approval of that deviation is claimed. The tool and model differ by phase and are named in each phase's `prompt.md` where recorded; the README's version record lists what is known (for example workers `sonnet` high in Phases 13 and 14 and `opus` high from 2026-11-14; from the human's instruction in the afternoon of 2026-11-16 (Chicago time; the Work order 3 launches earlier that day were on Opus 5.5 high) the workers of Phases 15 to 17 ran on Sonnet 5.5 high and the code-reviewer on Opus 5.5 high, per the "Model note" in [q12-rerun-addendum.md](../docs/agent-runs/phase-15/q12-rerun-addendum.md) and the [decision log](../docs/agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md), entry of 2026-11-20T03:19:12Z).

## 5. Authority and ownership design

[docs/agents.md](../docs/agents.md) maps every artifact class to one owner (for example `modules/spark/**` to `spark-engineer`, `infra/terraform/**` and `scripts/**` to `infra-engineer`, `README.md` and `docs/**` to `documentation-engineer`). An unlisted artifact is an orphan and stops for a human assignment; two claimed writers are a collision. This happened once in practice in the last phase: the new top-level `reports/` directory had no owner, and the human assigned it to the documentation-engineer on 2026-11-22 ([Phase 17 work order](../docs/agent-runs/phase-17/prompt.md)). The Claude Code `PreToolUse` guard rejects edits to constitutional paths by any agent except `factory-engineer` and blocks Terraform apply or destroy, forced pushes and destructive AWS calls; it only runs in Claude Code, so elsewhere the same rules were followed by process and review ([README, Hooks](../README.md#hooks-commands-and-mcp-servers)).

## 6. Human gates and repair loops

Gates recorded under [docs/agent-runs/](../docs/agent-runs/): each phase has a work order (`prompt.md`), owner reports, an independent review, a test report, repairs and a human-gate decision. The human architect holds the phase gates, and the live sessions, commits and spend were each gated by a recorded decision. Examples with verbatim decisions: the Session 2 approval ([session-2-approval.md](../docs/agent-runs/phase-15/session-2-approval.md)), "A" to recover the runtime-archive upload, "agree: no S retry (deterministic EmrFileSystem error)" (2026-11-18), "go neptune", "A" to accept the aborted load run, "apply P39" (all in the [decision log](../docs/agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md)), and the acceptance of Session 2 on 2026-11-20 ([human-gate.md](../docs/agent-runs/phase-15/human-gate.md)). Phase 18 gates, with the human's answers quoted in [its human gate](../docs/agent-runs/phase-18/human-gate.md): approval of the offline fix ("Approve, commit, push"), of the raised EMR limits ("Raise to 120 min", "Yes, allow 1 retry"), the numbered live gates of 2026-11-25 (gates 1 to 12; most carry a quoted human answer, for example "Approve EMR + run" and, after the first attempt failed, "Retry now"; gate 8 was a coordinator check and gate 9 had no chat answer, see the disclosed gate-order deviation), and the Day 3 redaction decisions.

Measured repair loops (heuristic parse of the phase records, [factory-metrics.md](../experiments/results/phase16/factory/factory-metrics.md)): 38 review units, 8 approved at the first verdict; 65 APPROVE and 62 REQUEST-CHANGES verdict lines; 378 finding lines (62 high severity on the normalised scale); 61 repair-round headings; 27 reports with `STATUS: BLOCKED-ON` and 93 `BLOCKED-ON OWNER` fields naming a role. Phases 1-5 used external reviewers; phases 12-15 used the code-reviewer subagent, so the eras are not comparable.

### What was agent-generated, repaired, edited by hand, or human-authored

The course asks the report to distinguish four classes. The records support these statements, and no more:

| Class | What the records show |
|---|---|
| Agent-generated and accepted without change | 8 of 38 review units were approved at their first verdict ([factory-metrics.md](../experiments/results/phase16/factory/factory-metrics.md)); the heuristic does not list which |
| Agent-generated and repaired by another agent | 61 repair-round headings; each review finding was routed to the owner by the orchestrator and re-reviewed ([repairs.md](../docs/agent-runs/phase-14/repairs.md) is one example) |
| Agent-generated and manually edited, disclosed | Ownership deviations accepted by the human in the Phase 14 gate: edits to `tests/infra/**` in commits `155562d` and `2b2d263`, and to `Dockerfile` and `project/**` in `9ee5bbe` ([Phase 14 human gate](../docs/agent-runs/phase-14/human-gate.md)); the human formatted a private tfvars file by hand on 2026-11-20 ([decision log](../docs/agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md)); the Phase 5 ER labels were drafted by a model and reviewed by one human |
| Human-authored | phase work orders and acceptance criteria; every gate decision; the root-console steps in the live sessions (IAM windows, secret value entry, dashboard reads); ratification; the demo narration (recorded by the human) |

Whether a given source line was edited by hand outside these records is not established by the records.

## 7. Hadoop pipeline

Nine MapReduce jobs (J01 DblpExtract to J09 GraphCandidateExport) turn DBLP XML and OpenAlex, Crossref and ORCID JSONL into domain records. Contracts for each job (input format, reducer, reject codes, output prefix, fixture) are in [modules/hadoop/README.md](../modules/hadoop/README.md). Design points: an XML input format that synchronises on complete top-level records; no combiners, because block size, observation identity and pair expansion are not safe partial aggregates; blocking has a maximum block size, fallback keys and `OVERSIZE_BLOCK` and `OVERSIZE_CANDIDATE_PAIRS` rejects instead of a bigger reducer; rejects are written, not dropped silently.

Evidence on real data: on EMR the Hadoop-prep counters, summed over the nine jobs (`counter-summary.json` sums each counter over the jobs, so ACCEPTED can exceed INPUT), were INPUT 290,343, ACCEPTED 515,309 and REJECTED 1,243, and the Hadoop counters were identical to the local run ([performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md)). Local at size L (48,187 works): 131.8, 137.2 and 141.3 s in three runs, 210 works dropped by the team limit (`OVERSIZE_TEAM`, maximum team 79) ([experiments/README.md](../experiments/README.md)).

## 8. Entity-resolution method and evaluation

Cross-dataset identity is decided per candidate pair on one of five recorded paths: ExactIdentifier, HardConflict, Scored, DeterministicBibliographic or LlmAdjudicated (the last is an optional adjudicator). Candidates come from the Hadoop blocking jobs. The evaluated configuration is the deterministic `er-offline-uncalibrated-v2` with the adjudicator disabled and zero real-provider calls. Module contracts: [modules/entity-resolution/README.md](../modules/entity-resolution/README.md).

Evaluation (200 held-out queued pairs, 194 binary; 40 development pairs; AI-drafted labels reviewed by one human; [identity-metrics.md](../experiments/results/phase16/identity/identity-metrics.md)): TP 57, FP 0, FN 15, TN 122; precision 100.0% (57/57; Wilson 93.7-100.0%), recall 79.2% (57/72; 68.4-86.9%), F1 0.8837, decisive coverage 48.5% (94/194). The ExactIdentifier path is 55/55 by construction of the sample; the Scored path has recall 2/17. No pair took the DeterministicBibliographic or LlmAdjudicated path in the sample. The course asks for at least 200 reviewed pairs: 240 were reviewed (200 held-out of which 194 binary). Limits: convenience strata, a single reviewer, no calibration, no blocking-recall estimate. 15 of 72 true matches were withheld, which is the main negative result of this component.

## 9. Spark graph, metrics, paths, communities, bridges and temporal analytics

[Phase6Main](../modules/spark/README.md) runs eleven distributed jobs over a completed Hadoop export and a completed entity-resolution export, with manifests, hashes and run IDs cross-checked before any write. All graph-sized work stays in DataFrames (no RDD or GraphX, no whole-graph collect). Outputs: canonical nodes and edges, weighted coauthor edges with support works, researcher collaboration metrics, components, communities, bridges, k-core, path evidence and semantic summaries, per time window. Hand-checkable fixtures cover degree, weighted degree, components, shortest paths, community and bridge behaviour (9 tests are named `[small graph]` in the 47-test inventory of 6 suites; [graph-correctness.md](../experiments/results/phase16/graph/graph-correctness.md)).

Measured on the one export used downstream (size S, run `run:ba7402d1-959a-4277-8c6e-e92878a38afa`): 78,104 nodes (RESEARCHER 21,819; WORK 10,578; AUTHOR_MENTION 45,591; VENUE 112; TOPIC 3; INSTITUTION 1), 100,252 graph edges, 228,715 coauthor edges; every coauthor edge is supported by works that both endpoints authored (228715/228715); no dangling edge, no duplicate id. 852 RESEARCHER nodes have no AUTHORED edge (3.9049%). Local timing of the same chain (LOCAL-MAC): Spark job 362.87 s at S; with entity resolution bypassed, 459.84 s at S and 1110.14 s at L (L: 48,188 works, 76,623 researchers, 320,690 all-years coauthor edges, against S 10,578, 21,819 and 81,181). In Session 2 the Spark step did not run on EMR (section 21); after the Phase 18 fix it ran once on EMR on 2026-11-25 (export `run:30b3ef84-11dc-4c8c-b9c2-c632477d7282`: 10,578 canonical works, 21,819 canonical researchers, 81,181 all-years edges, 3,942 components; community detection stopped at its 20-iteration limit without converging; [spark-counters.json](../docs/agent-runs/phase-18/evidence/day2/emr/spark-counters.json)). The works, researchers and all-years edge counts equal those of the local export above; no other comparison of the two exports was made.

## 10. Storage architecture

| Store | Holds | Why this store | Evidence |
|---|---|---|---|
| S3 | raw samples, Hadoop and Spark outputs, the runtime artifact, text pointed to by vectors | cheap, durable, authoritative text store | [modules/storage/README.md](../modules/storage/README.md) |
| Neptune (Serverless, openCypher) | the exact coauthorship graph for path and neighbourhood queries | graph traversal with exact edges | Session 1: 78,104 nodes, 328,967 edges, `LOAD_COMPLETED` ([Phase 14 evidence](../docs/agent-runs/phase-14/evidence/14b/replan/real-slice-export.md)) |
| DynamoDB | run ledger, caches, query sessions | per-key state with provenance of every load and answer | Session 1: 166,088 cache writes ([decision log](../docs/agent-runs/phase-14/evidence/14b/session-1/00-timeline/decision-log.md)) |
| S3 Vectors | five embedding indexes | semantic context with source pointers | section 11 |

Exact counts, weights, components, paths and bridge scores come from Neptune, DynamoDB or Spark outputs, never from vector similarity. Neptune was loaded only in Session 1; in Session 2 it ran empty (it was up for the elasticity window only) because the budget did not allow a reload ([session-2-plan.md](../docs/runbooks/session-2-plan.md), section 8). The runtime also reads one immutable bounded S3 artifact built from the Spark export (default caps 10,000 rows and 16 MiB).

## 11. S3 Vectors and the optional OpenSearch design

Five indexes: `researcher-profile-v1`, `collaboration-community-v1`, `paper-abstract-v1`, `collaboration-path-v1`, `topic-institution-summary-v1`, each holding deterministic Spark summaries rendered to text, not raw abstracts; vector metadata holds filters and an S3 pointer, not long text ([modules/rag/README.md](../modules/rag/README.md)). Embeddings: Voyage AI `voyage-4-lite`, dimension 256. Session 2 ingest 2 wrote 10,000 vectors with 0 rejected at 3.599 vectors/s (2778.273 s): collaboration-community 3,292, collaboration-path 120, paper-abstract 3,292, researcher-profile 3,292, topic-institution-summary 4. Query smoke: 5 of 5 known-item queries returned the expected neighbour, 7 pointers verified ([retrieval-metrics.md](../experiments/results/phase16/retrieval/retrieval-metrics.md)).

**OpenSearch (optional) was not implemented.** A search on 2026-11-22 of `modules/storage/src/main` and `infra/terraform/modules` found no OpenSearch adapter or module; only the agent catalog text mentions it. The index does not exist any more: the stack was destroyed on 2026-11-18.

## 12. Runtime collaboration-analysis agents

The runtime has fixed stages ([prompts/runtime/](../prompts/runtime/), [prompts/schemas/](../prompts/schemas/), [modules/rag/README.md](../modules/rag/README.md)):

1. **Planner** (`planner-v1`): the model turns the untrusted question into an allowlisted typed plan with a tool call; it must not return Cypher, SQL, shell, AWS actions, researcher IDs, counts or scores. Researcher IDs are never accepted from the model.
2. **Retrieval**: graph evidence from the stored artifact and graph service, semantic context from S3 Vectors, combined into one evidence bundle whose items carry evidence IDs.
3. **Synthesis** (`synthesis-v2`, schema `scholarchain.runtime.synthesis.v2`): the input contains a `claimScaffold`, a list of claims the deterministic verifier is known to accept; the model returns only the IDs of the claims it selects and the prose.
4. **Verifier**: independent deterministic check of every claim against the evidence; unsupported claims are rejected or the system abstains with "Insufficient verified evidence".

Models: the Anthropic model `claude-haiku-5-5` (the configured synthesis model id in `ProviderDefaults.scala`) and `voyage-4-lite` for embeddings. The Anthropic path never sends `temperature`, `top_p` or `top_k` (Haiku 5.5 rejects non-default values), so answers are not deterministic. The Bedrock fallback configuration (Haiku 4.5, Titan V2) exists in code and Terraform and was tested offline only ([README, providers](../README.md#model-providers-the-bedrock-restriction-and-the-fallback-configuration)). Why: the course AWS account had a Bedrock quota of 0 for these models, and on 2026-11-09 the instructor approved the Anthropic and Voyage fallback ([provider-fallback.md](../docs/report/provider-fallback.md)). Question text and evidence snippets therefore leave AWS.

## 13. Microservice architecture and API

Four independently deployable services on ECS Fargate behind one HTTPS load balancer: `query-api` (public, API-key authenticated), `graph-service`, `semantic-service` and `embedding-worker` ([modules/services/README.md](../modules/services/README.md)). Public routes include `POST /v1/query`, `GET /v1/evidence/{evidenceId}`, `GET /v1/explain/{queryId}`, `GET /v1/jobs/{jobId}` and `POST /v1/semantic/retrieve`, with typed errors (for example 503 `MODEL_NOT_CONFIGURED` on the local no-key stack, per [modules/services/README.md](../modules/services/README.md)), idempotency keys and health routes. The full route reference is [docs/api.md](../docs/api.md). Why services: the course requires at least three independently deployable services, and separate task definitions let the HTTP services scale between 1 and 2 tasks while the embedding worker stayed at one task ([demo-script.md](../docs/demo-script.md), section 3).

## 14. Terraform architecture

All AWS infrastructure is Terraform (`infra/terraform`, pinned Terraform 1.13.5 and AWS provider 6.44.0) with twelve modules: foundation, network, identity, datalake, dynamodb, neptune, s3vectors, emr, messaging, workflow, runtime and observability, plus a separate `deployer` stack for the deployer and operator roles and permission boundaries ([infra/terraform/README.md](../infra/terraform/README.md)). The root uses a local state file bound to each plan by lineage, serial and sha256. Provider selection (Anthropic and Voyage by default, Bedrock optional) is a variable with guards that refuse inconsistent combinations. Cost-bearing parts (Neptune, EMR, runtime services) are switches that were off until each stage's approval.

Session 2 plans, each saved, reviewed against an expected action list, and applied only after a human approval record that names the plan's sha256 ([decision log](../docs/agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md)): stage-a base 171 adds; recovery plan 0 changes; EMR enable 13 adds; R-b Neptune base 5 adds, 1 change, 12 destroys (the EMR cluster had already ended); runtime 25 adds, 4 changes; cleanup-prepare 20 updates (protection flags). Destroy: pass 1 listed 201 deletes and ended PARTIAL at one forbidden `DisassociateAddress` call (inventory 297 to 65); pass 2 removed the last address (65 to 63). Plan checksums are in [reports/release-manifest.md](release-manifest.md).

## 15. Build, deployment, experiment and reproduction automation

Source-controlled scripts ([scripts/README.md](../scripts/README.md)): `scripts/check.sh` (seven gates: constitution, hooks, shell, python, terraform, script-tests, sbt), `package.sh`, `plan.sh`, `deploy.sh`, `rollback.sh`, `cleanup.sh`, `smoke-test.sh`, `smoke-local.sh`, `run-bounded-pipeline.sh`, `run-experiment.sh` and `archive-evidence.sh`. Each prints `STEP:` markers and one final `RESULT:` line; deploy, rollback and cleanup are dry runs unless a human passes `--execute` with an approval record. The repository definition of done is `sbt check` (JDK 17) with a generated marker that the Claude Code Stop hook reads. The last full check before the first version of this report ran on `main` at `55fb1b3` (`RESULT: PASS gates=7`; per-gate counts in [reports/release-manifest.md](release-manifest.md)). Phase 18 added full checks on branch `phase-18`: runs `20261124T213555Z-18186` and `20261125T013045Z-81496`, each `RESULT: PASS gates=7` ([Phase 18 test report](../docs/agent-runs/phase-18/test-report.md)); On Day 3 (records-only change, `b11afe9`) run `20261126T170301Z-26256` passed six gates and failed the terraform gate (`terraform fmt -check` on two git-ignored local variable files); after a whitespace-only format of those files, `scripts/check.sh --only terraform` run `20261126T190048Z-32280` passed. The two runs together pass all seven gates; no single run passed all seven after the change ([Phase 18 test report](../docs/agent-runs/phase-18/test-report.md), "Day 3").

## 16. Security and threat model

The threat model ([docs/threat-model.md](../docs/threat-model.md)) covers prompt injection, data poisoning, credential exposure, over-permission, denial of service, destructive commands and provenance tampering. Controls with evidence in the records: untrusted text treated as data in prompts and in adversarial tests ([README, injection fixtures](../README.md#test-data-that-contains-prompt-injection-text)); the model cannot supply identities, paths or scores; API keys only in Secrets Manager (empty containers made by Terraform, values entered by hand; the four secrets were force-deleted and both Voyage keys revoked at 22:46:11Z on 2026-11-18, and the Q12 Anthropic key was revoked on 2026-11-21); least-privilege roles with permission boundaries and temporary IAM windows that the human opened and closed (windows of 14:04:38-14:32:48Z with narrow policies to 16:16:32Z, 22:40:31-22:45:28Z and, on 2026-11-19, 18:58:04-19:09:33Z; [Phase 15 human gate](../docs/agent-runs/phase-15/human-gate.md); and in Phase 18 16:37:43Z-16:45:21Z on 2026-11-25 and 02:57:35Z-03:11:50Z on 2026-11-26, [Phase 18 test report](../docs/agent-runs/phase-18/test-report.md), lines 106 and 114); the deployer role was removed by the reviewed P39 procedure (18 resources destroyed on 2026-11-19; the role was created again for Phase 18 and removed again the same way, 18 destroyed, on the evening of 2026-11-25); immutable ECR tags checked against pushed digests; the guard hook and `permissions.deny`. A known inert leftover remains by the human's decision: the inline policy `scholarchain-assume-deployer` on the admin IAM user, which points at a deleted role, to be removed after grading. The IAM windows were not verified in CloudTrail.

## 17. Elasticity experiments

Source: [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md), summarised in [docs/evaluation.md](../docs/evaluation.md). One AWS run `rb-20261118` (semantic route, LLM disabled, empty graph, ECS query-api and semantic-service at 1 to 2 tasks, scaling on ALB requests per target plus CPU 60%): levels 1, 5, 25 and 50 workers with 0 errors, p95 193.556 ms at baseline and 826.71 ms at level-50; **aborted in hold-50** by the load generator's 5xx guard after 67 failed requests (49 x 503, 16 x 504, 2 transport) within 5.5 s; 26,962 requests in total, 0 x 429. Scale-out: poll states [1, 1, 0] at 20:51:54Z, desired 2 at 20:52:55Z, running 2 at 20:53:56Z (task start upper bound 61.0 s); scale-in seen at about 21:09-21:10Z on the dashboard (human reading, not an export). Failure example: stop-task on query-api, recovery to healthy in 113 s and 68 s (two effective events). Not measured: throughput at 2 tasks, a complete hold phase, the cooldown phase, repeats. The 5xx cause is undiagnosed ([incident](../docs/incidents/2026-11-18-rb-load-test-abort-5xx-burst.md)). The size-L and EMR scaling experiments were dropped (section 21).

## 18. Retrieval and answer evaluation

Full tables in [docs/evaluation.md](../docs/evaluation.md). Headline results with their limits:

- Q12 run-1 (commit `ec675d5`) versus run-2 (commit `827fcd5`), 27 answer-expected questions: all three checks passed 4 versus 23 (14.8% versus 85.2%); independent claim re-check 36/36 and 65/65 consistent (0 contradictions); abstentions 6/6 in both runs. They are a before/after pair on different code, one run each.
- The four run-2 failures: q08, q19 and q30 (all community questions) and q14 (HTTP 504). All three community questions failed in both runs.
- Graph-mode ranking retrieval: MRR 0.8333 over 6 scorable ranking questions (0.7143 with the tied-key question counted at 0, a lower bound).
- 16B Session 1 (earlier code, 40 questions): 7/8 component and 7/8 ranking answered; 0/14 direct-coauthor and 0/10 path questions answered.
- Vector-only and fused retrieval: **GAP**, no labelled run exists.

## 19. Agentic factory evaluation

Section 6 gives the counts. The evaluation's own caveats apply: heuristic parsing, whole-phase units for phases 1-4, no per-agent acceptance rate, no log-derived count of guard blocks (the hook writes no persistent log). A hand audit of phase 3 found 14 review events against 11 parsed ([factory-metrics.md](../experiments/results/phase16/factory/factory-metrics.md)).

## 20. Cost analysis

Two ledgers and two Anthropic scopes are reported and not summed across scopes. Project cost report as of 2026-11-20T15:48:56Z ([cost-report.log](../docs/agent-runs/phase-15/evidence/session-2/c11/cost-report.log)):

| Provider | USD | Basis |
|---|---|---|
| AWS | 17.88 | Cost Explorer 2026-11-01..2026-11-20, credits excluded |
| Anthropic | 0.08 | earlier phases only (ledger 0.075075, receipt figure 0.08); no Session 2 use |
| Voyage AI | 0.00 | dashboard, inside the free tokens; R-b window not isolable, unverified |
| Combined | 17.96 | ceiling 25.00, remaining 7.04 |
| Anthropic, Q12 key (separate scope, not in the combined figure) | 0.08 | Anthropic Console, 2026-11-20 and 2026-11-21 UTC, as of 2026-11-21T23:33Z ([docs/report/evaluation.md](../docs/report/evaluation.md), group 4) |

Cost by major experiment (AWS before credits, from the records):

| Experiment | USD | Source |
|---|---|---|
| Session 1 (2026-11-13 to 2026-11-15), whole AWS bill Nov 1-15 | 15.75 as printed (the listed parts are rounded and add to 15.76): Neptune 9.05, ECS 1.78, EC2-Other 1.72, EC2-Instances 0.75, ELB 0.68, Route 53 0.50, VPC 0.46, DynamoDB 0.22, S3 0.22, Secrets Manager 0.15, EMR service fee 0.14, other 0.09 | [Phase 14 human gate](../docs/agent-runs/phase-14/human-gate.md); breakdown in [session-2-plan.md](../docs/runbooks/session-2-plan.md), section 6 |
| Session 2 day, 2026-11-18 | 2.13: Neptune 0.49, EC2-Other 0.44, EC2-Instances 0.28, S3 0.26, DynamoDB 0.19, EFS 0.14, ECS 0.12, VPC 0.06, EMR 0.06, ELB 0.05, Secrets Manager 0.03, KMS 0.01 | [cost-report.log](../docs/agent-runs/phase-15/evidence/session-2/c11/cost-report.log) |
| Session 2 EMR run | 0.37 measured (2377.157 s at USD 0.555/h, including idle time after the failed step) | [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) |
| Session 2 Voyage embeddings | dashboard 0.00; run-report upper bounds 0.23 (ingest 2) and 0.0232 (query smoke) | [Phase 15 human gate](../docs/agent-runs/phase-15/human-gate.md) |
| Q12 and probes (Anthropic) | Console 0.08; token-derived lower bound 0.039535 | [docs/report/evaluation.md](../docs/report/evaluation.md) |
| Phase 18 EMR runs, 2026-11-25 (ledger estimates, not billed amounts) | run 4 (failed at `hadoop-prep`) 0.09; run 5 (passed) 0.51; Day 2 total 0.60; EMR ledger after termination 5 of 5 runs, USD 2.65 of the USD 4.70 cap | [emr-actual-2end.log](../docs/agent-runs/phase-18/evidence/day2/emr/emr-actual-2end.log); [Phase 18 test report](../docs/agent-runs/phase-18/test-report.md), Day 2 |
| AWS Budgets console, 2026-11-25 about 9:12 PM CST | USD 19.26 of USD 25.00 (77.05%), read as root after the live day; the decision log notes +1.38 since the 17.88 reading, "today's spend, not final". Cost Explorer lags, so the final Day 2 AWS figure is not recorded | [decision-log.md](../docs/agent-runs/phase-18/evidence/day2/00-timeline/decision-log.md), line 90 |

Largest cost drivers: Neptune Serverless capacity (USD 9.05 in Session 1, all serverless usage, about 56 NCU-hours over about 32 hours, an average near 1.8 NCU, because the cluster stayed up between steps; [session-2-plan.md](../docs/runbooks/session-2-plan.md), section 6.1a), then ECS, EC2-Other (NAT) and the load balancer. Language-model cost was small (cents). Cost of the AWS load run and cost per request are not recorded (a whole-day, whole-account figure only). The Phase 18 day has no per-service breakdown yet. The decision log records the bills read on 2026-11-25 at 10:21 CST from the human's screenshots and chat: AWS Cost Explorer USD 17.88 (Nov 1-25 view), Anthropic Console USD 0.08 (Nov 20-21) and Voyage USD 0 ([decision-log.md](../docs/agent-runs/phase-18/evidence/day2/00-timeline/decision-log.md), line 6). No combined total was computed for that day, so the combined 17.96 (as of 2026-11-20) is not restated; the newest AWS figure is the Budgets reading above.

## 21. Failures and incident analysis

Index: [docs/incidents/README.md](../docs/incidents/README.md). Records written from committed evidence only (no cloud call):

| Failure | Status | Record |
|---|---|---|
| EMR `spark-job` step: `EmrFileSystem` ClassNotFound on `copyToLocal` (exit 255); human decided no retry (2026-11-18) | open and accepted on 2026-11-20; resolved 2026-11-25 by the Phase 18 fix, verified on EMR in one run | [record](../docs/incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md) |
| EMR `hadoop-prep` step, Phase 18 Day 2 (2026-11-25): job 2 input (job 1 output) not found on the shared mount, `InvalidInputException`; passed on one retry with no change | mitigated by the retry; root cause open | [record](../docs/incidents/2026-11-25-emr-hadoop-prep-intermediate-missing.md) |
| Vector ingest 1: all 10,000 items rejected with HTTP 401, an invalid Voyage key; about 46 minutes lost, nothing written | closed (ingest 2 with a new key) | [record](../docs/incidents/2026-11-18-vectors-ingest-1-voyage-401.md) |
| Runtime-archive upload `RequestTimeout` (321,876,735 bytes) after a clean Terraform apply; recovered with a no-change plan, about 52 minutes | closed | [record](../docs/incidents/2026-11-18-base-apply-runtime-archive-requesttimeout.md) |
| Load test aborted on a 5xx burst (67 failed requests) | open, accepted limitation, cause undiagnosed | [record](../docs/incidents/2026-11-18-rb-load-test-abort-5xx-burst.md) |
| Deployer role-session drops (blank ECS poll lines, profile mix-ups) | closed for the session | [record](../docs/incidents/2026-11-18-deployer-session-drops.md) |
| Console permission gaps (admin profile cannot read secrets, task lists or metrics; deployer lacks several read permissions) | closed for the session | [record](../docs/incidents/2026-11-18-console-permission-gaps.md) |
| Kit omitted the narrow policies for A7, B3b and C5 | follow-up open | [record](../docs/incidents/2026-11-18-kit-missing-a7-b3b-c5-policies.md) |
| P0: budget modify applied, wrapper stopped on its backup check (Phase 14 to 15 transition) | contained | [record](../docs/incidents/2026-11-16-p0-budget-modify-backup-check.md) |

Other dropped or failed items, from the Phase 14 gate: Session 1 EMR was PARTIAL (the Hadoop config was a local path never uploaded; per [docs/evaluation.md](../docs/evaluation.md) the five size-25 runs of 2026-11-14 ended with non-zero exit codes and produced no Hadoop counters), the 15B elasticity runs were dropped for budget, and the first demo video (63 s) showed an account ID and is replaced.

## 22. Threats to validity

Consolidated in [docs/evaluation.md](../docs/evaluation.md), section 6. In short: the answer key, scorer and ER labels come from the same project; samples are convenience samples; the Q12 runs are a before/after pair; local and AWS numbers are not comparable; the graph checks show internal consistency only; planner-token cost and per-service load cost are unrecorded; the factory counts are heuristic.

## 23. Limitations

- **Scale.** The DBLP functional run covers 10,577 works against the course's 100,000; the course instructor's reply approved about 10.5k and about 50k for this project ([session-2-plan.md](../docs/runbooks/session-2-plan.md), section 1b). Graph edges (328,967 loaded; 320,690 at L locally with ER bypassed) are below the 1,000,000 edges the course asks for subject to budget.
- **EMR.** The Spark step failed on EMR on 2026-11-18 and, after the Phase 18 fix, completed once on EMR on 2026-11-25 at size S (one run, not repeated; the fix is inferred from the ordering change, the 2026-11-18 error was not reproduced). The first attempt on 2026-11-25 failed at `hadoop-prep` with an open root cause. The EMR ledger is at 5 of 5 runs, so no further EMR run is possible without a new human decision. The EMR Spark export is not used downstream. EMR was not run at two sizes; L runs only locally and its Spark figures bypass entity resolution (entity resolution ran out of memory at 22 GB after 963.5 s).
- **Elasticity.** One aborted AWS load run on an empty graph with the semantic route only; no result for graph or LLM work under load.
- **Datasets.** OpenAlex, Crossref and ORCID are small committed samples that were not scaled with the DBLP slices, so cross-source resolution at scale is not shown. The runtime ranks only the researchers in its bounded artifact.
- **Neptune and DynamoDB** were loaded and queried in Session 1 only; Session 2 did not reload them.
- **Answers.** Anthropic answers are not deterministic. Community questions failed in both Q12 runs. No human-rated usefulness score exists. 16B Session 1 abstained on all direct-coauthor and path questions.
- **Retrieval.** No labelled vector-only or fused evaluation.
- **Entity resolution.** One reviewer; 15 of 72 held-out true matches withheld; no calibration.
- **Not implemented.** OpenSearch; EMR managed scaling; live Bedrock use.
- **Cleanup (Session 2).** 63 inventory entries remained after cleanup: two free `terraform_data` guards and tagging-index entries that the orchestrator judged to be leftovers of deleted or inactive resources; the state of the second KMS key in the inventory was not read ([inventories](../docs/agent-runs/phase-15/evidence/session-2/inventories/)); several console checks were not made ([Phase 15 human gate](../docs/agent-runs/phase-15/human-gate.md), "Not verified").
- **Cleanup (Phase 18, 2026-11-25).** After the second destroy pass 46 inventory entries remained: 35 ECS task-definition revisions, 7 terminated EMR clusters, the deleted ECS cluster, the KMS key (pending deletion) and 2 Terraform guard records, described in the test report as tag-index records, none billable. Why the inventory fell from 87 to 48 between the two passes is not established (likely tag-index lag). The NAT Elastic IP stayed allocated for about 7.6 hours between the two passes (about USD 0.04 at the AWS list price, which is not repository evidence) ([Phase 18 test report](../docs/agent-runs/phase-18/test-report.md), Day 2).
- **Phase 18 evidence.** The EMR step stderr, step logs and the 468-object Spark export are not in the repository (private or downloaded outside it); the committed evidence is redacted copies and the counters file. Console durations of run 5 come from a screenshot that is not kept.
- **Reproduction.** The 17G fresh-clone replay (fresh clone of `main` at `d1d4fe7`, JDK 17, offline, 2026-11-22) passed `sbt -batch clean check` (1,773 tests succeeded, 0 failed, 2 canceled) but did not cover `scripts/package.sh`, the live AWS steps, the P6 local chain run or query examples against a deployed host; `eval16_repro.py --verify` is partial on a fresh clone (10 pass, 5 scripts skipped for git-ignored inputs). Some Phase 16 tables regenerate only on the author's machine.

## 24. Lessons learned

These are lessons the recorded events support, not general advice.

1. **Check the text, not only the claims.** In Q12 run-1 every verified claim was consistent with the export (36/36), yet only 4 of 27 answer-expected questions passed, because 11 of 15 answers left the rank-1 researcher or coauthor list out of the prose. A claim verifier alone did not catch that.
2. **Do not retry a deterministic failure; fix it, then test the fix.** On 2026-11-18 the `EmrFileSystem` error would have recurred, so the retry was declined and the local export kept the session productive. Phase 18 then changed the script order offline, had it reviewed, and tested it on EMR in one run. The one retry on 2026-11-25 was for a different failure (`hadoop-prep`), taken by a human decision because the cause looked intermittent; that cause is still open, so the retry is not evidence that it is understood.
3. **Bind approvals to plan checksums.** Every mutating stage ran only after a record naming the plan's sha256, which made the mid-session upload recovery (a new no-change plan, a new record serial) safe to review.
4. **An idle serverless database is the largest line.** Neptune was 9.05 of 15.75 in Session 1; keeping it up between steps drove cost, so Session 2 kept it for the elasticity window only and destroyed it first.
5. **Provision the permission kit completely.** The kit omitted three narrow policies, and the admin profile could not read what later checks needed, so steps moved to the root console under recorded human decisions.
6. **Version prompts when they change.** `synthesis-v1` was edited in place during Session 1; the review required a bump to `synthesis-v2` before any later paid answer.
7. **Prefer offline proof before spend.** Every live repair was first tested and reviewed offline; the live sessions still found failures offline checks could not (an invalid pasted key, an EMR class path, a load-time 5xx burst, and in Phase 18 a `hadoop-prep` failure on a shared-mount input path whose cause is still open).
8. **Keep negative results.** The aborted load run, the failed Spark step (kept as dated history after its fix) and the 0/14 and 0/10 answer rates are all in the submission with their causes marked undiagnosed where they are; the open `hadoop-prep` cause is recorded the same way.
9. **Heuristic factory metrics need caveats.** Parsing prose records gave counts, but not per-agent rates or hook-block totals, because the hook keeps no log.

## 25. Reproduction and cleanup instructions

Reproduction: [README](../README.md) (build, test, Terraform plan, deployment path, bounded data run, query examples, cleanup, deliverable index) and [Reproducing the agentic workflow](../README.md#reproducing-the-agentic-workflow). Cloud reproduction needs the human gates in [docs/runbook.md](../docs/runbook.md) and [docs/runbooks/phase-14-live-session.md](../docs/runbooks/phase-14-live-session.md); no live step was repeated for this report and none is needed to read it.

Cleanup: [docs/runbook.md](../docs/runbook.md), `scripts/cleanup.sh` (dry run, `--prepare`, then a confirmed pass bound to a saved plan). The Session 2 cleanup is recorded in the [Phase 15 human gate](../docs/agent-runs/phase-15/human-gate.md) and the [inventories](../docs/agent-runs/phase-15/evidence/session-2/inventories/): 297 entries before, 65 after pass 1, 63 after pass 2. The cleanup script was not rehearsed again in Phase 17A or run in the 17G replay. It was run again in Phase 18 on 2026-11-25: cleanup-prepare, a two-pass destroy (pass 1: 183 deletes listed, 331 to 87 inventory entries, partial at the known Elastic IP 403; pass 2: 48 to 46 entries) and the removal of the operator roles (13) and the deployer role (18 resources), with the human-confirmed final inventory in [the Phase 18 test report](../docs/agent-runs/phase-18/test-report.md) and the logs under [evidence/day2/](../docs/agent-runs/phase-18/evidence/day2/INDEX.md).

Commands replayed for this report (2026-11-22, offline, the author's machine):

| Command | Observed |
|---|---|
| `python3 -I experiments/scripts/eval16_repro.py --verify` | `REGENERATION: PASS pass=24 fail=0 skipped_scripts=0`, exit 0 |
| `(cd datasets && shasum -a 256 -c samples/SHA256SUMS)` | four samples, each `OK` |
| `python3 -I experiments/scripts/check_manifests.py` | `RESULT: OK (placeholders allowed; run with --final before the commit freeze)`; 106 file hashes verified |
| `git log --format=%s \| grep -c '^phase-[0-9]'` | 37 of 151 commit subjects (see the README, "Known repository-history limits") |
| `bash scripts/run-bounded-pipeline.sh --help` | usage text printed (read-only); not a pipeline run |
| `bash scripts/smoke-local.sh --help` | usage text printed (read-only); the smoke run itself was not replayed in 17A (it was replayed in 17G, second table) |
| `sbt clean check`, `scripts/plan.sh`, `scripts/deploy.sh`, `scripts/cleanup.sh`, query examples | not replayed in 17A; see the 17G table below for what was replayed later |

Commands replayed in 17G (2026-11-22, fresh clone of `main` at `d1d4fe7`, JDK 17, offline; record `docs/agent-runs/phase-17/17g-replay.md`, which also holds the full `scripts/check.sh` result on the clone):

| Command | Observed |
|---|---|
| `sbt -batch clean check` | passed: 1,773 tests succeeded, 0 failed, 2 canceled; sbt total time 14:48 |
| `sbt -batch fmt` | tree unchanged (`git status --porcelain` empty) |
| `sbt -batch compile` | success |
| `sbt -batch core/test` | 208 succeeded |
| `sbt -batch packageRelease` | success |
| `(cd datasets && shasum -a 256 -c samples/SHA256SUMS)` | 4 files OK |
| `python3 -I experiments/scripts/check_manifests.py` | `RESULT: OK` |
| `python3 -I experiments/scripts/eval16_repro.py --verify` | `REGENERATION: PARTIAL pass=10 fail=0 skipped_scripts=5`, exit 4: the five skipped scripts (and their tables) need git-ignored local inputs that a fresh clone does not have |
| `bash scripts/plan.sh --env course` | refused: `region required: --region or SCHOLARCHAIN_AWS_REGION`, exit 2 |
| `bash scripts/plan.sh --env course --region us-east-2` | `RESULT: DRY-RUN no aws or terraform command was run and no file was written; re-run with --execute (approval point 4) to plan` |
| `bash scripts/smoke-local.sh --build` | `RESULT: PASS local offline-synthetic query-api passed all smoke checks (the six plus the semantic route and its cache counter) on 127.0.0.1:<port>` |
| `python3 -I scripts/lib/p6_local_chain.py --help` | exit 0 (the chain itself was not run: it needs the pinned runtime archive and the Hadoop client classpath file) |

Not replayed in 17G: `bash scripts/package.sh` (the Docker daemon was not running), the live AWS steps (human-gated, spend), `scripts/deploy.sh`, `scripts/cleanup.sh`, and the query examples (no deployed stack).

## 26. Phase 18 addendum (2026-11-24 to 2026-11-26)

Phase 18 took place after the first submission (`v1.0-final`, commit `ad86b07`). Its goal was the open EMR Spark failure. Sources: the [work order](../docs/agent-runs/phase-18/work-order.md), the [human gate](../docs/agent-runs/phase-18/human-gate.md), the [test report](../docs/agent-runs/phase-18/test-report.md) and the [Day 2 evidence index](../docs/agent-runs/phase-18/evidence/day2/INDEX.md). Facts, in order:

1. **Fix (Day 1, 2026-11-24, offline, package 18A).** In `scripts/emr/sc-step.sh` the `spark-job` step now fetches its template before `spark_env` sets the portable-runtime environment. The diagnosis was a hypothesis from the script order and the two other steps that fetched from S3 on the same cluster; it was written down before the run and not tested against the step's stderr. A regression test fails on the old order. Review round 2: APPROVE; full check `20261124T213555Z-18186`, `RESULT: PASS gates=7` ([test report](../docs/agent-runs/phase-18/test-report.md)).
2. **Limits (package 18B, offline).** Size-S run limit 75 to 120 minutes and USD 0.84 to USD 1.25; EMR ledger caps 4 to 5 live runs and USD 3.53 to USD 4.70 (per run USD 3, unchanged). Full check `20261125T013045Z-81496`, `RESULT: PASS gates=7`. A disclosed finding: the frozen Phase 15 plan totals USD 24.07 with the new EMR allowance, above its floor-2 limit of 23.00 and below the firm 25.00 ceiling (a finding, not a gate).
3. **Live proof (Day 2, 2026-11-25).** The official extension of the deadline to 2026-11-30, 8:00 PM CST is recorded in the human gate. The first S attempt (run 4) failed at `hadoop-prep` (job 2 could not find job 1's output on the shared mount; [incident](../docs/incidents/2026-11-25-emr-hadoop-prep-intermediate-missing.md), root cause not determined). After the human's "Retry now", run 5 (`15a-emr-size-100-20261125T174034Z-99560`) completed stage-in, hadoop-prep, entity-resolution, spark-class-origin, spark-job and copy-out ([emr-run-2.log](../docs/agent-runs/phase-18/evidence/day2/emr/emr-run-2.log)). That proves the fix on EMR in one run. The cause of the 2026-11-18 error stays inferred, because it was not reproduced.
4. **Result of the Spark step.** Counters of `run:30b3ef84-11dc-4c8c-b9c2-c632477d7282` ([spark-counters.json](../docs/agent-runs/phase-18/evidence/day2/emr/spark-counters.json)): canonicalWorks 10,578; canonicalResearchers 21,819; allYearsEdges 81,181; components 3,942; crossCommunityEdges 17,589; communityIterations 20 with the community step not converged. Console step durations of run 5: hadoop-prep 7m6s, entity-resolution 6m2s, spark-job 16m38s (screenshot, not kept).
5. **Ledger and cost.** After the cluster ended: 5 of 5 live runs, USD 2.65 of the USD 4.70 cap ([emr-actual-2end.log](../docs/agent-runs/phase-18/evidence/day2/emr/emr-actual-2end.log)), ledger estimates. No further EMR run is possible without a new human decision. The AWS Budgets console showed USD 19.26 of USD 25.00 at about 9:12 PM CST on 2026-11-25 (not final).
6. **Cleanup.** The stack was destroyed in two passes, the 13 operator-role resources and then the deployer role with 18 resources were removed (IAM window 2 closed at 03:11:50Z on 2026-11-26), and the human confirmed the final inventory (nothing billable; KMS key pending deletion). Two gate-order deviations are disclosed in the human gate: the cleanup-prepare run had no chat yes (the human's own approval record stands) and the P39 yes arrived in the same message as the pasted apply output. The Phase 18 Day 1 work ran in the Phase 17 coordinator session, a disclosed deviation from the fresh-session rule, with the human's agreement ([human gate](../docs/agent-runs/phase-18/human-gate.md), 2026-11-24, 1:30 PM).
7. **Day 3 (2026-11-26, records only).** A secret scanner flagged a used one-time destroy confirmation token in a committed Phase 18 listing. These tokens are not credentials. The human approved redacting the two Day 2 values and, as a one-time exception to the rule against editing historical Phase 15 records, the two used tokens in one Phase 15 session-2 file; the values remain in git history. The Phase 16 reproducibility evidence and the manifest hashes that followed from that edit were regenerated by the experiment-engineer ([human gate](../docs/agent-runs/phase-18/human-gate.md), Day 3). No AWS step was taken on Day 3.

Limits of the Phase 18 result: one successful run; the `hadoop-prep` cause open; size L still not run on EMR; the evaluation tables, stores and answer key are unchanged and still derive from the local export; the factory metrics of section 6 were not recomputed to include Phases 16 to 18.

## Contribution table

Individual project; the human author is Danny Nguyen. Agents are tools under the one-writer map and are not co-authors.

| Area | Human | Agents (owner) | Record |
|---|---|---|---|
| Architecture | intent, scope, approvals of the reduced scale | factory, domain, infra, spark, storage, rag and service engineers proposed designs in work orders | [docs/agent-runs/](../docs/agent-runs/) |
| Prompting | wrote or approved every phase work order | runtime prompts by the rag-engineer (`prompts/runtime/**`) | each phase `prompt.md`; [prompts/](../prompts/) |
| Ratification | recorded approval of the Phase 1 control plane and of each phase at its gate | factory-engineer proposed | [phase-01 human gate](../docs/agent-runs/phase-01/human-gate.md) and each phase `human-gate.md` |
| Implementation review | reviewed diffs at each gate | code-reviewer, external reviewers (phases 1-5, 13-14) | each phase `review.md` |
| Datasets | selected scope and slice size | dataset-engineer | [datasets/](../datasets/) |
| Experiments | approved budget and each live action, performed the console steps of the live sessions | experiment-engineer, test-engineer | [experiments/](../experiments/), [phase-16](../docs/agent-runs/phase-16/) |
| Documentation | reviews and accepts | documentation-engineer | this report and the documents listed at the top |
| Demonstration | records the clips and narrates the video; uploads it | documentation-engineer drafted the script; an agent edited the clips at the human's request (silence cuts, 1.2x speech, title labels and provenance captions); the coordinator added six correction captions and the item 6 owner-report clip after reviews by a separate agent session (pasted in chat, not stored in the repository) | [docs/demo-script.md](../docs/demo-script.md) |

## Scale table (Phase 17 report template, P28)

Template: [session-2-plan.md](../docs/runbooks/session-2-plan.md), section 8. One row per scaled item. Values are from the evidence named; "not recorded" marks a gap. All times are seconds unless stated.

| Item | Original requirement (course) | Actual size | Reason for reduction | Cost | Execution time | Limitations | Fixture or real |
|---|---|---|---|---|---|---|---|
| DBLP integrated functional run | at least 100,000 DBLP works; approved for ScholarChain: about 10.5k and about 50k | 10,577 works (S). Session 1: local Hadoop, ER and Spark, loaded into Neptune, DynamoDB and S3 Vectors, API answers. Session 2: Hadoop and ER on EMR; Spark export taken from the local chain; about 10,000 vectors | approved reduction; USD 25 firm | Session 1 AWS 15.75 (Nov 1-15); Session 2 day 2.13 | local chain: Hadoop 36.73, ER 96.7, Spark 362.87; EMR upper bounds (Session 2): stage-in 32.0, hadoop-prep 490.0, ER 368.0, spark-class-origin 62.0; Phase 18 run 5 (console): hadoop-prep 7m6s, entity-resolution 6m2s, spark-job 16m38s | convenience slice; other sources tiny; no Session 2 graph reload; EMR Spark step failed in Session 2 and completed once in Phase 18 (the loaded graph is still the local export) | real (DBLP `dblp-2026-10-03`, CC0); other sources real but tiny |
| EMR scale measurement (two sizes) | measurements at several sizes; approved S and L | S = 10,577 works on EMR (Session 2: Spark step failed; Phase 18, 2026-11-25: all six steps completed in one run, 10,578 canonical works in the Spark counters). L (48,187 works) dropped on EMR; local: Hadoop 131.8 / 137.2 / 141.3, 210 works dropped by team limit, max team 79; ER out of memory at 22 GB after 963.5; Spark with ER bypassed 1110.14 at L against 459.84 at S | ER memory; approved reduction | Session 2 EMR run 0.37 measured (2377.157 s at USD 0.555/h); EMR ledger 2.05 of 3.53 cumulative after Session 2; after Phase 18, 2.65 of 4.70 (5 of 5 runs; Phase 18 run 5 measured 0.51, run 4 0.09, ledger estimates) | per-step values above | one size on EMR, and its Spark step completed in one run only; L figures bypass ER and are local only; 5-minute metric granularity | real (L Spark bypasses ER) |
| Graph edges in the scale experiment | at least 1,000,000 edges, subject to budget | 328,967 at 10,577 works (100,252 graph + 228,715 coauthor); L local, ER bypassed: 320,690 all-years coauthor edges at 48,188 works (S bypassed: 81,181) | budget; L not loaded | in the EMR and Session 1 rows | local Spark times above | L not loaded into any store; below the 1,000,000 target | real (ER bypassed at L) |
| Neptune graph | store the processed graph | Session 1: 78,104 nodes, 328,967 edges, `LOAD_COMPLETED`. Session 2: up empty for the elasticity window | not reloaded: USD 25 firm | Session 1 9.05; Session 2 day 0.49 | Session 1 graph-only load 3,540 | not queried live in Session 2 | real (Session 1) |
| DynamoDB items | operational records, caches, run ledger | Session 1: 166,088 cache writes plus run-ledger records. Session 2: run-ledger records only (a RUN item `complete` with 10,001 records, per the decision log) | no cache reload (budget) | Session 1 0.22; Session 2 day 0.19 | about 2 hours (Session 1, per the plan template) | Session 2 shows a ledger record, not the cache | real |
| ER gold set | at least 200 manually reviewed pairs | 240 reviewed (40 development, 200 held-out; held-out 194 binary + 6 uncertain; 181 binary without 22 assisted) | none | 0 (offline) | offline | AI-assisted labels, one reviewer; 0 FP observed; recall 79.2% (57/72) | real records, human-reviewed labels |
| S3 Vectors | at least 10,000 chunks; approved: up to 10,000 real vectors | Session 1: 104 (25/25/25/25/4). Session 2: 10,000 (3,292 / 3,292 / 3,292 / 120 / 4), 0 rejected | approved | Voyage 0.00 on the dashboard; run-report bounds 0.23 and 0.0232 | 2778.273 s (3.599 vectors/s) | deterministic Spark summaries, not raw abstracts | real (derived from the S export) |
| Vector retrieval | ingestion and retrieval demonstrated | Session 2 query smoke: 5 of 5 known-item queries, 7 pointers verified; SDK call times 351.009, 166.084, 364.769, 307.769, 91.162 ms | none | included above | as stated | stored texts used as queries; n = 5; no API-level semantic answers in Session 2 | real |
| 16B benchmark | at least 30 questions across 11 topics | Session 1: 40 asked (component 7/8, ranking 7/8, direct coauthors 0/14, path 0/10). Q12 (local loopback, live model): 33 questions x 2 runs plus 2 probes | Session 2 R-c dropped for budget; Q12 ran later on the local stack | Anthropic Session 1: 16B run-record estimate 0.054600; Q12 Console 0.08 | Session 1 about 3 minutes; Q12 run-1 2026-11-20T21:34:35.759Z to 21:36:40.865Z, run-2 2026-11-21T17:08:30.609Z to 17:11:05.721Z | four question kinds in 16B; ranking over included researchers only; Q12 is one run per code version | real (Session 1 on AWS; Q12 on the local stack) |
| Elasticity | at least four concurrency levels; one scale-out and one scale-in | levels 1/5/25/50 then hold-50; run aborted in hold-50; scale-out seen (poll brackets), scale-in seen on the dashboard (about 21:09-21:10Z) | USD 25 firm; semantic route only | included in the Session 2 day (not isolable) | 2026-11-18T20:43:32.897Z to 20:52:54.484Z | empty graph; no LLM or graph work under load; cooldown skipped; 67 failed requests | real deployment and vectors; synthetic request mix |
| EMR cluster size | burst or managed scaling in the plan | 1 primary r5.xlarge + 1 core m5.xlarge, no task nodes, no managed scaling | cost | in the EMR row | in the EMR row | no capacity change shown | not applicable |
| LLM answers | bounded by budget | Session 1: 55 answers (`claude-haiku-5-5`). Q12: 2 runs of 33 plus 2 probes | budget | Session 1 ledger 0.075075; Q12 Console 0.08 | Q12 p50 3002.443 and 3396.397 ms | no temperature 0 on the Anthropic path | real |
| Not evaluated because of resource limits | n/a | live graph load at S in Session 2; live API answers on AWS in Session 2; coauthor and path reruns on AWS; elasticity of the graph and LLM paths; EMR managed scaling; L on EMR; loading L into any store; a repeat of the Phase 18 EMR run (the ledger is at 5 of 5) | USD 25 firm (a budget raise was declined) | not applicable | not applicable | Session 1 covers graph load and answers at 10,577 works | not applicable |

## Fixture versus real

What ran on fixtures and what ran on real data, stated in one place so no result is read across the line.

| Item | Fixture | Real |
|---|---|---|
| Unit and contract tests (all modules) | hand-derived synthetic fixtures, fake HTTP servers, stubbed SDKs; Spark known-graph fixtures | not applicable |
| Committed dataset samples | three DBLP records, tiny OpenAlex, Crossref and ORCID samples (checksums in [SHA256SUMS](../datasets/samples/SHA256SUMS)) | the same sources at larger size only through the acquisition scripts |
| Hadoop, ER and Spark runs | sample-path test runs | the 10,577-work DBLP slice (S) on EMR (Hadoop and ER in Session 2; all three, Spark included, in one Phase 18 run) and locally (all three); L locally for Hadoop and bypassed Spark |
| Graph correctness evaluation | none | one real size-S Spark export |
| `scripts/smoke-local.sh` | the real query-api in `offline-synthetic` mode with a throwaway key; the question "Synthetic fixture: publication count for A"; no cloud service contacted | none |
| P35 local rehearsal (LOCAL-LOOPBACK-DOCKER) | offline-synthetic query-api at 0.25 vCPU; not an AWS number | none |
| AWS load run `rb-20261118` | synthetic request mix (fixed set of real topic questions), empty graph | real deployment, real 10,000 vectors in S3 Vectors |
| Q12 benchmark | none | live model, real export (loopback stack, not AWS) |
| 16B Session 1 | none | AWS deployment, live model, real graph (Session 1 artifact) |
| ER evaluation | none | real record pairs, labels AI-drafted and reviewed by one human |
| Bedrock configuration | tested with fake HTTP only | never run |
| Demo video | local fixture run for the API clip is allowed by the demo script | live clips from Session 2 and Q12 are real; stack destroyed afterwards |

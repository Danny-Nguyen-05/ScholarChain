# ScholarChain Phase 5 work order — authorized Subphase 5A

## User authorization and refinements — 2026-10-15

The user supplied `/Users/danny/Documents/plan/phase5.md` and authorized only Subphase 5A after a read-only project/planning discussion. Their implementation authorization is reproduced verbatim:

> 1. Use a computer-science sample focused on distributed systems/data engineering. Choose sources and years that provide enough repeated authors, difficult negatives, and independent evaluation groups.
>
> 2. Aim for 240 reviews: 40 development and 200 held out. Report if uncertain labels require additional reviews.
>
> 3. Plan around the repository’s existing material. I’ll provide paths if I have additional datasets; don’t assume any exist.
>
> Resolve the technical contract details through the appropriate owners during 5A, including the entity-resolution owner.
>
> Proceed with 5A only. When ready, give me the reviewer prompt and stop for my review.
> Any push back or suggestions or any other questions?

These refinements supersede the original plan's proposed 40/160 allocation. No source acquisition, human labeling, paid/model call, commit, push, Phase 5B, or later phase is authorized by this checkpoint. A modest reserve candidate supply is a planning recommendation, not manufactured human evidence or an unapproved expansion of review work.

## Execution context and evidence ownership

- Coordinator: `/root`, native Codex runtime; specialist roles are explicitly launched native subagents, not automatically registered Claude agents. Four total active slots: coordinator plus at most three specialists. No specialist may delegate.
- Starting branch `main`, HEAD `099e303311be7a1b2e2cf5655e0c7ce9fa710474`; tracked/untracked status was empty before launching workers. Phase 4 implementation base `3ccd61c071d8080dda04d5e9cf73e9ed19dd75a7` has recorded human acceptance; no Phase 5 acceptance is inferred.
- Domain owner: `/root/phase5a_domain`, modules/core/**. Inventory/proposal first; additive shared contracts only after ER agreement.
- Build owner: `/root/phase5a_build`, build.sbt/project/**/.gitignore. Minimal independent-test wiring; no incidental upgrades.
- Dataset inventory owner: `/root/phase5a_dataset`, read-only inventory and future bounded-acquisition design; any necessary authored readiness artifact restricted to datasets/**. Expanded acquisition is 5C.
- Entity-resolution owner: joins when a slot is free, owns modules/entity-resolution/**. 5A contract/config/label/policy examples and interface agreement only; no matching/provider/review-tool/evaluator implementation.
- Coordinator alone writes docs/agent-runs/phase-05/**, records observed evidence and produces external reviewer prompt. Human decisions/labels are never authored by implementation workers.
- A single serialized sbt gate will run against a frozen tree. Workers report exact observed commands and unrun verification honestly.
- Independent code-reviewer is user-selected and user-run. Coordinator will never launch or impersonate it.

The read-only pre-implementation pass found two details to make explicit in 5A: UTC decision timestamps and LLM-reported confidence separate from calibrated system confidence, as required by the authoritative course entity-linkage policy. ORCID activities/profile observations must not be treated as full publication author lists or all converted to work endpoints. Preserve Phase 3/4 wire formats, IDs and closed prep-features-v2 vocabulary.

## Original external plan (complete, verbatim)

# ScholarChain Phase 5 — implementation and handoff plan

Prepared: 2026-10-15. Intended reader: a fresh manager/orchestrator agent in Codex or Cursor.

## 1. Your assignment

Implement Phase 5, entity resolution, in `/Users/danny/Documents/UIC/CS441/ScholarChain`. Act as the coordinator: explicitly launch specialist subagents using your tool's native delegation capability, give each a bounded work order, route dependencies and repairs, collect observed evidence, and prepare independent review handoffs for the user. **Do not launch, invoke or auto-select a code-reviewer yourself.** The user will copy your generated prompt into their preferred reviewer and bring its verdict back. Do not implement specialist production code yourself. Subagents must not launch more subagents.

The user primarily uses Codex and Cursor. Preserve the existing Claude compatibility files. The `.claude/agents/*.md` files describe the roles and their fences; reading them does not register native agents or enforce permissions in another tool. Use the corresponding role instructions when launching each native subagent. If delegation is unavailable, report that limitation and request a tool/session that supports it; do not claim delegation occurred.

This document is an implementation work order, not proof of human acceptance, instructor approval, a completed evaluation, or permission to spend money. After preflight, implement **Subphase 5A only**. Follow the mandatory stop-and-review protocol in Section 14: complete one subphase, hand it back to the user, and wait for explicit authorization before starting the next. Do not execute all five subphases in one uninterrupted run.

## 2. Project context and verified starting point

ScholarChain links scholarly datasets, resolves researcher and work identities, and eventually builds a temporal coauthorship graph with Spark, AWS storage, and evidence-backed retrieval. Incorrect identity merges damage every downstream graph metric.

Completed work:

- Phases 0–1 established the project and agent workflow.
- Phase 2 established the Scala multi-project build, formatting, tests, and packaging.
- Phase 3 introduced datasets, shared records, stable IDs, configuration, serialization, and validation.
- Phase 4 implemented nine Hadoop MapReduce preparation jobs: extract/normalize, identifier index/join, blocking/candidates, publication teams, coauthor pairs, and export.
- Phase 4 is accepted. The recorded implementation commit is `3ccd61c071d8080dda04d5e9cf73e9ed19dd75a7`. The acceptance-evidence commit and observed HEAD when this plan was prepared is `099e303311be7a1b2e2cf5655e0c7ce9fa710474`.
- The working tree was clean when inspected for this plan. Recheck; do not reset another person's changes.
- Phase 4's recorded final evidence is 220 passing tests, verified current-core packaging contents, and two fresh logically equivalent sample runs. This is historical evidence, not a new test run for Phase 5.
- The committed portfolio is DBLP, OpenAlex, Crossref, and ORCID. Existing samples are deliberately tiny; they do not establish a sufficient evaluation population.
- `modules/entity-resolution/` currently has placeholder source/test roots. The sbt project ID is `entityResolution`; it depends on `core`.
- `independentTests` currently depends on `core` and `hadoop`; build-owner wiring is needed to test entity resolution independently.

Toolchain recorded by Phase 4: Java 17.0.20.1, Scala 3.3.4, sbt 1.10.7, Hadoop 3.3.6. Current pins include uPickle 4.0.2 and ScalaTest 3.2.19. Prefer the existing dependencies and Java 17. Do not upgrade the stack incidentally.

## 3. Source of authority and required reading

Read these before delegating or editing, and check for applicable nested `AGENTS.md` instructions:

1. Root `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`.
2. `docs/agent-runs/README.md`; the Phase 1 human decision for authority context.
3. Each assigned role's `.claude/agents/<role>.md`.
4. Phase 3 reports and relevant core contracts/tests.
5. `modules/hadoop/README.md`, Phase 4's current owner/test reports and final review, `human-gate.md`, and `accepted-commit.md`. Earlier REQUEST-CHANGES sections are historical; inspect the final disposition.
6. `build.sbt`, `project/ScholarChainBuild.scala`, `project/Dependencies.scala`, `project/Versions.scala`, `.gitignore`.
7. `datasets/dataset-manifest.yaml`, `datasets/acquisition-index.v1.json`, schemas, licenses, acquisition/validation scripts.
8. The authoritative course [Phase 5 specification](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-5-implement-entity-resolution). Also read the entity-resolution detail, evaluation, deliverable D07, and relevant Phase 6 input expectations. Resolve a material mismatch explicitly rather than silently changing scope.

Course requirements, summarized: resolve identity with exact IDs, normalized text, evidence features, versioned scoring and thresholds; preserve identifier conflicts and uncertainty; restrict LLM adjudication to bounded uncertain cases, with validated accept/reject/abstain JSON and versioned caching; emit all four decision outcomes and a human review queue. Cover DOI, arXiv, ORCID, OpenAlex, Semantic Scholar, and repository URLs. Evaluate at least 200 manually reviewed pairs with precision, recall, F1, confusion matrix, coverage, results by entity type and matching path, threshold sensitivity, and representative errors (ten false positives/negatives when available). Run `sbt check` and gold-set evaluation. Prevent evaluation-label leakage. [Source: course README](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-5-implement-entity-resolution).

The concrete design and sequencing below are proposed engineering choices for this repository. They are not additional claims about what the course text explicitly specifies.

## 4. Decisions already agreed with the user

- Build the complete matching subsystem and a **local human review tool**.
- Develop and test LLM behavior using simulated responses first; live calls are disabled by default.
- Include a real-provider integration stage for uncertain matches, with a small explicitly authorized budget. Provider/model and numerical limits are not selected yet. Ask once the adapter, tests, and representative request are ready.
- The coding agent's own reasoning during development is not the deployed program's LLM integration and is not human evaluation evidence.
- The user reviews at least 200 distinct real candidate pairs. Never fabricate labels, mark agent-generated labels as human-reviewed, or automate clicks to manufacture that evidence.
- Deliver the runnable review tool and queue before asking for labeling. Work only within the currently authorized subphase. At every subphase boundary, stop for user review; while labels or other human input are pending, do not advance to another subphase without explicit authorization. Phase acceptance remains pending until missing human/live-model/evaluation gates are genuinely satisfied.
- No AWS setup, Terraform apply, EMR provisioning, deployment, full dataset download, or later-phase implementation is needed for this work order. Local code does not require cloud infrastructure.
- Do not commit or push unless the user separately requests it. Do not start Phase 6.

## 5. Delegation and ownership

Launch actual agents only for the currently authorized subphase; record their native IDs, assigned paths, scope, dependencies, and handoffs. Use available native models; no specific model is required by this plan. Respect concurrency limits and keep one active writer per artifact class. Run one full sbt gate at a time against a stable tree. The role table describes eventual participation, not permission to start later-subphase work early.

| Role | Assignment and owned files | When |
|---|---|---|
| `domain-engineer` | `modules/core/**`: review shared contracts; implement only necessary additive shared types/validators and their local tests | First; return a contract inventory and gap decision |
| `build-engineer` | `build.sbt`, `project/**`, `.gitignore`: independent-test wiring, commands/dependencies if needed, ignore rules | First; coordinate APIs with owners |
| `entity-resolution-engineer` | `modules/entity-resolution/**`: matching, policy/config, provider adapters, module-local prompt/schema resources, review page, CLI, evaluator, module tests and README | Primary implementation, after interface agreement |
| `dataset-engineer` | `datasets/**`: bounded real evaluation population, acquisition provenance, manifests/licenses, review-queue inputs, validation | Start early; dataset sufficiency is a real dependency |
| `test-engineer` | `tests/**`: independent adversarial/integration/evaluator checks, including review UI tests | After initial interfaces; runs the integrated gate when the tree is frozen |
| `code-reviewer` (user-selected external agent) | Independent read-only review text returned by the user; no file writes or builds/test execution | Manager generates a copy-paste prompt after each subphase and after blocking repairs; user launches the reviewer |

Conditional roles: `hadoop-engineer` only for demonstrated missing preparation evidence under `modules/hadoop/**`; `rag-engineer` only if shared `prompts/runtime/**` or `prompts/schemas/**` must change; `infra-engineer` only for a justified new `scripts/**` helper; `documentation-engineer` for general `docs/**`/root README changes. No need to launch every role at once. Entity-resolution-local resources avoid creating shared prompt ownership unnecessarily.

The coordinator alone assembles `docs/agent-runs/phase-05/**` reports from agent responses. The human owns gate decisions and actual labels. Dataset engineering may validate/import human label files without rewriting the original annotations. Module owners own module-local tests; the independent tester owns `tests/**`. No role may edit another owner's paths. An unlisted path or ownership collision must be resolved before creation. This external handoff plan does not amend the constitutional files.

### Explicit parallel task schedule

Use parallel work only inside the authorized subphase. Start independent lanes together when slots are available; do not launch more writers just to fill slots. With four total slots, the coordinator can run at most three specialist agents concurrently. If a tool has a different limit, adapt the schedule without changing ownership or checkpoints.

| Subphase | Tasks that can run in parallel | Dependencies and sequential work |
|---|---|---|
| **5A** | Domain owner inventories/designs shared contracts; build owner inspects/wires project dependencies and test settings; dataset owner inventories real records, distinct pair supply, licenses and bounded acquisition options. These are three separate lanes. | Agree endpoint/config/serialization examples before dependent implementation. Build owner waits for agreed API/dependency decisions where necessary. Dataset inventory can start immediately; expanded acquisition belongs to 5C. Consolidate and review contract examples before handing back 5A. |
| **5B** | Entity-resolution owner implements matching and offline adjudication in its module; independent tester authors separate cases under `tests/**` once interfaces are agreed. A demonstrated upstream contract/preparation repair may run in its own owner's territory while unrelated work proceeds. | Production interface changes must be communicated before dependent tests are finalized. Compile/run dependent tests after the required implementation lands. A repair that changes an input contract requires dependent work to be rechecked. Within the entity-resolution owner's lane, schedule normalization/features, resolution, and adjudication components in dependency order; do not create multiple simultaneous writers for the same module. |
| **5C** | Dataset owner performs bounded acquisition and provenance validation; entity-resolution owner develops the local review page, queue/label tooling and evaluator; independent tester develops UI and hand-computable evaluation cases under `tests/**`. | Development can use clearly synthetic fixtures while real data arrives. The real queue and frozen population/split require validated source data; browser integration requires an exported page; evaluator checks require its agreed interface. The review page and evaluator share one production owner and are not separate concurrent production writers. |
| **5D** | After user authorization for 5D, entity-resolution owner implements the chosen provider adapter while the user labels the already reviewed real queue. Independent tester adds adapter failure/schema/budget tests separately. Dataset owner can validate and import completed annotation batches when a slot is available. | Provider-specific implementation waits for provider/model selection. Live calls additionally wait for approved numerical limits, runtime credentials and passing offline checks. Label import waits for actual human exports. Final held-out evaluation remains in 5E. Never let parallel provider work expose predictions to the blind labeling tool. |
| **5E** | After source/policy/prompt/model freeze, evaluation against frozen predictions and independent artifact/provenance inspection may run concurrently if they have immutable inputs and separate output directories. Coordinator may assemble reports from completed evidence. | Produce frozen predictions before scoring them. Serialize sbt builds/tests and any tasks sharing generated output or cache directories. Final comprehensive code review waits for completed gate/evaluation evidence. Repairs precede fresh affected verification and review. Human acceptance follows the technical handoff. |

For each launch, record what is ready, what it depends on, who owns its files, and which output other agents may consume. Never read a half-written manifest, queue, prediction file or policy as a finalized input. Publish completed artifacts atomically or hand them off after their writer finishes. All lanes must finish or stop before the current subphase is returned to the user.

### Work order every subagent must receive

Include: phase goal; **currently authorized subphase and its stopping boundary**; exact baseline/current diff; relevant paths and role definition; allowed writes; forbidden writes/actions; input/output contracts; dependencies; acceptance cases; allowed commands; report fields. Require exact observed results and `BLOCKED-ON` evidence where appropriate. Subagents must not implement later subphases speculatively. They return reports to the coordinator and never self-approve or modify human decisions.

## 6. Preflight and interface agreement

1. Inspect `git status --short`, branch, HEAD and relevant diff. Confirm the accepted Phase 4 baseline exists. Preserve unrelated changes and note any changed assumptions.
2. Read required instructions. Record the current tool/runtime and native delegation limits. Do not infer constitutional ratification from file presence.
3. Have domain and entity-resolution owners agree on entity endpoints, observation keys, decision/audit envelopes, policy fields, review labels, and downstream link exports. Freeze interface examples before parallel implementation.
4. Have dataset engineering count distinct available pairs by entity type and evidence path. Do not discover at the end that there are only a handful of source records.
5. Establish `docs/agent-runs/phase-05/prompt.md` from this work order and start an owner report with unresolved dependencies. Do not create an acceptance statement.

## 7. Input bridge: Phase 4 evidence to identity candidates

Consume actual completed Phase 4 exports, not just hand-crafted fixtures. Prefer a local path to a completed run and validate its completion metadata and file digests according to Phase 4's documented format. Never accept a partial or corrupt run as trusted input. If regenerating local samples, use the documented Hadoop entry point and record the exact invocation.

Current export layout is `export/snapshot=<snapshot>/run=<uuid>/<kind>/`. Relevant kinds include `work`, `author-mention`, `match-candidate`, `index`, `mention-affiliation`, `enrichment`, `orcid-profile`, `orcid-activity`, `institution`, `venue`, `graph-edge`, and `text`. Verify concrete files and framing; use the existing readers/contracts where appropriate. This plan does not assert a particular run directory exists.

Important contract constraints:

- `CandidateObservation` carries source, sourceRecordId, datasetSnapshot, optional workId. Lookup by the full observation key, never by workId alone. Two sources can already share a DOI-based workId without a Phase 5 identity decision.
- Phase 4 `MatchCandidate` is bibliographic blocking evidence, not a researcher pair and not a confirmed merge. Preserve every contributing candidateId/blockKey. Its ID includes the block, so the same observation pair can occur in several blocks.
- Deduplicate final comparisons by canonical unordered observation/entity pair plus entity type and snapshot identity; aggregate block evidence. Prevent duplicate blocks from multiplying evidence or evaluation counts.
- Preserve Phase 4 candidates and `prep-features-v1/v2` unchanged. The v2 feature vocabulary is closed; Phase 5 features require their own versioned representation, not new names inserted into old candidates.
- Derive work comparisons from observation pairs. Derive researcher comparisons from explicit author mentions/profiles and bounded mention blocking/alignment, retaining parent works and evidence pointers. Sharing a paper, title, ordinal, affiliation, or name does not independently establish researcher identity.
- Include bounded cross-publication mention comparisons; work-only candidate pairs are not sufficient researcher disambiguation. Avoid all-pairs enumeration for common names. Cap block size, pairs, evidence bytes, and work performed; retain skipped/oversize counts and reasons.
- An ORCID work activity is not a full publication author list. Do not manufacture authorship or publication teams from it.
- Missing source observations, dangling references, invalid schema versions, or conflicting duplicate lookup keys must produce explicit errors/rejects, not silent drops or overwritten records.

Read core `Records.scala`, `StableIds.scala`, `DomainValidation.scala`, `CoreJson.scala`, `TextNorm.scala`, `PreparationFeatures.scala`, config classes/loaders, and their tests. Use `DomainValidation` and strengthen Phase 5's contextual validation where generic checks are insufficient.

Current `MatchDecision` has sourceId, targetId, features, decision, confidence, reasonCodes, policyVersion, runId, uncertainty, and provenance. It does not itself carry every audit field needed here. Prefer a versioned wrapper with entityType, pairId, typed source observation refs, contributing candidate IDs, feature availability, decision path, policy/config hashes, evidence refs, and optional adjudication metadata. If another module consumes a new type, route that shared contract to domain engineering; do not duplicate incompatible shared definitions.

Preserve original observations and IDs. `StableIds` currently permits validated ORCID researcher IDs or deterministic provisional ScholarChain IDs; OpenAlex author IDs are evidence/hypotheses, not canonical ORCID identities. Reuse those rules. Version and document deterministic representative selection for accepted groups. Never derive a supposedly confirmed identity from name text alone. Snapshot-bound wrappers must disambiguate source observations even where an existing mention ID does not encode a snapshot.

## 8. Matching subsystem design

Implement both **work resolution and researcher resolution**, with separate features, policy sections, results, and metrics. Keep the implementation modular and testable with pure functions around I/O.

### 8.1 Normalization and identifier evidence

Preserve raw values alongside normalized values and normalization version. Define Unicode handling, case folding with a fixed locale, punctuation/whitespace treatment, title markup removal, initials, and name-order variants. Normalization is a comparison aid, not an identity claim. Do not erase discriminating information or execute/resolve arbitrary markup.

Define namespace-aware normalization, syntax validation, and exact comparison for DOI, arXiv, ORCID, OpenAlex, Semantic Scholar and repository URLs. Distinguish work IDs from author IDs. Document arXiv version behavior and repository URL normalization boundaries. Do not equate arbitrary URLs or different repository paths by aggressive stripping. Support identifier rules with unit fixtures even when a source is absent from the real portfolio; do not add Semantic Scholar to `SourceType` or claim live coverage without actual acquisition.

Apply conflict checks before exact-ID acceptance and again before any LLM outcome or group formation. Compare authoritative identifiers within the same namespace and entity meaning. Do not treat missing IDs or distinct namespace strings as contradictions. Preserve declared identifier disagreements from `observedIdentifiers`, preferred fields, ORCID work references, and original source links. Authority rules must distinguish trusted direct identifiers from weaker source hypotheses. Different ORCIDs cannot silently merge through a shared OpenAlex hypothesis. Work equality does not imply author equality.

### 8.2 Features and scoring policy

Implement an explicit feature catalog for both entity types. Cover names/initials, author order, coauthor overlap, affiliation compatibility, identifier evidence, title similarity, year distance, venue compatibility, citation neighborhoods when actually available, and source reliability. For each feature document formula, range, missing behavior, entity applicability, and evidence source. Unavailable citation evidence remains unavailable; no fabricated neighborhoods. Count weak or correlated evidence conservatively.

Use a transparent deterministic weighted scorer as the first version unless calibration justifies something more complex. A score is not a calibrated probability unless evaluated as such. Missing evidence must not become a perfect match or a negative fact. Preserve availability indicators and finite numeric values; do not reuse Phase 4's `year_abs_delta=-1` as an ordinary distance. Require sufficient independent evidence before accepting name-based matches.

All weights, minimum evidence requirements, threshold boundaries, conflict precedence, source-reliability settings, blocking bounds and LLM bands belong to a versioned policy/config file. No hidden numeric production defaults or model IDs. The existing shared `EntityResolutionConfig` has policyVersion, acceptThreshold, rejectThreshold, llmBandMin, llmBandMax; the sample values are local-dev placeholders, not calibrated thresholds. Avoid competing settings: explicitly derive from or supersede the shared section, bind effective values into a fingerprint, and reject disagreement. Keep local-only config types in this module; shared config changes belong to domain engineering.

Choose and test an unambiguous boundary convention, e.g. reject when score <= rejectThreshold, accept when score >= acceptThreshold, unresolved otherwise, after hard conflict checks. Require a strict gap between reject/accept thresholds and place the entire LLM band inside that gap. The current generic loader does not enforce all these Phase 5 conditions; enforce them at Phase 5 startup. Invalid config fails before output writes or calls.

Record paths such as exact ID, deterministic bibliographic, probabilistic/scored, and LLM-adjudicated separately. Keep score, path, reason codes, uncertainty, and feature evidence for every result. Do not hide an exact-ID conflict behind a high score.

### 8.3 Link exports and group safety

Emit separate accepted, rejected, unresolved and conflict streams by entity type, plus invalid-input/reject diagnostics and run summaries. Produce a documented typed accepted-link format that Phase 6 can consume without parsing free text; include observation/member IDs, representative ID if assigned, decision IDs, policy version and provenance. Preserve unresolved mentions.

Guard transitive merges: A–B and B–C must not silently create a group containing mutually conflicting authoritative IDs. Either emit pairwise links with explicit constraints for downstream grouping or implement conflict-aware grouping with deterministic conflict propagation; test the resulting contract. No graph metrics, Spark jobs, AWS storage, HTTP microservices, or final application features belong here.

## 9. LLM adjudication in two stages

### Stage A: build/test offline

Implement a narrow provider interface and deterministic fake responses for tests. Disabled mode never makes network calls; eligible cases remain unresolved with a reason. This mode is runnable without credentials and must not be presented as real model evidence.

Create versioned module-local prompt and JSON schema resources. A request contains only bounded relevant candidate evidence, allowed endpoint IDs/evidence references, policy and request hashes. Treat all dataset text as untrusted data. No tools, arbitrary URLs, source mutation, external browsing, or hidden chain-of-thought is needed. Ask for a concise evidence-based rationale.

Validate responses with a strict closed schema: request identity, accept/reject/abstain, permitted evidence refs, bounded reason codes/rationale, and any explicitly designed optional confidence field. Reject unknown fields, wrong types/enums, oversized responses, unrelated IDs/evidence, and stale/mismatched requests. Model confidence is not calibrated system confidence. An LLM cannot mint identifiers, bypass conflicts, edit source records, or turn an absent fact into evidence.

Only eligible unresolved pairs inside the configured band reach the adapter. Limit evidence/request bytes, response size, timeouts, retries, concurrency, total requests and token/spend allowance. Budget exhaustion, timeout, malformed output or provider failure yields unresolved with an auditable reason, not default acceptance. Preserve a single final path plus the pre-LLM score/outcome.

Cache validated adjudications by canonical input hash, prompt version/content hash, provider/model version and generation settings, policy version/hash, and schema version. Include every evidence field that can affect the answer. Cache reads validate context and schema. Use safe atomic writes and deterministic replay; distinguish hit/miss and fake/live provenance. Never let fake outputs satisfy a live run. Missing provider resolution information must not be invented.

### Stage B: provider selection and bounded real evidence

After Stage A is runnable, show the user a concrete sanitized request and explain the remaining choice in plain language. Ask for provider/model and request/token/spend limits. A cloud API or a genuinely running local model can implement the interface; do not assume a paid subscription includes API credits. Do not install or download a large local model incidentally.

The adapter can accept a secret at runtime through approved credential mechanisms. Never inspect `.env`, credential files or secret directories, dump the environment, log keys, or commit credentials. Read current official provider documentation when implementing that adapter. Configure secret variable names, never secret values, in examples.

When authorized and configured, run a bounded real adjudication against eligible **development/demo** pairs and record provider/model, prompt/policy/schema hashes, call/cache counts, failure/abstention rates, and observed usage. Keep the locked test partition untouched during this demo. Execute the frozen evaluation later. If no eligible real pair exists, report that gap and route acquisition; do not force scores into the band to manufacture a demo.

If provider choice, credentials or budget is pending, finish all independent work and hand back the exact remaining step. Code-ready and phase-accepted are different states. Mocks alone do not demonstrate real LLM adjudication.

## 10. Real evaluation population and label integrity

Dataset engineering must supply enough **distinct, real, traceable candidate pairs** for at least 200 human reviews, covering both entity types and a useful mixture of easy positives, hard negatives, common names, missing fields, cross-source observations and uncertain cases. Aim for roughly balanced researcher/work coverage; explain actual composition rather than inventing minimum per-type quotas from the course.

Do not inflate the count through repeated blocks, reversed pairs, repeated snapshots of the same evidence, copies or trivial synthetic variants. Unit-test fixtures are synthetic and never substitute for the human-reviewed real set. If committed samples are insufficient, use a documented bounded expansion of the existing datasets with license, retrieval date, snapshot identity, checksum, byte/record/request bounds and failure handling. Route acquisition and manifest changes to dataset engineering and source normalization gaps to Hadoop engineering. Preserve previous sample provenance rather than silently replacing accepted inputs. If public acquisition requires keys, paid access or a broader download, ask for that concrete missing input while continuing other work.

Freeze a source population manifest and candidate population before scoring for evaluation. Use reproducible sampling across evidence strata and record seed, selection rule and sample counts. Do not cherry-pick only accepted or successful LLM outcomes. If oversampling strata, report stratified sample metrics; population claims require a justified sampling/weighting design.

Split development/calibration and held-out evaluation **before labels are used**. One workable starting allocation is 40 development pairs and 160 held-out pairs out of 200, adjusted for usable labels and entity coverage; these counts are a plan choice, not a course mandate. Group shared records, near duplicates, known identities and linked works into the same partition to reduce leakage. Document residual leakage risks and infeasible grouping; don't fall back silently to random pair splits. Provide sufficient binary-labeled examples of both classes per entity type to make metrics meaningful.

Freeze policy/prompt/model settings after development calibration. Production matching must have no code path that reads gold labels or a held-out membership list as identity evidence. The evaluator reads predictions and labels separately. Held-out labels may be used for final measurement, not threshold selection. Subsequent tuning requires a new version and fresh holdout or an explicit statement that results are exploratory.

Distinguish pair classification recall within the candidate population from end-to-end matching recall. Add a bounded independently selected positive-pair check outside generated candidates where feasible to measure blocking misses; otherwise state that blocking recall is unmeasured. Never call conditional candidate recall global researcher recall.

## 11. Local human review tool

Recommended minimal implementation: a self-contained HTML/JavaScript page bundled under `modules/entity-resolution/src/main/resources/review/`, exported by the Scala CLI. It opens locally, uses file selection to load a review queue, and downloads label/checkpoint JSON. No cloud hosting, frontend framework, external scripts, analytics, credentials, API server or runtime service is needed.

Requirements:

- Show the two records side by side, clearly identifying researcher versus work tasks. Include raw names/titles, dates, author order/context, identifiers, affiliations when present, and source/snapshot/locator references. Show absent evidence as missing.
- Offer Same, Different, and Uncertain, plus a bounded optional note/reason and progress/navigation controls. No preselected answer, automatic label or model-suggested label.
- Keep scores, policy predictions and LLM judgments hidden during initial labeling to reduce anchoring. Separate optional post-evaluation error analysis from blind annotation.
- Export pair IDs, entity type, queue/schema/source hashes, label, human-entered reviewer ID, timestamps and label revisions. Reviewer ID is provenance, not proof of authentication; disclose that limitation.
- Allow resuming from an exported checkpoint, undoing/revising labels, skipping, and detecting incompatible queues or duplicate/conflicting imports. Completed work must survive refresh through an explicit saved checkpoint; do not promise unsaved browser state is durable.
- Never execute source-provided HTML. Render data with safe text APIs. Do not auto-fetch source links. Make deliberate external links safe and distinguish them from verified local evidence.
- Importer rejects unknown pair IDs, altered evidence hashes, unsupported labels and mixed queue versions. Preserve original human label files, and write a validated derived dataset rather than silently editing annotations.
- Explain that Uncertain is valid and is not a negative label. Report uncertain counts separately and request more review/adjudication if binary gold is insufficient.
- Include a short plain-language guide: what each label means, how to inspect evidence, save/resume/export, and what to send back to the coordinator.

Test the actual page in a browser with a small synthetic queue: import, safe rendering, labeling, navigation, export, refresh/reimport and mixed-queue rejection. Automated clicks exercise the tool only; they do not create human evidence. Keep these test outputs separate from real labels. Browser test sources belong to `tests/**`; route build/tool dependencies if necessary.

At the human checkpoint, provide one exact tool path, one queue path, simple opening/loading/saving steps, and the count remaining. Ask the user to label; never claim the 200 reviews occurred because a queue was generated.

## 12. Evaluation and reporting

Implement the evaluator and test it against small hand-computable matrices before real labels arrive. Report researcher/work results separately and by matching path; include counts and denominators even when a path is empty.

Required output design:

- A gold-label by four-outcome table so accepted/rejected/unresolved/conflict are visible.
- A clearly defined binary acceptance confusion matrix: positive prediction is ACCEPTED; all other outcomes are nonacceptance. TP/FP/FN/TN and precision/recall/F1 follow that definition. FN therefore includes true matches left unresolved or in conflict. Also report decisive-only accuracy/metrics separately, with explicit denominators, so abstentions cannot hide misses.
- Decisive coverage `(accepted + rejected) / evaluable binary-gold pairs`, plus unresolved/conflict rates, manual-uncertain count, invalid predictions, missing predictions and invalid inputs. Never silently omit missing predictions to improve metrics.
- Breakdowns for exact-ID, deterministic bibliographic, scored/probabilistic and LLM-adjudicated paths, with fake/live/cache provenance. No-data metrics are null/not applicable, not manufactured zero or 100% accuracy.
- Threshold sensitivity on the development partition. A frozen held-out sensitivity table may be descriptive only; don't use it to pick the reported production policy. Do not make paid calls for every threshold permutation without a separate bound/approval.
- Representative error records with evidence refs, decision path and concise analysis. Include up to ten available false positives and ten false negatives; if fewer exist, state the actual counts. Never invent errors to reach ten.
- Evaluation manifest binding input/candidate/split/label/prediction hashes, code revision and dirty diff/source hashes, policy/config/prompt/model/schema versions, seed and command, actual toolchain, time, and all limitations. New run UUIDs must not invalidate substantive replay comparisons; normalize only declared invocation metadata.

No numeric accuracy target was agreed in this chat. Do not invent a course precision target or declare the model good solely because tests pass. Summarize observed errors and risks for human review, especially false merges and common-name cases.

## 13. Proposed implementation layout and CLI contract

These paths/classes are proposed, not existing APIs. The owners may refine names before interface freeze, then update all documented commands consistently.

```text
modules/entity-resolution/
  README.md
  src/main/scala/edu/uic/cs441/scholarchain/entityresolution/
    Phase5Main.scala
    InputLoader.scala           # completed exports, lookups, validation
    CandidateBuilder.scala      # work/mention pairs, bounds, dedup
    ResolutionPolicy.scala      # strict config, policy hashes
    Normalization.scala
    IdentifierRules.scala
    FeatureExtractor.scala
    ResolutionEngine.scala      # precedence, scoring, audit results
    LinkExporter.scala          # typed downstream links/group constraints
    Adjudication.scala          # schema, adapter, bounded orchestration
    AdjudicationCache.scala
    ReviewQueue.scala           # deterministic sampling and splits
    GoldLabels.scala            # separate annotation import/validation
    Evaluation.scala            # label-free matcher; label-aware evaluator
  src/main/resources/
    phase5-policy.v1.json
    adjudication/               # prompt, strict schema, examples
    review/                     # offline HTML/JS and plain guide
  src/test/scala/...            # owner unit/feature tests
tests/src/test/scala/...        # independent integration/adversarial tests
datasets/entity-resolution/     # dataset-owner population, checksums,
                                # provenance, human-input/validated labels
docs/agent-runs/phase-05/        # coordinator evidence and reports
target/phase5/                  # ignored generated runs/cache/review exports
```

Do not require that raw model responses, downloaded full datasets, credentials or huge caches be committed. Keep small license-compatible representative evidence and manifests sufficient for replay. Human label files need explicit preservation and backup instructions; do not put the only copy in an ignored disposable target directory. Review exports may be saved by the user to a durable chosen path before validated import.

Implement a single Scala main with explicit subcommands and clear failure exits. The documented command set should cover:

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home

# Existing gate and project IDs:
sbt -batch check
sbt -batch 'entityResolution/test' 'independentTests/test'

# Proposed CLI contract; implement and verify before calling these runnable:
sbt -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main resolve --input <completed-phase4-run> --policy <policy.json> --llm-mode disabled --output <new-run-dir>'
sbt -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main build-review-queue --input <completed-phase4-run> --sampling <sampling.json> --output <queue-dir>'
sbt -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main export-review-tool --output <tool-dir>'
sbt -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main import-labels --queue <queue.json> --labels <human-export.json> --output <validated-labels.json>'
sbt -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main evaluate --predictions <frozen-predictions> --gold <validated-labels.json> --split <frozen-split.json> --output <evaluation-dir>'
```

The angle-bracket arguments are placeholders. In the handoff, replace them with actual verified paths and successful invocations. Provide explicit sampling/split configuration and `--help` examples. No subcommand silently overwrites a completed run, edits inputs, enables live calls, or recursively deletes output. Equivalent reruns should reuse only verified artifacts or write to a new output directory.

## 14. Implementation sequence and checkpoints

### Mandatory execution rule: one subphase at a time

Execute **5A → user review → 5B → user review → 5C → user review → 5D → user review → 5E → final user review**.

- The initial implementation task authorizes Subphase 5A and its preflight only. The rest of this document describes future work, not permission to perform it immediately.
- Complete the current subphase, its relevant tests, evidence consolidation and necessary repairs before handing it back. Do not combine subphases to save time or defer every review until the end.
- At each handoff, ensure all current-subphase workers have finished or been stopped. No agents, builds, acquisition jobs or live calls may continue in the background beyond the checkpoint. Do not launch the next subphase's agents while waiting.
- Return a concrete review packet: subphase completed or blocked; changed files/diff; actual commands and results; runnable demo or serialized examples where applicable; the complete copy-paste prompt for the user-selected external reviewer; any returned reviewer findings; limitations; manual actions; and the proposed scope of the next subphase. Keep that evidence in the existing required reports, grouped by subphase; do not create five new sets of reports.
- End the response with a clear checkpoint statement, for example: **“Subphase 5A is ready for your review. I have stopped. I will start Subphase 5B only when you explicitly tell me to continue.”** Then end the turn.
- Wait for the user to return the external reviewer verdict and explicitly approve advancement, such as **“Continue to 5B.”** If the verdict has not been supplied, state that the review gate is still pending rather than inferring APPROVE. Elapsed time, silence, a subagent's APPROVE, test success, labels being uploaded, or the original request to implement Phase 5 is not authorization to advance.
- If the returned reviewer requests blocking changes or the user requests fixes, route repairs to the current owners, rerun relevant verification and return an updated copy-paste review prompt. Wait for the user to obtain and return a fresh verdict. A repair request alone does not authorize the next subphase.
- Resume from the reviewed work after authorization. Do not reimplement accepted subphases or silently widen their scope; report newly discovered dependencies and route the minimal repair.
- Advancing into 5D does not itself authorize paid/model calls: the provider/model and numerical budget must also be explicitly approved. Passing 5E's technical gates does not replace final human Phase 5 acceptance.
- These checkpoint rules take precedence over any general instruction elsewhere in this plan to continue independent work. Parallel work is allowed only within the current subphase.

### Subphase 5A. Contract and data readiness

Spawn domain, build and dataset inventory owners in parallel as scheduled in Section 5. Agree endpoint/audit/config contracts and independent-test wiring. Inventory candidate supply, real source evidence and acquisition bounds. Delegate only proven missing contracts; do not redesign all of core.

Exit: concrete serialized examples for work/researcher pairs, decisions, labels and policy; owners agree on inputs; candidate sufficiency is assessed and the later acquisition work is specified. **STOP and return the Subphase 5A review packet. Wait for the user to authorize Subphase 5B.**

### Subphase 5B. Deterministic resolution and offline adjudication

Spawn entity-resolution implementation. Build source lookups, pair derivation/dedup, normalization, identifier/conflict rules, evidence features, scoring and exports. Implement provider seam, strict schema, fake adapter, cache and disabled behavior. Add module tests as behavior is introduced. Build independent tests after APIs settle, using hand-computable outcomes rather than mirroring the scoring implementation.

Exit: actual Phase 4 data produces auditable typed decisions; fake/disabled modes are honest; no implicit merges or source mutation. **STOP and return the Subphase 5B review packet. Wait for the user to authorize Subphase 5C.**

### Subphase 5C. Review tool and evaluation readiness

Finish browser review tool, queue/split generator, label import, evaluator, guide and deterministic replay. Dataset owner completes bounded acquisition/provenance and verifies enough unique pairs. Execute local browser tests and independent matrix checks. Freeze labels/policy access boundaries.

Exit: provide the user a working review page and real queue, with current-subphase tests, documentation and any preliminary review completed before handoff. If human labels are pending, mark final evaluation/acceptance BLOCKED-ON human review. **STOP and return the Subphase 5C review packet. Wait for the user to authorize Subphase 5D; do not begin provider integration or label-dependent evaluation while waiting.**

### Subphase 5D. Real-provider checkpoint and human review

Show sanitized example and request provider/model/budget when ready. Implement the selected adapter under the same owner, test it with fakes, then execute only authorized bounded real calls. The user labels pairs using the tool; import annotations without changing them. Keep development/held-out partitioning intact.

Exit: traceable human reviews and real LLM evidence exist, or precisely identify which external prerequisite is pending. Do not invent a completed gate. **STOP and return the Subphase 5D review packet. If prerequisites remain missing, report a blocked checkpoint, not completion. Once the checkpoint is satisfied, wait for the user to authorize Subphase 5E.**

### Subphase 5E. Frozen evaluation and full review

Freeze code/policy/prompt/model and manifests; run fresh predictions and evaluation, then `sbt check` on the final source state. Retain command exit codes, meaningful logs and hashes. Run two equivalent local resolution passes against the same verified inputs and controlled fake/cached adjudications; compare logical outputs without erasing real source differences.

Generate and give the user a complete copy-paste prompt for their preferred fresh read-only code-reviewer, using the external-review protocol below. Include the **entire Phase 5 diff, including untracked files**, contracts, source manifests, UI behavior evidence, evaluation artifacts and retained gate logs. Do not launch the reviewer yourself. Ask it to report **all confirmed findings in one pass**, classify blockers versus nonblocking observations, and cite paths/lines, reproduction reasoning, impact and owner. The reviewer does not run builds/tests or edit files; owners/tester produce missing evidence. Stop and wait for the user to return the verdict.

When the user returns the verdict, route all blockers together to their owners, rerun affected gates, then generate an updated comprehensive review prompt for the user to run externally. Wait for the returned recheck verdict; do not perform or self-approve the independent review. Preserve historical findings and mark resolutions with evidence. Don't restart from scratch or require repair of unrelated cosmetic issues to close the phase.

Exit: independent APPROVE for the reviewed scope, observed final gates and complete evaluation. **STOP and return the Subphase 5E/final Phase 5 review packet for the human acceptance decision.** A code-only preliminary APPROVE does not mean labels/provider requirements are complete. Do not commit, push or begin Phase 6 without separate authorization.

### External code-review handoff: manager generates the prompt, user runs it

This is mandatory after **5A, 5B, 5C, 5D and 5E**, and after repairs to blocking findings. Review each subphase as a coherent deliverable; do not request a review after every individual task. Implementation and test subagents remain manager-launched. The code reviewer is the exception: **the manager must never launch it**.

1. Finish the authorized subphase and its relevant verification; freeze its source and evidence before requesting review. If a prerequisite is missing, provide an honest partial/blocked review scope, not a completed-subphase claim.
2. Generate one self-contained prompt and display its full text in a copyable code block in the handoff response. Do not merely say “ask a reviewer” or provide only a file path. A copy may also be kept inside the existing phase evidence.
3. Fill the template below with actual paths, SHAs, changed/untracked file lists, command results and evidence locations. Do not leave placeholders for information the manager already knows. Capture each subphase's starting HEAD plus dirty tracked/untracked file hashes or a retained diff manifest, so the reviewer can distinguish current-subphase edits from earlier uncommitted work. A single HEAD alone is insufficient when several subphases remain uncommitted.
4. Tell the user to paste that prompt into their preferred independent reviewer and return its full verdict. Stop; do not invoke a reviewer, choose a reviewer model, impersonate its verdict or automatically proceed.
5. Preserve the returned verdict in `review.md` under the subphase heading, with its provenance as user-supplied external review. Track routed fixes in `repairs.md`. Do not fabricate native reviewer IDs if the user did not supply them.
6. A returned APPROVE still needs the user's explicit instruction before starting the next subphase. A REQUEST-CHANGES verdict leads to routed repairs and a new external review prompt. If a finding concerns unfinished later-subphase scope, classify it honestly as future work rather than forcing early implementation. Nonblocking observations do not require an endless repair loop.
7. The final 5E prompt requests a comprehensive whole-Phase-5 review as well as the last subphase's changes. Earlier subphase approvals do not replace that final review. Every independent reviewer remains strictly read-only.

**Template the manager must complete and give to the user:**

Reviewer instructions removed at the user’s request; review prompts are provided in chat.

## 15. Required test matrix

| Area | Minimum meaningful cases |
|---|---|
| Input and provenance | completed vs partial/corrupt run; missing lookup; same work ID across distinct observations; snapshots; duplicate conflicting payloads; multi-block dedup; unknown schema |
| IDs | DOI prefixes/case; arXiv versions; valid/invalid ORCID checksum; OpenAlex author/work distinction; Semantic Scholar syntax; repository path/query boundaries; missing vs conflicting evidence |
| Text and features | Unicode/diacritics, punctuation, markup, initials, reordered names, common-name negatives, missing year/venue/affiliation, no citation data, feature availability, nonfinite values |
| Decisions | exact evidence vs conflicting authoritative IDs; threshold boundaries; insufficient name-only evidence; separate work/researcher policies; transitive conflict; deterministic output |
| LLM | disabled makes zero calls; band bounds; abstain; bad JSON/extra fields; wrong IDs/hashes; fabricated refs; injection text; timeouts/retries/budget; bounded response; cannot override conflicts |
| Cache | replay; each relevant key change invalidates; fake/live isolation; corruption/mismatched request; safe interruption/atomic writes |
| Review UI/import | safe text rendering; same/different/uncertain; save/resume/undo; wrong queue; duplicate revisions; labels not auto-filled; no silent annotation mutation |
| Evaluation | hand-calculated TP/FP/FN/TN and four-outcome tables; abstentions/conflicts; no-data denominators; missing predictions; duplicate pairs; entity/path splits; leakage guards; threshold sensitivity |
| End to end | real completed Hadoop export to typed outputs/queue; two-run logical equivalence; small bounded live evidence only when authorized; final full `sbt check` |

Tests must assert required behavior, not only assert that implementation code agrees with itself. Passing mock tests is not a claim that a live provider ran. Synthetic labels are test-only.

## 16. Evidence, final gates, and manager handoff

Keep reports concise and consolidate validation into required reports; do not add a separate `validation.md`. Use the exact report fields from `docs/agent-runs/README.md`:

`STATUS`, `OWNER`, `WORK ORDER`, `FILES CREATED`, `FILES MODIFIED`, `COMMANDS RUN`, `TEST RESULTS`, `VALIDATION RESULTS`, `ASSUMPTIONS`, `RISKS`, `MANUAL ACTION REQUIRED`, `BLOCKED-ON OWNER`, `BLOCKED-ON EVIDENCE`, `NEXT GATE`.

Assemble `prompt.md`, `owner-report.md`, `test-report.md`, `review.md`, and `repairs.md` as needed under `docs/agent-runs/phase-05/`. The human supplies acceptance; an agent must not invent or rewrite that decision. Record an accepted commit hash only after a real commit exists and the user authorizes that workflow. This plan does not authorize a commit or push.

Final checklist:

- [ ] Each subphase was handed back separately, and explicit user authorization was obtained before starting the next.
- [ ] Both work and researcher resolution consume actual preparation evidence with typed links and preserved uncertainty.
- [ ] Exact-ID rules, feature definitions, versioned policy, threshold boundaries and conflict precedence are documented and tested.
- [ ] Unsafe pair or transitive merges are prevented; raw source observations remain immutable.
- [ ] Four outcomes and all skips/rejects have traceable evidence and counts.
- [ ] Local review tool works; at least 200 unique real pairs have actual human review, with usable label counts reported.
- [ ] Frozen split/label/policy/prompt/model/input manifests establish evaluation provenance and guard leakage.
- [ ] Real LLM adjudication is bounded, schema-validated, cached and demonstrated; mocks are explicitly separate.
- [ ] Separate researcher/work metrics, path metrics, confusion tables, coverage/uncertainty, errors and development sensitivity are retained with honest limitations.
- [ ] Fresh final `sbt check`, independent adversarial checks, UI smoke evidence and deterministic replay pass on the reviewed source.
- [ ] User-selected external reviews were requested with copy-paste prompts after every subphase; actual returned verdicts are retained. The final comprehensive independent reviewer returns APPROVE; nonblocking notes are disclosed.
- [ ] Human acceptance is genuinely recorded before Phase 5 is called accepted. Phase 6 has not started.

Return to the user: implementation summary; exact files and runnable commands; native agent IDs/roles; fresh test/review results; data/label/model provenance; evaluation metrics or an explicit pending status; all manual actions; remaining blockers/nonblocking risks; and the next human gate. Give the next independent reviewer the base SHA, complete changed/untracked file inventory, source/evidence hashes and current report locations. Never guarantee that a review found every possible defect.

If waiting on labels, provider credentials/budget or acquisition, finish only unaffected work inside the currently authorized subphase and hand back the result with the exact missing input. At a subphase boundary, end the turn and wait for the user; do not continue in the background or begin the next subphase. Do not present pending requirements as a completed subphase or phase.


## User-supplied external review repair work order — Subphase 5A B1

The user returned an independent user-launched Claude Code REQUEST-CHANGES verdict with one blocker B1 and nine nonblocking observations. Full report is preserved in review.md. This authorizes the plan's current-subphase repair/recheck workflow only;5B remains unauthorized. No manager-launched reviewer is permitted.

Before repairs, the coordinator verified all140original frozen source hashes unchanged and retained the original diff/inventory/prompt/freeze in history/5a-initial-handoff/. b1-repair-start.json binds the pre-repair dirty source state at unchanged main HEAD099e303311be7a1b2e2cf5655e0c7ce9fa710474.

Bounded ownership: domain-engineer `/root/phase5a_domain` owns modules/core/** typed authority namespace/validators/owner tests/fixtures/docs; ER owner `/root/phase5a_er` confirms authority policy and changes only its module README; independent tester `/root/phase5a_test` owns tests/** executable before/after regression and fresh serialized gates; coordinator owns phase-05 reports/evidence. No worker delegates; no code reviewer is launched. All original one-writer/source/security/no-commit/no-cloud rules remain.

Agreed B1fix: closed explicit wire namespace doi/arxiv for works,orcid for researchers; canonical existing StableIds values only; entity-compatibility checks before conflict decisions; unknown/case/alias spellings rejected. Base-only arXiv hard authority avoids false conflict across source versions; raw versioned observations remain preserved. Native DBLP/OpenAlex work IDs remain source bindings and OpenAlexauthor IDs remain hypotheses. SemanticScholar/repository authority waits for validated namespace/canonicalizer design5B, without source addition or invented acquisition. The canonical old grouping fixture may remain byte-identical under the strict new codec and must be Scala-roundtrip verified, not cosmetically altered to manufacture a diff.

Verification sequence: independent tester demonstrates B1against pre-fix code if executable, then releases exclusive sbt slot; domain implements/updates own tests; tester adapts only own fixtures to finalenum; domain formats/tests onlycore; tester formats/tests onlytests/**; capture new sourcefreeze; run one fresh sbtcheck; retain exact failed/successful command outputs and compare sourcehashes. No overlapping sbt runs or writers. Full gate/evidence must describe observed results only.

N1–N9 remain nonblocking followups with explicit owners/timing in repairs.md. N6ownership was proposed to human at the B1work-order start; that pending status is superseded by the explicit user approval recorded in repairs.md. Silence was not treated as approval. Repairs do not authorize later subphases or human/provider work.

Exit: all jobs/workers stopped, concrete B1repair/evidence packet and complete external recheck prompt returned to user. Wait for returned recheck verdict and explicit advancement authorization; do not self-approve.


## B2 repair work order — current5Aonly

User returned B1recheck REQUEST-CHANGES: B1independentlyCLOSED,newB2source-groundingblocker,N10coveredprofileownORCIDomission and N11supersededpendingwording. Fullreportretainedreview.md. RepairB2plusN10minimalcoverageconsistency and N11coordinatordocs only; N1–N5/N7–N9remainfollowups,no5Bauthorization.

Domainownsmodules/core/** sourcefactgrounding/contextchecks/ownfixtures/tests/docs; ERconfirms namespace/sourcefieldgrounding andmoduleREADMEonly; testerownstests/** independentbefore/afterregression; coordinatorownsphaseevidenceandserializedsbtcommands. Beforeproductionwrites, independenttestsdemonstrateoldB2andN10behavioragainstunchangedcore. Afterrepairformat/targetedsuites,newsourcefreeze,onefreshfullsbtcheckandpostgatehash/JUnit/markerinspection,thenfreshuser-runexternalreviewpromptandstop. Noagentsmaylaunchreviewer,delegate,readsecrets,commit/push/acquire/callmodels/cloud orlater-phasecode.

b2-repair-start.jsonandhistory/5a-b1-recheck/preserveprior141filefrozenstate/diff/inventory/prompt. Nooldreviewresult/logoverwritten; newlysuppliedreviewprovenanceuser-launched. Assertionsmustbeclosedcanonicalnamespace/valueandmatchactualvalidatedsourcefactsforeachendpoint. Contradictoryknownfactsarenotmadeconsistentbyinventingassertions; preserveallsourceobservations. Canonicalsourceformcomparisonisgroundingonly,notnewmatchingpolicy. Noarbitrarysourcefetchoridentityclaim.

N6ownershipisalreadyexplicitlyapprovedanddocumented:Phase6spark-engineerownsgrouping/representativeselectionmodules/spark/**;domainownsIDrules/sharedcontracts. N11onlyclarifiessupersededcoordinatorpendingtext; no humangateorconstitutionalchanges.


## Subphase 5B authorization and work order — 2026-10-16

Human statements, transcribed without expanding the decision:

> status approved. So now we're good to go to 5b, but before go on, give me a oneline commit message so I can push this change before we move on

> alright now let move on phase 5b. Are you ready to implement phase 5b?

The user created commit `4ac236fcb01825b73635fa4c762a35bed4b362cd` on `phase-5`; preflight observed a clean working tree and all 142 committed 5A source hashes match the prior freeze. The coordinator did not commit or push. This records human approval/advancement; no complete external B2/N10 APPROVE report was provided or invented. Earlier pending-review text remains historical.

Authorized scope: 5B only, as original plan §§7–9 Stage A and §14 specify: actual completed Phase 4 input verification, bounded work/researcher candidates, normalization, source-grounded conflicts, features/scoring, typed four-outcome/link/complete-constraint exports, strict offline fake/disabled adjudication and cache, tests and fresh full gate. No 5C acquisition/review UI/evaluator, 5D provider/live calls or human-label import, 5E evaluation, Phase 6, cloud action or commit/push. Preserve the 40 development + 200 held-out review target and existing dataset shortfall.

Native owners: `/root/phase5b_er` writes `modules/entity-resolution/**`; `/root/phase5b_test` writes `tests/**`; `/root/phase5b_domain` writes only demonstrated minimal core accessor and its tests under `modules/core/**`. Coordinator alone assembles phase evidence. Subagents cannot delegate. Public APIs agreed before dependent tests; all sbt builds serialized by coordinator. Agents inherit parent model/settings; prior model recommendations are not recorded as an executed override.

Core dependency: expose existing validated `ResolutionValidationContext.groundedAuthority` read-only to ER, retaining identical B2/N10 semantics and v1 wires. N1 indexed component validator deferred because 5B validates whole constraints once and assigns no groups. N2/N4/N5/N7/N8/N9 are addressed as runtime policy/input/diagnostics/audit/manifest behavior where applicable; N3 existing v1 enum wires remain pinned. Full start source hashes and authority limitations in `5b-baseline.json`; previous handoff archived in `history/5a-final-handoff/`.

Stop after complete 5B verification; give full copy-paste reviewer prompt. Never launch external reviewer. Wait for returned verdict and explicit 5C authorization.


### 5B demonstrated source-link grounding dependency — owner agreement

The independent test owner found that preferred DOI X plus retained DBLP electronic-publication link to DOI Y could otherwise accept X while losing Y from downstream constraints. Original plan §8.1 explicitly requires retaining disagreements from original source links. Domain and ER owners agreed, and coordinator approved, a narrow extension: only Work.source DBLP and sourceLinks field name exactly `ee`; http(s) URLs on exact `doi.org`/`dx.doi.org`, or `arxiv.org` with `/abs/` or `/pdf/`, provide declared publication identifiers after existing StableIds normalization. Preserve all canonical values and contradictions; arXiv version-to-base behavior remains explicit. Recognized resolver links with malformed tokens, userinfo, port, query or fragment fail closed. Other fields (`url` may be a TOC/backlink), arbitrary hosts/names, author/provenance links remain weak observations. No generic URL becomes authoritative; no wire/StableIds formula changes. Domain owns core implementation and feature tests; ER consumes the same accessor; tester adds independent conflict/constraint cases. This is a proven 5B dependency beyond the initial visibility-only change; initial narrower scope statements above are historical.


## Subphase 5B repair work order after external review

The user returned REQUEST-CHANGES with B1/B2 blockers and ten nonblocking findings. The complete report is preserved in review.md and evidence/5b-repair/external-review.txt. All 170 reviewed source hashes matched before repair; history/5b-initial-review retains the exact prior handoff. Current branch/HEAD remain phase-5 / 4ac236fcb01825b73635fa4c762a35bed4b362cd; changes remain uncommitted.

Domain owner repairs B1 by grounding recognized literal DOI resolver suffixes with the same existing StableIds semantics Phase 4 accepted, without decoding or dropping suffix characters. Existing contradictory values remain explicit. A bound raw-link/fact accessor supplies ER audit catalog semantics without duplicating DOI parsing. ER owner repairs B2 by comparing venue/affiliation only within comparable representations, using explicit unavailable reasons; feature and policy versions change to v2. Independent tester first authors executable regressions against unchanged production, including a real Hadoop-prepared synthetic completed-run bridge. No original source schema, StableIds formula, Hadoop production or dataset acquisition changes are authorized.

Related bounded fixes: disable the unsafe default bibliographic shortcut pending a fuller policy, isolate CLI input/output/cache paths, validate reason/outcome consistency, make the identifier catalog agree with grounded electronic-publication facts, and retain empty normalized names as unavailable. N-2 performance work, N-8 quota release and N-9 staging/race handling remain disclosed follow-ups. N-7 same-publication researcher limits become an explicit evaluation stratum. N-10 receives readable forward-looking summaries; earlier review/history is preserved.

Owners remain /root/phase5b_domain (core), /root/phase5b_er (ER), /root/phase5b_test (tests). Coordinator alone assembles evidence. Tests/builds remain serialized, and production repair waits for captured red regressions. Stop after fresh targeted/full gates, real-input reruns and a complete external recheck prompt. No reviewer launch, 5C work, acquisition, live call, commit or push.


## Subphase 5C authorization and bounded work order — 2026-10-16

Human advancement, verbatim:

> alright let move to phase 5c

The coordinator observed a clean working tree on `phase-5` at `c8342d25ba04dede26af10bedc5a76691824d1ca`, the user-created 5B commit. All 174 files in the reviewed 5B source freeze matched. `5c-baseline.json` binds committed starting inputs; `history/5b-final-handoff/` retains the previous diff/freeze/inventory/prompt. External 5B APPROVE and explicit human approval remain in the existing reports.

Authorized scope is original plan §§10–14 Subphase 5C only: bounded source acquisition/provenance, real candidate population, score-blind grouped development/held-out split and review queue, self-contained local browser tool/guide, strict annotation/checkpoint import, evaluator implementation checked with synthetic hand-computable labels, deterministic replay, independent browser/integration tests and fresh `sbt check`. Target is 40 development + 200 held-out initial real reviews, 60 reserve candidates when feasible. No actual labels are fabricated or imported as human evidence, and final label-dependent evaluation remains future scope.

The user explicitly instructed all remaining 5B nonblocking issues to remain unfixed. Preserve their historical descriptions, do not opportunistically repair or retune matching policy. If an issue prevents the authorized current deliverable, report exact evidence and route the dependency before widening repair scope.

Native delegated owners: `/root/phase5c_dataset` writes only `datasets/**`; `/root/phase5c_er` writes only `modules/entity-resolution/**`; `/root/phase5c_test` writes only `tests/**`. Coordinator writes only phase-05 evidence and performs serialized existing CLI/build orchestration. Owners may not delegate. No reviewer is launched.

Acquisition uses the original bounded proposal: DBLP ≤600, OpenAlex ≤800, Crossref ≤600, ORCID ≤60 ingestion records, aggregate ≤2060; ≤2400 HTTP attempts within per-source caps; ≤256 MiB transferred; ≤75 minutes; concurrency 1, at most 1 request/second, 20-second request timeout, at most 2 retries within budget. CS distributed systems/data engineering 2018–2024, repeated authors, difficult negatives and independent leakage groups; existing source portfolio only. No full corpus, paid service, credentials, AWS or live model calls. Actual shortfalls are reported rather than disguised as sufficient reviews.

Stop after 5C gates and hand back complete external reviewer prompt. No 5D provider work, actual human labeling, final held-out evaluation, Phase 6, commit or push is authorized by this advancement. User runs the reviewer; returned verdict and explicit advancement required before 5D.


## Subphase 5C B1/B2 repair authorization

User returned external REQUEST-CHANGES (2 blockers, 8 nonblocking findings) and explicitly instructed:

> fix the blockings bugs first for me

Complete verdict is retained in review.md and evidence/5c-repair/external-review.txt. Before repair, all 509 reviewed source hashes matched; history/5c-initial-review/ preserves six prior handoff artifacts. 5c-repair-start.json binds the starting dirty5C tree at unchanged HEADc8342d25ba04dede26af10bedc5a76691824d1ca.

Scope: B1 separates immutable annotation population/evidence/split bindings from mutable prediction policy/config/prompt/model/code metadata, with independent before/after tests. B2 retains exact required completed preparation bytes outside ignored target, manifest-bound, and proves Scala input/candidate replay. No nonblocking repair is authorized. Dataset engineering owns retained prepared population material in existing datasets/** territory; this routes within the established artifact class and does not amend the constitutional ownership map or invent a human ratification.

Native owners remain /root/phase5c_er (ER), /root/phase5c_dataset (datasets), /root/phase5c_test (independent tests); coordinator owns phase evidence and serialized builds. No agent delegates or launches a reviewer. Capture two failing B1 regressions before ER production repair; then targeted gates, actual durable reload, regenerated real queue/replay, fresh sourcefreeze/fullcheck and user-launched recheck prompt. Preserve previous evidence and every original annotation; real human labels remainzero.

No new acquisition, source normalization change, matcher threshold tuning, live provider call, 5D/5E work, commit or push. N1–N8 and earlier accepted nonblocking findings remain documented/unfixed; a minimal B1 adapter CLI acceptance check is part of blocker closure, not a general N4 repair. Stop after repair handoff; user returns verdict and explicitly authorizes later advancement.


## Approved 5C bounded pre-commit cleanup

The user supplied external APPROVE closing B1/B2 and requested the bounded work order preserved verbatim in evidence/5c-precommit/user-work-order.txt. No 5D authorization, source/logic change, reviewer launch, commit or push is included. .gitattributes is explicitly assigned to build-engineer. Coordinator replaces only the four named giant diffs with exact-regeneration manifests; v1/v2 and the pre-repair queue/split remain unchanged pending a separate decision. Test-engineer performs a real-queue load-only check with zero label clicks; ER owner verifies the optional one-line guide warning. One final sbt check runs on the updated frozen tree, then final size/commit-message handoff and stop.


## Approved 5C lean packaging before commit

User explicitly approved optional lean cleanup: archive v1/v2 duplicate payloads and the old pre-repair queue/split outside the repository and target, SHA-256 verify every archived file before removal, retain original v1/v2 population manifests and compact archive manifests, audit dependencies first, update active README validation commands, widen build-owned .gitattributes byte-preservation rules, run v3/prepared validators and all Python dataset tests, then one sbt check and updated freeze/inventory. No source logic, data-content, labels, commit/push or 5D changes.

Dataset owner /root/phase5c_dataset owns dataset archival and dataset docs; coordinator owns historical evidence archival/current handoff/packaging recipes; build owner /root/phase5c_precommit_build owns .gitattributes; ER owner /root/phase5c_er audits runtime references and updates only its README. Original historical reports and human decisions remain unchanged; new notes identify archival. All archive writes use native sandbox authorization for the explicitly chosen durable Documents/ScholarChain-archive/phase5c location.


## Authorized Subphase 5D — real-provider checkpoint and human review

User work order, verbatim: “alright please do 5d for me. Ask me questions if you have any”

User provider/model selection, verbatim: “Let use openAI gpt 6 luna”

5D starts from clean branch phase-5 at commit 61d32a38eaad5b2fc352acf0b7f85f3815c2336d (completed 5C). This authorizes provider-specific OpenAI gpt-6-luna adapter implementation, offline owner/independent tests, human-review handoff and imports of user-provided annotation batches. Live calls still require concrete sanitized request, explicit numerical request/token/spend approval, runtime credentials and passing offline gates. No credentials may be read from files, printed or committed. The live development/demo run must exclude locked held-out tasks and leave the blind page unchanged. No policy calibration, held-out evaluation, additional acquisition, deferred unrelated repairs, reviewer launch, commit/push or 5E is authorized. Existing one-writer owners remain: ER modules/entity-resolution/**, independent tester tests/**, dataset datasets/** only when actual human batches exist, coordinator phase evidence. No actual human label or live-provider result is inferred.


### 5D numerical live-call authorization

User question, verbatim: “May ScholarChain make up to 10 GPT‑6 Luna API attempts for the 5D test, spending at most $1? This uses the token limits described above; it does not replace your human labeling.”

User answer, verbatim: “Yes, approve the $1 test”

Referenced numerical proposal is retained in evidence/5d/proposed-live-budget.json: 10 total attempts including retries, at most1 retry per pair, sequential concurrency1,1,000,000input tokens total,40,960output tokens total,4096output tokens per attempt,60seconds per attempt, standard OpenAI gpt-6-luna, maximum$1.00USD. This authorizes only the bounded development/demo pilot after passing offline checks, with naturally eligible real evidence and runtime credentials. It does not authorize held-out demo calls, new acquisition, policy tuning, later phases or substitute model output for human labels.


### 5D bounded development/demo supplement authorization

User question, verbatim: “To find a suitable live-test pair, may I reuse up to 14 already downloaded records and, if needed, fetch up to 30 additional public OpenAlex records? The fetch would stop at 20 web requests, 16 MB or 10 minutes, whichever comes first, with no paid data service. Your existing 240-review queue stays unchanged, and anything overlapping held-out groups is excluded before scoring.”

User answer, verbatim: “Approve this bounded demo supplement”

Exact proposed caps/provenance/admission constraints are retained in evidence/5d/demo-evidence-proposal.json and user-supplement-approval.json. This authorizes a separately manifested demo-only supplement, unchanged normalization and locked-held-out component exclusion before scoring. It does not authorize modifying the frozen v3 population, prepared input, queue/split, labels, thresholds or feature policy. Stop on bounds or access refusal; no credentials, paid fallback or silent expansion.


### 5D human-review prerequisite status

Asked whether any original human-review checkpoint JSON files had been saved, the user replied verbatim: “Not yet”. The coordinator records zero provided/imported real human annotations. The technical implementation checkpoint does not substitute synthetic tests, model output or browser fixtures for these reviews. No human acceptance is inferred.


## 5D B1/B2 repair authorization

User instruction, verbatim: “only fix all blockings bug for me ignore the non-blockings. Then return for me a reviewer prompt so I can copy and paste it to my reviewer”. The user subsequently supplied the missing blocker sections, preserved as received in evidence/5d-repair/external-review.txt and review.md. Only B1 credential preflight before reservation/dispatch and B2 correct demo-only retention provenance are authorized. N1–N8 are not a separate repair work order. B1's required no-credential-echo behavior necessarily shares the same credential validation boundary discussed in N2; this is not a separate nonblocking project.

Owners: ER modules/entity-resolution/**, dataset datasets/**, independent tester tests/**, coordinator phase evidence. Capture executable credential failures on reviewed production before ER repair; preserve uncertain-dispatch accounting and all original approval limits; no real credentials, network/model calls, new acquisition, label/policy changes, reviewer launch, commit/push or 5E. All retained data and original 5C evaluation manifest must remain byte-identical. After targeted tests, validators and fresh frozen sbt check, paste the full read-only recheck prompt in chat and stop. No prompt text file is created or restored.


## 5D actual human-reviewed batch import authorization

User stated “alright I did all of them” after reviewing the twelve Markdown batches; coordinator read-only verification found 240 valid task selections, 83 Same /149 Different /8 Uncertain,17changes from AI drafts. User explicitly authorized the proposed next steps with “alright can you do that for me”: convert/import the confirmed decisions, preserve original batches and AI-assisted provenance, report uncertainty/remaining needs, and assess the live-demo prerequisite. This remains5D; no5E,held-out prediction/evaluation,policy tuning,newacquisition or modelcall is authorized by this import. Earlier paidpilotnumerical limits remain unchanged.

Dataset owner creates an exact original-batch archive, conversion provenance and strict checkpoint under datasets/**; coordinator invokes the unchanged importer and records execution receipts. Source Markdown/AI drafts remain immutable; final notes may contain actual human comments and explicit AI-assistance disclosure, never AI rationale presented as Danny's own words. Original decision timestamps were not captured; conversion time is disclosed rather than invented as review time. ER owner assesses only existing live-readiness evidence without seeing label values; no source edits or newdatarequests. Original human gate/acceptance files are not rewritten.


## 5D additional bounded demo search authorization

User explicitly replied “Approve this additional bounded search” to the complete question retained in evidence/5d-followup-demo/user-approval.json: at most30newOpenAlexrecords,20HTTPattempts,8MiB,5minutes,no paiddata/credentials, no label-based selection, frozenreviewsetunchanged, exactheldoutoverlapexclusionbefore scoring. This is a separate bounded stage, not a reset of the prior search receipt. Original $1/10attempt model approval and5D-only stoppingboundary remainunchanged. Dataset owner implements source/provenance; rootsoleHTTP/Hadoopexecution; ERowner supplies read-only canonicaladmission strategy without readinghumanlabels. No5E,predictionevaluation,policychange orcommit/push.


### Additional search implementation adjustment

The two canonical metadata screens found no suitable existing author seeds, with zero new HTTP requests. The exact user approval allows one public OpenAlex search within the recorded bounds; the coordinator’s initially narrower existing-seed strategy is replaced by two fixed public CS topic queries (five works each), then at most four author-neighborhood queries (five works each). Selection uses observed metadata only, never labels or comparison scores. Provisional discovery selection is not canonical held-out clearance; final combined-input transitive held-out exclusion is mandatory before scoring. All requests share the same 30-record/20-attempt/8-MiB/300-second allowance, without pagination, refill or timer reset. Exact implementation rationale is in evidence/5d-followup-demo/strategy-update.json. No user decision or prior report was rewritten.
     1	
     2	
     3	## 5D decision-attribution statement — 2026-10-20
     4	
     5	After an independent review noted that all 17 differences from the AI drafts coincide with "Source check by Claude ... not Danny" Comments, and that five such Comments say "Switched same -> uncertain", the user stated, verbatim: “it was actually from me but claude mistaken but under it decision, now I want you to change all of them under my decisions”. Asked to route the edit through the owners, the user replied, verbatim: “I want you to change it, that's fine”. The user thereby directed the reviewing session to record the attribution itself; this is a disclosed departure from reviewer/implementer separation. Scope: record that danny set all 22 final checkboxes and Claude performed only the external source checks. No label value, checkpoint, validated derivative, provenance file, conversion report or source byte may change. No 5E, evaluation, acquisition or search re-run is authorized by this statement.


## 5D external B2 discovery-ordering repair and corrected search

The user returned external blocker B2: topic discovery's explicit publication_date:asc displaced relevance, returning unrelated repository records and undermining the search checkpoint. Only this blocker repair, its regression tests, append-only root-cause disclosure and verification are authorized. Existing records/manifests/executed scripts and all human decisions/attribution remain unchanged. Dataset engineer owns datasets/**; coordinator owns phase evidence and serialized execution.

The user explicitly answered “Approve this corrected bounded rerun” to the full question retained in evidence/5d-search-repair/user-rerun-approval.json. The new stage is capped at 30 returned records including exclusions, 20 HTTP attempts, 8 MiB and 300 seconds without credentials or paid data. Preserve cumulative counters from the earlier stages; apply canonical transitive held-out exclusion before scoring. Original $1/10-attempt model approval is unchanged, and no eligibility or provider evidence is guaranteed. No reviewer, label/policy/queue change, 5E, commit or push is authorized.

The reviewer also refers to a B1 attribution record. Existing decision-attribution.v1.json and its self-attested attribution remain protected; the coordinator requested the missing B1 finding rather than inventing its acceptance conditions.


### B1 attribution clarification for the B2 repair gate

The user confirmed that B1 attribution changes were already applied at their direction in the reviewing session, a disclosed departure from reviewer/implementer separation. Their full clarification is retained in evidence/5d-search-repair/b1-user-clarification.json. No further B1 implementation is requested. Preserve the full current label tree unchanged; include its README and decision-attribution.v1.json in the refreshed freeze and fresh independent B1/B2 recheck. The future 5E with/without-22-pair analysis remains a documented nonblocking later requirement, not current implementation.


## 5D focused Michael Benedikt public-metadata search authorization

The user asked how to obtain the pending real-model demonstration and then explicitly replied “go ahead” to the complete focused-search proposal retained verbatim in evidence/5d-focused-demo/user-approval.json. They subsequently instructed “pleaes continue”. This authorizes reuse of the existing development publication DOI 10.1145/3299887.3299889 and one new public OpenAlex metadata search around its observed author name Michael Benedikt. Maximum 30 returned metadata records TOTAL, including author lookup profiles, publication rows, duplicates and exclusions; 20 HTTP attempts including retries, 8 MiB and 300 seconds, with no credentials or paid data. Prior cumulative acquisition history is preserved. No label-based selection or matching-policy/queue change. Canonical full-component held-out exclusion is required before any scoring.

Dataset owner writes a new standalone script and tests in datasets/**; coordinator executes the bounded HTTP command, unchanged Hadoop, canonical admission, offline gates and any naturally eligible existing approved model pilot. The first dataset owner hit a usage limit before completing tests and stopped; /root/phase5d_focused_dataset replaces it as the sole writer for this new dataset work. Existing ER owner supplies read-only execution advice only, without label access. No ER production changes or nonblocking repairs are authorized.

The existing $1/10-attempt numerical model approval, model/provider and approval-scoped budget/cache remain unchanged. No call occurs without eligibility, passing offline checks, sanitized request preview and runtime credential preflight. Runtime keys are never read from files, printed or stored. No 5E, policy calibration, reviewer invocation, commit or push. Stop at the stage bounds without fallback, refill, identity fabrication or masking observed IDs; a suitable pair is not guaranteed.


## 5E limited evaluation authorization

The user replied “yes” to proceeding with Phase 5E evaluation of the existing deterministic/fake configuration, explicitly keeping real-provider evidence pending and overall Phase 5 acceptance open. Exact scope and preceding message are retained in evidence/5e/user-authorization.json. Preserve completed AI-assisted human choices, frozen population/split and matcher/policy/config; no live calls, further acquisition, Phase 6, commit/push or manager-launched reviewer. Produce source-bound predictions before scoring, development-only sensitivity, held-out metrics, with/without 22 externally assisted pairs, replay evidence, fresh deterministic gate and a copy-paste external review prompt (no prompt text file).


## Final targeted real-provider attempt after limited 5E review

The user returned an independent APPROVE for limited 5E and the implemented changes (zero blockers, six nonblocking observations), explicitly leaving real-provider evidence and overall acceptance open. The user instructed that nonblocking findings need no repair. The user then replied “alright do it” to one final targeted attempt with unchanged rules and existing $1 budget. This does not authorize Phase 6, commit/push, changes to labels, policy or approved evaluation. Preparation starts offline; new public acquisition waits for explicit numerical limits. Summary-only review receipt: evidence/5d-final-attempt/prior-review-summary.json; start/protected snapshot: start.json.


### Final Rice-team acquisition numerical approval

The user explicitly answered “Approve this final bounded attempt” to the question retained in evidence/5d-final-attempt/user-approval.json: at most 30 public OpenAlex work rows including duplicates/exclusions, 20 HTTP attempts, 8 MiB and 300 seconds, no data credentials or paid data. Query only the two already observed author IDs for Luis Leopoldo Perez and Christopher Jermaine, fixed 15 rows each, citation-count descending, years 2018–2024, no refill/fallback. Exact old seed bytes are discovery proof only; ingestion uses fresh response observations with stage-specific snapshot/date. Preserve cumulative acquisition counters. Apply canonical transitive held-out exclusion before scoring. Existing $1/10-attempt model approval remains unchanged and requires natural eligibility, passing offline checks, sanitized preview and credential preflight. Preserve the approved 5E evidence and all labels/rules. No nonblocking repairs, Phase 6, commit/push or reviewer launch.


## Versioned adjudication eligibility revision authorization

The user replied “alright can you do it now” after the coordinator proposed handling implementation, tests, a bounded live run and updated evaluation, while retaining the existing $1 / 10-attempt approval, preserving all 240 human reviews and leaving independent review and final acceptance to the user. This authorizes a focused, separately versioned model-request eligibility policy using development-only evidence, with automatic acceptance and identifier-conflict protections preserved. No new source acquisition or unrelated nonblocking repairs. Preserve original policy resources, labels, approved 5E artifacts and existing human-gate.md byte-for-byte. Keep disabled/legacy behavior reproducible. Fresh predictions precede label-aware evaluation; no threshold selection from held-out results. Later measurements on the previously exposed held-out set must be explicitly described as reused-set/descriptive validation, not a fresh unseen test. Provider calls additionally require passing offline gates, a sanitized qualifying preview, original budget/approval binding and runtime credential preflight. No reviewer launch, commit/push, Phase 6 or overall acceptance. Exact receipt: evidence/5d-eligibility-revision/user-authorization.json.


## Safe live response diagnostics continuation — 2026-10-21

The user returned a real terminal run with ADJUDICATION_FAILED for both eligible pairs, cumulative attempts 2 and observed cost upper bound 2772 micro-USD. The approved demonstration remains the active work order. The coordinator routes a narrow response-diagnostic repair to the ER and test owners: preserve strict response/identity/citation validation, model, policy, credentials isolation, numerical approval and cumulative ledger; expose only finite sanitized validation categories and bounded hashes/counts/booleans; no raw response text, provider-error body, rationale, arbitrary exceptions or key values. Narrow the next explicit user execution to one eligible pair. Prior outputs and labels are immutable. No further API request is made by the coordinator during diagnosis. Fresh offline gates precede another user-launched attempt. No reviewer, commit, push, acceptance or Phase 6 is authorized. The exact earlier content rejection is unknown because that output was not retained.


## User-returned successful live run — 2026-10-21

The user returned live-resume-20261021T201707Z with VALIDATED_LIVE, cumulative attempts 4 and costUpperBoundMicrousd 5576. The coordinator verified the retained successful response, cache and bindings offline; it did not make another API call or access .env. This is observed implementation evidence, not a human acceptance decision. The next gate is the user-launched independent review.


## Explicit human Phase 5 acceptance — 2026-10-21

The user supplied the independent checkpoint APPROVE, instructed “ignore all non-blockings bugs. Are they good now?”, and then replied “I approve them” after the coordinator explicitly identified human Phase 5 acceptance with the documented limitations as the remaining decision. Record that new human decision append-only, preserve the full external report, and defer all nonblocking findings. No implementation, new tests/calls, budget reset, commit, push or Phase 6 is authorized by this documentation step. Exact receipt: evidence/phase5-human-acceptance/human-acceptance.json.

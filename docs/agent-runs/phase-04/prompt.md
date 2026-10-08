# Phase 4 work order

STATUS: the orchestrator is executing this order. Human acceptance is not recorded here.

Repository: `/Users/danny/Documents/UIC/CS441/ScholarChain`

Base commit at start: `742aa0f209284eed257b8d070a40f8136b0fb543` (`Record Phase 3 human acceptance and accepted commit`). Parent implementation: `52c32063311d0c0eacea69ad311b44132f34f0c4`. Branch: local `main`. Do not commit or push.

Tools: Codex and Cursor. Preserve Claude Code compatibility and required `.claude` artifacts. `.claude/agents/*.md` describes roles; it does not register subagents or enforce permissions in Cursor.

## Human decisions for this run

- Subagent models: `domain-engineer` and `hadoop-engineer` use Grok 4.7 High (`grok-4.7-high`). `build-engineer`, `test-engineer`, and `infra-engineer` use Composer 2.5 Fast (`composer-2.5-fast`). `code-reviewer` uses Grok 4.7 High in a fresh context.
- Approval mode: subagents inherit this session. The CLI config `approvalMode` is `auto-review`.
- Stay on local `main`. No branch, commit, or push.
- Local MapReduce outputs go in gitignored `target/phase4-runs/`. Representative records, counters, rejects, and replay commands are copied into `docs/agent-runs/phase-04/`.
- Small expected-output fixtures may be committed under `tests/**` only when a deterministic assertion needs them. `test-engineer` owns those files.
- `dataset-engineer` is unused unless a concrete `datasets/**` dependency appears. Do not modify samples to make tests pass.

## Objective

Implement the complete local Hadoop preparation pipeline required by Phase 4 and the Detailed Hadoop requirements in the assignment README (`https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md`).

Cover DBLP extraction, normalization of OpenAlex, Crossref, and ORCID, exact-identifier indexing and join preparation, bounded blocking and deterministic candidate features, publication teams, authorship, coauthor-pair candidates, and Spark-ready exports.

Execute at least two genuine Hadoop MapReduce jobs. The full required pipeline must work. Two jobs are the minimum execution gate, not permission to omit stages.

Use Scala 3 with Hadoop APIs. LocalJobRunner is acceptable for bounded local execution. Production processing must use Hadoop jobs rather than driver-side collection loops substituted for distributed stages.

Do not implement final probabilistic identity decisions, LLM adjudication, Spark analytics, storage adapters, or runtime services. Matching outputs prepare evidence for Phase 5.

## Owners

| Role | Territory | Model |
| --- | --- | --- |
| `domain-engineer` | `modules/core/**` | Grok 4.7 High |
| `build-engineer` | `build.sbt`, `project/**`, packaging, `.gitignore` | Composer 2.5 Fast |
| `hadoop-engineer` | `modules/hadoop/**` | Grok 4.7 High |
| `test-engineer` | `tests/**` | Composer 2.5 Fast |
| `infra-engineer` | `scripts/**` for the bounded EMR smoke script | Composer 2.5 Fast |
| `code-reviewer` | read-only review delivered to the orchestrator | Grok 4.7 High, fresh context |
| orchestrator | `docs/agent-runs/phase-04/**` | this session |

Subagents must not spawn or invoke other subagents. One writer per path. No overlapping sbt runs or shared output directories.

Do not change ownership rules or constitutional files (`AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `docs/agent-runs/README.md`, `.claude/**`).

## Dataset inputs

Use the committed samples as the first real end-to-end input:

- `datasets/samples/dblp/linked-records.xml`
- `datasets/samples/openalex/works.jsonl`
- `datasets/samples/crossref/works.jsonl`
- `datasets/samples/orcid/records.jsonl`

`datasets/samples/SHA256SUMS` and `datasets/dataset-manifest.yaml` are authoritative. The accepted DBLP sample uses an empty internal DOCTYPE subset (`<!DOCTYPE dblp []>`).

## Contract constraints routed to domain-engineer

Reuse `StableIds`, `TextNorm`, `CoreJson`, `DomainValidation`, `WorkRecord`, `AuthorMention`, `PublicationTeam`, `AuthorshipRecord`, `CoauthorPairCandidate`, `RunManifest`, `Venue`, `Institution`, `Topic`, `ObservedIdentifier`, and `GraphEdge` where validation can be satisfied without an identity decision.

`Records.scala` has `MatchDecision` and no `MatchCandidate`. Add shared contracts Hadoop needs. Do not let Hadoop invent a competing domain model.

Preserve `scholarchain.config.v1` and accepted wire examples. Hadoop limits belong in a new additive config type and schema version, not a required field on `ScholarChainConfig`. No compiled-in AWS bucket, endpoint, or account default.

`MatchCandidate` carries deterministic features and both source observations. It is not a `MatchDecision` and must not contain an accept/reject identity outcome.

Derived team, authorship, and pair records use `DomainValidation.check(record, work)` or an immutable `WorkValidationContext`. `checkStructure` is not full source validation. No process-global mutable bibliography.

## Build constraints routed to build-engineer

`hadoop-client` 3.3.6 is `Provided`. `sbt hadoop/run` and a plain packaged JAR do not contain Hadoop. Local launch must use a classpath that includes Provided dependencies. EMR launch uses the thin job JAR plus the cluster Hadoop classpath.

Independent tests under `tests/**` must be executed by `sbt check`. `test-engineer` owns the test sources. `target/` already ignores `target/phase4-runs/`.

## Pipeline behavior

Configurable limits, validated before launch: record size, XML/entity expansion, reducer count, candidate block size, candidate pairs per block, author-team size and pair expansion, and local sample bounds.

Oversize handling must be explicit. Do not silently truncate a team or block and call the result complete. Bounded memory and counters. Duplicate and conflicting source records are distinct deterministic outcomes.

Rejects keep schema version, source locator and snapshot, processing run, stage, reason code, and a bounded diagnostic excerpt or hash. Parse failures are retained when a valid domain record cannot be constructed.

Output roots are configured, partitioned by snapshot and run. Never recursively delete an existing user output directory. Never mix partial output with a successful run. Reuse an output path only when input and configuration identity match and completion is verified; otherwise fail and require a new output path.

Logical-record determinism. Do not require compressed files to be byte-identical when headers differ. State which run metadata is excluded from equivalence comparisons.

Safe combiners only where the operation permits them. Document partitioning and compression.

DBLP streaming reader: supported publication types, unsupported elements, split-edge InputFormat tests, compressed-XML processing documentation, no full-dump load into driver or mapper memory, bounded local entity declarations, no arbitrary external DTD retrieval, file access, or entity expansion. Preserve title text across inline markup and every author position, including repeated names. Do not invent missing values.

OpenAlex and Crossref: native source keys stay distinct from preferred work IDs. Preserve author identifiers, enrichment relationships, disagreements, and abstract text or a reproducible local reference that the pipeline emits or that already exists.

ORCID: public researcher/activity record, not a fabricated publication. Preserve declared identifiers, affiliation evidence, and work references. Keep ROR and Ringgold distinct. A linked DOI or observed ORCID is evidence for later resolution, not proof of authorship or a cross-dataset merge.

Unknown or malformed identifiers must not silently become authoritative IDs. One DOI-based work ID may occur in several source observations. Keep source, sourceRecordId, and datasetSnapshot. Unresolved author mentions stay unresolved. Do not assign canonical researcher identities from names. When ordering pair endpoints, move each endpoint's ordinal with its ID.

`RunManifest` and outputs bind input snapshots and checksums, processing run ID, configuration fingerprint, and schema and transformation versions. Source metadata stays distinct from processing-run metadata.

## Gates

- `sbt check` on Java 17 when that toolchain is installed. Record actual Java, sbt, Hadoop, Scala, and agent model versions.
- Complete bounded local pipeline over all four real samples.
- Two equivalent runs compared as logical output.
- At least two actual MapReduce job completions, with retained counters.
- Independent adversarial tests under `tests/**`, wired to a documented command.
- Job packaging and a replayable launch command.
- Dataset manifest validation and sample checksums. Do not download a full corpus.
- Fresh read-only `code-reviewer` verdict: APPROVE or REQUEST-CHANGES. Each finding has severity, file and line, evidence, impact, required owner, and whether it blocks Phase 4.

## EMR script

`infra-engineer` authors a bounded smoke-run script that requires explicit existing AWS resources and paths, uses the verified packaging contract, enforces sample and job limits, exposes dry-run behavior, and produces traceable job and output locations. It must not create infrastructure or widen permissions.

Validate syntax and dry-run locally. Do not submit EMR steps, upload data, create resources, apply Terraform, or deploy. An unrun EMR script is unverified in AWS.

## Evidence

The orchestrator assembles:

- `docs/agent-runs/phase-04/prompt.md`
- `docs/agent-runs/phase-04/owner-report.md`
- `docs/agent-runs/phase-04/test-report.md`
- `docs/agent-runs/phase-04/review.md`
- `docs/agent-runs/phase-04/repairs.md`

Use the fields in `docs/agent-runs/README.md`. Do not fabricate approval, a commit SHA, or successful execution. Do not write `human-gate.md` or `accepted-commit.md`. Do not begin Phase 5.

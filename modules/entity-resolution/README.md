# Entity resolution — Phase 5A interface agreement

This module currently contains design artifacts only. Phase 5A adds shared resolution contracts in
`core`; it does not implement a matcher, CLI, provider, review page, label importer, or evaluator.
The examples in [contracts/](contracts/) are proposed module-local JSON documents. Their numeric
values are illustrative, uncalibrated, and not production defaults. No example is source evidence,
a human annotation, or a live model result.

The user authorized a distributed systems/data engineering population and **40 development plus
200 held-out reviews**. Existing records do not supply that evaluation population. Dataset readiness
and the bounded expansion proposal are recorded in the Phase 5 owner report. Future population
artifacts belong to `datasets/entity-resolution/`; acquisition waits for 5C.
Additional reviews may be needed when human labels are uncertain or per-type binary coverage is poor.
The dataset owner's proposal targets 2018–2024 records from SIGMOD/PVLDB/VLDB/ICDE and
SoCC/Middleware/ICDCS/OSDI/SOSP, with a 300-pair eligible pool to support 240 initial reviews and
60 reserve pairs. Those are proposed acquisition/sampling targets, not observed dataset sufficiency.

## Shared boundary

The domain and entity-resolution owners agreed on `scholarchain.resolution.v1`. Use the actual
`ResolutionContracts.scala`, `ResolutionValidation.scala`, their tests, and serialized core fixtures
as the authoritative shared API; this module does not define competing endpoint or decision types.
Existing `WorkRecord`, `AuthorMention`, `MatchCandidate`, `MatchDecision`, `StableIds`, and
`prep-features-v1/v2` remain unchanged.

Concrete shared serialized examples (synthetic contract fixtures, not resolution results):

- [Work pair](../core/src/test/resources/wire/resolution-work-pair.json) and
  [researcher pair](../core/src/test/resources/wire/resolution-researcher-pair.json).
- [Work decision](../core/src/test/resources/wire/resolution-work-decision.json) and
  [researcher decision](../core/src/test/resources/wire/resolution-researcher-decision.json).
- [Accepted link](../core/src/test/resources/wire/resolution-accepted-link.json) and
  [grouping constraints](../core/src/test/resources/wire/resolution-grouping-constraints.json).

An observation is `(source, sourceRecordId, datasetSnapshot)`. Lookup by `workId` alone is forbidden:
independent source records may already share a DOI-derived ID without any identity decision.
The closed endpoint families are:

| Endpoint | Compared entity | Required context |
| --- | --- | --- |
| `Work` | work | Exact source observation and its validated `WorkRecord` |
| `OrcidWorkActivity` | work | Exact ORCID activity observation, with `activityKind=Work`; optional observed work ID must agree |
| `Mention` | researcher | Exact parent work observation, containing the actual mention |
| `OrcidProfile` | researcher | Exact ORCID profile observation and matching validated ORCID |

An ORCID work activity supplies weak bibliographic evidence, never a complete author list or
publication team. Employment, education, distinctions, and other nonwork activities remain evidence;
a bibliographic candidate involving one receives an explicit unsupported-endpoint skip in 5B.
Missing observations and dangling references are errors, distinct from a known unsupported kind.
Identical duplicate payloads may collapse; conflicting payloads at one observation key must fail.

`ResolutionIds` computes canonical endpoint and unordered pair IDs using versioned compact JSON
identity tuples. A pair includes entity type and snapshots. Carried preferred work IDs and ORCIDs
are checked against context, not used to collapse source observations. Reversed pairs and repeated
blocks must not inflate comparisons or review counts. Every contributing candidate ID and block key
remains attached. Researcher pairs must come from real mentions/profiles, including bounded
cross-publication comparisons; a bibliographic candidate is never directly a researcher pair.

`ResolutionDecision` wraps the unchanged `MatchDecision` with the typed pair, candidate/block refs,
feature availability/evidence, final path, explicit confidence semantics, policy/config/input hashes,
UTC decision timestamp, and optional adjudication audit. Legacy source/target IDs in this wrapper
are snapshot endpoint IDs. `MatchDecision.confidence` is an uncalibrated score unless calibration
evidence supports the other declared semantics. The required LLM `reportedConfidence` is separate.
When no score was produced, `confidenceSemantics=Unavailable`, `scoreUnavailableReason` is
required and the legacy required numeric confidence is `0` solely as a compatibility placeholder.
It must never be interpreted as a score, rejection or calibrated probability. An LLM decision has
one final `decisionPath=LlmAdjudicated` and preserves the unresolved pre-LLM outcome, optional
score and scored/bibliographic path in `adjudication.preAdjudication`.
Unknown versions, invalid IDs, nonfinite numbers, mismatched refs, or wrong entity families fail
validation; parsing alone is insufficient. Shared contracts do not authenticate evidence or prove
that a provider ran.

`ResolutionAcceptedLink` exports pairwise accepted links and their decision/policy/run provenance.
It assigns no canonical representative. Phase 6 must validate proposed components against
`ResolutionGroupingConstraints`: cannot-link pairs and same-namespace authoritative assertions.
`ResolutionIdentifierAssertion.namespace` uses the closed `ResolutionAuthorityNamespace` set:
`doi` and `arxiv` apply only to work endpoints; `orcid` applies only to researcher endpoints.
Only those exact lowercase wire codes are accepted. Values must already equal the output of the
corresponding existing `StableIds` canonicalizer: normalized bare DOI, unversioned bare arXiv ID,
or bare checksum-valid ORCID. Namespace aliases/case variants, noncanonical values, incompatible
entity types and version-bearing arXiv assertions fail validation. Raw arXiv versions remain source
observations; a named version-comparison rule belongs to 5B, with no implicit suffix stripping here.
DBLP and OpenAlex work native IDs remain source/endpoint bindings: different native records do
not by themselves prove different scholarly works. OpenAlex author IDs remain hypotheses.
Semantic Scholar IDs and repository URLs remain observed evidence; adding them to hard-authority
constraints waits for validated namespace meanings and canonicalizers in 5B. This narrow assertion
set preserves existing source evidence and introduces no new source types or matching algorithms.
Each assertion must also be grounded in the exact endpoint's validated source observation.
Profiles support their own bare ORCID; mentions support only that actual member's `observedOrcid`.
Works support their declared DOI/arXiv fields, a Crossref source-key DOI, and identifier roles
`doi`, `arxiv`, `openalex.doi`, `openalex.ids.doi` after trim/lowercase with `Locale.ROOT`.
ORCID work activities support declared DOI and recognized
self-related DOI/arXiv references, not related-work identifiers such as `part-of` or `version-of`.
Reference types must be exactly `doi`/`arxiv` and their relationship `self`, ignoring case/outer space.
A standalone preferred activity DOI can support grounding when no corresponding recognized DOI
reference is present; matching nonself-only reference metadata instead produces an explicit
grounding error.
Source DOI/ORCID spellings are canonicalized with existing helpers for support checks. An actual
versioned arXiv source ID supports its base only under this grounding rule; submitted assertions
still require the strict canonical base form. Unknown free-text external identifiers and arbitrary
source links remain observations, not hard-authority facts. Malformed recognized facts fail closed.

Every covered endpoint must have assertions for **all** its recognized canonical authority facts,
including an ORCID profile's own ID. Conflicting source values remain present; selecting one
convenient ID or omitting another cannot hide a contradiction from component validation. Checking
record-field consistency and this bounded fact coverage is not the 5B matching/input-bridge policy.
It does not prove that an exporter included every source observation or evidence file: whole-run
manifest completeness and source-file integrity remain separate checks. Synthetic positive test
fixtures must actually carry each asserted identifier; a test-only value absent from its record is
invalid evidence, even when its namespace and spelling are valid.
Its explicit covered endpoints include members with no identifiers; missing member coverage fails
closed rather than treating an absent constraint record as permission to merge.
Callers must supply explicit member and constraint bounds to the component validator.
The shared bounded component check is validation, not grouping. A–B plus B–C cannot override an
A–C constraint or conflicting authoritative IDs. Unresolved mentions remain available downstream.
The user assigned Phase 6 canonical group construction and deterministic representative selection
to the `spark-engineer` in `modules/spark/**`, using Phase 5 accepted links and conflict constraints.
The `domain-engineer` owns any shared contract changes. Representative selection must be versioned
and preserve the existing stable-ID authority rules; this ownership decision authorizes no Phase 6
implementation now.

## Policy and configuration contract for 5B

See [policy.example.v1.json](contracts/policy.example.v1.json) and
[config.example.v1.json](contracts/config.example.v1.json). They specify separate work/researcher
sections, explicit limits and evidence gates. They are not accepted runtime files yet.

The Phase 5 policy will be the sole effective source of thresholds, weights, source reliability,
conflict precedence, evidence gates, blocking bounds, and LLM bands. It **supersedes** the generic
`ScholarChainConfig.entityResolution` placeholders. The Phase 5 runtime document contains no copy
of those settings. The CLI will not silently load a global config or its ER environment overrides.
Explicitly supplying legacy/shared ER settings alongside the new policy is a startup error, including
any disagreement; do not choose one silently. Existing global config remains valid for other modules.
If a global config hash is retained as provenance, that does not activate its ER settings.

Future startup validation must finish before output writes or adapter calls:

- Require a supported closed schema, all required values, no unknown fields, unique feature names,
  finite positive weights, finite `[0,1]` thresholds, positive bounded resource limits, and no secrets.
- Require `0 <= reject < bandMin <= bandMax < accept <= 1` separately for both entity types.
  Reject at `score <= reject`, accept at `score >= accept` only after evidence gates; otherwise
  unresolved. The LLM band includes its two endpoints and lies strictly inside the unresolved gap.
- Apply hard identifier conflict checks before exact, bibliographic, scored, or LLM acceptance,
  and again before exporting accepted links/components. Missing identifiers are not conflicts.
- A scored decision requires available evidence. Available-feature weighted average is
  `sum(weight * value) / sum(available weights)`; zero available weight yields unresolved,
  not zero score/rejection. Missing values cannot become perfect similarities or negative facts.
- Acceptance additionally requires the configured independent evidence groups; name/initial/order
  signals are correlated and cannot count as three independent groups. A source reliability weight
  is not an independent identity fact. Failed sufficiency leaves a high score unresolved.
- Hash the complete effective policy and runtime config using an explicitly versioned canonical
  serialization; include exact file hashes in the run manifest. No compiled numeric defaults or
  implicit environment overrides. Freeze actual serialization/hash fixtures when the loader is
  implemented in 5B; shared pair-ID serialization does not change.

Proposed feature semantics for `er-features-v1` (implementation and fixtures are 5B):

| Group / signal | Formula and range | Evidence / missing rule |
| --- | --- | --- |
| identifier agreement | Exact normalized namespace/entity equality, 0 or 1 | Present comparable IDs only; hypothesis IDs never outrank direct authority |
| title | Jaccard of nonempty normalized title-token sets, `[0,1]` | Works or parent works; empty/absent input unavailable |
| name | Maximum token-set Jaccard across documented name-order variants, `[0,1]` | Actual mention/profile names; normalization is not identity |
| initials | Exact normalized surname plus compatible given initials, 0 or 1 | Missing surname/given component unavailable; correlated with name |
| author order | `1 / (1 + abs(leftOrdinal-rightOrdinal))`, `(0,1]` | Actual parent authors only; absent author list unavailable |
| author/coauthor overlap | Jaccard of observed normalized names after excluding focal mentions, `[0,1]` | Empty/incomplete evidence unavailable; never invent resolved neighbors |
| affiliation | Exact normalized ROR or conservative normalized-name compatibility, 0 or 1 | Only attached affiliation observations; absence unavailable |
| year compatibility | `max(0, 1-abs(yearA-yearB)/yearToleranceYears)`, `[0,1]` | Tolerance required in policy; absent year unavailable, not prep sentinel `-1` |
| venue | Exact validated venue ID or normalized venue label, 0 or 1 | Same-kind comparable observations required; absent venue unavailable |
| citation neighborhood | Jaccard of actual observed citation neighbors, `[0,1]` | Current preparation has no citation-neighborhood export; unavailable |
| source reliability | Explicit policy lookup per source, `[0,1]` | Scoring modifier only; no invented accuracy claim |

Missing features carry a missing reason and no value; present features carry finite values and
input evidence refs. Features use their own catalog, never additions to closed prep-features-v2.
The example policy lists only illustrative scored subsets; the full catalog, identifier authority,
normalization rules, formulas, applicable entity types and minimum gates require tested completion
in 5B before any real decision. Candidate-generation coverage is distinct from scorer accuracy.

Identifier comparison will cover DOI, arXiv, ORCID, OpenAlex work/author distinction, Semantic Scholar
work/author distinction and stable repository URLs, while preserving raw inputs and normalization
versions. DOI prefix/case and valid ORCID checksum rules must be tested. arXiv versions remain
preserved raw; comparison may ignore only a valid terminal version suffix under a named rule.
Repository normalization may lowercase scheme/host and remove a default port; it must preserve
path boundaries and identity-bearing queries. No arbitrary fetching, cross-host aliases or blanket
path/query stripping. Semantic Scholar syntax fixtures do not imply acquisition or a new SourceType.
Conflicting direct ORCIDs cannot merge through a shared OpenAlex hypothesis.

## Offline and future provider boundary

Disabled is the only proposed default mode. The example sets live request/token/spend allowances
to zero and omits provider/model selection; it grants no live authority. Fake mode is explicit,
test-only and isolated from live cache/output. Unresolved eligible cases stay unresolved when the
adapter is disabled, budgets are exhausted or validation fails. Provider/model and numeric live
limits are a 5D human decision after a representative request and passing offline checks exist.

The later strict response schema must require request/pair/endpoint identity, accept/reject/abstain,
reported confidence, bounded reasons/rationale, and citations restricted to supplied input fields.
Unknown fields, wrong hashes/IDs, fabricated refs, oversized outputs, injection instructions and
timeouts cannot accept a pair. The LLM cannot override a hard conflict or mint identifiers.
Cache identity binds every relevant input field, prompt/version/content, provider/model/version,
generation settings, policy/config and response schema. Atomic validated cache replay preserves
Fake/Live and cache-hit provenance; replay cannot masquerade as a new live call.

## Review, split and labels contract for 5C

[sampling.example.v1.json](contracts/sampling.example.v1.json) fixes the requested review allocation
and records a planning reserve rather than extra authorized reviews. Freeze the real source and
candidate population before scoring. Partition whole leakage groups before labels are used: union
shared source observations, underlying works/near duplicates, directly observed identity anchors,
and their attached mentions/pairs. Repeated snapshots do not become independent review evidence.
Conflicting identifier observations are grouping evidence for leakage prevention, not merge authority.
If groups are too connected for a useful split, report infeasibility and expand sampling; never
silently fall back to random pair splitting. Record residual undetectable identity leakage.

Aim for balanced entity coverage and usable same/different labels in each partition, plus hard
negatives, common names, missing fields and repeated authors across publications. Sampling uses
evidence strata and a fixed seed, never predictions, LLM success or label outcomes. Reserve pairs
must remain in their original group/partition. Any replacement review needs a recorded reason;
retain uncertain originals and report all counts rather than deleting inconvenient cases.

The matcher accepts neither labels nor a held-out membership file. The blind review queue shows
evidence and source refs, never scores, predictions, LLM judgments or suggested/preselected labels.
Development calibration receives only development annotations. Held-out annotations become
accessible to the evaluator after source/policy/prompt/model freeze. A new tuning cycle needs a
fresh holdout or an explicit exploratory-results qualification.

[labels.example.v1.json](contracts/labels.example.v1.json) is a synthetic revision/checkpoint
shape, not actual human work. Labels are `same`, `different`, `uncertain`; uncertain is not negative.
The future importer binds queue ID/version/hash, source population and per-pair evidence hashes,
pair/entity identity, human-entered reviewer ID, timestamps and monotonic revisions. It rejects
unknown pairs, altered evidence, mixed queues, duplicate revision IDs and conflicting revision
histories. Reviewer ID is self-entered provenance, not authentication. Preserve original human
exports; write a derived validated dataset without rewriting annotations. Save original exports
to a durable user-chosen path outside disposable `target/` and back them up.

## Proposed CLI and output layout — not implemented or runnable

One future `edu.uic.cs441.scholarchain.entityresolution.Phase5Main` will expose:

| Subcommand | Explicit inputs | Outputs / stage |
| --- | --- | --- |
| `resolve` | `--input` completed Phase 4 run, `--policy`, `--config`, `--llm-mode`, `--output` new directory | Four typed decision streams by entity, pairwise links, constraints, diagnostics/summary/manifest; 5B |
| `build-review-queue` | `--input`, `--sampling`, `--output` | Frozen blind queue, population/split manifests; 5C |
| `export-review-tool` | `--output` | Self-contained local page and guide; 5C |
| `import-labels` | `--queue`, `--labels`, `--output` | Validated derived annotations plus preserved-input hashes; 5C |
| `evaluate` | `--predictions`, `--labels`, `--split`, `--manifest`, `--output` | Per-type/path matrices, coverage, errors and provenance; 5C implementation / 5E held-out run |

Before trusting input, verify `_SCHOLARCHAIN_COMPLETE`, run manifest, schema/config/input identity,
every listed export partition, byte length and SHA-256; reject partial, missing, corrupt or unexpected
input. Use the documented snapshot/run/kind JSON framing and record resolved input hashes.
No output overwrite/reuse without matching complete manifest; write new outputs atomically and
mark complete last. Fatal config/input failures exit nonzero with explicit diagnostics. A completed
run may contain unresolved/conflict/skipped records, but summary counts must account for all inputs.
Output names are proposed: `decisions/{work,researcher}/{accepted,rejected,unresolved,conflict}.jsonl`,
`accepted-links.jsonl`, `grouping-constraints.json`, `diagnostics.jsonl`, `summary.json`, `run-manifest.json`.

The future evaluator treats ACCEPTED as positive and the other three outcomes as nonacceptance,
reports TP/FP/FN/TN and the full gold-by-four-outcome table, decisive coverage and uncertainty,
missing/invalid predictions, uncertain human labels, entity/path breakdowns and null denominators.
Recall is conditional on the candidate population unless a separate blocking-recall check exists.
Development threshold sensitivity must not tune the held-out result. No gold-set evaluation,
240 human reviews or live model run has happened in 5A.

Existing verification commands are `sbt -batch check` and `sbt -batch 'entityResolution/test'
'independentTests/test'` under Java 17. The coordinator serializes gates against a frozen tree and
reports observed results. Shared wire examples/tests belong to core; module-local runtime behavior
and its tests remain 5B/5C work. Stop after the 5A external-review handoff and wait for authorization.

# Entity resolution — shared contracts, offline runtime and Phase 5C review readiness

Phase 5A established shared resolution contracts in `core`. Phase 5B now implements the bounded
local matcher and offline adjudication runtime described below. Phase 5C adds the offline review
page, leakage-aware queue/split generator, label importer and evaluator readiness. Actual human
labels, live providers and final frozen evaluation remain later checkpoints.
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
observations; the explicit 5B base-comparison policy is documented in the runtime section below.
DBLP and OpenAlex work native IDs remain source/endpoint bindings: different native records do
not by themselves prove different scholarly works. OpenAlex author IDs remain hypotheses.
Semantic Scholar IDs and repository URLs remain observed evidence; adding them to hard-authority
constraints requires a future authority-policy extension; they remain weak evidence in 5B. This narrow assertion
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
source links remain observations, not hard-authority facts. Only DBLP `sourceLinks` named exactly
`ee` gain DOI/arXiv authority through the strict recognized publication-resolver boundary described
below. Malformed recognized facts fail closed.

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

## Retained Phase 5A design agreement

The following design sections preserve the 5A interface agreement and later-subphase proposals.
The implemented **Phase 5B runtime** section below supersedes their preliminary API/settings
descriptions. Review tooling, labels, evaluator and provider-selection commands remain future work.

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

## Historical 5A CLI proposal — superseded by the 5B and 5C runtime sections

The following table records the earlier design proposal; use `Phase5Main --help` and the implemented
5B/5C sections below for current flags and paths:

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

## Phase 5B runtime

`Phase5Main` implements only `resolve` and `--help`. Review queues, labels, evaluation, live
providers and Spark grouping are later-subphase work. The matcher has no gold-label input or
held-out membership argument. This implementation makes no accuracy, calibration or human-review
claim. The original [contracts](contracts/) remain DESIGN_ONLY; the separate runtime examples in
`src/main/resources/phase5-policy.v1.json` and `phase5-config.v1.json` are executable **uncalibrated**
settings. Their numerical choices have not been fitted to labels.

The current runtime policy is `er-offline-uncalibrated-v2`, using `er-features-v2`. The policy schema
remains v1; v1 feature semantics are rejected at startup rather than silently reused. The feature
version changed because namespace-incomparable venue/affiliation evidence is now unavailable and
excluded from the available-weight denominator. Policy/config/request/cache hashes bind the changed
settings. The `contracts/` examples retain their original historical design values.

From the repository root, with Java 17:

```bash
sbt -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main --help'
sbt -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main resolve --input target/phase4-runs/fda6168a-d4e6-4c20-bf73-42a1c3724f7f --policy modules/entity-resolution/src/main/resources/phase5-policy.v1.json --config modules/entity-resolution/src/main/resources/phase5-config.v1.json --llm-mode disabled --output target/phase5/5b-disabled-demo'
```

The input path above identifies the actual retained Phase 4 sample; it must exist and pass a fresh
reader verification. Output paths must be new. Repeating the command requires another output path.
Fake mode is selected explicitly with `--llm-mode fake`; optional `--cache PATH` uses a separate
`fake/` cache namespace. The default fake adapter deterministically abstains. It never calls a model.
No live mode or live adapter exists in 5B. Invalid config, partial inputs and existing outputs fail
before calls or output writes. Policy explicitly supersedes `ScholarChainConfig.entityResolution`;
this CLI accepts no legacy config argument, and unknown/duplicate CLI or JSON fields fail.
Input, output and cache directories must be physically disjoint: equal paths or any ancestor/child
relationship fail before calls or writes, including aliases resolved through existing real ancestors.
The loaded input carries its source root only as local IO metadata, never as scholarly identity
or scoring evidence. Public engine/cache and export boundaries also protect that source root.

### Input and candidate integrity

`InputLoader.load` verifies both completion/manifest schemas and identity, all input-checksum,
snapshot and retrieval-date bindings, transformation version, all nine job success markers, the
exact export-part inventory and partition paths, every length and SHA-256, strict UTF-8 and JSONL
framing. Every known export kind is parsed with closed keys and domain validation. Authorship,
team and coauthor rows are validated against actual works; standalone author rows must exactly
match the nested mentions. Unknown kinds/schemas, missing candidates/lookups, dangling member
refs, conflicting observation payloads and noncanonical source-record aliases fail. Input bytes,
rows, row bytes, export files and lookup size have explicit limits. Source files are read only.

`ResolutionInput.create` provides the same validated source context for deterministic test/adaptor
use. It does not certify a human label or a completed Hadoop run; `completionHash=None` records that
limit. Full source/native-record/snapshot keys keep equal DOI-based work IDs as separate observations.

`CandidateBuilder.build` preserves all Phase 4 contributing candidate IDs/block keys. Known
profile/work cross-entity rows and nonwork ORCID activities receive separate row and distinct-pair
skip counts. Work activities become work comparisons without authors or teams. Researcher
comparisons use bounded name/order-variant, surname-initial, ORCID and OpenAlex-author blocks over
actual mentions/profiles; they include cross-observation publication contexts. The per-mention
cross-publication cap conservatively also counts copies of one publication across observations.
It never compares two members from the same source observation. Block membership, block size,
block pairs, total attempted pairs, retained comparisons, per-mention pairs and aggregate evidence
bytes are explicit bounds. Oversize blocks are skipped whole. A pair whose multiblock evidence
would exceed its bound is removed whole with a diagnostic; contributing refs are never silently
trimmed. Derived block evidence has a distinct `er-derived-candidate-v1` hashing formula and is
retained only for retained pairs. Preparation candidates and their feature vocabulary are unchanged.

### Normalization, identifiers and features

Normalization v1 uses Unicode NFKC, Locale.ROOT lowercase, whitespace/punctuation tokenization and
literal markup removal; it never executes text. Accents remain in title tokens. A separate NFD
mark fold aids names while raw source strings remain in exported evidence. Name-order variants are
comparison/blocking aids, not identities. Initials compatibility requires the same folded surname
and equal ordered given-name initials; a single token is unavailable.

DOIs and ORCIDs use core canonicalizers, including ORCID checksum validation. Ordinary arXiv fields
retain versions in their raw/normalized catalog entries. Hard authority and exact comparison use
the unversioned publication base, so versions of one arXiv publication are not conflicts. Distinct
bases are conflicts. The DBLP `ee` catalog uses core's bound electronic-publication helper: its raw
resolver spelling, namespace and canonical authority are retained together, including repetitions
and disagreements. DOI resolver suffixes use existing StableIds literal-token semantics without URI
decoding or query stripping: `%`, `?` and SICI punctuation remain literal DOI material. arXiv links
retain the separate conservative URI boundary; raw URI versions remain visible while their authority
catalog value is the unversioned base. OpenAlex work and author IDs use separate typed normalizers. Semantic Scholar
work IDs are 40 hex digits and author IDs are positive decimal IDs (or their matching official URLs).
These and OpenAlex author IDs remain hypotheses. Repository URLs accept HTTP(S), lowercase only
scheme/host, remove default ports, preserve raw case-sensitive paths, percent escapes and queries,
and reject credentials/fragments. They are never fetched; different paths or meaningful queries are
not equated. Unsupported raw identifiers remain in the source evidence and errors are explicit in
the catalog. No new SourceType is introduced.

Hard authority is exactly core's `groundedAuthority`, memoized per endpoint: DOI/arXiv for works,
ORCID for researchers, including recognized DBLP `ee` self-publication resolver links. That public
source-consistency API preserves contradictions and rejects malformed declared hard facts. Arbitrary
links and related ORCID work references never become self identifiers. Every known source authority
fact is exported in complete constraints. Same-namespace conflicts are checked before exact-ID,
bibliographic, scored or LLM acceptance and again before accepted-link creation. Missing IDs and
different namespaces are not conflicts. Sharing a work never establishes author identity.

Every feature has an explicit value or missing reason and actual source-record refs. Formulae:

| Feature | Formula/range and availability |
|---|---|
| title | Token Jaccard [0,1]; work/activity titles required on both sides |
| name | Accent-folded name-token Jaccard [0,1]; researcher names required |
| initials | 1/0 under the surname/initial rule above; unavailable without sufficient name parts |
| authorOverlap | Jaccard of folded complete author-name sets; full work author lists required |
| coauthorOverlap | Jaccard of folded other-author names; missing empty sets or copies known to be the same publication |
| authorOrder | `1/(1+abs(ordinalA-ordinalB))`; actual mention ordinals required |
| affiliation | Compare ROR/ROR, Ringgold/Ringgold, OpenAlex-institution/OpenAlex-institution and folded-name/name sets separately; minimum Jaccard over shared namespaces; missing/incomparable evidence unavailable |
| yearCompatibility | `max(0,1-abs(yearA-yearB)/yearToleranceYears)`; both years required |
| venue | 1/0 only inside the same complete venue-ID namespace (`venue:issn`, `venue:openalex`, `venue:dblp-booktitle`); cross-namespace or missing values unavailable |
| identifier | 1/0 for shared/no-shared values in at least one comparable namespace; distinct namespaces alone are unavailable |
| citationNeighborhood | Unavailable: preparation exports no citation neighborhoods |
| sourceReliability | Minimum configured source multiplier [0,1]; never contributes identity support |

Work-only and researcher-only features are explicitly unavailable for the other entity. Scores are
weighted averages over available configured features, multiplied by source reliability. Missing
weights do not contribute to numerator or denominator; no available weighted evidence gives no
score and UNRESOLVED. Preparation sentinel values are never used. Source reliability affects the
score only; it is neither measured accuracy nor independent identity evidence.
An incomparable venue has `UNAVAILABLE_INCOMPARABLE_VENUE_NAMESPACES`; disjoint nonempty affiliation
namespaces have `UNAVAILABLE_INCOMPARABLE_AFFILIATION_NAMESPACES`. One-sided absent fields retain the
generic missing-source reason. Organization names form a weak separate namespace; they never map
ROR to Ringgold or OpenAlex. A one-sided optional name does not dilute matching RORs. When several
namespaces are comparable, their minimum similarity conservatively retains any observed same-kind
disagreement. Names empty after normalization are unavailable with `EMPTY_NORMALIZED_NAME`, not zero.

Feature groups collapse correlated name/initial/order and title/venue evidence. Only actual feature
values at least `supportiveFeatureMin` count toward supporting groups; availability alone does not.
Acceptance requires configured minimum/required supporting groups. The runtime researcher policy
requires name, coauthor context and a third group; name alone remains unresolved. Exact grounded
shared IDs can accept after conflict checks. The supplied runtime policy disables the experimental
work-only bibliographic shortcut: generic titles such as “Preface” plus a shared author/year do not
establish uniqueness. Explicitly enabling that optional rule still requires policy review and remains
a disclosed limitation until document-type/uniqueness evidence is designed. Tests explicitly enable
it only to exercise the existing branch. When enabled, the rule requires
configured title/complete-author-set similarity and actual year-distance bounds; it cannot run for
activities without author lists. Disabling the shortcut is only a partial precaution: generic-title
records with enough matching scored features can still be accepted by the scored path. N1's complete
generic-title/document-type/uniqueness policy remains deferred for attention before the 5C policy
freeze; this implementation makes no quality guarantee for that stratum.
Scored rejection is `score <= rejectThreshold`; scored acceptance
is `score >= acceptThreshold` after sufficiency; otherwise unresolved. The inclusive LLM band lies
strictly inside the threshold gap. Exact/conflict/bibliographic rule paths have no numerical score;
legacy confidence zero is explicitly marked unavailable.

### Offline adjudication and cache

Only sufficient unresolved comparisons in the configured band are eligible. Disabled mode invokes
no adapter or cache and adds `LLM_DISABLED`. The provider seam is injectable for tests; the supplied
adapter is an explicit deterministic abstention fixture. Budgets reserve UTF-8 byte counts as a
conservative token allowance, not measured model usage. Every attempted call, including retries,
consumes the request and response reservations. Calls are sequential, with configured timeout,
retry, request/response bytes, rationale/reason/field citation sizes and total budgets. A failed,
malformed, timed-out or exhausted adjudication stays unresolved. An adapter ignoring cancellation
fuses the runner against retries/subsequent calls; arbitrary JVM code cannot be forcibly terminated,
so the production fake is synchronous and bounded and that seam is not an untrusted plugin loader.

Prompt and closed response schema are module resources. Response identity must echo all request IDs
and hashes. Only accept/reject/abstain and closed reason codes are allowed. Decisive responses cite
allowed evidence refs plus existing nonnull input fields as `evidenceRef#/JSON/pointer`; fabricated
fields, array indices, refs, extra/duplicate keys and oversized text fail. Embedded dataset
instructions are untrusted data. No tool/URL access occurs. Outcome/reason consistency is strict: accept has only `SUPPORTED_SAME_IDENTITY`, reject only
`SUPPORTED_DIFFERENT_IDENTITY`, and abstain only `INSUFFICIENT_EVIDENCE`; contradictory or mixed codes
fail closed. Separate model reason codes, rationale
and field citations remain in `audit-details.jsonl`; core adjudication stores the allowed record
refs and separate reported confidence. The final path is singular and preserves unresolved pre-LLM
outcome/score/path. Model confidence never replaces the system score or becomes calibration.

Requests/cache keys bind every supplied evidence payload/locator, feature, normalized identifier,
input/policy/config hash, provider/model/version/settings, prompt content/version and response
schema content/version, endpoint/pair identity and explicit fake mode. Cache hits revalidate exact
request and closed response plus content hashes. Corruption fails closed. Fake entries live under
`fake/`; live contexts are rejected. All cache ancestors must be nonsymlinks, writes are to unique
partial files then atomic rename, and existing differing entries are never replaced. Interrupted
partial files are not hits.

### Outputs and downstream ownership

A new output directory is published through a sibling partial directory and atomic rename after all
files and the completion marker exist. Failure leaves an untrusted partial directory, never a
completed output. Every entity has separate accepted/rejected/unresolved/conflict JSONL streams,
accepted pairwise links and one complete grouping-constraint JSON. Evidence, decision details,
diagnostics and effective settings are exported separately. Empty streams remain present.
`resolution-manifest.json` binds run/input/policy/config, prompt/schema, outcome counts, every file's
length/hash/count and the complete constraint bundle's full file hash for each entity. The completion
marker binds the manifest bytes. `LinkExporter.verify` checks inventory/digests/settings/bundle
bindings before downstream use. Hashes establish internal consistency, not external authenticity.

No groups or canonical representative IDs are assigned here. Phase 6's spark-engineer owns work
and researcher grouping and representative selection in `modules/spark/**`; the domain-engineer
owns shared ID rules/conflict semantics. Phase 6 must fail closed on missing coverage, cannot-links
and authoritative conflicts, including transitive A–B–C conflicts. The existing in-memory component
validator still revalidates the full bundle (N1); 5B does not call it repeatedly or construct groups.
An indexed/scalable consumer and shared conflict vectors remain required before Phase 6 scale use.

Human labels (40 development + 200 held out), calibration, provider choice, real calls and final
measured evaluation remain later gates. Phase 5C acquisition and queue evidence is reported in the
phase handoff; source record counts alone do not establish independent review-group sufficiency.


The offline default and later review queue must preserve distinct reporting strata for exact-ID,
scored, optional bibliographic and fake/live adjudication paths. Future human review should include
common names, generic publication titles, missing fields and cross-source identifier representations;
the present tiny portfolio supplies no calibrated per-stratum quality claim. Run-level performance
optimization and cache disk quotas remain tracked follow-ups before wider acquisition/scale use.


## Phase 5C implemented review readiness

`ReviewQueue.build` consumes only validated source observations and `CandidatePopulation`, with
explicit `ReviewSampling` and `ReviewBinding`. It never invokes the matcher or reads predictions,
labels, a gold set or LLM results. The runtime sampling resource is
`src/main/resources/review/sampling.v1.json`: **40 development + 200 held-out initial tasks**, with
**10 development + 50 held-out reserves**. Reserves are available evidence, not extra reviews
silently substituted for uncertain answers. A replacement requires a separately recorded reason
and decision, and must preserve the original uncertain annotation and partition.

Leakage components contain endpoints sharing a source/native observation (snapshot omitted), a
preferred underlying work ID, grounded authoritative DOI/arXiv/ORCID, directly observed OpenAlex
author hypothesis, or normalized title tokens. Work observations and their attached mentions
share their publication/identity anchors. Near-title anchors omit one sorted title token for
six-or-more-token titles (up to 256 tokens); this conservatively groups one-token variants.
Conflicting identifiers and OpenAlex author IDs are leakage evidence only, never merge authority.
Ambiguous names alone do not create identity components. Candidate comparison edges also do not
union components: a hard negative is not evidence that two people/publications are identical.

A fixed seed and degree/hash ordering select whole components for development; per-entity
coverage targets keep low-degree work pairs from exhausting development allocation before
researcher groups are considered. Evidence strata are round-robin within each entity, then entity
types are round-robin. Component connectivity can prevent balance, so actual counts and target
shortfalls remain reported. At least one held-out candidate per entity is preserved when its
source population permits. The remaining components stay held out. Only candidates whose endpoint components share a partition are eligible; cross-partition
candidates are counted and excluded. Entity/evidence strata are sampled round-robin within each
partition. The split retains all component endpoint IDs, hashed anchors, candidate-to-component
assignments, partition assignments, selected initial/reserve roles and excluded-edge count.
There is no random pair fallback. Insufficient source population, giant components or a conservative
selection failure returns an explicit `INFEASIBLE_*` error. The indexed search has a five-million
incident-edge work bound; a bounded greedy failure does not prove that every possible allocation is
impossible. Expand the population or record a revised sampling decision, rather than weakening
leakage grouping silently. Unknown identities, title paraphrases and other unobserved links can
still cause residual leakage; candidate recall is not global or blocking recall.

Queue and split hashes bind the complete sampled evidence and selection. The queue's
`ReviewPopulationBinding` contains only input and candidate population hashes; source population,
sampling, split, endpoint/task evidence and initial/reserve roles are also fixed by the queue/split
hashes. Human labels therefore remain usable when later development calibration or a provider
checkpoint legitimately changes the prediction policy, config, prompt, schema, model or code.
Those matcher settings are not human annotation identity. Changing source observations, candidate
population, task evidence or split still requires a newly bound queue and cannot relabel old exports.

`ReviewBinding` is a separate full **prediction-run** binding: input/candidates plus policy, config,
prompt/schema, configured model, code revision and source-tree hashes. Queue generation writes its
then-current metadata separately to `generation-binding.json`; that file is audit context and is
excluded from the label queue hash. It does not freeze later predictions to the generation policy.
An evaluation report records the actual P1 prediction-run binding alongside the unchanged population,
queue, split and label hashes. `--code-revision` and `--source-hash` remain explicit declared freeze
metadata, which the coordinator must independently verify against the frozen tree; they are not
authentication. A configured offline fake model identity does not claim it ran.

Before later held-out evaluation, freeze the actual prediction policy/prompt/model/code as its own
run binding after development calibration. A changed prediction run may reuse unchanged human
labels, but it cannot use held-out labels for tuning without a new holdout or an explicit exploratory
qualification. Population stability does not imply that every model/policy comparison is an
independent final evaluation.

### Offline review page and original annotations

`export-review-tool` copies `index.html`, `guide.txt` and `sampling.v1.json` from the bundled review
resources. Open the page locally and select `queue.json`. The default view contains initial tasks;
reserves require an explicit separate selector. Both observations show the indicated mention or
publication plus raw source records, author context, IDs, affiliations and source/snapshot/locator
refs. Missing values remain missing. No prediction, score, LLM judgment or suggested label is in
the queue. Source text is rendered with `textContent`; the page uses no external scripts, link
fetching, analytics or server, and its CSP forbids network connections.

Enter a reviewer ID, choose Same / Different / Uncertain and optionally enter a note. Navigate or
skip without assigning a label. Notes are committed only with an explicit answer/undo action.
Every answer and correction creates a bounded linear revision with a unique revision ID, previous
revision ID and UTC timestamp. Undo adds the internal `unlabeled` revision without deleting prior
annotations; it is not a fourth identity judgment or a binary negative. The importer preserves all
history and reports current uncertain/unlabeled/missing counts separately. Reviewer IDs are
self-entered provenance, not authentication.

Save checkpoints frequently to a durable folder **outside `target/`**, verify the downloaded file
exists, and keep a backup. A browser download request is not proof of persistence. Unsaved browser
state is not durable; refresh requires loading the same queue and saved checkpoint. The page rejects
mixed queues, altered hashes, duplicate revisions, unknown pairs and incompatible histories. It
never silently merges divergent checkpoints. `GoldLabels` also applies closed typed JSON validation,
source/pair/entity/evidence binding, revision-chain and UTC checks before producing a separate
`ValidatedLabels` derivation. Original checkpoint bytes are never rewritten, and their SHA-256 and
full original annotation history remain in the derivation. New validated label files refuse target
paths, symlink ancestors, input overlap and overwrites. Preserve the original user exports even
after successful import.

### Evaluation semantics and access boundaries

The matching runtime has no label/split loader. `Evaluation` is a separate consumer of queue, split,
validated annotations and an explicitly frozen prediction dataset. It rejects duplicate prediction
pairs and mismatched population bindings; the separate complete prediction-run binding remains
validated and recorded even when it legitimately differs from queue-generation settings. Wrong pair/entity/evidence, unsupported outcomes/paths and
nonfinite scores become counted invalid predictions; absent rows are counted missing predictions.
Neither disappears from binary denominators. Initial tasks only are evaluated; reserves are not
automatically counted. Unknown prediction pairs outside the sampled queue are counted separately.

Positive prediction means `ACCEPTED`; every other outcome, including missing/invalid, is
nonacceptance. TP/FP/FN/TN therefore count unresolved/conflict true matches as false negatives.
Manual `uncertain` and `unlabeled` annotations are excluded from binary gold and reported separately.
Reports retain gold-by-four-outcome tables (with explicit MISSING/INVALID columns), researcher/work,
path and fake/live/cache breakdowns, binary precision/recall/F1/accuracy, decisive-only metrics,
decisive coverage, unresolved/conflict rates, denominators and null metrics for empty denominators.
Up to ten actual false positives and false negatives retain evidence refs and concise interpretations.
Uncertain plus unreviewed initial tasks are reported as additional reviews/adjudications needed;
useful binary class/entity coverage still requires human assessment.

`fromDecisions` preserves fake/live/cache provenance and verifies pair/audit identity and frozen
metadata against an explicit full prediction-run binding. `prepare-evaluation-predictions` requires
`--binding PREDICTION_RUN_BINDING_JSON` and verifies that binding against the actual completed
resolution marker/manifest, all listed file digests, the actual config/model, and each typed decision
against the completed Phase 4 input context. It recomputes `CandidateBuilder` using the verified
input and actual run config; a blocking change that alters the candidate population is refused,
while an adjudication-only config change with identical candidates can retain the labels.
Its explicit code/source arguments must match the prediction run binding; old resolution manifests
do not independently authenticate those declarations. Reports bind labels/predictions/input/candidates/split,
code/source/policy/config/prompt/schema/model, seed, invocation, observed Java/Scala-library versions
and actual UTC time. The phase evidence records the actual sbt/Scala compiler toolchain as well.
A report is readiness evidence, not final Phase 5E acceptance.

Sensitivity accepts development only and makes no provider calls. It is a hypothetical acceptance
cutoff table over existing scored rows; exact/conflict/LLM and missing/invalid rows remain fixed.
It does not replay evidence-sufficiency rules or establish a calibrated production policy. Held-out
sensitivity/tuning is rejected. Actual held-out measurement waits for human labels and the later
frozen 5E gate; 5C tests use explicitly synthetic labels only.

### Current CLI contract

Run `sbt -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main --help'`
for all current flags. Subcommands use new output paths and refuse existing outputs; fatal failures
exit 2. Queue and prediction JSON readers are UTF-8, closed-schema and bounded to 64 MiB at review
boundaries. Outputs must be physically disjoint from their input files/runs. The phase handoff supplies
actual verified source-run, tool, queue and evidence paths; these commands show argument roles:

```text
build-review-queue --input COMPLETED_PHASE4_RUN --policy POLICY_JSON --config CONFIG_JSON --sampling SAMPLING_JSON --code-revision GIT_SHA40 --source-hash FROZEN_SOURCE_SHA256 --output NEW_DIRECTORY
export-review-tool --output NEW_DIRECTORY
import-labels --queue QUEUE_JSON --labels ORIGINAL_CHECKPOINT_JSON --output NEW_DURABLE_VALIDATED_JSON
prepare-evaluation-predictions --input COMPLETED_PHASE4_RUN --config CONFIG_JSON --queue QUEUE_JSON --predictions COMPLETED_RESOLUTION_RUN --binding PREDICTION_RUN_BINDING_JSON --code-revision GIT_SHA40 --source-hash FROZEN_SOURCE_SHA256 --output NEW_JSON
evaluate --queue QUEUE_JSON --split SPLIT_JSON --gold VALIDATED_LABELS_JSON --predictions EVALUATION_PREDICTIONS_JSON --partition development|held-out --output NEW_DIRECTORY
sensitivity --queue QUEUE_JSON --split SPLIT_JSON --gold VALIDATED_LABELS_JSON --predictions EVALUATION_PREDICTIONS_JSON --partition development --thresholds 0.8,0.9 --output NEW_JSON
```

The queue command writes `queue.json`, `split.json` and separate `generation-binding.json`; the evaluation command writes
`evaluation.json`. Import writes one derived file at the explicit durable output path. The independent
browser tests exercise a separate synthetic queue/checkpoint and never count as human labels.
No 5B nonblocking findings are repaired by this subphase: those matching/scaling/IO limitations
remain documented under the user's instruction to leave them unfixed.


### Durable completed-input replay (5C B2 repair)

The dataset-owned `datasets/entity-resolution/prepared/` handoff retains the exact completed Hadoop
export, completion marker, run manifest and required success markers used by the real queue. The
original run UUID, source payloads and snapshots remain unchanged: copying this verified run changes
its physical path without changing its input evidence or candidate hashes. The CLI accepts that
completed durable directory through the existing strict loader; no source normalization or new UUID
is needed. Per-file dataset replay manifests and phase evidence establish which original bytes were
retained. Re-running Hadoop from raw samples is a separate transformation run and is not a substitute
for retaining the reviewed queue's exact observation provenance.

### Current review handoff and archived acquisition attempts

Use `docs/agent-runs/phase-05/evidence/5c-repair/review-artifacts/queue.json` and its sibling
`split.json` for the repaired review population, backed by the durable completed input at
`datasets/entity-resolution/prepared/bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/`.
Earlier v1/v2 acquisition payloads and the pre-repair `evidence/5c/review-artifacts/` queue/split
are historical archive material, not CLI or test dependencies. Their retained manifests and
historical reports describe the original attempts; use the packaging archive inventory to locate
archived payloads rather than treating an old path as the current human-review handoff.

## Phase 5D bounded OpenAI development checkpoint

The selected provider is OpenAI Responses with API model `gpt-6-luna`. The provider adapter uses
JDK 17 HTTP APIs, so no SDK/build dependency is added. The official model page exposes that alias
without a dated snapshot; the configured alias and the actual model identifier reported by each
response are recorded separately. There is no model fallback. See the fetched official
[model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna),
[Responses API reference](https://developers.openai.com/api/reference/typescript/resources/responses/methods/create)
and [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

The ordinary `resolve` command retains its disabled/fake behavior. Two separate commands implement
the explicitly development-only checkpoint; neither imports labels:

```text
prepare-live-demo --input COMPLETED_DEMO_PHASE4_RUN --frozen-input FROZEN_REVIEW_PHASE4_RUN --queue QUEUE_JSON --split SPLIT_JSON --policy POLICY_JSON --config SOURCE_CONFIG_JSON --live-config LIVE_CONFIG_JSON --scope development|supplement --code-revision GIT_SHA40 --source-hash SOURCE_SHA256 --output NEW_DIRECTORY
adjudicate-demo --input COMPLETED_DEMO_PHASE4_RUN --frozen-input FROZEN_REVIEW_PHASE4_RUN --queue QUEUE_JSON --split SPLIT_JSON --policy POLICY_JSON --config SOURCE_CONFIG_JSON --live-config APPROVED_LIVE_CONFIG_JSON --scope development|supplement --code-revision GIT_SHA40 --source-hash SOURCE_SHA256 --runtime-binding BINDING_JSON --approval USER_APPROVAL_RECEIPT_JSON --enable-live APPROVAL_ID --output NEW_DIRECTORY
```

`prepare-live-demo` performs no credential lookup or provider call. `LiveDemo.select` admits only
candidates whose complete frozen leakage groups are development, including unselected demo pairs;
held-out and unassigned components are excluded **before classification**. `selectSupplement`
protects the same frozen holdout when separately authorized real demo evidence is introduced.
It reuses the exact frozen source/identifier/title/attached-mention anchors, unions new observations
transitively by those anchors, then excludes every new component touching a held-out anchor.
Negative candidate edges never union identity components. Both endpoints must survive admission
before the unchanged classifier runs. The admission artifact binds both source populations, candidate
hash, original queue/split, protected-anchor hash, admitted and excluded pair IDs. The review queue,
source population and human annotations are unchanged; unknown identities remain a leakage limit.

A naturally eligible pair must remain unresolved, have sufficient independent evidence, lie inside
the existing inclusive LLM band, and have no authoritative conflict. Request selection is deterministic.
The initial frozen population supplies zero eligible candidates among its 50 selected development
reviews/reserves and all 62 development-component candidate comparisons under the unchanged policy.
That observed shortfall does not authorize changing scores, bands, sufficiency or source evidence.
Any later supplement and its actual eligibility proof are documented in the phase evidence.
No eligible pair means no provider, transport factory, runtime credential or budget-ledger access.

### Provider protocol and credentials

The existing typed `AdjudicationRequest`/`AdjudicationResponse` protocol remains the local contract.
A separate live prompt and provider-compatible closed JSON schema are bundled under `adjudication/`.
The OpenAI schema omits unsupported `allOf`/`if`/`then` and related composition keywords; the existing
local validator still enforces outcome/reason agreement, exact request identity, allowed evidence
refs, present JSON-pointer field citations, rationale bounds and finite reported confidence.
Explicit live response limits must agree with the actual source config. Model confidence remains
separate from the uncalibrated deterministic score and never bypasses authoritative conflicts.

The fixed endpoint is `https://api.openai.com/v1/responses`; redirects, tools, streaming, storage,
server-side truncation and alternate hosts are unavailable. The wire request explicitly selects
standard service tier, the approved reasoning effort and bounded `max_output_tokens` (including
reasoning tokens). Complete response bodies have a byte bound and deadline. Refusals, incomplete
responses, unexpected tool outputs, wrong models, invalid JSON/citations, transport failures and
missing usage fail closed. No raw provider error body or transport exception is stored as an error.

Only the actual live transport resolves the named `OPENAI_API_KEY` environment variable, at
runtime dispatch after admission, approval and budget reservation. Never put its value in arguments,
tracked configuration, logs or evidence. No `.env` or credential file is read. Disabled/preparation,
zero-eligible and exhausted-budget paths do not resolve credentials. Tests inject a transport and
use synthetic responses; those tests do not create real-provider evidence.

### Approval-scoped persistent allowances

`adjudication/openai-live.example.v1.json` remains `approved: false`; examples grant no live authority.
The approved pilot allowance is recorded separately in coordinator-owned human evidence. The CLI
checks the exact receipt bytes, provider/model/settings and numerical ceilings, then verifies a
runtime binding to a single canonical ledger/cache directory under
`docs/agent-runs/phase-05/evidence/5d/live-state/approval-<receipt-sha-prefix>/`.
Changing the output directory cannot reset that allowance. A process-lifetime file lock refuses
concurrent ledger writers. Each attempt, including a retry, reserves and durably records allowances
before dispatch. Unknown failures retain reservations; they are not refunded. A timeout or ignored
cancellation fuses further requests rather than allowing overlapping retries.

Input reservation is wire UTF-8 bytes plus a 4,096-token framing allowance: a conservative estimate,
not exact provider tokenization. Requests are capped at 64 KiB and exclude long-context pricing.
Output reservation uses the provider-enforced maximum including reasoning tokens. Requests, total
input/output allowance and integer USD-micro spend must all fit before dispatch. An observed usage
overrun fuses subsequent calls. Reported input/output/total, reasoning and cached tokens are retained
separately; absent cache-write details are zero **reported** writes, not evidence that caching never
occurred. Unknown usage remains counted as unknown and fully reserved.

The verified short-context standard rates are $0.10 input, $0.01 cached input, $0.125 cache writes
and $0.50 output per million tokens. Reservations and observed-cost upper bounds charge all input at
the higher cache-write rate, giving no speculative discount. These are conservative cost estimates,
not an invoice or a claim that provider billing was verified. Fast/regional/long-context service is
not selected. Actual usage, failures, abstentions, request IDs, selected/reported model identity and
cache provenance remain auditable.

Live cache entries have a distinct `live/openai/gpt-6-luna/` namespace and schema. Keys bind the
complete live request, effective config, prompt/schema/model/settings and source evidence. Replay
revalidates content, local response semantics and original provider provenance; it consumes no new
provider attempt and cannot masquerade as a new call. Fake entries never satisfy a live request.

### Demo outputs and remaining gate

The demo publishes core-validated decisions, accepted pairwise links and complete source-authority
constraints, plus admission, effective settings, provider traces/usage and a hash-bound completion
manifest. These outputs explicitly cover a **development demo**, not a complete candidate-population
matching run or final held-out evaluation. The full source coverage of a constraint bundle is not
proof that all source candidate pairs were predicted. Source records and the review queue remain
immutable. The actual provider-reported model is retained in traces and the manifest; core audit
metadata records the explicitly configured alias without inventing a dated version.

Real calls require the recorded numerical approval, passing offline checks, naturally eligible
non-held-out evidence and runtime credential availability. The coordinator executes any authorized
pilot; implementation agents do not initiate calls. Actual human reviews/import and later frozen
5E evaluation remain separate prerequisites. Provider code, fake tests or a prepared request alone
do not satisfy the real-provider or human-review gate.

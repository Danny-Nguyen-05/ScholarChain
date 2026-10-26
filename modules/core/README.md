# Core contract boundaries

## Phase 5 identity contracts (Subphase 5A)

`ResolutionContracts.schemaVersion` is `scholarchain.resolution.v1`. These additive types do
not change `scholarchain.domain.v1`, existing stable IDs, preparation features or shared config.
`ResolutionObservationRef` binds source, native record key and snapshot. `ResolutionEndpoint`
distinguishes a work observation, a parent-work author mention, an ORCID profile, and an ORCID
work activity. A work activity has no author list; employment, education and other nonwork
activities are evidence only and require an explicit unsupported-pair skip in the future ER
input bridge. A lookup hit on an unsupported kind must not be reported as a missing record.

`ResolutionValidationContext.create(works, profiles, activities)` validates the supplied domain
records before constructing immutable lookups. Identical duplicates are allowed, conflicting
payloads for one full observation key fail, and separate snapshots remain separate. Mention
endpoints must name an actual nested author in their parent work. Endpoint bindings (work ID,
ORCID, activity kind and optional observed work ID) must agree with that source context.
This checks consistency of supplied observations, not external existence or factual identity.

`ResolutionIds.pair(entityType, first, second)` creates a canonical unordered pair. It checks
endpoint syntax and type, while `ResolutionValidation.check(pair, context)` additionally binds
the pair to source records. The endpoint identity tuple is compact JSON
`[kind, sourceWire, sourceRecordId, datasetSnapshot, mentionIdOrEmpty]`, where kind is `work`,
`mention`, `orcid-profile` or `orcid-work-activity`. Carried work/ORCID values are bindings,
not extra identities. Canonical order is `String.compareTo` on these tuple strings. A self pair
fails. `resolution-endpoint:` hashes that compact tuple with SHA-256 over UTF-8.
`resolution-pair:` hashes the compact JSON array
`[schemaVersion, entityType.toString, leftTuple, rightTuple]`. It does not depend on blocks,
scores, policy, run IDs or timestamps. Duplicate blocks must be aggregated by the ER owner.
uPickle uses `$type` for endpoint variants and strings `Work`/`Researcher` for entity types.

`ResolutionDecision` wraps the unchanged `MatchDecision`. Its source/target IDs are snapshot
endpoint hashes, its derived provenance source is `SCHOLARCHAIN`, and provenance source-record
ID names the pair. The wrapper requires a UTC instant ending `Z`, policy/config/input-evidence
hashes, evidence references, contributing candidate/block references, versioned feature
availability, a decision path and explicit confidence semantics. Features have a finite value
or a nonblank missing reason, never both. Available values must exactly repeat the legacy
decision feature vector; missing values are excluded. `Unavailable` confidence requires a
reason and compatibility value zero; that zero is not a score. `UncalibratedScore` does not
claim probability calibration. Feature formulas, namespace rules, eligibility, evidence loading,
policy validation and calibration remain ER responsibilities; core checks carried consistency.
Candidate IDs/references and evidence references are structurally checked here; the future
input bridge must verify their existence, content hashes, relationship to the pair and bounds.

When present, `ResolutionAdjudication` requires the model's `reportedConfidence` separately
from system confidence, hashes/versions/provider/model metadata, fake/live mode and cache status.
Unknown model versions remain absent. `preAdjudication` retains the optional pre-LLM score,
unresolved outcome and original scored/bibliographic path. It cannot claim an exact or conflict
case was eligible. Adjudication metadata exists exactly when the final path is `LlmAdjudicated`;
that final path cannot report `CONFLICT`. The ER policy must enforce the uncertainty band and
conflict precedence.
`resolution-decision:` hashes compact JSON of the full wrapper with only `decisionId` blanked;
time and run therefore change audit identity while pair identity stays stable.

`ResolutionValidation.check(link, audit, context)` requires the actual accepted decision and
matching pair, decision ID, policy, run and provenance. `ResolutionAcceptedLink` exports
pairwise acceptance only and assigns no canonical representative. Phase 6 must consume the
complete `ResolutionGroupingConstraints` from the same policy/run population before grouping.
`coveredEndpoints` explicitly includes members with no authoritative IDs: missing coverage
fails closed. Cannot-link pairs and authoritative namespace/value assertions are explicit
constraints, emitted by ER and checked against each endpoint's validated source observation.

`ResolutionIdentifierAssertion.namespace` uses the closed `ResolutionAuthorityNamespace` set:
explicit wire codes `doi` and `arxiv` for Work endpoints, and `orcid` for Researcher endpoints.
Unknown codes, aliases, casing variants and entity-incompatible assertions fail closed. Values
must already equal the output of the existing `StableIds.normalizeIndexedIdentifier` rule:
DOIs are normalized lowercase bare tokens, ORCIDs are bare checksum-valid identifiers, and
arXiv identifiers are canonical unversioned tokens. Version-bearing arXiv assertions fail
rather than treating versions as conflicting works or stripping versions implicitly. Their
original source values remain observations for the later version-aware matching policy.
Ingestion must normalize supported raw spellings before constructing assertions; component
validation rejects noncanonical values before comparing authoritative identifiers. This avoids
treating an ORCID URL and its bare identifier, or DOI case variants, as separate authorities.

Each assertion must match a supported fact on that exact source/snapshot endpoint. Every
supported fact must be explicitly asserted for every covered endpoint, including an ORCID
profile's own ORCID and a mention's own observed ORCID. An assertion cannot borrow another
mention's identifier, a parent work's identifier, an OpenAlex hypothesis, or an arbitrary
profile external ID. Actual absence of supported identifiers is valid; omission of an observed
identifier is not. Contradictory same-namespace observations must all be retained: a complete
bundle can describe them, but a proposed component containing them fails the conflict guard.

`context.groundedAuthority(endpoint)` exposes those same canonical source facts as a read-only
`Either[Vector[DomainViolation], Set[(ResolutionAuthorityNamespace, String)]]` for ER conflict
checks and complete constraint export. A bound endpoint without supported IDs returns an empty
set; an unknown/mismatched endpoint or malformed supported own-identity evidence returns errors.
Contradictory facts are returned together. The accessor does not decide matches, prove external
existence or produce evidence references: ER must attach references to the actual input evidence.
`context.groundedElectronicPublicationFacts(endpoint)` additionally exposes each bound DBLP
`ee` link as `(NamedText, ResolutionAuthorityNamespace, canonicalValue)` within the same error
envelope. This preserves raw link roles and values for ER's identifier catalog without copying
resolver rules. Unsupported roles/endpoints return an empty vector after endpoint validation;
contradictory and repeated recognized links remain represented.

The grounding roles are deliberately closed. Work observations use their DOI/arXiv fields,
Crossref's DOI source-record key even when the optional DOI field is absent, and declared
`observedIdentifiers` roles `doi`, `arxiv`, `openalex.doi`, `openalex.ids.doi`. Role names use
trimmed `Locale.ROOT` lowercase matching; OpenAlex roles retain existing source validation.
Raw supported values are normalized with existing `StableIds` rules; explicit arXiv resolver
URLs use the existing URI helper. Source arXiv versions that the existing parser accepts are
reduced to their base only for grounding an unversioned assertion. This does not change work
IDs or source records. Unsupported old-style version syntax fails closed rather than inventing
a base identifier. DBLP `sourceLinks` with exact field name `ee` additionally ground direct
publication resolver identifiers: exact HTTP(S) `doi.org/`/`dx.doi.org/` prefixes, or `arxiv.org`
and path `/abs/…` or `/pdf/…`. DOI values use `StableIds.normalizeDoi` on the entire original
resolver string, exactly as preferred fields and Phase 4: literal percent escapes, `?`, `#` and
SICI angle brackets in valid suffixes are preserved under the existing trim/lowercase rule.
They are neither URI-decoded nor stripped as queries/fragments, and distinct literal suffixes
remain distinct facts. arXiv keeps separate conservative resolver syntax: query strings,
fragments and percent-encoded paths fail closed. Recognized malformed identifiers, user
information and explicit ports fail closed. Every retained resolver identifier is included
even when it contradicts the preferred field.
Other source types, field names (including DBLP `url` table-of-contents links), hosts and arXiv
nonpublication paths remain weak observations. Arbitrary `sourceLinks` are not authority facts.

An ORCID work activity uses `observedDoi` and declared DOI/arXiv `workReferences` whose
relationship is `self` (trimmed, case-insensitive type and relationship tokens). Related or
missing-relationship references remain evidence, not assertions about the activity's own work.
A legacy preferred DOI can ground an assertion without a corresponding reference; if matching
retained DOI references exist only with nonself/unknown relationships, grounding fails instead
of promoting that related identifier or silently dropping the preferred field. Malformed
recognized own-identity facts fail the whole bundle, including facts on members outside the
currently proposed component. Unknown identifier roles remain original observations. This is
source-consistency validation, not a general authority extraction or matching policy.

The authority set is narrower than source observation identifiers. DBLP and OpenAlex work IDs
remain source bindings: different native records may still describe the same work. OpenAlex
author IDs remain disambiguation hypotheses. Semantic Scholar IDs and repository URLs remain
comparison evidence for Phase 5B; they are excluded from this hard-conflict namespace because
their entity/canonicalization semantics require later policy work. Scopus and other free-text
external identifier namespaces remain original observations, never coerced into this set. No
source record, existing identifier normalizer or source enum is changed by this restriction.

`ResolutionValidation.checkComponent(members, constraints, context, maxMembers, maxConstraints)`
checks an already proposed component. Both limits are caller-supplied positive bounds, checked
before traversing the bundle; constraint size is covered endpoints plus cannot-links plus
identifier assertions. It rejects duplicate/uncovered members, cannot-link endpoints in the
same component, and distinct authoritative values in one namespace anywhere in the component.
Thus accepting A–B and B–C does not authorize merging a conflicting A–C. The validator does
not construct components, select representatives, invent constraints or prove export completeness
beyond supported source-fact coverage. The future export manifest must bind the complete constraint-bundle content hash
to its run, input population and policy hash; consumers must verify that binding before grouping.
Structural validation alone does not establish a complete export.
The user assigned Phase 6 grouping and deterministic representative selection to the
`spark-engineer` under `modules/spark/**`; the `domain-engineer` owns shared contract changes.
That ownership assignment does not begin Phase 6 implementation.

Frozen wire examples live under `src/test/resources/wire/resolution-*.json`; tests roundtrip
work/researcher pairs, both audit examples, a link and constraints. Their source facts reuse
existing core fixtures, while decisions, scores, policy and grouping assertions are explicitly
synthetic contract examples. They are not produced matches, human labels or evaluation results.
Phase 5 policy, labels, provider behavior and the review tool remain module-local future work.

`DomainValidation.check(work)` validates one immutable source observation and never registers it globally. `WorkValidationContext.create(works)` validates all supplied works before creating an immutable lookup keyed by `(source, sourceRecordId, datasetSnapshot)`. Identical duplicates are allowed; conflicting records under the same key are rejected deterministically, including differing lineage metadata. Separate snapshots and separate contexts cannot overwrite each other.

Full validation of a `CoauthorPairCandidate`, `AuthorshipRecord`, or `PublicationTeam` requires `DomainValidation.check(record, work)` or `DomainValidation.check(record, context)`. The single argument `check` returns `MissingValidationContext`. `checkStructure(record)` checks the carried fields and their internal consistency only; it does not establish a relationship to a source work. A record's own DOI or URI cannot supply missing context.

The contextual check binds source, source-record key, snapshot, authoritative work ID, and actual member mentions. Pairs repeat that observation's DOI/arXiv fields and year. Teams contain all source mentions in author ordinal order. Authorship position matches the source mention ordinal. A resolved researcher ID is syntactically checked; its identity decision remains the responsibility of entity resolution. The producing `runId` can differ from the source acquisition run, so a later Hadoop or Spark run can reuse the same snapshot. Nested source author mentions must carry the work's source, record key, and snapshot.

Work IDs prefer DOI, then arXiv, then a supported native ID. Crossref's source-record key is itself an authoritative DOI, including when the optional `doi` field is absent. DOI or arXiv identifiers in direct resolver links must agree with the work fields (or Crossref's authoritative record key). Ordinary unrelated URLs are locators and supply no bibliographic authority. Both DOI and arXiv may be observed on the same work; DOI wins for the work ID. Syntax checking and consistent source metadata do not prove that an external record exists or that two observations should merge.

`ResearcherMetrics` describes the complete deduplicated canonical graph and publication population for its policy and window. Weighted degree is the sum of incident joint-publication edge counts and equals total coauthor occurrences. Average equals occurrences divided by publications, including solo papers. Zero publications require zero collaboration values; maximum and distinct counts are bounded by occurrences, maximum is bounded by distinct coauthors, and occurrences are bounded by publications times maximum. Products use `BigInt`. Double arithmetic accepts an absolute tolerance of `max(1e-12, 4 * ulp(expected))`. The retained provisional researcher fixture demonstrates sample arithmetic and explicitly says graph analytics were not computed.

## Phase 6B Spark analytics contracts

`SchemaVersions.sparkAnalytics` (`scholarchain.spark-analytics.v1`) versions new Phase 6 output records. Each carries `SparkRecordContext`: schema version, run ID, optional window ID, and `SparkLineage` with Hadoop run/snapshot, entity-resolution run/policy/hash, plus bounded source work and mention references. Empty source-ID vectors still point to the complete upstream runs; consumers must retain complete support tables and manifests. `SparkAnalyticsValidation.check` validates each new record locally. Spark jobs must additionally check cross-row invariants.

`StableIds.researcherIdFromDblpName(policy, exactName)` hashes the policy, LF, and trimmed NFC DBLP name, preserving case, internal spacing and homonym suffixes. It yields `researcher:dblp:<sha256>`. `parseResearcherId` accepts this new form alongside the frozen ORCID and provisional forms. `StableIds.sparkAnalyticsId` supplies component, community and path-evidence IDs from policy, window ID and stable material. `StableIds.sparkSemanticSummaryId(entityId, policyVersion, windowId, summaryType, text)` uses `chunkOrProfileId` with `sourceVersion = policyVersion + ":" + windowId`; the record carries the policy and window so validation can recompute the exact ID. This gives `profile:` IDs to researcher profiles and `chunk:` IDs to other summary types, compatible with the existing citation parser.

The existing `CoauthorEdge` and `ResearcherMetrics` wire formats and ID formulas stay unchanged. New analytics use `SparkCoauthorEdge`, `ResearcherMetricsDetail` and `ResearcherBridgeMetrics`. `ResearcherMetricsDetail` enforces the frozen count, average, weighted-degree, maximum and coreness relations plus max-team work tie bounds. `SparkCoauthorEdge` uses `StableIds.sparkCoauthorEdgeId(a, b, window, policy)`, which hashes ordered researcher IDs, the configured window ID, optional numeric start and end bounds (empty fields when absent), and graph policy. The edge row carries `windowStartYear` and `windowEndYear` so validation can recompute its ID. Its first/last collaboration years are separate optional observations. An all-years edge supported only by yearless DBLP works has those collaboration years absent; a year-bounded window excludes those works. `CoauthorEdgeSupport` has an optional year and points to every supporting work, while representative IDs remain capped. This avoids treating numeric sentinel bounds as observed years. `EvidenceItem` accepts `spark-coauthor-edge:` locators with `evidence:edge:` IDs; a yearless edge still needs a Phase 7 storage mapping because the frozen graph-edge coauthorship fields require integer years.

`SparkAnalyticsConfigLoader.load` and `.loadText` read the strict JSON config contract in [`scholarchain.spark-analytics-config.v1.json`](src/main/resources/scholarchain.spark-analytics-config.v1.json). Its full canonical JSON fingerprint is SHA-256. `logicalFingerprint` hashes schema, windows, policies, algorithm caps, checkpoint interval, hard-invariant mode, benchmark pairs and sampling settings; it excludes input/output roots, checkpoint path and shuffle partition count. `StableIds.sparkAnalyticsRunId` binds both upstream run IDs and manifest hashes, the ER policy version/hash, the logical fingerprint and code version into a SHA-256-derived UUID with v4/variant bits set; it passes the existing `run:` parser. The default windows are all-years; consecutive comparison windows through 2009, 2010–2014, 2015–2019 and 2020–2026; and cumulative since-2015. Optional year bounds represent all-years and the first open-start window. Representative edge works are capped at 5; max-team work IDs at 20, with the full tie count in `ResearcherMetricsDetail`. The default resource uses placeholder local run roots and must be supplied with real completed run roots by the caller.

`TemporalChange` carries `fromPresent` and `toPresent`. Numeric deltas are present only when the researcher appears in both adjacent comparison windows; entry and exit rows leave them absent, preserving the difference between missing and zero. `PathStatus` wire values are `found`, `no-path` and `exceeded-maxHops`.

All new wire snapshots are in [`src/test/resources/wire/spark-*.json`](src/test/resources/wire/), with round-trip and validation tests in `SparkAnalyticsContractSpec`. The same suite confirms the frozen `coauthor-edge.json` and `researcher-metrics.json` still parse.

`GraphEdge.coauthorship` is an optional typed `CoauthorshipProperties` record, required only for `COAUTHORED_WITH`. Representative works form a nonempty distinct vector bounded by joint-publication count. Named text properties must have distinct keys and cannot duplicate the four reserved coauthorship names. Both unresolved mentions and canonical researchers can be `AUTHORED` sources.

`GraphSourceEvidence.Work(workId)` is a typed work pointer. `GraphSourceEvidence.SourceRecord(source, sourceRecordId, datasetSnapshot)` is an external observation pointer and must match the edge's provenance source, record key, and snapshot. Supported source-record keys include DBLP keys, Crossref DOI keys, OpenAlex entity IDs, and checksum-valid ORCID IDs with optional supported activity paths such as `/0000-0002-4414-6920/employment/19198978`. These validate reference syntax and locator consistency, not the external evidence's factual contents.

Graph-edge IDs retain SHA-256 over LF-joined edge type, canonical endpoints, policy version, and evidence pointer. Work evidence uses the original work ID pointer, preserving existing work-based edge IDs. Source-record evidence uses the compact JSON array `["source-record", SOURCE_WIRE, sourceRecordId, snapshot]` as the last hash field. JSON escaping makes the pointer unambiguous. The serialized evidence object uses uPickle's tagged enum encoding. Reference IDs use the same strict parsers in graph nodes, endpoints, and concrete Venue/Institution/Topic records; supported namespaces are documented by `StableIds` constructors and parsers. ROR checks the [official identifier pattern](https://ror.readme.io/docs/identifier), not registry membership or the checksum.

# Configuration profile

`scholarchain.config.v1.conf` contains JSON syntax, a valid HOCON subset, and is byte-identical to the `.json` resource. `ConfigLoader` supports exactly this JSON profile plus explicit environment overrides and quoted `${ENV_NAME}` placeholders. It uses the existing ujson dependency and rejects non-JSON HOCON and YAML syntax. General HOCON includes, unquoted values, and substitutions are not implemented. This implements the human work order's JSON HOCON profile; it makes no claim of instructor approval or general format support.

# Phase 4 Hadoop preparation contracts

These types are additive on `scholarchain.domain.v1`. Hadoop preparation limits are not fields of `ScholarChainConfig`. They use `scholarchain.hadoop-prep.v1`, loaded only by `HadoopPrepConfigLoader`. A `Left` result fails closed; do not launch a job from it. The committed sample profile is `scholarchain.hadoop-prep.v1.json`. Its `outputRoot` is the relative path `target/phase4-runs`. The loader has no compiled-in numeric, bucket, endpoint, account, or execution-mode default. A caller-supplied `s3://`, `s3a://`, or `s3n://` output root with a non-empty bucket and key prefix is valid. A bare AWS hostname or endpoint is rejected. A `RunManifest` may name `scholarchain.config.v1` or `scholarchain.hadoop-prep.v1` in `configSchemaVersion` (`SchemaVersions.supportedManifestConfig`). `ConfigLoader` still accepts only `scholarchain.config.v1`. `compressionCodec` is `none` when intermediate compression is disabled, and an explicit codec name when it is enabled.

`HadoopPrepConfig.executionMode` is required. The closed wire values are `local` and `cluster`. A missing field fails the loader. `local` allows LocalJobRunner. `cluster` must not set `mapreduce.framework.name` to `local`. `maxLocalSampleRecords` is a launch-level bound on accepted input records across the whole launch, not a per-mapper cap. `maxRecordBytes` bounds a record before its full text is materialized. `intermediateCompressionEnabled` means intermediate `FileOutputFormat` compression, not only shuffle compression.

`DatasetSnapshotRef` is unchanged: `source`, `snapshot`, and `retrievalDate`. Processing identity includes the source snapshot id, the retrieval date, and the checksum of the acquired bytes. A live API retrieval date is not a bulk snapshot date. Do not relabel an API retrieval as a monthly bulk snapshot.

`MatchCandidate` is block evidence. It is not a `MatchDecision`: it has no `MatchOutcome`, threshold, or claimed merge. `candidateId` is `match-candidate:{sha256}`. The hash input is the block key plus the two observations in canonical order, LF-joined, with no trailing LF. Each observation contributes source wire, source record id, dataset snapshot, and work id or an empty field. Canonical order is Scala `String.compareTo` on that same LF-joined order key. The lesser key is hashed first, so swapping the two sides does not change the id. Observation identity is source, source record id, and dataset snapshot. Equal identities are not a candidate: identical work ids are duplicates, and disagreeing work ids are a conflict. Stored `left` and `right` must already be in that order. Features stay sorted distinct `NamedNumber` values, values are finite, and a feature name must not be a `MatchOutcome` wire name. Provenance source is `SCHOLARCHAIN`, and its source record id is the candidate id.

`PreparationFeatures` is the bibliographic feature catalog. `prep-features-v1` records stay valid under the generic feature rules above. `prep-features-v2` is the policy Hadoop uses for the closed name set. For that policy, `DomainValidation` requires every feature name to be in the set, names distinct and sorted, values finite, and no `MatchOutcome` wire name. A v2 candidate may carry a sorted selection of the catalog. It must not carry any other name. The sorted names are:

- `block_size`
- `exact_shared_identifier` (1 when the block is an exact shared identifier, else 0)
- `same_work_id` (1 only when both observations already have the same validated work id; this is not a merge)
- `shared_affiliation_name_count`
- `shared_author_initial_count`
- `shared_author_name_count`
- `shared_coauthor_name_count`
- `title_equal`
- `venue_equal`
- `year_abs_delta` (use -1 when either year is absent)
- `year_equal`

Hadoop block keys are not a new type. They stay inside the existing `StableIds` block-key rules: trimmed, no CR or LF, and length at most 512. The grammars Hadoop emits are `exact:{namespace}:{value}`, `name:{normalized}`, `initial:{normalized}`, `title-year:{normalizedTitle}:{year-or-unknown}`, `venue:{normalized}`, `affiliation:{normalized}`, `coauthor:{normalized}`, and `fallback:{sourceWire}:{sourceRecordId}`. The `title-year` year segment is the decimal year, or `unknown` when the year is absent. A `fallback:` key is per observation (`sourceWire` and `sourceRecordId`). It must not by itself pair unrelated records. Do not put observations that missed every other block into one shared fallback group. Different observations keep different fallback keys.

`RejectRecord` is emitted when a valid domain record cannot be constructed. `source` is empty for a byte-level parse failure; do not invent `DBLP` or any other source. `datasetSnapshot` may also be empty. At least one of `diagnosticExcerpt` and `diagnosticHash` is required. The excerpt is at most 256 UTF-16 code units. The hash is lowercase SHA-256 hex. Closed `reasonCode` values are `MALFORMED_RECORD`, `UNSUPPORTED_RECORD_TYPE`, `INVALID_IDENTIFIER`, `MISSING_REQUIRED_FIELD`, `OVERSIZE_RECORD`, `OVERSIZE_XML_ENTITY_EXPANSION`, `UNSAFE_ENTITY`, `OVERSIZE_BLOCK`, `OVERSIZE_CANDIDATE_PAIRS`, `OVERSIZE_TEAM`, `SCHEMA_FAILURE`, `CONFLICTING_OBSERVATION`, `DUPLICATE_IDENTICAL_OBSERVATION`, and `PROVENANCE_MISMATCH`. Identical duplicates and contradictory observations use the last two different codes. Compare team size, block size, and pair expansion to the hadoop-prep limits and emit the matching oversize code. Do not truncate and call the result complete.

`IdentifierIndexEntry` is one observation of one normalized identifier. The row key includes source, source record id, and dataset snapshot, so one DOI shared by DBLP and Crossref stays two rows. `StableIds.normalizeIndexedIdentifier` produces the stored value. `StableIds.identifierPreferredWorkId` returns `Some(work:...)` for `doi`, `arxiv`, `dblp`, and `openalex-work`. It returns `None` for a parsed `orcid`, `openalex-author`, `ror`, `ringgold`, or `openalex-institution`; that row is a non-authoritative observation and must not be copied into a work id. `openalex-institution` is not in `IdentifierNamespace.workNamespaces`. Its indexed value is the bare OpenAlex institution token (`I` plus a positive integer) from `institutionIdFromOpenAlex`, with the `institution:openalex:` prefix removed. A URL such as `https://openalex.org/I79516672` and the bare token `I79516672` both normalize to `I79516672`. Malformed input returns an error and no work id. Emit `RejectRecord` with `INVALID_IDENTIFIER` instead of an index row. Unknown namespaces are not in `IdentifierNamespace`; reject them the same way.

`abstractTextRef` remains a `chunk:{64 hex}` or `profile:{64 hex}` id from `StableIds.chunkOrProfileId`. A URL, inverted index, or raw abstract is not a reference. `EmittedTextDocument` is the target record. No new abstract type is required. A supplied Crossref or OpenAlex abstract is an `EmittedTextDocument` with `documentType` `abstract`, `entityId` equal to the work id, and `sourceVersion` equal to the dataset snapshot. `WorkRecord.abstractTextRef` equals that chunk id. `documentType` `researcher-profile` uses the existing `profile:` prefix. `textId` must match the formula for that text.

`AuthorMention` has no affiliation field and must not gain one. `EnrichmentLink` requires a `targetId`, so it cannot store a publisher affiliation name when no ROR or Ringgold exists. `MentionAffiliation` is that additive record. Its fields are `schemaVersion`, `mentionId`, `source`, `sourceRecordId`, `datasetSnapshot`, `organizationName` (`Option[String]`), `ror` (`Option[String]`), `ringgold` (`Option[String]`), `institutionId` (`Option[String]`), `uncertainty`, and `provenance`. An empty `organizationName` means the name is absent. Validation rejects a blank string and rejects the literal placeholder `institution`. It also rejects a record that has no organization name, ROR, or Ringgold. `institutionId` is set only when it is exactly the ROR or Ringgold institution id of the populated field. Do not invent an institution id from a name. A name-only affiliation leaves `ror`, `ringgold`, and `institutionId` empty.

Reuse `WorkRecord`, `AuthorMention`, `PublicationTeam`, `AuthorshipRecord`, `CoauthorPairCandidate`, `Venue`, `Topic`, `GraphEdge`, `Provenance`, `RunManifest`, `ObservedIdentifier`, and `NamedNumber` without changing their fields or JSON names. `Institution` adds a trailing `observedSourceIds` field, defaulting to an empty vector. `OrcidActivityRecord` adds a trailing `workReferences` field, defaulting to an empty vector. Coauthor pair endpoints stay in `String.compareTo` order of the mention ids, and each ordinal stays the ordinal embedded in its own mention id. `CoauthorPairCandidate` full validation still needs `DomainValidation.check(record, work)` or a `WorkValidationContext`.

`GraphEdge` can carry `PUBLISHED_IN`, `HAS_TOPIC`, mention-sourced `AUTHORED`, and `AFFILIATED_WITH` from `researcher:orcid:{orcid}` to one institution id. Do not emit `RESOLVES_TO` or researcher `COAUTHORED_WITH`; those are identity decisions. Keep ROR and Ringgold in their own fields and in their own institution ids (`institution:ror:` and `institution:ringgold:`). Do not copy one into the other. A DOI or ORCID link is not authorship and not a cross-dataset merge.

`OrcidProfileRecord` exists because `CanonicalResearcher` is an identity record and `WorkRecord` would fabricate a publication. `OrcidActivityRecord` exists because an ORCID work summary has no author list, and one `GraphEdge` endpoint cannot retain both a ROR and a Ringgold. `observedDoi` and `observedWorkId` stay the preferred DOI fields. `observedWorkId` is set only on a work activity and only as `work:doi:{normalized DOI}`. `workReferences` keeps every declared external id: `externalIdType`, `value`, and `relationship` when the source supplied `external-id-relationship`. That includes the DOI, `other-id`, ISBN, and ISSN. Each `externalIdType` and `value` is trimmed and non-empty. A present `relationship` is trimmed and non-empty. Those references are evidence. They do not replace the preferred DOI and they do not merge records. Employment and education years stay in `startYear`. `Institution.institutionId` remains the preferred institution id, which may be the ROR id when the source also observed an OpenAlex institution id. `observedSourceIds` carries that other observation, for example `ObservedIdentifier(namespace = "openalex-institution", value = "https://openalex.org/I79516672", interpretation = SOURCE_OBSERVATION)`. Each entry needs a known `IdentifierNamespace` wire and a trimmed non-empty value. The vector does not create a researcher id or a work id. `EnrichmentLink` exists because `AFFILIATED_WITH` requires a researcher id, so an unresolved mention cannot use that edge. Venue, institution, and topic targets use the existing id parsers. `MentionAffiliation` exists for a mention whose affiliation is only a name, or whose ROR or Ringgold should stay on the mention without pretending the name is an institution id.

## Phase 8 embedding contracts (8A)

`EmbeddingContracts.schemaVersion` is `scholarchain.embedding.v1`; existing domain,
Spark and identity contracts remain unchanged. `EmbeddingDocument` retains stable chunk/profile
ID, source entity/window/run, rendering-template version, exact text, source row/field references,
and explicit `textSelection` (`generated-summary`, `permitted-abstract`, or
`paper-summary-fallback`). Abstract/fallback selections are paper-only. References assert locators,
not externally verified facts or abstract permissions: rendering and ingestion owners must bind
them to actual producer exports.

`EmbeddingModel.tag` length-frames model ID, explicit model version and output dimension using
UTF-8 byte lengths. `EmbeddingContracts.vectorKey(document, model)` extends the Phase 7
length-framing convention over seven fields: document type, original entity ID, window, template
version, chunk-policy version, zero-based chunk ordinal and model tag. This is a stable slot:
text, text-hashed `documentId` and source `runId` do not enter the key. Changed text in the same
slot therefore reaches the ingestion conflict guard; a source rerun cannot evade that guard.
`documentId` remains content-addressed metadata using unchanged `StableIds` formulas. Distinct
ordinals separate chunks, while a new template/chunk policy/model version creates a new slot.
The rendering owner must bind chunk-policy version to its algorithm and all segmentation limits;
changing a boundary policy requires a new policy version. Core rejects negative ordinals and
blank, whitespace/control-containing, or over-256-byte template/policy versions. Additive missing
slot fields decode to empty policy/-1 ordinal for compatibility but fail validation before writes.
A new model/version/dimension therefore has a new key. A work item's SHA-256 hashes the exact
UTF-8 text, with no normalization;
its pointer names ordinary S3 JSON, never S3 Vectors. `EmbeddingValidation.workItem` checks the
key binding, text hash, five-type index mapping and pointer, plus the document/model structure.

Phase 8B adds `chunkCount` and `wholeTextHash` to `EmbeddingDocument`. Renderers provide the
total chunk count and SHA-256 of the exact full text before chunking, including overlap only
as it appeared in the original text. These values do not alter vector keys or content IDs.
`EmbeddingContracts.groupKey(document, model)` length-frames type, entity, window, template,
chunk policy and model tag, excluding ordinal and run. Storage binds that group to count and
whole-text hash and must reject an inconsistent or incomplete group before embedding any member.
Counts must be positive and every ordinal less than its count. Multi-chunk documents require an
explicit lowercase 64-hex whole-text hash. For additive compatibility, missing group fields decode
to count 1 and an empty hash; that form is valid only for ordinal zero, where
`EmbeddingContracts.wholeTextHash(document)` uses the exact chunk text hash. A supplied hash for
a single chunk must match its text. Multi-chunk hash correctness and complete/unique ordinal
coverage require renderer and ingestion checks; single-record structural validation cannot prove
the full source text. Group fields stay in the ordinary-S3 document, without expanding vector
filter metadata.

`EmbeddingVectorMetadata.compact` emits only typed identity/model/template/hash/pointer fields.
Optional `identityFields` are limited to researcher, community, topic, institution and source-dataset
filters, at most 256 UTF-8 bytes each. Unknown fields fail validation and are excluded from
`compact`. All consumers must validate before side effects; the storage adapter additionally
applies service metadata/key/request limits. The core contracts deliberately depend on neither
storage nor RAG. `EmbeddingClient` preserves input order/cardinality and returns one
`EmbeddingSuccess` or `EmbeddingFailure` per text, with model and provider-attempt count.
Zero attempts means a preflight failure. Retry policy/provider execution belongs to RAG.

`SemanticContext` always serializes its descriptive-only usage label and false graph/metric
authority flags. `EmbeddingValidation.context` rejects changed authority, nonfinite scores,
invalid pointers/hashes and oversized excerpts. A ranking score or context excerpt cannot prove
an edge, path, component, count or bridge measure; synthesis must obtain those claims from
explicit graph/metric evidence. Structural validation is not source existence verification.

Four `wire/embedding-*.json` test resources freeze synthetic document, work-item, metadata and
context examples. They are contract fixtures and describe no observed researcher.

## Phase 9A runtime contracts

`QueryPlan`, `EvidenceItem`, `EvidenceBundle` and `AnswerClaim` retain their existing domain
wire formats and add defaulted optional `runtime` payloads. Existing frozen examples remain
readable. Runtime numerical claim values use decimal strings to preserve stored integer
precision. Per-claim `ClaimVerdict` maps to the existing overall `VerificationStatus`; explicit
abstention remains `ABSTAINED`. Audit contracts preserve all attempted and rejected claims.

`scholarchain.runtime-config.v1.json` is a local configuration example, with an unselected
Converse model placeholder and configured `us-east-2` region. It authorizes no live call.
`RuntimeConfigLoader` reads JSON only. Its validation includes the complete serial/parallel
critical path within `operations.synchronousDeadlineMs`; stage budgets include retries.
The legacy numeric window projection for an unbounded runtime window is compatibility
metadata only: actual retrieval and evidence use the stored window ID and optional bounds.
Runtime ranking filters identify a population and do not recompute metrics on filtered works.

Evidence-item IDs retain their existing parsers. The storage owner's immutable ordinary-object
item-to-bundle pointer index resolves an item ID through `EvidenceBundleStore.getItem`; no
new database table or index is required. Retrieval/synthesis/verifier implementations belong
to later subphases; these declarations are contracts only.

Phase 9A repair B2 gives identity resolution its own `resolver` limits, independent of
`retrieval.graphLimit`. The example permits 25 distinct canonical candidates, 16 source IDs,
32 evidence references, 16 affiliations and 8 source-run IDs per candidate. These conservative
output bounds keep common-name ambiguity and accumulated mention provenance reviewable;
they are configurable output caps, not measured latency guarantees or limits on cache-row count.
The larger evidence-reference allowance retains more source pointers than identity labels.
Legacy runtime configuration without the `resolver` object uses these same compatibility defaults.
Every bound must be positive. `ResearcherCandidate.provenanceSummary` optionally retains the
distinct merged count of each provenance list before clipping plus a truncation flag, including
context-derived evidence references and run IDs. An omitted summary means the original
producer supplied no count/truncation observation; it never implies completeness. Coauthor
context retains its separate truncation flag. Candidate-set overflow is disclosed by the RAG
resolver's bounded `Ambiguous` result, rather than failing identity resolution.

Phase 9B closes the evidence-partition contract gap at bundle admission.
`DomainValidation.check(EvidenceBundle)` uses `RuntimeContractValidation.bundleItems` when
the bundle has a runtime context. Every item must then carry its own runtime payload.
Deterministic items must have `descriptive=false` and cannot use the `TEXT_CHUNK` evidence
type. Semantic items must have `descriptive=true` and use `TEXT_CHUNK` or
`RESEARCHER_PROFILE`; graph, edge and metric locators, typed numeric/flag/ID values, metric
versions and deterministic convergence/approximation qualifications are rejected there.
Provenance fields such as source references, source-run IDs, subject/window IDs and text
pointers remain available without authorizing a factual claim. Vector mode still rejects
any deterministic partition. Legacy bundles without a runtime context and their frozen
wire examples retain their original validation. The older `bundle(context,itemIds)` helper
remains a structural-only compatibility check; admission must use the actual-item helper.

Runtime evidence persisted through the immutable item index also needs content-bound IDs:
the same node path or edge can recur with different windows, source runs or observations.
`RuntimeEvidenceIds.bind(item)` sets the additive optional runtime
`contentBindingVersion` to `runtime-evidence-content-v1`, then hashes the complete item
excluding only `evidenceId`. Object keys are sorted recursively, array order is retained,
and the binding includes text, score, source URI, provenance, runtime values and the version
marker. `expectedId(item)` returns that expected ID for an already marked item.
Graph paths, edges and metrics retain their precise evidence types and existing
`evidence:graph-path:`, `evidence:edge:` and `evidence:metric:` formats. Researcher profiles
use the existing `profile:` format; other types use `chunk:`. Metric locators retain the
actual stored policy version. Domain validation checks both the content binding and all
existing type-specific locator requirements; a changed payload with an unchanged ID fails.
New runtime builders use the binding helper. The marker defaults to `None`, so old runtime
records and frozen legacy examples retain their original locator-only ID rules. Unknown
binding versions fail closed. This is an additive identity contract, not a new wire hierarchy.

`RuntimeBundleContext.resolvedCandidates` defaults to an empty vector for old JSON and retains
the bounded resolver observations needed to cite display names, source IDs and individual
confidence values. Bundle validation checks canonical researcher IDs, nonblank names, distinct
nonblank source/reference/affiliation lists, source-run IDs, confidence bounds and provenance
count/truncation summaries. Candidate IDs are unique within the bundle. The evidence builder
enforces configured resolver bounds and budgets rendered identity context; the core contract
does not read runtime configuration or invent missing confidence observations.

# Phase 3 independent code review

STATUS: REQUEST_CHANGES

OWNER: `code-reviewer` (`gpt-6-sol`, high reasoning effort). Read-only review; the coordinator transcribed this report. The reviewer made no repository edits.

WORK ORDER: Review the Phase 3 dataset and domain changes against the course Phase 3 requirements, repository ownership map, official dataset sources, contracts, tests, and full worktree diff.

## Findings

1. **P1 — Unsupported DBLP snapshot provenance.** Owner: `dataset-engineer`. `datasets/dataset-manifest.yaml:20` claims a 2026-10-03 monthly “delta,” DOI `10.4230/dblp.xml.2026-10-03`, size, and MD5. The [official Dagstuhl collection](https://drops.dagstuhl.de/entities/collection/10.4230/dblp.xml) listed 2026-09-01 as its latest release during review and describes full XML snapshots. `datasets/scripts/acquire_samples.py:31` hardcodes the same unverified artifact URL. Verify the real release and substantiate its size and checksum from the official artifact; do not claim the current identity as verified.
2. **P1 — DBLP byte cap is not enforced.** Owner: `dataset-engineer`. `datasets/scripts/acquire_samples.py:82-91` sends an 8 MiB `Range` request but calls unbounded `resp.read()` without checking status or `Content-Range`. A server ignoring `Range` can deliver the full corpus. Enforce a response byte limit and reject an unexpected full response.
3. **P1 — Conflict match outcome is absent.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/Enums.scala:19` has accepted, rejected, and unresolved outcomes only. The course requires conflict match records, so the current `MatchDecision` wire contract cannot represent one without mislabeling it.
4. **P1 — Invalid coauthor pairs can pass.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala:129` checks mention IDs and lexical order but does not ensure both mentions belong to the same work or that embedded ordinals match `leftOrdinal` and `rightOrdinal`. Unrelated publication mentions can form a false collaboration pair.
5. **P2 — Refreshed DBLP excerpts may be invalid XML.** Owner: `dataset-engineer`. `datasets/scripts/acquire_samples.py:94` extracts record text without a DTD declaration. [DBLP documents](https://dblp.org/faq/16154937.html) that its XML uses named entities from its DTD. The reviewer reproduced an `undefined entity` parse failure with an excerpt containing `&eacute;`.
6. **P2 — Work provenance can contradict the work record.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala:14` validates source fields and provenance independently but does not compare their source and source-record ID. A DBLP work with Crossref provenance can pass.
7. **P2 — Evidence IDs are restricted to text chunk/profile IDs.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala:326` rejects `EvidenceItem.evidenceId` outside `chunk:` or `profile:`; line 376 applies the same restriction to claims. Graph-path, metric, and edge evidence lack a distinct stable evidence-ID function and must masquerade as text chunks.

## Validation and limits

The reviewer ran `git status --short --untracked-files=all`, `git diff --stat HEAD`, `python3 datasets/scripts/acquire_samples.py --mode regenerate` (four committed samples verified; this mode performs no writes or network access), `/tmp/scholarchain-datasets-venv/bin/python datasets/scripts/validate_datasets.py` (four datasets, samples, and script bounds reported OK), and `cd datasets && shasum -a 256 -c samples/SHA256SUMS` (all four samples OK). The system Python could not run `validate_datasets.py` because it lacks PyYAML. The reviewer also reproduced the XML named-entity failure in memory.

The reviewer did not run `sbt check` because it writes build outputs and the test marker outside the reviewer’s read-only role. `docs/agent-runs/phase-03/` was absent at review time, so owner-run results and acquisition evidence could not be corroborated. The official DBLP binary and MD5 sidecar were inaccessible through the reviewer’s web tool. The reviewed [OpenAlex](https://github.com/ourresearch/openalex-docs/blob/main/license.md), [ORCID](https://info.orcid.org/public-data-file-use-policy/), and [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) license summaries otherwise matched their primary sources.

NEXT GATE: Route findings 1, 2, and 5 to `dataset-engineer`, and findings 3, 4, 6, and 7 to `domain-engineer`. The authorized owners must repair their files, run `sbt check` and dataset validation, and submit exact results. Then obtain a fresh independent read-only review. No human acceptance or commit follows from this verdict.

## Second independent review after owner repairs — 2026-10-05

STATUS: REQUEST_CHANGES

OWNER: `code-reviewer` (`gpt-6-sol`, high reasoning effort), in a fresh read-only context. The coordinator appended this verdict without modifying implementation files.

The reviewer confirmed fixes for the hard response cap and HTTP 200 rejection, `CONFLICT` wire outcome, mention ordinal checks, work/mention provenance comparison, and distinct graph-path, metric, and edge evidence IDs. It found these remaining or new issues:

1. **P1 — DBLP release claim remains unsupported.** Owner: `dataset-engineer`. `datasets/dataset-manifest.yaml:20-29`, `datasets/scripts/acquire_samples.py:39-43`, and the sample XML comment claim a verified 2026-10-03 snapshot, DOI, size, and MD5. The [official Dagstuhl collection](https://drops.dagstuhl.de/entities/collection/10.4230/dblp.xml) listed 2026-09-01 as latest during review; its [September artifact page](https://drops.dagstuhl.de/entities/artifact/10.4230/dblp.xml.2026-09-01) identifies a different actual file and checksum. The asserted October artifact and sidecar could not be opened and an exact DOI search found no result. Remove or replace the unsupported verification claim with official evidence.
2. **P1 — A coauthor pair can cite the wrong work.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala:492-513` checks that mention IDs match each other and match their ordinals, but not that their embedded source record matches pair provenance or `workId`. A Berkeley pair copied with both mentions from `series/sapere/NasutoB13` passes while keeping the Berkeley work and provenance.
3. **P2 — Standard XML escapes break DBLP refresh.** Owner: `dataset-engineer`. `datasets/scripts/dblp_entities.py:79-100` treats `&amp;` as unsupported. `dblp_sample_prolog("<title>A &amp; B</title>")` raises `ValueError`. The earlier named-entity case with `&eacute;` was fixed.
4. **P2 — Oversized mention ordinal throws during validation.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/StableIds.scala:390-412` accepts `mention:dblp:foo#2147483648` in a first parse, then `.toInt` throws `NumberFormatException` in pair validation instead of returning a domain violation.
5. **P3 — Generated Python bytecode is untracked.** Owners: `dataset-engineer` for cleaning `datasets/scripts/__pycache__/*.pyc`, and `build-engineer` for any `.gitignore` change. Keep generated bytecode out of the Phase 3 commit.

The reviewer ran read-only git and source-inspection commands and reproduced finding 3 with `python3 -B -c 'import sys; sys.path.insert(0, "datasets/scripts"); from dblp_entities import dblp_sample_prolog; print(dblp_sample_prolog("<title>A &amp; B</title>"))'`, which exited 1. It did not run `sbt check`, refresh samples, or edit files. The coordinator's independent checks are recorded separately in `test-report.md`. No Phase 3 owner report existed for reviewer corroboration at the time of this verdict.

NEXT GATE: Route findings 1 and 3 to `dataset-engineer`, 2 and 4 to `domain-engineer`, and 5 to the stated owners. Record repair and owner test evidence, then obtain a fresh independent read-only review. Do not accept or commit Phase 3 from this verdict.

## Third independent review after further repairs — 2026-10-05

STATUS: REQUEST_CHANGES

OWNER: `code-reviewer` (`gpt-6-sol`, high reasoning effort), in a fresh read-only context. The coordinator appended this verdict; the reviewer made no repository edits.

The reviewer confirmed repairs for bounded DBLP reads and HTTP 206 checks, `CONFLICT`, same-work mention and ordinal checks, `WorkRecord` provenance agreement, non-text evidence IDs, XML predefined and named entities, oversized ordinal domain violations, and Python bytecode exclusion. Two P1 findings remain:

1. **Unsupported DBLP release verification.** Owner: `dataset-engineer`. `datasets/dataset-manifest.yaml:20-38`, `datasets/scripts/acquire_samples.py:39-46`, `datasets/schemas/dblp-xml.md:5-9`, and `datasets/samples/dblp/linked-records.xml:2` claim the October 3, 2026 DOI, release, byte size, and MD5 were verified from Dagstuhl. The accessible [official collection](https://drops.dagstuhl.de/entities/collection/10.4230/dblp.xml) listed September 1 first; its [September artifact page](https://drops.dagstuhl.de/entities/artifact/10.4230/dblp.xml.2026-09-01) has a different file and MD5. The asserted October artifact and DOI could not be opened through the reviewer's web tool, exact searches found no result, and a shell request failed at DNS resolution. This does not establish that an October release is nonexistent; it means the repository's verification claim and pinned refresh URL lack independently reproducible evidence. Provide official accessible evidence or pin a supported release, then update every affected manifest, schema, sample, and fixture claim through its owner.
2. **Pair provenance can contradict the work and mentions.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala:513-539` derives the candidate's source record from `workId` **or** provenance. A pair whose `workId` and mention IDs use `series/sapere/NasutoB13`, but whose provenance names `series/sapere/BerkeleyR13`, can pass. Require the mentions, provenance, and any source record embedded in `workId` to agree; add a test for that concrete case.

The reviewer ran read-only git and source inspections, `git check-ignore` on Python bytecode (matched `.gitignore:24`), and a `python3 -B` XML parse of `&amp;` and `&eacute;` (parsed text `A & B é`). It did not run `sbt check` or refresh samples. The coordinator's separately observed passing checks are in `test-report.md`.

NEXT GATE: Route finding 1 to `dataset-engineer` and finding 2 to `domain-engineer`; obtain repair tests, authoritative DBLP source evidence, and another independent read-only review. No human acceptance or commit follows from this verdict.

## Fourth independent review after further repairs — 2026-10-05

STATUS: REQUEST_CHANGES

OWNER: `code-reviewer` (`gpt-6-sol`, high reasoning effort), in a fresh read-only context. The coordinator appended this verdict; the reviewer made no implementation edits.

The previous DBLP release finding is **resolved**. A bounded, read-only request to the [official October 2026 artifact page](https://drops.dagstuhl.de/entities/artifact/10.4230/dblp.xml.2026-10-03) returned HTTP 200 and showed DOI `10.4230/dblp.xml.2026-10-03`, the linked `dblp-2026-10-03.xml.gz`, and MD5 `cbd329100ea1bbb2873fa2f6d414ea00`. The [official MD5 sidecar](https://drops.dagstuhl.de/storage/artifacts/dblp/xml/2026/dblp-2026-10-03.xml.gz.md5) matched. A HEAD request to the gzip returned HTTP 200, `Content-Length: 1107081001`, and `Content-Type: application/x-gzip`. No full corpus was downloaded. The Dagstuhl collection page still displayed September first; its ordering was not evidence that October did not exist.

Two domain findings remain:

1. **P1 — DOI and arXiv work IDs can identify a different work.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala:517-537` treats an authoritative `work:doi:` or `work:arxiv:` ID as having no embedded source record, so `embeddedAgrees` is vacuously true. A Berkeley pair copied with valid `work:doi:10.5555/unrelated` while retaining Berkeley mentions and provenance passes structural validation, despite the pair contract stating it comes from one work (`Records.scala:98-109`). Add a source-to-authoritative-ID binding or validation against the corresponding `WorkRecord`, and test the mismatched DOI case.
2. **P2 — A source-native WorkRecord ID can contradict its source record.** Owner: `domain-engineer`. `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala:19-44` parses `workId` but does not compare a `work:dblp:<key>` with `sourceRecordId` when DOI and arXiv ID are absent. A Berkeley record with `work:dblp:series/sapere/NasutoB13` passes, mislabeling publication evidence.

The reviewer confirmed the earlier pair/provenance and source-native pair mismatch repairs, byte cap, XML entity handling, oversized ordinal behavior, conflict outcome, evidence IDs, and Python bytecode exclusion on inspection. The reviewer ran read-only source/git checks, four Python unit tests, manifest validation, four sample checksum checks, and the bounded official-source requests above. It did not run `sbt check`; the coordinator's separately observed results are recorded in `test-report.md`. No Phase 3 owner work order or owner report existed for corroboration at this review.

NEXT GATE: Route both findings to `domain-engineer`, obtain targeted repair tests and owner evidence, then request another independent read-only review. No human acceptance or commit follows from this verdict.

## Fifth independent review after further repairs — 2026-10-05

STATUS: REQUEST_CHANGES

OWNER: `code-reviewer` (`gpt-6-sol`, high reasoning effort), in a fresh read-only context. The coordinator appended this verdict; the reviewer made no repository edits.

The earlier source-native `WorkRecord` mismatch is fixed at `DomainValidation.scala:45-61`, with an adversarial test at `ValidationSpec.scala:277-295`. Three domain contract findings remain:

1. **P1 — An unrelated DOI pair still passes validation.** Owner: `domain-engineer`. `DomainValidation.scala:537-543` binds `workId` only to the DOI in the pair's own `provenance.sourceUri`. Copying the Berkeley fixture with both `workId = work:doi:10.5555/unrelated` and `provenance.sourceUri = https://doi.org/10.5555/unrelated` leaves Berkeley mentions and source record unchanged but passes the current checks. The new test at `ValidationSpec.scala:226-240` changes only `workId`, so it misses this case. Bind to the corresponding `WorkRecord` or another independent source-to-authoritative-ID contract, and add the combined mismatch test.
2. **P2 — Valid authoritative-ID pairs are rejected.** Owner: `domain-engineer`. `StableIds.scala:124-135` derives an authoritative ID from a DOI URI or source-native record, but never arXiv. `DomainValidation.scala:585-598` consequently rejects a valid `work:arxiv:` pair, and rejects a DOI pair when optional `provenance.sourceUri` is absent. Add positive tests for both supported cases.
3. **P2 — Team and authorship records allow mismatched mentions.** Owner: `domain-engineer`. `DomainValidation.scala:119-151` parses IDs independently. An `AuthorshipRecord` with `position = 2` and a `#1` mention ID passes; a Berkeley `PublicationTeam` with two Nasuto mention IDs also passes. Check the position and source-record relationships and add adversarial tests.

The reviewer inspected the Phase 3 dataset and core worktree, ran `python3 -B datasets/scripts/acquire_samples.py --mode regenerate` in its read-only context (verified four samples), ran four Python unit tests, validated the manifest, and checked all four sample hashes. It did not run `sbt check`; the coordinator's independently observed result is in `test-report.md`. The October DBLP release was verified in the fourth review; the official pages were inaccessible to this reviewer's web tool. The findings above are code-path deductions, not executed Scala mismatch probes.

The Phase 3 `prompt.md`, `owner-report.md`, `repairs.md`, and applicable human gate are still absent from the evidence directory. Worktree state alone does not establish the author of the `.gitignore` edit, which belongs to `build-engineer`.

NEXT GATE: Route all three findings to `domain-engineer`, obtain targeted repair tests and owner evidence, then request a fresh independent read-only review. Do not accept or commit Phase 3 from this verdict.

## Sixth independent full review after further repairs — 2026-10-05

STATUS: REQUEST_CHANGES

OWNER: `code-reviewer` (`gpt-6-sol`, high reasoning effort), in a fresh read-only context. The coordinator appended the consolidated verdict; the reviewer made no repository edits. The reviewer was explicitly asked to inspect the full Phase 3 worktree and report all material findings in one pass.

The three fifth-review cases are addressed on inspected paths: the paired `workId`/URI mismatch is rejected while the record DOI remains unchanged; DOI without URI and arXiv pairs validate; authorship position and team mention/source mismatches are checked. The full sweep found these additional issues:

1. **P1 — Frozen metrics count the author as a coauthor.** Owner: `domain-engineer`. `Fixtures.scala:292-300` and `wire/researcher-metrics.json:5-9` describe one publication, one distinct and total coauthor occurrence, but set average and maximum coauthors per paper to 2. Under the [course metric definitions](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#what-must-be-measured), both should be 1. `DomainValidation.scala:230-249` only checks nonnegativity, so the contradictory fixture passes.
2. **P1 — Duplicate team mentions inflate team size.** Owner: `domain-engineer`. `DomainValidation.scala:648-681` checks source alignment but not distinct mention IDs or ordinals. `Fixtures.team.copy(memberMentionIds = Vector(Fixtures.berkeleyMentionId, Fixtures.berkeleyMentionId))` can retain `teamSize = 2` and pass, representing one author twice.
3. **P1 — Authoritative work binding still trusts derived fields.** Owner: `domain-engineer`. `DomainValidation.scala:602-623` rejects the old DOI pair when `doi` remains unchanged. If both `Fixtures.pair.workId` and `Fixtures.pair.doi` are retargeted to `10.5555/unrelated`, Berkeley mentions and provenance remain but `authoritativeWorkIdForMentions` (`DomainValidation.scala:684-699`) derives the expected ID from the altered DOI. `AuthorshipRecord` and `PublicationTeam` paths at `DomainValidation.scala:625-679` derive DOI/arXiv from `workId` itself. Bind derived records to an independently validated `WorkRecord` or source observation; test the combined retargeting.
4. **P1 — Graph-path evidence may omit or misstate its path.** Owner: `domain-engineer`. `DomainValidation.scala:361-370` validates the `evidence:graph-path:` ID shape but does not require `graphPath` or verify its nodes against the ID. `Fixtures.graphPathEvidence.copy(graphPath = None)` can pass. Metric and edge evidence also lack locator fields from which their hashes could be checked.
5. **P2 — Graph edges accept malformed endpoints and properties.** Owner: `domain-engineer`. `StableIds.scala:347` requires only nonblank endpoint IDs; `DomainValidation.scala:325-358` validates the recomputed hash and required coauthorship property names, but not endpoint classes or property values. A `COAUTHORED_WITH` edge from `abc` to `def` with a recomputed ID and `jointPublicationCount = not-a-number` can pass.
6. **P2 — Crossref work source DOI can disagree with its work ID.** Owner: `domain-engineer`. `DomainValidation.scala:14-74` verifies the `doi`/`workId` relationship but does not require Crossref's DOI-valued `sourceRecordId` to agree. Changing both `sourceRecordId` and provenance to another valid DOI while retaining the original `doi` and `workId` can pass.
7. **P2 — Config accepts graph years outside domain range.** Owner: `domain-engineer`. `ConfigLoader.scala:460-464` checks only start <= end; `-1..0` and `10000..10001` can load, while `DomainValidation.scala:790-802` rejects years outside 1..9999.
8. **P2 — API refresh responses are not byte bounded.** Owner: `dataset-engineer`. `datasets/scripts/acquire_samples.py:81-84` calls `resp.read()` without a cap for OpenAlex, ORCID, and Crossref. The `MAX_WORKS = 1` request limit does not bound response bytes; add a hard cap and an oversized-response test.
9. **P2 — DBLP sample refers to an absent DTD.** Owner: `dataset-engineer`. `datasets/samples/dblp/linked-records.xml:3` declares `dblp-2023-06-28.dtd`, which is not packaged beside the sample. The current ElementTree check ignores the external DTD, but an offline validating/DTD-resolving Phase 4 reader may fail. Make the sample self-contained or provide a local DTD and resolution rule.
10. **P2 — ORCID schema note contradicts sample.** Owner: `dataset-engineer`. `datasets/schemas/orcid-record.md:26-29` says the committed sample has no DOI-bearing public works list, while `datasets/samples/orcid/records.jsonl` has a DOI external ID in `activities-summary.works.group[7]`.

Separate process/evidence gaps:

11. **P2 — No versioned runnable configuration file.** Owner: `domain-engineer`, with coordinator routing if placed outside `modules/core/**`. `ConfigLoader.scala:192` requires `SCHOLARCHAIN_CONFIG`; the only complete configuration is a test string in `ConfigLoaderSpec.scala:8`. The [Phase 3 work order](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-3-define-contracts-configuration-and-dataset-manifests) requires environment variables plus a versioned HOCON or YAML file.
12. **P2 — Phase evidence is incomplete.** Owner: Phase 3 coordinator; `.gitignore` author evidence involves `build-engineer`. Only `review.md` and `test-report.md` exist in `docs/agent-runs/phase-03/`. `prompt.md`, `owner-report.md`, and `repairs.md` are required by `docs/agent-runs/README.md`. The worktree does not establish who authored the build-engineer-owned `.gitignore` edit. Human gate and accepted commit are future steps, not current approval.

The reviewer ran read-only `python3 -B datasets/scripts/acquire_samples.py --mode regenerate` (verified four samples), four Python unit tests, manifest validation, and four sample SHA-256 checks; all passed. It inspected the full dataset/core files and frozen wire examples. The counterexamples above are code-path deductions, not executed Scala probes. It did not run `sbt check`; coordinator results are in `test-report.md`. The prior official Dagstuhl verification remains the basis for the October DBLP snapshot claim; its page could not be reopened through the reviewer's web tool in this round.

NEXT GATE: Route findings 1-7 and 11 to `domain-engineer` (with ownership routing for the config file), 8-10 to `dataset-engineer`, and evidence item 12 to the coordinator/build owner. Add targeted tests and owner reports, then obtain another independent read-only review. Do not accept or commit Phase 3 from this verdict.

## Seventh independent review after sixth-review repairs — 2026-10-05

STATUS: APPROVE

OWNER: `code-reviewer` (`inherit`, Grok 4.7), agent `9ca96605-a003-47dc-a704-b077244823f9`. Read-only. The coordinator appended this verdict. The reviewer made no repository edits.

The reviewer checked findings 1–12 from the sixth review against the current source and the 17:18 CDT JUnit XML from `sbt-launch.jar check`. Core tests were 52 with 0 failures. Build-verification tests were 2 with 0 failures. `.claude/.last-test-run` was `success=true` at timestamp `1791238702020`. The reviewer did not re-run `sbt`, dataset validation, or checksums. It accepted the coordinator’s recorded `sbt check` because the on-disk reports match the current specs. The Python regenerate, validation, unit, and checksum commands were not re-run.

No remaining defect was routed. `human-gate.md` and `accepted-commit.md` stay unwritten. This verdict does not accept Phase 3.

NEXT GATE: Human architect decision. Do not commit or push from this verdict.

## WorkRecord binding reviews — 2026-10-05

The human asked for one tightening after the seventh approval: a coauthor pair must not authorize its own DOI. It must be checked against the corresponding `WorkRecord`.

First repair review, agent `ddac278d-1daf-45bf-ba73-deeb9b6bed50`, returned `REQUEST_CHANGES`. The DBLP cases held. `DomainValidation` returned true for every source other than DBLP and OpenAlex, so a Crossref or ORCID pair could still set `workId` and `doi` to `10.5555/unrelated`.

Repair owner: `domain-engineer` `969b6ead-07ac-4e11-a466-712f36168c70`. Bibliographic work IDs now bind to the registered `WorkRecord` for every source. Owner-reported `sbt -batch check` exit 0: 54 core tests, 2 build-verification tests.

Second repair review, agent `22f20892-f0f8-44d3-98c6-3547970d0411`, returned `APPROVE`. Read-only. No repository edits. Retained JUnit XML at `2026-10-05T17:53:14` shows `ValidationSpec` 31, `ConfigLoaderSpec` 8, `StableIdSpec` 10, and `SerializationContractSpec` 5, all with 0 failures (54). Build-verification tests were 2 with 0 failures. The Crossref matching, unrelated-DOI, and URI-spoof cases, and the three existing DBLP cases, hold in source and in that XML. `sbt` was not re-run. This verdict does not accept Phase 3.

NEXT GATE: Human architect decision. Do not write `human-gate.md` or `accepted-commit.md` from this review. Do not commit or push.

## Eighth independent full review after WorkRecord binding repairs — 2026-10-05

STATUS: REQUEST_CHANGES

OWNER: `code-reviewer` (`gpt-6-sol`, high reasoning effort), fresh read-only context. The coordinator appended the verdict; the reviewer edited no repository files. This review examined the current worktree beyond the prior repair cases and returned all material findings in one pass.

All eight code findings belong to `domain-engineer`:

1. **P1 — Work binding is process-order dependent.** `DomainValidation.scala:10-50,118-120,606-614` keeps bibliography in a process-wide mutable `TrieMap` keyed only by `(source, sourceRecordId)`. A valid DOI pair fails before its `WorkRecord` is checked, while a second validated same-key work overwrites the first binding. Snapshot and run are excluded. Use an explicit validated work input or immutable, scoped lookup.
2. **P1 — WorkRecord can register a false DOI.** `DomainValidation.scala:57-106` does not compare DOI/work ID with DOI-valued `provenance.sourceUri` or `externalUrl`. `Fixtures.work.copy(doi = Some("10.5555/unrelated"), workId = "work:doi:10.5555/unrelated")` retains original DOI URLs yet passes and registers a false binding.
3. **P1 — Authorship and team binding can trust a spoofed URI.** `DomainValidation.scala:31-43,708-776` falls back to each record's own provenance URI when no `WorkRecord` is registered. After clearing the registry, changing both `workId` and URI to an unrelated DOI while keeping original DBLP mention IDs can pass.
4. **P1 — ResearcherMetrics accepts impossible counts.** `DomainValidation.scala:819-854` permits positive collaboration counts with zero publications, incorrect averages for multiple publications, and weighted degree inconsistent with total coauthor occurrences. For example, two publications, four occurrences, average one, maximum three, and weighted degree zero can pass. The [course definitions](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#what-must-be-measured) require these to agree.
5. **P2 — Coauthorship graph properties can conflict.** `DomainValidation.scala:889-927` reads only the first property with each name, allowing a duplicate conflicting value, and does not reject firstCollaborationYear after lastCollaborationYear. `representativeWorkIds` is parsed as a single work ID without a defined multiwork representation.
6. **P2 — Crossref records without DOI can take unrelated work IDs.** `DomainValidation.scala:88-106,637-655` skips DOI/source-record agreement and source-native binding when `doi = None`. A Crossref work with the original DOI-valued source record and `workId = work:dblp:any` can pass.
7. **P2 — Some graph edges cannot cite their actual source.** `DomainValidation.scala:382-383,856-887` requires every `GraphEdge.sourceEvidence` to parse as a work ID. An `AFFILIATED_WITH` edge from an ORCID employment record cannot cite the ORCID record.
8. **P2 — Some GraphNode IDs accept bare prefixes.** `DomainValidation.scala:1052-1073` accepts `venue:`, `institution:`, and `topic:` as IDs, contrary to the Phase 3 malformed-ID gate.

**Specification interpretation:** `ConfigLoader.scala:16-18,206-221` accepts JSON syntax only. `docs/agent-runs/phase-03/prompt.md:17` explicitly authorizes a JSON HOCON profile, while the [course Phase 3 work order](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-3-define-contracts-configuration-and-dataset-manifests) names HOCON or YAML. Record a course-compliance decision or provide a loader and file for a named format; the reviewer kept this separate from the eight code defects.

**Evidence:** The prior `test-report.md` ended at 44 core tests while `owner-report.md` reported 52 and current retained JUnit XML showed 54. The coordinator appended its own current observed 54-core/2-build and dataset results to `test-report.md` after this review; that evidence gap is now resolved. Human gate and accepted commit remain pending by design.

The reviewer ran read-only sample regeneration (verification mode), dataset manifest validation, six Python tests, four sample SHA-256 checks, `git diff --check`, and inspected retained JUnit XML (54 core tests, zero failures). It did not run sbt or edit files. The coordinator's separately observed `sbt check` appears in `test-report.md`. Scala counterexamples above were deduced from current validation branches, not executed as new tests.

NEXT GATE: Route findings 1-8 to `domain-engineer` for coordinated contract repair and targeted tests, resolve the config-format interpretation against the course work order, then obtain a fresh independent review. Do not accept or commit Phase 3 from this verdict.

## Ninth independent review after delegated domain repair

STATUS: REQUEST_CHANGES — two P2 findings. OWNER: `/root/phase3_repaired_code_review`, `code-reviewer` (`gpt-6-sol`, high reasoning effort). The coordinator assembled this verdict; the reviewer edited no files.

All eight eighth-review areas are addressed in the inspected implementation. The reviewer verified explicit immutable work context, source and snapshot binding, DOI/arXiv/Crossref checks, the complete canonical metric population, typed graph coauthorship properties and ORCID source-record evidence, shared reference ID parsers, both AUTHORED endpoint forms, and frozen wire examples. Two cases remain, both owned by `domain-engineer`:

1. **P2 — All-solo metrics accept tiny nonzero collaboration values.** `DomainValidation.scala:842-844,868-883` permits average and weighted degree `1e-13` for a record with three publications and zero distinct/total/maximum coauthors because the zero comparison uses a `1e-12` absolute tolerance. Require exact zero when total occurrences are zero, while retaining ratio rounding tolerance for positive values.
2. **P2 — Coauthorship work evidence can be unrelated to supporting publications.** `DomainValidation.scala:448-508` permits replacing singleton `Fixtures.graphEdge.sourceEvidence` with `GraphSourceEvidence.Work("work:doi:10.5555/unrelated")` and recomputing `edgeId`, while preserving one joint publication, the original representative work and provenance. Bind work evidence to supported representative publications and test the recomputed-ID case.

The JSON profile is explicitly authorized by the human work order and is valid HOCON syntax under the [primary HOCON specification](https://github.com/lightbend/config/blob/main/HOCON.md). Its restricted parser is documented and is not a separate blocker in this review. This corrects the earlier configuration interpretation without claiming instructor approval.

The reviewer parsed all 26 frozen wire JSON files, compared `.conf`/`.json` resources, and ran `git diff --check`; it did not run sbt or edit files. The source-derived counterexamples were not executed as new Scala tests. Owner fresh-JVM suite 23/23 and coordinator check 77 core/2 build with dataset gates are recorded in the reports.

NEXT GATE: The coordinator routed both findings to the same domain owner for targeted repairs and tests. Independent review and human acceptance remain pending.

## Tenth independent review of final delegated repairs

STATUS: APPROVE. OWNER: `/root/phase3_final_repair_review`, fresh `code-reviewer` (`gpt-6-sol`, high reasoning effort), read-only. The coordinator assembled this verdict.

Both ninth-review P2s are fixed. `DomainValidation.scala:864-872` requires exactly zero average and weighted degree when total occurrences are zero; positive values retain documented tolerance. `DomainValidation.scala:904-917` binds Work evidence to representative publications for COAUTHORED_WITH, the work target for AUTHORED, and work source for PUBLISHED_IN/HAS_TOPIC. Generic DERIVED_FROM/SUPPORTED_BY may retain independent supporting works. Four regressions at `ContractRepairSpec.scala:642-723` cover the prior counterexamples and valid multiple works/publication endpoints/generic relationships.

The reviewer rechecked all eight earlier areas in the finished core source, immutable WorkValidationContext, stable ID parsers, tests, and wire formats and found no material defect or regression. Read-only checks: `git status --short --untracked-files=all`, `git diff --check` (exit 0), Python `-B` parse of all 26 frozen wire JSON files, config `.conf`/`.json` byte comparison (exit 0), and source/report inspection. The reviewer did not run sbt or edit files. Owner targeted 27/27 and full 81-core/2-build results plus coordinator independent full check are in `owner-report.md` and `test-report.md`.

LIMITS: Code and provenance consistency checks cannot prove external source contents or authorize researcher identity decisions. The reviewer approves these repairs; human Phase 3 acceptance and any commit/push are separate gates.

NEXT GATE: Human architect review of the current Phase 3 worktree and acceptance. No human-gate record or accepted commit is authored by this code review.

## Eleventh independent review of the current Phase 3 worktree — 2026-10-05

STATUS: COMPLETE

OWNER: [Phase 3 code review retry](2e5ca20a-cb83-4b77-aa2b-3a65d4f8c979), `code-reviewer` using `grok-4.7-high`. Read-only. The coordinator assembled this verdict; the reviewer edited no files. An earlier attempt, [Phase 3 code review](ef3916b4-1eda-4596-bb21-27216594d493), stalled before returning a verdict and is not evidence.

WORK ORDER: Fresh read-only review of the current Phase 3 worktree against the course Phase 3 contract, configuration, and manifest requirements, `docs/agents.md`, `docs/agent-runs/README.md`, and `docs/agent-runs/phase-03/prompt.md`, including the eighth-review domain repair. The authorized config scope is the JSON file read as the HOCON profile. Prior verdicts, including the tenth-review APPROVE, were not treated as binding. This review does not write `human-gate.md`, does not accept Phase 3, and does not authorize a commit or push.

FILES CREATED: none

FILES MODIFIED: none

COMMANDS RUN: The reviewer ran no shell commands. It did not run `sbt check`, Python tests, `shasum`, `git status`, `git diff`, or a live Dagstuhl request. Inspection was file reads of the Phase 3 prompt, ownership map, phase reports, `datasets/**`, `modules/core/**`, `.git/HEAD`, and `.git/refs/heads/main`. The coordinator separately parsed `datasets/samples/orcid/records.jsonl` with `python3` and confirmed the schema mismatch below.

TEST RESULTS: Not re-executed by the reviewer. Retained JUnit XML under `modules/core/target/test-reports/`, timestamp `2026-10-05T21:47:54`, shows `ValidationSpec` 31, `ConfigLoaderSpec` 8, `StableIdSpec` 10, `ContractRepairSpec` 27, and `SerializationContractSpec` 5, each with 0 failures (81 core tests). That artifact agrees with the coordinator’s claimed final `sbt -batch check` in `test-report.md` (81 core, 2 build-verification, exit 0, local completion 2026-10-05 21:47:56). Python `test_acquire_bounds.py` (6 tests), `validate_datasets.py`, and sample SHA-256 checks cited there were not re-run.

VALIDATION RESULTS: REQUEST_CHANGES

The eighth-review domain defects and the two ninth-review follow-ups are closed in the current source and in adversarial tests. Pair, authorship, and team checks do not self-authorize from a DOI, an arXiv id, `provenance.sourceUri`, or a missing URI. There is no process-global bibliography registry. The remaining domain, config, DBLP bound, and sample-hash checks listed by the reviewer were closed on inspection. One dataset documentation defect remains:

1. **P3 — ORCID schema notes contradict the committed sample.** Owner: `dataset-engineer`. `datasets/schemas/orcid-record.md` lines 12–13 give given-names `Charles` and family-name `Claiborne Rice`. The sample has given-names `Charles Claiborne`, family-name `Rice`, and credit-name `Claiborne Rice`. Line 16 describes employment put-code `19198978` as a ROR URL; that employment uses RINGGOLD `4365`. Lines 27–30 say education history entries are absent; the sample contains education put-codes `19198991` (University of Georgia) and `19198994` (University of Chicago), and person-level Scopus Author ID `55497628100`. The DOI index on lines 17 and 32–34 is correct. Smallest repair: correct those notes only. No sample, checksum, or core-contract change is required.

ASSUMPTIONS: JSON-as-HOCON remains the human-authorized config profile. `HEAD` is `61d1ebdf31e636d502343418ebdd6efdad95e3ed`. `.gitignore` lines 24–25 are the bytecode rules attributed to `build-engineer` in `repairs.md`; authorship was not proved from history.

RISKS: `git diff` was not run, so edits outside the reviewed trees were not enumerated. `http_get_range` caps the read but does not reject a longer body after the read the way `http_get` does; default mode does not download. Live Dagstuhl MD5, size, and DOI were not re-fetched. Sample SHA-256 values were not recomputed. License pages were not re-fetched. Syntax checks do not prove external identity.

MANUAL ACTION REQUIRED: Route the P3 schema correction to `dataset-engineer`. Do not treat this review as human acceptance, and do not commit or push from it.

BLOCKED-ON OWNER: none for this review. The open repair owner is `dataset-engineer`.

BLOCKED-ON EVIDENCE: This review did not execute `git diff`, `sbt check`, Python tests, checksum recomputation, or a bounded Dagstuhl request. Retained JUnit XML and `test-report.md` are prior artifacts, not a fresh gate.

NEXT GATE: `dataset-engineer` corrects `datasets/schemas/orcid-record.md` only, then a fresh read-only review. Human Phase 3 acceptance remains separate. No `human-gate.md` or `accepted-commit.md` is authorized by this verdict.

## Twelfth independent readiness review

STATUS: APPROVE for Phase 3 readiness. BLOCKERS: none. OWNER: `/root/phase3_acceptance_review`, fresh `code-reviewer` (`gpt-6-sol`, high reasoning effort), read-only. The coordinator appended this verdict following the user's instruction to keep minor nonblocking items as follow-ups.

The reviewer found no material regression in the current core contracts or dataset worktree. It verified explicit immutable work context and source/snapshot binding, DOI/arXiv consistency, canonical metric equations and exact zero behavior, typed graph properties/evidence, publication evidence binding, and strict IDs. ORCID notes match the current worktree sample, including the five DOI-bearing groups at indexes 0, 1, 2, 3, and 7. The sample is currently untracked; references to a committed sample in the reviewer response mean the supplied worktree file, not HEAD.

NONBLOCKING FOLLOW-UP: `dataset-engineer` may harden optional DBLP refresh at `datasets/scripts/acquire_samples.py:155-175` to require Content-Range start offset zero and compare received body length with declared span. The current hard 8 MiB read cap and HTTP 200 rejection remain enforced. This does not block Phase 3 readiness and is not expanded into a repair loop.

Read-only verification: narrow ORCID JSON parse, retained JUnit XML parse (81 core tests, zero failures), config `.conf`/`.json` byte comparison, and `git diff --check`. The reviewer relied on recorded build 2/2 and dataset gates rather than rerunning sbt or upstream network requests. Existing independent coordinator gate evidence remains in `test-report.md`; this pass changed documentation only.

NEXT GATE: Human Phase 3 acceptance; proceed past the optional follow-up. This review does not author a human decision or authorize commit/push.

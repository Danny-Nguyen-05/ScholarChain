# Phase 5C real metadata population

The final CS-focused ingestion population is `5c-2026-10-16-v3/`. It contains
**446 OpenAlex works, 10 Crossref works, 8 ORCID public records and zero newly
acquired DBLP records**. The initial 211-record attempt and unfiltered v2
population (600 OpenAlex, 10 Crossref, 15 ORCID) are complete in the verified
external archive described below. Their original `population-manifest.v1.json`
files remain here verbatim, alongside compact archive manifests. Their records
and HTTP budget are included in v3, not counted as additional observations.
Existing `datasets/samples/`, its checksums and acquisition index are unchanged.
The ingestion populations contain no human labels or model predictions. The separately retained human-reviewed, AI-assisted annotations are under
`labels/2026-10-20-danny-ai-assisted-v1/`; their provenance limitations and observed import are documented in that directory.

The offline v3 CS venue filter rejects 154 OpenAlex works outside the explicit
distributed-systems/data-engineering venue regex and 7 ORCID profiles whose IDs
are absent from retained work authors. Provider author-ID neighborhoods contained
medical records, so they were not silently included as CS data. Original v2
responses and records remain unchanged in the external archive. `selection-exclusions.json` identifies
every exclusion; the v3 manifest binds the regex and filter script hash. Known
CS source names, rather than predicted identities or labels, drive this filter.

Each final source path, SHA-256, record count, live API snapshot identity and
retrieval date is in `population-manifest.v1.json`. The manifest binds every
retained response, request ledger, normalized ingestion file, record provenance
and diagnostic. The validator verifies record membership in original responses,
not only output hashes. Ingestion is a documented subset/serialization transform;
source facts are not invented or corrected. Empty `dblp/records.xml` is a valid
empty container, not an acquired source sample.

## Selection and limitations

Crossref discovery queried `query.container-title` for each of eight venue
families (SIGMOD, VLDB/PVLDB, ICDE, SoCC, Middleware, ICDCS, OSDI and SOSP),
2018–2024 inclusive, first 30 results per venue/year. A record must have a DOI,
title, authors, matching observed year and a container title matching the
script's explicit venue regex. Up to ten unique records per stratum are selected
by ascending SHA-256 of `phase5c-v1:<lowercase DOI>`. Only the first stratum
succeeded: the second request returned HTTP 429 and disabled Crossref.

OpenAlex matching DOI requests preserve those source copies. A copy can disagree
on publication year; the original value is retained and these DOI-copy exceptions
are not falsely described as year-filtered observations. Verified venue discovery
uses public `/sources` searches, a matching source-name regex and a deterministic
source-ID tie break. Each source/year `/works` request is limited to the first
12 results, verifies returned source identity/name and year, and uses no cursor
or credentials. Some venue/year windows returned no records, recorded as zero.
Up to twenty author neighborhoods per invocation (ten works each, 2018–2024)
provide repeated-author contexts. Author selection orders observed author IDs by
frequency, then hash. OpenAlex author IDs are conservative leakage hypotheses,
not researcher identity labels. Native work IDs deduplicate ingestion. This is a
bounded convenience population; it is not an unbiased global sample.

The request ledger records precise query URLs, timestamps, allowed headers,
statuses, bytes read, response hashes and retry indices. DBLP returned HTTP 202
HTML with a bot challenge; no challenge, alternate-host, credential or bulk
fallback was attempted. Crossref returned HTTP 429. An ORCID response reached the
1 MiB per-record cap, was retained explicitly as truncated diagnostic bytes,
and disabled further ORCID requests; it was never ingested. `diagnostics.json`
records empty/limited discovery strata. `acquisition-session.v1.json` also records
two connectivity attempts outside the acquisition ledger and the active-duration
versus elapsed-time distinction in the retained v2 manifest.

The final ledger has 125 HTTP attempts and 12,732,948 bytes read. Including the
connectivity probes conservatively gives 127 attempts and 12,733,448 bytes,
within 2,400 attempts / 256 MiB / 75 minutes. One request at a time, at most one
request start per second. Per-source record/attempt limits remain 600/750 DBLP,
800/850 OpenAlex, 600/650 Crossref and 60/100 ORCID. No access tokens, keys,
account creation, paid API, corpus download, cloud operation or live LLM occurred.

Real eligible candidate counts, difficult-negative composition and independent
leakage-group sufficiency require the actual Hadoop preparation and ER queue.
A source count never establishes 300 reviewable pairs or 40+200 completed reviews.
Any queue shortfall must be reported rather than filled with synthetic labels,
reverse pairs, repeated snapshots or copies of one publication.

## Replay and integrity

Verify without network:

```bash
python3 datasets/scripts/validate_resolution_population.py datasets/entity-resolution/5c-2026-10-16-v3
python3 -m unittest discover -s datasets/scripts -p 'test_*.py' -v
```

The two historical directories in this repository now contain **only** their
original population manifest and `archive-manifest.v1.json`. They are archive
pointers, not complete locally valid populations: do not pass these manifest-only
directories to the population validator. All 179 archived files were SHA-256 and
byte verified before the 177 inactive payload files were removed (31,229,073 bytes).
No v3 or prepared input file was removed. The current runtime, dataset tests,
Scala fixtures, evaluator and human handoff use v3/prepared/current repaired queue;
historical diff reconstruction explicitly resolves archived original bytes.

The durable archive is outside this repository and outside `target/`:
`/Users/danny/Documents/ScholarChain-archive/phase5c/dataset-history-20261017T005030Z`.
Its `archive-proof.v1.json` SHA-256 is
`4cac1c976ff45babcf76bcb4f1bdd6b2ae5b3848b457672d891f6cf1c967a488`.
Each compact in-repository archive manifest lists every original relative path,
byte count, hash and absolute archive location. Verify complete archived file
sets with existing checksum tooling:

```bash
cd /Users/danny/Documents/ScholarChain-archive/phase5c/dataset-history-20261017T005030Z
shasum -a 256 -c 5c-2026-10-16.SHA256SUMS
shasum -a 256 -c 5c-2026-10-16-v2.SHA256SUMS
```

The complete archive copies can also be validated with the unchanged population
validator from the repository root:

```bash
python3 datasets/scripts/validate_resolution_population.py /Users/danny/Documents/ScholarChain-archive/phase5c/dataset-history-20261017T005030Z/5c-2026-10-16
python3 datasets/scripts/validate_resolution_population.py /Users/danny/Documents/ScholarChain-archive/phase5c/dataset-history-20261017T005030Z/5c-2026-10-16-v2
```

These absolute archive paths are local historical provenance, not portable runtime
requirements. If history is needed on another machine, transfer the complete
verified archive and validate it; the repository alone intentionally retains only
its manifests. For optional future reproduction, `--base` accepts the complete
archived population path directly; restoring inactive payload into the repository
is unnecessary. No new acquisition is authorized by this packaging change.

Hadoop inputs are `dblp/records.xml`, `openalex/works.jsonl`,
`crossref/works.jsonl`, and `orcid/records.jsonl` under the final directory.
Set each `--<source>-snapshot` to `<source>-er5c-live-api-2026-10-16` and
`--<source>-retrieval` to `2026-10-16`; use a separately generated configuration
with `maxLocalSampleRecords >= 464` (the agreed overall cap is 2,060). Normal
parser/block/team rejects remain evidence; no source normalization repair is
claimed. The exact executed preparation command is in coordinator phase evidence.

Acquisition is opt-in and never overwrites an output:

```bash
python3 datasets/scripts/acquire_resolution_population.py --acquire --output <new-directory>
python3 datasets/scripts/acquire_resolution_population.py --acquire --base <immutable-completed-population> --output <new-extension-directory>
```

An extension carries the original counters, byte allowance and disabled sources;
it cannot reset a rate/auth refusal or silently increase a bound. A new acquisition
requires an authorized work order. API responses may change; deterministic local
verification of the frozen files, rather than identical future live responses,
is the reproducibility claim.

## Source rights and access evidence

Checked 2026-10-16 using the official documentation:

- DBLP metadata: [CC0 metadata license](https://dblp.org/faq/Under+what+license+is+the+data+from+dblp+released.html).
- OpenAlex: [open data overview](https://openalex.org/),
  [authentication and keyless basic-query limits](https://help.openalex.org/api/authentication/).
  Data are CC0; no claim is made to publisher full text. The legacy documentation
  URI in the frozen manifest was inaccessible during documentation verification;
  these current official links clarify it without rewriting the frozen record.
- Crossref: [metadata access and licensing](https://www.crossref.org/documentation/retrieve-metadata/).
  Bibliographic metadata are reusable facts; abstracts may retain publisher or
  author copyright. `select` excludes abstracts, references and full text.
- ORCID: [Public APIs terms](https://info.orcid.org/public-client-terms-of-service/)
  grant limited noncommercial public-data use, applicable to this academic project.
  [Public Data File policy](https://info.orcid.org/public-data-file-use-policy/)
  concerns the annual CC0 file; it is not a blanket public API license or license
  for linked materials. We acquired public API records, not that annual file.

Raw responses are provenance, including blocked HTML and a capped ORCID response;
only successfully parsed, validated records enter ingestion. No linked articles,
PDFs, private ORCID sections or external resources were fetched.

## Frozen queue preparation input retention (5C B2 repair)

The exact completed input used by the frozen real queue is now retained under
[`prepared/`](prepared/README.md), outside ignored `target/`. Its sibling hash
manifest covers 68 original files / 49,547,452 bytes, preserving all run IDs and
source bytes. Use the retained completed directory directly for future queue-bound
prediction replay; rerunning Hadoop creates a different identity binding. The
prepared-input guide covers clean-checkout verification and preservation of future
human checkpoints. This is dataset-owned evaluation-input retention; the later
human-approved lean packaging archives only the inactive v1/v2 raw payloads and
leaves this exact prepared input and final v3 population complete.

## 2026-10-20 bounded demo follow-up

The separately approved follow-up search is retained in `5d-demo-2026-10-20-screened/`. Canonical screening first found no safe missing-ORCID affiliated author seed in either the previous supplement or frozen development components. The coordinator therefore used the explicitly recorded fixed topic-discovery strategy: `state machine replication` and `distributed stream processing`, five works each, with no pagination or refill. Only actually returned, affiliated authors lacking observed ORCID could seed at most four five-work neighbor queries. All newly returned components would still need canonical held-out exclusion before any scoring; no label or score drove this search.

The actual run made **two HTTP 200 requests**, read **43,664 response bytes** and took **1.3677 seconds**. It returned **ten distinct new works**, all excluded by the unchanged CS venue filter; their year and record-byte checks passed. No author was selected, no neighbor request occurred and no new record entered ingestion. The existing context remains fourteen Crossref and twelve OpenAlex records. Stage limits were thirty returned works including exclusions, twenty HTTP attempts including retries, eight MiB and five minutes. Across the previous and follow-up acquisition stages, the retained ledger reports thirty distinct returned works, nine attempts, 215,344 bytes and 7.9818 seconds; those are cumulative counters, not a reset of the earlier approval.

The executed script copy, two original response bodies, exact fixed plan, failed existing-seed screening receipt, approval receipt, selection trace, exclusions and prior context are hash-bound by the new population manifest. Its dataset-level canonical-admission status remains pending; it does not claim an eligible pair. Because ingestion records are unchanged, the coordinator can prove semantic equivalence to the existing completed demo input rather than retaining another duplicate Hadoop run. This search produced no model calls, no spend, no new human labels and no 5E result. The live-provider prerequisite remains unresolved; no further search or policy relaxation is implied.

Validate offline:

```sh
python3 datasets/scripts/acquire_screened_demo.py validate \
  --population datasets/entity-resolution/5d-demo-2026-10-20-screened
```

### B2 discovery-order root cause and correction

The original topic search combined text search with `sort=publication_date:asc`. That explicit sort overrode OpenAlex's search-relevance ordering and took the earliest five matching works for each topic. The ten excluded records therefore characterize that narrow date-ordered request only; they do not show that relevant CS works or eligible demo pairs do not exist. The old responses, ledgers, manifests and executed script remain immutable historical evidence.

The repaired discovery request explicitly uses `sort=relevance_score:desc`, retaining the same two topics, 2018–2024 dates, five-result limit, field allowlist and numerical stage caps. OpenAlex's official [search documentation](https://help.openalex.org/api/searching/) specifies descending relevance as the search default; its [sorting documentation](https://help.openalex.org/api/sorting/) supports explicit descending `relevance_score` when search is present. These documentation checks are not acquisition or a claim that the repaired search finds an eligible pair.

New acquisitions record `queryPlanVersion: scholarchain.topic-discovery-order.v2` and `discoveryOrdering: relevance_score:desc`. The validator still recognizes the old date-ordered acquisition only through its exact retained executed-script SHA-256, and reports its legacy ordering explicitly; unknown ordering/version combinations are refused. A separately approved rerun supplies `--previous-stage` so the old ten excluded observations, two attempts and their bytes/time remain in cumulative history rather than being discarded or double-counted through repeated context copies. Any new real result still requires canonical whole-component held-out exclusion before scoring. No label or model-policy change is part of this ordering repair.

### Observed separately approved relevance-ordered rerun

The corrected execution is retained separately in `5d-demo-2026-10-20-relevance-v2/`. It made three HTTP 200 requests, read 75,738 bytes and took 2.2322 seconds. Fourteen distinct works were returned, including exclusions; five new works passed the unchanged ingestion filters. The fixed two topic requests selected one actually observed missing-ORCID affiliated author, leading to one neighbor request. There was no pagination, refill, policy tuning or numerical-cap expansion. The combined demo ingestion now contains seventeen OpenAlex and fourteen Crossref records.

The prior failed date-ordered stage is retained byte-for-byte under the new stage's `previous-stage/`, alongside the exact original ingestion context. Distinct manifest-bound history preserves cumulative totals of forty-four distinct returned works, twelve HTTP attempts, 291,082 response bytes and 10.214 seconds. The new manifest explicitly records relevance ordering and query-plan v2; it does not relabel the earlier request or discard excluded observations.

The coordinator ran unchanged Hadoop preparation for these new records. Its exact completed output is durably retained as `prepared/f22f1a12-c7be-43af-b470-d4f4e244ca9d/` with explicit `development-demo` purpose. Dataset retention and acquisition validation do not establish canonical held-out admission, model eligibility or a real-provider response. The coordinator must perform canonical whole-component exclusion before scoring. No human labels, attribution records or frozen review inputs were modified by this rerun or retention.

```sh
python3 datasets/scripts/acquire_screened_demo.py validate \
  --population datasets/entity-resolution/5d-demo-2026-10-20-relevance-v2
python3 datasets/scripts/retain_prepared_population.py validate \
  --population datasets/entity-resolution/prepared/f22f1a12-c7be-43af-b470-d4f4e244ca9d
```

## Separately approved author-focused 5D demonstration search

The later focused search is retained in `5d-demo-2026-10-20-benedikt/`. Its explicit approval caps **all returned metadata rows**, including author profiles, work duplicates and excluded records, at thirty; the other caps remain twenty HTTP attempts, eight MiB and five minutes. One fixed relevance-ordered `Michael Benedikt` author lookup returned five provisional profiles. Their actual returned IDs, sorted deterministically, supplied five bounded 2018–2024 work queries. These profiles are discovery hypotheses, not verified identity assertions or ingested author facts. No labels, scores, credentials, pagination, refill or fallback were used.

The actual search made six HTTP 200 requests, read 218,664 response bytes and took 5.3543 seconds. It returned 26 metadata rows: five author profiles and 21 works. Cumulative acquisition history records eighteen attempts, 509,746 bytes, 15.5683 seconds, 65 distinct work IDs, seventy returned work rows and five author-profile rows. Distinct work IDs are not the thirty-row stage cap: that cap includes profiles and duplicate/excluded rows. The exact approved existing Crossref seed `10.1145/3299887.3299889` is reused without changing its original source line, snapshot or retrieval date.

The initial venue-name filter admitted seven OpenAlex records, but five were particle-physics publications in the source named `Institutional Repositories DataBase (IRDB)`. Its `type: repository` and the substring `database` do not establish a CS publication venue. The coordinator detected this before any entity-resolution scoring. The entire raw acquisition remains immutable; its seven-record preparation run under `target/` was not used for ER or durably retained.

A separate **offline** derived population, `5d-demo-2026-10-20-benedikt-cs/`, excludes those five records before ER. The versioned slice requires an observed `conference` or `journal` source type before applying the existing CS venue/year/record bounds; unknown types fail closed. It keeps the exact original lines for two actual PODS works (`W2659288104` and `W2803866544`) and the one Crossref seed, preserving every observed identifier. It binds its parent manifest and carries the parent's acquisition counters as references, not new requests or reset allowances. No additional HTTP request occurred.

Only this derived two-OpenAlex/one-Crossref input was prepared for ER. Its exact completed output is retained under `prepared/88e3a197-6155-4936-8cf5-e0357cd73208/`, explicitly `development-demo`. Whole-component canonical held-out exclusion must precede scoring; the dataset validators do not establish admission, model eligibility, model execution or identity accuracy. Reviews, attribution records, matching policy and the frozen evaluation population remain unchanged.

The coordinator's canonical target-input check observed six candidates, all six admitted after held-out exclusion, zero excluded and zero model-eligible. Three Work pairs have hard DOI conflicts; one Researcher pair is accepted by exact identifier; two Researcher pairs remain unresolved with insufficient groups (name-only scores 0.9 and 1.0, with no supporting coauthor or affiliation feature). No model or credential lookup occurred. This is a result for the bounded CS slice only, not evidence that eligible public CS pairs do not exist. Durable replay is a separate coordinator verification gate.

```sh
python3 datasets/scripts/acquire_author_focused_demo.py validate \
  --population datasets/entity-resolution/5d-demo-2026-10-20-benedikt
python3 datasets/scripts/derive_focused_cs_population.py validate \
  --parent datasets/entity-resolution/5d-demo-2026-10-20-benedikt \
  --population datasets/entity-resolution/5d-demo-2026-10-20-benedikt-cs
python3 datasets/scripts/retain_prepared_population.py validate \
  --population datasets/entity-resolution/prepared/88e3a197-6155-4936-8cf5-e0357cd73208
```

## Final bounded Rice-team development/demo attempt

The final separately approved acquisition is retained in `5d-demo-2026-10-20-rice-final/`. It issued exactly two fixed author-filter queries, for actually observed OpenAlex IDs `A5085731856` (Luis Leopoldo Perez) and `A5109437922` (Christopher Jermaine), with 2018–2024 dates, `cited_by_count:desc` and at most fifteen works per query. There was no author lookup, text discovery, pagination, refill or fallback. These IDs are provider hypotheses used for discovery, not verified researcher identities. The unchanged matching policy and human labels played no part in selection.

The two HTTP 200 responses returned **fifteen work rows**, including three duplicate appearances across the requests, representing **twelve distinct work IDs**. The client read **112,270 response bytes** in **1.4782 seconds**. Eight distinct IDs had not appeared in prior stages. Three records passed the explicit conference/journal CS venue, year, record-byte and maximum sixteen-author-team bounds; excluded records remain in the responses and exclusion ledger. Whole records are excluded rather than truncating author lists or masking identifiers. The approved thirty-row, twenty-attempt, eight-MiB, five-minute limits count all returned duplicates and exclusions.

Only records from these fresh responses enter ingestion. The three selected works are `W2799457717`, `W2889897289` and `W2895331519`; each receives the new stage-specific source snapshot and its actual UTC retrieval date, 2026-10-21. The two older seed lines are retained separately as **selection proof only**, with original source snapshot `openalex-5d-demo-2026-10-17`, retrieval date 2026-10-17, line numbers and exact byte hashes. Their presence in fresh responses is a new observed retrieval, not relabelling of copied old observations. The directory's 2026-10-20 date follows the local work-order date.

Prior history remains in its existing retained stage, bound by an exact manifest copy and hash-verified reference rather than another recursive copy. Cumulative totals are **twenty HTTP attempts**, **622,016 response bytes**, **17.0465 seconds**, **73 distinct work IDs**, **85 returned work rows** and **five previously returned author-profile rows**. The ninety cumulative metadata rows are not the new stage's fifteen-row count or a reset of any approval.

The exact executed acquisition script and helper dependency, fixed plan, approval receipt, original response bodies, selection proofs and exclusions are hash-bound by the new manifest. Dataset validation does not establish model eligibility. Canonical whole-component held-out exclusion must precede any scoring; no eligible pair or provider result is claimed here. This final attempt authorizes no further acquisition or policy change, and does not alter the frozen queue, labels or approved limited 5E evaluation.

```sh
python3 datasets/scripts/acquire_rice_team_demo.py validate \
  --population datasets/entity-resolution/5d-demo-2026-10-20-rice-final
```

The fixed venue-name catalog has a measured domain-coverage limitation: both responses also contain the legitimate CS journal record `W3044177535`, “Scalable linear algebra on a relational database system” (2020, DOI `10.1145/3405470`), whose observed source is `Communications of the ACM` (`S103482838`, `type: journal`). That name does not match the acquisition script's fixed venue substrings, so the record remains excluded. No post-response allowlist expansion or replacement population was performed in this final attempt. This metadata-only observation establishes a catalog omission, not an identity label or model-eligibility result; eligibility for excluded records was not tested. Any zero-eligible result for the three admitted ingestion records therefore cannot establish absence of eligible public CS evidence.

The final attempt's exact three-record completed preparation is retained as `prepared/8d30085c-cb67-4d25-909f-5f2603ad4511/`, with explicit `development-demo` purpose. The retainer verified 38 files / 204,212 bytes without changing any source observation or run identity. The coordinator's target-input canonical check found eleven candidates, all eleven admitted after held-out exclusion, zero excluded and zero model-eligible. This is a result for the fixed selected population, with the venue-catalog omission above still disclosed. The final attempt produced no qualifying live-model demonstration; no further search or policy adjustment follows from this result.

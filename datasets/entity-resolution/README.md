# Phase 5C real metadata population

The final CS-focused ingestion population is `5c-2026-10-16-v3/`. It contains
**446 OpenAlex works, 10 Crossref works, 8 ORCID public records and zero newly
acquired DBLP records**. The initial 211-record attempt and unfiltered v2
population (600 OpenAlex, 10 Crossref, 15 ORCID) are complete in the verified
external archive described below. Their original `population-manifest.v1.json`
files remain here verbatim, alongside compact archive manifests. Their records
and HTTP budget are included in v3, not counted as additional observations.
Existing `datasets/samples/`, its checksums and acquisition index are unchanged.
No human labels or model predictions are contained here.

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

# Authorized Phase 5D development/demo supplement

The user approved the bounded supplement recorded in
`docs/agent-runs/phase-05/evidence/5d/user-supplement-approval.json`.
These are separate development/demo observations, not additions to the frozen
240-review queue or its held-out population. No labels, scores or model calls
are created by acquisition.

`5d-demo-2026-10-17-seeds/` contains fourteen previously downloaded Crossref
observations, extracted without altering their metadata from the verified
`5c-2026-10-16-v3/responses/0002-crossref.body`. The source response SHA-256 is
`73a27212459508e6c41df659c391603682e4a9e0afc0da21f4b5a01701263e4f`.
The full original response, per-record provenance and the exact executed script
bytes are retained in the supplement. Only the fourteen explicitly listed records
are ingestion inputs. Earlier provisional screening did not establish canonical
held-out clearance or naturally eligible cases.

The manifest lists all four explicit Hadoop input paths, record counts, snapshot
IDs, retrieval dates, executed-script hash, and every file's SHA-256/bytes.
DBLP XML is an empty valid document; ORCID JSONL is empty. Explicitly supply
all four paths and snapshot/retrieval overrides to avoid loading unrelated default
samples. Crossref retrieval remains the original 2026-10-16 date. Empty source
placeholders use the manifest's declared demo snapshot/date; they do not claim
acquired observations.

Verify with no network:

```bash
python3 datasets/scripts/acquire_demo_supplement.py validate --population datasets/entity-resolution/5d-demo-2026-10-17-seeds
python3 -m unittest discover -s datasets/scripts -p 'test_demo_supplement.py' -v
```

The existing evidence is normalized first through the unchanged Hadoop pipeline.
If insufficient, the authorized optional OpenAlex stage uses a separate new output
directory and preserves the seed-only input. Every executed acquisition script
version is copied verbatim and hashed **before its first HTTP request**.

Optional acquisition bounds are thirty observed new OpenAlex works including
subsequently excluded works: at most six DOI seed matches and twenty-four
neighbor works. Fixed hash selects six of the fourteen observed seed DOIs.
An observed author without an ORCID is preferred per seed as a declared missing-ID
stratum, then hash breaks ties; no score or label selects records. Each author
query requests the first four 2018–2024 works. Source facts and IDs are never
removed to make a pair eligible. Neighbors outside declared CS venue criteria
remain response evidence/exclusions and do not enter ingestion.

Hard limits: twenty total HTTP attempts including retries, sixteen MiB total
response bytes, two MiB per response, one MiB per ingestion record, ten minutes,
twenty-second request timeout bounded by remaining time, one concurrent request,
at most one request start per second, and one transient retry. Access/quota
refusals stop the client. No redirect or challenge bypass, keys, account creation,
paid data service, full corpus, abstracts or full text are used.

The standalone command is explicit opt-in, requires the prior seed population,
and refuses an existing output. Its actual invocation, output location and result
belong in coordinator evidence; merely documenting the command does not claim an
acquisition occurred:

```text
python3 datasets/scripts/acquire_demo_supplement.py create --original-crossref-response datasets/entity-resolution/5c-2026-10-16-v3/responses/0002-crossref.body --base datasets/entity-resolution/5d-demo-2026-10-17-seeds --acquire-openalex --output NEW_DEMO_POPULATION
```

The dataset validator checks complete inventory, script hash, request/byte ledger,
source counts and record membership in successful original responses. Its
admission status intentionally remains pending: only the ER owner's exact
canonical endpoint/anchor and transitive-component check can admit records.
Normalize at most forty-four records into a new demo-only Hadoop run. **Before
scoring**, reject each entire supplement component connected to locked held-out
anchors/endpoints, including connections through another new record. Never move
held-out groups, rewrite the original queue/split, or score held-out pairs to
obtain a live example. Coordinator/ER evidence records actual admitted pairs.

Original v3, prepared input, queue, split and human labels remain unchanged.
Eligibility must arise under the frozen policy without threshold, feature,
identifier or evidence manipulation. Zero naturally eligible cases means zero
live adjudication calls; this supplement offers no guaranteed eligible case or
held-out accuracy claim.

Rights follow the existing public Crossref bibliographic metadata and OpenAlex
portfolio terms documented in `README.md`; publisher abstracts/full text were
not requested. ORCID profile acquisition is outside this supplement.

The seed-only completed preparation input is durably retained at
`prepared/3bfbd651-5982-4f3d-b29b-246fb88d07a1/`, with its sibling retention
manifest: 36 files / 524,961 bytes. The completion SHA-256 is
`037ab3766408f3cb6dae85636b4b3c4cb0bd73c29251f21578bdbc828e58c65c`.
Use the existing retention validator to verify it. This preserves actual normalized
seed evidence and processing UUID; retention itself does not prove ER admission
or natural eligibility.

## Executed optional acquisition

After the coordinator's exact seed-only admission check found 79 admitted
candidate pairs and zero naturally eligible cases, the optional authorized
OpenAlex stage completed in `5d-demo-2026-10-17-openalex/`:

- **7 HTTP attempts, 171,680 response bytes, 6.6141 seconds**, no retries.
- **20 distinct newly observed OpenAlex works**, including all exclusions.
- **12 OpenAlex ingestion records + the same 14 original Crossref seeds**;
  eight newly observed works excluded by the declared year/domain/record filter.
- Zero DBLP/ORCID observations. Explicit empty inputs remain present.
- Population manifest SHA-256:
  `ff4154deda081832db8f0ca85bce33a96075d0c722b41bfcc4996ee056f4ea41`.
- Executed acquisition script SHA-256:
  `28b566359007f532f9f640b198d56a4eeba0fd7469ddf011a90c8651615cd9b4`;
  exact bytes retained at `scripts/acquire_demo_supplement.py` within this input.

An earlier worker native approval request was interrupted before an execution
receipt was returned. Read-only inspection found no staging/output directory and
no HTTP ledger; it is not counted as a completed HTTP attempt. The coordinator
then executed the single actual acquisition after native approval. Its seven
requests, statuses, response bodies/hashes and timestamps are retained in the
population ledger and coordinator command evidence. No acquisition was rerun to
increase eligibility or spend unused limits.

The unchanged dataset validator passed all sixteen retained-file hashes,
per-record original-response membership, script hash, record caps and request/byte
ledger consistency. All 33 dataset Python tests passed afterward. These are
integrity/bounds observations, not a claim of canonical held-out admission,
eligible pairs, human review or live-model success. ER admission must still occur
before scoring this new normalized input. Original frozen 5C inputs remain unchanged.

The actual optional-supplement completed preparation input is retained at
`prepared/68c2b012-6d04-4eef-a7bf-5ca31706d895/`, with its sibling retention
manifest: **60 files / 1,271,664 bytes**, verified against the original completed
run without rewriting any bytes or processing UUID. Retention-manifest SHA-256:
`d9eec30ba05026f1cd8078745a6b8646d40826551b473a9b7eae64044fd64685`.
Completion SHA-256:
`4113b3f1a8a8c6e8a60d5fd759520ef53d3905d4d3e8ce4bed006fc8840a6c8b`.
The coordinator/ER admission report, rather than data retention, determines whether
its components are clear of locked held-out evidence and naturally eligible.


The external 5D blocker B2 correction makes both sibling retention manifests
explicitly `development-demo` purpose. Their prior automatic frozen-5C wording
was incorrect. This correction does not turn these inputs into gold labels or
held-out evaluation material. All retained bytes, completion/run manifests and
source ingestion populations remain unchanged. The prepared-input guide lists
both current metadata manifest hashes and the distinct unchanged frozen 5C input.

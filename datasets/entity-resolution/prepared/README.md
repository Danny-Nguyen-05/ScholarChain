# Prepared inputs: frozen review and separate development/demo evidence

This directory contains two distinct purposes. Purpose describes retained input
provenance, not identity accuracy, human review or permission to evaluate.

| Completed run | Purpose | Retained files / bytes |
| --- | --- | --- |
| `bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3` | Frozen Phase 5C review population and future queue-bound human-label evaluation replay | 68 / 49,547,452 |
| `3bfbd651-5982-4f3d-b29b-246fb88d07a1` | Phase 5D development/demo only: reused Crossref seed preparation | 36 / 524,961 |
| `68c2b012-6d04-4eef-a7bf-5ca31706d895` | Phase 5D development/demo only: bounded OpenAlex supplement preparation | 60 / 1,271,664 |

The two 5D runs are **not** the frozen 5C review population, human gold labels or
held-out evaluation input. Their sibling retention manifests now explicitly use
`purposeKind: development-demo`. This corrects only retention purpose/ownership
metadata; every retained payload, completion and Hadoop run-manifest byte remains
unchanged. The accepted 5C retention manifest remains byte-identical and valid.
The frozen-review replay instructions below apply only to its named 5C run.

## Frozen Phase 5C input

`bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/` is the durable, byte-exact completed
preparation input consumed by the original real 300-pair review queue. Its
sibling `bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3.retention-manifest.v1.json`
binds all **68 files / 49,547,452 bytes** by relative path, byte length and SHA-256.
This material lives outside ignored `target/` and must be included in the change.
No additional acquisition or human labels are contained here.

Ownership follows the existing dataset-engineer ownership of `datasets/**`:
these are retained evaluation-population inputs, not a change to Hadoop logic,
ER contracts or the constitutional ownership map. The retention manifest records
this decision and the exact retained scope. Earlier raw population/history
artifacts were unchanged by the B2 repair. The later human-approved lean packaging
archives inactive v1/v2 raw payloads externally while keeping their original
manifest files; this prepared input and the complete v3 population remain unchanged.

The retained scope is:

- Entire original `export/**`, including hidden Hadoop checksum metadata.
- Original `_SCHOLARCHAIN_COMPLETE` and `run-manifest.json`, unchanged.
- Eight `intermediate/j01/_SUCCESS` through `intermediate/j08/_SUCCESS` files.
  The ninth required job-success marker is `export/_SUCCESS`.

The ER input loader reads these files and validates its export inventory. It does
not read the omitted intermediate data, stats or counter summary. These omitted
files are not claimed retained. Original run IDs, record provenance, locators,
paths written inside records/manifests and JSON whitespace are preserved exactly;
relocating the directory does not rewrite them. Source-input checksum claims in
the original completion marker still refer to the separately retained v3 raw
population. The original ignored preparation run remains untouched.

## Verify after a clean checkout

From the repository root:

```bash
python3 datasets/scripts/retain_prepared_population.py validate --population datasets/entity-resolution/prepared/bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3
python3 -m unittest discover -s datasets/scripts -p 'test_prepared_retention.py' -v
```

The validator requires the sibling retention manifest, all nine success markers,
matching completion/run identities, the exact export-part inventory and hashes,
and the complete retained file inventory. Missing, altered or extra files fail
closed. The bounded tests use small synthetic framing fixtures; their records
are not real evaluation data. A real-copy integrity test remains runnable even
when `target/` is absent.

**Do not regenerate Hadoop output to recover this queue.** A fresh Hadoop run
assigns a different processing UUID, which changes the frozen source/evidence
binding. Use this retained directory directly as `--input` in the ER CLI.
A deleted local working copy can be restored from the committed tree using
ordinary checkout; there is no need to recreate the ignored original run or
rename a new run to the old UUID. Copying the retained tree to another local
working directory is also valid when every byte and relative path is preserved;
copy its sibling retention manifest alongside it and validate the copy first.

The current repaired frozen queue is
`docs/agent-runs/phase-05/evidence/5c-repair/review-artifacts/queue.json`, with its
`split.json` sibling. The older `evidence/5c/review-artifacts/` queue is historical
and has been moved to the coordinator's verified external archive; its compact
archive manifest remains in phase evidence. Use the current repaired queue for
human checkpoints and evaluation. The source population bindings are unchanged:

- Input evidence hash: `57efd81957e5eec9194d4b5c42f6ef170213640f148b56bf8b99a51d1d09d1fe`
- Candidate population hash: `9381588e35a418a84a22e9a680db4ab7886a8d33cf9463166edc1222cd8a5581`
- Completion-file SHA-256: `ecb1744d591092f66fa57c87108497caf80349d183b79816f7607dcc7b21f399`
- Run-manifest SHA-256: `9d70503b9b3496eb2c39e2f61009a1614db755b783668fd452fb3777a0d48552`

The first two values are the pre-repair real-queue bindings, not values computed
by this Python retainer. The coordinator's repair evidence records actual Scala
input-loader/candidate replay checks from the durable directory. Python integrity
checks do not establish that semantic replay or human review happened.

## Preserve future human work

Human checkpoints must keep the original frozen queue and evidence hashes.
Import them through `import-labels --queue <frozen queue> --labels <original human
checkpoint> --output <new durable validated file>`; never rewrite the original
annotation to fit a regenerated queue. Save original human files durably and
separately from synthetic browser/evaluator test artifacts.

When the appropriate later subphase is authorized, resolution and
`prepare-evaluation-predictions` must use this durable completed input with the
frozen queue/config. Code/source/policy provenance must describe the actual
executed version; do not supply an old code hash to disguise new code. The ER
owner's CLI contract documents prediction binding, label import and evaluation.
No real labeling, held-out evaluation, provider call or later-subphase acceptance
is claimed by retaining these inputs.

## Retain another explicitly authorized completed population

The retention script never overwrites an existing population or sibling manifest:

```text
python3 datasets/scripts/retain_prepared_population.py retain --source COMPLETED_RUN --destination NEW_DURABLE_RUN_DIRECTORY --purpose frozen-5c-review|development-demo
```

It validates the original framing and part hashes before copying, copies into a
new sibling staging directory, verifies copied bytes and publishes the completed
run directory followed by the sibling manifest. Validation refuses a directory
whose sibling manifest is absent, including an interrupted publication. The
hard bound is 1,000 files / 96 MiB. This command performs no network calls,
Hadoop execution, identity decisions, metadata normalization or run-ID changes.


Choose `--purpose frozen-5c-review` only for an authorized frozen review population;
choose `--purpose development-demo` for separate demo/development evidence. The CLI
and Python API require the choice and do not silently default to review/evaluation.
Validation checks that the closed purpose kind, descriptive purpose and ownership
text agree. Known retained 5D run IDs cannot claim the frozen-review purpose;
the named 5C run cannot claim demo purpose. The accepted original 5C manifest is
supported without rewriting it; other new manifests require explicit purpose.

Validate the separate 5D inputs without acquiring or scoring anything:

```bash
python3 datasets/scripts/retain_prepared_population.py validate --population datasets/entity-resolution/prepared/3bfbd651-5982-4f3d-b29b-246fb88d07a1
python3 datasets/scripts/retain_prepared_population.py validate --population datasets/entity-resolution/prepared/68c2b012-6d04-4eef-a7bf-5ca31706d895
```

The corrected 5D retention-manifest SHA-256 values are:

- Seeds: `b413bc380845719b88f655ec5200ea1f6eb6bd4ae4744ec1b4fa1609031547b1`
- OpenAlex demo: `d9eec30ba05026f1cd8078745a6b8646d40826551b473a9b7eae64044fd64685`

## Separately retained relevance-ordered 5D demo input

`f22f1a12-c7be-43af-b470-d4f4e244ca9d/` retains the exact completed preparation from the separately approved corrected relevance-ordered search in `../5d-demo-2026-10-20-relevance-v2/`. It is **development/demo evidence only**, not a frozen review population, gold-label input or held-out evaluation population. The raw ingestion comprises seventeen OpenAlex and fourteen Crossref records; whole-component held-out exclusion still precedes all scoring.

The retainer copied and independently verified 60 files totaling 1,444,292 bytes, without rewriting run IDs, records, completion files or export paths. Retention includes the entire export, original completion and run manifests, and required intermediate success markers; it does not claim to retain unrelated Hadoop intermediate parts.

- Run ID: `run:f22f1a12-c7be-43af-b470-d4f4e244ca9d`
- Explicit purpose: `development-demo`
- Sibling retention-manifest SHA-256: `54e06ea923025fe67997ec0a89e248c57cd991e3bca8eb907912d72263037ec9`
- Completion SHA-256: `421f1ba83af4eacdb49aced4be54377b4d0d9ea2ff85f900f2586ed915a81d42`
- Run-manifest SHA-256: `2888834b20b6b2087a5ab2c24823c61efc2ee33dc12dda15263e3a49b3ac2360`

```sh
python3 datasets/scripts/retain_prepared_population.py validate \
  --population datasets/entity-resolution/prepared/f22f1a12-c7be-43af-b470-d4f4e244ca9d
```

These are integrity/provenance facts only. They establish neither identity accuracy, live-provider execution, calibration nor Phase 5 acceptance. The original 5C and prior 5D inputs remain unchanged.

## Focused 5D CS-only demo input

`88e3a197-6155-4936-8cf5-e0357cd73208/` retains the exact completed preparation of `../5d-demo-2026-10-20-benedikt-cs/`: two actual PODS works and the exact original Crossref seed. It is **development/demo evidence only**, not frozen review, gold labels or held-out evaluation input. Its parent focused acquisition remains immutable; an offline source-type filter excluded five particle-physics repository records before any ER scoring. The initial seven-OpenAlex raw preparation was not used by ER and is not retained here.

Retention copied and verified 56 files / 82,072 bytes. Original completion files, run IDs, export bytes and source observations were not rewritten. Canonical whole-component held-out exclusion remains required before scoring; retention itself claims no identity decisions, model eligibility or provider evidence.

- Run ID: `run:88e3a197-6155-4936-8cf5-e0357cd73208`
- Explicit purpose: `development-demo`
- Sibling retention-manifest SHA-256: `74a037bbcb06e5fa6e925949570fc29a69a7705469902159b0a62b52659167f2`
- Completion SHA-256: `d59dfe49e3c38c44014774733029c6c21d083871904255ba9a5fff987422e5ef`
- Run-manifest SHA-256: `82d1008a627de5601a598582b7a8d9d16d22b86cd367113775e3048a36b9898a`

```sh
python3 datasets/scripts/retain_prepared_population.py validate \
  --population datasets/entity-resolution/prepared/88e3a197-6155-4936-8cf5-e0357cd73208
```

Earlier retained populations and all human-review artifacts remain unchanged. This retention is not overall 5D or Phase 5 acceptance and does not authorize 5E.

The coordinator's canonical check of the matching completed target input found six candidates, six admitted, zero held-out exclusions and zero eligible pairs. The six decisions are three Work hard conflicts, one exact-ID Researcher acceptance and two insufficient-evidence Researcher unresolved outcomes. The latter lack coauthor and affiliation support despite name similarity. These observed results do not establish absence of eligible evidence beyond this bounded population. Byte-identical durable replay is checked separately by the coordinator; no model calls or credentials were used for the target check.

## Final bounded Rice-team demo input

`8d30085c-cb67-4d25-909f-5f2603ad4511/` retains the exact completed preparation of `../5d-demo-2026-10-20-rice-final/`: three fresh-response OpenAlex records. It is explicitly **development/demo evidence only**, not a frozen review population, gold-label input or held-out evaluation population. Older seed rows are separate selection proof and were not copied into preparation as newly retrieved observations. All original identifiers, source values and full author lists are preserved.

The existing retainer copied and verified **38 files / 204,212 bytes**, preserving the original completion file, run manifest, export bytes and run identity. No new Hadoop execution, acquisition or source transformation was performed by retention.

- Run ID: `run:8d30085c-cb67-4d25-909f-5f2603ad4511`
- Explicit purpose: `development-demo`
- Sibling retention-manifest SHA-256: `88bf307b498efae7660ef24a6ab384b69cab5bdcc522f670ad8572035b140c7c`
- Completion SHA-256: `82e3ea89777fa5309f636d8b829ef934094b4eef78f6f5bd612aed81250fe261`
- Run-manifest SHA-256: `664e4e602e220246343b10d25ef438ca05ead688ccb8c9ee1b6efdbac653691d`

```sh
python3 datasets/scripts/retain_prepared_population.py validate \
  --population datasets/entity-resolution/prepared/8d30085c-cb67-4d25-909f-5f2603ad4511
```

The coordinator's canonical check of the target input observed eleven candidate pairs, eleven admitted after whole-component held-out exclusion, zero excluded and zero model-eligible. Its classifications comprise two Work hard conflicts; five exact-ID Researcher acceptances; two scored Researcher acceptances; and two unresolved Researcher pairs. These results apply only to the fixed three-record ingestion population. The acquisition's documented CACM venue-catalog omission remains unchanged; excluded records were not scored. Durable replay is a separate coordinator gate. No provider execution or overall Phase 5 acceptance is established by retention, and the human labels and approved limited 5E evaluation remain unchanged.

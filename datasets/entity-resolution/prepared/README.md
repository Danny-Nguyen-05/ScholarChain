# Exact prepared input for the frozen Phase 5C queue

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
python3 datasets/scripts/retain_prepared_population.py retain --source COMPLETED_RUN --destination NEW_DURABLE_RUN_DIRECTORY
```

It validates the original framing and part hashes before copying, copies into a
new sibling staging directory, verifies copied bytes and publishes the completed
run directory followed by the sibling manifest. Validation refuses a directory
whose sibling manifest is absent, including an interrupted publication. The
hard bound is 1,000 files / 96 MiB. This command performs no network calls,
Hadoop execution, identity decisions, metadata normalization or run-ID changes.

# Dataset scripts

`acquire_samples.py` uses the Python 3 standard library only. `validate_datasets.py`
requires PyYAML (see `requirements.txt`). On PEP 668 managed Python installs, use a
virtual environment:

```bash
python3 -m venv /tmp/scholarchain-datasets-venv
/tmp/scholarchain-datasets-venv/bin/pip install -r datasets/scripts/requirements.txt
/tmp/scholarchain-datasets-venv/bin/python datasets/scripts/validate_datasets.py
```

## Default (no network)

```bash
python3 datasets/scripts/acquire_samples.py --mode regenerate
python3 datasets/scripts/validate_datasets.py
cd datasets && shasum -a 256 -c samples/SHA256SUMS
```

## Bounded refresh (explicit opt-in)

```bash
python3 datasets/scripts/acquire_samples.py --mode refresh --target all --rewrite-checksums
```

After refresh, update `committed_sample_sha256` values in `dataset-manifest.yaml`
to match `samples/SHA256SUMS`.

Refresh mode never downloads full DBLP, OpenAlex, ORCID, or Crossref corpus files.

## Phase 5C entity-resolution population

The separate bounded CS metadata population and its source/access limitations are
in [entity-resolution/README.md](../entity-resolution/README.md). The accepted
four-source sample manifest and acquisition index are preserved.

- `acquire_resolution_population.py`: explicit opt-in public API requests, fixed
  caps, no credentials, no full corpus and no output overwrite. Extension copies
  an immutable completed population and carries its consumed budgets/refusals.
- `filter_resolution_population.py`: no-network CS venue selection; retains
  original acquisition records/responses separately and lists every exclusion.
- `validate_resolution_population.py`: no-network inventory, hash, bounds,
  source/native record provenance and original-response membership checks.
- `test_resolution_population.py`: deterministic acquisition, integrity and
  domain-filter cases, with no network or fabricated human reviews.

```bash
python3 datasets/scripts/validate_resolution_population.py datasets/entity-resolution/5c-2026-10-16-v3
python3 -m unittest discover -s datasets/scripts -p 'test_*.py' -v
```

## Exact prepared input retention (5C blocker B2)

`retain_prepared_population.py` copies an explicitly authorized completed Hadoop
population into a new durable dataset directory without rewriting any bytes or
run IDs. It retains exactly the export tree, completion/run manifests and required
nine job-success markers. A sibling manifest binds the entire retained inventory.
`test_prepared_retention.py` checks exact copying, missing/corrupt input rejection,
overwrite refusal and frozen real-copy integrity without network access.

```bash
python3 datasets/scripts/retain_prepared_population.py validate --population datasets/entity-resolution/prepared/bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3
```

See [the prepared population guide](../entity-resolution/prepared/README.md) for
clean-checkout replay and future human-checkpoint preservation. No Hadoop rerun or
new source acquisition is needed to load the existing frozen queue's input.

## Archived inactive Phase 5C attempts

The v1/v2 population directories retain their original manifests and compact
`archive-manifest.v1.json` pointers only. They are not complete validator inputs.
Their inactive payloads are preserved in a verified durable external archive;
final v3, prepared input, tests and runtime inputs remain complete in the repository.
See [archive verification commands and locations](../entity-resolution/README.md#replay-and-integrity)
for existing `shasum` checks and optional population validation of complete archive
copies. No acquisition/validation script logic changed for this packaging cleanup.

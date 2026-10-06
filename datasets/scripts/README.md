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

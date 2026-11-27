#!/usr/bin/env python3
"""Validate ScholarChain dataset manifest, sample checksums, and script bounds."""

from __future__ import annotations

import ast
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install with: pip install -r datasets/scripts/requirements.txt"
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dataset-manifest.yaml"
SHA256SUMS = ROOT / "samples" / "SHA256SUMS"
ACQUIRE_SCRIPT = ROOT / "scripts" / "acquire_samples.py"

REQUIRED_ENTRY_FIELDS = (
    "name",
    "required",
    "purpose",
    "source_url",
    "documentation_url",
    "license",
    "license_evidence_url",
    "snapshot_or_version",
    "retrieval_date",
    "format",
    "size_estimate",
    "size_estimate_source",
    "raw_prefix",
    "committed_sample",
    "committed_sample_sha256",
    "committed_sample_covers",
    "upstream_full_checksum",
    "bounded_subset_rule",
    "schema",
    "schema_version",
    "linkage_keys",
    "update_method",
    "limitations",
    "privacy_considerations",
    "validation_commands",
    "owning_agent",
    "acquisition_script",
    "default_download_bounded",
    "max_download_bound",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        raise SystemExit(f"missing manifest: {MANIFEST}")
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "datasets" not in data:
        raise SystemExit("manifest must contain top-level 'datasets' mapping")
    return data


def validate_manifest_structure(manifest: dict) -> None:
    datasets = manifest["datasets"]
    if not isinstance(datasets, dict) or len(datasets) < 4:
        raise SystemExit("manifest must define at least four datasets (DBLP + three enrichments)")
    for key, entry in datasets.items():
        if not isinstance(entry, dict):
            raise SystemExit(f"dataset {key} must be a mapping")
        missing = [f for f in REQUIRED_ENTRY_FIELDS if f not in entry]
        if missing:
            raise SystemExit(f"dataset {key} missing fields: {', '.join(missing)}")
        if not entry["default_download_bounded"]:
            raise SystemExit(f"dataset {key} must set default_download_bounded: true")
        if not entry["committed_sample_sha256"]:
            raise SystemExit(f"dataset {key} missing committed_sample_sha256")
        if entry.get("required") is True and key != "dblp":
            pass  # only dblp flagged required
    if not datasets.get("dblp", {}).get("required"):
        raise SystemExit("dblp entry must set required: true")


SCHEMA_VERSION_RE = re.compile(r"^scholarchain\.[a-z0-9-]+-schema\.v[0-9]+$")
SCHEMA_VERSION_LINE = "**Schema version:**"


def validate_schema_versions(manifest: dict) -> None:
    """Each entry's schema_version must be stated in the schema note it points to."""
    for key, entry in manifest["datasets"].items():
        version = entry["schema_version"]
        if not isinstance(version, str) or not SCHEMA_VERSION_RE.match(version):
            raise SystemExit(f"dataset {key} schema_version is not a valid id: {version!r}")
        note = ROOT / entry["schema"]
        if not note.is_file():
            raise SystemExit(f"schema note missing for {key}: {entry['schema']}")
        statements = [
            line
            for line in note.read_text(encoding="utf-8").splitlines()
            if line.startswith(SCHEMA_VERSION_LINE)
        ]
        if not statements:
            raise SystemExit(f"{entry['schema']} has no '{SCHEMA_VERSION_LINE}' statement")
        if not any(f"`{version}`" in line for line in statements):
            raise SystemExit(
                f"{entry['schema']} schema version statement does not match manifest "
                f"schema_version {version} for {key}"
            )


def validate_sample_checksums(manifest: dict) -> None:
    if not SHA256SUMS.is_file():
        raise SystemExit(f"missing {SHA256SUMS}")
    sums: dict[str, str] = {}
    for line in SHA256SUMS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, rel = line.split(None, 1)
        sums[rel.strip()] = digest.lower()

    for key, entry in manifest["datasets"].items():
        rel = entry["committed_sample"]
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"committed sample missing for {key}: {rel}")
        expected = entry["committed_sample_sha256"].lower()
        actual = sha256_file(path)
        if actual != expected:
            raise SystemExit(
                f"checksum mismatch for {key} ({rel}): manifest {expected}, file {actual}"
            )
        if rel not in sums:
            raise SystemExit(f"{rel} not listed in samples/SHA256SUMS")
        if sums[rel] != expected:
            raise SystemExit(
                f"SHA256SUMS mismatch for {rel}: manifest {expected}, SHA256SUMS {sums[rel]}"
            )


def validate_acquire_script_bounds() -> None:
    source = ACQUIRE_SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cap_name = "DBLP_MAX_COMPRESSED_BYTES"
    cap_value = None

    def eval_const(node: ast.AST) -> int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            return eval_const(node.left) * eval_const(node.right)
        raise ValueError(f"unsupported constant expression: {ast.dump(node)}")

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == cap_name:
                    cap_value = eval_const(node.value)
    if cap_value is None:
        raise SystemExit(f"could not find {cap_name} in acquire_samples.py")
    if cap_value != 8388608:
        raise SystemExit(f"unexpected {cap_name}={cap_value}")

    if "dblp.xml.gz" in source and "Range" not in source:
        raise SystemExit("acquire_samples.py references gzip without HTTP Range bounds")
    if re.search(r"--mode\s+full|download_full_snapshot|FULL_SNAPSHOT", source):
        raise SystemExit("acquire_samples.py appears to allow full snapshot download")

    default_mode_regenerate = 'default="regenerate"' in source or "default='regenerate'" in source
    if not default_mode_regenerate:
        raise SystemExit("acquire_samples.py default mode must be regenerate (no network)")

    if "read_body_with_hard_cap" not in source:
        raise SystemExit(
            "acquire_samples.py must enforce a hard read cap (read_body_with_hard_cap)"
        )
    range_fn = re.search(
        r"def http_get_range\([^)]*\).*?(?=\ndef |\Z)", source, re.DOTALL
    )
    if not range_fn:
        raise SystemExit("acquire_samples.py missing http_get_range")
    range_src = range_fn.group(0)
    if "resp.read()" in range_src.replace("read_body_with_hard_cap", ""):
        raise SystemExit("http_get_range must not call unbounded resp.read()")
    if "206" not in range_src or "Content-Range" not in range_src:
        raise SystemExit("http_get_range must validate partial content (206 / Content-Range)")


def validate_dblp_sample_xml(manifest: dict) -> None:
    rel = manifest["datasets"]["dblp"]["committed_sample"]
    path = ROOT / rel
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        raise SystemExit(f"DBLP committed sample is not well-formed XML: {exc}") from exc


def main() -> None:
    manifest = load_manifest()
    validate_manifest_structure(manifest)
    validate_schema_versions(manifest)
    validate_sample_checksums(manifest)
    validate_dblp_sample_xml(manifest)
    validate_acquire_script_bounds()
    print(
        f"OK: manifest ({len(manifest['datasets'])} datasets), samples, and script bounds validated"
    )


if __name__ == "__main__":
    main()

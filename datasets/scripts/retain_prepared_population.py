#!/usr/bin/env python3
"""Retain exact completed Hadoop input with an explicitly declared purpose.

No Hadoop re-execution, network, UUID rewriting or source fact transformation.
The sibling retention manifest is mandatory for independent integrity checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

VERSION = "scholarchain.prepared-population-retention.v1"
MAX_FILES = 1000
MAX_BYTES = 96 * 1024 * 1024
FROZEN_PURPOSE = "frozen-5c-review"
DEMO_PURPOSE = "development-demo"
PURPOSES = {
    FROZEN_PURPOSE: "Exact immutable completed preparation input for frozen Phase 5C review population and future human-label evaluation replay.",
    DEMO_PURPOSE: "Exact immutable completed preparation input for Phase 5D development/demo evidence only; not frozen review, gold labels or held-out evaluation input."
}
FROZEN_RUN = "run:bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3"
DEMO_RUNS = {"run:3bfbd651-5982-4f3d-b29b-246fb88d07a1", "run:68c2b012-6d04-4eef-a7bf-5ca31706d895"}
OWNERSHIP = {
    FROZEN_PURPOSE: "dataset-engineer owns datasets/** prepared evaluation population material; no constitutional ownership change.",
    DEMO_PURPOSE: "dataset-engineer owns datasets/** prepared development/demo evidence material; no constitutional ownership change."
}
REQUIRED = ("_SCHOLARCHAIN_COMPLETE", "run-manifest.json", "export/_SUCCESS") + tuple(
    f"intermediate/j{n:02d}/_SUCCESS" for n in range(1, 9))


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_file(root, relative):
    rel = Path(relative)
    if not relative or rel.is_absolute() or ".." in rel.parts or rel.as_posix() != relative:
        raise ValueError("unsafe retained relative path: " + relative)
    path = root / rel
    for part in [path] + list(path.parents):
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError("symlink in prepared population: " + relative)
    if not path.is_file():
        raise ValueError("missing required prepared file: " + relative)
    return path


def framed_files(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("completed prepared directory required")
    for rel in REQUIRED:
        safe_file(root, rel)
    marker = json.loads((root / "_SCHOLARCHAIN_COMPLETE").read_bytes())
    run_manifest = json.loads((root / "run-manifest.json").read_bytes())
    if not marker.get("complete") or marker.get("runId") != run_manifest.get("runId"):
        raise ValueError("incomplete or mismatched prepared run identity")
    if marker.get("configFingerprint") != run_manifest.get("configFingerprint"):
        raise ValueError("prepared config fingerprint mismatch")
    exports = []
    for path in sorted((root / "export").rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink in prepared export")
        if path.is_file():
            exports.append(path.relative_to(root).as_posix())
    data_files = {rel.removeprefix("export/") for rel in exports
                  if not Path(rel).name.startswith(("_", ".")) and not rel.endswith(".crc")}
    parts = marker.get("exportParts", [])
    if not parts or len(parts) != len({part["path"] for part in parts}) or data_files != {part["path"] for part in parts}:
        raise ValueError("completion marker does not cover exact export inventory")
    for part in parts:
        path = safe_file(root, "export/" + part["path"])
        if path.stat().st_size != part["bytes"] or sha256(path) != part["sha256"]:
            raise ValueError("completion export hash/size mismatch: " + part["path"])
    partitions = {Path(rel).parent.as_posix() for rel in data_files if Path(rel).parent.as_posix() != "."}
    if len(marker.get("partitions", [])) != len(set(marker.get("partitions", []))) or set(marker["partitions"]) != partitions:
        raise ValueError("completion export partitions mismatch")
    files = sorted(set(exports) | set(REQUIRED))
    if len(files) > MAX_FILES or sum(safe_file(root, rel).stat().st_size for rel in files) > MAX_BYTES:
        raise ValueError("prepared retention file/byte bound exceeded")
    return files, marker


def manifest_path(root):
    return root.with_name(root.name + ".retention-manifest.v1.json")


def check_purpose(manifest):
    kind = manifest.get("purposeKind")
    # Preserve the accepted original 5C manifest verbatim. No other untyped
    # manifest may silently inherit its historical review/evaluation claim.
    if kind is None and manifest.get("runId") == FROZEN_RUN:
        kind = FROZEN_PURPOSE
    if kind not in PURPOSES or manifest.get("purpose") != PURPOSES[kind] or manifest.get("ownership") != OWNERSHIP[kind]:
        raise ValueError("missing, unsupported or inconsistent retention purpose")
    if manifest.get("runId") in DEMO_RUNS and kind != DEMO_PURPOSE:
        raise ValueError("known Phase 5D demo input cannot claim frozen review purpose")
    if manifest.get("runId") == FROZEN_RUN and kind != FROZEN_PURPOSE:
        raise ValueError("frozen Phase 5C review input cannot claim demo purpose")
    return kind


def validate(root):
    root = root.absolute()
    manifest = json.loads(manifest_path(root).read_bytes())
    if manifest.get("version") != VERSION or manifest.get("retainedDirectory") != root.name:
        raise ValueError("unsupported or mismatched retention manifest")
    purpose = check_purpose(manifest)
    files, marker = framed_files(root)
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != set(files) or set(files) != set(manifest["files"]):
        raise ValueError("retained run file inventory differs from manifest")
    for rel, fact in manifest["files"].items():
        path = safe_file(root, rel)
        if path.stat().st_size != fact["bytes"] or sha256(path) != fact["sha256"]:
            raise ValueError("retention hash/size mismatch: " + rel)
    if marker["runId"] != manifest["runId"]:
        raise ValueError("retained run ID differs from manifest")
    count, total = len(files), sum(fact["bytes"] for fact in manifest["files"].values())
    if count != manifest["fileCount"] or total != manifest["totalBytes"]:
        raise ValueError("retention totals mismatch")
    return {"status": "VALID", "runId": marker["runId"], "purposeKind": purpose, "files": count,
            "bytes": total, "completionSha256": sha256(root / "_SCHOLARCHAIN_COMPLETE"),
            "runManifestSha256": sha256(root / "run-manifest.json")}


def retain(source, destination, *, purpose):
    if purpose not in PURPOSES:
        raise ValueError("explicit supported retention purpose required")
    source, destination = source.absolute(), destination.absolute()
    if destination.exists() or manifest_path(destination).exists():
        raise ValueError("retention destination already exists; never overwrite")
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("retention source and destination must be disjoint")
    files, marker = framed_files(source)
    check_purpose({"runId": marker["runId"], "purposeKind": purpose,
                   "purpose": PURPOSES[purpose], "ownership": OWNERSHIP[purpose]})
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".prepared-retention-", dir=destination.parent))
    pending_manifest = None
    try:
        facts = {}
        for rel in files:
            original = safe_file(source, rel)
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            facts[rel] = {"bytes": original.stat().st_size, "sha256": sha256(original)}
            if target.stat().st_size != facts[rel]["bytes"] or sha256(target) != facts[rel]["sha256"]:
                raise ValueError("source changed while retaining: " + rel)
        copied, copied_marker = framed_files(staging)
        if copied != files or copied_marker != marker:
            raise ValueError("prepared source changed during retention")
        document = {"version": VERSION, "retainedDirectory": destination.name,
                    "runId": marker["runId"], "sourceRunDirectoryName": source.name,
                    "purposeKind": purpose, "purpose": PURPOSES[purpose],
                    "ownership": OWNERSHIP[purpose],
                    "retentionScope": "entire export/**, original completion and run manifests, eight intermediate job success files; no source/run ID/path rewriting",
                    "omitted": "Intermediate data parts, stats and counter summary are not read by the ER InputLoader. They are not claimed retained.",
                    "bounds": {"maxFiles": MAX_FILES, "maxBytes": MAX_BYTES},
                    "fileCount": len(facts), "totalBytes": sum(row["bytes"] for row in facts.values()), "files": facts}
        fd, pending = tempfile.mkstemp(prefix=".prepared-manifest-", dir=destination.parent)
        pending_manifest = Path(pending)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(document, file, sort_keys=True, indent=2)
            file.write("\n")
        if destination.exists() or manifest_path(destination).exists():
            raise ValueError("retention destination appeared before publish")
        staging.rename(destination)
        pending_manifest.rename(manifest_path(destination))
        return validate(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if pending_manifest is not None and pending_manifest.exists():
            pending_manifest.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("retain")
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--destination", type=Path, required=True)
    create.add_argument("--purpose", choices=tuple(PURPOSES), required=True,
                        help="declare frozen review input or separate development/demo evidence")
    check = sub.add_parser("validate")
    check.add_argument("--population", type=Path, required=True)
    args = parser.parse_args()
    result = retain(args.source, args.destination, purpose=args.purpose) if args.command == "retain" else validate(args.population)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Retain the exact completed Hadoop input consumed by a frozen review queue.

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


def validate(root):
    root = root.absolute()
    manifest = json.loads(manifest_path(root).read_bytes())
    if manifest.get("version") != VERSION or manifest.get("retainedDirectory") != root.name:
        raise ValueError("unsupported or mismatched retention manifest")
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
    return {"status": "VALID", "runId": marker["runId"], "files": count,
            "bytes": total, "completionSha256": sha256(root / "_SCHOLARCHAIN_COMPLETE"),
            "runManifestSha256": sha256(root / "run-manifest.json")}


def retain(source, destination):
    source, destination = source.absolute(), destination.absolute()
    if destination.exists() or manifest_path(destination).exists():
        raise ValueError("retention destination already exists; never overwrite")
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("retention source and destination must be disjoint")
    files, marker = framed_files(source)
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
                    "purpose": "Exact immutable completed preparation input for frozen Phase 5C review population and future human-label evaluation replay.",
                    "ownership": "dataset-engineer owns datasets/** prepared evaluation population material; no constitutional ownership change.",
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
    check = sub.add_parser("validate")
    check.add_argument("--population", type=Path, required=True)
    args = parser.parse_args()
    result = retain(args.source, args.destination) if args.command == "retain" else validate(args.population)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

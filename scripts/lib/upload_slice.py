#!/usr/bin/env python3
"""Planning, comparison and manifest helper of scripts/upload-slice.sh (stdlib only; run as python3 -I).

The shell script owns every AWS call; this module owns the pure decisions so they are testable without AWS:
which local files of a COMPLETED Phase 6 export are uploaded, their keys under <run_prefix>/, their sha256, and the
comparison of what S3 reports with what was planned. It never calls a cloud API and never prints a credential.

Subcommands (exit 0 ok, 1 refused with an "UPLOAD-REFUSED: <reason>" line on stdout, 2 usage)
  scan       --export DIR --prefix RUN_PREFIX --out PLAN.json     validate the export, hash every file, write the plan
  existing   --plan PLAN.json --listing LIST.json                  print "EXISTING <index>" for every planned key already listed
  compare    --plan PLAN.json --index N --attributes ATTR.json     an existing object must hold the planned bytes
  put        --plan PLAN.json --index N --response RESP.json --results R.jsonl   record an upload response
  verify     --plan PLAN.json --index N --head HEAD.json --state S --results R.jsonl   head-object must equal the plan
  list       --plan PLAN.json [--only-file F | --skip-file F]      print "<index>TAB<relative path>TAB<key>TAB<base64 sha256>" rows
  manifest   --plan PLAN.json --results R.jsonl --bucket-label L --region R --created-utc T --commit C   JSON on stdout
"""
import argparse
import base64
import hashlib
import json
import os
import re
import stat
import sys

SCHEMA = "scholarchain.upload-manifest.v1"
RUN_PREFIX_RE = re.compile(r"^run-[a-z0-9][a-z0-9-]{1,27}$")  # the same rule as the deployer's operator_run_prefix
# '%' is accepted only as the exact escape %3A (uppercase): Spark writes a ':' in a partition value as %3A, so the real
# export directories are named run_id=run%3A<uuid>. Every other '%' sequence (%20, %2F, %2E, %3a, a bare '%') is refused.
# The key stays byte-identical to the on-disk path (S3 stores the literal '%3A').
KEY_CHARS_RE = re.compile(r"^(?:[A-Za-z0-9._=:+@/-]|%3A)+$")
TABLE_ROOTS = ("nodes", "edges", "metrics", "path-evidence", "semantic-summaries")
TYPED_ROOTS = ("nodes", "edges", "metrics")  # one table per type=<name> directory
ROOT_FILES = ("run-manifest.json", "run-metadata.json", "counters.json", "_SCHOLARCHAIN_SPARK_COMPLETE")
MANIFEST_DIR = "load-manifests"
MAX_FILES = 5000
MAX_FILE_BYTES = 5 * 1024 ** 3 - 1  # PutObject accepts at most 5 GiB per request
MAX_TOTAL_BYTES = 20 * 1024 ** 3
MAX_KEY_BYTES = 1024
MARKER_MAX_BYTES = 4 * 1024 * 1024


class Refused(Exception):
    pass


def refuse(message):
    raise Refused(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.digest()


def read_small(path, limit=MARKER_MAX_BYTES):
    if os.path.getsize(path) > limit:
        refuse("%s is larger than %d bytes" % (os.path.basename(path), limit))
    with open(path, "rb") as handle:
        return handle.read()


def check_prefix(prefix):
    if not isinstance(prefix, str) or not RUN_PREFIX_RE.match(prefix):
        refuse("the run prefix must match ^run-[a-z0-9][a-z0-9-]{1,27}$ (for example run-20261115)")
    return prefix


def check_key(key, prefix):
    if not key.startswith(prefix + "/") or len(key) == len(prefix) + 1:
        refuse("key %s is outside the run prefix %s/" % (key, prefix))
    if len(key.encode("utf-8")) > MAX_KEY_BYTES or not KEY_CHARS_RE.match(key):
        refuse("key %s has characters or a length outside the accepted set" % key)
    parts = key.split("/")
    if any(part in ("", ".", "..") for part in parts):
        refuse("key %s has an empty, '.' or '..' segment" % key)
    return key


def lstat_regular(path, label):
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        refuse("%s is a symbolic link; symlinks are never uploaded" % label)
    if not stat.S_ISREG(info.st_mode):
        refuse("%s is not a regular file" % label)
    return info.st_size


def verify_completed(base):
    """The export must be COMPLETE: manifests present and the completion marker equal to the hash the Spark job writes
    (modules/storage ManifestRows.scala: sha256hex(run-manifest + LF + run-metadata) + LF)."""
    for name in ROOT_FILES:
        path = os.path.join(base, name)
        if not os.path.lexists(path):
            refuse("the export is not completed: %s is missing (no run manifest or completion marker)" % name)
        lstat_regular(path, name)
    manifest_dir = os.path.join(base, MANIFEST_DIR)
    if not os.path.isdir(manifest_dir) or os.path.islink(manifest_dir):
        refuse("the export is not completed: %s/ is missing" % MANIFEST_DIR)
    if not [n for n in os.listdir(manifest_dir) if n.endswith(".json")]:
        refuse("the export is not completed: %s/ holds no load manifest" % MANIFEST_DIR)
    run_manifest = read_small(os.path.join(base, "run-manifest.json"))
    run_metadata = read_small(os.path.join(base, "run-metadata.json"))
    marker = read_small(os.path.join(base, "_SCHOLARCHAIN_SPARK_COMPLETE")).decode("utf-8", "replace")
    expected = hashlib.sha256(run_manifest + b"\n" + run_metadata).hexdigest() + "\n"
    if marker != expected:
        refuse("the completion marker does not match run-manifest.json and run-metadata.json (incomplete or altered export)")
    try:
        run_id = json.loads(run_manifest.decode("utf-8")).get("runId")
        meta_id = json.loads(run_metadata.decode("utf-8")).get("runId")
    except (ValueError, AttributeError):
        refuse("run-manifest.json or run-metadata.json is not valid JSON")
    if not isinstance(run_id, str) or not run_id or run_id != meta_id:
        refuse("run-manifest.json and run-metadata.json do not name the same runId")
    return run_id, hashlib.sha256(marker.encode("utf-8")).hexdigest()


def is_sidecar(name):
    """Files Spark and Hadoop add next to the data; never uploaded."""
    return name.startswith(".") or name.startswith("_") or name.endswith(".crc")


def table_of(rel_parts):
    root = rel_parts[0]
    if root in TYPED_ROOTS:
        if len(rel_parts) < 3 or not rel_parts[1].startswith("type="):
            refuse("%s is not under %s/type=<name>/" % ("/".join(rel_parts), root))
        return "%s/%s" % (root, rel_parts[1])
    return root


def collect(base, prefix):
    entries, skipped = [], {}
    for name in ROOT_FILES:
        entries.append((name, None))
    manifest_dir = os.path.join(base, MANIFEST_DIR)
    for name in sorted(os.listdir(manifest_dir)):
        full = os.path.join(manifest_dir, name)
        if name.endswith(".json"):
            entries.append(("%s/%s" % (MANIFEST_DIR, name), None))
        else:
            lstat_regular(full, "%s/%s" % (MANIFEST_DIR, name))
            skipped["other"] = skipped.get("other", 0) + 1
    for root in TABLE_ROOTS:
        top = os.path.join(base, root)
        if not os.path.lexists(top):
            continue
        if os.path.islink(top) or not os.path.isdir(top):
            refuse("%s/ is not a real directory" % root)
        for current, dirs, files in os.walk(top, followlinks=False):
            dirs.sort()
            for directory in dirs:
                if os.path.islink(os.path.join(current, directory)):
                    refuse("%s is a symbolic link; symlinks are never uploaded" % os.path.relpath(os.path.join(current, directory), base))
            for name in sorted(files):
                rel = os.path.relpath(os.path.join(current, name), base)
                if is_sidecar(name):
                    skipped["sidecar"] = skipped.get("sidecar", 0) + 1
                    continue
                if not name.endswith(".parquet"):
                    refuse("unexpected file %s inside the export tables (only Parquet part files are uploaded)" % rel)
                entries.append((rel.replace(os.sep, "/"), table_of(rel.split(os.sep))))
    for name in sorted(os.listdir(base)):
        if name in ROOT_FILES or name == MANIFEST_DIR or name in TABLE_ROOTS:
            continue
        skipped["not-uploaded:" + name] = 1
    return entries, skipped


def cmd_scan(args):
    prefix = check_prefix(args.prefix)
    export = args.export
    if not os.path.isdir(export):
        refuse("the export directory does not exist: %s" % os.path.basename(export.rstrip("/")))
    base = os.path.realpath(export)
    run_id, marker_sha = verify_completed(base)
    entries, skipped = collect(base, prefix)
    parquet = [e for e in entries if e[1] is not None]
    if not parquet:
        refuse("the export holds no Parquet table files")
    if len(entries) > MAX_FILES:
        refuse("the export has %d files; the limit is %d" % (len(entries), MAX_FILES))
    seen, files, total = set(), [], 0
    for rel, table in entries:
        key = check_key("%s/%s" % (prefix, rel), prefix)
        if key in seen:
            refuse("duplicate key %s" % key)
        seen.add(key)
        path = os.path.join(base, rel)
        size = lstat_regular(path, rel)
        if size > MAX_FILE_BYTES:
            refuse("%s is %d bytes; one PutObject request is limited to 5 GiB" % (rel, size))
        total += size
        if total > MAX_TOTAL_BYTES:
            refuse("the export exceeds the %d byte upload limit of this tool" % MAX_TOTAL_BYTES)
        raw = sha256_file(path)
        files.append({
            "rel": rel, "key": key, "bytes": size, "sha256": raw.hex(),
            "checksum_sha256_b64": base64.b64encode(raw).decode("ascii"), "table": table,
        })
    tables = sorted({f["table"] for f in files if f["table"]})
    plan = {"run_prefix": prefix, "export_run_id": run_id, "marker_sha256": marker_sha, "tables": tables, "skipped": skipped, "files": files, "total_bytes": total}
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(plan, handle, sort_keys=True)
    print("EXPORT-RUN: id=%s tables=%d files=%d bytes=%d" % (run_id, len(tables), len(files), total))
    for name, count in sorted(skipped.items()):
        print("EXPORT-SKIPPED: %s count=%d" % (name, count))
    for index, item in enumerate(files):
        print("UPLOAD-FILE: %d path=%s key=%s bytes=%d sha256=%s" % (index, item["rel"], item["key"], item["bytes"], item["sha256"]))
    return 0


def load_plan(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def planned(plan, index):
    try:
        return plan["files"][int(index)]
    except (IndexError, ValueError, KeyError):
        refuse("no planned file with index %s" % index)


def load_json_or_empty(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read().strip()
    if not text or text == "null":
        return {}
    try:
        return json.loads(text)
    except ValueError:
        refuse("an AWS response was not valid JSON")


def read_indices(path):
    with open(path, encoding="utf-8") as handle:
        return {int(line.strip()) for line in handle if line.strip()}


def cmd_list(args):
    plan = load_plan(args.plan)
    only = read_indices(args.only_file) if args.only_file else None
    skip = read_indices(args.skip_file) if args.skip_file else set()
    for index, item in enumerate(plan["files"]):
        if (only is not None and index not in only) or index in skip:
            continue
        print("%d\t%s\t%s\t%s" % (index, item["rel"], item["key"], item["checksum_sha256_b64"]))
    return 0


def cmd_existing(args):
    plan = load_plan(args.plan)
    listing = load_json_or_empty(args.listing)
    listed = {}
    for item in listing.get("Contents") or []:
        if isinstance(item, dict) and isinstance(item.get("Key"), str):
            listed[item["Key"]] = item.get("Size")
    count = 0
    for index, item in enumerate(plan["files"]):
        if item["key"] in listed:
            count += 1
            print("EXISTING %d %s size=%s" % (index, item["key"], listed[item["key"]]))
    print("PREFLIGHT: listed=%d planned=%d existing=%d new=%d" % (len(listed), len(plan["files"]), count, len(plan["files"]) - count))
    return 0


def cmd_compare(args):
    plan = load_plan(args.plan)
    item = planned(plan, args.index)
    attrs = load_json_or_empty(args.attributes)
    remote_sum = (attrs.get("Checksum") or {}).get("ChecksumSHA256")
    remote_size = attrs.get("ObjectSize")
    if not remote_sum:
        refuse("existing object %s has no SHA-256 checksum, so its content cannot be proven equal; nothing was uploaded" % item["key"])
    if remote_sum != item["checksum_sha256_b64"] or remote_size != item["bytes"]:
        refuse("existing object %s has different content (size or SHA-256 differs); nothing was uploaded and nothing was overwritten" % item["key"])
    print("UNCHANGED: %s" % item["key"])
    return 0


def append_result(path, record):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def cmd_put(args):
    plan = load_plan(args.plan)
    item = planned(plan, args.index)
    response = load_json_or_empty(args.response)
    checksum = response.get("ChecksumSHA256")
    if checksum and checksum != item["checksum_sha256_b64"]:
        refuse("S3 reported a different SHA-256 for %s than the local file" % item["key"])
    append_result(args.results, {"index": int(args.index), "status": "uploaded", "version_id": response.get("VersionId")})
    print("UPLOADED: %s bytes=%d" % (item["key"], item["bytes"]))
    return 0


def cmd_verify(args):
    plan = load_plan(args.plan)
    item = planned(plan, args.index)
    head = load_json_or_empty(args.head)
    if head.get("ContentLength") != item["bytes"]:
        refuse("%s: stored size %s differs from the local %d bytes" % (item["key"], head.get("ContentLength"), item["bytes"]))
    if head.get("ChecksumSHA256") != item["checksum_sha256_b64"]:
        refuse("%s: stored SHA-256 differs from the local file" % item["key"])
    append_result(args.results, {"index": int(args.index), "status": args.state, "verified": True, "version_id": head.get("VersionId")})
    print("VERIFIED: %s bytes=%d" % (item["key"], item["bytes"]))
    return 0


def cmd_manifest(args):
    plan = load_plan(args.plan)
    status, version = {}, {}
    with open(args.results, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("verified"):
                status[record["index"]] = record["status"]
                version[record["index"]] = record.get("version_id")
    files = []
    for index, item in enumerate(plan["files"]):
        if index not in status:
            refuse("%s was not verified; no manifest is written" % item["key"])
        files.append({
            "key": item["key"], "bytes": item["bytes"], "sha256": item["sha256"],
            "checksum_sha256_b64": item["checksum_sha256_b64"], "version_id": version.get(index), "status": status[index],
        })
    files.sort(key=lambda f: f["key"])
    document = {
        "schema": SCHEMA, "created_utc": args.created_utc, "commit": args.commit, "bucket": args.bucket_label, "region": args.region,
        "run_prefix": plan["run_prefix"], "export_run_id": plan["export_run_id"], "export_marker_sha256": plan["marker_sha256"],
        "tables": plan["tables"],
        "totals": {"files": len(files), "bytes": plan["total_bytes"], "uploaded": sum(1 for f in files if f["status"] == "uploaded"),
                   "unchanged": sum(1 for f in files if f["status"] == "unchanged")},
        "files": files,
    }
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="upload_slice.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan")
    p.add_argument("--export", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("list")
    p.add_argument("--plan", required=True)
    p.add_argument("--only-file")
    p.add_argument("--skip-file")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("existing")
    p.add_argument("--plan", required=True)
    p.add_argument("--listing", required=True)
    p.set_defaults(fn=cmd_existing)
    p = sub.add_parser("compare")
    p.add_argument("--plan", required=True)
    p.add_argument("--index", required=True)
    p.add_argument("--attributes", required=True)
    p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("put")
    p.add_argument("--plan", required=True)
    p.add_argument("--index", required=True)
    p.add_argument("--response", required=True)
    p.add_argument("--results", required=True)
    p.set_defaults(fn=cmd_put)
    p = sub.add_parser("verify")
    p.add_argument("--plan", required=True)
    p.add_argument("--index", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--state", required=True, choices=("uploaded", "unchanged"))
    p.add_argument("--results", required=True)
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("manifest")
    p.add_argument("--plan", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--bucket-label", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--created-utc", required=True)
    p.add_argument("--commit", required=True)
    p.set_defaults(fn=cmd_manifest)
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except Refused as error:
        print("UPLOAD-REFUSED: %s" % error)
        return 1
    except OSError as error:
        print("UPLOAD-REFUSED: %s" % error.strerror)
        return 1


if __name__ == "__main__":
    sys.exit(main())

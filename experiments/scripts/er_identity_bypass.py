#!/usr/bin/env python3
"""Phase 15 second-size experiment: write an IDENTITY entity-resolution run root from a completed Hadoop prep run (offline, stdlib).

ER BYPASSED: identity pass-through (no cross-source resolution), local only, not the EMR path.

Why: at size L the real ER step (Phase5Main) runs out of memory locally (> 22 GB heap after 16 min), so Spark could never be timed at L.
The human decision (Phase 15, 2026-11-16) allows a disclosed identity bypass when it needs no module, JAR, step-program, pin or EMR
change. This script is that bypass. It never runs ER and never invents a match: it writes an ER run root with ZERO accepted links, ZERO
cannot-links, ZERO authoritative identifiers and ZERO unresolved/conflict decisions for both entity types.

Identity pass-through, as the unchanged Spark job then interprets it (modules/spark/.../Phase6CJobs.scala):
  * every DBLP author string resolves to itself: researcherId = StableIds.researcherIdFromDblpName(identity-v1, nameText);
  * no cross-source matches: non-DBLP mentions (OpenAlex, Crossref, ORCID) stay unmapped; each source work is its own canonical work.

The output satisfies the Spark ER input contract read by Phase6CReaders.verifyEr / requireErPrepBinding / load:
  resolution-manifest.json  schemaVersion scholarchain.resolution-export.v1, complete=true, runId run:<uuid v4>, policyVersion,
                            policyHash (64 hex), prepCompletionHash = sha256(hadoop marker text + "\\n" + hadoop run-manifest text),
                            files[] = every inventory file with path, bytes, sha256, records; constraints[] has exactly 2 entries
  _SCHOLARCHAIN_RESOLUTION_COMPLETE  sha256(manifest text) + "\\n"
  {researcher,work}/{accepted-links,unresolved,conflict}.jsonl   empty
  {researcher,work}/grouping-constraints.json  one JSON line, schemaVersion scholarchain.resolution.v1, empty arrays
  bypass-policy.json  the identity policy and the disclosure (hashed into policyHash)
Every value is derived from the Hadoop input bytes and fixed text, so two runs on the same input are byte-identical (no timestamps).

Refusals (exit 2): the input is not a completed Hadoop prep run (missing/invalid _SCHOLARCHAIN_COMPLETE, run-manifest.json or
export/_SUCCESS, schema mismatch, runId/config mismatch, export inventory or byte-size mismatch; an ER run root is refused), or the output
path already exists. --verify-hashes additionally checks every export part sha256 (Spark re-checks them anyway).

Usage (repository root):
  python3 -I experiments/scripts/er_identity_bypass.py --hadoop-root <completed hadoop run dir> --out <new er run dir> [--verify-hashes]
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile

DISCLOSURE = "ER bypassed: identity pass-through (no cross-source resolution), local only, not the EMR path"
POLICY_VERSION = "er-identity-bypass-v1"
IMPLEMENTATION_VERSION = "experiments-er-identity-bypass-v1"
EXPORT_SCHEMA = "scholarchain.resolution-export.v1"
RESOLUTION_SCHEMA = "scholarchain.resolution.v1"
DOMAIN_SCHEMA = "scholarchain.domain.v1"
HADOOP_PREP_SCHEMA = "scholarchain.hadoop-prep.v1"
HADOOP_MARKER = "_SCHOLARCHAIN_COMPLETE"
ER_MARKER = "_SCHOLARCHAIN_RESOLUTION_COMPLETE"
ER_MANIFEST = "resolution-manifest.json"
ENTITIES = (("Researcher", "researcher"), ("Work", "work"))
EMPTY_DECISION_FILES = ("accepted-links.jsonl", "unresolved.jsonl", "conflict.jsonl")


class Refused(Exception):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def regular_file(root, name):
    path = os.path.join(root, name)
    if os.path.islink(path) or not os.path.isfile(path):
        raise Refused("not a completed Hadoop prep run: missing or unsafe %s under %s" % (name, root))
    return path


def read_text(path):
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8")


def visible_files(root):
    """Same filter as Phase6CReaders.actualFiles: regular files whose last segment starts with neither '.' nor '_'."""
    found = set()
    for current, _dirs, files in os.walk(root):
        for name in files:
            full = os.path.join(current, name)
            if os.path.isfile(full) and not name.startswith(".") and not name.startswith("_"):
                found.add(os.path.relpath(full, root).replace(os.sep, "/"))
    return found


def verify_hadoop(root, verify_hashes=False):
    """The checks Phase6CReaders.verifyHadoop makes (hashes optional); returns (hadoopRunId, prepCompletionHash, exportBytes)."""
    if os.path.islink(root) or not os.path.isdir(root):
        raise Refused("not a completed Hadoop prep run: %s is not a directory" % root)
    if os.path.exists(os.path.join(root, ER_MARKER)) or os.path.exists(os.path.join(root, ER_MANIFEST)):
        raise Refused("input is an entity-resolution run root, not a Hadoop prep run")
    marker_text = read_text(regular_file(root, HADOOP_MARKER))
    manifest_text = read_text(regular_file(root, "run-manifest.json"))
    try:
        marker, manifest = json.loads(marker_text), json.loads(manifest_text)
    except ValueError as error:
        raise Refused("not a completed Hadoop prep run: unparseable marker or manifest (%s)" % error)
    if not isinstance(marker, dict) or not isinstance(manifest, dict):
        raise Refused("not a completed Hadoop prep run: marker and manifest must be JSON objects")
    if marker.get("complete") is not True or marker.get("runId") != manifest.get("runId") or not marker.get("runId"):
        raise Refused("Hadoop completion/manifest mismatch")
    if (marker.get("schemaVersion") != DOMAIN_SCHEMA or marker.get("hadoopPrepSchema") != HADOOP_PREP_SCHEMA
            or marker.get("configFingerprint") != manifest.get("configFingerprint")):
        raise Refused("unsupported Hadoop completion schema/config")
    if manifest.get("pipelineName") not in (None, "hadoop-prep"):
        raise Refused("run-manifest.json is not a hadoop-prep manifest (pipelineName=%s)" % manifest.get("pipelineName"))
    export = os.path.join(root, "export")
    regular_file(root, "export/_SUCCESS")
    parts = marker.get("exportParts")
    if not isinstance(parts, list) or not parts:
        raise Refused("Hadoop export inventory missing")
    names = [p.get("path") for p in parts]
    if len(set(names)) != len(names) or visible_files(export) != set(names):
        raise Refused("Hadoop export inventory mismatch")
    total = 0
    for part in parts:
        name = part["path"]
        if os.path.isabs(name) or ".." in name.split("/"):
            raise Refused("unsafe export path %s" % name)
        path = regular_file(export, name)
        size = os.path.getsize(path)
        if size != int(part["bytes"]) or (verify_hashes and sha256_file(path) != part["sha256"]):
            raise Refused("Hadoop export byte/hash mismatch: %s" % name)
        total += size
    prep_hash = sha256_bytes((marker_text + "\n" + manifest_text).encode("utf-8"))
    return marker["runId"], prep_hash, total


def uuid4_from(hex_material):
    """A deterministic string in the run:<uuid v4> form that StableIds.parseRunId accepts (version nibble 4, variant 8..b)."""
    h = list(hex_material[:32])
    h[12] = "4"
    h[16] = "89ab"[int(h[16], 16) & 3]
    s = "".join(h)
    return "run:%s-%s-%s-%s-%s" % (s[0:8], s[8:12], s[12:16], s[16:20], s[20:32])


def build(hadoop_root, out, verify_hashes=False):
    hadoop_root, out = os.path.abspath(hadoop_root), os.path.abspath(out)
    if os.path.lexists(out):
        raise Refused("output %s already exists: an ER run root is never overwritten" % out)
    hadoop_run_id, prep_hash, export_bytes = verify_hadoop(hadoop_root, verify_hashes)
    policy = {
        "schemaVersion": "scholarchain.er-identity-bypass.v1",
        "policyVersion": POLICY_VERSION,
        "disclosure": DISCLOSURE,
        "researcherRule": "every DBLP author string resolves to itself (Spark researcherIdFromDblpName); no accepted researcher links",
        "workRule": "every source work is its own canonical work; no accepted work links",
        "crossSourceMatches": 0,
        "llmCalls": 0,
        "erJarExecuted": False,
    }
    policy_text = compact(policy) + "\n"
    policy_hash = sha256_bytes(policy_text.encode("utf-8"))
    run_id = uuid4_from(sha256_bytes(("%s\n%s\n%s" % (POLICY_VERSION, policy_hash, prep_hash)).encode("utf-8")))
    contents = {"bypass-policy.json": (policy_text, 1)}
    for entity, folder in ENTITIES:
        for name in EMPTY_DECISION_FILES:
            contents["%s/%s" % (folder, name)] = ("", 0)
        constraint = {
            "schemaVersion": RESOLUTION_SCHEMA, "entityType": entity, "policyVersion": POLICY_VERSION, "policyHash": policy_hash,
            "coveredEndpoints": [], "cannotLinks": [], "authoritativeIdentifiers": [],
        }
        # Field order as the ER LinkExporter writes it; one line so Spark's line-delimited JSON reader sees one record.
        contents["%s/grouping-constraints.json" % folder] = (json.dumps(constraint, separators=(",", ":")) + "\n", 1)
    files = []
    for path in sorted(contents):
        text, records = contents[path]
        data = text.encode("utf-8")
        files.append({"path": path, "bytes": len(data), "sha256": sha256_bytes(data), "records": records})
    by_path = {f["path"]: f for f in files}
    manifest = {
        "schemaVersion": EXPORT_SCHEMA,
        "complete": True,
        "implementationVersion": IMPLEMENTATION_VERSION,
        "runId": run_id,
        "erBypassed": True,
        "disclosure": DISCLOSURE,
        "hadoopRunId": hadoop_run_id,
        "hadoopExportBytes": export_bytes,
        "prepCompletionHash": prep_hash,
        "policyVersion": POLICY_VERSION,
        "policyHash": policy_hash,
        "llmMode": "disabled",
        "fakeCalls": 0,
        "liveCalls": 0,
        "files": files,
        "constraints": [
            {"entityType": entity, "path": "%s/grouping-constraints.json" % folder,
             "sha256": by_path["%s/grouping-constraints.json" % folder]["sha256"],
             "coveredEndpoints": 0, "assertions": 0, "cannotLinks": 0}
            for entity, folder in (("Work", "work"), ("Researcher", "researcher"))
        ],
        "outcomeCounts": {"%s:%s" % (e, o): 0 for e, _ in ENTITIES for o in ("ACCEPTED", "REJECTED", "UNRESOLVED", "CONFLICT")},
    }
    manifest_text = compact(manifest)
    parent = os.path.dirname(out)
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".er-identity-bypass.", dir=parent)
    try:
        for path, (text, _records) in contents.items():
            full = os.path.join(staging, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as handle:
                handle.write(text.encode("utf-8"))
        with open(os.path.join(staging, ER_MANIFEST), "wb") as handle:
            handle.write(manifest_text.encode("utf-8"))
        with open(os.path.join(staging, ER_MARKER), "wb") as handle:  # written last: completion
            handle.write((sha256_bytes(manifest_text.encode("utf-8")) + "\n").encode("utf-8"))
        os.rename(staging, out)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {"erRunId": run_id, "hadoopRunId": hadoop_run_id, "prepCompletionHash": prep_hash, "policyVersion": POLICY_VERSION,
            "policyHash": policy_hash, "manifestSha256": sha256_bytes(manifest_text.encode("utf-8")), "files": len(files),
            "hadoopExportBytes": export_bytes, "out": out, "disclosure": DISCLOSURE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hadoop-root", required=True, help="completed Hadoop prep run directory (holds _SCHOLARCHAIN_COMPLETE)")
    parser.add_argument("--out", required=True, help="new ER run root to create (must not exist)")
    parser.add_argument("--verify-hashes", action="store_true", help="also check every Hadoop export part sha256")
    args = parser.parse_args(argv)
    try:
        result = build(args.hadoop_root, args.out, args.verify_hashes)
    except Refused as error:
        sys.stderr.write("REFUSED: %s\n" % error)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

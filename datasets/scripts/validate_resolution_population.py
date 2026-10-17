#!/usr/bin/env python3
"""Verify a completed bounded Phase 5C population without network access."""
import argparse
import collections
import json
from pathlib import Path

from acquire_resolution_population import BOUNDS, VERSION, canonical_doi, digest, encoded


def validate(root):
    root = root.resolve()
    manifest_path = root / "population-manifest.v1.json"
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get("version") != VERSION or manifest.get("bounds") != BOUNDS:
        raise ValueError("unsupported population manifest or bounds")
    if manifest.get("humanReviews") != 0:
        raise ValueError("acquisition cannot claim human labels")
    files = manifest["files"]
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(files) | {"population-manifest.v1.json"}:
        raise ValueError("file inventory differs from final manifest")
    for rel, fact in files.items():
        path = root / rel
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("unsafe population path")
        body = path.read_bytes()
        if len(body) != fact["bytes"] or digest(body) != fact["sha256"]:
            raise ValueError("hash/size mismatch: " + rel)
    ledger = [json.loads(line) for line in (root / "request-ledger.jsonl").read_bytes().splitlines()]
    counts = collections.Counter(event["source"] for event in ledger)
    if [row["attempt"] for row in ledger] != list(range(1, len(ledger) + 1)):
        raise ValueError("HTTP attempts must be unique, contiguous and ordered")
    if len(ledger) > BOUNDS["totalAttempts"] or any(counts[s] > BOUNDS["attempts"][s] for s in counts):
        raise ValueError("HTTP attempt cap exceeded")
    total_bytes = sum(row["bytesRead"] for row in ledger)
    if total_bytes > BOUNDS["totalBytes"] or total_bytes != manifest["observed"]["responseBytes"]:
        raise ValueError("HTTP byte cap/count mismatch")
    if manifest["observed"]["seconds"] > BOUNDS["seconds"] + BOUNDS["timeoutSeconds"]:
        raise ValueError("time allowance exceeded")
    if counts != manifest["observed"]["attempts"] or len(ledger) != manifest["observed"]["totalAttempts"]:
        raise ValueError("HTTP source counters disagree")
    for row in ledger:
        if row.get("responsePath"):
            body = (root / row["responsePath"]).read_bytes()
            if len(body) != row["bytesRead"] or digest(body) != row["sha256"]:
                raise ValueError("retained response hash mismatch")
    provenance = [json.loads(line) for line in (root / "record-provenance.jsonl").read_bytes().splitlines()]
    index = {(row["source"], row["nativeId"]): row for row in provenance}
    if len(index) != len(provenance):
        raise ValueError("duplicate observation provenance")
    summary = {}
    for source, fact in manifest["sources"].items():
        body = (root / fact["path"]).read_bytes()
        if digest(body) != fact["sha256"] or len(body) != fact["bytes"]:
            raise ValueError("source checksum mismatch")
        rows = [] if source == "dblp" else [json.loads(line) for line in body.splitlines()]
        if source == "dblp" and fact["records"] != 0:
            raise ValueError("this acquisition version cannot claim DBLP records")
        if len(rows) != fact["records"] or len(rows) > BOUNDS["records"][source]:
            raise ValueError("source record count/cap mismatch")
        natives = set()
        for item in rows:
            native = canonical_doi(item["message"]["DOI"]) if source == "crossref" else item["id"] if source == "openalex" else item["orcid-identifier"]["path"]
            if native in natives or (source, native) not in index:
                raise ValueError("duplicate or unprovenanced source record")
            natives.add(native)
            proof = index[(source, native)]
            event = ledger[proof["requestAttempt"] - 1]
            if event["source"] != source or event["result"] != "ok" or digest(encoded(item)) != proof["normalizedRecordSha256"]:
                raise ValueError("source record is not bound to successful original response")
            response = json.loads((root / event["responsePath"]).read_bytes())
            original = response.get("message", {}).get("items", []) if source == "crossref" else response.get("results", []) if source == "openalex" else [response]
            target = item["message"] if source == "crossref" else item
            if target not in original:
                raise ValueError("record does not equal a selected original response object")
            if source == "openalex" and proof["stratum"] != "crossref-doi-match" and not 2018 <= item.get("publication_year", 0) <= 2024:
                raise ValueError("OpenAlex work outside selected year window")
            if source == "crossref" and "abstract" in item["message"]:
                raise ValueError("unrequested copyrighted abstract retained")
            if source == "openalex" and "abstract_inverted_index" in item:
                raise ValueError("unrequested abstract retained")
        summary[source] = len(rows)
    if sum(summary.values()) != len(provenance):
        raise ValueError("unbound extra provenance")
    return {"status": "VALID", "records": summary, "hashedFiles": len(files), "attempts": len(ledger), "responseBytes": total_bytes, "humanReviews": 0, "candidateReadiness": manifest["readiness"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("population", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.population), indent=2))

#!/usr/bin/env python3
"""Publish a CS-focused derived ingestion population, preserving acquisition bytes.

No network, labels, predictions, identity decisions or source fact edits.
"""
import argparse
import collections
import json
import re
import shutil
from pathlib import Path

from acquire_resolution_population import canonical_doi, digest, encoded
from validate_resolution_population import validate

CS_VENUE = re.compile(
    r"sigmod|vldb|very large data bases|data engineering|cloud computing|middleware|"
    r"distributed computing systems|operating systems|principles of database|management of data|"
    r"parallel and distributed|distributed and parallel|transactions on database|"
    r"eurosys|computer systems|computing surveys|supercomputing|high performance computing|"
    r"parallel processing|data management", re.I)


def derive(base, output):
    validate(base)
    if output.exists():
        raise ValueError("derived population must be a new directory")
    shutil.copytree(base, output)
    manifest = json.loads((base / "population-manifest.v1.json").read_bytes())
    provenance = [json.loads(line) for line in (base / "record-provenance.jsonl").read_bytes().splitlines()]
    selected, removed = {}, []
    oa = []
    for line in (base / manifest["sources"]["openalex"]["path"]).read_bytes().splitlines():
        item = json.loads(line)
        venue = ((item.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        if CS_VENUE.search(venue):
            oa.append(item)
            selected[("openalex", item["id"])] = True
        else:
            removed.append({"source": "openalex", "nativeId": item["id"], "venue": venue, "reason": "outside-explicit-CS-venue-filter"})
    (output / manifest["sources"]["openalex"]["path"]).write_bytes(b"".join(encoded(item) + b"\n" for item in oa))
    orcids = {a["author"]["orcid"].rsplit("/", 1)[-1] for item in oa for a in item.get("authorships", []) if a.get("author", {}).get("orcid")}
    for line in (base / manifest["sources"]["crossref"]["path"]).read_bytes().splitlines():
        row = json.loads(line)["message"]
        selected[("crossref", canonical_doi(row["DOI"]))] = True
        orcids.update(a["ORCID"].rsplit("/", 1)[-1] for a in row.get("author", []) if a.get("ORCID"))
    profiles = []
    for line in (base / manifest["sources"]["orcid"]["path"]).read_bytes().splitlines():
        item = json.loads(line)
        native = item["orcid-identifier"]["path"]
        if native in orcids:
            profiles.append(item)
            selected[("orcid", native)] = True
        else:
            removed.append({"source": "orcid", "nativeId": native, "reason": "not-observed-in-CS-retained-work-authors"})
    (output / manifest["sources"]["orcid"]["path"]).write_bytes(b"".join(encoded(item) + b"\n" for item in profiles))
    provenance = [row for row in provenance if (row["source"], row["nativeId"]) in selected]
    (output / "record-provenance.jsonl").write_bytes(b"".join(encoded(row) + b"\n" for row in provenance))
    (output / "selection-exclusions.json").write_bytes(encoded(removed) + b"\n")
    manifest["derivedFromPopulationManifestSha256"] = digest((base / "population-manifest.v1.json").read_bytes())
    manifest["domainFilter"] = {"version": "cs-distributed-data-venue-v1", "venueRegex": CS_VENUE.pattern, "scriptSha256": digest(Path(__file__).read_bytes()), "excludedBySource": dict(collections.Counter(row["source"] for row in removed)), "usesLabelsOrPredictions": False}
    manifest["selectionVersion"] += "/cs-distributed-data-venue-v1"
    manifest["limitations"].append("The CS venue filter excludes unrecognized/missing venues conservatively, including some potentially relevant works. ORCID profiles are retained only when their ORCID occurs in retained work authors; public career records themselves are not rewritten or year-truncated.")
    for source, fact in manifest["sources"].items():
        path = output / fact["path"]
        fact["records"] = 0 if source == "dblp" else len(path.read_bytes().splitlines())
        fact.update(sha256=digest(path.read_bytes()), bytes=path.stat().st_size)
    manifest["files"] = {p.relative_to(output).as_posix(): {"sha256": digest(p.read_bytes()), "bytes": p.stat().st_size} for p in sorted(output.rglob("*")) if p.is_file() and p.name != "population-manifest.v1.json"}
    (output / "population-manifest.v1.json").write_bytes(encoded(manifest) + b"\n")
    return validate(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(derive(args.base.resolve(), args.output.resolve()), indent=2))

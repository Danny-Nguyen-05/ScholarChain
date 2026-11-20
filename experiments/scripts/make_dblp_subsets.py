#!/usr/bin/env python3
"""Build the three Experiment 15A input trees from the real Phase 6 DBLP slice (stdlib only; run with python3 -I).

Source (read only):  target/phase6-inputs/6fg-dblp/dblp.xml, the selected slice described by
                     datasets/phase6/dblp-slice-manifest.v1.json (10,577 inproceedings, dblp-2026-10-03).
Output (git-ignored): <output-root>/size-<P>/datasets/samples/{dblp,openalex,crossref,orcid}/...  (the Phase 4 layout that
                     run-bounded-pipeline.sh stages and HadoopPrepMain reads) plus <output-root>/size-<P>.subset.json.

Selection rule (deterministic, nested): per venue (key conf/<venue>/..., wdag counted as disc), keep the FIRST
ceil(n_venue * P / 100) records in the slice's own file order; records are written in the original file order. So the 25 percent
set is contained in the 50 percent set, which is contained in the 100 percent set, and the 100 percent file is byte-identical to
the Phase 6 slice (checked and recorded). This keeps the venue mix and the source-order bias of the slice; it is not a random
sample. The three other sources are the committed Phase 4 samples, copied unchanged and checked against
datasets/samples/SHA256SUMS; they are NOT scaled, so scaling is by DBLP publications only.

The same builder makes the size-L tree (P21): --source <L slice XML> --slice-manifest <L slice manifest> --sizes 100 --tree-label size-l
(experiments/scripts/build_l_input.py runs exactly that, then re-renders the manifests). --tree-label names the tree and its subset file
instead of size-<P> and needs exactly one size.

Nothing here touches the network or AWS. Existing output directories are refused, never overwritten.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SOURCE = os.path.join("target", "phase6-inputs", "6fg-dblp", "dblp.xml")
DEFAULT_SLICE_MANIFEST = os.path.join("datasets", "phase6", "dblp-slice-manifest.v1.json")
DEFAULT_OUTPUT = os.path.join("target", "experiment-inputs", "15a")
DEFAULT_SAMPLES = os.path.join("datasets", "samples")
SAMPLE_FILES = ("dblp/linked-records.xml", "openalex/works.jsonl", "crossref/works.jsonl", "orcid/records.jsonl")
RECORD = re.compile(r"<inproceedings\b.*?</inproceedings>", re.DOTALL)
KEY = re.compile(r'<inproceedings\b[^>]*\bkey="([^"]+)"')
AUTHOR = re.compile(r"<author\b[^>]*>(.*?)</author>", re.DOTALL)
YEAR = re.compile(r"<year>(\d{4})</year>")
VENUE_ALIASES = {"wdag": "disc"}
HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n'
TREE_LABEL = re.compile(r"^size-[a-z0-9]{1,8}$")
FOOTER = "</dblp>\n"


class Refused(Exception):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def venue_of(key):
    parts = key.split("/")
    venue = parts[1] if len(parts) > 2 and parts[0] == "conf" else "other"
    return VENUE_ALIASES.get(venue, venue)


def parse_records(text):
    records = []
    for match in RECORD.finditer(text):
        body = match.group(0)
        key = KEY.match(body)
        if not key:
            raise Refused("an inproceedings record has no key attribute")
        records.append((key.group(1), body))
    return records


def select(records, percent):
    """Indexes of the first ceil(n_venue * percent / 100) records of every venue (exact integer arithmetic)."""
    totals = {}
    for key, _ in records:
        venue = venue_of(key)
        totals[venue] = totals.get(venue, 0) + 1
    quota = {venue: -(-count * percent // 100) for venue, count in totals.items()}
    seen = {}
    chosen = []
    for index, (key, _) in enumerate(records):
        venue = venue_of(key)
        rank = seen.get(venue, 0)
        seen[venue] = rank + 1
        if rank < quota[venue]:
            chosen.append(index)
    return chosen


def describe(records, indexes):
    authorships = 0
    distinct = set()
    years = []
    venues = {}
    for index in indexes:
        key, body = records[index]
        authors = AUTHOR.findall(body)
        authorships += len(authors)
        distinct.update(authors)
        year = YEAR.search(body)
        if year:
            years.append(int(year.group(1)))
        venues[venue_of(key)] = venues.get(venue_of(key), 0) + 1
    return {
        "publications": len(indexes),
        "authorships": authorships,
        "distinct_exact_author_strings": len(distinct),
        "min_year": min(years) if years else None,
        "max_year": max(years) if years else None,
        "per_venue": dict(sorted(venues.items())),
    }


def verify_samples(samples_dir):
    sums = {}
    with open(os.path.join(samples_dir, "SHA256SUMS"), encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                digest, name = line.split(None, 1)
                sums[name.strip()] = digest
    out = {}
    for relative in SAMPLE_FILES:
        with open(os.path.join(samples_dir, relative), "rb") as handle:
            data = handle.read()
        expected = sums.get("samples/" + relative)
        if expected is None or sha256_bytes(data) != expected:
            raise Refused("committed sample %s does not match datasets/samples/SHA256SUMS" % relative)
        out[relative] = data
    return out


def write_new(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def build(args):
    root = REPO
    source = args.source if os.path.isabs(args.source) else os.path.join(root, args.source)
    manifest_path = args.slice_manifest if os.path.isabs(args.slice_manifest) else os.path.join(root, args.slice_manifest)
    samples = args.samples_dir if os.path.isabs(args.samples_dir) else os.path.join(root, args.samples_dir)
    out_root = args.output_root if os.path.isabs(args.output_root) else os.path.join(root, args.output_root)
    with open(manifest_path, encoding="utf-8") as handle:
        slice_manifest = json.load(handle)
    with open(source, "rb") as handle:
        raw = handle.read()
    if not args.skip_source_check:
        expected = slice_manifest["output"]["sha256"]
        if sha256_bytes(raw) != expected:
            raise Refused("source %s does not match the slice manifest sha256 (expected %s)" % (args.source, expected))
    text = raw.decode("utf-8")
    records = parse_records(text)
    declared = slice_manifest["selection"]["publicationCount"]
    if not args.skip_source_check and len(records) != declared:
        raise Refused("parsed %d records, the slice manifest declares %d" % (len(records), declared))
    sample_bytes = verify_samples(samples)
    percents = [int(p) for p in args.sizes.split(",")]
    label = getattr(args, "tree_label", None)
    if label is not None and (len(percents) != 1 or not TREE_LABEL.match(label)):
        raise Refused("--tree-label needs exactly one size and must match %s" % TREE_LABEL.pattern)
    names = {p: label or "size-%d" % p for p in percents}
    for p in percents:
        if not 1 <= p <= 100:
            raise Refused("size %d is not a percentage from 1 to 100" % p)
        if os.path.lexists(os.path.join(out_root, names[p])) or os.path.lexists(os.path.join(out_root, "%s.subset.json" % names[p])):
            raise Refused("%s already exists under %s: choose a new --output-root" % (names[p], args.output_root))
    results = []
    previous = set()
    for p in sorted(percents):
        indexes = select(records, p)
        if not previous <= set(indexes):
            raise Refused("selection is not nested at %d percent" % p)
        previous = set(indexes)
        dblp = (HEADER + "".join(records[i][1] + "\n" for i in indexes) + FOOTER).encode("utf-8")
        tree = os.path.join(out_root, names[p])
        files = {"dblp/linked-records.xml": dblp}
        files.update({name: data for name, data in sample_bytes.items() if name != "dblp/linked-records.xml"})
        for relative, data in files.items():
            write_new(os.path.join(tree, "datasets", "samples", relative), data)
        keys_sha = sha256_bytes("\n".join(sorted(records[i][0] for i in indexes)).encode("utf-8"))
        info = {
            "schema": "scholarchain.experiment-input-subset.v1",
            "size_percent": p,
            "tree_label": names[p],
            "source": {
                "path": args.source,
                "sha256": sha256_bytes(raw),
                "slice_manifest": args.slice_manifest,
                "slice_publication_count": len(records),
            },
            "rule": "first ceil(n_venue*P/100) records per venue in slice file order; records kept in file order; nested sets",
            "actual_fraction": round(len(indexes) / len(records), 6),
            "selected_keys_sha256_sorted_newline_joined": keys_sha,
            "counts": describe(records, indexes),
            "dblp_file_sha256": sha256_bytes(dblp),
            "dblp_file_bytes": len(dblp),
            "byte_identical_to_source": dblp == raw,
            "other_sources": "committed Phase 4 samples copied unchanged (not scaled)",
            "files": {"datasets/samples/" + name: {"sha256": sha256_bytes(data), "bytes": len(data)} for name, data in sorted(files.items())},
        }
        write_new(os.path.join(out_root, "%s.subset.json" % names[p]), (json.dumps(info, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        results.append(info)
    return results


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--slice-manifest", default=DEFAULT_SLICE_MANIFEST)
    parser.add_argument("--samples-dir", default=DEFAULT_SAMPLES)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT)
    parser.add_argument("--sizes", default="25,50,100", help="comma separated percentages (default 25,50,100)")
    parser.add_argument("--tree-label", help="name of the tree and subset file instead of size-<P> (one size only), e.g. size-l")
    parser.add_argument("--skip-source-check", action="store_true", help="tests only: skip the slice manifest sha256 and count check")
    args = parser.parse_args(argv)
    try:
        results = build(args)
    except (Refused, OSError, KeyError, ValueError) as error:
        print("SUBSET-REFUSED: %s" % error)
        return 1
    for info in results:
        c = info["counts"]
        print(
            "SUBSET %s size=%d%% publications=%d authorships=%d distinct_author_strings=%d dblp_bytes=%d identical_to_source=%s"
            % (info["tree_label"], info["size_percent"], c["publications"], c["authorships"], c["distinct_exact_author_strings"], info["dblp_file_bytes"], info["byte_identical_to_source"])
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

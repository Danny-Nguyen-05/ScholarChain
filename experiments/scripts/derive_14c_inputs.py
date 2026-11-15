#!/usr/bin/env python3
"""Derive the real 14C / 15B / 16B input files from a completed Phase 6 Spark export (stdlib only; run with python3 -I).

Reads ONLY the plain-CSV Neptune openCypher sidecar of the export (no Parquet reader is needed):
  <export-dir>/run-manifest.json
  <export-dir>/neptune-opencypher-csv/data/nodes/*.csv          (RESEARCHER nodes: id and display name)
  <export-dir>/neptune-opencypher-csv/data/graph-edges/*.csv    (AUTHORED edges: researcher -> work)
  <export-dir>/neptune-opencypher-csv/data/coauthor-edges/*.csv (COAUTHORED_WITH edges, one row per window)

Writes (refuses to overwrite unless --overwrite; every file is LF-terminated and byte-identical for the same input):
  include-ids.txt   one stable ID per line (researcher:...), sorted, at most 2000: every researcher the questions name
  real-query.json   {"question": ..., "output": {"includeScores": false}}  (the 14C real-data smoke body)
  questions.txt     one question per line: the 40 fixed questions for 15B (cycled) and 16B (once each)
  node-ids.txt      graph node IDs for loadgen.py --node-ids-file (researcher: and work: IDs, one per line)
  provenance.json   export run id, sha256 of every file read, the selection rule, counts and the sha256 of each output

Selection rule (no randomness; every tie is broken by the stable ID):
  degree(r)   = number of distinct coauthors of r in the 'all-years' window (distinct unordered pairs).
  eligible(r) = the display name is unique among ALL researcher nodes after trim + lowercase + whitespace collapse (so the
                runtime name resolver is not ambiguous), is 3..60 characters of ASCII letters, spaces, hyphens or apostrophes
                (no digits such as a DBLP homonym suffix, no quotes or accents), the ID is a researcher:<source>:<key> ID, and
                the degree lies in the band --degree-min..--degree-max (default 10..22). The band keeps the runtime artifact inside its
                caps (10,000 rows, 16 MiB): the artifact holds about 9.1 rows per unit of all-years degree of each included researcher,
                so a hub such as a degree-247 researcher alone is about 2,200 rows.
  pool        = eligible researchers sorted by (-degree, id), first --pool (default 80).
  direct      = pool[0], pool[step], pool[2*step], ... (step = pool // (direct + component), at least 1): the first --direct
                (default 14) names, then the next --component (default 8) names, taken from pool positions spread over the pool.
  path pairs  = --paths (default 10) pairs, half direct coauthor pairs, half two-hop pairs, no researcher in two pairs:
                coauthor pairs: eligible pairs joined in 'all-years' sorted by (-jointPublicationCount, id_a, id_b);
                two-hop pairs: for each pool researcher A in order, the first (by ID) eligible C that is a coauthor of a coauthor B
                of A, is not A and not a coauthor of A.  Researchers already used by another pair are skipped.
  global      = 8 fixed ranking questions that name no entity (distinct coauthors, since 2015, windows, team size, bridges, repeats).
  questions   = the four lists interleaved round-robin (direct, component, path, global); when the shorter lists run out the
                remaining direct questions follow. The count must equal --total (default 40) or the run is refused.
  budget      = the include list's total all-years degree must be at most --degree-budget (default 900, about 8,200 artifact rows,
                below the 10,000-row cap); the script refuses to write anything when it is exceeded.
  smoke       = real-query.json asks for the direct coauthors of the pool[0] researcher (highest degree).
  node ids    = the researchers named in the questions, then their coauthors (the endpoint nodes inside the artifact closure) by
                (-degree, id) up to --node-researchers (default 60), then --node-works (default 40) works authored by the
                researchers named in the questions (the works inside the closure), by work ID.

Exit codes: 0 ok, 1 refused (bad input, would overwrite, count mismatch), 2 usage.
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys

SCHEMA = "scholarchain.experiment-inputs-provenance.v1"
ALL_YEARS = "all-years"
NAME_OK = re.compile(r"^[A-Za-z][A-Za-z '\-]{1,58}[A-Za-z]$")
RESEARCHER_ID = re.compile(r"^researcher:[a-z0-9-]+:[^\s]{1,400}$")
FILE_ID = re.compile(r"^[^\s\x00-\x1f\x7f]{1,200}$")
GLOBAL_QUESTIONS = (
    "Which researchers have the most distinct coauthors?",
    "Which researchers have the most distinct coauthors since 2015?",
    "Which researchers have the most distinct coauthors in window 2020-2026?",
    "Which researchers have the most distinct coauthors in window through-2009?",
    "Which researchers have the largest team size?",
    "Which researchers are the strongest bridges?",
    "Which researchers are the strongest bridges since 2015?",
    "Show the strongest repeated collaborations",
)
DEFAULTS = {"direct": 14, "component": 8, "paths": 10, "pool": 80, "total": 40, "degree_min": 10, "degree_max": 22, "degree_budget": 900, "node_researchers": 60, "node_works": 40}
MAX_INCLUDE = 2000


class Refused(Exception):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm_name(raw):
    return " ".join(raw.strip().lower().split())


def csv_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            yield row


def list_csv(directory):
    files = sorted(glob.glob(os.path.join(glob.escape(directory), "*.csv")))
    if not files:
        raise Refused("no CSV part files in %s" % directory)
    return files


def load_export(export_dir):
    """Returns (run_id, researchers{id: name}, coauthor{(a,b): joint}, authored{researcher: [works]}, files_read[(relpath, sha)])."""
    export_dir = os.path.abspath(export_dir)
    manifest_path = os.path.join(export_dir, "run-manifest.json")
    if not os.path.isfile(manifest_path):
        raise Refused("%s has no run-manifest.json: not a Phase 6 Spark export" % os.path.basename(export_dir))
    with open(manifest_path, encoding="utf-8") as handle:
        run_id = json.load(handle).get("runId")
    if not isinstance(run_id, str) or not run_id.startswith("run:"):
        raise Refused("run-manifest.json holds no runId")
    data = os.path.join(export_dir, "neptune-opencypher-csv", "data")
    files_read = [("run-manifest.json", sha256_file(manifest_path))]
    researchers, coauthor, authored = {}, {}, {}
    maximum = 2 ** 31 - 1
    csv.field_size_limit(maximum)
    for part in list_csv(os.path.join(data, "nodes")):
        files_read.append((os.path.relpath(part, export_dir), sha256_file(part)))
        for row in csv_rows(part):
            if row[":LABEL"] == "RESEARCHER":
                researchers[row[":ID"]] = row["label:String"]
    for part in list_csv(os.path.join(data, "graph-edges")):
        files_read.append((os.path.relpath(part, export_dir), sha256_file(part)))
        for row in csv_rows(part):
            if row[":TYPE"] == "AUTHORED":
                authored.setdefault(row[":START_ID"], set()).add(row[":END_ID"])
    for part in list_csv(os.path.join(data, "coauthor-edges")):
        files_read.append((os.path.relpath(part, export_dir), sha256_file(part)))
        for row in csv_rows(part):
            if row["windowId:String"] != ALL_YEARS:
                continue
            a, b = sorted((row[":START_ID"], row[":END_ID"]))
            if a == b:
                continue
            joint = int(row["jointPublicationCount:Long"] or 0)
            coauthor[(a, b)] = max(joint, coauthor.get((a, b), 0))
    if not researchers or not coauthor:
        raise Refused("the export holds no researcher nodes or no all-years coauthor edges")
    files_read.sort()
    return run_id, researchers, coauthor, authored, files_read


def neighbours_of(coauthor, researcher):
    return [b if a == researcher else a for (a, b) in coauthor if researcher in (a, b)]


def select(researchers, coauthor, authored, cfg):
    neighbours = {}
    for (a, b) in coauthor:
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    degree = {r: len(neighbours.get(r, ())) for r in researchers}
    name_count = {}
    for name in researchers.values():
        name_count[norm_name(name)] = name_count.get(norm_name(name), 0) + 1
    eligible = {r for r, name in researchers.items()
                if RESEARCHER_ID.match(r) and FILE_ID.match(r) and NAME_OK.match(name.strip())
                and name_count[norm_name(name)] == 1 and name == name.strip() and "  " not in name
                and cfg["degree_min"] <= degree[r] <= cfg["degree_max"]}
    pool = sorted(eligible, key=lambda r: (-degree[r], r))[:cfg["pool"]]
    named = cfg["direct"] + cfg["component"]
    if named > len(pool):
        raise Refused("only %d eligible researchers in the pool, %d needed" % (len(pool), named))
    step = max(1, len(pool) // max(named, 1))
    spread = [pool[i * step] for i in range(named)]
    direct, component = spread[:cfg["direct"]], spread[cfg["direct"]:]
    used = set()
    pairs = []
    # coauthor pairs: strongest joint publication counts first
    for (a, b), joint in sorted(coauthor.items(), key=lambda kv: (-kv[1], kv[0])):
        if len(pairs) >= cfg["paths"] // 2:
            break
        if a in eligible and b in eligible and a not in used and b not in used:
            pairs.append((a, b, "direct"))
            used.update((a, b))
    # two-hop pairs, walking the pool in order
    for start in pool:
        if len(pairs) >= cfg["paths"]:
            break
        if start in used:
            continue
        found = None
        for mid in sorted(neighbours.get(start, ())):
            for end in sorted(neighbours.get(mid, ())):
                if end != start and end in eligible and end not in used and end not in neighbours[start]:
                    found = end
                    break
            if found:
                break
        if found:
            pairs.append((start, found, "two-hop"))
            used.update((start, found))
    if len(pairs) != cfg["paths"]:
        raise Refused("found %d of %d path pairs" % (len(pairs), cfg["paths"]))
    return degree, eligible, pool, direct, component, pairs


def build(researchers, coauthor, authored, cfg):
    degree, eligible, pool, direct, component, pairs = select(researchers, coauthor, authored, cfg)
    name = lambda r: researchers[r].strip()
    q_direct = ['Who are the direct coauthors of "%s"?' % name(r) for r in direct]
    q_component = ['What is the component of "%s"?' % name(r) for r in component]
    q_path = ['What is the shortest coauthor path between "%s" and "%s"?' % (name(a), name(b)) for a, b, _ in pairs]
    q_global = list(GLOBAL_QUESTIONS)
    lists = [q_direct, q_component, q_path, q_global]
    questions = []
    for index in range(max(len(x) for x in lists)):
        for items in lists:
            if index < len(items):
                questions.append(items[index])
    if len(questions) != cfg["total"]:
        raise Refused("the selection gives %d questions, --total says %d" % (len(questions), cfg["total"]))
    if len(set(questions)) != len(questions):
        raise Refused("duplicate questions")
    named_ids = set(direct) | set(component) | {x for a, b, _ in pairs for x in (a, b)}
    include = sorted(named_ids | {pool[0]})
    total_degree = sum(degree[r] for r in include)
    if total_degree > cfg["degree_budget"]:
        raise Refused("the include list's total all-years degree is %d, above the --degree-budget %d (about 9.1 artifact rows per degree; the artifact cap is 10,000 rows)" % (total_degree, cfg["degree_budget"]))
    if len(include) > MAX_INCLUDE:
        raise Refused("include list would hold %d IDs (maximum %d)" % (len(include), MAX_INCLUDE))
    real_query = {"question": 'Who are the direct coauthors of "%s"?' % name(pool[0]), "output": {"includeScores": False}}
    base = sorted(named_ids | {pool[0]})
    closure = set()
    for r in base:
        closure.update(n for n in neighbours_of(coauthor, r) if n in researchers and FILE_ID.match(n))
    extras = sorted(closure - set(base), key=lambda x: (-degree[x], x))
    node_researchers = sorted(base + extras[:max(0, cfg["node_researchers"] - len(base))])
    works = sorted({w for r in base for w in authored.get(r, ()) if FILE_ID.match(w)})
    node_ids = node_researchers + works[:cfg["node_works"]]
    rule = {"degree": "distinct all-years coauthors", "eligible": "unique normalized name, ASCII letters/space/hyphen/apostrophe, 3..60 chars, degree in the band",
            "degree_min": cfg["degree_min"], "degree_max": cfg["degree_max"], "degree_budget": cfg["degree_budget"],
            "pool": cfg["pool"], "direct": cfg["direct"], "component": cfg["component"], "paths": cfg["paths"],
            "global": len(q_global), "total": cfg["total"], "node_researchers": cfg["node_researchers"], "node_works": cfg["node_works"]}
    counts = {"researchers": len(researchers), "eligible": len(eligible), "all_years_coauthor_pairs": len(coauthor), "pool": len(pool),
              "questions": len(questions), "include_ids": len(include), "include_total_degree": total_degree, "node_ids": len(node_ids)}
    outputs = {
        "include-ids.txt": "".join(x + "\n" for x in include),
        "real-query.json": json.dumps(real_query, separators=(",", ":"), ensure_ascii=True) + "\n",
        "questions.txt": "".join(q + "\n" for q in questions),
        "node-ids.txt": "".join(x + "\n" for x in node_ids),
    }
    return outputs, rule, counts


def provenance(run_id, files_read, rule, counts, outputs):
    listing = "".join("%s  %s\n" % (sha, rel) for rel, sha in files_read)
    return json.dumps({
        "schema": SCHEMA,
        "tool": "experiments/scripts/derive_14c_inputs.py",
        "source": {"run_id": run_id, "format": "Phase 6 Spark export, neptune-opencypher-csv sidecar (plain CSV)",
                   "files_read": len(files_read), "files_read_listing_sha256": sha256_text(listing), "files_read_sha256": dict(files_read)},
        "rule": rule,
        "counts": counts,
        "outputs": {name: {"lines": text.count("\n"), "sha256": sha256_text(text)} for name, text in sorted(outputs.items())},
        "note": "IDs, DBLP author names and fixed question text only; DBLP is public (CC0). No credential, account or host value.",
    }, indent=2, sort_keys=True) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export-dir", required=True, help="completed Phase 6 Spark export run directory (read only)")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    for key, value in DEFAULTS.items():
        parser.add_argument("--" + key.replace("_", "-"), type=int, default=value)
    args = parser.parse_args(argv)
    cfg = {key: getattr(args, key) for key in DEFAULTS}
    if min(cfg.values()) < 0 or cfg["pool"] < 1 or cfg["paths"] < 2 or cfg["paths"] % 2:
        print("DERIVE-REFUSED: counts must be non-negative, --paths even and at least 2, --pool at least 1")
        return 1
    try:
        run_id, researchers, coauthor, authored, files_read = load_export(args.export_dir)
        outputs, rule, counts = build(researchers, coauthor, authored, cfg)
        outputs["provenance.json"] = provenance(run_id, files_read, rule, counts, outputs)
        out_dir = os.path.abspath(args.out_dir)
        if not args.overwrite:
            for name in outputs:
                if os.path.lexists(os.path.join(out_dir, name)):
                    raise Refused("%s exists (use --overwrite)" % name)
        os.makedirs(out_dir, exist_ok=True)
        for name, text in sorted(outputs.items()):
            with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            print("WROTE %s lines=%d sha256=%s" % (name, text.count("\n"), sha256_text(text)))
    except Refused as error:
        print("DERIVE-REFUSED: %s" % error)
        return 1
    except (OSError, ValueError, KeyError) as error:
        print("DERIVE-REFUSED: %s: %s" % (type(error).__name__, error))
        return 1
    print("RESULT: OK run=%s questions=%d include_ids=%d node_ids=%d" % (run_id, counts["questions"], counts["include_ids"], counts["node_ids"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

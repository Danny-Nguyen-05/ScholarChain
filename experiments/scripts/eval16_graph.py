#!/usr/bin/env python3
"""Phase 16, group 2 (graph correctness): integrity, duplicate, orphan, support and provenance checks of a completed Phase 6 Spark export
(stdlib only; python3 -I; offline, read-only on the export; streams the CSV parts).

  python3 -I experiments/scripts/eval16_graph.py --export-dir <spark export dir> [--out-dir experiments/results/phase16/graph] [--sample 50]

Evidence read (Python here has no Parquet reader, so the plain-CSV Neptune openCypher sidecar of the export is the source, the same files the Q12 scripts read):
  <export>/neptune-opencypher-csv/data/nodes/*.csv          nodes of every label
  <export>/neptune-opencypher-csv/data/graph-edges/*.csv    AUTHORED, RESOLVES_TO, PUBLISHED_IN, HAS_TOPIC, AFFILIATED_WITH edges
  <export>/neptune-opencypher-csv/data/coauthor-edges/*.csv COAUTHORED_WITH edges, one row per stored window, with the representative support works
  <export>/run-manifest.json, counters.json, load-manifests/neptune-opencypher-csv.json   run identity and the Spark job's own counters (cross-check only)
The sha256 of every file read is written to the output so the result is tied to the run. The Parquet support table (edges/type=coauthored_with_support) is NOT
read: the check "support" below uses the representative work ids stored on each coauthor edge row; the Parquet row count is only compared with the load manifest.
Checks (each a count over a denominator, with a Wilson 95% interval where it is a proportion):
  referential integrity   every edge endpoint resolves to a node of the right label; every representative support work resolves to a WORK node and was authored by both
                          endpoints (an AUTHORED edge exists from each endpoint to the work)
  duplicates              duplicate node ids, duplicate edge ids, duplicate (type,start,end) edges, duplicate coauthor (pair,window) rows, self-loops
  orphans                 nodes with no incident edge of the kind their label requires
  coauthor support        edges with at least one support work, all support works resolving, both endpoints authoring each; all-years joint counts recounted from AUTHORED
  provenance audit        a seeded sample of coauthor edges traced edge -> support works -> AUTHORED edges -> endpoint nodes -> RESOLVES_TO mentions, plus the run id
Exit codes: 0 done, 1 refused (not a Phase 6 export or unreadable input), 2 usage.
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHEMA = "scholarchain.eval16-graph.v1"
Z = 1.959963984540054
SAMPLE_SEED = "eval16-graph-v1"
EDGE_ENDPOINT_LABELS = {"AUTHORED": ("RESEARCHER", "WORK"), "RESOLVES_TO": ("AUTHOR_MENTION", "RESEARCHER"), "PUBLISHED_IN": ("WORK", "VENUE"),
                        "HAS_TOPIC": ("WORK", "TOPIC"), "AFFILIATED_WITH": ("RESEARCHER", "INSTITUTION")}
SUPPORT_CAP = 5   # q12_graph.py: representative work ids hold at most 5 works (all joint works when joint <= 5); verified here, not assumed
SPARK_TEST_DIR = "modules/spark/src/test/scala"
LAST_CHECK_FILE = "docs/agent-runs/phase-15/test-report.md"


class Refused(Exception):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson(k, n, z=Z):
    """Wilson score interval of k successes in n trials as (low, high); None when n is 0."""
    if n <= 0:
        return None
    p = k / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half = z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / denominator
    # exact at the boundaries: the lower limit is 0 when k = 0 and the upper limit is 1 when k = n (avoids a 1e-16 rounding artefact)
    return (0.0 if k == 0 else max(0.0, centre - half), 1.0 if k == n else min(1.0, centre + half))


def proportion(k, n):
    interval = wilson(k, n)
    return {"k": k, "n": n, "value": (k / n) if n else None, "wilson95": [round(interval[0], 6), round(interval[1], 6)] if interval else None}


def _parts(directory):
    files = sorted(glob.glob(os.path.join(glob.escape(directory), "*.csv")))
    if not files:
        raise Refused("no CSV part files in %s" % directory)
    return files


def _rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            yield row


# loading -----------------------------------------------------------------------------------------------------------------------------
def load_export(export_dir):
    """Stream the sidecar into compact in-memory structures. Returns (model, files) where files is [(relative path, bytes, sha256)]."""
    export_dir = os.path.abspath(export_dir)
    manifest_path = os.path.join(export_dir, "run-manifest.json")
    if not os.path.isfile(manifest_path):
        raise Refused("%s has no run-manifest.json: not a Phase 6 Spark export" % os.path.basename(export_dir))
    with open(manifest_path, encoding="utf-8") as handle:
        run_id = json.load(handle).get("runId")
    if not isinstance(run_id, str) or not run_id.startswith("run:"):
        raise Refused("run-manifest.json holds no runId")
    data = os.path.join(export_dir, "neptune-opencypher-csv", "data")
    csv.field_size_limit(2 ** 31 - 1)
    files = []

    def note(path):
        files.append((os.path.relpath(path, export_dir), os.path.getsize(path), sha256_file(path)))

    for extra in ("run-manifest.json", "counters.json", os.path.join("load-manifests", "neptune-opencypher-csv.json")):
        path = os.path.join(export_dir, extra)
        if os.path.isfile(path):
            note(path)
    node_label, node_rows = {}, []
    for part in _parts(os.path.join(data, "nodes")):
        note(part)
        for row in _rows(part):
            node_rows.append((row[":ID"], row[":LABEL"]))
    for node_id, label in node_rows:
        node_label[node_id] = label
    needle = '"runId":"%s"' % run_id
    graph_edges, run_id_ok_graph = [], 0
    for part in _parts(os.path.join(data, "graph-edges")):
        note(part)
        for row in _rows(part):
            graph_edges.append((row[":ID"], row[":START_ID"], row[":END_ID"], row[":TYPE"]))
            run_id_ok_graph += needle in row.get("contextJson:String", "")
    coauthor, run_id_ok_coauthor = [], 0
    for part in _parts(os.path.join(data, "coauthor-edges")):
        note(part)
        for row in _rows(part):
            try:
                support = json.loads(row.get("representativeWorkIdsJson:String") or "[]")
            except ValueError:
                support = None
            support = tuple(sorted(w for w in support if isinstance(w, str))) if isinstance(support, list) else None
            coauthor.append((row[":ID"], row[":START_ID"], row[":END_ID"], row["windowId:String"], int(row["jointPublicationCount:Long"] or 0), support,
                             row.get("evidenceEdgeId:String", "")))
            run_id_ok_coauthor += needle in row.get("contextJson:String", "")
    files.sort()
    model = {"run_id": run_id, "node_rows": node_rows, "node_label": node_label, "graph_edges": graph_edges, "coauthor": coauthor,
             "run_id_in_context": {"graph_edges": run_id_ok_graph, "coauthor_edges": run_id_ok_coauthor}}
    return model, files


# pure checks (unit-tested on small fixtures) ----------------------------------------------------------------------------------------
def duplicates(model):
    node_ids = [n for n, _ in model["node_rows"]]
    edge_ids = [e[0] for e in model["graph_edges"]]
    triples = [(e[3], e[1], e[2]) for e in model["graph_edges"]]
    co_ids = [c[0] for c in model["coauthor"]]
    co_pairs = [(min(c[1], c[2]), max(c[1], c[2]), c[3]) for c in model["coauthor"]]
    loops = sum(1 for c in model["coauthor"] if c[1] == c[2])

    def dup(items):
        return len(items) - len(set(items))
    return {"node_ids": proportion(dup(node_ids), len(node_ids)), "graph_edge_ids": proportion(dup(edge_ids), len(edge_ids)),
            "graph_edge_type_start_end": proportion(dup(triples), len(triples)), "coauthor_edge_ids": proportion(dup(co_ids), len(co_ids)),
            "coauthor_pair_window": proportion(dup(co_pairs), len(co_pairs)), "coauthor_self_loops": proportion(loops, len(co_pairs)),
            "note": "a duplicate is a row beyond the first with the same key: count = rows - distinct keys"}


def referential_integrity(model):
    labels = model["node_label"]
    dangling, wrong_label = {}, {}
    totals = {}
    for edge_id, start, end, kind in model["graph_edges"]:
        totals[kind] = totals.get(kind, 0) + 1
        missing = (start not in labels) + (end not in labels)
        dangling[kind] = dangling.get(kind, 0) + (1 if missing else 0)
        want = EDGE_ENDPOINT_LABELS.get(kind)
        if want and start in labels and end in labels and (labels[start], labels[end]) != want:
            wrong_label[kind] = wrong_label.get(kind, 0) + 1
    co_dangling = sum(1 for c in model["coauthor"] if c[1] not in labels or c[2] not in labels)
    co_wrong = sum(1 for c in model["coauthor"] if c[1] in labels and c[2] in labels and (labels[c[1]], labels[c[2]]) != ("RESEARCHER", "RESEARCHER"))
    by_kind = {kind: {"edges": totals[kind], "with_unresolved_endpoint": proportion(dangling.get(kind, 0), totals[kind]),
                      "with_wrong_endpoint_label": proportion(wrong_label.get(kind, 0), totals[kind]),
                      "expected_labels": list(EDGE_ENDPOINT_LABELS.get(kind, ())) or None} for kind in sorted(totals)}
    return {"graph_edges_by_type": by_kind,
            "graph_edges_total_with_unresolved_endpoint": proportion(sum(dangling.values()), len(model["graph_edges"])),
            "coauthor_edges_with_unresolved_endpoint": proportion(co_dangling, len(model["coauthor"])),
            "coauthor_edges_with_non_researcher_endpoint": proportion(co_wrong, len(model["coauthor"]))}


def authorship(model):
    """(authored_by {researcher: set(work)}, mentions_of {researcher: count of RESOLVES_TO mentions}, venues_per_work {work: count})."""
    authored_by, mentions_of, venues = {}, {}, {}
    for edge_id, start, end, kind in model["graph_edges"]:
        if kind == "AUTHORED":
            authored_by.setdefault(start, set()).add(end)
        elif kind == "RESOLVES_TO":
            mentions_of[end] = mentions_of.get(end, 0) + 1
        elif kind == "PUBLISHED_IN":
            venues[start] = venues.get(start, 0) + 1
    return authored_by, mentions_of, venues


def orphans(model):
    labels = model["node_label"]
    touched = {}
    for edge_id, start, end, kind in model["graph_edges"]:
        touched.setdefault(start, set()).add(("out", kind))
        touched.setdefault(end, set()).add(("in", kind))
    co_nodes = set()
    for c in model["coauthor"]:
        co_nodes.add(c[1])
        co_nodes.add(c[2])
    totals, orphan = {}, {}

    def count(label, is_orphan):
        totals[label] = totals.get(label, 0) + 1
        orphan[label] = orphan.get(label, 0) + (1 if is_orphan else 0)
    for node_id, label in model["node_rows"]:
        kinds = touched.get(node_id, set())
        if label == "AUTHOR_MENTION":
            count("AUTHOR_MENTION (no RESOLVES_TO edge)", ("out", "RESOLVES_TO") not in kinds)
        elif label == "RESEARCHER":
            count("RESEARCHER (no AUTHORED edge)", ("out", "AUTHORED") not in kinds)
            count("RESEARCHER (no coauthor edge in any window)", node_id not in co_nodes)
            count("RESEARCHER (no RESOLVES_TO mention)", ("in", "RESOLVES_TO") not in kinds)
        elif label == "WORK":
            count("WORK (no AUTHORED edge)", ("in", "AUTHORED") not in kinds)
            count("WORK (no PUBLISHED_IN edge)", ("out", "PUBLISHED_IN") not in kinds)
        else:
            count("%s (no incident edge)" % label, not kinds)
    return {name: proportion(orphan[name], totals[name]) for name in sorted(totals)}


def support_checks(model, authored_by):
    """Per-row support checks, summarised for all rows and for the all-years rows."""
    labels = model["node_label"]
    all_years = {}
    for c in model["coauthor"]:
        if c[3] == "all-years":
            all_years[(min(c[1], c[2]), max(c[1], c[2]))] = c[4]

    def summarize(rows):
        n = len(rows)
        out = {"edges": n, "with_support_work": 0, "joint_at_least_one": 0, "all_support_works_resolve": 0, "all_support_works_authored_by_both": 0,
               "support_count_equals_min_joint_cap": 0, "fully_supported": 0, "window_pair_in_all_years": 0, "window_joint_le_all_years": 0}
        for c in rows:
            support, joint = c[5], c[4]
            has = bool(support)
            resolves = has and all(labels.get(w) == "WORK" for w in support)
            both = has and all(w in authored_by.get(c[1], ()) and w in authored_by.get(c[2], ()) for w in support)
            out["with_support_work"] += has
            out["joint_at_least_one"] += joint >= 1
            out["all_support_works_resolve"] += resolves
            out["all_support_works_authored_by_both"] += both
            out["support_count_equals_min_joint_cap"] += has and len(support) == min(joint, SUPPORT_CAP)
            out["fully_supported"] += has and resolves and both and joint >= 1
            key = (min(c[1], c[2]), max(c[1], c[2]))
            out["window_pair_in_all_years"] += key in all_years
            out["window_joint_le_all_years"] += key in all_years and joint <= all_years[key]
        return {k: (v if k == "edges" else proportion(v, n)) for k, v in out.items()}

    rows_all = model["coauthor"]
    rows_ay = [c for c in rows_all if c[3] == "all-years"]
    recount_ok = recount_n = 0
    mismatches = []
    for c in sorted(rows_ay, key=lambda r: r[0]):
        recount_n += 1
        shared = len(authored_by.get(c[1], set()) & authored_by.get(c[2], set()))
        if shared == c[4]:
            recount_ok += 1
        elif len(mismatches) < 10:
            mismatches.append({"edge_id": c[0], "stored_joint": c[4], "recount_from_authored": shared})
    by_window = {}
    for window in sorted({c[3] for c in rows_all}):
        by_window[window] = summarize([c for c in rows_all if c[3] == window])
    return {"all_windows": summarize(rows_all), "all_years": summarize(rows_ay), "by_window": by_window,
            "all_years_joint_count_recount": {"definition": "stored jointPublicationCount equals the number of distinct works authored (AUTHORED edges) by both endpoints",
                                              "matching": proportion(recount_ok, recount_n), "first_mismatches": mismatches}}


def provenance_audit(model, authored_by, mentions_of, sample_size, seed=SAMPLE_SEED):
    """Seeded sample of coauthor rows traced edge -> support works -> authorship -> endpoints -> mentions, and the run id."""
    labels = model["node_label"]
    rows = sorted(model["coauthor"], key=lambda r: r[0])
    rng = random.Random(seed)
    picks = sorted(rng.sample(range(len(rows)), min(sample_size, len(rows))))
    ay = {}
    for c in rows:
        if c[3] == "all-years":
            ay[(min(c[1], c[2]), max(c[1], c[2]))] = c[4]
    traces, resolved = [], 0
    for index in picks:
        c = rows[index]
        support = c[5] or ()
        steps = {
            "endpoints_are_researcher_nodes": labels.get(c[1]) == "RESEARCHER" and labels.get(c[2]) == "RESEARCHER",
            "has_support_works": bool(support),
            "support_works_are_work_nodes": bool(support) and all(labels.get(w) == "WORK" for w in support),
            "each_endpoint_authored_each_support_work": bool(support) and all(w in authored_by.get(c[1], ()) and w in authored_by.get(c[2], ()) for w in support),
            "each_endpoint_has_resolving_mention": mentions_of.get(c[1], 0) >= 1 and mentions_of.get(c[2], 0) >= 1,
            "pair_present_in_all_years_with_joint_ge_window": (min(c[1], c[2]), max(c[1], c[2])) in ay and ay[(min(c[1], c[2]), max(c[1], c[2]))] >= c[4],
        }
        ok = all(steps.values())
        resolved += ok
        traces.append({"edge_id": c[0], "window": c[3], "joint": c[4], "support_works": list(support), "steps": steps, "fully_resolves": ok})
    step_names = sorted(traces[0]["steps"]) if traces else []
    return {"seed": seed, "sample_size": len(traces), "population": len(rows), "fully_resolves": proportion(resolved, len(traces)),
            "by_step": {s: proportion(sum(1 for t in traces if t["steps"][s]), len(traces)) for s in step_names},
            "windows_in_sample": {w: sum(1 for t in traces if t["window"] == w) for w in sorted({t["window"] for t in traces})}, "traces": traces}


# context: the Spark job's own counters, load manifest and known-graph tests -------------------------------------------------------------
def spark_counters(export_dir):
    names = ("missingGraphEndpoints", "acceptedWorkLinksMissingEndpoint", "acceptedResearcherLinksMissingEndpoint", "graphEdgesMissingEvidenceWorkDropped", "pairCountMismatches",
             "selfPairsDropped", "missingCommunityMembership", "unresolvedMentions", "canonicalResearchers", "canonicalWorks", "allYearsEdges")
    path = os.path.join(export_dir, "counters.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        counters = json.load(handle)
    return {c["name"]: c["value"] for c in counters if c.get("name") in names}


def load_manifest_rows(export_dir):
    path = os.path.join(export_dir, "load-manifests", "neptune-opencypher-csv.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    return {"datasets": {d["path"].rsplit("/", 1)[-1]: int(d["rowCount"]) for d in manifest.get("datasets", [])},
            "source_tables": {t["path"]: int(t["rowCount"]) for t in manifest.get("sourceTables", [])}}


def manifest_cross_check(model, rows):
    """The CSV row counts against the Spark load manifest's row counts, and the support-table row count against the support works stored on the coauthor rows."""
    if not rows:
        return None
    counted = {"nodes": len(model["node_rows"]), "graph-edges": len(model["graph_edges"]), "coauthor-edges": len(model["coauthor"])}
    out = [{"dataset": k, "csv_rows": v, "load_manifest_rows": rows["datasets"].get(k), "agrees": rows["datasets"].get(k) == v} for k, v in sorted(counted.items())]
    stored = sum(len(c[5] or ()) for c in model["coauthor"])
    joint_sum = sum(c[4] for c in model["coauthor"])
    capped_sum = sum(min(c[4], SUPPORT_CAP) for c in model["coauthor"])
    table = rows["source_tables"].get("edges/type=coauthored_with_support")
    return {"row_counts": out, "support_table_rows_in_load_manifest": table, "sum_of_joint_publication_counts": joint_sum,
            "support_table_rows_equal_sum_of_joint_counts": table == joint_sum,
            "support_work_ids_stored_on_coauthor_rows": stored, "sum_of_min_joint_and_cap": capped_sum, "stored_pairs_equal_sum_of_min_joint_and_cap": stored == capped_sum,
            "note": "the Parquet support table was not read; two consistency checks: (a) its load-manifest row count equals the sum of jointPublicationCount over the CSV coauthor rows "
                    "(one support row per joint publication), and (b) the (edge, support work) pairs stored on the CSV rows equal the sum of min(joint, %d) because the CSV keeps at most %d "
                    "representative works per edge. Check (b) is a consistency check of the cap, not a comparison with the Parquet table." % (SUPPORT_CAP, SUPPORT_CAP)}


SMALL_GRAPH = re.compile(r"\bG1\b|chain|triangle|two-person|nine |synthetic|BFS|coreness|three-node", re.I)
TEST_NAME = re.compile(r'^\s*test\("((?:[^"\\]|\\.)*)"\)', re.M)


def spark_known_graph_tests(root):
    """List (do not run) the Spark test names, by suite. Returns None when the test directory is missing."""
    base = os.path.join(root, SPARK_TEST_DIR)
    if not os.path.isdir(base):
        return None
    suites = []
    for path in sorted(glob.glob(os.path.join(glob.escape(base), "**", "*.scala"), recursive=True)):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        names = [m.group(1).replace('\\"', '"') for m in TEST_NAME.finditer(text)]
        if names:
            suites.append({"suite": os.path.basename(path)[:-len(".scala")], "path": os.path.relpath(path, root), "sha256": sha256_file(path), "tests": names})
    total = sum(len(s["tests"]) for s in suites)
    return {"directory": SPARK_TEST_DIR, "suite_count": len(suites), "test_count": total, "suites": suites,
            "note": "listed from source with a regular expression for AnyFunSuite test(\"...\") calls; helper-generated or nested tests would be missed; the tests are NOT run here"}


def last_full_check(root):
    path = os.path.join(root, LAST_CHECK_FILE)
    if not os.path.isfile(path):
        return None
    found = None
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if "scripts/check.sh" in line and "RESULT: PASS" in line:
                found = (number, line.strip())
    if not found:
        return None
    m = re.search(r"worktree of ([0-9a-f]{7,40})( plus [^,;.]*)?", found[1])
    tree = ("commit %s%s (a detached worktree), per the quoted line" % (m.group(1), m.group(2) or "")) if m else "the tree named in the quoted line"
    return {"file": LAST_CHECK_FILE, "file_sha256": sha256_file(path), "line": found[0], "tree": tree, "text": found[1][:900],
            "note": "this is the coordinator's recorded result in the Phase 15 test report, quoted, not a run made by this script; the sbt gate of that check runs the Spark suites above"}


# output --------------------------------------------------------------------------------------------------------------------------
def fmt(p):
    if p["value"] is None:
        return "n/a (n=0)"
    low, high = p["wilson95"]
    return "%.4f%% (%d/%d; Wilson 95%% %.4f-%.4f%%)" % (100 * p["value"], p["k"], p["n"], 100 * low, 100 * high)


def markdown(doc):
    L = ["# Phase 16 group 2: graph correctness (Spark export %s)" % doc["export"]["run_id"], "",
         "Generated by `experiments/scripts/eval16_graph.py`; do not edit by hand. Measured facts first, then threats and gaps, then interpretation.", "",
         "## Evidence", "", "The export directory is outside git (`target/`); the table lists every file read with its size and sha256, so the result is tied to the run.", "",
         "Run id `%s`; %d files read; listing sha256 `%s`." % (doc["export"]["run_id"], len(doc["export"]["files"]), doc["export"]["files_listing_sha256"]), "",
         "| file | bytes | sha256 |", "|---|---|---|"]
    for name, size, digest in doc["export"]["files"]:
        L.append("| `%s` | %d | `%s` |" % (name, size, digest))
    L += ["", "Node rows by label: " + ", ".join("%s %d" % (k, v) for k, v in sorted(doc["counts"]["nodes_by_label"].items())) + ".",
          "Graph edge rows by type: " + ", ".join("%s %d" % (k, v) for k, v in sorted(doc["counts"]["graph_edges_by_type"].items())) + ".",
          "Coauthor edge rows by window: " + ", ".join("%s %d" % (k, v) for k, v in sorted(doc["counts"]["coauthor_edges_by_window"].items())) + ".", "",
          "## Measured: referential integrity", "", "| edge type | rows | unresolved endpoint | wrong endpoint label |", "|---|---|---|---|"]
    ri = doc["referential_integrity"]
    for kind, row in ri["graph_edges_by_type"].items():
        L.append("| %s | %d | %s | %s |" % (kind, row["edges"], fmt(row["with_unresolved_endpoint"]), fmt(row["with_wrong_endpoint_label"])))
    L += ["", "- all graph edges with an unresolved endpoint: %s" % fmt(ri["graph_edges_total_with_unresolved_endpoint"]),
          "- coauthor edges with an unresolved endpoint: %s" % fmt(ri["coauthor_edges_with_unresolved_endpoint"]),
          "- coauthor edges with a non-RESEARCHER endpoint: %s" % fmt(ri["coauthor_edges_with_non_researcher_endpoint"]), "",
          "## Measured: duplicates", ""]
    for key, value in doc["duplicates"].items():
        if key != "note":
            L.append("- %s: %s" % (key, fmt(value)))
    L += ["", "(%s)" % doc["duplicates"]["note"], "", "Works with more than one PUBLISHED_IN edge: %d (of %d works with at least one)." % (
        doc["counts"]["works_with_multiple_venues"], doc["counts"]["works_with_venue"]), "", "## Measured: orphan nodes", "", "| node class | orphans / nodes |", "|---|---|"]
    for name, p in doc["orphans"].items():
        L.append("| %s | %s |" % (name, fmt(p)))
    L += ["", "## Measured: coauthor-edge support", "", "A coauthor edge row is *fully supported* when it names at least one support work, every named work is a WORK node, both endpoints "
          "have an AUTHORED edge to every named work, and its joint count is at least 1.", "", "| rows | edges | with a support work | all works resolve | authored by both endpoints | support count = min(joint, 5) | fully supported | window pair in all-years | window joint <= all-years joint |",
          "|---|---|---|---|---|---|---|---|---|"]
    s = doc["support"]
    for label, row in [("all windows", s["all_windows"]), ("all-years", s["all_years"])] + [("window " + w, r) for w, r in s["by_window"].items()]:
        L.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (label, row["edges"], fmt(row["with_support_work"]), fmt(row["all_support_works_resolve"]), fmt(row["all_support_works_authored_by_both"]),
                                                                 fmt(row["support_count_equals_min_joint_cap"]), fmt(row["fully_supported"]), fmt(row["window_pair_in_all_years"]),
                                                                 fmt(row["window_joint_le_all_years"])))
    rc = s["all_years_joint_count_recount"]
    L += ["", "All-years joint-count recount (%s): %s" % (rc["definition"], fmt(rc["matching"])), ""]
    if rc["first_mismatches"]:
        L += ["First mismatches: " + "; ".join("%s stored %d recount %d" % (m["edge_id"], m["stored_joint"], m["recount_from_authored"]) for m in rc["first_mismatches"]), ""]
    a = doc["provenance_audit"]
    L += ["## Measured: sampled provenance audit", "", "Seed `%s`, %d coauthor rows sampled from %d (sorted by edge id, `random.sample`); windows in the sample: %s." % (
        a["seed"], a["sample_size"], a["population"], ", ".join("%s %d" % kv for kv in sorted(a["windows_in_sample"].items()))), "",
          "- sampled edges that resolve through every step: %s" % fmt(a["fully_resolves"]), ""]
    for step, p in sorted(a["by_step"].items()):
        L.append("  - %s: %s" % (step, fmt(p)))
    L += ["", "The full per-edge trace (edge id, window, joint count, support works, each step) is in `graph-correctness.json` under `provenance_audit.traces`.", "",
          "## Cross-check: the Spark job's own counters and load manifest", ""]
    cc = doc["cross_check"]
    if cc["spark_counters"]:
        L.append("Counters recorded by the Spark run (`counters.json`): " + ", ".join("%s=%s" % kv for kv in sorted(cc["spark_counters"].items())) + ".")
    if cc["load_manifest"]:
        L += ["", "| dataset | CSV rows read here | load manifest rows | agrees |", "|---|---|---|---|"]
        for r in cc["load_manifest"]["row_counts"]:
            L.append("| %s | %d | %s | %s |" % (r["dataset"], r["csv_rows"], r["load_manifest_rows"], "yes" if r["agrees"] else "NO"))
        lm = cc["load_manifest"]
        L += ["", "Support table (`edges/type=coauthored_with_support`, Parquet, not read here):",
              "- load-manifest row count %s against the sum of jointPublicationCount over the CSV coauthor rows %d: %s." % (
                  lm["support_table_rows_in_load_manifest"], lm["sum_of_joint_publication_counts"], "equal" if lm["support_table_rows_equal_sum_of_joint_counts"] else "NOT EQUAL"),
              "- (edge, support work) pairs stored on the CSV rows %d against the sum of min(joint, %d) %d: %s (the CSV keeps at most %d works per edge, so this is a check of the cap)." % (
                  lm["support_work_ids_stored_on_coauthor_rows"], SUPPORT_CAP, lm["sum_of_min_joint_and_cap"], "equal" if lm["stored_pairs_equal_sum_of_min_joint_and_cap"] else "NOT EQUAL", SUPPORT_CAP)]
    t = doc["known_small_graph_tests"]
    L += ["", "## Spark test inventory (listed from source, not run here)", ""]
    if t:
        L += ["%d suites, %d tests under `%s`. Only tests whose names mention a small known graph are marked **[small graph]** (selection by name pattern, not by reading the tests); "
              "the others test the job plumbing (schemas, markers, hashes, limits)." % (t["suite_count"], t["test_count"], t["directory"]), ""]
        for suite in t["suites"]:
            L += ["**%s** (`%s`, sha256 `%s`), %d tests:" % (suite["suite"], suite["path"], suite["sha256"][:16], len(suite["tests"])), ""]
            L += ["- %s%s" % ("**[small graph]** " if SMALL_GRAPH.search(name) else "", name) for name in suite["tests"]] + [""]
        L.append("%d tests match the small-graph name pattern. %s" % (sum(1 for x in t["suites"] for n in x["tests"] if SMALL_GRAPH.search(n)), t["note"]))
    else:
        L.append("GAP: the Spark test directory is missing.")
    lc = doc["last_full_check"]
    L += ["", "Last recorded full check that ran these suites: " + ("`%s` line %d (file sha256 `%s`). It ran on %s, **not on the current HEAD**. Quoted line: %s" % (
        lc["file"], lc["line"], lc["file_sha256"][:16], lc["tree"], lc["text"]) if lc else "GAP: no recorded full check found."),
          "", "## Sample limits, threats to validity and missing data", ""]
    L += ["- %s" % x for x in doc["threats_to_validity"]]
    L += ["", "## Gaps (not measured, with the reason)", ""]
    L += ["- **%s**: %s" % (g["metric"], g["reason"]) for g in doc["gaps"]]
    L += ["", "## Interpretation (separate from the measured facts above)", ""]
    L += ["- %s" % x for x in doc["interpretation"]]
    return "\n".join(L) + "\n"


def threats(audit, run_id):
    """Threat sentences; the run id, sample size and interval come from the computed audit, not from constants."""
    return [
    "One export (size S, " + run_id + ") is checked; the result describes that bounded run, not the full corpus or later runs.",
    "The checks read the CSV sidecar generated from the same Spark tables by the same job; a defect common to both would not show. The Parquet tables are not read (no stdlib Parquet reader), so the support table and the integrity/violations table are unverified here.",
    "The audit checks internal consistency (every edge traces to authored works and resolved nodes). It does not check the facts against the original sources (DBLP, OpenAlex, Crossref, ORCID), so a wrong merge made upstream by entity resolution would pass these checks.",
    "The provenance audit samples %d coauthor rows with a fixed seed; %d of %d resolved, so the Wilson 95%% interval of the resolution rate is %.1f%%-%.1f%%, not certainty." % (
        audit["sample_size"], audit["fully_resolves"]["k"], audit["fully_resolves"]["n"], 100 * audit["fully_resolves"]["wilson95"][0], 100 * audit["fully_resolves"]["wilson95"][1]),
    "Window-specific correctness (that a work belongs to the year window of an edge) is not checked: the CSV sidecar carries no work years.",
    "Known small-graph tests are listed from source, not run by this package; their pass state comes from the recorded full check cited above, which ran on a different tree than the current HEAD.",
    ]
GAPS = [
    {"metric": "support rows read from Parquet (edges/type=coauthored_with_support)", "reason": "no stdlib Parquet reader in an offline stdlib-only package; the support works stored on the CSV coauthor rows are used, and the Parquet row count is compared via the load manifest"},
    {"metric": "integrity/violations and integrity/rejects Parquet contents", "reason": "Parquet not readable here; the Spark job's own counters (missingGraphEndpoints and related) are quoted as a cross-check"},
    {"metric": "agreement of graph content with upstream source records", "reason": "needs the source data and an independent gold set, outside this offline package"},
    {"metric": "window membership of support works by publication year", "reason": "work years are not in the CSV sidecar"},
]


def interpretation(doc):
    ri, d, s, a = doc["referential_integrity"], doc["duplicates"], doc["support"], doc["provenance_audit"]
    out = ["Referential integrity: %d graph-edge rows and %d coauthor rows were checked; unresolved endpoints are %d and %d respectively." % (
        ri["graph_edges_total_with_unresolved_endpoint"]["n"], ri["coauthor_edges_with_unresolved_endpoint"]["n"],
        ri["graph_edges_total_with_unresolved_endpoint"]["k"], ri["coauthor_edges_with_unresolved_endpoint"]["k"]),
           "Duplicates: duplicate node ids %d, duplicate edge ids %d, duplicate coauthor (pair, window) rows %d." % (
               d["node_ids"]["k"], d["graph_edge_ids"]["k"], d["coauthor_pair_window"]["k"]),
           "Coauthor support: %s of coauthor rows are fully supported (all windows); the all-years joint count matches the recount from authorship for %s." % (
               fmt(s["all_windows"]["fully_supported"]), fmt(s["all_years_joint_count_recount"]["matching"])),
           "Orphans: %s of RESEARCHER nodes have no AUTHORED edge and %s have no coauthor edge in any window; %s of WORK nodes have no AUTHORED edge. This package does not explain these orphans "
           "(they are not integrity failures of an edge: no edge dangles); they are reported as measured." % (
               fmt(doc["orphans"]["RESEARCHER (no AUTHORED edge)"]), fmt(doc["orphans"]["RESEARCHER (no coauthor edge in any window)"]), fmt(doc["orphans"]["WORK (no AUTHORED edge)"])),
           "Provenance audit: %s of the %d sampled edges resolve through every step." % (fmt(a["fully_resolves"]), a["sample_size"]),
           "These checks establish internal consistency of the exported graph; they do not establish that the underlying identity decisions or source facts are correct (see the entity-resolution evaluation for the identity sample)."]
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export-dir", required=True)
    parser.add_argument("--out-dir", default=os.path.join(ROOT, "experiments", "results", "phase16", "graph"))
    parser.add_argument("--sample", type=int, default=50)
    args = parser.parse_args(argv)
    try:
        model, files = load_export(args.export_dir)
    except (OSError, ValueError, KeyError, Refused) as error:
        print("EVAL16-GRAPH-REFUSED: %s: %s" % (type(error).__name__, error))
        return 1
    authored_by, mentions_of, venues = authorship(model)
    nodes_by_label, edges_by_type, windows = {}, {}, {}
    for _, label in model["node_rows"]:
        nodes_by_label[label] = nodes_by_label.get(label, 0) + 1
    for e in model["graph_edges"]:
        edges_by_type[e[3]] = edges_by_type.get(e[3], 0) + 1
    for c in model["coauthor"]:
        windows[c[3]] = windows.get(c[3], 0) + 1
    listing = "\n".join("%s  %d  %s" % (digest, size, name) for name, size, digest in files)
    export_dir = os.path.abspath(args.export_dir)
    doc = {"schema": SCHEMA,
           "export": {"run_id": model["run_id"], "files": [list(f) for f in files], "files_listing_sha256": hashlib.sha256(listing.encode("utf-8")).hexdigest(),
                      "directory_note": "path given on the command line; the export lives under target/ and is not tracked by git"},
           "counts": {"nodes_by_label": nodes_by_label, "graph_edges_by_type": edges_by_type, "coauthor_edges_by_window": windows,
                      "works_with_venue": len(venues), "works_with_multiple_venues": sum(1 for v in venues.values() if v > 1),
                      "run_id_in_row_context": {"graph_edges": proportion(model["run_id_in_context"]["graph_edges"], len(model["graph_edges"])),
                                                "coauthor_edges": proportion(model["run_id_in_context"]["coauthor_edges"], len(model["coauthor"]))}},
           "referential_integrity": referential_integrity(model), "duplicates": duplicates(model), "orphans": orphans(model),
           "support": support_checks(model, authored_by), "provenance_audit": provenance_audit(model, authored_by, mentions_of, args.sample),
           "cross_check": {"spark_counters": spark_counters(export_dir), "load_manifest": manifest_cross_check(model, load_manifest_rows(export_dir))},
           "known_small_graph_tests": spark_known_graph_tests(ROOT), "last_full_check": last_full_check(ROOT),
           "gaps": GAPS}
    doc["threats_to_validity"] = threats(doc["provenance_audit"], model["run_id"])
    doc["interpretation"] = interpretation(doc)
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "graph-correctness.json"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    with open(os.path.join(args.out_dir, "graph-correctness.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown(doc))
    a, s = doc["provenance_audit"], doc["support"]
    print("EVAL16-GRAPH run=%s nodes=%d graph_edges=%d coauthor_rows=%d | unresolved_graph=%d unresolved_coauthor=%d | dup_node_ids=%d dup_edge_ids=%d | fully_supported=%d/%d | audit=%d/%d | recount_ok=%d/%d" % (
        model["run_id"], len(model["node_rows"]), len(model["graph_edges"]), len(model["coauthor"]),
        doc["referential_integrity"]["graph_edges_total_with_unresolved_endpoint"]["k"], doc["referential_integrity"]["coauthor_edges_with_unresolved_endpoint"]["k"],
        doc["duplicates"]["node_ids"]["k"], doc["duplicates"]["graph_edge_ids"]["k"], s["all_windows"]["fully_supported"]["k"], s["all_windows"]["fully_supported"]["n"],
        a["fully_resolves"]["k"], a["fully_resolves"]["n"], s["all_years_joint_count_recount"]["matching"]["k"], s["all_years_joint_count_recount"]["matching"]["n"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

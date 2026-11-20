#!/usr/bin/env python3
"""Compute the Q12 answer key from the Phase 6 export CSV sidecar and the derived question specs (stdlib only; python3 -I).

  python3 -I experiments/scripts/q12_answer_key.py --export-dir <spark export dir> \\
      --specs experiments/inputs/q12/question-specs.json --out experiments/inputs/q12/answer-key.json [--overwrite]

The key is computed by experiments/scripts/q12_graph.py (see its docstring for the algorithm of every quantity, each a port of
modules/spark). Which method is used per question type:
  coauthor_breadth  VALUES-AND-ORDER: distinct coauthors per window from the CSV (option b) are exact per researcher; the ranking is only checked
                    for values and order (the runtime ranks its artifact population, not the corpus); corpus top-100 recorded.
  max_team_size     all-years: VALUES-AND-ORDER from the AUTHORED edges (option b), top-100 recorded. Windowed: BOUNDED (the CSV has no work years):
                    every cited value must not exceed the researcher's all-years maximum, and a cited max-team work's team size must equal
                    the value + 1.
  direct_collab     EXACT: the complete coauthor list and joint publication counts of the window graph.
  shortest_path     EXACT: BFS hop count, number of shortest paths and up to 25 of them (the runtime limit), within maxPathDepth 6.
  component         EXACT: union-find component size and id.
  community         EXACT by independent port (option b) of the synchronous label propagation of job06, validated against
                    analytics-report.json (rows, sizeMax, iterations, finalChangedCount of every window) and against observed Session 1
                    values; community and component ids ported from StableIds.sparkAnalyticsId.
  bridge            VALUES-AND-ORDER from the ported community partition (crossCommunityDegree etc.), top-100 recorded.
  temporal          EXACT for distinct coauthors, component size, entered/left largest component, community ids and the four bridge deltas;
                    the community Jaccard overlap is a LOWER BOUND (the runtime also counts one-person communities of researchers with no edge
                    in the window, Phase6FGJobs.scala:118-147, which the CSV lacks); NOT CHECKED: deltaAverageCoauthorsPerPaper and deltaMaximumCoauthorsOnOnePaper (need work years).
  topic, institution  ABSTAIN (thin data): the export has no authoritative topic or institution metadata for any researcher.
  evidence          EXACT: a 1-hop shortest path between two direct coauthors with 2..5 joint works; the key is the exact set and count of joint works
                    (the edge row's representative work ids, which for joint <= 5 are exactly the joint works in every window of the real export, and
                    for all-years equal the AUTHORED intersection of the pair), checked against the edge evidence workIds and the answer text.
Ranking populations: the runtime ranks only the researchers inside its bounded artifact, so the recorded top-100 lists are corpus-wide;
the scorer checks every cited value against the export, ordering within the answer, and reports agreement with the corpus top as information.
Replayable validation (refuses on mismatch, --skip-validation records "skipped"): before the key is written the port is compared, window by window,
with the export's own analytics-report.json: largest component, community iterations, final changed count, largest community, the maxima of the four
bridge measures and (all-years) the maximum team size; the compared values are written to answer-key.json under source.validation.
Exit codes: 0 ok, 1 refused (including a validation mismatch), 2 usage.
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("q12_graph_for_key", os.path.join(HERE, "q12_graph.py"))
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)
Refused = g.Refused
SCHEMA = "scholarchain.q12-answer-key.v1"
TOP = 100
PATH_LIMIT = 25
MAX_DEPTH = 6


def number_alts(*alternatives):
    """A requirement group: satisfied when any alternative (a list of numbers that must all appear) is present."""
    out = []
    for alt in alternatives:
        alt = [int(n) if float(n).is_integer() else n for n in alt]
        if alt not in out:
            out.append(alt)
    return out


def ranking_top(values, ex):
    ordered = sorted(values.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP]
    return [{"rank": i + 1, "id": r, "name": ex.researchers.get(r, "").strip(), "value": v} for i, (r, v) in enumerate(ordered)]


def key_for(spec, ex, sizes):
    kind, p = spec["type"], spec["params"]
    out = {"id": spec["id"], "type": kind, "question": spec["question"], "slot": spec["slot"], "planner": spec["planner"],
           "window": p.get("window"), "params": p}
    if kind == "coauthor_breadth":
        wg = ex.window(p["window"])
        values = {r: len(a) for r, a in wg.adj.items()}
        out.update(check_level="values-and-order", expected_outcome="answer",
                   expected={"metric": p["metric"], "window": p["window"], "tie_break": "researcher id ascending", "top": ranking_top(values, ex),
                             "population_caveat": "the runtime ranks only the researchers inside its bounded artifact; the top list is corpus-wide"},
                   required_evidence={"kinds": ["ranking"], "fields_checked_per_entity": ["distinctCoauthorCount", "weightedDegree", "componentId", "communityId"]},
                   required_text={"mode": "ranking", "note": "the text must name the rank-1 cited researcher and state that researcher's value"})
    elif kind == "max_team_size":
        if p["window"] == "all-years":
            values = {r: g.max_team(ex, r, sizes)[0] for r in ex.authored_by}
            out.update(check_level="values-and-order", expected_outcome="answer",
                       expected={"metric": p["metric"], "window": p["window"], "tie_break": "researcher id ascending", "top": ranking_top(values, ex),
                                 "global_maximum": max(values.values()),
                                 "population_caveat": "the runtime ranks only the researchers inside its bounded artifact; the top list is corpus-wide"},
                       required_evidence={"kinds": ["ranking"], "fields_checked_per_entity": ["maximumCoauthorsOnOnePaper", "maxTeamWorkIds"]},
                       required_text={"mode": "ranking", "note": "the text must name the rank-1 cited researcher and state that researcher's value"})
        else:
            out.update(check_level="bounded", expected_outcome="answer",
                       expected={"metric": p["metric"], "window": p["window"], "global_maximum_all_years": max(max_v for max_v in
                                 (sizes[w] - 1 for w in sizes)),
                                 "rule": "each cited value <= the researcher's all-years maximum <= global_maximum_all_years; each cited max-team work "
                                         "must have team size value + 1 in the AUTHORED edges (a work lies in a window entirely)"},
                       required_evidence={"kinds": ["ranking"], "fields_checked_per_entity": ["maximumCoauthorsOnOnePaper", "maxTeamWorkIds"]},
                       required_text={"mode": "ranking", "note": "the text must name the rank-1 cited researcher and state that researcher's value"})
    elif kind == "bridge":
        wg = ex.window(p["window"])
        values = {r: b["crossCommunityDegree"] for r, b in wg.bridges().items()}
        out.update(check_level="values-and-order", expected_outcome="answer",
                   expected={"measure": p["measure"], "window": p["window"], "tie_break": "researcher id ascending", "top": ranking_top(values, ex),
                             "population_caveat": "the runtime ranks only the researchers inside its bounded artifact; the top list is corpus-wide",
                             "qualification": "community-derived: synchronous label propagation, iteration-limited at 20 (not converged); the answer should say so"},
                   required_evidence={"kinds": ["bridge"], "fields_checked_per_entity": ["crossCommunityDegree", "crossCommunityWeight", "communitiesConnected", "participationCoefficient", "communityId"]},
                   required_text={"mode": "ranking", "note": "the text must name the rank-1 cited researcher and state that researcher's value"})
    elif kind == "direct_collab":
        r, window = p["researcher"]["id"], p["window"]
        wg = ex.window(window)
        coauthors = sorted(({"id": o, "name": ex.researchers.get(o, "").strip(), "joint": j} for o, j in wg.adj[r].items()), key=lambda c: (-c["joint"], c["id"]))
        total = len(coauthors)
        shown = min(total, PATH_LIMIT)
        out.update(check_level="exact", expected_outcome="answer",
                   expected={"researcher": p["researcher"], "window": window, "total": total, "page_limit": PATH_LIMIT, "truncated": total > PATH_LIMIT,
                             "coauthors": coauthors},
                   required_evidence={"kinds": ["direct-coauthors"], "subjects": [r], "rule": "cited coauthorIds are a subset of expected.coauthors; "
                                      "returnedCount equals min(total, page_limit)"},
                   required_text={"names": [p["researcher"]["name"]], "numbers": [number_alts([total], [shown])],
                                  "coauthor_name_recall_min": 0.6, "coauthor_names_expected": shown,
                                  "note": "the count is total or the page size; at least 60 percent of the shown coauthors are named when the page is not truncated"})
    elif kind == "shortest_path":
        a, b, window = p["a"]["id"], p["b"]["id"], p["window"]
        wg = ex.window(window)
        hops, count, paths = wg.shortest_paths(a, b, limit=PATH_LIMIT, max_depth=MAX_DEPTH)
        if hops is None:
            raise Refused("%s: no path within %d hops between the chosen researchers" % (spec["id"], MAX_DEPTH))
        names = lambda path: [ex.researchers.get(x, "").strip() for x in path]
        middles = sorted({n for pth in paths for n in names(pth)[1:-1]})
        out.update(check_level="exact", expected_outcome="answer",
                   expected={"a": p["a"], "b": p["b"], "window": window, "status": "Found", "hops": hops, "shortest_path_count": count,
                             "paths": [{"ids": pth, "names": names(pth)} for pth in paths[:5]], "max_hops": MAX_DEPTH},
                   required_evidence={"kinds": ["path"], "subjects": [a, b], "rule": "every cited path's ids are a real path in the window graph "
                                      "with hopCount == hops, first id a and last id b"},
                   required_text={"names": [p["a"]["name"], p["b"]["name"]], "numbers": [number_alts([hops])],
                                  "hop_words": hops, "path_names_any_of": [names(pth)[1:-1] for pth in paths],
                                  "note": "the hop count appears as a digit or word; for 2 or more hops the interior names of at least one shortest path appear"})
    elif kind == "component":
        r, window = p["researcher"]["id"], p["window"]
        wg = ex.window(window)
        label_of, members = wg.components()
        label = label_of[r]
        largest = max(members.items(), key=lambda kv: (len(kv[1]), kv[0]))[0]
        size = len(members[label])
        out.update(check_level="exact", expected_outcome="answer",
                   expected={"researcher": p["researcher"], "window": window, "component_id": g.analytics_id("component", window, label), "size": size,
                             "is_largest": label == largest, "number_of_components_with_edges": len(members)},
                   required_evidence={"kinds": ["metrics"], "subjects": [r], "rule": "the metrics evidence componentId equals component_id"},
                   required_text={"names": [p["researcher"]["name"]], "numbers": [number_alts([size])],
                                  "note": "the answer states the component size (digits with or without thousands separators) or the component id"})
    elif kind == "community":
        r, window = p["researcher"]["id"], p["window"]
        wg = ex.window(window)
        label = wg.communities()[0][r]
        members = wg.community_members()[label]
        mset = set(members)
        neighbours = {}
        cross_edges = 0
        lab = wg.communities()[0]
        for m in members:
            for o in wg.adj[m]:
                if o not in mset:
                    cross_edges += 1
                    neighbours[lab[o]] = neighbours.get(lab[o], 0) + 1
        out.update(check_level="exact", expected_outcome="answer",
                   expected={"researcher": p["researcher"], "window": window, "community_id": g.analytics_id("community", window, label),
                             "size": len(members), "members": members,
                             "neighbor_community_ids": sorted(g.analytics_id("community", window, c) for c in neighbours),
                             "cross_community_edge_count": cross_edges, "converged": wg.communities()[3], "iterations": wg.communities()[1],
                             "qualification": "iteration-limited" if not wg.communities()[3] else "converged"},
                   required_evidence={"kinds": ["community"], "subjects": [r], "rule": "evidence communityId == community_id, size == size, "
                                      "selectedMemberIds subset of members, neighborCommunityIds subset of neighbor_community_ids"},
                   required_text={"names": [p["researcher"]["name"]], "numbers": [number_alts([len(members)])],
                                  "note": "the answer states the community size; communities are iteration-limited and the answer should say so"})
    elif kind == "temporal":
        r, w_from, w_to = p["researcher"]["id"], p["from"], p["to"]
        a, b = ex.window(w_from), ex.window(w_to)
        if r not in a.adj or r not in b.adj:
            raise Refused("%s: researcher has no edge in both windows" % spec["id"])
        la, lb = a.communities()[0], b.communities()[0]
        ba, bb = a.bridges()[r], b.bridges()[r]
        comp_a, comp_b = a.components(), b.components()
        largest = lambda comps: max(comps[1].items(), key=lambda kv: (len(kv[1]), kv[0]))[0]
        in_largest_a, in_largest_b = comp_a[0][r] == largest(comp_a), comp_b[0][r] == largest(comp_b)
        old_members = a.community_members()
        new_members = b.community_members()
        prev, cur = la[r], lb[r]
        best = None
        old_set = set(old_members[prev])
        for label, mem in new_members.items():
            inter = len(old_set & set(mem))
            if inter:
                j = inter / (len(old_set) + len(mem) - inter)
                cid = g.analytics_id("community", w_to, label)
                if best is None or (-j, cid) < (-best[0], best[1]):
                    best = (j, cid)
        delta_d = len(b.adj[r]) - len(a.adj[r])
        out.update(check_level="exact", expected_outcome="answer",
                   expected={"researcher": p["researcher"], "from": w_from, "to": w_to, "fromPresent": True, "toPresent": True,
                             "distinctCoauthors": {"from": len(a.adj[r]), "to": len(b.adj[r])}, "deltaDistinctCoauthors": delta_d,
                             "deltaComponentSize": len(comp_b[1][comp_b[0][r]]) - len(comp_a[1][comp_a[0][r]]),
                             "componentSize": {"from": len(comp_a[1][comp_a[0][r]]), "to": len(comp_b[1][comp_b[0][r]])},
                             "enteredLargestComponent": in_largest_b and not in_largest_a, "leftLargestComponent": in_largest_a and not in_largest_b,
                             "previousCommunityId": g.analytics_id("community", w_from, prev), "currentCommunityId": g.analytics_id("community", w_to, cur),
                             "communityJaccardOverlap": best[0],
                             "communityJaccardOverlap_semantics": "LOWER BOUND: the runtime also counts the one-person communities of researchers with no edge in a window "
                                                                  "(they are not in the CSV), so its value may be higher; accepted when key <= runtime <= 1",
                             "deltaCrossCommunityDegree": bb["crossCommunityDegree"] - ba["crossCommunityDegree"],
                             "deltaCrossCommunityWeight": bb["crossCommunityWeight"] - ba["crossCommunityWeight"],
                             "deltaCommunitiesConnected": bb["communitiesConnected"] - ba["communitiesConnected"],
                             "deltaParticipationCoefficient": bb["participationCoefficient"] - ba["participationCoefficient"],
                             "not_checked": ["deltaAverageCoauthorsPerPaper", "deltaMaximumCoauthorsOnOnePaper"]},
                   required_evidence={"kinds": ["temporal"], "subjects": [r], "rule": "evidence values equal the expected deltas and ids"},
                   required_text={"names": [p["researcher"]["name"]],
                                  "numbers": [number_alts([abs(delta_d)], [len(a.adj[r]), len(b.adj[r])])] if delta_d else [number_alts([0], [len(a.adj[r])])],
                                  "note": "the answer states the change in distinct coauthors (absolute value) or both window values"})
    elif kind in ("topic", "institution"):
        what = "topic" if kind == "topic" else "institution"
        out.update(check_level="abstain", expected_outcome="abstain",
                   expected={"filter": what, "value": p.get(what), "window": p["window"], "thin_data": True,
                             "reason": ("no researcher has authoritative topic metadata in the export (%d TOPIC nodes, all on %d work with no AUTHORED edge)" % (len(ex.topics), len(ex.has_topic))
                                        if kind == "topic" else
                                        "no researcher has authoritative institution metadata in the export (%d INSTITUTION node, %d AFFILIATED_WITH edges)" % (len(ex.institutions), sum(len(v) for v in ex.affiliated.values())))
                                       + "; the runtime rejects the filtered ranking (unsupported-authoritative-filter-metadata) and must abstain",
                             "acceptable_abstention_forms": ["HTTP 200 answer with outcome ABSTAINED and no verified ranking claim", "HTTP 422 with the closed error code UNSUPPORTED_QUERY"],
                             "forbidden": "any ranking of researchers presented as filtered by the %s" % what},
                   required_evidence={"kinds": []}, required_text={"mode": "abstain"})
    elif kind == "evidence":
        a, b, window = p["a"]["id"], p["b"]["id"], p["window"]
        pair = (a, b) if a < b else (b, a)
        wg = ex.window(window)
        joint = wg.joint(a, b)
        works = sorted(ex.edge_works[window].get(pair, ()))
        shared = ex.authored_by.get(a, set()) & ex.authored_by.get(b, set())
        if not 2 <= joint <= 5 or len(works) != joint or not set(works) <= shared or (window == "all-years" and set(works) != shared):
            raise Refused("%s: the pair does not have 2..5 exactly known joint works in %s" % (spec["id"], window))
        if sorted(p.get("joint_work_ids") or []) != works:
            raise Refused("%s: the specs list different joint works than the export" % spec["id"])
        hops, count, paths = wg.shortest_paths(a, b, limit=PATH_LIMIT, max_depth=MAX_DEPTH)
        if hops != 1:
            raise Refused("%s: the pair is not a direct pair in %s" % (spec["id"], window))
        out.update(check_level="exact", expected_outcome="answer",
                   expected={"a": p["a"], "b": p["b"], "window": window, "status": "Found", "hops": 1, "joint_publications": joint, "joint_work_ids": works,
                             "joint_work_titles": [ex.works.get(w, "") for w in works], "edge_id": ex.edge_ids[window][pair],
                             "rule": "the cited edge evidence names both researchers in the window, jointPublicationCount equals joint_publications and its "
                                     "workIds are exactly joint_work_ids; the cited path has hopCount 1"},
                   required_evidence={"kinds": ["edge", "path"], "subjects": [a, b], "any_kind": True},
                   required_text={"names": [p["a"]["name"], p["b"]["name"]], "numbers": [number_alts([joint])], "count_words": joint,
                                  "note": "the answer names both researchers and states the number of joint works (digit or word)"})
    else:
        raise Refused("unknown question type %s" % kind)
    return out


def validate_against_report(ex, export_dir):
    """Compare the port with analytics-report.json of the export; returns {window: {name: {computed, report}}}; raises Refused on a mismatch."""
    path = os.path.join(export_dir, "analytics-report.json")
    if not os.path.isfile(path):
        raise Refused("%s has no analytics-report.json to validate the port against (use --skip-validation to record that it was skipped)" % os.path.basename(os.path.abspath(export_dir)))
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    by = lambda section: {e.get("window"): e for e in report.get(section, [])}
    comps, comms, conv, bridges, metrics = (by(x) for x in ("components", "communities", "communityConvergence", "bridges", "metrics"))
    sizes = g.team_sizes(ex)
    compared, problems = {}, []
    windows = [w for w in g.WINDOWS if w in comps]
    if not windows:
        raise Refused("analytics-report.json holds no window the port can be compared on")
    for w in windows:
        wg = ex.window(w)
        label, iterations, changed, _converged = wg.communities()
        br = wg.bridges()
        rows = {
            "largestComponent": (max(len(m) for m in wg.components()[1].values()), comps[w].get("largestSize")),
            "communityIterations": (iterations, conv.get(w, {}).get("iterations")),
            "communityFinalChangedCount": (changed, conv.get(w, {}).get("finalChangedCount")),
            "communityLargest": (max(len(m) for m in wg.community_members().values()), comms.get(w, {}).get("sizeMax")),
            "crossCommunityDegreeMax": (max(b["crossCommunityDegree"] for b in br.values()), bridges.get(w, {}).get("crossCommunityDegreeMax")),
            "crossCommunityWeightMax": (max(b["crossCommunityWeight"] for b in br.values()), bridges.get(w, {}).get("crossCommunityWeightMax")),
            "communitiesConnectedMax": (max(b["communitiesConnected"] for b in br.values()), bridges.get(w, {}).get("communitiesConnectedMax")),
            "participationCoefficientMax": (max(b["participationCoefficient"] for b in br.values()), bridges.get(w, {}).get("participationCoefficientMax")),
        }
        if w == "all-years":
            rows["maximumCoauthorsOnOnePaperMax"] = (max(sizes.values()) - 1, metrics.get(w, {}).get("maximumCoauthorsOnOnePaperMax"))
        compared[w] = {}
        for name, (mine, theirs) in rows.items():
            ok = theirs is not None and abs(float(mine) - float(theirs)) <= 1e-9
            compared[w][name] = {"computed": mine, "report": theirs}
            if not ok:
                problems.append("%s %s: computed %s, report %s" % (w, name, mine, theirs))
    if problems:
        raise Refused("the port disagrees with analytics-report.json: " + "; ".join(problems[:6]))
    return compared


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export-dir", required=True)
    parser.add_argument("--specs", required=True, help="question-specs.json written by derive_q12_inputs.py")
    parser.add_argument("--out", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-validation", action="store_true", help="do not compare the port with analytics-report.json (recorded in the key)")
    args = parser.parse_args(argv)
    try:
        with open(args.specs, encoding="utf-8") as handle:
            specs = json.load(handle)
        specs_sha = g.sha256_file(args.specs)
        ex = g.Export(args.export_dir)
        if specs.get("run_id") != ex.run_id:
            raise Refused("the specs were derived from %s, the export is %s" % (specs.get("run_id"), ex.run_id))
        if os.path.lexists(args.out) and not args.overwrite:
            raise Refused("%s exists (use --overwrite)" % args.out)
        validation = {"status": "skipped"} if args.skip_validation else {"status": "matched", "against": "analytics-report.json", "windows": validate_against_report(ex, args.export_dir)}
        sizes = g.team_sizes(ex)
        questions = [key_for(q, ex, sizes) for q in specs["questions"]]
        listing = "".join("%s  %s\n" % (sha, rel) for rel, sha in ex.files_read)
        by_level = {}
        for q in questions:
            by_level[q["check_level"]] = by_level.get(q["check_level"], 0) + 1
        doc = {"schema": SCHEMA, "tool": "experiments/scripts/q12_answer_key.py",
               "source": {"run_id": ex.run_id, "files_read_listing_sha256": g.sha256_text(listing), "question_specs_sha256": specs_sha,
                          "graph_helper_sha256": g.sha256_file(os.path.join(HERE, "q12_graph.py")), "seed": specs.get("seed"), "validation": validation},
               "method": {"windows": list(g.WINDOWS), "path_depth": MAX_DEPTH, "page_limit": PATH_LIMIT, "ranking_top": TOP,
                          "communities": "independent port of synchronous label propagation (modules/spark job06), validated against analytics-report.json",
                          "not_checked": ["deltaAverageCoauthorsPerPaper", "deltaMaximumCoauthorsOnOnePaper"]},
               "counts": {"questions": len(questions), "by_check_level": dict(sorted(by_level.items()))},
               "questions": questions}
        text = json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("WROTE %s sha256=%s" % (args.out, g.sha256_text(text)))
        for q in questions:
            print("%s %-16s %-10s %-7s %s" % (q["id"], q["type"], q["check_level"], q["expected_outcome"], q["question"][:90]))
    except Refused as error:
        print("KEY-REFUSED: %s" % error)
        return 1
    except (OSError, ValueError, KeyError) as error:
        print("KEY-REFUSED: %s: %s" % (type(error).__name__, error))
        return 1
    print("RESULT: OK questions=%d by_check_level=%s" % (len(questions), json.dumps(dict(sorted(by_level.items())))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

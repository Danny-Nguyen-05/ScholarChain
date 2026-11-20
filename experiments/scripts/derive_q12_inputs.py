#!/usr/bin/env python3
"""Derive the Q12 benchmark inputs (33 questions, 3 per type x 11 types) from a completed Phase 6 Spark export (stdlib only; python3 -I).

Reads ONLY the plain-CSV Neptune openCypher sidecar of the export through experiments/scripts/q12_graph.py (no Parquet reader).
Writes into --out-dir (refuses to overwrite without --overwrite; LF-terminated; byte-identical for the same input and --seed):
  questions.txt         33 questions, one per line, id order q01..q33 (round-robin over the 11 types, see TYPES)
  include-ids.txt       researcher IDs the runtime artifact must hold: every researcher named in a question plus the one middle
                        researcher of the 3-hop path (so the hop between the two middle researchers is inside the artifact closure)
  question-specs.json   per question: id, type, slot, planner route, the structured parameters the answer key computes from
  provenance.json       export run id, sha256 of every file read, the selection rule, the seed, counts, sha256 of each output

The eleven types (user decision 2026-11-16: coauthor breadth, max team size, direct collaboration, shortest paths, components,
communities, bridge researchers, temporal change, topics, institutions, evidence):
  coauthor_breadth   ranking by distinct coauthors, windows all-years / since-2015 / 2010-2014
  max_team_size      ranking by maximum team size (maximum coauthors on one paper), windows all-years / since-2015 / 2020-2026
  direct_collab      "Who are the direct coauthors of X?" (all-years degree 26..35 so the 25-row limit truncates; all-years degree
                     10..22; since-2015 degree 10..22)
  shortest_path      two researchers at hop distance 1 (all-years), 2 (since-2015) and 3 (all-years; the middle researcher is added to
                     the include list)
  component          component of a researcher: all-years in the largest component; through-2009 and since-2015 in a smaller one
  community          "Compare communities of X" for all-years, since-2015 and 2020-2026 (planner route: LLM; not in the fallback grammar)
  bridge             ranking of bridge researchers (default cross-community degree), windows all-years / since-2015 / 2020-2026
  temporal           "Did X change from W1 to W2?" for the three adjacent stored window pairs (planner route: LLM)
  topic              ranking filtered by topic "..."; THIN DATA: the export has 3 TOPIC nodes, all on one work with no AUTHORED edge,
                     so no researcher has authoritative topic metadata and the runtime must abstain (key expected: abstain)
  institution        ranking filtered by institution "..."; THIN DATA: 1 INSTITUTION node and 0 AFFILIATED_WITH edges: abstain
  evidence           "Explain the research collaboration of X": the explain / SemanticExplanation operation; every question is also scored
                     on its evidence trail, and this type isolates the explanation form: the answer must be backed by evidence items
                     that resolve through /v1/evidence/{id} and name the researcher (planner route: LLM)

Selection rule (no randomness other than the recorded seed; every tie is broken by the stable ID):
  eligible(r) = the display name is unique among ALL researcher nodes after trim + lowercase + whitespace collapse, is also unique after
                removing a DBLP homonym suffix (" 0001") from every researcher name (so "Wei Wang" is ineligible when "Wei Wang 0001" exists),
                is 3..60 characters of ASCII letters, spaces, hyphens or apostrophes, and the ID is a researcher:<source>:<key> ID.
  pick(slot)  = candidates sorted by ID (pairs by (id_a, id_b)); start index = int(sha256(seed + "|" + slot)[:8], 16) mod len; the first
                candidate from that index (cyclically) that is not already named by an earlier slot. Slots run in a fixed order.
  degree      = distinct coauthors in the stated window. Budget: the include list's total all-years degree must be at most
                --degree-budget (default 900, about 8,200 artifact rows below the 10,000-row cap, as derive_14c_inputs.py).
Exit codes: 0 ok, 1 refused (bad input, would overwrite, no candidate, budget), 2 usage.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("q12_graph_for_derive", os.path.join(HERE, "q12_graph.py"))
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)
Refused = g.Refused

SCHEMA = "scholarchain.q12-inputs-provenance.v1"
SPECS_SCHEMA = "scholarchain.q12-question-specs.v1"
NAME_OK = re.compile(r"^[A-Za-z][A-Za-z '\-]{1,58}[A-Za-z]$")
RESEARCHER_ID = re.compile(r"^researcher:[a-z0-9-]+:[^\s]{1,400}$")
# Order of the round-robin over the question file: the two abstain-expected types (topic, institution) are never adjacent, so the expected
# 422 refusals cannot meet at the consecutive-failure stop of the runner (and a failure on a neighbour cannot look like a run of them).
TYPES = ("coauthor_breadth", "topic", "max_team_size", "direct_collab", "institution", "shortest_path", "component", "community",
         "bridge", "temporal", "evidence")
HOMONYM = re.compile(r"\s+[0-9]{4}$")
PLANNER = {"coauthor_breadth": "fallback", "max_team_size": "fallback", "direct_collab": "fallback", "shortest_path": "fallback",
           "component": "fallback", "community": "llm", "bridge": "fallback", "temporal": "llm", "topic": "fallback",
           "institution": "fallback", "evidence": "llm"}
DEFAULT_SEED = "q12-v1"
DEFAULT_BUDGET = 900
BAND = (10, 22)
HUB_BAND = (26, 35)


def window_suffix(window):
    """The accepted request grammar for a stored window: nothing, 'since 2015' or 'in window <id>'."""
    if window == "all-years":
        return ""
    if window == "since-2015":
        return " since 2015"
    return " in window " + window


class Selector:
    def __init__(self, export, seed):
        self.ex, self.seed, self.used = export, seed, set()
        counts, base_counts = {}, {}
        for name in export.researchers.values():
            counts[g.norm_name(name)] = counts.get(g.norm_name(name), 0) + 1
            base = HOMONYM.sub("", g.norm_name(name))   # "Wei Wang 0001" counts as "wei wang": the plain name is then ambiguous too
            base_counts[base] = base_counts.get(base, 0) + 1
        self.eligible = {r for r, name in export.researchers.items()
                         if RESEARCHER_ID.match(r) and NAME_OK.match(name.strip()) and name == name.strip() and "  " not in name
                         and counts[g.norm_name(name)] == 1 and base_counts[g.norm_name(name)] == 1}
        self.sizes = g.team_sizes(export)

    def deg(self, r, window):
        return self.ex.window(window).degree(r)

    def start(self, slot, size):
        return int(g.sha256_text(self.seed + "|" + slot)[:8], 16) % size

    def pick(self, slot, candidates):
        items = sorted(candidates)
        if not items:
            raise Refused("slot %s has no candidate" % slot)
        first = self.start(slot, len(items))
        for offset in range(len(items)):
            item = items[(first + offset) % len(items)]
            ids = item if isinstance(item, tuple) else (item,)
            if not any(i in self.used for i in ids):
                return item
        raise Refused("slot %s has no unused candidate" % slot)

    def take(self, slot, candidates):
        item = self.pick(slot, candidates)
        self.used.update(item if isinstance(item, tuple) else (item,))
        return item

    def researchers(self, window, lo, hi, all_max=None, all_min=None):
        out = []
        for r in self.ex.window(window).adj:
            if r in self.eligible and lo <= self.deg(r, window) <= hi:
                d_all = self.deg(r, "all-years")
                if (all_max is None or d_all <= all_max) and (all_min is None or d_all >= all_min):
                    out.append(r)
        return out


def person(ex, r):
    return {"id": r, "name": ex.researchers[r].strip()}


def build(ex, seed, budget):
    sel = Selector(ex, seed)
    specs = {t: [] for t in TYPES}
    support = []   # extra include ids that are not named in a question

    def add(kind, slot, question, params):
        specs[kind].append({"type": kind, "slot": slot, "question": question, "planner": PLANNER[kind], "params": params})

    # coauthor breadth, max team size and bridges: global rankings, no entity
    for window in ("all-years", "since-2015", "2010-2014"):
        add("coauthor_breadth", "breadth-" + window, "Which researchers have the most distinct coauthors%s?" % window_suffix(window),
            {"window": window, "metric": "DISTINCT_COAUTHOR_COUNT"})
    team_forms = (("all-years", "Which researchers have the largest team size?"),
                  ("since-2015", "Which researchers have the maximum team size since 2015?"),
                  ("2020-2026", "Rank researchers by maximum team size in window 2020-2026"))
    for window, text in team_forms:
        add("max_team_size", "team-" + window, text, {"window": window, "metric": "MAXIMUM_COAUTHORS_ON_ONE_PAPER"})
    for window in ("all-years", "since-2015", "2020-2026"):
        add("bridge", "bridge-" + window, "Which researchers are the strongest bridges%s?" % window_suffix(window),
            {"window": window, "measure": "CROSS_COMMUNITY_DEGREE"})

    # direct collaboration
    hub = sel.take("direct-hub", sel.researchers("all-years", HUB_BAND[0], HUB_BAND[1]))
    mid = sel.take("direct-all", sel.researchers("all-years", BAND[0], BAND[1]))
    since = sel.take("direct-since", sel.researchers("since-2015", BAND[0], BAND[1], all_max=BAND[1]))
    for slot, r, window in (("direct-hub", hub, "all-years"), ("direct-all", mid, "all-years"), ("direct-since", since, "since-2015")):
        add("direct_collab", slot, 'Who are the direct coauthors of "%s"%s?' % (ex.researchers[r].strip(), window_suffix(window)),
            {"window": window, "researcher": person(ex, r)})

    # shortest paths: distances 1, 2 and 3
    all_graph = ex.window("all-years")
    pairs1 = [(a, b) for (a, b), joint in all_graph.weight.items()
              if joint >= 2 and a in sel.eligible and b in sel.eligible and BAND[0] <= all_graph.degree(a) <= BAND[1]
              and BAND[0] <= all_graph.degree(b) <= BAND[1]]
    a, b = sel.take("path-1", pairs1)
    add("shortest_path", "path-1", 'What is the shortest coauthor path between "%s" and "%s"?' % (ex.researchers[a].strip(), ex.researchers[b].strip()),
        {"window": "all-years", "a": person(ex, a), "b": person(ex, b), "expected_hops": 1})

    def far_pairs(window, hops, starts, other_ok):
        wg = ex.window(window)
        out = []
        for s in starts:
            dist, _ = wg.bfs(s, hops)
            out.extend((s, t) for t, d in dist.items() if d == hops and other_ok(t))
        return out
    starts2 = sorted(sel.researchers("since-2015", BAND[0], BAND[1], all_max=BAND[1]))
    starts2 = [s for s in starts2 if s not in sel.used][:60:2]
    ok2 = lambda t: t in sel.eligible and t not in sel.used and BAND[0] <= sel.deg(t, "since-2015") <= BAND[1] and sel.deg(t, "all-years") <= BAND[1]
    a, b = sel.take("path-2", far_pairs("since-2015", 2, starts2, ok2))
    add("shortest_path", "path-2", 'What is the shortest coauthor path between "%s" and "%s"%s?' % (ex.researchers[a].strip(), ex.researchers[b].strip(), window_suffix("since-2015")),
        {"window": "since-2015", "a": person(ex, a), "b": person(ex, b), "expected_hops": 2})
    starts3 = [s for s in sorted(sel.researchers("all-years", BAND[0], BAND[1])) if s not in sel.used][:60:2]
    ok3 = lambda t: t in sel.eligible and t not in sel.used and BAND[0] <= all_graph.degree(t) <= BAND[1]
    a, b = sel.take("path-3", far_pairs("all-years", 3, starts3, ok3))
    hops, count, paths = all_graph.shortest_paths(a, b, limit=25, max_depth=6)
    best = min(paths, key=lambda p: (all_graph.degree(p[2]), p))   # the third node of the path joins the include list
    support.append(best[2])
    add("shortest_path", "path-3", 'What is the shortest coauthor path between "%s" and "%s"?' % (ex.researchers[a].strip(), ex.researchers[b].strip()),
        {"window": "all-years", "a": person(ex, a), "b": person(ex, b), "expected_hops": 3, "support_include_id": best[2]})

    # components
    giant = max(all_graph.components()[1].items(), key=lambda kv: (len(kv[1]), kv[0]))[0]
    giant_members = set(all_graph.components()[1][giant])
    r = sel.take("component-all", [x for x in sel.researchers("all-years", BAND[0], BAND[1]) if x in giant_members])
    add("component", "component-all", 'What is the component of "%s"?' % ex.researchers[r].strip(), {"window": "all-years", "researcher": person(ex, r)})
    for slot, window in (("component-through-2009", "through-2009"), ("component-since-2015", "since-2015")):
        wg = ex.window(window)
        label_of, members = wg.components()
        largest = max(members.items(), key=lambda kv: (len(kv[1]), kv[0]))[0]
        cands = [x for x in sel.researchers(window, BAND[0], BAND[1], all_max=BAND[1]) if label_of[x] != largest and len(members[label_of[x]]) >= 12]
        r = sel.take(slot, cands)
        add("component", slot, 'What is the component of "%s"%s?' % (ex.researchers[r].strip(), window_suffix(window)), {"window": window, "researcher": person(ex, r)})

    # communities
    for slot, window in (("community-all", "all-years"), ("community-since-2015", "since-2015"), ("community-2020-2026", "2020-2026")):
        wg = ex.window(window)
        label = wg.communities()[0]
        members = wg.community_members()
        cands = [x for x in sel.researchers(window, BAND[0], BAND[1], all_max=BAND[1]) if 4 <= len(members[label[x]]) <= 40]
        r = sel.take(slot, cands)
        add("community", slot, 'Compare communities of "%s"%s' % (ex.researchers[r].strip(), window_suffix(window)), {"window": window, "researcher": person(ex, r)})

    # temporal change: the three adjacent stored window pairs
    for slot, w_from, w_to in (("temporal-1", "through-2009", "2010-2014"), ("temporal-2", "2010-2014", "2015-2019"), ("temporal-3", "2015-2019", "2020-2026")):
        cands = [x for x in sel.researchers(w_from, 8, 30, all_max=35) if 8 <= sel.deg(x, w_to) <= 30]
        r = sel.take(slot, cands)
        add("temporal", slot, 'Did "%s" change from %s to %s?' % (ex.researchers[r].strip(), w_from, w_to),
            {"researcher": person(ex, r), "from": w_from, "to": w_to})

    # topics and institutions: thin data, the runtime must abstain
    topics = sorted(ex.topics.values())
    institutions = sorted(ex.institutions.values())
    if len(topics) < 1 or len(institutions) < 1:
        raise Refused("the export holds no TOPIC or no INSTITUTION node to name in a filter")
    t_forms = (("Which researchers have the most distinct coauthors topic \"{f}\"?", "all-years"),
               ("Which researchers have the most distinct coauthors topic \"{f}\" since 2015?", "since-2015"),
               ("Rank researchers by distinct coauthors topic \"{f}\" in window 2020-2026", "2020-2026"))
    for i, (form, window) in enumerate(t_forms):
        topic = topics[i % len(topics)]
        add("topic", "topic-%d" % (i + 1), form.format(f=topic), {"window": window, "topic": topic, "thin_data": True})
    i_forms = (("Which researchers have the most distinct coauthors institution \"{f}\"?", "all-years", "DISTINCT_COAUTHOR_COUNT"),
               ("Rank bridge researchers institution \"{f}\" since 2015", "since-2015", "CROSS_COMMUNITY_DEGREE"),
               ("Which researchers have the largest team size institution \"{f}\"?", "all-years", "MAXIMUM_COAUTHORS_ON_ONE_PAPER"))
    for i, (form, window, metric) in enumerate(i_forms):
        institution = institutions[i % len(institutions)]
        add("institution", "institution-%d" % (i + 1), form.format(f=institution), {"window": window, "institution": institution, "metric": metric, "thin_data": True})

    # evidence: the explain form for three researchers
    for slot in ("evidence-1", "evidence-2", "evidence-3"):
        r = sel.take(slot, [x for x in sel.researchers("all-years", BAND[0], BAND[1]) if len(ex.authored_by.get(x, ())) >= 3])
        add("evidence", slot, 'Explain the research collaboration of "%s"' % ex.researchers[r].strip(), {"window": "all-years", "researcher": person(ex, r)})

    questions = []
    for index in range(3):
        for kind in TYPES:
            spec = dict(specs[kind][index])
            spec["id"] = "q%02d" % (len(questions) + 1)
            questions.append(spec)
    texts = [q["question"] for q in questions]
    if len(questions) != 33 or len(set(texts)) != 33:
        raise Refused("expected 33 distinct questions, got %d (%d distinct)" % (len(questions), len(set(texts))))
    named = set(sel.used)
    include = sorted(named | set(support))
    total_degree = sum(all_graph.degree(r) for r in include)
    if total_degree > budget:
        raise Refused("the include list's total all-years degree is %d, above the --degree-budget %d" % (total_degree, budget))
    if len(include) > 2000:
        raise Refused("include list would hold %d IDs (maximum 2000)" % len(include))
    counts = {"researchers": len(ex.researchers), "eligible": len(sel.eligible), "all_years_coauthor_pairs": len(all_graph.weight), "questions": len(questions),
              "include_ids": len(include), "include_total_degree": total_degree, "topic_nodes": len(ex.topics), "institution_nodes": len(ex.institutions),
              "has_topic_works": len(ex.has_topic), "affiliated_with_researchers": len(ex.affiliated)}
    return questions, include, counts


RULE = {
    "types": list(TYPES), "per_type": 3, "total": 33, "band": list(BAND), "hub_band": list(HUB_BAND),
    "eligible": "unique normalized name, ASCII letters/space/hyphen/apostrophe, 3..60 chars, researcher:<source>:<key> id",
    "pick": "candidates sorted by id (pairs by (id_a, id_b)); start = int(sha256(seed|slot)[:8],16) mod n; first unused candidate cyclically",
    "windows_stored": list(g.WINDOWS),
    "thin_data": "topic and institution questions: the export has 3 TOPIC nodes on one work with no AUTHORED edge and 1 INSTITUTION node with 0 AFFILIATED_WITH edges, so the expected outcome is a verified abstention",
    "evidence_type": "explain form (SemanticExplanation) naming one researcher; also every question is scored on its evidence trail",
    "planner_routes": {"fallback": "accepted by the deterministic QueryPlannerAgent fallback grammar", "llm": "needs the planner LLM (temporal, community comparison and named explain are not in the fallback grammar)"},
}


def render(export, run_id, seed, questions, include, counts):
    outputs = {
        "questions.txt": "".join(q["question"] + "\n" for q in questions),
        "include-ids.txt": "".join(x + "\n" for x in include),
        "question-specs.json": json.dumps({"schema": SPECS_SCHEMA, "run_id": run_id, "seed": seed, "questions": questions}, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
    }
    listing = "".join("%s  %s\n" % (sha, rel) for rel, sha in export.files_read)
    outputs["provenance.json"] = json.dumps({
        "schema": SCHEMA, "tool": "experiments/scripts/derive_q12_inputs.py",
        "source": {"run_id": run_id, "format": "Phase 6 Spark export, neptune-opencypher-csv sidecar (plain CSV)", "files_read": len(export.files_read),
                   "files_read_listing_sha256": g.sha256_text(listing), "files_read_sha256": dict(export.files_read)},
        "seed": seed, "rule": RULE, "counts": counts,
        "types": {kind: [q["id"] for q in questions if q["type"] == kind] for kind in TYPES},
        "outputs": {name: {"lines": text.count("\n"), "sha256": g.sha256_text(text)} for name, text in sorted(outputs.items()) if name != "provenance.json"},
        "note": "IDs, DBLP author names, topic and institution names and fixed question text only; DBLP is public (CC0). No credential, account or host value.",
    }, indent=2, sort_keys=True) + "\n"
    return outputs


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export-dir", required=True, help="completed Phase 6 Spark export run directory (read only)")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--degree-budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        ex = g.Export(args.export_dir)
        questions, include, counts = build(ex, args.seed, args.degree_budget)
        outputs = render(ex, ex.run_id, args.seed, questions, include, counts)
        out_dir = os.path.abspath(args.out_dir)
        if not args.overwrite:
            for name in outputs:
                if os.path.lexists(os.path.join(out_dir, name)):
                    raise Refused("%s exists (use --overwrite)" % name)
        os.makedirs(out_dir, exist_ok=True)
        for name, text in sorted(outputs.items()):
            with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            print("WROTE %s lines=%d sha256=%s" % (name, text.count("\n"), g.sha256_text(text)))
    except Refused as error:
        print("DERIVE-REFUSED: %s" % error)
        return 1
    except (OSError, ValueError, KeyError) as error:
        print("DERIVE-REFUSED: %s: %s" % (type(error).__name__, error))
        return 1
    print("RESULT: OK run=%s questions=%d include_ids=%d" % (ex.run_id, counts["questions"], counts["include_ids"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

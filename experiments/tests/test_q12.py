#!/usr/bin/env python3
"""Tests for experiments/scripts/q12_graph.py, derive_q12_inputs.py, q12_answer_key.py and q12_score.py (offline, stdlib) and the committed
experiments/inputs/q12 files.

Run from the repository root:   python3 -I -m unittest discover -s experiments/tests -v

Two fixtures, both hand-built; every expected value below is derived by hand from the algorithm in q12_graph.py's docstring, not by running the code.

Small export (ids a1<a2<a3<b1<b2<b3, all one source), windows all-years, 2010-2014, 2015-2019:
  all-years   barbell: triangle a1-a2-a3, triangle b1-b2-b3, bridge a3-b1 (every edge joint 1)
  2010-2014   path a1-a2-a3          2015-2019   triangle a1-a2-a3 plus a3-b1
  works       w1 {a1,a2,a3}  w2 {a1,a2,a3,b1}  w3 {b1,b2,b3}
Hand derivation, synchronous label propagation (ties to the smallest label):
  triangle b1..b3 alone, all-years barbell: iteration 1 a1->a2 a2->a1 a3->a1 b1->a3 b2->b1 b3->b1; iteration 2 a-side all a1, b1->b1 b2->a3 b3->a3;
  iteration 3 b1->a3; iteration 4 nothing changes. Final labels a1,a2,a3 = a1 and b1,b2,b3 = a3; 4 iterations, converged.
  2010-2014 path: iteration 1 a1=a2 a2=a1 a3=a2, iteration 2 a1=a1 a2=a2 a3=a1, then it oscillates with period 2; after 20 iterations the state is
  that of iteration 2 (a1=a1 a2=a2 a3=a1), all 3 labels changed in the last iteration, not converged.
  2015-2019: iteration 1 a1=a2 a2=a1 a3=a1 b1=a3, iteration 2 all a1, iteration 3 no change: 3 iterations, one community of 4.
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, relative))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


g = load("q12_graph_under_test", "experiments/scripts/q12_graph.py")
derive = load("derive_q12_under_test", "experiments/scripts/derive_q12_inputs.py")
keymod = load("q12_key_under_test", "experiments/scripts/q12_answer_key.py")
score = load("q12_score_under_test", "experiments/scripts/q12_score.py")
RUN = "run:00000000-0000-4000-8000-0000000000b1"
R = lambda n: "researcher:dblp:%s" % n
A1, A2, A3, B1, B2, B3 = (R(x) for x in ("a1", "a2", "a3", "b1", "b2", "b3"))
NAMES = {A1: "Ann One", A2: "Bob Two", A3: "Cat Three", B1: "Dan Four", B2: "Eve Five", B3: "Fay Six"}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def build_export(root, names, authored, edges, topics=(), institutions=()):
    """edges: {window: [(a, b, joint)]}; authored: {work: [researcher]}."""
    data = os.path.join(root, "neptune-opencypher-csv", "data")
    write(os.path.join(root, "run-manifest.json"), json.dumps({"runId": RUN}))
    rows = [":ID,:LABEL,label:String"] + ["%s,RESEARCHER,%s" % (r, n) for r, n in sorted(names.items())]
    rows += ["%s,WORK,Work %s" % (w, w) for w in sorted(authored)]
    rows += ["topic:t%d,TOPIC,%s" % (i, t) for i, t in enumerate(topics)] + ["institution:i%d,INSTITUTION,%s" % (i, t) for i, t in enumerate(institutions)]
    write(os.path.join(data, "nodes", "part-00000.csv"), "\n".join(rows) + "\n")
    lines = [":ID,:START_ID,:END_ID,:TYPE"] + ["ge:%s:%s,%s,%s,AUTHORED" % (w, r, r, w) for w, people in sorted(authored.items()) for r in people]
    write(os.path.join(data, "graph-edges", "part-00000.csv"), "\n".join(lines) + "\n")
    out = [":ID,:START_ID,:END_ID,:TYPE,jointPublicationCount:Long,windowId:String,evidenceEdgeId:String"]
    for window, items in sorted(edges.items()):
        for a, b, joint in items:
            out.append("e,%s,%s,COAUTHORED_WITH,%d,%s,edge:%s:%s:%s" % (a, b, joint, window, window, a[-6:], b[-6:]))
    write(os.path.join(data, "coauthor-edges", "part-00000.csv"), "\n".join(out) + "\n")


def small_export(root):
    build_export(root, NAMES, {"w1": [A1, A2, A3], "w2": [A1, A2, A3, B1], "w3": [B1, B2, B3]}, {
        "all-years": [(A1, A2, 1), (A1, A3, 1), (A2, A3, 1), (B1, B2, 1), (B1, B3, 1), (B2, B3, 1), (A3, B1, 1)],
        "2010-2014": [(A1, A2, 1), (A2, A3, 1)],
        "2015-2019": [(A1, A2, 1), (A1, A3, 1), (A2, A3, 1), (A3, B1, 1)],
    }, topics=("Topic One",), institutions=("Inst One",))


class GraphTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="q12-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "export")
        small_export(self.root)
        self.ex = g.Export(self.root)

    def test_components_degrees_and_ids(self):
        wg = self.ex.window("all-years")
        label_of, members = wg.components()
        self.assertEqual(members, {A1: [A1, A2, A3, B1, B2, B3]})  # the bridge joins both triangles: one component of 6
        self.assertEqual([wg.degree(x) for x in (A1, A3, B1)], [2, 3, 3])
        self.assertEqual(self.ex.window("2010-2014").component_size(A2), 3)
        expected = g.sha256_text("graph-v1\nall-years\n" + A1)  # StableIds.sparkAnalyticsId: sha256 of policy, window, label joined by newline
        self.assertEqual(g.analytics_id("component", "all-years", A1), "component:" + expected)

    def test_shortest_paths_hand_derived(self):
        wg = self.ex.window("all-years")
        hops, count, paths = wg.shortest_paths(A1, B3)   # a1-a3-b1-b3: 3 hops, the only shortest path
        self.assertEqual((hops, count, paths), (3, 1, [[A1, A3, B1, B3]]))
        self.assertEqual(wg.shortest_paths(A1, A3)[0], 1)
        self.assertEqual(wg.shortest_paths(A1, B3, max_depth=2)[0], None)   # beyond maxPathDepth: no path within the limit
        self.assertEqual(self.ex.window("2010-2014").shortest_paths(A1, B1)[0], None)   # b1 has no edge in that window

    def test_label_propagation_converges_on_the_barbell(self):
        label, iterations, changed, converged = self.ex.window("all-years").communities()
        self.assertEqual((iterations, changed, converged), (4, 0, True))
        self.assertEqual({x: label[x] for x in (A1, A2, A3, B1, B2, B3)}, {A1: A1, A2: A1, A3: A1, B1: A3, B2: A3, B3: A3})

    def test_label_propagation_oscillates_on_the_path(self):
        label, iterations, changed, converged = self.ex.window("2010-2014").communities()
        self.assertEqual((iterations, changed, converged), (20, 3, False))
        self.assertEqual({x: label[x] for x in (A1, A2, A3)}, {A1: A1, A2: A2, A3: A1})

    def test_bridges_hand_derived(self):
        bridges = self.ex.window("all-years").bridges()
        # a3: neighbours a1 a2 (own community) and b1 (other, joint 1): cross degree 1, cross weight 1, 1 community, 1 - (2^2 + 1^2) / 3^2 = 4/9
        self.assertEqual(bridges[A3]["crossCommunityDegree"], 1)
        self.assertEqual(bridges[A3]["crossCommunityWeight"], 1)
        self.assertEqual(bridges[A3]["communitiesConnected"], 1)
        self.assertAlmostEqual(bridges[A3]["participationCoefficient"], 4 / 9)
        self.assertEqual(bridges[A1], {"crossCommunityDegree": 0, "crossCommunityWeight": 0, "communitiesConnected": 0, "participationCoefficient": 0.0, "degree": 2})

    def test_team_sizes(self):
        sizes = g.team_sizes(self.ex)
        self.assertEqual(sizes, {"w1": 3, "w2": 4, "w3": 3})
        self.assertEqual(g.max_team(self.ex, A1, sizes), (3, ["w2"]))   # a1 is on w1 (2 coauthors) and w2 (3 coauthors)
        self.assertEqual(g.max_team(self.ex, B2, sizes), (2, ["w3"]))

    def test_missing_manifest_is_refused(self):
        os.remove(os.path.join(self.root, "run-manifest.json"))
        with self.assertRaises(g.Refused):
            g.Export(self.root)


class KeyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="q12-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "export")
        small_export(self.root)
        self.ex = g.Export(self.root)
        self.sizes = g.team_sizes(self.ex)

    def key(self, kind, window="all-years", **params):
        spec = {"id": "q99", "type": kind, "slot": "s", "question": "Q?", "planner": "fallback", "params": dict(params, window=window)}
        return keymod.key_for(spec, self.ex, self.sizes)

    def person(self, r):
        return {"id": r, "name": NAMES[r]}

    def test_direct_collab(self):
        k = self.key("direct_collab", researcher=self.person(A3))
        e = k["expected"]
        self.assertEqual((e["total"], e["truncated"]), (3, False))
        self.assertEqual([c["id"] for c in e["coauthors"]], [A1, A2, B1])   # equal joint publications: by id
        self.assertEqual(k["required_text"]["numbers"], [[[3]]])

    def test_shortest_path(self):
        k = self.key("shortest_path", a=self.person(A1), b=self.person(B3))
        self.assertEqual((k["expected"]["hops"], k["expected"]["shortest_path_count"]), (3, 1))
        self.assertEqual(k["required_text"]["path_names_any_of"], [["Cat Three", "Dan Four"]])

    def test_component_community_and_temporal(self):
        self.assertEqual(self.key("component", researcher=self.person(A2))["expected"]["size"], 6)
        c = self.key("community", researcher=self.person(A3))["expected"]
        self.assertEqual((c["size"], c["converged"], c["members"], c["cross_community_edge_count"]), (3, True, [A1, A2, A3], 1))
        self.assertEqual(c["community_id"], g.analytics_id("community", "all-years", A1))
        self.assertEqual(c["neighbor_community_ids"], [g.analytics_id("community", "all-years", A3)])
        t = self.key("temporal", researcher=self.person(A3), **{"from": "2010-2014", "to": "2015-2019"})["expected"]
        # a3: 1 coauthor (a2) then 3 (a1 a2 b1); component 3 then 4 members; communities {a1,a3} then {a1,a2,a3,b1}: Jaccard 2 / (2 + 4 - 2) = 0.5
        self.assertEqual((t["deltaDistinctCoauthors"], t["deltaComponentSize"], t["communityJaccardOverlap"]), (2, 1, 0.5))
        self.assertEqual((t["enteredLargestComponent"], t["leftLargestComponent"]), (False, False))
        self.assertEqual((t["previousCommunityId"], t["currentCommunityId"]), (g.analytics_id("community", "2010-2014", A1), g.analytics_id("community", "2015-2019", A1)))

    def test_rankings(self):
        k = self.key("coauthor_breadth", metric="DISTINCT_COAUTHOR_COUNT")
        self.assertEqual([(e["id"], e["value"]) for e in k["expected"]["top"][:3]], [(A3, 3), (B1, 3), (A1, 2)])   # ties by id ascending
        k = self.key("max_team_size", metric="MAXIMUM_COAUTHORS_ON_ONE_PAPER")
        self.assertEqual([(e["id"], e["value"]) for e in k["expected"]["top"][:4]], [(A1, 3), (A2, 3), (A3, 3), (B1, 3)])
        self.assertEqual(k["expected"]["global_maximum"], 3)
        k = self.key("bridge", measure="CROSS_COMMUNITY_DEGREE")
        self.assertEqual([(e["id"], e["value"]) for e in k["expected"]["top"][:3]], [(A3, 1), (B1, 1), (A1, 0)])

    def test_thin_data_questions_expect_abstention(self):
        k = self.key("topic", topic="Topic One")
        self.assertEqual((k["check_level"], k["expected_outcome"]), ("abstain", "abstain"))
        self.assertIn("topic", k["expected"]["reason"])
        k = self.key("institution", institution="Inst One", metric="DISTINCT_COAUTHOR_COUNT")
        self.assertEqual(k["expected_outcome"], "abstain")


# a planner-grammar check: a Python port of the anchored fallback grammar of QueryPlannerAgent.fallback (QueryPlannerAgent.scala:100-160)
STORED = {"all-years", "through-2009", "2010-2014", "2015-2019", "2020-2026", "since-2015"}
FALLBACK = [re.compile(p, re.I) for p in (
    r'(?:what is the )?shortest (?:coauthor )?path between "([^"]+)" and "([^"]+)"', r'(?:who are the )?direct coauthors of "([^"]+)"',
    r'(?:what is the )?component (?:of|for) "([^"]+)"', r'(?:show|rank) (?:the )?strongest repeated collaboration(?:s)?')]
FALLBACK_NORMALISED = re.compile(
    r"(?:which researchers have the most|rank researchers by|researchers with the most) distinct coauthors|"
    r"(?:which researchers have the|rank researchers by) (?:largest|maximum) (?:author )?team size|"
    r"(?:which researchers are the strongest bridges|rank bridge researchers)")


def fallback_accepts(question):
    remaining = question.strip().rstrip("?").strip()
    remaining = re.sub(r'(?i)\b(topic|institution|venue)\s+"([^"]+)"', "", remaining).strip()
    remaining = re.sub(r"\s+", " ", remaining)
    since = re.search(r"(?i)\s+since ([0-9]{4})$", remaining)
    if since:
        if since.group(1) != "2015":
            return False
        remaining = remaining[:since.start()].strip()
    window = re.search(r"(?i)\s+(?:in window|window) ([a-z0-9-]+)$", remaining)
    if window:
        if window.group(1) not in STORED:
            return False
        remaining = remaining[:window.start()].strip()
    if any(p.fullmatch(remaining) for p in FALLBACK):
        return True
    return bool(FALLBACK_NORMALISED.fullmatch(" ".join(remaining.lower().split())))


def nm(i):
    return "Zed%s%s Quux%s%s" % (chr(97 + i // 26), chr(97 + i % 26), chr(97 + i // 26), chr(97 + i % 26))


def synthetic_export(root):
    """15 cliques of 14 researchers (12 chained into one giant component, 3 isolated), a hub with 30 coauthors, 3 works per clique; every edge in every window."""
    names, authored, edges = {}, {}, []
    cliques = [[R("c%02d-%02d" % (c, m)) for m in range(14)] for c in range(15)]
    index = 0
    for clique in cliques:
        for r in clique:
            names[r] = nm(index)
            index += 1
    hub = R("hub")
    names[hub] = nm(index)
    for c, clique in enumerate(cliques):
        for i, a in enumerate(clique):
            for b in clique[i + 1:]:
                edges.append((a, b, 2))
        for w in range(3):
            authored["w-%02d-%d" % (c, w)] = list(clique)
    for c in range(11):
        edges.append((cliques[c][0], cliques[c + 1][1], 1))
    for member in [cliques[c][m] for c in range(12) for m in (2, 3, 4)][:30]:
        edges.append((hub, member, 1))
    build_export(root, names, authored, {w: edges for w in sorted(STORED)}, topics=("Alpha Topic", "Beta Topic"), institutions=("Gamma Institute",))


class DeriveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="q12-derive-")
        cls.root = os.path.join(cls.tmp, "export")
        synthetic_export(cls.root)
        cls.out = os.path.join(cls.tmp, "out")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cls.rc = derive.main(["--export-dir", cls.root, "--out-dir", cls.out])
        cls.stdout = out.getvalue()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def read(self, name):
        with open(os.path.join(self.out, name), encoding="utf-8") as handle:
            return handle.read()

    def test_writes_33_distinct_questions_three_per_type(self):
        self.assertEqual(self.rc, 0, self.stdout)
        questions = self.read("questions.txt").splitlines()
        self.assertEqual((len(questions), len(set(questions))), (33, 33))
        specs = json.loads(self.read("question-specs.json"))["questions"]
        self.assertEqual([q["question"] for q in specs], questions)
        self.assertEqual([q["id"] for q in specs], ["q%02d" % i for i in range(1, 34)])
        for kind in derive.TYPES:
            self.assertEqual(sum(1 for q in specs if q["type"] == kind), 3, kind)

    def test_fallback_questions_are_in_the_planner_grammar(self):
        for q in json.loads(self.read("question-specs.json"))["questions"]:
            if q["planner"] == "fallback":
                self.assertTrue(fallback_accepts(q["question"]), q["question"])
            else:
                self.assertFalse(fallback_accepts(q["question"]), "an LLM-route question is not in the fallback grammar: " + q["question"])
        planners = [q["planner"] for q in json.loads(self.read("question-specs.json"))["questions"]]
        self.assertEqual((planners.count("fallback"), planners.count("llm")), (24, 9))

    def test_named_researchers_are_in_the_include_list_and_budget(self):
        specs = json.loads(self.read("question-specs.json"))["questions"]
        include = self.read("include-ids.txt").splitlines()
        self.assertEqual(include, sorted(set(include)))
        named = set()
        for q in specs:
            for key in ("researcher", "a", "b"):
                if key in q["params"]:
                    named.add(q["params"][key]["id"])
        self.assertEqual(len(named), 21)   # 3 direct + 6 path endpoints + 3 component + 3 community + 3 temporal + 3 evidence, all distinct
        self.assertTrue(named <= set(include))
        self.assertIn(len(include), (len(named), len(named) + 1))   # plus the middle researcher of the 3-hop path unless it is already named

    def test_distance_and_degree_rules(self):
        ex = g.Export(self.root)
        specs = {q["slot"]: q for q in json.loads(self.read("question-specs.json"))["questions"]}
        hub = specs["direct-hub"]["params"]["researcher"]["id"]
        self.assertEqual(ex.window("all-years").degree(hub), 30)   # 26..35: the 25-row page is truncated
        for slot, hops in (("path-1", 1), ("path-2", 2), ("path-3", 3)):
            p = specs[slot]["params"]
            self.assertEqual(ex.window(p["window"]).shortest_paths(p["a"]["id"], p["b"]["id"])[0], hops, slot)
        for slot in ("component-through-2009", "component-since-2015"):
            wg = ex.window(specs[slot]["params"]["window"])
            r = specs[slot]["params"]["researcher"]["id"]
            self.assertGreaterEqual(wg.component_size(r), 12)
            self.assertLess(wg.component_size(r), 200)   # not the giant component (12 chained cliques = 168 + the hub)

    def test_thin_data_is_recorded(self):
        prov = json.loads(self.read("provenance.json"))
        self.assertEqual(prov["source"]["run_id"], RUN)
        self.assertEqual(prov["seed"], "q12-v1")
        self.assertEqual((prov["counts"]["topic_nodes"], prov["counts"]["institution_nodes"]), (2, 1))
        self.assertIn("verified abstention", prov["rule"]["thin_data"])
        self.assertEqual(sorted(prov["types"]), sorted(derive.TYPES))
        for name in ("questions.txt", "include-ids.txt", "question-specs.json"):
            self.assertEqual(prov["outputs"][name]["sha256"], g.sha256_text(self.read(name)))

    def test_deterministic_overwrite_seed_and_budget(self):
        second = os.path.join(self.tmp, "second")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(derive.main(["--export-dir", self.root, "--out-dir", second]), 0)
        for name in ("questions.txt", "include-ids.txt", "question-specs.json", "provenance.json"):
            with open(os.path.join(second, name), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), self.read(name), name)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(derive.main(["--export-dir", self.root, "--out-dir", second]), 1)
        self.assertIn("exists (use --overwrite)", out.getvalue())
        other = os.path.join(self.tmp, "other-seed")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(derive.main(["--export-dir", self.root, "--out-dir", other, "--seed", "another"]), 0)
        with open(os.path.join(other, "questions.txt"), encoding="utf-8") as handle:
            self.assertNotEqual(handle.read(), self.read("questions.txt"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(derive.main(["--export-dir", self.root, "--out-dir", os.path.join(self.tmp, "tight"), "--degree-budget", "50"]), 1)
        self.assertIn("above the --degree-budget 50", out.getvalue())
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "tight")))

    def test_a_directory_that_is_not_an_export_is_refused(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(derive.main(["--export-dir", self.tmp, "--out-dir", os.path.join(self.tmp, "nope")]), 1)
        self.assertIn("not a Phase 6 Spark export", out.getvalue())


class ScoreTest(unittest.TestCase):
    """Synthetic raw answers against a key computed from the small export. Each case states what must fail and why."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="q12-score-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "export")
        small_export(self.root)
        self.ex = g.Export(self.root)
        self.sizes = g.team_sizes(self.ex)
        self.deep = score.Deep(g, self.ex)

    def q(self, kind, window="all-years", **params):
        spec = {"id": "q01", "type": kind, "slot": "s", "question": "Q for %s?" % kind, "planner": "fallback", "params": dict(params, window=window)}
        return keymod.key_for(spec, self.ex, self.sizes)

    @staticmethod
    def item(evidence_id, kind, subjects, windows, **fields):
        values = [{"field": "kind", "text": kind}]
        for name, value in fields.items():
            if isinstance(value, bool):
                values.append({"field": name, "flag": value})
            elif isinstance(value, (int, float)):
                values.append({"field": name, "number": repr(value) if isinstance(value, float) else str(value)})
            elif isinstance(value, list):
                values.append({"field": name, "ids": value})
            else:
                values.append({"field": name, "text": value})
        return {"evidenceId": evidence_id, "supportingContent": {"subjectIds": subjects, "windowIds": windows, "values": values}}

    def row(self, q, summary, items, claims=None, outcome="ANSWERED", attempted=1, verified=1, rejected=0, status=200, verdicts=None):
        claims = claims if claims is not None else [{"claimId": "claim:1", "evidenceIds": [i["evidenceId"] for i in items], "runtime": {"claimType": "METRIC", "subjectIds": [], "values": []}}]
        return {"qid": q["id"], "question": q["question"], "status": status, "job_state": None,
                "answer": {"answer": {"summary": summary}, "claims": claims, "queryId": "qry-1"} if status == 200 else None,
                "explain": {"status": 200, "body": {"outcome": outcome, "verificationStatus": "VERIFIED", "evidenceIds": [i["evidenceId"] for i in items],
                                                    "counters": {"attemptedClaims": attempted, "verifiedClaims": verified, "rejectedClaims": rejected},
                                                    "verification": verdicts if verdicts is not None else [{"claimId": "claim:1", "verdict": "VERIFIED"}]}},
                "evidence": {i["evidenceId"]: {"status": 200, "item": i} for i in items}}

    def test_component_answer_passes_all_three(self):
        q = self.q("component", researcher={"id": A2, "name": NAMES[A2]})
        comp = g.analytics_id("component", "all-years", A1)
        it = self.item("evidence:metric:1", "metrics", [A2], ["all-years"], distinctCoauthorCount=2, weightedDegree=2, componentId=comp)
        result = score.score_question(q, self.row(q, "Bob Two is in a component of 6 researchers.", [it]), self.deep)
        self.assertEqual((result["retrieval"]["pass"], result["claims"]["pass"], result["text"]["pass"], result["pass"]), (True, True, True, True), json.dumps(result, indent=1))

    def test_wrong_value_wrong_number_and_rejected_claim_fail(self):
        q = self.q("component", researcher={"id": A2, "name": NAMES[A2]})
        it = self.item("evidence:metric:1", "metrics", [A2], ["all-years"], distinctCoauthorCount=5, componentId="component:wrong")
        result = score.score_question(q, self.row(q, "Bob Two is in a component of 7 researchers.", [it], attempted=2, verified=1, rejected=1), self.deep)
        self.assertFalse(result["retrieval"]["pass"])
        self.assertTrue(any("componentId" in r for r in result["retrieval"]["reasons"]))
        self.assertTrue(any("distinctCoauthorCount 5.0 != 2" in r for r in result["retrieval"]["reasons"]), result["retrieval"]["reasons"])
        self.assertFalse(result["claims"]["pass"])
        self.assertIn("1 claims rejected", result["claims"]["reasons"])
        self.assertFalse(result["text"]["pass"])
        self.assertTrue(any("number alternatives" in r for r in result["text"]["reasons"]))

    def test_unresolvable_evidence_fails_retrieval(self):
        q = self.q("component", researcher={"id": A2, "name": NAMES[A2]})
        it = self.item("evidence:metric:1", "metrics", [A2], ["all-years"], componentId=g.analytics_id("component", "all-years", A1))
        row = self.row(q, "Bob Two: 6 researchers.", [it])
        row["evidence"]["evidence:metric:1"] = {"status": 404, "item": None}
        result = score.score_question(q, row, self.deep)
        self.assertFalse(result["retrieval"]["pass"])
        self.assertIn("1 of 1 cited evidence ids do not resolve", result["retrieval"]["reasons"])

    def test_abstention_is_correct_only_where_the_key_says_abstain(self):
        topic = self.q("topic", topic="Topic One")
        abstained = self.row(topic, "Insufficient verified evidence to answer.", [], claims=[], outcome="ABSTAINED", attempted=0, verified=0, verdicts=[])
        result = score.score_question(topic, abstained, self.deep)
        self.assertEqual((result["pass"], result["text"]["abstention_kind"]), (True, "verified-abstention"))
        refused = score.score_question(topic, {"qid": "q01", "question": topic["question"], "status": 422, "answer": None, "explain": None, "evidence": {}}, self.deep)
        self.assertEqual((refused["pass"], refused["text"]["abstention_kind"]), (True, "refused-4xx"))
        answered = self.row(topic, "A ranking.", [self.item("evidence:ranking:1", "ranking", [A1], ["all-years"], rank=1, rankingValue=2)],
                            claims=[{"claimId": "claim:1", "evidenceIds": ["evidence:ranking:1"], "runtime": {"claimType": "RANKING", "subjectIds": [A1], "values": []}}])
        self.assertFalse(score.score_question(topic, answered, self.deep)["pass"])
        comp = self.q("component", researcher={"id": A2, "name": NAMES[A2]})
        wrong = self.row(comp, "Insufficient verified evidence to answer.", [], claims=[], outcome="ABSTAINED", attempted=0, verified=0, verdicts=[])
        result = score.score_question(comp, wrong, self.deep)
        self.assertEqual((result["retrieval"]["pass"], result["claims"]["pass"], result["text"]["pass"], result["outcome_kind"]), (False, False, False, "abstained"))

    def test_ranking_checks_order_values_and_the_rank_one_text(self):
        q = self.q("coauthor_breadth", metric="DISTINCT_COAUTHOR_COUNT")
        first = self.item("evidence:ranking:1", "ranking", [A3], ["all-years"], rank=1, rankingValue=3, distinctCoauthorCount=3, weightedDegree=3)
        second = self.item("evidence:ranking:2", "ranking", [A1], ["all-years"], rank=2, rankingValue=2, distinctCoauthorCount=2, weightedDegree=2)
        claims = [{"claimId": "claim:1", "evidenceIds": [first["evidenceId"]], "runtime": {"claimType": "RANKING", "subjectIds": [A3], "values": [{"field": "distinctCoauthorCount", "number": "3"}]}}]
        row = self.row(q, "Cat Three has the most distinct coauthors: 3.", [first, second], claims=claims)
        result = score.score_question(q, row, self.deep)
        self.assertTrue(result["pass"], json.dumps(result, indent=1))
        self.assertTrue(result["ranking"]["corpus_top1_agrees"])
        bad = self.item("evidence:ranking:3", "ranking", [A3], ["all-years"], rank=3, rankingValue=3, distinctCoauthorCount=9)
        result = score.score_question(q, self.row(q, "Ann One has 2.", [first, second, bad], claims=claims), self.deep)
        self.assertFalse(result["retrieval"]["pass"])
        self.assertTrue(any("distinctCoauthorCount" in r for r in result["retrieval"]["reasons"]))
        self.assertFalse(result["text"]["pass"])

    def test_path_hops_and_names_in_text(self):
        q = self.q("shortest_path", a={"id": A1, "name": NAMES[A1]}, b={"id": B3, "name": NAMES[B3]})
        path = self.item("evidence:path:1", "path", [A1, A3, B1, B3], ["all-years"], pathStatus="Found", orderedResearcherIds=[A1, A3, B1, B3], hopCount=3)
        ok = score.score_question(q, self.row(q, "Ann One reaches Fay Six in three hops through Cat Three and Dan Four.", [path]), self.deep)
        self.assertTrue(ok["pass"], json.dumps(ok, indent=1))
        short = self.item("evidence:path:2", "path", [A1, B3], ["all-years"], pathStatus="Found", orderedResearcherIds=[A1, B3], hopCount=1)
        bad = score.score_question(q, self.row(q, "Ann One and Fay Six are direct coauthors.", [short]), self.deep)
        self.assertFalse(bad["retrieval"]["pass"])
        self.assertTrue(any("not coauthor edges" in r or "key says 3 hops" in r for r in bad["retrieval"]["reasons"]))
        self.assertFalse(bad["text"]["pass"])

    def test_without_the_export_the_deep_checks_are_reported_skipped(self):
        q = self.q("component", researcher={"id": A2, "name": NAMES[A2]})
        it = self.item("evidence:metric:1", "metrics", [A2], ["all-years"], componentId=g.analytics_id("component", "all-years", A1))
        result = score.score_question(q, self.row(q, "Bob Two: 6 researchers.", [it]), None)
        self.assertTrue(result["pass"])
        self.assertEqual(result["retrieval"]["deep"], "skipped (no --export-dir)")

    def test_main_writes_json_and_markdown(self):
        key = {"schema": keymod.SCHEMA, "source": {"run_id": RUN}, "questions": [self.q("component", researcher={"id": A2, "name": NAMES[A2]}), self.q("topic", topic="Topic One")]}
        key["questions"][1]["id"] = "q02"
        key_path = os.path.join(self.tmp, "key.json")
        with open(key_path, "w") as handle:
            json.dump(key, handle)
        raw = os.path.join(self.tmp, "raw")
        os.makedirs(raw)
        comp = self.item("evidence:metric:1", "metrics", [A2], ["all-years"], componentId=g.analytics_id("component", "all-years", A1))
        q1, q2 = key["questions"]
        rows = [self.row(q1, "Bob Two: 6 researchers.", [comp]),
                dict(self.row(q2, "Insufficient verified evidence to answer.", [], claims=[], outcome="ABSTAINED", attempted=0, verified=0, verdicts=[]), qid="q02")]
        with open(os.path.join(raw, "answers.jsonl"), "w") as handle:
            handle.write("".join(json.dumps(r) + "\n" for r in rows))
        out_json, out_md = os.path.join(self.tmp, "s.json"), os.path.join(self.tmp, "s.md")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = score.main(["--key", key_path, "--raw", raw, "--export-dir", self.root, "--out-json", out_json, "--out-md", out_md])
        self.assertEqual(rc, 0, out.getvalue())
        self.assertIn("SCORED questions=2 retrieval=2 claims=2 text=2 all=2 abstained_or_refused=1 deep_checks=export", out.getvalue())
        with open(out_md) as handle:
            md = handle.read()
        self.assertIn("| component | 1 | 1 | 1 | 1 | 1 | 0 |", md)
        self.assertIn("| topic | 1 | 1 | 1 | 1 | 1 | 1 |", md)
        wrong = os.path.join(self.tmp, "wrong-export")
        small_export(wrong)
        write(os.path.join(wrong, "run-manifest.json"), json.dumps({"runId": "run:other"}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = score.main(["--key", key_path, "--raw", raw, "--export-dir", wrong, "--out-json", out_json, "--out-md", out_md])
        self.assertEqual(rc, 1)
        self.assertIn("not the run the key was computed from", out.getvalue())


class CommittedInputsTest(unittest.TestCase):
    """The committed experiments/inputs/q12 files must stay consistent with each other and with the manifest."""

    def load(self, name):
        with open(os.path.join(REPO, "experiments", "inputs", "q12", name), encoding="utf-8") as handle:
            return handle.read()

    def test_questions_specs_key_provenance_and_manifest_agree(self):
        text = self.load("questions.txt")
        questions = text.splitlines()
        self.assertEqual((len(questions), len(set(questions))), (33, 33))
        specs = json.loads(self.load("question-specs.json"))["questions"]
        key = json.loads(self.load("answer-key.json"))
        prov = json.loads(self.load("provenance.json"))
        manifest = json.load(open(os.path.join(REPO, "experiments", "manifests", "q12-benchmark.json"), encoding="utf-8"))
        self.assertEqual([q["question"] for q in specs], questions)
        self.assertEqual([q["question"] for q in key["questions"]], questions)
        self.assertEqual(sorted({q["type"] for q in key["questions"]}), sorted(derive.TYPES))
        self.assertEqual(g.sha256_text(text), manifest["questions"]["sha256"])
        self.assertEqual(prov["outputs"]["questions.txt"]["sha256"], manifest["questions"]["sha256"])
        self.assertEqual(key["source"]["question_specs_sha256"], g.sha256_text(self.load("question-specs.json")))
        self.assertEqual(key["source"]["run_id"], manifest["source"]["export_run_id"])
        self.assertEqual(manifest["llm"]["answers"], 33)
        self.assertEqual(manifest["llm"]["bucket"], "16b")
        self.assertEqual(key["counts"]["by_check_level"], {"abstain": 6, "bounded": 2, "exact": 22, "structural": 3})

    def test_every_type_is_covered_and_thin_data_is_marked(self):
        key = json.loads(self.load("answer-key.json"))
        for kind in derive.TYPES:
            self.assertEqual(sum(1 for q in key["questions"] if q["type"] == kind), 3, kind)
        for q in key["questions"]:
            if q["type"] in ("topic", "institution"):
                self.assertEqual(q["expected_outcome"], "abstain")
                self.assertTrue(q["expected"]["thin_data"])
        include = self.load("include-ids.txt").splitlines()
        self.assertTrue(all(re.match(r"^researcher:dblp:[0-9a-f]{64}$", x) for x in include))

    def test_no_credential_account_or_host_value(self):
        for name in ("questions.txt", "include-ids.txt", "question-specs.json", "provenance.json", "answer-key.json"):
            body = self.load(name)
            self.assertNotRegex(body, r"(?<![0-9a-f])[0-9]{12}(?![0-9a-f])" if name == "provenance.json" else r"AKIA[0-9A-Z]{16}|sk-ant-")
            self.assertNotIn("/Users/", body)


if __name__ == "__main__":
    unittest.main()

"""Feature tests for the Phase 16 evaluation package, instance A (groups 1, 2, 4): experiments/scripts/eval16_identity.py, eval16_graph.py, eval16_answers.py and
the check_16_evaluation part of check_manifests.py. Fixture-based: every metric function runs on a small hand-computed input; the end-to-end tests read only
committed files (the Phase 5E evidence, the frozen Q12 raw copies and the committed results) and never touch the network, AWS or the untracked Spark export.

  python3 -I -m unittest discover -s experiments/tests
"""
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(REPO, "experiments", "scripts")


def load(name):
    spec = importlib.util.spec_from_file_location(name + "_under_test", os.path.join(SCRIPTS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ident = load("eval16_identity")
graph = load("eval16_graph")
ans = load("eval16_answers")
check = load("check_manifests")


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def item(gold, outcome, path="Scored", entity="Researcher", pair="p"):
    return {"pair": pair, "partition": "held-out", "role": "initial", "stratum": "s", "entity": entity, "gold": gold, "outcome": outcome, "path": path}


class WilsonInterval(unittest.TestCase):
    def test_known_values(self):
        low, high = ident.wilson(0, 10)
        self.assertEqual(low, 0.0)
        self.assertAlmostEqual(high, 0.27753, places=4)
        low, high = ident.wilson(5, 10)
        self.assertAlmostEqual(low, 0.23659, places=4)
        self.assertAlmostEqual(high, 0.76341, places=4)
        low, high = ident.wilson(57, 57)
        self.assertAlmostEqual(low, 0.93686, places=4)
        self.assertEqual(high, 1.0)

    def test_empty_denominator_is_undefined_not_zero(self):
        self.assertIsNone(ident.wilson(0, 0))
        p = ident.proportion(0, 0)
        self.assertEqual((p["value"], p["wilson95"]), (None, None))

    def test_the_three_scripts_agree(self):
        for k, n in ((0, 1), (1, 1), (3, 7), (50, 50), (122, 122)):
            self.assertEqual(ident.wilson(k, n), graph.wilson(k, n))
            self.assertEqual(ident.wilson(k, n), ans.wilson(k, n))

    def test_interval_contains_the_estimate_and_stays_in_unit_range(self):
        for n in (1, 2, 10, 200):
            for k in range(0, n + 1, max(1, n // 5)):
                low, high = ident.wilson(k, n)
                self.assertTrue(0.0 <= low <= k / n <= high <= 1.0)


class ConfusionMetrics(unittest.TestCase):
    def test_classify_pair_table(self):
        self.assertEqual(ident.classify_pair("same", "ACCEPTED"), "tp")
        self.assertEqual(ident.classify_pair("same", "UNRESOLVED"), "fn")
        self.assertEqual(ident.classify_pair("different", "ACCEPTED"), "fp")
        self.assertEqual(ident.classify_pair("different", "CONFLICT"), "tn")
        self.assertEqual(ident.classify_pair("different", "REJECTED"), "tn")
        self.assertIsNone(ident.classify_pair("uncertain", "ACCEPTED"))
        self.assertIsNone(ident.classify_pair("missing", "ACCEPTED"))

    def test_matrix_rates_and_exclusion_of_uncertain(self):
        items = ([item("same", "ACCEPTED")] * 3 + [item("same", "UNRESOLVED")] + [item("different", "REJECTED")] * 2 + [item("different", "CONFLICT")] * 2
                 + [item("different", "ACCEPTED")] + [item("uncertain", "ACCEPTED"), item("missing", "ACCEPTED")])
        m = ident.confusion(items)
        self.assertEqual((m["tp"], m["fp"], m["fn"], m["tn"]), (3, 1, 1, 4))
        self.assertEqual((m["binary"], m["uncertain"], m["tasks"]), (9, 1, 11))
        self.assertEqual((m["precision"]["k"], m["precision"]["n"]), (3, 4))
        self.assertEqual((m["recall"]["k"], m["recall"]["n"]), (3, 4))
        self.assertAlmostEqual(m["f1"]["value"], 6 / 8)
        self.assertEqual((m["accuracy"]["k"], m["accuracy"]["n"]), (7, 9))
        # decisive = ACCEPTED or REJECTED among binary: 3 + 2 + 1 = 6 of 9
        self.assertEqual((m["decisive_coverage"]["k"], m["decisive_coverage"]["n"]), (6, 9))
        self.assertEqual((m["unresolved_rate"]["k"], m["conflict_rate"]["k"]), (1, 2))
        self.assertEqual(m["outcome_by_gold"]["uncertain"]["ACCEPTED"], 1)

    def test_undefined_ratios_are_null(self):
        m = ident.confusion([item("different", "CONFLICT")] * 3)
        self.assertEqual((m["tp"], m["fp"], m["fn"], m["tn"]), (0, 0, 0, 3))
        self.assertIsNone(m["precision"]["value"])
        self.assertIsNone(m["recall"]["value"])
        self.assertIsNone(m["f1"]["value"])
        self.assertEqual(m["false_merge_rate"]["n"], 3)
        self.assertIsNone(ident.confusion([])["accuracy"]["value"])

    def test_bootstrap_is_seeded_and_bounded(self):
        items = [item("same", "ACCEPTED")] * 8 + [item("same", "UNRESOLVED")] * 2 + [item("different", "REJECTED")] * 10
        a, b = ident.bootstrap_f1(items), ident.bootstrap_f1(items)
        self.assertEqual(a, b)
        self.assertTrue(0.0 <= a["low"] <= ident.f1_of(8, 0, 2) <= a["high"] <= 1.0)
        self.assertIsNone(ident.bootstrap_f1([item("uncertain", "ACCEPTED")]))

    def test_bootstrap_percentile_indexes_are_symmetric(self):
        for n in (2, 3, 10, 99, 1999, 2000):
            self.assertEqual(ident.percentile_index(n, 0.025) + ident.percentile_index(n, 0.975), n - 1, n)

    def test_interpretation_wording_follows_the_numbers(self):
        clean = ident.block([item("same", "ACCEPTED", "ExactIdentifier")] * 3 + [item("same", "UNRESOLVED", "Scored")] + [item("different", "REJECTED", "Scored")] * 2)
        text = " ".join(ident.interpretation({"held-out": clean}))
        self.assertIn("favours precision", text)
        self.assertIn("Scored 1", text)
        wrong = ident.block([item("same", "ACCEPTED", "Scored"), item("different", "ACCEPTED", "Scored")])
        self.assertNotIn("favours precision", " ".join(ident.interpretation({"held-out": wrong})))

    def test_groups_split_by_path_and_entity(self):
        items = [item("same", "ACCEPTED", "ExactIdentifier", "Work"), item("same", "UNRESOLVED", "Scored", "Researcher"), item("different", "CONFLICT", "HardConflict", "Work")]
        by = ident.group_by(items, lambda i: i["path"])
        self.assertEqual(sorted(by), ["ExactIdentifier", "HardConflict", "Scored"])
        self.assertEqual(by["Scored"]["fn"], 1)
        self.assertEqual(ident.group_by(items, lambda i: i["entity"])["Work"]["tasks"], 2)

    def test_build_items_marks_missing_prediction_and_label(self):
        queue = {"tasks": [{"pair": {"pairId": "a", "entityType": "Work"}, "partition": "held-out", "role": "initial", "stratum": "x"},
                           {"pair": {"pairId": "b", "entityType": "Work"}, "partition": "held-out", "role": "reserve", "stratum": "x"}]}
        labels = {"current": [{"pairId": "a", "label": "same"}]}
        predictions = {"rows": [{"pairId": "b", "outcome": "ACCEPTED", "path": "Scored"}]}
        items = ident.build_items(queue, labels, predictions)
        self.assertEqual((items[0]["gold"], items[0]["outcome"], items[0]["path"]), ("same", "MISSING", "MISSING"))
        self.assertEqual(items[1]["gold"], "missing")
        self.assertEqual([i["pair"] for i in ident.slice_items(items, "held-out")], ["a"])   # reserves are never in the initial slice
        self.assertEqual(ident.slice_items(items, "held-out", frozenset({"a"})), [])         # the assisted mask removes pairs

    def test_cross_check_flags_a_disagreement(self):
        m = ident.confusion([item("same", "ACCEPTED"), item("different", "REJECTED")])
        evaluator = {"overall": {"tp": 1, "fp": 0, "fn": 0, "tn": 1, "binaryGold": 2, "uncertain": 0}}
        rows = ident.cross_check(m, evaluator, {"tp": 1, "fp": 0, "fn": 0, "tn": 1})
        self.assertTrue(all(r["evaluator_agrees"] for r in rows))
        evaluator["overall"]["tp"] = 2
        rows = ident.cross_check(m, evaluator, {"tp": 1})
        self.assertFalse(next(r for r in rows if r["field"] == "tp")["evaluator_agrees"])


class IdentityEndToEnd(unittest.TestCase):
    """Reads the committed Phase 5E evidence only; pins the observed 5E numbers as the cross-check, not as a source."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.rc = ident.main(["--out-dir", cls.tmp])
        with open(os.path.join(cls.tmp, "identity-metrics.json"), encoding="utf-8") as handle:
            cls.doc = json.load(handle)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_held_out_matrix_matches_the_5e_report(self):
        self.assertEqual(self.rc, 0)
        o = self.doc["slices"]["held-out"]["overall"]
        self.assertEqual((o["binary"], o["tp"], o["fp"], o["fn"], o["tn"]), (194, 57, 0, 15, 122))
        o = self.doc["slices"]["held-out without the 22 AI-assisted pairs"]["overall"]
        self.assertEqual((o["binary"], o["tp"], o["fp"], o["fn"], o["tn"]), (181, 51, 0, 8, 122))
        self.assertTrue(self.doc["cross_check"]["all_agree"])

    def test_output_is_deterministic(self):
        other = tempfile.mkdtemp()
        try:
            self.assertEqual(ident.main(["--out-dir", other]), 0)
            for name in ("identity-metrics.json", "identity-metrics.md"):
                self.assertEqual(sha256(os.path.join(other, name)), sha256(os.path.join(self.tmp, name)))
        finally:
            shutil.rmtree(other)

    def test_committed_result_equals_a_fresh_run(self):
        for name in ("identity-metrics.json", "identity-metrics.md"):
            self.assertEqual(sha256(os.path.join(REPO, "experiments", "results", "phase16", "identity", name)), sha256(os.path.join(self.tmp, name)), name)

    def test_gaps_and_threats_are_stated(self):
        self.assertTrue(any("blocking recall" in g["metric"] for g in self.doc["gaps"]))
        self.assertTrue(any("AI-assisted" in t for t in self.doc["threats_to_validity"]))


# graph fixtures -------------------------------------------------------------------------------------------------------------------
def tiny_model():
    nodes = [("r1", "RESEARCHER"), ("r2", "RESEARCHER"), ("r3", "RESEARCHER"), ("r4", "RESEARCHER"), ("w1", "WORK"), ("w2", "WORK"), ("w3", "WORK"), ("v1", "VENUE"),
             ("m1", "AUTHOR_MENTION"), ("m2", "AUTHOR_MENTION"), ("m3", "AUTHOR_MENTION"), ("m4", "AUTHOR_MENTION"), ("m5", "AUTHOR_MENTION")]
    edges = [("e1", "r1", "w1", "AUTHORED"), ("e2", "r2", "w1", "AUTHORED"), ("e3", "r1", "w2", "AUTHORED"), ("e4", "r2", "w2", "AUTHORED"), ("e5", "r3", "w3", "AUTHORED"),
             ("e6", "w1", "v1", "PUBLISHED_IN"), ("e7", "w2", "v1", "PUBLISHED_IN"), ("e8", "w3", "v1", "PUBLISHED_IN"),
             ("e9", "m1", "r1", "RESOLVES_TO"), ("e10", "m2", "r2", "RESOLVES_TO"), ("e11", "m3", "r3", "RESOLVES_TO"), ("e12", "m4", "r4", "RESOLVES_TO")]
    coauthor = [("c1", "r1", "r2", "all-years", 2, ("w1", "w2"), "c1"), ("c2", "r1", "r2", "2010-2014", 1, ("w1",), "c2")]
    return {"run_id": "run:x", "node_rows": nodes, "node_label": dict(nodes), "graph_edges": edges, "coauthor": coauthor, "run_id_in_context": {"graph_edges": 12, "coauthor_edges": 2}}


class GraphChecks(unittest.TestCase):
    def test_clean_graph_has_no_duplicates_or_dangling_edges(self):
        model = tiny_model()
        d = graph.duplicates(model)
        self.assertEqual([d[k]["k"] for k in ("node_ids", "graph_edge_ids", "graph_edge_type_start_end", "coauthor_edge_ids", "coauthor_pair_window", "coauthor_self_loops")], [0] * 6)
        ri = graph.referential_integrity(model)
        self.assertEqual(ri["graph_edges_total_with_unresolved_endpoint"]["k"], 0)
        self.assertEqual(ri["coauthor_edges_with_unresolved_endpoint"]["k"], 0)

    def test_duplicates_dangling_and_wrong_label_are_counted(self):
        model = tiny_model()
        model["node_rows"].append(("r1", "RESEARCHER"))                        # duplicate node id
        model["graph_edges"].append(("e1", "r1", "w1", "AUTHORED"))             # duplicate edge id and duplicate (type, start, end)
        model["graph_edges"].append(("e99", "r1", "ghost", "AUTHORED"))         # dangling end
        model["graph_edges"].append(("e98", "w1", "r1", "AUTHORED"))            # wrong labels (WORK -> RESEARCHER)
        model["coauthor"].append(("c3", "r2", "r1", "all-years", 2, ("w1", "w2"), "c3"))  # same pair and window reversed
        model["coauthor"].append(("c4", "r3", "r3", "all-years", 1, ("w3",), "c4"))      # self loop
        model["coauthor"].append(("c5", "r1", "nobody", "all-years", 1, ("w1",), "c5"))  # unresolved endpoint
        d = graph.duplicates(model)
        self.assertEqual(d["node_ids"]["k"], 1)
        self.assertEqual(d["graph_edge_ids"]["k"], 1)
        self.assertEqual(d["graph_edge_type_start_end"]["k"], 1)
        self.assertEqual(d["coauthor_pair_window"]["k"], 1)
        self.assertEqual(d["coauthor_self_loops"]["k"], 1)
        ri = graph.referential_integrity(model)
        self.assertEqual(ri["graph_edges_by_type"]["AUTHORED"]["with_unresolved_endpoint"]["k"], 1)
        self.assertEqual(ri["graph_edges_by_type"]["AUTHORED"]["with_wrong_endpoint_label"]["k"], 1)
        self.assertEqual(ri["coauthor_edges_with_unresolved_endpoint"]["k"], 1)

    def test_orphans(self):
        o = graph.orphans(tiny_model())
        self.assertEqual(o["AUTHOR_MENTION (no RESOLVES_TO edge)"]["k"], 1)   # m5 resolves nowhere
        self.assertEqual(o["RESEARCHER (no AUTHORED edge)"]["k"], 1)          # r4
        self.assertEqual(o["RESEARCHER (no coauthor edge in any window)"]["k"], 2)   # r3 and r4
        self.assertEqual(o["WORK (no AUTHORED edge)"]["k"], 0)
        self.assertEqual(o["WORK (no PUBLISHED_IN edge)"]["k"], 0)
        self.assertEqual(o["VENUE (no incident edge)"]["k"], 0)

    def test_support_and_recount(self):
        model = tiny_model()
        authored_by, mentions_of, venues = graph.authorship(model)
        s = graph.support_checks(model, authored_by)
        self.assertEqual(s["all_windows"]["fully_supported"]["k"], 2)
        self.assertEqual(s["all_years_joint_count_recount"]["matching"]["k"], 1)
        self.assertEqual(s["all_windows"]["window_joint_le_all_years"]["k"], 2)
        # break it: a support work the second endpoint did not author, a missing support list, a wrong stored joint count
        model["coauthor"] = [("c1", "r1", "r2", "all-years", 3, ("w1", "w2"), "c1"), ("c2", "r1", "r2", "2010-2014", 1, ("w3",), "c2"), ("c3", "r1", "r3", "2015-2019", 1, (), "c3")]
        s = graph.support_checks(model, authored_by)
        self.assertEqual(s["all_windows"]["with_support_work"]["k"], 2)
        self.assertEqual(s["all_windows"]["all_support_works_authored_by_both"]["k"], 1)
        self.assertEqual(s["all_windows"]["fully_supported"]["k"], 1)
        rc = s["all_years_joint_count_recount"]
        self.assertEqual((rc["matching"]["k"], rc["matching"]["n"]), (0, 1))
        self.assertEqual(rc["first_mismatches"][0], {"edge_id": "c1", "stored_joint": 3, "recount_from_authored": 2})
        self.assertEqual(s["all_windows"]["window_pair_in_all_years"]["k"], 2)    # r1-r3 has no all-years edge

    def test_provenance_audit_is_seeded_and_flags_a_broken_edge(self):
        model = tiny_model()
        authored_by, mentions_of, venues = graph.authorship(model)
        a = graph.provenance_audit(model, authored_by, mentions_of, 50)
        self.assertEqual(a["sample_size"], 2)
        self.assertEqual(a["fully_resolves"]["k"], 2)
        self.assertEqual(a, graph.provenance_audit(model, authored_by, mentions_of, 50))
        model["coauthor"][0] = ("c1", "r1", "r2", "all-years", 2, ("w1", "ghost"), "c1")
        a = graph.provenance_audit(model, authored_by, mentions_of, 50)
        self.assertEqual(a["fully_resolves"]["k"], 1)
        bad = next(t for t in a["traces"] if t["edge_id"] == "c1")
        self.assertFalse(bad["steps"]["support_works_are_work_nodes"])

    def test_sample_is_a_subset_of_a_fixed_seed(self):
        model = tiny_model()
        model["coauthor"] = [("c%03d" % i, "r1", "r2", "w%d" % i, 1, ("w1",), "c") for i in range(100)]
        authored_by, mentions_of, venues = graph.authorship(model)
        first = [t["edge_id"] for t in graph.provenance_audit(model, authored_by, mentions_of, 10)["traces"]]
        second = [t["edge_id"] for t in graph.provenance_audit(model, authored_by, mentions_of, 10, seed="another-seed")["traces"]]
        self.assertEqual(len(first), 10)
        self.assertEqual(first, [t["edge_id"] for t in graph.provenance_audit(model, authored_by, mentions_of, 10)["traces"]])
        self.assertNotEqual(first, second)

    def test_support_table_checks_with_joint_counts_above_the_cap(self):
        model = tiny_model()
        model["coauthor"] = [("c1", "r1", "r2", "all-years", 7, ("w1", "w2", "w3", "w4", "w5"), "c1"), ("c2", "r1", "r3", "all-years", 2, ("w1", "w2"), "c2"),
                             ("c3", "r2", "r3", "all-years", 12, ("w1", "w2", "w3", "w4", "w5"), "c3")]
        rows = {"datasets": {"nodes": len(model["node_rows"]), "graph-edges": len(model["graph_edges"]), "coauthor-edges": 3}, "source_tables": {"edges/type=coauthored_with_support": 21}}
        out = graph.manifest_cross_check(model, rows)
        self.assertEqual((out["sum_of_joint_publication_counts"], out["support_table_rows_equal_sum_of_joint_counts"]), (21, True))
        self.assertEqual((out["support_work_ids_stored_on_coauthor_rows"], out["sum_of_min_joint_and_cap"], out["stored_pairs_equal_sum_of_min_joint_and_cap"]), (12, 12, True))
        self.assertNotIn("equal", out)       # the old, misleading stored-vs-table comparison is gone
        rows["source_tables"]["edges/type=coauthored_with_support"] = 20
        self.assertFalse(graph.manifest_cross_check(model, rows)["support_table_rows_equal_sum_of_joint_counts"])
        model["coauthor"][0] = ("c1", "r1", "r2", "all-years", 7, ("w1", "w2"), "c1")        # a cap violation: 2 stored for joint 7
        self.assertFalse(graph.manifest_cross_check(model, rows)["stored_pairs_equal_sum_of_min_joint_and_cap"])

    def test_last_full_check_names_its_own_tree(self):
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, "docs", "agent-runs", "phase-15"))
            with open(os.path.join(tmp, graph.LAST_CHECK_FILE), "w", encoding="utf-8") as handle:
                handle.write("| old | `scripts/check.sh` on a detached worktree of 1111111 | RESULT: PASS gates=7 |\n| new | `scripts/check.sh` on a detached worktree of 9e881a2 plus the branch x tracked diff, JDK 17 | exit 0, `RESULT: PASS gates=7`. |\n")
            lc = graph.last_full_check(tmp)
            self.assertEqual(lc["line"], 2)
            self.assertIn("9e881a2", lc["tree"])
        finally:
            shutil.rmtree(tmp)

    def test_threat_text_uses_the_computed_audit(self):
        audit = {"sample_size": 7, "fully_resolves": graph.proportion(7, 7)}
        text = " ".join(graph.threats(audit, "run:abc"))
        self.assertIn("samples 7 coauthor rows", text)
        self.assertIn("run:abc", text)
        self.assertIn("7 of 7 resolved", text)

    def test_known_small_graph_test_listing(self):
        tmp = tempfile.mkdtemp()
        try:
            suite_dir = os.path.join(tmp, "modules", "spark", "src", "test", "scala", "pkg")
            os.makedirs(suite_dir)
            with open(os.path.join(suite_dir, "AGraphSpec.scala"), "w", encoding="utf-8") as handle:
                handle.write('class AGraphSpec extends AnyFunSuite {\n  test("module G1 has nine edges") {\n  }\n  test("quoted \\"name\\" works") {\n  }\n  // test("commented out") {\n}\n')
            listing = graph.spark_known_graph_tests(tmp)
            self.assertEqual((listing["suite_count"], listing["test_count"]), (1, 2))
            self.assertEqual(listing["suites"][0]["tests"], ["module G1 has nine edges", 'quoted "name" works'])
            self.assertIsNone(graph.spark_known_graph_tests(os.path.join(tmp, "nowhere")))
        finally:
            shutil.rmtree(tmp)

    def test_real_spark_suites_are_listed_with_names(self):
        listing = graph.spark_known_graph_tests(REPO)
        self.assertGreaterEqual(listing["suite_count"], 5)
        self.assertTrue(any("G1" in name for s in listing["suites"] for name in s["tests"]))


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


class GraphExportFixture(unittest.TestCase):
    """A tiny Phase 6 export written to a temporary directory: load, refuse and run end to end."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.export = os.path.join(self.tmp, "export")
        data = os.path.join(self.export, "neptune-opencypher-csv", "data")
        for sub in ("nodes", "graph-edges", "coauthor-edges"):
            os.makedirs(os.path.join(data, sub))
        with open(os.path.join(self.export, "run-manifest.json"), "w", encoding="utf-8") as handle:
            json.dump({"runId": "run:fixture"}, handle)
        ctx = '{"runId":"run:fixture"}'
        model = tiny_model()
        write_csv(os.path.join(data, "nodes", "part-0.csv"), [":ID", ":LABEL", "contextJson:String"], [(i, l, ctx) for i, l in model["node_rows"]])
        write_csv(os.path.join(data, "graph-edges", "part-0.csv"), [":ID", ":START_ID", ":END_ID", ":TYPE", "contextJson:String"], [(e, s, t, k, ctx) for e, s, t, k in model["graph_edges"]])
        write_csv(os.path.join(data, "coauthor-edges", "part-0.csv"),
                  [":ID", ":START_ID", ":END_ID", "windowId:String", "jointPublicationCount:Long", "representativeWorkIdsJson:String", "evidenceEdgeId:String", "contextJson:String"],
                  [(c[0], c[1], c[2], c[3], c[4], json.dumps(list(c[5])), c[6], ctx) for c in model["coauthor"]])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_load_and_end_to_end(self):
        out = os.path.join(self.tmp, "out")
        self.assertEqual(graph.main(["--export-dir", self.export, "--out-dir", out]), 0)
        with open(os.path.join(out, "graph-correctness.json"), encoding="utf-8") as handle:
            doc = json.load(handle)
        self.assertEqual(doc["counts"]["nodes_by_label"]["RESEARCHER"], 4)
        self.assertEqual(doc["support"]["all_windows"]["fully_supported"]["k"], 2)
        self.assertEqual(doc["counts"]["run_id_in_row_context"]["coauthor_edges"]["k"], 2)
        self.assertEqual(doc["export"]["run_id"], "run:fixture")
        self.assertTrue(all(len(f[2]) == 64 for f in doc["export"]["files"]))
        out2 = os.path.join(self.tmp, "out2")
        self.assertEqual(graph.main(["--export-dir", self.export, "--out-dir", out2]), 0)
        self.assertEqual(sha256(os.path.join(out, "graph-correctness.json")), sha256(os.path.join(out2, "graph-correctness.json")))

    def test_refuses_a_directory_that_is_not_an_export(self):
        os.remove(os.path.join(self.export, "run-manifest.json"))
        self.assertEqual(graph.main(["--export-dir", self.export, "--out-dir", os.path.join(self.tmp, "o")]), 1)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "o")))


# answers -------------------------------------------------------------------------------------------------------------------------
def row(qid, attempted, verified, rejected, verification_len=None, tokens=None):
    body = {"counters": {"attemptedClaims": attempted, "verifiedClaims": verified, "rejectedClaims": rejected},
            "verification": [{}] * (attempted if verification_len is None else verification_len)}
    if tokens:
        body["modelVersions"] = [{"inputTokens": tokens[0], "outputTokens": tokens[1]}]
    return {"qid": qid, "status": 200, "explain": {"body": body}}


class AnswerMetrics(unittest.TestCase):
    def test_claim_support(self):
        rows = [row("q1", 2, 2, 0), row("q2", 3, 2, 1), row("q3", 0, 0, 0), {"qid": "q4", "status": 422}]
        c = ans.claim_support(rows)
        self.assertEqual((c["claims_attempted"], c["claims_verified"], c["claims_rejected"]), (5, 4, 1))
        self.assertEqual((c["runtime_self_reported_verification_rate"]["k"], c["runtime_self_reported_verification_rate"]["n"]), (4, 5))
        self.assertEqual(c["questions_with_explain"], 3)              # the 422 row has no explain record
        self.assertEqual((c["questions_with_at_least_one_claim"], c["questions_with_all_claims_verified"]["k"]), (2, 1))
        self.assertEqual(ans.claim_support(rows, lambda r: r["qid"] == "q1")["claims_attempted"], 2)
        self.assertIsNone(ans.claim_support([])["runtime_self_reported_verification_rate"]["value"])

    def test_explain_list_length_mismatch_is_reported(self):
        self.assertEqual(ans.claim_support([row("q1", 2, 2, 0, verification_len=1)])["explain_list_length_differs_from_counter"], 1)

    def test_token_usage_and_cost_at_the_pinned_rates(self):
        t = ans.token_usage([row("q1", 1, 1, 0, tokens=(1000000, 1000000)), row("q2", 1, 1, 0), {"qid": "q3"}])
        self.assertEqual((t["synthesis_calls"], t["input_tokens"], t["output_tokens"], t["rows_with_model_usage"], t["rows_without"]), (1, 1000000, 1000000, 1, 2))
        self.assertAlmostEqual(ans.usd(1000000, 1000000), 0.60)
        self.assertAlmostEqual(ans.usd(235950, 42900), 0.045045, places=6)    # the pinned estimate in the run records

    def test_abstention_quality(self):
        def r(expected, kind, ok):
            return {"expected_outcome": expected, "outcome_kind": kind, "pass": ok}
        results = [r("abstain", "refused", True), r("abstain", "abstained", True), r("abstain", "answered", False), r("abstain", "error", False),
                   r("answer", "answered", True), r("answer", "abstained", False), r("answer", "refused", False), r("answer", "error", False)]
        a = ans.abstention_quality(results)
        self.assertEqual((a["correct_abstentions"]["k"], a["correct_abstentions"]["n"]), (2, 4))
        self.assertEqual((a["abstain_expected_but_answered"], a["abstain_expected_but_error"]), (1, 1))
        self.assertEqual((a["answer_expected_wrongly_abstained_or_refused"]["k"], a["answer_expected_wrongly_abstained_or_refused"]["n"]), (2, 4))
        self.assertEqual((a["answer_expected_wrongly_abstained"], a["answer_expected_wrongly_refused_422"], a["answer_expected_errors"], a["answer_expected_answered"]), (1, 1, 1, 1))

    def test_accuracy_blocks_and_contradictions(self):
        def r(kind, retrieval, claims, text, checked=0, mismatching=0):
            ok = retrieval and claims and text
            return {"expected_outcome": "answer", "outcome_kind": kind, "pass": ok, "retrieval": {"pass": retrieval}, "text": {"pass": text},
                    "claims": {"pass": claims, "verified_claims_checked": checked, "verified_claims_mismatching": mismatching}}
        results = [r("answered", True, True, True, 2), r("answered", True, False, False, 3, 1), r("abstained", False, False, False), r("answered", True, True, False, 1)]
        a = ans.accuracy_blocks(results)
        self.assertEqual((a["answer_expected_questions"], a["answered_questions"]), (4, 3))
        self.assertEqual((a["all_pass_of_answered"]["k"], a["all_pass_of_answered"]["n"]), (1, 3))
        self.assertEqual((a["all_pass_of_answer_expected"]["k"], a["all_pass_of_answer_expected"]["n"]), (1, 4))
        self.assertEqual((a["verified_claims_checked_against_export"], a["verified_claims_contradicting_key_or_export"]), (6, 1))
        self.assertEqual(a["contradiction_rate_of_verified_claims"]["n"], 6)

    def test_name_omission_counts_only_text_only_failures(self):
        def r(retrieval, claims, reasons):
            return {"expected_outcome": "answer", "outcome_kind": "answered", "retrieval": {"pass": retrieval}, "claims": {"pass": claims}, "text": {"pass": False, "reasons": reasons}}
        out = ans.name_omission([r(True, True, ["the rank-1 cited researcher 'X' does not appear"]), r(True, True, ["only 0 of 3 coauthor names appear"]),
                                 r(True, False, ["the rank-1 cited researcher 'X' does not appear"]), r(True, True, ["wrong hop count"])])
        # 4 failures: 3 carry a missing-name reason; only 2 carry nothing but missing-name reasons with retrieval and claims passing (the third has a failed claims check)
        self.assertEqual(out, {"answered_with_text_fail": 4, "with_a_missing_name_reason": 3, "every_text_reason_is_missing_name_and_retrieval_and_claims_pass": 2})
        mixed = ans.name_omission([r(True, True, ["the rank-1 cited researcher 'X' does not appear", "wrong hop count"])])
        self.assertEqual((mixed["with_a_missing_name_reason"], mixed["every_text_reason_is_missing_name_and_retrieval_and_claims_pass"]), (1, 0))

    def test_16b_classification_and_outcomes(self):
        self.assertEqual(ans.classify_16b('Who are the direct coauthors of "X"?'), "direct coauthors")
        self.assertEqual(ans.classify_16b('What is the component of "X"?'), "component")
        self.assertEqual(ans.classify_16b('What is the shortest coauthor path between "A" and "B"?'), "path")
        self.assertEqual(ans.classify_16b("Which researchers have the largest team size?"), "ranking")
        self.assertEqual(ans.classify_16b("Show the strongest repeated collaborations"), "ranking")
        ok = {"status": 200, "answer": {"answer": {"summary": "X: publications 4"}, "claims": [{}, {}]}, "question": "Which researchers have the most distinct coauthors?"}
        none = {"status": 200, "answer": {"answer": {"summary": "Insufficient verified evidence to answer."}, "claims": []}, "question": 'What is the component of "Y"?'}
        err = {"status": 422, "answer": None, "question": "Show the strongest repeated collaborations"}
        self.assertEqual([ans.outcome_16b(x) for x in (ok, none, err)], ["answered", "insufficient-evidence abstention", "error"])
        out = ans.analyse_16b([ok, none, err])
        self.assertEqual(out["by_type"]["ranking"]["answered"]["k"], 1)
        self.assertEqual(out["by_type"]["ranking"]["errors"], 1)
        self.assertEqual(out["by_type"]["ranking"]["claims_in_answers"], 2)
        self.assertEqual(out["by_type"]["component"]["insufficient_evidence_abstentions"], 1)


class RegenerationIsPathIndependent(unittest.TestCase):
    """Instance B's `eval16_repro.py --verify` regenerates into a temporary directory: the bytes must not depend on the out dir (repair round 1)."""

    def test_identity_output_is_identical_for_two_out_dirs(self):
        a, b = tempfile.mkdtemp(), os.path.join(tempfile.mkdtemp(), "deeper", "dir")
        try:
            self.assertEqual((ident.main(["--out-dir", a]), ident.main(["--out-dir", b])), (0, 0))
            for name in ("identity-metrics.json", "identity-metrics.md"):
                self.assertEqual(sha256(os.path.join(a, name)), sha256(os.path.join(b, name)), name)
        finally:
            shutil.rmtree(a)
            shutil.rmtree(os.path.dirname(os.path.dirname(b)))

    def test_graph_output_is_identical_for_two_out_dirs(self):
        fixture = GraphExportFixture("test_load_and_end_to_end")
        fixture.setUp()
        try:
            a, b = os.path.join(fixture.tmp, "one"), os.path.join(fixture.tmp, "x", "y", "two")
            self.assertEqual((graph.main(["--export-dir", fixture.export, "--out-dir", a]), graph.main(["--export-dir", fixture.export, "--out-dir", b])), (0, 0))
            for name in ("graph-correctness.json", "graph-correctness.md"):
                self.assertEqual(sha256(os.path.join(a, name)), sha256(os.path.join(b, name)), name)
        finally:
            fixture.tearDown()

    def test_answers_output_text_names_no_out_dir(self):
        # analyse() needs the untracked export for the scorer, so check the committed result instead: it must hold no repository-relative or absolute out-dir path
        with open(os.path.join(REPO, "experiments", "results", "phase16", "answers", "answer-quality.json"), encoding="utf-8") as handle:
            doc = json.load(handle)
        for run in ("q12-benchmark-q12-run-1", "q12-benchmark-q12-run-2"):
            for name in doc["q12"][run]["scorer_outputs"]:
                self.assertEqual(os.path.basename(name), name)
        with open(os.path.join(REPO, "experiments", "results", "phase16", "answers", "answer-quality.md"), encoding="utf-8") as handle:
            self.assertNotIn("experiments/results", handle.read().split("## Threats")[0].split("## Inputs")[1].replace("q12-raw", ""))


class FreezeAndVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src, self.dst = os.path.join(self.tmp, "src"), os.path.join(self.tmp, "dst")

    def tearDown(self):
        for base, dirs, names in os.walk(self.tmp):
            for name in names:
                os.chmod(os.path.join(base, name), 0o644)
        shutil.rmtree(self.tmp)

    def make_run(self, run, extra=b""):
        raw = os.path.join(self.src, run, "raw")
        os.makedirs(raw)
        answers = b'{"qid": "q01"}\n' + extra
        with open(os.path.join(raw, "answers.jsonl"), "wb") as handle:
            handle.write(answers)
        with open(os.path.join(raw, "run-record.json"), "wb") as handle:
            handle.write(b"{}")
        with open(os.path.join(raw, "events.jsonl"), "wb") as handle:
            handle.write(b"")
        with open(os.path.join(raw, "raw.sha256"), "w", encoding="utf-8") as handle:
            handle.write("%s  answers.jsonl\n" % hashlib.sha256(answers).hexdigest())

    def test_secret_patterns_are_detected_case_insensitively(self):
        os.makedirs(os.path.join(self.src, "r", "raw"))
        for text, key in ((b"Authorization: x", "Authorization"), (b"BEARER abc", "Bearer"), (b"X-API-KEY: z", "x-api-key"), (b"sk-ant-abc", "sk-ant")):
            with open(os.path.join(self.src, "r", "raw", "f"), "wb") as handle:
                handle.write(text)
            hits = ans.scan_secrets(os.path.join(self.src, "r", "raw"))
            self.assertEqual(hits[key], 1, key)
        with open(os.path.join(self.src, "r", "raw", "f"), "wb") as handle:
            handle.write(b"nothing here")
        self.assertEqual(sum(ans.scan_secrets(os.path.join(self.src, "r", "raw")).values()), 0)

    def test_freeze_copies_read_only_refuses_secret_runs_and_verifies(self):
        self.make_run(ans.RUNS[0])
        self.make_run(ans.RUNS[1], extra=b"Bearer abc123\n")
        self.assertEqual(ans.freeze(self.src, self.dst), 1)                      # one run refused
        self.assertTrue(os.path.isdir(os.path.join(self.dst, ans.RUNS[0])))
        self.assertFalse(os.path.exists(os.path.join(self.dst, ans.RUNS[1])))     # not copied
        mode = os.stat(os.path.join(self.dst, ans.RUNS[0], "answers.jsonl")).st_mode
        self.assertEqual(mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH), 0)
        self.assertEqual(ans.verify_frozen(self.dst), [])
        with open(os.path.join(self.dst, "freeze-report.json"), encoding="utf-8") as handle:
            report = json.load(handle)
        self.assertEqual(report["last_invocation"]["refused_for_secret_pattern"], [ans.RUNS[1]])
        self.assertFalse(report["first_freeze"]["recovered_from_observable_evidence"])
        self.assertEqual(len(report["first_freeze"]["source_files_sha256"]), 4)

    def test_tamper_is_detected_and_refreeze_never_overwrites(self):
        self.make_run(ans.RUNS[0])
        self.assertEqual(ans.freeze(self.src, self.dst), 0)
        target = os.path.join(self.dst, ans.RUNS[0], "answers.jsonl")
        os.chmod(target, 0o644)
        with open(target, "ab") as handle:
            handle.write(b"x")
        problems = ans.verify_frozen(self.dst)
        self.assertTrue(any("sha256 mismatch" in p for p in problems))
        self.assertEqual(ans.freeze(self.src, self.dst), 1)                      # the copy differs from the source: refused

    def test_unlisted_file_is_reported(self):
        self.make_run(ans.RUNS[0])
        ans.freeze(self.src, self.dst)
        with open(os.path.join(self.dst, ans.RUNS[0], "extra.txt"), "w", encoding="utf-8") as handle:
            handle.write("x")
        self.assertTrue(any("unlisted" in p for p in ans.verify_frozen(self.dst)))


class FrozenCopiesInTheRepository(unittest.TestCase):
    FROZEN = os.path.join(REPO, ans.FROZEN)

    def test_frozen_copies_match_sha256sums_and_each_runs_own_seal(self):
        self.assertEqual(ans.verify_frozen(self.FROZEN), [])

    def test_all_five_runs_are_present(self):
        # read-only mode (0444) is set by the freeze step, but git does not keep it in a fresh clone, so only presence is asserted here
        for run in ans.RUNS:
            for name in ans.RAW_FILES:
                self.assertTrue(os.path.isfile(os.path.join(self.FROZEN, run, name)), "%s/%s" % (run, name))

    def test_freeze_report_records_a_clean_secret_scan(self):
        with open(os.path.join(self.FROZEN, "freeze-report.json"), encoding="utf-8") as handle:
            report = json.load(handle)
        self.assertEqual(report["last_invocation"]["refused_for_secret_pattern"], [])
        for run, info in report["last_invocation"]["runs"].items():
            self.assertEqual(sum(info["secret_pattern_files"].values()), 0, run)

    def test_committed_scores_match_the_recorded_totals(self):
        for run, name in (("q12-benchmark-q12-run-1", "q12-run-1-scores.json"), ("q12-benchmark-q12-run-2", "q12-run-2-scores.json")):
            with open(os.path.join(REPO, "experiments", "results", "phase16", "answers", name), encoding="utf-8") as handle:
                scores = json.load(handle)
            check_row = ans.scorer_cross_check(run, scores)
            self.assertTrue(check_row["agrees"], (run, check_row))

    def test_16b_recomputed_from_the_frozen_raw_matches_the_recorded_totals(self):
        rows = ans.read_jsonl(os.path.join(self.FROZEN, "16b-live-evaluation-16b-1", "answers.jsonl"))
        out = ans.analyse_16b(rows)
        self.assertEqual(out["questions"], 40)
        self.assertTrue(all(v["agrees"] for v in out["recorded_totals_cross_check"].values()))
        self.assertEqual({k: v["questions"] for k, v in out["by_type"].items()}, {"component": 8, "direct coauthors": 14, "path": 10, "ranking": 8})

    def test_claim_support_recomputed_from_the_frozen_run_2(self):
        rows = ans.read_jsonl(os.path.join(self.FROZEN, "q12-benchmark-q12-run-2", "answers.jsonl"))
        c = ans.claim_support(rows)
        self.assertEqual(c["claims_attempted"], c["claims_verified"] + c["claims_rejected"])
        self.assertEqual(len(rows), 33)


class FirstFreezeRecord(FreezeAndVerify):
    def test_first_freeze_record_is_kept_by_a_later_freeze(self):
        self.make_run(ans.RUNS[0])
        self.assertEqual(ans.freeze(self.src, self.dst), 0)
        path = os.path.join(self.dst, "freeze-report.json")
        with open(path, encoding="utf-8") as handle:
            first = json.load(handle)["first_freeze"]
        self.assertFalse(first["recovered_from_observable_evidence"])
        self.assertEqual(ans.freeze(self.src, self.dst), 0)          # a second invocation copies nothing and must not rewrite the first record
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle)
        self.assertEqual(report["first_freeze"], first)
        self.assertEqual(report["last_invocation"]["files_copied_this_invocation"], [])
        self.assertEqual(first["source_files_sha256"], ans.sums_lines(self.dst, [ans.RUNS[0]]))

    def test_a_legacy_report_without_the_record_is_recovered_from_file_mtimes_and_says_so(self):
        self.make_run(ans.RUNS[0])
        ans.freeze(self.src, self.dst)
        path = os.path.join(self.dst, "freeze-report.json")
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle)
        del report["first_freeze"]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle)
        ans.freeze(self.src, self.dst)
        with open(path, encoding="utf-8") as handle:
            first = json.load(handle)["first_freeze"]
        self.assertTrue(first["recovered_from_observable_evidence"])
        self.assertIn("mtime", first["time_source"])
        self.assertRegex(first["utc"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_content_notes_count_home_paths_emails_and_standalone_12_digit_runs(self):
        self.make_run(ans.RUNS[0], extra=b'{"p": "/Users/someone/x", "m": "a@b.com", "n": 111122223333, "u": "run:5715c79e-c72e-4989-a15d-756859780620"}\n')
        ans.freeze(self.src, self.dst)
        notes = ans.content_notes(self.dst, [ans.RUNS[0]])
        self.assertEqual(notes["files_containing_a_local_home_directory_path"], [ans.RUNS[0] + "/answers.jsonl"])
        self.assertEqual((notes["email_like_strings"], notes["standalone_12_digit_runs"]), (1, 1))   # the UUID tail is not counted


class CostScopeAndEnvironment(unittest.TestCase):
    def test_rates_come_from_the_committed_profile(self):
        with open(os.path.join(REPO, "load-tests", "config", "load-profile.v1.json"), encoding="utf-8") as handle:
            pricing = json.load(handle)["llm"]["pricing"]
        self.assertEqual((ans.RATE_INPUT_PER_M, ans.RATE_OUTPUT_PER_M), (float(pricing["input_usd_per_million_tokens"]), float(pricing["output_usd_per_million_tokens"])))

    def test_earlier_phases_figure_is_a_separate_scope_with_its_source(self):
        e = ans.earlier_phases_cost({"cost_report": {"anthropic": {"usd": "0.054600"}}})
        self.assertEqual(e["16b_run_record_estimate_usd"], "0.054600")
        self.assertIn("0.075075", e["quoted"])
        self.assertIn("different Anthropic key", e["scope"])
        self.assertEqual(len(e["source_sha256"]), 64)

    def test_environment_labels(self):
        self.assertEqual(ans.environment_label({"target": {"loopback": True}}), "LOCAL-LOOPBACK-LLM")
        self.assertEqual(ans.environment_label({"target": {"loopback": False}}), "AWS-ECS-LLM")
        self.assertEqual(ans.run_commit({"target": {"loopback": True, "host": "127.0.0.1", "scheme": "http"}})["target_loopback"], True)

    def test_committed_result_labels_every_run_and_probe(self):
        with open(os.path.join(REPO, "experiments", "results", "phase16", "answers", "answer-quality.json"), encoding="utf-8") as handle:
            doc = json.load(handle)
        self.assertEqual(doc["session1_16b_record"]["environment"], "AWS-ECS-LLM")
        self.assertFalse(doc["session1_16b_record"]["target_loopback"])
        for run in ("q12-benchmark-q12-run-1", "q12-benchmark-q12-run-2"):
            self.assertEqual(doc["q12"][run]["record"]["environment"], "LOCAL-LOOPBACK-LLM")
        for probe in doc["q12_probes"].values():
            self.assertEqual(probe["record"]["environment"], "LOCAL-LOOPBACK-LLM")
        self.assertIn("CS441-key", doc["cost"]["console_cost_of_record"]["key"])


class ManifestCheck(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "experiments", "manifests"))
        os.makedirs(os.path.join(self.root, "experiments", "results", "phase16"))
        self.file = os.path.join(self.root, "experiments", "results", "phase16", "out.txt")
        with open(self.file, "w", encoding="utf-8") as handle:
            handle.write("hello\n")
        self.digest = sha256(self.file)
        self.manifest = {"schema": "scholarchain.eval16-manifest.v1", "id": "16-evaluation", "run_date": "2026-11-21",
                         "scope": {"offline": True, "network_calls": 0, "aws_calls": 0, "model_calls": 0, "spend_usd": "0.00"},
                         "inputs": [{"path": "experiments/results/phase16/out.txt", "sha256": self.digest, "tracked": True},
                                    {"path": "target/untracked/thing", "sha256": "a" * 64, "tracked": False}],
                         "scripts": [{"path": "experiments/results/phase16/out.txt", "sha256": self.digest}],
                         "outputs": [{"path": "experiments/results/phase16/out.txt", "sha256": self.digest}]}

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_check(self):
        with open(os.path.join(self.root, "experiments", "manifests", "16-evaluation.json"), "w", encoding="utf-8") as handle:
            json.dump(self.manifest, handle)
        lines = []
        return check.check_16_evaluation(self.root, lines), lines

    def test_valid_manifest_passes_and_untracked_inputs_are_not_required(self):
        failed, lines = self.run_check()
        self.assertFalse(failed, lines)
        self.assertIn("CHECK-OK", lines[-1])

    def test_a_changed_output_is_detected(self):
        with open(self.file, "w", encoding="utf-8") as handle:
            handle.write("changed\n")
        failed, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("differs from the recorded sha256" in x for x in lines))

    def test_missing_tracked_file_scope_violation_and_account_id_are_refused(self):
        self.manifest["outputs"].append({"path": "experiments/results/phase16/missing.txt", "sha256": "b" * 64})
        self.assertTrue(self.run_check()[0])
        self.manifest["outputs"].pop()
        self.manifest["scope"]["spend_usd"] = "0.10"
        self.assertTrue(self.run_check()[0])
        self.manifest["scope"]["spend_usd"] = "0.00"
        self.manifest["note"] = "account 111122223333 here"
        failed, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("12 digits" in x for x in lines))

    def test_absolute_and_parent_paths_are_refused(self):
        self.manifest["inputs"].append({"path": "/etc/passwd", "sha256": "c" * 64})
        self.assertTrue(self.run_check()[0])
        self.manifest["inputs"][-1] = {"path": "a/../b", "sha256": "c" * 64}
        self.assertTrue(self.run_check()[0])

    def test_no_results_tree_means_hashes_are_not_verified_but_the_shape_still_is(self):
        shutil.rmtree(os.path.join(self.root, "experiments", "results"))
        failed, lines = self.run_check()
        self.assertFalse(failed, lines)
        self.manifest["scope"]["model_calls"] = 3
        self.assertTrue(self.run_check()[0])

    def test_entry_without_sha256_fails_unless_an_untracked_directory_entry_with_a_listing_hash(self):
        self.manifest["outputs"].append({"path": "experiments/results/phase16/nohash.txt"})
        failed, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("has no sha256" in x for x in lines))
        self.manifest["outputs"].pop()
        self.manifest["inputs"].append({"path": "target/dir (3 files)", "tracked": False, "files_listing_sha256": "d" * 64})
        self.assertFalse(self.run_check()[0])
        self.manifest["inputs"][-1] = {"path": "target/dir (3 files)", "tracked": True, "files_listing_sha256": "d" * 64}
        self.assertTrue(self.run_check()[0])

    def test_a_result_file_that_is_not_listed_fails_unless_declared_excluded(self):
        extra = os.path.join(self.root, "experiments", "results", "phase16", "extra.log")
        with open(extra, "w", encoding="utf-8") as handle:
            handle.write("x")
        failed, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("neither listed nor declared" in x for x in lines))
        self.manifest["excluded_outputs"] = {"experiments/results/phase16/extra.log": "refreshed by another owner"}
        self.assertFalse(self.run_check()[0])

    def test_absent_manifest_is_a_skip_not_a_failure(self):
        lines = []
        self.assertFalse(check.check_16_evaluation(self.root, lines))
        self.assertIn("CHECK-SKIP", lines[0])

    def test_the_committed_manifest_passes_in_the_repository(self):
        lines = []
        self.assertFalse(check.check_16_evaluation(REPO, lines), lines)
        self.assertTrue(any("file hashes verified" in x for x in lines), lines)


if __name__ == "__main__":
    unittest.main()

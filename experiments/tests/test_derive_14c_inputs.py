#!/usr/bin/env python3
"""Tests for experiments/scripts/derive_14c_inputs.py (offline, stdlib), the committed experiments/inputs/14c files and the 15A config sources.

Run from the repository root:   python3 -I -m unittest discover -s experiments/tests -v
The fixture is a tiny hand-built Phase 6 export (neptune-opencypher-csv sidecar); every expected output below is derived by hand from the
selection rule in the script's docstring, not by calling the code under test.

Fixture researchers (id suffix, name, all-years distinct coauthors):
  r01 Ada Alpha 5 | r02 Ben Beta 2 | r03 Cy Gamma 3 | r04 Di Delta 2 | r05 Ed Epsilon 2 | r06 Flo Zeta 1 | r07 Gus Eta 2
  r08 and r09 both named Dup Name (not unique: ineligible) | r10 Ivy 0001 (digit: ineligible) | r11 a non-ASCII name (ineligible)
  r12 Lone Wolf, 0 coauthors in all-years (its only edge is in window 2015-2019, which must be ignored)
All-years edges (joint publications): r01-r02 5, r01-r03 3, r01-r04 2, r01-r08 1, r01-r10 1, r02-r03 4, r04-r05 2, r05-r06 1, r03-r07 1, r07-r09 1.
Parameters used: --pool 6 --direct 2 --component 1 --paths 2 --total 13 --node-researchers 5 --node-works 3 --degree-min 2 --degree-max 5
--degree-budget 14. The band 2..5 removes r06 (degree 1) and r12 (degree 0); the budget 14 is exactly the total degree of the include list
r01..r05 (5 + 2 + 3 + 2 + 2).
Pool (eligible, sorted by -degree then id, first 6): r01, r03, then the degree-2 ids in order r02, r04, r05, r07.
named = 3, step = 6 // 3 = 2 -> r01, r02, r05: direct r01, r02; component r05.
Pairs: coauthor pair with the largest joint count (r01, r02); two-hop pair: r01 and r02 are used, so r03 (neighbours r01, r02, r07; via r01
the first unused eligible non-neighbour is r04) -> (r03, r04).
"""
import contextlib
import hashlib
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


derive = load("derive_under_test", "experiments/scripts/derive_14c_inputs.py")
loadgen = load("loadgen_for_derive_test", "load-tests/loadgen.py")

NODE_HEADER = ":ID,:LABEL,label:String,schemaVersion:String,propertiesJson:String"
EDGE_HEADER = ":ID,:START_ID,:END_ID,:TYPE,schemaVersion:String"
CO_HEADER = ":ID,:START_ID,:END_ID,:TYPE,jointPublicationCount:Long,windowId:String"
RID = lambda n: "researcher:dblp:r%02d" % n
NAMES = {1: "Ada Alpha", 2: "Ben Beta", 3: "Cy Gamma", 4: "Di Delta", 5: "Ed Epsilon", 6: "Flo Zeta", 7: "Gus Eta", 8: "Dup Name", 9: "Dup Name",
         10: "Ivy 0001", 11: "Zoë Ünal", 12: "Lone Wolf"}
CO_EDGES = [(1, 2, 5), (1, 3, 3), (1, 4, 2), (1, 8, 1), (1, 10, 1), (2, 3, 4), (4, 5, 2), (5, 6, 1), (3, 7, 1), (7, 9, 1)]
AUTHORED = [(1, "w1"), (1, "w2"), (2, "w2"), (2, "w3"), (6, "w9")]
SPARK_RUN = "run:00000000-0000-4000-8000-00000000000a"
ARGS = ["--pool", "6", "--direct", "2", "--component", "1", "--paths", "2", "--total", "13", "--node-researchers", "5", "--node-works", "3",
        "--degree-min", "2", "--degree-max", "5", "--degree-budget", "14"]


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def build_export(root, split=False):
    """A hand-built export. With split=True every table is spread over two part files in reverse row order."""
    data = os.path.join(root, "neptune-opencypher-csv", "data")
    write(os.path.join(root, "run-manifest.json"), json.dumps({"runId": SPARK_RUN}))
    nodes = ["%s,RESEARCHER,%s,v1,[]" % (RID(n), '"%s"' % NAMES[n] if "," in NAMES[n] else NAMES[n]) for n in sorted(NAMES)]
    nodes += ["work:dblp:w1,WORK,Work one,v1,[]", "venue:dblp:v1,VENUE,A venue,v1,[]", "mention:dblp:m1,AUTHOR_MENTION,Ada Alpha,v1,[]"]
    graph = ["e%d,%s,work:dblp:%s,AUTHORED,v1" % (i, RID(r), w) for i, (r, w) in enumerate(AUTHORED)]
    graph += ["e90,work:dblp:w1,venue:dblp:v1,PUBLISHED_IN,v1", "e91,mention:dblp:m1,%s,RESOLVES_TO,v1" % RID(1)]
    co = ["c%d,%s,%s,COAUTHORED_WITH,%d,all-years" % (i, RID(a), RID(b), j) for i, (a, b, j) in enumerate(CO_EDGES)]
    co += ["c90,%s,%s,COAUTHORED_WITH,1,2015-2019" % (RID(1), RID(12)), "c91,%s,%s,COAUTHORED_WITH,9,since-2015" % (RID(2), RID(12))]
    for name, header, rows in (("nodes", NODE_HEADER, nodes), ("graph-edges", EDGE_HEADER, graph), ("coauthor-edges", CO_HEADER, co)):
        if split:
            half = len(rows) // 2
            parts = [list(reversed(rows[half:])), list(reversed(rows[:half]))]
        else:
            parts = [rows]
        for index, part in enumerate(parts):
            write(os.path.join(data, name, "part-%05d-fixture-c000.csv" % index), header + "\n" + "".join(r + "\n" for r in part))


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = derive.main(argv)
    return rc, out.getvalue()


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DeriveFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="derive-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.export = os.path.join(self.tmp, "export")
        build_export(self.export)

    def derive_to(self, name, export=None, extra=()):
        out = os.path.join(self.tmp, name)
        rc, text = run(["--export-dir", export or self.export, "--out-dir", out] + ARGS + list(extra))
        return rc, text, out

    def test_outputs_match_the_hand_derived_selection(self):
        rc, text, out = self.derive_to("o1")
        self.assertEqual(rc, 0, text)
        self.assertEqual(read(os.path.join(out, "include-ids.txt")), "".join(RID(n) + "\n" for n in (1, 2, 3, 4, 5)))
        expected_questions = [
            'Who are the direct coauthors of "Ada Alpha"?',
            'What is the component of "Ed Epsilon"?',
            'What is the shortest coauthor path between "Ada Alpha" and "Ben Beta"?',
            "Which researchers have the most distinct coauthors?",
            'Who are the direct coauthors of "Ben Beta"?',
            'What is the shortest coauthor path between "Cy Gamma" and "Di Delta"?',
            "Which researchers have the most distinct coauthors since 2015?",
            "Which researchers have the most distinct coauthors in window 2020-2026?",
            "Which researchers have the most distinct coauthors in window through-2009?",
            "Which researchers have the largest team size?",
            "Which researchers are the strongest bridges?",
            "Which researchers are the strongest bridges since 2015?",
            "Show the strongest repeated collaborations",
        ]
        self.assertEqual(read(os.path.join(out, "questions.txt")), "".join(q + "\n" for q in expected_questions))
        self.assertEqual(read(os.path.join(out, "real-query.json")), '{"question":"Who are the direct coauthors of \\"Ada Alpha\\"?","output":{"includeScores":false}}\n')
        self.assertEqual(json.loads(read(os.path.join(out, "real-query.json")))["output"], {"includeScores": False})
        # node ids: the 5 researchers named, then the works authored by them in id order (w1, w2, w3; w9 belongs to r06, not selected)
        self.assertEqual(read(os.path.join(out, "node-ids.txt")), "".join(RID(n) + "\n" for n in (1, 2, 3, 4, 5)) + "work:dblp:w1\nwork:dblp:w2\nwork:dblp:w3\n")

    def test_ineligible_researchers_never_appear(self):
        rc, text, out = self.derive_to("o1")
        everything = "".join(read(os.path.join(out, n)) for n in ("include-ids.txt", "questions.txt", "node-ids.txt"))
        for bad in (RID(8), RID(9), RID(10), RID(11), RID(12), "Dup Name", "Ivy", "Ünal", "Lone Wolf", "Flo Zeta"):
            self.assertNotIn(bad, everything)

    def test_same_input_gives_byte_identical_output(self):
        rc1, _, a = self.derive_to("a")
        rc2, _, b = self.derive_to("b")
        self.assertEqual((rc1, rc2), (0, 0))
        for name in sorted(os.listdir(a)):
            self.assertEqual(read(os.path.join(a, name)), read(os.path.join(b, name)), name)

    def test_row_order_and_part_layout_do_not_change_the_selection(self):
        other = os.path.join(self.tmp, "export-split")
        build_export(other, split=True)
        rc1, _, a = self.derive_to("a")
        rc2, _, b = self.derive_to("b", export=other)
        self.assertEqual((rc1, rc2), (0, 0))
        for name in ("include-ids.txt", "questions.txt", "node-ids.txt", "real-query.json"):
            self.assertEqual(read(os.path.join(a, name)), read(os.path.join(b, name)), name)
        # the provenance does differ: the part files (and so their hashes) are different
        self.assertNotEqual(read(os.path.join(a, "provenance.json")), read(os.path.join(b, "provenance.json")))

    def test_provenance_names_the_run_and_the_hash_of_every_file_read(self):
        rc, text, out = self.derive_to("o1")
        prov = json.loads(read(os.path.join(out, "provenance.json")))
        self.assertEqual(prov["source"]["run_id"], SPARK_RUN)
        files = prov["source"]["files_read_sha256"]
        self.assertEqual(sorted(files), ["neptune-opencypher-csv/data/coauthor-edges/part-00000-fixture-c000.csv",
                                         "neptune-opencypher-csv/data/graph-edges/part-00000-fixture-c000.csv",
                                         "neptune-opencypher-csv/data/nodes/part-00000-fixture-c000.csv", "run-manifest.json"])
        for rel, digest in files.items():
            with open(os.path.join(self.export, rel), "rb") as handle:
                self.assertEqual(digest, hashlib.sha256(handle.read()).hexdigest())
        for name, entry in prov["outputs"].items():
            self.assertEqual(entry["sha256"], sha(read(os.path.join(out, name))))
            self.assertEqual(entry["lines"], read(os.path.join(out, name)).count("\n"))
        self.assertEqual(prov["counts"], {"researchers": 12, "eligible": 6, "all_years_coauthor_pairs": 10, "pool": 6, "questions": 13, "include_ids": 5, "include_total_degree": 14, "node_ids": 8})
        self.assertNotIn(self.tmp, json.dumps(prov))  # no absolute path

    def test_refuses_to_overwrite_and_overwrites_on_request(self):
        rc, _, out = self.derive_to("o1")
        self.assertEqual(rc, 0)
        marker = os.path.join(out, "questions.txt")
        write(marker, "kept\n")
        rc, text, _ = self.derive_to("o1")
        self.assertEqual(rc, 1)
        self.assertIn("DERIVE-REFUSED", text)
        self.assertEqual(read(marker), "kept\n")
        rc, text, _ = self.derive_to("o1", extra=["--overwrite"])
        self.assertEqual(rc, 0)
        self.assertNotEqual(read(marker), "kept\n")

    def test_question_count_mismatch_is_refused_and_writes_nothing(self):
        out = os.path.join(self.tmp, "o2")
        rc, text = run(["--export-dir", self.export, "--out-dir", out] + ARGS[:8] + ["--total", "12", "--node-researchers", "5", "--node-works", "3", "--degree-min", "2", "--degree-max", "5"])
        self.assertEqual(rc, 1)
        self.assertIn("the selection gives 13 questions, --total says 12", text)
        self.assertFalse(os.path.exists(out))

    def test_degree_budget_is_enforced_and_nothing_is_written(self):
        rc, text, out = self.derive_to("ok", extra=["--degree-budget", "14"])  # a later --degree-budget overrides the one in ARGS
        self.assertEqual(rc, 0, text)
        rc, text, out = self.derive_to("over", extra=["--degree-budget", "13"])
        self.assertEqual(rc, 1)
        self.assertIn("total all-years degree is 14, above the --degree-budget 13", text)
        self.assertFalse(os.path.exists(out))

    def test_degree_band_limits_the_pool(self):
        # band 3..5 leaves only r01 (5) and r03 (3): fewer than the 3 named researchers needed
        rc, text, out = self.derive_to("band", extra=["--degree-min", "3"])
        self.assertEqual(rc, 1)
        self.assertIn("only 2 eligible researchers in the pool, 3 needed", text)
        self.assertFalse(os.path.exists(out))
        # a wider band 1..5 adds r06 (degree 1) to the eligible set only; the pool of 6 and the outputs do not change
        rc1, _, a = self.derive_to("wide", extra=["--degree-min", "1"])
        rc2, _, b = self.derive_to("base")
        self.assertEqual((rc1, rc2), (0, 0))
        self.assertEqual(json.loads(read(os.path.join(a, "provenance.json")))["counts"]["eligible"], 7)
        self.assertEqual(read(os.path.join(a, "include-ids.txt")), read(os.path.join(b, "include-ids.txt")))

    def test_node_ids_prefer_the_closure_of_the_included_researchers(self):
        # 7 researchers: r01..r05 named, then their coauthors by (-degree, id): r07 (2), then r06 (1) before r08 and r10; works only of named researchers
        rc, text, out = self.derive_to("nodes", extra=["--node-researchers", "7"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(read(os.path.join(out, "node-ids.txt")), "".join(RID(n) + "\n" for n in range(1, 8)) + "work:dblp:w1\nwork:dblp:w2\nwork:dblp:w3\n")

    def test_not_an_export_is_refused(self):
        rc, text = run(["--export-dir", self.tmp, "--out-dir", os.path.join(self.tmp, "o3")])
        self.assertEqual(rc, 1)
        self.assertIn("not a Phase 6 Spark export", text)

    def test_outputs_obey_the_include_list_and_loadgen_formats(self):
        rc, text, out = self.derive_to("o1")
        include = read(os.path.join(out, "include-ids.txt")).splitlines()
        self.assertEqual(include, sorted(set(include)))
        self.assertTrue(0 < len(include) <= 2000)
        self.assertTrue(all(re.fullmatch(r"(researcher|work):[^\s]{1,500}", line) for line in include))  # IncludeList.shape in RuntimeArtifactSubset.scala
        self.assertEqual(len(loadgen.read_lines(os.path.join(out, "node-ids.txt"), "node ids", maxlen=200)), 8)
        self.assertEqual(len(loadgen.read_lines(os.path.join(out, "questions.txt"), "questions")), 13)


class CommittedInputsTests(unittest.TestCase):
    """The committed experiments/inputs/14c files (derived once from export f6e63b4b; the export itself is git-ignored and not needed here)."""
    DIR = os.path.join(REPO, "experiments", "inputs", "14c")
    # SHAPE check only: the first-stage patterns of QueryPlannerAgent.fallback. It does not run the planner; QueryPlannerAgent.coveredQuestion
    # (checked read-only by review 8) additionally rejects an unquoted 'in window since-...' (the filter text stops at the keyword 'since').
    GRAMMAR = [
        r'Who are the direct coauthors of "[A-Za-z \'-]{3,60}"\?',
        r'What is the component of "[A-Za-z \'-]{3,60}"\?',
        r'What is the shortest coauthor path between "[A-Za-z \'-]{3,60}" and "[A-Za-z \'-]{3,60}"\?',
        r"Which researchers have the most distinct coauthors( since 2015| in window (2020-2026|through-2009))?\?",
        r"Which researchers have the largest team size\?",
        r"Which researchers are the strongest bridges( since 2015)?\?",
        r"Show the strongest repeated collaborations",
    ]

    def lines(self, name):
        return read(os.path.join(self.DIR, name)).splitlines()

    def test_questions_are_the_40_fixed_supported_questions(self):
        questions = self.lines("questions.txt")
        self.assertEqual(len(questions), 40)  # the 16B evaluation asks these 40 fixed questions once (bucket 16b was 40 answers when they were derived; 80 since 2026-11-21)
        self.assertEqual(len(set(questions)), 40)
        for q in questions:
            self.assertTrue(any(re.fullmatch(g, q) for g in self.GRAMMAR), q)
        # 14 direct + 8 component + 10 path + 8 global
        self.assertEqual([sum(1 for q in questions if re.fullmatch(g, q)) for g in self.GRAMMAR[:3]], [14, 8, 10])
        self.assertEqual(sum(1 for q in questions if "researchers" in q or q.startswith("Show")), 8)

    def test_no_question_has_the_window_id_that_starts_with_a_planner_keyword(self):
        # review 8 B1: 'in window since-2015' is refused by coveredQuestion (the unquoted-filter lookahead stops at 'since'); use 'since 2015'
        for q in self.lines("questions.txt"):
            self.assertNotRegex(q, r"in window since-")
        self.assertIn("Which researchers are the strongest bridges since 2015?", self.lines("questions.txt"))

    def test_include_ids_follow_the_include_list_format(self):
        include = self.lines("include-ids.txt")
        self.assertEqual(include, sorted(set(include)))
        self.assertTrue(0 < len(include) <= 2000)
        self.assertTrue(all(re.fullmatch(r"researcher:dblp:[0-9a-f]{64}", line) for line in include))
        self.assertLess(os.path.getsize(os.path.join(self.DIR, "include-ids.txt")), 1024 * 1024)

    def test_real_query_is_the_smoke_body_and_names_a_question_subject(self):
        body = json.loads(read(os.path.join(self.DIR, "real-query.json")))
        self.assertEqual(sorted(body), ["output", "question"])
        self.assertEqual(body["output"], {"includeScores": False})
        self.assertIn(body["question"], self.lines("questions.txt"))

    def test_node_ids_are_researcher_and_work_ids_for_loadgen(self):
        ids = loadgen.read_lines(os.path.join(self.DIR, "node-ids.txt"), "node ids", maxlen=200)
        self.assertEqual(len(ids), 100)
        self.assertEqual(len(set(ids)), 100)
        self.assertTrue(all(i.startswith(("researcher:dblp:", "work:dblp:", "work:doi:")) for i in ids))
        self.assertTrue(set(self.lines("include-ids.txt")) <= set(ids))

    def test_provenance_matches_the_committed_files(self):
        prov = json.loads(read(os.path.join(self.DIR, "provenance.json")))
        self.assertEqual(prov["schema"], derive.SCHEMA)
        self.assertEqual(prov["source"]["run_id"], "run:f6e63b4b-d542-4a32-930c-f21f002cba76")
        self.assertEqual(prov["source"]["files_read"], 58)
        self.assertEqual(len(prov["source"]["files_read_sha256"]), 58)
        self.assertEqual(sorted(prov["outputs"]), ["include-ids.txt", "node-ids.txt", "questions.txt", "real-query.json"])
        for name, entry in prov["outputs"].items():
            text = read(os.path.join(self.DIR, name))
            self.assertEqual(entry["sha256"], sha(text), name)
            self.assertEqual(entry["lines"], text.count("\n"), name)

    def test_provenance_records_the_degree_band_and_budget(self):
        prov = json.loads(read(os.path.join(self.DIR, "provenance.json")))
        self.assertEqual((prov["rule"]["degree_min"], prov["rule"]["degree_max"], prov["rule"]["degree_budget"]), (10, 22, 900))
        total = prov["counts"]["include_total_degree"]
        self.assertTrue(0 < total <= 900, total)
        self.assertEqual(prov["counts"]["include_ids"], len(self.lines("include-ids.txt")))
        # about 9.1 artifact rows per unit of degree against the 10,000-row cap of RuntimeArtifactConfig
        self.assertLess(total * 9.1, 10000)
        # the include list needs at least one researcher per direct/component question and per path endpoint, at most 22 + 20
        self.assertTrue(len(self.lines("include-ids.txt")) <= 42)

    def test_no_account_number_email_or_secret_shaped_text(self):
        for name in os.listdir(self.DIR):
            text = read(os.path.join(self.DIR, name))
            stripped = re.sub(r"[0-9a-f]{64}", "", text)  # sha256 values and researcher keys are hex, not account numbers
            self.assertIsNone(re.search(r"\b\d{12}\b", stripped), name)
            self.assertNotIn(chr(64), text, name)  # no email address
            self.assertIsNone(re.search(r"(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{12,}|pa-[A-Za-z0-9_-]{20,})", text), name)


class ConfigSourcesTests(unittest.TestCase):
    """Item 1: the --er-policy and --er-config files are the repository's Phase 5/6 files, --spark-config-template and --hadoop-config the
    experiment-owned 15A files (P24, P1/P22); their hashes must not drift."""
    def test_sources_exist_and_hashes_match(self):
        doc = json.loads(read(os.path.join(REPO, "experiments", "inputs", "15a", "config-sources.json")))
        self.assertEqual(sorted(doc["files"]), ["er-config", "er-policy", "hadoop-config", "spark-config-template"])
        for name, entry in doc["files"].items():
            path = os.path.join(REPO, entry["path"])
            self.assertTrue(os.path.isfile(path), name)
            with open(path, "rb") as handle:
                self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), entry["sha256"], name)
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")

    def test_the_template_holds_the_four_keys_the_render_step_replaces(self):
        doc = json.loads(read(os.path.join(REPO, "experiments", "inputs", "15a", "config-sources.json")))
        template = json.loads(read(os.path.join(REPO, doc["files"]["spark-config-template"]["path"])))
        for key in ("hadoopRunRoot", "entityResolutionRunRoot", "outputRoot", "checkpointDirectory"):
            self.assertIn(key, template)  # scripts/emr/sc-render-spark-config.py refuses a template without them

    def test_the_policy_version_is_the_one_in_the_export_lineage(self):
        doc = json.loads(read(os.path.join(REPO, "experiments", "inputs", "15a", "config-sources.json")))
        policy = json.loads(read(os.path.join(REPO, doc["files"]["er-policy"]["path"])))
        self.assertEqual(policy["policyVersion"], "er-offline-uncalibrated-v2")  # entityResolutionPolicyVersion of export f6e63b4b


if __name__ == "__main__":
    unittest.main()

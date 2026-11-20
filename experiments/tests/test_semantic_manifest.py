#!/usr/bin/env python3
"""Tests for the P42 semantic 15B manifest check (check_manifests.check_semantic) and the questions-file builder (derive_semantic_questions.py).

Run from the repository root:   python3 -I -m unittest discover -s experiments/tests -v
Offline, stdlib only. Expected numbers are hand-derived from the requirement: required per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000
(198,600 in total), a warm-up of at most 200 requests, at least 25 quiet minutes, a fixed set of 100-200 distinct questions.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
REPO = os.path.dirname(EXPERIMENTS)


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, relative))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load("check_semantic_under_test", "experiments/scripts/check_manifests.py")
derive = load("derive_semantic_under_test", "experiments/scripts/derive_semantic_questions.py")
SEMANTIC = "15b-ecs-scaling-semantic.json"
REAL_SLICE = os.path.join(REPO, "target", "phase6-inputs", "6fg-dblp", "dblp.xml")


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, document):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sem-fixture-")
        self.addCleanup(shutil.rmtree, self.root, True)
        for relative in ("experiments/manifests", "experiments/inputs/15b", "load-tests/config", "datasets/phase6"):
            shutil.copytree(os.path.join(REPO, relative), os.path.join(self.root, relative), ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("loadgen.py", "llm_budget.py"):
            shutil.copy(os.path.join(REPO, "load-tests", name), os.path.join(self.root, "load-tests", name))
        self.loadgen = load("loadgen_for_semantic_check_test", "load-tests/loadgen.py")
        self.profile_path = os.path.join(self.root, "load-tests", "config", "load-profile.v1.json")
        self.manifest_path = os.path.join(self.root, "experiments", "manifests", SEMANTIC)
        self.questions_path = os.path.join(self.root, "experiments", "inputs", "15b", "semantic-questions.txt")
        self.provenance_path = os.path.join(self.root, "experiments", "inputs", "15b", "semantic-questions.provenance.json")

    def run_check(self):
        lines = []
        failed = check.check_semantic(self.root, False, lines, self.loadgen, self.loadgen.load_profile(self.profile_path))
        return failed, lines

    def mutate_manifest(self, change):
        document = read_json(self.manifest_path)
        change(document)
        write_json(self.manifest_path, document)

    def phase(self, document, name):
        return [p for p in document["phases"] if p["name"] == name][0]

    def assert_fails(self, needle):
        failed, lines = self.run_check()
        self.assertTrue(failed, "\n".join(lines))
        self.assertTrue(any("CHECK-FAILED" in line and needle in line for line in lines), "\n".join(lines))


class SemanticManifestCheck(Fixture):
    def test_the_committed_manifest_passes_with_the_hand_derived_totals(self):
        failed, lines = self.run_check()
        self.assertFalse(failed, "\n".join(lines))
        self.assertEqual(len(lines), 1)
        self.assertIn("= 198600 requests", lines[0])
        self.assertIn("warm-up 200 <= 200", lines[0])
        self.assertIn("quiet window 30 min", lines[0])
        self.assertIn("150 fixed questions", lines[0])
        document = read_json(self.manifest_path)
        self.assertEqual(sum(p["max_requests"] for p in document["phases"] if p["type"] == "load"), 600 + 3000 + 15000 + 30000 + 150000)

    def test_the_full_check_script_includes_the_semantic_manifest(self):
        lines = []
        check.check_15b_16b(REPO, False, lines)
        self.assertTrue(any("CHECK-OK: %s" % SEMANTIC in line for line in lines), "\n".join(lines))

    def test_a_raised_limit_fails_for_each_phase(self):
        for name, cap in (("baseline-1", 601), ("level-5", 3001), ("level-25", 15001), ("level-50", 30001), ("hold-50", 150001)):
            shutil.copy(os.path.join(REPO, "experiments", "manifests", SEMANTIC), self.manifest_path)
            self.mutate_manifest(lambda d: self.phase(d, name).update(max_requests=cap))
            self.assert_fails("exceeds the required limit")

    def test_a_lowered_limit_or_a_missing_phase_fails_the_committed_shape(self):
        self.mutate_manifest(lambda d: self.phase(d, "hold-50").update(max_requests=100000))  # allowed by loadgen, but the committed manifest is exactly the required value
        self.assert_fails("must run at level 50 with max_requests exactly 150000")
        shutil.copy(os.path.join(REPO, "experiments", "manifests", SEMANTIC), self.manifest_path)
        self.mutate_manifest(lambda d: d["phases"].remove(self.phase(d, "level-25")))
        self.assert_fails("level-25")

    def test_warmup_rules(self):
        self.mutate_manifest(lambda d: self.phase(d, "warmup").update(max_requests=201))
        self.assert_fails("max_requests must be an integer from 1 to 200")
        shutil.copy(os.path.join(REPO, "experiments", "manifests", SEMANTIC), self.manifest_path)
        self.mutate_manifest(lambda d: d["phases"].remove(self.phase(d, "warmup")))
        self.assert_fails("exactly one warmup phase")
        shutil.copy(os.path.join(REPO, "experiments", "manifests", SEMANTIC), self.manifest_path)
        self.mutate_manifest(lambda d: self.phase(d, "warmup").update(max_requests=149))
        self.assert_fails("below the 150 distinct questions")

    def test_the_quiet_window_must_be_at_least_25_minutes(self):
        self.mutate_manifest(lambda d: self.phase(d, "cooldown-observe").update(duration_seconds=1499))
        self.assert_fails("under 25 minutes")
        self.mutate_manifest(lambda d: self.phase(d, "cooldown-observe").update(duration_seconds=1500))
        failed, lines = self.run_check()
        self.assertFalse(failed, "\n".join(lines))

    def test_the_questions_file_is_pinned_distinct_and_matches_its_provenance(self):
        with open(self.questions_path, "a", encoding="utf-8") as handle:
            handle.write("an extra phrase\n")
        self.assert_fails("differs from the manifest pin")
        shutil.copy(os.path.join(REPO, "experiments", "inputs", "15b", "semantic-questions.txt"), self.questions_path)
        provenance = read_json(self.provenance_path)
        provenance["source"]["sha256"] = "0" * 64
        write_json(self.provenance_path, provenance)
        self.assert_fails("differs from the Phase 6 slice manifest")
        provenance["source"] = read_json(os.path.join(REPO, "experiments", "inputs", "15b", "semantic-questions.provenance.json"))["source"]
        provenance["phrases"][0]["phrase"] = "something else"
        write_json(self.provenance_path, provenance)
        self.assert_fails("provenance record does not match")

    def test_a_missing_manifest_or_a_weaker_semantic_route_fails(self):
        profile = read_json(self.profile_path)
        profile["routes"]["semantic"]["weight"] = 14  # not above the other routes together
        write_json(self.profile_path, profile)
        self.assert_fails("weight above all other routes")
        os.remove(self.manifest_path)
        self.assert_fails("missing or not valid JSON")

    def test_a_twelve_digit_run_in_the_manifest_fails_the_policy(self):
        digits = "9" * 12  # built at runtime: no 12-digit literal in the source
        self.mutate_manifest(lambda d: d.update(description=d["description"] + " " + digits))
        self.assert_fails("12 digits")


class QuestionsBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sem-derive-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        os.makedirs(os.path.join(self.tmp, "datasets", "phase6"))
        os.makedirs(os.path.join(self.tmp, "target"))

    @staticmethod
    def read_bytes(path):
        with open(path, "rb") as handle:
            return handle.read()

    def read_text(self, path):
        return self.read_bytes(path).decode("utf-8")

    @staticmethod
    def word(i, salt):
        letters = "bcdfghklmnprtvwz"
        out = salt
        n = i + 1
        while n:
            out += letters[n % len(letters)] + "a"
            n //= len(letters)
        return out

    def write_slice(self, titles, pin=True):
        body = "<dblp>\n" + "".join("<inproceedings><title>%s</title></inproceedings>\n" % t for t in titles) + "</dblp>\n"
        path = os.path.join(self.tmp, "target", "slice.xml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        digest = sha256_bytes(body.encode("utf-8")) if pin else "f" * 64
        write_json(os.path.join(self.tmp, "datasets", "phase6", "dblp-slice-manifest.v1.json"), {"output": {"sha256": digest}, "license": {"name": "CC0 1.0 Universal (test)"}})
        return path

    def run_derive(self, source, *extra, out="out"):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = derive.main(["--root", self.tmp, "--source", source, "--out-dir", os.path.join(self.tmp, out)] + list(extra))
        return rc, buffer.getvalue()

    def titles_for(self, count):
        """count distinct two-word topics; topic i appears in (count - i) titles, so the document frequency (and the rank) is hand-known."""
        titles = []
        for i in range(count):
            titles += ["%s %s." % (self.word(i, "quad"), self.word(i, "xylo"))] * (count - i)
        return titles

    def test_windows_break_on_stop_generic_and_non_words(self):
        self.assertEqual(derive.windows("Brief Announcement: Fast Leader Election in the Cloud."), {"fast leader", "leader election", "fast leader election"})
        self.assertEqual(derive.windows("A Study of 5G Networks Using Paxos"), set())  # study, using, 5g break every window; one word is no phrase
        self.assertEqual(derive.windows("Low-latency key-value stores"), {"low-latency key-value", "key-value stores", "low-latency key-value stores"})

    def test_rank_is_document_frequency_then_words_then_text_and_counts_are_exact(self):
        source = self.write_slice(self.titles_for(120))
        rc, out = self.run_derive(source, "--count", "100", "--min-df", "1")
        self.assertEqual(rc, 0, out)
        lines = self.read_text(os.path.join(self.tmp, "out", "semantic-questions.txt")).split("\n")
        self.assertEqual(lines.pop(), "")
        self.assertEqual(len(lines), 100)
        self.assertEqual(lines, ["%s %s" % (self.word(i, "quad"), self.word(i, "xylo")) for i in range(100)])  # topic 0 is in 120 titles, topic 99 in 21
        provenance = read_json(os.path.join(self.tmp, "out", "semantic-questions.provenance.json"))
        self.assertEqual(provenance["counts"]["questions"], 100)
        self.assertEqual((provenance["phrases"][0]["titles"], provenance["phrases"][99]["titles"]), (120, 21))
        self.assertEqual(provenance["source"]["sha256"], sha256_bytes(self.read_bytes(source)))
        self.assertEqual(provenance["outputs"]["semantic-questions.txt"]["sha256"], sha256_bytes(("\n".join(lines) + "\n").encode("utf-8")))
        self.assertEqual(provenance["source"]["titles_read"], sum(range(1, 121)))

    def test_output_is_byte_identical_and_an_existing_file_is_refused(self):
        source = self.write_slice(self.titles_for(110))
        self.assertEqual(self.run_derive(source, "--count", "100", "--min-df", "1", out="a")[0], 0)
        self.assertEqual(self.run_derive(source, "--count", "100", "--min-df", "1", out="b")[0], 0)
        for name in ("semantic-questions.txt", "semantic-questions.provenance.json"):
            self.assertEqual(self.read_bytes(os.path.join(self.tmp, "a", name)), self.read_bytes(os.path.join(self.tmp, "b", name)))
        rc, out = self.run_derive(source, "--count", "100", "--min-df", "1", out="a")
        self.assertEqual(rc, 1)
        self.assertIn("exists", out)
        self.assertEqual(self.run_derive(source, "--count", "100", "--min-df", "1", "--overwrite", out="a")[0], 0)

    def test_a_fragment_of_a_longer_topic_and_a_plural_duplicate_are_skipped(self):
        titles = ["Fast Leader Election."] * 6 + ["Cloud Storage."] * 5 + ["Cloud Storages."] * 5
        chosen, eligible, _ = derive.select(titles, 10, 5)
        phrases = [p for p, _ in chosen]
        self.assertIn("fast leader election", phrases)
        self.assertNotIn("leader election", phrases)  # a fragment: the trigram has the same document frequency
        self.assertNotIn("fast leader", phrases)
        self.assertEqual(sum(1 for p in phrases if p.startswith("cloud storage")), 1)  # the plural form is the same topic

    def test_refusals(self):
        source = self.write_slice(self.titles_for(110))
        self.assertEqual(self.run_derive(source, "--count", "99", "--min-df", "1")[0], 1)  # below 100
        self.assertEqual(self.run_derive(source, "--count", "201", "--min-df", "1")[0], 1)  # above 200
        rc, out = self.run_derive(source, "--count", "150", "--min-df", "1")  # only 110 topics exist
        self.assertEqual(rc, 1)
        self.assertIn("only 110 phrases", out)
        wrong = self.write_slice(self.titles_for(110), pin=False)  # a source that is not the pinned Phase 6 slice
        rc, out = self.run_derive(wrong, "--count", "100", "--min-df", "1", out="c")
        self.assertEqual(rc, 1)
        self.assertIn("records", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "c")))

    @unittest.skipUnless(os.path.isfile(REAL_SLICE), "the ignored Phase 6 slice target/phase6-inputs/6fg-dblp/dblp.xml is not present")
    def test_the_committed_questions_are_reproduced_byte_for_byte_from_the_phase6_slice(self):
        buffer = io.StringIO()
        out_dir = os.path.join(self.tmp, "real")
        with contextlib.redirect_stdout(buffer):
            rc = derive.main(["--out-dir", out_dir])
        self.assertEqual(rc, 0, buffer.getvalue())
        for name in ("semantic-questions.txt", "semantic-questions.provenance.json"):
            with open(os.path.join(out_dir, name), "rb") as made, open(os.path.join(EXPERIMENTS, "inputs", "15b", name), "rb") as committed:
                self.assertEqual(made.read(), committed.read(), name)


class CommittedProvenance(unittest.TestCase):
    def test_provenance_records_the_source_the_rule_and_the_counts(self):
        provenance = read_json(os.path.join(EXPERIMENTS, "inputs", "15b", "semantic-questions.provenance.json"))
        slice_manifest = read_json(os.path.join(REPO, "datasets", "phase6", "dblp-slice-manifest.v1.json"))
        self.assertEqual(provenance["source"]["sha256"], slice_manifest["output"]["sha256"])
        self.assertEqual(provenance["source"]["recorded_in"], "datasets/phase6/dblp-slice-manifest.v1.json")
        self.assertIn("CC0", provenance["source"]["license"])
        self.assertEqual(provenance["counts"]["questions"], 150)
        self.assertEqual(len(provenance["phrases"]), 150)
        self.assertEqual(provenance["script"], "experiments/scripts/derive_semantic_questions.py")
        self.assertTrue(all(row["titles"] >= provenance["counts"]["min_df"] for row in provenance["phrases"]))
        text = json.dumps(provenance)
        self.assertNotRegex(__import__("re").sub(r"[0-9a-f]{64}", "", text), r"[0-9]{12}")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for the Phase 15 experiment manifests, the manifest renderer and the DBLP subset builder (offline, stdlib).

Run from the repository root:   python3 -I -m unittest discover -s experiments/tests -v
Expected numbers are hand-derived from the requirement or the committed Phase 6 slice manifest.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
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


subsets = load("subsets_under_test", "experiments/scripts/make_dblp_subsets.py")
render = load("render_under_test", "experiments/scripts/render_manifests.py")
check = load("check_under_test", "experiments/scripts/check_manifests.py")
HEX_A = "a" * 64
FAKE_ACCOUNT = "1" * 6 + "2" * 6  # built at runtime: no 12-digit literal in the source
DIGIT_HASH = ("1234" * 4) * 4  # a 64-character sha256 made of digits only


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def validate_with_run_experiments_validator(path):
    """scripts/lib/experiment.py is what scripts/run-experiment.sh calls in its manifest-schema step; pinned caps from the task.
    The committed manifests carry ${...} tokens that run-experiment.sh resolves at run time, so the copy given to the validator has the
    tokens replaced by valid dummy names."""
    with open(path, encoding="utf-8") as handle:
        text = check.substitute(handle.read())
    with tempfile.TemporaryDirectory(prefix="exp-validate-") as scratch:
        copy = os.path.join(scratch, os.path.basename(path))
        write_text(copy, text)
        done = subprocess.run([sys.executable, "-I", os.path.join(REPO, "scripts", "lib", "experiment.py"), "validate", "--manifest", copy, "--max-run-usd", "3",
                               "--max-runtime-cap", "180", "--max-capacity-cap", "4", "--max-idle-cap", "900"], capture_output=True, text=True, timeout=60)
    return done.returncode, done.stdout


class CommittedManifests(unittest.TestCase):
    def test_each_15a_manifest_passes_the_run_experiment_validator(self):
        for size in (25, 50, 100):
            path = os.path.join(EXPERIMENTS, "manifests", "15a-emr-size-%d.json" % size)
            rc, out = validate_with_run_experiments_validator(path)
            self.assertEqual((rc, out), (0, ""), path)

    def test_committed_manifests_hold_tokens_only_and_no_account_id(self):
        for name in sorted(os.listdir(os.path.join(EXPERIMENTS, "manifests"))):
            with open(os.path.join(EXPERIMENTS, "manifests", name), encoding="utf-8") as handle:
                text = handle.read()
            self.assertEqual(check.policy_problems(text), [], name)
            self.assertNotRegex(__import__("re").sub(r"[0-9a-f]{64}", "", text), r"[0-9]{12}", name)

    def test_policy_rejects_literal_buckets_and_twelve_digit_runs_but_not_hashes(self):
        good = '{"a": "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/x", "h": "%s"}' % DIGIT_HASH  # a sha256 made of digits only
        self.assertEqual(check.policy_problems(good), [])
        self.assertEqual(len(check.policy_problems('{"a": "s3://scholarchain-course-%s-artifacts/emr/x"}' % FAKE_ACCOUNT)), 2)  # literal bucket and 12 digits
        self.assertEqual(len(check.policy_problems('{"a": "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/run-%s"}' % FAKE_ACCOUNT)), 1)
        self.assertEqual(len(check.policy_problems('{"a": "s3://some-bucket/emr/x"}')), 1)
        self.assertEqual(check.placeholder_problems('{"j": "%s"}' % ("0" * 64)), ["an all-zero sha256 placeholder remains"])

    def test_15a_limits_match_the_approved_caps(self):
        total = 0
        for size in (25, 50, 100):
            manifest = read_json(os.path.join(EXPERIMENTS, "manifests", "15a-emr-size-%d.json" % size))
            self.assertEqual(manifest["id"], "15a-emr-size-%d" % size)
            self.assertEqual(manifest["budget"]["max_runtime_minutes"], 90)  # 90 minutes of cluster time per run
            self.assertEqual(manifest["teardown"]["mode"], "auto-termination")
            self.assertEqual(manifest["budget"]["max_capacity"], 1 + manifest["pipeline"]["core_count"] + manifest["pipeline"]["max_task_count"])
            self.assertEqual(manifest["budget"]["max_capacity"], 2)
            self.assertEqual(manifest["pipeline"]["input_prefix"], "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/input/size-%d" % size)
            self.assertEqual(manifest["pipeline"]["output_prefix"], "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/pipeline/${SCHOLARCHAIN_RUN_PREFIX}/15a/size-%d" % size)
            self.assertEqual(manifest["pipeline"]["er_jar"], "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/jars/entity-resolution.jar")
            self.assertEqual(manifest["pipeline"]["er_policy"], "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/config/er-policy.json")
            self.assertEqual(manifest["metrics"]["locations"], ["s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/pipeline/${SCHOLARCHAIN_RUN_PREFIX}/15a/size-%d/metrics/" % size])
            total += manifest["budget"]["max_usd"]
        self.assertAlmostEqual(total, 2.52)  # three runs x 0.84 = 2.52, within the 2.52 cumulative cap

    def test_g6_estimate_is_hand_derived(self):
        manifest = read_json(os.path.join(EXPERIMENTS, "manifests", "15a-emr-size-25.json"))
        pricing = {"EMR_RATE_EC2_M5_XLARGE": "0.192", "EMR_RATE_EMR_M5_XLARGE": "0.048"}
        # 2 instances x 0.240 USD/h x (90 min + 900 s idle = 6300 s = 1.75 h) = 0.84
        self.assertEqual(str(check.g6_estimate(manifest, pricing)), "0.84")
        manifest["pipeline"]["max_task_count"] = 1
        self.assertEqual(str(check.g6_estimate(manifest, pricing)), "1.26")  # 3 x 0.24 x 1.75

    def test_committed_prep_config_passes_every_ceiling_except_the_sample_bound(self):
        prep = read_json(os.path.join(EXPERIMENTS, "inputs", "15a", "prep-config.json"))
        conf = check.read_conf(os.path.join(REPO, "scripts", "config", "release.conf"))
        over = [field for field, key in check.CEILING_KEYS if prep[field] > int(conf[key])]
        # Today the only violation may be maxLocalSampleRecords (BLOCKED-ON infra-engineer); any other field over its ceiling is a defect here.
        self.assertTrue(set(over) <= {"maxLocalSampleRecords"}, over)
        self.assertGreaterEqual(prep["maxLocalSampleRecords"], 10577 + 100)  # the 100 percent slice plus the small samples is never truncated

    def test_datasets_manifest_names_the_four_sources(self):
        datasets = read_json(os.path.join(EXPERIMENTS, "inputs", "15a", "datasets.json"))
        self.assertEqual(sorted(datasets), ["crossref", "dblp", "openalex", "orcid"])
        self.assertEqual(datasets["dblp"]["snapshot"], "dblp-2026-10-03")

    def test_check_script_reports_no_failure_on_the_committed_files(self):
        lines = []
        failed_a, _ = check.check_15a(REPO, False, lines)
        failed_b = check.check_15b_16b(REPO, False, lines)
        self.assertFalse(failed_a or failed_b, "\n".join(lines))
        self.assertTrue(any("<= shared cap" in line for line in lines))

    def test_llm_allocation_fits_the_shared_cap_with_hand_derived_numbers(self):
        allocation = read_json(os.path.join(EXPERIMENTS, "manifests", "llm-allocation.json"))
        self.assertEqual(allocation["schema"], "scholarchain.llm-allocation.v2")
        buckets = {name: entry["answers"] for name, entry in allocation["buckets"].items()}
        self.assertEqual(buckets, {"14c": 10, "15b": 60, "16b": 40, "17": 5})  # user decision 2026-11-08
        self.assertEqual(sum(buckets.values()), 115)
        # 115 x 0.01155 = 1.32825 <= 1.33
        self.assertEqual(round(115 * 0.01155, 5), 1.32825)
        self.assertEqual(allocation["shared_cap_usd"], "1.33")  # user decision 2026-11-09, lowered from 1.50
        self.assertLessEqual(115 * 0.01155, float(allocation["shared_cap_usd"]))
        # one more answer: 116 x 0.01155 = 1.3398 > 1.33, so the shared cap refuses it
        self.assertEqual(round(116 * 0.01155, 5), 1.3398)
        self.assertGreater(116 * 0.01155, float(allocation["shared_cap_usd"]))
        profile = read_json(os.path.join(REPO, "load-tests", "config", "load-profile.v1.json"))
        self.assertEqual(profile["llm"]["shared_cap_usd"], allocation["shared_cap_usd"])
        manifest = read_json(os.path.join(EXPERIMENTS, "manifests", "15b-ecs-scaling.json"))
        per_phase = {p["name"]: p.get("llm_answers", 0) for p in manifest["phases"] if p["type"] == "load"}
        self.assertEqual(per_phase, {"baseline-1": 10, "level-5": 15, "level-25": 20, "level-50": 15, "hold-50": 0})  # 10 / 15 / 20 / 15 = 60
        self.assertEqual(sum(per_phase.values()), buckets["15b"])
        profile = read_json(os.path.join(REPO, "load-tests", "config", "load-profile.v1.json"))
        self.assertEqual([profile["per_level"][k]["llm_answers"] for k in ("1", "5", "25", "50")], [10, 15, 20, 15])
        self.assertEqual(read_json(os.path.join(EXPERIMENTS, "manifests", "16b-live-evaluation.json"))["llm"]["answers"], buckets["16b"])

    def test_15b_manifest_covers_all_levels_and_a_scale_in_window(self):
        manifest = read_json(os.path.join(EXPERIMENTS, "manifests", "15b-ecs-scaling.json"))
        self.assertEqual({p["level"] for p in manifest["phases"] if p["type"] == "load"}, {1, 5, 25, 50})
        observe = [p for p in manifest["phases"] if p["type"] == "observe"]
        self.assertEqual(len(observe), 1)
        self.assertGreaterEqual(observe[0]["duration_seconds"], 15 * 60 + 300)  # 15 low minutes plus the 300 s scale-in cooldown
        self.assertFalse(manifest["llm"]["default_enabled"])


class Fixture(unittest.TestCase):
    """A scratch copy of the files check_manifests.py reads, so a test can change a manifest or a pin."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="exp-fixture-")
        self.addCleanup(shutil.rmtree, self.root, True)
        for relative in ("scripts/config", "scripts/lib", "experiments/manifests", "experiments/inputs", "load-tests/config"):
            shutil.copytree(os.path.join(REPO, relative), os.path.join(self.root, relative), ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("loadgen.py", "llm_budget.py"):
            shutil.copy(os.path.join(REPO, "load-tests", name), os.path.join(self.root, "load-tests", name))
        self.conf = os.path.join(self.root, "scripts", "config", "release.conf")

    def set_pin(self, key, value):
        with open(self.conf, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        lines = ["%s=%s" % (key, value) if line.startswith(key + "=") else line for line in lines]
        write_text(self.conf, "\n".join(lines) + "\n")

    def run_check(self, final=False):
        lines = []
        failed_a, blocked = check.check_15a(self.root, final, lines)
        failed_b = check.check_15b_16b(self.root, final, lines)
        return failed_a or failed_b, blocked, lines

    def manifest_path(self, name):
        return os.path.join(self.root, "experiments", "manifests", name)


class RenderAndCheck(Fixture):
    SHAS = ["--sha", "hadoop-submit-jar=%s" % ("1" * 64), "--sha", "hadoop-libjars=%s" % ("2" * 64), "--sha", "er-jar=%s" % ("3" * 64), "--sha", "job-jar=%s" % ("4" * 64),
            "--sha", "er-policy=%s" % ("5" * 64), "--sha", "er-config=%s" % ("6" * 64), "--sha", "spark-config-template=%s" % ("7" * 64)]

    def test_rendering_real_hashes_keeps_tokens_and_passes_the_final_check(self):
        self.set_pin("PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS", "12000")  # what the infra-engineer is asked to pin
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = render.main(["--out-dir", os.path.join(self.root, "experiments", "manifests"), "--overwrite"] + self.SHAS)
        self.assertEqual(rc, 0, out.getvalue())
        manifest = read_json(self.manifest_path("15a-emr-size-50.json"))
        self.assertEqual(manifest["pipeline"]["artifact_sha256"]["job-jar"], "4" * 64)
        self.assertEqual(manifest["pipeline"]["artifact_sha256"]["er-policy"], "5" * 64)
        self.assertIn("${SCHOLARCHAIN_ARTIFACTS_BUCKET}", manifest["pipeline"]["input_prefix"])  # tokens survive rendering
        for size in (25, 50, 100):
            rc, out_text = validate_with_run_experiments_validator(self.manifest_path("15a-emr-size-%d.json" % size))
            self.assertEqual((rc, out_text), (0, ""))
        failed, blocked, lines = self.run_check(final=True)
        self.assertFalse(failed or blocked, "\n".join(lines))

    def test_zero_hashes_pass_the_normal_check_but_fail_final(self):
        self.set_pin("PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS", "12000")
        failed, blocked, lines = self.run_check(final=False)
        self.assertFalse(failed or blocked, "\n".join(lines))
        failed, blocked, lines = self.run_check(final=True)
        self.assertTrue(failed)
        self.assertTrue(any("all-zero sha256" in line for line in lines))

    def test_a_literal_bucket_or_account_id_in_a_manifest_fails_even_without_final(self):
        self.set_pin("PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS", "12000")
        path = self.manifest_path("15a-emr-size-25.json")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        write_text(path, text.replace("${SCHOLARCHAIN_ARTIFACTS_BUCKET}", "scholarchain-course-%s-artifacts" % FAKE_ACCOUNT, 1))
        failed, _, lines = self.run_check(final=False)
        self.assertTrue(failed)
        self.assertTrue(any("12 digits" in line for line in lines))
        self.assertTrue(any("not the committed token" in line for line in lines))

    def test_a_ceiling_below_the_prep_config_is_reported_as_blocked_not_failed(self):
        self.set_pin("PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS", "1000")
        failed, blocked, lines = self.run_check()
        self.assertFalse(failed)
        self.assertTrue(blocked)
        self.assertTrue(any("CHECK-BLOCKED" in line and "maxLocalSampleRecords=12000" in line for line in lines))

    def test_budget_runtime_and_cumulative_violations_fail(self):
        self.set_pin("PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS", "12000")
        path = self.manifest_path("15a-emr-size-25.json")
        original = read_json(path)
        mutated = json.loads(json.dumps(original))
        mutated["budget"]["max_usd"] = 0.8  # below the 0.84 estimate
        write_text(path, json.dumps(mutated))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("G6 estimate 0.84 exceeds budget.max_usd 0.8" in line for line in lines))
        mutated = json.loads(json.dumps(original))
        mutated["budget"]["max_runtime_minutes"] = 120
        write_text(path, json.dumps(mutated))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("90 minutes" in line for line in lines))
        write_text(path, json.dumps(original))
        self.set_pin("EMR_CUMULATIVE_CAP_USD", "2.00")  # 3 x 0.84 = 2.52 no longer fits
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("cumulative cap" in line for line in lines))

    def test_allocation_over_the_shared_cap_fails(self):
        path = self.manifest_path("llm-allocation.json")
        allocation = read_json(path)
        allocation["buckets"]["16b"]["answers"] = 100  # 10 + 60 + 100 + 5 = 175 x 0.01155 = 2.02125 > 1.33
        write_text(path, json.dumps(allocation))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("exceeds the shared cap" in line for line in lines))

    def test_renderer_refuses_overwrite_and_bad_sha(self):
        out = io.StringIO()
        target = os.path.join(self.root, "rendered")
        with contextlib.redirect_stdout(out):
            self.assertEqual(render.main(["--out-dir", target]), 0)
            self.assertEqual(render.main(["--out-dir", target]), 1)  # exists
            self.assertEqual(render.main(["--out-dir", target + "2", "--sha", "job-jar=xyz"]), 1)
            self.assertEqual(render.main(["--out-dir", target + "3", "--sha", "unknown=" + HEX_A]), 1)
        self.assertEqual(read_json(os.path.join(target, "15a-emr-size-25.json")), read_json(os.path.join(EXPERIMENTS, "manifests", "15a-emr-size-25.json")))


class SubsetBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="exp-subsets-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        record = '<inproceedings mdate="2020-01-01" key="conf/%s/%s%02d">\n<author>%s</author>\n<author>Shared Person</author>\n<title>T%d.</title>\n<year>%d</year>\n</inproceedings>\n'
        order = [("podc", 8), ("wdag", 4), ("osdi", 1)]  # 8 podc, 4 wdag (counted as disc), 1 osdi; interleaved below
        items = []
        for venue, count in order:
            for i in range(count):
                items.append((venue, i))
        items.sort(key=lambda x: (x[1], x[0]))  # interleave: i=0 of each venue first, and so on
        self.expected_keys = ["conf/%s/%s%02d" % (v, v, i) for v, i in items]
        body = "".join(record % (v, v, i, "Author %s%d" % (v, i), n, 2000 + n) for n, (v, i) in enumerate(items))
        self.source_text = '<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n' + body + "</dblp>\n"
        self.source = os.path.join(self.tmp, "dblp.xml")
        write_text(self.source, self.source_text)
        self.samples = os.path.join(self.tmp, "samples")
        sums = []
        for name in subsets.SAMPLE_FILES:
            data = ("sample " + name).encode()
            os.makedirs(os.path.dirname(os.path.join(self.samples, name)), exist_ok=True)
            with open(os.path.join(self.samples, name), "wb") as handle:
                handle.write(data)
            sums.append("%s  samples/%s" % (hashlib.sha256(data).hexdigest(), name))
        write_text(os.path.join(self.samples, "SHA256SUMS"), "\n".join(sums) + "\n")
        self.out = os.path.join(self.tmp, "out")

    def build(self, sizes="25,50,100"):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = subsets.main(["--source", self.source, "--samples-dir", self.samples, "--output-root", self.out, "--sizes", sizes, "--skip-source-check", "--slice-manifest",
                               os.path.join(REPO, "datasets", "phase6", "dblp-slice-manifest.v1.json")])
        return rc, buffer.getvalue()

    def keys(self, percent):
        with open(os.path.join(self.out, "size-%d" % percent, "datasets", "samples", "dblp", "linked-records.xml"), encoding="utf-8") as handle:
            return [k for k in __import__("re").findall(r'key="([^"]+)"', handle.read())]

    def test_quota_rule_counts_are_hand_derived(self):
        rc, out = self.build()
        self.assertEqual(rc, 0, out)
        # venue sizes disc(=wdag) 4, osdi 1, podc 8.  25%: ceil(1)+ceil(.25)+ceil(2) = 1+1+2 = 4;  50%: 2+1+4 = 7;  100%: 13
        counts = {p: read_json(os.path.join(self.out, "size-%d.subset.json" % p))["counts"]["publications"] for p in (25, 50, 100)}
        self.assertEqual(counts, {25: 4, 50: 7, 100: 13})
        info = read_json(os.path.join(self.out, "size-50.subset.json"))
        self.assertEqual(info["counts"]["per_venue"], {"disc": 2, "osdi": 1, "podc": 4})
        # every record has 2 authors, 1 of them shared: 7 publications -> 14 authorships, 7 + 1 distinct strings
        self.assertEqual((info["counts"]["authorships"], info["counts"]["distinct_exact_author_strings"]), (14, 8))

    def test_sets_are_nested_ordered_and_the_full_size_is_byte_identical(self):
        self.assertEqual(self.build()[0], 0)
        k25, k50, k100 = self.keys(25), self.keys(50), self.keys(100)
        self.assertTrue(set(k25) <= set(k50) <= set(k100))
        self.assertEqual(k100, self.expected_keys)  # original order kept
        self.assertEqual(k50, [k for k in self.expected_keys if k in set(k50)])
        # the first records of each venue are the ones kept
        self.assertIn("conf/podc/podc00", k25)
        self.assertNotIn("conf/podc/podc07", k25)
        with open(os.path.join(self.out, "size-100", "datasets", "samples", "dblp", "linked-records.xml"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), self.source_text)
        self.assertTrue(read_json(os.path.join(self.out, "size-100.subset.json"))["byte_identical_to_source"])
        self.assertFalse(read_json(os.path.join(self.out, "size-25.subset.json"))["byte_identical_to_source"])

    def test_phase4_layout_and_unscaled_other_sources(self):
        self.assertEqual(self.build("50")[0], 0)
        base = os.path.join(self.out, "size-50", "datasets", "samples")
        for name in ("dblp/linked-records.xml", "openalex/works.jsonl", "crossref/works.jsonl", "orcid/records.jsonl"):
            self.assertTrue(os.path.isfile(os.path.join(base, name)), name)
        with open(os.path.join(base, "openalex", "works.jsonl"), "rb") as handle:
            self.assertEqual(handle.read(), b"sample openalex/works.jsonl")

    def test_existing_output_and_tampered_samples_are_refused(self):
        self.assertEqual(self.build("25")[0], 0)
        rc, out = self.build("25")
        self.assertEqual(rc, 1)
        self.assertIn("already exists", out)
        with open(os.path.join(self.samples, "orcid", "records.jsonl"), "ab") as handle:
            handle.write(b"x")
        self.out = os.path.join(self.tmp, "out2")
        rc, out = self.build("25")
        self.assertEqual(rc, 1)
        self.assertIn("SHA256SUMS", out)

    def test_source_that_does_not_match_the_slice_manifest_is_refused(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = subsets.main(["--source", self.source, "--samples-dir", self.samples, "--output-root", self.out])
        self.assertEqual(rc, 1)
        self.assertIn("does not match the slice manifest sha256", buffer.getvalue())

    def test_real_slice_quotas_from_the_committed_manifest(self):
        manifest = read_json(os.path.join(REPO, "datasets", "phase6", "dblp-slice-manifest.v1.json"))
        per_venue = manifest["selection"]["perVenue"]
        for percent, expected in ((25, 2648), (50, 5290), (100, 10577)):
            # hand-derived: sum over the eight venues of ceil(n * P / 100) with integer arithmetic
            self.assertEqual(sum(-(-n * percent // 100) for n in per_venue.values()), expected)
        self.assertEqual(sum(per_venue.values()), manifest["selection"]["publicationCount"])

    @unittest.skipUnless(os.path.isfile(os.path.join(REPO, subsets.DEFAULT_SOURCE)), "the ignored Phase 6 slice file is not present")
    def test_real_slice_subsets_match_the_hand_derived_counts(self):
        manifest = read_json(os.path.join(REPO, "datasets", "phase6", "dblp-slice-manifest.v1.json"))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = subsets.main(["--output-root", self.out])
        self.assertEqual(rc, 0, buffer.getvalue())
        got = {p: read_json(os.path.join(self.out, "size-%d.subset.json" % p)) for p in (25, 50, 100)}
        self.assertEqual({p: g["counts"]["publications"] for p, g in got.items()}, {25: 2648, 50: 5290, 100: 10577})
        self.assertEqual(got[100]["counts"]["distinct_exact_author_strings"], manifest["selection"]["distinctExactAuthorStrings"])
        self.assertTrue(got[100]["byte_identical_to_source"])
        self.assertEqual(got[100]["dblp_file_sha256"], manifest["output"]["sha256"])


if __name__ == "__main__":
    unittest.main()

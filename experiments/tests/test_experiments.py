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
build_l = load("build_l_under_test", "experiments/scripts/build_l_input.py")
LABELS = ("size-25", "size-50", "size-100")  # the EMR set: Session 1 history (25, 50) and size S (100); L is local evidence only
L_EVIDENCE = os.path.join(EXPERIMENTS, "inputs", "15a", "size-l-local-evidence.json")
TOKEN_ROOT = "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}"
PATH_KEYS = ("hadoopRunRoot", "entityResolutionRunRoot", "outputRoot", "checkpointDirectory")
HEX_A = "a" * 64
FAKE_ACCOUNT = "1" * 6 + "2" * 6  # built at runtime: no 12-digit literal in the source
DIGIT_HASH = ("1234" * 4) * 4  # a 64-character sha256 made of digits only


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def zero_artifact_hashes(manifest):
    """The renderer writes exactly one set of sha256 values: pipeline.artifact_sha256 (one per artifact name). Returns a copy with each set to 64 zeros,
    which makes a committed manifest comparable whether it carries the all-zero placeholders or real hashes."""
    zeroed = json.loads(json.dumps(manifest))
    for name in zeroed["pipeline"]["artifact_sha256"]:
        zeroed["pipeline"]["artifact_sha256"][name] = "0" * 64
    return zeroed


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
        for label in LABELS:
            path = os.path.join(EXPERIMENTS, "manifests", "15a-emr-%s.json" % label)
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
        for label in LABELS:
            size = label[len("size-"):]
            manifest = read_json(os.path.join(EXPERIMENTS, "manifests", "15a-emr-%s.json" % label))
            self.assertEqual(manifest["id"], "15a-emr-size-%s" % size)
            self.assertEqual(manifest["teardown"], {"mode": "auto-termination", "max_idle_timeout_seconds": 900})
            self.assertEqual(manifest["budget"]["max_capacity"], 1 + manifest["pipeline"]["core_count"] + manifest["pipeline"]["max_task_count"])
            # history 0.84 (90 min); size S 1.25 (120 min, human 2026-11-24, docs/agent-runs/phase-18/human-gate.md)
            self.assertEqual((manifest["budget"]["max_capacity"], manifest["budget"]["max_usd"], manifest["pipeline"]["instance_type"]), (2, 1.25 if label == "size-100" else 0.84, "m5.xlarge"))
            self.assertEqual(manifest["pipeline"]["input_prefix"], "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/input/size-%s" % size)
            self.assertEqual(manifest["pipeline"]["output_prefix"], "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/pipeline/${SCHOLARCHAIN_RUN_PREFIX}/15a/size-%s" % size)
            self.assertEqual(manifest["metrics"]["locations"], ["s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/pipeline/${SCHOLARCHAIN_RUN_PREFIX}/15a/size-%s/metrics/" % size])

    def test_size_s_is_the_120_minute_r5_primary_run(self):
        manifest = read_json(os.path.join(EXPERIMENTS, "manifests", "15a-emr-size-100.json"))
        # user, 2026-11-16 ("S run cap and D3 go-ahead"): r5.xlarge primary, m5.xlarge core, no task nodes; the cap was 75 minutes, raised to 120
        # (max_usd 0.84 -> 1.25) by the human on 2026-11-24 ("Raise to 120 min", docs/agent-runs/phase-18/human-gate.md)
        self.assertEqual(manifest["budget"]["max_runtime_minutes"], 120)
        self.assertEqual(manifest["budget"]["max_usd"], 1.25)
        self.assertEqual((manifest["pipeline"]["primary_instance_type"], manifest["pipeline"]["instance_type"]), ("r5.xlarge", "m5.xlarge"))
        self.assertEqual((manifest["pipeline"]["core_count"], manifest["pipeline"]["max_task_count"]), (1, 0))
        # P1: the Hadoop prep config is an uploaded artifact (the key the infra-engineer's --hadoop-config option writes), pinned by sha256
        self.assertEqual(manifest["pipeline"]["hadoop_config"], TOKEN_ROOT + "/config/hadoop-config.json")
        self.assertEqual(manifest["pipeline"]["spark_config_template"], TOKEN_ROOT + "/config/spark-config-template.json")
        self.assertIn("hadoop-config", manifest["pipeline"]["artifact_sha256"])

    def test_session1_history_manifests_are_the_committed_bytes(self):
        # Session 1's m5.xlarge runs stay as the ledger history: unchanged since commit 7a02de2 (hashes taken from that commit)
        expected = {"15a-emr-size-25.json": "a6ff25a35888685e3007a37d2c9de01c8779c330cbbac1c1d8ff7b38dab5e102",
                    "15a-emr-size-50.json": "0d7fe029b4bad906d7b37af1e09ed05f573964556cb67ee0f1a5fecdcd0902a0"}
        for name, digest in expected.items():
            with open(os.path.join(EXPERIMENTS, "manifests", name), "rb") as handle:
                self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), digest, name)
            self.assertEqual(read_json(os.path.join(EXPERIMENTS, "manifests", name))["budget"]["max_runtime_minutes"], 90)

    def test_no_emr_manifest_exists_for_size_l(self):
        self.assertFalse(any("size-l" in n for n in os.listdir(os.path.join(EXPERIMENTS, "manifests"))))
        evidence = read_json(L_EVIDENCE)
        self.assertTrue(evidence["emr"].startswith("NOT an EMR run"))
        self.assertEqual(evidence["identityBypassSpark"]["disclosure"], "ER bypassed: identity pass-through (no cross-source resolution), local only, not the EMR path")
        self.assertEqual(evidence["slice"]["publicationCount"], 48187)

    def test_g6_estimate_is_hand_derived(self):
        manifest = read_json(os.path.join(EXPERIMENTS, "manifests", "15a-emr-size-25.json"))
        pricing = {"EMR_RATE_EC2_M5_XLARGE": "0.192", "EMR_RATE_EMR_M5_XLARGE": "0.048", "EMR_RATE_EC2_R5_XLARGE": "0.252", "EMR_RATE_EMR_R5_XLARGE": "0.063"}
        # 2 instances x 0.240 USD/h x (90 min + 900 s idle = 6300 s = 1.75 h) = 0.84
        self.assertEqual(str(check.g6_estimate(manifest, pricing)), "0.84")
        manifest["pipeline"]["max_task_count"] = 1
        self.assertEqual(str(check.g6_estimate(manifest, pricing)), "1.26")  # 3 x 0.24 x 1.75
        s = read_json(os.path.join(EXPERIMENTS, "manifests", "15a-emr-size-100.json"))
        # D3: primary r5.xlarge 0.252 + 0.063 = 0.315/h, core m5.xlarge 0.240/h; (120 min + 900 s) = 2.25 h; 0.555 x 2.25 = 1.24875 -> 1.25
        self.assertEqual(str(check.g6_estimate(s, pricing)), "1.25")
        s["budget"]["max_runtime_minutes"] = 75  # the former cap: 0.555 x 1.5 = 0.8325 -> 0.84
        self.assertEqual(str(check.g6_estimate(s, pricing)), "0.84")
        s["budget"]["max_runtime_minutes"] = 90  # 0.555 x 1.75 = 0.97125 -> 0.98
        self.assertEqual(str(check.g6_estimate(s, pricing)), "0.98")
        s["budget"]["max_runtime_minutes"] = 60  # 0.555 x 1.25 = 0.69375 -> 0.70
        self.assertEqual(str(check.g6_estimate(s, pricing)), "0.70")

    def test_committed_prep_config_passes_every_ceiling_except_the_sample_bound(self):
        prep = read_json(os.path.join(EXPERIMENTS, "inputs", "15a", "prep-config.json"))
        conf = check.read_conf(os.path.join(REPO, "scripts", "config", "release.conf"))
        over = [field for field, key in check.CEILING_KEYS if prep[field] > int(conf[key])]
        # The only violation may be maxLocalSampleRecords until the infra-engineer's matching pin lands (BLOCKED-ON); any other field is a defect.
        self.assertTrue(set(over) <= {"maxLocalSampleRecords"}, over)
        # P22: L at most 50,000 DBLP records (TARGET_MAX of the dataset-engineer's selector) + 3 one-line committed samples = 50,003, rounded up to 60,000
        self.assertEqual(prep["maxLocalSampleRecords"], 60000)
        self.assertEqual(check.other_source_records(REPO), 3)
        self.assertGreaterEqual(prep["maxLocalSampleRecords"], check.L_PLANNING_MAX + 3)

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
        self.assertEqual(buckets, {"14c": 10, "15b": 60, "16b": 80, "17": 10})  # user decisions 2026-11-08 and 2026-11-21 (option A: 16b 40 -> 80, 17 5 -> 10)
        self.assertEqual(sum(buckets.values()), 160)
        # 160 x 0.001365 = 0.2184 <= 1.33 (claude-haiku-5-5: 7,150 in x 0.10 + 1,300 out x 0.50 per 1M tokens)
        self.assertEqual(round(160 * 0.001365, 6), 0.2184)
        self.assertEqual(allocation["shared_cap_usd"], "1.33")  # user decision 2026-11-09, lowered from 1.50
        self.assertLessEqual(160 * 0.001365, float(allocation["shared_cap_usd"]))
        # 1.33 is a conservative upper bound now: the cap would hold 974 answers (974 x 0.001365 = 1.32951) and not 975 (1.330875)
        self.assertLessEqual(974 * 0.001365, float(allocation["shared_cap_usd"]))
        self.assertGreater(975 * 0.001365, float(allocation["shared_cap_usd"]))
        # the per-bucket estimates in USD
        self.assertEqual([round(n * 0.001365, 6) for n in (10, 60, 80, 10)], [0.01365, 0.0819, 0.1092, 0.01365])
        profile = read_json(os.path.join(REPO, "load-tests", "config", "load-profile.v1.json"))
        self.assertEqual(profile["llm"]["shared_cap_usd"], allocation["shared_cap_usd"])
        manifest = read_json(os.path.join(EXPERIMENTS, "manifests", "15b-ecs-scaling.json"))
        per_phase = {p["name"]: p.get("llm_answers", 0) for p in manifest["phases"] if p["type"] == "load"}
        self.assertEqual(per_phase, {"baseline-1": 10, "level-5": 15, "level-25": 20, "level-50": 15, "hold-50": 0})  # 10 / 15 / 20 / 15 = 60
        self.assertEqual(sum(per_phase.values()), buckets["15b"])
        profile = read_json(os.path.join(REPO, "load-tests", "config", "load-profile.v1.json"))
        self.assertEqual([profile["per_level"][k]["llm_answers"] for k in ("1", "5", "25", "50")], [10, 15, 20, 15])
        self.assertEqual(read_json(os.path.join(EXPERIMENTS, "manifests", "16b-live-evaluation.json"))["llm"]["answers"], buckets["16b"])

    def test_allocation_and_15b_notes_state_the_current_unit_and_route(self):
        allocation = read_json(os.path.join(EXPERIMENTS, "manifests", "llm-allocation.json"))
        m15b = read_json(os.path.join(EXPERIMENTS, "manifests", "15b-ecs-scaling.json"))
        m16b = read_json(os.path.join(EXPERIMENTS, "manifests", "16b-live-evaluation.json"))
        for text in (allocation["note"], m15b["llm"]["note"]):
            self.assertIn("0.001365", text)
            self.assertNotIn("0.01155", text)
        self.assertIn("USD 0.0819", m15b["llm"]["note"])
        self.assertIn("claude-haiku-5-5", allocation["note"])
        self.assertIn("us.anthropic.claude-haiku-4-5-20251001-v1:0", allocation["note"])  # the Bedrock fallback is named
        self.assertIn("USD 0.1092", m16b["llm"]["draws_from"])
        emb = m16b["llm"]["embeddings"]
        self.assertEqual((emb["provider"], emb["model"], emb["output_dimension"], emb["cap_usd"]), ("voyage", "voyage-4-lite", 256, "0.30"))
        self.assertIn("USD 0.02 per 1M tokens", emb["price"])
        self.assertIn("AWS, Anthropic and Voyage", m16b["llm"]["cost_reporting"])

    def test_check_script_checks_unit_text_and_embeddings_block(self):
        lines = []
        check.check_15b_16b(REPO, False, lines)
        text = "\n".join(lines)
        self.assertIn("per-bucket estimates (USD) 14c 0.013650, 15b 0.081900, 16b 0.109200, 17 0.013650, total 0.218400", text)
        self.assertIn("embeddings voyage-4-lite 256 dims USD 0.02 per 1M tokens, first 200M tokens free, cap USD 0.30", text)

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
        evidence = os.path.join("docs", "agent-runs", "phase-15", "evidence", "session-2", "emr", "emr-actual-1end.log")  # the Session 2 S attempt
        os.makedirs(os.path.join(self.root, os.path.dirname(evidence)))
        shutil.copy(os.path.join(REPO, evidence), os.path.join(self.root, evidence))
        for name in ("loadgen.py", "llm_budget.py"):
            shutil.copy(os.path.join(REPO, "load-tests", name), os.path.join(self.root, "load-tests", name))
        self.conf = os.path.join(self.root, "scripts", "config", "release.conf")
        for entry in read_json(os.path.join(EXPERIMENTS, "inputs", "15a", "config-sources.json"))["files"].values():  # files outside experiments/
            target = os.path.join(self.root, entry["path"])
            if not os.path.exists(target):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy(os.path.join(REPO, entry["path"]), target)

    def pin_session2(self):
        """The pins the infra-engineer is asked for: the P22 sample ceiling and the EMR ledger (5 runs, 4.70 USD cap; human 2026-11-24, 120-minute S
        cap and one more retry, docs/agent-runs/phase-18/human-gate.md; the P25 pins were 4 runs and 3.53 USD)."""
        self.set_pin("PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS", "60000")
        self.set_pin("EMR_MAX_LIVE_RUNS", "5")
        self.set_pin("EMR_CUMULATIVE_CAP_USD", "4.70")

    def write_l_slice(self, count=48187, sha=None):
        evidence = read_json(L_EVIDENCE)["slice"]
        path = os.path.join(self.root, "datasets", "phase15", "dblp-l-slice-manifest.v1.json")
        write_text(path, json.dumps({"selection": {"publicationCount": count}, "output": {"sha256": sha or evidence["sha256"]}, "nestingCheck": {"result": "PASS"}}))
        return path

    def render_into_fixture(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = render.main(["--out-dir", os.path.join(self.root, "experiments", "manifests"), "--overwrite"] + list(extra))
        return rc, out.getvalue()

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
    SHAS = ["--sha", "hadoop-submit-jar=%s" % ("1" * 64), "--sha", "hadoop-libjars=%s" % ("2" * 64), "--sha", "er-jar=%s" % ("3" * 64), "--sha", "job-jar=%s" % ("4" * 64)]

    def config_sha(self, name):
        entry = read_json(os.path.join(EXPERIMENTS, "inputs", "15a", "config-sources.json"))["files"][name]
        with open(os.path.join(REPO, entry["path"]), "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

    def test_rendering_real_hashes_keeps_tokens_and_passes_the_final_check(self):
        self.pin_session2()
        history = {n: read_json(self.manifest_path(n)) for n in ("15a-emr-size-25.json", "15a-emr-size-50.json")}
        rc, out = self.render_into_fixture(*self.SHAS)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.count("RENDERED"), 1)  # only size S; the Session 1 history is never rewritten
        for name, document in history.items():
            self.assertEqual(read_json(self.manifest_path(name)), document, name)
        manifest = read_json(self.manifest_path("15a-emr-size-100.json"))
        self.assertEqual(manifest["pipeline"]["artifact_sha256"]["job-jar"], "4" * 64)
        # the four configuration hashes come from the repository files themselves, not from --sha
        for name in ("hadoop-config", "er-policy", "er-config", "spark-config-template"):
            self.assertEqual(manifest["pipeline"]["artifact_sha256"][name], self.config_sha(name), name)
        self.assertIn("${SCHOLARCHAIN_ARTIFACTS_BUCKET}", manifest["pipeline"]["input_prefix"])  # tokens survive rendering
        for label in LABELS:
            rc, out_text = validate_with_run_experiments_validator(self.manifest_path("15a-emr-%s.json" % label))
            self.assertEqual((rc, out_text), (0, ""))
        failed, blocked, lines = self.run_check(final=True)
        self.assertFalse(failed or blocked, "\n".join(lines))

    def test_zero_hashes_pass_the_normal_check_but_fail_final(self):
        self.pin_session2()
        self.assertEqual(self.render_into_fixture()[0], 0)  # the default all-zero JAR hashes
        failed, blocked, lines = self.run_check(final=False)
        self.assertFalse(failed or blocked, "\n".join(lines))
        failed, blocked, lines = self.run_check(final=True)
        self.assertTrue(failed)
        self.assertTrue(any("15a-emr-size-100.json: an all-zero sha256" in line for line in lines))

    def test_a_config_sha_that_differs_from_the_repository_file_is_refused_by_render_and_check(self):
        self.pin_session2()
        rc, out = self.render_into_fixture("--sha", "er-policy=%s" % ("5" * 64))
        self.assertEqual(rc, 1)
        self.assertIn("RENDER-REFUSED: --sha er-policy=", out)
        rc, out = self.render_into_fixture("--sha", "hadoop-config=%s" % self.config_sha("hadoop-config"))  # the same value is accepted
        self.assertEqual(rc, 0, out)
        path = self.manifest_path("15a-emr-size-100.json")
        manifest = read_json(path)
        manifest["pipeline"]["artifact_sha256"]["spark-config-template"] = "753adaeccd524d4fdfa6028bb0a7af6394e461021dfb013587a87c24eafcf458"  # the old Phase 6 pin
        write_text(path, json.dumps(manifest))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("artifact_sha256.spark-config-template=753adaec" in line and "re-render" in line for line in lines))

    def test_hadoop_config_must_be_the_uploaded_s3_key(self):
        self.pin_session2()
        path = self.manifest_path("15a-emr-size-100.json")
        manifest = read_json(path)
        manifest["pipeline"]["hadoop_config"] = "experiments/inputs/15a/prep-config.json"  # the old local form
        write_text(path, json.dumps(manifest))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("pipeline.hadoop_config must be s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/config/hadoop-config.json" in line for line in lines))

    def test_a_drifted_config_file_fails(self):
        self.pin_session2()
        prep_path = os.path.join(self.root, "experiments", "inputs", "15a", "prep-config.json")
        prep = read_json(prep_path)
        prep["maxLocalSampleRecords"] = 59999
        write_text(prep_path, json.dumps(prep))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("hadoop-config (experiments/inputs/15a/prep-config.json) has sha256" in line for line in lines))

    def test_l_slice_manifest_binds_the_evidence_record_and_the_sample_bound(self):
        self.pin_session2()
        self.write_l_slice(count=48187)
        failed, blocked, lines = self.run_check()
        self.assertFalse(failed or blocked, "\n".join(lines))
        self.assertTrue(any("maxLocalSampleRecords=60000 >= 48190 = the L slice manifest publicationCount 48187 + 3 other-source records" in line for line in lines))
        self.assertTrue(any("size L is local evidence only" in line for line in lines))
        self.write_l_slice(count=48188)  # the slice changed: the evidence record is stale
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("size-l-local-evidence.json states 48187 publications" in line for line in lines))
        self.write_l_slice(count=59998)  # 59,998 + 3 = 60,001 > 60,000
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("maxLocalSampleRecords=60000 < 60001" in line for line in lines))

    def test_an_emr_manifest_for_size_l_or_any_other_size_is_refused(self):
        self.pin_session2()
        s = read_json(self.manifest_path("15a-emr-size-100.json"))
        s["id"] = "15a-emr-size-l"
        write_text(self.manifest_path("15a-emr-size-l.json"), json.dumps(s))
        failed, _, lines = self.run_check(final=True)
        self.assertTrue(failed)
        self.assertTrue(any("CHECK-FAILED: 15a-emr-size-l.json is not in the EMR run set" in line and "local evidence only" in line for line in lines))
        self.assertTrue(any("15A ledger reserves 4.55 USD over 5 runs" in line for line in lines))  # the refused manifest is not charged

    def test_size_s_is_required_and_must_keep_the_d3_types_and_the_120_minute_cap(self):
        self.pin_session2()
        path = self.manifest_path("15a-emr-size-100.json")
        original = read_json(path)
        mutated = json.loads(json.dumps(original))
        del mutated["pipeline"]["primary_instance_type"]  # an m5.xlarge primary
        write_text(path, json.dumps(mutated))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("primary/core types are m5.xlarge/m5.xlarge; D3 approved r5.xlarge primary and m5.xlarge core" in line for line in lines))
        mutated = json.loads(json.dumps(original))
        mutated["budget"]["max_runtime_minutes"] = 150  # 0.555 x 2.75 = 1.52625 -> 1.53, above the 1.25 budget and the 120-minute pin
        write_text(path, json.dumps(mutated))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("G6 estimate 1.53 exceeds budget.max_usd 1.25" in line for line in lines))
        self.assertTrue(any("max_runtime_minutes is 150 but the approved cap for size S run and one retry is 120 minutes" in line for line in lines))
        mutated = json.loads(json.dumps(original))
        mutated["budget"]["max_runtime_minutes"] = 75  # the former cap is no longer the approved one
        mutated["budget"]["max_usd"] = 0.84
        write_text(path, json.dumps(mutated))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("max_runtime_minutes is 75 but the approved cap for size S run and one retry is 120 minutes" in line for line in lines))
        os.remove(path)
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("needs 15a-emr-size-100.json (size S)" in line for line in lines))

    def test_a_missing_or_wrong_l_evidence_record_fails(self):
        self.pin_session2()
        path = os.path.join(self.root, "experiments", "inputs", "15a", "size-l-local-evidence.json")
        evidence = read_json(path)
        evidence["emr"] = "planned on EMR"
        write_text(path, json.dumps(evidence))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("must be scholarchain.experiment-local-evidence.v1 and state that L is NOT an EMR run" in line for line in lines))
        os.remove(path)
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("size-l-local-evidence.json is missing" in line for line in lines))

    def test_keep_jar_shas_copies_the_jar_hashes_from_size_s(self):
        self.pin_session2()
        self.assertEqual(self.render_into_fixture(*self.SHAS)[0], 0)
        self.assertEqual(self.render_into_fixture("--keep-jar-shas")[0], 0)
        shas = read_json(self.manifest_path("15a-emr-size-100.json"))["pipeline"]["artifact_sha256"]
        self.assertEqual([shas[n] for n in render.JAR_SHA_NAMES], ["1" * 64, "2" * 64, "3" * 64, "4" * 64])

    def test_a_literal_bucket_or_account_id_in_a_manifest_fails_even_without_final(self):
        self.pin_session2()
        path = self.manifest_path("15a-emr-size-25.json")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        write_text(path, text.replace("${SCHOLARCHAIN_ARTIFACTS_BUCKET}", "scholarchain-course-%s-artifacts" % FAKE_ACCOUNT, 1))
        failed, _, lines = self.run_check(final=False)
        self.assertTrue(failed)
        self.assertTrue(any("12 digits" in line for line in lines))
        self.assertTrue(any("not the committed token" in line for line in lines))

    def test_a_ceiling_below_the_prep_config_is_reported_as_blocked_not_failed(self):
        self.pin_session2()
        self.set_pin("PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS", "12000")  # the pre-P22 pin
        failed, blocked, lines = self.run_check()
        self.assertFalse(failed)
        self.assertTrue(blocked)
        self.assertTrue(any("CHECK-BLOCKED" in line and "maxLocalSampleRecords=60000" in line for line in lines))

    def test_budget_runtime_and_cumulative_violations_fail(self):
        self.pin_session2()
        failed, blocked, lines = self.run_check()
        self.assertFalse(failed or blocked, "\n".join(lines))
        # The ledger holds Session 1 history 0.84 + 0.84, the Session 2 S attempt of 2026-11-18 recorded at 0.37 (emr-actual-1end.log:9-10), then S and
        # one S retry 1.25 + 1.25: 4.55 USD of reserves over 5 runs against the 4.70 USD / 5-run cap, margin 0.15 USD and no spare run
        self.assertTrue(any("15A ledger reserves 4.55 USD over 5 runs (Session 1 history 1.68 + Session 2 S attempt as recorded 0.37 + S + one S retry) <= cumulative cap 4.70 USD / 5 runs (margin 0.15 USD against the reserves, 0 spare runs)" in line for line in lines))
        # the stricter admission rule of scripts/lib/budget.py: recorded 2.05, idle tail 0.14, measured bound 4.70 - 2.05 - 0.14 - 1.25 = 1.26, margin 0.01
        self.assertTrue(any("recorded 2.05 USD (Session 1 history 1.68 + Session 2 attempt 0.37)" in line and "4.70 - 2.05 - 0.14 - 1.25 = 1.26" in line
                            and "leaves a margin of 0.01 USD" in line for line in lines))
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
        self.assertTrue(any("max_runtime_minutes is 120 but the approved cap for Session 1 history is 90 minutes" in line for line in lines))
        write_text(path, json.dumps(original))
        self.set_pin("EMR_CUMULATIVE_CAP_USD", "3.53")  # the pre-Phase-18 ledger cap (P25): a pin owned elsewhere
        failed, blocked, lines = self.run_check()
        self.assertFalse(failed, "\n".join(lines))
        self.assertTrue(blocked)
        self.assertTrue(any("CHECK-BLOCKED: 15A ledger reserves 4.55 USD over 5 runs" in line and "cumulative cap 3.53 USD" in line for line in lines))
        self.set_pin("EMR_CUMULATIVE_CAP_USD", "4.54")  # 4.18 (Session 2 attempt dropped from the model) would fit; 4.55 does not
        failed, blocked, lines = self.run_check()
        self.assertTrue(blocked and not failed)
        self.assertTrue(any("CHECK-BLOCKED: 15A ledger reserves 4.55 USD" in line for line in lines))
        self.set_pin("EMR_CUMULATIVE_CAP_USD", "4.70")
        self.set_pin("EMR_MAX_LIVE_RUNS", "4")  # the real ledger already holds 3 runs, so S plus one retry is run 5: 4 runs cannot hold it
        failed, blocked, lines = self.run_check()
        self.assertTrue(blocked and not failed)
        self.assertTrue(any("CHECK-BLOCKED: 15A ledger reserves 4.55 USD over 5 runs" in line and "/ 4 runs pinned" in line for line in lines))

    def test_the_stricter_admission_rule_blocks_even_when_the_reserves_fit(self):
        """4.68 holds the 4.55 reserves, but run 5 after a run 4 at its full 1.25 estimate needs 2.05 + 1.25 + 0.14 + 1.25 = 4.69 (budget.py ledger_problems)."""
        self.pin_session2()
        self.set_pin("EMR_CUMULATIVE_CAP_USD", "4.69")  # margin exactly 0.00: still admitted
        failed, blocked, lines = self.run_check()
        self.assertFalse(failed or blocked, "\n".join(lines))
        self.assertTrue(any("leaves a margin of 0.00 USD" in line for line in lines))
        self.set_pin("EMR_CUMULATIVE_CAP_USD", "4.68")
        failed, blocked, lines = self.run_check()
        self.assertTrue(blocked and not failed)
        self.assertFalse(any("CHECK-BLOCKED: 15A ledger reserves" in line for line in lines))  # the reserves figure (4.55) still fits
        self.assertTrue(any("CHECK-BLOCKED: 15A real admission" in line and "leaves a margin of -0.01 USD" in line for line in lines))

    def test_the_session_2_attempt_is_modelled_from_its_committed_evidence(self):
        self.pin_session2()
        path = os.path.join(self.root, check.SESSION2_EVIDENCE)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        write_text(path, text.replace("measured_usd=0.37", "measured_usd=0.38"))  # the recorded figure changed: the model is stale
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("no longer states measured_usd=0.37 tail_seconds=0 tail_usd=0.00" in line for line in lines))
        os.remove(path)
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("emr-actual-1end.log is missing" in line for line in lines))

    def test_allocation_over_the_shared_cap_fails(self):
        path = self.manifest_path("llm-allocation.json")
        allocation = read_json(path)
        allocation["buckets"]["16b"]["answers"] = 1000  # 10 + 60 + 1000 + 10 = 1080 x 0.001365 = 1.4742 > 1.33
        write_text(path, json.dumps(allocation))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("exceeds the shared cap" in line for line in lines))

    def test_a_stale_unit_in_the_allocation_note_fails(self):
        path = self.manifest_path("llm-allocation.json")
        allocation = read_json(path)
        allocation["note"] = allocation["note"].replace("0.001365", "0.01155")
        write_text(path, json.dumps(allocation))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("llm-allocation.json does not state the pinned cost per answer 0.001365" in line for line in lines))

    def test_a_changed_embeddings_block_or_route_fails(self):
        path = os.path.join(self.root, "load-tests", "config", "load-profile.v1.json")
        original = read_json(path)
        mutated = json.loads(json.dumps(original))
        mutated["embeddings"]["cap_usd"] = "0.50"
        write_text(path, json.dumps(mutated))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("embeddings block must be voyage / voyage-4-lite / 256" in line for line in lines))
        mutated = json.loads(json.dumps(original))
        mutated["llm"]["pricing"]["model_route"] = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        write_text(path, json.dumps(mutated))
        failed, _, lines = self.run_check()
        self.assertTrue(failed)
        self.assertTrue(any("must price claude-haiku-5-5 on the Anthropic API" in line for line in lines))

    def test_renderer_refuses_overwrite_and_bad_sha(self):
        out = io.StringIO()
        target = os.path.join(self.root, "rendered")
        with contextlib.redirect_stdout(out):
            self.assertEqual(render.main(["--out-dir", target]), 0)
            self.assertEqual(render.main(["--out-dir", target]), 1)  # exists
            self.assertEqual(render.main(["--out-dir", target + "2", "--sha", "job-jar=xyz"]), 1)
            self.assertEqual(render.main(["--out-dir", target + "3", "--sha", "unknown=" + HEX_A]), 1)
        self.assertEqual(sorted(os.listdir(target)), ["15a-emr-size-100.json"])
        committed = read_json(os.path.join(EXPERIMENTS, "manifests", "15a-emr-size-100.json"))
        self.assertEqual(zero_artifact_hashes(read_json(os.path.join(target, "15a-emr-size-100.json"))), zero_artifact_hashes(committed))  # equal in structure whether the hashes are zero or real


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


class SparkEmrTemplate(unittest.TestCase):
    """P24: the experiment-owned EMR Spark template (both sizes) is the Phase 6 first-run config with 64 shuffle partitions and neutral path keys."""

    def setUp(self):
        self.template = read_json(os.path.join(EXPERIMENTS, "inputs", "15a", "spark-emr-template.json"))
        self.phase6 = read_json(os.path.join(REPO, "docs", "agent-runs", "phase-06", "evidence", "6fg", "local-spark-first-config.json"))

    def test_only_the_shuffle_partitions_and_the_four_replaced_path_keys_differ_from_phase6(self):
        self.assertEqual(list(self.template), list(self.phase6))  # same keys, same order
        differ = sorted(k for k in self.template if self.template[k] != self.phase6[k])
        self.assertEqual(differ, sorted(PATH_KEYS + ("shufflePartitions",)))
        self.assertEqual((self.phase6["shufflePartitions"], self.template["shufflePartitions"]), (4, 64))  # the accepted 14C export value
        for key in PATH_KEYS:
            self.assertEqual(self.template[key], "/replaced-at-run-time/" + key)  # no local user path is uploaded

    def test_the_phase6_evidence_file_is_unchanged(self):
        with open(os.path.join(REPO, "docs", "agent-runs", "phase-06", "evidence", "6fg", "local-spark-first-config.json"), "rb") as handle:
            self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), "753adaeccd524d4fdfa6028bb0a7af6394e461021dfb013587a87c24eafcf458")

    def test_the_template_has_exactly_the_fields_of_the_core_contract(self):
        contract = read_json(os.path.join(REPO, "modules", "core", "src", "main", "resources", "scholarchain.spark-analytics-config.v1.json"))
        self.assertEqual(sorted(self.template), sorted(contract))  # SparkAnalyticsConfigLoader rejects unknown and missing fields
        self.assertEqual(self.template["configSchemaVersion"], contract["configSchemaVersion"])

    def test_the_emr_render_step_replaces_exactly_the_four_path_keys(self):
        with tempfile.TemporaryDirectory(prefix="spark-render-") as scratch:
            out = os.path.join(scratch, "rendered.json")
            args = ["/mnt/x/hadoop", "/mnt/x/er", "/mnt/x/spark", "/mnt/x/checkpoints"]
            done = subprocess.run([sys.executable, "-I", os.path.join(REPO, "scripts", "emr", "sc-render-spark-config.py"),
                                   os.path.join(EXPERIMENTS, "inputs", "15a", "spark-emr-template.json"), out] + args, capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
            rendered = read_json(out)
        self.assertEqual([rendered[k] for k in PATH_KEYS], args)
        self.assertEqual({k: v for k, v in rendered.items() if k not in PATH_KEYS}, {k: v for k, v in self.template.items() if k not in PATH_KEYS})


class LInput(unittest.TestCase):
    """P21: --tree-label and the one-command L build (synthetic S and L slices; the real run is recorded in the lane report)."""

    RECORD = '<inproceedings mdate="2020-01-01" key="conf/%s/k%05d">\n<author>A%d</author>\n<author>B%d</author>\n<title>T.</title>\n<year>2010</year>\n</inproceedings>'

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="exp-l-input-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # L: 10,600 records (the renderer requires more than the 10,577-work S slice); S: the podc records, a strict subset
        records = [self.RECORD % ("podc" if i < 300 else "usenix", i, i, i) for i in range(10600)]
        frame = lambda rs: '<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n' + "\n".join(rs) + "\n</dblp>\n"
        self.l_xml = os.path.join(self.tmp, "l", "dblp.xml")
        self.s_xml = os.path.join(self.tmp, "s", "dblp.xml")
        write_text(self.l_xml, frame(records))
        write_text(self.s_xml, frame(records[:300]))
        sha = build_l.sha256_file
        self.s_manifest = os.path.join(self.tmp, "s-manifest.json")
        write_text(self.s_manifest, json.dumps({"output": {"sha256": sha(self.s_xml)}, "selection": {"publicationCount": 300}}))
        self.l_manifest = os.path.join(self.tmp, "l-manifest.json")
        self.l_doc = {"output": {"path": self.l_xml, "sha256": sha(self.l_xml)}, "selection": {"publicationCount": 10600},
                      "nestingCheck": {"result": "PASS", "sManifest": {"sha256": sha(self.s_manifest)}}}
        write_text(self.l_manifest, json.dumps(self.l_doc))
        self.evidence = os.path.join(self.tmp, "size-l-local-evidence.json")
        write_text(self.evidence, json.dumps({"slice": {"publicationCount": 10600, "sha256": sha(self.l_xml)}}))
        self.out = os.path.join(self.tmp, "trees")

    def run_build(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = build_l.main(["--l-slice-manifest", self.l_manifest, "--s-slice-manifest", self.s_manifest, "--s-xml", self.s_xml,
                               "--output-root", self.out, "--evidence", self.evidence])
        return rc, buffer.getvalue()

    def test_one_command_builds_the_tree_checks_nesting_and_the_evidence_record(self):
        manifests_before = sorted(os.listdir(os.path.join(EXPERIMENTS, "manifests")))
        rc, out = self.run_build()
        self.assertEqual(rc, 0, out)
        self.assertIn("L-NESTING PASS (300 S keys, all in the 10600 size-l keys)", out)
        info = read_json(os.path.join(self.out, "size-l.subset.json"))
        self.assertEqual((info["tree_label"], info["counts"]["publications"], info["byte_identical_to_source"]), ("size-l", 10600, True))
        base = os.path.join(self.out, "size-l", "datasets", "samples")
        for name in ("dblp/linked-records.xml", "openalex/works.jsonl", "crossref/works.jsonl", "orcid/records.jsonl"):
            self.assertTrue(os.path.isfile(os.path.join(base, name)), name)
        self.assertIn("L-EVIDENCE", out)
        self.assertEqual(sorted(os.listdir(os.path.join(EXPERIMENTS, "manifests"))), manifests_before)  # no EMR manifest is written for L
        rc, out = self.run_build()  # an existing tree is never overwritten
        self.assertEqual(rc, 1)
        self.assertIn("already exists", out)

    def test_a_missing_or_unproven_l_slice_is_refused(self):
        os.remove(self.l_manifest)
        rc, out = self.run_build()
        self.assertEqual(rc, 1)
        self.assertIn("is not delivered yet", out)
        self.l_doc["nestingCheck"]["sManifest"]["sha256"] = HEX_A
        write_text(self.l_manifest, json.dumps(self.l_doc))
        rc, out = self.run_build()
        self.assertEqual(rc, 1)
        self.assertIn("is not the committed S manifest", out)
        self.assertFalse(os.path.exists(self.out))

    def test_a_stale_evidence_record_is_refused(self):
        write_text(self.evidence, json.dumps({"slice": {"publicationCount": 10599, "sha256": self.l_doc["output"]["sha256"]}}))
        rc, out = self.run_build()
        self.assertEqual(rc, 1)
        self.assertIn("update the evidence record", out)

    def test_an_l_slice_that_does_not_match_its_manifest_is_refused(self):
        with open(self.l_xml, "a", encoding="utf-8") as handle:
            handle.write(" ")
        rc, out = self.run_build()
        self.assertEqual(rc, 1)
        self.assertIn("does not match the slice manifest sha256", out)

    def test_tree_label_needs_exactly_one_size(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = subsets.main(["--source", self.l_xml, "--slice-manifest", self.l_manifest, "--output-root", self.out, "--sizes", "50,100", "--tree-label", "size-l"])
        self.assertEqual(rc, 1)
        self.assertIn("--tree-label needs exactly one size", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()

"""Independent tests for scripts/run-experiment.sh (Subphase 13B, test-engineer).

Step 0 answer 6 and README "Experiment runner": only a manifest that is tracked and unchanged at HEAD runs; a manifest
without a budget or teardown section is rejected (exit 3, step=manifest-committed or step=manifest-schema); the dry run
prints the record fields (commit SHA, limits, region, metric locations) and delegates to run-bounded-pipeline.sh; the
approval record for --execute uses APPROVED_ACTION=run-experiment plus APPROVED_MANIFEST_SHA256, and a pipeline record
cannot authorise an experiment (and vice versa). Fixture manifests only; nothing is run against a real account.
"""
import copy
import json
import re
import unittest

import sc_support as S

MANIFEST_PATH = "experiments/exp-a.json"


def manifest(fx):
    return {
        "schema": "scholarchain.experiment-manifest.v1",
        "id": "exp-a-smoke",
        "description": "fixture experiment for the independent 13B tests",
        "budget": {"max_usd": 3, "max_runtime_minutes": 60, "max_capacity": 2, "region": "us-east-2"},
        "teardown": {"mode": "auto-termination", "max_idle_timeout_seconds": 900},
        "pipeline": {
            "instance_type": "m5.xlarge", "core_count": 1, "max_task_count": 0,
            "input_prefix": "s3://inbucket/data/in", "output_prefix": "s3://outbucket/data/out",
            "hadoop_submit_jar": "s3://abucket/hadoop-submit.jar", "hadoop_libjars": "s3://abucket/hadoop-libs.jar",
            "hadoop_config": "inputs/prep.json", "er_jar": "s3://abucket/er.jar", "er_policy": "s3://abucket/policy.json",
            "er_config": "s3://abucket/er-config.json", "spark_config_template": "s3://abucket/spark-template.json",
            "datasets_manifest": "inputs/datasets.json",
            "artifact_sha256": {name: S.HEX64 for name in S.ARTIFACT_NAMES},
        },
        "metrics": {"locations": ["s3://metricsbucket/exp-a/emr-metrics/", "s3://metricsbucket/exp-a/events/"]},
    }


class Base(unittest.TestCase):
    def committed(self, mutate=None, infra=False):
        fx = S.Fixture(self, infra=infra)
        doc = manifest(fx)
        if mutate:
            mutate(doc)
        S.Fixture.write_json(fx.repo / MANIFEST_PATH, doc)
        fx.commit_all("add experiment manifest")
        return fx

    def dry(self, fx, extra=(), env=None, manifest_path=None, **kw):
        args = ["--manifest", str(manifest_path or (fx.repo / MANIFEST_PATH)), "--cluster-id", "j-TESTCLUSTER"] + list(extra)
        return fx.run("run-experiment.sh", args, env, **kw)

    def assert_refused(self, run, step, no_pipeline=True):
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(run.status, "REFUSED", run.describe())
        self.assertEqual(len(run.results()), 1)
        self.assertIn("step=%s" % step, run.result, run.describe())
        self.assertEqual(run.calls, [], "no fake binary may run for a refused manifest")
        if no_pipeline:
            self.assertFalse(run.grep(r"^pipeline\| "), "the pipeline must not run for a refused manifest")
            self.assertNotIn("EXPERIMENT-RECORD:", run.out if step == "manifest-committed" else "")


class ExperimentDryRun(Base):
    def test_committed_valid_manifest_dry_run_prints_the_record_and_the_pipeline_dry_run(self):
        fx = self.committed()
        r = self.dry(fx, secrets=True)
        self.assertEqual((r.rc, r.status), (0, "DRY-RUN"), r.describe())
        self.assertEqual(len(r.results()), 1)
        self.assertTrue(r.lines()[-1].startswith("RESULT: DRY-RUN"))
        steps = r.steps()
        for expected in ("manifest-committed", "manifest-schema", "run-record", "delegate-pipeline"):
            self.assertIn(expected, steps)
        self.assertLess(steps.index("manifest-committed"), steps.index("manifest-schema"))
        self.assertLess(steps.index("manifest-schema"), steps.index("delegate-pipeline"))
        record = r.grep(r"^EXPERIMENT-RECORD: ")[0]
        self.assertIn("commit=" + fx.head(), record)
        self.assertIn("region=us-east-2", record)
        self.assertIn("manifest_sha256=" + S.sha256_file(fx.repo / MANIFEST_PATH), record)
        self.assertRegex(record, r"start_utc=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
        limits = r.grep(r"^EXPERIMENT-LIMITS: ")[0]
        for expected in ("max_usd=3", "max_runtime_minutes=60", "max_capacity=2", "region=us-east-2", "idle_timeout_seconds<=900"):
            self.assertIn(expected, limits)
        locs = [l.split(": ", 1)[1] for l in r.grep(r"^EXPERIMENT-METRIC-LOCATION: ")]
        self.assertEqual(locs, ["s3://metricsbucket/exp-a/emr-metrics/", "s3://metricsbucket/exp-a/events/"])

    def test_dry_run_delegates_to_the_pipeline_dry_run_and_calls_no_binary(self):
        fx = self.committed()
        r = self.dry(fx)
        pipe = [l for l in r.lines() if l.startswith("pipeline| ")]
        self.assertTrue(pipe, "no pipeline output")
        self.assertTrue(any("RESULT: DRY-RUN" in l for l in pipe))
        self.assertEqual(sum(1 for l in pipe if "DRY-RUN CMD" in l and "aws emr add-steps" in l), 6)
        self.assertTrue(any(l.startswith("pipeline| RUN-CONFIG-SHA256: ") for l in pipe))
        self.assertEqual(r.calls, [], "the dry run called a fake binary")
        printed = [l for l in pipe if "DRY-RUN CMD" in l or "STEP-BODY" in l or l.startswith("pipeline| CMD:")]
        self.assertNotRegex("\n".join(printed), r"create-cluster|run-job-flow")

    def test_dry_run_prints_both_experiment_and_pipeline_approval_lines(self):
        fx = self.committed()
        r = self.dry(fx)
        sha = S.sha256_file(fx.repo / MANIFEST_PATH)
        self.assertIn("EXPERIMENT-APPROVAL-LINE: APPROVED_ACTION=run-experiment", r.out)
        self.assertIn("EXPERIMENT-APPROVAL-LINE: APPROVED_MANIFEST_SHA256=" + sha, r.out)
        self.assertIn("pipeline| APPROVAL-LINE: APPROVED_ACTION=run-experiment", r.out)
        self.assertIn("pipeline| APPROVAL-LINE: APPROVED_MANIFEST_SHA256=" + sha, r.out)
        self.assertIn("pipeline| APPROVAL-LINE: APPROVED_MAX_CAPACITY=2", r.out)

    def test_dry_run_writes_nothing_and_leaks_no_canary(self):
        fx = self.committed()
        r = self.dry(fx, secrets=True)
        self.assertFalse((fx.repo / "target").exists(), "a dry run must write nothing")
        self.assertEqual(fx.git("status", "--porcelain"), "")
        for canary in S.CANARIES:
            self.assertNotIn(canary, r.text)

    def test_manifest_limits_become_pipeline_limits(self):
        def tweak(d):
            d["budget"].update(max_usd=2.5, max_runtime_minutes=90, max_capacity=3)
            d["pipeline"]["core_count"] = 2
        fx = self.committed(tweak)
        r = self.dry(fx)
        self.assertEqual(r.rc, 0, r.describe())
        self.assertIn("pipeline| PLAN: max-runtime-minutes: 90", r.out)
        self.assertIn("pipeline| PLAN: budget-usd: 2.5", r.out)
        self.assertIn("pipeline| APPROVAL-LINE: APPROVED_MAX_CAPACITY=3", r.out)


class ExperimentManifestRefusals(Base):
    def test_untracked_manifest_is_rejected(self):
        fx = S.Fixture(self)
        S.Fixture.write_json(fx.repo / MANIFEST_PATH, manifest(fx))
        self.assert_refused(self.dry(fx), "manifest-committed")

    def test_git_ignored_manifest_is_rejected(self):
        fx = S.Fixture(self)
        S.Fixture.write_json(fx.repo / "target/exp-a.json", manifest(fx))
        self.assert_refused(self.dry(fx, manifest_path=fx.repo / "target/exp-a.json"), "manifest-committed")

    def test_added_but_never_committed_manifest_is_rejected(self):
        fx = S.Fixture(self)
        S.Fixture.write_json(fx.repo / MANIFEST_PATH, manifest(fx))
        fx.git("add", MANIFEST_PATH)
        self.assert_refused(self.dry(fx), "manifest-committed")

    def test_modified_or_staged_but_different_manifest_is_rejected(self):
        fx = self.committed()
        doc = manifest(fx)
        doc["description"] = "edited after the commit"
        S.Fixture.write_json(fx.repo / MANIFEST_PATH, doc)
        self.assert_refused(self.dry(fx), "manifest-committed")
        fx.git("add", MANIFEST_PATH)  # staged but not committed is still different from HEAD
        self.assert_refused(self.dry(fx), "manifest-committed")

    def test_manifest_edited_and_restored_to_head_bytes_is_accepted(self):
        fx = self.committed()
        path = fx.repo / MANIFEST_PATH
        original = path.read_bytes()
        path.write_text("changed")
        path.write_bytes(original)
        r = self.dry(fx)
        self.assertEqual(r.rc, 0, r.describe())

    def test_manifest_outside_the_repository_or_missing_is_rejected(self):
        fx = self.committed()
        outside = S.Fixture.write_json(fx.aux / "outside.json", manifest(fx))
        self.assert_refused(self.dry(fx, manifest_path=outside), "manifest-committed")
        self.assert_refused(self.dry(fx, manifest_path=fx.repo / "experiments/nope.json"), "manifest-committed")

    def schema_refusal(self, mutate, label):
        fx = self.committed(mutate)
        r = self.dry(fx)
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), "%s\n%s" % (label, r.describe()))
        self.assertIn("step=manifest-schema", r.result, "%s\n%s" % (label, r.describe()))
        self.assertEqual(r.calls, [])
        self.assertFalse(r.grep(r"^pipeline\| "), "%s: the pipeline ran for an invalid manifest" % label)

    def test_missing_budget_or_teardown_section_is_rejected(self):
        for label, mutate in (
            ("no budget", lambda d: d.pop("budget")),
            ("no teardown", lambda d: d.pop("teardown")),
            ("empty budget", lambda d: d.__setitem__("budget", {})),
            ("empty teardown", lambda d: d.__setitem__("teardown", {})),
            ("null budget", lambda d: d.__setitem__("budget", None)),
            ("budget without max_usd", lambda d: d["budget"].pop("max_usd")),
            ("budget without max_runtime_minutes", lambda d: d["budget"].pop("max_runtime_minutes")),
            ("budget without max_capacity", lambda d: d["budget"].pop("max_capacity")),
            ("budget without region", lambda d: d["budget"].pop("region")),
            ("teardown without mode", lambda d: d["teardown"].pop("mode")),
            ("teardown without idle timeout", lambda d: d["teardown"].pop("max_idle_timeout_seconds")),
        ):
            with self.subTest(case=label):
                self.schema_refusal(mutate, label)

    def test_unknown_keys_at_every_level_are_rejected(self):
        for label, mutate in (
            ("top level", lambda d: d.__setitem__("surprise", 1)),
            ("budget", lambda d: d["budget"].__setitem__("max_gpus", 1)),
            ("teardown", lambda d: d["teardown"].__setitem__("grace", 5)),
            ("pipeline", lambda d: d["pipeline"].__setitem__("extra_flag", "x")),
            ("metrics", lambda d: d["metrics"].__setitem__("bucket", "s3://x/y")),
        ):
            with self.subTest(level=label):
                self.schema_refusal(mutate, label)

    def test_out_of_range_values_are_rejected(self):
        for label, mutate in (
            ("max_usd above the USD 3 cap", lambda d: d["budget"].__setitem__("max_usd", 3.01)),
            ("max_usd zero", lambda d: d["budget"].__setitem__("max_usd", 0)),
            ("runtime above 180", lambda d: d["budget"].__setitem__("max_runtime_minutes", 181)),
            ("runtime below 10", lambda d: d["budget"].__setitem__("max_runtime_minutes", 9)),
            ("capacity above 4", lambda d: (d["budget"].__setitem__("max_capacity", 5), d["pipeline"].__setitem__("core_count", 4))),
            ("capacity not 1+core+task", lambda d: d["budget"].__setitem__("max_capacity", 3)),
            ("teardown mode manual", lambda d: d["teardown"].__setitem__("mode", "manual")),
            ("idle timeout above cap", lambda d: d["teardown"].__setitem__("max_idle_timeout_seconds", 3601)),
            ("idle timeout below 60", lambda d: d["teardown"].__setitem__("max_idle_timeout_seconds", 59)),
            ("wrong schema", lambda d: d.__setitem__("schema", "scholarchain.experiment-manifest.v2")),
            ("bad id", lambda d: d.__setitem__("id", "Bad Id!")),
            ("empty metric locations", lambda d: d["metrics"].__setitem__("locations", [])),
            ("non-s3 metric location", lambda d: d["metrics"].__setitem__("locations", ["/tmp/metrics"])),
            ("missing metrics", lambda d: d.pop("metrics")),
            ("missing pipeline", lambda d: d.pop("pipeline")),
            ("string max_usd", lambda d: d["budget"].__setitem__("max_usd", "3")),
        ):
            with self.subTest(case=label):
                self.schema_refusal(mutate, label)

    def test_invalid_json_manifest_is_rejected(self):
        fx = S.Fixture(self)
        (fx.repo / MANIFEST_PATH).parent.mkdir(parents=True)
        (fx.repo / MANIFEST_PATH).write_text("{ nope")
        fx.commit_all()
        r = self.dry(fx)
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertIn("step=manifest-schema", r.result)

    def test_usage_errors_exit_two(self):
        fx = self.committed()
        self.assertEqual(fx.run("run-experiment.sh", ["--cluster-id", "j-TESTCLUSTER"]).rc, 2)
        self.assertEqual(fx.run("run-experiment.sh", ["--manifest", str(fx.repo / MANIFEST_PATH)], {"SCHOLARCHAIN_EMR_CLUSTER_ID": ""}).rc, 2)
        self.assertEqual(fx.run("run-experiment.sh", ["--bogus"]).rc, 2)


class ExperimentExecute(Base):
    def prepare(self, fx, manifest_sha=None, **kw):
        """Approval + receipt for an experiment run; derives the run configuration hash from the delegated dry run."""
        pre = fx.write_prespend()
        env = fx.exec_env()
        dry = self.dry(fx, env=env)
        self.assertEqual(dry.rc, 0, dry.describe())
        run_cfg = None
        for line in dry.lines():
            if line.startswith("pipeline| RUN-CONFIG-SHA256: "):
                run_cfg = line.split(": ", 1)[1].strip()
        self.assertTrue(run_cfg, dry.describe())
        sha = manifest_sha or S.sha256_file(fx.repo / MANIFEST_PATH)
        values = [
            ("APPROVED_ACTION", "run-experiment"), ("APPROVED_COMMIT", fx.head()), ("APPROVED_ACCOUNT_SHA256", fx.account_hash()),
            ("APPROVED_REGION", "us-east-2"), ("APPROVED_CLUSTER_ID", "j-TESTCLUSTER"), ("APPROVED_RUN_CONFIG_SHA256", run_cfg),
            ("APPROVED_BUDGET_USD", "3"), ("APPROVED_MAX_CAPACITY", "2"), ("APPROVED_MAX_RUNTIME_MINUTES", "60"),
            ("APPROVED_TEARDOWN", "auto-termination"), ("APPROVED_PRESPEND_SHA256", S.sha256_file(pre)),
            ("APPROVED_MANIFEST_SHA256", sha),
        ]
        approval = fx.write_approval(values, **kw)
        return approval, pre, env

    def execute(self, fx, approval, pre, env, **kw):
        fx.log.write_text("")
        return self.dry(fx, extra=["--approval", str(approval), "--prespend", str(pre), "--execute"], env=env, **kw)

    def test_green_execute_records_commit_limits_region_and_metric_locations(self):
        fx = self.committed()
        approval, pre, env = self.prepare(fx)
        r = self.execute(fx, approval, pre, env, secrets=True)
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        self.assertEqual(len(r.results()), 1)
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 6)
        dirs = list((fx.repo / "target/experiment-runs").iterdir())
        self.assertEqual(len(dirs), 1)
        self.assertTrue(dirs[0].name.startswith("exp-a-smoke-"))
        record_text = (dirs[0] / "experiment-record.json").read_text()
        record = json.loads(record_text)
        for expected in (fx.head(), "us-east-2", S.sha256_file(fx.repo / MANIFEST_PATH), "s3://metricsbucket/exp-a/emr-metrics/",
                         "s3://metricsbucket/exp-a/events/", "auto-termination", "exp-a-smoke"):
            self.assertIn(expected, record_text, "experiment record lacks %r" % expected)
        self.assertRegex(record_text, r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
        self.assertTrue(record)
        result_text = (dirs[0] / "experiment-result.json").read_text()
        self.assertRegex(result_text, r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
        self.assertIn("0", result_text)
        for canary in S.CANARIES:
            self.assertNotIn(canary, r.text)
            for name, text in fx.tree_text(fx.repo / "target").items():
                self.assertNotIn(canary, text, name)
        self.assertEqual(fx.git("status", "--porcelain"), "")

    def test_execute_without_an_approval_naming_the_manifest_is_refused_and_writes_no_record(self):
        fx = self.committed()
        approval, pre, env = self.prepare(fx, manifest_sha="e" * 64)
        r = self.execute(fx, approval, pre, env)
        self.assertEqual(r.rc, 3, r.describe())
        self.assertEqual(r.aws_verbs(), [])
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 0)

    def test_a_pipeline_record_cannot_authorise_an_experiment(self):
        fx = self.committed()
        approval, pre, env = self.prepare(fx, override={"APPROVED_ACTION": "run-bounded-pipeline"})
        r = self.execute(fx, approval, pre, env)
        self.assertEqual(r.rc, 3, r.describe())
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 0)
        # and a record without the manifest line at all
        approval2, pre2, env2 = self.prepare(fx, drop=("APPROVED_MANIFEST_SHA256",), name="approval2.md")
        r = self.execute(fx, approval2, pre2, env2)
        self.assertEqual(r.rc, 3, r.describe())
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 0)

    def test_an_experiment_record_cannot_authorise_a_pipeline_run(self):
        fx = self.committed()
        approval, pre, env = self.prepare(fx)
        # the same record handed to run-bounded-pipeline.sh directly (without the delegation flag)
        pargs = fx.full_args(run_id="bp-direct-1", output_prefix="s3://outbucket/data/out", budget_usd=3) + [
            "--approval", str(approval), "--prespend", str(pre), "--execute"]
        fx.log.write_text("")
        r = fx.run("run-bounded-pipeline.sh", pargs, env)
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertEqual(r.calls, [])

    def test_every_pipeline_gate_still_applies_to_an_experiment(self):
        fx = self.committed()
        approval, pre, env = self.prepare(fx)
        # pricing not confirmed
        r = self.execute(fx, approval, pre, dict(env, SCHOLARCHAIN_PRICING_FILE=str(fx.pricing_file(confirmed=False))))
        self.assertEqual(r.rc, 3, r.describe())
        self.assertEqual(r.calls, [])
        # wrong cluster id on the command line versus the record
        fx.log.write_text("")
        r = fx.run("run-experiment.sh", ["--manifest", str(fx.repo / MANIFEST_PATH), "--cluster-id", "j-OTHERONE", "--approval", str(approval),
                                         "--prespend", str(pre), "--execute"], env)
        self.assertEqual(r.rc, 3, r.describe())
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 0)

    def test_manifest_changed_after_approval_is_refused_before_anything_runs(self):
        fx = self.committed()
        approval, pre, env = self.prepare(fx)
        doc = manifest(fx)
        doc["description"] = "changed after approval"
        S.Fixture.write_json(fx.repo / MANIFEST_PATH, doc)
        r = self.execute(fx, approval, pre, env)
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertIn("step=manifest-committed", r.result)
        self.assertEqual(r.calls, [])
        self.assertFalse((fx.repo / "target").exists())


if __name__ == "__main__":
    unittest.main()

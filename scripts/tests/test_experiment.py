"""run-experiment.sh (Subphase 13B): only a committed, unchanged manifest with valid budget and teardown sections runs; the
pipeline part is delegated to run-bounded-pipeline.sh (same approval, pre-spend and G6 gates). Fixture manifests live in
scripts/tests/fixtures/experiment; the tests copy them into a temp git repository."""
import json
import os
import re
import shutil
import subprocess
import unittest

from helpers import FAKE_ACCOUNT, REGION, SCRIPTS_DIR, account_hash, sha256_bytes
from pipeline_helpers import CLUSTER, FIXTURES, PIPELINE_FIXTURES, PipelineFixture, read

EXPERIMENT = os.path.join(SCRIPTS_DIR, "run-experiment.sh")
MANIFEST_REL = "experiments/fixture/manifest.json"
STEPS = ("stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job", "copy-out")


class ExperimentFixture(PipelineFixture):
    def build_repo(self):
        super().build_repo()
        self.write("fixture-inputs/prep-config.json", read(os.path.join(PIPELINE_FIXTURES, "prep-config.json")))
        self.write("fixture-inputs/datasets.json", read(os.path.join(PIPELINE_FIXTURES, "datasets.json")))
        self.write(MANIFEST_REL, read(os.path.join(FIXTURES, "experiment", "valid-manifest.json")))
        self.commit("fixture experiment manifest")

    def manifest_path(self):
        return os.path.join(self.repo, MANIFEST_REL)

    def manifest(self):
        with open(self.manifest_path(), encoding="utf-8") as handle:
            return json.load(handle)

    def commit_manifest(self, document=None, text=None, rel=MANIFEST_REL):
        content = text if text is not None else json.dumps(document, indent=2, sort_keys=True) + "\n"
        self.write(rel, content)
        self.commit("manifest change")
        return os.path.join(self.repo, rel)

    def experiment(self, *extra, manifest=None, cluster=CLUSTER, **env):
        args = ["--manifest", manifest or self.manifest_path(), "--cluster-id", cluster] + list(extra)
        return self.run_script("run-experiment.sh", *args, **env)

    def manifest_sha(self):
        with open(self.manifest_path(), "rb") as handle:
            return sha256_bytes(handle.read())


class CommittedManifestTests(ExperimentFixture):
    def refused(self, result, *needles, step="manifest-committed"):
        self.assertEqual(result.rc, 3, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: REFUSED"), result.result_line())
        self.assertIn("step=%s" % step, result.result_line())
        for needle in needles:
            self.assertIn(needle, result.out)
        self.assertEqual(self.calls(), [], "a refusal makes no cloud call")
        self.assertNotIn("pipeline|", result.stdout, "the pipeline is not even started")

    def test_a_committed_unchanged_manifest_dry_runs_and_delegates_the_pipeline(self):
        result = self.experiment()
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: DRY-RUN"), result.result_line())
        self.assertIn("EXPERIMENT-RECORD: experiment=fixture-exp-a commit=%s manifest=%s manifest_sha256=%s region=%s" % (self.head(), MANIFEST_REL, self.manifest_sha(), REGION), result.stdout.replace("  ", " "))
        self.assertIn("EXPERIMENT-LIMITS: max_usd=2.5 max_runtime_minutes=90 max_capacity=3 region=us-east-2 idle_timeout_seconds<=900", result.stdout)
        self.assertIn("EXPERIMENT-METRIC-LOCATION: s3://fixture-bucket/metrics/fixture-exp-a/", result.stdout)
        self.assertIn("EXPERIMENT-APPROVAL-LINE: APPROVED_MANIFEST_SHA256=%s" % self.manifest_sha(), result.stdout)
        self.assertEqual([l for l in result.stdout.splitlines() if l.startswith("pipeline| STEP: step-")], ["pipeline| STEP: step-" + n for n in STEPS])
        self.assertIn("pipeline| RESULT: DRY-RUN", result.stdout)
        self.assertEqual(len([l for l in result.stdout.splitlines() if "pipeline| DRY-RUN CMD:" in l and "emr add-steps" in l]), 6)
        self.assertIn("pipeline| ESTIMATE-USD: 1.26", result.stdout)
        self.assertIn("pipeline| APPROVAL-LINE: APPROVED_ACTION=run-experiment", result.stdout)
        self.assertEqual(self.calls(), [])
        self.assertTrue(self.tree_clean())
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "experiment-runs")), "a dry run writes no record")
        self.assertEqual(result.stdout.count("\nRESULT: ") + (1 if result.stdout.startswith("RESULT: ") else 0), 1, "exactly one final RESULT line (the pipeline's is prefixed)")

    def test_an_untracked_manifest_is_refused(self):
        path = os.path.join(self.repo, "experiments", "fixture", "untracked.json")
        self.write("experiments/fixture/untracked.json", read(self.manifest_path()))
        self.refused(self.experiment(manifest=path), "is not tracked by git")

    def test_a_git_ignored_manifest_is_refused(self):
        path = self.write("target/exp/manifest.json", read(self.manifest_path()))
        self.refused(self.experiment(manifest=path), "is not tracked by git")

    def test_a_modified_manifest_is_refused(self):
        document = self.manifest()
        document["budget"]["max_usd"] = 2.0
        with open(self.manifest_path(), "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self.refused(self.experiment(), "differs from HEAD")

    def test_a_staged_but_uncommitted_change_is_refused(self):
        with open(self.manifest_path(), "a", encoding="utf-8") as handle:
            handle.write("\n")
        subprocess.run(["git", "-C", self.repo, "add", MANIFEST_REL], check=True)
        self.refused(self.experiment(), "differs from HEAD")

    def test_a_manifest_outside_the_repository_is_refused(self):
        outside = os.path.join(self.tmp, "outside.json")
        shutil.copy(self.manifest_path(), outside)
        self.refused(self.experiment(manifest=outside), "outside the repository")

    def test_a_missing_manifest_and_missing_flags(self):
        self.refused(self.experiment(manifest=os.path.join(self.repo, "absent.json")), "manifest not found")
        self.assertEqual(self.run_script("run-experiment.sh", "--cluster-id", CLUSTER).rc, 2)
        self.assertEqual(self.run_script("run-experiment.sh", "--manifest", self.manifest_path(), SCHOLARCHAIN_EMR_CLUSTER_ID=None).rc, 2)
        self.assertEqual(self.run_script("run-experiment.sh", "--bogus").rc, 2)


class ManifestSchemaTests(ExperimentFixture):
    def refused(self, result, needle):
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("step=manifest-schema", result.result_line())
        self.assertIn(needle, result.out)
        self.assertNotIn("pipeline|", result.stdout)
        self.assertEqual(self.calls(), [])

    def test_the_committed_fixture_without_a_budget_section_is_rejected(self):
        path = self.commit_manifest(text=read(os.path.join(FIXTURES, "experiment", "missing-budget.json")))
        self.refused(self.experiment(manifest=path), "the budget section is required")

    def test_the_committed_fixture_without_a_teardown_section_is_rejected(self):
        path = self.commit_manifest(text=read(os.path.join(FIXTURES, "experiment", "missing-teardown.json")))
        self.refused(self.experiment(manifest=path), "the teardown section is required")

    def test_invalid_json_is_rejected(self):
        path = self.commit_manifest(text=read(os.path.join(FIXTURES, "experiment", "invalid-json.json")))
        self.refused(self.experiment(manifest=path), "not valid JSON")

    def test_every_invalid_budget_or_teardown_member_is_rejected(self):
        def mutate(fn):
            with open(os.path.join(FIXTURES, "experiment", "valid-manifest.json"), encoding="utf-8") as handle:
                document = json.load(handle)  # always start from the pristine fixture, never from a previous case
            fn(document)
            return document

        cases = {
            "empty budget": (lambda d: d.update(budget={}), "budget.max_usd is required"),
            "budget missing region": (lambda d: d["budget"].pop("region"), "budget.region is required"),
            "budget missing max_usd": (lambda d: d["budget"].pop("max_usd"), "budget.max_usd is required"),
            "budget missing runtime": (lambda d: d["budget"].pop("max_runtime_minutes"), "budget.max_runtime_minutes is required"),
            "budget missing capacity": (lambda d: d["budget"].pop("max_capacity"), "budget.max_capacity is required"),
            "max_usd over the cap": (lambda d: d["budget"].update(max_usd=3.5), "exceeds the per-run cap"),
            "max_usd zero": (lambda d: d["budget"].update(max_usd=0), "number greater than 0"),
            "max_usd a string": (lambda d: d["budget"].update(max_usd="2.5"), "number greater than 0"),
            "runtime over the cap": (lambda d: d["budget"].update(max_runtime_minutes=181), "from 10 to 180"),
            "runtime below 10": (lambda d: d["budget"].update(max_runtime_minutes=5), "from 10 to 180"),
            "capacity over the cap": (lambda d: d["budget"].update(max_capacity=5), "from 1 to 4"),
            "capacity not matching the nodes": (lambda d: d["budget"].update(max_capacity=2), "must equal 1 + core_count + max_task_count = 3"),
            "invalid region": (lambda d: d["budget"].update(region="mars"), "budget.region must be an AWS region name"),
            "unknown budget key": (lambda d: d["budget"].update(extra=1), "unknown budget key: extra"),
            "empty teardown": (lambda d: d.update(teardown={}), "teardown.mode is required"),
            "teardown without idle timeout": (lambda d: d["teardown"].pop("max_idle_timeout_seconds"), "teardown.max_idle_timeout_seconds is required"),
            "teardown mode none": (lambda d: d["teardown"].update(mode="none"), "teardown.mode must be auto-termination"),
            "idle timeout above the cap": (lambda d: d["teardown"].update(max_idle_timeout_seconds=7200), "from 60 to 900"),
            "idle timeout below 60": (lambda d: d["teardown"].update(max_idle_timeout_seconds=30), "from 60 to 900"),
            "teardown not an object": (lambda d: d.update(teardown="auto-termination"), "the teardown section is required"),
            "budget not an object": (lambda d: d.update(budget=[1]), "the budget section is required"),
            "unknown top-level key": (lambda d: d.update(cluster_id=CLUSTER), "unknown top-level key: cluster_id"),
            "unknown pipeline key": (lambda d: d["pipeline"].update(create_cluster=True), "unknown pipeline key: create_cluster"),
            "pipeline without job-jar sha": (lambda d: d["pipeline"]["artifact_sha256"].pop("job-jar"), "must be an object that includes job-jar"),
            "input prefix not s3": (lambda d: d["pipeline"].update(input_prefix="/tmp/in"), "pipeline.input_prefix must be s3://"),
            "no metrics": (lambda d: d.update(metrics={"locations": []}), "metrics.locations must be a non-empty list"),
            "wrong schema": (lambda d: d.update(schema="other"), "schema must be scholarchain.experiment-manifest.v1"),
            "bad id": (lambda d: d.update(id="Bad Id"), "id must match"),
        }
        for label, (fn, needle) in cases.items():
            with self.subTest(label):
                path = self.commit_manifest(mutate(fn))
                self.refused(self.experiment(manifest=path), needle)

    def test_a_valid_alternative_manifest_is_accepted(self):
        document = self.manifest()
        document["budget"]["max_usd"] = 3
        document["budget"]["max_runtime_minutes"] = 180
        path = self.commit_manifest(document)
        self.assertEqual(self.experiment(manifest=path).rc, 0)

    def test_the_manifest_arguments_become_the_pipeline_flags(self):
        result = self.experiment()
        self.assertEqual(result.rc, 0, result.out)
        out = result.stdout
        for needle in ("pipeline| PLAN: cluster-id: %s" % CLUSTER, "pipeline| PLAN: region: us-east-2", "pipeline| PLAN: budget-usd: 2.5", "pipeline| PLAN: max-runtime-minutes: 90", "max-capacity=3",
                       "pipeline| PLAN: input-prefix: s3://fixture-bucket/inputs", "pipeline| PLAN: output-prefix: s3://fixture-bucket/outputs/fixture-exp-a-"):
            self.assertIn(needle, out)
        self.assertIn("auto-termination idle timeout of at most 900 s", out.replace("\n", " ") + "")
        self.assertIn("pipeline| TEARDOWN: forced auto-termination: the cluster must have an idle timeout of at most 900s", out)


class ExperimentExecuteTests(ExperimentFixture):
    def ready(self, **record_override):
        """Pricing confirmed, receipt, and an approval record built from the experiment's own dry-run output."""
        self.set_pricing(confirmed=True)
        dry = self.experiment()
        self.assertEqual(dry.rc, 0, dry.out)
        run_sha = self.value_of(dry, "pipeline| RUN-CONFIG-SHA256: ")
        prespend_path, prespend_sha = self.write_prespend()
        values = self.approval_lines(run_sha, prespend_sha, APPROVED_ACTION="run-experiment", APPROVED_BUDGET_USD="2.5")
        values["APPROVED_MANIFEST_SHA256"] = self.manifest_sha()
        values.update(record_override)
        record = self.write_record(values)
        return ["--approval", record, "--prespend", prespend_path, "--profile", "approved-profile", "--execute"]

    def refused(self, result, *needles):
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.submitted_steps(), [])
        for needle in needles:
            self.assertIn(needle, result.out)

    def test_execute_runs_the_pipeline_and_writes_the_private_experiment_record(self):
        args = self.ready()
        result = self.experiment(*args)
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PASS"), result.result_line())
        self.assertEqual(len(self.submitted_steps()), 6)
        self.assertEqual(self.emr_ops()[:2], ["describe-cluster", "get-auto-termination-policy"])
        runs = os.path.join(self.repo, "target", "experiment-runs")
        directory = [d for d in os.listdir(runs) if d.startswith("fixture-exp-a-")]
        self.assertEqual(len(directory), 1)
        base = os.path.join(runs, directory[0])
        with open(os.path.join(base, "experiment-record.json"), encoding="utf-8") as handle:
            record = json.load(handle)
        self.assertEqual(oct(os.stat(os.path.join(base, "experiment-record.json")).st_mode & 0o777), "0o600")
        self.assertEqual(record["commit"], self.head())
        self.assertEqual(record["manifest_sha256"], self.manifest_sha())
        self.assertEqual(record["region"], REGION)
        self.assertEqual(record["resource_limits"]["max_usd"], 2.5)
        self.assertEqual(record["resource_limits"]["max_capacity"], 3)
        self.assertEqual(record["resource_limits"]["max_runtime_minutes"], 90)
        self.assertEqual(record["resource_limits"]["teardown"], {"mode": "auto-termination", "max_idle_timeout_seconds": 900})
        self.assertEqual(record["metric_locations"], ["s3://fixture-bucket/metrics/fixture-exp-a/"])
        self.assertRegex(record["start_time_utc"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        with open(os.path.join(base, "experiment-result.json"), encoding="utf-8") as handle:
            outcome = json.load(handle)
        self.assertEqual(outcome["status"], "PASS")
        self.assertEqual(outcome["exit_code"], 0)
        self.assertEqual(outcome["start_time_utc"], record["start_time_utc"])
        self.assertRegex(outcome["end_time_utc"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(record["pipeline_run_id"], outcome["pipeline_run_id"])
        self.assertTrue(os.path.isfile(os.path.join(self.repo, "target", "pipeline-runs", record["pipeline_run_id"], "run-manifest.json")))
        for secret in (FAKE_ACCOUNT,):
            self.assertNotIn(secret, result.out)
        self.assertTrue(self.tree_clean())

    def test_a_manifest_hash_mismatch_in_the_record_refuses(self):
        self.refused(self.experiment(*self.ready(APPROVED_MANIFEST_SHA256="5" * 64)), "APPROVED_MANIFEST_SHA256")

    def test_a_record_for_the_pipeline_action_does_not_authorise_an_experiment(self):
        args = self.ready(APPROVED_ACTION="run-bounded-pipeline")
        self.refused(self.experiment(*args), "APPROVED_ACTION run-bounded-pipeline != the action being run (run-experiment)")

    def test_the_same_gates_as_the_pipeline_apply(self):
        # unconfirmed pricing
        args = self.ready()
        self.set_pricing(confirmed=False)
        # pricing is not part of the manifest, so the record is still valid: only the G6 gate refuses
        self.refused(self.experiment(*args), "pricing is not confirmed by the human")
        # ledger
        self.set_pricing(confirmed=True)
        self.write_ledger(["0.50", "0.50", "0.50", "0.50", "0.50"])  # Phase 18 18B: the live-run limit is 5 (it was 4, Phase 15 P25)
        self.refused(self.experiment(*args), "5 live EMR runs")
        # a stale pre-spend receipt
        self.write_ledger([])  # a fresh, initialised ledger
        args = self.ready()
        self.write_prespend()  # same name: unchanged; now make it stale and re-hash
        stale_path, stale_sha = self.write_prespend(cost_snapshot_utc="2020-01-01T00:00:00Z")
        run_sha = self.value_of(self.experiment(), "pipeline| RUN-CONFIG-SHA256: ")
        values = self.approval_lines(run_sha, stale_sha, APPROVED_ACTION="run-experiment", APPROVED_BUDGET_USD="2.5")
        values["APPROVED_MANIFEST_SHA256"] = self.manifest_sha()
        record = self.write_record(values, name="stale.md")
        self.refused(self.experiment("--approval", record, "--prespend", stale_path, "--profile", "p", "--execute"), "pre-spend receipt rejected before initial")

    def test_a_failed_pipeline_makes_the_experiment_fail_and_is_recorded(self):
        args = self.ready()
        result = self.experiment(*args, FAKE_EMR_STEP_STATE_2="FAILED")
        self.assertEqual(result.rc, 4, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: FAIL"), result.result_line())
        runs = os.path.join(self.repo, "target", "experiment-runs")
        base = os.path.join(runs, os.listdir(runs)[0])
        with open(os.path.join(base, "experiment-result.json"), encoding="utf-8") as handle:
            outcome = json.load(handle)
        self.assertEqual((outcome["status"], outcome["exit_code"]), ("FAIL", 4))

    def test_a_modified_manifest_cannot_be_executed_even_with_a_record(self):
        args = self.ready()
        with open(self.manifest_path(), "a", encoding="utf-8") as handle:
            handle.write("\n")
        self.refused(self.experiment(*args), "differs from HEAD")
        self.assertEqual(self.calls(), [])


RUN = "run-20261115"
OTHER_ACCOUNT = "9" * 12  # another account than FAKE_ACCOUNT, built without a 12-digit literal


def bucket(zone, account=FAKE_ACCOUNT, env="course"):
    return "scholarchain-%s-%s-%s" % (env, account, zone)


class TokenFixture(ExperimentFixture):
    """A committed manifest that holds only tokens (replan G-MAIN, Option B): the bucket names embed the account id, so they are
    resolved from the environment at run time and the account never enters a committed file."""

    TOKEN_ENV = None

    def setUp(self):
        super().setUp()
        self.token_env = {"SCHOLARCHAIN_ARTIFACTS_BUCKET": bucket("artifacts"), "SCHOLARCHAIN_RUN_PREFIX": RUN}
        document = self.manifest()
        pipeline = document["pipeline"]
        base = "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}"
        pipeline["input_prefix"] = base + "/input/size-25"
        pipeline["output_prefix"] = "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/pipeline/${SCHOLARCHAIN_RUN_PREFIX}/15a/size-25"
        pipeline["hadoop_submit_jar"] = base + "/jars/hadoop-submit.jar"
        pipeline["hadoop_libjars"] = base + "/jars/hadoop-bundle.jar"
        pipeline["er_jar"] = base + "/jars/entity-resolution.jar"
        pipeline["er_policy"] = base + "/config/er-policy.json"
        pipeline["er_config"] = base + "/config/er-config.json"
        pipeline["spark_config_template"] = base + "/config/spark-config-template.json"
        document["metrics"]["locations"] = ["s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/pipeline/${SCHOLARCHAIN_RUN_PREFIX}/15a/size-25/metrics/"]
        self.tokenized = document
        self.path = self.commit_manifest(document)

    def experiment(self, *extra, manifest=None, cluster=CLUSTER, **env):
        merged = dict(self.token_env)
        merged.update(env)
        return super().experiment(*extra, manifest=manifest or self.path, cluster=cluster, **merged)

    def resolved_sha(self, values=None):
        """Independent of the script: replace the tokens in every string value, dump the way the renderer documents, hash the bytes."""
        values = values or {"SCHOLARCHAIN_ARTIFACTS_BUCKET": bucket("artifacts"), "SCHOLARCHAIN_RUN_PREFIX": RUN}

        def walk(item):
            if isinstance(item, str):
                for name, value in values.items():
                    item = item.replace("${%s}" % name, value)
                return item
            if isinstance(item, list):
                return [walk(x) for x in item]
            if isinstance(item, dict):
                return {k: walk(v) for k, v in item.items()}
            return item

        return sha256_bytes((json.dumps(walk(self.tokenized), indent=2, sort_keys=True) + "\n").encode())

    def refused_tokens(self, result, needle):
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("step=manifest-tokens", result.result_line())
        self.assertIn(needle, result.out)
        self.assertEqual(self.calls(), [], "a refusal makes no cloud call")
        self.assertNotIn("pipeline|", result.stdout, "the pipeline is not even started")

    def committed_sha(self):
        with open(self.path, "rb") as handle:
            return sha256_bytes(handle.read())


class TokenResolutionTests(TokenFixture):
    def test_the_committed_manifest_holds_no_account_id_and_the_dry_run_resolves_the_tokens(self):
        with open(self.path, encoding="utf-8") as handle:
            self.assertNotIn(FAKE_ACCOUNT, handle.read())
        result = self.experiment()
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("pipeline| PLAN: input-prefix: s3://%s/emr/%s/input/size-25" % ("scholarchain-course-<acct>-artifacts", RUN), result.stdout)
        self.assertIn("pipeline| PLAN: output-prefix: s3://scholarchain-course-<acct>-artifacts/pipeline/%s/15a/size-25" % RUN, result.stdout)
        self.assertIn("EXPERIMENT-METRIC-LOCATION: s3://scholarchain-course-<acct>-artifacts/pipeline/%s/15a/size-25/metrics/" % RUN, result.stdout)
        self.assertIn("EXPERIMENT-TOKEN: SCHOLARCHAIN_ARTIFACTS_BUCKET scholarchain-course-<acct>-artifacts", result.stdout)
        self.assertIn("EXPERIMENT-TOKEN: SCHOLARCHAIN_RUN_PREFIX %s" % RUN, result.stdout)
        self.assertNotIn(FAKE_ACCOUNT, result.out, "no raw account id on screen")
        for line in result.stdout.splitlines():
            if line.startswith("pipeline|"):
                self.assertNotIn("${SCHOLARCHAIN", line, "no unresolved token reaches the pipeline")

    def test_the_committed_and_the_resolved_sha256_are_both_reported_and_the_resolved_one_is_the_documented_dump(self):
        result = self.experiment()
        self.assertIn("EXPERIMENT-MANIFEST-SHA256: committed=%s rendered=%s" % (self.committed_sha(), self.resolved_sha()), result.stdout)
        self.assertNotEqual(self.committed_sha(), self.resolved_sha())
        self.assertIn("EXPERIMENT-APPROVAL-LINE: APPROVED_MANIFEST_SHA256=%s" % self.committed_sha(), result.stdout)
        self.assertIn("EXPERIMENT-APPROVAL-NOTE: Rendered manifest sha256: %s" % self.resolved_sha(), result.stdout)

    def test_a_manifest_without_tokens_is_unchanged_and_unused_token_variables_are_ignored(self):
        document = self.manifest()  # the earlier fixture content is replaced by the tokenised one; rebuild a plain one
        plain = json.loads(read(os.path.join(FIXTURES, "experiment", "valid-manifest.json")))
        path = self.commit_manifest(plain, rel="experiments/fixture/plain.json")
        result = super(TokenFixture, self).experiment(manifest=path, SCHOLARCHAIN_ARTIFACTS_BUCKET="not-a-project-bucket", SCHOLARCHAIN_RUN_PREFIX="bad")
        self.assertEqual(result.rc, 0, result.out)
        with open(path, "rb") as handle:
            sha = sha256_bytes(handle.read())
        self.assertIn("EXPERIMENT-MANIFEST-SHA256: committed=%s rendered=%s" % (sha, sha), result.stdout)
        self.assertNotIn("EXPERIMENT-TOKEN:", result.stdout)
        self.assertEqual(document["id"], plain["id"])

    def test_an_unknown_token_is_refused(self):
        for token in ("${SCHOLARCHAIN_SECRET_BUCKET}", "${HOME}", "${}", "${SCHOLARCHAIN_ARTIFACTS_BUCKET2}"):
            with self.subTest(token):
                document = json.loads(json.dumps(self.tokenized))
                document["pipeline"]["er_jar"] = "s3://" + token + "/x.jar"
                self.path = self.commit_manifest(document)
                self.refused_tokens(self.experiment(), "unknown token")

    def test_a_malformed_unclosed_token_is_refused(self):
        document = json.loads(json.dumps(self.tokenized))
        document["pipeline"]["er_jar"] = "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET/x.jar"
        self.path = self.commit_manifest(document)
        self.refused_tokens(self.experiment(), "malformed token")

    def test_a_token_without_braces_is_refused_not_passed_on_literally(self):
        for field in ("er_jar", "input_prefix"):
            with self.subTest(field):
                document = json.loads(json.dumps(self.tokenized))
                document["pipeline"][field] = "s3://$SCHOLARCHAIN_ARTIFACTS_BUCKET/x"
                self.path = self.commit_manifest(document)
                self.refused_tokens(self.experiment(), "without braces")

    def test_an_empty_or_unset_variable_for_a_token_in_use_is_refused(self):
        for name in ("SCHOLARCHAIN_ARTIFACTS_BUCKET", "SCHOLARCHAIN_RUN_PREFIX"):
            for value in ("", None):
                with self.subTest(name=name, value=value):
                    self.refused_tokens(self.experiment(**{name: value}), "environment variable %s is empty or unset" % name)

    def test_a_bucket_value_of_another_shape_is_refused(self):
        bad = {
            "not a project bucket": "fixture-bucket",
            "no account digits": "scholarchain-course-artifacts",
            "eleven digits": "scholarchain-course-%s-artifacts" % FAKE_ACCOUNT[:11],
            "thirteen digits": "scholarchain-course-%s3-artifacts" % FAKE_ACCOUNT,
            "uppercase environment": "scholarchain-Course-%s-artifacts" % FAKE_ACCOUNT,
            "the wrong zone suffix": bucket("raw"),
            "the logs bucket": bucket("logs"),
            "a trailing slash": bucket("artifacts") + "/",
            "an s3 uri": "s3://" + bucket("artifacts"),
        }
        for label, value in bad.items():
            with self.subTest(label):
                self.refused_tokens(self.experiment(SCHOLARCHAIN_ARTIFACTS_BUCKET=value), "must be a project bucket name scholarchain-<env>-<12 digits>-artifacts")

    def test_a_run_prefix_of_another_shape_is_refused(self):
        for value in ("Run-20261115", "run-a", "run--x", "run-" + "a" * 29, "20261115", "run-../x", "run-20261115/", "run 1"):
            with self.subTest(value):
                self.refused_tokens(self.experiment(SCHOLARCHAIN_RUN_PREFIX=value), "SCHOLARCHAIN_RUN_PREFIX must match")

    def test_the_longest_valid_run_prefix_is_accepted(self):
        self.assertEqual(self.experiment(SCHOLARCHAIN_RUN_PREFIX="run-" + "a" * 28).rc, 0)

    def test_buckets_of_different_accounts_or_environments_are_refused(self):
        document = json.loads(json.dumps(self.tokenized))
        document["metrics"]["locations"] = ["s3://${SCHOLARCHAIN_LOGS_BUCKET}/emr/m/"]
        self.path = self.commit_manifest(document)
        for other in (bucket("logs", account=OTHER_ACCOUNT), bucket("logs", env="other")):
            with self.subTest(other):
                self.refused_tokens(self.experiment(SCHOLARCHAIN_LOGS_BUCKET=other), "different environments or accounts")
        ok = self.experiment(SCHOLARCHAIN_LOGS_BUCKET=bucket("logs"))
        self.assertEqual(ok.rc, 0, ok.out)
        self.assertIn("EXPERIMENT-TOKEN: SCHOLARCHAIN_LOGS_BUCKET scholarchain-course-<acct>-logs", ok.stdout)

    def test_the_raw_and_reports_tokens_resolve_with_their_own_suffixes(self):
        document = json.loads(json.dumps(self.tokenized))
        document["metrics"]["locations"] = ["s3://${SCHOLARCHAIN_REPORTS_BUCKET}/pipeline/m/", "s3://${SCHOLARCHAIN_RAW_BUCKET}/x/"]
        self.path = self.commit_manifest(document)
        env = {"SCHOLARCHAIN_REPORTS_BUCKET": bucket("reports"), "SCHOLARCHAIN_RAW_BUCKET": bucket("raw")}
        self.assertEqual(self.experiment(**env).rc, 0)
        self.refused_tokens(self.experiment(**dict(env, SCHOLARCHAIN_RAW_BUCKET=bucket("reports"))), "-raw")

    def test_a_raw_account_id_in_a_committed_string_is_refused(self):
        for text in ("s3://%s/x.jar" % bucket("artifacts"), "account %s" % FAKE_ACCOUNT):
            with self.subTest(text):
                document = json.loads(json.dumps(self.tokenized))
                document["pipeline"]["er_jar"] = text if text.startswith("s3://") else "s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/x.jar"
                document["description"] = text if not text.startswith("s3://") else document["description"]
                self.path = self.commit_manifest(document)
                self.refused_tokens(self.experiment(), "raw 12-digit account id")

    def test_a_64_hex_sha256_is_not_mistaken_for_an_account_id(self):
        document = json.loads(json.dumps(self.tokenized))
        document["pipeline"]["artifact_sha256"]["er-jar"] = "0" * 12 + "a" * 52
        document["pipeline"]["artifact_sha256"]["job-jar"] = "1" * 64
        self.path = self.commit_manifest(document)
        self.assertEqual(self.experiment().rc, 0)

    def test_tokens_are_replaced_in_values_only_never_in_keys(self):
        document = json.loads(json.dumps(self.tokenized))
        document["pipeline"]["${SCHOLARCHAIN_RUN_PREFIX}"] = "x"
        self.path = self.commit_manifest(document)
        result = self.experiment()
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("unknown pipeline key", result.out)


class TokenExecuteTests(TokenFixture):
    def ready(self, **record_override):
        self.set_pricing(confirmed=True)
        dry = self.experiment()
        self.assertEqual(dry.rc, 0, dry.out)
        run_sha = self.value_of(dry, "pipeline| RUN-CONFIG-SHA256: ")
        prespend_path, prespend_sha = self.write_prespend()
        values = self.approval_lines(run_sha, prespend_sha, APPROVED_ACTION="run-experiment", APPROVED_BUDGET_USD="2.5")
        values["APPROVED_MANIFEST_SHA256"] = self.committed_sha()
        values.update(record_override)
        return ["--approval", self.write_record(values), "--prespend", prespend_path, "--profile", "approved-profile", "--execute"]

    def test_execute_records_both_hashes_and_the_substituted_values_without_the_account_id(self):
        result = self.experiment(*self.ready())
        self.assertEqual(result.rc, 0, result.out)
        self.assertNotIn(FAKE_ACCOUNT, result.out)
        runs = os.path.join(self.repo, "target", "experiment-runs")
        base = os.path.join(runs, [d for d in os.listdir(runs) if d.startswith("fixture-exp-a-")][0])
        with open(os.path.join(base, "experiment-record.json"), encoding="utf-8") as handle:
            text = handle.read()
        record = json.loads(text)
        self.assertNotIn(FAKE_ACCOUNT, text, "the record holds no account id")
        self.assertEqual(record["manifest_sha256"], self.committed_sha())
        self.assertEqual(record["rendered_manifest_sha256"], self.resolved_sha())
        self.assertEqual(record["token_substitutions"], {"SCHOLARCHAIN_ARTIFACTS_BUCKET": "scholarchain-course-<acct>-artifacts", "SCHOLARCHAIN_RUN_PREFIX": RUN})
        self.assertEqual(record["metric_locations"], ["s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/pipeline/${SCHOLARCHAIN_RUN_PREFIX}/15a/size-25/metrics/"])
        with open(os.path.join(base, "experiment-result.json"), encoding="utf-8") as handle:
            outcome_text = handle.read()
        outcome = json.loads(outcome_text)
        self.assertNotIn(FAKE_ACCOUNT, outcome_text)
        self.assertEqual((outcome["rendered_manifest_sha256"], outcome["status"]), (self.resolved_sha(), "PASS"))
        self.assertTrue(self.tree_clean(), "the resolved manifest is a private temp file, never written into the repository")

    def test_the_pipeline_receives_the_resolved_names_so_the_run_configuration_binds_them(self):
        dry = self.experiment()
        resolved = self.value_of(dry, "pipeline| RUN-CONFIG-SHA256: ")
        other = self.experiment(SCHOLARCHAIN_RUN_PREFIX="run-20261116")
        self.assertNotEqual(resolved, self.value_of(other, "pipeline| RUN-CONFIG-SHA256: "), "a different run prefix changes what the human approves")

    def test_the_approval_record_binds_the_committed_file_not_the_resolved_one(self):
        result = self.experiment(*self.ready(APPROVED_MANIFEST_SHA256=self.resolved_sha()))
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("APPROVED_MANIFEST_SHA256", result.out)
        self.assertEqual(self.submitted_steps(), [])


class NoDuplicatedStepLogicTests(unittest.TestCase):
    def test_run_experiment_delegates_and_holds_no_step_or_cluster_logic(self):
        text = read(EXPERIMENT)
        code = re.sub(r"usage\(\) \{.*?\n\}\n", "", text, flags=re.S)
        code = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith("#"))
        for needle in ("add-steps", "spark-submit", "yarn application", "hadoop jar", "aws emr", "describe-cluster", "run_bounded"):
            self.assertNotIn(needle, code, needle)
        self.assertIn("run-bounded-pipeline.sh", code)

    def test_the_help_documents_the_schema_the_gates_and_the_exit_codes(self):
        text = subprocess.run(["bash", EXPERIMENT, "--help"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}).stdout
        for needle in ("TRACKED by git", "UNCHANGED against HEAD", "budget", "teardown", "APPROVED_MANIFEST_SHA256", "run-bounded-pipeline.sh", "Human approval points", "Exit codes", "Evidence produced", "scholarchain.experiment-manifest.v1"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

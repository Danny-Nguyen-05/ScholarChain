"""run-bounded-pipeline.sh (Subphase 13B): dry run, ceilings, G6, approval and pre-spend gates, forced auto-termination,
the YARN kill by tag (carried item 1), the driver and executor class-origin check, Terraform-only behaviour.

Fake aws/yarn/hadoop/spark-submit/timeout binaries only. Every expected value is hand-derived from the requirement, never
read back from the implementation: estimate = instances x (EC2 + EMR rate) x (runtime + idle tail) hours, for example 3 x (0.192 + 0.048) x (1.5 h + 900 s) = 1.26.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

from helpers import FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, REGION, SCRIPTS_DIR, account_hash, sha256_bytes, utc_hours_ago
from pipeline_helpers import CLUSTER, JOB_SHA, PIPELINE_FIXTURES, RUN, PipelineFixture, read

PIPELINE = os.path.join(SCRIPTS_DIR, "run-bounded-pipeline.sh")
STEPS = ("stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job", "copy-out")
# maxLocalSampleRecords is the one pipeline-specific exception (12000, replan G-MAIN); the Phase 4 smoke script keeps 1000.
PIPELINE_LOCAL_SAMPLE_CEILING = 12000
PHASE4_LOCAL_SAMPLE_CEILING = 1000
CEILINGS = {
    "maxLocalSampleRecords": PIPELINE_LOCAL_SAMPLE_CEILING,
    "reducerCount": 8,
    "maxCandidateBlockSize": 256,
    "maxCandidatePairsPerBlock": 4096,
    "maxAuthorTeamSize": 64,
    "maxRecordBytes": 8388608,
    "maxXmlEntityExpansion": 8388608,
}
EXPECTED_SECONDS = {"stage-in": 270, "hadoop-prep": 1080, "entity-resolution": 1080, "spark-class-origin": 270, "spark-job": 2160, "copy-out": 540}
READ_ONLY_EMR = {"describe-cluster", "get-auto-termination-policy", "list-instance-groups", "describe-step"}
FORBIDDEN_INFRA_WORDS = ("create-cluster", "run-job-flow", "modify-instance-groups", "terminate-clusters", "put-managed-scaling-policy", "set-termination-protection")


def last_result(result):
    return result.result_line()


class DryRunTests(PipelineFixture):
    def test_dry_run_prints_every_command_and_runs_nothing(self):
        result = self.dry()
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(last_result(result).startswith("RESULT: DRY-RUN"), last_result(result))
        self.assertEqual(self.calls(), [], "no fake aws, yarn, hadoop or spark call at all")
        printed = [l for l in result.stdout.splitlines() if l.startswith("DRY-RUN CMD:")]
        verbs = []
        for line in printed:
            m = re.search(r"aws (sts get-caller-identity|emr [a-z-]+)", line)
            self.assertIsNotNone(m, line)
            verbs.append(m.group(1))
        self.assertEqual(verbs, ["sts get-caller-identity", "emr describe-cluster", "emr get-auto-termination-policy", "emr list-instance-groups"] + ["emr add-steps"] * 6)
        self.assertTrue(self.tree_clean(), "a dry run writes nothing into the repository")
        with open(self.ledger_path(), encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 1, "a dry run reserves nothing: the ledger still holds only its init record")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "pipeline-runs")))

    def test_step_markers_are_in_order(self):
        steps = self.dry().steps()
        wanted = ["step-" + name for name in STEPS]
        self.assertEqual([s for s in steps if s.startswith("step-")], wanted)
        self.assertLess(steps.index("g6-estimate"), steps.index("plan"))
        self.assertLess(steps.index("plan"), steps.index("step-stage-in"))
        self.assertLess(steps.index("cluster-check"), steps.index("step-stage-in"))

    def test_the_estimate_is_hand_derived_and_printed_before_anything_else_is_planned(self):
        # 1 primary + 1 core + 1 task = 3 x (0.192 + 0.048) x (90 min + 900 s idle tail = 1.75 h) = 1.26
        result = self.dry()
        self.assertIn("ESTIMATE-USD: 1.26", result.stdout)
        self.assertLess(result.stdout.index("ESTIMATE-USD:"), result.stdout.index("RUN-CONFIG-SHA256:"))
        # m5.2xlarge, 1 core, 0 task = 2 x (0.384 + 0.096) x (60 min + 900 s = 1.25 h) = 1.20
        two = self.dry(**{"--instance-type": "m5.2xlarge", "--max-task-count": "0", "--max-runtime-minutes": "60", "--budget-usd": "1.50"})
        self.assertIn("ESTIMATE-USD: 1.20", two.stdout, two.out)
        self.assertEqual(two.rc, 0, two.out)

    def test_the_run_configuration_hash_is_stable_and_changes_with_anything_that_matters(self):
        first = self.run_config_sha()
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        self.assertEqual(first, self.run_config_sha())
        self.assertEqual(first, self.run_config_sha(**{"--run-id": "bp-another-run-id"}), "the run id is not part of the approved configuration")
        for change in ({"--budget-usd": "2.00"}, {"--max-runtime-minutes": "80"}, {"--core-count": "2"}, {"--output-prefix": "s3://fixture-bucket/other"}, {"--cluster-id": "j-ZZZ999"}):
            with self.subTest(change):
                self.assertNotEqual(first, self.run_config_sha(**change))

    def test_the_spark_step_carries_every_decision_12_10_setting(self):
        # Finding C1: the settings are SPARK_CONF=key=value parameters of the printed step; the spark-submit assembly is in the
        # installed runner, so the text asserted here is the printed step plus the installed programs (step_text).
        body = self.step_text("spark-job")
        for needle in (
            "spark-submit",
            "--master yarn --deploy-mode cluster",
            "spark.yarn.jars=local:/opt/scholarchain-runtime/jars/*",
            "spark.yarn.populateHadoopClasspath=false",
            "spark.authenticate=true",
            "spark.network.crypto.enabled=true",
            "spark.network.crypto.authEngineVersion=1",
            "spark.network.crypto.saslFallback=false",
            "spark.io.encryption.enabled=true",
            "spark.dynamicAllocation.enabled=true",
            "spark.dynamicAllocation.shuffleTracking.enabled=true",
            "spark.shuffle.service.enabled=false",
            "spark.yarn.tags=${TAG}",
            "spark.hadoop.fs.defaultFS=file:///",
            "spark.yarn.appMasterEnv.JAVA_HOME=${JAVA_HOME}",
            "spark.executorEnv.JAVA_HOME=${JAVA_HOME}",
            "edu.uic.cs441.scholarchain.spark.Phase6Main",
            'local:${JOB_JAR}',
        ):
            self.assertIn(needle, body)
        codec = re.search(r"spark\.hadoop\.io\.compression\.codecs=(\S+)", body).group(1).rstrip("'\\")
        self.assertEqual(
            sorted(codec.split(",")),
            sorted(["org.apache.hadoop.io.compress.GzipCodec", "org.apache.hadoop.io.compress.DefaultCodec", "org.apache.hadoop.io.compress.BZip2Codec", "org.apache.hadoop.io.compress.SnappyCodec"]),
        )
        self.assertNotIn("lzo", body.lower())
        # tags are the run id; maxExecutors = (1 core + 1 task) x 2 per node = 4
        self.assertIn("MAX_EXECUTORS=4", body)
        self.assertIn('spark.dynamicAllocation.maxExecutors=${MAX_EXECUTORS}', body)
        self.assertIn("TAG=%s" % RUN, body)
        self.assertEqual(len([w for w in self.step_argv("spark-job") if w.startswith("SPARK_CONF=")]), 22, "all 22 decision 12-10 settings travel as parameters")

    def test_java_17_is_resolved_at_run_time_never_hard_coded(self):
        result = self.dry()
        for name in ("entity-resolution", "spark-class-origin", "spark-job"):
            body = self.step_text(name)
            self.assertIn('JAVA_HOME="$(head -n 1 "${JAVA_HOME_FILE}")"', body, name)
            self.assertIn("JAVA_HOME_FILE=/opt/scholarchain-spike/java-home", body, name)
        for needle in ("/usr/lib/jvm", "java-17-amazon-corretto", "corretto", "jre-17"):
            self.assertNotIn(needle, result.stdout)

    def test_the_class_origin_check_precedes_the_spark_job_and_is_fail_closed_in_both_steps(self):
        steps = [s for s in self.dry().steps() if s.startswith("step-")]
        self.assertLess(steps.index("step-spark-class-origin"), steps.index("step-spark-job"))
        probe = self.step_text("spark-class-origin")
        self.assertIn("edu.uic.cs441.scholarchain.spark.Phase12Readiness", probe)
        self.assertRegex(probe, r'probe "\$\{probe_shared\}" "\$\{probe_out\}" distributed')
        self.assertIn("CLASS-ORIGIN-FAILED", probe)
        argv = self.step_argv("spark-class-origin")
        for word in ("EXPECTED_SPARK_VERSION=3.5.4", "EXPECTED_SCALA_VERSION=2.13.14", "RUNTIME_DIR=/opt/scholarchain-runtime", "JOB_JAR_SHA=" + JOB_SHA):
            self.assertIn(word, argv)
        self.assertIn("CLASS_ORIGIN_PY_SHA=" + sha256_bytes(open(os.path.join(SCRIPTS_DIR, "emr", "sc-class-origin-verify.py"), "rb").read()), argv, "the verifier's sha256 is a parameter of both steps")
        job = self.step_text("spark-job")
        self.assertIn("CLASS-ORIGIN-FAILED", job)
        self.assertIn("refusing to start the Spark job", job)
        runner = read(os.path.join(SCRIPTS_DIR, "emr", "sc-step.sh"))
        body = runner[runner.index("body_spark_job() {"):runner.index("body_copy_out() {")]
        self.assertLess(body.index("refusing to start the Spark job"), body.index("verify_class_origin"))
        self.assertLess(body.index("verify_class_origin"), body.index('build_spark_cmd "${SPARK_MAIN}"'))
        self.assertLess(body.index('build_spark_cmd "${SPARK_MAIN}"'), body.index('run_bounded "${STEP_SECONDS}" "${SPARK_CMD[@]}"'))
        for text in (probe, job):
            self.assertIn("scala3-library", text)
            self.assertIn("scala-reflect", text)

    def test_forced_auto_termination_runtime_cap_and_yarn_tag_are_printed(self):
        result = self.dry()
        self.assertIn("TEARDOWN: forced auto-termination", result.stdout)
        self.assertIn("aws emr get-auto-termination-policy", result.stdout)
        self.assertIn("YARN-TAG: %s" % RUN, result.stdout)
        total = 0
        for name in STEPS:
            line = [l for l in result.stdout.splitlines() if l.startswith("STEP-TIMEOUT: %s " % name)]
            self.assertEqual(len(line), 1)
            seconds = int(re.search(r" (\d+)s ", line[0]).group(1))
            self.assertEqual(seconds, EXPECTED_SECONDS[name])
            total += seconds
        self.assertLessEqual(total, 90 * 60)
        for name in ("hadoop-prep", "spark-class-origin", "spark-job"):
            body = self.step_text(name)
            self.assertIn("timeout --kill-after=", body)
            self.assertIn("yarn application -list -appStates NEW,NEW_SAVING,SUBMITTED,ACCEPTED,RUNNING -appTags", body)
            self.assertIn("yarn application -kill", body)

    def test_the_script_only_issues_the_reviewed_aws_verbs_and_never_creates_infrastructure(self):
        dry = self.dry()
        self.assertEqual(self.calls(), [])
        for line in dry.stdout.splitlines():
            if line.startswith("DRY-RUN CMD:"):
                for word in FORBIDDEN_INFRA_WORDS:
                    self.assertNotIn(word, line)
        for name in STEPS:
            body = self.step_text(name)
            for word in FORBIDDEN_INFRA_WORDS + ("terraform",):
                self.assertNotIn(word, body, name)
        self.assertNotIn("terraform", " ".join(a for _n, a in self.calls()))

    def test_no_secret_or_account_id_appears_in_any_output(self):
        env = {"SCHOLARCHAIN_RUN_CANARY_TOKEN": "CANARY-TOKEN-VALUE-98765"}
        result = self.run_pipeline(**env)
        for secret in (FAKE_SECRET, FAKE_TOKEN, "AKIAFAKEFAKEFAKEFAKE", "CANARY-TOKEN-VALUE-98765"):
            self.assertNotIn(secret, result.out)
        self.assertNotIn(FAKE_ACCOUNT, result.out)

    def test_help_documents_approval_record_keys_caps_item_1_and_exit_codes(self):
        text = subprocess.run(["bash", PIPELINE, "--help"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}).stdout
        for needle in (
            "APPROVED_ACTION", "APPROVED_COMMIT", "APPROVED_ACCOUNT_SHA256", "APPROVED_REGION", "APPROVED_CLUSTER_ID", "APPROVED_RUN_CONFIG_SHA256", "APPROVED_BUDGET_USD",
            "APPROVED_MAX_CAPACITY", "APPROVED_MAX_RUNTIME_MINUTES", "APPROVED_TEARDOWN", "APPROVED_PRESPEND_SHA256", "EMR_MAX_RUN_USD", "EMR_MAX_LIVE_RUNS", "EMR_CUMULATIVE_CAP_USD",
            "EMR_PRICING_CONFIRMED_BY_HUMAN", "yarn application -kill", "appTags", "create-cluster", "run-job-flow", "Human approval points", "Exit codes", "Evidence produced",
        ):
            self.assertIn(needle, text)


class RefusalTests(PipelineFixture):
    def refused(self, result, *needles):
        self.assertEqual(result.rc, 3, result.out)
        self.assertTrue(last_result(result).startswith("RESULT: REFUSED"), last_result(result))
        for needle in needles:
            self.assertIn(needle, result.out)
        self.assertEqual(self.calls(), [], "a refusal makes no cloud call")
        self.assertNotIn("emr add-steps", result.stdout)

    def write_prep(self, **changes):
        with open(self.prep_config, encoding="utf-8") as handle:
            document = json.load(handle)
        document.update(changes)
        with open(self.prep_config, "w", encoding="utf-8") as handle:
            json.dump(document, handle)

    def test_each_phase_4_ceiling_refuses_one_above_and_accepts_the_inclusive_limit(self):
        for field, limit in CEILINGS.items():
            with self.subTest(field + "-above"):
                self.write_prep(**{field: limit + 1})
                self.refused(self.dry(), field, "exceeds ceiling %d" % limit)
            with self.subTest(field + "-at-limit"):
                self.write_prep(**{field: limit})
                self.assertEqual(self.dry().rc, 0)

    def test_a_missing_or_non_numeric_ceiling_field_or_invalid_json_refuses(self):
        self.write_prep(maxRecordBytes="8")
        self.refused(self.dry(), "maxRecordBytes must be a JSON number")
        with open(self.prep_config, encoding="utf-8") as handle:
            document = json.load(handle)
        del document["reducerCount"]
        with open(self.prep_config, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self.refused(self.dry(), "missing numeric field: reducerCount")
        with open(self.prep_config, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self.refused(self.dry(), "not valid JSON")

    def test_capacity_runtime_and_input_limits(self):
        self.refused(self.dry(**{"--core-count": "3", "--max-task-count": "2", "--budget-usd": "3"}), "capacity 6", "exceeds the cap 4")
        self.refused(self.dry(**{"--max-runtime-minutes": "181"}), "--max-runtime-minutes must be between 10 and the cap 180")
        self.refused(self.dry(**{"--max-runtime-minutes": "9"}), "between 10 and the cap 180")
        self.refused(self.dry(**{"--input-prefix": "s3://fixture-bucket"}), "--input-prefix must be s3://bucket/non-empty-prefix")
        self.refused(self.dry(**{"--output-prefix": "http://x/y"}), "--output-prefix must be s3://bucket/non-empty-prefix")

    def test_g6_estimate_over_the_per_run_cap_refuses_even_a_dry_run(self):
        # m5.2xlarge, 1 + 3 core = 4 nodes x 0.48 x (180 min + 900 s = 3.25 h) = 6.24 USD > 3
        self.refused(
            self.dry(**{"--instance-type": "m5.2xlarge", "--core-count": "3", "--max-task-count": "0", "--max-runtime-minutes": "180", "--budget-usd": "3"}),
            "G6-REFUSED", "estimate 6.24 USD exceeds the per-run cap 3.00 USD",
        )
        # the pinned worst case, 4 x m5.xlarge for 180 min: 4 x 0.24 x 3.25 h = 3.12 USD > 3 (13B reviewer finding B3)
        self.refused(
            self.dry(**{"--core-count": "2", "--max-task-count": "1", "--max-runtime-minutes": "180", "--budget-usd": "3"}),
            "G6-REFUSED", "estimate 3.12 USD exceeds the per-run cap 3.00 USD",
        )

    def test_g6_budget_above_the_cap_or_below_the_estimate_refuses(self):
        self.refused(self.dry(**{"--budget-usd": "3.50"}), "the declared budget 3.50 USD exceeds the per-run cap 3.00 USD")
        self.refused(self.dry(**{"--budget-usd": "0.50"}), "estimate 1.26 USD exceeds the declared budget 0.50 USD")

    def test_a_lowered_per_run_cap_in_the_test_config_is_honoured(self):
        self.use_config(EMR_MAX_RUN_USD="1")
        self.refused(self.dry(), "estimate 1.26 USD exceeds the per-run cap 1.00 USD")

    def test_usage_errors_exit_2(self):
        for flag in ("--cluster-id", "--region", "--instance-type", "--core-count", "--max-runtime-minutes", "--budget-usd", "--input-prefix", "--hadoop-config", "--datasets-manifest"):
            with self.subTest(flag):
                result = self.run_pipeline(args=self.pipeline_args(drop=(flag,)), SCHOLARCHAIN_EMR_CLUSTER_ID=None, SCHOLARCHAIN_AWS_REGION=None)
                self.assertEqual(result.rc, 2, result.out)
        self.assertEqual(self.run_pipeline("--bogus").rc, 2)
        self.assertEqual(self.dry(**{"--region": "mars"}).rc, 2)
        self.assertEqual(self.dry(**{"--budget-usd": "lots"}).rc, 2)

    def test_run_id_cluster_id_and_job_jar_hash_are_validated(self):
        self.refused(self.dry(**{"--run-id": "x"}), "run id must be 6-64 characters")
        self.refused(self.dry(**{"--cluster-id": "cluster-1"}), "cluster id must look like j-")
        self.refused(self.run_pipeline(args=self.pipeline_args(drop=("--artifact-sha256:job-jar",))), "no sha256 for job-jar")
        self.refused(self.dry(**{"--hadoop-submit-jar": self.prep_config}), "has sha256", "but --artifact-sha256 says")

    def test_the_spark_property_file_must_match_decision_12_10(self):
        conf_path = os.path.join(self.repo, "scripts/config/spark-12-10.conf")
        text = read(conf_path)
        cases = {
            "an lzo codec": text.replace("org.apache.hadoop.io.compress.SnappyCodec", "com.hadoop.compression.lzo.LzoCodec"),
            "no shuffle tracking": text.replace("spark.dynamicAllocation.shuffleTracking.enabled true", "spark.dynamicAllocation.shuffleTracking.enabled false"),
            "auth engine 2": text.replace("authEngineVersion 1", "authEngineVersion 2"),
            "populate classpath": text.replace("populateHadoopClasspath false", "populateHadoopClasspath true"),
            "a run-specific key": text + "spark.yarn.tags something\n",
        }
        for label, content in cases.items():
            with self.subTest(label):
                with open(conf_path, "w", encoding="utf-8") as handle:
                    handle.write(content)
                self.refused(self.dry())
        with open(conf_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.assertEqual(self.dry().rc, 0)

    def test_the_datasets_manifest_must_name_the_four_sources(self):
        with open(self.datasets, "w", encoding="utf-8") as handle:
            json.dump({"dblp": {"snapshot": "a", "retrieval": "b"}}, handle)
        self.refused(self.dry(), "must name exactly dblp, openalex, crossref, orcid")


class ExecuteGateTests(PipelineFixture):
    def refused(self, result, *needles, code=3):
        self.assertEqual(result.rc, code, result.out)
        self.assertEqual(self.submitted_steps(), [], "no step may be submitted")
        self.assertNotIn("add-steps", self.emr_ops())
        for needle in needles:
            self.assertIn(needle, result.out)

    def test_a_complete_execute_run_submits_the_six_steps_reserves_the_ledger_and_writes_private_records(self):
        args = self.ready()
        result = self.execute(args)
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(last_result(result).startswith("RESULT: PASS"), last_result(result))
        ops = self.emr_ops()
        self.assertEqual(ops[:3], ["describe-cluster", "get-auto-termination-policy", "list-instance-groups"])
        self.assertEqual([o for o in ops if o == "add-steps"], ["add-steps"] * 6)
        self.assertEqual(ops[3:], ["add-steps", "describe-step"] * 6)
        self.assertEqual(self.aws_calls()[0].split()[:2], ["sts", "get-caller-identity"], "the account check comes before any other call")
        steps = self.submitted_steps()
        self.assertEqual([s["Name"] for s in steps], ["ScholarChain-%s-%s" % (RUN, n) for n in STEPS])
        dry = self.dry()
        for index, name in enumerate(STEPS):
            args = steps[index]["HadoopJarStep"]["Args"]
            self.assertEqual(args, self.step_argv(name), "the submitted arguments are exactly the command the dry run printed")
            self.assertEqual(args[:2], ["bash", "-c"])
            self.assertTrue(all(len(a) <= 10280 for a in args), "every submitted argument is within the EMR limit")
            self.assertEqual(steps[index]["HadoopJarStep"]["Jar"], "command-runner.jar")
        with open(self.ledger_path(), encoding="utf-8") as handle:
            ledger = [json.loads(l) for l in handle]
        self.assertEqual([entry["event"] for entry in ledger], ["init", "reserve"])
        self.assertEqual(ledger[1]["estimate_usd"], "1.26")
        self.assertEqual(ledger[1]["run_id"], RUN)
        self.assertEqual(ledger[1]["approval_record_sha256"], sha256_bytes(read(self.record_path).encode()), "the reservation stores the approval record sha256 (finding B4)")
        run_dir = os.path.join(self.repo, "target", "pipeline-runs", RUN)
        manifest_path = os.path.join(run_dir, "run-manifest.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(oct(os.stat(manifest_path).st_mode & 0o777), "0o600")
        self.assertEqual(manifest["commit"], self.head())
        self.assertEqual(manifest["cluster_id"], CLUSTER)
        self.assertEqual(manifest["account_sha256"], account_hash())
        self.assertEqual(manifest["artifact_sha256"]["job-jar"], JOB_SHA)
        self.assertEqual(manifest["dataset_snapshots"]["dblp"], {"snapshot": "dblp-snapshot-1", "retrieval": "2026-10-05"})
        self.assertEqual(manifest["run_config_sha256"], self.value_of(dry, "RUN-CONFIG-SHA256: "))
        self.assertEqual(manifest["runtime_archive_sha256"], "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5")
        self.assertEqual(manifest["output_locations"]["spark"], "s3://fixture-bucket/outputs/%s/spark/" % RUN)
        self.assertEqual(manifest["teardown"]["mode"], "auto-termination")
        with open(os.path.join(run_dir, "run-result.json"), encoding="utf-8") as handle:
            outcome = json.load(handle)
        self.assertEqual([o["state"] for o in outcome["step_outcomes"]], ["COMPLETED"] * 6)
        self.assertEqual(self.calls("terraform"), [], "no Terraform command at all")
        self.assertTrue(self.tree_clean(), "the private outputs are git-ignored")
        for secret in (FAKE_SECRET, FAKE_TOKEN, FAKE_ACCOUNT):
            self.assertNotIn(secret, result.out)
            self.assertNotIn(secret, read(manifest_path))

    def test_the_prespend_receipt_is_reverified_before_each_step_submission(self):
        args = self.ready()
        self.use_config()
        now = datetime.datetime.now(datetime.timezone.utc)
        clock = {"default": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "step-spark-job": (now + datetime.timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")}
        clock_path = os.path.join(self.tmp, "clock.json")
        with open(clock_path, "w", encoding="utf-8") as handle:
            json.dump(clock, handle)
        result = self.execute(args, SCHOLARCHAIN_TEST_CLOCK_FILE=clock_path)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("pre-spend receipt rejected before step-spark-job", result.out)
        self.assertEqual(len(self.submitted_steps()), 4, "the four steps before the expiry were submitted, the fifth was not")
        self.assertEqual(result.stdout.count("pre-spend receipt re-verified before submitting step"), 4)

    def test_a_failed_step_stops_the_run_and_later_steps_are_not_submitted(self):
        args = self.ready()
        result = self.execute(args, FAKE_EMR_STEP_STATE_3="FAILED")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(len(self.submitted_steps()), 3)
        self.assertIn("STEP-RESULT: entity-resolution s-FAKE3 FAILED", result.stdout)
        self.assertTrue(last_result(result).startswith("RESULT: FAIL"), last_result(result))
        with open(os.path.join(self.repo, "target", "pipeline-runs", RUN, "run-result.json"), encoding="utf-8") as handle:
            self.assertEqual([o["state"] for o in json.load(handle)["step_outcomes"]], ["COMPLETED", "COMPLETED", "FAILED"])

    def test_the_hard_wall_clock_cap_cancels_the_running_step(self):
        args = self.ready()
        self.use_config()
        result = self.execute(args, FAKE_EMR_STEP_STATE="RUNNING", SCHOLARCHAIN_TEST_DEADLINE_SECONDS="0", PIPELINE_POLL_SECONDS="0")
        self.assertEqual(result.rc, 124, result.out)
        self.assertIn("DEADLINE-OVERRIDE", result.stdout)
        self.assertTrue(any(a.startswith("emr cancel-steps") and "SEND_INTERRUPT" in a and "s-FAKE1" in a for a in self.aws_calls()), self.aws_calls())
        self.assertIn("TIMED OUT at step stage-in", result.out)

    def test_the_wall_clock_override_is_ignored_with_the_real_config(self):
        args = self.ready()
        result = self.execute(args, SCHOLARCHAIN_TEST_DEADLINE_SECONDS="0")
        self.assertIn("DEADLINE-IGNORED", result.stdout)
        self.assertEqual(result.rc, 0, result.out)

    # ---- the approval record must match the human record: every key ----------------------------------------------------
    def test_every_approval_key_mismatch_refuses_before_any_step(self):
        mismatches = {
            "APPROVED_COMMIT": "0" * 40,
            "APPROVED_REGION": "us-west-2",
            "APPROVED_CLUSTER_ID": "j-OTHER123456",
            "APPROVED_RUN_CONFIG_SHA256": "1" * 64,
            "APPROVED_BUDGET_USD": "2.00",
            "APPROVED_MAX_CAPACITY": "4",
            "APPROVED_MAX_RUNTIME_MINUTES": "91",
            "APPROVED_PRESPEND_SHA256": "2" * 64,
            "APPROVED_ACCOUNT_SHA256": "3" * 64,
        }
        for key, value in mismatches.items():
            with self.subTest(key):
                self.setUp_clean()
                args = self.ready(record_override={key: value})
                result = self.execute(args)
                self.refused(result, key)
                self.assertTrue(last_result(result).startswith("RESULT: REFUSED"), last_result(result))
        # the teardown value is a literal
        self.setUp_clean()
        self.refused(self.execute(self.ready(record_override={"APPROVED_TEARDOWN": "none"})), "APPROVED_TEARDOWN")
        self.setUp_clean()
        self.refused(self.execute(self.ready(record_override={"APPROVED_ACTION": "run-experiment"})), "APPROVED_ACTION")

    def setUp_clean(self):
        """Fresh fake call logs between sub-cases."""
        for path in (self.log, self.log + ".steps"):
            if os.path.exists(path):
                open(path, "w").close()

    def test_account_mismatch_is_detected_with_a_single_read_only_call(self):
        args = self.ready(record_override={"APPROVED_ACCOUNT_SHA256": account_hash("999999999999")})
        result = self.execute(args)
        self.refused(result, "APPROVED_ACCOUNT_SHA256")
        self.assertEqual(self.emr_ops(), [])
        self.assertEqual([a.split()[:2] for a in self.aws_calls()], [["sts", "get-caller-identity"]])

    def test_a_malformed_record_is_refused_line_by_line(self):
        base = self.ready()
        run_sha = self.value_of(self.dry(), "RUN-CONFIG-SHA256: ")
        good = self.approval_lines(run_sha, self.prespend_sha)
        cases = {
            "missing key": ({k: v for k, v in good.items() if k != "APPROVED_REGION"}, ""),
            "duplicate key": (good, "APPROVED_REGION=us-east-2\n"),
            "quoted value": ({**good, "APPROVED_REGION": '"us-east-2"'}, ""),
            "uppercase hex": ({**good, "APPROVED_RUN_CONFIG_SHA256": run_sha.upper()}, ""),
            "spaces around equals": ({k: v for k, v in good.items() if k != "APPROVED_REGION"}, "APPROVED_REGION = us-east-2\n"),
            "indented line": ({k: v for k, v in good.items() if k != "APPROVED_REGION"}, "  APPROVED_REGION=us-east-2\n"),
            "carriage return": ({**good, "APPROVED_REGION": "us-east-2\r"}, ""),
            "forbidden manifest line": (good, "APPROVED_MANIFEST_SHA256=" + "4" * 64 + "\n"),
        }
        for label, (values, extra) in cases.items():
            with self.subTest(label):
                self.setUp_clean()
                record = self.write_record(values, name="bad-%s.md" % label.replace(" ", "-"), raw_extra=extra)
                args = [a for a in base]
                args[args.index("--approval") + 1] = record
                self.refused(self.execute(args), "approval record")

    def test_a_missing_approval_or_prespend_file_refuses(self):
        args = self.ready()
        args[args.index("--approval") + 1] = os.path.join(self.tmp, "absent.md")
        self.refused(self.execute(args), "approval record not found")
        args = self.ready()
        args[args.index("--prespend") + 1] = os.path.join(self.tmp, "absent.json")
        self.refused(self.execute(args), "pre-spend receipt not found")

    def test_prespend_receipt_failures_refuse(self):
        cases = {
            "stale snapshot": {"cost_snapshot_utc": utc_hours_ago(30)},
            "monitoring not confirmed": {"monitoring_confirmed_active": False},
            "headroom below 3 USD": {"remaining_headroom_usd": 2.99},
            "headroom 1 USD (not enough for a paid run; cleanup-prepare has no floor)": {"remaining_headroom_usd": 1},
            "negative headroom": {"remaining_headroom_usd": -0.01},
        }
        for label, override in cases.items():
            with self.subTest(label):
                self.setUp_clean()
                args = self.ready(prespend_override=override)
                result = self.execute(args)
                self.refused(result, "pre-spend receipt rejected before initial")
                self.assertEqual(self.emr_ops(), [])

    def test_prespend_headroom_of_exactly_the_pinned_3_usd_floor_is_accepted_and_the_cleanup_exemption_does_not_apply(self):
        """Hand-derived: the floor is PRESPEND_MIN_HEADROOM_USD = 3 (inclusive). The absence of a floor is deploy.sh --stage
        cleanup-prepare only; a bounded pipeline run keeps the normal floor, so 1 USD is refused (see the failures test above)."""
        args = self.ready(prespend_override={"remaining_headroom_usd": 3})
        self.assertEqual(self.execute(args).rc, 0)

    def test_a_dirty_tree_refuses_but_only_the_literal_record_path_is_exempt(self):
        args = self.ready()
        self.write("stray.txt", "x\n")
        self.refused(self.execute(args), "work tree is dirty")
        os.remove(os.path.join(self.repo, "stray.txt"))
        literal = os.path.join(self.repo, "docs/agent-runs/phase-15/human-gate.md")
        os.makedirs(os.path.dirname(literal), exist_ok=True)
        with open(literal, "w", encoding="utf-8") as handle:
            handle.write(read(self.record_path))
        args[args.index("--approval") + 1] = literal
        self.setUp_clean()
        self.assertEqual(self.execute(args).rc, 0)
        self.setUp_clean()
        alias = literal + ".bak"
        with open(alias, "w", encoding="utf-8") as handle:
            handle.write("x")
        self.refused(self.execute(args), "work tree is dirty")

    # ---- G6 ---------------------------------------------------------------------------------------------------------------
    def test_g6_unconfirmed_pricing_refuses_execute_until_the_human_confirms(self):
        args = self.ready(pricing_confirmed=False)
        result = self.execute(args)
        self.refused(result, "pricing is not confirmed by the human", "EMR_PRICING_CONFIRMED_BY_HUMAN")
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.dry().rc, 0, "the dry run still passes and says --execute would be refused")
        self.assertIn("G6-STATUS: --execute would be refused", self.dry().stdout)

    def test_g6_environment_variables_cannot_confirm_pricing_or_set_rates(self):
        args = self.ready(pricing_confirmed=False)
        result = self.execute(args, EMR_PRICING_CONFIRMED_BY_HUMAN="true", EMR_RATE_EC2_M5_XLARGE="0.0001")
        self.refused(result, "pricing is not confirmed")
        self.assertIn("CONFIG-IGNORED: pinned pricing settings cannot be overridden by the environment", result.stdout)
        self.assertIn("ESTIMATE-USD: 1.26", result.stdout)

    def test_g6_missing_rates_refuse_execute_and_are_never_read_as_zero(self):
        self.set_pricing(drop=("EMR_RATE_EC2_M5_XLARGE", "EMR_RATE_EMR_M5_XLARGE"))
        dry = self.dry()
        self.assertEqual(dry.rc, 0, dry.out)
        self.assertIn("ESTIMATE-USD: unavailable", dry.stdout)
        self.assertNotIn("ESTIMATE-USD: 0", dry.stdout)
        args = self.ready()
        self.set_pricing(drop=("EMR_RATE_EC2_M5_XLARGE", "EMR_RATE_EMR_M5_XLARGE"))
        # the run configuration changed (the estimate is part of it), so rebuild the record for the new hash
        run_sha = self.run_config_sha()
        record = self.write_record(self.approval_lines(run_sha, self.prespend_sha), name="norates.md")
        args[args.index("--approval") + 1] = record
        result = self.execute(args)
        self.refused(result, "no reviewed hourly rate for m5.xlarge")
        self.assertEqual(self.calls(), [])
        env = self.execute(args, EMR_RATE_EC2_M5_XLARGE="0.1", EMR_RATE_EMR_M5_XLARGE="0.1")
        self.refused(env, "no reviewed hourly rate")

    def test_g6_three_live_runs_in_the_ledger_refuse(self):
        args = self.ready()
        self.write_ledger(["0.50", "0.50", "0.50"])
        self.refused(self.execute(args), "3 live EMR runs are already recorded in the ledger (limit 3)")
        self.assertEqual(self.calls(), [])

    def test_g6_the_cumulative_estimate_may_not_exceed_2_52(self):
        """Hand-derived with the pinned cap 2.52 (user decision 2026-11-09) and this run's estimate 1.26 (2 x 0.24 x 2.625 h)."""
        args = self.ready()
        self.write_ledger(["1.00", "0.27"])  # 1.27 + 1.26 = 2.53 > 2.52
        self.refused(self.execute(args), "cumulative estimate 2.53 USD (recorded 1.27 + this run 1.26) would exceed the cap 2.52 USD")
        self.write_ledger(["1.00", "0.26"])  # 1.26 + 1.26 = 2.52 <= 2.52: allowed (the cap is inclusive)
        self.setUp_clean()
        self.assertEqual(self.execute(args).rc, 0)

    def test_g6_a_third_run_that_the_count_allows_is_still_refused_when_it_would_pass_the_2_52_cap(self):
        """Two recorded runs of 0.50 and 0.60 total 1.10; a third of 1.26 makes 2.36 (allowed); a ledger of 1.00, 1.00 makes 3.26 (refused)."""
        args = self.ready()
        self.write_ledger(["0.50", "0.60"])
        self.assertEqual(self.execute(args).rc, 0)
        self.setUp_clean()
        self.write_ledger(["1.00", "1.00"])
        self.refused(self.execute(args), "cumulative estimate 3.26 USD (recorded 2.00 + this run 1.26) would exceed the cap 2.52 USD")

    def test_g6_a_malformed_ledger_refuses_rather_than_reading_as_empty(self):
        args = self.ready()
        os.makedirs(os.path.dirname(self.ledger_path()), exist_ok=True)
        with open(self.ledger_path(), "w", encoding="utf-8") as handle:
            handle.write("not json\n")
        self.refused(self.execute(args), "the run ledger cannot be read")

    def test_g6_each_execute_adds_one_ledger_line_so_the_fourth_run_is_refused(self):
        # This test isolates the run COUNT limit: three runs of 1.26 (3.78) would exceed the 2.52 USD cumulative cap, which has its own tests.
        self.use_config(EMR_CUMULATIVE_CAP_USD="9.50")
        for index in range(3):
            args = self.ready(serial=index, **{"--run-id": "bp-test-%04d" % (index + 10)})
            self.setUp_clean()
            self.assertEqual(self.execute(args).rc, 0, index)
        with open(self.ledger_path(), encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 4, "the init record and three reservations")
        args = self.ready(serial=99, **{"--run-id": "bp-test-0099"})
        self.setUp_clean()
        self.refused(self.execute(args), "3 live EMR runs")

    # ---- forced auto-termination and capacity (read from the live cluster, before anything paid) -------------------------------
    def test_a_cluster_without_auto_termination_is_refused_before_any_step(self):
        args = self.ready()
        result = self.execute(args, FAKE_EMR_IDLE="none")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("NO auto-termination policy", result.out)
        self.assertEqual(self.emr_ops(), ["describe-cluster", "get-auto-termination-policy", "list-instance-groups"])
        self.assertEqual(self.submitted_steps(), [])
        with open(self.ledger_path(), encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 1, "no ledger slot is reserved for a refused run")

    def test_cluster_state_idle_timeout_type_and_capacity_are_verified(self):
        def groups(core=1, task=0, kind="m5.xlarge", master=1):
            return json.dumps(
                [
                    {"InstanceGroupType": "MASTER", "InstanceType": kind, "RequestedInstanceCount": master, "RunningInstanceCount": master},
                    {"InstanceGroupType": "CORE", "InstanceType": kind, "RequestedInstanceCount": core, "RunningInstanceCount": core},
                    {"InstanceGroupType": "TASK", "InstanceType": kind, "RequestedInstanceCount": task, "RunningInstanceCount": task},
                ]
            )

        cases = {
            "terminated cluster": ({"FAKE_EMR_STATE": "TERMINATED"}, "the cluster state is TERMINATED"),
            "idle timeout above the cap": ({"FAKE_EMR_IDLE": "7200"}, "idle timeout 7200 s is outside 60..900 s"),
            "idle timeout one above the 900 s cap (finding B3)": ({"FAKE_EMR_IDLE": "901"}, "idle timeout 901 s is outside 60..900 s"),
            "the former 3600 s cap is refused now": ({"FAKE_EMR_IDLE": "3600"}, "idle timeout 3600 s is outside 60..900 s"),
            "idle timeout below 60": ({"FAKE_EMR_IDLE": "30"}, "outside 60..900"),
            "other instance type": ({"FAKE_EMR_GROUPS": groups(kind="m5.2xlarge")}, "uses m5.2xlarge, not the approved m5.xlarge"),
            "more core nodes than approved": ({"FAKE_EMR_GROUPS": groups(core=2)}, "CORE group has 2 instances, above the approved 1"),
            "more task nodes than approved": ({"FAKE_EMR_GROUPS": groups(task=2)}, "TASK group has 2 instances, above the approved 1"),
            "other cluster": ({"FAKE_EMR_CLUSTER_ID": "j-OTHER123456"}, "another cluster id"),
        }
        for label, (env, needle) in cases.items():
            with self.subTest(label):
                self.setUp_clean()
                args = self.ready()
                result = self.execute(args, **env)
                self.assertEqual(result.rc, 4, result.out)
                self.assertIn(needle, result.out)
                self.assertEqual(self.submitted_steps(), [])

    def test_no_aws_call_is_made_when_a_local_gate_refuses(self):
        args = self.ready()
        args[args.index("--approval") + 1] = os.path.join(self.tmp, "absent.md")
        self.refused(self.execute(args))
        self.assertEqual(self.calls(), [])

    def test_execute_needs_a_profile(self):
        args = self.ready()
        i = args.index("--profile")
        del args[i : i + 2]
        result = self.execute(args, AWS_PROFILE=None)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("approved AWS profile", result.out)
        self.assertEqual(self.calls(), [])


class StepBodyTests(PipelineFixture):
    """The cluster bodies run locally against a fake primary node (mount, runtime, Java 17 home file, fake commands)."""

    def setUp(self):
        super().setUp()
        self.node_config()
        self.run_root = os.path.join(self.mnt, "runs", RUN)

    def local_artifacts(self, **extra):
        """Local copies of the jars and configs so the plan hashes them and the body can localize them with cp."""
        refs = {}
        for name in ("hadoop-submit", "hadoop-bundle", "er"):
            path = os.path.join(self.inputs, name + ".jar")
            with open(path, "wb") as handle:
                handle.write(("bytes-of-" + name).encode())
            refs[name] = path
        for name in ("er-policy", "er-config"):
            path = os.path.join(self.inputs, name + ".json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}\n")
            refs[name] = path
        template = os.path.join(self.inputs, "spark-template.json")
        with open(os.path.join(PIPELINE_FIXTURES, "spark-template.json"), encoding="utf-8") as src, open(template, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        refs["spark-template"] = template
        overrides = {
            "--hadoop-submit-jar": refs["hadoop-submit"],
            "--hadoop-libjars": refs["hadoop-bundle"],
            "--er-jar": refs["er"],
            "--er-policy": refs["er-policy"],
            "--er-config": refs["er-config"],
            "--spark-config-template": template,
            "drop": ("--artifact-sha256:hadoop-submit-jar", "--artifact-sha256:hadoop-libjars", "--artifact-sha256:er-jar", "--artifact-sha256:er-policy", "--artifact-sha256:er-config", "--artifact-sha256:spark-config-template"),
        }
        overrides.update(extra)
        return overrides

    def make_completed_hadoop(self):
        run = os.path.join(self.run_root, "hadoop", "run-1")
        os.makedirs(run)
        with open(os.path.join(run, "_SCHOLARCHAIN_COMPLETE"), "w", encoding="utf-8") as handle:
            handle.write("done\n")
        return run

    def probe_file(self, mutate=None):
        with open(os.path.join(PIPELINE_FIXTURES, "probe-ok.json"), encoding="utf-8") as handle:
            document = json.load(handle)
        jars = os.path.join(self.runtime, "jars") + "/"
        for report in [document["driver"]] + document["taskProcesses"]:
            for lib in report["libraries"]:
                if lib["component"] == "scala3-library":
                    lib["origin"] = self.jobjar
                    lib["codeSourceSha256"] = JOB_SHA
                else:
                    lib["origin"] = jars + os.path.basename(lib["origin"])
        if mutate:
            mutate(document)
        path = os.path.join(self.tmp, "probe.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return path

    def stage_class_origin(self, mutate=None):
        os.makedirs(os.path.join(self.run_root, "results"), exist_ok=True)
        target = os.path.join(self.run_root, "results", "class-origin.json")
        with open(self.probe_file(mutate), encoding="utf-8") as src, open(target, "w", encoding="utf-8") as dst:
            dst.write(src.read())

    def spark_job_ready(self, mutate=None):
        body = self.step_body("spark-job", **self.local_artifacts())
        self.make_completed_hadoop()
        os.makedirs(os.path.join(self.run_root, "er", "run"))
        self.stage_class_origin(mutate)
        return body

    # ---- item 1: the YARN application is killed by tag when the runtime cap fires ---------------------------------------------
    def test_item_1_the_runtime_cap_kills_the_yarn_application_by_tag(self):
        body = self.spark_job_ready()
        for rc in ("124", "137", "143"):
            with self.subTest(rc):
                with open(self.nodelog, "w"):
                    pass
                for leftover in ("spark", "config"):
                    shutil.rmtree(os.path.join(self.run_root, leftover), ignore_errors=True)
                result = self.run_body(body, {"FAKE_TIMEOUT_RC": rc, "FAKE_YARN_APP": "1"})
                self.assertEqual(result.returncode, int(rc), result.stdout + result.stderr)
                self.assertIn("runtime cap reached (exit %s): killing the YARN application tagged %s" % (rc, RUN), result.stdout)
                calls = self.node_calls()
                lists = [c for c in calls if c.startswith("yarn application -list")]
                kills = [c for c in calls if c.startswith("yarn application -kill")]
                self.assertTrue(lists, calls)
                self.assertIn("-appTags %s" % RUN, lists[0])
                self.assertIn("-appStates NEW,NEW_SAVING,SUBMITTED,ACCEPTED,RUNNING", lists[0])
                self.assertIn("yarn application -kill application_1700000000000_0007", kills)
                first_kill = calls.index(kills[0])
                self.assertTrue(any(c.startswith("timeout --kill-after=60 2160") for c in calls[:first_kill]), "the kill follows the timed-out spark-submit")

    def test_item_1_no_kill_is_issued_when_the_step_finishes_inside_the_cap(self):
        body = self.spark_job_ready()
        result = self.run_body(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("runtime cap reached", result.stdout)
        self.assertEqual([c for c in self.node_calls() if c.startswith("yarn application -kill")], [])

    def test_item_1_hadoop_prep_is_tagged_and_killed_by_tag_too(self):
        body = self.step_body("hadoop-prep", **self.local_artifacts())
        os.makedirs(os.path.join(self.run_root, "inputs"))
        result = self.run_body(body, {"FAKE_TIMEOUT_RC": "124", "FAKE_YARN_APP": "1"})
        self.assertEqual(result.returncode, 124, result.stdout + result.stderr)
        calls = self.node_calls()
        self.assertTrue(any(c.startswith("yarn application -kill application_1700000000000_0007") for c in calls), calls)
        self.assertTrue(any(c.startswith("timeout --kill-after=60 1080 hadoop jar") for c in calls), calls)

    # ---- the spark step: exact spark-submit arguments ---------------------------------------------------------------------------
    def test_the_spark_job_step_runs_spark_submit_with_the_decision_12_10_arguments(self):
        body = self.spark_job_ready()
        result = self.run_body(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        submits = [c for c in self.node_calls() if c.startswith("spark-submit ")]
        self.assertEqual(len(submits), 1)
        line = submits[0]
        for needle in (
            "--master yarn --deploy-mode cluster",
            "--class edu.uic.cs441.scholarchain.spark.Phase6Main",
            "--conf spark.yarn.tags=%s" % RUN,
            "--conf spark.yarn.jars=local:/opt/scholarchain-runtime/jars/*",
            "--conf spark.yarn.populateHadoopClasspath=false",
            "--conf spark.network.crypto.authEngineVersion=1",
            "--conf spark.io.encryption.enabled=true",
            "--conf spark.authenticate=true",
            "--conf spark.dynamicAllocation.shuffleTracking.enabled=true",
            "--conf spark.yarn.appMasterEnv.JAVA_HOME=%s" % self.javahome,
            "--conf spark.executorEnv.JAVA_HOME=%s" % self.javahome,
            "--conf spark.yarn.stagingDir=file://%s/staging" % self.mnt,
            "local:%s %s/config/spark-config.json" % (self.jobjar, self.run_root),
        ):
            self.assertIn(needle, line)
        self.assertNotIn("lzo", line.lower())
        timeouts = [c for c in self.node_calls() if c.startswith("timeout ")]
        self.assertEqual(timeouts[0].split()[:3], ["timeout", "--kill-after=60", "2160"])
        rendered = os.path.join(self.run_root, "config", "spark-config.json")
        with open(rendered, encoding="utf-8") as handle:
            config = json.load(handle)
        self.assertEqual(config["hadoopRunRoot"], os.path.join(self.run_root, "hadoop", "run-1"))
        self.assertEqual(config["entityResolutionRunRoot"], os.path.join(self.run_root, "er", "run"))
        self.assertEqual(config["outputRoot"], os.path.join(self.run_root, "spark"))
        self.assertEqual(config["shufflePartitions"], 4, "template keys other than the four paths are preserved")

    # ---- the class-origin check is fail-closed ---------------------------------------------------------------------------------
    def test_a_failing_class_origin_result_stops_the_spark_job_before_spark_submit(self):
        def other_scala(document):
            for lib in document["taskProcesses"][0]["libraries"]:
                if lib["component"] == "scala-library":
                    lib["runtimeVersion"] = "2.13.12"

        body = self.spark_job_ready(other_scala)
        result = self.run_body(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CLASS-ORIGIN-FAILED", result.stderr)
        self.assertEqual([c for c in self.node_calls() if c.startswith("spark-submit")], [], "the Spark job must not start")

    def test_a_missing_class_origin_result_stops_the_spark_job(self):
        body = self.step_body("spark-job", **self.local_artifacts())
        self.make_completed_hadoop()
        os.makedirs(os.path.join(self.run_root, "er", "run"))
        result = self.run_body(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to start the Spark job", result.stderr)
        self.assertEqual([c for c in self.node_calls() if c.startswith("spark-submit")], [])

    def test_the_class_origin_step_submits_the_probe_and_fails_closed_without_a_result(self):
        body = self.step_body("spark-class-origin", **self.local_artifacts())
        os.makedirs(os.path.join(self.run_root, "inputs"))
        absent = self.run_body(body)
        self.assertNotEqual(absent.returncode, 0, "no probe output must be a failure")
        self.assertIn("CLASS-ORIGIN-FAILED: probe result unreadable", absent.stderr)
        submit = [c for c in self.node_calls() if c.startswith("spark-submit")][0]
        self.assertIn("--class edu.uic.cs441.scholarchain.spark.Phase12Readiness", submit)
        self.assertTrue(submit.endswith("probe %s/probe %s/results/class-origin.json distributed" % (self.run_root, self.run_root)), submit)
        self.assertIn("--conf spark.yarn.tags=%s" % RUN, submit)
        with open(self.nodelog, "w"):
            pass
        ok = self.run_body(body, {"FAKE_PROBE_SRC": self.probe_file()})
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("CLASS-ORIGIN-OK: the driver and 1 executor report(s) agree on Spark 3.5.4, Scala 2.13.14", ok.stdout)

    def test_the_job_jar_on_the_node_must_have_the_approved_sha256(self):
        body = self.spark_job_ready()
        with open(self.jobjar, "wb") as handle:
            handle.write(b"another jar")
        result = self.run_body(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not have the approved sha256", result.stderr)
        self.assertEqual([c for c in self.node_calls() if c.startswith("spark-submit")], [])

    # ---- hadoop prep: ceilings repeated on the cluster ----------------------------------------------------------------------------
    def test_hadoop_prep_runs_phase_4_style_with_the_tag_and_dataset_snapshots(self):
        body = self.step_body("hadoop-prep", **self.local_artifacts())
        os.makedirs(os.path.join(self.run_root, "inputs"))
        result = self.run_body(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        jar = [c for c in self.node_calls() if c.startswith("hadoop jar")][0]
        for needle in (
            "edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain",
            "-Dmapreduce.job.tags=%s" % RUN,
            "--once --execution-mode cluster --run-id %s" % RUN,
            "--output-root file://%s/hadoop" % self.run_root,
            "--dblp file://%s/inputs/datasets/samples/dblp/linked-records.xml --dblp-snapshot dblp-snapshot-1 --dblp-retrieval 2026-10-05" % self.run_root,
            "--orcid file://%s/inputs/datasets/samples/orcid/records.jsonl --orcid-snapshot orcid-snapshot-1" % self.run_root,
        ):
            self.assertIn(needle, jar)
        self.assertTrue([c for c in self.node_calls() if c.startswith("timeout --kill-after=60 1080 hadoop jar")])

    def test_hadoop_prep_repeats_the_ceiling_check_on_the_cluster_before_hadoop_jar(self):
        late = os.path.join(self.tmp, "late-config.json")  # not there at plan time, so only the cluster check can see it
        with open(self.prep_config, encoding="utf-8") as handle:
            document = json.load(handle)
        document["reducerCount"] = 9
        text = json.dumps(document)
        over = self.local_artifacts(**{"--hadoop-config": late})
        over["--artifact-sha256:hadoop-config"] = "x"
        args = self.pipeline_args(**{k: v for k, v in over.items() if k != "--artifact-sha256:hadoop-config"})
        args += ["--artifact-sha256", "hadoop-config=%s" % sha256_bytes(text.encode())]
        plan = self.run_pipeline(args=args)
        self.assertEqual(plan.rc, 0, plan.out)
        body = plan.stdout.split("STEP-BODY-BEGIN: hadoop-prep\n", 1)[1].split("STEP-BODY-END: hadoop-prep\n", 1)[0]
        with open(late, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.makedirs(os.path.join(self.run_root, "inputs"))
        result = self.run_body(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reducerCount 9 exceeds ceiling 8", result.stderr)
        self.assertEqual([c for c in self.node_calls() if c.startswith("hadoop jar")], [], "hadoop jar must not run")

    # ---- entity resolution, stage-in and copy-out ------------------------------------------------------------------------------------
    def test_entity_resolution_uses_the_java_home_the_bootstrap_resolved(self):
        body = self.step_body("entity-resolution", **self.local_artifacts())
        self.make_completed_hadoop()
        result = self.run_body(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        java = [c for c in self.node_calls() if c.startswith("java ") and "-cp" in c][0]
        self.assertIn("-Xmx3g -cp", java)
        self.assertIn("edu.uic.cs441.scholarchain.entityresolution.Phase5Main resolve", java)
        self.assertIn("--input %s/hadoop/run-1" % self.run_root, java)
        self.assertIn("--llm-mode disabled --output %s/er/run" % self.run_root, java)
        self.assertTrue(any(c.startswith("timeout --kill-after=60 1080 %s/bin/java" % self.javahome) for c in self.node_calls()))
        os.remove(self.javafile)
        with open(self.nodelog, "w"):
            pass
        os.rename(os.path.join(self.run_root, "er"), os.path.join(self.tmp, "er-away"))
        missing = self.run_body(body)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("no resolved Java 17 home", missing.stderr)
        self.assertEqual([c for c in self.node_calls() if c.startswith("java ") and "-cp" in c], [])

    def test_entity_resolution_refuses_a_non_17_java(self):
        body = self.step_body("entity-resolution", **self.local_artifacts())
        self.make_completed_hadoop()
        with open(os.path.join(self.javahome, "bin", "java"), "w", encoding="utf-8") as handle:
            handle.write('#!/bin/bash\necho \'openjdk version "11.0.2" 2019-01-15\' >&2\n')
        result = self.run_body(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("the resolved Java is not 17", result.stderr)

    def test_stage_in_copies_from_s3_to_efs_inside_the_size_ceiling(self):
        body = self.step_body("stage-in")
        ok = self.run_body(body, {"FAKE_S3_TOTAL": "268435456"})
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        cp = [a for a in self.aws_calls() if a.startswith("s3 cp")]
        self.assertEqual(cp, ["s3 cp s3://fixture-bucket/inputs/ %s/inputs/ --recursive --region %s --only-show-errors" % (self.run_root, REGION)])

    def test_stage_in_refuses_oversize_input_a_non_mount_and_a_reused_run_directory(self):
        body = self.step_body("stage-in")
        big = self.run_body(body, {"FAKE_S3_TOTAL": "268435457"})
        self.assertNotEqual(big.returncode, 0)
        self.assertIn("exceeds the 268435456 byte ceiling", big.stderr)
        self.assertEqual([a for a in self.aws_calls() if a.startswith("s3 cp")], [])
        with open(self.procmounts, "w", encoding="utf-8") as handle:
            handle.write("")
        notmount = self.run_body(body)
        self.assertNotEqual(notmount.returncode, 0)
        self.assertIn("is not a mount point", notmount.stderr)
        with open(self.procmounts, "w", encoding="utf-8") as handle:
            handle.write("fs-fake:/ %s efs rw 0 0\n" % self.mnt)
        os.makedirs(self.run_root)
        reused = self.run_body(body)
        self.assertNotEqual(reused.returncode, 0)
        self.assertIn("already exists", reused.stderr)

    def test_copy_out_copies_results_to_s3_with_a_manifest_inside_the_ceiling(self):
        for part in ("hadoop", "er", "spark", "results", "config"):
            os.makedirs(os.path.join(self.run_root, part))
            with open(os.path.join(self.run_root, part, "f.txt"), "w", encoding="utf-8") as handle:
                handle.write(part + "\n")
        body = self.step_body("copy-out")
        result = self.run_body(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        cp = [a for a in self.aws_calls() if a.startswith("s3 cp")]
        for part in ("hadoop", "er", "spark", "results", "config"):
            self.assertIn("s3 cp %s/%s/ s3://fixture-bucket/outputs/%s/%s/ --recursive --region %s --only-show-errors" % (self.run_root, part, RUN, part, REGION), cp)
        self.assertTrue(any("copyout-manifest.sha256" in a and "s3://fixture-bucket/outputs/%s/copyout-manifest.sha256" % RUN in a for a in cp))
        with open(os.path.join(self.run_root, "copyout-manifest.sha256"), encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        self.assertEqual(len(lines), 5)
        self.assertIn("%s  hadoop/f.txt" % sha256_bytes(b"hadoop\n"), lines)

    def test_copy_out_refuses_an_oversize_result(self):
        self.node_config(PIPELINE_MAX_COPYOUT_BYTES="1")
        os.makedirs(os.path.join(self.run_root, "spark"))
        with open(os.path.join(self.run_root, "spark", "f.txt"), "w", encoding="utf-8") as handle:
            handle.write("data\n")
        body = self.step_body("copy-out")
        result = self.run_body(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeds the 1 byte ceiling", result.stderr)
        self.assertEqual([a for a in self.aws_calls() if a.startswith("s3 cp")], [])


class ClassOriginVerifierTests(PipelineFixture):
    """The verifier program the cluster runs, executed here through pipeline.py with hand-built probe results."""

    def verify(self, mutate=None, job_sha=JOB_SHA, spark="3.5.4", scala="2.13.14"):
        with open(os.path.join(PIPELINE_FIXTURES, "probe-ok.json"), encoding="utf-8") as handle:
            document = json.load(handle)
        for report in [document["driver"]] + document["taskProcesses"]:
            for lib in report["libraries"]:
                if lib["component"] == "scala3-library":
                    lib["codeSourceSha256"] = JOB_SHA
        if mutate:
            mutate(document)
        path = os.path.join(self.tmp, "probe.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        completed = subprocess.run(
            [sys.executable, "-I", os.path.join(SCRIPTS_DIR, "lib", "pipeline.py"), "verify-class-origin", path, spark, scala, "/opt/scholarchain-runtime/jars", "/opt/scholarchain-runtime/application/scholarchain-job.jar", job_sha],
            capture_output=True,
            text=True,
        )
        return completed

    @staticmethod
    def lib(document, role, component):
        report = document["driver"] if role == "driver" else document["taskProcesses"][0]
        return [l for l in report["libraries"] if l["component"] == component][0]

    def test_matching_driver_and_executor_pass(self):
        done = self.verify()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("CLASS-ORIGIN-OK", done.stdout)

    def test_every_difference_fails_closed(self):
        cases = {
            "executor Scala library version": (lambda d: self.lib(d, "executor", "scala-library").update(runtimeVersion="2.13.12"), "Scala library version 2.13.12"),
            "driver Scala library version": (lambda d: self.lib(d, "driver", "scala-library").update(runtimeVersion="2.12.18"), "differs from the packaged job"),
            "executor Spark version": (lambda d: self.lib(d, "executor", "spark").update(runtimeVersion="3.5.4-amzn-0"), "Spark version"),
            "stock EMR Spark origin": (lambda d: self.lib(d, "executor", "spark").update(origin="/usr/lib/spark/jars/spark-core_2.12-3.5.4-amzn-0.jar"), "outside the runtime jar directory"),
            "scala-library from another directory": (lambda d: self.lib(d, "driver", "scala-library").update(origin="/usr/lib/spark/jars/scala-library-2.13.14.jar"), "outside the runtime jar directory"),
            "scala-library jar of another patch level": (lambda d: self.lib(d, "driver", "scala-library").update(origin="/opt/scholarchain-runtime/jars/scala-library-2.13.12.jar"), "is not scala-library-2.13.14.jar"),
            "scala3-library from another jar": (lambda d: self.lib(d, "executor", "scala3-library").update(origin="/opt/scholarchain-runtime/jars/scala3-library_3-3.3.4.jar"), "not loaded from the packaged job jar"),
            "scala3-library jar with another sha256": (lambda d: self.lib(d, "executor", "scala3-library").update(codeSourceSha256="9" * 64), "not loaded from the packaged job jar"),
            "executor class bytes differ from the driver": (lambda d: self.lib(d, "executor", "scala-library").update(classSha256="8" * 64), "classSha256 differs between the driver and executor-2"),
            "executor jar bytes differ from the driver": (lambda d: self.lib(d, "executor", "spark").update(codeSourceSha256="7" * 64), "codeSourceSha256 differs"),
            "executor on Java 11": (lambda d: d["taskProcesses"][0].update(javaVersion="11.0.2"), "not 17"),
            "driver on Java 8": (lambda d: d["driver"].update(javaVersion="1.8.0_402"), "not 17"),
            "no executor report": (lambda d: d.update(taskProcesses=[]), "missing"),
            "executor not verified outside the driver": (lambda d: d.update(externalExecutorVerified=False), "not verified outside the driver process"),
            "the driver acting as the executor": (lambda d: d["taskProcesses"][0].update(executorId="driver"), "not an executor process"),
            "missing scala-reflect": (lambda d: d["driver"].update(libraries=[l for l in d["driver"]["libraries"] if l["component"] != "scala-reflect"]), "lacks scala-reflect"),
            "wrong schema": (lambda d: d.update(schemaVersion="other"), "not a Phase 12 readiness probe result"),
        }
        for label, (mutate, needle) in cases.items():
            with self.subTest(label):
                done = self.verify(mutate)
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertIn("CLASS-ORIGIN-FAILED", done.stderr)
                self.assertIn(needle, done.stderr)
                self.assertNotIn("CLASS-ORIGIN-OK", done.stdout)

    def test_a_different_packaged_job_hash_or_pinned_version_fails(self):
        self.assertEqual(self.verify(job_sha="a" * 64).returncode, 1)
        self.assertEqual(self.verify(spark="3.5.5").returncode, 1)
        self.assertEqual(self.verify(scala="2.13.15").returncode, 1)

    def test_an_unreadable_probe_file_fails(self):
        done = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS_DIR, "lib", "pipeline.py"), "verify-class-origin", os.path.join(self.tmp, "absent.json"), "3.5.4", "2.13.14", "/j", "/j/job.jar", JOB_SHA], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("probe result unreadable", done.stderr)


class Phase4ParityTests(unittest.TestCase):
    def test_the_pinned_ceilings_and_field_order_equal_the_phase_4_smoke_script(self):
        smoke = read(os.path.join(SCRIPTS_DIR, "phase4-emr-smoke.sh"))
        values = {name: int(v) for name, v in re.findall(r"readonly SMOKE_MAX_([A-Z_]+)=(\d+)", smoke)}
        conf = {k: v for k, v in re.findall(r"^PIPELINE_CEILING_([A-Z_]+)=(\d+)$", read(os.path.join(SCRIPTS_DIR, "config", "release.conf")), re.M)}
        pipeline_values = {(k[len("MAX_"):] if k.startswith("MAX_") else k): int(v) for k, v in conf.items()}
        # Six ceilings are identical to the Phase 4 smoke script; maxLocalSampleRecords is the documented pipeline-specific exception.
        self.assertEqual(values["LOCAL_SAMPLE_RECORDS"], PHASE4_LOCAL_SAMPLE_CEILING, "the Phase 4 smoke script keeps its own 1000")
        self.assertEqual(pipeline_values["LOCAL_SAMPLE_RECORDS"], PIPELINE_LOCAL_SAMPLE_CEILING)
        self.assertEqual({k: v for k, v in pipeline_values.items() if k != "LOCAL_SAMPLE_RECORDS"}, {k: v for k, v in values.items() if k != "LOCAL_SAMPLE_RECORDS"})
        phase4_fields = re.search(r"FIELDS = \((.*?)\)", smoke, re.S).group(1)
        ours = re.search(r"FIELDS = \((.*?)\)", read(os.path.join(SCRIPTS_DIR, "lib", "pipeline.py")), re.S).group(1)
        self.assertEqual(re.findall(r'"(\w+)"', phase4_fields), re.findall(r'"(\w+)"', ours))
        expected = dict(values, LOCAL_SAMPLE_RECORDS=PIPELINE_LOCAL_SAMPLE_CEILING)
        self.assertEqual(
            [CEILINGS[f] for f in re.findall(r'"(\w+)"', phase4_fields)],
            [expected[k] for k in ("LOCAL_SAMPLE_RECORDS", "REDUCER_COUNT", "CANDIDATE_BLOCK_SIZE", "CANDIDATE_PAIRS_PER_BLOCK", "AUTHOR_TEAM_SIZE", "RECORD_BYTES", "XML_ENTITY_EXPANSION")],
        )

    def test_the_largest_phase_15a_input_fits_the_pipeline_ceiling_and_the_exception_is_documented_in_the_config(self):
        """The three 15A inputs hold 2648, 5290 and 10577 publications (user decision); the pin must admit the largest and no more than needed."""
        conf = read(os.path.join(SCRIPTS_DIR, "config", "release.conf"))
        pin = int(re.search(r"^PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS=(\d+)$", conf, re.M).group(1))
        self.assertGreaterEqual(pin, 10577)
        self.assertLess(pin, 100000, "not an unbounded ceiling")
        self.assertIn("PIPELINE-SPECIFIC EXCEPTION", conf)

    def test_the_step_weights_never_exceed_the_runtime_and_the_caps_are_the_decided_values(self):
        conf = read(os.path.join(SCRIPTS_DIR, "config", "release.conf"))
        weights = re.search(r"^PIPELINE_STEP_WEIGHTS=(.*)$", conf, re.M).group(1).split()
        self.assertEqual(sum(int(w.split("=")[1]) for w in weights), 100)
        self.assertEqual(re.search(r"^EMR_MAX_RUN_USD=(.*)$", conf, re.M).group(1), "3")
        self.assertEqual(re.search(r"^EMR_MAX_LIVE_RUNS=(.*)$", conf, re.M).group(1), "3")
        self.assertEqual(re.search(r"^EMR_CUMULATIVE_CAP_USD=(.*)$", conf, re.M).group(1), "2.52")

    def test_the_committed_pricing_file_is_unconfirmed_and_cites_sources_and_a_retrieval_date(self):
        pricing = read(os.path.join(SCRIPTS_DIR, "config", "emr-pricing.conf"))
        self.assertIn("EMR_PRICING_CONFIRMED_BY_HUMAN=false", pricing)
        self.assertRegex(pricing, r"EMR_PRICING_RETRIEVED=\d{4}-\d{2}-\d{2}")
        self.assertIn("https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-2/index.csv", pricing)
        self.assertIn("https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/ElasticMapReduce/current/us-east-2/index.json", pricing)
        rates = dict(re.findall(r"^(EMR_RATE_[A-Z0-9_]+)=([0-9.]+)$", pricing, re.M))
        # hand-copied from the public price list on the retrieval date (us-east-2, Linux, on-demand): see the file header
        self.assertEqual(rates, {"EMR_RATE_EC2_M5_XLARGE": "0.192", "EMR_RATE_EMR_M5_XLARGE": "0.048", "EMR_RATE_EC2_M5_2XLARGE": "0.384", "EMR_RATE_EMR_M5_2XLARGE": "0.096"})


if __name__ == "__main__":
    unittest.main()

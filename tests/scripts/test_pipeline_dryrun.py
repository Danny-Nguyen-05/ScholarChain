"""Independent dry-run tests for scripts/run-bounded-pipeline.sh (Subphase 13B, test-engineer).

Covers: no cloud call without --execute, greppable markers and a single RESULT line, no secret in output, forced
termination and hard runtime cap in the printed commands (plan section 9, Pipeline), the Spark step carrying the
decision 12-10 settings and a class-origin check before the job, the Terraform-only rule (no create-cluster or
run-job-flow), YARN kill by run tag present in every YARN-submitting body, and the run configuration hash.
"""
import os
import re
import unittest

import sc_support as S


def snapshot(root):
    state = {}
    for base, dirs, files in os.walk(str(root)):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            path = os.path.join(base, name)
            state[os.path.relpath(path, str(root))] = (os.path.getsize(path), os.stat(path).st_mtime_ns)
    return state


class PipelineDryRun(unittest.TestCase):
    def setUp(self):
        self.fx = S.Fixture(self)
        self.run_ = self.fx.dry(secrets=True)

    # ----- no cloud call, nothing written -----
    def test_dry_run_exits_zero_and_calls_no_binary_at_all(self):
        r = self.run_
        self.assertEqual((r.rc, r.status), (0, "DRY-RUN"), r.describe())
        for tool in ("aws", "yarn", "hadoop", "spark-submit", "terraform", "docker", "sbt", "timeout", "java"):
            self.assertEqual(r.tool_calls(tool), [], "dry run called the fake %s" % tool)
        self.assertEqual(r.calls, [])

    def test_dry_run_writes_nothing_into_the_repository(self):
        fx = S.Fixture(self)
        before = snapshot(fx.repo)
        r = fx.dry()
        self.assertEqual(r.rc, 0, r.describe())
        self.assertEqual(before, snapshot(fx.repo), "a dry run created or changed files")
        self.assertFalse((fx.repo / "target").exists())

    def test_every_cloud_command_is_printed_not_run_and_carries_a_timeout(self):
        cmds = self.run_.grep(r"^DRY-RUN CMD: ")
        self.assertEqual(len(cmds), 9, "1 sts + 2 cluster verifications + 6 add-steps expected\n" + "\n".join(c[:120] for c in cmds))
        for c in cmds:
            self.assertRegex(c, r"^DRY-RUN CMD: timeout=\d+s ")
            self.assertIn(" aws ", c)
        verbs = [re.search(r" aws (\S+ \S+)", c).group(1) for c in cmds]
        self.assertEqual(verbs, ["sts get-caller-identity", "emr describe-cluster", "emr get-auto-termination-policy"]
                         + ["emr add-steps"] * 6)
        self.assertFalse(self.run_.grep(r"^CMD: "), "an executed (non-DRY-RUN) command line was printed")

    # ----- markers -----
    def test_every_run_prints_step_markers_and_exactly_one_final_result_line(self):
        r = self.run_
        self.assertEqual(len(r.results()), 1)
        self.assertTrue(r.lines()[-1].startswith("RESULT: DRY-RUN"), r.lines()[-1])
        steps = r.steps()
        self.assertEqual(steps[0], "start")
        self.assertEqual(steps[-1], "dry-run-complete")
        step_markers = [s for s in steps if s.startswith("step-")]
        self.assertEqual(step_markers, ["step-" + n for n in S.STEP_NAMES])
        for expected in ("inputs", "g6-estimate", "plan", "g6-gate", "approval-record", "prespend-receipt", "account-check", "cluster-check"):
            self.assertIn(expected, steps)

    # ----- secrets -----
    def test_no_canary_secret_in_stdout_or_stderr(self):
        for canary in S.CANARIES:
            self.assertNotIn(canary, self.run_.out)
            self.assertNotIn(canary, self.run_.err)

    # ----- forced termination and runtime cap -----
    def test_forced_auto_termination_is_stated_and_verified_by_printed_commands(self):
        r = self.run_
        self.assertTrue(r.grep(r"^TEARDOWN: forced auto-termination"))
        self.assertTrue(r.grep(r"aws emr get-auto-termination-policy .*--cluster-id j-TESTCLUSTER"))
        self.assertTrue(r.grep(r"APPROVAL-LINE: APPROVED_TEARDOWN=auto-termination"))

    def test_step_timeouts_are_weighted_percentages_of_the_runtime_cap_and_never_exceed_it(self):
        r = self.run_
        got = {m.group(1): int(m.group(2)) for m in (re.match(r"STEP-TIMEOUT: (\S+) (\d+)s", l) for l in r.lines()) if m}
        # 60 minutes = 3600 s; weights 5/20/20/5/40/10 percent
        self.assertEqual(got, {"stage-in": 180, "hadoop-prep": 720, "entity-resolution": 720,
                               "spark-class-origin": 180, "spark-job": 1440, "copy-out": 360})
        self.assertLessEqual(sum(got.values()), 60 * 60)
        r2 = self.fx.dry(max_runtime_minutes=120, budget_usd=3)
        got2 = {m.group(1): int(m.group(2)) for m in (re.match(r"STEP-TIMEOUT: (\S+) (\d+)s", l) for l in r2.lines()) if m}
        self.assertEqual(got2["spark-job"], 2880)
        self.assertLessEqual(sum(got2.values()), 120 * 60)

    def test_yarn_submitting_bodies_run_under_timeout_with_the_run_id_as_yarn_tag_and_kill_by_tag(self):
        """C1 form: the step passes TAG, STEP_SECONDS and KILL_AFTER as parameters; the installed runner (the sha256-pinned
        program the step executes) does the timeout and the kill by tag. The behaviour is proven by running it in
        test_pipeline_bodies (YarnKillByTag); here the parameters and the pinned program text are checked."""
        program = S.installed_program(self.fx, "sc-step.sh")
        for name in ("hadoop-prep", "spark-class-origin", "spark-job"):
            params = S.step_params(S.step_args(self.run_, name))
            self.assertEqual(params["TAG"], ["bp-test-run-1"], name)
            self.assertEqual(params["KILL_AFTER"], ["60"], name)
            self.assertEqual(params["STEP_SECONDS"], [str(S.STEP_SECONDS[name])], name)
        self.assertRegex(program, r"timeout --kill-after=")
        self.assertIn("yarn application -list", program)
        self.assertIn("-appTags", program)
        self.assertIn("yarn application -kill", program)
        for code in ("124", "137", "143"):
            self.assertIn(code, program, "the runner must treat exit %s as the runtime cap firing" % code)
        self.assertRegex(program, r"trap '[^']*kill_tagged[^']*' EXIT")
        self.assertRegex(program, r"trap '[^']*kill_tagged[^']*' TERM")
        self.assertIn("-Dmapreduce.job.tags=${TAG}", program)
        self.assertIn("spark.yarn.tags=${TAG}", program)

    # ----- Terraform-only rule -----
    def test_no_infrastructure_creating_command_is_ever_printed(self):
        r = self.run_
        printed = [l for l in r.lines() if l.startswith("DRY-RUN CMD") or l.startswith("CMD:")]
        for name in S.STEP_NAMES:
            printed += S.extract_body(r, name).splitlines()
            printed += S.installed_program(self.fx, "sc-step.sh").splitlines()  # the program every step executes
        banned = re.compile(r"create-cluster|run-job-flow|terminate-clusters|modify-instance-(groups|fleet)|set-termination-protection|"
                            r"put-auto-termination-policy|add-instance-(groups|fleet)|terraform\s+(apply|destroy|plan|init)|"
                            r"aws\s+emr\s+create|aws\s+ec2\s+run-instances|aws\s+ec2\s+terminate")
        for line in printed:
            self.assertIsNone(banned.search(line), "infrastructure command printed: %s" % line[:160])

    # ----- Spark step: decision 12-10 and class origin -----
    def test_spark_job_step_carries_the_decision_12_10_settings(self):
        """C1 form: the settings travel as SPARK_CONF=key=value parameters (read from scripts/config/spark-12-10.conf); the pinned
        runner turns each into a spark-submit --conf. The spark-submit argv itself is asserted by running the step."""
        args = S.step_args(self.run_, "spark-job")
        confs = S.step_params(args)["SPARK_CONF"]
        required = [
            "spark.yarn.jars=local:/opt/scholarchain-runtime/jars/*",
            "spark.yarn.populateHadoopClasspath=false",
            "spark.authenticate=true",
            "spark.network.crypto.enabled=true",
            "spark.network.crypto.authEngineVersion=1",
            "spark.io.encryption.enabled=true",
            "spark.dynamicAllocation.enabled=true",
            "spark.dynamicAllocation.shuffleTracking.enabled=true",
            "spark.shuffle.service.enabled=false",
        ]
        for prop in required:
            self.assertIn(prop, confs, "decision 12-10 property missing from the step parameters: " + prop)
        codec = [c for c in confs if c.startswith("spark.hadoop.io.compression.codecs=")]
        self.assertEqual(len(codec), 1, "the codec override is missing")
        self.assertNotIn("lzo", codec[0].lower(), "the codec list must not name LZO codecs")
        self.assertFalse([c for c in confs if c.startswith("spark.authenticate.secret")], "no Spark secret may be set")
        self.assertFalse([c for c in confs if "JAVA_HOME" in c], "JAVA_HOME is resolved at run time, never configured here")
        params = S.step_params(args)
        self.assertEqual(params["JAVA_HOME_FILE"], ["/opt/scholarchain-spike/java-home"])
        self.assertNotRegex(" ".join(args[6:]), r"JAVA_HOME=/usr/lib/jvm|JAVA_HOME=/opt/(?!scholarchain)")
        program = S.installed_program(self.fx, "sc-step.sh")
        self.assertIn("--master yarn --deploy-mode cluster", program)
        self.assertIn("spark.yarn.appMasterEnv.JAVA_HOME=${JAVA_HOME}", program)
        self.assertIn("spark.executorEnv.JAVA_HOME=${JAVA_HOME}", program)

    def test_class_origin_check_runs_before_the_spark_job_both_as_a_step_and_inside_the_job_body(self):
        r = self.run_
        order = [s for s in r.steps() if s.startswith("step-")]
        self.assertLess(order.index("step-spark-class-origin"), order.index("step-spark-job"))
        verifier_sha = S.sha256_file(self.fx.stepbin / "sc-class-origin-verify.py")
        probe = S.step_params(S.step_args(r, "spark-class-origin"))
        job = S.step_params(S.step_args(r, "spark-job"))
        for params in (probe, job):
            self.assertEqual(params["CLASS_ORIGIN_PY_SHA"], [verifier_sha], "both steps verify with the pinned verifier program")
            self.assertEqual(params["EXPECTED_SPARK_VERSION"], ["3.5.4"])
            self.assertEqual(params["EXPECTED_SCALA_VERSION"], ["2.13.14"])
        program = S.installed_program(self.fx, "sc-step.sh")
        self.assertIn("Phase12Readiness", program)
        self.assertIn("distributed", program)
        class_origin_body = program[program.index("body_spark_class_origin() {"):program.index("body_spark_job() {")]
        self.assertIn('--master yarn', program)
        self.assertLess(class_origin_body.index("build_spark_cmd"), class_origin_body.index("verify_class_origin"))
        job_body = program[program.index("body_spark_job() {"):program.index("body_copy_out() {")]
        self.assertLess(job_body.index("verify_class_origin"), job_body.index('build_spark_cmd "${SPARK_MAIN}"'),
                        "the class-origin check must precede the job's spark-submit")
        self.assertIn("scala3-library", S.installed_program(self.fx, "sc-class-origin-verify.py"))
        self.assertIn("CLASS-ORIGIN-FAILED", S.installed_program(self.fx, "sc-class-origin-verify.py"))

    def test_hadoop_and_er_step_forms(self):
        r = self.run_
        hadoop = S.step_params(S.step_args(r, "hadoop-prep"))
        for source, info in S.DATASETS.items():
            self.assertEqual(hadoop[source.upper() + "_SNAPSHOT"], [info["snapshot"]])
            self.assertEqual(hadoop[source.upper() + "_RETRIEVAL"], [info["retrieval"]])
        self.assertEqual(hadoop["CEILINGS"], ["12000 8 256 4096 64 8388608 8388608"])
        program = S.installed_program(self.fx, "sc-step.sh")
        for token in ("HadoopPrepMain", "--once", "--execution-mode cluster", '--run-id "${RUN_ID}"', "file://"):
            self.assertIn(token, program)
        er = S.step_params(S.step_args(r, "entity-resolution"))
        self.assertEqual(er["JAVA_HOME_FILE"], ["/opt/scholarchain-spike/java-home"])
        for token in ("Phase5Main", "resolve", "--llm-mode disabled"):
            self.assertIn(token, program)
        self.assertNotRegex(" ".join(S.step_args(r, "entity-resolution")[6:]) + program, r"/usr/lib/jvm|java-17-|jdk-17",
                            "Java 17 must be resolved at run time, never hard-coded")
        stage_in = S.step_params(S.step_args(r, "stage-in"))
        self.assertEqual(stage_in["INPUT_PREFIX"], ["s3://inbucket/data/in/"])
        copy_out = S.step_params(S.step_args(r, "copy-out"))
        self.assertEqual(copy_out["OUTPUT_PREFIX"], ["s3://outbucket/data/out/bp-test-run-1"])
        self.assertIn("aws s3 cp", program)
        self.assertIn("sha256", program)

    def test_dry_run_prints_dataset_snapshots_run_id_yarn_tag_and_outputs(self):
        r = self.run_
        for source, info in S.DATASETS.items():
            self.assertIn("PLAN: dataset %s: snapshot=%s retrieval=%s" % (source, info["snapshot"], info["retrieval"]), r.out)
        self.assertIn("PLAN: run-id: bp-test-run-1", r.out)
        self.assertIn("YARN-TAG: bp-test-run-1", r.out)
        self.assertIn("PLAN: output-prefix: s3://outbucket/data/out/bp-test-run-1/", r.out)
        self.assertIn("PLAN: region: us-east-2", r.out)

    def test_dry_run_prints_every_approval_line_for_the_human(self):
        r = self.run_
        keys = [l.split("=", 1)[0].split(": ", 1)[1] for l in r.grep(r"^APPROVAL-LINE: ")]
        self.assertEqual(sorted(keys), sorted([
            "APPROVED_ACTION", "APPROVED_COMMIT", "APPROVED_ACCOUNT_SHA256", "APPROVED_REGION", "APPROVED_CLUSTER_ID",
            "APPROVED_RUN_CONFIG_SHA256", "APPROVED_BUDGET_USD", "APPROVED_MAX_CAPACITY", "APPROVED_MAX_RUNTIME_MINUTES",
            "APPROVED_TEARDOWN", "APPROVED_PRESPEND_SHA256"]))
        self.assertIn("APPROVAL-LINE: APPROVED_COMMIT=" + self.fx.head(), r.out)
        self.assertIn("APPROVAL-LINE: APPROVED_MAX_CAPACITY=2", r.out)

    # ----- run configuration hash -----
    def test_run_config_hash_ignores_run_id_but_covers_what_decides_cost_and_behaviour(self):
        base = self.fx.run_config_sha(self.run_)
        self.assertRegex(base, r"^[0-9a-f]{64}$")
        self.assertEqual(base, self.fx.run_config_sha(self.fx.dry(run_id="bp-another-run")), "the run id must not be part of the approved hash")
        changed = {
            "core count": dict(core_count=2),
            "runtime": dict(max_runtime_minutes=61),
            "budget": dict(budget_usd="2.5"),
            "region": dict(region="us-west-2"),
            "output prefix": dict(output_prefix="s3://outbucket/data/other"),
            "input prefix": dict(input_prefix="s3://inbucket/data/other"),
            "artifact hash": dict(artifact_hashes={"job-jar": "b" * 64}),
            "instance type": dict(instance_type="m5.2xlarge", budget_usd=3),
        }
        seen = {base}
        for label, kw in changed.items():
            with self.subTest(change=label):
                run = self.fx.dry(**kw)
                self.assertEqual(run.rc, 0, run.describe())
                digest = self.fx.run_config_sha(run)
                self.assertNotIn(digest, seen, "changing the %s did not change the approved run configuration hash" % label)
                seen.add(digest)
        edited = S.Fixture(self)
        (edited.repo / "inputs/datasets.json").write_text(
            (edited.repo / "inputs/datasets.json").read_text().replace("dblp-2026-01", "dblp-2026-02"))
        self.assertNotEqual(base, edited.run_config_sha(edited.dry()), "dataset snapshots must be part of the run configuration")

    def test_dry_run_is_deterministic_apart_from_timestamps(self):
        a = self.fx.dry()
        b = self.fx.dry()
        strip = lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("["))
        self.assertEqual(strip(a.out), strip(b.out))


if __name__ == "__main__":
    unittest.main()

"""Phase 15 P6 local step-chain harness: feature tests for the node-tool stand-ins and the driver (offline; no AWS, no JVM).

Run: python3 -I -m unittest discover -s scripts/tests -p 'test_p6_local_chain.py' -v
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(TESTS))
LIB = os.path.join(REPO, "scripts", "lib")
BIN = os.path.join(REPO, "scripts", "p6local", "bin")
sys.path.insert(0, LIB)
import p6_local  # noqa: E402
import p6_local_chain  # noqa: E402

# The hadoop copy-out filter table of scripts/emr/sc-step.sh (copyout_rules hadoop), in order.
HADOOP_FILTERS = [("exclude", "intermediate/*"), ("exclude", "*/intermediate/*"), ("exclude", "export/*"), ("exclude", "*/export/*"),
                  ("include", "export/*/reject/*"), ("include", "*/export/*/reject/*")]


def write(path, data="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(data)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class Tool:
    def __init__(self, test):
        self.dir = tempfile.mkdtemp()
        test.addCleanup(lambda: subprocess.run(["rm", "-rf", self.dir]))
        self.s3 = os.path.join(self.dir, "s3")
        os.makedirs(self.s3)
        self.log = os.path.join(self.dir, "calls.jsonl")

    def env(self, **extra):
        env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin:" + os.path.dirname(sys.executable), "P6_S3_ROOT": self.s3, "P6_SHIM_LOG": self.log}
        env.update(extra)
        return env

    def run(self, tool, *argv, **extra):
        return subprocess.run([os.path.join(BIN, tool)] + list(argv), env=self.env(**extra), capture_output=True, text=True)


class AwsStandInTests(unittest.TestCase):
    def setUp(self):
        self.t = Tool(self)

    def test_every_non_s3_command_is_refused_with_97(self):
        for argv in (["sts", "get-caller-identity"], ["emr", "add-steps", "--cluster-id", "j-X"], ["s3api", "list-buckets"], ["s3", "rm", "s3://b-b/k"]):
            result = self.t.run("aws", *argv)
            self.assertEqual(result.returncode, 97, argv)
            self.assertIn("P6-LOCAL-AWS-REFUSED", result.stderr)

    def test_without_the_stand_in_root_nothing_is_served(self):
        result = self.t.run("aws", "s3", "ls", "s3://bkt/x/", "--recursive", "--summarize", P6_S3_ROOT="")
        self.assertEqual(result.returncode, 97)

    def test_a_dot_dot_key_is_refused(self):
        result = self.t.run("aws", "s3", "cp", "s3://bkt/a/../../etc/", os.path.join(self.t.dir, "o") + "/", "--recursive")
        self.assertEqual(result.returncode, 97)

    def test_stage_in_listing_and_recursive_download(self):
        write(os.path.join(self.t.s3, "bkt", "emr", "p", "input", "size-100", "datasets", "samples", "dblp", "a.xml"), "12345")
        write(os.path.join(self.t.s3, "bkt", "emr", "p", "input", "size-1000", "other"), "zz")  # same string prefix without the slash
        ls = self.t.run("aws", "s3", "ls", "s3://bkt/emr/p/input/size-100/", "--recursive", "--summarize", "--region", "us-east-2")
        self.assertEqual(ls.returncode, 0, ls.stderr)
        self.assertIn("Total Size: 5", ls.stdout)
        self.assertEqual(subprocess.run(["awk", "/Total Size:/{print $3}"], input=ls.stdout, capture_output=True, text=True).stdout.strip(), "5")
        dest = os.path.join(self.t.dir, "inputs")
        cp = self.t.run("aws", "s3", "cp", "s3://bkt/emr/p/input/size-100/", dest + "/", "--recursive", "--region", "us-east-2", "--only-show-errors")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(read(os.path.join(dest, "datasets", "samples", "dblp", "a.xml")), "12345")
        self.assertFalse(os.path.exists(os.path.join(dest, "other")))

    def test_copy_out_applies_the_awscli_filters_last_match_wins(self):
        src = os.path.join(self.t.dir, "run", "hadoop")
        layout = {"r1/_SCHOLARCHAIN_COMPLETE": True, "r1/counter-summary.json": True, "r1/export/snapshot=d/run=r1/reject/part-r-00000": True,
                  "r1/export/snapshot=d/run=r1/work/part-r-00000": False, "r1/intermediate/j06/part-r-00000": False,
                  "r1/intermediate/j01/reject/part": False, "r1/stats/j05.txt": True}
        for rel in layout:
            write(os.path.join(src, rel))
        args = []
        for action, pattern in HADOOP_FILTERS:
            args += ["--" + action, pattern]
        result = self.t.run("aws", "s3", "cp", src + "/", "s3://bkt/pipeline/p/15a/size-100/run1/hadoop/", "--recursive", *args,
                            "--no-follow-symlinks", "--region", "us-east-2", "--only-show-errors")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = os.path.join(self.t.s3, "bkt", "pipeline", "p", "15a", "size-100", "run1", "hadoop")
        copied = sorted(os.path.relpath(f, out) for f in p6_local.walk_files(out, False))
        self.assertEqual(copied, sorted(k for k, keep in layout.items() if keep))

    def test_links_are_not_followed_or_copied_with_no_follow_symlinks(self):
        src = os.path.join(self.t.dir, "run", "spark")
        write(os.path.join(src, "real.parquet"))
        write(os.path.join(self.t.dir, "outside", "secret.txt"))
        os.symlink(os.path.join(self.t.dir, "outside", "secret.txt"), os.path.join(src, "link.txt"))
        os.symlink(os.path.join(self.t.dir, "outside"), os.path.join(src, "linkdir"))
        result = self.t.run("aws", "s3", "cp", src + "/", "s3://bkt/out/spark/", "--recursive", "--no-follow-symlinks")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = os.path.join(self.t.s3, "bkt", "out", "spark")
        self.assertEqual([os.path.relpath(f, out) for f in p6_local.walk_files(out, False)], ["real.parquet"])

    def test_single_file_upload_and_every_call_is_logged(self):
        write(os.path.join(self.t.dir, "m.sha256"), "abc")
        result = self.t.run("aws", "s3", "cp", os.path.join(self.t.dir, "m.sha256"), "s3://bkt/out/run1/copyout-manifest.sha256", "--region", "us-east-2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(read(os.path.join(self.t.s3, "bkt", "out", "run1", "copyout-manifest.sha256")), "abc")
        calls = [json.loads(line) for line in read(self.t.log).splitlines()]
        self.assertEqual(calls[-1]["tool"], "aws")
        self.assertEqual(calls[-1]["argv"][:2], ["s3", "cp"])


class HadoopAndYarnStandInTests(unittest.TestCase):
    def setUp(self):
        self.t = Tool(self)

    def test_only_the_execution_mode_pair_is_substituted(self):
        argv = ["jar", "/w/job.jar", "M", "-Dmapreduce.job.tags=t", "-libjars", "/w/b.jar", "--once", "--execution-mode", "cluster",
                "--run-id", "cluster", "--dblp", "file:///x"]
        command, subs = p6_local.hadoop_jar_command(argv, "/j/bin/java", "/w/b.jar", "/c/h.jar", ["-Xmx4g"])
        self.assertEqual(command[:6], ["/j/bin/java", "-Xmx4g", "-cp", "/w/b.jar:/c/h.jar", "org.apache.hadoop.util.RunJar", "/w/job.jar"])
        self.assertEqual(command[6:], ["M", "-Dmapreduce.job.tags=t", "-libjars", "/w/b.jar", "--once", "--execution-mode", "local",
                                       "--run-id", "cluster", "--dblp", "file:///x"])
        self.assertEqual(len(subs), 1)

    def test_the_run_id_workaround_is_opt_in_and_keeps_a_v4_id(self):
        argv = ["jar", "/w/job.jar", "M", "--once", "--run-id", "p6-S-20261116T155022Z", "--execution-mode", "cluster",
                "--output-root", "file:///mnt/runs/r/hadoop"]
        plain, _ = p6_local.hadoop_jar_command(argv, "/j", "", "/c", [])
        self.assertIn("p6-S-20261116T155022Z", plain, "without the opt-in the defect is reproduced, not hidden")
        self.assertIn("file:///mnt/runs/r/hadoop", plain)
        dropped, subs = p6_local.hadoop_jar_command(argv, "/j", "", "/c", [], drop_non_v4_run_id=True)
        self.assertNotIn("--run-id", dropped)
        self.assertEqual(dropped[dropped.index("--output-root") + 1], "/mnt/runs/r/hadoop")
        self.assertEqual(len([s for s in subs if s.startswith("WORKAROUND")]), 2)
        v4 = ["jar", "/w/job.jar", "M", "--run-id", "run:0f8fad5b-d9cb-469f-a165-70867728950e"]
        kept, _ = p6_local.hadoop_jar_command(v4, "/j", "", "/c", [], drop_non_v4_run_id=True)
        self.assertIn("run:0f8fad5b-d9cb-469f-a165-70867728950e", kept)

    def test_hadoop_jar_runs_java_with_the_substitution(self):
        java_home = os.path.join(self.t.dir, "jdk")
        write(os.path.join(java_home, "bin", "java"), "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$P6_TEST_OUT\"\nexit 7\n")
        os.chmod(os.path.join(java_home, "bin", "java"), 0o755)
        out = os.path.join(self.t.dir, "argv.txt")
        result = self.t.run("hadoop", "jar", "/w/job.jar", "M", "--execution-mode", "cluster", P6_JAVA_HOME=java_home,
                            P6_HADOOP_CLIENT_CLASSPATH="/c/h.jar", HADOOP_CLASSPATH="/w/b.jar", P6_TEST_OUT=out)
        self.assertEqual(result.returncode, 7)
        self.assertIn("P6-SUBSTITUTION hadoop", result.stderr)
        self.assertEqual(read(out).split("\n")[:7], ["-cp", "/w/b.jar:/c/h.jar", "org.apache.hadoop.util.RunJar", "/w/job.jar", "M", "--execution-mode", "local"])

    def test_copy_to_local_reads_the_stand_in_and_other_verbs_are_refused(self):
        write(os.path.join(self.t.s3, "bkt", "emr", "p", "jars", "x.jar"), "jar")
        dest = os.path.join(self.t.dir, "x.jar")
        self.assertEqual(self.t.run("hadoop", "fs", "-copyToLocal", "s3://bkt/emr/p/jars/x.jar", dest).returncode, 0)
        self.assertEqual(read(dest), "jar")
        self.assertEqual(self.t.run("hadoop", "fs", "-copyToLocal", "s3://bkt/emr/p/jars/missing.jar", dest + "2").returncode, 1)
        self.assertEqual(self.t.run("hadoop", "fs", "-rm", "-r", "s3://bkt/x").returncode, 97)

    def test_yarn_lists_no_application_and_refuses_other_commands(self):
        listing = self.t.run("yarn", "application", "-list", "-appStates", "RUNNING", "-appTags", "t")
        self.assertEqual(listing.returncode, 0)
        self.assertNotIn("application_", listing.stdout)
        self.assertEqual(self.t.run("yarn", "application", "-kill", "application_1").returncode, 0)
        self.assertEqual(self.t.run("yarn", "node", "-list").returncode, 97)


class TimeoutStandInTests(unittest.TestCase):
    def setUp(self):
        self.t = Tool(self)

    def test_the_exit_code_passes_through(self):
        self.assertEqual(self.t.run("timeout", "--kill-after=1", "10", "sh", "-c", "exit 3").returncode, 3)

    def test_a_timeout_returns_124(self):
        start = time.monotonic()
        self.assertEqual(self.t.run("timeout", "--kill-after=2", "1", "sleep", "30").returncode, 124)
        self.assertLess(time.monotonic() - start, 10)

    def test_a_child_that_ignores_term_is_killed_and_returns_137(self):
        result = self.t.run("timeout", "--kill-after=1", "1", "sh", "-c", "trap '' TERM; sleep 30")
        self.assertEqual(result.returncode, 137)

    def test_bad_usage_is_125(self):
        self.assertEqual(self.t.run("timeout", "--foreground", "1", "true").returncode, 125)


EMR_SUBMIT = ["--master", "yarn", "--deploy-mode", "cluster", "--name", "scholarchain-bounded-r", "--class", "M",
              "--conf", "spark.yarn.tags=r", "--conf", "spark.dynamicAllocation.maxExecutors=2", "--conf", "spark.executor.cores=1",
              "--conf", "spark.executor.memory=3g", "--conf", "spark.authenticate=true", "local:/opt/job.jar", "/run/config/spark-config.json"]


class SparkSubmitStandInTests(unittest.TestCase):
    def test_yarn_cluster_becomes_local_cluster_with_the_executor_shape(self):
        args, subs, auth, dist = p6_local.spark_submit_translate(EMR_SUBMIT)
        self.assertEqual(args[:2], ["--master", "local-cluster[2,1,3072]"])
        self.assertNotIn("--deploy-mode", args)
        self.assertEqual(args[-2:], ["local:/opt/job.jar", "/run/config/spark-config.json"])
        self.assertIn("spark.authenticate=true", args)
        self.assertTrue(auth)
        self.assertEqual(dist, "/opt/job.jar", "the node-local job jar is used in place, after the runtime jars, as on YARN")
        self.assertNotIn("spark.executor.extraClassPath", " ".join(args))
        self.assertEqual(len(subs), 3)

    def test_other_forms_are_refused(self):
        with self.assertRaises(ValueError):
            p6_local.spark_submit_translate(["--master", "local[2]", "--deploy-mode", "cluster", "x.jar"])
        with self.assertRaises(ValueError):
            p6_local.spark_submit_translate(["--master", "yarn", "--deploy-mode", "cluster", "--jars", "a.jar", "x.jar"])
        with self.assertRaises(ValueError):
            p6_local.spark_submit_translate(["--master", "yarn", "--deploy-mode", "cluster", "--conf", "spark.executor.cores=1", "x.jar"])

    def test_the_secret_file_is_private_while_the_job_runs_and_removed_after(self):
        t = Tool(self)
        bindir = os.path.join(t.dir, "runtime", "bin")
        os.makedirs(bindir)
        os.symlink(os.path.join(BIN, "spark-submit"), os.path.join(bindir, "spark-submit"))
        out = os.path.join(t.dir, "seen.json")
        write(os.path.join(bindir, "spark-submit.real"),
              "props=\"$2\"\nmode=$(stat -f %Lp \"$props\" 2>/dev/null || stat -c %a \"$props\")\n"
              "printf '{\"first\":\"%s\",\"props\":\"%s\",\"mode\":\"%s\",\"local\":\"%s\",\"master\":\"%s\",\"dist\":\"%s\"}' \"$1\" \"$props\" \"$mode\" \"$SPARK_LOCAL_DIRS\" \"$4\" \"$SPARK_DIST_CLASSPATH\" > \"$P6_TEST_OUT\"\n")
        result = subprocess.run([os.path.join(bindir, "spark-submit")] + EMR_SUBMIT, capture_output=True, text=True,
                                env=t.env(P6_TEST_OUT=out, P6_SPARK_LOCAL_DIRS="/p6/spark-local", TMPDIR=t.dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        seen = json.loads(read(out))
        self.assertEqual(seen["first"], "--properties-file")
        self.assertEqual(seen["mode"], "600")
        self.assertEqual(seen["local"], "/p6/spark-local")
        self.assertEqual(seen["master"], "local-cluster[2,1,3072]")
        self.assertEqual(seen["dist"], "/opt/job.jar")
        self.assertFalse(os.path.exists(seen["props"]), "the throwaway secret file is deleted after the job")
        self.assertNotIn("spark.authenticate.secret", result.stderr + result.stdout)


class DriverTests(unittest.TestCase):
    def step(self, sha, extra=()):
        return {"name": "spark-job", "args": ["bash", "-c", "launcher", "sc-step", sha, "spark-job", "STEP_SECONDS=2160", "MNT=/mnt/scholarchain",
                                              "RUN_ID=r", "JAVA_HOME_FILE=/opt/scholarchain-spike/java-home", "RUNTIME_DIR=/opt/scholarchain-runtime",
                                              "JOB_JAR=/opt/scholarchain-runtime/application/scholarchain-job.jar", "JOB_JAR_SHA=" + "b" * 64,
                                              "SPARK_CONF=spark.executor.memory=3g"] + list(extra)}

    def test_only_the_four_node_local_values_are_replaced(self):
        overrides = {"MNT": "/l/mnt", "RUNTIME_DIR": "/l/rt", "JOB_JAR": "/l/rt/application/scholarchain-job.jar", "JAVA_HOME_FILE": "/l/jh"}
        params, replaced = p6_local_chain.step_params(self.step("a" * 64), "a" * 64, overrides)
        self.assertEqual(sorted(replaced), sorted(p6_local_chain.NODE_LOCAL_KEYS))
        self.assertEqual(params, ["STEP_SECONDS=2160", "MNT=/l/mnt", "RUN_ID=r", "JAVA_HOME_FILE=/l/jh", "RUNTIME_DIR=/l/rt",
                                  "JOB_JAR=/l/rt/application/scholarchain-job.jar", "JOB_JAR_SHA=" + "b" * 64, "SPARK_CONF=spark.executor.memory=3g"])

    def test_a_diagnostic_er_config_can_never_produce_a_retained_export(self):
        root = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", root]))
        rc = p6_local_chain.main(["run", "--size", "S", "--root", root, "--retain", "--er-config", os.path.join(root, "er.json")])
        self.assertEqual(rc, 3)
        self.assertEqual(os.listdir(root), [], "refused before anything was created")

    def test_a_drifted_step_runner_pin_is_refused(self):
        with self.assertRaises(p6_local_chain.Refused):
            p6_local_chain.step_params(self.step("a" * 64), "c" * 64, {})

    def test_the_real_plan_for_s_has_the_six_steps_and_the_pinned_runner(self):
        work = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", work]))
        os.makedirs(os.path.join(work, "evidence"))
        conf = p6_local_chain.read_conf(os.path.join(REPO, "scripts", "config", "release.conf"))
        pricing = p6_local_chain.read_conf(os.path.join(REPO, conf["PIPELINE_PRICING_FILE"]))
        plan, rendered = p6_local_chain.build_plan("S", "p6-S-test-run", work, conf, pricing)
        self.assertEqual([s["name"] for s in plan["steps"]], list(p6_local_chain.STEP_ORDER))
        runner = p6_local.sha256_file(os.path.join(REPO, "scripts", "emr", "sc-step.sh"))
        weights = dict(item.split("=") for item in conf["PIPELINE_STEP_WEIGHTS"].split())
        total = int(rendered["budget"]["max_runtime_minutes"]) * 60
        for step in plan["steps"]:
            params, _ = p6_local_chain.step_params(step, runner, {})
            self.assertIn("STEP_SECONDS=%d" % (total * int(weights[step["name"]]) // 100), params)
        copy_out = dict(kv.split("=", 1) for kv in p6_local_chain.step_params(plan["steps"][5], runner, {})[0])
        self.assertEqual(copy_out["MAX_COPYOUT_BYTES"], conf["PIPELINE_MAX_COPYOUT_BYTES"])
        self.assertTrue(copy_out["OUTPUT_PREFIX"].startswith("s3://scholarchain-p6local-000000000000-artifacts/pipeline/run-p6local/15a/size-100/"))


class RetentionTests(unittest.TestCase):
    def test_sha256sums_are_relative_sorted_and_check_with_shasum(self):
        base = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", base]))
        for rel in ("spark/b/part-1.parquet", "spark/a=1/x.json", "spark/_SCHOLARCHAIN_SPARK_COMPLETE", "spark/load-manifests/s3.json"):
            write(os.path.join(base, rel), rel)
        sums = p6_local.sha256sums(os.path.join(base, "spark"), prefix="spark/")
        paths = [line.split("  ", 1)[1] for line in sums.splitlines()]
        self.assertEqual(paths, sorted(paths))
        self.assertTrue(all(p.startswith("spark/") for p in paths))
        write(os.path.join(base, "SHA256SUMS"), sums)
        self.assertEqual(subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=base, capture_output=True).returncode, 0)
        write(os.path.join(base, "spark/b/part-1.parquet"), "changed")
        self.assertNotEqual(subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=base, capture_output=True).returncode, 0)

    def test_seal_refuses_a_render_report_of_another_run(self):
        base = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", base]))
        write(os.path.join(base, "spark", "x"), "x")
        write(os.path.join(base, "SHA256SUMS"), p6_local.sha256sums(os.path.join(base, "spark"), prefix="spark/"))
        write(os.path.join(base, "provenance.json"), json.dumps({"p6RunId": "run:a", "sha256sumsSha256": p6_local.sha256_file(os.path.join(base, "SHA256SUMS"))}))
        report = os.path.join(base, "report.json")
        write(report, json.dumps({"sourceRunId": "run:b", "mode": "render-only", "embeddingCalls": 0}))
        self.assertEqual(p6_local_chain.main(["seal", "--retention-dir", base, "--render-report", report]), 3)
        write(report, json.dumps({"sourceRunId": "run:a", "mode": "render-only", "embeddingCalls": 0, "selectedDocuments": 3}))
        self.assertEqual(p6_local_chain.main(["seal", "--retention-dir", base, "--render-report", report]), 0)
        self.assertEqual(json.loads(read(os.path.join(base, "provenance.json")))["renderReport"]["sourceRunId"], "run:a")


if __name__ == "__main__":
    unittest.main()

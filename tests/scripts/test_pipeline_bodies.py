"""Independent tests that RUN the printed EMR step bodies locally against fake binaries (Subphase 13B, test-engineer).

Each body is taken verbatim from a dry run's STEP-BODY-BEGIN/END block and executed with bash -c, as the cluster's
command-runner.jar would, but on this machine with: a test-only config (SCHOLARCHAIN_CONFIG_FILE) that points the EFS mount,
runtime directory, job jar and Java-home file at temp directories, the body's documented SC_PROC_MOUNTS seam, and fake
`timeout`, `yarn`, `hadoop`, `spark-submit`, `java`, `aws` and `sha256sum` binaries that log their argv.

Plan items: carried 12D item 1 (the hard runtime cap kills the YARN application by the run tag, not only the client),
section 7.2 (class-origin check before the real Spark job, fail closed, Java 17 resolved at run time), README step table
(stage-in mount and size checks, copy-out size ceiling and sha256 manifest).
"""
import hashlib
import json
import os
import signal
import subprocess
import time
import unittest
from pathlib import Path

import sc_support as S

TAG = "bp-test-run-1"
APPS = "application_1700000000000_0001,application_1700000000000_0002"


class Harness:
    def __init__(self, test, patch=None, **cfg_over):
        self.test = test
        self.fx = S.Fixture(test, patch=patch)
        a = self.fx.aux
        self.mnt = a / "mnt"
        self.runtime = a / "runtime"
        self.jdk = a / "jdk17"
        self.javahome = a / "java-home"
        self.mounts = a / "proc-mounts"
        self.jobjar = self.runtime / "application" / "scholarchain-job.jar"
        for d in (self.mnt, self.runtime / "bin", self.runtime / "application", self.runtime / "jars", self.jdk / "bin"):
            d.mkdir(parents=True, exist_ok=True)
        S.write_fake(self.jdk / "bin" / "java", "java")
        S.write_fake(self.runtime / "bin" / "spark-submit", "spark-submit")
        self.javahome.write_text(str(self.jdk) + "\n")
        self.mounts.write_text("fs-123.efs.us-east-2.amazonaws.com:/ %s nfs4 rw 0 0\n" % self.mnt)
        self.jobjar.write_bytes(b"packaged job jar bytes")
        self.job_sha = S.sha256_file(self.jobjar)
        self.hadoop_jar = a / "fake-s3" / "hadoop-submit.jar"
        for name, data in (("hadoop-submit.jar", b"hadoop submit jar"), ("hadoop-libs.jar", b"hadoop libs bundle")):
            (self.fx.s3dir / name).write_bytes(data)
        (self.fx.s3dir / "spark-template.json").write_text(json.dumps({
            "hadoopRunRoot": "x", "entityResolutionRunRoot": "x", "outputRoot": "x", "checkpointDirectory": "x", "other": 1}))
        self.cfg = dict(PIPELINE_EFS_MOUNT=str(self.mnt), PIPELINE_RUNTIME_DIR=str(self.runtime), PIPELINE_JOB_JAR_PATH=str(self.jobjar),
                        PIPELINE_JAVA_HOME_FILE=str(self.javahome), PIPELINE_POLL_SECONDS="0")
        self.cfg.update(cfg_over)
        self.env_cfg = {"SCHOLARCHAIN_CONFIG_FILE": str(self.fx.test_config(**self.cfg))}
        hashes = {
            "hadoop-submit-jar": S.sha256_text("hadoop submit jar"), "hadoop-libjars": S.sha256_text("hadoop libs bundle"),
            "job-jar": self.job_sha, "spark-config-template": S.sha256_file(self.fx.s3dir / "spark-template.json"),
        }
        self.dry = self.fx.dry(extra_env=self.env_cfg, artifact_hashes=hashes)
        test.assertEqual(self.dry.rc, 0, self.dry.describe())
        self.run_root = self.mnt / "runs" / TAG

    def body_env(self, **extra):
        env = {
            "PATH": "%s:%s" % (self.fx.bin, os.environ.get("PATH", "/usr/bin:/bin")),
            "HOME": str(self.fx.home), "TMPDIR": str(self.fx.tmp), "SC_PROC_MOUNTS": str(self.mounts),
            "SC_FAKE_LOG": str(self.fx.log), "SC_FAKE_SCENARIO": str(self.fx.scenario_path), "SC_FAKE_STATE": str(self.fx.state_path),
            "SC_FAKE_S3DIR": str(self.fx.s3dir), "SC_FAKE_YARN_TAG": TAG, "SC_FAKE_YARN_APPS": APPS,
        }
        env.update(extra)
        return env

    def run_body(self, name, timeout=120, **extra):
        self.fx.log.write_text("")
        done = subprocess.run(["bash", "-c", S.extract_body(self.dry, name)], env=self.body_env(**extra), cwd=str(self.fx.repo),
                              capture_output=True, text=True, timeout=timeout)
        return done, self.fx.calls()

    # probe document in the shape the Phase 12 readiness job reports (README: driver and executor, Java 17, pinned
    # Spark/Scala versions, runtime-jar origins, scala3-library from the packaged job jar, identical hashes)
    def libs(self, spark="3.5.4", scala="2.13.14", origin_dir=None, s3_origin=None, s3_sha=None, class_sha="c1"):
        jars = origin_dir or str(self.runtime / "jars")
        return [
            {"component": "spark", "runtimeVersion": spark, "origin": "%s/spark-core_2.13-%s.jar" % (jars, spark), "classSha256": class_sha, "codeSourceSha256": "s1"},
            {"component": "scala-library", "runtimeVersion": scala, "origin": "%s/scala-library-%s.jar" % (jars, scala), "classSha256": "c2", "codeSourceSha256": "s2"},
            {"component": "scala-reflect", "runtimeVersion": scala, "origin": "%s/scala-reflect-%s.jar" % (jars, scala), "classSha256": "c3", "codeSourceSha256": "s3"},
            {"component": "scala3-library", "runtimeVersion": "3.3.5", "origin": s3_origin or str(self.jobjar), "classSha256": "c4",
             "codeSourceSha256": s3_sha or self.job_sha},
        ]

    def write_probe(self, executor=None, driver=None, **top):
        doc = {"schemaVersion": "scholarchain.phase12-readiness.v1", "stage": "probe", "externalExecutorVerified": True,
               "distributedRequired": True,
               "driver": {"javaVersion": "17.0.12", "libraries": self.libs()},
               "taskProcesses": [{"executorId": "1", "javaVersion": "17.0.12", "libraries": self.libs()}]}
        if driver:
            doc["driver"].update(driver)
        if executor is not None:
            doc["taskProcesses"] = [executor]
        doc.update(top)
        path = self.run_root / "results" / "class-origin.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc))
        return doc

    def stage_for_spark_job(self):
        marker = self.run_root / "hadoop" / "run-1" / "_SCHOLARCHAIN_COMPLETE"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("")
        (self.run_root / "er" / "run").mkdir(parents=True, exist_ok=True)
        self.write_probe()


def argv_of(calls, tool):
    return [c["argv"] for c in calls if c["tool"] == tool]


def is_step_wrapper(argv):
    """The B1 step-level wrapper: `timeout --kill-after=N SECONDS bash <step bin>/sc-step.sh __body STEP KEY=VALUE...`."""
    return len(argv) >= 5 and argv[0].startswith("--kill-after=") and argv[2] == "bash" and argv[3].endswith("/sc-step.sh") and argv[4] == "__body"


def step_wrappers(calls):
    return [a for a in argv_of(calls, "timeout") if is_step_wrapper(a)]


def inner_timeouts(calls):
    """Every other `timeout` call: the client wrapper (`run_bounded`) inside a YARN-submitting body."""
    return [a for a in argv_of(calls, "timeout") if not is_step_wrapper(a)]


class YarnKillByTag(unittest.TestCase):
    """Carried item 1: when the runtime cap fires, the body kills the YARN application tagged with the run id."""

    def check_kill(self, done, calls, expect_rc):
        self.assertEqual(done.returncode, expect_rc, done.stdout + done.stderr)
        yarn = argv_of(calls, "yarn")
        lists = [i for i, a in enumerate(yarn) if a[:2] == ["application", "-list"]]
        kills = [(i, a[2]) for i, a in enumerate(yarn) if a[:2] == ["application", "-kill"]]
        self.assertTrue(lists, "no `yarn application -list` was issued: %s" % yarn)
        for i in lists:
            self.assertEqual(yarn[i][yarn[i].index("-appTags") + 1], TAG, "the application list must be filtered by the run id tag")
        killed = {app for _, app in kills}
        self.assertEqual(killed, set(APPS.split(",")), "every application carrying the run tag must be killed, and only those")
        self.assertLess(lists[0], kills[0][0], "the tagged applications must be listed before they are killed")

    def test_hadoop_prep_cap_exit_124_137_143_each_kills_the_tagged_applications(self):
        for code in (124, 137, 143):
            with self.subTest(timeout_exit=code):
                h = Harness(self)
                done, calls = h.run_body("hadoop-prep", SC_FAKE_TIMEOUT_MODE="exit:%d" % code)
                self.check_kill(done, calls, code)
                timeouts = inner_timeouts(calls)
                self.assertEqual(len(timeouts), 1)
                self.assertIn("HadoopPrepMain", " ".join(timeouts[0]))
                self.assertIn("-Dmapreduce.job.tags=%s" % TAG, timeouts[0])
                self.assertIn("720", timeouts[0], "the step timeout derived from the runtime cap must wrap the client")
                # B1: the whole body also runs under the step wrapper: 20% of 3600 s = 720 s, kill-after 60 s
                self.assertEqual([a[:3] for a in step_wrappers(calls)], [["--kill-after=60", "720", "bash"]])

    def test_spark_job_cap_kills_the_tagged_applications(self):
        h = Harness(self)
        h.stage_for_spark_job()
        done, calls = h.run_body("spark-job", SC_FAKE_TIMEOUT_MODE="exit:124")
        self.check_kill(done, calls, 124)
        wrapped = inner_timeouts(calls)[0]
        self.assertEqual([a[:3] for a in step_wrappers(calls)], [["--kill-after=60", "1440", "bash"]], "40% of 3600 s")
        self.assertTrue(any(a.endswith("/bin/spark-submit") for a in wrapped))
        self.assertIn("spark.yarn.tags=%s" % TAG, wrapped)

    def test_a_tag_that_matches_no_application_kills_nothing(self):
        h = Harness(self)
        done, calls = h.run_body("hadoop-prep", SC_FAKE_TIMEOUT_MODE="exit:124", SC_FAKE_YARN_TAG="some-other-run")
        self.assertEqual(done.returncode, 124, done.stdout + done.stderr)
        self.assertTrue([a for a in argv_of(calls, "yarn") if a[:2] == ["application", "-list"]])
        self.assertEqual([a for a in argv_of(calls, "yarn") if a[:2] == ["application", "-kill"]], [])

    def test_a_body_that_fails_for_another_reason_still_kills_tagged_applications_from_the_exit_trap(self):
        h = Harness(self)
        done, calls = h.run_body("hadoop-prep", SC_FAKE_HADOOP_JAR_RC="1")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        kills = [a for a in argv_of(calls, "yarn") if a[:2] == ["application", "-kill"]]
        self.assertEqual({a[2] for a in kills}, set(APPS.split(",")))

    def test_a_clean_body_runs_the_client_and_issues_no_kill_when_nothing_is_running(self):
        h = Harness(self)
        done, calls = h.run_body("hadoop-prep", SC_FAKE_YARN_APPS="")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(inner_timeouts(calls)), 1)
        self.assertEqual(len(step_wrappers(calls)), 1)
        self.assertTrue([a for a in argv_of(calls, "hadoop") if a[:1] == ["jar"]])
        self.assertEqual([a for a in argv_of(calls, "yarn") if a[:2] == ["application", "-kill"]], [])

    def test_hadoop_body_refuses_an_artifact_whose_sha256_differs_before_any_client_runs(self):
        h = Harness(self)
        (h.fx.s3dir / "hadoop-submit.jar").write_bytes(b"tampered jar")
        done, calls = h.run_body("hadoop-prep")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("sha256 mismatch", done.stderr)
        self.assertEqual([a for a in argv_of(calls, "hadoop") if a[:1] == ["jar"]], [])
        self.assertEqual(inner_timeouts(calls), [])

    def test_hadoop_body_repeats_the_phase4_ceiling_check_on_the_cluster(self):
        h = Harness(self)
        bad = dict(S.SAFE_PREP)
        bad["reducerCount"] = 9
        # the node-side copy of the config is what the body checks: change the file after the plan hashed it
        cfg = h.fx.repo / "inputs/prep.json"
        sha = S.sha256_file(cfg)
        cfg.write_text(json.dumps(bad))
        body = S.extract_body(h.dry, "hadoop-prep").replace(sha, S.sha256_file(cfg))
        h.fx.log.write_text("")
        done = subprocess.run(["bash", "-c", body], env=h.body_env(), cwd=str(h.fx.repo), capture_output=True, text=True, timeout=120)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("reducerCount 9 exceeds ceiling 8", done.stderr)
        self.assertEqual([a for a in argv_of(h.fx.calls(), "hadoop") if a[:1] == ["jar"]], [])


class StageInAndCopyOut(unittest.TestCase):
    def test_stage_in_refuses_a_directory_that_is_not_a_mount_point(self):
        h = Harness(self)
        h.mounts.write_text("tmpfs /somewhere/else tmpfs rw 0 0\n")
        done, calls = h.run_body("stage-in")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("not a mount point", done.stderr)
        self.assertEqual(argv_of(calls, "aws"), [])

    def test_stage_in_refuses_an_input_over_the_byte_ceiling_and_accepts_exactly_the_ceiling(self):
        h = Harness(self)
        h.fx.update_scenario(s3_total_size=268435457)
        done, calls = h.run_body("stage-in")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("exceeds", done.stderr)
        self.assertFalse([a for a in argv_of(calls, "aws") if a[:2] == ["s3", "cp"]], "nothing may be copied when the input is too large")
        h2 = Harness(self)
        h2.fx.update_scenario(s3_total_size=268435456)
        done, calls = h2.run_body("stage-in")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        copies = [a for a in argv_of(calls, "aws") if a[:2] == ["s3", "cp"]]
        self.assertEqual(len(copies), 1)
        self.assertIn("--recursive", copies[0])
        self.assertTrue(copies[0][2].startswith("s3://inbucket/data/in"))
        self.assertTrue(copies[0][3].startswith(str(h2.run_root)), "the input must land under the run directory on EFS")

    def test_stage_in_never_reuses_a_run_directory(self):
        h = Harness(self)
        h.run_root.mkdir(parents=True)
        done, calls = h.run_body("stage-in")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("already exists", done.stderr)
        self.assertEqual(argv_of(calls, "aws"), [])

    def test_copy_out_writes_a_sha256_manifest_and_copies_each_part_to_the_output_prefix(self):
        h = Harness(self)
        contents = {"hadoop/a.txt": b"hadoop output", "er/b.txt": b"er output", "spark/c.txt": b"spark output",
                    "results/d.txt": b"results", "config/e.json": b"{}"}
        for rel, data in contents.items():
            p = h.run_root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        done, calls = h.run_body("copy-out")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        manifest = (h.run_root / "copyout-manifest.sha256").read_text().splitlines()
        expected = sorted("%s  %s" % (hashlib.sha256(data).hexdigest(), rel) for rel, data in contents.items())
        self.assertEqual(sorted(manifest), expected)
        copies = [a for a in argv_of(calls, "aws") if a[:2] == ["s3", "cp"]]
        targets = sorted(a[3] for a in copies)
        self.assertEqual(targets, sorted(["s3://outbucket/data/out/%s/%s/" % (TAG, p) for p in ("hadoop", "er", "spark", "results", "config")]
                                         + ["s3://outbucket/data/out/%s/copyout-manifest.sha256" % TAG]))

    def test_copy_out_of_a_partial_run_lists_and_copies_only_the_parts_that_exist(self):
        """13C fix: a salvaged run may lack some of hadoop, er, spark, results, config; the manifest and the copies cover
        exactly the present parts and the step succeeds."""
        h = Harness(self)
        contents = {"results/d.txt": b"results", "config/e.json": b"{}"}
        for rel, data in contents.items():
            p = h.run_root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        done, calls = h.run_body("copy-out")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("STEP-FAIL", done.stderr)
        manifest = (h.run_root / "copyout-manifest.sha256").read_text().splitlines()
        self.assertEqual(sorted(manifest), sorted("%s  %s" % (hashlib.sha256(d).hexdigest(), r) for r, d in contents.items()))
        targets = sorted(a[3] for a in argv_of(calls, "aws") if a[:2] == ["s3", "cp"])
        self.assertEqual(targets, sorted(["s3://outbucket/data/out/%s/results/" % TAG, "s3://outbucket/data/out/%s/config/" % TAG,
                                          "s3://outbucket/data/out/%s/copyout-manifest.sha256" % TAG]))

    def test_copy_out_with_no_part_present_fails_with_an_explicit_marker_and_copies_nothing(self):
        h = Harness(self)
        h.run_root.mkdir(parents=True)
        done, calls = h.run_body("copy-out")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("STEP-FAIL copy-out: nothing to copy out", done.stderr)
        self.assertEqual([a for a in argv_of(calls, "aws") if a[:2] == ["s3", "cp"]], [])
        self.assertFalse((h.run_root / "copyout-manifest.sha256").exists())

    def test_copy_out_refuses_results_over_the_byte_ceiling(self):
        h = Harness(self, PIPELINE_MAX_COPYOUT_BYTES="2048")
        big = h.run_root / "results" / "big.bin"
        big.parent.mkdir(parents=True)
        big.write_bytes(os.urandom(64 * 1024))
        done, calls = h.run_body("copy-out")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("exceeds", done.stderr)
        self.assertEqual([a for a in argv_of(calls, "aws") if a[:2] == ["s3", "cp"]], [])

    def test_copy_out_never_overwrites_an_existing_manifest(self):
        h = Harness(self)
        (h.run_root / "results").mkdir(parents=True)
        (h.run_root / "results" / "r.txt").write_text("r")
        (h.run_root / "copyout-manifest.sha256").write_text("earlier\n")
        done, calls = h.run_body("copy-out")
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual((h.run_root / "copyout-manifest.sha256").read_text(), "earlier\n")


class SparkJobClassOriginGate(unittest.TestCase):
    """Plan 7.2: the real job never starts without a passing driver AND executor class-origin result; Java 17 is resolved."""

    def expect_blocked(self, h, needle=None):
        done, calls = h.run_body("spark-job")
        self.assertNotEqual(done.returncode, 0, "the spark job body must fail closed\n" + done.stdout + done.stderr)
        self.assertEqual(argv_of(calls, "spark-submit"), [], "spark-submit must not run after a failed class-origin gate")
        self.assertEqual(inner_timeouts(calls), [])
        if needle:
            self.assertIn(needle, done.stderr)
        return done

    def test_passing_probe_runs_spark_submit_once_with_decision_12_10_settings(self):
        h = Harness(self)
        h.stage_for_spark_job()
        done, calls = h.run_body("spark-job")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("CLASS-ORIGIN-OK", done.stdout)
        submits = argv_of(calls, "spark-submit")
        self.assertEqual(len(submits), 1)
        argv = submits[0]
        joined = " ".join(argv)
        self.assertEqual(argv[argv.index("--master") + 1], "yarn")
        self.assertEqual(argv[argv.index("--deploy-mode") + 1], "cluster")
        confs = [argv[i + 1] for i, a in enumerate(argv) if a == "--conf"]
        for want in ("spark.yarn.tags=" + TAG, "spark.yarn.populateHadoopClasspath=false", "spark.authenticate=true",
                     "spark.network.crypto.enabled=true", "spark.network.crypto.authEngineVersion=1", "spark.io.encryption.enabled=true",
                     "spark.dynamicAllocation.shuffleTracking.enabled=true", "spark.yarn.jars=local:/opt/scholarchain-runtime/jars/*",
                     "spark.yarn.appMasterEnv.JAVA_HOME=" + str(h.jdk), "spark.executorEnv.JAVA_HOME=" + str(h.jdk)):
            self.assertIn(want, confs)
        self.assertFalse([c for c in confs if "lzo" in c.lower()])
        self.assertEqual(argv[-2], "local:" + str(h.jobjar))
        rendered = json.loads((h.run_root / "config" / "spark-config.json").read_text())
        self.assertEqual(rendered["outputRoot"], str(h.run_root / "spark"))
        self.assertEqual(rendered["hadoopRunRoot"], str(h.run_root / "hadoop" / "run-1"))
        self.assertEqual(rendered["other"], 1, "only the four documented keys may be rewritten in the template")

    def test_no_probe_result_blocks_the_job(self):
        h = Harness(self)
        h.stage_for_spark_job()
        (h.run_root / "results" / "class-origin.json").unlink()
        self.expect_blocked(h, "no class-origin result")

    def test_each_documented_class_origin_violation_blocks_the_job(self):
        h0 = Harness(self)
        jars = str(h0.runtime / "jars")
        cases = {
            "executor on Java 11": dict(executor={"executorId": "1", "javaVersion": "11.0.2", "libraries": h0.libs()}),
            "driver on Java 8": dict(driver={"javaVersion": "1.8.0_402"}),
            "executor Spark version differs": dict(executor={"executorId": "1", "javaVersion": "17.0.12", "libraries": h0.libs(spark="3.5.1")}),
            "executor Scala 2.12": dict(executor={"executorId": "1", "javaVersion": "17.0.12", "libraries": h0.libs(scala="2.12.18")}),
            "executor classes outside the runtime jars": dict(executor={"executorId": "1", "javaVersion": "17.0.12",
                                                                         "libraries": h0.libs(origin_dir="/usr/lib/spark/jars")}),
            "scala3-library from another jar": dict(executor={"executorId": "1", "javaVersion": "17.0.12",
                                                              "libraries": h0.libs(s3_origin="/tmp/other.jar")}),
            "scala3-library jar hash differs": dict(executor={"executorId": "1", "javaVersion": "17.0.12", "libraries": h0.libs(s3_sha="f" * 64)}),
            "class hash differs between driver and executor": dict(executor={"executorId": "1", "javaVersion": "17.0.12",
                                                                             "libraries": h0.libs(class_sha="DIFFERENT")}),
            "executor is the driver process": dict(executor={"executorId": "driver", "javaVersion": "17.0.12", "libraries": h0.libs()}),
            "no executor reported": dict(taskProcesses=[]),
            "executor not verified externally": dict(externalExecutorVerified=False),
        }
        for label, parts in cases.items():
            with self.subTest(case=label):
                h = Harness(self)
                h.stage_for_spark_job()
                h.write_probe(**parts)
                self.expect_blocked(h, "CLASS-ORIGIN-FAILED")

    def test_wrong_packaged_job_jar_on_the_node_blocks_the_job(self):
        h = Harness(self)
        h.stage_for_spark_job()
        h.jobjar.write_bytes(b"a different jar")
        self.expect_blocked(h, "approved sha256")

    def test_java_that_is_not_17_or_a_missing_java_home_file_blocks_the_job(self):
        h = Harness(self)
        h.stage_for_spark_job()
        done, calls = h.run_body("spark-job", SC_FAKE_JAVA_VERSION="11.0.22")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("not 17", done.stderr)
        self.assertEqual(argv_of(calls, "spark-submit"), [])
        h2 = Harness(self)
        h2.stage_for_spark_job()
        h2.javahome.unlink()
        self.expect_blocked(h2, "no resolved Java 17 home")

    def test_job_needs_exactly_one_completed_hadoop_run_and_er_output(self):
        h = Harness(self)
        h.stage_for_spark_job()
        (h.run_root / "hadoop" / "run-2").mkdir(parents=True)
        (h.run_root / "hadoop" / "run-2" / "_SCHOLARCHAIN_COMPLETE").write_text("")
        self.expect_blocked(h, "exactly one completed run")
        h = Harness(self)
        h.stage_for_spark_job()
        (h.run_root / "er" / "run").rmdir()
        self.expect_blocked(h, "no entity-resolution output")


class StepBodyOnNodeTimeout(unittest.TestCase):
    """13C finding B1: EVERY step body (stage-in and copy-out included, not only the YARN submit) runs on the node under
    `timeout --kill-after=<PIPELINE_KILL_AFTER_SECONDS> <its timeout_seconds> bash FILE`, so a hung copy is killed.

    The `timeout` fake can enforce a short real deadline with GNU semantics (SC_FAKE_OUTER_TIMEOUT_MODE=real): the
    recorded argv carries the true duration (asserted below), the enforced one is shortened so the test is fast. A hung
    `aws s3 cp` is a fake that records its pid and sleeps; the test then proves the process is gone."""

    REAL = {"SC_FAKE_OUTER_TIMEOUT_MODE": "real", "SC_FAKE_TIMEOUT_REAL_SECONDS": "2", "SC_FAKE_TIMEOUT_REAL_KILL_AFTER": "1"}

    def hang_env(self, h, **extra):
        pidfile = h.fx.aux / "hang.pids"
        pidfile.write_text("")
        env = dict(self.REAL, SC_FAKE_AWS_HANG="s3 cp", SC_FAKE_HANG_PIDFILE=str(pidfile))
        env.update(extra)
        return pidfile, env

    @staticmethod
    def pids(pidfile):
        return [int(x) for x in pidfile.read_text().split()]

    def assert_dead(self, pids):
        self.assertTrue(pids, "the hung copy never started, so the test proves nothing")
        for pid in pids:
            for _ in range(50):
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.1)
            else:
                self.fail("the hung process %d is still alive after the step timeout" % pid)

    def stage_copy_out_inputs(self, h):
        # all five parts must exist: the manifest `find hadoop er spark results config` exits 1 on a missing directory
        # (see the report: copy-out is silent-exit-1 when one part is absent although the copy loop skips it)
        for rel, data in {"hadoop/a.txt": b"h", "er/b.txt": b"e", "spark/c.txt": b"s", "results/d.txt": b"r", "config/e.json": b"{}"}.items():
            p = h.run_root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

    def test_every_step_is_printed_with_the_wrapper_parameters_and_its_derived_seconds(self):
        """Hand-derived: max runtime 60 min = 3600 s; weights 5/20/20/5/40/10 -> 180, 720, 720, 180, 1440, 360 s; kill-after 60.
        C1 form: the seconds travel as STEP_SECONDS / KILL_AFTER parameters of the sha256-pinned runner, whose wrapper is
        `timeout --kill-after=KILL_AFTER STEP_SECONDS bash SELF __body STEP ...`."""
        h = Harness(self)
        program = S.installed_program(h.fx, "sc-step.sh")
        self.assertIn('timeout --kill-after="${KILL_AFTER}" "${STEP_SECONDS}" bash "${SELF}" __body "${STEP_NAME}"', program)
        for name, seconds in (("stage-in", 180), ("hadoop-prep", 720), ("entity-resolution", 720), ("spark-class-origin", 180),
                              ("spark-job", 1440), ("copy-out", 360)):
            with self.subTest(step=name):
                params = S.step_params(S.step_args(h.dry, name))
                self.assertEqual(params["STEP_SECONDS"], [str(seconds)])
                self.assertEqual(params["KILL_AFTER"], ["60"])
                self.assertRegex(h.dry.out, r"STEP-TIMEOUT: %s %ds " % (name, seconds))

    def scenario_hung_copy_is_killed(self, step, seconds, patch=None):
        """Run `step` with a hanging `aws s3 cp` under the (fake, GNU-semantics) on-node timeout; assert it was killed."""
        h = Harness(self, patch=patch)
        if step == "copy-out":
            self.stage_copy_out_inputs(h)
        pidfile, env = self.hang_env(h)
        self.addCleanup(self.reap, pidfile)
        try:
            done, calls = h.run_body(step, timeout=20, **env)
        except subprocess.TimeoutExpired:
            self.fail("the %s body did not return: the hung copy was NOT killed by an on-node timeout" % step)
        self.assertEqual(done.returncode, 124, done.stdout + done.stderr)
        self.assertIn("STEP-FAIL %s: exceeded the %ds step timeout (exit 124)" % (step, seconds), done.stderr)
        self.assertEqual([a[:3] for a in step_wrappers(calls)], [["--kill-after=60", str(seconds), "bash"]])
        self.assert_dead(self.pids(pidfile))
        return calls

    def reap(self, pidfile):
        """Never leave a hung fake behind, even when a (mutation) case proves the body did not kill it."""
        try:
            for pid in self.pids(pidfile):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        except OSError:
            pass

    def test_a_hanging_copy_in_stage_in_is_killed_by_the_on_node_timeout(self):
        calls = self.scenario_hung_copy_is_killed("stage-in", 180)
        self.assertEqual(inner_timeouts(calls), [], "stage-in has no client wrapper: only the step wrapper can kill the hung copy")

    def test_mutation_without_the_step_wrapper_a_hung_stage_in_and_copy_out_are_not_killed(self):
        def drop_wrapper(scripts):
            path = scripts / "emr" / "sc-step.sh"
            text = path.read_text()
            old = 'timeout --kill-after="${KILL_AFTER}" "${STEP_SECONDS}" bash "${SELF}" __body'
            self.assertIn(old, text, "mutation anchor moved: update the mutation")
            path.write_text(text.replace(old, 'bash "${SELF}" __body', 1))
        for step, seconds in (("stage-in", 180), ("copy-out", 360)):
            with self.subTest(step=step):
                with self.assertRaises(AssertionError):
                    self.scenario_hung_copy_is_killed(step, seconds, patch=drop_wrapper)

    def test_a_hanging_copy_in_copy_out_is_killed_by_the_on_node_timeout(self):
        self.scenario_hung_copy_is_killed("copy-out", 360)

    @staticmethod
    def run_with_short_grace(h, step, env):
        """Run the printed step command with its KILL_AFTER=60 parameter edited to 2 (the pinned value would make the test wait a minute)."""
        body = S.extract_body(h.dry, step)
        assert "KILL_AFTER=60" in body
        h.fx.log.write_text("")
        done = subprocess.run(["bash", "-c", body.replace("KILL_AFTER=60", "KILL_AFTER=2", 1)], env=h.body_env(**env),
                              cwd=str(h.fx.repo), capture_output=True, text=True, timeout=40)
        return done, h.fx.calls()

    def scenario_term_ignoring_grandchild_is_dead(self, patch=None):
        """After a step timeout a grandchild that ignores SIGTERM must not outlive the step: the step wrapper kills the whole
        process group (TERM, then KILL after the grace) and says so with STEP-WARN. The `timeout` fake follows coreutils
        semantics (it exits once its direct child is gone), so only the wrapper's group kill can reap the grandchild."""
        h = Harness(self, patch=patch)
        pidfile, env = self.hang_env(h, SC_FAKE_HANG_IGNORE_TERM="1")
        self.addCleanup(self.reap, pidfile)
        try:
            done, calls = self.run_with_short_grace(h, "stage-in", env)
        except subprocess.TimeoutExpired:
            self.fail("the step body did not return")
        self.assertIn("STEP-FAIL stage-in: exceeded the 180s step timeout", done.stderr)
        self.assertIn(done.returncode, (124, 137), done.stdout + done.stderr)
        self.assertEqual([a[:3] for a in step_wrappers(calls)], [["--kill-after=2", "180", "bash"]])
        self.assert_dead(self.pids(pidfile))
        return done

    def test_a_term_ignoring_grandchild_is_dead_after_a_step_timeout_and_the_wrapper_says_so(self):
        done = self.scenario_term_ignoring_grandchild_is_dead()
        self.assertIn("STEP-WARN stage-in", done.stderr)

    def test_a_grandchild_that_obeys_term_leaves_no_warning(self):
        h = Harness(self)
        pidfile, env = self.hang_env(h)
        self.addCleanup(self.reap, pidfile)
        done, _ = self.run_with_short_grace(h, "stage-in", env)
        self.assertEqual(done.returncode, 124, done.stdout + done.stderr)
        self.assertNotIn("STEP-WARN", done.stderr)
        self.assert_dead(self.pids(pidfile))

    def test_mutation_without_the_group_kill_a_term_ignoring_grandchild_survives(self):
        def patch(scripts):
            path = scripts / "emr" / "sc-step.sh"
            text = path.read_text()
            old = "\n    kill_group KILL\n"
            self.assertIn(old, text, "mutation anchor moved: update the mutation")
            path.write_text(text.replace(old, "\n    true\n", 1))
        with self.assertRaises(AssertionError):
            self.scenario_term_ignoring_grandchild_is_dead(patch=patch)

    def test_a_step_that_finishes_in_time_passes_through_its_own_exit_status(self):
        h = Harness(self)
        done, calls = h.run_body("stage-in", **self.REAL)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("STEP-FAIL", done.stderr)
        self.assertEqual(len(step_wrappers(calls)), 1)
        h2 = Harness(self)
        h2.fx.update_scenario(s3_total_size=268435457)
        done, _ = h2.run_body("stage-in", **self.REAL)
        self.assertEqual(done.returncode, 1, "an ordinary die() keeps exit 1 and is not mislabelled as a timeout")
        self.assertIn("exceeds", done.stderr)
        self.assertNotIn("exceeded the", done.stderr)

    def test_term_sent_to_the_step_is_forwarded_and_the_hung_copy_dies(self):
        """EMR cancel-steps sends an interrupt to the step process; the wrapper must forward it to the timeout process."""
        h = Harness(self)
        pidfile, env = self.hang_env(h, SC_FAKE_TIMEOUT_REAL_SECONDS="100")
        h.fx.log.write_text("")
        proc = subprocess.Popen(["bash", "-c", S.extract_body(h.dry, "stage-in")], env=h.body_env(**env), cwd=str(h.fx.repo),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            for _ in range(100):
                if pidfile.read_text().strip():
                    break
                time.sleep(0.1)
            self.assertTrue(pidfile.read_text().strip(), "the copy never started")
            os.kill(proc.pid, signal.SIGTERM)
            out, err = proc.communicate(timeout=30)
        finally:
            if proc.poll() is None:
                proc.kill()
        self.assertEqual(proc.returncode, 143, out + err)
        self.assert_dead(self.pids(pidfile))

    def test_a_yarn_body_still_kills_the_tagged_application_when_the_step_timeout_fires(self):
        """Item 1 together with B1: a hung hadoop client under the step wrapper ends with the YARN kill by run tag."""
        h = Harness(self)
        done, calls = h.run_body("hadoop-prep", SC_FAKE_TIMEOUT_MODE="exit:124")
        self.assertEqual(done.returncode, 124, done.stdout + done.stderr)
        self.assertEqual({a[2] for a in argv_of(calls, "yarn") if a[:2] == ["application", "-kill"]}, set(APPS.split(",")))
        self.assertEqual(len(step_wrappers(calls)), 1)


if __name__ == "__main__":
    unittest.main()

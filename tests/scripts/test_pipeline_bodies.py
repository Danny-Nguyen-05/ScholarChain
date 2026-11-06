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
import subprocess
import unittest
from pathlib import Path

import sc_support as S

TAG = "bp-test-run-1"
APPS = "application_1700000000000_0001,application_1700000000000_0002"


class Harness:
    def __init__(self, test, **cfg_over):
        self.test = test
        self.fx = S.Fixture(test)
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

    def run_body(self, name, **extra):
        self.fx.log.write_text("")
        done = subprocess.run(["bash", "-c", S.extract_body(self.dry, name)], env=self.body_env(**extra), cwd=str(self.fx.repo),
                              capture_output=True, text=True, timeout=120)
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
                timeouts = argv_of(calls, "timeout")
                self.assertEqual(len(timeouts), 1)
                self.assertIn("HadoopPrepMain", " ".join(timeouts[0]))
                self.assertIn("-Dmapreduce.job.tags=%s" % TAG, timeouts[0])
                self.assertIn("720", timeouts[0], "the step timeout derived from the runtime cap must wrap the client")

    def test_spark_job_cap_kills_the_tagged_applications(self):
        h = Harness(self)
        h.stage_for_spark_job()
        done, calls = h.run_body("spark-job", SC_FAKE_TIMEOUT_MODE="exit:124")
        self.check_kill(done, calls, 124)
        wrapped = argv_of(calls, "timeout")[0]
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
        self.assertEqual(len(argv_of(calls, "timeout")), 1)
        self.assertTrue([a for a in argv_of(calls, "hadoop") if a[:1] == ["jar"]])
        self.assertEqual([a for a in argv_of(calls, "yarn") if a[:2] == ["application", "-kill"]], [])

    def test_hadoop_body_refuses_an_artifact_whose_sha256_differs_before_any_client_runs(self):
        h = Harness(self)
        (h.fx.s3dir / "hadoop-submit.jar").write_bytes(b"tampered jar")
        done, calls = h.run_body("hadoop-prep")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("sha256 mismatch", done.stderr)
        self.assertEqual([a for a in argv_of(calls, "hadoop") if a[:1] == ["jar"]], [])
        self.assertEqual(argv_of(calls, "timeout"), [])

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
        self.assertEqual(argv_of(calls, "timeout"), [])
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


if __name__ == "__main__":
    unittest.main()

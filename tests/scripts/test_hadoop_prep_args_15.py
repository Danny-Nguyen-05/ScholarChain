"""Phase 15 P6 defects D1/D2: the EXACT hadoop-prep argument vector that sc-step.sh builds is accepted by the real Hadoop job
(test-engineer, independent, cross-module: scripts/emr/sc-step.sh -> modules/hadoop HadoopPrepMain).

Human instruction (2026-11-16): "D1/D2: add a test that feeds the exact arguments sc-step.sh builds into the Hadoop job's parser,
plus the S run without workarounds as proof."

How (black box on both sides, nothing re-derived):
  1. The hadoop-prep body is taken verbatim from a dry run of the real scripts/run-bounded-pipeline.sh (a scratch copy) and run with
     bash against the sc_support fakes (test_pipeline_bodies.Harness). The fake S3 serves the REAL built JARs and the real Phase 15A
     prep config, so the body's sha256 checks pass on the real artifacts. The fake `hadoop` binary records the argv
     `jar <job.jar> <main> ...` that the body builds; that recorded argv is the object under test.
  2. The recorded argv is replayed unchanged through `org.apache.hadoop.util.RunJar` (what `hadoop jar` runs) on Java 17 with the
     built submit JAR, the dependency bundle the argv names in -libjars, and the Hadoop client classpath of the Phase 15 P6 build.
     NO substitution: `--execution-mode cluster` is kept. HadoopPrepMain parses the generic options and the app args, validates the
     config, then HadoopPrepPipeline.execute checks the run id (`run:<uuid v4>`), resolves the output root, binds the four staged
     inputs (copies of datasets/samples/**) and claims the run directory (mkdirs) BEFORE any job is submitted. Acceptance is
     observed as that run directory appearing at exactly <--output-root>/<uuid>; the JVM is then stopped (there is no YARN here).
  3. Mutations of the fixture's COPY of sc-step.sh restore the pre-fix forms: `--run-id "${RUN_ID}"` (D1) is refused by the same
     parser ("run id is not a version-4 run id") and nothing is claimed; `--output-root "file://${out_dir}"` (D2) is not refused
     but misrouted: the run directory is claimed under a RELATIVE `file:` directory in the working directory, not under the output
     root (FsPaths.runPath treats a non-remote root as a java.nio path). Both mutants are therefore detected.

Proof run (cited, not re-run here): target/phase15/p6/work/p6-S-20261116T171431Z/evidence/summary.json (git-ignored; read 2026-11-16):
allStepsPassed true, all 6 steps exit 0, `workarounds` holds only the ER heap item (D3) and no hadoop-CLI workaround (the opt-in
P6_WORKAROUND_HADOOP_CLI path of scripts/lib/p6_local.py that removed the run id and the file:// scheme was not used); the Hadoop
run id was run:650ff98f-1fff-49e3-9957-a0d84c3e992a under <run>/hadoop/650ff98f-...; its pins hadoop-submit-jar 3defe8e6... and
hadoop-libjars 76a1b455... equal the JARs this test used on 2026-11-16.

Prerequisites (otherwise the class is SKIPPED with the reason, never passed): a Java 17 home, the two built Hadoop JARs and the
Hadoop client classpath file of the P6 build. No sbt, no AWS, no network.
"""
import glob
import os
import re
import shutil
import signal
import subprocess
import time
import unittest
from pathlib import Path

import sc_support as S
from test_pipeline_bodies import Harness

HADOOP_TARGET = S.REPO / "modules/hadoop/target/scala-3.3.4"
SUBMIT_JAR = HADOOP_TARGET / "hadoop-submit_3-0.1.0-SNAPSHOT.jar"
BUNDLE_JAR = HADOOP_TARGET / "hadoop-dependency-bundle_3-0.1.0-SNAPSHOT.jar"
CLIENT_CP_FILE = S.REPO / "target/phase15/p6/build/hadoop-dependency-classpath.raw.txt"
PREP_CONFIG = S.REPO / "experiments/inputs/15a/prep-config.json"
SAMPLES = S.REPO / "datasets/samples"
MAIN = "edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"
V4_RUN_ID = re.compile(r"^run:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")  # core StableIds run id rule
CLAIM_SECONDS = 180


def java17_home():
    candidates = [os.environ.get("SC_TEST_JAVA17_HOME", ""), "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"]
    candidates += sorted(glob.glob("/usr/lib/jvm/*17*")) + sorted(glob.glob("/Library/Java/JavaVirtualMachines/*17*/Contents/Home"))
    for home in candidates:
        java = os.path.join(home, "bin", "java")
        if home and os.path.isfile(java):
            done = subprocess.run([java, "-version"], capture_output=True, text=True)
            if re.search(r'version "17[."]', done.stderr):
                return home
    return None


def client_classpath():
    if not CLIENT_CP_FILE.is_file():
        return ""
    parts = [line.strip() for line in CLIENT_CP_FILE.read_text().splitlines()]
    return ":".join(p for p in parts if p.startswith("/") and p.endswith(".jar") and os.path.isfile(p))


JAVA17 = java17_home()
CLIENT_CP = client_classpath()
MISSING = [what for what, ok in (("a Java 17 home", JAVA17), ("the built hadoop-submit JAR", SUBMIT_JAR.is_file()),
                                 ("the built hadoop dependency bundle", BUNDLE_JAR.is_file()),
                                 ("the P6 Hadoop client classpath", "hadoop-common" in CLIENT_CP)) if not ok]


def old_run_id(scripts):
    """D1 mutant: the pre-fix argument, the pipeline run id itself."""
    edit(scripts, '--run-id "${hadoop_id}"', '--run-id "${RUN_ID}"')


def old_output_root(scripts):
    """D2 mutant: the pre-fix file:// URI as the output root."""
    edit(scripts, '--output-root "${out_dir}"', '--output-root "file://${out_dir}"')


def edit(scripts, old, new):
    path = scripts / "emr" / "sc-step.sh"
    text = path.read_text()
    if text.count(old) != 1:
        raise AssertionError("mutation anchor not found exactly once in the fixture copy of sc-step.sh: %s" % old)
    path.write_text(text.replace(old, new))


def option(argv, name):
    return argv[argv.index(name) + 1]


@unittest.skipIf(MISSING, "prerequisites missing: %s" % ", ".join(MISSING))
class HadoopPrepArgumentsReachTheRealParser(unittest.TestCase):
    def capture(self, patch=None):
        """Runs the dry-run hadoop-prep body on the real artifacts and returns (harness, recorded `hadoop jar` argv)."""
        h = Harness(self, patch=patch)
        shutil.copyfile(SUBMIT_JAR, h.fx.s3dir / "hadoop-submit.jar")
        shutil.copyfile(BUNDLE_JAR, h.fx.s3dir / "hadoop-libs.jar")
        shutil.copyfile(PREP_CONFIG, h.fx.repo / "inputs/prep.json")
        h.fx.commit_all("phase 15A prep config")
        hashes = {"hadoop-submit-jar": S.sha256_file(SUBMIT_JAR), "hadoop-libjars": S.sha256_file(BUNDLE_JAR), "job-jar": h.job_sha,
                  "spark-config-template": S.sha256_file(h.fx.s3dir / "spark-template.json")}
        h.dry = h.fx.dry(extra_env=h.env_cfg, artifact_hashes=hashes)
        self.assertEqual(h.dry.rc, 0, h.dry.describe())
        shutil.copytree(SAMPLES, h.run_root / "inputs" / "datasets" / "samples")  # what stage-in leaves on the mount
        done, calls = h.run_body("hadoop-prep")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        jars = [c["argv"] for c in calls if c["tool"] == "hadoop" and c["argv"][:1] == ["jar"]]
        self.assertEqual(len(jars), 1, calls)
        argv = jars[0]
        self.assertEqual(argv[2], MAIN)
        return h, argv

    def replay(self, h, argv):
        """`hadoop jar` = RunJar on HADOOP_CLASSPATH (the bundle, as the body exports it) + the Hadoop client classpath; argv unchanged.
        Returns (exit code or None if stopped, output, working directory, claimed run directory or None)."""
        cwd = h.fx.aux / ("replay-%d" % len(list(h.fx.aux.glob("replay-*"))))
        tmp = cwd / "tmp"
        tmp.mkdir(parents=True)
        bundle = option(argv, "-libjars")
        expected = Path(option(argv, "--output-root")) / option(argv, "--run-id").replace("run:", "", 1)
        command = [os.path.join(JAVA17, "bin", "java"), "-Xmx1g", "-Djava.io.tmpdir=%s" % tmp,
                   "-cp", bundle + ":" + CLIENT_CP, "org.apache.hadoop.util.RunJar"] + argv[1:]
        env = {"PATH": "/usr/bin:/bin", "HOME": str(h.fx.home), "JAVA_HOME": JAVA17, "TMPDIR": str(tmp)}
        log = cwd / "replay.log"
        with open(log, "w") as handle:
            child = subprocess.Popen(command, cwd=str(cwd), env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
            claimed, deadline = None, time.time() + CLAIM_SECONDS
            try:
                while time.time() < deadline and child.poll() is None:
                    found = [p for p in (expected, *cwd.glob("file:/**/%s" % expected.name)) if p.is_dir()]
                    if found:
                        claimed = found[0]
                        break
                    time.sleep(0.2)
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    rc = None
                else:
                    rc = child.returncode
        if claimed is None:
            found = [p for p in (expected, *cwd.glob("file:/**/%s" % expected.name)) if p.is_dir()]
            claimed = found[0] if found else None
        return rc, log.read_text(errors="replace"), cwd, claimed

    def test_the_argv_sc_step_builds_is_accepted_and_claims_the_run_directory_under_the_output_root(self):
        h, argv = self.capture()
        run_id, root = option(argv, "--run-id"), option(argv, "--output-root")
        self.assertRegex(run_id, V4_RUN_ID, "D1: the Hadoop run id must be run:<uuid v4>")
        self.assertNotEqual(run_id, "bp-test-run-1")
        self.assertEqual(root, str(h.run_root / "hadoop"), "D2: a plain absolute path to the run's hadoop/ directory")
        self.assertNotIn("://", root)
        self.assertEqual(option(argv, "--execution-mode"), "cluster")
        for flag in ("--dblp", "--openalex", "--crossref", "--orcid"):
            self.assertTrue(option(argv, flag).startswith("file://"), "the input URIs may keep file://")
        rc, out, cwd, claimed = self.replay(h, argv)
        self.assertEqual(claimed, Path(root) / run_id.replace("run:", "", 1),
                         "the parser must accept the run id and output root and claim <root>/<uuid>\nrc=%s\n%s" % (rc, out[-3000:]))
        self.assertNotIn("run id is not a version-4 run id", out)
        self.assertNotIn("output root is empty or unresolved", out)
        self.assertFalse((cwd / "file:").exists(), "nothing may be created under a relative file: directory")

    def test_mutant_d1_the_pipeline_run_id_is_refused_by_the_same_parser(self):
        h, argv = self.capture(patch=old_run_id)
        self.assertEqual(option(argv, "--run-id"), "bp-test-run-1")
        rc, out, cwd, claimed = self.replay(h, argv)
        self.assertEqual(rc, 1, out[-3000:])
        self.assertIn("run id is not a version-4 run id: bp-test-run-1", out)
        self.assertIsNone(claimed)
        self.assertFalse((h.run_root / "hadoop").exists(), "a refused run claims nothing")

    def test_mutant_d2_a_file_uri_output_root_is_misrouted_to_a_relative_file_directory(self):
        h, argv = self.capture(patch=old_output_root)
        root = option(argv, "--output-root")
        self.assertTrue(root.startswith("file:///"), root)
        intended = Path(root[len("file://"):]) / option(argv, "--run-id").replace("run:", "", 1)
        rc, out, cwd, claimed = self.replay(h, argv)
        self.assertIsNotNone(claimed, "the mutant was expected to reach the claim\nrc=%s\n%s" % (rc, out[-3000:]))
        self.assertFalse(intended.exists(), "D2 mutant: nothing may reach the intended output root")
        self.assertTrue(str(claimed).startswith(str(cwd / "file:") + os.sep), claimed)


if __name__ == "__main__":
    unittest.main()

import hashlib
import os
import tarfile
import unittest

from helpers import EMR_DIR, ShimTestCase, write_exec

RUN_STEP = os.path.join(EMR_DIR, "run-step.sh")
COLLECT = os.path.join(EMR_DIR, "collect-results.sh")
BUCKET = "scholarchain-spike-emr-111122223333-us-east-2"


class RunStepTests(ShimTestCase):
    def test_wraps_command_in_timeout_with_runtime_env(self):
        self.add_shim("timeout", 'echo "JAVA_HOME=$JAVA_HOME SPARK_HOME=$SPARK_HOME SCALA=$SPARK_SCALA_VERSION CP=${CLASSPATH:-unset}" >> "$SHIM_ORDER_LOG"; shift; shift; exec "$@"')
        r = self.run_script(RUN_STEP, ["300", "echo", "hello"], CLASSPATH="/stock/emr/lib/*")
        self.assertEqual(r.returncode, 0, r.stderr)
        order = self.order()
        self.assertEqual(order[0], "timeout --kill-after=60 300 echo hello")
        self.assertIn("JAVA_HOME=/usr/lib/jvm/java-17-amazon-corretto", order[1])
        self.assertIn("SPARK_HOME=/opt/scholarchain-runtime", order[1])
        self.assertIn("SCALA=2.13", order[1])
        self.assertIn("CP=unset", order[1])
        self.assertIn("hello", r.stdout)

    def test_rejects_non_numeric_timeout(self):
        r = self.run_script(RUN_STEP, ["abc", "true"])
        self.assertEqual(r.returncode, 64)


class CollectResultsTests(ShimTestCase):
    def setUp(self):
        super().setUp()
        self.mnt = os.path.join(self.tmp, "mnt")
        os.makedirs(os.path.join(self.mnt, "results"))
        os.makedirs(os.path.join(self.mnt, "outputs", "g1"))
        with open(os.path.join(self.mnt, "results", "probe-distributed.json"), "w") as h:
            h.write('{"ok":true}\n')
        with open(os.path.join(self.mnt, "outputs", "g1", "t.jsonl"), "w") as h:
            h.write("row\n")
        self.add_shim("sha256sum", 'exec shasum -a 256 "$@"')

    def run_c(self, *extra):
        return self.run_script(COLLECT, ["--bucket", BUCKET, "--region", "us-east-2", *extra],
                               SC_MNT=self.mnt, SC_WORK=os.path.join(self.tmp, "w"))

    def test_uploads_tar_and_matching_manifest(self):
        r = self.run_c()
        self.assertEqual(r.returncode, 0, r.stderr)
        tar_path = os.path.join(self.fake_dir, "s3", BUCKET, "results", "scholarchain-spike-results.tar.gz")
        man_path = os.path.join(self.fake_dir, "s3", BUCKET, "results", "results-manifest.sha256")
        with open(tar_path, "rb") as h:
            digest = hashlib.sha256(h.read()).hexdigest()
        with open(man_path) as h:
            self.assertEqual(h.read().split()[0], digest)
        with tarfile.open(tar_path) as tar:
            names = tar.getnames()
        self.assertIn("files-manifest.sha256", names)
        self.assertIn("results/probe-distributed.json", names)

    def test_refuses_oversize_without_uploading(self):
        r = self.run_c("--max-bytes", "10")
        self.assertEqual(r.returncode, 5)
        self.assertFalse(os.path.exists(os.path.join(self.fake_dir, "s3")))

    def test_requires_bucket_and_region(self):
        r = self.run_script(COLLECT, [])
        self.assertEqual(r.returncode, 64)


if __name__ == "__main__":
    unittest.main()

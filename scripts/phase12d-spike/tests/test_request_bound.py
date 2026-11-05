import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPTS_DIR

BOUND = os.path.join(SCRIPTS_DIR, "request_bound.py")
MANIFEST = os.path.join(SCRIPTS_DIR, "request-manifest.json")
TF_DIR = os.path.normpath(os.path.join(SCRIPTS_DIR, "..", "..", "infra", "terraform", "spikes", "emr-spark-isolated"))


def run(*args):
    return subprocess.run([sys.executable, "-I", BOUND, *args], capture_output=True, text=True, timeout=60)


class RequestBoundTests(unittest.TestCase):
    def test_bound_is_inside_the_reviewed_envelope(self):
        r = run("--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertLessEqual(out["put_list"]["upper_bound"], 1000)
        self.assertLessEqual(out["get_head"]["upper_bound"], 10000)
        self.assertTrue(out["within_envelope"])
        self.assertGreater(out["terraform_api_calls_upper_bound"], 0)
        self.assertEqual(out["inputs"]["staged_objects"], 7)

    def test_log_pusher_assumption_is_explicit_and_counted(self):
        out = json.loads(run().stdout)
        self.assertGreater(out["put_list"]["emr_log_pusher_assumption"], 0)
        self.assertEqual(out["put_list"]["upper_bound"], out["put_list"]["subtotal_with_retry"] + out["put_list"]["emr_log_pusher_assumption"])

    def test_large_runtime_object_uses_multipart_in_the_count(self):
        out = json.loads(run().stdout)
        # 321,876,735 bytes at 5 MiB parts is 62 parts + create + complete, plus smaller objects
        self.assertGreaterEqual(out["put_list"]["terraform_uploads_and_object_tags"], 64)

    def _copy_tf(self):
        tmp = tempfile.mkdtemp(prefix="sc-spike-tf-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name in os.listdir(TF_DIR):
            if name.endswith(".tf"):
                shutil.copy(os.path.join(TF_DIR, name), tmp)
        return tmp

    def test_new_staged_object_without_manifest_update_fails(self):
        tmp = self._copy_tf()
        with open(os.path.join(tmp, "extra.tf"), "w") as handle:
            handle.write('resource "aws_s3_object" "sneaky" {\n  bucket = "x"\n  key = "y"\n}\n')
        r = run("--tf-dir", tmp, "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("MANIFEST MISMATCH", r.stderr)

    def test_manifest_entry_without_terraform_object_fails(self):
        with open(MANIFEST) as handle:
            manifest = json.load(handle)
        manifest["staged_objects"].append({"id": "ghost", "terraform_resource": "aws_s3_object.ghost", "key": "k", "max_bytes": 10, "consumers": ["primary"], "downloader": "cli"})
        tmp = tempfile.mkdtemp(prefix="sc-spike-m-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = os.path.join(tmp, "m.json")
        with open(path, "w") as handle:
            json.dump(manifest, handle)
        r = run("--manifest", path, "--check")
        self.assertEqual(r.returncode, 1)

    def test_check_fails_when_the_envelope_is_exceeded(self):
        with open(MANIFEST) as handle:
            manifest = json.load(handle)
        manifest["assumptions"]["emr_log_pusher_changed_objects_per_interval"] = 100
        tmp = tempfile.mkdtemp(prefix="sc-spike-m-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = os.path.join(tmp, "m.json")
        with open(path, "w") as handle:
            json.dump(manifest, handle)
        r = run("--manifest", path, "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("EXCEEDS", r.stderr)

    def test_repo_script_sizes_fit_their_manifest_caps(self):
        for name in ("bootstrap.sh", "run-step.sh", "collect-results.sh"):
            self.assertLess(os.path.getsize(os.path.join(SCRIPTS_DIR, "emr", name)), 65536)


if __name__ == "__main__":
    unittest.main()

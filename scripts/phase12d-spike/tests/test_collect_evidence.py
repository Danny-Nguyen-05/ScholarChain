import hashlib
import io
import os
import tarfile
import unittest

from helpers import SCRIPTS_DIR, ShimTestCase

SCRIPT = os.path.join(SCRIPTS_DIR, "collect-evidence.sh")
BUCKET = "scholarchain-spike-emr-111122223333-us-east-2"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CollectEvidenceTests(ShimTestCase):
    def stage_results(self, tamper_manifest=False, tamper_file=False):
        probe = b'{"probe":"ok"}\n'
        files = {"results/probe-distributed.json": probe, "outputs/g1/table.jsonl": b"row\n"}
        manifest = "".join(f"{sha(v)}  {k}\n" for k, v in sorted(files.items()))
        if tamper_file:
            manifest = manifest.replace(sha(probe), "0" * 64)
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name, data in list(files.items()) + [("files-manifest.sha256", manifest.encode())]:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        blob = buf.getvalue()
        digest = sha(blob) if not tamper_manifest else "f" * 64
        self.put(f"s3/{BUCKET}/results/scholarchain-spike-results.tar.gz", blob, "wb")
        self.put(f"s3/{BUCKET}/results/results-manifest.sha256", f"{digest}  scholarchain-spike-results.tar.gz\n")
        self.put(f"s3/{BUCKET}/emr-logs/j-1/node/i-1/controller.gz", b"log", "wb")

    def run_ce(self, dest, **kw):
        return self.run_script(SCRIPT, ["--bucket", BUCKET, "--dest", dest], **kw)

    def test_happy_path_writes_manifest(self):
        self.stage_results()
        dest = os.path.join(self.tmp, "evidence")
        r = self.run_ce(dest)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        with open(os.path.join(dest, "evidence-manifest.sha256")) as handle:
            manifest = handle.read()
        self.assertIn("results/scholarchain-spike-results.tar.gz", manifest)
        self.assertIn("emr-logs/j-1/node/i-1/controller.gz", manifest)
        self.assertIn("results-extracted/results/probe-distributed.json", manifest)

    def test_fails_on_tarball_manifest_mismatch(self):
        self.stage_results(tamper_manifest=True)
        r = self.run_ce(os.path.join(self.tmp, "evidence"))
        self.assertEqual(r.returncode, 3)
        self.assertIn("MISMATCH", r.stderr)

    def test_fails_on_inner_file_mismatch(self):
        self.stage_results(tamper_file=True)
        r = self.run_ce(os.path.join(self.tmp, "evidence"))
        self.assertEqual(r.returncode, 3)
        self.assertIn("FILE MISMATCH", r.stderr)

    def test_fails_when_results_missing(self):
        os.makedirs(os.path.join(self.fake_dir, "s3", BUCKET, "emr-logs"))
        r = self.run_ce(os.path.join(self.tmp, "evidence"))
        self.assertEqual(r.returncode, 3)

    def test_download_attempts_are_bounded(self):
        # force the recursive copy to fail: the fake returns rc for s3-cp.rc
        self.put("s3-cp.rc", "1")
        r = self.run_ce(os.path.join(self.tmp, "evidence"))
        self.assertEqual(r.returncode, 4)
        with open(self.aws_log) as handle:
            calls = [l for l in handle if "s3 cp" in l]
        self.assertEqual(len(calls), 3)

    def test_rejects_foreign_bucket(self):
        r = self.run_script(SCRIPT, ["--bucket", "other-bucket", "--dest", os.path.join(self.tmp, "e")])
        self.assertEqual(r.returncode, 64)


if __name__ == "__main__":
    unittest.main()

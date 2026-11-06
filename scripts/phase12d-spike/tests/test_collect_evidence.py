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
    def stage_results(self, tamper_manifest=False, tamper_file=False, extra_files=None, extra_members=()):
        probe = b'{"probe":"ok"}\n'
        files = {"results/probe-distributed.json": probe, "outputs/g1/table.jsonl": b"row\n"}
        files.update(extra_files or {})
        manifest = "".join(f"{sha(v)}  {k}\n" for k, v in sorted(files.items()))
        if tamper_file:
            manifest = manifest.replace(sha(probe), "0" * 64)
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name, data in list(files.items()) + [("files-manifest.sha256", manifest.encode())] + list(extra_members):
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

    def test_item_31_extracts_hadoop_crc_files_that_macos_tar_mistakes_for_appledouble(self):
        # Hadoop writes real checksum files named ._SUCCESS.crc; bsdtar on macOS refuses to restore them
        # ("Failed to restore metadata", exit 1) and `set -e` then stopped the script (live attempt 5).
        extra = {"outputs/g1/_SUCCESS": b"", "outputs/g1/._SUCCESS.crc": b"crc\x00\x00\x00\x00", "outputs/g1/.part-0.snappy.parquet.crc": b"crc1"}
        self.stage_results(extra_files=extra)
        dest = os.path.join(self.tmp, "evidence")
        r = self.run_ce(dest)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("verified 5 extracted file(s)", r.stdout)
        crc = os.path.join(dest, "results-extracted", "outputs", "g1", "._SUCCESS.crc")
        self.assertTrue(os.path.isfile(crc), "the ._SUCCESS.crc member must be extracted verbatim")
        with open(crc, "rb") as handle:
            self.assertEqual(handle.read(), b"crc\x00\x00\x00\x00")
        with open(os.path.join(dest, "evidence-manifest.sha256")) as handle:
            self.assertIn("results-extracted/outputs/g1/._SUCCESS.crc", handle.read())

    def test_item_31_the_script_does_not_extract_with_the_system_tar_and_disables_mac_metadata(self):
        with open(SCRIPT, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotRegex(text, r"(?m)^\s*tar\s+-x")
        self.assertIn("COPYFILE_DISABLE=1", text)

    def test_unsafe_tar_members_are_refused(self):
        self.stage_results(extra_members=[("../escape.txt", b"x")])
        r = self.run_ce(os.path.join(self.tmp, "evidence"))
        self.assertEqual(r.returncode, 3)
        self.assertIn("could not be extracted safely", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "escape.txt")))

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

"""Phase 15 P1: scripts/upload-emr-artifacts.sh --hadoop-config FILE uploads the Hadoop prep config to
emr/<run_prefix>/config/hadoop-config.json, so the experiment manifest's pipeline.hadoop_config can be the S3 URI
s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/config/hadoop-config.json with the sha pin name hadoop-config.

Runs against the fake aws of fake_tool.py (no cloud, no credentials). The base fixture (test_upload_emr_artifacts.EmrBase) plans 20 files;
--hadoop-config adds exactly one. Expected values are computed here with hashlib, independent of the script.
"""
import os
import re
import unittest

from helpers import sha256_bytes
from test_upload_emr_artifacts import MANIFEST_REL, ROOT, EmrBase, plan_hash

PREP = b'{"maxLocalSampleRecords": 60000, "reducerCount": 8}\n'
KEY = ROOT + "/config/hadoop-config.json"


class HadoopConfigUploadTests(EmrBase):
    def setUp(self):
        super().setUp()
        self.prep = self.write_bytes("../cfg/prep-config.json", PREP)

    def with_prep(self, **kwargs):
        extra = list(kwargs.pop("extra", ())) + ["--hadoop-config", self.prep]
        return self.run_upload(extra=extra, **kwargs)

    def test_the_dry_run_prints_the_key_and_sha256_and_calls_no_aws(self):
        result = self.with_prep()
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.calls("aws"), [])
        self.assertRegex(result.stdout, r"(?m)^UPLOAD-FILE: \d+ class=config:hadoop-config\.json key=%s bytes=%d sha256=%s$"
                         % (re.escape(KEY), len(PREP), sha256_bytes(PREP)))
        self.assertEqual(len(re.findall(r"^UPLOAD-FILE: ", result.stdout, re.M)), 21, "20 base files plus the Hadoop config")
        self.assertIn("EMR-RENDER: --sha hadoop-config=%s    # ref s3://scholarchain-course-<acct>-artifacts/%s" % (sha256_bytes(PREP), KEY),
                      result.stdout)

    def test_the_plan_hash_covers_the_hadoop_config(self):
        expected = dict(self.expected, **{KEY: PREP})
        result = self.with_prep()
        self.assertIn("PLAN-SHA256: %s" % plan_hash(expected), result.stdout)
        self.assertNotIn("PLAN-SHA256: %s" % plan_hash(self.expected), result.stdout)

    def test_the_object_name_is_fixed_whatever_the_local_file_name(self):
        other = self.write_bytes("../cfg/any-name.json", PREP)
        keys = re.findall(r" key=(\S+) ", self.run_upload(extra=["--hadoop-config", other]).stdout)
        self.assertIn(KEY, keys)
        self.assertEqual([k for k in keys if k.endswith("hadoop-config.json")], [KEY])

    def test_without_the_option_nothing_changes(self):
        result = self.run_upload()
        self.assertEqual(result.rc, 0, result.out)
        self.assertNotIn("hadoop-config", result.stdout)
        self.assertEqual(len(re.findall(r"^UPLOAD-FILE: ", result.stdout, re.M)), 20)

    def test_a_missing_or_linked_hadoop_config_is_refused(self):
        missing = self.run_upload(extra=["--hadoop-config", os.path.join(self.tmp, "nope.json")])
        self.assertEqual(missing.rc, 3, missing.out)
        self.assertIn("--hadoop-config file nope.json does not exist", missing.stdout)
        link = os.path.join(self.tmp, "link.json")
        os.symlink(self.prep, link)
        linked = self.run_upload(extra=["--hadoop-config", link])
        self.assertEqual(linked.rc, 3, linked.out)
        self.assertIn("symbolic link", linked.stdout)

    def test_the_option_needs_a_value(self):
        result = self.run_script("upload-emr-artifacts.sh", *(self.args() + ["--hadoop-config"]), FAKE_S3_DIR=self.s3)
        self.assertEqual(result.rc, 2, result.out)
        self.assertIn("--hadoop-config needs a value", result.out)

    def test_execute_uploads_and_verifies_the_hadoop_config(self):
        expected = dict(self.expected, **{KEY: PREP})
        approval = self.write_record(self.approval_text(entries=expected))
        result = self.with_prep(execute=True, approval=approval)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.stored(KEY), PREP)
        files = {f["key"]: f for f in self.manifest(MANIFEST_REL)["files"]}
        self.assertEqual((files[KEY]["class"], files[KEY]["sha256"], files[KEY]["status"]), ("config:hadoop-config.json", sha256_bytes(PREP), "uploaded"))
        self.assertTrue(all(k.startswith(ROOT + "/") for k in self.stored_keys()))

    def test_help_documents_the_option_and_the_manifest_uri(self):
        result = self.run_script("upload-emr-artifacts.sh", "--help")
        self.assertEqual(result.rc, 0)
        self.assertIn("[--hadoop-config FILE]", result.stdout)
        self.assertIn("config/hadoop-config.json", result.stdout)
        self.assertIn("pipeline.hadoop_config is s3://<bucket>/emr/<run-prefix>/config/hadoop-config.json", result.stdout)


if __name__ == "__main__":
    unittest.main()

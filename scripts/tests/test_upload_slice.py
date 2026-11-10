"""scripts/upload-slice.sh (Phase 14C): upload of a completed Phase 6 export to the curated bucket under <run_prefix>/.

Everything runs against a fake aws that keeps a bucket in a directory (fake_tool.py, FAKE_S3_DIR): no cloud, no credentials.
Hand-derived expectations: the export fixture below has 5 Parquet table files (one per table root, two under nodes/ and edges/ are
single types) plus 4 root files and 4 load manifests, so 5 + 4 + 4 = 13 uploaded files; the sidecars (_SUCCESS, a .crc file), the
Neptune CSV directory, plans/, integrity/ and the event-log summary are never uploaded. The expected checksum is computed here
with hashlib, independent of the script: S3's ChecksumSHA256 is base64 of the raw sha256 digest.
"""
import hashlib
import json
import os
import re
import sys
import unittest
from unittest import mock

from helpers import FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, SCRIPTS_DIR, Fixture, b64_sha256, sha256_bytes

sys.path.insert(0, os.path.join(SCRIPTS_DIR, "lib"))
import upload_slice  # noqa: E402

PREFIX = "run-20261115"
BUCKET = "scholarchain-course-%s-curated" % FAKE_ACCOUNT
MANIFEST_REL = os.path.join("target", "phase14", "evidence", "14c", "upload-manifest.json")
PARQUET_FILES = {
    "nodes/type=researcher/run_id=r1/part-00000.parquet": b"PAR1 researcher nodes",
    "edges/type=coauthored_with/run_id=r1/part-00000.parquet": b"PAR1 coauthored edges",
    "metrics/type=kcore/window=all-years/run_id=r1/part-00000.parquet": b"PAR1 kcore metrics",
    "path-evidence/window=all-years/run_id=r1/part-00000.parquet": b"PAR1 path evidence",
    "semantic-summaries/window=all-years/run_id=r1/part-00000.parquet": b"PAR1 semantic summaries",
}
RUN_MANIFEST = json.dumps({"runId": "run-synthetic-1", "schema": "synthetic"})
RUN_METADATA = json.dumps({"runId": "run-synthetic-1", "tables": []})
LOAD_MANIFESTS = ("neptune", "dynamodb", "s3vectors", "s3")


def marker_for(manifest, metadata):
    """What the Spark job writes (modules/storage ManifestRows.scala): sha256(run-manifest + LF + run-metadata) + LF."""
    return hashlib.sha256((manifest + "\n" + metadata).encode()).hexdigest() + "\n"


class UploadBase(Fixture):
    def setUp(self):
        super().setUp()
        self.s3 = os.path.join(self.tmp, "s3")
        os.makedirs(self.s3)
        self.export = self.make_export("export")

    # ---- fixtures ---------------------------------------------------------------------------
    def put_file(self, root, rel, data):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode())
        return path

    def make_export(self, name, manifest=RUN_MANIFEST, metadata=RUN_METADATA, marker=None):
        root = os.path.join(self.tmp, name)
        for rel, data in PARQUET_FILES.items():
            self.put_file(root, rel, data)
        self.put_file(root, "nodes/type=researcher/run_id=r1/.part-00000.parquet.crc", b"crc")
        self.put_file(root, "nodes/type=researcher/run_id=r1/_SUCCESS", b"")
        self.put_file(root, "run-manifest.json", manifest)
        self.put_file(root, "run-metadata.json", metadata)
        self.put_file(root, "counters.json", "[]")
        self.put_file(root, "_SCHOLARCHAIN_SPARK_COMPLETE", marker if marker is not None else marker_for(manifest, metadata))
        for store in LOAD_MANIFESTS:
            self.put_file(root, "load-manifests/%s.json" % store, '{"store": "%s"}' % store)
        self.put_file(root, "neptune-opencypher-csv/data/nodes/part-00000.csv", b"id\n")
        self.put_file(root, "plans/plan.json", "{}")
        self.put_file(root, "integrity/note.txt", "x")
        self.put_file(root, "event-log-summary.json", "{}")
        return root

    def expected_files(self):
        """{relative path: bytes} of everything that must be uploaded, derived from the fixture alone."""
        files = dict(PARQUET_FILES)
        files["run-manifest.json"] = RUN_MANIFEST.encode()
        files["run-metadata.json"] = RUN_METADATA.encode()
        files["counters.json"] = b"[]"
        files["_SCHOLARCHAIN_SPARK_COMPLETE"] = marker_for(RUN_MANIFEST, RUN_METADATA).encode()
        for store in LOAD_MANIFESTS:
            files["load-manifests/%s.json" % store] = ('{"store": "%s"}' % store).encode()
        return files

    def seed(self, key, data, checksum="auto"):
        """Pre-existing object in the fake bucket (data plus its S3 metadata)."""
        path = os.path.join(self.s3, BUCKET, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        meta = os.path.join(self.s3, ".meta", BUCKET, key + ".json")
        os.makedirs(os.path.dirname(meta), exist_ok=True)
        with open(meta, "w", encoding="utf-8") as handle:
            json.dump({"ChecksumSHA256": b64_sha256(data) if checksum == "auto" else checksum, "VersionId": "seeded-version"}, handle)

    def stored(self, key):
        with open(os.path.join(self.s3, BUCKET, key), "rb") as handle:
            return handle.read()

    def stored_keys(self):
        base = os.path.join(self.s3, BUCKET)
        found = []
        for current, _dirs, files in os.walk(base):
            for name in files:
                found.append(os.path.relpath(os.path.join(current, name), base).replace(os.sep, "/"))
        return sorted(found)

    # ---- runners ----------------------------------------------------------------------------
    def args(self, execute=False, prefix=PREFIX, bucket=BUCKET, export=None, profile="scholarchain-operator", extra=()):
        argv = ["--export-dir", export or self.export, "--run-prefix", prefix, "--bucket", bucket, "--region", "us-east-2"]
        if execute and profile:
            argv += ["--profile", profile]
        if execute:
            argv.append("--execute")
        return argv + list(extra)

    def run_upload(self, execute=False, env=None, **kwargs):
        environment = {"FAKE_S3_DIR": self.s3}
        environment.update(env or {})
        return self.run_script("upload-slice.sh", *self.args(execute=execute, **kwargs), **environment)

    def aws_calls(self, op=None):
        calls = [args for _n, args in self.calls("aws")]
        return [a for a in calls if op is None or a.startswith("s3api %s" % op) or a.startswith(op)]

    def manifest(self):
        with open(os.path.join(self.repo, MANIFEST_REL), encoding="utf-8") as handle:
            return json.load(handle)


class DryRunTests(UploadBase):
    def test_the_dry_run_prints_the_plan_with_path_key_bytes_and_sha256_and_calls_no_aws(self):
        result = self.run_upload()
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.calls("aws"), [], "a dry run makes no aws call at all")
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)), "a dry run writes no manifest")
        expected = self.expected_files()
        self.assertIn("EXPORT-RUN: id=run-synthetic-1 tables=5 files=%d bytes=%d" % (len(expected), sum(len(v) for v in expected.values())), result.stdout)
        self.assertEqual(len(expected), 13)
        for rel, data in expected.items():
            line = "path=%s key=%s/%s bytes=%d sha256=%s" % (rel, PREFIX, rel, len(data), sha256_bytes(data))
            self.assertIn(line, result.stdout)
        self.assertEqual(len(re.findall(r"^UPLOAD-FILE: ", result.stdout, re.M)), 13)
        self.assertTrue(result.result_line().startswith("RESULT: PASS dry run: 13 file(s) planned under %s/; nothing was uploaded" % PREFIX), result.result_line())

    def test_every_planned_key_is_inside_the_run_prefix(self):
        result = self.run_upload()
        keys = re.findall(r" key=(\S+) ", result.stdout)
        self.assertEqual(len(keys), 13)
        for key in keys:
            self.assertTrue(key.startswith(PREFIX + "/"), key)
            self.assertNotIn("..", key.split("/"))

    def test_sidecars_the_neptune_csv_plans_integrity_and_event_logs_are_not_uploaded(self):
        result = self.run_upload()
        for needle in ("_SUCCESS", ".crc", "neptune-opencypher-csv", "plans/", "integrity", "event-log-summary"):
            self.assertNotIn("path=%s" % needle, result.stdout)
            self.assertNotRegex(result.stdout, r"UPLOAD-FILE: .*%s" % re.escape(needle))
        self.assertIn("EXPORT-SKIPPED: sidecar count=2", result.stdout)
        for name in ("neptune-opencypher-csv", "plans", "integrity", "event-log-summary.json"):
            self.assertIn("EXPORT-SKIPPED: not-uploaded:%s count=1" % name, result.stdout)

    def test_the_dry_run_prints_the_commands_execute_would_run_with_the_checksum_and_conditional_write(self):
        result = self.run_upload()
        put = [line for line in result.stdout.splitlines() if line.startswith("DRY-RUN CMD:") and "put-object" in line]
        self.assertEqual(len(put), 1)
        for needle in ("--checksum-algorithm SHA256", "--checksum-sha256", "--if-none-match", "--bucket", "<acct>"):
            self.assertIn(needle, put[0])
        self.assertNotIn(FAKE_ACCOUNT, result.out, "the account in the bucket name is shown as <acct>")
        self.assertIn("get-object-attributes", result.stdout)
        self.assertIn("head-object", result.stdout)

    def test_the_dry_run_needs_no_profile_but_execute_does(self):
        result = self.run_upload(profile=None)
        self.assertEqual(result.rc, 0, result.out)
        refused = self.run_upload(execute=True, profile=None, env={"AWS_PROFILE": None})
        self.assertEqual(refused.rc, 2, refused.out)
        self.assertIn("--execute needs --profile", refused.out)
        self.assertEqual(self.aws_calls(), [])

    def test_help_documents_the_refusals_the_conditional_write_and_the_exit_codes(self):
        result = self.run_script("upload-slice.sh", "--help")
        self.assertEqual(result.rc, 0)
        for needle in ("^run-[a-z0-9][a-z0-9-]{1,27}$", "--if-none-match", "--checksum-algorithm SHA256", "Dry run (default)", "UNCHANGED", "never overwritten", "upload-manifest"):
            self.assertIn(needle, result.stdout)
        self.assertNotRegex(result.stdout, r"\b\d{12}\b")

    def test_help_lists_the_bad_run_prefix_under_usage_errors_exit_2_as_the_script_behaves(self):
        """The help used to list the run prefix under 'Refusals (exit 3)' although the script exits 2 (usage). Behavior is exit 2 (see
        test_a_missing_or_invalid_run_prefix_is_a_usage_error); the help must say the same."""
        text = self.run_script("upload-slice.sh", "--help").stdout
        usage_part = text.split("Usage errors (exit 2", 1)[1].split("Refusals (exit 3", 1)[0]
        refusal_part = text.split("Refusals (exit 3", 1)[1].split("Dry run (default)", 1)[0]
        self.assertIn("run prefix", usage_part)
        self.assertIn("^run-[a-z0-9][a-z0-9-]{1,27}$", usage_part)
        self.assertIn("-curated", usage_part)
        self.assertNotIn("run prefix", refusal_part)
        self.assertNotIn("^run-[a-z0-9]", refusal_part)
        bad = self.run_script("upload-slice.sh", "--export-dir", self.export, "--run-prefix", "pipeline", "--bucket", BUCKET, "--region", "us-east-2")
        self.assertEqual(bad.rc, 2, bad.out)


class RefusalTests(UploadBase):
    def refused(self, rc=3, **kwargs):
        result = self.run_upload(**kwargs)
        self.assertEqual(result.rc, rc, result.out)
        self.assertEqual(self.calls("aws"), [], "a refusal happens before any aws call")
        self.assertEqual(self.stored_keys(), [])
        return result

    def test_a_missing_or_invalid_run_prefix_is_a_usage_error(self):
        for prefix in ("", "pipeline", "run-", "run-a", "RUN-20261115", "run-../x", "run-20261115/", "run-" + "a" * 40, "embedding-text"):
            with self.subTest(prefix=prefix):
                argv = ["--export-dir", self.export, "--bucket", BUCKET, "--region", "us-east-2"]
                if prefix:
                    argv += ["--run-prefix", prefix]
                result = self.run_script("upload-slice.sh", *argv, FAKE_S3_DIR=self.s3)
                self.assertEqual(result.rc, 2, result.out)
                self.assertIn("RESULT: REFUSED step=usage", result.stdout)
        self.assertEqual(self.calls("aws"), [])

    def test_a_bucket_that_is_not_the_curated_bucket_is_a_usage_error(self):
        for bucket in ("", "scholarchain-course-%s-graph" % FAKE_ACCOUNT, "scholarchain-course-curated", "other-%s-curated" % FAKE_ACCOUNT, "scholarchain-course-12345-curated"):
            with self.subTest(bucket=bucket):
                result = self.run_script("upload-slice.sh", "--export-dir", self.export, "--run-prefix", PREFIX, "--bucket", bucket, "--region", "us-east-2")
                self.assertEqual(result.rc, 2, result.out)
        self.assertEqual(self.calls("aws"), [])

    def test_an_export_without_the_completion_marker_is_not_completed(self):
        os.remove(os.path.join(self.export, "_SCHOLARCHAIN_SPARK_COMPLETE"))
        result = self.refused()
        self.assertIn("UPLOAD-REFUSED: the export is not completed: _SCHOLARCHAIN_SPARK_COMPLETE is missing", result.stdout)

    def test_an_export_without_manifests_is_not_completed(self):
        for rel in ("run-manifest.json", "run-metadata.json", "counters.json"):
            with self.subTest(rel):
                export = self.make_export("export-" + rel.split(".")[0])
                os.remove(os.path.join(export, rel))
                result = self.run_upload(export=export)
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn("is missing", result.stdout)
        export = self.make_export("export-no-load-manifests")
        for store in LOAD_MANIFESTS:
            os.remove(os.path.join(export, "load-manifests", "%s.json" % store))
        result = self.run_upload(export=export)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("holds no load manifest", result.stdout)
        self.assertEqual(self.calls("aws"), [])

    def test_a_marker_that_does_not_match_the_manifests_is_refused(self):
        export = self.make_export("export-altered")
        with open(os.path.join(export, "run-metadata.json"), "a", encoding="utf-8") as handle:
            handle.write(" ")
        result = self.run_upload(export=export)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("completion marker does not match", result.stdout)
        export = self.make_export("export-marker", marker="not-a-hash\n")
        self.assertEqual(self.run_upload(export=export).rc, 3)
        self.assertEqual(self.calls("aws"), [])

    def test_manifests_that_name_different_runs_are_refused(self):
        other = json.dumps({"runId": "run-synthetic-2"})
        export = self.make_export("export-two-runs", metadata=other)
        result = self.run_upload(export=export)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("do not name the same runId", result.stdout)

    def test_an_export_without_parquet_files_is_refused(self):
        export = self.make_export("export-empty")
        for rel in PARQUET_FILES:
            os.remove(os.path.join(export, rel))
        result = self.run_upload(export=export)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("no Parquet table files", result.stdout)

    def test_an_unexpected_file_inside_a_table_directory_is_refused(self):
        self.put_file(self.export, "nodes/type=researcher/run_id=r1/notes.txt", "x")
        result = self.refused()
        self.assertIn("unexpected file nodes/type=researcher/run_id=r1/notes.txt", result.stdout)

    def test_a_parquet_file_outside_a_typed_table_directory_is_refused(self):
        self.put_file(self.export, "nodes/stray.parquet", b"PAR1")
        result = self.refused()
        self.assertIn("is not under nodes/type=<name>/", result.stdout)

    def test_a_symbolic_link_is_never_uploaded(self):
        target = os.path.join(self.tmp, "outside.parquet")
        with open(target, "wb") as handle:
            handle.write(b"outside")
        os.symlink(target, os.path.join(self.export, "nodes", "type=researcher", "run_id=r1", "link.parquet"))
        result = self.refused()
        self.assertIn("symbolic link", result.stdout)
        os.remove(os.path.join(self.export, "nodes", "type=researcher", "run_id=r1", "link.parquet"))
        os.symlink(os.path.join(self.export, "counters.json"), os.path.join(self.export, "load-manifests", "link.json"))
        self.assertEqual(self.run_upload().rc, 3)

    def test_a_key_with_characters_outside_the_accepted_set_is_refused(self):
        self.put_file(self.export, "nodes/type=researcher/run_id=r1/part with space.parquet", b"PAR1")
        result = self.refused()
        self.assertIn("characters or a length outside the accepted set", result.stdout)

    def test_a_missing_export_directory_is_refused(self):
        result = self.run_upload(export=os.path.join(self.tmp, "no-such-export"))
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.calls("aws"), [])

    def test_an_existing_manifest_output_is_never_overwritten_and_is_refused_before_any_aws_call(self):
        path = os.path.join(self.repo, MANIFEST_REL)
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("earlier evidence")
        result = self.refused(execute=True)
        self.assertIn("RESULT: REFUSED", result.stdout)
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "earlier evidence")

    def test_a_manifest_output_outside_target_is_refused(self):
        for out in (os.path.join(self.tmp, "elsewhere.json"), os.path.join(self.repo, "docs", "upload-manifest.json")):
            with self.subTest(out=out):
                result = self.run_upload(execute=True, extra=["--manifest-out", out])
                self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.calls("aws"), [])


class UnitTests(unittest.TestCase):
    def test_check_key_keeps_every_key_inside_the_run_prefix(self):
        self.assertEqual(upload_slice.check_key("run-1a/nodes/x.parquet", "run-1a"), "run-1a/nodes/x.parquet")
        for key in ("run-1a", "run-1a/", "other/nodes/x.parquet", "run-1a/../x", "run-1a//x", "run-1a/./x", "run-1ab/x", "run-1a/a b", "run-1a/" + "a" * 1100):
            with self.subTest(key=key[:30]):
                with self.assertRaises(upload_slice.Refused):
                    upload_slice.check_key(key, "run-1a")

    def test_check_prefix_matches_the_deployer_rule(self):
        for good in ("run-20261115", "run-ab", "run-a-b", "run-" + "a" * 28):
            self.assertEqual(upload_slice.check_prefix(good), good)
        for bad in ("run-", "run-a", "run--a", "Run-ab", "run-ab_", "run-" + "a" * 29, "x-run-ab", None):
            with self.subTest(bad=bad):
                with self.assertRaises(upload_slice.Refused):
                    upload_slice.check_prefix(bad)

    def scan(self, export, prefix=PREFIX):
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json") as out:
            return upload_slice.main(["scan", "--export", export, "--prefix", prefix, "--out", out.name])

    def test_a_file_over_the_single_put_limit_is_refused(self):
        base = UploadBase("run_upload")
        base.setUp()
        self.addCleanup(base._remove_tmp)
        with mock.patch.object(upload_slice, "MAX_FILE_BYTES", 10):
            self.assertEqual(self.scan(base.export), 1)

    def test_more_files_than_the_limit_or_more_bytes_than_the_total_are_refused(self):
        base = UploadBase("run_upload")
        base.setUp()
        self.addCleanup(base._remove_tmp)
        with mock.patch.object(upload_slice, "MAX_FILES", 12):
            self.assertEqual(self.scan(base.export), 1)
        with mock.patch.object(upload_slice, "MAX_TOTAL_BYTES", 100):
            self.assertEqual(self.scan(base.export), 1)
        self.assertEqual(self.scan(base.export), 0, "the limits are the only reason for the refusals above")


class ExecuteTests(UploadBase):
    def test_every_file_is_uploaded_with_its_sha256_and_a_conditional_write_then_verified(self):
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 0, result.out)
        expected = self.expected_files()
        self.assertEqual(self.stored_keys(), sorted("%s/%s" % (PREFIX, rel) for rel in expected))
        for rel, data in expected.items():
            self.assertEqual(self.stored("%s/%s" % (PREFIX, rel)), data)
        puts = self.aws_calls("put-object")
        self.assertEqual(len(puts), 13)
        for rel, data in expected.items():
            key = "%s/%s" % (PREFIX, rel)
            matching = [p for p in puts if "--key %s " % key in p]
            self.assertEqual(len(matching), 1, key)
            for needle in ("--checksum-algorithm SHA256", "--checksum-sha256 %s" % b64_sha256(data), "--if-none-match *", "--bucket %s" % BUCKET):
                self.assertIn(needle, matching[0])
        self.assertEqual(len(self.aws_calls("head-object")), 13, "every object is verified after the upload")
        self.assertTrue(all("--checksum-mode ENABLED" in a for a in self.aws_calls("head-object")))
        self.assertIn("RESULT: PASS 13 file(s) verified under %s/ (13 uploaded, 0 unchanged)" % PREFIX, result.stdout)

    def test_the_preflight_runs_entirely_before_the_first_put(self):
        self.run_upload(execute=True)
        ops = [a.split()[1] if a.startswith("s3api") else a.split()[0] + " " + a.split()[1] for a in self.aws_calls()]
        first_put = ops.index("put-object")
        self.assertEqual(ops[:2], ["sts get-caller-identity", "sts get-caller-identity"])
        self.assertIn("list-objects-v2", ops[:first_put])
        self.assertNotIn("head-object", ops[:first_put])

    def test_the_manifest_records_key_bytes_sha256_and_version_id_without_the_account_or_credentials(self):
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 0, result.out)
        path = os.path.join(self.repo, MANIFEST_REL)
        self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
        document = self.manifest()
        self.assertEqual(document["schema"], "scholarchain.upload-manifest.v1")
        self.assertEqual((document["run_prefix"], document["export_run_id"], document["region"]), (PREFIX, "run-synthetic-1", "us-east-2"))
        self.assertEqual(document["bucket"], "scholarchain-course-<acct>-curated")
        self.assertEqual(document["totals"], {"files": 13, "bytes": sum(len(v) for v in self.expected_files().values()), "uploaded": 13, "unchanged": 0})
        self.assertEqual(len(document["tables"]), 5)
        by_key = {f["key"]: f for f in document["files"]}
        for rel, data in self.expected_files().items():
            entry = by_key["%s/%s" % (PREFIX, rel)]
            self.assertEqual((entry["bytes"], entry["sha256"], entry["checksum_sha256_b64"], entry["status"]), (len(data), sha256_bytes(data), b64_sha256(data), "uploaded"))
            self.assertRegex(entry["version_id"], r"^ver-[0-9a-f]{10}$")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for canary in (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, "AKIAFAKEFAKEFAKEFAKE"):
            self.assertNotIn(canary, text)
            self.assertNotIn(canary, result.out)

    def test_aws_is_called_with_the_profile_and_credentials_never_appear_in_the_output(self):
        result = self.run_upload(execute=True, env={"FAKE_EMIT": "echo of %s and %s" % (FAKE_SECRET, FAKE_TOKEN)})
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(all(profile == "profile=set" for _n, _a, profile in self.raw_calls()))
        for canary in (FAKE_SECRET, FAKE_TOKEN, "AKIAFAKEFAKEFAKEFAKE", FAKE_ACCOUNT):
            self.assertNotIn(canary, result.out)

    def test_a_rerun_skips_objects_that_already_hold_the_same_content(self):
        expected = self.expected_files()
        for rel in list(expected)[:4]:
            self.seed("%s/%s" % (PREFIX, rel), expected[rel])
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(len(self.aws_calls("put-object")), 9)
        self.assertEqual(result.stdout.count("UNCHANGED: "), 4)
        self.assertIn("(9 uploaded, 4 unchanged)", result.stdout)
        document = self.manifest()
        self.assertEqual(sorted(f["status"] for f in document["files"]).count("unchanged"), 4)
        unchanged = [f for f in document["files"] if f["status"] == "unchanged"]
        self.assertTrue(all(f["version_id"] == "seeded-version" for f in unchanged))

    def test_a_complete_rerun_uploads_nothing(self):
        self.assertEqual(self.run_upload(execute=True).rc, 0)
        os.remove(os.path.join(self.repo, MANIFEST_REL))
        before = self.stored_keys()
        calls_before = len(self.aws_calls("put-object"))
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(len(self.aws_calls("put-object")), calls_before, "no second put")
        self.assertEqual(self.stored_keys(), before)
        self.assertEqual(self.manifest()["totals"]["unchanged"], 13)

    def test_an_existing_object_with_different_content_refuses_before_anything_is_uploaded(self):
        expected = self.expected_files()
        keys = ["%s/%s" % (PREFIX, rel) for rel in expected]
        self.seed(keys[0], expected[list(expected)[0]])
        self.seed(keys[5], b"someone else's bytes")
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("UPLOAD-REFUSED: existing object %s has different content" % keys[5], result.stdout)
        self.assertEqual(self.aws_calls("put-object"), [], "nothing is uploaded when any object conflicts")
        self.assertEqual(self.stored(keys[5]), b"someone else's bytes", "and nothing is overwritten")
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)))

    def test_an_existing_object_of_the_same_size_but_another_sha256_is_a_conflict(self):
        expected = self.expected_files()
        rel = "counters.json"
        self.seed("%s/%s" % (PREFIX, rel), b"XX")  # same size (2 bytes) as "[]"
        self.assertEqual(len(expected[rel]), 2)
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.aws_calls("put-object"), [])

    def test_an_existing_object_without_a_sha256_checksum_cannot_be_proven_equal(self):
        expected = self.expected_files()
        self.seed("%s/counters.json" % PREFIX, expected["counters.json"], checksum=None)
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("has no SHA-256 checksum", result.stdout)
        self.assertEqual(self.aws_calls("put-object"), [])

    def test_a_caller_that_is_not_an_operator_loader_session_is_refused(self):
        for arn in (
            "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-reader/s" % FAKE_ACCOUNT,
            "arn:aws:sts::%s:assumed-role/scholarchain-deployer/s" % FAKE_ACCOUNT,
            "arn:aws:iam::%s:user/someone" % FAKE_ACCOUNT,
        ):
            with self.subTest(arn=arn):
                result = self.run_upload(execute=True, env={"FAKE_STS_ARN": arn})
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn("not an operator-loader session", result.out)
        self.assertEqual(self.aws_calls("put-object") + self.aws_calls("list-objects-v2"), [])

    def test_a_bucket_of_another_account_is_refused(self):
        result = self.run_upload(execute=True, bucket="scholarchain-course-999988887777-curated")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("another account", result.out)
        self.assertEqual(self.aws_calls("put-object"), [])

    def test_a_failed_listing_uploads_nothing(self):
        result = self.run_upload(execute=True, env={"FAKE_S3_LIST_RC": "255"})
        self.assertEqual(result.rc, 5, result.out)
        self.assertEqual(self.aws_calls("put-object"), [])

    def test_a_failed_upload_stops_the_run_writes_no_manifest_and_a_rerun_finishes_the_job(self):
        expected = self.expected_files()
        failing = "%s/%s" % (PREFIX, sorted(expected)[6])
        result = self.run_upload(execute=True, env={"FAKE_S3_PUT_FAIL_KEY": failing})
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("a re-run skips the objects already stored with the same content", result.out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)))
        stored_before = self.stored_keys()
        self.assertLess(len(stored_before), 13)
        self.assertNotIn(failing, stored_before)
        again = self.run_upload(execute=True)
        self.assertEqual(again.rc, 0, again.out)
        self.assertEqual(len(self.stored_keys()), 13)
        self.assertEqual(self.manifest()["totals"]["unchanged"], len(stored_before))

    def test_a_stored_object_whose_checksum_differs_fails_verification_and_writes_no_manifest(self):
        bad = "%s/%s" % (PREFIX, "counters.json")
        result = self.run_upload(execute=True, env={"FAKE_S3_CORRUPT_KEY": bad})
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("RESULT: FAIL step=verify", result.stdout)
        self.assertIn("stored SHA-256 differs from the local file", result.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)))

    def test_an_aws_cli_without_conditional_writes_fails_closed(self):
        result = self.run_upload(execute=True, env={"FAKE_S3_NO_IF_NONE_MATCH": "1"})
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("Unknown options: --if-none-match", result.out)
        self.assertEqual(self.stored_keys(), [])
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)))

    def test_the_run_prefix_is_the_only_place_that_is_written(self):
        self.seed("other-prefix/keep.txt", b"keep")
        self.assertEqual(self.run_upload(execute=True).rc, 0)
        self.assertEqual(self.stored("other-prefix/keep.txt"), b"keep")
        written = [k for k in self.stored_keys() if k != "other-prefix/keep.txt"]
        self.assertTrue(all(k.startswith(PREFIX + "/") for k in written))
        for call in self.aws_calls("put-object"):
            self.assertRegex(call, r"--key %s/" % PREFIX)

    def test_a_custom_manifest_output_below_target_is_used(self):
        out = os.path.join(self.repo, "target", "custom", "manifest.json")
        result = self.run_upload(execute=True, extra=["--manifest-out", out])
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(os.path.isfile(out))
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)))


if __name__ == "__main__":
    unittest.main()

"""Independent tests for scripts/archive-evidence.sh (Subphase 13B, test-engineer).

Contract: scripts/README.md "Evidence archive" and the script's --help (Step 0 answer 7 and carried item 31):
files of at most 1 MiB that are UTF-8 text are copied after redaction; larger or binary files are indexed with their
sha256 and a REQUIRED external location; the label directory must not exist; symlinks and private material are refused;
`._` and .DS_Store names never enter the directory or a tar; --s3-prefix only prints a command; exit 3 is a refusal,
2 a usage error. Expectations are hand-derived; the redaction oracle uses canary values planted by the test.
"""
import hashlib
import json
import os
import subprocess
import tarfile
import unittest

import sc_support as S

LIMIT = 1048576


def label_dir(fx, phase="13", label="t1"):
    return fx.repo / "docs" / "agent-runs" / ("phase-" + phase) / "evidence" / label


class Base(unittest.TestCase):
    def setUp(self):
        self.fx = S.Fixture(self)
        self.src = self.fx.aux / "src"
        self.src.mkdir()

    def put(self, rel, data):
        path = self.src / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            path.write_text(data)
        else:
            path.write_bytes(data)
        return path

    def archive(self, *extra, label="t1", phase="13", category="test-reports", include=None, env=None, secrets=False):
        args = ["--phase", phase, "--label", label, "--include", "%s=%s" % (category, include or self.src)] + list(extra)
        return self.fx.run("archive-evidence.sh", args, env, secrets=secrets)

    def index(self, label="t1"):
        return json.loads((label_dir(self.fx, label=label) / "INDEX.json").read_text())

    def assert_refused(self, r, code=3):
        self.assertEqual(r.rc, code, r.describe())
        self.assertEqual(r.status, "REFUSED", r.describe())
        self.assertEqual(len(r.results()), 1)
        self.assertEqual(r.calls, [])


class ArchiveThresholds(Base):
    def test_small_text_is_copied_and_indexed_with_both_hashes(self):
        self.put("report.txt", "all tests passed\n")
        r = self.archive()
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        copy = label_dir(self.fx) / "test-reports" / "report.txt"
        self.assertTrue(copy.is_file(), "the copied file must sit below <label>/<category>/")
        self.assertEqual(copy.read_text(), "all tests passed\n")
        idx = self.index()
        self.assertEqual(idx["schema"], "scholarchain.evidence-index.v1")
        self.assertEqual(idx["commit"], self.fx.head())
        entry = [e for e in idx["entries"] if e["path"].endswith("report.txt")][0]
        self.assertEqual(entry["category"], "test-reports")
        self.assertEqual(entry["size"], 17)
        self.assertEqual(entry["sha256"], hashlib.sha256(b"all tests passed\n").hexdigest())
        self.assertEqual(entry["archived_sha256"], S.sha256_file(copy))
        self.assertTrue(entry["status"].startswith("copied"))

    def test_exactly_one_mebibyte_is_copied_and_one_byte_more_is_only_indexed(self):
        self.put("edge.log", "x" * LIMIT)
        self.put("over.log", "y" * (LIMIT + 1))
        r = self.archive("--external-location", "over.log=s3://evidence-bucket/archive/over.log")
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        base = label_dir(self.fx) / "test-reports"
        self.assertTrue((base / "edge.log").is_file(), "a file of exactly 1048576 bytes is inclusive and must be copied")
        self.assertEqual((base / "edge.log").stat().st_size, LIMIT)
        self.assertFalse((base / "over.log").exists(), "a file over 1 MiB must not be copied")
        idx = self.index()
        over = [e for e in idx["entries"] if e["path"].endswith("over.log")][0]
        self.assertEqual(over["sha256"], hashlib.sha256(b"y" * (LIMIT + 1)).hexdigest())
        self.assertEqual(over["size"], LIMIT + 1)
        self.assertEqual(over["external_location"], "s3://evidence-bucket/archive/over.log")
        self.assertNotEqual(over["status"].split("-")[0], "copied")

    def test_large_file_without_an_external_location_refuses_the_whole_run_before_writing_anything(self):
        self.put("small.txt", "fine")
        self.put("big.log", "z" * (LIMIT + 1))
        r = self.archive()
        self.assert_refused(r)
        self.assertFalse(label_dir(self.fx).exists(), "nothing may be written when a location is missing")
        self.assertFalse((self.fx.repo / "docs/agent-runs/phase-13").exists())

    def test_binary_file_is_not_copied_and_needs_a_location(self):
        self.put("blob.bin", b"\xff\xfe\x00\x01\x02")
        self.assert_refused(self.archive())
        self.assertFalse(label_dir(self.fx).exists())
        r = self.archive("--external-location", "blob.bin=drive:Evidence folder / blob")
        self.assertEqual(r.rc, 0, r.describe())
        self.assertFalse((label_dir(self.fx) / "test-reports" / "blob.bin").exists())
        entry = [e for e in self.index()["entries"] if e["path"].endswith("blob.bin")][0]
        self.assertEqual(entry["external_location"], "drive:Evidence folder / blob")
        self.assertEqual(entry["sha256"], hashlib.sha256(b"\xff\xfe\x00\x01\x02").hexdigest())

    def test_external_location_must_be_s3_drive_text_or_a_drive_url(self):
        self.put("big.log", "z" * (LIMIT + 1))
        r = self.archive("--external-location", "big.log=/Users/someone/Desktop/big.log")
        self.assertNotEqual(r.rc, 0, r.describe())
        self.assertFalse(label_dir(self.fx).exists())
        r = self.archive("--external-location", "big.log=https://drive.google.com/file/d/abc123/view")
        self.assertEqual(r.rc, 0, r.describe())

    def test_external_location_can_be_named_by_relative_path_or_category_path(self):
        self.put("sub/a.log", "a" * (LIMIT + 1))
        self.put("sub/b.log", "b" * (LIMIT + 1))
        r = self.archive("--external-location", "sub/a.log=s3://bk/a", "--external-location", "test-reports/sub/b.log=s3://bk/b")
        self.assertEqual(r.rc, 0, r.describe())

    def test_markers_and_one_result_line(self):
        self.put("a.txt", "a")
        r = self.archive()
        self.assertEqual(r.rc, 0, r.describe())
        self.assertEqual(len(r.results()), 1)
        self.assertTrue(r.lines()[-1].startswith("RESULT: PASS"))
        for step in ("archive-inputs", "archive-scan", "archive-write", "archive-verify"):
            self.assertIn(step, r.steps())


class ArchiveNeverOverwrites(Base):
    def test_existing_label_directory_is_refused_and_left_untouched(self):
        self.put("a.txt", "first")
        self.assertEqual(self.archive().rc, 0)
        before = {p.relative_to(label_dir(self.fx)): p.read_bytes() for p in label_dir(self.fx).rglob("*") if p.is_file()}
        self.put("a.txt", "second")
        self.put("extra.txt", "more")
        r = self.archive()
        self.assert_refused(r)
        after = {p.relative_to(label_dir(self.fx)): p.read_bytes() for p in label_dir(self.fx).rglob("*") if p.is_file()}
        self.assertEqual(before, after, "an existing evidence directory was modified")

    def test_empty_existing_label_directory_is_also_refused(self):
        label_dir(self.fx).mkdir(parents=True)
        self.put("a.txt", "x")
        self.assert_refused(self.archive())

    def test_existing_tar_is_never_replaced(self):
        self.put("a.txt", "x")
        tar_path = label_dir(self.fx).parent / "t1.tar.gz"
        tar_path.parent.mkdir(parents=True)
        tar_path.write_bytes(b"precious earlier tar")
        r = self.archive("--tar")
        self.assertNotEqual(r.rc, 0, r.describe())
        self.assertEqual(tar_path.read_bytes(), b"precious earlier tar")

    def test_a_new_label_leaves_the_earlier_label_untouched(self):
        self.put("a.txt", "x")
        self.assertEqual(self.archive(label="v1").rc, 0)
        first = (label_dir(self.fx, label="v1") / "INDEX.json").read_bytes()
        self.assertEqual(self.archive(label="v2").rc, 0)
        self.assertEqual((label_dir(self.fx, label="v1") / "INDEX.json").read_bytes(), first)


class ArchiveRefusals(Base):
    def test_symlinks_are_refused(self):
        outside = self.fx.aux / "outside.txt"
        outside.write_text("outside data")
        os.symlink(str(outside), str(self.src / "link.txt"))
        self.put("ok.txt", "ok")
        self.assert_refused(self.archive())
        self.assertFalse(label_dir(self.fx).exists())

    def test_a_symlinked_include_path_or_directory_is_refused(self):
        real = self.fx.aux / "real-dir"
        real.mkdir()
        (real / "a.txt").write_text("a")
        link = self.fx.aux / "linked-dir"
        os.symlink(str(real), str(link))
        self.assert_refused(self.archive(include=link))
        os.symlink(str(real), str(self.src / "subdir-link"))
        self.assert_refused(self.archive(label="t2"))

    def test_private_and_secret_like_names_are_refused_outright(self):
        names = ["terraform.tfstate", "terraform.tfstate.backup", "dev.tfplan", "course.tfvars", "private.tfvars.json", ".env", ".env.local", ".env.production",
                 "server.pem", "deploy.key", "id_rsa", "id_ed25519", "aws-credentials.txt", "my_credentials.json", "plan.tfplan.json", "plan.tfplan.txt"]
        for name in names:
            with self.subTest(name=name):
                fx = S.Fixture(self)
                src = fx.aux / "src"
                src.mkdir()
                (src / name).write_text("irrelevant")
                (src / "fine.txt").write_text("fine")
                r = fx.run("archive-evidence.sh", ["--phase", "13", "--label", "t1", "--include", "plan-receipts=%s" % src])
                self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
                self.assertFalse(label_dir(fx).exists(), "a refused run must not leave a directory")

    def test_only_receipts_and_checksum_sidecars_are_accepted_from_the_plan_family(self):
        self.put("course-abc.tfplan.receipt.json", json.dumps({"schema": "scholarchain.plan-receipt.v2", "commit": self.fx.head()}))
        self.put("course-abc.tfplan.sha256", "a" * 64 + "  course-abc.tfplan\n")
        r = self.archive(category="plan-receipts")
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        base = label_dir(self.fx) / "plan-receipts"
        self.assertTrue((base / "course-abc.tfplan.receipt.json").is_file())
        self.assertTrue((base / "course-abc.tfplan.sha256").is_file())

    def test_missing_source_unknown_category_and_missing_dest_root(self):
        self.assert_refused(self.archive(include=self.fx.aux / "does-not-exist"))
        self.put("a.txt", "a")
        r = self.archive(category="not-a-category")
        self.assertNotEqual(r.rc, 0, r.describe())
        self.assertFalse(label_dir(self.fx).exists())
        r = self.archive("--dest-root", str(self.fx.aux / "no-such-root"))
        self.assert_refused(r)

    def test_usage_errors_exit_two(self):
        self.put("a.txt", "a")
        for args in (["--phase", "1", "--label", "x", "--include", "test-reports=%s" % self.src],
                     ["--phase", "abc", "--label", "x", "--include", "test-reports=%s" % self.src],
                     ["--phase", "13", "--include", "test-reports=%s" % self.src],
                     ["--phase", "13", "--label", "x"],
                     ["--bogus"]):
            with self.subTest(args=args):
                r = self.fx.run("archive-evidence.sh", args)
                self.assertEqual(r.rc, 2, r.describe())
                self.assertEqual(r.calls, [])
                self.assertFalse((self.fx.repo / "docs/agent-runs/phase-13").exists())

    def test_malformed_include_is_rejected_before_anything_is_written(self):
        self.put("a.txt", "a")
        r = self.fx.run("archive-evidence.sh", ["--phase", "13", "--label", "x", "--include", "no-equals-sign"])
        self.assertIn(r.rc, (2, 3), r.describe())
        self.assertEqual(r.status, "REFUSED", r.describe())
        self.assertFalse((self.fx.repo / "docs/agent-runs/phase-13").exists())

    def test_option_parse_errors_print_step_markers_and_one_result_line(self):
        """Resolved finding O3. scripts/README.md: an unknown flag or a flag without its value prints STEP: start,
        STEP: usage and one RESULT: REFUSED step=usage line and exits 2 (the same for every script; see
        test_regression_13a.UsageErrors for all eleven)."""
        for args in (["--bogus"], ["--phase"], ["--label"], ["--include"], ["--external-location"]):
            with self.subTest(args=args):
                r = self.fx.run("archive-evidence.sh", args)
                self.assertEqual(r.rc, 2, r.describe())
                self.assertEqual(r.steps(), ["start", "usage"], r.describe())
                self.assertEqual(len(r.results()), 1, r.describe())
                self.assertTrue(r.result.startswith("RESULT: REFUSED step=usage"), r.result)
                self.assertTrue(r.lines()[-1].startswith("RESULT:"))
                self.assertEqual(r.calls, [])

    def test_label_cannot_escape_the_evidence_directory(self):
        self.put("a.txt", "a")
        for label in ("../escape", "a/b", "..", ".hidden/../../x"):
            with self.subTest(label=label):
                r = self.archive(label=label)
                self.assertNotEqual(r.rc, 0, r.describe())
                self.assertFalse((self.fx.repo / "docs/agent-runs/phase-13/escape").exists())
                self.assertFalse((self.fx.repo / "docs/agent-runs/escape").exists())


class ArchiveMacMetadata(Base):
    """Carried item 31: no `._` member in a new archive."""

    def populate(self):
        self.put("report.txt", "report")
        self.put("._report.txt", "AppleDouble resource fork")
        self.put(".DS_Store", "finder")
        self.put("sub/._nested.txt", "AppleDouble")
        self.put("sub/nested.txt", "nested")
        self.put("hadoop/part-r-00000", "data")
        self.put("hadoop/._SUCCESS.crc", "crc")
        self.put("hadoop/_SUCCESS", "")

    def test_metadata_files_are_skipped_listed_and_never_copied(self):
        self.populate()
        r = self.archive()
        self.assertEqual(r.rc, 0, r.describe())
        copied = sorted(str(p.relative_to(label_dir(self.fx))) for p in label_dir(self.fx).rglob("*") if p.is_file())
        for path in copied:
            base = os.path.basename(path)
            self.assertFalse(base.startswith("._"), path)
            self.assertNotEqual(base, ".DS_Store", path)
        self.assertIn("test-reports/report.txt", copied)
        self.assertIn("test-reports/sub/nested.txt", copied)
        skipped = [e["path"] for e in self.index()["entries"] if e["status"] == "skipped-metadata"]
        self.assertEqual(sorted(os.path.basename(p) for p in skipped), sorted([".DS_Store", "._report.txt", "._nested.txt", "._SUCCESS.crc"]))

    def test_tar_has_no_dot_underscore_members_under_python_tarfile_and_system_tar(self):
        self.populate()
        r = self.archive("--tar")
        self.assertEqual(r.rc, 0, r.describe())
        tar_path = label_dir(self.fx).parent / "t1.tar.gz"
        self.assertTrue(tar_path.is_file(), "--tar must build <label>.tar.gz next to the label directory")
        with tarfile.open(str(tar_path)) as tf:
            names = tf.getnames()
        self.assertTrue(names)
        for name in names:
            self.assertFalse(os.path.basename(name).startswith("._"), name)
            self.assertNotEqual(os.path.basename(name), ".DS_Store")
        self.assertTrue(any(n.endswith("report.txt") for n in names))
        self.assertTrue(any(n.endswith("INDEX.json") for n in names))
        env = dict(os.environ, COPYFILE_DISABLE="1")
        listing = subprocess.run(["tar", "-tzf", str(tar_path)], capture_output=True, text=True, env=env)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        for line in listing.stdout.splitlines():
            self.assertFalse(os.path.basename(line.rstrip("/")).startswith("._"), line)
        self.assertEqual(sorted(listing.stdout.split()), sorted(names))
        self.assertIn("ARCHIVE-TAR", r.out)
        self.assertIn(hashlib.sha256(tar_path.read_bytes()).hexdigest(), r.out, "the tar's sha256 must be printed")

    def test_tar_extracts_cleanly_with_a_plain_tar_command(self):
        self.populate()
        self.assertEqual(self.archive("--tar").rc, 0)
        out = self.fx.aux / "extracted"
        out.mkdir()
        done = subprocess.run(["tar", "-xzf", str(label_dir(self.fx).parent / "t1.tar.gz"), "-C", str(out)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(any(p.name == "report.txt" for p in out.rglob("*")))
        self.assertFalse([p for p in out.rglob("*") if p.name.startswith("._")])


class ArchiveRedaction(Base):
    def test_secrets_accounts_keys_and_private_values_are_redacted_from_copies_and_output(self):
        private_value = "private-tfvars-value-5c61d0e9"
        private = self.fx.aux / "private.tfvars"
        private.write_text('notification_email = "%s"\n' % private_value)
        text = "\n".join([
            "account %s in a log line" % S.ACCOUNT,
            "env value %s" % S.CANARY_SECRET,
            "session %s" % S.CANARY_TOKEN,
            "access key id AKIAIOSFODNN7EXAMPLE",
            "Authorization: Bearer abc.def.ghi-jkl-0123456789",
            "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "aws_session_token: FwoGZXIvYXdzEBYaDExampleSessionTokenValue0123456789",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA7bq98BAD\n-----END RSA PRIVATE KEY-----",
            "tfvars value %s" % private_value,
            "checksum %s" % ("a" * 10 + "123456789012" + "b" * 42),
            "ordinary line that must survive",
        ]) + "\n"
        self.put("log.txt", text)
        r = self.archive(env={"SCHOLARCHAIN_TF_PRIVATE_VARS": str(private)}, secrets=True)
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        copy = (label_dir(self.fx) / "test-reports" / "log.txt").read_text()
        for leaked in (S.ACCOUNT, S.CANARY_SECRET, S.CANARY_TOKEN, "AKIAIOSFODNN7EXAMPLE", "abc.def.ghi-jkl-0123456789",
                       "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "FwoGZXIvYXdzEBYaDExampleSessionTokenValue0123456789",
                       "MIIEowIBAAKCAQEA7bq98BAD", private_value):
            self.assertNotIn(leaked, copy, "unredacted value in the archived copy: %r" % leaked[:20])
        self.assertIn("ordinary line that must survive", copy)
        self.assertIn("a" * 10 + "123456789012" + "b" * 42, copy, "a 12-digit run inside a 64-hex checksum must be left alone")
        for leaked in (S.CANARY_SECRET, S.CANARY_TOKEN, S.ACCOUNT, private_value):
            self.assertNotIn(leaked, r.out)
            self.assertNotIn(leaked, r.err)
        for name, content in self.fx.tree_text(label_dir(self.fx)).items():
            for leaked in (S.CANARY_SECRET, S.CANARY_TOKEN, S.ACCOUNT, private_value):
                self.assertNotIn(leaked, content, "leak in %s" % name)
        entry = [e for e in self.index()["entries"] if e["path"].endswith("log.txt")][0]
        self.assertEqual(entry["sha256"], hashlib.sha256(text.encode()).hexdigest(), "the index keeps the sha256 of the ORIGINAL bytes")
        self.assertNotEqual(entry["archived_sha256"], entry["sha256"])
        self.assertEqual(entry["archived_sha256"], S.sha256_file(label_dir(self.fx) / "test-reports" / "log.txt"))

    def test_generic_secret_token_password_and_api_key_assignments_are_redacted(self):
        """Resolved finding O2. archive-evidence.sh --help: any generic secret, token, password, api-key or credential
        assignment (api_token = ..., client_secret: ..., password=..., api_key: ..., JSON "secret": "...") is redacted
        in the archived copy; numbers, booleans and checksums are left intact; the index keeps the original sha256."""
        pw = "pass" + "word"
        sha = "ab" * 32
        text = "\n".join([
            "api_token = tok_live_51Hq0AbCdEfGh",
            "client_secret: s3cr3t-value-0042",
            "db %s=hunter2hunter2" % pw,
            "api_key: ak_live_9f8e7d6c5b4a",
            '{"secret": "json-secret-value-77", "name": "kept-json-name"}',
            "token_count: 42",
            "secret_rotation_enabled = true",
            "secret_sha256: %s" % sha,
            "ordinary line that must survive",
        ]) + "\n"
        self.put("log.txt", text)
        r = self.archive()
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        copy = (label_dir(self.fx) / "test-reports" / "log.txt").read_text()
        for value in ("tok_live_51Hq0AbCdEfGh", "s3cr3t-value-0042", "hunter2hunter2", "ak_live_9f8e7d6c5b4a", "json-secret-value-77"):
            self.assertNotIn(value, copy, "unredacted value in the archived copy: %s" % value)
            self.assertNotIn(value, r.out + r.err)
        for kept in ("ordinary line that must survive", "kept-json-name", "token_count: 42", "secret_rotation_enabled = true", sha):
            self.assertIn(kept, copy, "text that is not a secret must be left intact: %s" % kept)
        entry = [e for e in self.index()["entries"] if e["path"].endswith("log.txt")][0]
        self.assertEqual(entry["sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertNotEqual(entry["archived_sha256"], entry["sha256"])

    def test_the_source_file_is_never_modified(self):
        original = "account %s\n" % S.ACCOUNT
        path = self.put("log.txt", original)
        self.assertEqual(self.archive().rc, 0)
        self.assertEqual(path.read_text(), original)


class ArchiveS3Prefix(Base):
    def test_s3_prefix_is_a_printed_command_and_nothing_is_uploaded(self):
        self.put("a.txt", "a")
        r = self.archive("--s3-prefix", "s3://evidence-bucket/phase13/13b-v1", "--region", "us-east-2", "--tar")
        self.assertEqual(r.rc, 0, r.describe())
        cmds = [l for l in r.lines() if "aws s3 cp" in l]
        self.assertTrue(cmds, "the S3 command must be printed for the human")
        self.assertTrue(any("--checksum-algorithm SHA256" in l for l in cmds))
        self.assertTrue(any("s3://evidence-bucket/phase13/13b-v1" in l for l in cmds))
        self.assertTrue(any("us-east-2" in l for l in cmds))
        self.assertEqual(r.tool_calls("aws"), [], "archive-evidence.sh must never run aws")
        self.assertEqual(r.calls, [])

    def test_no_cloud_binary_is_called_without_s3_prefix_either(self):
        self.put("a.txt", "a")
        r = self.archive("--tar")
        self.assertEqual(r.calls, [])

    def test_s3_prefix_must_be_an_s3_uri(self):
        self.put("a.txt", "a")
        r = self.archive("--s3-prefix", "https://example.com/x")
        self.assertNotEqual(r.rc, 0, r.describe())
        self.assertEqual(r.calls, [])


class ArchiveDestRoot(Base):
    def test_dest_root_changes_the_location(self):
        self.put("a.txt", "a")
        dest = self.fx.aux / "dest"
        dest.mkdir()
        r = self.archive("--dest-root", str(dest))
        self.assertEqual(r.rc, 0, r.describe())
        self.assertTrue((dest / "phase-13" / "evidence" / "t1" / "INDEX.json").is_file())
        self.assertFalse(label_dir(self.fx).exists())

    def test_multiple_categories_are_kept_apart(self):
        self.put("a.txt", "a")
        other = self.fx.aux / "other"
        other.mkdir()
        (other / "m.json").write_text("{}")
        r = self.fx.run("archive-evidence.sh", ["--phase", "13", "--label", "t1", "--include", "test-reports=%s" % self.src,
                                                "--include", "run-manifests=%s" % other])
        self.assertEqual(r.rc, 0, r.describe())
        self.assertTrue((label_dir(self.fx) / "test-reports" / "a.txt").is_file())
        self.assertTrue((label_dir(self.fx) / "run-manifests" / "m.json").is_file())


if __name__ == "__main__":
    unittest.main()

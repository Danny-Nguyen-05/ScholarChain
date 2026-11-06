"""archive-evidence.sh (Subphase 13B): versioned never-overwritten evidence directories, the 1 MiB copy threshold with required
external locations, redaction, refusal of private material, and tars without macOS "._" members (carried item 31)."""
import hashlib
import json
import os
import subprocess
import tarfile
import unittest

from helpers import FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, SCRIPTS_DIR, Fixture, sha256_bytes

MIB = 1048576
ARCHIVE = os.path.join(SCRIPTS_DIR, "archive-evidence.sh")
DRIVE = "drive:ScholarChain/phase13/%s"


class ArchiveBase(Fixture):
    def setUp(self):
        super().setUp()
        self.src = os.path.join(self.tmp, "src")
        self.dest_root = os.path.join(self.tmp, "evidence-root")
        os.makedirs(self.src)
        os.makedirs(self.dest_root)

    def put(self, rel, data, sub="reports"):
        path = os.path.join(self.src, sub, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode())
        return path

    def archive(self, *extra, label="13b-v1", phase="13", category="test-reports", sub="reports", includes=None, **env):
        args = ["--phase", phase, "--label", label, "--dest-root", self.dest_root]
        for item in includes if includes is not None else ["%s=%s" % (category, os.path.join(self.src, sub))]:
            args += ["--include", item]
        return self.run_script("archive-evidence.sh", *(args + list(extra)), **env)

    def dest(self, label="13b-v1", phase="13"):
        return os.path.join(os.path.realpath(self.dest_root), "phase-%s" % phase, "evidence", label)

    def index(self, label="13b-v1"):
        with open(os.path.join(self.dest(label), "INDEX.json"), encoding="utf-8") as handle:
            return json.load(handle)

    def entry(self, path, label="13b-v1"):
        found = [e for e in self.index(label)["entries"] if e["path"] == path]
        self.assertEqual(len(found), 1, path)
        return found[0]

    def refused(self, result, *needles):
        self.assertEqual(result.rc, 3, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: REFUSED"), result.result_line())
        for needle in needles:
            self.assertIn(needle, result.out)


class CopyAndIndexTests(ArchiveBase):
    def test_small_text_files_are_copied_with_an_index_of_both_hashes(self):
        original = "unit test report: 12 tests, 0 failures\n"
        self.put("report.txt", original)
        self.put("nested/summary.json", '{"tests": 12}\n')
        result = self.archive()
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PASS evidence directory"), result.result_line())
        for marker in ("archive-inputs", "archive-scan", "archive-write", "archive-verify", "archive-complete"):
            self.assertIn(marker, result.steps())
        with open(os.path.join(self.dest(), "test-reports", "report.txt"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), original)
        index = self.index()
        self.assertEqual(index["schema"], "scholarchain.evidence-index.v1")
        self.assertEqual((index["phase"], index["label"], index["commit"]), ("13", "13b-v1", self.head()))
        entry = self.entry("test-reports/report.txt")
        self.assertEqual(entry["status"], "copied")
        self.assertEqual(entry["sha256"], sha256_bytes(original.encode()))
        self.assertEqual(entry["archived_sha256"], sha256_bytes(original.encode()))
        self.assertEqual(entry["size"], len(original))
        self.assertEqual(entry["redactions"], 0)
        self.assertEqual(self.entry("test-reports/nested/summary.json")["status"], "copied")

    def test_exactly_one_mebibyte_is_copied_and_one_byte_more_is_indexed_with_its_external_location(self):
        at_limit = ("a" * (MIB - 1)) + "\n"
        over = ("b" * MIB) + "\n"
        self.put("at-limit.txt", at_limit)
        self.put("over.txt", over)
        self.assertEqual(len(at_limit.encode()), MIB)
        refused = self.archive()
        self.refused(refused, "over.txt", "no required external location", "--external-location")
        self.assertFalse(os.path.exists(self.dest()), "nothing is written when a location is missing")
        result = self.archive("--external-location", "over.txt=" + DRIVE % "over.txt")
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.entry("test-reports/at-limit.txt")["status"], "copied")
        big = self.entry("test-reports/over.txt")
        self.assertEqual(big["status"], "indexed-external")
        self.assertEqual(big["sha256"], sha256_bytes(over.encode()))
        self.assertEqual(big["size"], MIB + 1)
        self.assertEqual(big["external_location"], DRIVE % "over.txt")
        self.assertFalse(os.path.exists(os.path.join(self.dest(), "test-reports", "over.txt")), "an over-limit file is never copied")
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "test-reports", "at-limit.txt")))

    def test_a_large_file_needs_a_valid_s3_or_drive_location(self):
        self.put("big.txt", "c" * (MIB + 5))
        for bad in ("somewhere", "http://example.com/x", "", "ftp://x/y"):
            with self.subTest(bad):
                self.refused(self.archive("--external-location", "big.txt=" + bad), "--external-location")
        self.assertEqual(self.archive("--external-location", "big.txt=s3://bucket/key/big.txt").rc, 0)
        self.assertEqual(self.entry("test-reports/big.txt", "13b-v1")["external_location"], "s3://bucket/key/big.txt")

    def test_the_external_location_may_name_the_file_by_relative_path_or_category_path(self):
        self.put("deep/one.txt", "x" * (MIB + 1))
        self.put("deep/two.txt", "y" * (MIB + 1))
        result = self.archive("--external-location", "deep/one.txt=" + DRIVE % "one", "--external-location", "test-reports/deep/two.txt=" + DRIVE % "two")
        self.assertEqual(result.rc, 0, result.out)

    def test_binary_files_cannot_be_redacted_so_they_are_indexed_not_copied(self):
        self.put("blob.bin", b"\x00\x01\x02binary")
        self.refused(self.archive(), "binary (cannot be redacted)")
        self.assertEqual(self.archive("--external-location", "blob.bin=" + DRIVE % "blob").rc, 0)
        self.assertEqual(self.entry("test-reports/blob.bin")["status"], "indexed-external")
        self.assertFalse(os.path.exists(os.path.join(self.dest(), "test-reports", "blob.bin")))

    def test_all_categories_are_accepted_and_an_unknown_one_is_refused(self):
        for category in ("test-reports", "plan-receipts", "image-digests", "run-manifests", "metric-exports", "experiment-outputs", "release-metadata"):
            with self.subTest(category):
                directory = os.path.join(self.tmp, "cat-" + category)
                os.makedirs(directory)
                with open(os.path.join(directory, "f.txt"), "w") as handle:
                    handle.write(category)
                result = self.archive(label="cat-" + category, includes=["%s=%s" % (category, directory)])
                self.assertEqual(result.rc, 0, result.out)
                self.assertTrue(os.path.exists(os.path.join(self.dest("cat-" + category), category, "f.txt")))
        self.refused(self.archive(label="bad", includes=["other=%s" % self.src]), "CATEGORY")

    def test_a_single_file_source_and_several_includes(self):
        single = self.put("one.json", '{"a": 1}\n')
        other = os.path.join(self.tmp, "digests")
        os.makedirs(other)
        with open(os.path.join(other, "images.txt"), "w") as handle:
            handle.write("sha256:abc\n")
        result = self.archive(includes=["run-manifests=" + single, "image-digests=" + other])
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "run-manifests", "one.json")))
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "image-digests", "images.txt")))


class NeverOverwriteTests(ArchiveBase):
    def test_an_existing_label_directory_is_refused_and_its_content_is_untouched(self):
        self.put("report.txt", "first\n")
        self.assertEqual(self.archive().rc, 0)
        index_before = open(os.path.join(self.dest(), "INDEX.json"), "rb").read()
        self.put("report.txt", "second\n")
        again = self.archive()
        self.refused(again, "never overwritten")
        with open(os.path.join(self.dest(), "test-reports", "report.txt")) as handle:
            self.assertEqual(handle.read(), "first\n")
        self.assertEqual(open(os.path.join(self.dest(), "INDEX.json"), "rb").read(), index_before)
        self.assertEqual(self.archive(label="13b-v2").rc, 0, "a new label makes a new versioned directory")
        with open(os.path.join(self.dest("13b-v2"), "test-reports", "report.txt")) as handle:
            self.assertEqual(handle.read(), "second\n")

    def test_a_symlink_at_the_label_or_a_parent_is_refused(self):
        self.put("report.txt", "x\n")
        elsewhere = os.path.join(self.tmp, "elsewhere")
        os.makedirs(elsewhere)
        os.makedirs(os.path.join(self.dest_root, "phase-13", "evidence"))
        os.symlink(elsewhere, self.dest())
        self.refused(self.archive(), "a path component is a symlink")
        self.assertEqual(os.listdir(elsewhere), [])
        os.unlink(self.dest())
        os.rmdir(os.path.join(self.dest_root, "phase-13", "evidence"))
        os.symlink(elsewhere, os.path.join(self.dest_root, "phase-13", "evidence"))
        refused = self.archive()
        self.assertEqual(refused.rc, 3, refused.out)
        self.assertEqual(os.listdir(elsewhere), [])

    def test_a_missing_destination_root_and_bad_inputs(self):
        self.put("report.txt", "x\n")
        result = self.run_script("archive-evidence.sh", "--phase", "13", "--label", "x1", "--dest-root", os.path.join(self.tmp, "nope"), "--include", "test-reports=" + self.src)
        self.refused(result, "the destination root does not exist")
        self.assertEqual(self.archive(phase="1").rc, 2)
        self.assertEqual(self.archive(label="bad label").rc, 2)
        self.assertEqual(self.archive(label="../escape").rc, 2)
        self.assertEqual(self.run_script("archive-evidence.sh", "--phase", "13", "--label", "x2").rc, 2)
        self.assertEqual(self.run_script("archive-evidence.sh", "--bogus").rc, 2)
        self.assertEqual(self.archive("--s3-prefix", "not-s3").rc, 2)

    def test_the_default_destination_is_the_repository_evidence_directory(self):
        self.put("report.txt", "x\n")
        result = self.run_script("archive-evidence.sh", "--phase", "13", "--label", "13b-v1", "--include", "test-reports=" + os.path.join(self.src, "reports"))
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(os.path.isfile(os.path.join(self.repo, "docs", "agent-runs", "phase-13", "evidence", "13b-v1", "INDEX.json")))


class RedactionTests(ArchiveBase):
    def test_account_ids_secrets_and_credential_shapes_are_redacted_in_copied_text(self):
        text = (
            "account %s deployed\n" % FAKE_ACCOUNT
            + "arn:aws:iam::%s:role/x\n" % FAKE_ACCOUNT
            + "env secret value %s here\n" % FAKE_SECRET
            + "AKIAABCDEFGHIJKLMNOP is a key id\n"
            + "aws_secret_access_key = abcdefghijklmnopqrstuvwxyz0123456789ABCD\n"
            + "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\n"
            + "token %s\n" % FAKE_TOKEN
            + "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Qu\n-----END RSA PRIVATE KEY-----\n"
            + "a checksum %s stays\n" % ("f" * 64)
        )
        self.put("log.txt", text)
        result = self.archive()
        self.assertEqual(result.rc, 0, result.out)
        with open(os.path.join(self.dest(), "test-reports", "log.txt"), encoding="utf-8") as handle:
            archived = handle.read()
        for secret in (FAKE_ACCOUNT, FAKE_SECRET, "AKIAABCDEFGHIJKLMNOP", "abcdefghijklmnopqrstuvwxyz0123456789ABCD", "abcdefghijklmnopqrstuvwxyz123456", FAKE_TOKEN, "MIIBOgIBAAJBAKj34Gkx"):
            self.assertNotIn(secret, archived)
        self.assertIn("account <acct> deployed", archived)
        self.assertIn("arn:aws:iam::<acct>:role/x", archived)
        self.assertIn("a checksum %s stays" % ("f" * 64), archived)
        entry = self.entry("test-reports/log.txt")
        self.assertEqual(entry["sha256"], sha256_bytes(text.encode()), "the index records the ORIGINAL hash")
        self.assertNotEqual(entry["archived_sha256"], entry["sha256"])
        self.assertGreaterEqual(entry["redactions"], 5)
        self.assertEqual(entry["archived_sha256"], sha256_bytes(archived.encode()))
        for secret in (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN):
            self.assertNotIn(secret, result.out)

    def test_the_verification_step_catches_a_value_that_redaction_missed(self):
        self.put("log.txt", "plain\n")
        done = subprocess.run(["bash", ARCHIVE, "--phase", "13", "--label", "v9", "--dest-root", self.dest_root, "--include", "test-reports=" + os.path.join(self.src, "reports")], capture_output=True, text=True, env=self.env())
        self.assertEqual(done.returncode, 0)
        target = os.path.join(self.dest("v9"), "test-reports", "log.txt")
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("late edit: %s\n" % FAKE_ACCOUNT)
        verify = subprocess.run(["python3", "-I", os.path.join(SCRIPTS_DIR, "lib", "archive.py"), "verify", "--dest", self.dest("v9")], capture_output=True, text=True)
        self.assertEqual(verify.returncode, 1)
        self.assertIn("does not match its recorded archived sha256", verify.stdout)
        self.assertIn("12-digit run", verify.stdout)


class PrivateMaterialTests(ArchiveBase):
    def test_private_names_are_refused_outright(self):
        for name in ("terraform.tfstate", "terraform.tfstate.backup", "course.tfplan", "course.tfplan.json", "course.tfplan.txt", "private.local.tfvars", "x.tfvars", ".env", ".env.local", "server.pem", "api.key", "id_rsa", "aws-credentials", "credentials.csv"):
            with self.subTest(name):
                directory = os.path.join(self.tmp, "priv-" + name.replace("/", "_"))
                os.makedirs(directory)
                with open(os.path.join(directory, name), "w") as handle:
                    handle.write("x")
                result = self.archive(label="p-" + str(abs(hash(name)))[:6], includes=["test-reports=" + directory])
                self.refused(result, "private material")
                self.assertEqual(os.listdir(self.dest_root), [], "nothing was written")

    def test_plan_receipts_and_checksum_sidecars_are_accepted(self):
        directory = os.path.join(self.tmp, "plans")
        os.makedirs(directory)
        for name, text in (("course-abc.tfplan.receipt.json", '{"schema": "scholarchain.plan-receipt.v2"}\n'), ("course-abc.tfplan.sha256", "a" * 64 + "\n")):
            with open(os.path.join(directory, name), "w") as handle:
                handle.write(text)
        result = self.archive(includes=["plan-receipts=" + directory])
        self.assertEqual(result.rc, 0, result.out)

    def test_a_symlink_in_a_source_is_refused(self):
        self.put("real.txt", "x\n")
        os.symlink(os.path.join(self.src, "reports", "real.txt"), os.path.join(self.src, "reports", "link.txt"))
        self.refused(self.archive(), "symlink")
        outside = os.path.join(self.tmp, "outside.txt")
        with open(outside, "w") as handle:
            handle.write("secret")
        os.unlink(os.path.join(self.src, "reports", "link.txt"))
        self.assertEqual(self.archive().rc, 0)

    def test_a_missing_or_empty_source_is_refused(self):
        self.refused(self.archive(includes=["test-reports=" + os.path.join(self.tmp, "absent")]), "source refused")
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        self.refused(self.archive(includes=["test-reports=" + empty]), "holds no file")


class MetadataAndTarTests(ArchiveBase):
    """Carried item 31: archives are built without macOS metadata members."""

    def test_metadata_files_are_skipped_listed_and_never_enter_the_directory_or_the_tar(self):
        self.put("report.txt", "report\n")
        self.put("._report.txt", b"\x00\x05\x16\x07AppleDouble")
        self.put(".DS_Store", b"\x00\x00\x00\x01Bud1")
        self.put("sub/._SUCCESS.crc", b"crc")
        result = self.archive("--tar")
        self.assertEqual(result.rc, 0, result.out)
        names = []
        for base, _dirs, files in os.walk(self.dest()):
            names += files
        self.assertEqual(sorted(names), ["INDEX.json", "report.txt"])
        skipped = [e for e in self.index()["entries"] if e["status"] == "skipped-metadata"]
        self.assertEqual({e["path"] for e in skipped}, {"test-reports/._report.txt", "test-reports/.DS_Store", "test-reports/sub/._SUCCESS.crc"})
        self.assertIn("skipped-metadata=3", result.stdout)

    def test_the_tar_listing_has_no_appledouble_member_checked_two_ways(self):
        self.put("a.txt", "a\n")
        self.put("dir/b.txt", "b\n")
        self.put("dir/._b.txt", b"apple")
        result = self.archive("--tar")
        self.assertEqual(result.rc, 0, result.out)
        tar_path = self.dest() + ".tar.gz"
        self.assertTrue(os.path.isfile(tar_path))
        with tarfile.open(tar_path, "r:gz") as archive:
            members = archive.getnames()
            for member in archive.getmembers():
                self.assertEqual((member.uid, member.gid, member.uname, member.gname), (0, 0, "", ""), "no owner names are recorded")
        self.assertEqual(sorted(members), ["13b-v1/INDEX.json", "13b-v1/test-reports/a.txt", "13b-v1/test-reports/dir/b.txt"])
        self.assertFalse([m for m in members if os.path.basename(m).startswith("._")])
        listing = subprocess.run(["tar", "-tzf", tar_path], capture_output=True, text=True, env=dict(os.environ, COPYFILE_DISABLE="1"))
        self.assertEqual(listing.returncode, 0)
        self.assertFalse([l for l in listing.stdout.splitlines() if os.path.basename(l).startswith("._")])
        self.assertIn("no ._ or .DS_Store member", result.stdout)
        self.assertIn("COPYFILE_DISABLE=1", result.stdout)

    def test_the_tar_can_be_extracted_by_the_system_tar_without_errors(self):
        self.put("a.txt", "a\n")
        self.assertEqual(self.archive("--tar").rc, 0)
        out = os.path.join(self.tmp, "extracted")
        os.makedirs(out)
        done = subprocess.run(["tar", "-xzf", self.dest() + ".tar.gz", "-C", out], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(os.path.isfile(os.path.join(out, "13b-v1", "test-reports", "a.txt")))

    def test_an_existing_tar_is_never_overwritten(self):
        self.put("a.txt", "a\n")
        os.makedirs(os.path.join(self.dest_root, "phase-13", "evidence"))
        with open(self.dest() + ".tar.gz", "wb") as handle:
            handle.write(b"existing")
        result = self.archive("--tar")
        self.assertNotEqual(result.rc, 0, result.out)
        with open(self.dest() + ".tar.gz", "rb") as handle:
            self.assertEqual(handle.read(), b"existing")

    def test_the_tar_is_reproducible_in_content_order_and_mtime(self):
        self.put("b.txt", "b\n")
        self.put("a.txt", "a\n")
        self.assertEqual(self.archive("--tar").rc, 0)
        with tarfile.open(self.dest() + ".tar.gz", "r:gz") as archive:
            self.assertEqual([m.mtime for m in archive.getmembers()], [0, 0, 0])
            self.assertEqual(archive.getnames(), sorted(archive.getnames()))


class S3DryRunTests(ArchiveBase):
    def test_the_s3_prefix_prints_the_checksum_command_and_uploads_nothing(self):
        self.put("a.txt", "a\n")
        result = self.archive("--tar", "--s3-prefix", "s3://example-bucket/evidence", "--region", "us-east-2")
        self.assertEqual(result.rc, 0, result.out)
        lines = [l for l in result.stdout.splitlines() if l.startswith("DRY-RUN CMD:")]
        self.assertEqual(len(lines), 2)
        self.assertIn("aws s3 cp %s s3://example-bucket/evidence/phase-13/evidence/13b-v1/ --recursive --checksum-algorithm SHA256 --region us-east-2" % self.dest(), lines[0])
        self.assertIn("aws s3 cp %s.tar.gz s3://example-bucket/evidence/phase-13/evidence/13b-v1.tar.gz --checksum-algorithm SHA256" % self.dest(), lines[1])
        with open(self.dest() + ".tar.gz", "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        self.assertIn("ARCHIVE-TAR-SHA256: %s 13b-v1.tar.gz" % digest, result.stdout)
        self.assertEqual(self.calls(), [], "the aws command is only printed, never run")

    def test_without_an_s3_prefix_no_aws_command_is_printed(self):
        self.put("a.txt", "a\n")
        result = self.archive()
        self.assertNotIn("DRY-RUN CMD", result.stdout)
        self.assertEqual(self.calls(), [])


class HelpTests(unittest.TestCase):
    def test_help_documents_thresholds_locations_exclusions_and_exit_codes(self):
        text = subprocess.run(["bash", ARCHIVE, "--help"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}).stdout
        for needle in ("1 MiB", "ARCHIVE_MAX_COPY_BYTES", "--external-location", "Never overwritten", "COPYFILE_DISABLE=1", "._", "--s3-prefix", "DRY RUN ONLY", "Exit codes", "Human approval points", "Evidence produced", "INDEX.json"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

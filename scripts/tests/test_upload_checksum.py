"""N5 (repair round 3): after the runtime archive upload, deploy.sh compares the object's S3-COMPUTED ChecksumSHA256
(`head-object --checksum-mode ENABLED`, base64 of the raw sha256) with the verified private copy, in addition to the size
and the sha256 metadata the script set itself. A multipart object (the real 322 MB archive) reports a composite checksum;
it is verified part by part against the part list S3 reports. Fake aws only.
"""
import base64
import hashlib
import unittest

from helpers import head_object_text
from test_deploy import ARCHIVE_BYTES, DeployBase


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


class UploadChecksumTests(DeployBase):
    def setUp(self):
        super().setUp()
        self.arrange("base-apply")

    def head_calls(self):
        return [a for _n, a in self.calls("aws") if a.startswith("s3api head-object")]

    def parts_calls(self):
        return [a for _n, a in self.calls("aws") if a.startswith("s3api get-object-attributes")]

    def multipart(self, sizes, tamper=None):
        assert sum(sizes) == len(ARCHIVE_BYTES)
        raws, lines, offset = [], [], 0
        for number, size in enumerate(sizes, 1):
            raw = hashlib.sha256(ARCHIVE_BYTES[offset:offset + size]).digest()
            offset += size
            raws.append(raw)
            lines.append("%d\t%d\t%s" % (number, size, b64(b"\0" * 32 if tamper == number else raw)))
        return b64(hashlib.sha256(b"".join(raws)).digest()) + "-%d" % len(sizes), "\n".join(lines)

    def test_the_s3_computed_checksum_is_compared_and_a_match_passes(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        head = self.head_calls()
        self.assertEqual(len(head), 1)
        self.assertIn("--checksum-mode ENABLED", head[0])
        self.assertIn("ChecksumSHA256", head[0])
        self.assertEqual(self.parts_calls(), [], "a single-part object needs no part list")
        self.assertIn("S3-computed ChecksumSHA256 equals the sha256 of the verified private copy", result.out)

    def test_a_checksum_that_is_not_the_private_copys_fails_the_stage_even_when_size_and_metadata_match(self):
        wrong = b64(hashlib.sha256(b"some other object").digest())
        result = self.execute(FAKE_HEAD_OBJECT=head_object_text(ARCHIVE_BYTES, checksum=wrong))
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("RESULT: FAIL step=runtime-archive-upload", result.stdout)
        self.assertIn("S3-computed ChecksumSHA256 differs", result.out)
        self.assertEqual(self.deploy_manifests("base-apply"), [], "not recorded as a success")

    def test_the_hex_digest_or_a_missing_checksum_fails_closed(self):
        for value in (hashlib.sha256(ARCHIVE_BYTES).hexdigest(), "None"):
            with self.subTest(value=value[:8]):
                result = self.execute(FAKE_HEAD_OBJECT=head_object_text(ARCHIVE_BYTES, checksum=value))
                self.assertEqual(result.rc, 4, result.out)
                self.assertIn("S3-CHECKSUM-FAILED", result.out)

    def test_a_two_field_head_object_answer_is_not_accepted(self):
        result = self.execute(FAKE_HEAD_OBJECT="%d\t%s" % (len(ARCHIVE_BYTES), hashlib.sha256(ARCHIVE_BYTES).hexdigest()))
        self.assertEqual(result.rc, 4, result.out)

    def test_size_and_metadata_are_still_checked_first(self):
        result = self.execute(FAKE_HEAD_OBJECT=head_object_text(ARCHIVE_BYTES, size=5))
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("remote size/sha256 metadata differ", result.out)

    def test_a_multipart_object_is_verified_part_by_part_from_the_part_list_s3_reports(self):
        composite, parts = self.multipart([8, 12])
        result = self.execute(FAKE_HEAD_OBJECT=head_object_text(ARCHIVE_BYTES, checksum=composite), FAKE_OBJECT_PARTS=parts)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(len(self.parts_calls()), 1)
        self.assertIn("--object-attributes ObjectParts", self.parts_calls()[0])
        self.assertIn("composite ChecksumSHA256 (2 parts)", result.out)

    def test_a_multipart_part_that_differs_or_a_truncated_part_list_fails_the_stage(self):
        composite, parts = self.multipart([8, 12], tamper=1)
        result = self.execute(FAKE_HEAD_OBJECT=head_object_text(ARCHIVE_BYTES, checksum=composite), FAKE_OBJECT_PARTS=parts)
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("part 1", result.out)
        composite, parts = self.multipart([8, 12])
        result = self.execute(FAKE_HEAD_OBJECT=head_object_text(ARCHIVE_BYTES, checksum=composite), FAKE_OBJECT_PARTS=parts.splitlines()[0])
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("names 2", result.out)
        self.assertEqual(self.deploy_manifests("base-apply"), [])

    def test_the_dry_run_prints_the_checksum_check_and_runs_no_aws_command(self):
        result = self.deploy()
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])
        self.assertIn("--checksum-mode ENABLED", result.stdout)
        self.assertIn("ChecksumSHA256 is compared with the private copy", result.stdout)
        self.assertIn("get-object-attributes --object-attributes ObjectParts", result.stdout)

    def test_the_uploaded_copy_is_still_the_one_verified(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        uploads = self.uploads()
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0][1], hashlib.sha256(ARCHIVE_BYTES).hexdigest())


if __name__ == "__main__":
    unittest.main()

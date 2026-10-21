#!/usr/bin/env python3
"""Bounded, offline prepared-population retention regression tests."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import retain_prepared_population as retention


class RetentionTests(unittest.TestCase):
    def fixture(self, root):
        root.mkdir()
        for rel in retention.REQUIRED:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"")
        part = root / "export/snapshot=test/run=fixture/work/part-r-00000"
        part.parent.mkdir(parents=True)
        part.write_bytes(b'{"synthetic":"unit-test framing only"}\n')
        (part.parent / ".part-r-00000.crc").write_bytes(b"fixture-crc")
        marker = {"complete": True, "runId": "run:synthetic-unit-test", "configFingerprint": "a" * 64,
                  "partitions": ["snapshot=test/run=fixture/work"], "exportParts": [{"path": "snapshot=test/run=fixture/work/part-r-00000", "bytes": part.stat().st_size, "sha256": retention.sha256(part)}]}
        (root / "_SCHOLARCHAIN_COMPLETE").write_text(json.dumps(marker))
        (root / "run-manifest.json").write_text(json.dumps({"runId": marker["runId"], "configFingerprint": marker["configFingerprint"]}))
        return part.relative_to(root).as_posix()

    def test_retains_exact_bytes_and_nine_success_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            result = retention.retain(source, output)
            self.assertEqual(result["status"], "VALID")
            self.assertEqual(result["files"], 13)
            for rel in retention.framed_files(source)[0]:
                self.assertEqual((source / rel).read_bytes(), (output / rel).read_bytes())
            self.assertTrue((output / "export/snapshot=test/run=fixture/work/.part-r-00000.crc").exists())
            self.assertEqual(len([rel for rel in retention.REQUIRED if rel.endswith("_SUCCESS")]), 9)

    def test_missing_stage_success_rejects_before_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            (source / "intermediate/j04/_SUCCESS").unlink()
            with self.assertRaisesRegex(ValueError, "missing required prepared file"):
                retention.retain(source, output)
            self.assertFalse(output.exists())

    def test_corrupt_export_rejects_before_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            part = self.fixture(source)
            (source / part).write_bytes(b"altered")
            with self.assertRaisesRegex(ValueError, "completion export hash/size mismatch"):
                retention.retain(source, output)
            self.assertFalse(output.exists())

    def test_mutated_retained_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            retention.retain(source, output)
            (output / "export/snapshot=test/run=fixture/work/.part-r-00000.crc").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "retention hash/size mismatch"):
                retention.validate(output)

    def test_missing_retention_manifest_is_not_verified_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            retention.retain(source, output)
            retention.manifest_path(output).unlink()
            with self.assertRaises(FileNotFoundError):
                retention.validate(output)

    def test_existing_destination_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            retention.retain(source, output)
            before = retention.sha256(retention.manifest_path(output))
            with self.assertRaisesRegex(ValueError, "never overwrite"):
                retention.retain(source, output)
            self.assertEqual(before, retention.sha256(retention.manifest_path(output)))

    def test_unsafe_marker_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            self.fixture(source)
            marker = json.loads((source / "_SCHOLARCHAIN_COMPLETE").read_bytes())
            marker["exportParts"][0]["path"] = "../escape"
            (source / "_SCHOLARCHAIN_COMPLETE").write_text(json.dumps(marker))
            with self.assertRaises(ValueError):
                retention.retain(source, Path(tmp) / "output")

    def test_frozen_real_copy_matches_original_without_rewriting(self):
        repository = Path(__file__).resolve().parents[2]
        run = "bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3"
        durable = repository / "datasets/entity-resolution/prepared" / run
        result = retention.validate(durable)
        self.assertEqual(result["files"], 68)
        self.assertEqual(result["bytes"], 49547452)
        self.assertEqual(result["completionSha256"], "ecb1744d591092f66fa57c87108497caf80349d183b79816f7607dcc7b21f399")
        # This test remains runnable after ignored target/ has been cleaned.
        source = repository / "target/phase5c-prep-runs" / run
        if source.exists():
            for rel in retention.framed_files(durable)[0]:
                self.assertEqual(retention.sha256(source / rel), retention.sha256(durable / rel))


if __name__ == "__main__":
    unittest.main()

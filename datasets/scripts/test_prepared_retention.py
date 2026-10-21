#!/usr/bin/env python3
"""Bounded, offline prepared-population retention regression tests."""
import hashlib
import json
import tempfile
import unittest
import subprocess
import sys
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
            result = retention.retain(source, output, purpose=retention.FROZEN_PURPOSE)
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
                retention.retain(source, output, purpose=retention.FROZEN_PURPOSE)
            self.assertFalse(output.exists())

    def test_corrupt_export_rejects_before_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            part = self.fixture(source)
            (source / part).write_bytes(b"altered")
            with self.assertRaisesRegex(ValueError, "completion export hash/size mismatch"):
                retention.retain(source, output, purpose=retention.FROZEN_PURPOSE)
            self.assertFalse(output.exists())

    def test_mutated_retained_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            retention.retain(source, output, purpose=retention.FROZEN_PURPOSE)
            (output / "export/snapshot=test/run=fixture/work/.part-r-00000.crc").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "retention hash/size mismatch"):
                retention.validate(output)

    def test_missing_retention_manifest_is_not_verified_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            retention.retain(source, output, purpose=retention.FROZEN_PURPOSE)
            retention.manifest_path(output).unlink()
            with self.assertRaises(FileNotFoundError):
                retention.validate(output)

    def test_existing_destination_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            retention.retain(source, output, purpose=retention.FROZEN_PURPOSE)
            before = retention.sha256(retention.manifest_path(output))
            with self.assertRaisesRegex(ValueError, "never overwrite"):
                retention.retain(source, output, purpose=retention.FROZEN_PURPOSE)
            self.assertEqual(before, retention.sha256(retention.manifest_path(output)))

    def test_unsafe_marker_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            self.fixture(source)
            marker = json.loads((source / "_SCHOLARCHAIN_COMPLETE").read_bytes())
            marker["exportParts"][0]["path"] = "../escape"
            (source / "_SCHOLARCHAIN_COMPLETE").write_text(json.dumps(marker))
            with self.assertRaises(ValueError):
                retention.retain(source, Path(tmp) / "output", purpose=retention.FROZEN_PURPOSE)

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

    def test_new_retention_requires_explicit_purpose_in_api_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            with self.assertRaises(TypeError):
                retention.retain(source, output)
            result = subprocess.run([sys.executable, retention.__file__, "retain", "--source", str(source), "--destination", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("--purpose", result.stderr)
            self.assertFalse(output.exists())

    def test_demo_retention_has_demo_purpose_and_exact_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            self.fixture(source)
            result = retention.retain(source, output, purpose=retention.DEMO_PURPOSE)
            self.assertEqual(result["purposeKind"], retention.DEMO_PURPOSE)
            manifest = json.loads(retention.manifest_path(output).read_bytes())
            self.assertEqual(manifest["purpose"], retention.PURPOSES[retention.DEMO_PURPOSE])
            for relative in manifest["files"]:
                self.assertEqual((source / relative).read_bytes(), (output / relative).read_bytes())
            manifest["purpose"] = retention.PURPOSES[retention.FROZEN_PURPOSE]
            retention.manifest_path(output).write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "inconsistent retention purpose"):
                retention.validate(output)

    def test_known_demo_inputs_cannot_be_claimed_as_frozen_review(self):
        for run in retention.DEMO_RUNS:
            with self.subTest(run=run):
                claim = {"runId": run, "purposeKind": retention.FROZEN_PURPOSE,
                         "purpose": retention.PURPOSES[retention.FROZEN_PURPOSE],
                         "ownership": retention.OWNERSHIP[retention.FROZEN_PURPOSE]}
                with self.assertRaisesRegex(ValueError, "demo input cannot claim"):
                    retention.check_purpose(claim)

    def test_legacy_5c_manifest_remains_identical_and_demo_payloads_validate(self):
        prepared = Path(__file__).resolve().parents[1] / "entity-resolution/prepared"
        frozen = prepared / retention.FROZEN_RUN.removeprefix("run:")
        self.assertEqual(retention.sha256(retention.manifest_path(frozen)), "c51963569827ceaba35d1f816a918afecd32a547725ba2b1bb63aa38d49e8556")
        self.assertEqual(retention.validate(frozen)["purposeKind"], retention.FROZEN_PURPOSE)
        expected = {"3bfbd651-5982-4f3d-b29b-246fb88d07a1": (36, 524961, "037ab3766408f3cb6dae85636b4b3c4cb0bd73c29251f21578bdbc828e58c65c"),
                    "68c2b012-6d04-4eef-a7bf-5ca31706d895": (60, 1271664, "4113b3f1a8a8c6e8a60d5fd759520ef53d3905d4d3e8ce4bed006fc8840a6c8b")}
        for run, (count, size, completion) in expected.items():
            with self.subTest(run=run):
                result = retention.validate(prepared / run)
                self.assertEqual((result["purposeKind"], result["files"], result["bytes"], result["completionSha256"]), (retention.DEMO_PURPOSE, count, size, completion))


if __name__ == "__main__":
    unittest.main()

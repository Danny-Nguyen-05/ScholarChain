#!/usr/bin/env python3
"""Tests for the per-entry schema_version field and schema note version statements (no network)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_datasets  # noqa: E402

VERSION = "scholarchain.demo-schema.v1"


def entry(version: str = VERSION) -> dict:
    return {"schema": "schemas/demo.md", "schema_version": version}


class SchemaVersionValidationTests(unittest.TestCase):
    def check(self, note_text: str | None, manifest: dict) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if note_text is not None:
                (root / "schemas").mkdir()
                (root / "schemas" / "demo.md").write_text(note_text, encoding="utf-8")
            with mock.patch.object(validate_datasets, "ROOT", root):
                validate_datasets.validate_schema_versions(manifest)

    def test_matching_statement_passes(self) -> None:
        note = f"# Demo\n\n**Schema version:** `{VERSION}`. Describes the demo.\n"
        self.check(note, {"datasets": {"demo": entry()}})

    def test_missing_statement_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.check("# Demo\n\nNo statement here.\n", {"datasets": {"demo": entry()}})
        self.assertIn("no '**Schema version:**' statement", str(ctx.exception))

    def test_mismatched_version_fails(self) -> None:
        note = "# Demo\n\n**Schema version:** `scholarchain.demo-schema.v2`.\n"
        with self.assertRaises(SystemExit) as ctx:
            self.check(note, {"datasets": {"demo": entry()}})
        self.assertIn("does not match manifest schema_version", str(ctx.exception))

    def test_malformed_version_id_fails(self) -> None:
        note = "# Demo\n\n**Schema version:** `1.0`.\n"
        with self.assertRaises(SystemExit) as ctx:
            self.check(note, {"datasets": {"demo": entry("1.0")}})
        self.assertIn("not a valid id", str(ctx.exception))

    def test_missing_note_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.check(None, {"datasets": {"demo": entry()}})
        self.assertIn("schema note missing", str(ctx.exception))

    def test_schema_version_is_a_required_manifest_field(self) -> None:
        self.assertIn("schema_version", validate_datasets.REQUIRED_ENTRY_FIELDS)
        manifest = validate_datasets.load_manifest()
        for key, value in manifest["datasets"].items():
            self.assertIn("schema_version", value, key)


class CommittedManifestTests(unittest.TestCase):
    def test_committed_manifest_and_notes_agree(self) -> None:
        manifest = validate_datasets.load_manifest()
        validate_datasets.validate_manifest_structure(manifest)
        validate_datasets.validate_schema_versions(manifest)

    def test_every_dataset_names_its_upstream_version_or_says_not_recorded(self) -> None:
        manifest = validate_datasets.load_manifest()
        for key, value in manifest["datasets"].items():
            text = (validate_datasets.ROOT / value["schema"]).read_text(encoding="utf-8")
            self.assertIn("**Upstream version:**", text, key)


if __name__ == "__main__":
    unittest.main()

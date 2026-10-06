#!/usr/bin/env python3
"""Regression tests for bounded DBLP acquisition (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import acquire_samples  # noqa: E402
from dblp_entities import dblp_sample_prolog  # noqa: E402


class DblpEntityPrologTests(unittest.TestCase):
    def test_amp_standard_xml_escape_succeeds(self) -> None:
        body = "<title>A &amp; B</title>\n"
        prolog = dblp_sample_prolog(body)
        document = prolog + f"<dblp>\n{body}</dblp>\n"
        import xml.etree.ElementTree as ET

        root = ET.fromstring(document)
        title = root.find("title")
        self.assertIsNotNone(title)
        assert title is not None
        self.assertEqual(title.text, "A & B")

    def test_eacute_entity_is_declared_for_well_formed_xml(self) -> None:
        body = "<title>caf&eacute;</title>\n"
        prolog = dblp_sample_prolog(body)
        self.assertIn("<!ENTITY eacute", prolog)
        document = prolog + f"<dblp>\n{body}</dblp>\n"
        import xml.etree.ElementTree as ET

        ET.fromstring(document)


class _FakeResponse:
    def __init__(self, status: int, headers: dict[str, str], body: bytes) -> None:
        self.status = status
        self.headers = headers
        self._body = body
        self._offset = 0

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            n = len(self._body) - self._offset
        chunk = self._body[self._offset : self._offset + n]
        self._offset += len(chunk)
        return chunk


class HttpGetBoundedTests(unittest.TestCase):
    def test_rejects_body_larger_than_cap(self) -> None:
        payload = b"y" * 2048
        resp = _FakeResponse(200, {}, payload)
        cm = mock.MagicMock()
        cm.__enter__.return_value = resp
        cm.__exit__.return_value = None
        with mock.patch("urllib.request.urlopen", return_value=cm):
            with self.assertRaises(RuntimeError) as ctx:
                acquire_samples.http_get(
                    "http://example.invalid/openalex", max_bytes=512
                )
        self.assertIn("exceeds hard cap", str(ctx.exception))

    def test_rejects_declared_content_length_over_cap(self) -> None:
        resp = _FakeResponse(200, {"Content-Length": "2048"}, b"y" * 2048)
        cm = mock.MagicMock()
        cm.__enter__.return_value = resp
        cm.__exit__.return_value = None
        with mock.patch("urllib.request.urlopen", return_value=cm):
            with self.assertRaises(RuntimeError) as ctx:
                acquire_samples.http_get(
                    "http://example.invalid/orcid", max_bytes=512
                )
        self.assertIn("Content-Length", str(ctx.exception))


class HttpGetRangeTests(unittest.TestCase):
    def test_rejects_full_200_response(self) -> None:
        resp = _FakeResponse(200, {}, b"x" * 64)
        cm = mock.MagicMock()
        cm.__enter__.return_value = resp
        cm.__exit__.return_value = None
        with mock.patch("urllib.request.urlopen", return_value=cm):
            with self.assertRaises(RuntimeError) as ctx:
                acquire_samples.http_get_range("http://example.invalid/dblp.xml.gz", 1024)
        self.assertIn("HTTP 200", str(ctx.exception))

    def test_hard_cap_stops_read_before_full_body(self) -> None:
        payload = b"z" * 4096
        resp = _FakeResponse(
            206,
            {
                "Content-Range": "bytes 0-4095/999999999",
                "Content-Length": str(len(payload)),
            },
            payload,
        )
        body = acquire_samples.read_body_with_hard_cap(resp, 512)
        self.assertEqual(len(body), 512)


if __name__ == "__main__":
    unittest.main()

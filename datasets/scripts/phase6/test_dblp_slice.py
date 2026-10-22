#!/usr/bin/env python3
"""Offline feature tests; never contact DBLP."""
from __future__ import annotations
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acquire_dblp_slice as a


class Response(io.BytesIO):
    status = 200
    def __init__(self, body, declared):
        super().__init__(body)
        self.headers = {'Content-Length': str(declared)}
        self.read_sizes = []
    def geturl(self):
        return a.URL
    def read(self, n=-1):
        self.read_sizes.append(n)
        return super().read(n)


class AcquisitionTests(unittest.TestCase):
    def test_budget_does_not_request_more_than_remaining(self):
        budget = a.Budget(byte_cap=9)
        budget.received = 7
        self.assertEqual(budget.allowance(), 2)
        budget.received = 9
        with self.assertRaisesRegex(RuntimeError, 'byte cap'):
            budget.allowance()

    def test_deadline_refuses_body_read(self):
        clock = iter([0, 1801]).__next__
        budget = a.Budget(clock=clock)
        with self.assertRaisesRegex(RuntimeError, 'deadline'):
            budget.allowance()

    def test_header_refuses_before_body_when_larger_than_remaining_budget(self):
        response = Response(b'abcdef', 6)
        with tempfile.TemporaryDirectory() as root, patch.object(a, 'EXPECTED_BYTES', 6):
            with self.assertRaisesRegex(RuntimeError, 'remaining cumulative'):
                a.download(Path(root) / 'a.gz', a.Budget(byte_cap=5), lambda *x, **kw: response)
        self.assertEqual(response.read_sizes, [])

    def test_redirect_is_refused_without_body_read(self):
        response = Response(b'do not read redirect body', 25)
        with self.assertRaisesRegex(RuntimeError, 'Redirect refused'):
            a.NoRedirect().redirect_request(None, response, 302, '', {}, 'https://other.invalid/')
        self.assertEqual(response.read_sizes, [])

    def test_exact_length_body_read_then_verified_no_extra_byte(self):
        response = Response(b'abcdeEXTRA', 5)
        with tempfile.TemporaryDirectory() as root, patch.object(a, 'EXPECTED_BYTES', 5):
            path = Path(root) / 'a.gz'
            result = a.download(path, a.Budget(byte_cap=5), lambda *x, **kw: response)
            self.assertEqual(path.read_bytes(), b'abcde')
            self.assertEqual(result['bodyBytes'], 5)
        self.assertEqual(response.read_sizes, [5])

    def test_truncated_body_fails_without_retry(self):
        response = Response(b'ab', 5)
        calls = []
        def opener(*args, **kw):
            calls.append(1)
            return response
        with tempfile.TemporaryDirectory() as root, patch.object(a, 'EXPECTED_BYTES', 5):
            with self.assertRaisesRegex(RuntimeError, 'Truncated'):
                a.download(Path(root) / 'a.gz', a.Budget(), opener)
        self.assertEqual(len(calls), 1)

    def test_wrong_pinned_size_or_checksum_refuses_extraction(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'a.gz'
            path.write_bytes(b'not the release')
            with self.assertRaisesRegex(RuntimeError, 'MD5 mismatch'):
                a.verify_archive(path)


class SliceTests(unittest.TestCase):
    def test_adjacent_records_across_arbitrary_chunks(self):
        text = '<dblp><article>unrelated</article><inproceedings key="conf/podc/a">\n<year>2005</year></inproceedings><inproceedings key="conf/wdag/b"><year>2026</year>\n</inproceedings></dblp>'
        expected = ['<inproceedings key="conf/podc/a">\n<year>2005</year></inproceedings>', '<inproceedings key="conf/wdag/b"><year>2026</year>\n</inproceedings>']
        for chunk_size in (1, 7, 16, 1000):
            self.assertEqual(list(a.publication_records(io.StringIO(text), chunk_size)), expected)

    def test_truncated_publication_refused(self):
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            list(a.publication_records(io.StringIO('<inproceedings key="a">')))

    def test_year_venue_cap_source_order_entities_and_replay(self):
        def row(key, year, name='Jos&eacute;'):
            return f'<inproceedings key="{key}">\n<author>{name}</author>\n<title>A &amp; B</title><year>{year}</year>\n</inproceedings>\n'
        text = '<dblp>\n' + ''.join([
            row('conf/podc/a', 2004), row('conf/podc/b', 2005),
            row('conf/podc/c', 2010), row('conf/podc/d', 2026),
            row('conf/wdag/a', 2026), row('conf/disc/b', 2027),
            row('conf/other/a', 2019)]) + '</dblp>\n'
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            archive = root / 'source.gz'
            archive.write_bytes(gzip.compress(text.encode()))
            result = a.select_slice(archive, root / 'one.xml', per_venue_cap=2)
            replay = a.select_slice(archive, root / 'two.xml', per_venue_cap=2)
            self.assertEqual(result, replay)
            self.assertEqual((root / 'one.xml').read_bytes(), (root / 'two.xml').read_bytes())
            self.assertEqual(result['perVenue'], {'disc': 1, 'podc': 2})
            self.assertEqual(result['maximumAuthorCount'], 1)
            self.assertEqual(result['authorCountHistogram'], {'1': 3})
            self.assertEqual(result['publicationCountOver16Authors'], 0)
            parsed = ET.parse(root / 'one.xml').getroot()
            self.assertEqual([n.attrib['key'] for n in parsed], ['conf/podc/b', 'conf/podc/c', 'conf/wdag/a'])
            self.assertEqual(parsed[0].findtext('author'), 'José')
            self.assertEqual(parsed[0].findtext('title'), 'A & B')
            self.assertNotIn('DOCTYPE', (root / 'one.xml').read_text())

    def test_unknown_entity_refused(self):
        with self.assertRaisesRegex(ValueError, 'Unknown DBLP'):
            a.xml_entities('<title>&external;</title>')

    def test_no_eligible_rows_refused(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            archive = root / 'source.gz'
            archive.write_bytes(gzip.compress(b'<dblp/>\n'))
            with self.assertRaisesRegex(ValueError, 'Empty approved slice'):
                a.select_slice(archive, root / 'out.xml')


if __name__ == '__main__':
    unittest.main(verbosity=2)

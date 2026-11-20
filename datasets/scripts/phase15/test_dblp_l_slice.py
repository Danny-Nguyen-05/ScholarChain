#!/usr/bin/env python3
"""Offline feature tests for the P21 L slice; synthetic DBLP XML only, never network."""
from __future__ import annotations
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent))
import select_dblp_l_slice as l  # noqa: E402
s6 = l.s6

CANDIDATES = (('alpha', ('alpha',)), ('beta', ('beta',)), ('gamma', ('gamma',)), ('delta', ('delta',)))


def row(key, year, authors=('Jos&eacute; A',)):
    people = ''.join(f'<author>{a}</author>' for a in authors)
    return f'<inproceedings mdate="2026-01-01" key="{key}">\n{people}<title>T &amp; U</title><year>{year}</year>\n</inproceedings>'


def fixture_text():
    rows = [row('conf/podc/p1', 2004), row('conf/podc/p2', 2005, ('A', 'B')),
            row('conf/alpha/a1', 2010, ('B', 'C')), row('conf/podc/p3', 2010),
            row('conf/podc/p4', 2026),  # beyond S cap 2: in L only when L cap is larger
            row('conf/wdag/d1', 2026, ('C', 'D', 'E')), row('conf/disc/d2', 2027),
            row('conf/beta/b1', 2011), row('conf/beta/b2', 2012, ('F',)), row('conf/beta/b3', 2013),
            row('conf/gamma/g1', 2014, ('G',)), row('conf/gamma/g2', 2015),
            row('conf/delta/x1', 2016), row('conf/other/o1', 2019)]
    # DBLP joins adjacent records on one line; mix both layouts.
    return '<dblp>\n' + ''.join(r + ('' if i % 3 else '\n') for i, r in enumerate(rows)) + '\n</dblp>\n'


class Fixture:
    def __init__(self, root, text=None):
        self.root = Path(root)
        self.archive = self.root / 'archive.xml.gz'
        self.archive.write_bytes(gzip.compress((text or fixture_text()).encode(), mtime=0))
        self.expected = {k: v for k, v in s6.hashes(self.archive).items()}
        self.s_xml = self.root / 's.xml'
        sel = s6.select_slice(self.archive, self.s_xml, per_venue_cap=2)
        self.s_manifest = self.root / 's-manifest.json'
        body = {'selection': {'recordType': 'inproceedings', 'venueKeyAliases': s6.VENUE_ALIASES,
                              'perVenueMaximumRecords': 2, 'minYear': 2005, 'maxYear': 2026, **sel},
                'output': {'sha256': s6.hashes(self.s_xml)['sha256']}}
        self.s_manifest.write_text(json.dumps(body))

    def build(self, **kw):
        options = dict(expected=self.expected, candidates=CANDIDATES, cap=2, target_max=7, minimum=5)
        options.update(kw)
        return l.build(self.archive, self.s_manifest, self.s_xml, **options)


class LSliceTests(unittest.TestCase):
    def test_prefix_rule_counts_authors_and_nesting(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            xml_bytes, manifest = f.build()
            sel = manifest['selection']
            # S = podc p2,p3 + disc d1 (3); alpha +1 = 4; beta +2 = 6; gamma +2 = 8 > 7 stops.
            self.assertEqual(sel['perVenue'], {'alpha': 1, 'beta': 2, 'disc': 1, 'podc': 2})
            self.assertEqual(sel['includedCandidateVenues'], ['alpha', 'beta'])
            self.assertEqual(sel['stoppedAtCandidate'], 'gamma')
            self.assertEqual(sel['candidateEligibleCounts'], {'alpha': 1, 'beta': 2, 'gamma': 2, 'delta': 1})
            self.assertEqual(sel['publicationCount'], 6)
            # Exact strings: A, B, C, D, E, F and the entity-decoded "José A".
            self.assertEqual(sel['distinctExactAuthorStrings'], 7)
            self.assertEqual(sel['observedInproceedings'], 14)
            keys = [n.attrib['key'] for n in ET.fromstring(xml_bytes)]
            self.assertEqual(keys, ['conf/podc/p2', 'conf/alpha/a1', 'conf/podc/p3', 'conf/wdag/d1',
                                    'conf/beta/b1', 'conf/beta/b2'])
            nest = manifest['nestingCheck']
            self.assertEqual(nest['result'], 'PASS')
            self.assertEqual((nest['sPublicationCount'], nest['lPublicationCount']), (3, 6))
            self.assertEqual(nest['sRebuiltOutputSha256'], s6.hashes(f.s_xml)['sha256'])
            self.assertEqual(nest['sXmlFile']['keysMissingFromL'], 0)
            self.assertEqual(manifest['license']['name'], 'CC0 1.0 Universal (DBLP bibliographic metadata)')
            self.assertEqual(manifest['retrieval'], {'mode': 'verified-local-copy', 'bodyBytes': 0})
            self.assertNotIn(b'DOCTYPE', xml_bytes)

    def test_higher_cap_still_nests_and_adds_records(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            xml_bytes, manifest = f.build(cap=3, target_max=20, minimum=5)
            self.assertEqual(manifest['selection']['perVenue']['podc'], 3)
            self.assertIn(b'conf/podc/p4', xml_bytes)
            self.assertEqual(manifest['nestingCheck']['result'], 'PASS')
            self.assertIsNone(manifest['selection']['stoppedAtCandidate'])

    def test_deterministic_bytes_and_manifest_via_cli(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            runs = []
            for name in ('one', 'two'):
                out, man = f.root / f'{name}.xml', f.root / f'{name}.json'
                with patch.object(l, 'PINNED_ARCHIVE', f.expected), \
                     patch.object(l, 'CANDIDATE_VENUES', CANDIDATES), patch.object(l, 'PER_VENUE_CAP', 2), \
                     patch.object(l, 'TARGET_MAX', 7), patch.object(l, 'MINIMUM_TOTAL', 5), \
                     patch('sys.stdout'):
                    with patch.object(l, 'build', lambda a, s, x: l_build(f, a, s, x)):
                        l.main(['--archive', str(f.archive), '--s-manifest', str(f.s_manifest),
                                '--s-xml', str(f.s_xml), '--output', str(out), '--manifest', str(man)])
                body = json.loads(man.read_text())
                runs.append((out.read_bytes(), body))
            (x1, m1), (x2, m2) = runs
            self.assertEqual(x1, x2)
            self.assertEqual(m1['output']['sha256'], m2['output']['sha256'])
            for key in ('selection', 'nestingCheck', 'source'):
                self.assertEqual(m1[key], m2[key])

    def test_cli_refuses_overwrite_before_reading(self):
        with tempfile.TemporaryDirectory() as root:
            existing = Path(root) / 'out.xml'
            existing.write_text('keep')
            with self.assertRaises(FileExistsError):
                l.main(['--archive', str(Path(root) / 'missing.gz'), '--output', str(existing),
                        '--manifest', str(Path(root) / 'm.json')])
            self.assertEqual(existing.read_text(), 'keep')

    def test_nesting_fails_loudly_on_s_manifest_mismatch_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            body = json.loads(f.s_manifest.read_text())
            body['output']['sha256'] = '0' * 64
            f.s_manifest.write_text(json.dumps(body))
            with self.assertRaisesRegex(l.NestingError, 'S subset-of L FAILED.*rebuilt S sha256'):
                f.build()

    def test_cli_nesting_failure_writes_no_output_or_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            body = json.loads(f.s_manifest.read_text())
            body['selection']['selectedKeysSha256'] = '0' * 64
            f.s_manifest.write_text(json.dumps(body))
            out, man = f.root / 'l.xml', f.root / 'l.json'
            with patch.object(l, 'build', lambda a, s, x: l_build(f, a, s, x)), patch('sys.stderr'):
                with self.assertRaisesRegex(l.NestingError, 'selected-keys sha256'):
                    l.main(['--archive', str(f.archive), '--s-manifest', str(f.s_manifest),
                            '--s-xml', str(f.s_xml), '--output', str(out), '--manifest', str(man)])
            self.assertFalse(out.exists())
            self.assertFalse(man.exists())

    def test_receipt_validated_before_scan_and_embedded(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            pinned = dict(f.expected)
            good = {'url': s6.URL, 'bodyBytes': pinned['bytes'], 'sha256': pinned['sha256'], 'retries': 0}
            self.assertEqual(l.load_receipt(self._json(f.root / 'r.json', good), pinned), good)
            for bad, message in ((dict(good, url='https://example.invalid/x.gz'), 'not for the complete'),
                                 (dict(good, bodyBytes=1), 'not for the complete'),
                                 (dict(good, sha256='a' * 64), 'sha256 differs')):
                with self.assertRaisesRegex(ValueError, message):
                    l.load_receipt(self._json(f.root / 'bad.json', bad), pinned)
            out, man = f.root / 'l.xml', f.root / 'l.json'
            receipt = self._json(f.root / 'bad2.json', dict(good, url='https://example.invalid/x.gz'))
            with patch.object(l, 'build', side_effect=AssertionError('scanned')), patch('sys.stderr'):
                with self.assertRaisesRegex(ValueError, 'not for the complete'):
                    l.main(['--archive', str(f.archive), '--s-manifest', str(f.s_manifest), '--output', str(out),
                            '--manifest', str(man), '--acquisition-receipt', str(receipt)])
            self.assertFalse(out.exists())

    @staticmethod
    def _json(path, body):
        Path(path).write_text(json.dumps(body))
        return path

    def test_nesting_fails_when_s_xml_has_key_absent_from_l(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            f.s_xml.write_text(f.s_xml.read_text().replace('conf/podc/p3', 'conf/podc/zz'))
            with self.assertRaisesRegex(l.NestingError, 'S XML keys missing from L'):
                f.build()

    def test_nesting_fails_when_l_not_strict_superset(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            with self.assertRaisesRegex(l.NestingError, 'not a strict superset'):
                f.build(target_max=3, minimum=3)

    def test_nonmonotonic_rule_refused_before_scan(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            with patch.object(l, 'scan', side_effect=AssertionError('scanned')):
                with self.assertRaisesRegex(l.NestingError, 'below S cap'):
                    f.build(cap=1)
                with self.assertRaisesRegex(l.NestingError, 'year range'):
                    f.build(min_year=2006)
                with self.assertRaisesRegex(ValueError, 'collides'):
                    f.build(candidates=(('podc', ('newpodc',)),))

    def test_minimum_total_enforced(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            with self.assertRaisesRegex(ValueError, 'below minimum'):
                f.build(target_max=100, minimum=50)

    def test_archive_missing_or_mismatched_refused_without_network(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            with patch.object(s6, 'download', side_effect=AssertionError('network')), \
                 patch('urllib.request.urlopen', side_effect=AssertionError('network')):
                with self.assertRaisesRegex(FileNotFoundError, 'never downloads'):
                    l.build(Path(root) / 'absent.gz', f.s_manifest, expected=f.expected)
                bad = dict(f.expected, sha256='f' * 64)
                with self.assertRaisesRegex(RuntimeError, 'sha256 mismatch'):
                    l.build(f.archive, f.s_manifest, expected=bad)

    def test_production_rule_constants(self):
        self.assertEqual(l.PINNED_ARCHIVE['sha256'], '20e45961bec5610dc07b8e932ccd27a2387534cfa12c92a24289fe873aebe969')
        self.assertEqual((l.PER_VENUE_CAP, l.MIN_YEAR, l.MAX_YEAR), (s6.PER_VENUE_CAP, s6.MIN_YEAR, s6.MAX_YEAR))
        self.assertLessEqual(l.TARGET_MAX, 55000)
        s_rule = {'aliases': s6.VENUE_ALIASES, 'cap': s6.PER_VENUE_CAP, 'minYear': s6.MIN_YEAR, 'maxYear': s6.MAX_YEAR}
        aliases = l.l_aliases(s_rule, l.CANDIDATE_VENUES)
        l.check_rule_monotonic(s_rule, l.PER_VENUE_CAP, l.MIN_YEAR, l.MAX_YEAR, aliases)
        committed = json.loads((Path(__file__).resolve().parents[2] / 'phase6' / 'dblp-slice-manifest.v1.json').read_text())
        self.assertEqual(l.load_s_rule(committed), s_rule)


def l_build(f, archive, s_manifest, s_xml):
    return ORIGINAL_BUILD(archive, s_manifest, s_xml, expected=f.expected, candidates=CANDIDATES,
                          cap=2, target_max=7, minimum=5)


ORIGINAL_BUILD = l.build

if __name__ == '__main__':
    unittest.main(verbosity=2)

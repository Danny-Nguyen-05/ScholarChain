#!/usr/bin/env python3
"""Offline domain-slice tests; no response re-fetch or identity scoring."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import derive_focused_cs_population as d


PARENT = Path(__file__).resolve().parents[1] / 'entity-resolution/5d-demo-2026-10-20-benedikt'


def record(kind, venue):
    return {'id': 'https://openalex.org/W1', 'publication_year': 2020,
            'primary_location': {'source': {'type': kind, 'display_name': venue}}}


class DomainSliceTests(unittest.TestCase):
    def test_repository_database_label_never_establishes_cs_venue(self):
        self.assertIn('REPOSITORY_IS_NOT_CS_VENUE', d.exclusion(record('repository', 'Institutional Repositories DataBase (IRDB)')))
        self.assertIn('REPOSITORY_IS_NOT_CS_VENUE', d.exclusion(record('repository', 'Distributed Database Systems')))

    def test_missing_unknown_and_nonpublication_source_type_fail_closed(self):
        for kind in [None, '', 'unknown', 'book series', 'metadata']:
            with self.subTest(kind=kind):
                self.assertEqual(d.exclusion(record(kind, 'Database Systems')), 'UNAVAILABLE_COMPARABLE_PUBLICATION_VENUE_TYPE')

    def test_publication_type_still_requires_cs_venue_and_bounded_year(self):
        self.assertIsNone(d.exclusion(record('conference', 'Principles of Database Systems')))
        self.assertIsNone(d.exclusion(record('journal', 'Distributed Computing')))
        self.assertIsNotNone(d.exclusion(record('journal', 'Particle Physics')))
        too_old = record('conference', 'Database Systems'); too_old['publication_year'] = 2010
        self.assertIsNotNone(d.exclusion(too_old))

    @unittest.skipUnless(PARENT.is_dir(), 'actual acquired parent not available')
    def test_actual_parent_domain_slice_keeps_two_pods_and_excludes_five_repositories(self):
        original, selected, excluded = d.expected(PARENT)
        self.assertEqual([row['id'] for _, row in selected], ['https://openalex.org/W2659288104', 'https://openalex.org/W2803866544'])
        self.assertEqual(len(excluded), 5)
        self.assertTrue(all('REPOSITORY_IS_NOT_CS_VENUE' in row['reason'] for row in excluded))

    @unittest.skipUnless(PARENT.is_dir(), 'actual acquired parent not available')
    def test_exact_parent_lines_seed_and_counters_are_preserved_without_http(self):
        with tempfile.TemporaryDirectory() as td, patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('offline only')):
            output = Path(td) / 'offline-cs-fixture'
            result = d.create(PARENT, output)
            self.assertEqual(result['sources'], {'crossref': 1, 'dblp': 0, 'openalex': 2, 'orcid': 0})
            self.assertEqual(result['newHttpAttempts'], 0)
            manifest = json.loads((output / 'population-manifest.v1.json').read_bytes())
            parent_manifest = json.loads((PARENT / 'population-manifest.v1.json').read_bytes())
            self.assertEqual(manifest['sources']['crossref'], parent_manifest['sources']['crossref'])
            self.assertEqual((output / 'input/crossref.jsonl').read_bytes(), (PARENT / 'input/crossref.jsonl').read_bytes())
            source_lines = (PARENT / 'input/openalex.jsonl').read_bytes().splitlines(keepends=True)
            self.assertTrue(all(line in source_lines for line in (output / 'input/openalex.jsonl').read_bytes().splitlines(keepends=True)))
            self.assertEqual(manifest['acquisition']['cumulative'], parent_manifest['cumulative'])
            self.assertEqual(manifest['sources']['openalex']['retrievalDate'], parent_manifest['sources']['openalex']['retrievalDate'])
            self.assertEqual(manifest['sources']['openalex']['snapshotId'], 'openalex-offline-cs-fixture')
            before = (output / 'population-manifest.v1.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'never overwrite'): d.create(PARENT, output)
            self.assertEqual((output / 'population-manifest.v1.json').read_bytes(), before)

    @unittest.skipUnless(PARENT.is_dir(), 'actual acquired parent not available')
    def test_forged_slice_counters_or_snapshot_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / 'offline-cs-fixture'
            d.create(PARENT, output)
            path = output / 'population-manifest.v1.json'; original = path.read_bytes()
            mutations = ['counters', 'snapshot', 'admission', 'source-date']
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    manifest = json.loads(original)
                    if mutation == 'counters': manifest['acquisition']['newHttpAttempts'] = 1
                    if mutation == 'snapshot': manifest['sources']['openalex']['snapshotId'] = 'reused-snapshot'
                    if mutation == 'source-date': manifest['sources']['crossref']['retrievalDate'] = '2099-01-01'
                    if mutation == 'admission': manifest['heldOutAdmissionStatus'] = 'ALREADY_ELIGIBLE'
                    path.write_bytes(d.parent.enc(manifest))
                    with self.assertRaises(ValueError): d.validate(output, PARENT)
            path.write_bytes(original)
            self.assertEqual(d.validate(output, PARENT)['status'], 'VALID')


if __name__ == '__main__': unittest.main()

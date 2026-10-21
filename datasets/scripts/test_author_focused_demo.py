#!/usr/bin/env python3
"""Offline fixed-query, full-row-budget, immutable-seed and replay guard tests."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import acquire_author_focused_demo as d


class Response(io.BytesIO):
    status = 200
    headers = {'Content-Type': 'application/json'}


def profile(i):
    return {'id': f'https://openalex.org/A{i}', 'display_name': 'Synthetic person',
            'orcid': 'https://orcid.org/0000-0002-1825-0097', 'affiliations': []}


def work(i, venue='Distributed Computing'):
    return {'id': f'https://openalex.org/W{i}', 'publication_year': 2020,
            'primary_location': {'source': {'display_name': venue}},
            'authorships': [{'author': profile(1)}]}


def seed(root):
    root.mkdir()
    body = d.enc({'message': {'DOI': d.SEED_DOI, 'title': ['Synthetic seed']}}) + b'\n'
    (root / 'crossref.jsonl').write_bytes(body)
    source = {'path': 'crossref.jsonl', 'bytes': len(body), 'sha256': d.sha(body),
              'snapshotId': 'original-crossref-snapshot', 'retrievalDate': '2026-10-16'}
    manifest = d.enc({'sources': {'crossref': source}})
    (root / 'population-manifest.v1.json').write_bytes(manifest)
    return manifest, body


def history(root):
    root.mkdir()
    raw = d.enc({'results': [work(90)]})
    event = d.enc({'result': 'ok', 'responsePath': 'response.body', 'bytesRead': len(raw)}) + b'\n'
    files = {'response.body': raw, 'request-ledger.jsonl': event}
    for name, body in files.items(): (root / name).write_bytes(body)
    manifest = d.enc({'files': {name: {'bytes': len(body), 'sha256': d.sha(body)} for name, body in files.items()},
                      'observed': {'seconds': 1.5}})
    (root / 'population-manifest.v1.json').write_bytes(manifest)
    return manifest


class FocusedTests(unittest.TestCase):
    def client(self, root, bodies):
        (root / 'responses').mkdir()
        responses = iter(bodies)
        return d.Client(root, opener=lambda *a, **kw: Response(next(responses)), clock=lambda: 0, sleep=lambda _: None)

    def test_author_lookup_preserves_relevance_and_closed_fields(self):
        url = urlsplit(d.authors_url()); q = parse_qs(url.query)
        self.assertEqual((url.scheme, url.netloc, url.path), ('https', 'api.openalex.org', '/authors'))
        self.assertEqual(q, {'search': ['Michael Benedikt'], 'sort': ['relevance_score:desc'],
                             'per-page': ['5'], 'select': ['id,display_name,orcid,affiliations']})

    def test_work_filter_uses_actual_id_and_bounded_years(self):
        q = parse_qs(urlsplit(d.works_url('https://openalex.org/A17')).query)
        self.assertEqual(q['filter'], ['author.id:A17,from_publication_date:2018-01-01,to_publication_date:2024-12-31'])
        self.assertEqual(q['per-page'], ['5'])
        self.assertNotIn('search', q)
        for invalid in ['A17', 'https://evil/A17', 'https://openalex.org/A17?secret=1']:
            with self.assertRaises(ValueError): d.works_url(invalid)

    def test_author_selection_is_observed_deterministic_and_does_not_mask_orcid(self):
        rows = [(profile(9), 1), (profile(2), 1), (profile(9), 1)]
        self.assertEqual(d.selected_authors(rows), ['https://openalex.org/A2', 'https://openalex.org/A9'])
        self.assertEqual(rows[0][0]['orcid'], 'https://orcid.org/0000-0002-1825-0097')

    def test_profiles_duplicates_and_exclusions_all_consume_rows(self):
        with tempfile.TemporaryDirectory() as td:
            c = self.client(Path(td), [d.enc({'results': [profile(1)] * 5}), d.enc({'results': [work(1, 'Botany')] * 5})])
            self.assertEqual(len(c.get('authors')), 5)
            rows = c.get('works', 'https://openalex.org/A1')
            self.assertFalse(d.allowed_work(rows[0][0]))
            self.assertEqual((c.returned_records, c.author_records, c.work_records), (10, 5, 5))
            self.assertEqual((len(c.author_ids), len(c.work_ids)), (1, 1))

    def test_full_thirty_row_budget_prevents_next_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            c = self.client(Path(td), [d.enc({'results': [profile(1)] * 5})])
            c.returned_records = 30
            with self.assertRaises(d.StopBudget): c.get('authors')
            self.assertEqual(c.events, [])

    def test_oversized_server_results_fail_closed_and_are_counted(self):
        with tempfile.TemporaryDirectory() as td:
            c = self.client(Path(td), [d.enc({'results': [profile(1)] * 6})])
            with self.assertRaises(d.StopBudget): c.get('authors')
            self.assertEqual(c.returned_records, 6)
            ledger = json.loads((Path(td) / 'request-ledger.jsonl').read_bytes())
            self.assertEqual(ledger['returnedRecords'], 6)

    def test_wall_and_attempt_limits_prevent_dispatch(self):
        for limit in ['wall', 'attempts']:
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as td:
                c = self.client(Path(td), [])
                if limit == 'wall': c.start = -300
                else: c.events = [{}] * 20
                with self.assertRaises(d.StopBudget): c.get('authors')
                self.assertEqual(c.bytes, 0)

    def test_response_limit_counts_bytes_and_records_stop(self):
        with tempfile.TemporaryDirectory() as td:
            c = self.client(Path(td), [b'x' * 100])
            with patch.dict(d.BOUNDS, {'perResponseBytes': 10}), self.assertRaises(d.StopBudget): c.get('authors')
            self.assertEqual(c.bytes, 10)
            self.assertEqual(json.loads((Path(td) / 'request-ledger.jsonl').read_bytes())['bytesRead'], 10)

    def test_network_retry_is_only_one_and_attempts_are_counted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'responses').mkdir()
            calls = []
            def fail(*args, **kwargs):
                calls.append(1); raise urllib.error.URLError('offline synthetic failure')
            c = d.Client(root, opener=fail, clock=lambda: 0, sleep=lambda _: None)
            self.assertEqual(c.get('authors'), [])
            self.assertEqual(len(calls), 2)
            self.assertEqual([e['retry'] for e in c.events], [0, 1])
            self.assertTrue(c.stopped)

    def test_rate_limit_does_not_retry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'responses').mkdir()
            def limited(*args, **kwargs):
                raise urllib.error.HTTPError(d.authors_url(), 429, 'rate limit', {}, io.BytesIO(b'limited'))
            c = d.Client(root, opener=limited, clock=lambda: 0, sleep=lambda _: None)
            self.assertEqual(c.get('authors'), [])
            self.assertEqual(len(c.events), 1)
            self.assertEqual(c.bytes, 7)

    def test_abstract_and_bad_native_ids_are_not_ingested(self):
        for row in [{**profile(1), 'abstract_inverted_index': {}}, {**profile(1), 'id': 'https://evil/A1'}]:
            with self.subTest(row=row), tempfile.TemporaryDirectory() as td:
                c = self.client(Path(td), [d.enc({'results': [row]})])
                self.assertEqual(c.get('authors'), [])
                self.assertTrue(c.stopped)

    def create(self, root):
        seed_bytes, line = seed(root / 'seed')
        history_bytes = history(root / 'prior')
        approval = d.enc({'limits': {'returnedMetadataRecordsIncludingProfilesWorksDuplicatesAndExcluded': 30,
                                    'httpAttemptsIncludingRetries': 20, 'responseBytes': 8 * 1024 * 1024,
                                    'wallSeconds': 300, 'credentials': False, 'paidData': False},
                          'originalLiveApprovalUnchanged': True})
        plan = {'schemaVersion': d.PLAN_VERSION, 'stageId': 'fixture-stage', 'authorSearch': d.AUTHOR_NAME,
                'seedDoi': d.SEED_DOI, 'authorSelect': d.AUTHOR_FIELDS, 'recordsPerRequest': 5,
                'maxReturnedRecordsIncludingAuthorLookups': 30, 'seedPopulationManifestSha256': d.sha(seed_bytes),
                'previousStageSha256': d.sha(history_bytes), 'approvalReceiptSha256': d.sha(approval), 'seedLineSha256': d.sha(line)}
        (root / 'plan.json').write_bytes(d.enc(plan)); (root / 'approval.json').write_bytes(approval)
        responses = iter([d.enc({'results': [profile(1)]}), d.enc({'results': [work(1), work(2, 'Botany')]})])
        cls = d.Client
        def factory(out, **kwargs):
            return cls(out, opener=lambda *a, **k: Response(next(responses)), clock=lambda: kwargs['start'], sleep=lambda _: None, **kwargs)
        with patch.object(d, 'Client', factory):
            result = d.publish(root / 'fixture-stage', root / 'plan.json', root / 'approval.json', root / 'seed', root / 'prior')
        return result, root / 'fixture-stage', line

    def test_publish_replays_exact_seed_and_preserves_cumulative_counts(self):
        with tempfile.TemporaryDirectory() as td:
            result, stage, line = self.create(Path(td))
            self.assertEqual(result['status'], 'VALID')
            self.assertEqual((stage / 'input/crossref.jsonl').read_bytes(), line)
            manifest = json.loads((stage / 'population-manifest.v1.json').read_bytes())
            self.assertEqual(manifest['sources']['crossref']['snapshotId'], 'original-crossref-snapshot')
            self.assertEqual(manifest['sources']['crossref']['retrievalDate'], '2026-10-16')
            self.assertEqual(result['observed']['returnedMetadataRecordsIncludingDuplicatesExcluded'], 3)
            self.assertEqual(result['cumulative']['httpAttemptsAcrossStages'], 3)
            self.assertEqual(result['cumulative']['distinctWorkIdsAcrossStages'], 3)
            self.assertEqual(result['cumulative']['returnedMetadataRecordsAcrossStages'], 4)
            self.assertEqual(result['sources']['openalex'], 1)
            self.assertEqual(json.loads((stage / 'lookup/authors.jsonl').read_bytes())['orcid'], profile(1)['orcid'])

    def test_approval_hash_and_fixed_limits_checked_before_http(self):
        receipt = d.enc({'limits': {}})
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            d.validate_approval({'approvalReceiptSha256': 'a' * 64}, receipt)
        with self.assertRaisesRegex(ValueError, 'fixed limits'):
            d.validate_approval({'approvalReceiptSha256': d.sha(receipt)}, receipt)

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            result, stage, _ = self.create(Path(td))
            before = (stage / 'population-manifest.v1.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'never overwrite'):
                d.publish(stage, stage / 'proof/plan.json', stage / 'proof/user-approval.json', Path(td) / 'seed', Path(td) / 'prior')
            self.assertEqual((stage / 'population-manifest.v1.json').read_bytes(), before)

    def test_changed_retained_response_or_extra_file_is_rejected(self):
        for mutation in ['response', 'extra']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as td:
                _, stage, _ = self.create(Path(td))
                if mutation == 'response': (stage / 'responses/001-authors.body').write_bytes(b'{}')
                else: (stage / 'extra.txt').write_text('extra')
                with self.assertRaises(ValueError): d.validate(stage)


if __name__ == '__main__': unittest.main()

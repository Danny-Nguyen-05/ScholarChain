#!/usr/bin/env python3
"""Offline fixed-scope acquisition and provenance regression tests; no HTTP."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import acquire_rice_team_demo as d


class Response(io.BytesIO):
    status = 200
    headers = {'Content-Type': 'application/json'}


def work(i, kind='journal', venue='Distributed Computing'):
    return {'id': f'https://openalex.org/W{i}', 'publication_year': 2020,
            'primary_location': {'source': {'display_name': venue, 'type': kind}},
            'authorships': [{'author': {'id': a, 'display_name': 'Synthetic name', 'orcid': None}} for a in d.AUTHOR_IDS]}


def seed(root):
    root.mkdir()
    rows = [{**work(i), 'id': native} for i, native in enumerate(d.SEED_IDS, 1)]
    lines = [d.enc(row) + b'\n' for row in rows]
    body = b''.join(lines)
    (root / 'works.jsonl').write_bytes(body)
    source = {'path': 'works.jsonl', 'records': 2, 'sha256': d.sha(body),
              'snapshotId': 'openalex-original', 'retrievalDate': '2026-10-17'}
    manifest = d.enc({'sources': {'openalex': source}})
    (root / 'population-manifest.v1.json').write_bytes(manifest)
    return manifest, lines


def prior(root):
    root.mkdir()
    raw = d.enc({'results': [work(90)]})
    ledger = d.enc({'result': 'ok', 'responsePath': 'response.body', 'bytesRead': len(raw)}) + b'\n'
    files = {'response.body': raw, 'request-ledger.jsonl': ledger}
    for name, body in files.items(): (root / name).write_bytes(body)
    manifest = d.enc({'files': {k: {'bytes': len(v), 'sha256': d.sha(v)} for k, v in files.items()}, 'observed': {'seconds': 1.5}})
    (root / 'population-manifest.v1.json').write_bytes(manifest)
    return manifest


class RiceTests(unittest.TestCase):
    def client(self, root, bodies):
        (root / 'responses').mkdir()
        responses = iter(bodies)
        return d.Client(root, opener=lambda *a, **kw: Response(next(responses)), clock=lambda: 0, sleep=lambda _: None)

    def test_fixed_actual_author_queries_have_closed_fields_sort_and_years(self):
        for author in d.AUTHOR_IDS:
            parsed = urlsplit(d.works_url(author))
            self.assertEqual((parsed.scheme, parsed.netloc, parsed.path), ('https', 'api.openalex.org', '/works'))
            self.assertEqual(parse_qs(parsed.query), {'filter': [f'author.id:{author.rsplit("/", 1)[-1]},from_publication_date:2018-01-01,to_publication_date:2024-12-31'],
                                                     'per-page': ['15'], 'sort': ['cited_by_count:desc'], 'select': [d.WORK_FIELDS]})
        for author in ['https://openalex.org/A1', 'https://evil/A5085731856', 'A5085731856']:
            with self.assertRaises(ValueError): d.works_url(author)

    def test_repository_oversized_team_and_non_cs_are_excluded_without_mutation(self):
        self.assertTrue(d.allowed_work(work(1)))
        for row in [work(1, kind='repository', venue='Institutional Repositories Database'), work(1, venue='Botany'),
                    {**work(1), 'authorships': work(1)['authorships'] * 9}]:
            before = d.enc(row)
            self.assertFalse(d.allowed_work(row)); self.assertEqual(d.enc(row), before)

    def test_duplicate_and_excluded_rows_consume_all_thirty_without_refill(self):
        with tempfile.TemporaryDirectory() as td:
            c = self.client(Path(td), [d.enc({'results': [work(1)] * 15}), d.enc({'results': [work(2, venue='Botany')] * 15})])
            c.get(d.AUTHOR_IDS[0]); c.get(d.AUTHOR_IDS[1])
            self.assertEqual(c.returned_records, 30); self.assertEqual(len(c.work_ids), 2)
            with self.assertRaises(d.history.StopBudget): c.get(d.AUTHOR_IDS[0])
            self.assertEqual(len(c.events), 2)

    def test_server_overdelivery_is_counted_then_refused(self):
        with tempfile.TemporaryDirectory() as td:
            c = self.client(Path(td), [d.enc({'results': [work(1)] * 16})])
            with self.assertRaises(d.history.StopBudget): c.get(d.AUTHOR_IDS[0])
            self.assertEqual(c.returned_records, 16)
            self.assertEqual(json.loads((Path(td) / 'request-ledger.jsonl').read_bytes())['returnedRecords'], 16)

    def test_wall_and_attempt_limits_prevent_http(self):
        for mode in ['wall', 'attempts']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                c = self.client(Path(td), [])
                if mode == 'wall': c.start = -300
                else: c.events = [{}] * 20
                with self.assertRaises(d.history.StopBudget): c.get(d.AUTHOR_IDS[0])
                self.assertEqual(c.bytes, 0)

    def test_byte_cap_records_consumed_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            c = self.client(Path(td), [b'x' * 100])
            with patch.dict(d.BOUNDS, {'perResponseBytes': 10}), self.assertRaises(d.history.StopBudget): c.get(d.AUTHOR_IDS[0])
            self.assertEqual(c.bytes, 10)

    def test_network_retries_once_without_adding_targets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'responses').mkdir()
            def fail(*a, **k): raise urllib.error.URLError('synthetic offline failure')
            c = d.Client(root, opener=fail, clock=lambda: 0, sleep=lambda _: None)
            self.assertEqual(c.get(d.AUTHOR_IDS[0]), [])
            self.assertEqual([x['retry'] for x in c.events], [0, 1]); self.assertTrue(c.stopped)

    def test_rate_limit_does_not_retry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'responses').mkdir()
            def limited(*a, **k): raise urllib.error.HTTPError(d.works_url(d.AUTHOR_IDS[0]), 429, 'limited', {}, io.BytesIO(b'limited'))
            c = d.Client(root, opener=limited, clock=lambda: 0, sleep=lambda _: None)
            c.get(d.AUTHOR_IDS[0]); self.assertEqual(len(c.events), 1); self.assertTrue(c.stopped)

    def test_unexpected_fulltext_or_id_fails_closed(self):
        for row in [{**work(1), 'abstract_inverted_index': {}}, {**work(1), 'id': 'https://evil/W1'}]:
            with self.subTest(row=row), tempfile.TemporaryDirectory() as td:
                c = self.client(Path(td), [d.enc({'results': [row]})])
                self.assertEqual(c.get(d.AUTHOR_IDS[0]), []); self.assertTrue(c.stopped)

    def create(self, root):
        seed_bytes, lines = seed(root / 'original')
        history_bytes = prior(root / '5d-demo-2026-10-20-benedikt')
        approval = d.enc({'limits': {'returnedWorkRowsIncludingDuplicatesAndExcluded': 30, 'httpAttemptsIncludingRetries': 20,
                                    'responseBytes': 8 * 1024 * 1024, 'wallSeconds': 300, 'credentials': False, 'paidData': False},
                          'originalLiveApprovalUnchanged': True})
        plan = {'schemaVersion': d.PLAN_VERSION, 'stageId': 'synthetic-stage', 'authorIds': d.AUTHOR_IDS,
                'recordsPerRequest': 15, 'sort': 'cited_by_count:desc', 'seedPopulationManifestSha256': d.sha(seed_bytes),
                'previousStageSha256': d.sha(history_bytes), 'approvalReceiptSha256': d.sha(approval), 'seedLinesSha256': [d.sha(x) for x in lines]}
        (root / 'plan.json').write_bytes(d.enc(plan)); (root / 'approval.json').write_bytes(approval)
        real_client = d.Client
        changed = work(1); changed['authorships'][0]['author']['orcid'] = 'https://orcid.org/0000-0002-1825-0097'
        bodies = iter([d.enc({'results': [changed, work(2, kind='repository')]}), d.enc({'results': [changed, work(3)]})])
        def factory(out, **kwargs):
            return real_client(out, opener=lambda *a, **k: Response(next(bodies)), clock=lambda: kwargs['start'], sleep=lambda _: None, **kwargs)
        with patch.object(d, 'Client', factory):
            result = d.publish(root / 'synthetic-stage', root / 'plan.json', root / 'approval.json', root / 'original', root / '5d-demo-2026-10-20-benedikt')
        return result, root / 'synthetic-stage', lines

    def test_publish_fresh_only_preserves_seed_provenance_orcid_and_cumulative(self):
        with tempfile.TemporaryDirectory() as td:
            result, root, lines = self.create(Path(td))
            self.assertEqual(result['status'], 'VALID')
            self.assertEqual(result['observed']['returnedWorkRecordsIncludingDuplicatesExcluded'], 4)
            self.assertEqual(result['sources']['openalex'], 2)
            self.assertEqual(result['cumulative']['returnedWorkRecordsAcrossStages'], 5)
            self.assertEqual(result['cumulative']['httpAttemptsAcrossStages'], 3)
            m = json.loads((root / 'population-manifest.v1.json').read_bytes())
            self.assertEqual(m['seed']['originalSource']['retrievalDate'], '2026-10-17')
            self.assertEqual(m['seed']['originalSource']['snapshotId'], 'openalex-original')
            self.assertEqual((root / 'seed/selection-only.jsonl').read_bytes(), b''.join(lines))
            ingested = [json.loads(x) for x in (root / 'input/openalex.jsonl').read_bytes().splitlines()]
            self.assertFalse(set(d.SEED_IDS) & {x['id'] for x in ingested})
            self.assertEqual(ingested[0]['authorships'][0]['author']['orcid'], 'https://orcid.org/0000-0002-1825-0097')
            self.assertFalse((root / 'previous-stage').exists())

    def test_invalid_approval_rejected_before_output_or_http(self):
        body = d.enc({'limits': {}})
        with self.assertRaises(ValueError): d.validate_approval({'approvalReceiptSha256': 'a' * 64}, body)
        with self.assertRaises(ValueError): d.validate_approval({'approvalReceiptSha256': d.sha(body)}, body)

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            _, root, _ = self.create(Path(td)); before = (root / 'population-manifest.v1.json').read_bytes()
            with self.assertRaises(ValueError): d.publish(root, root / 'proof/plan.json', root / 'proof/user-approval.json', Path(td) / 'original', Path(td) / '5d-demo-2026-10-20-benedikt')
            self.assertEqual((root / 'population-manifest.v1.json').read_bytes(), before)

    def test_corrupt_response_extra_file_or_prior_history_rejected(self):
        for mode in ['response', 'extra', 'prior']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                _, root, _ = self.create(Path(td))
                if mode == 'response': (root / 'responses/001-works.body').write_bytes(b'{}')
                elif mode == 'extra': (root / 'unexpected.txt').write_text('extra')
                else: (root.parent / '5d-demo-2026-10-20-benedikt/response.body').write_bytes(b'{}')
                with self.assertRaises(ValueError): d.validate(root)


if __name__ == '__main__': unittest.main()

#!/usr/bin/env python3
"""Offline mocked bounds/provenance tests; no network or human labels."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
import acquire_screened_demo as d


class Response(io.BytesIO):
    status = 200
    headers = {'Content-Type': 'application/json'}


def work(i, author=None, orcid=None, venue='Distributed Computing'):
    author = author or 'https://openalex.org/A' + str(i)
    return {'id': 'https://openalex.org/W' + str(i), 'title': 'Synthetic fixture only', 'publication_year': 2020,
            'primary_location': {'source': {'display_name': venue}},
            'authorships': [{'author': {'id': author, 'orcid': orcid}, 'institutions': [{'id': 'https://openalex.org/I1'}]}]}


def mock_context(root):
    root.mkdir()
    files = {'openalex/works.jsonl': d.enc(work(99)) + b'\n',
             'crossref/works.jsonl': b'{}\n' * 14, 'orcid/records.jsonl': b'',
             'dblp/records.xml': b'<dblp/>\n', 'request-ledger.jsonl': b''}
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    manifest = {'files': {name: {'sha256': d.sha(data), 'bytes': len(data)} for name, data in files.items()},
                'observed': {'seconds': 0}}
    body = d.enc(manifest)
    (root / 'population-manifest.v1.json').write_bytes(body)
    return body


class ScreenedTests(unittest.TestCase):
    def client(self, root, body=b'{"results":[]}'):
        (root / 'responses').mkdir()
        return d.Client(root, opener=lambda *a, **kw: Response(body), clock=lambda: 0, sleep=lambda _: None)

    def test_topic_discovery_keeps_relevance_order_without_changing_bounds(self):
        from urllib.parse import parse_qs, urlsplit
        for query in d.TOPICS:
            parts = urlsplit(d.discovery_url(query))
            params = parse_qs(parts.query)
            self.assertEqual((parts.scheme, parts.netloc, parts.path), ('https', 'api.openalex.org', '/works'))
            self.assertEqual(params['search'], [query])
            self.assertEqual(params['sort'], ['relevance_score:desc'])
            self.assertEqual(params['filter'], ['from_publication_date:2018-01-01,to_publication_date:2024-12-31'])
            self.assertEqual(params['per-page'], ['5'])
            self.assertEqual(params['select'], [d.FIELDS])
            self.assertEqual(set(params), {'search', 'sort', 'filter', 'per-page', 'select'})

    def test_immutable_legacy_population_uses_exact_retained_script_order(self):
        root = Path(__file__).resolve().parents[1] / 'entity-resolution/5d-demo-2026-10-20-screened'
        manifest = json.loads((root / 'population-manifest.v1.json').read_bytes())
        original_manifest = (root / 'population-manifest.v1.json').read_bytes()
        result = d.validate(root)
        self.assertEqual(result['discoveryOrdering'], 'publication_date:asc')
        self.assertEqual(result['queryPlanVersion'], 'legacy-exact-executed-script')
        self.assertEqual((root / 'population-manifest.v1.json').read_bytes(), original_manifest)
        script = (root / manifest['executedScript']['path']).read_bytes()
        changed = dict(manifest, executedScript={'sha256': d.sha(script + b'changed')})
        with self.assertRaisesRegex(ValueError, 'unrecognized'):
            d.retained_discovery_order(changed, script + b'changed')

    def test_unknown_order_or_missing_new_version_is_rejected(self):
        script = b'synthetic script bytes'
        base = {'executedScript': {'sha256': d.sha(script)}}
        for addition in [{}, {'queryPlanVersion': d.QUERY_PLAN_VERSION, 'discoveryOrdering': 'publication_date:asc'},
                         {'queryPlanVersion': 'unknown', 'discoveryOrdering': d.DISCOVERY_ORDER}]:
            with self.subTest(addition=addition), self.assertRaisesRegex(ValueError, 'unrecognized'):
                d.retained_discovery_order({**base, **addition}, script)
        self.assertEqual(d.retained_discovery_order({**base, 'queryPlanVersion': d.QUERY_PLAN_VERSION, 'discoveryOrdering': d.DISCOVERY_ORDER}, script), 'relevance_score:desc')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            d.retained_discovery_order({**base, 'queryPlanVersion': d.QUERY_PLAN_VERSION, 'discoveryOrdering': d.DISCOVERY_ORDER}, script + b'changed')
        with self.assertRaises(ValueError):
            d._discovery_url(d.TOPICS[0], 'cited_by_count:desc')

    def test_fixed_query_plan_and_screen_binding(self):
        screen = b'no safe existing seeds'
        plan = {'schemaVersion': 'scholarchain.topic-demo-plan.v1', 'screenReceiptSha256': d.sha(screen), 'queries': list(d.TOPICS)}
        d.validate_plan(plan, screen)
        for changed in [{**plan, 'queries': ['other']}, {**plan, 'screenReceiptSha256': 'a' * 64}]:
            with self.assertRaises(ValueError): d.validate_plan(changed, screen)
        with self.assertRaises(ValueError): d.discovery_url('other')

    def test_selection_uses_observed_missing_orcid_affiliation_and_domain(self):
        good = [(work(i), 1) for i in range(1, 10)]
        candidates = good + [(work(10, orcid='https://orcid.org/0000'), 1), (work(11, venue='Botany'), 1)]
        empty = work(12); empty['authorships'][0]['institutions'] = []
        candidates.append((empty, 1))
        expected = sorted([f'https://openalex.org/A{i}' for i in range(1, 10)], key=lambda x: (d.sha(x.encode()), x))[:4]
        self.assertEqual(d.choose_authors(candidates), expected)
        self.assertEqual(d.choose_authors(list(reversed(candidates))), expected)

    def test_excluded_records_still_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            body = d.enc({'results': [work(1, venue='Botany'), work(2)]})
            client = self.client(root, body)
            rows = client.get(query=d.TOPICS[0])
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(client.unique), 2)
            self.assertFalse(d.allowed(rows[0][0]))
            self.assertEqual(client.bytes, len(body))

    def test_request_and_wall_caps_prevent_dispatch(self):
        for kind in ['attempt', 'wall']:
            with tempfile.TemporaryDirectory() as td:
                client = self.client(Path(td))
                if kind == 'attempt': client.events = [{}] * 20
                else: client.start = -300
                with self.assertRaises(d.StopBudget): client.get(query=d.TOPICS[0])
                self.assertEqual(client.bytes, 0)

    def test_response_byte_limit_fails_closed_and_counts(self):
        with tempfile.TemporaryDirectory() as td:
            client = self.client(Path(td), b'x' * 100)
            with patch.dict(d.BOUNDS, {'perResponseBytes': 10}):
                with self.assertRaises(d.StopBudget): client.get(query=d.TOPICS[0])
            self.assertEqual(client.bytes, 10)
            self.assertEqual(json.loads((Path(td) / 'request-ledger.jsonl').read_text())['bytesRead'], 10)

    def test_schema_and_requested_record_count_fail_closed(self):
        for value in [{'bad': []}, {'results': [work(i) for i in range(1, 7)]}]:
            with tempfile.TemporaryDirectory() as td:
                client = self.client(Path(td), d.enc(value))
                if 'results' in value:
                    with self.assertRaises(d.StopBudget): client.get(query=d.TOPICS[0])
                else:
                    self.assertEqual(client.get(query=d.TOPICS[0]), [])
                    self.assertTrue(client.stopped)

    def test_invalid_author_or_query_has_zero_attempts(self):
        with tempfile.TemporaryDirectory() as td:
            client = self.client(Path(td))
            for kwargs in [{'author': 'https://evil/A1'}, {'query': 'other'}, {}]:
                with self.assertRaises(ValueError): client.get(**kwargs)
            self.assertEqual(client.events, [])

    def test_http_errors_count_bytes_and_retry_only_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'responses').mkdir()
            calls = []
            def opener(req, **kwargs):
                calls.append(req.full_url)
                raise urllib.error.HTTPError(req.full_url, 503, 'unavailable', {}, io.BytesIO(b'failure'))
            client = d.Client(root, opener=opener, clock=lambda: 0, sleep=lambda _: None)
            self.assertEqual(client.get(query=d.TOPICS[0]), [])
            self.assertEqual(len(calls), 2)
            self.assertEqual(client.bytes, 14)
            self.assertTrue(client.stopped)
            self.assertEqual([x['retry'] for x in client.events], [0, 1])

    def test_full_mock_acquisition_preserves_script_before_http_and_caps_all_records(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            context = root / 'context'
            manifest = mock_context(context)
            screen = root / 'screen.json'; screen.write_bytes(b'{"existingSafeSeeds":0}')
            plan = root / 'plan.json'; plan.write_bytes(d.enc({'schemaVersion': 'scholarchain.topic-demo-plan.v1', 'screenReceiptSha256': d.sha(screen.read_bytes()), 'contextPopulationSha256': d.sha(manifest), 'queries': list(d.TOPICS)}))
            approval = root / 'approval.json'; approval.write_bytes(b'{"syntheticTestOnly":true}')
            output = root / 'out'
            cls = d.Client
            calls = []
            def opener(req, **kwargs):
                self.assertEqual((output / 'scripts/acquire_screened_demo.py').read_bytes(), Path(d.__file__).read_bytes())
                self.assertTrue((output / 'proof/user-approval.json').exists())
                i = len(calls); calls.append(req.full_url)
                return Response(d.enc({'results': [work(100 + i * 5 + j) for j in range(5)]}))
            with patch.object(d, 'Client', lambda where, start=None: cls(where, opener=opener, sleep=lambda _: None, start=start)):
                result = d.publish(output, plan, screen, approval, context)
            self.assertEqual(result['observed']['httpAttempts'], 6)
            self.assertEqual(result['observed']['distinctReturnedWorksIncludingExcluded'], 30)
            self.assertEqual(result['sources']['openalex'], 31)
            self.assertEqual(result['sources']['crossref'], 14)
            self.assertEqual(result['cumulative']['distinctReturnedWorksAcrossStages'], 30)
            self.assertEqual(result['admission'], 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING')
            self.assertEqual(result['discoveryOrdering'], 'relevance_score:desc')
            self.assertEqual(result['queryPlanVersion'], d.QUERY_PLAN_VERSION)
            self.assertEqual((output / 'context/openalex/works.jsonl').read_bytes(), (context / 'openalex/works.jsonl').read_bytes())
            body = (output / 'input/openalex.jsonl').read_bytes()
            (output / 'input/openalex.jsonl').write_bytes(body + b'{}\n')
            with self.assertRaisesRegex(ValueError, 'hash differs'): d.validate(output)

    def test_rerun_preserves_prior_failed_search_and_deduplicates_context_counters(self):
        populations = Path(__file__).resolve().parents[1] / 'entity-resolution'
        context = populations / '5d-demo-2026-10-17-openalex'
        previous = populations / '5d-demo-2026-10-20-screened'
        prior = d.history_facts(previous)
        self.assertEqual((len(prior['ids']), prior['attempts'], prior['bytes']), (30, 9, 215344))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            screen = root / 'screen.json'; screen.write_bytes(b'{"syntheticScreen":true}')
            plan = root / 'plan.json'; plan.write_bytes(d.enc({
                'schemaVersion': 'scholarchain.topic-demo-plan.v1', 'queries': list(d.TOPICS),
                'screenReceiptSha256': d.sha(screen.read_bytes()),
                'contextPopulationSha256': d.sha((context / 'population-manifest.v1.json').read_bytes()),
                'previousStageSha256': d.sha((previous / 'population-manifest.v1.json').read_bytes())}))
            approval = root / 'approval.json'; approval.write_bytes(b'{"syntheticTestOnly":true}')
            output = root / 'new'
            cls = d.Client
            calls = []
            def opener(req, **kwargs):
                calls.append(req.full_url)
                return Response(b'{"results":[]}')
            with patch.object(d, 'Client', lambda where, start=None: cls(where, opener=opener, sleep=lambda _: None, start=start)):
                result = d.publish(output, plan, screen, approval, context, previous)
            self.assertEqual(len(calls), 2)
            self.assertEqual(result['observed']['distinctReturnedWorksIncludingExcluded'], 0)
            self.assertEqual(result['cumulative']['previousStageDistinctReturnedWorks'], 30)
            self.assertEqual(result['cumulative']['distinctReturnedWorksAcrossStages'], 30)
            self.assertEqual(result['cumulative']['httpAttemptsAcrossStages'], 11)
            self.assertEqual(result['cumulative']['responseBytesAcrossStages'], 215344 + 28)
            self.assertEqual((output / 'previous-stage/population-manifest.v1.json').read_bytes(), (previous / 'population-manifest.v1.json').read_bytes())
            self.assertEqual(result['discoveryOrdering'], 'relevance_score:desc')

    def test_planned_previous_stage_cannot_be_omitted(self):
        populations = Path(__file__).resolve().parents[1] / 'entity-resolution'
        context = populations / '5d-demo-2026-10-17-openalex'
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            screen = root / 'screen.json'; screen.write_bytes(b'{}')
            plan = root / 'plan.json'; plan.write_bytes(d.enc({
                'schemaVersion': 'scholarchain.topic-demo-plan.v1', 'queries': list(d.TOPICS),
                'screenReceiptSha256': d.sha(screen.read_bytes()),
                'contextPopulationSha256': d.sha((context / 'population-manifest.v1.json').read_bytes()),
                'previousStageSha256': 'a' * 64}))
            approval = root / 'approval.json'; approval.write_bytes(b'{}')
            with patch.object(d, 'Client') as client, self.assertRaisesRegex(ValueError, 'must be supplied'):
                d.publish(root / 'new', plan, screen, approval, context)
            client.assert_not_called()
            self.assertFalse((root / 'new').exists())

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, 'never overwrite'):
                d.publish(Path(td), Path('unused'), Path('unused'), Path('unused'), Path('unused'))


if __name__ == '__main__':
    unittest.main()

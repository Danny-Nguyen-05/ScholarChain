#!/usr/bin/env python3
"""Offline 5D supplement bounds/provenance tests; no labels or model calls."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import acquire_demo_supplement as d

class Response(io.BytesIO):
    status=200
    headers={"Content-Type":"application/json"}

class DemoTests(unittest.TestCase):
    def client(self, root, body):
        (root/'responses').mkdir()
        return d.Client(root, opener=lambda *args,**kwargs:Response(body))
    def test_request_byte_and_record_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            body=b'{"results":[{"id":"https://openalex.org/W123"}]}'
            c=self.client(Path(tmp),body)
            self.assertEqual(c.get('https://api.openalex.org/works','doi-seed-match',6)[0][0]['id'],'https://openalex.org/W123')
            self.assertEqual(len(c.unique),1)
            self.assertEqual(c.bytes,len(body))
            self.assertEqual(json.loads((Path(tmp)/'request-ledger.jsonl').read_text())['sha256'],d.sha(body))
    def test_foreign_host_refused_before_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.client(Path(tmp),b'{}')
            with self.assertRaises(ValueError):c.get('https://example.org/works','doi-seed-match',6)
            self.assertEqual(len(c.events),0)
    def test_request_cap_prevents_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.client(Path(tmp),b'{}');c.events=[{}]*20
            with self.assertRaises(d.StopBudget):c.get('https://api.openalex.org/works','doi-seed-match',6)
    def test_response_cap_counts_excluded_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.client(Path(tmp),b'x'*100)
            with patch.dict(d.BOUNDS,{'responseBytes':10}):self.assertEqual(c.get('https://api.openalex.org/works','doi-seed-match',6),[])
            self.assertEqual(c.bytes,10);self.assertTrue(c.stopped)
    def test_unexpected_record_count_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.client(Path(tmp),json.dumps({'results':[{'id':'https://openalex.org/W'+str(n)} for n in range(7)]}).encode())
            self.assertEqual(c.get('https://api.openalex.org/works','doi-seed-match',6),[])
            self.assertTrue(c.stopped)
    def test_seed_population_is_real_and_source_script_is_retained(self):
        root=Path(__file__).resolve().parents[1]/'entity-resolution/5d-demo-2026-10-17-seeds'
        result=d.validate(root)
        self.assertEqual(result['records'],{'crossref':14,'openalex':0,'dblp':0,'orcid':0})
        self.assertEqual(result['observed']['httpAttempts'],0)
        self.assertEqual(result['admission'],'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING')
    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'never overwrite'):d.publish(Path(tmp),Path('unused'))

if __name__=='__main__':unittest.main()

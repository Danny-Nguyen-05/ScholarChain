#!/usr/bin/env python3
"""Deterministic acquisition/validation tests. No network or human labels."""
import io
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import acquire_resolution_population as a
import filter_resolution_population as f
import validate_resolution_population as v


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}


class PopulationTests(unittest.TestCase):
    def test_doi_literal_normalization_preserves_suffix(self):
        self.assertEqual(a.canonical_doi("https://doi.org/10.9999/Encoded%2Fvalue?x=1"), "10.9999/encoded%2fvalue?x=1")
        self.assertIsNone(a.canonical_doi("made-up"))

    def test_selection_requires_venue_year_authors_title(self):
        row = {"DOI": "10.9999/good", "title": ["A Distributed System"], "container-title": ["Proceedings of ACM SIGMOD"], "author": [{"family": "Smith"}], "published-print": {"date-parts": [[2020]]}}
        bad_venue = dict(row, DOI="10.9999/wrong-venue", **{"container-title": ["Ecology"]})
        bad_year = dict(row, DOI="10.9999/wrong-year", **{"published-print": {"date-parts": [[2017]]}})
        self.assertEqual(a.choose_records([bad_venue, row, bad_year, row], "sigmod", 2020), [row])

    def test_selection_is_deterministic_under_input_reordering(self):
        rows = [{"DOI": f"10.9999/{n}", "title": ["Record"], "container-title": ["VLDB"], "author": [{"family": "Author"}], "issued": {"date-parts": [[2021]]}} for n in range(25)]
        self.assertEqual(a.choose_records(rows, "vldb", 2021), a.choose_records(list(reversed(rows)), "vldb", 2021))
        self.assertEqual(len(a.choose_records(rows, "vldb", 2021)), 10)

    def test_client_counts_real_bytes_and_retains_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "responses").mkdir()
            client = a.Client(root, opener=lambda *args, **kwargs: Response(b'{"value":1}'))
            result = client.get("crossref", "https://api.crossref.org/works/10.9999/test")
            self.assertEqual(result[0], {"value": 1})
            self.assertEqual(client.byte_count, 11)
            self.assertEqual(client.events[0]["sha256"], a.digest(b'{"value":1}'))
            self.assertEqual(client.attempts["crossref"], 1)

    def test_total_request_bound_prevents_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = a.Client(Path(tmp), opener=lambda *args, **kwargs: self.fail("must not dispatch"))
            client.attempts["crossref"] = a.BOUNDS["totalAttempts"]
            with self.assertRaises(a.BoundReached):
                client.get("crossref", "https://api.crossref.org/works")

    def test_response_cap_never_reads_past_allowance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "responses").mkdir()
            response = Response(b"x" * 100)
            client = a.Client(root, opener=lambda *args, **kwargs: response)
            with patch.dict(a.BOUNDS, {"totalBytes": 20}):
                self.assertIsNone(client.get("crossref", "https://api.crossref.org/works"))
            self.assertEqual(client.byte_count, 20)
            self.assertIn("crossref", client.disabled)
            self.assertEqual((root / "responses/0001-crossref.body").stat().st_size, 20)

    def test_challenge_not_ingested_and_disables_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "responses").mkdir()
            class Challenge(Response):
                status = 202
            client = a.Client(root, opener=lambda *args, **kwargs: Challenge(b"<html>challenge</html>"))
            self.assertIsNone(client.get("dblp", "https://dblp.org/search/publ/api"))
            self.assertIsNone(client.get("dblp", "https://dblp.org/search/publ/api"))
            self.assertEqual(client.attempts["dblp"], 1)

    def test_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "already exists"):
                a.acquire(Path(tmp))

    def test_domain_filter_rejects_medical_and_accepts_distributed_data_venues(self):
        for venue in ("Circulation", "The Lancet", "New England Journal of Medicine", ""):
            self.assertIsNone(f.CS_VENUE.search(venue))
        for venue in ("Proceedings of the VLDB Endowment", "ACM Symposium on Cloud Computing (SoCC)", "Operating Systems Design and Implementation"):
            self.assertIsNotNone(f.CS_VENUE.search(venue))

    def test_final_real_population_integrity(self):
        population = Path(__file__).resolve().parents[1] / "entity-resolution/5c-2026-10-16-v3"
        result = v.validate(population)
        self.assertEqual(result["records"], {"dblp": 0, "openalex": 446, "crossref": 10, "orcid": 8})
        self.assertEqual(result["humanReviews"], 0)

    def test_validator_rejects_tampered_source_bytes(self):
        population = Path(__file__).resolve().parents[1] / "entity-resolution/5c-2026-10-16-v3"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "mutated"
            shutil.copytree(population, output)
            with (output / "crossref/works.jsonl").open("ab") as file:
                file.write(b"\n")
            with self.assertRaisesRegex(ValueError, "hash/size mismatch"):
                v.validate(output)

    def test_validator_rejects_unmanifested_file(self):
        population = Path(__file__).resolve().parents[1] / "entity-resolution/5c-2026-10-16-v3"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "mutated"
            shutil.copytree(population, output)
            (output / "invented-labels.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "file inventory"):
                v.validate(output)


if __name__ == "__main__":
    unittest.main()

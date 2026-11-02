#!/usr/bin/env python3
"""Offline public-only fixtures; never invoke budget execution or read real records."""
import copy
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1] / 'publication_evidence.py'
spec = importlib.util.spec_from_file_location('publication_evidence', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ADDRESS = 'synthetic@example.invalid'


class PublicationFeatures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='publication helper ')
        self.repo = Path(self.temp.name).resolve()
        self.repo.chmod(0o700)
        self.evidence = self.repo / m.EVIDENCE
        self.evidence.mkdir(parents=True, mode=0o700)
        self.staging = m.EVIDENCE + '/12d-publication-input-fixture'
        (self.repo / self.staging / 'artifacts').mkdir(parents=True, mode=0o700)
        (self.repo / self.staging / 'suffixes').mkdir(mode=0o700)
        self.root = m.EVIDENCE + '/12d-publication-output-fixture'
        self.request_rel = self.staging + '/request.json'
        self.freeze_rel = self.root + '.freeze.json'
        self.receipt_rel = m.EVIDENCE + '/12d-publication-scan-fixture.json'
        self.bind = {'gate_sha256': 'a' * 64, 'operation': 'fixture',
                     'plan_sha256': m.PLAN, 'actor_arn': m.ACTOR}
        self.base, self.suffix = {}, {}
        for idx, record in enumerate(m.RECORDS):
            self.base[record] = ('Existing public record ' + str(idx) + '\n').encode()
            self.suffix[record] = ('\nApproved final suffix ' + str(idx) + '\n').encode()
            self.write(record, self.base[record])
            self.write(self.staging + '/suffixes/' + Path(record).name + '.txt', self.suffix[record])
        self.write(self.staging + '/artifacts/report.md', ('Public synthetic fixture ' + ADDRESS + '\n').encode())
        self.request = {'root': self.root, 'binding': self.bind,
                        'artifacts': ['artifacts/report.md'],
                        'suffixes': {x: 'suffixes/' + Path(x).name + '.txt' for x in m.RECORDS}}
        self.save_request()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, rel, data):
        f = self.repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        f.chmod(0o600)

    def save_request(self):
        self.write(self.request_rel, m.encoded(self.request))

    def assemble(self):
        return m.assemble(self.repo, self.request_rel)

    def scanned(self):
        self.assemble()
        self.freeze_sha = m.sha((self.repo / self.freeze_rel).read_bytes())
        self.freeze = json.loads((self.repo / self.freeze_rel).read_text())
        self.receipt = {**self.bind, 'stage': 'post-freeze-scan',
                        'observed_at': '2026-11-01T21:00:00+00:00',
                        'public_manifest_sha256': self.freeze_sha,
                        'files_scanned': len(self.freeze['files']), 'matches': 0,
                        'excluded': m.EXCLUDED}
        self.save_receipt()

    def save_receipt(self):
        self.write(self.receipt_rel, m.encoded(self.receipt))

    def verify(self, after=False):
        return m.verify(self.repo, self.freeze_rel, self.freeze_sha, self.receipt_rel,
                        self.bind['gate_sha256'], self.bind['operation'], after)

    def publish_fixture(self):
        # Test-owned public fixtures only; production helper has no append operation.
        for record in m.RECORDS:
            self.write(record, self.base[record] + self.suffix[record])

    def test_happy_before_after_all_five_exact_suffixes(self):
        self.scanned()
        before = self.verify()
        self.assertEqual(before['record_count'], 5)
        self.assertFalse(before['scan_authenticity_verified'])
        for record in m.RECORDS:
            self.assertEqual((self.repo / record).read_bytes(), self.base[record])
        self.publish_fixture()
        after = self.verify(True)
        self.assertTrue(after['exact_bytes_match'])
        self.assertFalse(after['publication_performed'])

    def test_manifest_complete_and_wrapper_compatible(self):
        self.scanned()
        self.assertEqual(set(self.freeze), {'root', 'files'})
        self.assertEqual({r['path'] for r in self.freeze['files']},
                         set(m.inventory_files(self.repo, self.root)))
        self.assertEqual(len(self.freeze['files']), 7)
        for row in self.freeze['files']:
            self.assertEqual(set(row), {'path', 'bytes', 'sha256'})

    def test_assembly_never_changes_destinations(self):
        self.assemble()
        self.assertTrue(all((self.repo / k).read_bytes() == v for k, v in self.base.items()))

    def test_empty_suffix_allowed_and_exact(self):
        record = m.RECORDS[0]
        self.suffix[record] = b''
        self.write(self.staging + '/' + self.request['suffixes'][record], b'')
        self.scanned(); self.verify(); self.publish_fixture(); self.verify(True)

    def test_repeat_assembly_never_overwrites(self):
        self.assemble()
        original = (self.repo / self.freeze_rel).read_bytes()
        with self.assertRaisesRegex(m.Blocked, 'OUTPUT_EXISTS'):
            self.assemble()
        self.assertEqual((self.repo / self.freeze_rel).read_bytes(), original)

    def test_changed_packet_requires_rescan(self):
        self.scanned()
        self.write(self.root + '/artifacts/report.md', b'changed')
        with self.assertRaisesRegex(m.Blocked, 'PACKET_CHANGED_RESCAN'):
            self.verify()

    def test_extra_packet_file_requires_rescan(self):
        self.scanned(); self.write(self.root + '/artifacts/extra.md', b'extra')
        with self.assertRaisesRegex(m.Blocked, 'PACKET_INCOMPLETE_RESCAN'):
            self.verify()

    def test_missing_packet_file_stops(self):
        self.scanned(); (self.repo / self.root / 'artifacts/report.md').unlink()
        with self.assertRaisesRegex(m.Blocked, 'MISSING_PATH'):
            self.verify()

    def test_extra_unscanned_append_rejected_before(self):
        self.scanned(); self.write(m.RECORDS[0], self.base[m.RECORDS[0]] + b'unscanned')
        with self.assertRaisesRegex(m.Blocked, 'BASE_OR_SUFFIX_CHANGED'):
            self.verify()

    def test_extra_unscanned_append_rejected_after(self):
        self.scanned(); self.publish_fixture()
        self.write(m.RECORDS[0], (self.repo / m.RECORDS[0]).read_bytes() + b'unscanned')
        with self.assertRaisesRegex(m.Blocked, 'PUBLISHED_BYTES_MISMATCH'):
            self.verify(True)

    def test_missing_suffix_or_base_edit_after_rejected(self):
        self.scanned(); self.publish_fixture()
        self.write(m.RECORDS[-1], self.base[m.RECORDS[-1]])
        with self.assertRaisesRegex(m.Blocked, 'PUBLISHED_BYTES_MISMATCH'):
            self.verify(True)

    def test_missing_fifth_record_rejected(self):
        del self.request['suffixes'][m.RECORDS[-1]]; self.save_request()
        with self.assertRaisesRegex(m.Blocked, 'INPUT_INVENTORY'):
            self.assemble()

    def test_duplicate_artifact_rejected(self):
        self.request['artifacts'] *= 2; self.save_request()
        with self.assertRaisesRegex(m.Blocked, 'DUPLICATE_INPUT'):
            self.assemble()

    def test_unlisted_staging_file_rejected(self):
        self.write(self.staging + '/artifacts/forgotten.md', b'forgotten')
        with self.assertRaisesRegex(m.Blocked, 'UNLISTED_STAGING_FILE'):
            self.assemble()

    def test_paths_private_binary_and_escape_rejected(self):
        for value in ('../outside.md', '/tmp/outside.md', 'artifacts/.env',
                      'artifacts/notification.private.json', 'artifacts/raw.tfstate',
                      'artifacts/code.py', 'scripts/file.md', 'artifacts/a/../../x.md'):
            with self.subTest(value=value):
                self.request['artifacts'] = [value]; self.save_request()
                with self.assertRaises(m.Blocked): self.assemble()

    def test_unknown_request_field_and_duplicate_json_rejected(self):
        self.request['approval'] = True; self.save_request()
        with self.assertRaisesRegex(m.Blocked, 'REQUEST_SCHEMA'): self.assemble()
        self.write(self.request_rel, b'{"root":1,"root":2}')
        with self.assertRaisesRegex(m.Blocked, 'DUPLICATE_JSON_KEY'): self.assemble()

    def test_binary_input_rejected(self):
        self.write(self.staging + '/artifacts/report.md', b'\x00binary')
        with self.assertRaisesRegex(m.Blocked, 'PUBLIC_TEXT_REQUIRED'): self.assemble()

    def test_invalid_utf8_rejected(self):
        self.write(self.staging + '/artifacts/report.md', b'\xff')
        with self.assertRaisesRegex(m.Blocked, 'PUBLIC_TEXT_REQUIRED'): self.assemble()

    def test_symlink_leaf_rejected(self):
        f = self.repo / self.staging / 'artifacts/report.md'
        f.unlink(); f.symlink_to(self.repo / m.RECORDS[0])
        with self.assertRaisesRegex(m.Blocked, 'SYMLINK_PATH'): self.assemble()

    def test_symlink_ancestor_rejected(self):
        old = self.repo / self.staging / 'artifacts'
        old.rename(old.with_name('moved'))
        old.symlink_to(old.with_name('moved'))
        with self.assertRaisesRegex(m.Blocked, 'SYMLINK_PATH'): self.assemble()

    def test_hardlink_input_rejected(self):
        f = self.repo / self.staging / 'artifacts/report.md'; f.unlink()
        os.link(self.repo / m.RECORDS[0], f)
        with self.assertRaisesRegex(m.Blocked, 'PUBLIC_FILE_METADATA'): self.assemble()

    def test_packet_symlink_rejected(self):
        self.scanned()
        f = self.repo / self.root / 'artifacts/report.md'; f.unlink()
        f.symlink_to(self.repo / m.RECORDS[0])
        with self.assertRaisesRegex(m.Blocked, 'SYMLINK_PATH'): self.verify()

    def test_receipt_matrix_fail_closed(self):
        self.scanned()
        cases = {'matches': 1, 'files_scanned': 1, 'public_manifest_sha256': 'b' * 64,
                 'gate_sha256': 'b' * 64, 'operation': 'wrong', 'plan_sha256': 'b' * 64,
                 'actor_arn': 'wrong', 'stage': 'readback', 'excluded': 'arbitrary exclusions',
                 'observed_at': 'unrecognized'}
        original = copy.deepcopy(self.receipt)
        for key, value in cases.items():
            with self.subTest(key=key):
                self.receipt = {**original, key: value}; self.save_receipt()
                with self.assertRaises(m.Blocked): self.verify()
        self.receipt = {**original, 'private_payload': ADDRESS}; self.save_receipt()
        with self.assertRaisesRegex(m.Blocked, 'SCAN_RECEIPT_SCHEMA'): self.verify()

    def test_expected_gate_and_operation_fail_closed(self):
        self.scanned()
        for gate, operation in [('b' * 64, 'fixture'), ('a' * 64, 'other')]:
            with self.assertRaisesRegex(m.Blocked, 'EXPECTED_BINDING'):
                m.verify(self.repo, self.freeze_rel, self.freeze_sha, self.receipt_rel, gate, operation)

    def test_changed_freeze_rejected(self):
        self.scanned(); self.write(self.freeze_rel, m.encoded({**self.freeze, 'extra': 1}))
        with self.assertRaisesRegex(m.Blocked, 'FREEZE_CHANGED'): self.verify()

    def test_scan_receipt_location_restricted(self):
        self.scanned()
        with self.assertRaisesRegex(m.Blocked, 'SCAN_RECEIPT_LOCATION'):
            m.verify(self.repo, self.freeze_rel, self.freeze_sha, self.request_rel, 'a' * 64, 'fixture')

    def test_exclusive_files_private_modes_and_fsync(self):
        with mock.patch.object(m.os, 'fsync', wraps=m.os.fsync) as sync:
            self.assemble()
        self.assertGreater(sync.call_count, 7)
        for rel in m.inventory_files(self.repo, self.root) + [self.freeze_rel]:
            self.assertEqual((self.repo / rel).stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.repo / self.root).stat().st_mode & 0o777, 0o700)

    def test_fsync_failure_stops_without_publication(self):
        with mock.patch.object(m.os, 'fsync', side_effect=OSError('fixture')):
            with self.assertRaises(OSError): self.assemble()
        self.assertTrue(all((self.repo / k).read_bytes() == v for k, v in self.base.items()))
        self.assertFalse((self.repo / self.freeze_rel).exists())

    def test_source_changes_during_assembly_rejected(self):
        original = m.read_public
        counts = {}
        def changing(repo, rel):
            counts[rel] = counts.get(rel, 0) + 1
            data = original(repo, rel)
            return data + b'changed' if rel == m.RECORDS[0] and counts[rel] == 2 else data
        with mock.patch.object(m, 'read_public', side_effect=changing):
            with self.assertRaisesRegex(m.Blocked, 'BASE_CHANGED'): self.assemble()
        self.assertFalse((self.repo / self.root).exists())

    def test_destination_changes_during_verification_rejected(self):
        self.scanned(); original = m.read_public; count = [0]
        def changing(repo, rel):
            if rel == m.RECORDS[0]:
                count[0] += 1
                if count[0] == 2: return original(repo, rel) + b'changed'
            return original(repo, rel)
        with mock.patch.object(m, 'read_public', side_effect=changing):
            with self.assertRaisesRegex(m.Blocked, 'DESTINATION_CHANGED'): self.verify()

    def test_cli_success_never_emits_address_or_record_content(self):
        out = io.StringIO()
        with mock.patch('sys.stdout', new=out):
            self.assertEqual(m.main(['assemble', '--repo', str(self.repo), '--request', self.request_rel]), 0)
        self.assertNotIn(ADDRESS, out.getvalue())
        self.assertNotIn(m.sha(ADDRESS.encode()), out.getvalue())
        self.assertNotIn('Existing public record', out.getvalue())

    def test_cli_error_never_emits_untrusted_payload(self):
        self.request['binding']['operation'] = ADDRESS; self.save_request()
        out = io.StringIO()
        with mock.patch('sys.stdout', new=out):
            self.assertEqual(m.main(['assemble', '--repo', str(self.repo), '--request', self.request_rel]), 2)
        self.assertNotIn(ADDRESS, out.getvalue())
        self.assertEqual(json.loads(out.getvalue())['code'], 'BINDING_VALUE')

    def test_oversized_input_stops_before_output(self):
        with mock.patch.object(m, 'MAX_FILE', 1):
            with self.assertRaisesRegex(m.Blocked, 'PUBLIC_FILE_METADATA'): self.assemble()
        self.assertFalse((self.repo / self.root).exists())

    def refreeze(self, mutate):
        """Fixture-only malformed/refrozen metadata; receipt provenance is synthetic."""
        inv_rel = self.root + '/publication-inventory.json'
        inv = json.loads((self.repo / inv_rel).read_text())
        mutate(inv)
        self.write(inv_rel, m.encoded(inv))
        for row in self.freeze['files']:
            if row['path'] == inv_rel:
                row.update(m.metadata(inv_rel, (self.repo / inv_rel).read_bytes()))
        self.write(self.freeze_rel, m.encoded(self.freeze))
        self.freeze_sha = m.sha((self.repo / self.freeze_rel).read_bytes())
        self.receipt['public_manifest_sha256'] = self.freeze_sha
        self.save_receipt()

    def test_refrozen_artifact_inventory_omission_rejected(self):
        self.scanned(); self.refreeze(lambda value: value['artifacts'].clear())
        with self.assertRaisesRegex(m.Blocked, 'INVENTORY_INCOMPLETE'): self.verify()

    def test_refrozen_duplicate_artifact_inventory_rejected(self):
        self.scanned(); self.refreeze(lambda value: value['artifacts'].append(value['artifacts'][0]))
        with self.assertRaisesRegex(m.Blocked, 'ARTIFACT_DUPLICATE'): self.verify()

    def test_refrozen_extra_destination_rejected(self):
        self.scanned(); self.refreeze(lambda value: value['records'][0].update(destination='docs/agent-runs/phase-12/human-gate.md'))
        with self.assertRaisesRegex(m.Blocked, 'RECORD_SET'): self.verify()

    def test_duplicate_freeze_entry_rejected(self):
        self.scanned(); self.freeze['files'].append(self.freeze['files'][0])
        self.write(self.freeze_rel, m.encoded(self.freeze))
        self.freeze_sha = m.sha((self.repo / self.freeze_rel).read_bytes())
        with self.assertRaisesRegex(m.Blocked, 'FREEZE_PATH'): self.verify()

    def test_untrusted_cli_parse_error_has_no_payload(self):
        for args in ([ADDRESS], ['assemble', '--unknown', ADDRESS]):
            out, err = io.StringIO(), io.StringIO()
            with mock.patch('sys.stdout', new=out), mock.patch('sys.stderr', new=err):
                self.assertEqual(m.main(args), 2)
            self.assertNotIn(ADDRESS, out.getvalue() + err.getvalue())
            self.assertEqual(json.loads(out.getvalue())['code'], 'CLI_OPTIONS')

    def test_separate_workspace_transfer_validates_canonical_bases(self):
        self.scanned()
        # Separate test-owned canonical stand-in receives only packet + external freeze.
        with tempfile.TemporaryDirectory(prefix='canonical publication fixture ') as target:
            canonical = Path(target).resolve()
            (canonical / m.EVIDENCE).mkdir(parents=True)
            for record, data in self.base.items():
                f = canonical / record; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(data)
            shutil.copytree(self.repo / self.root, canonical / self.root)
            shutil.copyfile(self.repo / self.freeze_rel, canonical / self.freeze_rel)
            self.assertFalse((canonical / self.staging).exists())
            self.assertFalse((canonical / self.receipt_rel).exists())
            # In live operation scanner stdout is captured externally, not in canonical
            # checkout. Only after scanner completion is its fixed receipt transferred.
            shutil.copyfile(self.repo / self.receipt_rel, canonical / self.receipt_rel)
            before = m.verify(canonical, self.freeze_rel, self.freeze_sha, self.receipt_rel,
                              self.bind['gate_sha256'], self.bind['operation'])
            self.assertTrue(before['exact_bytes_match'])
            f = canonical / m.RECORDS[0]; f.write_bytes(b'different canonical base')
            with self.assertRaisesRegex(m.Blocked, 'BASE_OR_SUFFIX_CHANGED'):
                m.verify(canonical, self.freeze_rel, self.freeze_sha, self.receipt_rel,
                         self.bind['gate_sha256'], self.bind['operation'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

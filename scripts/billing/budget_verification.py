#!/usr/bin/env python3
"""Read-only post-create verification. Authoring/review never authorizes execution."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('billing_verification_core', Path(__file__).with_name('budget_execution.py'))
b = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = b
_spec.loader.exec_module(b)

ORIGINAL_OPERATION = 'billing-budget-attempt-02'
ORIGINAL_GATE_SHA = '4af82b7d800cc746fdd8f2abdc5882019b9bade87c9b771a6aa419b84df1b8b3'
ORIGINAL_SOURCE = '4000889e244dacdb4c0445b2f6a93b24841a0ad7'
ORIGINAL_WRAPPER = 'a31852d14e80d970e2338f8a5d94320ea3ca3b89ec759584689d8331d446080b'
ORIGINAL_PLAN = 'ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855'
STATE_SHA = '271fe888595b6d71eedb649b7cdb87686ded0b3cbb1e2b9a19f76d7575be3f67'
STATE_BYTES = 40818
PERMISSIONS = {'verify', 'post-freeze-scan', 'original-linkage-read', 'opaque-state-backup-check', 'private-recipient-compare'}
MAX_FILES = 256
MAX_TOTAL = 32 * 1024 * 1024
EXCLUDED = ('Only this external fixed-schema receipt and the external freeze-input manifest; every existing packet file was scanned. '
            'Any packet addition or change requires a new frozen manifest and scan.')
GATE_FIELDS = {'operation', 'option', 'plan_sha256', 'proposal_sha256', 'wrapper_files', 'source_commit',
               'human_record_sha256', 'g1_affirmation', 'actor_arn', 'account', 'profile', 'region',
               'window_start', 'window_end', 'timezone', 'login_at', 'human_sts_observed_at', 'human_sts',
               'permissions', 'retention_accepted', 'verification_review_approved', 'original_provenance_confirmed',
               'aws_cli_sha256', 'public_packet_root', 'original_operation', 'original_gate_sha256',
               'original_source_commit', 'original_wrapper_sha256', 'original_apply_receipt_sha256',
               'state_backup_sha256', 'state_backup_bytes', 'original_gate_filename'}


def sha(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def canonical_receipt_bytes(value):
    """Canonical public-receipt encoding, exactly matching core save_json."""
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode('utf-8')


def regular(path, uid, mode=0o600):
    st = b.file_meta(path, uid, mode)
    b.require(st.st_nlink == 1, 'HARDLINK_FILE')
    return st


def read_private(path, uid):
    regular(path, uid)
    return b.read_nofollow(path)


def public_read(repo, path):
    """Read a public file with no-follow traversal of every path component."""
    path = Path(path)
    b.require(not path.is_absolute() and '..' not in path.parts and path.parts, 'PUBLIC_PATH')
    b.require(repo.resolve() == repo, 'PUBLIC_REPO_SYMLINK')
    fd = os.open(repo, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[:-1]:
            new_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new_fd
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            before = os.fstat(file_fd)
            b.require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= b.MAX_BYTES,
                      'PUBLIC_FILE_TYPE_SIZE')
            data = bytearray()
            while chunk := os.read(file_fd, min(65536, b.MAX_BYTES + 1 - len(data))):
                data.extend(chunk); b.require(len(data) <= b.MAX_BYTES, 'PUBLIC_FILE_SIZE')
            b.require(b.identity(before) == b.identity(os.fstat(file_fd))
                      == b.identity(os.stat(path.name, dir_fd=fd, follow_symlinks=False)), 'PUBLIC_FILE_CHANGED')
            return bytes(data)
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def inventory(repo, root):
    """No exclusions, no symlink descendants, bounded packet membership."""
    root = Path(root)
    b.require(not root.is_absolute() and '..' not in root.parts, 'PUBLIC_PATH')
    # public_read below checks ancestors for each file; check empty roots/dirs too.
    node = repo
    for part in root.parts:
        node /= part
        b.require(stat.S_ISDIR(node.lstat().st_mode) and not node.is_symlink(), 'PUBLIC_DIRECTORY')
    found = set()
    for directory, dirs, files in os.walk(node, followlinks=False):
        for name in dirs:
            p = Path(directory) / name
            b.require(not p.is_symlink() and stat.S_ISDIR(p.lstat().st_mode), 'PUBLIC_DIRECTORY')
        for name in files:
            p = Path(directory) / name
            b.require(not p.is_symlink() and stat.S_ISREG(p.lstat().st_mode), 'PUBLIC_FILE_TYPE_SIZE')
            found.add(str(p.relative_to(repo)))
            b.require(len(found) <= MAX_FILES, 'PUBLIC_PACKET_LIMIT')
    return found


class Verification:
    """Independent read-only dispatcher; no initial-create Execution inheritance."""
    def __init__(self, policy, runner=None, now=b.stamp):
        self.p = policy
        self.runner = runner or b.PrivateRunner()
        self.now = now
        self.gate = self.binding = self.op = None

    def load_gate(self, gate_path, gate_sha, operation):
        b.require(type(operation) is str and re.fullmatch(r'verify-[A-Za-z0-9_-]{1,56}', operation) is not None,
                  'VERIFICATION_OPERATION')
        raw = read_private(gate_path, self.p.uid)
        b.require(sha(gate_sha) and b.digest(raw) == gate_sha, 'GATE_HASH')
        g = b.parse_json(raw)
        b.require(type(g) is dict and set(g) == GATE_FIELDS, 'VERIFICATION_GATE_SCHEMA')
        b.require(g['option'] == 'B' and g['operation'] == operation, 'VERIFICATION_OPTION')
        b.require(type(g['original_gate_filename']) is str
                  and re.fullmatch(r'approval-[A-Za-z0-9_-]{1,96}\.json', g['original_gate_filename']) is not None,
                  'ORIGINAL_GATE_FILENAME')
        b.require(g['plan_sha256'] == ORIGINAL_PLAN == self.p.pins['plan_sha256']
                  and g['proposal_sha256'] == self.p.pins['proposal_sha256'], 'GATE_PLAN_BINDING')
        b.require(g['human_record_sha256'] == self.p.pins['human_record_sha256']
                  and type(g['g1_affirmation']) is str and len(g['g1_affirmation'].strip()) >= 10, 'G1_REQUIRED')
        b.require(g['original_operation'] == ORIGINAL_OPERATION and g['original_gate_sha256'] == ORIGINAL_GATE_SHA
                  and g['original_source_commit'] == ORIGINAL_SOURCE and g['original_wrapper_sha256'] == ORIGINAL_WRAPPER
                  and sha(g['original_apply_receipt_sha256']) and g['state_backup_sha256'] == STATE_SHA
                  and type(g['state_backup_bytes']) is int and g['state_backup_bytes'] == STATE_BYTES, 'ORIGINAL_GATE_BINDING')
        b.require(g['actor_arn'] == b.CALLER and g['account'] == b.ACCOUNT and g['profile'] == b.PROFILE
                  and g['region'] == b.REGION and g['human_sts'] == {'Account': b.ACCOUNT, 'Arn': b.CALLER}, 'HUMAN_IDENTITY')
        b.require(type(g['permissions']) is list and len(g['permissions']) == len(PERMISSIONS)
                  and all(type(x) is str for x in g['permissions']) and set(g['permissions']) == PERMISSIONS
                  and g['retention_accepted'] is True and g['verification_review_approved'] is True
                  and g['original_provenance_confirmed'] is True, 'HUMAN_GATE_REQUIRED')
        b.require(g['timezone'] == 'America/Chicago', 'WINDOW_TIMEZONE')
        start, end, login, observed = map(b.date, (g['window_start'], g['window_end'], g['login_at'], g['human_sts_observed_at']))
        b.require(start <= login <= observed <= self.now() < end and 0 < (end-start).total_seconds() <= 3600,
                  'SESSION_WINDOW')
        b.require(type(g['source_commit']) is str and re.fullmatch(r'[0-9a-f]{40}', g['source_commit']) is not None
                  and sha(g['aws_cli_sha256']), 'GATE_HASH_SCHEMA')
        root = g['public_packet_root']
        b.require(type(root) is str and re.fullmatch(r'docs/agent-runs/phase-12/evidence/12d-publication-output-verify-[A-Za-z0-9_-]{1,56}', root)
                  is not None, 'GATE_PACKET_SCOPE')
        self.gate = g
        self.op = self.p.primary / 'operations' / operation
        self.binding = {'gate_sha256': gate_sha, 'operation': operation, 'plan_sha256': ORIGINAL_PLAN, 'actor_arn': b.CALLER}
        self.check_window()
        return self

    def check_window(self):
        g = self.gate
        b.require(g is not None and b.date(g['window_start']) <= b.date(g['login_at'])
                  <= b.date(g['human_sts_observed_at']) <= self.now() < b.date(g['window_end'])
                  and (self.now()-b.date(g['login_at'])).total_seconds() < 3600, 'WINDOW_EXPIRED')

    def check_checkout(self, allow_packet=False, external_freeze=None):
        # Reuse only the source/Git checker, never create/apply stage dispatch.
        b.Execution.check_checkout(self, allow_packet, external_freeze)
        for rel in self.gate['wrapper_files']:
            p = Path(rel)
            b.require(sha(self.gate['wrapper_files'][rel]), 'WRAPPER_HASH_SCHEMA')
            b.require(b.digest(public_read(self.p.repo, p)) == self.gate['wrapper_files'][rel], 'WRAPPER_HASH')

    def linkage(self):
        """Future authorized fixed metadata reads plus opaque state hashes only."""
        p, g = self.p, self.gate
        for directory in (p.primary, p.backups, p.primary/'operations', p.primary/'operations'/ORIGINAL_OPERATION, p.config):
            b.secure_dir(directory, p.uid)
        old_op = p.primary/'operations'/ORIGINAL_OPERATION
        raw_gate = read_private(p.primary/g['original_gate_filename'], p.uid)
        b.require(b.digest(raw_gate) == ORIGINAL_GATE_SHA, 'ORIGINAL_GATE_HASH')
        old_gate = b.parse_json(raw_gate)
        b.require(type(old_gate) is dict and old_gate.get('operation') == ORIGINAL_OPERATION
                  and old_gate.get('source_commit') == ORIGINAL_SOURCE and old_gate.get('plan_sha256') == ORIGINAL_PLAN
                  and old_gate.get('actor_arn') == b.CALLER and old_gate.get('account') == b.ACCOUNT
                  and old_gate.get('profile') == b.PROFILE and old_gate.get('region') == b.REGION
                  and type(old_gate.get('wrapper_files')) is dict
                  and old_gate['wrapper_files'].get('scripts/billing/budget_execution.py') == ORIGINAL_WRAPPER,
                  'ORIGINAL_GATE_CONTEXT')
        raw = read_private(old_op/'apply.receipt.json', p.uid)
        b.require(b.digest(raw) == g['original_apply_receipt_sha256'], 'ORIGINAL_APPLY_HASH')
        receipt = b.parse_json(raw)
        b.require(type(receipt) is dict and set(receipt) == {'gate_sha256', 'operation', 'plan_sha256', 'actor_arn', 'stage', 'observed_at', 'result'}, 'ORIGINAL_APPLY_SCHEMA')
        expected = {'gate_sha256': ORIGINAL_GATE_SHA, 'operation': ORIGINAL_OPERATION,
                    'plan_sha256': ORIGINAL_PLAN, 'actor_arn': b.CALLER, 'stage': 'apply'}
        b.require(all(receipt[k] == value for k, value in expected.items()), 'ORIGINAL_APPLY_CONTEXT')
        when = b.date(receipt['observed_at'])
        b.require(b.date(old_gate['window_start']) <= when < b.date(old_gate['window_end'])
                  and when < b.date(g['window_start']), 'ORIGINAL_APPLY_TIME')
        result = receipt['result']
        b.require(type(result) is dict and set(result) == {'backup', 'backup_verified', 'exit', 'window_open_for_further_live'}
                  and result['backup_verified'] is True and type(result['exit']) is int and result['exit'] == 0
                  and type(result['window_open_for_further_live']) is bool, 'ORIGINAL_APPLY_RESULT')
        b.require(type(result['backup']) is dict and result['backup'] == {'bytes': STATE_BYTES, 'equal': True,
                  'fsync_completed': True, 'sha256': STATE_SHA} and type(result['backup']['bytes']) is int
                  and result['backup']['equal'] is True and result['backup']['fsync_completed'] is True, 'ORIGINAL_BACKUP_RESULT')
        for name in ('apply.started', 'readback.started'):
            b.require(regular(old_op/name, p.uid).st_size == 0, 'ORIGINAL_JOURNAL_SHAPE')
        b.require(not os.path.lexists(old_op/'readback.receipt.json'), 'ORIGINAL_READBACK_CONFLICT')
        for root in (p.primary, p.config):
            for name in ('.billing.execution.tfstate.lock.info', 'billing.execution.tfstate.lock.info', '.terraform.tfstate.lock.info'):
                b.require(not os.path.lexists(root/name), 'TERRAFORM_LOCK_PRESENT')
        for state in (p.state, p.backups/'initial-ab9f141e83058209/billing.execution.tfstate'):
            st = regular(state, p.uid)
            b.require(st.st_size == STATE_BYTES and b.hash_file(state) == STATE_SHA, 'STATE_BACKUP_DRIFT')
        b.require(p.aws.resolve().is_file() and b.hash_file(p.aws.resolve()) == g['aws_cli_sha256'], 'AWS_CLI_HASH')
        return {'original_operation': ORIGINAL_OPERATION, 'original_gate_sha256': ORIGINAL_GATE_SHA,
                'original_apply_receipt_sha256': g['original_apply_receipt_sha256'],
                'state_backup_verified': True}

    @contextmanager
    def lease(self, mode):
        b.secure_dir(self.op, self.p.uid)
        lock = self.p.primary/'.billing-wrapper-active.lock'
        fd = b.create_file(lock); owner = b.identity(os.fstat(fd)); os.close(fd)
        try:
            fd = b.create_file(self.op/(mode+'.started')); os.close(fd)
            yield
        finally:
            if b.identity(lock.lstat()) == owner:
                lock.unlink(); b.sync_dir(self.p.primary)

    def query(self, operation, extra, label):
        self.check_window()
        timeout = min(b.READ_TIMEOUT_SECONDS, (b.date(self.gate['window_end'])-self.now()).total_seconds())
        b.require(timeout > 0, 'WINDOW_EXPIRED')
        code, out, err = self.runner(self.p.aws_argv(operation, extra), self.p.config, self.p.env(), self.op, label, timeout)
        b.require(type(code) is int and code == 0 and not err.strip(), 'READBACK_COMMAND_FAILED')
        value = b.parse_json(out)
        b.require(type(value) is dict and not value.get('NextToken'), 'READBACK_TRUNCATED')
        self.check_window()
        return value

    def recipient_identity(self):
        return list(b.identity(regular(self.p.primary/'notification.private.tfvars.json', self.p.uid)))

    def private_recipient(self):
        # A new gate explicitly permits this exact in-memory comparison, never publication.
        regular(self.p.primary/'notification.private.tfvars.json', self.p.uid)
        return b.Execution.private_recipient(self)

    def verify(self):
        self.check_checkout(); self.check_window()
        parent = self.p.primary/'operations'; b.secure_dir(parent, self.p.uid)
        b.require(not os.path.lexists(self.p.primary/'.billing-wrapper-active.lock'), 'WRAPPER_ACTIVE')
        preflight_link = self.linkage()
        self.check_window()
        self.op.mkdir(mode=0o700)  # Exclusive distinct namespace, no replay.
        with self.lease('verify'):
            link = self.linkage()
            b.require(link == preflight_link, 'LINKAGE_CHANGED')
            self.check_window()
            common = ['--account-id', b.ACCOUNT, '--budget-name', b.BUDGET]
            budget = self.query('describe-budget', common+['--show-filter-expression'], 'verify-budget')
            tags = self.query('list-tags-for-resource', ['--resource-arn', b.ARN], 'verify-tags')
            notifications = self.query('describe-notifications-for-budget', common+['--max-results', '100', '--no-paginate'], 'verify-notifications')
            subscribers = {}
            for threshold in (50, 80, 100):
                subscribers[threshold] = self.query('describe-subscribers-for-notification', common+['--notification',
                    json.dumps(b.expected_notification(threshold), separators=(',', ':')), '--max-results', '100', '--no-paginate'],
                    'verify-subscribers-'+str(threshold))
            input_identity = self.recipient_identity()
            safe = b.sanitize_readback(budget, tags, notifications, subscribers, self.private_recipient())
            b.require(self.recipient_identity() == input_identity, 'PRIVATE_INPUT_CHANGED')
            self.check_checkout(); self.check_window(); b.require(self.linkage() == link, 'LINKAGE_CHANGED')
            self.check_window()
            receipt = {**self.binding, 'stage': 'verify', 'option': 'B', 'observed_at': b.iso(self.now()),
                       'linkage': link, 'result': safe}
            # Identity metadata remains private; no recipient/hash/size enters public receipt.
            receipt_sha = b.digest(canonical_receipt_bytes(receipt))
            b.save_json(self.op/'verify.input-identity.json', {**self.binding, 'verification_receipt_sha256': receipt_sha,
                                                          'identity': input_identity})
            b.require(self.recipient_identity() == input_identity, 'PRIVATE_INPUT_CHANGED')
            self.check_window()
            b.save_json(self.op/'verify.receipt.json', receipt)
            return receipt

    def verified(self):
        raw = read_private(self.op/'verify.receipt.json', self.p.uid)
        receipt = b.parse_json(raw)
        b.require(type(receipt) is dict and set(receipt) == {*self.binding, 'stage', 'option', 'observed_at', 'linkage', 'result'}, 'VERIFY_RECEIPT_SCHEMA')
        b.require(all(receipt[k] == v for k,v in self.binding.items()) and receipt['stage'] == 'verify'
                  and receipt['option'] == 'B' and self.linkage() == receipt['linkage'], 'VERIFY_RECEIPT_BINDING')
        b.require(b.date(self.gate['window_start']) <= b.date(receipt['observed_at']) <= self.now()
                  < b.date(self.gate['window_end']), 'VERIFY_RECEIPT_TIME')
        checkpoint = b.parse_json(read_private(self.op/'verify.input-identity.json', self.p.uid))
        b.require(type(checkpoint) is dict and set(checkpoint) == {*self.binding, 'verification_receipt_sha256', 'identity'}
                  and all(checkpoint[k] == value for k,value in self.binding.items())
                  and checkpoint['verification_receipt_sha256'] == b.digest(raw)
                  and type(checkpoint['identity']) is list and len(checkpoint['identity']) == 5
                  and all(type(x) is int for x in checkpoint['identity'])
                  and checkpoint['identity'] == self.recipient_identity(), 'PRIVATE_INPUT_CHANGED')
        result = receipt['result']
        expected_true = {'budget_fields_match', 'cost_scope_match', 'tags_match', 'dates_match', 'account_request_matches',
                         'scope_filters_absent', 'private_recipients_match'}
        expected_fields = expected_true | {'notification_count', 'email_subscribers_each', 'sns_subscribers',
                                          'health_reported', 'health_healthy_if_reported', 'delivery_verified', 'phase12d_complete'}
        b.require(type(result) is dict and set(result) == expected_fields
                  and all(result[k] is True for k in expected_true)
                  and type(result['notification_count']) is int and result['notification_count'] == 3
                  and type(result['email_subscribers_each']) is int and result['email_subscribers_each'] == 1
                  and type(result['sns_subscribers']) is int and result['sns_subscribers'] == 0
                  and type(result['health_reported']) is bool and type(result['health_healthy_if_reported']) is bool
                  and result['health_reported'] == result['health_healthy_if_reported']
                  and result['delivery_verified'] is False and result['phase12d_complete'] is False, 'VERIFY_RECEIPT_RESULT')
        return b.digest(raw)

    def scan(self, manifest_path, manifest_sha, expected_verification_sha):
        b.require(sha(manifest_sha) and sha(expected_verification_sha), 'SCAN_HASH_ARGUMENTS')
        manifest_path = Path(manifest_path)
        b.require(manifest_path.is_absolute() and manifest_path.is_relative_to(self.p.repo), 'FREEZE_LOCATION')
        rel_manifest = manifest_path.relative_to(self.p.repo)
        self.check_checkout(True, manifest_path); self.check_window()
        b.require(not os.path.lexists(self.p.primary/'.billing-wrapper-active.lock'), 'WRAPPER_ACTIVE')
        # Pre-stage read-only checks let a human correct an input typo without a consumed journal.
        b.require(self.verified() == expected_verification_sha, 'VERIFY_RECEIPT_HASH')
        preflight_manifest = public_read(self.p.repo, rel_manifest)
        b.require(b.digest(preflight_manifest) == manifest_sha, 'PUBLIC_FREEZE_HASH')
        self.check_window()
        with self.lease('post-freeze-scan'):
            b.require(sha(expected_verification_sha), 'VERIFY_RECEIPT_HASH_REQUIRED')
            verification_sha = self.verified()
            b.require(verification_sha == expected_verification_sha, 'VERIFY_RECEIPT_HASH')
            raw = public_read(self.p.repo, rel_manifest)
            b.require(sha(manifest_sha) and b.digest(raw) == manifest_sha, 'PUBLIC_FREEZE_HASH')
            freeze = b.parse_json(raw)
            b.require(type(freeze) is dict and set(freeze) == {'root','files'} and type(freeze['files']) is list
                      and 0 < len(freeze['files']) <= MAX_FILES and freeze['root'] == self.gate['public_packet_root'], 'PUBLIC_FREEZE_SCHEMA')
            root = Path(freeze['root'])
            b.require(not rel_manifest.is_relative_to(root), 'FREEZE_MANIFEST_MUST_BE_OUTSIDE_PACKET')
            actual = inventory(self.p.repo, root)
            rows = {}; total = 0
            recipient = self.private_recipient().encode().lower()
            for row in freeze['files']:
                b.require(type(row) is dict and set(row) == {'path','bytes','sha256'} and type(row['path']) is str
                          and type(row['bytes']) is int and 0 <= row['bytes'] <= b.MAX_BYTES and sha(row['sha256']), 'PUBLIC_FREEZE_ENTRY')
                rel = Path(row['path'])
                b.require(not rel.is_absolute() and '..' not in rel.parts and rel.is_relative_to(root)
                          and str(rel) == row['path'] and row['path'] not in rows, 'PUBLIC_SCAN_SCOPE')
                rows[row['path']] = row
                total += row['bytes']; b.require(total <= MAX_TOTAL, 'PUBLIC_PACKET_LIMIT')
                data = public_read(self.p.repo, rel)
                b.require(len(data) == row['bytes'] and b.digest(data) == row['sha256'], 'PUBLIC_CONTENT_CHANGED_RESCAN')
                b.require(recipient not in data.lower(), 'PUBLIC_RECIPIENT_FOUND')
            b.require(actual == set(rows) == inventory(self.p.repo, root), 'PUBLIC_FREEZE_INCOMPLETE')
            for rel, row in rows.items():
                data = public_read(self.p.repo, Path(rel))
                b.require(len(data) == row['bytes'] and b.digest(data) == row['sha256'], 'PUBLIC_CONTENT_CHANGED_RESCAN')
            b.require(public_read(self.p.repo, rel_manifest) == raw, 'PUBLIC_FREEZE_CHANGED')
            self.check_checkout(True, manifest_path); self.check_window()
            b.require(self.verified() == verification_sha and inventory(self.p.repo, root) == set(rows), 'VERIFICATION_OR_PACKET_CHANGED')
            self.check_window()
            receipt = {**self.binding, 'stage': 'post-freeze-scan', 'observed_at': b.iso(self.now()),
                       'public_manifest_sha256': manifest_sha, 'files_scanned': len(rows), 'matches': 0, 'excluded': EXCLUDED}
            # Private sidecar links the unchanged ten-key public receipt to the new verification receipt.
            b.save_json(self.op/'post-freeze-scan.receipt.json', {'scan': receipt, 'verification_receipt_sha256': verification_sha})
            return receipt


def production_policy():
    b.require(Path(__file__).resolve() == b.REPO/'scripts/billing/budget_verification.py', 'VERIFIER_LOCATION')
    return b.production_policy()


class PublicParser(argparse.ArgumentParser):
    def error(self, message):
        raise b.Blocked('CLI_ARGUMENTS')


def main(argv=None):
    parser = PublicParser(description=__doc__)
    parser.add_argument('mode', choices=('verify','post-freeze-scan'))
    parser.add_argument('--gate', type=Path, required=True)
    parser.add_argument('--gate-sha256', required=True)
    parser.add_argument('--operation', required=True)
    parser.add_argument('--public-manifest', type=Path)
    parser.add_argument('--public-manifest-sha256')
    parser.add_argument('--verification-receipt-sha256')
    os.umask(0o077)
    try:
        args = parser.parse_args(argv)
        b.require(sha(args.gate_sha256), 'GATE_HASH_SCHEMA')
        if args.mode == 'post-freeze-scan':
            b.require(args.public_manifest is not None and sha(args.public_manifest_sha256)
                      and sha(args.verification_receipt_sha256), 'SCAN_ARGUMENTS')
        else:
            b.require(args.public_manifest is None and args.public_manifest_sha256 is None
                      and args.verification_receipt_sha256 is None, 'UNEXPECTED_SCAN_OPTIONS')
        ex = Verification(production_policy()).load_gate(args.gate, args.gate_sha256, args.operation)
        if args.mode == 'post-freeze-scan':
            b.require(args.public_manifest is not None and args.public_manifest_sha256 is not None, 'PUBLIC_FREEZE_REQUIRED')
            result = ex.scan(args.public_manifest, args.public_manifest_sha256, args.verification_receipt_sha256)
        else:
            b.require(args.public_manifest is None and args.public_manifest_sha256 is None
                      and args.verification_receipt_sha256 is None, 'UNEXPECTED_SCAN_OPTIONS')
            result = ex.verify()
        print(json.dumps(result, sort_keys=True)); return 0
    except b.Blocked as error:
        print(json.dumps({'status':'BLOCKED-ON','code':str(error)})); return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, subprocess.SubprocessError):
        print(json.dumps({'status':'BLOCKED-ON','code':'LOCAL_OR_SCHEMA_FAILURE_NO_RETRY'})); return 2


if __name__ == '__main__':
    raise SystemExit(main())

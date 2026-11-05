#!/usr/bin/env python3
"""Public-only W3 evidence assembly/comparison. Never scans secrets or publishes records."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

REPO = Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
EVIDENCE = 'docs/agent-runs/phase-12/evidence'
RECORDS = tuple('docs/agent-runs/phase-12/' + n for n in
                ('prompt.md', 'review.md', 'repairs.md', 'owner-report.md', 'test-report.md'))
PLAN = 'ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855'
ACTOR = 'arn:aws:sts::530332961125:assumed-role/scholarchain-billing-deployer/scholarchain-billing-operator'
EXCLUDED = 'Only this external fixed-schema receipt and the external freeze-input manifest; every existing packet file was scanned. Any packet addition or change requires a new frozen manifest and scan.'
MAX_FILE = 8 * 1024 * 1024
MAX_FILES = 256
MAX_TOTAL = 64 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}')


class Blocked(Exception):
    pass


class PublicParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default repeats untrusted arguments; never echo them.
        raise Blocked('CLI_OPTIONS')


def need(value, code):
    if not value:
        raise Blocked(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def relative(value):
    need(type(value) is str and value and '\\' not in value, 'PATH_SCHEMA')
    p = PurePosixPath(value)
    need(not p.is_absolute() and str(p) == value and '..' not in p.parts
         and all(re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*', part) for part in p.parts),
         'PATH_SCOPE')
    forbidden = ('private', 'credential', 'secret', '.env', '.tfstate', '.tfplan', '.aws')
    need(not any(term in part.lower() for part in p.parts for term in forbidden), 'PRIVATE_PATH_FORBIDDEN')
    return p


def checked(repo, rel, exists=True):
    p = repo / str(relative(rel))
    # Canonical root is required; no resolve() that silently follows an input link.
    need(repo.is_absolute() and repo.resolve() == repo, 'REPO_NOT_CANONICAL')
    for node in [repo, *repo.parents]:
        need(not stat.S_ISLNK(node.lstat().st_mode), 'SYMLINK_PATH')
    parts = p.relative_to(repo).parts
    node = repo
    for index, part in enumerate(parts):
        node = node / part
        if not node.exists() and not node.is_symlink():
            need(not exists and index == len(parts) - 1, 'MISSING_PATH')
            break
        st = node.lstat()
        need(not stat.S_ISLNK(st.st_mode), 'SYMLINK_PATH')
        if index < len(parts) - 1:
            need(stat.S_ISDIR(st.st_mode), 'DIRECTORY_REQUIRED')
    return p


def read_public(repo, rel):
    p = checked(repo, rel)
    before = p.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
         and before.st_uid == os.getuid() and before.st_size <= MAX_FILE, 'PUBLIC_FILE_METADATA')
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        need(identity(before) == identity(os.fstat(fd)), 'FILE_CHANGED')
        chunks, size = [], 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            size += len(chunk)
            need(size <= MAX_FILE, 'FILE_TOO_LARGE')
            chunks.append(chunk)
        need(identity(before) == identity(os.fstat(fd)) == identity(p.lstat()), 'FILE_CHANGED')
    finally:
        os.close(fd)
    data = b''.join(chunks)
    try:
        text = data.decode('utf-8')
    except UnicodeError:
        raise Blocked('PUBLIC_TEXT_REQUIRED') from None
    need(all(c in '\n\r\t' or ord(c) >= 32 for c in text), 'PUBLIC_TEXT_REQUIRED')
    return data


def pairs(rows):
    result = {}
    for k, v in rows:
        need(k not in result, 'DUPLICATE_JSON_KEY')
        result[k] = v
    return result


def parse(data):
    try:
        return json.loads(data, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, TypeError):
        raise Blocked('INVALID_JSON') from None


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(repo, rel, data):
    p = checked(repo, rel, exists=False)
    need(not p.exists(), 'OUTPUT_EXISTS')
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    sync(p.parent)


def leaf(value, prefix):
    p = relative(value)
    need(str(p.parent) == EVIDENCE and p.name.startswith(prefix)
         and len(p.name) > len(prefix), 'EVIDENCE_SCOPE')
    return str(p)


def metadata(path, data):
    return {'path': path, 'bytes': len(data), 'sha256': sha(data)}


def inventory_files(repo, root):
    base = checked(repo, root)
    need(base.is_dir(), 'PACKET_DIRECTORY')
    found = []
    for node in base.rglob('*'):
        rel = str(node.relative_to(repo))
        checked(repo, rel)
        if node.is_file():
            found.append(rel)
        else:
            need(node.is_dir(), 'SPECIAL_PATH')
    need(len(found) <= MAX_FILES, 'TOO_MANY_FILES')
    return sorted(found)


def binding(value):
    need(type(value) is dict and set(value) == {'gate_sha256', 'operation', 'plan_sha256', 'actor_arn'},
         'BINDING_SCHEMA')
    need(type(value['gate_sha256']) is str and HEX.fullmatch(value['gate_sha256'])
         and type(value['operation']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value['operation'])
         and value['plan_sha256'] == PLAN and value['actor_arn'] == ACTOR, 'BINDING_VALUE')
    return value


def assemble(repo, request_rel):
    """Read public staging only; write one exclusive new evidence packet + external freeze."""
    request_rel = str(relative(request_rel))
    staging = leaf(str(PurePosixPath(request_rel).parent), '12d-publication-input-')
    need(PurePosixPath(request_rel).name == 'request.json', 'REQUEST_LOCATION')
    raw = read_public(repo, request_rel)
    request = parse(raw)
    need(type(request) is dict and set(request) == {'root', 'binding', 'artifacts', 'suffixes'}, 'REQUEST_SCHEMA')
    root = leaf(request['root'], '12d-publication-output-')
    bind = binding(request['binding'])
    artifacts, suffixes = request['artifacts'], request['suffixes']
    need(type(artifacts) is list and type(suffixes) is dict and set(suffixes) == set(RECORDS), 'INPUT_INVENTORY')
    need(len(artifacts) <= MAX_FILES - 7, 'TOO_MANY_FILES')
    staged, output = {request_rel}, {}
    for item in artifacts:
        rel = relative(item)
        need(rel.parts[0] == 'artifacts' and len(rel.parts) > 1
             and rel.suffix in ('.md', '.txt', '.json', '.log'), 'ARTIFACT_SCOPE')
        source = staging + '/' + str(rel)
        need(source not in staged, 'DUPLICATE_INPUT')
        staged.add(source)
        output[str(rel)] = read_public(repo, source)
    records = []
    for record in RECORDS:
        rel = relative(suffixes[record])
        expected = 'suffixes/' + PurePosixPath(record).name + '.txt'
        need(str(rel) == expected, 'SUFFIX_SCOPE')
        source = staging + '/' + expected
        staged.add(source)
        suffix = read_public(repo, source)
        base = read_public(repo, record)
        output[expected] = suffix
        records.append({'destination': record, 'base_bytes': len(base), 'base_sha256': sha(base),
                        'suffix': root + '/' + expected, 'suffix_bytes': len(suffix),
                        'suffix_sha256': sha(suffix), 'final_bytes': len(base + suffix),
                        'final_sha256': sha(base + suffix)})
    need(set(inventory_files(repo, staging)) == staged, 'UNLISTED_STAGING_FILE')
    need(sum(len(v) for v in output.values()) <= MAX_TOTAL, 'TOTAL_SIZE_LIMIT')
    # Freeze every staged byte and the base records again before the first output write.
    need(read_public(repo, request_rel) == raw, 'INPUT_CHANGED')
    for rel, data in output.items():
        need(read_public(repo, staging + '/' + rel) == data, 'INPUT_CHANGED')
    for row in records:
        data = read_public(repo, row['destination'])
        need(len(data) == row['base_bytes'] and sha(data) == row['base_sha256'], 'BASE_CHANGED')
    packet = checked(repo, root, exists=False)
    freeze_rel = root + '.freeze.json'
    checked(repo, freeze_rel, exists=False)
    need(not packet.exists() and not (repo / freeze_rel).exists(), 'OUTPUT_EXISTS')
    packet.mkdir(mode=0o700)
    for folder in ('artifacts', 'suffixes'):
        (packet / folder).mkdir(mode=0o700)
    for rel, data in sorted(output.items()):
        parent = PurePosixPath(rel).parent
        current = packet
        for part in parent.parts:
            current = current / part
            if not current.exists():
                current.mkdir(mode=0o700)
        write_new(repo, root + '/' + rel, data)
    rows = [metadata(root + '/' + rel, data) for rel, data in sorted(output.items())]
    inv = {'schema': 1, 'root': root, 'binding': bind, 'records': records,
           'artifacts': [x for x in rows if '/artifacts/' in x['path']]}
    inv_data = encoded(inv)
    write_new(repo, root + '/publication-inventory.json', inv_data)
    rows.append(metadata(root + '/publication-inventory.json', inv_data))
    # No internal recursive manifest: the external freeze is the complete packet manifest.
    freeze = {'root': root, 'files': sorted(rows, key=lambda x: x['path'])}
    freeze_data = encoded(freeze)
    need(inventory_files(repo, root) == sorted(row['path'] for row in rows), 'PACKET_CHANGED')
    for row in rows:
        data = read_public(repo, row['path'])
        need(metadata(row['path'], data) == row, 'PACKET_CHANGED')
    write_new(repo, freeze_rel, freeze_data)
    sync(packet)
    return {'status': 'ASSEMBLED', 'packet_files': len(rows), 'record_suffixes': 5,
            'freeze_sha256': sha(freeze_data), 'publication_performed': False,
            'actual_recipient_scan_performed': False}


def validate_receipt(receipt, bind, freeze_sha, count):
    fields = {'gate_sha256', 'operation', 'plan_sha256', 'actor_arn', 'stage', 'observed_at',
              'public_manifest_sha256', 'files_scanned', 'matches', 'excluded'}
    need(type(receipt) is dict and set(receipt) == fields, 'SCAN_RECEIPT_SCHEMA')
    need(all(receipt[k] == v for k, v in bind.items()), 'SCAN_RECEIPT_BINDING')
    need(receipt['stage'] == 'post-freeze-scan' and receipt['public_manifest_sha256'] == freeze_sha
         and type(receipt['files_scanned']) is int and receipt['files_scanned'] == count
         and type(receipt['matches']) is int and receipt['matches'] == 0
         and receipt['excluded'] == EXCLUDED, 'SCAN_RECEIPT_RESULT')
    try:
        value = datetime.fromisoformat(receipt['observed_at'].replace('Z', '+00:00'))
        need(value.utcoffset() is not None, 'SCAN_RECEIPT_TIME')
    except (AttributeError, ValueError, TypeError):
        raise Blocked('SCAN_RECEIPT_TIME') from None


def verify(repo, freeze_rel, freeze_sha, receipt_rel, gate_sha, operation, after=False):
    """Metadata receipt is not proof of scan authenticity. Deployment verifies provenance."""
    need(type(freeze_sha) is str and HEX.fullmatch(freeze_sha), 'FREEZE_HASH_SCHEMA')
    freeze_rel = str(relative(freeze_rel))
    need(freeze_rel.endswith('.freeze.json'), 'FREEZE_LOCATION')
    root = leaf(freeze_rel[:-len('.freeze.json')], '12d-publication-output-')
    raw = read_public(repo, freeze_rel)
    need(sha(raw) == freeze_sha, 'FREEZE_CHANGED')
    freeze = parse(raw)
    need(type(freeze) is dict and set(freeze) == {'root', 'files'} and freeze['root'] == root,
         'FREEZE_SCHEMA')
    rows = freeze['files']
    need(type(rows) is list and 6 <= len(rows) <= MAX_FILES, 'FREEZE_SCHEMA')
    seen, total = set(), 0
    content = {}
    for row in rows:
        need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'FREEZE_ENTRY')
        rel = str(relative(row['path']))
        need(PurePosixPath(rel).is_relative_to(PurePosixPath(root)) and rel not in seen,
             'FREEZE_PATH')
        need(type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_FILE
             and type(row['sha256']) is str and HEX.fullmatch(row['sha256']), 'FREEZE_ENTRY')
        seen.add(rel)
        data = read_public(repo, rel)
        need(metadata(rel, data) == row, 'PACKET_CHANGED_RESCAN')
        total += len(data)
        content[rel] = data
    need(total <= MAX_TOTAL and set(inventory_files(repo, root)) == seen, 'PACKET_INCOMPLETE_RESCAN')
    inv = parse(content.get(root + '/publication-inventory.json', b'null'))
    need(type(inv) is dict and set(inv) == {'schema', 'root', 'binding', 'records', 'artifacts'}
         and type(inv['schema']) is int and inv['schema'] == 1 and inv['root'] == root, 'INVENTORY_SCHEMA')
    bind = binding(inv['binding'])
    need(bind['gate_sha256'] == gate_sha and bind['operation'] == operation, 'EXPECTED_BINDING')
    records, artifacts = inv['records'], inv['artifacts']
    need(type(records) is list and len(records) == 5 and type(artifacts) is list, 'INVENTORY_SCHEMA')
    need(all(type(row) is dict for row in records)
         and [row.get('destination') for row in records] == list(RECORDS), 'RECORD_SET')
    covered = {root + '/publication-inventory.json'}
    for row in artifacts:
        need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
             and row in rows and str(row['path']).startswith(root + '/artifacts/'), 'ARTIFACT_INVENTORY')
        need(row['path'] not in covered, 'ARTIFACT_DUPLICATE')
        covered.add(row['path'])
    for row in records:
        need(set(row) == {'destination', 'base_bytes', 'base_sha256', 'suffix', 'suffix_bytes',
                          'suffix_sha256', 'final_bytes', 'final_sha256'}, 'RECORD_SCHEMA')
        suffix_rel = root + '/suffixes/' + PurePosixPath(row['destination']).name + '.txt'
        need(row['suffix'] == suffix_rel and suffix_rel in content, 'SUFFIX_BINDING')
        covered.add(suffix_rel)
        suffix = content[suffix_rel]
        need(type(row['base_bytes']) is int and 0 <= row['base_bytes'] <= MAX_FILE
             and type(row['suffix_bytes']) is int and len(suffix) == row['suffix_bytes']
             and sha(suffix) == row['suffix_sha256']
             and type(row['final_bytes']) is int
             and row['final_bytes'] == row['base_bytes'] + len(suffix)
             and all(type(row[k]) is str and HEX.fullmatch(row[k])
                     for k in ('base_sha256', 'suffix_sha256', 'final_sha256')), 'SUFFIX_BINDING')
        destination = read_public(repo, row['destination'])
        if after:
            need(len(destination) == row['final_bytes'] and sha(destination) == row['final_sha256']
                 and sha(destination[:row['base_bytes']]) == row['base_sha256']
                 and destination[row['base_bytes']:] == suffix, 'PUBLISHED_BYTES_MISMATCH')
        else:
            need(len(destination) == row['base_bytes'] and sha(destination) == row['base_sha256']
                 and sha(destination + suffix) == row['final_sha256'], 'BASE_OR_SUFFIX_CHANGED')
    need(covered == seen, 'INVENTORY_INCOMPLETE')
    receipt_rel = str(relative(receipt_rel))
    need(str(PurePosixPath(receipt_rel).parent) == EVIDENCE
         and PurePosixPath(receipt_rel).name.startswith('12d-publication-scan-')
         and receipt_rel.endswith('.json'), 'SCAN_RECEIPT_LOCATION')
    receipt_raw = read_public(repo, receipt_rel)
    validate_receipt(parse(receipt_raw), bind, freeze_sha, len(rows))
    # A second pass rejects packet or destination changes during verification.
    need(read_public(repo, freeze_rel) == raw and read_public(repo, receipt_rel) == receipt_raw,
         'VERIFICATION_INPUT_CHANGED')
    need(set(inventory_files(repo, root)) == seen, 'PACKET_INCOMPLETE_RESCAN')
    for rel, data in content.items():
        need(read_public(repo, rel) == data, 'PACKET_CHANGED_RESCAN')
    for row in records:
        data = read_public(repo, row['destination'])
        need(sha(data) == row['final_sha256' if after else 'base_sha256'], 'DESTINATION_CHANGED')
    return {'status': 'VERIFIED_AFTER' if after else 'VERIFIED_BEFORE',
            'public_manifest_sha256': freeze_sha, 'record_count': 5, 'packet_files': len(rows),
            'exact_bytes_match': True, 'scan_receipt_binding_matches': True,
            'scan_authenticity_verified': False, 'publication_performed': False,
            'actual_recipient_scan_performed': False}


def main(argv=None):
    parser = PublicParser(description=__doc__)
    parser.add_argument('mode', choices=('assemble', 'verify-before', 'verify-after'))
    parser.add_argument('--repo', type=Path, default=REPO)
    parser.add_argument('--request')
    parser.add_argument('--freeze')
    parser.add_argument('--freeze-sha256')
    parser.add_argument('--scan-receipt')
    parser.add_argument('--gate-sha256')
    parser.add_argument('--operation')
    os.umask(0o077)
    try:
        args = parser.parse_args(argv)
        if args.mode == 'assemble':
            need(args.request and not any((args.freeze, args.freeze_sha256, args.scan_receipt,
                                          args.gate_sha256, args.operation)), 'CLI_OPTIONS')
            result = assemble(args.repo, args.request)
        else:
            need(not args.request and all((args.freeze, args.freeze_sha256, args.scan_receipt,
                                          args.gate_sha256, args.operation)), 'CLI_OPTIONS')
            result = verify(args.repo, args.freeze, args.freeze_sha256, args.scan_receipt,
                            args.gate_sha256, args.operation, args.mode == 'verify-after')
        print(json.dumps(result, sort_keys=True))
        return 0
    except Blocked as error:
        print(json.dumps({'status': 'BLOCKED-ON', 'code': str(error)}))
        return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print(json.dumps({'status': 'BLOCKED-ON', 'code': 'PUBLIC_INPUT_OR_FILESYSTEM_FAILURE'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

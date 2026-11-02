"""Coordinator evidence assembly only. No cloud/private/durable artifact access."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
PHASE = ROOT / 'docs/agent-runs/phase-12'
AP = PHASE / 'evidence/12d-billing-apply-proposal'
RR = PHASE / 'evidence/12d-billing-durable-plan-review-record'
SCRATCH = Path('/tmp/scholarchain-phase12d-billing-apply-proposal')
PROMPT = PHASE / 'reviewer-prompt-12d-billing-apply-proposal.md'
FIELDS = ['STATUS', 'OWNER', 'WORK ORDER', 'FILES CREATED', 'FILES MODIFIED',
          'COMMANDS RUN', 'TEST RESULTS', 'VALIDATION RESULTS', 'ASSUMPTIONS',
          'RISKS', 'MANUAL ACTION REQUIRED', 'BLOCKED-ON OWNER',
          'BLOCKED-ON EVIDENCE', 'NEXT GATE']

def sha(data):
    return hashlib.sha256(data).hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')

def run(argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    assert result.returncode == 0, (argv, result.returncode)
    return result.stdout

def info(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}

def unchanged(item):
    path = ROOT / item['path']
    data = path.read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
    if 'mtime_ns' in item:
        assert path.stat().st_mtime_ns == item['mtime_ns'], item['path']

pre = json.loads((RR / 'preflight.json').read_text())
assert run(['git', 'branch', '--show-current']).decode().strip() == pre['branch']
assert run(['git', 'rev-parse', 'HEAD']).decode().strip() == pre['head']
for item in pre['durable_packet_files']:
    unchanged(item)
unchanged(pre['human_record'])
freeze = ROOT / 'docs/agent-runs/phase-12/evidence/12d-billing-policy-amendment/source-freeze.json'
for item in json.loads(freeze.read_text())['files']:
    unchanged(item)

# Only already-public scratch output is copied, preserving its owner manifest.
manifest = json.loads((SCRATCH / 'artifact-manifest.json').read_text())
for item in manifest['files']:
    data = (SCRATCH / item['path']).read_bytes()
    assert sha(data) == item['sha256'] and len(data) == item['bytes']
for name in ['proposal.md', 'sources.json', 'owner-report.txt', 'artifact-manifest.json']:
    if (AP / name).exists():
        assert (AP / name).read_bytes() == (SCRATCH / name).read_bytes(), name
    else:
        shutil.copyfile(SCRATCH / name, AP / name)
proposal = (AP / 'proposal.md').read_text()
assert 'After all public content is fully assembled and frozen' in proposal
assert 'ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855' in proposal
attachment = Path('/Users/danny/.codex/attachments/755bfe5a-968b-4cb3-9d62-75311f39de3b/Pasted text.txt').read_bytes()
assert (RR / 'user-supplied-review.txt').read_bytes() == attachment
assert attachment in (PHASE / 'review.md').read_bytes()

save(AP / 'assembly-notes.json', {
    'recorded_utc': now(), 'scope': 'Public proposal/evidence assembly only',
    'infra_owner': '/root/infra_12d_apply_proposal',
    'no_execution_or_private_reads': True,
    'D2_followup': 'Infra owner corrected future exact-recipient scan to after final assembly/freeze; any subsequent content change requires rescan.',
    'lookup_erratum': 'Coordinator rg referenced nonexistent docs/phase-plan.md. rg emitted a missing-file diagnostic; the combined shell invocation ended 0 because later head/tail succeeded. Discovered the neutral evidence/12c/phase12-plan-at-start.md with rg --files and read it. No source/live failure or retry.',
    'assembly_erratum': 'First assemble-public.py exit1 at the D2 text assertion: check expected a paraphrase rather than the actual corrected sentence. Four public specialist files had been copied; no records appended yet. Corrected assertion to the actual sentence and verified existing copies byte-equal before resuming. No specialist content, source, private or cloud artifact changed.',
    'limits': 'Preservation proves selected 209 source files, 83 prior packet files and five record prefixes; not a full repository baseline.',
    'test_scope': 'No behavior change, tests or builds. Historical seven mock passes and sbt are not rerun.',
})

report = '''STATUS: COMPLETE — durable-plan verdict recorded and bounded apply proposal prepared; execution remains unapproved and blocked on later prerequisites.
OWNER: coordinator /root; specialist /root/infra_12d_apply_proposal, infra-engineer, authoring only; native model inherited, exact version not exposed. No reviewer or child launched.
WORK ORDER: User-invoked NEXT PROMPT in attachment 755bfe5a-968b-4cb3-9d62-75311f39de3b/Pasted text.txt. Branch phase-12, HEAD/base 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f; record durable-plan APPROVE and prepare only an apply proposal.
FILES CREATED: evidence/12d-billing-durable-plan-review-record/**; evidence/12d-billing-apply-proposal/**; reviewer-prompt-12d-billing-apply-proposal.md under docs/agent-runs/phase-12/. Inventories/manifests enumerate exact new files.
FILES MODIFIED: Append-only prompt.md, review.md, repairs.md, owner-report.md and test-report.md under docs/agent-runs/phase-12/. No human record, source, lock or prior packet change.
COMMANDS RUN: Public cat/rg/rg --files/head/tail/sed/pwd/ls; git branch --show-current, git rev-parse HEAD, git status --short --untracked-files=all, git diff --check and read-only git show for record prefixes; public python3 -I evidence assembly/hash/byte/mtime/prefix/manifest/field/generic-address validation through retained assemble-public.py. Exact primary assembly command: python3 -I docs/agent-runs/phase-12/evidence/12d-billing-apply-proposal/assemble-public.py. First assembly exit1 from a paraphrased D2-text assertion, corrected to actual sentence before resuming; no records appended on that failure. Infra public-document research is recorded in sources.json. Wrong-filename lookup/masked shell exit and assembly failure are disclosed in assembly-notes.json. No Terraform/AWS/login/console/build/test/private/durable access, reviewer launch, commit or push.
TEST RESULTS: Not run; proposal/documentation only. Prior durable-plan seven mock passes, six assertions/four expected-failure runs and earlier JDK17 full sbt gate are historical evidence only; no new test pass claimed.
VALIDATION RESULTS: Supplied review retained/appended verbatim. P2 satisfied only at plan stage. D1 append-only timing erratum prepared, old evidence preserved. Public owner packet hashes verified; 209 source hashes/bytes/mtimes, 83 prior packet files, five old record prefixes and human record 1334 bytes/abe3a50a preserved. Final receipt files record observed prefix/hash/manifest/status/diff/generic-address checks; exact-recipient scan not run in this authoring-only scope. Proposal binds 6631-byte plan ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855. D2 future scan ordering corrected by infra owner; D3 remains informational.
ASSUMPTIONS: Previously independently reviewed public metadata remains authoritative. No new inspection of actual plan/state/toolchain, private recipient or current cloud state. Prior uncommitted work is retained under explicit user-invoked work order; no clean-tree exception granted.
RISKS: P3 absence/identity and effective permissions, state backup, live acceptance/delivery/accounting, current spend/allowance, IAM inventory/refresh and EMR runtime remain unverified. Same-disk backups do not protect disk failure. No approved executable wrapper or clean execution checkout currently demonstrated. G1/G2/F4/P3/B1/B2/B3/R1/N19/N20 remain open. No spending authority or Phase12D completion.
MANUAL ACTION REQUIRED: User launches the prepared independent proposal review. Later bounded infra wrapper authorship/offline tests and independent script review; human source-control/clean-checkout decision, own-words G1 affirmation and personally written exact-checksum/identity/window execution gate. No repeated login/email input requested in this authoring task.
BLOCKED-ON OWNER: None for current proposal handoff. Future execution: human architect for G1/source-control/window/approval; infra-engineer for reviewed executable wrapper; deploy-engineer after gates; incident-responder on failure.
BLOCKED-ON EVIDENCE: Future apply requires proposal/script APPROVE, approved source-controlled wrapper and clean execution checkout, G1, personal full-checksum/window gate and fresh in-window P3 identity/exact-name absence. No apply, backup-success or live readback receipt yet exists.
NEXT GATE: User-launched independent APPLY PROPOSAL ONLY review with explicit D1 assessment; never launch reviewer. If approved, separately bounded wrapper authorship/offline testing/review only, no automatic live action. Stop after this handoff.
'''
assert re.findall(r'^([A-Z][A-Z -]+):', report, re.M) == FIELDS
(AP / 'coordinator-report.txt').write_text(report)
for name in ['owner-report.md', 'test-report.md']:
    with (PHASE / name).open('a') as stream:
        stream.write('\n\n## Subphase 12D — durable-plan verdict and bounded apply proposal\n\n')
        stream.write(report)

prefixes = []
for item in pre['records']:
    path = ROOT / item['path']
    data = path.read_bytes()
    assert sha(data[:item['bytes']]) == item['sha256'], item['path']
    head = subprocess.run(['git', 'show', pre['head'] + ':' + item['path']], cwd=ROOT, capture_output=True)
    assert head.returncode in [0, 128]
    head_ok = data.startswith(head.stdout) if head.returncode == 0 else None
    assert head_ok is not False, item['path']
    prefixes.append({'path': item['path'], 'before_bytes': item['bytes'], 'before_sha256': item['sha256'],
                     'prefix_preserved': True, 'head_prefix_preserved': head_ok,
                     'after_bytes': len(data), 'after_sha256': sha(data)})
save(RR / 'record-prefix-check.json', {'checked_utc': now(), 'records': prefixes, 'review_verbatim': True, 'human_record_unchanged': True})
for item in pre['durable_packet_files']:
    unchanged(item)
for item in json.loads(freeze.read_text())['files']:
    unchanged(item)
save(AP / 'preservation-check.json', {'checked_utc': now(), 'source_files_hash_bytes_mtime': 209,
                                    'prior_packet_files': 83, 'mismatches': [], 'human_record': pre['human_record']})
run(['git', 'diff', '--check'])
(AP / 'diff-check.log.txt').write_bytes(b'')
save(AP / 'diff-check-result.json', {'command': ['git', 'diff', '--check'], 'exit': 0, 'observed_utc': now()})

# Declare final paths first so Git inventory includes every new artifact.
for folder, names in [(AP, ['final-status.log.txt', 'handoff-files.json', 'public-address-scan.json', 'evidence-manifest.json']),
                       (RR, ['evidence-manifest.json'])]:
    for name in names:
        assert not (folder / name).exists(), name
        (folder / name).write_text('{}\n')
status = run(['git', 'status', '--short', '--untracked-files=all'])
(AP / 'final-status.log.txt').write_bytes(status)
before = (RR / 'preflight-status.log.txt').read_bytes().splitlines()
after = status.splitlines()
assert set(before) <= set(after), 'Preexisting status entry changed/disappeared'
added = sorted(set(after) - set(before))
new_files = [str(p.relative_to(ROOT)) for folder in [AP, RR] for p in folder.rglob('*') if p.is_file()]
new_files.append(str(PROMPT.relative_to(ROOT)))
assert len(after) == pre['status_entries'] + len(new_files)
assert len(added) == len(new_files)
save(AP / 'handoff-files.json', {'observed_utc': now(), 'base_status_entries': pre['status_entries'],
    'final_status_entries': len(after), 'new_files': sorted(new_files),
    'new_file_count': len(new_files), 'preexisting_status_entries_retained': True,
    'five_append_only_records': [x['path'] for x in pre['records']]})

# Generic scan only; no access to the actual private recipient. Final content is now frozen.
excluded_names = {'evidence-manifest.json', 'public-address-scan.json'}
scan_data = [(str(p.relative_to(ROOT)), p.read_bytes()) for folder in [AP, RR]
             for p in folder.rglob('*') if p.is_file() and p.name not in excluded_names]
scan_data.append((str(PROMPT.relative_to(ROOT)), PROMPT.read_bytes()))
for item in pre['records']:
    scan_data.append((item['path'] + ' [new suffix only]', (ROOT / item['path']).read_bytes()[item['bytes']:]))
pattern = re.compile(rb'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
unknown = []
fixture_count = 0
for label, data in scan_data:
    matches = pattern.findall(data)
    fixture_count += sum(match == b'synthetic@example.invalid' for match in matches)
    if any(match != b'synthetic@example.invalid' for match in matches):
        unknown.append(label)
assert not unknown, unknown
save(AP / 'public-address-scan.json', {'checked_utc': now(), 'type': 'Generic email-pattern scan ONLY; not exact-recipient verification',
    'scope_units': len(scan_data), 'scope': 'Both newly assembled public packets, reviewer prompt and five appended record suffixes',
    'exclusions': 'This count-only receipt and hash-only root manifests to avoid recursive mutation; original specialist manifest included',
    'reserved_fixture_matches': fixture_count, 'other_address_matches': 0,
    'private_data_access': False, 'future_D2': 'Exact-recipient check after final public assembly/freeze only in later explicitly authorized wrapper; rescan after content changes.'})
for folder in [RR, AP]:
    entries = []
    for path in sorted(folder.rglob('*')):
        if path.is_file() and path != folder / 'evidence-manifest.json':
            data = path.read_bytes()
            entries.append({'path': str(path.relative_to(folder)), 'bytes': len(data), 'sha256': sha(data)})
    save(folder / 'evidence-manifest.json', {'scope': 'Public proposal-only handoff', 'self_excluded': True, 'files': entries})
    observed = json.loads((folder / 'evidence-manifest.json').read_text())
    assert len(observed['files']) + 1 == len([p for p in folder.rglob('*') if p.is_file()])
    for item in observed['files']:
        data = (folder / item['path']).read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['bytes']
run(['git', 'diff', '--check'])
assert run(['git', 'status', '--short', '--untracked-files=all']) == status
print(json.dumps({'scope': 'Proposal only; nothing executed', 'status_before': pre['status_entries'],
                  'status_after': len(after), 'new_files': len(new_files), 'source_files_unchanged': 209,
                  'prior_packet_files_unchanged': 83, 'five_prefixes_preserved': True,
                  'generic_scan_scope_units': len(scan_data), 'unexpected_address_matches': 0,
                  'diff_check_exit': 0, 'manifest_mismatches': 0}))

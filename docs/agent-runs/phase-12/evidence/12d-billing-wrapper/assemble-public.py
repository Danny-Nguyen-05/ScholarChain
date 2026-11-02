"""Coordinator-only public evidence assembly; no deployment or private reads."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
PHASE = ROOT / 'docs/agent-runs/phase-12'
E = PHASE / 'evidence/12d-billing-wrapper'
RR = PHASE / 'evidence/12d-billing-apply-proposal-review-record'
SCRATCH = Path('/tmp/scholarchain-phase12d-billing-wrapper')
PROMPT = PHASE / 'reviewer-prompt-12d-billing-wrapper.md'
FIELDS = ['STATUS', 'OWNER', 'WORK ORDER', 'FILES CREATED', 'FILES MODIFIED',
          'COMMANDS RUN', 'TEST RESULTS', 'VALIDATION RESULTS', 'ASSUMPTIONS',
          'RISKS', 'MANUAL ACTION REQUIRED', 'BLOCKED-ON OWNER',
          'BLOCKED-ON EVIDENCE', 'NEXT GATE']

def sha(data):
    return hashlib.sha256(data).hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def command(argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    assert result.returncode == 0, (argv, result.returncode)
    return result.stdout

def verify(row, metadata=False):
    path = ROOT / row['path']
    data = path.read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    if metadata:
        assert path.stat().st_mtime_ns == row['mtime_ns'], row['path']

pre = json.loads((RR / 'preflight.json').read_text())
assert command(['git', 'rev-parse', 'HEAD']).decode().strip() == pre['head']
assert command(['git', 'branch', '--show-current']).decode().strip() == pre['branch']
for row in pre['prior_public_files']:
    verify(row)
verify(pre['human_record'])
freeze_path = PHASE / 'evidence/12d-billing-policy-amendment/source-freeze.json'
freeze = json.loads(freeze_path.read_text())['files']
for row in freeze:
    verify(row, metadata=True)

manifest = json.loads((SCRATCH / 'artifact-manifest.json').read_text())
assert len(manifest['files']) == 13
for row in manifest['files']:
    data = (SCRATCH / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    if (E / row['path']).exists():
        assert (E / row['path']).read_bytes() == data, row['path']
    else:
        shutil.copyfile(SCRATCH / row['path'], E / row['path'])
shutil.copyfile(SCRATCH / 'artifact-manifest.json', E / 'artifact-manifest.json')
result = json.loads((E / 'result.json').read_text())
assert (result['final_offline_tests'], result['final_failures'], result['final_errors']) == (37, 0, 0)
assert result['final_A1_assertions'] == 7
assert result['attempts'][-1]['terraform_exits'] == [0, 0, 0]
assert 'Ran 37 tests' in (E / 'offline-tests-attempt4.log.txt').read_text()
assert (E / 'offline-tests-attempt4.log.txt').read_text().rstrip().endswith('OK')
assert all(json.loads((E / 'a1-result.json').read_text())['checks'].values())
assert result['attempts'][-1]['final_wrapper_sha256'] == result['final_wrapper_sha256']
for row in result['source_files']:
    verify(row)
assert len(result['source_files']) == 5
pins = json.loads((ROOT / 'scripts/billing/reviewed-pins.json').read_text())
assert len(pins['source_freeze']) == 209 and len(pins['config']) == 7
assert pins['source_freeze'] == [{key: row[key] for key in ['path', 'bytes', 'sha256']} for row in freeze]

review = (RR / 'user-supplied-review.txt').read_bytes()
attachment = Path('/Users/danny/.codex/attachments/072c1d14-43a6-4edf-9b30-faebe176918f/Pasted text.txt').read_bytes()
assert review == attachment and review in (PHASE / 'review.md').read_bytes()
repair_note = '\n\n## Subphase 12D — wrapper offline evidence prepared\n\nD1 remains independently CLOSED. A1 and A2 repairs are prepared for independent acceptance, not self-closed: final37 feature tests passed; final pinned1.13.5 terraform_data scratch init/plan/saved-apply exits0/0/0 and all7 state/lock assertions passed against wrapper SHA81fe564942a9f53ccf40236f32569a0f3fbdba13119c1ca3a23305d64c0039f0. Explicit config/errored.tfstate preservation is tested. Earlier failed harness attempts retained. G1/G2/F4/P3/B1/B2/B3/R1/N19/N20, source-control/clean execution and all human/live gates remain open. No production wrapper mode was invoked.\n'
if not (PHASE / 'repairs.md').read_text().endswith(repair_note):
    with (PHASE / 'repairs.md').open('a') as out:
        out.write(repair_note)

report = '''STATUS: COMPLETE — apply-proposal verdict recorded; bounded wrapper and offline-test packet prepared for independent review. No live execution approved.
OWNER: coordinator /root; infra owner /root/infra_12d_apply_proposal, sole writer scripts/billing/**; inherited native model, exact version not exposed. No children/reviewer launched; all specialist jobs finished.
WORK ORDER: User-invoked NEXT PROMPT from attachment 072c1d14-43a6-4edf-9b30-faebe176918f/Pasted text.txt. Branch phase-12, HEAD/base5ca8406bad5fe55f732458fa0cbd5d561ac83d8f. Existing687-entry work retained; no commit/push or clean-tree exception.
FILES CREATED: Five scripts/billing/** files listed in source-file-hashes.json; evidence/12d-billing-wrapper/**; evidence/12d-billing-apply-proposal-review-record/**; reviewer-prompt-12d-billing-wrapper.md, all evidence under docs/agent-runs/phase-12/. Exact inventory and hashes retained.
FILES MODIFIED: Append-only prompt.md, review.md, repairs.md, owner-report.md and test-report.md. No preexisting source, reviewed proposal/packet, Terraform lock or human record modified.
COMMANDS RUN: Infra exact commands/attempts in result.json and owner-report.txt: python3 -I scripts/billing/tests/test_budget_execution.py exits1/1/0/0; python3 -I scripts/billing/tests/terraform_state_binding.py exits0/0, each only3 scratch terraform_data calls exits0/0/0. Coordinator public cat/rg/rg --files/sed/tail/ls and git branch/rev-parse/status/diff; python3 -I public preflight/hash/prefix/byte/mtime/manifest/report-field/address checks. Exact assembly: python3 -I docs/agent-runs/phase-12/evidence/12d-billing-wrapper/assemble-public.py. Coordinator failed lookups, concurrent-snapshot assertion and unnecessary old temporary directory metadata listing are disclosed in process-notes.json; listing included private-input filename/mode/size only, no contents read. No further private-directory inspection. No production mode, AWS/IAM/login/console/paid call, actual plan/state/private-input content/credentials/config/cache or durable primary/backups access; no build or reviewer invocation.
TEST RESULTS: Final37 feature tests passed,0failures/0errors. Final A1 against wrapper SHA81fe564942a9f53ccf40236f32569a0f3fbdba13119c1ca3a23305d64c0039f0: pinned Terraform1.13.5, isolated credential-free terraform_data, exact apply argv builder/PrivateRunner,3calls exits0/0/0,7assertions passed. Initial33-test run12failures/15errors (macOS temp symlink ancestry); second1failure (OS-added child environment); third33passed; fourth37passed after additional controls/tests. A1 first passed and reran after final launch changes. No new sbt/full-tree Terraform result claimed; only explicit offline gates run.
VALIDATION RESULTS: Verdict retained/appended verbatim; D1 closed by independent reviewer. A1/A2 evidence prepared pending independent acceptance. Reviewed-hash CLI modes p3-check/apply/readback/post-freeze-scan; gated exact identity/window/source/plan, private logs, no retries, opaque backup/recovery including errored.tfstate, safe readback/scan. All5script hashes/bytes match, prior105public files and209source hashes/bytes/mtimes unchanged; human1334bytes/abe3a50a unchanged; five record prefixes preserved. Receipts record final manifest/status/diff/generic-email checks. Current generic scan only; actual recipient remains unknown and untouched.
ASSUMPTIONS: Retained offline logs/results accurately reflect delegated observed runs, validated by their manifests. Prior durable metadata remains authoritative; current real toolchain/plan/state/AWS CLI/cloud context not inspected. SHA cannot prove human-gate authorship; external personal provenance remains required. A1 tests argv builder/launch primitive with scratch Policy; it does not run the full real authorization gate.
RISKS: Effective live permissions, budget absence/ownership/create/tag/CUSTOM/CostTypes acceptance, current allowance, private delivery, F4 inventory/refresh and EMR remain unverified. Same-disk backup limitation; alerts are not caps. Scripts are currently uncommitted. Scan-only bounded new-packet allowance is documented/tested and does not waive wholly clean live-stage checkout. G1/G2/F4/P3/B1/B2/B3/R1/N19/N20 remain open. No spending authority or Phase12D completion.
MANUAL ACTION REQUIRED: User launches independent wrapper/offline-test review. Later bundle human source-control/clean-checkout decision, own-words G1 affirmation, and personally written full plan/proposal/wrapper checksum/actor/account/profile/role/dated-window gate; fresh human login/STS and P3 only at approved execution. No approval template/signature or real gate written by agents; test gates are explicitly synthetic fixtures.
BLOCKED-ON OWNER: None for this authoring handoff. Future execution: user-launched independent reviewer, human architect/coordinator and deploy-engineer after prerequisites; incident-responder for future failure diagnosis.
BLOCKED-ON EVIDENCE: Independent script/test APPROVE including A1/A2 acceptance; human source-controlled clean execution checkout and G1; personally written exact-checksum/identity/window gate; fresh in-window P3. No real apply/backup/readback proof exists.
NEXT GATE: User-launched independent WRAPPER/OFFLINE TESTS ONLY review. If approved, prepare concrete bundled human execution-gate handoff; no automatic live run. No reviewer launch, commit/push, Phase13 or next subphase. Stop after handoff.
'''
assert re.findall(r'^([A-Z][A-Z -]+):', report, re.M) == FIELDS
assert re.findall(r'^([A-Z][A-Z -]+):', (E / 'owner-report.txt').read_text(), re.M) == FIELDS
(E / 'coordinator-report.txt').write_text(report)
for name in ['owner-report.md', 'test-report.md']:
    if not (PHASE / name).read_text().endswith(report):
        with (PHASE / name).open('a') as stream:
            stream.write('\n\n## Subphase 12D — bounded billing wrapper and offline tests\n\n' + report)

prefixes = []
for row in pre['records']:
    data = (ROOT / row['path']).read_bytes()
    assert sha(data[:row['bytes']]) == row['sha256'], row['path']
    prefixes.append({**row, 'prefix_preserved': True, 'after_bytes': len(data), 'after_sha256': sha(data)})
save(RR / 'record-prefix-check.json', {'checked_utc': now(), 'records': prefixes, 'review_verbatim': True})
for row in pre['prior_public_files']:
    verify(row)
for row in freeze:
    verify(row, metadata=True)
verify(pre['human_record'])
save(E / 'preservation-check.json', {'checked_utc': now(), 'prior_public_files_checked': 105,
    'source_hash_bytes_mtime_checked': 209, 'new_source_files': result['source_files'],
    'human_record': pre['human_record'], 'mismatches': [], 'scope': 'Selected prior packets/source freeze/five record prefixes; not a full-repository baseline'})
command(['git', 'diff', '--check'])
save(E / 'diff-check-result.json', {'command': ['git', 'diff', '--check'], 'exit': 0, 'observed_utc': now()})

for folder, names in [(E, ['final-status.log.txt', 'handoff-files.json', 'public-address-scan.json', 'evidence-manifest.json']),
                       (RR, ['evidence-manifest.json'])]:
    for name in names:
        if not (folder / name).exists():
            (folder / name).write_text('{}\n')
status = command(['git', 'status', '--short', '--untracked-files=all'])
(E / 'final-status.log.txt').write_bytes(status)
old = (RR / 'preflight-status.log.txt').read_bytes().splitlines()
new = status.splitlines()
assert set(old) <= set(new), 'Existing status path changed/disappeared'
created = sorted(str(f.relative_to(ROOT)) for folder in [E, RR, ROOT / 'scripts/billing']
                 for f in folder.rglob('*') if f.is_file())
created.append(str(PROMPT.relative_to(ROOT)))
assert len(new) == 687 + len(created)
assert len(set(new) - set(old)) == len(created)
save(E / 'handoff-files.json', {'observed_utc': now(), 'base_status_entries': 687,
    'final_status_entries': len(new), 'new_file_count': len(created), 'new_files': sorted(created),
    'preexisting_status_entries_preserved': True, 'five_append_only_records': [r['path'] for r in pre['records']]})

# Generic-only scan of all final public content, no actual recipient access.
excluded = {'public-address-scan.json', 'evidence-manifest.json'}
scan = [(str(f.relative_to(ROOT)), f.read_bytes()) for folder in [E, RR, ROOT / 'scripts/billing']
        for f in folder.rglob('*') if f.is_file() and f.name not in excluded]
scan.append((str(PROMPT.relative_to(ROOT)), PROMPT.read_bytes()))
for row in pre['records']:
    scan.append((row['path'] + ' [new suffix only]', (ROOT / row['path']).read_bytes()[row['bytes']:]))
pattern = re.compile(rb'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
unexpected, fixture_count = [], 0
for label, data in scan:
    found = pattern.findall(data)
    allowed = {b'synthetic@example.invalid'}
    if label == 'scripts/billing/tests/test_budget_execution.py':
        allowed.add(b'other' + b'@example.invalid')
    fixture_count += sum(value in allowed for value in found)
    if any(value not in allowed for value in found):
        unexpected.append(label)
assert not unexpected, unexpected
save(E / 'public-address-scan.json', {'checked_utc': now(), 'type': 'Generic email-pattern scan ONLY',
    'scope': 'Both final new public packets, all5script files, reviewer prompt and5appended suffixes',
    'scope_units': len(scan), 'reserved_fixture_matches': fixture_count, 'other_address_matches': 0,
    'fixture_allowlist': 'Reserved synthetic address in public artifacts; additionally the reserved other address only in the exact authored subscriber-drift test source. No non-reserved address permitted.',
    'exclusions': 'This count-only receipt and hash-only root manifests; original specialist manifest included',
    'actual_recipient_processing': False, 'future_requirement': 'Authorized runtime exact-recipient scan after final assembly/freeze; repeat after any change'})
for folder in [RR, E]:
    rows = []
    for f in sorted(folder.rglob('*')):
        if f.is_file() and f != folder / 'evidence-manifest.json':
            data = f.read_bytes()
            rows.append({'path': str(f.relative_to(folder)), 'bytes': len(data), 'sha256': sha(data)})
    save(folder / 'evidence-manifest.json', {'scope': 'Public wrapper/offline handoff only', 'self_excluded': True, 'files': rows})
    for row in rows:
        data = (folder / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    assert len(rows) + 1 == len([f for f in folder.rglob('*') if f.is_file()])
command(['git', 'diff', '--check'])
assert command(['git', 'status', '--short', '--untracked-files=all']) == status
print(json.dumps({'tests_passed': 37, 'A1_assertions_passed': 7, 'source_files_preserved': 209,
    'prior_files_preserved': 105, 'human_record_unchanged': True, 'five_prefixes_preserved': True,
    'manifest_mismatches': 0, 'generic_scope_units': len(scan), 'other_addresses': 0,
    'git_status_entries': len(new), 'new_files': len(created), 'diff_check_exit': 0,
    'live_execution': False}))

"""Coordinator public evidence assembly. Never invokes publication or budget helpers."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
PHASE = ROOT / 'docs/agent-runs/phase-12'
E = PHASE / 'evidence/12d-billing-publication-helper'
SCRATCH = Path('/tmp/scholarchain-phase12d-billing-publication-helper')
REVIEWER = PHASE / 'reviewer-prompt-12d-billing-publication-helper.md'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def verify(row, mtime=False):
    f = ROOT / row['path']
    data = f.read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    if mtime:
        assert f.stat().st_mtime_ns == row['mtime_ns'], row['path']

def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    assert result.returncode == 0, (args, result.returncode)
    return result.stdout

pre = json.loads((E / 'preflight.json').read_text())
assert git('rev-parse', 'HEAD').decode().strip() == pre['head']
assert git('branch', '--show-current').decode().strip() == pre['branch']
for row in pre['prior_public_files'] + pre['scripts'] + [pre['human_record']]:
    verify(row)
freeze = json.loads((PHASE / 'evidence/12d-billing-policy-amendment/source-freeze.json').read_text())['files']
for row in freeze:
    verify(row, True)
infra = E / 'infra'
infra.mkdir()
manifest = json.loads((SCRATCH / 'artifact-manifest.json').read_text())
for row in manifest['files']:
    data = (SCRATCH / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
    shutil.copyfile(SCRATCH / row['path'], infra / row['path'])
shutil.copyfile(SCRATCH / 'artifact-manifest.json', infra / 'artifact-manifest.json')
result = json.loads((infra / 'result.json').read_text())
assert result['final_tests'] > 0 and result['failures'] == result['errors'] == 0
new_sources = result['source_files']
assert len(new_sources) == 3
for row in new_sources:
    verify(row)
all_scripts = []
for path in sorted((ROOT / 'scripts/billing').rglob('*')):
    if path.is_file():
        data = path.read_bytes()
        all_scripts.append({'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
assert len(all_scripts) == 8
save(E / 'all-script-bindings.json', {'scope': 'Future personal wrapper_files gate must bind all8files; historical five-file gate insufficient',
    'files': all_scripts, 'original_five_unchanged': True, 'new_helper_independently_approved': False})
count = result['final_tests']
fields = [
('STATUS', 'COMPLETE — user-selected offline publication helper and fixture-test evidence prepared for independent review only.'),
('OWNER', 'Coordinator /root owns phase evidence; /root/infra_12d_publication_helper is infra-engineer sole writer of three new scripts/billing files. Native model inherited, exact version not exposed. No child/reviewer launched.'),
('WORK ORDER', 'User answered yes to offline helper preparation/testing; exact question/reply in human-choice.json. W3 assembly/freeze/publication equality tooling only. Branch phase-12, HEAD5ca8406bad5fe55f732458fa0cbd5d561ac83d8f; preflight780entries.'),
('FILES CREATED', 'Three new script/test/documentation files in infra/result.json; evidence/12d-billing-publication-helper/** and reviewer-prompt-12d-billing-publication-helper.md under docs/agent-runs/phase-12/. Exact inventory/manifests retained.'),
('FILES MODIFIED', 'Five phase records appended only by coordinator. All five existing billing scripts, approved proposals/packets, original source/locks and human record unchanged.'),
('COMMANDS RUN', 'Infra exact offline commands/counts/exits/failures in infra/result.json and owner-report.txt; python3 -I fixture tests only. Coordinator public cat/sed/rg, git branch/HEAD/status/diff and python3 -I snapshot/hash/byte/mtime/prefix/manifest/report/generic-address checks. Exact assembly: python3 -I docs/agent-runs/phase-12/evidence/12d-billing-publication-helper/assemble-public.py. One public new-scratch-directory lookup exit2 disclosed in coordinator-notes.json. No actual production helper/budget wrapper/private scan/Terraform/AWS/CLI/login/build, durable/private/actual state/plan/credential/config/cache access, commit/push or reviewer launch.'),
('TEST RESULTS', f'New helper final offline suite: {count}passed,0failures,0errors. All attempts and limitations retained in infra/result.json/logs; synthetic public fixtures only. No existing wrapper/A1/full sbt rerun; independently accepted46wrappertests/7A1checks remain historical. No behavior change to those existing files.'),
('VALIDATION RESULTS', 'New source hashes match infra evidence; all8file future gate binding retained, original5 unchanged. Public packet includes exact5suffix copies/base+suffix hashes, wrapper-compatible complete external freeze, strict receipt metadata verification and exact publication equality without appending records or private scanning.190prior public files,209original source hashes/bytes/mtimes,5record prefixes and1334byte human record/abe3a50a preserved. Final manifest/status/diff/generic-address checks retained; no actual-recipient scan claimed.'),
('ASSUMPTIONS', 'Synthetic wrapper receipt fixtures are not authentic runtime proof. Receipt authenticity/freshness and source/gate/window supervision remain external deployment-gate checks. Only explicit public staging inputs may be supplied; helper is not a sanitizer. Future canonical checkout workflow must exclude staging and scan receipt until permitted stage, as documented.'),
('RISKS', 'W3 remains open until actual approved final assembly/private scan/equality evidence. Helper does not publish records or provide atomic five-file transactions; later additions invalidate coverage. Future gate must bind all8scripts. Human source-control/clean canonical checkout, R1residualrisk acceptance, actual dated window and personal execution gate pending. No active budget/spend/EMR readiness or phase completion. Other open gates carried unchanged.'),
('MANUAL ACTION REQUIRED', 'User launches helper-only independent review. After approval resume concise remaining human sourcecontrol/R1risk/window/personal-gate decisions. No fresh login/email/CLI check requested here; previous G1/H1/CLI observations remain evidence, not apply authority.'),
('BLOCKED-ON OWNER', 'None for authoring handoff; independent reviewer/human architect/coordinator/deploy owner hold future execution gates. Incident-responder on unknown runtime completion.'),
('BLOCKED-ON EVIDENCE', 'Helper review APPROVE plus committed all8file release/clean canonical checkout, personal exact-plan/proposal/script/identity/window gate, R1acknowledgment, fresh P3 and actual W3finalpublication coverage. No actual private scan or budget execution proof.'),
('NEXT GATE', 'User-launched independent HELPER/OFFLINE TESTS ONLY review. No automatic production helper/private scan/AWS work, reviewer launch, commit/push or Phase13. Stop after handoff.')]
assert len(fields) == 14
report = '\n'.join(k + ': ' + v for k, v in fields) + '\n'
(E / 'coordinator-report.txt').write_text(report)
for name in ['owner-report.md', 'test-report.md']:
    with (PHASE / name).open('a') as stream:
        stream.write('\n\n## Subphase 12D — offline publication helper and fixture tests\n\n' + report)
with (PHASE / 'review.md').open('a') as stream:
    stream.write('\n\n## Subphase 12D offline publication helper — review pending\n\nNo new independent verdict yet. User-selected helper authorship/tests prepared for user-launched review only; no live authority.\n')
with (PHASE / 'repairs.md').open('a') as stream:
    stream.write(f'\n\n## Subphase 12D — W3helper evidence prepared\n\nThree new public-helper files prepared;{count}offline tests passed. Existing five scripts unchanged. W3tooling prepared for independent acceptance, W3actualpublication gate still OPEN. All8script hashes now required in future personal gate. Separate assembly workspace/canonical frozen-packet transfer and postscan receipt ordering documented/tested; helper never appends records, invokes scanner or reads recipient. R1residualrisk/window/sourcecontrol/personal gate remain pending; W1/W2/A1/A2closed.\n')
prefix = []
for row in pre['records']:
    data = (ROOT / row['path']).read_bytes()
    assert sha(data[:row['bytes']]) == row['sha256']
    prefix.append({**row, 'prefix_preserved': True, 'after_bytes': len(data), 'after_sha256': sha(data)})
save(E / 'preservation-check.json', {'records': prefix, 'prior_public_files':190, 'original_billing_scripts':5,
    'source_hash_bytes_mtime':209, 'human_record':pre['human_record'], 'mismatches':[]})
for row in pre['prior_public_files'] + pre['scripts'] + [pre['human_record']]:
    verify(row)
git('diff', '--check')
save(E / 'diff-check-result.json', {'command':['git','diff','--check'], 'exit':0})
for name in ['handoff-files.json','final-status.log.txt','public-address-scan.json','evidence-manifest.json']:
    (E / name).write_text('{}\n')
status = git('status','--short','--untracked-files=all')
(E / 'final-status.log.txt').write_bytes(status)
old = (E / 'preflight-status.log.txt').read_bytes().splitlines()
assert set(old) <= set(status.splitlines())
created = sorted(str(f.relative_to(ROOT)) for f in E.rglob('*') if f.is_file())
created += [row['path'] for row in new_sources] + [str(REVIEWER.relative_to(ROOT))]
assert len(status.splitlines()) == 780 + len(created)
save(E / 'handoff-files.json', {'baseline_status_entries':780, 'final_status_entries':len(status.splitlines()),
    'new_file_count':len(created), 'new_files':sorted(created), 'five_records_appended':[row['path'] for row in pre['records']]})
scan = [(str(f.relative_to(ROOT)), f.read_bytes()) for f in E.rglob('*') if f.is_file()
        and f.name not in {'evidence-manifest.json','public-address-scan.json'}]
scan += [(row['path'], (ROOT / row['path']).read_bytes()) for row in new_sources]
scan.append((str(REVIEWER.relative_to(ROOT)),REVIEWER.read_bytes()))
for row in pre['records']:
    scan.append((row['path']+' [new suffix only]', (ROOT / row['path']).read_bytes()[row['bytes']:]))
pattern = re.compile(rb'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
fixtures = 0
for label, data in scan:
    values = pattern.findall(data)
    assert all(value == b'synthetic@example.invalid' for value in values), label
    fixtures += len(values)
save(E / 'public-address-scan.json', {'type':'Generic email-pattern only; not actual-recipient scan',
    'scope':'Finalnewpacket/new3sources/reviewerprompt/fiveappendedsuffixes','units':len(scan),
    'reserved_fixture_matches':fixtures,'other_matches':0,'private_access':False,
    'exclusions':'Count-only scan receipt and hash-only root manifest; no arbitrary prose exclusion'})
rows = []
for f in sorted(E.rglob('*')):
    if f.is_file() and f != E / 'evidence-manifest.json':
        data = f.read_bytes()
        rows.append({'path':str(f.relative_to(E)), 'bytes':len(data), 'sha256':sha(data)})
save(E / 'evidence-manifest.json', {'scope':'Public helper authoring/offline evidence only','self_excluded':True,'files':rows})
for row in rows:
    data = (E / row['path']).read_bytes()
    assert len(data)==row['bytes'] and sha(data)==row['sha256']
assert len(rows)+1 == len([f for f in E.rglob('*') if f.is_file()])
git('diff','--check')
assert git('status','--short','--untracked-files=all') == status
print(json.dumps({'helper_tests_passed':count,'manifest_mismatches':0,'original5scripts_unchanged':True,
    'source_files_preserved':209,'prior_public_files_preserved':190,'five_prefixes_preserved':True,
    'human_record_unchanged':True,'status_entries':len(status.splitlines()),'new_files':len(created),
    'generic_scan_units':len(scan),'other_addresses':0,'diff_check_exit':0,'live_or_private_work':False}))

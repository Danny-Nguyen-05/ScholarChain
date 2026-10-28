"""Reconcile this repair's frozen full gate; never run a build or change source."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]


def read(name):
    return json.loads((OUT / name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x') as f:
        f.write(json.dumps(value, indent=2) + '\n')


start = read('full-check-start.json')
result = read('full-check-result.json')
assert result['exit_code'] == 0 and not result['rewritten_sources']
assert result['start_record_unchanged']
assert digest(Path(result['raw_log'])) == result['raw_sha256']
assert digest(OUT / 'full-check-start.json') == result['start_record_sha256']
assert (OUT / 'full-check-start.json').stat().st_mtime_ns == result['start_record_mtime_ns']
assert start['writing_barrier']['stopped_writing']
assert start['writing_barrier']['recorded_epoch'] < start['start_epoch']
for p, expected in start['source_files'].items():
    assert digest(ROOT / p) == expected == result['source_files_after'][p], p

rows, stale, cases = [], [], set()
for module in ['modules/core', 'modules/hadoop', 'modules/entity-resolution', 'modules/spark',
               'modules/storage', 'modules/rag', 'modules/services', 'tests', 'build-verification']:
    counts = dict(reports=0, tests=0, failures=0, errors=0, skipped=0)
    for path in sorted((ROOT / module / 'target/test-reports').glob('*.xml')):
        if path.stat().st_mtime < start['start_epoch']:
            stale.append(str(path.relative_to(ROOT)))
            continue
        counts['reports'] += 1
        suite = ET.parse(path).getroot()
        for key in ['tests', 'failures', 'errors', 'skipped']:
            counts[key] += int(suite.get(key, 0))
        cases |= {(suite.get('name').split('.')[-1], c.get('name')) for c in suite.findall('testcase')}
    assert counts['reports'] > 0, module
    rows.append(dict(module=module, **counts))
totals = {k: sum(r[k] for r in rows) for k in ['reports', 'tests', 'failures', 'errors', 'skipped']}
assert totals['failures'] == totals['errors'] == totals['skipped'] == 0, totals
raw = Path(result['raw_log']).read_text(errors='replace')
log_counts = [int(n) for n in re.findall(r'Total number of tests run: (\d+)', raw)]
assert len(log_counts) == len(rows) and sum(log_counts) == totals['tests'], log_counts
assert '[success]' in raw and 'TestRunMarker' in raw

preflight = read('preflight.json')
protected = hashlib.sha256()
tracked = subprocess.check_output(['git', 'ls-files', 'modules', 'tests', 'project', 'build.sbt', 'prompts'], cwd=ROOT, text=True).splitlines()
protected_paths = [p for p in tracked if not p.startswith('modules/services/')
                   and p != 'tests/src/test/scala/edu/uic/cs441/scholarchain/independent/AdversarialRuntimeHttpSpec.scala']
assert len(protected_paths) == preflight['protected_file_count']
for p in protected_paths:
    protected.update(p.encode() + b'\0' + hashlib.sha256((ROOT / p).read_bytes()).digest())
assert protected.hexdigest() == preflight['protected_aggregate_sha256']
historical_changed_reports = {f'docs/agent-runs/phase-11/{n}.md' for n in
                              ['owner-report', 'test-report', 'prompt', 'review', 'repairs']}
for p, expected in preflight['prior_evidence_hashes'].items():
    if p in historical_changed_reports:
        assert hashlib.sha256((ROOT / p).read_bytes()[:preflight['prior_report_prefix_bytes'][p]]).hexdigest() == expected, p
    else:
        assert digest(ROOT / p) == expected, 'Historical evidence changed: ' + p

module_cases = sorted([list(c) for c in cases if c[0] == 'SessionBindingRecoverySpec'])
http_cases = sorted([list(c) for c in cases if c[0] == 'AdversarialRuntimeHttpSpec'])
assert module_cases and len(http_cases) >= 7
coverage = read('coverage.json')
mapped = {tuple(t) for c in coverage['categories'].values() for kind in ['existing', 'new'] for t in c[kind]}
assert len(mapped) == 84 and mapped <= cases, mapped - cases
baseline = read('baseline-test-counts.json')['totals']
assert totals['tests'] == baseline['tests'] + len(module_cases) + len(http_cases) - 6
assert totals['reports'] == baseline['reports'] + 1
save('full-check-summary.json', dict(totals=totals, rows=rows, log_group_counts=log_counts,
    excluded_stale_report_paths=stale, module_regression_cases=module_cases,
    mapped_distinct=len(mapped), mapped_missing_from_fresh_reports=[],
    final_independent_http_cases=http_cases, baseline=baseline,
    raw_log=result['raw_log'], raw_bytes=result['raw_bytes'], raw_sha256=result['raw_sha256'],
    exit_code=result['exit_code'], sources_frozen=len(start['source_files']),
    protected_files_unchanged=len(protected_paths),
    historical_evidence_unchanged_except_append_reports=True,
    start_record_sha256=result['start_record_sha256'], start_record_mtime_ns=result['start_record_mtime_ns'],
    collected_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
save('defects.json', dict(exposed_defect_count=0, tagged_tests=[],
    repaired_pending_independent_recheck=['R11C-1', 'R11C-2', 'R11C-5'],
    unmodified_nonblocking=['R11C-3', 'R11C-4', 'R11C-6', 'F11B-3', 'F11B-4', '11A N3',
                          'Phase9 NB1–NB10', 'Phase10 F7/F8/F10–F17'],
    note='Red regression failures remain in the red-run evidence. All final cases pass, no tag or exclusion wiring needed. Passing repair tests are not independent approval or closure of carried findings.'))
print(json.dumps(dict(totals=totals, module_regression_tests=len(module_cases),
    independent_http_tests=len(http_cases), protected_files=len(protected_paths),
    stale_reports_excluded=len(stale))))

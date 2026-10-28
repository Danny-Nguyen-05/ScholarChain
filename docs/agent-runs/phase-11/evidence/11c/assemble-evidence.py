"""Coordinator-only Phase 11C assembly; no builds, tests, or production writes.

Run once from the repository root. Historical evidence is read, never regenerated.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shlex
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PHASE = OUT.parent.parent
BASE = '2b0aee044f243f01bbb603170d09f5c507df8bb7'
REVIEW_BASE = '03493882399e9020e6892c9f97e0ec8919365215'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
COMMANDS = []


def run(args, env=None, expected=0):
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True)
    COMMANDS.append(dict(argv=args, command=shlex.join(args), cwd=str(ROOT),
                         exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr))
    assert p.returncode == expected, (args, p.returncode, p.stderr)
    return p.stdout


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x') as f:
        f.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def write(path, content):
    with path.open('x') as f:
        f.write(content)


def append(name, content):
    with (PHASE / name).open('a') as f:
        f.write('\n\n## Subphase 11C\n\n' + content.rstrip() + '\n')


status = run(['git', 'status', '--short'])
assert status.splitlines() == ['?? docs/agent-runs/phase-11/evidence/11c/'], status
# The only preflight write is this assembly script; the user confirmed scope first.
branch = run(['git', 'branch', '--show-current']).strip()
head = run(['git', 'rev-parse', 'HEAD']).strip()
assert branch == 'phase-11' and head == BASE
last = run(['git', 'log', '-1', '--format=%H%n%s'])
run(['git', 'merge-base', '--is-ancestor', REVIEW_BASE, 'HEAD'])
run(['git', 'merge-base', '--is-ancestor', '0c5ee89994b5b738a3490ef5e8f032fdc67327b2', 'HEAD'])
scope_stat = run(['git', 'diff', '--shortstat', REVIEW_BASE, 'HEAD']).strip()
scope_paths = run(['git', 'diff', '--name-only', REVIEW_BASE, 'HEAD']).splitlines()
# Avoid retaining a large repository inventory in commands.json.
COMMANDS[-1]['stdout'] = f'{len(scope_paths)} paths; full list reproducible with recorded command\n'
env = os.environ.copy()
env['JAVA_HOME'] = '/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'
env['PATH'] = env['JAVA_HOME'] + '/bin:' + env['PATH']
env['SBT_OPTS'] = '-Dlogback.configurationFile=' + str(ROOT / 'docs/agent-runs/phase-04/xml-repair-logback.xml')
java_out = run(['java', '-version'], env=env)
java = COMMANDS[-1]['stderr'] + java_out
assert '17.0.20.1' in java
write(OUT / 'java-version.txt', java)
save('preflight.json', dict(recorded_utc=NOW, branch=branch, base_sha=head, head=head,
    clean_before_first_edit=True, original_read_only_status='',
    status_after_assembly_script_creation=status, last_commit=last,
    review_baseline=REVIEW_BASE, review_scope='Complete repository at HEAD plus baseline-to-HEAD diff and current working diff/untracked files',
    review_diff_stat=scope_stat, review_diff_files=len(scope_paths),
    environment={k: env[k] for k in ('JAVA_HOME', 'SBT_OPTS')}, path_prefix=env['JAVA_HOME']+'/bin',
    step_0=dict(question='Confirm complete repository at HEAD 2b0aee0 plus diff from baseline 0349388',
                answer='Confirm recorded scope (Recommended)', other_questions='None',
                inherited=['ExposedDefect tags and explicit defect runs if needed', 'Requirement-to-test table and exact counts; no coverage tool']),
    stop_point='11C tasks 1–2 only; no reviewer, repairs, delegation or builds'))

coverage = {}
per_plane = {}
all_old, all_new = set(), set()
for plane in ('11a', '11b'):
    source = read(OUT.parent / plane / 'coverage.json')
    old = {tuple(t) for c in source.values() for t in c['existing']}
    new = {tuple(t) for c in source.values() for t in c['new']}
    per_plane[plane] = dict(existing_distinct=len(old), new_distinct=len(new), total_distinct=len(old | new))
    all_old |= old
    all_new |= new
    for key, value in source.items():
        coverage[key] = dict(plane=plane, existing=value['existing'], new=value['new'],
                             existing_count=len(value['existing']), new_count=len(value['new']),
                             total=len(value['existing'])+len(value['new']),
                             source=f'docs/agent-runs/phase-11/evidence/{plane}/coverage.json',
                             scope_note=value.get('gap', 'See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.'))
assert set(coverage) == {str(i) for i in range(1, 21)}
assert len(all_new) == 32 and not all_new & all_old
save('coverage.json', dict(categories=coverage, planes=per_plane,
    existing_distinct=len(all_old), new_distinct=len(all_new), combined_distinct=len(all_old | all_new),
    note='Selected named requirements coverage, not a line/branch coverage percentage. Category counts overlap.'))
md = '# Phase 11 categories 1–20\n\nSources are the committed 11A/11B maps; names are preserved exactly. Counts overlap across categories.\n\n| Category | Plane | Existing | New | Total |\n| --- | --- | ---: | ---: | ---: |\n'
for k, c in sorted(coverage.items(), key=lambda t: int(t[0])):
    md += f'| {k} | {c["plane"]} | {c["existing_count"]} | {c["new_count"]} | {c["total"]} |\n'
md += f'\nDistinct selected tests: {len(all_old)} existing + {len(all_new)} new = {len(all_old | all_new)}. '
md += 'This is a selected requirement map, not an exhaustive test census or a guarantee of full category depth. Category 20 covers configuration parsing, not startup composition (F11B-3). Category 16 has all three named faults plus extra audit-failure coverage (F11B-4).\n'
for k, c in sorted(coverage.items(), key=lambda t: int(t[0])):
    md += f'\n## Category {k}\n\n'
    for kind in ('existing', 'new'):
        for suite, name in c[kind]:
            md += f'- {kind}: `{suite}` — {name}\n'
    md += '\nScope: ' + c['scope_note'] + '\n'
write(OUT / 'coverage.md', md)

defect_sources = {p: read(OUT.parent / p / 'defects.json') for p in ('11a', '11b')}
assert all(d['exposed_defect_count'] == 0 for d in defect_sources.values())
save('defects.json', dict(exposed_defect_count=0, tagged_tests=[], production_defects_exposed_by_completed_runs=[],
    sources=[f'docs/agent-runs/phase-11/evidence/{p}/defects.json' for p in defect_sources],
    distinction='F11B-1 and 11A N4 are unconfirmed code-reading leads, not executed failing tests. Zero exposed tests does not close any registered finding.',
    repairs=[], routing_started=False, build_exclusion_required=False))

# Verify current source bytes and retained raw logs without executing tests.
source_checks = []
raw_checks = []
summaries = {}
for plane in ('11a', '11b'):
    s = read(OUT.parent / plane / 'full-check-summary.json')
    summaries[plane] = dict(path=f'docs/agent-runs/phase-11/evidence/{plane}/full-check-summary.json',
        totals=s['totals'], exit_code=s['exit_code'], raw_log=s['raw_log'], raw_sha256=s['raw_sha256'])
    for path, expected in s.get('final_new_source_hashes', s.get('source_files', {})).items():
        actual = digest(ROOT / path)
        assert actual == expected, path
        source_checks.append(dict(path=path, sha256=actual, matches_historical_gate=True))
    raw = Path(s['raw_log'])
    exists = raw.is_file()
    actual = digest(raw) if exists else None
    if exists:
        assert actual == s['raw_sha256'] and raw.stat().st_size == s['raw_bytes']
    raw_checks.append(dict(path=str(raw), exists=exists, bytes=raw.stat().st_size if exists else None,
                           sha256=actual, matches=actual == s['raw_sha256']))

modules = ['modules/core', 'modules/hadoop', 'modules/entity-resolution', 'modules/spark',
           'modules/storage', 'modules/rag', 'modules/services', 'tests', 'build-verification']
cases = set()
totals = dict(reports=0, tests=0, failures=0, errors=0, skipped=0)
for module in modules:
    for path in (ROOT / module / 'target/test-reports').glob('*.xml'):
        suite = ET.parse(path).getroot()
        totals['reports'] += 1
        for key in ('tests', 'failures', 'errors', 'skipped'):
            totals[key] += int(suite.get(key, 0))
        cases |= {(suite.get('name').split('.')[-1], c.get('name')) for c in suite.findall('testcase')}
assert totals == summaries['11b']['totals'], totals
assert all_old | all_new <= cases, (all_old | all_new) - cases

# Phase 11A/11B commits contain only new tests and phase evidence.
phase_changes = run(['git', 'diff', '--name-status', '0c5ee89994b5b738a3490ef5e8f032fdc67327b2', 'HEAD'])
for line in phase_changes.splitlines():
    state, path = line.split('\t', 1)
    assert (state == 'A' and path.startswith('tests/')) or path.startswith('docs/agent-runs/phase-11/'), line

indexed = []
for n in range(1, 11):
    for name in ('owner-report.md', 'test-report.md', 'review.md', 'repairs.md'):
        path = ROOT / f'docs/agent-runs/phase-{n:02d}' / name
        if path.is_file():
            indexed.append(dict(path=str(path.relative_to(ROOT)), sha256=digest(path),
                scope='Prior active-disposition scans carried from 11A/11B; indexed now, not a fresh line-by-line review.'))
for path in sorted((ROOT / 'modules').glob('*/README.md')):
    indexed.append(dict(path=str(path.relative_to(ROOT)), sha256=digest(path), scope='Heading/limit scan; full review belongs to independent reviewer.'))
save('test-evidence.json', dict(historical_summaries=summaries, current_source_hash_checks=source_checks,
    current_raw_full_log_checks=raw_checks, current_retained_junit_counts=totals,
    all_mapped_names_present_in_current_retained_junit=True, mapped_distinct=len(all_old | all_new),
    tests_executed_in_11c=0, source_change_in_11c=False,
    earlier_reports_and_module_readmes=indexed,
    test_reports='docs/agent-runs/phase-11/test-report.md sections Subphase 11A and Subphase 11B (append-only; original content remains)',
    mutation_checks=dict(data_plane=8, runtime_plane=9, execution='Reasoning only; no production mutations'),
    course=dict(url='https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md',
        accessed_utc=NOW, scope='Primary course Phase 11, required test inventory, evaluation deductions retrieved with web open/find; no full page copy retained.'),
    limitations=['No new test execution or independent review in 11C assembly',
        'Historical evidence remains historical; no earlier inventory is rewritten after commit',
        'Raw logs exist only in /tmp and may disappear; availability/hash observed now',
        'Synthetic offline fixtures; live AWS/provider/EMR/scale/cost not established',
        'Exact inherited model revision unavailable; no constitutional/instructor ratification inferred']))

# Preserve the exact current Phase 11 nonblocking table as context, not a repair order.
register = (PHASE / 'repairs.md').read_text()
phase11_context = register[register.index('### Subphase 11B external review'):]
phase9 = (ROOT / 'docs/agent-runs/phase-09/review.md').read_text()
nb = phase9[phase9.index('#: NB1\n'):phase9.index('Unverified future gates (not 9C defects):')]
phase10 = (ROOT / 'docs/agent-runs/phase-10/repairs.md').read_text()
f10 = phase10[phase10.index('### Carried inputs for Phase 11 or later'):]
carried = '''# Carried context for the independent 11C reviewer

This index preserves original owners and dispositions. It does not confirm, close, reprioritize or authorize repair of a finding. Verify each lead against current files and later dispositions. Do not treat historical OPEN/pending checkpoints as final when a later review supersedes them.

## Phase 11A

- N1/N2: formatting and start-record precision lessons applied in 11B; the historical records remain unchanged. Verify the 11B disclosure/barriers rather than retroactively rewriting 11A.
- N3 (Low, test-engineer): AdversarialDataPlaneSpec.scala:114–116 uses work-key-implied disjointness and does not compare orders downstream; AdversarialBlockingReplaySpec.scala:156–161 includes redundant hash equality and an always-true assertion; the old “independent SHA256” wording overstates independence. Optional strengthening, unmodified.
- N4 (Info, unconfirmed lead; hadoop-engineer if confirmed, test-engineer for assertion update): TextNorm.scala:9–14 and HadoopPrepSpec.scala:59 preserve title markup; DerivedRecords.scala:342–345 uses that normalized title in title-year blocks while ER normalization strips markup (ER README:341–342). Check a same-title/same-year cross-source pair with and without inline markup for a missed candidate. No reproduction or repair has run.
- N5: historical scan-level reading, unknown model revision, temporary raw logs, synthetic fixtures and earlier limits retained. See review.md for the verbatim external review.

## Phase 11B external review input (verbatim existing routing-context section)

'''+phase11_context+'''

## Phase 9C NB1–NB10 (verbatim review extract)

Source: docs/agent-runs/phase-09/review.md. Earlier 9A/9B observations and repairs remain in that phase's review.md and repairs.md; this extract does not replace those registers.

'''+nb+'''
## Phase 10 final carried register (verbatim extract)

Source: docs/agent-runs/phase-10/repairs.md. F1–F6/F9 and O1/O2 closures remain governed by the external reviews; do not reopen or close them without current evidence.

'''+f10+'''

## Earlier registers and disclosed limits

- Phase 4: prefix replay may have large-corpus I/O cost; use phase-04 module/report evidence.
- Phase 5: matching/scaling/IO and identity-evaluation limits remain in phase-05/{review,repairs,owner-report,test-report}.md. Labels are not blind calibrated truth: eight uncertain labels and 22 externally assisted cases without retained external evidence. Do not infer population accuracy or recall.
- Phase 6: phase-06/{review,repairs,owner-report,test-report}.md covers LPA nonconvergence, approximate P90/partition dependence, bounded buffering, metadata reuse and runtime/Scala alignment. EMR execution is deferred to Phase 15. Historical yearless-edge/consumer gates must be checked against later Phase 7 dispositions. No new closure inferred.
- Phase 7: phase-07/{review,repairs,owner-report,test-report}.md governs N4/N5/N7/N9–N16 and 7C-L1/L2/L3; N6 was externally closed. 7C-M1 has an offline repair and final local validation; use the later review/disposition evidence to establish closure, not its older OPEN row. Actual live cleanup, SDK/IAM compatibility and cost remain unverified (Phase 14C). Do not execute cleanup.
- Phase 8: phase-08/{review,repairs,owner-report,test-report}.md governs N2–N8/R2–R3/N10–N19 and accepted closures B1/N9/F1/N1/R1. Live rendering/model/vector/retrieval cost remains Phase 14C scope; authored smoke commands are not executed evidence.
- Phase 9: all earlier N/O/R observations remain governed by phase-09/repairs.md and subsequent review.md dispositions, in addition to NB1–NB10 above.
- Codex/Cursor-led orchestration remains a disclosed deviation from the course Claude workflow; required .claude artifacts are not native Codex enforcement. No instructor acceptance or human constitutional ratification is inferred from file existence.

Full prior-report paths and hashes are indexed in test-evidence.json. The inherited reading scope is active-disposition scanning, not a fresh line-by-line independent review. Current whole-repository review remains unrun. Phase 12+ infrastructure, Phase 14 live gates, Phase 15 bounded EMR/deployment and the user's final human gate are future scope; do not turn future live evidence into an offline success claim.
'''
write(OUT / 'carried-findings.md', carried)

append('prompt.md', '''Exact current user instruction: “now start phase 11c.”

Continuation: the user-supplied 11B APPROVE/NEXT PROMPT permits only 11C tasks 1–2: assemble both test reports, combined defect list, categories 1–20, earlier registers and F11B-1..F11B-4; produce one whole-repository read-only reviewer prompt in the 12-point order; do not launch a reviewer, route repairs, edit production/build/tests, run cloud/provider calls or create human-owned records. The prior verdict and F11B findings were already appended and committed in 2b0aee0; do not duplicate or rewrite them.

Step 0 asked together: “11C Step 0: Confirm the recorded review scope: the complete repository at HEAD 2b0aee0 plus the diff from baseline 0349388. I have no other questions for this subphase.” User answer: “Confirm recorded scope (Recommended)”. No other questions for this subphase. Earlier ExposedDefect/table decisions persist.

Stop at the first 11C review handoff. No independent whole-repository verdict or completed Phase 11 is claimed.''')
append('review.md', '''No 11C reviewer has been launched or selected. The coordinator assembled the first-stop-point packet only. The user-supplied 11A/11B APPROVE records above remain unchanged; 11B is committed as 2b0aee044f243f01bbb603170d09f5c507df8bb7. This is a pending-review checkpoint, not an approval or human gate. No independent 11C verdict has been received.''')
append('repairs.md', '''First stop point: assembly only. No finding has been routed for implementation and no repair has run. The combined ExposedDefect inventory remains zero; F11B-1 and 11A N4 remain unconfirmed review leads. F11B-1..F11B-4 and earlier findings retain their original owners, severity and dispositions. See evidence/11c/carried-findings.md for review context. Await the user-launched whole-repository verdict before grouping/routing any blocking findings; each authorized owner batch is a separate repair stop point.''')

NEW_NAMES = ['assemble-evidence.py', 'preflight.json', 'java-version.txt', 'commands.json',
    'coverage.json', 'coverage.md', 'defects.json', 'test-evidence.json', 'carried-findings.md',
    'README.md', 'handoff-files.json', 'final-validation.json']
modified = [str((PHASE / name).relative_to(ROOT)) for name in
            ('prompt.md', 'owner-report.md', 'test-report.md', 'review.md', 'repairs.md')]
created = [str((OUT / name).relative_to(ROOT)) for name in NEW_NAMES] + ['docs/agent-runs/phase-11/reviewer-prompt-11c.md']
save('handoff-files.json', dict(modified=sorted(modified), untracked=sorted(created),
    modified_count=len(modified), untracked_count=len(created),
    scope='Only coordinator phase evidence; no production/build/test changes'))

report = f'''STATUS: COMPLETE (11C tasks 1–2 assembly only; whole-repository review pending)

OWNER: Coordinator `/root`; no delegated writer or reviewer invoked in 11C.

WORK ORDER: phase11.md §§3–7, §8 11C tasks 1–2, §9–§11; user's “now start phase 11c.” and supplied 11B NEXT PROMPT. Branch phase-11; base/current HEAD {BASE}; confirmed review baseline {REVIEW_BASE}, plus all repository files at HEAD and current diff/untracked evidence. 11A/11B commits and Phase 10 ancestry are present. Step 0: user confirmed recorded scope; no other questions.

FILES CREATED: 12 files under evidence/11c/ and reviewer-prompt-11c.md; exact paths in evidence/11c/handoff-files.json.

FILES MODIFIED: Append-only prompt.md, owner-report.md, test-report.md, review.md, repairs.md under this phase. No production/build/test/prompt asset or human-decision record changed.

COMMANDS RUN: `python3 docs/agent-runs/phase-11/evidence/11c/assemble-evidence.py` performs coordinator assembly and read-only assertions. Exact child argv, exits and observed output: evidence/11c/commands.json. Includes git status/branch/HEAD/log, ancestor checks for 0349388 and 0c5ee89, baseline shortstat/name list, JDK 17 `java -version`, Phase 11 path audit, current diff/whitespace/process checks. All recorded required-success subprocesses exit 0. Java reports OpenJDK 17.0.20.1 under plan §2 environment. No sbt, formatter, test, AWS or provider invocation in 11C. See final-validation.json for assembly assertions; command success means evidence assembly, not independent approval.

TEST RESULTS: Zero tests executed in 11C. Retained 11A full gate: 1,231/152 reports; 11B: 1,248/155 reports; both exit 0 and zero failures/errors/skips. New tests: 15 + 17 = 32 in 6 suites, plus one shared fixture source. Independent module final: 664 tests/89 reports. Current retained XML reconciles to 1,248/155, and all {len(all_old | all_new)} distinct mapped cases appear. Combined selected map: {len(all_old)} existing + 32 new = {len(all_old | all_new)} across all 20 categories; categories overlap. ExposedDefect count 0. Mutation thought checks: 8 data-plane, 9 runtime; no production mutations. Prior failed development/compile gates remain recorded in evidence/11a and evidence/11b, not erased.

VALIDATION RESULTS: Seven current new-source hashes match the passing historical gates; both historical full raw-log hashes/byte counts rechecked when available (test-evidence.json). Phase 11 base-to-HEAD path audit has no production/build/existing-test delta. Current 11C delta is restricted to coordinator evidence, prior report content is preserved as a prefix, coverage names/counts and retained XML agree, and git diff --check passes. Review baseline-to-HEAD diff: {scope_stat}. Full repository scope includes unchanged and pre-baseline files, not just those {len(scope_paths)} changed paths. Current file list/validation are in evidence/11c/handoff-files.json and final-validation.json.

ASSUMPTIONS: Historical passing gates apply to their frozen source hashes; no fresh execution or general correctness claim is made. The user launches a separate independent read-only reviewer. No finding is closed by passing tests or by this assembly.

RISKS: F11B-1 lost-reply/body-bind QUEUED lead and 11A N4 markup-sensitive blocking lead are unconfirmed; F11B-2/F11B-3 test-contract limits and F11B-4 context remain logged. Earlier registers remain under original owners/dispositions. Synthetic local fixtures do not establish live AWS/provider, scale, model quality, IAM, cleanup, EMR or cost. Raw logs only in /tmp; model revision unavailable; inherited report reading is scan-level. Codex/course-workflow deviation persists. No optional OpenSearch/index/service/CI/coverage-tool work added. Whole-repository verdict and human phase gate remain unverified.

MANUAL ACTION REQUIRED: User launches the read-only reviewer using reviewer-prompt-11c.md and returns its verdict/NEXT PROMPT. No commit/push requested or performed in this stop point. Human gate and acceptance remain user-owned; Phase 12 does not start automatically.

BLOCKED-ON OWNER: None for assembly; reviewer/user own the next gate.

BLOCKED-ON EVIDENCE: Independent whole-repository verdict remains pending; live gates are deferred, not passed.

NEXT GATE: User-launched whole-repository review. On a returned REQUEST_CHANGES, only the authorized owner batch may run, followed by affected/full JDK 17 gates and another handoff. No repairs or routing now. No active subagents/builds/jobs started by this assembly.
'''
append('owner-report.md', report)
append('test-report.md', report + '\nCoverage tables and exact suite/name mappings are assembled in evidence/11c/coverage.md and coverage.json, preserving the original 11A/11B report sections above.\n')

write(OUT / 'README.md', '''# Phase 11C first review stop point

Status: assembly COMPLETE; independent whole-repository review PENDING. No repairs, tests, cloud/provider calls, delegated work or human decision records.

- preflight.json: branch, base/HEAD, confirmed Step 0, review baseline, environment and initial status.
- commands.json / java-version.txt: exact child commands, exits/output and JDK 17 observation. The assembly script is the reproducible coordinator procedure; it uses exclusive creation and must not be rerun over existing records.
- coverage.json / coverage.md: combined categories 1–20 with original suite/name pairs and exact overlapping counts.
- defects.json: zero executed ExposedDefect tests, kept distinct from unconfirmed code-reading leads.
- test-evidence.json: original report paths, gate summaries, 7 source hashes, current retained XML reconciliation, raw full-log hashes and reading limitations. Main test-report.md retains both original test reports unchanged before its appended 11C section.
- carried-findings.md: Phase 11A/11B review inputs and earlier registers; context only, no repair routing or closure.
- handoff-files.json / final-validation.json: exact changed/new files, append-only/scope/whitespace checks and process observation.
- ../../reviewer-prompt-11c.md: the single user-run whole-repository prompt; no reviewer invoked here.

Historical failure details, formatter rewrite disclosures, gate barriers and hashes remain under ../11a/ and ../11b/. Do not rerun their collectors after commit. Read their original records as historical snapshots, not current status.

The current assembly can validate retained evidence but cannot approve itself. Phase 11 closes only after an independent whole-repository verdict, any owner repairs and rerun evidence, and the user's human gate. Do not launch Phase 12 from this packet.
''')

prompt = f'''You are the independent, read-only code reviewer for ScholarChain Phase 11,
Subphase 11C, initial whole-repository review (no repair round), in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md. No human ratification is inferred from file existence.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase11.md
   §§1–7, §8 Subphase 11C, §§9–11. This is the first 11C stop point:
   coordinator tasks 1–2 only, before any review-driven repair batch.
3. The primary course specification, including Phase 11, Required test inventory,
   and Evaluation deductions and failure conditions:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-11-adversarial-testing-and-full-repository-review
4. docs/agent-runs/phase-11/prompt.md, owner-report.md, test-report.md,
   review.md and repairs.md (11A, 11B and appended 11C sections), plus
   docs/agent-runs/phase-11/evidence/11c/README.md, preflight.json,
   commands.json, coverage.md, coverage.json, defects.json, test-evidence.json,
   carried-findings.md, handoff-files.json and final-validation.json.
5. All seven module READMEs and relevant earlier phase owner/test/review/repair
   reports. The prior-report index in test-evidence.json is a reading aid, not
   proof that the coordinator performed the independent review.

Checkpoint facts:
- Branch: phase-11. Subphase base SHA and current HEAD:
  {BASE} (approved 11B commit).
  Approved 11A commit: d80afb755c649ecc5cda60525a1a0201aceb4c03.
- User-confirmed whole-repository diff baseline:
  {REVIEW_BASE} (0349388).
  Review the COMPLETE repository at HEAD, including unchanged/pre-baseline files,
  plus `git diff {REVIEW_BASE} HEAD`,
  `git diff {BASE}` and every current untracked file.
  Baseline-to-HEAD shortstat: {scope_stat}.
- Changed tracked files (all appended under docs/agent-runs/phase-11/):
  prompt.md, owner-report.md, test-report.md, review.md, repairs.md.
- Untracked: docs/agent-runs/phase-11/reviewer-prompt-11c.md and these 12
  files under docs/agent-runs/phase-11/evidence/11c/:
  assemble-evidence.py, preflight.json, java-version.txt, commands.json,
  coverage.json, coverage.md, defects.json, test-evidence.json,
  carried-findings.md, README.md, handoff-files.json, final-validation.json.
  Verify the live status against handoff-files.json; do not rely only on this list.
- Step 0: user answered “Confirm recorded scope (Recommended)” for whole HEAD
  plus 0349388 diff. No other questions. Earlier decisions: ExposedDefect tags
  and explicit defect runs if needed; exact requirement tables, no coverage tool.
- 11C command: `python3 docs/agent-runs/phase-11/evidence/11c/assemble-evidence.py`;
  assembly/assertions exit 0. Child argv/exits/output in commands.json.
  Read-only Git preflight/ancestry/path checks and `java -version` exit 0;
  OpenJDK 17.0.20.1 under the plan §2 JAVA_HOME/PATH/SBT_OPTS environment.
  `git diff --check` exit 0; 5 existing docs append-only, 13 new evidence/prompt
  files, no production/build/test/prompt-asset changes in this stop point.
- ZERO builds/tests run in 11C. Retained 11A full `/usr/bin/time -p sbt -batch check`:
  exit 0, 1,231 tests/152 reports; 11B same full command: exit 0,
  1,248 tests/155 reports, 0 failures/errors/skips, sbt 720 s.
  11B final targeted `sbt -batch 'independentTests / Test / scalafmtCheck'
  'independentTests / Test / testOnly *AdversarialRuntime*'`: exit 0, 17/17,
  3 suites. Earlier 11B targeted-1 exit 1 was 2 Logback compile errors, 0 tests;
  formatter-1 rewrote 4 new files, formatter-2 rewrote 1 HTTP file, disclosed.
  Historical exact argv/exits and all development failures remain in
  evidence/11a/commands.json and evidence/11b/commands.json; do not rerun collectors.
- Combined coverage: 20 categories, {len(all_old)} existing + 32 new = {len(all_old | all_new)} distinct
  mapped cases; category counts overlap. 15 new data-plane + 17 runtime cases,
  6 suites and one shared runtime fixture. Mutation checks: 8 data-plane and
  9 runtime, reasoning only. ExposedDefect inventory: 0; no exclusion or
  explicit defect runs required for an empty list. This does not mean no defects.
- Historical full logs (hash rechecked during assembly if available):
  /tmp/phase11a-final-check.log: 1,717,764 bytes,
  SHA256 07f515f3f51427dac4a730bf2ab0af39c3c7d005111b335b7c6c6a78fff32758;
  /tmp/phase11b-full-check.log: 1,721,327 bytes,
  SHA256 142d10e1518e579d76a45f6a4c2db93771d496105f777a8f301ebf03559cfb31.
  Both only in /tmp: verify availability and hashes; absence is a disclosed
  durability limitation. Current retained XML and 7 source hashes reconcile in
  test-evidence.json; these are read-only checks, not fresh test execution.

Ownership map (docs/agents.md controls exact precedence):
- factory-engineer: AGENTS.md, CLAUDE.md, docs/agents.md, .claude/** except
  generated .last-test-run, .mcp.json, docs/agent-runs/README.md.
- build-engineer: build.sbt, project/**, .scalafmt.conf, compose/packaging,
  .gitignore, generated marker. dependency-updater: approved ledger value tokens only.
- domain-engineer: modules/core/**. dataset-engineer: datasets/**.
- hadoop-engineer: modules/hadoop/**.
- entity-resolution-engineer: modules/entity-resolution/**.
- spark-engineer: modules/spark/**. storage-engineer: modules/storage/**.
- rag-engineer: modules/rag/**, prompts/runtime/**, prompts/schemas/**.
- service-engineer: modules/services/**.
- Each module owner owns its module-local tests; test-engineer owns tests/**
  independent/cross-module/adversarial cases and never production implementation.
- infra-engineer: infra/terraform/**, scripts/**, optional .github/workflows/**.
- deploy-engineer: approved execution/release evidence only.
- experiment-engineer: experiments/**, load-tests/**.
- documentation-engineer: README.md and docs/** except reserved subtrees.
- incident-responder: docs/incidents/**.
- Coordinator: assembles docs/agent-runs/** phase evidence from owner reports.
  Human owns gate/acceptance/ratification records; no agent rewrites them.
- code-reviewer: returned review text only; no edits, no self-approval.
  Unknown/overlapping ownership requires an explicit finding/decision.

Defect and carried context (verify against actual current files):
- Executed ExposedDefect list is EMPTY. No repaired finding or blanket closure
  is claimed by this packet; prior 11A/11B APPROVE verdicts are recorded externally.
- F11B-1 Medium, UNCONFIRMED code-reading lead, service-engineer; test-engineer
  for reproduction if confirmed: QueryService.scala:152–156,178–190,114 and
  DynamoStorage.scala:137. First body-binding CAS write applies, reply is lost,
  retry returns Retried(1, Rejected("conditional-conflict")); submit returns 503
  without scheduling. Same-key replay may see the bound QUEUED row and return
  202 indefinitely until TTL. Existing N04 injects only clean rejection.
  Check the apply-then-reject fake scenario against code; acceptance is exactly
  one workflow execution/reconciled scheduling, no stranded QUEUED or duplicate run.
  This may overlap Phase 10's deferred durable-dispatcher limit; assess impact
  and requirement, rather than assuming either a new blocker or a confirmed defect.
- F11B-2 Low, test-engineer: HTTP spec:138–140 pins replay-after-failed-bind
  503; assess requirement versus present behavior. F11B-3 Low, test-engineer/
  service-engineer: Boundary spec:77–98 tests config parsing, not startup
  composition; generic error clarity remains a decision, never expose values.
  F11B-4 Info: category-16 E11 extra coverage and weak summary.contains("3")
  backed by exact claims; no action previously required.
- 11A N3 weak/redundant assertions and N4 possible markup-sensitive title-year
  blocking miss remain uninvestigated. For N4 compare same title/year with and
  without inline markup in TextNorm/DerivedRecords/ER normalization; hadoop-engineer
  owns a confirmed pipeline repair, test-engineer any independent assertion change.
- Earlier registers and full original owners/acceptance checks:
  evidence/11c/carried-findings.md; phase-05 through phase-10 review.md/repairs.md.
  Preserve Phase 9 NB1–NB10 and Phase 10 F7/F8/F10–F17; do not silently close
  them. Check later dispositions when historical rows say OPEN/pending.
- Disclosed limits: synthetic local/scripted fixtures, scan-level historical
  reading, unknown exact model revision, temporary raw logs; Phase 5 label/
  calibration limits, Phase 6 convergence/approximation/runtime limits, Phase 7–8
  live/cleanup gates, prior runtime observations. Live AWS/provider gates are
  Phase 14, bounded EMR Phase 15, infrastructure Phase 12 onward. No optional
  OpenSearch/index/service/CI/coverage-tool work added. Codex workflow is not
  instructor-approved equivalence to Claude enforcement. Human Phase 11 gate unverified.

Perform the whole-repository review IN THIS EXACT 12-POINT ORDER:
1. Correctness and data loss.
2. Contract and schema drift.
3. Artifact ownership violations.
4. Security, secrets, IAM assumptions and injection risks.
5. Hadoop and Spark distribution mistakes.
6. Entity-resolution over-merging and unreported uncertainty.
7. Storage idempotency and provenance.
8. RAG grounding and unsupported claims.
9. API behavior and failure handling.
10. Tests that would pass even if the behavior were broken.
11. Documentation claims not supported by implementation.
12. Cost and cleanup risks.
Report your inspected scope/evidence in this order; disclose unread areas or
truncated source access. The known-findings list must not narrow the review.

Review rules:
- Strictly read-only: edit NOTHING, create no files, run no builds/tests,
  call no AWS or model provider, change no data, commit/push nothing, launch no
  subagents and read no secrets (.env, private keys, credentials or secret dirs).
  Safe read-only Git/file/hash/XML/JSON inspection is permitted.
- Verify EVERY candidate finding against actual current files before reporting.
  Report ALL confirmed findings in one pass. For each give severity, exact
  path:line, concrete failure input, expected versus actual code behavior,
  evidence, impact, owning agent, acceptance check and blocking yes/no.
  Mark code-derived/unexecuted findings explicitly; do not claim a reproduction.
- Check one-writer ownership, no production edits by the test-engineer, no
  hardcoded live resources/models/thresholds without configuration/rationale,
  no secret exposure, honest retained evidence, fault injection and hand-derived
  assertions, ExposedDefect accounting, coverage depth and exact named counts.
- Inspect unchanged sources as well as baseline/full current diff and untracked
  evidence. Phase 11 path audit is distinct from the large earlier production diff.
- Distinguish blockers, nonblocking observations, accepted limitations and future
  unverified gates. Do not demand live infrastructure/provider work assigned to
  later phases here. Passing synthetic tests do not establish general correctness.
- This is an initial whole-repository review, not approval of any 11C repair:
  no repairs/routing have occurred. Do not repair findings yourself.

Return:
1. VERDICT: APPROVE or REQUEST_CHANGES for Subphase 11C whole-repository review.
2. Findings with every required field above, grouped in the 12-point order.
3. All report fields from docs/agent-runs/README.md: STATUS, OWNER, WORK ORDER,
   FILES CREATED, FILES MODIFIED, COMMANDS RUN, TEST RESULTS, VALIDATION RESULTS,
   ASSUMPTIONS, RISKS, MANUAL ACTION REQUIRED, BLOCKED-ON OWNER,
   BLOCKED-ON EVIDENCE, NEXT GATE. State no builds/tests were run by reviewer.
4. ONE fenced NEXT PROMPT for the main coordinator:
   - Append your verdict VERBATIM under Subphase 11C in phase-11/review.md,
     marked user-supplied external review; append findings to repairs.md without
     rewriting earlier review/human records.
   - If REQUEST_CHANGES: group blocking findings by owner, honor Step 0 and
     authorize ONLY the first bounded owner batch (identify exact IDs/paths and
     owner). No nested delegation or reviewer launch. Owners write their own
     artifacts; test-engineer handles independent tests and affected reruns;
     build-engineer only build/tag exclusion changes if required. Use plan §2
     JDK 17 for affected tests and full sbt -batch check, with source freeze,
     honest formatter disclosure and once-written pre-launch records. Return a
     complete recheck prompt and STOP; no next batch/phase automatically.
   - If APPROVE: tell the coordinator to record the verdict, confirm the user's
     11C commit (ask/wait if uncommitted; no automatic commit/push), and tell the
     user Phase 11 is ready for their own human-gate/commit records. Phase 12 is
     next only after a separate explicit prompt; do not start or prepare it.
   - Never write human-gate.md, commit.txt or approval/ratification records;
     never launch/invoke/auto-select a reviewer. End the authorized stop point
     with its handoff and a complete copyable reviewer prompt where applicable.
'''
write(PHASE / 'reviewer-prompt-11c.md', prompt)

# Final assembly validation is read-only outside coordinator evidence.
run(['git', 'diff', '--check'])
changed = run(['git', 'diff', '--name-only']).splitlines()
untracked = run(['git', 'ls-files', '--others', '--exclude-standard']).splitlines()
# commands.json and final-validation.json are written last and are planned here.
assert sorted(changed) == sorted(modified), changed
pending = {str((OUT / n).relative_to(ROOT)) for n in ('commands.json', 'final-validation.json')}
assert set(untracked) | pending == set(created), set(untracked) ^ set(created)
prefix_checks = {}
for name in modified:
    original = run(['git', 'show', 'HEAD:' + name])
    COMMANDS[-1]['stdout'] = f'{len(original.encode())} bytes; content omitted, append-only check below\n'
    assert (ROOT / name).read_text().startswith(original), name
    prefix_checks[name] = True
processes = run(['ps', '-axo', 'pid=,comm='])
java_processes = [line.strip() for line in processes.splitlines()
                  if Path(line.strip().split(maxsplit=1)[-1]).name in ('java', 'sbt')]
COMMANDS[-1]['stdout'] = '\n'.join(java_processes) + ('\n' if java_processes else '')
assert not java_processes, java_processes
save('commands.json', dict(assembly_invocation='python3 docs/agent-runs/phase-11/evidence/11c/assemble-evidence.py',
    commands=COMMANDS, note='No sbt/build/test/provider command. Python assembly assertions and reads are visible in the retained script. Large read-only inventories and historical report bodies omitted from command output; paths/counts retained.'))
save('final-validation.json', dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    base_sha=BASE, head=head, branch=branch, modified_files=sorted(changed), untracked_files=sorted(created),
    modified_count=len(changed), untracked_count=len(created), prior_report_prefix_preserved=prefix_checks,
    paths_only_coordinator_evidence=True, git_diff_check_exit=0, current_retained_junit=totals,
    mapped_distinct=len(all_old | all_new), all_mapped_names_present=True, source_hashes_matched=7,
    raw_full_logs=raw_checks, tests_executed_in_11c=0, repairs=0, reviewer_invoked=False,
    new_delegation=False, prior_agent_status='Native list_agents observed test_engineer_11b completed; no active child agents',
    java_or_sbt_processes_observed=java_processes, human_records_written=False,
    note='Working status captured before the last two evidence files; their planned paths are included and externally verified after script exit. No independent verdict claimed.'))
print(json.dumps(dict(status='ASSEMBLY_COMPLETE_REVIEW_PENDING', categories=20,
    existing_distinct=len(all_old), new_tests=32, mapped_distinct=len(all_old | all_new),
    retained_tests=totals, modified=len(modified), new_files=len(created), tests_run=0)))

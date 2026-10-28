"""Assemble final reports only after the observed successful full repair gate."""
from pathlib import Path
import datetime
import hashlib
import json
import shlex
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
PHASE = OUT.parent.parent
BASE = '2b0aee044f243f01bbb603170d09f5c507df8bb7'
REVIEW_BASE = '03493882399e9020e6892c9f97e0ec8919365215'
GATES = ['red-format', 'red', 'red-format-2', 'red-2', 'final-format', 'format-check', 'targeted', 'full-check']


def read(name):
    return json.loads((OUT / name).read_text())


def save(name, value):
    with (OUT / name).open('x') as f:
        f.write(json.dumps(value, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


summary = read('full-check-summary.json')
totals = summary['totals']
assert totals == dict(reports=156, tests=1253, failures=0, errors=0, skipped=0), totals
assert git('rev-parse', 'HEAD').strip() == BASE and git('branch', '--show-current').strip() == 'phase-11'
gate_records = []
for gate in GATES:
    start, result = read(gate + '-start.json'), read(gate + '-result.json')
    assert result['start_record_unchanged']
    assert digest(OUT / (gate + '-start.json')) == result['start_record_sha256']
    assert (OUT / (gate + '-start.json')).stat().st_mtime_ns == result['start_record_mtime_ns']
    assert start['writing_barrier']['recorded_epoch'] < start['start_epoch']
    assert digest(Path(result['raw_log'])) == result['raw_sha256']
    gate_records.append(dict(gate=gate, **start, result=result))
for name in ['format-check', 'targeted', 'full-check']:
    result = read(name + '-result.json')
    assert result['exit_code'] == 0 and not result['rewritten_sources']
save('commands.json', dict(cwd=str(ROOT), gates=gate_records,
    coordinator_commands=[
        dict(command='java -version', exit_code=0, environment='plan §2 JDK 17; preflight.json and java-version.txt'),
        dict(command='python3 docs/agent-runs/phase-11/evidence/11c-r1/collect-evidence.py', exit_code=0,
             result=summary['totals']),
        dict(command='git diff --check', exit_code=0)],
    note='Exact argv/environment/exits retained for every gate. Red first attempt is compile-only, red-2 is four actual test failures. No cloud/provider call. Historical records are not rewritten.'))

head_diff = git('diff', '--numstat')
changed = sorted(git('diff', '--name-only').splitlines())
module_test = 'modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/SessionBindingRecoverySpec.scala'
allowed_changed = {f'docs/agent-runs/phase-11/{n}.md' for n in ['owner-report', 'test-report', 'prompt', 'review', 'repairs']} | {
    'modules/services/README.md',
    'modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala',
    'tests/src/test/scala/edu/uic/cs441/scholarchain/independent/AdversarialRuntimeHttpSpec.scala'}
assert set(changed) == allowed_changed, changed
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)

gate_table = '| Gate | Exact sbt arguments (all wrapped by /usr/bin/time -p sbt -batch) | Exit | Result |\n| --- | --- | ---: | --- |\n'
descriptions = {
    'red-format': 'Reformatted only new SessionBindingRecoverySpec',
    'red': 'Compile-only failure:4 ambiguous fixture references;0 tests',
    'red-format-2': 'Reformatted only corrected SessionBindingRecoverySpec',
    'red-2': '4 executed,0 passed,4 failed against unchanged production/README',
    'final-format': 'Reformatted QueryService.scala and HTTP spec only',
    'format-check': 'Both requested format checks passed; no rewrite',
    'targeted': 'Services40/7suites + Runtime18/3suites =58 passed,0 failed',
    'full-check': '1253 passed/156 fresh reports,0 failures/errors/skips; no rewrite',
}
for record in gate_records:
    gate_table += f'| {record["gate"]} | `{shlex.join(record["command"][4:])}` | {record["result"]["exit_code"]} | {descriptions[record["gate"]]} |\n'

report = f'''### Subphase 11C repair round 1 — batch 1 completion

STATUS: COMPLETE (authorized local repair/gates; external recheck pending)

OWNER: Coordinator /root assembles evidence. service-engineer /root/service_engineer_11c_r1 solely wrote modules/services/**; test-engineer /root/test_engineer_11c_r1 then solely wrote the independent HTTP spec. Inherited models, exact revisions unavailable. No nested delegation, reviewer or build-engineer invoked. Both specialists completed and stopped writing before final gates.

WORK ORDER: User-supplied initial 11C REQUEST_CHANGES and “Fix all blocking bugs for me.” Only batch 1 R11C-1/R11C-2 plus user-approved R11C-5 README. Branch phase-11, base/current HEAD {BASE}; earlier uncommitted 11C assembly preserved. Step 0 user answered “Yes, include R11C-5 (Recommended)”. Whole-repository baseline remains {REVIEW_BASE} plus all repository files at HEAD/current diff/untracked evidence.

FILES CREATED: New service-owned SessionBindingRecoverySpec.scala (4 cases), coordinator evidence/11c-r1/** and reviewer-prompt-11c-r1.md. Prior untracked evidence/11c/** and reviewer-prompt-11c.md remain untouched. Full changed/untracked inventory: evidence/11c-r1/handoff-files.json.

FILES MODIFIED: Service owner: QueryService.scala and modules/services/README.md. Test owner: tests/**/AdversarialRuntimeHttpSpec.scala only. Coordinator: append-only prompt.md, owner-report.md, test-report.md, review.md and repairs.md. No storage/core/Hadoop/Spark/RAG/build/infra/prompt-asset or human-owned decision changes. No commit/push.

COMMANDS RUN: All sbt commands used the exact plan §2 environment: JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; PATH prefixed with $JAVA_HOME/bin; SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml. Observed java -version: OpenJDK 17.0.20.1, sbt 1.10.7. Coordinator wrappers, argv/cwd/env/exits, start/result/excerpts and raw hashes are in evidence/11c-r1/commands.json. Exact invocations use `python3 docs/agent-runs/phase-11/evidence/11c-r1/run-gate.py <gate> <arguments>`; resolved sbt argv follow.

{gate_table}
Coordinator reconciliation: `python3 docs/agent-runs/phase-11/evidence/11c-r1/collect-evidence.py` exit0; `git diff --check` exit0. Each gate-start record was exclusively created immediately before launch, never rewritten; all eight final hashes/mtimes match. Explicit stopped-writing barriers precede every gate. Format rewrites were owner-authorized and are disclosed above. Final sources remained frozen through format-check/targeted/full-check.

TEST RESULTS: First red attempt compiled0 tests due to new fixture name ambiguity, corrected only by its service test owner. Actual red-2 executed4/failure4 before any production or README edit. Final targeted58/58,0 failed/canceled/ignored/pending (services40/7suites; runtime18/3suites). Full1253/156 fresh reports,0 failures/errors/skips: baseline1248 +4module +1net independent =1253. Services40, independent665; other module/build totals unchanged. Stale report exclusions are listed in full-check-summary.json. Full raw bytes {summary['raw_bytes']}; SHA256 {summary['raw_sha256']}; elapsed {read('full-check-result.json')['elapsed_seconds']:.2f}s. The expected nested checkProbeInjectFailure self-test is not an outer failure; outer success and TestRunMarker observed.

VALIDATION RESULTS: R11C-1 now reconciles an applied binding's ambiguous reply against the exact intended primary row, including revision/fingerprint/requestId/traceId and per-attempt UUID token. R11C-2 allows later replay to CAS-bind an unbound revision0 reservation. Only the winning binder schedules; losing binders replay or409, even when client IDs are identical. Module tests exercise direct/lost winner replies with two QueryService instances sharing a store. Independent HTTP tests assert actual workflow/model counts1, grounded literal verified count3, persisted SUCCEEDED/result, unchanged audit/stored replay and changed-body409. R11C-5 documents recovery and remaining process-death durability limits. Current requirement map:51 existing +33 new cross-module =84 selected tests over20categories, plus4 additional module regressions; category16=2existing/4new/6, category17=2/5/7. Counts overlap. Historical maps preserved, renamed test accounted for. ExposedDefect0; all final tests pass, no tag/exclusion/build-engineer needed. Protected423 tracked artifacts unchanged and prior evidence preserved except append-only reports; frozen {summary['sources_frozen']} owned/runtime files match final gate hashes. Mutation checks are reasoning only:6 service-owner +7 independent sensitivities in the owner handoffs; no production mutations.

ASSUMPTIONS: Storage primary reads/CAS honor their contracts. Binding token lives in opaque session JSON, not a shared schema; client IDs alone are not ownership proof. Store/LLM inputs are synthetic. Local verification is not independent acceptance.

RISKS: Persistent store outage and process death after successful binding still lack durable dispatcher recovery. No live DynamoDB/AWS/provider, scale, deployment or general model-quality guarantee. R11C-3 remains an unassigned orphan needing a future human owner decision; no deletion or ignore edit. R11C-4/R11C-6, F11B-3/F11B-4, 11A N3, Phase9 NB1–NB10, Phase10 F7/F8/F10–F17 and earlier limits remain untouched. Raw logs only in /tmp; model revision unavailable; earlier reviewer unread areas/scan-level reports and Codex/course deviation remain disclosed. Optional OpenSearch/index/service/CI/coverage tooling omitted.

MANUAL ACTION REQUIRED: User launches independent read-only repair recheck using reviewer-prompt-11c-r1.md and returns verdict/NEXT PROMPT. Do not commit until recheck. Human acceptance/gate and any orphan ownership decision remain user-owned. No further batch or Phase12 starts automatically.

BLOCKED-ON OWNER: None for this authorized local repair; independent reviewer/user own next gate.

BLOCKED-ON EVIDENCE: Independent recheck pending; future live/deployment gates remain unverified.

NEXT GATE: User-launched read-only 11C repair-round 1 recheck; stop after this handoff. No active child writers/builds/jobs remain at handoff.
'''
for name in ['owner-report.md', 'test-report.md']:
    with (PHASE / name).open('a') as f:
        f.write('\n\n' + report)
with (PHASE / 'repairs.md').open('a') as f:
    f.write('''

### Subphase 11C repair round 1 — local disposition, independent recheck pending

| ID | Owner | Local result | Independent disposition |
| --- | --- | --- | --- |
| R11C-1 | service-engineer; test-engineer HTTP case | Applied-then-retried-conflict primary reconciliation, one dispatcher, completion/stored replay/409; red reproduced then targeted/full pass | PENDING user-launched recheck |
| R11C-2 | service-engineer; test-engineer | Clean rejection followed by revision0 replay CAS recovery; two cross-instance concurrency variants and updated HTTP expectation pass | PENDING user-launched recheck |
| R11C-5 | service-engineer; user approved Step 0 inclusion | README accurately states binding recovery and remaining already-bound process-crash limits | PENDING user-launched recheck |
| R11C-3 | ORPHAN; human assigns writer | UNTOUCHED, no ownership inferred, no deletion/ignore edit | Nonblocking, future human decision |
| R11C-4/R11C-6 and carried findings | Original owners | UNTOUCHED, no closure implied | Original nonblocking/accepted/future dispositions retained |

Final local gates: services40/runtime18 targeted58passed; full1253passed/156freshreports,0failures/errors/skips. ExposedDefect0. Evidence: evidence/11c-r1/; no independent approval or human gate inferred. Stop before any further batch/phase.
''')
with (PHASE / 'prompt.md').open('a') as f:
    f.write('\nRound1 execution: service test-only reproduction, service implementation/README, then independent HTTP writer, all sequential; coordinator ran the requested frozen-source JDK 17 gates. Only R11C-1/R11C-2/R11C-5 repaired. No other batch, reviewer, commit/push or human record. Final handoff: reviewer-prompt-11c-r1.md.\n')
with (PHASE / 'review.md').open('a') as f:
    f.write('\n\n### Subphase 11C repair round 1 — pending independent recheck\n\nAuthorized batch 1 R11C-1/R11C-2 plus user-approved R11C-5 passed local affected/full gates. No recheck reviewer has been launched and no independent repair verdict received. The initial REQUEST_CHANGES above is retained verbatim; local passing tests do not supersede it with self-approval.\n')

readme = '''# Phase 11C repair round 1, batch 1

Local implementation/gates complete; independent recheck pending. No reviewer, cloud/provider, further batch, commit/push or human record.

- preflight.json / java-version.txt / baseline-test-counts.json / step-0.json: base/status, preserved earlier evidence, JDK 17, historical1248 baseline and user-approved README scope.
- delegation.json / service-owner-report.md / test-owner-report.md: sequential one-writer handoffs, exact scope, native IDs, assertions and reasoned mutation sensitivity.
- red-reproduction.json / red*-start.json / red*-result.json / red*-excerpt.txt: first compile-only authoring failure retained; actual red-2 shows4 test failures against unchanged production/README.
- final-format/format-check/targeted/full-check start/result/excerpt records: exact resolved commands/env/exits, immutable start hashes/mtimes, real formatter rewrites, stopped-writing snapshots, frozen sources, raw-log hashes.
- coverage.json / coverage.md: current 20-category named 84-case map; historical maps untouched; new4module cases additionally listed in full-check-summary.json.
- full-check-summary.json / defects.json: fresh XML/log reconciliation, stale exclusions,1253tests/156reports/0failure, ExposedDefect0,423 protected files unchanged, no silent finding closure.
- commands.json / final-validation.json / handoff-files.json: exact gate evidence, scope/ownership/append-only assertions, full changed/new inventory (including prior uncommitted11C evidence).
- run-gate.py / collect-evidence.py / finish-round.py: coordinator reproducible evidence procedures; exclusive record creation prevents overwriting prior gate evidence.
- ../../reviewer-prompt-11c-r1.md: complete user-run recheck prompt. Reviewer edits nothing and runs no builds/tests.

Raw logs remain in /tmp/phase11c-r1-*.log, not reboot-durable. No live service, provider, deployment or general durability result is claimed. Persistent outages/process death after successful binding remain outside batch guarantees. R11C-3 ownership is unassigned; R11C-4/R11C-6 and all other carried observations remain untouched. Initial reviewer unread areas and scan-level historical reading remain disclosed. Human Phase 11 gate is still user-owned.
'''
with (OUT / 'README.md').open('x') as f:
    f.write(readme)

new_prompt_path = PHASE / 'reviewer-prompt-11c-r1.md'
prompt = f'''You are the independent, READ-ONLY reviewer for ScholarChain Phase 11,
Subphase 11C repair round 1, batch 1, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase11.md
   §§2–7.4, §8 Subphase 11C, §§9–11.
3. The primary course Phase 11 specification, Required test inventory and deductions:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-11-adversarial-testing-and-full-repository-review
4. docs/agent-runs/phase-11/prompt.md, owner-report.md, test-report.md,
   review.md, repairs.md, especially initial11C REQUEST_CHANGES and repair-round 1 sections.
5. docs/agent-runs/phase-11/evidence/11c-r1/README.md, preflight.json,
   step-0.json, delegation.json, both specialist owner reports, red-reproduction.json,
   commands.json, all gate start/result/excerpts, coverage.md/coverage.json,
   full-check-summary.json, defects.json, final-validation.json, handoff-files.json.
   Inspect actual source/tests and retained raw logs where available.
6. Initial whole-repository packet evidence/11c/, reviewer-prompt-11c.md and all
   module READMEs/earlier phase registers as needed. Historical pending checkpoints
   do not override later external dispositions; do not rerun old collectors.

Checkpoint facts:
- Branch phase-11. Repair-round base/current HEAD:
  {BASE}. Initial11C assembly was uncommitted and is preserved.
- User-confirmed whole-repository baseline {REVIEW_BASE}.
  Review all repository files at HEAD plus the baseline-to-HEAD diff,
  `git diff {BASE}` and ALL untracked files. No repair commit exists.
- Changed tracked paths: modules/services/README.md;
  modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala;
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/AdversarialRuntimeHttpSpec.scala;
  docs/agent-runs/phase-11/{{prompt,owner-report,test-report,review,repairs}}.md.
- Untracked: new service module SessionBindingRecoverySpec.scala at
  modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/;
  docs/agent-runs/phase-11/reviewer-prompt-11c.md and reviewer-prompt-11c-r1.md;
  initial evidence/11c/ (12 files), current evidence/11c-r1/ (exact full filenames
  and counts in handoff-files.json). Verify every actual file against the inventory.
- Step 0 user selected “Yes, include R11C-5 (Recommended)”. Scope ONLY blocking
  R11C-1/R11C-2 plus same-owner README R11C-5. ExposedDefect tags/explicit runs
  if needed, exact requirement tables and no coverage tool remain prior decisions.
- Coordinator ran all sbt commands with plan§2 JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home,
  PATH=$JAVA_HOME/bin:$PATH, SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml.
  java -version exit0: OpenJDK 17.0.20.1; sbt 1.10.7.
- Actual red gate: `sbt -batch 'services / Test / scalafmtCheck' 'services / Test / testOnly *SessionBindingRecoverySpec'`
  red-2 exit1:4executed/4failed before production/README edits. The prior red
  attempt was a fixture compile error (4 ambiguous references,0tests), corrected
  by the service test owner and honestly retained.
- Final requested format checks:
  `sbt -batch 'services / Test / scalafmtCheck' 'independentTests / Test / scalafmtCheck'`
  exit0; no rewrites.
- Targeted:
  `sbt -batch 'services / testOnly *' 'independentTests / Test / testOnly *AdversarialRuntime*'`
  exit0; services40/7suites + runtime18/3suites =58passed,0failed/canceled/ignored/pending.
- Full `/usr/bin/time -p sbt -batch check`: exit0,1,253 tests / 156 fresh reports,
  0failures/errors/skips; baseline1248+4module+1net independent=1253.
  Services40, independent665. Expected nested failure-probe self-test is not an
  outer failure; outer success/TestRunMarker verified. Raw full log:
  {summary['raw_log']}, {summary['raw_bytes']}bytes,
  SHA256 {summary['raw_sha256']}.
  Full elapsed {read('full-check-result.json')['elapsed_seconds']:.2f}s. Other exact argv/env/exits/raw hashes: commands.json.
- Formatting disclosure: red-format and red-format-2 each rewrote only the new
  module suite; final-format rewrote only QueryService.scala and the HTTP spec.
  Owners authorized those rewrites. Both specialists stopped writing before gates.
  All 8 gate-start records were exclusive-created immediately before launch,
  never rewritten; final hashes/mtimes match. Final 25-file snapshot remained frozen.
- Current coverage20categories:51existing+33new cross-module=84 selected named
  tests, plus4 additional module regression cases. Runtime map21existing+18new=39;
  category16 existing2/new4/total6; category17 2/5/7. Historical maps unchanged;
  current map replaces the old permanent503 expectation and adds lost-reply HTTP.
  ExposedDefect0; no tag/exclusion/build-engineer needed. All mapped cases appear
  in fresh XML. Mutation checks6service+7independent are reasoning only.
- Evidence scripts exit0; git diff --check exit0.423 protected files and earlier
  evidence unchanged except append-only reports. No cloud/provider, nested
  delegation, reviewer, commit/push, human gate or further batch occurred.

Required repair acceptance:
R11C-1 High (formerly F11B-1), service-engineer + independent test-engineer:
- Fake body-binding update really applies the revision0 write, then returns
  Retried(1,Rejected("conditional-conflict")). Authoritative primary-read
  reconciliation proves this caller's intended revision+1/fingerprint/requestId/
  traceId/payload before scheduling. Unique bindingToken is internal opaque JSON;
  reused client IDs cannot let a losing caller claim another binder's row.
- Require one workflow execution,200 or202that completes, persisted SUCCEEDED/result,
  stored-result same-key replay without another run, different body409.
- Verify both module regression and independent actual HTTP→QueryService→real
  runtime workflow case. Count3 is a literal hand-derived fixture fact; verify
  exact accepted claim/audit as well as workflow and LLM counters1.
R11C-2 Medium (coupled), same owners:
- One clean rejection leaves an unbound revision0 row. Same-key replay competes
  for the existing CAS and completes once rather than remaining retryable503forever.
- Both direct-success and lost-winner-reply module concurrency cases use two
  QueryService instances sharing a store and identical client request/trace IDs.
  Force both CAS contenders to rendezvous and losing caller to read the winner's
  QUEUED snapshot before winner returns. Exactly one applied binding/workflow.
- Independent HTTP case must assert initial503with0workflow/model calls, then
  completing replay,2bind attempts/1apply, stored replay/no rerun and changed409.
R11C-5 Low, user-approved README:
- Document real recovery, binder ownership and lost replies accurately; do not
  claim a durable dispatcher. Already-bound process-death and persistent outage
  limitations remain.

Ownership map (exact precedence in docs/agents.md):
- service-engineer alone: modules/services/** production/module tests/README.
  Native /root/service_engineer_11c_r1 wrote these, then stopped.
- test-engineer alone: tests/**; native /root/test_engineer_11c_r1 modified only
  AdversarialRuntimeHttpSpec.scala after service writer stopped; no production edits.
- Coordinator /root: docs/agent-runs/** phase evidence assembly only; prior content
  preserved. Human owns gate/commit/acceptance/ratification records.
- domain-engineer modules/core/**; hadoop-engineer modules/hadoop/**;
  entity-resolution-engineer modules/entity-resolution/**; spark-engineer modules/spark/**;
  storage-engineer modules/storage/**; rag-engineer modules/rag/** and prompts/runtime/**,
  prompts/schemas/**. Each module owner owns its module-local tests.
- build-engineer build.sbt/project/**/format/packaging/ignore/generated marker;
  factory-engineer constitutional/.claude/** except marker/.mcp.json and reserved
  agent-map/evidence-template files. dataset-engineer datasets/**;
  infra-engineer infra/terraform/**,scripts/**,optional .github/workflows/**;
  deploy-engineer approved execution evidence; experiment-engineer experiments/**,
  load-tests/**; documentation-engineer README.md/docs/** outside reserved subtrees;
  incident-responder docs/incidents/**; dependency-updater approved value tokens only.
  Reviewer owns no implementation edits. Unlisted/orphan ownership is not inferred.

Carried items and limitations:
- R11C-3 Medium NONBLOCKING remains ORPHAN: 24 tracked file:/var/** stats/.crc outputs
  need a human-assigned writer before deletion/ignore work. No assignment/removal now.
- R11C-4 Low title-markup blocking mismatch (hadoop-engineer) and R11C-6 Low run-ledger
  CAS lost-reply observation (storage-engineer) untouched. R11C-6 downstream impact
  remains untraced. Do not confuse service binding repair with storage-wide CAS repair.
- F11B-3/F11B-4,11A N3,Phase9 NB1–NB10,Phase10 F7/F8/F10–F17 and earlier Phase5–8
  limits unchanged; see repairs.md and initial evidence/11c/carried-findings.md.
- Raw logs only in /tmp; exact model revision unavailable. Synthetic local fakes
  establish no live DynamoDB/AWS/provider/EMR/scale/cost/durable-dispatch guarantee.
  Initial reviewer did not read most40k main-code lines or the full datasets;
  reports were scan-level and course README summarized. Disclose remaining unread
  scope rather than treating initial APPROVE gates as comprehensive assurance.
- Live AWS/provider Phase14, bounded EMR Phase15, infrastructure Phase12+ remain
  future gates. No optional OpenSearch/index/service/CI/coverage tooling added.
  Codex workflow deviation/instructor acceptance and human Phase 11gate unverified.

Re-assess the WHOLE repository for regressions in this exact 12-point order:
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
The repair acceptance above must not narrow the whole-repository review.

Rules:
- READ-ONLY. Edit/create NOTHING. Run no builds/tests, AWS/provider calls,
  data mutations, commits/pushes or subagents. Do not read secrets (.env,
  credentials, private keys or secret directories). Safe read-only Git/file/
  hash/XML/JSON inspection is allowed.
- Verify every finding against actual current files, then report ALL confirmed
  findings in one pass. Give severity,path:line,concrete failure input,expected/
  actual behavior,evidence,impact,owning agent,acceptance check,blocking yes/no.
  Clearly label code-derived/unexecuted findings; do not invent reproduction.
- Check owner separation for every changed/new path, actual fault injection,
  hand-derived assertions/mutation sensitivity, stored replay and CAS ownership,
  no hidden failing/skipped cases, evidence/raw hashes/start barriers/source freeze,
  no hardcoded live resources/secrets and no unsupported claims.
- Distinguish blockers, nonblocking observations, accepted limits and later gates.
  Local passes do not constitute independent approval; do not repair anything yourself.

Return:
1 VERDICT: APPROVE or REQUEST_CHANGES for Subphase 11C repair round 1 batch 1.
2 Findings in the 12-point order, with all required fields. Explicitly disposition
  R11C-1/R11C-2/R11C-5 against current files/evidence; carried items retain owners.
3 Report fields from docs/agent-runs/README.md: STATUS,OWNER,WORK ORDER,
  FILES CREATED,FILES MODIFIED,COMMANDS RUN,TEST RESULTS,VALIDATION RESULTS,
  ASSUMPTIONS,RISKS,MANUAL ACTION REQUIRED,BLOCKED-ON OWNER,
  BLOCKED-ON EVIDENCE,NEXT GATE. State no reviewer builds/tests/files edited.
4 ONE fenced NEXT PROMPT for the coordinator:
  Append verdict VERBATIM under Subphase 11C repair round 1 in review.md, marked
  user-supplied external review, and append finding dispositions to repairs.md.
  If REQUEST_CHANGES, authorize only the next bounded blocking owner batch with
  explicit IDs/paths, Step 0, sequential/no nested delegation, affected/full JDK 17
  gates and immutable pre-launch records; then complete recheck handoff and STOP.
  If APPROVE, tell coordinator to confirm the user's11Ccommit (ask/wait if not
  committed; no automatic commit/push), and tell user Phase 11is ready for their
  own human-gate/commit records. Do not infer human acceptance or start/prepare
  another batch or Phase12. R11C-3 ownership needs a separate human decision.
  Never launch a reviewer or write human-gate.md,commit.txt,approval/ratification
  records. Stop at the authorized handoff with a complete reviewer prompt as applicable.
'''
with new_prompt_path.open('x') as f:
    f.write(prompt)

# Manifest includes pending evidence outputs, then checks actual status after writing them.
untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
pending = {str((OUT / n).relative_to(ROOT)) for n in ['handoff-files.json', 'final-validation.json']}
untracked |= pending
for p in untracked:
    assert p.startswith('docs/agent-runs/phase-11/') or p == module_test, p
manifest = dict(base_sha=BASE, head=BASE, branch='phase-11', modified=changed,
    untracked=sorted(untracked), modified_count=len(changed), untracked_count=len(untracked),
    note='Includes preserved initial11C assembly plus this repair; no staging/commit.')
save('handoff-files.json', manifest)
processes = subprocess.check_output(['ps', '-axo', 'pid=,comm='], text=True)
java = [line.strip() for line in processes.splitlines()
        if Path(line.strip().split(maxsplit=1)[-1]).name in ['java', 'sbt']]
assert not java, java
preflight = read('preflight.json')
prefix_preserved = {}
for p, size in preflight['prior_report_prefix_bytes'].items():
    assert hashlib.sha256((ROOT / p).read_bytes()[:size]).hexdigest() == preflight['prior_evidence_hashes'][p]
    prefix_preserved[p] = True
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
save('final-validation.json', dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    branch='phase-11', base_sha=BASE, head=BASE, modified_count=len(changed), untracked_count=len(untracked),
    all_prior_report_prefixes_preserved=prefix_preserved, protected_files_unchanged=423,
    historical_evidence_preserved=True, gate_start_records_unchanged=8,
    final_sources_frozen=25, current_mapped_cases=84, full_check_totals=totals,
    targeted=dict(services=40, runtime=18, total=58, failed=0), exposed_defect_count=0,
    ownership_scope_pass=True, git_diff_check_exit=0, java_or_sbt_processes=java,
    child_agents='Both repair specialists completed; no active child agents',
    reviewer_launched=False, cloud_provider_calls=0, commit_push=False,
    human_gate_or_approval_record_written=False, further_batch_or_phase_started=False,
    pending='Independent user-launched recheck; local verification does not supersede REQUEST_CHANGES'))
assert sorted(git('ls-files', '--others', '--exclude-standard').splitlines()) == sorted(untracked)
print(json.dumps(dict(status='LOCAL_REPAIR_COMPLETE_RECHECK_PENDING', tests=totals,
    targeted=58, modified=len(changed), untracked=len(untracked), git_diff_check_exit=0)))

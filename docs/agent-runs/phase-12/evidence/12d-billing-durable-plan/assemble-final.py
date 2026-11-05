from pathlib import Path
import datetime, hashlib, json, re, shutil, subprocess

R=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
P=R/'docs/agent-runs/phase-12'
E=P/'evidence/12d-billing-durable-plan'
S=Path('/tmp/scholarchain-phase12d-billing-durable-plan-handoff/safe')
PLAN_SHA='ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855'
BASE='/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap'
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=R)

assert git('rev-parse','HEAD').decode().strip()=='5ca8406bad5fe55f732458fa0cbd5d561ac83d8f'
assert git('branch','--show-current').decode().strip()=='phase-12'
assert sha(S/'artifact-manifest.json')=='3982c5cae40d26705f329b724ed544209b24bcddf0302e0546786b355e93d4b3'
m=json.loads((S/'artifact-manifest.json').read_text())
assert m['artifact_count']==len(m['files'])==32
assert {x['path'] for x in m['files']}=={str(q.relative_to(S)) for q in S.rglob('*') if q.is_file() and q.name!='artifact-manifest.json'}
for x in m['files']:
    q=S/x['path'];assert not q.is_symlink() and sha(q)==x['sha256'] and q.stat().st_size==x['bytes']
assert not (E/'infra').exists()
shutil.copytree(S,E/'infra')
summary=json.loads((E/'infra/plan-summary.json').read_text())
assert summary['plan_sha256']==PLAN_SHA and summary['plan_bytes']==6631 and summary['plan_exit_code']==2
assert summary['counts']==dict(add=1,change=0,destroy=0,replace=0) and not summary['applied']
assert summary['plan_path']==BASE+'/billing.execution.tfplan'
commands=json.loads((E/'infra/commands.json').read_text())
assert len(commands)==7 and [x['exit_code'] for x in commands]==[0,0,0,0,0,2,0]
assert commands[5]['environment']['TF_DATA_DIR']==BASE+'/tf-data'
assert commands[5]['cwd']==BASE+'/config'
assert '-state='+BASE+'/billing.execution.tfstate' in commands[5]['argv']
pre=json.loads((E/'preflight.json').read_text())
for x in pre['prior_packet_files']:
    q=R/x['path'];assert sha(q)==x['sha256'] and q.stat().st_size==x['bytes']
human=R/pre['human_record']['path']
assert sha(human)==pre['human_record']['sha256'] and human.stat().st_size==1334
freeze=json.loads((E/'source-freeze-before.json').read_text())
for x in freeze['files']:
    q=R/x['path'];assert sha(q)==x['sha256'] and q.stat().st_size==x['bytes'] and q.stat().st_mtime_ns==x['mtime_ns']
assert len(freeze['files'])==209
assert re.search(r'^enable_budget_resource\s*=\s*false',(R/'infra/terraform/environments/course.tfvars').read_text(),re.M)
assert (E/'infra/approved-public-inputs.json').read_bytes()==(P/'evidence/12d-billing-execution-plan/infra/approved-public-inputs.json').read_bytes()
write('source-freeze-after.json',{'checked_utc':NOW,'before_reference':'source-freeze-before.json','before_sha256':sha(E/'source-freeze-before.json'),'checked_files':209,'hash_bytes_mtime_mismatches':[],'no_source_or_pin_lock_changes':True,'new_sbt_run':False,'historical_sbt_reference':'docs/agent-runs/phase-12/evidence/12d-billing-policy-amendment/build/','historical_sbt_tests':1255,'historical_fresh_xml':157,'historical_failures_errors_skips':0})
notes=json.loads((E/'coordinator-preparation-notes.json').read_text())
notes['human_fresh_identity_and_saved_pending']=False
notes['read_only_lookup_errata'].append({'command_summary':'Safe inventory read plus guessed recipient-git-scan.json','exit_code':'Grouped shell returned0 because commands.json was final successful read; intermediate cat reported missing file','explanation':'Actual listed filename recipient-privacy-scan.json then read successfully; no private artifact accessed.'})
(E/'coordinator-preparation-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
scan=json.loads((E/'infra/recipient-privacy-scan.json').read_text())
assert scan['files_scanned']==2995 and scan['matching_file_count']==0
write('result.json',{'completed_utc':NOW,'scope':'Fresh durable-path read-only billing plan only','plan_sha256':PLAN_SHA,'plan_bytes':6631,'counts':summary['counts'],'applied':False,'profile':'scholarchain-billing-deployer','state_path':BASE+'/billing.execution.tfstate','plan_path':BASE+'/billing.execution.tfplan','TF_DATA_DIR':BASE+'/tf-data','cwd':BASE+'/config','old_tmp_plan':'Superseded; retained untouched, not deleted','P1':'APPROVE; F1/F2/F3 closed by independent review','P2':'Durable-plan evidence prepared; independent review pending; not self-closed','G1':'Human own-words affirmation of abe3a50a record required before any apply','G2':'Accepted timing uncertainty/deviation does not prove original60minute compliance','P3':'In-window exact caller and exact-name remote budget absence checks still unrun','password_detour':'User withdrew recovery proposal and reported access; no agent reset, no human reset reported or inferred','live_budget_or_delivery_proof':False,'no_jobs_running':True})
report='''STATUS: COMPLETE
OWNER: coordinator assembling infra-engineer /root/infra_12d_durable_plan
WORK ORDER: User-invoked P1 timing APPROVE NEXT PROMPT authorizes only fresh durable-path read-only billing plan. P1 F1/F2/F3 independently closed. Existing selected public inputs/storage/retention reused; fresh human operator/role console flow, user-pasted exact CLI identity and hidden-helper success received. Branch phase-12; base/HEAD5ca8406bad5fe55f732458fa0cbd5d561ac83d8f. Preparation complete, independent durable-plan review pending.
FILES CREATED: evidence/12d-billing-durable-plan/** including137-file prior-packet baseline,209-source freeze, fresh authentication/screenshots, preparation checkpoint,32 final infra artifacts plus manifest, result/integrity/handoff; reviewer-prompt-12d-billing-durable-plan.md. Selected protected durable primary/backups/config/toolchain/runner/helper/private artifacts created outside Git. No password recovery authorization or reset performed by agent.
FILES MODIFIED: Append-only prompt.md, review.md, repairs.md, owner-report.md and test-report.md across this continuation. The separately recorded password-recovery proposal is unapproved and was withdrawn when user regained access. Source, human record and137 earlier packet files unchanged. No reset, policy widening or old-plan deletion inferred.
COMMANDS RUN: Seven exact Terraform argv/cwd/non-secret environment/times/exits/log hashes in infra/commands.json: offline init/fmt/validate/test all0, protected init0/plan2/show0. No failed provider retry this time; reviewed escalation used for durable writes/provider spawning. Human ran fresh login/STS and hidden helper; output retained as user-supplied, actual human process cwd/times/exits unknown. Coordinator public file/JSON/hash/prefix/Git checks only. Read-only filename lookup errata in coordinator-preparation-notes.json. No independent agent AWS identity/inventory call.
TEST RESULTS: Current billing7passed/0failed,6assertions,4expected-failure runs. All209 source hash/bytes/mtimes unchanged; seven config copies match source. No new sbt or four-root gate; historical1255-test/157-fresh-XML result remains reference, not rerun. Generic public-address scan distinguishes unchanged reserved mock fixtures from recipient values.
VALIDATION RESULTS: Durable plan proposes only aws_budgets_budget.project[0],1create/0change/0destroy/0replace. USD200 COST/CUSTOM, UTC2026-10-01_00:00 through2027-01-01_00:00, exact account/name/tags, credits/refunds excluded, no filters, three ACTUAL GREATER_THAN PERCENTAGE alerts50/80/100, one private email each/zeroSNS. New plan6631bytes/SHA256ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855 at selected durable primary/billing.execution.tfplan. State primary/billing.execution.tfstate; TF_DATA_DIR primary/tf-data; cwd primary/config. Owned directories0700,data0600,executables0700, durable provider targets verified, no selected/default state exists. Scope-limited recipient comparison2995Git-visible docs/infra public-text files,1539paths excluded,0matches; no private input contents/hash/size returned. Terraform1.13.5/AWS6.44.0/lock unchanged; main course budget remains disabled. Old temporary plan35e35914… superseded and untouched.
ASSUMPTIONS: User-pasted fresh STS identity accurately represents the fresh dedicated profile. Profile/account guard consumed by provider; actual provider-resolved ARN not separately queried. Metadata confirms physical selected path outside recognized sync/Git/volatile paths; arbitrary third-party backup software cannot be ruled out. Local backup is same disk, not disaster recovery.
RISKS: Independent durable-plan review, G1 human own-words pre-apply affirmation, P3 fresh caller/exact-name absence and later human-written exact-checksum/window approval remain required. Remote budget absence/ownership, create/tag rights, CUSTOM/deprecated CostTypes/tag acceptance, active monitor/delivery, refresh lifetime, IAM adoption/inventory, current costs/remaining allowance and EMR gates remain unverified. No state means no backup yet, not remote absence. Alerts are not hard spending cutoffs. ProposedUSD5spike/USD10EMRreserve/USD5.09margin and B1/B2/B3/R1/N19/N20 unchanged.
MANUAL ACTION REQUIRED: User launches independent read-only durable-plan review with complete prompt. Later human apply approval must separately name exact reviewed checksum/identity/window and retain state/backup controls; obtain G1 affirmation and execute authorized P3 checks first. No more password or recipient values requested in chat. Human controls retention/cleanup.
BLOCKED-ON OWNER: None for this completed read-only plan. User-launched independent reviewer/human architect own later acceptance and execution gates.
BLOCKED-ON EVIDENCE: None for plan completion; no durable-plan verdict/apply authority, G1 affirmation, P3 live checks, active monitor/delivery or paid-run readiness yet.
NEXT GATE: User-launched independent read-only durable-plan review and stop. Nothing applied; no IAM/resource mutation, import/destroy/state mutation, paid call, reviewer launch, commit/push or Phase13.
'''
(E/'coordinator-report.md').write_text(report)
heading='\n\n## Subphase 12D — durable-path read-only billing plan completion\n\n'
for n in ['owner-report.md','test-report.md']:
    assert heading not in (P/n).read_text()
    with (P/n).open('a') as f:f.write(heading+report)
with (P/'repairs.md').open('a') as f:
    f.write(heading+'P2 durable-path plan now generated successfully with selected state/data/config/toolchain and new checksum ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855. Independent durable-plan review still required; coordinator does not close P2. P1 F1/F2/F3 remain independently CLOSED. G1 pre-apply human affirmation, G2 accepted timing uncertainty, F4 inventory/adoption/refresh and P3 live checks remain. Password-recovery proposal was withdrawn; no reset performed by agent or reported by human. Old/tmp plan35e35914… remains untouched but superseded. Nothing applied; all live budget/EMR gates remain open.\n')
review='''Independent read-only review — Phase12D fresh DURABLE-PATH billing plan ONLY.

Repository /Users/danny/Documents/UIC/CS441/ScholarChain; branch phase-12; base/HEAD5ca8406bad5fe55f732458fa0cbd5d561ac83d8f. Existing uncommitted work retained. Read AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md, docs/agent-runs/README.md and neutral phase plan docs/agent-runs/phase-12/evidence/12c/phase12-plan-at-start.md.

Evidence: docs/agent-runs/phase-12/evidence/12d-billing-durable-plan/. User-invoked P1 APPROVE next prompt authorizes this read-only plan only. P1 F1/F2/F3 closed; do not reopen the completed technical IAM/timing review. G1 remains a pre-apply human affirmation, G2 an accepted historical deviation/uncertainty. No apply, IAM mutation or spending approved.

Forbidden: edits, tests/builds, Terraform/AWS/login/console/account/paid calls, agents, credentials/AWS config/cache/state/private-input/raw-plan/raw-JSON/log reads, human approval writes, commits/pushes and Phase13. Read-only Git/public source/sanitized evidence/hash inspection and filesystem metadata allowed. Optional opaque saved-plan checksum only; never decode plan. Do not invoke retained helper/runner scripts.

Verify:
1. New plan /Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/billing.execution.tfplan,6631bytes,SHA256ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855. Only aws_budgets_budget.project[0],1add/0change/0destroy/0replace. Account530332961125/profile scholarchain-billing-deployer/us-east-2, USD200 COST/CUSTOM2026-10-01_00:00→2027-01-01_00:00UTC, budget scholarchain-project-budget, no filters, credit/refund excluded, five exact governance tags, ACTUAL/GREATER_THAN/PERCENTAGE50/80/100, one private subscriber each/zeroSNS.
2. Exact cwd primary/config; explicit state primary/billing.execution.tfstate; TF_DATA_DIR primary/tf-data; durable executable/tfrc/provider mirror. Resolve installed provider symlinks: all runtime targets remain inside primary, not/tmp. New owned dirs0700/data0600/executables0700, physical non-symlink primary/backups, ACL/ownership checks and recognized cloud-sync/Git exclusion. Same-disk backup limitation and selected retention explicit; backup directory empty because no state, no fictitious backup claim. No selected/default state after plan; no remote absence inference.
3. infra/commands.json exactly7Terraform calls exits0/0/0/0/0/2/0; current7mocktests0fail,6assertions,4expected-failure runs. Reviewed escalation, no sandbox-failure retry this time. Check logs/public helper/runner/setup and seven source copies. Private input never directly read/hashed/size-published; protected JSON only programmatic allowlist extraction. Scoped exact-recipient scan2995Git-visible docs/infra public-text files/1539excluded/0matches; do not overclaim all repository binaries/secrets scanned. New public generic-address scan permits only byte-identical reserved mock fixtures.
4. Fresh user console screenshots, exact-role STS output and hidden-helper success support prerequisite workflow; distinguish user evidence from independent agent API. Provider resolved ARN not separately queried. No passwords/recipient values in evidence. Recovery proposal was withdrawn; no reset reported/performed by agent. Old/tmp plan35e35914… superseded, retained untouched, no decoding/deletion.
5. Root/nested/preparation manifests, final-integrity.json and handoff-files.json reconcile. All209 source SHA/bytes/mtimes and137 earlier packet files unchanged; human record1334bytes/SHAabe3a50ad7167fa01227c73e15e92a422a50609f6313bdcc56404cb61765d71a unchanged. Five phase-record prefixes preserved; original P1 review appended verbatim. Pins/locks/source unchanged; course budget disabled. No new sbt claimed; historical full gate clearly attributed. Lookup errata retained, no source/live failures hidden.
6. This demonstrates durable read-only planning, not live create/tag permission, CUSTOM/CostTypes/tags acceptance, delivery, remote ownership/absence, costs/remaining allowance, full refresh lifetime or EMR feasibility. Keep F4/G1/G2/P3 and B1/B2/B3/R1/N19/N20. No paid run, apply or Phase12D completion.

Return APPROVE or REQUEST-CHANGES for DURABLE READ-ONLY PLAN ONLY, explicit P2 assessment, severity/path/evidence/owner/acceptance findings, exactly14report fields and complete next coordinator prompt. Approval does not authorize apply/IAM/spending or Phase12D completion. If approved, next prompt records verdict append-only and prepares a separately bounded apply proposal with G1 human affirmation, exact reviewed checksum/identity/window, P3 caller/exact-budget checks, identical state/data/config/toolchain, backup/retention and private post-apply readback/delivery requirements. Human writes any actual apply approval personally. Never launch reviewer or execute mutation; stop after review.
'''
(P/'reviewer-prompt-12d-billing-durable-plan.md').write_text(review)
(E/'handoff.md').write_text('''Fresh durable-path USD200 budget plan COMPLETE for read-only planning; independent review pending. Nothing applied.

This replaces the temporary plan to address P2 durability. It proposes the same single account-wide budget, not ScholarChain deployment/EMR. New plan6631bytes/SHA256ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855. Saved under /Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/. Exact state/data/cwd/toolchain paths and7commands are in infra/commands.json; summary in infra/plan-summary.json.

Tests7/0,6assertions,4expected-failure runs. Source209and137earlier-packet files unchanged; no new sbt run. Five coordinator records append-only, human record unchanged. Final inventory/manifest checks retained. Preparation checkpoint preserved separately from final infra evidence.

P1 independently approved; P2 awaits this review. Later gates: G1 personal affirmation, P3 exact identity/remote-name check, human-written exact-checksum/window approval, state/backup procedure, budget/accounting/tags/alerts/readback and private delivery. All live cost/EMR gates remain open. Old/tmp plan superseded but untouched. Private recipient/raw plan/logs stay protected outside Git under selected retention. No new secret inputs, reset, apply or spending authorized by handoff.
''')
prefix=[]
for x in pre['records']:
    q=R/x['path'];b=q.read_bytes();assert hashlib.sha256(b[:x['bytes']]).hexdigest()==x['sha256']
    assert b.startswith(git('show','HEAD:'+x['path']))
    prefix.append({'path':x['path'],'before_sha256':x['sha256'],'before_bytes':x['bytes'],'before_prefix_preserved':True,'HEAD_prefix_preserved':True,'after_sha256':sha(q),'after_bytes':len(b)})
write('record-prefix-check.json',{'records':prefix,'human_record_unchanged':True,'prior_packet_files_unchanged':137})
write('final-integrity.json',{'checked_utc':NOW,'source_files_unchanged':209,'prior_packet_files_unchanged':137,'human_record_sha256':sha(human),'phase_records_append_only':5,'infra_artifacts':32,'infra_manifest_sha256':sha(E/'infra/artifact-manifest.json'),'plan_sha256':PLAN_SHA,'no_jobs_running':True,'reviewer_not_launched':True,'applied':False})
result=subprocess.run(['git','diff','--check'],cwd=R,capture_output=True)
(E/'diff-check.log.txt').write_bytes(result.stdout+result.stderr);assert result.returncode==0
write('diff-check-result.json',{'argv':['git','diff','--check'],'cwd':str(R),'exit_code':result.returncode,'output_sha256':sha(E/'diff-check.log.txt')})
for n in ['handoff-files.json','evidence-manifest.json','final-status.log.txt']:(E/n).touch()
status=git('status','--porcelain=v1','--untracked-files=all').decode();(E/'final-status.log.txt').write_text(status)
previous=set((E/'preflight-status.log.txt').read_text().splitlines());current=set(status.splitlines())
assert previous<=current,'Earlier Git status entry disappeared/changed'
write('handoff-files.json',{'branch':'phase-12','head':pre['head'],'preflight_status_entries':pre['status_entries'],'final_status_entries':len(status.splitlines()),'new_status_entries_since_start':sorted(current-previous),'new_external_work_file':'docs/agent-runs/phase-12/reviewer-prompt-12d-billing-durable-plan.md','phase_records_append_only':[x['path'] for x in pre['records']],'evidence_files':[str(q.relative_to(E)) for q in sorted(E.rglob('*')) if q.is_file()],'earlier_uncommitted_work_retained':True,'password_detour_new_files':'docs/agent-runs/phase-12/evidence/12d-password-recovery-proposal/ (proposal only, withdrawn)'})
# Conventional address scan of new public packet, never compare/read private input.
fixtures=[]
for q in [*E.rglob('*'),P/'reviewer-prompt-12d-billing-durable-plan.md']:
    if not q.is_file():continue
    try:t=q.read_text()
    except UnicodeDecodeError:continue
    hits=re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',t)
    if hits:
        assert str(q.relative_to(E)) in ['infra/config-copies/tests/budget.tftest.hcl','infra-preparation/config-copies/tests/budget.tftest.hcl','infra/recipient-privacy-scan.json','infra/run.py','infra/patch-runner.py','infra-preparation/run.py']
        assert all(v.rsplit('@',1)[1]=='example.invalid' for v in hits)
        fixtures.append({'path':str(q.relative_to(E)),'reserved_example_matches':len(hits)})
write('public-address-scan.json',{'scope':'Current public durable-plan evidence/reviewer prompt; binary images excluded; no private input used','nonfixture_matches':0,'reserved_fixtures':fixtures,'exact_recipient_scan_reference':'infra/recipient-privacy-scan.json (2995 public docs/infra text files,0matches;1539excluded)'})
# Refresh inventory after the privacy-result file is created.
inv=json.loads((E/'handoff-files.json').read_text());inv['evidence_files']=[str(q.relative_to(E)) for q in sorted(E.rglob('*')) if q.is_file()]
(E/'final-status.log.txt').write_bytes(git('status','--porcelain=v1','--untracked-files=all'))
nowstatus=set((E/'final-status.log.txt').read_text().splitlines());inv['final_status_entries']=len(nowstatus);inv['new_status_entries_since_start']=sorted(nowstatus-previous);write('handoff-files.json',inv)
files=[q for q in sorted(E.rglob('*')) if q.is_file() and q!=E/'evidence-manifest.json']
write('evidence-manifest.json',{'checked_utc':NOW,'self_excluded':'evidence-manifest.json','count':len(files),'files':[{'path':str(q.relative_to(E)),'sha256':sha(q),'bytes':q.stat().st_size} for q in files]})
print(json.dumps({'plan_complete':True,'evidence_files':len(files)+1,'current_tests_passed':7,'source_unchanged':209,'prior_packet_files_unchanged':137,'phase_prefixes_preserved':5,'git_status_entries':inv['final_status_entries'],'new_plan_sha256':PLAN_SHA,'nothing_applied':True,'manifest_sha256':sha(E/'evidence-manifest.json')}))

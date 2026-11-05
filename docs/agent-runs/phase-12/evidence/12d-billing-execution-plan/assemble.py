"""Assemble only curated public evidence; never open protected planning artifacts."""
from pathlib import Path
import datetime, hashlib, json, re, shutil, subprocess

ROOT = Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
PHASE = ROOT / 'docs/agent-runs/phase-12'
E = PHASE / 'evidence/12d-billing-execution-plan'
SAFE = Path('/tmp/scholarchain-phase12d-billing-execution-plan/safe')
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
BASE_SHA = '5ca8406bad5fe55f732458fa0cbd5d561ac83d8f'
PLAN_SHA = '35e3591498a3708ff82617ff4ee382f3402bdcf0176a8d4c95e6260913d1cdc5'

def digest(b): return hashlib.sha256(b).hexdigest()
def write(name, data):
    (E/name).write_text(json.dumps(data, indent=2)+'\n')
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)
def info(p):
    b=p.read_bytes()
    return {'path':str(p.relative_to(ROOT)), 'sha256':digest(b), 'bytes':len(b), 'mtime_ns':p.stat().st_mtime_ns}

assert git('rev-parse','HEAD').decode().strip()==BASE_SHA
assert git('branch','--show-current').decode().strip()=='phase-12'
baseline=json.loads((E/'preflight-baseline.json').read_text())
assert baseline['file_count']==len(baseline['files'])==4397
manifest=json.loads((SAFE/'artifact-manifest.json').read_text())
assert digest((SAFE/'artifact-manifest.json').read_bytes())=='e48dcfb0d7dd3a9f53786c64602d4ee28284ed41856fff0fefc60c949a39ff2e'
assert manifest['artifact_count']==len(manifest['files'])==31
assert not (E/'infra').exists(), 'Assembly is single-use; do not overwrite earlier evidence'
for x in manifest['files']:
    p=SAFE/x['path']; assert p.is_file() and not p.is_symlink()
    b=p.read_bytes(); assert digest(b)==x['sha256'] and len(b)==x['bytes']
shutil.copytree(SAFE,E/'infra')

summary=json.loads((E/'infra/plan-summary.json').read_text())
assert summary['plan_sha256']==PLAN_SHA and summary['plan_bytes']==6626
assert summary['counts']==dict(add=1,change=0,destroy=0,replace=0)
assert summary['applied'] is False
assert summary['budget']['account_id']=='530332961125'
assert summary['budget']['name']=='scholarchain-project-budget'
assert summary['budget']['limit_amount']=='200'
assert len(summary['notifications'])==3
assert [n['threshold'] for n in summary['notifications']]==[50,80,100]
assert all(n['subscriber_count']==1 and n['sns_subscriber_count']==0 for n in summary['notifications'])
assert 'subscriber_email_addresses' not in json.dumps(summary)
assert not re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',json.dumps(summary))
assert len(json.loads((E/'infra/commands.json').read_text()))==10
assert re.search(r'^enable_budget_resource\s*=\s*false', (ROOT/'infra/terraform/environments/course.tfvars').read_text(),re.M)

previous=PHASE/'evidence/12d-billing-policy-amendment/source-freeze.json'
oldfreeze=json.loads(previous.read_text())
fresh=[info(ROOT/x['path']) for x in oldfreeze['files']]
assert len(fresh)==209
assert all(a==b for a,b in zip(fresh,oldfreeze['files']))
write('source-freeze.json',{'timestamp_utc':NOW,'scope':'Same 209 source paths as prior approved freeze; no source changes or new sbt run','reference':str(previous.relative_to(ROOT)),'reference_sha256':digest(previous.read_bytes()),'file_count':len(fresh),'files':fresh})
write('regression-reference.json',{'current_billing_tests':{'passed':7,'failed':0,'assertions':6,'expected_failure_runs':4},'current_full_sbt_run':False,'reason':'No source or behavior changes. All 209 reference source SHA/bytes/mtimes match; complete preflight baseline also reconciled. Relevant billing gates were rerun.','historical_sbt':{'evidence':'docs/agent-runs/phase-12/evidence/12d-billing-policy-amendment/build/','tests':1255,'fresh_xml':157,'failures':0,'errors':0,'skips':0,'stale_xml_excluded':1,'raw_log_sha256':'e1a8bce426a50cf105c4e3bd9184c7237267215251c573ad9e2a6dc5cb90931b'},'historical_four_root_tests':{'passed':72,'failed':0,'assertions':80,'expected_failure_runs':40},'historical_results_are_not_new_runs':True})
write('human-input-completion.json',{'recorded_utc':NOW,'public_input_confirmation_verbatim':'everything is good','private_helper_reply_verbatim':'Saved','private_helper_command':'python3 -I /tmp/scholarchain-phase12d-billing-execution-plan/save-recipient.py','exact_recipient_not_captured':True,'human_command_exit_code':'not separately captured; human reported success','private_file_contents_hash_and_size_not_in_evidence':True})
write('public-references.json',{'access_context':'Primary documentation browsed during this work order, client date October 31, 2026','references':[{'url':'https://developer.hashicorp.com/terraform/cli/v1.13.x/commands/plan','use':'Pinned CLI version: plan proposes changes; -out retains a sensitive plan; detailed-exitcode 2 means proposed changes.'},{'url':'https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/v6.44.0/website/docs/index.html.markdown','use':'Pinned provider profile/configuration precedence and allowed_account_ids guard. Named profile is not immutable resolved-ARN proof.'},{'url':'https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/','use':'Standard budget monitoring and notifications are free under published pricing. This proposed budget has no Budget Actions or reports. USD200 is the monitoring threshold, not a purchase or hard cutoff.'}],'lookup_limitations':['Registry 6.44.0 documentation page required JavaScript; pinned raw provider documentation used instead. Latest Terraform page replaced with pinned 1.13.x documentation.'],'actual_current_account_cost_and_remaining_allowance_verified':False})
write('coordinator-checks.json',{'recorded_utc':NOW,'safe_manifest_artifacts':31,'safe_manifest_sha256':digest((E/'infra/artifact-manifest.json').read_bytes()),'sanitized_summary_checked':True,'source_reference_paths_equal':209,'foundation_budget_disabled':True,'foundation_tfvars':'infra/terraform/environments/course.tfvars','no_account_inventory_call':True,'no_private_raw_artifact_opened_by_coordinator':True,'specialist_no_running_jobs_or_children_reported':True,'read_only_lookup_errata':['Earlier preflight cat requested nonexistent billing-bootstrap/providers.tf; main.tf holds provider. Earlier listing of deleted old private planner directory exited 2.','Coordinator cat requested nonexistent safe/private-artifact-metadata.json and returned 1; actual safe/protected-artifact-metadata.json then read successfully.','Coordinator rg requested nonexistent infra/terraform/course.tfvars and exited 2; rg --files found environments/course.tfvars, disabled flag confirmed.','Collapsed git status --short reports directories; final inventory uses --untracked-files=all, matching preflight entry semantics.'],'report_cleanup':'Specialist corrected unreviewed scratch owner-report command spacing and regenerated its manifest before assembly; no source/live commands changed.'})

report='''STATUS: COMPLETE
OWNER: coordinator assembling infra-engineer /root/infra_12d_execution_plan
WORK ORDER: User “alright let's continue” selects the fresh read-only billing plan; “everything is good” confirms USD 200, scholarchain-project-budget, October 1, 2026 through January 1, 2027 UTC, dedicated profile scholarchain-billing-deployer/account 530332961125/us-east-2; “Saved” confirms private Terminal recipient entry. Branch phase-12; base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f. Complete for planning only; independent review pending.
FILES CREATED: docs/agent-runs/phase-12/evidence/12d-billing-execution-plan/**, including 31 curated infra artifacts plus nested manifest, source-reference/freeze, input/command/privacy/regression/integrity evidence; reviewer-prompt-12d-billing-execution-plan.md. Protected raw plan/logs/JSON remain outside Git.
FILES MODIFIED: Append-only phase prompt.md, repairs.md, owner-report.md and test-report.md. No production source or earlier evidence changed. review.md and human-owned records preserved. Exact current-work footprint is handoff-files.json; earlier uncommitted work is retained.
COMMANDS RUN: infra/commands.json retains all 10 exact Terraform argv/cwd/timestamp/environment/exit/log-hash records. Initial sandbox init 0, fmt 0, validate 1 (provider handshake); identical pinned retry init/fmt/validate/test all 0. Protected live init 0, plan 2 (-detailed-exitcode), show -json 0. Pinned binary /tmp/scholarchain-phase12b-repair1-infra/terraform; Terraform 1.13.5/AWS 6.44.0. Isolated backend-disabled config, explicit external -state/-out and public/private -var-file inputs. No standalone AWS identity/inventory call. Coordinator performed curated file/JSON/hash comparisons, Git metadata/diff checks and primary-document lookups. Read-only lookup errors are disclosed in coordinator-checks.json.
TEST RESULTS: Current billing mock tests 7 passed / 0 failed, 6 assertions, 4 expected-failure runs. Initial provider-handshake validate failure preserved and resolved by same pinned retry outside sandbox; no policy/source widening. No new full sbt run: all 209 reference source SHA/bytes/mtimes unchanged. Historical 1255-test/157-fresh-XML JDK17 gate and 72-test four-root gate remain references, not current runs.
VALIDATION RESULTS: Fresh execution-profile plan: 1 create / 0 change / 0 destroy / 0 replace, only aws_budgets_budget.project[0]. Plan SHA256 35e3591498a3708ff82617ff4ee382f3402bdcf0176a8d4c95e6260913d1cdc5, 6626 bytes, /tmp/scholarchain-phase12d-billing-execution-plan/billing.execution.tfplan. USD200 COST/CUSTOM exact UTC dates, account-wide/no filters, credit/refund excluded, five tags and three ACTUAL GREATER_THAN PERCENTAGE alerts at 50/80/100, one private email each/zero SNS. Seven config copies and toolchain/locks unchanged. Recipient values excluded from safe summary; protected directory 0700/files 0600. No state file created. Main course budget remains disabled. Baseline, prefix, human/prior-record and manifest reconciliation retained.
ASSUMPTIONS: Prior user-provided STS output identifies the intended assumed role. Pinned provider successfully consumed the named profile for planning with allowed account guard; resolved provider ARN was not independently queried. Human-entered notification recipient is correct. Local state absence does not establish remote budget absence.
RISKS: Remote name/ownership conflict unverified; check before later apply under separate scope. Plan success does not prove live create/tag permissions, CUSTOM/deprecated CostTypes/tags acceptance, delivery, full OAuth refresh lifetime, current costs or remaining allowance. Raw artifacts may contain recipient; human decides retention without automatic deletion. Budget alerts are not hard cutoffs; ModifyBudget is coarse. Manual IAM Terraform adoption and actual bootstrap timing remain unverified. All paid EMR/runtime/teardown gates remain open; proposed USD5 spike/USD10 EMR reserve/USD5.09 upper-window margin and B1/B2/B3/R1/N19/N20 unchanged.
MANUAL ACTION REQUIRED: User launches independent read-only review with the supplied prompt. Separate human-written exact-plan apply authorization is required later, including execution identity/checksum and ownership/state handling. Then verify actual budget/accounting/tags/dates/notifications and delivery before paid work. No approval file written for the human.
BLOCKED-ON OWNER: None for completed read-only planning. Human architect and deployment owner control review, ownership/state decision, private retention and any later apply.
BLOCKED-ON EVIDENCE: Live budget acceptance/active monitor/delivery and remote ownership remain unverified; no Phase12D runtime completion or spending authorization.
NEXT GATE: User-launched independent read-only review of this plan only; stop. No apply/destroy/import, IAM mutation, paid calls, EMR launch, reviewer launch, commit/push or Phase13 performed or authorized by this result.
'''
(E/'coordinator-report.md').write_text(report)
heading='\n\n## Subphase 12D — fresh billing execution-identity read-only plan\n\n'
for name in ['owner-report.md','test-report.md']:
    p=PHASE/name
    assert heading not in p.read_text()
    with p.open('a') as f: f.write(heading+report)
with (PHASE/'repairs.md').open('a') as f:
    f.write(heading+'Planning now demonstrates pinned provider consumption of the dedicated login profile. Initial sandbox provider handshake failure is retained; identical pinned retry passed. No source repair or policy widening occurred. Exact provider ARN, refresh lifetime, live budget acceptance/delivery, remote ownership, manual IAM adoption and bootstrap timing remain limited/unverified. No active monitor or paid EMR readiness is claimed. B1/B2/B3/R1/N19/N20 and all live gates carry forward unchanged.\n')

review='''Independent read-only review — Phase 12D fresh billing execution-identity plan ONLY.

Repository /Users/danny/Documents/UIC/CS441/ScholarChain; branch phase-12; base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f. Earlier 12D work remains uncommitted. Read AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md, docs/agent-runs/README.md and docs/agent-runs/phase-12/evidence/12c/phase12-plan-at-start.md. Current evidence: docs/agent-runs/phase-12/evidence/12d-billing-execution-plan/.

User authorized a fresh read-only plan (“alright let's continue”), confirmed all public inputs (“everything is good”), and confirmed hidden local recipient entry (“Saved”). No apply or spending authorized. No reviewer was launched.

Forbidden: writes, tests/builds, Terraform/AWS/account/login/console/paid calls, agents, credential/config/cache/state/private-input/raw-plan or raw-JSON/log reads, human approval writes, commits/pushes and Phase13. Public documentation, read-only Git/source/sanitized-log/hash inspection and scratch calculations allowed. Optional opaque binary checksum only; never decode the private plan or recover deleted old artifacts.

Verify:
1. handoff-files.json, evidence-manifest.json, infra/artifact-manifest.json and final-integrity.json reconcile. Preflight 4397 files: only four coordinator records changed append-only; all earlier bytes preserved, review.md/human records/prior packets/source unchanged. No production changes. 209 source hashes/bytes/mtimes match prior approved freeze. Course budget remains disabled. Terraform1.13.5/AWS6.44.0 pins/locks unchanged; seven scratch copies equal source.
2. infra/commands.json has ten records: initial sandbox init0/fmt0/validate1 provider handshake; retry init0/fmt0/validate0/test0; protected init0/plan2/show0. Relevant billing tests7/0, six assertions/four expected-failure runs. No new sbt claimed; historical1255-test/157-fresh-XML and72-test four-root gates clearly historical. Failed lookups and report cleanup disclosed.
3. infra/plan-summary.json proposes only aws_budgets_budget.project[0], 1add/0change/0destroy/0replace. Account530332961125, profile scholarchain-billing-deployer, us-east-2; USD200 COST/CUSTOM, 2026-10-01_00:00 to2027-01-01_00:00 UTC, scholarchain-project-budget, no filters, credit/refund excluded, tags course=CS441/project=scholarchain/environment=course/owner=danny/expiration_date=2027-01-01. Exactly three ACTUAL/GREATER_THAN/PERCENTAGE alerts50/80/100, one private email each, zero SNS.
4. Saved plan /tmp/scholarchain-phase12d-billing-execution-plan/billing.execution.tfplan is6626 bytes, SHA256 35e3591498a3708ff82617ff4ee382f3402bdcf0176a8d4c95e6260913d1cdc5. Inspect public runner/helper and sanitizer allowlist. No recipient/credentials retained in Git; private input never directly inspected/hashed; directory0700/files0600; raw artifacts outside Git. Human retention decision remains open.
5. Earlier user STS result proves intended CLI identity only. Current provider consumed named profile with account guard; resolved provider ARN not independently queried. No independent inventory: fresh local-state absence cannot prove remote budget absence or ownership. Plan is not live create/tag permission, CUSTOM/CostTypes/tag acceptance, active monitor, delivery or refresh-lifetime proof. Bootstrap timing/manual IAM adoption remain open. All EMR/spending/runtime gates and B1/B2/B3/R1/N19/N20 carry forward.

Return APPROVE or REQUEST-CHANGES for this read-only plan only, with severity/path/evidence/owner/acceptance findings, the exact 14 report fields, and a complete next coordinator prompt. Approval must not authorize apply, IAM changes, spending or Phase12D completion. If approved, next prompt records your verdict append-only and prepares a bounded ownership/state and exact-plan apply handoff; obtain the human-written gate before any mutation. Never write the human decision or launch a reviewer. Stop after this review.
'''
(PHASE/'reviewer-prompt-12d-billing-execution-plan.md').write_text(review)
(E/'handoff.md').write_text('''Fresh billing execution-identity plan: COMPLETE for planning; review pending. Nothing applied.

Base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f, branch phase-12. User confirmed all selected inputs and reported private input Saved. Current changes are evidence/reviewer prompt plus four append-only coordinator records; earlier uncommitted work retained. Exact footprint and checksums are in handoff-files.json/evidence-manifest.json.

Result: 1 budget create / 0 changes / 0 destroys / 0 replacements. Plan SHA256 35e3591498a3708ff82617ff4ee382f3402bdcf0176a8d4c95e6260913d1cdc5, 6626 bytes. Ten Terraform commands, including initial sandbox validation failure then successful retry, are recorded exactly in infra/commands.json. Current tests: 7 passed, 0 failed. No source changes or full sbt rerun.

The public summary contains counts, never notification recipient values. Raw plan/JSON/logs and private recipient remain protected outside Git at /tmp/scholarchain-phase12d-billing-execution-plan/. No automatic deletion or retention decision. Standard monitoring/notifications have no service fee under referenced pricing; USD200 is a threshold, not prepaid credit or an enforced cutoff. Account charges and remaining allowance remain unverified.

Provider session consumption worked for planning. Live acceptance/delivery, create/tag rights, remote name/ownership conflict, complete refresh lifetime and all EMR gates remain open. Read-only review is next; any later exact-plan apply needs separate human-written approval and ownership/state handling. No apply, IAM change, paid work, reviewer launch, commit/push or Phase13.\n''')

allowed={str((PHASE/n).relative_to(ROOT)) for n in ['prompt.md','owner-report.md','test-report.md','repairs.md']}
changed=[]; prefixes=[]; unchanged=0
for old in baseline['files']:
    p=ROOT/old['path']; assert p.exists(), old['path']
    assert p.name!='.env' and '.aws' not in p.parts
    cur=info(p)
    if cur!=old:
        assert old['path'] in allowed, ('Unexpected earlier file changed',old['path'])
        b=p.read_bytes(); assert digest(b[:old['bytes']])==old['sha256']
        changed.append(old['path']);prefixes.append({'path':old['path'],'old_bytes':old['bytes'],'old_sha256':old['sha256'],'prefix_preserved':True,'new_bytes':len(b),'new_sha256':digest(b)})
    else: unchanged+=1
assert set(changed)==allowed
write('report-prefix-check.json',{'preflight_prefixes':prefixes,'head_prefixes':[{'path':p,'preserved':(ROOT/p).read_bytes().startswith(git('show','HEAD:'+p))} for p in sorted(allowed)],'review_and_human_records_unchanged':True})
assert all((ROOT/p).read_bytes().startswith(git('show','HEAD:'+p)) for p in allowed)
write('final-integrity.json',{'recorded_utc':NOW,'branch':'phase-12','head':BASE_SHA,'preflight_file_count':4397,'earlier_files_unchanged':unchanged,'earlier_files_changed_append_only':sorted(changed),'earlier_files_removed':[],'production_source_changes':[],'source_reference_files_equal':209,'prior_packets_review_human_records_unchanged':True,'infra_safe_artifacts':31,'infra_manifest_sha256':digest((E/'infra/artifact-manifest.json').read_bytes()),'plan_sha256':PLAN_SHA,'no_apply':True,'reviewer_not_launched':True,'specialist_finished_no_running_jobs':True})
result=subprocess.run(['git','diff','--check'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(E/'diff-check.log.txt').write_bytes(result.stdout);assert result.returncode==0
write('diff-check-result.json',{'argv':['git','diff','--check'],'cwd':str(ROOT),'exit_code':result.returncode,'log':'diff-check.log.txt','log_sha256':digest(result.stdout)})
# Reserve all inventory members before capturing complete Git-visible footprint.
for name in ['handoff-files.json','evidence-manifest.json','final-status.log.txt']:
    (E/name).touch()
status=git('status','--porcelain=v1','--untracked-files=all').decode()
(E/'final-status.log.txt').write_text(status)
allpaths={x.decode() for x in git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if x}
oldpaths={x['path'] for x in baseline['files']}
new=sorted(allpaths-oldpaths)
assert all(p.startswith(str(E.relative_to(ROOT))+'/') or p==str((PHASE/'reviewer-prompt-12d-billing-execution-plan.md').relative_to(ROOT)) for p in new)
write('handoff-files.json',{'branch':'phase-12','head':BASE_SHA,'status_mode':'porcelain=v1 --untracked-files=all','preflight_status_entries':len((E/'preflight-status.log.txt').read_text().splitlines()),'final_status_entries':len(status.splitlines()),'current_work_modified_existing':sorted(changed),'current_work_new':new,'new_file_count':len(new),'earlier_uncommitted_work_retained':True,'all_evidence_files':[str(p.relative_to(E)) for p in sorted(E.rglob('*')) if p.is_file()],'inventory_contains_manifest_and_itself':True})
files=[p for p in sorted(E.rglob('*')) if p.is_file() and p.name!='evidence-manifest.json']
write('evidence-manifest.json',{'recorded_utc':NOW,'excludes_only':'evidence-manifest.json itself','artifact_count':len(files),'files':[{'path':str(p.relative_to(E)),'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size} for p in files]})
print(json.dumps({'complete':True,'evidence_artifacts_plus_manifest':len(files)+1,'new_files':len(new),'changed_existing':len(changed),'earlier_unchanged':unchanged,'status_entries':len(status.splitlines()),'manifest_sha256':digest((E/'evidence-manifest.json').read_bytes())}))

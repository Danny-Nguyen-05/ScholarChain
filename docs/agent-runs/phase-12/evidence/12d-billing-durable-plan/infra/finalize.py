from pathlib import Path
import os,stat,json,hashlib,datetime,subprocess
BASE=Path('/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap')
SAFE=Path('/tmp/scholarchain-phase12d-billing-durable-plan-handoff/safe')
os.umask(0o077)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n');p.chmod(0o600)
plan=json.loads((SAFE/'plan-summary.json').read_text());assert plan['applied']==False
metadata=[]
for name in ['billing.execution.tfplan','billing.execution.plan.json','protected-init.log.txt','real-plan.log.txt','protected-show.log.txt','notification.private.tfvars.json','approved-public-inputs.tfvars.json','run.py','save-recipient.py','toolchain/terraform.tfrc','toolchain/terraform-1.13.5']:
 p=BASE/name;s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_uid==os.getuid()
 expected=0o700 if name in ['run.py','save-recipient.py','toolchain/terraform-1.13.5'] else 0o600
 assert stat.S_IMODE(s.st_mode)==expected
 row={'path':str(p),'mode':oct(expected),'uid':s.st_uid,'symlink':False,'resolved':str(p.resolve())}
 if name=='notification.private.tfvars.json':row.update({'contents_read_or_hashed':False,'size_withheld':True})
 else:row.update({'bytes':s.st_size,'sha256':sha(p)})
 metadata.append(row)
assert not (BASE/'billing.execution.tfstate').exists() and not (BASE/'config/terraform.tfstate').exists()
write(SAFE/'protected-artifact-metadata.json',{'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':metadata,'selected_state_path_exists':False,'default_config_state_path_exists':False,'remote_budget_absence':'not verified; local absence is not account inventory'})
targets=[]
for dirname in ['offline-tf-data','tf-data']:
 for p in (BASE/dirname/'providers').rglob('*'):
  assert p.resolve().is_relative_to(BASE)
  targets.append({'path':str(p),'symlink':p.is_symlink(),'resolved':str(p.resolve()),'mode':oct(stat.S_IMODE(p.lstat().st_mode)),'uid':p.lstat().st_uid})
write(SAFE/'final-provider-targets.json',{'all_targets_within_primary':True,'paths':targets})
write(SAFE/'privacy-and-scope.json',{'applied':False,'cloud_mutation':False,'independent_account_inventory':False,'provider_resolved_caller_arn':'Not independently queried; user supplied fresh sanitized STS via coordinator. Profile chain consumed internally by Terraform.','private_input_read_or_hashed':False,'protected_plan_json_processed_programmatically':True,'private_values_returned_to_model':False,'retention':'State/backups through reviewed teardown and final reconciliation plus human-approved cleanup; plans until superseded and human-approved cleanup. Same-disk backup does not protect disk failure.','backups':'Protected sibling initialized empty; no state exists and no state backup claimed.','old_plan':{'path':'/tmp/scholarchain-phase12d-billing-execution-plan/billing.execution.tfplan','sha256':'35e3591498a3708ff82617ff4ee382f3402bdcf0176a8d4c95e6260913d1cdc5','status':'superseded by fresh durable plan; untouched, not deleted or decoded'},'not_verified':['live create/tag IAM acceptance','CUSTOM/CostTypes/tags service acceptance','active budget','delivery','full OAuth refresh lifetime','remote budget name ownership/absence','G1 human-authored pre-apply confirmation','P3 pre-apply checks'],'no_sbt_rerun':'No repository/source changes; relevant seven current billing tests passed. Prior full build remains historical.'})
commands=json.loads((SAFE/'commands.json').read_text());assert len(commands)==7
for c in commands:assert c['exit_code']==(2 if c['label']=='real-plan' else 0)
report='''STATUS: COMPLETE (fresh durable-path read-only plan only); not apply approval or P2 closure.
OWNER: infra-engineer; native agent /root/infra_12d_durable_plan. No children or reviewers launched.
WORK ORDER: User-invoked NEXT PROMPT in P1 timing/provenance APPROVE attachment 0527b32b-49cc-4d29-85bc-aa63f5a12d5b/Pasted text.txt; coordinator assigned protected durable setup and one fresh read-only billing plan with previously approved public inputs, fresh private recipient and fresh human role-login/STS prerequisite. No repo/source writes.
FILES CREATED: Selected primary and backups directories, durable public config/toolchain/mirror/CLI config, helper/runner, hidden recipient input, protected plan/JSON/logs and curated public scratch handoff. See storage-and-toolchain.json and protected-artifact-metadata.json. Private values are not included in handoff.
FILES MODIFIED: No repository/source/human record or old plan modified. Public runner gained in-process count-only privacy comparison before live execution; unchanged source seven-file copies verified before/offline/after plan.
COMMANDS RUN: Exact seven Terraform argv/environment/cwd/start/end/wall/exit/log hashes are in commands.json: offline init -backend=false -input=false -no-color -lockfile=readonly; fmt -check -recursive; validate -no-color; test -no-color; protected init with same flags; plan -input=false -no-color -detailed-exitcode -lock-timeout=30s with exact durable state/public/private/out paths; protected show -json. All directly used reviewed require_escalated execution for durable writes/provider spawning; no failed sandbox attempt. Setup.py and patch-runner.py were run via python3 -I; public source/metadata reads and finalizer are retained. Initial selected absent-path ls returned 1 with existing parent metadata; no source or live failure.
TEST RESULTS: Current billing tests 7 passed, 0 failed, 6 assertions and 4 expected-failure runs. Init/fmt/validate/test each exit 0. No sbt rerun and no new whole-repository test claim.
VALIDATION RESULTS: Plan exit 2; exactly 1 add, 0 change, 0 destroy, 0 replace for aws_budgets_budget.project[0]. USD 200 COST/CUSTOM 2026-10-01 through 2027-01-01 UTC, account/profile/region exact, credits/refunds excluded, five tags, three ACTUAL alerts 50/80/100, one private email each and zero SNS, no filters. New plan checksum/bytes in plan-summary.json. Public config seven copies match hashes/bytes/source mtimes. Durable provider symlink targets remain within primary; new directories 0700, data 0600 and executables 0700. State absent after plan; does not prove remote absence. Privacy scan count-only and scoped to Git-visible public docs/infra text.
ASSUMPTIONS: Coordinator verifies user fresh role-login and sanitized STS evidence before goahead; exact public inputs unchanged. Physical Application Support paths are outside Git/recognized cloud-sync paths; cannot prove absence of arbitrary third-party backup software. Published Terraform provider lock and reused approved mirror provenance accepted without reinstall or pin change.
RISKS: No live budget/notification delivery proven; CUSTOM/CostTypes/tag/create permissions unverified until separately approved apply/readback. Remote name ownership unknown. Same-disk backups do not protect disk failure; backup directory empty because no state exists. Manual IAM adoption/inventory, refresh lifetime, G1 and P3 remain open. Budget alerts are monitoring, not a spending cutoff.
MANUAL ACTION REQUIRED: User launches independent durable-plan review. Before any apply: resolve G1 in human's own words, complete separately authorized P3 ownership/state checks, and obtain human-written exact-checksum/window approval. Human controls retention/deletion.
BLOCKED-ON OWNER: None for this bounded read-only plan. Human architect and later independent reviewer/deploy-engineer own future gates.
BLOCKED-ON EVIDENCE: None for plan preparation; apply remains blocked on independent durable-plan verdict, G1 confirmation, P3 checks and exact-plan human approval.
NEXT GATE: Coordinator copies only curated safe artifacts, assembles append-only evidence and reviewer prompt, then stops. No live jobs, apply, import, destroy, IAM mutation, paid calls, commits, pushes or Phase 13.
'''
(SAFE/'owner-report.txt').write_text(report)
for name in ['patch-runner.py','finalize.py']:(SAFE/name).write_bytes((SAFE.parent/name).read_bytes())
files=[]
for p in sorted(SAFE.rglob('*')):
 if p.is_file() and p.name!='artifact-manifest.json':
  p.chmod(0o600);files.append({'path':str(p.relative_to(SAFE)),'bytes':p.stat().st_size,'sha256':sha(p)})
write(SAFE/'artifact-manifest.json',{'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'self_excluded':True,'artifact_count':len(files),'files':files})
print(json.dumps({'safe_artifact_count':len(files),'manifest_sha256':sha(SAFE/'artifact-manifest.json'),'plan_sha256':plan['plan_sha256'],'plan_bytes':plan['plan_bytes'],'counts':plan['counts'],'commands':len(commands),'no_state':True,'private_metadata_only':True}))

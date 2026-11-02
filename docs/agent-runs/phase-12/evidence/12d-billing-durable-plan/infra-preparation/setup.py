from pathlib import Path
import os, stat, json, hashlib, shutil, subprocess, datetime
os.umask(0o077)
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
BASE=Path('/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap')
BACK=BASE.with_name('billing-bootstrap-backups')
SAFE=Path('/tmp/scholarchain-phase12d-billing-durable-plan-handoff/safe')
SAFE.mkdir(mode=0o700)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n');p.chmod(0o600)
parents=[]
for p in list(BASE.parents)[::-1]+[BASE,BACK]:
 if p.exists() or p.is_symlink():
  s=p.lstat();assert not p.is_symlink() and stat.S_ISDIR(s.st_mode)
  assert p.resolve()==p
  assert not stat.S_IMODE(s.st_mode)&0o022
  if str(p).startswith('/Users/danny'):assert s.st_uid==os.getuid()
  acl=subprocess.run(['/bin/ls','-ldeO@',str(p)],capture_output=True,text=True,check=True).stdout
  for line in acl.splitlines()[1:]:
   if ': ' in line:assert 'deny delete' in line and 'allow' not in line
  parents.append({'path':str(p),'mode':oct(stat.S_IMODE(s.st_mode)),'uid':s.st_uid,'acl_metadata':acl})
  if p in [BASE,BACK]:raise RuntimeError('Selected target already exists; stop conflict')
 else:p.mkdir(mode=0o700)
assert not any((p/'.git').exists() for p in [BASE]+list(BASE.parents))
assert 'CloudStorage' not in str(BASE.resolve()) and 'Mobile Documents' not in str(BASE.resolve())
dirs=['config/tests','toolchain/provider-mirror/registry.terraform.io/hashicorp/aws/6.44.0/darwin_arm64','tf-data','offline-tf-data']
for d in dirs:(BASE/d).mkdir(mode=0o700,parents=True,exist_ok=True)
for p in BASE.rglob('*'):
 if p.is_dir():p.chmod(0o700)
sources=[]
for rel in ['README.md','main.tf','outputs.tf','variables.tf','versions.tf','tests/budget.tftest.hcl','.terraform.lock.hcl']:
 src=ROOT/'infra/terraform/billing-bootstrap'/rel;dst=BASE/'config'/rel
 shutil.copyfile(src,dst);dst.chmod(0o600)
 sources.append({'source':str(src.relative_to(ROOT)),'copy_relative':str(dst.relative_to(BASE)),'sha256':sha(src),'bytes':src.stat().st_size,'mtime_ns':src.stat().st_mtime_ns,'copy_sha256':sha(dst)})
write(SAFE/'config-provenance-before.json',{'files':sources})
tool=BASE/'toolchain/terraform-1.13.5';old=Path('/tmp/scholarchain-phase12b-repair1-infra/terraform')
assert sha(old)=='899b3c0ca0d2669ebd67be4bcd98e84bd9a914ce2fb3897ad0b86c98cbf3c962'
shutil.copyfile(old,tool);tool.chmod(0o700);assert sha(old)==sha(tool)
mirror=[]
for name in ['terraform-provider-aws_v6.44.0_x5','LICENSE.txt']:
 rel=Path('registry.terraform.io/hashicorp/aws/6.44.0/darwin_arm64')/name
 src=Path('/tmp/scholarchain-phase12b-repair1-infra/mirror')/rel;dst=BASE/'toolchain/provider-mirror'/rel
 assert not src.is_symlink();shutil.copyfile(src,dst);dst.chmod(0o700 if name.startswith('terraform-provider') else 0o600)
 assert sha(src)==sha(dst)
 mirror.append({'path':str(dst),'source':str(src),'sha256':sha(dst),'bytes':dst.stat().st_size,'mode':oct(stat.S_IMODE(dst.stat().st_mode)),'resolved':str(dst.resolve())})
tfrc=BASE/'toolchain/terraform.tfrc'
tfrc.write_text('disable_checkpoint = true\nprovider_installation {\n filesystem_mirror {\n  path = '+json.dumps(str(BASE/'toolchain/provider-mirror'))+'\n  include = ["registry.terraform.io/hashicorp/aws"]\n }\n}\n');tfrc.chmod(0o600)
public=json.loads((ROOT/'docs/agent-runs/phase-12/evidence/12d-billing-execution-plan/infra/approved-public-inputs.json').read_text())
write(BASE/'approved-public-inputs.tfvars.json',public);write(SAFE/'approved-public-inputs.json',public)
helper=(ROOT/'docs/agent-runs/phase-12/evidence/12d-billing-execution-plan/infra/save-recipient.py').read_text().replace('/tmp/scholarchain-phase12d-billing-execution-plan',str(BASE))
(BASE/'save-recipient.py').write_text(helper);(BASE/'save-recipient.py').chmod(0o700)
(SAFE/'save-recipient.py').write_text(helper)
runner=(ROOT/'docs/agent-runs/phase-12/evidence/12d-billing-execution-plan/infra/run.py').read_text()
runner=runner.replace("BASE=Path('/tmp/scholarchain-phase12d-billing-execution-plan')",'BASE=Path('+repr(str(BASE))+')')
runner=runner.replace("SAFE=BASE/'safe';",'SAFE=Path('+repr(str(SAFE))+');')
runner=runner.replace("TF='/tmp/scholarchain-phase12b-repair1-infra/terraform'; TFRC='/tmp/scholarchain-phase12b-repair1-infra/terraformrc'",'TF='+repr(str(tool))+'; TFRC='+repr(str(tfrc)))
runner=runner.replace("BASE/'live-tf-data'","BASE/'tf-data'")
runner=runner.replace("plan_exit=code","plan_exit=code\n assert plan_exit==2")
runner=runner.replace("budget['time_unit']=='CUSTOM'","budget['time_unit']=='CUSTOM' and budget['budget_type']=='COST'")
runner=runner.replace("meta={k:getattr(s,k) for k in ['st_ino','st_dev','st_size','st_mtime_ns']}","meta={k:getattr(s,k) for k in ['st_ino','st_dev','st_mtime_ns']}")
(BASE/'run.py').write_text(runner);(BASE/'run.py').chmod(0o700);(SAFE/'run.py').write_text(runner)
write(SAFE/'storage-and-toolchain.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'primary':str(BASE),'backups':str(BACK),'existing_parent_metadata':parents,'new_dirs_mode':'0700','data_mode':'0600','executables_mode':'0700','terraform_binary':str(tool),'binary_sha256':sha(tool),'terraform_pin':'1.13.5','aws_pin':'6.44.0','lock_sha256':sha(BASE/'config/.terraform.lock.hcl'),'cli_config':str(tfrc),'cli_config_sha256':sha(tfrc),'cli_config_public':tfrc.read_text(),'mirror':mirror,'cloud_sync_assessment':'Physical Application Support path, no symlink or Git ancestor, outside recognized CloudStorage/Mobile Documents/Dropbox/OneDrive paths; no evidence of cloud synchronization. Filesystem metadata cannot rule out arbitrary third-party backup software.','retention':'State and backups through reviewed teardown/final reconciliation and human-approved cleanup; plans through supersession and human-approved cleanup. Same-disk backups do not protect disk failure.','backup_status':'Directory initialized empty. No resource state yet, no state backup claimed.','old_plan':'/tmp/scholarchain-phase12d-billing-execution-plan/billing.execution.tfplan untouched; superseded only after successful fresh plan'})
print(json.dumps({'setup_complete':True,'helper':str(BASE/'save-recipient.py'),'offline_runner':str(BASE/'run.py'),'safe_handoff':str(SAFE)}))

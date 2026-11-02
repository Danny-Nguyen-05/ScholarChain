from pathlib import Path
import os,json,hashlib,subprocess,shutil,datetime,time
repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain'); out=Path('/tmp/scholarchain-phase12d-execution-prep-infra'); src=repo/'infra/terraform/billing-execution'; scratch=out/'red-tree'
def snapshot():
 paths=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z','--','infra/terraform'],cwd=repo).split(b'\0')
 return {os.fsdecode(p):hashlib.sha256((repo/os.fsdecode(p)).read_bytes()).hexdigest() for p in paths if p and (repo/os.fsdecode(p)).is_file()}
before=snapshot()
shutil.copytree(src,scratch,ignore=shutil.ignore_patterns('.terraform','*.tfstate*'))
p=scratch/'main.tf';original=p.read_bytes();text=original.decode();assert text.count('Resource = [local.budget_arn]')==1
p.write_text(text.replace('Resource = [local.budget_arn]','Resource = ["*"]'))
assert (scratch/'tests/policy.tftest.hcl').read_bytes()==(src/'tests/policy.tftest.hcl').read_bytes()
config='/tmp/scholarchain-phase12b-repair1-infra/terraformrc';tf='/tmp/scholarchain-phase12b-repair1-infra/terraform';env=os.environ.copy();env['TF_CLI_CONFIG_FILE']=config
records=json.loads((out/'commands.json').read_text())
for label,args in [('red-init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly']),('red-test',['test','-no-color'])]:
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();r=subprocess.run([tf]+args,cwd=scratch,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=out/(label+'.log.txt');log.write_bytes(r.stdout)
 records.append({'argv':[tf]+args,'cwd':str(scratch),'environment':{'TF_CLI_CONFIG_FILE':config},'started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.monotonic()-t,'exit_code':r.returncode,'log':log.name,'sha256':hashlib.sha256(r.stdout).hexdigest(),'bytes':len(r.stdout)})
 print(label,r.returncode,flush=True)
 assert r.returncode==(0 if label=='red-init' else 1)
 if label=='red-test':
  diagnostic=r.stdout.decode();assert 'Test assertion failed' in diagnostic and 'Allow only the five required Budgets IAM actions' in diagnostic
  assert 'unknown value' not in diagnostic and 'known after apply' not in diagnostic
  print(diagnostic[-2500:])
after=snapshot();assert before==after
(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
(out/'red-proof.json').write_text(json.dumps({'mutation':'Only execution policy Resource [local.budget_arn] changed to ["*"] in scratch main.tf; same new assertions','source_main_sha256':hashlib.sha256(original).hexdigest(),'scratch_main_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'test_sha256':hashlib.sha256((src/'tests/policy.tftest.hcl').read_bytes()).hexdigest(),'repository_before':before,'repository_after':after,'repository_unchanged':before==after},indent=2)+'\n')

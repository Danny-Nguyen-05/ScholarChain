from pathlib import Path
import os,subprocess,hashlib,json,datetime,shutil,re,difflib
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');OUT=Path('/tmp/scholarchain-phase12d-preparation-repair1-infra');TF='/tmp/scholarchain-phase12b-repair1-infra/terraform';ENV={'TF_CLI_CONFIG_FILE':'/tmp/scholarchain-phase12b-repair1-infra/terraformrc'}
os.environ['TF_CLI_CONFIG_FILE']=ENV['TF_CLI_CONFIG_FILE']
paths=[x['path'] for x in json.loads((OUT/'original-source-files.json').read_text())['files']]
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
before=hashes();red=OUT/'red-missing-owner';red.mkdir(exist_ok=True)
for p in paths:
 if p.startswith('infra/terraform/billing-bootstrap/'):
  d=red/Path(p).relative_to('infra/terraform/billing-bootstrap');d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,d)
f=red/'main.tf';s=f.read_text();assert s.count('tags              = local.required_tags')==1
f.write_text(s.replace('tags              = local.required_tags','tags              = { for key, value in local.required_tags : key => value if key != "owner" }'))
records=[]
def run(name,cwd,args):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run([TF]+args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);p=OUT/(name+'.log.txt');p.write_bytes(r.stdout)
 records.append({'argv':[TF]+args,'cwd':str(cwd),'environment':ENV,'started_utc':start,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r.returncode,'log':p.name,'sha256':hashlib.sha256(r.stdout).hexdigest(),'bytes':len(r.stdout)})
 (OUT/'final-commands.json').write_text(json.dumps(records,indent=2)+'\n');print(name,r.returncode,flush=True);return r
assert run('red-missing-owner-init',red,['init','-backend=false','-input=false','-no-color','-lockfile=readonly']).returncode==0
r=run('red-missing-owner-test',red,['test','-no-color']);assert r.returncode==1
text=r.stdout.decode();assert 'Test assertion failed' in text and 'The budget resource must carry all five configured ownership tags' in text
assert 'known after apply' not in text.lower() and 'Unknown condition value' not in text
shutil.copy2(red/'main.tf',OUT/'red-missing-owner-main.tf.txt')
assert before==hashes()
(OUT/'red-proof.json').write_text(json.dumps({'mutation':'only actual budget tags omit owner; inputs and tag assertion unchanged','before':before,'after':hashes(),'repository_unchanged':True,'scratch_main_sha256':hashlib.sha256((red/'main.tf').read_bytes()).hexdigest(),'scratch_test_sha256':hashlib.sha256((red/'tests/budget.tftest.hcl').read_bytes()).hexdigest(),'test_diagnostic':'The budget resource must carry all five configured ownership tags, with expiration tied to its reconciliation end.','result_summary':re.findall(r'Failure!.*',text)},indent=2)+'\n')
for name,rel in [('budget','infra/terraform/billing-bootstrap'),('spike','infra/terraform/spikes/emr-spark'),('course','infra/terraform')]:
 for stage,args in [('init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly']),('fmt-check',['fmt','-check','-recursive']),('validate',['validate','-no-color']),('test',['test','-no-color'])]:
  assert run('final-'+name+'-'+stage,ROOT/rel,args).returncode==0,(name,stage)
# Exact edited-file patch, relative to retained pre-repair copies.
patch=[];current=[]
for p in paths:
 old=(OUT/'original'/p).read_bytes();new=(ROOT/p).read_bytes();stat=(ROOT/p).stat();current.append({'path':p,'sha256':hashlib.sha256(new).hexdigest(),'bytes':len(new),'mtime_ns':stat.st_mtime_ns})
 if old!=new:patch.extend(difflib.unified_diff(old.decode().splitlines(keepends=True),new.decode().splitlines(keepends=True),fromfile='a/'+p,tofile='b/'+p))
(OUT/'delta.patch').write_text(''.join(patch));(OUT/'source-files.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':current},indent=2)+'\n')
counts={}
for name,rel in [('budget','infra/terraform/billing-bootstrap/tests'),('spike','infra/terraform/spikes/emr-spark/tests'),('course','infra/terraform/tests')]:
 texts=[p.read_text() for p in (ROOT/rel).glob('*.tftest.hcl')];counts[name]={k:sum(len(re.findall(pattern,t,re.M)) for t in texts) for k,pattern in [('runs',r'^\s*run\s+"'),('assertions',r'^\s*assert\s*\{'),('expected_failure_runs',r'^\s*expect_failures\s*=')]}
(OUT/'test-counts.json').write_text(json.dumps(counts,indent=2)+'\n')
# Check that original main and both isolated locks still agree.
lock=(ROOT/'infra/terraform/.terraform.lock.hcl').read_bytes();assert all((ROOT/p).read_bytes()==lock for p in paths if p.endswith('.terraform.lock.hcl'))
print(json.dumps(counts,indent=2),flush=True)

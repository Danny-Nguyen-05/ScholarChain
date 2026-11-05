import os,subprocess,json,hashlib,time,datetime,pathlib
out=pathlib.Path('/tmp/scholarchain-phase12d-execution-prep-infra');repo=pathlib.Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
tf='/tmp/scholarchain-phase12b-repair1-infra/terraform'; config='/tmp/scholarchain-phase12b-repair1-infra/terraformrc'
env=os.environ.copy();env['TF_CLI_CONFIG_FILE']=config
records=[]
for label,root in [('course','infra/terraform'),('billing','infra/terraform/billing-bootstrap'),('proposal','infra/terraform/spikes/emr-spark'),('execution','infra/terraform/billing-execution')]:
 for stage,args in [('init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly']),('fmt',['fmt','-check','-recursive']),('validate',['validate','-no-color']),('test',['test','-no-color'])]:
  start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
  p=subprocess.run([tf]+args,cwd=repo/root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  path=out/f'{label}-{stage}.log.txt';path.write_bytes(p.stdout)
  record={'argv':[tf]+args,'cwd':str(repo/root),'environment':{'TF_CLI_CONFIG_FILE':config},'started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.monotonic()-t,'exit_code':p.returncode,'log':path.name,'sha256':hashlib.sha256(p.stdout).hexdigest(),'bytes':len(p.stdout)};records.append(record)
  (out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
  print(label,stage,p.returncode,flush=True)
  if p.returncode:
   print(p.stdout.decode()[-8000:]);raise SystemExit(1)

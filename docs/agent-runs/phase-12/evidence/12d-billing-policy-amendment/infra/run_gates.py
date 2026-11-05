from pathlib import Path
import subprocess,json,datetime,time,hashlib
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');OUT=Path('/tmp/scholarchain-phase12d-policy-amendment-infra');TF='/tmp/scholarchain-phase12b-repair1-infra/terraform'
ENV={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','LANG':'C','TF_CLI_CONFIG_FILE':'/tmp/scholarchain-phase12b-repair1-infra/terraformrc','AWS_EC2_METADATA_DISABLED':'true','AWS_CONFIG_FILE':'/dev/null','AWS_SHARED_CREDENTIALS_FILE':'/dev/null'}
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
def run(label,argv,cwd):
 log=OUT/(label+'.log.txt');started=stamp();t=time.monotonic()
 p=subprocess.run(argv,cwd=cwd,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log.write_bytes(p.stdout)
 records.append({'label':label,'argv':argv,'cwd':str(cwd),'environment':ENV,'started_utc':started,'ended_utc':stamp(),'wall_seconds':round(time.monotonic()-t,6),'exit_code':p.returncode,'log':log.name,'bytes':len(p.stdout),'sha256':sha(log)})
 (OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(label,p.returncode,flush=True)
 return p.returncode
assert sha(Path(TF))=='899b3c0ca0d2669ebd67be4bcd98e84bd9a914ce2fb3897ad0b86c98cbf3c962'
# Development formatting is retained separately from every final check-only gate.
assert run('development-format',[TF,'fmt','-recursive'],ROOT/'infra/terraform/billing-execution')==0
roots={'course':ROOT/'infra/terraform','billing':ROOT/'infra/terraform/billing-bootstrap','proposal':ROOT/'infra/terraform/spikes/emr-spark','execution':ROOT/'infra/terraform/billing-execution'}
for label,cwd in roots.items():
 for suffix,args in [('init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly']),('fmt-check',['fmt','-check','-recursive']),('validate',['validate','-no-color']),('test',['test','-no-color'])]:
  code=run(label+'-'+suffix,[TF]+args,cwd)
  if code:raise SystemExit(code)
print('ALL FOUR ROOT GATES PASSED',flush=True)

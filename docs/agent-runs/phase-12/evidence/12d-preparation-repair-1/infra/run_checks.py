import subprocess,json,hashlib,datetime,os
from pathlib import Path
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
OUT=Path('/tmp/scholarchain-phase12d-preparation-repair1-infra')
TF='/tmp/scholarchain-phase12b-repair1-infra/terraform'
ENV={'TF_CLI_CONFIG_FILE':'/tmp/scholarchain-phase12b-repair1-infra/terraformrc'}
os.environ['TF_CLI_CONFIG_FILE']=ENV['TF_CLI_CONFIG_FILE']
records=[]
for name,rel in [('budget','infra/terraform/billing-bootstrap'),('spike','infra/terraform/spikes/emr-spark')]:
 for stage,args in [('init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly']),('fmt',['fmt','-recursive']),('fmt-check',['fmt','-check','-recursive']),('validate',['validate','-no-color']),('test',['test','-no-color'])]:
  start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run([TF]+args,cwd=ROOT/rel,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  p=OUT/f'development-{name}-{stage}.log.txt';p.write_bytes(r.stdout)
  records.append({'argv':[TF]+args,'cwd':str(ROOT/rel),'environment':ENV,'started_utc':start,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r.returncode,'log':p.name,'sha256':hashlib.sha256(r.stdout).hexdigest(),'bytes':len(r.stdout)})
  print(name,stage,r.returncode, r.stdout.decode(errors='replace')[-900:])
(OUT/'development-commands.json').write_text(json.dumps(records,indent=2)+'\n')
raise SystemExit(any(r['exit_code'] for r in records))

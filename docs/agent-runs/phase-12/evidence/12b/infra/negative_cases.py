from pathlib import Path
import json,shutil,subprocess,hashlib,datetime,difflib,os
repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain'); source=repo/'infra/terraform';scratch=Path('/tmp/scholarchain-phase12b-infra');runner=scratch/'run.py';tf='/tmp/scholarchain-phase12a-infra-toolchain/terraform'
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--','infra/terraform'],cwd=repo,text=True).splitlines()
def snapshot():return {p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in paths}
before=snapshot();results=[]
env=dict(os.environ,TF_CLI_CONFIG_FILE=str(scratch/'terraformrc'))
cases=[('graph-write','modules/identity/phase12b.tf','"neptune-db:ReadDataViaQuery"','"neptune-db:WriteDataViaQuery"','The graph role must have only explicit read/query-control access'),('public-neptune','modules/neptune/main.tf','publicly_accessible          = false','publicly_accessible          = true','Neptune must be private'),('flatten-dashboard','modules/observability/main.tf','concat([for service in local.services : [for metric in ["DesiredTaskCount", "RunningTaskCount", "PendingTaskCount"] : ["ECS/ContainerInsights", metric, "ClusterName", var.name_prefix, "ServiceName", service]]]...)','flatten([for service in local.services : [for metric in ["DesiredTaskCount", "RunningTaskCount", "PendingTaskCount"] : ["ECS/ContainerInsights", metric, "ClusterName", var.name_prefix, "ServiceName", service]]])','CloudWatch metrics must be arrays')]
for name,rel,old,new,diagnostic in cases:
 dest=scratch/('mutation-v2-'+name)
 if dest.exists():raise RuntimeError('Never overwrite retained negative run '+str(dest))
 shutil.copytree(source,dest,ignore=shutil.ignore_patterns('.terraform','*.tfstate','*.tfstate.*','*.tfplan'))
 p=dest/rel;original=p.read_text()
 # Format alignment is irrelevant to the semantic mutation.
 if name=='public-neptune':
  import re
  updated,count=re.subn(r'(publicly_accessible\s*= )false',r'\1true',original)
  if count!=1:raise RuntimeError('public mutation must change exactly one literal')
 else:
  if original.count(old)!=1:raise RuntimeError(name+' mutation token missing or ambiguous')
  updated=original.replace(old,new)
 p.write_text(updated);(scratch/('mutation-v2-'+name+'.patch')).write_text(''.join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 init=subprocess.run(['python3',str(runner),'mutation-v2-'+name+'-init',tf,'init','-backend=false','-input=false','-no-color'],cwd=dest,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 test=subprocess.run(['python3',str(runner),'mutation-v2-'+name+'-test',tf,'test','-no-color'],cwd=dest,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 text=test.stdout.decode();normalized=' '.join(text.split())
 ok=init.returncode==0 and test.returncode==1 and diagnostic in normalized and 'Test assertion failed' in text
 result={'name':name,'cwd':str(dest),'changed_file':rel,'init_exit':init.returncode,'test_exit':test.returncode,'expected_diagnostic':diagnostic,'matched':ok,'repository_source_unchanged':snapshot()==before}
 results.append(result);print(json.dumps(result),flush=True)
 if not ok:
  (scratch/'negative-results-v2.json').write_text(json.dumps(results,indent=2)+'\n');raise RuntimeError('Negative case did not prove intended assertion: '+name)
(scratch/'negative-results-v2.json').write_text(json.dumps(results,indent=2)+'\n')
(scratch/'mutation-source-unchanged.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before':before,'after':snapshot(),'equal':before==snapshot()},indent=2)+'\n')

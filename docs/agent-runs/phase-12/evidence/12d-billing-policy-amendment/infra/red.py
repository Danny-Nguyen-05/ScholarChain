from pathlib import Path
import subprocess,json,hashlib,datetime,time,shutil,re
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');OUT=Path('/tmp/scholarchain-phase12d-policy-amendment-infra');TF='/tmp/scholarchain-phase12b-repair1-infra/terraform';SRC=ROOT/'infra/terraform/billing-execution';RED=OUT/'red-tree'
ENV={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','LANG':'C','TF_CLI_CONFIG_FILE':'/tmp/scholarchain-phase12b-repair1-infra/terraformrc','AWS_EC2_METADATA_DISABLED':'true','AWS_CONFIG_FILE':'/dev/null','AWS_SHARED_CREDENTIALS_FILE':'/dev/null'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def snapshot():
 names=set(subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0'))-{''}
 return {x:sha(ROOT/x) for x in sorted(names) if x.startswith('infra/terraform/') and (ROOT/x).is_file()}
def run(label,args,cwd):
 path=OUT/(label+'.log.txt');start=stamp();t=time.monotonic();p=subprocess.run([TF]+args,cwd=cwd,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);path.write_bytes(p.stdout)
 rows=json.loads((OUT/'commands.json').read_text());rows.append({'label':label,'argv':[TF]+args,'cwd':str(cwd),'environment':ENV,'started_utc':start,'ended_utc':stamp(),'wall_seconds':round(time.monotonic()-t,6),'exit_code':p.returncode,'log':path.name,'bytes':len(p.stdout),'sha256':sha(path)});(OUT/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');return p.returncode
before=snapshot();RED.mkdir(exist_ok=True)
for rel in ['.terraform.lock.hcl','versions.tf','variables.tf','main.tf','README.md','tests/policy.tftest.hcl']:
 p=RED/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/rel,p)
main=RED/'main.tf';s=main.read_text();needle=':oauth2/public-client/localhost';assert s.count(needle)==1;main.write_text(s.replace(needle,':oauth2/public-client/*'))
(OUT/'red-main.tf.txt').write_bytes(main.read_bytes());(OUT/'red-policy.tftest.hcl.txt').write_bytes((RED/'tests/policy.tftest.hcl').read_bytes());assert sha(SRC/'tests/policy.tftest.hcl')==sha(RED/'tests/policy.tftest.hcl')
assert run('red-login-init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly'],RED)==0
code=run('red-login-test',['test','-no-color'],RED);assert code==1
text=(OUT/'red-login-test.log.txt').read_text();assert 'Test assertion failed' in text and not re.search('known after apply|unknown value',text,re.I)
assert 'login_policy_is_exact_same_device_only' in text
result={'mutation':'Scratch main.tf login Resource suffix localhost widened to *; no other source mutation','source_main_sha256':sha(SRC/'main.tf'),'scratch_main_sha256':sha(main),'source_test_sha256':sha(SRC/'tests/policy.tftest.hcl'),'scratch_test_sha256':sha(RED/'tests/policy.tftest.hcl'),'init_exit':0,'test_exit':code,'test_result':re.findall(r'Failure!.*',text)[-1],'assertion_lines':re.findall(r'on tests/policy.tftest.hcl line (\d+)',text),'repository_before':before,'repository_after':snapshot()};result['repository_unchanged']=result['repository_before']==result['repository_after'];assert result['repository_unchanged'];(OUT/'red-proof.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('repository_before','repository_after')})
# Independent E1 guard regression: restore only the old case-sensitive comparison.
E=OUT/'red-e1-tree';E.mkdir(exist_ok=True)
for rel in ['.terraform.lock.hcl','versions.tf','variables.tf','main.tf','README.md','tests/policy.tftest.hcl']:
 p=E/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/rel,p)
p=E/'variables.tf';s=p.read_text();needle='endswith(lower(var.operator_user_arn),';assert s.count(needle)==1;p.write_text(s.replace(needle,'endswith(var.operator_user_arn,'));(OUT/'red-e1-variables.tf.txt').write_bytes(p.read_bytes())
assert run('red-e1-init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly'],E)==0
code=run('red-e1-test',['test','-no-color'],E);assert code==1;text=(OUT/'red-e1-test.log.txt').read_text();assert 'Missing expected failure' in text and 'mixed_case_planner_cannot_be_operator' in text
result={'mutation':'Scratch variables.tf restores old case-sensitive planner guard only','source_variables_sha256':sha(SRC/'variables.tf'),'scratch_variables_sha256':sha(p),'source_test_sha256':sha(SRC/'tests/policy.tftest.hcl'),'scratch_test_sha256':sha(E/'tests/policy.tftest.hcl'),'init_exit':0,'test_exit':code,'test_result':re.findall(r'Failure!.*',text)[-1],'diagnostic':'Missing expected failure in the mixed-case planner run; subsequent runs may be skipped by Terraform','repository_before':before,'repository_after':snapshot()};result['repository_unchanged']=result['repository_before']==result['repository_after'];assert result['repository_unchanged'];(OUT/'red-e1-proof.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('repository_before','repository_after')})

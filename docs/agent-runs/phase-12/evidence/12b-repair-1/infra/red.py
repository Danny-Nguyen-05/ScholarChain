from pathlib import Path
import subprocess,hashlib,shutil,json,datetime,os
repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');r=Path('/tmp/scholarchain-phase12b-repair1-infra');dest=r/'red-pre-fix'
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--','infra/terraform'],cwd=repo,text=True).splitlines()
def hashes():return {p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in paths}
before=hashes();shutil.copytree(repo/'infra/terraform',dest,ignore=shutil.ignore_patterns('.terraform','*.tfstate','*.tfstate.*','*.tfplan'))
# Only new test is in place; this scratch policy is the unmodified reviewed12B pre-fix source.
assert (dest/'modules/identity/main.tf').read_bytes()==(r/'pre-repair-copies/modules/identity/main.tf').read_bytes()
env=dict(os.environ,TF_CLI_CONFIG_FILE=str(r/'terraformrc'));tf=str(r/'terraform');runner=str(r/'run.py')
a=subprocess.run(['python3',runner,'b3-red-init',tf,'init','-backend=false','-input=false','-no-color'],cwd=dest,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
b=subprocess.run(['python3',runner,'b3-red-test',tf,'test','-no-color'],cwd=dest,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
log=b.stdout.decode();normalized=' '.join(log.split());ok=a.returncode==0 and b.returncode==1 and 'Test assertion failed' in log and 'B3: The project CMK must allow exactly one S3 Vectors indexing service' in normalized and 'known after apply' not in log and hashes()==before
result={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scratch':str(dest),'init_exit':a.returncode,'test_exit':b.returncode,'intended_assertion_failed':ok,'new_assertion_against_pre_fix_policy':True,'repository_before':before,'repository_after':hashes(),'repository_unchanged':before==hashes(),'test_summary':[x for x in log.splitlines() if x.startswith('Failure!') or x.startswith('Success!')]}
(r/'red-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['repository_before','repository_after']}));assert ok

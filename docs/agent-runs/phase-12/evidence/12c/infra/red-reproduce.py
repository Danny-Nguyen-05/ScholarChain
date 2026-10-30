#!/usr/bin/env python3
"""Reproduce the mock-only pre-fix failure without modifying repository files."""
from pathlib import Path
import subprocess, shutil, tempfile, hashlib, json
root=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
base='3b0855b9657a72b30e8ac43bd484161a9b886c79'
tf='/tmp/scholarchain-phase12b-repair1-infra/terraform'
cli='/tmp/scholarchain-phase12b-repair1-infra/terraformrc'
paths=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard','--','infra/terraform'],cwd=root).decode().split('\0')
def snapshot():return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths if p and (root/p).is_file()}
before=snapshot(); scratch=Path(tempfile.mkdtemp(prefix='scholarchain12c-red-reproduce-'))
shutil.copytree(root/'infra/terraform',scratch,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.terraform','*.local.tfvars','*.tfstate*','*.tfplan','*.plan.json'))
originals={}
for rel in ['modules/identity/main.tf','modules/identity/phase12b.tf','phase12b-variables.tf','modules/workflow/main.tf','modules/observability/main.tf']:
    content=subprocess.check_output(['git','show',base+':infra/terraform/'+rel],cwd=root)
    (scratch/rel).write_bytes(content); originals[rel]=hashlib.sha256(content).hexdigest()
results=[]
for name,args in [('init',['init','-backend=false','-input=false','-no-color']),('test',['test','-no-color','-filter=tests/phase12c.tftest.hcl'])]:
    command=['env','TF_CLI_CONFIG_FILE='+cli,tf]+args
    r=subprocess.run(command,cwd=scratch,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=scratch/(name+'.log.txt'); log.write_bytes(r.stdout)
    results.append({'command':command,'cwd':str(scratch),'exit':r.returncode,'log':str(log),'sha256':hashlib.sha256(r.stdout).hexdigest()})
assert before==snapshot(),'Repository changed during scratch run'
assert results[0]['exit']==0 and results[1]['exit']==1,results
print(json.dumps({'original_production_hashes':originals,'repository_unchanged':True,'results':results},indent=2))

from pathlib import Path
import subprocess,json,hashlib
cwd=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform'); binary='/tmp/scholarchain-phase12a-infra-toolchain/terraform';prefix='/tmp/scholarchain-phase12a-repair1-infra-'
commands=[('init-final',['init','-backend=false','-input=false','-no-color']),('fmt-final',['fmt','-check','-recursive']),('validate-final',['validate','-no-color']),('test-final',['test','-no-color'])]
records=[]
for label,args in commands:
 result=subprocess.run([binary]+args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 log=Path(prefix+label+'.log');log.write_text(result.stdout)
 records.append({'label':label,'command':[binary]+args,'cwd':str(cwd),'exit_code':result.returncode,'log':str(log),'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
 Path(prefix+'final-command-results.json').write_text(json.dumps(records,indent=2))
 print(label,'exit',result.returncode,flush=True)
 assert result.returncode==0
 if label=='test-final':assert 'Success! 13 passed, 0 failed.' in result.stdout

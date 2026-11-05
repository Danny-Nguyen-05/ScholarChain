from pathlib import Path
import subprocess,json,sys,hashlib,time,datetime,os
r=Path('/tmp/scholarchain-phase12b-repair1-infra');name=sys.argv[1];cmd=sys.argv[2:];t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);p=r/(name+'.log.txt');p.write_bytes(result.stdout)
f=r/'command-manifest.json';m=json.loads(f.read_text()) if f.exists() else [];m.append({'name':name,'cwd':str(Path.cwd()),'command':cmd,'TF_CLI_CONFIG_FILE':os.environ.get('TF_CLI_CONFIG_FILE'),'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':result.returncode,'wall_seconds':time.monotonic()-t,'log':str(p),'sha256':hashlib.sha256(result.stdout).hexdigest(),'bytes':len(result.stdout)});f.write_text(json.dumps(m,indent=2)+'\n');sys.stdout.buffer.write(result.stdout);sys.exit(result.returncode)

import subprocess,sys,json,time,hashlib,pathlib,datetime,os
root=pathlib.Path('/tmp/scholarchain-phase12b-infra'); manifest=root/'commands.json'
name=sys.argv[1];cmd=sys.argv[2:];start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
p=root/(name+'.log');p.write_bytes(r.stdout)
m=json.loads(manifest.read_text()) if manifest.exists() else []
m.append(dict(environment={"TF_CLI_CONFIG_FILE":os.environ.get("TF_CLI_CONFIG_FILE")},name=name,cwd=str(pathlib.Path.cwd()),command=cmd,start=start,end=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-t,exit_code=r.returncode,log=str(p),sha256=hashlib.sha256(r.stdout).hexdigest(),bytes=len(r.stdout)));manifest.write_text(json.dumps(m,indent=2)+'\n')
sys.stdout.buffer.write(r.stdout);sys.exit(r.returncode)

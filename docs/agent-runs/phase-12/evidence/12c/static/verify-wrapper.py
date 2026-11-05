from pathlib import Path
from datetime import datetime, timezone
import subprocess,time,hashlib,json,sys
root=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
e=Path('/tmp/scholarchain-phase12c-test')
command=['/bin/zsh','-c', 'set -e\nexport JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home\nexport PATH="$JAVA_HOME/bin:$PATH"\nexport SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"\njava -version\nsbt -batch "independentTests/Test/scalafmt" "independentTests/testOnly edu.uic.cs441.scholarchain.independent.IndependentTerraformSourceSpec"']
start=datetime.now(timezone.utc).isoformat();t=time.monotonic()
with (e/'wrapper-verification.log.txt').open('wb') as log:
 r=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
b=(e/'wrapper-verification.log.txt').read_bytes()
record={'name':'wrapper-verification','argv':command,'cwd':str(root),'start_utc':start,'end_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':round(time.monotonic()-t,3),'exit_code':r.returncode,'log':str(e/'wrapper-verification.log.txt'),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
m=json.loads((e/'commands.json').read_text());m.append(record);(e/'commands.json').write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps(record))
print(b.decode(errors='replace')[-7000:])
sys.exit(r.returncode)

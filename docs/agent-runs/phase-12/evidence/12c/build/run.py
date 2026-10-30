from pathlib import Path
from datetime import datetime, timezone
import subprocess, json, hashlib, time, gzip, re, os
import xml.etree.ElementTree as ET
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
OUT=Path('/tmp/scholarchain-phase12c-build')
FREEZE=ROOT/'docs/agent-runs/phase-12/evidence/12c/source-freeze.json'
EXPECTED='9f61ad19c6bff130e2d110fb69ca682497ec4b2a8674c5e84f58645f49db583b'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
def save(name,v): (OUT/name).write_text(json.dumps(v,indent=2)+'\n')
def visible():
    r=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT)
    paths=sorted(set(filter(None,r.decode().split('\0'))))
    return [p for p in paths if not p.startswith('docs/agent-runs/phase-12/') and '.env' not in Path(p).parts and not any(x.lower() in ('secrets','credentials','private-keys') for x in Path(p).parts)]
def snapshot():
    result=[]
    for name in visible():
        p=ROOT/name
        if p.is_file():
            b=p.read_bytes(); st=p.stat()
            result.append({'path':name,'sha256':sha(b),'bytes':len(b),'mtime_ns':st.st_mtime_ns})
    return result
freeze_bytes=FREEZE.read_bytes(); assert sha(freeze_bytes)==EXPECTED
freeze=json.loads(freeze_bytes)
def freeze_check():
    mismatches=[]
    for f in freeze['files']:
        p=ROOT/f['path']
        if not p.is_file(): mismatches.append({'path':f['path'],'reason':'missing'});continue
        b=p.read_bytes(); st=p.stat()
        if (sha(b),len(b),st.st_mtime_ns)!=(f['sha256'],f['bytes'],f['mtime_ns']): mismatches.append({'path':f['path'],'reason':'hash/bytes/mtime'})
    return mismatches
assert not freeze_check()
before=snapshot(); save('source-before.json',{'timestamp_utc':now(),'scope':'All Git-visible files except active phase-12 coordinator records/evidence and forbidden credential/secret path classes. This is a conservative superset of Scala/build/resources plus all infra/tests inputs.','files':before})
start=now(); start_ns=time.time_ns(); wall=time.monotonic()
assert datetime.fromisoformat(start)>datetime.fromisoformat(freeze['timestamp_utc'])
commands=[]
save('build-start.json',{'started_utc':start,'started_ns':start_ns,'cwd':str(ROOT),'base_sha':'3b0855b9657a72b30e8ac43bd484161a9b886c79','freeze_path':str(FREEZE),'freeze_sha256':EXPECTED,'freeze_timestamp':freeze['timestamp_utc'],'snapshot_files':len(before),'runner_pid':os.getpid(),'java_home':'/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home','sbt_opts':'-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml'})
print(json.dumps({'state':'started','started_utc':start,'snapshot_files':len(before),'freeze_sha256':EXPECTED}),flush=True)
prefix='export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home\nexport PATH="$JAVA_HOME/bin:$PATH"\nexport SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"\n'
java_start=now();t=time.monotonic()
java=subprocess.run(['/bin/zsh','-c',prefix+'java -version'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(OUT/'java-version.log.txt').write_bytes(java.stdout)
commands.append({'command':'java -version','cwd':str(ROOT),'environment_setup':prefix,'started_utc':java_start,'finished_utc':now(),'exit_code':java.returncode,'wall_seconds':time.monotonic()-t,'log':'java-version.log.txt','sha256':sha(java.stdout)})
assert java.returncode==0
sbt_start=now();t=time.monotonic()
with (OUT/'sbt-check.log.txt').open('wb') as log:
    proc=subprocess.Popen(['/bin/zsh','-c',prefix+'sbt -batch check'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    save('process.json',{'runner_pid':os.getpid(),'sbt_shell_pid':proc.pid,'started_utc':sbt_start,'log':'sbt-check.log.txt'})
    result=proc.wait()
sbt_wall=time.monotonic()-t; finish=now(); finish_ns=time.time_ns()
raw=(OUT/'sbt-check.log.txt').read_bytes()
with (OUT/'sbt-check.log.gz').open('wb') as f:
    with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as gz:gz.write(raw)
commands.append({'command':'sbt -batch check','cwd':str(ROOT),'environment_setup':prefix,'started_utc':sbt_start,'finished_utc':finish,'exit_code':result,'wall_seconds':sbt_wall,'log':'sbt-check.log.txt','sha256':sha(raw),'compressed_log':'sbt-check.log.gz','compressed_sha256':sha((OUT/'sbt-check.log.gz').read_bytes())})
save('commands.json',commands)
after=snapshot(); save('source-after.json',{'timestamp_utc':now(),'files':after})
before_map={f['path']:f for f in before};after_map={f['path']:f for f in after}
changes=[{'path':p,'before':before_map.get(p),'after':after_map.get(p)} for p in sorted(before_map.keys()|after_map.keys()) if before_map.get(p)!=after_map.get(p)]
xmls=[];totals={'tests':0,'failures':0,'errors':0,'skipped':0}
for parent in (ROOT/'modules',ROOT/'tests',ROOT/'target'):
    if not parent.exists():continue
    for p in parent.rglob('TEST-*.xml'):
        if 'test-reports' not in p.parts: continue
        tree=ET.parse(p).getroot();nodes=[tree] if tree.tag=='testsuite' else list(tree.findall('testsuite'))
        counts={key:sum(int(x.attrib.get(key,'0')) for x in nodes) for key in totals}
        st=p.stat();fresh=start_ns<=st.st_mtime_ns<=finish_ns
        b=p.read_bytes();xmls.append({'path':str(p.relative_to(ROOT)),'mtime_ns':st.st_mtime_ns,'fresh':fresh,'sha256':sha(b),**counts})
        for k,v in counts.items():totals[k]+=v
xmls.sort(key=lambda x:x['path'])
validation={'started_utc':start,'sbt_started_utc':sbt_start,'finished_utc':finish,'exit_code':result,'wall_seconds':time.monotonic()-wall,'sbt_wall_seconds':sbt_wall,'snapshot_files':len(before),'source_changes':changes,'freeze_mismatches_after':freeze_check(),'xml_report_count':len(xmls),'fresh_xml_count':sum(x['fresh'] for x in xmls),'xml_totals':totals,'xml_reports':xmls,'sbt_total_time_lines':re.findall(r'^.*Total time:.*$',raw.decode(errors='replace'),re.M),'expected_probe_present':b'checkProbeInjectFailure' in raw,'error_lines':[x for x in raw.decode(errors='replace').splitlines() if '[error]' in x],'raw_log_bytes':len(raw),'raw_log_sha256':sha(raw),'compressed_log_bytes':(OUT/'sbt-check.log.gz').stat().st_size,'compressed_log_sha256':sha((OUT/'sbt-check.log.gz').read_bytes()),'decompressed_hash_matches':sha(gzip.decompress((OUT/'sbt-check.log.gz').read_bytes()))==sha(raw),'java_version':java.stdout.decode(errors='replace')}
save('build-result.json',validation)
print(json.dumps({k:v for k,v in validation.items() if k not in ('xml_reports','error_lines')}),flush=True)

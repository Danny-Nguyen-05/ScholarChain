from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, signal, subprocess, time
from urllib.parse import unquote, urlparse

os.umask(0o077)
repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
work=repo/'target/phase12d-readiness-20261103'
build=Path('/private/tmp/scholarchain-phase12d-spark-build-runtime-20261103')
java_home='/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'
java=java_home+'/bin/java'
plan=json.loads((work/'input-generation-plan.json').read_text())
env={'HOME':'/Users/danny','USER':'danny','LOGNAME':'danny','PATH':java_home+'/bin:/usr/bin:/bin','JAVA_HOME':java_home,'TMPDIR':'/private/tmp','LANG':'en_US.UTF-8','SPARK_LOCAL_IP':'127.0.0.1','SPARK_LOCAL_HOSTNAME':'127.0.0.1','AWS_EC2_METADATA_DISABLED':'true'}
def enc(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def save(path,value):
    with path.open('xb') as out:out.write(enc(value));out.flush();os.fsync(out.fileno())
def run(stage,classpath,args):
    cp=classpath.read_text().strip()
    assert cp and all(Path(p).is_absolute() and Path(p).exists() for p in cp.split(':'))
    argv=[java,'-Xmx1g','-Djava.net.preferIPv4Stack=true','-cp',cp,*args]
    started=time.monotonic()
    save(work/'logs'/f'{stage}-command.json',{'argv':argv,'environment':env,'started_at':datetime.now(timezone.utc).isoformat(),'timeout_seconds':180})
    with (work/'logs'/f'{stage}.stdout.txt').open('xb') as out,(work/'logs'/f'{stage}.stderr.txt').open('xb') as err:
        p=subprocess.Popen(argv,cwd=repo,env=env,stdout=out,stderr=err,start_new_session=True)
        expired=False;forced=False
        try:code=p.wait(timeout=180)
        except subprocess.TimeoutExpired:
            expired=True;os.killpg(p.pid,signal.SIGINT)
            try:code=p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGTERM)
                try:code=p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    forced=True;os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=5)
    result={'exit':code,'timed_out':expired,'forced_group_kill':forced,'wall_seconds':round(time.monotonic()-started,3),'completed_at':datetime.now(timezone.utc).isoformat()}
    save(work/'logs'/f'{stage}-result.json',result)
    print(json.dumps({'stage':stage,**result}),flush=True)
    assert code==0 and not expired

assert not (work/'upstream/hadoop').exists() and not (work/'upstream/er').exists()
run('hadoop',build/'hadoop-compile-classpath.txt',[plan['hadoop_main'],*plan['hadoop_args']])
lines=(work/'logs/hadoop.stdout.txt').read_text().splitlines()
locations=[x.split('=',1)[1] for x in lines if x.startswith('runDirectory=')]
assert len(locations)==1
uri=urlparse(locations[0]);assert uri.scheme in ('file','')
hadoop=Path(unquote(uri.path) if uri.scheme else locations[0]).resolve()
assert hadoop.is_relative_to(work/'upstream/hadoop')
marker=json.loads((hadoop/'_SCHOLARCHAIN_COMPLETE').read_text());manifest=json.loads((hadoop/'run-manifest.json').read_text())
assert marker['complete'] is True and marker['runId']==manifest['runId']==plan['requested_run_id']
er=work/'upstream/er'
run('er',build/'er-compile-classpath.txt',['edu.uic.cs441.scholarchain.entityresolution.Phase5Main','resolve','--input',str(hadoop),'--policy',str(repo/'modules/entity-resolution/src/main/resources/phase5-policy.v1.json'),'--config',str(repo/'modules/entity-resolution/src/main/resources/phase5-config.v1.json'),'--llm-mode','disabled','--output',str(er)])
er_manifest=(er/'resolution-manifest.json').read_bytes()
assert (er/'_SCHOLARCHAIN_RESOLUTION_COMPLETE').read_text()==hashlib.sha256(er_manifest).hexdigest()+'\n'
em=json.loads(er_manifest);assert em['complete'] is True
result={'kind':'Observed genuine local upstream production using synthetic fixture','hadoop_root':str(hadoop),'hadoop_run_id':manifest['runId'],'hadoop_manifest_sha256':hashlib.sha256((hadoop/'run-manifest.json').read_bytes()).hexdigest(),'er_root':str(er),'er_run_id':em['runId'],'er_manifest_sha256':hashlib.sha256(er_manifest).hexdigest(),'ER_mode':'disabled','Hadoop_exit':0,'ER_exit':0,'synthetic':True,'AWS_calls':0,'completion_markers_generated_by_unchanged_pipelines':True}
save(work/'upstream-result.json',result)
print(json.dumps(result,sort_keys=True),flush=True)

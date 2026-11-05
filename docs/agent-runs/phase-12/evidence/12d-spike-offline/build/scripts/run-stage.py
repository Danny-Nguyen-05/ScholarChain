"""Run one spike stage. usage: run-stage.py <name> <stage:probe|pipeline|compare> <security:v2|v1|none> [--classload] [--exec-mem 512m]
Secret is generated per run, passed only via env _SPARK_AUTH_SECRET, never recorded."""
import os,sys,json,subprocess,time,signal,hashlib,gzip,secrets,shutil,glob
from pathlib import Path
from datetime import datetime,timezone
base=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase12d-spike-offline')
repo=base.parents[1]
name,stage,sec=sys.argv[1:4];flags=sys.argv[4:]
classload='--classload' in flags
execmem=flags[flags.index('--exec-mem')+1] if '--exec-mem' in flags else '512m'
assert stage in('probe','pipeline','compare') and (sec in('v2','v1','none') or sec.startswith('file:'))
ex=base/'run/ex1';spark=ex/'scholarchain-runtime';job=spark/'application/scholarchain-job.jar'
rd=base/'run'/name;assert not rd.exists();(rd/'worker').mkdir(parents=True);(rd/'logs').mkdir();(rd/'results').mkdir();(rd/'shared').mkdir();(rd/'logs-gz').mkdir()
java='/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'
secret=secrets.token_hex(32)
env={'PATH':java+'/bin:/usr/bin:/bin','JAVA_HOME':java,'LANG':'en_US.UTF-8','SPARK_HOME':str(spark),'SPARK_CONF_DIR':str(spark/'conf'),'SPARK_LOCAL_IP':'127.0.0.1','SPARK_LOCAL_HOSTNAME':'127.0.0.1','SPARK_SCALA_VERSION':'2.13','SPARK_WORKER_DIR':str(rd/'worker'),'SPARK_LOG_DIR':str(rd/'logs'),'TMPDIR':'/private/tmp','AWS_EC2_METADATA_DISABLED':'true','SPARK_SUBMIT_OPTS':'-Djava.net.preferIPv4Stack=true'}
cluster=stage!='compare'
master='local-cluster[2,1,1024]' if cluster else 'local[2]'
conf={'spark.ui.enabled':'false','spark.driver.host':'127.0.0.1','spark.driver.bindAddress':'127.0.0.1','spark.hadoop.fs.defaultFS':'file:///','spark.task.maxFailures':'1','spark.yarn.populateHadoopClasspath':'false','spark.dynamicAllocation.enabled':'false','spark.shuffle.service.enabled':'false'}
if cluster:
    conf.update({'spark.executor.memory':execmem,'spark.executor.cores':'1','spark.cores.max':'2','spark.rpc.netty.dispatcher.numThreads':'2','spark.deploy.maxExecutorRetries':'0'})
    if sec!='none':
        env['_SPARK_AUTH_SECRET']=secret;env['SPARK_SUBMIT_OPTS']+=' -Dspark.authenticate.secret='+secret
jopts=[]
if sec!='none' and stage!='compare': jopts.append('-Dlog4j.configurationFile='+str(base/'conf/log4j2-security-debug.properties'))
if classload: jopts.append('-Xlog:class+load=info')
if jopts:
    conf['spark.driver.extraJavaOptions']=' '.join(jopts);conf['spark.executor.extraJavaOptions']=' '.join(jopts)
main='edu.uic.cs441.scholarchain.spark.Phase6Main' if stage=='pipeline' else 'edu.uic.cs441.scholarchain.spark.Phase12Readiness'
if stage=='pipeline':
    c=json.load(open(base/'conf/spark-g1-spike.json'));c['outputRoot']=str(ex/('outputs/'+name));c['checkpointDirectory']=str(ex/('checkpoints/'+name))
    cfg=rd/'g1-config.json';cfg.write_text(json.dumps(c,indent=2));args=[str(cfg)]
elif stage=='probe':
    args=['probe',str(rd/'shared'),str(rd/'results/probe.json'),'distributed']
else:
    cand=sys.argv[sys.argv.index('--candidate')+1]
    args=['compare',str(repo/'target/phase12d-readiness-20261103/baseline/g1-a-attempt2/run:2047866e-0b89-4047-9a31-dccb2515c68d'),cand,str(rd/'results/comparison.json')]
cmd=[str(spark/'bin/spark-submit'),'--master',master,'--driver-memory','2g','--class',main]
if sec!='none': cmd+=['--properties-file',(sec[5:] if sec.startswith('file:') else str(base/('spark-security.conf' if sec=='v2' else 'conf/spark-security-authv1.conf')))]
for k,v in conf.items():cmd+=['--conf',k+'='+v]
cmd+=[str(job),*args]
timeout=600
started=datetime.now(timezone.utc).isoformat();t0=time.monotonic()
rec_env=dict(env)
rec_env={k:v.replace(secret,'<redacted>') for k,v in rec_env.items()}
(rd/'command.json').write_text(json.dumps({'name':name,'stage':stage,'security':sec,'classload':classload,'command':cmd,'environment':rec_env,'cwd':str(ex),'timeout_seconds':timeout,'started_at':started,'job_jar_sha256':hashlib.sha256(job.read_bytes()).hexdigest()},indent=2)+'\n')
so=rd/'logs/driver.stdout.txt';se=rd/'logs/driver.stderr.txt'
with so.open('xb') as o,se.open('xb') as e:
    p=subprocess.Popen(cmd,cwd=ex,env=env,stdout=o,stderr=e,start_new_session=True)
    try: code=p.wait(timeout=timeout);to=False
    except subprocess.TimeoutExpired:
        to=True;os.killpg(p.pid,signal.SIGTERM)
        try: code=p.wait(timeout=20)
        except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=10)
secs=time.monotonic()-t0
wk=spark/'work'
if wk.exists():
    for a in sorted(wk.glob('app-*')):
        for j in a.glob('*/scholarchain-job.jar'): j.unlink()
        shutil.move(str(a),str(rd/'worker'/a.name))
# kill leftover group members
try: os.killpg(p.pid,signal.SIGKILL)
except ProcessLookupError: pass
sha=lambda b:hashlib.sha256(b).hexdigest()
files=[]
def gz(src,dst):
    b=Path(src).read_bytes();raw=sha(b)
    with open(dst,'wb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as g:g.write(b)
    files.append({'source':str(Path(src).relative_to(rd)),'bytes':len(b),'lines':b.count(b'\n'),'raw_sha256':raw,'gz':str(Path(dst).relative_to(rd)),'gz_sha256':sha(Path(dst).read_bytes())})
leak=0
allf=[so,se]+[Path(x) for x in sorted(glob.glob(str(rd/'worker/**/std*'),recursive=True))]
for f in allf:
    if secret.encode() in f.read_bytes():leak+=1
gz(so,rd/'logs-gz/driver.stdout.txt.gz');gz(se,rd/'logs-gz/driver.stderr.txt.gz')
for f in allf[2:]:
    rel=f.relative_to(rd/'worker');gz(f,rd/'logs-gz'/('worker-'+str(rel).replace('/','_')+'.gz'))
# scan any file in run dir (cheap) for secret
for f in rd.rglob('*'):
    if f.is_file() and f.suffix!='.gz' and f not in allf and f.stat().st_size<50_000_000 and secret.encode() in f.read_bytes():leak+=1
res={'name':name,'stage':stage,'security':sec,'classload':classload,'exit':code,'timed_out':to,'started_at':started,'seconds':secs,'driver_stdout_sha256':sha(so.read_bytes()),'driver_stderr_sha256':sha(se.read_bytes()),'secret_occurrences_in_run_files':leak,'log_files':files}
(rd/'result.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps({k:res[k] for k in('name','exit','timed_out','seconds','secret_occurrences_in_run_files')}))
if code:print(se.read_text()[-2500:])

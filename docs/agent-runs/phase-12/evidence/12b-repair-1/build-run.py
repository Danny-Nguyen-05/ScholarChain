from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,time

REPO=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
BASE=Path('/tmp/scholarchain-phase12b-repair1-build')
DENIED_DIRS={'.terraform','.plans','.git','secrets','credentials','private-keys','target'}

def nonsecret(path):
    p=Path(path)
    return not any(part.lower() in DENIED_DIRS for part in p.parts) and p.name!='.env' and not p.name.startswith('.env.') and p.suffix.lower() not in {'.pem','.key','.p12','.pfx'}

def authored_infra_paths():
    paths=[]
    for root,dirs,files in os.walk(REPO/'infra/terraform'):
        dirs[:]=[d for d in dirs if d.lower() not in DENIED_DIRS]
        for name in files:
            path=Path(root)/name
            rel=path.relative_to(REPO)
            # Keep declared course.tfvars and lockfiles; exclude local runtime outputs.
            if not nonsecret(rel):
                continue
            if name.endswith('.tfvars') and str(rel)!='infra/terraform/environments/course.tfvars':
                continue
            if name.endswith('.tfvars.json') or '.tfstate' in name or name.endswith(('.tfplan','.plan','.tfplan.json','.tfplan.txt')) or name.startswith(('tfplan','terraform-plan.')) or name in {'plan','plan.json','plan.out','plan.txt','crash.log'}:
                continue
            if name == '.gitkeep' or name.endswith(('.tf','.hcl','.md','.sh','.json','.yaml','.yml','.tpl','.tftpl','.tfvars')):
                paths.append(str(rel))
    return sorted(paths)

def tracked_source_paths():
    argv=['git','ls-files','-z','--','build.sbt','project/','modules/','tests/','scripts/','.scalafmt.conf','.gitignore','Dockerfile','.dockerignore','docker-compose.yml','docker-compose.yaml','compose.yaml','compose.yml']
    raw=subprocess.check_output(argv,cwd=REPO)
    return sorted(str(Path(p)) for p in raw.decode().split('\0') if p and nonsecret(p) and (REPO/p).is_file())

def snapshot():
    infra=authored_infra_paths()
    sources=tracked_source_paths()
    files={}
    for name in sorted(set(infra+sources)):
        path=REPO/name
        st=path.stat()
        files[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':st.st_size,'mtime_epoch':st.st_mtime,'mtime_ns':st.st_mtime_ns}
    return {'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'infra_paths':infra,'tracked_source_paths':sources,'branch':subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'files':files}

parser=argparse.ArgumentParser(description='Run only after coordinator authorizes the final Phase12B freeze.')
parser.add_argument('--freeze',required=True,type=Path)
args=parser.parse_args()
freeze=json.loads(args.freeze.read_text())
expected=freeze.get('files')
assert isinstance(expected,dict) and expected,'Expected nonempty freeze files map'
freeze_utc=freeze.get('frozen_at_utc') or freeze.get('captured_at_utc')
assert freeze_utc,'Freeze timestamp missing'
freeze_epoch=datetime.datetime.fromisoformat(freeze_utc.replace('Z','+00:00')).timestamp()
before=snapshot()
Path(str(BASE)+'-source-before.json').write_text(json.dumps(before,indent=2)+'\n')
mismatches=[]
for name,value in expected.items():
    sha=value if isinstance(value,str) else value.get('sha256')
    if name not in before['files'] or before['files'][name]['sha256']!=sha:
        mismatches.append(name)
assert not mismatches,f'Frozen source mismatches: {mismatches}'
assert set(name for name in expected if name.startswith('infra/terraform/'))==set(before['infra_paths']),'Freeze does not cover exact current authored infra inventory'
assert before['branch']=='phase-12'
assert before['head']=='a83f62e9af56058a170075f98c4e027d039567ec'
max_source_mtime=max(v['mtime_epoch'] for v in before['files'].values())
env=os.environ.copy()
env['JAVA_HOME']='/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'
env['PATH']=env['JAVA_HOME']+'/bin:'+env.get('PATH','')
env['SBT_OPTS']='-Dlogback.configurationFile='+str(REPO)+'/docs/agent-runs/phase-04/xml-repair-logback.xml'
start=time.time()
assert start>freeze_epoch and start>max_source_mtime
metadata={'owner':'build-engineer','native_task':'/root/build_12a','phase':'12B repair round1','model':'inherited; exact model identifier not exposed','cwd':str(REPO),'start_epoch':start,'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'branch':before['branch'],'head':before['head'],'environment':{k:env[k] for k in ['JAVA_HOME','SBT_OPTS']},'path_prefix':env['JAVA_HOME']+'/bin','commands':[['java','-version'],['sbt','-batch','check']],'freeze_path':str(args.freeze),'freeze_sha256':hashlib.sha256(args.freeze.read_bytes()).hexdigest(),'freeze_epoch':freeze_epoch,'max_source_mtime_epoch':max_source_mtime,'start_after_freeze':start>freeze_epoch,'start_after_all_source_mtimes':start>max_source_mtime,'frozen_source_count':len(expected),'infra_source_count':len(before['infra_paths']),'tracked_source_count':len(before['tracked_source_paths']),'all_snapshot_file_count':len(before['files']),'frozen_hash_mismatches':mismatches,'source_before_path':str(BASE)+'-source-before.json','results':[]}
Path(str(BASE)+'-start.json').write_text(json.dumps(metadata,indent=2)+'\n')
exit_code=0
for argv in metadata['commands']:
    label='java-version' if argv[0]=='java' else 'sbt-check'
    log_path=Path(str(BASE)+'-'+label+'.log')
    t=time.time()
    with log_path.open('w') as log:
        proc=subprocess.run(argv,cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,text=True)
    result={'argv':argv,'cwd':str(REPO),'start_epoch':t,'exit_code':proc.returncode,'elapsed_seconds':round(time.time()-t,3),'log':str(log_path),'log_sha256':hashlib.sha256(log_path.read_bytes()).hexdigest(),'log_bytes':log_path.stat().st_size}
    metadata['results'].append(result)
    print(json.dumps(result),flush=True)
    Path(str(BASE)+'-result.json').write_text(json.dumps(metadata,indent=2)+'\n')
    if proc.returncode:
        exit_code=proc.returncode
        break
after=snapshot()
Path(str(BASE)+'-source-after.json').write_text(json.dumps(after,indent=2)+'\n')
all_paths=set(before['files'])|set(after['files'])
changed=[name for name in sorted(all_paths) if before['files'].get(name)!=after['files'].get(name)]
metadata.update({'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':round(time.time()-start,3),'source_after_path':str(BASE)+'-source-after.json','source_changed_paths':changed,'source_unchanged':not changed,'git_branch_head_unchanged':all(before[k]==after[k] for k in ['branch','head']),'gate_exit_code':exit_code})
Path(str(BASE)+'-result.json').write_text(json.dumps(metadata,indent=2)+'\n')
assert not changed,f'Sources changed during gate: {changed}'
assert metadata['git_branch_head_unchanged'],'Branch or HEAD changed during gate'
raise SystemExit(exit_code)

from pathlib import Path
import subprocess,time,json,datetime,hashlib,os
repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
base=Path('/tmp/scholarchain-phase12a-repair1-build')
freeze_path=Path('/tmp/scholarchain-phase12a-repair1-infra-source-freeze.json')
freeze=json.loads(freeze_path.read_text())
def snapshot():
    paths=list(freeze['files'])+['.gitignore']
    files={}
    for name in paths:
        p=repo/name
        st=p.stat()
        files[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':st.st_size,'mtime_epoch':st.st_mtime,'mtime_ns':st.st_mtime_ns}
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    return {'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'branch':branch,'head':head,'files':files}
start_snapshot=snapshot()
Path(str(base)+'-source-before.json').write_text(json.dumps(start_snapshot,indent=2)+'\n')
mismatches=[name for name,sha in freeze['files'].items() if start_snapshot['files'][name]['sha256']!=sha]
assert not mismatches, f'Frozen source hash mismatches: {mismatches}'
freeze_epoch=datetime.datetime.fromisoformat(freeze['frozen_at_utc']).timestamp()
max_source_mtime=max(v['mtime_epoch'] for v in start_snapshot['files'].values())
env=os.environ.copy()
env['JAVA_HOME']='/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'
env['PATH']=env['JAVA_HOME']+'/bin:'+env.get('PATH','')
env['SBT_OPTS']='-Dlogback.configurationFile='+str(repo)+'/docs/agent-runs/phase-04/xml-repair-logback.xml'
commands=[['java','-version'],['sbt','-batch','check']]
start=time.time()
assert start>freeze_epoch and start>max_source_mtime
metadata={'owner':'build-engineer','native_task':'/root/build_12a','model':'inherited; exact model identifier not exposed','cwd':str(repo),'start_epoch':start,'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'environment':{k:env[k] for k in ['JAVA_HOME','SBT_OPTS']},'path_prefix':env['JAVA_HOME']+'/bin','commands':commands,'freeze_path':str(freeze_path),'freeze_sha256':hashlib.sha256(freeze_path.read_bytes()).hexdigest(),'freeze_epoch':freeze_epoch,'max_source_mtime_epoch':max_source_mtime,'start_after_freeze':start>freeze_epoch,'start_after_all_source_mtimes':start>max_source_mtime,'frozen_source_count':len(freeze['files']),'frozen_hash_mismatches':mismatches,'source_before_path':str(base)+'-source-before.json','results':[]}
Path(str(base)+'-start.json').write_text(json.dumps(metadata,indent=2)+'\n')
exit_code=0
for argv in commands:
    label='java-version' if argv[0]=='java' else 'sbt-check'
    output=Path(str(base)+'-'+label+'.log')
    t=time.time()
    with output.open('w') as log:
        p=subprocess.run(argv,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,text=True)
    result={'argv':argv,'cwd':str(repo),'start_epoch':t,'exit_code':p.returncode,'elapsed_seconds':round(time.time()-t,3),'log':str(output),'log_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'log_bytes':output.stat().st_size}
    metadata['results'].append(result)
    print(json.dumps(result),flush=True)
    Path(str(base)+'-result.json').write_text(json.dumps(metadata,indent=2)+'\n')
    if p.returncode:
        exit_code=p.returncode
        break
end_snapshot=snapshot()
Path(str(base)+'-source-after.json').write_text(json.dumps(end_snapshot,indent=2)+'\n')
changed=[name for name,before in start_snapshot['files'].items() if before!=end_snapshot['files'][name]]
metadata['end_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
metadata['elapsed_seconds']=round(time.time()-start,3)
metadata['source_after_path']=str(base)+'-source-after.json'
metadata['source_changed_paths']=changed
metadata['source_unchanged']=not changed
metadata['git_branch_head_unchanged']=all(start_snapshot[k]==end_snapshot[k] for k in ['branch','head'])
metadata['gate_exit_code']=exit_code
Path(str(base)+'-result.json').write_text(json.dumps(metadata,indent=2)+'\n')
assert not changed,f'Sources changed during gate: {changed}'
assert metadata['git_branch_head_unchanged'],'Branch or HEAD changed during gate'
raise SystemExit(exit_code)

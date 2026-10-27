import subprocess, time, json, hashlib, pathlib, urllib.request, urllib.error, traceback
ROOT=pathlib.Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
LOG=pathlib.Path('/tmp/phase10b-docker.log')
RESULT=pathlib.Path('/tmp/phase10b-docker-result.json')
roles={'query-api':'QueryApiMain','graph-service':'GraphServiceMain','semantic-service':'SemanticServiceMain','embedding-worker':'EmbeddingWorkerMain'}
# Deliberately public local-only smoke placeholders, unrelated to any provider/account.
api='phase10b-public-local-smoke-api'
internal='phase10b-public-local-smoke-internal'
env={'SCHOLARCHAIN_API_KEY_SHA256':hashlib.sha256(api.encode()).hexdigest(),'SCHOLARCHAIN_INTERNAL_TOKEN_SHA256':hashlib.sha256(internal.encode()).hexdigest(),'SCHOLARCHAIN_HTTP_HOST':'0.0.0.0','SCHOLARCHAIN_GRAPH_CURSOR_KEY':'phase10b-public-local-cursor'}
report={'startedUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'commands':[],'images':{},'smoke':[],'cleanup':[]}
started=time.monotonic(); active=[]
def run(cmd, expected=0):
    mark=time.monotonic()
    with LOG.open('a') as f:
        f.write('\nCOMMAND '+json.dumps(cmd)+'\n');f.flush()
        p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        f.write(p.stdout);f.flush()
    report['commands'].append({'argv':cmd,'exitCode':p.returncode,'elapsedSeconds':round(time.monotonic()-mark,3)})
    if expected is not None and p.returncode!=expected: raise AssertionError(f'{cmd[0:3]} exit {p.returncode}, expected {expected}; see {LOG}')
    return p.stdout.strip()
def request(port,path,body=None,auth=True,key=None):
    h={'X-Request-Id':'phase10b-smoke-request','X-Trace-Id':'phase10b-smoke-trace'}
    if auth:h['Authorization']='Bearer '+api
    if body is not None:h['Content-Type']='application/json'
    if key:h['Idempotency-Key']=key
    req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=None if body is None else json.dumps(body).encode(),headers=h)
    try:
        with urllib.request.urlopen(req,timeout=10) as r:return r.status,r.read().decode(),dict(r.headers)
    except urllib.error.HTTPError as e:return e.code,e.read().decode(),dict(e.headers)
def start_container(role,mode):
    name='phase10b-smoke-'+role+'-'+mode
    cmd=['docker','run','-d','--name',name,'-p','127.0.0.1::8080']
    for k,v in env.items():cmd+=['-e',k+'='+v]
    if mode!='unconfigured':cmd+=['-e','SCHOLARCHAIN_SERVICE_MODE='+mode]
    cmd+=['scholarchain-'+role+':local']
    run(cmd);active.append(name)
    port=int(run(['docker','port',name,'8080/tcp']).rsplit(':',1)[1])
    end=time.monotonic()+30
    while True:
        try:
            code,body,_=request(port,'/healthz',auth=False)
            if code==200:break
        except (OSError,urllib.error.URLError):pass
        if time.monotonic()>end:raise AssertionError('health startup timeout '+name)
        time.sleep(.25)
    uid=run(['docker','exec',name,'id','-u']);assert uid!='0'
    health=request(port,'/healthz',auth=False);ready=request(port,'/readyz',auth=False)
    assert health[0]==200
    assert ready[0]==(200 if mode=='offline-synthetic' else 503)
    if ready[0]!=200:assert json.loads(ready[1])['traceId']=='phase10b-smoke-trace'
    assert request(port,'/metrics',auth=False)[0]==401
    metrics=request(port,'/metrics');assert metrics[0]==200
    row={'role':role,'mode':mode,'health':health[0],'ready':ready[0],'uid':uid,'metrics':metrics[0],'unauthorizedMetrics':401}
    if role=='query-api' and mode=='offline-synthetic':
        payload={'question':'Synthetic fixture: publication count for A'}
        response=request(port,'/v1/query',payload,key='phase10b-smoke-idempotency');assert response[0] in (200,202),response
        answer=json.loads(response[1])
        if response[0]==202:
            end=time.monotonic()+15
            while time.monotonic()<end:
                response=request(port,'/v1/jobs/'+answer['jobId']+'/result')
                if response[0]==200:break
                assert response[0]==202,response
                time.sleep(.1)
            answer=json.loads(response[1]);assert response[0]==200
        assert answer['claims']
        assert all(c['verificationStatus'].lower()=='verified' for c in answer['claims']),answer
        researchers=answer['answer']['researchers'];assert researchers and researchers[0]['publicationCount']=='3',answer
        same=request(port,'/v1/query',payload,key='phase10b-smoke-idempotency');assert same[0]==200 and json.loads(same[1])==answer
        conflict=request(port,'/v1/query',{'question':'different fixture body'},key='phase10b-smoke-idempotency');assert conflict[0]==409
        evidence_list=request(port,answer['links']['evidence']);assert evidence_list[0]==200,evidence_list
        ids=json.loads(evidence_list[1])['evidenceIds'];assert ids
        evidence=request(port,'/v1/evidence/'+ids[0]);assert evidence[0]==200,evidence
        assert json.loads(evidence[1])['sourceRecordId']
        explain=request(port,answer['links']['explain']);assert explain[0]==200,explain
        explanation=json.loads(explain[1]);assert explanation['verificationStatus'].lower()=='verified',explanation
        row['queryLifecycle']={'queryStatus':200,'claims':len(answer['claims']),'verified':True,'publicationCount':'3','sameKeyReplay':200,'differentBody':409,'evidenceIndex':200,'evidenceFetch':200,'explain':200,'evidenceCount':len(ids)}
    report['smoke'].append(row)
    run(['docker','logs',name])
    run(['docker','rm','-f',name]);active.remove(name);report['cleanup'].append(name)
try:
    LOG.write_text('Phase10B local Docker rebuild and smoke; no push or cloud/provider calls.\n')
    distribution=ROOT/'modules/services/target/distribution'
    app=distribution/'services.jar'
    report['servicesJarSha256']=hashlib.sha256(app.read_bytes()).hexdigest()
    assets={str(p.relative_to(distribution)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((distribution/'prompts').rglob('*')) if p.is_file()}
    assert len(assets)==4,assets
    report['assetHashes']=assets
    for role,main in roles.items():
        image='scholarchain-'+role+':local'
        run(['docker','build','-f','Dockerfile','--build-arg','MAIN_CLASS=edu.uic.cs441.scholarchain.services.'+main,'-t',image,'.'])
        info=json.loads(run(['docker','image','inspect',image]))[0]
        assert info['Config']['User']=='scholarchain'
        assert 'SCHOLARCHAIN_MAIN_CLASS=edu.uic.cs441.scholarchain.services.'+main in info['Config']['Env']
        hashes=run(['docker','run','--rm','--network','none','--entrypoint','sha256sum',image,'/app/services.jar']+['/app/'+p for p in assets])
        parsed={line.split()[1].removeprefix('/app/'):line.split()[0] for line in hashes.splitlines()}
        assert parsed['services.jar']==report['servicesJarSha256']
        assert all(parsed[p]==sha for p,sha in assets.items())
        invalid=run(['docker','run','--rm','--network','none',image],expected=2)
        assert 'invalid-or-missing-service-configuration' in invalid
        report['images'][role]={'id':info['Id'],'mainClass':main,'user':info['Config']['User'],'invalidConfigExit':2,'packageHashMatches':True,'promptAssetsHashMatches':True}
        for mode in ('unconfigured','offline-synthetic'):start_container(role,mode)
    report['status']='PASS'
except BaseException as e:
    report['status']='FAIL';report['error']=str(e)
    with LOG.open('a') as f:f.write(traceback.format_exc())
finally:
    for name in active[:]:
        run(['docker','logs',name],expected=None)
        run(['docker','rm','-f',name],expected=None)
        report['cleanup'].append(name);active.remove(name)
    report['elapsedSeconds']=round(time.monotonic()-started,3)
    report['finishedUtc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    report['logSha256']=hashlib.sha256(LOG.read_bytes()).hexdigest()
    RESULT.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'images':len(report['images']),'smokeCases':len(report['smoke']),'elapsedSeconds':report['elapsedSeconds'],'log':str(LOG),'result':str(RESULT),'error':report.get('error')}))
raise SystemExit(0 if report['status']=='PASS' else 1)

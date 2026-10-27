import subprocess,time,json,pathlib,hashlib,urllib.request,urllib.error,traceback
ROOT=pathlib.Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
LOG=pathlib.Path('/tmp/phase10b-docker-remote.log');RESULT=pathlib.Path('/tmp/phase10b-docker-remote-result.json')
network='phase10b-remote-isolated-smoke'; active=[]; created=False
api='phase10b-public-local-smoke-api';token='phase10b-public-local-smoke-internal'
env={'SCHOLARCHAIN_API_KEY_SHA256':hashlib.sha256(api.encode()).hexdigest(),'SCHOLARCHAIN_INTERNAL_TOKEN_SHA256':hashlib.sha256(token.encode()).hexdigest(),'SCHOLARCHAIN_HTTP_HOST':'0.0.0.0','SCHOLARCHAIN_SERVICE_MODE':'offline-synthetic','SCHOLARCHAIN_GRAPH_CURSOR_KEY':'phase10b-public-local-cursor','SCHOLARCHAIN_DOWNSTREAM_TIMEOUT_MS':'500','SCHOLARCHAIN_DOWNSTREAM_MAX_ATTEMPTS':'1'}
report={'startedUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'commands':[],'cleanup':[]};start=time.monotonic()
def run(cmd,expected=0):
    t=time.monotonic()
    with LOG.open('a') as f:
        shown=['SCHOLARCHAIN_INTERNAL_TOKEN=<public-local-smoke-placeholder>' if a.startswith('SCHOLARCHAIN_INTERNAL_TOKEN=') else 'Authorization: Bearer <public-local-smoke-placeholder>' if a.startswith('Authorization: Bearer ') else a for a in cmd]
        f.write('\nCOMMAND '+json.dumps(shown)+'\n');f.flush()
        p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        f.write(p.stdout);f.flush()
    report['commands'].append({'argv':shown,'exitCode':p.returncode,'elapsedSeconds':round(time.monotonic()-t,3)})
    if expected is not None:assert p.returncode==expected,(shown,p.returncode)
    return p.stdout.strip()
def request(port,path,body=None,key=None):
    cmd=['docker','exec','phase10b-remote-query-api','curl','-sS','--max-time','5','-w','\n%{http_code}','-H','Authorization: Bearer '+api,'-H','X-Request-Id: phase10b-remote-request','-H','X-Trace-Id: phase10b-remote-trace']
    if body is not None:cmd+=['-H','Content-Type: application/json','--data',json.dumps(body)]
    if key:cmd+=['-H','Idempotency-Key: '+key]
    cmd+=['http://127.0.0.1:8080'+path]
    output=run(cmd,None)
    if '\n' not in output:raise OSError('HTTP listener not ready')
    data,status=output.rsplit('\n',1)
    if not status.isdecimal() or status=='000':raise OSError('HTTP listener not ready')
    return int(status),data,{}

try:
    LOG.write_text('Local three-packaged-main integration on isolated internal Docker network. No cloud/provider calls.\n')
    run(['docker','network','create','--internal',network]);created=True
    for role in ('graph-service','semantic-service','query-api'):
        name='phase10b-remote-'+role
        cmd=['docker','run','-d','--name',name,'--network',network]
        # Internal Docker network deliberately has no published host ports.
        for k,v in env.items():cmd+=['-e',k+'='+v]
        if role=='query-api':
            cmd+=['-e','SCHOLARCHAIN_GRAPH_BASE_URI=http://phase10b-remote-graph-service:8080','-e','SCHOLARCHAIN_SEMANTIC_BASE_URI=http://phase10b-remote-semantic-service:8080','-e','SCHOLARCHAIN_INTERNAL_TOKEN='+token]
        cmd+=['scholarchain-'+role+':local'];run(cmd);active.append(name)
    port=8080
    end=time.monotonic()+30
    while True:
        try:
            health=request(port,'/healthz');ready=request(port,'/readyz')
            if health[0]==200 and ready[0]==200:break
        except (OSError,urllib.error.URLError):pass
        assert time.monotonic()<end,'three-main ready startup timeout'
        time.sleep(.2)
    report['initial']={'health':health[0],'ready':ready[0]}
    r=request(port,'/v1/query',{'question':'Synthetic fixture: publication count for A'},'phase10b-remote-key')
    assert r[0] in (200,202),r
    answer=json.loads(r[1])
    if r[0]==202:
        end=time.monotonic()+15
        while time.monotonic()<end:
            r=request(port,'/v1/jobs/'+answer['jobId']+'/result')
            if r[0]==200:break
            assert r[0]==202,r
            time.sleep(.1)
        answer=json.loads(r[1])
    assert r[0]==200,r
    assert answer['answer']['researchers'][0]['publicationCount']=='3',answer
    assert answer['claims'] and all(c['verificationStatus'].lower()=='verified' for c in answer['claims']),answer
    report['query']={'status':r[0],'verified':True,'publicationCount':'3','claims':len(answer['claims'])}
    metrics=request(port,'/metrics');assert metrics[0]==200
    for dependency in ('graph','semantic'):
        assert 'downstream_circuit_state{dependency="'+dependency+'",state="CLOSED"} 1' in metrics[1],metrics
    report['breakerGauges']={'graph':'CLOSED','semantic':'CLOSED'}
    graph_logs=run(['docker','logs','phase10b-remote-graph-service'])
    semantic_logs=run(['docker','logs','phase10b-remote-semantic-service'])
    assert 'phase10b-remote-trace' in graph_logs and '\"status\":200' in graph_logs,graph_logs
    assert 'phase10b-remote-trace' in semantic_logs and '\"status\":200' in semantic_logs,semantic_logs
    report['propagation']={'graphCorrelatedRequest200':True,'semanticCorrelatedRequest200':True,'traceId':'phase10b-remote-trace','internalRouteLogLabel':'unmatched'}
    run(['docker','stop','--time','2','phase10b-remote-graph-service'])
    t=time.monotonic();health=request(port,'/healthz');ready=request(port,'/readyz');elapsed=time.monotonic()-t
    assert health[0]==200,health
    assert ready[0]==503,ready
    err=json.loads(ready[1]);assert err['traceId']=='phase10b-remote-trace' and err['error']=='NOT_READY',err
    assert 'phase10b-remote-graph-service' not in ready[1]
    report['afterGraphStopped']={'health':health[0],'ready':ready[0],'error':err['error'],'traceId':err['traceId'],'elapsedSeconds':round(elapsed,3)}
    report['status']='PASS'
except BaseException as e:
    report['status']='FAIL';report['error']=str(e)
    with LOG.open('a') as f:f.write(traceback.format_exc())
finally:
    for name in active:
        run(['docker','logs',name],None)
        run(['docker','rm','-f',name],None)
        report['cleanup'].append(name)
    if created:
        run(['docker','network','rm',network],None);report['cleanup'].append(network)
    report['elapsedSeconds']=round(time.monotonic()-start,3)
    report['finishedUtc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    report['logSha256']=hashlib.sha256(LOG.read_bytes()).hexdigest()
    RESULT.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report.get(k) for k in ('status','initial','query','breakerGauges','propagation','afterGraphStopped','elapsedSeconds','error')}))
raise SystemExit(0 if report['status']=='PASS' else 1)

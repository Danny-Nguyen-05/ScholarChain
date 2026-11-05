from pathlib import Path
from datetime import datetime,timezone
import urllib.request,hashlib,json,time
root=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase12d-portable-runtime-20261103'); evidence=Path('/tmp/scholarchain-phase12d-portable-runtime-build-20261103'); dl=root/'downloads';dl.mkdir()
base='https://archive.apache.org/dist/spark/spark-3.5.4/'
items=[('spark.sha512',base+'spark-3.5.4-bin-hadoop3-scala2.13.tgz.sha512',65536),('spark.asc',base+'spark-3.5.4-bin-hadoop3-scala2.13.tgz.asc',65536),('spark-KEYS','https://downloads.apache.org/spark/KEYS',8*1024*1024),('spark-3.5.4-bin-hadoop3-scala2.13.tgz',base+'spark-3.5.4-bin-hadoop3-scala2.13.tgz',512*1024*1024)]
rows=[]
for name,url,limit in items:
 start=datetime.now(timezone.utc).isoformat();start_mono=time.monotonic();target=dl/name
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ScholarChain-offline-runtime-verification/1'})
  with urllib.request.urlopen(req,timeout=60) as response:
   assert response.url.startswith('https://')
   assert response.status==200
   length=response.headers.get('Content-Length')
   if length is not None:assert int(length)<=limit
   size=0;sha=hashlib.sha256();sha512=hashlib.sha512()
   with target.open('xb') as output:
    while True:
     assert time.monotonic()-start_mono<360,'wall time bound'
     chunk=response.read(1024*1024)
     if not chunk:break
     size+=len(chunk);assert size<=limit,'size bound';output.write(chunk);sha.update(chunk);sha512.update(chunk)
  row={'name':name,'url':url,'final_url':response.url,'status':200,'bytes':size,'sha256':sha.hexdigest(),'sha512':sha512.hexdigest(),'started_at':start,'completed_at':datetime.now(timezone.utc).isoformat(),'size_limit':limit,'elapsed_seconds':time.monotonic()-start_mono,'path':str(target)}
 except Exception as e:
  row={'name':name,'url':url,'started_at':start,'completed_at':datetime.now(timezone.utc).isoformat(),'exception_type':type(e).__name__,'error':str(e),'path':str(target)}
 rows.append(row);(evidence/'fetch-manifest.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
 if row.get('status')!=200:raise SystemExit(2)

from pathlib import Path
from datetime import datetime,timezone
import urllib.request,hashlib,json
r=Path('/tmp/scholarchain-phase12d-portable-runtime-build-20261103/security-source');r.mkdir();rows=[]
for name,path in [('LocalSparkCluster.scala','core/src/main/scala/org/apache/spark/deploy/LocalSparkCluster.scala'),('SecurityManager.scala','core/src/main/scala/org/apache/spark/SecurityManager.scala'),('AuthEngine.java','common/network-common/src/main/java/org/apache/spark/network/crypto/AuthEngine.java'),('GcmTransportCipher.java','common/network-common/src/main/java/org/apache/spark/network/crypto/GcmTransportCipher.java'),('TransportConf.java','common/network-common/src/main/java/org/apache/spark/network/util/TransportConf.java')]:
 url='https://raw.githubusercontent.com/apache/spark/v3.5.4/'+path
 try:
  with urllib.request.urlopen(url,timeout=30) as f:b=f.read(1024*1024+1);assert len(b)<=1024*1024 and f.status==200
  (r/name).write_bytes(b);row={'name':name,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'status':200,'retrieved_at':datetime.now(timezone.utc).isoformat()}
 except Exception as e:row={'name':name,'url':url,'error_type':type(e).__name__,'error':str(e)}
 rows.append(row);print(json.dumps(row),flush=True)
(r/'fetch-manifest.json').write_text(json.dumps(rows,indent=2)+'\n')

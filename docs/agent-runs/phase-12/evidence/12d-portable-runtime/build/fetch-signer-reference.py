from pathlib import Path
from datetime import datetime,timezone
import urllib.request,hashlib,json
r=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase12d-portable-runtime-20261103/downloads');e=Path('/tmp/scholarchain-phase12d-portable-runtime-build-20261103');rows=[]
for name,url in [('apache-spark-docker-release-template.py','https://raw.githubusercontent.com/apache/spark-docker/6b917ced4279dd7b3a33a81a08db37b3f27e037b/tools/template.py'),('yangjie01.asc','https://people.apache.org/keys/committer/yangjie01.asc')]:
 try:
  with urllib.request.urlopen(url,timeout=60) as f:
   b=f.read(2*1024*1024+1);assert len(b)<=2*1024*1024;assert f.status==200
  (r/name).write_bytes(b);row={'name':name,'url':url,'status':200,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat()}
 except Exception as x:row={'name':name,'url':url,'exception':type(x).__name__,'error':str(x)}
 rows.append(row);print(json.dumps(row))
(e/'signer-reference-fetch.json').write_text(json.dumps(rows,indent=2)+'\n')
assert all(x.get('status')==200 for x in rows)

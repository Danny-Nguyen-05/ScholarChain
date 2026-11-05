from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import urllib.request,json,hashlib,gzip
root=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-12/evidence/12d-portable-runtime/public-sources')
root.mkdir(exist_ok=False)
items={
 's3-multipart':'https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html',
 's3-multipart-limits':'https://docs.aws.amazon.com/AmazonS3/latest/userguide/qfacts.html',
 's3-kms':'https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html',
 'emr-certificates':'https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-encryption-enable.html',
 'emr-storage':'https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-storage.html',
 'iam-simulator':'https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html',
 'spark-yarn-v3.5.4':'https://raw.githubusercontent.com/apache/spark/v3.5.4/docs/running-on-yarn.md',
 'spark-security-v3.5.4':'https://raw.githubusercontent.com/apache/spark/v3.5.4/docs/security.md'}
def fetch(item):
 name,url=item;start=datetime.now(timezone.utc).isoformat();req=urllib.request.Request(url,headers={'User-Agent':'ScholarChain-public-document-research/1','Accept-Encoding':'identity'})
 try:
  with urllib.request.urlopen(req,timeout=35) as r:
   assert r.status==200;raw=r.read(2*1024*1024+1);assert len(raw)<=2*1024*1024;final=r.url
  compressed=gzip.compress(raw,mtime=0);(root/(name+'.response.gz')).write_bytes(compressed)
  return {'name':name,'url':url,'final_url':final,'started_at':start,'completed_at':datetime.now(timezone.utc).isoformat(),'http_status':200,'decoded_bytes':len(raw),'decoded_sha256':hashlib.sha256(raw).hexdigest(),'saved_sha256':hashlib.sha256(compressed).hexdigest(),'max_bytes':2*1024*1024}
 except Exception as e:return {'name':name,'url':url,'started_at':start,'completed_at':datetime.now(timezone.utc).isoformat(),'error_type':type(e).__name__,'error':str(e)}
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,items.items()))
(root/'fetch-manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'attempts':len(rows),'successes':sum(x.get('http_status')==200 for x in rows),'failures':[x for x in rows if x.get('http_status')!=200],'AWS_account_calls':0},indent=2))

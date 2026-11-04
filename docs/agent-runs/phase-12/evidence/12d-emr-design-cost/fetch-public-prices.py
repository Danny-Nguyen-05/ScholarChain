from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.error, json, gzip, hashlib, time

root=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-12/evidence/12d-emr-design-cost/public-prices')
root.mkdir(mode=0o700)
urls={
 'ec2-linux-ohio':'https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/US%20East%20(Ohio)/Linux/index.json',
 'emr':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/ElasticMapReduce/current/us-east-2/index.json',
 'efs':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEFS/current/us-east-2/index.json',
 'vpc':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/current/us-east-2/index.json',
 's3':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-2/index.json',
 'kms':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/awskms/current/us-east-2/index.json',
 'lambda':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSLambda/current/us-east-2/index.json',
 'cloudwatch':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/us-east-2/index.json',
 'eventbridge':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSEvents/current/us-east-2/index.json',
 'states':'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonStates/current/us-east-2/index.json',
 'ebs-page':'https://aws.amazon.com/ebs/pricing/',
 'vpc-page':'https://aws.amazon.com/vpc/pricing/',
 'kms-page':'https://aws.amazon.com/kms/pricing/',
 'efs-page':'https://aws.amazon.com/efs/pricing/',
}
sha=lambda data:hashlib.sha256(data).hexdigest()
def fetch(item):
 name,url=item;begin=time.monotonic();row={'name':name,'url':url,'requested_at':datetime.now(timezone.utc).isoformat(),'anonymous_public_HTTP':True}
 try:
  request=urllib.request.Request(url,headers={'Accept-Encoding':'gzip','User-Agent':'ScholarChain-public-cost-research/1.0'})
  with urllib.request.urlopen(request,timeout=35) as response:
   data=response.read(16*1024*1024+1);assert len(data)<=16*1024*1024,'bounded response limit'
   row.update({'http_status':response.status,'final_url':response.url,'content_type':response.headers.get('Content-Type'),'content_encoding':response.headers.get('Content-Encoding'),'last_modified':response.headers.get('Last-Modified')})
  decoded=gzip.decompress(data) if data.startswith(b'\x1f\x8b') else data
  assert len(decoded)<=32*1024*1024,'decoded response limit'
  with (root/(name+'.response.gz')).open('xb') as f:f.write(gzip.compress(decoded,mtime=0))
  row.update({'response_bytes':len(data),'response_sha256':sha(data),'decoded_bytes':len(decoded),'decoded_sha256':sha(decoded),'saved':name+'.response.gz','saved_sha256':sha((root/(name+'.response.gz')).read_bytes())})
  if 'json' in row['content_type'] or url.endswith('.json'):
   parsed=json.loads(decoded);row.update({'json_decoded':True,'catalog_version':parsed.get('version'),'publication_date':parsed.get('publicationDate')})
 except Exception as exc:
  row.update({'error_type':type(exc).__name__,'error':str(exc)})
 row.update({'completed_at':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-begin,3)})
 return row
with ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(fetch,urls.items()))
with (root/'fetch-manifest.json').open('x') as f:json.dump(rows,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps([{'name':r['name'],'status':r.get('http_status'),'bytes':r.get('decoded_bytes'),'error':r.get('error')} for r in rows],sort_keys=True))

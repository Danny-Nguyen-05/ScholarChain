from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,tarfile,gzip
repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');root=repo/'target/phase12d-portable-runtime-20261103';ev=Path('/tmp/scholarchain-phase12d-portable-runtime-build-20261103');local=Path('/tmp/sc-runtime-test-20261103');source=repo/'target/phase12d-readiness-20261103/bundles/g1-a';dest=local/'inputs/g1';dest.parent.mkdir();shutil.copytree(source,dest);sha=lambda b:hashlib.sha256(b).hexdigest();rows=[]
for p in sorted(source.rglob('*')):
 assert not p.is_symlink()
 if p.is_file():
  q=dest/p.relative_to(source);b=p.read_bytes();assert q.read_bytes()==b;rows.append({'path':str(p.relative_to(source)),'bytes':len(b),'sha256':sha(b),'mode':oct(p.stat().st_mode&0o777)})
assert len(rows)==85
out=root/'artifacts/scholarchain-g1-upstream-inputs.tgz'
with out.open('xb') as raw:
 with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as gz:
  with tarfile.open(fileobj=gz,mode='w') as tar:
   for row in rows:
    p=source/row['path'];info=tar.gettarinfo(str(p),arcname='g1/'+row['path']);info.uid=info.gid=info.mtime=0;info.uname=info.gname=''
    with p.open('rb') as f:tar.addfile(info,f)
with tarfile.open(out) as t:
 members=t.getmembers();assert len(members)==85
 for m in members:
  assert m.isfile() and not m.issym() and not m.islnk();rel=Path(m.name).relative_to('g1');p=dest/rel;assert t.extractfile(m).read()==p.read_bytes()
inputinfo={'source':str(source),'relocated_inputs':str(dest),'members':rows,'files':len(rows),'expanded_bytes':sum(r['bytes'] for r in rows),'artifact':{'name':out.name,'path':str(out),'bytes':out.stat().st_size,'sha256':sha(out.read_bytes())},'symlinks':0,'hardlinks':0,'byte_identical':True,'archive_members_match':85};(ev/'input-bundle-inventory.json').write_text(json.dumps(inputinfo,indent=2)+'\n')
prior=json.loads((repo/'target/phase12d-readiness-20261103/config/spark-g1-a.json').read_text());prior['hadoopRunRoot']=str(dest/'hadoop');prior['entityResolutionRunRoot']=str(dest/'er');prior['outputRoot']=str(local/'outputs/g1-portable');prior['checkpointDirectory']=str(local/'checkpoints/g1-portable');prior['shufflePartitions']=2
(local/'config').mkdir();(local/'outputs').mkdir();(local/'results').mkdir();(local/'config/spark-g1-portable.json').write_text(json.dumps(prior,indent=2)+'\n')
print(json.dumps({'input_archive':inputinfo['artifact'],'expanded_bytes':inputinfo['expanded_bytes'],'files':85,'relocated':str(dest)}))

from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import tarfile,hashlib,json,shutil,os,stat
repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain'); root=repo/'target/phase12d-portable-runtime-20261103'; ev=Path('/tmp/scholarchain-phase12d-portable-runtime-build-20261103');source=root/'official';source.mkdir();sha=lambda b:hashlib.sha256(b).hexdigest();prefix='spark-3.5.4-bin-hadoop3-scala2.13'; rows=[]
with tarfile.open(root/'downloads'/f'{prefix}.tgz') as t:
 members=t.getmembers();assert len(members)<=50000;assert sum(x.size for x in members)<=3*1024**3;seen=set()
 for m in members:
  q=PurePosixPath(m.name);assert not q.is_absolute() and '..' not in q.parts and q.parts[0]==prefix and m.name not in seen;seen.add(m.name);assert m.isdir() or m.isfile();assert not(m.mode&0o7000)
  out=source.joinpath(*q.parts)
  if m.isdir():out.mkdir(parents=True,exist_ok=True);kind='directory';h=None
  else:
   assert m.size<=512*1024**2;out.parent.mkdir(parents=True,exist_ok=True);stream=t.extractfile(m);digest=hashlib.sha256();count=0
   with out.open('xb') as f:
    for b in iter(lambda:stream.read(1024*1024),b''):count+=len(b);assert count<=m.size;f.write(b);digest.update(b)
   assert count==m.size;out.chmod(m.mode&0o777);h=digest.hexdigest();kind='regular'
  rows.append({'path':m.name,'kind':kind,'bytes':m.size,'mode':oct(m.mode),'sha256':h})
(ev/'official-member-inventory.json').write_text(json.dumps({'member_count':len(rows),'expanded_bytes':sum(x['bytes'] for x in rows),'symlinks':0,'hardlinks':0,'members':rows},indent=2)+'\n')
release=root/'release/scholarchain-runtime';release.mkdir(parents=True);original=source/prefix
for name in ['bin','sbin','conf','jars','licenses']:
 shutil.copytree(original/name,release/name)
for name in ['LICENSE','NOTICE','RELEASE']:shutil.copy2(original/name,release/name)
removed=[]
for name in ['scala-library-2.13.8.jar','scala-reflect-2.13.8.jar','scala-compiler-2.13.8.jar']:
 p=release/'jars'/name;removed.append({'name':name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'reason':'Replace library/reflect with2.13.14 to match immutable job; omit unused2.13.8 compiler. Spark shell capability not claimed.'});p.unlink()
ref=json.loads((repo/'docs/agent-runs/phase-12/evidence/12d-spark-readiness/runtime/runtime-manifest.json').read_text());allrefs=ref['external_artifacts']+ref['excluded_bundled_user_libraries'];overlay=[]
for name in ['scala-library-2.13.14.jar','scala-reflect-2.13.14.jar']:
 records=[r for r in allrefs if r['artifact']==name];assert records and len({r['sha256'] for r in records})==1;r=records[0];p=Path(r['resolved_path']);b=p.read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'];shutil.copy2(p,release/'jars'/name);overlay.append({'name':name,'bytes':len(b),'sha256':sha(b),'source':str(p),'prior_manifest_binding':'docs/agent-runs/phase-12/evidence/12d-spark-readiness/runtime/runtime-manifest.json'})
job=repo/'modules/spark/target/spark-job_3-0.1.0-SNAPSHOT.jar';b=job.read_bytes();assert len(b)==11732592 and sha(b)=='d52f11ebad5ec9e1ffdd1910d562023e934ce7ab62e7c74a5ffd650f8951b86b';(release/'application').mkdir();shutil.copy2(job,release/'application/scholarchain-job.jar')
(release/'RUNTIME-NOTES.txt').write_text('ScholarChain offline portable runtime candidate. Based on verified ApacheSpark3.5.4 Scala2.13 distribution. Library/reflect2.13.14 replace2.13.8 to match immutable job; compiler2.13.8 omitted. No shell/REPL capability claimed. Java17 is an external prerequisite. No EMR/YARN/cloud compatibility is established. All application Scala3.3.4 and user libraries stay inside the unchanged job JAR. No credentials/config from the author machine are bundled.\n')
files=[]
for p in sorted(release.rglob('*')):
 assert not p.is_symlink()
 if p.is_file():files.append({'path':str(p.relative_to(release)),'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode)),'sha256':sha(p.read_bytes())})
assert not any('_2.12-' in r['path'] or 'scala-library-2.13.8' in r['path'] for r in files)
(ev/'runtime-file-inventory.json').write_text(json.dumps({'root':str(release),'files':files,'file_count':len(files),'bytes':sum(x['bytes'] for x in files),'symlinks':0,'hardlinks':0,'removed_official_jars':removed,'added_overlay_jars':overlay,'job_jar_sha256':sha(b),'java17_external_prerequisite':True,'built_at':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
print(json.dumps({'release':str(release),'files':len(files),'jars':len(list((release/'jars').glob('*.jar'))),'bytes':sum(x['bytes'] for x in files),'job_jar_sha256':sha(b)}))

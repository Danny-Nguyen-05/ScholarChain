from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import tarfile,gzip,zipfile,hashlib,json,stat,os
root=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase12d-portable-runtime-20261103');source=root/'release/scholarchain-runtime';ev=Path('/tmp/scholarchain-phase12d-portable-runtime-build-20261103');out=root/'artifacts';out.mkdir();sha=lambda b:hashlib.sha256(b).hexdigest();manifest=json.loads((ev/'runtime-file-inventory.json').read_text())
full=out/'scholarchain-spark3.5.4-scala2.13.14-java17-runtime.tgz'
with full.open('xb') as raw:
 with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as gz:
  with tarfile.open(fileobj=gz,mode='w') as tar:
   for row in manifest['files']:
    p=source/row['path'];b=p.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'];info=tar.gettarinfo(str(p),arcname='scholarchain-runtime/'+row['path']);info.uid=info.gid=info.mtime=0;info.uname=info.gname='';info.mode=int(row['mode'],8)
    with p.open('rb') as f:tar.addfile(info,f)
yarn=out/'scholarchain-spark3.5.4-scala2.13.14-yarn-jars.zip'
with zipfile.ZipFile(yarn,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted((source/'jars').glob('*.jar')):
  info=zipfile.ZipInfo(p.name,date_time=(1980,1,1,0,0,0));info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
files=[]
for p,role,unpacked,members in [(full,'Portable JVM runtime plus unchanged application job; candidate staging object, no live strategy selected',manifest['bytes'],manifest['file_count']),(yarn,'Optional separate spark.yarn.archive with all runtime JARs at archive root; additional object, not silently included in runtime TGZ staging cost',sum(p.stat().st_size for p in (source/'jars').glob('*.jar')),len(list((source/'jars').glob('*.jar'))))]:
 files.append({'path':str(p),'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'uncompressed_regular_bytes':unpacked,'regular_members':members,'role':role})
(ev/'package-artifacts.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'files':files,'both_archives_compressed_bytes':sum(x['bytes'] for x in files),'cloud_staging_selected':False,'spark_shell_supported':False,'java17_bundled':False,'symlinks':0,'hardlinks':0,'application_jar_sha256':'d52f11ebad5ec9e1ffdd1910d562023e934ce7ab62e7c74a5ffd650f8951b86b'},indent=2)+'\n')
relocated=Path('/tmp/sc-runtime-test-20261103');relocated.mkdir()
with tarfile.open(full) as tar:
 entries=tar.getmembers();assert len(entries)==manifest['file_count'];assert sum(t.size for t in entries)==manifest['bytes'];assert len(entries)<=50000 and sum(t.size for t in entries)<=3*1024**3
 for member in entries:
  q=PurePosixPath(member.name);assert q.parts[0]=='scholarchain-runtime' and '..' not in q.parts and not q.is_absolute() and member.isfile() and not(member.mode&0o7000);target=relocated.joinpath(*q.parts);target.parent.mkdir(parents=True,exist_ok=True)
  with tar.extractfile(member) as src,target.open('xb') as dst:
   while b:=src.read(1024*1024):dst.write(b)
  target.chmod(member.mode&0o777)
for row in manifest['files']:
 p=relocated/'scholarchain-runtime'/row['path'];b=p.read_bytes();assert not p.is_symlink() and len(b)==row['bytes'] and sha(b)==row['sha256'];assert stat.S_IMODE(p.stat().st_mode)==int(row['mode'],8)
(ev/'relocation-validation.json').write_text(json.dumps({'source_artifact':str(full),'source_sha256':files[0]['sha256'],'relocated_root':str(relocated/'scholarchain-runtime'),'file_hash_and_mode_matches':manifest['file_count'],'symlinks':0,'hardlinks':0,'old_cache_links':0},indent=2)+'\n')
print(json.dumps({'archives':files,'relocated_root':str(relocated/'scholarchain-runtime'),'matches':manifest['file_count']},indent=2))

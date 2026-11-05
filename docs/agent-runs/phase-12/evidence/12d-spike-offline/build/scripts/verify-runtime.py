import tarfile,hashlib,json,re,sys
tgz=sys.argv[1];out=sys.argv[2]
sha=hashlib.sha256(open(tgz,'rb').read()).hexdigest()
t=tarfile.open(tgz,'r:gz')
members=t.getmembers()
job=[m for m in members if m.name=='scholarchain-runtime/application/scholarchain-job.jar']
jm=job[0]
jsha=hashlib.sha256(t.extractfile(jm).read()).hexdigest()
jars=[m.name for m in members if m.isfile() and m.name.endswith('.jar')]
sel=sorted(n for n in jars if re.search(r'/(scala-|scala3-|spark-core)',n.rsplit('/',1)[1] and '/'+n.rsplit('/',1)[1]))
bad212=sorted(n for n in jars if '_2.12' in n)
sl=sorted(n for n in jars if n.rsplit('/',1)[1].startswith('scala-library'))
sl212=[n for n in sl if re.search(r'scala-library-2\.12\.',n)]
tops=sorted({m.name.split('/')[0] for m in members})
r={'tgz':tgz,'sha256':sha,'expected_sha256':'789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5','sha256_match':sha=='789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5',
'member_count':len(members),'file_member_count':sum(m.isfile() for m in members),'jar_count':len(jars),'top_dirs':tops,
'job_jar':{'member':jm.name,'mode_octal':oct(jm.mode),'mode_is_0644':jm.mode&0o7777==0o644,'sha256':jsha,'expected_sha256':'d52f11ebad5ec9e1ffdd1910d562023e934ce7ab62e7c74a5ffd650f8951b86b','sha256_match':jsha=='d52f11ebad5ec9e1ffdd1910d562023e934ce7ab62e7c74a5ffd650f8951b86b'},
'scala_and_spark_core_jars':sel,'scala_library_jars':sl,'jars_with__2.12':bad212,'scala_library_2.12_jars':sl212,
'assert_no__2.12_jar':len(bad212)==0,'assert_no_scala_library_2.12':len(sl212)==0}
json.dump(r,open(out,'w'),indent=2);print(json.dumps(r,indent=1))

from pathlib import Path
import sys, subprocess, json, hashlib, datetime, time, gzip, os, re, xml.etree.ElementTree as ET
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
OUT=Path('/tmp/scholarchain-phase12d-execution-prep-build')
FREEZE=Path(sys.argv[1]).resolve()

def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data): (OUT/name).write_text(json.dumps(data,indent=2)+'\n')
def file_record(rel):
 p=ROOT/rel;s=p.stat();return {'path':rel,'sha256':sha(p),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
def snapshot():
 names=sorted(set(subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0'))-{''})
 files=[];excluded=[]
 for rel in names:
  if rel.startswith('docs/agent-runs/'): continue
  p=ROOT/rel
  if not p.is_file(): continue
  parts=Path(rel).parts
  if any(q in ('secrets','credentials','.aws','.ssh') for q in parts) or p.name=='.env' or p.name.startswith('.env.') or p.suffix in ('.pem','.key','.p12','.pfx'):
   excluded.append(rel);continue
  files.append(file_record(rel))
 return {'timestamp_utc':stamp(),'scope':'All Git-visible files except mutable docs/agent-runs/** and credential-like files; ignored generated files are absent by git inventory.','excluded_sensitive_names':excluded,'files':files}
def frozen_check():
 d=json.loads(FREEZE.read_text());bad=[]
 for f in d['files']:
  p=ROOT/f['path']
  if not p.is_file():bad.append({'path':f['path'],'reason':'missing'});continue
  a=file_record(f['path'])
  diff={k:{'expected':f[k],'actual':a[k]} for k in ('sha256','bytes','mtime_ns') if f[k]!=a[k]}
  if diff:bad.append({'path':f['path'],'differences':diff})
 return {'files':len(d['files']),'mismatches':bad,'freeze_sha256':sha(FREEZE),'checked_at':stamp()}
pre=frozen_check();write('freeze-before.json',pre)
if pre['mismatches']: raise SystemExit('Source freeze mismatch before build')
before=snapshot();write('source-before.json',before)
commands=[]
java_home='/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'
prefix='export JAVA_HOME='+java_home+'\nexport PATH="$JAVA_HOME/bin:$PATH"\nexport SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"\n'

selected_environment={'JAVA_HOME':java_home,'PATH_prefix':java_home+'/bin','SBT_OPTS':'-Dlogback.configurationFile='+str(ROOT/'docs/agent-runs/phase-04/xml-repair-logback.xml')}

def run(label,command):
 start_ns=time.time_ns();started=stamp();t=time.monotonic();log=OUT/(label+'.log.txt')
 argv=['/bin/bash','-c',prefix+command]
 with log.open('wb') as stream:
  p=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  (OUT/'active-process.json').write_text(json.dumps({'label':label,'pid':p.pid,'started_utc':started})+'\n')
  code=p.wait()
 ended=stamp();end_ns=time.time_ns()
 r={'label':label,'argv':argv,'cwd':str(ROOT),'environment':selected_environment,'environment_capture':'Only JAVA_HOME, SBT_OPTS and the prepended JDK bin prefix; inherited PATH intentionally omitted.','started_utc':started,'ended_utc':ended,'start_ns':start_ns,'end_ns':end_ns,'exit_code':code,'wall_seconds':round(time.monotonic()-t,6),'log':log.name,'log_sha256':sha(log),'log_bytes':log.stat().st_size}
 commands.append(r);write('commands.json',commands)
 return r
java=run('java-version','java -version')
if java['exit_code']:raise SystemExit('java-version failed')
build=run('sbt-check','sbt -batch check')
after=snapshot();write('source-after.json',after)
a={x['path']:x for x in before['files']};b={x['path']:x for x in after['files']}
deltas=[]
for path in sorted(a.keys()|b.keys()):
 if a.get(path)!=b.get(path):deltas.append({'path':path,'before':a.get(path),'after':b.get(path)})
post=frozen_check();write('freeze-after.json',post)
raw=OUT/'sbt-check.log.txt'
with raw.open('rb') as src, (OUT/'sbt-check.log.gz').open('wb') as dst:
 with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0) as gz:
  while True:
   chunk=src.read(1024*1024)
   if not chunk:break
   gz.write(chunk)
fresh=[];stale=[];xml_errors=[]
xml_paths=subprocess.check_output(['rg','--files','--hidden','--no-ignore','-g','TEST-*.xml','-g','!.git/**'],cwd=ROOT).decode().splitlines()
for p in sorted(ROOT/x for x in xml_paths):
 if not p.is_file():continue
 s=p.stat();row=file_record(str(p.relative_to(ROOT)))
 if not (build['start_ns']<=s.st_mtime_ns<=build['end_ns']):stale.append(row);continue
 try:
  tree=ET.parse(p).getroot()
  suites=[tree] if tree.tag=='testsuite' else list(tree.iter('testsuite'))
  row.update({k:sum(int(x.attrib.get(k,'0')) for x in suites) for k in ('tests','failures','errors','skipped')})
  row['suites']=[x.attrib.get('name','') for x in suites]
  fresh.append(row)
 except Exception as e:xml_errors.append({'path':str(p.relative_to(ROOT)),'error':str(e)})
totals={k:sum(x[k] for x in fresh) for k in ('tests','failures','errors','skipped')}
text=raw.read_text(errors='replace');error_lines=[line for line in text.splitlines() if '[error]' in line]
summary_lines=[line for line in text.splitlines() if any(s in line for s in ('Total number of tests run:','Tests: succeeded','Total time:','checkProbeInjectFailure'))]
result={'status':'COMPLETE' if build['exit_code']==0 and not deltas and not post['mismatches'] and not xml_errors and all(totals[k]==0 for k in ('failures','errors','skipped')) else 'FAILED','scope':'12D billing execution preparation offline regression gate; no live authorization or compatibility claim','cwd':str(ROOT),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'freeze':str(FREEZE),'freeze_sha256':sha(FREEZE),'java':java,'build':build,'snapshot_files_before':len(a),'snapshot_files_after':len(b),'snapshot_deltas':deltas,'freeze_before':pre,'freeze_after':post,'fresh_xml_count':len(fresh),'stale_xml_count':len(stale),'xml_errors':xml_errors,'test_totals':totals,'raw_log_sha256':sha(raw),'gzip_sha256':sha(OUT/'sbt-check.log.gz'),'gzip_bytes':(OUT/'sbt-check.log.gz').stat().st_size,'error_lines':error_lines,'summary_lines':summary_lines}
write('xml-reports.json',{'gate_start_ns':build['start_ns'],'gate_end_ns':build['end_ns'],'fresh':fresh,'stale':stale,'xml_errors':xml_errors,'totals':totals})
module_log_totals=[int(n) for n in re.findall(r'Total number of tests run: (\d+)',text)]
xml_groups={}
for row in fresh:
 group=row['path'].split('/target/')[0]
 bucket=xml_groups.setdefault(group,{'reports':0,'tests':0,'failures':0,'errors':0,'skipped':0})
 bucket['reports']+=1
 for key in ('tests','failures','errors','skipped'):bucket[key]+=row[key]
result['module_log_test_counts']=module_log_totals
result['module_log_tests_sum']=sum(module_log_totals)
result['module_log_matches_xml']=sum(module_log_totals)==totals['tests']
result['selected_environment']=selected_environment
if not result['module_log_matches_xml']:result['status']='FAILED'
write('xml-groups.json',xml_groups)
write('build-result.json',result)
(OUT/'active-process.json').unlink(missing_ok=True)
print(json.dumps({k:result[k] for k in ('status','head','snapshot_files_before','snapshot_files_after','fresh_xml_count','stale_xml_count','test_totals','raw_log_sha256','gzip_sha256')},indent=2))

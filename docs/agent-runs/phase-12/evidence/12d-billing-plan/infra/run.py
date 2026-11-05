from pathlib import Path
import json,hashlib,subprocess,datetime,time,os,stat,shutil,re
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
OUT=Path('/tmp/scholarchain-phase12d-billing-plan-infra-evidence')
PRIVATE=Path('/tmp/scholarchain-phase12d-billing-plan')
TF='/tmp/scholarchain-phase12b-repair1-infra/terraform'
TFRC='/tmp/scholarchain-phase12b-repair1-infra/terraformrc'
commands=[]

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
 p=OUT/name;p.write_text(json.dumps(data,indent=2)+'\n');p.chmod(0o600)
def run(label,args,cwd,private_output=False):
 start=now();begin=time.monotonic();target=(PRIVATE if private_output else OUT)/(label+'.log.txt')
 fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as stream:
  r=subprocess.run(args,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,env={**os.environ,'TF_CLI_CONFIG_FILE':TFRC})
 rec={'label':label,'argv':args,'cwd':str(cwd),'environment':{'TF_CLI_CONFIG_FILE':TFRC},'started_utc':start,'ended_utc':now(),'wall_seconds':time.monotonic()-begin,'exit_code':r.returncode,'private_output':private_output}
 if private_output:
  rec['log_location']='outside Git and curated evidence: '+str(target)
  rec['diagnostic_policy']='Raw output not returned; private recipient may occur. Only sanitized plan fields are retained.'
 else:rec.update({'log':target.name,'bytes':target.stat().st_size,'sha256':sha(target)})
 commands.append(rec);write('commands.json',commands)
 return rec,target

roots=[('course',ROOT/'infra/terraform'),('billing',ROOT/'infra/terraform/billing-bootstrap'),('proposal',ROOT/'infra/terraform/spikes/emr-spark')]
counts={}
for name,cwd in roots:
 for step,args in [('init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly']),('fmt-check',['fmt','-check','-recursive']),('validate',['validate','-no-color']),('test',['test','-no-color'])]:
  rec,log=run(name+'-'+step,[TF]+args,cwd)
  if rec['exit_code']!=0:
   write('failure.json',{'stage':name+'-'+step,'exit_code':rec['exit_code'],'diagnostic_class':'offline validation failed; see synthetic-only log'})
   raise SystemExit('Offline gate failed: '+name+'-'+step)
  if step=='test':
   text=log.read_text();m=re.search(r'Success!\s+(\d+) passed, (\d+) failed',text);assert m,name
   files=list((cwd/'tests').glob('*.tftest.hcl'));source='\n'.join(p.read_text() for p in files)
   counts[name]={'passed':int(m[1]),'failed':int(m[2]),'runs':len(re.findall(r'^run\s+"',source,re.M)),'assertions':len(re.findall(r'\bassert\s*\{',source)),'expected_failure_runs':len(re.findall(r'\bexpect_failures\s*=',source))}
write('test-counts.json',counts)

assert stat.S_IMODE(PRIVATE.stat().st_mode)==0o700
recipient=PRIVATE/'notification.private.tfvars.json';rs=recipient.lstat();assert stat.S_ISREG(rs.st_mode) and not recipient.is_symlink();assert stat.S_IMODE(rs.st_mode)==0o600
private_before={'mtime_ns':rs.st_mtime_ns,'inode':rs.st_ino,'device':rs.st_dev}
config=PRIVATE/'config';config.mkdir(mode=0o700)
source=ROOT/'infra/terraform/billing-bootstrap';source_records=[]
for p in sorted([*source.glob('*.tf'),source/'.terraform.lock.hcl']):
 shutil.copy2(p,config/p.name);(config/p.name).chmod(0o600)
 source_records.append({'source':str(p.relative_to(ROOT)),'copy':str(config/p.name),'sha256':sha(p),'copy_sha256':sha(config/p.name),'bytes':p.stat().st_size,'source_mtime_ns':p.stat().st_mtime_ns})
assert len(source_records)==5
public=PRIVATE/'public-plan-inputs.tfvars.json';public_data={'aws_account_id':'530332961125','aws_profile':'scholarchain-planner','aws_region':'us-east-2','budget_name':'scholarchain-project-budget','project_period_start_utc':'2026-10-01_00:00','project_period_end_utc':'2027-01-01_00:00','budget_limit_usd':200,'enable_budget':True}
fd=os.open(public,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(public_data,stream,indent=2);stream.write('\n')
write('approved-public-inputs.json',public_data)
rec,log=run('protected-init',[TF,'init','-backend=false','-input=false','-no-color','-lockfile=readonly'],config,True)
if rec['exit_code']!=0:
 write('failure.json',{'stage':'protected-init','exit_code':rec['exit_code'],'diagnostic_class':'protected init failed; raw output withheld'})
 raise SystemExit('Protected init failed; raw output withheld')
plan=PRIVATE/'billing.tfplan'
start_sources={'timestamp':now(),'config':source_records,'public_input_sha256':sha(public),'private_input_stat_only':{'path':str(recipient),'mode':'0600','mtime_ns':rs.st_mtime_ns,'contents_read_or_hashed':False},'prior_state_file_exists':(config/'terraform.tfstate').exists()}
assert not start_sources['prior_state_file_exists']
write('plan-inputs-before.json',start_sources)
rec,log=run('real-plan',[TF,'plan','-input=false','-no-color','-detailed-exitcode','-lock-timeout=30s','-var-file='+str(public),'-var-file='+str(recipient),'-out='+str(plan)],config,True)
if rec['exit_code'] not in (0,2):
 # Classify only established error types; do not expose messages or recipient values.
 text=log.read_text(errors='replace')
 known={'expired_session':'session has expired','access_denied':'AccessDenied','missing_credential':'No valid credential','invalid_time_unit':'time_unit','invalid_argument':'Invalid value for'}
 classes=[k for k,v in known.items() if v in text]
 write('failure.json',{'stage':'real-plan','exit_code':rec['exit_code'],'diagnostic_classes':classes or ['unclassified; private output withheld']})
 print(json.dumps({'plan_exit':rec['exit_code'],'diagnostic_classes':classes or ['unclassified; private output withheld']}))
 raise SystemExit(1)
plan.chmod(0o600)
json_path=PRIVATE/'billing.plan.json';fd=os.open(json_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as stream:
 started=now();begin=time.monotonic();r=subprocess.run([TF,'show','-json',str(plan)],cwd=config,stdout=stream,stderr=subprocess.PIPE,env={**os.environ,'TF_CLI_CONFIG_FILE':TFRC})
 show={'label':'show-json','argv':[TF,'show','-json',str(plan)],'cwd':str(config),'environment':{'TF_CLI_CONFIG_FILE':TFRC},'started_utc':started,'ended_utc':now(),'wall_seconds':time.monotonic()-begin,'exit_code':r.returncode,'private_output':True,'output_location':'outside Git and curated evidence: '+str(json_path)}
 commands.append(show);write('commands.json',commands)
 if r.returncode:
  (PRIVATE/'show-json.stderr.log.txt').write_bytes(r.stderr);(PRIVATE/'show-json.stderr.log.txt').chmod(0o600)
  write('failure.json',{'stage':'show-json','exit_code':r.returncode,'diagnostic_class':'show JSON failed; private stderr withheld'})
  raise SystemExit('Show JSON failed')
# Parse only selected plan properties; never persist variables, output controls or recipient strings.
data=json.loads(json_path.read_text());changes=data.get('resource_changes',[])
summary_changes=[];adds=updates=deletes=replaces=0
for c in changes:
 actions=c['change']['actions'];adds+=int('create' in actions);updates+=int('update' in actions);deletes+=int('delete' in actions);replaces+=int('create' in actions and 'delete' in actions)
 summary_changes.append({'address':c['address'],'type':c['type'],'actions':actions})
assert deletes==0 and replaces==0,'Unexpected destroy/replacement; stop without apply'
assert len(changes)==1 and changes[0]['type']=='aws_budgets_budget','Unexpected resource scope'
a=changes[0]['change']['after'];notifications=[]
for n in a.get('notification',[]):
 notifications.append({'comparison':n['comparison_operator'],'threshold':n['threshold'],'threshold_type':n['threshold_type'],'notification_type':n['notification_type'],'subscriber_count':len(n.get('subscriber_email_addresses',[])),'sns_subscriber_count':len(n.get('subscriber_sns_topic_arns',[]))})
summary={'plan_created_at':now(),'terraform_version':data['terraform_version'],'plan_exit_code':rec['exit_code'],'plan_path':str(plan),'plan_sha256':sha(plan),'plan_bytes':plan.stat().st_size,'counts':{'add':adds,'change':updates,'destroy':deletes,'replace':replaces},'resources':summary_changes,'budget':{k:a.get(k) for k in ['account_id','name','budget_type','limit_amount','limit_unit','time_unit','time_period_start','time_period_end','cost_types','cost_filter','filter_expression','tags']},'notifications':sorted(notifications,key=lambda n:n['threshold']),'private_recipient_values_retained':False,'private_input_contents_read_or_hashed':False,'prior_state_resource_count':len(data.get('prior_state',{}).get('values',{}).get('root_module',{}).get('resources',[])),'state_file_exists_after_plan':(config/'terraform.tfstate').exists(),'applied':False}
write('plan-summary.json',summary)
after=[]
for r in source_records:
 p=ROOT/r['source'];copy=Path(r['copy']);assert sha(p)==r['sha256'] and sha(copy)==r['sha256'];after.append({'source':r['source'],'sha256':sha(p),'copy_sha256':sha(copy),'source_mtime_ns':p.stat().st_mtime_ns,'source_unchanged':p.stat().st_mtime_ns==r['source_mtime_ns']})
rs2=recipient.lstat();assert {'mtime_ns':rs2.st_mtime_ns,'inode':rs2.st_ino,'device':rs2.st_dev}==private_before
write('plan-inputs-after.json',{'timestamp':now(),'config':after,'public_input_sha256':sha(public),'private_input_stat_unchanged':True,'private_input_contents_read_or_hashed':False})
# Make a final source inventory and prove only the assigned README changed.
before=json.loads((OUT/'source-before.json').read_text());all_after=[];delta=[]
for r in before['files']:
 p=ROOT/r['path'];s=p.stat();record={'path':r['path'],'sha256':sha(p),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns};all_after.append(record)
 if record['sha256']!=r['sha256']:delta.append(r['path'])
assert delta==['infra/terraform/billing-bootstrap/README.md'],delta
write('source-after.json',{'timestamp':now(),'files':all_after,'changed':delta})
print(json.dumps({'native_passed':sum(x['passed'] for x in counts.values()),'native_failed':sum(x['failed'] for x in counts.values()),'plan_exit':rec['exit_code'],'counts':summary['counts'],'plan_sha256':summary['plan_sha256'],'private_recipient_logged':False,'source_delta':delta}))

from pathlib import Path
import json, hashlib, subprocess, datetime, time, os, stat, re, sys
BASE=Path('/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap')
SAFE=Path('/tmp/scholarchain-phase12d-billing-durable-plan-handoff/safe'); CONFIG=BASE/'config'; ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
TF='/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/toolchain/terraform-1.13.5'; TFRC='/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/toolchain/terraform.tfrc'
os.umask(0o077)

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):
 p.write_text(json.dumps(data,indent=2)+'\n');p.chmod(0o600)
commands=json.loads((SAFE/'commands.json').read_text()) if (SAFE/'commands.json').exists() else []
common={'HOME':'/Users/danny','PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','TF_CLI_CONFIG_FILE':TFRC,'TF_IN_AUTOMATION':'1','AWS_EC2_METADATA_DISABLED':'true','AWS_PAGER':''}
offline={**common,'AWS_CONFIG_FILE':'/dev/null','AWS_SHARED_CREDENTIALS_FILE':'/dev/null','TF_DATA_DIR':str(BASE/'offline-tf-data')}
live={**common,'AWS_PROFILE':'scholarchain-billing-deployer','AWS_REGION':'us-east-2','AWS_DEFAULT_REGION':'us-east-2','AWS_SDK_LOAD_CONFIG':'1','TF_DATA_DIR':str(BASE/'tf-data')}

def run(label,args,env,private=False,separate_stdout=None):
 path=(BASE if private else SAFE)/(label+'.log.txt')
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 started=now();begin=time.monotonic()
 with os.fdopen(fd,'wb') as log:
  if separate_stdout:
   outfd=os.open(separate_stdout,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   with os.fdopen(outfd,'wb') as out:
    r=subprocess.run(args,cwd=CONFIG,env=env,stdout=out,stderr=log)
  else:r=subprocess.run(args,cwd=CONFIG,env=env,stdout=log,stderr=subprocess.STDOUT)
 rec={'label':label,'argv':args,'cwd':str(CONFIG),'environment':env,'started_utc':started,'ended_utc':now(),'wall_seconds':time.monotonic()-begin,'exit_code':r.returncode,'log':str(path),'log_sha256':sha(path),'log_bytes':path.stat().st_size,'raw_private':private}
 if separate_stdout:rec['protected_stdout_path']=str(separate_stdout)
 commands.append(rec);write(SAFE/'commands.json',commands)
 return r.returncode,path

def verify_sources():
 records=json.loads((SAFE/'config-provenance-before.json').read_text())['files'];after=[]
 for rec in records:
  source=ROOT/rec['source'];copy=BASE/rec['copy_relative']
  assert sha(source)==rec['sha256'] and source.stat().st_size==rec['bytes'] and source.stat().st_mtime_ns==rec['mtime_ns']
  assert sha(copy)==rec['sha256']
  after.append({'source':rec['source'],'sha256':sha(source),'bytes':source.stat().st_size,'mtime_ns':source.stat().st_mtime_ns,'copy_sha256':sha(copy)})
 return after

def offline_gates(suffix=""):

 verify_sources();counts={}
 for label,args in [('offline-init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly']),('offline-fmt-check',['fmt','-check','-recursive']),('offline-validate',['validate','-no-color']),('offline-test',['test','-no-color'])]:
  code,log=run(label+suffix,[TF]+args,offline)
  if code:raise RuntimeError(label)
  if label=='offline-test':
   text=log.read_text();m=re.search(r'Success!\s+(\d+) passed, (\d+) failed',text);assert m
   src='\n'.join(p.read_text() for p in (CONFIG/'tests').glob('*.tftest.hcl'))
   counts={'passed':int(m[1]),'failed':int(m[2]),'runs':len(re.findall(r'^run\s+"',src,re.M)),'assertions':len(re.findall(r'\bassert\s*\{',src)),'expected_failure_runs':len(re.findall(r'\bexpect_failures\s*=',src))}
 write(SAFE/'test-counts.json',counts);write(SAFE/'config-provenance-after-offline.json',{'timestamp_utc':now(),'files':verify_sources()})
 print(json.dumps({'offline_complete':True,'counts':counts}))

def plan():
 assert stat.S_IMODE(BASE.stat().st_mode)==0o700
 recipient=BASE/'notification.private.tfvars.json';s=recipient.lstat();assert stat.S_ISREG(s.st_mode) and not recipient.is_symlink() and stat.S_IMODE(s.st_mode)==0o600 and s.st_uid==os.getuid()
 meta={k:getattr(s,k) for k in ['st_ino','st_dev','st_mtime_ns']}
 state=BASE/'billing.execution.tfstate';plan=BASE/'billing.execution.tfplan';planjson=BASE/'billing.execution.plan.json'
 assert not state.exists() and not plan.exists() and not planjson.exists()
 before={'timestamp_utc':now(),'config':verify_sources(),'public_input_sha256':sha(BASE/'approved-public-inputs.tfvars.json'),'private_input_metadata_only':{'path':str(recipient),'mode':'0600','present':True,'contents_read_or_hashed':False},'local_state_path':str(state),'local_state_existed':False,'existing_remote_budget_inventory':'not queried; fresh local state does not establish budget absence'}
 write(SAFE/'plan-inputs-before.json',before)
 for label,args in [('protected-init',['init','-backend=false','-input=false','-no-color','-lockfile=readonly']),('real-plan',['plan','-input=false','-no-color','-detailed-exitcode','-lock-timeout=30s','-state='+str(state),'-var-file='+str(BASE/'approved-public-inputs.tfvars.json'),'-var-file='+str(recipient),'-out='+str(plan)])]:
  code,log=run(label,[TF]+args,live,True)
  if code not in ((0,2) if label=='real-plan' else (0,)):
   text=log.read_text(errors='replace')
   markers={'expired_session':['session has expired','ExpiredToken','expired token'],'access_denied':['AccessDenied','Access Denied','not authorized'],'missing_credentials':['No valid credential','failed to refresh cached credentials'],'name_conflict':['DuplicateRecordException','already exists'],'network_or_provider':['failed to query','Failed to query','could not connect'],'invalid_input':['Invalid value for','InvalidParameter']}
   classes=[k for k,v in markers.items() if any(m.lower() in text.lower() for m in v)]
   write(SAFE/'failure.json',{'stage':label,'exit_code':code,'diagnostic_classes':classes or ['unclassified; private diagnostic withheld'],'no_retry_or_policy_widening':True})
   print(json.dumps({'stopped':True,'stage':label,'exit_code':code,'diagnostic_classes':classes or ['unclassified; private diagnostic withheld']}));return
 plan_exit=code
 assert plan_exit==2
 assert stat.S_IMODE(plan.stat().st_mode)==0o600
 code,log=run('protected-show',[TF,'show','-json',str(plan)],live,True,planjson)
 if code:raise RuntimeError('protected-show')
 data=json.loads(planjson.read_text());changes=data.get('resource_changes',[])
 count={k:0 for k in ['add','change','destroy','replace']};resources=[]
 for c in changes:
  actions=c['change']['actions'];count['add']+=int('create' in actions);count['change']+=int('update' in actions);count['destroy']+=int('delete' in actions);count['replace']+=int('create' in actions and 'delete' in actions);resources.append({'address':c['address'],'type':c['type'],'actions':actions})
 assert count=={'add':1,'change':0,'destroy':0,'replace':0}
 assert len(changes)==1 and changes[0]['address']=='aws_budgets_budget.project[0]' and changes[0]['change']['actions']==['create']
 a=changes[0]['change']['after'];notifications=[]
 for n in a.get('notification',[]):
  notifications.append({'comparison':n['comparison_operator'],'threshold':n['threshold'],'threshold_type':n['threshold_type'],'notification_type':n['notification_type'],'subscriber_count':len(n.get('subscriber_email_addresses',[])),'sns_subscriber_count':len(n.get('subscriber_sns_topic_arns',[]))})
 budget={k:a.get(k) for k in ['account_id','name','budget_type','limit_amount','limit_unit','time_unit','time_period_start','time_period_end','cost_types','cost_filter','filter_expression','tags']}
 assert budget['account_id']=='530332961125' and budget['name']=='scholarchain-project-budget' and float(budget['limit_amount'])==200 and budget['limit_unit']=='USD' and budget['time_unit']=='CUSTOM' and budget['budget_type']=='COST'
 assert budget['time_period_start']=='2026-10-01_00:00' and budget['time_period_end']=='2027-01-01_00:00'
 assert budget['tags']=={'course':'CS441','project':'scholarchain','environment':'course','owner':'danny','expiration_date':'2027-01-01'}
 assert not budget['cost_filter'] and not budget['filter_expression']
 assert len(notifications)==3 and sorted(n['threshold'] for n in notifications)==[50,80,100] and all(n['subscriber_count']==1 and n['sns_subscriber_count']==0 and n['comparison']=='GREATER_THAN' and n['threshold_type']=='PERCENTAGE' and n['notification_type']=='ACTUAL' for n in notifications)
 assert budget['cost_types'][0]['include_credit']==False and budget['cost_types'][0]['include_refund']==False
 # Compare plan-derived subscriber values in-process only. Never read private input.
 subscribers={v for n in a.get('notification',[]) for v in n.get('subscriber_email_addresses',[])}
 assert len(subscribers)==1 and all(isinstance(v,str) and v for v in subscribers)
 gitpaths=subprocess.run(['/usr/bin/git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT,env={'HOME':'/Users/danny','PATH':'/usr/bin:/bin'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.split(b'\0')
 matches=[];scanned=0;excluded=0
 for raw in sorted(set(gitpaths)):
  if not raw:continue
  rel=Path(os.fsdecode(raw));parts=[v.lower() for v in rel.parts]
  deny=any(v in {'.git','.aws','.ssh','.codex','.agents','.env','node_modules','target'} or v.startswith('.env.') or 'credential' in v or v in {'secrets','secret','private-keys'} for v in parts)
  allow=rel.parts[0] in {'docs','infra'} and rel.suffix.lower() in {'.md','.json','.txt','.tf','.hcl','.py','.sh','.csv','.log'}
  target=ROOT/rel
  if deny or not allow or target.is_symlink() or not target.is_file():excluded+=1;continue
  content=target.read_bytes();scanned+=1
  if any(v.encode() in content for v in subscribers):matches.append(str(rel))
 write(SAFE/'recipient-privacy-scan.json',{'timestamp_utc':now(),'scope':'Git-visible docs/ and infra/ public text, including all current phase evidence; excluded credentials/secrets/environment/private-key directories and binary/other source paths. Does not read private input.','files_scanned':scanned,'paths_excluded':excluded,'matching_file_count':len(matches),'matching_filenames':matches,'recipient_source':'new protected plan JSON notification subscribers, in-process only; no address values or private-value hashes returned','known_public_fixture':'synthetic@example.invalid in unchanged mock tests is a public fixture, not considered recipient absent proof by itself','private_input_contents_read_or_hashed':False})
 assert not matches
 summary={'sanitized_at_utc':now(),'terraform_version':data['terraform_version'],'plan_exit_code':plan_exit,'plan_path':str(plan),'plan_sha256':sha(plan),'plan_bytes':plan.stat().st_size,'counts':count,'resources':resources,'budget':budget,'notifications':sorted(notifications,key=lambda n:n['threshold']),'privacy':{'raw_plan_json_retained_outside_git':True,'private_recipient_values_retained_in_safe_summary':False,'private_input_contents_read_or_hashed':False,'plan_and_raw_logs_can_contain_recipient':True},'provider_identity':'provider allowed_account_ids pins account; profile supplied; user separately verified exact billing assumed-role ARN before this work; no standalone identity call repeated','remote_budget_absence_verified':False,'fresh_local_state_does_not_prove_remote_absence':True,'local_state_file_exists_after_plan':state.exists(),'applied':False}
 write(SAFE/'plan-summary.json',summary)
 assert {k:getattr(recipient.lstat(),k) for k in meta}==meta
 write(SAFE/'plan-inputs-after.json',{'timestamp_utc':now(),'config':verify_sources(),'public_input_sha256':sha(BASE/'approved-public-inputs.tfvars.json'),'private_input_metadata_unchanged':True,'private_input_contents_read_or_hashed':False})
 write(SAFE/'safe-summary-validation.json',{'exactly_one_budget_create':True,'no_replacement_or_destruction':True,'approved_account_name_amount_dates_tags':True,'three_exact_actual_thresholds':True,'one_private_email_each_count_only':True,'no_filters':True,'credit_refund_excluded_in_authored_plan':True,'live_service_cost_type_tags_acceptance':'unverified until separately approved apply/readback','existing_remote_monitor_conflict':'unverified; no API inventory authorized','raw_plan_variables_outputs_and_recipient_strings_excluded':True})
 print(json.dumps({'plan_complete':True,'plan_exit_code':plan_exit,'counts':count,'plan_sha256':sha(plan),'private_output_withheld':True}))

if __name__=='__main__':
 try:
  if sys.argv[1:] == ['offline']:offline_gates()
  elif sys.argv[1:] == ['offline-retry']:offline_gates('-retry')
  elif sys.argv[1:] == ['plan']:plan()
  else:raise RuntimeError('Select offline or plan')
 except Exception as exc:
  write(SAFE/'runner-failure.json',{'type':type(exc).__name__,'details':'withheld to avoid protected data exposure','timestamp_utc':now(),'stop':True})
  print(json.dumps({'stopped':True,'exception_class':type(exc).__name__,'private_diagnostics_withheld':True}));sys.exit(1)

from pathlib import Path
import datetime,subprocess,hashlib,json,time,urllib.request,re
O=Path('/tmp/scholarchain-phase12d-login-eval-infra');ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
def sha(b):return hashlib.sha256(b).hexdigest()
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,d):(O/n).write_text(json.dumps(d,indent=2)+'\n')
commands=[]
def run(label,argv,env):
 st=stamp();t=time.monotonic();p=subprocess.run(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=label+'.log.txt';(O/log).write_bytes(p.stdout);commands.append({'label':label,'argv':argv,'cwd':str(ROOT),'environment':env,'started_utc':st,'ended_utc':stamp(),'wall_seconds':round(time.monotonic()-t,6),'exit_code':p.returncode,'log':log,'sha256':sha(p.stdout),'bytes':len(p.stdout)});save('commands.json',commands)
 return p
clean={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','LANG':'C','AWS_CONFIG_FILE':'/dev/null','AWS_SHARED_CREDENTIALS_FILE':'/dev/null','AWS_EC2_METADATA_DISABLED':'true','AWS_CLI_AUTO_PROMPT':'off','AWS_PAGER':'','PAGER':'cat'}
run('cli-version',['/opt/homebrew/bin/aws','--version'],clean)
run('cli-login-help',['/opt/homebrew/bin/aws','login','help'],clean)
run('cli-assume-role-help',['/opt/homebrew/bin/aws','sts','assume-role','help'],clean)
urls={
'cli-login':'https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html',
'cli-login-reference':'https://docs.aws.amazon.com/cli/latest/reference/login/',
'cli-login-troubleshooting':'https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in-troubleshoot.html',
'iam-condition-keys':'https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html',
'iam-console-switch':'https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html',
'iam-mfa-api':'https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_configure-api-require.html',
'sts-assume-role':'https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html',
'sts-get-session-token':'https://docs.aws.amazon.com/STS/latest/APIReference/API_GetSessionToken.html',
'signin-actions':'https://docs.aws.amazon.com/service-authorization/latest/reference/list_signin.html',
'signin-managed-policy':'https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SignInLocalDevelopmentAccess.html',
'startup-short-lived':'https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-startup-security-baseline/acct-13.html',
'provider-go-mod':'https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/v6.44.0/go.mod',
'cli-public-login-utils':'https://raw.githubusercontent.com/aws/aws-cli/2.35.4/awscli/customizations/login/utils.py',
'cli-public-credentials':'https://raw.githubusercontent.com/aws/aws-cli/2.35.4/awscli/botocore/credentials.py'}
references=[]
for name,url in urls.items():
 row={'name':name,'url':url,'checked_utc':stamp()}
 try:
  with urllib.request.urlopen(url,timeout=25) as h:b=h.read();row.update({'http_status':h.status,'resolved_url':h.url,'bytes':len(b),'sha256':sha(b)})
  if name=='provider-go-mod':(O/'provider-go.mod.txt').write_bytes(b);row['retained_as']='provider-go.mod.txt'
  else:row['retained_as']=None;row['retention']='Digest-only reference; no full documentation page retained.'
 except Exception as e:row['error']=str(e)
 references.append(row);save('public-references.json',references)
installed=Path('/opt/homebrew/Cellar/awscli/2.35.4/libexec/lib/python3.14/site-packages')
extracts=[]
for rel,ranges in [('awscli/customizations/login/login.py',[(34,61),(175,203)]),('awscli/customizations/login/utils.py',[(34,45),(127,153),(179,197)]),('awscli/botocore/credentials.py',[(1628,1676),(1804,1846),(2647,2697)])]:
 p=installed/rel;b=p.read_bytes();lines=b.decode().splitlines();chunks=[]
 for start,end in ranges:chunks+=['\n# Source lines '+str(start)+'-'+str(end)]+[f'{i+1}: {lines[i]}' for i in range(start-1,min(end,len(lines))) ]
 name=p.name+'.source-extract.txt';(O/name).write_text('\n'.join(chunks)+'\n');extracts.append({'installed_source':str(p),'original_bytes':len(b),'original_sha256':sha(b),'ranges':ranges,'retained_as':name,'retained_sha256':sha((O/name).read_bytes())})
save('installed-source-provenance.json',extracts)
print(json.dumps({'commands':[(c['label'],c['exit_code']) for c in commands],'public_references':len(references),'fetch_errors':[{r['name']:r['error']} for r in references if 'error' in r]},indent=2))

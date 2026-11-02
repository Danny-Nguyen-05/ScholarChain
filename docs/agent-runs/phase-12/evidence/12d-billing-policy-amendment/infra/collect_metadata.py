from pathlib import Path
import json,re,difflib,hashlib
R=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');O=Path('/tmp/scholarchain-phase12d-policy-amendment-infra');S=R/'infra/terraform/billing-execution'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[];patch=[]
for f in json.loads((O/'pre-edit-source.json').read_text())['files']:
 p=R/f['path'];old=O/f['retained_before'];assert sha(old)==f['sha256'];rows.append({'path':f['path'],'before_sha256':f['sha256'],'after_sha256':sha(p),'changed':sha(p)!=f['sha256']})
 if sha(p)!=f['sha256']:patch.extend(difflib.unified_diff(old.read_text().splitlines(keepends=True),p.read_text().splitlines(keepends=True),fromfile='a/'+f['path'],tofile='b/'+f['path']))
(O/'delta.patch').write_text(''.join(patch));(O/'source-delta.json').write_text(json.dumps(rows,indent=2)+'\n')
def block(s,name):
 m=re.search(r'\b'+re.escape(name)+r'\s*=',s);assert m;start=m.start();pos=s.index('{',start);level=0
 for i in range(pos,len(s)):
  if s[i]=='{':level+=1
  if s[i]=='}':
   level-=1
   if level==0:return s[start:i+1]
 raise AssertionError(name)
a=(O/'before/main.tf').read_text();b=(S/'main.tf').read_text();blocks=[]
for n in ['execution_policy','trust_policy','caller_policy']:
 before=block(a,n);after=block(b,n);assert before==after,n;blocks.append({'block':n,'byte_identical':True,'sha256':hashlib.sha256(before.encode()).hexdigest()})
(O/'preserved-policy-blocks.json').write_text(json.dumps(blocks,indent=2)+'\n')
summary={}
for label,d in [('course',R/'infra/terraform'),('billing',R/'infra/terraform/billing-bootstrap'),('proposal',R/'infra/terraform/spikes/emr-spark'),('execution',S)]:
 text='\n'.join(p.read_text() for p in sorted((d/'tests').glob('*.tftest.hcl')));summary[label]={'runs':len(re.findall(r'^run\s+"',text,re.M)),'assertions':len(re.findall(r'^\s*assert\s*{',text,re.M)),'expected_failure_runs':len(re.findall(r'^\s*expect_failures\s*=',text,re.M))}
summary['total']={k:sum(x[k] for x in summary.values()) for k in ('runs','assertions','expected_failure_runs')}
summary['toolchain']={'path':'/tmp/scholarchain-phase12b-repair1-infra/terraform','sha256':sha(Path('/tmp/scholarchain-phase12b-repair1-infra/terraform')),'reinstalled':False}
summary['source_changed_paths']=[x['path'] for x in rows if x['changed']]
summary['source_inspection']={'files':[str(x.relative_to(R)) for x in S.glob('*.tf')],'forbidden_blocks':[],'basis':'Source inspection, not output constants'}
for p in S.glob('*.tf'):assert not re.search(r'^\s*(resource|data|provider|module|provisioner)\s+["{]',p.read_text(),re.M)
cmd=json.loads((O/'commands.json').read_text());summary['commands']=len(cmd);summary['unexpected_native_failures']=[c['label'] for c in cmd if c['exit_code']!=0 and not c['label'].startswith('red-')]
summary['final_results']={k:re.findall('Success!.*',(O/(k+'-test.log.txt')).read_text())[-1] for k in ('course','billing','proposal','execution')};summary['red']={k:{f:v for f,v in json.loads((O/n).read_text()).items() if f in ('test_result','assertion_lines','repository_unchanged','init_exit','test_exit')} for k,n in [('login','red-proof.json'),('E1','red-e1-proof.json')]}
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
refs=[{'url':'https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SignInLocalDevelopmentAccess.html','checked':'2026-10-31','use':'v3 two Sign-In actions on public-client resources; narrowed pattern remains live-unverified'},{'url':'https://docs.aws.amazon.com/service-authorization/latest/reference/list_signin.html','checked':'2026-10-31','use':'Localhost resource and OAuthClientId condition; console resource also listed, no automatic widening'},{'url':'https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html','checked':'2026-10-31','use':'Role-selected session, same-device scope and session duration; full composition remains inference'}]
(O/'public-references.json').write_text(json.dumps(refs,indent=2)+'\n');print(json.dumps({'total':summary['total'],'commands':len(cmd),'final_results':summary['final_results'],'red':summary['red'],'preserved_blocks':blocks},indent=2))

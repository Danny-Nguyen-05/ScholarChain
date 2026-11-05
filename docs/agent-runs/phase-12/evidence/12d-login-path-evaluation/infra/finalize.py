from pathlib import Path
import json,hashlib,datetime,subprocess,time
O=Path('/tmp/scholarchain-phase12d-login-eval-infra');ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
def sha(b):return hashlib.sha256(b).hexdigest()
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
cmds=json.loads((O/'commands.json').read_text());clean=cmds[0]['environment'];start=stamp();t=time.monotonic();argv=['/opt/homebrew/bin/aws','configure','export-credentials','help'];p=subprocess.run(argv,cwd=ROOT,env=clean,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);name='cli-export-credentials-help.log.txt';(O/name).write_bytes(p.stdout);cmds.append({'label':'cli-export-credentials-help','argv':argv,'cwd':str(ROOT),'environment':clean,'started_utc':start,'ended_utc':stamp(),'wall_seconds':round(time.monotonic()-t,6),'exit_code':p.returncode,'log':name,'sha256':sha(p.stdout),'bytes':len(p.stdout)});(O/'commands.json').write_text(json.dumps(cmds,indent=2)+'\n')
# Add exact source ranges needed for the resolver/MFA implementation evidence.
p=Path('/opt/homebrew/Cellar/awscli/2.35.4/libexec/lib/python3.14/site-packages/awscli/botocore/credentials.py');b=p.read_bytes();lines=b.decode().splitlines();ranges=[(202,213),(260,270),(915,933),(1638,1671),(1806,1838)]
(O/'cli-resolver.source-extract.txt').write_text('\n'.join(f'{i+1}: {lines[i]}' for a,z in ranges for i in range(a-1,z))+'\n')
prov=json.loads((O/'installed-source-provenance.json').read_text());prov.append({'installed_source':str(p),'original_bytes':len(b),'original_sha256':sha(b),'ranges':ranges,'retained_as':'cli-resolver.source-extract.txt','retained_sha256':sha((O/'cli-resolver.source-extract.txt').read_bytes())});(O/'installed-source-provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
F=ROOT/'docs/agent-runs/phase-12/evidence/12d-billing-execution-prep/source-freeze.json';freeze=json.loads(F.read_text());bad=[]
for f in freeze['files']:
 q=ROOT/f['path'];s=q.stat()
 if sha(q.read_bytes())!=f['sha256'] or s.st_size!=f['bytes'] or s.st_mtime_ns!=f['mtime_ns']:bad.append(f['path'])
assert not bad
report='''STATUS: COMPLETE — offline login evaluation; all account and security gates remain unrun.
OWNER: infra-engineer, /root/infra_12d_login_evaluation.
WORK ORDER: Evaluate recommended browser-login path with temporary credentials for a distinct proposed scholarchain-billing-operator; no source/account actions. Base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f.
FILES CREATED: Scratch-only curated evaluation, public-source references/digests, pinned SDK/provider sources, installed CLI source excerpts, four help/version command logs and artifact manifest under /tmp/scholarchain-phase12d-login-eval-infra/.
FILES MODIFIED: None in repository. E1 deferred to next actual source amendment.
COMMANDS RUN: Four recorded CLI help/version commands in sanitized environment with AWS config/shared-credentials paths /dev/null, metadata disabled and no secrets/environment dump. No login command without help; no AWS/account endpoint request. Read-only source inspection and public primary documentation/source fetches; fetch digests and errors retained in public-references.json. Exact command argv/cwd/times/env/exits/hashes in commands.json.
TEST RESULTS: No Terraform, application or build tests run; behavior unchanged. All four local help/version commands exit 0. No live IAM/MFA/Sign-In proof claimed. Prior tests are historical and not presented as new passes.
VALIDATION RESULTS: Installed AWS CLI 2.35.4; local login help explicitly illustrates assumed-role login. Pinned provider sources show native login support and the separate MFA-token callback requirement. Current SignInLocalDevelopmentAccess v3 has TWO actions, AuthorizeOAuth2Access plus CreateOAuth2Token; exact localhost scoping documented. All 209 previously frozen files still match hash/bytes/mtime. Public source request failures are disclosed, not passes.
ASSUMPTIONS: Published primary documentation/pinned source describe intended behavior. Composition of console MFA switch and selected-role login is inferred from documented components; actual account support, authorization, expiry and native SDK cache interoperability still need live proof after separate authorization.
RISKS: Operator does not exist or is unverified; actual identity ARN unset. Browser IAM-user token MFA propagation remains unproven. Candidate B requires a separately reviewed two-action Sign-In grant on the billing role. Candidate A requires a separately reviewed CLI credential-process bridge and careful MFA/cache expiry handling. No fallback, exception, grant or spending inferred. ModifyBudget remains coarse; sessions/alerts do not cap spending.
MANUAL ACTION REQUIRED: Human selects the next bounded offline amendment (recommend candidate B). After independent review, human personally records any bootstrap exception and authorizes identity establishment; separately authorize login/identity proof, fresh billing plan, review and apply. Never elevate planner or create root/long-lived keys.
BLOCKED-ON OWNER: None for evaluation; human architect for design choice and future IAM/console/live authorizations; infra-engineer for any selected source amendment and E1.
BLOCKED-ON EVIDENCE: No actual operator/role/login, live strict-MFA boundary evidence, exact installed login grant, execution plan, active budget, delivery or usable cost data. Every live EMR prerequisite remains open.
NEXT GATE: Coordinator assembles evaluation for independent read-only review and obtains the next bounded work order; no source edits, IAM creation, plan/apply, paid work or Phase 13 automatically follows.
'''
(O/'owner-report.txt').write_text(report)
(O/'validation.json').write_text(json.dumps({'timestamp':stamp(),'local_commands':len(cmds),'all_help_version_exit_zero':all(x['exit_code']==0 for x in cmds),'freeze_files':len(freeze['files']),'freeze_sha256':sha(F.read_bytes()),'freeze_mismatches':bad,'source_edits':[],'account_calls':0,'public_fetch_errors':[{'name':x['name'],'error':x['error']} for x in json.loads((O/'public-references.json').read_text()) if 'error'in x]},indent=2)+'\n')
manifest=[]
for q in sorted(O.iterdir()):
 if q.is_file() and q.name!='artifact-manifest.json':manifest.append({'path':q.name,'sha256':sha(q.read_bytes()),'bytes':q.stat().st_size})
(O/'artifact-manifest.json').write_text(json.dumps({'artifacts':manifest},indent=2)+'\n');print(json.dumps({'artifacts':len(manifest),'help_commands':len(cmds),'freeze_mismatches':bad,'public_errors':[x['name'] for x in json.loads((O/'public-references.json').read_text()) if 'error'in x]},indent=2))

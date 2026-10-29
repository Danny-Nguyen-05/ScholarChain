from pathlib import Path
import subprocess,json,hashlib,gzip,datetime
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');OUT=ROOT/'docs/agent-runs/phase-12/evidence/12b-repair-1';BASE='a83f62e9af56058a170075f98c4e027d039567ec'
def sha(raw):return hashlib.sha256(raw).hexdigest()
baseline=json.loads((OUT/'preflight-and-baseline.json').read_text())['files']
append_paths={'docs/agent-runs/phase-12/'+name for name in ['review.md','repairs.md','owner-report.md','test-report.md']}
expected={'infra/terraform/README.md','infra/terraform/modules/identity/main.tf','infra/terraform/tests/phase12b.tftest.hcl'}
changed=[];errors=[];prefixes=[];packet_count=0
for name,v in baseline.items():
 p=ROOT/name
 if not p.is_file():errors.append(name);continue
 raw=p.read_bytes();h=sha(raw)
 if name in append_paths:
  if sha(raw[:v['bytes']])!=v['sha256']:errors.append(name)
  else:prefixes.append(name)
 elif name.startswith('infra/terraform/'):
  if h!=v['sha256']:changed.append(name)
 elif h!=v['sha256']:errors.append(name)
 if name.startswith('docs/agent-runs/phase-12/evidence/12b/'):packet_count+=1
assert set(changed)==expected,changed
assert not errors,errors
freeze=json.loads((OUT/'infra-source-freeze.json').read_text());freeze_errors=[]
for name,v in freeze['files'].items():
 p=ROOT/name;st=p.stat()
 if sha(p.read_bytes())!=v['sha256'] or st.st_size!=v['bytes'] or st.st_mtime_ns!=v['mtime_ns']:freeze_errors.append(name)
assert not freeze_errors,freeze_errors
noninfra=json.loads((ROOT/'docs/agent-runs/phase-12/evidence/12b/non-infra-source-baseline.json').read_text())['files'];noninfra_errors=[name for name,h in noninfra.items() if sha((ROOT/name).read_bytes())!=h];assert not noninfra_errors,noninfra_errors
tracked=subprocess.check_output(['git','diff','--name-only',BASE],cwd=ROOT,text=True).splitlines();new=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines();outside=[x for x in tracked+new if not x.startswith(('infra/terraform/','docs/agent-runs/phase-12/'))];assert not outside,outside
human=[x for x in tracked+new if Path(x).name in ['human-gate.md','commit.txt','accepted-commit.md'] or 'approval' in Path(x).name.lower()];assert not human,human
new_since_repair=[x for x in tracked+new if x not in baseline and not x.startswith('docs/agent-runs/phase-12/evidence/12b-repair-1/') and x!='docs/agent-runs/phase-12/reviewer-prompt-12b-recheck-1.md'];assert not new_since_repair,new_since_repair
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert branch=='phase-12' and head==BASE
ret=json.loads((OUT/'infra-retention-validation.json').read_text())
for r in ret['records']:assert sha((ROOT/r['retained_path']).read_bytes())==r['sha256'],r['retained_path']
summary={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_sha':BASE,'branch':branch,'head':head,'repair_changed_infra_paths':sorted(changed),'new_infra_files':0,'all_frozen_source_hash_bytes_mtime_match':not freeze_errors,'frozen_file_count':len(freeze['files']),'pre_repair_baseline_count':len(baseline),'preservation_errors':errors,'append_only_prefixes_preserved':prefixes,'prior_12b_evidence_files_preserved':packet_count,'noninfra_source_files_unchanged':len(noninfra),'out_of_scope_paths':outside,'human_owned_changed_paths':human,'tracked_changed_count':len(tracked),'untracked_count':len(new),'infra_artifacts_checked':ret['artifact_count'],'native_command_logs_checked':ret['command_log_count']}
if (OUT/'build-validation.json').exists():
 b=json.loads((OUT/'build-validation.json').read_text());raw=gzip.decompress((OUT/'sbt-check.log.gz').read_bytes());assert sha(raw)==b['log_sha256'];summary['build']={k:b[k] for k in ['gate_exit_code','counts','xml_report_count','fresh_xml_report_count','source_unchanged','all_snapshot_file_count','start_after_freeze','start_after_all_source_mtimes','xml_log_count_agrees','log_sha256']};assert b['gate_exit_code']==0 and b['source_unchanged'] and b['all_xml_fresh'] and b['xml_log_count_agrees']
(OUT/'coordinator-final-validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

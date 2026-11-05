from pathlib import Path
import datetime,hashlib,json,subprocess,gzip
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
EVIDENCE=ROOT/'docs/agent-runs/phase-12/evidence/12b'
BASE='a83f62e9af56058a170075f98c4e027d039567ec'
def sha(raw):return hashlib.sha256(raw).hexdigest()
noninfra=json.loads((EVIDENCE/'non-infra-source-baseline.json').read_text())['files']
changed_noninfra=[p for p,h in noninfra.items() if not (ROOT/p).is_file() or sha((ROOT/p).read_bytes())!=h]
old=json.loads((EVIDENCE/'prior-records-baseline.json').read_text())
prior_errors=[]
for p,v in old['files'].items():
 current=(ROOT/p).read_bytes()
 if p in old['append_only_allowed']:
  original=subprocess.check_output(['git','show',f'{BASE}:{p}'],cwd=ROOT)
  if not current.startswith(original):prior_errors.append(p)
 elif sha(current)!=v['sha256']:prior_errors.append(p)
tracked=subprocess.check_output(['git','diff','--name-only',BASE],cwd=ROOT,text=True).splitlines()
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
allpaths=tracked+untracked
outside=[p for p in allpaths if not p.startswith(('infra/terraform/','docs/agent-runs/phase-12/'))]
protected=[p for p in allpaths if Path(p).name in ['human-gate.md','commit.txt','accepted-commit.md'] or 'approval' in Path(p).name.lower()]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
freeze_path=EVIDENCE/'infra-source-freeze.json'
freeze_errors=[]
if freeze_path.exists():
 freeze=json.loads(freeze_path.read_text())
 for p,v in freeze['files'].items():
  h=v if isinstance(v,str) else v['sha256']
  if not (ROOT/p).is_file() or sha((ROOT/p).read_bytes())!=h:freeze_errors.append(p)
summary={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_sha':BASE,'head':head,'branch':branch,'tracked_changed_paths':tracked,'untracked_paths':untracked,'tracked_changed_count':len(tracked),'untracked_count':len(untracked),'noninfra_baseline_count':len(noninfra),'changed_noninfra_paths':changed_noninfra,'prior_records_count':len(old['files']),'prior_record_preservation_errors':prior_errors,'out_of_scope_paths':outside,'human_owned_changed_paths':protected,'frozen_source_mismatches':freeze_errors}
validation=EVIDENCE/'build-validation.json'
if validation.exists():
 b=json.loads(validation.read_text()); summary['build']={k:b[k] for k in ['gate_exit_code','counts','xml_report_count','fresh_xml_report_count','all_xml_fresh','source_unchanged','start_after_freeze','start_after_all_source_mtimes','xml_log_count_agrees']}
 compressed=EVIDENCE/'sbt-check.log.gz'
 if compressed.exists():
  h=hashlib.sha256()
  with gzip.open(compressed,'rb') as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
  summary['decompressed_sbt_log_sha256']=h.hexdigest(); summary['decompressed_hash_matches_build']=h.hexdigest()==b['log_sha256']
assert not changed_noninfra and not prior_errors and not outside and not protected and not freeze_errors,summary
assert head==BASE and branch=='phase-12',summary
(EVIDENCE/'coordinator-final-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['tracked_changed_paths','untracked_paths']},indent=2))

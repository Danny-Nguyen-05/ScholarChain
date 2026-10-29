from pathlib import Path
import json,hashlib,subprocess,xml.etree.ElementTree as ET,re
repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
base=Path('/tmp/scholarchain-phase12b-repair1-build')
metadata=json.loads(Path(str(base)+'-result.json').read_text())
assert 'source_unchanged' in metadata, 'Gate has not completed'
start=metadata['start_epoch']
report_files=sorted([*(repo/'modules').glob('*/target/test-reports/*.xml'),*(repo/'tests').glob('target/test-reports/*.xml'),*(repo/'build-verification').glob('target/test-reports/*.xml'),*(repo/'target').glob('test-reports/*.xml')])
entries=[]
for path in report_files:
    root=ET.parse(path).getroot()
    suites=[root] if root.tag=='testsuite' else list(root.findall('testsuite'))
    entries.append({'path':str(path.relative_to(repo)),'mtime_epoch':path.stat().st_mtime,'mtime_ns':path.stat().st_mtime_ns,'fresh':path.stat().st_mtime>=start,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**{key:sum(int(s.attrib.get(key,'0')) for s in suites) for key in ['tests','failures','errors','skipped']}})
log=Path(str(base)+'-sbt-check.log')
lines=log.read_text(errors='replace').splitlines()
keys=['Total number of tests run:','Suites: completed','Tests: succeeded','All tests passed','checkProbeInjectFailure','injected format-stage failure','TestRunMarker','[success] Total time:']
excerpt='\n'.join(line for line in lines if any(k in line for k in keys) or line.startswith('[error]'))+'\n'
Path(str(base)+'-sbt-check-excerpt.txt').write_text(excerpt)
counts=[int(m.group(1)) for line in lines if (m:=re.search(r'Total number of tests run: (\d+)',line))]
summary={'gate_start_utc':metadata['start_utc'],'gate_end_utc':metadata['end_utc'],'gate_exit_code':metadata['gate_exit_code'],'sbt_elapsed_seconds':metadata['results'][-1]['elapsed_seconds'],'gate_elapsed_seconds':metadata['elapsed_seconds'],'source_unchanged':metadata['source_unchanged'],'source_changed_paths':metadata['source_changed_paths'],'git_branch_head_unchanged':metadata['git_branch_head_unchanged'],'frozen_source_count':metadata['frozen_source_count'],'infra_source_count':metadata['infra_source_count'],'tracked_source_count':metadata['tracked_source_count'],'all_snapshot_file_count':metadata['all_snapshot_file_count'],'start_after_freeze':metadata['start_after_freeze'],'start_after_all_source_mtimes':metadata['start_after_all_source_mtimes'],'source_before_path':metadata['source_before_path'],'source_after_path':metadata['source_after_path'],'xml_scope':'Current configured sbt targets: modules/*/target/test-reports, tests/target/test-reports, build-verification/target/test-reports, target/test-reports. Legacy project/verification/target is outside active buildVerification target.','xml_report_count':len(entries),'fresh_xml_report_count':sum(e['fresh'] for e in entries),'counts':{k:sum(e[k] for e in entries) for k in ['tests','failures','errors','skipped']},'all_xml_fresh':all(e['fresh'] for e in entries),'xml_entries':entries,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'log_bytes':log.stat().st_size,'log_test_group_counts':counts,'log_total_test_summary_sum':sum(counts),'unexpected_failed_marker_lines':[line for line in lines if '*** FAILED ***' in line],'error_lines':[line for line in lines if line.startswith('[error]')],'sbt_version_line':next((line for line in lines if 'welcome to sbt' in line),None),'java_version':Path(str(base)+'-java-version.log').read_text(),'gitignore_sha256':hashlib.sha256((repo/'.gitignore').read_bytes()).hexdigest(),'support_file_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(str(base)+'-run.py'),Path(str(base)+'-source-before.json'),Path(str(base)+'-source-after.json'),Path(str(base)+'-start.json'),Path(str(base)+'-result.json')]}}
summary['xml_log_count_agrees']=summary['counts']['tests']==summary['log_total_test_summary_sum']
summary['expected_check_probe_failure_detected']=any('injected format-stage failure' in line for line in lines) and any('(checkProbeInjectFailure)' in line for line in lines)
summary['test_run_marker_detected']=any('running scholarchain.build.TestRunMarker ' in line for line in lines)
summary['gate_success_line']=next((line for line in reversed(lines) if '[success] Total time:' in line),None)
summary['collector_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
summary['attempt_manifest']='/tmp/scholarchain-phase12b-repair1-build-attempts.json'
Path(str(base)+'-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['xml_entries','error_lines','support_file_hashes']},indent=2))
assert summary['gate_exit_code']==0
assert summary['source_unchanged'] and summary['git_branch_head_unchanged']
assert summary['all_xml_fresh'] and summary['xml_log_count_agrees']
assert summary['counts']['failures']==summary['counts']['errors']==summary['counts']['skipped']==0
assert not summary['unexpected_failed_marker_lines']

assert summary['expected_check_probe_failure_detected']
assert summary['test_run_marker_detected'] and summary['gate_success_line']

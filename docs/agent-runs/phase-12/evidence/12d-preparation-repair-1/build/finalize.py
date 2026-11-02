from pathlib import Path
import json,hashlib,gzip,datetime,re
out=Path('/tmp/scholarchain-phase12d-preparation-repair1-build')
r=json.loads((out/'build-result.json').read_text())
raw=(out/'sbt-check.log.txt').read_bytes();packed=(out/'sbt-check.log.gz').read_bytes()
assert gzip.decompress(packed)==raw
lines=raw.decode(errors='replace').splitlines();error_positions=[i+1 for i,s in enumerate(lines) if '[error]' in s]
blocks=[]
for pos in error_positions:
 if not blocks or pos!=blocks[-1][-1]+1:blocks.append([pos])
 else:blocks[-1].append(pos)
probe_present='checkProbeInjectFailure' in raw.decode(errors='replace') and 'injected format-stage failure' in raw.decode(errors='replace')
error_check={'positions':error_positions,'contiguous_blocks':[[x[0],x[-1],len(x)] for x in blocks],'expected_probe_present':probe_present,'only_one_expected_block':len(blocks)==1 and probe_present}
(out/'expected-error-check.json').write_text(json.dumps(error_check,indent=2)+'\n')
if r['error_lines'] and not error_check['only_one_expected_block']:r['status']='FAILED'
(out/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
java=r['java'];build=r['build'];tot=r['test_totals']
report=f'''STATUS: {r['status']}
OWNER: build-engineer (/root/build_12d_repair1)
WORK ORDER: Phase 12D preparation repair round 1, offline post-freeze full JDK 17 regression gate. Branch phase-12; HEAD {r['head']}.
FILES CREATED: Scratch evidence only under {out}; artifact-manifest.json indexes retained origin files. Coordinator owns repository evidence.
FILES MODIFIED: No source, build or configuration files edited; normal ignored test outputs and success marker generated.
COMMANDS RUN: java -version (exit {java['exit_code']}); sbt -batch check (exit {build['exit_code']}), cwd {r['cwd']}. Exact shell argv, selected non-secret JAVA_HOME/PATH/SBT_OPTS, UTC/nanosecond timestamps and per-command SHA/bytes are recorded in commands.json. Gate {build['started_utc']}–{build['ended_utc']}; wall {build['wall_seconds']} seconds.
TEST RESULTS: {tot['tests']} tests across {r['fresh_xml_count']} fresh XML reports, {tot['failures']} failures, {tot['errors']} errors, {tot['skipped']} skips. Module log totals sum to {r['module_log_tests_sum']} and match XML: {r['module_log_matches_xml']}. {r['stale_xml_count']} stale reports excluded and listed individually in xml-reports.json. Only expected checkProbeInjectFailure error block: {error_check['only_one_expected_block']}. Summary lines and groups retained.
VALIDATION RESULTS: {r['freeze_before']['files']} frozen files before and after; {len(r['freeze_before']['mismatches'])}/{len(r['freeze_after']['mismatches'])} mismatches. Freeze SHA {r['freeze_sha256']}. {r['snapshot_files_before']} before / {r['snapshot_files_after']} after snapshot files, {len(r['snapshot_deltas'])} changes in SHA/bytes/mtime. Raw log SHA {r['raw_log_sha256']}; gzip SHA {r['gzip_sha256']}; decompressed bytes {len(raw)} equal raw. Exact JDK version is in java-version.log.txt.
ASSUMPTIONS: Coordinator freeze identifies the final repair sources. Mutable docs/agent-runs evidence is excluded from broad build snapshots; scope and any sensitive-name exclusions are explicit in snapshots.
RISKS: Local tests do not establish live budget delivery, CUSTOM/CostTypes service acceptance, IAM/KMS effectiveness, EMR distributed compatibility, cost fit, deadline enforcement or teardown.
MANUAL ACTION REQUIRED: Coordinator retains logs, counts and provenance, then supplies the independent preparation-only recheck handoff. Live work remains blocked on its existing gates.
BLOCKED-ON OWNER: None for this build gate.
BLOCKED-ON EVIDENCE: None for this build gate.
NEXT GATE: User-launched independent read-only preparation recheck. No AWS, Terraform, credential, paid-service, agent, commit or push action occurred; build and runner exited.
'''
(out/'build-owner-report.txt').write_text(report)
files=[]
for p in sorted(out.iterdir()):
 if p.is_file() and p.name not in ['artifact-manifest.json','active-process.json','finalize.py']:
  b=p.read_bytes();files.append({'path':p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(out/'artifact-manifest.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files},indent=2)+'\n')
print(json.dumps({'status':r['status'],'tests':tot,'fresh_xml':r['fresh_xml_count'],'snapshots':r['snapshot_files_before'],'stale_xml':r['stale_xml_count'],'only_expected_error_block':error_check['only_one_expected_block'],'artifact_count':len(files),'raw_sha':r['raw_log_sha256'],'gzip_sha':r['gzip_sha256']},indent=2))

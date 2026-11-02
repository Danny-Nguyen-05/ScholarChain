from pathlib import Path
import json, hashlib, datetime, subprocess, re
R=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');P=R/'docs/agent-runs/phase-12';E=P/'evidence/12d-billing-apply-gate-repair-prep'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
pre=json.loads((E/'preflight.json').read_text());assert pre['head']=='5ca8406bad5fe55f732458fa0cbd5d561ac83d8f' and pre['branch']=='phase-12'
old=json.loads((P/'evidence/12d-billing-policy-amendment/source-freeze.json').read_text())
for x in old['files']:
    p=R/x['path'];assert sha(p)==x['sha256'] and p.stat().st_size==x['bytes'] and p.stat().st_mtime_ns==x['mtime_ns']
assert len(old['files'])==209
for x in pre['earlier_packet_files']:
    p=R/x['path'];assert sha(p)==x['sha256'] and p.stat().st_size==x['bytes']
attachment=(E/'user-supplied-external-review.txt').read_bytes()
assert attachment==Path('/Users/danny/.codex/attachments/88e447bc-88a7-4a53-9010-942d88af5ef9/Pasted text.txt').read_bytes()
assert attachment in (P/'review.md').read_bytes()
human=P/'billing-bootstrap-exception.md';answers=json.loads((E/'human-inputs.json').read_text())
human_changed_after_question=sha(human)!=answers['human_record']['observed_current_sha256']
timing='A further human file change is visible; independent reviewer must assess exact timing and discrepancy.' if human_changed_after_question else 'Human reports clarification saved, but on-disk file remains unchanged from supervised9–10PM text and still promises actual times afterward. Clarification not observed.'
write('timing-followup.json',{'recorded_utc':now,'user_followup_reply_verbatim':'Actual timing and discrepancy clarified in my file','human_record_path':str(human.relative_to(R)),'observed_sha256':sha(human),'further_file_change_observed':human_changed_after_question,'assessment':timing,'agent_edited_human_record':False,'historical_records_not_rewritten':True,'timing_acceptance_by_independent_reviewer_pending':True})
write('local-validation.json',{'recorded_utc':now,'review_attachment_verbatim':True,'earlier_packet_files_preserved':len(pre['earlier_packet_files']),'source_reference_209_hash_bytes_mtime_equal':True,'source_changes':0,'current_terraform_aws_build_test_calls':0,'tests_not_rerun_reason':'Only coordinator evidence and offline proposal/review-prompt documents authored; no behavior or production source changed. Prior test results remain historical.','specialist_manifest_artifacts':4,'specialist_manifest_sha256':sha(E/'infra/artifact-manifest.json'),'durable_paths_created':False,'private_input_requested_or_read':False,'replacement_plan_generated':False,'actual_apply_handoff_prepared':False,'aws_mutations':0,'reviewer_launched':False,'running_specialist_jobs':False})
report='''STATUS: BLOCKED-ON
OWNER: coordinator assembling infra-engineer /root/infra_12d_durable_storage_prep
WORK ORDER: User “Fix all blocking bugs” supplies independent APPROVE for fresh read-only execution-identity plan only, with P1/P2 Medium apply blockers and P3 Low later-handoff requirement. Record verdict verbatim, route blockers and prepare independent identity-review/storage proposals. Branch phase-12; base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f. Human selected recommended durable paths/retention and conditional read-only regeneration after prerequisites. Preparation complete; blockers not falsely closed.
FILES CREATED: docs/agent-runs/phase-12/evidence/12d-billing-apply-gate-repair-prep/** and reviewer-prompt-12d-identity-establishment.md. Includes original review, coordinator transcriptions/baseline/validation, four public specialist artifacts plus manifest, reproducible assembly/finalization sources, repair status and handoff inventory.
FILES MODIFIED: Append-only prompt.md, review.md, repairs.md, owner-report.md and test-report.md. No production source or earlier packet edit. Human independently reported editing the exception; agent did not edit it or rewrite historical hashes. Latest timing follow-up is recorded separately without inventing actual start/end.
COMMANDS RUN: Local read-only Git/status/branch/HEAD, source/report/attachment reads, selected path-ancestor stat/resolve, Python JSON/hash/byte-prefix/source-freeze/manifest/privacy validations and coordinator evidence assembly. Specialist public primary-source browsing and local proposal checks documented in infra/owner-report.txt and infra/sources.json. No Terraform/AWS/login/build/paid calls. Initial assembly stdin script had a non-ASCII bytes-literal SyntaxError exit1 before any code executed; corrected UTF-8 assembly exit0. Read-only path lookup errata retained in human-inputs.json. git diff --check result retained separately.
TEST RESULTS: No feature behavior or production source changed, so no new Terraform or sbt tests. All209 source reference hash/bytes/mtimes equal;96 earlier packet files preserved. Prior billing7/0, four-root72/0 and sbt1255 results remain historical. Specialist manifest4 artifacts checked; both reports have14 fields. Public source study is not runtime validation.
VALIDATION RESULTS: Original review appended verbatim; read-only-plan APPROVE preserved without apply authority. P1 identity prompt covers all3 packets/11 screenshots, exact exception/policies/tags, inventory limitation, password-label discrepancy and timing. P2 human selected /Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap and sibling billing-bootstrap-backups, directory0700/sensitive data0600/executable0700, retained through teardown/reconciliation and human-approved cleanup. Offline proposal includes durable config/toolchain/mirror/data/state/new plan and backups. Pinned Terraform1.13.5 source confirms explicit local -state override matters even for saved-plan apply; TF_DATA_DIR does not relocate resource state. P3 design requires exact caller/account and structured NotFoundException for exact budget; unknown/denied/network stops. No live check or storage/plan creation occurred.
ASSUMPTIONS: User-reported edits and storage selections are accurately transcribed; on-disk timing is checked independently of a reply. Same-disk backups protect accidental deletion, not disk failure. The independent reviewer must determine evidence sufficiency; coordinator cannot approve its own prior identity guidance.
RISKS: P1 remains open until human timing or unavailability reason is observed/assessed and user-launched independent review APPROVES. P2 remains open until durable-path plan is regenerated and new checksum independently reviewed. Old /tmp plan cannot be used for apply. Remote ownership/absence, provider ARN, live permissions/CUSTOM/CostTypes/tags/monitor/delivery/refresh/cost data remain unverified. B1/B2/B3/R1/N19/N20 and all EMR gates unchanged; USD5 proposed spike/USD10 EMR reserve/USD5.09 margin unchanged and not spending approval.
MANUAL ACTION REQUIRED: Human saves timing/discrepancy or inability/reason in own record; user launches independent P1 review with complete supplied prompt. After prerequisites and a new work prompt, infra-engineer may regenerate only the read-only durable plan using selected public inputs and newly hidden recipient, then return new checksum for independent review. Any apply needs a later human-written exact-plan approval/window; no approval record authored here.
BLOCKED-ON OWNER: Human architect (own timing record); user-launched independent reviewer (P1 verdict); infra-engineer/coordinator (later gated P2 regeneration). No user reviewer launched by coordinator.
BLOCKED-ON EVIDENCE: Human timing clarification must be visible and independently assessed; no independent review of three identity packets has been supplied; no durable-path replacement plan/new reviewed checksum exists. P3 live checks remain intentionally unrun.
NEXT GATE: User-launched P1 identity-evidence review. Stop; no apply handoff, durable setup/plan regeneration, AWS/IAM mutation, spending, reviewer launch, commit/push or Phase13 before prerequisites and next prompt.
'''
(E/'coordinator-report.md').write_text(report)
heading='\n\n## Subphase 12D — billing apply-gate repair preparation\n\n'
for n in ['owner-report.md','test-report.md']:
    assert heading not in (P/n).read_text()
    with (P/n).open('a') as f:f.write(heading+report)
write('repair-status.json',{'P1':{'severity':'Medium','blocks':'apply gate','status':'OPEN','prepared':'Independent user-launched reviewer prompt; exact review recorded; human timing follow-up transcribed','remaining':'Human timing/unavailability reason saved and assessed; independent identity review APPROVE'},'P2':{'severity':'Medium','blocks':'apply gate','status':'OPEN','prepared':'Human storage/retention choices and offline durable config/toolchain/state/backup/regeneration proposal','remaining':'After P1 prerequisites, fresh durable-path read-only plan/new checksum and independent review'},'P3':{'severity':'Low','status':'DESIGN PREPARED; LIVE CHECK UNRUN','remaining':'Inside separately authorized apply window, exact-role caller and exact-name absence checks; fail closed'},'apply_authorized':False,'all_blockers_closed':False})
(E/'handoff.md').write_text('''Billing apply-gate repair preparation — BLOCKED-ON human timing evidence and user-launched P1 review.

Original read-only-plan APPROVE is recorded verbatim; P1/P2 remain open. Human chose durable local paths/retention and conditional regeneration after prerequisites. No source, AWS, durable storage or plan mutation occurred. All209 source reference hashes/bytes/mtimes and96 prior-packet files match. No new tests/builds; historical results unchanged.

Use ../../reviewer-prompt-12d-identity-establishment.md for the independent review of all3 identity packets. Coordinator cannot launch that reviewer or write the human timing record. The on-disk timing observation is in timing-followup.json; no times are inferred from the human's menu reply. Human-owned record edits are attributed separately, not incorporated into historical manifests.

P2 storage/regeneration proposal: infra/proposal.md. P3 in-window preflight design: infra/preflight-design.md. Actual apply handoff is not prepared until prerequisites. The old /tmp plan is historical read-only evidence and must not be applied. Nothing applied, no reviewer launched, no spending/Phase13 authorized.
''')
prefixes=[]
for x in pre['records']:
    p=R/x['path'];b=p.read_bytes();assert hashlib.sha256(b[:x['bytes']]).hexdigest()==x['sha256']
    head=subprocess.check_output(['git','show','HEAD:'+x['path']],cwd=R);assert b.startswith(head)
    prefixes.append({'path':x['path'],'preflight_prefix_preserved':True,'head_prefix_preserved':True,'current_sha256':sha(p),'current_bytes':len(b)})
write('record-prefix-check.json',{'records':prefixes,'count':5,'prior_packet_files_preserved':96,'human_record_agent_writes':0})
v=subprocess.run(['git','diff','--check'],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(E/'diff-check.log.txt').write_bytes(v.stdout);assert v.returncode==0
write('diff-check-result.json',{'argv':['git','diff','--check'],'cwd':str(R),'exit_code':v.returncode,'output_sha256':sha(E/'diff-check.log.txt')})
for n in ['handoff-files.json','evidence-manifest.json','final-status.log.txt']:(E/n).touch()
(E/'final-status.log.txt').write_bytes(subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=R))
paths=[str(p.relative_to(E)) for p in sorted(E.rglob('*')) if p.is_file()]
write('handoff-files.json',{'branch':'phase-12','head':pre['head'],'current_work_evidence_files':paths,'current_work_reviewer_prompt':'docs/agent-runs/phase-12/reviewer-prompt-12d-identity-establishment.md','current_work_append_only_records':[x['path'] for x in pre['records']],'human_record_changed_by_human_reported_not_agent':str(human.relative_to(R)),'earlier_uncommitted_work_retained':True,'final_git_status_entries':len((E/'final-status.log.txt').read_text().splitlines()),'inventory_includes_itself_and_manifest':True})
files=[p for p in sorted(E.rglob('*')) if p.is_file() and p.name!='evidence-manifest.json']
write('evidence-manifest.json',{'recorded_utc':now,'self_excluded':'evidence-manifest.json','count':len(files),'files':[{'path':str(p.relative_to(E)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]})
print(json.dumps({'repair_prep_complete':True,'blocking_findings_still_open':['P1','P2'],'source_reference_equal':209,'earlier_packet_files_preserved':96,'human_record_change_since_reply_observed':human_changed_after_question,'evidence_files':len(files)+1,'manifest_sha256':sha(E/'evidence-manifest.json')}))

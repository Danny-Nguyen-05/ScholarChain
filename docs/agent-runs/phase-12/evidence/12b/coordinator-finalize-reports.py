from pathlib import Path
import json,subprocess,datetime
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain'); RUN=ROOT/'docs/agent-runs/phase-12'; EV=RUN/'evidence/12b'
BASE='a83f62e9af56058a170075f98c4e027d039567ec'
b=json.loads((EV/'build-validation.json').read_text()); result=json.loads((EV/'build-result.json').read_text())
assert b['gate_exit_code']==0 and b['source_unchanged'] and b['all_xml_fresh'] and b['xml_log_count_agrees']
assert all(b['counts'][x]==0 for x in ['failures','errors','skipped'])
assert result['git_branch_head_unchanged'] and result['start_after_freeze'] and result['start_after_all_source_mtimes']
counts=b['counts']; scope=json.loads((EV/'infra/source-scope.json').read_text())
commands='''From /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform:
TF_CLI_CONFIG_FILE=/tmp/scholarchain-phase12b-infra/terraformrc /tmp/scholarchain-phase12a-infra-toolchain/terraform init -backend=false -input=false -no-color
/tmp/scholarchain-phase12a-infra-toolchain/terraform fmt -check -recursive
/tmp/scholarchain-phase12a-infra-toolchain/terraform validate -no-color
/tmp/scholarchain-phase12a-infra-toolchain/terraform test -no-color
From the repository root: git diff --check
All final exits: 0. Exact per-attempt cwd/argv/exits/log SHA-256: evidence/12b/infra/commands.json. Raw logs retain byte hashes with .log.txt suffixes because *.log is ignored; infra/log-name-map.json and infra-retention-validation.json resolve original names.

From /Users/danny/Documents/UIC/CS441/ScholarChain:
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
sbt -batch check
Both exits: 0. Build runner/collector, exact environment, timestamps and raw log hashes are retained under evidence/12b/.
'''
answers='''Account/profile/region and budget pending, no spending authorized; course environment. Neptune Serverless 1–2.5 NCUs, seven-day backups, private/CMK/IAM/protected, disabled until engine/family selection. EMR disabled pending explicit verified release/runtime/bootstrap/TLS and concrete control-plane policy; one primary, one core, at most two task nodes, no Spot. Prefix-scoped output deletes only. Fixed-queue Step Functions producer, production caller deferred13. ALB access logs off, cert pending, empty public ingress, HTTPS only when configured, no HTTP. Runtime disabled; activated defaults512CPU/1024MiB, HTTP services min1/max2 CPU60%, worker min1/max4 backlog10/task. Five Phase7 indexes,256/cosine/float32, exact non-filterable textS3Uri. Configurable TitanV2 embedding; synthesis unset/no query-model grant. Logs7days; alarms5% HTTP errors,5s p95 latency,300s queue age; SNS unset. Add functional Step Functions with least privilege, retries and DLQ. Current unconfigured app composition and custom-metric publisher remain explicit Phase13/14 dependencies; graph replicas require shared cursor-key ARN. Complete accepted recommendations and verbatim user acceptance: evidence/12b/step-0-answers.md.'''
limits='''No real AWS plan, apply/destroy/import, account API, credential lookup or paid model call. Live IAM/KMS/region/quotas, engine availability, cost/budget-filter activation, EMR Spark compatibility and output commits remain unverified. Native plans use only mock_provider aws / command=plan. No security scanner ran; manual source/schema/feature checks are disclosed. Current service artifacts remain unconfigured/readiness503; acknowledgments in tests are synthetic and do not prove production readiness. No live CloudWatch application publisher or notification recipient exists. EMR service policy is pending, not replaced by a broad default; the synthetic DescribeInstances-only fixture cannot launch a cluster. S3/vector prevent_destroy needs separately reviewed source changes for cleanup. OpenSearch, EventBridge and Glue omitted; scripts deferred13. Step Functions is now authored under the user's selection, without instructor/full-course approval. No commits/pushes in12B.'''
summary=f'''Native Terraform:31 passed/0 failed (13 retained12A+18new12B),51 assertions,16 expected-failure cases. Three retained mutations each init0/test1,30passed/1failed, with intended diagnostics and repository unchanged. Full JDK17 sbt: exit0,{counts['tests']}tests,{b['fresh_xml_report_count']}/{b['xml_report_count']}fresh XML,0failures/errors/skips;{b['gate_elapsed_seconds']}s gate wall time ({b['sbt_elapsed_seconds']}s sbt wall). Expected checkProbeInjectFailure self-test only. Raw/decompressed sbt SHA256 {b['log_sha256']}.'''
freeze=json.loads((EV/'infra-source-freeze.json').read_text())
for name,owner in [('owner-report.md','coordinator assembling infra-engineer /root/infra_12b and build-engineer /root/build_12a; exact inherited model identifiers unavailable'),('test-report.md','coordinator assembling infra-owner native tests and build-engineer full gate; no reviewer invoked')]:
 report=f'''

## Subphase 12B

STATUS: COMPLETE (12B local authoring and required local gates; independent review pending)
OWNER: {owner}.
WORK ORDER: ONLY12B, accepted Step0 recommendation set and user answer `use all recommendations`; full work order in prompt.md/review.md. Branch phase-12, base/HEAD {BASE}. 12A plus repair/review records were committed/pushed before this work; no commit/push of12B.
FILES CREATED:25 new Terraform files, including five new modules, identity/runtime additions, root wiring/variables and phase12b native tests. Coordinator evidence/12b packet and reviewer-prompt-12b.md. Exact final changed/untracked inventories: evidence/12b/handoff-files.json. All67 Git-visible infra files (including original .gitkeep) frozen.
FILES MODIFIED:13 existing Terraform paths in evidence/12b/infra/source-scope.json; coordinator append-only prompt/repairs/owner/test records. No authored application/build/scripts/constitution changes; generated ignored test marker is build-owned. Earlier93 phase records preserved byte-for-byte except four allowed append-only reports;455 non-infra baseline files unchanged. No human-owned gate/approval/commit files edited.
COMMANDS RUN: Final exact commands and environment below. All final Terraform init/fmt-check/validate/test/diff-check0; JDK17 java-version0 and sbt-check0. The48 native command logs and70 curated artifacts reconcile their recorded hashes. Nonzero development attempts are retained, including syntax/conditional/mock/metric errors, registry timeout and initial incomplete mirror lock failure; the complete pinned package mirror fixes init without changing pins/lock. Initial build readiness preflight1 before java/sbt was corrected only in scratch to include .gitkeep; provenance retained in build-preflight-retry.json. Parent inspection diagnostics about nonexistent candidate paths/unfinished report glob occurred outside gates; no failed gate is hidden.
TEST RESULTS: {summary}
VALIDATION RESULTS: Terraform1.13.5/AWS6.44.0 exact across14 versions.tf files; lock byte-identical to base. Coordinator freeze {freeze['frozen_at_utc']}; build start {b['gate_start_utc']}, end {b['gate_end_utc']}, after freeze and all source mtimes. All{b['all_snapshot_file_count']} build-snapshotted files ({b['infra_source_count']}infra+{b['tracked_source_count']}tracked source inputs) unchanged in bytes/hash/mtime across gate; coordinator additionally checks Dockerfile.dockerignore in455-file baseline. All route/table/association declarations remain in modules/network. Selected hygiene checks report no hits; not a scanner or independent security approval. Evidence/12b/infra-gate-reconciliation.json and coordinator-final-validation.json retain reconciliation.
ASSUMPTIONS: {answers}
RISKS: {limits}
MANUAL ACTION REQUIRED: User launches independent read-only12B reviewer using reviewer-prompt-12b.md, then commits only after approval. Create/configure AWS account before12C (or earlier separately approved12D), and supply profile/region/budget/AZs/principal and planning authorization then. Neptune engine/family, EMR runtime/control policy, immutable images/secrets/certificate, service-owner live composition and metrics publisher need their later explicit gates. Human-owned approval records remain user-written.
BLOCKED-ON OWNER: None for12B local source/gates. Independent acceptance belongs to user-launched reviewer; later live prerequisites belong to user and owning specialists.
BLOCKED-ON EVIDENCE: No local gate blocker. Live plan/cost/compatibility/readiness/security effectiveness are unrun, not passed.
NEXT GATE: Independent user-launched12B review; no12C/12D, reviewer launch, commit or push. All delegated owners report no remaining jobs at handoff.

Exact final gate commands:

```bash
{commands}```
'''
 with (RUN/name).open('a') as f:f.write(report)
changed='\n'.join('- '+p for p in scope['tracked_changed'])
created='\n'.join('- '+p for p in scope['new'])
prompt=f'''You are the independent, read-only code reviewer for ScholarChain Phase12, Subphase12B, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md, docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase12.md, Sections2–7, Subphase12B in Section8, Sections9–10. The user's accepted answers supersede the earlier Step Functions omission and select offline disabled EMR authoring before the live spike.
3. Course Phase12, security, observability, cost controls and Phase15 scaling rules:
https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-12-create-the-aws-infrastructure-in-terraform
4. docs/agent-runs/phase-12/prompt.md, review.md (prior12A APPROVE), repairs.md, owner-report.md/test-report.md (Subphase12B), evidence/12b/step-0-answers.md, input-contracts.json, infra/owner-report.md, infra/commands.json, infra/test-coverage.json, infra/negative-results-v2.json, infra/log-name-map.json, infra-retention-validation.json, infra-gate-reconciliation.json, infra-source-freeze.json, build-validation.json, build-result.json, coordinator-final-validation.json and handoff-files.json.

Checkpoint:
- Branch phase-12; base and current HEAD {BASE}. 12A approved work was committed and pushed before12B. This12B diff remains uncommitted/unpushed.
- Source change footprint:13 tracked infra files modified,25 new infra files;67 git-visible infra files frozen (includes original .gitkeep). Coordinator docs edits append prompt/repairs/owner/test and add evidence/12b plus reviewer-prompt-12b.md. Complete exact final tracked/untracked paths/counts are in evidence/12b/handoff-files.json; no out-of-scope or human-owned changes.
- Modified infra paths:
{changed}
- New infra paths:
{created}
- Accepted setup: {answers}
- Observed gates: {summary}
- Source freeze {freeze['frozen_at_utc']}; full gate {b['gate_start_utc']} through {b['gate_end_utc']}. Before/after source continuity and fresh XML proof retained. All70 curated infra artifact hashes/48 command-log hashes reconciled; compressed debug aliases explained in infra/compressed-log-manifest.json. Full sbt log retained compressed.
- Exact final commands:
{commands}

Review rules:
- Read-only. Do not edit, run builds/tests/provider/Terraform commands, call AWS, discover/read secrets, mutate data, commit/push or launch agents. Read public documentation if needed. Git/status/diff/hash and scratch-only evidence inspection are allowed.
- Inspect git diff {BASE} plus all new files. Report ALL confirmed findings in one pass. Implementation owners cannot approve their own work; no independent12B approval exists yet.
- Check ownership and no changes outside12B; prior records remain intact and report prefixes preserved. Compare source hashes, retained logs/manifests, native counts and build/XML timing. Retained failed development/preflight attempts must not be presented as passes.
- Derive security expectations independently: no public data store; Neptune IAM/encryption/backups/protection; graph role has no write action; EMR has no DynamoDB and deletes only configured output prefixes; vector read/write and model grants scope concrete resources; workflow role trusts only the exact state machine, queues fixed, retries/timeouts/DLQ bounded, CMK queue/workflow grants distinct and correctly conditioned. Check wildcard exceptions and documented future EMR control-policy constraints.
- Verify every Section7.2 item12 policy: bounded EMR, HTTP CPU, worker SQS backlog per running task with actual Container Insights metric source; DDB on-demand. Ensure disabled runtime cannot start tasks through autoscaling, activation guards reject absent prerequisites, and HTTPS has no HTTP fallback.
- Verify all five vector indexes match names,256/cosine/float32 and non-filterable textS3Uri from actual storage/rag contracts. Verify auth/token/cursor secrets are ARN-only, graph replicas share a cursor key, and task mode remains honestly unconfigured until application-owner integration.
- Check CloudWatch dashboard JSON metric-array shape, real native metric/dimension contracts, Phase15 coverage, missing-data behavior, retention and empty notification targets. Custom publisher is explicitly future work; do not treat a panel definition as emitted telemetry.
- Verify N1/N2/N5 answered dispositions; optional N3/N4/N6 remain disclosed; N7 post-freeze order preserved; N8 now has functional Step Functions rather than a Pass placeholder and no waiver/compliance claim. B1/B2 regression controls must remain effective. R1: every aws_route/route-table resource is within modules/network; R2 real-plan replacement check remains unrun; R3 no action.
- Check three retained negative cases fail intended assertions (each30/1), not merely unknown values/provider failure, with repo source unchanged. No live plan is required for12B; do not call later live gates passed.
- Limitations: {limits}

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase12B.
2. Every confirmed finding: severity, path:line, evidence/concrete failure input, impact, owning agent, acceptance check, blocking yes/no. Separate nonblocking observations and unverified gates.
3. Exact14 report fields from docs/agent-runs/README.md.
4. A COMPLETE NEXT PROMPT in one fenced block for the coordinator, with all facts filled:
   - APPROVE: append your complete review verbatim to review.md as user-supplied external review; record dispositions; confirm approved12B work/review records committed (ask user if not). Never commit/push unless the user explicitly requests it anew. Then start ONLY12C Step0 questions, requiring AWS account/profile/region/budget and explicit read-only planning authorization before any account call; do not auto-start a12D spike. Preserve remaining runtime/composition/cost gates. Complete only that one authorized subphase, hand off reviewer prompt, stop.
   - REQUEST-CHANGES: append complete review/findings, route only blockers to owners; infra owns infra/terraform, coordinator owns phase evidence, build-engineer runs post-final-freeze JDK17 check. Fix bounded12B repair only, retain red/green evidence, run affected native checks and full post-freeze sbt gate, return complete recheck prompt, stop without12C/12D or launching reviewers. Carry nonblocking items without unrelated repairs.
'''
(RUN/'reviewer-prompt-12b.md').write_text(prompt)
(EV/'handoff.md').write_text(f'''# Subphase12B handoff\n\nStatus: local implementation/gates complete; independent review pending.\nBranch: phase-12. Base/HEAD: {BASE}. No12B commit/push.\n\n{summary}\n\nSource footprint:13 modified infra files and25 new;67 frozen. Full final tracked/untracked names/counts are in handoff-files.json. Coordinator docs only outside infra.\n\nAccepted Step0 answers: {answers}\n\nExact commands:\n\n```bash\n{commands}```\n\nEvidence: this directory, infra/commands.json and owner-report.md, negative-results-v2.json, both source freezes, build-start/result/validation.json, compressed full sbt log, retention manifests and coordinator-final-validation.json. Reviewer prompt: ../../reviewer-prompt-12b.md.\n\nLimitations: {limits}\n\nManual actions: independent user review then commit approved work. Create/configure an AWS account before12C or an earlier separately approved12D; select account/profile/region/budget and remaining engine/runtime/deployment inputs at that gate. All agents/jobs must be finished before final handoff. No next subphase started.\n''')
print('Appended both complete reports and wrote handoff/reviewer prompt from observed final evidence.')

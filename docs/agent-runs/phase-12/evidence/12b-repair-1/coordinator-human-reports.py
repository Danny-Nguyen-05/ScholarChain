from pathlib import Path
import json
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');RUN=ROOT/'docs/agent-runs/phase-12';OUT=RUN/'evidence/12b-repair-1';BASE='a83f62e9af56058a170075f98c4e027d039567ec'
b=json.loads((OUT/'build-validation.json').read_text());f=json.loads((OUT/'infra-source-freeze.json').read_text());assert b['gate_exit_code']==0 and b['source_unchanged'] and b['all_xml_fresh'] and b['xml_log_count_agrees']
assert all(b['counts'][k]==0 for k in ['failures','errors','skipped'])
commands='''cd /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform
TF_CLI_CONFIG_FILE=/tmp/scholarchain-phase12b-repair1-infra/terraformrc /tmp/scholarchain-phase12b-repair1-infra/terraform init -backend=false -input=false -no-color
/tmp/scholarchain-phase12b-repair1-infra/terraform fmt -check -recursive
/tmp/scholarchain-phase12b-repair1-infra/terraform validate -no-color
/tmp/scholarchain-phase12b-repair1-infra/terraform test -no-color
cd /Users/danny/Documents/UIC/CS441/ScholarChain
git diff --check
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
sbt -batch check
'''
summary=f"Terraform: 31 passed / 0 failed, 52 assertions, 16 expected-failure cases. Red scratch: init 0, test 1, 30 passed / 1 failed at B3. Full JDK 17 check: exit 0, {b['counts']['tests']} tests, {b['fresh_xml_report_count']}/{b['xml_report_count']} fresh XML reports, zero failures/errors/skips. Wall time: {b['sbt_elapsed_seconds']} seconds for sbt; {b['gate_elapsed_seconds']} seconds for the gate. Expected checkProbeInjectFailure only. Raw/decompressed sbt SHA-256: {b['log_sha256']}."
limitations='No live S3 Vectors/KMS effectiveness, real plan, account API, region/quotas, costs, budget-filter activation, EMR runtime/output commits or deployment readiness verified. No scanner ran. N9–N16 remain nonblocking and untouched: EMR service-role KMS, wildcard ARN guard, plausible empty dashboard arrays, native metrics gaps, HTTPS test scope, workflow missing-path handling, internal HTTP and absent loader/writer identities. Optional N3/N4/N6 remain carried. Service composition and the CloudWatch publisher are absent; scripts remain Phase 13. No instructor approval or full phase closure claimed.'
for name,owner in [('owner-report.md','coordinator assembling infra-engineer /root/infra_12b and build-engineer /root/build_12a reports'),('test-report.md','coordinator assembling native/red test evidence and the build-engineer full gate')]:
 text=f'''

## Subphase 12B repair round 1

STATUS: COMPLETE (B3 source repair and required local gates; independent recheck pending)
OWNER: {owner}. Exact inherited model identifiers unavailable. No reviewer invoked.
WORK ORDER: Fix only B3 from the user-supplied independent REQUEST-CHANGES. Complete review/work order appended verbatim under Subphase 12B in review.md and retained in evidence/12b-repair-1/user-supplied-external-review.txt. User request: `Fix all blockings bug for me`. No questions. Branch phase-12, base/HEAD {BASE}; existing uncommitted 12B work preserved. No 12C/12D, commit or push.
FILES CREATED: No new infrastructure files. Coordinator created the evidence/12b-repair-1 packet and reviewer-prompt-12b-recheck-1.md. Complete final tracked/untracked inventory: evidence/12b-repair-1/handoff-files.json. Native raw logs use .log.txt; full sbt log retained as gzip with raw/compressed hashes.
FILES MODIFIED: Exactly three of 67 infrastructure files relative to reviewed 12B: modules/identity/main.tf, tests/phase12b.tftest.hcl and README.md. Coordinator appended review/repairs/owner/test records only. Other 64 infrastructure files, pins, lock, .gitignore, application/build/scripts/constitution and human-owned records unchanged. All 103 original 12B evidence files preserved. Reverse application of delta.patch in scratch reconstructs all three reviewed pre-repair hashes.
COMMANDS RUN: Exact final commands below; init/fmt-check/validate/test/diff-check and Java/sbt all exit 0. The pre-fix red test intentionally exits 1 at B3; scratch init/helper exit 0. Eleven native command logs and 25 curated infrastructure artifacts hash-reconciled. Old /tmp toolchain/mirror paths were absent; official Terraform 1.13.5 ARM64 ZIP reinstalled to the repair prefix and verified against retained official SHA-256 1bf942231235e7e1a4c38c6d7b820e54f526ac487f87d19f0c4a425c6ddb62cb. Complete installed AWS 6.44.0 package hashes match prior provenance; no lock/pin workaround. Harmless missing-path inspection diagnostics disclosed. Setup observed exit 0; exact provenance in infra/toolchain-provenance.json and all gate argv/cwd/exits/timing/log hashes in infra/command-manifest.json and build-start/result.json.
TEST RESULTS: {summary}
VALIDATION RESULTS: Exact Terraform 1.13.5 / AWS 6.44.0 pins in all 14 versions.tf files; lock unchanged. Owner freeze 2026-10-29T15:35:04.829559Z; coordinator freeze {f['frozen_at_utc']}. Full gate {b['gate_start_utc']} through {b['gate_end_utc']}, after freeze and all source mtimes. All {b['all_snapshot_file_count']} snapshotted inputs ({b['infra_source_count']} infrastructure + {b['tracked_source_count']} tracked inputs) unchanged in hash/bytes/mtime across gate. Additional 455-file non-infrastructure baseline unchanged. New assertion checks exported CMK policy principal/action/account/bucket/context and total statement count. Root delegation unchanged, exact bucket ARN built without a module cycle. Red source continuity, patch reconstruction, log retention, XML and final scope reconciliation retained. No independent security approval claimed.
ASSUMPTIONS: Existing accepted 12B recommendations remain unchanged. New service grant is only kms:Decrypt, with exact account/project bucket and documented encryption-context conditions. Resource="*" means this key in KMS key-policy syntax; SourceArn has no wildcard. Synthetic fixture values are not actual account, region or budget selections. Existing disabled activation defaults and runtime/engine choices unchanged.
RISKS: {limitations}
MANUAL ACTION REQUIRED: User launches independent read-only repair recheck using reviewer-prompt-12b-recheck-1.md; no commit before approval. Create/configure AWS account before 12C or an earlier separately approved 12D; account/profile/region/budget remain pending. Later live actions need their own authorization. Human-owned approval files remain user-written.
BLOCKED-ON OWNER: None for local B3 implementation/gates. Independent acceptance belongs to the user-launched reviewer; later prerequisites remain with the user and owning specialists.
BLOCKED-ON EVIDENCE: No local repair gate blocker. Live KMS effectiveness and other live gates are unrun, not passed.
NEXT GATE: Independent user-launched 12B repair round 1 recheck. Assigned agents report no remaining jobs at handoff. Do not start 12C/12D, commit/push or invoke a reviewer.

Exact final commands (all final gate exits 0):

```bash
{commands}```
'''
 with (RUN/name).open('a') as file:file.write(text)
(OUT/'handoff.md').write_text(f'''# Subphase 12B repair round 1 handoff

Status: B3 local repair/gates complete; independent recheck pending.
Branch: phase-12. Base/HEAD: {BASE}. No commits or pushes.

Exactly three existing infrastructure files changed: identity/main.tf, tests/phase12b.tftest.hcl and README.md. All 67 files frozen. Other 64 and original 103-file 12B evidence packet unchanged. Complete final tracked/untracked names/counts: handoff-files.json.

{summary}

Exact commands:

```bash
{commands}```

Evidence: infra/command-manifest.json, red-proof.json, delta.patch, both source freezes, delta-reconstruction-proof.json, build-start/result/validation/source-before/source-after, compressed full sbt log, retention manifests and coordinator-final-validation.json. Complete reviewer prompt: ../../reviewer-prompt-12b-recheck-1.md.

{limitations}

Manual action: user launches independent recheck, then commits only after approval. Create/configure AWS account before 12C or an earlier separately approved 12D. Account/profile/region/budget remain pending. All delegated agents and builds completed; no next subphase started.
''')
with (RUN/'repairs.md').open('a') as file:file.write('\n### Subphase 12B repair round 1 — implementation result, recheck pending\n\nB3 owner repair is complete: one scoped indexing-service decrypt statement, one exact native assertion and one README note. Red 30/1, then green 31/0; 52 assertions, 16 expected-failure cases. Full post-freeze JDK 17 gate passed; counts/timing/hash in repair owner/test sections. Exactly three infrastructure files changed; other 64 and original 12B evidence unchanged. N9–N16 remain NOT REPAIRED. Independent acceptance belongs to the user-launched recheck. No next subphase, commit, push or cloud call.\n')
print('Appended both complete repair reports and handoff from observed final evidence.')

from pathlib import Path
import json
ROOT=Path('/Users/danny/Documents/UIC/CS441/ScholarChain');RUN=ROOT/'docs/agent-runs/phase-12';OUT=RUN/'evidence/12b-repair-1';BASE='a83f62e9af56058a170075f98c4e027d039567ec'
b=json.loads((OUT/'build-validation.json').read_text());f=json.loads((OUT/'infra-source-freeze.json').read_text())
text=f'''You are the independent, read-only reviewer for ScholarChain Phase 12,
Subphase 12B repair round 1, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Authority and reading:
1. AGENTS.md, CLAUDE.md, docs/agents.md,
   .claude/agents/code-reviewer.md, docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase12.md
   Sections 2–7, Subphase 12B, Sections 9–10.
3. Course Phase 12, security, cost and observability requirements:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-12-create-the-aws-infrastructure-in-terraform
4. docs/agent-runs/phase-12/review.md (complete user-supplied 12B review),
   repairs.md, owner-report.md and test-report.md (repair round 1 sections).
5. docs/agent-runs/phase-12/evidence/12b-repair-1/:
   preflight-and-baseline.json, user-supplied-external-review.txt,
   infra/owner-report.md, infra/command-manifest.json, infra/delta.patch,
   infra/red-proof.json, infra/test-coverage.json,
   infra/scope-and-preservation.json, infra/toolchain-provenance.json,
   infra-retention-validation.json, delta-reconstruction-proof.json,
   infra-source-freeze.json, build-start.json, build-result.json,
   build-validation.json, build-source-before.json, build-source-after.json,
   build-retention-manifest.json, coordinator-final-validation.json,
   handoff-files.json and handoff.md.
6. Original evidence/12b packet and reviewer-prompt-12b.md as needed.

Checkpoint:
- Branch: phase-12. Base and HEAD: {BASE}.
  Existing 12B and repair work remain uncommitted and unpushed.
- Only blocker B3 was authorized. Exactly three existing infrastructure
  files changed relative to the reviewed 12B source; no new infra files:
  infra/terraform/modules/identity/main.tf
  infra/terraform/tests/phase12b.tftest.hcl
  infra/terraform/README.md
- All 67 infrastructure files are frozen. Other 64 infra files, pins,
  provider lock and .gitignore are unchanged. The original 103-file 12B
  evidence packet is unchanged. Review/repairs/owner/test records have
  allowed appends only. Exact current tracked/untracked paths and counts
  are in handoff-files.json. No human-owned record changed.
- B3 adds one CMK statement for indexing.s3vectors.amazonaws.com:
  Effect Allow; Action exactly ["kms:Decrypt"]; Resource "*" for this key;
  StringEquals aws:SourceAccount = configured account;
  ArnLike aws:SourceArn = exact project vector bucket ARN;
  ForAnyValue:StringEquals kms:EncryptionContextKeys =
  ["aws:s3vectors:arn", "aws:s3vectors:resource-id"].
  The ARN is constructed from region/account/name_prefix, matching the
  vector bucket naming contract without a module-output dependency.
  Root delegation is unchanged. README adds one short control note.
- RED: new assertion against pre-fix policy in scratch; init exit 0,
  test exit 1, 30 passed/1 failed at B3, with a real value mismatch.
  Repository source unchanged across scratch execution.
- GREEN: final init/fmt-check/validate/test/diff-check exit 0;
  31 passed/0 failed, 52 assertions, 16 expected-failure cases.
- Coordinator freeze: {f['frozen_at_utc']}.
  Full JDK 17 gate: {b['gate_start_utc']} through {b['gate_end_utc']}.
  Exit 0; {b['counts']['tests']} tests; {b['fresh_xml_report_count']}/{b['xml_report_count']} fresh XML;
  zero failures/errors/skips. Expected checkProbeInjectFailure only.
  sbt wall time {b['sbt_elapsed_seconds']} seconds; gate wall {b['gate_elapsed_seconds']} seconds.
  All {b['all_snapshot_file_count']} source inputs unchanged across gate;
  gate started after freeze and all source mtimes.
- Raw/decompressed sbt log SHA-256:
  {b['log_sha256']}
- Twenty-five infra artifacts and eleven native command logs reconciled.
  Raw native logs use .log.txt; full sbt log is gzip with both hashes.
  Toolchain was recovered because old /tmp paths were gone: official
  Terraform 1.13.5 ARM64 ZIP matched retained official SHA-256; the full
  installed AWS 6.44.0 package matched prior provenance. Pins/lock unchanged.

Exact final commands:
Cwd /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform:
TF_CLI_CONFIG_FILE=/tmp/scholarchain-phase12b-repair1-infra/terraformrc /tmp/scholarchain-phase12b-repair1-infra/terraform init -backend=false -input=false -no-color
/tmp/scholarchain-phase12b-repair1-infra/terraform fmt -check -recursive
/tmp/scholarchain-phase12b-repair1-infra/terraform validate -no-color
/tmp/scholarchain-phase12b-repair1-infra/terraform test -no-color
All final exits 0. Exact red/helper commands, cwd, exits, timings and
log hashes: infra/command-manifest.json. Red test intentionally exited 1.

Cwd /Users/danny/Documents/UIC/CS441/ScholarChain:
git diff --check
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
sbt -batch check
Diff-check, Java and sbt exits 0. One full build, after the final freeze.

Review rules:
- Strictly read-only. No edits, builds/tests, Terraform/provider/account
  calls, secrets, commits/pushes or agents. Git/diff/hash, public primary
  documentation and scratch-only evidence reconstruction are allowed.
- Inspect git diff {BASE} plus untracked files. Isolate this repair using
  delta.patch, original 12B freeze and repair preflight baseline. Reverse
  patch in scratch must reproduce all three reviewed pre-repair hashes.
- Verify B3 against the primary AWS documentation:
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-data-encryption.html
  Require the exact principal, action list, account, project bucket and
  encryption-context conditions; no broadening of root delegation or
  wildcard Allow beyond Resource="*" meaning this key. Check ARN naming
  and absence of a dependency cycle.
- Inspect the assertion on output.iam_controls.kms_policy independently.
  Confirm RED uses pre-fix policy plus the new assertion and fails for the
  actual mismatch, not unknown values/provider errors. Confirm GREEN,
  source continuity and exact counts.
- Preserve B1/B2/R1 controls, read-only graph role, EMR without DynamoDB,
  fixed-queue workflow, bounded capacity and private encrypted data.
- N9–N16 are NONBLOCKING and NOT repaired this round. Verify they are
  recorded and their implementation remains unchanged:
  N9 EMR service-role KMS; N10 wildcard ARN guard;
  N11 PLAUSIBLE empty metric widgets; N12 native observability gaps;
  N13 HTTPS test scope; N14 workflow IsPresent;
  N15 internal HTTP disclosure; N16 loader/writer identities deferred.
  N1/N2/N5 resolved as answered; N3/N4/N6 optional; N7 procedural;
  N8 addressed without instructor approval; R2 needs 12C plan; R3 no action.
- Reconcile retained hashes, all 67 source hashes/bytes/mtimes, build
  before/after equality, gate timing, fresh XML counts and expected probe.
  Preserve prior records except allowed appends and old 12B evidence.
  Current generated XML belongs to this repair gate; old XML hashes need
  not match newly regenerated output.
- No live S3 Vectors/KMS effectiveness is claimed. No real plan, account
  API, apply/destroy/import, paid call or security scanner ran. Account,
  profile, region and budget remain pending. EMR runtime, costs, quotas,
  live application composition and CloudWatch publisher remain unverified.
  No next subphase, reviewer, commit or push was started. All jobs finished.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for 12B including repair round 1.
2. ALL confirmed findings in one pass: severity, path:line, evidence,
   concrete failure input, impact, owner, acceptance check, blocking yes/no.
   Separate nonblocking observations and unverified gates.
3. All 14 exact report fields from docs/agent-runs/README.md.
4. A COMPLETE NEXT PROMPT in one fenced block with every fact filled:
   APPROVE: append your full review verbatim as user-supplied external
   review under Subphase 12B repair round 1; record B3 accepted and carries.
   Confirm approved 12B plus repair/review records committed; ask user if
   not. Never commit/push unless explicitly requested anew. After commit
   confirmation begin ONLY 12C Step 0 questions, requiring actual AWS
   account/profile/region/budget and explicit read-only plan authorization
   before account calls. Do not auto-start 12D. Preserve live/runtime/cost
   gates. Complete one authorized subphase, hand off and stop.
   REQUEST-CHANGES: record review; route only blockers to their owners.
   Infra owns infra/terraform, coordinator phase evidence, build-engineer
   post-final-freeze JDK 17 gate. Retain red/green evidence, rerun affected
   native gates plus full sbt check, return a complete independent recheck
   prompt, then stop. No unrelated repairs, 12C/12D or reviewer invocation.
'''
(RUN/'reviewer-prompt-12b-recheck-1.md').write_text(text)
print('Wrote complete readable independent recheck prompt from final observed evidence.')

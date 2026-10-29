You are the independent, read-only reviewer for ScholarChain Phase12,
Subphase12A repair round1, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read:
1. AGENTS.md, CLAUDE.md, docs/agents.md,
   .claude/agents/code-reviewer.md, docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase12.md
   Sections3–7, Subphase12A, Sections9–10; course Phase12 requirements:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-12-create-the-aws-infrastructure-in-terraform
3. docs/agent-runs/phase-12/review.md: complete user-supplied REQUEST-CHANGES,
   findings B1/B2 and N1–N8, and repair work order retained verbatim.
4. docs/agent-runs/phase-12/prompt.md, repairs.md, owner-report.md, test-report.md
   (12A repair round1 sections), and infra/terraform/README.md.
5. docs/agent-runs/phase-12/evidence/12a-repair-1/README.md and all referenced
   evidence; original12A evidence remains under evidence/12a/.

Checkpoint facts:
- Branch phase-12; base SHA and HEAD both 649b13b9bb40b0b6218bf7f2b71ab9d541c7aafe.
  No commits/pushes, no reset/discard. Existing12A uncommitted state was explicitly
  authorized for repair. Changed tracked file remains .gitignore, unchanged in
  this round. 134 untracked files total; exact complete file list and5-file
  repair list: evidence/12a-repair-1/handoff-files.json.
- Only5 of41 Terraform files changed from reviewed12A:
  infra/terraform/README.md
  infra/terraform/modules/identity/main.tf
  infra/terraform/modules/network/main.tf
  infra/terraform/modules/network/outputs.tf
  infra/terraform/tests/phase12a.tftest.hcl
  infra-repair.patch and before/after SHA256 freeze prove the bounded diff.
  repair-patch-reconciliation.json reconstructs all5 original reviewed hashes.
- Owner /root/infra_12a wrote only these B1/B2 source changes. /root/build_12a
  ran the full JDK17 gate and generated its ignored marker, no authored edits.
  Coordinator assembled review/routing/evidence and appended reports. Exact
  inherited model IDs unavailable. No reviewer or nested agent launched.
- Step0: No questions. Prior accepted recommendations unchanged; account/profile,
  region and budget remain unset. User wants reminder before account is required:
  before12C real planning, or earlier separately approved12D. No account needed now.
- B1: removed ALL DynamoDB actions from EMR data policy. Added mock-plan assertion
  over iam_controls.emr_data_policy rejecting DynamoDB and wildcard actions.
  README distinguishes separate storage loader identities. No per-table ARN
  differentiation needed for this no-DynamoDB alternative. Before-fix test exited1,
  12passed/1failed at the new assertion; repaired baseline passes.
- B2: routes consolidated into aws_route.default; data_route_count counts actual
  instances whose route_table_id is data's. Removed mock inline route=[];
  distinct route-table IDs supplied. Test enforces canonical route declaration
  across ALL network module *.tf files and forbids inline routes. Source guard
  is conservative text inspection, not a general HCL policy engine.
- Isolated scratch mutations: adding a data default route fails isolation;
  adding standalone rogue route in NEW module file fails declaration guard.
  Each native test exited1 with12passed/1failed; init0. Exact patches, scripts,
  diagnostics and hashes retained. Repo source unchanged by experiments.
  First helper postprocessing failed on wrapped diagnostics after correct red
  test; attempt1 retained, corrected whitespace handling helper exited0.
  One development fmt exit is explicitly unknown; final independent fmt-check0.
- Final Terraform1.13.5/AWS6.44.0 pins/lock unchanged. Cwd infra/terraform,
  executable /tmp/scholarchain-phase12a-infra-toolchain/terraform:
  init -backend=false -input=false -no-color:0
  fmt -check -recursive:0
  validate -no-color:0
  test -no-color:0;13passed/0failed,29assertions,6expected-failure cases.
  All13 runs mock_provider aws and command=plan; no apply command.
  Exact history/cwds/exits/SHA256: infra-command-manifest.json.
  git diff --check:0; no out-of-scope paths.
- Source freeze2026-10-28T21:33:23.682294Z; full gate started
  2026-10-28T21:34:18.242955Z, ended2026-10-28T21:46:27.766216Z.
  From repository root, required environment:
  export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  export PATH="$JAVA_HOME/bin:$PATH"
  export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
  java -version:0; sbt -batch check:0. sbt1.10.7/JDK17.0.20.1.
  1253tests,156/156fresh XML,0failures/errors/skips;729.463s wall,727s sbt.
  Expected checkProbeInjectFailure only. Final XML/log counts computed/reconciled.
  All41 Terraform plus.gitignore hashes/bytes/mtimes unchanged during gate.
- Evidence paths: docs/agent-runs/phase-12/evidence/12a-repair-1/.
  build-start.json, build-result.json, build-validation.json,
  build-source-before.json, build-source-after.json,
  coordinator-final-validation.json, infra-source-freeze.json and coverage.
  Durable full log sbt-check.log.gz; decompressed SHA256
  390b4f7ad2c62309a3df98f1fe0f9ad8abfdd1f599ea879a264d175dfe07fc3a.
  Original40 report/evidence files preserved; aggregate reports appended only.
- N1–N8 recorded, no unrelated fixes. B1 necessarily adds EMR assertion relating
  to part of N4; no loader/KMS test expansion. Required gate ordering handles N7
  without rewriting original evidence. N1 EMRFS delete, N2 producer, N3 general
  mock ARNs, N4 other policies, N5 access-log encryption, N6 KMS cosmetic cleanup,
  N8 Step Functions/human decision remain carried. Course scripts deferred13.
- Unverified: real AWS plan, live IAM/KMS effectiveness, quotas/service regions,
  cost/budget filter, scanner, Neptune sizing, EMR runtime. No live AWS/API,
  apply/destroy/import, credential lookup, paid provider, commit or push occurred.
  B2 mutation snapshot predates final B1 wildcard guard tightening; B2 code and
  assertions unchanged. Final source freeze is authoritative.

Review rules:
- Read-only: no edits, builds/tests, AWS/provider calls, data changes, commits,
  pushes, secrets/state reads or agent launches. Read retained gzip/diffs normally.
- Inspect git diff 649b13b9bb40b0b6218bf7f2b71ab9d541c7aafe plus untracked files. Since12A sources are
  untracked, use original41-file freeze and retained repair.patch/before-after
  hashes to verify repair scope. Report ALL confirmed findings in one pass.
- Verify B1/B2 acceptance, meaningful failing-before/passing-after proof, final
  green logs/counts/hashes, source freeze before full gate, no changes outside
  B1/B2, correct ownership, no secret/cloud/spend violations, N1–N8 carried.
- Distinguish blockers, nonblocking observations and unverified gates. Do not
  demand12B/12C/12D work. Implementation reports are not reviewer approval.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase12A repair round1.
2. Findings: severity,path:line,evidence,impact,owner,acceptance,blocking yes/no;
   explicitly disposition B1/B2 and carry N1–N8.
3. Exact report fields from docs/agent-runs/README.md.
4. COMPLETE NEXT PROMPT in one fenced block:
   If APPROVE: append your COMPLETE review verbatim to phase-12/review.md marked
   user-supplied external review; append accepted B1/B2 dispositions to repairs.md;
   confirm user committed12A+repair (ask/wait if not); then start ONLY12B from
   named plan with Step0 questions. Preserve open account/budget/region/EMR
   decisions and account reminder. Return new complete reviewer prompt, no
   reviewer launch, then stop. Do not begin a second subphase.
   If REQUEST-CHANGES: append complete review verbatim and route blocking findings
   to owners in repairs.md; repair ONLY listed blockers; rerun affected gates
   and full JDK17check after final edits; do not start12B; return complete recheck
   prompt; stop. Never auto-launch any reviewer or commit/push.

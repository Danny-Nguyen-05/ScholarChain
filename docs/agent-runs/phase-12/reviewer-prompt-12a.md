You are the independent, read-only code reviewer for ScholarChain Phase 12,
Subphase 12A, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase12.md
   — Sections 3–7 and Subphase 12A in Section 8. Exact plan snapshot and user
   setup answers are also retained in docs/agent-runs/phase-12/prompt.md.
3. Course Phase 12 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-12-create-the-aws-infrastructure-in-terraform
4. docs/agent-runs/phase-12/prompt.md, owner-report.md and test-report.md
   (Subphase 12A), infra/terraform/README.md and all evidence under
   docs/agent-runs/phase-12/evidence/12a/.

Checkpoint facts:
- Branch: phase-12. Subphase base SHA: 649b13b9bb40b0b6218bf7f2b71ab9d541c7aafe.
  Current HEAD: 649b13b9bb40b0b6218bf7f2b71ab9d541c7aafe. No agent commit or push.
- Changed tracked files: .gitignore.
- Untracked files (81 total), exact list:
- docs/agent-runs/phase-12/evidence/12a/README.md
- docs/agent-runs/phase-12/evidence/12a/authority-reading.json
- docs/agent-runs/phase-12/evidence/12a/build-evidence-reconciliation.json
- docs/agent-runs/phase-12/evidence/12a/build-ignore-checks.json
- docs/agent-runs/phase-12/evidence/12a/build-owner-report.txt
- docs/agent-runs/phase-12/evidence/12a/build-result.json
- docs/agent-runs/phase-12/evidence/12a/build-sbt-check-excerpt.txt
- docs/agent-runs/phase-12/evidence/12a/build-start.json
- docs/agent-runs/phase-12/evidence/12a/build-validation.json
- docs/agent-runs/phase-12/evidence/12a/coordinator-validation.json
- docs/agent-runs/phase-12/evidence/12a/handoff-files.json
- docs/agent-runs/phase-12/evidence/12a/infra-command-manifest.json
- docs/agent-runs/phase-12/evidence/12a/infra-coverage.json
- docs/agent-runs/phase-12/evidence/12a/infra-final-command-results.json
- docs/agent-runs/phase-12/evidence/12a/infra-fmt-development-2.txt
- docs/agent-runs/phase-12/evidence/12a/infra-fmt-development.txt
- docs/agent-runs/phase-12/evidence/12a/infra-fmt-final.txt
- docs/agent-runs/phase-12/evidence/12a/infra-init-2.txt
- docs/agent-runs/phase-12/evidence/12a/infra-init.txt
- docs/agent-runs/phase-12/evidence/12a/infra-manual-checklist.json
- docs/agent-runs/phase-12/evidence/12a/infra-native-vector-schema-check.json
- docs/agent-runs/phase-12/evidence/12a/infra-owner-report.md
- docs/agent-runs/phase-12/evidence/12a/infra-source-freeze.json
- docs/agent-runs/phase-12/evidence/12a/infra-test-1.txt
- docs/agent-runs/phase-12/evidence/12a/infra-test-2.txt
- docs/agent-runs/phase-12/evidence/12a/infra-validate-1.txt
- docs/agent-runs/phase-12/evidence/12a/infra-validate-2.txt
- docs/agent-runs/phase-12/evidence/12a/infra-validate-final.txt
- docs/agent-runs/phase-12/evidence/12a/java-version.txt
- docs/agent-runs/phase-12/evidence/12a/ownership-and-reading.json
- docs/agent-runs/phase-12/evidence/12a/preflight.json
- docs/agent-runs/phase-12/evidence/12a/sbt-check.log.gz
- docs/agent-runs/phase-12/evidence/12a/sbt-log-integrity.json
- docs/agent-runs/phase-12/evidence/12a/step-0-answers.md
- docs/agent-runs/phase-12/evidence/12a/terraform-1.13.5-official-checksums.txt
- docs/agent-runs/phase-12/evidence/12a/terraform-cli-install.json
- docs/agent-runs/phase-12/owner-report.md
- docs/agent-runs/phase-12/prompt.md
- docs/agent-runs/phase-12/reviewer-prompt-12a.md
- docs/agent-runs/phase-12/test-report.md
- infra/terraform/.terraform.lock.hcl
- infra/terraform/README.md
- infra/terraform/environments/course.tfvars
- infra/terraform/main.tf
- infra/terraform/modules/datalake/main.tf
- infra/terraform/modules/datalake/outputs.tf
- infra/terraform/modules/datalake/variables.tf
- infra/terraform/modules/datalake/versions.tf
- infra/terraform/modules/dynamodb/main.tf
- infra/terraform/modules/dynamodb/outputs.tf
- infra/terraform/modules/dynamodb/variables.tf
- infra/terraform/modules/dynamodb/versions.tf
- infra/terraform/modules/foundation/bootstrap/main.tf
- infra/terraform/modules/foundation/bootstrap/outputs.tf
- infra/terraform/modules/foundation/bootstrap/variables.tf
- infra/terraform/modules/foundation/bootstrap/versions.tf
- infra/terraform/modules/foundation/main.tf
- infra/terraform/modules/foundation/outputs.tf
- infra/terraform/modules/foundation/variables.tf
- infra/terraform/modules/foundation/versions.tf
- infra/terraform/modules/identity/main.tf
- infra/terraform/modules/identity/outputs.tf
- infra/terraform/modules/identity/variables.tf
- infra/terraform/modules/identity/versions.tf
- infra/terraform/modules/messaging/main.tf
- infra/terraform/modules/messaging/outputs.tf
- infra/terraform/modules/messaging/variables.tf
- infra/terraform/modules/messaging/versions.tf
- infra/terraform/modules/network/main.tf
- infra/terraform/modules/network/outputs.tf
- infra/terraform/modules/network/variables.tf
- infra/terraform/modules/network/versions.tf
- infra/terraform/modules/runtime/main.tf
- infra/terraform/modules/runtime/outputs.tf
- infra/terraform/modules/runtime/variables.tf
- infra/terraform/modules/runtime/versions.tf
- infra/terraform/outputs.tf
- infra/terraform/providers.tf
- infra/terraform/tests/phase12a.tftest.hcl
- infra/terraform/variables.tf
- infra/terraform/versions.tf
- The same list is in evidence/12a/handoff-files.json. Ignore local provider
  cache/state; do not read secrets, credential files or state.
- User answer: “Use the recommendations; leave account, region, and budget pending.
  Tell me to create it when required”. Environment course; owner danny; expiration
  2026-11-25 provisional; local state; one NAT + S3/DDB gateways; required interface
  endpoints only; Step Functions/EventBridge/OpenSearch omitted per phase plan;
  manual scanner fallback; native S3 Vectors provider support verified; Neptune
  sizing/EMR runtime/spike pending. Budget and account/profile/region unset;
  7–10 day duration is provisional, not spending approval. No AWS account needed
  now; account reminder is due before12C or earlier approved12D.
- Owners: /root/infra_12a wrote only infra/terraform/**;
  /root/build_12a wrote .gitignore and generated ignored successful test marker;
  coordinator assembled docs/agent-runs/phase-12/**. Models inherited; exact
  identifiers not exposed. No reviewer or nested agent was launched.
- Commands/results (Terraform1.13.5, AWS6.44.0; cwd infra/terraform):
  /tmp/scholarchain-phase12a-infra-toolchain/terraform init -backend=false -input=false -no-color:0.
  Same tool: fmt -check -recursive:0; validate -no-color:0;
  test -no-color:0,13 passed/0 failed,27 assertions+6 expected-failure cases.
  Initial test:0,11/0 with fixed GSI deprecation warning. One intermediate fmt
  parse failure:2, fixed. Two Python development errors:1, disclosed; original
  failure outputs survive only in tool transcript. Exact historical commands,
  cwds and retained-log SHA256 are in infra-command-manifest.json.
  git check-ignore matrix:33/33 expected results. git diff --check:0.
  Root gate used JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home,
  PATH="$JAVA_HOME/bin:$PATH",
  SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml";
  java -version:0; sbt -batch check:0,1253 tests/156 fresh XML,0 failures/errors/skips,
  722.354s wall. Expected checkProbeInjectFailure self-test only.
- Evidence: docs/agent-runs/phase-12/evidence/12a/README.md maps all files.
  Full durable sbt log: sbt-check.log.gz; decompressed SHA256
  aa3fc6b34ee2797205a4199ef6a7d37c87bb7f14b1a4ed3b25c76d0d20b20af1.
  Terraform final logs, manifests,41-file source freeze, limited manual checklist,
  schema proof, tool install checksum and ownership/preflight retained.
- Limitations: no live AWS plan/apply/destroy/import/API call, account, cost fit,
  runtime compatibility or scanner result. Deployment role is trust-only; EMR
  service control-plane and Neptune/vector/Bedrock grants await later owning
  resources. Bootstrap is unreferenced/mock-tested, no remote migration. S3
  prevent_destroy remains literal true; cleanup needs extra human-reviewed source
  change. Course explicitly requires Step Functions although phase plan omits it;
  human/instructor resolution needed before full phase closure. Course scripts
  deferred to13. Git-SHA image tag naming enforcement belongs to13. Native S3
  locking vs deprecated DynamoDB locking is documented; no design migration done.
- Future scope:12B Neptune/S3Vectors/EMR/ECS/ALB/scaling/observability;12C actual
  read-only plan/checksum/cost/security prep;12D separately approved live spike.
- Prior external findings/repair rounds: none for12A. Authoring iterations are
  disclosed in command manifests, not an external review verdict.

Review rules:
- Read-only. Do not edit files, run builds/tests, call AWS or providers, change
  data, commit or push. Do not read secrets. Reading retained compressed logs is
  allowed. Do not launch agents.
- Inspect git diff 649b13b9bb40b0b6218bf7f2b71ab9d541c7aafe plus every untracked source/evidence file.
  Report ALL confirmed findings in one pass.
- Check one writer per path, configuration rather than hardcoded live inputs,
  no secret values, honest retained evidence, hand-derived meaningful feature
  tests, cloud/spend gates, and disclosed lean omissions.
- For12A check pinned provider/CLI, foundation/network/identity/datalake/six
  application DynamoDB tables/GSI/SQS-DLQ/ECR and local state hygiene. Optional
  unreferenced bootstrap lock table is separate from the six application tables.
- Check wildcard IAM Allow and its written exceptions, public access, graph
  reader write permissions, protections and explicit cleanup, correct encryption,
  role/SG boundaries, no invented actual account/model/resource identity, and
  bounded12A queue settings. Universal TLS wildcard Deny is not a public Allow.
- Do not demand later modules/live plan/cost/autoscaling tests in12A. Record
  course/plan Step Functions discrepancy and deferred scripts as unresolved full
  phase issues, not claimed waivers. Distinguish blockers, nonblocking
  observations and unverified gates. No implementation or agent may approve itself.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase12A.
2. Findings: severity,path:line,evidence/reasoning,impact,owning agent,
   acceptance check,blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A NEXT PROMPT for the main agent in one fenced code block:
   - If APPROVE: append this complete returned verdict/findings/report text
     verbatim to docs/agent-runs/phase-12/review.md under Subphase12A marked
     user-supplied external review; confirm user committed12A (ask/wait if not);
     start ONLY12B from the named plan, beginning with Step0 questions; retain
     unresolved account/budget/region and EMR decisions; do not call AWS without
     authorization. End with complete reviewer prompt and stop. No reviewer launch.
   - If REQUEST-CHANGES: append complete verdict verbatim to review.md and
     findings to repairs.md; route blocking findings to named owners; fix ONLY
     those findings; rerun affected tests and full sbt check on JDK17; do not
     start12B; return complete recheck reviewer prompt; stop. Nonblocking
     findings are listed but not required. No reviewer launch.

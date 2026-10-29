# Subphase12B handoff

Status: local implementation/gates complete; independent review pending.
Branch: phase-12. Base/HEAD: a83f62e9af56058a170075f98c4e027d039567ec. No12B commit/push.

Native Terraform:31 passed/0 failed (13 retained12A+18new12B),51 assertions,16 expected-failure cases. Three retained mutations each init0/test1,30passed/1failed, with intended diagnostics and repository unchanged. Full JDK17 sbt: exit0,1253tests,156/156fresh XML,0failures/errors/skips;721.615s gate wall time (721.485s sbt wall). Expected checkProbeInjectFailure self-test only. Raw/decompressed sbt SHA256 72d8f26147b49d7c3cc5cf017183c33eab52e7c4c969c955b3d5033b5030d8a8.

Final git footprint:17 modified tracked files and129 untracked files. Source footprint:13 modified infra files and25 new;67 frozen. Full final tracked/untracked names/counts are in handoff-files.json. Coordinator docs only outside infra.

Accepted Step0 answers: Account/profile/region and budget pending, no spending authorized; course environment. Neptune Serverless 1–2.5 NCUs, seven-day backups, private/CMK/IAM/protected, disabled until engine/family selection. EMR disabled pending explicit verified release/runtime/bootstrap/TLS and concrete control-plane policy; one primary, one core, at most two task nodes, no Spot. Prefix-scoped output deletes only. Fixed-queue Step Functions producer, production caller deferred13. ALB access logs off, cert pending, empty public ingress, HTTPS only when configured, no HTTP. Runtime disabled; activated defaults512CPU/1024MiB, HTTP services min1/max2 CPU60%, worker min1/max4 backlog10/task. Five Phase7 indexes,256/cosine/float32, exact non-filterable textS3Uri. Configurable TitanV2 embedding; synthesis unset/no query-model grant. Logs7days; alarms5% HTTP errors,5s p95 latency,300s queue age; SNS unset. Add functional Step Functions with least privilege, retries and DLQ. Current unconfigured app composition and custom-metric publisher remain explicit Phase13/14 dependencies; graph replicas require shared cursor-key ARN. Complete accepted recommendations and verbatim user acceptance: evidence/12b/step-0-answers.md.

Exact commands:

```bash
From /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform:
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
```

Evidence: this directory, infra/commands.json and owner-report.md, negative-results-v2.json, both source freezes, build-start/result/validation.json, compressed full sbt log, retention manifests and coordinator-final-validation.json. Reviewer prompt: ../../reviewer-prompt-12b.md.

Limitations: No real AWS plan, apply/destroy/import, account API, credential lookup or paid model call. Live IAM/KMS/region/quotas, engine availability, cost/budget-filter activation, EMR Spark compatibility and output commits remain unverified. Native plans use only mock_provider aws / command=plan. No security scanner ran; manual source/schema/feature checks are disclosed. Current service artifacts remain unconfigured/readiness503; acknowledgments in tests are synthetic and do not prove production readiness. No live CloudWatch application publisher or notification recipient exists. EMR service policy is pending, not replaced by a broad default; the synthetic DescribeInstances-only fixture cannot launch a cluster. S3/vector prevent_destroy needs separately reviewed source changes for cleanup. OpenSearch, EventBridge and Glue omitted; scripts deferred13. Step Functions is now authored under the user's selection, without instructor/full-course approval. No commits/pushes in12B.

Manual actions: independent user review then commit approved work. Create/configure an AWS account before12C or an earlier separately approved12D; select account/profile/region/budget and remaining engine/runtime/deployment inputs at that gate. All delegated agents completed and report no jobs remaining; build session16091 exited. No next subphase started.

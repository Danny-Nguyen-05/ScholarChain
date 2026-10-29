# Subphase 12A

STATUS: COMPLETE (12A local deterministic gates only)
OWNER: coordinator assembling infra-engineer and build-engineer observed evidence; no independent reviewer verdict implied.
WORK ORDER: Test Phase 12A configuration and required repository gate without AWS access.
FILES CREATED: Native tests are infra/terraform/tests/phase12a.tftest.hcl (infra-engineer); coordinator evidence under evidence/12a/. Full inventory: evidence/12a/handoff-files.json.
FILES MODIFIED: None by coordinator outside phase evidence. Build-engineer owns .gitignore and generated ignored test marker.
COMMANDS RUN:
- In infra/terraform, /tmp/scholarchain-phase12a-infra-toolchain/terraform init -backend=false -input=false -no-color: exit 0.
- Same directory/tool, fmt -check -recursive: exit 0; validate -no-color: exit 0; test -no-color: exit 0 (13/0).
- git check-ignore --no-index matrix: 33 expected ignore/visibility assertions passed.
- From repository root, export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; export PATH="$JAVA_HOME/bin:$PATH"; export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"; java -version; sbt -batch check: both exit 0.
- git diff --check: exit 0. Coordinator JSON/XML/hash reconciliation: exit 0, zero mismatches.
- Historical commands and fixed development failures: infra-command-manifest.json. Initial native tests 11/0 with GSI deprecation warning; final 13/0 without warnings. One intermediate fmt parse failure exit 2 fixed; Python development errors exit 1 disclosed there.
TEST RESULTS: 13 Terraform mock plan runs; 27 explicit assertions; 6 expected-failure cases. Coverage mapped in infra-coverage.json. Full Scala gate: 1,253 tests, 156 fresh XML reports, 0 failures/errors/skips; XML/log counts match. Build self-test's injected format-stage failure is expected; overall check exit 0 and successful marker recorded.
VALIDATION RESULTS: Exact pins Terraform 1.13.5/AWS 6.44.0; final fmt/validate pass; native vector schema support verified. All XML hashes and retained raw sbt hash reconciled. Source has 13 plan commands, zero apply commands, and mock_provider aws. No out-of-scope changes. Evidence includes full compressed sbt log, excerpt, command manifests, checksums, manual checklist and source freeze.
ASSUMPTIONS: Synthetic mock account/region/ARN/budget values are fixtures only. No account is required to run these local gates; provider installation needs network.
RISKS: Mocks/schema checks do not establish live authorization, service availability, quotas, prices, deletion behavior or runtime compatibility. Scanner not run; selected-pattern/manual checks are limited. No real AWS plan/checksum exists yet; those are 12C. No live EMR spike, services or model invocation was tested.
MANUAL ACTION REQUIRED: Independent read-only 12A review, then human commit. Create/configure AWS account when 12C needs it, or before earlier approved 12D; no account action required for 12A.
BLOCKED-ON OWNER: None for local 12A gates.
BLOCKED-ON EVIDENCE: None for local gates. Live tests and plan remain unverified future scope.
NEXT GATE: User launches read-only reviewer; stop at 12A.

## 12A repair round 1

STATUS: COMPLETE (required local repair gates; independent recheck pending)
OWNER: coordinator assembling infra-engineer and build-engineer observed reports, not an independent reviewer.
WORK ORDER: B1/B2-only repair; full repository gate after final Terraform edits.
FILES CREATED: Separate evidence/12a-repair-1/ packet; tests remain in existing infra/terraform/tests/phase12a.tftest.hcl.
FILES MODIFIED: Test file and4related Terraform/README files by infra-engineer only. Original test-report section preserved verbatim; no other production owner edits.
COMMANDS RUN: From infra/terraform, /tmp/scholarchain-phase12a-infra-toolchain/terraform init -backend=false -input=false -no-color:0; fmt -check -recursive:0; validate -no-color:0; test -no-color:0. git diff --check:0. Exact scratch commands and initial helper failure/unknown development fmt status in infra-command-manifest.json. From repository root, export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; export PATH="$JAVA_HOME/bin:$PATH"; export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"; java -version:0; sbt -batch check:0.
TEST RESULTS: Terraform13passed/0failed,29assertions,6expected-failure input cases; mock_provider aws,13command=plan,0apply. B1 before-fix regression12passed/1failed exit1; canonical-data-route and standalone-new-file mutations each12passed/1failed exit1 as expected. Full sbt1253tests/156fresh XML,0failures/errors/skips;729.463s wall,727s sbt. Counts reconciled programmatically. checkProbeInjectFailure is expected self-test.
VALIDATION RESULTS: Final native gates0; same pinned CLI/provider/lock. Source freeze21:33:23.682294Z precedes full gate start21:34:18.242955Z/end21:46:27.766216Z. All41Terraform plus.gitignore hashes/bytes/mtimes unchanged during gate; all156XML hashes match; full raw/decompressed sbt SHA256390b4f7ad2c62309a3df98f1fe0f9ad8abfdd1f599ea879a264d175dfe07fc3a matches retained gzip and build result. Patch reverse-reconstruction matches all5old hashes. No source scope drift.
ASSUMPTIONS: Synthetic mock fixtures only; account/profile/region/budget unset; source guard enforces the canonical network route convention.
RISKS: Mocks do not prove live AWS behavior. No real plan/scanner/runtime/cost gate. N1–N8 carried without unrelated repairs; B1 adds only its required EMR policy assertion and required gate ordering handles N7. Negative cases' source snapshot predates final B1 wildcard predicate; B2 unchanged.
MANUAL ACTION REQUIRED: User launches independent recheck, then commits approved work. Account reminder before12C or earlier approved12D; no account needed now.
BLOCKED-ON OWNER: None for required local gates; reviewer owns acceptance.
BLOCKED-ON EVIDENCE: None for required local gates; live gates unverified.
NEXT GATE: Independent read-only12A repair1 recheck; stop at this repair.

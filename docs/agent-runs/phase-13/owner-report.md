# Phase 13 owner reports

## Subphase 13A — check, package, plan, deploy, rollback, cleanup

Assembled by the Claude Code orchestrator from the agent reports and the orchestrator's own checks. Branch `phase-13`. Base SHA `8bee663040ba4e66b1edc1676d5346621c3f7384`. HEAD is unchanged; nothing is committed. Agents: `build-engineer` and `infra-engineer`, both launched with model `sonnet` (Sonnet 5.5) at effort `high`, as the user asked. Native agent IDs: build-engineer `ab501a4a617dd57dc`; infra-engineer `a36d15cf3230ed85b` (first pass plus one repair continuation, same agent). No reviewer was launched.

### build-engineer

```text
STATUS: COMPLETE
OWNER: build-engineer
WORK ORDER: docs/agent-runs/phase-13/prompt.md, Subphase 13A. Close Phase 6 finding 6A F6 (packaging not guarded by the JDK check); add one release-packaging alias for scripts/package.sh.
FILES CREATED: project/verification/src/test/scala/scholarchain/build/PackagingJava17GuardSpec.scala
FILES MODIFIED: build.sbt; project/ScholarChainBuild.scala; project/HadoopPackaging.md. Dockerfile unchanged.
COMMANDS RUN:
- sbt -batch packageRelease under JDK 27 (negative probe)
- sbt -batch <task> under JDK 27 for 12 packaging tasks and aliases
- sbt -batch <per-module clean> packageRelease on JDK 17, twice
- sbt -batch "buildVerification/testOnly ...PackagingJava17GuardSpec ...", with and without SCHOLARCHAIN_NON17_JAVA_HOME
- sbt -batch check on JDK 17, twice
- docker buildx imagetools inspect <base digest>
- docker buildx build --platform linux/amd64 --load (QueryApiMain probe)
TEST RESULTS:
- sbt -batch check, run 2: exit 0, 759 s.
- Per-module tests (all 0 failed): core 207, hadoop 64, entityResolution 39, sparkAnalytics 50, storage 80, rag 107, services 40, independentTests 667, buildVerification 18 succeeded with 1 canceled. The canceled test is the optional live non-17 probe, which is skipped when SCHOLARCHAIN_NON17_JAVA_HOME is unset.
- Run 1 failed at scalafmtSbtCheck because ScholarChainBuild.scala was not formatted (exit 1); fixed with scalafmtSbt.
- PackagingJava17GuardSpec with the live probe enabled (JDK 27): succeeded 6, failed 0.
VALIDATION RESULTS:
- Under JDK 27, packageRelease and 12 other packaging entry points exit 1 with "ScholarChain check requires Java 17; found Java 27. ...".
- The mtimes and sizes of the jars were unchanged after the refused tasks.
- JDK 17 packageRelease: exit 0.
- The amd64 probe image built and inspected as linux/amd64. The base image index includes linux/amd64.
ASSUMPTIONS: The guard message wording is reused unchanged. The guard is scoped to ThisBuild. Every Compile/packageBin is guarded (a no-op on JDK 17).
RISKS: The Hadoop submit JAR is not byte-reproducible (it embeds timestamps), so record its hash after each build. buildx adds attestation manifests by default; package.sh disables them.
MANUAL ACTION REQUIRED: Independent review.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: User-launched review of 13A.
```

Evidence: `evidence/13a/build/`. The full sbt log (1.7 MB) stays outside Git; `check-jdk17-excerpt.txt` holds the result lines.

### infra-engineer (first pass and repair continuation)

```text
STATUS: COMPLETE (after the user-authorized repair pass; the first pass ended PARTIAL on a base Terraform test defect)
OWNER: infra-engineer
WORK ORDER: Orchestrator work order derived from plan Section 7.1 and the Step 0 answers, plus the follow-up message carrying the user's mid-subphase decisions (prompt.md) and the orchestrator's config-pin item.
FILES CREATED:
- scripts/check.sh, package.sh, plan.sh, deploy.sh, rollback.sh, cleanup.sh
- scripts/lib/common.sh, lib/timeout.py, lib/tools.py, lib/plan_summary.py
- scripts/config/release.conf
- scripts/tests/fake_tool.py, helpers.py, test_timeout.py, test_deploy.py, test_package.py, test_plan.py, test_rollback.py, test_cleanup.py, test_check.py, test_syntax.py, test_safety.py, test_terraform_r1.py
FILES MODIFIED:
- scripts/README.md: Phase 13 section appended; the phase4 content is unchanged.
- infra/terraform/tests/phase12b.tftest.hcl: one line (R1 fileset also accepts "spikes/"). This was a scope widening the user authorized in 13A.
COMMANDS RUN (outputs in evidence/13a/infra/):
- bash -n and shellcheck -x -P SCRIPTDIR on all 7 shell files
- cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py'
- cd infra/terraform && terraform init -backend=false -input=false -lockfile=readonly && terraform test
- scripts/package.sh (real run: jars plus 4 linux/amd64 images)
- Dry runs of plan.sh, deploy.sh, rollback.sh, cleanup.sh (real repo and a synthetic clean temp repo)
- scripts/check.sh --only <fast gates> from a clean temp copy of tracked and new files
- scripts/check.sh full default run: first pass (check-full.txt), and once on the final tree (check-full-r1.txt)
TEST RESULTS:
- scripts/tests: 148 tests OK (final tree).
- Root terraform test: 40 passed, 0 failed (39/1 before the R1 fix).
- First full check.sh: exit 4. Only the terraform gate failed (root R1 test, base defect from f52b981); sbt PASS 749 s.
- Final full check.sh: RESULT: PASS gates=7, exit=0, 992 s. Gates: constitution, hooks, shell, python, script-tests (208 s), sbt (758 s), terraform (24 s).
VALIDATION RESULTS:
- shellcheck 0.11.0: zero findings.
- package.sh: exit 0. Architecture gate passed (all four images linux/amd64; ECS cpu_architecture X86_64 maps to linux/amd64).
- G5 archive verified: 321876735 bytes, sha256 789a9684…6de5. Nothing uploaded.
- Release manifest: commit 8bee663…, dirty=true, tag <sha>-dirty.
- Deploy dry run on a clean synthetic repo with a matching record: RESULT: DRY-RUN, exit 0, 17 steps, no cloud command.
- Deploy refusals: plan checksum exit 3; missing record exit 3.
- plan, rollback and cleanup dry runs: RESULT: DRY-RUN, exit 0.
ASSUMPTIONS:
- Only the exact approval-record path is exempt from the dirty-tree refusal (user accepted).
- Two-stage rollback --execute (user accepted).
- S3 runtime-archive upload verification uses size plus sha256 object metadata via head-object.
- Pinned config keys cannot be overridden by an environment variable: REQUIRED_TERRAFORM_VERSION, RUNTIME_ARCHIVE_EXPECTED_SHA256, RUNTIME_ARCHIVE_EXPECTED_SIZE, IMAGE_PLATFORM, ECS_ARCH_SOURCE, APPROVAL_RECORD_PATH, SERVICE_ARTIFACTS. Test-only SCHOLARCHAIN_CONFIG_FILE is announced on stdout.
RISKS:
- A first deployment needs an approved base apply before the image push, because of the ecr-repositories-exist refusal (user accepted; documented).
- Destroy may need cleanup_mode=true applied before DynamoDB deletion protection is released (unverified live).
- The terraform gate needs network for provider downloads when .terraform is absent.
- test_terraform_r1.py is skipped without Terraform 1.13.5 or provider access.
- An unrelated tracked directory named `file:` exists in the repo root (Oct 7 Hadoop test artifacts); not addressed.
MANUAL ACTION REQUIRED: None new for 13A. Phase 14 decisions remain with the human.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: User-launched review of 13A.
```

An incidental side effect was reverted: the first terraform-gate run added `zh:` hashes to the tracked lock files `infra/terraform/deployer/.terraform.lock.hcl` and `infra/terraform/spikes/emr-spark-isolated/.terraform.lock.hcl`. infra-engineer restored both with `git checkout --` and changed the gate to `init -lockfile=readonly`. A later lock-file change now fails the gate. `git status -- infra` on the final tree shows only `phase12b.tftest.hcl`.

### Orchestrator checks (observed)

- **Preflight:** clean tree at base; JDK 17.0.20.1; Terraform 1.13.5; shellcheck 0.11.0; Docker 29.5.3 on linux/arm64; G5 tgz 321876735 bytes with sha256 `789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5`.
- **Before the agents:** shellcheck on all 11 previously tracked `*.sh` files gave zero findings.
- **Base defect:** confirmed that `infra/terraform/tests/phase12b.tftest.hcl:136` scans every `**/*.tf`, including `spikes/emr-spark-isolated/network.tf` from `f52b981`. The user chose to fix it in 13A.
- **Final tree:** no files are newer than the infra-engineer pre-run tree snapshot (`tree-before-full-check-r1.txt`), so `check-full-r1.txt` covers the final tree.
- **Independent reruns, all in `evidence/13a/orchestrator/`:**
  - `bash -n` and shellcheck: rc 0.
  - scripts/tests: 148 OK, 115 s.
  - `check.sh --only shell,constitution,hooks,python`: exit 5, `RESULT: PARTIAL`.
  - `deploy.sh` on the real dirty tree: exit 3, `RESULT: REFUSED step=clean-tree`.
- **Interrupted run:** an orchestrator full `check.sh` run started before the repair pass was stopped by the orchestrator (exit 144) once the repair was routed. Its partial output is not used as evidence.

### Lean-scope omissions

- No GitHub Actions workflows (plan lean scope).
- No real plan, deploy, rollback or cleanup execution. Every `--execute` path is exercised only against fakes.
- The 13B scripts (`smoke-test.sh`, `run-bounded-pipeline.sh`, `run-experiment.sh`, `archive-evidence.sh`) and the YARN-kill logic (item 1) were not authored.
- No retry helper.
- G6 (USD 9.50 to Phase 15; USD 3 per run; at most 3 live EMR runs) is recorded in `prompt.md` and is enforced in the 13B pipeline/experiment scripts, not in 13A.

## Subphase 13A — repair round 1

The trigger was the external review (REQUEST-CHANGES, F1–F10 blocking, N1–N2 nonblocking); see `review.md` and `repairs.md`. The user's decisions for F3 (preservation classes) and F5 (pre-spend receipt, 24 h, USD 20) are recorded in `repairs.md`.

### infra-engineer (fresh context; native ID `ac3278ecc022a0927`; Sonnet 5.5, effort high)

```text
STATUS: COMPLETE (pending independent recheck)
OWNER: infra-engineer
WORK ORDER: 13A repair round 1: F1–F10 and N1, per review.md, repairs.md and the user decisions.
FILES CREATED: scripts/lib/redact.py, scripts/lib/verify.py, scripts/tests/test_verify_redact.py
FILES MODIFIED:
- scripts/plan.sh, deploy.sh, rollback.sh, cleanup.sh, check.sh
- scripts/lib/common.sh, timeout.py, tools.py, plan_summary.py
- scripts/config/release.conf
- scripts/README.md
- scripts/tests/fake_tool.py, helpers.py, test_deploy.py, test_plan.py, test_rollback.py, test_cleanup.py, test_check.py, test_safety.py, test_syntax.py, test_terraform_r1.py, test_timeout.py, test_package.py
- No file outside scripts/** was changed.
COMMANDS RUN (evidence/13a/repair-1/):
- bash -n + shellcheck -x -P SCRIPTDIR over 18 shell files
- cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v
- scripts/check.sh --only constitution,hooks,shell,python,script-tests,terraform
- dry runs via dry-runs/dryruns-harness.py (synthetic clean temp repo, fake binaries, synthetic receipts)
TEST RESULTS:
- scripts/tests: Ran 281 tests, OK, none skipped (the 10 R1 tests ran real Terraform 1.13.5 with mock providers).
- An earlier iteration had 1 failure, fixed: unittest-scripts-tests-run1.txt.
- check.sh partial run: exit 5, RESULT: PARTIAL passed=6 skipped: sbt.
VALIDATION RESULTS:
- shellcheck: 0 findings.
- Dry runs: plan (2), deploy (base-apply, push, runtime-apply), rollback (app, infra) and cleanup all exit 0 with RESULT: DRY-RUN.
- Refusals: stale pre-spend receipt exit 3; dirty tree exit 3.
- No synthetic private value or raw account ID appears in any output.
- Two self-found defects fixed: a raw account ID would have been kept in the task-definition ARN; registering a bare 12-digit ID as a substring secret could mangle checksums.
ASSUMPTIONS:
- A1: materialized previous sources live under the ignored PLAN_DIR/source/<sha> (read-only).
- A2: the teardown set adds the runtime IAM roles/policies/instance profile and the observability alarms/dashboard (open for the human).
- A3: PRESERVE wins over TEARDOWN; any other address is unlisted and refused.
- A4: each stage needs its own fresh pre-spend receipt.
- A5: infrastructure rollback skips the runtime-archive re-upload.
- A6: private-value redaction covers quoted values of at least 6 characters.
RISKS:
- Live Terraform/AWS behaviour is unverified: destroy -target dependents, the show -json layout, push digest output, ECS responses.
- A real destroy plan that pulls in an unlisted address refuses with POLICY-VIOLATION; the human then widens the pinned config.
- deploy.sh dry run needs the initialized checkout where plan.sh ran.
- The freshness check uses the local clock.
- Phase 14 access gate carried: the deployer permission sets lack ECR/ECS actions.
MANUAL ACTION REQUIRED: The human confirms or edits A2. Before Phase 14, review the --execute paths with the approved profile.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: Orchestrator clean-snapshot full check (done below), then the user-launched independent recheck.
```

### Orchestrator (repair round 1)

- **Repair records:** appended the reviewer verdict verbatim to `review.md`. Recorded F1–F10 and N1–N2 with their routing, the user decisions and the results in `repairs.md`.
- **N2:** renamed the git-ignored `.log` evidence in `evidence/13a/build/` to `.txt` excerpts, each with a command header.
- **F9 clean-snapshot evidence:**
  - Snapshot: `git ls-files -co --exclude-standard` copied into a fresh directory, `git init`, one local snapshot commit `1076eef9…`.
  - Command: `scripts/check.sh` → `RESULT: PASS gates=7`, exit 0, 21:13:51Z–21:36:05Z.
  - Gates: script-tests 440 s (281/70/69/47/39 executed, 0 skipped); sbt 787 s (40, 667, 18 + 1 canceled; 0 failed); terraform 102 s (7/19/29/38/6/40 passed).
  - Identity check: every working-tree source outside `docs/agent-runs/phase-13` matched the snapshot (5361 compared, 0 differing).
  - Evidence: `evidence/13a/repair-1/check-full-clean-snapshot.txt` and `clean-snapshot-manifest.txt`.
- **Scope check:** `git diff --stat` outside `scripts/**` is unchanged from the first handoff (build.sbt, project/**, the one-line phase12b test); shellcheck rc 0.
- **Working-tree sbt run:** `sbt -batch check` on JDK 17 in the real working tree, to refresh the repo's local test marker. Result: see `test-report.md`.

## Subphase 13A — repair round 2

The trigger was external review 2 (REQUEST-CHANGES: R1–R9 blocking, N3 nonblocking); see `review.md` and `repairs.md`. The user asked the orchestrator to fix all blocking findings. The orchestrator paused once for the user's usage budget, stopped the agent, and resumed it with its context.

### infra-engineer (fresh context; native ID `ac38b9848cff4b821`; Sonnet 5.5, effort high)

```text
STATUS: COMPLETE (pending independent recheck)
OWNER: infra-engineer
WORK ORDER: 13A repair round 2: R1–R9 and N3, per review.md (review 2) and repairs.md (round-2 section and orchestrator repair design).
FILES CREATED:
- scripts/lib/safeio.py, lib/state_bind.py, lib/records.py
- scripts/tests/test_safeio.py (15), test_state_records.py (21), test_terraform_state_binding.py (7, real Terraform 1.13.5 on local fixtures)
FILES MODIFIED:
- scripts/plan.sh, deploy.sh, rollback.sh, cleanup.sh
- scripts/lib/common.sh, timeout.py, redact.py, verify.py, plan_summary.py, tools.py
- scripts/config/release.conf (new pinned keys: TERRAFORM_STATE_FILE, CLEANUP_PROTECTION_RULES, CLEANUP_PREPARE_ALLOWED_ATTRS)
- scripts/README.md
- scripts/tests/helpers.py, fake_tool.py, test_plan.py, test_deploy.py, test_cleanup.py, test_rollback.py, test_safety.py, test_syntax.py, test_terraform_r1.py
- Nothing outside scripts/** was changed.
COMMANDS RUN (evidence/13a/repair-2/):
- bash -n + shellcheck -x -P SCRIPTDIR on the 7 release shell files
- cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v
- scripts/check.sh --only constitution,hooks,shell,python,script-tests,terraform
- N3: env -i HOME=$HOME PATH=/usr/bin:/bin TERRAFORM_BIN=/opt/homebrew/bin/terraform python3 -I -m unittest discover -s . -p test_terraform_r1.py -v
- dry runs via dryruns-harness.py
TEST RESULTS:
- scripts/tests: Ran 434 tests in 641.6 s, OK, 0 skipped.
- check.sh partial: exit 5, RESULT: PARTIAL passed=6 skipped: sbt.
- N3 run: 10/10 executed, 0 skipped, with no Terraform on PATH.
VALIDATION RESULTS:
- shellcheck: 0 findings.
- Dry runs: every dry run's fake log holds only `terraform version`. Inspection commands are printed as DEFERRED.
- Refusals shown: runtime-apply without a push record; a symlink at a derived plan output name; plan without a live state file.
ASSUMPTIONS:
- Live state is the local infra/terraform/terraform.tfstate (pinned TERRAFORM_STATE_FILE).
- New required approval lines: APPROVED_RECEIPT_SHA256 and APPROVED_ENVIRONMENT.
- New cleanup-prepare deploy stage; cleanup --confirm needs --plan.
- --prepare needs --image-revision when a runtime is deployed.
RISKS:
- The real checkout has no live state yet, so the first base apply needs plan.sh --expect-new-state.
- Fresh run dirs re-run terraform init, so set TF_PLUGIN_CACHE_DIR.
- Unverified live: protection attribute names, ECR/ECS behaviour, effective permissions, the two-pass destroy.
- scripts/tests now takes about 11 minutes.
MANUAL ACTION REQUIRED:
- Human: accept or adjust the approval-format additions and the cleanup-prepare stage.
- Human: decide A2.
- Human: confirm the live state location.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: Orchestrator clean-snapshot full check (done below), then the user-launched recheck.
```

### Orchestrator (repair round 2)

- **Repair records:** appended review 2 verbatim to `review.md`. Recorded R1–R9 and N3, the repair design, the results and the pending items in `repairs.md`.
- **Clean snapshot:** `git ls-files -co --exclude-standard` copied into a fresh directory, `git init`, local snapshot commit `c93c3763…`, then `scripts/check.sh`.
  - Result: `RESULT: PASS gates=7`, exit 0, 01:54:09Z–02:23:49Z (2026-11-06 UTC).
  - script-tests (827 s): 426 executed + 1 skipped / 70 / 69 / 47 / 39.
  - sbt (798 s): 40, 667, 18 + 1 canceled; 0 failed.
  - terraform (148 s): 7/19/29/38/6/40 passed.
- **The one skip:** the `test_terraform_state_binding` class needs providers, which a fresh snapshot only gets from the later terraform-gate init. Re-run in the snapshot afterwards: 7 tests OK, 0 skipped, exit 0 (`state-binding-in-snapshot.txt`).
- **Identity check:** 5367 compared, 0 differing.
- **Working-tree `sbt -batch check`, JDK 17.0.20.1:** exit 0, 742 s.
  - Tests: core 207, hadoop 64, ER 39, spark 50, storage 80, rag 107, services 40, independentTests 667, buildVerification 18 + 1 canceled; 0 failed.
- **Scope check:** the tracked diff outside `scripts/**` is unchanged (build.sbt, project/**, the one-line phase12b test).

## Subphase 13A — repair round 3

The trigger was external review 3 (REQUEST-CHANGES: S1 blocking; N4 and N5 nonblocking). The user chose S1 option (a), keeping the runtime. For verification, the user chose the fast gates in a clean snapshot, reusing the round-2 sbt evidence.

### infra-engineer (fresh context; native ID `a89ab5013d9c6e932`; Sonnet 5.5, effort high)

```text
STATUS: COMPLETE (pending independent recheck)
OWNER: infra-engineer
WORK ORDER: 13A repair round 3: S1 (option a), N4, N5, per review.md review 3 and repairs.md round 3.
FILES CREATED:
- scripts/lib/suite_run.py
- scripts/tests/test_runtime_rollback.py (51), test_runtime_guard.py (24), test_upload_checksum.py (9)
FILES MODIFIED:
- scripts/deploy.sh, rollback.sh, check.sh; plan.sh (help only)
- scripts/lib/verify.py, tools.py, records.py, common.sh
- scripts/config/release.conf (pinned RUNTIME_LIVE_MODULE, RUNTIME_LIVE_PROTECTED_TYPES)
- scripts/README.md
- scripts/tests/helpers.py, fake_tool.py, test_check.py, test_deploy.py, test_rollback.py, test_safety.py
- Nothing outside scripts/** was changed.
COMMANDS RUN (evidence/13a/repair-3/):
- shell-checks-harness: bash -n + shellcheck -x -P SCRIPTDIR on all 14 *.sh under scripts/
- cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v
- scripts/check.sh --only constitution,hooks,shell,python,terraform,script-tests
- dryruns-harness.py (11 dry-run transcripts)
- An early baseline run was contaminated by concurrent edits and was discarded.
TEST RESULTS:
- shellcheck: 0 findings; bash -n: 14 files, 0 failures.
- scripts/tests: Ran 529, OK, 0 skipped (434 previously; 95 tests added).
- check.sh partial: exit 5, RESULT: PARTIAL passed=6 skipped: sbt. Required classes executed 7 and 6, 0 skipped.
VALIDATION RESULTS:
- Each of the 11 dry runs makes 0 calls other than the Terraform version probe.
- A live runtime with no binding is refused at STEP runtime-state (exit 3).
- No new stage: a carried rollback uses APPROVED_STAGE=runtime-apply with APPROVED_COMMIT=PREV.
ASSUMPTIONS:
- The deploy-manifest fields match what tools.py writes. The environment is bound through the repository names.
- "Runtime live" means managed module.runtime resources of a protected type exist in state (v4 layout, checked only against fixtures).
- Task definitions are not protected types.
RISKS:
- Live behaviour is unverified: real state/show -json layout, ECS/ECR output, and real S3 multipart checksums.
- s3:GetObjectAttributes (and possibly KMS decrypt) is needed; this is part of the Phase 14 access gate.
- No pre-apply ECS read confirms that the named revision is the one currently deployed.
- The app rollback keeps its existing manifest check.
- The billing `files:` suites still use the older count.
MANUAL ACTION REQUIRED: Full seven-gate check after approval. Human decisions: A2, the approval-format additions, the live-state location.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: Orchestrator clean-snapshot gates, then the user-launched recheck.
```

### Orchestrator (repair round 3)

- **Records:** appended review 3 verbatim to `review.md`. Recorded S1, N4 and N5, the user's S1 decision, the N4 evidence-wording correction and the results in `repairs.md`. Recorded the decisions in `prompt.md`.
- **sbt-input identity:** compared the working tree with the repair-2 clean snapshot, which passed its sbt gate and the 742 s working-tree `sbt check`. Scope: `build.sbt`, `project`, `modules`, `.scalafmt.conf`, `.sbtopts`, `Dockerfile`, `tests`. Result: 459 compared, 0 differing, none missing (`sbt-input-identity.txt`).
- **Clean-snapshot gates:** fresh copy of `git ls-files -co --exclude-standard`, local snapshot commit `eea862df…`, then `scripts/check.sh --skip sbt`.
  - Result: `RESULT: PARTIAL passed=6 skipped: sbt`, exit 5, 04:04:53Z–04:23:07Z (2026-11-06 UTC).
  - terraform: 7/19/29/38/6/40 passed.
  - script-tests: scripts/tests 529 executed with 0 skipped tests and 0 skipped classes; the required classes executed 7 and 6; phase12d-spike 70; billing 69/47/39.
  - Snapshot identity: 5371 compared, 0 differing.
- **Working-tree marker:** not refreshed at handoff, because sbt was not run. After the handoff, a working-tree `sbt -batch check` exited 0 in 752 s (`repair-3/sbt-check-worktree-excerpt.txt`).

## Subphase 13A — repair round 4

The trigger was external review 4 (REQUEST-CHANGES: T1 blocking; O1 a disclosed nonblocking observation). The user asked the orchestrator to fix the blocking finding with an Opus 5.5 (effort high) subagent.

### infra-engineer (fresh context; native ID `ae02e16d0b35969ce`; model `opus` / Opus 5.5, effort high)

```text
STATUS: COMPLETE (pending independent recheck)
OWNER: infra-engineer
WORK ORDER: 13A repair round 4: T1, per review.md (review 4) and repairs.md (round 4).
FILES CREATED: scripts/tests/test_runtime_base_apply.py (31)
FILES MODIFIED:
- scripts/config/release.conf (new pinned RUNTIME_LIVE_INDICATOR_TYPES; RUNTIME_LIVE_PROTECTED_TYPES unchanged in value)
- scripts/lib/common.sh (pinned key added)
- scripts/lib/verify.py (absent/live/partial verdict; --indicators)
- scripts/rollback.sh, deploy.sh (indicator wiring, help)
- scripts/README.md (new "What runtime live means (T1)" section)
- scripts/tests/helpers.py (realistic state builders)
- scripts/tests/test_runtime_guard.py (three fixtures that encoded the wrong assumption)
- Nothing outside scripts/** was changed.
COMMANDS RUN (evidence/13a/repair-4/):
- bash -n + shellcheck -x -P SCRIPTDIR on every *.sh under scripts/
- cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_*.py' -v
- dry-runs-harness.py: 6 rollback dry runs on fixture states
TEST RESULTS:
- shellcheck 0.11.0: 14 files, 0 failures/findings.
- Ran 560 tests in 895.5 s, OK, 0 skipped. Round 3 had 529; 31 tests added.
VALIDATION RESULTS: dry runs, all with 0 calls beyond the version probe:
- (1) post-base-apply, no binding: accepted (DRY-RUN, base-apply delegate).
- (2) and (3) post-base-apply with a manifest or push-record binding: REFUSED at runtime-state, "would CREATE the runtime".
- (4) partial state: REFUSED, RUNTIME-LIVE-CHECK-FAILED.
- (5) live with a manifest binding: DRY-RUN.
- (6) live with no binding: REFUSED, "RUNNING runtime".
ASSUMPTIONS:
- The state v4 layout is checked only against fixtures.
- Other gated dependents (task definitions, service discovery, autoscaling) are not indicators.
- Listener count is 0–1, because it also needs certificate_arn.
- O1 is not implemented (it needs a live ECS read).
RISKS:
- All live paths are unverified.
- A partial state blocks rollback and base-apply until a human decides the recovery.
- While the runtime is not live, the cluster can be changed by base-apply (an accepted, tested boundary).
MANUAL ACTION REQUIRED: Orchestrator: full gates. Human: A2, approval-format additions, live-state location.
BLOCKED-ON OWNER: none for T1
BLOCKED-ON EVIDENCE: none
NEXT GATE: Orchestrator full seven-gate clean-snapshot check.sh and JDK 17 sbt check, then the recheck.
```

### Orchestrator (repair round 4)

- **Records:** appended review 4 verbatim to `review.md`. Recorded T1, O1 and the results in `repairs.md`.
- **Working-tree `sbt -batch check`, JDK 17.0.20.1:** exit 0, 749 s, 0 failed. It ran concurrently with the agent's dry runs; sbt does not read `scripts/`, and no script file changed after the sbt run.
- **Full seven-gate `scripts/check.sh` in a clean snapshot** (local commit `2734d34e…`; no `--only`/`--skip`):
  - Result: `RESULT: PASS gates=7`, exit 0.
  - terraform 128 s: 7/19/29/38/6/40 passed.
  - script-tests 974 s: 560 executed, 0 skipped; the required classes executed 7 and 6; phase12d-spike 70; billing 69/47/39.
  - sbt 806 s: 40, 667, 18 + 1 canceled; 0 failed.
  - Snapshot identity: 5372 compared, 0 differing.
- **Deferred run now done:** this completes the full seven-gate run that was deferred in round 3.

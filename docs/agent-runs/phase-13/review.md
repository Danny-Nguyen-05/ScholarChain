# Phase 13 reviews

## Subphase 13A

### Review 1 — user-supplied external review (pasted by the user on 2026-11-05; reproduced verbatim)

VERDICT: REQUEST-CHANGES — Subphase 13A
Reviewed branch phase-13 at 8bee663040ba4e66b1edc1676d5346621c3f7384, including five modified tracked files and 50 non-ignored untracked files. HEAD still matches the handoff base. The changes fit the recorded ownership map and the one-line Terraform test exception. This was a read-only review. I made no edits, ran no builds or tests, and made no AWS or provider calls.
Blocking findings
P1 · F1 · Deploy can accept a dirty tree. Owner infra-engineer. Blocking yes. --approval adds a second Git exclusion beyond the agreed Phase 14 record. That exclusion uses pathspec matching, and the helper also honors an inherited SC_DIRTY_EXTRA_EXCLUDE. A failed git status produces an empty result and is treated as clean. A modified source path can therefore be excluded from the deployment gate. Acceptance — Only the literal agreed record path is exempt. Test an alternate in-repo approval path, an inherited exclusion, pathspec metacharacters, and a failing Git status. Each must refuse before AWS or Docker runs. Deploy exclusion · Git helper · Recorded decision
P1 · F2 · Deploy checks approval fields separately from the saved plan’s actual target. Owner infra-engineer. Blocking yes. The gate compares the record with HEAD, the CLI region, the STS account and the plan hash. It checks only an optional sidecar’s image_revision. It never binds the saved plan’s actual region, account, image revision or clean-source provenance to those inputs. Terraform uses the provider settings embedded in the plan. A matching checksum can therefore coexist with a different planned region, or a rollback can verify one image revision and apply a plan for another. The same mutable plan path is also reopened for apply after ECR operations. Acceptance — Verify the saved plan’s target and revision, require clean plan provenance tied to its checksum, and apply the verified bytes. Add fake tests for missing or mismatched provenance, different planned account, region and image revision, and a plan replaced between verification and apply. Deploy checks · Optional receipt · Apply · Terraform provider
P1 · F3 · Cleanup neither enforces preservation nor confirms the actual deletion set. Owner infra-engineer. Blocking yes. The script prints CLEANUP_PRESERVE and then builds a whole-root destroy plan. On a populated root, protected S3 and S3 Vectors resources can prevent that plan from succeeding. The script has no policy check to exclude grading log groups or the dependencies that keep retained evidence accessible. The confirmation token covers a redacted inventory gathered before planning. It omits account and plan identity, so a token can be reused for identical redacted listings across accounts, and the applied plan can include actions absent from the reviewed list. Acceptance — Produce a policy-compliant teardown plan, list its actual destructive actions, and bind confirmation to the exact saved plan, account, region and environment. Fake tests must reject a protected target, an unlisted delete, a changed plan and token reuse across accounts. Keep the existing Terraform protections and the carried two-pass IAM constraint. Preserve list · Inventory token · Destroy sequence · Bucket protection · Grading log resources
P1 · F4 · A supported plan filename can leave sensitive JSON eligible for commit. Owner infra-engineer. Blocking yes. --plan-out course.plan at the repo root passes the ignore check through *.plan. The script then writes raw terraform show -json output to course.plan.json, which that rule does not cover. The export can contain private variable values and planned resource data. Separately, the optional timeout trace writes raw argv, including the account embedded in Docker registry arguments, and the shared --log path persists subprocess output before redaction. Acceptance — Keep raw plan exports private and outside commit scope for every supported output path. Test .plan and an exact-name ignore rule, plus fake private values in subprocess diagnostics and account-bearing argv. Assert that stdout, stderr and retained logs contain no canaries. Plan output paths · Raw JSON capture · Ignore rules · Timeout trace · Persistent logs
P1 · F5 · Paid deployment can proceed without the required pre-spend check. Owner infra-engineer. Blocking yes. The execute path goes from approval and identity checks to registry push, Terraform apply and S3 upload without verifying active monitoring or available headroom. Application and infrastructure rollback inherit the same path. Section 7.3a applies to this deployment path. The separate G6 EMR run caps belong to 13B. Acceptance — Verify human-approved pre-spend evidence before any paid mutation. Use fakes to prove missing monitoring, stale or missing cost evidence, and insufficient headroom prevent push, apply and upload. Deploy mutation sequence · Plan §7.3a
P2 · F6 · The images pushed and the ECS revision reported are insufficiently verified. Owner infra-engineer. Blocking yes. Deploy validates manifest strings, then tags and pushes mutable local tags without matching them to the recorded image IDs or inspecting their architecture. After apply it accepts any nonempty ECS service response and records task-definition strings without checking that all four services reference the intended images. The happy-path fake returns only query-api and still expects PASS. Acceptance — Verify the identity and architecture of the images actually pushed. For a runtime deployment, verify all four deployed task definitions and expected image references before recording success. Exercise a replaced local tag, a missing service and a stale task definition with fakes. Manifest validation · Image push · ECS result · Single-service fake
P2 · F7 · Infrastructure rollback cannot replay the pre-13A checkout as documented. Owner infra-engineer. Blocking yes. The human is told to check out the previous commit and rerun scripts/rollback.sh there. The reviewed base has no such script. The test supplies its current fixture HEAD as the “previous” SHA and runs the script from the source checkout, so it misses the failure. The documented first-deployment flow also leaves the push-only step without a script invocation. The normal push path always proceeds to apply. Acceptance — Document and fake-test the complete flow with a previous tree lacking the release scripts and with separately approved base apply, image push and runtime apply. Keep the agreed ECR-existence refusal and two-stage rollback. Rollback instructions · Rollback fixture · First-deployment flow
P2 · F8 · Plan review hides resource actions behind the last-40-lines display. Owner infra-engineer. Blocking yes. The shared wrapper retains no plan log for this call and prints only its tail. The receipt supplies counts and IAM/stateful addresses, so it cannot recover the omitted changes. The course requires the plan output to remain reviewable before apply. Acceptance — Provide a complete review path for the exact saved plan with private values protected. A fake plan longer than 40 lines must preserve an early action and omit a synthetic private value from shareable output. Plan invocation · Output truncation · Course Phase 12 script requirements⁠�
P2 · F9 · The required clean-checkout gate lacks evidence, and a full PASS can omit script tests. Owners infra-engineer and orchestrator for evidence. Blocking yes. The real seven-gate log comes from the uncommitted tree. The clean-copy log ran five gates and predates the final partial exit behavior. Separately, SCRIPT_TEST_SUITES can replace the required list, and an existing empty files: suite passes without running a test. Acceptance — Make the default gate fail or report partial when a required suite is omitted or empty. Retain one final, real, seven-gate scripts/check.sh exit 0 from a clean snapshot of the repaired sources under JDK 17. Suite runner · Clean-copy log · Full-run tree snapshot
P2 · F10 · The R1 test copies local Terraform inputs into its fixture. Owner infra-engineer. Blocking yes. copytree excludes state, plan binaries and .terraform, but includes ignored private tfvars and raw plan JSON if present under the root. It then symlinks the live checkout’s entire .terraform directory into the fixture used by init. Acceptance — Construct the fixture from approved source inputs only and isolate Terraform working metadata. Test with synthetic ignored private files and verify they are excluded. Use a valid inside-network fixture and require a successful run before reporting that case as passing. Fixture setup · Inside-network assertion
Nonblocking observations and unverified gates
P3 · N1 · Replay details. Owner infra-engineer. Blocking no. Rollback’s printed delegated commands omit an explicitly supplied --profile. Terraform’s version probe bypasses the timeout helper, and that helper accepts non-finite limits. Acceptance — Assert profile propagation in the dry-run text, bound version probing, and reject nan and inf before spawning a child. Rollback command construction · Version probe · Timeout validation
P3 · N2 · Evidence retention. Owner orchestrator. Blocking no. The local JDK 27 refusal and six-test live probe match the reports. Both cited logs are ignored by *.log. Acceptance — Retain small commit-eligible excerpts with the commands and results. Test report · Ignore rule
Phase 14 access gate. Owners infra-engineer for policy and deploy-engineer for approved validation. The checked-in deployer permission sets have no ECR/ECS actions for the new path. Effective live permissions remain unverified. Confirm access through the human gate before execution. Terraform policy widening is outside the authorized 13A repair scope. Deployer attachments · Permission sets
Live Terraform planning, deploy, rollback, cleanup, registry login/push, Docker-unreachable fallback and the two-pass destroy remain unverified. The retained evidence shows local packaging and dry runs, with execute paths exercised against fakes. The 13B scripts, G6 caps, YARN kill and macOS tar work, and the 13C EMR port, TLS decision and carried hardening remain future scope. The owner report records the CI omission and Hadoop JAR timestamp limitation. Test report · Owner report
Review report
STATUS: COMPLETE
OWNER: code-reviewer
WORK ORDER: Independent read-only review of ScholarChain Phase 13, Subphase 13A.
FILES CREATED: None.
FILES MODIFIED: None.
COMMANDS RUN: git --no-optional-locks status --short --untracked-files=all; git branch --show-current; git rev-parse HEAD; git diff --no-ext-diff --no-textconv 8bee663040ba4e66b1edc1676d5346621c3f7384 --stat; git diff --no-ext-diff --no-textconv 8bee663 --check; targeted git diff, git ls-tree, git ls-files, git check-ignore, and read-only cat, sed, nl and rg inspections. Opened the linked course specification.
TEST RESULTS: Reviewer reruns prohibited by work order. Retained logs show full check exit 0 in 992 s with seven gates, 148 script tests OK, shellcheck exit 0, root Terraform 40 passed / 0 failed, and build verification 18 passed / 1 canceled in the full sbt run. The separate JDK 27 probe shows exit 1 for packageRelease and six tests passed with the live guard probe enabled.
VALIDATION RESULTS: Diff whitespace check exit 0. Path ownership matches the work order. The four cloud scripts default to dry run and fake-tool tests permit only the local Terraform version probe. The account hash uses the 12 digits without a trailing newline. Same-named environment variables do not replace the enumerated pins in the normal config. The timeout expiry path signals the process group. No raw account ID or credential pattern was found in the retained 13A evidence inspected. Execute-path and clean-checkout blockers are listed above.
ASSUMPTIONS: Reviewed the uncommitted handoff against the recorded base. Treated the approved Docker fallback, ECR-existence refusal, two-stage rollback and later-subphase deferrals as accepted scope.
RISKS: Unverified live gates and nonblocking observations are listed above. Retained logs support the reported local results and do not establish live AWS behavior.
MANUAL ACTION REQUIRED: Paste the next prompt into the main agent session. Keep Phase 14 execution behind the human gate.
BLOCKED-ON OWNER: infra-engineer for F1–F10 implementation and tests; orchestrator for F9 final clean-snapshot evidence.
BLOCKED-ON EVIDENCE: F1–F10, with source paths and acceptance checks above.
NEXT GATE: 13A repair, affected tests, full JDK 17 sbt check and clean-snapshot check.sh, then user-launched independent recheck.

### Review 2 (recheck of repair round 1) — user-supplied external review (pasted by the user on 2026-11-05; reproduced verbatim)

VERDICT: REQUEST-CHANGES — Subphase 13A, repair round 1
The clean-snapshot evidence closes F9. The remaining blockers concern which Terraform state rollback uses, which images deployment accepts, and how the scripts handle approval, teardown and private output. The review was read-only. I inspected the uncommitted changes on `phase-13` at `8bee663040ba4e66b1edc1676d5346621c3f7384` and ran no builds, tests, AWS commands or providers.
Blocking findings
All implementation and regression-test findings below route to `infra-engineer`.

1. P1 · R1 · F7 remains open — Infrastructure rollback plans against a fresh local state. Blocking yes. The course root uses local state. Rollback archives the old Terraform sources into a different, read-only root and sets `TF_DATA_DIR` there. That setting moves Terraform metadata. It does not point Terraform at the existing state file. The plan can propose creating resources already managed by the live stack, and apply has no binding to that stack’s state. The fake tests verify the archived source and command arguments, but do not model existing state. Acceptance: In a no-cloud regression, start with populated local state and an older commit that lacks the release scripts. Prove rollback plans against the existing state and refuses a missing or different state before apply. Keep the two-stage approval flow. [Rollback plan root (line 202)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/plan.sh:202) · [Rollback apply root (line 357)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:357) · [Repository state design (line 179)](/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/README.md:179) · [HashiCorp local backend reference](https://developer.hashicorp.com/terraform/language/backend/local)
2. P1 · R2 · F4 remains open — Derived plan outputs can escape the private directory. Blocking yes. `plan.sh` canonicalizes the binary path and an explicit receipt path, but checks the derived JSON, text, log and default receipt paths only with `git check-ignore`. For example, an ignored `target/plans/course.tfplan.json` symlink can point to a tracked file. The capture opens its destination with `O_TRUNC` and follows the symlink, so raw plan JSON can overwrite that tracked file. Cleanup’s containment check still passes the original filename to the writer, and its evidence directory can alias a plan output. Acceptance: Confine every output to a private directory at write time. Reject symlinks and colliding output paths. Fake tests should cover pre-existing links at the derived filenames and prove an outside canary file remains intact. [Plan output checks (line 164)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/plan.sh:164) · [Capture writer (line 63)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/lib/timeout.py:63) · [Cleanup output checks (line 181)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/cleanup.sh:181)
3. P1 · R3 · F2 remains open — The receipt can claim a clean source and environment the plan did not use. Blocking yes. The approved plan copy is now independently checked for region, account and revision. However, normal planning reads directly from the worktree, where Git-ignored `override.tf` files can alter Terraform configuration while `clean=true`. The receipt also copies `--env` into `env`, while the later private tfvars file can override the actual Terraform `environment`. Deploy validates the receipt’s label and never checks the plan’s environment. The approval hashes the binary, while the unsigned sidecar can be changed to claim clean provenance for those same bytes. Acceptance: Verify which source Terraform loaded, check the saved plan’s actual environment, and bind the reviewed provenance to the approval. Add regressions for an ignored Terraform override, a mismatched planned environment, and a receipt edited after review. [Git ignore rules (line 51)](/Users/danny/Documents/UIC/CS441/ScholarChain/.gitignore:51) · [Source and variable selection (line 194)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/plan.sh:194) · [Deploy receipt check (line 345)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:345) · [Saved-plan verifier (line 197)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/lib/verify.py:197)
4. P2 · R4 · F6 remains open — Runtime apply accepts a registry digest without linking it to the verified push. Blocking yes. The push stage verifies the local image ID and architecture and records the resulting registry digest. Normal runtime apply never consumes that record. It accepts any well-formed digest currently under the commit tag, then accepts the same tag string in the ECS task definition. A pre-existing tag pointing to different bytes can therefore pass without a successful verified push. The rollback branch already compares registry digests with a manifest. Acceptance: Bind normal runtime apply to the verified push record for the same commit, account, region and four repositories. Prove a missing record or changed digest refuses before apply. Retain the four-service ECS verification and rollback digest checks. [Push digest verification (line 623)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:623) · [Runtime digest checks (line 638)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:638) · [Runtime happy-path test (line 812)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_deploy.py:812)
5. P2 · R5 · F3 remains open — The documented teardown omits prerequisites for protected Neptune and load-balancer resources. Blocking yes. The repair lists the saved plan’s destructive actions, enforces the preservation allowlist and binds the token to the plan. But the script issues a delete-only plan and documents the preparatory `cleanup_mode=true` apply only for DynamoDB and ECR. The Terraform configuration also enables deletion protection on Neptune and the query load balancer. Those resources cannot be deleted while that protection is active, so the documented two-pass procedure can leave teardown resources in place. Acceptance: Document and gate the separately reviewed Terraform preparation for all applicable protected teardown resources. Test that an active protection blocks the destructive sequence until preparation is complete. Keep the preservation policy, saved-plan confirmation and carried two-pass IAM constraint. [Cleanup prerequisites (line 55)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/cleanup.sh:55) · [Neptune protection (line 26)](/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/modules/neptune/main.tf:26) · [Load-balancer protection (line 74)](/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/modules/runtime/compute.tf:74) · [AWS Neptune deletion rules](https://docs.aws.amazon.com/neptune/latest/userguide/api-clusters.html) · [AWS load-balancer deletion rules](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-delete.html)
6. P2 · R6 · F7 remains open — First-deployment ordering changed. Blocking yes. The recorded sequence is approved base apply, push, then runtime plan. The new push stage requires a plan with the current image revision, and the runbook explicitly requires the runtime plan before push. Acceptance: Demonstrate the recorded sequence end to end with fakes, including a separately approved push that refuses if ECR repositories are missing. If a different sequence is needed, obtain and record the human’s decision before changing the contract. [Recorded sequence (line 37)](/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-13/prompt.md:37) · [Push plan requirement (line 325)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:325) · [Revised runbook (line 162)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/README.md:162)
7. P2 · R7 · F5 remains open at the freshness boundary. Blocking yes. The new receipt checks correctly reject missing, stale and insufficient evidence at startup. The check runs once, before plan inspection, identity checks and a potentially long apply. A receipt just inside 24 hours can expire before the first paid command or before the later archive upload, and execution still proceeds. Acceptance: Use a controllable clock in fake tests. Demonstrate that a receipt expiring after initial verification prevents the next paid operation, including an upload after base apply. [Initial receipt validation (line 292)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:292) · [Apply and upload sequence (line 530)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:530) · [Recorded freshness rule (line 24)](/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-13/repairs.md:24)
8. P2 · R8 · Dry run now executes `terraform show`. Blocking yes. Deploy runs `show -json` without `--execute`, including when rollback delegates to it. The fake test explicitly expects this extra Terraform call. This regresses the requested print-only contract, which previously allowed the local version probe, and adds an initialized-checkout prerequisite to dry run. Acceptance: Dry runs print the `show` command and disclose that inspection is deferred. Assert no AWS, Docker or Terraform operation beyond the version probe. Keep independent inspection of the verified plan mandatory before any execute-path mutation. [Deploy inspection (line 357)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:357) · [Dry-run fake assertion (line 612)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_deploy.py:612)
9. P2 · R9 · G5 upload can publish bytes other than the bytes that passed the hash check. Blocking yes. The script hashes the original archive path before apply and reopens it afterward for upload. If a same-size file replaces it in between, the upload uses the replacement and sets `Metadata.sha256` to the expected hash itself. The subsequent check can report success because it reads that metadata and the size. Acceptance: Upload the same private copy whose bytes passed the pinned size and SHA-256 checks. Use a fake apply to replace the original archive and prove the replacement is never uploaded or recorded as verified. [Archive preflight (line 405)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:405) · [Upload and metadata check (line 530)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/deploy.sh:530)

Prior findings and remaining gates

* F1, F8, F9 and F10 meet their original acceptance checks. The Git check now uses one literal exemption and refuses status failures. The long-plan regression retains early actions and a complete private review file. The clean-snapshot run passed all seven gates, and the R1 fixture now excludes ignored inputs, isolates Terraform metadata and requires the valid inside-network case to succeed. R2 is a separate defect in the private output handling. [Repair mapping (line 46)](/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-13/repairs.md:46) · [Clean-snapshot result (line 117)](/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-13/evidence/13a/repair-1/check-full-clean-snapshot.txt:117)
* N1 and N2 are closed. Rollback propagates the profile, Terraform version probing is bounded, non-finite timeouts are rejected, and the two JDK probe excerpts are commit-eligible. P3 · N3 · Blocking no. The R1 test still invokes literal `terraform` and can skip its provider-backed cases when Terraform 1.13.5 is available only via `TERRAFORM_BIN`. Owner `infra-engineer`. Acceptance is to honor that override and show the R1 cases ran on an override-only installation. [R1 tool lookup (line 73)](/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_terraform_r1.py:73) · [JDK 27 refusal excerpt (line 30)](/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-13/evidence/13a/build/neg-probe-jdk27-packageRelease.txt:30)
* A2 remains a disclosed assumption for human decision. The runtime IAM roles, policies, instance profile, alarms and dashboard are in the teardown set. Their inclusion needs resolution before live cleanup. The retained logs show fake execution and local validation. Live plan/apply, targeted teardown and the two-pass result, ECR/ECS behavior, effective deployer permissions and the real Docker-unreachable fallback remain unverified. The 13B scripts and G6 caps, 13C EMR and IAM work, and recorded lean-scope omissions remain outside this repair. [A2 record (line 68)](/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-13/repairs.md:68) · [Unverified gates (line 78)](/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-13/test-report.md:78)

Review report

```
STATUS: COMPLETE
OWNER: code-reviewer
WORK ORDER: Independent read-only recheck of ScholarChain Phase 13, Subphase 13A repair round 1.
FILES CREATED: None.
FILES MODIFIED: None.
COMMANDS RUN: git --no-optional-locks status --short --untracked-files=all; git branch --show-current; git rev-parse HEAD; git diff --no-ext-diff --no-textconv 8bee663 --check; git diff --no-ext-diff --no-textconv 8bee663 --stat; path-scoped diffs against the full base SHA; git check-ignore for the retained JDK excerpts; targeted read-only cat, sed, nl and rg inspections. Read the linked course specification and official Terraform/AWS references.
TEST RESULTS: Retained evidence only. Clean snapshot 1076eef903053656fc8c71c6c23a27d0228b1261 shows scripts/check.sh exit 0 with seven gates and script suites 281/70/69/47/39 executed. Snapshot manifest records 5361 source comparisons and zero differences. Working-tree JDK 17 sbt -batch check exited 0 in 725 s with zero failures and one canceled optional probe. Shell evidence shows 18 files checked and zero findings. Six-gate check exited 5 PARTIAL.
VALIDATION RESULTS: HEAD equals the base. Five tracked files modified and 79 non-ignored untracked files. Tracked diff whitespace check exited 0. Paths match the ownership map and one-line Terraform exception. Normal same-named environment overrides of the enumerated pins are ignored. Account hashing and process-group timeout behavior match the decisions. A pattern scan of retained 13A evidence returned no raw account or credential-pattern matches. R1–R9 remain blocking.
ASSUMPTIONS: Treated the ECR refusal, exact record-path exemption, two-stage rollback, Terraform protections and two-pass destroy policy as binding. Treated A2 as pending human confirmation.
RISKS: The retained results establish local and fake-tool behavior. Live provider and Phase 14 access gates remain unverified.
MANUAL ACTION REQUIRED: Route R1–R9 for repair. Resolve A2 before live cleanup.
BLOCKED-ON OWNER: infra-engineer for R1–R9; orchestrator for retained evidence; human architect for A2 or any changed deployment-order decision.
BLOCKED-ON EVIDENCE: R1–R9 above, with source references and acceptance checks.
NEXT GATE: Repair round 2, affected tests, full JDK 17 sbt check, refreshed clean-snapshot evidence, and user-launched independent recheck.
```

### Review 3 (recheck of repair round 2) — user-supplied external review (pasted by the user on 2026-11-05; reproduced verbatim)

VERDICT: REQUEST-CHANGES — Subphase 13A, repair round 2
R1–R9 and N3 meet their review-2 acceptance checks. F1, F8, F9, F10, N1 and N2 are still closed, and the accepted designs did not regress. One new blocker remains: infrastructure rollback can’t be used once the runtime is live. It either fails at plan time or removes the runtime. This was a read-only review. HEAD is still `8bee663040ba4e66b1edc1676d5346621c3f7384`, and the work is uncommitted. I made no edits, ran no builds or tests, and made no AWS or provider calls.
Blocking finding
P2 · S1 · Infrastructure rollback can’t keep a running runtime (policy 13-5).

* Owner: `infra-engineer`. Blocking: yes.
* Where:
   * scripts/deploy.sh:419-422: `base-apply` forces `--no-image-revision`.
   * scripts/deploy.sh:279-281: `--source-commit` is accepted only with `base-apply`.
   * `scripts/rollback.sh:246,248`: the infra plan carries no `--image-revision` and is applied as `base-apply`.
   * scripts/lib/verify.py:248-250 and `:301-303`: a plan or receipt that carries an image revision is refused for this stage.
* Reasoning:
   * The only infra-rollback path is `plan.sh --source-commit SHA` followed by `deploy.sh --stage base-apply --source-commit SHA`. Both require `image_revision` to be null.
   * With a null revision, `infra/terraform/modules/runtime/compute.tf:2,75,88,173` creates no ECS services, query load balancer or listener.
   * After first deployment step 4, the private vars enable the runtime. The precondition at infra/terraform/phase12b.tf:25 (`!var.runtime_enabled || (... image_revision != null ...)`) then fails the plan.
   * So with the runtime live, the plan either fails or, if the human disables the runtime to get past the precondition, destroys all four services and the ALB.
   * `runtime-apply` can’t carry `--source-commit`. No path rolls infrastructure back to a previous commit while keeping a revision deployed.
   * The README rollback section (scripts/README.md:203-206) doesn’t disclose this. The infra-rollback tests use `image_revision=None` fixtures only (`scripts/tests/test_rollback.py:223,307`).
* Impact: after Phase 14 deploys the runtime, the rollback that 13-5 requires is unusable, or it removes the production runtime. A human could approve that teardown without realising it, because nothing calls it out.
* Acceptance check — either of:
   * (a) Infra rollback carries a deployed image revision. It is bound to a verified previous deploy manifest, or to a push record whose registry digests are checked before apply, the same way as `--reuse-images`. The receipt, approval and plan-target checks stay. Afterwards, all four ECS services are verified. Fake tests cover a populated state with the runtime enabled.
   * (b) A recorded human decision limits infra rollback to runtime-disabled states. Then any infra-rollback plan that deletes or replaces runtime-class resources, or fails the runtime precondition, is refused fail-closed with a clear `STEP` marker, and the limit is documented in `--help` and scripts/README.md. A fake test exercises that refusal.
   * Either way, keep the two-stage flow, the state binding, the ECR-existence refusal and the recorded first-deployment order.

Nonblocking observations
P3 · N4 · The R1 real-Terraform proof is skipped in the default gate from a clean checkout.

* Owner: `infra-engineer`; the evidence wording belongs to the orchestrator. Blocking: no.
* Where: scripts/tests/test_terraform_state_binding.py:53-55; scripts/check.sh:267-300; evidence/13a/repair-2/check-full-clean-snapshot.txt:54.
* Reasoning:
   * The state-binding test class skips without local providers, which a fresh checkout only gets from the later Terraform gate. The full scripts/check.sh still reports PASS.
   * The count is also slightly off. “Ran 427” is 434 minus the 7 tests that never ran. The class-level skip isn’t counted in “Ran”, so 427 tests did execute; “426 executed” undercounts by one. The accurate statement is that 427 executed and the 7 state-binding tests did not run.
   * The separate snapshot rerun (`state-binding-in-snapshot.txt`: 7 OK) does prove R1. The gate alone doesn’t.
* Acceptance check: the default gate runs these tests on a clean checkout, for example by initialising providers first, ordering the Terraform gate earlier, or failing on a skip of a required class. Reword the evidence counts.

P3 · N5 · The upload check compares metadata the script set itself.

* Owner: `infra-engineer`. Blocking: no.
* Where: scripts/deploy.sh:757-769.
* Reasoning: `head-object` compares the client-set `Metadata.sha256` and the size. Integrity of the bytes actually rests on `--checksum-algorithm SHA256`, which S3 validates at upload. R9’s acceptance check is still met.
* Acceptance check (optional): compare the object’s S3-computed `ChecksumSHA256`, or document why the upload-time check is enough.

Verified closed this round

* R1: a generated `backend "local"` binds the source to the live state. Lineage, serial and sha256 are checked before every apply. Real Terraform proves that rollback plans against the existing state without creating resources, and that a missing, different-lineage or changed state is refused (`test_terraform_state_binding.py:121-209`).
* R2: `safeio.py` requires every output to be absent beforehand, with no symlink in its path and no collision with another output. Files are created with O_CREAT|O_EXCL|O_NOFOLLOW. Cleanup evidence and plan outputs can’t alias each other (`cleanup.sh:273-288`).
* R3: planning always uses a `git archive` of the commit. `source_tree_sha256` is re-checked at deploy, the planned environment and project are checked, and `APPROVED_RECEIPT_SHA256` binds the receipt to the approval.
* R4: a push record is required, and registry digests must equal the pushed digests before apply (`deploy.sh:626-641,899-909`).
* R5: a `PREPARE-REQUIRED` refusal, plus a separately approved `cleanup-prepare` stage with a preparation-policy check.
* R6: the push stage takes no plan. The recorded order is proven end to end with fakes (`test_deploy.py:1533`).
* R7: the pre-spend receipt is re-checked before the ECR login, each push, each apply and the upload. The test clock is honoured only with the announced test config.
* R8: a dry run makes exactly one Terraform call (the version probe) and none to `aws` or `docker`. `init` and `show` are printed as deferred (`test_deploy.py:966-1006`).
* R9: the archive is uploaded from its private copy, which is re-hashed first (`test_deploy.py:1138`).
* N3: the R1 test honours `TERRAFORM_BIN`; 10/10 executed with no Terraform on PATH.

Other checks held: the exact approval-record path exemption, the ECR-existence refusal, the two-stage rollback, the Terraform protections, the two-pass destroy and the pinned config keys (no environment override). Ownership matches the map. No real account ID or secret appears in any new file or in the evidence; only fake IDs appear in tests, and the real ID in `scripts/billing` predates this phase.
Pending human decisions (not defects)

* A2.
* The approval-format additions: `APPROVED_RECEIPT_SHA256`, `APPROVED_ENVIRONMENT`, the `cleanup-prepare` stage, and `cleanup --confirm` taking `--plan`.
* The live-state location (infra/terraform/terraform.tfstate), and `--expect-new-state` for the first base apply.

Unverified gates and future scope

* Unverified: every live path. That covers AWS, real-state Terraform, ECR/ECS, the protection attribute names in a real `show -json`, effective deployer permissions (the Phase 14 access gate), the two-pass teardown and the Docker-unreachable fallback.
* 13B: `smoke-test.sh`, `run-bounded-pipeline.sh`, `run-experiment.sh`, `archive-evidence.sh`, the G6 caps, and carried items 1 and 31.
* 13C: the EMR module port to 12-10, the TLS decision, the IAM items and the test gaps.
* Lean scope: no CI (recorded).

Review report

```
STATUS: COMPLETE
```

`OWNER: code-reviewer`
`WORK ORDER: Independent read-only review of ScholarChain Phase 13, Subphase 13A repair round 2.`
`FILES CREATED: None.`
`FILES MODIFIED: None.`
`COMMANDS RUN: git status --short; git log --oneline -3; git diff 8bee663 --stat; git diff 8bee663 -- infra/terraform/tests/phase12b.tftest.hcl; git check-ignore -v (state, plan, release, evidence, prespend paths); read-only cat/sed/grep/wc of scripts/**, infra/terraform (runtime module, phase12b.tf, variables), docs/agent-runs/phase-13/** and the plan file; pattern scans for 12-digit IDs and credential patterns.`
`TEST RESULTS: Not rerun (prohibited). Retained evidence: clean snapshot c93c376 check.sh RESULT PASS gates=7 exit 0 (scripts/tests Ran 427 with one class-level skip: the 7 state-binding tests did not run; 70/69/47/39; sbt 40/667/18+1 canceled; terraform 7/19/29/38/6/40); state-binding rerun 7 OK; identity 5367/0; working-tree sbt -batch check on JDK 17.0.20.1 exit 0, 742 s, 0 failed; scripts/tests Ran 434 OK, 0 skipped; check.sh --only 6 gates exit 5 PARTIAL; N3 10/10; shellcheck exit 0 on 7 files.`
`VALIDATION RESULTS: R1–R9 and N3 meet their review-2 acceptance checks. F1, F8, F9, F10, N1 and N2 stay closed. Accepted designs did not regress. Dry runs make only the Terraform version probe. Ownership matches. No secret or real account ID appears in new files or evidence. New blocker: S1.`
`ASSUMPTIONS: A2, the approval-format additions and the live-state location are pending human decisions, not defects. Reviewed the uncommitted tree against 8bee663.`
`RISKS: S1 makes infrastructure rollback unusable, or destructive to the runtime, once the runtime is live. All live paths are unverified.`
`MANUAL ACTION REQUIRED: Route S1 to infra-engineer, or record a human decision for S1 option (b). Decide A2, the approval-format additions and the live-state location before Phase 14.`
`BLOCKED-ON OWNER: infra-engineer (S1; N4 and N5 optional); orchestrator (N4 evidence wording); human architect (S1 option (b) if chosen, A2, approval-format additions, live-state location).`
`BLOCKED-ON EVIDENCE: scripts/deploy.sh:279-281,419-422; scripts/rollback.sh:246,248; scripts/lib/verify.py:248-250,301-303; infra/terraform/phase12b.tf:25; infra/terraform/modules/runtime/compute.tf:2,75; scripts/README.md:203-206; scripts/tests/test_rollback.py:223,307.`
`NEXT GATE: Repair round 3 (S1), affected script tests, full JDK 17 sbt check, refreshed clean-snapshot check.sh, user-launched independent recheck.`

### Review 4 (recheck of repair round 3) — user-supplied external review (pasted by the user on 2026-11-05; reproduced verbatim)

VERDICT: REQUEST-CHANGES — Subphase 13A, repair round 3
N4 and N5 are closed. S1 is close but has one blocker. The runtime-live check counts the ECS cluster as a sign of a live runtime, but Terraform creates the cluster even when the runtime is disabled. After the first base apply, the runtime-disabled infrastructure rollback is therefore refused. A rollback that carries a push record would create the runtime instead of being refused, as the round-3 design intends. The fixtures miss this because they model “no runtime” as an empty state.
This was a read-only review. HEAD is still `8bee663040ba4e66b1edc1676d5346621c3f7384`, and the work is uncommitted. I made no edits, ran no builds or tests, and made no AWS or provider calls.
Blocking finding
P2 · T1 · The runtime-live check treats the base-apply ECS cluster as a running runtime.

* Owner: `infra-engineer`. Blocking: yes.
* Where:
   * scripts/config/release.conf:164-165: `RUNTIME_LIVE_PROTECTED_TYPES` includes `aws_ecs_cluster`.
   * scripts/lib/verify.py:576-610: `runtime_instances` counts any instance of those types.
   * scripts/rollback.sh (STEP `runtime-state`) and the `runtime-preservation` calls in scripts/deploy.sh use that count.
* Reasoning:
   * infra/terraform/modules/runtime/compute.tf:6 declares `aws_ecs_cluster.course` with no `count`. The `module "runtime"` block at infra/terraform/main.tf:97 has no `count` either.
   * So the first `base-apply` (runtime disabled, `image_revision = null`) already leaves `module.runtime.aws_ecs_cluster.course` in state.
   * Only `aws_ecs_service`, `aws_lb`, `aws_lb_target_group` and `aws_lb_listener` depend on `image_revision != null` (`compute.tf:2,75,88,101,114`).
   * Against a real post-base-apply state:
      * `rollback.sh --mode infra` without a binding is refused at `runtime-state` (“a plan without one would delete the runtime”), so the runtime-disabled rollback can’t be used in the base-apply → runtime-apply window.
      * With `--deployed-push-record` (the record exists after the push stage), the “binding but no live runtime” refusal is skipped. The carried plan then creates the four services and the ALB. `runtime-preservation` checks only deletes and replaces, so it passes.
   * The fixtures model “no runtime” as an empty state (scripts/tests/test_runtime_rollback.py:226, `set_live_state([])`), so the tests miss this. The owner report lists the state layout as an assumption “checked only against fixtures”. This defect follows from the Terraform source, not from unverified live behaviour.
* Impact: in the Phase 14 window after the base apply, the runtime-disabled infrastructure rollback can’t be used. A push-record-bound rollback would deploy a runtime that was never running, against the S1 contract recorded in `repairs.md`.
* Acceptance check:
   * Decide “runtime live” from resources that exist only when the runtime is deployed, such as `aws_ecs_service` instances, or `aws_lb` / `aws_lb_target_group` with `count`. Keep `aws_ecs_cluster` protected against delete or replace while the runtime is live.
   * Add fixtures that model a realistic post-base-apply state (the ECS cluster and ECR repositories, plus non-runtime modules, with no services). Tests must show three things:
      * the runtime-disabled infra rollback is accepted;
      * a manifest or push-record binding is refused with “would CREATE the runtime”;
      * a base-apply plan that keeps the cluster passes.
   * Keep every existing S1 refusal and test.

Nonblocking observation (disclosed, no action required)

* O1: nothing confirms that the revision named by `--deployed-push-record` is the one currently running. The binding is human input plus the digest, plan and post-apply checks. This is disclosed in the owner report. It could later be tightened with a read-only pre-apply `ecs describe-services` read during execute. Owner: `infra-engineer`.

Verified this round

* S1 (except T1):
   * Infra rollback takes `--deployed-manifest` or `--deployed-push-record`.
   * Registry digests are checked before any plan.
   * The plan is `plan.sh --source-commit PREV --image-revision REV`.
   * The apply is `deploy.sh --stage runtime-apply --source-commit PREV` with `--reuse-images`, or with `--image-revision` plus `--push-record`.
   * The manifest binding requires a runtime-apply manifest for this account, region and the four repositories.
   * `runtime-preservation` checks the receipt (in dry runs too) and the verified plan’s `show -json` with `--execute`.
   * The four services are verified after apply.
   * The two-stage flow, state binding, receipt/approval/plan-target checks and pre-spend re-checks are kept.
* N4: the Terraform gate now runs before script tests. `suite_run.py` reports executed counts and class skips, and a full default run fails when a required class is skipped. The clean-snapshot log shows `RealStateBindingTests executed=7` and `RouteOwnershipTest executed=6`, both with 0 skipped (`check-clean-snapshot-no-sbt.txt:89-91`).
* N5: `head-object --checksum-mode ENABLED` must return a `ChecksumSHA256` that matches the private copy. Multipart uploads are verified part by part through `get-object-attributes`, and the composite checksum is recomputed (`verify.py:709-771`).
* Evidence:
   * Clean snapshot `--skip sbt`: exit 5 PARTIAL with 6/6 gates passing; scripts/tests ran 529.
   * The working-tree unittest run shows OK.
   * Dry runs refuse a live runtime with no binding at `runtime-state`.
   * The sbt-input identity log shows 459 files compared and 0 differing. No sbt or test source references `scripts/`, so reusing the round-2 sbt result is consistent with the recorded scope decision.
   * No 12-digit IDs or secrets appear in the round-3 evidence or the new script files.
* No regression: F1–F10, N1–N3 and R1–R9 stay closed. The accepted designs are intact: the exact record-path exemption, the ECR-existence refusal, the two-stage rollback, the first-deployment order, the dry-run contract, the protections and two-pass destroy, the pinned keys (including the new `RUNTIME_LIVE_*`) and the preservation policy.

Pending, unverified and future scope

* Pending human decisions (not defects):
   * A2.
   * The approval-format additions, including a carried rollback using `APPROVED_STAGE=runtime-apply` with `APPROVED_COMMIT=PREV`.
   * The live-state location.
* Unverified:
   * Every live path: AWS, a real state’s `show -json` layout, ECR/ECS output, real S3 multipart checksums and `s3:GetObjectAttributes`, effective deployer permissions (the Phase 14 access gate), and the two-pass teardown.
   * The full seven-gate run and a fresh sbt run were deferred by user decision.
* Future scope:
   * 13B: the four remaining scripts, the G6 caps, and carried items 1 and 31.
   * 13C: the EMR port, the TLS decision, and the IAM items and test gaps.
   * Lean scope: no CI (recorded).

Review report

```
STATUS: COMPLETE
```

`OWNER: code-reviewer`
`WORK ORDER: Independent read-only recheck of ScholarChain Phase 13, Subphase 13A repair round 3.`
`FILES CREATED: None.`
`FILES MODIFIED: None.`
`COMMANDS RUN: git status --short; git log --oneline -2; read-only sed/grep/wc of scripts/{deploy,rollback,check}.sh, scripts/lib/verify.py, scripts/config/release.conf, scripts/tests/test_runtime_rollback.py, infra/terraform/main.tf and modules/runtime/compute.tf, docs/agent-runs/phase-13/{prompt,repairs,owner-report,test-report}.md and evidence/13a/repair-3/*; grep for scripts/ references in sbt sources; pattern scan for 12-digit IDs.`
`TEST RESULTS: Not rerun (prohibited). Retained: clean snapshot eea862df check.sh --skip sbt exit 5 PARTIAL passed=6 (terraform 7/19/29/38/6/40; scripts/tests Ran 529, 529 executed, required classes 7 and 6 executed, 0 skipped; 70/69/47/39); working-tree unittest Ran 529 OK; sbt-input identity 459/0; round-2 sbt evidence reused per user decision.`
`VALIDATION RESULTS: N4 and N5 meet their acceptance checks. S1 meets option (a) except T1 (runtime-live detection counts the base-apply ECS cluster). Prior findings stay closed; accepted designs not regressed; ownership scripts/** only; no secrets or raw account IDs in new files or evidence.`
`ASSUMPTIONS: The round-3 verification scope, A2, the approval-format additions and the live-state location are recorded or pending human decisions, not defects.`
`RISKS: T1 blocks the runtime-disabled infra rollback after the first base apply and lets a push-record-bound rollback create the runtime. All live paths are unverified.`
`MANUAL ACTION REQUIRED: Route T1 to infra-engineer. Resolve A2, the approval-format additions and the live-state location before Phase 14.`
`BLOCKED-ON OWNER: infra-engineer (T1); human architect (pending decisions).`
`BLOCKED-ON EVIDENCE: scripts/config/release.conf:164-165; scripts/lib/verify.py:576-610; infra/terraform/modules/runtime/compute.tf:6; infra/terraform/main.tf:97; scripts/tests/test_runtime_rollback.py:226.`
`NEXT GATE: Repair round 4 (T1), affected script tests, full JDK 17 sbt check and full seven-gate clean-snapshot check.sh, user-launched recheck.`

### Review 5 (repair round 4) — user-supplied external review — APPROVE (pasted by the user on 2026-11-05; reproduced verbatim)

VERDICT: APPROVE — Subphase 13A (repair round 4).
T1 fixed and meets review 4's acceptance check: runtime-live is decided only from RUNTIME_LIVE_INDICATOR_TYPES (aws_ecs_service=4, aws_lb=1, aws_lb_target_group=1, aws_lb_listener=0-1), matching the count/for_each gating in infra/terraform/modules/runtime/compute.tf and re-derived by SourceDerivedClassificationTests; aws_ecs_cluster stays in RUNTIME_LIVE_PROTECTED_TYPES and is refused for delete/replace while the runtime is live; a partial state fails closed; realistic post-base-apply fixtures (scripts/tests/helpers.py) prove (a) the runtime-disabled rollback is accepted, (b) a manifest or push-record binding is refused at runtime-state with "would CREATE the runtime", (c) a base-apply that keeps the cluster passes. test_runtime_rollback.py (51) unchanged; 529 + 31 = 560 tests. F1–F10, N1–N5, R1–R9 and S1 closed; no regressions in the accepted designs. Evidence matches the claims (check.sh PASS gates=7 exit 0; Ran 560, 0 skipped; SUITE-REQUIRED 7/6; sbt check exit 0 on JDK 17.0.20.1; 6 dry runs with 0 non-version calls). No secrets or raw account IDs.
Nonblocking: N6 (orchestrator) — the snapshot identity "compared=5372, differing=0" has no retained evidence file; retain it or mark it as orchestrator-stated. N7 (infra-engineer) — scripts/tests/helpers.py:110 docstring names "repositories.tf"; the ECR repositories are in modules/runtime/main.tf. O1 still disclosed (no live ECS read of the running revision).
Pending human decisions (not defects): A2; the approval-format additions (incl. a carried rollback with APPROVED_STAGE=runtime-apply and APPROVED_COMMIT=PREV); the live-state location.
Unverified (live): real state v4 layout and show -json, ECR/ECS output, S3 multipart ChecksumSHA256, deployer permissions, two-pass teardown.
Future scope: 13B (smoke-test.sh, run-bounded-pipeline.sh with the Spark EMR step, run-experiment.sh, archive-evidence.sh, G6 caps, items 1 and 31); 13C (EMR module port to 12-10, TLS decision, IAM items, test gaps).

The full review the user pasted also includes the findings table (N6 Low, N7 Trivial, O1 disclosed; none blocking) and the report fields. STATUS: COMPLETE; BLOCKED-ON OWNER: none; NEXT GATE: user commit of 13A, then Subphase 13B Step 0.

## Subphase 13B

### Review 1 — user-supplied external review — APPROVE (pasted by the user on 2026-11-06; reproduced verbatim)

VERDICT: APPROVE — Subphase 13B (base 52c2e21).
13B "Done when" is met: smoke-test.sh, run-bounded-pipeline.sh (with the Spark EMR step), run-experiment.sh and archive-evidence.sh exist, are strict-mode, dry-run by default, documented and tested with fake binaries; the dry run calls no binary (guard log empty); the pipeline submits steps to an existing Terraform-created cluster and never creates infrastructure. Decision 12-10 settings are enforced from scripts/config/spark-12-10.conf (refused if they depart); the driver and executor class-origin check runs as its own step and again inside the job body, and fails closed. G6: exact decimal estimate, USD 3 per run, 3 runs, USD 9.50 cumulative, a missing rate is never zero, unconfirmed pricing refuses --execute, rates are pinned. Item 1: YARN kill by run tag on timeout and on the EXIT/TERM traps (mutation-checked). Item 31: tarfile extraction plus COPYFILE_DISABLE=1, with before/after tests. Experiment: only a tracked, unchanged manifest with budget and teardown sections. Archive: 1 MiB threshold, redaction, no overwrite, no ._ members. No 13A regression; no secrets or real account IDs. Evidence matches the claims: check.sh PASS gates=7 exit 0 (scripts/tests 745, phase12d-spike 73, tests/scripts 198, 0 skipped; sbt 0 failed); snapshot identity 5409/0 retained; worktree sbt check exit 0 on JDK 17.
Nonblocking findings (owner infra-engineer unless noted):
B1 (medium): the stage-in and copy-out bodies (scripts/lib/pipeline.py:424, :590; step_json :629) and localize (:363) run aws/hadoop copies without an on-node timeout, while the dry run prints "the body runs under timeout" for every step (run-bounded-pipeline.sh:505). If the client dies, a hung copy keeps the cluster busy and auto-termination never fires. Acceptance: every step body runs under an on-node timeout; a fake-binary test kills a hanging copy; the printed text is accurate. Fix before the first Phase 15 --execute.
B2 (medium): the G6 ledger EMR_LEDGER_PATH=target/emr-ledger/runs.jsonl (release.conf:194) is deleted by sbt clean or a fresh clone, and an absent ledger reads as zero runs (budget.py:124). Acceptance: move it outside sbt-cleaned output (build-engineer for any new ignore rule), or fail closed on an absent ledger after the first live run; test and document it. Fix before Phase 15.
B3 (low; human decides): the estimate excludes the auto-termination idle tail (up to 3600 s), which is not disclosed; the worst case is USD 3.84 against the USD 3 per-run cap. Include it or disclose and accept it.
B4 (low; human decides): one approval record plus a 24 h receipt can start several paid runs up to the ledger caps (the run id is not in the run-config hash, and the ledger does not record the approval sha256). Make approvals single-use, or document and accept retries.
B5 (trivial): the stale PENDING_UNTIL_POPULATED exemption in scripts/check.sh:285.
Pending human decisions: EMR pricing confirmation; B3; B4; A2, the approval-format additions and the live-state location (from 13A).
Unverified (live, Phase 15): EMR steps, hadoop fs S3 access, HadoopPrepMain on EFS file://, YARN -appTags list/kill, cancel-steps SEND_INTERRUPT, G2/G3/G4, real probe JSON, real ECS/S3, deployed smoke.
Future scope: 13C (EMR module port to 12-10, TLS decision, IAM items 2/5/14/16/17, test gaps 6/7/10/12/20/21); the ER JAR packaging is BLOCKED-ON build-engineer.

The full review the user pasted also includes the findings table (B1 Medium, B2 Medium, B3 Low, B4 Low, B5 Trivial; none blocking) and the report fields. STATUS: COMPLETE; BLOCKED-ON OWNER: build-engineer (ER JAR packaging, already disclosed); NEXT GATE: user commit of 13B, then Subphase 13C Step 0.

## Subphase 13C

### Review 1 — user-supplied external review — REQUEST-CHANGES (pasted by the user on 2026-11-06; reproduced verbatim)

1. VERDICT: REQUEST-CHANGES — Subphase 13C (base 56144457f38e29b7c6211e040dd1fb15270a50bf, 13C uncommitted)
Most of 13C meets its acceptance criteria:

EMR module and decision 12-10: the main module matches decision 12-10.
TLS decision: in-transit TLS is off and disclosed. At-rest encryption stays on.
Spark settings: the module renders exactly the 22 keys in scripts/config/spark-12-10.conf, and a test fails if they drift.
Gaps G1–G3 and G5:
G1: EFS staging, with a TLS-only, access-point-scoped file-system policy.
G2: shuffle tracking.
G3: task nodes and managed scaling off by default; caps are checked against the G6 cost limits.
G5: the runtime archive comes from a tfvars S3 URI with its sha256 pinned.
IAM items:
Item 17: the stack tag is required on terminate, modify, ENI delete and DeleteTags.
Items 2, 5 and 14: closed, each with a negative test.
Item 16: honestly disclosed as a mitigation only.
Test gaps 6, 7, 10, 12, 20 and 21: closed.
Bootstrap items 8, 28 and 29: closed.
13B findings B2–B5: meet their acceptance checks.
Safety defaults: dry run is still the default and --init-ledger makes no cloud call. Tests used a temporary HOME; ~/.scholarchain does not exist on this machine.
Secrets and IDs: no real account ID or secret anywhere. The only 12-digit numbers are the synthetic 111122223333, 555555555555 and 000000000001.
Evidence: the claimed results match the retained logs:
RESULT: PASS gates=7, exit 0.
Script suites 831 / 73 / 69 / 47 / 39 / 256 / 126, all executed, none skipped.
Terraform tests 7 / 19 / 37 / 40 / 6 / 69.
sbt 40 / 667 / 18 (+1 canceled), 0 failed.
Snapshot identity 5430 / 0.
One defect blocks approval: the B1 change makes the Spark job step impossible to submit to EMR.

2. Findings
#	Severity	Path:line	Evidence and reasoning	Impact	Owner	Acceptance check	Blocking
C1	High	scripts/lib/pipeline.py:633-686 (wrap_body), :694 ("Args": ["bash","-c",body]), :840	Each string in an EMR step’s Args may be at most 10,280 characters (AWS API reference, HadoopJarStepConfig.Args). The retained 13B dry run (evidence/13b/infra/pipeline-dry-run-full.txt:442) has a spark-job body of 10,279 characters, using short fixture values. 13C’s wrap_body puts the whole body inside a 37-line wrapper of about 1.6 KB. That makes the spark-job argument about 11.8 KB, over the limit; class-origin is about 10.2 KB, right at it. Real bucket and prefix names make both longer. No test bounds the length, and 13C keeps no full dry run of the wrapped bodies.	In Phase 15 --execute, the steps are submitted one at a time. The ledger slot and the single-use approval are used up first. Stage-in, Hadoop prep and ER then run and bill. Only then does add-steps for spark-job fail with a ValidationException, so one of the three funded runs is lost.	infra-engineer (scripts/**); test-engineer for an independent test in tests/scripts	(a) The plan builder refuses, before any cloud call and also in the dry run, any step argument longer than 10,280 characters. (b) Every step is brought under the limit, for example by installing the wrapper and the large Python snippets as sha-pinned files through the bootstrap’s --artifact into /opt/scholarchain-spike/bin, or by passing a sha-verified body file. (c) Fake-binary tests use maximum-length realistic values (63-character bucket names, long prefixes, a 64-character run id). (d) A 13C dry run is retained that prints each step’s argument length.	Yes
C2	Low	infra/terraform/modules/emr/variables.tf:20, phase12b-variables.tf (runtime_archive_sha256)	The decision 12-10 runtime hash is only a default. Validation checks that a tfvars value is 64-character hex, not that it equals the pinned hash, and the test checks only the default.	A tfvars override would install a different runtime. The class-origin check fails closed later, but only at run time, after spend.	infra-engineer	A validation requiring equality with the pinned hash (or with RUNTIME_ARCHIVE_EXPECTED_SHA256 from release.conf), plus a negative test.	No
C3	Trivial	scripts/config/release.conf:193	The comment still says the ledger is “git-ignored … Written only below target/”, but the path is now ~/.scholarchain/emr-ledger/runs.jsonl.	Misleading documentation.	infra-engineer	Correct the comment.	No
C4	Low	docs/agent-runs/phase-13/evidence/13c/infra/{pipeline-run1.txt (330 KB), tests-scripts-run.txt (363 KB), pipeline-run2.txt (139 KB), test_experiment-run3.txt (130 KB)}	These are full intermediate failing-test logs with local temporary paths, about 1 MB in total. Plan §6.11 says evidence stays lean.	Repository bloat. Nothing secret was found.	orchestrator	Replace them with failure excerpts and summary lines, keeping the commands and exit codes.	No
Pending human decisions:

Confirm EMR pricing (EMR_PRICING_CONFIRMED_BY_HUMAN stays false).
Initialise the ledger before Phase 15.
The deferred 13A items: decision A2, the approval-format additions, and where live state lives.
Refresh the stale pins in scripts/billing/reviewed-pins.json (stale at base).
The ER JAR packaging (BLOCKED-ON build-engineer).
Not verified live (Phase 14/15):

The bootstrap on real nodes: runtime install, Java resolution, the EFS tls,iam mount, amazon-efs-utils and S3 egress.
The item 17 stack tag on ENIs that EMR creates.
The process-group kill and the cancel-steps signal on a node.
Effective deployer permissions.
G2, G3 and G4.
Future scope:

Item 25, an optional tightening.
The main stack’s EMR service policy is user-supplied, follows AmazonEMRServicePolicy_v2’s tag conditions and has no stack-tag condition. Review it at the Phase 14 pre-flight.
3. Report fields
STATUS: COMPLETE (review); verdict REQUEST-CHANGES
OWNER: code-reviewer
WORK ORDER: Phase 13 Subphase 13C independent review (user-supplied prompt, 2026-11-06)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only git diff/status/log, grep/awk/sed over sources and retained evidence; AWS documentation read (HadoopJarStepConfig, BootstrapActionConfig); no build, test, AWS account or provider call
TEST RESULTS: not run (read-only); retained logs match the claims (check.sh PASS gates=7 exit 0; suites 831/73/69/47/39/256/126; terraform 7/19/37/40/6/69; sbt 0 failed; worktree sbt exit 0, 764 s)
VALIDATION RESULTS: C1 blocking (EMR step Args length); C2–C4 nonblocking
ASSUMPTIONS: the wrapper's static size (~1.5–1.7 KB) was measured from source, not by running the code; the 13B body length was measured from retained dry-run evidence
RISKS: one funded Phase 15 run is lost if C1 is not fixed; live-unverified items as listed
MANUAL ACTION REQUIRED: pricing confirmation, ledger init, A2/approval-format/live-state decisions, reviewed-pins refresh, ER JAR packaging decision
BLOCKED-ON OWNER: infra-engineer (C1); build-engineer (ER JAR, pre-existing)
BLOCKED-ON EVIDENCE: evidence/13b/infra/pipeline-dry-run-full.txt:442 (spark-job body 10,279 chars); scripts/lib/pipeline.py:633-694
NEXT GATE: C1 repair, then a recheck review of 13C repair round 1

### Review 2 — repair round 1 recheck — APPROVE (user-supplied external review, pasted by the user on 2026-11-06; reproduced verbatim)

1. VERDICT: APPROVE — Subphase 13C repair round 1
Base and HEAD are 56144457f38e29b7c6211e040dd1fb15270a50bf, with the work uncommitted. All four prior findings (C1–C4) are fixed, and the claimed results match the retained logs. One small nonblocking issue remains, listed as R1 below.

C1 — the EMR step argument limit is fixed:

New step form: each step’s Args are now bash -c <293-char launcher> sc-step <sha> <STEP> KEY=VALUE… (scripts/lib/pipeline.py:267-342).
Launcher: it checks the installed sc-step.sh against a sha256 computed from the repository file and refuses to run if the file is missing or different. It then execs the runner, with $0/$1 handled correctly.
Length check:
check_arg_lengths (pipeline.py:361) runs inside the plan builder, before the g6-gate step, the ledger and the approval (run-bounded-pipeline.sh:362-383).
The limit is pinned at 10,280 and can only be lowered within 1000..10280 (pipeline.py:476).
At maximum realistic values, the longest argument in the retained dry run is 1,043 characters (evidence/13c/infra/repair1-dry-run-arg-lengths.txt:27-33).
B1 is preserved: the whole body still runs under timeout --kill-after in its own process group, with TERM, then KILL after the grace period, and a STEP-WARN message (scripts/emr/sc-step.sh:117-150).
Item 1 is preserved: YARN applications are still killed by tag on EXIT/TERM and when the cap fires.
Class-origin is preserved: the check still fails closed in both steps, and the job is gated before spark-submit. The verifier is line-for-line the base 13B snippet.
The 22 decision 12-10 settings are preserved: they still come from spark-12-10.conf, and the forbidden-key check is still at pipeline.py:195. The order of the --conf flags is unchanged.
Parameters are safe:
Each step accepts only its allow-listed keys; an unknown, duplicated or missing key is refused.
Inherited environment variables are unset first, so they cannot stand in for a missing parameter.
Values are never evaluated.
Each Python program is checked against its own sha256 before it runs.
Pinned in Terraform: phase12b.tf:34 requires each of the four programs exactly once in extra_artifacts, at bin_dir/name with the sha from emr-step-programs.json. Tests cover a wrong sha, a wrong destination, a missing program and a duplicate.
Drift is refused offline: pipeline.py refuses a plan when the programs and the manifest disagree (STEP-PROGRAM-DRIFT, pipeline.py:147).
Tests:
scripts/tests/test_c1_step_args.py (25 tests) and the independent tests/scripts/test_step_arg_limit_13c.py (20 tests).
They cover the 10,280 / 10,281 boundary, --execute leaving the ledger and approval untouched, tampered or missing programs, and the allow-list.
The mutation evidence shows the boundary tests catch a disabled check, and the source was restored byte-identically.
Test rewrites are sound: the dry-run assertions moved from body text to Args parameters plus the pinned runner text. The behaviour itself is still exercised in test_pipeline_bodies.py:501-560 and test_13c_pipeline.py:113-212.
C2 is fixed: runtime_archive_sha256 must equal the 12-10 pin in both the root config and the module config (phase12b-variables.tf:142, modules/emr/variables.tf:93).

C3 is fixed: the ledger comment is corrected (release.conf:192-195).

C4 is fixed: no evidence file under evidence/13c/infra/ is larger than 100 KB.

Other checks:

Ownership: each path has one writer. infra-engineer wrote scripts/** and infra/terraform/**; test-engineer wrote only tests/**.
No account ID or secret: the only 12-digit numbers are synthetic.
No live cloud command ran: tests ran with credentials and profiles unset, and AWS_EC2_METADATA_DISABLED=true.
Evidence matches the claims:
Terraform tests 7 / 19 / 37 / 40 / 6 / 77.
Test suites 856 / 276 / 128 / 73, plus 69 / 47 / 39 OK.
Snapshot identity 5437 / 0.
sbt inputs identical: 335 / 0 paths unchanged.
2. Findings
#	Severity	Path:line	Evidence	Impact	Owner	Acceptance check	Blocking
R1	Low	docs/agent-runs/phase-13/evidence/13c/infra/repair1-tests-scripts-run.txt:1-8, …/repair1-tests-scripts-with-manifest-copied.txt	These are failing tests/scripts runs from before test-engineer adapted the fixtures (ERROR/FAIL lines). The first file has no label saying it is an intermediate run. Neither file is mentioned in owner-report.md or test-report.md.	A reader could mistake them for current results.	orchestrator	Add a one-line “intermediate, superseded by test/repair1-scripts-suite-run.txt” header to both files, or mention them in the repair-round report.	No
Not verified live (Phase 14/15):

The bootstrap actually installing the four programs on a node.
command-runner.jar running bash -c with the launcher.
The process-group kill and the EMR cancel signal on a node.
The EFS mount.
The item 17 stack tag on ENIs that EMR creates.
G2–G4.
The 10,280 limit itself, which is taken from the AWS documentation and not observed live.
Accepted and disclosed: between the launcher’s sha check and the exec there is a short window, on root-owned mode-755 files.

Future scope (Phase 14):

The human adds the four programs to emr_config.extra_artifacts in *.local.tfvars. The Terraform guard refuses a plan without them.
Review the EMR service policy at the pre-flight.
Pending human decisions:

Pricing confirmation.
Ledger init before Phase 15.
Decision A2, the approval-format additions and where live state lives.
The reviewed-pins refresh.
The ER JAR packaging (BLOCKED-ON build-engineer).
Not yet run: the seven-gate scripts/check.sh as one command, and a fresh sbt check. Your recorded preference is one full check after approval. Section 11 requires a fresh sbt check on JDK 17.

3. Report fields
STATUS: COMPLETE (review); verdict APPROVE
OWNER: code-reviewer
WORK ORDER: Phase 13 Subphase 13C repair round 1 independent review (user-supplied prompt, 2026-11-06)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only git rev-parse/status/diff/show, grep/sed/awk/cat/wc/ls over sources, plan and retained evidence; no build, test, AWS or provider call
TEST RESULTS: not run (read-only); retained logs match the claims: terraform 7/19/37/40/6/77; scripts/tests 856, tests/scripts 276, tests/infra 128, spike 73 (all executed, 0 skipped/failed/errored); billing 69/47/39 OK; check.sh --skip sbt,script-tests exit 5 PARTIAL passed=5 (by design); snapshot 5437/0; sbt inputs 335/0 against the 13C snapshot whose sbt gate passed
VALIDATION RESULTS: C1–C4 fixed; R1 nonblocking
ASSUMPTIONS: the 10,280-character limit comes from the AWS API reference; behaviour on real EMR is unverified
RISKS: node-side behaviour of the launcher, runner and bootstrap install is unproven until Phase 14/15; any later edit under scripts/emr/sc-* needs `pipeline.py step-manifest --write` and new tfvars hashes
MANUAL ACTION REQUIRED: one full check.sh plus a fresh sbt check on JDK 17; human-gate.md and commit.txt (human only); pricing confirmation; ledger init; A2, approval-format and live-state decisions; reviewed-pins refresh; extra_artifacts in *.local.tfvars at Phase 14
BLOCKED-ON OWNER: build-engineer (ER JAR packaging, pre-existing)
BLOCKED-ON EVIDENCE: none new
NEXT GATE: full verification, then the Phase 13 human gate (13C is the last subphase)

# Phase 14 owner reports

## Subphase 14A — pre-flight, dry run and the approval request

Assembled by the coordinator from the agents' final reports. The agents' own counts are listed only where the coordinator did not re-run them; the coordinator's observed results are in [test-report.md](test-report.md).

### Agents launched

| Agent | Native ID (Claude Code) | Model / effort | Paths | Rounds |
|---|---|---|---|---|
| `infra-engineer` | `a195f9a04f32d5b27` | Sonnet 5.5 (`sonnet`), high | `infra/terraform/**`, `scripts/phase12d-spike/tests/test_terraform_static.py` (round 3); scratch `target/phase14/evidence/14a-infra/` | 1: 14-6, 14-3, Task 3, Q13. 2: D1, D2, D4 note, D5, Haiku example. 3: D6 gate repair |
| `test-engineer` | `a75fa96b59087cf23` | Sonnet 5.5 (`sonnet`), high | `tests/infra/**`; scratch `target/phase14/evidence/14a-test/` | 1: D3 |

No reviewer was launched. `deploy-engineer` was not used (Q14). No agent made an AWS call, a real plan or an apply, read a private tfvars, state or `.env` file, or committed.

### infra-engineer

```text
STATUS: COMPLETE (round 2); round 1 returned two BLOCKED-ON items, decided by the user as D1-D3
OWNER: infra-engineer
WORK ORDER: docs/agent-runs/phase-14/prompt.md, 14A (14-6, 14-3, Task 3, Q13; then D1, D2, D4, D5 and the Haiku 4.5 example)
FILES CREATED:
  infra/terraform/deployer/phase14_main.tf
  infra/terraform/deployer/boundaries/runtime.json.tftpl
  infra/terraform/deployer/boundaries/emr-service.json.tftpl
  infra/terraform/deployer/tests/default_set.tftest.hcl
  infra/terraform/tests/phase14a.tftest.hcl
  infra/terraform/environments/course.local.tfvars.example
  infra/terraform/environments/emr-service-policy.json.example
FILES MODIFIED:
  infra/terraform/README.md
  infra/terraform/deployer/{README.md,main.tf,outputs.tf,permission_sets.tf,variables.tf,tests/deployer.tftest.hcl}
  infra/terraform/main.tf
  infra/terraform/phase12b-variables.tf
  infra/terraform/modules/identity/{main.tf,outputs.tf,phase12b.tf,variables.tf}
  infra/terraform/modules/network/{main.tf,outputs.tf}
  infra/terraform/modules/workflow/{main.tf,outputs.tf}
COMMANDS RUN (agent-reported; offline, AWS environment neutralized):
  terraform fmt -check -recursive infra/terraform (0)
  deployer and root: init -backend=false -lockfile=readonly, validate, test (deployer 61/0, root 106/0)
  scripts/check.sh --only terraform (PARTIAL by design, exit 5; terraform gate PASS)
  git diff --check (0)
  python3 -I scripts/lib/pipeline.py step-manifest (0)
  terraform console over the mock config (action list and expected deployer addresses)
TEST RESULTS: re-run by the coordinator; see test-report.md.
VALIDATION RESULTS:
  phase14-main: 7 documents (characters: network 3824, network-mod 2540, data 5164, keys-obs 4999, compute 5696,
    emr-efs 5113, iam 5637); 7 managed attachments + 1 inline login policy; 384 Allow actions, 10 Deny actions.
  Boundaries (created by the deployer root): scholarchain-course-permissions-boundary 3372 characters,
    scholarchain-course-emr-service-boundary 4607 characters.
  D1 role-to-boundary mapping:
    EMR service boundary: the -emr-service role only.
    Runtime boundary: every other main role (4 task, 4 execution, -neptune-loader, -emr-ec2, -deployment,
    -embedding-producer).
    The ARN is built from aws_account_id plus the fixed name; no remote state, no new tfvars entry.
  Mutations (agent-reported): deployer 34, of which 33 caught by the deployer suite; M32 is caught by the root
    boundary-coverage test. Root 37 of 37 caught.
    Evidence: evidence/14a/infra/mutation-results-*.txt.
  Resource enumeration: 62 aws_* types (evidence/14a/infra/resource-types.txt).
  Full action list per document: evidence/14a/phase14-main-actions.txt.
ASSUMPTIONS:
  IAM action names, refresh calls and condition keys come from AWS documentation and provider behavior; none were
    observed live.
  Tag scoping assumes the provider default_tags reach every taggable resource.
  The boundaries are action-level ceilings; resource-level agreement is not tested.
RISKS:
  Disclosure (14-6): a missed action shows up as AccessDenied during base-apply. It is fixed by a routed
    infra-engineer repair, a new reviewed deployer apply and a new plan. Plausible gaps the agent named:
    - s3 reads of aws_s3_bucket in provider 6.44.0;
    - the Cloud Map / Route 53 private-zone calls;
    - kms:ViaService for S3 Vectors;
    - RetireGrant conditions;
    - ECS TagResource on task definitions;
    - KMS tag authorization right after CreateKey.
  Honest-list broad statements (D4, accepted as disclosed):
    - ec2:RevokeSecurityGroupIngress/Egress on any security group in the region, because aws_default_security_group
      adopts the untagged default group;
    - Route 53 unscoped.
    ec2:Vpc note: the key exists for EC2 security-group actions, but the VPC ARN is unknown when the deployer root is
    applied, and the default group is the one being adopted, so it cannot narrow these statements now. The agent did
    not open the Revoke rows of the Service Authorization Reference; reviewer spot-check needed.
  Destructive actions (delete on stack types, kms:ScheduleKeyDeletion on project keys) are granted on purpose;
    the script cleanup policy, not IAM, preserves keys and buckets.
  Not granted: the 14C data-plane loads, Phase 15 AddJobFlowSteps/CancelSteps, iam:AttachRolePolicy, budgets.
MANUAL ACTION REQUIRED: the human back-ups and deployer apply (evidence/14a/deployer-apply-proposal.md);
  confirm the Haiku routing with aws bedrock get-inference-profile (read-only).
BLOCKED-ON OWNER: none after round 2.
BLOCKED-ON EVIDENCE: all live AWS authorization; the real deployer state's addresses.
NEXT GATE: coordinator gates, independent review, human deployer apply.
```

Further findings from the infra-engineer:
- **Bedrock (14-3):**
  - Synthesis uses the Converse API, which needs only `bedrock:InvokeModel`; streaming is not granted.
  - Titan Text Embeddings V2 supports on-demand in us-east-2 with no profile.
  - Claude Haiku 4.5 has no in-region ID, so the `us.` profile is required; it routes to us-east-1, us-east-2 and us-west-2. Source: the AWS model card `model-card-anthropic-claude-haiku-4-5.html`, read 2026-11-06.
  - With a profile, the grant is the profile ARN in us-east-2 plus one foundation-model ARN per routed region, conditioned on `bedrock:InferenceProfileArn`. A `global.` profile adds a region-less ARN. Without a profile, behavior is unchanged.
  - The application must pass the profile ID as `modelId`. That is service configuration, not Terraform.
- **EMR in Phase 14 (Task 3):** disabled in both Phase 14 plans; the first EMR-created ENIs appear at the Phase 15 apply. The `extra_artifacts` guard applies only when `emr_config.enabled` is true.
- **Q13:** the main stack attaches the EMR service policy as inline JSON (`emr_service_policy_json`). Its validator rejects the published managed v2 policy, so `environments/emr-service-policy.json.example` mirrors v2, scoped to us-east-2 and the account. Accepted by the user; it is used from Phase 15.
- **D2 defect, fixed:** the EMR v2 network tag was on `emr_service_access` only. It is now also on the application subnets and `security_group.role["emr"]`.

#### infra-engineer round 3 (D6 gate repair)

```text
STATUS: DONE
TRIGGER:
  The coordinator's first full check.sh (clean snapshot e690b50) failed script-tests (EXIT 4).
  Failing test: scripts/phase12d-spike/tests test_terraform_static
    DefaultSecurityGroupTests.test_every_ec2_create_tags_has_a_create_action_condition.
  Cause: phase14_main.tf Ec2AdoptedDefaultSgFirstTags, the disclosed honest-list row "ec2:CreateTags (first tags of that
    group)", has no ec2:CreateAction condition.
  Neither agent had run that suite in rounds 1-2.
DECISION: D6 (user), a named exception; the statement itself is unchanged.
FILES MODIFIED: scripts/phase12d-spike/tests/test_terraform_static.py (+154/-3); nothing else.
CHANGE:
  The fixed 700-character window is replaced by statement parsing on balanced {...} blocks.
  Every ec2:CreateTags-only statement other than the D6 Sid must still carry ec2:CreateAction.
  The D6 Sid is validated strictly: it exists exactly once; Effect is Allow; Action is exactly [ec2:CreateTags];
    Resource is exactly [${local.arn_ec2}:security-group/*]; c_req_main and the aws:TagKeys = var.main_tag_keys
    conditions are present.
  New class CreateTagsExemptionCannotWidenTests: 9 in-memory mutation tests (a second statement, a wildcard Resource,
    an extra ARN, no TagKeys, no request tags, an extra action, a neighbour losing CreateAction, a duplicate, and the
    unmutated text).
COMMANDS RUN (agent-reported):
  suite_run.py on scripts/phase12d-spike/tests: 82 run, OK (exit 0)
  check.sh --only python: PARTIAL by design (exit 5); the python gate passed
  git diff --check (0)
RISKS: text-level check. Two-action statements such as Ec2RetagProjectResources (CreateTags plus DeleteTags,
  resource-tag conditioned) are outside this rule, as before.
```

### test-engineer

```text
STATUS: COMPLETE
OWNER: test-engineer
WORK ORDER: docs/agent-runs/phase-14/prompt.md, D3 (pin the spike-era suites, phase14-main checks, guard allowlist,
  template scan coverage)
FILES CREATED:
  tests/infra/phase14_checks.py
  tests/infra/test_phase14_main.py (75 tests)
  tests/infra/test_guard_phase14.py (20 tests)
FILES MODIFIED:
  tests/infra/infra_support.py
  tests/infra/tftests/deployer_snapshot.tftest.hcl
  tests/infra/terraform_source_guard.py
  tests/infra/README.md
COMMANDS RUN (agent-reported):
  python3 -I -m unittest discover -s tests/infra (223 run, OK)
  python3 -I tests/infra/terraform_source_guard.py --repo-root . (93 files, 0 findings)
  python3 -I tests/infra/terraform_source_guard.py --self-test (16 OK)
  git diff --check (0)
TEST RESULTS: re-run by the coordinator; see test-report.md.
VALIDATION RESULTS:
  Spike-era suites pinned to spike-emr; no assertion weakened.
  Infra mutations 52 of 52 caught; guard mutations 11 of 11 caught. Evidence: evidence/14a/test/.
  Guard allowlist: 7 GlobalGrant entries, each matching file + exact action set + Resource "*". Six require a
    non-empty Condition (Route 53 is exempt from that requirement). Stale entries are reported.
  The guard now scans *.json.tftpl under infra/terraform and environments/*.json.example. ${...} and %{...}
    interpolations are blanked. 0 findings on the real templates.
ASSUMPTIONS: the SAR URL slugs and justifications follow the infra owner's README; they were not fetched.
RISKS:
  Some checks are stricter than the literal requirement (PutRolePolicy conditioned on both boundaries; exempt
    services exactly {iam, route53}; no NotAction).
  Ceiling observations, not defects:
    - the runtime boundary allows secretsmanager:GetSecretValue on secret:* in the region and account (the
      deployer itself denies it);
    - the EMR boundary allows kms:CreateGrant without kms:GrantIsForAWSResource (the EMR role policy has it).
MANUAL ACTION REQUIRED: reviewer spot-check of the cited SAR pages.
BLOCKED-ON OWNER: none.
BLOCKED-ON EVIDENCE: none.
NEXT GATE: coordinator re-runs everything; independent review.
```

### Coordinator

```text
STATUS: COMPLETE pending the coordinator gate (test-report.md) and the independent review
OWNER: coordinator (Claude Code main session)
WORK ORDER: plan Section 8, Subphase 14A, tasks 1, 4 and 5; decisions in prompt.md
FILES CREATED:
  docs/agent-runs/phase-14/prompt.md
  docs/agent-runs/phase-14/owner-report.md
  docs/agent-runs/phase-14/test-report.md
  docs/agent-runs/phase-14/approval-request-14a.md
  docs/agent-runs/phase-14/evidence/14a/** (carried-findings-status.md, deployer-apply-proposal.md,
    phase14-main-actions.txt, pin-drift.txt, dryrun/, infra/, test/, gates/)
FILES MODIFIED: none outside docs/agent-runs/phase-14/
COMMANDS RUN: see test-report.md (dry runs, gates, snapshot identity, pin drift)
ASSUMPTIONS:
  The cost model reuses the Phase 12C Ohio rates (fetched 2026-10-30) and assumes minimum capacity for all
    239 h (Nov 15 00:00 to Nov 24 23:00 CST).
  The last recorded spend is USD 0.34 (Phase 12 gate).
RISKS:
  Billing data lags; the user supplies cost-to-date before 14B.
  Refreshing scripts/billing/reviewed-pins.json changes a scripts/billing file. That file's hash is bound in the
    billing execution gate (wrapper_files), so any later billing verify/readback needs a new billing gate.
MANUAL ACTION REQUIRED: see the approval request and the handoff.
BLOCKED-ON OWNER: none.
BLOCKED-ON EVIDENCE: no live check of quotas, model access, budgets, secrets or Cost Explorer (human items).
NEXT GATE: user-launched independent review of 14A.
```

### Lean-scope omissions (14A)

- No OpenSearch, CI workflow, interface endpoint or extra index.
- The deployer set does not grant the 14C data-plane loads or the Phase 15 step actions; they are added by a routed repair when needed.
- Secrets are created by the human in Secrets Manager outside Terraform, on purpose, so their values never enter state; Terraform receives only the ARNs (14-4).

## Subphase 14A — repair round 1 (review 1, REQUEST-CHANGES)

The coordinator assembled this section from the agents' final reports. Every count below was reported by the agent. The coordinator's own re-runs are in [test-report.md](test-report.md), "Repair round 1".

The user ordered: "fix all blocking bugs for me". The coordinator recorded that as F1 option (1) and F2 narrowing; see `prompt.md` and `repairs.md`.

### Agents launched

| Agent | Native ID (Claude Code) | Model / effort | Paths | Task |
|---|---|---|---|---|
| `service-engineer` | `a33aeae8caae698c6` | Sonnet 5.5, high | `modules/services/**` | F1: aws mode (2 rounds) |
| `storage-engineer` | `a974d2a6ba389c0e8` | Sonnet 5.5, high | `modules/storage/**` | F1: Neptune reader `connect` and directed edges |
| `infra-engineer` | `a195f9a04f32d5b27` | Sonnet 5.5, high | `infra/terraform/**`, `scripts/phase12d-spike/tests/test_terraform_static.py` | F2 narrowing and F5 (round 4); F1 task environment and grants (round 5) |
| `test-engineer` | `a75fa96b59087cf23` | Sonnet 5.5, high | `tests/infra/**` | 5 stale tests after F2, plus independent F2 checks |

No reviewer was launched. No agent made an AWS call or a commit, or read a secret, state or private tfvars file.

### service-engineer

```text
STATUS: COMPLETE (2 rounds)
FILES CREATED:
  modules/services/src/main/.../{AwsConfig,AwsPorts,AwsComposition,ReadinessGate,LiveAdapters}.scala
  modules/services/src/test/.../{AwsTestSupport,AwsConfigSpec,ReadinessGateSpec,AwsCompositionSpec,AwsBootstrapSpec,
    LiveGraphSnapshotSpec}.scala
FILES MODIFIED: ServiceMains.scala, GraphApi.scala, modules/services/README.md
CHANGE:
  Modes: unconfigured | offline-synthetic | aws. The aws mode composes only the storage and rag adapters; a source
    scan forbids InMemory/Deterministic/Offline/Fixture/Synthetic tokens.
  Configuration: fail-closed env validation (exit 2, value never echoed). The inference-profile ID is accepted as the
    Converse modelId; temperature 0.0 and the forced tool choice are unchanged (P14-1).
  Readiness: bounded, cached and single-flight dependency probes through the ports, using only granted actions.
    Liveness never touches a dependency. Empty data counts as ready.
  graph-service: NeptuneGraphReader.connect through StorageGraphReaderProvider; LiveGraphSnapshot over
    directedEdges; undirected COAUTHORED_WITH handling; no invented provenance (coauthor rows carry `evidence`
    pointers and provenance null; rows missing both are refused with 502).
TEST RESULTS (agent-reported): services 90 tests in 12 suites (40 earlier, 50 new); sbt check exit 0, totals
  207/64/39/50/100/107/90/667/18, 0 failed, 1 canceled.
RISKS: nothing live-verified. Bedrock has no free readiness probe, so model access shows only on the first call.
  Planner usage is not in the audit modelUsage. A placeholder query-embedding carrier exists (rag port shape).
  Remote community reads are refused. Stage deadlines (5 s) may be tight.
MANUAL ACTION REQUIRED: human review; runtime_composition_verified stays false until the recheck APPROVE and the
  commit.
```

### storage-engineer

```text
STATUS: COMPLETE
FILES CREATED: modules/storage/src/test/.../DirectedGraphReaderSpec.scala (20 tests)
FILES MODIFIED: StoragePorts.scala (additive types and trait), NeptuneGraphReader.scala, InMemoryStorage.scala,
  modules/storage/README.md
CHANGE:
  NeptuneGraphReader.connect(endpoint, region, credentials, config): Either[String, NeptuneGraphReader]
    - strict https + explicit-port endpoint and region checks; no network call;
    - SDK retries off (the reader's own retry policy applies); owned client closed once.
  DirectedGraphReader.directedEdges(id, window, direction, edgeTypes, limit, cursor)
    - three fixed parameterized openCypher templates; at most limit+1 rows per query;
    - malformed or over-bound responses refused;
    - in-memory fake agrees with the Neptune mapping on a hand-written 5-edge graph.
  The existing GraphReader and GraphNeighbor are unchanged.
TEST RESULTS (agent-reported): sbt check exit 0 (totals 207/64/39/50/100/107/78/667/18, 0 failed, 1 canceled).
RISKS: the Cypher templates are unverified against a live Neptune engine; ORDER BY string-collation; SKIP paging
  without snapshot isolation.
```

### infra-engineer, rounds 4 and 5

```text
STATUS: COMPLETE
FILES MODIFIED:
  infra/terraform/deployer/{phase14_main.tf,variables.tf,README.md,tests/deployer.tftest.hcl}
  infra/terraform/modules/identity/{main.tf,variables.tf}
  infra/terraform/modules/network/main.tf
  infra/terraform/modules/runtime/{compute.tf,variables.tf,outputs.tf}
  infra/terraform/{main.tf,phase12b.tf,phase12b-variables.tf,README.md}
  infra/terraform/environments/course.local.tfvars.example
  infra/terraform/tests/{phase14a,phase12b,phase12c}.tftest.hcl
  scripts/phase12d-spike/tests/test_terraform_static.py (D6 exception removed)
F2:
  KMS:
    - Removed KmsManageProjectKeys, KmsUseProjectKeysViaServices and KmsGrantsForAwsResourcesOnly from IAM.
    - The key policy now has 5 statements: account-root delegation, S3 Vectors decrypt, DeployerAdministersThisKey
      (15 actions), DeployerUsesThisKeyOnlyThroughServices (via 9 services), DeployerGrantsForAwsResourcesOnly.
    - kms:TagResource on key/* stays, because AWS requires it for tagging at CreateKey (AWS KMS add-tags doc),
      limited by request tags and aws:TagKeys.
  Security groups: aws_default_security_group.closed removed; Ec2AdoptedDefaultSgRevokeRules and
    Ec2AdoptedDefaultSgFirstTags deleted. D4 and D6 are superseded for these statements.
  Documents: keys-obs 3327 and network-mod 1702 characters; 363 Allow actions in total.
F5: LimitExceeded rule in deployer-apply-proposal.md and the deployer README. Plan counts unchanged (16 add, 9 destroy).
F1 infra:
  Task environment: SCHOLARCHAIN_SERVICE_MODE=aws only when enabled AND runtime_composition_verified; otherwise
    unconfigured, with no aws variables.
  Variables: per-role variables from the service contract. The synthesis model is the profile ID when set,
    otherwise the foundation ID. Secrets stay ARN bindings.
  Embedding model version: new root variable embedding_model_version (null default, guarded). It is a human value;
    see approval request row 18.
  Grants:
    - ReservationInQuerySessionTableAndIndex for embedding-worker;
    - ListRagBucketPrefixes (s3:prefix-scoped) and HeadAbsentRagKeyAs404NotListing (Null s3:prefix = true) for
      query-api and embedding-worker.
    Both are within the runtime boundary.
TEST RESULTS (agent-reported):
  deployer 62/0; root 117/0; phase12d-spike suite 78 OK; guard 93 files with 0 findings; tests/infra 246 OK.
  Mutations: deployer 40 (39 caught by the deployer suite; M32 is caught by the root suite); root F2 46/46;
    root F1 19/19.
RISKS:
  - The HEAD-absent-key mechanism rests on undocumented S3 behavior (P14-7).
  - The key policy is authored from documentation; the lockout check is unobserved live.
  - The default SG is unmanaged and keeps AWS's default rules.
```

### test-engineer, round 2

```text
STATUS: COMPLETE
FILES MODIFIED: tests/infra/{test_static_sources.py,phase14_checks.py,test_phase14_main.py,README.md}
CHANGE:
  The 5 stale tests now expect zero aws_default_security_group, and the over-limit pad is computed from the document
    size.
  New hand-derived checks:
    - no_kms_administration_in_iam;
    - security_group_mutations_need_project_tag;
    - security_group_tagging_cannot_adopt;
    - no_default_security_group.
  New class Phase14F2InMemory (20 tests).
  Deviation: check (c) also accepts the project resource tag (Ec2RetagProjectResources), because such a grant cannot
    adopt a foreign untagged group.
TEST RESULTS (agent-reported):
  tests/infra 246 OK; 113 phase14 mutations, all caught; guard 0 findings; self-test 16 OK.
  An earlier run gave 5 transient failures while infra was mid-edit; the 5 tests passed when re-run alone, and the
    whole suite passed when re-run.
```

## Subphase 14B — Step 0 and the Q6 repair

### infra-engineer (Sonnet 5.5, high effort)

STATUS: COMPLETE. OWNER: infra-engineer. WORK ORDER: 14B Step 0 Q6 / review 2 N3, plus the N4 stale comment in the touched file.
FILES CREATED: `infra/terraform/tests/phase14b.tftest.hcl` (8 runs).
FILES MODIFIED: `infra/terraform/modules/runtime/compute.tf` (local `load_balanced_service` shared by the `load_balancer` block and `health_check_grace_period_seconds`; N4 comment), `infra/terraform/modules/runtime/variables.tf` (`health_check_grace_period_seconds`, number, default 120, whole seconds 0..3600), `infra/terraform/README.md` (stale sentence and a grace-period paragraph).
COMMANDS RUN / TEST RESULTS: see `test-report.md` B1.
ASSUMPTIONS: no root variable; the module default is the single source. Upper bound 3600 s.
RISKS: 120 s is a mitigation, not proof; if peers take longer the circuit breaker is still reachable. Reviewer note (no change): `/healthz` on the ALB target group would decouple query-api's public health from its peers; keeping `/readyz` makes the grace period load-bearing on every redeploy. Two shell edits were refused by the PreToolUse hook and redone with Edit.
MANUAL ACTION REQUIRED: review; the user's commit. BLOCKED-ON OWNER: none. BLOCKED-ON EVIDENCE: none. NEXT GATE: review, then the user's commit.

### test-engineer (Sonnet 5.5, high effort)

STATUS: COMPLETE. OWNER: test-engineer. WORK ORDER: independent static test of the Q6 requirement, written from the requirement.
FILES CREATED: `tests/infra/phase14b_checks.py`, `tests/infra/test_phase14b_grace.py` (13 tests).
FILES MODIFIED: `tests/infra/README.md`.
COMMANDS RUN / TEST RESULTS: see `test-report.md` B1.
ASSUMPTIONS: the variable name is derived from the expression; a shared local is allowed; the "same condition" check is behavioural (truth table over the four services, with and without a certificate); the 3600 bound is not asserted.
RISKS: text-only; a refactor outside the evaluator grammar fails closed. Two shell edits were refused by the PreToolUse hook and redone.
BLOCKED-ON OWNER: none. NEXT GATE: review.

### Coordinator

Recorded the Step 0 answers, the tentative Nov 11 date and the open HTTPS-certificate item in `prompt.md`; ran B2 and B3; assembled evidence under `evidence/14b/` (`gates/check-full-q6.txt`, `gates/sbt-check-live-q6-summary.txt`, `q6/pin-drift.txt`, `q6/test-engineer-mutations.jsonl`). No live command, no commit.

## Subphase 14B — repair round 1 (14B review 1, B1)

### infra-engineer (Sonnet 5.5, high effort)

STATUS: COMPLETE. OWNER: infra-engineer. WORK ORDER: B1 option (a).
FILES CREATED: `infra/terraform/tests/phase14b_root.tftest.hcl` (6 runs); `infra/terraform/tests/phase14b.tftest.hcl` rewritten (30 runs); `target/phase14/evidence/14b/r1/infra-mutations.txt`.
FILES MODIFIED: `modules/runtime/compute.tf` (explicit target-group `interval`, `timeout`, `healthy_threshold`, `unhealthy_threshold` from variables; precondition timeout < interval; service precondition grace ≥ healthy_threshold × interval when load-balanced), `modules/runtime/variables.tf` (grace default 300; `health_check_interval_seconds` 30 [5–300], `health_check_timeout_seconds` 5 [2–120], `health_check_healthy_threshold` 3 [2–10], `health_check_unhealthy_threshold` 3 [2–10], all whole), `modules/runtime/outputs.tf` (`compute_controls.target_groups`, for tests), `main.tf` (one line), `phase12b-variables.tf` (root `query_health_check_grace_period_seconds`, default 300, whole 0–3600), `environments/course.local.tfvars.example` (commented line), `README.md` (variable table and arithmetic: unhealthy after 3 × 30 = 90 s, recovery 3 × 30 = 90 s, 300 s covers peers ready within about 200 s).
ASSUMPTIONS: the timing variables stay module-level (tuning them needs a commit); timeout 5 matches the ELBv2 HTTP default.
RISKS: the guard's refusal is tested only at module level (`terraform test` cannot expect failures on a module resource from a root run); nothing live-verified.
BLOCKED-ON OWNER: none. NEXT GATE: recheck review.

### test-engineer (Sonnet 5.5, high effort)

STATUS: COMPLETE. OWNER: test-engineer. WORK ORDER: update the independent check for B1 option (a).
FILES MODIFIED: `tests/infra/phase14b_checks.py`, `tests/infra/test_phase14b_grace.py` (21 tests), `tests/infra/README.md`. Evidence: `target/phase14/evidence/14b/r1/test-engineer-mutations.jsonl`.
ASSUMPTIONS: the guard is a lifecycle precondition on the service; validation must reject -1, a fraction and 2147483648 (exact bounds not asserted); the root variable name is discovered from the pass-through.
RISKS: static text checks; a rewrite outside the evaluator grammar fails closed.
BLOCKED-ON OWNER: none. NEXT GATE: recheck review.

### Coordinator

Appended 14B review 1 verbatim to `review.md`; logged B1 and N1–N5 in `repairs.md`; recorded the repair decision and the N1 arithmetic (USD 3.82 headroom for Nov 11) in `prompt.md`; corrected the deployer-apply dates (N3); added the dated 14B addendum to `approval-request-14a.md` (N2); retained snapshot identity counts and both mutation records as evidence files (N4); ran R2 and R3. No live command, no commit.

## Subphase 14B — replan under the USD 25 cap

The coordinator assembled this from the agent reports. Every agent ran Sonnet 5.5 at high effort. None ran live commands, made AWS calls, or read secrets, private tfvars or state.

| Owner | Delivered | Open items |
|---|---|---|
| infra-engineer | Shape flags and Fargate 256 CPU; ACM in base-apply with validation in runtime-apply; Neptune tunnel task; Neptune outputs; delete-everything cleanup; deployer ACM and ECS Exec grants; four MFA operator roles (4 h, `aws login`) plus the pipeline role in the same deployer apply; billing modify mode at USD 25 with alerts at 10/15/20; `upload-slice.sh`, `upload-emr-artifacts.sh`, experiment tokens, `smoke-test.sh --checks`, release.conf pins | Pre-session items 4–7, 9 and 10; two trailing blank lines (P4) |
| build-engineer | Reproducible entity-resolution job JAR and EMR artifact manifest, built locally only | none |
| spark-engineer | Neptune CSV part cap of 16 MiB; real slice re-exported (run `f6e63b4b`, 78,104 nodes, 328,967 edges; `evidence/14b/replan/real-slice-export.md`) | none |
| storage-engineer | Bounded runtime artifact (≤ 10,000 rows, 16 MiB) with a selection rule; loader timeouts; credential check; Phase 8 R3 fixed | Pre-session item 2 (shared); one trailing blank line (P4) |
| rag-engineer | Phase 8 N15 fixed; embedding token-cost bound before any Titan call; 14C templates (`evidence/14b/replan/14c-templates.md`); fallback note; offline Anthropic client in a separate, unmerged worktree | Pre-session item 8 |
| experiment-engineer | Load generator with non-LLM endpoints by default and the shared Haiku cap; 15A manifests for three sizes; 15B and 16B manifests; Haiku bucket ledger (10/60/40/5) | Pre-session items 1–3 |
| deploy-engineer | Read-only drafting run (Sonnet 5.5, high effort; task "draft exact session runbook"), launched by the coordinator on 2026-11-08. No file edited, no live command, no AWS call, no `--execute`; it was limited to reading files and to `--help` or dry-run modes that make no AWS call. Its draft came back to the coordinator as report text. Documentation-engineer turned it into the runbook, and the gaps it found became the gap routing in `prompt.md` ("Gap routing … after the deploy-engineer runbook draft"). This corrects the earlier omission (review N6). The 14A statement that deploy-engineer was not used (`owner-report.md:14`) is still true for 14A | none |
| documentation-engineer | `docs/runbooks/phase-14-live-session.md` (sections A–E, glossary, go/no-go checks), from the deploy-engineer draft | none |
| test-engineer | Independent suites for every item, including direct assertions for A3 and U1; account-scan merge-base fix; timeout-test retry; source-guard allowlist entries; 53 of 53 final mutants caught | AWS example-account exception awaiting confirmation; one trailing blank line (P4) |

### Coordinator

- Recorded the user decisions in `prompt.md`.
- Wrote `approval-request-14b-replan.md`.
- Built clean snapshots 7 and 8 and ran the seven-gate check on both (snapshot 7 failed and was repaired; snapshot 8 passed).
- Ran the live `sbt check`.
- Sanitized the evidence logs.
- Recomputed the pin drift.

No live command and no commit.

## Subphase 14B — repair round 2 (14B review 2, B2; N1–N8)

Every agent ran Sonnet 5.5 at high effort. None ran live commands, made AWS calls, committed, or touched any whitespace.

### infra-engineer

STATUS: COMPLETE. WORK ORDER: B2.
FILES MODIFIED:
- `scripts/lib/verify.py`: `prespend` takes exactly one of `--min-headroom D` or `--no-headroom-floor`. A required mutually exclusive group means both or neither exits 2. In no-floor mode the headroom comparison is skipped, but the field must still be a finite number. It prints `PRESPEND: cleanup-prepare has no headroom floor (remaining_headroom_usd=<2 decimals>)`.
- `scripts/deploy.sh`: `HEADROOM_ARGS` comes from STAGE alone. cleanup-prepare gets `--no-headroom-floor`; every other stage gets `--min-headroom ${PRESPEND_MIN_HEADROOM_USD}` (3).
- `scripts/config/release.conf`: `PRESPEND_MIN_HEADROOM_CLEANUP_USD` removed, and its comment explains there is no cleanup floor and no config key.
- `scripts/lib/common.sh`: the stale key removed from `SC_PINNED_KEYS`.
- `scripts/README.md`: lines 53, 156 and 265.
- `scripts/tests/test_deploy.py`, `test_verify_redact.py`, `test_syntax.py`, `test_pipeline.py`: updated and new cases.
DESIGN NOTE: no environment variable or config value can select the no-floor path.
RISKS: a caller of `verify.py --no-headroom-floor` gets no floor. Only deploy.sh calls it, and test-engineer's static guard (f) enforces this.
BLOCKED-ON: closed. The test files went to test-engineer, and the approval request §4 and §7 were updated by the coordinator.

### test-engineer

STATUS: COMPLETE. WORK ORDERS: the named account-scan exception, and the B2 tests.
FILES MODIFIED:
- `tests/infra/account_scan.py`: `ScopedSynthetic(name, value, path, pattern)` entries. `aws-documentation-example-account` has the exact value, the exact path compared by string equality, and pattern None.
- `tests/infra/test_billing_replan_14b.py`: class `AwsDocumentationExampleAccountEntry`, tests (i)–(v).
- `tests/scripts/test_prespend_floors_14b.py`: rewritten, 26 tests covering (a)–(f) and extras.
- `tests/scripts/test_pipeline_refusals.py`: stale key references removed.
- `tests/infra/README.md`: content only. The trailing blank line was left as it was.
ASSUMPTIONS: a non-numeric `PRESPEND_MIN_HEADROOM_USD` refuses every stage, cleanup-prepare included, as deploy.sh validates the config before the stage branch.
RISKS: mutation (a1), a path turned into an equivalent pattern, is caught only by the structure test (iv).

### documentation-engineer

STATUS: COMPLETE. WORK ORDER: B2, runbook part.
FILES MODIFIED: `docs/runbooks/phase-14-live-session.md`, in place with no added lines:
- glossary line 96;
- R.1 lines 616 and 617;
- C2 lines 1293, 1298 and 1303;
- E5 line 1416.
They now say cleanup-prepare has no headroom floor, a negative headroom is accepted, and the receipt is still fully checked. Lines 432, 437 and 845 were left untouched (whitespace deferred).
NOTE: C2 describes the printed line in general terms. The exact text is `PRESPEND: cleanup-prepare has no headroom floor (remaining_headroom_usd=…)`.

### Coordinator

- Appended the review 2 verdict and the reviewer's follow-up verbatim to `review.md`:
  - replaced the email-bearing plan path at line 378 with `<plan path>` (N2);
  - replaced the AWS example ID in the quoted follow-up with a placeholder;
  - noted each substitution.
- Logged B2 and N1–N8 in `repairs.md`.
- Recorded in `prompt.md`:
  - the user's decisions (whitespace deferred; the test exception);
  - the answers to B2 and N1;
  - the full-check timing decision.
- Wrote approval request §3.2 (tax at 11%: totals, the 2.5 NCU effect, the failed 42 h floor and the options), §3.4 (N4), §4 and §7 (B2) and §5 (N5). Wrote the deploy-engineer provenance (N6).
- Ran Q2.

No live command and no commit.

## Subphase 14B — post-approval (review 3 APPROVE; F1–F3, whitespace, caps = planned use)

Every agent ran Sonnet 5.5 at high effort. None ran live commands, made AWS calls or committed.

| Owner | Files | Result |
|---|---|---|
| infra-engineer | Whitespace: `infra/terraform/billing-execution/README.md`, `scripts/billing/PUBLICATION.md`, `infra/terraform/tests/phase14b_root.tftest.hcl`. Cap: `scripts/config/release.conf` (`EMR_CUMULATIVE_CAP_USD=2.52`, with the reason in the comment), `scripts/run-bounded-pipeline.sh` (help text), `scripts/README.md` (5 statements), `scripts/tests/test_pipeline.py` (re-derived boundaries), `scripts/tests/test_budget.py` (2 new tests) | done |
| storage-engineer | `modules/storage/README.md`, final newline only | done |
| test-engineer | `tests/infra/README.md` (final newline); `tests/scripts/test_cap_pins_14b.py` (new); `test_prespend_floors_14b.py`, `test_llm_budget_14b.py`, `test_pipeline_refusals.py` (cap expectations) | done; mutations m1, m2 and m2b caught |
| experiment-engineer | `experiments/manifests/llm-allocation.json`, `load-tests/config/load-profile.v1.json` (`shared_cap_usd` 1.33); READMEs, manifest notes and docstrings; `load-tests/tests/*` and `experiments/tests/*` (re-derived) | done. Risk: the shared-cap reserve is USD 0.00175 |
| documentation-engineer | `docs/runbooks/phase-14-live-session.md`: trailing whitespace at lines 432, 437 and 845; hard stop H37 and cleanup by H35 (13 lines, including the approval-expiry H0 + 37 h); R.1 with tax and the new caps; the R.2 JSON example (0.56 / 21.01 / 3.09); the B9, GO/NO-GO 6, E8 and E9 caps; the idle rates with tax | done |
| coordinator | Recorded review 3 verbatim. Logged F1–F3. Redacted the plan path at `review.md:136` and `:263` (F3). Recorded the user decisions (F1 37 h, F3, N4, caps = planned use, review order). Updated approval request §1, §3.2 (37 h projection, the H0-receipt finding and the current projection), §3.3, §4, §5 header, §8 status and §11. Ran S2 | done |

## Subphase 14B — post-approval delta repair (review 4: D1; N1–N5)

Every agent ran Sonnet 5.5 at high effort. None ran live commands, made AWS calls or committed.

| Owner | Files | Result |
|---|---|---|
| experiment-engineer | `experiments/README.md:23`, `experiments/scripts/render_manifests.py:23` | D1 done: cap 2.52; scale-out 2.94 > 2.52 needs a human cap decision |
| infra-engineer | `scripts/tests/test_pipeline.py:580` (comment only) | N1 done |
| documentation-engineer | `docs/runbooks/phase-14-live-session.md:614-615` | N2 done (0.3096, about 0.31); N3 margin sentence added |
| coordinator | `review.md` (review 4, verbatim), `repairs.md`, `prompt.md` (N4 and N5 answers; ruling pending), `test-report.md`, `owner-report.md` | done |

## Subphase 14B — final full check (snapshots 9 and 10)

| Owner | Work | Result |
|---|---|---|
| coordinator | Built snapshots 9 and 10; ran the seven-gate check on both; ran the live `sbt check`, the whitespace check and the pin-drift check; masked the placeholder at `review.md:909` (verbatim-text redaction with a note, user decision); sanitized logs; replaced approval request §8 | snapshot 9 failed (account scan, U1); snapshot 10 `RESULT: PASS gates=7` |

No agent was launched. No live command and no commit.

## Subphase 14B — repair round 3 (Anthropic API and Voyage AI switch)

Base SHA `f5490d3` (branch `phase-14`). Work order and shared contract: `prompt.md`, "Repair round 3 work order". Every agent ran Sonnet 5.5 at high effort; none ran live commands, made AWS, Anthropic or Voyage calls, read secrets, or committed. Counts below are agent-reported; the coordinator's own runs are in `test-report.md`.

| Owner | Delivered | Agent-reported gate |
|---|---|---|
| experiment-engineer | load profile on `claude-haiku-5-5` (0.10 / 0.50 per 1M; tokens +30%: 1,950/260 and 5,200/1,040); unit USD 0.001365, 115 answers USD 0.156975; shared cap still 1.33; embeddings block (voyage-4-lite, 256, 0.02 per 1M, 200M free, cap 0.30); `cost_report` in loadgen; manifests and check_manifests | load-tests 54 OK; experiments 28 OK; check_manifests OK |
| rag-engineer | Anthropic client taken byte-identical from worktree `phase14-anthropic-fallback` (sha256 checked; its README diff not taken) and updated to the Haiku 5.5 rules; Voyage client; provider selection; vector-consistency check; provider-aware embedding cost bound with token counter; follow-up: model ids, endpoints, limits, price and cap moved into `ProviderDefaults.scala` with one-line rationales (plan rule 6.7); worktree untouched | rag 179, then 186 OK |
| service-engineer | provider switches and key env parsing via rag's types; keys held redacted; Bedrock clients only when selected; `RagProviderClients` with one embedding counter per process; startup vector-consistency check; follow-up: model ids, versions and dimension from configuration with rag defaults | services 105, 112, then 113 OK; rag 186 OK |
| infra-engineer | `phase14b-providers.tf`; secrets `scholarchain-<env>/anthropic-api-key` and `/voyage-api-key` only when selected, no version, recovery window 0; ECS secret injection per service; `InjectProviderApiKey` scoped per role; provider guard; deployer `keys-obs` (no PutSecretValue); Bedrock grants only for a bedrock provider, no Marketplace; receipts require Anthropic and Voyage spend; `PRESPEND_PROJECT_CEILING_USD=25` arithmetic check; cleanup deletes both secrets and prints the key-revocation reminder; `scripts/lib/cost_report.py` | terraform root 268, deployer 111 passed; scripts/tests 1,030 ran with 7 `test_terraform_r1` failures caused by untracked new files (10/10 with the file intent-added) |
| documentation-engineer | root `README.md` (new; none existed), `docs/report/provider-fallback.md` (new report section), runbook: superseded Bedrock-only steps, new unit, B3b key-entry guide (method pending user confirmation), receipt fields, key revocation, three-provider monitoring | docs only; 16 cited paths exist |
| test-engineer | repaired fixtures broken by the switch; new `tests/infra/test_providers_14b.py` (34), `tests/scripts/test_providers_14b.py` (26), `IndependentProviderRound3Spec.scala` (18) | tests/infra 460, tests/scripts 462, independentTests 693, all OK |

### Incident (infra-engineer)

The infra-engineer ran `git stash` and `git stash pop` once while other agents were editing. Tracked edits were briefly reverted and then restored. The coordinator compared `modules/services/.../ServiceMains.scala` with the copy the agent saved (identical), confirmed the service-engineer's later edits were on top of it, and that the live `sbt check` passed after all edits. Later work orders forbid `git stash` and any command that rewrites other agents' files.

### Open for the user

- Key-entry method (runbook B3b): AWS console with the user's own identity (coordinator default) or `file:///dev/stdin`.
- The infra-engineer's USD 25 receipt arithmetic check (added beyond the work order; it refuses a receipt whose headroom exceeds 25 minus recorded spend and reserves; it does not block spending).
- The synthesis cap stays 1.33 against the plan's 1.50 (Step 0 answer 3).

## Subphase 14B — pre-session items (after review 7 APPROVE; round 3 committed as `13b886a`)

Base SHA `13b886a` (branch `phase-14`). Decisions: `prompt.md`, "Subphase 14B — pre-session items" (user: "accepts all by default") and "Coordinator decisions from the wave 1 reports". Every agent ran Sonnet 5.5 at high effort; none ran live commands, made AWS, Anthropic or Voyage calls, read secrets, used git stash, changed the index or committed.

| Owner | Items | Delivered | Agent-reported gate |
|---|---|---|---|
| experiment-engineer | 1, 2, 3 | `experiments/inputs/15a/config-sources.json` (the three committed EMR config files with sha256); `experiments/scripts/derive_14c_inputs.py` and the committed `experiments/inputs/14c/` (40 include IDs, `real-query.json`, 40 questions, 100 node IDs, provenance); `load-tests/eval16b.py` (16B command, charges bucket 16b itself; `plan` makes no network call); README and 16B manifest updates. Item 2 was reworked once (degree band 10..22, total-degree budget 900; include total 813) after the storage check refused the first list | experiments/tests 50 OK, load-tests/tests 70 OK, `check_manifests.py` OK; local `RuntimeArtifactMain` exit 0, `SELECTION: rows=9643 bytes=9633173 researchers=41 (include-list=40 fill=1)` |
| storage-engineer | 2 (check) | Offline check: include-list format conforms (`RuntimeArtifactSubset.scala:19-37`); first list refused on the 10,000-row cap (`include-list-exceeds-cap`, exit 1); every node ID and named researcher resolves; verified the degree-band fix. No storage code changed | local `RuntimeArtifactMain` runs only (target/) |
| rag-engineer | 8 | `idempotencyIndex` confirmed as the GSI name `by-idempotency-key` (`infra/terraform/variables.tf:156-160`, consumed in `modules/storage`); guard in `LiveEmbeddingConfig` refusing a blank, malformed or table-equal value; `LiveEmbeddingIdempotencyIndexSpec` (3); replacement text for the stale 14C template fields | rag 192 passed, 0 failed |
| infra-engineer | 4, 5, 6, 7, 9, 10 | `scripts/lib/emr_service_policy.py` (render and check of `emr_service_policy_json`) and tests; billing login wording "to be confirmed live in the session"; 28 (modify gate) and 29 (post-modify verification gate) both correct, cross-referenced and pinned by tests; output `vector_bucket_name`; offline expected plan deltas (`phase14b_plan_deltas.tftest.hcl`, `scripts/config/expected-plan-deltas.json`, `scripts/lib/plan_deltas.py` checker); archive refuses plan files and same-named receipts (two tests) | terraform test 272 passed; scripts/tests archive 27, emr_service_policy 9, plan_deltas 15; billing 113/62/39; tests/infra 460 |
| documentation-engineer | runbook for 1–10, O2 | Every "Gap" note for the 10 items replaced (count 0); A1, A3, A8, A10, A12, B8.3–B8.6, B9.1–B9.3, B11, B13.3 updated; `templateVersion` `phase14c-v1` in render-config only; B13.3 numbered receipt copies; A4 STOP rule (review 7 O2) | `git diff --check` clean; link and privacy checks clean |

Coordinator: recorded the user's answers and the item 4 values (`runtime_reference`, `templateVersion`), added superseding notes on top of `evidence/14b/replan/14c-templates.md` and `fallback-note.md` (old text unchanged), routed the item 2 rework, answered the `templateVersion` question, and ran the gates in `test-report.md` ("Pre-session items").

### Open for the user

- Review the 40 questions in `experiments/inputs/14c/questions.txt` and the smoke question (`real-query.json`, "Songwu Lu") before the commit freeze.
- Pin refresh before the commit: 2 rows drift (`infra/terraform/README.md`, `infra/terraform/outputs.tf`).
- Your plan file still says the synthesis cap is USD 1.50; the decided cap is 1.33 (extra D).
- Not routed (recorded): the archive name filter does not match `*.plan.txt` (no runbook include reaches `target/phase14/private`); review 7 O1 (Voyage 2048 dimensions refused at preflight); N1–N4.

## Subphase 14B — pre-session R1 (review 8: REQUEST-CHANGES B1, B2)

Base `13b886a`. Every agent ran Sonnet 5.5 at high effort; no live command, no AWS, Anthropic or Voyage call, no secrets read, no git stash, no index change, no commit.

| Owner | Finding | Delivered | Agent-reported gate |
|---|---|---|---|
| experiment-engineer | B1, N1, N2 | Question 28 replaced in `derive_14c_inputs.py`; `questions.txt` and `provenance.json` regenerated (other three files byte-identical); shape test plus a test that no question has an `in window since-` id; `experiments/README.md` no longer claims the 40 are in the planner grammar without the real-planner check; `load-tests/README.md` counts; shared-cap refusal test for `eval16b` | experiments 51 OK, load-tests 71 OK |
| rag-engineer | B1 | `Phase14QuestionSetPlannerSpec`: all 40 committed questions `Planned` through the fallback; 8 ranking lines with hand-derived operation, metric, measure and window; old phrasing `Unsupported` (documents N4); `QueryPlannerAgent` unchanged | rag 196 |
| documentation-engineer | — | Not needed: the runbook and the 16B manifest do not quote the changed question or its hash | — |
| coordinator | B2, N3 | Reran the billing files per file, the `suite_run` comparison on a clean clone, Terraform fmt/validate, the experiment gates, `sbt check`, `git diff --check` and the privacy scan with retained logs (`evidence/14b/presession/r1/`); corrected the W2 cause statement in an appended section | see `test-report.md` X2 |

**Cost-to-date (N3).** No spend this round: every step was offline. Cost-to-date is unchanged at the last recorded figure, USD 0.34 (AWS, `approval-request-14b-replan.md` §1 and §3.2), with Anthropic USD 0 and Voyage USD 0 (no key exists yet); combined USD 0.34 of the USD 25 ceiling.

Not routed: N4 (planner coverage regex and "in window since-…" phrasing, rag-engineer, future scope); N5 (`*.plan.txt` archive name filter, infra-engineer, future scope). N6 accepted.

## Subphase 14B — runbook A1 preparation (after commit 2eb30ef)

| Owner | Delivered | Gate |
|---|---|---|
| coordinator | A1.2 expiry read (user kept 2026-11-25); A1.4 `sbt -batch packageEmr` (exit 0, JDK 17.0.20.1; JAR manifest sha256 `1d977b23b5371cf6f49cc9b3d538779a4e9511181a29e613ede926a7808465d4`); `upload-emr-artifacts.sh` dry run with a placeholder account (no AWS call; `RESULT: PASS`, 7 `EMR-RENDER` lines; the 3 fixed values equal the runbook); `approval-14c.md` drafted at the user's request and saved after the user's confirmation | logs in ignored `target/phase14/evidence/14b/` (`a1-expiration.log`, `a1-packageEmr.log`, `a0-decision.md`, `a1-emr-pricing.log`); dry-run output in `target/phase14/private/` |
| experiment-engineer | `render_manifests.py --overwrite` with the 7 values: 3 `15a-*` manifests (hashes only); `test_experiments.py`: helper `zero_artifact_hashes` and the two `RenderAndCheck` tests made independent of placeholder or real hashes | `check_manifests.py --final` `RESULT: OK (final: no placeholders)`; experiments/tests 51 OK (also OK, 1 unrelated skip, in a copy with the placeholder manifests) |
| user | A1.3 flag `EMR_PRICING_CONFIRMED_BY_HUMAN=true`; A0 decision; questions and plan cap confirmed; `approval-14c.md` confirmed | — |

No spend: cost-to-date unchanged at USD 0.34 (AWS), Anthropic 0, Voyage 0.

## Subphase 14B — A3 skipped by the user (after commit a87885e)

| Owner | Delivered | Gate |
|---|---|---|
| user | Decision to skip runbook A3 (budget stays USD 200, alerts 50/80/100%) | recorded verbatim in `prompt.md` |
| coordinator | Decision and its consequences recorded (late first alert at about USD 100; disclosed repository-versus-live drift in `billing-bootstrap`); no AWS call | — |

No spend: cost-to-date unchanged at USD 0.34 (AWS), Anthropic 0, Voyage 0.

## Subphase 14B — A4 deployer apply (after commit bfb7311)

| Owner | Delivered | Gate |
|---|---|---|
| user | Manual IAM window (decision "choose a"); deployer plan and apply in their own terminal; window closed at about 19:45 local | apply decision recorded in `prompt.md` before the apply |
| coordinator | Identified the missing admin profile; checked the saved plan (sha256 `7594d212…e33f`) against the v2 STOP rules; recorded the decision and results; no AWS call | Plan `29 to add, 0 to change, 9 to destroy` (Case A); apply `29 added, 0 changed, 9 destroyed`; verification `7` / `3600` / `14400` x4 / policy names as expected |

Coordinator error, corrected: the first tfvars command used `$ACCT:user`, which zsh expanded as a `:u` modifier; the plan failed variable validation and saved nothing. Fixed with `${ACCT}`.

No spend: IAM only. Cost-to-date unchanged at USD 0.34 (AWS), Anthropic 0, Voyage 0.

## Subphase 14B — A5 profiles and sign-in rehearsal

| Owner | Delivered | Gate |
|---|---|---|
| user | 7 profiles added to their AWS config (loader, reader, cleanup, pipeline, and three `-java` credential-process profiles); each role signed in once; session-manager-plugin installed | loader, reader, cleanup, pipeline and deployer (`scholarchain-deployer` and `-tf`) ARNs each name their own role with session `scholarchain-billing-operator`; `CREDENTIALS-RESOLVED ... sessionToken=true` for loader-, reader- and cleanup-java; aws-cli 2.35.4; session-manager-plugin 1.2.896.0 |
| coordinator | Commands and checks; caught a first pass in which three profiles took the loader browser session (redone) | ignored log `target/phase14/evidence/14b/a5-login-rehearsal.log` (account masked) |

No spend.

## Subphase 14B — A7 Secrets Manager secrets

| Owner | Delivered | Gate |
|---|---|---|
| user | Narrow IAM window (decision "let's do A"); four secrets created; raw API key in the password manager; window closed at about 15:23 local | four names printed twice as the runbook expects |
| coordinator | Policy text and commands; shape check of the private ARN file without printing it; records | no `get-secret-value`, no value in any log or file |

Spend: four secrets at about USD 0.40 per secret per month, prorated (cents until cleanup C5). AWS cost-to-date otherwise unchanged at USD 0.34; Anthropic 0, Voyage 0.

## Subphase 14B — A8 private tfvars (base stage) and EMR service policy

| Owner | Delivered | Gate |
|---|---|---|
| user | Private `course.local.tfvars` (base stage) and the rendered EMR service policy appended; Neptune 1.4.8.1 / `neptune1.4` and the domain decided | ignored and mode 600; 21 settings; EMR policy check 12 OK, `RESULT: PASS` |
| coordinator | Base values from recorded decisions; review of the EMR policy check output (the file itself not read) | — |

No spend.

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

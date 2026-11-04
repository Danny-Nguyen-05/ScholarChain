# Phase 12D Step A report — offline spike packaging and Terraform roots

STATUS: COMPLETE offline. Independent review: BLOCK (B1-B4), then BLOCK (R1), then APPROVE-WITH-NONBLOCKING on 2026-11-04 after the R1 repair. Findings and the carried nonblocking list are in [review-findings.md](review-findings.md). No cloud action.

## Repair after review (2026-11-03)

- **B1:** the only attach allowlist entry is now the EMR v2 managed policy, matched by exact equality. Customer-policy management is removed. Explicit Denies cover boundary policy versions and deletion, boundary removal or trust edits on spike roles, and `sts:AssumeRole` to spike roles.
- **B2:** all tagging is tag-on-create only, through `ec2:CreateAction` and `elasticfilesystem:CreateAction`. EMR AddTags is allowed only on clusters that are already stack-tagged.
  - KMS administration has moved into the key policy, granted to the deployer role (new variable `deployer_role_arn`).
  - The boundary's KMS ceiling is now scoped by alias.
  - **`aws_default_security_group` is dropped by human decision.** The VPC's default group keeps the AWS default rules, and nothing attaches to it.
- **B3:** `elasticmapreduce:Get/Put/RemoveAutoTerminationPolicy` are granted on stack-tagged clusters in both the instance policy and the boundary (source: AWS re:Post, emr-troubleshoot-cluster-termination).
- **B4:** the gate logs are now `.txt` files and none are git-ignored.
- **New residual risks from the repair:**
  - EMR may authorize `AddTags` inside `RunJobFlow` against a cluster that doesn't exist yet; the ResourceTag-only rule would then deny the create. That would fail closed at the first apply.
  - Boundary KMS alias scoping assumes `kms:ResourceAliases` is evaluated for the roles' key calls.
- **Post-repair gates:** deployer 22/22, spike 37/37, scripts 60 OK, guard 0 findings, request bound 561/1929/5610. `sbt check` exit 0, 1,267/0.

## Repair after re-review (R1, 2026-11-04)

- The boundary's region-only EC2 mutation ceiling is replaced by statements mirroring AmazonEMRServicePolicy_v2 (`deployer/permission_sets.tf:482-560`):
  - actions on existing resources require `aws:ResourceTag/for-use-with-amazon-emr-managed-policies=true`;
  - subnet, security-group and VPC targets additionally require the stack tag;
  - creates require `aws:RequestTag`;
  - CreateTags only with `ec2:CreateAction`;
  - v2's VPC-endpoint, placement-group and LaunchTemplateVersion actions are omitted.
- The instance role has no EC2 actions.
- New test `boundary_ec2_mutations_are_tag_conditioned_like_emr_v2` fails when a condition is removed.
- **New residual risks:**
  - The boundary is tighter than v2, so EMR could fail closed at launch if it needs an omitted action or sends no request tag.
  - EMR-tagged instances, ENIs and launch templates from other EMR use are not stack-scoped.
  - The boundary is 5,672 of 6,144 characters.
- **Gates:** deployer 23/23, spike 37/37, scripts 60 OK, guard 0, `sbt check` attempt 4 exit 0 (1,267/0).

The remainder of this report describes the pre-review Step A. Where repair changed a count, the post-repair figure in [gates.json](gates.json) supersedes the one here.
OWNER: coordinator (assembled from build-engineer, infra-engineer and test-engineer reports; all Sonnet 5.5, high effort).
WORK ORDER: [work-order.md](work-order.md). Baseline: [baseline.json](baseline.json) (HEAD b4207c8).

## What changed (untracked, not committed)

- `infra/terraform/deployer/`: new root for the scoped `scholarchain-deployer` role. Its trust allows only the operator ARN and requires MFA, with a 1 h session. Permissions come from `enabled_permission_sets = ["spike-emr"]`, so Phase 14 can add sets. A permissions boundary covers every role the deployer creates. PassRole is limited to `scholarchain-spike-emr-*` roles and to the EMR and EC2 services. The billing deployer is untouched.
- `infra/terraform/spikes/emr-spark-isolated/`: new root for the spike, built to the approved simplified design. It has:
  - one VPC with a private subnet and a public subnet for the NAT gateway;
  - EMR 7.8.0 with only Hadoop installed, 1 primary + 1 core m5.xlarge;
  - 4 gp3 volumes, 32 GiB each;
  - EFS with TLS and an access point, one KMS key with a 7-day deletion window, and one S3 bucket with `force_destroy`;
  - three steps (probe, then G1, then collect) and four termination layers.
- `scripts/phase12d-spike/`:
  - Bootstrap and step scripts. The bootstrap arms the shutdown deadline before it downloads anything, and fails on a sha256 mismatch.
  - preflight, collect-evidence, inventory and request-bound scripts, with fake-AWS tests.
- `tests/infra/terraform_source_guard.py` and its README: an exact allowlist of nine actions that have no resource type, sourced from the Service Authorization Reference. A statement is exempt only if all of its actions are on the allowlist.
- Source hashes: [source-hashes.json](source-hashes.json), 45 files.

## Runtime and Spark security

- Runtime tgz `789a96…6de5` is unchanged. The job JAR is mode 0644 with sha `d52f11…b86b`. The tgz contains only Scala 2.13.14 and Spark 3.5.4_2.13 jars, with no `_2.12` jar. See [build/runtime-verification.json](build/runtime-verification.json).
- **Chosen config:** `spark.authenticate`, `network.crypto.enabled` with the default AES-CTR cipher, **`authEngineVersion=1`**, `saslFallback=false` and `io.encryption.enabled`.
- **Local result:** with `authEngineVersion=2`, the G1 pipeline failed twice when combined with io encryption. With v1 the pipeline passed twice and the comparison was 28/28 tables exact. All of this was observed in local-cluster mode only.

## Gates (coordinator-observed; details in [gates.json](gates.json))

| Gate | Result |
|---|---|
| `sbt -batch check`, JDK 17 | exit 0; 1,267 passed, 0 failed; marker updated. Attempt 1 failed on the guard and was then repaired. |
| Terraform deployer root: fmt, validate, test | 0, 0, 0; 18 passed |
| Terraform spike root: fmt, validate, test | 0, 0, 0; 34 passed |
| Script unit tests | 57 OK |
| Request bound | PUT/LIST ≤ 561 of 1000; GET/HEAD ≤ 1929 of 10000; TF API ≤ 5712 |
| Terraform source guard: self-test and repo scan | 0 and 0 (0 findings) |
| `bash -n` | ok |
| shellcheck | not installed (unverified) |

## Cost ([cost-replay.py](cost-replay.py), reviewed public rates from 12d-emr-design-cost)

| Scenario | Total incl. 25% tax allowance and USD 0.75 reserve |
|---|---:|
| Nominal (cluster 2 h, ancillary 3 h) | USD 4.13 |
| Ancillary up 24 h | USD 5.50 |
| Ancillary up 72 h | USD 8.64 |
| Each extra day not destroyed (NAT 1.08, IPv4 0.12, EFS 0.05, S3 <0.01, before tax) | USD 1.57 |

The cap is USD 10. The KMS key is counted as a full month (USD 1).

## Disclosed limitations and carried risks

1. Hadoop and YARN RPC are unencrypted inside the single private subnet. No in-transit TLS certificates are used (human-approved).
2. AES-GCM is not used: the Spark 3.5.4 probe failures from `/tmp` are preserved in `target/phase12d-spike-offline/preserved-repair-probe/`. `authEngineVersion=2` with io encryption also failed locally, so v1 is used.
3. **Shutdown timer:** AWS documents that OS shutdown stops an EBS-backed instance, and that a stopped EMR primary terminates the cluster. It does not document EMR's instance-initiated shutdown behaviour, the detection delay, or what happens to the stopped instances and volumes afterwards. The timer is therefore best-effort. The guarantees are steps-then-terminate, TERMINATE_CLUSTER on collect, the 900 s idle timeout, and the same-session destroy plus inventory.
4. The provider's `aws_emr_cluster` waiter may report an error if the transient cluster reaches TERMINATING before apply polls it. The cluster's actual state must be read, not the apply exit code alone.
5. Untested until live:
   - the runtime's Hadoop 3.3.4 client against EMR's Hadoop 3.4.1 YARN;
   - YARN localization from `file://` staging on EFS;
   - the EFS TLS+IAM mount through NAT;
   - whether the minimal instance profile is enough;
   - the Corretto 17 path `/usr/lib/jvm/java-17-amazon-corretto`.
6. **Deployer scope:**
   - Nine actions remain on `Resource="*"` because they have no resource type: `tag:GetResources`, six EMR actions (including `RunJobFlow`, request-tag conditioned) and `kms:CreateKey` (request-tag conditioned) / `kms:ListAliases`.
   - (Superseded by the B2 repair: default security group adoption and its revoke/tag rights were removed by human decision.)
   - The EFS describe actions are ARN-scoped, so the inventory's list-all call may be denied; the inventory then exits 3 (inconclusive), not pass.
7. The EMR log-pusher request count (252 PUT) is an assumption. The figure of about 10 MB of G1 logs is not wired into the request model.
8. The lock files carry only the darwin_arm64 hash. shellcheck has not been run.
9. All verification is local or mock-only: no IAM effectiveness, EMR behaviour or live cost is proven.

## Next gate

Independent review (the human runs it in a separate session). After APPROVE comes Step B: the human approval record and the exact commands. No live action before that.

# Step A independent review — findings and dispositions

The review was run by the human in a separate session on 2026-11-03. The verdict was **BLOCK**, on four blocking findings. Everything else in the nine-point checklist passed. The reviewer's evidence included:

- 33 mutations, of which 28 were caught;
- all 45 source and 69 evidence hashes matching;
- exact cost arithmetic;
- replayed results: Terraform tests 34/34 and 18/18, guard 0 findings, script tests 57 OK, request bound 561/1929/5712.

This file records the findings as the coordinator received them. It is not a human decision record.

## Blocking findings, routed for repair

| ID | Finding | Owner | Repair |
|---|---|---|---|
| B1 | `iam:CreatePolicyVersion` on `policy/scholarchain-spike-emr-*` also matches the boundary policy. That allows escalation to admin, via a new boundary version, then CreateRole, then PutRolePolicy, then assume or pass the role. The AttachRolePolicy test used `contains`. | infra-engineer | Remove the statement and the spike-prefix PolicyARN branch. Explicit Denies on boundary policy versions/deletion and on `sts:AssumeRole` to spike roles. Exact-equality test. |
| B2 | Tag laundering: tagging resources the spike doesn't own unlocks permissions on them. Cases: CreateTags on any security group, then Authorize/Revoke/Delete; KMS TagResource on any key, then PutKeyPolicy/ScheduleKeyDeletion; EFS TagResource without CreateAction, then destructive actions; EMR AddTags on any cluster, then TerminateJobFlows; boundary CreateTags on existing EC2 resources. | infra-engineer | Tag-on-create conditions only. KMS admin moves into the key policy, granted to the deployer role. **Human decision 2026-11-03: drop `aws_default_security_group`** together with its revoke/tag rights. The default SG keeps AWS default rules, nothing attaches to it, and this is disclosed. |
| B3 | The idle auto-termination layer probably doesn't work. The instance profile lacks `elasticmapreduce:Get/Put/RemoveAutoTerminationPolicy`, according to AWS re:Post. | infra-engineer | Grant those actions on the stack-tagged `cluster/*` in both the instance policy and the boundary. Add tests. Correct the README and limitation text. |
| B4 | `.gitignore` `*.log` hides four gate logs that `gates.json` and the manifest cite. | coordinator | Gate logs are rewritten as `.txt` and the manifest regenerated. |

## Re-review (human, separate session, 2026-11-03): BLOCK on R1

B2, B3 and B4 were verified closed. B1 was closed only for the path originally reported. The reviewer replayed:

- Terraform tests 37/37 and 22/22;
- script tests 60 OK;
- guard 0 findings;
- request bound 561/1929/5610;
- sbt attempt 3 at 1267/0;
- 15 new repair mutations, of which 14 were caught.

| ID | Finding | Owner | Repair |
|---|---|---|---|
| R1 | The boundary statement `EmrServiceRoleEc2MutationCeiling` (`permission_sets.tf:473-488`) grants SG authorize/revoke, TerminateInstances, ModifyInstanceAttribute, RunInstances, DeleteNetworkInterface and ModifyVpcEndpoint on any region resource, with no tag condition. Escalation path: the deployer puts an inline policy on a spike role, passes it as the instance profile, and runs a bootstrap script. Node code can then open or terminate foreign resources. | infra-engineer | Mirror AmazonEMRServicePolicy_v2's conditions in the boundary: `aws:ResourceTag/for-use-with-amazon-emr-managed-policies=true` on existing resources and `aws:RequestTag` on creates. Add a test that every non-create EC2 mutation carries a ResourceTag condition. Correct the deployer README. |

The disclosed residual risks are accepted by the reviewer as nonblocking fail-closed live risks:

- **AddTags during RunJobFlow:** the AWS example uses `elasticmapreduce:ResourceTag`. Suggestion: also allow it.
- **`kms:ResourceAliases`:** risks are alias propagation delay and evaluation on grant-based calls. Either would fail at bootstrap and spend the single attempt.

## Nonblocking, listed once and carried (no rechecks)

1. **`emr/run-step.sh:21`:** `timeout` kills only the spark-submit client, not the YARN application. A hung probe can starve G1 on the single core node. Suggested fix: a trap that runs `yarn application -kill`.
2. **Network interfaces (`permission_sets.tf:356-363`):** ENI delete and modify-attribute are not scoped within the region. Disclose this.
3. **Inventory:** with `DescribeFileSystems` scoped to ARNs, the inventory's list-all call will likely always exit 3 (inconclusive). Allow it on `*` (read-only) or rely on the tagging API.
4. **`CreateFileSystem`:** it has no resource type but is granted only on `file-system/*` ARNs, so it may be denied. Verify at plan time.
5. **`kms.tf:45-54`:** the service role's CreateGrant has no `kms:GrantIsForAWSResource` condition.
6. **Mutations that survived the tests:** an added 0.0.0.0/0:22 ingress rule; a second KMS key; GetObject widened to `bucket/*`; added SNS/SQS resources (absence of dropped elements is not asserted); root volume gp3 IOPS/throughput not pinned.
7. **Tags:** the tag test checks `output.default_tags`, not each resource's `tags_all`.
8. **`bootstrap.sh:130-138,155`:** spark-defaults, the step scripts and the G1 config are not checked against sha256.
9. **Role operator:** `aws:MultiFactorAuthPresent` may be absent in role-chained or SSO sessions, which would lock the operator out. Verify before choosing a role.
10. **Guard:** it doesn't check conditions; for example, `kms:CreateKey` on `*` without the request-tag condition would pass. No deployer test asserts that condition.
11. **Housekeeping:** the empty `build/runs/ex1/` directory has been removed. Attempt 1's "666/1" counted only the failing suite; the log totals 1,253 succeeded and 1 failed across 8 suites. `gates.json` has been corrected.
12. **Re-review:** re-adding `aws_default_security_group` is not caught by any test. The deployer lacks the rights, so an apply would fail closed. A test asserting the resource is absent would close this.
13. **Re-review:** `CreateAccessPoint` (`permission_sets.tf:294-301`) is not scoped to the spike's file system; a stack-tagged access point could be created on another root's EFS. Suggested fix: its own statement requiring `aws:ResourceTag/scholarchain:stack`.
14. **Re-review:** KMS `TagResource` is allowed on any key, which AWS requires for tagged creation. No permission keys off KMS tags anymore. Options: restrict `aws:TagKeys`, or create the key untagged.
15. **Re-review, stale text:** `report.md:82` has been corrected by the coordinator. The comment at `kms.tf:26-27` still says the root statement "delegates to IAM (the deployer role)"; that is infra-owned and carried.
16. **Re-review:** spike roles can be given trust policies naming other principals; the Deny covers only the deployer assuming them. R1's fix reduces what such access is worth.

## Final re-review (human, separate session, 2026-11-04): APPROVE-WITH-NONBLOCKING

R1 is closed. The reviewer ran 12 R1 mutations, of which 11 were caught. All 46 source and 72 evidence hashes match, and no evidence file is git-ignored. The reviewer replayed deployer 23/23, spike 37/37, scripts 60 OK, guard 0 findings and sbt attempt 4 at 1267/0. All disclosed risks were accepted as fail-closed live risks.

17. **Carried, must close before Phase 14 or any other EMR cluster in us-east-2:** the boundary lets a passed spike role terminate or modify any EMR-tagged instance or ENI, and delete EMR-tagged launch templates (`permission_sets.tf:493-498,519-524,550-557`). This is the same reach as v2. `infra/terraform/modules/emr/main.tf:52` tags the main cluster with that tag. Suggested fix: require the stack tag on `instance/*`, since cluster tags propagate.
18. **Overstated wording:** `deployer/README.md:69` says node code cannot terminate a foreign instance, which is untrue for EMR-tagged instances. It also overstates the security-group stack-tag requirement for creates. There is no impact beyond the spike, because the subnet must carry the stack tag.
19. **Stale evidence lines:** the `gates.json` post-repair deployer count and `report.md:3` status were corrected by the coordinator after this review.
20. **Test gap:** the tag-condition test checks that keys are present, not that their value is `"true"`.

## Post-approval addendum (2026-11-04): deployer `aws login` permission

When the human tried `aws login` for the operator user, the coordinator found that the `scholarchain-deployer` role had no signin permissions, so `aws login --profile scholarchain-deployer` would fail in Step C.

- **Change (infra-engineer):** `infra/terraform/deployer/main.tf` adds `aws_iam_role_policy.login`. It grants `signin:AuthorizeOAuth2Access` and `signin:CreateOAuth2Token` on `arn:aws:signin:us-east-2:<account>:oauth2/public-client/localhost`, with `signin:OAuthClientId = arn:aws:signin:::devtools/same-device`. This matches the installed billing-role login policy.
- **Tests:** 2 new tests (deployer 25/25); a mutation widening the resource to `*` failed as expected.
- **Gates:** `sbt check` attempt 5 exit 0, 1267/0.
- **Status:** awaiting independent review before the deployer apply.
- **Operator login:** the operator user's own CLI login permission is handled by the human as a manual inline policy during the `IAMFullAccess` window, removed at the end of the window.

Addendum review (human, separate session, 2026-11-04 10:56): **APPROVE-WITH-NONBLOCKING**, with no blocking findings. The policy content matches the readback, and scratch mutations (an extra action, a widened resource, a changed client condition) all failed. Replay: deployer 25/25, spike 37/37, guard 7/7 self-tests and 0 findings. All 46 source and 73 evidence hashes match.

21. **Carried:** the login policy's attachment target is untested (`deployer.tftest.hcl:556`); retargeting `login.role` still passes. Add an assertion that ties it to the deployer role.
22. **Fixed by the coordinator:** `gates.json` attempt 5 now reads "9 sbt result groups (158 Scala suites)" instead of "9 suites". The same wording in attempts 2 to 4 refers to result groups.

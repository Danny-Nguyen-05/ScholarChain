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

## Live-found addendum (2026-11-04): parent-resource create permissions and credential refresh

Live attempt 1 failed before any cluster existed (`../12d-spike-live/attempt1-partial-apply.md`). The spike's create calls are also authorized against existing parent resources (the VPC, and for some calls the subnet, route table, elastic IP and security group). A request-tag condition never applies to an existing parent, so those calls were denied.

- **Change (infra-engineer):** `infra/terraform/deployer/permission_sets.tf` adds:
  - `Ec2CreateOnExistingStackParents`: CreateSubnet, CreateRouteTable, CreateSecurityGroup, CreateNatGateway and CreateVpcEndpoint on stack-tagged `vpc`, `subnet`, `route-table`, `elastic-ip` and `security-group`, with `aws:ResourceTag/scholarchain:stack` plus the region condition;
  - `EfsCreateAccessPointOnStackFileSystem`.
  A new resource has no tag yet, so these statements cannot authorize creating one. CreateTags is still CreateAction-only.
- **Tests:** a new 3-assertion test covers 24 EC2 and 5 EFS call/parent pairs (deployer 26/26). Removing `vpc/*` makes it fail.
- **Credentials:** the operator run method is documented in `scripts/phase12d-spike/README.md`: a `credential_process` profile, `scholarchain-deployer-tf`. At the human's request, the coordinator appended that profile to the human's `~/.aws/config` (append only, nothing else read). The human verified it resolves to `assumed-role/scholarchain-deployer`.
- **Gates:** `sbt check` attempt 6 exit 0, 1267/0.
- **Status:** awaiting independent review, then a human deployer re-apply in an admin window.

Live-found addendum review (human, separate session, 2026-11-04 12:00): **BLOCK**. The EC2 parent grants, the audit completeness, the `credential_process` method, the evidence and the hashes were all verified.

| ID | Finding | Owner | Repair |
|---|---|---|---|
| L1 | `EfsCreateAccessPointOnStackFileSystem` (`permission_sets.tf:326`) allows an untagged access point on a stack-tagged file system. CreateAccessPoint is authorized against the file system only, and omitting tags skips TagResource. | infra-engineer | Require both the request and resource stack tags. Add a negative test. Correct `README.md:92`. |

23. **Carried:** `git diff --check` reports extra blank lines at EOF in `deployer.tftest.hcl:630` and `scripts/phase12d-spike/README.md:48`.

L1 repair (infra-engineer): CreateAccessPoint is now allowed only by `EfsCreateAccessPointOnStackFileSystemWithStackTag` (`permission_sets.tf:328`), which requires the region, the stack ResourceTag and the stack RequestTag. It was removed from `EfsCreateFileSystemWithStackTag`, whose request-tag-only condition had also allowed CreateAccessPoint on a foreign file system. A new test fails on either mutation (deployer 27/27). `sbt check` attempt 7 exit 0, 1267/0. Awaiting re-review.

L1 re-review (human, separate session, 2026-11-04): **APPROVE**. No new findings; L1 is closed. The reviewer replayed deployer 27/27, spike 37/37 and the guard (0 findings). Mutations that remove either tag or the region, or restore the request-only Allow, all fail. Manifests match 75/75 and 3/3; source hashes 45/45 (the tfvars example was left unread).

## Live-found addendum 2 (2026-11-04): boundary launch dependencies (attempt 2 root cause)

CloudTrail showed the EMR service role denied `ec2:RunInstances` on `image/ami-*` by the permissions boundary (`../12d-spike-live/attempt2-validation-failure.md`). The boundary had put `aws:RequestTag` on existing launch dependencies.

- **Repair (infra-engineer, `deployer/permission_sets.tf`):**
  - `V2ExistingLaunchDependencies` (around `:547`) mirrors v2 `ResourcesToLaunchEC2` with a region-only condition.
  - `V2CreateNewWithEmrRequestTag` (around `:528`) is limited to new resources.
  - Launch-template grants are dropped; the observed request used none.
  - `SpikeKeyDescribeViaEc2` is added.
  - `ec2:DisassociateAddress` is added on stack-tagged EIPs (around `:219`).
- **Tests:** deployer 29/29. A new RunInstances request-shape test fails if the AMI statement regains the request tag.
- **Gates:** `sbt check` attempt 8 exit 0, 1267/0.
- **Coordinator note for the reviewer:** attempt 2's DisassociateAddress denial named the resource `arn:aws:ec2:us-east-2:<acct>:*/*`, not an elastic-ip ARN, so the tag-scoped grant may not cover that call. A second destroy pass succeeded once the NAT gateway was gone. The same two-pass destroy is the documented fallback.
- **Status:** reviewed.

Addendum 2 review (human, separate session, 2026-11-04): **APPROVE-WITH-NONBLOCKING**, with no blocking findings.
- The fix widens nothing: launches still need the stack-tagged subnet and security group and tagged new resources. The CreateFleet grant is inert, since no launch-template grant remains.
- The RunInstances audit is complete for the observed request.
- The reviewer ran 10 targeted mutations; all were caught.
- All hashes match (46 source, 76 offline evidence, 4 live evidence), and there are no 12-digit numbers in the live evidence.

Carried items, listed once:

24. The `DisassociateAddress` grant (`permission_sets.tf:219`) probably won't fix the destroy, because the denial named the resource `*/*`. Do not widen the grant to `*`. Keep the two-pass destroy as the documented procedure.
25. A passed spike role can now launch any AMI and instance type, but only into the spike's tagged subnet and security group. This is v2 parity; the cost risk is bounded by the cap and the same-session destroy. Optional tightening: an `ec2:Owner` condition on the AMI.
26. Unverified live: `kms:ResourceAliases` on EC2-initiated CreateGrant, and EMR's later security-group rule calls. Both fail closed. EC2 reports only the first denied resource.
27. The reviewer corrected their own earlier re-review: the claimed request-tag security-group bypass does not exist, because request tags don't apply to existing resources.

## Live-found addendum 3 (2026-11-04): bootstrap Java detection (attempt 3 root cause)

Attempt 3 launched both instances. The bootstrap then exited with code 4: `no java at /usr/lib/jvm/java-17-amazon-corretto/bin/java`. The node's environment showed `JAVA_HOME=/etc/alternatives/jre` and `/usr/lib/jvm/jre-17` (`../12d-spike-live/attempt3-bootstrap-java-path.md`).

- **Repair (infra-engineer):**
  - `scripts/phase12d-spike/emr/bootstrap.sh:134-151` resolves Java 17 at runtime: an explicit `--java-home`, then `jre-17`, the corretto directories, the `/etc/alternatives/jre` target, and the java on `PATH`. A candidate is accepted only if it reports major version 17; otherwise the script exits 4 and lists the candidates tried.
  - The resolved path is written to `/opt/scholarchain-spike/java-home` and used to rewrite the node-local spark-defaults for the AM and executor JAVA_HOME.
  - `run-step.sh` reads that file, and refuses to run without it.
  - Terraform no longer hard-codes JAVA_HOME or passes `--java-home`.
  - Deadline arming is still first.
- **Tests:** bootstrap 21, step scripts 7, all script tests 70 OK. Spike root 37/37, deployer 29/29 (unchanged), guard 0 findings, request bound unchanged.
- **Assumption:** both nodes use the same AMI, so the path resolved on the primary is valid on the core node.
- **Status:** reviewed.

Addendum 3 review (human, separate session, 2026-11-04): **APPROVE-WITH-NONBLOCKING**, with no blocking findings.
- The candidate order matches the EMR layout. The version check accepts 17 and rejects 170. Deadline arming still comes first.
- `run-step` propagation is correct. The same-AMI assumption is reasonable.
- Terraform has no hard-coded JAVA_HOME. Object keys and the request manifest are unchanged.
- No other definite node-path failure was found. The reviewer replayed 70/70 script tests and spike 37/37.

Carried items, listed once:

28. `bootstrap.sh:163`: the resolved path is not validated for the properties format. A newline in an alternatives target could inject spark-defaults lines. The current EMR paths are system-controlled. Reject unsafe characters and add a regression test.
29. `bootstrap.sh:162`: the JAVA_HOME removal does not match leading whitespace or tab separators. The appended values take precedence, and the Terraform output contains neither key. Match every separator, and test that each key occurs exactly once.

## Live-found addendum 4 (2026-11-04): Hadoop codec override (attempt 4 G1 failure)

In attempt 4 the probe passed and G1 failed with `Compression codec com.hadoop.compression.lzo.LzoCodec not found`. EMR's node `io.compression.codecs` lists the LZO codecs, and the portable runtime has no LZO jar. See `../12d-spike-live/attempt4-runtime-proven-g1-codec.md`.

- **Repair (infra-engineer):** `infra/terraform/spikes/emr-spark-isolated/main.tf:60` adds `spark.hadoop.io.compression.codecs` with the Gzip, Default, BZip2 and Snappy codecs. All four classes were verified offline in the runtime's `hadoop-client-api-3.3.4.jar`. The bootstrap rewrite keeps the line, which the extended bootstrap test asserts. A new mock test checks the exact line and that `lzo` appears nowhere; spike 38/38.
- **Coordinator offline scan:** all 1,055 EMR Hadoop properties from the attempt-4 event log were checked against the classes in the runtime jars.
  - 70 class references are missing from the runtime. Nearly all are filesystem implementations for unused schemes (s3, s3a, abfs, gs and others), YARN server-side classes, or the old-API `mapred.output.committer.class = DirectFileOutputCommitter`.
  - G1 uses only `file:///`, and it writes only through DataFrame `.parquet(...)` on the new-API commit protocol. Nothing in `modules/spark` uses `saveAsTextFile` or `saveAsHadoop*`. So no other missing class is expected on G1's path. This is an inference, not a live proof.
- **Gates:** spike 38/38, deployer 29/29, scripts 70 OK, guard 0 findings. `sbt check` attempt 10 was running when the review began.

Addendum 4 review (human, separate session, 2026-11-04): **APPROVE-WITH-NONBLOCKING**, with no blocking findings.
- The codec override is correct: all four classes are in `hadoop-client-api-3.3.4`, and Parquet selects its own codec.
- The bootstrap keeps the line, and the mock test is meaningful.
- The coordinator's inference is reasonable, but stays an inference until G1 completes live.
- Replay: bootstrap tests 21/21; scoped `git diff --check` passed.

30. Carried: the spike README at line 40 wrongly says Hadoop's Snappy codec needs native libhadoop. In Hadoop 3.3.4 it uses `org.xerial.snappy.Snappy`, and the factory instantiates codecs rather than only loading the class. Correct the explanation.

31. Carried (live attempt 5): `scripts/phase12d-spike/collect-evidence.sh` exits 1 on macOS. macOS `tar` would not extract the 28 `._SUCCESS.crc` entries, and `set -e` then stopped the script before it checked each file. The tarball sha256 had already verified, and a Python `tarfile` extraction verified 241/241 files. Use a portable extractor and add a test with `._`-prefixed members.

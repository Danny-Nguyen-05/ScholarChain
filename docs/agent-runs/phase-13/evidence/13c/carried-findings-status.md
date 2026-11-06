# Phase 13 status of the 12D carried findings

The source list is `docs/agent-runs/phase-12/evidence/12d-spike-closeout/carried-findings.md`, which stays unchanged. This file records the Phase 13 status of each item. All results are offline (Terraform mock tests, fake-binary script tests). Nothing was applied and no live behaviour was observed.

| # | Short | Phase 13 status | Subphase / owner | Proving test (and mutation) |
|---|---|---|---|---|
| 1 | `timeout` kills only the client | closed offline | 13B, infra-engineer | YARN kill by run tag on timeout and traps; mutation-checked (see 13B evidence) |
| 2 | ENI delete/modify not region-scoped | closed (already in code at base; now pinned) | 13C, infra-engineer | `deployer.tftest.hcl` `item_2_eni_delete_and_modify_are_scoped_to_the_region_and_account`; region-condition and wildcard-region mutations fail |
| 5 | Service role CreateGrant lacks `kms:GrantIsForAWSResource` | closed | 13C, infra-engineer | spike `item_5_the_service_role_may_create_kms_grants_only_for_aws_resources`; main `main_emr_service_role_create_grant_is_conditioned_on_aws_resources` (phase13c) and `emr_service_role_owns_ebs_key_permissions` (phase12c); condition removed or false fails |
| 6 | Surviving mutations (22/tcp, second key, GetObject, SNS/SQS, gp3) | closed | 13C, test-engineer | `tests/infra/test_spike_hardening.py`; 9 item-6 mutations all caught |
| 7 | Tag test checks `default_tags`, not `tags_all` | closed | 13C, test-engineer | `test_item7_every_taggable_resource_carries_required_tags_in_tags_all` (41 resources); 3 mutations caught |
| 8 | Bootstrap does not sha-check spark-defaults, step scripts, G1 config | closed offline | 13C, infra-engineer | `scripts/tests/test_emr_bootstrap.py` `ShaVerificationTests` |
| 10 | Guard does not inspect conditions | closed | 13C, test-engineer | `tests/infra/terraform_source_guard.py` new category `unconditioned-request-scoped-action`; `test_guard_conditions.py` (old guard fails 9 of 11) |
| 12 | No test that `aws_default_security_group` is absent | closed | 13C, test-engineer | `test_item12_default_security_group_is_absent_from_the_plan` and the static checks; re-adding it fails |
| 14 | KMS `TagResource` on any key | closed (`ForAllValues:StringEquals aws:TagKeys`) | 13C, infra-engineer | deployer `item_14_kms_tag_resource_is_limited_to_the_spike_tag_keys` and two rejection runs; condition removal fails |
| 15 | Stale comment `kms.tf:26-27` | closed (wording) | 13C, infra-engineer | no test (comment) |
| 16 | Spike roles can be given trust policies naming other principals | **mitigated, not fully closeable in IAM** (no condition key on the trust document) | 13C, infra-engineer | `iam:CreateRole` limited to the two spike role ARNs, `UpdateAssumeRolePolicy` denied, trust policies asserted to name only EMR/EC2 service principals: deployer `item_16_*`, spike `item_16_the_spike_roles_trust_only_the_emr_and_ec2_service_principals`, phase13c `main_emr_roles_trust_only_their_service_principals`; 3 mutations fail |
| 17 | Boundary lets a passed role terminate/modify any EMR-tagged instance or ENI | closed offline (live ENI tagging unverified until Phase 14) | 13C, infra-engineer | deployer `item_17_boundary_instance_and_eni_mutations_require_the_stack_tag`; terminate, DeleteTags and launch-template-delete mutations without the stack tag fail |
| 18 | `deployer/README.md:69` overstates guarantees | closed (wording) | 13C, infra-engineer | no test (documentation) |
| 20 | Tag-condition test does not check the value `"true"` | closed | 13C, test-engineer | `test_item20_every_tag_condition_has_the_exact_value`; 3 value mutations caught |
| 21 | Login policy attachment target untested | closed | 13C, test-engineer | `test_item21_login_policy_attaches_to_the_deployer_role` and `test_item21_only_one_role_exists_and_every_attachment_targets_it`; 2 retarget mutations caught |
| 23 | EOF blank lines | closed (infra part; `git diff --check` clean) | 13C, infra-engineer | no test |
| 24 | `DisassociateAddress` grant does not fix destroy | unchanged by design; two-pass destroy stays the procedure | — | — |
| 25 | Any AMI/instance type into the tagged subnet | open (optional tightening) | — | — |
| 28 | Java path not validated for the properties format | closed offline | 13C, infra-engineer | `test_emr_bootstrap.JavaResolutionTests` |
| 29 | `JAVA_HOME` removal misses separators | closed offline | 13C, infra-engineer | `test_emr_bootstrap.JavaHomeSeparatorTests` |
| 30 | Spike README Snappy explanation | closed (wording) | 13C, infra-engineer | no test |
| 31 | `collect-evidence.sh` fails on macOS `tar` | closed | 13B, infra-engineer | before/after tests (see 13B evidence) |

Still open after Phase 13: 24 (by design), 25 (optional), and 16 only as an IAM-level limitation (mitigated as above). Live verification of 17 (ENI tag propagation), the bootstrap on real nodes and the EFS mount is due in Phase 14/15.

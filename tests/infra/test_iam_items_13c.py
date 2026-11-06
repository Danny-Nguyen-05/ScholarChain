"""Independent tests of the Phase 13C IAM hardening (carried 12D findings 2, 5, 14, 16 and 17), hand-derived from the
finding texts in docs/agent-runs/phase-12/evidence/12d-spike-offline/review-findings.md and the Phase 13 plan, not from
the Terraform that was changed. Every property has a scratch-copy MUTATION that must make its named check fail (and the
unmutated copy passes); the repository is never edited.

Item 17  the permissions boundary lets a passed spike role terminate/modify instances, delete ENIs and tags (and delete launch
         templates) only on resources carrying the stack tag as well as the EMR tag.
Item 2   ENI create/delete/modify-attribute are scoped to this region and account.
Item 5   the EMR service role's kms:CreateGrant (spike key policy) requires kms:GrantIsForAWSResource = "true"; the main
         module's project-key grant likewise (static source check).
Item 14  kms:TagResource is limited to the spike's own tag keys with the stack request tag.
Item 16  iam:CreateRole only for the two spike role ARNs; UpdateAssumeRolePolicy denied; the spike roles' trust policies
         name only the EMR and EC2 service principals. IAM has no trust-document condition key, so this is a mitigation.
"""
import json
import unittest

import deployer_checks as d
import hcl_text
import infra_support as s
import spike_checks as c
from infra_support import InfraTestCase, TfTree, record_mutation

PERMISSION_SETS = "permission_sets.tf"
IDENTITY_PHASE12B = s.REPO / "infra/terraform/modules/identity/phase12b.tf"


class Mutations(InfraTestCase):
    """Shared mutation runner for one root."""

    root = None
    module = None

    def run_mutation(self, name, mutate, expect):
        with TfTree(self.root) as tree:
            mutate(tree)
            failing = self.module.failing_plan_checks(tree.plan_json())
            existing = tree.existing_tests()
            record_mutation("%s:%s" % (self.root, name), {
                "root": self.root, "new_plan_checks_failing": sorted(failing), "new_state_checks_failing": [],
                "existing_terraform_test_rc": existing.returncode,
                "existing_terraform_test_summary": (existing.stdout.strip().splitlines() or [""])[-1],
                "caught_by_new_suite": bool(failing), "caught_by_existing_suite": existing.returncode != 0,
            })
        self.assertCaught(failing, expect, name)


class DeployerIamItems(InfraTestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = TfTree("deployer")
        cls.addClassCleanup(cls.tree.close)
        cls.plan = cls.tree.plan_json()

    def test_named_iam_checks_hold_on_the_current_tree(self):
        for name in d.IAM_ITEM_CHECKS:
            with self.subTest(check=name):
                self.assertEqual(d.PLAN_CHECKS[name](self.plan), [], name)

    # ---- item 17 -----------------------------------------------------------------------------------------------

    def test_item17_boundary_terminate_modify_eni_delete_and_delete_tags_require_the_stack_tag(self):
        boundary = d._doc(self.plan, d.BOUNDARY_ADDRESS)
        for action in ("ec2:TerminateInstances", "ec2:ModifyInstanceAttribute", "ec2:DeleteNetworkInterface", "ec2:DeleteTags"):
            statements = [st for st in s.policy_statements(boundary) if st["Effect"] == "Allow" and action in s.as_list(st["Action"])]
            self.assertEqual(len(statements), 1, action)
            equals = statements[0]["Condition"]["StringEquals"]
            self.assertEqual(equals["aws:ResourceTag/scholarchain:stack"], "spike-emr", action)
            self.assertEqual(equals["aws:ResourceTag/for-use-with-amazon-emr-managed-policies"], "true", action)
            self.assertEqual(equals["aws:RequestedRegion"], "us-east-2", action)

    def test_item17_no_launch_template_delete_exists_in_the_boundary(self):
        """The 12D boundary no longer carries launch-template statements; if one returns it must carry the stack tag."""
        boundary = d._doc(self.plan, d.BOUNDARY_ADDRESS)
        self.assertEqual([st["Sid"] for st in s.policy_statements(boundary)
                          if any("LaunchTemplate" in a for a in s.as_list(st["Action"])) and st["Effect"] == "Allow"
                          and not any(a.startswith("ec2:Describe") for a in s.as_list(st["Action"]))], [])

    def test_item17_the_stack_tag_actually_reaches_the_spike_nodes(self):
        """The stack-tag condition only works if the tag is on the nodes: the spike cluster carries it (tags_all) and EMR
        propagates cluster tags to its instances; the spike plan view proves the cluster side."""
        with TfTree("spike") as spike:
            tags_all = s.after(spike.plan_json(), "aws_emr_cluster.spike")["tags_all"]
        self.assertEqual(tags_all["scholarchain:stack"], "spike-emr")
        self.assertEqual(tags_all["for-use-with-amazon-emr-managed-policies"], "true")

    # ---- item 2 -----------------------------------------------------------------------------------------------

    def test_item2_every_eni_statement_is_region_and_account_scoped(self):
        found = 0
        for address, doc in d.policy_documents(self.plan):
            for st in s.policy_statements(doc):
                if st["Effect"] == "Allow" and any(a in s.as_list(st["Action"]) for a in d.ENI_ACTIONS):
                    found += 1
                    for resource in s.as_list(st["Resource"]):
                        self.assertTrue(resource.startswith("arn:aws:ec2:us-east-2:111122223333:"), resource)
                    self.assertEqual(st["Condition"]["StringEquals"]["aws:RequestedRegion"], "us-east-2", st["Sid"])
        self.assertGreaterEqual(found, 2)

    # ---- item 14 -----------------------------------------------------------------------------------------------

    def test_item14_kms_tag_resource_is_limited_to_the_spike_tag_keys(self):
        found = [st for _, doc in d.policy_documents(self.plan) for st in s.policy_statements(doc)
                 if st["Effect"] == "Allow" and "kms:TagResource" in s.as_list(st["Action"])]
        self.assertEqual(len(found), 1)
        st = found[0]
        self.assertEqual(set(st["Condition"]["ForAllValues:StringEquals"]["aws:TagKeys"]), d.SPIKE_KMS_TAG_KEYS)
        self.assertEqual(st["Condition"]["StringEquals"]["aws:RequestTag/scholarchain:stack"], "spike-emr")

    def test_item14_the_spike_key_tags_are_within_the_allowed_tag_keys(self):
        """Cross-root: every tag the spike root puts on its KMS key may be applied by the deployer's kms:TagResource."""
        with TfTree("spike") as spike:
            keys = set(s.after(spike.plan_json(), "aws_kms_key.spike")["tags_all"])
        self.assertLessEqual(keys, d.SPIKE_KMS_TAG_KEYS, "the spike key carries a tag key the deployer may not apply: %s" % sorted(keys - d.SPIKE_KMS_TAG_KEYS))

    # ---- item 16 ----------------------------------------------------------------------------------------------

    def test_item16_create_role_is_limited_to_the_two_spike_roles(self):
        found = [st for _, doc in d.policy_documents(self.plan) for st in s.policy_statements(doc)
                 if st["Effect"] == "Allow" and "iam:CreateRole" in s.as_list(st["Action"])]
        self.assertEqual(len(found), 1)
        self.assertEqual(set(found[0]["Resource"]), d.SPIKE_ROLE_ARNS)
        self.assertEqual(found[0]["Condition"]["StringEquals"]["iam:PermissionsBoundary"], d.BOUNDARY_ARN)
        self.assertEqual(found[0]["Condition"]["StringEquals"]["aws:RequestTag/scholarchain:stack"], "spike-emr")

    def test_item16_update_assume_role_policy_is_denied_on_the_spike_roles(self):
        denies = [st for _, doc in d.policy_documents(self.plan) for st in s.policy_statements(doc)
                  if st["Effect"] == "Deny" and "iam:UpdateAssumeRolePolicy" in s.as_list(st["Action"])]
        self.assertEqual(len(denies), 1)
        self.assertEqual(s.as_list(denies[0]["Resource"]), ["arn:aws:iam::111122223333:role/scholarchain-spike-emr-*"])

    def test_item16_variable_validations_refuse_wider_role_names_and_tag_keys(self):
        bad = (
            ({"spike_role_names": ["scholarchain-spike-emr-service"]}, "one name"),
            ({"spike_role_names": ["scholarchain-spike-emr-service", "scholarchain-spike-emr-*"]}, "wildcard name"),
            ({"spike_role_names": ["scholarchain-spike-emr-service", "other-role"]}, "foreign prefix"),
            ({"spike_role_names": ["scholarchain-spike-emr-service", "scholarchain-spike-emr-service"]}, "duplicate"),
            ({"spike_role_names": ["scholarchain-spike-emr-a", "scholarchain-spike-emr-b", "scholarchain-spike-emr-c"]}, "three names"),
            ({"spike_kms_tag_keys": ["*"]}, "wildcard tag key"),
            ({"spike_kms_tag_keys": ["course", "aws:cloudformation:stack-id", "scholarchain:stack"]}, "aws: prefix"),
            ({"spike_kms_tag_keys": ["course", "owner"]}, "missing the stack tag key"),
            ({"spike_kms_tag_keys": ["scholarchain:stack", "scholarchain:stack"]}, "duplicate tag key"),
        )
        for json_vars, label in bad:
            with self.subTest(case=label):
                done = self.tree.plan_attempt(json_vars=json_vars)
                self.assertNotEqual(done.returncode, 0, "the validation accepted %s" % label)
                self.assertIn("Invalid value for variable", done.stderr + done.stdout)
        good = self.tree.plan_attempt(json_vars={"spike_role_names": ["scholarchain-spike-emr-service", "scholarchain-spike-emr-instance"]})
        self.assertEqual(good.returncode, 0, good.stdout[-800:] + good.stderr[-400:])


class DeployerMutationsIam(Mutations):
    root = "deployer"
    module = d

    def test_item17_boundary_terminate_without_the_stack_tag_is_rejected(self):
        def mutate(t):
            t.replace_after(PERMISSION_SETS, '"V2ManageTaggedInstancesAndEnis"',
                            "merge(local.c_region, local.c_res_emr_tag, local.c_res_stack)", "merge(local.c_region, local.c_res_emr_tag)")
        self.run_mutation("v2_manage_without_stack_tag", mutate, ["item17_boundary_stack_tag"])

    def test_item17_boundary_delete_tags_without_the_stack_tag_is_rejected(self):
        def mutate(t):
            t.replace_after(PERMISSION_SETS, '"V2DeleteTagsOnEmrTaggedResources"',
                            "merge(local.c_region, local.c_res_emr_tag, local.c_res_stack)", "merge(local.c_region, local.c_res_emr_tag)")
        self.run_mutation("delete_tags_without_stack_tag", mutate, ["item17_boundary_stack_tag"])

    def test_item17_boundary_launch_template_delete_with_only_the_emr_tag_is_rejected(self):
        def mutate(t):
            t.replace(PERMISSION_SETS, "# v2 ManageSecurityGroups.", '''Sid      = "MutationLaunchTemplateDelete"
        Effect   = "Allow"
        Action   = ["ec2:DeleteLaunchTemplate"]
        Resource = ["${local.arn_ec2}:launch-template/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_emr_tag) }
      },
      {
        # v2 ManageSecurityGroups.''')
        self.run_mutation("launch_template_delete_emr_tag_only", mutate, ["item17_boundary_stack_tag"])

    def test_item17_boundary_terminate_with_the_emr_tag_value_not_true_is_rejected(self):
        def mutate(t):
            t.regex_sub(PERMISSION_SETS, r'^([ \t]*c_res_emr_tag[ \t]*=.*?)"true"', r'\1"false"')
        self.run_mutation("boundary_emr_tag_false", mutate, ["item17_boundary_stack_tag"])

    def test_item2_eni_statement_without_the_region_condition_is_rejected(self):
        def mutate(t):
            t.strip_attribute_after(PERMISSION_SETS, '"EfsMountTargetNetworkInterfaceUnscopable"', "Condition")
        self.run_mutation("eni_without_region_condition", mutate, ["item2_eni_region_scope"])

    def test_item2_eni_statement_on_a_wildcard_region_arn_is_rejected(self):
        def mutate(t):
            t.replace_after(PERMISSION_SETS, '"EfsMountTargetNetworkInterfaceUnscopable"',
                            '"${local.arn_ec2}:network-interface/*"', '"arn:aws:ec2:*:${local.acct}:network-interface/*"')
        self.run_mutation("eni_wildcard_region_arn", mutate, ["item2_eni_region_scope"])

    def test_item14_kms_tag_resource_without_the_tag_key_restriction_is_rejected(self):
        def mutate(t):
            t.replace_after(PERMISSION_SETS, '"KmsTagOnCreate"', '"ForAllValues:StringEquals" = { "aws:TagKeys" = var.spike_kms_tag_keys }', "")
        self.run_mutation("kms_tag_resource_unrestricted_keys", mutate, ["item14_kms_tag_resource"])

    def test_item14_kms_tag_resource_without_the_stack_request_tag_is_rejected(self):
        def mutate(t):
            t.replace_after(PERMISSION_SETS, '"KmsTagOnCreate"', "merge(local.c_region, local.c_req_stack)", "local.c_region")
        self.run_mutation("kms_tag_resource_no_stack_tag", mutate, ["item14_kms_tag_resource"])

    def test_item14_widened_default_tag_keys_are_rejected(self):
        def mutate(t):
            t.replace("variables.tf", '"Name"]', '"Name", "extra-key"]')
        self.run_mutation("kms_tag_keys_widened", mutate, ["item14_kms_tag_resource"])

    def test_item16_create_role_on_the_whole_prefix_is_rejected(self):
        def mutate(t):
            t.replace_after(PERMISSION_SETS, '"CreateSpikeRolesOnlyWithBoundaryAndTag"', "Resource = local.role_create_arns", "Resource = local.role_arns")
        self.run_mutation("create_role_prefix_wildcard", mutate, ["item16_role_creation_and_trust"])

    def test_item16_create_role_without_the_boundary_condition_is_rejected(self):
        def mutate(t):
            t.replace_after(PERMISSION_SETS, '"CreateSpikeRolesOnlyWithBoundaryAndTag"',
                            'StringEquals = merge(local.c_req_stack, { "iam:PermissionsBoundary" = local.spike_boundary_arn })', "StringEquals = local.c_req_stack")
        self.run_mutation("create_role_without_boundary", mutate, ["item16_role_creation_and_trust"])

    def test_item16_update_assume_role_policy_no_longer_denied_is_rejected(self):
        def mutate(t):
            t.replace(PERMISSION_SETS, ', "iam:UpdateAssumeRolePolicy"]', "]")
        self.run_mutation("update_assume_role_policy_not_denied", mutate, ["item16_role_creation_and_trust"])

    def test_item16_update_assume_role_policy_allowed_is_rejected(self):
        def mutate(t):
            t.replace_after(PERMISSION_SETS, '"AttachAndPutOnBoundedSpikeRolesOnly"', '"iam:DetachRolePolicy"]', '"iam:DetachRolePolicy", "iam:UpdateAssumeRolePolicy"]')
        self.run_mutation("update_assume_role_policy_allowed", mutate, ["item16_role_creation_and_trust"])


class SpikeIamItems(InfraTestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = TfTree("spike")
        cls.addClassCleanup(cls.tree.close)
        cls.plan = cls.tree.plan_json()

    def test_item5_named_checks_hold_on_the_current_tree(self):
        for name in ("item5_service_role_create_grant", "item16_trust_service_principals_only"):
            with self.subTest(check=name):
                self.assertEqual(c.PLAN_CHECKS[name](self.plan), [], name)

    def test_item5_service_role_create_grant_requires_grant_is_for_aws_resource(self):
        policy = json.loads(s.after(self.plan, "aws_kms_key.spike")["policy"])
        grants = [st for st in policy["Statement"] if "kms:CreateGrant" in s.as_list(st["Action"])
                  and st["Principal"]["AWS"] == "arn:aws:iam::111122223333:role/scholarchain-spike-emr-service"]
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["Action"], ["kms:CreateGrant"])
        self.assertEqual(grants[0]["Condition"], {"Bool": {"kms:GrantIsForAWSResource": "true"}})
        self.assertEqual(len(policy["Statement"]), 6)

    def test_item16_spike_trust_policies_name_only_the_emr_and_ec2_service_principals(self):
        service = json.loads(s.after(self.plan, "aws_iam_role.service")["assume_role_policy"])["Statement"][0]
        instance = json.loads(s.after(self.plan, "aws_iam_role.instance")["assume_role_policy"])["Statement"][0]
        self.assertEqual(service["Principal"], {"Service": "elasticmapreduce.amazonaws.com"})
        self.assertEqual(instance["Principal"], {"Service": "ec2.amazonaws.com"})
        self.assertEqual(service["Action"], "sts:AssumeRole")
        self.assertEqual(instance["Action"], "sts:AssumeRole")


class SpikeMutationsIam(Mutations):
    root = "spike"
    module = c

    def test_item5_service_role_create_grant_without_the_condition_is_rejected(self):
        def mutate(t):
            t.strip_attribute_after("kms.tf", '"EmrServiceRoleCreateGrantForAwsResourcesOnly"', "Condition")
        self.run_mutation("create_grant_without_condition", mutate, ["item5_service_role_create_grant"])

    def test_item5_condition_value_false_is_rejected(self):
        def mutate(t):
            t.replace_after("kms.tf", '"EmrServiceRoleCreateGrantForAwsResourcesOnly"', '"kms:GrantIsForAWSResource" = "true"', '"kms:GrantIsForAWSResource" = "false"')
        self.run_mutation("create_grant_condition_false", mutate, ["item5_service_role_create_grant"])

    def test_item5_create_grant_moved_back_into_the_unconditioned_statement_is_rejected(self):
        def mutate(t):
            t.replace_after("kms.tf", '"EmrServiceRoleEbsEncryption"', '"kms:ListGrants"', '"kms:CreateGrant", "kms:ListGrants"')
        self.run_mutation("create_grant_unconditioned", mutate, ["item5_service_role_create_grant"])

    def test_item5_instance_role_create_grant_is_rejected(self):
        def mutate(t):
            t.replace_after("kms.tf", '"InstanceProfileDataKeyUse"', '"kms:DescribeKey"', '"kms:DescribeKey", "kms:CreateGrant"')
        self.run_mutation("instance_role_create_grant", mutate, ["item5_service_role_create_grant"])

    def test_item16_instance_trust_naming_another_principal_is_rejected(self):
        def mutate(t):
            t.replace("iam.tf", 'Principal = { Service = "ec2.amazonaws.com" }', 'Principal = { AWS = "arn:aws:iam::111122223333:root" }')
        self.run_mutation("instance_trust_account_principal", mutate, ["item16_trust_service_principals_only"])

    def test_item16_service_trust_with_an_extra_service_principal_is_rejected(self):
        def mutate(t):
            t.replace("iam.tf", 'Principal = { Service = "elasticmapreduce.amazonaws.com" }',
                      'Principal = { Service = ["elasticmapreduce.amazonaws.com", "lambda.amazonaws.com"] }')
        self.run_mutation("service_trust_extra_service", mutate, ["item16_trust_service_principals_only"])


class MainModuleItem5Static(unittest.TestCase):
    """Item 5, main module side (N9): the EMR service role's CreateGrant on the project CMK carries
    kms:GrantIsForAWSResource = "true". The main root is too large to plan offline here, so this is a source-text check."""

    @staticmethod
    def problems(text):
        statement = hcl_text.smallest_object_containing(text, 'Action = ["kms:CreateGrant"]')
        if statement is None:
            return ["no statement with Action = [kms:CreateGrant] found"]
        flat = " ".join(statement.split())
        found = []
        if 'Effect = "Allow"' not in flat:
            found.append("the CreateGrant statement is not an Allow")
        if '"kms:GrantIsForAWSResource" = "true"' not in flat or "Bool" not in flat:
            found.append("the CreateGrant statement lacks Bool kms:GrantIsForAWSResource = \"true\"")
        if flat.count("kms:CreateGrant") != 1:
            found.append("kms:CreateGrant appears %d times in the statement" % flat.count("kms:CreateGrant"))
        return found

    def test_the_main_service_role_grant_requires_grant_is_for_aws_resource(self):
        self.assertEqual(self.problems(IDENTITY_PHASE12B.read_text()), [])

    def test_mutations_without_the_condition_or_with_value_false_are_rejected(self):
        text = IDENTITY_PHASE12B.read_text()
        # the statement is a single-line object, so strip the condition textually
        needle = ', Condition = { Bool = { "kms:GrantIsForAWSResource" = "true" } }'
        self.assertIn(needle, text, "mutation anchor moved: update the mutation")
        self.assertTrue(self.problems(text.replace(needle, "", 1)))
        self.assertTrue(self.problems(text.replace('"kms:GrantIsForAWSResource" = "true"', '"kms:GrantIsForAWSResource" = "false"', 1)))


if __name__ == "__main__":
    unittest.main()

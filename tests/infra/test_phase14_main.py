"""Phase 14A independent checks of decision 14-6 (the `phase14-main` deployer set) and the mid-subphase decisions D1 and D2.

Real-tree cases plan the deployer root with its DEFAULT permission set and the MAIN root, both offline (real AWS provider,
fake static credentials, closed proxy; no AWS call is possible) and assert hand-derived expectations from
phase14_checks.py. Mutation cases edit only a SCRATCH COPY (a temporary directory outside the repository) and require the
SPECIFIC named check to fire; every mutation result is appended to $SC_INFRA_EVIDENCE_FILE when that is set.

The spike-era suites keep planning the deployer with enabled_permission_sets = ["spike-emr"] (infra_support.ROOTS["deployer"]).
This module uses ROOTS["deployer14"], which sets nothing, so the root's default (phase14-main) is what is tested.
"""
import json
import copy
import re
import unittest

import infra_support as s
import phase14_checks as c
from infra_support import InfraTestCase, MutationAnchorMissing, TfTree, record_mutation

PHASE14 = "phase14_main.tf"
BOTH = ["spike-emr", "phase14-main"]

_CACHE = {}


def with_vars(kind, **extra):
    """A scratch tree whose plan variables are the root's synthetic defaults plus `extra` (the shared ROOTS dict is not changed)."""
    tree = TfTree(kind)
    tree.spec = dict(tree.spec, vars=dict(tree.spec["vars"], **extra))
    return tree


def real_plan(kind, **extra):
    key = (kind, tuple(sorted(extra.items())))
    if key not in _CACHE:
        with with_vars(kind, **extra) as tree:
            _CACHE[key] = tree.plan_json()
    return _CACHE[key]


def flat(text):
    """Terraform wraps error messages in a box; collapse the frame and whitespace so a phrase can be searched."""
    return " ".join(text.replace("│", " ").split())


# ---------------------------------------------------------------------------------------------------------------
# real tree
# ---------------------------------------------------------------------------------------------------------------

class Phase14MainRealTree(InfraTestCase):
    @classmethod
    def setUpClass(cls):
        cls.deployer = real_plan("deployer14")
        cls.main = real_plan("main14")

    def test_every_named_deployer_check_holds(self):
        failing = c.failing_deployer_checks(self.deployer)
        for name in c.DEPLOYER_CHECKS:
            with self.subTest(check=name):
                self.assertEqual(failing.get(name, []), [], name)

    def test_every_named_main_root_check_holds(self):
        self.assertEqual(c.failing_main_checks(self.main, self.deployer), {})

    # ---- selection ---------------------------------------------------------------------------------------------

    def test_default_set_is_phase14_main_and_nothing_else(self):
        docs = c.permission_set_documents(self.deployer)
        self.assertEqual(sorted(a.split('"')[1] for a in docs), sorted("phase14-main--" + p for p in
                         ("network", "network-mod", "data", "keys-obs", "compute", "emr-efs", "iam")))
        names = {a: n for a, (n, _) in c.policy_resources(self.deployer).items()}
        self.assertFalse([a for a in names if "spike" in a], names)

    def test_spike_emr_is_not_attached(self):
        attachments = [a for a in s.managed_changes(self.deployer) if a.startswith("aws_iam_role_policy_attachment.")]
        self.assertEqual(len(attachments), 7)
        self.assertFalse([a for a in attachments if "spike" in a])
        self.assertNotIn("aws_iam_policy.spike_boundary[0]", s.managed_changes(self.deployer))

    def test_spike_emr_and_phase14_main_cannot_be_combined(self):
        with TfTree("deployer14") as tree:
            done = tree.plan_attempt(json_vars={"enabled_permission_sets": BOTH})
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("must not be enabled together", flat(done.stdout + done.stderr))

    def test_an_unknown_permission_set_is_refused(self):
        with TfTree("deployer14") as tree:
            done = tree.plan_attempt(json_vars={"enabled_permission_sets": ["phase14-main", "no-such-set"]})
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("Unknown permission set", flat(done.stdout + done.stderr))

    # ---- sizes and quota ---------------------------------------------------------------------------------------

    def test_every_policy_is_under_6144_characters_as_minified_json(self):
        docs = c.policy_resources(self.deployer)
        self.assertEqual(len(docs), 9)
        for address, (_, doc) in docs.items():
            with self.subTest(policy=address):
                self.assertLessEqual(len(json.dumps(doc, separators=(",", ":"))), 6144)

    def test_documents_stay_under_the_limit_with_the_longest_allowed_environment_name(self):
        longest = "abcdefghij"  # the main root allows 2..10 characters
        plan = real_plan("deployer14", main_environment=longest)
        self.assertEqual(c.check_document_sizes(plan), [])
        self.assertEqual(c.check_iam_scope(plan, env=longest), [])

    def test_the_role_has_at_most_ten_managed_attachments(self):
        self.assertEqual(c.check_attachment_count(self.deployer), [])

    # ---- region ------------------------------------------------------------------------------------------------

    def test_regional_allow_statements_carry_the_region_and_only_iam_and_route53_are_exempt(self):
        self.assertEqual(c.check_region_condition(self.deployer), [])
        self.assertEqual(c.check_region_exemption_is_only_iam_and_route53(self.deployer), [])
        unconditioned = {sv for _, st in c.statements(c.permission_set_documents(self.deployer), "Allow")
                         if c.as_list(c.pairs_of(st).get(("StringEquals", "aws:RequestedRegion"))) != [c.REGION]
                         for sv in c.services_of(st)}
        self.assertEqual(unconditioned, {"iam", "route53"})

    # ---- IAM ---------------------------------------------------------------------------------------------------

    def test_iam_resources_are_the_main_prefix_and_never_the_deployer_or_billing_roles(self):
        self.assertEqual(c.check_iam_scope(self.deployer), [])

    def test_create_role_requires_one_of_the_two_boundaries(self):
        self.assertEqual(c.check_create_role_requires_boundary(self.deployer), [])

    def test_boundary_tampering_and_secret_reads_are_denied(self):
        self.assertEqual(c.check_deny_statements(self.deployer), [])

    def test_pass_role_always_names_the_service(self):
        self.assertEqual(c.check_pass_role_names_the_service(self.deployer), [])

    def test_no_wildcard_actions_in_the_documents_or_the_boundaries(self):
        self.assertEqual(c.check_no_wildcard_actions(self.deployer), [])

    def test_trust_requires_mfa_and_sessions_last_one_hour(self):
        self.assertEqual(c.check_trust_and_session(self.deployer), [])

    # ---- the main root -----------------------------------------------------------------------------------------

    def test_the_hand_derived_role_list_is_exactly_what_the_main_root_plans(self):
        self.assertEqual(set(c.main_roles(self.main)), c.expected_main_role_names("course"))
        self.assertEqual(len(c.main_roles(self.main)), 13)

    def test_all_seven_role_blocks_carry_a_boundary_equal_to_the_deployer_roots(self):
        self.assertEqual(c.check_main_roles_carry_the_deployer_boundaries(self.main, self.deployer), [])
        runtime, emr = c.boundary_arns(self.deployer)
        roles = c.main_roles(self.main)
        self.assertEqual(roles["scholarchain-course-emr-service"], emr)
        self.assertEqual({b for n, b in roles.items() if n != "scholarchain-course-emr-service"}, {runtime})

    def test_the_deployer_may_create_every_main_role_and_only_with_the_boundary_it_carries(self):
        self.assertEqual(c.check_create_role_covers_main_roles(self.deployer, c.main_roles(self.main)), [])

    def test_boundary_naming_follows_a_changed_environment_in_both_roots(self):
        deployer = real_plan("deployer14", main_environment="demo")
        main = real_plan("main14", environment="demo")
        self.assertEqual(c.failing_deployer_checks(deployer, env="demo"), {})
        self.assertEqual(c.check_main_roles_carry_the_deployer_boundaries(main, deployer, env="demo"), [])
        self.assertEqual(c.check_create_role_covers_main_roles(deployer, c.main_roles(main)), [])
        self.assertTrue(all("scholarchain-demo-" in b for b in c.main_roles(main).values()))
        # A main root and a deployer root planned for different environments must NOT line up.
        self.assertNotEqual(c.check_main_roles_carry_the_deployer_boundaries(main, self.deployer, env="demo"), [])

    def test_emr_managed_policy_tag_is_on_exactly_the_application_subnets_and_the_two_emr_groups(self):
        self.assertEqual(c.check_emr_managed_policy_tag(self.main), [])
        tagged = sorted(a for a, rc in s.managed_changes(self.main).items()
                        if rc["type"] in ("aws_subnet", "aws_security_group")
                        and rc["change"]["after"].get("tags_all", {}).get(c.EMR_TAG) == "true")
        self.assertEqual(tagged, [
            'module.network.aws_security_group.emr_service_access',
            'module.network.aws_security_group.role["emr"]',
            'module.network.aws_subnet.application["0"]',
            'module.network.aws_subnet.application["1"]'])


# ---------------------------------------------------------------------------------------------------------------
# mutations (scratch copies only)
# ---------------------------------------------------------------------------------------------------------------

def ra(anchor, old, new, file=PHASE14):
    return lambda t: t.replace_after(file, anchor, old, new)


def rp(old, new, file=PHASE14, count=1):
    return lambda t: t.replace(file, old, new, count)


def doc_size(part):
    """Minified-JSON size of the current real policy whose resource address contains `part` (planned once, cached)."""
    plan = real_plan("deployer14")
    sizes = [len(json.dumps(doc, separators=(",", ":"))) for address, (_, doc) in c.policy_resources(plan).items() if part in address]
    assert len(sizes) == 1, (part, sizes)
    return sizes[0]


def over_the_limit(part, anchor, file):
    """Edit that replaces a Sid by a pad so that the document `part` ends up well over 6,144 characters, whatever its
    current size (the pad is computed from the real plan, so a document that shrinks or grows cannot make this a no-op)."""
    def edit(tree):
        pad = c.SIZE_LIMIT - doc_size(part) + len(anchor) + 500
        tree.replace_after(file, anchor, anchor, '"%s"' % ("A" * pad))
    return edit


def largest_document_part():
    plan = real_plan("deployer14")
    sizes = {a: len(json.dumps(doc, separators=(",", ":"))) for a, (_, doc) in c.permission_set_documents(plan).items()}
    return max(sizes, key=sizes.get)


DENY_BOUNDARY = '"DenyBoundaryPolicyMutation"'
DENY_REMOVAL = '"DenyBoundaryRemovalAndTrustChangeOnMainRoles"'
DENY_VALUES = '"DenyReadingSecretValues"'
QUOTA = "length(local.selected_policies) <= 10"
ADDED_PARTS = ("iam         = local.m14_iam\n      x1 = local.m14_network\n      x2 = local.m14_data\n"
               "      x3 = local.m14_compute\n      x4 = local.m14_emr_efs")

# name -> (edits, checks that must fire). The deployer root is planned with its default (phase14-main) set.
DEPLOYER_MUTATIONS = {
    # selection and quota
    "spike_policies_attached_beside_phase14_main": (
        [rp("for s in var.enabled_permission_sets : {", 'for s in concat(tolist(var.enabled_permission_sets), ["spike-emr"]) : {', "main.tf"),
         rp(QUOTA, "length(local.selected_policies) <= 30", "main.tf")], ["spike_absent"]),
    "smallest_document_over_6144_characters": (
        [over_the_limit('phase14-main--network-mod', '"Ec2ModifyDeleteProjectTaggedOnly"', PHASE14)], ["document_sizes"]),
    "runtime_boundary_over_6144_characters": (
        [over_the_limit("main_boundary_runtime", '"DynamoDbItemsOfTheMainStack"', "boundaries/runtime.json.tftpl")], ["document_sizes"]),
    "eleven_managed_attachments": (
        [ra('"phase14-main" = {', "iam         = local.m14_iam", ADDED_PARTS, "permission_sets.tf"),
         rp(QUOTA, "length(local.selected_policies) <= 30", "main.tf")], ["attachment_count"]),
    # region
    "region_condition_removed_from_sqs": ([ra('"SqsQueues"', "Condition = { StringEquals = local.c_region }", "")], ["region_condition"]),
    "region_condition_names_us_east_1": (
        [ra('"S3VectorsBucketAndIndexes"', "Condition = { StringEquals = local.c_region }", 'Condition = { StringEquals = { "aws:RequestedRegion" = "us-east-1" } }')],
        ["region_condition"]),
    "tag_service_statement_loses_the_region_condition": (
        [ra('"TagInventoryNoResourceType"', "Condition = { StringEquals = local.c_region }", "")], ["region_condition", "region_exemption_only_iam_route53"]),
    # iam scope
    "role_arns_widened_to_scholarchain_star": (
        [rp('m_role_arns  = ["${local.arn_iam}:role/${local.mp}-*"]', 'm_role_arns  = ["${local.arn_iam}:role/scholarchain-*"]')], ["iam_scope"]),
    "billing_deployer_role_added_to_read_update_delete": (
        [ra('"ReadUpdateDeleteMainRoles"', "Resource = local.m_role_arns",
            'Resource = concat(local.m_role_arns, ["${local.arn_iam}:role/scholarchain-billing-deployer"])')], ["iam_scope"]),
    "instance_profile_resource_becomes_star": (
        [ra('"ManageMainInstanceProfile"', '["${local.arn_iam}:instance-profile/${local.mp}-*"]', '["*"]')], ["iam_scope"]),
    "attach_role_policy_allowed": (
        [ra('"ReadUpdateDeleteMainRoles"', '"iam:GetRole",', '"iam:GetRole", "iam:AttachRolePolicy",')], ["iam_scope"]),
    # create role needs a boundary
    "create_role_boundary_condition_dropped": (
        [ra('"CreateRuntimeRolesOnlyWithRuntimeBoundary"', 'merge(local.c_req_main, { "iam:PermissionsBoundary" = local.m_boundary_runtime_arn })', "local.c_req_main")],
        ["create_role_requires_boundary", "create_role_covers_main_roles"]),
    "emr_service_role_created_with_the_runtime_boundary": (
        [ra('"CreateEmrServiceRoleOnlyWithEmrBoundary"', "local.m_boundary_emr_arn", "local.m_boundary_runtime_arn")],
        ["create_role_requires_boundary", "create_role_covers_main_roles"]),
    "runtime_roles_may_use_either_boundary": (
        [ra('"CreateRuntimeRolesOnlyWithRuntimeBoundary"', '"iam:PermissionsBoundary" = local.m_boundary_runtime_arn', '"iam:PermissionsBoundary" = local.m_boundary_arns')],
        ["create_role_requires_boundary"]),
    "put_role_policy_no_longer_requires_a_boundary": (
        [ra('"RolePoliciesOnBoundedMainRolesOnly"', '{ "iam:PermissionsBoundary" = local.m_boundary_arns }', '{ "aws:RequestedRegion" = "us-east-2" }')],
        ["create_role_requires_boundary"]),
    "embedding_producer_dropped_from_create_role": (
        [ra('"CreateRuntimeRolesOnlyWithRuntimeBoundary"', '"embedding-producer", ', "")], ["create_role_covers_main_roles"]),
    # explicit denies
    "deny_set_default_policy_version_removed": ([ra(DENY_BOUNDARY, '"iam:SetDefaultPolicyVersion", ', "")], ["deny_statements"]),
    "deny_create_policy_version_removed": ([ra(DENY_BOUNDARY, '"iam:CreatePolicyVersion", ', "")], ["deny_statements"]),
    "deny_delete_policy_removed": ([ra(DENY_BOUNDARY, '"iam:DeletePolicy", ', "")], ["deny_statements"]),
    "deny_boundary_policy_covers_only_the_runtime_boundary": (
        [ra(DENY_BOUNDARY, "Resource = local.m_boundary_arns", "Resource = [local.m_boundary_runtime_arn]")], ["deny_statements"]),
    "deny_delete_role_permissions_boundary_removed": ([ra(DENY_REMOVAL, '"iam:DeleteRolePermissionsBoundary", ', "")], ["deny_statements"]),
    "deny_put_role_permissions_boundary_removed": ([ra(DENY_REMOVAL, '"iam:PutRolePermissionsBoundary", ', "")], ["deny_statements"]),
    "boundary_removal_deny_turned_into_allow": ([ra(DENY_REMOVAL, 'Effect   = "Deny"', 'Effect   = "Allow"')], ["deny_statements", "iam_scope"]),
    "deny_get_secret_value_removed": ([ra(DENY_VALUES, '"secretsmanager:GetSecretValue", ', "")], ["deny_statements"]),
    "deny_secret_reads_narrowed_to_one_prefix": (
        [ra(DENY_VALUES, 'Resource = ["*"]', 'Resource = ["${local.m_arn_secret}:secret:${local.mp}-*"]')], ["deny_statements"]),
    "deny_secret_reads_gets_a_condition": (
        [ra(DENY_VALUES, 'Resource = ["*"]', 'Resource = ["*"]\n        Condition = { StringEquals = local.c_region }')], ["deny_statements"]),
    # pass role
    "pass_role_to_neptune_loses_the_service_condition": (
        [ra('"PassRoleToNeptune"', '{ "iam:PassedToService" = ["rds.amazonaws.com"] }', '{ "aws:RequestedRegion" = "us-east-2" }')], ["pass_role_names_the_service"]),
    "pass_role_to_emr_on_any_resource": (
        [ra('"PassRoleToEmr"', '["${local.arn_iam}:role/${local.mp}-emr-service"]', '["*"]')], ["pass_role_names_the_service", "iam_scope"]),
    # wildcards
    "s3_service_wildcard_added": ([rp('"s3:CreateBucket"', '"s3:*"')], ["no_wildcard_actions"]),
    "star_action_added": ([ra('"TagInventoryNoResourceType"', 'Action    = ["tag:GetResources"]', 'Action    = ["*"]')], ["no_wildcard_actions"]),
    "star_colon_star_action_added": ([ra('"KmsCreateKeyWithProjectTags"', 'Action    = ["kms:CreateKey"]', 'Action    = ["*:*"]')], ["no_wildcard_actions"]),
    "service_wildcard_in_the_runtime_boundary": ([rp('"dynamodb:GetItem",', '"ec2:*",\n        "dynamodb:GetItem",', "boundaries/runtime.json.tftpl")], ["no_wildcard_actions"]),
    "not_action_allow_added": ([ra('"KmsListAliasesNoResourceType"', 'Action    = ["kms:ListAliases"]', 'NotAction = ["kms:ListAliases"]')], ["no_wildcard_actions"]),
    # trust and session
    "trust_loses_the_mfa_condition": ([rp('      Condition = { Bool = { "aws:MultiFactorAuthPresent" = "true" } }\n', "", "main.tf")], ["trust_and_session"]),
    "trust_mfa_value_false": ([rp('"aws:MultiFactorAuthPresent" = "true"', '"aws:MultiFactorAuthPresent" = "false"', "main.tf")], ["trust_and_session"]),
    "trust_principal_is_any_aws_principal": ([rp("Principal = { AWS = var.operator_principal_arn }", 'Principal = { AWS = "*" }', "main.tf")], ["trust_and_session"]),
    "session_duration_twelve_hours": ([rp("max_session_duration = 3600", "max_session_duration = 43200", "main.tf")], ["trust_and_session"]),
}

EMR_TAG_ENTRY = '"for-use-with-amazon-emr-managed-policies" = "true"'
NET = "modules/network/main.tf"
MAIN_MUTATIONS = {
    "producer_role_boundary_removed": (
        [lambda t: t.regex_sub("modules/workflow/main.tf", r"^[ \t]*permissions_boundary = .*\n", "")], ["main_roles_boundaries"]),
    "emr_service_role_gets_the_runtime_boundary": (
        [lambda t: t.replace_after("modules/identity/main.tf", 'resource "aws_iam_role" "emr_service"', "local.boundary_arn.emr_service", "local.boundary_arn.runtime")],
        ["main_roles_boundaries"]),
    "deployment_role_gets_the_emr_service_boundary": (
        [lambda t: t.replace_after("modules/identity/main.tf", 'resource "aws_iam_role" "deployment"', "local.boundary_arn.runtime", "local.boundary_arn.emr_service")],
        ["main_roles_boundaries"]),
    "task_roles_boundary_removed": (
        [lambda t: t.replace_after("modules/identity/main.tf", 'resource "aws_iam_role" "task"', "permissions_boundary = local.boundary_arn.runtime", "")],
        ["main_roles_boundaries"]),
    "runtime_boundary_renamed_in_the_identity_module": (
        [lambda t: t.replace("modules/identity/main.tf", "${var.name_prefix}-permissions-boundary", "${var.name_prefix}-runtime-boundary")],
        ["main_roles_boundaries", "create_role_covers_main_roles"]),
    "a_new_role_without_a_boundary_is_added": (
        [lambda t: t.add_file("modules/workflow/zz_rogue_role.tf",
                              'resource "aws_iam_role" "rogue" {\n  name               = "${var.name_prefix}-rogue"\n  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [] })\n}\n')],
        ["main_roles_boundaries"]),
    # D2
    "application_subnets_lose_the_emr_tag": (
        [lambda t: t.replace_after(NET, 'resource "aws_subnet" "application"', ", " + EMR_TAG_ENTRY, "")], ["emr_managed_policy_tag"]),
    "application_subnets_tag_value_false": (
        [lambda t: t.replace_after(NET, 'resource "aws_subnet" "application"', EMR_TAG_ENTRY, EMR_TAG_ENTRY.replace('"true"', '"false"'))], ["emr_managed_policy_tag"]),
    "public_subnets_gain_the_emr_tag": (
        [lambda t: t.replace_after(NET, 'resource "aws_subnet" "public"', 'tier = "public" }', 'tier = "public", ' + EMR_TAG_ENTRY + " }")], ["emr_managed_policy_tag"]),
    "data_subnets_gain_the_emr_tag": (
        [lambda t: t.replace_after(NET, 'resource "aws_subnet" "data"', 'tier = "data" }', 'tier = "data", ' + EMR_TAG_ENTRY + " }")], ["emr_managed_policy_tag"]),
    "emr_node_group_loses_the_emr_tag": (
        [lambda t: t.replace_after(NET, 'resource "aws_security_group" "role"', 'each.key == "emr" ? { %s } : {}' % EMR_TAG_ENTRY, "{}")], ["emr_managed_policy_tag"]),
    "every_role_security_group_gains_the_emr_tag": (
        [lambda t: t.replace_after(NET, 'resource "aws_security_group" "role"', 'each.key == "emr" ? { %s } : {}' % EMR_TAG_ENTRY, "{ %s }" % EMR_TAG_ENTRY)],
        ["emr_managed_policy_tag"]),
    "emr_service_access_group_loses_the_emr_tag": (
        [lambda t: t.replace_after(NET, 'resource "aws_security_group" "emr_service_access"', ", { %s }" % EMR_TAG_ENTRY, "")], ["emr_managed_policy_tag"]),
    "default_security_group_is_managed_again": (
        [lambda t: t.add_file("modules/network/zz_default_sg.tf",
                              'resource "aws_default_security_group" "closed" {\n  vpc_id = aws_vpc.course.id\n}\n')],
        ["no_default_security_group"]),
}


class MutationBase(InfraTestCase):
    kind = None

    def run_mutation(self, name, edits, expected):
        with TfTree(self.kind) as tree:
            for edit in edits:
                edit(tree)
            plan = tree.plan_json()
            failing = self.failing(plan)
        record_mutation("phase14:%s:%s" % (self.kind, name), {
            "root": self.kind, "expected_checks": sorted(expected), "fired_checks": sorted(failing),
            "caught": all(e in failing for e in expected),
            "first_problem": {k: v[0] for k, v in sorted(failing.items())}})
        self.assertCaught(failing, expected, name)


class DeployerMutations(MutationBase):
    kind = "deployer14"

    @classmethod
    def setUpClass(cls):
        cls.main_roles = c.main_roles(real_plan("main14"))

    def failing(self, plan):
        failing = c.failing_deployer_checks(plan)
        cross = c.check_create_role_covers_main_roles(plan, self.main_roles)
        if cross:
            failing["create_role_covers_main_roles"] = cross
        return failing

    def test_the_unmutated_copy_passes_every_check(self):
        with TfTree(self.kind) as tree:
            self.assertEqual(self.failing(tree.plan_json()), {})

    def test_a_mutation_whose_anchor_is_missing_is_an_error_not_a_pass(self):
        with TfTree(self.kind) as tree:
            with self.assertRaises(MutationAnchorMissing):
                ra('"SqsQueues"', "this text is not in the file", "x")(tree)

    def test_removing_the_combination_refusal_is_caught(self):
        """Selecting spike-emr with phase14-main must be refused BY the dedicated rule (not only by the attachment quota)."""
        with TfTree(self.kind) as tree:
            rp('condition     = !(contains(var.enabled_permission_sets, "spike-emr") && contains(var.enabled_permission_sets, "phase14-main"))',
               "condition     = length(var.enabled_permission_sets) >= 0", "main.tf")(tree)
            done = tree.plan_attempt(json_vars={"enabled_permission_sets": BOTH})
        said = "must not be enabled together" in flat(done.stdout + done.stderr)
        record_mutation("phase14:deployer14:combination_refusal_removed", {
            "root": "deployer14", "expected_checks": ["combination_refused"], "fired_checks": [] if said else ["combination_refused"],
            "caught": not said, "plan_returncode": done.returncode})
        self.assertFalse(said, "the dedicated refusal still fired after its condition was removed")


class MainRootMutations(MutationBase):
    kind = "main14"

    @classmethod
    def setUpClass(cls):
        cls.deployer = real_plan("deployer14")

    def failing(self, plan):
        return c.failing_main_checks(plan, self.deployer)


class Phase14F2InMemory(InfraTestCase):
    """Repair round 1, finding F2 (tag adoption). The real plan must satisfy the F2 checks, and each check must fire on an
    in-memory edit of a COPY of that plan (no Terraform run, nothing on disk): a statement is added or weakened in the parsed
    policy JSON of one planned managed policy. Every case records its result to $SC_INFRA_EVIDENCE_FILE."""

    @classmethod
    def setUpClass(cls):
        cls.deployer = real_plan("deployer14")
        cls.main = real_plan("main14")

    # ---- helpers -----------------------------------------------------------------------------------------------

    def mutated(self, part, edit):
        """A deep copy of the deployer plan in which the policy whose address contains `part` was edited by edit(document)."""
        plan = copy.deepcopy(self.deployer)
        hits = 0
        for rc in plan["resource_changes"]:
            if rc["type"] == "aws_iam_policy" and part in rc["address"]:
                doc = json.loads(rc["change"]["after"]["policy"])
                edit(doc)
                rc["change"]["after"]["policy"] = json.dumps(doc)
                hits += 1
        self.assertEqual(hits, 1, part)
        return plan

    @staticmethod
    def statement(doc, sid):
        found = [st for st in doc["Statement"] if st.get("Sid") == sid]
        assert len(found) == 1, sid
        return found[0]

    def assertFires(self, name, check, plan, **kwargs):
        problems = check(plan, **kwargs)
        record_mutation("phase14:in-memory:" + name, {
            "root": "in-memory", "expected_checks": [check.__name__], "fired_checks": [check.__name__] if problems else [],
            "caught": bool(problems), "first_problem": {check.__name__: problems[0] if problems else None}})
        self.assertTrue(problems, "mutation %r was NOT caught by %s" % (name, check.__name__))

    def add_statement(self, part, **statement):
        return self.mutated(part, lambda doc: doc["Statement"].append(dict({"Effect": "Allow"}, **statement)))

    KEY = "arn:aws:kms:us-east-2:111122223333:key/*"
    SG = "arn:aws:ec2:us-east-2:111122223333:security-group/*"
    REGION = {"StringEquals": {"aws:RequestedRegion": "us-east-2"}}
    REQ = {"StringEquals": {"aws:RequestedRegion": "us-east-2", "aws:RequestTag/project": "scholarchain", "aws:RequestTag/environment": "course"}}

    # ---- the real plan holds ------------------------------------------------------------------------------------

    def test_real_plan_has_no_kms_administration_use_or_grants_in_iam(self):
        self.assertEqual(c.check_no_kms_administration_use_or_grants_in_iam(self.deployer), [])
        kms = {a for _, st in c.statements(c.permission_set_documents(self.deployer), "Allow")
               for a in c.as_list(st["Action"]) if a.startswith("kms:")}
        # Hand-derived: only create-time helpers and alias and list actions of the main stack remain in IAM.
        self.assertEqual(kms, {"kms:CreateKey", "kms:TagResource", "kms:CreateAlias", "kms:UpdateAlias", "kms:DeleteAlias", "kms:ListAliases"})

    def test_real_plan_security_group_mutations_need_the_project_resource_tag(self):
        self.assertEqual(c.check_security_group_mutations_need_the_project_resource_tag(self.deployer), [])

    def test_real_plan_tagging_cannot_adopt_a_foreign_security_group(self):
        self.assertEqual(c.check_security_group_tagging_cannot_adopt(self.deployer), [])

    def test_real_main_plan_has_no_default_security_group(self):
        self.assertEqual(c.check_no_default_security_group(self.main), [])
        self.assertFalse([a for a, rc in s.managed_changes(self.main).items() if rc["type"] == "aws_default_security_group"])

    def test_the_adoption_statements_are_gone_from_the_documents(self):
        sids = {st.get("Sid") for _, st in c.statements(c.permission_set_documents(self.deployer), "Allow")}
        self.assertFalse({"Ec2AdoptedDefaultSgRevokeRules", "Ec2AdoptedDefaultSgFirstTags", "KmsManageProjectKeys",
                          "KmsUseProjectKeysViaServices", "KmsGrantsForAwsResourcesOnly"} & sids)

    # ---- (a) kms ------------------------------------------------------------------------------------------------

    def test_a_every_administration_use_and_grant_action_on_a_key_is_caught(self):
        for action in c.KMS_ADMIN_USE_GRANT:
            with self.subTest(action=action):
                plan = self.add_statement("phase14-main--keys-obs", Sid="Added", Action=[action], Resource=[self.KEY], Condition=self.REGION)
                self.assertFires("kms_%s_on_key" % action.split(":")[1], c.check_no_kms_administration_use_or_grants_in_iam, plan)

    def test_a_administration_actions_on_star_are_caught(self):
        for action in ("kms:PutKeyPolicy", "kms:ScheduleKeyDeletion", "kms:Decrypt", "kms:CreateGrant"):
            with self.subTest(action=action):
                plan = self.add_statement("phase14-main--keys-obs", Sid="Added", Action=[action], Resource=["*"], Condition=self.REGION)
                self.assertFires("kms_%s_on_star" % action.split(":")[1], c.check_no_kms_administration_use_or_grants_in_iam, plan)

    def test_a_a_kms_service_wildcard_is_caught(self):
        plan = self.add_statement("phase14-main--keys-obs", Sid="Added", Action=["kms:*"], Resource=[self.KEY], Condition=self.REGION)
        self.assertFires("kms_service_wildcard_on_key", c.check_no_kms_administration_use_or_grants_in_iam, plan)

    def test_a_an_administration_action_smuggled_into_the_tag_statement_is_caught(self):
        plan = self.mutated("phase14-main--keys-obs", lambda d: self.statement(d, "KmsTagWithProjectTags")["Action"].append("kms:PutKeyPolicy"))
        self.assertFires("kms_put_key_policy_added_to_tag_resource_statement", c.check_no_kms_administration_use_or_grants_in_iam, plan)

    def test_a_tag_resource_must_keep_its_request_tags_and_literal_tag_keys(self):
        def drop(key):
            def edit(doc):
                st = self.statement(doc, "KmsTagWithProjectTags")
                st["Condition"]["StringEquals"].pop(key)
            return edit
        for key in ("aws:RequestTag/project", "aws:RequestTag/environment"):
            plan = self.mutated("phase14-main--keys-obs", drop(key))
            self.assertFires("kms_tag_resource_without_%s" % key.split("/")[1], c.check_no_kms_administration_use_or_grants_in_iam, plan)
        plan = self.mutated("phase14-main--keys-obs", lambda d: self.statement(d, "KmsTagWithProjectTags")["Condition"].pop("ForAllValues:StringEquals"))
        self.assertFires("kms_tag_resource_without_tag_keys", c.check_no_kms_administration_use_or_grants_in_iam, plan)
        plan = self.mutated("phase14-main--keys-obs", lambda d: self.statement(d, "KmsTagWithProjectTags")["Condition"]["ForAllValues:StringEquals"].update({"aws:TagKeys": ["*"]}))
        self.assertFires("kms_tag_resource_with_wildcard_tag_keys", c.check_no_kms_administration_use_or_grants_in_iam, plan)
        plan = self.mutated("phase14-main--keys-obs", lambda d: self.statement(d, "KmsTagWithProjectTags").update({"Resource": ["*"]}))
        self.assertFires("kms_tag_resource_on_star", c.check_no_kms_administration_use_or_grants_in_iam, plan)

    def test_a_create_key_must_keep_its_request_tags(self):
        plan = self.mutated("phase14-main--keys-obs", lambda d: self.statement(d, "KmsCreateKeyWithProjectTags").update({"Condition": self.REGION}))
        self.assertFires("kms_create_key_without_request_tags", c.check_no_kms_administration_use_or_grants_in_iam, plan)

    # ---- (b) security-group mutations ---------------------------------------------------------------------------

    def test_b_each_mutation_without_the_project_resource_tag_is_caught(self):
        for action in c.SG_MUTATIONS:
            with self.subTest(action=action):
                plan = self.add_statement("phase14-main--network-mod", Sid="Added", Action=[action], Resource=[self.SG], Condition=self.REQ)
                self.assertFires("sg_%s_without_resource_tag" % action.split(":")[1], c.check_security_group_mutations_need_the_project_resource_tag, plan)

    def test_b_a_mutation_on_star_is_caught(self):
        plan = self.add_statement("phase14-main--network-mod", Sid="Added", Action=["ec2:DeleteSecurityGroup"], Resource=["*"], Condition=self.REGION)
        self.assertFires("sg_delete_on_star", c.check_security_group_mutations_need_the_project_resource_tag, plan)

    def test_b_the_existing_resource_tag_condition_cannot_be_dropped_or_changed(self):
        plan = self.mutated("phase14-main--network-mod", lambda d: self.statement(d, "Ec2ModifyDeleteProjectTaggedOnly").update({"Condition": self.REGION}))
        self.assertFires("sg_modify_delete_statement_loses_resource_tag", c.check_security_group_mutations_need_the_project_resource_tag, plan)
        plan = self.mutated("phase14-main--network-mod", lambda d: self.statement(d, "Ec2ModifyDeleteProjectTaggedOnly")["Condition"]["StringEquals"].update({"aws:ResourceTag/project": "other"}))
        self.assertFires("sg_modify_delete_statement_resource_tag_value_changed", c.check_security_group_mutations_need_the_project_resource_tag, plan)

    def test_b_revoke_on_the_rule_arn_needs_the_resource_tag_but_authorize_may_use_the_request_tag(self):
        rule = "arn:aws:ec2:us-east-2:111122223333:security-group-rule/*"
        plan = self.add_statement("phase14-main--network-mod", Sid="Added", Action=["ec2:RevokeSecurityGroupIngress"], Resource=[rule], Condition=self.REQ)
        self.assertFires("sg_revoke_on_rule_with_request_tag_only", c.check_security_group_mutations_need_the_project_resource_tag, plan)
        ok = self.add_statement("phase14-main--network-mod", Sid="Added", Action=["ec2:AuthorizeSecurityGroupEgress"], Resource=[rule], Condition=self.REQ)
        self.assertEqual(c.check_security_group_mutations_need_the_project_resource_tag(ok), [])

    # ---- (c) tagging ---------------------------------------------------------------------------------------------

    def test_c_a_request_tag_only_create_tags_on_security_groups_is_caught(self):
        plan = self.add_statement("phase14-main--network-mod", Sid="Added", Action=["ec2:CreateTags"], Resource=[self.SG],
                                  Condition={"StringEquals": dict(self.REQ["StringEquals"]), "ForAllValues:StringEquals": {"aws:TagKeys": ["project", "environment"]}})
        self.assertFires("sg_create_tags_on_adoption_statement_restored", c.check_security_group_tagging_cannot_adopt, plan)

    def test_c_create_tags_on_star_is_caught(self):
        plan = self.add_statement("phase14-main--network-mod", Sid="Added", Action=["ec2:CreateTags"], Resource=["*"], Condition=self.REGION)
        self.assertFires("ec2_create_tags_on_star", c.check_security_group_tagging_cannot_adopt, plan)

    def test_c_the_create_time_tagging_statement_cannot_lose_its_create_action(self):
        plan = self.mutated('phase14-main--network"]', lambda d: self.statement(d, "Ec2TagOnCreateOnly")["Condition"]["StringEquals"].pop("ec2:CreateAction"))
        self.assertFires("sg_tag_on_create_statement_loses_create_action", c.check_security_group_tagging_cannot_adopt, plan)

    def test_c_the_retag_statement_cannot_lose_its_resource_tag(self):
        plan = self.mutated('phase14-main--network"]', lambda d: self.statement(d, "Ec2RetagProjectResources").update({"Condition": self.REGION}))
        self.assertFires("sg_retag_statement_loses_resource_tag", c.check_security_group_tagging_cannot_adopt, plan)

    # ---- (d) the default group ----------------------------------------------------------------------------------

    def test_d_a_planned_default_security_group_is_caught(self):
        plan = copy.deepcopy(self.main)
        plan["resource_changes"].append({"address": "module.network.aws_default_security_group.closed", "mode": "managed",
                                         "type": "aws_default_security_group", "name": "closed",
                                         "change": {"actions": ["create"], "after": {"tags": {}, "tags_all": {}}}})
        self.assertFires("default_security_group_in_the_main_plan", c.check_no_default_security_group, plan)


def _add(cls, table):
    for name, (edits, expected) in table.items():
        def test(self, name=name, edits=edits, expected=expected):
            self.run_mutation(name, edits, expected)
        test.__name__ = "test_mutation_" + re.sub(r"\W", "_", name)
        setattr(cls, test.__name__, test)


_add(DeployerMutations, DEPLOYER_MUTATIONS)
_add(MainRootMutations, MAIN_MUTATIONS)

if __name__ == "__main__":
    unittest.main()

"""Phase 13C carried test gaps for the isolated EMR spike root (12D review items 6, 7, 12).

Real-tree cases prove the named invariants hold on a scratch copy of the current spike root. Mutation cases apply
one defect to a scratch copy (never the repository) and require the SPECIFIC named check to fire, so a mutation
cannot be "caught" by an unrelated failure. Each mutation also records whether the root's pre-existing
`terraform test` suite noticed it (informational raw evidence: the original 12D finding was that it did not).

Item 6   added 0.0.0.0/0:22 ingress, second KMS key, GetObject widened to bucket/*, added SNS/SQS, gp3 IOPS and
         throughput not pinned.
Item 7   every taggable resource's tags_all (not only provider default_tags) carries the seven required tags.
Item 12  aws_default_security_group is absent; re-adding it is caught.
"""
import unittest

import infra_support as s
import spike_checks as c
from infra_support import InfraTestCase, TfTree, record_mutation, tail


class SpikeRealTree(InfraTestCase):
    """The current spike root satisfies every named invariant."""

    @classmethod
    def setUpClass(cls):
        cls.tree = TfTree("spike")
        cls.addClassCleanup(cls.tree.close)
        cls.plan = cls.tree.plan_json()
        cls.state = cls.tree.state_json()

    def test_every_named_plan_check_holds(self):
        for name, fn in c.PLAN_CHECKS.items():
            with self.subTest(check=name):
                self.assertEqual(fn(self.plan), [], name)

    def test_every_named_state_check_holds(self):
        for name, fn in c.STATE_CHECKS.items():
            with self.subTest(check=name):
                self.assertEqual(fn(self.state), [], name)

    def test_existing_spike_suite_passes_on_the_unmutated_copy(self):
        """The scratch copy is faithful: the root's own committed terraform tests pass on it."""
        done = self.tree.existing_tests()
        self.assertEqual(done.returncode, 0, tail(done.stdout, 1500) + tail(done.stderr, 800))
        self.assertRegex(done.stdout, r"Success!\s+\d+ passed, 0 failed")

    # ---- item 6: exact inventory and counts ---------------------------------------------------------------

    def test_item6_exact_resource_inventory_and_counts(self):
        changes = s.managed_changes(self.plan)
        self.assertEqual(len(changes), 55)
        self.assertEqual(set(changes), set(c.EXPECTED_ADDRESSES))
        types = [a.split(".")[0] for a in changes]
        for resource_type, count in (("aws_kms_key", 1), ("aws_kms_alias", 1), ("aws_s3_bucket", 1), ("aws_s3_object", 7),
                                     ("aws_security_group", 4), ("aws_vpc_security_group_ingress_rule", 9),
                                     ("aws_vpc_security_group_egress_rule", 4), ("aws_iam_role", 2),
                                     ("aws_emr_cluster", 1), ("aws_efs_file_system", 1), ("aws_vpc", 1)):
            self.assertEqual(types.count(resource_type), count, resource_type)
        self.assertFalse([t for t in types if t.startswith(("aws_sns_", "aws_sqs_"))])

    def test_item6_no_ingress_from_a_cidr_and_no_ssh(self):
        for address in s.managed_changes(self.plan):
            if address.startswith("aws_vpc_security_group_ingress_rule."):
                a = s.after(self.plan, address)
                self.assertIsNone(a["cidr_ipv4"], address)
                self.assertIsNone(a["cidr_ipv6"], address)
                self.assertIsNone(a["prefix_list_id"], address)
                self.assertNotEqual(a["from_port"], 22, address)

    def test_item6_instance_policy_get_object_is_staging_only_with_exact_arn(self):
        values = s.state_resources(self.state)["aws_iam_role_policy.instance"]
        statements = s.policy_statements(values["policy"])
        get_object = [st for st in statements if "s3:GetObject" in s.as_list(st["Action"])]
        self.assertEqual(len(get_object), 1)
        self.assertEqual(s.as_list(get_object[0]["Resource"]), [c.BUCKET_ARN + "/staging/*"])

    def test_item6_data_volumes_pin_iops_and_throughput(self):
        cluster = s.after(self.plan, "aws_emr_cluster.spike")
        for group in ("master_instance_group", "core_instance_group"):
            config = cluster[group][0]["ebs_config"][0]
            self.assertEqual((config["type"], config["size"], config["iops"], config["throughput"]), ("gp3", 32, 3000, 125), group)

    # ---- item 7: tags_all on every taggable resource --------------------------------------------------------

    def test_item7_every_taggable_resource_carries_required_tags_in_tags_all(self):
        checked = 0
        for address in sorted(c.EXPECTED_TAGGABLE):
            tags_all = s.after(self.plan, address).get("tags_all")
            self.assertIsInstance(tags_all, dict, "%s exposes no tags_all" % address)
            for key, value in c.REQUIRED_TAGS.items():
                self.assertEqual(tags_all.get(key), value, "%s tags_all[%s]" % (address, key))
            checked += 1
        self.assertEqual(checked, 41)  # 55 resources minus the 14 that have no tags argument

    def test_item7_non_taggable_resources_are_exactly_the_reviewed_set(self):
        exposing = {a for a in s.managed_changes(self.plan) if isinstance(s.after(self.plan, a).get("tags_all"), dict)}
        self.assertEqual(exposing, set(c.EXPECTED_TAGGABLE))

    # ---- item 12: the default security group is not managed --------------------------------------------------

    def test_item12_default_security_group_is_absent_from_the_plan(self):
        self.assertEqual([a for a in s.managed_changes(self.plan) if a.startswith("aws_default_")], [])
        self.assertEqual(c.check_default_security_group_absent(self.plan), [])


class SpikeMutations(InfraTestCase):
    """Each mutation, applied to a scratch copy, must make a SPECIFIC invariant fail."""

    def run_mutation(self, name, mutate, expect_plan=(), expect_state=()):
        with TfTree("spike") as tree:
            mutate(tree)
            failing_plan = c.failing_plan_checks(tree.plan_json())
            failing_state = c.failing_state_checks(tree.state_json())
            existing = tree.existing_tests()
            record_mutation("spike:" + name, {
                "root": "spike",
                "new_plan_checks_failing": sorted(failing_plan),
                "new_state_checks_failing": sorted(failing_state),
                "existing_terraform_test_rc": existing.returncode,
                "existing_terraform_test_summary": (existing.stdout.strip().splitlines() or [""])[-1],
                "caught_by_new_suite": bool(failing_plan or failing_state),
                "caught_by_existing_suite": existing.returncode != 0,
            })
        self.assertCaught(failing_plan, expect_plan, name)
        self.assertCaught(failing_state, expect_state, name)
        self.assertTrue(failing_plan or failing_state, "mutation %r passed every check" % name)

    # ---- item 6 ----------------------------------------------------------------------------------------------

    def test_item6_added_world_open_ssh_ingress_rule_is_caught(self):
        def mutate(t):
            t.add_file("zz_mutation.tf", '''resource "aws_vpc_security_group_ingress_rule" "ssh_from_world" {
  security_group_id = aws_security_group.primary.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
}
''')
        self.run_mutation("ssh_from_world_rule", mutate, ["security_group_rules", "inventory"])

    def test_item6_added_legacy_security_group_rule_for_ssh_is_caught(self):
        def mutate(t):
            t.add_file("zz_mutation.tf", '''resource "aws_security_group_rule" "ssh_legacy" {
  type              = "ingress"
  security_group_id = aws_security_group.core.id
  cidr_blocks       = ["0.0.0.0/0"]
  protocol          = "tcp"
  from_port         = 22
  to_port           = 22
}
''')
        self.run_mutation("ssh_legacy_rule", mutate, ["security_group_rules", "forbidden_families", "inventory"])

    def test_item6_inline_ingress_block_on_a_security_group_is_caught(self):
        def mutate(t):
            t.regex_sub("security_groups.tf", r'^resource "aws_security_group" "primary" \{\n',
                        'resource "aws_security_group" "primary" {\n  ingress {\n    from_port   = 22\n    to_port     = 22\n'
                        '    protocol    = "tcp"\n    cidr_blocks = ["0.0.0.0/0"]\n  }\n')
        self.run_mutation("ssh_inline_ingress_block", mutate, ["security_group_rules"])

    def test_item6_second_kms_key_is_caught(self):
        def mutate(t):
            t.add_file("zz_mutation.tf", 'resource "aws_kms_key" "second" {\n  description = "unreviewed second key"\n}\n')
        self.run_mutation("second_kms_key", mutate, ["single_kms_key", "inventory"])

    def test_item6_get_object_widened_to_whole_bucket_is_caught(self):
        def mutate(t):
            t.replace("iam.tf", '"${aws_s3_bucket.spike.arn}/staging/*"', '"${aws_s3_bucket.spike.arn}/*"')
        self.run_mutation("get_object_bucket_wide", mutate, expect_state=["s3_get_object_scope", "instance_policy_exact"])

    def test_item6_get_object_action_widened_to_wildcard_is_caught(self):
        def mutate(t):
            t.replace("iam.tf", '"s3:GetObject"', '"s3:Get*"')
        self.run_mutation("get_object_wildcard_action", mutate, expect_state=["instance_policy_exact"])

    def test_item6_added_sns_and_sqs_resources_are_caught(self):
        def mutate(t):
            t.add_file("zz_mutation.tf", 'resource "aws_sns_topic" "extra" {\n  name = "scholarchain-spike-emr-extra"\n}\n\n'
                       'resource "aws_sqs_queue" "extra" {\n  name = "scholarchain-spike-emr-extra"\n}\n')
        self.run_mutation("sns_sqs_added", mutate, ["forbidden_families", "inventory"])

    def test_item6_gp3_iops_and_throughput_removed_is_caught(self):
        def mutate(t):
            t.regex_sub("emr.tf", r"^[ \t]*(iops|throughput)[ \t]*=[ \t]*\d+[ \t]*\n", "", count=0)
        self.run_mutation("gp3_unpinned", mutate, ["ebs_pinned"])

    def test_item6_gp3_iops_changed_is_caught(self):
        def mutate(t):
            t.replace("emr.tf", "iops                 = 3000", "iops                 = 16000", count=-1)
        self.run_mutation("gp3_iops_changed", mutate, ["ebs_pinned"])

    # ---- item 7 ------------------------------------------------------------------------------------------------

    def test_item7_resource_level_tag_override_is_caught_by_tags_all(self):
        def mutate(t):
            t.regex_sub("iam.tf", r'^resource "aws_iam_role" "service" \{\n',
                        'resource "aws_iam_role" "service" {\n  tags = { owner = "someone-else" }\n')
        self.run_mutation("iam_role_owner_override", mutate, ["tags_all"])

    def test_item7_stack_tag_override_on_the_cluster_is_caught(self):
        def mutate(t):
            t.regex_sub("emr.tf", r'^resource "aws_emr_cluster" "spike" \{\n',
                        'resource "aws_emr_cluster" "spike" {\n  tags = { "scholarchain:stack" = "other" }\n')
        self.run_mutation("cluster_stack_tag_override", mutate, ["tags_all"])

    def test_item7_dropping_a_default_tag_is_caught(self):
        def mutate(t):
            t.regex_sub("main.tf", r"^[ \t]*expiration[ \t]*=[ \t]*var\.expiration_date[ \t]*\n", "")
        self.run_mutation("default_tag_expiration_dropped", mutate, ["tags_all"])

    # ---- item 12 -----------------------------------------------------------------------------------------------

    def test_item12_re_adding_the_default_security_group_is_caught(self):
        def mutate(t):
            t.add_file("zz_mutation.tf", 'resource "aws_default_security_group" "readded" {\n  vpc_id = aws_vpc.spike.id\n}\n')
        self.run_mutation("default_sg_readded", mutate, ["default_security_group_absent", "forbidden_families", "inventory"])


if __name__ == "__main__":
    unittest.main()

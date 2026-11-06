"""Phase 13C carried test gaps for the deployer root (12D review items 10, 20, 21).

Real-tree cases prove the invariants on a scratch copy of the current deployer root. Mutation cases edit only that
scratch copy and require the SPECIFIC named check to fire. Each mutation also records whether the root's own
committed `terraform test` suite noticed it (informational raw evidence).

Item 10  a policy whose request-tag condition was stripped or weakened is rejected (kms:CreateKey on * without the
         request-tag condition; RunJobFlow without the EMR tag). The static guard is covered in
         test_guard_conditions.py; this module checks the rendered policy conditions themselves.
Item 20  the tag conditions carry the exact value ("true" / "spike-emr"), not merely the key.
Item 21  the login policy attaches to the deployer role; retargeting login.role fails.
"""
import unittest

import deployer_checks as d
import infra_support as s
from infra_support import InfraTestCase, TfTree, record_mutation, tail

CREATE_KEY_SID = '"KmsCreateKeyWithStackTag"'
RUN_JOB_FLOW_SID = '"EmrRunJobFlowRequireStackTags"'


class DeployerRealTree(InfraTestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = TfTree("deployer")
        cls.addClassCleanup(cls.tree.close)
        cls.plan = cls.tree.plan_json()
        cls.state = cls.tree.state_json()

    def test_every_named_check_holds(self):
        for name, fn in d.PLAN_CHECKS.items():
            with self.subTest(check=name):
                self.assertEqual(fn(self.plan), [], name)
        for name, fn in d.STATE_CHECKS.items():
            with self.subTest(check=name):
                self.assertEqual(fn(self.state), [], name)

    def test_existing_deployer_suite_passes_on_the_unmutated_copy(self):
        done = self.tree.existing_tests()
        self.assertEqual(done.returncode, 0, tail(done.stdout, 1500) + tail(done.stderr, 800))
        self.assertRegex(done.stdout, r"Success!\s+\d+ passed, 0 failed")

    # ---- item 10 ---------------------------------------------------------------------------------------------

    def test_item10_create_key_is_allowed_only_with_request_tag_and_region(self):
        found = []
        for address, doc in d.policy_documents(self.plan):
            for st in s.policy_statements(doc):
                if st.get("Effect") == "Allow" and "kms:CreateKey" in s.as_list(st["Action"]):
                    found.append(st)
        self.assertEqual(len(found), 1)
        st = found[0]
        self.assertEqual(s.as_list(st["Resource"]), ["*"])
        self.assertEqual(st["Condition"]["StringEquals"]["aws:RequestTag/scholarchain:stack"], "spike-emr")
        self.assertEqual(st["Condition"]["StringEquals"]["aws:RequestedRegion"], "us-east-2")

    def test_item10_run_job_flow_needs_stack_and_emr_request_tags(self):
        found = [st for _, doc in d.policy_documents(self.plan) for st in s.policy_statements(doc)
                 if st.get("Effect") == "Allow" and "elasticmapreduce:RunJobFlow" in s.as_list(st["Action"])]
        self.assertEqual(len(found), 1)
        equals = found[0]["Condition"]["StringEquals"]
        self.assertEqual(equals["aws:RequestTag/scholarchain:stack"], "spike-emr")
        self.assertEqual(equals["aws:RequestTag/for-use-with-amazon-emr-managed-policies"], "true")

    def test_item10_no_unconditioned_allow_on_a_wildcard_resource(self):
        self.assertEqual(d.check_wildcard_resource_allows_are_conditioned(self.plan), [])

    # ---- item 20 -----------------------------------------------------------------------------------------------

    def test_item20_every_tag_condition_has_the_exact_value(self):
        stack = emr = 0
        for address, doc in d.policy_documents(self.plan):
            for st in s.policy_statements(doc):
                for operator, key, value in s.condition_pairs(st):
                    if key.endswith("/scholarchain:stack") and "Tag/" in key:
                        self.assertEqual((operator, value), ("StringEquals", "spike-emr"), "%s %s" % (address, key))
                        stack += 1
                    if key.endswith("/for-use-with-amazon-emr-managed-policies") and "Tag/" in key:
                        self.assertEqual((operator, value), ("StringEquals", "true"), "%s %s" % (address, key))
                        emr += 1
        self.assertGreaterEqual(stack, 15)
        self.assertGreaterEqual(emr, 5)

    # ---- item 21 -----------------------------------------------------------------------------------------------

    def test_item21_login_policy_attaches_to_the_deployer_role(self):
        resources = s.state_resources(self.state)
        login, deployer = resources["aws_iam_role_policy.login"], resources["aws_iam_role.deployer"]
        self.assertEqual(deployer["name"], "scholarchain-deployer")
        self.assertIn(login["role"], (deployer["id"], deployer["name"]))
        self.assertEqual(login["name"], "scholarchain-deployer-same-device-login")

    def test_item21_only_one_role_exists_and_every_attachment_targets_it(self):
        self.assertEqual(d.check_attachments_target_deployer_role(self.plan), [])


class DeployerMutations(InfraTestCase):
    def run_mutation(self, name, mutate, expect_plan=(), expect_state=()):
        with TfTree("deployer") as tree:
            mutate(tree)
            failing_plan = d.failing_plan_checks(tree.plan_json())
            failing_state = d.failing_state_checks(tree.state_json())
            existing = tree.existing_tests()
            record_mutation("deployer:" + name, {
                "root": "deployer",
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

    # ---- item 10 -----------------------------------------------------------------------------------------------

    def test_item10_create_key_with_the_condition_stripped_is_rejected(self):
        def mutate(t):
            t.strip_attribute_after("permission_sets.tf", CREATE_KEY_SID, "Condition")
        self.run_mutation("create_key_condition_stripped", mutate,
                          ["request_tag_only_actions", "wildcard_resource_allows_are_conditioned"])

    def test_item10_create_key_request_tag_dropped_leaving_only_the_region_is_rejected(self):
        def mutate(t):
            t.replace_after("permission_sets.tf", CREATE_KEY_SID, "merge(local.c_region, local.c_req_stack)", "local.c_region")
        self.run_mutation("create_key_request_tag_dropped", mutate, ["request_tag_only_actions"])

    def test_item10_run_job_flow_without_the_emr_request_tag_is_rejected(self):
        def mutate(t):
            t.replace_after("permission_sets.tf", RUN_JOB_FLOW_SID,
                            "merge(local.c_region, local.c_req_stack, local.c_req_emr_tag)", "merge(local.c_region, local.c_req_stack)")
        self.run_mutation("run_job_flow_emr_tag_dropped", mutate, ["request_tag_only_actions"])

    # ---- item 20 -----------------------------------------------------------------------------------------------

    def test_item20_emr_request_tag_value_false_is_rejected(self):
        def mutate(t):
            t.regex_sub("permission_sets.tf", r'^([ \t]*c_req_emr_tag[ \t]*=.*?)"true"', r'\1"false"')
        self.run_mutation("emr_request_tag_value_false", mutate, ["tag_condition_values", "request_tag_only_actions"])

    def test_item20_emr_resource_tag_value_false_is_rejected(self):
        def mutate(t):
            t.regex_sub("permission_sets.tf", r'^([ \t]*c_res_emr_tag[ \t]*=.*?)"true"', r'\1"false"')
        self.run_mutation("emr_resource_tag_value_false", mutate, ["tag_condition_values"])

    def test_item20_stack_tag_value_changed_is_rejected(self):
        def mutate(t):
            t.regex_sub("permission_sets.tf", r'^([ \t]*spike_stack_value[ \t]*=[ \t]*)"spike-emr"', r'\1"other-stack"')
        self.run_mutation("stack_tag_value_changed", mutate, ["tag_condition_values"])

    # ---- item 21 -----------------------------------------------------------------------------------------------

    def test_item21_login_policy_retargeted_to_another_named_role_is_rejected(self):
        def mutate(t):
            t.replace_after("main.tf", 'resource "aws_iam_role_policy" "login"', "aws_iam_role.deployer.id", '"scholarchain-billing-deployer"')
        self.run_mutation("login_retargeted_to_billing_role", mutate, expect_state=["login_attachment"])

    def test_item21_login_policy_retargeted_to_a_second_role_resource_is_rejected(self):
        def mutate(t):
            t.add_file("zz_mutation.tf", 'resource "aws_iam_role" "other" {\n  name               = "scholarchain-other"\n'
                       '  assume_role_policy = jsonencode(local.trust_policy)\n}\n')
            t.replace_after("main.tf", 'resource "aws_iam_role_policy" "login"', "aws_iam_role.deployer.id", "aws_iam_role.other.id")
        self.run_mutation("login_retargeted_to_second_role", mutate, ["attachments_target_deployer_role"], ["login_attachment"])


if __name__ == "__main__":
    unittest.main()

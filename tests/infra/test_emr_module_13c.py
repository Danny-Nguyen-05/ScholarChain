"""Independent tests of the ported main EMR module (infra/terraform/modules/emr), Phase 13C task 1 and 4.

Expectations come from decision 12-10, the Phase 13 plan, the Step 0 answers in docs/agent-runs/phase-13/prompt.md and the
reviewed pins in scripts/config (see emr_module_checks.py); the G6 reason for the task-node and instance-type bounds is
computed here from emr-pricing.conf and release.conf. The module is planned through a scratch wrapper root (real provider in
a no-network configuration) and applied against mocks for the values that only exist after apply. Every property has a
scratch-copy MUTATION that must fail it; the repository is never edited.
"""
import unittest
from decimal import Decimal as D

import emr_module_checks as e
import infra_support as s
from infra_support import EmrModuleTree, InfraTestCase, record_mutation

VARIABLES = "modules/emr/variables.tf"
MAIN = "modules/emr/main.tf"
EFS = "modules/emr/efs.tf"


def refused(tree):
    """(refused?, text): a plan that fails with a variable validation message."""
    done = tree.plan_attempt()
    return done.returncode != 0 and "Invalid value for variable" in (done.stderr + done.stdout), done.stderr + done.stdout


def scenario_g6_bounds(test, patch=None):
    """The module accepts exactly the cluster sizes the G6 per-run cap allows, computed independently."""
    cap, hours, per_instance = e.g6_bounds()
    test.assertEqual((cap, hours), (D("3"), D("3.25")), "the pinned inputs changed: re-derive the expectations")
    max_instances = e.max_instances(per_instance["M5_XLARGE"], hours, cap)
    test.assertEqual(max_instances, 3)  # floor(3 / (0.240 x 3.25)) = floor(3.846)
    allowed_tasks = max_instances - 2  # minus the primary and the one core node
    test.assertEqual(allowed_tasks, 1)
    # the m5.2xlarge minimum cluster (2 instances) already costs 2 x 0.480 x 3.25 = 3.12 > 3, so it is never allowed
    test.assertEqual(e.max_instances(per_instance["M5_2XLARGE"], hours, cap), 1)

    def tree(config):
        t = EmrModuleTree(config)
        test.addCleanup(t.close)
        if patch:
            patch(t)
        return t
    ok = tree({"max_task_nodes": allowed_tasks, "task_node_count": allowed_tasks}).plan_attempt()
    test.assertEqual(ok.returncode, 0, ok.stdout[-800:] + ok.stderr[-800:])
    over, text = refused(tree({"max_task_nodes": allowed_tasks + 1, "task_node_count": allowed_tasks + 1}))
    test.assertTrue(over, "max_task_nodes=%d (a cluster of %d instances over the cap) was accepted\n%s" % (allowed_tasks + 1, max_instances + 1, text[-400:]))
    big, text = refused(tree({"instance_type": "m5.2xlarge"}))
    test.assertTrue(big, "m5.2xlarge was accepted although its smallest cluster exceeds the cap\n" + text[-400:])
    unpriced, text = refused(tree({"instance_type": "m5.4xlarge"}))
    test.assertTrue(unpriced, "an instance type without a reviewed rate was accepted\n" + text[-400:])


def scenario_idle_cap(test, patch=None):
    def tree(config):
        t = EmrModuleTree(config)
        test.addCleanup(t.close)
        if patch:
            patch(t)
        return t
    for idle in (60, 900):
        test.assertEqual(tree({"idle_timeout_seconds": idle}).plan_attempt().returncode, 0, "idle timeout %d must be accepted" % idle)
    for idle in (59, 901, 1800, 3600):
        was_refused, text = refused(tree({"idle_timeout_seconds": idle}))
        test.assertTrue(was_refused, "idle timeout %d was accepted (cap 900 s)\n%s" % (idle, text[-300:]))


class EmrModuleReal(InfraTestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = EmrModuleTree()
        cls.addClassCleanup(cls.tree.close)
        cls.plan = cls.tree.plan_json()
        cls.state = cls.tree.state_json()

    def test_every_named_check_holds_on_the_current_module(self):
        for name, fn in e.PLAN_CHECKS.items():
            with self.subTest(check=name):
                self.assertEqual(fn(self.plan), [], name)
        for name, fn in e.STATE_CHECKS.items():
            with self.subTest(check=name):
                self.assertEqual(fn(self.state), [], name)

    # ---- decision 12-10 ----------------------------------------------------------------------------------------

    def test_applications_are_hadoop_only_on_emr_7_8_0(self):
        c = s.after(self.plan, e.PREFIX + "aws_emr_cluster.pipeline[0]")
        self.assertEqual(c["applications"], ["Hadoop"])
        self.assertEqual(c["release_label"], "emr-7.8.0")

    def test_in_transit_tls_is_off_and_at_rest_encryption_is_on(self):
        import json
        conf = json.loads(s.after(self.plan, e.PREFIX + "aws_emr_security_configuration.encrypted[0]")["configuration"])["EncryptionConfiguration"]
        self.assertIs(conf["EnableInTransitEncryption"], False)
        self.assertIs(conf["EnableAtRestEncryption"], True)
        self.assertNotIn("InTransitEncryptionConfiguration", conf)

    def test_rendered_spark_settings_equal_the_reviewed_conf_parsed_independently(self):
        text, sha_arg, _ = e.rendered_spark_defaults(self.state)
        got, want = e.parse_spark_conf(text), e.parse_spark_conf(e.SPARK_CONF.read_text())
        self.assertEqual(got, want)
        self.assertGreaterEqual(len(want), 22)
        self.assertEqual(got["spark.dynamicAllocation.shuffleTracking.enabled"], "true")
        self.assertEqual(got["spark.shuffle.service.enabled"], "false")
        self.assertEqual(got["spark.dynamicAllocation.enabled"], "true")
        self.assertEqual(got["spark.network.crypto.authEngineVersion"], "1")
        import hashlib
        self.assertEqual(sha_arg, hashlib.sha256(text.encode()).hexdigest())

    def test_default_cluster_has_zero_task_nodes_and_no_managed_scaling(self):
        names = set(s.managed_changes(self.plan))
        self.assertFalse([a for a in names if "aws_emr_instance_group" in a or "managed_scaling" in a])
        self.assertEqual(len(names), 11)

    def test_efs_admits_nfs_from_the_emr_group_only_with_no_cidr(self):
        ingress = {a: s.after(self.plan, a) for a in s.managed_changes(self.plan) if "ingress_rule" in a}
        self.assertEqual(list(ingress), [e.PREFIX + "aws_vpc_security_group_ingress_rule.efs_from_emr[0]"])
        rule = next(iter(ingress.values()))
        self.assertEqual((rule["ip_protocol"], rule["from_port"], rule["to_port"]), ("tcp", 2049, 2049))
        self.assertEqual(rule["referenced_security_group_id"], e.EMR_SG)
        self.assertIsNone(rule["cidr_ipv4"])
        self.assertIsNone(rule["cidr_ipv6"])
        self.assertIsNone(rule["prefix_list_id"])

    def test_the_stack_tag_is_on_the_cluster_for_propagation(self):
        tags = s.after(self.plan, e.PREFIX + "aws_emr_cluster.pipeline[0]")["tags"]
        self.assertEqual(tags["scholarchain:stack"], "main-emr")
        self.assertEqual(tags["for-use-with-amazon-emr-managed-policies"], "true")

    def test_idle_timeout_default_is_900(self):
        self.assertEqual(s.after(self.plan, e.PREFIX + "aws_emr_cluster.pipeline[0]")["auto_termination_policy"], [{"idle_timeout": 900}])

    def test_the_g6_reason_is_derived_from_the_reviewed_rates(self):
        cap, hours, per = e.g6_bounds()
        self.assertEqual(str(per["M5_XLARGE"]), "0.240")
        self.assertEqual(str(per["M5_2XLARGE"]), "0.480")
        # 4 x 0.240 x 3.25 = 3.12 > 3 (two task nodes); 3 x 0.240 x 3.25 = 2.34 <= 3 (one task node)
        self.assertEqual(4 * per["M5_XLARGE"] * hours, D("3.12"))
        self.assertEqual(3 * per["M5_XLARGE"] * hours, D("2.34"))
        self.assertGreater(4 * per["M5_XLARGE"] * hours, cap)
        self.assertLessEqual(3 * per["M5_XLARGE"] * hours, cap)

    def test_task_node_group_pins_gp3_size_iops_and_volumes_and_the_provider_has_no_throughput_argument(self):
        """The optional task group pins gp3, the configured size, 3000 IOPS and one volume per instance; the primary and core
        groups additionally pin throughput 125. The task group cannot pin throughput because the pinned provider's
        aws_emr_instance_group ebs_config has no such argument (confirmed here from the provider schema, offline): gp3's
        125 MiB/s baseline is then the default. If a future provider adds the argument, this test fails and the pin is due."""
        scenario_task_group_ebs(self)

    def test_primary_and_core_groups_pin_gp3_iops_and_throughput(self):
        c = s.after(self.plan, e.PREFIX + "aws_emr_cluster.pipeline[0]")
        for group in ("master_instance_group", "core_instance_group"):
            ebs = c[group][0]["ebs_config"][0]
            self.assertEqual({k: ebs.get(k) for k in ("type", "iops", "throughput")}, {"type": "gp3", "iops": 3000, "throughput": 125}, group)


def provider_ebs_config_attributes(tree):
    """Attribute names of aws_emr_instance_group.ebs_config and aws_emr_cluster master ebs_config, read from the provider schema
    (`terraform providers schema -json`, offline, from the initialised scratch root)."""
    import json
    tree.init()
    done = tree.tf("providers", "schema", "-json")
    assert done.returncode == 0, done.stderr[-500:]
    resources = json.loads(done.stdout)["provider_schemas"]["registry.terraform.io/hashicorp/aws"]["resource_schemas"]
    group = resources["aws_emr_instance_group"]["block"]["block_types"]["ebs_config"]["block"]["attributes"]
    cluster = resources["aws_emr_cluster"]["block"]["block_types"]["master_instance_group"]["block"]["block_types"]["ebs_config"]["block"]["attributes"]
    return set(group), set(cluster)


def scenario_task_group_ebs(test, patch=None):
    tree = EmrModuleTree({"max_task_nodes": 1, "task_node_count": 1})
    test.addCleanup(tree.close)
    if patch:
        patch(tree)
    group_attrs, cluster_attrs = provider_ebs_config_attributes(tree)
    test.assertIn("throughput", cluster_attrs, "the cluster groups can pin throughput, so the primary/core pins are meaningful")
    test.assertNotIn("throughput", group_attrs, "the provider now supports throughput on aws_emr_instance_group: pin it in the module and update this test")
    test.assertEqual(group_attrs, {"iops", "size", "type", "volumes_per_instance"})
    ebs = s.after(tree.plan_json(), e.PREFIX + "aws_emr_instance_group.task[0]")["ebs_config"][0]
    test.assertEqual({k: ebs.get(k) for k in ("type", "size", "iops", "volumes_per_instance")}, {"type": "gp3", "size": 32, "iops": 3000, "volumes_per_instance": 1})


class EmrModuleBounds(InfraTestCase):
    def test_task_nodes_and_instance_types_are_bounded_by_the_g6_cap_computed_independently(self):
        scenario_g6_bounds(self)

    def test_idle_timeout_is_capped_at_900_seconds(self):
        scenario_idle_cap(self)

    def test_one_task_node_and_bounded_managed_scaling_are_expressible(self):
        t = EmrModuleTree({"max_task_nodes": 1, "task_node_count": 1, "managed_scaling_enabled": True, "managed_scaling_max_capacity": 2})
        self.addCleanup(t.close)
        plan = t.plan_json()
        changes = s.managed_changes(plan)
        task = [a for a in changes if "aws_emr_instance_group.task" in a]
        scaling = [a for a in changes if "aws_emr_managed_scaling_policy" in a]
        self.assertEqual(len(task), 1)
        self.assertEqual(len(scaling), 1)
        group = s.after(plan, task[0])
        self.assertEqual((group["instance_type"], group["instance_count"]), ("m5.xlarge", 1))
        limits = s.after(plan, scaling[0])["compute_limits"][0]
        self.assertEqual(limits["unit_type"], "Instances")
        self.assertLessEqual(limits["maximum_capacity_units"], 2)
        self.assertLessEqual(limits["maximum_core_capacity_units"], 1)

    def test_managed_scaling_without_task_nodes_and_oversized_scaling_are_refused(self):
        for config, label in (({"managed_scaling_enabled": True}, "scaling with no task nodes"),
                              ({"max_task_nodes": 1, "managed_scaling_enabled": True, "managed_scaling_max_capacity": 3}, "capacity above core + 1 task"),
                              ({"task_node_count": 1}, "task_node_count above max_task_nodes"),
                              ({"ebs_iops": 4000}, "provisioned IOPS"),
                              ({"ebs_throughput": 250}, "provisioned throughput"),
                              ({"release_label": "emr-7.9.0"}, "another release")):
            with self.subTest(case=label):
                t = EmrModuleTree(config)
                self.addCleanup(t.close)
                was_refused, text = refused(t)
                self.assertTrue(was_refused, "the module accepted %s\n%s" % (label, text[-300:]))

    def test_bad_artifact_references_are_refused(self):
        for config, label in (({"bootstrap_sha256": "xyz"}, "bad hash"),
                              ({"bootstrap_uri": "https://example.invalid/b.sh"}, "non-S3 uri"),
                              ({"extra_artifacts": [{"uri": "s3://%s/x" % s.EMR_BUCKET, "sha256": "d" * 64, "dest": "/etc/x"}]}, "dest outside the allowed directories"),
                              ({"extra_artifacts": [{"uri": "s3://%s/x" % s.EMR_BUCKET, "sha256": "d" * 64, "dest": "/opt/scholarchain-runtime/../x"}]}, "dest with ..")):
            with self.subTest(case=label):
                t = EmrModuleTree(config)
                self.addCleanup(t.close)
                was_refused, text = refused(t)
                self.assertTrue(was_refused, "accepted %s\n%s" % (label, text[-300:]))


class EmrModuleMutations(InfraTestCase):
    def run_mutation(self, name, mutate, expect_plan=(), expect_state=(), expect_refusal=None):
        """Apply `mutate` to a scratch copy. The mutation is caught when a named check fires, or (expect_refusal) when the
        module's own validation now refuses the plan with a message containing expect_refusal."""
        with EmrModuleTree() as tree:
            mutate(tree)
            if expect_refusal:
                done = tree.plan_attempt()
                self.assertNotEqual(done.returncode, 0, "mutation %r still plans" % name)
                self.assertIn(expect_refusal, done.stderr + done.stdout, "mutation %r was refused for another reason" % name)
                record_mutation("emrmodule:" + name, {"root": "emrmodule", "caught_by_new_suite": True, "caught_by": "validation: " + expect_refusal,
                                                      "new_plan_checks_failing": [], "new_state_checks_failing": [],
                                                      "existing_terraform_test_rc": None, "existing_terraform_test_summary": "not applicable",
                                                      "caught_by_existing_suite": None})
                return
            failing_plan = e.failing_plan_checks(tree.plan_json())
            failing_state = e.failing_state_checks(tree.state_json())
            record_mutation("emrmodule:" + name, {"root": "emrmodule", "caught_by_new_suite": bool(failing_plan or failing_state),
                                                  "new_plan_checks_failing": sorted(failing_plan), "new_state_checks_failing": sorted(failing_state),
                                                  "existing_terraform_test_rc": None, "existing_terraform_test_summary": "not applicable",
                                                  "caught_by_existing_suite": None})
        self.assertCaught(failing_plan, expect_plan, name)
        self.assertCaught(failing_state, expect_state, name)

    def test_applications_with_spark_added_are_caught(self):
        self.run_mutation("applications_hadoop_spark", lambda t: t.replace(MAIN, 'applications                      = ["Hadoop"]', 'applications                      = ["Hadoop", "Spark"]'),
                          ["cluster_decision_12_10"])

    def test_in_transit_encryption_enabled_is_caught(self):
        self.run_mutation("in_transit_on", lambda t: t.replace(MAIN, "EnableInTransitEncryption = false", "EnableInTransitEncryption = true"),
                          ["security_configuration"])

    def test_at_rest_encryption_disabled_is_caught(self):
        self.run_mutation("at_rest_off", lambda t: t.replace(MAIN, "EnableAtRestEncryption    = true", "EnableAtRestEncryption    = false"),
                          ["security_configuration"])

    def test_a_changed_default_spark_setting_is_caught_by_the_cross_check(self):
        self.run_mutation("spark_memory_changed", lambda t: t.replace(VARIABLES, '"spark.executor.memory" = "3g"', '"spark.executor.memory" = "6g"'),
                          expect_state=["spark_settings_equal_conf"])

    def test_shuffle_tracking_turned_off_is_refused_by_the_module(self):
        self.run_mutation("shuffle_tracking_off", lambda t: t.replace(VARIABLES, '"spark.dynamicAllocation.shuffleTracking.enabled" = "true"\n    "spark.shuffle.service.enabled"', '"spark.dynamicAllocation.shuffleTracking.enabled" = "false"\n    "spark.shuffle.service.enabled"'),
                          expect_refusal="Decision 12-10 requires")

    def test_default_task_nodes_and_managed_scaling_on_are_caught(self):
        def mutate(t):
            t.replace(VARIABLES, "max_task_nodes               = optional(number, 0)", "max_task_nodes               = optional(number, 1)")
            t.replace(VARIABLES, "managed_scaling_enabled      = optional(bool, false)", "managed_scaling_enabled      = optional(bool, true)")
        self.run_mutation("g3_defaults_on", mutate, ["g3_defaults", "inventory"])

    def test_the_task_node_cap_relaxed_to_two_is_caught(self):
        def patch(t):
            t.replace(VARIABLES, "var.config.max_task_nodes >= 0 && var.config.max_task_nodes <= 1", "var.config.max_task_nodes >= 0 && var.config.max_task_nodes <= 2")
        with self.assertRaises(AssertionError):
            scenario_g6_bounds(self, patch=patch)

    def test_the_instance_type_pin_relaxed_is_caught(self):
        def patch(t):
            t.replace(VARIABLES, 'var.config.instance_type == "m5.xlarge"', 'contains(["m5.xlarge", "m5.2xlarge"], var.config.instance_type)')
        with self.assertRaises(AssertionError):
            scenario_g6_bounds(self, patch=patch)

    def test_the_idle_timeout_cap_relaxed_is_caught(self):
        def patch(t):
            t.replace(VARIABLES, "var.config.idle_timeout_seconds <= 900", "var.config.idle_timeout_seconds <= 3600")
        with self.assertRaises(AssertionError):
            scenario_idle_cap(self, patch=patch)

    def test_a_world_open_nfs_rule_is_caught(self):
        def mutate(t):
            t.add_file("modules/emr/zz_mutation.tf", 'resource "aws_vpc_security_group_ingress_rule" "efs_world" {\n  security_group_id = aws_security_group.efs[0].id\n'
                       '  cidr_ipv4         = "0.0.0.0/0"\n  ip_protocol       = "tcp"\n  from_port         = 2049\n  to_port           = 2049\n}\n')
        self.run_mutation("efs_world_rule", mutate, ["efs_nfs_from_emr_only", "inventory"])

    def test_the_efs_rule_switched_from_the_emr_group_to_a_cidr_is_caught(self):
        def mutate(t):
            t.replace(EFS, "referenced_security_group_id = var.security_group_id\n  ip_protocol                  = \"tcp\"\n  from_port                    = 2049\n  to_port                      = 2049\n  description                  = \"NFS from the EMR node group only\"",
                      "cidr_ipv4                    = \"10.0.0.0/8\"\n  ip_protocol                  = \"tcp\"\n  from_port                    = 2049\n  to_port                      = 2049\n  description                  = \"NFS from the EMR node group only\"")
        self.run_mutation("efs_rule_cidr_source", mutate, ["efs_nfs_from_emr_only"])

    def test_the_stack_tag_removed_from_the_cluster_is_caught(self):
        self.run_mutation("stack_tag_removed", lambda t: t.regex_sub(MAIN, r'^[ \t]*"scholarchain:stack"[ \t]*=[ \t]*local\.cfg\.stack_tag_value[ \t]*\n', ""),
                          ["stack_tag"])

    def test_the_gp3_iops_pin_removed_from_the_primary_is_caught(self):
        self.run_mutation("primary_iops_removed", lambda t: t.regex_sub(MAIN, r"^[ \t]*iops[ \t]*=[ \t]*local\.ebs\.iops[ \t]*\n", "", count=1),
                          ["ebs_pinned"])

    def test_an_unconditioned_auto_termination_grant_is_caught(self):
        def mutate(t):
            t.strip_attribute_after(EFS, '"AutoTerminationPolicyOnStackClusters"', "Condition")
        with EmrModuleTree() as tree:
            mutate(tree)
            self.assertTrue(e.failing_state_checks(tree.state_json()).get("node_policy"))
            record_mutation("emrmodule:auto_termination_unconditioned", {"root": "emrmodule", "caught_by_new_suite": True,
                                                                          "new_plan_checks_failing": [], "new_state_checks_failing": ["node_policy"],
                                                                          "existing_terraform_test_rc": None,
                                                                          "existing_terraform_test_summary": "not applicable",
                                                                          "caught_by_existing_suite": None})

    def test_a_provisioned_task_group_iops_value_is_caught(self):
        def patch(t):
            t.replace_after("modules/emr/main.tf", 'resource "aws_emr_instance_group" "task"', "local.ebs.iops", "4000")
        with self.assertRaises(AssertionError):
            scenario_task_group_ebs(self, patch=patch)

    def test_the_runtime_hash_default_changed_is_refused_by_the_c2_validation(self):
        """Since C2 the module refuses a runtime archive hash other than the decision 12-10 pin, so changing only the default is
        caught at plan time by that validation (mutation of ONE occurrence)."""
        def mutate(t):
            t.replace(VARIABLES, 'optional(string, "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5")', 'optional(string, "' + "0" * 64 + '")')
        self.run_mutation("runtime_hash_default_changed", mutate, expect_refusal="Carried finding C2")

    def test_the_runtime_hash_pin_changed_everywhere_is_caught_by_the_bootstrap_arguments_check(self):
        """Mutating BOTH the default and the validation pin gets past C2; the independent check of the bootstrap arguments
        (the pinned 789a96... hash) still fails."""
        def mutate(t):
            t.replace(VARIABLES, "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5", "0" * 64, count=-1)
        self.run_mutation("runtime_hash_pin_changed_everywhere", mutate, expect_state=["bootstrap_arguments"])

    def test_a_runtime_hash_different_from_the_decision_12_10_pin_is_rejected(self):
        for value, label in (("f" * 64, "another valid hash"), ("0" * 63, "short hash"), ("789A9684F91527DFD9B97D56ACF9DBFE5DD4C328299542245DA92968F916DE5".ljust(64, "0"), "upper case")):
            with self.subTest(case=label):
                t = EmrModuleTree({"runtime_archive_sha256": value})
                self.addCleanup(t.close)
                done = t.plan_attempt()
                self.assertNotEqual(done.returncode, 0, "the module accepted %s" % label)
                self.assertIn("Invalid value for variable", done.stderr + done.stdout)
        accepted = EmrModuleTree({"runtime_archive_sha256": "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5"})
        self.addCleanup(accepted.close)
        self.assertEqual(accepted.plan_attempt().returncode, 0)


if __name__ == "__main__":
    unittest.main()

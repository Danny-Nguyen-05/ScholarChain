"""Phase 14B replan (USD 25 course cap), workstream W1: the cost-shape switches, tested from the requirement (test-engineer).

Requirement (user, 2026-11-08; see runtime_shape_checks.py for the full text):
  * container_insights_enabled=false: cluster setting "disabled"; NO embedding-worker backlog policy (its RunningTaskCount metric
    exists only with Container Insights); the three HTTP CPU target-tracking policies REMAIN and use the predefined, free
    ECSServiceAverageCPUUtilization metric; nothing in the plan references the ECS/ContainerInsights namespace. True (the default):
    "enabled" and the backlog policy exists.
  * dashboard_enabled=false: no CloudWatch dashboard (alarms and log groups stay). True (the default): one dashboard.
  * service_capacity: 256 CPU / 1024 MiB accepted for all four services; 256/512 and 256/4096 refused; the committed defaults are
    unchanged (512 CPU / 1024 MiB, min 1, max 2; the worker max 4).
Every check runs a REAL offline `terraform plan` (real provider, no network) on a scratch copy of the module or on the real root
`variable` blocks; the repository is never written. A toolchain that is not initialised is a failure, not a skip.
"""
import json
import re
import unittest

import runtime_shape_checks as R
from infra_support import REPO

EXAMPLE = REPO / "infra/terraform/environments/course.local.tfvars.example"
INSIGHTS_NS = "ECS/ContainerInsights"


def settings(cluster):
    return {s["name"]: s["value"] for s in cluster["setting"]}


def predefined(policy):
    cfg = policy["target_tracking_scaling_policy_configuration"][0]
    spec = cfg.get("predefined_metric_specification") or []
    custom = cfg.get("customized_metric_specification") or []
    return [s["predefined_metric_type"] for s in spec], custom, cfg


class RuntimeShape(unittest.TestCase):
    @classmethod
    def plan(cls, **overrides):
        tree = R.ModuleTree("runtime", R.RUNTIME_VALUES, overrides)
        try:
            return tree.planned(), tree
        finally:
            tree.close()

    @classmethod
    def setUpClass(cls):
        cls.on, _ = cls.plan(container_insights_enabled=True)
        cls.off, _ = cls.plan(container_insights_enabled=False)
        cls.small, _ = cls.plan(container_insights_enabled=False, capacity=R.capacity(256, 1024))

    def test_with_container_insights_the_cluster_setting_is_enabled_and_the_backlog_policy_exists(self):
        self.assertEqual(settings(self.on["aws_ecs_cluster.course"])["containerInsights"], "enabled")
        self.assertIn("aws_appautoscaling_policy.worker_backlog[0]", self.on)

    def test_without_container_insights_the_cluster_setting_is_disabled(self):
        for label, planned in (("committed shape 512/1024", self.off), ("256/1024", self.small)):
            with self.subTest(label):
                self.assertEqual(settings(planned["aws_ecs_cluster.course"]), {"containerInsights": "disabled"})

    def test_without_container_insights_the_worker_backlog_policy_is_absent(self):
        for label, planned in (("committed shape 512/1024", self.off), ("256/1024", self.small)):
            with self.subTest(label):
                self.assertEqual([a for a in planned if "worker_backlog" in a], [])
                self.assertEqual([a for a in planned if a.startswith("aws_appautoscaling_policy")],
                                 ['aws_appautoscaling_policy.http_cpu["%s"]' % s for s in sorted(R.HTTP_SERVICES)])

    def test_the_three_http_cpu_policies_remain_and_use_the_free_predefined_cpu_metric(self):
        for label, planned in (("insights on", self.on), ("insights off", self.off), ("off, 256/1024", self.small)):
            for service in R.HTTP_SERVICES:
                with self.subTest(label=label, service=service):
                    policy = planned['aws_appautoscaling_policy.http_cpu["%s"]' % service]
                    self.assertEqual(policy["policy_type"], "TargetTrackingScaling")
                    types, custom, cfg = predefined(policy)
                    self.assertEqual(types, ["ECSServiceAverageCPUUtilization"])
                    self.assertEqual(custom, [], "a CPU policy must not carry a custom (paid) metric")
                    self.assertEqual(cfg["target_value"], 60)  # cpu_target input
                    self.assertEqual(policy["service_namespace"], "ecs")
                    self.assertEqual(policy["scalable_dimension"], "ecs:service:DesiredCount")

    def test_nothing_in_the_plan_references_the_container_insights_namespace_when_it_is_off(self):
        for label, planned in (("committed shape 512/1024", self.off), ("256/1024", self.small)):
            with self.subTest(label):
                self.assertNotIn(INSIGHTS_NS, json.dumps(planned, sort_keys=True, default=str))
        self.assertIn(INSIGHTS_NS, json.dumps(self.on, sort_keys=True, default=str), "the control case must show the namespace")

    def test_scaling_targets_survive_so_the_worker_stays_at_its_minimum(self):
        for planned in (self.on, self.off, self.small):
            for service in R.SERVICES:
                target = planned['aws_appautoscaling_target.service["%s"]' % service]
                self.assertEqual(target["min_capacity"], 1)
                self.assertEqual(target["scalable_dimension"], "ecs:service:DesiredCount")

    def test_the_smallest_fargate_shape_reaches_every_task_definition(self):
        for service in R.SERVICES:
            with self.subTest(service=service):
                task = self.small['aws_ecs_task_definition.service["%s"]' % service]
                self.assertEqual((task["cpu"], task["memory"]), ("256", "1024"))
                kept = self.off['aws_ecs_task_definition.service["%s"]' % service]
                self.assertEqual((kept["cpu"], kept["memory"]), ("512", "1024"), "the module input, unchanged, reaches the task")

    def test_the_same_resources_exist_in_every_shape_except_the_backlog_policy(self):
        self.assertEqual(set(self.on) - set(self.off), {"aws_appautoscaling_policy.worker_backlog[0]"})
        self.assertEqual(set(self.off) - set(self.on), set())
        self.assertEqual(set(self.off), set(self.small))


class DashboardShape(unittest.TestCase):
    def planned(self, **overrides):
        tree = R.ModuleTree("observability", R.OBSERVABILITY_VALUES, overrides)
        try:
            return tree.planned()
        finally:
            tree.close()

    def test_dashboard_disabled_removes_only_the_dashboard(self):
        on = self.planned(dashboard_enabled=True)
        off = self.planned(dashboard_enabled=False)
        self.assertEqual([a for a in on if "dashboard" in a], ["aws_cloudwatch_dashboard.elasticity[0]"])
        self.assertEqual([a for a in off if "dashboard" in a], [])
        self.assertEqual(set(on) - set(off), {"aws_cloudwatch_dashboard.elasticity[0]"})
        self.assertEqual(set(off) - set(on), set())
        alarms = {re.sub(r"\[.*$", "", a) for a in off if a.startswith("aws_cloudwatch_metric_alarm")}
        self.assertEqual(alarms, {"aws_cloudwatch_metric_alarm.api_errors", "aws_cloudwatch_metric_alarm.latency",
                                  "aws_cloudwatch_metric_alarm.queue_age"})
        self.assertTrue([a for a in off if a.startswith("aws_cloudwatch_log_group")])

    def test_the_module_default_keeps_the_dashboard(self):
        tree = R.ModuleTree("observability", {k: v for k, v in R.OBSERVABILITY_VALUES.items()})
        try:
            self.assertNotIn("dashboard_enabled", tree.values, "the module must not require the variable (default kept)")
            self.assertEqual([a for a in tree.planned() if "dashboard" in a], ["aws_cloudwatch_dashboard.elasticity[0]"])
        finally:
            tree.close()


class RootVariables(unittest.TestCase):
    """The real root `variable` blocks, evaluated by Terraform."""

    NAMES = ["service_capacity", "container_insights_enabled", "dashboard_enabled"]

    @classmethod
    def setUpClass(cls):
        cls.tree = R.VariablesTree(cls.NAMES)
        cls.addClassCleanup(cls.tree.close)

    def accepted(self, **values):
        rc, text, outputs = self.tree.plan(**values)
        self.assertEqual(rc, 0, text[-1500:])
        return outputs

    def refused(self, **values):
        rc, text, _ = self.tree.plan(**values)
        self.assertNotEqual(rc, 0, "the value must be refused:\n" + text[-800:])
        return text

    def test_committed_defaults_are_unchanged(self):
        outputs = self.accepted()
        self.assertIs(outputs["container_insights_enabled"], True)
        self.assertIs(outputs["dashboard_enabled"], True)
        for service in R.SERVICES:
            with self.subTest(service=service):
                got = outputs["service_capacity"][service]
                self.assertEqual((got["cpu"], got["memory"], got["min"]), (512, 1024, 1))
                self.assertEqual(got["max"], 4 if service == "embedding-worker" else 2)
        self.assertEqual(sorted(outputs["service_capacity"]), sorted(R.SERVICES))

    def test_256_cpu_with_1024_or_2048_mib_is_accepted_for_all_four_services(self):
        for memory in (1024, 2048):
            with self.subTest(memory=memory):
                outputs = self.accepted(service_capacity=R.capacity(256, memory))
                for service in R.SERVICES:
                    self.assertEqual(outputs["service_capacity"][service]["cpu"], 256)
                    self.assertEqual(outputs["service_capacity"][service]["memory"], memory)

    def test_other_standard_pairs_are_still_accepted(self):
        for cpu, memory in ((512, 1024), (512, 2048), (1024, 2048)):
            with self.subTest(cpu=cpu, memory=memory):
                self.accepted(service_capacity=R.capacity(cpu, memory))

    def test_256_cpu_with_512_or_4096_mib_is_refused(self):
        for memory in (512, 4096):
            with self.subTest(memory=memory):
                self.refused(service_capacity=R.capacity(256, memory))

    def test_a_single_service_with_a_refused_pair_refuses_the_whole_map(self):
        mixed = R.capacity(256, 1024)
        mixed["graph-service"]["memory"] = 512
        self.refused(service_capacity=mixed)

    def test_pairs_fargate_or_the_one_gib_floor_excludes_are_refused(self):
        for cpu, memory in ((1024, 1024), (512, 512), (2048, 4096), (128, 1024), (256, 3072)):
            with self.subTest(cpu=cpu, memory=memory):
                self.refused(service_capacity=R.capacity(cpu, memory))

    def test_the_bounded_task_counts_are_kept(self):
        too_many_http = R.capacity(256, 1024)
        too_many_http["query-api"]["max"] = 3
        self.refused(service_capacity=too_many_http)
        too_many_workers = R.capacity(256, 1024)
        too_many_workers["embedding-worker"]["max"] = 5
        self.refused(service_capacity=too_many_workers)
        zero_min = R.capacity(256, 1024)
        zero_min["semantic-service"]["min"] = 0
        self.refused(service_capacity=zero_min)
        missing = R.capacity(256, 1024)
        del missing["embedding-worker"]
        self.refused(service_capacity=missing)
        self.accepted(service_capacity=R.capacity(256, 1024, workers_max=4))

    def test_the_switches_accept_booleans_and_refuse_anything_else(self):
        for name in ("container_insights_enabled", "dashboard_enabled"):
            for value in (True, False):
                with self.subTest(name=name, value=value):
                    self.assertIs(self.accepted(**{name: value})[name], value)
            with self.subTest(name=name, value="maybe"):
                self.refused(**{name: "maybe"})

    def test_the_example_tfvars_selects_the_cheap_shape_and_it_is_valid(self):
        """course.local.tfvars.example (the template of the private file) sets the three values uncommented; they must pass."""
        text = EXAMPLE.read_text()
        lines = text.splitlines()
        picked = [ln for ln in lines if re.match(r"^(container_insights_enabled|dashboard_enabled)\s*=", ln)]
        self.assertEqual(len(picked), 2, picked)
        start = next(i for i, ln in enumerate(lines) if re.match(r"^service_capacity\s*=\s*\{", ln))
        end = next(i for i in range(start, len(lines)) if lines[i].startswith("}"))
        block = lines[start:end + 1]
        scratch = self.tree.base / "example.tfvars"
        scratch.write_text("\n".join(picked + block) + "\n")
        from infra_support import run, tf_env, TF_BIN
        done = run([TF_BIN, "plan", "-no-color", "-input=false", "-var-file=" + str(scratch), "-out=" + str(self.tree.base / "e.tfplan")],
                   self.tree.base, tf_env(self.tree.data_dir))
        self.assertEqual(done.returncode, 0, (done.stdout + done.stderr)[-1500:])
        shown = run([TF_BIN, "show", "-json", str(self.tree.base / "e.tfplan")], self.tree.base, tf_env(self.tree.data_dir))
        outputs = {k: v["value"] for k, v in json.loads(shown.stdout)["planned_values"]["outputs"].items()}
        self.assertIs(outputs["container_insights_enabled"], False)
        self.assertIs(outputs["dashboard_enabled"], False)
        for service in R.SERVICES:
            self.assertEqual((outputs["service_capacity"][service]["cpu"], outputs["service_capacity"][service]["memory"]), (256, 1024))
            self.assertEqual(outputs["service_capacity"][service]["min"], 1)


if __name__ == "__main__":
    unittest.main()

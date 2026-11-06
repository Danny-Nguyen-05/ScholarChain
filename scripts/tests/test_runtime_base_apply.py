"""T1 (repair round 4): "runtime live" means the runtime is DEPLOYED, never that a runtime-disabled base apply ran.

The first base apply (runtime disabled, image_revision = null) already leaves module.runtime.aws_ecs_cluster.course, the
service-discovery namespace and the four ECR repositories in the state, because modules/runtime declares them without a
count. Only the ECS services, the query load balancer, its target group and its listener (and their gated dependents)
exist once the runtime is deployed. These tests use a realistic post-base-apply state (helpers.post_base_apply_resources)
and prove:

  (a) the runtime-disabled infrastructure rollback (no binding) is ACCEPTED on it (dry run and the execute path);
  (b) a --deployed-manifest or --deployed-push-record binding is REFUSED on it at STEP runtime-state with "would CREATE
      the runtime", before any registry or plan call (and deploy.sh refuses the carried apply the same way);
  (c) a base-apply plan that keeps (no-op or update) the cluster passes runtime-preservation on it, while a live runtime
      still refuses a delete or replace of the cluster;
  (d) a realistic live state (post-base-apply plus the deployed runtime) behaves as the round-3 live fixture;
  plus the ambiguous PARTIAL state (some indicators, not all), which is refused fail-closed with a STEP marker,
  and a source-derived check that the pinned indicator types are exactly gated resources of the Terraform source.

Everything runs against the fake aws, terraform and docker executables: no cloud, no real state, no real Terraform.
"""
import json
import os
import re
import subprocess
import sys
import unittest

import test_runtime_rollback as s1
from helpers import (
    REAL_REPO,
    SCRIPTS_DIR,
    SERVICES,
    STATE_ATTRIBUTE_CANARY,
    deployed_runtime_resources,
    live_after_runtime_apply_resources,
    post_base_apply_resources,
)

LIB = os.path.join(SCRIPTS_DIR, "lib")
RUNTIME_SOURCE = os.path.join(REAL_REPO, "infra", "terraform", "modules", "runtime")
CLUSTER = "module.runtime.aws_ecs_cluster.course"
ECR = 'module.runtime.aws_ecr_repository.service["%s"]'
NAMESPACE = "module.runtime.aws_service_discovery_private_dns_namespace.course"
TARGET_GROUP = "module.runtime.aws_lb_target_group.query[0]"


def parse_conf():
    conf = {}
    with open(os.path.join(SCRIPTS_DIR, "config", "release.conf"), encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line.rstrip("\n"))
            if match:
                conf[match.group(1)] = match.group(2)
    return conf


CONF = parse_conf()
INDICATORS = CONF["RUNTIME_LIVE_INDICATOR_TYPES"]
PROTECTED = CONF["RUNTIME_LIVE_PROTECTED_TYPES"]
MODULE = CONF["RUNTIME_LIVE_MODULE"]


def indicator_types():
    return [entry.split("=", 1)[0] for entry in INDICATORS.split(",")]


def run_verify(*args):
    completed = subprocess.run([sys.executable, "-I", os.path.join(LIB, "verify.py")] + list(args), capture_output=True, text=True)
    return completed.returncode, completed.stdout + completed.stderr


# The partial (ambiguous) states: some, but not all, of the deployed-runtime resources.
PARTIAL_STATES = {
    "a load balancer and target group but no ECS service": dict(services=()),
    "only three of the four ECS services": dict(services=SERVICES[:3]),
    "only one ECS service": dict(services=SERVICES[:1]),
    "the four services but no load balancer or target group": dict(load_balancer=False, target_group=False, listener=False),
    "a load balancer without its target group": dict(target_group=False),
    "a target group without its load balancer": dict(load_balancer=False, listener=False),
}


def partial_state(**parts):
    return post_base_apply_resources() + deployed_runtime_resources(**parts)


# ---------------------------------------------------------------------------------------------------------------------
# The pinned classification is derived from the Terraform source, not assumed.
# ---------------------------------------------------------------------------------------------------------------------

def runtime_resource_gating():
    """{type: gated?} for every resource of modules/runtime: gated means its count/for_each depends on image_revision
    (directly, or through local.active_services / local.http_services, which are themselves checked)."""
    text = ""
    for name in sorted(os.listdir(RUNTIME_SOURCE)):
        if name.endswith(".tf"):
            with open(os.path.join(RUNTIME_SOURCE, name), encoding="utf-8") as handle:
                text += handle.read() + "\n"
    gated_locals = set()
    for local_name in ("active_services", "http_services"):
        match = re.search(r"^\s*%s\s*=\s*(.+)$" % local_name, text, re.M)
        if match and "image_revision != null" in match.group(1):
            gated_locals.add("local." + local_name)
    gating = {}
    headers = list(re.finditer(r'^resource "([a-z0-9_]+)" "([a-z0-9_]+)" \{$', text, re.M))
    for index, header in enumerate(headers):
        body_end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[header.end():body_end]
        meta = re.search(r"^\s*(count|for_each)\s*=\s*(.+)$", body, re.M)
        expression = meta.group(2) if meta else ""
        gated = "image_revision != null" in expression or any(name in expression for name in gated_locals)
        gating.setdefault(header.group(1), set()).add(gated)
    return gating, gated_locals


class SourceDerivedClassificationTests(unittest.TestCase):
    def setUp(self):
        self.gating, self.gated_locals = runtime_resource_gating()

    def test_the_locals_that_gate_the_services_depend_on_the_image_revision(self):
        self.assertEqual(self.gated_locals, {"local.active_services", "local.http_services"})

    def test_every_indicator_type_exists_only_when_the_runtime_is_deployed(self):
        for rtype in indicator_types():
            with self.subTest(rtype):
                self.assertIn(rtype, self.gating, "indicator type not declared in modules/runtime")
                self.assertEqual(self.gating[rtype], {True}, "%s must be count/for_each-gated on image_revision" % rtype)

    def test_the_base_apply_resources_are_ungated_and_are_not_indicators(self):
        ungated = {t for t, flags in self.gating.items() if flags == {False}}
        self.assertEqual(ungated, {"aws_ecs_cluster", "aws_service_discovery_private_dns_namespace", "aws_ecr_repository"})
        self.assertFalse(ungated & set(indicator_types()))

    def test_the_runtime_module_block_itself_has_no_count(self):
        with open(os.path.join(REAL_REPO, "infra", "terraform", "main.tf"), encoding="utf-8") as handle:
            text = handle.read()
        block = re.search(r'^module "runtime" \{$(.*?)^\}$', text, re.M | re.S).group(1)
        self.assertIsNone(re.search(r"^\s*(count|for_each)\s*=", block, re.M), "a disabled base apply still creates the cluster")

    def test_protected_types_are_the_indicator_types_plus_the_cluster(self):
        self.assertEqual(set(PROTECTED.split(",")), set(indicator_types()) | {"aws_ecs_cluster"})
        self.assertNotIn("aws_ecs_task_definition", PROTECTED.split(","), "a new revision legitimately replaces task definitions")

    def test_the_post_base_apply_fixture_holds_exactly_the_ungated_runtime_types(self):
        ungated = {t for t, flags in self.gating.items() if flags == {False}}
        fixture = {r["type"] for r in post_base_apply_resources() if r["module"] == "module.runtime"}
        self.assertEqual(fixture, ungated)
        deployed = {r["type"] for r in deployed_runtime_resources()}
        self.assertTrue(deployed <= {t for t, flags in self.gating.items() if flags == {True}})

    def test_the_new_keys_are_pinned(self):
        with open(os.path.join(LIB, "common.sh"), encoding="utf-8") as handle:
            pinned = re.search(r'SC_PINNED_KEYS="([^"]*)"', handle.read()).group(1).split()
        for key in ("RUNTIME_LIVE_MODULE", "RUNTIME_LIVE_INDICATOR_TYPES", "RUNTIME_LIVE_PROTECTED_TYPES"):
            self.assertIn(key, pinned)
            self.assertIn(key, CONF)


# ---------------------------------------------------------------------------------------------------------------------
# verify.py on the realistic states
# ---------------------------------------------------------------------------------------------------------------------

class StateFiles(unittest.TestCase):
    def setUp(self):
        import shutil
        import tempfile

        self.tmp = tempfile.mkdtemp(prefix="sc-t1-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def put(self, name, document):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return path

    def state(self, resources, name="terraform.tfstate"):
        return self.put(name, {"version": 4, "serial": 3, "lineage": "l", "outputs": {}, "resources": resources})

    def live(self, path, indicators=INDICATORS, types=PROTECTED):
        args = ["runtime-live", "--state", path, "--module", MODULE, "--indicators", indicators]
        if types is not None:
            args += ["--types", types]
        return run_verify(*args)

    def preserve(self, state, actions=None, show=None, expect="any", indicators=INDICATORS):
        args = ["runtime-preservation", "--state", state, "--module", MODULE, "--indicators", indicators, "--types", PROTECTED, "--expect", expect]
        if show is not None:
            path = self.put("show.json", {"resource_changes": [{"address": a, "type": t, "change": {"actions": acts}} for a, t, acts in show]})
            return run_verify(*(args + ["--show-json", path]))
        return run_verify(*(args + ["--receipt", self.put("receipt.json", {"actions": actions or []})]))


class RuntimeLiveOnRealisticStatesTests(StateFiles):
    def test_the_post_base_apply_state_is_not_live(self):
        rc, out = self.live(self.state(post_base_apply_resources()))
        self.assertEqual(rc, 0, out)
        self.assertIn("RUNTIME-LIVE: no (0 deployed-runtime indicator instance(s) of module.runtime", out)
        self.assertIn("the ECS cluster and ECR repositories of a runtime-disabled base apply are not indicators", out)
        self.assertNotIn(STATE_ATTRIBUTE_CANARY, out)

    def test_the_state_after_a_runtime_apply_is_live_with_or_without_the_listener(self):
        for listener in (True, False):
            with self.subTest(listener=listener):
                rc, out = self.live(self.state(live_after_runtime_apply_resources(listener=listener)))
                self.assertEqual(rc, 0, out)
                self.assertIn("RUNTIME-LIVE: yes (%d deployed-runtime indicator instance(s)" % (6 + int(listener)), out)
                self.assertNotIn(STATE_ATTRIBUTE_CANARY, out)

    def test_a_partial_runtime_fails_closed(self):
        cases = dict(PARTIAL_STATES)
        cases["a lone listener"] = dict(services=(), load_balancer=False, target_group=False)
        for label, parts in cases.items():
            with self.subTest(label):
                rc, out = self.live(self.state(partial_state(**parts)))
                self.assertEqual(rc, 1, out)
                self.assertIn("RUNTIME-LIVE: partial", out)
                self.assertIn("a complete runtime has aws_ecs_service=4 aws_lb=1 aws_lb_target_group=1 aws_lb_listener=0-1", out)
                self.assertTrue(out.rstrip().splitlines()[-1].startswith("RUNTIME-LIVE-CHECK-FAILED: the live state holds an INCOMPLETE runtime"), out)

    def test_an_extra_service_instance_is_not_a_complete_runtime(self):
        resources = live_after_runtime_apply_resources()
        for resource in resources:
            if resource["type"] == "aws_ecs_service":
                resource["instances"].append({"index_key": "unexpected-service"})
        rc, out = self.live(self.state(resources))
        self.assertEqual(rc, 1, out)
        self.assertIn("RUNTIME-LIVE: partial", out)

    def test_a_malformed_or_inconsistent_configuration_is_a_usage_error(self):
        state = self.state(post_base_apply_resources())
        for label, indicators, types, needle in (
            ("empty", "", PROTECTED, "empty or malformed"),
            ("no count", "aws_ecs_service,aws_lb", PROTECTED, "empty or malformed"),
            ("inverted range", "aws_ecs_service=4,aws_lb_listener=1-0", PROTECTED, "empty or malformed"),
            ("nothing required", "aws_lb_listener=0-1", PROTECTED, "empty or malformed"),
            ("repeated", "aws_ecs_service=4,aws_ecs_service=4", PROTECTED, "empty or malformed"),
            ("an indicator that is not protected", INDICATORS + ",aws_ecs_task_definition=4", PROTECTED, "not protected types"),
        ):
            with self.subTest(label):
                rc, out = self.live(state, indicators=indicators, types=types)
                self.assertEqual(rc, 2, out)
                self.assertIn(needle, out)
                rc, out = self.preserve(state, indicators=indicators)
                self.assertEqual(rc, 2, out)
                self.assertIn("RUNTIME-PRESERVATION-FAILED", out)


class RuntimePreservationOnRealisticStatesTests(StateFiles):
    def test_c_a_base_apply_plan_that_keeps_the_cluster_passes_on_the_post_base_apply_state(self):
        state = self.state(post_base_apply_resources())
        update = [{"address": CLUSTER, "type": "aws_ecs_cluster", "actions": "update"}, {"address": ECR % "query-api", "type": "aws_ecr_repository", "actions": "update"}]
        for expect in ("any", "not-live"):
            with self.subTest(expect=expect, source="receipt, cluster updated"):
                rc, out = self.preserve(state, actions=update, expect=expect)
                self.assertEqual(rc, 0, out)
                self.assertIn("RUNTIME-LIVE: no", out)
                self.assertIn("runtime preservation ok: the bound state shows no live runtime; nothing to preserve", out)
            with self.subTest(expect=expect, source="receipt, cluster no-op (a receipt lists no no-op)"):
                rc, out = self.preserve(state, actions=[], expect=expect)
                self.assertEqual(rc, 0, out)
            with self.subTest(expect=expect, source="show -json"):
                rc, out = self.preserve(state, show=[(CLUSTER, "aws_ecs_cluster", ["no-op"]), (NAMESPACE, "aws_service_discovery_private_dns_namespace", ["update"])], expect=expect)
                self.assertEqual(rc, 0, out)

    def test_c_a_live_runtime_still_refuses_a_cluster_delete_or_replace(self):
        state = self.state(live_after_runtime_apply_resources())
        for verbs, word in (("delete", "delete"), ("create+delete", "replace"), ("delete+create", "replace")):
            with self.subTest(verbs=verbs):
                rc, out = self.preserve(state, actions=[{"address": CLUSTER, "type": "aws_ecs_cluster", "actions": verbs}])
                self.assertEqual(rc, 1, out)
                self.assertIn("RUNTIME-PRESERVATION-FAILED: the plan would %s the live runtime resource %s" % (word, CLUSTER), out)
        rc, out = self.preserve(state, show=[(CLUSTER, "aws_ecs_cluster", ["delete", "create"])])
        self.assertEqual(rc, 1, out)
        self.assertIn("would replace the live runtime resource %s" % CLUSTER, out)
        rc, out = self.preserve(state, actions=[{"address": CLUSTER, "type": "aws_ecs_cluster", "actions": "update"}], expect="live")
        self.assertEqual(rc, 0, out)
        self.assertIn("deletes or replaces no protected resource of the live runtime", out)

    def test_the_cluster_is_protected_only_while_the_runtime_is_live(self):
        """The acceptance boundary: with no deployed runtime there is nothing running on the cluster to preserve."""
        state = self.state(post_base_apply_resources())
        rc, out = self.preserve(state, actions=[{"address": CLUSTER, "type": "aws_ecs_cluster", "actions": "create+delete"}])
        self.assertEqual(rc, 0, out)
        self.assertIn("nothing to preserve", out)

    def test_b_a_carry_on_the_post_base_apply_state_would_create_the_runtime(self):
        rc, out = self.preserve(self.state(post_base_apply_resources()), actions=[], expect="live")
        self.assertEqual(rc, 1, out)
        self.assertIn("shows no live runtime", out)
        self.assertIn("would CREATE the runtime", out)

    def test_a_partial_runtime_is_refused_whatever_the_plan_and_the_expectation(self):
        for label, parts in PARTIAL_STATES.items():
            state = self.state(partial_state(**parts))
            for expect in ("any", "live", "not-live"):
                with self.subTest(label, expect=expect):
                    rc, out = self.preserve(state, actions=[], expect=expect)
                    self.assertEqual(rc, 1, out)
                    self.assertIn("RUNTIME-LIVE: partial", out)
                    self.assertIn("RUNTIME-PRESERVATION-FAILED: the live state holds an INCOMPLETE runtime", out)
                    self.assertNotIn("runtime preservation ok", out)


# ---------------------------------------------------------------------------------------------------------------------
# rollback.sh on the realistic states
# ---------------------------------------------------------------------------------------------------------------------

class RollbackOnPostBaseApplyStateBase(s1.RollbackKeepsRuntimeBase):
    def setUp(self):
        super().setUp()
        self.set_live_state(post_base_apply_resources())
        # A runtime-disabled plan of the previous source on this state: no image revision; it keeps the cluster (update),
        # leaves the ECR repositories and the namespace alone (no-op) and changes a non-runtime resource.
        self.disabled_changes = [
            (CLUSTER, "aws_ecs_cluster", ["update"]),
            (ECR % "query-api", "aws_ecr_repository", ["no-op"]),
            (NAMESPACE, "aws_service_discovery_private_dns_namespace", ["no-op"]),
            ("module.network.aws_vpc.course", "aws_vpc", ["update"]),
        ]
        self.use_show(self.disabled_changes, revision=None, name="disabled-show.json")

    def deploy_line(self, result):
        return [l for l in result.stdout.splitlines() if l.startswith("DRY-RUN CMD:") and "scripts/deploy.sh" in l][0]


class RollbackOnPostBaseApplyStateTests(RollbackOnPostBaseApplyStateBase):
    def test_a_the_runtime_disabled_dry_run_is_accepted_and_reaches_the_plan_step(self):
        result = self.rb(binding=None, execute=False)
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: DRY-RUN"))
        steps = result.steps()
        for step in ("previous-commit", "runtime-state", "delegate-plan", "delegate-deploy"):
            self.assertIn(step, steps)
        self.assertLess(steps.index("runtime-state"), steps.index("delegate-plan"))
        self.assertNotIn("deployed-revision", steps)
        self.assertIn("RUNTIME-LIVE: no (0 deployed-runtime indicator instance(s)", result.stdout)
        self.assertNotIn("-var=image_revision", result.stdout)
        line = self.deploy_line(result)
        self.assertIn("--stage base-apply", line)
        self.assertIn("--skip-runtime-archive", line)
        self.assertNotIn("--image-revision", line)
        self.assertNotIn("--reuse-images", line)
        self.assertNotIn(STATE_ATTRIBUTE_CANARY, result.out)
        self.nothing_ran()

    def test_a_the_runtime_disabled_execute_path_plans_without_an_image_revision_and_deploys(self):
        result = self.rb("plan", binding=None)
        self.assertEqual(result.rc, 0, result.out[-2500:])
        plans = [a for n, a in self.calls("terraform") if " plan " in " " + a + " "]
        self.assertEqual(len(plans), 1)
        self.assertNotIn("image_revision", plans[0])
        self.assertIn("/source/%s/infra/terraform " % self.prev_commit, plans[0])
        self.assertEqual([a for n, a in self.calls("aws") if a.startswith("ecr")], [], "no registry call without a binding")
        self.assertIn("STEP: runtime-preservation", result.stdout)
        self.assertIn("runtime preservation ok: the bound state shows no live runtime; nothing to preserve", result.stdout)
        self.assertEqual(self.mutating_calls(), [])
        plan = self.plan_of(result)
        with open(plan + ".receipt.json") as handle:
            receipt = json.load(handle)
        self.assertIsNone(receipt["image_revision"])
        self.assertEqual(receipt["commit"], self.prev_commit)
        self.assertIn({"address": CLUSTER, "type": "aws_ecs_cluster", "actions": "update"}, receipt["actions"])
        # Stage deploy after the human's NEW base-apply approval record (APPROVED_STAGE=base-apply, APPROVED_COMMIT=PREV).
        prespend, prespend_sha = self.write_prespend()
        record = self.approval_text(s1._sha256(plan), commit=self.prev_commit, prespend_sha=prespend_sha, stage="base-apply", receipt_sha=self.receipt_sha(plan))
        approval = {"approval": self.write_approval(record, name="base-gate.md"), "prespend": prespend}
        before = len(self.calls())
        deployed = self.deploy_stage(plan, approval, binding=None)
        self.assertEqual(deployed.rc, 0, deployed.out[-2500:])
        self.assertIn("runtime preservation ok: the bound state shows no live runtime; nothing to preserve", deployed.out)
        self.assertEqual(len(self.applied()), 1)
        self.assertEqual(self.applied()[0][1], s1._sha256(plan))
        stage_calls = self.calls()[before:]
        self.assertEqual(self.calls("docker"), [])
        self.assertEqual([a for n, a in stage_calls if n == "aws" and (a.startswith("ecr") or a.startswith("ecs") or a.startswith("s3"))], [])

    def test_b_a_manifest_or_push_record_binding_is_refused_because_it_would_create_the_runtime(self):
        for binding in ("manifest", "push"):
            for execute in (False, True):
                with self.subTest(binding=binding, execute=execute):
                    open(self.log, "w").close()
                    result = self.rb("plan" if execute else None, binding=binding, execute=execute)
                    self.assertEqual(result.rc, 3, result.out)
                    self.assertEqual(result.steps()[-1], "runtime-state")
                    self.assertIn("RESULT: REFUSED step=runtime-state", result.stdout)
                    self.assertIn("would CREATE the runtime", result.stdout)
                    self.assertIn("the ECS cluster and ECR repositories of a runtime-disabled base apply do not count", result.stdout)
                    self.assertNotIn("deployed-revision", result.steps())
                    self.nothing_ran()

    def test_the_indicator_pin_cannot_be_overridden_from_the_environment(self):
        result = self.rb("plan", binding="push", RUNTIME_LIVE_INDICATOR_TYPES="aws_ecs_cluster=1", RUNTIME_LIVE_PROTECTED_TYPES="aws_ecs_cluster")
        self.assertIn("CONFIG-IGNORED", result.stdout)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "runtime-state")
        self.assertIn("would CREATE the runtime", result.stdout)
        self.nothing_ran()


class RollbackOnPartialStateTests(RollbackOnPostBaseApplyStateBase):
    def test_a_partial_runtime_is_refused_at_runtime_state_with_or_without_a_binding(self):
        for label, parts in PARTIAL_STATES.items():
            self.set_live_state(partial_state(**parts))
            for binding in (None, "manifest", "push"):
                for execute in (False, True):
                    with self.subTest(label, binding=binding, execute=execute):
                        open(self.log, "w").close()
                        result = self.rb("plan" if execute else None, binding=binding, execute=execute)
                        self.assertEqual(result.rc, 3, result.out)
                        self.assertEqual(result.steps()[-1], "runtime-state")
                        self.assertIn("RUNTIME-LIVE: partial", result.stdout)
                        self.assertIn("RESULT: REFUSED step=runtime-state reason=RUNTIME-LIVE-CHECK-FAILED: the live state holds an INCOMPLETE runtime", result.stdout)
                        self.nothing_ran()


class RollbackOnRealisticLiveStateTests(RollbackOnPostBaseApplyStateBase):
    """(d) on a realistic live state (post-base-apply plus the deployed runtime) the round-3 behaviour holds."""

    def setUp(self):
        super().setUp()
        self.set_live_state(live_after_runtime_apply_resources())
        self.use_show(s1.KEEP)

    def test_d_no_binding_is_refused_and_a_binding_keeps_the_runtime(self):
        result = self.rb("plan", binding=None)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "runtime-state")
        self.assertIn("a plan without one would delete the runtime", result.out)
        self.nothing_ran()
        for binding in ("manifest", "push"):
            with self.subTest(binding=binding):
                result = self.rb(binding=binding, execute=False)
                self.assertEqual(result.rc, 0, result.out)
                self.assertIn("RUNTIME-LIVE: yes (7 deployed-runtime indicator instance(s)", result.stdout)
                self.assertIn("-var=image_revision=%s" % s1.REV, result.stdout)
                self.assertIn("--stage runtime-apply", self.deploy_line(result))

    def test_d_without_a_certificate_the_runtime_is_still_live(self):
        self.set_live_state(live_after_runtime_apply_resources(listener=False))
        result = self.rb(execute=False)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("RUNTIME-LIVE: yes (6 deployed-runtime indicator instance(s)", result.stdout)

    def test_c_a_carried_plan_that_replaces_the_cluster_is_refused_when_planning(self):
        self.use_show(s1.KEEP + [(CLUSTER, "aws_ecs_cluster", ["delete", "create"])], name="cluster-show.json")
        result = self.rb("plan")
        self.assertEqual(result.rc, 3, result.out[-2500:])
        self.assertEqual(result.steps()[-1], "runtime-preservation")
        self.assertIn("RUNTIME-PRESERVATION-FAILED: the plan would replace the live runtime resource %s" % CLUSTER, result.stdout)
        self.assertEqual(self.mutating_calls(), [])


# ---------------------------------------------------------------------------------------------------------------------
# deploy.sh on the realistic states
# ---------------------------------------------------------------------------------------------------------------------

class DeployOnRealisticStatesBase(s1.CarryDeployBase):
    def arrange_base(self, changes, at_head=False):
        """A base-apply plan (no image revision) of the previous source (a rollback) or of HEAD (a re-run of step 1)."""
        commit = self.new_head if at_head else self.prev_commit
        self.stage = "base-apply"
        self.revision = None
        self.plan, self.plan_sha = self.make_plan(name="base.tfplan")
        self.show = self.write_show_json(changes, name="base-show.json")
        self.receipt = self.write_plan_receipt(self.plan, self.plan_sha, commit=commit, scripts_commit=self.new_head, image_revision=None, actions=s1.receipt_actions(changes))
        self.receipt_sha_value = self.receipt_sha(self.plan)
        self.approval = self.write_approval(self.approval_text(self.plan_sha, commit=commit, prespend_sha=self.prespend_sha, stage="base-apply", receipt_sha=self.receipt_sha_value), name="base-gate.md")
        self.base_env["FAKE_SHOW_JSON"] = self.show

    def base_args(self, at_head=False):
        return (["--source-commit", self.prev_commit] if not at_head else []) + ["--skip-runtime-archive"]


KEEPS_THE_CLUSTER = [
    (CLUSTER, "aws_ecs_cluster", ["update"]),
    (ECR % "query-api", "aws_ecr_repository", ["no-op"]),
    ("module.network.aws_vpc.course", "aws_vpc", ["update"]),
]
CLUSTER_NOOP = [(CLUSTER, "aws_ecs_cluster", ["no-op"]), ("module.dynamodb.aws_dynamodb_table.table[\"RunLedger\"]", "aws_dynamodb_table", ["update"])]


class DeployOnPostBaseApplyStateTests(DeployOnRealisticStatesBase):
    def setUp(self):
        super().setUp()
        self.set_live_state(post_base_apply_resources())
        self.arrange_carry()

    def test_c_a_base_apply_that_keeps_the_cluster_passes_runtime_preservation(self):
        for label, changes in (("cluster updated", KEEPS_THE_CLUSTER), ("cluster no-op", CLUSTER_NOOP)):
            for at_head in (False, True):
                with self.subTest(label, at_head=at_head):
                    open(self.log, "w").close()
                    if os.path.exists(self.log + ".applied"):
                        os.remove(self.log + ".applied")
                    self.arrange_base(changes, at_head=at_head)
                    dry = self.deploy(*self.base_args(at_head))
                    self.assertEqual(dry.rc, 0, dry.out[-2000:])
                    self.assertIn("STEP: runtime-preservation", dry.stdout)
                    self.assertIn("RUNTIME-LIVE: no", dry.stdout)
                    self.assertIn("runtime preservation ok: the bound state shows no live runtime; nothing to preserve", dry.stdout)
                    result = self.execute(*self.base_args(at_head))
                    self.assertEqual(result.rc, 0, result.out[-2000:])
                    self.assertEqual(result.stdout.count("runtime preservation ok"), 2, "the receipt and the verified plan's show -json")
                    self.assertEqual(len(self.applied()), 1)
                    self.assertNotIn(STATE_ATTRIBUTE_CANARY, result.out)

    def test_b_the_carried_apply_on_the_post_base_apply_state_is_refused_before_anything_runs(self):
        for label, args in (("manifest", self.manifest_args()), ("push record", self.record_args())):
            with self.subTest(label):
                open(self.log, "w").close()
                for result in (self.deploy(*args), self.execute(*args)):
                    self.assertEqual(result.rc, 3, result.out)
                    self.assertEqual(result.steps()[-1], "runtime-preservation")
                    self.assertIn("would CREATE the runtime", result.stdout)
                    self.assertEqual(self.applied(), [])
                    self.assertEqual(self.mutating_calls(), [])


class DeployOnRealisticLiveStateTests(DeployOnRealisticStatesBase):
    def setUp(self):
        super().setUp()
        self.set_live_state(live_after_runtime_apply_resources())
        self.arrange_carry()

    def test_d_the_carried_apply_keeps_the_runtime(self):
        result = self.execute(*self.manifest_args())
        self.assertEqual(result.rc, 0, result.out[-2500:])
        self.assertIn("deletes or replaces no protected resource of the live runtime", result.out)
        self.assertEqual(len(self.applied()), 1)

    def test_c_a_base_apply_that_replaces_or_deletes_the_cluster_is_refused_while_the_runtime_is_live(self):
        for verbs in (["delete"], ["delete", "create"], ["create", "delete"]):
            with self.subTest(verbs=verbs):
                open(self.log, "w").close()
                self.arrange_base([(CLUSTER, "aws_ecs_cluster", verbs)])
                for result in (self.deploy(*self.base_args()), self.execute(*self.base_args())):
                    self.assertEqual(result.rc, 3, result.out[-2000:])
                    self.assertEqual(result.steps()[-1], "runtime-preservation")
                    self.assertIn("the live runtime resource %s" % CLUSTER, result.stdout)
                    self.assertEqual(self.applied(), [])

    def test_c_a_cluster_replace_hidden_from_the_receipt_is_caught_in_the_verified_plan(self):
        self.arrange_base([(CLUSTER, "aws_ecs_cluster", ["update"])])
        self.base_env["FAKE_SHOW_JSON"] = self.write_show_json([(CLUSTER, "aws_ecs_cluster", ["delete", "create"])], name="hidden-show.json")
        dry = self.deploy(*self.base_args())
        self.assertIn("RUNTIME-LIVE: yes", dry.stdout)
        result = self.execute(*self.base_args())
        self.assertEqual(result.rc, 3, result.out[-2000:])
        self.assertEqual(result.steps()[-1], "runtime-preservation")
        self.assertIn("would replace the live runtime resource %s" % CLUSTER, result.stdout)
        self.assertEqual(self.applied(), [])


class DeployOnPartialStateTests(DeployOnRealisticStatesBase):
    def test_a_partial_runtime_refuses_the_base_apply_and_the_carried_apply(self):
        for label, parts in PARTIAL_STATES.items():
            self.set_live_state(partial_state(**parts))
            with self.subTest(label, stage="base-apply"):
                open(self.log, "w").close()
                self.arrange_base(KEEPS_THE_CLUSTER)
                for result in (self.deploy(*self.base_args()), self.execute(*self.base_args())):
                    self.assertEqual(result.rc, 3, result.out[-2000:])
                    self.assertEqual(result.steps()[-1], "runtime-preservation")
                    self.assertIn("RUNTIME-PRESERVATION-FAILED: the live state holds an INCOMPLETE runtime", result.stdout)
                    self.assertEqual(self.applied(), [])
            with self.subTest(label, stage="runtime-apply carry"):
                open(self.log, "w").close()
                self.arrange_carry()
                result = self.execute(*self.manifest_args())
                self.assertEqual(result.rc, 3, result.out[-2000:])
                self.assertEqual(result.steps()[-1], "runtime-preservation")
                self.assertIn("INCOMPLETE runtime", result.stdout)
                self.assertEqual(self.applied(), [])


if __name__ == "__main__":
    unittest.main()

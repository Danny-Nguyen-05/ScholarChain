"""S1 (repair round 3): an infrastructure rollback keeps a RUNNING runtime.

The fixture is a POPULATED local state with the runtime enabled (the ECS cluster, four services, the query load balancer
and its listener are in the state file). `rollback.sh --mode infra` then carries the CURRENTLY DEPLOYED image revision, bound
to a verified previous deploy manifest or to a push record of that revision; the registry digests are compared with it
before apply; the plan's image_revision must equal the bound revision; a plan that deletes or replaces a runtime-class
resource of the live runtime is refused; after apply all four ECS services must reference the bound revision.

Everything runs against the fake aws, terraform and docker executables: no cloud, no real state, no real Terraform.
"""
import json
import os
import re
import unittest

from helpers import FAKE_ACCOUNT, REGION, SERVICES, account_hash, registry_digest
from test_deploy import DeployBase
from test_rollback import RollbackBase, _sha256

REV = "d" * 40
OTHER_REV = "e" * 40
SVC_ADDRESS = 'module.runtime.aws_ecs_service.service["%s"]'
LISTENER = "module.runtime.aws_lb_listener.https[0]"
LOAD_BALANCER = "module.runtime.aws_lb.query[0]"


def live_runtime_state():
    """The resources a state holds while the runtime is deployed (module path, type and instances only)."""
    def block(rtype, name, instances, module="module.runtime"):
        return {"module": module, "mode": "managed", "type": rtype, "name": name, "instances": [{"index_key": i} for i in instances]}

    return [
        block("aws_ecs_cluster", "course", [None]),
        block("aws_ecs_service", "service", SERVICES),
        block("aws_lb", "query", [0]),
        block("aws_lb_listener", "https", [0]),
        block("aws_lb_target_group", "query", [0]),
        block("aws_ecs_task_definition", "service", SERVICES),
        block("aws_ecr_repository", "service", SERVICES),
        block("aws_s3_bucket", "evidence", [None], module="module.datalake"),
    ]


def keep_changes():
    """A plan that keeps the runtime: in-place updates of the services, the load balancer and the listener, and a task
    definition replacement (a new revision legitimately replaces it)."""
    changes = [(SVC_ADDRESS % s, "aws_ecs_service", ["update"]) for s in SERVICES]
    changes += [(LOAD_BALANCER, "aws_lb", ["update"]), (LISTENER, "aws_lb_listener", ["update"])]
    changes += [('module.runtime.aws_ecs_task_definition.service["%s"]' % s, "aws_ecs_task_definition", ["create", "delete"]) for s in SERVICES]
    return changes


def receipt_actions(changes):
    return [{"address": a, "type": t, "actions": "+".join(acts)} for a, t, acts in changes if acts not in (["no-op"], ["read"])]


KEEP = keep_changes()
DELETES_A_SERVICE = KEEP + [(SVC_ADDRESS % "query-api", "aws_ecs_service", ["delete"])]
REPLACES_THE_LISTENER = [c for c in KEEP if c[0] != LISTENER] + [(LISTENER, "aws_lb_listener", ["create", "delete"])]
DELETES_THE_LOAD_BALANCER = KEEP + [(LOAD_BALANCER, "aws_lb", ["delete"])]


class RuntimeFixtureMixin:
    def push_record_with(self, **fields):
        """The push record of REV with some top-level fields replaced (including `commit`, which write_push_record names itself)."""
        path = self.write_push_record(commit=REV)
        with open(path) as handle:
            document = json.load(handle)
        document.update(fields)
        with open(path, "w") as handle:
            json.dump(document, handle)
        return path

    def set_live_state(self, resources=None):
        self.write_state(extra={"resources": live_runtime_state() if resources is None else resources})

    def write_runtime_manifest(self, revision=REV, name="deployed-manifest.json", **overrides):
        document = {
            "schema": "scholarchain.deploy-manifest.v1",
            "stage": "runtime-apply",
            "commit": revision,
            "image_revision": revision,
            "region": REGION,
            "account_sha256": account_hash(),
            "plan_sha256": "a" * 64,
            "run_id": "earlier-run",
            "images": [{"service": s, "repository": "scholarchain-course/%s" % s, "tag": revision, "registry_digest": registry_digest(s, revision)} for s in SERVICES],
            "ecs_services": [{"service": s, "task_definition": "arn:aws:ecs:%s:<acct>:task-definition/scholarchain-course-%s:7" % (REGION, s)} for s in SERVICES],
        }
        for key, value in overrides.items():
            document[key] = value
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return path


class RollbackKeepsRuntimeBase(RuntimeFixtureMixin, RollbackBase):
    def setUp(self):
        super().setUp()
        self.prev_commit = self.head()
        self.write("infra/terraform/modules/runtime/newer.tf", "# added after the rollback target\n")
        self.new_head = self.commit("newer tree")
        self.set_live_state()
        self.deployed = self.write_runtime_manifest()
        self.push_record = self.write_push_record(commit=REV)
        self.env_all["FAKE_ECS_TAG"] = REV
        self.use_show(KEEP)

    def use_show(self, changes, revision=REV, name="rb-show.json"):
        self.env_all["FAKE_SHOW_JSON"] = self.write_show_json(changes, image_revision=revision, name=name)

    def rb(self, stage=None, *extra, binding="manifest", execute=True, **env):
        args = ["--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", self.prev_commit]
        if binding == "manifest":
            args += ["--deployed-manifest", self.deployed]
        elif binding == "push":
            args += ["--deployed-push-record", self.push_record]
        if stage:
            args += ["--stage", stage]
        args += list(extra)
        if execute:
            args += ["--profile", "approved", "--execute"]
        return self.rollback(*args, **env)

    @staticmethod
    def plan_of(result):
        """rollback.sh --stage plan echoes plan.sh prefixed; its own RESULT line names the plan file."""
        match = re.search(r"RESULT: PASS rollback plan recorded at (\S+?);", result.stdout)
        if not match:
            raise AssertionError("no rollback plan path in: " + result.stdout[-400:])
        return match.group(1)

    def refused_in(self, result, step):
        """A refusal printed by the delegated deploy.sh: rollback.sh echoes it prefixed, so match the RESULT line."""
        self.assertEqual(result.rc, 3, result.out[-2500:])
        self.assertIn("RESULT: REFUSED step=%s" % step, result.out)

    def non_version_calls(self):
        return [c for c in self.calls() if not c[1].startswith("version")]

    def nothing_ran(self):
        self.assertEqual(self.non_version_calls(), [], "no aws, docker or Terraform command beyond the version probe")

    def applied(self):
        path = self.log + ".applied"
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def plan_and_approve(self, binding="manifest", **env):
        """Stage plan, then the human's NEW approval record (APPROVED_STAGE=runtime-apply, APPROVED_COMMIT = the rollback source)."""
        result = self.rb("plan", binding=binding, **env)
        self.assertEqual(result.rc, 0, result.out[-2500:])
        plan = self.plan_of(result)
        return plan, self.approve(plan)

    def approve(self, plan, **overrides):
        prespend, prespend_sha = self.write_prespend()
        record = self.approval_text(_sha256(plan), commit=self.prev_commit, prespend_sha=prespend_sha, stage="runtime-apply", receipt_sha=self.receipt_sha(plan), **overrides)
        return {"approval": self.write_approval(record), "prespend": prespend}

    def deploy_stage(self, plan, approval, binding="manifest", **env):
        return self.rb("deploy", "--plan", plan, "--approval", approval["approval"], "--prespend", approval["prespend"], binding=binding, **env)

    def runtime_apply_manifests(self):
        found = []
        directory = os.path.join(self.repo, "target", "release", self.new_head)
        if os.path.isdir(directory):
            for name in os.listdir(directory):
                if name.startswith("deploy-manifest-runtime-apply-"):
                    with open(os.path.join(directory, name)) as handle:
                        found.append(json.load(handle))
        return found


class RollbackKeepsRuntimeDryRunTests(RollbackKeepsRuntimeBase):
    def test_a_manifest_bound_dry_run_carries_the_revision_and_runs_nothing_but_the_version_probe(self):
        result = self.rb(execute=False)
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: DRY-RUN"))
        self.nothing_ran()
        for step in ("previous-commit", "runtime-state", "deployed-revision", "verify-registry-digests", "delegate-plan", "delegate-deploy"):
            self.assertIn(step, result.steps())
        out = result.stdout
        self.assertIn("RUNTIME-LIVE: yes", out)
        self.assertIn("keeping the running runtime at image revision %s" % REV, out)
        self.assertIn("-var=image_revision=%s" % REV, out, "the re-plan carries the bound revision")
        self.assertIn("--source-commit %s" % self.prev_commit, out)
        deploy_line = [l for l in out.splitlines() if l.startswith("DRY-RUN CMD:") and "scripts/deploy.sh" in l][0]
        self.assertIn("--stage runtime-apply", deploy_line)
        self.assertIn("--source-commit %s" % self.prev_commit, deploy_line)
        self.assertIn("--reuse-images %s" % self.deployed, deploy_line)
        self.assertNotIn("base-apply", deploy_line)
        self.assertIn("would require scholarchain-course/query-api:%s to resolve to %s" % (REV, registry_digest("query-api", REV)), out)
        self.assertIn("(STEP runtime-preservation)", out)

    def test_a_push_record_bound_dry_run_names_the_revision_and_the_record(self):
        result = self.rb(binding="push", execute=False)
        self.assertEqual(result.rc, 0, result.out)
        self.nothing_ran()
        deploy_line = [l for l in result.stdout.splitlines() if l.startswith("DRY-RUN CMD:") and "scripts/deploy.sh" in l][0]
        self.assertIn("--stage runtime-apply", deploy_line)
        self.assertIn("--image-revision %s" % REV, deploy_line)
        self.assertIn("--push-record %s" % self.push_record, deploy_line)
        self.assertNotIn("--reuse-images", deploy_line)
        self.assertIn("-var=image_revision=%s" % REV, result.stdout)

    def test_the_delegated_deploy_dry_run_with_a_plan_checks_everything_locally_and_still_runs_nothing(self):
        plan, approval = self.plan_and_approve()
        before = len(self.calls())
        result = self.rb(None, "--plan", plan, "--approval", approval["approval"], "--prespend", approval["prespend"], execute=False)
        self.assertEqual(result.rc, 0, result.out[-2500:])
        self.assertEqual([c for c in self.calls()[before:] if not c[1].startswith("version")], [], "R8: a dry run runs no show, init, aws or docker command")
        for step in ("image-revision-binding", "runtime-preservation", "state-binding"):
            self.assertIn("STEP: %s" % step, result.stdout)
        self.assertIn("DEFERRED to --execute", result.out)

    def test_a_dry_run_does_not_compare_registry_digests_it_only_prints_the_check(self):
        result = self.rb(execute=False, FAKE_IMAGE_DIGEST="sha256:" + "9" * 64)
        self.assertEqual(result.rc, 0, result.out)
        self.nothing_ran()

    def test_the_runtime_disabled_dry_run_is_unchanged(self):
        self.set_live_state([])
        result = self.rb(binding=None, execute=False)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("RUNTIME-LIVE: no", result.stdout)
        self.assertNotIn("deployed-revision", result.steps())
        deploy_line = [l for l in result.stdout.splitlines() if l.startswith("DRY-RUN CMD:") and "scripts/deploy.sh" in l][0]
        self.assertIn("--stage base-apply", deploy_line)
        self.assertNotIn("--reuse-images", deploy_line)
        self.assertNotIn("--image-revision", deploy_line)
        self.assertIn("--skip-runtime-archive", deploy_line)
        self.nothing_ran()


class RollbackKeepsRuntimeStateTests(RollbackKeepsRuntimeBase):
    def test_a_live_runtime_without_a_deployed_revision_is_refused_before_anything_runs(self):
        for execute in (False, True):
            with self.subTest(execute=execute):
                result = self.rb("plan" if execute else None, binding=None, execute=execute)
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "runtime-state")
                self.assertIn("a plan without one would delete the runtime", result.out)
                self.nothing_ran()

    def test_a_deployed_revision_while_the_state_shows_no_runtime_is_refused(self):
        self.set_live_state([])
        for binding in ("manifest", "push"):
            with self.subTest(binding=binding):
                result = self.rb("plan", binding=binding)
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "runtime-state")
                self.assertIn("would CREATE the runtime", result.out)
                self.nothing_ran()

    def test_an_unreadable_state_is_refused(self):
        with open(self.state_path(), "w") as handle:
            handle.write("not json")
        result = self.rb("plan")
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "runtime-state")
        self.nothing_ran()

    def test_both_bindings_or_a_binding_in_application_mode_are_usage_errors(self):
        both = self.rollback("--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", self.prev_commit,
                             "--deployed-manifest", self.deployed, "--deployed-push-record", self.push_record)
        self.assertEqual(both.rc, 2, both.out)
        app = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--deployed-manifest", self.deployed)
        self.assertEqual(app.rc, 2, app.out)


class RollbackKeepsRuntimeBindingTests(RollbackKeepsRuntimeBase):
    def refused_at_deployed_revision(self, result):
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "deployed-revision")
        self.nothing_ran()

    def test_a_missing_manifest_or_record_is_refused_before_any_aws_or_plan_call(self):
        gone = os.path.join(self.tmp, "gone.json")
        for flag in ("--deployed-manifest", "--deployed-push-record"):
            with self.subTest(flag):
                result = self.rollback("--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", self.prev_commit, flag, gone,
                                       "--stage", "plan", "--profile", "approved", "--execute")
                self.refused_at_deployed_revision(result)
                self.assertIn("not found", result.out)

    def test_an_unverified_manifest_is_refused_before_any_aws_or_plan_call(self):
        images = self.write_runtime_manifest()
        with open(images) as handle:
            good = json.load(handle)
        cases = {
            "the manifest of a push, not of a runtime-apply": {"stage": "push"},
            "another region": {"region": "us-west-2"},
            "another repository": {"images": [dict(i, repository="other/%s" % i["service"]) if i["service"] == "graph-service" else i for i in good["images"]]},
            "no ECS service recorded": {"ecs_services": []},
            "one ECS service missing": {"ecs_services": good["ecs_services"][:3]},
            "a revision that is not a commit SHA": {"image_revision": "c"},
            "a tag that is not the revision": {"images": [dict(i, tag=OTHER_REV) if i["service"] == "query-api" else i for i in good["images"]]},
            "a malformed digest": {"images": [dict(i, registry_digest="sha256:abc") if i["service"] == "query-api" else i for i in good["images"]]},
            "another schema": {"schema": "scholarchain.deploy-manifest.v0"},
        }
        for label, overrides in cases.items():
            with self.subTest(label):
                self.write_runtime_manifest(**overrides)
                self.refused_at_deployed_revision(self.rb("plan"))
                open(self.log, "w").close()

    def test_an_unverified_push_record_is_refused_before_any_aws_or_plan_call(self):
        with open(self.push_record) as handle:
            good = json.load(handle)
        cases = {
            "another region": {"region": "us-west-2"},
            "another environment": {"environment": "staging"},
            "another schema": {"schema": "scholarchain.push-record.v0"},
            "a commit that is not the tag of the images": {"commit": OTHER_REV},
            "a repository is another one": {"images": [dict(i, repository="other/%s" % i["service"]) if i["service"] == "query-api" else i for i in good["images"]]},
            "a service is missing": {"images": [i for i in good["images"] if i["service"] != "embedding-worker"]},
            "a digest is malformed": {"images": [dict(i, pushed_digest="sha256:abc") if i["service"] == "query-api" else i for i in good["images"]]},
        }
        for label, overrides in cases.items():
            with self.subTest(label):
                self.push_record_with(**overrides)
                self.refused_at_deployed_revision(self.rb("plan", binding="push"))
                open(self.log, "w").close()

    def test_a_registry_tag_that_no_longer_matches_the_manifest_is_refused_before_any_plan(self):
        for stage in ("plan", "deploy"):
            with self.subTest(stage=stage):
                extra = ("--plan", os.path.join(self.tmp, "p.tfplan")) if stage == "deploy" else ()
                result = self.rb(stage, *extra, FAKE_IMAGE_DIGEST="sha256:" + "9" * 64)
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "verify-registry-digests")
                self.assertIn("does not resolve to the recorded digest", result.out)
                self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " " or " apply " in " " + a + " "], [])
                open(self.log, "w").close()

    def test_one_changed_digest_in_the_manifest_is_refused(self):
        with open(self.deployed) as handle:
            good = json.load(handle)
        images = [dict(i, registry_digest="sha256:" + "8" * 64) if i["service"] == "graph-service" else i for i in good["images"]]
        self.write_runtime_manifest(images=images)
        result = self.rb("plan")
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "verify-registry-digests")
        self.assertIn("scholarchain-course/graph-service:%s" % REV, result.out)
        self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " "], [])

    def test_a_registry_tag_that_no_longer_matches_the_push_record_is_refused(self):
        result = self.rb("plan", binding="push", FAKE_IMAGE_DIGEST="sha256:" + "9" * 64)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "verify-registry-digests")
        self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " "], [])


class RollbackKeepsRuntimeExecuteTests(RollbackKeepsRuntimeBase):
    def test_stage_plan_verifies_the_registry_then_plans_the_previous_source_with_the_bound_revision_and_applies_nothing(self):
        result = self.rb("plan")
        self.assertEqual(result.rc, 0, result.out[-2500:])
        calls = self.calls()
        describes = [i for i, (n, a) in enumerate(calls) if n == "aws" and a.startswith("ecr describe-images")]
        plan_index = next(i for i, (n, a) in enumerate(calls) if n == "terraform" and " plan " in " " + a + " ")
        self.assertEqual(len(describes), 4)
        self.assertLess(max(describes), plan_index, "every registry digest is verified before the plan")
        plans = [a for n, a in self.calls("terraform") if " plan " in " " + a + " "]
        self.assertEqual(len(plans), 1)
        self.assertIn("-var=image_revision=%s" % REV, plans[0])
        self.assertIn("/source/%s/infra/terraform " % self.prev_commit, plans[0])
        self.assertEqual(self.mutating_calls(), [])
        receipt_path = self.plan_of(result) + ".receipt.json"
        with open(receipt_path) as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["commit"], self.prev_commit)
        self.assertEqual(receipt["scripts_commit"], self.new_head)
        self.assertEqual(receipt["image_revision"], REV)
        self.assertEqual(receipt["state"], self.state_identity(), "the plan is bound to the populated live state")
        self.assertIn("STEP: runtime-preservation", result.stdout)
        self.assertIn("runtime preservation ok", result.stdout)
        # The fake plan keeps the runtime: no delete or replace of the ECS services, the load balancer or the listener.
        for entry in receipt["actions"]:
            if entry["type"] in ("aws_ecs_service", "aws_lb", "aws_lb_listener"):
                self.assertNotIn("delete", entry["actions"], entry)
        self.assertEqual({e["actions"] for e in receipt["actions"] if e["type"] == "aws_ecs_service"}, {"update"})

    def check_the_complete_flow(self, binding):
        plan, approval = self.plan_and_approve(binding)
        before = len(self.calls())
        result = self.deploy_stage(plan, approval, binding)
        self.assertEqual(result.rc, 0, result.out[-3000:])
        stage_calls = self.calls()[before:]
        # (1) the registry digests were verified, again, before the single apply of exactly the approved plan bytes.
        apply_index = next(i for i, (n, a) in enumerate(stage_calls) if n == "terraform" and " apply " in " " + a + " ")
        describes = [i for i, (n, a) in enumerate(stage_calls) if n == "aws" and a.startswith("ecr describe-images")]
        self.assertTrue(describes and max(describes[:4]) < apply_index)
        self.assertEqual(len([i for i in describes if i < apply_index]), 8, "rollback.sh verifies, then deploy.sh verifies again: four digests each, before apply")
        applied = self.applied()
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0][1], _sha256(plan))
        applies = [a for n, a in stage_calls if n == "terraform" and " apply " in " " + a + " "]
        self.assertIn("/source/%s/infra/terraform " % self.prev_commit, applies[0], "the previous source, from the same state-bound materialized copy")
        chdir_apply = [l for l in self.chdir_lines() if l[0] == "apply"][0]
        self.assertEqual(chdir_apply[3], os.path.realpath(self.state_path()), "the apply updates the live state file")
        # (2) nothing pushed, nothing uploaded, the runtime is not torn down.
        self.assertEqual(self.calls("docker"), [])
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3")], [])
        # (3) all four ECS services were verified against the bound revision before success was recorded.
        self.assertEqual(len([a for n, a in stage_calls if n == "aws" and a.startswith("ecs describe-task-definition")]), 4)
        manifests = self.runtime_apply_manifests()
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["image_revision"], REV)
        self.assertEqual(manifests[0]["commit"], self.prev_commit)
        self.assertEqual(manifests[0]["plan_sha256"], _sha256(plan))
        self.assertEqual({e["service"] for e in manifests[0]["ecs_services"]}, set(SERVICES))
        self.assertEqual({i["registry_digest"] for i in manifests[0]["images"]}, {registry_digest(s, REV) for s in SERVICES})
        self.assertNotIn(FAKE_ACCOUNT, json.dumps(manifests[0]))
        self.assertNotIn(FAKE_ACCOUNT, result.out)

    def chdir_lines(self):
        path = self.log + ".chdir"
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def test_the_two_stage_flow_with_a_manifest_binding_applies_and_verifies_four_services(self):
        self.check_the_complete_flow("manifest")

    def test_the_two_stage_flow_with_a_push_record_binding_applies_and_verifies_four_services(self):
        self.check_the_complete_flow("push")

    def test_deploy_needs_a_plan_and_execute_needs_a_stage(self):
        self.assertEqual(self.rb("deploy").rc, 2)
        self.assertEqual(self.rb(None).rc, 2)

    # ---- the plan's image_revision must equal the bound revision -----------------------------------
    def test_a_plan_for_another_revision_is_refused_when_planning(self):
        self.use_show(KEEP, revision=OTHER_REV)
        result = self.rb("plan")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("planned image_revision %s != expected %s" % (OTHER_REV, REV), result.out)
        self.assertEqual(self.mutating_calls(), [])

    def test_a_receipt_for_another_revision_is_refused_before_apply(self):
        plan, approval = self.plan_and_approve()
        self.write_plan_receipt(plan, _sha256(plan), commit=self.prev_commit, scripts_commit=self.new_head, image_revision=OTHER_REV, actions=receipt_actions(KEEP))
        approval = self.approve(plan)
        result = self.deploy_stage(plan, approval)
        self.refused_in(result, "plan-provenance")
        self.assertIn("receipt image_revision differs", result.out)
        self.assertEqual(self.applied(), [])

    def test_a_saved_plan_that_really_carries_another_revision_is_refused_before_apply(self):
        plan, approval = self.plan_and_approve()
        self.use_show(KEEP, revision=OTHER_REV, name="swapped-show.json")
        result = self.deploy_stage(plan, approval)
        self.refused_in(result, "plan-inspect")
        self.assertIn("planned image_revision %s != expected %s" % (OTHER_REV, REV), result.out)
        self.assertEqual(self.applied(), [])

    def test_a_plan_without_any_image_revision_is_refused_before_apply(self):
        plan, approval = self.plan_and_approve()
        self.use_show(KEEP, revision=None, name="none-show.json")
        result = self.deploy_stage(plan, approval)
        self.refused_in(result, "plan-inspect")
        self.assertEqual(self.applied(), [])

    # ---- a plan that would delete or replace the live runtime is refused (safety net) --------------
    def test_a_plan_that_deletes_or_replaces_the_runtime_is_refused_when_planning(self):
        cases = {
            "an ECS service is deleted": (DELETES_A_SERVICE, "would delete the live runtime resource %s" % (SVC_ADDRESS % "query-api")),
            "the listener is replaced": (REPLACES_THE_LISTENER, "would replace the live runtime resource %s" % LISTENER),
            "the load balancer is deleted": (DELETES_THE_LOAD_BALANCER, "would delete the live runtime resource %s" % LOAD_BALANCER),
        }
        for label, (changes, needle) in cases.items():
            with self.subTest(label):
                self.use_show(changes, name="deleting-show.json")
                result = self.rb("plan")
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "runtime-preservation")
                self.assertIn("RUNTIME-PRESERVATION-FAILED: the plan %s" % needle, result.out)
                self.assertIn("do NOT approve or apply it", result.out)
                self.assertEqual(self.mutating_calls(), [])
                open(self.log, "w").close()

    def test_a_task_definition_replacement_alone_is_not_a_runtime_deletion(self):
        self.use_show([c for c in KEEP if c[1] == "aws_ecs_task_definition"], name="taskdef-show.json")
        result = self.rb("plan")
        self.assertEqual(result.rc, 0, result.out[-2000:])

    def test_a_receipt_that_lists_a_runtime_deletion_is_refused_by_deploy_in_a_dry_run_and_with_execute(self):
        plan, approval = self.plan_and_approve()
        self.write_plan_receipt(plan, _sha256(plan), commit=self.prev_commit, scripts_commit=self.new_head, image_revision=REV, actions=receipt_actions(DELETES_A_SERVICE))
        approval = self.approve(plan)
        dry = self.rb(None, "--plan", plan, "--approval", approval["approval"], "--prespend", approval["prespend"], execute=False)
        self.assertEqual(dry.rc, 3, dry.out)
        self.assertIn("RUNTIME-PRESERVATION-FAILED", dry.out)
        before = len(self.calls())
        result = self.deploy_stage(plan, approval)
        self.refused_in(result, "runtime-preservation")
        self.assertEqual(self.applied(), [])
        self.assertEqual([a for n, a in self.calls()[before:] if n == "terraform" and " apply " in " " + a + " "], [])

    def test_a_saved_plan_that_really_deletes_the_runtime_is_refused_even_when_the_receipt_is_clean(self):
        plan, approval = self.plan_and_approve()
        self.use_show(DELETES_A_SERVICE, name="deleting-show.json")
        result = self.deploy_stage(plan, approval)
        self.refused_in(result, "runtime-preservation")
        self.assertIn("the verified plan itself would not keep the live runtime", result.out)
        self.assertEqual(self.applied(), [])

    # ---- the state binding and the pre-spend gate are inherited ------------------------------------
    def test_a_state_that_changed_after_the_plan_is_refused_before_apply(self):
        plan, approval = self.plan_and_approve()
        with open(self.state_path()) as handle:
            document = json.load(handle)
        document["serial"] += 1
        with open(self.state_path(), "w") as handle:
            json.dump(document, handle)
        result = self.deploy_stage(plan, approval)
        self.refused_in(result, "state-binding")
        self.assertIn("live state changed after the plan", result.out)
        self.assertEqual(self.applied(), [])

    def test_a_state_from_another_stack_is_refused_before_apply(self):
        plan, approval = self.plan_and_approve()
        self.write_state(lineage="ffffffff-0000-0000-0000-000000000000", extra={"resources": live_runtime_state()})
        result = self.deploy_stage(plan, approval)
        self.refused_in(result, "state-binding")
        self.assertEqual(self.applied(), [])

    def test_a_missing_state_is_refused_before_any_apply(self):
        plan, approval = self.plan_and_approve()
        os.remove(self.state_path())
        result = self.deploy_stage(plan, approval)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.applied(), [])

    def test_a_missing_prespend_receipt_is_refused_before_any_apply(self):
        plan, approval = self.plan_and_approve()
        os.remove(approval["prespend"])
        result = self.deploy_stage(plan, approval)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("pre-spend receipt not found", result.out)
        self.assertEqual(self.applied(), [])

    def test_a_record_for_a_plain_runtime_apply_or_another_stage_cannot_apply_the_rollback_plan(self):
        plan, approval = self.plan_and_approve()
        other_stage = self.approve(plan)
        record = self.approval_text(_sha256(plan), commit=self.prev_commit, prespend_sha=_sha256(other_stage["prespend"]), stage="base-apply", receipt_sha=self.receipt_sha(plan))
        wrong_stage = dict(other_stage, approval=self.write_approval(record, name="base-record.md"))
        result = self.deploy_stage(plan, wrong_stage)
        self.refused_in(result, "stage-match")
        record = self.approval_text(_sha256(plan), commit=self.new_head, prespend_sha=_sha256(other_stage["prespend"]), stage="runtime-apply", receipt_sha=self.receipt_sha(plan))
        head_record = dict(other_stage, approval=self.write_approval(record, name="head-record.md"))
        result = self.deploy_stage(plan, head_record)
        self.refused_in(result, "commit-match")
        self.assertEqual(self.applied(), [])

    # ---- after apply ---------------------------------------------------------------------------------
    def test_a_stale_or_missing_ecs_service_after_apply_is_not_recorded_as_success(self):
        for env in ({"FAKE_ECS_STALE_SERVICE": "semantic-service"}, {"FAKE_ECS_SERVICES": "query-api"}, {"FAKE_ECS_SWAP_SERVICE": "graph-service"}):
            with self.subTest(env=env):
                plan, approval = self.plan_and_approve()
                result = self.deploy_stage(plan, approval, **env)
                self.assertEqual(result.rc, 4, result.out)
                self.assertIn("step=record-ecs", result.out)
                self.assertEqual(self.runtime_apply_manifests(), [])
                open(self.log, "w").close()
                open(self.log + ".applied", "w").close()


class CarryDeployBase(RuntimeFixtureMixin, DeployBase):
    """deploy.sh directly: --stage runtime-apply --source-commit PREV with the carried revision."""

    def setUp(self):
        super().setUp()
        self.prev_commit = self.head()
        self.write("infra/terraform/modules/runtime/newer.tf", "# added after the rollback target\n")
        self.new_head = self.commit("newer tree")
        self.set_live_state()
        self.deployed = self.write_runtime_manifest()
        self.push_record_file = self.write_push_record(commit=REV)
        self.arrange_carry()

    def arrange_carry(self, actions=None, show_changes=None, receipt_revision=REV, show_revision=REV):
        self.stage = "runtime-apply"
        self.revision = REV
        self.plan, self.plan_sha = self.make_plan()
        self.show = self.write_show_json(KEEP if show_changes is None else show_changes, image_revision=show_revision, name="carry-show.json")
        self.receipt = self.write_plan_receipt(
            self.plan, self.plan_sha, commit=self.prev_commit, scripts_commit=self.new_head, image_revision=receipt_revision,
            actions=receipt_actions(KEEP) if actions is None else actions,
        )
        self.receipt_sha_value = self.receipt_sha(self.plan)
        self.prespend, self.prespend_sha = self.write_prespend()
        self.approval = self.write_approval(self.approval_text(self.plan_sha, commit=self.prev_commit, prespend_sha=self.prespend_sha, stage="runtime-apply", receipt_sha=self.receipt_sha_value))
        self.base_env = {
            "FAKE_SHOW_JSON": self.show,
            "FAKE_ECS_TAG": REV,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE": self.archive,
        }

    def reapprove(self):
        """The human reviews the (edited) receipt: the NEW approval record names its hash; the commit is the rollback source."""
        self.receipt_sha_value = self.receipt_sha(self.plan)
        self.approval = self.write_approval(self.approval_text(self.plan_sha, commit=self.prev_commit, prespend_sha=self.prespend_sha, stage="runtime-apply", receipt_sha=self.receipt_sha_value))

    def manifest_args(self):
        return ["--source-commit", self.prev_commit, "--reuse-images", self.deployed]

    def record_args(self):
        return ["--source-commit", self.prev_commit, "--image-revision", REV, "--push-record", self.push_record_file]

    def non_version(self):
        return [c for c in self.calls() if not c[1].startswith("version")]

    def stage_manifests(self):
        return self.deploy_manifests("runtime-apply")


class CarryDeployTests(CarryDeployBase):
    def test_the_dry_run_binds_the_revision_and_runs_only_the_version_probe(self):
        for label, args in (("manifest", self.manifest_args()), ("push record", self.record_args())):
            with self.subTest(label):
                result = self.deploy(*args)
                self.assertEqual(result.rc, 0, result.out)
                self.assertTrue(result.result_line().startswith("RESULT: DRY-RUN"))
                self.assertEqual(self.non_version(), [])
                for step in ("image-revision-binding", "state-binding", "plan-inspect", "runtime-preservation"):
                    self.assertIn(step, result.steps())
                self.assertIn("infrastructure rollback that KEEPS the runtime", result.out)
                self.assertIn("DEFERRED to --execute", result.out)
                open(self.log, "w").close()

    def test_execute_with_a_manifest_applies_the_verified_plan_and_checks_the_four_services_for_the_bound_revision(self):
        result = self.execute(*self.manifest_args())
        self.assertEqual(result.rc, 0, result.out[-2500:])
        calls = self.cloud_calls()
        apply_index = next(i for i, (n, a) in enumerate(calls) if n == "terraform" and " apply " in " " + a + " ")
        describes = [i for i, (n, a) in enumerate(calls) if n == "aws" and a.startswith("ecr describe-images")]
        self.assertEqual(len(describes), 4)
        self.assertLess(max(describes), apply_index, "the registry digests equal the manifest's BEFORE apply")
        self.assertEqual(len(self.applied()), 1)
        self.assertEqual(self.applied()[0][1], self.plan_sha)
        self.assertEqual(self.calls("docker"), [])
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3")], [])
        self.assertEqual(len([a for _n, a in self.calls("aws") if a.startswith("ecs describe-task-definition")]), 4)
        data = self.stage_manifests()
        self.assertEqual(len(data), 1)
        self.assertEqual((data[0]["image_revision"], data[0]["commit"]), (REV, self.prev_commit))
        self.assertEqual(len(data[0]["ecs_services"]), 4)
        self.assertIn("all four ECS services run task definitions that reference", result.out)

    def test_execute_with_a_push_record_applies_and_checks_the_four_services(self):
        result = self.execute(*self.record_args())
        self.assertEqual(result.rc, 0, result.out[-2500:])
        self.assertIn("push record names revision %s" % REV, result.out)
        self.assertEqual(len(self.applied()), 1)
        self.assertEqual(self.stage_manifests()[0]["image_revision"], REV)

    def test_source_commit_alone_is_still_refused_with_runtime_apply(self):
        result = self.execute("--source-commit", self.prev_commit)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("needs the deployed image revision", result.out)
        self.assertEqual(self.calls("aws"), [])
        result = self.execute("--source-commit", self.prev_commit, "--push-record", self.push_record_file)
        self.assertEqual(result.rc, 3, result.out)

    def test_image_revision_is_only_valid_with_runtime_apply(self):
        result = self.run_script("deploy.sh", "--stage", "base-apply", "--region", REGION, "--plan", self.plan, "--image-revision", REV)
        self.assertEqual(result.rc, 2, result.out)

    def test_an_image_revision_that_is_not_the_manifests_revision_is_refused(self):
        result = self.execute("--source-commit", self.prev_commit, "--reuse-images", self.deployed, "--image-revision", OTHER_REV)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "image-revision-binding")
        self.assertIn("!= the previous deploy manifest's image revision", result.out)
        self.assertEqual(self.applied(), [])

    def test_a_manifest_that_is_not_bound_to_this_deployment_is_refused_before_anything_runs(self):
        with open(self.deployed) as handle:
            good = json.load(handle)
        cases = {
            "another account": {"account_sha256": "e" * 64},
            "another region": {"region": "us-west-2"},
            "a push manifest": {"stage": "push"},
            "no ecs services": {"ecs_services": []},
            "another repository": {"images": [dict(i, repository="other/%s" % i["service"]) if i["service"] == "query-api" else i for i in good["images"]]},
        }
        for label, overrides in cases.items():
            with self.subTest(label):
                self.write_runtime_manifest(**overrides)
                result = self.execute(*self.manifest_args())
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "image-revision-binding")
                self.assertIn("MANIFEST-CHECK-FAILED", result.out)
                self.assertEqual(self.cloud_calls(), [], "refused before any aws, docker, init or apply")
                open(self.log, "w").close()

    def test_a_registry_tag_that_moved_is_refused_before_apply(self):
        for args in (self.manifest_args(), self.record_args()):
            with self.subTest(args=args[2]):
                result = self.execute(*args, FAKE_IMAGE_DIGEST="sha256:" + "9" * 64)
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "verify-registry-images")
                self.assertEqual(self.applied(), [])
                open(self.log, "w").close()

    def test_a_missing_or_foreign_push_record_is_refused_before_any_registry_call(self):
        os.remove(self.push_record_file)
        result = self.execute(*self.record_args())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "push-record")
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("ecr")], [])
        for overrides in ({"account_sha256": "e" * 64}, {"region": "us-west-2"}, {"environment": "staging"}, {"commit": OTHER_REV}):
            with self.subTest(overrides):
                self.push_record_with(**overrides)
                result = self.execute(*self.record_args())
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "push-record")
                self.assertIn("PUSH-RECORD-FAILED", result.out)
                self.assertEqual(self.applied(), [])

    def test_a_plan_revision_that_is_not_the_bound_one_is_refused(self):
        self.arrange_carry(receipt_revision=OTHER_REV)
        result = self.execute(*self.manifest_args())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "plan-provenance")
        self.arrange_carry(show_revision=OTHER_REV)
        result = self.execute(*self.manifest_args())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "plan-inspect")
        self.assertEqual(self.applied(), [])

    def test_a_runtime_deleting_plan_is_refused_by_the_receipt_in_a_dry_run_and_by_the_show_json_when_executing(self):
        self.arrange_carry(actions=receipt_actions(DELETES_A_SERVICE))
        dry = self.deploy(*self.manifest_args())
        self.assertEqual(dry.rc, 3, dry.out)
        self.assertEqual(dry.steps()[-1], "runtime-preservation")
        self.assertIn("RUNTIME-PRESERVATION-FAILED: the plan would delete the live runtime resource", dry.out)
        self.assertEqual(self.non_version(), [])
        self.arrange_carry(show_changes=REPLACES_THE_LISTENER)
        result = self.execute(*self.manifest_args())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "runtime-preservation")
        self.assertIn("would replace the live runtime resource %s" % LISTENER, result.out)
        self.assertEqual(self.applied(), [])
        self.assertEqual(self.calls("docker"), [])

    def test_a_receipt_without_an_action_list_is_refused_while_the_runtime_is_live(self):
        self.arrange_carry()
        with open(self.receipt) as handle:
            document = json.load(handle)
        del document["actions"]
        with open(self.receipt, "w") as handle:
            json.dump(document, handle)
        self.reapprove()
        result = self.deploy(*self.manifest_args())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "runtime-preservation")
        self.assertIn("unreadable or holds no action list", result.out)

    def test_the_carry_needs_a_state_that_shows_the_runtime(self):
        self.set_live_state([])
        self.arrange_carry()
        result = self.deploy(*self.manifest_args())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "runtime-preservation")
        self.assertIn("shows no live runtime", result.out)

    def test_a_missing_or_changed_state_is_refused_before_apply(self):
        with open(self.state_path()) as handle:
            document = json.load(handle)
        document["serial"] += 1
        with open(self.state_path(), "w") as handle:
            json.dump(document, handle)
        result = self.execute(*self.manifest_args())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "state-binding")
        os.remove(self.state_path())
        result = self.execute(*self.manifest_args())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.applied(), [])

    def test_a_stale_service_after_apply_is_not_recorded(self):
        result = self.execute(*self.manifest_args(), FAKE_ECS_STALE_SERVICE="semantic-service")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("RESULT: FAIL step=record-ecs", result.stdout)
        self.assertEqual(self.stage_manifests(), [])

    def test_the_stage_binding_is_unambiguous(self):
        """A record for base-apply, or for a plain runtime-apply at HEAD, cannot apply the carried plan."""
        self.approval = self.write_approval(self.approval_text(self.plan_sha, commit=self.prev_commit, prespend_sha=self.prespend_sha, stage="base-apply", receipt_sha=self.receipt_sha_value), name="b.md")
        self.assert_refused(self.deploy(*self.manifest_args()), "stage-match")
        self.approval = self.write_approval(self.approval_text(self.plan_sha, commit=self.new_head, prespend_sha=self.prespend_sha, stage="runtime-apply", receipt_sha=self.receipt_sha_value), name="h.md")
        self.assert_refused(self.deploy(*self.manifest_args()), "commit-match")
        # And the carried record cannot apply a plain runtime-apply at HEAD.
        self.approval = self.write_approval(self.approval_text(self.plan_sha, commit=self.prev_commit, prespend_sha=self.prespend_sha, stage="runtime-apply", receipt_sha=self.receipt_sha_value), name="c.md")
        self.assert_refused(self.deploy(), "commit-match")


class BaseApplySafetyNetTests(CarryDeployBase):
    """A base-apply carries NO image revision: with the runtime live its plan would delete the runtime, so it is refused."""

    def arrange_base(self, changes, actions):
        self.stage = "base-apply"
        self.revision = None
        self.plan, self.plan_sha = self.make_plan(name="base.tfplan")
        self.show = self.write_show_json(changes, name="base-show.json")
        self.receipt = self.write_plan_receipt(self.plan, self.plan_sha, commit=self.prev_commit, scripts_commit=self.new_head, image_revision=None, actions=actions)
        self.receipt_sha_value = self.receipt_sha(self.plan)
        self.approval = self.write_approval(self.approval_text(self.plan_sha, commit=self.prev_commit, prespend_sha=self.prespend_sha, stage="base-apply", receipt_sha=self.receipt_sha_value), name="base-gate.md")
        self.base_env["FAKE_SHOW_JSON"] = self.show

    def test_a_base_apply_plan_that_deletes_the_live_runtime_is_refused_before_apply(self):
        deleting = [(SVC_ADDRESS % s, "aws_ecs_service", ["delete"]) for s in SERVICES] + [(LOAD_BALANCER, "aws_lb", ["delete"])]
        self.arrange_base(deleting, receipt_actions(deleting))
        args = ["--source-commit", self.prev_commit, "--skip-runtime-archive"]
        dry = self.deploy(*args)
        self.assertEqual(dry.rc, 3, dry.out)
        self.assertEqual(dry.steps()[-1], "runtime-preservation")
        result = self.execute(*args)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "runtime-preservation")
        self.assertEqual(self.applied(), [])

    def test_a_base_apply_plan_that_keeps_the_runtime_or_a_state_without_one_is_not_blocked(self):
        quiet = [("module.network.aws_vpc.main", "aws_vpc", ["update"])]
        self.arrange_base(quiet, receipt_actions(quiet))
        result = self.execute("--source-commit", self.prev_commit, "--skip-runtime-archive")
        self.assertEqual(result.rc, 0, result.out[-2000:])
        self.assertIn("runtime preservation ok", result.out)


if __name__ == "__main__":
    unittest.main()

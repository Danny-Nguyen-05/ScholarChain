"""Phase 15 P7 (stage-a apply path) and P18 (the stage-a base plan against the residual state Session 1 left).

P7 (b): the reviewed Session 2 stages of scripts/config/expected-plan-deltas.json (stagea-base, stagea-emr-enable, rb-base),
        derived offline by `plan_deltas.py derive --set stagea` from infra/terraform/tests/phase15_stagea.tftest.hcl, and
        the optional-entry rule of `plan_deltas.py check` (the R-b cluster delete is absent once the cluster TERMINATED).
P7 (c): deploy.sh --stage base-apply --skip-runtime-archive accepts the EMR-only plan (stage a, step 4) and the R-b base
        plan with its module.emr deletes, on realistic post-base-apply states (no live runtime), through the fake tools.
P18:    (1) real Terraform with the built-in provider only (no AWS provider, no network, no cloud): a terraform_data guard
        without input that is already in the state is a NO-OP, an absent one is created; the two residual guards of the
        source have no input or triggers_replace, so the result transfers. (2) plan.sh --execute (fake tools) against a
        synthetic copy of the residual state records the state's lineage and 171 creates, `plan_deltas.py check --stage
        stagea-base` on its log is IDENTICAL, and deploy.sh base-apply accepts that very plan and receipt. (3) the
        move-aside alternative (no state, --expect-new-state) creates the two guards again: the reviewed list then
        DIFFERS by exactly those two creates.
No real state is read; every state here is synthetic and hand-written. No AWS call.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import REAL_REPO, REGION, SCRIPTS_DIR, STATE_LINEAGE, account_hash, post_base_apply_resources, sha256_bytes, state_resource
from test_deploy import DeployBase
from test_runtime_base_apply import DeployOnRealisticStatesBase

sys.path.insert(0, os.path.join(SCRIPTS_DIR, "lib"))
import plan_deltas as pd  # noqa: E402

TOOL = os.path.join(SCRIPTS_DIR, "lib", "plan_deltas.py")
EXPECTED = os.path.join(SCRIPTS_DIR, "config", "expected-plan-deltas.json")
TF_ROOT = os.path.join(REAL_REPO, "infra", "terraform")
STAGEA_TFTEST = os.path.join(TF_ROOT, "tests", "phase15_stagea.tftest.hcl")
CLUSTER = "module.emr.aws_emr_cluster.pipeline[0]"
GRAPH_POLICY = 'module.identity.aws_iam_role_policy.task["graph-service"]'
BUILTIN = 'provider["terraform.io/builtin/terraform"]'
CLEAN_AWS_ENV = ("AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")


def load_expected():
    with open(EXPECTED, encoding="utf-8") as handle:
        return json.load(handle)


def rtype(address):
    """Resource type of a plan address (module path and index key removed)."""
    return re.sub(r"\[.*\]$", "", address).split(".")[-2]


def stage_changes(stage, skip_optional=False):
    """(address, type, [actions]) triples for the fake show-json of a reviewed stage."""
    out = []
    for entry in load_expected()["stages"][stage]["actions"]:
        if skip_optional and entry.get("optional"):
            continue
        out.append((entry["address"], rtype(entry["address"]), entry["actions"].split("+")))
    return out


def residual_guards():
    """A synthetic copy of the residual state's resources (address, type and name only; Session 1 after-cleanup inventory)."""
    resources = []
    for name in ("configuration_guard", "provider_guard"):
        resource = state_resource(None, "terraform_data", name)
        resource.pop("module")
        resource["provider"] = BUILTIN
        resources.append(resource)
    return resources


def emr_state_resources():
    """The module.emr resources and the two EMR inline policies after the stage-a EMR enable (from the reviewed list)."""
    out = []
    for entry in load_expected()["stages"]["stagea-emr-enable"]["actions"]:
        match = re.match(r"^module\.([a-z0-9_]+)\.([a-z0-9_]+)\.([a-z0-9_]+)\[0\]$", entry["address"])
        out.append(state_resource("module." + match.group(1), match.group(2), match.group(3), (0,)))
    return out


class ExpectedStageaListTests(unittest.TestCase):
    def setUp(self):
        self.doc = load_expected()
        self.stages = self.doc["stages"]

    def addresses(self, stage, action=None):
        return [e["address"] for e in self.stages[stage]["actions"] if action is None or e["actions"] == action]

    def test_each_new_stage_names_its_own_offline_source(self):
        for name in ("stagea-base", "stagea-emr-enable", "rb-base"):
            with self.subTest(name):
                prov = self.stages[name]["provenance"]
                self.assertEqual(prov["source_test"], "infra/terraform/tests/phase15_stagea.tftest.hcl")
                self.assertIn("derive --set stagea", prov["derivation"])
                self.assertEqual(prov["terraform_version"], "1.13.5")
                self.assertIn("178 addresses of the real Session 1 base plan", prov["cross_check"])
        # The Phase 14 stages keep the top-level provenance.
        self.assertNotIn("provenance", self.stages["pointer-apply"])
        self.assertNotIn("provenance", self.stages["emr-apply"])

    def test_the_stagea_base_creates_171_resources_and_keeps_the_two_residual_guards(self):
        stage = self.stages["stagea-base"]
        added = self.addresses("stagea-base")
        self.assertEqual(len(added), 171)
        self.assertEqual(len(set(added)), 171)
        self.assertEqual({e["actions"] for e in stage["actions"]}, {"create"})
        self.assertEqual(stage["residual_state_kept"], list(pd.RESIDUAL_STATE))
        for kept in pd.RESIDUAL_STATE:
            self.assertNotIn(kept, added)
        self.assertIn("terraform_data.phase12b_guard", added, "state rm'ed in Session 1, so created again")
        self.assertEqual(stage["plan_line"], "Plan: 171 to add, 0 to change, 0 to destroy.")

    def test_the_stagea_base_has_no_neptune_emr_ecs_service_alb_dashboard_or_certificate_validation(self):
        added = self.addresses("stagea-base")
        self.assertEqual([a for a in added if a.startswith(("module.neptune.", "module.emr."))], [])
        forbidden = {"aws_ecs_service", "aws_ecs_task_definition", "aws_lb", "aws_lb_target_group", "aws_lb_listener",
                     "aws_cloudwatch_dashboard", "aws_acm_certificate_validation", "aws_appautoscaling_target"}
        self.assertEqual([a for a in added if rtype(a) in forbidden], [])
        # emr_data (the instance role's bucket access) is unconditional; the two gated EMR inline policies are not planned.
        self.assertEqual([a for a in added if a.startswith(("module.identity.aws_iam_role_policy.emr_control", "module.identity.aws_iam_role_policy.emr_disk_encryption"))], [])
        self.assertIn("module.identity.aws_iam_role_policy.emr_data", added)
        # What stage a needs is there: the certificate request (validated before R-b), the NAT path, the vector store.
        for needed in ("aws_acm_certificate.api[0]", "module.network.aws_nat_gateway.course", "module.s3vectors.aws_s3vectors_vector_bucket.embeddings",
                       "module.runtime.aws_ecs_cluster.course"):
            self.assertIn(needed, added)

    def test_the_stagea_emr_enable_is_exactly_the_reviewed_phase14_emr_apply(self):
        mine = {(e["address"], e["actions"]) for e in self.stages["stagea-emr-enable"]["actions"]}
        phase14 = {(e["address"], e["actions"]) for e in self.stages["emr-apply"]["actions"]}
        self.assertEqual(mine, phase14)
        self.assertEqual(len(mine), 13)
        self.assertEqual(self.stages["stagea-emr-enable"]["plan_line"], "Plan: 13 to add, 0 to change, 0 to destroy.")

    def test_the_rb_base_adds_neptune_updates_one_policy_and_deletes_every_stagea_emr_resource(self):
        creates = self.addresses("rb-base", "create")
        self.assertEqual(len(creates), 5)
        self.assertTrue(all(a.startswith("module.neptune.") for a in creates), creates)
        self.assertEqual(self.addresses("rb-base", "update"), [GRAPH_POLICY])
        self.assertEqual(sorted(self.addresses("rb-base", "delete")), sorted(self.addresses("stagea-emr-enable")))
        optional = [e for e in self.stages["rb-base"]["actions"] if e.get("optional")]
        self.assertEqual([e["address"] for e in optional], [CLUSTER])
        self.assertIn("TERMINATED", optional[0]["optional"])

    def test_the_rb_base_plan_lines_with_and_without_the_optional_cluster_delete(self):
        stage = self.stages["rb-base"]
        self.assertEqual(stage["plan_line"], "Plan: 5 to add, 1 to change, 13 to destroy.")
        self.assertEqual(stage["summary_line"], "summary: add=5 change=1 destroy=13 replace=0")
        kinds = [pd.normalize_actions(e["actions"]) for e in stage["actions"] if not e.get("optional")]
        self.assertEqual(stage["plan_line_if_optional_absent"], "Plan: %d to add, %d to change, %d to destroy." % (kinds.count("create"), kinds.count("update"), kinds.count("delete")))
        self.assertEqual(stage["summary_line_if_optional_absent"], "summary: add=5 change=1 destroy=12 replace=0")

    def test_only_the_rb_cluster_delete_is_optional_in_the_whole_list(self):
        optional = [(name, e["address"]) for name, s in self.stages.items() for e in s["actions"] if e.get("optional")]
        self.assertEqual(optional, [("rb-base", CLUSTER)])

    def test_the_stagea_tftest_carries_the_three_run_names_the_parser_expects_and_is_plan_only(self):
        with open(STAGEA_TFTEST, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(re.findall(r'^run "([a-z0-9_]+)"', text, re.M), list(pd.STAGEA_RUNS))
        self.assertIsNone(re.search(r"command\s*=\s*apply", text), "plan-only: the mock provider must never apply")
        self.assertEqual(len(re.findall(r"command\s*=\s*plan", text)), 3)
        self.assertIn('mock_provider "aws"', text)
        self.assertIsNone(re.search(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])", text), "no 12-digit literal")

    def test_the_residual_guards_in_the_source_have_no_input_or_triggers_replace(self):
        """The P18 no-op proof below uses guards without input; it transfers only if the real guards have none either."""
        for fname, name in (("main.tf", "configuration_guard"), ("phase14b-providers.tf", "provider_guard"), ("phase12b.tf", "phase12b_guard")):
            with self.subTest(name):
                with open(os.path.join(TF_ROOT, fname), encoding="utf-8") as handle:
                    text = handle.read()
                start = text.index('resource "terraform_data" "%s" {' % name)
                depth, end = 0, start
                for end in range(text.index("{", start), len(text)):
                    depth += {"{": 1, "}": -1}.get(text[end], 0)
                    if depth == 0:
                        break
                block = text[start:end + 1]
                self.assertIsNone(re.search(r"^\s*(input|triggers_replace)\s*=", block, re.M), block[:200])


def resource_block(text, rtype, name):
    """The text of `resource "<rtype>" "<name>" { ... }` (brace-matched; the module sources hold no braces in strings here)."""
    start = text.index('resource "%s" "%s" {' % (rtype, name))
    depth = 0
    for end in range(text.index("{", start), len(text)):
        depth += {"{": 1, "}": -1}.get(text[end], 0)
        if depth == 0:
            return text[start:end + 1]
    raise ValueError("unterminated block")


class EmrClusterWaitsForTheMountTargetTests(unittest.TestCase):
    """P7 (d), Session 1 finding S1-F2: the cluster was created in parallel with the EFS mount target and the primary node's
    bootstrap failed "EFS mount failed". The bootstrap arguments reference only the file system and the access point, so
    the ordering must be explicit."""

    def setUp(self):
        with open(os.path.join(TF_ROOT, "modules", "emr", "main.tf"), encoding="utf-8") as handle:
            self.block = resource_block(handle.read(), "aws_emr_cluster", "pipeline")

    def test_the_cluster_depends_on_the_efs_mount_target(self):
        match = re.search(r"^\s*depends_on\s*=\s*\[([^\]]*)\]", self.block, re.M)
        self.assertIsNotNone(match, "aws_emr_cluster.pipeline has no depends_on")
        self.assertIn("aws_efs_mount_target.staging", [d.strip() for d in match.group(1).split(",")])

    def test_the_mount_target_is_not_otherwise_referenced_so_the_depends_on_is_needed(self):
        without = re.sub(r"^\s*depends_on\s*=.*$", "", self.block, flags=re.M)
        self.assertNotIn("aws_efs_mount_target", without)
        self.assertIn("aws_efs_file_system.staging[0].id", open(os.path.join(TF_ROOT, "modules", "emr", "main.tf"), encoding="utf-8").read())


def verbose(plans):
    out = ["tests/x.tftest.hcl... in progress"]
    for run, resources in plans.items():
        out += ['  run "%s"... pass' % run, "", "Terraform will perform the following actions:", ""]
        for address, lines in resources.items():
            out += ["  # %s will be created" % address, '  + resource "t" "n" {'] + lines + ["    }", ""]
        out += ["Plan: %d to add, 0 to change, 0 to destroy." % len(resources), ""]
    return "\n".join(out)


class DeriveAndCheckStageaTests(unittest.TestCase):
    def plans(self):
        guards = {a: ['      + id = "(known after apply)"'] for a in pd.RESIDUAL_STATE}
        base = dict(guards, **{"terraform_data.phase12b_guard": ["      + id = 1"], "module.network.aws_vpc.course": ['      + cidr = "10.0.0.0/16"'],
                               GRAPH_POLICY: ["      + statements = 1"]})
        emr = dict(base, **{CLUSTER: ["      + name = 1"]})
        rb = dict(base, **{"module.neptune.aws_neptune_cluster.data[0]": ["      + n = 1"], GRAPH_POLICY: ["      + statements = 2"]})
        return {pd.STAGEA_RUNS[0]: base, pd.STAGEA_RUNS[1]: emr, pd.STAGEA_RUNS[2]: rb}

    def test_derive_drops_the_residual_guards_from_the_base_and_diffs_the_increments(self):
        result = pd.derive(verbose(self.plans()), "stagea")
        self.assertEqual(result["stagea-base"]["added"], [GRAPH_POLICY, "module.network.aws_vpc.course", "terraform_data.phase12b_guard"])
        self.assertEqual(result["stagea-base"]["kept_from_residual_state"], list(pd.RESIDUAL_STATE))
        self.assertEqual(result["stagea-emr-enable"], {"added": [CLUSTER], "removed": [], "changed": []})
        self.assertEqual(result["rb-base"], {"added": ["module.neptune.aws_neptune_cluster.data[0]"], "removed": [CLUSTER], "changed": [GRAPH_POLICY]})

    def test_derive_refuses_a_base_without_the_residual_guards_or_a_missing_run(self):
        plans = self.plans()
        del plans[pd.STAGEA_RUNS[0]]["terraform_data.provider_guard"]
        with self.assertRaises(ValueError):
            pd.derive(verbose(plans), "stagea")
        plans = self.plans()
        del plans[pd.STAGEA_RUNS[2]]
        with self.assertRaises(ValueError):
            pd.derive(verbose(plans), "stagea")
        with self.assertRaises(ValueError):
            pd.derive(verbose(self.plans()), "phase14b")

    def test_cli_derive_set_and_unknown_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(verbose(self.plans()))
            done = subprocess.run([sys.executable, "-I", TOOL, "derive", "--set", "stagea", "--verbose-output", path], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)["stagea-emr-enable"]["added"], [CLUSTER])
            done = subprocess.run([sys.executable, "-I", TOOL, "derive", "--set", "bogus", "--verbose-output", path], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 2)

    def log(self, changes):
        lines = ["PLAN-ACTION: %s %s" % ("+".join(acts), address) for address, _t, acts in changes]
        return "\n".join(["PLAN-ACTIONS-BEGIN count=%d" % len(lines)] + lines + ["PLAN-ACTIONS-END count=%d" % len(lines)])

    def test_the_rb_cluster_delete_may_be_absent_but_never_differ(self):
        expected = load_expected()
        lines, ok = pd.check("rb-base", self.log(stage_changes("rb-base", skip_optional=True)), expected)
        self.assertTrue(ok, lines)
        self.assertEqual([l for l in lines if l.startswith("ABSENT-OPTIONAL:")], ["ABSENT-OPTIONAL: delete %s (optional: %s)" % (CLUSTER, [e for e in expected["stages"]["rb-base"]["actions"] if e["address"] == CLUSTER][0]["optional"])])
        lines, ok = pd.check("rb-base", self.log(stage_changes("rb-base")), expected)
        self.assertTrue(ok, lines)
        self.assertIn("MATCH: delete %s" % CLUSTER, lines)
        changed = [c if c[0] != CLUSTER else (CLUSTER, "aws_emr_cluster", ["create"]) for c in stage_changes("rb-base")]
        lines, ok = pd.check("rb-base", self.log(changed), expected)
        self.assertFalse(ok)
        self.assertIn("ACTION-DIFFERS: %s expected=delete actual=create" % CLUSTER, lines)

    def test_a_non_optional_entry_is_still_missing_and_the_stagea_lists_never_cross_match(self):
        expected = load_expected()
        without_policy = [c for c in stage_changes("rb-base") if c[0] != GRAPH_POLICY]
        lines, ok = pd.check("rb-base", self.log(without_policy), expected)
        self.assertFalse(ok)
        self.assertIn("MISSING: update %s (expected, not in the plan)" % GRAPH_POLICY, lines)
        lines, ok = pd.check("stagea-base", self.log(stage_changes("stagea-emr-enable")), expected)
        self.assertFalse(ok)
        lines, ok = pd.check("stagea-emr-enable", self.log(stage_changes("stagea-emr-enable")), expected)
        self.assertTrue(ok, lines)

    def test_cli_check_accepts_the_new_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.log")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.log(stage_changes("stagea-base")))
            done = subprocess.run([sys.executable, "-I", TOOL, "check", "--stage", "stagea-base", "--plan-log", path], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(done.stdout.count("MATCH: create "), 171)
            self.assertTrue(done.stdout.strip().splitlines()[-1].startswith("RESULT: IDENTICAL stage=stagea-base"))


def terraform_1135():
    exe = shutil.which("terraform")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "version", "-json"], capture_output=True, text=True, timeout=60, env=clean_env()).stdout
        return exe if json.loads(out).get("terraform_version") == "1.13.5" else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def clean_env():
    env = {k: v for k, v in os.environ.items() if k not in CLEAN_AWS_ENV and not k.startswith("TF_")}
    env.update({"AWS_EC2_METADATA_DISABLED": "true", "AWS_CONFIG_FILE": os.devnull, "AWS_SHARED_CREDENTIALS_FILE": os.devnull,
                "TF_IN_AUTOMATION": "1", "TF_INPUT": "0", "CHECKPOINT_DISABLE": "1"})
    return env


GUARD_CONFIG = '''variable "x" {
  type    = number
  default = 1
}
resource "terraform_data" "configuration_guard" {
  lifecycle {
    precondition {
      condition     = var.x == 1
      error_message = "synthetic precondition (the real guards hold preconditions only)"
    }
  }
}
resource "terraform_data" "provider_guard" {
  lifecycle {
    precondition {
      condition     = var.x > 0
      error_message = "synthetic"
    }
  }
}
resource "terraform_data" "phase12b_guard" {}
'''


class ResidualGuardsAreNoOpWithRealTerraformTests(unittest.TestCase):
    """P18 (1): real Terraform 1.13.5, the BUILT-IN provider only (no provider download, no AWS provider, no network), a
    scratch directory and a hand-written synthetic state. Plan only; nothing is applied."""

    def setUp(self):
        self.tf = terraform_1135()
        if not self.tf:
            self.skipTest("terraform 1.13.5 is not on PATH")
        self.dir = tempfile.mkdtemp(prefix="sc-p18-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        with open(os.path.join(self.dir, "main.tf"), "w", encoding="utf-8") as handle:
            handle.write(GUARD_CONFIG)
        state = {"version": 4, "terraform_version": "1.13.5", "serial": 40, "lineage": STATE_LINEAGE, "outputs": {}, "check_results": None,
                 "resources": [{"mode": "managed", "type": "terraform_data", "name": n, "provider": BUILTIN,
                                "instances": [{"schema_version": 0, "attributes": {"id": "synthetic-%s" % n, "input": None, "output": None, "triggers_replace": None},
                                               "sensitive_attributes": []}]} for n in ("configuration_guard", "provider_guard")]}
        with open(os.path.join(self.dir, "terraform.tfstate"), "w", encoding="utf-8") as handle:
            json.dump(state, handle)

    def run_tf(self, *args):
        return subprocess.run([self.tf] + list(args), cwd=self.dir, capture_output=True, text=True, timeout=300, env=clean_env())

    def test_the_two_residual_guards_are_kept_and_the_removed_guard_is_created(self):
        with open(os.path.join(self.dir, "terraform.tfstate"), "rb") as handle:
            before = handle.read()
        plan = self.run_tf("plan", "-input=false", "-lock=false", "-no-color", "-out=p.tfplan")
        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        self.assertIn("Plan: 1 to add, 0 to change, 0 to destroy.", plan.stdout)
        show = self.run_tf("show", "-json", "p.tfplan")
        self.assertEqual(show.returncode, 0, show.stderr)
        actions = {c["address"]: c["change"]["actions"] for c in json.loads(show.stdout)["resource_changes"]}
        self.assertEqual(actions, {"terraform_data.configuration_guard": ["no-op"], "terraform_data.provider_guard": ["no-op"], "terraform_data.phase12b_guard": ["create"]})
        with open(os.path.join(self.dir, "terraform.tfstate"), "rb") as handle:
            self.assertEqual(handle.read(), before, "a plan never writes the state")
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".terraform")), "no provider was installed")


class ResidualStatePlanToDeployTests(DeployBase):
    """P18 (2) and (3): plan.sh against a synthetic residual state, the reviewed-list check, then deploy.sh base-apply."""

    def setUp(self):
        super().setUp()
        self.private_vars = os.path.join(self.tmp, "synthetic-private.local.tfvars")
        with open(self.private_vars, "w") as handle:
            handle.write('owner = "synthetic"\n')
        self.write_state(serial=41, extra={"resources": residual_guards()})
        guards = [(a, "terraform_data", ["no-op"]) for a in pd.RESIDUAL_STATE]
        self.base_show = self.write_show_json(stage_changes("stagea-base") + guards, name="stagea-base-show.json")

    def plan_sh(self, *extra, show=None):
        return self.run_script("plan.sh", "--env", "course", "--region", REGION, "--profile", "approved", "--execute", *extra,
                               SCHOLARCHAIN_TF_PRIVATE_VARS=self.private_vars, FAKE_SHOW_JSON=show or self.base_show, FAKE_PLAN_SALT="stagea")

    def check_log(self, stdout):
        path = os.path.join(self.tmp, "stagea-plan.log")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(stdout)
        return subprocess.run([sys.executable, "-I", TOOL, "check", "--stage", "stagea-base", "--plan-log", path], capture_output=True, text=True, timeout=60)

    def test_the_plan_against_the_residual_state_is_the_reviewed_list_and_base_apply_accepts_it(self):
        planned = self.plan_sh()
        self.assertEqual(planned.rc, 0, planned.out[-2500:])
        plan_file = self.plan_file_of(planned)
        with open(plan_file + ".receipt.json", encoding="utf-8") as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["state"], self.state_identity())
        self.assertEqual(receipt["state"]["lineage"], STATE_LINEAGE)
        summary = receipt["summary"]
        self.assertEqual((summary["add"], summary["change"], summary["destroy"], summary["replace"], summary["no_op"]), (171, 0, 0, 0, 2))
        self.assertEqual(len(receipt["actions"]), 171)
        self.assertEqual(planned.stdout.count("PLAN-ACTION: "), 171)
        for kept in pd.RESIDUAL_STATE:
            self.assertNotIn(kept, planned.stdout)
        checked = self.check_log(planned.stdout)
        self.assertEqual(checked.returncode, 0, checked.stdout[-1500:])
        self.assertTrue(checked.stdout.strip().splitlines()[-1].startswith("RESULT: IDENTICAL stage=stagea-base"))
        # The human reviews and approves exactly this plan and receipt; deploy.sh base-apply then accepts it.
        self.stage, self.revision, self.plan = "base-apply", None, plan_file
        with open(plan_file, "rb") as handle:
            self.plan_sha = sha256_bytes(handle.read())
        self.receipt_sha_value = self.receipt_sha(plan_file)
        self.set_prespend()
        self.base_env["FAKE_SHOW_JSON"] = self.base_show
        dry = self.deploy("--skip-runtime-archive")
        self.assertEqual(dry.rc, 0, dry.out[-2500:])
        self.assertIn("RUNTIME-LIVE: no", dry.stdout)
        self.assertIn("STEP: state-binding", dry.stdout)
        result = self.execute("--skip-runtime-archive")
        self.assertEqual(result.rc, 0, result.out[-2500:])
        self.assertEqual(len(self.applied()), 1)
        self.assertEqual(self.applied()[0][1], self.plan_sha)
        self.assertEqual(result.stdout.count("runtime preservation ok"), 2)
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3 cp")], [], "--skip-runtime-archive uploads nothing")

    def test_the_move_aside_alternative_recreates_the_guards_and_differs_from_the_reviewed_list(self):
        os.remove(self.state_path())
        guards = [(a, "terraform_data", ["create"]) for a in pd.RESIDUAL_STATE]
        fresh_show = self.write_show_json(stage_changes("stagea-base") + guards, name="stagea-fresh-show.json")
        refused = self.plan_sh(show=fresh_show)
        self.assertEqual(refused.rc, 3, "without --expect-new-state a missing state is refused")
        planned = self.plan_sh("--expect-new-state", show=fresh_show)
        self.assertEqual(planned.rc, 0, planned.out[-2500:])
        with open(self.plan_file_of(planned) + ".receipt.json", encoding="utf-8") as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["state"], {"present": False})
        self.assertEqual(receipt["summary"]["add"], 173)
        checked = self.check_log(planned.stdout)
        self.assertEqual(checked.returncode, 1)
        self.assertEqual(sorted(l for l in checked.stdout.splitlines() if l.startswith("UNEXPECTED:")),
                         ["UNEXPECTED: create %s (in the plan, not in the reviewed list)" % a for a in pd.RESIDUAL_STATE])


class StageaBaseApplyTests(DeployOnRealisticStatesBase):
    """P7 (c): the EMR-only plan of stage a and the R-b base plan go through --stage base-apply --skip-runtime-archive."""

    def run_base_apply(self, changes):
        open(self.log, "w").close()
        if os.path.exists(self.log + ".applied"):
            os.remove(self.log + ".applied")
        self.arrange_base(changes, at_head=True)
        dry = self.deploy(*self.base_args(at_head=True))
        self.assertEqual(dry.rc, 0, dry.out[-2500:])
        self.assertIn("RUNTIME-LIVE: no", dry.stdout)
        self.assertIn("runtime archive upload skipped by --skip-runtime-archive", dry.out)
        result = self.execute(*self.base_args(at_head=True))
        self.assertEqual(result.rc, 0, result.out[-2500:])
        self.assertTrue(result.result_line().startswith("RESULT: PASS"), result.result_line())
        self.assertEqual(len(self.applied()), 1)
        self.assertEqual(result.stdout.count("runtime preservation ok"), 2, "the receipt and the verified plan's show -json")
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3 cp")], [])
        manifests = self.deploy_manifests("base-apply")
        self.assertEqual(manifests[-1]["ecs_services"], [])
        self.assertEqual(manifests[-1]["images"], [])
        return result

    def test_the_stagea_emr_enable_plan_is_accepted_on_the_stagea_base_state(self):
        self.set_live_state(post_base_apply_resources() + residual_guards())
        self.run_base_apply(stage_changes("stagea-emr-enable"))

    def test_the_rb_base_plan_with_the_emr_deletes_is_accepted_with_or_without_the_cluster_delete(self):
        self.set_live_state(post_base_apply_resources() + residual_guards() + emr_state_resources())
        for skip in (False, True):
            with self.subTest(cluster_already_terminated=skip):
                self.run_base_apply(stage_changes("rb-base", skip_optional=skip))

    def test_the_receipt_of_the_emr_enable_lists_the_13_creates_and_no_image_revision(self):
        self.set_live_state(post_base_apply_resources() + residual_guards())
        self.arrange_base(stage_changes("stagea-emr-enable"), at_head=True)
        with open(self.receipt, encoding="utf-8") as handle:
            receipt = json.load(handle)
        self.assertIsNone(receipt["image_revision"])
        self.assertEqual(sorted(a["address"] for a in receipt["actions"]), sorted(e[0] for e in stage_changes("stagea-emr-enable")))
        self.assertEqual(receipt["account_sha256"], account_hash())


if __name__ == "__main__":
    unittest.main()

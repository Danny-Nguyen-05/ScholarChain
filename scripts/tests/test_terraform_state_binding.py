"""R1 regression with REAL terraform 1.13.5 on a local, no-cloud fixture: infrastructure rollback plans and applies against
the EXISTING live local state, never a fresh one, and refuses a missing or different state before apply.

The fixture is a throwaway git repository: a Terraform root whose only resources are built-in `terraform_data`
(no provider API, no network), the real aws provider binary used read-only through TF_CLI_ARGS_init=-plugin-dir
(never downloaded), a fake `aws` for the identity call, and a `terraform` wrapper that logs every command and runs the
real binary. The older commit has no scripts/ directory. Nothing touches AWS or the real repository's state.
The terraform binary honours TERRAFORM_BIN; if Terraform 1.13.5 or the local aws provider is missing the tests are
reported as SKIPPED (a skip is not a pass).
"""
import json
import os
import shutil
import subprocess
import unittest

from helpers import FAKE_ACCOUNT, REAL_REPO, REGION, Fixture, account_hash, sha256_bytes, write_exec

TF_BIN = os.environ.get("TERRAFORM_BIN") or shutil.which("terraform") or "terraform"
PROVIDERS = os.path.join(REAL_REPO, "infra", "terraform", ".terraform", "providers")
LOCK = os.path.join(REAL_REPO, "infra", "terraform", ".terraform.lock.hcl")
REAL_HOME = os.environ.get("HOME", "/")  # tfenv resolves the pinned version from HOME

VERSIONS = 'terraform {\n  required_version = "1.13.5"\n  required_providers {\n    aws = {\n      source  = "hashicorp/aws"\n      version = "= 6.44.0"\n    }\n  }\n}\n'
VARIABLES = (
    'variable "aws_region" { type = string }\n'
    'variable "aws_profile" {\n  type    = string\n  default = ""\n}\n'
    'variable "aws_account_id" { type = string }\n'
    'variable "environment" {\n  type    = string\n  default = "course"\n}\n'
    'variable "project" {\n  type    = string\n  default = "scholarchain"\n}\n'
    'variable "image_revision" {\n  type    = string\n  default = ""\n}\n'
)
PROVIDER = (
    'provider "aws" {\n  region                      = var.aws_region\n  access_key                  = "fake"\n  secret_key                  = "fake"\n'
    "  skip_credentials_validation = true\n  skip_requesting_account_id  = true\n  skip_metadata_api_check     = true\n}\n"
)
OLDER_MAIN = 'resource "terraform_data" "existing" {\n  input = "v0"\n}\n'
NEWER_MAIN = 'resource "terraform_data" "existing" {\n  input = "v1"\n}\n\nresource "terraform_data" "newer" {\n  input = "added after the rollback target"\n}\n'


def tool_ready():
    try:
        out = subprocess.run([TF_BIN, "version", "-json"], capture_output=True, text=True, env=dict(os.environ), timeout=60).stdout
        return json.loads(out)["terraform_version"] == "1.13.5"
    except Exception:  # noqa: BLE001
        return False


class RealStateBindingTests(Fixture):
    @classmethod
    def setUpClass(cls):
        if not tool_ready():
            raise unittest.SkipTest("terraform 1.13.5 not available (set TERRAFORM_BIN)")
        if not os.path.isdir(PROVIDERS) or not os.path.isfile(LOCK):
            raise unittest.SkipTest("the local aws provider directory or the lock file is missing")

    # The Fixture builds a different repository; this class builds its own no-cloud Terraform repository.
    def build_repo(self):
        os.makedirs(self.repo)
        subprocess.run(["git", "-C", self.repo, "init", "-q"], check=True)
        self.write(".gitignore", "target/\n*.tfstate\n*.tfstate.backup\n.terraform/\noverride.tf\n*_override.tf\n")
        self.write("infra/terraform/versions.tf", VERSIONS)
        self.write("infra/terraform/variables.tf", VARIABLES)
        self.write("infra/terraform/provider.tf", PROVIDER)
        self.write("infra/terraform/environments/course.tfvars", 'environment = "course"\n')
        self.write("infra/terraform/modules/runtime/compute.tf", 'runtime_platform {\n  cpu_architecture = "X86_64"\n}\n')
        shutil.copy(LOCK, os.path.join(self.repo, "infra", "terraform", ".terraform.lock.hcl"))
        self.write("infra/terraform/main.tf", OLDER_MAIN)
        self.prev_commit = self.commit("older commit: no scripts directory")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "scripts")))
        self.write("infra/terraform/main.tf", NEWER_MAIN)
        self.write("scripts/marker.txt", "the newer tree carries scripts/\n")
        self.new_head = self.commit("newer commit")

    def setUp(self):
        super().setUp()
        self.private_vars = os.path.join(self.tmp, "private.local.tfvars")
        with open(self.private_vars, "w") as handle:
            handle.write('aws_account_id = "%s"\n' % FAKE_ACCOUNT)
        self.wrapper_log = os.path.join(self.tmp, "terraform-wrapper.log")
        open(self.wrapper_log, "w").close()
        write_exec(os.path.join(self.bin, "terraform"), '#!/bin/bash\nprintf "%%s\\n" "$*" >> "%s"\nexec "%s" "$@"\n' % (self.wrapper_log, TF_BIN))
        self.use_config()
        self.extra = {
            "HOME": REAL_HOME,
            "TF_CLI_ARGS_init": "-plugin-dir=" + PROVIDERS,
            "SCHOLARCHAIN_TF_PRIVATE_VARS": self.private_vars,
            "AWS_EC2_METADATA_DISABLED": "true",
        }
        self.populate_live_state()

    def tf(self, *args):
        env = dict(os.environ, HOME=REAL_HOME, TF_IN_AUTOMATION="1", TF_INPUT="0", CHECKPOINT_DISABLE="1", TF_CLI_ARGS_init="-plugin-dir=" + PROVIDERS,
                   TF_DATA_DIR=os.path.join(self.tmp, "tfdata-live"))
        return subprocess.run([TF_BIN, "-chdir=" + os.path.join(self.repo, "infra", "terraform")] + list(args), capture_output=True, text=True, env=env, timeout=900)

    def populate_live_state(self):
        """The live local state: created by real terraform from the NEWER configuration (resources existing and newer)."""
        init = self.tf("init", "-input=false", "-lockfile=readonly")
        self.assertEqual(init.returncode, 0, init.stderr[-800:])
        applied = self.tf("apply", "-auto-approve", "-input=false", "-var=aws_region=%s" % REGION, "-var=aws_account_id=%s" % FAKE_ACCOUNT)
        self.assertEqual(applied.returncode, 0, applied.stdout[-800:] + applied.stderr[-800:])
        with open(self.state_path()) as handle:
            document = json.load(handle)
        self.assertEqual(sorted(r["name"] for r in document["resources"]), ["existing", "newer"])
        self.live_lineage = document["lineage"]

    def state_document(self):
        with open(self.state_path()) as handle:
            return json.load(handle)

    def state_bytes(self):
        with open(self.state_path(), "rb") as handle:
            return handle.read()

    def script(self, name, *args, **env):
        merged = dict(self.extra)
        merged.update(env)
        return self.run_script(name, *args, **merged)

    def rollback_plan(self):
        result = self.script("rollback.sh", "--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", self.prev_commit,
                             "--profile", "approved", "--stage", "plan", "--execute")
        self.assertEqual(result.rc, 0, result.out[-3000:])
        plan = self.plan_file_of_rollback(result)
        with open(plan + ".receipt.json") as handle:
            return plan, json.load(handle)

    @staticmethod
    def plan_file_of_rollback(result):
        for line in result.stdout.splitlines():
            if "PLAN-FILE: " in line:
                return line.split("PLAN-FILE: ", 1)[1].strip()
        raise AssertionError(result.stdout[-1500:])

    def actions(self, receipt):
        return {a["address"]: a["actions"] for a in receipt["actions"]}

    @staticmethod
    def sha_of_file(path):
        with open(path, "rb") as handle:
            return sha256_bytes(handle.read())

    def approve_and_deploy(self, plan, receipt, **env):
        prespend, prespend_sha = self.write_prespend()
        approval = self.write_approval(
            self.approval_text(self.sha_of_file(plan), commit=self.prev_commit, prespend_sha=prespend_sha, stage="base-apply",
                               receipt_sha=self.sha_of_file(plan + ".receipt.json"))
        )
        return self.script("rollback.sh", "--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", self.prev_commit, "--profile", "approved",
                           "--stage", "deploy", "--plan", plan, "--approval", approval, "--prespend", prespend, "--execute", **env)

    def wrapper_commands(self):
        with open(self.wrapper_log) as handle:
            return handle.read().splitlines()

    def applies(self):
        return [c for c in self.wrapper_commands() if " apply " in " " + c + " " and "-auto-approve" not in c]

    def test_the_rollback_plans_against_the_existing_state_not_a_fresh_one(self):
        before = self.state_bytes()
        plan, receipt = self.rollback_plan()
        actions = self.actions(receipt)
        # Hand-derived: the live state holds existing (input v1) and newer; the older commit wants existing (input v0) and no newer.
        self.assertEqual(actions, {"terraform_data.existing": "update", "terraform_data.newer": "delete"}, actions)
        self.assertNotIn("create", actions.values(), "no create for the resource the live stack already manages")
        self.assertEqual((receipt["summary"]["add"], receipt["summary"]["change"], receipt["summary"]["destroy"]), (0, 1, 1))
        self.assertEqual(receipt["state"]["lineage"], self.live_lineage)
        self.assertEqual(receipt["state"]["sha256"], sha256_bytes(before))
        self.assertEqual(receipt["commit"], self.prev_commit)
        self.assertEqual(self.state_bytes(), before, "planning never changes the live state")
        # The plan used the materialized older source, bound to the live state file.
        binding = [p for p in self.find_binding_files()]
        self.assertEqual(len(binding), 1)
        with open(binding[0]) as handle:
            self.assertIn('path = "%s"' % os.path.realpath(self.state_path()), handle.read())

    def find_binding_files(self):
        found = []
        for base, _dirs, files in os.walk(os.path.join(self.repo, "target", "plans")):
            if "zz_scholarchain_state_binding.tf" in files:
                found.append(os.path.join(base, "zz_scholarchain_state_binding.tf"))
        return found

    def test_without_the_live_state_the_same_rollback_would_have_proposed_to_create_the_existing_resource(self):
        """The control: a fresh (absent) state plans a create for the resource the live stack already has."""
        saved = self.state_bytes()
        os.rename(self.state_path(), self.state_path() + ".aside.tfstate")
        try:
            result = self.script("plan.sh", "--env", "course", "--region", REGION, "--profile", "approved", "--source-commit", self.prev_commit, "--expect-new-state", "--execute")
            self.assertEqual(result.rc, 0, result.out[-2500:])
            plan = [l.split("PLAN-FILE: ", 1)[1] for l in result.stdout.splitlines() if l.startswith("PLAN-FILE: ")][0]
            with open(plan + ".receipt.json") as handle:
                receipt = json.load(handle)
            self.assertEqual(self.actions(receipt), {"terraform_data.existing": "create"})
            self.assertEqual(receipt["state"], {"present": False})
        finally:
            os.replace(self.state_path() + ".aside.tfstate", self.state_path())
        self.assertEqual(self.state_bytes(), saved)

    def test_the_approved_rollback_applies_to_the_live_state(self):
        plan, receipt = self.rollback_plan()
        serial = self.state_document()["serial"]
        result = self.approve_and_deploy(plan, receipt)
        self.assertEqual(result.rc, 0, result.out[-3000:])
        self.assertEqual(len(self.applies()), 1)
        document = self.state_document()
        self.assertEqual(document["lineage"], self.live_lineage, "the live state file itself was updated, not a new one")
        self.assertGreater(document["serial"], serial)
        by_name = {r["name"]: r for r in document["resources"]}
        self.assertEqual(sorted(by_name), ["existing"], "newer was destroyed by the rollback")
        self.assertEqual(by_name["existing"]["instances"][0]["attributes"]["input"]["value"], "v0")
        self.assertEqual(account_hash(), receipt["account_sha256"])

    def test_a_missing_state_is_refused_before_apply_and_no_new_state_appears(self):
        plan, receipt = self.rollback_plan()
        os.remove(self.state_path())
        result = self.approve_and_deploy(plan, receipt)
        self.assertEqual(result.rc, 3, result.out[-2000:])
        self.assertIn("RESULT: REFUSED step=state-binding", result.out)
        self.assertIn("the live state file is missing", result.out)
        self.assertEqual(self.applies(), [])
        self.assertFalse(os.path.exists(self.state_path()), "no fresh state was created by the refused run")

    def test_a_state_with_a_different_lineage_is_refused_before_apply_and_left_untouched(self):
        plan, receipt = self.rollback_plan()
        document = self.state_document()
        document["lineage"] = "00000000-0000-4000-8000-00000000abcd"
        with open(self.state_path(), "w") as handle:
            json.dump(document, handle)
        before = self.state_bytes()
        result = self.approve_and_deploy(plan, receipt)
        self.assertEqual(result.rc, 3, result.out[-2000:])
        self.assertIn("RESULT: REFUSED step=state-binding", result.out)
        self.assertIn("lineage differs", result.out)
        self.assertEqual(self.applies(), [])
        self.assertEqual(self.state_bytes(), before)

    def test_a_state_changed_after_the_plan_is_refused_before_apply(self):
        plan, receipt = self.rollback_plan()
        document = self.state_document()
        document["serial"] += 1
        with open(self.state_path(), "w") as handle:
            json.dump(document, handle)
        result = self.approve_and_deploy(plan, receipt)
        self.assertEqual(result.rc, 3, result.out[-2000:])
        self.assertIn("changed after the plan", result.out)
        self.assertEqual(self.applies(), [])

    def test_an_ignored_override_file_in_the_worktree_cannot_change_what_the_rollback_loads(self):
        """R3 with real terraform: an ignored override.tf that would rename the input is not in the git archive."""
        self.write("infra/terraform/override.tf", 'resource "terraform_data" "existing" {\n  input = "INJECTED"\n}\n')
        plan, receipt = self.rollback_plan()
        with open(plan + ".json") as handle:
            document = json.load(handle)
        changes = {c["address"]: c["change"] for c in document["resource_changes"]}
        self.assertEqual(changes["terraform_data.existing"]["after"]["input"], "v0", "the committed older source was loaded")
        self.assertNotIn("INJECTED", json.dumps(document))
        self.assertTrue(os.path.exists(os.path.join(self.repo, "infra", "terraform", "override.tf")), "the override really is in the work tree")


if __name__ == "__main__":
    unittest.main()

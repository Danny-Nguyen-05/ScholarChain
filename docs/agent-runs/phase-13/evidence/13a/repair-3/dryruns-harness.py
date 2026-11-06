"""Retained dry-run transcripts (repair round 3): rollback infra (runtime enabled, both bindings), rollback infra
(runtime disabled), rollback app, and every deploy stage, each with the fake tool log that proves only the Terraform
version probe ran. Fake aws/terraform/docker on PATH; temp git fixture; no cloud, no real state.

Run:  python3 -I dryruns.py     (it imports the fixtures from scripts/tests)
"""
import sys
import unittest

sys.path.insert(0, "/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests")

from helpers import REGION  # noqa: E402
from test_deploy import DeployBase  # noqa: E402
from test_runtime_rollback import REV, CarryDeployBase, RollbackKeepsRuntimeBase  # noqa: E402


def banner(title, result, test):
    print("=" * 110)
    print("## " + title)
    print("## exit code: %d" % result.rc)
    for line in result.stdout.splitlines():
        print(line)
    log = test.raw_calls()
    print("## fake tool log (%d call(s); version probe = the only allowed one):" % len(log))
    for tool, args, profile in log:
        print("##   %s %s [%s]" % (tool, args[:110], profile))
    extra = [c for c in test.calls() if not c[1].startswith("version")]
    print("## calls other than the Terraform version probe: %d" % len(extra))
    assert extra == [], extra


class RollbackDry(RollbackKeepsRuntimeBase):
    def test_1_rollback_infra_runtime_enabled_manifest_binding(self):
        banner("rollback.sh --mode infra (runtime ENABLED in the state) --deployed-manifest: dry run", self.rb(execute=False), self)

    def test_2_rollback_infra_runtime_enabled_push_record_binding(self):
        banner("rollback.sh --mode infra (runtime ENABLED) --deployed-push-record: dry run", self.rb(binding="push", execute=False), self)

    def test_3_rollback_infra_runtime_disabled(self):
        self.set_live_state([])
        banner("rollback.sh --mode infra (runtime DISABLED in the state, no revision): dry run, as before", self.rb(binding=None, execute=False), self)

    def test_4_rollback_infra_live_runtime_without_a_revision_is_refused(self):
        result = self.rb(binding=None, execute=False)
        banner("rollback.sh --mode infra, runtime live, NO --deployed-*: refused (STEP runtime-state)", result, self)

    def test_5_rollback_app(self):
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous)
        banner("rollback.sh (application rollback, --previous-manifest): dry run", result, self)

    def test_6_rollback_infra_with_plan_runs_the_delegated_deploy_dry_run(self):
        plan, approval = self.plan_and_approve()
        open(self.log, "w").close()
        result = self.rb(None, "--plan", plan, "--approval", approval["approval"], "--prespend", approval["prespend"], execute=False)
        banner("rollback.sh --mode infra --plan <rollback plan> (delegated deploy.sh dry run): dry run", result, self)


class DeployDry(DeployBase):
    def test_7_base_apply(self):
        self.arrange("base-apply")
        banner("deploy.sh --stage base-apply: dry run", self.deploy(), self)

    def test_8_push(self):
        self.arrange("push")
        banner("deploy.sh --stage push: dry run", self.deploy(), self)

    def test_9_runtime_apply(self):
        self.arrange("runtime-apply")
        banner("deploy.sh --stage runtime-apply (plain, HEAD): dry run", self.deploy(), self)


class CarryDry(CarryDeployBase):
    def test_a_runtime_apply_carried_by_manifest(self):
        banner("deploy.sh --stage runtime-apply --source-commit <prev> --reuse-images <manifest> (S1): dry run", self.deploy(*self.manifest_args()), self)

    def test_b_runtime_apply_carried_by_push_record(self):
        banner("deploy.sh --stage runtime-apply --source-commit <prev> --image-revision %s.. --push-record <record> (S1): dry run" % REV[:6], self.deploy(*self.record_args()), self)


if __name__ == "__main__":
    unittest.main(verbosity=0, argv=["dryruns"], exit=True)

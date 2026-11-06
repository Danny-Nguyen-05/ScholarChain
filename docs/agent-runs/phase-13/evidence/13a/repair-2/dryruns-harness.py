"""Dry runs of every Phase 13A script against a synthetic clean temp repo with synthetic receipts/records.
Prints the commands, the RESULT line and the complete list of terraform/aws/docker calls (the fakes log argv only)."""
import os
import sys
import unittest

sys.path.insert(0, "/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests")
from helpers import REGION, SERVICES, Fixture, registry_digest, sha256_bytes  # noqa: E402

PRIOR = "c" * 40
ARCHIVE = b"tiny-runtime-archive"


class Demo(Fixture):
    def setUp(self):
        super().setUp()
        self.archive = os.path.join(self.tmp, "runtime.tgz")
        with open(self.archive, "wb") as handle:
            handle.write(ARCHIVE)
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE)), RUNTIME_ARCHIVE_EXPECTED_SHA256=sha256_bytes(ARCHIVE))
        self.private = os.path.join(self.tmp, "p.local.tfvars")
        with open(self.private, "w") as handle:
            handle.write('owner = "private-value-abc123"\n')
        self.env_extra = {"SCHOLARCHAIN_TF_PRIVATE_VARS": self.private, "SCHOLARCHAIN_RUNTIME_ARCHIVE": self.archive,
                          "SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI": "s3://bucket-test/key/runtime.tgz"}

    def show(self, title, result, repo_calls=True):
        print("=" * 100)
        print("# " + title)
        for line in result.out.splitlines():
            if line.startswith(("STEP:", "RESULT:", "DRY-RUN CMD:", "CMD:", "PLAN-", "APPROVED_", "PROTECTION", "TEARDOWN-", "CONFIRM", "DESTROY", "POLICY")) or "DEFERRED" in line or "PREPARE-REQUIRED" in line:
                print("  " + line[:240])
        print("  exit code: %d" % result.rc)
        calls = self.calls()
        print("  fake-tool calls recorded (%d): %s" % (len(calls), [(n, a.split()[0] if n != 'aws' else ' '.join(a.split()[:2])) for n, a in calls]))
        open(self.log, "w").close()

    def test_all(self):
        d = self.head()
        env = dict(self.env_extra)
        self.show("plan.sh dry run", self.run_script("plan.sh", "--env", "course", "--region", REGION, **env))
        # synthetic receipts/records
        for stage in ("base-apply", "push", "runtime-apply"):
            plan = None
            args = ["--stage", stage, "--region", REGION]
            prespend, psha = self.write_prespend(name="pre-%s.json" % stage)
            if stage == "push":
                self.write_release_manifest()
                approval = self.write_approval(self.approval_text(prespend_sha=psha, stage="push"), name="rec-push.md")
            else:
                plan, plan_sha = self.make_plan(name="%s.tfplan" % stage)
                revision = None if stage == "base-apply" else d
                self.write_plan_receipt(plan, plan_sha, image_revision=revision)
                approval = self.write_approval(self.approval_text(plan_sha, prespend_sha=psha, stage=stage, receipt_sha=self.receipt_sha(plan)), name="rec-%s.md" % stage)
                args += ["--plan", plan]
                if stage == "runtime-apply":
                    self.write_release_manifest()
                    self.write_push_record()
            args += ["--approval", approval, "--prespend", prespend]
            self.show("deploy.sh --stage %s dry run" % stage, self.run_script("deploy.sh", *args, **env))
            if stage == "runtime-apply":
                os.remove(os.path.join(self.repo, "target", "release", d, "push-record.json"))
                self.show("REFUSAL: runtime-apply without a push record", self.run_script("deploy.sh", *args, **env))
        previous = self.write_deploy_manifest(revision=PRIOR, digests={s: registry_digest(s, PRIOR) for s in SERVICES})
        self.show("rollback.sh app dry run", self.run_script("rollback.sh", "--env", "course", "--region", REGION, "--previous-manifest", previous, **env))
        self.show("rollback.sh infra dry run", self.run_script("rollback.sh", "--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", d, **env))
        self.show("cleanup.sh dry run (listing)", self.run_script("cleanup.sh", "--env", "course", "--region", REGION, **env))
        self.show("cleanup.sh --prepare dry run", self.run_script("cleanup.sh", "--env", "course", "--region", REGION, "--prepare", **env))
        # key refusals
        self.show("REFUSAL: plan.sh --plan-out with a pre-existing symlink at the .json name", self._symlink_plan(env))
        os.remove(self.state_path())
        self.write_state()
        self.show("REFUSAL: plan.sh --execute without a live state file", self._no_state(env))

    def _symlink_plan(self, env):
        plans = os.path.join(self.repo, "target", "plans")
        os.makedirs(plans, exist_ok=True)
        canary = os.path.join(self.tmp, "canary.txt")
        with open(canary, "w") as handle:
            handle.write("CANARY\n")
        os.symlink(canary, os.path.join(plans, "x.tfplan.json"))
        env2 = dict(env, FAKE_SHOW_JSON=self.write_show_json([], name="s.json"))
        return self.run_script("plan.sh", "--env", "course", "--region", REGION, "--profile", "p", "--plan-out", os.path.join(plans, "x.tfplan"), "--execute", **env2)

    def _no_state(self, env):
        os.remove(self.state_path())
        return self.run_script("plan.sh", "--env", "course", "--region", REGION, "--profile", "p", "--execute", **env)


if __name__ == "__main__":
    suite = unittest.TestSuite([Demo("test_all")])
    unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)

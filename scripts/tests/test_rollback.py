"""rollback.sh (policy 13-5): delegates to plan.sh and deploy.sh; dry run by default.

Repair round 1: F7 (the current scripts run against a previous commit's materialized Terraform source;
a previous tree without scripts/ works), F5/F2 inherited through deploy.sh, N1 (--profile in printed commands).
"""
import glob
import json
import os
import stat
import unittest

from helpers import FAKE_ACCOUNT, FAKE_SECRET, REGION, SERVICES, Fixture, account_hash, head_object_text, registry_digest, sha256_bytes

PREV = "c" * 40
ARCHIVE_BYTES = b"tiny-runtime-archive"


class RollbackBase(Fixture):
    def setUp(self):
        super().setUp()
        self.previous = self.write_deploy_manifest(revision=PREV, digests={s: registry_digest(s, PREV) for s in SERVICES})
        self.private_vars = os.path.join(self.tmp, "private.local.tfvars")
        with open(self.private_vars, "w") as handle:
            handle.write("x = 1\n")
        self.show = self.write_show_json([], image_revision=PREV)
        self.archive = os.path.join(self.tmp, "runtime.tgz")
        with open(self.archive, "wb") as handle:
            handle.write(ARCHIVE_BYTES)
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE_BYTES)), RUNTIME_ARCHIVE_EXPECTED_SHA256=sha256_bytes(ARCHIVE_BYTES))
        self.env_all = {
            "SCHOLARCHAIN_TF_PRIVATE_VARS": self.private_vars,
            "FAKE_SHOW_JSON": self.show,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE": self.archive,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI": "s3://bucket-test/key/runtime.tgz",
            "FAKE_HEAD_OBJECT": head_object_text(ARCHIVE_BYTES),
            "FAKE_ECS_TAG": PREV,
        }

    def rollback(self, *args, **env):
        merged = dict(self.env_all)
        merged.update(env)
        return self.run_script("rollback.sh", *args, **merged)

    def arrange_deploy_inputs(self, stage, commit=None, revision=None, name="rollback.tfplan"):
        """Plan, plan receipt, planned-variable fixture, pre-spend receipt and a NEW approval record."""
        plan, sha = self.make_plan(name=name)
        commit = commit or self.head()
        self.write_plan_receipt(plan, sha, commit=commit, scripts_commit=self.head(), image_revision=revision)
        self.env_all["FAKE_SHOW_JSON"] = self.write_show_json([], image_revision=revision, name="rollback-show.json")
        prespend, prespend_sha = self.write_prespend()
        approval = self.write_approval(self.approval_text(sha, commit=commit, prespend_sha=prespend_sha, stage=stage, receipt_sha=self.receipt_sha(plan)))
        return plan, sha, approval, prespend


class RollbackDryRunTests(RollbackBase):
    def test_app_dry_run_shows_replan_digest_check_and_deploy_without_running_anything(self):
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous)
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: DRY-RUN"))
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])
        for step in ("previous-manifest", "verify-registry-digests", "delegate-plan", "delegate-deploy"):
            self.assertIn(step, result.steps())
        out = result.stdout
        self.assertIn("rolling back to image revision %s" % PREV, out)
        # The re-plan carries image_revision=<previous commit SHA>, through plan.sh.
        self.assertIn("-var=image_revision=%s" % PREV, out)
        self.assertIn("plan.sh --env course --region us-east-2", out.replace("\\", ""))
        # The registry tag is checked against the recorded digest (printed, not run).
        for svc in SERVICES:
            self.assertIn("--repository-name scholarchain-course/%s" % svc, out)
        self.assertIn("imageTag=%s" % PREV, out)
        self.assertIn("would require scholarchain-course/query-api:%s to resolve to %s" % (PREV, registry_digest("query-api", PREV)), out)
        # Then deploy.sh --stage runtime-apply with --reuse-images and a new approval record.
        self.assertIn("--stage runtime-apply", out)
        self.assertIn("--reuse-images", out)
        self.assertIn("scripts/deploy.sh", out)
        self.assertIn("NEW approval record", out)
        self.assertIn("approval point 1", out)

    def test_profile_is_propagated_to_every_printed_delegated_command(self):
        """N1: an explicitly supplied --profile appears in the printed plan.sh and deploy.sh commands."""
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "my-approved-profile")
        self.assertEqual(result.rc, 0, result.out)
        plan_lines = [l for l in result.stdout.splitlines() if "plan.sh" in l and l.startswith("CMD:")]
        deploy_lines = [l for l in result.stdout.splitlines() if l.startswith("DRY-RUN CMD:") and "scripts/deploy.sh" in l]
        self.assertEqual(len(plan_lines), 1)
        self.assertEqual(len(deploy_lines), 1)
        self.assertIn("--profile my-approved-profile", plan_lines[0])
        self.assertIn("--profile my-approved-profile", deploy_lines[0])
        self.assertIn("--execute", deploy_lines[0])
        self.assertIn("-var=aws_profile=my-approved-profile", result.stdout, "the delegated plan dry run shows the profile too")

    def test_profile_placeholder_is_printed_when_none_was_given(self):
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous, AWS_PROFILE=None)
        self.assertIn("--profile <profile>", result.stdout)

    def test_dry_run_with_plan_also_runs_the_local_deploy_checks(self):
        plan, sha, approval, prespend = self.arrange_deploy_inputs("runtime-apply", revision=PREV)
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--plan", plan, "--approval", approval, "--prespend", prespend)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("rollback mode: reusing images already in the registry", result.out)
        self.assertEqual(self.mutating_calls(), [])
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [], "R8: the delegated deploy dry run runs no show, init or aws command")
        self.assertIn("DEFERRED to --execute", result.out)
        self.assertIn("--prespend %s" % prespend, result.out)

    def test_infra_dry_run_prints_the_materialization_flow_not_a_checkout(self):
        result = self.rollback("--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", self.head())
        self.assertEqual(result.rc, 0, result.out)
        self.assertNotIn("git switch", result.out)
        self.assertIn("--source-commit %s" % self.head(), result.out)
        self.assertIn("--stage base-apply", result.out)
        self.assertIn("materialized read-only", result.out)
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])

    def test_bad_manifest_or_usage_is_rejected(self):
        self.assertEqual(self.rollback("--env", "course", "--region", REGION).rc, 2)
        self.assertEqual(self.rollback("--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", "abc").rc, 2)
        self.assertEqual(self.rollback("--env", "course", "--region", REGION, "--mode", "weird").rc, 2)
        missing = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", os.path.join(self.tmp, "nope.json"))
        self.assertEqual(missing.rc, 3, missing.out)
        bad = os.path.join(self.tmp, "bad.json")
        with open(bad, "w") as handle:
            handle.write('{"schema":"scholarchain.deploy-manifest.v1","image_revision":"c","images":[]}')
        self.assertEqual(self.rollback("--env", "course", "--region", REGION, "--previous-manifest", bad).rc, 3)

    def test_wrong_terraform_version_refused(self):
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous, FAKE_TF_VERSION="1.13.4")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("1.13.4", result.out)


class RollbackExecuteTests(RollbackBase):
    def test_execute_needs_a_stage(self):
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "p", "--execute")
        self.assertEqual(result.rc, 2, result.out)

    def test_stage_plan_replans_with_previous_revision_and_never_applies(self):
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "approved", "--stage", "plan", "--execute")
        self.assertEqual(result.rc, 0, result.out)
        plans = [a for n, a in self.calls("terraform") if " plan " in " " + a + " "]
        self.assertEqual(len(plans), 1)
        self.assertIn("-var=image_revision=%s" % PREV, plans[0])
        self.assertRegex(plans[0], r"-out=\S+/target/plans/\S+/course-%s\.tfplan" % self.head())
        self.assertIn("PLAN-FILE: ", result.out)
        self.assertEqual(self.mutating_calls(), [])
        self.assertIn("write a NEW approval record", result.out)

    def test_registry_tag_that_moved_refuses_before_any_plan(self):
        result = self.rollback(
            "--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "approved", "--stage", "plan", "--execute",
            FAKE_IMAGE_DIGEST="sha256:" + "9" * 64,
        )
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "verify-registry-digests")
        self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " "], [])

    def test_stage_deploy_requires_the_new_approval_record_and_pushes_nothing(self):
        plan, sha, approval, prespend = self.arrange_deploy_inputs("runtime-apply", revision=PREV)
        result = self.rollback(
            "--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "approved", "--stage", "deploy",
            "--plan", plan, "--approval", approval, "--prespend", prespend, "--execute",
        )
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual([a for n, a in self.calls("docker") if a.startswith("push")], [])
        applied = [l for l in open(self.log + ".applied").read().splitlines()]
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0].split("\t")[1], sha, "exactly the approved plan bytes")
        self.assertNotIn(FAKE_ACCOUNT, result.out)
        self.assertEqual(len([a for n, a in self.calls("aws") if a.startswith("ecs describe-task-definition")]), 4)

    def test_stage_deploy_without_a_matching_record_is_refused_and_applies_nothing(self):
        plan, _sha, approval, prespend = self.arrange_deploy_inputs("runtime-apply", revision=PREV)
        approval = self.write_approval(self.approval_text("0" * 64, prespend_sha=_sha256(prespend), stage="runtime-apply"), name="wrong-record.md")
        result = self.rollback(
            "--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "approved", "--stage", "deploy",
            "--plan", plan, "--approval", approval, "--prespend", prespend, "--execute",
        )
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("plan sha256", result.out)
        self.assertEqual(self.mutating_calls(), [])
        self.assertEqual([a for _n, a in self.calls("aws") if not a.startswith("ecr describe-images")], [], "only rollback.sh's own read-only digest verification ran")

    def test_stage_deploy_without_a_prespend_receipt_is_refused_before_any_aws_call(self):
        """F5 through rollback: a rollback deploy inherits the pre-spend gate."""
        plan, _sha, approval, prespend = self.arrange_deploy_inputs("runtime-apply", revision=PREV)
        os.remove(prespend)
        result = self.rollback(
            "--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "approved", "--stage", "deploy",
            "--plan", plan, "--approval", approval, "--prespend", prespend, "--execute",
        )
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("pre-spend receipt not found", result.out)
        self.assertEqual([a for _n, a in self.calls("aws") if not a.startswith("ecr describe-images")], [], "no sts, push or upload: only the read-only digest verification ran")
        self.assertEqual(self.mutating_calls(), [])

    def test_no_secret_in_output(self):
        result = self.rollback("--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "approved", "--stage", "plan", "--execute")
        for forbidden in (FAKE_SECRET, FAKE_ACCOUNT, self.private_vars, account_hash() + "x"):
            self.assertNotIn(forbidden, result.out)


def _sha256(path):
    with open(path, "rb") as handle:
        return sha256_bytes(handle.read())


class InfraRollbackFromATreeWithoutScriptsTests(RollbackBase):
    """F7: the CURRENT scripts run against the previous commit's Terraform source; the previous tree has no scripts/."""

    def setUp(self):
        super().setUp()
        self.prev_commit = self.head()  # the fixture's first commit: no scripts/ directory at all
        self.assertFalse(os.path.exists(os.path.join(self.repo, "scripts")))
        self.write(".gitignore", "target/\n*.local.tfvars\n")
        self.write("infra/terraform/versions.tf", "# CHANGED later\n")
        self.write("infra/terraform/only-in-newer.tf", "# added after the rollback target\n")
        self.write("scripts/marker.txt", "the newer tree carries scripts/\n")
        self.new_head = self.commit("newer tree")
        self.assertNotEqual(self.new_head, self.prev_commit)
        # An ignored, uncommitted private file sits in the working tree: it must never reach the materialized source.
        self.write("infra/terraform/private.local.tfvars", "secret_like = 1\n")
        self.env_all["FAKE_SHOW_JSON"] = self.write_show_json([], image_revision=None)

    def infra(self, stage, *extra, **env):
        return self.rollback(
            "--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", self.prev_commit, "--profile", "approved",
            "--stage", stage, *extra, "--execute", **env,
        )

    def source_bases(self):
        return glob.glob(os.path.join(os.path.realpath(self.repo), "target", "plans", "*", "source", self.prev_commit))

    def chdir_lines(self):
        path = self.log + ".chdir"
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def test_stage_plan_materializes_the_previous_source_read_only_and_records_the_previous_commit(self):
        result = self.infra("plan")
        self.assertEqual(result.rc, 0, result.out)
        bases = self.source_bases()
        self.assertEqual(len(bases), 1)
        root = os.path.join(bases[0], "infra", "terraform")
        with open(os.path.join(root, "versions.tf")) as handle:
            self.assertEqual(handle.read(), "# root\n", "the PREVIOUS commit's content, not the working tree's")
        self.assertFalse(os.path.exists(os.path.join(root, "only-in-newer.tf")))
        self.assertFalse(os.path.exists(os.path.join(bases[0], "scripts")), "the previous tree has no scripts and none is needed")
        self.assertFalse(os.path.exists(os.path.join(root, "private.local.tfvars")))
        mode = os.stat(os.path.join(root, "versions.tf")).st_mode
        self.assertEqual(mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH), 0, "materialized source is read-only")
        # terraform runs in the materialized directory, bound to the LIVE state file (R1), with an isolated TF_DATA_DIR.
        inits = [a for n, a in self.calls("terraform") if " init " in " " + a + " "]
        self.assertEqual(len(inits), 1)
        self.assertTrue(inits[0].startswith("-chdir=%s " % root) and inits[0].endswith("-lockfile=readonly"), "read-only source: init must not rewrite a lock file: " + inits[0])
        plans = [a for n, a in self.calls("terraform") if " plan " in " " + a + " "]
        self.assertEqual(len(plans), 1)
        self.assertTrue(plans[0].startswith("-chdir=%s " % root), plans[0])
        for sub, chdir, _files, binding in self.chdir_lines():
            if sub in ("init", "plan", "show"):
                self.assertEqual(chdir, root)
                self.assertEqual(binding, os.path.realpath(self.state_path()), "the rollback plans against the EXISTING live state")
        run_dir = os.path.dirname(os.path.dirname(bases[0]))
        self.assertTrue(any("TF_DATA_DIR=%s" % os.path.join(run_dir, "tfdata") in line for line in self.timeout_helper_lines()))
        # The receipt records the PREVIOUS commit as the planned source, HEAD as the scripts commit and the live state identity.
        receipts = glob.glob(os.path.join(os.path.realpath(self.repo), "target", "plans", "*", "*.receipt.json"))
        self.assertEqual(len(receipts), 1)
        with open(receipts[0]) as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["commit"], self.prev_commit)
        self.assertEqual(receipt["scripts_commit"], self.new_head)
        self.assertTrue(receipt["clean"])
        self.assertEqual(receipt["state"], self.state_identity())
        self.assertEqual(receipt["source_tree_sha256"], self.tree_sha(self.prev_commit))
        self.assertIn("PLAN-FILE: ", result.stdout)
        self.assertEqual(self.mutating_calls(), [])
        # The work tree and HEAD were never changed.
        self.assertEqual(self.head(), self.new_head)
        self.assertTrue(os.path.exists(os.path.join(self.repo, "infra", "terraform", "only-in-newer.tf")))

    def test_stage_deploy_applies_the_verified_plan_from_the_materialized_source(self):
        plan, sha, approval, prespend = self.arrange_deploy_inputs("base-apply", commit=self.prev_commit, revision=None)
        result = self.infra("deploy", "--plan", plan, "--approval", approval, "--prespend", prespend)
        self.assertEqual(result.rc, 0, result.out)
        applies = [a for n, a in self.calls("terraform") if " apply " in " " + a + " "]
        self.assertEqual(len(applies), 1)
        self.assertIn("/source/%s/infra/terraform " % self.prev_commit, applies[0])
        self.assertNotIn(os.path.join(os.path.realpath(self.repo), "infra", "terraform "), applies[0])
        apply_line = [l for l in self.chdir_lines() if l[0] == "apply"][0]
        self.assertEqual(apply_line[3], os.path.realpath(self.state_path()), "apply uses the live state file too")
        self.assertEqual(self.calls("docker"), [], "an infrastructure rollback pushes nothing")
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3")], [], "and uploads no archive")
        with open(self.log + ".applied") as handle:
            self.assertEqual(handle.read().split("\t")[1].strip(), sha)

    def test_the_approved_commit_must_be_the_previous_commit(self):
        plan, sha, approval, prespend = self.arrange_deploy_inputs("base-apply", commit=self.new_head, revision=None)
        result = self.infra("deploy", "--plan", plan, "--approval", approval, "--prespend", prespend)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("source commit %s != APPROVED_COMMIT" % self.prev_commit, result.out)
        self.assertEqual(self.mutating_calls(), [])

    def test_a_receipt_for_the_wrong_source_commit_is_refused(self):
        plan, sha, approval, prespend = self.arrange_deploy_inputs("base-apply", commit=self.prev_commit, revision=None)
        self.write_plan_receipt(plan, sha, commit=self.new_head, scripts_commit=self.new_head, image_revision=None)
        approval = self.write_approval(self.approval_text(sha, commit=self.prev_commit, prespend_sha=_sha256(prespend), stage="base-apply", receipt_sha=self.receipt_sha(plan)), name="re-reviewed.md")
        result = self.infra("deploy", "--plan", plan, "--approval", approval, "--prespend", prespend)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("receipt commit differs", result.out)
        self.assertEqual(self.mutating_calls(), [])

    def test_unknown_previous_commit_is_refused(self):
        result = self.rollback(
            "--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", "e" * 40, "--profile", "approved", "--stage", "plan", "--execute"
        )
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "previous-commit")
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])

    def test_previous_commit_without_the_terraform_root_is_refused(self):
        import subprocess

        empty = subprocess.run(["git", "-C", self.repo, "hash-object", "-t", "tree", "/dev/null"], capture_output=True, text=True, check=True).stdout.strip()
        orphan = subprocess.run(
            ["git", "-C", self.repo, "-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit-tree", empty, "-m", "no terraform"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        result = self.rollback(
            "--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", orphan, "--profile", "approved", "--stage", "plan", "--execute"
        )
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("has no infra/terraform", result.out)


if __name__ == "__main__":
    unittest.main()

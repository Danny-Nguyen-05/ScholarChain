"""plan.sh: dry run runs nothing; execute (fakes) records a v2 provenance receipt and never applies.

Repair round 1: F2 (receipt provenance), F4 (private outputs inside the ignored plan dir, redaction),
F8 (complete review path), N1 (bounded version probe). Repair round 2: R1 (state binding), R2 (confined private
outputs, one fresh run directory per run), R3 (plan from a git archive, planned environment and project checked,
receipt bound by hash). Expectations are hand-derived.
"""
import glob
import json
import os
import re
import stat
import subprocess
import unittest

from helpers import FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, REGION, STATE_LINEAGE, Fixture, account_hash, sha256_bytes

PRIVATE_CANARY = "CANARY-PRIVATE-VALUE-ALPHA-7781"
EMAIL_CANARY = "canary.owner@example.invalid"

OTHER_ACCOUNT = "999988887777"
CHANGES = [
    ("aws_s3_bucket.a", "aws_s3_bucket", ["create"]),
    ("aws_iam_role.r", "aws_iam_role", ["create"]),
    ("aws_dynamodb_table.t", "aws_dynamodb_table", ["update"]),
    ("aws_neptune_cluster.n", "aws_neptune_cluster", ["delete", "create"]),
    ("aws_instance.i", "aws_instance", ["delete"]),
    ("aws_kms_key.k", "aws_kms_key", ["no-op"]),
    ("aws_cloudwatch_log_group.l", "aws_cloudwatch_log_group", ["create"]),
    ("aws_iam_role_policy.p", "aws_iam_role_policy", ["update"]),
]


class PlanBase(Fixture):
    def setUp(self):
        super().setUp()
        self.private_vars = os.path.join(self.tmp, "secret-private.local.tfvars")
        with open(self.private_vars, "w") as handle:
            handle.write("aws_account_id = \"%s\"\nnotification_email = \"%s\"\nowner_note = \"%s\"\n" % (FAKE_ACCOUNT, EMAIL_CANARY, PRIVATE_CANARY))
        self.show = self.write_show_json(CHANGES)

    def plan(self, *args, **env):
        return self.run_script("plan.sh", *args, **env)

    def artifact(self, suffix=""):
        """The single default-named artifact of the (one) run: <PLAN_DIR>/<run-id>/course-<head>.tfplan<suffix>."""
        found = glob.glob(os.path.join(self.repo, "target", "plans", "*", "course-%s.tfplan%s" % (self.head(), suffix)))
        self.assertEqual(len(found), 1, found)
        return found[0]

    def execute_env(self, **extra):
        env = {
            "SCHOLARCHAIN_TF_PRIVATE_VARS": self.private_vars,
            "FAKE_SHOW_JSON": self.show,
            "FAKE_PLAN_SALT": "salt-1",
        }
        env.update(extra)
        return env


class PlanDryRunTests(PlanBase):
    def test_dry_run_prints_exact_commands_and_runs_nothing(self):
        result = self.plan("--env", "course", "--region", REGION)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(result.result_line()[:15], "RESULT: DRY-RUN")
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [], "dry run must run no aws or terraform command")
        for step in ("inputs", "output-paths", "terraform-version", "materialize-source", "account-identity", "terraform-init", "terraform-plan", "terraform-show", "terraform-show-text", "plan-receipt"):
            self.assertIn(step, result.steps())
        out = result.stdout
        self.assertIn("aws sts get-caller-identity --region us-east-2 --query Account --output text", out)
        self.assertIn(" init -input=false -lockfile=readonly", out)
        self.assertIn(" plan -input=false -lock-timeout=60s", out)
        # The plan runs from a materialized git archive inside a fresh run directory, never from the work tree.
        match = re.search(r"-var-file=(\S+/target/plans/(\S+?)/source/%s/infra/terraform/environments/course\.tfvars)" % self.head(), out)
        self.assertIsNotNone(match, out)
        self.assertNotIn("-chdir=%s " % os.path.join(os.path.realpath(self.repo), "infra", "terraform"), out)
        self.assertIn("-var-file=<private-vars-file>", out)
        self.assertIn("-var=aws_region=us-east-2", out)
        self.assertIn("-var=aws_profile=<profile>", out)
        self.assertRegex(out, r"/target/plans/\S+/course-%s\.tfplan" % self.head())
        self.assertIn(" show -json ", out)
        self.assertIn(" show -no-color ", out)
        self.assertNotIn(" apply", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "plans")), "a dry run writes nothing")

    def test_dry_run_with_private_vars_never_echoes_the_path(self):
        result = self.plan("--env", "course", "--region", REGION, **self.execute_env())
        self.assertEqual(result.rc, 0, result.out)
        self.assertNotIn(self.private_vars, result.out)
        self.assertNotIn("secret-private.local.tfvars", result.out)
        self.assertIn("-var-file=<redacted>", result.stdout)

    def test_image_revision_is_validated_and_passed(self):
        bad = self.plan("--env", "course", "--region", REGION, "--image-revision", "abc")
        self.assertEqual(bad.rc, 2)
        good = self.plan("--env", "course", "--region", REGION, "--image-revision", "c" * 40)
        self.assertEqual(good.rc, 0, good.out)
        self.assertIn("-var=image_revision=%s" % ("c" * 40), good.stdout)

    def test_region_from_environment_variable(self):
        result = self.plan("--env", "course", SCHOLARCHAIN_AWS_REGION="eu-west-1")
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("-var=aws_region=eu-west-1", result.stdout)

    def test_refusals_and_usage_errors(self):
        self.assertEqual(self.plan("--region", REGION).rc, 2)
        self.assertEqual(self.plan("--env", "course").rc, 2)
        self.assertEqual(self.plan("--env", "course", "--region", "Ohio").rc, 2)
        missing = self.plan("--env", "nonexistent", "--region", REGION)
        self.assertEqual(missing.rc, 3)
        self.assertIn("environment file not found", missing.out)
        self.assertEqual(self.plan("--bogus").rc, 2)

    def test_wrong_terraform_version_names_the_found_version(self):
        result = self.plan("--env", "course", "--region", REGION, FAKE_TF_VERSION="1.13.4")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("terraform version 1.13.4 found; exactly 1.13.5 is required", result.out)
        self.assertEqual(result.steps()[-1], "terraform-version")

    def test_required_version_cannot_be_lowered_by_the_environment(self):
        result = self.plan("--env", "course", "--region", REGION, FAKE_TF_VERSION="1.13.4", REQUIRED_TERRAFORM_VERSION="1.13.4")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("exactly 1.13.5 is required", result.out)
        self.assertIn("CONFIG-IGNORED", result.stdout)

    def test_fixture_config_file_is_announced(self):
        self.use_config(REQUIRED_TERRAFORM_VERSION="1.13.4")
        result = self.plan("--env", "course", "--region", REGION, FAKE_TF_VERSION="1.13.4")
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("CONFIG-FILE: using", result.stdout)

    def test_terraform_bin_override(self):
        fake = os.path.join(self.tmp, "other-terraform")
        with open(fake, "w") as handle:
            handle.write('#!/bin/bash\necho \'{"terraform_version":"1.9.0"}\'\n')
        os.chmod(fake, 0o755)
        result = self.plan("--env", "course", "--region", REGION, TERRAFORM_BIN=fake)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("1.9.0", result.out)


class PlanExecuteTests(PlanBase):
    def test_execute_requires_profile_and_private_vars(self):
        no_profile = self.plan("--env", "course", "--region", REGION, "--execute", **self.execute_env())
        self.assertEqual(no_profile.rc, 3, no_profile.out)
        self.assertIn("profile", no_profile.out)
        no_vars = self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", SCHOLARCHAIN_TF_PRIVATE_VARS=None)
        self.assertEqual(no_vars.rc, 3, no_vars.out)
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])

    def test_receipt_summary_and_no_apply(self):
        result = self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env())
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PASS"))
        calls = [c for c in self.calls() if not c[1].startswith("version")]
        self.assertEqual(calls[0][0:2], ("aws", "sts get-caller-identity --region %s --query Account --output text" % REGION))
        words = " ".join(a for _, a in calls)
        self.assertNotIn(" apply", " " + words)
        self.assertNotIn("destroy", words)
        plan_file = self.artifact()
        self.assertEqual(os.path.realpath(plan_file), os.path.realpath(self.plan_file_of(result)))
        with open(plan_file, "rb") as handle:
            plan_bytes = handle.read()
        receipt_path = plan_file + ".receipt.json"
        with open(receipt_path) as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["plan_sha256"], sha256_bytes(plan_bytes))
        self.assertEqual(receipt["schema"], "scholarchain.plan-receipt.v2")
        self.assertEqual(receipt["commit"], self.head())
        self.assertEqual(receipt["scripts_commit"], self.head())
        self.assertIs(receipt["clean"], True)
        self.assertIsNone(receipt["image_revision"])
        self.assertRegex(receipt["created_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(receipt["region"], REGION)
        self.assertEqual(receipt["account_sha256"], account_hash())
        self.assertEqual(receipt["account_binding"], "matched")
        self.assertEqual(receipt["env"], "course")
        self.assertEqual(receipt["terraform_version"], "1.13.5")
        summary = receipt["summary"]
        # Hand-derived from CHANGES: creates {bucket, role, log group}, updates {table, role policy},
        # one delete, one replace (delete+create), one no-op.
        self.assertEqual((summary["add"], summary["change"], summary["destroy"], summary["replace"], summary["no_op"]), (3, 2, 1, 1, 1))
        self.assertEqual({e["address"] for e in summary["iam_resource_changes"]}, {"aws_iam_role.r", "aws_iam_role_policy.p"})
        self.assertEqual(
            {e["address"] for e in summary["stateful_resource_changes"]},
            {"aws_s3_bucket.a", "aws_dynamodb_table.t", "aws_neptune_cluster.n", "aws_cloudwatch_log_group.l"},
        )
        replaced = [e for e in summary["stateful_resource_changes"] if e["address"] == "aws_neptune_cluster.n"][0]
        self.assertEqual(replaced["actions"], "delete+create")
        # Approval-record candidate lines for the human, and nothing sensitive anywhere.
        self.assertIn("APPROVED_PLAN_SHA256=%s" % sha256_bytes(plan_bytes), result.stdout)
        self.assertIn("APPROVED_COMMIT=%s" % self.head(), result.stdout)
        self.assertIn("APPROVED_ACCOUNT_SHA256=%s" % account_hash(), result.stdout)
        self.assertIn("APPROVED_REGION=%s" % REGION, result.stdout)
        with open(receipt_path) as handle:
            receipt_text = handle.read()
        for forbidden in (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, self.private_vars):
            self.assertNotIn(forbidden, result.out)
            self.assertNotIn(forbidden, receipt_text)

    def test_every_execute_command_goes_through_the_timeout_helper(self):
        self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env())
        helper = self.timeout_helper_lines()
        self.assertEqual(len(helper), len(self.calls()), "every external command, including the terraform version probe, is recorded by the helper")
        self.assertTrue(any("terraform" in l and " plan " in l for l in helper))
        self.assertTrue(any(l.startswith("timeout=1800 ") for l in helper), "plan uses the plan timeout")

    def test_children_run_with_the_approved_profile_set(self):
        result = self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env())
        self.assertEqual(result.rc, 0)
        profiles = [profile for _name, args, profile in self.raw_calls() if not args.startswith("version")]
        self.assertTrue(profiles)
        self.assertTrue(all(profile == "profile=set" for profile in profiles))

    def test_plan_for_a_different_account_is_a_gate_failure(self):
        show = self.write_show_json(CHANGES, account=OTHER_ACCOUNT)
        result = self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env(FAKE_SHOW_JSON=show))
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("ACCOUNT-BINDING-MISMATCH", result.out)
        self.assertNotIn(OTHER_ACCOUNT, result.out)
        self.assertNotIn(FAKE_ACCOUNT, result.out)
        self.assertEqual([c for c in self.calls() if " apply" in c[1]], [])

    def test_terraform_plan_failure_exit_5(self):
        result = self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env(FAKE_TF_PLAN_RC="1"))
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("RESULT: FAIL step=terraform-plan", result.stdout)

    def test_dirty_tree_is_recorded_not_hidden(self):
        self.write("junk.txt", "x\n")
        result = self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env())
        self.assertEqual(result.rc, 0, result.out)
        receipt = self.artifact(".receipt.json")
        with open(receipt) as handle:
            self.assertFalse(json.load(handle)["clean"])

    def test_failing_git_status_is_recorded_as_not_clean(self):
        self.install_git_wrapper("fail")
        result = self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env())
        self.assertEqual(result.rc, 0, result.out)
        receipt = self.artifact(".receipt.json")
        with open(receipt) as handle:
            self.assertFalse(json.load(handle)["clean"], "an unreadable tree is never recorded as clean")


class PlanOutputPathTests(PlanBase):
    """F4/R2: every plan output lives inside the ignored plan directory, is absent beforehand, distinct and confined."""

    def run_plan(self, *extra, **env):
        merged = self.execute_env()
        merged.update(env)
        return self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", *extra, **merged)

    def assert_refused_before_any_write(self, result, needle):
        self.assertEqual(result.rc, 3, result.out)
        self.assertRegex(result.out, needle)
        self.assertEqual(result.steps()[-1], "output-paths")
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [], "refused before any aws or terraform command")

    def plans_dir(self):
        return os.path.join(self.repo, "target", "plans")

    def test_plan_out_at_the_repo_root_is_refused(self):
        """The reviewer's attack: course.plan passes the *.plan ignore rule, but its .json export would not."""
        for name in ("course.plan", os.path.join(self.repo, "course.plan"), os.path.join(self.repo, "course.tfplan")):
            with self.subTest(name):
                result = self.run_plan("--plan-out", name)
                self.assert_refused_before_any_write(result, "must live inside target/plans")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "course.plan.json")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "course.plan")))

    def test_plan_out_outside_the_repo_is_refused(self):
        result = self.run_plan("--plan-out", os.path.join(self.tmp, "elsewhere.tfplan"))
        self.assert_refused_before_any_write(result, "must live inside target/plans")

    def test_plan_out_that_escapes_through_dotdot_or_a_symlink_is_refused(self):
        os.makedirs(self.plans_dir())
        os.symlink(self.repo, os.path.join(self.plans_dir(), "link"))
        for name in (os.path.join(self.plans_dir(), "..", "escape.tfplan"), os.path.join(self.plans_dir(), "link", "escape.tfplan")):
            with self.subTest(name):
                self.assert_refused_before_any_write(self.run_plan("--plan-out", name), "must live inside target/plans")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "escape.tfplan")))

    def test_a_symlinked_directory_component_inside_the_plan_dir_is_refused(self):
        outside = os.path.join(self.tmp, "outside-dir")
        os.makedirs(outside)
        os.makedirs(self.plans_dir())
        os.symlink(outside, os.path.join(self.plans_dir(), "sub"))
        result = self.run_plan("--plan-out", os.path.join(self.plans_dir(), "sub", "x.tfplan"))
        self.assert_refused_before_any_write(result, "symlink")
        self.assertEqual(os.listdir(outside), [], "nothing was written through the symlinked directory")

    def test_receipt_outside_the_plan_dir_is_refused(self):
        result = self.run_plan("--receipt", os.path.join(self.repo, "receipt.json"))
        self.assert_refused_before_any_write(result, "--receipt must live inside")

    def test_a_derived_json_path_that_is_not_ignored_is_refused(self):
        """target/plans is only partly ignored: the plan name is ignored but its .json export is not."""
        self.write(".gitignore", "target/*\n!target/plans/\ntarget/plans/*\n!target/plans/*.tfplan.json\n")
        self.commit("selective ignore")
        result = self.run_plan("--plan-out", os.path.join(self.plans_dir(), "x.tfplan"))
        self.assert_refused_before_any_write(result, "is not git-ignored")
        self.assertIn(".tfplan.json", result.out)
        self.assertFalse(os.path.exists(self.plans_dir()))

    def test_dry_run_also_verifies_the_derived_paths(self):
        self.write(".gitignore", "target/*\n!target/plans/\ntarget/plans/*\n!target/plans/*.tfplan.txt\n")
        self.commit("selective ignore")
        result = self.plan("--env", "course", "--region", REGION, "--plan-out", os.path.join(self.plans_dir(), "x.tfplan"))
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("is not git-ignored", result.out)

    def test_a_plan_out_inside_the_plan_dir_places_every_artifact_there_privately(self):
        name = os.path.join(self.plans_dir(), "sub", "mine.tfplan")
        result = self.run_plan("--plan-out", name)
        self.assertEqual(result.rc, 0, result.out)
        for suffix in ("", ".json", ".txt", ".log", ".receipt.json"):
            path = name + suffix
            self.assertTrue(os.path.isfile(path), path)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600, "%s must be 0600" % path)
        self.assertEqual(stat.S_IMODE(os.stat(self.plans_dir()).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.plans_dir(), "sub")).st_mode), 0o700)
        tracked = subprocess_check(["git", "-C", self.repo, "status", "--porcelain", "--untracked-files=all"])
        self.assertEqual(tracked, "", "no plan output is visible to git")

    def test_each_run_gets_a_fresh_private_run_directory_and_never_touches_an_earlier_one(self):
        first = self.run_plan()
        self.assertEqual(first.rc, 0, first.out)
        first_plan = self.plan_file_of(first)
        with open(first_plan, "rb") as handle:
            first_bytes = handle.read()
        second = self.run_plan(FAKE_PLAN_SALT="salt-2")
        self.assertEqual(second.rc, 0, second.out)
        second_plan = self.plan_file_of(second)
        self.assertNotEqual(os.path.dirname(first_plan), os.path.dirname(second_plan), "a run directory is never reused")
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(second_plan)).st_mode), 0o700)
        with open(first_plan, "rb") as handle:
            self.assertEqual(handle.read(), first_bytes, "the earlier run's plan was not rewritten")

    def test_a_leftover_plan_file_is_never_overwritten(self):
        name = os.path.join(self.plans_dir(), "leftover.tfplan")
        os.makedirs(self.plans_dir())
        with open(name, "w") as handle:
            handle.write("an earlier plan\n")
        result = self.run_plan("--plan-out", name)
        self.assert_refused_before_any_write(result, "already exists")
        with open(name) as handle:
            self.assertEqual(handle.read(), "an earlier plan\n")

    def test_a_preexisting_symlink_at_each_derived_filename_is_refused_and_the_outside_canary_is_unchanged(self):
        """R2 acceptance: a link at the json, txt, log, receipt (or plan) name pointing OUTSIDE the plan dir is never written through."""
        canary = os.path.join(self.tmp, "outside-canary.txt")
        for suffix in ("", ".json", ".txt", ".log", ".receipt.json"):
            with self.subTest(suffix or "plan file"):
                with open(canary, "w") as handle:
                    handle.write("CANARY-UNTOUCHED\n")
                name = os.path.join(self.plans_dir(), "victim%s.tfplan" % ("".join(c for c in suffix if c.isalnum()) or "plan"))
                os.makedirs(self.plans_dir(), exist_ok=True)
                link = name + suffix
                if os.path.lexists(link):
                    os.remove(link)
                os.symlink(canary, link)
                result = self.run_plan("--plan-out", name)
                self.assert_refused_before_any_write(result, "already exists|symlink")
                with open(canary) as handle:
                    self.assertEqual(handle.read(), "CANARY-UNTOUCHED\n")
                os.remove(link)

    def test_a_dangling_symlink_at_a_derived_filename_is_refused(self):
        name = os.path.join(self.plans_dir(), "dangling.tfplan")
        os.makedirs(self.plans_dir())
        target = os.path.join(self.tmp, "does-not-exist-yet.txt")
        os.symlink(target, name + ".txt")
        result = self.run_plan("--plan-out", name)
        self.assert_refused_before_any_write(result, "already exists|symlink")
        self.assertFalse(os.path.exists(target), "the dangling link target was not created")

    def test_colliding_output_paths_are_refused(self):
        plan = os.path.join(self.plans_dir(), "c.tfplan")
        cases = {
            "receipt equals the plan file": ("--receipt", plan),
            "receipt equals the json export": ("--receipt", plan + ".json"),
            "receipt equals the log": ("--receipt", plan + ".log"),
            "receipt differs only by case": ("--receipt", os.path.join(self.plans_dir(), "C.TFPLAN.JSON")),
        }
        for label, (flag, value) in cases.items():
            with self.subTest(label):
                result = self.run_plan("--plan-out", plan, flag, value)
                self.assert_refused_before_any_write(result, "collide")

    def test_the_plan_out_may_not_name_a_directory_that_holds_another_output(self):
        plan = os.path.join(self.plans_dir(), "d.tfplan")
        result = self.run_plan("--plan-out", plan, "--receipt", os.path.join(plan, "inside.json"))
        self.assert_refused_before_any_write(result, "collide")


def subprocess_check(cmd):
    import subprocess

    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


class PlanReviewPathTests(PlanBase):
    """F8: the complete plan is reviewable from a private file; the shareable output lists every action."""

    def many_changes(self, count=75):
        changes = [("aws_s3_bucket.aaa_first_resource", "aws_s3_bucket", ["create"])]
        changes += [("aws_sqs_queue.q%03d" % i, "aws_sqs_queue", ["create"]) for i in range(count)]
        changes += [("aws_iam_role.zzz_last_resource", "aws_iam_role", ["delete"])]
        return changes

    def plan_text(self, count=75):
        lines = ["Terraform will perform the following actions:"]
        lines += ["  # aws_sqs_queue.q%03d will be created" % i for i in range(count)]
        lines.insert(1, "  # aws_s3_bucket.aaa_first_resource will be created")
        lines.append('      + notification_email = "%s"' % EMAIL_CANARY)
        lines.append('      + owner_note = "%s"' % PRIVATE_CANARY)
        path = os.path.join(self.tmp, "plan-text.txt")
        with open(path, "w") as handle:
            handle.write("\n".join(lines) + "\n")
        return path

    def run_long_plan(self):
        show = self.write_show_json(self.many_changes(), name="long-show.json")
        text = self.plan_text()
        result = self.plan(
            "--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env(FAKE_SHOW_JSON=show, FAKE_SHOW_TEXT=text)
        )
        self.assertEqual(result.rc, 0, result.out)
        return result

    def test_a_plan_longer_than_forty_lines_keeps_the_early_action_everywhere_it_must(self):
        result = self.run_long_plan()
        plan_txt = self.artifact(".txt")
        with open(plan_txt) as handle:
            full = handle.read()
        self.assertGreater(len(full.splitlines()), 40)
        self.assertIn("aws_s3_bucket.aaa_first_resource", full.splitlines()[1] + "\n", "the early action is in the full text file")
        # Shareable action list: every resource, never truncated.
        actions = [line for line in result.stdout.splitlines() if line.startswith("PLAN-ACTION: ")]
        self.assertEqual(len(actions), 77, "75 queues + 1 bucket + 1 role: every one is listed")
        self.assertIn("PLAN-ACTION: create aws_s3_bucket.aaa_first_resource", actions)
        self.assertIn("PLAN-ACTION: delete aws_iam_role.zzz_last_resource", actions)
        self.assertIn("PLAN-ACTIONS-END count=77", result.stdout)
        receipt_path = self.artifact(".receipt.json")
        with open(receipt_path) as handle:
            receipt = json.load(handle)
        by_address = {a["address"]: a["actions"] for a in receipt["actions"]}
        self.assertEqual(len(by_address), 77)
        self.assertEqual(by_address["aws_s3_bucket.aaa_first_resource"], "create")
        self.assertEqual(by_address["aws_iam_role.zzz_last_resource"], "delete")

    def test_plan_text_path_and_sha256_are_printed_and_match_the_file(self):
        result = self.run_long_plan()
        plan_txt = self.artifact(".txt")
        with open(plan_txt, "rb") as handle:
            digest = sha256_bytes(handle.read())
        line = [l for l in result.stdout.splitlines() if l.startswith("PLAN-TEXT: ")]
        self.assertEqual(len(line), 1)
        self.assertIn(plan_txt, line[0])
        self.assertIn("sha256=%s" % digest, line[0])
        receipt_path = self.artifact(".receipt.json")
        with open(receipt_path) as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["plan_text_sha256"], digest)

    def test_a_synthetic_private_value_in_the_plan_text_never_reaches_shareable_output(self):
        result = self.run_long_plan()
        plan_txt = self.artifact(".txt")
        with open(plan_txt) as handle:
            text = handle.read()
        self.assertIn(PRIVATE_CANARY, text, "the private file DOES hold the value (so the test is meaningful)")
        receipt_path = self.artifact(".receipt.json")
        with open(receipt_path) as handle:
            receipt_text = handle.read()
        for canary in (PRIVATE_CANARY, EMAIL_CANARY, FAKE_ACCOUNT):
            self.assertNotIn(canary, result.stdout)
            self.assertNotIn(canary, result.stderr)
            self.assertNotIn(canary, receipt_text)

    def test_the_plan_text_is_not_echoed_on_success(self):
        result = self.run_long_plan()
        self.assertNotIn("will be created", result.out, "the plan body is reviewed from the private file, not the console")


class PlanRedactionTests(PlanBase):
    """F4: subprocess diagnostics, argv and retained logs carry no canary private value."""

    def run_failing_plan(self):
        emit = "Error: invalid value %s for var.owner_note; account %s; token %s" % (PRIVATE_CANARY, FAKE_ACCOUNT, FAKE_TOKEN)
        return self.plan(
            "--env", "course", "--region", REGION, "--profile", "approved", "--execute",
            **self.execute_env(FAKE_TF_PLAN_RC="1", FAKE_EMIT=emit),
        )

    def test_failure_diagnostics_are_redacted_on_stdout_and_stderr(self):
        result = self.run_failing_plan()
        self.assertEqual(result.rc, 5, result.out)
        for canary in (PRIVATE_CANARY, EMAIL_CANARY, FAKE_ACCOUNT, FAKE_TOKEN, FAKE_SECRET):
            self.assertNotIn(canary, result.stdout, canary)
            self.assertNotIn(canary, result.stderr, canary)
        self.assertIn("<redacted>", result.stdout)

    def test_retained_plan_log_and_timeout_trace_are_redacted(self):
        self.run_failing_plan()
        log = self.artifact(".log")
        with open(log) as handle:
            retained = handle.read()
        self.assertIn("<redacted>", retained, "the error text is retained, redacted")
        with open(self.timeout_log) as handle:
            trace = handle.read()
        for canary in (PRIVATE_CANARY, EMAIL_CANARY, FAKE_ACCOUNT, FAKE_TOKEN, FAKE_SECRET, self.private_vars):
            self.assertNotIn(canary, retained, canary)
            self.assertNotIn(canary, trace, canary)
        self.assertIn("-var-file=<redacted>", trace)
        self.assertEqual(stat.S_IMODE(os.stat(log).st_mode), 0o600)

    def test_account_bearing_argv_is_redacted_in_the_trace(self):
        trace_before = len(self.timeout_helper_lines())
        result = self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", **self.execute_env())
        self.assertEqual(result.rc, 0, result.out)
        trace = "\n".join(self.timeout_helper_lines()[trace_before:])
        self.assertNotIn(FAKE_ACCOUNT, trace)
        self.assertNotIn(PRIVATE_CANARY, trace)


class PlanTargetBindingTests(PlanBase):
    """F2 (plan side): the saved plan's own region and image_revision are checked against the inputs."""

    def run_with_show(self, show, *extra):
        return self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", *extra, **self.execute_env(FAKE_SHOW_JSON=show))

    def test_planned_region_mismatch_is_a_gate_failure_and_writes_no_receipt(self):
        show = self.write_show_json(CHANGES, region="us-west-2", name="west.json")
        result = self.run_with_show(show)
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("planned provider region us-west-2 != expected %s" % REGION, result.out)
        self.assertEqual(glob.glob(os.path.join(self.repo, "target", "plans", "*", "*.receipt.json")), [], "no receipt on a gate failure")

    def test_planned_image_revision_must_equal_the_requested_one(self):
        revision = "c" * 40
        good = self.write_show_json(CHANGES, image_revision=revision, name="good.json")
        self.assertEqual(self.run_with_show(good, "--image-revision", revision).rc, 0)
        receipt = self.artifact(".receipt.json")
        with open(receipt) as handle:
            self.assertEqual(json.load(handle)["image_revision"], revision)
        bad = self.write_show_json(CHANGES, image_revision="d" * 40, name="bad.json")
        result = self.run_with_show(bad, "--image-revision", revision)
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("planned image_revision", result.out)

    def test_a_plan_that_carries_an_unrequested_image_revision_is_refused(self):
        show = self.write_show_json(CHANGES, image_revision="c" * 40, name="unrequested.json")
        result = self.run_with_show(show)
        self.assertEqual(result.rc, 4, result.out)

    def test_candidate_lines_name_the_new_approval_fields(self):
        result = self.run_with_show(self.show)
        self.assertIn("APPROVED_PRESPEND_SHA256=<sha256 of the human-written pre-spend receipt", result.stdout)
        self.assertIn("APPROVED_STAGE=<one of base-apply | runtime-apply (a push approval record names no plan", result.stdout)
        receipt = self.artifact(".receipt.json")
        with open(receipt, "rb") as handle:
            self.assertIn("APPROVED_RECEIPT_SHA256=%s" % sha256_bytes(handle.read()), result.stdout)
        self.assertIn("APPROVED_ENVIRONMENT=course", result.stdout)


class PlanStateBindingTests(PlanBase):
    """R1 (plan side): the plan is bound to the LIVE local state file and records its identity."""

    def run_execute(self, *extra, **env):
        merged = self.execute_env()
        merged.update(env)
        return self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", *extra, **merged)

    def chdir_lines(self):
        with open(self.log + ".chdir", encoding="utf-8") as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def test_the_materialized_root_is_bound_to_the_live_state_and_the_receipt_records_its_identity(self):
        result = self.run_execute()
        self.assertEqual(result.rc, 0, result.out)
        live = os.path.realpath(self.state_path())
        lines = [l for l in self.chdir_lines() if l[0] in ("init", "plan", "show")]
        self.assertTrue(lines)
        for sub, chdir, files, binding in lines:
            self.assertIn("/target/plans/", chdir, "terraform runs in the materialized copy: %s" % chdir)
            self.assertNotEqual(os.path.realpath(chdir), os.path.realpath(os.path.join(self.repo, "infra", "terraform")), sub)
            self.assertIn("zz_scholarchain_state_binding.tf", files.split(","), sub)
            self.assertEqual(binding, live, "%s must use the LIVE state file, not a fresh one" % sub)
        with open(self.artifact(".receipt.json")) as handle:
            receipt = json.load(handle)
        # Hand-derived from the fixture state: lineage, serial 7, sha256 of the file bytes.
        with open(self.state_path(), "rb") as handle:
            digest = sha256_bytes(handle.read())
        self.assertEqual(receipt["state"], {"present": True, "lineage": STATE_LINEAGE, "serial": 7, "sha256": digest})
        self.assertEqual(receipt["source_tree_sha256"], self.tree_sha())
        self.assertEqual(receipt["purpose"], "deploy-plan")
        self.assertEqual((receipt["planned_environment"], receipt["planned_project"]), ("course", "scholarchain"))
        self.assertIn("lineage", result.stdout)
        self.assertNotIn("resources", json.dumps(receipt), "no state content other than the identity is recorded")

    def test_a_missing_live_state_is_refused_before_any_aws_or_terraform_command(self):
        os.remove(self.state_path())
        result = self.run_execute()
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "materialize-source")
        self.assertIn("does not exist", result.out)
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])

    def test_a_state_file_that_is_not_a_terraform_state_is_refused(self):
        for label, text in (("not json", "not json at all"), ("no lineage", '{"serial": 3}'), ("string serial", '{"lineage": "x", "serial": "3"}')):
            with self.subTest(label):
                with open(self.state_path(), "w") as handle:
                    handle.write(text)
                result = self.run_execute()
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "materialize-source")

    def test_a_symlinked_state_file_is_refused(self):
        real = os.path.join(self.tmp, "elsewhere.tfstate")
        os.replace(self.state_path(), real)
        os.symlink(real, self.state_path())
        result = self.run_execute()
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("symlink", result.out)

    def test_expect_new_state_records_an_absent_state_and_refuses_an_existing_one(self):
        os.remove(self.state_path())
        result = self.run_execute("--expect-new-state")
        self.assertEqual(result.rc, 0, result.out)
        with open(self.artifact(".receipt.json")) as handle:
            self.assertEqual(json.load(handle)["state"], {"present": False})
        self.write_state()
        again = self.run_execute("--expect-new-state")
        self.assertEqual(again.rc, 3, again.out)
        self.assertIn("already exists", again.out)

    def test_a_state_that_changes_while_planning_is_a_gate_failure_and_writes_no_receipt(self):
        result = self.run_execute(FAKE_PLAN_BUMP_STATE=self.state_path())
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("changed while planning", result.out)
        self.assertEqual(glob.glob(os.path.join(self.repo, "target", "plans", "*", "*.receipt.json")), [])


class PlanSourceTests(PlanBase):
    """R3: the plan always runs from a git archive of the commit; ignored overrides cannot load; the planned environment is checked."""

    def run_execute(self, *extra, **env):
        merged = self.execute_env()
        merged.update(env)
        return self.plan("--env", "course", "--region", REGION, "--profile", "approved", "--execute", *extra, **merged)

    def materialized_root(self):
        found = glob.glob(os.path.join(self.repo, "target", "plans", "*", "source", self.head(), "infra", "terraform"))
        self.assertEqual(len(found), 1, found)
        return found[0]

    def test_ignored_override_files_in_the_worktree_never_reach_the_materialized_source(self):
        baseline = self.run_execute()
        self.assertEqual(baseline.rc, 0, baseline.out)
        base_files = sorted(os.listdir(self.materialized_root()))
        for name in ("override.tf", "zz_override.tf", "override.tf.json"):
            self.write("infra/terraform/" + name, 'variable "x" { default = "injected" }\n' if name.endswith(".tf") else "{}\n")
        ignored = subprocess_check(["git", "-C", self.repo, "check-ignore", "infra/terraform/override.tf", "infra/terraform/zz_override.tf"])
        self.assertIn("override.tf", ignored, "the fixture really ignores them (the clean tree is unchanged)")
        self.assertEqual(subprocess_check(["git", "-C", self.repo, "status", "--porcelain", "--untracked-files=all", "--", "infra"]).count("override"), 0)
        shutil_rmtree(os.path.join(self.repo, "target", "plans"))
        open(self.log + ".chdir", "w").close()
        result = self.run_execute()
        self.assertEqual(result.rc, 0, result.out)
        root = self.materialized_root()
        self.assertEqual(sorted(os.listdir(root)), base_files, "the materialized source holds exactly the committed files plus the state binding")
        for name in ("override.tf", "zz_override.tf", "override.tf.json"):
            self.assertFalse(os.path.exists(os.path.join(root, name)), name)
        with open(self.log + ".chdir") as handle:
            for line in handle:
                sub, chdir, files, _binding = line.rstrip("\n").split("\t")
                self.assertNotIn("override.tf", files.split(","), sub)
                self.assertNotEqual(os.path.realpath(chdir), os.path.realpath(os.path.join(self.repo, "infra", "terraform")), "never the work tree: " + sub)
        with open(self.artifact(".receipt.json")) as handle:
            self.assertEqual(json.load(handle)["source_tree_sha256"], self.tree_sha(), "the recorded hash is the hash of the committed source")

    def test_a_modified_tracked_file_in_the_worktree_is_not_planned(self):
        self.write("infra/terraform/versions.tf", "# edited in the work tree only\n")
        result = self.run_execute()
        self.assertEqual(result.rc, 0, result.out)
        with open(os.path.join(self.materialized_root(), "versions.tf")) as handle:
            self.assertEqual(handle.read(), "# root\n", "the committed bytes, not the edited work tree file")
        with open(self.artifact(".receipt.json")) as handle:
            receipt = json.load(handle)
        self.assertFalse(receipt["clean"])
        self.assertEqual(receipt["source_tree_sha256"], self.tree_sha())

    def test_the_materialized_source_is_read_only(self):
        result = self.run_execute()
        self.assertEqual(result.rc, 0, result.out)
        root = self.materialized_root()
        self.assertEqual(os.stat(os.path.join(root, "versions.tf")).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH), 0)

    def run_with_show(self, show):
        return self.run_execute(FAKE_SHOW_JSON=show)

    def test_a_planned_environment_that_differs_from_the_requested_one_is_a_gate_failure(self):
        """The private tfvars file can override environment: the plan's own variable is what counts."""
        show = self.write_show_json(CHANGES, environment="staging", name="env.json")
        result = self.run_with_show(show)
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("planned environment staging != expected course", result.out)
        self.assertEqual(glob.glob(os.path.join(self.repo, "target", "plans", "*", "*.receipt.json")), [])

    def test_a_planned_project_that_differs_is_a_gate_failure(self):
        show = self.write_show_json(CHANGES, project="otherproj", name="proj.json")
        result = self.run_with_show(show)
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("planned project otherproj != expected scholarchain", result.out)

    def test_a_plan_without_an_environment_variable_value_is_a_gate_failure(self):
        with open(self.show) as handle:
            document = json.load(handle)
        del document["variables"]["environment"]
        path = os.path.join(self.tmp, "no-env.json")
        with open(path, "w") as handle:
            json.dump(document, handle)
        result = self.run_with_show(path)
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("PLANNED-ENVIRONMENT-MISSING", result.out)


def shutil_rmtree(path):
    import shutil

    subprocess.run(["chmod", "-R", "u+w", path], capture_output=True)
    shutil.rmtree(path)


if __name__ == "__main__":
    unittest.main()

"""Cheap regression probes for the 13A scripts and strict-mode checks for every Phase 13 script (test-engineer, 13B).

Plan section 9 rows covered here: Syntax (bash -n, shellcheck), Dry run (plan.sh and cleanup.sh print their commands and
run nothing beyond the Terraform version probe), Deploy refusals (missing approval record, dirty tree), Cleanup (refuses
without the documented confirmation inputs), Safety (every script prints STEP markers and exactly one RESULT line, no
canary secret in output). Expectations come from scripts/README.md and each script's --help, not from the scripts' code.
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import sc_support as S

SCRIPTS_13B = ["smoke-test.sh", "run-bounded-pipeline.sh", "run-experiment.sh", "archive-evidence.sh"]
SCRIPTS_13A = ["check.sh", "package.sh", "plan.sh", "deploy.sh", "rollback.sh", "cleanup.sh"]
ALL = SCRIPTS_13A + SCRIPTS_13B


class Syntax(unittest.TestCase):
    def test_every_phase13_script_is_strict_mode_bash_with_a_shebang(self):
        for name in ALL:
            with self.subTest(script=name):
                path = S.SRC_SCRIPTS / name
                self.assertTrue(path.is_file(), name)
                text = path.read_text()
                self.assertEqual(text.splitlines()[0], "#!/usr/bin/env bash")
                self.assertRegex(text, r"(?m)^set -euo pipefail$")
                self.assertTrue(path.stat().st_mode & 0o100, "%s is not executable" % name)

    def test_bash_n_is_clean_for_every_phase13_script_and_library(self):
        paths = [S.SRC_SCRIPTS / n for n in ALL] + [S.SRC_SCRIPTS / "lib" / "common.sh", S.SRC_SCRIPTS / "smoke-local.sh"]
        for path in paths:
            with self.subTest(script=path.name):
                done = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)

    def test_shellcheck_is_clean_for_the_13b_scripts(self):
        exe = shutil.which("shellcheck")
        self.assertIsNotNone(exe, "shellcheck is a documented prerequisite (scripts/README.md); install it to run this check")
        paths = [S.SRC_SCRIPTS / n for n in SCRIPTS_13B] + [S.SRC_SCRIPTS / "smoke-local.sh"]
        done = subprocess.run([exe, "-x"] + [str(p) for p in paths], capture_output=True, text=True, cwd=str(S.SRC_SCRIPTS))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_no_script_hardcodes_a_bucket_account_or_endpoint(self):
        for name in SCRIPTS_13B:
            with self.subTest(script=name):
                text = (S.SRC_SCRIPTS / name).read_text()
                self.assertIsNone(re.search(r"(?<![0-9])[0-9]{12}(?![0-9])", text), "a 12-digit (account-like) number is hardcoded")
                self.assertIsNone(re.search(r"s3://[a-z0-9][a-z0-9.-]{2,}/", re.sub(r"s3://(bucket|b)/", "", text)), "a bucket URI is hardcoded")


class RequiredSuite(unittest.TestCase):
    def test_check_sh_pins_this_directory_as_a_required_discover_suite(self):
        text = (S.SRC_SCRIPTS / "check.sh").read_text()
        self.assertIn("discover:tests/scripts", text, "scripts/check.sh must pin tests/scripts as a required suite (README 13B)")

    def test_this_suite_is_discoverable_from_the_repository_root_without_helpers_from_scripts_tests(self):
        for path in Path(__file__).resolve().parent.glob("*.py"):
            text = path.read_text()
            self.assertNotRegex(text, r"(?m)^\s*(from|import)\s+(fake_tool|pipeline_helpers|scripts\.tests)", "%s reuses scripts/tests helpers" % path.name)


class UsageErrors(unittest.TestCase):
    """scripts/README.md: an unknown flag or a flag without its value prints STEP: start, STEP: usage and one
    RESULT: REFUSED step=usage line and exits 2, in all eleven scripts that parse options; --help still exits 0."""

    ELEVEN = ALL + ["smoke-local.sh"]
    VALUE_FLAGS = {
        "plan.sh": "--region", "deploy.sh": "--region", "rollback.sh": "--region", "cleanup.sh": "--region",
        "check.sh": "--only", "smoke-test.sh": "--url", "run-bounded-pipeline.sh": "--region", "run-experiment.sh": "--manifest",
        "archive-evidence.sh": "--phase",
    }

    def assert_usage(self, r, label):
        self.assertEqual(r.rc, 2, "%s\n%s" % (label, r.describe()))
        self.assertEqual(r.steps(), ["start", "usage"], "%s\n%s" % (label, r.describe()))
        self.assertEqual(len(r.results()), 1, "%s\n%s" % (label, r.describe()))
        self.assertTrue(r.result.startswith("RESULT: REFUSED step=usage"), "%s: %s" % (label, r.result))
        self.assertTrue(r.lines()[-1].startswith("RESULT:"), label)
        self.assertEqual(r.calls, [], label)

    def test_unknown_flag_is_a_usage_refusal_with_markers_in_every_script(self):
        self.assertEqual(len(self.ELEVEN), 11)
        fx = S.Fixture(self)
        for name in self.ELEVEN:
            with self.subTest(script=name):
                self.assert_usage(fx.run(name, ["--no-such-flag"]), name)

    def test_flag_without_its_value_is_a_usage_refusal_with_markers(self):
        fx = S.Fixture(self)
        for name, flag in self.VALUE_FLAGS.items():
            with self.subTest(script=name, flag=flag):
                self.assert_usage(fx.run(name, [flag]), "%s %s" % (name, flag))

    def test_help_still_exits_zero_for_every_script(self):
        fx = S.Fixture(self)
        for name in self.ELEVEN:
            with self.subTest(script=name):
                r = fx.run(name, ["--help"])
                self.assertEqual(r.rc, 0, r.describe())
                self.assertEqual(r.results(), [], "--help must not print a RESULT line")


class Help(unittest.TestCase):
    def test_help_exits_zero_and_documents_exit_codes_and_evidence(self):
        for name in SCRIPTS_13B + ["deploy.sh", "plan.sh", "rollback.sh", "cleanup.sh"]:
            with self.subTest(script=name):
                fx = S.Fixture(self)
                r = fx.run(name, ["--help"])
                self.assertEqual(r.rc, 0, r.describe())
                self.assertIn("Exit codes", r.out)
                self.assertIn("Usage", r.out)
                self.assertEqual(r.calls, [])

    def test_pipeline_and_experiment_help_state_the_approval_point_and_dry_run_default(self):
        fx = S.Fixture(self)
        for name in ("run-bounded-pipeline.sh", "run-experiment.sh"):
            r = fx.run(name, ["--help"])
            self.assertIn("approval point", r.out.lower().replace("approval points", "approval point"))
            self.assertIn("--execute", r.out)
            self.assertRegex(r.out, r"(?i)dry run")


class CloudScriptsDryRun(unittest.TestCase):
    """plan.sh, cleanup.sh print every command and run nothing beyond the Terraform version probe."""

    def check_only_version_probe(self, r):
        self.assertEqual(r.tool_calls("aws"), [])
        self.assertEqual(r.tool_calls("docker"), [])
        self.assertEqual([c["argv"] for c in r.tool_calls("terraform")], [["version", "-json"]] * len(r.tool_calls("terraform")))
        self.assertLessEqual(len(r.tool_calls("terraform")), 2)

    def test_plan_dry_run_prints_commands_and_runs_only_the_version_probe(self):
        fx = S.Fixture(self, infra=True)
        r = fx.run("plan.sh", ["--env", "course", "--region", "us-east-2"], secrets=True)
        self.assertEqual((r.rc, r.status), (0, "DRY-RUN"), r.describe())
        self.assertEqual(len(r.results()), 1)
        self.check_only_version_probe(r)
        cmds = r.grep(r"^DRY-RUN CMD: ")
        self.assertTrue(cmds)
        for c in cmds:
            self.assertRegex(c, r"^DRY-RUN CMD: timeout=\d+s ")
        self.assertTrue(any("terraform" in c and "plan" in c for c in cmds))
        self.assertFalse([c for c in cmds if re.search(r"terraform\S*\s+(apply|destroy)", c)], "plan.sh must never print an apply")
        for canary in S.CANARIES:
            self.assertNotIn(canary, r.text)

    def test_cleanup_dry_run_lists_targets_and_runs_only_the_version_probe(self):
        fx = S.Fixture(self, infra=True)
        r = fx.run("cleanup.sh", ["--env", "course", "--region", "us-east-2"], secrets=True)
        self.assertEqual((r.rc, r.status), (0, "DRY-RUN"), r.describe())
        self.check_only_version_probe(r)
        self.assertTrue(r.grep(r"^DRY-RUN CMD: "))
        for step in ("before-inventory", "protection-check", "destroy-commands"):
            self.assertIn(step, r.steps())
        self.assertLess(r.steps().index("before-inventory"), r.steps().index("destroy-commands"), "the inventory is listed before any deletion")
        for canary in S.CANARIES:
            self.assertNotIn(canary, r.text)

    def test_execute_without_the_approved_profile_is_refused_before_any_command(self):
        cases = (("plan.sh", ["--env", "course", "--region", "us-east-2", "--execute"]),
                 ("cleanup.sh", ["--env", "course", "--region", "us-east-2", "--execute"]),
                 ("deploy.sh", ["--stage", "base-apply", "--plan", "/nonexistent", "--region", "us-east-2", "--execute"]))
        for script, args in cases:
            with self.subTest(script=script):
                fx = S.Fixture(self, infra=True)
                r = fx.run(script, args)
                self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
                self.assertEqual(r.calls, [])

    def test_cleanup_execute_needs_the_private_variable_file_and_confirm_needs_a_plan(self):
        fx = S.Fixture(self, infra=True)
        r = fx.run("cleanup.sh", ["--env", "course", "--region", "us-east-2", "--execute", "--profile", "p"])
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertEqual(r.calls, [])
        r = fx.run("cleanup.sh", ["--env", "course", "--region", "us-east-2", "--execute", "--profile", "p", "--confirm", "abc"])
        self.assertEqual((r.rc, r.status), (2, "REFUSED"), r.describe())
        self.assertEqual(r.calls, [])


class DeployAndRollbackRefusals(unittest.TestCase):
    def test_missing_approval_record_is_refused_with_no_cloud_call(self):
        fx = S.Fixture(self, infra=True)
        r = fx.run("deploy.sh", ["--stage", "base-apply", "--plan", "/nonexistent", "--region", "us-east-2",
                                 "--approval", str(fx.aux / "missing.md")])
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertEqual(S.last_step(r), "approval-record")
        self.assertEqual(len(r.results()), 1)
        self.assertEqual(r.tool_calls("aws"), [])
        self.assertEqual(r.tool_calls("docker"), [])
        self.assertTrue(all(c["argv"] == ["version", "-json"] for c in r.tool_calls("terraform")))

    def test_dirty_tree_is_refused_before_the_approval_record_is_read(self):
        fx = S.Fixture(self, infra=True)
        (fx.repo / "stray.txt").write_text("x")
        r = fx.run("deploy.sh", ["--stage", "base-apply", "--plan", "/nonexistent", "--region", "us-east-2"])
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertEqual(S.last_step(r), "clean-tree")
        self.assertEqual(r.tool_calls("aws") + r.tool_calls("docker"), [])

    def test_stage_is_required_and_region_has_no_default(self):
        fx = S.Fixture(self, infra=True)
        r = fx.run("deploy.sh", ["--stage", "base-apply"])
        self.assertEqual(r.rc, 2, r.describe())
        self.assertEqual(r.calls, [])

    def test_rollback_with_a_missing_previous_manifest_is_refused(self):
        fx = S.Fixture(self, infra=True)
        r = fx.run("rollback.sh", ["--env", "course", "--region", "us-east-2", "--previous-manifest", "/nonexistent"])
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertEqual(S.last_step(r), "previous-manifest")
        self.assertEqual(r.tool_calls("aws") + r.tool_calls("docker"), [])

    def test_terraform_that_is_not_the_pinned_version_is_refused(self):
        fx = S.Fixture(self, infra=True)
        fx.update_scenario(terraform_version="1.9.0")
        r = fx.run("plan.sh", ["--env", "course", "--region", "us-east-2"])
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertIn("1.9.0", r.result)
        self.assertEqual(r.tool_calls("aws"), [])


if __name__ == "__main__":
    unittest.main()

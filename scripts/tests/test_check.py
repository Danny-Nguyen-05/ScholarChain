"""check.sh: a deliberately broken gate fails; fake sbt/terraform failures propagate; clean fast gates pass.

F9: the three required script-test suites are pinned in check.sh; an omitted suite fails the gate, a suite
that executes zero tests fails the gate, and the pinned list cannot be replaced from the environment.
"""
import os
import shutil
import subprocess
import unittest

from helpers import REAL_REPO, SCRIPTS_DIR, Fixture


REQUIRED_SUITE_DIRS = ("scripts/tests", "scripts/phase12d-spike/tests", "scripts/billing/tests")
# Subphase 13B: the test-engineer's independent script tests are a fourth REQUIRED discover suite. It is enforced in a
# default full run; a partial run only warns while it is not populated yet (SUITE-PENDING).
TEST_ENGINEER_SUITE = "tests/scripts"
REQUIRED_TF_FILES = {
    "scripts/tests/test_terraform_state_binding.py": "RealStateBindingTests",
    "scripts/tests/test_terraform_r1.py": "RouteOwnershipTest",
}
STATE_BINDING_CLASS = "test_terraform_state_binding.RealStateBindingTests"
R1_CLASS = "test_terraform_r1.RouteOwnershipTest"


def required_class_module(class_name, body):
    """A module defining the pinned required class with the given body (its tests are what the gate counts)."""
    return "import unittest\n\n\nclass %s(unittest.TestCase):\n%s\n\nif __name__ == '__main__':\n    unittest.main()\n" % (class_name, body)


PASSING_BODY = "    def test_a(self):\n        self.assertTrue(True)\n"
CLASS_SKIP_BODY = "    @classmethod\n    def setUpClass(cls):\n        raise unittest.SkipTest('providers missing')\n\n    def test_a(self):\n        pass\n\n    def test_b(self):\n        pass\n"
METHOD_SKIP_BODY = "    def setUp(self):\n        self.skipTest('init failed')\n\n    def test_a(self):\n        pass\n\n    def test_b(self):\n        pass\n"
PASSING_TEST = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertTrue(True)\n\n\nif __name__ == '__main__':\n    unittest.main()\n"
ALL_SKIPPED_TEST = "import unittest\n\n\nclass T(unittest.TestCase):\n    @unittest.skip('nothing runs')\n    def test_a(self):\n        pass\n\n\nif __name__ == '__main__':\n    unittest.main()\n"
NO_TESTS = "import unittest\n\nif __name__ == '__main__':\n    unittest.main()\n"


class CheckBase(Fixture):
    def build_repo(self):
        super().build_repo()
        for rel in ("AGENTS.md", "CLAUDE.md", "docs/agents.md", "docs/agent-runs/README.md"):
            self.write(rel, "# placeholder\n")
        self.write(".claude/settings.json", "{}\n")
        self.write(".claude/ownership-audit.json", "{}\n")
        self.write(".claude/agents/example.md", "# agent\n")
        self.write(".mcp.json", "{}\n")
        self.write(".claude/hooks/ok.sh", '#!/usr/bin/env bash\nset -euo pipefail\necho "ok"\n', 0o755)
        for suite in REQUIRED_SUITE_DIRS:
            self.write("%s/test_one.py" % suite, PASSING_TEST)
        self.write("%s/test_one.py" % TEST_ENGINEER_SUITE, PASSING_TEST)
        for path, class_name in REQUIRED_TF_FILES.items():
            self.write(path, required_class_module(class_name, PASSING_BODY))
        self.write("scripts/ok.sh", '#!/usr/bin/env bash\nset -euo pipefail\nname="x"\necho "${name}"\n', 0o755)
        self.write("scripts/ok.py", "print('ok')\n")
        self.commit("constitution fixture")

    def check(self, *args, **env):
        return self.run_script("check.sh", *args, **env)

    def gate_line(self, result, gate):
        lines = [l for l in result.stdout.splitlines() if l.startswith("GATE: %s " % gate)]
        self.assertEqual(len(lines), 1, result.out)
        return lines[0]

    @staticmethod
    def must_have_shellcheck():
        if not shutil.which("shellcheck"):
            raise unittest.SkipTest("shellcheck not installed")


class CheckFastGatesTests(CheckBase):
    def test_clean_fast_gates_pass_and_run_ends_partial_listing_skipped_gates(self):
        self.must_have_shellcheck()
        result = self.check("--only", "constitution,hooks,shell,python")
        self.assertEqual(result.rc, 5, result.out)
        for gate in ("constitution", "hooks", "shell", "python"):
            self.assertEqual(self.gate_line(result, gate).split()[2], "PASS", result.out)
            self.assertIn("STEP: gate-%s" % gate, result.stdout)
        self.assertIn("RESULT: PARTIAL passed=4 skipped: terraform script-tests sbt", result.stdout)
        self.assertIn("GATE SUMMARY", result.stdout)

    def test_broken_json_fails_the_constitution_gate(self):
        self.write("config/broken.json", '{"a": ')
        result = self.check("--only", "constitution")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.gate_line(result, "constitution").split()[2], "FAIL")
        self.assertIn("RESULT: FAIL", result.stdout)
        self.assertIn("config/broken.json", result.out)

    def test_documented_fixture_prefix_is_excluded_from_json_parsing(self):
        self.write("scripts/tests/fixtures/deliberately-broken.json", "{")
        result = self.check("--only", "constitution")
        self.assertEqual(result.rc, 5, result.out)

    def test_missing_constitution_file_fails(self):
        os.remove(os.path.join(self.repo, ".mcp.json"))
        subprocess.run(["git", "-C", self.repo, "rm", "-q", "--cached", ".mcp.json"], check=True)
        result = self.check("--only", "constitution")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn(".mcp.json", result.out)

    def test_shellcheck_finding_fails_the_shell_gate(self):
        self.must_have_shellcheck()
        self.write("scripts/finding.sh", '#!/usr/bin/env bash\nset -euo pipefail\nfor f in $(ls); do echo $f; done\n', 0o755)
        result = self.check("--only", "shell")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.gate_line(result, "shell").split()[2], "FAIL")
        self.assertIn("SC2", result.out)

    def test_bash_syntax_error_fails_the_shell_gate(self):
        self.write("scripts/syntax.sh", "#!/usr/bin/env bash\nif then fi\n", 0o755)
        result = self.check("--only", "shell")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("bash -n failed: scripts/syntax.sh", result.out)

    def test_untracked_new_script_is_also_checked(self):
        self.write("scripts/new-untracked.sh", "#!/usr/bin/env bash\nif then fi\n", 0o755)
        self.assertFalse(subprocess.run(["git", "-C", self.repo, "ls-files", "--error-unmatch", "scripts/new-untracked.sh"], capture_output=True).returncode == 0)
        self.assertEqual(self.check("--only", "shell").rc, 4)

    def test_broken_hook_fails_the_hooks_gate(self):
        self.write(".claude/hooks/bad.sh", "#!/usr/bin/env bash\nif then fi\n", 0o755)
        result = self.check("--only", "hooks")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.gate_line(result, "hooks").split()[2], "FAIL")

    def test_python_syntax_error_fails_the_python_gate(self):
        self.write("scripts/bad.py", "def broken(:\n")
        result = self.check("--only", "python")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.gate_line(result, "python").split()[2], "FAIL")

    def test_python_gate_does_not_leave_bytecode_in_the_repo(self):
        self.check("--only", "python")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "scripts", "__pycache__")))

    def test_real_repository_fast_gates_pass(self):
        """The real checkout: constitution, hooks, shell and python gates all pass."""
        self.must_have_shellcheck()
        env = self.env()
        env["SCHOLARCHAIN_REPO_ROOT"] = REAL_REPO
        completed = subprocess.run(
            ["bash", os.path.join(SCRIPTS_DIR, "check.sh"), "--only", "constitution,hooks,shell,python"],
            env=env, capture_output=True, text=True, timeout=300, cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 5, completed.stdout + completed.stderr)
        self.assertIn("RESULT: PARTIAL", completed.stdout)


class CheckScriptTestGateTests(CheckBase):
    def gate(self, **env):
        return self.check("--only", "script-tests", **env)

    def test_all_three_pinned_suites_run_and_each_reports_executed_tests(self):
        result = self.gate()
        self.assertEqual(result.rc, 5, result.out)  # PARTIAL: the other gates were skipped
        self.assertEqual(self.gate_line(result, "script-tests").split()[2], "PASS", result.out)
        self.assertIn("suite scripts/tests: Ran 3 tests", result.out)
        self.assertIn("(3 executed, 0 skipped tests, 0 skipped classes)", result.out)
        self.assertIn("suite scripts/phase12d-spike/tests: Ran 1 test", result.out)
        self.assertIn("suite file scripts/billing/tests/test_one.py: 1 executed OK", result.out)

    def test_a_failing_suite_fails_the_gate(self):
        self.write("scripts/phase12d-spike/tests/test_bad.py", "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.fail('boom')\n")
        result = self.gate()
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("suite failed: scripts/phase12d-spike/tests", result.out)

    def test_an_omitted_required_suite_fails_the_gate(self):
        for suite in REQUIRED_SUITE_DIRS:
            with self.subTest(suite):
                backup = os.path.join(self.tmp, "backup-" + suite.replace("/", "_"))
                os.rename(os.path.join(self.repo, suite), backup)
                result = self.gate()
                self.assertEqual(result.rc, 4, result.out)
                self.assertIn("required test suite directory missing: %s" % suite, result.out)
                self.assertEqual(self.gate_line(result, "script-tests").split()[2], "FAIL")
                os.rename(backup, os.path.join(self.repo, suite))

    def test_the_environment_cannot_replace_the_required_suite_list(self):
        """Neither SCRIPT_TEST_SUITES nor a same-named config key narrows the pinned list."""
        os.rename(os.path.join(self.repo, "scripts/billing/tests"), os.path.join(self.tmp, "billing-away"))
        for value in (" ", "discover:scripts/tests", "files:scripts/tests"):
            with self.subTest(value):
                result = self.gate(SCRIPT_TEST_SUITES=value)
                self.assertEqual(result.rc, 4, result.out)
                self.assertIn("required test suite directory missing: scripts/billing/tests", result.out)

    def test_an_all_skipped_discover_suite_executes_zero_tests_and_fails(self):
        self.write("scripts/tests/test_one.py", ALL_SKIPPED_TEST)
        for path, class_name in REQUIRED_TF_FILES.items():
            self.write(path, required_class_module(class_name, "    @unittest.skip('nothing runs')\n    def test_a(self):\n        pass\n"))
        result = self.gate()
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("suite scripts/tests executed zero tests: an empty suite is a failure", result.out)

    def test_a_discover_suite_with_no_tests_fails(self):
        self.write("scripts/phase12d-spike/tests/test_one.py", NO_TESTS)
        result = self.gate()
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.gate_line(result, "script-tests").split()[2], "FAIL")

    def test_a_files_suite_with_a_file_that_runs_zero_tests_fails(self):
        self.write("scripts/billing/tests/test_one.py", ALL_SKIPPED_TEST)
        result = self.gate()
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("scripts/billing/tests/test_one.py executed zero tests: an empty suite is a failure", result.out)

    def test_a_files_suite_with_a_file_that_collects_no_tests_fails(self):
        self.write("scripts/billing/tests/test_one.py", NO_TESTS)
        result = self.gate()
        self.assertEqual(result.rc, 4, result.out)

    def test_an_empty_files_suite_directory_fails(self):
        os.remove(os.path.join(self.repo, "scripts/billing/tests/test_one.py"))
        self.write("scripts/billing/tests/terraform_state_binding.py", "# excluded helper, not a test file\n")
        result = self.gate()
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("suite scripts/billing/tests holds no test_*.py file: an empty suite is a failure", result.out)

    def test_each_billing_test_file_runs_in_its_own_process(self):
        self.write("scripts/billing/tests/test_two.py", PASSING_TEST)
        result = self.gate()
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("suite file scripts/billing/tests/test_one.py: 1 executed OK", result.out)
        self.assertIn("suite file scripts/billing/tests/test_two.py: 1 executed OK", result.out)

    def test_the_test_only_override_is_announced_and_can_never_produce_a_full_pass(self):
        self.write("custom_suite/test_x.py", PASSING_TEST)
        result = self.check("--skip", "sbt,terraform", SC_TEST_ONLY_SCRIPT_TEST_SUITES="discover:custom_suite")
        self.assertIn("SUITES-OVERRIDE: test-only suite list in use (discover:custom_suite)", result.stdout)
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("RESULT: PARTIAL", result.stdout)
        self.assertIn("custom-script-test-suites", result.stdout)

    def test_the_test_only_override_cannot_make_a_default_run_pass(self):
        self.must_have_shellcheck()
        self.write("custom_suite/test_x.py", PASSING_TEST)
        result = self.check(SC_TEST_ONLY_SCRIPT_TEST_SUITES="discover:custom_suite")
        self.assertEqual(result.rc, 5, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PARTIAL"), result.result_line())


class CheckTestEngineerSuiteTests(CheckBase):
    """13B: tests/scripts is a pinned REQUIRED suite (discover). The directory is created by the test-engineer, so these
    tests simulate it inside the fixture repository; nothing under the real tests/** is touched."""

    def remove_suite(self):
        shutil.rmtree(os.path.join(self.repo, TEST_ENGINEER_SUITE))

    def test_the_suite_is_pinned_in_check_sh_as_a_discover_suite(self):
        with open(os.path.join(SCRIPTS_DIR, "check.sh"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("discover:tests/scripts", text.split("REQUIRED_SUITES=", 1)[1].splitlines()[0])

    def test_a_populated_suite_is_run_and_reports_executed_tests(self):
        result = self.check("--only", "script-tests")
        self.assertEqual(result.rc, 5, result.out)  # PARTIAL by --only; the gate itself passes
        self.assertEqual(self.gate_line(result, "script-tests").split()[2], "PASS", result.out)
        self.assertIn("suite tests/scripts: Ran 1 test", result.out)
        self.assertNotIn("SUITE-PENDING", result.out)

    def test_a_default_full_run_fails_when_the_suite_directory_is_missing(self):
        self.must_have_shellcheck()
        self.remove_suite()
        result = self.check()
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("required test suite directory missing: tests/scripts", result.out)
        self.assertEqual(self.gate_line(result, "script-tests").split()[2], "FAIL")
        self.assertTrue(result.result_line().startswith("RESULT: FAIL"), result.result_line())

    def test_a_default_full_run_fails_when_the_suite_executes_zero_tests(self):
        self.must_have_shellcheck()
        self.write("%s/test_one.py" % TEST_ENGINEER_SUITE, NO_TESTS)
        result = self.check()
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("suite tests/scripts executed zero tests: an empty suite is a failure", result.out)

    def test_a_partial_run_only_warns_while_the_suite_is_missing_and_never_passes(self):
        self.remove_suite()
        result = self.check("--only", "script-tests")
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("SUITE-PENDING: required suite tests/scripts does not exist yet", result.out)
        self.assertEqual(self.gate_line(result, "script-tests").split()[2], "PASS", result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PARTIAL"), result.result_line())

    def test_a_partial_run_only_warns_while_the_suite_executes_no_test(self):
        self.write("%s/test_one.py" % TEST_ENGINEER_SUITE, NO_TESTS)
        result = self.check("--only", "script-tests")
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("SUITE-PENDING: suite tests/scripts executed no test yet", result.out)

    def test_a_populated_failing_suite_fails_even_a_partial_run(self):
        self.write("%s/test_bad.py" % TEST_ENGINEER_SUITE, "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.fail('boom')\n")
        result = self.check("--only", "script-tests")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("suite failed: tests/scripts", result.out)

    def test_the_pending_allowance_does_not_extend_to_the_other_required_suites(self):
        self.remove_suite()
        shutil.rmtree(os.path.join(self.repo, "scripts/billing/tests"))
        result = self.check("--only", "script-tests")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("required test suite directory missing: scripts/billing/tests", result.out)

    def test_the_environment_cannot_make_a_default_run_treat_the_suite_as_pending(self):
        self.must_have_shellcheck()
        self.remove_suite()
        for name in ("PENDING_UNTIL_POPULATED", "FULL_RUN", "TEST_ENGINEER_SUITE"):
            with self.subTest(name):
                result = self.check(**{name: "x"})
                self.assertEqual(result.rc, 4, result.out)


class CheckRequiredRealTerraformTests(CheckBase):
    """N4: the real-Terraform proofs must EXECUTE in a default full run (a skip is not a pass), the terraform gate runs
    before script-tests so a clean checkout has the providers, and the executed count is Ran minus method-level skips."""

    def full(self, **env):
        self.must_have_shellcheck()
        return self.check(**env)

    def test_the_terraform_gate_runs_before_script_tests_in_the_default_order(self):
        self.assertEqual(self.check("--list-gates").stdout.split(), ["constitution", "hooks", "shell", "python", "terraform", "script-tests", "sbt"])
        result = self.full()
        self.assertEqual(result.rc, 0, result.out)
        steps = result.steps()
        self.assertLess(steps.index("gate-terraform"), steps.index("gate-script-tests"))

    def test_a_default_full_run_fails_when_a_required_class_is_skipped_at_class_level(self):
        self.write("scripts/tests/test_terraform_state_binding.py", required_class_module("RealStateBindingTests", CLASS_SKIP_BODY))
        result = self.full()
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.gate_line(result, "script-tests").split()[2], "FAIL")
        self.assertIn("SUITE-REQUIRED %s executed=0 skipped=1 status=SKIPPED" % STATE_BINDING_CLASS, result.out)
        self.assertIn("a required real-Terraform test class was skipped or missing in a default full run", result.out)
        self.assertIn("RESULT: FAIL failed: script-tests", result.stdout)

    def test_a_default_full_run_fails_when_a_required_class_skips_its_tests_one_by_one(self):
        self.write("scripts/tests/test_terraform_r1.py", required_class_module("RouteOwnershipTest", METHOD_SKIP_BODY))
        result = self.full()
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("SUITE-REQUIRED %s executed=0 skipped=2 status=SKIPPED" % R1_CLASS, result.out)

    def test_a_default_full_run_fails_when_a_required_class_is_missing(self):
        os.rename(os.path.join(self.repo, "scripts/tests/test_terraform_state_binding.py"), os.path.join(self.repo, "scripts/tests/test_renamed_away.py"))
        result = self.full()
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("SUITE-REQUIRED %s executed=0 skipped=0 status=MISSING" % STATE_BINDING_CLASS, result.out)

    def test_the_environment_cannot_weaken_the_pinned_required_classes_or_the_full_run_flag(self):
        self.write("scripts/tests/test_terraform_state_binding.py", required_class_module("RealStateBindingTests", CLASS_SKIP_BODY))
        result = self.full(REQUIRED_REAL_TERRAFORM_CLASSES="nothing.Nothing", FULL_RUN="0")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn(STATE_BINDING_CLASS, result.out)

    def test_a_partial_run_only_warns_and_still_ends_partial(self):
        self.write("scripts/tests/test_terraform_state_binding.py", required_class_module("RealStateBindingTests", CLASS_SKIP_BODY))
        result = self.check("--only", "script-tests")
        self.assertEqual(result.rc, 5, result.out)
        self.assertEqual(self.gate_line(result, "script-tests").split()[2], "PASS")
        self.assertIn("required real-Terraform class did not run (not enforced in a partial run)", result.out)
        self.assertIn("SUITE-SKIPPED-CLASS setUpClass (%s)" % STATE_BINDING_CLASS, result.out)
        self.assertIn("RESULT: PARTIAL", result.stdout)

    def test_the_executed_count_is_ran_minus_method_skips_and_class_skips_are_listed_separately(self):
        """Ran counts collected tests: a class-level skip adds one skip and NO test to Ran, a method skip adds one of each."""
        self.write(
            "scripts/tests/test_counts.py",
            "import unittest\n\n\nclass SkippedClass(unittest.TestCase):\n"
            "    @classmethod\n    def setUpClass(cls):\n        raise unittest.SkipTest('class level')\n\n"
            "    def test_p(self):\n        pass\n\n    def test_q(self):\n        pass\n\n\n"
            "class Mixed(unittest.TestCase):\n"
            "    def test_1(self):\n        pass\n\n    def test_2(self):\n        pass\n\n    def test_3(self):\n        pass\n\n"
            "    @unittest.skip('method level')\n    def test_4(self):\n        pass\n",
        )
        result = self.check("--only", "script-tests")
        self.assertEqual(result.rc, 5, result.out)
        # 2 required placeholders + test_one (1) + Mixed (4) = 7 collected; one method skip: 6 executed.
        self.assertIn("suite scripts/tests: Ran 7 tests", result.out)
        self.assertIn("(6 executed, 1 skipped tests, 1 skipped classes) OK", result.out)
        self.assertIn("SUITE-SKIPPED-CLASS setUpClass (test_counts.SkippedClass) :: class level", result.out)
        self.assertNotIn("(5 executed", result.out, "Ran minus the reported skipped=2 would undercount")


class SuiteRunTests(CheckBase):
    """scripts/lib/suite_run.py itself, on throwaway suites."""

    def suite(self, **modules):
        directory = os.path.join(self.tmp, "suite")
        os.makedirs(directory, exist_ok=True)
        for name, body in modules.items():
            with open(os.path.join(directory, "test_%s.py" % name), "w") as handle:
                handle.write(body)
        return directory

    def run_suite(self, directory, *extra):
        return subprocess.run(
            ["python3", "-I", os.path.join(SCRIPTS_DIR, "lib", "suite_run.py"), "--start-dir", directory, *extra],
            capture_output=True, text=True, timeout=120,
        )

    def test_summary_counts_and_exit_codes(self):
        directory = self.suite(ok=PASSING_TEST, skipped=required_class_module("Gate", CLASS_SKIP_BODY))
        done = self.run_suite(directory)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("SUITE-SUMMARY ran=1 executed=1 skipped_tests=0 skipped_classes=1 failures=0 errors=0", done.stdout)
        self.assertIn("SUITE-SKIPPED-CLASS setUpClass (test_skipped.Gate) :: providers missing", done.stdout)
        self.assertIn("Ran 1 test", done.stderr, "unittest's own report is unchanged")

    def test_required_classes_report_status_and_only_fail_when_enforced(self):
        directory = self.suite(ok=PASSING_TEST, skipped=required_class_module("Gate", CLASS_SKIP_BODY))
        soft = self.run_suite(directory, "--require-class", "test_skipped.Gate,test_ok.T,test_absent.Nope")
        self.assertEqual(soft.returncode, 0, soft.stdout)
        self.assertIn("SUITE-REQUIRED test_skipped.Gate executed=0 skipped=1 status=SKIPPED", soft.stdout)
        self.assertIn("SUITE-REQUIRED test_ok.T executed=1 skipped=0 status=ok", soft.stdout)
        self.assertIn("SUITE-REQUIRED test_absent.Nope executed=0 skipped=0 status=MISSING", soft.stdout)
        self.assertNotIn("SUITE-REQUIRED-FAILED", soft.stdout)
        hard = self.run_suite(directory, "--require-class", "test_skipped.Gate", "--enforce-required")
        self.assertEqual(hard.returncode, 3, hard.stdout)
        self.assertIn("SUITE-REQUIRED-FAILED", hard.stdout)

    def test_a_failing_test_is_exit_1_even_when_the_required_classes_ran(self):
        directory = self.suite(bad="import unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.fail('boom')\n")
        done = self.run_suite(directory, "--require-class", "test_bad.T", "--enforce-required")
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("failures=1", done.stdout)

    def test_a_module_that_cannot_be_imported_is_an_error(self):
        directory = self.suite(broken="import not_a_real_module_xyz\n")
        done = self.run_suite(directory)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("errors=1", done.stdout)


class CheckSbtGateTests(CheckBase):
    def test_sbt_check_runs_batch_check_under_jdk17(self):
        result = self.check("--only", "sbt")
        self.assertEqual(result.rc, 5, result.out)
        self.assertEqual([a for n, a in self.calls("sbt")], ["-batch check"])
        self.assertIn("JAVA_HOME=%s" % self.jdk, self.sbt_env_lines()[0])
        self.assertTrue(any(l.startswith("timeout=3600 ") and "sbt -batch check" in l for l in self.timeout_helper_lines()))

    def test_fake_sbt_failure_propagates_to_a_nonzero_exit(self):
        result = self.check("--only", "sbt", FAKE_SBT_RC="1")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.gate_line(result, "sbt").split()[2], "FAIL")
        self.assertIn("RESULT: FAIL failed: sbt", result.stdout)

    def test_sbt_missing_jdk17_fails_the_gate_with_a_message(self):
        result = self.check("--only", "sbt", JAVA_HOME="/nonexistent", JAVA_HOME_TOOL="/nonexistent", JDK17_FALLBACK_HOME="/nonexistent")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("JDK 17 not found", result.out)
        self.assertEqual(self.calls("sbt"), [])


class CheckTerraformGateTests(CheckBase):
    def build_repo(self):
        super().build_repo()
        self.write("infra/terraform/deployer/tests/x.tftest.hcl", "# test\n")
        self.write("infra/terraform/modules/runtime/versions.tf", "# module: not a root\n")
        self.commit("tests dir")

    def test_fmt_init_validate_and_test_per_root_with_credentials_neutralized(self):
        result = self.check("--only", "terraform", AWS_PROFILE="leaky-profile")
        self.assertEqual(result.rc, 5, result.out)
        words = [a for n, a in self.calls("terraform") if not a.startswith("version")]
        self.assertTrue(any("fmt -check -recursive" in a for a in words))
        roots = ("infra/terraform", "infra/terraform/deployer")
        for root in roots:
            self.assertTrue(any(a.split()[0] == "-chdir=" + root and " init -backend=false -input=false" in a for a in words), root)
            self.assertTrue(any(a.split()[0] == "-chdir=" + root and a.endswith(" validate") for a in words), root)
        self.assertFalse(any("modules/runtime" in a and "init" in a for a in words), "modules are not roots")
        self.assertTrue(all("-lockfile=readonly" in a for a in words if " init " in " " + a + " "), "init must not rewrite tracked lock files")
        tests = [a for a in words if a.endswith(" test")]
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].split()[0], "-chdir=infra/terraform/deployer")
        # AWS_PROFILE leaked into the environment must not reach terraform.
        profiles = [p for n, a, p in self.raw_calls() if n == "terraform" and not a.startswith("version")]
        self.assertTrue(profiles and all(p == "profile=unset" for p in profiles))

    def test_fake_terraform_failures_propagate(self):
        for env in ({"FAKE_TF_FMT_RC": "3"}, {"FAKE_TF_VALIDATE_RC": "1"}, {"FAKE_TF_INIT_RC": "1"}, {"FAKE_TF_TEST_RC": "1"}):
            with self.subTest(env=env):
                result = self.check("--only", "terraform", **env)
                self.assertEqual(result.rc, 4, result.out)
                self.assertEqual(self.gate_line(result, "terraform").split()[2], "FAIL")

    def test_a_modified_tracked_lock_file_fails_the_gate(self):
        self.write("infra/terraform/deployer/.terraform.lock.hcl", "# original\n")
        self.commit("lock")
        self.write("infra/terraform/deployer/.terraform.lock.hcl", "# rewritten by init\n")
        result = self.check("--only", "terraform")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("was modified during the terraform gate", result.out)

    def test_wrong_terraform_version_fails_the_gate_naming_it(self):
        result = self.check("--only", "terraform", FAKE_TF_VERSION="1.13.4")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("terraform version 1.13.4 found; exactly 1.13.5 is required", result.out)
        self.assertEqual([a for n, a in self.calls("terraform") if not a.startswith("version")], [])


class CheckFullRunTests(CheckBase):
    def test_default_invocation_runs_every_gate_and_passes_with_fakes(self):
        self.must_have_shellcheck()
        result = self.check()
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(result.result_line(), "RESULT: PASS gates=7")
        for gate in ("constitution", "hooks", "shell", "python", "script-tests", "sbt", "terraform"):
            self.assertEqual(self.gate_line(result, gate).split()[2], "PASS", result.out)

    def test_skip_marks_the_run_partial(self):
        result = self.check("--skip", "sbt,terraform,script-tests")
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("RESULT: PARTIAL", result.stdout)
        self.assertIn("skipped: terraform script-tests sbt", result.stdout)

    def test_unknown_gate_is_a_usage_error(self):
        self.assertEqual(self.check("--only", "bogus").rc, 2)
        self.assertEqual(self.check("--bogus").rc, 2)

    def test_one_failing_gate_makes_the_whole_run_fail(self):
        result = self.check("--skip", "terraform,script-tests", FAKE_SBT_RC="1")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("RESULT: FAIL failed: sbt", result.stdout)


if __name__ == "__main__":
    unittest.main()

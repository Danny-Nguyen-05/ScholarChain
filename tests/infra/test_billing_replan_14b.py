"""Phase 14B replan (USD 25 course cap), workstream W3: billing, tested from the requirement (test-engineer).

Requirement (user, 2026-11-08): the project budget is USD 25 (the professor's cap; created at 200 in Phase 12D and moved by an
in-place modify) with exactly three ACTUAL-spend alerts at the ABSOLUTE_VALUE amounts 10, 15 and 20 (GREATER_THAN); alerts do not
stop charges. The tooling's public input template for the modify path carries no real account ID (a `<acct>` placeholder) and no
12-digit number at all. "No raw account ID in any new or changed file" (answer 3): a repository scan of what the working tree adds
(legacy Phase 12 evidence is excluded by decision). Findings never print the digits.

The root is planned offline with the real provider (infra_support.ROOTS["billing"], synthetic account and profile); nothing is
applied and no AWS call is made.
"""
import json
import re
import subprocess
import unittest

import account_scan as scan
from infra_support import REPO, InfraTestCase, TfTree, after, managed_changes

ROOT = REPO / "infra/terraform/billing-bootstrap"
TEMPLATE = REPO / "scripts/billing/modify-public-inputs.template.json"
BUDGET = "aws_budgets_budget.project[0]"


class BudgetPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = TfTree("billing")
        cls.addClassCleanup(cls.tree.close)
        cls.budget = after(cls.tree.plan_json(), BUDGET)

    def test_the_only_managed_resource_is_the_one_budget(self):
        self.assertEqual(sorted(managed_changes(self.tree.plan_json())), [BUDGET])

    def test_amount_is_25_usd_over_the_fixed_custom_period(self):
        self.assertEqual(float(self.budget["limit_amount"]), 25.0)
        self.assertEqual(self.budget["limit_unit"], "USD")
        self.assertEqual(self.budget["budget_type"], "COST")
        self.assertEqual(self.budget["time_unit"], "CUSTOM")
        self.assertEqual((self.budget["time_period_start"], self.budget["time_period_end"]), ("2026-10-01_00:00", "2027-01-01_00:00"))

    def test_exactly_three_actual_absolute_value_alerts_at_10_15_and_20(self):
        notes = self.budget["notification"]
        self.assertEqual(len(notes), 3)
        self.assertEqual(sorted(n["threshold"] for n in notes), [10, 15, 20])
        for n in notes:
            with self.subTest(threshold=n["threshold"]):
                self.assertEqual(n["notification_type"], "ACTUAL")
                self.assertEqual(n["threshold_type"], "ABSOLUTE_VALUE")
                self.assertEqual(n["comparison_operator"], "GREATER_THAN")
                self.assertTrue(n["subscriber_email_addresses"], "an alert without a recipient alerts nobody")

    def test_no_percentage_forecasted_or_legacy_alert_remains(self):
        for n in self.budget["notification"]:
            self.assertNotEqual(n["threshold_type"], "PERCENTAGE")
            self.assertNotEqual(n["notification_type"], "FORECASTED")
            self.assertNotIn(n["threshold"], (50, 80, 100, 160, 200))

    def test_credits_stay_out_of_the_budget_so_it_tracks_usage(self):
        cost = self.budget["cost_types"][0]
        self.assertIs(cost["include_credit"], False)
        self.assertIs(cost["include_refund"], False)

    def test_there_is_no_filter_that_could_hide_part_of_the_spend(self):
        self.assertEqual(self.budget["filter_expression"], [])
        self.assertFalse(self.budget.get("cost_filter"))


class BudgetVariables(InfraTestCase):
    def test_the_ceiling_is_25_by_default_and_only_25_is_accepted(self):
        with TfTree("billing") as tree:
            for value in ("200", "26", "24.99", "0", "-25"):
                with self.subTest(value=value):
                    done = tree.plan_attempt(extra_vars={"budget_limit_usd": value})
                    self.assertNotEqual(done.returncode, 0, "a ceiling of %s must be refused\n%s" % (value, done.stdout[-600:]))
            ok = tree.plan_attempt(extra_vars={"budget_limit_usd": "25"})
            self.assertEqual(ok.returncode, 0, (ok.stdout + ok.stderr)[-1500:])

    def test_the_budget_stays_disabled_unless_asked(self):
        with TfTree("billing") as tree:
            done = tree.plan_attempt(extra_vars={"enable_budget": "false"})
            self.assertEqual(done.returncode, 0, (done.stdout + done.stderr)[-1500:])
            self.assertNotIn("aws_budgets_budget", done.stdout)
            self.assertNotIn("Plan:", done.stdout)

    def test_enabling_the_budget_needs_a_recipient(self):
        with TfTree("billing") as tree:
            done = tree.plan_attempt(json_vars={"budget_notification_emails": []})
            self.assertNotEqual(done.returncode, 0)


class ModifyTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = TEMPLATE.read_text()
        cls.data = json.loads(cls.text)

    def test_the_template_holds_no_twelve_digit_number(self):
        self.assertEqual(re.findall(r"[0-9]{12}", self.text), [])

    def test_the_account_is_the_placeholder(self):
        self.assertEqual(self.data["aws_account_id"], "<acct>")
        self.assertEqual(self.text.count("<acct>"), 1)

    def test_the_template_asks_for_the_25_dollar_budget(self):
        self.assertEqual(self.data["budget_limit_usd"], 25)
        self.assertIs(self.data["enable_budget"], True)

    def test_every_key_is_a_declared_variable_and_every_required_variable_is_present(self):
        declared = set(re.findall(r'^variable\s+"([A-Za-z0-9_]+)"', (ROOT / "variables.tf").read_text(), re.M))
        self.assertLessEqual(set(self.data), declared, "a key the root does not declare would be silently ignored or refused")
        required = {"aws_account_id", "aws_profile", "aws_region", "budget_name", "project_period_start_utc", "project_period_end_utc"}
        self.assertLessEqual(required, set(self.data))

    def test_no_notification_address_is_in_the_template(self):
        self.assertNotIn("@", self.text)
        self.assertNotIn("budget_notification_emails", self.data)


class NoRealAccountIdIsAdded(unittest.TestCase):
    def test_no_file_the_working_tree_adds_or_changes_holds_a_real_looking_account_id(self):
        findings, scanned = scan.scan_tree()
        self.assertEqual(findings, [], "%d file(s) scanned; digits intentionally not shown" % len(scanned))

    def test_the_scan_really_covers_changed_and_new_files(self):
        findings, scanned = scan.scan_tree()
        # the billing template is new in this work order, so a scan that reads untracked files must include it
        self.assertIn("scripts/billing/modify-public-inputs.template.json", scanned)
        self.assertFalse([p for p in scanned if p.startswith("docs/agent-runs/phase-12/")])


class AccountScanSelfTest(unittest.TestCase):
    """The scanner flags what it must and ignores what it must; the digits below are synthetic or built to be non-matching."""

    REAL_LOOKING = "4" + "8" * 5 + "7" * 6  # twelve digits, not an allowed synthetic id

    def test_flags_a_real_looking_id_in_every_common_shape(self):
        n = self.REAL_LOOKING
        for text in ("account = %s" % n, "arn:aws:iam::%s:role/x" % n, "bucket-%s-logs" % n, '{"aws_account_id": "%s"}' % n, "id=%s;" % n):
            with self.subTest(text=text.replace(n, "<12>")):
                self.assertEqual(scan.disallowed("docs/x.md", text), [1])

    def test_allows_only_the_synthetic_ids(self):
        for allowed in sorted(scan.SYNTHETIC):
            self.assertEqual(scan.disallowed("docs/x.md", "arn:aws:iam::%s:root" % allowed), [])

    def test_scoped_synthetic_values_are_scoped_to_their_files(self):
        for entry in scan.SCOPED_SYNTHETIC:
            self.assertEqual(scan.disallowed("docs/x.md", "id %s" % entry.value), [1], "outside its file the value is a finding")

    def test_ignores_longer_tokens_hashes_and_uuid_tails(self):
        n = self.REAL_LOOKING
        for text in ("x" + n, n + "0", "sha256:" + "a" * 8 + n + "b" * 8, "11111111-2222-3333-4444-" + "5" * 12, "1" + n):
            with self.subTest(text=text.replace(n, "<12>")):
                self.assertEqual(scan.disallowed("docs/x.md", text), [])

    def test_without_a_merge_base_the_scan_fails_instead_of_passing_vacuously(self):
        import subprocess
        from unittest import mock
        failed = subprocess.CompletedProcess([], 128, stdout="", stderr="fatal: Not a valid object name main")
        with mock.patch.object(scan.subprocess, "run", return_value=failed):
            with self.assertRaises(scan.BaseNotFound):
                scan.scan_tree()

    def test_the_base_is_the_merge_base_with_main_not_head(self):
        base = scan.base_commit()
        self.assertRegex(base, r"^[0-9a-f]{40}$")
        head = scan._git("rev-parse", "HEAD").decode().strip()
        ancestor = subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", base, head]).returncode
        self.assertEqual(ancestor, 0, "the base is an ancestor of HEAD, so committed work after it is scanned")

    def test_reports_the_line_number_not_the_digits(self):
        n = self.REAL_LOOKING
        text = "clean\nclean\nleak %s here\n" % n
        self.assertEqual(scan.disallowed("docs/x.md", text), [3])


class AwsDocumentationExampleAccountEntry(unittest.TestCase):
    """User decision 2026-11-09: AWS's documentation example account is allowed only in AwsTestSupport.scala, as a named exact entry."""

    NAME = "aws-documentation-example-account"
    PATH = "modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/AwsTestSupport.scala"
    EXAMPLE = "1234" + "5678" + "9012"  # split: no literal run in this file
    OTHER = "7" * 12  # twelve digits, not an allowed synthetic value
    ROLE = "arn:aws:iam::%s:role/x"

    def entry(self):
        found = [e for e in scan.SCOPED_SYNTHETIC if e.name == self.NAME]
        self.assertEqual(len(found), 1, "exactly one entry carries the name")
        return found[0]

    def test_i_the_example_id_is_allowed_in_that_exact_file(self):
        self.assertEqual(scan.disallowed(self.PATH, self.ROLE % self.EXAMPLE), [])
        self.assertEqual(scan.disallowed(self.PATH, "ok\n" + self.ROLE % self.EXAMPLE), [])

    def test_ii_any_other_twelve_digit_id_in_that_file_is_a_finding(self):
        self.assertNotIn(self.OTHER, scan.SYNTHETIC)
        self.assertEqual(scan.disallowed(self.PATH, self.ROLE % self.OTHER), [1])
        self.assertEqual(scan.disallowed(self.PATH, "ok\n" + self.ROLE % self.OTHER + "\n" + self.ROLE % self.EXAMPLE), [2])
        # the other scoped synthetic values are not allowed in this file either
        for entry in scan.SCOPED_SYNTHETIC:
            if entry.name != self.NAME:
                self.assertEqual(scan.disallowed(self.PATH, self.ROLE % entry.value), [1], entry.name)

    def test_iii_the_example_id_in_any_other_file_is_a_finding(self):
        directory = self.PATH.rsplit("/", 1)[0]
        others = (
            directory + "/OtherTestSupport.scala",
            directory + "/AwsTestSupport.scala.bak",
            directory + "/AwsTestSupport.scalax",
            directory + "/awstestsupport.scala",
            directory + "/AWSTestSupport.scala",
            "x/" + self.PATH,
            self.PATH + "/",
            "/" + self.PATH,
            self.PATH.replace("src/test", "src/main"),
            "docs/x.md",
            "modules/services/src/test/scala/AwsTestSupport.scala",
        )
        for other in others:
            with self.subTest(path=other):
                self.assertEqual(scan.disallowed(other, self.ROLE % self.EXAMPLE), [1])

    def test_iv_the_entry_is_found_by_name_and_its_path_is_a_plain_string(self):
        entry = self.entry()
        self.assertIs(type(entry.path), str)
        self.assertEqual(entry.path, self.PATH)
        self.assertIsNone(entry.pattern, "the entry carries no pattern")
        self.assertEqual(entry.value, self.EXAMPLE)
        self.assertEqual(entry.name, scan.AWS_DOCUMENTATION_EXAMPLE_ACCOUNT)

    def test_v_no_other_scoped_entry_and_not_the_global_set_allows_the_example(self):
        self.assertNotIn(self.EXAMPLE, scan.SYNTHETIC)
        holders = [e.name for e in scan.SCOPED_SYNTHETIC if e.value == self.EXAMPLE]
        self.assertEqual(holders, [self.NAME])
        names = [e.name for e in scan.SCOPED_SYNTHETIC]
        self.assertEqual(len(names), len(set(names)), "entry names are unique")


if __name__ == "__main__":
    unittest.main()

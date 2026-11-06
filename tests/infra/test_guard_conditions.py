"""Phase 13C item 10: the Terraform literal-source guard (tests/infra/terraform_source_guard.py) must inspect
conditions. Before this change `kms:CreateKey` on Resource "*" passed whatever its Condition said, because the
no-resource-type exemption ignored the Condition entirely.

The guard is stdlib-only, offline and reads source text, so these cases need no Terraform. The guard's path is
tests/infra/terraform_source_guard.py (run by IndependentTerraformSourceSpec through sbt check as well).
"""
import json
import subprocess
import sys
import unittest

import hcl_text
import infra_support as s
import terraform_source_guard as guard

CREATE_KEY = '{Effect="Allow", Action=["kms:CreateKey"], Resource="*"%s}'
RUN_JOB_FLOW = '{Effect="Allow", Action=["elasticmapreduce:RunJobFlow"], Resource="*"%s}'
REQUEST_TAG = ', Condition={StringEquals={"aws:RequestTag/scholarchain:stack"="spike-emr"}}'
CATEGORY = "unconditioned-request-scoped-action"


def categories(source):
    return [f["category"] for f in guard.scan("synthetic.tf", source)]


class GuardInspectsConditions(unittest.TestCase):
    def test_condition_stripped_create_key_is_rejected(self):
        self.assertIn(CATEGORY, categories(CREATE_KEY % ""))

    def test_condition_stripped_run_job_flow_is_rejected(self):
        self.assertIn(CATEGORY, categories(RUN_JOB_FLOW % ""))

    def test_empty_null_and_region_only_conditions_are_rejected(self):
        for condition in (", Condition={}", ", Condition=null",
                          ', Condition={StringEquals={"aws:RequestedRegion"="us-east-2"}}'):
            with self.subTest(condition=condition):
                self.assertIn(CATEGORY, categories(CREATE_KEY % condition))
                self.assertIn(CATEGORY, categories(RUN_JOB_FLOW % condition))

    def test_request_tag_condition_is_accepted_and_exempt_actions_stay_exempt(self):
        self.assertEqual(categories(CREATE_KEY % REQUEST_TAG), [])
        self.assertEqual(categories(RUN_JOB_FLOW % REQUEST_TAG), [])
        # Read-only no-resource-type actions need no request tag.
        self.assertEqual(categories('{Effect="Allow", Action=["kms:ListAliases"], Resource="*"}'), [])

    def test_a_deny_for_the_same_action_is_not_flagged(self):
        self.assertEqual(categories('{Effect="Deny", Action=["kms:CreateKey"], Resource="*"}'), [])

    def test_mixing_a_second_action_does_not_hide_the_missing_condition(self):
        self.assertIn(CATEGORY, categories('{Effect="Allow", Action=["kms:CreateKey", "kms:ListAliases"], Resource="*"}'))

    def test_findings_carry_only_path_line_and_category(self):
        found = guard.scan("p.tf", "\n\n" + CREATE_KEY % "")
        self.assertEqual(found, [{"path": "p.tf", "line": 3, "category": CATEGORY}])

    # ---- the real deployer source -------------------------------------------------------------------------------

    def test_the_real_deployer_source_passes(self):
        text = (s.REPO / "infra/terraform/deployer/permission_sets.tf").read_text()
        self.assertEqual(guard.scan("permission_sets.tf", text), [])

    def test_stripping_the_condition_from_the_real_create_key_statement_is_rejected_at_its_line(self):
        text = (s.REPO / "infra/terraform/deployer/permission_sets.tf").read_text()
        mutated = hcl_text.strip_attribute_after(text, '"KmsCreateKeyWithStackTag"', "Condition")
        self.assertNotEqual(mutated, text)
        found = guard.scan("permission_sets.tf", mutated)
        self.assertEqual([f["category"] for f in found], [CATEGORY])
        action_line = [i for i, line in enumerate(mutated.splitlines(), 1)
                       if '"kms:CreateKey"' in line and not line.lstrip().startswith("#")]
        self.assertEqual([found[0]["line"]], action_line)

    def test_stripping_the_condition_from_the_real_run_job_flow_statement_is_rejected(self):
        text = (s.REPO / "infra/terraform/deployer/permission_sets.tf").read_text()
        mutated = hcl_text.strip_attribute_after(text, '"EmrRunJobFlowRequireStackTags"', "Condition")
        self.assertEqual([f["category"] for f in guard.scan("permission_sets.tf", mutated)], [CATEGORY])

    # ---- the command line contract used by sbt check ---------------------------------------------------------------

    def test_guard_self_test_and_repository_scan_pass(self):
        guard_path = str(s.HERE / "terraform_source_guard.py")
        selftest = subprocess.run([sys.executable, "-I", guard_path, "--self-test"], capture_output=True, text=True, timeout=120)
        self.assertEqual(selftest.returncode, 0, selftest.stderr[-800:])
        self.assertRegex(selftest.stderr + selftest.stdout, r"Ran \d+ tests?")
        scan = subprocess.run([sys.executable, "-I", guard_path, "--repo-root", str(s.REPO)], capture_output=True, text=True, timeout=120)
        self.assertEqual(scan.returncode, 0, scan.stdout[-800:] + scan.stderr[-400:])
        self.assertEqual(json.loads(scan.stdout)["findings"], [])


if __name__ == "__main__":
    unittest.main()

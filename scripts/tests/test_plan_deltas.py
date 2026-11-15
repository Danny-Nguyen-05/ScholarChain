"""Phase 14B pre-session item 9: the reviewed expected plan addresses of the pointer and EMR runtime-applies
(scripts/config/expected-plan-deltas.json), the offline derivation parser and the live comparison
(scripts/lib/plan_deltas.py). Hand-derived expectations on synthetic text; no Terraform run, no AWS call.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import REAL_REPO, SCRIPTS_DIR

TOOL = os.path.join(SCRIPTS_DIR, "lib", "plan_deltas.py")
EXPECTED = os.path.join(SCRIPTS_DIR, "config", "expected-plan-deltas.json")
TFTEST = os.path.join(REAL_REPO, "infra", "terraform", "tests", "phase14b_plan_deltas.tftest.hcl")
sys.path.insert(0, os.path.join(SCRIPTS_DIR, "lib"))
import plan_deltas as pd  # noqa: E402

TASK = 'module.runtime.aws_ecs_task_definition.service["query-api"]'
SERVICE = 'module.runtime.aws_ecs_service.service["query-api"]'


def verbose(plans):
    """Build `terraform test -verbose` shaped text. plans: {run: {address: [attribute lines]}}."""
    out = ["tests/x.tftest.hcl... in progress"]
    for run, resources in plans.items():
        out += ['  run "%s"... pass' % run, "", "Terraform will perform the following actions:", ""]
        for address, lines in resources.items():
            out += ["  # %s will be created" % address, '  + resource "t" "n" {'] + lines + ["    }", ""]
        out += ["Plan: %d to add, 0 to change, 0 to destroy." % len(resources), ""]
    return "\n".join(out)


class Expected(unittest.TestCase):
    def setUp(self):
        with open(EXPECTED, encoding="utf-8") as handle:
            self.doc = json.load(handle)

    def test_the_list_declares_itself_offline_derived_and_never_an_approval(self):
        self.assertEqual(self.doc["schema"], "scholarchain.expected-plan-deltas.v1")
        self.assertIn("DERIVED OFFLINE", self.doc["status"])
        self.assertIn("not an approval", self.doc["status"])
        self.assertEqual(self.doc["provenance"]["source_test"], "infra/terraform/tests/phase14b_plan_deltas.tftest.hcl")
        self.assertEqual(self.doc["provenance"]["terraform_version"], "1.13.5")
        self.assertEqual(set(self.doc["stages"]), {"pointer-apply", "emr-apply"})

    def test_the_pointer_apply_is_one_replaced_task_definition_and_one_updated_service_of_query_api(self):
        stage = self.doc["stages"]["pointer-apply"]
        self.assertEqual({e["address"]: e["actions"] for e in stage["actions"]}, {TASK: "delete+create", SERVICE: "update"})
        self.assertEqual(stage["plan_line"], "Plan: 1 to add, 1 to change, 1 to destroy.")
        self.assertEqual(stage["summary_line"], "summary: add=0 change=1 destroy=0 replace=1")
        basis = {e["address"]: e["basis"] for e in stage["actions"]}
        self.assertTrue(basis[TASK].startswith("mock-derived"))
        self.assertTrue(basis[SERVICE].startswith("hand-derived"), "the service update cannot be seen offline and must say so")

    def test_the_emr_apply_creates_thirteen_emr_resources_and_nothing_else(self):
        stage = self.doc["stages"]["emr-apply"]
        self.assertEqual(len(stage["actions"]), 13)
        self.assertEqual({e["actions"] for e in stage["actions"]}, {"create"})
        addresses = [e["address"] for e in stage["actions"]]
        self.assertEqual(len(set(addresses)), 13)
        self.assertEqual(sorted(a for a in addresses if not a.startswith("module.emr.")),
                         ["module.identity.aws_iam_role_policy.emr_control[0]", "module.identity.aws_iam_role_policy.emr_disk_encryption[0]"])
        self.assertIn("module.emr.aws_emr_cluster.pipeline[0]", addresses)
        self.assertEqual(stage["plan_line"], "Plan: 13 to add, 0 to change, 0 to destroy.")
        self.assertEqual(stage["summary_line"], "summary: add=13 change=0 destroy=0 replace=0")

    def test_summary_lines_follow_from_the_action_lists(self):
        for name, stage in self.doc["stages"].items():
            with self.subTest(stage=name):
                kinds = [pd.normalize_actions(e["actions"]) for e in stage["actions"]]
                add, change, destroy, replace = kinds.count("create"), kinds.count("update"), kinds.count("delete"), kinds.count("replace")
                self.assertEqual(stage["plan_line"], "Plan: %d to add, %d to change, %d to destroy." % (add + replace, change, destroy + replace))
                self.assertEqual(stage["summary_line"], "summary: add=%d change=%d destroy=%d replace=%d" % (add, change, destroy, replace))

    def test_every_listed_address_names_a_resource_that_exists_in_the_terraform_source(self):
        for stage in self.doc["stages"].values():
            for entry in stage["actions"]:
                module, rtype, name = re.match(r"^module\.([a-z_]+)\.([a-z0-9_]+)\.([a-z_0-9]+)(\[.*\])?$", entry["address"]).groups()[:3]
                found = False
                for fname in os.listdir(os.path.join(REAL_REPO, "infra", "terraform", "modules", module)):
                    if fname.endswith(".tf"):
                        with open(os.path.join(REAL_REPO, "infra", "terraform", "modules", module, fname), encoding="utf-8") as handle:
                            found = found or ('resource "%s" "%s"' % (rtype, name)) in handle.read()
                self.assertTrue(found, entry["address"])

    def test_no_account_id_email_or_key_is_stored_in_the_list(self):
        text = open(EXPECTED, encoding="utf-8").read()
        self.assertIsNone(re.search(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])", text))
        self.assertNotIn(chr(64), text)

    def test_the_derivation_test_file_carries_the_three_run_names_the_parser_expects(self):
        with open(TFTEST, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(re.findall(r'^run "([a-z0-9_]+)"', text, re.M), list(pd.EXPECTED_RUNS))
        self.assertIsNone(re.search(r"command\s*=\s*apply", text), "plan-only: the mock provider must never apply")
        self.assertEqual(len(re.findall(r"command\s*=\s*plan", text)), 3)


class Derive(unittest.TestCase):
    def plans(self):
        base = {'a.one': ["      + name = \"x\""], 'a.two': ["      + id   = \"k3j4h5g6\""], TASK: ["      + env = 1"]}
        pointer = {'a.one': ["      + name = \"x\""], 'a.two': ["      + id   = \"z9y8x7w6\""], TASK: ["      + env = 2"]}
        emr = dict(pointer, **{'module.emr.b': ["      + k = 1"]})
        return {pd.EXPECTED_RUNS[0]: base, pd.EXPECTED_RUNS[1]: pointer, pd.EXPECTED_RUNS[2]: emr}

    def test_mock_noise_is_ignored_and_real_differences_are_found(self):
        result = pd.derive(verbose(self.plans()))
        self.assertEqual(result["pointer-apply"], {"added": [], "removed": [], "changed": [TASK]})
        self.assertEqual(result["emr-apply"], {"added": ["module.emr.b"], "removed": [], "changed": []})
        self.assertEqual(result["plan_sizes"], {pd.EXPECTED_RUNS[0]: 3, pd.EXPECTED_RUNS[1]: 3, pd.EXPECTED_RUNS[2]: 4})

    def test_a_missing_run_is_an_error_not_an_empty_delta(self):
        plans = self.plans()
        del plans[pd.EXPECTED_RUNS[2]]
        with self.assertRaises(ValueError):
            pd.derive(verbose(plans))
        with self.assertRaises(ValueError):
            pd.derive("nothing here")

    def test_cli_derive_prints_json_and_exits_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(verbose(self.plans()))
            done = subprocess.run([sys.executable, "-I", TOOL, "derive", "--verbose-output", path], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)["pointer-apply"]["changed"], [TASK])
            done = subprocess.run([sys.executable, "-I", TOOL, "derive", "--verbose-output", path + ".absent"], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 2)


class Check(unittest.TestCase):
    def setUp(self):
        self.expected = pd.load_expected(EXPECTED)
        self.tmp = tempfile.mkdtemp(prefix="sc-deltas-")
        self.addCleanup(subprocess.run, ["rm", "-rf", self.tmp])

    def log(self, entries):
        return "\n".join(["PLAN-ACTIONS-BEGIN count=%d" % len(entries)] + ["PLAN-ACTION: %s %s" % e for e in entries] + ["PLAN-ACTIONS-END count=%d" % len(entries)])

    def pointer_entries(self):
        return [(e["actions"], e["address"]) for e in self.expected["stages"]["pointer-apply"]["actions"]]

    def test_the_expected_pointer_plan_is_identical_and_either_replace_order_is_accepted(self):
        lines, ok = pd.check("pointer-apply", self.log(self.pointer_entries()), self.expected)
        self.assertTrue(ok, lines)
        swapped = [("create+delete", TASK), ("update", SERVICE)]
        lines, ok = pd.check("pointer-apply", self.log(swapped), self.expected)
        self.assertTrue(ok, lines)

    def test_missing_unexpected_and_changed_actions_are_all_reported(self):
        cases = {
            "MISSING": [("delete+create", TASK)],
            "UNEXPECTED": self.pointer_entries() + [("update", 'module.runtime.aws_ecs_service.service["graph-service"]')],
            "ACTION-DIFFERS": [("create", TASK), ("update", SERVICE)],
        }
        for tag, entries in cases.items():
            with self.subTest(tag):
                lines, ok = pd.check("pointer-apply", self.log(entries), self.expected)
                self.assertFalse(ok)
                self.assertTrue(any(line.startswith(tag + ":") for line in lines), lines)

    def test_a_delete_or_replace_of_a_load_balancer_is_unexpected(self):
        entries = self.pointer_entries() + [("delete+create", "module.runtime.aws_lb.query[0]")]
        lines, ok = pd.check("pointer-apply", self.log(entries), self.expected)
        self.assertFalse(ok)
        self.assertIn("UNEXPECTED: replace module.runtime.aws_lb.query[0] (in the plan, not in the reviewed list)", lines)

    def test_the_emr_stage_is_checked_against_its_own_list_and_an_empty_log_never_matches(self):
        entries = [(e["actions"], e["address"]) for e in self.expected["stages"]["emr-apply"]["actions"]]
        lines, ok = pd.check("emr-apply", self.log(entries), self.expected)
        self.assertTrue(ok, lines)
        lines, ok = pd.check("pointer-apply", self.log(entries), self.expected)
        self.assertFalse(ok)
        lines, ok = pd.check("emr-apply", "no plan lines at all", self.expected)
        self.assertFalse(ok)

    def test_cli_exit_codes_and_the_final_result_line(self):
        path = os.path.join(self.tmp, "plan.log")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.log(self.pointer_entries()))
        done = subprocess.run([sys.executable, "-I", TOOL, "check", "--stage", "pointer-apply", "--plan-log", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(done.stdout.strip().splitlines()[-1].startswith("RESULT: IDENTICAL stage=pointer-apply"))
        self.assertIn("not an approval to apply", done.stdout)
        done = subprocess.run([sys.executable, "-I", TOOL, "check", "--stage", "emr-apply", "--plan-log", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 1)
        self.assertTrue(done.stdout.strip().splitlines()[-1].startswith("RESULT: DIFFERS stage=emr-apply"))
        done = subprocess.run([sys.executable, "-I", TOOL, "check", "--stage", "emr-apply", "--plan-log", path + ".absent"], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2)
        done = subprocess.run([sys.executable, "-I", TOOL, "check", "--stage", "bogus", "--plan-log", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2)


if __name__ == "__main__":
    unittest.main()

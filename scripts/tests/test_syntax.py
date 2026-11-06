"""Static checks: bash -n and shellcheck clean, --help contents, configuration, no hardcoded identifiers."""
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import REAL_REPO, SCRIPTS_DIR

SCRIPTS_13A = ["check.sh", "package.sh", "plan.sh", "deploy.sh", "rollback.sh", "cleanup.sh"]
SCRIPTS_13B = ["smoke-test.sh", "smoke-local.sh", "run-bounded-pipeline.sh", "run-experiment.sh", "archive-evidence.sh"]
SCRIPTS = SCRIPTS_13A + SCRIPTS_13B
SHELL_FILES = SCRIPTS + ["lib/common.sh", "emr/bootstrap.sh", "emr/sc-step.sh"]
PY_FILES = [
    "lib/timeout.py", "lib/tools.py", "lib/plan_summary.py", "lib/redact.py", "lib/verify.py", "lib/safeio.py", "lib/state_bind.py", "lib/records.py",
    "lib/budget.py", "lib/pipeline.py", "lib/run_approval.py", "lib/experiment.py", "lib/smoke_client.py", "lib/archive.py",
    "emr/sc-ceiling-check.py", "emr/sc-class-origin-verify.py", "emr/sc-render-spark-config.py",
]
CLOUD_SCRIPTS = ["plan.sh", "deploy.sh", "rollback.sh", "cleanup.sh", "run-bounded-pipeline.sh"]


def read(rel):
    with open(os.path.join(SCRIPTS_DIR, rel), encoding="utf-8") as handle:
        return handle.read()


def parse_conf():
    values = {}
    for line in read("config/release.conf").splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


class SyntaxTests(unittest.TestCase):
    def test_bash_syntax(self):
        for rel in SHELL_FILES:
            with self.subTest(rel):
                result = subprocess.run(["bash", "-n", os.path.join(SCRIPTS_DIR, rel)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_shellcheck_reports_zero_findings(self):
        if not shutil.which("shellcheck"):
            self.skipTest("shellcheck is not installed")
        result = subprocess.run(
            ["shellcheck", "-x", "-P", "SCRIPTDIR"] + [os.path.join(SCRIPTS_DIR, rel) for rel in SHELL_FILES],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_no_blanket_shellcheck_disables_and_each_targeted_one_is_justified(self):
        for rel in SHELL_FILES:
            for number, line in enumerate(read(rel).splitlines(), 1):
                if "shellcheck disable" in line:
                    self.assertRegex(line, r"shellcheck disable=SC\d+ #\s*\S+", "%s:%d needs a justification comment" % (rel, number))

    def test_strict_mode_and_shebang(self):
        for rel in SCRIPTS:
            with self.subTest(rel):
                text = read(rel)
                self.assertTrue(text.startswith("#!/usr/bin/env bash\n"))
                self.assertIn("\nset -euo pipefail\n", text)
                self.assertTrue(os.access(os.path.join(SCRIPTS_DIR, rel), os.X_OK), "%s must be executable" % rel)

    def test_python_helpers_compile(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in PY_FILES + ["tests/fake_tool.py", "tests/helpers.py"]:
                py_compile.compile(os.path.join(SCRIPTS_DIR, rel), cfile=os.path.join(tmp, os.path.basename(rel) + "c"), doraise=True)

    def test_no_script_reads_a_secret_file_or_env_file(self):
        for rel in SHELL_FILES + PY_FILES:
            text = read(rel)
            self.assertNotRegex(text, r"(?<![\w.])\.env(?![\w-])", rel)
            self.assertNotRegex(text, r"\.local\.tfvars", rel + " must not reference private var files by name")


class HelpTests(unittest.TestCase):
    def help_of(self, rel):
        result = subprocess.run(["bash", os.path.join(SCRIPTS_DIR, rel), "--help"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}, cwd=tempfile.gettempdir())
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_every_help_documents_purpose_inputs_approval_exit_codes_and_evidence(self):
        for rel in SCRIPTS:
            with self.subTest(rel):
                text = self.help_of(rel)
                lowered = text.lower()
                self.assertIn("Purpose", text)
                self.assertIn("Inputs", text)
                self.assertIn("Exit codes", text)
                self.assertIn("evidence produced", lowered)
                self.assertIn("human approval", lowered)
                self.assertTrue(re.search(r"^\s+2\s+usage error", text, re.M), "exit code 2 documented")
                self.assertTrue(re.search(r"^\s+0\s+", text, re.M), "exit code 0 documented")

    def test_cloud_scripts_document_dry_run_as_the_default(self):
        for rel in CLOUD_SCRIPTS:
            with self.subTest(rel):
                text = self.help_of(rel).lower()
                self.assertIn("dry run", text)
                self.assertIn("--execute", text)
        for rel in CLOUD_SCRIPTS:
            self.assertRegex(self.help_of(rel).lower(), r"default", rel)

    def test_help_lists_env_var_names_not_values(self):
        for rel in CLOUD_SCRIPTS:
            text = self.help_of(rel)
            self.assertIn("SCHOLARCHAIN_AWS_REGION", text)
            self.assertNotRegex(text, r"\b\d{12}\b")

    def test_deploy_help_documents_the_stages_the_prespend_gate_and_the_exact_dirty_tree_exemption(self):
        text = self.help_of("deploy.sh")
        for needle in (
            "APPROVED_PRESPEND_SHA256", "APPROVED_STAGE", "APPROVED_RECEIPT_SHA256", "APPROVED_ENVIRONMENT", "--stage base-apply|push|runtime-apply|cleanup-prepare", "PRESPEND_MAX_AGE_HOURS", "PRESPEND_MIN_HEADROOM_USD",
            "literal configured approval-record path", "plan-provenance", "verified copy", "state-binding", "push record", "DEFERRED to --execute", "RE-VERIFIED",
        ):
            self.assertIn(needle, text)

    def test_cleanup_help_documents_the_preservation_policy_and_the_bound_token(self):
        text = self.help_of("cleanup.sh")
        for needle in ("PRESERVED", "TEARDOWN", "-target", "CONFIRM-TOKEN", "does NOT re-plan", "S3 Vectors", "KMS", "PREPARE-REQUIRED", "--prepare", "CLEANUP_PROTECTION_RULES", "cleanup-prepare"):
            self.assertIn(needle, text)

    def test_plan_help_documents_the_private_outputs_and_the_complete_review_path(self):
        text = self.help_of("plan.sh")
        for needle in ("PLAN-ACTION", "PLAN-TEXT", "show -no-color", "git check-ignore", "--source-commit", "plan-receipt.v2", "--expect-new-state", "git archive", "TERRAFORM_STATE_FILE", "O_CREAT|O_EXCL|O_NOFOLLOW"):
            self.assertIn(needle, text)

    def test_distinct_documented_exit_codes_for_cloud_scripts(self):
        for rel in CLOUD_SCRIPTS:
            text = self.help_of(rel)
            self.assertIn("3", text)
            self.assertRegex(text, r"124")


class ConfigurationTests(unittest.TestCase):
    def test_required_settings_present_with_documented_values(self):
        conf = parse_conf()
        self.assertEqual(conf["IMAGE_PLATFORM"], "linux/amd64")
        self.assertEqual(conf["REQUIRED_TERRAFORM_VERSION"], "1.13.5")
        self.assertEqual(conf["APPROVAL_RECORD_PATH"], "docs/agent-runs/phase-14/human-gate.md")
        self.assertEqual(conf["RUNTIME_ARCHIVE_EXPECTED_SHA256"], "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5")
        self.assertEqual(conf["RUNTIME_ARCHIVE_EXPECTED_SIZE"], "321876735")
        self.assertEqual(conf["RUNTIME_ARCHIVE_S3_URI_ENV"], "SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI")
        services = dict(pair.split("=") for pair in conf["SERVICE_ARTIFACTS"].split())
        self.assertEqual(
            services,
            {
                "query-api": "edu.uic.cs441.scholarchain.services.QueryApiMain",
                "graph-service": "edu.uic.cs441.scholarchain.services.GraphServiceMain",
                "semantic-service": "edu.uic.cs441.scholarchain.services.SemanticServiceMain",
                "embedding-worker": "edu.uic.cs441.scholarchain.services.EmbeddingWorkerMain",
            },
        )
        for key, value in conf.items():
            if key.startswith("TIMEOUT_"):
                self.assertTrue(value.isdigit() and int(value) > 0, key)

    def test_new_policy_and_prespend_settings_are_pinned_with_the_decided_values(self):
        conf = parse_conf()
        self.assertEqual(conf["PRESPEND_MAX_AGE_HOURS"], "24")
        self.assertEqual(conf["PRESPEND_MIN_HEADROOM_USD"], "20")
        self.assertEqual(conf["PLAN_DIR"], "target/plans")
        common = read("lib/common.sh")
        pinned = re.search(r'SC_PINNED_KEYS="([^"]*)"', common).group(1).split()
        for key in ("PLAN_DIR", "PRESPEND_MAX_AGE_HOURS", "PRESPEND_MIN_HEADROOM_USD", "CLEANUP_PRESERVE_TYPE_RULES", "CLEANUP_PRESERVE_ADDRESS_RULES", "CLEANUP_TEARDOWN_ADDRESS_RULES", "APPROVAL_RECORD_PATH", "TERRAFORM_STATE_FILE", "CLEANUP_PROTECTION_RULES", "CLEANUP_PREPARE_ALLOWED_ATTRS"):
            self.assertIn(key, pinned)
            self.assertIn(key, conf)

    def test_the_required_script_test_suites_are_pinned_in_check_sh_not_in_the_config(self):
        self.assertNotIn("SCRIPT_TEST_SUITES", parse_conf())
        check = read("check.sh")
        self.assertIn('REQUIRED_SUITES="discover:scripts/tests discover:scripts/phase12d-spike/tests files:scripts/billing/tests discover:tests/scripts discover:tests/infra"', check)
        self.assertNotIn("${SCRIPT_TEST_SUITES", check)

    def test_the_preservation_policy_covers_every_preserved_class_the_user_decided(self):
        conf = parse_conf()
        types = conf["CLEANUP_PRESERVE_TYPE_RULES"].split(",")
        for prefix in ("aws_s3_bucket", "aws_s3_object", "aws_s3vectors_", "aws_kms_", "aws_cloudwatch_log_group"):
            self.assertIn(prefix, types)
        for address in ("module.foundation.", "module.datalake.", "module.s3vectors."):
            self.assertIn(address, conf["CLEANUP_PRESERVE_ADDRESS_RULES"].split(","))
        teardown = conf["CLEANUP_TEARDOWN_ADDRESS_RULES"].split(",")
        for module in ("runtime", "emr", "neptune", "dynamodb", "messaging", "workflow", "network"):
            self.assertIn("module.%s." % module, teardown)
        self.assertNotIn("module.identity.aws_iam_role.deployment", teardown)
        self.assertFalse([t for t in teardown if t.startswith(("module.foundation", "module.datalake", "module.s3vectors"))])

    def test_every_setting_block_has_a_rationale_comment(self):
        """Each KEY=value line belongs to a blank-line-separated block that starts with a comment."""
        lines = read("config/release.conf").splitlines()
        for index, line in enumerate(lines):
            if re.match(r"^[A-Z][A-Z0-9_]*=", line):
                cursor = index
                while cursor > 0 and lines[cursor - 1].strip() != "":
                    cursor -= 1
                self.assertTrue(lines[cursor].startswith("#"), "%s needs a rationale comment above it" % line.split("=")[0])

    def test_no_bucket_account_region_or_endpoint_is_hardcoded(self):
        conf = read("config/release.conf")
        self.assertNotRegex(conf, r"s3://")
        self.assertNotRegex(conf, r"\b\d{12}\b")
        self.assertNotRegex(conf, r"\b[a-z]{2}-[a-z]+-\d\b", "no region in config")
        self.assertNotRegex(conf, r"amazonaws\.com")
        for rel in SHELL_FILES + PY_FILES:
            text = read(rel)
            self.assertNotRegex(text, r"(?<![\d.])\d{12}(?![\d.])", "%s contains a 12-digit run" % rel)
            self.assertNotRegex(text, r"s3://(?!bucket/)[a-z0-9][a-z0-9.-]+/", "%s hardcodes a bucket" % rel)

    def test_config_is_consistent_with_the_real_dockerfile_and_ecs_task(self):
        conf = parse_conf()
        with open(os.path.join(REAL_REPO, "Dockerfile")) as handle:
            dockerfile = handle.read()
        allow = set(re.findall(r"(edu\.uic\.cs441\.scholarchain\.services\.\w+Main)", dockerfile.split("case", 1)[1].split("esac", 1)[0]))
        self.assertEqual(allow, {pair.split("=")[1] for pair in conf["SERVICE_ARTIFACTS"].split()})
        completed = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS_DIR, "lib", "tools.py"), "ecs-arch", os.path.join(REAL_REPO, conf["ECS_ARCH_SOURCE"])], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), conf["IMAGE_PLATFORM"])


if __name__ == "__main__":
    unittest.main()

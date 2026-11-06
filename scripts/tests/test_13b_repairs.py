"""Subphase 13B repair round (findings D1, O1, O2, O3, O4 of the independent tests/scripts suite), each tested at its boundary.

D1 the documented 10 minute minimum is real; O1 an unknown APPROVED_* key refuses; O2 generic secret/token/password/api-key
assignments are redacted and flagged by the post-write verification; O3 bad usage still prints markers and one RESULT line in
every script; O4 API_KEY-named and *_KEY-named variables are redacted by every script."""
import json
import os
import re
import subprocess
import sys
import unittest

from helpers import FAKE_ACCOUNT, SCRIPTS_DIR, Fixture, sha256_bytes
from pipeline_helpers import PipelineFixture
from test_archive import ArchiveBase

ALL_SCRIPTS = (
    "check.sh", "package.sh", "plan.sh", "deploy.sh", "rollback.sh", "cleanup.sh", "smoke-test.sh", "smoke-local.sh",
    "run-bounded-pipeline.sh", "run-experiment.sh", "archive-evidence.sh",
)
VALUE_FLAG = {
    "check.sh": "--only", "plan.sh": "--env", "deploy.sh": "--stage", "rollback.sh": "--env", "cleanup.sh": "--env", "smoke-test.sh": "--url",
    "smoke-local.sh": "--port", "run-bounded-pipeline.sh": "--cluster-id", "run-experiment.sh": "--manifest", "archive-evidence.sh": "--phase",
}
APPROVAL_LIB = os.path.join(SCRIPTS_DIR, "lib", "run_approval.py")


class UsageTests(Fixture):
    def check_usage(self, script, *args):
        result = self.run_script(script, *args)
        self.assertEqual(result.rc, 2, "%s %s: %s" % (script, args, result.out))
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "STEP: start", result.out)
        self.assertIn("STEP: usage", lines)
        results = [l for l in lines if l.startswith("RESULT: ")]
        self.assertEqual(len(results), 1, result.out)
        self.assertTrue(results[0].startswith("RESULT: REFUSED step=usage reason="), results[0])
        self.assertEqual(lines[-1], results[0], "the RESULT line is the last line")
        self.assertEqual(self.calls(), [], "a usage error runs nothing")
        return result

    def test_an_unknown_flag_prints_markers_and_exactly_one_result_line_in_every_script(self):
        for script in ALL_SCRIPTS:
            with self.subTest(script):
                result = self.check_usage(script, "--bogus-flag")
                self.assertIn("unknown argument: --bogus-flag", result.out)

    def test_a_flag_without_its_value_does_too(self):
        for script, flag in VALUE_FLAG.items():
            with self.subTest(script):
                result = self.check_usage(script, flag)
                self.assertIn("needs a value", result.out)

    def test_help_still_exits_zero_without_a_result_line(self):
        for script in ALL_SCRIPTS:
            with self.subTest(script):
                result = self.run_script(script, "--help")
                self.assertEqual(result.rc, 0, result.out)
                self.assertFalse([l for l in result.stdout.splitlines() if l.startswith("RESULT: ")])

    def test_the_usage_message_is_redacted(self):
        result = self.run_script("check.sh", "--bogus-%s" % FAKE_ACCOUNT)
        self.assertEqual(result.rc, 2)
        self.assertNotIn(FAKE_ACCOUNT, result.out)


class RuntimeMinimumTests(PipelineFixture):
    def test_ten_minutes_is_the_accepted_minimum_and_nine_is_refused_with_the_range(self):
        ok = self.dry(**{"--max-runtime-minutes": "10", "--budget-usd": "1"})
        self.assertEqual(ok.rc, 0, ok.out)
        self.assertIn("PLAN: max-runtime-minutes: 10", ok.stdout)
        seconds = {m.group(1): int(m.group(2)) for m in re.finditer(r"^STEP-TIMEOUT: (\S+) (\d+)s", ok.stdout, re.M)}
        self.assertEqual(seconds, {"stage-in": 30, "hadoop-prep": 120, "entity-resolution": 120, "spark-class-origin": 30, "spark-job": 240, "copy-out": 60})
        self.assertEqual(sum(seconds.values()), 600, "the weighted timeouts fit the 10 minute cap exactly")
        refused = self.dry(**{"--max-runtime-minutes": "9", "--budget-usd": "1"})
        self.assertEqual(refused.rc, 3, refused.out)
        self.assertIn("step=plan", refused.result_line())
        self.assertIn("--max-runtime-minutes must be between 10 and the cap 180", refused.out)
        self.assertEqual(self.calls(), [])

    def test_the_weighted_timeouts_never_exceed_the_cap_at_any_accepted_runtime(self):
        for minutes in (10, 11, 15, 19, 20, 33, 180):
            with self.subTest(minutes):
                result = self.dry(**{"--max-runtime-minutes": str(minutes), "--budget-usd": "3"})
                self.assertEqual(result.rc, 0, result.out)
                total = sum(int(m.group(1)) for m in re.finditer(r"^STEP-TIMEOUT: \S+ (\d+)s", result.stdout, re.M))
                self.assertLessEqual(total, minutes * 60)

    def test_a_larger_step_floor_in_the_pinned_config_refuses_a_run_that_cannot_fit(self):
        self.use_config(PIPELINE_MIN_STEP_SECONDS="120")
        result = self.dry(**{"--max-runtime-minutes": "10", "--budget-usd": "1"})
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("(each at least 120 s) exceed the maximum runtime of 600 s", result.out)

    def test_help_and_readme_document_the_minimum(self):
        text = subprocess.run(["bash", os.path.join(SCRIPTS_DIR, "run-bounded-pipeline.sh"), "--help"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}).stdout
        self.assertIn("10 is a real minimum", text)
        self.assertIn("PIPELINE_MIN_STEP_SECONDS", text)
        with open(os.path.join(SCRIPTS_DIR, "README.md"), encoding="utf-8") as handle:
            self.assertIn("so 10 is a real minimum and 9 is refused at step `plan`", handle.read())


class UnknownApprovalKeyTests(PipelineFixture):
    def run_with_extra(self, extra):
        args = self.ready()
        run_sha = self.value_of(self.dry(), "RUN-CONFIG-SHA256: ")
        record = self.write_record(self.approval_lines(run_sha, self.prespend_sha), name="extra.md", raw_extra=extra)
        args[args.index("--approval") + 1] = record
        return self.execute(args)

    def test_an_unknown_approved_key_refuses_a_pipeline_record_before_any_cloud_call(self):
        for line in ("APPROVED_UNKNOWN_KEY=1\n", "APPROVED_COMMITT=%s\n" % ("a" * 40), "  APPROVED_REGIONN = us-east-2\n", "APPROVED_lower=1\n"):
            with self.subTest(line):
                open(self.log, "w").close()
                result = self.run_with_extra(line)
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn("step=approval-record", result.result_line())
                self.assertIn("unknown key APPROVED_", result.out)
                self.assertEqual(self.calls(), [])
                self.assertEqual(self.submitted_steps(), [])

    def test_text_that_is_not_an_approved_line_stays_ignored(self):
        result = self.run_with_extra("Notes: APPROVED_UNKNOWN_KEY=1 is only mentioned here.\n# APPROVED_OTHER=2 in a comment\n")
        self.assertEqual(result.rc, 0, result.out)

    def test_the_parser_refuses_an_unknown_key_for_both_actions(self):
        keys = {
            "run-bounded-pipeline": ["APPROVED_ACTION", "APPROVED_COMMIT", "APPROVED_ACCOUNT_SHA256", "APPROVED_REGION", "APPROVED_CLUSTER_ID", "APPROVED_RUN_CONFIG_SHA256", "APPROVED_BUDGET_USD", "APPROVED_MAX_CAPACITY", "APPROVED_MAX_RUNTIME_MINUTES", "APPROVED_TEARDOWN", "APPROVED_PRESPEND_SHA256"],
        }
        keys["run-experiment"] = keys["run-bounded-pipeline"] + ["APPROVED_MANIFEST_SHA256"]
        good = {"APPROVED_ACTION": None, "APPROVED_COMMIT": "a" * 40, "APPROVED_ACCOUNT_SHA256": "b" * 64, "APPROVED_REGION": "us-east-2", "APPROVED_CLUSTER_ID": "j-ABC123DEF456", "APPROVED_RUN_CONFIG_SHA256": "c" * 64,
                "APPROVED_BUDGET_USD": "2.5", "APPROVED_MAX_CAPACITY": "3", "APPROVED_MAX_RUNTIME_MINUTES": "90", "APPROVED_TEARDOWN": "auto-termination", "APPROVED_PRESPEND_SHA256": "d" * 64, "APPROVED_MANIFEST_SHA256": "e" * 64}
        for action, required in keys.items():
            path = os.path.join(self.tmp, "rec-%s.md" % action)
            lines = ["%s=%s" % (k, action if k == "APPROVED_ACTION" else good[k]) for k in required]
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")
            ok = subprocess.run([sys.executable, "-I", APPROVAL_LIB, "parse", "--file", path, "--action", action], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write("APPROVED_UNKNOWN_KEY=1\n")
            bad = subprocess.run([sys.executable, "-I", APPROVAL_LIB, "parse", "--file", path, "--action", action], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("APPROVAL-REFUSED: approval record has an unknown key APPROVED_UNKNOWN_KEY", bad.stdout)

    def test_the_experiment_record_with_an_unknown_key_is_refused_too(self):
        # the delegated pipeline parses the experiment record with the same parser
        path = os.path.join(self.tmp, "exp.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("APPROVED_ACTION=run-experiment\nAPPROVED_TYPO=1\n")
        bad = subprocess.run([sys.executable, "-I", APPROVAL_LIB, "parse", "--file", path, "--action", "run-experiment"], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("unknown key APPROVED_TYPO", bad.stdout)


class DeployUnknownApprovalKeyTests(unittest.TestCase):
    def test_the_deploy_record_parser_documents_and_enforces_the_same_rule(self):
        with open(os.path.join(SCRIPTS_DIR, "deploy.sh"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("any extra APPROVED_* key refuses", text)
        with open(os.path.join(SCRIPTS_DIR, "README.md"), encoding="utf-8") as handle:
            self.assertIn("an unknown `APPROVED_*` key (for example a misspelt one) refuses", handle.read())


class GenericRedactionArchiveTests(ArchiveBase):
    def archived(self, text, name="log.txt"):
        self.put(name, text)
        result = self.archive()
        self.assertEqual(result.rc, 0, result.out)
        with open(os.path.join(self.dest(), "test-reports", name), encoding="utf-8") as handle:
            return handle.read(), result

    def test_generic_assignments_are_redacted_in_every_form(self):
        pw = "pass" + "word"
        text = (
            "api_token = tok_live_51Hq0AbCdEfGh\n"
            "client_secret: s3cr3t-value-0042\n"
            "db %s=hunter2hunter2\n" % pw
            + "api_key: abc123XYZ-key-value\n"
            + 'json {"secret": "zzz-yyy-0001", "%s":"p4ssw0rd-x"}\n' % pw
            + "export SERVICE_API_KEY='single-quoted-value'\n"
            + "credential=cred-value-77\n"
            + "private_key: pk-value-88\n"
        )
        archived, _ = self.archived(text)
        for value in ("tok_live_51Hq0AbCdEfGh", "s3cr3t-value-0042", "hunter2hunter2", "abc123XYZ-key-value", "zzz-yyy-0001", "p4ssw0rd-x", "single-quoted-value", "cred-value-77", "pk-value-88"):
            self.assertNotIn(value, archived)
        self.assertIn('"secret": "<redacted>"', archived)
        self.assertIn("api_token = <redacted>", archived)
        self.assertIn("SERVICE_API_KEY='<redacted>'", archived)

    def test_checksums_numbers_booleans_and_harmless_words_stay_intact(self):
        digest = "f" * 64
        text = (
            "sha256: %s\n" % digest
            + "secret_sha256=%s\n" % digest
            + "max_tokens: 4096\n"
            + "token_count = 12\n"
            + "use_password: false\n"
            + "the password policy is documented; the secrets manager holds tokens\n"
            + "token budget and key figures\n"
            + "checksum %s keeps\n" % digest
        )
        archived, _ = self.archived(text)
        self.assertEqual(archived, text)

    def test_the_post_write_verification_flags_a_remaining_assignment(self):
        self.put("log.txt", "plain\n")
        done = subprocess.run(["bash", os.path.join(SCRIPTS_DIR, "archive-evidence.sh"), "--phase", "13", "--label", "v7", "--dest-root", self.dest_root, "--include", "test-reports=" + os.path.join(self.src, "reports")], capture_output=True, text=True, env=self.env())
        self.assertEqual(done.returncode, 0)
        target = os.path.join(self.dest("v7"), "test-reports", "log.txt")
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("api_key: left-behind-value\n")
        verify = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS_DIR, "lib", "archive.py"), "verify", "--dest", self.dest("v7")], capture_output=True, text=True)
        self.assertEqual(verify.returncode, 1)
        self.assertIn("still holds a secret, token, password or api-key assignment", verify.stdout)

    def test_redaction_is_linear_on_a_megabyte_of_one_character_or_one_keyword(self):
        import importlib.util
        import time

        spec = importlib.util.spec_from_file_location("sc_archive", os.path.join(SCRIPTS_DIR, "lib", "archive.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for text in ("a" * 1048576, "secret" * 174762, "a_secret_" * 116508, "-" * 1048576, "token=" * 174762):
            started = time.monotonic()
            redacted, _count = module.redact_text(text, [])
            module.generic_remaining(redacted)
            self.assertLess(time.monotonic() - started, 5.0, "catastrophic backtracking on a %d byte input" % len(text))

    def test_the_index_records_the_original_hash_and_counts_the_redactions(self):
        text = "client_secret: abcdefgh1234\n"
        self.archived(text)
        entry = self.entry("test-reports/log.txt")
        self.assertEqual(entry["sha256"], sha256_bytes(text.encode()))
        self.assertEqual(entry["redactions"], 1)
        self.assertNotEqual(entry["archived_sha256"], entry["sha256"])


class ApiKeyRedactionTests(PipelineFixture):
    CANARY = "CANARY-api-key-value-7788"

    def failing_sts(self, **env):
        args = self.ready()
        return self.execute(args, FAKE_STS_RC="1", FAKE_EMIT="boom echoed %s" % self.CANARY, **env)

    def test_an_api_key_named_variable_is_redacted_from_shown_command_output(self):
        for name in ("SCHOLARCHAIN_SMOKE_API_KEY", "MY_SERVICE_KEY", "VENDOR_API_KEY_V2"):
            with self.subTest(name):
                result = self.failing_sts(**{name: self.CANARY})
                self.assertNotEqual(result.rc, 0)
                self.assertIn("boom echoed", result.out, "the failing command's output is shown")
                self.assertNotIn(self.CANARY, result.out)
                self.assertIn("<redacted>", result.out)

    def test_a_harmless_variable_name_is_not_redacted_so_the_test_is_sensitive(self):
        result = self.failing_sts(SOME_HARMLESS_NOTE=self.CANARY)
        self.assertIn(self.CANARY, result.out)

    def test_redact_py_and_common_sh_agree_on_the_rule(self):
        env = dict(os.environ, SCHOLARCHAIN_SMOKE_API_KEY=self.CANARY, OTHER_KEY="plain-key-value-1", NOTKEYED="visible-value-2")
        done = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS_DIR, "lib", "redact.py")], input="a %s b plain-key-value-1 c visible-value-2\n" % self.CANARY, capture_output=True, text=True, env=env)
        self.assertEqual(done.stdout, "a <redacted> b <redacted> c visible-value-2\n")
        shell = subprocess.run(
            ["bash", "-c", 'source "%s/lib/common.sh"; sc_redact "x $SCHOLARCHAIN_SMOKE_API_KEY y $OTHER_KEY z $NOTKEYED"' % SCRIPTS_DIR],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(shell.stdout, "x <redacted> y <redacted> z visible-value-2")

    def test_every_script_family_hides_the_smoke_key_variable(self):
        # a usage error echoes its message through sc_redact; the pipeline above covers the cloud output path
        result = self.run_script("run-bounded-pipeline.sh", "--bogus-%s" % self.CANARY, SCHOLARCHAIN_SMOKE_API_KEY=self.CANARY)
        self.assertEqual(result.rc, 2)
        self.assertNotIn(self.CANARY, result.out)


if __name__ == "__main__":
    unittest.main()

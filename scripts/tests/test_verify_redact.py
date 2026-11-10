"""Direct tests of scripts/lib/redact.py and scripts/lib/verify.py (hand-derived inputs and expectations)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPTS_DIR

REDACT = os.path.join(SCRIPTS_DIR, "lib", "redact.py")
VERIFY = os.path.join(SCRIPTS_DIR, "lib", "verify.py")


def run(script, args, stdin=None, env=None):
    return subprocess.run([sys.executable, "-I", script] + args, input=stdin, capture_output=True, text=True, env=env, timeout=60)


class RedactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as handle:
            handle.write(text)
        return path

    def test_private_values_extraction_keeps_long_strings_and_skips_bare_account_ids_and_short_ones(self):
        path = self.write(
            "p.tfvars",
            'aws_account_id = "123456789012"\nowner = "alice@example.invalid"\nname = "ab"\nzones = ["us-east-2a", "us-east-2b"]\nflag = true\n',
        )
        result = run(REDACT, ["--extract-private-vars", path])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(), ["alice@example.invalid", "us-east-2a", "us-east-2b"])

    def test_redaction_of_registered_env_and_account_values(self):
        values = self.write("values", "S\tREGISTERED-VALUE-77\nA\t999988887777\n")
        env = dict(os.environ, MY_PASSWORD="hunter2-password-value", PLAIN_SETTING="not-a-secret-value")
        text = "a REGISTERED-VALUE-77 b hunter2-password-value c 999988887777 d 123456789012.dkr.ecr e not-a-secret-value f " + "a" * 8 + "123456789012" + "b" * 8
        result = run(REDACT, ["--values-file", values], stdin=text, env=env)
        self.assertEqual(
            result.stdout,
            "a <redacted> b <redacted> c <acct> d <acct>.dkr.ecr e not-a-secret-value f aaaaaaaa123456789012bbbbbbbb",
        )

    def test_a_longer_registered_value_is_replaced_whole(self):
        values = self.write("values", "S\tsecret-prefix\nS\tsecret-prefix-and-more\n")
        result = run(REDACT, ["--values-file", values], stdin="x secret-prefix-and-more y")
        self.assertEqual(result.stdout, "x <redacted> y")

    def test_missing_values_file_still_redacts_account_ids(self):
        result = run(REDACT, ["--values-file", os.path.join(self.tmp.name, "absent")], stdin="id 123456789012!")
        self.assertEqual(result.stdout, "id <acct>!")


class GitTreeTests(unittest.TestCase):
    """verify.py git-tree: exact path comparison on parsed porcelain -z output."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        self.git("init", "-q")
        self.put("tracked.txt", "a\n")
        self.put("docs/record.md", "record\n")
        self.git("add", "-A")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x")

    def git(self, *args):
        subprocess.run(["git", "-C", self.repo] + list(args), check=True, capture_output=True)

    def put(self, rel, text):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text)

    def state(self, exempt="docs/record.md"):
        result = run(VERIFY, ["git-tree", "--repo", self.repo, "--exempt", exempt])
        return result.returncode, result.stdout.strip()

    def test_clean_and_exact_exemption(self):
        self.assertEqual(self.state(), (0, "clean"))
        self.put("docs/record.md", "modified record\n")
        self.assertEqual(self.state()[0], 0, "the exempt path alone may differ")
        self.put("docs/record.md.bak", "x\n")
        self.assertEqual(self.state()[0], 1, "a sibling that merely starts with the exempt path is dirty")

    def test_metacharacter_names_are_ordinary_paths(self):
        for name in ("*", "docs/*", ":(exclude)tracked.txt", "docs/rec?rd.md"):
            with self.subTest(name):
                self.put(name, "x\n")
                code, text = self.state()
                self.assertEqual(code, 1, text)
                os.remove(os.path.join(self.repo, name))

    def test_rename_involving_the_exempt_path_is_dirty(self):
        self.git("mv", "docs/record.md", "docs/renamed.md")
        self.assertEqual(self.state()[0], 1)

    def test_not_a_repository_is_an_error_not_clean(self):
        with tempfile.TemporaryDirectory() as empty:
            result = run(VERIFY, ["git-tree", "--repo", empty, "--exempt", "x"])
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("clean", result.stdout)


class ClassificationTests(unittest.TestCase):
    RULES = [
        "--preserve-types", "aws_s3_bucket,aws_kms_,aws_cloudwatch_log_group",
        "--preserve-addresses", "module.foundation.,module.datalake.",
        "--teardown-addresses", "module.runtime.,module.network.,module.identity.aws_iam_role.task",
    ]

    def classify(self, addresses):
        with tempfile.TemporaryDirectory() as tmp:
            state = os.path.join(tmp, "state")
            targets = os.path.join(tmp, "targets")
            with open(state, "w") as handle:
                handle.write("\n".join(addresses) + "\n")
            result = run(VERIFY, ["classify-state", "--state-file", state, "--targets-out", targets] + self.RULES)
            with open(targets) as handle:
                return result.stdout.splitlines(), handle.read().splitlines()

    def test_preserve_wins_and_index_is_stripped_for_matching_and_targeting(self):
        lines, targets = self.classify(
            [
                'module.runtime.aws_ecs_service.service["a.b"]',
                'module.runtime.aws_cloudwatch_log_group.extra',  # type rule beats the teardown prefix
                "module.identity.aws_iam_role.task[\"query-api\"]",
                "module.identity.aws_iam_role.deployment",  # an exact rule does not cover a sibling name
                "module.identity.aws_iam_role.task_other",
                "data.aws_caller_identity.current",
                "module.foundation.aws_dynamodb_table.lock",
                "aws_instance.rogue",
            ]
        )
        self.assertEqual(targets, ["module.identity.aws_iam_role.task", "module.runtime.aws_ecs_service.service"])
        joined = "\n".join(lines)
        self.assertIn("PRESERVE module.runtime.aws_cloudwatch_log_group.extra (type aws_cloudwatch_log_group)", joined)
        self.assertIn("PRESERVE module.foundation.aws_dynamodb_table.lock (address module.foundation.)", joined)
        self.assertIn("NOT-TARGETED module.identity.aws_iam_role.deployment", joined)
        self.assertIn("NOT-TARGETED module.identity.aws_iam_role.task_other", joined)
        self.assertIn("NOT-TARGETED aws_instance.rogue", joined)
        self.assertNotIn("data.aws_caller_identity", joined, "data sources are ignored")


class PrespendBoundaryTests(unittest.TestCase):
    def check(self, document, text=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            with open(path, "w") as handle:
                handle.write(text if text is not None else json.dumps(document))
            result = run(VERIFY, ["prespend", "--file", path, "--max-age-hours", "24", "--min-headroom", "20"])
            return result.returncode, result.stdout

    def base(self, **overrides):
        import datetime

        stamp = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        doc = {"monitoring_confirmed_active": True, "cost_snapshot_utc": stamp, "reported_spend_usd": 0, "unreported_usage_allowance_usd": 0, "reserves_usd": 0, "remaining_headroom_usd": 20}
        doc.update(overrides)
        return doc

    def test_zero_is_a_legitimate_value_but_missing_is_not(self):
        self.assertEqual(self.check(self.base())[0], 0, "explicit zeros and exactly 20 USD of headroom pass")
        doc = self.base()
        del doc["reported_spend_usd"]
        code, text = self.check(doc)
        self.assertEqual(code, 1)
        self.assertIn("reported_spend_usd is missing or not a number", text)

    def test_future_snapshot_and_malformed_timestamp_are_refused(self):
        self.assertEqual(self.check(self.base(cost_snapshot_utc="2999-01-01T00:00:00Z"))[0], 1)
        self.assertEqual(self.check(self.base(cost_snapshot_utc="yesterday"))[0], 1)

    def test_nan_literal_is_refused(self):
        text = json.dumps(self.base()).replace('"reserves_usd": 0', '"reserves_usd": NaN')
        self.assertEqual(self.check(None, text=text)[0], 1)

    # ---- 14B repair round 2 (B2): the floor is either --min-headroom D or --no-headroom-floor, never both or neither ----
    def run_flags(self, document, flags, text=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            with open(path, "w") as handle:
                handle.write(text if text is not None else json.dumps(document))
            result = run(VERIFY, ["prespend", "--file", path, "--max-age-hours", "24"] + flags)
            return result.returncode, result.stdout + result.stderr

    def test_spending_floor_2_99_is_refused_and_3_00_is_accepted(self):
        self.assertEqual(self.run_flags(self.base(remaining_headroom_usd=2.99), ["--min-headroom", "3"])[0], 1)
        self.assertEqual(self.run_flags(self.base(remaining_headroom_usd=3.00), ["--min-headroom", "3"])[0], 0)

    def test_no_headroom_floor_accepts_negative_headroom_and_says_so(self):
        for headroom in (-5.00, -0.01, 0, 1, 150.25):
            with self.subTest(headroom=headroom):
                code, text = self.run_flags(self.base(remaining_headroom_usd=headroom), ["--no-headroom-floor"])
                self.assertEqual(code, 0, text)
                self.assertIn("PRESPEND: cleanup-prepare has no headroom floor (remaining_headroom_usd=%.2f)" % headroom, text)

    def test_no_headroom_floor_still_requires_a_finite_numeric_headroom_and_every_other_check(self):
        for label, overrides in {
            "string": {"remaining_headroom_usd": "-5.00"},
            "null": {"remaining_headroom_usd": None},
            "boolean": {"remaining_headroom_usd": True},
            "stale": {"cost_snapshot_utc": "2000-01-01T00:00:00Z"},
            "future": {"cost_snapshot_utc": "2999-01-01T00:00:00Z"},
            "monitoring false": {"monitoring_confirmed_active": False},
            "reserves string": {"reserves_usd": "0"},
        }.items():
            with self.subTest(label):
                self.assertEqual(self.run_flags(self.base(**overrides), ["--no-headroom-floor"])[0], 1)
        for label, key in (("missing", "remaining_headroom_usd"), ("missing spend", "reported_spend_usd")):
            with self.subTest(label):
                doc = self.base()
                del doc[key]
                self.assertEqual(self.run_flags(doc, ["--no-headroom-floor"])[0], 1)
        for literal in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(literal):
                text = json.dumps(self.base()).replace('"remaining_headroom_usd": 20', '"remaining_headroom_usd": ' + literal)
                self.assertEqual(self.run_flags(None, ["--no-headroom-floor"], text=text)[0], 1)

    def test_giving_both_or_neither_headroom_flag_is_a_usage_error(self):
        document = self.base(remaining_headroom_usd=100)
        for flags in (["--min-headroom", "3", "--no-headroom-floor"], []):
            with self.subTest(flags=flags):
                code, text = self.run_flags(document, flags)
                self.assertEqual(code, 2, text)
                self.assertNotIn("pre-spend receipt ok", text)


if __name__ == "__main__":
    unittest.main()

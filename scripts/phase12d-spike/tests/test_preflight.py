import os
import unittest

from helpers import SCRIPTS_DIR, ShimTestCase

SCRIPT = os.path.join(SCRIPTS_DIR, "preflight.sh")
ACCT = "111122223333"


class PreflightTests(ShimTestCase):
    def identity(self, arn, account=ACCT):
        self.put("sts.txt", f"{arn}\t{account}\n")

    def run_pf(self, region="us-east-2", **kw):
        env = {"AWS_REGION": region} if region else {}
        return self.run_script(SCRIPT, ["--account", ACCT, "--role", "scholarchain-deployer"], **env, **kw)

    def test_accepts_expected_identity(self):
        self.identity(f"arn:aws:sts::{ACCT}:assumed-role/scholarchain-deployer/session1")
        r = self.run_pf()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("PREFLIGHT OK", r.stdout)
        self.assertIn(f"Account={ACCT}", r.stdout)

    def test_refuses_wrong_account(self):
        self.identity("arn:aws:sts::999999999999:assumed-role/scholarchain-deployer/s", "999999999999")
        r = self.run_pf()
        self.assertEqual(r.returncode, 1)
        self.assertIn("account", r.stderr)

    def test_refuses_wrong_role(self):
        self.identity(f"arn:aws:sts::{ACCT}:assumed-role/scholarchain-billing-deployer/s")
        r = self.run_pf()
        self.assertEqual(r.returncode, 1)
        self.assertIn("not an assumed-role session of scholarchain-deployer", r.stderr)

    def test_refuses_plain_user(self):
        self.identity(f"arn:aws:iam::{ACCT}:user/someone")
        r = self.run_pf()
        self.assertEqual(r.returncode, 1)

    def test_refuses_wrong_region(self):
        self.identity(f"arn:aws:sts::{ACCT}:assumed-role/scholarchain-deployer/s")
        r = self.run_pf(region="us-west-2")
        self.assertEqual(r.returncode, 1)
        self.assertIn("region", r.stderr)

    def test_refuses_unset_region(self):
        self.identity(f"arn:aws:sts::{ACCT}:assumed-role/scholarchain-deployer/s")
        r = self.run_pf(region="")
        self.assertEqual(r.returncode, 1)

    def test_fails_when_identity_call_fails(self):
        # no sts.txt -> fake aws exits 255
        r = self.run_pf()
        self.assertEqual(r.returncode, 1)

    def test_prints_nothing_but_arn_account_region(self):
        self.identity(f"arn:aws:sts::{ACCT}:assumed-role/scholarchain-deployer/s")
        r = self.run_pf()
        for line in r.stdout.strip().splitlines():
            self.assertTrue(line.split("=")[0] in ("Arn", "Account", "Region") or line == "PREFLIGHT OK", line)

    def test_makes_exactly_one_aws_call_when_region_in_env(self):
        self.identity(f"arn:aws:sts::{ACCT}:assumed-role/scholarchain-deployer/s")
        self.run_pf()
        with open(self.aws_log) as handle:
            calls = [l for l in handle if l.strip()]
        self.assertEqual(len(calls), 1)
        self.assertIn("sts get-caller-identity", calls[0])

    def test_bad_usage(self):
        r = self.run_script(SCRIPT, ["--account", "123"])
        self.assertEqual(r.returncode, 64)


if __name__ == "__main__":
    unittest.main()

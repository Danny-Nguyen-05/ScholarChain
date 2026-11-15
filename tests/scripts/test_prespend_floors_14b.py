"""Phase 14B replan, repair round 2: the pre-spend headroom rules of scripts/deploy.sh (test-engineer, independent).

Requirement (user decisions): the receipt's remaining headroom must be at least USD 3 for every stage that can spend
(base-apply, push, runtime-apply; 2.99 is refused, 3.00 is accepted). The teardown-only stage `cleanup-prepare` has NO headroom floor:
the user's words are "cleanup-prepare has no headroom floor, so negative headroom is accepted. The receipt must still exist, match
its hash, be fresh, confirm monitoring and carry every numeric field. Cleanup must never be blocked by overspend." So for
cleanup-prepare a headroom of -5.00, -0.01 or 0 is accepted and the stage prints
`PRESPEND: cleanup-prepare has no headroom floor (remaining_headroom_usd=<2 decimals>)`, while a missing, null, string, NaN or
infinite headroom, a stale or future snapshot, monitoring that is not true, a hash mismatch and a missing receipt are all still
refused. The old separate cleanup floor setting no longer exists (not in release.conf, not in the pinned keys), and setting it in
the environment changes nothing. `--no-headroom-floor` exists only in scripts/deploy.sh and scripts/lib/verify.py, and deploy.sh
passes it only under a `cleanup-prepare` stage condition.

Written from that requirement, not from scripts/tests/test_deploy.py. It drives the real scripts/deploy.sh (a copy in a scratch
git repository) with the fake terraform/aws/docker binaries of sc_support, in dry-run mode, through the `prespend-receipt`
step. Everything after that step needs a real plan and receipt, which this module deliberately does not build: a stage that
PASSES the pre-spend step is recognised by the run getting past it (last STEP is not `prespend-receipt` and no pre-spend
refusal text), a refused one by rc 3, status REFUSED and last STEP `prespend-receipt`. No cloud call is made.
"""
import datetime
import re
import subprocess
import sys
import unittest

import sc_support as S

STAGES = ("base-apply", "push", "runtime-apply", "cleanup-prepare")
SPENDING = ("base-apply", "push", "runtime-apply")
ZERO = "0" * 64
FLOOR_REFUSAL = re.compile(r"below the required ([0-9.]+) USD")
OLD_KEY = "PRESPEND_MIN_HEADROOM_" + "CLEANUP_USD"  # the removed setting; spelled in two pieces so a plain search for it finds only real uses


def no_floor_line(two_decimals):
    return "PRESPEND: cleanup-prepare has no headroom floor (remaining_headroom_usd=%s)" % two_decimals


class FloorBase(unittest.TestCase):
    def setUp(self):
        self.fx = S.Fixture(self, infra=True)

    def receipt(self, **mods):
        return self.fx.write_prespend(**mods)

    def deploy(self, stage, prespend, extra_env=None, approved_sha=None):
        """Dry-run deploy.sh for `stage` with an approval record that names the receipt's hash; returns the Run."""
        fx = self.fx
        values = [
            ("APPROVED_STAGE", stage), ("APPROVED_COMMIT", fx.head()), ("APPROVED_ACCOUNT_SHA256", fx.account_hash()),
            ("APPROVED_REGION", "us-east-2"), ("APPROVED_ENVIRONMENT", "course"),
            ("APPROVED_PRESPEND_SHA256", approved_sha or S.sha256_file(prespend)),
        ]
        args = ["--stage", stage, "--region", "us-east-2"]
        if stage != "push":
            values += [("APPROVED_PLAN_SHA256", ZERO), ("APPROVED_RECEIPT_SHA256", ZERO)]
            args += ["--plan", str(fx.aux / "no-such-plan.bin")]
        approval = fx.aux / ("approval-%s.md" % stage)
        approval.write_text("\n".join("%s=%s" % kv for kv in values) + "\n")
        args += ["--approval", str(approval), "--prespend", str(prespend)]
        return fx.run("deploy.sh", args, extra_env)

    def assert_floor_refusal(self, run, floor):
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertEqual(S.last_step(run), "prespend-receipt", run.describe())
        found = [float(f) for f in FLOOR_REFUSAL.findall(run.text)]
        self.assertTrue(found, "the refusal must state the required floor\n" + run.describe())
        self.assertEqual(set(found), {floor}, run.describe())
        self.assertEqual(run.tool_calls("aws") + run.tool_calls("docker"), [], "no cloud call may precede a refused receipt")

    def assert_refused_at_prespend(self, run):
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertEqual(S.last_step(run), "prespend-receipt", run.describe())
        self.assertNotIn("pre-spend receipt ok", run.text, run.describe())
        self.assertEqual(run.tool_calls("aws") + run.tool_calls("docker"), [], "no cloud call may precede a refused receipt")

    def assert_past_prespend(self, run):
        """The pre-spend step passed: no floor refusal, and the run went on to a later step (it then stops on the missing plan)."""
        self.assertNotRegex(run.text, FLOOR_REFUSAL, run.describe())
        self.assertIn("prespend-receipt", run.steps(), run.describe())
        self.assertNotEqual(S.last_step(run), "prespend-receipt", run.describe())
        self.assertEqual(run.tool_calls("aws") + run.tool_calls("docker"), [])

    def set_config(self, **overrides):
        """Rewrite KEY=value lines of the fixture repository's release.conf and commit the change."""
        conf = self.fx.repo / "scripts/config/release.conf"
        text = conf.read_text()
        for key, value in overrides.items():
            changed = re.sub(r"^%s=.*$" % key, "%s=%s" % (key, value), text, flags=re.M)
            self.assertNotEqual(changed, text, "%s is not a line of release.conf" % key)
            text = changed
        conf.write_text(text)
        self.fx.git("add", "-A")
        self.fx.git("commit", "-q", "-m", "config change")


class StageListIsAsExpected(FloorBase):
    def test_deploy_accepts_exactly_the_four_stages_this_module_covers(self):
        usage = (S.REPO / "scripts/deploy.sh").read_text()
        listed = re.search(r"--stage STAGE\s+required: ([a-z-]+(?: \| [a-z-]+)*)", usage)
        self.assertIsNotNone(listed, "deploy.sh help no longer lists the stages in the expected form")
        self.assertEqual(tuple(listed.group(1).split(" | ")), ("base-apply", "push", "runtime-apply", "cleanup-prepare"))
        self.assertEqual(set(STAGES), set(listed.group(1).split(" | ")))

    def test_an_unknown_stage_is_a_usage_error_and_never_reaches_the_receipt(self):
        receipt = self.receipt(remaining_headroom_usd=-5)
        run = self.fx.run("deploy.sh", ["--stage", "cleanup", "--region", "us-east-2", "--prespend", str(receipt)])
        self.assertNotEqual(run.rc, 0, run.describe())
        self.assertNotIn("prespend-receipt", run.steps(), run.describe())


class SpendingStagesKeepTheThreeDollarFloor(FloorBase):
    def test_headroom_below_three_is_refused_by_every_spending_stage(self):
        for stage in SPENDING:
            for headroom in (2.99, 1, 0, -0.01):
                with self.subTest(stage=stage, headroom=headroom):
                    self.assert_floor_refusal(self.deploy(stage, self.receipt(remaining_headroom_usd=headroom)), 3.0)

    def test_headroom_of_exactly_three_and_above_passes_the_prespend_step(self):
        for stage in SPENDING:
            for headroom in (3, 3.0, 3.00, 3.01, 19.99, 20.25):
                with self.subTest(stage=stage, headroom=headroom):
                    self.assert_past_prespend(self.deploy(stage, self.receipt(remaining_headroom_usd=headroom)))

    def test_headroom_above_the_ceiling_arithmetic_is_refused_by_every_spending_stage(self):
        """Repair round 3, hand-derived: the default receipt states AWS 1.5, Anthropic 0.25, Voyage 0.0, allowance 1.0, reserves 2.0, so the
        most it may state is 25 - 1.75 - 1.0 - 2.0 = 20.25 (a cent of tolerance: 20.26 passes, 20.27 and 150.25 do not)."""
        for stage in SPENDING:
            with self.subTest(stage=stage, headroom=20.26):
                self.assert_past_prespend(self.deploy(stage, self.receipt(remaining_headroom_usd=20.26)))
            for headroom in (20.27, 21, 150.25):
                with self.subTest(stage=stage, headroom=headroom):
                    run = self.deploy(stage, self.receipt(remaining_headroom_usd=headroom))
                    self.assert_refused_at_prespend(run)
                    self.assertIn("exceeds the ceiling arithmetic", run.text, run.describe())

    def test_a_provider_left_out_of_the_headroom_is_refused(self):
        """A receipt that reports Anthropic spend 5 but keeps the old headroom (20.25) leaves a provider out: 25 - (1.5 + 5) - 3 = 15.5."""
        for stage in SPENDING:
            with self.subTest(stage=stage):
                run = self.deploy(stage, self.receipt(anthropic_spend_to_date_usd=5.0, remaining_headroom_usd=20.25))
                self.assert_refused_at_prespend(run)
                run = self.deploy(stage, self.receipt(anthropic_spend_to_date_usd=5.0, remaining_headroom_usd=15.5))
                self.assert_past_prespend(run)
                run = self.deploy(stage, self.receipt(voyage_spend_to_date_usd=5.0, remaining_headroom_usd=20.25))
                self.assert_refused_at_prespend(run)

    def test_a_spending_stage_never_prints_the_no_floor_line(self):
        for stage in SPENDING:
            with self.subTest(stage=stage):
                run = self.deploy(stage, self.receipt(remaining_headroom_usd=3.5))
                self.assertNotIn("has no headroom floor", run.text, run.describe())


class CleanupPrepareHasNoHeadroomFloor(FloorBase):
    def test_negative_zero_and_positive_headroom_are_accepted_and_the_no_floor_line_is_printed(self):
        # hand-derived: the line carries the receipt value with two decimals
        for headroom, shown in ((-5.00, "-5.00"), (-5, "-5.00"), (-0.01, "-0.01"), (0, "0.00"), (0.0, "0.00"), (1, "1.00"),
                                (150.25, "150.25"), (-123.456, "-123.46")):
            with self.subTest(headroom=headroom):
                run = self.deploy("cleanup-prepare", self.receipt(remaining_headroom_usd=headroom))
                self.assert_past_prespend(run)
                self.assertIn(no_floor_line(shown), run.text, run.describe())

    def test_the_same_negative_receipt_is_refused_by_every_spending_stage(self):
        receipt = self.receipt(remaining_headroom_usd=-5)
        self.assert_past_prespend(self.deploy("cleanup-prepare", receipt))
        for stage in SPENDING:
            with self.subTest(stage=stage):
                self.assert_floor_refusal(self.deploy(stage, receipt), 3.0)

    def test_headroom_that_is_not_a_finite_number_is_still_refused(self):
        cases = {
            "missing": ..., "null": None, "string": "1", "string negative": "-5", "NaN": float("nan"),
            "Infinity": float("inf"), "-Infinity": float("-inf"), "true": True, "list": [1], "object": {"v": 1},
        }
        for label, value in cases.items():
            with self.subTest(headroom=label):
                run = self.deploy("cleanup-prepare", self.receipt(remaining_headroom_usd=value))
                self.assert_refused_at_prespend(run)
                self.assertNotIn("has no headroom floor", run.text, "the no-floor line is printed only for a usable headroom value")

    def test_every_other_numeric_field_must_still_be_a_finite_number(self):
        for key in ("reported_spend_usd", "anthropic_spend_to_date_usd", "voyage_spend_to_date_usd", "unreported_usage_allowance_usd", "reserves_usd"):
            for label, value in (("missing", ...), ("null", None), ("string", "1"), ("NaN", float("nan")), ("Infinity", float("inf"))):
                with self.subTest(field=key, value=label):
                    run = self.deploy("cleanup-prepare", self.receipt(remaining_headroom_usd=-5, **{key: value}))
                    self.assert_refused_at_prespend(run)

    def test_a_stale_or_future_snapshot_or_unconfirmed_monitoring_is_still_refused(self):
        now = S.now_utc()
        cases = {
            "stale 25h": dict(snapshot_dt=now - datetime.timedelta(hours=25)),
            "stale 3 days": dict(snapshot_dt=now - datetime.timedelta(days=3)),
            "future 2h": dict(snapshot_dt=now + datetime.timedelta(hours=2)),
            "monitoring false": dict(monitoring_confirmed_active=False),
            "monitoring string": dict(monitoring_confirmed_active="true"),
            "monitoring missing": dict(monitoring_confirmed_active=...),
            "snapshot missing": dict(cost_snapshot_utc=...),
        }
        for label, mods in cases.items():
            for headroom in (-5, 100):
                with self.subTest(case=label, headroom=headroom):
                    run = self.deploy("cleanup-prepare", self.receipt(**dict(dict(remaining_headroom_usd=headroom), **mods)))
                    self.assert_refused_at_prespend(run)

    def test_a_fresh_snapshot_just_inside_the_age_limit_is_accepted_with_negative_headroom(self):
        run = self.deploy("cleanup-prepare", self.receipt(remaining_headroom_usd=-5, snapshot_dt=S.now_utc() - datetime.timedelta(hours=23)))
        self.assert_past_prespend(run)

    def test_a_receipt_that_does_not_match_the_approval_hash_is_refused_even_with_negative_headroom(self):
        receipt = self.receipt(remaining_headroom_usd=-5)
        approved = S.sha256_file(receipt)
        receipt.write_text(receipt.read_text().replace('"remaining_headroom_usd": -5', '"remaining_headroom_usd": -6'))
        self.assertNotEqual(approved, S.sha256_file(receipt))
        run = self.deploy("cleanup-prepare", receipt, approved_sha=approved)
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertIn("sha256", run.text, run.describe())
        self.assertNotIn("has no headroom floor", run.text, run.describe())
        self.assertEqual(run.tool_calls("aws") + run.tool_calls("docker"), [])

    def test_a_missing_receipt_is_refused(self):
        run = self.deploy("cleanup-prepare", self.fx.aux / "no-such-receipt.json", approved_sha="a" * 64)
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertIn("pre-spend receipt not found", run.text, run.describe())
        self.assertNotIn("has no headroom floor", run.text, run.describe())

    def test_a_receipt_that_is_not_json_or_not_an_object_is_refused(self):
        for label, text in (("not json", "headroom=-5\n"), ("array", "[-5]\n"), ("empty", "")):
            with self.subTest(case=label):
                path = self.fx.write(self.fx.aux / "bad.json", text)
                self.assert_refused_at_prespend(self.deploy("cleanup-prepare", path))


class VerifyPrespendFlags(FloorBase):
    """scripts/lib/verify.py prespend needs exactly one of --min-headroom D or --no-headroom-floor (checked on the real script)."""

    def verify(self, receipt, *flags):
        done = subprocess.run([sys.executable, "-I", str(S.REPO / "scripts/lib/verify.py"), "prespend", "--file", str(receipt),
                               "--max-age-hours", "24"] + list(flags), capture_output=True, text=True, timeout=60)
        return done.returncode, done.stdout + done.stderr

    def test_both_flags_or_neither_is_a_usage_error(self):
        receipt = self.receipt(remaining_headroom_usd=100)
        for flags in ((), ("--min-headroom", "3", "--no-headroom-floor"), ("--no-headroom-floor", "--min-headroom", "3")):
            with self.subTest(flags=flags):
                self.assertEqual(self.verify(receipt, *flags)[0], 2)

    def test_no_floor_mode_accepts_negative_headroom_and_prints_the_line(self):
        rc, out = self.verify(self.receipt(remaining_headroom_usd=-5), "--no-headroom-floor")
        self.assertEqual(rc, 0, out)
        self.assertIn(no_floor_line("-5.00"), out)

    def test_floor_mode_refuses_below_and_accepts_at_the_floor(self):
        self.assertEqual(self.verify(self.receipt(remaining_headroom_usd=2.99), "--min-headroom", "3")[0], 1)
        self.assertEqual(self.verify(self.receipt(remaining_headroom_usd=3.0), "--min-headroom", "3")[0], 0)

    def test_no_floor_mode_still_needs_a_finite_headroom_number(self):
        for label, value in (("missing", ...), ("null", None), ("string", "-5"), ("NaN", float("nan")), ("Infinity", float("inf"))):
            with self.subTest(headroom=label):
                rc, out = self.verify(self.receipt(remaining_headroom_usd=value), "--no-headroom-floor")
                self.assertEqual(rc, 1, out)
                self.assertNotIn("has no headroom floor", out)


class TheRemovedCleanupFloorSettingIsGone(FloorBase):
    def test_the_key_is_absent_from_release_conf_and_from_the_pinned_keys(self):
        conf = (S.REPO / "scripts/config/release.conf").read_text()
        self.assertNotIn(OLD_KEY, conf)
        common = (S.REPO / "scripts/lib/common.sh").read_text()
        pinned = re.search(r'^SC_PINNED_KEYS="([^"]*)"', common, re.M).group(1).split()
        self.assertNotIn(OLD_KEY, pinned)
        self.assertNotIn(OLD_KEY, common)

    def test_the_other_pins_are_unchanged(self):
        conf = (S.REPO / "scripts/config/release.conf").read_text()
        values = dict(re.findall(r"^([A-Z_]+)=(\S+)", conf, re.M))
        self.assertEqual(float(values["PRESPEND_MIN_HEADROOM_USD"]), 3.0)
        self.assertEqual(float(values["EMR_CUMULATIVE_CAP_USD"]), 2.52)
        self.assertEqual(float(values["EMR_MAX_RUN_USD"]), 3.0)
        self.assertEqual(int(values["EMR_MAX_LIVE_RUNS"]), 3)
        common = (S.REPO / "scripts/lib/common.sh").read_text()
        pinned = re.search(r'^SC_PINNED_KEYS="([^"]*)"', common, re.M).group(1).split()
        for key in ("PRESPEND_MIN_HEADROOM_USD", "PRESPEND_MAX_AGE_HOURS", "EMR_CUMULATIVE_CAP_USD", "PRESPEND_PROJECT_CEILING_USD"):
            self.assertIn(key, pinned)
        self.assertEqual(float(values["PRESPEND_PROJECT_CEILING_USD"]), 25.0)

    def test_the_environment_cannot_raise_the_pinned_project_ceiling(self):
        for value in ("1000", "0", "abc", ""):
            for stage in SPENDING:
                with self.subTest(stage=stage, value=value):
                    run = self.deploy(stage, self.receipt(remaining_headroom_usd=150.25), {"PRESPEND_PROJECT_CEILING_USD": value})
                    self.assert_refused_at_prespend(run)
                    self.assertIn("exceeds the ceiling arithmetic", run.text, run.describe())

    def test_setting_the_old_key_in_the_environment_changes_nothing_for_any_stage(self):
        for value in ("0", "-100", "1000", "abc", ""):
            env = {OLD_KEY: value}
            for stage in SPENDING:
                with self.subTest(stage=stage, value=value, headroom=2.99):
                    self.assert_floor_refusal(self.deploy(stage, self.receipt(remaining_headroom_usd=2.99), env), 3.0)
                with self.subTest(stage=stage, value=value, headroom=3):
                    self.assert_past_prespend(self.deploy(stage, self.receipt(remaining_headroom_usd=3.00), env))
            with self.subTest(stage="cleanup-prepare", value=value, headroom=-5):
                run = self.deploy("cleanup-prepare", self.receipt(remaining_headroom_usd=-5), env)
                self.assert_past_prespend(run)
                self.assertIn(no_floor_line("-5.00"), run.text, run.describe())
            with self.subTest(stage="cleanup-prepare", value=value, headroom=1000):
                self.assert_past_prespend(self.deploy("cleanup-prepare", self.receipt(remaining_headroom_usd=1000), env))

    def test_the_old_key_inside_the_config_file_changes_nothing_either(self):
        conf = self.fx.repo / "scripts/config/release.conf"
        conf.write_text(conf.read_text() + "\n%s=100\n" % OLD_KEY)
        self.fx.git("add", "-A")
        self.fx.git("commit", "-q", "-m", "stray old key")
        self.assert_floor_refusal(self.deploy("runtime-apply", self.receipt(remaining_headroom_usd=0)), 3.0)
        self.assert_past_prespend(self.deploy("cleanup-prepare", self.receipt(remaining_headroom_usd=-5)))

    def test_environment_cannot_lower_the_spending_floor_or_pretend_a_floor_on_cleanup(self):
        receipt = self.receipt(remaining_headroom_usd=1)
        for stage in SPENDING:
            with self.subTest(stage=stage, direction="cannot relax a spending stage"):
                run = self.deploy(stage, receipt, {"PRESPEND_MIN_HEADROOM_USD": "0"})
                self.assert_floor_refusal(run, 3.0)
                self.assertIn("CONFIG-IGNORED", run.out)
        with self.subTest(direction="cannot raise cleanup-prepare"):
            run = self.deploy("cleanup-prepare", receipt, {"PRESPEND_MIN_HEADROOM_USD": "50"})
            self.assert_past_prespend(run)


class NonNumericSpendingFloorRefusesClosed(FloorBase):
    def test_a_non_numeric_floor_in_the_config_refuses_every_stage_before_the_receipt_is_looked_at(self):
        for bad in ("abc", "-1", "3usd", "1e1", "NaN"):
            fx = S.Fixture(self, infra=True)
            self.fx = fx
            self.set_config(PRESPEND_MIN_HEADROOM_USD=bad)
            for stage in STAGES:
                with self.subTest(stage=stage, value=bad):
                    run = self.deploy(stage, self.receipt(remaining_headroom_usd=100))
                    self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
                    self.assertNotIn("prespend-receipt", run.steps(), run.describe())
                    self.assertIn("must be numeric", run.text, run.describe())


class NoHeadroomFloorFlagIsConfined(unittest.TestCase):
    """Static guard on the real scripts tree: the flag exists only where the requirement puts it."""

    FLAG = "--no-headroom-floor"
    ALLOWED = {"scripts/deploy.sh", "scripts/lib/verify.py"}

    def code_files(self):
        for path in sorted((S.REPO / "scripts").rglob("*")):
            rel = path.relative_to(S.REPO).as_posix()
            if not path.is_file() or "__pycache__" in rel or path.suffix == ".pyc":
                continue
            if rel.startswith("scripts/tests/") or "/tests/" in rel or path.suffix == ".md":
                continue  # tests and prose documentation may name the flag
            yield rel, path

    def test_the_flag_appears_only_in_deploy_sh_and_verify_py(self):
        holders = set()
        for rel, path in self.code_files():
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            if self.FLAG in text:
                holders.add(rel)
        self.assertEqual(holders, self.ALLOWED)

    def test_deploy_sh_selects_the_flag_only_under_a_cleanup_prepare_stage_condition(self):
        lines = (S.REPO / "scripts/deploy.sh").read_text().splitlines()
        code = [(n, l.strip()) for n, l in enumerate(lines, 1) if l.strip() and not l.strip().startswith("#")]
        uses = [i for i, (_, l) in enumerate(code) if self.FLAG in l]
        self.assertEqual(len(uses), 1, "exactly one non-comment use of the flag in deploy.sh")
        i = uses[0]
        self.assertEqual(code[i][1], "HEADROOM_ARGS=(--no-headroom-floor)")
        self.assertEqual(code[i - 1][1], 'if [[ "${STAGE}" == "cleanup-prepare" ]]; then', "the flag is set directly under the stage condition")
        self.assertEqual(code[i + 1][1], "else")
        self.assertEqual(code[i + 2][1], 'HEADROOM_ARGS=(--min-headroom "${PRESPEND_MIN_HEADROOM_USD}")')
        self.assertEqual(code[i + 3][1], "fi")
        # no other place builds the headroom arguments, and the verify call takes them from that variable
        self.assertEqual(len([l for _, l in code if l.startswith("HEADROOM_ARGS=")]), 2)
        self.assertTrue(any('"${HEADROOM_ARGS[@]}"' in l for _, l in code))
        self.assertFalse(any("--min-headroom" in l and "HEADROOM_ARGS" not in l for _, l in code), "no literal --min-headroom elsewhere")


if __name__ == "__main__":
    unittest.main()

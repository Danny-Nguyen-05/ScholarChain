"""scripts/lib/budget.py (G6): exact decimal estimate, refusal and ledger rules. Expectations are hand-derived.

Subphase 13C updates (findings B2, B3, B4): the estimate adds the auto-termination idle tail, the ledger lives outside
the repository and is never read as empty when absent, and an approval record is single-use.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from helpers import SCRIPTS_DIR

BUDGET = os.path.join(SCRIPTS_DIR, "lib", "budget.py")


def run(*args):
    done = subprocess.run([sys.executable, "-I", BUDGET] + [str(a) for a in args], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def estimate(nodes_core=1, tasks=0, minutes=60, idle=900, ec2="0.192", emr="0.048", cap="3", budget="3", itype="m5.xlarge"):
    return run(
        "estimate", "--instance-type", itype, "--primary-count", 1, "--core-count", nodes_core, "--task-count", tasks, "--minutes", minutes,
        "--idle-seconds", idle, "--ec2-rate", ec2, "--emr-rate", emr, "--max-run-usd", cap, "--budget-usd", budget,
    )


def approval(label):
    return hashlib.sha256(label.encode()).hexdigest()


class EstimateTests(unittest.TestCase):
    def test_estimate_is_instances_times_rate_times_runtime_plus_idle_hours(self):
        # 3 nodes x (0.192 + 0.048) x (90 min + 900 s = 6300 s = 1.75 h) = 0.72 x 1.75 = 1.26
        rc, out, _ = estimate(nodes_core=1, tasks=1, minutes=90)
        self.assertEqual(rc, 0, out)
        doc = json.loads(out)
        self.assertEqual(doc["estimate_usd"], "1.26")
        self.assertEqual(doc["instances"], 3)
        self.assertEqual(doc["hourly_usd"], "0.720")
        self.assertEqual((doc["max_runtime_minutes"], doc["idle_timeout_seconds"], doc["billed_seconds"]), (90, 900, 6300))
        self.assertIn("(max_runtime + idle_timeout)", doc["formula"])
        # 2 nodes x (0.384 + 0.096) x (60 min + 900 s = 1.25 h) = 0.96 x 1.25 = 1.20
        self.assertEqual(json.loads(estimate(minutes=60, ec2="0.384", emr="0.096", itype="m5.2xlarge")[1])["estimate_usd"], "1.20")
        # 3 nodes x 0.24 x (180 min + 900 s = 3.25 h) = 0.72 x 3.25 = 2.34 (inside the 3 USD cap)
        self.assertEqual(json.loads(estimate(nodes_core=1, tasks=1, minutes=180)[1])["estimate_usd"], "2.34")

    def test_the_idle_tail_is_billed_finding_b3(self):
        # 2 nodes x 0.24 x 1 h = 0.48 without an idle tail; with 900 s the billed time is 1.25 h: 0.60
        self.assertEqual(json.loads(estimate(minutes=60, idle=0)[1])["estimate_usd"], "0.48")
        self.assertEqual(json.loads(estimate(minutes=60, idle=900)[1])["estimate_usd"], "0.60")
        # 60 s of idle tail: 2 x 0.24 x (3660 / 3600) = 0.488 -> 0.49
        self.assertEqual(json.loads(estimate(minutes=60, idle=60)[1])["estimate_usd"], "0.49")

    def test_the_worst_case_of_the_pinned_caps_is_refused_with_the_idle_tail(self):
        # 4 nodes x 0.24 x (180 min + 900 s = 3.25 h) = 0.96 x 3.25 = 3.12 > 3: the cap now catches it (the 13B reviewer's
        # 3.84 USD worst case used a 3600 s idle tail).
        rc, out, _ = estimate(nodes_core=2, tasks=1, minutes=180)
        self.assertEqual(rc, 1, out)
        self.assertIn("estimate 3.12 USD exceeds the per-run cap 3.00 USD", out)
        # the same shape with the 13B idle tail would have cost 4 x 0.24 x 4 h = 3.84
        rc, out, _ = estimate(nodes_core=2, tasks=1, minutes=180, idle=3600)
        self.assertIn("estimate 3.84 USD exceeds the per-run cap 3.00 USD", out)

    def test_the_estimate_rounds_up_to_the_cent_never_down(self):
        # 2 nodes x 0.24 x (60 s / 3600 s) = 0.008 -> 0.01
        self.assertEqual(json.loads(estimate(minutes=1, idle=0)[1])["estimate_usd"], "0.01")
        # 2 nodes x 0.24 x (61 min / 60) = 0.488 -> 0.49
        self.assertEqual(json.loads(estimate(minutes=61, idle=0)[1])["estimate_usd"], "0.49")
        # one idle second more than a minute: 2 x 0.24 x 61/3600 = 0.00813 -> 0.01
        self.assertEqual(json.loads(estimate(minutes=1, idle=1)[1])["estimate_usd"], "0.01")

    def test_unset_or_unusable_rates_are_unavailable_never_zero(self):
        for ec2, emr in (("", "0.048"), ("0.192", ""), ("0", "0.048"), ("-1", "0.048"), ("nan", "0.048"), ("inf", "0.048"), ("abc", "0.048"), ("0.192", "Infinity")):
            with self.subTest((ec2, emr)):
                rc, out, _ = estimate(ec2=ec2, emr=emr)
                self.assertEqual(rc, 2, out)
                self.assertIn("G6-UNAVAILABLE", out)
                self.assertNotIn('"estimate_usd"', out)

    def test_over_the_per_run_cap_or_the_declared_budget_refuses(self):
        # 4 nodes x 0.48 x 3.25 h = 6.24
        rc, out, _ = estimate(nodes_core=2, tasks=1, minutes=180, ec2="0.384", emr="0.096", cap="3", budget="3")
        self.assertEqual(rc, 1)
        self.assertIn("estimate 6.24 USD exceeds the per-run cap 3.00 USD", out)
        # 3 nodes x 0.24 x 1.75 h = 1.26 > 1.00
        rc, out, _ = estimate(minutes=90, nodes_core=1, tasks=1, budget="1.00")
        self.assertEqual(rc, 1)
        self.assertIn("estimate 1.26 USD exceeds the declared budget 1.00 USD", out)
        rc, out, _ = estimate(budget="3.01")
        self.assertEqual(rc, 1)
        self.assertIn("the declared budget 3.01 USD exceeds the per-run cap 3.00 USD", out)

    def test_exactly_at_the_cap_is_allowed(self):
        # 3 nodes x 0.2 x (285 min + 900 s = 18000 s = 5 h) = 3.00
        rc, out, _ = estimate(nodes_core=1, tasks=1, minutes=285, ec2="0.1", emr="0.1", cap="3", budget="3")
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(out)["estimate_usd"], "3.00")

    def test_no_binary_floating_point_surprises(self):
        # 0.1 + 0.2 style sums stay exact in Decimal: 3 x (0.1 + 0.2) x 1 h = 0.90 (no idle tail here)
        self.assertEqual(json.loads(estimate(nodes_core=1, tasks=1, minutes=60, idle=0, ec2="0.1", emr="0.2")[1])["estimate_usd"], "0.90")

    def test_invalid_counts_and_idle_refuse(self):
        rc, out, _ = run("estimate", "--instance-type", "m5.xlarge", "--primary-count", 1, "--core-count", -1, "--task-count", 0, "--minutes", 60, "--idle-seconds", 900, "--ec2-rate", "0.1", "--emr-rate", "0.1", "--max-run-usd", 3, "--budget-usd", 3)
        self.assertEqual(rc, 1)
        self.assertIn("core count must not be negative", out)
        self.assertEqual(estimate(minutes=0)[0], 1)
        rc, out, _ = estimate(idle=-1)
        self.assertEqual(rc, 1)
        self.assertIn("idle timeout must not be negative", out)

    def test_the_idle_argument_is_required(self):
        rc, _out, err = run("estimate", "--instance-type", "m5.xlarge", "--primary-count", 1, "--core-count", 1, "--task-count", 0, "--minutes", 60, "--ec2-rate", "0.1", "--emr-rate", "0.1", "--max-run-usd", 3, "--budget-usd", 3)
        self.assertEqual(rc, 2)
        self.assertIn("--idle-seconds", err)


class LedgerBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-ledger-")
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.home = os.path.realpath(os.path.join(self.tmp, "home"))
        self.repo = os.path.realpath(os.path.join(self.tmp, "repo"))
        os.makedirs(self.home)
        os.makedirs(self.repo)
        self.within = os.path.join(self.home, ".scholarchain")
        self.ledger = os.path.join(self.within, "emr-ledger", "runs.jsonl")

    def init(self, ledger=None, who="alice", repo=None):
        return run(
            "ledger-init", "--root", self.home, "--within-name", ".scholarchain under HOME", "--within", self.within, "--ledger", ledger or self.ledger,
            "--repo-root", repo or self.repo, "--initialized-by", who, "--initialized-utc", "2026-11-06T09:00:00Z",
        )

    def reserve(self, run_id="r-1", estimate="1.08", ledger=None, max_runs=3, cap="9.50", approval_sha=None, repo=None):
        return run(
            "ledger-reserve", "--root", self.home, "--ledger", ledger or self.ledger, "--repo-root", repo or self.repo, "--run-id", run_id, "--estimate", estimate,
            "--max-runs", max_runs, "--cumulative-cap", cap, "--action", "run-bounded-pipeline", "--run-config-sha256", "a" * 64,
            "--approval-sha256", approval_sha or approval("approval-" + run_id), "--reserved-utc", "2026-11-06T10:00:00Z",
        )

    def check(self, estimate="1.08", max_runs=3, cap="9.50", approval_sha=None, ledger=None, repo=None):
        args = ["ledger-check", "--ledger", ledger or self.ledger, "--repo-root", repo or self.repo, "--estimate", estimate, "--max-runs", max_runs, "--cumulative-cap", cap]
        if approval_sha:
            args += ["--approval-sha256", approval_sha]
        return run(*args)

    def write(self, estimates, init=True):
        os.makedirs(os.path.dirname(self.ledger), exist_ok=True)
        with open(self.ledger, "w", encoding="utf-8") as handle:
            if init:
                handle.write(json.dumps({"event": "init", "initialized_by": "fixture", "initialized_utc": "2026-11-01T00:00:00Z"}) + "\n")
            for index, value in enumerate(estimates):
                handle.write(json.dumps({"event": "reserve", "run_id": "e%d" % index, "estimate_usd": value, "approval_record_sha256": approval("earlier-%d" % index)}) + "\n")


class LedgerInitTests(LedgerBase):
    def test_init_creates_a_private_ledger_with_one_who_and_when_record(self):
        rc, out, _ = self.init(who="alice")
        self.assertEqual(rc, 0, out)
        self.assertIn("LEDGER-INITIALIZED", out)
        self.assertEqual(oct(os.stat(self.ledger).st_mode & 0o777), "0o600")
        self.assertEqual(oct(os.stat(os.path.dirname(self.ledger)).st_mode & 0o777), "0o700")
        with open(self.ledger, encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle]
        self.assertEqual(len(lines), 1)
        self.assertEqual((lines[0]["event"], lines[0]["initialized_by"], lines[0]["initialized_utc"]), ("init", "alice", "2026-11-06T09:00:00Z"))
        rc, out, _ = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("live_runs=0 of 3 cumulative_usd=0.00", out)

    def test_init_refuses_when_the_ledger_exists_and_leaves_it_unchanged(self):
        self.assertEqual(self.init()[0], 0)
        self.assertEqual(self.reserve("r-1")[0], 0)
        with open(self.ledger, "rb") as handle:
            before = handle.read()
        rc, out, _ = self.init(who="mallory")
        self.assertEqual(rc, 1)
        self.assertIn("already exists", out)
        self.assertIn("refusing to re-initialise", out)
        with open(self.ledger, "rb") as handle:
            self.assertEqual(handle.read(), before)

    def test_init_refuses_an_empty_existing_file_too(self):
        os.makedirs(os.path.dirname(self.ledger))
        open(self.ledger, "w").close()
        rc, out, _ = self.init()
        self.assertEqual(rc, 1)
        self.assertIn("already exists", out)

    def test_init_refuses_a_ledger_inside_the_repository_and_creates_nothing(self):
        inside = os.path.join(self.repo, "target", "emr-ledger", "runs.jsonl")
        rc, out, _ = self.init(ledger=inside)
        self.assertEqual(rc, 1)
        self.assertIn("outside the repository", out)
        self.assertFalse(os.path.exists(inside))

    def test_init_refuses_a_ledger_outside_the_scholarchain_directory(self):
        rc, out, _ = self.init(ledger=os.path.join(self.home, "elsewhere", "runs.jsonl"))
        self.assertEqual(rc, 1)
        self.assertIn("G6-REFUSED", out)
        self.assertFalse(os.path.exists(os.path.join(self.home, "elsewhere")))

    def test_init_refuses_a_multiline_name(self):
        rc, out, _ = self.init(who="a\nb")
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(self.ledger))


class LedgerTests(LedgerBase):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.init()[0], 0)

    def test_the_third_run_is_allowed_and_the_fourth_is_refused(self):
        self.write(["1.00", "1.00"])
        self.assertEqual(self.check()[0], 0)
        self.write(["1.00", "1.00", "1.00"])
        rc, out, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("3 live EMR runs are already recorded in the ledger (limit 3)", out)

    def test_the_cumulative_cap_is_inclusive_at_9_50(self):
        self.write(["4.00", "4.42"])  # 8.42 + 1.08 = 9.50
        self.assertEqual(self.check()[0], 0)
        self.write(["4.00", "4.43"])  # 8.43 + 1.08 = 9.51
        rc, out, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("cumulative estimate 9.51 USD (recorded 8.43 + this run 1.08) would exceed the cap 9.50 USD", out)

    def test_an_unreadable_ledger_refuses_rather_than_reading_as_empty(self):
        init_line = json.dumps({"event": "init", "initialized_by": "x", "initialized_utc": "t"}) + "\n"
        for text in (
            init_line + "garbage\n", init_line + '{"event": "other", "estimate_usd": "1"}\n', init_line + '{"event": "reserve"}\n',
            init_line + '{"event": "reserve", "estimate_usd": "nan"}\n', init_line + '{"event": "reserve", "estimate_usd": "-1"}\n',
            init_line + '{"event": "reserve", "estimate_usd": "1", "approval_record_sha256": "xyz"}\n',
            init_line + init_line,
        ):
            with self.subTest(text):
                with open(self.ledger, "w", encoding="utf-8") as handle:
                    handle.write(text)
                rc, out, _ = self.check()
                self.assertEqual(rc, 1)
                self.assertIn("the run ledger cannot be read", out)

    def test_a_symlinked_ledger_is_refused(self):
        os.remove(self.ledger)
        real = os.path.join(self.home, "elsewhere.jsonl")
        open(real, "w").close()
        os.symlink(real, self.ledger)
        self.assertEqual(self.check()[0], 1)
        rc, out, _ = self.reserve()
        self.assertEqual(rc, 1)
        self.assertIn("G6-REFUSED", out)
        self.assertEqual(os.path.getsize(real), 0)

    def test_reserve_appends_one_line_per_run_with_the_approval_hash(self):
        rc, out, _ = self.reserve("r-1", "1.08")
        self.assertEqual(rc, 0, out)
        self.assertEqual(oct(os.stat(self.ledger).st_mode & 0o777), "0o600")
        rc, out, _ = self.reserve("r-2", "2.00")
        self.assertEqual(rc, 0)
        with open(self.ledger, encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle]
        self.assertEqual([entry["event"] for entry in lines], ["init", "reserve", "reserve"])
        reserves = lines[1:]
        self.assertEqual([entry["run_id"] for entry in reserves], ["r-1", "r-2"])
        self.assertEqual([entry["estimate_usd"] for entry in reserves], ["1.08", "2.00"])
        self.assertEqual([entry["approval_record_sha256"] for entry in reserves], [approval("approval-r-1"), approval("approval-r-2")])
        self.assertTrue(all(entry["run_config_sha256"] == "a" * 64 for entry in reserves))
        self.assertIn("LEDGER-RESERVED: run=r-2 live_runs=2 of 3 cumulative_usd=3.08", out)

    def test_reserve_repeats_the_check_so_the_cap_cannot_be_passed(self):
        self.assertEqual(self.reserve("r-1", "3.00")[0], 0)
        self.assertEqual(self.reserve("r-2", "3.00")[0], 0)
        self.assertEqual(self.reserve("r-3", "3.00")[0], 0)
        rc, out, _ = self.reserve("r-4", "0.10")
        self.assertEqual(rc, 1)
        self.assertIn("live EMR runs", out)
        rc, out, _ = self.reserve("r-5", "0.10", cap="9.00")
        self.assertEqual(rc, 1)
        with open(self.ledger, encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 4)  # the init record and three reservations

    def test_three_runs_of_0_84_exactly_fill_the_2_52_cap_and_more_is_refused(self):
        """Decision 2026-11-09 (caps = planned use): 0.84 + 0.84 + 0.84 = 2.52 passes (inclusive, exact Decimal), a fourth run or 2.53 does not."""
        for index in (1, 2, 3):
            rc, out, _ = self.check(estimate="0.84", cap="2.52")
            self.assertEqual(rc, 0, out)
            rc, out, _ = self.reserve("r-%d" % index, "0.84", cap="2.52")
            self.assertEqual(rc, 0, out)
        self.assertIn("cumulative_usd=2.52", out)
        rc, out, _ = self.check(estimate="0.01", cap="2.52")
        self.assertEqual(rc, 1)
        self.assertIn("3 live EMR runs", out)
        rc, out, _ = self.reserve("r-4", "0.84", cap="2.52")
        self.assertEqual(rc, 1)
        with open(self.ledger, encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 4)  # the init record and three reservations only

    def test_a_cumulative_total_of_2_53_is_refused_against_the_2_52_cap(self):
        self.assertEqual(self.reserve("r-1", "0.84", cap="2.52")[0], 0)
        self.assertEqual(self.reserve("r-2", "0.84", cap="2.52")[0], 0)
        rc, out, _ = self.check(estimate="0.85", cap="2.52")
        self.assertEqual(rc, 1)
        self.assertIn("cumulative estimate 2.53 USD (recorded 1.68 + this run 0.85) would exceed the cap 2.52 USD", out)
        rc, out, _ = self.reserve("r-3", "0.85", cap="2.52")
        self.assertEqual(rc, 1)
        self.assertIn("would exceed the cap 2.52 USD", out)
        rc, out, _ = self.check(estimate="0.84", cap="2.52")
        self.assertEqual(rc, 0, out)

    def test_concurrent_reservations_cannot_exceed_the_live_run_limit(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda n: self.reserve("c-%d" % n, "0.50")[0], range(8)))
        self.assertEqual(sorted(results), [0, 0, 0, 1, 1, 1, 1, 1])
        with open(self.ledger, encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 4)

    def test_an_approval_is_single_use_even_after_a_failed_run_finding_b4(self):
        same = approval("one-approval-record")
        self.assertEqual(self.reserve("r-1", approval_sha=same)[0], 0)
        # the first run may have failed after spending: the ledger still holds the reservation, so reuse is refused
        rc, out, _ = self.reserve("r-2", approval_sha=same)
        self.assertEqual(rc, 1)
        self.assertIn("this approval record (sha256 %s) already started a run" % same, out)
        self.assertIn("single-use", out)
        rc, out, _ = self.check(approval_sha=same)
        self.assertEqual(rc, 1)
        self.assertIn("already started a run", out)
        with open(self.ledger, encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 2)  # init + the first reservation only
        # a different record is accepted
        other = approval("a-new-approval-record")
        self.assertEqual(self.check(approval_sha=other)[0], 0)
        self.assertEqual(self.reserve("r-3", approval_sha=other)[0], 0)

    def test_concurrent_runs_with_one_approval_start_exactly_one(self):
        same = approval("shared-record")
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda n: self.reserve("s-%d" % n, "0.10", approval_sha=same)[0], range(6)))
        self.assertEqual(sorted(results), [0, 1, 1, 1, 1, 1])

    def test_a_malformed_approval_hash_is_refused(self):
        rc, out, _ = self.reserve("r-1", approval_sha="not-a-hash")
        self.assertEqual(rc, 1)
        self.assertIn("not 64 lowercase hex", out)
        self.assertEqual(self.check(approval_sha="G" * 64)[0], 1)

    def test_a_ledger_path_outside_the_scholarchain_home_but_in_the_repo_is_refused(self):
        inside = os.path.join(self.repo, "target", "emr-ledger", "runs.jsonl")
        for command in (self.check, self.reserve):
            with self.subTest(command.__name__):
                rc, out, _ = command(ledger=inside)
                self.assertEqual(rc, 1)
                self.assertIn("outside the repository", out)
        self.assertFalse(os.path.exists(inside))

    def test_relative_and_dotdot_ledger_paths_are_refused(self):
        for path in ("runs.jsonl", os.path.join(self.within, "..", "runs.jsonl")):
            with self.subTest(path):
                rc, out, _ = self.check(ledger=path)
                self.assertEqual(rc, 1)
                self.assertIn("G6-REFUSED", out)

    def test_the_ledger_must_stay_inside_the_root(self):
        outside = os.path.join(tempfile.gettempdir(), "sc-outside-ledger.jsonl")
        rc, out, _ = self.reserve(ledger=outside)
        self.assertEqual(rc, 1)
        self.assertIn("G6-REFUSED", out)
        self.assertFalse(os.path.exists(outside))


class AbsentLedgerTests(LedgerBase):
    """Finding B2: an absent ledger is never read as zero runs, and nothing but --init-ledger creates it."""

    def test_check_refuses_an_absent_ledger(self):
        rc, out, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("does not exist", out)
        self.assertIn("--init-ledger", out)
        self.assertIn("never read as zero runs", out)

    def test_reserve_refuses_an_absent_ledger_and_creates_nothing(self):
        rc, out, _ = self.reserve()
        self.assertEqual(rc, 1)
        self.assertIn("does not exist", out)
        self.assertFalse(os.path.exists(self.ledger))
        self.assertFalse(os.path.exists(self.ledger + ".lock"))
        self.assertFalse(os.path.exists(self.within))

    def test_an_empty_file_is_not_an_initialised_ledger(self):
        os.makedirs(os.path.dirname(self.ledger))
        open(self.ledger, "w").close()
        rc, out, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("no init record", out)
        rc, out, _ = self.reserve()
        self.assertEqual(rc, 1)

    def test_a_file_whose_first_record_is_not_init_is_refused(self):
        self.write(["1.00"], init=False)
        rc, out, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("ledger line 1 is malformed", out)

    def test_deleting_the_ledger_after_a_run_refuses_instead_of_resetting_the_caps(self):
        self.assertEqual(self.init()[0], 0)
        for n in range(3):
            self.assertEqual(self.reserve("r-%d" % n)[0], 0)
        self.assertEqual(self.check()[0], 1)  # the fourth is refused
        os.remove(self.ledger)  # an sbt clean or a fresh clone used to do this when the ledger sat under target/
        rc, out, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("does not exist", out)


class ReleaseConfTests(unittest.TestCase):
    def conf(self):
        values = {}
        with open(os.path.join(SCRIPTS_DIR, "config", "release.conf"), encoding="utf-8") as handle:
            for line in handle:
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.rstrip("\n").partition("=")
                    values[key] = value
        return values

    def test_the_ledger_is_pinned_under_home_outside_target(self):
        path = self.conf()["EMR_LEDGER_PATH"]
        self.assertEqual(path, "~/.scholarchain/emr-ledger/runs.jsonl")
        self.assertNotIn("target", path.split("/"))

    def test_the_idle_timeout_cap_is_900_seconds_finding_b3(self):
        self.assertEqual(self.conf()["PIPELINE_MAX_IDLE_TIMEOUT_SECONDS"], "900")


if __name__ == "__main__":
    unittest.main()

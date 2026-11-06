"""scripts/lib/budget.py (G6): exact decimal estimate, refusal and ledger rules. Expectations are hand-derived."""
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


def estimate(nodes_core=1, tasks=0, minutes=60, ec2="0.192", emr="0.048", cap="3", budget="3", itype="m5.xlarge"):
    return run("estimate", "--instance-type", itype, "--primary-count", 1, "--core-count", nodes_core, "--task-count", tasks, "--minutes", minutes, "--ec2-rate", ec2, "--emr-rate", emr, "--max-run-usd", cap, "--budget-usd", budget)


class EstimateTests(unittest.TestCase):
    def test_estimate_is_instances_times_rate_times_hours(self):
        # 3 nodes x (0.192 + 0.048) x 1.5 h = 1.08
        rc, out, _ = estimate(nodes_core=1, tasks=1, minutes=90)
        self.assertEqual(rc, 0)
        doc = json.loads(out)
        self.assertEqual(doc["estimate_usd"], "1.08")
        self.assertEqual(doc["instances"], 3)
        self.assertEqual(doc["hourly_usd"], "0.720")
        # 2 nodes x (0.384 + 0.096) x 1 h = 0.96
        self.assertEqual(json.loads(estimate(minutes=60, ec2="0.384", emr="0.096", itype="m5.2xlarge")[1])["estimate_usd"], "0.96")
        # 4 nodes x 0.24 x 3 h = 2.88 (inside the 3 USD cap)
        self.assertEqual(json.loads(estimate(nodes_core=3, minutes=180)[1])["estimate_usd"], "2.88")

    def test_the_estimate_rounds_up_to_the_cent_never_down(self):
        # 2 nodes x 0.24 x (1/60) h = 0.008 -> 0.01
        self.assertEqual(json.loads(estimate(minutes=1)[1])["estimate_usd"], "0.01")
        # 2 nodes x 0.24 x (61/60) h = 0.488 -> 0.49
        self.assertEqual(json.loads(estimate(minutes=61)[1])["estimate_usd"], "0.49")

    def test_unset_or_unusable_rates_are_unavailable_never_zero(self):
        for ec2, emr in (("", "0.048"), ("0.192", ""), ("0", "0.048"), ("-1", "0.048"), ("nan", "0.048"), ("inf", "0.048"), ("abc", "0.048"), ("0.192", "Infinity")):
            with self.subTest((ec2, emr)):
                rc, out, _ = estimate(ec2=ec2, emr=emr)
                self.assertEqual(rc, 2, out)
                self.assertIn("G6-UNAVAILABLE", out)
                self.assertNotIn('"estimate_usd"', out)

    def test_over_the_per_run_cap_or_the_declared_budget_refuses(self):
        # 4 nodes x 0.48 x 3 h = 5.76
        rc, out, _ = estimate(nodes_core=3, minutes=180, ec2="0.384", emr="0.096", cap="3", budget="3")
        self.assertEqual(rc, 1)
        self.assertIn("estimate 5.76 USD exceeds the per-run cap 3.00 USD", out)
        rc, out, _ = estimate(minutes=90, nodes_core=1, tasks=1, budget="1.00")
        self.assertEqual(rc, 1)
        self.assertIn("estimate 1.08 USD exceeds the declared budget 1.00 USD", out)
        rc, out, _ = estimate(budget="3.01")
        self.assertEqual(rc, 1)
        self.assertIn("the declared budget 3.01 USD exceeds the per-run cap 3.00 USD", out)

    def test_exactly_at_the_cap_is_allowed(self):
        # 3 nodes x 0.2 x 5 h would be 3.00: use rates 0.1 + 0.1 and 300 min
        rc, out, _ = estimate(nodes_core=1, tasks=1, minutes=300, ec2="0.1", emr="0.1", cap="3", budget="3")
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(out)["estimate_usd"], "3.00")

    def test_no_binary_floating_point_surprises(self):
        # 0.1 + 0.2 style sums stay exact in Decimal: 3 x (0.1 + 0.2) x 1 h = 0.90
        self.assertEqual(json.loads(estimate(nodes_core=1, tasks=1, minutes=60, ec2="0.1", emr="0.2")[1])["estimate_usd"], "0.90")

    def test_invalid_counts_refuse(self):
        rc, out, _ = run("estimate", "--instance-type", "m5.xlarge", "--primary-count", 1, "--core-count", -1, "--task-count", 0, "--minutes", 60, "--ec2-rate", "0.1", "--emr-rate", "0.1", "--max-run-usd", 3, "--budget-usd", 3)
        self.assertEqual(rc, 1)
        self.assertIn("core count must not be negative", out)
        self.assertEqual(estimate(minutes=0)[0], 1)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-ledger-")
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.root = os.path.realpath(self.tmp)
        os.makedirs(os.path.join(self.root, "target", "emr-ledger"))
        self.ledger = os.path.join(self.root, "target", "emr-ledger", "runs.jsonl")

    def reserve(self, run_id="r-1", estimate="1.08", ledger=None, max_runs=3, cap="9.50"):
        return run("ledger-reserve", "--root", self.root, "--ledger", ledger or self.ledger, "--run-id", run_id, "--estimate", estimate, "--max-runs", max_runs, "--cumulative-cap", cap, "--action", "run-bounded-pipeline", "--run-config-sha256", "a" * 64, "--reserved-utc", "2026-11-06T00:00:00Z")

    def check(self, estimate="1.08", max_runs=3, cap="9.50"):
        return run("ledger-check", "--ledger", self.ledger, "--estimate", estimate, "--max-runs", max_runs, "--cumulative-cap", cap)

    def write(self, estimates):
        with open(self.ledger, "w", encoding="utf-8") as handle:
            for index, value in enumerate(estimates):
                handle.write(json.dumps({"event": "reserve", "run_id": "e%d" % index, "estimate_usd": value}) + "\n")

    def test_an_absent_ledger_counts_zero_runs(self):
        rc, out, _ = self.check()
        self.assertEqual(rc, 0)
        self.assertIn("live_runs=0 of 3 cumulative_usd=0.00 this_run_usd=1.08 cap_usd=9.50", out)

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
        for text in ("garbage\n", '{"event": "other", "estimate_usd": "1"}\n', '{"event": "reserve"}\n', '{"event": "reserve", "estimate_usd": "nan"}\n', '{"event": "reserve", "estimate_usd": "-1"}\n'):
            with self.subTest(text):
                with open(self.ledger, "w", encoding="utf-8") as handle:
                    handle.write(text)
                rc, out, _ = self.check()
                self.assertEqual(rc, 1)
                self.assertIn("the run ledger cannot be read", out)

    def test_a_symlinked_ledger_is_refused(self):
        real = os.path.join(self.root, "elsewhere.jsonl")
        open(real, "w").close()
        os.symlink(real, self.ledger)
        self.assertEqual(self.check()[0], 1)
        rc, out, _ = self.reserve()
        self.assertEqual(rc, 1)
        self.assertIn("G6-REFUSED", out)
        self.assertEqual(os.path.getsize(real), 0)

    def test_reserve_creates_a_private_ledger_and_appends_one_line_per_run(self):
        rc, out, _ = self.reserve("r-1", "1.08")
        self.assertEqual(rc, 0, out)
        self.assertEqual(oct(os.stat(self.ledger).st_mode & 0o777), "0o600")
        rc, out, _ = self.reserve("r-2", "2.00")
        self.assertEqual(rc, 0)
        with open(self.ledger, encoding="utf-8") as handle:
            lines = [json.loads(l) for l in handle]
        self.assertEqual([l["run_id"] for l in lines], ["r-1", "r-2"])
        self.assertEqual([l["estimate_usd"] for l in lines], ["1.08", "2.00"])
        self.assertTrue(all(l["event"] == "reserve" and l["run_config_sha256"] == "a" * 64 for l in lines))
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
            self.assertEqual(len(handle.readlines()), 3)

    def test_concurrent_reservations_cannot_exceed_the_live_run_limit(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda n: self.reserve("c-%d" % n, "0.50")[0], range(8)))
        self.assertEqual(sorted(results), [0, 0, 0, 1, 1, 1, 1, 1])
        with open(self.ledger, encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 3)

    def test_the_ledger_must_stay_inside_the_root(self):
        outside = os.path.join(tempfile.gettempdir(), "sc-outside-ledger.jsonl")
        rc, out, _ = self.reserve(ledger=outside)
        self.assertEqual(rc, 1)
        self.assertIn("G6-REFUSED", out)
        self.assertFalse(os.path.exists(outside))


if __name__ == "__main__":
    unittest.main()

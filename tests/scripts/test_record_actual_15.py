"""Phase 15 D3: `run-bounded-pipeline.sh --record-actual` (test-engineer, independent, black box).

Requirement (human, docs/agent-runs/phase-15/prompt.md "S run cap and D3 go-ahead", 2026-11-16): "Record the EMR actuals right after
each S run so the pre-R-b check uses real numbers, not the cap." As documented in the script's --help: after a run the operator
saves `aws emr describe-cluster --output json` to a private file and runs
    scripts/run-bounded-pipeline.sh --record-actual --run-id <run id> --describe <file> [--as-of-utc <save time>]
which makes no cloud call, binds the run to its cluster through the run manifest, REPLACES that run's reserved estimate in the
cumulative total with the measured cluster time x the reviewed rates of its instance groups (rounded UP to the cent), adds the
pending auto-termination tail while the cluster has not ended, never changes the run count, and prints LEDGER-OVER-CAP when the
new total is above the cumulative cap.

Driven end to end with the sc_support fakes: a green `--execute` (r5.xlarge primary, m5.xlarge core) reserves the run and writes its
manifest; the synthetic describe-cluster JSON is written here. Expected amounts are derived by hand from the reviewed rates in
scripts/config/emr-pricing.conf: r5.xlarge 0.252 + 0.063 = 0.315, m5.xlarge 0.192 + 0.048 = 0.240, cluster 0.555 USD per hour.
"""
import datetime
import json
import re
import unittest
from decimal import Decimal as D

import sc_support as S

R5 = dict(primary_instance_type="r5.xlarge")
GROUPS = {"InstanceGroups": [
    {"InstanceGroupType": "MASTER", "InstanceType": "r5.xlarge", "RequestedInstanceCount": 1, "RunningInstanceCount": 1},
    {"InstanceGroupType": "CORE", "InstanceType": "m5.xlarge", "RequestedInstanceCount": 1, "RunningInstanceCount": 1}]}
CREATED = "2026-11-15T15:00:00Z"
RUN_ID = "bp-test-run-1"


def describe(end_seconds=None, state="TERMINATED", cluster="j-TESTCLUSTER", groups=GROUPS):
    """A synthetic `aws emr describe-cluster --output json` document (CLI v2 shape); the end time is CREATED + end_seconds."""
    timeline = {"CreationDateTime": CREATED}
    if end_seconds is not None:
        h, rest = divmod(15 * 3600 + end_seconds, 3600)
        m, s = divmod(rest, 60)
        timeline["EndDateTime"] = "2026-11-15T%02d:%02d:%02dZ" % (h, m, s)
    return {"Cluster": {"Id": cluster, "Status": {"State": state, "Timeline": timeline}, "InstanceGroups": groups["InstanceGroups"]}}


def ledger_value(run, key):
    found = re.findall(r"\b%s=([0-9.]+)" % key, run.out)
    if not found:
        raise AssertionError("no %s= in the output\n%s" % (key, run.describe()))
    return found[-1]


class RecordActual(unittest.TestCase):
    def executed(self, ledger):
        """A fixture whose ledger holds `ledger` (earlier runs) plus one green r5-primary run reserved at its estimate."""
        fx = S.Fixture(self)
        fx.update_scenario(groups=GROUPS)
        fx.write_ledger(ledger)
        run = fx.execute(pipeline_over=R5)
        self.assertEqual(run.rc, 0, run.describe())
        self.assertEqual(len(fx.reservations()), len(ledger) + 1)
        self.assertEqual(fx.reservations()[-1]["run_id"], RUN_ID)
        self.assertEqual(fx.reservations()[-1]["estimate_usd"] if isinstance(fx.reservations()[-1]["estimate_usd"], str)
                         else "%.2f" % fx.reservations()[-1]["estimate_usd"], "0.70")  # (0.315 + 0.240) x 1.25 h, rounded up
        return fx

    def record(self, fx, document, as_of=None, run_id=RUN_ID):
        path = fx.aux / "describe-private.json"
        path.write_text(json.dumps(document))
        args = ["--record-actual", "--run-id", run_id, "--describe", str(path)]
        if as_of:
            args += ["--as-of-utc", as_of]
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, fx.exec_env())
        return run

    def test_an_ended_cluster_replaces_the_estimate_and_never_changes_the_run_count(self):
        """Session 1 (0.84 + 0.84) + this run reserved at 0.70 = 2.38. Measured: one hour at 0.555 = 0.555 -> 0.56, no tail (ended),
        so the total becomes 1.68 + 0.56 = 2.24 and the live-run count stays 3."""
        fx = self.executed(["0.84", "0.84"])
        before = fx.reservations()
        run = self.record(fx, describe(end_seconds=3600))
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        self.assertEqual(run.calls, [], "--record-actual makes no cloud call")
        self.assertEqual(ledger_value(run, "measured_usd"), "0.56")
        self.assertEqual(ledger_value(run, "tail_usd"), "0.00")
        self.assertEqual(ledger_value(run, "reserved_estimate_usd"), "0.70")
        self.assertIn("live_runs=3 of 5", run.out)
        self.assertEqual(ledger_value(run, "cumulative_usd"), "2.24")
        self.assertNotIn("LEDGER-OVER-CAP", run.out)
        self.assertEqual(fx.reservations(), before, "the reserve records are untouched: an actual never frees or adds a run slot")
        actuals = [r for r in fx.ledger_records() if r.get("event") == "actual"]
        self.assertEqual(len(actuals), 1)
        self.assertEqual((actuals[0]["run_id"], actuals[0]["cluster_id"], actuals[0]["measured_usd"]), (RUN_ID, "j-TESTCLUSTER", "0.56"))
        # the next run sees the measured total: a run whose estimate fits 4.70 - 2.24 = 2.46 is still allowed, and the count is 3 of 5 (Phase 18 18B caps)
        dry = fx.dry(extra_env=fx.exec_env(), **R5)
        self.assertEqual(dry.rc, 0, dry.describe())
        self.assertNotIn("G6-STATUS: --execute would be refused", dry.out)

    def test_a_running_cluster_adds_the_pending_idle_tail(self):
        """RUNNING, saved one hour after creation: measured 0.56 plus the 900 s auto-termination tail still to come,
        0.555 x 0.25 = 0.13875 -> 0.14. Total 1.68 + 0.56 + 0.14 = 2.38. Without --as-of-utc a running cluster is refused."""
        fx = self.executed(["0.84", "0.84"])
        refused = self.record(fx, describe(state="RUNNING"))
        self.assertEqual((refused.rc, refused.status), (3, "REFUSED"), refused.describe())
        run = self.record(fx, describe(state="RUNNING"), as_of="2026-11-15T16:00:00Z")
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        self.assertEqual(ledger_value(run, "measured_usd"), "0.56")
        self.assertEqual(ledger_value(run, "tail_usd"), "0.14")
        self.assertEqual(ledger_value(run, "cumulative_usd"), "2.38")
        self.assertIn("live_runs=3 of 5", run.out)

    def test_over_the_cap_prints_ledger_over_cap_and_exactly_the_cap_does_not(self):
        """Phase 18 18B cap (release.conf EMR_CUMULATIVE_CAP_USD 4.70; it was 3.53 with X = 1.85 at 12000 s). Session 1 1.68 + measured X against
        the cap 4.70. X = 3.02 at 19589 s (0.555 x 19589 / 3600 = 3.019896, rounded up 3.02): total 4.70, at the cap, no marker. 19590 s
        (3.020125 -> 3.03): total 4.71 > 4.70, LEDGER-OVER-CAP, and every further run is refused. The run count stays 3 (of 5) in both."""
        at_cap = self.executed(["0.84", "0.84"])
        run = self.record(at_cap, describe(end_seconds=19589))
        self.assertEqual((run.rc, ledger_value(run, "measured_usd"), ledger_value(run, "cumulative_usd")), (0, "3.02", "4.70"), run.describe())
        self.assertNotIn("LEDGER-OVER-CAP", run.out)
        self.assertIn("cap_usd=4.70", run.out)
        over = self.executed(["0.84", "0.84"])
        run = self.record(over, describe(end_seconds=19590))
        self.assertEqual((run.rc, ledger_value(run, "measured_usd"), ledger_value(run, "cumulative_usd")), (0, "3.03", "4.71"), run.describe())
        self.assertIn("LEDGER-OVER-CAP", run.out)
        self.assertIn("live_runs=3 of 5", run.out)
        self.assertEqual(len(over.reservations()), 3)
        dry = over.dry(extra_env=over.exec_env(), **R5)
        self.assertIn("G6-STATUS: --execute would be refused", dry.out, dry.describe())

    def test_refusals_leave_the_ledger_unchanged(self):
        fx = self.executed(["0.84", "0.84"])
        before = fx.ledger_path.read_text()
        unpriced = {"InstanceGroups": [dict(GROUPS["InstanceGroups"][0], InstanceType="r6i.xlarge"), GROUPS["InstanceGroups"][1]]}
        cases = (("another cluster", describe(end_seconds=3600, cluster="j-SOMEONEELSE"), RUN_ID),
                 ("a group without a reviewed rate", describe(end_seconds=3600, groups=unpriced), RUN_ID),
                 ("a run that was never reserved", describe(end_seconds=3600), "bp-never-reserved"))
        for label, document, run_id in cases:
            with self.subTest(case=label):
                run = self.record(fx, document, run_id=run_id)
                self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
                self.assertEqual(fx.ledger_path.read_text(), before)
                self.assertEqual(run.calls, [])


class TimeoutThenRetryOnTheSameCluster(unittest.TestCase):
    """Review finding 1 (Phase 15), restated for Phase 18 18B (human decisions 2026-11-24, docs/agent-runs/phase-18/human-gate.md,
    verbatim answers "Raise to 120 min (Recommended)" and "Yes, allow 1 retry"): the size-S run times out, its actual is recorded, and the
    one retry runs on the same cluster. Real run-bounded-pipeline.sh --execute / --record-actual code paths (budget.py ledger), fakes
    for every cloud binary. Hand-derived, rates from emr-pricing.conf (r5.xlarge 0.315 + m5.xlarge 0.240 = 0.555 USD per hour):

      * the 120-minute S run: 0.555 x (120 x 60 + 900) / 3600 = 0.555 x 2.25 = 1.24875, rounded up 1.25 (the reserved estimate; so is the
        retry's; it was 0.84 at 75 minutes);
      * the ledger as of 2026-11-24 holds 3 runs and USD 2.05 (here 0.84 + 0.84 + 0.37; only the sum and the count matter);
      * run 4 (S) times out and the cluster still runs (idle, awaiting auto-termination). Measured from creation: 8160 s ->
        0.555 x 8160 / 3600 = 1.258, rounded up 1.26; 8220 s -> 1.26725 -> 1.27. Tail: 900 s x 0.555 / 3600 = 0.13875 -> 0.14.
        The ledger counts S at the measured amount plus the latest actual's tail: 2.05 + 1.26 + 0.14 = 3.45 (or 2.05 + 1.27 + 0.14 = 3.46);
      * the retry (estimate 1.25): 3.45 + 1.25 = 4.70, which equals the release.conf cap (inclusive, allowed); 3.46 + 1.25 = 4.71, refused;
      * the retry is the fifth live run; a sixth is refused by EMR_MAX_LIVE_RUNS (5) whatever it would cost.
    """
    PLAN = dict(R5, max_runtime_minutes=120)
    PRIOR = ["0.84", "0.84", "0.37"]  # 3 runs, USD 2.05

    @staticmethod
    def cap():
        return D(re.search(r"^EMR_CUMULATIVE_CAP_USD=(\S+)", (S.REPO / "scripts/config/release.conf").read_text(), re.M).group(1))

    @staticmethod
    def max_runs():
        return int(re.search(r"^EMR_MAX_LIVE_RUNS=(\S+)", (S.REPO / "scripts/config/release.conf").read_text(), re.M).group(1))

    @staticmethod
    def max_run_usd():
        return D(re.search(r"^EMR_MAX_RUN_USD=(\S+)", (S.REPO / "scripts/config/release.conf").read_text(), re.M).group(1))

    def timed_out_s(self, measured_seconds):
        """The prior ledger (3 runs, 2.05) plus the 120-minute S run (run 4) reserved at its estimate, then its actual recorded while the
        cluster is still running `measured_seconds` after creation. Returns the fixture and the --record-actual run."""
        fx = S.Fixture(self)
        fx.update_scenario(groups=GROUPS)
        fx.write_ledger(self.PRIOR)
        run = fx.execute(pipeline_over=self.PLAN, runtime="120")
        self.assertEqual(run.rc, 0, run.describe())
        self.assertEqual(fx.reservations()[-1]["run_id"], RUN_ID)
        self.assertEqual(str(fx.reservations()[-1]["estimate_usd"]), "1.25", "0.555 x (7200 + 900) / 3600 = 1.24875 -> 1.25")
        self.assertEqual(len(fx.reservations()), 4)
        as_of = datetime.datetime(2026, 11, 15, 15, 0, 0) + datetime.timedelta(seconds=measured_seconds)
        path = fx.aux / "describe-private.json"
        path.write_text(json.dumps(describe(state="RUNNING")))
        fx.log.write_text("")
        actual = fx.run("run-bounded-pipeline.sh", ["--record-actual", "--run-id", RUN_ID, "--describe", str(path),
                                                    "--as-of-utc", as_of.strftime("%Y-%m-%dT%H:%M:%SZ")], fx.exec_env())
        self.assertEqual((actual.rc, actual.status), (0, "PASS"), actual.describe())
        return fx, actual

    def retry(self, fx, run_id="bp-retry-2", serial="retry"):
        return fx.execute(pipeline_over=dict(self.PLAN, run_id=run_id), runtime="120", serial=serial,
                          approval_name="approval-%s.md" % serial)

    def test_the_live_caps_in_release_conf_are_five_runs_4_70_and_3_per_run_and_are_the_hand_derived_ones(self):
        self.assertEqual(self.cap(), D("2.05") + D("1.26") + D("0.14") + D("1.25"))
        self.assertEqual(self.cap(), D("4.70"))
        self.assertEqual(self.max_runs(), 5)
        self.assertEqual(self.max_run_usd(), D("3"))
        self.assertLess(D("1.25"), self.max_run_usd(), "the 120-minute estimate stays below the per-run cap")

    def test_retry_at_exactly_the_cap_is_admitted_and_a_sixth_run_is_refused_by_the_run_limit(self):
        fx, actual = self.timed_out_s(8160)
        self.assertEqual((ledger_value(actual, "measured_usd"), ledger_value(actual, "tail_usd")), ("1.26", "0.14"), actual.describe())
        self.assertEqual(ledger_value(actual, "cumulative_usd"), "3.45")
        self.assertIn("live_runs=4 of 5", actual.out)
        self.assertNotIn("LEDGER-OVER-CAP", actual.out)
        run = self.retry(fx)
        self.assertEqual(run.rc, 0, run.describe())  # 2.05 + 1.26 + 0.14 + 1.25 = 4.70 <= 4.70, inclusive
        self.assertIn("LEDGER-RESERVED", run.out, run.describe())
        self.assertNotIn("would exceed the cap", run.text)
        self.assertEqual([r["run_id"] for r in fx.reservations()][-2:], [RUN_ID, "bp-retry-2"])
        self.assertEqual(len(fx.reservations()), 5)
        # the fifth run is on the books: a sixth is refused at the g6-gate by the run limit (it would also break the cap)
        before = fx.ledger_path.read_text()
        sixth = self.retry(fx, run_id="bp-sixth-3", serial="sixth")
        self.assertEqual((sixth.rc, sixth.status, S.last_step(sixth)), (3, "REFUSED", "g6-gate"), sixth.describe())
        self.assertIn("5 live EMR runs are already recorded in the ledger (limit 5)", sixth.text)
        self.assertEqual(fx.ledger_path.read_text(), before, "a refused run reserves nothing")
        self.assertEqual(len(fx.reservations()), 5)

    def test_retry_one_cent_over_the_cap_is_refused_with_the_cumulative_cap_message(self):
        """The Phase 18 retry boundary: run 4 measured 1.26 admits the retry (above), 1.27 refuses it."""
        fx, actual = self.timed_out_s(8220)
        self.assertEqual((ledger_value(actual, "measured_usd"), ledger_value(actual, "tail_usd")), ("1.27", "0.14"), actual.describe())
        self.assertEqual(ledger_value(actual, "cumulative_usd"), "3.46")
        self.assertNotIn("LEDGER-OVER-CAP", actual.out, "3.46 is below the cap; only the retry would not fit")
        before = fx.ledger_path.read_text()
        run = self.retry(fx)
        self.assertEqual((run.rc, run.status, S.last_step(run)), (3, "REFUSED", "g6-gate"), run.describe())
        self.assertIn("cumulative estimate 4.71 USD (recorded 3.46 + this run 1.25) would exceed the cap 4.70 USD", run.text)
        self.assertNotIn("live EMR runs are already recorded", run.text, "four runs are on the books: only the cap refuses")
        self.assertEqual(fx.ledger_path.read_text(), before, "a refused run reserves nothing")
        self.assertEqual(len(fx.reservations()), 4)


if __name__ == "__main__":
    unittest.main()

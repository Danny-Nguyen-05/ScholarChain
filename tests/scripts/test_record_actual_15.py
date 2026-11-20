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
        self.assertIn("live_runs=3 of 4", run.out)
        self.assertEqual(ledger_value(run, "cumulative_usd"), "2.24")
        self.assertNotIn("LEDGER-OVER-CAP", run.out)
        self.assertEqual(fx.reservations(), before, "the reserve records are untouched: an actual never frees or adds a run slot")
        actuals = [r for r in fx.ledger_records() if r.get("event") == "actual"]
        self.assertEqual(len(actuals), 1)
        self.assertEqual((actuals[0]["run_id"], actuals[0]["cluster_id"], actuals[0]["measured_usd"]), (RUN_ID, "j-TESTCLUSTER", "0.56"))
        # the next run sees the measured total: a run whose estimate fits 3.53 - 2.24 = 1.29 is still allowed, and the count is 3
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
        self.assertIn("live_runs=3 of 4", run.out)

    def test_over_the_cap_prints_ledger_over_cap_and_exactly_the_cap_does_not(self):
        """Session 1 1.68 + measured X against the cap 3.53. X = 1.85 at 12000 s (0.555 x 12000 / 3600 = 1.85 exactly): total
        3.53, at the cap, no marker. 12001 s (1.850154 -> 1.86): total 3.54 > 3.53, LEDGER-OVER-CAP, and every further run is
        refused. The run count stays 3 in both."""
        at_cap = self.executed(["0.84", "0.84"])
        run = self.record(at_cap, describe(end_seconds=12000))
        self.assertEqual((run.rc, ledger_value(run, "measured_usd"), ledger_value(run, "cumulative_usd")), (0, "1.85", "3.53"), run.describe())
        self.assertNotIn("LEDGER-OVER-CAP", run.out)
        over = self.executed(["0.84", "0.84"])
        run = self.record(over, describe(end_seconds=12001))
        self.assertEqual((run.rc, ledger_value(run, "measured_usd"), ledger_value(run, "cumulative_usd")), (0, "1.86", "3.54"), run.describe())
        self.assertIn("LEDGER-OVER-CAP", run.out)
        self.assertIn("live_runs=3 of 4", run.out)
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
    """Review finding 1 (Phase 15, user decision 2026-11-16 "Raise cap to 3.53"): S times out, its actual is recorded, and the one
    S retry runs on the same cluster. Real run-bounded-pipeline.sh --execute / --record-actual code paths (budget.py ledger), fakes
    for every cloud binary. Hand-derived, rates from emr-pricing.conf (r5.xlarge 0.315 + m5.xlarge 0.240 = 0.555 USD per hour):

      * the 75-minute S run: 0.555 x (75 x 60 + 900) / 3600 = 0.8325, rounded up 0.84 (the reserved estimate; so is the retry's);
      * Session 1 holds 2 runs at 0.84 = 1.68;
      * S timed out and the cluster still runs (idle, awaiting auto-termination). Measured from creation: 5643 s ->
        0.555 x 5643 / 3600 = 0.869946, rounded up 0.87; 5700 s -> 0.87875 -> 0.88. Tail: 900 s x 0.555 / 3600 = 0.13875 -> 0.14.
        The ledger counts S at the measured amount plus the latest actual's tail: 1.68 + 0.87 + 0.14 = 2.69 (or 2.70);
      * the retry (estimate 0.84): 2.69 + 0.84 = 3.53, which equals the release.conf cap (inclusive, allowed); 2.70 + 0.84 = 3.54, refused;
      * the retry is the fourth live run; a fifth is refused by EMR_MAX_LIVE_RUNS (4) whatever it would cost.
    """
    PLAN = dict(R5, max_runtime_minutes=75)

    @staticmethod
    def cap():
        return D(re.search(r"^EMR_CUMULATIVE_CAP_USD=(\S+)", (S.REPO / "scripts/config/release.conf").read_text(), re.M).group(1))

    @staticmethod
    def max_runs():
        return int(re.search(r"^EMR_MAX_LIVE_RUNS=(\S+)", (S.REPO / "scripts/config/release.conf").read_text(), re.M).group(1))

    def timed_out_s(self, measured_seconds):
        """Session 1 (0.84 + 0.84) plus the 75-minute S run reserved at its estimate, then its actual recorded while the cluster is
        still running `measured_seconds` after creation. Returns the fixture and the --record-actual run."""
        fx = S.Fixture(self)
        fx.update_scenario(groups=GROUPS)
        fx.write_ledger(["0.84", "0.84"])
        run = fx.execute(pipeline_over=self.PLAN, runtime="75")
        self.assertEqual(run.rc, 0, run.describe())
        self.assertEqual(fx.reservations()[-1]["run_id"], RUN_ID)
        self.assertEqual(str(fx.reservations()[-1]["estimate_usd"]), "0.84", "0.555 x (4500 + 900) / 3600 = 0.8325 -> 0.84")
        as_of = datetime.datetime(2026, 11, 15, 15, 0, 0) + datetime.timedelta(seconds=measured_seconds)
        path = fx.aux / "describe-private.json"
        path.write_text(json.dumps(describe(state="RUNNING")))
        fx.log.write_text("")
        actual = fx.run("run-bounded-pipeline.sh", ["--record-actual", "--run-id", RUN_ID, "--describe", str(path),
                                                    "--as-of-utc", as_of.strftime("%Y-%m-%dT%H:%M:%SZ")], fx.exec_env())
        self.assertEqual((actual.rc, actual.status), (0, "PASS"), actual.describe())
        return fx, actual

    def retry(self, fx, run_id="bp-retry-2", serial="retry"):
        return fx.execute(pipeline_over=dict(self.PLAN, run_id=run_id), runtime="75", serial=serial,
                          approval_name="approval-%s.md" % serial)

    def test_the_cap_and_run_limit_in_release_conf_are_the_hand_derived_ones(self):
        self.assertEqual(self.cap(), D("1.68") + D("0.87") + D("0.14") + D("0.84"))
        self.assertEqual(self.cap(), D("3.53"))
        self.assertEqual(self.max_runs(), 4)

    def test_retry_at_exactly_the_cap_is_admitted_and_a_fifth_run_is_refused_by_the_run_limit(self):
        fx, actual = self.timed_out_s(5643)
        self.assertEqual((ledger_value(actual, "measured_usd"), ledger_value(actual, "tail_usd")), ("0.87", "0.14"), actual.describe())
        self.assertEqual(ledger_value(actual, "cumulative_usd"), "2.69")
        self.assertIn("live_runs=3 of 4", actual.out)
        self.assertNotIn("LEDGER-OVER-CAP", actual.out)
        run = self.retry(fx)
        self.assertEqual(run.rc, 0, run.describe())  # 1.68 + 0.87 + 0.14 + 0.84 = 3.53 <= 3.53, inclusive
        self.assertIn("LEDGER-RESERVED", run.out, run.describe())
        self.assertNotIn("would exceed the cap", run.text)
        self.assertEqual([r["run_id"] for r in fx.reservations()][-2:], [RUN_ID, "bp-retry-2"])
        self.assertEqual(len(fx.reservations()), 4)
        # the fourth run is on the books: a fifth is refused at the g6-gate by the run limit (it would also break the cap)
        before = fx.ledger_path.read_text()
        fifth = self.retry(fx, run_id="bp-fifth-3", serial="fifth")
        self.assertEqual((fifth.rc, fifth.status, S.last_step(fifth)), (3, "REFUSED", "g6-gate"), fifth.describe())
        self.assertIn("4 live EMR runs are already recorded in the ledger (limit 4)", fifth.text)
        self.assertEqual(fx.ledger_path.read_text(), before, "a refused run reserves nothing")
        self.assertEqual(len(fx.reservations()), 4)

    def test_retry_one_cent_over_the_cap_is_refused_with_the_cumulative_cap_message(self):
        fx, actual = self.timed_out_s(5700)
        self.assertEqual((ledger_value(actual, "measured_usd"), ledger_value(actual, "tail_usd")), ("0.88", "0.14"), actual.describe())
        self.assertEqual(ledger_value(actual, "cumulative_usd"), "2.70")
        self.assertNotIn("LEDGER-OVER-CAP", actual.out, "2.70 is below the cap; only the retry would not fit")
        before = fx.ledger_path.read_text()
        run = self.retry(fx)
        self.assertEqual((run.rc, run.status, S.last_step(run)), (3, "REFUSED", "g6-gate"), run.describe())
        self.assertIn("cumulative estimate 3.54 USD (recorded 2.70 + this run 0.84) would exceed the cap 3.53 USD", run.text)
        self.assertNotIn("live EMR runs are already recorded", run.text, "three runs are on the books: only the cap refuses")
        self.assertEqual(fx.ledger_path.read_text(), before, "a refused run reserves nothing")
        self.assertEqual(len(fx.reservations()), 3)


if __name__ == "__main__":
    unittest.main()

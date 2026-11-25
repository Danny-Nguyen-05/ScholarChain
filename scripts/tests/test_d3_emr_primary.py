"""Phase 15 D3: a separate EMR primary type (r5.xlarge), the 12g entity-resolution heap, the 75-minute S cap and the ledger actuals.

Human decision and go-ahead (docs/agent-runs/phase-15/prompt.md, "D3 decision" and "S run cap and D3 go-ahead", 2026-11-16):
"75 min. Go ahead: r5.xlarge primary, ER heap 12g, S run cap 75 min with the step timeouts you listed, budget.py and the pricing file
updated ... The margins are thin (22.98 / 23.00; ledger 3.35 / 3.36). Record the EMR actuals right after each S run so the pre-R-b
check uses real numbers, not the cap."

Every expected number is derived by hand from the reviewed rates (coordinator, public AWS price lists read 2026-11-16, us-east-2):
r5.xlarge 0.252 EC2 + 0.063 EMR = 0.315 USD/h, m5.xlarge 0.192 + 0.048 = 0.240 USD/h, so primary r5 + one core m5 = 0.555 USD/h.
At the 75-minute cap plus the 900 s idle tail: 0.555 x (4500 + 900) / 3600 = 0.8325, rounded UP to the cent = 0.84.
Session 1's ledger holds 2 x 0.84 = 1.68, so S + one S retry = 1.68 + 0.84 + 0.84 = 3.36 (the coordinator's 3.35 is the unrounded
1.68 + 2 x 0.8325 = 3.345). User decision 2026-11-16, verbatim "Raise cap to 3.53": EMR_CUMULATIVE_CAP_USD is 3.53 = 1.68 + 3.33 h x 0.555 = 1.85,
because --record-actual measures S from cluster creation and adds a 0.14 idle tail per cluster; the retry (0.84) is admitted iff S measured
<= 3.53 - 1.68 - 0.84 - 0.14 = 0.87 (the quoted "3.36" above is the cap before that decision).
Step timeouts at 75 minutes from PIPELINE_STEP_WEIGHTS (5/20/20/5/40/10 percent of 4500 s): 225, 900, 900, 225, 1800, 450 s.
Phase 18 18B (human decisions 2026-11-24 about 5:40 PM CST, docs/agent-runs/phase-18/human-gate.md: "Raise to 120 min (Recommended)" and "Yes,
allow 1 retry"): the live ledger caps are now 5 runs and USD 4.70 and the S run may take 120 minutes (estimate 1.25; step timeouts 360, 1440,
1440, 360, 2880, 720 s). The Phase 15 arithmetic classes below keep the Phase 15 caps (HISTORIC_MAX_RUNS 4, HISTORIC_CAP 3.53) as explicit
fixtures so they still prove the ledger machinery; the Phase 18 classes at the end of the file use the live release.conf values.
Fake aws/yarn/hadoop binaries only; no network, no credentials, no cloud call.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPTS_DIR
from pipeline_helpers import CLUSTER, RUN, PipelineFixture, read
from test_experiment import ExperimentFixture

BUDGET = os.path.join(SCRIPTS_DIR, "lib", "budget.py")
EXPERIMENT_PY = os.path.join(SCRIPTS_DIR, "lib", "experiment.py")
REPO = os.path.dirname(SCRIPTS_DIR)
STEP_SECONDS_75 = (("stage-in", 225), ("hadoop-prep", 900), ("entity-resolution", 900), ("spark-class-origin", 225), ("spark-job", 1800), ("copy-out", 450))
STEP_SECONDS_120 = (("stage-in", 360), ("hadoop-prep", 1440), ("entity-resolution", 1440), ("spark-class-origin", 360), ("spark-job", 2880), ("copy-out", 720))
RATES = ["--rate", "m5.xlarge=0.192,0.048", "--rate", "r5.xlarge=0.252,0.063"]
HISTORIC_MAX_RUNS, HISTORIC_CAP = "4", "3.53"  # Phase 15 values (the arithmetic classes keep their hand-derived numbers)


def run(*args):
    done = subprocess.run([sys.executable, "-I", BUDGET] + [str(a) for a in args], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def conf(rel):
    values = {}
    for line in read(os.path.join(REPO, rel)).splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def groups(master="r5.xlarge", core="m5.xlarge", master_count=1, core_count=1, task=None):
    out = [
        {"InstanceGroupType": "MASTER", "InstanceType": master, "RequestedInstanceCount": master_count, "RunningInstanceCount": master_count},
        {"InstanceGroupType": "CORE", "InstanceType": core, "RequestedInstanceCount": core_count, "RunningInstanceCount": core_count},
    ]
    if task is not None:
        out.append({"InstanceGroupType": "TASK", "InstanceType": core, "RequestedInstanceCount": task, "RunningInstanceCount": task})
    return out


def describe(cluster=CLUSTER, state="TERMINATED", created="2026-11-18T16:00:00Z", ended="2026-11-18T17:30:00Z", instance_groups=None):
    timeline = {"CreationDateTime": created}
    if ended is not None:
        timeline["EndDateTime"] = ended
    return {"Cluster": {"Id": cluster, "Status": {"State": state, "Timeline": timeline}, "InstanceGroups": groups() if instance_groups is None else instance_groups}}


# ---------------------------------------------------------------------------------------------------------------------------------
class PinTests(unittest.TestCase):
    def test_the_er_heap_is_12g(self):
        self.assertEqual(conf("scripts/config/release.conf")["PIPELINE_ER_XMX"], "12g")

    def test_the_r5_rates_and_the_human_confirmation_flag(self):
        pricing = conf("scripts/config/emr-pricing.conf")
        self.assertEqual((pricing["EMR_RATE_EC2_R5_XLARGE"], pricing["EMR_RATE_EMR_R5_XLARGE"]), ("0.252", "0.063"))
        self.assertEqual((pricing["EMR_RATE_EC2_M5_XLARGE"], pricing["EMR_RATE_EMR_M5_XLARGE"]), ("0.192", "0.048"))
        self.assertEqual(pricing["EMR_PRICING_R5_XLARGE_RETRIEVED"], "2026-11-16")
        text = read(os.path.join(REPO, "scripts/config/emr-pricing.conf"))
        self.assertEqual(re.findall(r"^EMR_PRICING_CONFIRMED_BY_HUMAN=(.*)$", text, re.M), ["true"])
        self.assertIn("docs/agent-runs/phase-15/prompt.md", text)
        self.assertIn("ElasticMapReduce/current/us-east-2/index.json", text)
        self.assertIn("AmazonEC2/current/us-east-2/index.csv", text)

    def test_the_ledger_caps_and_step_weights_are_the_ones_the_arithmetic_uses(self):
        release = conf("scripts/config/release.conf")
        self.assertEqual((release["EMR_MAX_LIVE_RUNS"], release["EMR_CUMULATIVE_CAP_USD"], release["PIPELINE_MAX_IDLE_TIMEOUT_SECONDS"]), ("5", "4.70", "900"))  # Phase 18 18B: was 4 and 3.53
        self.assertEqual(release["PIPELINE_STEP_WEIGHTS"], "stage-in=5 hadoop-prep=20 entity-resolution=20 spark-class-origin=5 spark-job=40 copy-out=10")

    def test_terraform_defaults_to_an_r5_primary_and_an_m5_core(self):
        for rel, var in (("infra/terraform/modules/emr/variables.tf", "var.config"), ("infra/terraform/phase12b-variables.tf", "var.emr_config")):
            text = read(os.path.join(REPO, rel))
            self.assertRegex(text, r'primary_instance_type\s*=\s*optional\(string, "r5\.xlarge"\)', rel)
            self.assertRegex(text, r'instance_type\s*=\s*optional\(string, "m5\.xlarge"\)', rel)
            self.assertIn('contains(["m5.xlarge", "r5.xlarge"], %s.primary_instance_type)' % var, text, rel)
            self.assertIn('%s.instance_type == "m5.xlarge"' % var, text, rel)
        main = read(os.path.join(REPO, "infra/terraform/modules/emr/main.tf"))
        master = main[main.index("master_instance_group {"):main.index("core_instance_group {")]
        self.assertRegex(master, r"instance_type\s*=\s*local\.cfg\.primary_instance_type")


# ---------------------------------------------------------------------------------------------------------------------------------
class PerGroupEstimateTests(unittest.TestCase):
    def estimate(self, minutes, primary="r5.xlarge", p_ec2="0.252", p_emr="0.063", budget="3", tasks=0):
        return run(
            "estimate", "--instance-type", "m5.xlarge", "--primary-count", 1, "--core-count", 1, "--task-count", tasks, "--minutes", minutes,
            "--idle-seconds", 900, "--ec2-rate", "0.192", "--emr-rate", "0.048", "--max-run-usd", "3", "--budget-usd", budget,
            "--primary-instance-type", primary, "--primary-ec2-rate", p_ec2, "--primary-emr-rate", p_emr,
        )

    def test_the_75_minute_s_run_is_0_84(self):
        rc, out, _ = self.estimate(75, budget="0.84")
        self.assertEqual(rc, 0, out)
        doc = json.loads(out)
        # 0.315 + 0.240 = 0.555 USD/h; (75 x 60 + 900) / 3600 = 1.5 h; 0.8325 -> 0.84 (rounded up)
        self.assertEqual((doc["hourly_usd"], doc["billed_seconds"], doc["estimate_usd"]), ("0.555", 5400, "0.84"))
        self.assertEqual((doc["primary_instance_type"], doc["primary_ec2_rate_usd_per_hour"], doc["primary_emr_rate_usd_per_hour"]), ("r5.xlarge", "0.252", "0.063"))
        self.assertEqual((doc["instance_type"], doc["instances"]), ("m5.xlarge", 2))
        self.assertIn("primary x (primary EC2 + EMR)", doc["formula"])

    def test_the_120_minute_s_run_is_1_25_and_one_cent_less_budget_refuses(self):
        """Phase 18 18B: (120 x 60 + 900) / 3600 = 2.25 h; 0.555 x 2.25 = 1.24875, rounded UP to the cent = 1.25 (it is 0.84 at 75 minutes)."""
        rc, out, _ = self.estimate(120, budget="1.25")
        self.assertEqual(rc, 0, out)
        doc = json.loads(out)
        self.assertEqual((doc["hourly_usd"], doc["billed_seconds"], doc["estimate_usd"], doc["max_runtime_minutes"]), ("0.555", 8100, "1.25", 120))
        rc, out, _ = self.estimate(120, budget="1.24")
        self.assertEqual(rc, 1, out)
        self.assertIn("estimate 1.25 USD exceeds the declared budget 1.24 USD", out)
        self.assertEqual(json.loads(self.estimate(120)[1])["estimate_usd"], "1.25", "below the per-run cap EMR_MAX_RUN_USD (3)")

    def test_the_coordinators_cap_table_rounded_up(self):
        # 90 min: 0.555 x 1.75 = 0.97125 -> 0.98; 60 min: 0.555 x 1.25 = 0.69375 -> 0.70 (prompt.md: 0.971 / 0.833 / 0.694 unrounded)
        for minutes, want in ((90, "0.98"), (75, "0.84"), (60, "0.70")):
            with self.subTest(minutes=minutes):
                self.assertEqual(json.loads(self.estimate(minutes)[1])["estimate_usd"], want)

    def test_a_task_node_is_priced_at_the_core_type(self):
        # (0.315 + 2 x 0.240) x 1.5 h = 1.1925 -> 1.20
        self.assertEqual(json.loads(self.estimate(75, tasks=1)[1])["estimate_usd"], "1.20")

    def test_without_a_distinct_primary_the_document_is_unchanged(self):
        base = ["estimate", "--instance-type", "m5.xlarge", "--primary-count", 1, "--core-count", 1, "--task-count", 0, "--minutes", 90, "--idle-seconds", 900,
                "--ec2-rate", "0.192", "--emr-rate", "0.048", "--max-run-usd", "3", "--budget-usd", "3"]
        rc1, plain, _ = run(*base)
        rc2, same, _ = run(*(base + ["--primary-instance-type", "m5.xlarge"]))
        self.assertEqual((rc1, rc2), (0, 0))
        self.assertEqual(plain, same)
        self.assertNotIn("primary_instance_type", json.loads(plain))
        self.assertEqual(json.loads(plain)["estimate_usd"], "0.84")  # 2 x 0.240 x 1.75 h = 0.84, as before D3

    def test_a_missing_primary_rate_is_unavailable_never_zero(self):
        rc, out, _ = self.estimate(75, p_ec2="", p_emr="")
        self.assertEqual(rc, 2, out)
        self.assertIn("G6-UNAVAILABLE: the EC2 on-demand hourly rate for the primary type r5.xlarge", out)


# ---------------------------------------------------------------------------------------------------------------------------------
class LedgerBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-d3-ledger-")
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.home = os.path.realpath(os.path.join(self.tmp, "home"))
        self.repo = os.path.realpath(os.path.join(self.tmp, "repo"))
        os.makedirs(self.repo)
        self.ledger = os.path.join(self.home, ".scholarchain", "emr-ledger", "runs.jsonl")
        os.makedirs(os.path.dirname(self.ledger))
        self.cap, self.max_runs = HISTORIC_CAP, HISTORIC_MAX_RUNS
        with open(self.ledger, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": "init", "initialized_by": "fixture", "initialized_utc": "2026-11-13T00:00:00Z"}) + "\n")
        for index, value in enumerate(("0.84", "0.84")):  # Session 1's two runs (prompt.md, P25 coordinator check)
            self.append({"event": "reserve", "run_id": "session-1-%d" % index, "estimate_usd": value, "approval_record_sha256": "%064x" % (index + 1)})

    def append(self, entry):
        with open(self.ledger, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def reserve(self, run_id, estimate="0.84"):
        return run("ledger-reserve", "--root", self.home, "--ledger", self.ledger, "--repo-root", self.repo, "--run-id", run_id, "--estimate", estimate,
                   "--max-runs", self.max_runs, "--cumulative-cap", self.cap, "--action", "run-experiment", "--run-config-sha256", "a" * 64,
                   "--approval-sha256", hashlib.sha256(("approval-" + run_id).encode()).hexdigest(), "--reserved-utc", "2026-11-18T16:00:00Z")

    def check(self, estimate="0.84"):
        return run("ledger-check", "--ledger", self.ledger, "--repo-root", self.repo, "--estimate", estimate, "--max-runs", self.max_runs, "--cumulative-cap", self.cap)

    def record(self, run_id, document, as_of="", expected="", idle=900, rates=None, recorded="2026-11-18T18:00:00Z"):
        path = os.path.join(self.tmp, "describe-%s-%d.json" % (run_id, len(os.listdir(self.tmp))))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(document if isinstance(document, str) else json.dumps(document))
        args = ["ledger-record-actual", "--root", self.home, "--ledger", self.ledger, "--repo-root", self.repo, "--run-id", run_id, "--describe", path,
                "--pending-idle-seconds", idle, "--recorded-utc", recorded, "--max-runs", self.max_runs, "--cumulative-cap", self.cap]
        args += rates if rates is not None else RATES
        if as_of:
            args += ["--as-of-utc", as_of]
        if expected:
            args += ["--expected-cluster-id", expected]
        return run(*args)

    def cumulative(self):
        # A probe check with generous limits only to read the recorded total (cumulative_usd excludes the probe estimate).
        rc, out, _ = run("ledger-check", "--ledger", self.ledger, "--repo-root", self.repo, "--estimate", "0.01", "--max-runs", 99, "--cumulative-cap", "99")
        self.assertEqual(rc, 0, out)
        return re.search(r"live_runs=(\d+) of \d+ cumulative_usd=(\S+)", out).groups()

    def lines(self):
        with open(self.ledger, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]


class LedgerAt75MinutesTests(LedgerBase):
    def test_s_and_one_s_retry_fit_the_3_53_cap_and_nothing_more(self):
        self.assertEqual(self.cap, "3.53")
        self.assertEqual(self.reserve("s-run")[0], 0)  # 1.68 + 0.84 = 2.52
        rc, out, _ = self.reserve("s-retry")  # 2.52 + 0.84 = 3.36 <= 3.53
        self.assertEqual(rc, 0, out)
        self.assertIn("live_runs=4 of 4 cumulative_usd=3.36", out)
        rc, out, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("4 live EMR runs are already recorded in the ledger (limit 4)", out)
        self.assertIn("cumulative estimate 4.20 USD (recorded 3.36 + this run 0.84) would exceed the cap 3.53 USD", out)

    def test_the_largest_per_run_estimate_that_fits_twice_is_0_92(self):
        # 1.68 + 2 x 0.92 = 3.52 <= 3.53 fits; 1.68 + 2 x 0.93 = 3.54 > 3.53 does not (0.925 is the exact limit)
        self.assertEqual(self.reserve("s-run", "0.92")[0], 0)
        self.assertEqual(self.reserve("s-retry", "0.92")[0], 0)
        self.assertEqual(self.cumulative(), ("4", "3.52"))

    def test_one_cent_more_per_run_would_not_fit(self):
        self.assertEqual(self.reserve("s-run", "0.93")[0], 0)  # 1.68 + 0.93 = 2.61
        rc, out, _ = self.reserve("s-retry", "0.93")  # 2.61 + 0.93 = 3.54 > 3.53
        self.assertEqual(rc, 1)
        self.assertIn("cumulative estimate 3.54 USD (recorded 2.61 + this run 0.93) would exceed the cap 3.53 USD", out)

    def test_the_old_90_minute_cap_with_an_r5_primary_would_not_fit(self):
        # 0.98 per run at 90 minutes: 1.68 + 0.98 + 0.98 = 3.64 > 3.53
        self.assertEqual(self.reserve("s-run", "0.98")[0], 0)
        self.assertEqual(self.reserve("s-retry", "0.98")[0], 1)


class RecordActualTests(LedgerBase):
    def test_a_terminated_cluster_replaces_the_estimate_with_the_measured_cost(self):
        self.reserve("s-run")
        # 16:00 -> 16:50 = 3000 s x 0.555 / 3600 = 0.4625 -> 0.47
        rc, out, _ = self.record("s-run", describe(ended="2026-11-18T16:50:00Z"), expected=CLUSTER)
        self.assertEqual(rc, 0, out)
        self.assertIn("LEDGER-ACTUAL: run=s-run cluster=%s window=2026-11-18T16:00:00Z..2026-11-18T16:50:00Z seconds=3000" % CLUSTER, out)
        self.assertIn("hourly_usd=0.555 measured_usd=0.47 tail_seconds=0 tail_usd=0.00 reserved_estimate_usd=0.84", out)
        self.assertIn("cumulative_usd=2.15 (was 2.52; 1 run(s) now counted at actuals)", out)
        self.assertEqual(self.cumulative(), ("3", "2.15"))  # the run count is unchanged
        entry = self.lines()[-1]
        self.assertEqual((entry["event"], entry["measured_usd"], entry["cluster_ended"]), ("actual", "0.47", True))
        self.assertEqual([g["instance_type"] for g in entry["groups"]], ["r5.xlarge", "m5.xlarge"])
        # the retry's check now uses the real number: 2.15 + 0.84 = 2.99
        rc, out, _ = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("cumulative_usd=2.15 this_run_usd=0.84", out)

    def test_a_waiting_cluster_counts_the_measured_time_plus_the_idle_tail_still_to_come(self):
        self.reserve("s-run")
        # 16:00 -> 16:40 = 0.555 x 2/3 = 0.37; tail 900 s x 0.555 / 3600 = 0.13875 -> 0.14; total 1.68 + 0.37 + 0.14 = 2.19
        rc, out, _ = self.record("s-run", describe(state="WAITING", ended=None), as_of="2026-11-18T16:40:00Z")
        self.assertEqual(rc, 0, out)
        self.assertIn("measured_usd=0.37 tail_seconds=900 tail_usd=0.14", out)
        self.assertEqual(self.cumulative(), ("3", "2.19"))

    def test_a_retry_on_the_same_cluster_starts_where_the_previous_actual_ended(self):
        self.reserve("s-run")
        self.assertEqual(self.record("s-run", describe(state="WAITING", ended=None), as_of="2026-11-18T16:40:00Z")[0], 0)
        self.reserve("s-retry")
        # 16:40 -> 17:40 = 1 h x 0.555 = 0.555 -> 0.56; the first actual's provisional tail is replaced: 1.68 + 0.37 + 0.56 = 2.61
        rc, out, _ = self.record("s-retry", describe(ended="2026-11-18T17:40:00Z"))
        self.assertEqual(rc, 0, out)
        self.assertIn("window=2026-11-18T16:40:00Z..2026-11-18T17:40:00Z seconds=3600", out)
        self.assertIn("measured_usd=0.56 tail_seconds=0", out)
        self.assertEqual(self.cumulative(), ("4", "2.61"))

    def test_recording_again_after_termination_supersedes_the_provisional_actual(self):
        self.reserve("s-run")
        self.record("s-run", describe(state="WAITING", ended=None), as_of="2026-11-18T16:40:00Z")
        # 16:00 -> 16:55 = 0.555 x 55/60 = 0.50875 -> 0.51, tail 0: 1.68 + 0.51 = 2.19
        rc, out, _ = self.record("s-run", describe(ended="2026-11-18T16:55:00Z"))
        self.assertEqual(rc, 0, out)
        self.assertIn("window=2026-11-18T16:00:00Z..2026-11-18T16:55:00Z", out)
        self.assertEqual(self.cumulative(), ("3", "2.19"))

    def retry_after_s_measured(self, seconds, wanted_measured):
        """Session 1 (1.68) + S reserved (0.84); S's actual is recorded on a WAITING cluster (measured from creation 16:00:00Z, plus the
        0.14 idle tail); then the retry estimate 0.84 is checked against the cap."""
        self.assertEqual(self.cap, "3.53")
        self.reserve("s-run")
        as_of = "2026-11-18T%02d:%02d:00Z" % (16 + seconds // 3600, seconds % 3600 // 60)
        rc, out, _ = self.record("s-run", describe(state="WAITING", ended=None), as_of=as_of)
        self.assertEqual(rc, 0, out)
        self.assertIn("measured_usd=%s tail_seconds=900 tail_usd=0.14" % wanted_measured, out)
        return self.check("0.84")

    def test_the_retry_is_admitted_when_s_measured_0_87_and_refused_at_0_88(self):
        # 5640 s x 0.555 / 3600 = 0.8695 -> 0.87; tail 900 s x 0.555 / 3600 = 0.13875 -> 0.14
        # recorded 1.68 + 0.87 + 0.14 = 2.69; the retry 0.84 -> 3.53 <= 3.53 (inclusive): admitted
        rc, out, _ = self.retry_after_s_measured(5640, "0.87")
        self.assertEqual(rc, 0, out)
        self.assertIn("cumulative_usd=2.69 this_run_usd=0.84", out)
        rc, out, _ = self.reserve("s-retry")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.cumulative(), ("4", "3.53"))  # 1.68 + 0.87 + 0.84 + 0.14 = 3.53 exactly

    def test_the_retry_is_refused_when_s_measured_0_88(self):
        # 5700 s x 0.555 / 3600 = 0.87875 -> 0.88; recorded 1.68 + 0.88 + 0.14 = 2.70; 2.70 + 0.84 = 3.54 > 3.53: refused
        rc, out, _ = self.retry_after_s_measured(5700, "0.88")
        self.assertEqual(rc, 1)
        self.assertIn("cumulative estimate 3.54 USD (recorded 2.70 + this run 0.84) would exceed the cap 3.53 USD", out)
        rc, out, _ = self.reserve("s-retry")
        self.assertEqual(rc, 1)
        self.assertEqual(self.cumulative(), ("3", "2.70"), "a refused reservation writes nothing")

    def test_epoch_second_timestamps_are_accepted(self):
        self.reserve("s-run")
        doc = describe()
        doc["Cluster"]["Status"]["Timeline"] = {"CreationDateTime": 1795017600.0, "EndDateTime": 1795017600.0 + 3600}
        rc, out, _ = self.record("s-run", doc)
        self.assertEqual(rc, 0, out)
        self.assertIn("seconds=3600", out)
        self.assertIn("measured_usd=0.56", out)

    def test_refusals_leave_the_ledger_unchanged(self):
        self.reserve("s-run")
        self.reserve("s-other")
        self.assertEqual(self.record("s-other", describe(state="WAITING", ended=None), as_of="2026-11-18T16:30:00Z")[0], 0)
        before = read(self.ledger)
        cases = {
            "no reservation": (("not-reserved", describe()), {}, "has no reservation in the ledger"),
            "no reviewed rate for the primary type": (("s-run", describe()), {"rates": ["--rate", "m5.xlarge=0.192,0.048"]}, "no reviewed hourly rate for r5.xlarge (MASTER group)"),
            "another cluster than the run manifest": (("s-run", describe(cluster="j-OTHERCLUSTER1")), {"expected": CLUSTER}, "ran on %s (run manifest)" % CLUSTER),
            "not ended and no --as-of-utc": (("s-run", describe(cluster="j-SECONDCLUSTER", state="WAITING", ended=None)), {}, "--as-of-utc"),
            "--as-of-utc before creation": (("s-run", describe(cluster="j-SECONDCLUSTER", state="WAITING", ended=None)), {"as_of": "2026-11-18T15:00:00Z"}, "before it starts"),
            "--as-of-utc in the future": (("s-run", describe(cluster="j-SECONDCLUSTER", state="WAITING", ended=None)), {"as_of": "2026-11-19T18:00:00Z"}, "lies in the future"),
            "terminated without an end time": (("s-run", describe(ended=None)), {}, "has no Status.Timeline.EndDateTime"),
            "a time without a zone": (("s-run", describe(created="2026-11-18T16:00:00")), {}, "has no time zone"),
            "no primary instance": (("s-run", describe(instance_groups=groups(master_count=0))), {}, "the MASTER group reports no instance"),
            "no instance groups": (("s-run", describe(instance_groups=[])), {}, "no Cluster.InstanceGroups"),
            "not JSON": (("s-run", "{not json"), {}, "unreadable or not JSON"),
            "a window overlapping a later run on the cluster": (("s-run", describe(state="WAITING", ended=None)), {"as_of": "2026-11-18T16:20:00Z"}, "before it starts"),
        }
        for label, ((run_id, document), kwargs, needle) in cases.items():
            with self.subTest(label):
                rc, out, _ = self.record(run_id, document, **kwargs)
                self.assertEqual(rc, 1, out)
                self.assertTrue(out.startswith("G6-REFUSED: "), out)
                self.assertIn(needle, out)
                self.assertEqual(read(self.ledger), before)

    def test_superseding_after_another_run_recorded_on_the_cluster_is_refused(self):
        self.reserve("s-run")
        self.record("s-run", describe(state="WAITING", ended=None), as_of="2026-11-18T16:40:00Z")
        self.reserve("s-retry")
        self.record("s-retry", describe(state="WAITING", ended=None), as_of="2026-11-18T17:20:00Z")
        rc, out, _ = self.record("s-run", describe(ended="2026-11-18T17:35:00Z"))
        self.assertEqual(rc, 1)
        self.assertIn("another run recorded an actual on %s after run s-run" % CLUSTER, out)

    def test_an_actual_line_for_an_unreserved_run_makes_the_ledger_unreadable(self):
        self.append({"event": "actual", "run_id": "ghost", "cluster_id": CLUSTER, "measured_usd": "0.10", "tail_usd": "0.00",
                     "measured_from_utc": "2026-11-18T16:00:00Z", "measured_to_utc": "2026-11-18T16:10:00Z"})
        rc, out, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("ledger line 4 is malformed", out)

    def test_an_actual_above_the_cap_is_recorded_and_flagged(self):
        self.reserve("s-run")
        self.reserve("s-retry")
        # 16:00 -> 19:00 = 3 h x 0.555 = 1.665 -> 1.67: 1.68 + 1.67 + 0.84 = 4.19 > 3.53
        rc, out, _ = self.record("s-run", describe(ended="2026-11-18T19:00:00Z"), recorded="2026-11-18T19:05:00Z")
        self.assertEqual(rc, 0, out)
        self.assertIn("LEDGER-OVER-CAP: the cumulative total 4.19 USD exceeds the cap 3.53 USD", out)
        self.assertEqual(self.check()[0], 1)


class Phase18LedgerTests(LedgerBase):
    """Phase 18 18B, the live release.conf caps (5 runs, USD 4.70) against the ledger as it stood on 2026-11-24 (3 runs, USD 2.05 recorded:
    the fixture is Session 1's 0.84 + 0.84 plus a third run recorded at 0.37; only the sum and the count matter to admission).
    Admission (scripts/lib/budget.py ledger_problems): refused when runs >= max runs or recorded + estimate > cap (inclusive).
    Per-run estimate at the 120-minute total cap: 1.25. Run 4: 2.05 + 1.25 = 3.30. Run 5 after run 4 recorded at its measured cost m (plus the
    0.14 idle tail while the cluster is up): 2.05 + m + 0.14 + 1.25 <= 4.70, i.e. m <= 1.26 (m = 1.25 gives 4.69). A sixth run: the count."""

    def setUp(self):
        super().setUp()
        release = conf("scripts/config/release.conf")
        self.cap, self.max_runs = release["EMR_CUMULATIVE_CAP_USD"], release["EMR_MAX_LIVE_RUNS"]
        self.append({"event": "reserve", "run_id": "session-2-run-3", "estimate_usd": "0.37", "approval_record_sha256": "%064x" % 3})
        self.assertEqual(self.cumulative(), ("3", "2.05"))

    def run_4_measured(self, seconds):
        """Reserve run 4 at 1.25, then record its actual on a WAITING cluster created 16:00:00Z, measured to 16:00 + seconds."""
        rc, out, _ = self.reserve("run-4", "1.25")
        self.assertEqual(rc, 0, out)
        self.assertIn("live_runs=4 of 5 cumulative_usd=3.30", out)  # 2.05 + 1.25
        as_of = "2026-11-18T%02d:%02d:00Z" % (16 + seconds // 3600, seconds % 3600 // 60)
        rc, out, _ = self.record("run-4", describe(state="WAITING", ended=None), as_of=as_of, recorded="2026-11-18T20:00:00Z")
        self.assertEqual(rc, 0, out)
        return out

    def test_the_live_pins_are_five_runs_and_4_70_and_the_project_constants_are_unchanged(self):
        release = conf("scripts/config/release.conf")
        self.assertEqual((release["EMR_MAX_RUN_USD"], release["EMR_MAX_LIVE_RUNS"], release["EMR_CUMULATIVE_CAP_USD"]), ("3", "5", "4.70"))
        self.assertEqual((release["PIPELINE_MAX_RUNTIME_MINUTES"], release["PIPELINE_MAX_IDLE_TIMEOUT_SECONDS"]), ("180", "900"))
        self.assertEqual((release["PRESPEND_MIN_HEADROOM_USD"], release["PRESPEND_PROJECT_CEILING_USD"], release["PRESPEND_MAX_AGE_HOURS"]), ("2", "25", "24"))
        text = read(os.path.join(REPO, "scripts/config/release.conf"))
        self.assertIn("docs/agent-runs/phase-18/human-gate.md", text)
        self.assertIn('"Raise to 120 min (Recommended)"', text)
        self.assertIn('"Yes, allow 1 retry"', text)
        self.assertEqual(int(release["EMR_CUMULATIVE_CAP_USD"].replace(".", "")), 205 + 125 + 14 + 125 + 1, "4.69 plus one cent of room")

    def test_run_4_at_the_120_minute_estimate_is_admitted(self):
        rc, out, _ = self.check("1.25")
        self.assertEqual(rc, 0, out)
        self.assertIn("LEDGER: live_runs=3 of 5 cumulative_usd=2.05 this_run_usd=1.25 cap_usd=4.70", out)
        self.assertEqual(self.reserve("run-4", "1.25")[0], 0)

    def test_run_5_is_admitted_when_run_4_measured_its_full_estimate_and_a_sixth_is_refused(self):
        # 8100 s x 0.555 / 3600 = 1.24875 -> 1.25; tail 900 s x 0.555 / 3600 = 0.13875 -> 0.14; recorded 2.05 + 1.25 + 0.14 = 3.44
        out = self.run_4_measured(8100)
        self.assertIn("measured_usd=1.25 tail_seconds=900 tail_usd=0.14", out)
        self.assertEqual(self.cumulative(), ("4", "3.44"))
        rc, out, _ = self.check("1.25")  # 3.44 + 1.25 = 4.69 <= 4.70
        self.assertEqual(rc, 0, out)
        rc, out, _ = self.reserve("run-5", "1.25")
        self.assertEqual(rc, 0, out)
        self.assertIn("live_runs=5 of 5 cumulative_usd=4.69", out)
        before = read(self.ledger)
        rc, out, _ = self.check("0.01")
        self.assertEqual(rc, 1)
        self.assertIn("5 live EMR runs are already recorded in the ledger (limit 5)", out)
        rc, out, _ = self.reserve("run-6", "0.01")
        self.assertEqual(rc, 1)
        self.assertIn("5 live EMR runs are already recorded in the ledger (limit 5)", out)
        self.assertEqual(read(self.ledger), before, "a refused reservation writes nothing")

    def test_run_5_is_still_admitted_when_run_4_measured_1_26_and_refused_at_1_27(self):
        # 8160 s -> 1.258 -> 1.26: 2.05 + 1.26 + 0.14 = 3.45; 3.45 + 1.25 = 4.70 <= 4.70 (inclusive)
        out = self.run_4_measured(8160)
        self.assertIn("measured_usd=1.26 tail_seconds=900 tail_usd=0.14", out)
        rc, out, _ = self.check("1.25")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.reserve("run-5", "1.25")[0], 0)
        self.assertEqual(self.cumulative(), ("5", "4.70"))

    def test_run_5_is_refused_when_run_4_measured_1_27(self):
        # 8220 s -> 1.26725 -> 1.27: 2.05 + 1.27 + 0.14 = 3.46; 3.46 + 1.25 = 4.71 > 4.70
        out = self.run_4_measured(8220)
        self.assertIn("measured_usd=1.27 tail_seconds=900 tail_usd=0.14", out)
        rc, out, _ = self.check("1.25")
        self.assertEqual(rc, 1)
        self.assertIn("cumulative estimate 4.71 USD (recorded 3.46 + this run 1.25) would exceed the cap 4.70 USD", out)
        rc, out, _ = self.reserve("run-5", "1.25")
        self.assertEqual(rc, 1)
        self.assertEqual(self.cumulative(), ("4", "3.46"), "a refused reservation writes nothing")

    def test_the_old_75_minute_cap_arithmetic_would_have_refused_run_5_by_the_count(self):
        # Without the Phase 18 change: 4 runs maximum, so run 4 fills the ledger and run 5 is refused whatever it costs
        self.assertEqual(self.reserve("run-4", "1.25")[0], 0)
        rc, out, _ = run("ledger-check", "--ledger", self.ledger, "--repo-root", self.repo, "--estimate", "0.01", "--max-runs", HISTORIC_MAX_RUNS, "--cumulative-cap", "99")
        self.assertEqual(rc, 1)
        self.assertIn("4 live EMR runs are already recorded in the ledger (limit 4)", out)


# ---------------------------------------------------------------------------------------------------------------------------------
class PipelinePrimaryTests(PipelineFixture):
    S_OVER = {"--primary-instance-type": "r5.xlarge", "--max-task-count": "0", "--max-runtime-minutes": "75", "--budget-usd": "0.84"}

    def setUp_clean(self):
        for path in (self.log, self.log + ".steps"):
            if os.path.exists(path):
                open(path, "w").close()

    def test_the_75_minute_dry_run_has_the_listed_step_timeouts_and_the_0_84_estimate(self):
        result = self.dry(**self.S_OVER)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("ESTIMATE-USD: 0.84", result.stdout)
        for name, seconds in STEP_SECONDS_75:
            self.assertIn("STEP-TIMEOUT: %s %ss " % (name, seconds), result.stdout)
            self.assertIn("PLAN: step %s: timeout=%ds" % (name, seconds), result.stdout)
        self.assertEqual(sum(s for _, s in STEP_SECONDS_75), 75 * 60)
        self.assertIn("PLAN: primary-instance-type: r5.xlarge (core and task: m5.xlarge)", result.stdout)
        self.assertIn("PLAN: instance-type: m5.xlarge primary=1 core=1 max-task=0 max-capacity=2", result.stdout)
        self.assertIn("ER_XMX=12g", result.stdout)
        self.assertIn("a r5.xlarge primary and only m5.xlarge core and task groups", result.out)
        self.assertEqual(self.calls(), [])

    def test_the_120_minute_dry_run_has_the_phase_18_step_timeouts_and_the_1_25_estimate(self):
        """Phase 18 18B: 7200 s x weights 5/20/20/5/40/10 percent = 360, 1440, 1440, 360, 2880 (spark-job, 48 minutes), 720 s; estimate 1.25."""
        result = self.dry(**dict(self.S_OVER, **{"--max-runtime-minutes": "120", "--budget-usd": "1.25"}))
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("ESTIMATE-USD: 1.25", result.stdout)
        self.assertIn("PLAN: max-runtime-minutes: 120", result.stdout)
        for name, seconds in STEP_SECONDS_120:
            self.assertIn("STEP-TIMEOUT: %s %ss " % (name, seconds), result.stdout)
            self.assertIn("PLAN: step %s: timeout=%ds" % (name, seconds), result.stdout)
        self.assertEqual(sum(s for _, s in STEP_SECONDS_120), 120 * 60)
        self.assertEqual(dict(STEP_SECONDS_120)["spark-job"], 48 * 60)
        self.assertEqual(self.calls(), [])
        # the declared budget must cover the estimate: 1.24 is refused before any cloud call
        low = self.dry(**dict(self.S_OVER, **{"--max-runtime-minutes": "120", "--budget-usd": "1.24"}))
        self.assertNotEqual(low.rc, 0, low.out)
        self.assertEqual(self.calls(), [])

    def test_the_120_minute_execute_is_admitted_as_run_4_and_run_5_and_refused_as_run_6(self):
        """Phase 18 18B at the execute gate, live release.conf caps (5 runs, USD 4.70), estimate 1.25. Ledger as of 2026-11-24: 3 runs, 2.05.
        Run 4: 2.05 + 1.25 = 3.30. Run 5 after run 4 recorded at 1.25 plus the 0.14 tail (3.44): 3.44 + 1.25 = 4.69 <= 4.70. Run 6: the count."""
        plan = dict(self.S_OVER, **{"--max-runtime-minutes": "120", "--budget-usd": "1.25"})
        override = {"APPROVED_BUDGET_USD": "1.25", "APPROVED_MAX_CAPACITY": "2", "APPROVED_MAX_RUNTIME_MINUTES": "120"}
        for serial, (label, ledger, rc, needle) in enumerate((
            ("run 4", ["0.84", "0.84", "0.37"], 0, None),
            ("run 5", ["0.84", "0.84", "0.37", "1.39"], 0, None),  # 3.44 recorded
            ("run 5 two cents over", ["0.84", "0.84", "0.37", "1.41"], 3, "cumulative estimate 4.71 USD (recorded 3.46 + this run 1.25) would exceed the cap 4.70 USD"),
            ("run 6", ["0.84", "0.84", "0.37", "1.39", "0.01"], 3, "5 live EMR runs are already recorded in the ledger (limit 5)"),
        )):
            with self.subTest(label):
                self.setUp_clean()
                self.write_ledger(ledger)
                result = self.execute(self.ready(serial=serial, record_override=override, **dict(plan, **{"--run-id": "bp-test-%04d" % (serial + 40)})), FAKE_EMR_GROUPS=json.dumps(groups()))
                self.assertEqual(result.rc, rc, result.out)
                if needle:
                    self.assertIn(needle, result.out)
                    self.assertEqual(self.submitted_steps(), [])
                else:
                    self.assertIn("ESTIMATE-USD: 1.25", result.stdout)
                    self.assertEqual(len(self.submitted_steps()), 6)

    def test_the_primary_type_is_part_of_the_approved_run_configuration(self):
        self.assertNotEqual(self.run_config_sha(**self.S_OVER), self.run_config_sha(**dict(self.S_OVER, **{"--primary-instance-type": "m5.xlarge"})))
        self.assertEqual(self.run_config_sha(**dict(self.S_OVER, **{"--primary-instance-type": "m5.xlarge"})), self.run_config_sha(**dict(self.S_OVER, drop=("--primary-instance-type",))))

    def test_a_primary_type_without_a_reviewed_rate_is_not_runnable(self):
        result = self.dry(**dict(self.S_OVER, **{"--primary-instance-type": "r5.2xlarge"}))
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("ESTIMATE-USD: unavailable (rates EMR_RATE_EC2_M5_XLARGE, EMR_RATE_EMR_M5_XLARGE, EMR_RATE_EC2_R5_2XLARGE and EMR_RATE_EMR_R5_2XLARGE", result.stdout)
        self.assertIn("or the primary r5.2xlarge", result.out)

    def test_a_malformed_primary_type_is_a_usage_error_before_any_estimate(self):
        for bad in ("R5.XLARGE", "r5 xlarge", "r5.xlarge;x", "x[0]"):
            with self.subTest(bad):
                result = self.dry(**dict(self.S_OVER, **{"--primary-instance-type": bad}))
                self.assertEqual(result.rc, 2, result.out)
                self.assertIn("--primary-instance-type must look like r5.xlarge", result.out)
                self.assertNotIn("ESTIMATE-USD", result.stdout)

    def test_execute_checks_the_primary_and_the_core_type_exactly(self):
        cases = {
            "r5 primary, m5 core (the reviewed pair)": (groups(), 0, None),
            "m5 primary": (groups(master="m5.xlarge"), 4, "MASTER group uses m5.xlarge, not the approved r5.xlarge"),
            "r5 core": (groups(core="r5.xlarge"), 4, "CORE group uses r5.xlarge, not the approved m5.xlarge"),
            "r5 task": (groups() + [{"InstanceGroupType": "TASK", "InstanceType": "r5.xlarge", "RequestedInstanceCount": 0, "RunningInstanceCount": 0}], 4, "TASK group uses r5.xlarge, not the approved m5.xlarge"),
        }
        for serial, (label, (instance_groups, rc, needle)) in enumerate(cases.items()):
            with self.subTest(label):
                self.setUp_clean()
                self.write_ledger([])
                args = self.ready(serial=serial, record_override={"APPROVED_BUDGET_USD": "0.84", "APPROVED_MAX_CAPACITY": "2", "APPROVED_MAX_RUNTIME_MINUTES": "75"}, **self.S_OVER)
                result = self.execute(args, FAKE_EMR_GROUPS=json.dumps(instance_groups))
                self.assertEqual(result.rc, rc, result.out)
                if needle:
                    self.assertIn(needle, result.out)
                    self.assertEqual(self.submitted_steps(), [])
                else:
                    self.assertIn("type=m5.xlarge primary_type=r5.xlarge", result.out)
                    self.assertEqual(len(self.submitted_steps()), 6)

    def test_record_actual_after_a_run_uses_the_run_manifest_and_makes_no_cloud_call(self):
        args = self.ready(record_override={"APPROVED_BUDGET_USD": "0.84", "APPROVED_MAX_CAPACITY": "2", "APPROVED_MAX_RUNTIME_MINUTES": "75"}, **self.S_OVER)
        result = self.execute(args, FAKE_EMR_GROUPS=json.dumps(groups()))
        self.assertEqual(result.rc, 0, result.out)
        self.setUp_clean()
        path = os.path.join(self.tmp, "describe-after-s.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(describe(ended="2026-11-18T16:50:00Z"), handle)
        result = self.run_script("run-bounded-pipeline.sh", "--record-actual", "--run-id", RUN, "--describe", path)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("LEDGER-ACTUAL: run=%s cluster=%s" % (RUN, CLUSTER), result.stdout)
        self.assertIn("measured_usd=0.47 tail_seconds=0 tail_usd=0.00 reserved_estimate_usd=0.84", result.stdout)
        self.assertIn("cumulative_usd=0.47 (was 0.84; 1 run(s) now counted at actuals) cap_usd=4.70", result.stdout)
        self.assertIn("RESULT: PASS", result.stdout)
        self.assertEqual(self.calls(), [], "--record-actual makes no aws call")
        with open(self.ledger_path(), encoding="utf-8") as handle:
            entries = [json.loads(line) for line in handle]
        self.assertEqual([e["event"] for e in entries], ["init", "reserve", "actual"])
        self.assertEqual(entries[-1]["run_id"], RUN)
        # the describe file of another cluster is refused against the run manifest
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(describe(cluster="j-OTHERCLUSTER1"), handle)
        result = self.run_script("run-bounded-pipeline.sh", "--record-actual", "--run-id", RUN, "--describe", path)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("ran on %s (run manifest)" % CLUSTER, result.out)

    def test_record_actual_usage_and_preconditions(self):
        path = os.path.join(self.tmp, "describe.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(describe(), handle)
        result = self.run_script("run-bounded-pipeline.sh", "--record-actual", "--describe", path)
        self.assertEqual(result.rc, 2, result.out)
        self.assertIn("--record-actual needs --run-id and --describe", result.out)
        result = self.run_script("run-bounded-pipeline.sh", "--record-actual", "--run-id", RUN, "--describe", path, "--execute")
        self.assertEqual(result.rc, 2, result.out)
        result = self.run_script("run-bounded-pipeline.sh", "--record-actual", "--run-id", "../../etc-x", "--describe", path)
        self.assertEqual(result.rc, 2, result.out)
        self.assertIn("--run-id must be a plain run id", result.out)
        result = self.run_script("run-bounded-pipeline.sh", "--record-actual", "--run-id", "bp-never-ran-1", "--describe", path)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("no run manifest", result.out)
        result = self.run_script("run-bounded-pipeline.sh", *(self.pipeline_args() + ["--describe", path]))
        self.assertEqual(result.rc, 2, result.out)
        self.assertIn("--describe and --as-of-utc belong to --record-actual", result.out)
        self.assertEqual(self.calls(), [])


# ---------------------------------------------------------------------------------------------------------------------------------
class ExperimentPrimaryTests(ExperimentFixture):
    def s_manifest(self, **pipeline):
        document = self.manifest()
        document["budget"].update({"max_runtime_minutes": 75, "max_usd": 0.84, "max_capacity": 2})
        document["pipeline"].update({"instance_type": "m5.xlarge", "primary_instance_type": "r5.xlarge", "core_count": 1, "max_task_count": 0})
        document["pipeline"].update(pipeline)
        return self.commit_manifest(document)

    def test_a_synthetic_s_manifest_dry_runs_with_the_75_minute_step_timeouts(self):
        result = self.experiment(manifest=self.s_manifest())
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("EXPERIMENT-LIMITS: max_usd=0.84 max_runtime_minutes=75 max_capacity=2", result.stdout)
        self.assertIn("pipeline| ESTIMATE-USD: 0.84", result.stdout)
        for name, seconds in STEP_SECONDS_75:
            self.assertIn("pipeline| STEP-TIMEOUT: %s %ss " % (name, seconds), result.stdout)
        self.assertIn("pipeline| PLAN: primary-instance-type: r5.xlarge (core and task: m5.xlarge)", result.stdout)
        self.assertIn("ER_XMX=12g", result.stdout)
        self.assertEqual(self.calls(), [])

    def test_a_synthetic_s_manifest_at_120_minutes_dry_runs_with_the_phase_18_step_timeouts(self):
        document = self.manifest()
        document["budget"].update({"max_runtime_minutes": 120, "max_usd": 1.25, "max_capacity": 2})
        document["pipeline"].update({"instance_type": "m5.xlarge", "primary_instance_type": "r5.xlarge", "core_count": 1, "max_task_count": 0})
        result = self.experiment(manifest=self.commit_manifest(document))
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("EXPERIMENT-LIMITS: max_usd=1.25 max_runtime_minutes=120 max_capacity=2", result.stdout)
        self.assertIn("pipeline| ESTIMATE-USD: 1.25", result.stdout)
        for name, seconds in STEP_SECONDS_120:
            self.assertIn("pipeline| STEP-TIMEOUT: %s %ss " % (name, seconds), result.stdout)
        self.assertEqual(self.calls(), [])

    def test_the_manifest_primary_type_becomes_the_pipeline_flag(self):
        path = self.s_manifest()
        done = subprocess.run([sys.executable, "-I", EXPERIMENT_PY, "args", "--manifest", path], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        lines = done.stdout.splitlines()
        self.assertEqual(lines[lines.index("--primary-instance-type") + 1], "r5.xlarge")
        self.assertEqual(lines[lines.index("--instance-type") + 1], "m5.xlarge")
        self.assertEqual(lines[lines.index("--max-runtime-minutes") + 1], "75")
        with open(os.path.join(SCRIPTS_DIR, "tests", "fixtures", "experiment", "valid-manifest.json"), encoding="utf-8") as handle:
            plain = self.commit_manifest(json.load(handle), rel="experiments/fixture/plain.json")
        done = subprocess.run([sys.executable, "-I", EXPERIMENT_PY, "args", "--manifest", plain], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("--primary-instance-type", done.stdout.splitlines(), "no primary field: the pipeline default (the core type) applies")

    def test_a_malformed_primary_type_is_rejected_by_the_schema(self):
        result = self.experiment(manifest=self.s_manifest(primary_instance_type="R5.XLARGE"))
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("pipeline.primary_instance_type must look like r5.xlarge", result.out)


if __name__ == "__main__":
    unittest.main()

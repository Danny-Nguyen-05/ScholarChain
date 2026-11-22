#!/usr/bin/env python3
"""Tests for experiments/scripts/eval16_perf.py, eval16_factory.py, eval16_retrieval.py and eval16_repro.py (Phase 16 groups 3, 5, 6, 7; offline, stdlib).

Run from the repository root:   python3 -I -m unittest discover -s experiments/tests -v

Every fixture is small and hand-built; each expected value is derived below by hand from the rule in the script's docstring, not by running the code.
No test reads git-ignored raw evidence: the scripts' own end-to-end runs are separate commands (see the Phase 16 evidence).

Hand derivations used more than once
  nearest-rank percentile of [1..10]: p50 -> rank ceil(0.5*10) = 5 -> 5; p95 -> rank ceil(9.5) = 10 -> 10; p99 -> rank 10 -> 10; of [1..100]: p95 -> 95, p99 -> 99.
  load group (seconds = 2): 6 requests = 4 ok at 10/20/30/40 ms, one 503 at 5000 ms, one 429 at 1 ms. The 429 is excluded from served, throughput, errors and latency:
  served 5, throughput 5/2 = 2.5, one failure, error rate 1/5 = 0.2; latency over responses [10,20,30,40,5000]: p50 rank 3 -> 30, p95 rank 5 -> 5000; over 2xx [10,20,30,40]: p50 rank 2 -> 20.
  DCG with ranks i = 1..K and gain/log2(i+1): retrieved [b,a,c], gains {a:3,b:2,c:1}: DCG = 2/1 + 3/log2(3) + 1/2; ideal [3,2,1]: 3/1 + 2/log2(3) + 1/2.
  Wilson 95% lower bound for 5 of 5: n / (n + z^2) = 5 / (5 + 3.8416) = 0.5655.
"""
import contextlib
import importlib.util
import io
import json
import math
import os
import shutil
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, relative))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


perf = load("eval16_perf", "experiments/scripts/eval16_perf.py")
factory = load("eval16_factory", "experiments/scripts/eval16_factory.py")
retrieval = load("eval16_retrieval", "experiments/scripts/eval16_retrieval.py")
repro = load("eval16_repro", "experiments/scripts/eval16_repro.py")


class PercentileTests(unittest.TestCase):
    def test_nearest_rank_on_one_to_ten(self):
        values = list(range(1, 11))
        self.assertEqual(perf.percentile(values, 50), 5)
        self.assertEqual(perf.percentile(values, 95), 10)
        self.assertEqual(perf.percentile(values, 99), 10)

    def test_nearest_rank_on_one_to_hundred(self):
        values = list(range(1, 101))
        self.assertEqual((perf.percentile(values, 50), perf.percentile(values, 95), perf.percentile(values, 99)), (50, 95, 99))

    def test_single_value_and_empty(self):
        self.assertEqual(perf.percentile([7.5], 99), 7.5)
        self.assertIsNone(perf.percentile([], 50))

    def test_matches_the_load_generator_rule_on_a_skewed_list(self):
        # n = 20: p95 rank ceil(19.0) = 19; p50 rank 10. The last value is an outlier that only p99/p100 sees.
        values = sorted([1] * 18 + [2, 1000])
        self.assertEqual(perf.percentile(values, 50), 1)
        self.assertEqual(perf.percentile(values, 95), 2)
        self.assertEqual(perf.percentile(values, 99), 1000)

    def test_median_and_bootstrap_are_deterministic(self):
        self.assertEqual(perf.median([5, 1, 3]), 3)
        self.assertEqual(perf.median([1, 2, 3, 4]), 2.5)
        values = [10, 20, 30, 40, 50, 60, 70, 80]
        first = perf.bootstrap_ci(values, perf.median, "seed-a")
        self.assertEqual(first, perf.bootstrap_ci(values, perf.median, "seed-a"))
        self.assertLessEqual(first[0], first[1])
        self.assertTrue(10 <= first[0] and first[1] <= 80)
        self.assertIsNone(perf.bootstrap_ci([1], perf.median, "x"))


class LoadStatsTests(unittest.TestCase):
    ROWS = [("p", 200, "ok", 10.0, "2026-01-01T00:00:00.100Z", "semantic"), ("p", 200, "ok", 20.0, "2026-01-01T00:00:00.200Z", "semantic"),
            ("p", 200, "ok", 30.0, "2026-01-01T00:00:01.100Z", "semantic"), ("p", 200, "ok", 40.0, "2026-01-01T00:00:01.200Z", "semantic"),
            ("p", 503, "server_error", 5000.0, "2026-01-01T00:00:01.300Z", "semantic"), ("p", 429, "throttled", 1.0, "2026-01-01T00:00:01.400Z", "semantic")]

    def test_group_stats_excludes_429_and_counts_failures(self):
        s = perf.group_stats(self.ROWS, 2.0)
        self.assertEqual((s["requests"], s["served"], s["successful"], s["rate_limited_429"]), (6, 5, 4, 1))
        self.assertEqual(s["throughput_rps"], 2.5)
        self.assertEqual((s["failures_5xx_or_transport"], s["error_rate_5xx_or_transport"]), (1, 0.2))
        self.assertEqual((s["latency_ms_all_responses"]["p50"], s["latency_ms_all_responses"]["p95"], s["latency_ms_all_responses"]["n"]), (30.0, 5000.0, 5))
        self.assertEqual((s["latency_ms_2xx"]["p50"], s["latency_ms_2xx"]["n"]), (20.0, 4))
        self.assertEqual(s["peak_success_rps_1s"], 2)  # two ok per whole second
        self.assertEqual(s["status_codes"], {"200": 4, "429": 1, "503": 1})

    def test_timeout_counts_as_failure_but_has_no_latency(self):
        rows = [("p", 200, "ok", 10.0, "2026-01-01T00:00:00.000Z", "r"), ("p", 0, "timeout", 10000.0, "2026-01-01T00:00:00.500Z", "r")]
        s = perf.group_stats(rows, 1.0)
        self.assertEqual(s["failures_5xx_or_transport"], 1)
        self.assertEqual(s["latency_ms_all_responses"]["n"], 1)

    def test_error_burst_window(self):
        rows = list(self.ROWS) + [("q", 504, "server_error", 5100.0, "2026-01-01T00:00:09.000Z", "r")]
        burst = perf.error_burst(rows, "p")
        self.assertEqual(burst["errors"], 1)
        self.assertEqual(burst["first_error_started_utc"], "2026-01-01T00:00:01.300Z")
        self.assertIsNone(perf.error_burst(rows, "none"))

    def test_minute_timeline(self):
        rows = [("p", 200, "ok", 10.0, "2026-01-01T00:00:10.000Z", "r"), ("p", 503, "server_error", 90.0, "2026-01-01T00:00:50.000Z", "r"),
                ("p", 200, "ok", 30.0, "2026-01-01T00:01:05.000Z", "r")]
        tl = perf.minute_timeline(rows, {"p": ("a", "b", 5)})
        self.assertEqual([(t["minute_utc"], t["requests"], t["errors_5xx_or_transport"], t["level"]) for t in tl], [("2026-01-01T00:00:00Z", 2, 1, 5), ("2026-01-01T00:01:00Z", 1, 0, 5)])

    def test_parse_utc_round_trip(self):
        self.assertEqual(perf.parse_utc("1970-01-01T00:00:01.500Z"), 1.5)
        self.assertEqual(perf.parse_utc("1970-01-01T00:01:00Z"), 60.0)
        self.assertEqual(perf.fmt_utc(60.0), "1970-01-01T00:01:00Z")


class ElasticityAndRecoveryTests(unittest.TestCase):
    POLL = textwrap.dedent("""\
        2026-11-18T20:40:00Z
        2026-11-18T20:41:00Z
        2026-11-18T20:51:00Z 1\t1\t0
        2026-11-18T20:52:00Z 2\t1\t1
        2026-11-18T20:53:00Z 2\t2\t0
        2026-11-18T21:00:00Z 2\t2\t0
        2026-11-18T21:01:00Z
        2026-11-18T21:15:00Z 1\t1\t0
        """).split("\n")

    def test_parse_poll_lines(self):
        polls = perf.parse_ecs_poll(self.POLL)
        self.assertEqual(len(polls), 8)
        self.assertIsNone(polls[0]["desired"])
        self.assertEqual((polls[3]["desired"], polls[3]["running"], polls[3]["pending"]), (2, 1, 1))
        self.assertEqual(polls[3]["line"], 4)

    def test_scale_brackets_are_bounds_not_delays(self):
        polls = perf.parse_ecs_poll(self.POLL)
        windows = {"level-50": ("2026-11-18T20:49:00.000Z", "2026-11-18T20:51:30.000Z", 50), "hold-50": ("2026-11-18T20:51:30.000Z", "2026-11-18T20:52:30.000Z", 50)}
        end = perf.parse_utc("2026-11-18T20:52:30.000Z")
        out = perf.elasticity_from_polls(polls, "x", windows, end)
        so, si = out["scale_out"], out["scale_in"]
        self.assertEqual(so["last_poll_with_data_before"]["utc"], "2026-11-18T20:51:00Z")
        self.assertEqual(so["first_poll_desired_2"]["utc"], "2026-11-18T20:52:00Z")
        self.assertEqual(so["first_poll_running_2"]["utc"], "2026-11-18T20:53:00Z")
        self.assertEqual(so["task_start_upper_bound_seconds"], 60.0)
        self.assertEqual(so["desired_2_no_later_than_seconds_after_phase_start"], {"hold-50": 30.0, "level-50": 180.0})
        self.assertEqual(si["last_poll_desired_2"]["utc"], "2026-11-18T21:00:00Z")
        self.assertEqual(si["first_later_poll_with_data"]["utc"], "2026-11-18T21:15:00Z")
        self.assertEqual(si["blank_polls_between"], 1)
        self.assertEqual(si["scale_in_happened_between_seconds_after_load_stop"], [450.0, 1350.0])
        self.assertIn("GAP", so["interpretation_limit"])

    PROBE = textwrap.dedent("""\
        21:37:50  healthz=200  readyz=200
        Wed Nov 18 21:37:55 UTC 2026
        DEACTIVATING\tSTOPPED\treason
        21:38:00  healthz=200  readyz=200
        21:38:05  healthz=503  readyz=503
        21:38:10  healthz=503  readyz=503
        21:38:15  healthz=200  readyz=503
        21:38:20  healthz=200  readyz=200
        21:38:25  healthz=200  readyz=200
        Wed Nov 18 21:39:55 UTC 2026
        DEACTIVATING\tSTOPPED\treason
        21:40:00  healthz=200  readyz=200
        """).split("\n")

    def test_recovery_from_probe_grid(self):
        out = perf.analyse_probe_lines(self.PROBE, "x")
        first, second = out["stop_task_events"]
        self.assertEqual(first["stop_task_utc_time"], "21:37:55Z")
        self.assertEqual(first["first_non_200_probe"]["utc_time"], "21:38:05Z")
        self.assertEqual(first["last_non_200_probe_utc_time"], "21:38:15Z")
        self.assertEqual(first["first_probe_with_both_200_after"]["utc_time"], "21:38:20Z")
        self.assertEqual(first["stop_to_recovery_seconds"], 25)          # 21:38:20 - 21:37:55
        self.assertEqual(first["observed_outage_seconds_first_bad_to_first_good"], 15)  # 21:38:20 - 21:38:05
        self.assertEqual(first["non_200_probes"], 3)
        self.assertIn("no non-200", second["observed"])
        self.assertEqual(out["probe_count"], 8)


class EmrParsingTests(unittest.TestCase):
    LOG = textwrap.dedent("""\
        pipeline| [2026-11-18T16:32:08Z] [id] INFO pre-spend receipt re-verified before submitting step stage-in
        pipeline| STEP-RESULT: stage-in s-AAA COMPLETED
        pipeline| [2026-11-18T16:32:40Z] [id] INFO pre-spend receipt re-verified before submitting step hadoop-prep
        pipeline| STEP-RESULT: hadoop-prep s-BBB COMPLETED
        pipeline| [2026-11-18T16:40:50Z] [id] INFO pre-spend receipt re-verified before submitting step spark-job
        pipeline| STEP-RESULT: spark-job s-CCC FAILED
        pipeline| [2026-11-18T16:41:20Z] [id] ERROR failed at step step-spark-job: run=x FAILED
        """).split("\n")

    def test_step_gaps_are_upper_bounds(self):
        out = perf.parse_emr_run_lines(self.LOG, "x")
        by = dict((s["step"], s) for s in out["steps"])
        self.assertEqual(by["stage-in"]["seconds_submit_to_next_event"], 32.0)
        self.assertEqual(by["hadoop-prep"]["seconds_submit_to_next_event"], 490.0)
        self.assertEqual(by["spark-job"]["seconds_submit_to_next_event"], 30.0)  # to the failure line
        self.assertEqual(by["spark-job"]["state"], "FAILED")
        self.assertEqual(by["hadoop-prep"]["submitted_line"], 3)


class FactoryParserTests(unittest.TestCase):
    REVIEW = textwrap.dedent("""\
        ## Subphase 6A
        VERDICT: REQUEST-CHANGES for Subphase 6A
        1. **P1 - Something broken.** Owner: `domain-engineer`. This blocks the phase.
        B2 — Medium — a nonblocking thing owned by `hadoop-engineer`
        STATUS: COMPLETE (review) — VERDICT REQUEST-CHANGES for Subphase 6A
        ## Subphase 6B
        STATUS: COMPLETE (review); verdict APPROVE for Subphase 6B
        Prose that says the plan was approved and APPROVED_PLAN_SHA256 is set.
        STATUS: Awaiting independent review; an earlier APPROVE is not restated here.
        """).split("\n")

    def test_verdicts_dedupe_footer_and_skip_prose(self):
        verdicts, findings = factory.parse_review(self.REVIEW, "06", "docs/agent-runs/phase-06/review.md")
        counted = [(v["line"], v["class"], v["unit"]) for v in verdicts if v["counted"]]
        self.assertEqual(counted, [(2, "REQUEST-CHANGES", "6A"), (7, "APPROVE", "6B")])
        excluded = dict((v["line"], v["reason"]) for v in verdicts if not v["counted"])
        self.assertIn("footer restatement of the verdict on line 2", excluded[5])
        self.assertIn("exclusion pattern", excluded[9])
        self.assertTrue(all(v["file"].endswith("review.md") and isinstance(v["line"], int) for v in verdicts))

    def test_findings_severity_blocking_and_owner(self):
        _, findings = factory.parse_review(self.REVIEW, "06", "f")
        by_line = dict((f["line"], f) for f in findings)
        self.assertEqual(sorted(by_line), [3, 4])
        self.assertEqual((by_line[3]["severity_as_written"], by_line[3]["severity_normalized"], by_line[3]["blocking_flag_in_line"]), ("P1", "high", True))
        self.assertEqual(by_line[3]["owners_named"], ["domain-engineer"])
        self.assertEqual((by_line[4]["id"], by_line[4]["severity_as_written"], by_line[4]["severity_normalized"]), ("B2", "Medium", "medium"))
        self.assertFalse(by_line[4]["blocking_flag_in_line"])
        self.assertEqual(by_line[4]["owners_named"], ["hadoop-engineer"])
        self.assertEqual(by_line[3]["unit"], "6A")

    def test_first_pass_per_unit(self):
        verdicts, _ = factory.parse_review(self.REVIEW, "06", "f")
        units = factory.first_pass(verdicts)
        self.assertEqual([(k, v["class"]) for k, v in units.items()], [(("06", "6A"), "REQUEST-CHANGES"), (("06", "6B"), "APPROVE")])

    def test_unpaired_status_lines_are_each_counted(self):
        lines = ["VERDICT: APPROVE for 12D", "STATUS: COMPLETE; verdict APPROVE for 12D one", "STATUS: COMPLETE; verdict APPROVE for 12D two"]
        verdicts, _ = factory.parse_review(lines, "12", "f")
        self.assertEqual([v["counted"] for v in verdicts], [True, False, True])  # the first footer pairs with the VERDICT line, the second is its own review

    def test_verdict_classes_as_written(self):
        lines = ["Initial verdict: CHANGES REQUESTED. x", "Verdict: changes_required for y", "STATUS: REQUEST_CHANGES"]
        verdicts, _ = factory.parse_review(lines, "01", "f")
        self.assertEqual([v["class"] for v in verdicts], ["CHANGES-REQUESTED", "CHANGES-REQUIRED", "REQUEST-CHANGES"])

    def test_report_blocked_repair_human_guard_lines(self):
        lines = ["OWNER: `build-engineer` (model)", "STATUS: BLOCKED-ON the domain contract", "BLOCKED-ON OWNER: domain-engineer for X", "BLOCKED-ON OWNER: None.",
                 "## Review round 1 repair round 2", "> I accept the result", "One command was blocked by the project's PreToolUse guard (false positive).",
                 "Terraform guard refuses a plan without them.", "A manual repair step was needed.", "MANUAL ACTION REQUIRED: User runs the recheck.", "MANUAL ACTION REQUIRED: None."]
        items = factory.parse_simple(lines, "06", "f", "owner-report") + factory.parse_simple(lines, "06", "g", "repairs") + factory.parse_simple(lines, "06", "h", "human-gate")
        kinds = [(i["kind"], i["line"]) for i in items]
        self.assertIn(("report", 1), kinds)
        self.assertEqual([i["role"] for i in items if i["kind"] == "report"], ["build-engineer"])
        self.assertEqual(len([i for i in items if i["kind"] == "status_blocked_on"]), 3)  # once per call: lines are re-read for each record type
        self.assertEqual([i["role"] for i in items if i["kind"] == "blocked_on_owner_named"][0], "domain-engineer")
        self.assertEqual(len([i for i in items if i["kind"] == "blocked_on_owner_named"]), 3)  # "None." names no role
        self.assertTrue(any(i["kind"] == "repair_round_heading" and i["line"] == 5 for i in items))
        self.assertTrue(any(i["kind"] == "human_gate_quote_or_decision" and i["line"] == 6 for i in items))
        guard = [i for i in items if i["kind"] == "guard_block"]
        self.assertEqual(sorted(set(i["line"] for i in guard)), [7])  # the Terraform guard line is not a PreToolUse/hook block
        self.assertTrue(any(i["kind"] == "manual_intervention_phrase" and i["line"] == 9 for i in items))
        self.assertEqual([(i["kind"], i["line"]) for i in items if i["kind"].startswith("manual_action")][:2], [("manual_action_required", 10), ("manual_action_field_none", 11)])
        self.assertFalse(any(i["kind"] == "manual_intervention_phrase" and i["line"] >= 10 for i in items))  # the contract field is not a free-text phrase

    def test_notes_verdicts_exclude_consent_and_sha_names(self):
        lines = ["2026 Services review round 1: CHANGES-REQUIRED. Blocker x", "APPROVED_PLAN_SHA256=abc and lower-case approve", "do the full check only after reviewer APPROVE",
                 "review r1 REQUEST-CHANGES (M1), r2 REQUEST-CHANGES, r3 APPROVE", "worktrees were refused by the PreToolUse guard", "HUMAN DECISION (chat), verbatim: A"]
        items = factory.parse_notes_lines(lines)
        verdicts = [(i["line"], i["class"]) for i in items if i["kind"] == "verdict"]
        self.assertEqual(verdicts, [(1, "CHANGES-REQUIRED"), (4, "REQUEST-CHANGES"), (4, "REQUEST-CHANGES"), (4, "APPROVE")])
        self.assertEqual([i["line"] for i in items if i["kind"] == "guard_block"], [5])
        self.assertEqual([i["line"] for i in items if i["kind"] == "human_decision_line"], [6])

    def test_redaction_of_account_ids_and_emails(self):
        self.assertEqual(factory.redact("acct 111122223333 and a.b@example.com"), "acct <12-digit> and <email>")
        self.assertEqual(repro.redact("x 111122223333"), "x <12-digit>")


class FactoryHandAuditTests(unittest.TestCase):
    def test_phase_03_parser_counts_agree_with_the_hand_audit(self):
        rel = "docs/agent-runs/phase-03/review.md"
        with open(os.path.join(REPO, rel), encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        verdicts, _ = factory.parse_review(lines, "03", rel)
        counted = [v for v in verdicts if v["counted"]]
        audit = factory.HAND_AUDIT_PHASE_03
        self.assertEqual([v["line"] for v in counted], audit["parser_counted"]["lines"])
        self.assertEqual(sum(1 for v in counted if v["class"] == "APPROVE"), audit["parser_counted"]["APPROVE"])
        self.assertEqual(sum(1 for v in counted if v["class"] == "REQUEST-CHANGES"), audit["parser_counted"]["REQUEST-CHANGES"])
        self.assertEqual(len(factory.first_pass(verdicts)), audit["review_units_by_parser"])
        self.assertNotEqual(len(counted), audit["hand_review_events"])  # the documented undercount: 11 against 14
        # the three events the hand audit says the parser misses are not counted
        for missed in (139, 143, 201):
            self.assertNotIn(missed, [v["line"] for v in counted])
        # first verdicts of phases 01, 02 and 04 named in the audit
        for phase, expected in (("01", "CHANGES-REQUESTED"), ("02", "REQUEST-CHANGES"), ("04", "REQUEST-CHANGES")):
            rel2 = "docs/agent-runs/phase-%s/review.md" % phase
            with open(os.path.join(REPO, rel2), encoding="utf-8") as handle:
                v2, _ = factory.parse_review(handle.read().split("\n"), phase, rel2)
            self.assertEqual(next(v for v in v2 if v["counted"])["class"], expected)


class RetrievalMetricTests(unittest.TestCase):
    def test_precision_recall_reciprocal_rank(self):
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "c", "x"}
        self.assertEqual(retrieval.precision_at_k(retrieved, relevant, 2), 0.5)          # a only
        self.assertEqual(retrieval.precision_at_k(retrieved, relevant, 4), 0.5)          # a, c
        self.assertAlmostEqual(retrieval.recall_at_k(retrieved, relevant, 4), 2 / 3.0)   # 2 of 3 relevant
        self.assertEqual(retrieval.reciprocal_rank(retrieved, relevant), 1.0)
        self.assertAlmostEqual(retrieval.reciprocal_rank(retrieved, {"c"}), 1 / 3.0)
        self.assertEqual(retrieval.reciprocal_rank(retrieved, {"zz"}), 0.0)
        self.assertIsNone(retrieval.recall_at_k(retrieved, set(), 3))
        self.assertIsNone(retrieval.precision_at_k(retrieved, relevant, 0))

    def test_ndcg_graded(self):
        gains = {"a": 3.0, "b": 2.0, "c": 1.0}
        expected = (2 + 3 / math.log2(3) + 1 / 2.0) / (3 + 2 / math.log2(3) + 1 / 2.0)
        self.assertAlmostEqual(retrieval.ndcg_at_k(["b", "a", "c"], gains, 3), expected)
        self.assertAlmostEqual(retrieval.ndcg_at_k(["a", "b", "c"], gains, 3), 1.0)
        self.assertEqual(retrieval.ndcg_at_k(["x", "y", "z"], gains, 3), 0.0)
        self.assertIsNone(retrieval.ndcg_at_k(["a"], {}, 3))
        # an item outside the labels has gain 0 and the ideal uses only the K largest gains: K = 2 -> ideal 3/1 + 2/log2(3)
        self.assertAlmostEqual(retrieval.ndcg_at_k(["a", "q"], gains, 2), 3 / (3 + 2 / math.log2(3)))

    def test_wilson_interval(self):
        self.assertIsNone(retrieval.wilson(0, 0))
        lo, hi = retrieval.wilson(5, 5)
        self.assertAlmostEqual(lo, 0.5655, places=3)
        self.assertEqual(hi, 1.0)
        lo, hi = retrieval.wilson(0, 3)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.5615, places=3)

    def test_mean_ignores_none(self):
        self.assertEqual(retrieval.mean([1.0, None, 0.0]), 0.5)
        self.assertIsNone(retrieval.mean([None]))

    def test_retrieved_researchers_maps_evidence_in_order(self):
        r1, r2 = "researcher:dblp:" + "1" * 64, "researcher:dblp:" + "2" * 64
        row = {"explain": {"body": {"evidenceIds": ["e2", "e1", "e3", "e1b"]}},
               "evidence": {"e1": {"item": {"provenance": {"sourceRecordId": "7:ranking:metrics/type=x:%s:*" % r1}}},
                            "e1b": {"item": {"provenance": {"sourceRecordId": "other:%s" % r1}}},
                            "e2": {"item": {"provenance": {"sourceRecordId": "7:ranking:metrics/type=x:%s:*" % r2}}}, "e3": {"item": {"provenance": {"sourceRecordId": "no id here"}}}}}
        ids, unmapped = retrieval.retrieved_researchers(row)
        self.assertEqual(ids, [r2, r1])  # order of evidenceIds; the duplicate e1b is not repeated
        self.assertEqual(unmapped, 1)
        self.assertIsNone(retrieval.retrieved_researchers({"explain": None}))

    def test_tie_check_reads_values_stated_in_the_answer(self):
        r1, r2, r3, rk = ("researcher:dblp:" + c * 64 for c in "1234")
        key = [{"id": rk, "rank": 1, "value": 15}, {"id": "researcher:dblp:" + "5" * 64, "rank": 2, "value": 15}]
        row = {"answer": {"answer": {"researchers": [{"researcherId": r1, "maximumCoauthorsOnOnePaper": "15"}, {"researcherId": r2, "maximumCoauthorsOnOnePaper": "14"}]}}}
        t = retrieval.tie_check(row, [r1, r2, r3], key, "MAXIMUM_COAUTHORS_ON_ONE_PAPER")
        self.assertEqual([o["value_stated_in_answer"] for o in t["retrieved_outside_key"]], ["15", "14", None])
        self.assertEqual((t["outside_with_value_equal_to_key_value"], t["outside_with_no_value_stated"], t["all_outside_tie_at_key_value"]), (1, 1, False))
        row_all = {"answer": {"answer": {"researchers": [{"researcherId": r1, "maximumCoauthorsOnOnePaper": "15"}]}}}
        self.assertTrue(retrieval.tie_check(row_all, [r1], key, "MAXIMUM_COAUTHORS_ON_ONE_PAPER")["all_outside_tie_at_key_value"])

    def test_score_ranking_question(self):
        key = [{"id": "r1", "rank": 1, "value": 10}, {"id": "r2", "rank": 2, "value": 8}, {"id": "r3", "rank": 3, "value": 5}, {"id": "r4", "rank": 4, "value": 1}]
        s = retrieval.score_ranking_question(["r1", "r3", "rX"], key)
        self.assertEqual(s["k"], 3)
        self.assertAlmostEqual(s["precision_at_k_vs_key_top100"], 2 / 3.0)
        self.assertAlmostEqual(s["precision_at_k_vs_key_topk"], 2 / 3.0)   # key top-3 = r1, r2, r3
        self.assertEqual(s["reciprocal_rank_of_key_rank1"], 1.0)
        self.assertAlmostEqual(s["ndcg_at_k_graded_by_key_value"], (10 + 5 / math.log2(3)) / (10 + 8 / math.log2(3) + 5 / 2.0))
        self.assertFalse(s["exact_order_match_with_key_topk"])
        self.assertFalse(s["key_saturated_by_ties"])
        tied = retrieval.score_ranking_question(["r9"], [{"id": "r1", "rank": 1, "value": 15}, {"id": "r2", "rank": 2, "value": 15}])
        self.assertTrue(tied["key_saturated_by_ties"])
        self.assertEqual(tied["precision_at_k_vs_key_top100"], 0.0)


class ReproComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="eval16-b-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.scripts = os.path.join(self.tmp, "scripts")
        self.results = os.path.join(self.tmp, "results")
        os.makedirs(self.scripts)
        os.makedirs(os.path.join(self.results, "demo"))

    def put(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def script(self, name, body):
        self.put(os.path.join(self.scripts, name), "import argparse, os, sys\np = argparse.ArgumentParser()\np.add_argument('--out-dir')\na = p.parse_args()\nos.makedirs(a.out_dir, exist_ok=True)\n" + body)

    def run_verify(self, scripts):
        lines = []
        totals = repro.verify(results_dir=self.results, scripts_dir=self.scripts, scripts=scripts, emit=lines.append)
        return totals, lines

    def test_matching_files_pass_and_summary_line(self):
        self.script("eval16_demo.py", "open(os.path.join(a.out_dir, 'a.json'), 'w').write('{}\\n')\n")
        self.put(os.path.join(self.results, "demo", "a.json"), "{}\n")
        totals, lines = self.run_verify((("eval16_demo.py", "demo"),))
        self.assertEqual((totals["pass"], totals["fail"], totals["skip"]), (1, 0, 0))
        self.assertIn("PASS demo/a.json", lines)
        self.assertEqual(lines[-1], "REGENERATION: PASS pass=1 fail=0 skipped_scripts=0")

    def test_differing_bytes_fail(self):
        self.script("eval16_demo.py", "open(os.path.join(a.out_dir, 'a.json'), 'w').write('{\"v\": 2}\\n')\n")
        self.put(os.path.join(self.results, "demo", "a.json"), "{\"v\": 1}\n")
        totals, lines = self.run_verify((("eval16_demo.py", "demo"),))
        self.assertEqual(totals["fail"], 1)
        self.assertTrue(any(l.startswith("FAIL demo/a.json (bytes differ") for l in lines))
        self.assertTrue(lines[-1].startswith("REGENERATION: FAIL"))

    def test_extra_and_missing_files(self):
        self.script("eval16_demo.py", "open(os.path.join(a.out_dir, 'new.json'), 'w').write('x\\n')\n")
        self.put(os.path.join(self.results, "demo", "stale.json"), "old\n")
        self.put(os.path.join(self.results, "demo", "regeneration-check.log"), "log\n")
        totals, lines = self.run_verify((("eval16_demo.py", "demo"),))
        self.assertTrue(any("FAIL demo/new.json (produced but not committed)" in l for l in lines))
        self.assertTrue(any("FAIL demo/stale.json (committed but not regenerated" in l for l in lines))
        self.assertTrue(any(l.startswith("NOT-COMPARED demo/regeneration-check.log") for l in lines))
        self.assertEqual(totals["fail"], 2)

    def test_absent_script_is_skip_not_pass(self):
        totals, lines = self.run_verify((("eval16_missing.py", "missing"),))
        self.assertEqual((totals["pass"], totals["skip"], totals["fail"]), (0, 1, 0))
        self.assertIn("SKIP missing (script not present yet)", lines)
        self.assertEqual(lines[-1], "REGENERATION: PARTIAL pass=0 fail=0 skipped_scripts=1")
        self.assertEqual(repro.exit_code(totals), 4)

    def test_exit_codes_pass_partial_fail(self):
        self.assertEqual((repro.verdict({"pass": 3, "fail": 0, "skip": 0}), repro.exit_code({"pass": 3, "fail": 0, "skip": 0})), ("PASS", 0))
        self.assertEqual((repro.verdict({"pass": 3, "fail": 0, "skip": 1}), repro.exit_code({"pass": 3, "fail": 0, "skip": 1})), ("PARTIAL", 4))
        self.assertEqual((repro.verdict({"pass": 3, "fail": 1, "skip": 1}), repro.exit_code({"pass": 3, "fail": 1, "skip": 1})), ("FAIL", 1))

    def test_exit_3_is_skip_and_partial_outputs_are_compared(self):
        self.script("eval16_demo.py", "open(os.path.join(a.out_dir, 'a.json'), 'w').write('{}\\n')\nprint('INPUTS-UNAVAILABLE: x')\nsys.exit(3)\n")
        self.put(os.path.join(self.results, "demo", "a.json"), "{}\n")
        self.put(os.path.join(self.results, "demo", "local-only.json"), "{}\n")
        totals, lines = self.run_verify((("eval16_demo.py", "demo"),))
        self.assertEqual((totals["pass"], totals["fail"], totals["skip"]), (1, 0, 1))
        self.assertTrue(lines[-1].startswith("REGENERATION: PARTIAL"))
        self.assertTrue(any(l.startswith("SKIP demo (inputs unavailable") for l in lines))
        self.assertTrue(any(l.startswith("SKIP demo/local-only.json") for l in lines))

    def test_script_error_is_fail(self):
        self.script("eval16_demo.py", "sys.exit(1)\n")
        totals, lines = self.run_verify((("eval16_demo.py", "demo"),))
        self.assertEqual(totals["fail"], 1)
        self.assertTrue(any(l.startswith("FAIL demo (script exited 1") for l in lines))

    def test_frozen_input_directory_is_verified_not_regenerated(self):
        frozen = os.path.join(self.results, "performance", "raw-rb-20261118")
        self.put(os.path.join(frozen, "a.jsonl"), "x\n")
        import hashlib
        digest = hashlib.sha256(b"x\n").hexdigest()
        self.put(os.path.join(frozen, "SHA256SUMS"), "%s  a.jsonl\n" % digest)
        lines = []
        self.assertEqual(repro.check_frozen_inputs(self.results, lines.append), (1, 0))
        self.assertTrue(lines[0].startswith("PASS performance/raw-rb-20261118 (frozen input: 1 files match"))
        self.put(os.path.join(frozen, "a.jsonl"), "tampered\n")
        lines = []
        self.assertEqual(repro.check_frozen_inputs(self.results, lines.append), (0, 1))
        self.assertIn("FAIL performance/raw-rb-20261118", lines[0])
        # the compare step leaves a frozen directory alone (it is not a regenerated file)
        produced = os.path.join(self.tmp, "produced")
        os.makedirs(produced)
        self.put(os.path.join(produced, "m.json"), "{}\n")
        self.put(os.path.join(self.results, "performance", "m.json"), "{}\n")
        lines = []
        self.assertEqual(repro.compare("performance", produced, os.path.join(self.results, "performance"), lines.append), (1, 0))

    def test_check_result_regex_and_notes_rules(self):
        m = [x.group(1) for x in repro.CHECK_RESULT.finditer("a `RESULT: PASS gates=7` b `RESULT: FAIL failed: script-tests` c RESULT: PARTIAL passed=6")]
        self.assertEqual(m, ["PASS gates=7", "FAIL failed: script-tests", "PARTIAL passed=6"])
        self.assertEqual(repro.NOTE_RULES[0][0].search("full check RESULT PASS gates=7 (sbt 834s)").group(1), "7")


class CommittedOutputsTests(unittest.TestCase):
    """The committed Phase 16 tables of this owner parse and carry the fields their scripts promise (no raw evidence needed)."""

    def read(self, rel):
        path = os.path.join(REPO, "experiments", "results", "phase16", rel)
        self.assertTrue(os.path.isfile(path), rel + " is not committed")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_performance_table_has_gaps_and_environment_labels(self):
        d = self.read("performance/performance-metrics.json")
        self.assertEqual(d["schema"], perf.SCHEMA)
        self.assertEqual(d["load_aws_ecs"]["environment"], "AWS-ECS")
        self.assertEqual(d["load_local_loopback_docker"]["environment"], "LOCAL-LOOPBACK-DOCKER")
        self.assertTrue(all(p["cross_check_vs_harness_summary"] == "MATCH" for p in d["load_aws_ecs"]["phases"] + d["load_local_loopback_docker"]["phases"]))
        self.assertGreaterEqual(len(d["gaps"]), 5)
        self.assertIn("inputs_sha256", d)

    def test_aws_raw_is_frozen_and_p35_is_a_declared_gap(self):
        d = self.read("performance/performance-metrics.json")
        frozen = os.path.join(REPO, "experiments", "results", "phase16", "performance", "raw-rb-20261118")
        listed = perf.verify_frozen("experiments/results/phase16/performance/raw-rb-20261118")
        self.assertEqual(sorted(listed), ["events.jsonl", "raw.sha256", "requests.jsonl", "run-record.json", "summary.csv"])
        self.assertEqual(d["inputs_sha256"]["rb-20261118 raw/requests.jsonl"], listed["requests.jsonl"])
        self.assertFalse(os.path.exists(os.path.join(frozen, "..", "raw-p35-local-1")))
        self.assertTrue(any("P35" in g["metric"] and "NOT frozen" in g["reason"] for g in d["gaps"]))

    def test_factory_items_all_have_file_and_line(self):
        items = self.read("factory/factory-items.json")
        everything = items["verdicts"] + items["findings"] + items["other_items"]
        self.assertGreater(len(everything), 100)
        self.assertTrue(all(isinstance(i["line"], int) and i["file"].startswith("docs/agent-runs/phase-") for i in everything))
        summary = self.read("factory/factory-metrics.json")
        self.assertEqual(sum(1 for v in items["verdicts"] if v["counted"]), summary["totals"]["verdict_lines_counted"])
        self.assertEqual(len(items["findings"]), summary["totals"]["finding_lines"])

    def test_retrieval_table_declares_vector_and_fused_as_gaps(self):
        d = self.read("retrieval/retrieval-metrics.json")
        self.assertEqual((d["mode_comparison"]["vector_only"], d["mode_comparison"]["fused"]), ("GAP", "GAP"))
        self.assertTrue(any("vector-only" in g["metric"] for g in d["gaps"]))

    def test_reproducibility_marks_fresh_clone_pending(self):
        d = self.read("reproducibility/reproducibility-evidence.json")
        clean = next(c for c in d["course_checks"] if c["check"] == "clean-checkout build")
        self.assertIn("PENDING", clean["status"])
        self.assertIn("not done", clean["status"])


if __name__ == "__main__":
    unittest.main()

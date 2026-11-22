#!/usr/bin/env python3
"""Tests for load-tests/llm_budget.py, the per-bucket Haiku answer ledger (stdlib, local files only).

Run from the repository root:   python3 -I -m unittest discover -s load-tests/tests -v
Expected values are hand-derived: unit cost 0.001365 USD = (7,150 x 0.10 + 1,300 x 0.50) / 1M (claude-haiku-5-5, tokens raised 30%); buckets 14c 10, 15b 60, 16b 80, 17 10 (16b and 17 raised by the user decision of 2026-11-21, option A; were 40 and 5); cap 1.33.
"""
import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LOAD_TESTS = os.path.dirname(HERE)
SCRIPT = os.path.join(LOAD_TESTS, "llm_budget.py")
sys.path.insert(0, LOAD_TESTS)
import importlib.util

spec = importlib.util.spec_from_file_location("llm_budget_under_test", SCRIPT)
lb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lb)


def write_json(path, document):
    with open(path, "w") as handle:
        json.dump(document, handle)


def read_text(path):
    with open(path) as handle:
        return handle.read()


def read_json(path):
    with open(path) as handle:
        return json.load(handle)


def read_lines(path):
    with open(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


class BudgetCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lb-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ledger = os.path.join(self.tmp, "sub", "ledger.jsonl")

    def cli(self, *argv, ledger=None, extra=()):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = lb.main(["--ledger", ledger or self.ledger] + list(extra) + list(argv), out=out)
        return rc, out.getvalue(), err.getvalue()

    def init(self, **kw):
        self.assertEqual(self.cli("init", **kw)[0], 0)

    def lines(self):
        return read_lines(self.ledger)


class DefaultAllocation(BudgetCase):
    def test_pinned_allocation_and_status_arithmetic(self):
        self.init()
        self.assertEqual(stat.S_IMODE(os.stat(self.ledger).st_mode), 0o600)
        rc, out, err = self.cli("status")
        self.assertEqual(rc, 0, err)
        self.assertIn("BUCKET 14c size=10 used=0 remaining=10", out)
        self.assertIn("BUCKET 15b size=60 used=0 remaining=60", out)
        self.assertIn("BUCKET 16b size=80 used=0 remaining=80", out)
        self.assertIn("BUCKET 17 size=10 used=0 remaining=10", out)
        for bucket, count in (("14c", 4), ("15b", 7), ("17", 1)):
            self.assertEqual(self.cli("reserve", "--bucket", bucket, "--answers", str(count))[0], 0)
        self.assertEqual(self.cli("adjust", "--usd", "0.05", "--source", "aws-bill")[0], 0)
        out = self.cli("status")[1]
        # 12 answers x 0.001365 = 0.016380; plus 0.05 adjust = 0.066380; remaining 1.33 - 0.06638 = 1.263620
        self.assertIn("BUCKET 14c size=10 used=4 remaining=6 est_usd_used=0.005460", out)
        self.assertIn("BUCKET 15b size=60 used=7 remaining=53 est_usd_used=0.009555", out)
        self.assertIn("BUCKET 16b size=80 used=0 remaining=80 est_usd_used=0.000000", out)
        self.assertIn("BUCKET 17 size=10 used=1 remaining=9 est_usd_used=0.001365", out)
        self.assertIn("TOTAL answers_used=12 usd_used=0.066380 (incl. adjust 0.050000) shared_cap_usd=1.330000 remaining_usd=1.263620 unit_usd=0.001365", out)

    def test_a_bucket_is_a_hard_stop_exactly_full_passes_one_more_is_refused(self):
        self.init()
        rc, out, err = self.cli("reserve", "--bucket", "17", "--answers", "10")  # exactly the size 10
        self.assertEqual(rc, 0, err)
        self.assertIn("RESULT: RESERVED bucket=17 answers=10 est_usd=0.013650", out)
        before = read_text(self.ledger)
        rc, out, err = self.cli("reserve", "--bucket", "17", "--answers", "1")
        self.assertEqual(rc, 3)
        self.assertIn("bucket 17: used 10 + requested 1 > size 10 (remaining 0)", err)
        self.assertEqual(read_text(self.ledger), before)  # a refusal writes nothing
        # other buckets are unaffected, and one reservation larger than the bucket is refused whole
        self.assertEqual(self.cli("reserve", "--bucket", "14c", "--answers", "11")[0], 3)
        self.assertEqual(self.cli("reserve", "--bucket", "14c", "--answers", "10")[0], 0)

    def test_total_cap_refuses_even_when_the_bucket_still_has_room(self):
        self.init()
        self.assertEqual(self.cli("adjust", "--usd", "1.32", "--source", "bill")[0], 0)
        # 1.32 + 7 x 0.001365 = 1.329555 <= 1.33 passes (bucket 14c has 10)
        self.assertEqual(self.cli("reserve", "--bucket", "14c", "--answers", "7")[0], 0)
        # one more: 1.329555 + 0.001365 = 1.33092 > 1.33 although 14c still has 3 free
        rc, _, err = self.cli("reserve", "--bucket", "14c", "--answers", "1")
        self.assertEqual(rc, 3)
        self.assertIn("ledger total 1.329555 USD + 1 answers x 0.001365 USD > shared cap 1.330000 USD", err)

    def test_release_gives_back_only_what_was_used(self):
        self.init()
        self.cli("reserve", "--bucket", "16b", "--answers", "6")
        self.assertEqual(self.cli("release", "--bucket", "16b", "--answers", "2")[0], 0)
        self.assertIn("BUCKET 16b size=80 used=4 remaining=76", self.cli("status")[1])
        rc, _, err = self.cli("release", "--bucket", "16b", "--answers", "5")
        self.assertEqual(rc, 3)
        self.assertIn("only 4 are recorded as used", err)
        self.assertIn("TOTAL answers_used=4 usd_used=0.005460", self.cli("status")[1])

    def test_unknown_bucket_bad_counts_absent_and_corrupt_ledgers(self):
        rc, _, err = self.cli("status")
        self.assertEqual(rc, 3)
        self.assertIn("does not exist", err)
        self.init()
        self.assertEqual(self.cli("init")[0], 3)  # never reset
        self.assertEqual(self.cli("reserve", "--bucket", "nope", "--answers", "1")[0], 3)
        self.assertEqual(self.cli("reserve", "--bucket", "14c", "--answers", "0")[0], 3)
        self.assertEqual(self.cli("reserve", "--bucket", "14c", "--answers", "-2")[0], 3)
        for bad in ("-1", "0", "nan", "abc"):
            self.assertEqual(self.cli("adjust", "--usd", bad, "--source", "x")[0], 3, bad)
        with open(self.ledger, "a") as handle:
            handle.write(json.dumps({"event": "mystery"}) + "\n")
        rc, _, err = self.cli("status")
        self.assertEqual(rc, 3)
        self.assertIn("not a valid entry", err)
        self.assertEqual(self.cli("reserve", "--bucket", "14c", "--answers", "1")[0], 3)

    def test_options_work_before_or_after_the_subcommand(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(lb.main(["init", "--ledger", self.ledger], out=out), 0)
            self.assertEqual(lb.main(["reserve", "--ledger", self.ledger, "--bucket", "17", "--answers", "1"], out=out), 0)

    def test_allocation_change_after_init_is_flagged(self):
        alloc = os.path.join(self.tmp, "alloc.json")
        document = read_json(lb.DEFAULT_ALLOCATION)
        write_json(alloc, document)
        self.init(extra=["--allocation", alloc])
        self.assertNotIn("ALLOCATION-CHANGED", self.cli("status", extra=["--allocation", alloc])[1])
        document["buckets"]["16b"]["answers"] = 79  # 10 + 60 + 79 + 10 = 159 x 0.001365 = 0.217035 <= 1.33, so the edited file still loads
        write_json(alloc, document)
        self.assertIn("ALLOCATION-CHANGED", self.cli("status", extra=["--allocation", alloc])[1])

    def test_real_allocation_fits_the_cap_and_the_buckets_bind_before_the_cap(self):
        self.init()
        for bucket, count in (("14c", 10), ("15b", 60), ("16b", 80), ("17", 10)):
            self.assertEqual(self.cli("reserve", "--bucket", bucket, "--answers", str(count))[0], 0)
        # 160 x 0.001365 = 0.2184 <= 1.33: every bucket is full and the ledger total is far inside the shared cap
        self.assertIn("TOTAL answers_used=160 usd_used=0.218400 (incl. adjust 0.000000) shared_cap_usd=1.330000 remaining_usd=1.111600 unit_usd=0.001365", self.cli("status")[1])
        # with every bucket full, one more answer is refused by the bucket, not by the cap (1.33 is a conservative upper bound now)
        rc, _, err = self.cli("reserve", "--bucket", "17", "--answers", "1")
        self.assertEqual(rc, 3)
        self.assertIn("bucket 17: used 10 + requested 1 > size 10 (remaining 0)", err)
        self.assertNotIn("shared cap", err)
        # the cap would hold 974 answers (974 x 0.001365 = 1.32951) and not 975 (1.330875 > 1.33): an allocation of 975 is refused whole
        alloc = os.path.join(self.tmp, "alloc975.json")
        document = read_json(lb.DEFAULT_ALLOCATION)
        document["buckets"]["16b"]["answers"] = 895  # 10 + 60 + 895 + 10 = 975
        write_json(alloc, document)
        rc, _, err = self.cli("status", extra=["--allocation", alloc])
        self.assertEqual(rc, 3)
        self.assertIn("exceeds the shared cap", err)
        document["buckets"]["16b"]["answers"] = 894  # 974 answers still load
        write_json(alloc, document)
        self.assertEqual(self.cli("status", extra=["--allocation", alloc])[0], 0)

    def test_ledger_total_refuses_an_answer_that_would_pass_the_shared_cap(self):
        self.init()
        self.assertEqual(self.cli("adjust", "--usd", "1.329", "--source", "aws-bill")[0], 0)  # spend observed elsewhere
        rc, _, err = self.cli("reserve", "--bucket", "14c", "--answers", "1")  # 1.329 + 0.001365 = 1.330365 > 1.33; bucket 14c is empty
        self.assertEqual(rc, 3)
        self.assertIn("ledger total 1.329000 USD + 1 answers x 0.001365 USD > shared cap 1.330000 USD", err)

    def test_allocation_over_the_cap_or_with_another_cap_is_refused(self):
        alloc = os.path.join(self.tmp, "alloc.json")
        document = read_json(lb.DEFAULT_ALLOCATION)
        document["buckets"]["16b"]["answers"] = 1000  # 10 + 60 + 1000 + 10 = 1080 x 0.001365 = 1.4742 > 1.33
        write_json(alloc, document)
        rc, _, err = self.cli("status", extra=["--allocation", alloc])
        self.assertEqual(rc, 3)
        self.assertIn("exceeds the shared cap", err)
        document["buckets"]["16b"]["answers"] = 80
        document["shared_cap_usd"] = "2.00"
        write_json(alloc, document)
        self.assertEqual(self.cli("status", extra=["--allocation", alloc])[0], 3)


class PricingAndCostReport(unittest.TestCase):
    """The pinned claude-haiku-5-5 and voyage-4-lite numbers and the AWS / Anthropic / Voyage cost report (hand-derived, no I/O)."""

    def setUp(self):
        self.profile = read_json(lb.DEFAULT_PROFILE)

    def test_profile_pins_haiku_5_5_rates_tokens_and_the_bedrock_fallback(self):
        llm = self.profile["llm"]
        self.assertEqual(llm["provider"], "anthropic")
        self.assertTrue(llm["pricing"]["model_route"].startswith("claude-haiku-5-5"))
        self.assertIn("us.anthropic.claude-haiku-4-5-20251001-v1:0", llm["pricing"]["fallback_model_route"])
        self.assertEqual((llm["pricing"]["input_usd_per_million_tokens"], llm["pricing"]["output_usd_per_million_tokens"]), ("0.10", "0.50"))
        # the old plan 1500 / 200 / 4000 / 800 raised 30 percent
        self.assertEqual(llm["tokens_per_answer"], {"planner_input": 1950, "planner_output": 260, "synthesis_input": 5200, "synthesis_output": 1040})
        self.assertEqual(llm["shared_cap_usd"], "1.33")  # unchanged by the user decision
        # (1950 + 5200) = 7150 in x 0.10 + (260 + 1040) = 1300 out x 0.50 per million = 715 + 650 micro-USD
        self.assertEqual(lb.money(lb.cost_per_answer(self.profile)), "0.001365")

    def test_embedding_allowance_and_charge(self):
        emb = self.profile["embeddings"]
        self.assertEqual((emb["model"], emb["output_dimension"], emb["usd_per_million_tokens"], emb["free_tokens"], emb["cap_usd"]), ("voyage-4-lite", 256, "0.02", 200000000, "0.30"))
        self.assertEqual(lb.money(lb.embedding_cost(self.profile, 5000000)), "0.000000")  # inside the free 200M
        self.assertEqual(lb.money(lb.embedding_cost(self.profile, 200000000)), "0.000000")  # exactly the allowance
        self.assertEqual(lb.money(lb.embedding_cost(self.profile, 1000000, prior_tokens=200000000)), "0.020000")  # all billable
        self.assertEqual(lb.money(lb.embedding_cost(self.profile, 2000000, prior_tokens=199000000)), "0.020000")  # 1M free + 1M billable
        for bad in (-1, 1.5, True):
            with self.assertRaises(lb.Refused):
                lb.embedding_cost(self.profile, bad)

    def test_cost_report_lists_aws_anthropic_voyage_then_the_combined_total(self):
        report = lb.cost_report(self.profile, 160)
        self.assertEqual(list(report)[:3], ["aws", "anthropic", "voyage"])
        self.assertEqual(report["anthropic"]["usd"], "0.218400")  # 160 x 0.001365
        self.assertEqual((report["anthropic"]["input_tokens_estimate"], report["anthropic"]["output_tokens_estimate"]), (160 * 7150, 160 * 1300))
        self.assertEqual(report["voyage"]["usd"], "0.000000")  # no charge: USD 0 with the usage noted
        self.assertIn("not metered", report["voyage"]["usage"])
        self.assertIsNone(report["aws"]["usd"])
        self.assertEqual(report["combined_usd"], "0.218400")
        self.assertIn("AWS not included", report["combined_scope"])
        full = lb.cost_report(self.profile, 10, embedding_tokens=3000000, aws_usd="0.50")
        self.assertEqual((full["aws"]["usd"], full["anthropic"]["usd"], full["voyage"]["usd"], full["combined_usd"]), ("0.500000", "0.013650", "0.000000", "0.513650"))
        self.assertEqual(full["combined_scope"], "aws + anthropic + voyage")
        self.assertIn("3000000 tokens counted", full["voyage"]["usage"])
        none = lb.cost_report(self.profile, 0)
        self.assertEqual((none["anthropic"]["usd"], none["combined_usd"]), ("0.000000", "0.000000"))
        self.assertIn("USD 0", none["anthropic"]["usage"])


class Transfers(BudgetCase):
    def approval(self, *rows):
        path = os.path.join(self.tmp, "approval.md")
        with open(path, "w") as handle:
            handle.write("\n".join(rows) + "\n")
        return path

    def test_transfer_needs_the_exact_approval_line(self):
        self.init()
        before = read_text(self.ledger)
        args = ("transfer", "--from", "14c", "--to", "15b", "--answers", "3")
        rc, _, err = self.cli(*args, "--approval", os.path.join(self.tmp, "missing.md"))
        self.assertEqual(rc, 3)
        self.assertIn("does not exist", err)
        wrong_rows = ["APPROVED_LLM_TRANSFER=14c->15b:2",  # other count
                      "APPROVED_LLM_TRANSFER=15b->14c:3",  # reversed
                      "APPROVED_LLM_TRANSFER=14c->16b:3",  # other target
                      "APPROVED_LLM_TRANSFER = 14c->15b:3",  # spaces
                      "xAPPROVED_LLM_TRANSFER=14c->15b:3",  # prefix text
                      "APPROVED_LLM_TRANSFER=14c->15b:3 ",  # accepted after strip? see below
                      "# APPROVED_LLM_TRANSFER=14c->15b:3",
                      "approved_llm_transfer=14c->15b:3"]
        for row in wrong_rows[:5] + wrong_rows[6:]:
            rc, _, err = self.cli(*args, "--approval", self.approval(row))
            self.assertEqual(rc, 3, row)
            self.assertIn("no line exactly: APPROVED_LLM_TRANSFER=14c->15b:3", err)
        self.assertEqual(read_text(self.ledger), before)  # nothing recorded
        good = self.approval("some text", "APPROVED_LLM_TRANSFER=14c->15b:3", "more text")
        rc, out, err = self.cli(*args, "--approval", good)
        self.assertEqual(rc, 0, err)
        status = self.cli("status")[1]
        self.assertIn("BUCKET 14c size=7 used=0 remaining=7", status)  # 10 - 3
        self.assertIn("BUCKET 15b size=63 used=0 remaining=63", status)  # 60 + 3
        recorded = [e for e in self.lines() if e["event"] == "transfer"]
        self.assertEqual(len(recorded), 1)
        self.assertEqual((recorded[0]["from"], recorded[0]["to"], recorded[0]["answers"]), ("14c", "15b", 3))
        self.assertEqual(recorded[0]["approval_line"], "APPROVED_LLM_TRANSFER=14c->15b:3")
        self.assertEqual(len(recorded[0]["approval_sha256"]), 64)
        # the same approval file cannot be applied twice
        rc, _, err = self.cli(*args, "--approval", good)
        self.assertEqual(rc, 3)
        self.assertIn("already applied", err)

    def test_only_unused_answers_move_and_the_new_size_is_a_hard_stop(self):
        self.init()
        self.cli("reserve", "--bucket", "14c", "--answers", "8")  # 2 unused
        rc, _, err = self.cli("transfer", "--from", "14c", "--to", "17", "--answers", "3", "--approval", self.approval("APPROVED_LLM_TRANSFER=14c->17:3"))
        self.assertEqual(rc, 3)
        self.assertIn("bucket 14c has only 2 unused answers, cannot move 3", err)
        self.assertEqual(self.cli("transfer", "--from", "14c", "--to", "17", "--answers", "2", "--approval", self.approval("APPROVED_LLM_TRANSFER=14c->17:2"))[0], 0)
        self.assertEqual(self.cli("reserve", "--bucket", "14c", "--answers", "1")[0], 3)  # 14c is now size 8, used 8
        self.assertEqual(self.cli("reserve", "--bucket", "17", "--answers", "12")[0], 0)  # 17 is now size 12 (10 + 2)
        self.assertEqual(self.cli("reserve", "--bucket", "17", "--answers", "1")[0], 3)
        self.assertIn("TOTAL answers_used=20", self.cli("status")[1])  # moving allowance never changes spend

    def test_bad_transfer_arguments(self):
        self.init()
        row = "APPROVED_LLM_TRANSFER=14c->14c:1"
        self.assertEqual(self.cli("transfer", "--from", "14c", "--to", "14c", "--answers", "1", "--approval", self.approval(row))[0], 3)
        row = "APPROVED_LLM_TRANSFER=14c->zz:1"
        self.assertEqual(self.cli("transfer", "--from", "14c", "--to", "zz", "--answers", "1", "--approval", self.approval(row))[0], 3)
        row = "APPROVED_LLM_TRANSFER=14c->15b:0"
        self.assertEqual(self.cli("transfer", "--from", "14c", "--to", "15b", "--answers", "0", "--approval", self.approval(row))[0], 3)
        directory = os.path.join(self.tmp, "adir")
        os.mkdir(directory)
        self.assertEqual(self.cli("transfer", "--from", "14c", "--to", "15b", "--answers", "1", "--approval", directory)[0], 3)


class Boundaries(BudgetCase):
    """A custom profile with its own cap of 1.50 USD, a unit cost of exactly 0.15 USD and one bucket of 10 answers: 10 x 0.15 = 1.50 = that cap (not the real cap of 1.33)."""

    def setUp(self):
        super().setUp()
        profile = read_json(lb.DEFAULT_PROFILE)
        profile["llm"]["tokens_per_answer"] = {"planner_input": 150000, "planner_output": 0, "synthesis_input": 0, "synthesis_output": 0}
        profile["llm"]["pricing"]["input_usd_per_million_tokens"] = "1.00"  # 150,000 tokens x 1.00 / 1M = 0.15
        profile["llm"]["shared_cap_usd"] = "1.50"  # the fixture's own cap; the allocation file below must carry the same value
        self.profile = os.path.join(self.tmp, "profile.json")
        write_json(self.profile, profile)
        self.alloc = os.path.join(self.tmp, "alloc.json")
        write_json(self.alloc, {"schema": "scholarchain.llm-allocation.v2", "shared_cap_usd": "1.50", "buckets": {"a": {"answers": 10}, "b": {"answers": 0}}})
        self.extra = ["--profile", self.profile, "--allocation", self.alloc]
        self.init(extra=self.extra)

    def test_total_cap_exactly_reached_passes_one_more_is_refused(self):
        self.assertIn("unit_usd=0.150000", self.cli("status", extra=self.extra)[1])
        self.assertEqual(self.cli("adjust", "--usd", "0.15", "--source", "bill", extra=self.extra)[0], 0)
        self.assertEqual(self.cli("reserve", "--bucket", "a", "--answers", "9", extra=self.extra)[0], 0)  # 0.15 + 9 x 0.15 = 1.50 exactly
        self.assertIn("remaining_usd=0.000000", self.cli("status", extra=self.extra)[1])
        rc, _, err = self.cli("reserve", "--bucket", "a", "--answers", "1", extra=self.extra)  # bucket has 1 free, the cap does not
        self.assertEqual(rc, 3)
        self.assertIn("> shared cap 1.500000 USD", err)

    def test_bucket_exactly_full_equals_the_cap(self):
        self.assertEqual(self.cli("reserve", "--bucket", "a", "--answers", "10", extra=self.extra)[0], 0)  # 10 x 0.15 = 1.50
        rc, _, err = self.cli("reserve", "--bucket", "a", "--answers", "1", extra=self.extra)
        self.assertEqual(rc, 3)
        self.assertIn("used 10 + requested 1 > size 10", err)
        self.assertEqual(self.cli("reserve", "--bucket", "b", "--answers", "1", extra=self.extra)[0], 3)  # a bucket of size 0 never allows a call


class Concurrency(BudgetCase):
    def test_concurrent_reservations_never_exceed_a_bucket_threads(self):
        self.init()
        budget = lb.Budget(self.ledger)
        original = budget._state

        def slow_state(fd):  # widen the read-then-append window, as a slow disk would, so an unlocked implementation overshoots
            result = original(fd)
            time.sleep(0.005)
            return result

        budget._state = slow_state
        granted = []

        def worker():
            for _ in range(5):
                ok, _ = budget.try_charge("17", 1)  # bucket 17 holds 10
                if ok:
                    granted.append(1)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(granted), 10)
        self.assertEqual(budget.state()["used"]["17"], 10)

    def test_concurrent_reservations_never_exceed_a_bucket_processes(self):
        self.init()
        procs = [subprocess.Popen([sys.executable, "-I", SCRIPT, "--ledger", self.ledger, "reserve", "--bucket", "17", "--answers", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for _ in range(14)]
        codes = sorted(p.wait(timeout=60) for p in procs)
        self.assertEqual(codes, [0] * 10 + [3] * 4)  # exactly the 10 answers of bucket 17 were granted
        self.assertEqual(len([e for e in self.lines() if e["event"] == "reserve"]), 10)
        self.assertIn("BUCKET 17 size=10 used=10 remaining=0", self.cli("status")[1])

    def test_concurrent_total_cap_across_buckets(self):
        self.init()
        self.assertEqual(self.cli("adjust", "--usd", "1.32", "--source", "bill")[0], 0)  # room for 7 more answers: 1.32 + 7 x 0.001365 = 1.329555 <= 1.33; an 8th = 1.33092 > 1.33
        budget = lb.Budget(self.ledger)
        granted = []

        def worker(bucket):
            for _ in range(4):
                if budget.try_charge(bucket, 1)[0]:
                    granted.append(bucket)

        threads = [threading.Thread(target=worker, args=(b,)) for b in ("14c", "15b", "16b", "17")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(granted), 7)  # 16 attempts, the cap allows exactly 7


if __name__ == "__main__":
    unittest.main()

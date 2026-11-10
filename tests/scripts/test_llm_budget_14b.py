"""load-tests/llm_budget.py and experiments/manifests/llm-allocation.json, written independently by the test-engineer from the user's
decisions (docs/agent-runs/phase-14/prompt.md, replan answer 6 "Caps: Haiku 4.5 USD 1.50", the 2026-11-08 bucket split and the 2026-11-09 decision "Caps = planned use", cap 1.33):

  * the single Haiku 4.5 cap of USD 1.33 (planned use, was 1.50) is split into answer buckets 14c = 10, 15b = 60, 16b = 40, 17 = 5 (115 answers);
  * the cost per answer comes from the confirmed rates (USD 1.10 input / 5.50 output per 1M tokens, geo route) and the token plan
    (planner 1,500 in + 200 out, synthesis 4,000 in + 800 out): 5,500 x 1.10/1e6 + 1,000 x 5.50/1e6 = 0.01155, hand-derived here;
    115 answers cost 1.32825, which is at most the 1.33 cap;
  * EACH bucket is a hard stop: a reservation beyond a bucket is refused (exit 3) and writes nothing; the shared cap is the backstop;
  * nothing rolls over automatically; a transfer needs the user's approval file.

Every test runs the real CLI (python3 -I) against a TEMPORARY ledger; the user's real ledger is never touched.
"""
import decimal
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

import sc_support as S

TOOL = S.REPO / "load-tests/llm_budget.py"
ALLOCATION = S.REPO / "experiments/manifests/llm-allocation.json"
PROFILE = S.REPO / "load-tests/config/load-profile.v1.json"
SIZES = {"14c": 10, "15b": 60, "16b": 40, "17": 5}
UNIT = (D(5500) * D("1.10") + D(1000) * D("5.50")) / D(1000000)  # hand-derived: 0.01155
CAP = D("1.33")


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="sc-llm-")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.ledger = self.dir / "ledger" / "haiku-ledger.jsonl"

    def run_tool(self, *args, ledger=True, extra_env=None):
        cmd = [sys.executable, "-I", str(TOOL)] + (["--ledger", str(self.ledger)] if ledger else []) + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, env={"PATH": "/usr/bin:/bin", "USER": "tester", "HOME": str(self.dir), **(extra_env or {})})

    def init(self):
        done = self.run_tool("init")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def lines(self):
        return [json.loads(l) for l in self.ledger.read_text().splitlines() if l.strip()] if self.ledger.exists() else []

    def status(self):
        done = self.run_tool("status")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        buckets = {m.group(1): (int(m.group(2)), int(m.group(3)), int(m.group(4))) for m in
                   (re.match(r"BUCKET (\S+) size=(\d+) used=(\d+) remaining=(\d+)", l) for l in done.stdout.splitlines()) if m}
        total = re.search(r"TOTAL answers_used=(\d+) usd_used=([0-9.]+) .*shared_cap_usd=([0-9.]+) remaining_usd=([0-9.]+) unit_usd=([0-9.]+)", done.stdout)
        return buckets, total.groups()


class Pins(unittest.TestCase):
    def test_the_bucket_sizes_in_the_pinned_allocation_are_exactly_10_60_40_5(self):
        doc = json.loads(ALLOCATION.read_text())
        self.assertEqual({k: v["answers"] for k, v in doc["buckets"].items()}, SIZES)
        self.assertEqual(sum(SIZES.values()), 115)

    def test_the_shared_cap_is_one_dollar_thirty_three(self):
        self.assertEqual(D(json.loads(ALLOCATION.read_text())["shared_cap_usd"]), CAP)
        self.assertEqual(D(json.loads(PROFILE.read_text())["llm"]["shared_cap_usd"]), CAP)

    def test_the_unit_cost_is_the_hand_derived_0_01155_from_the_confirmed_rates(self):
        llm = json.loads(PROFILE.read_text())["llm"]
        self.assertEqual((llm["pricing"]["input_usd_per_million_tokens"], llm["pricing"]["output_usd_per_million_tokens"]), ("1.10", "5.50"))
        tokens = llm["tokens_per_answer"]
        derived = (D(tokens["planner_input"] + tokens["synthesis_input"]) * D("1.10") + D(tokens["planner_output"] + tokens["synthesis_output"]) * D("5.50")) / D(1000000)
        self.assertEqual(derived, D("0.01155"))
        self.assertEqual(UNIT, D("0.01155"))
        self.assertEqual(D(llm["cost_multiplier"]), D(1))

    def test_all_buckets_together_cost_at_most_the_cap(self):
        total = UNIT * sum(SIZES.values())
        self.assertEqual(total, D("1.32825"))
        self.assertLessEqual(total, CAP)

    def test_every_other_bucket_cannot_hide_inside_the_file(self):
        doc = json.loads(ALLOCATION.read_text())
        self.assertEqual(sorted(doc["buckets"]), sorted(SIZES))
        self.assertEqual(doc["schema"], "scholarchain.llm-allocation.v2")
        self.assertTrue(all(isinstance(v["answers"], int) and v["answers"] > 0 for v in doc["buckets"].values()))


class Ledger(Base):
    def test_init_writes_the_allocation_hash_and_the_unit_cost_and_refuses_a_second_time(self):
        self.init()
        first = self.lines()
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["event"], "init")
        self.assertEqual(first[0]["alloc_sha256"], hashlib.sha256(ALLOCATION.read_bytes()).hexdigest())
        self.assertEqual(D(first[0]["unit_usd"]), UNIT)
        again = self.run_tool("init")
        self.assertEqual(again.returncode, 3, again.stdout + again.stderr)
        self.assertEqual(self.lines(), first, "the existing ledger is never rewritten")

    def test_status_shows_the_four_buckets_the_unit_and_the_cap(self):
        self.init()
        buckets, total = self.status()
        self.assertEqual(buckets, {k: (v, 0, v) for k, v in SIZES.items()})
        self.assertEqual((int(total[0]), D(total[1]), D(total[2]), D(total[3]), D(total[4])), (0, D(0), CAP, CAP, UNIT))

    def test_the_ledger_is_outside_the_repository_by_default(self):
        text = TOOL.read_text()
        self.assertIn("~/.scholarchain/llm-ledger/haiku-ledger.jsonl", text)
        self.assertNotIn(str(S.REPO), text)

    def test_a_missing_ledger_refuses_reservations(self):
        done = self.run_tool("reserve", "--bucket", "14c", "--answers", "1")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertFalse(self.ledger.exists(), "a reservation never creates the ledger")


class BucketsAreHardStops(Base):
    def test_each_bucket_accepts_exactly_its_size_and_refuses_one_more_without_writing(self):
        self.init()
        for bucket, size in SIZES.items():
            with self.subTest(bucket=bucket):
                done = self.run_tool("reserve", "--bucket", bucket, "--answers", str(size))
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertIn("est_usd=%s" % format((UNIT * size).quantize(D("0.000001")), "f"), done.stdout)
                before = self.ledger.read_text()
                over = self.run_tool("reserve", "--bucket", bucket, "--answers", "1")
                self.assertEqual(over.returncode, 3, over.stdout + over.stderr)
                self.assertIn("REFUSED", over.stderr)
                self.assertEqual(self.ledger.read_text(), before, "a refusal writes nothing")
        buckets, total = self.status()
        self.assertEqual(buckets, {k: (v, v, 0) for k, v in SIZES.items()})
        self.assertEqual((int(total[0]), D(total[1])), (115, D("1.32825")))

    def test_a_reservation_larger_than_the_bucket_is_refused_at_once(self):
        self.init()
        for bucket, size in SIZES.items():
            with self.subTest(bucket=bucket):
                done = self.run_tool("reserve", "--bucket", bucket, "--answers", str(size + 1))
                self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertEqual(len(self.lines()), 1, "only the init line exists")

    def test_the_total_of_partial_reservations_is_bounded_by_the_bucket(self):
        self.init()
        for n in (3, 3, 3):
            self.assertEqual(self.run_tool("reserve", "--bucket", "14c", "--answers", str(n)).returncode, 0)
        self.assertEqual(self.run_tool("reserve", "--bucket", "14c", "--answers", "2").returncode, 3, "9 used + 2 > 10")
        self.assertEqual(self.run_tool("reserve", "--bucket", "14c", "--answers", "1").returncode, 0, "9 used + 1 = 10")

    def test_one_bucket_never_borrows_from_another(self):
        self.init()
        self.assertEqual(self.run_tool("reserve", "--bucket", "17", "--answers", "5").returncode, 0)
        self.assertEqual(self.run_tool("reserve", "--bucket", "17", "--answers", "1").returncode, 3)
        buckets, _ = self.status()
        self.assertEqual(buckets["15b"], (60, 0, 60), "the spare answers of other buckets do not roll over")

    def test_unknown_bucket_zero_negative_and_non_numeric_answers_are_refused(self):
        self.init()
        for args in (("--bucket", "99", "--answers", "1"), ("--bucket", "", "--answers", "1"), ("--bucket", "14c", "--answers", "0"),
                     ("--bucket", "14c", "--answers", "-3"), ("--bucket", "14c", "--answers", "x"), ("--bucket", "14C", "--answers", "1")):
            with self.subTest(args=args):
                done = self.run_tool("reserve", *args)
                self.assertIn(done.returncode, (2, 3), done.stdout + done.stderr)
        self.assertEqual(len(self.lines()), 1)

    def test_release_gives_back_but_never_below_zero(self):
        self.init()
        self.run_tool("reserve", "--bucket", "16b", "--answers", "10")
        self.assertEqual(self.run_tool("release", "--bucket", "16b", "--answers", "4").returncode, 0)
        self.assertEqual(self.status()[0]["16b"], (40, 6, 34))
        self.assertEqual(self.run_tool("release", "--bucket", "16b", "--answers", "7").returncode, 3, "6 used cannot give back 7")
        self.assertEqual(self.status()[0]["16b"], (40, 6, 34))


class SharedCapBackstop(Base):
    def test_the_cap_refuses_even_when_the_bucket_has_room(self):
        self.init()
        done = self.run_tool("adjust", "--usd", "1.28", "--source", "aws-bill-test")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        # 1.28 + 10 x 0.01155 = 1.3955 > 1.33, although bucket 14c is empty
        refused = self.run_tool("reserve", "--bucket", "14c", "--answers", "10")
        self.assertEqual(refused.returncode, 3, refused.stdout + refused.stderr)
        # 1.28 + 4 x 0.01155 = 1.3262 <= 1.33 fits, 5 x = 1.33775 does not
        self.assertEqual(self.run_tool("reserve", "--bucket", "14c", "--answers", "5").returncode, 3)
        self.assertEqual(self.run_tool("reserve", "--bucket", "14c", "--answers", "4").returncode, 0)

    def test_adjust_counts_only_against_the_total(self):
        self.init()
        self.run_tool("adjust", "--usd", "0.40", "--source", "aws-bill-test")
        buckets, total = self.status()
        self.assertEqual(buckets, {k: (v, 0, v) for k, v in SIZES.items()})
        self.assertEqual(D(total[1]), D("0.40"))
        self.assertEqual(D(total[3]), D("0.93"))

    def test_a_negative_or_infinite_adjustment_is_refused(self):
        self.init()
        for usd in ("-0.01", "nan", "inf", "x"):
            with self.subTest(usd=usd):
                self.assertIn(self.run_tool("adjust", "--usd", usd, "--source", "s").returncode, (2, 3))
        self.assertEqual(len(self.lines()), 1)


class Transfers(Base):
    def approval(self, text):
        path = self.dir / "approval.md"
        path.write_text(text)
        return path

    def test_a_transfer_needs_the_exact_approval_line(self):
        self.init()
        self.run_tool("reserve", "--bucket", "15b", "--answers", "10")
        for label, text in (("no file", None), ("wrong amount", "APPROVED_LLM_TRANSFER=15b->16b:6\n"), ("wrong direction", "APPROVED_LLM_TRANSFER=16b->15b:5\n"),
                            ("empty", ""), ("prose only", "please move five answers from 15b to 16b\n")):
            with self.subTest(case=label):
                path = self.approval(text) if text is not None else self.dir / "absent.md"
                done = self.run_tool("transfer", "--from", "15b", "--to", "16b", "--answers", "5", "--approval", str(path))
                self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertEqual(self.status()[0]["16b"], (40, 0, 40), "no refused transfer changed a bucket")

    def test_an_approved_transfer_moves_unused_answers_once(self):
        self.init()
        path = self.approval("APPROVED_LLM_TRANSFER=15b->16b:5\n")
        done = self.run_tool("transfer", "--from", "15b", "--to", "16b", "--answers", "5", "--approval", str(path))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        buckets, total = self.status()
        self.assertEqual((buckets["15b"][0], buckets["16b"][0]), (55, 45))
        self.assertEqual(sum(v[0] for v in buckets.values()), 115, "a transfer never changes the total")
        again = self.run_tool("transfer", "--from", "15b", "--to", "16b", "--answers", "5", "--approval", str(path))
        self.assertEqual(again.returncode, 3, "an approval is not applied twice")

    def test_used_answers_cannot_be_transferred(self):
        self.init()
        self.run_tool("reserve", "--bucket", "15b", "--answers", "58")
        path = self.approval("APPROVED_LLM_TRANSFER=15b->16b:5\n")
        done = self.run_tool("transfer", "--from", "15b", "--to", "16b", "--answers", "5", "--approval", str(path))
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()

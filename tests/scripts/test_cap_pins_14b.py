"""Phase 14B, "Caps = planned use" (user decision 2026-11-09): independent guards for the two spending caps and the pre-spend total.

The user's words: "Caps = planned use (Recommended)". With about 11% sales tax counted toward the USD 25 cap, the caps are exactly the
planned use, every value below is derived by hand here and not read back from the code under test:

  * EMR: 3 live runs x 0.84 USD per run (2 x m5.xlarge at 0.24 USD per hour, 90 minutes cluster time = 2 x 0.24 x 1.5 = 0.72 plus the
    idle tail, planned at 0.84) = 2.52. scripts/config/release.conf pins EMR_CUMULATIVE_CAP_USD=2.52 and EMR_MAX_LIVE_RUNS=3.
  * Haiku 4.5: 115 answers (buckets 10 + 60 + 40 + 5) x 0.01155 USD per answer = 1.32825, so the shared cap is 1.33, which is the smallest
    cap in whole cents that holds the 115 answers and refuses a 116th (116 x 0.01155 = 1.3398 > 1.33). The cap is pinned in BOTH
    experiments/manifests/llm-allocation.json and load-tests/config/load-profile.v1.json, and the two must agree.
  * The H0 receipt arithmetic (derived from docs/agent-runs/phase-14/approval-request-14b-replan.md section 3.2): with every cap reserved
    at once, (11.15 + 1.17 + 2.41 + 0.05 + 0.30 + 2.52 + 1.33 + 0.50) x 1.11 + 0.34 must stay at or below 22.00, which keeps the headroom
    against USD 25 at 3.00 or more. This is a pure arithmetic guard: it reads no file and calls no tool.
"""
import json
import re
import unittest
from decimal import Decimal as D

import sc_support as S

RELEASE_CONF = S.REPO / "scripts/config/release.conf"
ALLOCATION = S.REPO / "experiments/manifests/llm-allocation.json"
PROFILE = S.REPO / "load-tests/config/load-profile.v1.json"

EMR_RUNS = 3
EMR_PER_RUN = D("0.84")
EMR_CAP = D("2.52")
HAIKU_UNIT = D("0.01155")  # (5500 x 1.10 + 1000 x 5.50) / 1,000,000
HAIKU_ANSWERS = 10 + 60 + 40 + 5
HAIKU_CAP = D("1.33")


def conf_values():
    return dict(re.findall(r"^([A-Z][A-Z0-9_]*)=(\S+)\s*$", RELEASE_CONF.read_text(), re.M))


class EmrCumulativeCap(unittest.TestCase):
    def test_the_hand_derivation_is_three_runs_of_eighty_four_cents(self):
        self.assertEqual(EMR_RUNS * EMR_PER_RUN, EMR_CAP)

    def test_release_conf_pins_the_cumulative_cap_at_planned_use(self):
        values = conf_values()
        self.assertEqual(D(values["EMR_CUMULATIVE_CAP_USD"]), EMR_CAP)
        self.assertEqual(D(values["EMR_CUMULATIVE_CAP_USD"]), EMR_RUNS * EMR_PER_RUN)
        self.assertEqual(values["EMR_CUMULATIVE_CAP_USD"], "2.52")

    def test_release_conf_allows_exactly_three_live_runs(self):
        self.assertEqual(int(conf_values()["EMR_MAX_LIVE_RUNS"]), EMR_RUNS)

    def test_the_cap_key_is_defined_once(self):
        self.assertEqual(len(re.findall(r"^EMR_CUMULATIVE_CAP_USD=", RELEASE_CONF.read_text(), re.M)), 1)


class HaikuSharedCap(unittest.TestCase):
    def test_the_hand_derivation_brackets_the_cap(self):
        self.assertEqual(HAIKU_ANSWERS, 115)
        self.assertEqual(HAIKU_ANSWERS * HAIKU_UNIT, D("1.32825"))
        self.assertLessEqual(HAIKU_ANSWERS * HAIKU_UNIT, HAIKU_CAP)
        self.assertLess(HAIKU_CAP, (HAIKU_ANSWERS + 1) * HAIKU_UNIT)

    def test_both_pinned_files_say_one_dollar_thirty_three(self):
        allocation = json.loads(ALLOCATION.read_text())["shared_cap_usd"]
        profile = json.loads(PROFILE.read_text())["llm"]["shared_cap_usd"]
        self.assertEqual(allocation, "1.33")
        self.assertEqual(profile, "1.33")

    def test_the_two_files_agree_with_each_other(self):
        allocation = D(json.loads(ALLOCATION.read_text())["shared_cap_usd"])
        profile = D(json.loads(PROFILE.read_text())["llm"]["shared_cap_usd"])
        self.assertEqual(allocation, profile)

    def test_the_pinned_cap_holds_115_answers_and_refuses_a_116th(self):
        cap = D(json.loads(ALLOCATION.read_text())["shared_cap_usd"])
        self.assertLessEqual(HAIKU_ANSWERS * HAIKU_UNIT, cap)
        self.assertLess(cap, (HAIKU_ANSWERS + 1) * HAIKU_UNIT)


class H0ReceiptArithmetic(unittest.TestCase):
    """Pure arithmetic from approval request section 3.2 (36 h run rate, with 11% sales tax, USD 0.34 already spent)."""

    LINES = {
        "run rate (36 h)": D("11.15"),
        "fixed lines": D("1.17"),
        "usage lines": D("2.41"),
        "tunnel task": D("0.05"),
        "Titan V2 embeddings cap": D("0.30"),
        "EMR cumulative cap": EMR_CAP,
        "Haiku shared cap": HAIKU_CAP,
        "reserve term": D("0.50"),
    }
    TAX_FACTOR = D("1.11")
    ALREADY_SPENT = D("0.34")
    LIMIT = D("22.00")
    CAP_TOTAL = D("25")
    MIN_HEADROOM = D("3")

    def total(self):
        return sum(self.LINES.values(), D(0)) * self.TAX_FACTOR + self.ALREADY_SPENT

    def test_the_new_spend_before_tax_is_nineteen_forty_three(self):
        self.assertEqual(sum(self.LINES.values(), D(0)), D("19.43"))

    def test_the_total_with_every_cap_reserved_is_at_most_twenty_two(self):
        self.assertEqual(self.total(), D("21.9073"))
        self.assertLessEqual(self.total(), self.LIMIT)

    def test_the_headroom_against_twenty_five_is_at_least_three(self):
        self.assertGreaterEqual(self.CAP_TOTAL - self.total(), self.MIN_HEADROOM)
        self.assertEqual(self.CAP_TOTAL - self.total(), D("3.0927"))

    def test_the_old_caps_would_have_broken_the_guard_margin(self):
        old = self.total() + (D("3.00") - EMR_CAP + D("1.50") - HAIKU_CAP) * self.TAX_FACTOR
        self.assertEqual(old, D("22.6288"))
        self.assertGreater(old, self.LIMIT)


if __name__ == "__main__":
    unittest.main()

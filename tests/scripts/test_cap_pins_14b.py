"""Phase 14B "Caps = planned use" (user decision 2026-11-09), amended by Phase 15 P25 and the Phase 15 budget rule: independent
guards for the two spending caps and the project total. Every value below is derived by hand here, not read back from the code
under test.

  * EMR (Phase 15 P25, user 2026-11-16, docs/agent-runs/phase-15/prompt.md line 131, verbatim: "P25: approved. Cap 4 runs and USD 3.36
    cumulative, including Session 1's EMR spend"; raised by the user decision of 2026-11-16 "Raise cap to 3.53"): 4 live runs, and
    3.53 = 1.68 (Session 1: 2 runs at the 0.84 estimate) + 1.85 (Session 2: the D3 block, 2 x (75 min + 15 min idle tail) + 20 min cold
    start = 200 min at 0.555 USD per hour = 1.85 exactly). scripts/config/release.conf pins EMR_CUMULATIVE_CAP_USD=3.53 and
    EMR_MAX_LIVE_RUNS=4. History: P25 pinned 4 runs x 0.84 = 3.36; Phase 14B pinned 3 runs x 0.84 = 2.52.
  * Synthesis (repair round 3, Step 0 answer 3, "easiest"): 160 answers (buckets 10 + 60 + 80 + 10, human "option A" 2026-11-21; was 10 + 60 + 40 + 5 = 115, 0.156975) x 0.001365 USD per answer
    (claude-haiku-5-5, (7150 x 0.10 + 1300 x 0.50) / 1e6) = 0.2184. The shared cap deliberately stays 1.33 (the receipt reserves the full cap), so it is
    still a conservative upper bound and the bucket counts bind first (1.33 / 0.001365 = 974 answers > 160). The cap is pinned in BOTH
    experiments/manifests/llm-allocation.json and load-tests/config/load-profile.v1.json, and the two must agree.
  * Project total (Phase 15 rule). History, Phase 14B H0 receipt arithmetic (approval-request-14b-replan.md section 3.2, a 36 h
    session plan, x 1.11 sales tax, USD 0.34 already spent, limit 22.00 = floor 3):
        (11.15 + 1.17 + 2.41 + 0.05 + 0.30 + 2.52 + 1.33 + 0.50) x 1.11 + 0.34 = 21.9073 <= 22.00
    Those terms no longer describe the Phase 15 plan (Session 1 has been spent, USD 15.83 combined, and Session 2 is priced as R0 + R-b
    blocks), so re-expressing them with the new rule (x 1.00, 3.36 for EMR, the P25 cap then: 20.27 + 0.34 = 20.61 <= 23.00) would guard nothing real.
    The guard now checks the Session 2 plan (docs/runbooks/session-2-plan.md sections 6.2-6.4, an untracked draft read 2026-11-16)
    under the human's two Phase 15 rules recorded in prompt.md:
      - tax 0 on credit-covered spend, factor 1.00 (verbatim: "the portion of your bill deducted/covered by AWS credits is not taxed.
        Since they are credits so tax is 0"), valid while AWS credits cover the spend;
      - option (i), floor 2: the project total must stay at or below 25.00 - 2.00 = 23.00.
    Pure arithmetic plus the release.conf pins: it calls no tool and reads no plan file (the plan figures are copied here as constants).
"""
import json
import re
import unittest
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal as D

import sc_support as S

RELEASE_CONF = S.REPO / "scripts/config/release.conf"
ALLOCATION = S.REPO / "experiments/manifests/llm-allocation.json"
PROFILE = S.REPO / "load-tests/config/load-profile.v1.json"

EMR_RUNS = 4  # Phase 15 P25 (was 3)
EMR_PER_RUN = D("0.84")
EMR_CAP = D("3.53")  # user decision 2026-11-16 "Raise cap to 3.53" (P25 had 3.36, Phase 14B 2.52)
SESSION_2_BLOCK = D("1.85")  # D3: 200 min x 0.555 USD per hour, exact
SESSION_1_RUNS = 2  # the ledger holds 2 Session 1 runs at the 0.84 estimate (prompt.md, coordinator check of P25)
HAIKU_UNIT = D("0.001365")  # (7150 x 0.10 + 1300 x 0.50) / 1,000,000
HAIKU_SIZES = {"14c": 10, "15b": 60, "16b": 80, "17": 10}  # hand-pinned, human option A 2026-11-21
HAIKU_ANSWERS = sum(HAIKU_SIZES.values())
HAIKU_CAP = D("1.33")


def conf_values():
    return dict(re.findall(r"^([A-Z][A-Z0-9_]*)=(\S+)\s*$", RELEASE_CONF.read_text(), re.M))


class EmrCumulativeCap(unittest.TestCase):
    def test_the_hand_derivation_is_session_1_plus_the_d3_session_2_block(self):
        self.assertEqual(SESSION_1_RUNS * EMR_PER_RUN + SESSION_2_BLOCK, EMR_CAP)
        self.assertEqual(D("0.555") * D(2 * (75 + 15) + 20) / D(60), SESSION_2_BLOCK)
        self.assertEqual(EMR_CAP - EMR_RUNS * EMR_PER_RUN, D("0.17"), "the margin over four planned runs, for a measured S overrun")

    def test_release_conf_pins_the_cumulative_cap_at_planned_use(self):
        values = conf_values()
        self.assertEqual(D(values["EMR_CUMULATIVE_CAP_USD"]), EMR_CAP)
        self.assertEqual(D(values["EMR_CUMULATIVE_CAP_USD"]), SESSION_1_RUNS * EMR_PER_RUN + SESSION_2_BLOCK)
        self.assertEqual(values["EMR_CUMULATIVE_CAP_USD"], "3.53")

    def test_release_conf_allows_exactly_four_live_runs(self):
        self.assertEqual(int(conf_values()["EMR_MAX_LIVE_RUNS"]), EMR_RUNS)
        self.assertEqual(conf_values()["EMR_MAX_LIVE_RUNS"], "4")

    def test_after_session_1_exactly_two_more_runs_fit_both_caps(self):
        """The caps are cumulative and include Session 1: 4 - 2 = 2 runs (S and its one S retry; L was dropped on EMR on 2026-11-16) and 3.53 - 1.68 = 1.85, room
        for 2 x 0.84 = 1.68 with 0.17 to spare (2.20 runs). A third Session 2 run would break both the run count and the cumulative
        cap (1.68 + 3 x 0.84 = 4.20 > 3.53)."""
        values = conf_values()
        runs, cap = int(values["EMR_MAX_LIVE_RUNS"]), D(values["EMR_CUMULATIVE_CAP_USD"])
        spent = SESSION_1_RUNS * EMR_PER_RUN
        self.assertEqual(spent, D("1.68"))
        self.assertEqual(runs - SESSION_1_RUNS, 2)
        self.assertEqual(cap - spent, SESSION_2_BLOCK)
        self.assertEqual(int((cap - spent) / EMR_PER_RUN), 2, "two whole planned runs fit, not three")
        self.assertGreater(spent + 3 * EMR_PER_RUN, cap)

    def test_the_cap_keys_are_defined_once(self):
        for key in ("EMR_CUMULATIVE_CAP_USD", "EMR_MAX_LIVE_RUNS"):
            with self.subTest(key=key):
                self.assertEqual(len(re.findall(r"^%s=" % key, RELEASE_CONF.read_text(), re.M)), 1)


class HaikuSharedCap(unittest.TestCase):
    def test_the_hand_derivation_brackets_the_cap(self):
        self.assertEqual(HAIKU_ANSWERS, 160)
        self.assertEqual(HAIKU_ANSWERS, 10 + 60 + 80 + 10)
        self.assertEqual(HAIKU_UNIT, (D(7150) * D("0.10") + D(1300) * D("0.50")) / D(1000000))
        self.assertEqual(HAIKU_ANSWERS * HAIKU_UNIT, D("0.2184"))
        self.assertLessEqual(HAIKU_ANSWERS * HAIKU_UNIT, HAIKU_CAP)
        self.assertGreater(HAIKU_CAP / HAIKU_UNIT, 160, "the bucket counts, not the cap, bind first")

    def test_both_pinned_files_say_one_dollar_thirty_three(self):
        allocation = json.loads(ALLOCATION.read_text())["shared_cap_usd"]
        profile = json.loads(PROFILE.read_text())["llm"]["shared_cap_usd"]
        self.assertEqual(allocation, "1.33")
        self.assertEqual(profile, "1.33")

    def test_the_two_files_agree_with_each_other(self):
        allocation = D(json.loads(ALLOCATION.read_text())["shared_cap_usd"])
        profile = D(json.loads(PROFILE.read_text())["llm"]["shared_cap_usd"])
        self.assertEqual(allocation, profile)

    def test_the_pinned_cap_holds_160_answers_and_the_unit_is_pinned_at_haiku_5_5_prices(self):
        cap = D(json.loads(ALLOCATION.read_text())["shared_cap_usd"])
        self.assertLessEqual(HAIKU_ANSWERS * HAIKU_UNIT, cap)
        pricing = json.loads(PROFILE.read_text())["llm"]["pricing"]
        self.assertEqual((pricing["input_usd_per_million_tokens"], pricing["output_usd_per_million_tokens"]), ("0.10", "0.50"))


class HaikuAllocationCrossCheck(unittest.TestCase):
    """The hand-pinned bucket sizes must equal the sizes in the allocation manifest, so this file cannot go stale silently."""

    def test_the_manifest_bucket_sizes_equal_the_pinned_sizes(self):
        buckets = json.loads(ALLOCATION.read_text())["buckets"]
        self.assertEqual({k: v["answers"] for k, v in buckets.items()}, HAIKU_SIZES)

    def test_the_manifest_total_cost_stays_under_the_cap(self):
        doc = json.loads(ALLOCATION.read_text())
        total = sum(v["answers"] for v in doc["buckets"].values())
        self.assertEqual(total, HAIKU_ANSWERS)
        self.assertLessEqual(total * HAIKU_UNIT, D(doc["shared_cap_usd"]))


class Phase15ProjectArithmetic(unittest.TestCase):
    """The Session 2 plan at caps under the Phase 15 rule (tax factor 1.00, floor 2, project <= 23.00); figures from
    session-2-plan.md sections 6.2-6.4 (draft read 2026-11-16), all in USD. Replaces the Phase 14B H0 receipt check (history in the
    module docstring)."""

    AWS_BEFORE_CREDITS = D("15.75")  # Session 1 AWS usage before credits (Cost Explorer, plan 6.2)
    ANTHROPIC_SPENT = D("0.075")  # Session 1, 55 answers
    VOYAGE_SPENT = D("0")
    TAX_FACTOR = D("1.00")  # Phase 15 tax decision (was 1.11 in Phase 14B)
    FIRM_LIMIT = D("25")
    FLOOR = D("2")  # option (i), 2026-11-16 (was 3 in Phase 14B)
    # session-2-plan.md 6.3-6.4 as published after D3 (documentation-engineer, read 2026-11-16): R0 cap 3.58, R0 + R-b cap 7.15,
    # project at caps 22.98 (margin 0.02), planned 19.54. History: before D3 (and L dropped) R0 3.57, 7.14, 22.97 (margin 0.03).
    R0_CAP = D("3.58")
    PRE_D3_R0_CAP = D("3.57")
    E_B = D("3.57")  # R-b cap with the 5.8 h Neptune hard stop at the 0.402/h ceiling
    LLM_ITEMS_CAP = D("0.42")  # Voyage 0.30 + Anthropic 0.10 + Voyage cache misses of the R-b load 0.02
    EMR_RATE = D("0.50")  # per cluster-hour (plan 6.1), the pre-D3 block rate
    EMR_BLOCK_HOURS = D("3.83")  # pre-D3: S + L at 90 min + 20 min cold start
    EMR_BLOCK_CAP = D("1.92")  # pre-D3 block inside the plan's R0 cap 3.57
    # Phase 15 D3 (human, prompt.md "D3 decision" and "S run cap and D3 go-ahead", 2026-11-16): r5.xlarge primary, m5.xlarge core,
    # S run cap 75 min. Rates from scripts/config/emr-pricing.conf (coordinator read of the public price lists, 2026-11-16):
    # r5.xlarge 0.252 + 0.063 = 0.315, m5.xlarge 0.192 + 0.048 = 0.240, cluster 0.555 per hour.
    D3_CLUSTER_RATE = D("0.315") + D("0.240")
    D3_RUN_MINUTES = 75
    D3_RATE_WITH_MARGIN = D("0.58")  # the plan rate published in 6.3 (0.555 + about 0.02 EBS, rounded up)
    CENT = D("0.01")

    def spent(self):
        return (self.AWS_BEFORE_CREDITS * self.TAX_FACTOR + self.ANTHROPIC_SPENT + self.VOYAGE_SPENT).quantize(self.CENT, ROUND_HALF_UP)

    def limit(self):
        return self.FIRM_LIMIT - self.FLOOR

    def test_the_rule_is_factor_one_and_limit_twenty_three(self):
        self.assertEqual(self.TAX_FACTOR, D("1.00"))
        self.assertEqual(self.limit(), D("23.00"))
        self.assertEqual(self.spent(), D("15.83"))
        self.assertEqual(self.limit() - self.spent(), D("7.17"), "S at floor 2")

    def test_r0_plus_r_b_at_caps_keeps_the_project_at_or_below_twenty_three(self):
        self.assertEqual(self.PRE_D3_R0_CAP + self.E_B, D("7.14"), "history: the pre-D3 cap")
        self.assertEqual(self.spent() + self.PRE_D3_R0_CAP + self.E_B, D("22.97"), "history: the pre-D3 project at caps")
        cap = self.R0_CAP + self.E_B
        self.assertEqual(cap, D("7.15"))
        self.assertLessEqual(cap, self.limit() - self.spent())
        project = self.spent() + cap
        self.assertEqual(project, D("22.98"))
        self.assertLessEqual(project, self.limit())
        self.assertEqual(self.limit() - project, D("0.02"), "the plan's stated margin (0.03 before D3)")
        self.assertEqual(cap - self.LLM_ITEMS_CAP, D("6.73"), "the Session 2 AWS cap the credit balance must cover (6.72 before D3)")

    def test_the_emr_cap_fits_inside_the_r0_emr_block(self):
        """Pre-D3 history (the plan's published 6.4 figures until the D3 rounding is published): the R0 EMR block is 3.83
        cluster-hours: 2 runs x (90 min + 15 min idle tail) = 3.50 h + 20 min cold start = 3.833 h,
        x 0.50 = 1.915, so 1.92. The ledger's remaining Session 2 allowance under the pinned cap is 3.53 - 1.68 = 1.85 (the D3 block),
        inside the 1.92 block of the plan's 7.14."""
        hours = (2 * (D(90) + D(15)) + D(20)) / D(60)
        self.assertEqual(hours.quantize(self.CENT, ROUND_HALF_UP), self.EMR_BLOCK_HOURS)
        self.assertEqual((self.EMR_BLOCK_HOURS * self.EMR_RATE).quantize(self.CENT, ROUND_HALF_UP), self.EMR_BLOCK_CAP)
        cap = D(conf_values()["EMR_CUMULATIVE_CAP_USD"])
        allowance = cap - SESSION_1_RUNS * EMR_PER_RUN
        self.assertEqual(allowance, D("1.85"))
        self.assertLessEqual(allowance, self.EMR_BLOCK_CAP)
        self.assertLessEqual(allowance, self.R0_CAP)

    def test_d3_emr_block_is_exactly_1_85_and_the_project_at_caps_stays_at_or_below_twenty_three(self):
        """D3 restatement of the block: 2 runs x (75 min + 15 min idle tail) + 20 min cold start = 200 min = 3.33 h, at 0.555/h
        = 1.85 exactly (was 3.83 h x 0.50 = 1.92). The plan publishes the margin rate 0.58/h (3.33 x 0.58 = 1.9314, 1.93; plan 6.3,
        read 2026-11-16); the guard checks both the exact block and the published one. Replacing
        the 1.92 block inside R0 + R-b at caps (7.14, project 22.97): exact 15.83 + 7.14 - 1.92 + 1.85 = 22.90; with the margin
        22.98 (the human's "22.98 / 23.00"). Both stay at or below 23.00."""
        minutes = 2 * (self.D3_RUN_MINUTES + 15) + 20
        self.assertEqual(minutes, 200)
        block = self.D3_CLUSTER_RATE * D(minutes) / D(60)
        self.assertEqual(self.D3_CLUSTER_RATE, D("0.555"))
        self.assertEqual(block, D("1.85"), "exact, no rounding needed")
        hours = (D(minutes) / D(60)).quantize(self.CENT, ROUND_HALF_UP)
        self.assertEqual(hours, D("3.33"))
        margin_block = (hours * self.D3_RATE_WITH_MARGIN).quantize(self.CENT, ROUND_HALF_UP)  # the plan rounds blocks half-up (1.915 -> 1.92)
        self.assertEqual(margin_block, D("1.93"))
        # published (plan 6.3): 0.58 per cluster-hour = model 0.555 + about 0.02 EBS = 0.575, rounded UP to the cent; block 1.93;
        # R0 cap = 3.57 - 1.92 + 1.93 = 3.58
        self.assertEqual((self.D3_CLUSTER_RATE + D("0.02")).quantize(self.CENT, ROUND_UP), self.D3_RATE_WITH_MARGIN)
        self.assertEqual(self.PRE_D3_R0_CAP - self.EMR_BLOCK_CAP + margin_block, self.R0_CAP)
        pre_d3_cap = self.PRE_D3_R0_CAP + self.E_B
        for label, emr_block, project in (("exact", block, D("22.90")), ("margin", margin_block, D("22.98"))):
            with self.subTest(block=label):
                total = self.spent() + pre_d3_cap - self.EMR_BLOCK_CAP + emr_block
                self.assertEqual(total, project)
                self.assertLessEqual(total, self.limit())
        # at the 90-minute cap the same rule breaks the limit, which is why the human chose 75 min: 3.83 h x 0.555 = 2.13 (exact rate)
        over = self.spent() + pre_d3_cap - self.EMR_BLOCK_CAP + (self.EMR_BLOCK_HOURS * self.D3_CLUSTER_RATE).quantize(self.CENT, ROUND_UP)
        self.assertGreater(over, self.limit())

    def test_d3_ledger_leaves_a_seventeen_cent_margin_under_the_cumulative_cap(self):
        """Per run (the budget.py method, rounded UP to the cent): 0.555 x (75 x 60 + 900) / 3600 = 0.555 x 1.5 = 0.8325, so 0.84.
        Session 1 (1.68) + S 0.84 + the one S retry 0.84 = 3.36 against the pinned 3.53: allowed with 0.17 margin (the room for a measured S
        overrun); the margin is exactly the D3 block (1.85) less the two planned runs (1.68)."""
        per_run = (self.D3_CLUSTER_RATE * D(self.D3_RUN_MINUTES * 60 + 900) / D(3600)).quantize(self.CENT, ROUND_UP)
        self.assertEqual(per_run, D("0.84"))
        cap = D(conf_values()["EMR_CUMULATIVE_CAP_USD"])
        total = SESSION_1_RUNS * EMR_PER_RUN + 2 * per_run
        self.assertEqual(total, D("3.36"))
        self.assertLessEqual(total, cap)
        self.assertEqual(cap - total, D("0.17"))
        self.assertGreater(total + D("0.18"), cap)

    def test_the_dropped_tax_column_would_have_broken_the_limit(self):
        """Why the factor matters (plan 6.4, column B, dropped 2026-11-16; pre-D3 figures, history): 15.75 x 1.11 + 0.075 = 17.5575 (17.56), then
        17.56 + 1.11 x 6.72 + 0.42 = 25.4392 (25.44), above both 23.00 and the firm 25.00."""
        spent_b = (self.AWS_BEFORE_CREDITS * D("1.11") + self.ANTHROPIC_SPENT).quantize(self.CENT, ROUND_HALF_UP)
        self.assertEqual(spent_b, D("17.56"))
        project_b = (spent_b + D("1.11") * (self.PRE_D3_R0_CAP + self.E_B - self.LLM_ITEMS_CAP) + self.LLM_ITEMS_CAP).quantize(self.CENT, ROUND_HALF_UP)
        self.assertEqual(project_b, D("25.44"))
        self.assertGreater(project_b, self.FIRM_LIMIT)


if __name__ == "__main__":
    unittest.main()

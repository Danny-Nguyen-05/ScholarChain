"""Offline label-only and independent rational-arithmetic checks; no writes/network."""
from pathlib import Path
from fractions import Fraction
import ast
import json

packet = Path(__file__).resolve().parent.parent
old = "ancillary_cleanup_delayed_24h"
new = "ancillary resources active 24 h total (21 h beyond nominal)"
before = json.loads((packet / "l1-wording-repair/before/cost-calculations.json").read_text())
after = json.loads((packet / "cost-calculations.json").read_text())
assert before["scenarios"][3]["name"] == old
assert after["scenarios"][3]["name"] == new
normalized = json.loads(json.dumps(after))
normalized["scenarios"][3]["name"] = old
assert normalized == before
assert ast.dump(ast.parse((packet / "replay-cost.py").read_text().replace(new, old))) == ast.dump(
    ast.parse((packet / "l1-wording-repair/before/replay-cost.py").read_text())
)
scenarios = after["scenarios"]
nominal = Fraction(scenarios[0]["quantities"]["ancillary_hours"])
scenario = scenarios[3]
hours = Fraction(scenario["quantities"]["ancillary_hours"])
assert nominal == 3 and hours == 24 and hours - nominal == 21
for key in ["lambda_invocations", "scheduler_invocations", "state_transitions"]:
    assert Fraction(scenario["quantities"][key]) / Fraction(scenarios[0]["quantities"][key]) == 8
for scenario in scenarios:
    subtotal = sum(Fraction(row["usd"]) for row in scenario["line_items"])
    assert abs(subtotal - Fraction(scenario["subtotal_usd"])) < Fraction(1, 10**22)
    total = (
        Fraction(scenario["subtotal_usd"])
        + Fraction(scenario["tax_planning_usd"])
        + Fraction(scenario["uncertainty_reserve_usd"])
    )
    # Saved Decimal components can differ by 5e-28 USD after finite rounding.
    # Match the existing disclosed 1e-22 tolerance, then independently ceil cents.
    assert abs(total - Fraction(scenario["modeled_total_usd"])) < Fraction(1, 10**22)
    assert Fraction((total * 100).__ceil__(), 100) == Fraction(scenario["display_total_usd"])
    assert scenario["launch_authorized"] is False
assert [scenario["display_total_usd"] for scenario in scenarios] == ["5.30", "6.21", "8.54", "7.52", "4.82"]
assert new in (packet / "cost-proposal.md").read_text()
assert new in (packet / "coordinator-report.md").read_text()
assert new in (packet / "record-suffixes/owner-report.md").read_text()
assert new in (packet.parents[1] / "owner-report.md").read_text()
print(json.dumps({
    "scenario_label_corrected": True,
    "only_calculation_json_change_is_label": True,
    "source_ast_equal_after_label_normalization": True,
    "nominal_hours": 3,
    "scenario_total_hours": 24,
    "beyond_nominal_hours": 21,
    "guard_count_scale": 8,
    "fraction_arithmetic_scenarios_checked": 5,
    "display_totals_unchanged": ["5.30", "6.21", "8.54", "7.52", "4.82"],
    "all_launch_flags_false": True,
}, sort_keys=True))

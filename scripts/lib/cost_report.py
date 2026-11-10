#!/usr/bin/env python3
"""Project cost report (stdlib only; python3 -I). Exact decimal arithmetic, fail closed.

  cost_report.py render --input FILE [--format text|json]

Why this exists (instructor ruling 2026-11-09, recorded in docs/agent-runs/phase-14/prompt.md): charges of external API providers
count toward the USD 25 project limit, and the report must list AWS, Anthropic and Voyage AI as SEPARATE items, followed by the
combined total. A provider that charged nothing is listed as USD 0 with its usage documented. This script only formats numbers the
human typed in from the three bills (AWS Cost Explorer, the Anthropic Console, the Voyage AI dashboard); it calls no service and
reads no credential.

INPUT, one JSON object (the human writes it; no key, token or account id belongs in it):

  {
    "schema": "scholarchain.cost-report.v1",
    "as_of_utc": "2026-11-20T12:00:00Z",
    "ceiling_usd": 25,
    "items": {
      "aws":       {"usd": 17.40, "usage": "ECS, Neptune, EMR, NAT, S3 ... as shown in Cost Explorer, tax included"},
      "anthropic": {"usd": 0.81,  "usage": "claude-haiku-5-5: 115 answers, input and output tokens as shown in the Anthropic Console"},
      "voyage":    {"usd": 0,     "usage": "voyage-4-lite: 3.1M tokens, inside the 200M free tokens of the account"}
    }
  }

Rules (every violation prints "COST-REPORT-REFUSED: ..." and exits 1; a usage error exits 2):
  * exactly the three items aws, anthropic and voyage; none may be missing and no other item is accepted (a charge cannot be hidden
    under an unlisted provider);
  * "usd" is a JSON number (not a string, boolean or null; no NaN or Infinity), at least 0 and at most 1,000,000;
  * "usage" is non-empty text of at most 400 characters, REQUIRED for every item (also when the amount is 0: a zero without
    documented usage is refused, so "no charge" always says what was used);
  * "as_of_utc" looks like 2026-11-20T12:00:00Z; "ceiling_usd" is a number above 0 (the project limit, 25).

OUTPUT: the three items in the fixed order AWS, Anthropic, Voyage AI, each with its amount and usage, then the combined total
(exact sum, to the cent), the ceiling and the remaining amount (negative when over). Exit 0 even when the total is over the
ceiling (reporting is not enforcement; the line says OVER THE CEILING).
"""
import argparse
import datetime
import decimal
import json
import sys

D = decimal.Decimal
CENT = D("0.01")
ORDER = (("aws", "AWS"), ("anthropic", "Anthropic"), ("voyage", "Voyage AI"))
MAX_USD = D("1000000")
MAX_USAGE = 400


def _reject_constant(name):
    raise ValueError("non-finite JSON constant %s" % name)


def money(value):
    return value.quantize(CENT, rounding=decimal.ROUND_HALF_UP)


def load(path, problems):
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle, parse_float=D, parse_constant=_reject_constant)
    except (OSError, ValueError) as error:
        problems.append("input unreadable or not valid JSON: %s" % type(error).__name__)
        return None
    if not isinstance(document, dict):
        problems.append("input must be a JSON object")
        return None
    return document


def _amount(item, label, problems):
    value = item.get("usd")
    if isinstance(value, bool) or not isinstance(value, (int, D)):
        problems.append("%s.usd is missing or not a number" % label)
        return None
    value = D(value)
    if not value.is_finite() or value < 0 or value > MAX_USD:
        problems.append("%s.usd must be a finite number from 0 to %s" % (label, MAX_USD))
        return None
    return value


def validate(document, problems):
    """The normalized report (a dict) or None, with every finding appended to PROBLEMS."""
    stamp = document.get("as_of_utc")
    if not isinstance(stamp, str):
        problems.append("as_of_utc is missing")
    else:
        try:
            datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            problems.append("as_of_utc must look like 2026-11-20T12:00:00Z")
    ceiling = document.get("ceiling_usd")
    if isinstance(ceiling, bool) or not isinstance(ceiling, (int, D)) or not D(ceiling).is_finite() or D(ceiling) <= 0:
        problems.append("ceiling_usd is missing or not a number above 0")
        ceiling = None
    else:
        ceiling = D(ceiling)
    items = document.get("items")
    if not isinstance(items, dict):
        problems.append("items must be an object with aws, anthropic and voyage")
        return None
    for name in sorted(set(items) - {key for key, _ in ORDER}):
        problems.append("unlisted item %s: only aws, anthropic and voyage are accepted" % name)
    rows = []
    for key, title in ORDER:
        item = items.get(key)
        if not isinstance(item, dict):
            problems.append("item %s is missing (a provider with no charge is written with usd 0 and its usage)" % key)
            continue
        amount = _amount(item, key, problems)
        usage = item.get("usage")
        if not isinstance(usage, str) or not usage.strip():
            problems.append("%s.usage is missing or empty (documented usage is required, also for USD 0)" % key)
            usage = None
        elif len(usage) > MAX_USAGE or any(ord(ch) < 32 for ch in usage):
            problems.append("%s.usage must be one line of at most %d characters" % (key, MAX_USAGE))
            usage = None
        rows.append((key, title, amount, usage))
    if problems:
        return None
    total = sum((amount for _key, _title, amount, _usage in rows), D(0))
    return {"as_of_utc": stamp, "ceiling": ceiling, "rows": rows, "total": total}


def render_text(report):
    lines = ["Project cost report as of %s" % report["as_of_utc"], ""]
    for key, title, amount, usage in report["rows"]:
        lines.append("%-10s USD %10s   usage: %s" % (title, money(amount), usage))
    lines.append("%-10s USD %10s   (AWS + Anthropic + Voyage AI)" % ("Combined", money(report["total"])))
    remaining = report["ceiling"] - report["total"]
    lines.append("")
    lines.append("Project ceiling USD %s; remaining USD %s%s" % (money(report["ceiling"]), money(remaining), "   OVER THE CEILING" if remaining < 0 else ""))
    return "\n".join(lines) + "\n"


def render_json(report):
    remaining = report["ceiling"] - report["total"]
    payload = {
        "schema": "scholarchain.cost-report.v1",
        "as_of_utc": report["as_of_utc"],
        "items": [{"provider": title, "usd": str(money(amount)), "usage": usage} for _key, title, amount, usage in report["rows"]],
        "combined_total_usd": str(money(report["total"])),
        "ceiling_usd": str(money(report["ceiling"])),
        "remaining_usd": str(money(remaining)),
        "over_ceiling": remaining < 0,
    }
    return json.dumps(payload, indent=2) + "\n"


def cmd_render(args):
    problems = []
    document = load(args.input, problems)
    report = validate(document, problems) if document is not None else None
    if problems or report is None:
        for problem in problems or ["no report"]:
            print("COST-REPORT-REFUSED: %s" % problem)
        return 1
    sys.stdout.write(render_json(report) if args.format == "json" else render_text(report))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("render")
    p.add_argument("--input", required=True)
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(fn=cmd_render)
    return parser


def main(argv):
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

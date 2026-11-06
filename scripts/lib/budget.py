#!/usr/bin/env python3
"""G6 EMR cost guard (stdlib; python3 -I). Exact decimal arithmetic, fail closed.

  estimate --instance-type T --primary-count N --core-count N --task-count N --minutes M
           --ec2-rate R --emr-rate R --max-run-usd C --budget-usd B
        estimate = (primary + core + task) x (EC2 rate + EMR uplift) x (M / 60), rounded UP to the cent.
        Prints one JSON object on stdout. Exit 2 with "G6-UNAVAILABLE: ..." lines when a rate is unset, not a
        positive decimal or not finite: the estimate cannot be computed, and it is never guessed or read as zero (a
        dry run reports it, --execute refuses). Exit 1 with "G6-REFUSED: ..." lines when the estimate exceeds the
        per-run cap C or the declared budget B, or an input is invalid.
  ledger-check --ledger FILE --estimate E --max-runs N --cumulative-cap C
        Reads the local run ledger (absent = no runs). Refuses when N live runs are already recorded or when the
        recorded estimates plus E would exceed C. An unreadable or malformed ledger refuses (never read as empty).
  ledger-reserve --root R --ledger FILE --run-id ID --estimate E --max-runs N --cumulative-cap C
                 --action A --run-config-sha256 H --reserved-utc T
        Repeats the ledger check under an exclusive file lock and appends one JSON line (event "reserve") to the
        ledger, creating it exclusively (safeio, never through a symlink) when absent. A reservation counts for
        good: a failed run may have spent money, so only a human editing the ignored file can release one.

The ledger is one JSON object per line: {"event": "reserve", "run_id", "action", "estimate_usd", "run_config_sha256",
"reserved_utc"}. It is local and git-ignored (under target/); it is not evidence.
"""
import argparse
import decimal
import fcntl
import importlib.util
import json
import os
import sys

D = decimal.Decimal
CENT = D("0.01")


def _safeio():
    spec = importlib.util.spec_from_file_location("sc_safeio", os.path.join(os.path.dirname(os.path.abspath(__file__)), "safeio.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_decimal(text, label, problems, positive=True):
    """A finite decimal from TEXT, or None with a problem recorded. Rejects empty, nan, inf, exponent-free garbage."""
    if text is None or str(text).strip() == "":
        problems.append("%s is unset" % label)
        return None
    try:
        value = D(str(text).strip())
    except decimal.InvalidOperation:
        problems.append("%s is not a decimal number" % label)
        return None
    if not value.is_finite():
        problems.append("%s is not finite" % label)
        return None
    if positive and value <= 0:
        problems.append("%s must be positive" % label)
        return None
    if value < 0:
        problems.append("%s must not be negative" % label)
        return None
    return value


def money(value):
    return format(value.quantize(CENT, rounding=decimal.ROUND_UP), "f")


def cmd_estimate(args):
    problems = []
    ec2 = parse_decimal(args.ec2_rate, "the EC2 on-demand hourly rate for %s (EMR_RATE_EC2_*)" % args.instance_type, problems)
    emr = parse_decimal(args.emr_rate, "the EMR uplift hourly rate for %s (EMR_RATE_EMR_*)" % args.instance_type, problems)
    rate_problems = list(problems)
    del problems[:]
    cap = parse_decimal(args.max_run_usd, "the per-run cap", problems)
    budget = parse_decimal(args.budget_usd, "the declared budget", problems)
    for label, value in (("primary", args.primary_count), ("core", args.core_count), ("task", args.task_count)):
        if value < 0:
            problems.append("%s count must not be negative" % label)
    nodes = args.primary_count + args.core_count + args.task_count
    if nodes < 1:
        problems.append("at least one instance is required")
    if args.minutes < 1:
        problems.append("the maximum runtime must be at least one minute")
    estimate = None
    if rate_problems and not problems:
        # No reviewed rate: the estimate cannot be computed. Never guessed, never zero (exit 2 = unavailable).
        for problem in rate_problems:
            print("G6-UNAVAILABLE: %s" % problem)
        return 2
    problems = rate_problems + problems
    if not problems:
        hourly = (ec2 + emr) * nodes
        estimate = (hourly * D(args.minutes) / D(60)).quantize(CENT, rounding=decimal.ROUND_UP)
        if budget > cap:
            problems.append("the declared budget %s USD exceeds the per-run cap %s USD" % (money(budget), money(cap)))
        if estimate > cap:
            problems.append("estimate %s USD exceeds the per-run cap %s USD" % (money(estimate), money(cap)))
        if estimate > budget:
            problems.append("estimate %s USD exceeds the declared budget %s USD" % (money(estimate), money(budget)))
    for problem in problems:
        print("G6-REFUSED: %s" % problem)
    if problems:
        return 1
    print(
        json.dumps(
            {
                "instance_type": args.instance_type,
                "instances": nodes,
                "ec2_rate_usd_per_hour": format(ec2, "f"),
                "emr_rate_usd_per_hour": format(emr, "f"),
                "hourly_usd": format((ec2 + emr) * nodes, "f"),
                "max_runtime_minutes": args.minutes,
                "estimate_usd": money(estimate),
                "formula": "instances x (EC2 on-demand + EMR uplift) x max_runtime_hours, rounded up to the cent",
            },
            sort_keys=True,
        )
    )
    return 0


def read_ledger(path):
    """Returns (live_runs, cumulative Decimal). Absent file: (0, 0). Raises ValueError on an unreadable ledger."""
    if not os.path.lexists(path):
        return 0, D(0)
    if os.path.islink(path) or not os.path.isfile(path):
        raise ValueError("the ledger is not a regular file")
    runs = 0
    total = D(0)
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if entry.get("event") != "reserve":
                    raise ValueError("unknown event")
                value = D(str(entry["estimate_usd"]))
                if not value.is_finite() or value < 0:
                    raise ValueError("bad estimate")
            except (ValueError, KeyError, TypeError, decimal.InvalidOperation, AttributeError):
                raise ValueError("ledger line %d is malformed" % number)
            runs += 1
            total += value
    return runs, total


def ledger_problems(path, estimate, max_runs, cap):
    problems = []
    try:
        runs, total = read_ledger(path)
    except (OSError, ValueError) as error:
        return None, None, ["the run ledger cannot be read (%s): refusing rather than reading it as empty" % error]
    if runs >= max_runs:
        problems.append("%d live EMR runs are already recorded in the ledger (limit %d)" % (runs, max_runs))
    if total + estimate > cap:
        problems.append("cumulative estimate %s USD (recorded %s + this run %s) would exceed the cap %s USD" % (money(total + estimate), money(total), money(estimate), money(cap)))
    return runs, total, problems


def _ledger_args(args):
    problems = []
    estimate = parse_decimal(args.estimate, "the estimate", problems)
    cap = parse_decimal(args.cumulative_cap, "the cumulative cap", problems)
    if problems:
        for problem in problems:
            print("G6-REFUSED: %s" % problem)
        return None
    return estimate, cap


def cmd_ledger_check(args):
    parsed = _ledger_args(args)
    if parsed is None:
        return 1
    estimate, cap = parsed
    runs, total, problems = ledger_problems(args.ledger, estimate, args.max_runs, cap)
    for problem in problems:
        print("G6-REFUSED: %s" % problem)
    if problems:
        return 1
    print("LEDGER: live_runs=%d of %d cumulative_usd=%s this_run_usd=%s cap_usd=%s" % (runs, args.max_runs, money(total), money(estimate), money(cap)))
    return 0


def cmd_ledger_reserve(args):
    parsed = _ledger_args(args)
    if parsed is None:
        return 1
    estimate, cap = parsed
    safeio = _safeio()
    lock_path = args.ledger + ".lock"
    try:
        try:
            safeio.open_new(args.root, lock_path).close()
        except safeio.Refused:
            pass  # the lock file already exists
        try:
            safeio.open_new(args.root, args.ledger).close()
        except safeio.Refused:
            pass  # the ledger already exists
        lock_handle = safeio.open_append_existing(args.root, lock_path)
        with lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            runs, total, problems = ledger_problems(args.ledger, estimate, args.max_runs, cap)
            for problem in problems:
                print("G6-REFUSED: %s" % problem)
            if problems:
                return 1
            entry = {
                "event": "reserve",
                "run_id": args.run_id,
                "action": args.action,
                "estimate_usd": money(estimate),
                "run_config_sha256": args.run_config_sha256,
                "reserved_utc": args.reserved_utc,
            }
            with safeio.open_append_existing(args.root, args.ledger) as handle:
                handle.write((json.dumps(entry, sort_keys=True) + "\n").encode("utf-8"))
            print("LEDGER-RESERVED: run=%s live_runs=%d of %d cumulative_usd=%s" % (args.run_id, runs + 1, args.max_runs, money(total + estimate)))
            return 0
    except (safeio.Refused, OSError) as error:
        print("G6-REFUSED: the run ledger could not be updated safely (%s)" % (error if isinstance(error, safeio.Refused) else type(error).__name__))
        return 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("estimate")
    p.add_argument("--instance-type", required=True)
    p.add_argument("--primary-count", type=int, required=True)
    p.add_argument("--core-count", type=int, required=True)
    p.add_argument("--task-count", type=int, required=True)
    p.add_argument("--minutes", type=int, required=True)
    p.add_argument("--ec2-rate", default="")
    p.add_argument("--emr-rate", default="")
    p.add_argument("--max-run-usd", required=True)
    p.add_argument("--budget-usd", required=True)
    p.set_defaults(fn=cmd_estimate)
    p = sub.add_parser("ledger-check")
    p.add_argument("--ledger", required=True)
    p.add_argument("--estimate", required=True)
    p.add_argument("--max-runs", type=int, required=True)
    p.add_argument("--cumulative-cap", required=True)
    p.set_defaults(fn=cmd_ledger_check)
    p = sub.add_parser("ledger-reserve")
    p.add_argument("--root", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--estimate", required=True)
    p.add_argument("--max-runs", type=int, required=True)
    p.add_argument("--cumulative-cap", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--run-config-sha256", required=True)
    p.add_argument("--reserved-utc", required=True)
    p.set_defaults(fn=cmd_ledger_reserve)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))

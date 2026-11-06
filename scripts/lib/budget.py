#!/usr/bin/env python3
"""G6 EMR cost guard (stdlib; python3 -I). Exact decimal arithmetic, fail closed.

  estimate --instance-type T --primary-count N --core-count N --task-count N --minutes M --idle-seconds S
           --ec2-rate R --emr-rate R --max-run-usd C --budget-usd B
        estimate = (primary + core + task) x (EC2 rate + EMR uplift) x (M x 60 + S) / 3600, rounded UP to the cent.
        M is the maximum runtime and S the largest auto-termination idle timeout the cluster may have (13C finding B3:
        the idle tail is billed too).
        Prints one JSON object on stdout. Exit 2 with "G6-UNAVAILABLE: ..." lines when a rate is unset, not a
        positive decimal or not finite: the estimate cannot be computed, and it is never guessed or read as zero (a
        dry run reports it, --execute refuses). Exit 1 with "G6-REFUSED: ..." lines when the estimate exceeds the
        per-run cap C or the declared budget B, or an input is invalid.
  ledger-init --root R --within-name N --within W --ledger FILE --repo-root REPO --initialized-by WHO --initialized-utc T
        Creates the ledger exclusively (safeio, never through a symlink) with one "init" record (who and when). It
        REFUSES when the ledger already exists, so an existing ledger can never be reset by a script.
  ledger-check --ledger FILE --repo-root REPO --estimate E --max-runs N --cumulative-cap C [--approval-sha256 H]
        Reads the run ledger. An ABSENT or uninitialised ledger refuses (13C finding B2: it is never read as zero runs).
        Refuses when N live runs are already recorded, when the recorded estimates plus E would exceed C, or (with
        --approval-sha256) when that approval record was already used by an earlier run (finding B4). An unreadable or
        malformed ledger refuses (never read as empty).
  ledger-reserve --root R --ledger FILE --repo-root REPO --run-id ID --estimate E --max-runs N --cumulative-cap C
                 --action A --run-config-sha256 H --approval-sha256 H --reserved-utc T
        Repeats the ledger check under an exclusive file lock and appends one JSON line (event "reserve") to the
        ledger. It never creates the ledger. A reservation counts for good: a failed run may have spent money, so only a
        human editing the file can release one. The approval record sha256 is stored with it, so the same record can
        never start a second run, even after a failed one.

The ledger is one JSON object per line. Line 1 is {"event": "init", "initialized_by", "initialized_utc"}; every later line
is {"event": "reserve", "run_id", "action", "estimate_usd", "run_config_sha256", "approval_record_sha256",
"reserved_utc"}. It lives outside the repository and outside sbt's target/ (EMR_LEDGER_PATH, by default under
~/.scholarchain/emr-ledger/): a clean checkout or `sbt clean` cannot erase it. It is local state, not evidence.
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
    if args.idle_seconds < 0:
        problems.append("the auto-termination idle timeout must not be negative")
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
        billed_seconds = args.minutes * 60 + args.idle_seconds
        estimate = (hourly * D(billed_seconds) / D(3600)).quantize(CENT, rounding=decimal.ROUND_UP)
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
                "idle_timeout_seconds": args.idle_seconds,
                "billed_seconds": billed_seconds,
                "estimate_usd": money(estimate),
                "formula": "instances x (EC2 on-demand + EMR uplift) x (max_runtime + idle_timeout) hours, rounded up to the cent",
            },
            sort_keys=True,
        )
    )
    return 0


HEX64 = "0123456789abcdef"


class LedgerAbsent(ValueError):
    pass


def ledger_location_problem(ledger, repo_root):
    """The ledger must be an absolute path with no '..' that lies OUTSIDE the repository (13C finding B2)."""
    if not isinstance(ledger, str) or not os.path.isabs(ledger):
        return "the ledger path must be absolute (EMR_LEDGER_PATH is expanded from ~ against HOME)"
    if ".." in ledger.split(os.sep):
        return "the ledger path must not contain '..'"
    real_ledger = os.path.realpath(ledger)
    real_repo = os.path.realpath(repo_root)
    if real_ledger == real_repo or real_ledger.startswith(real_repo + os.sep):
        return "the ledger must live outside the repository (sbt clean, git clean or a fresh clone would erase it)"
    return None


def read_ledger(path):
    """Returns (live_runs, cumulative Decimal, approval sha256 set).

    Raises LedgerAbsent when the file does not exist and ValueError when it is unreadable, not initialised (the first
    line must be the "init" record) or malformed. A ledger is never read as empty."""
    if not os.path.lexists(path):
        raise LedgerAbsent("the run ledger %s does not exist; the human creates it once with run-bounded-pipeline.sh --init-ledger" % path)
    if os.path.islink(path) or not os.path.isfile(path):
        raise ValueError("the ledger is not a regular file")
    runs = 0
    total = D(0)
    approvals = set()
    seen_init = False
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                event = entry.get("event")
                if not seen_init:
                    if event != "init" or not isinstance(entry.get("initialized_by"), str) or not isinstance(entry.get("initialized_utc"), str):
                        raise ValueError("the first record must be the init record")
                    seen_init = True
                    continue
                if event != "reserve":
                    raise ValueError("unknown event")
                value = D(str(entry["estimate_usd"]))
                if not value.is_finite() or value < 0:
                    raise ValueError("bad estimate")
                approval = entry.get("approval_record_sha256")
                if approval is not None:
                    if not isinstance(approval, str) or len(approval) != 64 or any(c not in HEX64 for c in approval):
                        raise ValueError("bad approval record hash")
                    approvals.add(approval)
            except (ValueError, KeyError, TypeError, decimal.InvalidOperation, AttributeError):
                raise ValueError("ledger line %d is malformed" % number)
            runs += 1
            total += value
    if not seen_init:
        raise ValueError("the ledger has no init record (an empty file is not an initialised ledger)")
    return runs, total, approvals


def ledger_problems(path, estimate, max_runs, cap, approval_sha=None, repo_root=None):
    problems = []
    if repo_root is not None:
        located = ledger_location_problem(path, repo_root)
        if located:
            return None, None, [located]
    try:
        runs, total, approvals = read_ledger(path)
    except LedgerAbsent as error:
        return None, None, ["%s (an absent ledger is never read as zero runs)" % error]
    except (OSError, ValueError) as error:
        return None, None, ["the run ledger cannot be read (%s): refusing rather than reading it as empty" % error]
    if runs >= max_runs:
        problems.append("%d live EMR runs are already recorded in the ledger (limit %d)" % (runs, max_runs))
    if total + estimate > cap:
        problems.append("cumulative estimate %s USD (recorded %s + this run %s) would exceed the cap %s USD" % (money(total + estimate), money(total), money(estimate), money(cap)))
    if approval_sha is not None and approval_sha in approvals:
        problems.append("this approval record (sha256 %s) already started a run: an approval is single-use, even after a failed run; the human writes a new record" % approval_sha)
    return runs, total, problems


def _ledger_args(args):
    problems = []
    estimate = parse_decimal(args.estimate, "the estimate", problems)
    cap = parse_decimal(args.cumulative_cap, "the cumulative cap", problems)
    approval = getattr(args, "approval_sha256", None)
    if approval is not None and (len(approval) != 64 or any(c not in HEX64 for c in approval)):
        problems.append("--approval-sha256 is not 64 lowercase hex")
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
    runs, total, problems = ledger_problems(args.ledger, estimate, args.max_runs, cap, getattr(args, "approval_sha256", None), args.repo_root)
    for problem in problems:
        print("G6-REFUSED: %s" % problem)
    if problems:
        return 1
    print("LEDGER: live_runs=%d of %d cumulative_usd=%s this_run_usd=%s cap_usd=%s" % (runs, args.max_runs, money(total), money(estimate), money(cap)))
    return 0


def cmd_ledger_init(args):
    safeio = _safeio()
    located = ledger_location_problem(args.ledger, args.repo_root)
    if located:
        print("G6-REFUSED: %s" % located)
        return 1
    if os.path.lexists(args.ledger):
        print("G6-REFUSED: the run ledger %s already exists: refusing to re-initialise it (a script never resets the spend record; resetting it is a deliberate human act)" % args.ledger)
        return 1
    if not args.initialized_by or any(c in args.initialized_by for c in "\r\n"):
        print("G6-REFUSED: --initialized-by must be a single-line name")
        return 1
    try:
        real_root = os.path.realpath(args.root)
        directory = safeio.confine(args.root, os.path.dirname(args.ledger), args.within_name, args.within, allow_base=True)
        safeio.ensure_dirs(real_root, directory)
        handle = safeio.open_new(args.root, args.ledger)
    except safeio.Refused as error:
        print("G6-REFUSED: the run ledger could not be created safely (%s)" % error)
        return 1
    except OSError as error:
        print("G6-REFUSED: the run ledger could not be created (%s)" % type(error).__name__)
        return 1
    with handle:
        record = {"event": "init", "initialized_by": args.initialized_by, "initialized_utc": args.initialized_utc, "schema": "scholarchain.emr-ledger.v2"}
        handle.write((json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
    print("LEDGER-INITIALIZED: %s by %s at %s" % (args.ledger, args.initialized_by, args.initialized_utc))
    return 0


def cmd_ledger_reserve(args):
    parsed = _ledger_args(args)
    if parsed is None:
        return 1
    estimate, cap = parsed
    located = ledger_location_problem(args.ledger, args.repo_root)
    if located:
        print("G6-REFUSED: %s" % located)
        return 1
    if not os.path.lexists(args.ledger):
        # Never create the ledger here: an absent ledger refuses (finding B2), so a reset cannot reopen the caps.
        print("G6-REFUSED: the run ledger %s does not exist; the human creates it once with run-bounded-pipeline.sh --init-ledger (an absent ledger is never read as zero runs)" % args.ledger)
        return 1
    safeio = _safeio()
    lock_path = args.ledger + ".lock"
    try:
        try:
            safeio.open_new(args.root, lock_path).close()
        except safeio.Refused:
            pass  # the lock file already exists
        lock_handle = safeio.open_append_existing(args.root, lock_path)
        with lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            runs, total, problems = ledger_problems(args.ledger, estimate, args.max_runs, cap, args.approval_sha256)
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
                "approval_record_sha256": args.approval_sha256,
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
    p.add_argument("--idle-seconds", type=int, required=True)
    p.add_argument("--ec2-rate", default="")
    p.add_argument("--emr-rate", default="")
    p.add_argument("--max-run-usd", required=True)
    p.add_argument("--budget-usd", required=True)
    p.set_defaults(fn=cmd_estimate)
    p = sub.add_parser("ledger-init")
    p.add_argument("--root", required=True)
    p.add_argument("--within-name", required=True)
    p.add_argument("--within", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--initialized-by", required=True)
    p.add_argument("--initialized-utc", required=True)
    p.set_defaults(fn=cmd_ledger_init)
    p = sub.add_parser("ledger-check")
    p.add_argument("--ledger", required=True)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--estimate", required=True)
    p.add_argument("--max-runs", type=int, required=True)
    p.add_argument("--cumulative-cap", required=True)
    p.add_argument("--approval-sha256", default=None)
    p.set_defaults(fn=cmd_ledger_check)
    p = sub.add_parser("ledger-reserve")
    p.add_argument("--root", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--estimate", required=True)
    p.add_argument("--max-runs", type=int, required=True)
    p.add_argument("--cumulative-cap", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--run-config-sha256", required=True)
    p.add_argument("--approval-sha256", required=True)
    p.add_argument("--reserved-utc", required=True)
    p.set_defaults(fn=cmd_ledger_reserve)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))

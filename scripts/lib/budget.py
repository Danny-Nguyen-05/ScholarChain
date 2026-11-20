#!/usr/bin/env python3
"""G6 EMR cost guard (stdlib; python3 -I). Exact decimal arithmetic, fail closed.

  estimate --instance-type T --primary-count N --core-count N --task-count N --minutes M --idle-seconds S
           --ec2-rate R --emr-rate R --max-run-usd C --budget-usd B
           [--primary-instance-type P --primary-ec2-rate R --primary-emr-rate R]
        estimate = (primary + core + task) x (EC2 rate + EMR uplift) x (M x 60 + S) / 3600, rounded UP to the cent.
        Per instance group (Phase 15 D3, docs/agent-runs/phase-15/prompt.md "S run cap and D3 go-ahead"): T and its rates are the
        core and task type; when the primary type P differs, the primary's own rates apply to the primary count:
        estimate = (primary x (P EC2 + P EMR) + (core + task) x (T EC2 + T EMR)) x (M x 60 + S) / 3600, rounded UP to the cent.
        Without --primary-instance-type (or with P equal to T) the primary uses T's rates, exactly as before.
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
  ledger-record-actual --root R --ledger FILE --repo-root REPO --run-id ID --describe FILE --rate TYPE=EC2,EMR [...]
                       --pending-idle-seconds S --recorded-utc T --max-runs N --cumulative-cap C [--as-of-utc T]
                       [--expected-cluster-id J]
        Phase 15 D3 (human, prompt.md "S run cap and D3 go-ahead": "Record the EMR actuals right after each S run so the pre-R-b
        check uses real numbers, not the cap"). Reads a saved `aws emr describe-cluster --output json` of the run's cluster (the
        operator saves it; no cloud call here) and appends one "actual" line that REPLACES that run's reserved estimate in the
        cumulative total with the measured cluster time x the reviewed rates of its instance groups (rounded UP to the cent):
          measured = (sum over groups of count x (EC2 + EMR rate of its type)) x (to - from) / 3600
          from     = the cluster's Status.Timeline.CreationDateTime, or, when an earlier actual on the same cluster exists, that
                     record's measured end (so a cluster shared by back-to-back runs is never counted twice)
          to       = Status.Timeline.EndDateTime when the cluster has ended; otherwise --as-of-utc (when the describe was saved)
          tail     = 0 when the cluster has ended; otherwise --pending-idle-seconds of idle time still to come (the auto-termination
                     tail), held as a provisional amount. Only the LATEST actual of a cluster keeps its tail.
        Recording again for the same run (for example after the cluster has terminated) supersedes that run's earlier actual,
        provided no other run has recorded on that cluster since. The run must have a reservation; the run count is unchanged
        (an actual never frees a run slot). A cluster group without a reviewed rate, a group count below one for the primary or
        core, a missing timestamp or a time going backwards refuses.

The ledger is one JSON object per line. Line 1 is {"event": "init", "initialized_by", "initialized_utc"}; every later line
is {"event": "reserve", "run_id", "action", "estimate_usd", "run_config_sha256", "approval_record_sha256",
"reserved_utc"} or {"event": "actual", "run_id", "cluster_id", "measured_from_utc", "measured_to_utc", "cluster_ended",
"hourly_usd", "measured_usd", "tail_seconds", "tail_usd", "groups", "recorded_utc"}. The cumulative total is, per reserved run,
its latest actual's measured_usd when one exists (else its estimate_usd), plus the tail_usd of the latest actual of each cluster.
It lives outside the repository and outside sbt's target/ (EMR_LEDGER_PATH, by default under
~/.scholarchain/emr-ledger/): a clean checkout or `sbt clean` cannot erase it. It is local state, not evidence.
"""
import argparse
import datetime
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
    primary_type = args.primary_instance_type or args.instance_type
    split = primary_type != args.instance_type
    if split:
        # Phase 15 D3: the primary node has its own type and therefore its own reviewed rates.
        p_ec2 = parse_decimal(args.primary_ec2_rate, "the EC2 on-demand hourly rate for the primary type %s (EMR_RATE_EC2_*)" % primary_type, problems)
        p_emr = parse_decimal(args.primary_emr_rate, "the EMR uplift hourly rate for the primary type %s (EMR_RATE_EMR_*)" % primary_type, problems)
    else:
        p_ec2, p_emr = ec2, emr
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
        hourly = (p_ec2 + p_emr) * args.primary_count + (ec2 + emr) * (args.core_count + args.task_count)
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
    document = {
        "instance_type": args.instance_type,
        "instances": nodes,
        "ec2_rate_usd_per_hour": format(ec2, "f"),
        "emr_rate_usd_per_hour": format(emr, "f"),
        "hourly_usd": format(hourly, "f"),
        "max_runtime_minutes": args.minutes,
        "idle_timeout_seconds": args.idle_seconds,
        "billed_seconds": billed_seconds,
        "estimate_usd": money(estimate),
        "formula": "instances x (EC2 on-demand + EMR uplift) x (max_runtime + idle_timeout) hours, rounded up to the cent",
    }
    if split:
        # Only a distinct primary type changes the document, so the single-type output is byte-for-byte as before.
        document.update(
            {
                "primary_instance_type": primary_type,
                "primary_ec2_rate_usd_per_hour": format(p_ec2, "f"),
                "primary_emr_rate_usd_per_hour": format(p_emr, "f"),
                "formula": "(primary x (primary EC2 + EMR) + (core + task) x (EC2 + EMR of instance_type)) x (max_runtime + idle_timeout) hours, rounded up to the cent",
            }
        )
    print(json.dumps(document, sort_keys=True))
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


def _nonneg_money(value, label):
    amount = D(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError(label)
    return amount


def parse_ledger(path):
    """Returns {"reserves": [entry...], "actuals": [entry...], "approvals": set} in file order.

    Raises LedgerAbsent when the file does not exist and ValueError when it is unreadable, not initialised (the first
    line must be the "init" record) or malformed. A ledger is never read as empty. An "actual" line must name a run reserved on
    an EARLIER line (Phase 15 D3)."""
    if not os.path.lexists(path):
        raise LedgerAbsent("the run ledger %s does not exist; the human creates it once with run-bounded-pipeline.sh --init-ledger" % path)
    if os.path.islink(path) or not os.path.isfile(path):
        raise ValueError("the ledger is not a regular file")
    reserves = []
    actuals = []
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
                if event == "reserve":
                    value = D(str(entry["estimate_usd"]))
                    if not value.is_finite() or value < 0:
                        raise ValueError("bad estimate")
                    approval = entry.get("approval_record_sha256")
                    if approval is not None:
                        if not isinstance(approval, str) or len(approval) != 64 or any(c not in HEX64 for c in approval):
                            raise ValueError("bad approval record hash")
                        approvals.add(approval)
                    reserves.append({"run_id": entry.get("run_id"), "estimate": value})
                elif event == "actual":
                    run_id = entry["run_id"]
                    cluster = entry["cluster_id"]
                    if not isinstance(run_id, str) or not isinstance(cluster, str) or not cluster:
                        raise ValueError("bad actual identity")
                    if not any(r["run_id"] == run_id for r in reserves):
                        raise ValueError("an actual for a run with no earlier reservation")
                    actuals.append(
                        {
                            "run_id": run_id,
                            "cluster_id": cluster,
                            "measured": _nonneg_money(entry["measured_usd"], "bad measured amount"),
                            "tail": _nonneg_money(entry["tail_usd"], "bad tail amount"),
                            "from": parse_time(entry["measured_from_utc"], "measured_from_utc"),
                            "to": parse_time(entry["measured_to_utc"], "measured_to_utc"),
                        }
                    )
                else:
                    raise ValueError("unknown event")
            except (ValueError, KeyError, TypeError, decimal.InvalidOperation, AttributeError):
                raise ValueError("ledger line %d is malformed" % number)
    if not seen_init:
        raise ValueError("the ledger has no init record (an empty file is not an initialised ledger)")
    return {"reserves": reserves, "actuals": actuals, "approvals": approvals}


def ledger_totals(parsed):
    """(live runs, cumulative Decimal, number of runs whose estimate an actual replaced).

    Per reserved run: the latest actual's measured amount when the run has one, else its reserved estimate; plus the provisional
    idle tail of the latest actual of each cluster (an earlier actual's tail is covered by the later record's window)."""
    amounts = [r["estimate"] for r in parsed["reserves"]]
    replaced = set()
    tails = {}
    for actual in parsed["actuals"]:
        index = max(i for i, r in enumerate(parsed["reserves"]) if r["run_id"] == actual["run_id"])
        amounts[index] = actual["measured"]
        replaced.add(index)
        tails[actual["cluster_id"]] = actual["tail"]
    return len(parsed["reserves"]), sum(amounts, D(0)) + sum(tails.values(), D(0)), len(replaced)


def read_ledger(path):
    """Returns (live_runs, cumulative Decimal, approval sha256 set); see parse_ledger and ledger_totals."""
    parsed = parse_ledger(path)
    runs, total, _ = ledger_totals(parsed)
    return runs, total, parsed["approvals"]


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


UTC = datetime.timezone.utc


def parse_time(value, label):
    """An aware datetime from an ISO 8601 string with a zone (a trailing Z is accepted) or epoch seconds (the AWS CLI prints
    either, depending on cli_timestamp_format). A time without a zone is refused (never guessed)."""
    if isinstance(value, bool):
        raise ValueError("%s is not a time" % label)
    if isinstance(value, (int, float)):
        try:
            moment = datetime.datetime.fromtimestamp(value, tz=UTC)
        except (OverflowError, OSError, ValueError):
            raise ValueError("%s is not a usable epoch time" % label)
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z") or text.endswith("z"):
            text = text[:-1] + "+00:00"
        try:
            moment = datetime.datetime.fromisoformat(text)
        except ValueError:
            raise ValueError("%s is not an ISO 8601 time" % label)
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("%s has no time zone" % label)
    else:
        raise ValueError("%s is missing" % label)
    return moment.astimezone(UTC)


def utc_text(moment):
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_rates(items):
    """{instance type: Decimal hourly (EC2 + EMR)} from --rate TYPE=EC2,EMR (the reviewed rates of emr-pricing.conf)."""
    rates = {}
    for item in items or []:
        name, _, pair = item.partition("=")
        parts = pair.split(",")
        if not name or len(parts) != 2:
            raise ValueError("--rate must be TYPE=EC2,EMR (got %r)" % item)
        problems = []
        ec2 = parse_decimal(parts[0], "the EC2 rate of %s" % name, problems)
        emr = parse_decimal(parts[1], "the EMR rate of %s" % name, problems)
        if problems:
            raise ValueError("; ".join(problems))
        rates[name] = ec2 + emr
    return rates


def describe_facts(path):
    """(cluster id, state, created, ended or None, groups [(kind, type, count)]) from a saved describe-cluster JSON."""
    try:
        with open(path, encoding="utf-8") as handle:
            described = json.load(handle)
    except (OSError, ValueError):
        raise ValueError("the describe-cluster file is unreadable or not JSON")
    cluster = described.get("Cluster") if isinstance(described, dict) else None
    if not isinstance(cluster, dict):
        raise ValueError("the describe-cluster file has no Cluster object")
    cluster_id = cluster.get("Id")
    if not isinstance(cluster_id, str) or not cluster_id.startswith("j-"):
        raise ValueError("the describe-cluster file has no cluster id")
    status = cluster.get("Status") or {}
    timeline = status.get("Timeline") or {}
    created = parse_time(timeline.get("CreationDateTime"), "Status.Timeline.CreationDateTime")
    ended = timeline.get("EndDateTime")
    ended = parse_time(ended, "Status.Timeline.EndDateTime") if ended is not None else None
    state = status.get("State")
    if ended is None and state in ("TERMINATED", "TERMINATED_WITH_ERRORS"):
        raise ValueError("the cluster is %s but has no Status.Timeline.EndDateTime" % state)
    groups = []
    found = cluster.get("InstanceGroups")
    if not isinstance(found, list) or not found:
        raise ValueError("the describe-cluster file has no Cluster.InstanceGroups")
    for group in found:
        if not isinstance(group, dict):
            raise ValueError("an instance group entry is not an object")
        kind = group.get("InstanceGroupType")
        kind_type = group.get("InstanceType")
        counts = [group.get("RequestedInstanceCount"), group.get("RunningInstanceCount")]
        if kind not in ("MASTER", "CORE", "TASK") or not isinstance(kind_type, str):
            raise ValueError("an instance group has no known type")
        if any(isinstance(c, bool) or not isinstance(c, int) or c < 0 for c in counts):
            raise ValueError("the %s group has no integer instance counts" % kind)
        groups.append((kind, kind_type, max(counts)))
    for kind in ("MASTER", "CORE"):
        if sum(count for k, _, count in groups if k == kind) < 1:
            raise ValueError("the %s group reports no instance: its cost cannot be measured from this file" % kind)
    return cluster_id, state, created, ended, groups


def cmd_ledger_record_actual(args):
    located = ledger_location_problem(args.ledger, args.repo_root)
    if located:
        print("G6-REFUSED: %s" % located)
        return 1
    if not os.path.lexists(args.ledger):
        print("G6-REFUSED: the run ledger %s does not exist; nothing to record against" % args.ledger)
        return 1
    try:
        rates = parse_rates(args.rate)
        recorded = parse_time(args.recorded_utc, "--recorded-utc")
        cluster_id, state, created, ended, groups = describe_facts(args.describe)
        as_of = parse_time(args.as_of_utc, "--as-of-utc") if args.as_of_utc else None
    except ValueError as error:
        print("G6-REFUSED: %s" % error)
        return 1
    if args.pending_idle_seconds < 0:
        print("G6-REFUSED: --pending-idle-seconds must not be negative")
        return 1
    cap_problems = []
    cap = parse_decimal(args.cumulative_cap, "the cumulative cap", cap_problems)
    if cap_problems:
        print("G6-REFUSED: %s" % cap_problems[0])
        return 1
    if args.expected_cluster_id and cluster_id != args.expected_cluster_id:
        print("G6-REFUSED: the describe-cluster file is for %s, but run %s ran on %s (run manifest)" % (cluster_id, args.run_id, args.expected_cluster_id))
        return 1
    hourly = D(0)
    lines = []
    for kind, kind_type, count in groups:
        if count == 0:
            continue
        if kind_type not in rates:
            print("G6-REFUSED: no reviewed hourly rate for %s (%s group): the actual cannot be computed and is never read as zero" % (kind_type, kind))
            return 1
        hourly += rates[kind_type] * count
        lines.append({"group": kind, "instance_type": kind_type, "count": count, "rate_usd_per_hour": format(rates[kind_type], "f")})
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
            try:
                parsed = parse_ledger(args.ledger)
            except (OSError, ValueError) as error:
                print("G6-REFUSED: the run ledger cannot be read (%s): refusing rather than reading it as empty" % error)
                return 1
            reserved = [r for r in parsed["reserves"] if r["run_id"] == args.run_id]
            if not reserved:
                print("G6-REFUSED: run %s has no reservation in the ledger: an actual replaces a reserved estimate, it never adds a run" % args.run_id)
                return 1
            on_cluster = [a for a in parsed["actuals"] if a["cluster_id"] == cluster_id]
            mine = [a for a in parsed["actuals"] if a["run_id"] == args.run_id]
            if mine:
                previous = mine[-1]
                if previous["cluster_id"] != cluster_id:
                    print("G6-REFUSED: run %s already has an actual on cluster %s, not %s" % (args.run_id, previous["cluster_id"], cluster_id))
                    return 1
                if on_cluster[-1] is not previous:
                    print("G6-REFUSED: another run recorded an actual on %s after run %s: superseding it would overlap; a human corrects the ledger" % (cluster_id, args.run_id))
                    return 1
                start = previous["from"]
            elif on_cluster:
                start = on_cluster[-1]["to"]
            else:
                start = created
            if ended is not None:
                end, tail_seconds = ended, 0
            else:
                if as_of is None:
                    print("G6-REFUSED: cluster %s is %s (not ended): --as-of-utc (the UTC time the describe-cluster file was saved) is required" % (cluster_id, state))
                    return 1
                if as_of > recorded + datetime.timedelta(seconds=300):
                    print("G6-REFUSED: --as-of-utc %s lies in the future" % utc_text(as_of))
                    return 1
                end, tail_seconds = as_of, args.pending_idle_seconds
            if end < start:
                print("G6-REFUSED: the measured window would end (%s) before it starts (%s)" % (utc_text(end), utc_text(start)))
                return 1
            seconds = D(str((end - start).total_seconds()))
            measured = (hourly * seconds / D(3600)).quantize(CENT, rounding=decimal.ROUND_UP)
            tail = (hourly * D(tail_seconds) / D(3600)).quantize(CENT, rounding=decimal.ROUND_UP)
            runs_before, total_before, _ = ledger_totals(parsed)
            entry = {
                "event": "actual",
                "run_id": args.run_id,
                "cluster_id": cluster_id,
                "cluster_state": state,
                "cluster_ended": ended is not None,
                "measured_from_utc": utc_text(start),
                "measured_to_utc": utc_text(end),
                "measured_seconds": format(seconds, "f"),
                "hourly_usd": format(hourly, "f"),
                "measured_usd": money(measured),
                "tail_seconds": tail_seconds,
                "tail_usd": money(tail),
                "groups": lines,
                "recorded_utc": utc_text(recorded),
            }
            parsed["actuals"].append({"run_id": args.run_id, "cluster_id": cluster_id, "measured": measured, "tail": tail, "from": start, "to": end})
            runs_after, total_after, replaced = ledger_totals(parsed)
            with safeio.open_append_existing(args.root, args.ledger) as handle:
                handle.write((json.dumps(entry, sort_keys=True) + "\n").encode("utf-8"))
    except (safeio.Refused, OSError) as error:
        print("G6-REFUSED: the run ledger could not be updated safely (%s)" % (error if isinstance(error, safeio.Refused) else type(error).__name__))
        return 1
    print(
        "LEDGER-ACTUAL: run=%s cluster=%s window=%s..%s seconds=%s hourly_usd=%s measured_usd=%s tail_seconds=%d tail_usd=%s reserved_estimate_usd=%s"
        % (args.run_id, cluster_id, utc_text(start), utc_text(end), format(seconds, "f"), format(hourly, "f"), money(measured), tail_seconds, money(tail), money(reserved[-1]["estimate"]))
    )
    print("LEDGER: live_runs=%d of %d cumulative_usd=%s (was %s; %d run(s) now counted at actuals) cap_usd=%s" % (runs_after, args.max_runs, money(total_after), money(total_before), replaced, money(cap)))
    if total_after > cap:
        print("LEDGER-OVER-CAP: the cumulative total %s USD exceeds the cap %s USD: every further run is refused" % (money(total_after), money(cap)))
    return 0


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
    p.add_argument("--primary-instance-type", default="")
    p.add_argument("--primary-ec2-rate", default="")
    p.add_argument("--primary-emr-rate", default="")
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
    p = sub.add_parser("ledger-record-actual")
    p.add_argument("--root", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--describe", required=True)
    p.add_argument("--rate", action="append", required=True)
    p.add_argument("--pending-idle-seconds", type=int, required=True)
    p.add_argument("--recorded-utc", required=True)
    p.add_argument("--as-of-utc", default="")
    p.add_argument("--expected-cluster-id", default="")
    p.add_argument("--max-runs", type=int, required=True)
    p.add_argument("--cumulative-cap", required=True)
    p.set_defaults(fn=cmd_ledger_record_actual)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))

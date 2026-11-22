#!/usr/bin/env python3
"""Phase 16, group 5 (performance and elasticity): compute every figure from raw evidence that already exists (stdlib only; python3 -I; offline).

  python3 -I experiments/scripts/eval16_perf.py [--out-dir experiments/results/phase16/performance]

No network, no AWS, no model call, no spend. Every number below is computed by this script from raw files; a number the harness already printed
(derived/summary.csv, results-summary.md) is only a cross-check and is reported as MATCH or MISMATCH, never used as a result. A quantity with no raw
evidence is written as a GAP with its reason (nothing is estimated).

Environments (a row is never to be read as another environment's number):
  AWS-ECS    the 15B semantic load against the deployed query-api behind the ALB, Session 2 run rb-20261118, 2026-11-18 (non-loopback https)
  LOCAL-LOOPBACK-DOCKER  the P35 rehearsal p35-local-1, 2026-11-16: query-api offline-synthetic in Docker, 0.25 vCPU / 1 GiB, load generator on the host
  LOCAL-LOOPBACK-LLM     the Q12 runs (query-api on 127.0.0.1, local graph export, live Anthropic synthesis calls), 2026-11-20 and 2026-11-21
  AWS-ECS-LLM            the 16B run 16b-1 (Session 1, 2026-11-14, non-loopback https, live Anthropic calls)
  AWS-EMR                the 15A size-100 EMR run, 2026-11-18 (m5.xlarge core, r5.xlarge primary)
  LOCAL-MAC              the P6 local chain runs (hadoop-prep, entity-resolution, spark) on the author's laptop
  AWS-S3VECTORS+VOYAGE   the 14C ingest and query smoke of 2026-11-18 from the laptop to S3 Vectors and Voyage

The AWS rb-20261118 raw is read from the committed frozen copy experiments/results/phase16/performance/raw-rb-20261118 (verified against its SHA256SUMS and the run's raw.sha256),
else from target/. The P35 local-rehearsal raw (83 MB) is NOT frozen: it is git-ignored, hash-only, and required (LOCAL_INPUTS); when it is absent the script
exits 3 (inputs unavailable) and writes nothing. The LLM runs' raw files are read from the committed frozen copies under experiments/results/phase16/q12-raw when present
(byte-identical to target/experiment-runs/<run>/raw), else from target/.
Every input's sha256 is written to the output. Percentiles are nearest-rank (the load generator's own method). Confidence intervals: a seeded percentile
bootstrap only where the samples are independent repeats (the Q12 questions); a single load run per level has no repeat, so no interval is given and the
per-minute spread is reported instead. Exit codes: 0 done, 1 refused (an input is unreadable or fails its sha256), 3 inputs unavailable.
"""
import argparse
import collections
import datetime
import hashlib
import json
import math
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHEMA = "scholarchain.eval16-performance.v1"
BOOTSTRAP_SEED = "eval16-performance-v1"
BOOTSTRAP_RESAMPLES = 2000

EV = "docs/agent-runs/phase-15/evidence"
S2 = EV + "/session-2"
RB_RUN = "target/experiment-runs/15b-ecs-scaling-semantic-rb-20261118"
RB_FROZEN = "experiments/results/phase16/performance/raw-rb-20261118"  # committed frozen copy (raw files + harness summary.csv + SHA256SUMS), byte-identical to RB_RUN/raw
P35_RUN = "target/experiment-runs/15b-ecs-scaling-semantic-p35-local-1"
Q12_RUNS = ("q12-benchmark-q12-probe-1", "q12-benchmark-q12-probe-2", "q12-benchmark-q12-run-1", "q12-benchmark-q12-run-2")
B16_RUN = "target/experiment-runs/16b-live-evaluation-16b-1"
FROZEN_RAW = "experiments/results/phase16/q12-raw"  # committed frozen copies of the LLM runs' raw files (byte-identical to target/experiment-runs/<run>/raw)
P6_WORK = "target/phase15/p6/work"
P6_BYPASS = ("target/phase15/p6/l-bypass/run-S.out", "target/phase15/p6/l-bypass/run-L.out")
LOAD_PROFILE = "load-tests/config/load-profile.v1.json"
DECISION_LOG = S2 + "/00-timeline/decision-log.md"
NOTES_LINES = {"ecs_poll": S2 + "/b10-load/b10-ecs-poll.log", "failure_probe": S2 + "/b35-failure/p11-failure.log", "emr_run": S2 + "/emr/emr-run-1.log",
               "emr_actual": S2 + "/emr/emr-actual-1end.log", "emr_counters": S2 + "/emr/hadoop-prep-counters.txt", "cost_report": S2 + "/c11/cost-report.log",
               "ingest_report": S2 + "/vectors/ingest-report-2.json", "ingest_log_1": S2 + "/vectors/ingest.log", "ingest_log_2": S2 + "/vectors/ingest-2.log",
               "query_report": S2 + "/vectors/query-report.json", "p35_summary_csv": EV + "/p35/loadgen/derived/summary.csv",
               "p35_raw_sha": EV + "/p35/loadgen/raw/raw.sha256"}
LOCAL_INPUTS = (P35_RUN + "/raw/requests.jsonl", P35_RUN + "/raw/events.jsonl")  # the P35 raw (83 MB) is NOT frozen in the repository: hash-only, stays on the laptop


class Refused(Exception):
    pass


class Unavailable(Exception):
    pass


# ---------------------------------------------------------------------------------------------------------------- helpers
def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(sorted_values, p):
    """Nearest-rank percentile: the value at rank ceil(p/100 * n) of the sorted list (the same rule as load-tests/loadgen.py)."""
    if not sorted_values:
        return None
    rank = max(1, math.ceil(p / 100.0 * len(sorted_values)))
    return sorted_values[rank - 1]


def parse_utc(text):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.datetime.strptime(text, fmt).replace(tzinfo=datetime.timezone.utc).timestamp()
        except ValueError:
            continue
    raise Refused("unparseable UTC time: %r" % text)


def fmt_utc(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def r3(value):
    return None if value is None else round(value, 3)


def bootstrap_ci(values, stat, seed, resamples=BOOTSTRAP_RESAMPLES):
    """Seeded percentile bootstrap (2.5%, 97.5%) of stat(values). Uses random() only, which is stable across Python versions."""
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    n = len(values)
    draws = sorted(stat([values[int(rng.random() * n)] for _ in range(n)]) for _ in range(resamples))
    return [r3(draws[int(0.025 * resamples)]), r3(draws[int(0.975 * resamples) - 1])]


def median(values):
    ordered = sorted(values)
    if not ordered:
        return None
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0


def path_of(rel):
    return os.path.join(ROOT, rel)


def read_lines(rel):
    try:
        with open(path_of(rel), encoding="utf-8") as handle:
            return handle.read().split("\n")
    except OSError as error:
        raise Unavailable("%s: %s" % (rel, error.strerror))


def read_json(rel):
    try:
        with open(path_of(rel), encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as error:
        raise Unavailable("%s: %s" % (rel, error.strerror))
    except ValueError as error:
        raise Refused("%s is not valid JSON: %s" % (rel, error))


class Inputs:
    """Records the sha256 of every file read, in sorted order, so the output names its raw evidence."""

    def __init__(self):
        self.shas = {}

    def touch(self, rel, label=None):
        key = label or rel
        if key not in self.shas:
            if not os.path.isfile(path_of(rel)):
                raise Unavailable("%s: absent" % rel)
            self.shas[key] = sha256_file(path_of(rel))
        return self.shas[key]


# ---------------------------------------------------------------------------------------------------------- load-test runs
LOAD_TYPES = ("load", "warmup")  # the load generator's own list of request-sending phase types


def load_rows(rel):
    rows = []
    with open(path_of(rel), encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                r = json.loads(line)
                rows.append((r["phase"], r["status"], r["outcome"], r["latency_ms"], r["started_utc"], r.get("route")))
    return rows


def is_failure(status, outcome):
    return status >= 500 or outcome in ("timeout", "transport_error")


def group_stats(rows, seconds):
    """Per-group figures from (phase, status, outcome, latency_ms, started_utc, route) tuples. A 429 is counted as a request, reported on its own and
    excluded from throughput, error rates and latency (the load generator's rule). Latency is over responses (status > 0)."""
    served = [r for r in rows if r[1] != 429]
    ok = [r for r in rows if r[2] == "ok"]
    responded = sorted(r[3] for r in served if r[1] > 0)
    good = sorted(r[3] for r in ok)
    failures = sum(1 for r in served if is_failure(r[1], r[2]))
    per_second = collections.Counter(r[4][:19] for r in ok)
    return {
        "requests": len(rows), "served": len(served), "successful": len(ok), "rate_limited_429": len(rows) - len(served),
        "outcomes": dict(sorted(collections.Counter(r[2] for r in rows).items())),
        "status_codes": dict(sorted((str(k), v) for k, v in collections.Counter(r[1] for r in rows).items())),
        "seconds": r3(seconds), "throughput_rps": r3(len(served) / seconds) if seconds > 0 else None,
        "success_rps": r3(len(ok) / seconds) if seconds > 0 else None,
        "peak_success_rps_1s": max(per_second.values()) if per_second else 0,
        "failures_5xx_or_transport": failures, "error_rate_5xx_or_transport": round(failures / len(served), 6) if served else None,
        "latency_ms_all_responses": {"n": len(responded), "p50": percentile(responded, 50), "p95": percentile(responded, 95), "p99": percentile(responded, 99),
                                     "max": responded[-1] if responded else None},
        "latency_ms_2xx": {"n": len(good), "p50": percentile(good, 50), "p95": percentile(good, 95), "p99": percentile(good, 99)},
    }


def minute_timeline(rows, windows):
    by = collections.OrderedDict()
    for r in rows:
        by.setdefault((r[4][:16] + ":00Z", r[0]), []).append(r)
    out = []
    for (minute, phase), group in sorted(by.items()):
        lat = sorted(x[3] for x in group if x[1] > 0 and x[1] != 429)
        out.append({"minute_utc": minute, "phase": phase, "level": windows.get(phase, (None, None, None))[2], "requests": len(group),
                    "errors_5xx_or_transport": sum(1 for x in group if is_failure(x[1], x[2])), "p95_ms": percentile(lat, 95)})
    return out


def read_csv_rows(rel):
    lines = [l for l in read_lines(rel) if l.strip()]
    header = lines[0].split(",")
    return [dict(zip(header, line.split(","))) for line in lines[1:]]


def verify_frozen(frozen_rel):
    """Check a frozen directory against its SHA256SUMS: the same file set, every sha256 equal. Raises Refused otherwise."""
    listed = {}
    for line in read_lines(frozen_rel + "/SHA256SUMS"):
        if line.strip():
            digest, name = line.split("  ", 1)
            listed[name.strip()] = digest
    actual = sorted(n for n in os.listdir(path_of(frozen_rel)) if n != "SHA256SUMS")
    if sorted(listed) != actual:
        raise Refused("the files in %s do not match its SHA256SUMS" % frozen_rel)
    for name, digest in listed.items():
        if sha256_file(path_of(frozen_rel + "/" + name)) != digest:
            raise Refused("%s/%s does not match its SHA256SUMS" % (frozen_rel, name))
    return listed


def rb_sources():
    """The AWS run's raw directory, its raw.sha256 and the harness summary.csv: the committed frozen copy (verified against SHA256SUMS) when present, else the git-ignored original."""
    if os.path.isfile(path_of(RB_FROZEN + "/SHA256SUMS")):
        verify_frozen(RB_FROZEN)
        return RB_FROZEN, RB_FROZEN + "/raw.sha256", RB_FROZEN + "/summary.csv"
    return RB_RUN + "/raw", RB_RUN + "/raw/raw.sha256", RB_RUN + "/derived/summary.csv"


def analyse_load_run(raw, expected_sha_rel, inputs, summary_csv_rel, label):
    """Recompute every per-phase figure from raw/requests.jsonl and compare to the harness summary (cross-check only). Inputs are recorded under logical labels."""
    sha_lines = [l for l in read_lines(expected_sha_rel) if l.strip()]
    expected = dict((l.split("  ", 1)[1].strip(), l.split("  ", 1)[0]) for l in sha_lines)
    verified = {}
    for name in ("events.jsonl", "requests.jsonl", "run-record.json"):
        actual = inputs.touch(raw + "/" + name, "%s raw/%s" % (label, name))
        if expected.get(name) != actual:
            raise Refused("%s/%s does not match its recorded sha256" % (raw, name))
        verified[name] = actual
    events = [json.loads(l) for l in read_lines(raw + "/events.jsonl") if l.strip()]
    record = read_json(raw + "/run-record.json")
    windows = {}
    for e in events:
        if e["event"] == "phase-end" and e.get("type") in LOAD_TYPES:
            windows[e["phase"]] = (e["started_utc"], e["ended_utc"], e["level"])
    rows = load_rows(raw + "/requests.jsonl")
    by_phase = collections.OrderedDict()
    for r in rows:
        by_phase.setdefault(r[0], []).append(r)
    harness = dict((row["phase"], row) for row in read_csv_rows(summary_csv_rel))
    inputs.touch(summary_csv_rel, "%s harness summary.csv" % label)
    phases = []
    for name, (start, end, level) in windows.items():
        seconds = parse_utc(end) - parse_utc(start)
        entry = {"phase": name, "level": level, "started_utc": start, "ended_utc": end}
        entry.update(group_stats(by_phase.get(name, []), seconds))
        h = harness.get(name)
        mism = []
        if h is None:
            mism.append("phase absent from the harness summary")
        else:
            pairs = (("requests", entry["requests"], float(h["requests"])), ("throughput_rps", entry["throughput_rps"], float(h["throughput_rps"])),
                     ("error_rate", entry["error_rate_5xx_or_transport"], float(h["error_rate_5xx_or_transport"])),
                     ("p50_ms", entry["latency_ms_all_responses"]["p50"], float(h["p50_ms"])), ("p95_ms", entry["latency_ms_all_responses"]["p95"], float(h["p95_ms"])),
                     ("p99_ms", entry["latency_ms_all_responses"]["p99"], float(h["p99_ms"])), ("peak_success_rps_1s", entry["peak_success_rps_1s"], float(h["peak_success_rps_1s"])))
            for label, mine, theirs in pairs:
                if mine is None or abs(mine - theirs) > 1e-6:
                    mism.append("%s computed %s harness %s" % (label, mine, theirs))
        entry["cross_check_vs_harness_summary"] = "MATCH" if not mism else "MISMATCH: " + "; ".join(mism)
        phases.append(entry)
    tl = minute_timeline(rows, windows)
    return {"run_id": record["run_id"], "commit": record["commit"], "tree_dirty": record["tree_dirty"], "outcome": record["outcome"],
            "outcome_reason": record.get("outcome_reason"), "started_utc": record["started_utc"], "ended_utc": record["ended_utc"],
            "target_loopback": record["target"]["loopback"], "target_host": record["target"]["host"], "routes": record["routes"],
            "llm_enabled": record["llm"]["enabled"], "raw_sha256_verified": dict(sorted(verified.items())), "phases": phases,
            "per_minute": tl, "total_requests": len(rows), "total_outcomes": dict(sorted(collections.Counter(r[2] for r in rows).items()))}, rows


def error_burst(rows, phase):
    errs = [r for r in rows if r[0] == phase and is_failure(r[1], r[2])]
    if not errs:
        return None
    per_second = collections.Counter(r[4][:19] for r in errs)
    return {"phase": phase, "errors": len(errs), "status_codes": dict(sorted((str(k), v) for k, v in collections.Counter(r[1] for r in errs).items())),
            "outcomes": dict(sorted(collections.Counter(r[2] for r in errs).items())), "first_error_started_utc": min(r[4] for r in errs),
            "last_error_started_utc": max(r[4] for r in errs), "errors_per_second": dict(sorted(per_second.items())),
            "error_latency_ms": {"min": min(r[3] for r in errs), "median": median([r[3] for r in errs]), "max": max(r[3] for r in errs)}}


# ------------------------------------------------------------------------------------------------------ elasticity and recovery
def parse_ecs_poll(lines):
    """Each line is a UTC time, optionally followed by three tab-separated integers (desired, running, pending). A bare time is a poll that returned
    nothing (the decision log records a credential failure for 20:42-20:50Z)."""
    polls = []
    for number, line in enumerate(lines, 1):
        m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)(?:\s+(\d+)\s+(\d+)\s+(\d+))?\s*$", line)
        if m:
            polls.append({"line": number, "utc": m.group(1), "desired": int(m.group(2)) if m.group(2) else None,
                          "running": int(m.group(3)) if m.group(3) else None, "pending": int(m.group(4)) if m.group(4) else None})
    return polls


def elasticity(poll_rel, windows, run_end_epoch, inputs):
    inputs.touch(poll_rel)
    return elasticity_from_polls(parse_ecs_poll(read_lines(poll_rel)), poll_rel, windows, run_end_epoch)


def elasticity_from_polls(polls, poll_rel, windows, run_end_epoch):
    data = [p for p in polls if p["desired"] is not None]
    blank = [p for p in polls if p["desired"] is None]
    first_two = next((p for p in data if p["desired"] >= 2), None)
    before = [p for p in data if first_two and p["line"] < first_two["line"]]
    running_two = next((p for p in data if p["running"] is not None and p["running"] >= 2), None)
    last_two = None
    after_in = None
    if first_two:
        twos = [p for p in data if p["desired"] >= 2]
        last_two = twos[-1]
        after_in = next((p for p in data if p["line"] > last_two["line"]), None)
    out = {"poll_lines_total": len(polls), "poll_lines_with_data": len(data), "poll_lines_blank": len(blank),
           "poll_interval_seconds_median": r3(median([parse_utc(b["utc"]) - parse_utc(a["utc"]) for a, b in zip(polls, polls[1:])])),
           "column_meaning": "desired running pending (ECS service counts; the decision log reads the 20:52:55Z line as desired 2 running 1 pending 1)",
           "source": "%s (committed evidence copy; polls were taken by a human-run loop, not a CloudWatch export)" % poll_rel}
    if first_two:
        lk = before[-1] if before else None
        out["scale_out"] = {
            "last_poll_with_data_before": lk and {"line": lk["line"], "utc": lk["utc"], "state": [lk["desired"], lk["running"], lk["pending"]]},
            "first_poll_desired_2": {"line": first_two["line"], "utc": first_two["utc"], "state": [first_two["desired"], first_two["running"], first_two["pending"]]},
            "first_poll_running_2": running_two and {"line": running_two["line"], "utc": running_two["utc"]},
            "blank_polls_before_first_data": sum(1 for b in blank if b["line"] < (data[0]["line"] if data else 0)),
            "desired_2_no_later_than_seconds_after_phase_start": dict(
                (name, r3(parse_utc(first_two["utc"]) - parse_utc(w[0]))) for name, w in sorted(windows.items()) if name in ("level-25", "level-50", "hold-50")),
            "task_start_upper_bound_seconds": r3(parse_utc(running_two["utc"]) - parse_utc(first_two["utc"])) if running_two else None,
            "interpretation_limit": "The polls before the last_poll_with_data_before line are blank, so the instant the desired count changed is unknown; the figures above are upper "
                                    "bounds measured from the poll grid (about 61 s). No CloudWatch alarm history or ECS service-event export was saved: the exact scale-out "
                                    "trigger delay is a GAP."}
        out["scale_in"] = {
            "last_poll_desired_2": {"line": last_two["line"], "utc": last_two["utc"]},
            "first_later_poll_with_data": after_in and {"line": after_in["line"], "utc": after_in["utc"], "state": [after_in["desired"], after_in["running"], after_in["pending"]]},
            "blank_polls_between": sum(1 for b in blank if last_two["line"] < b["line"] < (after_in["line"] if after_in else 10 ** 9)),
            "scale_in_happened_between_seconds_after_load_stop": [r3(parse_utc(last_two["utc"]) - run_end_epoch), r3(parse_utc(after_in["utc"]) - run_end_epoch)] if after_in else None,
            "interpretation_limit": "The desired count fell somewhere inside this bracket (the polls in between are blank); the exact scale-in instant is a GAP. The decision log "
                                    "records a dashboard reading of about 21:09-21:10Z (human-read from a clip, not a raw export)."}
    return out


def dashboard_reading():
    """Figures the human read from the elasticity dashboard clip (decision-log line, not a raw export), parsed by regex; None when the text changed."""
    lines = read_lines(DECISION_LOG)
    for number, text in enumerate(lines, 1):
        if "REC19" in text and "HealthyHostCount" in text:
            find = lambda pattern: (re.search(pattern, text) or [None, None])[1]
            return {"source": "%s:%d (human reading of the dashboard clip; not a raw export)" % (DECISION_LOG, number),
                    "healthy_hosts_1_to_2": find(r"HealthyHostCount 1->2 about ([0-9:\-Z]+)"), "healthy_hosts_2_to_1": find(r"2->1 about ([0-9:\-Z]+)"),
                    "cpu_max_percent": find(r"CPU max ([0-9.]+)%"), "requests_peak_per_minute": find(r"requests peak ~([0-9.]+K)/min"),
                    "p99_spike": find(r"p99 spike to ([0-9]+ s)")}
    return None


def failure_recovery(rel, inputs):
    inputs.touch(rel)
    return analyse_probe_lines(read_lines(rel), rel)


def analyse_probe_lines(lines, rel):
    """The failure-injection probe log: 'HH:MM:SS healthz=NNN readyz=NNN' lines roughly every 5 s, and 'Wed Nov 18 HH:MM:SS UTC 2026' lines that precede
    a 'DEACTIVATING STOPPED' line (a stop-task call). Recovery is measured on the probe grid."""
    probes, stops = [], []
    for number, line in enumerate(lines, 1):
        m = re.match(r"^(\d\d):(\d\d):(\d\d)\s+healthz=(\d+)\s+readyz=(\d+)\s*$", line)
        if m:
            probes.append((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)), int(m.group(4)), int(m.group(5)), number))
            continue
        m = re.match(r"^\w{3} \w{3} +\d+ (\d\d):(\d\d):(\d\d) UTC \d{4}$", line)
        if m and number < len(lines) and lines[number].startswith("DEACTIVATING"):
            stops.append((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)), number, lines[number].strip()))
    hms = lambda s: "%02d:%02d:%02dZ" % (s // 3600, s // 60 % 60, s % 60)
    rounds = []
    for stop_s, number, label in stops:
        later = [p for p in probes if stop_s <= p[0] <= stop_s + 180]
        bad = [p for p in later if p[1] != 200 or p[2] != 200]
        entry = {"stop_task_logged_line": number, "stop_task_utc_time": hms(stop_s), "stop_record": label}
        if not bad:
            entry["observed"] = "no non-200 probe within 180 s of the stop"
        else:
            first_bad = bad[0]
            good_after = next((p for p in later if p[0] > first_bad[0] and p[1] == 200 and p[2] == 200), None)
            entry.update({"first_non_200_probe": {"utc_time": hms(first_bad[0]), "line": first_bad[3], "healthz": first_bad[1], "readyz": first_bad[2]},
                          "last_non_200_probe_utc_time": hms(bad[-1][0]), "non_200_probes": len(bad),
                          "healthz_codes_during_outage": sorted(set(p[1] for p in bad)), "readyz_codes_during_outage": sorted(set(p[2] for p in bad)),
                          "first_probe_with_both_200_after": good_after and {"utc_time": hms(good_after[0]), "line": good_after[3]},
                          "stop_to_recovery_seconds": good_after[0] - stop_s if good_after else None,
                          "observed_outage_seconds_first_bad_to_first_good": good_after[0] - first_bad[0] if good_after else None,
                          "stop_to_first_bad_seconds": first_bad[0] - stop_s})
        rounds.append(entry)
    gaps = [b[0] - a[0] for a, b in zip(probes, probes[1:])]
    return {"source": rel, "probe_count": len(probes), "probe_interval_seconds_median": median(gaps), "probe_interval_seconds_max": max(gaps) if gaps else None,
            "stop_task_events": rounds,
            "interpretation_limit": "Recovery is measured with a probe every ~5 s on the public ALB host (healthz and readyz), so it carries about +/-5 s resolution. Two stop-task calls "
                                    "took effect; the call logged between them was a repeat on an already-stopped task (decision log) and shows no outage. Two events are not a "
                                    "distribution: no percentile is given."}


# ----------------------------------------------------------------------------------------------------------------- EMR and cost
def emr_steps(rel, inputs):
    inputs.touch(rel)
    return parse_emr_run_lines(read_lines(rel), rel)


def parse_emr_run_lines(lines, rel):
    starts, results, failure = [], {}, None
    for number, line in enumerate(lines, 1):
        m = re.search(r"\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\] \[[^\]]+\] INFO pre-spend receipt re-verified before submitting step (\S+)", line)
        if m:
            starts.append((m.group(2), m.group(1), number))
        m = re.search(r"STEP-RESULT: (\S+) (s-\w+) (\w+)", line)
        if m:
            results[m.group(1)] = (m.group(3), number)
        m = re.search(r"\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\] \[[^\]]+\] ERROR failed at step (\S+):", line)
        if m:
            failure = (m.group(2), m.group(1), number)
    steps = []
    for i, (name, ts, number) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else (failure[1] if failure else None)
        steps.append({"step": name, "submitted_utc": ts, "submitted_line": number, "next_event_utc": end,
                      "state": results.get(name, (None, None))[0], "state_line": results.get(name, (None, None))[1],
                      "seconds_submit_to_next_event": r3(parse_utc(end) - parse_utc(ts)) if end else None})
    return {"source": rel, "environment": "AWS-EMR", "steps": steps,
            "interpretation_limit": "Only submission instants are logged (the step runtime is not read from the EMR console), so a step time is the gap to the next submission or to the "
                                    "failure line: an upper bound that includes the poll interval and one pre-spend receipt check. The Spark job failed with 'Unknown Error.' "
                                    "(s1-spark-failure.json), so EMR has no Spark runtime to report."}


def emr_cost(rel, counters_rel, inputs):
    inputs.touch(rel)
    inputs.touch(counters_rel)
    actuals = []
    for number, line in enumerate(read_lines(rel), 1):
        m = re.search(r"LEDGER-ACTUAL: run=(\S+) cluster=(\S+) window=(\S+)\.\.(\S+) seconds=([0-9.]+) hourly_usd=([0-9.]+) measured_usd=([0-9.]+) tail_seconds=(\d+) "
                      r"tail_usd=([0-9.]+) reserved_estimate_usd=([0-9.]+)", line)
        if m:
            seconds, hourly = float(m.group(5)), float(m.group(6))
            actuals.append({"line": number, "run": m.group(1), "window_start_utc": m.group(3), "window_end_utc": m.group(4), "seconds": seconds, "hourly_usd": hourly,
                            "measured_usd_recorded": float(m.group(7)), "measured_usd_recomputed": round(seconds / 3600.0 * hourly, 2), "tail_seconds": int(m.group(8)),
                            "reserved_estimate_usd": float(m.group(10))})
    counters = {}
    for line in read_lines(counters_rel):
        if line.startswith("counters="):
            counters = dict((k, int(v)) for k, v in (pair.split(":") for pair in line[len("counters="):].split(",")))
    return {"source": rel, "environment": "AWS-EMR", "ledger_actual_lines": actuals,
            "note": "The first record (window end 16:56:18Z) is superseded by the second (cluster end 17:06:31Z); the billed window includes idle time after the failed Spark step.",
            "hadoop_prep_counters_on_emr": dict(sorted(counters.items()))}


def cost_report(rel, inputs):
    inputs.touch(rel)
    lines = read_lines(rel)
    out = {"source": rel, "environment": "AWS account, whole project (Cost Explorer, credits excluded)"}
    for number, line in enumerate(lines, 1):
        m = re.match(r"^AWS\s+USD\s+([0-9.]+)\s+usage: Cost Explorer (\S+)\.\.(\S+), daily by service, credits excluded: total ([0-9.]+); Session 2 day Nov 18 = ([0-9.]+) \((.*?)\);", line)
        if m:
            pairs = re.findall(r"([A-Za-z0-9\-]+) ([0-9.]+)", m.group(6))
            parts = dict((k, float(v)) for k, v in pairs)
            out.update({"line": number, "period": [m.group(2), m.group(3)], "project_total_usd": float(m.group(4)), "session_2_day_usd": float(m.group(5)),
                        "session_2_day_by_service_usd": dict(sorted(parts.items())), "service_parts_sum_usd": round(sum(parts.values()), 2)})
        if line.startswith("Anthropic"):
            out["anthropic_line"] = number
            out["anthropic_usd_recorded"] = float(line.split()[2])
        if line.startswith("Combined"):
            out["combined_usd_recorded"] = float(line.split()[2])
    out["gap"] = ("The bill is a whole-day, whole-account figure. The ECS/ALB share of the 2026-11-18 load, the cost of one request and the cost per 1,000 requests are GAPS: no per-service, "
                  "per-hour or per-resource cost export was saved before the stack was destroyed, so the load's own cost cannot be separated from Neptune, EMR and the rest of the day.")
    return out


def vectors(inputs):
    for key in ("ingest_report", "ingest_log_1", "ingest_log_2", "query_report"):
        inputs.touch(NOTES_LINES[key])
    ing = read_json(NOTES_LINES["ingest_report"])
    qr = read_json(NOTES_LINES["query_report"])
    elapsed = int(ing["elapsedNanos"]) / 1e9
    samples = [round(int(s["queryLatencyNanos"]) / 1e6, 3) for s in qr["samples"]]
    ordered = sorted(samples)
    attempts = []
    for key in ("ingest_log_1", "ingest_log_2"):
        text = "\n".join(read_lines(NOTES_LINES[key]))
        m = re.search(r"Total time: (\d+) s \((\d+:\d+)\), completed (.+)$", text, re.M)
        attempts.append({"source": NOTES_LINES[key], "total_seconds": int(m.group(1)) if m else None, "completed": m.group(3).strip() if m else None,
                         "failed": "[error] Exception" in text, "error": (re.search(r"\[error\] Exception in thread \"main\" (\S+): (\S+)", text) or [None, None, None])[2]})
    return {"environment": "AWS-S3VECTORS+VOYAGE (client on the author's laptop; ingest and query calls cross the internet)",
            "ingest": {"source": NOTES_LINES["ingest_report"], "vectors_written": ing["written"], "selected": ing["selectedVectors"], "rejected": ing["rejected"], "conflicts": ing["conflicts"],
                       "elapsed_seconds": r3(elapsed), "vectors_per_second_recomputed": r3(ing["written"] / elapsed), "vectors_per_second_recorded": r3(ing["vectorsPerSecond"]),
                       "ingest_concurrency": ing["ingestConcurrency"], "embedding_batch_size": ing["embeddingBatch"]["batchSize"],
                       "embedding_calls": ing["embeddingCalls"], "underlying_embedding_batch_calls": int(ing["embeddingBatch"]["underlyingCalls"]),
                       "per_index": dict(sorted(ing["perIndex"].items())), "assumed_upper_bound_usd_not_a_bill": ing["assumedUpperBoundUsd"],
                       "attempts": attempts},
            "query_smoke": {"source": NOTES_LINES["query_report"], "latency_scope": qr["latencyScope"], "samples": len(samples), "latency_ms_per_sample": samples,
                            "p50_ms": percentile(ordered, 50), "p95_ms": percentile(ordered, 95), "min_ms": ordered[0], "max_ms": ordered[-1],
                            "note": "n = 5 (one query per index): a smoke, not a latency distribution; a p99 would equal the maximum and is not reported."}}


# ---------------------------------------------------------------------------------------------------------- local chain (P6)
def p6_chain(inputs):
    base = path_of(P6_WORK)
    if not os.path.isdir(base):
        raise Unavailable(P6_WORK + ": absent")
    runs = []
    for name in sorted(os.listdir(base)):
        rel = "%s/%s/evidence/summary.json" % (P6_WORK, name)
        if not os.path.isfile(path_of(rel)):
            continue
        inputs.touch(rel)
        d = read_json(rel)
        steps = [{"step": s.get("step"), "wall_seconds": s.get("wallSeconds"), "exit_code": s.get("exitCode")} for s in d.get("steps", [])]
        counters = (d.get("evidence") or {}).get("hadoopCounters") or {}
        runs.append({"run_id": d.get("runId"), "size": d.get("size"), "all_steps_passed": d.get("allStepsPassed"), "chain_start_utc": d.get("chainStartUtc"),
                     "chain_end_utc": d.get("chainEndUtc"), "git_head": (d.get("git") or {}).get("head"), "work_tree_clean": (d.get("git") or {}).get("workTreeClean"),
                     "input_tree": d.get("inputTree"), "er_xmx": d.get("erXmxOverride") or d.get("planErXmx"), "steps": steps, "hadoop_input_records": counters.get("INPUT"),
                     "hadoop_counters": dict(sorted(counters.items())), "source": rel})
    bypass = []
    for rel in P6_BYPASS:
        if os.path.isfile(path_of(rel)):
            inputs.touch(rel)
            text = "\n".join(read_lines(rel)).lstrip()
            obj, _ = json.JSONDecoder().raw_decode(text)
            bypass.append({"source": rel, "label": obj.get("label"), "exit_code": obj.get("exitCode"), "wall_seconds": obj.get("wallSeconds"),
                           "peak_rss_bytes": (obj.get("peak") or {}).get("rssBytes"), "peak_sum_disk_bytes": (obj.get("peak") or {}).get("sumDiskBytes"),
                           "scope": "Spark job only with entity resolution bypassed (er_identity_bypass.py)"})
    return {"environment": "LOCAL-MAC", "runs": runs, "spark_only_bypass_runs": bypass,
            "note": "Local single-machine runs. Several early runs failed or were diagnostic (all_steps_passed false); they are listed, not hidden. Compare an EMR step with a local "
                    "step only for the same input (size S = 15a size-100 slice) and at the same commit (bd0b818)."}


def emr_vs_local(emr, chain):
    """EMR step gap vs the local chain at the same commit and input; hadoop-prep input records per second on both."""
    ref = next((r for r in chain["runs"] if r["all_steps_passed"] and r["size"] == "S" and (r["git_head"] or "").startswith("bd0b818")), None)
    if not ref:
        return {"gap": "no local passing S run at commit bd0b818 found"}
    emr_by = dict((s["step"], s) for s in emr["steps"])
    rows = []
    for step in ("stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job"):
        local = next((s for s in ref["steps"] if s["step"] == step), None)
        e = emr_by.get(step)
        rows.append({"step": step, "emr_seconds_upper_bound": e and e["seconds_submit_to_next_event"], "emr_state": e and e["state"],
                     "local_wall_seconds": local and local["wall_seconds"],
                     "emr_over_local": r3(e["seconds_submit_to_next_event"] / local["wall_seconds"])
                     if e and local and e["state"] == "COMPLETED" and e["seconds_submit_to_next_event"] and local["wall_seconds"] else None})
    prep = next((r for r in rows if r["step"] == "hadoop-prep"), None)
    rec = ref["hadoop_input_records"]
    return {"local_reference_run": ref["run_id"], "local_commit": ref["git_head"], "rows": rows,
            "hadoop_prep_input_records": rec, "hadoop_prep_records_per_second_local": r3(rec / prep["local_wall_seconds"]) if rec and prep and prep["local_wall_seconds"] else None,
            "hadoop_prep_records_per_second_emr_lower_bound": r3(rec / prep["emr_seconds_upper_bound"]) if rec and prep and prep["emr_seconds_upper_bound"] else None,
            "interpretation_limit": "Descriptive only: one EMR run (2 nodes, the second node r5.xlarge primary) against one laptop run; EMR time includes YARN start-up and S3/EFS staging, "
                                    "the laptop uses local files. No scaling claim (speed-up with node count) can be made: only one cluster size was ever completed."}


# ------------------------------------------------------------------------------------------------------------ LLM answer runs
def token_usage(row):
    exp = row.get("explain")
    body = exp.get("body") if isinstance(exp, dict) else None
    usage = (body or {}).get("modelVersions") or []
    ins = [m.get("inputTokens") for m in usage if isinstance(m.get("inputTokens"), int)]
    outs = [m.get("outputTokens") for m in usage if isinstance(m.get("outputTokens"), int)]
    return (sum(ins), sum(outs)) if ins or outs else None


def llm_base(run_dir):
    """The committed frozen copy of a run's raw files when present, else the git-ignored original (the two are byte-identical; the output names neither path)."""
    for base in ("%s/%s" % (FROZEN_RAW, run_dir), "target/experiment-runs/%s/raw" % run_dir):
        if os.path.isfile(path_of(base + "/answers.jsonl")) and os.path.isfile(path_of(base + "/run-record.json")):
            return base
    raise Unavailable("%s: neither the frozen copy under %s nor target/experiment-runs/%s/raw exists" % (run_dir, FROZEN_RAW, run_dir))


def llm_run(run_dir, environment, rates, inputs):
    base = llm_base(run_dir)
    for name in ("answers.jsonl", "run-record.json"):
        inputs.shas["llm-run %s/%s" % (run_dir, name)] = sha256_file(path_of(base + "/" + name))
    record = read_json(base + "/run-record.json")
    rows = [json.loads(l) for l in read_lines(base + "/answers.jsonl") if l.strip()]
    lat = sorted(r["latency_ms"] for r in rows)
    good = sorted(r["latency_ms"] for r in rows if r["outcome"] == "ok")
    failures = sum(1 for r in rows if is_failure(int(r["status"]), r["outcome"]) or r["outcome"] == "server_error")
    usage = [token_usage(r) for r in rows]
    usage = [u for u in usage if u]
    tokens_in, tokens_out = sum(u[0] for u in usage), sum(u[1] for u in usage)
    server_ms = sorted(int(r["explain"]["body"]["counters"]["latencyMillis"]) for r in rows if isinstance(r.get("explain"), dict) and isinstance(r["explain"].get("body"), dict)
                       and str((r["explain"]["body"].get("counters") or {}).get("latencyMillis", "")).isdigit())
    return {"run_id": record["run_id"], "environment": environment, "commit": record["commit"], "started_utc": record["started_utc"], "ended_utc": record["ended_utc"],
            "target_loopback": record["target"]["loopback"], "outcome": record["outcome"], "questions": len(rows),
            "outcomes": dict(sorted(collections.Counter(r["outcome"] for r in rows).items())),
            "status_codes": dict(sorted((str(k), v) for k, v in collections.Counter(int(r["status"]) for r in rows).items())),
            "server_failures_5xx_or_transport": failures, "server_failure_rate": round(failures / len(rows), 6) if rows else None,
            "latency_ms_all": {"n": len(lat), "p50": percentile(lat, 50), "p95": percentile(lat, 95), "p99": percentile(lat, 99), "min": lat[0], "max": lat[-1],
                               "p50_bootstrap_95ci": bootstrap_ci(lat, lambda v: percentile(sorted(v), 50), BOOTSTRAP_SEED + ":" + record["run_id"])},
            "latency_ms_ok_only": {"n": len(good), "p50": percentile(good, 50), "p95": percentile(good, 95), "p99": percentile(good, 99)},
            "server_reported_synthesis_latency_ms": {"n": len(server_ms), "p50": percentile(server_ms, 50), "p95": percentile(server_ms, 95)} if server_ms else None,
            "synthesis_token_usage": {"answers_with_recorded_usage": len(usage), "input_tokens": tokens_in, "output_tokens": tokens_out,
                                      "estimated_usd_at_pinned_rates": round((tokens_in * rates[0] + tokens_out * rates[1]) / 1e6, 6)} if usage else None,
            "run_record_estimated_usd": record["cost_report"]["anthropic"]["usd"], "answers_charged": record["llm"].get("answers_charged") or record["llm"].get("answers_sent"),
            "source": "raw/answers.jsonl and raw/run-record.json of target/experiment-runs/%s (frozen copy: %s/%s)" % (run_dir, FROZEN_RAW, run_dir)}, rows


def paired_latency(rows_a, rows_b, run_a, run_b):
    a = dict((r["qid"], r["latency_ms"]) for r in rows_a if "qid" in r)
    b = dict((r["qid"], r["latency_ms"]) for r in rows_b if "qid" in r)
    qids = sorted(set(a) & set(b))
    diffs = [b[q] - a[q] for q in qids]
    return {"pair": [run_a, run_b], "questions": len(qids), "median_diff_ms_second_minus_first": r3(median(diffs)),
            "median_diff_bootstrap_95ci": bootstrap_ci(diffs, median, BOOTSTRAP_SEED + ":paired:" + run_a + ":" + run_b),
            "share_second_slower": round(sum(1 for d in diffs if d > 0) / len(diffs), 3) if diffs else None,
            "note": "The two runs ask the same 33 questions at different commits (ec675d5 and 827fcd5), after planner and service changes: they are different code, not repeats. "
                    "Run-to-run variability is therefore not measured, and the difference is not a causal estimate."}


# ------------------------------------------------------------------------------------------------------------------- build
def build():
    inputs = Inputs()
    for rel in LOCAL_INPUTS:
        if not os.path.isfile(path_of(rel)):
            raise Unavailable("%s: absent (git-ignored raw evidence)" % rel)
    profile = read_json(LOAD_PROFILE)
    inputs.touch(LOAD_PROFILE)
    rates = (float(profile["llm"]["pricing"]["input_usd_per_million_tokens"]), float(profile["llm"]["pricing"]["output_usd_per_million_tokens"]))
    rb_raw, rb_sha, rb_csv = rb_sources()
    rb, rb_rows = analyse_load_run(rb_raw, rb_sha, inputs, rb_csv, "rb-20261118")
    inputs.touch(rb_sha, "rb-20261118 raw/raw.sha256")
    rb["environment"] = "AWS-ECS"
    rb["error_burst"] = error_burst(rb_rows, "hold-50")
    p35, _ = analyse_load_run(P35_RUN + "/raw", NOTES_LINES["p35_raw_sha"], inputs, NOTES_LINES["p35_summary_csv"], "p35-local-1")
    inputs.touch(NOTES_LINES["p35_raw_sha"])
    p35["environment"] = "LOCAL-LOOPBACK-DOCKER"
    windows = dict((p["phase"], (p["started_utc"], p["ended_utc"], p["level"])) for p in rb["phases"])
    run_end = max(parse_utc(p["ended_utc"]) for p in rb["phases"])
    elastic = elasticity(NOTES_LINES["ecs_poll"], windows, run_end, inputs)
    elastic["environment"] = "AWS-ECS"
    elastic["dashboard_reading"] = dashboard_reading()
    inputs.touch(DECISION_LOG)
    elastic["configured_cooldown_note"] = ("Scale-in cooldown 300 s and scale-out cooldown 60 s are the configured values in the Terraform policy, recorded in "
                                           "docs/agent-runs/phase-15/owner-report.md (the P41 section, 'Cooldowns: scale-in 300, scale-out 60'); they are configuration, not a measurement.")
    recovery = failure_recovery(NOTES_LINES["failure_probe"], inputs)
    recovery["environment"] = "AWS-ECS"
    decision_claim = None
    for line in read_lines(DECISION_LOG):
        m = re.search(r"Recovery to 200/200 about (\d+) min (\d+) s after the stop", line)
        if m:
            decision_claim = int(m.group(1)) * 60 + int(m.group(2))
    ev = recovery["stop_task_events"]
    first = next((e for e in ev if e.get("stop_to_recovery_seconds")), None)
    recovery["cross_check_decision_log_round_1_seconds"] = decision_claim
    recovery["cross_check_round_1"] = "MATCH" if first and decision_claim == first["stop_to_recovery_seconds"] else "MISMATCH or absent"
    emr = emr_steps(NOTES_LINES["emr_run"], inputs)
    cost = emr_cost(NOTES_LINES["emr_actual"], NOTES_LINES["emr_counters"], inputs)
    chain = p6_chain(inputs)
    comparison = emr_vs_local(emr, chain)
    local_ref = next((r for r in chain["runs"] if r["run_id"] == comparison.get("local_reference_run")), None)
    comparison["hadoop_counters_equal_emr_vs_local"] = bool(local_ref and local_ref["hadoop_counters"] == cost["hadoop_prep_counters_on_emr"])
    runs, answer_rows = [], {}
    for name in Q12_RUNS:
        entry, rows = llm_run(name.replace("target/experiment-runs/", ""), "LOCAL-LOOPBACK-LLM", rates, inputs)
        runs.append(entry)
        answer_rows[entry["run_id"]] = rows
    entry, _ = llm_run("16b-live-evaluation-16b-1", "AWS-ECS-LLM", rates, inputs)
    runs.append(entry)
    result = {
        "schema": SCHEMA,
        "scope": "offline recomputation from raw evidence; no network, AWS, model call or spend",
        "percentile_method": "nearest-rank", "bootstrap": {"seed": BOOTSTRAP_SEED, "resamples": BOOTSTRAP_RESAMPLES, "used_for": "Q12 answer latency (independent questions) only"},
        "inputs_sha256": dict(sorted(inputs.shas.items())),
        "load_aws_ecs": rb, "load_local_loopback_docker": p35, "elasticity_aws_ecs": elastic, "failure_recovery_aws_ecs": recovery,
        "emr_steps": emr, "emr_cost": cost, "local_chain": chain, "emr_vs_local_same_input": comparison,
        "llm_answer_latency": {"runs": runs, "paired_q12": paired_latency(answer_rows["q12-run-1"], answer_rows["q12-run-2"], "q12-run-1", "q12-run-2"),
                               "rates_usd_per_million_tokens": {"input": rates[0], "output": rates[1], "source": LOAD_PROFILE},
                               "note": "Q12 answers include a live Anthropic call and the graph retrieval; the loopback client is the same machine as the service. The probe runs are one answer each. "
                "The p50 bootstrap interval resamples these questions only: it describes this question mix (answered, abstained and refused questions together), not a population of questions."},
        "vectors": vectors(inputs), "cost_report": cost_report(NOTES_LINES["cost_report"], inputs),
        "gaps": [
            {"metric": "scale-out trigger delay and scale-in delay as single numbers", "reason": "ECS polls were blank (credential failure) before 20:51:54Z and between 21:00:02Z and 21:15:35Z, and no CloudWatch alarm history or service-event export was saved; only brackets are reported."},
            {"metric": "throughput and latency at 2 tasks versus 1 task", "reason": "the 2026-11-18 run was aborted by the load generator's 5xx guard at 20:52:49Z, about 32 s into hold-50, before the second task was running; no complete level was measured on 2 tasks."},
            {"metric": "p50/p95/p99 over repeated AWS load runs", "reason": "one AWS load run exists (the stack was destroyed); no repeat, so no run-to-run interval."},
            {"metric": "recomputation of the P35 local-rehearsal rows from the repository", "reason": "its raw requests.jsonl (83 MB) is NOT frozen in the repository (hash-only: the sha256 is in the committed raw.sha256) and stays on the laptop, so those rows regenerate only on that machine; the committed harness summary under docs/agent-runs/phase-15/evidence/p35 is the repository record. The AWS rb-20261118 raw (11 MB) is in the repository under experiments/results/phase16/performance/raw-rb-20261118 (hash-verified), but the script still needs the git-ignored P35 and P6 inputs, so a clean clone cannot rerun it."},
            {"metric": "cooldown-observe phase (1,800 s) result", "reason": "skipped after the abort (events.jsonl phase-skipped)."},
            {"metric": "cost of the ECS/ALB load, cost per request", "reason": "see cost_report.gap."},
            {"metric": "EMR scaling (speed-up versus node count) and Spark runtime on EMR", "reason": "only one EMR size-100 run reached the Spark step and it failed ('Unknown Error.'); the five size-25 runs of 2026-11-14 (Session 1) ended with exit codes 3, 5, 5, 5, 4 in their experiment-result.json files and produced no Hadoop counters (the owner report records hadoop-prep failing after 10 s on a missing config reference, docs/agent-runs/phase-15/owner-report.md line 2124); no EMR cluster size was completed end to end."},
            {"metric": "Neptune and DynamoDB request latency under load", "reason": "no per-store latency export exists in the repository (only the aborted semantic-route run was executed; the graph routes were dropped: no node_ids supplied)."},
        ],
        "threats_to_validity": [
            "The P35 raw (83 MB) is not in the repository: a reader without the laptop can check those rows only against the committed harness summary and the raw sha256, not recompute them.",
            "Single runs: each load level was run once; percentiles are point estimates and the per-minute spread is the only variability evidence.",
            "Load generator and service share the laptop in the LOCAL-LOOPBACK rows, and in the Q12 rows the client, the service and the graph export are one machine; those numbers are not AWS numbers.",
            "The AWS run used the semantic route only (no LLM, graph routes dropped), so its throughput does not describe /v1/query.",
            "The aborted AWS run covers about 32 s of hold-50, so the steady-state hold behaviour on AWS is unmeasured.",
            "EMR step times are upper bounds from submission instants, not from the EMR console.",
            "Token costs are the synthesis call only at the pinned rates (estimates); the Anthropic console is the cost of record.",
        ],
    }
    return result


# ----------------------------------------------------------------------------------------------------------------- markdown
def md_table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]


def load_table(run):
    rows = []
    for p in run["phases"]:
        lat = p["latency_ms_all_responses"]
        rows.append([p["phase"], p["level"], p["requests"], p["throughput_rps"], p["peak_success_rps_1s"], lat["p50"], lat["p95"], lat["p99"],
                     "%d (%s)" % (p["failures_5xx_or_transport"], p["error_rate_5xx_or_transport"]), p["rate_limited_429"], p["cross_check_vs_harness_summary"][:5]])
    return md_table(["phase", "level (workers)", "requests", "throughput req/s", "peak ok req/s in 1 s", "p50 ms", "p95 ms", "p99 ms", "errors (rate)", "429", "vs harness"], rows)


def render_md(r):
    L = ["# Phase 16 group 5: performance and elasticity", "",
         "Generated by `experiments/scripts/eval16_perf.py` from raw evidence (see `inputs_sha256` in `performance-metrics.json`). Measured facts only in the tables; interpretation is "
         "confined to the notes marked Interpretation. Every table names its environment; numbers from different environments must not be compared as if equal.", ""]
    rb, p35 = r["load_aws_ecs"], r["load_local_loopback_docker"]
    L += ["## 1. AWS ECS: semantic route load, run `%s`" % rb["run_id"], "",
          "Environment: AWS-ECS (deployed query-api behind the ALB, non-loopback https, host withheld), commit `%s`, %s to %s, outcome **%s** (%s), LLM disabled, routes %s. "
          "Percentiles are nearest-rank over responses; raw sha256 verified against `raw.sha256`. The AWS raw (11 MB) is in the repository (`experiments/results/phase16/performance/raw-rb-20261118/`, hash-verified against its SHA256SUMS; scan record `raw-rb-20261118-freeze-note.json`); the script still needs the git-ignored P35 and P6 inputs to run, so a clean clone cannot rerun it." % (rb["commit"][:7], rb["started_utc"], rb["ended_utc"], rb["outcome"], rb["outcome_reason"], ", ".join(rb["routes"])), ""]
    L += load_table(rb)
    b = rb["error_burst"]
    L += ["", "Error burst in `hold-50`: %d failed requests (status codes %s, outcomes %s), all started between %s and %s, error latency min/median/max %s / %s / %s ms. "
          "Total requests %d, outcomes %s." % (b["errors"], b["status_codes"], b["outcomes"], b["first_error_started_utc"], b["last_error_started_utc"], b["error_latency_ms"]["min"],
                                              b["error_latency_ms"]["median"], b["error_latency_ms"]["max"], rb["total_requests"], rb["total_outcomes"]), "",
          "Per-minute spread (requests / errors / p95 ms): " + "; ".join("%s %s %d/%d/%s" % (m["minute_utc"][11:16], m["phase"], m["requests"], m["errors_5xx_or_transport"], m["p95_ms"]) for m in rb["per_minute"]), ""]
    L += ["## 2. Local loopback (Docker 0.25 vCPU): P35 rehearsal `%s`" % p35["run_id"], "",
          "Environment: LOCAL-LOOPBACK-DOCKER (offline-synthetic query-api in Docker, cgroup 0.25 vCPU, load generator on the host), commit `%s`, tree dirty %s, %s to %s, outcome %s. "
          "**Not an AWS number.** Raw `requests.jsonl` sha256 verified against the committed `raw.sha256`. **The 83 MB raw is not in the repository (hash-only); it stays on the laptop, so these rows can be recomputed only there; the committed harness summary under docs/agent-runs/phase-15/evidence/p35 is the repository record.**" % (p35["commit"][:7], p35["tree_dirty"], p35["started_utc"], p35["ended_utc"], p35["outcome"]), ""]
    L += load_table(p35)
    hold = [m for m in p35["per_minute"] if m["phase"] == "hold-50"]
    L += ["", "hold-50 per-minute p95 range (ms): %s to %s over %d minutes (requests per minute %s)." % (min(m["p95_ms"] for m in hold), max(m["p95_ms"] for m in hold), len(hold), [m["requests"] for m in hold]), ""]
    e = r["elasticity_aws_ecs"]
    so, si = e.get("scale_out", {}), e.get("scale_in", {})
    L += ["## 3. AWS ECS elasticity (poll bracket, not a delay measurement)", "",
          "Source `%s`: %d poll lines, %d with data, %d blank (credential failure). Median poll interval %s s." % (e["source"], e["poll_lines_total"], e["poll_lines_with_data"], e["poll_lines_blank"], e["poll_interval_seconds_median"]), ""]
    L += md_table(["event", "bracket / value", "source line"],
                  [["last poll with data before scale-out", "%s state %s" % (so["last_poll_with_data_before"]["utc"], so["last_poll_with_data_before"]["state"]), so["last_poll_with_data_before"]["line"]],
                   ["first poll desired=2", "%s state %s" % (so["first_poll_desired_2"]["utc"], so["first_poll_desired_2"]["state"]), so["first_poll_desired_2"]["line"]],
                   ["first poll running=2", so["first_poll_running_2"]["utc"], so["first_poll_running_2"]["line"]],
                   ["desired=2 seen at most N s after phase start", so["desired_2_no_later_than_seconds_after_phase_start"], ""],
                   ["task start upper bound (desired=2 to running=2)", "%s s" % so["task_start_upper_bound_seconds"], ""],
                   ["last poll desired=2", si["last_poll_desired_2"]["utc"], si["last_poll_desired_2"]["line"]],
                   ["first later poll with data", "%s state %s" % (si["first_later_poll_with_data"]["utc"], si["first_later_poll_with_data"]["state"]), si["first_later_poll_with_data"]["line"]],
                   ["scale-in bracket, s after load stop", si["scale_in_happened_between_seconds_after_load_stop"], ""]])
    d = e["dashboard_reading"]
    L += ["", "Dashboard reading recorded by the human (%s): HealthyHostCount 1->2 about %s, 2->1 about %s, CPU max %s%%, request peak %s per minute, p99 spike to %s." % (
        d["source"], d["healthy_hosts_1_to_2"], d["healthy_hosts_2_to_1"], d["cpu_max_percent"], d["requests_peak_per_minute"], d["p99_spike"]),
          "Interpretation limit: " + so["interpretation_limit"], "", e["configured_cooldown_note"], ""]
    f = r["failure_recovery_aws_ecs"]
    L += ["## 4. AWS ECS failure injection and recovery (stop-task)", "", "Source `%s`; %d probes, median interval %s s (max %s s)." % (f["source"], f["probe_count"], f["probe_interval_seconds_median"], f["probe_interval_seconds_max"]), ""]
    rows = []
    for ev in f["stop_task_events"]:
        if "first_non_200_probe" in ev:
            rows.append([ev["stop_task_utc_time"], ev["stop_task_logged_line"], ev["first_non_200_probe"]["utc_time"], ev["last_non_200_probe_utc_time"],
                         ev["first_probe_with_both_200_after"]["utc_time"], ev["stop_to_recovery_seconds"], ev["observed_outage_seconds_first_bad_to_first_good"],
                         "%s / %s" % (ev["healthz_codes_during_outage"], ev["readyz_codes_during_outage"])])
        else:
            rows.append([ev["stop_task_utc_time"], ev["stop_task_logged_line"], "none", "none", "none", None, None, ev["observed"]])
    L += md_table(["stop-task logged", "log line", "first non-200", "last non-200", "first both 200", "stop to recovery s", "observed outage s", "codes healthz / readyz"], rows)
    L += ["", "Cross-check: the decision log states round-1 recovery as %s s: %s." % (f["cross_check_decision_log_round_1_seconds"], f["cross_check_round_1"]), "Interpretation limit: " + f["interpretation_limit"], ""]
    em, ec, cmp_ = r["emr_steps"], r["emr_cost"], r["emr_vs_local_same_input"]
    L += ["## 5. EMR (AWS-EMR) size-100 run and local chain", "", "EMR run `15a-emr-size-100-20261118T163203Z-87466` (m5.xlarge core, r5.xlarge primary, commit bd0b818). " + em["interpretation_limit"], ""]
    L += md_table(["step", "submitted UTC", "state", "seconds to next event (upper bound)", "local wall s (same input, commit bd0b818)", "EMR / local"],
                  [[x["step"], next((s["submitted_utc"] for s in em["steps"] if s["step"] == x["step"]), ""), x["emr_state"], x["emr_seconds_upper_bound"], x["local_wall_seconds"],
                    x["emr_over_local"]] for x in cmp_["rows"]])
    L += ["", "hadoop-prep input records per second (INPUT counter %s): local %s, EMR (lower bound) %s; Hadoop counters identical on EMR and local: %s." % (
        cmp_["hadoop_prep_input_records"], cmp_["hadoop_prep_records_per_second_local"], cmp_["hadoop_prep_records_per_second_emr_lower_bound"], cmp_["hadoop_counters_equal_emr_vs_local"]), "",
          "Interpretation limit: " + cmp_["interpretation_limit"], ""]
    L += ["EMR billing window (ledger actuals; `%s`):" % ec["source"], ""]
    L += md_table(["line", "window", "seconds", "$/h", "measured $ (recorded)", "recomputed $", "reserved estimate $"],
                  [[a["line"], "%s .. %s" % (a["window_start_utc"][11:19], a["window_end_utc"][11:19]), a["seconds"], a["hourly_usd"], a["measured_usd_recorded"], a["measured_usd_recomputed"], a["reserved_estimate_usd"]] for a in ec["ledger_actual_lines"]])
    L += ["", ec["note"], ""]
    L += ["Local P6 chain runs (LOCAL-MAC; step wall seconds):", ""]
    steps = ["stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job", "copy-out"]
    L += md_table(["run", "size", "passed", "head", "clean tree"] + steps,
                  [[c["run_id"], c["size"], c["all_steps_passed"], (c["git_head"] or "")[:7], c["work_tree_clean"]] + [next((s["wall_seconds"] for s in c["steps"] if s["step"] == st), "") for st in steps] for c in r["local_chain"]["runs"]])
    L += ["", "Spark-only bypass runs (entity resolution bypassed): " + "; ".join("%s wall %s s, peak RSS %s B (%s)" % (b2["label"], b2["wall_seconds"], b2["peak_rss_bytes"], b2["source"]) for b2 in r["local_chain"]["spark_only_bypass_runs"]), ""]
    L += ["## 6. LLM answer latency (end to end, one request per question)", "", "Environments differ by row; token cost is the synthesis call only at the pinned rates (estimate; the Anthropic console is the cost of record).", ""]
    L += md_table(["run", "environment", "commit", "n", "outcomes", "server failures", "p50 ms (95% CI)", "p95 ms", "p99 ms", "ok-only p50 / p95 ms", "answers with usage", "in / out tokens", "est. USD (synthesis)"],
                  [[x["run_id"], x["environment"], x["commit"][:7], x["questions"], x["outcomes"], x["server_failures_5xx_or_transport"],
                    "%s %s" % (x["latency_ms_all"]["p50"], x["latency_ms_all"]["p50_bootstrap_95ci"] or ""), x["latency_ms_all"]["p95"], x["latency_ms_all"]["p99"],
                    "%s / %s" % (x["latency_ms_ok_only"]["p50"], x["latency_ms_ok_only"]["p95"]),
                    x["synthesis_token_usage"] and x["synthesis_token_usage"]["answers_with_recorded_usage"], x["synthesis_token_usage"] and "%d / %d" % (x["synthesis_token_usage"]["input_tokens"], x["synthesis_token_usage"]["output_tokens"]),
                    x["synthesis_token_usage"] and x["synthesis_token_usage"]["estimated_usd_at_pinned_rates"]] for x in r["llm_answer_latency"]["runs"]])
    pq = r["llm_answer_latency"]["paired_q12"]
    L += ["", "Paired Q12 runs (%s then %s, %d questions): median per-question difference %s ms (95%% bootstrap CI %s), second run slower for %s of the questions. %s" % (
        pq["pair"][0], pq["pair"][1], pq["questions"], pq["median_diff_ms_second_minus_first"], pq["median_diff_bootstrap_95ci"], pq["share_second_slower"], pq["note"]),
          "With n = 33 the nearest-rank p95 is the 32nd and p99 the 33rd (maximum) value: they are order statistics, not stable tail estimates; n = 1 for the probes. The p50 bootstrap interval resamples these questions only: it describes this question mix (answered, abstained and refused questions together), not a population of questions.", ""]
    v = r["vectors"]
    L += ["## 7. S3 Vectors ingest and query smoke", "", "Environment: " + v["environment"], "",
          "Ingest `%s`: %d vectors written in %s s = %s vectors/s (recorded %s), concurrency %d, %d embedding calls in %d underlying batch calls, rejected %d, conflicts %d. "
          "First attempt failed (%s) after %s s; the second completed in %s s. The assumed upper bound USD %s is not a bill." % (
              v["ingest"]["source"], v["ingest"]["vectors_written"], v["ingest"]["elapsed_seconds"], v["ingest"]["vectors_per_second_recomputed"], v["ingest"]["vectors_per_second_recorded"],
              v["ingest"]["ingest_concurrency"], v["ingest"]["embedding_calls"], v["ingest"]["underlying_embedding_batch_calls"], v["ingest"]["rejected"], v["ingest"]["conflicts"],
              v["ingest"]["attempts"][0]["error"], v["ingest"]["attempts"][0]["total_seconds"], v["ingest"]["attempts"][1]["total_seconds"], v["ingest"]["assumed_upper_bound_usd_not_a_bill"]), "",
          "Query smoke (%s): samples %s ms, nearest-rank p50 %s, p95 %s (n = %d). %s" % (v["query_smoke"]["latency_scope"], v["query_smoke"]["latency_ms_per_sample"], v["query_smoke"]["p50_ms"], v["query_smoke"]["p95_ms"], v["query_smoke"]["samples"], v["query_smoke"]["note"]), ""]
    c = r["cost_report"]
    L += ["## 8. Cost evidence", "", "Whole-project AWS bill (Cost Explorer, `%s` line %d): total USD %s for %s..%s; the Session 2 day (2026-11-18) USD %s = %s (parts sum %s)." % (
        c["source"], c["line"], c["project_total_usd"], c["period"][0], c["period"][1], c["session_2_day_usd"], c["session_2_day_by_service_usd"], c["service_parts_sum_usd"]), "", "GAP: " + c["gap"], ""]
    L += ["## 9. GAPs (no raw evidence; nothing estimated)", ""] + ["- **%s**: %s" % (g["metric"], g["reason"]) for g in r["gaps"]] + ["", "## 10. Threats to validity", ""] + ["- " + t for t in r["threats_to_validity"]]
    L += ["", "## 11. Inputs (sha256)", ""] + ["- `%s` %s" % (k, h) for k, h in r["inputs_sha256"].items()]
    return "\n".join(L) + "\n"


def write(out_dir, name, text):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=os.path.join(ROOT, "experiments", "results", "phase16", "performance"))
    args = parser.parse_args(argv)
    try:
        result = build()
    except Unavailable as error:
        print("INPUTS-UNAVAILABLE: %s (git-ignored raw evidence or a committed record is missing; nothing written)" % error)
        return 3
    except Refused as error:
        print("REFUSED: %s" % error)
        return 1
    write(args.out_dir, "performance-metrics.json", json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    write(args.out_dir, "performance-metrics.md", render_md(result))
    print("WROTE %s (performance-metrics.json, performance-metrics.md)" % args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

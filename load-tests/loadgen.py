#!/usr/bin/env python3
"""ScholarChain query-api load generator (Phase 15, experiment D / 15B). Python 3 standard library only; run with python3 -I.

It drives the deployed query-api over HTTPS (plain http only for a loopback host) at the concurrency levels 1, 5, 25 and 50 for
bounded durations and writes immutable raw results. Nothing here calls AWS directly; the only network peer is the base URL you give.

DEFAULT: non-LLM endpoints only (GET /healthz /readyz /metrics, /v1/graph/nodes/{id}, /v1/graph/nodes/{id}/neighbors,
/v1/evidence/{id}). POST /v1/query runs the planner and the synthesis model (claude-haiku-5-5 on the Anthropic API, billed outside the AWS credits), so
it is OPT-IN (--llm) and charged to the 15b answer BUCKET of the shared ledger (load-tests/llm_budget.py; bucket sizes are pinned in
experiments/manifests/llm-allocation.json, overall cap USD 1.33):
  * planned answers must fit in the bucket's remaining answers, and (used + planned) x cost must stay within the shared cap;
  * the ledger must already exist (`llm_budget.py init`, once): an absent ledger is never read as zero;
  * --remaining-cap-usd (optional) lowers the run's own spend limit further;
  * the bucket and the cap are re-checked, under a file lock, BEFORE EVERY LLM request and the charge is appended before sending;
    the moment the 15b bucket (or the total, or the run limit) is exhausted all LLM calls stop for the rest of the run.
The cost per answer is an ESTIMATE derived from config/load-profile.v1.json (tokens x pinned claude-haiku-5-5 rates); it is not metered.

Subcommands
  plan            print the effective plan, the answer budget table and every refusal; sends nothing
  run             execute (sends requests); --manifest FILE takes the phases from a load experiment manifest
  summarize DIR   recompute derived/summary.json, summary.csv and timeline.csv from DIR/raw (hash-verified first)
  validate-manifest FILE   check a load experiment manifest (schema scholarchain.load-experiment-manifest.v1)
The ledger commands (init, status, reserve, release, transfer, adjust) are in load-tests/llm_budget.py.

Secrets: the API key is read only from the environment variable NAMED by --api-key-env (default SCHOLARCHAIN_LOAD_API_KEY).
Its value is sent only in the Authorization header of routes that need it. It is never printed, logged or written; response
bodies are not stored. The target host name is not written to the raw results either (only its sha256), because the domain is private.

Exit codes: 0 ok, 2 usage error, 3 refused before sending anything, 4 run aborted (repeated 5xx or auth failure, interrupt), 5 I/O error.
"""
import argparse
import collections
import csv
import datetime
import decimal
import hashlib
import http.client
import importlib.util
import io
import json
import math
import os
import random
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
_spec = importlib.util.spec_from_file_location("llm_budget_for_loadgen", os.path.join(HERE, "llm_budget.py"))
llm_budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(llm_budget)
Refused = llm_budget.Refused  # one refusal type for the generator and the ledger
money, parse_decimal, load_profile, cost_per_answer = llm_budget.money, llm_budget.parse_decimal, llm_budget.load_profile, llm_budget.cost_per_answer
DEFAULT_PROFILE = os.path.join(HERE, "config", "load-profile.v1.json")
DEFAULT_OUTPUT_ROOT = os.path.join(REPO, "target", "experiment-runs")
DEFAULT_KEY_ENV = "SCHOLARCHAIN_LOAD_API_KEY"
DEFAULT_URL_ENV = "SCHOLARCHAIN_LOAD_BASE_URL"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
D = decimal.Decimal
MICRO = D("0.000001")
EXPERIMENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,29}$")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:~-]{1,200}$")  # IDs the service returns (queryId, jobId)
FILE_ID = re.compile(r"^[^\s\x00-\x1f\x7f]{1,200}$")  # IDs supplied in files; always URL-quoted before use
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
MAX_BODY = 262144
USER_AGENT = "scholarchain-loadgen/1"
MANIFEST_SCHEMA = "scholarchain.load-experiment-manifest.v1"
MANIFEST_KEYS = {"schema", "id", "description", "region", "target", "phases", "llm", "metrics_to_collect", "approval_record_path", "provenance", "limits_note"}
PHASE_LOAD_KEYS = {"name", "type", "level", "duration_seconds", "llm_answers", "max_requests", "max_rps", "purpose"}
PHASE_OBSERVE_KEYS = {"name", "type", "duration_seconds", "purpose"}


class UsageError(Exception):
    pass


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (moment.microsecond // 1000)


def stamp(epoch):
    return iso(datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jdump(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


# -------------------------------------------------------------------------------------------------------------------- URL
def parse_base_url(url):
    parts = urllib.parse.urlsplit(url or "")
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise Refused("the base URL must be http(s)://host[:port]")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise Refused("the base URL must not hold user-info, a path, a query or a fragment")
    if parts.scheme == "http" and parts.hostname not in LOOPBACK:
        raise Refused("plain http is accepted only for a loopback host; use https for a remote target")
    try:
        port = parts.port
    except ValueError:
        raise Refused("the base URL has an invalid port")
    return parts.scheme, parts.hostname, port


def read_key(env_name):
    if not ENV_NAME.match(env_name or ""):
        raise Refused("--api-key-env must be an environment variable NAME")
    value = os.environ.get(env_name, "").strip()
    if not value:
        raise Refused("the environment variable %s holds no API key" % env_name)
    if re.search(r"[\x00-\x1f\x7f\s]", value):
        raise Refused("the API key in %s holds whitespace or control characters" % env_name)
    return value


def read_lines(path, label, limit=100000, maxlen=8192):
    try:
        with open(path, encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
    except OSError:
        raise Refused("%s file %s cannot be read" % (label, path))
    if not lines or len(lines) > limit or any(len(x) > maxlen for x in lines):
        raise Refused("%s file %s must hold 1..%d non-empty lines of at most %d characters" % (label, path, limit, maxlen))
    return lines


# ---------------------------------------------------------------------------------------------------------------- manifest
def manifest_problems(doc):
    problems = []
    if not isinstance(doc, dict):
        return ["the manifest must be a JSON object"]
    for key in sorted(set(doc) - MANIFEST_KEYS):
        problems.append("unknown top-level key: %s" % key)
    if doc.get("schema") != MANIFEST_SCHEMA:
        problems.append("schema must be %s" % MANIFEST_SCHEMA)
    if not isinstance(doc.get("id"), str) or not EXPERIMENT_ID.match(doc.get("id", "")):
        problems.append("id must match %s" % EXPERIMENT_ID.pattern)
    for key in ("description", "region", "approval_record_path"):
        if not isinstance(doc.get(key), str) or not doc[key].strip():
            problems.append("%s must be a non-empty string" % key)
    if not isinstance(doc.get("target"), dict) or not doc["target"].get("service"):
        problems.append("target.service is required")
    phases = doc.get("phases")
    if not isinstance(phases, list) or not phases:
        problems.append("phases must be a non-empty list")
        phases = []
    names = set()
    for index, phase in enumerate(phases):
        label = "phases[%d]" % index
        if not isinstance(phase, dict) or phase.get("type") not in ("load", "observe"):
            problems.append("%s.type must be load or observe" % label)
            continue
        allowed = PHASE_LOAD_KEYS if phase["type"] == "load" else PHASE_OBSERVE_KEYS
        for key in sorted(set(phase) - allowed):
            problems.append("%s has an unknown key: %s" % (label, key))
        name = phase.get("name")
        if not isinstance(name, str) or not re.match(r"^[a-z0-9][a-z0-9-]{0,39}$", name or ""):
            problems.append("%s.name must match ^[a-z0-9][a-z0-9-]{0,39}$" % label)
        elif name in names:
            problems.append("%s.name %s is not unique" % (label, name))
        names.add(name)
        duration = phase.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0 < duration <= 1800:
            problems.append("%s.duration_seconds must be a number from 1 to 1800" % label)
        if phase["type"] == "load":
            level = phase.get("level")
            if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 50:
                problems.append("%s.level must be an integer from 1 to 50" % label)
            answers = phase.get("llm_answers", 0)
            if isinstance(answers, bool) or not isinstance(answers, int) or answers < 0:
                problems.append("%s.llm_answers must be a non-negative integer" % label)
            cap = phase.get("max_requests", 1)
            if isinstance(cap, bool) or not isinstance(cap, int) or not 1 <= cap <= 300000:
                problems.append("%s.max_requests must be an integer from 1 to 300000" % label)
            rate = phase.get("max_rps", 1)
            if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not 0 < rate <= 5000:
                problems.append("%s.max_rps must be a number from 0 to 5000" % label)
    llm = doc.get("llm")
    if not isinstance(llm, dict) or set(llm) - {"default_enabled", "note"} or llm.get("default_enabled") is not False:
        problems.append("llm must be an object with default_enabled false (LLM use is enabled only by --llm on the command line)")
    metrics = doc.get("metrics_to_collect")
    if not isinstance(metrics, list) or not metrics or not all(isinstance(m, dict) and m.get("source") and m.get("metric") for m in metrics):
        problems.append("metrics_to_collect must be a non-empty list of objects with source and metric")
    return problems


def load_manifest(path):
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        raise Refused("the manifest %s is missing or not valid JSON" % path)
    problems = manifest_problems(doc)
    if problems:
        raise Refused("manifest invalid: " + "; ".join(problems))
    return doc, sha256_bytes(raw)


# ------------------------------------------------------------------------------------------------------------------ plan
def parse_level_map(text, label):
    """'1=10,5=15' -> {'1': 10, '5': 15}; with a manifest the keys are phase names ('level-50=20')."""
    out = {}
    for item in [x for x in (text or "").split(",") if x.strip()]:
        key, sep, count = item.partition("=")
        if not sep or not re.match(r"^[A-Za-z0-9-]{1,40}$", key.strip()) or not count.strip().isdigit():
            raise UsageError("%s must look like 1=10,5=15 (phase names such as level-50=20 with a manifest)" % label)
        out[key.strip()] = int(count)
    return out


def build_phases(args, profile, manifest):
    limits = profile["limits"]
    phases = []
    cli_answers = parse_level_map(args.llm_answers, "--llm-answers")
    if manifest:
        for item in manifest["phases"]:
            if item["type"] == "observe":
                phases.append({"name": item["name"], "type": "observe", "duration_seconds": float(item["duration_seconds"])})
            else:
                level = item["level"]
                default = profile["per_level"].get(str(level), {})
                phases.append({
                    "name": item["name"], "type": "load", "level": level, "duration_seconds": float(item["duration_seconds"]),
                    "max_requests": int(item.get("max_requests", default.get("max_requests", 1000))), "max_rps": item.get("max_rps"),
                    "llm_answers": cli_answers.get(item["name"], item.get("llm_answers", default.get("llm_answers", 0))),
                })
        return phases
    try:
        levels = [int(x) for x in args.levels.split(",") if x.strip()]
    except ValueError:
        raise UsageError("--levels must be a comma separated list of integers")
    if not levels:
        raise UsageError("--levels is empty")
    for index, level in enumerate(levels):
        default = profile["per_level"].get(str(level))
        if not 1 <= level <= limits["max_level"]:
            raise Refused("level %d is outside 1..%d" % (level, limits["max_level"]))
        duration = float(args.duration_seconds) if args.duration_seconds is not None else float((default or {}).get("duration_seconds", 60))
        cap = int(args.max_requests) if args.max_requests is not None else int((default or {}).get("max_requests", 1000))
        if index and args.pause_seconds > 0:
            phases.append({"name": "pause-%d" % index, "type": "observe", "duration_seconds": float(args.pause_seconds)})
        phases.append({"name": "level-%d" % level, "type": "load", "level": level, "duration_seconds": duration, "max_requests": cap, "max_rps": args.max_rps,
                       "llm_answers": cli_answers.get(str(level), (default or {}).get("llm_answers", 0))})
    return phases


def check_phase_limits(phases, profile):
    limits = profile["limits"]
    total_seconds = 0.0
    for phase in phases:
        if not 0 < phase["duration_seconds"] <= limits["max_phase_duration_seconds"]:
            raise Refused("phase %s: duration %s s is outside 0..%d s" % (phase["name"], phase["duration_seconds"], limits["max_phase_duration_seconds"]))
        total_seconds += phase["duration_seconds"]
        if phase["type"] == "load" and phase["max_requests"] < 1:
            raise Refused("phase %s: max_requests must be at least 1" % phase["name"])
    if total_seconds > limits["max_total_seconds"]:
        raise Refused("the phases add up to %.0f s, over the %d s total cap" % (total_seconds, limits["max_total_seconds"]))
    if sum(p["max_requests"] for p in phases if p["type"] == "load") > limits["max_total_requests"]:
        raise Refused("the per-phase request caps add up to more than the total cap %d" % limits["max_total_requests"])


def llm_plan(args, profile, phases):
    """Returns the LLM plan; raises Refused for every violated rule. With --llm absent the plan is 'disabled'."""
    cost = cost_per_answer(profile)
    cap = parse_decimal(profile["llm"]["shared_cap_usd"], "shared cap")
    rows = [(p["name"], p["level"], p["llm_answers"]) for p in phases if p["type"] == "load"]
    plan = {"enabled": bool(args.llm), "cost_per_answer_usd": money(cost), "shared_cap_usd": money(cap), "rows": rows, "bucket": args.bucket}
    if not args.llm:
        plan.update(planned_answers=0, planned_cost_usd="0.000000")
        return plan
    answers = sum(r[2] for r in rows)
    planned = cost * answers
    plan.update(planned_answers=answers, planned_cost_usd=money(planned))
    if answers < 1:
        raise Refused("--llm was given but the answer budget for these phases is 0")
    if args.remaining_cap_usd is not None:
        remaining = parse_decimal(args.remaining_cap_usd, "--remaining-cap-usd")
        if remaining > cap:
            raise Refused("--remaining-cap-usd %s exceeds the pinned shared cap %s" % (money(remaining), money(cap)))
        plan["remaining_cap_usd"] = money(remaining)
        if planned > remaining:
            raise Refused("%d planned answers x %s = %s USD exceeds the remaining cap %s USD" % (answers, money(cost), money(planned), money(remaining)))
    budget = llm_budget.Budget(args.ledger, args.allocation, args.profile)
    state = budget.state()  # refuses an absent or corrupt ledger
    if args.bucket not in state["sizes"]:
        raise Refused("unknown bucket %r (buckets: %s)" % (args.bucket, ", ".join(state["sizes"])))
    size, used = state["sizes"][args.bucket], state["used"][args.bucket]
    plan.update(ledger_path=budget.ledger_path, ledger_total_usd=money(state["usd"]), bucket_size=size, bucket_used=used,
                bucket_remaining=size - used, allocation_sha256=budget.alloc_sha)
    if answers > size - used:
        raise Refused("bucket %s: %d planned answers exceed the %d remaining (size %d, used %d); a bucket is a hard stop" % (args.bucket, answers, size - used, size, used))
    if state["usd"] + planned > cap:
        raise Refused("ledger total %s + planned %s USD exceeds the shared cap %s USD" % (money(state["usd"]), money(planned), money(cap)))
    if not args.questions_file:
        raise Refused("--questions-file is required with --llm (one question per line)")
    plan["questions"] = len(read_lines(args.questions_file, "questions"))
    return plan


def print_plan(plan, phases, out):
    out.write("PLAN: %d phase(s), total %.0f s\n" % (len(phases), sum(p["duration_seconds"] for p in phases)))
    for p in phases:
        if p["type"] == "load":
            out.write("PHASE %s: load level=%d duration=%.0fs max_requests=%d\n" % (p["name"], p["level"], p["duration_seconds"], p["max_requests"]))
        else:
            out.write("PHASE %s: observe (no requests) %.0fs\n" % (p["name"], p["duration_seconds"]))
    out.write("LLM: %s\n" % ("ENABLED (opt-in)" if plan["enabled"] else "disabled: non-LLM endpoints only, no POST /v1/query"))
    out.write("LLM-COST-PER-ANSWER-USD: %s (estimate, not metered)\n" % plan["cost_per_answer_usd"])
    if plan["enabled"]:
        for name, level, answers in plan["rows"]:
            out.write("LLM-BUDGET level=%d phase=%s answers=%d est_cost_usd=%s\n" % (level, name, answers, money(D(plan["cost_per_answer_usd"]) * answers)))
        out.write("LLM-TOTAL answers=%d planned_cost_usd=%s bucket=%s bucket_size=%d bucket_used=%d bucket_remaining=%d ledger_total_usd=%s shared_cap_usd=%s remaining_cap_usd=%s\n" % (
            plan["planned_answers"], plan["planned_cost_usd"], plan["bucket"], plan["bucket_size"], plan["bucket_used"], plan["bucket_remaining"],
            plan["ledger_total_usd"], plan["shared_cap_usd"], plan.get("remaining_cap_usd", "none")))


# ------------------------------------------------------------------------------------------------------------------ HTTP
class HttpClient:
    def __init__(self, scheme, host, port, timeout):
        self.scheme, self.host, self.port, self.timeout = scheme, host, port, timeout
        self.conn = None

    def _connect(self):
        if self.scheme == "https":
            self.conn = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=ssl.create_default_context())
        else:
            self.conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except OSError:
                pass
            self.conn = None

    def request(self, method, path, headers, body, timeout):
        """Returns (outcome, status, nbytes, response_request_id, body_bytes_or_None). Never raises for transport problems."""
        for attempt in (1, 2):
            reused = self.conn is not None
            if self.conn is None:
                self._connect()
            self.conn.timeout = timeout
            if self.conn.sock is not None:
                self.conn.sock.settimeout(timeout)
            try:
                self.conn.request(method, path, body=body, headers=headers)
                response = self.conn.getresponse()
                data = response.read(MAX_BODY + 1)
                extra = response.read()  # drain what is left so the connection can be reused
                nbytes = len(data) + len(extra)
                status = response.status
                echoed = response.getheader("X-Request-Id") or ""
                if response.getheader("Connection", "").lower() == "close":
                    self.close()
                return "", status, nbytes, echoed[:128], (data if len(data) <= MAX_BODY else None)
            except (socket.timeout, TimeoutError):
                self.close()
                return "timeout", 0, 0, "", None
            except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError):
                # A kept-alive connection the server closed while idle: reconnect and retry once (the Idempotency-Key makes a POST safe).
                self.close()
                if reused and attempt == 1:
                    continue
                return "transport_error", 0, 0, "", None
            except (OSError, http.client.HTTPException, ssl.SSLError):
                self.close()
                return "transport_error", 0, 0, "", None


def classify(status, error):
    if error:
        return error
    if 200 <= status < 300:
        return "ok"
    if status == 429:
        return "throttled"
    if 400 <= status < 500:
        return "client_error"
    if status >= 500:
        return "server_error"
    return "other"


# ------------------------------------------------------------------------------------------------------------------ runner
class Phase:
    def __init__(self, runner, spec):
        self.runner, self.spec = runner, spec
        self.lock = threading.Lock()
        self.issued = 0
        self.llm_total = spec.get("llm_answers", 0) if runner.llm_enabled else 0
        self.llm_next = 0
        self.llm_sent = 0
        self.inflight = 0
        self.max_inflight = 0
        self.start = 0.0
        self.deadline = 0.0
        self.llm_sem = threading.Semaphore(runner.limits["llm_max_inflight"])

    def take_request(self):
        with self.runner.count_lock:
            if self.runner.total_requests >= self.runner.limits["max_total_requests"]:
                return 0
            with self.lock:
                if self.issued >= self.spec["max_requests"]:
                    return 0
                self.issued += 1
            self.runner.total_requests += 1
            return self.runner.total_requests

    def try_llm_slot(self):
        if self.llm_total == 0 or self.runner.llm_stopped.is_set():
            return None
        with self.lock:
            if self.llm_next >= self.llm_total:
                return None
            # Slot i is due when the phase is (i + 0.5) / N done, by elapsed time OR by share of the request cap, whichever is further
            # along, so a fast target that exhausts the request cap early still gets every planned answer before the phase ends.
            done = max((time.monotonic() - self.start) / self.spec["duration_seconds"], self.issued / float(self.spec["max_requests"]))
            if done < (self.llm_next + 0.5) / self.llm_total or not self.llm_sem.acquire(blocking=False):
                return None
            self.llm_next += 1
            return self.llm_next


class Runner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.profile = cfg["profile"]
        self.limits = self.profile["limits"]
        self.scheme, self.host, self.port = cfg["target"]
        self.key = cfg.get("key")
        self.llm_enabled = cfg["llm_plan"]["enabled"]
        self.stop = threading.Event()
        self.llm_stopped = threading.Event()
        self.abort_reason = ""
        self.count_lock = threading.Lock()
        self.total_requests = 0
        self.io_lock = threading.Lock()
        self.fail_lock = threading.Lock()
        self.window = collections.deque(maxlen=self.limits["abort_failure_window_requests"])
        self.auth_streak = 0
        self.llm_lock = threading.Lock()
        self.llm_spent = D(0)
        self.llm_sent = 0
        self.llm_stop_reason = ""
        self.cost = cost_per_answer(self.profile)
        self.cap = parse_decimal(self.profile["llm"]["shared_cap_usd"], "shared cap")
        self.bucket = cfg["llm_plan"]["bucket"]
        remaining = cfg["llm_plan"].get("remaining_cap_usd")
        self.run_cap = D(remaining) if remaining is not None else None
        self.budget = cfg["budget"] if self.llm_enabled else None
        self.routes = cfg["routes"]
        self.dropped = cfg["dropped"]
        self.counts = collections.Counter()
        self.phase_results = []

    # --- outputs
    def emit(self, record):
        line = jdump(record) + "\n"
        with self.io_lock:
            self.req_file.write(line)
            self.req_file.flush()

    def event(self, name, **fields):
        line = jdump(dict(fields, event=name, at=stamp(time.time()), run_id=self.cfg["run_id"])) + "\n"
        with self.io_lock:
            self.evt_file.write(line)
            self.evt_file.flush()

    # --- abort rules
    def note_outcome(self, outcome, status):
        with self.fail_lock:
            self.window.append(1 if outcome in ("timeout", "transport_error") or status >= 500 else 0)
            self.auth_streak = self.auth_streak + 1 if status in (401, 403) else 0
            if sum(self.window) >= self.limits["abort_failure_threshold"]:
                self._abort("repeated-5xx-or-transport-failures")
            elif self.auth_streak >= self.limits["abort_consecutive_auth_failures"]:
                self._abort("repeated-auth-failures")

    def _abort(self, reason):
        if not self.stop.is_set():
            self.abort_reason = reason
            self.stop.set()
            self.event("abort", reason=reason)

    # --- LLM budget
    def charge_llm(self, phase, seq):
        with self.llm_lock:
            if self.llm_stopped.is_set():
                return False
            entry = {"source": "loadgen:" + self.cfg["run_id"], "run_id": self.cfg["run_id"], "phase": phase.spec["name"], "seq": seq}
            try:
                ok, why = self.budget.try_charge(self.bucket, 1, entry, event="answer", run_usd_spent=self.llm_spent, run_usd_limit=self.run_cap)
            except Refused as error:
                ok, why = False, "ledger-unreadable"
                self.event("llm-ledger-error", detail=str(error)[:200])
            if not ok:
                self.llm_stop_reason = why
                self.llm_stopped.set()
                self.event("llm-cap-reached", reason=why, bucket=self.bucket, answers_sent=self.llm_sent, spent_estimate_usd=money(self.llm_spent))
                return False
            self.llm_spent += self.cost
            self.llm_sent += 1
            return True

    # --- one request
    def headers(self, route, rid, extra=None):
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json", "X-Request-Id": rid, "X-Trace-Id": self.cfg["run_id"]}
        if route["auth"]:
            headers["Authorization"] = "Bearer " + self.key
        headers.update(extra or {})
        return headers

    def send(self, client, phase, worker, seq, route_name, route, path, body=None, extra=None, timeout=None, **fields):
        rid = "%s-%d" % (self.cfg["run_id"], seq)
        wall = time.time()
        t0 = time.perf_counter()
        error, status, nbytes, echoed, data = client.request(route["method"], path, self.headers(route, rid, extra), body, timeout or self.limits["request_timeout_seconds"])
        latency_ms = round((time.perf_counter() - t0) * 1000, 3)
        outcome = classify(status, error)
        record = {
            "schema": "scholarchain.load-request.v1", "run_id": self.cfg["run_id"], "experiment_id": self.cfg["experiment_id"], "seq": seq,
            "phase": phase.spec["name"], "level": phase.spec["level"], "worker": worker, "route": route_name, "method": route["method"],
            "path_template": route["path"].split("?")[0], "status": status, "outcome": outcome, "latency_ms": latency_ms, "bytes": nbytes,
            "started_utc": stamp(wall), "request_id": rid, "echoed_request_id": echoed, "llm": bool(route["llm"]),
        }
        record.update(fields)
        if route["llm"] and data:
            # keep only the two safe identifiers of the answer (never the body): they link the row to /v1/explain and the audit
            try:
                parsed = json.loads(data.decode("utf-8"))
            except ValueError:
                parsed = {}
            if isinstance(parsed, dict):
                for key, field in (("queryId", "query_id"), ("jobId", "job_id")):
                    if isinstance(parsed.get(key), str) and SAFE_ID.match(parsed[key]):
                        record[field] = parsed[key]
        self.emit(record)
        with self.count_lock:
            self.counts[outcome] += 1
        self.note_outcome(outcome, status)
        return status, data

    def do_normal(self, client, phase, worker, seq, rng):
        name = rng.choices(self.routes["names"], weights=self.routes["weights"])[0]
        route = self.cfg["profile"]["routes"][name]
        path = route["path"]
        fields = {}
        if "{node_id}" in path:
            target = rng.choice(self.cfg["node_ids"])
            path = path.replace("{node_id}", urllib.parse.quote(target, safe=""))
            fields["target_id"] = target
        if "{evidence_id}" in path:
            target = rng.choice(self.cfg["evidence_ids"])
            path = path.replace("{evidence_id}", urllib.parse.quote(target, safe=""))
            fields["target_id"] = target
        self.send(client, phase, worker, seq, name, route, path, **fields)

    def do_llm(self, client, phase, worker, seq, index):
        route = self.cfg["profile"]["routes"]["query"]
        questions = self.cfg["questions"]
        question = questions[(index - 1) % len(questions)]
        idem = "lt-%s-%s-%d" % (self.cfg["run_id"], phase.spec["name"], index)
        body = json.dumps({"question": question, "output": {"includeScores": False}}).encode("utf-8")
        extra = {"Content-Type": "application/json", "Idempotency-Key": idem[:256]}
        status, data = self.send(client, phase, worker, seq, "query", route, route["path"], body=body, extra=extra,
                                 timeout=self.limits["llm_request_timeout_seconds"], idempotency_key=idem[:256])
        job_id = ""
        if status == 202 and data:
            try:
                candidate = json.loads(data.decode("utf-8")).get("jobId", "")
            except (ValueError, AttributeError):
                candidate = ""
            job_id = candidate if isinstance(candidate, str) and SAFE_ID.match(candidate) else ""
        if job_id:
            self.poll_job(client, phase, worker, job_id)

    def poll_job(self, client, phase, worker, job_id):
        route = {"method": "GET", "path": "/v1/jobs/{job_id}", "auth": True, "llm": False}
        deadline = time.monotonic() + self.limits["llm_job_poll_seconds"]
        while time.monotonic() < deadline and not self.stop.is_set():
            with self.count_lock:
                self.total_requests += 1
                seq = self.total_requests
            status, data = self.send(client, phase, worker, seq, "job_status", route, "/v1/jobs/" + urllib.parse.quote(job_id, safe=""), job_id=job_id)
            try:
                state = str(json.loads(data.decode("utf-8")).get("state", "")) if data else ""
            except ValueError:
                state = ""
            if status != 200 or state not in ("QUEUED", "RUNNING", "PENDING"):
                return
            time.sleep(1.0)

    def worker(self, phase, wid):
        client = HttpClient(self.scheme, self.host, self.port, self.limits["request_timeout_seconds"])
        rng = random.Random("%s:%s:%d" % (self.cfg["run_id"], phase.spec["name"], wid))
        spec_level = phase.spec["level"]
        try:
            interval = (spec_level / float(phase.spec["max_rps"])) if phase.spec.get("max_rps") else 0.0
            next_at = time.monotonic()
            while not self.stop.is_set() and time.monotonic() < phase.deadline:
                if interval:
                    # optional pacing: this worker sends at most one request per `interval` seconds (all workers together <= max_rps)
                    wait = next_at - time.monotonic()
                    if wait > 0:
                        time.sleep(min(wait, 0.5))
                        continue
                    next_at = max(next_at + interval, time.monotonic() - interval)
                seq = phase.take_request()
                if not seq:
                    break
                with phase.lock:
                    phase.inflight += 1
                    phase.max_inflight = max(phase.max_inflight, phase.inflight)
                try:
                    index = phase.try_llm_slot()
                    if index is not None:
                        try:
                            if self.charge_llm(phase, seq):
                                with phase.lock:
                                    phase.llm_sent += 1
                                self.do_llm(client, phase, wid, seq, index)
                                continue
                        finally:
                            phase.llm_sem.release()
                    self.do_normal(client, phase, wid, seq, rng)
                finally:
                    with phase.lock:
                        phase.inflight -= 1
        finally:
            client.close()

    # --- phases
    def run_load(self, spec):
        phase = Phase(self, spec)
        counts_before = collections.Counter(self.counts)
        phase.start = time.monotonic()
        phase.deadline = phase.start + spec["duration_seconds"]
        started = time.time()
        self.event("phase-start", phase=spec["name"], type="load", level=spec["level"], planned_seconds=spec["duration_seconds"],
                   max_requests=spec["max_requests"], llm_answers_planned=phase.llm_total)
        threads = [threading.Thread(target=self.worker, args=(phase, i), daemon=True) for i in range(spec["level"])]
        for t in threads:
            t.start()
        for t in threads:
            while t.is_alive():
                t.join(0.2)
        ended = time.time()
        delta = {k: v - counts_before.get(k, 0) for k, v in self.counts.items()}
        result = {"phase": spec["name"], "type": "load", "level": spec["level"], "started_utc": stamp(started), "ended_utc": stamp(ended),
                  "requests": phase.issued, "outcomes": {k: v for k, v in sorted(delta.items()) if v}, "max_inflight_observed": phase.max_inflight,
                  "llm_answers_planned": phase.llm_total, "llm_answers_sent": phase.llm_sent}
        self.phase_results.append(result)
        self.event("phase-end", **{k: v for k, v in result.items() if k not in ("phase",)}, phase=spec["name"])

    def run_observe(self, spec):
        started = time.time()
        self.event("phase-start", phase=spec["name"], type="observe", planned_seconds=spec["duration_seconds"])
        end = time.monotonic() + spec["duration_seconds"]
        while not self.stop.is_set() and time.monotonic() < end:
            time.sleep(min(0.2, max(0.0, end - time.monotonic())))
        self.phase_results.append({"phase": spec["name"], "type": "observe", "started_utc": stamp(started), "ended_utc": stamp(time.time())})
        self.event("phase-end", phase=spec["name"], type="observe", started_utc=stamp(started), ended_utc=stamp(time.time()))

    def execute(self, phases):
        run_start = time.monotonic()
        for spec in phases:
            if self.stop.is_set() or time.monotonic() - run_start > self.limits["max_total_seconds"]:
                self.event("phase-skipped", phase=spec["name"], reason=self.abort_reason or "total-time-cap")
                continue
            (self.run_load if spec["type"] == "load" else self.run_observe)(spec)


# ------------------------------------------------------------------------------------------------------------- run setup
def git_state():
    def run(*cmd):
        try:
            done = subprocess.run(["git", "-C", REPO] + list(cmd), capture_output=True, text=True, timeout=20)
            return done.stdout.strip() if done.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain", "--untracked-files=no")
    return commit, (None if status is None else bool(status))


def check_output_root(root):
    root = os.path.abspath(root)
    target = os.path.join(REPO, "target")
    inside = os.path.commonpath([root, REPO]) == REPO
    if inside and os.path.commonpath([root, target]) != target:
        raise Refused("inside the repository the output root must be under the git-ignored target/ directory")
    return root


def new_dir(path, mode=0o700):
    try:
        os.mkdir(path, mode)
    except FileExistsError:
        raise Refused("%s already exists: a run directory is never reused or overwritten" % path)


def open_new_text(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    return os.fdopen(fd, "w", encoding="utf-8")


def default_run_id():
    return "lt-%s-%s" % (utc_now().strftime("%Y%m%dT%H%M%SZ"), os.urandom(2).hex())


def prepare(args, command):
    profile = load_profile(args.profile)
    manifest = manifest_sha = None
    if args.manifest:
        manifest, manifest_sha = load_manifest(args.manifest)
    experiment_id = args.experiment_id or (manifest["id"] if manifest else "adhoc-load")
    if not EXPERIMENT_ID.match(experiment_id):
        raise UsageError("--experiment-id must match %s" % EXPERIMENT_ID.pattern)
    run_id = args.run_id or default_run_id()
    if not RUN_ID.match(run_id):
        raise UsageError("--run-id must match %s" % RUN_ID.pattern)
    phases = build_phases(args, profile, manifest)
    check_phase_limits(phases, profile)
    plan = llm_plan(args, profile, phases)
    budget = llm_budget.Budget(args.ledger, args.allocation, args.profile) if plan["enabled"] else None
    cfg = {"budget": budget, "profile": profile, "profile_sha256": sha256_file(args.profile), "manifest": manifest, "manifest_sha256": manifest_sha, "experiment_id": experiment_id,
           "run_id": run_id, "phases": phases, "llm_plan": plan, "api_key_env": args.api_key_env}
    return cfg


def finish_setup(cfg, args):
    """Everything that needs the network target, the key, ID files and the question list (run only; plan skips the target)."""
    profile = cfg["profile"]
    url = args.base_url or os.environ.get(args.base_url_env, "")
    cfg["target"] = parse_base_url(url)
    cfg["target_loopback"] = cfg["target"][1] in LOOPBACK
    cfg["target_sha256"] = sha256_bytes(("%s://%s:%s" % (cfg["target"][0], cfg["target"][1], cfg["target"][2])).encode("utf-8"))
    cfg["node_ids"] = read_lines(args.node_ids_file, "node ids", maxlen=200) if args.node_ids_file else []
    cfg["evidence_ids"] = read_lines(args.evidence_ids_file, "evidence ids", maxlen=200) if args.evidence_ids_file else []
    for value in cfg["node_ids"] + cfg["evidence_ids"]:
        if not FILE_ID.match(value):
            raise Refused("an ID file holds a value with whitespace or control characters, or longer than 200 characters")
    cfg["questions"] = read_lines(args.questions_file, "questions") if cfg["llm_plan"]["enabled"] else []
    names, weights, dropped = [], [], []
    for name, route in profile["routes"].items():
        if route["llm"] or route["weight"] <= 0:
            continue
        need = route["needs"]
        if need and not cfg[need]:
            dropped.append({"route": name, "reason": "no %s supplied" % need})
            continue
        names.append(name)
        weights.append(route["weight"])
    if not names:
        raise Refused("no routes left to call")
    needs_auth = any(profile["routes"][n]["auth"] for n in names) or cfg["llm_plan"]["enabled"]
    cfg["key"] = read_key(args.api_key_env) if needs_auth else None
    cfg["routes"] = {"names": names, "weights": weights}
    cfg["dropped"] = dropped
    return cfg


def run_command(args, out):
    cfg = prepare(args, "run")
    finish_setup(cfg, args)
    root = check_output_root(args.output_root)
    run_dir = os.path.join(root, "%s-%s" % (cfg["experiment_id"], cfg["run_id"]))
    os.makedirs(root, mode=0o700, exist_ok=True)
    new_dir(run_dir)
    raw_dir = os.path.join(run_dir, "raw")
    new_dir(raw_dir)
    runner = Runner(cfg)
    commit, dirty = git_state()
    started = time.time()
    outcome, reason = "completed", ""
    runner.req_file = open_new_text(os.path.join(raw_dir, "requests.jsonl"))
    runner.evt_file = open_new_text(os.path.join(raw_dir, "events.jsonl"))
    try:
        print_plan(cfg["llm_plan"], cfg["phases"], out)
        out.write("RUN-ID: %s\nRUN-DIR: %s\n" % (cfg["run_id"], run_dir))
        runner.event("run-start", experiment_id=cfg["experiment_id"], commit=commit, tree_dirty=dirty, llm_enabled=runner.llm_enabled,
                     routes=cfg["routes"]["names"], routes_dropped=cfg["dropped"])
        for item in cfg["dropped"]:
            out.write("ROUTE-DROPPED: %s (%s)\n" % (item["route"], item["reason"]))
        runner.execute(cfg["phases"])
        if runner.stop.is_set():
            outcome, reason = "aborted", runner.abort_reason
    except KeyboardInterrupt:
        runner.stop.set()
        outcome, reason = "interrupted", "keyboard-interrupt"
    finally:
        runner.event("run-end", outcome=outcome, reason=reason)
        runner.req_file.close()
        runner.evt_file.close()
    ledger_end = bucket_end = None
    if runner.llm_enabled:
        end_state = runner.budget.state()
        ledger_end, bucket_end = money(end_state["usd"]), end_state["used"][runner.bucket]
    cost_report = llm_budget.cost_report(runner.profile, runner.llm_sent)
    record = {
        "schema": "scholarchain.load-run-record.v1", "run_id": cfg["run_id"], "experiment_id": cfg["experiment_id"], "outcome": outcome, "outcome_reason": reason,
        "started_utc": stamp(started), "ended_utc": stamp(time.time()), "commit": commit, "tree_dirty": dirty,
        "profile": {"path": os.path.relpath(args.profile, REPO) if os.path.commonpath([os.path.abspath(args.profile), REPO]) == REPO else "external", "sha256": cfg["profile_sha256"]},
        "manifest_sha256": cfg["manifest_sha256"], "target": {"scheme": cfg["target"][0], "loopback": cfg["target_loopback"], "base_url_sha256": cfg["target_sha256"],
                                                              "host": cfg["target"][1] if cfg["target_loopback"] else "withheld"},
        "api_key_env": args.api_key_env, "phases": runner.phase_results, "totals": {"requests": runner.total_requests, "outcomes": dict(sorted(runner.counts.items()))},
        "routes": cfg["routes"]["names"], "routes_dropped": cfg["dropped"],
        "llm": {"enabled": runner.llm_enabled, "answers_sent": runner.llm_sent, "estimated_cost_usd": money(runner.llm_spent), "cost_per_answer_usd": money(runner.cost),
                "stopped_reason": runner.llm_stop_reason or None, "shared_cap_usd": money(runner.cap), "remaining_cap_input_usd": cfg["llm_plan"].get("remaining_cap_usd"),
                "bucket": runner.bucket if runner.llm_enabled else None, "bucket_size": cfg["llm_plan"].get("bucket_size"), "bucket_used_at_start": cfg["llm_plan"].get("bucket_used"),
                "bucket_used_at_end": bucket_end, "allocation_sha256": cfg["llm_plan"].get("allocation_sha256"),
                "ledger_path": cfg["llm_plan"].get("ledger_path"), "ledger_total_at_start_usd": cfg["llm_plan"].get("ledger_total_usd"), "ledger_total_at_end_usd": ledger_end,
                "note": "estimated from pinned tokens and rates, not metered; the Anthropic console, the Voyage console and the AWS bill are the costs of record"},
        "cost_report": cost_report,
        "python": sys.version.split()[0],
    }
    with open_new_text(os.path.join(raw_dir, "run-record.json")) as handle:
        handle.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
    seal(raw_dir)
    summarize(run_dir)
    out.write("COST-REPORT: aws=%s anthropic=%s voyage=%s combined=%s (%s)\n" % (
        cost_report["aws"]["usd"] or "not-metered", cost_report["anthropic"]["usd"], cost_report["voyage"]["usd"], cost_report["combined_usd"], cost_report["combined_scope"]))
    out.write("RESULT: %s run=%s requests=%d llm_answers=%d reason=%s\n" % (outcome.upper(), cfg["run_id"], runner.total_requests, runner.llm_sent, reason or "-"))
    return 0 if outcome == "completed" else 4


# ------------------------------------------------------------------------------------------------- raw seal + summarize
def seal(raw_dir):
    names = sorted(n for n in os.listdir(raw_dir) if n != "raw.sha256")
    lines = ["%s  %s\n" % (sha256_file(os.path.join(raw_dir, n)), n) for n in names]
    with open_new_text(os.path.join(raw_dir, "raw.sha256")) as handle:
        handle.write("".join(lines))
    for n in names + ["raw.sha256"]:
        os.chmod(os.path.join(raw_dir, n), 0o444)


def verify_raw(raw_dir):
    try:
        with open(os.path.join(raw_dir, "raw.sha256"), encoding="utf-8") as handle:
            listed = dict((line.split("  ", 1)[1].strip(), line.split("  ", 1)[0]) for line in handle if line.strip())
    except (OSError, IndexError):
        raise Refused("raw.sha256 is missing or malformed in %s" % raw_dir)
    actual = sorted(n for n in os.listdir(raw_dir) if n != "raw.sha256")
    if sorted(listed) != actual:
        raise Refused("the files in %s do not match raw.sha256" % raw_dir)
    for name, digest in listed.items():
        if sha256_file(os.path.join(raw_dir, name)) != digest:
            raise Refused("raw file %s was modified after collection (sha256 mismatch)" % name)


def percentile(sorted_values, p):
    """Nearest-rank percentile: the value at rank ceil(p/100 * n) of the sorted list."""
    if not sorted_values:
        return None
    rank = max(1, math.ceil(p / 100.0 * len(sorted_values)))
    return sorted_values[rank - 1]


def parse_utc(text):
    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc).timestamp()


def group_stats(rows, seconds):
    responded = sorted(r["latency_ms"] for r in rows if r["status"] > 0)
    good = sorted(r["latency_ms"] for r in rows if r["outcome"] == "ok")
    outcomes = collections.Counter(r["outcome"] for r in rows)
    failures = sum(1 for r in rows if r["status"] >= 500 or r["outcome"] in ("timeout", "transport_error"))
    return {
        "requests": len(rows), "outcomes": dict(sorted(outcomes.items())), "seconds": round(seconds, 3),
        "throughput_rps": round(len(rows) / seconds, 3) if seconds > 0 else None,
        "error_rate_5xx_or_transport": round(failures / len(rows), 6) if rows else None,
        "client_error_rate": round(sum(1 for r in rows if r["outcome"] in ("client_error", "throttled")) / len(rows), 6) if rows else None,
        "latency_ms_all_responses": {"p50": percentile(responded, 50), "p95": percentile(responded, 95), "p99": percentile(responded, 99), "n": len(responded)},
        "latency_ms_2xx": {"p50": percentile(good, 50), "p95": percentile(good, 95), "p99": percentile(good, 99), "n": len(good)},
    }


def summarize(run_dir):
    raw_dir = os.path.join(run_dir, "raw")
    verify_raw(raw_dir)
    rows, events = [], []
    with open(os.path.join(raw_dir, "requests.jsonl"), encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    with open(os.path.join(raw_dir, "events.jsonl"), encoding="utf-8") as handle:
        events = [json.loads(line) for line in handle if line.strip()]
    windows = {}
    for event in events:
        if event["event"] == "phase-end" and event.get("type") == "load":
            windows[event["phase"]] = (event["started_utc"], event["ended_utc"], event["level"])
    by_phase = collections.OrderedDict()
    for row in rows:
        by_phase.setdefault(row["phase"], []).append(row)
    phases = []
    for name, (start, end, level) in windows.items():
        group = by_phase.get(name, [])
        entry = {"phase": name, "level": level, "started_utc": start, "ended_utc": end}
        entry.update(group_stats(group, parse_utc(end) - parse_utc(start)))
        entry["routes"] = {route: group_stats([r for r in group if r["route"] == route], parse_utc(end) - parse_utc(start)) for route in sorted({r["route"] for r in group})}
        phases.append(entry)
    summary = {"schema": "scholarchain.load-summary.v1", "run_id": rows[0]["run_id"] if rows else None, "derived_from": "raw/requests.jsonl, raw/events.jsonl (sha256 verified)",
               "percentile_method": "nearest-rank", "phases": phases, "events": [e for e in events if e["event"] in ("abort", "llm-cap-reached", "run-start", "run-end")]}
    derived = os.path.join(run_dir, "derived")
    os.makedirs(derived, mode=0o700, exist_ok=True)
    for name in ("summary.json", "summary.csv", "timeline.csv"):
        if os.path.lexists(os.path.join(derived, name)):
            os.chmod(os.path.join(derived, name), 0o600)
            os.remove(os.path.join(derived, name))  # derived files are reproducible; raw files are never touched
    with open_new_text(os.path.join(derived, "summary.json")) as handle:
        handle.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with open_new_text(os.path.join(derived, "summary.csv")) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["phase", "level", "started_utc", "ended_utc", "requests", "throughput_rps", "error_rate_5xx_or_transport", "client_error_rate", "p50_ms", "p95_ms", "p99_ms"])
        for p in phases:
            lat = p["latency_ms_all_responses"]
            writer.writerow([p["phase"], p["level"], p["started_utc"], p["ended_utc"], p["requests"], p["throughput_rps"], p["error_rate_5xx_or_transport"], p["client_error_rate"], lat["p50"], lat["p95"], lat["p99"]])
    buckets = collections.OrderedDict()
    for row in sorted(rows, key=lambda r: r["started_utc"]):
        minute = row["started_utc"][:16] + ":00Z"  # one row per UTC minute, the CloudWatch period
        buckets.setdefault((minute, row["phase"], row["level"]), []).append(row)
    with open_new_text(os.path.join(derived, "timeline.csv")) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["minute_utc", "phase", "level", "requests", "errors_5xx_or_transport", "p95_ms_all_responses"])
        for (minute, name, level), group in buckets.items():
            lat = sorted(r["latency_ms"] for r in group if r["status"] > 0)
            writer.writerow([minute, name, level, len(group), sum(1 for r in group if r["status"] >= 500 or r["outcome"] in ("timeout", "transport_error")), percentile(lat, 95)])
    return summary


# --------------------------------------------------------------------------------------------------------------------- CLI
def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--profile", default=DEFAULT_PROFILE)
        p.add_argument("--manifest", help="load experiment manifest (phases come from it)")
        p.add_argument("--levels", default="1,5,25,50", help="comma separated concurrency levels (default 1,5,25,50)")
        p.add_argument("--duration-seconds", type=float, help="override the duration of every level (profile default per level)")
        p.add_argument("--max-requests", type=int, help="override the per-level request cap")
        p.add_argument("--max-rps", type=float, help="optional pacing: at most this many requests per second in total, per level")
        p.add_argument("--pause-seconds", type=float, default=5.0, help="idle gap between levels (default 5)")
        p.add_argument("--experiment-id", help="default adhoc-load, or the manifest id")
        p.add_argument("--run-id")
        p.add_argument("--llm", action="store_true", help="OPT IN: also send POST /v1/query (calls claude-haiku-5-5 on the Anthropic API; capped by the answer budget and the ledger)")
        p.add_argument("--llm-answers", help="answer budget per level, for example 1=10,5=15,25=20,50=20 (default: the profile)")
        p.add_argument("--remaining-cap-usd", help="optional extra spend limit for this run in USD (the bucket and the shared cap always apply)")
        p.add_argument("--bucket", default="15b", help="answer bucket charged by --llm (default 15b)")
        p.add_argument("--allocation", default=llm_budget.DEFAULT_ALLOCATION, help="pinned bucket sizes (experiments/manifests/llm-allocation.json)")
        p.add_argument("--ledger", help="LLM ledger path (default from the profile, under ~/.scholarchain)")
        p.add_argument("--questions-file", help="one question per line (required with --llm)")
        p.add_argument("--api-key-env", default=DEFAULT_KEY_ENV, help="NAME of the environment variable holding the API key")

    p = sub.add_parser("plan")
    common(p)
    p = sub.add_parser("run")
    common(p)
    p.add_argument("--base-url", help="https://host[:port] of query-api (or set %s)" % DEFAULT_URL_ENV)
    p.add_argument("--base-url-env", default=DEFAULT_URL_ENV)
    p.add_argument("--node-ids-file", help="graph node IDs, one per line (graph routes are dropped without it)")
    p.add_argument("--evidence-ids-file", help="evidence IDs, one per line (the evidence route is dropped without it)")
    p.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    p = sub.add_parser("summarize")
    p.add_argument("run_dir")
    p = sub.add_parser("validate-manifest")
    p.add_argument("manifest")
    return parser


def main(argv, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "plan":
            cfg = prepare(args, "plan")
            print_plan(cfg["llm_plan"], cfg["phases"], out)
            out.write("RESULT: PLAN-OK (nothing sent)\n")
            return 0
        if args.cmd == "run":
            return run_command(args, out)
        if args.cmd == "summarize":
            summarize(os.path.abspath(args.run_dir))
            out.write("RESULT: SUMMARIZED\n")
            return 0
        if args.cmd == "validate-manifest":
            load_manifest(args.manifest)
            out.write("RESULT: MANIFEST-OK %s\n" % args.manifest)
            return 0
        return 0
    except Refused as error:
        sys.stderr.write("REFUSED: %s\n" % error)
        return 3
    except UsageError as error:
        sys.stderr.write("USAGE: %s\n" % error)
        return 2
    except OSError as error:
        sys.stderr.write("I/O-ERROR: %s\n" % type(error).__name__)
        return 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

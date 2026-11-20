#!/usr/bin/env python3
"""Phase 16B live evaluation runner: the fixed question set through POST /v1/query, charged to answer bucket 16b (python3 -I; stdlib only).

One command asks each question once, in file order, one at a time, and keeps the raw answers. It is the ONLY LLM-calling step that
charges bucket 16b, so do NOT run `llm_budget.py reserve --bucket 16b` for it (the command charges the ledger itself, one answer
before every request, exactly like the 15B load generator does for bucket 15b; reserving as well would count every answer twice).

  plan   print the question count, the bucket state and the estimated cost; reads the questions file and the local ledger only,
         never reads the API key or the base URL and makes NO network call
  run    execute against the deployed query-api (needs SCHOLARCHAIN_LOAD_BASE_URL and the key in the environment variable named by --api-key-env)

Questions: --questions-file, default experiments/inputs/14c/questions.txt (40 fixed questions, one per line; the same file the 15B load
generator cycles through; the 16B run uses each question exactly once). Every question must be in the supported request grammar of the
planner fallback; the file is derived from the real export by experiments/scripts/derive_14c_inputs.py.

Hard stops (all checked before anything is sent; exit 3, nothing written to the ledger):
  * the number of questions to ask must be at most the bucket's remaining answers (a bucket is a hard stop, nothing rolls over);
    a longer file is refused, never silently truncated; --max-answers N (lowers only) asks just the first N questions;
  * (ledger total + planned answers x cost per answer) must not pass the shared USD 1.33 cap;
  * the ledger must exist (an absent or corrupt ledger is never read as zero), the API key and the base URL must be present.
While running, the ledger is locked, re-read and appended with one `answer` line for bucket 16b BEFORE each request; if the bucket or the
cap no longer allows it the run stops (event llm-cap-reached) and sends nothing more. A charge is not refunded after a failed request
(the request may have reached the model); use `llm_budget.py release` only for answers you are sure were never sent.
The run also stops on the first 401/403 and after --max-consecutive-failures failed answers in a row (default 3), so a wrong key or a
dead service cannot burn the bucket.

Raw results (git-ignored, mode 0444, sealed with raw.sha256) under target/experiment-runs/16b-live-evaluation-<run-id>/raw/:
  answers.jsonl      one line per question asked: index, question, idempotency key, status, outcome, latency, query/job ids, job state,
                     sha256 and size of the answer, and the answer JSON itself for 2xx responses (bodies of errors are never stored)
  events.jsonl       run-start, llm-cap-reached, run-end
  run-record.json    commit, tree flag, file hashes, bucket and ledger numbers before and after, cost report (AWS, Anthropic, Voyage, combined)
The API key value is never printed, logged or written (only the variable name); the host name is withheld (only its sha256) unless it is a
loopback test host. Voyage embedding tokens are counted inside the service, not here: report them from the Voyage console.
Grading (groundedness, correctness) is a separate step on answers.jsonl; this command measures nothing it was not asked to.

Exit codes: 0 ok, 2 usage, 3 refused before sending, 4 run stopped early (auth failure, repeated failures, cap, interrupt), 5 I/O error.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
_spec = importlib.util.spec_from_file_location("loadgen_for_eval16b", os.path.join(HERE, "loadgen.py"))
loadgen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loadgen)
llm_budget = loadgen.llm_budget
Refused = loadgen.Refused
UsageError = loadgen.UsageError

BUCKET = "16b"
EXPERIMENT_ID = "16b-live-evaluation"
DEFAULT_QUESTIONS = os.path.join(REPO, "experiments", "inputs", "14c", "questions.txt")
MANIFEST = os.path.join(REPO, "experiments", "manifests", "16b-live-evaluation.json")
RECORD_SCHEMA = "scholarchain.eval16b-run-record.v1"   # evalq12.py sets its own
DEFAULT_KEY_ENV = loadgen.DEFAULT_KEY_ENV
DEFAULT_URL_ENV = loadgen.DEFAULT_URL_ENV
IN_PROGRESS = ("QUEUED", "RUNNING", "PENDING")
DONE_OK = ("SUCCEEDED", "SUCCESS", "COMPLETED", "DONE")
RUN_ID = loadgen.RUN_ID
MAX_ANSWER_BYTES = loadgen.MAX_BODY


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_state(args):
    """Validates everything that does not need the network. Returns the plan dict; raises Refused."""
    profile = loadgen.load_profile(args.profile)
    cost = loadgen.cost_per_answer(profile)
    cap = loadgen.parse_decimal(profile["llm"]["shared_cap_usd"], "shared cap")
    questions = loadgen.read_lines(args.questions_file, "questions")
    if len(set(questions)) != len(questions):
        raise Refused("the questions file holds duplicate questions")
    if args.max_answers is not None:
        if args.max_answers < 1:
            raise Refused("--max-answers must be at least 1")
        questions = questions[:args.max_answers]
    budget = llm_budget.Budget(args.ledger, args.allocation, args.profile)
    state = budget.state()  # refuses an absent or corrupt ledger
    size, used = state["sizes"][BUCKET], state["used"][BUCKET]
    remaining = size - used
    planned = len(questions)
    total = cost * planned
    plan = {"questions": questions, "planned_answers": planned, "cost_per_answer_usd": loadgen.money(cost), "planned_cost_usd": loadgen.money(total),
            "shared_cap_usd": loadgen.money(cap), "bucket": BUCKET, "bucket_size": size, "bucket_used": used, "bucket_remaining": remaining,
            "ledger_path": budget.ledger_path, "ledger_total_usd": loadgen.money(state["usd"]), "allocation_sha256": budget.alloc_sha,
            "questions_sha256": loadgen.sha256_file(args.questions_file), "profile": profile, "budget": budget}
    if planned > remaining:
        raise Refused("bucket %s: %d questions to ask exceed the %d remaining answers (size %d, used %d); a bucket is a hard stop: "
                      "shorten the file, use --max-answers, or ask the user for an approved transfer" % (BUCKET, planned, remaining, size, used))
    if state["usd"] + total > cap:
        raise Refused("ledger total %s + planned %s USD exceeds the shared cap %s USD" % (loadgen.money(state["usd"]), loadgen.money(total), loadgen.money(cap)))
    return plan


def print_plan(plan, out, mode):
    out.write("EXPERIMENT: %s (LLM bucket %s)\n" % (EXPERIMENT_ID, plan["bucket"]))
    out.write("QUESTIONS: %d from the questions file (sha256 %s)\n" % (plan["planned_answers"], plan["questions_sha256"]))
    out.write("BUCKET %s size=%d used=%d remaining=%d\n" % (plan["bucket"], plan["bucket_size"], plan["bucket_used"], plan["bucket_remaining"]))
    out.write("PLANNED: answers=%d estimated_usd=%s (%s USD per answer, estimate not metered) ledger_total_usd=%s shared_cap_usd=%s\n" % (
        plan["planned_answers"], plan["planned_cost_usd"], plan["cost_per_answer_usd"], plan["ledger_total_usd"], plan["shared_cap_usd"]))
    out.write("LEDGER: %s (this command charges bucket %s itself; do not also run llm_budget.py reserve for it)\n" % (plan["ledger_path"], plan["bucket"]))
    if mode == "plan":
        out.write("NETWORK: none (plan mode reads local files only)\n")


def read_json_body(data):
    if not data:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


class Evaluator:
    def __init__(self, cfg, answers_file, events_file):
        self.cfg = cfg
        self.answers_file, self.events_file = answers_file, events_file
        self.rows = []
        self.charged = 0
        self.consecutive_failures = 0
        self.stop_reason = ""
        self.sleep = time.sleep

    def event(self, kind, **fields):
        record = {"event": kind, "utc": loadgen.stamp(time.time())}
        record.update(fields)
        self.events_file.write(loadgen.jdump(record) + "\n")
        self.events_file.flush()

    def charge(self, index):
        try:
            ok, why = self.cfg["budget"].try_charge(BUCKET, 1, {"run": self.cfg["run_id"], "n": index}, event="answer")
        except Refused as error:
            ok, why = False, "ledger-unreadable"
            self.event("llm-ledger-error", detail=str(error)[:200])
        if not ok:
            self.stop_reason = why
            self.event("llm-cap-reached", reason=why, answers_charged=self.charged)
            return False
        self.charged += 1
        return True

    def request(self, client, method, path, key_needed, body=None, extra=None, timeout=None, rid=""):
        headers = {"User-Agent": "scholarchain-eval16b/1", "Accept": "application/json", "X-Request-Id": rid, "X-Trace-Id": self.cfg["run_id"]}
        if key_needed:
            headers["Authorization"] = "Bearer " + self.cfg["key"]
        headers.update(extra or {})
        started = time.perf_counter()
        error, status, nbytes, echoed, data = client.request(method, path, headers, body, timeout)
        return error, status, nbytes, data, round((time.perf_counter() - started) * 1000, 3)

    def ask(self, client, index, question):
        cfg = self.cfg
        idem = ("ev16b-%s-%d" % (cfg["run_id"], index))[:256]
        body = json.dumps({"question": question, "output": {"includeScores": False}}).encode("utf-8")
        started_wall = time.time()
        error, status, nbytes, data, latency = self.request(
            client, "POST", "/v1/query", True, body=body, extra={"Content-Type": "application/json", "Idempotency-Key": idem},
            timeout=cfg["profile"]["limits"]["llm_request_timeout_seconds"], rid="%s-%d" % (cfg["run_id"], index))
        row = {"schema": "scholarchain.eval16b-answer.v1", "run_id": cfg["run_id"], "index": index, "question": question,
               "question_sha256": sha256_text(question), "idempotency_key": idem, "started_utc": loadgen.stamp(started_wall),
               "status": status, "outcome": loadgen.classify(status, error), "latency_ms": latency, "bytes": nbytes,
               "query_id": None, "job_id": None, "job_state": None, "answer_sha256": None, "answer_bytes": None, "answer": None}
        parsed = read_json_body(data) if 200 <= status < 300 else None
        if isinstance(parsed, dict):
            for key, field in (("queryId", "query_id"), ("jobId", "job_id")):
                if isinstance(parsed.get(key), str) and loadgen.SAFE_ID.match(parsed[key]):
                    row[field] = parsed[key]
        final = parsed
        if status == 202 and row["job_id"]:
            final = self.wait_for_job(client, row, index)
        if isinstance(final, (dict, list)):
            text = json.dumps(final, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            raw = text.encode("utf-8")
            row["answer_sha256"], row["answer_bytes"] = hashlib.sha256(raw).hexdigest(), len(raw)
            if len(raw) <= MAX_ANSWER_BYTES:
                row["answer"] = final
        if row["outcome"] == "ok" and status == 202 and row["job_state"] not in DONE_OK:
            row["outcome"] = "job_not_done"
        self.answers_file.write(loadgen.jdump(row) + "\n")
        self.answers_file.flush()
        self.rows.append(row)
        return row

    def wait_for_job(self, client, row, index):
        cfg = self.cfg
        deadline = time.monotonic() + cfg["job_wait_seconds"]
        path = "/v1/jobs/" + urllib.parse.quote(row["job_id"], safe="")
        state = None
        while time.monotonic() < deadline:
            error, status, _n, data, _ms = self.request(client, "GET", path, True, timeout=cfg["profile"]["limits"]["request_timeout_seconds"], rid="%s-%d-job" % (cfg["run_id"], index))
            parsed = read_json_body(data) if status == 200 else None
            state = str(parsed.get("state", "")) if isinstance(parsed, dict) else None
            if status != 200 or state not in IN_PROGRESS:
                break
            self.sleep(1.0)
        row["job_state"] = state
        if state in DONE_OK:
            error, status, _n, data, _ms = self.request(client, "GET", path + "/result", True, timeout=cfg["profile"]["limits"]["request_timeout_seconds"], rid="%s-%d-result" % (cfg["run_id"], index))
            if 200 <= status < 300:
                return read_json_body(data)
        return None


def run_command(args, out):
    plan = plan_state(args)
    run_id = args.run_id or "ev-%s-%s" % (loadgen.utc_now().strftime("%Y%m%dT%H%M%SZ"), os.urandom(2).hex())
    if not RUN_ID.match(run_id):
        raise UsageError("--run-id must match %s" % RUN_ID.pattern)
    url = args.base_url or os.environ.get(args.base_url_env, "")
    target = loadgen.parse_base_url(url)
    key = loadgen.read_key(args.api_key_env)
    root = loadgen.check_output_root(args.output_root)
    run_dir = os.path.join(root, "%s-%s" % (EXPERIMENT_ID, run_id))
    os.makedirs(root, mode=0o700, exist_ok=True)
    loadgen.new_dir(run_dir)
    raw_dir = os.path.join(run_dir, "raw")
    loadgen.new_dir(raw_dir)
    cfg = {"budget": plan["budget"], "profile": plan["profile"], "run_id": run_id, "key": key, "job_wait_seconds": args.job_wait_seconds}
    answers_file = loadgen.open_new_text(os.path.join(raw_dir, "answers.jsonl"))
    events_file = loadgen.open_new_text(os.path.join(raw_dir, "events.jsonl"))
    evaluator = Evaluator(cfg, answers_file, events_file)
    commit, dirty = loadgen.git_state()
    started = time.time()
    outcome, reason = "completed", ""
    print_plan(plan, out, "run")
    out.write("RUN-ID: %s\nRUN-DIR: %s\n" % (run_id, run_dir))
    client = loadgen.HttpClient(target[0], target[1], target[2], plan["profile"]["limits"]["request_timeout_seconds"])
    try:
        evaluator.event("run-start", experiment_id=EXPERIMENT_ID, commit=commit, tree_dirty=dirty, planned_answers=plan["planned_answers"])
        for index, question in enumerate(plan["questions"], 1):
            if not evaluator.charge(index):
                outcome, reason = "stopped", evaluator.stop_reason
                break
            row = evaluator.ask(client, index, question)
            if row["status"] in (401, 403):
                outcome, reason = "aborted", "auth-failure"
                break
            if not row.get("expected_refusal"):   # (evalq12 only) an expected refusal is neutral: it neither adds to nor resets the failure run
                evaluator.consecutive_failures = 0 if row["outcome"] == "ok" else evaluator.consecutive_failures + 1
            if evaluator.consecutive_failures >= args.max_consecutive_failures:
                outcome, reason = "aborted", "repeated-failures"
                break
            if index < plan["planned_answers"] and args.pause_seconds:
                time.sleep(args.pause_seconds)
    except KeyboardInterrupt:
        outcome, reason = "interrupted", "keyboard-interrupt"
    finally:
        client.close()
        evaluator.event("run-end", outcome=outcome, reason=reason, answers_charged=evaluator.charged)
        answers_file.close()
        events_file.close()
    end_state = plan["budget"].state()
    counts = {}
    for row in evaluator.rows:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    cost_report = llm_budget.cost_report(plan["profile"], evaluator.charged)
    loopback = target[1] in loadgen.LOOPBACK
    record = {
        "schema": RECORD_SCHEMA, "run_id": run_id, "experiment_id": EXPERIMENT_ID, "outcome": outcome, "outcome_reason": reason,
        "started_utc": loadgen.stamp(started), "ended_utc": loadgen.stamp(time.time()), "commit": commit, "tree_dirty": dirty,
        "questions": {"file_sha256": plan["questions_sha256"], "planned": plan["planned_answers"], "asked": len(evaluator.rows)},
        "manifest_sha256": loadgen.sha256_file(MANIFEST) if os.path.isfile(MANIFEST) else None,
        "profile_sha256": loadgen.sha256_file(args.profile),
        "target": {"scheme": target[0], "loopback": loopback, "base_url_sha256": hashlib.sha256(("%s://%s:%s" % target).encode("utf-8")).hexdigest(),
                   "host": target[1] if loopback else "withheld"},
        "api_key_env": args.api_key_env, "outcomes": dict(sorted(counts.items())),
        "llm": {"bucket": BUCKET, "answers_charged": evaluator.charged, "estimated_cost_usd": loadgen.money(loadgen.cost_per_answer(plan["profile"]) * evaluator.charged),
                "bucket_size": plan["bucket_size"], "bucket_used_at_start": plan["bucket_used"], "bucket_used_at_end": end_state["used"][BUCKET],
                "ledger_total_at_start_usd": plan["ledger_total_usd"], "ledger_total_at_end_usd": loadgen.money(end_state["usd"]),
                "allocation_sha256": plan["allocation_sha256"], "ledger_path": plan["ledger_path"], "stopped_reason": evaluator.stop_reason or None,
                "note": "estimated from pinned tokens and rates, not metered; the Anthropic console, the Voyage console and the AWS bill are the costs of record"},
        "cost_report": cost_report, "python": sys.version.split()[0],
    }
    with loadgen.open_new_text(os.path.join(raw_dir, "run-record.json")) as handle:
        handle.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
    loadgen.seal(raw_dir)
    out.write("COST-REPORT: aws=%s anthropic=%s voyage=%s combined=%s (%s)\n" % (
        cost_report["aws"]["usd"] or "not-metered", cost_report["anthropic"]["usd"], cost_report["voyage"]["usd"], cost_report["combined_usd"], cost_report["combined_scope"]))
    out.write("RESULT: %s run=%s asked=%d charged=%d reason=%s\n" % (outcome.upper(), run_id, len(evaluator.rows), evaluator.charged, reason or "-"))
    return 0 if outcome == "completed" else 4


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--questions-file", default=DEFAULT_QUESTIONS, help="one question per line (default experiments/inputs/14c/questions.txt)")
        p.add_argument("--max-answers", type=int, help="ask only the first N questions (lowers the plan; never raises it)")
        p.add_argument("--profile", default=loadgen.DEFAULT_PROFILE)
        p.add_argument("--allocation", default=llm_budget.DEFAULT_ALLOCATION)
        p.add_argument("--ledger", help="LLM ledger path (default from the profile, under ~/.scholarchain)")

    common(sub.add_parser("plan"))
    p = sub.add_parser("run")
    common(p)
    p.add_argument("--run-id")
    p.add_argument("--base-url", help="https://host[:port] of query-api (or set %s)" % DEFAULT_URL_ENV)
    p.add_argument("--base-url-env", default=DEFAULT_URL_ENV)
    p.add_argument("--api-key-env", default=DEFAULT_KEY_ENV, help="NAME of the environment variable holding the API key")
    p.add_argument("--output-root", default=loadgen.DEFAULT_OUTPUT_ROOT)
    p.add_argument("--pause-seconds", type=float, default=1.0, help="gap between questions (default 1)")
    p.add_argument("--job-wait-seconds", type=float, default=60.0, help="how long to poll a 202 job for one question (default 60)")
    p.add_argument("--max-consecutive-failures", type=int, default=3)
    return parser


def main(argv, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "plan":
            print_plan(plan_state(args), out, "plan")
            out.write("RESULT: PLAN-OK (nothing sent)\n")
            return 0
        if args.max_consecutive_failures < 1 or not 0 <= args.pause_seconds <= 60 or not 1 <= args.job_wait_seconds <= 300:
            raise UsageError("--max-consecutive-failures >= 1, 0 <= --pause-seconds <= 60 and 1 <= --job-wait-seconds <= 300 are required")
        return run_command(args, out)
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

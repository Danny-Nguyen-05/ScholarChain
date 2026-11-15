#!/usr/bin/env python3
"""Feature tests for load-tests/loadgen.py against a fake query-api on 127.0.0.1 (no AWS, no non-loopback network).

Run from the repository root:   python3 -I -m unittest discover -s load-tests/tests -v
Expected values are derived by hand from the requirement (see each test), not by calling the code under test.
"""
import collections
import contextlib
import http.server
import importlib.util
import io
import json
import os
import shutil
import stat
import tempfile
import threading
import time
import unittest
from unittest import mock


def read_text(path):
    with open(path) as handle:
        return handle.read()


def read_json(path):
    with open(path) as handle:
        return json.load(handle)


def write_json(path, document):
    with open(path, "w") as handle:
        json.dump(document, handle)


def write_text(path, text):
    with open(path, "w") as handle:
        handle.write(text)

HERE = os.path.dirname(os.path.abspath(__file__))
LOADGEN = os.path.join(os.path.dirname(HERE), "loadgen.py")
spec = importlib.util.spec_from_file_location("loadgen_under_test", LOADGEN)
loadgen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loadgen)

BUDGET = loadgen.llm_budget
KEY = "sk-test-SENTINEL-9f8e7d6c5b4a39281706"
PUBLIC = {"/healthz", "/readyz"}


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.counts = collections.Counter()
        self.inflight = 0
        self.max_inflight = 0
        self.query_inflight = 0
        self.max_query_inflight = 0
        self.delay = 0.0
        self.query_delay = 0.0
        self.mode = "ok"  # ok | 503 | leak-key
        self.public_with_auth = 0
        self.auth_ok = 0
        self.idempotency_keys = []
        self.query_bodies = []
        self.after_query = None
        self.request_headers = []
        self.async_queries = False
        self.job_polls = 0


def make_handler(state):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _send(self, status, payload, extra=None):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Request-Id", self.headers.get("X-Request-Id", "none"))
            self.end_headers()
            self.wfile.write(body)

        def _route(self, method):
            path = self.path.split("?")[0]
            template = path
            for prefix in ("/v1/graph/nodes/", "/v1/evidence/", "/v1/jobs/"):
                if path.startswith(prefix):
                    template = prefix + ("{id}/neighbors" if path.endswith("/neighbors") else "{id}")
            with state.lock:
                state.counts[(method, template)] += 1
                state.inflight += 1
                state.max_inflight = max(state.max_inflight, state.inflight)
                state.request_headers.append(dict(self.headers))
            is_query = method == "POST" and path == "/v1/query"
            if is_query:
                with state.lock:
                    state.query_inflight += 1
                    state.max_query_inflight = max(state.max_query_inflight, state.query_inflight)
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                time.sleep(state.query_delay if is_query else state.delay)
                has_auth = self.headers.get("Authorization") == "Bearer " + KEY
                if path in PUBLIC and self.headers.get("Authorization"):
                    with state.lock:
                        state.public_with_auth += 1
                if state.mode == "503":
                    return self._send(503, {"error": "NOT_READY", "message": "down", "traceId": "t", "retryable": True})
                if state.mode == "leak-key":
                    return self._send(500, {"error": "INTERNAL", "message": "oops " + KEY})
                if path in PUBLIC:
                    return self._send(200, {"status": "alive" if path == "/healthz" else "ready"})
                if not has_auth:
                    return self._send(401, {"error": "UNAUTHORIZED", "message": "bad key", "traceId": "t", "retryable": False})
                with state.lock:
                    state.auth_ok += 1
                if is_query:
                    with state.lock:
                        state.idempotency_keys.append(self.headers.get("Idempotency-Key"))
                        state.query_bodies.append(body)
                        n = state.counts[("POST", "/v1/query")]
                    if state.after_query:
                        state.after_query(n)
                    if state.async_queries:
                        return self._send(202, {"queryId": "q-%d" % n, "jobId": "job-%064d" % n, "status": "QUEUED", "statusUrl": "/v1/jobs/x"})
                    return self._send(200, {"queryId": "q-%d" % n, "mode": "synchronous", "answer": {"summary": "x"}, "claims": [], "links": {}})
                if path.startswith("/v1/jobs/"):
                    with state.lock:
                        state.job_polls += 1
                        polls = state.job_polls
                    return self._send(200, {"state": "RUNNING" if polls == 1 else "SUCCEEDED"})
                return self._send(200, {"ok": True})
            finally:
                with state.lock:
                    state.inflight -= 1
                    if is_query:
                        state.query_inflight -= 1

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

    return Handler


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 256
    daemon_threads = True


class LoadgenCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lg-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.state = State()
        self.server = Server(("127.0.0.1", 0), make_handler(self.state))
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        env = mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": KEY, "SCHOLARCHAIN_LOAD_BASE_URL": "http://127.0.0.1:%d" % self.port})
        env.start()
        self.addCleanup(env.stop)
        self.node_ids = os.path.join(self.tmp, "nodes.txt")
        with open(self.node_ids, "w") as handle:
            handle.write("researcher:aaa\nresearcher:bbb\nwork:ccc/ddd\n")
        self.questions = os.path.join(self.tmp, "questions.txt")
        with open(self.questions, "w") as handle:
            handle.write("Synthetic question one\nSynthetic question two\n")
        self.ledger = os.path.join(self.tmp, "ledger", "haiku.jsonl")
        self.out_root = os.path.join(self.tmp, "runs")

    # --- helpers
    def go(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = loadgen.main(argv, out=out)
        return rc, out.getvalue(), err.getvalue()

    def run_load(self, *extra, run_id=None, experiment="t-exp", nodes=True):
        argv = ["run", "--output-root", self.out_root, "--experiment-id", experiment, "--run-id", run_id or "run-%d" % time.time_ns(), "--pause-seconds", "0"]
        if nodes:
            argv += ["--node-ids-file", self.node_ids]
        return self.go(argv + list(extra))

    def run_dir(self, experiment="t-exp"):
        dirs = [d for d in os.listdir(self.out_root) if d.startswith(experiment + "-")]
        self.assertEqual(len(dirs), 1, dirs)
        return os.path.join(self.out_root, dirs[0])

    def requests(self, run_dir):
        with open(os.path.join(run_dir, "raw", "requests.jsonl")) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def record(self, run_dir):
        with open(os.path.join(run_dir, "raw", "run-record.json")) as handle:
            return json.load(handle)

    def events(self, run_dir):
        with open(os.path.join(run_dir, "raw", "events.jsonl")) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def budget_cli(self, *argv, ledger=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = BUDGET.main(["--ledger", ledger or self.ledger] + list(argv), out=out)
        return rc, out.getvalue(), err.getvalue()

    def init_ledger(self, ledger=None):
        self.assertEqual(self.budget_cli("init", ledger=ledger)[0], 0)

    def ledger_lines(self):
        with open(self.ledger) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def llm_args(self, remaining=None, extra=()):
        rem = ["--remaining-cap-usd", remaining] if remaining is not None else []
        return ["--llm"] + rem + ["--ledger", self.ledger, "--questions-file", self.questions] + list(extra)

    # --- 1. default is non-LLM only
    def test_default_run_sends_no_v1_query(self):
        rc, out, err = self.run_load("--levels", "1,5", "--duration-seconds", "1")
        self.assertEqual(rc, 0, err + out)
        self.assertEqual(self.state.counts[("POST", "/v1/query")], 0)
        self.assertTrue(sum(self.state.counts.values()) > 0)
        run_dir = self.run_dir()
        rows = self.requests(run_dir)
        self.assertTrue(rows)
        self.assertTrue(all(r["route"] != "query" and not r["llm"] for r in rows))
        self.assertIn("LLM: disabled", out)
        self.assertFalse(self.record(run_dir)["llm"]["enabled"])
        self.assertEqual(self.record(run_dir)["llm"]["answers_sent"], 0)
        # the default mix (graph routes need node IDs, evidence needs evidence IDs): the dropped route is reported, not silent
        self.assertEqual([d["route"] for d in self.record(run_dir)["routes_dropped"]], ["evidence"])

    def test_graph_routes_are_dropped_and_reported_without_node_ids(self):
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "1", nodes=False)
        self.assertEqual(rc, 0, err)
        dropped = sorted(d["route"] for d in self.record(self.run_dir())["routes_dropped"])
        self.assertEqual(dropped, ["evidence", "graph_neighbors", "graph_node"])
        self.assertIn("ROUTE-DROPPED: graph_node", out)
        self.assertEqual({r["route"] for r in self.requests(self.run_dir())} - {"healthz", "readyz", "metrics"}, set())

    # --- 2. pinned cost and the budget table (hand-derived)
    def test_cost_per_answer_and_default_budget_table(self):
        profile = loadgen.load_profile(loadgen.DEFAULT_PROFILE)
        # (1950 + 5200) = 7150 in x 0.10 + (260 + 1040) = 1300 out x 0.50 per million = 715 + 650 micro-USD = 0.001365
        self.assertEqual(loadgen.money(loadgen.cost_per_answer(profile)), "0.001365")
        rc, out, err = self.go(["plan", "--llm", "--ledger", self.make_ledger(), "--questions-file", self.questions])
        self.assertEqual(rc, 0, err)
        # 10 + 15 + 20 + 15 = 60 answers x 0.001365 = 0.0819 (the 15b bucket holds exactly 60)
        self.assertIn("LLM-BUDGET level=1 phase=level-1 answers=10 est_cost_usd=0.013650", out)
        self.assertIn("LLM-BUDGET level=5 phase=level-5 answers=15 est_cost_usd=0.020475", out)
        self.assertIn("LLM-BUDGET level=25 phase=level-25 answers=20 est_cost_usd=0.027300", out)
        self.assertIn("LLM-BUDGET level=50 phase=level-50 answers=15 est_cost_usd=0.020475", out)
        self.assertIn("LLM-TOTAL answers=60 planned_cost_usd=0.081900 bucket=15b bucket_size=60 bucket_used=0 bucket_remaining=60", out)

    def make_ledger(self):
        self.init_ledger()
        return self.ledger

    # --- 3. refusals before anything is sent
    def test_refuses_when_planned_cost_exceeds_remaining_cap(self):
        self.init_ledger()
        rc, out, err = self.run_load("--levels", "1,5,25,50", "--duration-seconds", "1", *self.llm_args(remaining="0.08"))
        self.assertEqual(rc, 3)
        self.assertIn("60 planned answers", err)
        self.assertIn("exceeds the remaining cap", err)
        self.assertEqual(sum(self.state.counts.values()), 0)
        self.assertFalse(os.path.exists(self.out_root))

    def test_accepts_planned_cost_equal_to_remaining_cap(self):
        self.init_ledger()
        rc, out, err = self.go(["plan", "--llm", "--remaining-cap-usd", "0.081900", "--ledger", self.ledger, "--questions-file", self.questions])
        self.assertEqual(rc, 0, err)

    def test_refuses_when_ledger_plus_planned_exceeds_shared_cap(self):
        self.init_ledger()
        self.assertEqual(self.budget_cli("adjust", "--usd", "1.27", "--source", "aws-bill")[0], 0)
        # the 15b bucket is untouched (60 free) but 1.27 + 0.0819 = 1.3519 > 1.33
        rc, out, err = self.run_load("--levels", "1,5,25,50", "--duration-seconds", "1", *self.llm_args())
        self.assertEqual(rc, 3)
        self.assertIn("ledger total 1.270000", err)
        self.assertIn("exceeds the shared cap 1.330000", err)
        self.assertEqual(sum(self.state.counts.values()), 0)
        # 1.20 + 0.0819 = 1.2819 <= 1.33 passes (60 answers x 0.001365 = 0.0819)
        other = os.path.join(self.tmp, "ledger2.jsonl")
        self.init_ledger(other)
        self.budget_cli("adjust", "--usd", "1.20", "--source", "aws-bill", ledger=other)
        rc, out, err = self.go(["plan", "--llm", "--ledger", other, "--questions-file", self.questions])
        self.assertEqual(rc, 0, err)

    def test_refuses_when_the_planned_answers_exceed_the_15b_bucket(self):
        self.init_ledger()
        self.assertEqual(self.budget_cli("reserve", "--bucket", "15b", "--answers", "1")[0], 0)  # 59 left
        rc, out, err = self.run_load("--levels", "1,5,25,50", "--duration-seconds", "1", *self.llm_args())
        self.assertEqual(rc, 3)
        self.assertIn("bucket 15b: 60 planned answers exceed the 59 remaining (size 60, used 1)", err)
        self.assertEqual(sum(self.state.counts.values()), 0)
        # 10 + 15 + 20 = 45 for three levels still fit
        rc, out, err = self.go(["plan", "--levels", "1,5,25", "--llm", "--ledger", self.ledger, "--questions-file", self.questions])
        self.assertEqual(rc, 0, err)

    def test_other_llm_refusals(self):
        base = ["--levels", "1", "--duration-seconds", "1"]
        # absent ledger is never read as zero
        rc, _, err = self.run_load(*base, *self.llm_args())
        self.assertEqual(rc, 3)
        self.assertIn("does not exist", err)
        self.init_ledger()
        # --remaining-cap-usd is optional (the bucket and the shared cap always apply)
        self.assertEqual(self.go(["plan", "--llm", "--ledger", self.ledger, "--questions-file", self.questions])[0], 0)
        # remaining cap above the pinned shared cap, or not a number
        self.assertEqual(self.run_load(*base, *self.llm_args(remaining="2.00"))[0], 3)
        self.assertEqual(self.run_load(*base, *self.llm_args(remaining="nan"))[0], 3)
        self.assertEqual(self.run_load(*base, *self.llm_args(remaining="-1"))[0], 3)
        # no questions file
        rc, _, err = self.run_load(*base, "--llm", "--ledger", self.ledger)
        self.assertEqual(rc, 3)
        # zero budget with --llm
        rc, _, err = self.run_load(*base, *self.llm_args(extra=["--llm-answers", "1=0"]))
        self.assertEqual(rc, 3)
        self.assertIn("budget for these phases is 0", err)
        # a corrupt ledger line is refused, never skipped
        with open(self.ledger, "a") as handle:
            handle.write("not json\n")
        rc, _, err = self.run_load(*base, *self.llm_args())
        self.assertEqual(rc, 3)
        self.assertIn("not a valid entry", err)
        self.assertEqual(sum(self.state.counts.values()), 0)

    def test_llm_needs_the_key(self):
        self.init_ledger()
        with mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": ""}):
            rc, _, err = self.run_load("--levels", "1", "--duration-seconds", "1", *self.llm_args())
        self.assertEqual(rc, 3)
        self.assertIn("holds no API key", err)
        self.assertNotIn(KEY, err)

    # --- 4. LLM happy path and the ledger
    def test_llm_answers_are_counted_in_the_ledger_before_sending(self):
        self.init_ledger()
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "2", "--max-requests", "5000", *self.llm_args(extra=["--llm-answers", "1=4"]))
        self.assertEqual(rc, 0, err + out)
        self.assertEqual(self.state.counts[("POST", "/v1/query")], 4)
        entries = [e for e in self.ledger_lines() if e["event"] == "answer"]
        self.assertEqual(len(entries), 4)
        self.assertTrue(all(e["unit_usd"] == "0.001365" and e["bucket"] == "15b" and e["answers"] == 1 for e in entries))
        record = self.record(self.run_dir())
        self.assertEqual(record["llm"]["answers_sent"], 4)
        self.assertEqual(record["llm"]["estimated_cost_usd"], "0.005460")  # 4 x 0.001365
        self.assertEqual(record["llm"]["ledger_total_at_end_usd"], "0.005460")
        # cost report: AWS, Anthropic and Voyage separately, then the combined total (AWS is never estimated by the generator)
        report = record["cost_report"]
        self.assertTrue({"aws", "anthropic", "voyage", "combined_usd"} <= set(report))  # the file is key-sorted; the COST-REPORT line below keeps the order
        self.assertIsNone(report["aws"]["usd"])
        self.assertEqual((report["anthropic"]["usd"], report["anthropic"]["answers"], report["anthropic"]["model"]), ("0.005460", 4, "claude-haiku-5-5"))
        self.assertEqual((report["voyage"]["usd"], report["voyage"]["model"]), ("0.000000", "voyage-4-lite"))
        self.assertEqual(report["combined_usd"], "0.005460")
        self.assertIn("COST-REPORT: aws=not-metered anthropic=0.005460 voyage=0.000000 combined=0.005460", out)
        self.assertEqual((record["llm"]["bucket"], record["llm"]["bucket_used_at_start"], record["llm"]["bucket_used_at_end"]), ("15b", 0, 4))
        keys = self.state.idempotency_keys
        self.assertEqual(len(set(keys)), 4)  # a fresh Idempotency-Key per answer
        self.assertEqual(json.loads(self.state.query_bodies[0])["question"], "Synthetic question one")
        llm_rows = [r for r in self.requests(self.run_dir()) if r["route"] == "query"]
        self.assertEqual(len(llm_rows), 4)
        self.assertTrue(all(r["llm"] and r["method"] == "POST" and r["query_id"].startswith("q-") for r in llm_rows))

    def test_a_202_answer_is_followed_through_the_job_status(self):
        self.init_ledger()
        self.state.async_queries = True
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "2", "--max-requests", "100000", *self.llm_args(extra=["--llm-answers", "1=1"]))
        self.assertEqual(rc, 0, err)
        rows = self.requests(self.run_dir())
        query = [r for r in rows if r["route"] == "query"]
        self.assertEqual([r["status"] for r in query], [202])
        self.assertEqual(query[0]["job_id"], "job-%064d" % 1)
        polls = [r for r in rows if r["route"] == "job_status"]
        self.assertEqual(len(polls), 2)  # RUNNING, then SUCCEEDED, then it stops polling
        self.assertEqual(self.state.counts[("POST", "/v1/query")], 1)  # a poll never makes a second answer

    def test_mid_run_stop_when_the_total_cap_is_reached(self):
        self.init_ledger()

        def other_consumer(n):
            # after the 3rd answer another consumer posts USD 1.325 of observed spend against the shared cap
            if n == 3:
                self.budget_cli("adjust", "--usd", "1.325", "--source", "aws-bill")

        self.state.after_query = other_consumer
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "3", "--max-requests", "100000", *self.llm_args(extra=["--llm-answers", "1=10"]))
        self.assertEqual(rc, 0, err + out)
        # 3 x 0.001365 + 1.325 = 1.329095 <= 1.33, but a 4th answer makes 1.33046 > 1.33, so it is refused and every later one too
        self.assertEqual(self.state.counts[("POST", "/v1/query")], 3)
        record = self.record(self.run_dir())
        self.assertEqual(record["llm"]["answers_sent"], 3)
        self.assertEqual(record["llm"]["stopped_reason"], "ledger-cap")
        self.assertEqual(len([e for e in self.ledger_lines() if e["event"] == "answer"]), 3)
        stops = [e for e in self.events(self.run_dir()) if e["event"] == "llm-cap-reached"]
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["answers_sent"], 3)
        self.assertGreater(len([r for r in self.requests(self.run_dir()) if r["route"] != "query"]), 3)  # non-LLM load continued

    def test_mid_run_stop_when_the_15b_bucket_is_exhausted(self):
        self.init_ledger()

        def other_consumer(n):
            # after the 3rd answer something else uses the rest of bucket 15b (57 of 60); the total cap is nowhere near reached
            if n == 3:
                self.assertEqual(self.budget_cli("reserve", "--bucket", "15b", "--answers", "57")[0], 0)

        self.state.after_query = other_consumer
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "3", "--max-requests", "100000", *self.llm_args(extra=["--llm-answers", "1=10"]))
        self.assertEqual(rc, 0, err + out)
        self.assertEqual(self.state.counts[("POST", "/v1/query")], 3)
        record = self.record(self.run_dir())
        self.assertEqual(record["llm"]["stopped_reason"], "bucket-cap")
        self.assertEqual(record["llm"]["bucket_used_at_end"], 60)
        stops = [e for e in self.events(self.run_dir()) if e["event"] == "llm-cap-reached"]
        self.assertEqual((len(stops), stops[0]["bucket"]), (1, "15b"))

    def test_other_buckets_are_untouched_by_the_load_run(self):
        self.init_ledger()
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "2", "--max-requests", "5000", *self.llm_args(extra=["--llm-answers", "1=3"]))
        self.assertEqual(rc, 0, err)
        status = self.budget_cli("status")[1]
        self.assertIn("BUCKET 14c size=10 used=0 remaining=10", status)
        self.assertIn("BUCKET 15b size=60 used=3 remaining=57", status)

    def test_remaining_cap_usd_still_refuses_at_the_start(self):
        self.init_ledger()
        # 18 answers x 0.001365 = 0.02457 fits in 0.025, a 19th (0.025935) does not
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "3", "--max-requests", "100000", *self.llm_args(remaining="0.025", extra=["--llm-answers", "1=19"]))
        self.assertEqual(rc, 3)  # planned 19 x 0.001365 = 0.025935 > 0.025 is refused at the start
        self.assertIn("exceeds the remaining cap", err)

    def test_llm_inflight_is_capped_by_the_profile(self):
        self.init_ledger()
        profile = read_json(loadgen.DEFAULT_PROFILE)
        profile["limits"]["llm_max_inflight"] = 1
        path = os.path.join(self.tmp, "profile.json")
        write_json(path, profile)
        self.state.query_delay = 0.9
        rc, out, err = self.run_load("--profile", path, "--levels", "5", "--duration-seconds", "2", "--max-requests", "100000", *self.llm_args(extra=["--llm-answers", "5=4"]))
        self.assertEqual(rc, 0, err + out)
        self.assertEqual(self.state.max_query_inflight, 1)
        self.assertGreaterEqual(self.state.counts[("POST", "/v1/query")], 1)

    # --- 5. concurrency levels
    def test_concurrency_levels_are_honored(self):
        self.state.delay = 0.05
        for level in (1, 5, 25, 50):
            self.state.max_inflight = 0
            rc, out, err = self.run_load("--levels", str(level), "--duration-seconds", "1.5", experiment="lvl-%d" % level)
            self.assertEqual(rc, 0, err + out)
            self.assertEqual(self.state.max_inflight, level, "level %d" % level)
            rows = self.requests(self.run_dir("lvl-%d" % level))
            self.assertEqual({r["level"] for r in rows}, {level})
            self.assertEqual(len({r["worker"] for r in rows}), level)
            phase = self.record(self.run_dir("lvl-%d" % level))["phases"][0]
            self.assertEqual(phase["level"], level)

    def test_all_four_levels_in_order_with_run_ids(self):
        rc, out, err = self.run_load("--duration-seconds", "0.5", run_id="four-levels-1")
        self.assertEqual(rc, 0, err + out)
        rows = self.requests(self.run_dir())
        order = []
        for r in rows:
            if not order or order[-1] != r["level"]:
                order.append(r["level"])
        self.assertEqual(order, [1, 5, 25, 50])
        self.assertTrue(all(r["run_id"] == "four-levels-1" and r["experiment_id"] == "t-exp" and r["request_id"].startswith("four-levels-1-") for r in rows))
        self.assertEqual(len({r["request_id"] for r in rows}), len(rows))
        # the service echoed our X-Request-Id
        self.assertTrue(all(r["echoed_request_id"] == r["request_id"] for r in rows))
        self.assertTrue(all(r["status"] == 200 for r in rows))

    def test_max_requests_cap_is_honored(self):
        rc, out, err = self.run_load("--levels", "5", "--duration-seconds", "10", "--max-requests", "40")
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.requests(self.run_dir())), 40)

    def test_pacing_limits_the_request_rate(self):
        rc, out, err = self.run_load("--levels", "5", "--duration-seconds", "2", "--max-rps", "50", "--max-requests", "100000")
        self.assertEqual(rc, 0, err)
        # 50 requests per second for 2 s is 100 requests; allow the first request of each of the 5 workers to go out at once
        count = len(self.requests(self.run_dir()))
        self.assertTrue(80 <= count <= 110, count)

    def test_a_fast_target_still_gets_every_planned_answer(self):
        self.init_ledger()
        # the request cap (200) is exhausted in a few milliseconds, long before the 30 s duration; the answers are scheduled by cap share too
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "30", "--max-requests", "200", *self.llm_args(extra=["--llm-answers", "1=5"]))
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.state.counts[("POST", "/v1/query")], 5)
        self.assertEqual(len(self.requests(self.run_dir())), 200)

    # --- 6. the key never leaks
    def test_api_key_is_never_printed_or_stored(self):
        self.init_ledger()
        rc, out, err = self.run_load("--levels", "1,5", "--duration-seconds", "1", "--max-requests", "5000", *self.llm_args(extra=["--llm-answers", "1=2,5=2"]))
        self.assertEqual(rc, 0, err + out)
        self.assertGreater(self.state.auth_ok, 0)  # the key was really sent to the routes that need it
        self.assertEqual(self.state.public_with_auth, 0)  # and withheld from /healthz and /readyz
        self.assert_no_key(out, err)
        # an erroring server that echoes the key in its body
        self.state.mode = "leak-key"
        rc, out2, err2 = self.run_load("--levels", "1", "--duration-seconds", "1", experiment="leak-exp")
        self.assertEqual(rc, 4)
        self.assert_no_key(out2, err2)

    def assert_no_key(self, *streams):
        for text in streams:
            self.assertNotIn(KEY, text)
        for base in (self.out_root, os.path.dirname(self.ledger)):
            for root, _, files in os.walk(base):
                for name in files:
                    with open(os.path.join(root, name), "rb") as handle:
                        self.assertNotIn(KEY.encode(), handle.read(), name)
        # the environment variable NAME is recorded, never its value
        for d in os.listdir(self.out_root):
            record = read_json(os.path.join(self.out_root, d, "raw", "run-record.json"))
            self.assertEqual(record["api_key_env"], "SCHOLARCHAIN_LOAD_API_KEY")

    # --- 7. abort rules
    def test_aborts_on_repeated_5xx(self):
        self.state.mode = "503"
        started = time.time()
        rc, out, err = self.run_load("--levels", "1,5,25,50", "--duration-seconds", "20")
        self.assertEqual(rc, 4)
        self.assertLess(time.time() - started, 10)
        record = self.record(self.run_dir())
        self.assertEqual(record["outcome"], "aborted")
        self.assertEqual(record["outcome_reason"], "repeated-5xx-or-transport-failures")
        # the abort fires at the pinned threshold: 20 failures within the last 40 requests (level 1 is one worker, so exactly 20)
        self.assertEqual(self.state.counts[("GET", "/healthz")] + sum(v for (m, p), v in self.state.counts.items() if p != "/healthz"), 20)
        skipped = [e for e in self.events(self.run_dir()) if e["event"] == "phase-skipped"]
        self.assertEqual([e["phase"] for e in skipped], ["level-5", "level-25", "level-50"])  # --pause-seconds 0 adds no pause phases

    def test_aborts_on_repeated_auth_failures(self):
        with mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": "wrong-key-value"}):
            rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "20")
        self.assertEqual(rc, 4)
        self.assertEqual(self.record(self.run_dir())["outcome_reason"], "repeated-auth-failures")
        self.assertNotIn("wrong-key-value", out + err)

    def test_transport_errors_abort_too(self):
        self.server.shutdown()
        self.server.server_close()
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "20", nodes=False)
        self.assertEqual(rc, 4)
        self.assertEqual(self.record(self.run_dir())["outcome_reason"], "repeated-5xx-or-transport-failures")

    # --- 8. target rules
    def test_url_rules(self):
        parse = loadgen.parse_base_url
        self.assertEqual(parse("https://api.example.org"), ("https", "api.example.org", None))
        self.assertEqual(parse("http://127.0.0.1:8080"), ("http", "127.0.0.1", 8080))
        self.assertEqual(parse("http://localhost:9"), ("http", "localhost", 9))
        for bad in ("http://api.example.org", "http://10.0.0.5:80", "ftp://x", "https://u:p@api.example.org", "https://api.example.org/v1", "https://api.example.org?x=1", "https://api.example.org#f", "", "https://"):
            with self.assertRaises(loadgen.Refused, msg=bad):
                parse(bad)

    def test_plain_http_to_a_remote_host_sends_nothing(self):
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "1", "--base-url", "http://203.0.113.9:8080")
        self.assertEqual(rc, 3)
        self.assertIn("plain http", err)
        self.assertEqual(sum(self.state.counts.values()), 0)

    def test_output_root_inside_the_repo_must_be_under_target(self):
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "1", "--output-root", os.path.join(loadgen.REPO, "docs", "oops"))
        self.assertEqual(rc, 3)
        self.assertIn("target/", err)
        self.assertFalse(os.path.exists(os.path.join(loadgen.REPO, "docs", "oops")))
        loadgen.check_output_root(os.path.join(loadgen.REPO, "target", "experiment-runs"))  # the git-ignored default is accepted

    # --- 9. raw evidence
    def test_raw_files_are_sealed_and_never_reused(self):
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "1", run_id="sealed-run-1")
        self.assertEqual(rc, 0, err)
        run_dir = self.run_dir()
        raw = os.path.join(run_dir, "raw")
        self.assertEqual(sorted(os.listdir(raw)), ["events.jsonl", "raw.sha256", "requests.jsonl", "run-record.json"])
        for name in os.listdir(raw):
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(raw, name)).st_mode), 0o444)
        loadgen.verify_raw(raw)
        listing = read_text(os.path.join(raw, "raw.sha256"))
        self.assertIn("  requests.jsonl", listing)
        # the same run id again is refused
        rc2, _, err2 = self.run_load("--levels", "1", "--duration-seconds", "1", run_id="sealed-run-1")
        self.assertEqual(rc2, 3)
        self.assertIn("already exists", err2)
        # a later change to a raw file is detected by summarize
        os.chmod(os.path.join(raw, "requests.jsonl"), 0o644)
        with open(os.path.join(raw, "requests.jsonl"), "a") as handle:
            handle.write("{}\n")
        rc3, _, err3 = self.go(["summarize", run_dir])
        self.assertEqual(rc3, 3)
        self.assertIn("modified after collection", err3)

    def test_run_record_has_provenance_and_withholds_the_host(self):
        rc, out, err = self.run_load("--levels", "1", "--duration-seconds", "1")
        record = self.record(self.run_dir())
        for field in ("run_id", "experiment_id", "commit", "started_utc", "ended_utc", "outcome", "phases", "totals", "profile", "llm", "python"):
            self.assertIn(field, record)
        self.assertEqual(len(record["profile"]["sha256"]), 64)
        self.assertEqual(len(record["target"]["base_url_sha256"]), 64)
        self.assertTrue(record["target"]["loopback"])
        self.assertRegex(record["started_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")

    def test_percentiles_are_nearest_rank_and_hand_derived(self):
        pct = loadgen.percentile
        self.assertEqual([pct(list(range(1, 101)), p) for p in (50, 95, 99)], [50, 95, 99])
        self.assertEqual([pct([10, 20, 30, 40], p) for p in (50, 95, 99)], [20, 40, 40])  # ranks 2, 4, 4
        self.assertIsNone(pct([], 50))
        run_dir = os.path.join(self.tmp, "synthetic-run")
        raw = os.path.join(run_dir, "raw")
        os.makedirs(raw)
        rows = [{"run_id": "s", "phase": "level-5", "level": 5, "route": "healthz", "status": 200, "outcome": "ok", "latency_ms": float(i), "started_utc": "2026-11-20T10:00:%02d.000Z" % (i % 60)} for i in range(1, 101)]
        rows.append({"run_id": "s", "phase": "level-5", "level": 5, "route": "healthz", "status": 503, "outcome": "server_error", "latency_ms": 500.0, "started_utc": "2026-11-20T10:01:00.000Z"})
        write_text(os.path.join(raw, "requests.jsonl"), "".join(json.dumps(r) + "\n" for r in rows))
        events = [{"event": "phase-end", "type": "load", "phase": "level-5", "level": 5, "started_utc": "2026-11-20T10:00:00.000Z", "ended_utc": "2026-11-20T10:01:40.000Z"}]
        write_text(os.path.join(raw, "events.jsonl"), "".join(json.dumps(e) + "\n" for e in events))
        loadgen.seal(raw)
        summary = loadgen.summarize(run_dir)
        phase = summary["phases"][0]
        self.assertEqual(phase["requests"], 101)
        self.assertEqual(phase["latency_ms_2xx"], {"p50": 50.0, "p95": 95.0, "p99": 99.0, "n": 100})
        # all 101 responses sorted: 100 values 1..100 plus 500; ranks ceil(50.5)=51, ceil(95.95)=96, ceil(99.99)=100
        self.assertEqual(phase["latency_ms_all_responses"], {"p50": 51.0, "p95": 96.0, "p99": 100.0, "n": 101})
        self.assertEqual(phase["throughput_rps"], 1.01)  # 101 requests over the 100 s phase
        self.assertEqual(phase["error_rate_5xx_or_transport"], round(1 / 101, 6))
        for name in ("summary.json", "summary.csv", "timeline.csv"):
            self.assertTrue(os.path.exists(os.path.join(run_dir, "derived", name)))

    # --- 10. manifest-driven phases
    def test_manifest_phases_run_in_order_and_observe_sends_nothing(self):
        manifest = {
            "schema": "scholarchain.load-experiment-manifest.v1", "id": "mf-test", "description": "d", "region": "us-east-2", "target": {"service": "query-api"},
            "phases": [{"name": "baseline", "type": "load", "level": 1, "duration_seconds": 0.5}, {"name": "quiet", "type": "observe", "duration_seconds": 0.5},
                       {"name": "hold-5", "type": "load", "level": 5, "duration_seconds": 0.5}],
            "llm": {"default_enabled": False}, "metrics_to_collect": [{"source": "AWS/ECS", "metric": "CPUUtilization"}], "approval_record_path": "docs/x.md",
        }
        path = os.path.join(self.tmp, "m.json")
        write_json(path, manifest)
        rc, out, err = self.run_load("--manifest", path, experiment="mf-test")
        self.assertEqual(rc, 0, err + out)
        record = self.record(self.run_dir("mf-test"))
        self.assertEqual([p["phase"] for p in record["phases"]], ["baseline", "quiet", "hold-5"])
        self.assertEqual(len(record["manifest_sha256"]), 64)
        quiet = record["phases"][1]
        rows = self.requests(self.run_dir("mf-test"))
        self.assertTrue(all(not (quiet["started_utc"] < r["started_utc"] < quiet["ended_utc"]) for r in rows))
        # an unknown key in a phase is rejected
        manifest["phases"][0]["bogus"] = 1
        write_json(path, manifest)
        self.assertEqual(self.go(["validate-manifest", path])[0], 3)
        # LLM can never be switched on from a manifest
        manifest["phases"][0].pop("bogus")
        manifest["llm"] = {"default_enabled": True}
        write_json(path, manifest)
        self.assertEqual(self.go(["validate-manifest", path])[0], 3)

    def test_phase_duration_and_level_limits(self):
        self.assertEqual(self.run_load("--levels", "1", "--duration-seconds", "99999")[0], 3)
        self.assertEqual(self.run_load("--levels", "51", "--duration-seconds", "1")[0], 3)
        self.assertEqual(self.run_load("--levels", "0", "--duration-seconds", "1")[0], 3)
        self.assertEqual(sum(self.state.counts.values()), 0)


if __name__ == "__main__":
    unittest.main()

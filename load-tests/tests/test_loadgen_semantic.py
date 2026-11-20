#!/usr/bin/env python3
"""Feature tests for the P42 semantic route of load-tests/loadgen.py against a fake query-api on 127.0.0.1 (no AWS, no non-loopback network, no real key).

Run from the repository root:   python3 -I -m unittest discover -s load-tests/tests -v
Expected values are derived by hand from the requirement (session-2 plan rows P42 and P35): the route body and header, the required per-level request
limits 600 / 3,000 / 15,000 / 30,000 / 150,000 (198,600 in total), the warm-up pass, and the separate count of 429 replies.
"""
import collections
import contextlib
import csv
import hashlib
import http.server
import importlib.util
import io
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
LOADTESTS = os.path.dirname(HERE)
REPO = os.path.dirname(LOADTESTS)
spec = importlib.util.spec_from_file_location("loadgen_semantic_under_test", os.path.join(LOADTESTS, "loadgen.py"))
loadgen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loadgen)

KEY = "fake-semantic-key-SENTINEL-0a1b2c3d4e5f"  # a fake: never a real credential
COMMITTED_MANIFEST = os.path.join(REPO, "experiments", "manifests", "15b-ecs-scaling-semantic.json")
COMMITTED_QUESTIONS = os.path.join(REPO, "experiments", "inputs", "15b", "semantic-questions.txt")


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.semantic = []  # (headers, body bytes) of every POST /v1/semantic/retrieve
        self.other = collections.Counter()
        self.limit_every = 0  # every Nth semantic request is answered 429 (0 = never)
        self.limit_all = False
        self.limited = 0
        self.limited_delay = 0.0
        self.fail_semantic_numbers = set()  # semantic request numbers (1-based) answered with 503


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
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            with state.lock:
                state.other[self.path.split("?")[0]] += 1
            if self.path in ("/healthz", "/readyz"):
                return self._send(200, {"status": "ok"})
            if self.headers.get("Authorization") != "Bearer " + KEY:
                return self._send(401, {"error": "UNAUTHORIZED"})
            self._send(200, {"ok": True})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            if self.path != "/v1/semantic/retrieve":
                return self._send(404, {"error": "NOT_FOUND"})
            if self.headers.get("Authorization") != "Bearer " + KEY:
                return self._send(401, {"error": "UNAUTHORIZED"})
            with state.lock:
                state.semantic.append((dict(self.headers), body))
                number = len(state.semantic)
                limited = state.limit_all or (state.limit_every and number % state.limit_every == 0)
                if limited:
                    state.limited += 1
            if number in state.fail_semantic_numbers:
                return self._send(503, {"error": "NOT_READY"})
            if limited:
                time.sleep(state.limited_delay)
                return self._send(429, {"error": "RATE_LIMITED", "retryable": True}, {"Retry-After": "1"})
            self._send(200, {"hits": [], "model": {}})

    return Handler


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 256
    daemon_threads = True


def sha256_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class SemanticCase(unittest.TestCase):
    COUNT = 100

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lg-sem-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.state = State()
        self.server = Server(("127.0.0.1", 0), make_handler(self.state))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        env = mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": KEY, "SCHOLARCHAIN_LOAD_BASE_URL": "http://127.0.0.1:%d" % self.server.server_address[1]})
        env.start()
        self.addCleanup(env.stop)
        self.questions_path = os.path.join(self.tmp, "questions.txt")
        self.questions = ["topic phrase %03d %s" % (i, "alpha" if i % 2 else "beta") for i in range(self.COUNT)]
        self.write_questions(self.questions)
        self.out_root = os.path.join(self.tmp, "runs")

    # --- helpers
    def write_questions(self, questions):
        with open(self.questions_path, "w") as handle:
            handle.write("".join(q + "\n" for q in questions))

    def phases(self, warmup=None, level1=20, quick=0.4):
        phases = []
        if warmup is not False:
            phases.append({"name": "warmup", "type": "warmup", "level": 1, "duration_seconds": 30, "max_requests": warmup or self.COUNT, "purpose": "t"})
        phases.append({"name": "baseline-1", "type": "load", "level": 1, "duration_seconds": quick, "llm_answers": 0, "max_requests": level1, "purpose": "t"})
        phases.append({"name": "level-5", "type": "load", "level": 5, "duration_seconds": quick, "llm_answers": 0, "max_requests": 60, "purpose": "t"})
        phases.append({"name": "cooldown-observe", "type": "observe", "duration_seconds": 5, "purpose": "t"})
        return phases

    def manifest(self, phases=None, top_k=7, sha=None, count=None):
        return {
            "schema": "scholarchain.load-experiment-manifest.v1", "id": "sem-test", "description": "d", "region": "us-east-2", "target": {"service": "query-api"},
            "phases": phases or self.phases(), "llm": {"default_enabled": False}, "metrics_to_collect": [{"source": "AWS/ECS", "metric": "CPUUtilization"}],
            "approval_record_path": "docs/x.md",
            "semantic": {"route": "semantic", "top_k": top_k, "questions_file": "q.txt", "questions_sha256": sha or sha256_file(self.questions_path),
                         "questions_count": count or self.COUNT},
        }

    def write_manifest(self, doc, name="m.json"):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as handle:
            json.dump(doc, handle)
        return path

    def go(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = loadgen.main(argv, out=out)
        return rc, out.getvalue(), err.getvalue()

    def run_semantic(self, manifest_path, *extra, run_id=None, questions=True):
        argv = ["run", "--manifest", manifest_path, "--output-root", self.out_root, "--run-id", run_id or "r-%d" % time.time_ns(), "--observe-seconds", "0.2"]
        if questions:
            argv += ["--questions-file", self.questions_path]
        return self.go(argv + list(extra))

    def run_dir(self):
        dirs = os.listdir(self.out_root)
        self.assertEqual(len(dirs), 1, dirs)
        return os.path.join(self.out_root, dirs[0])

    def rows(self, run_dir=None):
        with open(os.path.join(run_dir or self.run_dir(), "raw", "requests.jsonl")) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def record(self):
        with open(os.path.join(self.run_dir(), "raw", "run-record.json")) as handle:
            return json.load(handle)

    def summary(self):
        with open(os.path.join(self.run_dir(), "derived", "summary.json")) as handle:
            return json.load(handle)

    # --- 1. the route: method, path, header, body
    def test_semantic_request_is_a_post_with_the_key_header_and_the_two_field_body(self):
        rc, out, err = self.run_semantic(self.write_manifest(self.manifest(top_k=7)))
        self.assertEqual(rc, 0, err + out)
        self.assertGreater(len(self.state.semantic), self.COUNT)
        for headers, body in self.state.semantic:
            self.assertEqual(headers["Authorization"], "Bearer " + KEY)
            self.assertEqual(headers["Content-Type"], "application/json")
            parsed = json.loads(body.decode("utf-8"))
            self.assertEqual(sorted(parsed), ["question", "topK"])  # nothing else: the P40 route rejects unknown keys
            self.assertEqual(parsed["topK"], 7)
            self.assertIn(parsed["question"], self.questions)
        # the question text is never written to the raw rows (only its index in the fixed file)
        with open(os.path.join(self.run_dir(), "raw", "requests.jsonl")) as handle:
            raw_text = handle.read()
        self.assertNotIn("topic phrase", raw_text)
        semantic_rows = [r for r in self.rows() if r["route"] == "semantic"]
        self.assertTrue(all(r["method"] == "POST" and r["path_template"] == "/v1/semantic/retrieve" and 0 <= r["question_index"] < self.COUNT for r in semantic_rows))

    def test_the_key_comes_from_the_environment_and_is_never_printed_or_stored(self):
        rc, out, err = self.run_semantic(self.write_manifest(self.manifest()))
        self.assertEqual(rc, 0, err + out)
        for text in (out, err):
            self.assertNotIn(KEY, text)
        for root, _, files in os.walk(self.out_root):
            for name in files:
                with open(os.path.join(root, name), "rb") as handle:
                    self.assertNotIn(KEY.encode(), handle.read(), name)
        self.assertEqual(self.record()["api_key_env"], "SCHOLARCHAIN_LOAD_API_KEY")
        # a different variable name is honoured; an unset one sends nothing and names only the variable
        with mock.patch.dict(os.environ, {"MY_OTHER_KEY": KEY}):
            self.assertEqual(self.run_semantic(self.write_manifest(self.manifest()), "--api-key-env", "MY_OTHER_KEY", run_id="r-other")[0], 0)
        before = len(self.state.semantic)
        with mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": ""}):
            rc, out, err = self.run_semantic(self.write_manifest(self.manifest()), run_id="r-nokey")
        self.assertEqual(rc, 3)
        self.assertIn("SCHOLARCHAIN_LOAD_API_KEY", err)
        self.assertEqual(len(self.state.semantic), before)

    def test_a_wrong_key_aborts_without_printing_it(self):
        with mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": "wrong-key-value-XYZ"}):
            rc, out, err = self.run_semantic(self.write_manifest(self.manifest()))
        self.assertEqual(rc, 4)
        self.assertNotIn("wrong-key-value-XYZ", out + err)
        self.assertEqual(self.record()["outcome_reason"], "repeated-auth-failures")

    # --- 2. weights favour semantic
    def test_route_weights_favour_semantic(self):
        profile = loadgen.load_profile(loadgen.DEFAULT_PROFILE)
        route = profile["routes"]["semantic"]
        self.assertEqual((route["method"], route["path"], route["auth"], route["llm"]), ("POST", "/v1/semantic/retrieve", True, False))
        others = sum(r["weight"] for n, r in profile["routes"].items() if n != "semantic" and not r["llm"])
        self.assertEqual(others, 14)  # healthz 2 + readyz 1 + metrics 1 + node 4 + neighbors 4 + evidence 2
        self.assertGreater(route["weight"], others)
        self.assertGreater(route["weight"] / (route["weight"] + 4.0), 0.9)  # with no ID files: healthz, readyz, metrics only
        # a real run: most requests are semantic
        rc, out, err = self.run_semantic(self.write_manifest(self.manifest(top_k=3)))
        self.assertEqual(rc, 0, err)
        measured = [r for r in self.rows() if r["phase"] != "warmup"]
        share = sum(1 for r in measured if r["route"] == "semantic") / float(len(measured))
        self.assertGreater(share, 0.7, share)
        self.assertEqual({r["route"] for r in self.rows()} - {"semantic", "healthz", "readyz", "metrics"}, set())

    def test_an_ordinary_run_neither_uses_nor_reports_the_semantic_route(self):
        rc, out, err = self.go(["run", "--output-root", self.out_root, "--run-id", "plain-run", "--levels", "1", "--duration-seconds", "0.5", "--pause-seconds", "0"])
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.state.semantic), 0)
        self.assertEqual(self.record()["routes_dropped"], [{"route": "graph_node", "reason": "no node_ids supplied"}, {"route": "graph_neighbors", "reason": "no node_ids supplied"},
                                                            {"route": "evidence", "reason": "no evidence_ids supplied"}])
        self.assertIsNone(self.record()["semantic"])

    # --- 3. the required per-level limits
    def test_the_required_limits_are_pinned_and_sum_to_198600(self):
        self.assertEqual(loadgen.SEMANTIC_LEVEL_CAPS, {1: 600, 5: 3000, 25: 15000, 50: 30000})
        self.assertEqual(loadgen.SEMANTIC_HOLD_CAP, 150000)
        self.assertEqual(sum(loadgen.SEMANTIC_LEVEL_CAPS.values()) + loadgen.SEMANTIC_HOLD_CAP, 198600)
        self.assertEqual(loadgen.SEMANTIC_RAMP_TOTAL, 198600)
        self.assertEqual(loadgen.SEMANTIC_WARMUP_MAX, 200)

    def full_phases(self, **over):
        caps = {"baseline-1": 600, "level-5": 3000, "level-25": 15000, "level-50": 30000, "hold-50": 150000}
        caps.update(over)
        levels = {"baseline-1": 1, "level-5": 5, "level-25": 25, "level-50": 50, "hold-50": 50}
        phases = [{"name": "warmup", "type": "warmup", "level": 1, "duration_seconds": 600, "max_requests": 200, "purpose": "t"}]
        phases += [{"name": n, "type": "load", "level": levels[n], "duration_seconds": 60, "llm_answers": 0, "max_requests": caps[n], "purpose": "t"} for n in caps]
        phases.append({"name": "cooldown-observe", "type": "observe", "duration_seconds": 1800, "purpose": "t"})
        return phases

    def test_the_manifest_at_the_required_limits_is_accepted_by_validate_plan_and_the_sum_is_198600(self):
        phases = self.full_phases()
        self.assertEqual(sum(p["max_requests"] for p in phases if p["type"] == "load"), 198600)
        path = self.write_manifest(self.manifest(phases=phases))
        self.assertEqual(self.go(["validate-manifest", path])[0], 0)
        rc, out, err = self.go(["plan", "--manifest", path, "--questions-file", self.questions_path])
        self.assertEqual(rc, 0, err)
        self.assertIn("ramp_cap_total=198600", out)
        self.assertIn("PHASE hold-50: load level=50 duration=60s max_requests=150000", out)

    def test_any_limit_above_the_required_value_is_refused_everywhere_and_nothing_is_sent(self):
        for name, over in (("baseline-1", 601), ("level-5", 3001), ("level-25", 15001), ("level-50", 30001), ("hold-50", 150001)):
            path = self.write_manifest(self.manifest(phases=self.full_phases(**{name: over})))
            rc, out, err = self.go(["validate-manifest", path])
            self.assertEqual(rc, 3, name)
            self.assertIn("exceeds the required limit", err, name)
            self.assertEqual(self.go(["plan", "--manifest", path, "--questions-file", self.questions_path])[0], 3, name)
            rc, out, err = self.run_semantic(path, run_id="r-%s" % name)
            self.assertEqual(rc, 3, name)
        self.assertEqual(len(self.state.semantic), 0)
        self.assertFalse(os.path.exists(self.out_root) and os.listdir(self.out_root))

    def test_phase_shapes_that_could_exceed_the_total_are_refused(self):
        base = self.full_phases()
        hold2 = dict(base[5], name="hold-50-b")  # a second hold: 348,600 requests in all
        cases = {
            "a second hold": base[:6] + [hold2] + base[6:],
            "a level that has no limit": [dict(p, level=10) if p["name"] == "level-5" else p for p in base],
            "a hold below level 50": [dict(p, level=25) if p["name"] == "hold-50" else p for p in base],
            "a missing max_requests": [{k: v for k, v in p.items() if k != "max_requests"} if p["name"] == "level-50" else p for p in base],
        }
        for label, phases in cases.items():
            path = self.write_manifest(self.manifest(phases=phases))
            self.assertEqual(self.go(["validate-manifest", path])[0], 3, label)

    def test_lowering_a_limit_is_allowed(self):
        path = self.write_manifest(self.manifest(phases=self.full_phases(**{"hold-50": 1000, "level-50": 100})))
        self.assertEqual(self.go(["validate-manifest", path])[0], 0)

    def test_the_semantic_block_needs_valid_fields_and_no_llm(self):
        doc = self.manifest(phases=self.full_phases())
        for label, change in (("top_k over the public limit", lambda d: d["semantic"].update(top_k=21)), ("top_k zero", lambda d: d["semantic"].update(top_k=0)),
                              ("bad sha", lambda d: d["semantic"].update(questions_sha256="abc")), ("too few questions", lambda d: d["semantic"].update(questions_count=99)),
                              ("too many questions", lambda d: d["semantic"].update(questions_count=201)), ("unknown key", lambda d: d["semantic"].update(bogus=1)),
                              ("llm answers", lambda d: d["phases"][1].update(llm_answers=1)), ("wrong route", lambda d: d["semantic"].update(route="query"))):
            mutated = json.loads(json.dumps(doc))
            change(mutated)
            self.assertEqual(self.go(["validate-manifest", self.write_manifest(mutated)])[0], 3, label)
        self.assertEqual(self.go(["validate-manifest", self.write_manifest(doc)])[0], 0)

    # --- 4. the warm-up pass
    def test_warmup_sends_each_distinct_question_once_in_file_order_before_the_ramp(self):
        rc, out, err = self.run_semantic(self.write_manifest(self.manifest()))
        self.assertEqual(rc, 0, err + out)
        rows = self.rows()
        warm = [r for r in rows if r["phase"] == "warmup"]
        self.assertEqual(len(warm), self.COUNT)  # one request per distinct question, no more
        self.assertEqual([r["question_index"] for r in warm], list(range(self.COUNT)))
        self.assertTrue(all(r["route"] == "semantic" and r["level"] == 1 and r["worker"] == 0 for r in warm))
        sent = [json.loads(body.decode())["question"] for _, body in self.state.semantic[:self.COUNT]]
        self.assertEqual(sent, self.questions)  # the server saw each question exactly once, in order
        self.assertEqual(rows[:self.COUNT], warm)  # nothing else was sent before the warm-up ended
        record = self.record()
        self.assertEqual([p["phase"] for p in record["phases"]][:2], ["warmup", "baseline-1"])
        self.assertEqual((record["phases"][0]["type"], record["phases"][0]["requests"], record["phases"][0]["questions_sent"]), ("warmup", self.COUNT, self.COUNT))
        # its figures are a phase of their own: the level-1 baseline holds none of them
        by_phase = {p["phase"]: p for p in self.summary()["phases"]}
        self.assertEqual(by_phase["warmup"]["requests"], self.COUNT)
        self.assertLessEqual(by_phase["baseline-1"]["requests"], 20)

    def test_warmup_is_not_retried_and_stays_within_its_limit(self):
        self.state.fail_semantic_numbers = {2}  # the second warm-up question gets a 503
        rc, out, err = self.run_semantic(self.write_manifest(self.manifest()))
        self.assertEqual(rc, 0, err)
        warm = [r for r in self.rows() if r["phase"] == "warmup"]
        self.assertEqual(len(warm), self.COUNT)
        self.assertEqual([r["status"] for r in warm].count(503), 1)
        self.assertEqual(len({r["question_index"] for r in warm}), self.COUNT)

    def test_warmup_limits_and_placement_are_enforced(self):
        # above 200, below the question count, not first, not level 1, twice, or without the semantic block: refused
        for label, phases in (
                ("201 requests", self.phases(warmup=201)),
                ("below the question count", self.phases(warmup=99)),
                ("no warm-up", self.phases(warmup=False)),
                ("not first", [self.phases()[1], self.phases()[0]] + self.phases()[2:]),
                ("level 5", [dict(self.phases()[0], level=5)] + self.phases()[1:]),
                ("two warm-ups", [self.phases()[0], dict(self.phases()[0], name="warmup-b")] + self.phases()[1:])):
            self.assertEqual(self.go(["validate-manifest", self.write_manifest(self.manifest(phases=phases))])[0], 3, label)
        plain = self.manifest()
        plain.pop("semantic")
        self.assertEqual(self.go(["validate-manifest", self.write_manifest(plain)])[0], 3)

    def test_the_questions_file_is_fixed_distinct_and_required(self):
        path = self.write_manifest(self.manifest())
        self.assertEqual(self.run_semantic(path, questions=False)[0], 3)  # no --questions-file
        self.write_questions(self.questions[:-1] + ["topic phrase 000 beta"])  # a duplicate and a changed file: refused on the pinned sha256
        rc, out, err = self.run_semantic(path, run_id="r-changed")
        self.assertEqual(rc, 3)
        self.assertIn("sha256 mismatch", err)
        dup = self.questions[:-1] + [self.questions[0].upper()]  # same count, a case-insensitive duplicate, with its own pin
        self.write_questions(dup)
        rc, out, err = self.run_semantic(self.write_manifest(self.manifest(sha=sha256_file(self.questions_path)), "m2.json"), run_id="r-dup")
        self.assertEqual(rc, 3)
        self.assertIn("distinct", err)
        self.assertEqual(len(self.state.semantic), 0)
        # a semantic manifest cannot be combined with --llm (the questions file is the semantic set)
        self.write_questions(self.questions)
        rc, out, err = self.run_semantic(path, "--llm", "--ledger", os.path.join(self.tmp, "ledger.jsonl"), run_id="r-llm")
        self.assertEqual(rc, 3)
        self.assertIn("--llm", err)

    # --- 5. 429 replies are separate
    def test_429s_are_counted_per_level_and_excluded_from_latency_throughput_and_success_rate(self):
        self.state.limit_every = 4
        self.state.limited_delay = 0.25  # a 429 is slow here, so any leak into the latency figures is visible
        rc, out, err = self.run_semantic(self.write_manifest(self.manifest()))
        self.assertEqual(rc, 0, err + out)  # a 429 is not a failure: the run completes
        rows = self.rows()
        self.assertEqual(sum(1 for r in rows if r["status"] == 429), self.state.limited)
        self.assertGreater(self.state.limited, 0)
        phases = {p["phase"]: p for p in self.summary()["phases"]}
        total_429 = 0
        for name, phase in phases.items():
            group = [r for r in rows if r["phase"] == name]
            n429 = sum(1 for r in group if r["status"] == 429)
            ok = sum(1 for r in group if r["status"] == 200)
            total_429 += n429
            self.assertEqual(phase["rate_limited_429"], n429, name)
            self.assertEqual(phase["requests"], len(group), name)  # a 429 still counts toward the request limit
            self.assertEqual(phase["successful_requests"], ok, name)
            self.assertEqual(phase["served_requests"], len(group) - n429, name)
            self.assertEqual(phase["outcomes"].get("throttled", 0), n429, name)
            self.assertEqual(phase["success_rps"], round(ok / phase["seconds"], 3), name)
            self.assertEqual(phase["throughput_rps"], round((len(group) - n429) / phase["seconds"], 3), name)
            self.assertEqual(phase["latency_ms_all_responses"]["n"], len(group) - n429, name)
            self.assertEqual(phase["latency_ms_2xx"]["n"], ok, name)
            self.assertLess(phase["latency_ms_all_responses"]["p99"], 200.0, name)  # the 250 ms replies are not in the latency
            self.assertEqual(phase["error_rate_5xx_or_transport"], 0.0, name)
            self.assertEqual(phase["client_error_rate"], 0.0, name)  # a 429 is not a client error figure either
            self.assertEqual(phase["routes"]["semantic"]["rate_limited_429"], n429, name)
        self.assertGreater(phases["baseline-1"]["rate_limited_429"] + phases["warmup"]["rate_limited_429"], 0)
        # the run record and the console report them per level, separately
        record = self.record()
        self.assertEqual(record["totals"]["rate_limited_429"], total_429)
        self.assertEqual({p["phase"]: p["rate_limited_429"] for p in record["phases"] if p["type"] != "observe"}, {n: p["rate_limited_429"] for n, p in phases.items()})
        for name, phase in phases.items():
            self.assertIn("RATE-LIMITED-429: phase=%s level=%d count=%d of %d requests" % (name, phase["level"], phase["rate_limited_429"], phase["requests"]), out)
        # summary.csv and timeline.csv carry the separate columns; the minute rows add up to the same counts
        with open(os.path.join(self.run_dir(), "derived", "summary.csv")) as handle:
            table = list(csv.DictReader(handle))
        self.assertEqual({r["phase"]: int(r["rate_limited_429"]) for r in table}, {n: p["rate_limited_429"] for n, p in phases.items()})
        with open(os.path.join(self.run_dir(), "derived", "timeline.csv")) as handle:
            minutes = list(csv.DictReader(handle))
        self.assertEqual(sum(int(r["rate_limited_429"]) for r in minutes), total_429)
        self.assertEqual(sum(int(r["successful_requests"]) for r in minutes), sum(1 for r in rows if r["status"] == 200))

    def test_a_limit_counts_429s_and_a_run_of_nothing_but_429s_still_completes(self):
        self.state.limit_all = True
        rc, out, err = self.run_semantic(self.write_manifest(self.manifest(phases=self.phases(level1=15))))
        self.assertEqual(rc, 0, err + out)
        baseline = [p for p in self.summary()["phases"] if p["phase"] == "baseline-1"][0]
        self.assertEqual(baseline["requests"], 15)  # the 429s counted toward the phase limit of 15
        semantic = baseline["routes"]["semantic"]  # (healthz, readyz and metrics are not limited by the fake, as on the real route)
        self.assertEqual((semantic["rate_limited_429"], semantic["successful_requests"], semantic["served_requests"]), (semantic["requests"], 0, 0))
        self.assertGreater(semantic["requests"], 0)
        self.assertIsNone(semantic["latency_ms_all_responses"]["p50"])
        self.assertEqual(semantic["throughput_rps"], 0.0)
        self.assertIsNone(semantic["error_rate_5xx_or_transport"])
        self.assertEqual(baseline["rate_limited_429"], semantic["requests"])
        self.assertEqual(self.record()["outcome"], "completed")

    def test_summarize_figures_are_hand_derived_with_429_rows(self):
        run_dir = os.path.join(self.tmp, "synthetic")
        raw = os.path.join(run_dir, "raw")
        os.makedirs(raw)
        rows = []
        for i in range(10):  # ten 2xx replies, 10..100 ms, two per second over five seconds
            rows.append({"run_id": "s", "phase": "level-5", "level": 5, "route": "semantic", "status": 200, "outcome": "ok", "latency_ms": 10.0 * (i + 1),
                         "started_utc": "2026-11-20T10:00:%02d.%03dZ" % (i // 2, (i % 2) * 400)})
        for i in range(5):  # five slow 429 replies
            rows.append({"run_id": "s", "phase": "level-5", "level": 5, "route": "semantic", "status": 429, "outcome": "throttled", "latency_ms": 900.0,
                         "started_utc": "2026-11-20T10:00:%02d.700Z" % i})
        with open(os.path.join(raw, "requests.jsonl"), "w") as handle:
            handle.write("".join(json.dumps(r) + "\n" for r in rows))
        with open(os.path.join(raw, "events.jsonl"), "w") as handle:
            handle.write(json.dumps({"event": "phase-end", "type": "load", "phase": "level-5", "level": 5, "started_utc": "2026-11-20T10:00:00.000Z", "ended_utc": "2026-11-20T10:00:10.000Z"}) + "\n")
        loadgen.seal(raw)
        phase = loadgen.summarize(run_dir)["phases"][0]
        self.assertEqual((phase["requests"], phase["rate_limited_429"], phase["served_requests"], phase["successful_requests"]), (15, 5, 10, 10))
        self.assertEqual(phase["success_rps"], 1.0)  # 10 successful over the 10 s window
        self.assertEqual(phase["throughput_rps"], 1.0)  # 429s excluded: 10 / 10 s, not 15 / 10 s
        self.assertEqual(phase["latency_ms_all_responses"], {"p50": 50.0, "p95": 100.0, "p99": 100.0, "n": 10})  # nearest rank over 10..100, no 900
        self.assertEqual(phase["latency_ms_2xx"], {"p50": 50.0, "p95": 100.0, "p99": 100.0, "n": 10})
        self.assertEqual(phase["peak_success_rps_1s"], 2)
        self.assertEqual(phase["error_rate_5xx_or_transport"], 0.0)

    # --- 6. the committed manifest and its questions file
    def test_the_committed_semantic_manifest_has_the_required_totals_and_a_fixed_questions_file(self):
        with open(COMMITTED_MANIFEST) as handle:
            doc = json.load(handle)
        load = [p for p in doc["phases"] if p["type"] == "load"]
        self.assertEqual([(p["name"], p["level"], p["max_requests"]) for p in load],
                         [("baseline-1", 1, 600), ("level-5", 5, 3000), ("level-25", 25, 15000), ("level-50", 50, 30000), ("hold-50", 50, 150000)])
        self.assertEqual(sum(p["max_requests"] for p in load), 198600)
        warm = [p for p in doc["phases"] if p["type"] == "warmup"]
        self.assertEqual(len(warm), 1)
        self.assertEqual((doc["phases"][0]["name"], warm[0]["level"]), ("warmup", 1))
        self.assertLessEqual(warm[0]["max_requests"], 200)
        self.assertGreaterEqual(warm[0]["max_requests"], doc["semantic"]["questions_count"])
        observe = sum(p["duration_seconds"] for p in doc["phases"] if p["type"] == "observe")
        self.assertGreaterEqual(observe, 25 * 60)
        self.assertEqual([p["name"] for p in doc["phases"]][-1], "cooldown-observe")  # the quiet window is last
        self.assertEqual(self.go(["validate-manifest", COMMITTED_MANIFEST])[0], 0)
        with open(COMMITTED_QUESTIONS) as handle:
            lines = [x for x in handle.read().split("\n") if x]
        self.assertEqual(len(lines), doc["semantic"]["questions_count"])
        self.assertTrue(100 <= len(lines) <= 200)
        self.assertEqual(len({x.casefold() for x in lines}), len(lines))
        self.assertEqual(sha256_file(COMMITTED_QUESTIONS), doc["semantic"]["questions_sha256"])
        self.assertTrue(all(len(x) <= 1000 for x in lines))
        rc, out, err = self.go(["plan", "--manifest", COMMITTED_MANIFEST, "--questions-file", COMMITTED_QUESTIONS])
        self.assertEqual(rc, 0, err)
        self.assertIn("RESULT: PLAN-OK", out)

    def test_observe_seconds_can_only_lower_a_quiet_window(self):
        path = self.write_manifest(self.manifest(phases=self.full_phases()))
        rc, out, err = self.go(["plan", "--manifest", path, "--questions-file", self.questions_path, "--observe-seconds", "30"])
        self.assertEqual(rc, 0, err)
        self.assertIn("PHASE cooldown-observe: observe (no requests) 30s", out)
        rc, out, err = self.go(["plan", "--manifest", path, "--questions-file", self.questions_path, "--observe-seconds", "99999"])
        self.assertIn("PHASE cooldown-observe: observe (no requests) 1800s", out)

    # --- the R-b quiet window cannot be shortened against a remote target (review 2, finding 2)
    def run_with_flag(self, base_url, observe="30"):
        path = self.write_manifest(self.manifest(phases=self.full_phases()))
        argv = ["run", "--manifest", path, "--output-root", self.out_root, "--run-id", "r-%d" % time.time_ns(), "--questions-file", self.questions_path,
                "--base-url", base_url]
        if observe is not None:
            argv += ["--observe-seconds", observe]
        return self.go(argv)

    def test_observe_seconds_is_refused_for_a_non_loopback_target_and_nothing_is_sent(self):
        for url in ("https://api.example.org", "https://api.example.org:8443", "https://10.0.0.5"):
            with mock.patch("socket.create_connection", side_effect=AssertionError("a connection was attempted")) as connect, \
                    mock.patch("socket.getaddrinfo", side_effect=AssertionError("a lookup was attempted")) as lookup:
                rc, out, err = self.run_with_flag(url)
            self.assertEqual(rc, 3, (url, err))
            self.assertIn("REFUSED: --observe-seconds is refused for a non-loopback target", err)
            self.assertIn("R-b quiet window", err)
            self.assertIn("drop the flag", err)
            self.assertIn("Nothing was sent", err)
            self.assertNotIn("RESULT", out)
            connect.assert_not_called()
            lookup.assert_not_called()
            self.assertEqual(len(self.state.semantic), 0)
            self.assertFalse(os.path.exists(self.out_root))  # no run directory was created either
        self.assertNotIn(KEY, err)

    def test_observe_seconds_is_refused_even_when_it_would_not_shorten_a_window(self):
        rc, out, err = self.run_with_flag("https://api.example.org", observe="99999")
        self.assertEqual(rc, 3)
        self.assertIn("--observe-seconds is refused for a non-loopback target", err)

    def test_observe_seconds_is_still_allowed_on_127_0_0_1_and_localhost(self):
        port = self.server.server_address[1]
        phases = self.phases()
        path = self.write_manifest(self.manifest(phases=phases))
        for host in ("127.0.0.1", "localhost"):
            out_root = os.path.join(self.tmp, "runs-" + host)
            argv = ["run", "--manifest", path, "--output-root", out_root, "--run-id", "r-" + host, "--questions-file", self.questions_path,
                    "--base-url", "http://%s:%d" % (host, port), "--observe-seconds", "0.2"]
            rc, out, err = self.go(argv)
            self.assertEqual(rc, 0, (host, err + out))
            self.assertNotIn("non-loopback", err)
            with open(os.path.join(out_root, os.listdir(out_root)[0], "raw", "run-record.json")) as handle:
                record = json.load(handle)
            self.assertTrue(record["target"]["loopback"])
            self.assertEqual(record["observe_seconds_override"], 0.2)

    def test_without_the_flag_the_manifest_windows_are_unchanged(self):
        path = self.write_manifest(self.manifest(phases=self.full_phases()))
        rc, out, err = self.go(["plan", "--manifest", path, "--questions-file", self.questions_path])
        self.assertEqual(rc, 0, err)
        self.assertIn("PHASE cooldown-observe: observe (no requests) 1800s", out)
        # the committed manifest keeps its 1800 s quiet window
        with open(COMMITTED_MANIFEST) as handle:
            doc = json.load(handle)
        self.assertEqual([p["duration_seconds"] for p in doc["phases"] if p["type"] == "observe"], [1800])


if __name__ == "__main__":
    unittest.main()

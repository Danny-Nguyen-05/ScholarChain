#!/usr/bin/env python3
"""Feature tests for load-tests/eval16b.py, the 16B live-evaluation command, against a fake query-api on 127.0.0.1 and fake ledgers.

Run from the repository root:   python3 -I -m unittest discover -s load-tests/tests -v
No AWS, Anthropic or Voyage call and no non-loopback network. Expected values are derived by hand from the requirement:
bucket 16b holds 80 answers (experiments/manifests/llm-allocation.json; 40 until the user decision of 2026-11-21, option A); one answer costs USD 0.001365 (see test_loadgen.py),
so the 40 committed questions cost 40 x 0.001365 = 0.054600 and 3 answers cost 0.004095.
"""
import contextlib
import http.server
import importlib.util
import io
import json
import os
import shutil
import socket
import stat
import tempfile
import threading
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
LOAD_TESTS = os.path.dirname(HERE)
REPO = os.path.dirname(LOAD_TESTS)
spec = importlib.util.spec_from_file_location("eval16b_under_test", os.path.join(LOAD_TESTS, "eval16b.py"))
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
BUDGET = ev.llm_budget
KEY = "TESTKEY-SENTINEL-1a2b3c4d5e6f708192a3"
REAL_QUESTIONS = os.path.join(REPO, "experiments", "inputs", "14c", "questions.txt")


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.posts = []          # (idempotency key, body bytes, authorization header)
        self.mode = "ok"         # ok | 401 | 503-leak | async
        self.after_post = None
        self.job_polls = 0
        self.other = []


def make_handler(state):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _send(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            with state.lock:
                state.posts.append((self.headers.get("Idempotency-Key"), body, self.headers.get("Authorization")))
                n = len(state.posts)
            if state.after_post:
                state.after_post(n)
            if state.mode == "401" or self.headers.get("Authorization") != "Bearer " + KEY:
                return self._send(401, {"error": "UNAUTHORIZED"})
            if state.mode == "503-leak":
                return self._send(503, {"error": "NOT_READY", "message": "echo " + KEY})
            if state.mode == "async":
                return self._send(202, {"queryId": "q-%d" % n, "jobId": "job-%d" % n, "status": "QUEUED"})
            return self._send(200, {"queryId": "q-%d" % n, "answer": {"summary": "a%d" % n}, "claims": []})

        def do_GET(self):
            with state.lock:
                state.other.append((self.path, self.headers.get("Authorization")))
            if self.path.endswith("/result"):
                return self._send(200, {"queryId": "q-r", "answer": {"summary": "from-job"}, "claims": []})
            if self.path.startswith("/v1/jobs/"):
                with state.lock:
                    state.job_polls += 1
                    polls = state.job_polls
                return self._send(200, {"state": "RUNNING" if polls == 1 else "SUCCEEDED"})
            return self._send(404, {"error": "NOT_FOUND"})

    return Handler


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True


class Eval16bCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ev16b-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.state = State()
        self.server = Server(("127.0.0.1", 0), make_handler(self.state))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        env = mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": KEY, "SCHOLARCHAIN_LOAD_BASE_URL": "http://127.0.0.1:%d" % self.server.server_address[1]})
        env.start()
        self.addCleanup(env.stop)
        self.ledger = os.path.join(self.tmp, "ledger", "haiku.jsonl")
        self.out_root = os.path.join(self.tmp, "runs")
        self.questions = self.write_questions(3)

    def write_questions(self, n, name="q.txt"):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as handle:
            handle.write("".join("Synthetic question %d?\n" % i for i in range(1, n + 1)))
        return path

    def budget(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = BUDGET.main(["--ledger", self.ledger] + list(argv), out=out)
        return rc, out.getvalue() + err.getvalue()

    def init_ledger(self):
        self.assertEqual(self.budget("init")[0], 0)

    def ledger_lines(self):
        with open(self.ledger) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def go(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = ev.main(argv, out=out)
        return rc, out.getvalue(), err.getvalue()

    def plan(self, *extra, questions=None):
        return self.go(["plan", "--questions-file", questions or self.questions, "--ledger", self.ledger] + list(extra))

    def run_eval(self, *extra, questions=None, run_id="ev-test-1"):
        return self.go(["run", "--questions-file", questions or self.questions, "--ledger", self.ledger, "--output-root", self.out_root,
                        "--run-id", run_id, "--pause-seconds", "0"] + list(extra))

    def raw(self, run_id="ev-test-1"):
        return os.path.join(self.out_root, "16b-live-evaluation-" + run_id, "raw")

    def answers(self, run_id="ev-test-1"):
        with open(os.path.join(self.raw(run_id), "answers.jsonl")) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def events(self, run_id="ev-test-1"):
        with open(os.path.join(self.raw(run_id), "events.jsonl")) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def record(self, run_id="ev-test-1"):
        with open(os.path.join(self.raw(run_id), "run-record.json")) as handle:
            return json.load(handle)

    # --- plan / dry run: no network, no ledger write
    def test_plan_makes_no_network_call_and_writes_nothing(self):
        self.init_ledger()
        before = self.ledger_lines()

        def no_network(*a, **k):
            raise AssertionError("plan must not open a network connection")

        env = {k: v for k, v in os.environ.items() if k not in ("SCHOLARCHAIN_LOAD_API_KEY", "SCHOLARCHAIN_LOAD_BASE_URL")}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(socket.socket, "connect", no_network), \
                mock.patch.object(socket, "create_connection", no_network), mock.patch.object(socket, "getaddrinfo", no_network):
            rc, out, err = self.plan(questions=REAL_QUESTIONS)
        self.assertEqual(rc, 0, err)
        # the committed question file holds 40 questions (half of the 80-answer bucket 16b), 40 x 0.001365 = 0.0546
        self.assertIn("QUESTIONS: 40 from the questions file", out)
        self.assertIn("BUCKET 16b size=80 used=0 remaining=80", out)
        self.assertIn("PLANNED: answers=40 estimated_usd=0.054600", out)
        self.assertIn("NETWORK: none", out)
        self.assertIn("RESULT: PLAN-OK (nothing sent)", out)
        self.assertEqual(self.ledger_lines(), before)
        self.assertEqual(self.state.posts, [])
        self.assertFalse(os.path.exists(self.out_root))

    def test_plan_refuses_more_questions_than_the_bucket(self):
        self.init_ledger()
        rc, out, err = self.plan(questions=self.write_questions(81))
        self.assertEqual(rc, 3)
        self.assertIn("81 questions to ask exceed the 80 remaining answers", err)
        self.assertEqual(len(self.ledger_lines()), 1)

    def test_run_refuses_more_than_the_bucket_before_sending_or_charging(self):
        self.init_ledger()
        rc, out, err = self.run_eval(questions=self.write_questions(81))
        self.assertEqual(rc, 3)
        self.assertEqual(self.state.posts, [])
        self.assertEqual(len(self.ledger_lines()), 1)  # only the init line
        self.assertFalse(os.path.exists(self.out_root))

    def test_remaining_answers_account_for_earlier_use(self):
        self.init_ledger()
        self.assertEqual(self.budget("reserve", "--bucket", "16b", "--answers", "5")[0], 0)
        rc, out, err = self.plan(questions=self.write_questions(76))
        self.assertEqual(rc, 3)
        self.assertIn("76 questions to ask exceed the 75 remaining answers (size 80, used 5)", err)
        rc, out, err = self.plan("--max-answers", "75", questions=self.write_questions(76))
        self.assertEqual(rc, 0, err)
        self.assertIn("PLANNED: answers=75", out)

    def test_max_answers_only_lowers(self):
        self.init_ledger()
        rc, out, err = self.plan("--max-answers", "2")
        self.assertEqual(rc, 0, err)
        self.assertIn("PLANNED: answers=2 estimated_usd=0.002730", out)
        rc, out, err = self.plan("--max-answers", "0")
        self.assertEqual(rc, 3)

    def test_plan_and_run_refuse_when_the_shared_cap_would_be_passed(self):
        # spend of USD 1.30 seen outside the buckets (adjust) + 40 answers x 0.001365 = 0.0546 -> 1.3546 > the shared cap 1.33; the bucket itself is empty
        self.init_ledger()
        self.assertEqual(self.budget("adjust", "--usd", "1.30", "--source", "test")[0], 0)
        questions = self.write_questions(40)
        rc, out, err = self.plan(questions=questions)
        self.assertEqual(rc, 3)
        self.assertIn("ledger total 1.300000 + planned 0.054600 USD exceeds the shared cap 1.330000 USD", err)
        before = self.ledger_lines()
        rc, out, err = self.run_eval(questions=questions)
        self.assertEqual(rc, 3)
        self.assertEqual(self.state.posts, [])
        self.assertEqual(self.ledger_lines(), before)
        # 1.30 + 22 x 0.001365 = 1.33003 > 1.33, but 21 answers = 1.328665 fit
        rc, out, err = self.plan("--max-answers", "22", questions=questions)
        self.assertEqual(rc, 3)
        rc, out, err = self.plan("--max-answers", "21", questions=questions)
        self.assertEqual(rc, 0, err)

    def test_absent_ledger_is_refused_not_read_as_zero(self):
        rc, out, err = self.plan()
        self.assertEqual(rc, 3)
        self.assertIn("does not exist", err)

    def test_duplicate_questions_are_refused(self):
        self.init_ledger()
        path = os.path.join(self.tmp, "dup.txt")
        with open(path, "w") as handle:
            handle.write("Same question?\nSame question?\n")
        rc, out, err = self.plan(questions=path)
        self.assertEqual(rc, 3)

    def test_run_without_key_or_url_is_refused_before_any_work(self):
        self.init_ledger()
        with mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": ""}):
            rc, out, err = self.run_eval()
        self.assertEqual(rc, 3)
        self.assertIn("holds no API key", err)
        self.assertEqual(len(self.ledger_lines()), 1)
        self.assertFalse(os.path.exists(self.out_root))

    # --- run
    def test_run_asks_each_question_once_and_charges_bucket_16b(self):
        self.init_ledger()
        rc, out, err = self.run_eval()
        self.assertEqual(rc, 0, err + out)
        self.assertEqual(len(self.state.posts), 3)
        for n, (idem, body, auth) in enumerate(self.state.posts, 1):
            self.assertEqual(idem, "ev16b-ev-test-1-%d" % n)
            self.assertEqual(json.loads(body), {"question": "Synthetic question %d?" % n, "output": {"includeScores": False}})
            self.assertEqual(auth, "Bearer " + KEY)
        # the ledger: init + 3 `answer` lines, all bucket 16b, 1 answer each
        lines = self.ledger_lines()
        self.assertEqual([x["event"] for x in lines], ["init", "answer", "answer", "answer"])
        self.assertTrue(all(x["bucket"] == "16b" and x["answers"] == 1 and x["unit_usd"] == "0.001365" for x in lines[1:]))
        rc, status = self.budget("status")
        self.assertIn("BUCKET 16b size=80 used=3 remaining=77", status)
        rows = self.answers()
        self.assertEqual([r["index"] for r in rows], [1, 2, 3])
        self.assertEqual(rows[0]["query_id"], "q-1")
        self.assertEqual(rows[0]["answer"]["answer"]["summary"], "a1")
        self.assertEqual(rows[0]["outcome"], "ok")
        record = self.record()
        self.assertEqual(record["outcome"], "completed")
        # 3 x 0.001365 = 0.004095; Anthropic, Voyage, AWS reported separately then combined
        self.assertEqual(record["cost_report"]["anthropic"]["usd"], "0.004095")
        self.assertEqual(record["cost_report"]["voyage"]["usd"], "0.000000")
        self.assertIsNone(record["cost_report"]["aws"]["usd"])
        self.assertEqual(record["cost_report"]["combined_usd"], "0.004095")
        self.assertEqual(record["llm"]["bucket_used_at_start"], 0)
        self.assertEqual(record["llm"]["bucket_used_at_end"], 3)
        self.assertIn("RESULT: COMPLETED run=ev-test-1 asked=3 charged=3", out)

    def test_raw_files_are_sealed_and_never_hold_the_key_or_host(self):
        self.init_ledger()
        self.assertEqual(self.run_eval()[0], 0)
        raw = self.raw()
        names = sorted(os.listdir(raw))
        self.assertEqual(names, ["answers.jsonl", "events.jsonl", "raw.sha256", "run-record.json"])
        for name in names:
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(raw, name)).st_mode), 0o444)
            with open(os.path.join(raw, name)) as handle:
                self.assertNotIn(KEY, handle.read())
        self.assertEqual(self.record()["api_key_env"], "SCHOLARCHAIN_LOAD_API_KEY")

    def test_async_answer_polls_the_job_and_keeps_the_result(self):
        self.init_ledger()
        self.state.mode = "async"
        rc, out, err = self.run_eval("--max-answers", "1")
        self.assertEqual(rc, 0, err + out)
        row = self.answers()[0]
        self.assertEqual(row["job_id"], "job-1")
        self.assertEqual(row["job_state"], "SUCCEEDED")
        self.assertEqual(row["answer"]["answer"]["summary"], "from-job")
        paths = [p for p, _ in self.state.other]
        self.assertEqual(paths, ["/v1/jobs/job-1", "/v1/jobs/job-1", "/v1/jobs/job-1/result"])

    def test_bucket_exhausted_during_the_run_stops_all_calls(self):
        self.init_ledger()

        def drain(n):
            if n == 1:  # another program reserves the rest of the bucket while question 1 is in flight (size 80, used 1 -> 79 more)
                self.assertEqual(self.budget("reserve", "--bucket", "16b", "--answers", "79")[0], 0)

        self.state.after_post = drain
        rc, out, err = self.run_eval()
        self.assertEqual(rc, 4)
        self.assertEqual(len(self.state.posts), 1)
        stop = [e for e in self.events() if e["event"] == "llm-cap-reached"]
        self.assertEqual(len(stop), 1)
        self.assertEqual(stop[0]["reason"], "bucket-cap")
        self.assertIn("RESULT: STOPPED", out)
        self.assertEqual(self.record()["llm"]["stopped_reason"], "bucket-cap")
        self.assertEqual(self.record()["llm"]["answers_charged"], 1)

    def test_auth_failure_stops_after_the_first_answer(self):
        self.init_ledger()
        self.state.mode = "401"
        rc, out, err = self.run_eval()
        self.assertEqual(rc, 4)
        self.assertEqual(len(self.state.posts), 1)
        self.assertEqual(self.record()["outcome_reason"], "auth-failure")
        self.assertEqual(self.record()["llm"]["answers_charged"], 1)

    def test_repeated_failures_stop_the_run_and_error_bodies_are_not_stored(self):
        self.init_ledger()
        self.state.mode = "503-leak"
        rc, out, err = self.run_eval("--max-consecutive-failures", "2", questions=self.write_questions(5))
        self.assertEqual(rc, 4)
        self.assertEqual(len(self.state.posts), 2)
        self.assertEqual(self.record()["outcome_reason"], "repeated-failures")
        rows = self.answers()
        self.assertTrue(all(r["outcome"] == "server_error" and r["answer"] is None for r in rows))
        with open(os.path.join(self.raw(), "answers.jsonl")) as handle:
            self.assertNotIn(KEY, handle.read())

    def test_a_run_directory_is_never_reused(self):
        self.init_ledger()
        self.assertEqual(self.run_eval()[0], 0)
        rc, out, err = self.run_eval()
        self.assertEqual(rc, 3)
        self.assertIn("already exists", err)
        self.assertEqual(len(self.state.posts), 3)

    def test_output_root_inside_the_repository_must_be_under_target(self):
        self.init_ledger()
        rc, out, err = self.run_eval("--output-root", os.path.join(REPO, "experiments", "runs-should-not-exist"))
        self.assertEqual(rc, 3)
        self.assertEqual(self.state.posts, [])


    def test_the_16b_run_record_keeps_its_own_schema_and_the_failure_rule_is_unchanged(self):
        # evalq12.py sets its own schema name and neutral expected refusals; eval16b itself is unchanged: 3 consecutive failures stop it
        self.init_ledger()
        self.state.mode = "503-leak"
        rc, out, err = self.run_eval(questions=self.write_questions(6))
        self.assertEqual(rc, 4)
        self.assertEqual(len(self.answers()), 3)
        self.assertEqual(self.record()["schema"], "scholarchain.eval16b-run-record.v1")
        self.assertTrue(all("expected_refusal" not in row for row in self.answers()))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Feature tests for load-tests/evalq12.py, the Q12 benchmark runner, against a fake query-api on 127.0.0.1 and fake ledgers.

Run from the repository root:   python3 -I -m unittest discover -s load-tests/tests -v
No AWS, Anthropic or Voyage call and no non-loopback network. Expected values are derived by hand from the requirement:
33 questions x USD 0.001365 per answer (load-tests/config/load-profile.v1.json) = 0.045045; bucket 16b holds 40 answers in a fresh ledger
(experiments/manifests/llm-allocation.json), so 33 fit and 34 reserved elsewhere would not.
"""
import contextlib
import http.server
import importlib.util
import io
import json
import os
import shutil
import socket
import tempfile
import threading
import unittest
import urllib.parse
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
LOAD_TESTS = os.path.dirname(HERE)
REPO = os.path.dirname(LOAD_TESTS)
spec = importlib.util.spec_from_file_location("evalq12_under_test", os.path.join(LOAD_TESTS, "evalq12.py"))
q12 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q12)
BUDGET = q12.ev.llm_budget
KEY = "TESTKEY-SENTINEL-9f8e7d6c5b4a39281706"
REAL_QUESTIONS = os.path.join(REPO, "experiments", "inputs", "q12", "questions.txt")


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.posts = []
        self.gets = []
        self.evidence_per_answer = 2


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

        def ids(self, n):
            return ["evidence:metric:%d-%d" % (n, i) for i in range(state.evidence_per_answer)]

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            with state.lock:
                state.posts.append((self.headers.get("Idempotency-Key"), json.loads(body), self.headers.get("Authorization")))
                n = len(state.posts)
            if self.headers.get("Authorization") != "Bearer " + KEY:
                return self._send(401, {"error": "UNAUTHORIZED"})
            claims = [{"claimId": "claim:%d" % n, "evidenceIds": self.ids(n)}]
            return self._send(200, {"queryId": "qry-%d" % n, "answer": {"summary": "answer %d" % n}, "claims": claims})

        def do_GET(self):
            with state.lock:
                state.gets.append((self.path, self.headers.get("Authorization")))
            path = urllib.parse.unquote(self.path)
            if self.headers.get("Authorization") != "Bearer " + KEY:
                return self._send(401, {"error": "UNAUTHORIZED"})
            if path.startswith("/v1/explain/qry-"):
                n = int(path.rsplit("-", 1)[1])
                return self._send(200, {"queryId": "qry-%d" % n, "outcome": "ANSWERED", "evidenceIds": self.ids(n) + ["evidence:extra:%d" % n],
                                        "counters": {"attemptedClaims": 1, "verifiedClaims": 1, "rejectedClaims": 0}})
            if path.startswith("/v1/evidence/"):
                evidence_id = path[len("/v1/evidence/"):]
                if evidence_id.startswith("evidence:extra"):
                    return self._send(404, {"error": "NOT_FOUND"})
                return self._send(200, {"evidenceId": evidence_id, "supportingContent": {"subjectIds": ["researcher:dblp:x"], "windowIds": ["all-years"], "values": [{"field": "kind", "text": "metrics"}]}})
            return self._send(404, {"error": "NOT_FOUND"})

    return Handler


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True


class EvalQ12Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="evq12-test-")
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
            handle.write("".join("Synthetic Q12 question %d?\n" % i for i in range(1, n + 1)))
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
            rc = q12.main(argv, out=out)
        return rc, out.getvalue(), err.getvalue()

    def run_q12(self, *extra, questions=None, run_id="q12-test-1"):
        return self.go(["run", "--questions-file", questions or self.questions, "--ledger", self.ledger, "--output-root", self.out_root,
                        "--run-id", run_id, "--pause-seconds", "0"] + list(extra))

    def raw(self, run_id="q12-test-1"):
        return os.path.join(self.out_root, "q12-benchmark-" + run_id, "raw")

    def answers(self, run_id="q12-test-1"):
        with open(os.path.join(self.raw(run_id), "answers.jsonl")) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def test_plan_for_the_committed_33_questions_makes_no_network_call(self):
        self.init_ledger()
        before = self.ledger_lines()

        def no_network(*a, **k):
            raise AssertionError("plan must not open a network connection")

        env = {k: v for k, v in os.environ.items() if k not in ("SCHOLARCHAIN_LOAD_API_KEY", "SCHOLARCHAIN_LOAD_BASE_URL")}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(socket.socket, "connect", no_network), \
                mock.patch.object(socket, "create_connection", no_network), mock.patch.object(socket, "getaddrinfo", no_network):
            rc, out, err = self.go(["plan", "--ledger", self.ledger])
        self.assertEqual(rc, 0, err)
        self.assertIn("EXPERIMENT: q12-benchmark (LLM bucket 16b)", out)
        self.assertIn("QUESTIONS: 33 from the questions file", out)
        self.assertIn("PLANNED: answers=33 estimated_usd=0.045045", out)   # 33 x 0.001365
        self.assertIn("NETWORK: none", out)
        self.assertEqual(self.ledger_lines(), before)
        self.assertEqual(self.state.posts, [])

    def test_plan_refuses_when_bucket_16b_holds_fewer_than_33_answers(self):
        self.init_ledger()
        self.assertEqual(self.budget("reserve", "--bucket", "16b", "--answers", "10")[0], 0)   # 40 - 10 = 30 remaining
        rc, out, err = self.go(["plan", "--ledger", self.ledger])
        self.assertEqual(rc, 3)
        self.assertIn("33 questions to ask exceed the 30 remaining answers (size 40, used 10)", err)

    def test_the_default_questions_file_must_match_the_manifest_pin(self):
        self.init_ledger()
        manifest = os.path.join(self.tmp, "manifest.json")
        with open(manifest, "w") as handle:
            json.dump({"questions": {"sha256": "0" * 64}}, handle)
        with mock.patch.object(q12, "MANIFEST", manifest):
            rc, out, err = self.go(["plan", "--ledger", self.ledger])
        self.assertEqual(rc, 3)
        self.assertIn("differs from the sha256 pinned", err)
        # the committed manifest pins the committed file
        with open(os.path.join(REPO, "experiments", "manifests", "q12-benchmark.json")) as handle:
            self.assertEqual(json.load(handle)["questions"]["sha256"], q12.loadgen.sha256_file(REAL_QUESTIONS))
        self.assertEqual(self.state.posts, [])

    def test_run_charges_16b_before_each_request_and_records_the_evidence_trail(self):
        self.init_ledger()
        rc, out, err = self.run_q12()
        self.assertEqual(rc, 0, err)
        answers = [line for line in self.ledger_lines() if line.get("event") == "answer"]
        self.assertEqual([(a["bucket"], a["answers"], a["run"], a["n"]) for a in answers], [("16b", 1, "q12-test-1", n) for n in (1, 2, 3)])
        rows = self.answers()
        self.assertEqual([r["qid"] for r in rows], ["q01", "q02", "q03"])
        for n, row in enumerate(rows, 1):
            self.assertEqual((row["status"], row["query_id"], row["outcome"]), (200, "qry-%d" % n, "ok"))
            self.assertEqual(row["explain"]["status"], 200)
            self.assertEqual(row["explain"]["body"]["counters"]["verifiedClaims"], 1)
            # the claim cites 2 evidence ids, /v1/explain cites the same 2 plus one that does not resolve: 3 distinct ids fetched
            self.assertEqual(sorted(row["evidence"]), ["evidence:extra:%d" % n, "evidence:metric:%d-0" % n, "evidence:metric:%d-1" % n])
            self.assertEqual(row["evidence"]["evidence:extra:%d" % n]["status"], 404)
            self.assertIsNone(row["evidence"]["evidence:extra:%d" % n]["item"])
            self.assertEqual(row["evidence"]["evidence:metric:%d-0" % n]["item"]["evidenceId"], "evidence:metric:%d-0" % n)
        self.assertEqual(len(self.state.posts), 3)
        self.assertTrue(all(auth == "Bearer " + KEY for _p, auth in self.state.gets))
        self.assertEqual(len(self.state.gets), 3 * (1 + 3))   # per answer: one explain and three evidence fetches
        with open(os.path.join(self.raw(), "run-record.json")) as handle:
            record = json.load(handle)
        self.assertEqual((record["experiment_id"], record["llm"]["bucket"], record["llm"]["answers_charged"]), ("q12-benchmark", "16b", 3))
        self.assertEqual(record["llm"]["estimated_cost_usd"], "0.004095")   # 3 x 0.001365

    def test_the_api_key_is_never_written(self):
        self.init_ledger()
        self.assertEqual(self.run_q12()[0], 0)
        for base, _dirs, files in os.walk(self.out_root):
            for name in files:
                with open(os.path.join(base, name), errors="replace") as handle:
                    self.assertNotIn(KEY, handle.read(), name)
        with open(self.ledger) as handle:
            self.assertNotIn(KEY, handle.read())

    def test_evidence_fetches_are_capped_at_60_per_question(self):
        self.init_ledger()
        self.state.evidence_per_answer = 70
        self.assertEqual(self.run_q12(questions=self.write_questions(1))[0], 0)
        row = self.answers()[0]
        self.assertEqual(len(row["evidence"]), 60)
        self.assertEqual(row["evidence_ids_skipped"], 11)   # 70 cited by the claim + 1 extra from explain - 60 fetched

    def test_run_refuses_more_questions_than_the_bucket_before_sending(self):
        self.init_ledger()
        rc, out, err = self.run_q12(questions=self.write_questions(41))
        self.assertEqual(rc, 3)
        self.assertEqual(self.state.posts, [])
        self.assertEqual(len(self.ledger_lines()), 1)

    def test_an_authentication_failure_stops_the_run_after_one_charge(self):
        self.init_ledger()
        with mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": "WRONGKEY-1234567890abcdef"}):
            rc, out, err = self.run_q12()
        self.assertEqual(rc, 4)
        self.assertEqual(len(self.state.posts), 1)
        self.assertEqual(len([line for line in self.ledger_lines() if line.get("event") == "answer"]), 1)


if __name__ == "__main__":
    unittest.main()

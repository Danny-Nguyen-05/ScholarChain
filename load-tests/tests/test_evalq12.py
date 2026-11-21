#!/usr/bin/env python3
"""Feature tests for load-tests/evalq12.py, the Q12 benchmark runner, against a fake query-api on 127.0.0.1 and fake ledgers.

Run from the repository root:   python3 -I -m unittest discover -s load-tests/tests -v
No AWS, Anthropic or Voyage call and no non-loopback network. Expected values are derived by hand from the requirement:
33 questions x USD 0.001365 per answer (load-tests/config/load-profile.v1.json) = 0.045045; bucket 16b holds 80 answers in a fresh ledger
(experiments/manifests/llm-allocation.json; 40 until the user decision of 2026-11-21, option A), so 33 fit and 48 reserved elsewhere would leave only 32.
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
        self.with_big = False     # the claims also cite an evidence item of about 70 KB
        self.forced = {}          # question text -> (status, payload) answered instead of the normal reply


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
            return ["evidence:metric:%d-%d" % (n, i) for i in range(state.evidence_per_answer)] + (["evidence:big:%d" % n] if state.with_big else [])

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            with state.lock:
                state.posts.append((self.headers.get("Idempotency-Key"), json.loads(body), self.headers.get("Authorization")))
                n = len(state.posts)
            if self.headers.get("Authorization") != "Bearer " + KEY:
                return self._send(401, {"error": "UNAUTHORIZED"})
            forced = state.forced.get(state.posts[-1][1]["question"])
            if forced:
                return self._send(*forced)
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
            if path.startswith("/v1/graph/nodes/"):
                if "missing" in path:
                    return self._send(404, {"error": "NOT_FOUND"})
                return self._send(200, {"nodeId": path.rsplit("/", 1)[1]})
            if path.startswith("/v1/evidence/"):
                evidence_id = path[len("/v1/evidence/"):]
                if evidence_id.startswith("evidence:big"):
                    return self._send(200, {"evidenceId": evidence_id, "supportingContent": {"subjectIds": [], "windowIds": [], "values": [{"field": "kind", "text": "x" * 70000}]}})
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
        self.assertEqual(self.budget("reserve", "--bucket", "16b", "--answers", "50")[0], 0)   # 80 - 50 = 30 remaining
        rc, out, err = self.go(["plan", "--ledger", self.ledger])
        self.assertEqual(rc, 3)
        self.assertIn("33 questions to ask exceed the 30 remaining answers (size 80, used 50)", err)

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
        rc, out, err = self.run_q12(questions=self.write_questions(81))
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

    # --- review round 1
    def test_expected_refusals_do_not_stop_the_run_but_unexpected_ones_do(self):
        self.init_ledger()
        questions = self.write_questions(6)
        with open(questions) as handle:
            lines = [x.strip() for x in handle]
        refusal = (422, {"error": "UNSUPPORTED_QUERY", "message": "do not store this text", "traceId": "t"})
        for q in lines[:4]:
            self.state.forced[q] = refusal   # four expected refusals in a row: more than the default 3 consecutive failures
        with mock.patch.object(q12, "abstain_questions", lambda: set(lines[:4])):
            rc, out, err = self.run_q12(questions=questions)
        self.assertEqual(rc, 0, err)
        rows = self.answers()
        self.assertEqual(len(rows), 6)   # the run completed
        for row in rows[:4]:
            self.assertEqual((row["status"], row["outcome"], row["raw_outcome"], row["expected_refusal"], row["error_code"]), (422, "expected_refusal", "client_error", True, "UNSUPPORTED_QUERY"))
            self.assertIsNone(row["query_id"])
            self.assertNotIn("do not store this text", json.dumps(row))   # only the closed error code of a 4xx body is kept
        self.assertEqual(rows[4]["outcome"], "ok")
        self.assertNotIn("expected_refusal", rows[4])
        with open(os.path.join(self.raw(), "run-record.json")) as handle:
            record = json.load(handle)
        self.assertEqual(record["outcomes"], {"expected_refusal": 4, "ok": 2})   # counted apart from ok and from failures
        self.assertEqual(record["schema"], "scholarchain.evalq12-run-record.v1")

    def test_the_same_refusals_on_questions_the_key_expects_answered_count_as_failures(self):
        self.init_ledger()
        questions = self.write_questions(6)
        with open(questions) as handle:
            lines = [x.strip() for x in handle]
        for q in lines[:4]:
            self.state.forced[q] = (422, {"error": "UNSUPPORTED_QUERY"})
        with mock.patch.object(q12, "abstain_questions", lambda: set()):
            rc, out, err = self.run_q12(questions=questions)
        self.assertEqual(rc, 4)
        self.assertEqual(len(self.answers()), 3)   # stopped after 3 consecutive failures
        self.assertTrue(all(r["outcome"] == "client_error" and "expected_refusal" not in r for r in self.answers()))

    def test_other_4xx_on_an_abstain_question_are_failures_and_the_error_code_is_closed(self):
        self.init_ledger()
        questions = self.write_questions(3)
        with open(questions) as handle:
            lines = [x.strip() for x in handle]
        self.state.forced[lines[0]] = (429, {"error": "RATE_LIMITED"})
        self.state.forced[lines[1]] = (422, {"error": "not a closed code <script>"})
        self.state.forced[lines[2]] = (400, {"error": "INVALID_REQUEST"})
        with mock.patch.object(q12, "abstain_questions", lambda: set(lines)):
            rc, out, err = self.run_q12(questions=questions)
        rows = self.answers()
        self.assertEqual(rc, 4)
        self.assertEqual([(r["status"], r["error_code"], r["outcome"]) for r in rows], [(429, "RATE_LIMITED", "throttled"), (422, None, "client_error"), (400, "INVALID_REQUEST", "client_error")])

    def test_a_non_loopback_base_url_is_refused_before_anything_is_sent(self):
        self.init_ledger()
        with mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_BASE_URL": "https://query.example.com"}):
            rc, out, err = self.run_q12()
        self.assertEqual(rc, 3)
        self.assertIn("loopback host", err)
        self.assertEqual((self.state.posts, self.state.gets), ([], []))
        self.assertEqual(len(self.ledger_lines()), 1)

    def include_file(self, *ids):
        path = os.path.join(self.tmp, "include.txt")
        with open(path, "w") as handle:
            handle.write("".join(i + "\n" for i in ids))
        return path

    def test_preflight_refuses_before_the_first_charge_when_an_include_id_is_missing(self):
        self.init_ledger()
        include = self.include_file("researcher:dblp:aaa", "researcher:dblp:missing1", "researcher:dblp:bbb")
        rc, out, err = self.run_q12("--include-ids-file", include)
        self.assertEqual(rc, 3)
        self.assertIn("PREFLIGHT: the running artifact lacks 1 of 3 include IDs", err)
        self.assertIn("nothing was charged", err)
        self.assertEqual(self.state.posts, [])
        self.assertEqual([line for line in self.ledger_lines() if line.get("event") == "answer"], [])
        self.assertEqual(len(self.state.gets), 3)   # one GET per include id, with the key, and no model call
        self.assertTrue(all(path.startswith("/v1/graph/nodes/") and auth == "Bearer " + KEY for path, auth in self.state.gets))

    def test_preflight_passes_and_the_run_proceeds(self):
        self.init_ledger()
        include = self.include_file("researcher:dblp:aaa", "researcher:dblp:bbb")
        rc, out, err = self.run_q12("--include-ids-file", include)
        self.assertEqual(rc, 0, err)
        self.assertIn("PREFLIGHT: 2 of 2 include IDs are present", out)
        self.assertEqual(len(self.state.posts), 3)

    def test_only_asks_the_named_questions_of_the_pinned_file_with_their_ids(self):
        self.init_ledger()
        rc, out, err = self.go(["run", "--only", "q04,q15", "--ledger", self.ledger, "--output-root", self.out_root, "--run-id", "q12-test-1", "--pause-seconds", "0"])
        self.assertEqual(rc, 0, err)
        with open(REAL_QUESTIONS) as handle:
            lines = [x.rstrip("\n") for x in handle if x.strip()]
        rows = self.answers()
        self.assertEqual([(r["qid"], r["question"]) for r in rows], [("q04", lines[3]), ("q15", lines[14])])
        self.assertEqual([p[1]["question"] for p in self.state.posts], [lines[3], lines[14]])
        self.assertEqual(len([line for line in self.ledger_lines() if line.get("event") == "answer"]), 2)   # one charge per question asked
        with open(os.path.join(REPO, "experiments", "inputs", "q12", "include-ids.txt")) as handle:
            n_include = len([x for x in handle if x.strip()])
        self.assertIn("PREFLIGHT: %d of %d include IDs are present" % (n_include, n_include), out)   # the committed include list is checked on a probe too
        self.assertIn("QUESTIONS: 2 from the questions file", out)

    def test_only_rejects_bad_ids_and_a_second_questions_file(self):
        self.init_ledger()
        for bad in ("q99", "q00", "4", "q04,q04", "q04,x"):
            rc, out, err = self.go(["run", "--only", bad, "--ledger", self.ledger, "--output-root", self.out_root])
            self.assertEqual(rc, 3, bad)
            self.assertIn("--only takes distinct question ids", err)
        rc, out, err = self.go(["run", "--only", "q04", "--questions-file", self.questions, "--ledger", self.ledger, "--output-root", self.out_root])
        self.assertEqual(rc, 3)
        self.assertIn("cannot be combined with another --questions-file", err)
        self.assertEqual(self.state.posts, [])

    def test_skipped_ids_are_listed(self):
        self.init_ledger()
        self.state.evidence_per_answer = 70
        self.assertEqual(self.run_q12(questions=self.write_questions(1))[0], 0)
        row = self.answers()[0]
        self.assertEqual(len(row["evidence"]), 60)
        self.assertEqual(len(row["evidence_skipped_ids"]), row["evidence_ids_skipped"])
        self.assertEqual(row["evidence_skipped_ids"][-1], "evidence:extra:1")   # 70 metric ids, then the explain-only id: the 71st is skipped
        self.assertTrue(set(row["evidence_skipped_ids"]).isdisjoint(row["evidence"]))
        self.assertTrue(all(v["oversize"] is False for v in row["evidence"].values()))

    def test_an_oversize_item_is_flagged_not_stored(self):
        self.init_ledger()
        self.state.with_big = True
        self.assertEqual(self.run_q12(questions=self.write_questions(1))[0], 0)
        row = self.answers()[0]
        big = row["evidence"]["evidence:big:1"]
        self.assertEqual((big["status"], big["item"], big["oversize"]), (200, None, True))   # over 64 KiB: flagged, the body is not kept
        self.assertFalse(row["evidence"]["evidence:metric:1-0"]["oversize"])

    def run_sequence(self, plan):
        """plan: list of 'f' (a 500, a failure), 'r' (an expected refusal) or 'o' (ok), one entry per question."""
        self.init_ledger()
        questions = self.write_questions(len(plan))
        with open(questions) as handle:
            lines = [x.strip() for x in handle]
        for line, kind in zip(lines, plan):
            if kind == "f":
                self.state.forced[line] = (500, {"error": "INTERNAL"})
            elif kind == "r":
                self.state.forced[line] = (422, {"error": "UNSUPPORTED_QUERY"})
        refusals = {line for line, kind in zip(lines, plan) if kind == "r"}
        with mock.patch.object(q12, "abstain_questions", lambda: refusals):
            rc, out, err = self.run_q12(questions=questions)
        return rc, [r["outcome"] for r in self.answers()]

    def test_an_expected_refusal_is_neutral_for_the_failure_counter(self):
        # failure, refusal, failure, refusal, failure: the refusals neither reset nor add, so the stop comes at the third FAILURE (the 5th question)
        rc, outcomes = self.run_sequence(["f", "r", "f", "r", "f", "o", "o"])
        self.assertEqual((rc, outcomes), (4, ["server_error", "expected_refusal", "server_error", "expected_refusal", "server_error"]))

    def test_an_expected_refusal_does_not_reset_the_failure_counter(self):
        # two failures, a refusal, a failure: the third failure stops the run at the 4th question
        rc, outcomes = self.run_sequence(["f", "f", "r", "f", "o"])
        self.assertEqual((rc, len(outcomes)), (4, 4))

    def test_a_success_still_resets_the_failure_counter_between_refusals(self):
        rc, outcomes = self.run_sequence(["f", "f", "r", "o", "f", "f", "r", "o"])
        self.assertEqual((rc, len(outcomes)), (0, 8))   # fail fail (refusal) ok resets: never three failures in a row

    def test_a_closed_error_code_needs_a_full_match_not_a_trailing_newline(self):
        self.init_ledger()
        questions = self.write_questions(1)
        with open(questions) as handle:
            line = handle.read().strip()
        self.state.forced[line] = (422, {"error": "UNSUPPORTED_QUERY\n"})
        with mock.patch.object(q12, "abstain_questions", lambda: {line}):
            self.run_q12(questions=questions)
        row = self.answers()[0]
        self.assertEqual((row["error_code"], row["outcome"], "expected_refusal" in row), (None, "client_error", False))

    def test_preflight_wording_separates_auth_transport_and_missing(self):
        include = self.include_file("researcher:dblp:aaa")
        self.init_ledger()
        with mock.patch.dict(os.environ, {"SCHOLARCHAIN_LOAD_API_KEY": "WRONGKEY-1234567890abcdef"}):
            rc, out, err = self.run_q12("--include-ids-file", include)
        self.assertEqual(rc, 3)
        self.assertIn("refused the API key (HTTP 401", err)
        self.assertIn("says nothing about the artifact", err)
        self.assertNotIn("lacks", err)
        self.server.shutdown()
        self.server.server_close()
        rc, out, err = self.run_q12("--include-ids-file", include)
        self.assertEqual(rc, 3)
        self.assertIn("transport error", err)
        self.assertNotIn("lacks", err)
        self.assertEqual([line for line in self.ledger_lines() if line.get("event") == "answer"], [])

    def test_the_inputs_must_agree_with_the_key_before_a_default_file_run(self):
        self.init_ledger()
        specs = json.load(open(q12.SPECS))
        specs["questions"][0]["question"] = "A changed question?"
        altered = os.path.join(self.tmp, "specs.json")
        with open(altered, "w") as handle:
            json.dump(specs, handle)
        with mock.patch.object(q12, "SPECS", altered):
            rc, out, err = self.go(["plan", "--ledger", self.ledger])
        self.assertEqual(rc, 3)
        self.assertIn("differs from the question_specs_sha256 of answer-key.json", err)
        self.assertEqual(self.state.posts, [])

    def test_only_accepts_the_default_questions_file_given_explicitly(self):
        self.init_ledger()
        rc, out, err = self.go(["run", "--only", "q04", "--questions-file", REAL_QUESTIONS, "--ledger", self.ledger, "--output-root", self.out_root,
                                "--run-id", "q12-test-1", "--pause-seconds", "0"])
        self.assertEqual(rc, 0, err)
        self.assertEqual([r["qid"] for r in self.answers()], ["q04"])
        rc, out, err = self.go(["run", "--only", "q05", "--questions-file=" + REAL_QUESTIONS, "--ledger", self.ledger, "--output-root", self.out_root,
                                "--run-id", "q12-test-2", "--pause-seconds", "0"])
        self.assertEqual(rc, 0, err)
        self.assertEqual([r["qid"] for r in self.answers("q12-test-2")], ["q05"])

    def test_probe_then_full_run_fit_the_raised_16b_bucket_with_the_transfer(self):
        """The documented order: the --only q04 probe (1 answer), then the full 33 run. The pinned base is 80 (user decision 2026-11-21, option A) and the ledger adds the 36 transferred in: size 116."""
        self.init_ledger()
        approval = os.path.join(self.tmp, "approval.txt")
        with open(approval, "w") as handle:
            handle.write("APPROVED_LLM_TRANSFER=15b->16b:36\n")
        self.assertEqual(self.budget("reserve", "--bucket", "16b", "--answers", "40")[0], 0)   # Session 1 used the 40 answers of the then-40-answer 16b bucket (stands in for a bucket used up before the transfer)
        rc, out = self.budget("transfer", "--from", "15b", "--to", "16b", "--answers", "36", "--approval", approval)
        self.assertEqual(rc, 0, out)
        rc, out, err = self.go(["run", "--only", "q04", "--ledger", self.ledger, "--output-root", self.out_root, "--run-id", "q12-probe", "--pause-seconds", "0"])
        self.assertEqual(rc, 0, err)
        rc, out, err = self.go(["plan", "--ledger", self.ledger])
        self.assertEqual(rc, 0, err)
        self.assertIn("BUCKET 16b size=116 used=41 remaining=75", out)   # 80 base + 36 transferred, 40 + 1 probe used: 75 left, 33 needed
        self.assertIn("PLANNED: answers=33", out)

    def test_the_committed_question_order_never_puts_two_abstain_questions_together(self):
        specs = os.path.join(REPO, "experiments", "inputs", "q12", "question-specs.json")
        with open(specs) as handle:
            flags = [q["type"] in q12.ABSTAIN_TYPES for q in json.load(handle)["questions"]]
        self.assertFalse(any(a and b for a, b in zip(flags, flags[1:])))
        self.assertEqual(len(q12.abstain_questions()), 6)


if __name__ == "__main__":
    unittest.main()

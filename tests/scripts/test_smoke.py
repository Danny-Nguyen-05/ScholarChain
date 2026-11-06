"""Independent tests for scripts/smoke-test.sh against a stub query-api server written for this suite (Subphase 13B).

Contract: modules/services/README.md and the OpenAPI file (healthz/readyz without a key; POST /v1/query with a Bearer
key and an Idempotency-Key; 200 answer or 202 job; GET /v1/evidence/{id}; GET /v1/queries/{id}/evidence; 401 UNAUTHORIZED
for a missing or invalid key), plus scripts/README.md "Smoke test": six markers smoke-healthz ... smoke-error-path, exit 4
with the failing marker as the last STEP line, 124 on a timeout, 3 for a missing key or an unsafe URL. The stub is a real
HTTP server on the loopback interface; no other network is used. The API key is a canary and must never be printed.
"""
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import sc_support as S

KEY = S.CANARY_SMOKE_KEY
STEPS = ["smoke-healthz", "smoke-readyz", "smoke-query", "smoke-evidence", "smoke-idempotency", "smoke-error-path"]


class Stub:
    """Configurable stub of the query-api contract. `behave` entries switch one documented behaviour off."""

    def __init__(self, **behave):
        self.behave = behave
        self.requests = []
        self.queries = {}  # idempotency key -> queryId
        self.evidence = {}  # queryId -> evidence ids
        self.counter = 0
        self.polls = 0
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, status, body, ctype="application/json"):
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def authed(self):
                return self.headers.get("Authorization") == "Bearer " + KEY

            def deny(self):
                body = {"error": "UNAUTHORIZED", "message": "missing or invalid credentials", "traceId": "t-1", "retryable": False}
                if stub.behave.get("echo_key"):
                    body["message"] = "bad credentials: " + (self.headers.get("Authorization") or "") + " " + KEY
                self.send(401, body)

            def record(self, body=None):
                stub.requests.append({"method": self.command, "path": self.path, "auth": self.headers.get("Authorization"),
                                      "idem": self.headers.get("Idempotency-Key"), "body": body})

            def do_GET(self):
                self.record()
                path = self.path
                if path == "/healthz":
                    if stub.behave.get("health_status"):
                        return self.send(stub.behave["health_status"], {"status": "alive"})
                    return self.send(200, {"status": stub.behave.get("health_body", "alive")})
                if path == "/readyz":
                    if stub.behave.get("slow_ready"):
                        time.sleep(stub.behave["slow_ready"])
                    if stub.behave.get("ready_status"):
                        return self.send(stub.behave["ready_status"], {"status": "not-ready"})
                    return self.send(200, {"status": "ready"})
                if path.startswith("/v1/jobs/"):
                    if not self.authed():
                        return self.deny()
                    stub.polls += 1
                    if path.endswith("/result"):
                        return self.send(200, stub.answer("q-job-1"))
                    state = stub.behave.get("job_state", "SUCCEEDED" if stub.polls > 1 else "RUNNING")
                    return self.send(200, {"jobId": "job-1", "queryId": "q-job-1", "state": state, "stage": "x", "createdAt": "2026-01-01T00:00:00Z",
                                           "updatedAt": "2026-01-01T00:00:00Z", "resultUrl": None, "error": None})
                if path.startswith("/v1/evidence/"):
                    if not self.authed():
                        return self.deny()
                    if stub.behave.get("evidence_404"):
                        return self.send(404, {"error": "NOT_FOUND", "message": "no", "traceId": "t", "retryable": False})
                    ev = path.rsplit("/", 1)[1]
                    item = {"evidenceId": ev, "evidenceType": "WORK", "sourceDataset": "synthetic", "provenance": {"snapshot": "s1"}}
                    if stub.behave.get("evidence_wrong_id"):
                        item["evidenceId"] = "someone-else"
                    if stub.behave.get("evidence_no_provenance"):
                        item["provenance"] = {}
                    return self.send(200, item)
                if path.startswith("/v1/queries/") and path.endswith("/evidence"):
                    if not self.authed():
                        return self.deny()
                    qid = path.split("/")[3]
                    ids = list(stub.evidence.get(qid, []))
                    if stub.behave.get("duplicate_evidence_on_repeat") and stub.counter > 1:
                        ids = ids + ["ev-dup"]
                    return self.send(200, {"queryId": qid, "evidenceIds": ids})
                self.send(404, {"error": "NOT_FOUND", "message": "no", "traceId": "t", "retryable": False})

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n).decode() if n else ""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = None
                self.record(body)
                if self.path != "/v1/query":
                    return self.send(404, {"error": "NOT_FOUND", "message": "no", "traceId": "t", "retryable": False})
                if not self.authed():
                    if stub.behave.get("accept_unauthenticated"):
                        return self.send(200, stub.answer("q-open"))
                    return self.deny()
                idem = self.headers.get("Idempotency-Key")
                if not idem:
                    return self.send(400, {"error": "BAD_REQUEST", "message": "Idempotency-Key required", "traceId": "t", "retryable": False})
                stub.counter += 1
                if stub.behave.get("new_query_each_time"):
                    qid = "q-%d" % stub.counter
                else:
                    qid = stub.queries.setdefault(idem, "q-%d" % (len(stub.queries) + 1))
                if stub.behave.get("async"):
                    return self.send(202, {"queryId": "q-job-1", "mode": "asynchronous", "jobId": "job-1", "status": "QUEUED", "statusUrl": "/v1/jobs/job-1"})
                return self.send(200, stub.answer(qid))

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def answer(self, qid):
        claims = [] if self.behave.get("no_claims") else [{"claimId": "c1", "evidenceIds": ["ev-1", "ev-2"]}]
        if self.behave.get("claims_without_evidence"):
            claims = [{"claimId": "c1", "evidenceIds": []}]
        self.evidence[qid] = ["ev-1", "ev-2"]
        return {"queryId": qid, "mode": "synchronous", "answer": {"summary": "publication count for A is 2"}, "claims": claims,
                "links": {"explain": "/v1/explain/" + qid, "evidence": "/v1/queries/%s/evidence" % qid, "result": "/v1/jobs/x/result"}}

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class SmokeBase(unittest.TestCase):
    def start(self, **behave):
        fx = S.Fixture(self)
        stub = Stub(**behave)
        self.addCleanup(stub.stop)
        return fx, stub

    def smoke(self, fx, stub, extra=(), env=None, url=None):
        e = {"SCHOLARCHAIN_SMOKE_API_KEY": KEY}
        e.update(env or {})
        return fx.run("smoke-test.sh", ["--url", url or stub.url] + list(extra), e, timeout=120)

    def assert_one_result(self, r):
        self.assertEqual(len(r.results()), 1, r.describe())


class SmokePasses(SmokeBase):
    def test_healthy_stub_passes_all_six_checks_in_order_with_markers(self):
        fx, stub = self.start()
        r = self.smoke(fx, stub)
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        self.assert_one_result(r)
        self.assertTrue(r.lines()[-1].startswith("RESULT: PASS"))
        got = [s for s in r.steps() if s.startswith("smoke-") and s != "smoke-complete"]
        self.assertEqual(got, STEPS)
        self.assertEqual(len(r.grep(r"^CHECK-OK")), 6)
        self.assertEqual(r.calls, [], "the smoke test must not touch aws or any cloud tool")

    def test_requests_follow_the_documented_contract(self):
        fx, stub = self.start()
        r = self.smoke(fx, stub)
        self.assertEqual(r.rc, 0, r.describe())
        by_path = {}
        for req in stub.requests:
            by_path.setdefault((req["method"], req["path"]), []).append(req)
        for probe in (("GET", "/healthz"), ("GET", "/readyz")):
            for req in by_path[probe]:
                self.assertIsNone(req["auth"], "%s must be called without credentials" % (probe,))
        posts = by_path[("POST", "/v1/query")]
        authed = [p for p in posts if p["auth"] == "Bearer " + KEY]
        self.assertGreaterEqual(len(authed), 2, "the query and its repeat both carry the bearer key")
        self.assertTrue(all(p["idem"] for p in authed), "every authenticated query carries an Idempotency-Key")
        self.assertEqual(authed[0]["idem"], authed[1]["idem"], "the repeat must reuse the same Idempotency-Key")
        self.assertEqual(authed[0]["body"], authed[1]["body"])
        self.assertEqual(authed[0]["body"]["question"], "Synthetic fixture: publication count for A")
        self.assertIn(("GET", "/v1/evidence/ev-1"), by_path, "the first evidence id cited by a claim must be fetched")
        unauth = [p for p in posts if p["auth"] != "Bearer " + KEY]
        self.assertGreaterEqual(len(unauth), 2, "one request with no key and one with an invalid key")
        self.assertTrue(any(p["auth"] is None for p in unauth))
        self.assertTrue(any(p["auth"] and p["auth"] != "Bearer " + KEY for p in unauth))

    def test_asynchronous_job_reference_is_followed_to_success(self):
        fx, stub = self.start(**{"async": True})
        r = self.smoke(fx, stub)
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        paths = [req["path"] for req in stub.requests]
        self.assertIn("/v1/jobs/job-1", paths)
        self.assertIn("/v1/jobs/job-1/result", paths)

    def test_custom_query_body_is_sent(self):
        fx, stub = self.start()
        body = fx.aux / "body.json"
        S.Fixture.write_json(body, {"question": "custom question", "output": {"includeScores": False}})
        r = self.smoke(fx, stub, extra=["--query-body", str(body)])
        self.assertEqual(r.rc, 0, r.describe())
        sent = [q["body"] for q in stub.requests if q["method"] == "POST" and q["auth"] == "Bearer " + KEY]
        self.assertEqual(sent[0]["question"], "custom question")

    def test_key_is_read_from_the_variable_named_by_api_key_env(self):
        fx, stub = self.start()
        r = fx.run("smoke-test.sh", ["--url", stub.url, "--api-key-env", "MY_OWN_KEY_VAR"], {"MY_OWN_KEY_VAR": KEY})
        self.assertEqual(r.rc, 0, r.describe())

    def test_smoke_url_environment_variable_is_accepted(self):
        fx, stub = self.start()
        r = fx.run("smoke-test.sh", [], {"SCHOLARCHAIN_SMOKE_URL": stub.url, "SCHOLARCHAIN_SMOKE_API_KEY": KEY})
        self.assertEqual(r.rc, 0, r.describe())

    def test_the_api_key_is_never_printed_even_when_every_request_succeeds(self):
        fx, stub = self.start()
        r = self.smoke(fx, stub, env=dict(S.SECRET_ENV))
        self.assertEqual(r.rc, 0, r.describe())
        for canary in (S.CANARY_SECRET, S.CANARY_TOKEN, KEY):
            self.assertNotIn(canary, r.out)
            self.assertNotIn(canary, r.err)


class SmokeFailures(SmokeBase):
    def expect_failure(self, stub_behave, marker, code=4, extra=(), env=None):
        fx, stub = self.start(**stub_behave)
        r = self.smoke(fx, stub, extra=extra, env=env)
        self.assertEqual(r.rc, code, "%s\n%s" % (stub_behave, r.describe()))
        self.assertEqual(r.status, "FAIL", r.describe())
        self.assert_one_result(r)
        self.assertEqual(S.last_step(r), marker, "the failing check must be the last STEP marker\n" + r.describe())
        self.assertTrue(r.grep(r"^CHECK-FAILED"), r.describe())
        self.assertNotIn(KEY, r.out + r.err)
        self.assertEqual(r.calls, [])
        return r

    def test_health_failure_is_reported_at_smoke_healthz(self):
        self.expect_failure({"health_status": 500}, "smoke-healthz")
        self.expect_failure({"health_body": "dead"}, "smoke-healthz")

    def test_readiness_failure_is_reported_at_smoke_readyz_and_stops_the_run(self):
        r = self.expect_failure({"ready_status": 503}, "smoke-readyz")
        self.assertNotIn("smoke-query", r.steps(), "later checks must not run after a failure")

    def test_query_without_claims_or_evidence_fails_at_smoke_query(self):
        self.expect_failure({"no_claims": True}, "smoke-query")
        self.expect_failure({"claims_without_evidence": True}, "smoke-query")

    def test_unknown_evidence_fails_at_smoke_evidence(self):
        self.expect_failure({"evidence_404": True}, "smoke-evidence")
        self.expect_failure({"evidence_wrong_id": True}, "smoke-evidence")
        self.expect_failure({"evidence_no_provenance": True}, "smoke-evidence")

    def test_duplicate_query_on_repeat_fails_at_smoke_idempotency(self):
        self.expect_failure({"new_query_each_time": True}, "smoke-idempotency")

    def test_changed_evidence_list_on_repeat_fails_at_smoke_idempotency(self):
        self.expect_failure({"duplicate_evidence_on_repeat": True}, "smoke-idempotency")

    def test_open_endpoint_that_accepts_requests_without_a_key_fails_at_smoke_error_path(self):
        self.expect_failure({"accept_unauthenticated": True}, "smoke-error-path")

    def test_error_body_that_echoes_the_key_fails_at_smoke_error_path_and_the_key_is_not_printed(self):
        r = self.expect_failure({"echo_key": True}, "smoke-error-path")
        self.assertNotIn(KEY, r.out + r.err)

    def test_failed_job_fails_at_smoke_query(self):
        self.expect_failure({"async": True, "job_state": "FAILED"}, "smoke-query")

    def test_slow_readiness_times_out_with_exit_124_at_smoke_readyz(self):
        fx, stub = self.start(slow_ready=5)
        r = self.smoke(fx, stub, extra=["--request-timeout", "1"])
        self.assertEqual((r.rc, r.status), (124, "FAIL"), r.describe())
        self.assertEqual(S.last_step(r), "smoke-readyz")
        self.assert_one_result(r)

    def test_closed_port_is_a_failure_not_a_pass(self):
        fx, stub = self.start()
        url = stub.url
        stub.stop()
        r = self.smoke(fx, stub, url=url, extra=["--request-timeout", "2"])
        self.assertEqual(r.rc, 4, r.describe())
        self.assertEqual(S.last_step(r), "smoke-healthz")


class SmokeRefusals(SmokeBase):
    def test_missing_key_is_refused_with_exit_3_before_any_request(self):
        fx, stub = self.start()
        r = fx.run("smoke-test.sh", ["--url", stub.url], {})
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertEqual(stub.requests, [])
        r = fx.run("smoke-test.sh", ["--url", stub.url, "--api-key-env", "NOT_SET_ANYWHERE"], {"SCHOLARCHAIN_SMOKE_API_KEY": KEY})
        self.assertEqual(r.rc, 3, r.describe())
        self.assertEqual(stub.requests, [])

    def test_plain_http_to_a_non_loopback_host_is_refused_so_the_key_never_leaves_in_clear_text(self):
        fx, stub = self.start()
        for url in ("http://example.com", "http://192.0.2.10:8080", "http://scholarchain.internal:80"):
            with self.subTest(url=url):
                r = self.smoke(fx, stub, url=url, extra=["--request-timeout", "1"])
                self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
                self.assertNotIn("smoke-healthz", r.steps(), "no request may be attempted for an unsafe URL")
                self.assertNotIn(KEY, r.out + r.err)

    def test_loopback_http_is_accepted_for_localhost_and_127_0_0_1(self):
        fx, stub = self.start()
        port = stub.url.rsplit(":", 1)[1]
        for host in ("127.0.0.1", "localhost"):
            with self.subTest(host=host):
                r = self.smoke(fx, stub, url="http://%s:%s" % (host, port))
                self.assertEqual(r.rc, 0, r.describe())

    def test_urls_with_userinfo_path_query_or_fragment_are_refused(self):
        fx, stub = self.start()
        port = stub.url.rsplit(":", 1)[1]
        for url in ("http://user:pw@127.0.0.1:%s" % port, "http://127.0.0.1:%s/v1" % port, "http://127.0.0.1:%s?x=1" % port,
                    "http://127.0.0.1:%s#frag" % port, "ftp://127.0.0.1:%s" % port, "not a url"):
            with self.subTest(url=url):
                r = self.smoke(fx, stub, url=url)
                self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
                self.assertEqual(stub.requests, [])

    def test_missing_url_and_bad_flags_are_usage_errors_exit_2(self):
        fx, stub = self.start()
        self.assertEqual(fx.run("smoke-test.sh", [], {"SCHOLARCHAIN_SMOKE_API_KEY": KEY}).rc, 2)
        self.assertEqual(fx.run("smoke-test.sh", ["--bogus"], {}).rc, 2)
        self.assertEqual(fx.run("smoke-test.sh", ["--url", stub.url, "--api-key-env", "bad name"], {}).rc, 2)
        self.assertEqual(fx.run("smoke-test.sh", ["--url", stub.url, "--request-timeout", "abc"], {"SCHOLARCHAIN_SMOKE_API_KEY": KEY}).rc, 2)
        self.assertEqual(fx.run("smoke-test.sh", ["--url", stub.url, "--query-body", "/no/such/file"], {"SCHOLARCHAIN_SMOKE_API_KEY": KEY}).rc, 2)


if __name__ == "__main__":
    unittest.main()

"""smoke-test.sh and smoke-local.sh (Subphase 13B) against a local stub server that implements the query-api contract
(modules/services/README.md and the OpenAPI file): healthy runs pass and every failure mode fails with the STEP marker of the
failed check. The stub never sees a real credential: the key is a throwaway test string."""
import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import unittest
import urllib.parse

from helpers import SCRIPTS_DIR, Fixture, write_exec

KEY = "stub-throwaway-key-Zq81-NotARealCredential"
QUERY_ID = "qry-" + "ab" * 32
JOB_ID = "job-" + "ab" * 32
EVIDENCE_ID = "evidence:metric:" + "cd" * 32
FIXTURE_BODY = {"question": "Synthetic fixture: publication count for A", "output": {"includeScores": False}}


class Stub:
    """A tiny HTTP server with failure switches. It records every request and checks the headers the contract requires."""

    def __init__(self, **flags):
        self.flags = {"async": False}
        self.flags.update(flags)
        self.requests = []
        self.bound = {}  # idempotency key -> (body, queryId)
        self.counter = 0
        stub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(self, status, document, extra=None):
                payload = json.dumps(document).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def authorised(self):
                header = self.headers.get("Authorization", "")
                return header == "Bearer " + KEY

            def unauthorized(self):
                message = "Missing or invalid authentication."
                if stub.flags.get("echo_key"):
                    message += " (the expected credential is " + KEY + ")"
                self.send(401, {"error": "UNAUTHORIZED", "message": message, "traceId": "t", "retryable": False})

            def do_GET(self):
                stub.requests.append(("GET", self.path, dict(self.headers)))
                path = urllib.parse.unquote(self.path)
                delay = stub.flags.get("delay_" + path)
                if delay:
                    time.sleep(delay)
                if path == "/healthz":
                    if stub.flags.get("health_fail"):
                        return self.send(500, {"error": "INTERNAL"})
                    return self.send(200, {"status": "alive"})
                if path == "/readyz":
                    if stub.flags.get("ready_fail"):
                        return self.send(503, {"error": "NOT_READY", "message": "no", "traceId": "t", "retryable": True})
                    return self.send(200, {"status": "ready"})
                if not self.authorised():
                    return self.unauthorized()
                if path.startswith("/v1/evidence/"):
                    if stub.flags.get("evidence_404"):
                        return self.send(404, {"error": "NOT_FOUND", "message": "n", "traceId": "t", "retryable": False})
                    evidence_id = path[len("/v1/evidence/"):]
                    wrong = "evidence:other" if stub.flags.get("evidence_wrong_id") else evidence_id
                    return self.send(200, {"evidenceId": wrong, "sourceDataset": "SCHOLARCHAIN", "provenance": {} if stub.flags.get("no_provenance") else {"runId": "run:x"}})
                if path.startswith("/v1/queries/") and path.endswith("/evidence"):
                    ids = [EVIDENCE_ID] + (["evidence:extra-%d" % stub.counter] if stub.flags.get("duplicate_evidence") and stub.counter > 1 else [])
                    return self.send(200, {"queryId": QUERY_ID, "evidenceIds": ids})
                if path == "/v1/jobs/%s" % JOB_ID:
                    state = "FAILED" if stub.flags.get("job_failed") else ("RUNNING" if stub.flags.get("job_never") else "SUCCEEDED")
                    return self.send(200, {"jobId": JOB_ID, "queryId": QUERY_ID, "state": state, "stage": "x", "createdAt": "t", "updatedAt": "t", "resultUrl": None, "error": None})
                if path == "/v1/jobs/%s/result" % JOB_ID:
                    return self.send(200, self.answer())
                self.send(404, {"error": "NOT_FOUND", "message": "n", "traceId": "t", "retryable": False})

            def answer(self):
                claims = [{"claimId": "c1", "evidenceIds": [] if stub.flags.get("no_evidence_ids") else [EVIDENCE_ID]}]
                if stub.flags.get("no_claims"):
                    claims = []
                return {"queryId": QUERY_ID, "mode": "synchronous", "answer": {"summary": "A: publications: 3"}, "claims": claims, "links": {"explain": "e", "evidence": "v", "result": "r"}}

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                stub.requests.append(("POST", self.path, dict(self.headers)))
                if self.path != "/v1/query":
                    return self.send(404, {"error": "NOT_FOUND"})
                if stub.flags.get("accept_without_auth"):
                    pass
                elif not self.authorised():
                    return self.unauthorized()
                key = self.headers.get("Idempotency-Key")
                if not key:
                    return self.send(400, {"error": "BAD_REQUEST", "message": "m", "traceId": "t", "retryable": False})
                stub.counter += 1
                if stub.flags.get("accept_without_auth") and not self.authorised():
                    return self.send(200, self.answer())
                query_id = QUERY_ID
                if stub.flags.get("new_query_each_time") and key in stub.bound:
                    query_id = "qry-" + "ee" * 32
                stub.bound.setdefault(key, (body, query_id))
                if stub.flags.get("async"):
                    job = JOB_ID if not (stub.flags.get("new_job_each_time") and stub.counter > 1) else "job-" + "ff" * 32
                    return self.send(202, {"queryId": query_id, "mode": "asynchronous", "jobId": job, "status": "RUNNING", "statusUrl": "/v1/jobs/" + job})
                document = self.answer()
                document["queryId"] = query_id
                self.send(200, document)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self.port

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def paths(self):
        return [(m, urllib.parse.unquote(p)) for m, p, _h in self.requests]


class SmokeBase(Fixture):
    def start(self, **flags):
        stub = Stub(**flags)
        self.addCleanup(stub.stop)
        return stub

    def smoke(self, stub, *extra, key=KEY, name="SCHOLARCHAIN_SMOKE_API_KEY", url=None, **env):
        environ = {name: key} if key is not None else {}
        environ.update(env)
        return self.run_script("smoke-test.sh", "--url", url or stub.url, "--request-timeout", "3", *extra, **environ)

    def failed(self, result, step, code=4):
        self.assertEqual(result.rc, code, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: FAIL"), result.result_line())
        self.assertIn("step=%s" % step, result.result_line())
        self.assertEqual(result.steps()[-1], step, "the last STEP marker names the failed check")
        self.assertNotIn(KEY, result.out)


class SmokeStubTests(SmokeBase):
    def test_a_healthy_service_passes_every_check_with_its_markers(self):
        stub = self.start()
        result = self.smoke(stub)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(result.result_line(), "RESULT: PASS all 6 checks passed against %s" % stub.url)
        steps = [s for s in result.steps() if s.startswith("smoke-")]
        self.assertEqual(steps, ["smoke-healthz", "smoke-readyz", "smoke-query", "smoke-evidence", "smoke-idempotency", "smoke-error-path", "smoke-complete"])
        for name in ("healthz", "readyz", "query", "evidence", "idempotency", "error-path"):
            self.assertIn("CHECK-OK: %s:" % name, result.stdout)
        self.assertNotIn(KEY, result.out)

    def test_the_query_carries_the_idempotency_key_the_bearer_key_and_the_fixture_body(self):
        stub = self.start()
        self.assertEqual(self.smoke(stub).rc, 0)
        posts = [(p, h) for m, p, h in stub.requests if m == "POST"]
        self.assertEqual(len(posts), 4, "query, repeat, no key, invalid key")
        first, repeat = posts[0][1], posts[1][1]
        self.assertEqual(first["Authorization"], "Bearer " + KEY)
        self.assertTrue(first["Idempotency-Key"].startswith("smoke-"))
        self.assertEqual(first["Idempotency-Key"], repeat["Idempotency-Key"])
        self.assertNotIn("Authorization", posts[2][1], "the error path sends no key at all")
        self.assertNotEqual(posts[3][1]["Authorization"], "Bearer " + KEY, "the invalid key is not the real key")
        self.assertEqual(stub.bound[first["Idempotency-Key"]][0], json.dumps(FIXTURE_BODY).encode())

    def test_the_asynchronous_job_contract_is_followed(self):
        stub = self.start(**{"async": True})
        result = self.smoke(stub)
        self.assertEqual(result.rc, 0, result.out)
        paths = stub.paths()
        self.assertIn(("GET", "/v1/jobs/%s" % JOB_ID), paths)
        self.assertIn(("GET", "/v1/jobs/%s/result" % JOB_ID), paths)
        self.assertIn("job=%s" % JOB_ID, result.stdout)

    def test_a_failed_or_unfinished_job_fails_the_query_check(self):
        self.failed(self.smoke(self.start(**{"async": True, "job_failed": True})), "smoke-query")
        slow = self.smoke(self.start(**{"async": True, "job_never": True}), "--job-timeout", "1")
        self.failed(slow, "smoke-query", code=124)

    def test_a_custom_query_body_and_key_variable_name(self):
        stub = self.start()
        body = os.path.join(self.tmp, "body.json")
        with open(body, "w", encoding="utf-8") as handle:
            json.dump({"question": "another"}, handle)
        result = self.smoke(stub, "--query-body", body, "--api-key-env", "MY_OWN_KEY_VAR", key=None, MY_OWN_KEY_VAR=KEY)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(list(stub.bound.values())[0][0], json.dumps({"question": "another"}).encode())

    # ---- each failure mode fails with the marker of its own check ----------------------------------------------------------
    def test_healthz_failure(self):
        result = self.smoke(self.start(health_fail=True))
        self.failed(result, "smoke-healthz")
        self.assertIn("GET /healthz returned 500", result.stdout)

    def test_readiness_failure(self):
        stub = self.start(ready_fail=True)
        result = self.smoke(stub)
        self.failed(result, "smoke-readyz")
        self.assertIn("GET /readyz returned 503", result.stdout)
        self.assertNotIn(("POST", "/v1/query"), stub.paths(), "later checks do not run after a failure")

    def test_an_answer_without_claims_or_evidence_ids_fails_the_query_check(self):
        self.failed(self.smoke(self.start(no_claims=True)), "smoke-query")
        self.failed(self.smoke(self.start(no_evidence_ids=True)), "smoke-query")

    def test_evidence_failures(self):
        self.failed(self.smoke(self.start(evidence_404=True)), "smoke-evidence")
        self.failed(self.smoke(self.start(evidence_wrong_id=True)), "smoke-evidence")
        self.failed(self.smoke(self.start(no_provenance=True)), "smoke-evidence")

    def test_idempotency_failures(self):
        different = self.smoke(self.start(new_query_each_time=True))
        self.failed(different, "smoke-idempotency")
        self.assertIn("different queryId", different.stdout)
        self.failed(self.smoke(self.start(**{"async": True, "new_job_each_time": True})), "smoke-idempotency")
        self.failed(self.smoke(self.start(duplicate_evidence=True)), "smoke-idempotency")

    def test_error_path_failures(self):
        accepts = self.smoke(self.start(accept_without_auth=True))
        self.failed(accepts, "smoke-error-path")
        self.assertIn("without a key returned 200, expected 401", accepts.stdout)

    def test_an_error_body_that_echoes_the_key_fails_and_the_key_is_never_printed(self):
        result = self.smoke(self.start(echo_key=True))
        self.failed(result, "smoke-error-path")
        self.assertNotIn(KEY, result.out)

    def test_a_slow_endpoint_times_out_with_the_marker_and_exit_124(self):
        stub = self.start(**{"delay_/readyz": 3})
        result = self.run_script("smoke-test.sh", "--url", stub.url, "--request-timeout", "0.5", SCHOLARCHAIN_SMOKE_API_KEY=KEY)
        self.failed(result, "smoke-readyz", code=124)
        self.assertIn("timed out", result.stdout)

    def test_an_unreachable_target_fails_the_first_check(self):
        stub = self.start()
        url = stub.url
        stub.stop()
        result = self.smoke(stub, url=url)
        self.failed(result, "smoke-healthz")

    # ---- refusals before any request ------------------------------------------------------------------------------------------
    def test_no_key_in_the_environment_is_refused_before_any_request(self):
        stub = self.start()
        result = self.smoke(stub, key=None)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("holds no API key", result.out)
        self.assertEqual(stub.requests, [])

    def test_unsafe_target_urls_are_refused(self):
        stub = self.start()
        for url in ("http://example.com", "http://user:pw@127.0.0.1:1", "http://127.0.0.1:1/v1", "http://127.0.0.1:1/?x=1", "ftp://127.0.0.1", "127.0.0.1:8080"):
            with self.subTest(url):
                result = self.smoke(stub, url=url)
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn("SMOKE-URL-REFUSED", result.out)
        self.assertEqual(stub.requests, [])

    def test_usage_errors_exit_2(self):
        self.assertEqual(self.run_script("smoke-test.sh", SCHOLARCHAIN_SMOKE_API_KEY=KEY).rc, 2)
        self.assertEqual(self.run_script("smoke-test.sh", "--bogus").rc, 2)
        self.assertEqual(self.run_script("smoke-test.sh", "--url", "http://127.0.0.1:1", "--api-key-env", "bad name").rc, 2)

    def test_the_key_is_never_printed_even_when_the_tool_environment_echoes_it(self):
        stub = self.start()
        result = self.smoke(stub, FAKE_EMIT=KEY)
        self.assertEqual(result.rc, 0, result.out)
        self.assertNotIn(KEY, result.out)

    def test_help_documents_the_checks_and_exit_codes(self):
        text = subprocess.run(["bash", os.path.join(SCRIPTS_DIR, "smoke-test.sh"), "--help"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}).stdout
        for needle in ("smoke-healthz", "smoke-readyz", "smoke-query", "smoke-evidence", "smoke-idempotency", "smoke-error-path", "SCHOLARCHAIN_SMOKE_API_KEY", "Idempotency-Key", "Exit codes", "Human approval points", "loopback"):
            self.assertIn(needle, text)


class SmokeLocalTests(SmokeBase):
    """smoke-local.sh with a fake java that serves the stub contract: proves only the sha256 of the key reaches the service,
    the mode is offline-synthetic, the service is stopped and a missing distribution is refused."""

    FAKE_JAVA = '''#!/usr/bin/env python3
import hashlib, http.server, json, os, sys
if "-version" in sys.argv:
    sys.stderr.write('openjdk version "17.0.9" 2023-10-17\\n')
    sys.exit(0)
log = os.environ["FAKE_JAVA_LOG"]
with open(log, "w") as handle:
    handle.write(json.dumps({"mode": os.environ.get("SCHOLARCHAIN_SERVICE_MODE"), "hash": os.environ.get("SCHOLARCHAIN_API_KEY_SHA256"),
        "internal": os.environ.get("SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"), "host": os.environ.get("SCHOLARCHAIN_HTTP_HOST"), "port": os.environ.get("SCHOLARCHAIN_HTTP_PORT"),
        "argv": sys.argv[1:], "cwd": os.getcwd(), "env_names": sorted(os.environ)}))
want = os.environ["SCHOLARCHAIN_API_KEY_SHA256"]
QUERY = "qry-" + "ab" * 32
EVIDENCE = "evidence:metric:" + "cd" * 32
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, status, doc):
        data = json.dumps(doc).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def ok(self):
        token = self.headers.get("Authorization", "")[len("Bearer "):]
        return token != "" and hashlib.sha256(token.encode()).hexdigest() == want
    def err(self): self.send(401, {"error": "UNAUTHORIZED", "message": "m", "traceId": "t", "retryable": False})
    def do_GET(self):
        if self.path == "/healthz": return self.send(200, {"status": "alive"})
        if self.path == "/readyz": return self.send(200, {"status": "ready"})
        if not self.ok(): return self.err()
        if self.path.startswith("/v1/evidence/"): return self.send(200, {"evidenceId": self.path[len("/v1/evidence/"):], "sourceDataset": "S", "provenance": {"a": 1}})
        if self.path.endswith("/evidence"): return self.send(200, {"queryId": QUERY, "evidenceIds": [EVIDENCE]})
        self.send(404, {})
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if not self.ok(): return self.err()
        self.send(200, {"queryId": QUERY, "mode": "synchronous", "answer": {"summary": "s"}, "claims": [{"claimId": "c", "evidenceIds": [EVIDENCE]}], "links": {}})
http.server.ThreadingHTTPServer(("127.0.0.1", int(os.environ["SCHOLARCHAIN_HTTP_PORT"])), H).serve_forever()
'''

    def setUp(self):
        super().setUp()
        self.dist = os.path.join(self.repo, "modules", "services", "target", "distribution")
        self.javalog = os.path.join(self.tmp, "java-run.json")
        write_exec(os.path.join(self.jdk, "bin", "java"), self.FAKE_JAVA)

    def make_distribution(self):
        os.makedirs(os.path.join(self.dist, "lib"))
        os.makedirs(os.path.join(self.dist, "prompts", "runtime"))
        with open(os.path.join(self.dist, "services.jar"), "wb") as handle:
            handle.write(b"fake-services-jar")

    def local(self, *extra, **env):
        return self.run_script("smoke-local.sh", *extra, FAKE_JAVA_LOG=self.javalog, **env)

    def test_a_missing_distribution_is_refused_with_the_build_hint(self):
        result = self.local()
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("sbt -batch packageServices", result.out)
        self.assertFalse(os.path.exists(self.javalog), "the service was never started")

    def test_the_service_gets_only_the_key_hash_in_offline_synthetic_mode_and_all_checks_pass(self):
        self.make_distribution()
        result = self.local("--startup-seconds", "20")
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PASS local offline-synthetic query-api passed all smoke checks"), result.result_line())
        for marker in ("smoke| STEP: smoke-healthz", "smoke| STEP: smoke-error-path", "smoke| RESULT: PASS all 6 checks"):
            self.assertIn(marker, result.stdout)
        with open(self.javalog, encoding="utf-8") as handle:
            run = json.load(handle)
        self.assertEqual(run["mode"], "offline-synthetic")
        self.assertRegex(run["hash"], r"^[0-9a-f]{64}$")
        self.assertRegex(run["internal"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(run["hash"], run["internal"], "the two credentials are distinct")
        self.assertEqual(run["host"], "127.0.0.1")
        self.assertEqual(run["argv"][-1], "edu.uic.cs441.scholarchain.services.QueryApiMain")
        self.assertIn("services.jar:lib/*", run["argv"])
        self.assertTrue(run["cwd"].endswith("modules/services/target/distribution"))
        self.assertNotIn("SCHOLARCHAIN_SMOKE_API_KEY", run["env_names"], "the raw key is not in the service environment")
        self.assertNotIn("SCHOLARCHAIN_API_KEY", run["env_names"])
        self.assertTrue(self.tree_clean_local())

    def tree_clean_local(self):
        return subprocess.run(["git", "-C", self.repo, "status", "--porcelain=v1", "--untracked-files=all"], capture_output=True, text=True).stdout.strip() == ""

    def test_the_key_hash_is_the_hash_of_a_key_the_script_never_prints(self):
        self.make_distribution()
        result = self.local("--startup-seconds", "20")
        self.assertEqual(result.rc, 0, result.out)
        with open(self.javalog, encoding="utf-8") as handle:
            run = json.load(handle)
        self.assertNotIn(run["hash"] + "x", result.out)
        self.assertNotRegex(result.out, r"smoke-[A-Za-z0-9_-]{40,}")
        self.assertNotRegex(result.out, r"internal-[A-Za-z0-9_-]{40,}")

    def test_the_service_process_is_stopped_after_the_run(self):
        self.make_distribution()
        result = self.local("--startup-seconds", "20")
        self.assertEqual(result.rc, 0, result.out)
        with open(self.javalog, encoding="utf-8") as handle:
            port = int(json.load(handle)["port"])
        time.sleep(0.5)
        import socket

        with socket.socket() as probe:
            probe.settimeout(1)
            self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0, "the port must be closed after the run")

    def test_a_service_that_never_becomes_healthy_is_refused_and_stopped(self):
        self.make_distribution()
        write_exec(os.path.join(self.jdk, "bin", "java"), '#!/bin/bash\nif [[ "$*" == *-version* ]]; then echo \'openjdk version "17.0.9" 2023-10-17\' >&2; exit 0; fi\nsleep 30\n')
        result = self.local("--startup-seconds", "2")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("did not become healthy", result.out)

    def test_help_and_usage_errors(self):
        text = subprocess.run(["bash", os.path.join(SCRIPTS_DIR, "smoke-local.sh"), "--help"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}).stdout
        for needle in ("offline-synthetic", "throwaway", "SCHOLARCHAIN_API_KEY_SHA256", "Exit codes", "Human approval points", "Evidence produced", "--build"):
            self.assertIn(needle, text)
        self.assertEqual(self.run_script("smoke-local.sh", "--bogus").rc, 2)
        self.assertEqual(self.run_script("smoke-local.sh", "--port", "x").rc, 2)


if __name__ == "__main__":
    unittest.main()

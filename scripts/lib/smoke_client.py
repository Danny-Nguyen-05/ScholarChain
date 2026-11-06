#!/usr/bin/env python3
"""HTTP checks for scripts/smoke-test.sh (stdlib http.client; python3 -I). Never prints the API key.

  validate-url URL               exit 0 when URL is http(s)://host[:port][/] with no user-info, query or fragment, and
                                 plain http only for a loopback host (a bearer key is never sent in clear to a remote host)
  check NAME --url URL --state FILE --key-env VAR [--body-file F] [--request-timeout S] [--job-timeout S] [--idem-key K]
        NAME is one of healthz, readyz, query, evidence, idempotency, error-path. Prints one "CHECK-OK: ..." line on
        success (exit 0), or "CHECK-FAILED: ..." (exit 1; exit 124 when a request or job timed out). The API key is read
        from the environment variable named by --key-env; its value never reaches stdout, stderr or the state file.
        Checks share a JSON state file (query id, job id, evidence ids, the first response fingerprint).

Contract (modules/services/README.md and the OpenAPI file):
  GET  /healthz                 200 {"status":"alive"}                      (no authentication)
  GET  /readyz                  200 {"status":"ready"}                      (no authentication)
  POST /v1/query                Authorization: Bearer <key>, Idempotency-Key: <key>, JSON body; 200 QueryResponse
                                {queryId, mode:"synchronous", answer:{summary}, claims:[{claimId, evidenceIds}], links}
                                or 202 JobReference {queryId, jobId, status, statusUrl}: GET /v1/jobs/{jobId} until
                                state SUCCEEDED, then GET /v1/jobs/{jobId}/result
  GET  /v1/evidence/{evidenceId}            200 Evidence {evidenceId, sourceDataset, provenance, ...}
  GET  /v1/queries/{queryId}/evidence       200 {queryId, evidenceIds}
  401 on a missing or invalid key           {error:"UNAUTHORIZED", message, traceId, retryable}
"""
import argparse
import http.client
import json
import os
import re
import sys
import time
import urllib.parse

MAX_BODY = 1048576
DEFAULT_BODY = {"question": "Synthetic fixture: publication count for A", "output": {"includeScores": False}}
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class CheckFailed(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


def parse_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise CheckFailed("the target URL must be http(s)://host[:port]")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise CheckFailed("the target URL must not hold user-info, a path, a query or a fragment")
    if parts.scheme == "http" and parts.hostname not in LOOPBACK:
        raise CheckFailed("plain http is accepted only for a loopback host; use https for a remote target")
    try:
        port = parts.port
    except ValueError:
        raise CheckFailed("the target URL has an invalid port")
    return parts.scheme, parts.hostname, port


class Client:
    def __init__(self, url, timeout, key):
        self.scheme, self.host, self.port = parse_url(url)
        self.timeout = timeout
        self.key = key

    def request(self, method, path, headers=None, body=None, auth=True, key_override=None):
        """Returns (status, headers dict, parsed JSON or None, raw text). Raises CheckFailed on timeout or transport error."""
        conn_class = http.client.HTTPSConnection if self.scheme == "https" else http.client.HTTPConnection
        connection = conn_class(self.host, self.port, timeout=self.timeout)
        send = dict(headers or {})
        key = self.key if key_override is None else key_override
        if auth and key:
            send["Authorization"] = "Bearer " + key
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            send["Content-Type"] = "application/json"
        try:
            connection.request(method, path, body=payload, headers=send)
            response = connection.getresponse()
            data = response.read(MAX_BODY + 1)
        except (TimeoutError, OSError) as error:
            if isinstance(error, TimeoutError) or "timed out" in str(error):
                raise CheckFailed("%s %s timed out after %ss" % (method, path, self.timeout), 124)
            raise CheckFailed("%s %s failed: %s" % (method, path, type(error).__name__))
        finally:
            connection.close()
        if len(data) > MAX_BODY:
            raise CheckFailed("%s %s returned more than %d bytes" % (method, path, MAX_BODY))
        text = data.decode("utf-8", errors="replace")
        parsed = None
        try:
            parsed = json.loads(text)
        except ValueError:
            pass
        return response.status, {k.lower(): v for k, v in response.getheaders()}, parsed, text


def load_state(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def save_state(path, state):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def expect(condition, message):
    if not condition:
        raise CheckFailed(message)


def query_body(args):
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as handle:
            return json.load(handle)
    return DEFAULT_BODY


def post_query(client, body, idem_key, auth=True, key_override=None):
    return client.request("POST", "/v1/query", headers={"Idempotency-Key": idem_key}, body=body, auth=auth, key_override=key_override)


def settle(client, status, parsed, args):
    """Follows the asynchronous job contract. Returns (queryId, jobId or None, QueryResponse dict)."""
    if status == 200:
        expect(isinstance(parsed, dict) and parsed.get("mode") == "synchronous", "a 200 query response must be a synchronous QueryResponse")
        return parsed["queryId"], None, parsed
    expect(status == 202 and isinstance(parsed, dict) and "jobId" in parsed and "queryId" in parsed, "POST /v1/query returned %s, not a 200 answer or a 202 job reference" % status)
    job_id = parsed["jobId"]
    expect(re.match(r"^[A-Za-z0-9:_.-]{1,200}$", job_id) is not None, "the job id is not a safe token")
    deadline = time.monotonic() + args.job_timeout
    quoted = urllib.parse.quote(job_id, safe=":")
    while True:
        job_status, _h, job, _t = client.request("GET", "/v1/jobs/%s" % quoted)
        expect(job_status == 200 and isinstance(job, dict), "GET /v1/jobs/{jobId} returned %s" % job_status)
        state = job.get("state")
        if state == "SUCCEEDED":
            break
        expect(state in ("QUEUED", "RUNNING"), "the job ended in state %s" % state)
        if time.monotonic() > deadline:
            raise CheckFailed("the job did not finish within %ss" % args.job_timeout, 124)
        time.sleep(0.5)
    result_status, _h, result, _t = client.request("GET", "/v1/jobs/%s/result" % quoted)
    expect(result_status == 200 and isinstance(result, dict), "GET /v1/jobs/{jobId}/result returned %s" % result_status)
    return parsed["queryId"], job_id, result


def check_healthz(client, args, state):
    status, _h, parsed, _t = client.request("GET", "/healthz", auth=False)
    expect(status == 200, "GET /healthz returned %s, expected 200" % status)
    expect(isinstance(parsed, dict) and parsed.get("status") == "alive", "GET /healthz did not report status alive")
    return "GET /healthz 200 status=alive"


def check_readyz(client, args, state):
    status, _h, parsed, _t = client.request("GET", "/readyz", auth=False)
    expect(status == 200, "GET /readyz returned %s, expected 200 (the service is not ready)" % status)
    expect(isinstance(parsed, dict) and parsed.get("status") == "ready", "GET /readyz did not report status ready")
    return "GET /readyz 200 status=ready"


def check_query(client, args, state):
    expect(bool(args.idem_key), "an idempotency key is required")
    status, _h, parsed, _t = post_query(client, query_body(args), args.idem_key)
    query_id, job_id, answer = settle(client, status, parsed, args)
    expect(isinstance(query_id, str) and query_id, "the response has no queryId")
    expect(isinstance(answer.get("answer"), dict) and isinstance(answer["answer"].get("summary"), str), "the answer has no summary")
    claims = answer.get("claims")
    expect(isinstance(claims, list) and claims, "the answer holds no claims to fetch evidence for")
    evidence_ids = []
    for claim in claims:
        expect(isinstance(claim, dict), "a claim is not an object")
        for evidence_id in claim.get("evidenceIds") or []:
            expect(isinstance(evidence_id, str) and evidence_id, "a claim lists a malformed evidence id")
            evidence_ids.append(evidence_id)
    expect(evidence_ids, "no claim cites an evidence id")
    state.update({"query_id": query_id, "job_id": job_id, "evidence_ids": evidence_ids, "claim_count": len(claims), "idem_key": args.idem_key})
    return "POST /v1/query %s queryId=%s claims=%d evidence_ids=%d%s" % (status, query_id, len(claims), len(evidence_ids), " job=%s" % job_id if job_id else "")


def check_evidence(client, args, state):
    expect(state.get("evidence_ids"), "no evidence id from the query check")
    evidence_id = state["evidence_ids"][0]
    status, _h, parsed, _t = client.request("GET", "/v1/evidence/%s" % urllib.parse.quote(evidence_id, safe=":"))
    expect(status == 200, "GET /v1/evidence/{id} returned %s, expected 200" % status)
    expect(isinstance(parsed, dict) and parsed.get("evidenceId") == evidence_id, "the evidence item does not carry the requested evidenceId")
    expect(isinstance(parsed.get("sourceDataset"), str) and parsed["sourceDataset"], "the evidence item has no sourceDataset")
    expect(isinstance(parsed.get("provenance"), dict) and parsed["provenance"], "the evidence item has no provenance")
    state["evidence_checked"] = evidence_id
    return "GET /v1/evidence/{id} 200 evidenceId matches, source=%s, provenance present" % parsed["sourceDataset"]


def evidence_list(client, query_id):
    status, _h, parsed, _t = client.request("GET", "/v1/queries/%s/evidence" % urllib.parse.quote(query_id, safe=":"))
    expect(status == 200 and isinstance(parsed, dict) and isinstance(parsed.get("evidenceIds"), list), "GET /v1/queries/{id}/evidence returned %s" % status)
    return sorted(parsed["evidenceIds"])


def check_idempotency(client, args, state):
    expect(state.get("query_id") and state.get("idem_key"), "no query id from the query check")
    before = evidence_list(client, state["query_id"])
    status, _h, parsed, _t = post_query(client, query_body(args), state["idem_key"])
    query_id, job_id, _answer = settle(client, status, parsed, args)
    expect(query_id == state["query_id"], "a repeated request with the same Idempotency-Key produced a different queryId (a duplicate query)")
    expect(job_id == state.get("job_id"), "a repeated request with the same Idempotency-Key produced a different job id")
    after = evidence_list(client, state["query_id"])
    expect(before == after, "the repeated request changed the stored evidence list (a duplicate)")
    return "repeat with the same Idempotency-Key returned the same queryId%s and the same %d evidence id(s)" % (" and job" if job_id else "", len(after))


def check_error_path(client, args, state):
    body = query_body(args)
    key = "smoke-401-%d" % int(time.time())
    status, _h, parsed, text = post_query(client, body, key, auth=False)
    expect(status == 401, "POST /v1/query without a key returned %s, expected 401" % status)
    expect(isinstance(parsed, dict) and parsed.get("error") == "UNAUTHORIZED" and parsed.get("retryable") is False, "the 401 body is not the typed UNAUTHORIZED error")
    bad = "invalid-" + "x" * 24
    status2, _h2, parsed2, text2 = post_query(client, body, key + "b", key_override=bad)
    expect(status2 == 401, "POST /v1/query with an invalid key returned %s, expected 401" % status2)
    secret = client.key or ""
    expect(not secret or (secret not in text and secret not in text2), "an error body echoed the API key")
    return "POST /v1/query without a key and with an invalid key both returned 401 UNAUTHORIZED"


CHECKS = {
    "healthz": check_healthz,
    "readyz": check_readyz,
    "query": check_query,
    "evidence": check_evidence,
    "idempotency": check_idempotency,
    "error-path": check_error_path,
}
NEEDS_KEY = {"query", "evidence", "idempotency", "error-path"}


def cmd_check(args):
    key = os.environ.get(args.key_env, "") if args.key_env else ""
    try:
        if args.name in NEEDS_KEY and not key:
            raise CheckFailed("the environment variable %s holds no API key" % args.key_env)
        client = Client(args.url, args.request_timeout, key)
        state = load_state(args.state)
        message = CHECKS[args.name](client, args, state)
        save_state(args.state, state)
    except CheckFailed as error:
        print("CHECK-FAILED: %s: %s" % (args.name, error))
        return error.code
    except (KeyError, TypeError, ValueError) as error:
        print("CHECK-FAILED: %s: unexpected response shape (%s)" % (args.name, type(error).__name__))
        return 1
    print("CHECK-OK: %s: %s" % (args.name, message))
    return 0


def cmd_validate_url(args):
    try:
        parse_url(args.url)
    except CheckFailed as error:
        print("SMOKE-URL-REFUSED: %s" % error)
        return 1
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate-url")
    p.add_argument("url")
    p.set_defaults(fn=cmd_validate_url)
    p = sub.add_parser("check")
    p.add_argument("name", choices=sorted(CHECKS))
    p.add_argument("--url", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--key-env", default="")
    p.add_argument("--body-file", default="")
    p.add_argument("--request-timeout", type=float, default=10.0)
    p.add_argument("--job-timeout", type=float, default=60.0)
    p.add_argument("--idem-key", default="")
    p.set_defaults(fn=cmd_check)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))

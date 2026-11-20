#!/usr/bin/env python3
"""Q12 benchmark runner: the 33 fixed questions through POST /v1/query, with the evidence trail, charged to answer bucket 16b (python3 -I; stdlib only).

A parameterised variant of load-tests/eval16b.py (same plan/run commands, same hard stops, same ledger charging before every request, same
raw-result sealing); it differs only in what it asks and records:
  questions   experiments/inputs/q12/questions.txt (33 questions, 3 per type x 11 types, ids q01..q33 in file order); refused when the
              file is not the one pinned by experiments/manifests/q12-benchmark.json (sha256), so the scorer's key always matches;
  per answer  after the answer it ALSO fetches GET /v1/explain/{queryId} and GET /v1/evidence/{id} for every evidence id cited by the
              answer's claims or by the explain body (at most 60 ids per question; GET requests, no model call, no ledger charge) and
              keeps the raw responses in answers.jsonl: qid, status, answer, explain {status, body}, evidence {id: {status, item}}.
Cost: 33 answers x USD 0.001365 = USD 0.045045 (estimate, not metered) from bucket 16b. Bucket 16b is a hard stop: it must hold 33 answers
(after the human-approved transfer APPROVED_LLM_TRANSFER=15b->16b:33 applied through load-tests/llm_budget.py transfer; this program never
creates or applies an approval). Do NOT also run `llm_budget.py reserve --bucket 16b` for it: the run charges the ledger itself.

  python3 -I load-tests/evalq12.py plan                       # no network; questions, bucket state, estimated cost
  python3 -I load-tests/evalq12.py run --run-id <run-id>      # needs SCHOLARCHAIN_LOAD_BASE_URL (loopback http or https) and SCHOLARCHAIN_LOAD_API_KEY

The API key is read only from the environment variable named by --api-key-env (default SCHOLARCHAIN_LOAD_API_KEY); never a CLI argument.
Run with shell tracing off (set +x). Raw results (git-ignored, sealed): target/experiment-runs/q12-benchmark-<run-id>/raw/ (answers.jsonl,
events.jsonl, run-record.json, raw.sha256). Score them with experiments/scripts/q12_score.py. All other options and exit codes: eval16b.py.
"""
import hashlib
import importlib.util
import json
import os
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
_spec = importlib.util.spec_from_file_location("eval16b_for_evalq12", os.path.join(HERE, "eval16b.py"))
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)
loadgen = ev.loadgen
Refused = ev.Refused

EXPERIMENT_ID = "q12-benchmark"
DEFAULT_QUESTIONS = os.path.join(REPO, "experiments", "inputs", "q12", "questions.txt")
MANIFEST = os.path.join(REPO, "experiments", "manifests", "q12-benchmark.json")
MAX_EVIDENCE_PER_QUESTION = 60
MAX_ITEM_BYTES = 65536
MAX_EXPLAIN_BYTES = 262144


def cited_evidence_ids(answer, explain):
    ids = []
    claims = answer.get("claims") if isinstance(answer, dict) else None
    for claim in claims if isinstance(claims, list) else []:
        if isinstance(claim, dict):
            ids.extend(e for e in claim.get("evidenceIds") or [] if isinstance(e, str))
    if isinstance(explain, dict):
        ids.extend(e for e in explain.get("evidenceIds") or [] if isinstance(e, str))
    seen, out = set(), []
    for e in ids:
        if e not in seen and 0 < len(e) <= 300:
            seen.add(e)
            out.append(e)
    return out


class Q12Evaluator(ev.Evaluator):
    """eval16b.Evaluator that also records the explain body and the cited evidence items of every answer."""

    def ask(self, client, index, question):
        cfg = self.cfg
        idem = ("q12-%s-%d" % (cfg["run_id"], index))[:256]
        body = json.dumps({"question": question, "output": {"includeScores": False}}).encode("utf-8")
        started_wall = time.time()
        error, status, nbytes, data, latency = self.request(
            client, "POST", "/v1/query", True, body=body, extra={"Content-Type": "application/json", "Idempotency-Key": idem},
            timeout=cfg["profile"]["limits"]["llm_request_timeout_seconds"], rid="%s-%d" % (cfg["run_id"], index))
        row = {"schema": "scholarchain.evalq12-answer.v1", "run_id": cfg["run_id"], "index": index, "qid": "q%02d" % index, "question": question,
               "question_sha256": ev.sha256_text(question), "idempotency_key": idem, "started_utc": loadgen.stamp(started_wall),
               "status": status, "outcome": loadgen.classify(status, error), "latency_ms": latency, "bytes": nbytes,
               "query_id": None, "job_id": None, "job_state": None, "answer_sha256": None, "answer_bytes": None, "answer": None,
               "explain": None, "evidence": {}, "evidence_ids_skipped": 0}
        parsed = ev.read_json_body(data) if 200 <= status < 300 else None
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
            if len(raw) <= ev.MAX_ANSWER_BYTES:
                row["answer"] = final
        if row["outcome"] == "ok" and status == 202 and row["job_state"] not in ev.DONE_OK:
            row["outcome"] = "job_not_done"
        if row["query_id"] is None and isinstance(final, dict) and isinstance(final.get("queryId"), str) and loadgen.SAFE_ID.match(final["queryId"]):
            row["query_id"] = final["queryId"]
        if row["query_id"]:
            self.record_trail(client, row, final, index)
        self.answers_file.write(loadgen.jdump(row) + "\n")
        self.answers_file.flush()
        self.rows.append(row)
        return row

    def get_json(self, client, path, rid, limit):
        timeout = self.cfg["profile"]["limits"]["request_timeout_seconds"]
        error, status, nbytes, data, _ms = self.request(client, "GET", path, True, timeout=timeout, rid=rid)
        parsed = ev.read_json_body(data) if 200 <= status < 300 else None
        if isinstance(parsed, (dict, list)) and len(json.dumps(parsed, separators=(",", ":"))) > limit:
            return status, None
        return status, parsed

    def record_trail(self, client, row, final, index):
        query = urllib.parse.quote(row["query_id"], safe="")
        status, body = self.get_json(client, "/v1/explain/" + query, "%s-%d-explain" % (self.cfg["run_id"], index), MAX_EXPLAIN_BYTES)
        row["explain"] = {"status": status, "body": body}
        ids = cited_evidence_ids(final, body)
        row["evidence_ids_skipped"] = max(0, len(ids) - MAX_EVIDENCE_PER_QUESTION)
        for n, evidence_id in enumerate(ids[:MAX_EVIDENCE_PER_QUESTION]):
            status, item = self.get_json(client, "/v1/evidence/" + urllib.parse.quote(evidence_id, safe=""), "%s-%d-ev%d" % (self.cfg["run_id"], index, n), MAX_ITEM_BYTES)
            row["evidence"][evidence_id] = {"status": status, "item": item}


def check_pinned_questions(argv):
    """The default questions file must be the one the manifest pins; another file (a smoke test with --questions-file) is the caller's choice."""
    path = DEFAULT_QUESTIONS
    for i, arg in enumerate(argv):
        if arg == "--questions-file" and i + 1 < len(argv):
            path = argv[i + 1]
        elif arg.startswith("--questions-file="):
            path = arg.split("=", 1)[1]
    if os.path.abspath(path) != os.path.abspath(DEFAULT_QUESTIONS):
        return
    with open(MANIFEST, encoding="utf-8") as handle:
        pinned = json.load(handle)["questions"]["sha256"]
    if loadgen.sha256_file(path) != pinned:
        raise Refused("experiments/inputs/q12/questions.txt differs from the sha256 pinned in experiments/manifests/q12-benchmark.json; "
                      "re-derive the inputs and the answer key together and update the manifest")


def main(argv, out=None):
    ev.EXPERIMENT_ID = EXPERIMENT_ID
    ev.DEFAULT_QUESTIONS = DEFAULT_QUESTIONS
    ev.MANIFEST = MANIFEST
    ev.Evaluator = Q12Evaluator
    try:
        check_pinned_questions(argv)
    except (Refused, OSError, ValueError, KeyError) as error:
        sys.stderr.write("REFUSED: %s\n" % error)
        return 3
    return ev.main(argv, out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

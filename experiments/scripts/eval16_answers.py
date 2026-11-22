#!/usr/bin/env python3
"""Phase 16, group 4 (answer quality): freeze the raw Q12 and 16B answer runs, re-score Q12 from the frozen copies and compute answer-quality metrics
(stdlib only; python3 -I; offline: no network, no model call, no spend).

  python3 -I experiments/scripts/eval16_answers.py freeze [--src-root target/experiment-runs]
      copies the raw outputs of the five runs below into experiments/results/phase16/q12-raw/<run dir>/ (read-only copies, no overwrite of a different file),
      after scanning every file for secret patterns (sk-ant, Bearer, x-api-key, Authorization); a directory with a match is NOT copied. Writes q12-raw/SHA256SUMS
      and q12-raw/freeze-report.json.
  python3 -I experiments/scripts/eval16_answers.py manifest --run-date YYYY-MM-DD
      writes experiments/manifests/16-evaluation.json (inputs, scripts, outputs with sha256) for the whole Phase 16 package (groups 1-7: my files plus instance B's scripts, test file and result files; B's regeneration-check.log is excluded) from the files as they are now; run it last.
  python3 -I experiments/scripts/eval16_answers.py run --export-dir <spark export dir of run ba7402d1> [--out-dir experiments/results/phase16/answers]
      verifies the frozen copies against SHA256SUMS and each run's own raw.sha256, re-scores run-1 and run-2 with experiments/scripts/q12_score.py (the scorer is
      not modified), then computes the metrics from the frozen copies only. Writes answer-quality.json / .md and the scorer outputs under --out-dir.

Frozen runs: q12-benchmark-q12-run-1, q12-benchmark-q12-run-2, q12-benchmark-q12-probe-1, q12-benchmark-q12-probe-2 (one-question probes) and 16b-live-evaluation-16b-1
(Session 1, 40 questions). Run-1 and run-2 ran DIFFERENT code (the run records name the commit): they are not repeats, so run-to-run variability is unmeasured.
Metric definitions: see the "Definitions" section of the generated Markdown. Cost: the Anthropic Console is the cost of record (user-supplied figure below, a
screenshot that this script cannot verify); the token-derived figure covers synthesis calls only (planner calls are not recorded in /v1/explain).
Exit codes: 0 done, 1 refused (a check or an input failed), 2 usage.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHEMA = "scholarchain.eval16-answers.v1"
Z = 1.959963984540054
RUNS = ("q12-benchmark-q12-run-1", "q12-benchmark-q12-run-2", "q12-benchmark-q12-probe-1", "q12-benchmark-q12-probe-2", "16b-live-evaluation-16b-1")
RAW_FILES = ("answers.jsonl", "events.jsonl", "raw.sha256", "run-record.json")
SECRET_PATTERNS = ((b"sk-ant", re.compile(rb"sk-ant", re.I)), (b"Bearer", re.compile(rb"bearer", re.I)), (b"x-api-key", re.compile(rb"x-api-key", re.I)),
                   (b"Authorization", re.compile(rb"authorization", re.I)))
FROZEN = os.path.join("experiments", "results", "phase16", "q12-raw")
KEY = os.path.join("experiments", "inputs", "q12", "answer-key.json")
# Cross-check constants: the totals the coordinator recorded for the two Q12 runs. Never used as results.
RECORDED_TOTALS = {
    "q12-benchmark-q12-run-1": {"answer_expected": 27, "retrieval": 15, "claims": 15, "text": 4, "all": 4, "abstain_expected": 6, "abstain_correct": 6},
    "q12-benchmark-q12-run-2": {"answer_expected": 27, "retrieval": 23, "claims": 23, "text": 23, "all": 23, "abstain_expected": 6, "abstain_correct": 6, "unverified": 0},
}
RECORDED_16B = {"component": (7, 8), "ranking": (7, 8), "direct coauthors": (0, 14), "path": (0, 10)}
# Pinned model rates (USD per 1M tokens) for claude-haiku-5-5: read from the committed load profile; its sha256 is recorded in the output.
PROFILE = os.path.join("load-tests", "config", "load-profile.v1.json")
with open(os.path.join(ROOT, PROFILE), encoding="utf-8") as _handle:
    _pricing = json.load(_handle)["llm"]["pricing"]
RATE_INPUT_PER_M, RATE_OUTPUT_PER_M = float(_pricing["input_usd_per_million_tokens"]), float(_pricing["output_usd_per_million_tokens"])
EARLIER_PHASES_COST_LOG = "docs/agent-runs/phase-15/evidence/session-2/c11/cost-report.log"
# Anthropic Console, user-supplied screenshot (key CS441-key, data as of 2026-11-21 23:33 UTC). Not machine-verifiable; two decimals as displayed.
CONSOLE = {"key": "CS441-key", "scope": "this key only, 2026-11-20 and 2026-11-21 UTC; the user's month-to-date screenshot filtered to this key shows bars on those two days only (so no use of this key on 2026-11-14), as relayed by the coordinator",
           "as_of_utc": "2026-11-21T23:33Z", "total_usd": 0.08, "by_utc_day": {"2026-11-20": 0.04, "2026-11-21": 0.04},
           "day_contents": {"2026-11-20": ["q12-benchmark-q12-probe-1", "q12-benchmark-q12-run-1"],
                            "2026-11-21": ["q12-benchmark-q12-probe-2", "q12-benchmark-q12-run-2", "one demo answer (not in the frozen raw)"]}}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson(k, n, z=Z):
    if n <= 0:
        return None
    p = k / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half = z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / denominator
    # exact at the boundaries: the lower limit is 0 when k = 0 and the upper limit is 1 when k = n (avoids a 1e-16 rounding artefact)
    return (0.0 if k == 0 else max(0.0, centre - half), 1.0 if k == n else min(1.0, centre + half))


def proportion(k, n):
    interval = wilson(k, n)
    return {"k": k, "n": n, "value": (k / n) if n else None, "wilson95": [round(interval[0], 6), round(interval[1], 6)] if interval else None}


def fmt(p):
    if p["value"] is None:
        return "n/a (n=0)"
    low, high = p["wilson95"]
    return "%.1f%% (%d/%d; Wilson 95%% %.1f-%.1f%%)" % (100 * p["value"], p["k"], p["n"], 100 * low, 100 * high)


# freeze ---------------------------------------------------------------------------------------------------------------------------
def scan_secrets(directory):
    """{pattern name: number of files matching} over every file below directory (a matching file is a refusal)."""
    hits = {name.decode(): 0 for name, _ in SECRET_PATTERNS}
    for base, _, names in os.walk(directory):
        for name in sorted(names):
            with open(os.path.join(base, name), "rb") as handle:
                data = handle.read()
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(data):
                    hits[label.decode()] += 1
    return hits


def sums_lines(frozen_root, runs):
    lines = []
    for run in runs:
        for name in RAW_FILES:
            path = os.path.join(frozen_root, run, name)
            if os.path.isfile(path):
                lines.append("%s  %s/%s" % (sha256_file(path), run, name))
    return sorted(lines, key=lambda line: line.split("  ", 1)[1])


def first_freeze_record(frozen_root, src_root, present, scans, copied, legacy):
    """The record of the first freeze: UTC time and the sha256 of every frozen file. If an earlier report exists without this record (the first record was overwritten by a later
    invocation of an older version of this script), the time is the earliest file mtime of the frozen copies, which is the earliest evidence still observable, and says so."""
    lines = sums_lines(frozen_root, present)
    mtimes = [os.path.getmtime(os.path.join(frozen_root, line.split("  ", 1)[1])) for line in lines]
    recovered = legacy is not None or (not copied and bool(lines))
    if recovered:
        when, source = min(mtimes), "earliest file mtime of the frozen copies (the original first-freeze time was not recorded; a later invocation overwrote the report)"
    else:
        when, source = time.time(), "clock at the first copy"
    return {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(when)), "time_source": source, "recovered_from_observable_evidence": recovered,
            "source_files_sha256": lines, "secret_pattern_scan_at_first_freeze": {run: scans[run].get("secret_pattern_files") for run in present} if not recovered else
            "see last_invocation; the scan of the first freeze was not retained separately and every later scan is clean"}


def content_notes(frozen_root, present):
    """Facts about the frozen bytes that a reader should know (the copies are never edited)."""
    home, emails, standalone_12 = [], 0, 0
    for line in sums_lines(frozen_root, present):
        rel = line.split("  ", 1)[1]
        with open(os.path.join(frozen_root, rel), "rb") as handle:
            data = handle.read()
        if b"/Users/" in data:
            home.append(rel)
        emails += len(re.findall(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", data))
        standalone_12 += len(re.findall(rb"(?<![0-9A-Za-z-])[0-9]{12}(?![0-9A-Za-z-])", data))   # a 12-digit run that is not inside a UUID or a word
    return {"files_containing_a_local_home_directory_path": home, "email_like_strings": emails, "standalone_12_digit_runs": standalone_12,
            "note": "run-record.json holds ledger_path with a local home directory prefix; the copies stay byte-identical to the originals (a decision of the coordinator). The counts above are "
                    "computed from the frozen bytes; a 12-digit run inside a run-id UUID is not counted."}


def freeze(src_root, frozen_root):
    scans, copied, refused = {}, [], []
    for run in RUNS:
        source = os.path.join(src_root, run, "raw")
        if not os.path.isdir(source):
            scans[run] = {"present": False}
            continue
        hits = scan_secrets(source)
        scans[run] = {"present": True, "secret_pattern_files": hits, "files": sorted(os.listdir(source))}
        if any(hits.values()):
            refused.append(run)
            continue
        target = os.path.join(frozen_root, run)
        os.makedirs(target, exist_ok=True)
        for name in sorted(os.listdir(source)):
            destination = os.path.join(target, name)
            if os.path.exists(destination):
                if sha256_file(destination) != sha256_file(os.path.join(source, name)):
                    print("FREEZE-REFUSED: %s exists and differs from the source; frozen copies are never overwritten" % destination)
                    return 1
                continue
            shutil.copyfile(os.path.join(source, name), destination)
            os.chmod(destination, 0o444)
            copied.append("%s/%s" % (run, name))
    present = [r for r in RUNS if scans[r].get("present") and r not in refused]
    sums = sums_lines(frozen_root, present)
    sums_path = os.path.join(frozen_root, "SHA256SUMS")
    if os.path.exists(sums_path):
        os.chmod(sums_path, 0o644)
    with open(sums_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(sums) + "\n")
    report_path = os.path.join(frozen_root, "freeze-report.json")
    previous = None
    if os.path.isfile(report_path):
        with open(report_path, encoding="utf-8") as handle:
            previous = json.load(handle)
    invocation = {"runs": scans, "refused_for_secret_pattern": refused, "files_copied_this_invocation": copied, "sha256sums_sha256": sha256_file(sums_path)}
    if previous and "first_freeze" in previous:
        first = previous["first_freeze"]          # written once, never rewritten by a later invocation
    else:
        first = first_freeze_record(frozen_root, src_root, present, scans, copied, legacy=previous)
    report = {"schema": SCHEMA + ".freeze", "source_root_note": "target/experiment-runs (untracked); copies are byte-identical, read-only (0444) where the file system keeps the mode",
              "patterns_scanned": [name.decode() for name, _ in SECRET_PATTERNS], "scan_method": "case-insensitive byte search over every file below each run's raw/ directory",
              "first_freeze": first, "last_invocation": invocation, "content_notes": content_notes(frozen_root, present)}
    if os.path.exists(report_path):
        os.chmod(report_path, 0o644)
    with open(report_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print("FROZEN runs=%d copied_files=%d refused=%s SHA256SUMS lines=%d" % (len(present), len(copied), refused or "none", len(sums)))
    return 1 if refused else 0


def verify_frozen(frozen_root):
    """Check SHA256SUMS and every run's own raw.sha256 against the frozen copies. Returns a list of problems (empty when all match)."""
    problems = []
    sums_path = os.path.join(frozen_root, "SHA256SUMS")
    if not os.path.isfile(sums_path):
        return ["SHA256SUMS is missing"]
    listed = set()
    with open(sums_path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            digest, rel = line.rstrip("\n").split("  ", 1)
            listed.add(rel)
            path = os.path.join(frozen_root, rel)
            if not os.path.isfile(path):
                problems.append("missing frozen file %s" % rel)
            elif sha256_file(path) != digest:
                problems.append("sha256 mismatch %s" % rel)
    for run in sorted(os.listdir(frozen_root)):
        run_dir = os.path.join(frozen_root, run)
        if not os.path.isdir(run_dir):
            continue
        for name in os.listdir(run_dir):
            if "%s/%s" % (run, name) not in listed:
                problems.append("unlisted frozen file %s/%s" % (run, name))
        own = os.path.join(run_dir, "raw.sha256")
        if os.path.isfile(own):
            with open(own, encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        digest, name = line.rstrip("\n").split("  ", 1)
                        target = os.path.join(run_dir, name)
                        if not os.path.isfile(target) or sha256_file(target) != digest:
                            problems.append("raw.sha256 of %s does not match %s" % (run, name))
    return problems


# loading ---------------------------------------------------------------------------------------------------------------------------
def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# metrics (pure; unit-tested) -------------------------------------------------------------------------------------------------------
def claim_counts(row):
    """(attempted, verified, rejected, verification_list_length) from the explain body of one raw row; None entries when there is no explain body."""
    body = ((row.get("explain") or {}).get("body")) or {}
    counters = body.get("counters") or {}
    verification = body.get("verification")
    return (counters.get("attemptedClaims"), counters.get("verifiedClaims"), counters.get("rejectedClaims"), len(verification) if isinstance(verification, list) else None)


def claim_support(rows, selector=lambda r: True):
    """Claim support over rows with explain counters: verified / attempted claims (Wilson), rejected count, and the question-level share fully verified."""
    attempted = verified = rejected = questions = fully = inconsistent = with_claims = 0
    for row in rows:
        if not selector(row):
            continue
        a, v, r, listed = claim_counts(row)
        if a is None:
            continue
        questions += 1
        attempted += a
        verified += v or 0
        rejected += r or 0
        with_claims += a >= 1
        fully += (a >= 1 and (v or 0) == a)
        inconsistent += listed is not None and listed != a
    return {"questions_with_explain": questions, "claims_attempted": attempted, "claims_verified": verified, "claims_rejected": rejected,
            "runtime_self_reported_verification_rate": proportion(verified, attempted), "questions_with_at_least_one_claim": with_claims, "questions_with_all_claims_verified": proportion(fully, with_claims),
            "explain_list_length_differs_from_counter": inconsistent}


def token_usage(rows):
    """Synthesis tokens from /v1/explain modelVersions: (calls, input tokens, output tokens, rows with usage, rows without)."""
    calls = tin = tout = with_usage = without = 0
    for row in rows:
        body = ((row.get("explain") or {}).get("body")) or {}
        versions = body.get("modelVersions")
        if not isinstance(versions, list) or not versions:
            without += 1
            continue
        with_usage += 1
        for entry in versions:
            if isinstance(entry, dict) and isinstance(entry.get("inputTokens"), int) and isinstance(entry.get("outputTokens"), int):
                calls += 1
                tin += entry["inputTokens"]
                tout += entry["outputTokens"]
    return {"synthesis_calls": calls, "input_tokens": tin, "output_tokens": tout, "rows_with_model_usage": with_usage, "rows_without": without}


def usd(tokens_in, tokens_out):
    return tokens_in * RATE_INPUT_PER_M / 1e6 + tokens_out * RATE_OUTPUT_PER_M / 1e6


def abstention_quality(results):
    """From scorer results: correct abstentions where the key says abstain; wrong abstentions, errors and answers where the key says answer."""
    ab = [r for r in results if r["expected_outcome"] == "abstain"]
    an = [r for r in results if r["expected_outcome"] == "answer"]
    abstain_kinds = ("abstained", "refused")
    return {"abstain_expected": len(ab), "correct_abstentions": proportion(sum(1 for r in ab if r["pass"]), len(ab)),
            "abstain_expected_but_answered": sum(1 for r in ab if r["outcome_kind"] == "answered"),
            "abstain_expected_but_error": sum(1 for r in ab if r["outcome_kind"] in ("error", "missing")),
            "answer_expected": len(an), "answer_expected_wrongly_abstained_or_refused": proportion(sum(1 for r in an if r["outcome_kind"] in abstain_kinds), len(an)),
            "answer_expected_wrongly_abstained": sum(1 for r in an if r["outcome_kind"] == "abstained"),
            "answer_expected_wrongly_refused_422": sum(1 for r in an if r["outcome_kind"] == "refused"),
            "answer_expected_errors": sum(1 for r in an if r["outcome_kind"] in ("error", "missing")),
            "answer_expected_answered": sum(1 for r in an if r["outcome_kind"] == "answered")}


def accuracy_blocks(results):
    """Scorer-judged accuracy over the answer-expected questions that were answered (denominator is stated each time)."""
    answered = [r for r in results if r["expected_outcome"] == "answer" and r["outcome_kind"] == "answered"]
    answer_expected = [r for r in results if r["expected_outcome"] == "answer"]
    verified_checked = sum(r["claims"].get("verified_claims_checked") or 0 for r in answered)
    mismatching = sum(r["claims"].get("verified_claims_mismatching") or 0 for r in answered)
    return {"answer_expected_questions": len(answer_expected), "answered_questions": len(answered),
            "answered_of_answer_expected": proportion(len(answered), len(answer_expected)),
            "retrieval_pass_of_answered (cited evidence resolves; entities, kinds, ids and numbers match the export)": proportion(sum(1 for r in answered if r["retrieval"].get("pass")), len(answered)),
            "claims_pass_of_answered (no rejected claim; every verified claim's values match the key and export)": proportion(sum(1 for r in answered if r["claims"].get("pass")), len(answered)),
            "text_pass_of_answered (prose contains the key numbers, names, hop counts)": proportion(sum(1 for r in answered if r["text"].get("pass")), len(answered)),
            "all_pass_of_answered": proportion(sum(1 for r in answered if r["pass"]), len(answered)),
            "all_pass_of_answer_expected": proportion(sum(1 for r in answer_expected if r["pass"]), len(answer_expected)),
            "verified_claims_checked_against_export": verified_checked, "verified_claims_contradicting_key_or_export": mismatching,
            "contradiction_rate_of_verified_claims": proportion(mismatching, verified_checked),
            "independent_claim_recheck_consistent (verified claims whose values the scorer re-checked against the export and found consistent)": proportion(verified_checked - mismatching, verified_checked)}


def per_type(results, rows_by_id):
    out = {}
    for kind in sorted({r["type"] for r in results}):
        group = [r for r in results if r["type"] == kind]
        rows = [rows_by_id[r["id"]] for r in group if r["id"] in rows_by_id]
        out[kind] = {"questions": len(group), "expected_outcome": sorted({r["expected_outcome"] for r in group}),
                     "answered": sum(1 for r in group if r["outcome_kind"] == "answered"),
                     "abstained_or_refused": sum(1 for r in group if r["outcome_kind"] in ("abstained", "refused")),
                     "errors": sum(1 for r in group if r["outcome_kind"] in ("error", "missing")),
                     "retrieval_pass": sum(1 for r in group if r["retrieval"].get("pass")), "claims_pass": sum(1 for r in group if r["claims"].get("pass")),
                     "text_pass": sum(1 for r in group if r["text"].get("pass")), "all_pass": sum(1 for r in group if r["pass"]),
                     "claims": claim_support(rows)}
    return out


def classify_16b(question):
    q = question.lower()
    if "direct coauthors" in q:
        return "direct coauthors"
    if "component" in q:
        return "component"
    if "shortest coauthor path" in q:
        return "path"
    if q.startswith("which researchers") or q.startswith("show the strongest"):
        return "ranking"   # includes the Session 1 question "Show the strongest repeated collaborations" (HTTP 422, counted as a ranking question by the recorded 7/8)
    return "other"


def outcome_16b(row):
    """'answered', 'insufficient-evidence abstention' or 'error' for one Session 1 row (no explain record exists in that raw)."""
    status = row.get("status")
    if status != 200 or not isinstance(row.get("answer"), dict):
        return "error"
    summary = ((row["answer"].get("answer") or {}).get("summary") or "")
    return "insufficient-evidence abstention" if summary.strip().startswith("Insufficient verified evidence") else "answered"


def analyse_16b(rows):
    kinds = {}
    for row in rows:
        kinds.setdefault(classify_16b(row.get("question", "")), []).append(row)
    out = {}
    for kind in sorted(kinds):
        group = kinds[kind]
        outcomes = [outcome_16b(r) for r in group]
        claims = sum(len((r.get("answer") or {}).get("claims") or []) for r in group if isinstance(r.get("answer"), dict))
        out[kind] = {"questions": len(group), "answered": proportion(outcomes.count("answered"), len(group)),
                     "insufficient_evidence_abstentions": outcomes.count("insufficient-evidence abstention"), "errors": outcomes.count("error"),
                     "http_statuses": {str(s): sum(1 for r in group if r.get("status") == s) for s in sorted({r.get("status") for r in group}, key=str)},
                     "claims_in_answers": claims}
    recorded = {k: {"recorded_answered": v[0], "recorded_of": v[1], "agrees": k in out and out[k]["answered"]["k"] == v[0] and out[k]["questions"] == v[1]} for k, v in RECORDED_16B.items()}
    return {"by_type": out, "recorded_totals_cross_check": recorded, "questions": len(rows)}


# scoring ---------------------------------------------------------------------------------------------------------------------------
def run_scorer(raw_dir, export_dir, out_json, out_md):
    command = [sys.executable, "-I", os.path.join(HERE, "q12_score.py"), "--key", os.path.join(ROOT, KEY), "--raw", raw_dir, "--export-dir", export_dir,
               "--out-json", out_json, "--out-md", out_md]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout.strip(), done.stderr.strip()


def scorer_cross_check(run, scores):
    recorded = RECORDED_TOTALS.get(run)
    if not recorded:
        return None
    t, a = scores["totals"]["answer_expected"], scores["totals"]["abstain_expected"]
    got = {"answer_expected": t["questions"], "retrieval": t["retrieval_pass"], "claims": t["claims_pass"], "text": t["text_pass"], "all": t["all_pass"],
           "abstain_expected": a["questions"], "abstain_correct": a["all_pass"]}
    if "unverified" in recorded:
        got["unverified"] = scores["unverified"]["items"]
    return {"recomputed": got, "coordinator_recorded": recorded, "agrees": got == recorded}


def environment_label(record):
    """The same labels as eval16_perf.py: a loopback target is the local stack; a non-loopback https target is the AWS ECS stack."""
    return "LOCAL-LOOPBACK-LLM" if (record.get("target") or {}).get("loopback") is True else "AWS-ECS-LLM"


def run_commit(record):
    target = record.get("target") or {}
    return {"environment": environment_label(record), "target_loopback": target.get("loopback"), "target_host": target.get("host"), "target_scheme": target.get("scheme"),
            "target_base_url_sha256": target.get("base_url_sha256"), "commit": record.get("commit"), "tree_dirty": record.get("tree_dirty"), "started_utc": record.get("started_utc"), "ended_utc": record.get("ended_utc"),
            "outcome": record.get("outcome"), "outcomes": record.get("outcomes"), "questions_asked": (record.get("questions") or {}).get("asked"),
            "estimate_in_run_record": (record.get("cost_report") or {}).get("anthropic")}


def analyse(frozen_root, export_dir, out_dir):
    key = read_json(os.path.join(ROOT, KEY))
    rows, records, scores, problems = {}, {}, {}, []
    for run in RUNS:
        path = os.path.join(frozen_root, run)
        if not os.path.isdir(path):
            problems.append("frozen run missing: %s" % run)
            continue
        rows[run] = read_jsonl(os.path.join(path, "answers.jsonl"))
        records[run] = read_json(os.path.join(path, "run-record.json"))
    if problems:
        return None, problems
    os.makedirs(out_dir, exist_ok=True)
    runs_doc = {}
    for run in ("q12-benchmark-q12-run-1", "q12-benchmark-q12-run-2"):
        short = run.replace("q12-benchmark-", "")
        out_json, out_md = os.path.join(out_dir, "q12-%s-scores.json" % short.replace("q12-", "")), os.path.join(out_dir, "q12-%s-scores.md" % short.replace("q12-", ""))
        code, stdout, stderr = run_scorer(os.path.join(frozen_root, run), export_dir, out_json, out_md)
        if code != 0:
            return None, ["q12_score.py failed for %s: exit %d: %s %s" % (run, code, stdout[:300], stderr[:300])]
        scores[run] = read_json(out_json)
        results = scores[run]["questions"]
        by_id = {r["qid"]: r for r in rows[run]}
        runs_doc[run] = {"scorer_stdout": stdout, "scorer_outputs": [os.path.basename(out_json), os.path.basename(out_md)],   # basenames: the out dir itself is never recorded, so any out dir gives identical bytes
                         "scorer_cross_check": scorer_cross_check(run, scores[run]), "record": run_commit(records[run]),
                         "claims_all_questions": claim_support(rows[run]), "claims_answer_expected": claim_support(rows[run], lambda r: _expected(key, r) == "answer"),
                         "accuracy": accuracy_blocks(results), "abstention": abstention_quality(results), "by_type": per_type(results, by_id),
                         "tokens": token_usage(rows[run]), "text_failures_name_omission": name_omission(results),
                         "failures": [{"id": r["id"], "type": r["type"], "outcome_kind": r["outcome_kind"], "http_status": r["http_status"],
                                       "first_reason": ((r["retrieval"].get("reasons") or r["claims"].get("reasons") or r["text"].get("reasons") or [""])[0])[:160]}
                                      for r in results if r["expected_outcome"] == "answer" and not r["pass"]]}
    probes = {}
    for run in ("q12-benchmark-q12-probe-1", "q12-benchmark-q12-probe-2"):
        probes[run] = {"record": run_commit(records[run]), "questions": [{"qid": r.get("qid"), "status": r.get("status"), "claims": claim_counts(r)[:3]} for r in rows[run]],
                       "tokens": token_usage(rows[run])}
    # cost: two separately scoped figures (Q12 key scope and earlier phases) plus the token-derived synthesis-only figure
    derived = {}
    for run in RUNS[:4]:
        tokens = token_usage(rows[run])
        derived[run] = {"input_tokens": tokens["input_tokens"], "output_tokens": tokens["output_tokens"], "usd": usd(tokens["input_tokens"], tokens["output_tokens"])}
    day1 = sum(derived[r]["usd"] for r in CONSOLE["day_contents"]["2026-11-20"])
    day2 = sum(derived[r]["usd"] for r in CONSOLE["day_contents"]["2026-11-21"] if r in derived)
    total = day1 + day2
    profile_path = os.path.join(ROOT, PROFILE)
    cost = {"rates_usd_per_million_tokens": {"input": RATE_INPUT_PER_M, "output": RATE_OUTPUT_PER_M, "source": PROFILE + " (llm.pricing)", "source_sha256": sha256_file(profile_path)},
            "token_derived_synthesis_only": derived,
            "token_derived_by_utc_day": {"2026-11-20": round(day1, 6), "2026-11-21_excluding_demo_answer": round(day2, 6)}, "token_derived_total": round(total, 6),
            "console_cost_of_record": CONSOLE,
            "console_over_derived_ratio": {"2026-11-20": [round(0.035 / day1, 2), round(0.045 / day1, 2)] if day1 else None,
                                           "2026-11-21": [round(0.035 / day2, 2), round(0.045 / day2, 2)] if day2 else None,
                                           "note": "the Console shows two decimals, so a displayed 0.04 means a true value in [0.035, 0.045); ratio is that range over the token-derived figure"},
            "earlier_phases_anthropic_spend": earlier_phases_cost(records["16b-live-evaluation-16b-1"]),
            "note": "token-derived = synthesis input/output tokens from /v1/explain modelVersions at the pinned rates; the planner (LLM) calls are not recorded in /v1/explain, and the demo answer "
                    "of 2026-11-21 is not in the frozen raw, so the token-derived figure is a lower bound and the Console is the cost of record for its key and days"}
    doc = {"schema": SCHEMA, "frozen_inputs": [line for line in open(os.path.join(frozen_root, "SHA256SUMS"), encoding="utf-8").read().splitlines() if line],
           "key": {"path": KEY, "sha256": sha256_file(os.path.join(ROOT, KEY)), "export_run_id": key["source"]["run_id"]},
           "q12": runs_doc, "q12_probes": probes, "session1_16b": analyse_16b(rows["16b-live-evaluation-16b-1"]),
           "session1_16b_record": run_commit(records["16b-live-evaluation-16b-1"]), "cost": cost,
           "question_sets": {"run-1 questions file sha256": records["q12-benchmark-q12-run-1"]["questions"]["file_sha256"], "run-2 questions file sha256": records["q12-benchmark-q12-run-2"]["questions"]["file_sha256"],
                             "same_question_file": records["q12-benchmark-q12-run-1"]["questions"]["file_sha256"] == records["q12-benchmark-q12-run-2"]["questions"]["file_sha256"]},
           "variability": {"repeats": "none of the same code: run-1 and run-2 ran different code (commits above), so they are a before/after pair, not repeats; variability across repeats is unmeasured",
                           "scorer_determinism": "the scorer and this script are deterministic given the frozen files"},
           "threats_to_validity": THREATS, "gaps": GAPS}
    doc["interpretation"] = interpretation(doc)
    return doc, []


NAME_OMISSION = re.compile(r"does not appear|coauthor names appear")


def name_omission(results):
    """Answered answer-expected questions whose text check failed, and how many have a missing-name reason, and how many have only missing-name reasons while retrieval and claims passed (the recorded reasons are capped at 12 per question)."""
    failed = [r for r in results if r["expected_outcome"] == "answer" and r["outcome_kind"] == "answered" and not r["text"].get("pass")]
    omitted = [r for r in failed if r["retrieval"].get("pass") and r["claims"].get("pass") and (r["text"].get("reasons") or []) and all(NAME_OMISSION.search(x) for x in r["text"]["reasons"])]
    with_reason = [r for r in failed if any(NAME_OMISSION.search(x) for x in r["text"].get("reasons") or [])]
    return {"answered_with_text_fail": len(failed), "with_a_missing_name_reason": len(with_reason),
            "every_text_reason_is_missing_name_and_retrieval_and_claims_pass": len(omitted)}


def earlier_phases_cost(record_16b):
    """The separately scoped Anthropic spend of the earlier phases (Session 1 16B and 14C, another key): the project cost report line, quoted, and the 16B run-record estimate."""
    path = os.path.join(ROOT, EARLIER_PHASES_COST_LOG)
    out = {"scope": "Session 1 16B and 14C, a different Anthropic key from CS441-key; not part of the Console figure above", "source": EARLIER_PHASES_COST_LOG,
           "16b_run_record_estimate_usd": ((record_16b.get("cost_report") or {}).get("anthropic") or {}).get("usd"),
           "16b_run_record_note": "estimated from pinned tokens and rates, not metered; the 16B raw holds no token usage, so no token-derived figure exists for it (gap)"}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        anthropic = [(i + 1, x) for i, x in enumerate(lines) if x.startswith("Anthropic")]
        out["source_sha256"] = sha256_file(path)
        out["line"] = anthropic[0][0] if anthropic else None
        out["quoted"] = anthropic[0][1][:400] if anthropic else None
    else:
        out["source_sha256"], out["line"], out["quoted"] = None, None, "GAP: the cost report file is missing"
    return out


def _expected(key, row):
    for q in key["questions"]:
        if q["id"] == row.get("qid"):
            return q["expected_outcome"]
    return None


THREATS = [
    "The Q12 answer key was computed offline from the same export by a port of the Spark definitions (q12_answer_key.py), and the scorer and key were written by the same project; no independent human label set exists for answers. "
    "The question set is fixed (the 33 questions), so a repeat tests the same wording.",
    "The runtime answers only over a bounded artifact (the ranking questions rank researchers inside it), so rankings are checked for values and order, not against the corpus-wide top.",
    "Run-1 and run-2 ran different code (the run records name two different commits). They are a before/after comparison, not repeats: "
    "there is one run per code version, so no variability or interval across repeats can be given, and run-2's pass counts are not evidence that run-2 code is stable.",
    "The claim support rate counts claims within questions; claims of one question are not independent, so its Wilson interval understates the uncertainty (it treats each claim as an independent trial).",
    "Q12 has 27 answer-expected questions (3 per type); a per-type rate has a very wide interval.",
    "The 16B Session 1 raw holds only the answer bodies (no /v1/explain record, no evidence fetch) and no answer key exists for its 40 questions, so it supports only 'answered vs abstained' rates, not correctness.",
    "The Console cost is a user-supplied screenshot read at two decimals; it cannot be re-derived or verified by this script.",
    "Free-text contradictions are not assessed: the text check looks for the key facts being present, and the claim check compares verified claims' values to the key and the export; a wrong sentence outside those would not be flagged.",
]
GAPS = [
    {"metric": "usefulness rubric", "reason": "no human-rated rubric scores exist for any answer; none is invented"},
    {"metric": "contradiction rate in free text", "reason": "only the scorer's value contradictions of verified claims are available (reported); no check of prose contradictions exists"},
    {"metric": "variability across repeats", "reason": "one run per code version; the two Q12 runs ran different code"},
    {"metric": "correctness of the 16B Session 1 answers", "reason": "no answer key for the 40 questions, no explain/evidence records in that raw, and the Session 1 runtime artifact (run f6e63b4b) differs from the export the Q12 key was computed from"},
    {"metric": "planner-call tokens and cost", "reason": "planner calls are not recorded in /v1/explain or the raw; only the Console total covers them"},
]


def interpretation(doc):
    r1, r2 = doc["q12"]["q12-benchmark-q12-run-1"], doc["q12"]["q12-benchmark-q12-run-2"]
    lines = ["Between run-1 and run-2 the all-three pass count on the %d answer-expected questions moved from %d to %d (code changed between the runs; one run each)." % (
        r1["accuracy"]["answer_expected_questions"], r1["accuracy"]["all_pass_of_answer_expected"]["k"], r2["accuracy"]["all_pass_of_answer_expected"]["k"])]
    key = "independent_claim_recheck_consistent (verified claims whose values the scorer re-checked against the export and found consistent)"
    lines.append("Independent claim re-check: run-1 %s, run-2 %s. Runtime self-reported verification (not independent): run-1 %s, run-2 %s; rejected claims %d and %d." % (
        fmt(r1["accuracy"][key]), fmt(r2["accuracy"][key]), fmt(r1["claims_all_questions"]["runtime_self_reported_verification_rate"]),
        fmt(r2["claims_all_questions"]["runtime_self_reported_verification_rate"]), r1["claims_all_questions"]["claims_rejected"], r2["claims_all_questions"]["claims_rejected"]))
    n = r1["text_failures_name_omission"]
    lines.append("Run-1: %d answered answer-expected questions failed the text check; %d of them carry a missing-name reason (rank-1 researcher or coauthor list absent from the prose) and %d carry only "
                 "missing-name reasons with retrieval and claims passing. The scorer found %d verified claims contradicting the key or export in run-1 and %d in run-2." % (
                     n["answered_with_text_fail"], n["with_a_missing_name_reason"], n["every_text_reason_is_missing_name_and_retrieval_and_claims_pass"],
                     r1["accuracy"]["verified_claims_contradicting_key_or_export"], r2["accuracy"]["verified_claims_contradicting_key_or_export"]))
    lines.append("Run-2: %d answer-expected questions did not pass all three checks; they are listed question by question under the run-2 failures (%s)." % (
        len(r2["failures"]), ", ".join("%s %s" % (f["id"], f["outcome_kind"]) for f in r2["failures"]) or "none"))
    b = doc["session1_16b"]["by_type"]
    zero = sorted(k for k, v in b.items() if v["answered"]["k"] == 0 and v["questions"] > 0)
    if zero:
        lines.append("16B Session 1 (code of commit %s, environment %s): no question of type %s was answered (all abstained with 'Insufficient verified evidence' or errored); the Q12 runs ran later code." % (
            doc["session1_16b_record"]["commit"][:8], doc["session1_16b_record"]["environment"], ", ".join(zero)))
    c = doc["cost"]
    lines.append("Cost, Q12 key scope: the token-derived synthesis-only figure is %.4f USD against a Console figure of %.2f USD for key %s (two-decimal display). The package cannot attribute the difference; "
                 "planner calls are not recorded and one demo answer is outside the frozen raw." % (c["token_derived_total"], c["console_cost_of_record"]["total_usd"], c["console_cost_of_record"]["key"]))
    return lines


def markdown(doc):
    L = ["# Phase 16 group 4: answer quality (Q12 runs 1 and 2, probes, 16B Session 1)", "",
         "Generated by `experiments/scripts/eval16_answers.py`; do not edit by hand. Order: inputs, definitions, measured facts, threats and gaps, interpretation.", "",
         "## Inputs (frozen raw copies; sha256 from `q12-raw/SHA256SUMS`)", "", "```"] + doc["frozen_inputs"] + ["```", "",
         "Answer key `%s` sha256 `%s`, computed from export run `%s`." % (doc["key"]["path"], doc["key"]["sha256"], doc["key"]["export_run_id"]), "",
         "## Definitions", "",
         "- *independent claim re-check* (the primary claim figure) = of the claims the runtime marked verified, the share whose values the scorer re-checked against the Spark export (distinct coauthors, weighted degree, component and community ids, bridge measures, team sizes, path edges) and found consistent; its complement is the *contradiction rate*.",
         "- *runtime self-reported verification rate* = verified / attempted claims from the `/v1/explain` counters. This is the runtime's own verifier reporting on itself, so it is **not** an independent measurement; it is shown for completeness.",
         "- *scorer-judged accuracy* = the three pass/fail checks of `q12_score.py` over the answer-expected questions that were answered: retrieval (every cited evidence id resolves and every cited value, entity id, path edge, component and community id matches the Spark export), "
         "claims (no rejected claim and every verified claim's values match key and export) and text (the answer prose contains the key numbers, names and hop counts). A failed or abstained question counts against `all_pass_of_answer_expected`.",
         "- *contradiction rate* = verified claims whose values contradict the key or the export / verified claims checked. Prose contradictions are not assessed (gap).",
         "- *abstention quality* = correct abstentions on the questions the key marks abstain-expected (HTTP 200 ABSTAINED or HTTP 422 UNSUPPORTED_QUERY), and wrong abstentions or refusals on the answer-expected questions.", ""]
    for run in ("q12-benchmark-q12-run-1", "q12-benchmark-q12-run-2"):
        r = doc["q12"][run]
        rec = r["record"]
        L += ["## Measured: %s [%s]" % (run, rec["environment"]), "", "Environment `%s` (target loopback %s, host %s, scheme %s, base-url sha256 `%s`). Code commit `%s` (tree dirty: %s), started %s, ended %s, run outcome `%s`, outcomes %s." % (
            rec["environment"], rec["target_loopback"], rec["target_host"], rec["target_scheme"], (rec["target_base_url_sha256"] or "")[:16], rec["commit"], rec["tree_dirty"], rec["started_utc"], rec["ended_utc"], rec["outcome"],
            json.dumps(rec["outcomes"], sort_keys=True)), "",
              "Scorer output line: `%s`; scorer files (next to this file) `%s`." % (r["scorer_stdout"], "`, `".join(r["scorer_outputs"])), ""]
        cc = r["scorer_cross_check"]
        if cc:
            L += ["Cross-check against the coordinator's recorded totals: recomputed %s; recorded %s; agree: **%s**." % (json.dumps(cc["recomputed"], sort_keys=True), json.dumps(cc["coordinator_recorded"], sort_keys=True), "yes" if cc["agrees"] else "NO"), ""]
        a, c, ab = r["accuracy"], r["claims_all_questions"], r["abstention"]
        L += ["- answer-expected questions answered: %s" % fmt(a["answered_of_answer_expected"])]
        for name, value in a.items():
            if isinstance(value, dict) and name not in ("answered_of_answer_expected",) and not name.startswith("independent_") and "k" in value:
                L.append("- %s: %s" % (name.replace("_", " ", 1) if False else name, fmt(value)))
        L += ["- verified claims checked against the export: %d; contradicting: %d" % (a["verified_claims_checked_against_export"], a["verified_claims_contradicting_key_or_export"]),
              "- **independent claim re-check (primary)**: %s of the verified claims were re-checked against the export and are consistent (%d contradicting)" % (
                  fmt(a["independent_claim_recheck_consistent (verified claims whose values the scorer re-checked against the export and found consistent)"]), a["verified_claims_contradicting_key_or_export"]),
              "- runtime self-reported verification rate (the runtime's own /v1/explain verifier, not independent; all %d questions with an explain record): %s; attempted %d, verified %d, rejected %d" % (
                  c["questions_with_explain"], fmt(c["runtime_self_reported_verification_rate"]), c["claims_attempted"], c["claims_verified"], c["claims_rejected"]),
              "- questions with at least one attempted claim whose attempted claims were all verified: %s" % fmt(c["questions_with_all_claims_verified"]),
              "- abstention: correct abstentions on abstain-expected %s; wrongly abstained or refused on answer-expected %s (abstained %d, refused 422 %d); errors on answer-expected %d; abstain-expected answered %d, errored %d" % (
                  fmt(ab["correct_abstentions"]), fmt(ab["answer_expected_wrongly_abstained_or_refused"]), ab["answer_expected_wrongly_abstained"], ab["answer_expected_wrongly_refused_422"],
                  ab["answer_expected_errors"], ab["abstain_expected_but_answered"], ab["abstain_expected_but_error"]), "",
              "| type | questions | answered | abstained/refused | errors | retrieval | claims | text | all pass | claims verified/attempted |", "|---|---|---|---|---|---|---|---|---|---|"]
        for kind, t in r["by_type"].items():
            L.append("| %s (%s) | %d | %d | %d | %d | %d | %d | %d | %d | %d/%d |" % (kind, "/".join(t["expected_outcome"]), t["questions"], t["answered"], t["abstained_or_refused"], t["errors"],
                                                                                   t["retrieval_pass"], t["claims_pass"], t["text_pass"], t["all_pass"], t["claims"]["claims_verified"], t["claims"]["claims_attempted"]))
        L += ["", "For the abstain-expected types the retrieval and claims columns are vacuous passes (not applicable: the key expects an abstention) and the text column is the abstention check.", "",
              "Answer-expected questions that did not pass all three checks (first recorded reason):", ""]
        L += ["- %s (%s): %s, HTTP %s: %s" % (f["id"], f["type"], f["outcome_kind"], f["http_status"], f["first_reason"] or "no reason recorded") for f in r["failures"]] or ["- none"]
        L.append("")
    L += ["## Measured: run-1 against run-2 per question type (all-three pass of 3 questions per type)", "", "| type | run-1 | run-2 |", "|---|---|---|"]
    t1, t2 = doc["q12"]["q12-benchmark-q12-run-1"]["by_type"], doc["q12"]["q12-benchmark-q12-run-2"]["by_type"]
    for kind in t1:
        L.append("| %s | %d/%d | %d/%d |" % (kind, t1[kind]["all_pass"], t1[kind]["questions"], t2[kind]["all_pass"], t2[kind]["questions"]))
    L += ["", "Run-1 and run-2 ran different code; this is a before/after comparison, not a repeat. Variability across repeats is unmeasured.", "",
          "## Measured: probes (one question each, not part of the totals)", ""]
    for run, p in doc["q12_probes"].items():
        L.append("- %s [%s, loopback %s]: commit `%s`, questions %s, tokens %s" % (run, p["record"]["environment"], p["record"]["target_loopback"], p["record"]["commit"], json.dumps(p["questions"], sort_keys=True), json.dumps(p["tokens"], sort_keys=True)))
    b = doc["session1_16b"]
    rb = doc["session1_16b_record"]
    L += ["", "## Measured: 16B Session 1 [%s] (%d questions, commit `%s`)" % (rb["environment"], b["questions"], rb["commit"]), "",
          "Environment `%s`: target loopback %s, host %s, scheme %s (Session 1, 2026-11-14, a different runtime and artifact from the Q12 runs)." % (rb["environment"], rb["target_loopback"], rb["target_host"], rb["target_scheme"]), "",
          "'answered' means HTTP 200 with a summary that is not the 'Insufficient verified evidence' abstention; it is not a correctness judgement (no key, no explain record).", "",
          "| type | questions | answered | insufficient-evidence abstentions | errors | HTTP statuses | recorded (coordinator) | agrees |", "|---|---|---|---|---|---|---|---|"]
    for kind, t in b["by_type"].items():
        rc = b["recorded_totals_cross_check"].get(kind)
        L.append("| %s | %d | %s | %d | %d | %s | %s | %s |" % (kind, t["questions"], fmt(t["answered"]), t["insufficient_evidence_abstentions"], t["errors"], json.dumps(t["http_statuses"], sort_keys=True),
                                                           "%d of %d" % (rc["recorded_answered"], rc["recorded_of"]) if rc else "n/a", ("yes" if rc["agrees"] else "NO") if rc else "n/a"))
    c = doc["cost"]
    e = c["earlier_phases_anthropic_spend"]
    L += ["", "## Measured: cost", "",
          "Two separately scoped Anthropic figures, plus a token-derived figure. Rates (USD per 1M tokens): input %.2f, output %.2f, read from `%s` (sha256 `%s`)." % (
              c["rates_usd_per_million_tokens"]["input"], c["rates_usd_per_million_tokens"]["output"], c["rates_usd_per_million_tokens"]["source"], c["rates_usd_per_million_tokens"]["source_sha256"]), "",
          "**Scope 1, Q12 key (CS441-key, 2026-11-20 and 2026-11-21 UTC).** Anthropic Console, the cost of record for this key: total USD %.2f as of %s (by UTC day %s: %s). Scope note: %s." % (
              c["console_cost_of_record"]["total_usd"], c["console_cost_of_record"]["as_of_utc"], json.dumps(c["console_cost_of_record"]["by_utc_day"], sort_keys=True),
              json.dumps(c["console_cost_of_record"]["day_contents"], sort_keys=True), c["console_cost_of_record"]["scope"]),
          "The Console value is a user-supplied screenshot figure; this script cannot verify it.", "",
          "Token-derived for the same runs, synthesis calls only (`/v1/explain` modelVersions):", "", "| run | input tokens | output tokens | USD |", "|---|---|---|---|"]
    for run, d in c["token_derived_synthesis_only"].items():
        L.append("| %s | %d | %d | %.6f |" % (run, d["input_tokens"], d["output_tokens"], d["usd"]))
    L += ["", "Token-derived by UTC day: %s; total %.6f USD. Console over token-derived ratio range: %s. %s" % (
        json.dumps(c["token_derived_by_utc_day"], sort_keys=True), c["token_derived_total"], json.dumps(c["console_over_derived_ratio"], sort_keys=True), c["note"]), "",
          "Estimates written into the Q12 run records (from pinned per-answer tokens, not metered): run-1 %s; run-2 %s." % (
              json.dumps(doc["q12"]["q12-benchmark-q12-run-1"]["record"]["estimate_in_run_record"], sort_keys=True), json.dumps(doc["q12"]["q12-benchmark-q12-run-2"]["record"]["estimate_in_run_record"], sort_keys=True)), "",
          "**Scope 2, earlier phases: %s.** Project cost report `%s` (sha256 `%s`) line %s: `%s`. The 16B run record's own estimate is USD %s (%s)." % (
              e["scope"], e["source"], e["source_sha256"], e["line"], e["quoted"], e["16b_run_record_estimate_usd"], e["16b_run_record_note"]), "",
          "The two scopes are different keys and different periods; they are not added together here.", "",
          "## Threats to validity and missing data", ""]
    L += ["- %s" % t for t in doc["threats_to_validity"]]
    L += ["", "## Gaps (not measured, with the reason)", ""] + ["- **%s**: %s" % (g["metric"], g["reason"]) for g in doc["gaps"]]
    L += ["", "## Variability", "", "Question set: %s (same question file in both runs: %s)." % (json.dumps(doc["question_sets"], sort_keys=True), "yes" if doc["question_sets"]["same_question_file"] else "NO"),
          "", doc["variability"]["repeats"], "", "## Interpretation (separate from the measured facts above)", ""]
    L += ["- %s" % t for t in doc["interpretation"]]
    return "\n".join(L) + "\n"


MANIFEST = os.path.join("experiments", "manifests", "16-evaluation.json")
MANIFEST_SCRIPTS = ("experiments/scripts/eval16_identity.py", "experiments/scripts/eval16_graph.py", "experiments/scripts/eval16_answers.py", "experiments/scripts/q12_score.py",
                    "experiments/scripts/q12_graph.py", "experiments/scripts/check_manifests.py", "experiments/tests/test_eval16_a.py",
                    "experiments/scripts/eval16_perf.py", "experiments/scripts/eval16_factory.py", "experiments/scripts/eval16_retrieval.py", "experiments/scripts/eval16_repro.py",
                    "experiments/tests/test_eval16_b.py")
MANIFEST_OUTPUT_DIRS = ("experiments/results/phase16/identity", "experiments/results/phase16/graph", "experiments/results/phase16/answers", "experiments/results/phase16/q12-raw",
                        "experiments/results/phase16/performance", "experiments/results/phase16/factory", "experiments/results/phase16/retrieval",
                        "experiments/results/phase16/reproducibility")
# Instance B refreshes this log after every regeneration check, so its bytes are not pinned by the manifest (the other files of that directory are).
MANIFEST_EXCLUDED_OUTPUTS = ("experiments/results/phase16/reproducibility/regeneration-check.log",)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def entry(rel, **extra):
    out = {"path": rel, "sha256": sha256_file(os.path.join(ROOT, rel))}
    out.update(extra)
    return out


def write_manifest(run_date):
    """Write experiments/manifests/16-evaluation.json (sorted keys; no timestamps other than the given run date, so a rerun gives identical bytes)."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", run_date):
        print("MANIFEST-REFUSED: --run-date must be YYYY-MM-DD")
        return 1
    identity = load_script("eval16_identity")
    five_e = identity.E5
    identity_inputs = [entry(rel, group=1, tracked=True) for rel in sorted(set(identity.INPUTS.values()) | set(identity.EVALUATOR_OUTPUTS.values()) |
                                                                           {five_e + "/evaluation-report.md", five_e + "/evaluation-manifest.json"})]
    graph_path = os.path.join(ROOT, "experiments", "results", "phase16", "graph", "graph-correctness.json")
    graph = read_json(graph_path)
    graph_inputs = [{"path": "target/phase15/p6/size-S/run:ba7402d1-959a-4277-8c6e-e92878a38afa/spark/" + name, "sha256": digest, "group": 2, "tracked": False,
                     "note": "untracked Spark export (git-ignored); sha256 taken from the listing in graph-correctness.json, verified only where the file exists"}
                    for name, size, digest in graph["export"]["files"] if not name.startswith("neptune-opencypher-csv")]
    graph_inputs.append({"path": "target/phase15/p6/size-S/run:ba7402d1-959a-4277-8c6e-e92878a38afa/spark/neptune-opencypher-csv/data (60 listed files)", "group": 2, "tracked": False,
                         "files_listing_sha256": graph["export"]["files_listing_sha256"], "note": "the listing of every CSV part with size and sha256 is in experiments/results/phase16/graph/graph-correctness.md"})
    graph_inputs += [entry("docs/agent-runs/phase-15/test-report.md", group=2, tracked=True, note="source of the recorded full check quoted by the graph result")]
    graph_inputs += [entry(s["path"], group=2, tracked=True, note="Spark suite listed, not run") for s in graph["known_small_graph_tests"]["suites"]]
    answer_inputs = [entry(KEY, group=4, tracked=True), entry("experiments/inputs/q12/questions.txt", group=4, tracked=True)]
    with open(os.path.join(ROOT, FROZEN, "SHA256SUMS"), encoding="utf-8") as handle:
        for line in handle.read().splitlines():
            digest, rel = line.split("  ", 1)
            answer_inputs.append({"path": "%s/%s" % (FROZEN.replace(os.sep, "/"), rel), "sha256": digest, "group": 4, "tracked": True, "note": "frozen copy; the original is under target/experiment-runs/ (untracked)"})
    outputs = []
    for rel in MANIFEST_OUTPUT_DIRS:
        for base, _, names in sorted(os.walk(os.path.join(ROOT, rel))):
            for name in sorted(names):
                rel_out = os.path.relpath(os.path.join(base, name), ROOT).replace(os.sep, "/")
                if rel_out not in MANIFEST_EXCLUDED_OUTPUTS:
                    outputs.append(entry(rel_out))
    manifest = {
        "schema": "scholarchain.eval16-manifest.v1", "id": "16-evaluation", "phase": 16, "owner": "experiment-engineer (instance A writes the manifest; instance B writes the files of groups 3, 5, 6, 7)",
        "groups": [1, 2, 3, 4, 5, 6, 7],
        "group_names": {"1": "entity resolution", "2": "graph correctness", "3": "retrieval", "4": "answer quality", "5": "performance and elasticity", "6": "agentic factory", "7": "reproducibility"}, "run_date": run_date,
        "scope": {"offline": True, "network_calls": 0, "aws_calls": 0, "model_calls": 0, "spend_usd": "0.00",
                  "note": "every metric is computed by a committed script from raw evidence that already existed; nothing was run on AWS or against a model"},
        "determinism": "python3 -I, stdlib only, sorted keys, fixed seeds (eval16-identity-v1, eval16-graph-v1); a rerun gives identical bytes",
        "inputs": sorted(identity_inputs + graph_inputs + answer_inputs, key=lambda e: (e["group"], e["path"])),
        "scripts": [entry(rel) for rel in MANIFEST_SCRIPTS], "outputs": sorted(outputs, key=lambda e: e["path"]),
        "commands": [
            "python3 -I experiments/scripts/eval16_identity.py",
            "python3 -I experiments/scripts/eval16_graph.py --export-dir 'target/phase15/p6/size-S/run:ba7402d1-959a-4277-8c6e-e92878a38afa/spark'",
            "python3 -I experiments/scripts/eval16_answers.py freeze   # once; refuses to overwrite a different frozen file",
            "python3 -I experiments/scripts/eval16_answers.py run --export-dir 'target/phase15/p6/size-S/run:ba7402d1-959a-4277-8c6e-e92878a38afa/spark'",
            "python3 -I experiments/scripts/eval16_answers.py manifest --run-date %s" % run_date,
            "python3 -I experiments/scripts/eval16_perf.py; eval16_factory.py; eval16_retrieval.py; eval16_repro.py   # instance B, see experiments/README.md",
            "python3 -I experiments/scripts/eval16_repro.py --verify",
            "python3 -I experiments/scripts/check_manifests.py",
            "python3 -I -m unittest discover -s experiments/tests"],
        "inputs_note": "the inputs list covers groups 1, 2 and 4; the raw inputs of groups 3, 5, 6 and 7 are read by instance B's scripts (see their result files for the inputs they read)",
        "excluded_outputs": {"experiments/results/phase16/reproducibility/regeneration-check.log": "refreshed by instance B after each `eval16_repro.py --verify` run, so it is not pinned here"}}
    path = os.path.join(ROOT, MANIFEST)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print("MANIFEST written %s: inputs=%d scripts=%d outputs=%d" % (MANIFEST, len(manifest["inputs"]), len(manifest["scripts"]), len(manifest["outputs"])))
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--run-date", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--src-root", default=os.path.join(ROOT, "target", "experiment-runs"))
    f.add_argument("--frozen-root", default=os.path.join(ROOT, FROZEN))
    r = sub.add_parser("run")
    r.add_argument("--export-dir", required=True)
    r.add_argument("--frozen-root", default=os.path.join(ROOT, FROZEN))
    r.add_argument("--out-dir", default=os.path.join(ROOT, "experiments", "results", "phase16", "answers"))
    args = parser.parse_args(argv)
    if args.mode == "freeze":
        return freeze(args.src_root, args.frozen_root)
    if args.mode == "manifest":
        return write_manifest(args.run_date)
    problems = verify_frozen(args.frozen_root)
    if problems:
        print("EVAL16-ANSWERS-REFUSED: frozen copies do not match SHA256SUMS: %s" % "; ".join(problems[:5]))
        return 1
    try:
        doc, problems = analyse(args.frozen_root, args.export_dir, args.out_dir)
    except (OSError, ValueError, KeyError) as error:
        print("EVAL16-ANSWERS-REFUSED: %s: %s" % (type(error).__name__, error))
        return 1
    if problems:
        print("EVAL16-ANSWERS-REFUSED: %s" % "; ".join(problems))
        return 1
    with open(os.path.join(args.out_dir, "answer-quality.json"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    with open(os.path.join(args.out_dir, "answer-quality.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown(doc))
    r1, r2 = doc["q12"]["q12-benchmark-q12-run-1"], doc["q12"]["q12-benchmark-q12-run-2"]
    print("EVAL16-ANSWERS run-1 all_pass=%d/%d runtime_self_reported=%s | run-2 all_pass=%d/%d runtime_self_reported=%s | scorer cross-check agrees: run-1=%s run-2=%s | 16B recorded agrees=%s | token_derived_total_usd=%.6f" % (
        r1["accuracy"]["all_pass_of_answer_expected"]["k"], r1["accuracy"]["all_pass_of_answer_expected"]["n"], fmt(r1["claims_all_questions"]["runtime_self_reported_verification_rate"]),
        r2["accuracy"]["all_pass_of_answer_expected"]["k"], r2["accuracy"]["all_pass_of_answer_expected"]["n"], fmt(r2["claims_all_questions"]["runtime_self_reported_verification_rate"]),
        r1["scorer_cross_check"]["agrees"], r2["scorer_cross_check"]["agrees"], all(v["agrees"] for v in doc["session1_16b"]["recorded_totals_cross_check"].values()),
        doc["cost"]["token_derived_total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Phase 16, group 7 (reproducibility): record the evidence that exists, and check that the committed Phase 16 tables regenerate byte for byte
(stdlib only; python3 -I; offline).

  python3 -I experiments/scripts/eval16_repro.py [--out-dir experiments/results/phase16/reproducibility]   write the evidence tables
  python3 -I experiments/scripts/eval16_repro.py --verify                                                  regenerate every table and compare

Record mode writes two table sets:
  reproducibility-evidence.json / .md   committed inputs only: the check.sh results the coordinator recorded in the phase test reports (file and line for each), the
                                        clean-snapshot procedure of Phase 14, the approved-plan deployment results of Session 2 (RESULT lines with file and line), the
                                        smoke-local record, and the status of the three checks the course names. A fresh-clone build is PENDING (Phase 17): it is listed
                                        as not done, never as passed.
  check-runs-local.json / .md           from git-ignored local files: the full-check runs in the coordinator notes (Phase 15 closeout, Q12, option A) and the replays of
                                        the local P6 chain. When those files are absent the committed tables are still written and the exit code is 3.

Verify mode runs every eval16_*.py script (this one included, in record mode) with --out-dir pointing into a temporary directory, then compares each produced file
with experiments/results/phase16/<group>/ byte for byte and prints PASS or FAIL per file. A script that is not present yet is reported as SKIP (not present); a script
that exits 3 (git-ignored raw inputs absent) is reported as SKIP (inputs unavailable) with its message; neither counts as a pass. Files in the committed directory that no
script produced (for example regeneration-check.log) are listed as NOT-COMPARED. The last line is `REGENERATION: PASS` (nothing failed, nothing skipped), `REGENERATION: PARTIAL` (nothing failed but at least one script was skipped, so not every table was checked) or `REGENERATION: FAIL`. Exit 0 only for PASS, 1 when any FAIL, 4 for PARTIAL. Invocation per script is the SCRIPTS table: --out-dir DIR for every script, plus --export-dir
for the graph script and the `run` subcommand for the answers script. Each script must write all its outputs directly under DIR and be deterministic (sorted keys, no timestamps).
Exit codes (record mode): 0 done, 1 refused, 3 local inputs absent (committed tables still written).
"""
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHEMA = "scholarchain.eval16-reproducibility.v1"
RESULTS = os.path.join(ROOT, "experiments", "results", "phase16")
NOTES = "target/phase15/session2/evidence/coordinator-notes.log"
NOTES_FROZEN_LINES = 199  # append-only log: the first 199 lines are the state when Phase 16 started; later notes are not read
P6_WORK = "target/phase15/p6/work"
EXPORT_DIR = "target/phase15/p6/size-S/run:ba7402d1-959a-4277-8c6e-e92878a38afa/spark"  # git-ignored local Spark export used by the graph and answers scripts
# (script, group directory, argument template, path that must exist). {out} = the temporary output directory, {export} = EXPORT_DIR. A script whose required path is absent is
# SKIPPED without being run. The identity, performance, factory, retrieval and reproducibility scripts take --out-dir only; the graph script also needs --export-dir; the answers
# script is invoked as its `run` subcommand (the other subcommands, freeze and manifest, write elsewhere and are not part of regeneration).
SCRIPTS = (("eval16_identity.py", "identity", ["--out-dir", "{out}"], None),
           ("eval16_graph.py", "graph", ["--export-dir", "{export}", "--out-dir", "{out}"], EXPORT_DIR),
           ("eval16_answers.py", "answers", ["run", "--export-dir", "{export}", "--out-dir", "{out}"], EXPORT_DIR),
           ("eval16_perf.py", "performance", ["--out-dir", "{out}"], None), ("eval16_factory.py", "factory", ["--out-dir", "{out}"], None),
           ("eval16_retrieval.py", "retrieval", ["--out-dir", "{out}"], None), ("eval16_repro.py", "reproducibility", ["--out-dir", "{out}"], None))
NOT_COMPARED = ("regeneration-check.log", "raw-rb-20261118-freeze-note.json")  # static records, not produced by a script
FROZEN_INPUT_DIRS = (("performance", "raw-rb-20261118"),)  # frozen raw inputs committed next to a table: not regenerated; their SHA256SUMS is verified instead
PHASES = tuple("%02d" % n for n in range(1, 16))
S2 = "docs/agent-runs/phase-15/evidence/session-2"
DEPLOY_FILES = (S2 + "/stage-a/stagea-results.txt", S2 + "/rb-runtime/rb-runtime-results.txt", S2 + "/section-c/cleanup-results.txt", S2 + "/emr/emr-dry-100-results.txt",
                S2 + "/emr/emr-upload-results.txt")
CHECK_RESULT = re.compile(r"RESULT:?\s+(PASS gates=\d+|FAIL failed: [a-z,\- ]+?(?=[`.\s]|$)|PARTIAL passed=\d+)")
DEPLOY_RESULT = re.compile(r"^(?:\w+\| )?RESULT: ([A-Z-]+)\b")
APPROVAL_MATCH = re.compile(r"plan sha256 matches the approval record|approval record matches the commit|has not started a run before \(single-use\)")
REDACT = [(re.compile(r"\b\d{12}\b"), "<12-digit>"), (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<email>")]


class Refused(Exception):
    pass


def redact(text):
    for pattern, repl in REDACT:
        text = pattern.sub(repl, text)
    return text


def excerpt(text, limit=200):
    return redact(re.sub(r"\s+", " ", text.strip())[:limit])


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_lines(rel):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as handle:
            return handle.read().split("\n")
    except OSError as error:
        raise Refused("%s: %s" % (rel, error.strerror))


def md_table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]


# -------------------------------------------------------------------------------------------------------------- committed evidence
def check_results_in_test_reports(inputs):
    items = []
    for phase in PHASES:
        rel = "docs/agent-runs/phase-%s/test-report.md" % phase
        if not os.path.isfile(os.path.join(ROOT, rel)):
            continue
        inputs[rel] = sha256_file(os.path.join(ROOT, rel))
        for number, line in enumerate(read_lines(rel), 1):
            for m in CHECK_RESULT.finditer(line):
                text = m.group(1)
                outcome = "PASS" if text.startswith("PASS") else ("FAIL" if text.startswith("FAIL") else "PARTIAL")
                items.append({"phase": phase, "file": rel, "line": number, "outcome": outcome, "result_text": text.strip(), "excerpt": excerpt(line)})
    per_phase = {}
    for phase in PHASES:
        rows = [i for i in items if i["phase"] == phase]
        if rows:
            per_phase[phase] = dict(sorted(collections.Counter(i["outcome"] for i in rows).items()))
    return {"rule": "Lines in docs/agent-runs/phase-NN/test-report.md (the coordinator's observed results) containing 'RESULT: PASS gates=N', 'RESULT: FAIL failed: <gate>' or "
                    "'RESULT: PARTIAL passed=N' (check.sh's own result lines; a run may be quoted on more than one line, so these are result-line mentions, not distinct runs).",
            "per_phase_result_line_mentions": per_phase, "items": items,
            "limitations": ["Mentions, not distinct runs: one run's result can be quoted several times in one report.",
                            "PARTIAL means check.sh was run with a gate skipped (for example --skip sbt) and cannot count as the full definition of done.",
                            "Phase 15's later runs (Q12 and option A) are in the coordinator notes, see check-runs-local."]}


def deployment_results(inputs):
    out = []
    for rel in DEPLOY_FILES:
        lines = read_lines(rel)
        inputs[rel] = sha256_file(os.path.join(ROOT, rel))
        results = []
        approvals = 0
        for number, line in enumerate(lines, 1):
            m = DEPLOY_RESULT.match(line)
            if m:
                results.append({"line": number, "class": m.group(1), "excerpt": excerpt(line, 150)})
            if APPROVAL_MATCH.search(line):
                approvals += 1
        out.append({"file": rel, "result_lines": results, "result_classes": dict(sorted(collections.Counter(r["class"] for r in results).items())),
                    "approval_binding_lines": approvals})
    return out


def committed_evidence():
    inputs = {}
    smoke = "scripts/smoke-local.sh"
    inputs[smoke] = sha256_file(os.path.join(ROOT, smoke))
    inputs["scripts/check.sh"] = sha256_file(os.path.join(ROOT, "scripts/check.sh"))
    test15 = read_lines("docs/agent-runs/phase-15/test-report.md")
    inputs["docs/agent-runs/phase-15/test-report.md"] = sha256_file(os.path.join(ROOT, "docs/agent-runs/phase-15/test-report.md"))
    smoke_line = next((n for n, l in enumerate(test15, 1) if "scripts/smoke-local.sh --build" in l and "PASS" in l), None)
    snap = read_lines("docs/agent-runs/phase-14/test-report.md")
    inputs["docs/agent-runs/phase-14/test-report.md"] = sha256_file(os.path.join(ROOT, "docs/agent-runs/phase-14/test-report.md"))
    snapshot_lines = [{"line": n, "excerpt": excerpt(l)} for n, l in enumerate(snap, 1) if re.match(r"^#{2,3} .*(?:Full seven-gate check|Clean snapshot|Clean-snapshot)", l, re.I)]
    counters = read_lines(S2 + "/emr/hadoop-prep-counters.txt")
    inputs[S2 + "/emr/hadoop-prep-counters.txt"] = sha256_file(os.path.join(ROOT, S2 + "/emr/hadoop-prep-counters.txt"))
    return {
        "schema": SCHEMA, "scope": "committed records only; regenerable from a clean clone", "inputs_sha256": None,
        "course_checks": [
            {"check": "clean-checkout build", "status": "PENDING (Phase 17): not done",
             "evidence_that_exists": "check.sh (scripts/check.sh, sha256 %s) ran on clean SNAPSHOTS in Phase 14: a git clone of the repository into a scratch directory with the uncommitted files copied "
                                     "in and committed there, identity proved with cmp (procedure at docs/agent-runs/phase-14/test-report.md, 'Clean-snapshot procedure'; headings: %s). A snapshot is a "
                                     "clone plus the working-tree changes, not a fresh clone of the pushed commit." % (inputs["scripts/check.sh"][:12], [s["line"] for s in snapshot_lines]),
             "what_is_missing": "a fresh clone of the pushed branch on a machine or directory with no prior target/ state, running sbt check and scripts/check.sh to RESULT: PASS gates=7. "
                                "Planned for Phase 17; not claimed here."},
            {"check": "bounded pipeline replay", "status": "PARTIAL: local replays recorded; EMR replay not repeatable (the stack is destroyed)",
             "evidence_that_exists": "the local P6 chain was replayed repeatedly on the same input (see check-runs-local.json: logical outputs identical across the passing runs); the same Hadoop "
                                     "counters appear on EMR (%s, committed) and locally; the EMR run's Spark step failed, so the full chain has no EMR replay." % (S2 + "/emr/hadoop-prep-counters.txt"),
             "what_is_missing": "a repeat of the bounded EMR chain end to end (it needs a live cluster and a human gate); a replay from a fresh clone (Phase 17)."},
            {"check": "deployment from an approved plan", "status": "DONE in Session 2 (2026-11-18); the stack was destroyed afterwards",
             "evidence_that_exists": "every mutating stage ran only after an approval record bound to the plan sha256 (RESULT lines and approval-binding lines with file and line in "
                                     "deployment_results below); the human gates are recorded in docs/agent-runs/phase-15/human-gate.md and the decision log.",
             "what_is_missing": "a second deployment from a fresh clone (not run, no spend this phase)."},
            {"check": "regeneration of reported tables", "status": "see regeneration-check.log (run with --verify); per-file PASS/FAIL/SKIP", "evidence_that_exists": "every Phase 16 table is written by a committed eval16_*.py script that "
                                                                                                                                                              "can be invoked as shown in SCRIPTS (eval16_repro.py) and is deterministic",
             "what_is_missing": "tables whose inputs are git-ignored raw files (performance, retrieval, the local factory notes) can be regenerated only on the machine that holds target/; in a "
                                "clean clone they SKIP (inputs unavailable), they do not pass."}],
        "check_results_in_test_reports": check_results_in_test_reports(inputs),
        "deployment_results": deployment_results(inputs),
        "smoke_local": {"script": smoke, "script_sha256": inputs[smoke], "recorded_pass": {"file": "docs/agent-runs/phase-15/test-report.md", "line": smoke_line,
                                                                                         "excerpt": excerpt(test15[smoke_line - 1]) if smoke_line else None},
                        "note": "Starts the real query-api offline-synthetic on loopback with a throwaway key, runs smoke-test.sh, stops it: no AWS, no model call."},
        "hadoop_counters_on_emr": [l for l in counters if l.startswith("counters=")],
        "gaps": ["Fresh-clone build and test (Phase 17).", "EMR end-to-end replay and elasticity replay: the AWS stack was destroyed on 2026-11-18 and no further live spend is allowed in this phase.",
                 "A recorded check.sh result for the final Phase 16 tree (the coordinator runs it after review, before the human gate)."],
        "threats_to_validity": ["Result-line mentions are counted from prose records written by the coordinator; they are not an independent log.",
                                "A check.sh pass on one machine (macOS, JDK 17, the author's laptop) says nothing about other platforms.",
                                "Local replays share one machine and one JDK; determinism of the logical outputs is shown, not portability."]}, inputs


# ---------------------------------------------------------------------------------------------------------------- local evidence
NOTE_RULES = (
    (re.compile(r"RESULT:? PASS gates=(\d+)"), "PASS", "all gates passed (check.sh RESULT line)"),
    (re.compile(r"(All 7) gates passed"), "PASS", "all 7 gates passed on the working tree (after a terraform rerun)"),
    (re.compile(r"stopped at user request"), "INTERRUPTED", "stopped at the human's request before completing"),
    (re.compile(r"\bsbt FAIL\b"), "FAIL", "sbt gate failed"),
    (re.compile(r"full sbt check stopped at rag scalafmtCheck"), "FAIL", "sbt gate stopped at scalafmtCheck"),
    (re.compile(r"terraform gate FAIL"), "FAIL", "terraform gate failed (local leftovers, not a code defect per the note)"),
    (re.compile(r"Full sbt -batch check .*\[success\]"), "PASS-SBT-ONLY", "sbt only, not the seven gates"),
)
NOTE_HUMAN = re.compile(r"HUMAN DECISION|USER \(verbatim\)|^\S+ User:", re.I)
NOTE_CANDIDATE = re.compile(r"[Ff]ull (?:sbt )?(?:-batch )?check|full check|check #\d|RESULT PASS gates")


def gate_count(match):
    g = match.group(1) if match.groups() else None
    return 7 if g == "All 7" else (int(g) if g and g.isdigit() else None)


def check_runs_from_notes():
    path = os.path.join(ROOT, NOTES)
    with open(path, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().split("\n")[:NOTES_FROZEN_LINES]
    if len(lines) < NOTES_FROZEN_LINES:
        raise Refused("%s has fewer than %d lines" % (NOTES, NOTES_FROZEN_LINES))
    runs, unclassified = [], []
    for number, line in enumerate(lines, 1):
        if not NOTE_CANDIDATE.search(line) or NOTE_HUMAN.search(line):
            continue  # a human's own words (consent conditions, instructions) are not check results
        label = None
        for pattern, outcome, meaning in NOTE_RULES:
            m = pattern.search(line)
            if m:
                label = (outcome, meaning, m)
                break
        if not label:
            unclassified.append({"line": number, "excerpt": excerpt(line, 160)})
            continue
        outcome, meaning, m = label
        run_id = re.search(r"run (\d{8}T\d{6}Z-\d+)", line)
        head = re.search(r"HEAD ([0-9a-f]{7,40})", line)
        sbt = re.search(r"sbt (\d+) ?s", line)
        script_tests = re.search(r"script-tests (\d+)s", line)
        runs.append({"line": number, "recorded_utc": line.split(" ", 1)[0], "outcome": outcome, "meaning": meaning, "gates": gate_count(m),
                     "run_id": run_id.group(1) if run_id else None, "head": head.group(1) if head else None, "sbt_seconds": int(sbt.group(1)) if sbt else None,
                     "script_tests_seconds": int(script_tests.group(1)) if script_tests else None, "excerpt": excerpt(line, 220)})
    return {"source": NOTES, "source_lines_read": NOTES_FROZEN_LINES, "source_sha256": hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8", errors="replace")).hexdigest(), "rule": "lines matching 'full (sbt) check', 'check #N' or 'RESULT PASS gates', classified by the first matching pattern in NOTE_RULES; a candidate "
            "line that matches no pattern (a start, a plan, a review) is listed under other_candidate_mentions_not_counted; a human's own quoted words (consent conditions) are skipped.",
            "runs": runs, "outcomes": dict(sorted(collections.Counter(r["outcome"] for r in runs).items())), "other_candidate_mentions_not_counted": unclassified,
            "limitations": ["The notes are a coordinator's running log, not a check.sh log: durations and counts are as the coordinator wrote them.",
                            "Several passing runs were on uncommitted working trees that were committed afterwards (the line says which commits followed); the notes do not store the tree hash.",
                            "The log is append-only and git-ignored: the first %d lines are read (its state when Phase 16 started); later notes are not part of this evaluation." % NOTES_FROZEN_LINES]}


def p6_replays():
    base = os.path.join(ROOT, P6_WORK)
    runs = []
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name, "evidence", "summary.json")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as handle:
            d = json.load(handle)
        if not (d.get("allStepsPassed") and d.get("size") == "S"):
            continue
        e = d.get("evidence") or {}
        canon = lambda obj: hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
        runs.append({"run_id": d["runId"], "git_head": (d.get("git") or {}).get("head"), "input_tree_sha256": d.get("inputTreeSha256"),
                     "hadoop_counters_sha256": canon(e.get("hadoopCounters")), "spark_counters_sha256": canon(e.get("sparkCounters")),
                     "sidecar_total_bytes": (e.get("sidecar") or {}).get("totalBytes"), "er_policy_hash": (e.get("erManifest") or {}).get("policyHash"),
                     "er_config_hash": (e.get("erManifest") or {}).get("configHash"), "export_files": e.get("exportFiles"), "export_bytes": e.get("exportBytes"),
                     "source": "%s/%s/evidence/summary.json" % (P6_WORK, name), "source_sha256": sha256_file(path)})
    distinct = lambda key: len(set(r[key] for r in runs))
    return {"environment": "LOCAL-MAC", "passing_size_S_runs": runs, "count": len(runs),
            "distinct_values_across_runs": {"input_tree_sha256": distinct("input_tree_sha256"), "hadoop_counters": distinct("hadoop_counters_sha256"), "spark_counters": distinct("spark_counters_sha256"),
                                            "sidecar_total_bytes": distinct("sidecar_total_bytes"), "er_policy_hash": distinct("er_policy_hash"), "er_config_hash": distinct("er_config_hash"),
                                            "export_files": distinct("export_files"), "export_bytes": distinct("export_bytes")},
            "export_bytes_min_max": [min(r["export_bytes"] for r in runs), max(r["export_bytes"] for r in runs)] if runs else None,
            "reading": "1 distinct value = identical in every passing run. The logical outputs (Hadoop and Spark counters, the CSV sidecar size, the entity-resolution policy and config hashes) are "
                       "identical; the physical Parquet export differs slightly in file count and size between runs (the summary does not record why: GAP).",
            "limitation": "Six passing runs on one machine, at three commits (the pipeline code was unchanged between them according to the run records' pins), one input slice; this shows run-to-run "
                          "determinism of the logical outputs, not a clean-clone replay."}


# -------------------------------------------------------------------------------------------------------------------- markdown
def render_md(e):
    L = ["# Phase 16 group 7: reproducibility (committed evidence)", "",
         "Generated by `experiments/scripts/eval16_repro.py` from committed records. The local-file evidence (coordinator notes, local P6 replays) is in `check-runs-local.md`. "
         "A check is marked done only where a record shows it.", "", "## 1. The checks the course names", ""]
    L += md_table(["check", "status", "evidence that exists", "what is missing"], [[c["check"], c["status"], c["evidence_that_exists"], c["what_is_missing"]] for c in e["course_checks"]])
    L += ["", "## 2. check.sh results recorded in the phase test reports", "", "Per phase, result-line mentions by outcome: %s" % e["check_results_in_test_reports"]["per_phase_result_line_mentions"], "",
          e["check_results_in_test_reports"]["rule"], ""]
    L += md_table(["phase", "outcome", "result", "source"], [[i["phase"], i["outcome"], i["result_text"], "%s:%d" % (i["file"], i["line"])] for i in e["check_results_in_test_reports"]["items"]])
    L += [""] + ["- " + x for x in e["check_results_in_test_reports"]["limitations"]]
    L += ["", "## 3. Deployment from an approved plan (Session 2, 2026-11-18)", ""]
    L += md_table(["file", "RESULT classes", "approval-binding lines"], [[d["file"], d["result_classes"], d["approval_binding_lines"]] for d in e["deployment_results"]])
    L += ["", "Each RESULT line with its line number is in `reproducibility-evidence.json` (deployment_results).", "", "## 4. Local smoke", "",
          "`%s` (sha256 %s): recorded PASS at `%s:%s`. %s" % (e["smoke_local"]["script"], e["smoke_local"]["script_sha256"], e["smoke_local"]["recorded_pass"]["file"], e["smoke_local"]["recorded_pass"]["line"],
                                                              e["smoke_local"]["note"]), "", "## 5. GAPs", ""] + ["- " + g for g in e["gaps"]]
    L += ["", "## 6. Threats to validity", ""] + ["- " + t for t in e["threats_to_validity"]]
    L += ["", "## 7. Inputs (sha256)", ""] + ["- `%s` %s" % (k, h) for k, h in e["inputs_sha256"].items()]
    return "\n".join(L) + "\n"


def render_local_md(c, p):
    L = ["# Phase 16 group 7: reproducibility (local-file evidence)", "",
         "Generated by `experiments/scripts/eval16_repro.py` from git-ignored local files; regenerable only on the machine that holds them.", "",
         "## 1. Full-check runs in the coordinator notes", "", "Source `%s` (first %d lines, sha256 %s). Outcomes: %s." % (c["source"], c["source_lines_read"], c["source_sha256"], c["outcomes"]), ""]
    L += md_table(["line", "recorded (UTC)", "outcome", "gates", "run id", "HEAD", "sbt s", "script-tests s", "meaning"],
                  [[r["line"], r["recorded_utc"], r["outcome"], r["gates"], r["run_id"], r["head"], r["sbt_seconds"], r["script_tests_seconds"], r["meaning"]] for r in c["runs"]])
    L += ["", "Excerpts (audit):", ""] + ["- line %d: %s" % (r["line"], r["excerpt"].replace("|", "/")) for r in c["runs"]]
    L += ["", c["rule"], ""] + ["- " + x for x in c["limitations"]]
    L += ["", "## 2. Local replays of the P6 chain (size S)", "", "Environment: %s. Passing S runs: %d. Distinct values across runs (1 = identical): %s. Export bytes min/max: %s." % (
        p["environment"], p["count"], p["distinct_values_across_runs"], p["export_bytes_min_max"]), ""]
    L += md_table(["run", "head", "sidecar bytes", "export files", "export bytes"], [[r["run_id"], (r["git_head"] or "")[:7], r["sidecar_total_bytes"], r["export_files"], r["export_bytes"]] for r in p["passing_size_S_runs"]])
    L += ["", p["reading"], "", "Limitation: " + p["limitation"]]
    return "\n".join(L) + "\n"


def write(out_dir, name, text):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def dump(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def record(out_dir):
    evidence, inputs = committed_evidence()
    evidence["inputs_sha256"] = dict(sorted(inputs.items()))
    write(out_dir, "reproducibility-evidence.json", dump(evidence))
    write(out_dir, "reproducibility-evidence.md", render_md(evidence))
    if not (os.path.isfile(os.path.join(ROOT, NOTES)) and os.path.isdir(os.path.join(ROOT, P6_WORK))):
        print("INPUTS-UNAVAILABLE: %s or %s (git-ignored local files; the committed-record tables are written, check-runs-local is not)" % (NOTES, P6_WORK))
        return 3
    checks, replays = check_runs_from_notes(), p6_replays()
    write(out_dir, "check-runs-local.json", dump({"schema": SCHEMA, "check_runs_in_coordinator_notes": checks, "p6_local_replays": replays}))
    write(out_dir, "check-runs-local.md", render_local_md(checks, replays))
    print("WROTE %s (reproducibility-evidence.json/.md, check-runs-local.json/.md)" % out_dir)
    return 0


# ---------------------------------------------------------------------------------------------------------------------- verify
def tree(path):
    out = {}
    for base, _, files in os.walk(path):
        for name in files:
            full = os.path.join(base, name)
            out[os.path.relpath(full, path)] = full
    return out


def compare(group, produced_dir, committed_dir, emit, partial=False):
    """Compare every produced file with the committed one; returns (passes, fails, not_compared)."""
    produced, committed = tree(produced_dir), tree(committed_dir) if os.path.isdir(committed_dir) else {}
    passes = fails = 0
    for rel in sorted(produced):
        label = "%s/%s" % (group, rel)
        if rel not in committed:
            emit("FAIL %s (produced but not committed)" % label)
            fails += 1
        elif sha256_file(produced[rel]) == sha256_file(committed[rel]):
            emit("PASS %s" % label)
            passes += 1
        else:
            emit("FAIL %s (bytes differ: regenerated sha256 %s, committed %s)" % (label, sha256_file(produced[rel])[:12], sha256_file(committed[rel])[:12]))
            fails += 1
    extra = [rel for rel in sorted(committed) if rel not in produced]
    for rel in extra:
        if rel in NOT_COMPARED:
            emit("NOT-COMPARED %s/%s (not produced by a script)" % (group, rel))
        elif any(g == group and rel.startswith(d + os.sep) for g, d in FROZEN_INPUT_DIRS):
            pass  # a frozen raw input; checked by check_frozen_inputs
        elif partial:
            emit("SKIP %s/%s (needs git-ignored inputs that are absent)" % (group, rel))
        else:
            emit("FAIL %s/%s (committed but not regenerated by %s)" % (group, rel, group))
            fails += 1
    return passes, fails


def check_frozen_inputs(results_dir, emit):
    """Verify every frozen raw-input directory against its SHA256SUMS (same file set, same bytes). Returns (passes, fails)."""
    passes = fails = 0
    for group, name in FROZEN_INPUT_DIRS:
        base = os.path.join(results_dir, group, name)
        label = "%s/%s" % (group, name)
        if not os.path.isdir(base):
            continue
        sums = os.path.join(base, "SHA256SUMS")
        try:
            with open(sums, encoding="utf-8") as handle:
                listed = dict((l.split("  ", 1)[1].strip(), l.split("  ", 1)[0]) for l in handle if l.strip())
        except (OSError, IndexError):
            emit("FAIL %s (SHA256SUMS missing or malformed)" % label)
            fails += 1
            continue
        present = sorted(n for n in os.listdir(base) if n != "SHA256SUMS")
        bad = [n for n in present if listed.get(n) != sha256_file(os.path.join(base, n))]
        if sorted(listed) != present or bad:
            emit("FAIL %s (frozen input does not match SHA256SUMS: %s)" % (label, bad or "file set differs"))
            fails += 1
        else:
            emit("PASS %s (frozen input: %d files match SHA256SUMS; not regenerated)" % (label, len(present)))
            passes += 1
    return passes, fails


def verdict(totals):
    return "FAIL" if totals["fail"] else ("PARTIAL" if totals["skip"] else "PASS")


def exit_code(totals):
    """0 = PASS, 1 = FAIL, 4 = PARTIAL (a skipped script means not every table was regenerated and compared)."""
    return 1 if totals["fail"] else (4 if totals["skip"] else 0)


def verify(results_dir=RESULTS, scripts_dir=HERE, scripts=SCRIPTS, emit=print):
    totals = {"pass": 0, "fail": 0, "skip": 0}
    with tempfile.TemporaryDirectory(prefix="eval16-regen-") as tmp:
        for entry in scripts:
            script, group = entry[0], entry[1]
            template = entry[2] if len(entry) > 2 else ["--out-dir", "{out}"]
            required = entry[3] if len(entry) > 3 else None
            path = os.path.join(scripts_dir, script)
            if not os.path.isfile(path):
                emit("SKIP %s (script not present yet)" % group)
                totals["skip"] += 1
                continue
            if required and not os.path.exists(os.path.join(ROOT, required)):
                emit("SKIP %s (inputs unavailable: %s is absent; git-ignored)" % (group, required))
                totals["skip"] += 1
                continue
            out_dir = os.path.join(tmp, group)
            argv = [a.replace("{out}", out_dir).replace("{export}", os.path.join(ROOT, EXPORT_DIR)) for a in template]
            proc = subprocess.run([sys.executable, "-I", path] + argv, capture_output=True, text=True, cwd=ROOT)
            message = (proc.stdout.strip().splitlines() or [""])[0][:200] if proc.returncode in (0, 3) else (proc.stderr.strip().splitlines() or proc.stdout.strip().splitlines() or [""])[-1][:200]
            if proc.returncode == 3:
                # exit 3 = git-ignored inputs absent; committed-only outputs may still have been written and are compared
                emit("SKIP %s (inputs unavailable: %s)" % (group, message))
                totals["skip"] += 1
                if os.path.isdir(out_dir) and os.listdir(out_dir):
                    p, f = compare(group, out_dir, os.path.join(results_dir, group), emit, partial=True)
                    totals["pass"] += p
                    totals["fail"] += f
                continue
            if proc.returncode != 0:
                emit("FAIL %s (script exited %d: %s)" % (group, proc.returncode, message))
                totals["fail"] += 1
                continue
            p, f = compare(group, out_dir, os.path.join(results_dir, group), emit)
            totals["pass"] += p
            totals["fail"] += f
    p, f = check_frozen_inputs(results_dir, emit)
    totals["pass"] += p
    totals["fail"] += f
    emit("REGENERATION: %s pass=%d fail=%d skipped_scripts=%d" % (verdict(totals), totals["pass"], totals["fail"], totals["skip"]))
    return totals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=os.path.join(RESULTS, "reproducibility"))
    parser.add_argument("--verify", action="store_true", help="regenerate every table into a temporary directory and compare with the committed files")
    args = parser.parse_args(argv)
    if args.verify:
        return exit_code(verify())
    try:
        return record(args.out_dir)
    except Refused as error:
        print("REFUSED: %s" % error)
        return 1


if __name__ == "__main__":
    sys.exit(main())

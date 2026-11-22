<!-- Course-named copy of owner-report.md in this folder, added in Phase 17 (package 17D, docs/agent-runs/phase-17/prompt.md). The text below this note is identical to owner-report.md, which is unchanged. -->

# Phase 16 owner reports (assembled by the coordinator)

Each section below summarises one owner's final report for this phase, in the fields of `docs/agent-runs/README.md`. Commands and results are those the owner reported and the coordinator re-ran where stated. The full results live under `experiments/results/phase16/` and in `docs/report/evaluation.md`.

## experiment-engineer, instance A (groups 1 entity resolution, 2 graph correctness, 4 answer quality)

STATUS: COMPLETE (initial run, repair round 1 A1-A13, final manifest re-pin)
OWNER: experiment-engineer (instance A)
WORK ORDER: `docs/agent-runs/phase-16/prompt.md`; coordinator repair messages after review rounds 1 and 2
FILES CREATED: `experiments/scripts/eval16_identity.py`, `eval16_graph.py`, `eval16_answers.py` (subcommands `freeze`, `run`, `manifest`); `experiments/tests/test_eval16_a.py` (70 tests); `experiments/manifests/16-evaluation.json` (43 inputs, 12 scripts, 52 outputs); `experiments/results/phase16/{identity,graph,answers}/**`; `experiments/results/phase16/q12-raw/**` (frozen copies of q12-run-1, q12-run-2, q12-probe-1, q12-probe-2 and 16b-live-evaluation-16b-1, `SHA256SUMS`, `freeze-report.json`)
FILES MODIFIED: `experiments/scripts/check_manifests.py` (Phase 16 manifest check: offline scope, policy, every hash, completeness of `results/phase16`), `experiments/README.md` (Phase 16 section, including instance B's paragraph at the coordinator's request)
COMMANDS RUN (observed, X = `target/phase15/p6/size-S/run:ba7402d1-959a-4277-8c6e-e92878a38afa/spark`):
- secret scan of the five run directories before copying: 0 matches; `eval16_answers.py freeze`: `FROZEN runs=5 copied_files=20 refused=none`
- `eval16_identity.py`: held-out binary 194, TP 57, FP 0, FN 15, TN 122, precision 100.0% (Wilson 93.7-100.0), recall 79.2% (68.4-86.9); cross-check with the Phase 5E evaluator agrees
- `eval16_graph.py --export-dir X`: 0/100,252 unresolved graph-edge endpoints, 0/228,715 unresolved coauthor rows, 0 duplicates, 228,715/228,715 coauthor rows supported, provenance audit 50/50, support-table rows = sum(joint) 269,753 = 269,753, stored pairs = sum(min(joint,5)) 267,597 = 267,597
- `eval16_answers.py run --export-dir X`: run-1 all-pass 4/27, run-2 23/27; independent scorer re-check of verified claims 36/36 and 65/65 consistent, 0 contradictions; scorer and 16B cross-checks agree; token-derived synthesis cost USD 0.039535
- `eval16_answers.py manifest --run-date 2026-11-21`: inputs 43, scripts 12, outputs 52
TEST RESULTS: `test_eval16_a.py` 70 OK; `experiments/tests` 258 OK; `check_manifests.py` RESULT OK, 106 file hashes verified (coordinator re-ran all three)
VALIDATION RESULTS: reruns byte-identical; outputs independent of the output directory (fixed in repair round 1)
ASSUMPTIONS: positive prediction is ACCEPTED (5E definition); graph support rows read from the CSV sidecar (Parquet unreadable by stdlib); Console figure user-supplied
RISKS: frozen `run-record.json` files keep a local home-directory path in `ledger_path` (kept byte-identical; disclosed in `freeze-report.json`; human decision at the gate); first-freeze time recovered from file mtimes; Q12 per-type intervals are wide (3 questions per type)
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none (gaps recorded in the results)
NEXT GATE: review, full check, human gate

## experiment-engineer, instance B (groups 3 retrieval, 5 performance and elasticity, 6 agentic factory, 7 reproducibility)

STATUS: COMPLETE (initial run, repair round 1 B1-B7, round 2 minors M1, M2)
OWNER: experiment-engineer (instance B)
WORK ORDER: `docs/agent-runs/phase-16/prompt.md`; coordinator repair messages
FILES CREATED: `experiments/scripts/eval16_perf.py`, `eval16_factory.py`, `eval16_retrieval.py`, `eval16_repro.py`; `experiments/tests/test_eval16_b.py` (44 tests); `experiments/results/phase16/{performance,factory,retrieval,reproducibility}/**`; frozen AWS load raw `experiments/results/phase16/performance/raw-rb-20261118/` (5 files, `SHA256SUMS`) and its scan record `raw-rb-20261118-freeze-note.json` (11 patterns, 0 matches)
FILES MODIFIED: none outside its own files
COMMANDS RUN (observed): the four scripts (each `WROTE ...`, exit 0); determinism by double run into scratch directories (identical); `eval16_repro.py --verify | tee .../regeneration-check.log`: `REGENERATION: PASS pass=24 fail=0 skipped_scripts=0` (23 regenerated files plus the frozen rb raw verified)
TEST RESULTS: `test_eval16_b.py` 44 OK (coordinator re-ran)
VALIDATION RESULTS: recomputed load metrics match the harness `summary.csv` for all 12 load phases; stop-task recovery 113 s matches the decision log; EMR cost USD 0.37 matches the ledger; factory hand audit of phase 03 (14 review events by hand vs 11 parsed) recorded next to the first-pass rate
ASSUMPTIONS: nearest-rank percentiles; retrieval order from `explain.body.evidenceIds`; coordinator notes read to line 199
RISKS: factory counts are heuristic regex parsing; the P35 local raw (83 MB) is hash-only and stays on the laptop, so the performance script cannot run in a clean clone (stated); retrieval metrics rest on 6-7 ranking questions and a key built in this repository
DISCLOSURE: while checking a setting, instance B printed `target/phase15/session2/14c-work/smoke-config.json` (contains the AWS account ID in bucket names) to its own tool output; nothing was copied into a tracked file and its outputs scan clean
MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none (11 gaps recorded, among them vector-only and fused retrieval, exact ECS scaling delays, 2-task throughput, per-request cost, EMR Spark, fresh clone)
NEXT GATE: review, full check, human gate

## documentation-engineer (write-up)

STATUS: COMPLETE (initial write-up, repair round 1 D1-D8, round 2 M1)
OWNER: documentation-engineer
WORK ORDER: `docs/agent-runs/phase-16/prompt.md`
FILES CREATED: `docs/report/evaluation.md` (634 lines)
FILES MODIFIED: none
COMMANDS RUN (observed): read-only number checks from the session scratchpad: 612 numeric tokens, 0 not found in sources; strict boundary check 0 missing; 92 value-and-interval pairs, 0 not found; 35 relative links, 0 broken; secret and identity scan clean
TEST RESULTS: not applicable
VALIDATION RESULTS: self-derived statements removed; reshaped table rows checked by hand
RISKS: length (634 lines, over the 250-400 aim)
MANUAL ACTION REQUIRED: none
NEXT GATE: review, full check, human gate

# Phase 16 work order: evaluation package

Assembled by the coordinator (Claude Code orchestrator) on 2026-11-22 (Sat Nov 21, 7 PM CST). This is the exact work order the owners received, in summary form, with the human decisions quoted verbatim.

## Human decisions

- 2026-11-21, after the Q12 rerun and the Anthropic Console cost check, the coordinator asked: "Start the Phase 16 records now?" The human answered: "Yes, start now".
- Earlier standing decisions that still apply: commits only on the human's explicit yes; no AWS, no live model calls and no spend in this phase (the Anthropic key `scholarchain-q12`, shown in the Console as `CS441-key`, was revoked on 2026-11-21); negative results stay in the submission.

## Course requirement (source and its limit)

Course README, https://raw.githubusercontent.com/0x1DOCD00D/ScholarChain/main/README.md, read 2026-11-22 through a fetch tool. The Phase 16 section was returned only as a tool-made summary, not verbatim, so the wording below is a paraphrase. Phase 16 evaluates the system scientifically, not from a few attractive answers, in seven groups:

1. Entity resolution: precision, recall, F1, confusion matrix, coverage, unresolved rate, per-matching-path metrics.
2. Graph correctness: referential integrity, duplicate and orphan rates, coauthor-edge support rate, known small-graph tests, sampled provenance audit.
3. Retrieval: recall@K, precision@K where labels allow, MRR, nDCG with graded labels; graph-only vs vector-only vs fused.
4. Answer quality: claim support rate, validity of coauthor edges, paths and supporting publications, identifier and numeric accuracy, contradiction rate, abstention quality, usefulness rubric.
5. Performance and elasticity: throughput, p50/p95/p99 latency, errors, scaling delay, recovery time, estimated cost.
6. Agentic factory: first-pass acceptance by agent, BLOCKED-ON count, ownership violations caught, reviewer findings by count and severity, repair iterations, manual interventions, unsafe actions prevented.
7. Reproducibility: clean-checkout build, bounded pipeline replay, deployment from an approved plan, regeneration of reported tables.

Rules: freeze raw outputs before conclusions; confidence intervals or variability where repeats exist; threats to validity and missing data stated; measured facts separate from interpretation; evaluation data not produced by the prompt under evaluation without independent review.

## Scope decision (coordinator)

Offline only: every metric is computed by a committed script from raw evidence that already exists (Sessions 1 and 2, the P6 local runs, the Q12 runs of 2026-11-20 and 2026-11-21, the phase records). Nothing is re-run on AWS or against a model. Where a group has no raw evidence (for example vector-only and fused retrieval with relevance labels), the package says so as a gap; nothing is estimated in its place.

## Owners and paths (one writer per file)

| Owner | Writes | Groups |
|---|---|---|
| experiment-engineer (instance A) | `experiments/scripts/eval16_identity.py`, `eval16_graph.py`, `eval16_answers.py`; `experiments/results/phase16/{identity,graph,answers}/**`; `experiments/results/phase16/q12-raw/**` (frozen copies of the Q12 run-1, run-2 and probe raw outputs with sha256); `experiments/manifests/16-evaluation.json`; `experiments/tests/test_eval16_a.py`; the Phase 16 section of `experiments/README.md` | 1, 2, 4 |
| experiment-engineer (instance B) | `experiments/scripts/eval16_perf.py`, `eval16_factory.py`, `eval16_retrieval.py`, `eval16_repro.py`; `experiments/results/phase16/{performance,factory,retrieval,reproducibility}/**`; `experiments/tests/test_eval16_b.py` | 3, 5, 6, 7 |
| documentation-engineer (after both freeze) | `docs/report/evaluation.md` | write-up |
| code-reviewer | report text only | independent review |
| coordinator | `docs/agent-runs/phase-16/{prompt,owner-report,test-report,review,repairs}.md`, `commit.txt` | assembly |
| human | `docs/agent-runs/phase-16/human-gate.md` | gate |

Gate: owners' targeted tests pass, independent review APPROVE, then one full `scripts/check.sh` (JDK 17), then the human's gate and commit decision.

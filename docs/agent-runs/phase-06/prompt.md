# Phase 6 work order and Subphase 6A start

The user supplied the repository's root `AGENTS.md` instructions in this session and identified `/Users/danny/Documents/plan/phase6.md` as the current plan. The exact implementation request was:

> Now I want you to implement the plan. Before implementing the plan, do you have any questions first?

The plan's Section 9 requires one subphase per prompt, starting with 6A, followed by an independent user-run review. It also requires questions before implementation. The coordinator asked all three listed 6A open questions and received these answers:

1. **6A-1 branch:** "Yes, create `phase-6` (recommended)."
2. **6A-2 models:** "Use the current model for each role and record it (recommended)."
3. **6A-3 EMR fallback investigation:** "Compare custom images on EMR Serverless/EKS and a custom Spark distribution on EMR EC2 (recommended)."

Scope is **Subphase 6A only**, as written in Section 9 of the supplied plan: establish the JDK 17 baseline; configure the Spark test harness, JDK guard, independent-test dependency, and Spark job packaging under build ownership; add one Spark smoke spec under Spark ownership after build wiring; research EMR Spark/Scala/Java compatibility under infrastructure ownership; run the final 6A gate and return a copyable independent reviewer prompt. No reviewer, cloud execution, later-subphase implementation, commit, or push is authorized in this work order.

Base SHA: `03493882399e9020e6892c9f97e0ec8919365215`. Initial working tree was clean on `main`; the coordinator created `phase-6` from that SHA. The existing Phase 5 human acceptance and documented limitations remain as recorded in `docs/agent-runs/phase-05/human-gate.md`.

## Subphase 6A repair round 1 work order

After a user-run external read-only reviewer returned `REQUEST-CHANGES`, the user instructed exactly: **"Fix F1, F2, F3 please"**. The full external review is retained in `review.md`; findings and scope dispositions are in `repairs.md`. The coordinator asked one remaining Step 0 question: whether the test-engineer may add a minimal `SparkSession` startup probe under `tests/**`. The user's answer was exactly: **"Yes, add the probe (recommended)"**. No other finding is assigned for implementation in this round. The repair stops with a new user-run reviewer handoff; Subphase 6B is not started.

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

## Subphase 6B work order

The user said, "now let move on phase 6b" after the externally approved 6A repair round. The user committed 6A as `bc1e4a17fc879b7aac254b28d83e78dbdd34e367` (`phase-06 build-engineer: add Spark test harness and packaging`). The `phase-6` working tree was clean at 6B preflight. This commit is the 6B base SHA and starting HEAD. The external 6A approval is retained verbatim in `review.md`.

The coordinator asked the plan's 6B-1, 6B-2 and 6B-3 questions and the 6B record-version choice. After the questions were repeated in ordinary text, the user answered exactly: **"yes to all"**. Thus the four recommended defaults are binding for 6B:

1. Canonical DBLP researcher IDs use `researcher:dblp:<SHA-256(identityPolicyVersion + "\n" + NFC trimmed exact DBLP author name)>`.
2. Windows are all-years, non-overlapping min–2009 / 2010–2014 / 2015–2019 / 2020–2026, and cumulative 2015–2026.
3. Representative edge works are capped at 5; max-team work IDs are capped at 20 while keeping the complete tie count.
4. New maximum-team evidence and explicit bridge measures use versioned companion metrics records, preserving the existing `ResearcherMetrics` wire format.

Scope is **Subphase 6B only**, as specified in `/Users/danny/Documents/plan/phase6.md` (SHA-256 `bd6ecba68004562a39338293e9e9c1ce9af094614b3efdb7ab8accb7229c2fa8`). `domain-engineer` owns additive shared contracts, IDs, Spark config/loader, wire examples and contract tests under `modules/core/**`. `spark-engineer` owns `modules/spark/README.md` design sections only, and must align them with published core examples before finalizing. The coordinator assembles `docs/agent-runs/phase-06/**`, runs the final JDK 17 `sbt -batch check`, and returns the Section 11 reviewer prompt. No 6C code, cloud action, reviewer launch, commit or push is in scope.

The coordinator's first 6B JDK probe ran `/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java -version` (exit 0): OpenJDK `17.0.20.1` Homebrew. All sbt runs use the plan's JDK 17 `JAVA_HOME`, `PATH` and `SBT_OPTS` settings. Tool: Codex native delegation and shell tools. Parent model is identified to the coordinator as GPT-6; exact deployed model build and delegated child model IDs are not exposed by the tool and will be reported as unavailable.

## Subphase 6B repair round 1 work order

The user supplied an independent read-only `REQUEST-CHANGES` review for 6B. Its complete text is appended in `review.md` under **Subphase 6B review — user-supplied external review**. The user then instructed exactly: **"Fix F1, F2, F3, F4 for me"**. F1–F3 are blocking; F4 is nonblocking but included by the user. F5–F8 are recorded with later owner/gate dispositions in `repairs.md` and are not implementation scope for this round.

The reviewer requested a Step 0 choice for F2. The coordinator asked whether to use `StableIds.chunkOrProfileId` with policy and window bound in `sourceVersion`, the recommended formula compatible with the plan and existing evidence IDs. The user answered exactly: **"yes, use chunkOrProfileId"**. No other Step 0 question remains open within the user's F1–F4 scope.

The repair remains on branch `phase-6`, base/current HEAD `bc1e4a17fc879b7aac254b28d83e78dbdd34e367`, with the uncommitted 6B tree intact. `domain-engineer` owns F1–F4 changes and tests under `modules/core/**`. `spark-engineer` owns only F2 design wording in `modules/spark/README.md`. The coordinator alone assembles `docs/agent-runs/phase-06/**`, retains the final JDK 17 gate, and returns a new read-only reviewer prompt. No 6C work, cloud calls, reviewer launch, commit or push is authorized.

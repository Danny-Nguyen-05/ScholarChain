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

## Subphase 6C work order

The user said exactly: **"alright let move on phase 6c"** after the independent reviewer approved 6B repair round 1. Preflight found a clean `phase-6` tree at base SHA `01d204b531d3fc72a5c49f884980a5c7c8926b18`, commit `phase-06 domain-engineer: add Spark analytics contracts, stable IDs, and configuration`. The approved 6B review and its R1/R2 dispositions are retained in `review.md` and `repairs.md`.

Step 0 answers:

1. 6C-1 and 6C-2: **"Yes to both (recommended)"** — exclude enrichment-only works from coauthorship and keep different DBLP names separate despite accepted links, counting both cases.
2. 6C-3: The coordinator initially suggested prepared run `f22f1a12-c7be-43af-b470-d4f4e244ca9d`, and the user answered **"Yes, use that run (recommended)"**. Read-only inspection then found no retained DBLP export partition in that completed prepared root. The coordinator sent a correction that superseded this question, naming the latest completed run with a DBLP export, `target/phase4-runs/ccd26111-d26d-4783-bc0f-e7106e4e617d`, and asking to verify or create a matching offline ER export. The user answered **"Use ccd26111… (recommended)"**.
3. F6: **"Bind bounds in 6C (recommended)"** — bind numeric window bounds as well as label in the new Spark edge ID helper and update the new 6B example before production output; frozen older IDs stay unchanged.
4. F7: **"Use logical fingerprint (recommended)"** — deterministic run identity includes input run/manifest hashes and logical algorithm settings while excluding machine-specific input roots, checkpoint path, output path and shuffle partition count.

Scope is **Subphase 6C only** of `/Users/danny/Documents/plan/phase6.md` (plan SHA-256 `bd6ecba68004562a39338293e9e9c1ce9af094614b3efdb7ab8accb7229c2fa8`). `domain-engineer` owns F6/F7 core helpers and tests under `modules/core/**`, publishing the interface before Spark uses it. `spark-engineer` owns `modules/spark/**` readers, manifest/output gate, bounded actions, jobs 1–2, module tests, runnable main and local smoke. `test-engineer` owns independent G1 tests under `tests/**`. The coordinator assembles `docs/agent-runs/phase-06/**`, runs one final stable-tree JDK 17 `sbt -batch check`, and returns a Section 11 reviewer prompt. R1 remains future F5 hardening; 6A F4/F6 remain future release gates. No AWS call, live LLM, 6D work, reviewer launch, commit or push is authorized.

## Subphase 6C repair round 1 work order

The user supplied a read-only external `REQUEST-CHANGES` review in two messages and instructed: **"fix all blocking bugs for me"**. The findings message identifies F1–F5 as blocking; the separately supplied report fields are retained with it in `review.md`. No descriptions of nonblocking N1–N7 were supplied, so this repair addresses F1–F5. `repairs.md` routes F1–F5 and records their acceptance checks.

The Spark owner repairs job selection, integrity reporting, ER reads and module coverage in `modules/spark/**`. The independent test owner adds separate F1/F2 cases in `tests/**`. The coordinator records review and evidence in `docs/agent-runs/phase-06/**`, runs the affected JDK 17 tests, a fresh local smoke and a final stable-tree `sbt -batch check`, then returns a copyable read-only recheck prompt. The branch and base/current HEAD remain `phase-6` and `01d204b531d3fc72a5c49f884980a5c7c8926b18`, with 6C uncommitted. No 6D, reviewer launch, AWS call, commit or push is in scope.

The user's subsequent external recheck supplied only report fields, finding F1–F5 changes substantive but blocked on R1-1 (missing/stale final evidence) and R1-2 (unchanged run ID after changed semantics). The user asked to fix all those blockers. A successor Spark owner closes R1-2 in `modules/spark/**`; the coordinator completes fresh targeted, smoke and JDK 17 full-gate evidence on the final repair tree. No further feature scope or 6D work is inferred from this recheck fragment.

The user-supplied independent recheck subsequently returned **APPROVE** for 6C repair round 1. Its complete text, including the previously missing nonblocking N1–N9 and later-gate list, is retained in `review.md`; `repairs.md` routes those items. The reviewer found no remaining 6C blocker. The user must commit the approved 6C tree before a new prompt can start 6D Step 0. This approval is not a commit or a request to begin 6D.

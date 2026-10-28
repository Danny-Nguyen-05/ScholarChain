# Phase 11 work order

User instruction: "now start the phase 11 A for me". Execute only Subphase 11A.

## Step 0 answers received before edits

- 11-1: Use ExposedDefect tags and explicit defect runs (Recommended). Build-engineer owns any exclusion wiring; production repairs deferred to 11C.
- 11-2: Requirement-to-test table and exact counts (Recommended); no coverage tool.
- 11-3: Use 0349388 plus whole-repository review (Recommended), recorded for later 11C.

## Exact supplied plan

# ScholarChain Phase 11 — Adversarial testing and full repository review: implementation and handoff plan

Prepared: 2026-10-22. Intended reader: a fresh manager/orchestrator agent in Codex, Cursor or Claude Code, and the independent reviewer agents the user launches between subphases.

**Schedule slot:** Nov 7 – Nov 16, 2026 (11A can start right after Phase 6; 11C is the gate before deployment).

> **⛔ WORK ONE SUBPHASE AT A TIME, THEN STOP.** Do exactly one subphase per prompt. When it is done or blocked, return the reviewer prompt and **end your turn**. Do not start, prepare or "get ahead on" the next subphase, even if you have time or the next step looks obvious. The user reviews every subphase before the next begins. Doing several subphases in one run is a failure of this work order, even when the code is correct.

## 1. Your assignment

Implement Phase 11, **Adversarial testing and full repository review**, in `/Users/danny/Documents/UIC/CS441/ScholarChain`.

You are the coordinator. Launch specialist subagents with your tool's native delegation, give each a bounded work order, route dependencies and repairs, collect observed evidence, and produce the review handoff prompt for the user. Do not write specialist production code yourself. Subagents must not launch more subagents.

Four rules apply to every subphase:

1. **Ask before implementing.** At the start of every subphase you may ask the user any question, and the user wants you to. Ask everything at once, give a recommended default for each question, and wait for answers before editing files. If you have no questions, say so explicitly, then proceed.
2. **One subphase at a time, then stop for the user's review.** Implement only the subphase named in the prompt you were given. When it is done or blocked, stop and end your turn. Do not begin the next subphase in the same run and do not draft its code ahead of time. The next subphase starts only when the user pastes a new prompt, normally the one the reviewer wrote. This also applies to repair rounds: fix only the listed findings, then stop.
3. **Do not trigger a code reviewer.** Never launch, invoke or auto-select the `code-reviewer` agent or any other reviewer. The user handles review outside your session.
4. **End every subphase with a copyable reviewer prompt.** Your final message for a subphase must contain the complete reviewer prompt in one fenced code block (Section 10). The user pastes it into a separate reviewer agent. That reviewer reviews read-only, then writes the next prompt for you: either the next subphase or a repair round. Then stop and wait.

This document is an implementation work order. It is not proof of human acceptance, instructor approval, a completed run, or permission to spend money on AWS.

## 2. Project context and verified starting point

- **Purpose:** attack the implementation with independent tests, then run a read-only adversarial review of the **whole repository**, then drive a repair loop until APPROVE or human escalation. Implementation agents optimize for their own work orders; this phase looks for what they missed.
- **Production code is frozen for this phase's test work.** `test-engineer` never edits production code. A defect exposed by a test is reported to the owning agent through the coordinator and repaired in the repair loop (11C).
- **Existing tests:** Phases 2–6 already have module tests and independent tests under `tests/src/test/scala/.../independent/`. Reuse the existing independent-test conventions and helpers; do not duplicate cases that already exist, and extend them where a category below is only partly covered. Check the current counts first.
- **Schedule slot:** 11A can start as soon as Phase 6 is committed (it only needs the data plane). 11B starts when Phases 9 and 10 are committed. 11C is the final gate before deployment. Overall window Nov 7 – Nov 16, 2026. 11A may run in a second session in parallel with Phases 7–10 because it touches only new files under `tests/**`; keep file names prefixed `Adversarial*` to avoid collisions.
- **No live AWS or paid providers.** The course allows bounded AWS integration tests under an approved profile; those run in Phase 14, not here. Everything in 11A–11B uses fakes.

Environment for every sbt command (copy exactly):

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch check        # about 7+ minutes; the "checkProbeInjectFailure ... injected format-stage failure" line is an expected self-test
```

## 3. Source of authority and required reading

1. `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `.claude/agents/test-engineer.md`, `.claude/agents/code-reviewer.md`, `docs/agent-runs/README.md`.
2. The course Phase 11 section (both work orders and the repair loop), "Required test inventory", and "Evaluation deductions and failure conditions": https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-11-adversarial-testing-and-full-repository-review
3. Every module README and every earlier phase's `owner-report.md`, `test-report.md`, `review.md` and `repairs.md` under `docs/agent-runs/` (known limitations list per phase, especially the Phase 5 accepted limitations).
4. The existing tests under `tests/` and each module's `src/test/**`, to map existing coverage before adding cases.

## 4. Decisions and open questions that apply to the whole phase

- **Open questions for the phase (ask in Step 0 of 11A):**
  - **11-1. How to handle tests that expose a production defect.** The course says to leave the defect exposed and report it, but `sbt check` must stay green for the build to remain usable. Recommended: tag such tests `ExposedDefect` (a ScalaTest tag excluded from `sbt check`), list each with its owner and ID in `test-report.md`, run them with an explicit command, and remove the tag when the owner's repair lands. `build-engineer` wires the exclusion if needed (BLOCKED-ON).
  - **11-2. Coverage measurement.** Recommended: no coverage tool; report coverage by requirement (a table mapping each course category to test names).
  - **11-3. Review scope for 11C.** Recommended: the whole repository at HEAD plus the diff from the Phase 4 baseline (`0349388` is the Phase 5 acceptance commit; use the first commit after Phase 3 acceptance if the user prefers a wider diff). Ask the user which base to use.
- **Reviewer separation is a graded item.** The reviewer prompt in 11C is returned to the user; a reviewer that edits production code costs a point per event.

## 5. Delegation and ownership

Follow `docs/agents.md`. One writer per artifact class. Record each launched agent's native ID, role, model, assigned paths and handoffs. You alone assemble `docs/agent-runs/phase-11/**` from agent reports.

| Agent | Owns | Subphases |
|---|---|---|
| `test-engineer` | `tests/**`: all adversarial, contract and end-to-end tests; the requirement-coverage table in `test-report.md` content (the coordinator assembles the file). Writes **no** production code | 11A–11B, reruns in 11C |
| `build-engineer` | `build.sbt`, `project/**`: the `ExposedDefect` tag exclusion if needed | on demand |
| Module owners (`hadoop-engineer`, `entity-resolution-engineer`, `spark-engineer`, `storage-engineer`, `rag-engineer`, `service-engineer`, `domain-engineer`) | Repairs to their own artifacts, each receiving only its findings | 11C repair loop |
| `code-reviewer` / user-launched reviewer | Read-only. The coordinator never launches it | 11C, via the user |

## 6. Global rules for every subphase

1. **Ask first.** Step 0 of every subphase: list your questions, including the subphase's "Open questions" that are still open, each with a recommended default. Wait for the user's answers. If none, write "No questions for this subphase" and proceed.
2. **Preflight.** Record `git status --short`, the branch and HEAD as this subphase's **base SHA**. If the previous subphase's changes are still uncommitted, ask the user whether to proceed or wait for their commit. Never reset or discard changes you did not make.
3. **JDK 17 for every sbt command** (Section 2). Report `java -version` in the first gate of each subphase.
4. **One writer per artifact.** Route every edit to the owner in Section 5 and `docs/agents.md`. An unlisted path is an orphan: stop and ask the user. Out-of-scope work is returned as `BLOCKED-ON <owner>` with evidence.
5. **Secrets.** Never read or print `.env`, private keys, tokens, generated credentials or secret directories. Secrets live in AWS Secrets Manager or approved local placeholders, never in tracked files, logs, prompts, Terraform source or plans.
6. **Cloud and money gates.** All AWS infrastructure is authored in Terraform. Live apply, deployment, costly scale changes, data destruction, security changes and rollback require the human gate recorded in the phase evidence. Do not run any command that creates, changes or deletes a cloud resource, or that calls a paid model provider, unless this subphase's text and the user's recorded approval allow it. Unit and contract tests use fakes.
7. **Configuration, not constants.** No hardcoded bucket names, endpoints, account IDs, regions, thresholds or model IDs without a configuration entry and a short rationale (the course deducts for this).
8. **Observability.** Structured logs with trace/run IDs; no secrets or full sensitive payloads in logs.
9. **Every behavior change has tests**, written from the stated requirement, not by re-running the implementation's own logic. Module owners add tests under their module's `src/test/**`; `test-engineer` adds independent tests under `tests/**`.
10. **Provenance.** Data transformations and runtime claims keep source and run provenance. An LLM may never invent a researcher identity, path, score or evidence.
11. **Evidence stays lean.** Put exact commands, exit codes, test counts and meaningful log excerpts under `docs/agent-runs/phase-11/evidence/<subphase>/`; summarize in `owner-report.md` and `test-report.md`. Do not commit full datasets, run outputs or large inventories. Human decisions (`human-gate.md`, `commit.txt`, any approval record) are written only by the user; never write or rewrite them.
12. **Reports** use exactly these fields: `STATUS`, `OWNER`, `WORK ORDER`, `FILES CREATED`, `FILES MODIFIED`, `COMMANDS RUN`, `TEST RESULTS`, `VALIDATION RESULTS`, `ASSUMPTIONS`, `RISKS`, `MANUAL ACTION REQUIRED`, `BLOCKED-ON OWNER`, `BLOCKED-ON EVIDENCE`, `NEXT GATE`. Never report an unobserved pass; list unrun commands as unverified.
13. **No commits or pushes by agents.** The user commits, normally once per approved subphase on a `phase-11` branch.
14. **Lean scope (about 30 days remain before the 2026-11-25 deadline).** Implement what the baseline and rubric require. Do not add optional components (OpenSearch, CI workflows, extra indexes or services) unless the user asks. Record each omission in the owner report so the final report can disclose it.
15. **Stop at the boundary.** When the subphase is done or blocked: ensure no subagents, builds or jobs are still running; return the handoff packet and the reviewer prompt (Section 10); end the turn with **"Subphase 11X is ready for review. I have stopped and will not start the next subphase until I receive the next prompt."**

## 7. Design (binding unless a subphase question changes it)

### 7.1 Required categories (from the course)

Each category below needs at least one test, with the existing coverage mapped first. Use the right owner module's public interface.

**Data plane (11A):**

1. Malformed and truncated DBLP XML; entity declarations; multiline titles; Unicode; records near split boundaries.
2. Unicode normalization and confusable characters in author names (NFC vs NFD, look-alike letters), including the DBLP homonym suffix.
3. Duplicate and conflicting DOI records.
4. Common author names and reordered author lists.
5. Very large blocking groups (the Hadoop candidate limits must hold).
6. Coauthor edges with unresolved or conflicting researcher endpoints.
7. Empty and disconnected graphs.
8. Known-graph cases for distinct degree, components, shortest path, bridge measures and k-core (extend the Phase 6 G1–G4 fixtures with new shapes, for example a barbell, a ring, a clique with pendant nodes).
9. Large-team pair expansion (n(n-1)/2) and common-name researcher resolution.
10. Missing topic, institution, abstract or researcher-profile metadata.
11. Replayed pipeline runs and output-gate behavior (same inputs → identical sorted-row hashes).

**Runtime plane (11B):**

12. Duplicate vector keys and stale model versions.
13. Prompt injection in title, abstract and full-text chunks (instruction text, tool-call text, JSON that mimics a plan).
14. LLM malformed JSON and fabricated identifiers.
15. Unsupported answer claims and claims citing nonexistent evidence.
16. Neptune timeout; DynamoDB conditional-write conflict; S3 Vectors throttling or transient failure (through fault-injecting fakes).
17. Replayed workflow and idempotency (same `Idempotency-Key`; same message twice).
18. API authentication, authorization, malformed bodies and timeouts.
19. Logging redaction (a secret in a config, header or exception never appears in logs or responses).
20. Configuration omissions (a missing required value fails fast with a clear error, not a default that hides it).

### 7.2 Test-plan rules

- Tests are written from the **requirement**, with expectations derived by hand, not by running the code and pasting its output.
- A test that passes only because it mirrors the implementation's own logic is a defect in the test.
- Mutation spot-check: for at least five important behaviors, temporarily reasoning (not editing production code) about whether the test would fail if the behavior were broken; record the five in the report. If a test would still pass with the behavior broken, strengthen it.
- Exact counts are reported: total tests, new tests, per-category counts, `ExposedDefect` count.

### 7.3 Whole-repository review (11C)

The reviewer prompt produced in 11C covers the complete repository and the full current diff and must follow the course review order:

1. Correctness and data loss. 2. Contract and schema drift. 3. Artifact ownership violations. 4. Security, secrets, IAM assumptions and injection risks. 5. Hadoop and Spark distribution mistakes. 6. Entity-resolution over-merging and unreported uncertainty. 7. Storage idempotency and provenance. 8. RAG grounding and unsupported claims. 9. API behavior and failure handling. 10. Tests that would pass even if the behavior were broken. 11. Documentation claims not supported by implementation. 12. Cost and cleanup risks.

For each finding: severity, file and line, concrete failure input, expected impact and owning agent; verified against the actual files. The verdict is `APPROVE` or `REQUEST_CHANGES`. The reviewer edits nothing.

### 7.4 Repair loop

1. The coordinator groups the reviewer's findings by owner and records them in `repairs.md`.
2. Each owning agent receives only its findings plus the context it needs.
3. The agent fixes its owned artifacts and runs its gate.
4. `test-engineer` reruns the relevant adversarial tests (and removes `ExposedDefect` tags only with the owner's repair evidence, through the owner or build-engineer as appropriate).
5. The user launches a fresh reviewer on the complete diff.
6. Repeat until APPROVE or human escalation. Each repair round is its own stop point with its own reviewer prompt.

## 8. Subphases

Execute the subphases in order: 11A → 11B → 11C. Each subphase starts only from a prompt produced by the reviewer of the previous one, or from the user. **One subphase per run:** after a subphase's handoff you stop, and the user reviews it before anything else happens. Never chain subphases together. Every subphase has the same frame:

> **Step 0 — Questions.** You may ask the user any question before implementing. Ask the open questions below that are still open, plus any of your own, each with a recommended default. Wait for answers.
> **Step N — Handoff and stop.** Do not trigger any code reviewer. Return the handoff packet and the copyable reviewer prompt (Section 10), then end your turn. Do not start the next subphase.

### Subphase 11A — Adversarial tests: data plane

**Owners:** `test-engineer` (primary), `build-engineer` (only for the `ExposedDefect` exclusion).

**Open questions:** 11-1, 11-2.

**Tasks:**

1. Inventory existing coverage for categories 1–11 and record the gaps.
2. Write the missing adversarial tests under `tests/**` (prefix `Adversarial`). No production edits.
3. Run the new tests and the full `sbt check`. Any test that fails because of a production defect gets the `ExposedDefect` tag per the user's answer to 11-1, and is listed with owner, input, expected and actual behavior.
4. Report exact counts and a requirement-coverage table for categories 1–11, plus the five mutation spot-checks.

**Done when:** categories 1–11 are covered (or each gap is explained); `sbt check` is green with defects tagged; the defect list is complete.

> **⛔ STOP after 11A.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 11B until the user sends a new prompt.

### Subphase 11B — Adversarial tests: runtime plane

**Start condition:** Phases 9 and 10 are committed.

**Owners:** `test-engineer`.

**Tasks:**

1. Same method for categories 12–20 using fault-injecting fakes (a fake store that times out, throttles, or raises a conditional conflict on demand; a scripted LLM that returns malformed or malicious output).
2. Include end-to-end injection cases through the full workflow and the HTTP layer.
3. Run all tests that do not require live AWS. Do **not** run any live AWS profile.
4. Report exact counts, the coverage table for categories 12–20, the updated defect list and the five mutation spot-checks for the runtime plane.

**Done when:** categories 12–20 are covered; `sbt check` is green with defects tagged; the combined defect list is complete.

> **⛔ STOP after 11B.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 11C until the user sends a new prompt.

### Subphase 11C — Whole-repository review prompt and repair loop

**Owners:** coordinator (assembly only); module owners for repairs; `test-engineer` reruns.

**Open question:** 11-3.

**Tasks:**

1. Assemble `docs/agent-runs/phase-11/` evidence: both test reports, the defect list, the coverage tables.
2. Produce **one** whole-repository reviewer prompt (Section 7.3 order, the user's base commit, the defect list as context, the ownership map) in a fenced code block. The user runs it in a separate agent.
3. When the user returns the reviewer's verdict: on REQUEST_CHANGES, group findings by owner, log them in `repairs.md`, run the repair loop one owner batch at a time, and after each round return a **recheck** reviewer prompt. Stop after each round.
4. Never launch a reviewer and never repair findings yourself.

**Done when:** no critical or major verified finding remains; every production behavior has a relevant test; all tests pass under their declared profiles; no reviewer wrote production code; repair records name owners and rerun evidence; the final reviewer verdict is APPROVE.

> **⛔ STOP after 11C.** Return the handoff packet and reviewer prompt, then end your turn. The phase closes only after the user's own review and `human-gate.md`.

## 9. Required test matrix

| Area | Minimum meaningful cases |
|---|---|
| Coverage accounting | A table mapping each of the 20 course categories to test names, with gaps explained |
| Data plane | Categories 1–11 (Section 7.1), each with at least one adversarial test |
| Runtime plane | Categories 12–20, each with at least one adversarial test |
| Defect handling | Every `ExposedDefect` test has owner, input, expected behavior and actual behavior listed; none is silently skipped |
| Independence | No production file changed by `test-engineer`; the diff of production paths in 11A and 11B is empty |
| Strength | Five mutation spot-checks per plane recorded with reasoning |

Tests assert required behavior from hand-derived expectations, not by re-running the implementation's own logic.

## 10. Handoff protocol and reviewer prompt

At the end of **every subphase and every repair round**, return a handoff packet to the user containing:

- Status (complete or blocked).
- Base SHA, branch and HEAD.
- Changed and untracked files.
- Exact commands with exit codes and test counts.
- Evidence paths.
- Answers the user gave in Step 0.
- Limitations and manual actions.
- **The complete reviewer prompt in one fenced code block**, with every placeholder filled with real values.

Then stop. **Never launch a reviewer.** The user pastes the prompt into a separate reviewer agent. That reviewer returns its verdict **and** the next prompt for you.

When you receive a prompt that came from the reviewer, first append the reviewer's verdict verbatim to `docs/agent-runs/phase-11/review.md` under the subphase heading, marked "user-supplied external review". On REQUEST-CHANGES, log the routed findings in `repairs.md`. Then do what the prompt asks.

**Template you must complete and give to the user:**

````text
You are the independent, read-only code reviewer for ScholarChain Phase 11,
Subphase [11X] [repair round N, if any], in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase11.md — Sections 3–7 and
   Subphase [11X] in Section 8 (scope, owners, open questions, tasks,
   "Done when").
3. The course Phase 11 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-11-adversarial-testing-and-full-repository-review
4. docs/agent-runs/phase-11/prompt.md, owner-report.md and test-report.md
   (Subphase [11X] sections), and evidence under
   docs/agent-runs/phase-11/evidence/[11x]/.

Checkpoint facts (filled in by the manager):
- Branch: [branch]   Subphase base SHA: [sha]   Current HEAD: [sha]
- Changed tracked files: [list]   Untracked files: [list]
- User answers to Step 0 questions: [answers]
- Commands run, exit codes, test counts: [exact results]
- Evidence paths: [paths]
- Known limitations / items deferred to later subphases: [list]
- Prior findings and repair evidence (repair rounds only): [list]

Review rules:
- Read-only. Do not edit files, run builds or tests, call AWS or any
  provider, change data, commit or push. Do not read secrets.
- Inspect `git diff [base]` plus untracked files. Report ALL confirmed
  findings in one pass.
- Check, as applicable to Subphase [11X]: ownership (one writer per path,
  per docs/agents.md and the plan's Section 5); no hardcoded
  buckets/endpoints/account IDs/models; no secrets in files, logs or
  evidence; honest evidence (claimed results match retained logs);
  required tests exist and assert hand-derived expectations;
  cloud/spend gates respected; lean-scope omissions recorded.
- Also check for Phase 11: the test agent changed no production file (check the diff by path); every test asserts a hand-derived expectation; fault-injection tests really inject the fault; `ExposedDefect` tests are listed, not hidden; the coverage table matches the tests that exist; for 11C, the whole-repo review followed the 12-point order and every finding was verified against the files.
- Do not demand work the plan assigns to a later subphase; list it as
  future scope. Distinguish blockers, nonblocking observations and
  unverified gates.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase [11X].
2. Findings: severity, path:line, evidence/reasoning, impact, owning agent,
   acceptance check, blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A NEXT PROMPT for the main agent, in one fenced code block, that I can
   paste directly:
   - If APPROVE: tell the main agent to (a) append this verdict verbatim to
     docs/agent-runs/phase-11/review.md under "Subphase [11X]",
     (b) confirm the user has committed Subphase [11X] (if not, ask the user),
     (c) start Subphase [next] of /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase11.md
     (or, after the last subphase, tell the user Phase 11 is ready for their
     human-gate and that Phase 12 is next), beginning with Step 0 questions,
     (d) end with a new reviewer prompt per Section 10 without triggering
     any reviewer, and (e) do ONLY that one subphase, then stop and end the
     turn; do not start the subphase after it.
   - If REQUEST-CHANGES: tell the main agent to (a) append this verdict
     verbatim to review.md and the findings to repairs.md, (b) route each
     blocking finding to its owning agent (listed), (c) rerun the affected
     tests and the full sbt check on JDK 17, (d) not start the next
     subphase, (e) return a recheck reviewer prompt per Section 10 without
     triggering any reviewer, and (f) stop and end the turn after the
     repair. Nonblocking findings are listed but not required.
````

## 11. Final checklist (Phase 11 complete)

- [ ] Each subphase was reviewed by a user-launched reviewer; verdicts are retained in `review.md`.
- [ ] All 20 adversarial categories have tests; coverage-by-requirement and exact counts are reported.
- [ ] No production code was changed by the test agent; defects were reported to owners.
- [ ] The whole-repository reviewer ran in the order of Section 7.3 and returned APPROVE (after repair rounds if needed).
- [ ] No critical or major verified finding remains; repair records identify owners and rerun evidence.
- [ ] No reviewer wrote production code.
- [ ] All tests pass under their declared profiles (`sbt check`; live profile deferred to Phase 14).
- [ ] The human wrote `human-gate.md` and `commit.txt`.


## Subphase 11B work-order continuation

User: "now move on phase 11b". Execute only 11B of the external phase11.md plan copied above. The user-supplied 11A APPROVE and full next prompt are retained in review.md and the session. 11A is committed and pushed at d80afb755c649ecc5cda60525a1a0201aceb4c03; Phase 9 and Phase 10 commits are in history. No Step 0 questions remain; prior defect/coverage decisions persist. No production edits, reviewer invocation, live AWS/provider calls, or 11C work. Test-engineer owns new Adversarial* tests; coordinator owns evidence. Apply N1/N2: state formatter rewrites explicitly or use scalafmtCheck, require writing barrier before gates, create gate-start record once immediately before launch and never rewrite. Return the complete reviewer prompt and stop. No human gate or approval record is authorized.

# Phase 6 human acceptance

Recorded: 2026-10-22T15:50:08.289269-05:00 (America/Chicago).

## Decision and authority

**ACCEPTED BY THE HUMAN: Phase 6 local implementation, with the open gates,
deferred findings and limitations below.**

This record transcribes the user's decision, rather than an agent's approval.
After the coordinator summarized the acceptance steps and open items, the user
stated **“I accept”**, then explicitly requested **“please write them for me”**.
That request authorizes the coordinator to write this acceptance record and the
commit-status record on the user's behalf. No previous human decision is changed.

## Accepted local scope and evidence

- The user-supplied independent comprehensive reviewer returned **APPROVE for
  6I and the comprehensive Phase 6 local implementation**, with no blocking
  defect. The complete verdict and N1–N7 are retained verbatim in [review.md](review.md).
- Accepted local scope includes Spark Jobs 1–11, CLI, graph/analytics contracts,
  Parquet exports, load-manifest proposals, module and independent tests, and
  the bounded local Hadoop → offline ER → Spark run and replay evidence.
- The fresh JDK 17 gate passed **554 tests / 0 failures**, exit **0**:
  core 144, Hadoop 64, ER 39, Spark 34, independent 266, build 7. Runtime:
  675.13 seconds; Java 17.0.20.1 and sbt 1.10.7. Full log:
  [final-check.txt](evidence/6i/final-check.txt), 1,359,860 bytes, SHA-256
  `e2bf289d11f6f2e4ff8e714d3fc4b9b56b16ea7ed59007abd00d5fe73d9d7367`.
  These are retained results; no new tests were run to write this record.
- The course traceability and limitations are in [owner-report.md](owner-report.md);
  open/deferred findings and downstream owners are in [repairs.md](repairs.md).

## Explicit EMR deferral acceptance

The human accepts the open gate **“bounded EMR Spark run — deferred to Phase 15,
script in Phase 13”** as a documented project deviation. The course work order
lists the bounded EMR run, even though its Gate bullets do not. Local acceptance
does not mean this course work-order item has been executed or waived by the
instructor.

The known risk is accepted: the retained compatibility memo identifies stock
EMR 7.x Spark 3.5.x as Scala 2.12, while this repository uses Scala 3 with
`spark-sql_2.13`. **No compatible runtime has been selected or tested.** The
custom-runtime work creates schedule and cost risk for Phases 13 and 15.
Runtime alignment, driver/executor class-origin checks, updated wrong-JDK
proof and JDK-guarded release packaging remain assigned later gates.
No cloud deployment, expenditure or AWS action is authorized by this record;
those require their own bounded human approvals.

## Workflow deviation and evidence retention

The human accepts the project's **Codex/Cursor-led workflow deviation** with
repository assignment/Claude artifacts retained. **No instructor approval,
cross-tool equivalence or constitutional ratification is claimed.**

The human accepts retaining the existing Phase 6 evidence, approximately
**15.9 MB**, including full gate logs and raw logs containing trailing whitespace.
The comprehensive reviewer attributed 188 whitespace findings to 17 raw logs;
current and cumulative non-evidence diffs are whitespace-clean. Originals are
retained for provenance. No trimming, deletion, log rewriting or future retention
policy is authorized by this acceptance.

## Accepted open findings and limitations

**N1–N7 and 6FG F4–F12 remain OPEN/nonblocking or deferred**, not repaired by this
acceptance. Scanner blind spots, 6A F4/F6/F8, Scala/EMR alignment and yearless
Neptune mapping also remain open with the owners/gates in [repairs.md](repairs.md).
In particular:

- Community, cross-community, bridge and continuity outputs are iteration-limited;
  all observed real windows reported non-convergence. Isolated-pair oscillation
  does not explain every real changed label. Phase 7–9 consumers must preserve
  `Converged: false` and must not present these as converged results; further
  per-component measurement or a revised converging rule remains open.
- Distance P90 is approximate and has latent partition dependence. Observed
  replay equality is not a guarantee for future inputs.
- The 28 logical tables and counters matched in the retained replay, while the
  operational analytics report differed in 12 numeric fields. Metadata-only reuse,
  fixed 256-shard executor buffering at bounded scale, and replay on identical
  local build artifacts remain limits.
- Real Researcher ER decisions were all zero; identity-merge/constraint branches
  are evidenced by fixtures and the tiny pipeline. No real identity accuracy or
  global recall claim follows from the bounded slice.
- Failed-run retry, summary richness/truncation, continuity observability,
  duplicate datasets, proposed storage keys, README drift, literal driver caps,
  shared-session optimizer setting/cost and plan-destination concurrency remain
  registered work. Dataset Python results remain separate from sbt counts.
- Store proposals are not loaded services. Store-key validation and yearless
  Neptune mapping are Phase 7 gates; summary improvements precede Phase 8.

## Commit status and stopping boundary

Acceptance covers the comprehensively reviewed local implementation and close-out
working tree, with these authorized acceptance records. Existing implementation
commit on `phase-6`: `d1afc7f6698965ddbe010621b277b10e655d25ff`. The final close-out commit is **PENDING** until
the user commits the uncommitted documents. [commit.txt](commit.txt) distinguishes
that pending commit from the existing implementation commit.

This records human acceptance of the local Phase 6 scope; the EMR work-order gate
remains open, and final commit evidence remains pending. The coordinator has not
committed or pushed. **Phase 7 requires a separate user prompt.**

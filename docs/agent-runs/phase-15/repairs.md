# Phase 15 repairs

## Subphase 15A — P0 repair round 1 (from review 1, REQUEST-CHANGES)

Source: the user-supplied external review in `review.md` (Subphase 15A — P0 budget guard (offline), review 1). Severity, owner and acceptance checks are kept as the reviewer gave them.

| ID | Severity / blocking | Owner | Path named by the reviewer | Acceptance check (reviewer) | Repair status |
|---|---|---|---|---|---|
| F1 | Medium / yes | coordinator (assembling the infra-engineer, test-engineer and documentation-engineer reports) | `docs/agent-runs/phase-15/owner-report.md:1-20` | A table of native ID, role, model and effort, assigned paths and handoffs for all three agents, plus each agent's 14-field report (or a consolidated one quoting them). Nothing invented; an unrecorded ID is stated as not recorded. | fixed: table with all three IDs (taken from the session's Agent tool results; none missing), each agent's final report verbatim, and a consolidated 14-field report |
| F2 | Low / no, fix before the commit | documentation-engineer | `docs/runbooks/phase-14-live-session.md:264` | The link to `session-2-plan.md` becomes a code-span path (or the draft is committed); a link check on a worktree of `a576878` plus the P0 patch only shows 0 broken. | fixed by documentation-engineer `ab222e483909f6714`; clean-worktree check: 62 links, 0 broken |
| N1 | Low / no | coordinator | `docs/agent-runs/phase-15/test-report.md:7-10` | Keep the logs with hashes, or label each line "agent-reported; log not retained". | fixed: labelled; the infra-engineer's failed `check.sh --only terraform` run (exit 4) is now recorded too |
| N2 | Info / no | coordinator | plan §6.11 | Optional: commit short excerpts under `docs/agent-runs/phase-15/evidence/15a/`. | not done (optional); `test-report.md` carries the totals and log hashes. Can be added at the user's request before the commit. |
| N3 | Info / no | coordinator | `docs/agent-runs/phase-15/prompt.md:33` | "(answers pending)" becomes "(answered 2026-11-15, below)". | fixed |
| N4 | Info / no, existing before P0 | — | `scripts/billing/budget_execution.py:611-614` | In the 2026-11-17 checklist, record `notifications_visible` from the plan inspection in the receipt. | carried to the 2026-11-17 live-modify checklist (prepared after approval) |

### Coordinator observation from the repair verification

| ID | Severity / blocking | Owner | Path | Evidence | Status |
|---|---|---|---|---|---|
| O1 | Low / no, existing before P0 | infra-engineer (`scripts/**`) | `scripts/billing/README.md:38` | The link `[reviewed Terraform input](/Users/…/infra/terraform/billing-bootstrap/main.tf:28)` is an absolute local path with a line suffix, so it is broken in any checkout and shows a local home path. It is identical at `a576878` and is not in the P0 diff. | not fixed (outside the P0 findings); proposed for a later infra-engineer order: a relative link `../../infra/terraform/billing-bootstrap/main.tf` |

### Status after review 2 (recheck, APPROVE, 2026-11-15)

| ID | Status |
|---|---|
| F1, F2, N1, N3 | closed (review 2) |
| N2 | open, optional |
| N4 | deferred to the 2026-11-17 live-modify checklist |
| N5 (review 2, Info) | fixed: the review 1 heading in `review.md` now says "sections 1–3 verbatim as pasted … section 4 followed, see repairs.md" |
| O1 | future scope: infra-engineer, `scripts/billing/README.md:38` to the relative link `../../infra/terraform/billing-bootstrap/main.tf` |

### Repair evidence (round 1)

- Agent report: `owner-report.md`, "Work order 1: P0 repair round 1". Coordinator runs: `test-report.md`, "Work order 1: P0 repair round 1".
- New P0 patch sha256 `ede0052faf4f066eea436b67c5e75b76bff22807fa2ee27040d806123055d6fb`; with line 264 reverted it reproduces the round-0 hash `def2c281…76d4f`, so the round-1 tracked change is that line only.
- `sbt check` not rerun (no Scala, build or test input changed); the P0 evidence stands (log sha256 `6c2f5e7e…f4960`).
- No AWS, Anthropic or Voyage call; nothing committed; no reviewer launched.

## Work order 2: P40 internal repair round 1 (before review, 2026-11-15)

Source: the test-engineer's independent suite (P40-T), not an external review. No external review of P40 has happened yet. Agent reports: `owner-report.md`, "Work order 2".

| ID | Severity / blocking | Found by | Owner | Path | Defect | Repair status |
|---|---|---|---|---|---|---|
| T1 | High / yes | test-engineer (`AdversarialPublicSemanticHttpSpec`, 13 of 14) | service-engineer | `modules/services/.../PublicSemanticRoute.scala` (`validate`), and the shared /v1 parse path | A body of about 8 KiB nested deeply, for example `"["*4096+"]"*4096`, overflowed the recursive `ujson.read`. The result was HTTP 500 and a printed StackOverflowError. | fixed by service-engineer `a72af9596c8a90dc4`. The new `RequestJson.withinDepth` is a non-recursive pre-scan with `MaxNestingDepth = 32`, applied before `ujson.read` in `PublicSemanticRoute.validate`, `QueryRequest.parse` and `SemanticApi.retrieve`. A `StackOverflowError` backstop in `ApiApplication.handle` returns a typed 500 and prints nothing. `RequestNestingSpec` has 10 tests, including the negative control that fails 5 tests when the guard is off. The independent suite is now 14/14 (agent-reported; the coordinator's `sbt check` is exit 0 with 1639/0/1, see `test-report.md`). |
| T1-side | Info / no | service-engineer | service-engineer | `ApiContracts.scala` (`/v1/query`) | Behaviour change: a body nested deeper than 32 levels now gets 400 `INVALID_REQUEST` instead of 422 `UNSUPPORTED_QUERY`. | documented in `modules/services/README.md` and the OpenAPI |
| T2 (a) | Low / no | test-engineer | service-engineer | `PublicSemanticRoute.scala` (`project`) | The route passed through more hits than topK when the downstream returned them, although the OpenAPI says at most topK. | fixed: `hits.take(topK)`, order kept, tested |
| T2 (b) | Low / no, existed before P40 | test-engineer | service-engineer | all `/v1` routes | A lower-case `bearer` scheme gets 401. RFC 7235 says the scheme is case-insensitive. | recorded only (coordinator decision); consistent across routes |
| T2 (c) | Low / no, existed before P40 | test-engineer | service-engineer | query-api internal semantic route | Forwarded shallow non-object bodies (needs the internal token). | recorded only. The depth limit now also covers the internal route (deep bodies get 400). |

### Coordinator observations (P40, not repaired)

| ID | Severity / blocking | Owner | Path | Evidence | Status |
|---|---|---|---|---|---|
| S1 | Low / no | infra-engineer | `scripts/smoke-local.sh` (`--build`) | `--build` packages only when `modules/services/target/distribution` is missing. It reused a services.jar built before P40, so the first coordinator run failed `smoke-semantic` with a 404 and exit 4 (`test-report.md`). It passed after `sbt -batch packageServices`. | proposed follow-up: `--build` should always package (or compare the jar with the sources). Until then, run `sbt -batch packageServices` first. |
| S2 | Low / no, existed before P40 | service-engineer | Cask default handler (`ApiApplication`) | When a reply is written after the caller has closed the socket, a `ClosedChannelException` stack trace is printed (seen in tests with a deliberately slow downstream). | **decision pending** (coordinator or user): leave it, or handle it quietly in a later order |
| S3 | Low / no | factory-engineer | the PostToolUse scalafmt hook script (`format-scala.sh`) | The hook runs sbt under Java 27, resolves the edited path against every subproject ("Failed to read ..."), starts sbt between agents' runs, and once rewrote a test file into code that did not parse (repaired by the service-engineer). | proposed follow-up for the factory-engineer (constitutional path; human ratification needed) |
| S4 | Info / no | documentation-engineer | `docs/runbooks/session-2-plan.md` (P40-D) | A rule slip: a recursive grep matched local `terraform.tfstate*` lines, and the output had an account ID. Nothing was used or written; the coordinator's grep of the plan found 0 twelve-digit numbers. | disclosed in `owner-report.md`. Later briefs require `--exclude='*.tfstate*'`. |

## Work order 2: P40 review round 1 (review 1, APPROVE, 2026-11-16)

Source: the user-supplied external review in `review.md` ("Work order 2 — P40 …", review 1). No finding is blocking, so none was repaired before the commit. Severity, owner and path are as the reviewer gave them.

| ID | Severity / blocking | Owner | Path | Finding | Status |
|---|---|---|---|---|---|
| R1 | Info / no | coordinator (records) / rag-engineer | `CachingEmbeddingClient.scala:35,83,105`; `modules/rag/README.md` | **Recorded deviation from accepted default (c):** the cache key is provider + model tag + SHA-256 of the text, with no explicit input type. That is safe today because only the query-purpose client is wrapped (`AwsComposition.scala:251`, `AwsPorts.scala:343`). If a document-purpose client is ever wrapped, the input type must be added to the key first. | recorded (this row); a key change would be a later rag-engineer order |
| R2 | Low / no, future scope | experiment-engineer / coordinator | `AwsComposition.scala:257`; plan F25 | In aws mode `embedding_cache_*` exist only on semantic-service `/metrics`, which the ALB does not route to. The R-b claim "Voyage calls ≤ distinct questions per task" needs another source (for example Voyage usage) or must be stated as unverified. | open: P42 / Session 2 runbook |
| R3 | Low / no | documentation-engineer | `docs/runbooks/session-2-plan.md:581` | The plan says `SemanticApi.scala` line 98 makes the QueryVectors call. Line 98 is the embed call; `vectors.query` is at line 100. | open: fix in the plan draft before the Session 2 plan approval |
| R4 | Info / no | — | `smoke-local-p40-r2.log` (hits=0) | The offline store is empty, so the smoke checks only the reply shape. Projection of non-empty hits is covered by tests. | recorded |
| R5 | Low / no (same as S1) | infra-engineer | `scripts/smoke-local.sh --build` | Stale jar risk. | open as S1; before P35, run `sbt -batch packageServices` explicitly |

## Work order 3: P41 internal repair round 1 (coordinator gate, 2026-11-16)

Source: the coordinator's clean-snapshot `check.sh` run 1 (`test-report.md`, "Work order 3"). This was before any review.

| ID | Severity / blocking | Owner | Path | Defect | Repair status |
|---|---|---|---|---|---|
| G1 | High / yes (gate FAIL) | infra-engineer | `infra/terraform/phase15-variables.tf` (new root file); `scripts/tests/test_terraform_r1.py:57-67` | The r1 fixture copies only tracked `infra/terraform` files, so the new untracked root variables file was missing and `main.tf:140-142` referred to undeclared variables. `scripts/tests` failed 7 of 1078. | fixed by the infra-engineer: the three variables moved unchanged into `phase12b-variables.tf` (lines 430-464) and `phase15-variables.tf` was deleted, with references updated. This also closes the gap in `tests/infra/runtime_shape_checks.py:31`. Agent-reported: `test_terraform_r1` 10 OK, terraform test 304 passed. Coordinator rerun pending (run 2). |
| G1-proc | Info / no | coordinator | — | The coordinator removed the run-1 worktree before reading the per-suite log. | process fix: per-suite logs are now copied to `target/phase15/p41/r1/check-logs/` before the worktree is removed |

### P41 review 1 (code-reviewer, APPROVE, 2026-11-16): nonblocking findings

| ID | Severity | Owner | Path | Status |
|---|---|---|---|---|
| F1 | Low | coordinator | `owner-report.md` | fixed before the commit: the repair-1 report is reproduced verbatim, and the follow-up about `ROOT_VARIABLE_FILES` is marked closed by G1 |
| F2 | Low | infra-engineer | `infra/terraform/README.md:883-884`, `phase12b-variables.tf:432-433`, `modules/runtime/variables.tf:178-179`, `course.local.tfvars.example:166-167` | open, routed to the elasticity bundle. Reword "With all three null the plan is the same as before": with the ALB present and the dashboard on, the panel is added regardless of these variables. |
| F3 | Low | infra-engineer | `infra/terraform/tests/phase15_p41*.tftest.hcl` | open, routed to the elasticity bundle: add a fractional-burst refusal run and a module run on the ACM path (`https_enabled = true`, `certificate_arn = null`, target 600) asserting one policy |
| F4 | Info | infra-engineer (P9) | observability dashboard | P9 scope: reduce the dashboard to ≤ 50 metrics |
| F5 | Info | human (Session 2) | live | not verifiable offline: the RequestCountPerTarget dimension, the ResourceLabel being accepted, and deployer coverage of the TargetTracking-* alarms |
| F6 | Info | coordinator | `test-report.md` | the run 2 RESULT line is recorded before the commit |
| F7 | Info | test-engineer (optional, deferred) | `tests/infra/test_runtime_shape_14b.py:64-71` | deferred by the user's time priority |

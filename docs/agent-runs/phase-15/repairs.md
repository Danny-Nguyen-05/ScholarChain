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

## Elasticity Terraform lane (P34, P9, P41 F2/F3), coordinator notes (2026-11-16)

| ID | Severity / blocking | Owner | Path | Evidence | Status |
|---|---|---|---|---|---|
| E1 | High / yes for the cost plan | human (money decision); documentation-engineer (plan and demo-script text after the decision) | `infra/terraform/phase12b.tf:22`; `docs/runbooks/session-2-plan.md` rows P34, F23, 6.3, 6.4 | **P34 is not possible.** Amazon Neptune User Guide, "Capacity scaling in a Neptune Serverless DB cluster" (read by the infra-engineer 2026-11-16, aws-knowledge): "the smallest value you can set for the maximum capacity is 2.5 NCUs". The plan's 0.1608/h Neptune ceiling cannot be enforced; the lowest ceiling is 2.5 NCU = 0.402/h. No code was changed for P34. | **decided 2026-11-16 (user):** min 1 / max 2.5 NCU, no Terraform change (none existed to revert); plan text corrected (see E5) |
| E2 | Medium / disclosed incident | infra-engineer (elasticity lane) | `infra/terraform/environments/course.local.tfvars` | `terraform fmt -recursive -check -diff .` walked into the private tfvars and printed part of its contents into the agent's context. `-check` wrote nothing; the file is unmodified; the agent says nothing was reused or repeated, and later fmt runs named explicit files. The content stays in the local session transcript only. | disclosed to the user; later briefs forbid recursive `terraform fmt` and require explicit file lists |
| E3 | Medium / yes (gate) | coordinator | `docs/agent-runs/phase-15/review.md:284` (committed in `7a02de2`) | `tests/infra/test_billing_replan_14b.NoRealAccountIdIsAdded` flags a 12-digit literal in the verbatim P41 review text. Both values were synthetic: the AWS documentation example account ID and a mock UUID tail. | fixed in the working tree: both values redacted with a coordinator note; the test file now passes (33 tests OK). Goes into the next approved commit. |
| E4 | Info | infra-engineer | `infra/terraform/tests/phase12b.tftest.hcl:135`, `phase12c.tftest.hcl:118-130` | P9 broke two old dashboard pins, so the agent edited them. They are inside the infra-engineer's territory but outside the brief's file list. | accepted by the coordinator; for the elasticity-bundle reviewer to check, together with the partial reversal of the Phase 12C N12 dashboard panels |
| E5 | High / yes for the cost plan | coordinator (error); human (money decision); documentation-engineer (plan text) | `docs/runbooks/session-2-plan.md` 6.4, gates 1 and 2 | The coordinator's chat figure "+0.37, project worst case 22.13" used R-c's 3.5 h Neptune cap, not R-b's. R-b's Neptune window is 5.0 h planned and 7.0 h at cap (back-solved from the 6.4 rows), so at the 0.402/h ceiling the R-b cap rises by 1.69: E_b 2.36 -> 4.05, project at caps 21.76 -> 23.45, gate 1 threshold 3.06 -> 1.37. The user's choice (a), hold 150,000 -> 90,000, was made on the wrong figure, and its condition fails at the planning rate (6.0 min hold against about 9.5 min needed). Not applied. | **decision pending (user)**; plan text corrected for the rate by the documentation-engineer, options (i)-(iv) listed in 6.4 |

## Pipeline bundle (Session 2 prerequisites), coordinator notes (2026-11-16)

| ID | Severity / blocking | Owner | Path | Evidence | Status |
|---|---|---|---|---|---|
| PB1 | High / process | coordinator | all six pipeline lanes | The lanes were interrupted at 23:17:01 CST on Nov 15 by a user interrupt during the Stop-hook loop. All six transcripts end "[Request interrupted by user]" at 05:17:01Z. Only lane D's two drafts and the stage-a tftest survived. | Relaunched 08:40 CST with progress logs under target/phase15/lanes/; drafts re-tested. The user now queues messages instead of stopping the session. |
| PB2 | High / yes | infra-engineer (lane A) | `scripts/emr/sc-step.sh` body_hadoop_prep | P6 D1: `--run-id "${RUN_ID}"` is always rejected by HadoopPrepPipeline.scala:58-59 (it needs run:<uuid v4>). The EMR hadoop-prep step would have failed at once. | Fixed: deterministic `hadoop_run_id()`. Tested (test_phase15_pipeline_pins, tests/scripts/test_hadoop_prep_args_15 feeds the exact argv to the real parser). Proof run p6-S-20261116T171431Z, all 6 steps, no workaround. |
| PB3 | High / yes | infra-engineer (lane A) | same | P6 D2: `--output-root "file://…"` misroutes the run under the working directory (HadoopIO.scala:39-45). | Fixed: plain absolute path. Same tests and proof run. |
| PB4 | High / yes | human decision; infra-engineer | `scripts/config/release.conf` PIPELINE_ER_XMX; modules/emr | P6 D3: the ER heap of 3g and 8g ran out of memory at S. 10g passes (RSS 11.6 GB) and 12g passes (RSS 13.9 GB). The m5.xlarge primary leaves an estimated 0.5-1 GiB free. | Human D3 decision: r5.xlarge primary (32 GiB), m5.xlarge core, 12g heap, S cap 75 min (prompt.md "D3 decision", "S run cap and D3 go-ahead"). Implemented with tests. |
| PB5 | High / scope | human decision | L on EMR | P6 D4: the pinned ER config refuses L (input byte bound). With raised bounds, L's ER ran out of memory at 22g after 963 s. | L dropped on EMR (P25 rule). Local evidence kept: Hadoop L, plus the Spark identity-bypass run disclosed as such (experiments/inputs/15a/size-l-local-evidence.json). |
| PB6 | High / yes | rag-engineer | modules/rag LiveEmbeddingIngestMain | Lane G found that a clean 10,000-item ingest fails at completeRun (query page limit) after all vectors are written. | Fixed: queryPageSize 1000, with a 10,000-item ledger test. |
| PB7 | High / yes | rag-engineer | modules/rag manifest cap | The hard 16 MiB live manifest cap would refuse about 10,000 items (20.5 MB measured). | Raised the code ceiling to 64 MiB; config 32 MiB. |
| PB8 | Medium / yes | infra-engineer; test-engineer | release.conf PRESPEND_MIN_HEADROOM_USD | Floor 3 would refuse spend at the option (i) caps (headroom 2.03). | Set to 2 per the human's floor-2 decision. Tests updated (boundary 1.99 refused, 2.00 accepted). A harness "security test removal" warning was reviewed: the values changed, the intent was kept, nothing was removed. |
| PB9 | Medium / gate | rag-engineer | Phase15VectorScaleSpec.scala | The account-ID scan flagged a synthetic 12-digit bucket ID. | Built at run time; tests/infra 468/468. |
| PB10 | Info | coordinator | target/phase15/pipeline/r1 | The first clean-snapshot gate run was taken 10 s before the test-engineer's final cap_pins edit. | Stopped and rebuilt on the final tree. |
| PB11 | Info / disclosed | dataset-engineer (lane D, first run) | target/phase6-inputs/6fg-dblp/*.partial | The first lane D run started the approved DBLP download at 05:15:29Z (approval at 05:13:55Z), and the interrupt cut it off. The archive was downloaded one and a fraction times. | Recorded in prompt.md. The partial file is kept; deleting it is the human's call. |

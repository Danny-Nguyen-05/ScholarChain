# Phase 15 reviews

## Subphase 15A — P0 budget guard (offline)

### Review 1 — user-supplied external review (pasted by the user on 2026-11-15; sections 1–3 verbatim as pasted, with the tables flattened by the paste; section 4 followed, see repairs.md)

```text
1. VERDICT: REQUEST-CHANGES for Subphase 15A, work order P0 (budget guard, offline part)
The budget change itself is correct, and the tests and evidence agree with each other. Two problems in the records block approval. Both are fixes to docs and records only; no code needs to change.
Confirmed correct:
The budget is still updated in place. It is still the one aws_budgets_budget.project[0]. The wrapper accepts only actions == ["update"] and an amount change from 200 to 25 (budget_execution.py:588-598).
Amount and period are unchanged. Amount 25, period 2026-10-01 to 2027-01-01, and tags are all the same.
Credits and refunds stay excluded. main.tf:32-33 sets include_credit=false and include_refund=false. This is asserted in budget.tftest.hcl:49, test_billing_replan_14b.py:72-73, and the wrapper's COST_TYPES refusal (budget_execution.py:430-432, test credits_included).
Exactly three alerts at 18, 20 and 22. Each is ACTUAL / ABSOLUTE_VALUE / GREATER_THAN (main.tf:51, USD25_SHAPE, budget_execution.py:66). Terraform, Python and tests/infra each assert this against hand-written values.
Old alert sets are refused before any backup or apply:
The plan check refuses a visible 10/15/20 set with PLAN_NOTIFICATIONS.
The live check refuses USD 25 with 10/15/20 alerts as LIVE_STATE_UNEXPECTED, before the state backup.
After apply, the readback refuses it as APPLIED_BUT_POST_VERIFY_FAILED.
50/80/100 is refused everywhere.
Pin-refresh instructions are accurate. I ran the documented read-only recompute: stale=7, and the rows match the README list exactly. The last pin refresh was 2eb30ef (2026-11-10). There is no modify key yet. The template sha256 946352f3…0af28 matches. No hash was invented.
The Phase 14 runbook only gained notes: 7 lines added, 0 deleted (git diff --numstat).
The evidence is honest:
git diff a576878 | shasum -a 256 gives def2c281…d4f, the same as the snapshot patch hash.
Both log hashes match the report.
The ScalaTest counts in the sbt log add up to 1567 succeeded, 1 canceled, exit=0, on Homebrew Java 17.0.20.1.
The snapshot log shows RESULT: PARTIAL passed=6 skipped: sbt, exit=5, and every gate count claimed.
The last P0 file was edited at 14:53:43, before the sbt run started at about 14:54, so the sbt run covered the final files.
Ownership: each path belongs to the claimed owner under docs/agents.md. No secrets, account IDs or *.local.tfvars appear in the in-scope files. No live action was taken.
2. Findings
#
Severity
Path:line
Evidence / reasoning
Impact
Owner
Acceptance check
Blocking
F1
Medium
docs/agent-runs/phase-15/owner-report.md:1-20
Two required things are missing. (1) Plan §5 requires each launched agent's native ID, role, model, assigned paths and handoffs. (2) AGENTS.md "Reports", plan §6.12 and docs/agent-runs/README.md require the 14-field report (STATUS … NEXT GATE) and "the owning agent's final report". The file has a coordinator summary table with neither. Phase 14 recorded both (phase-14/owner-report.md:11-12, 19-20). The line "each file was edited by its owner" (:18) therefore can't be checked.
The one-writer check can't be audited, and the record doesn't follow the evidence format.
Coordinator, assembling the infra-engineer, test-engineer and documentation-engineer reports
owner-report.md has a table of native ID, role, model and effort, assigned paths, and handoffs for all three agents, plus each agent's 14-field report (or the coordinator's consolidated 14-field report quoting them). Nothing invented: an ID that wasn't recorded is stated as not recorded.
Yes
F2
Low
docs/runbooks/phase-14-live-session.md:264
The new note links to […](session-2-plan.md). That file is untracked and, on your instructions, stays uncommitted. The 65-link check passed only because the draft was in the working tree, and the clean snapshot also included the drafts.
A commit made as instructed would contain a broken link.
documentation-engineer
Turn the link into a plain code-span path, or commit the draft first. Then a link check on a worktree of a576878 plus the P0 patch only (no untracked drafts) shows 0 broken.
No, but fix it in the same round, before the commit
N1
Low
docs/agent-runs/phase-15/test-report.md:7-10
No retained log backs five claims: the Terraform and Python mutation results, the standalone test_billing_replan_14b 33 OK, the scan-base mutation counts, and the 65-link check. Only the two logs whose hashes are listed exist under target/phase15/p0/. By reading the code I agree the mutations must fail, because the tests contain the literal values 18/20/22.
The evidence is weaker than the logged gates.
Coordinator
Either keep those logs with their hashes, or label each line "agent-reported; log not retained".
No
N2
Info
Plan §6.11
Nothing was committed under docs/agent-runs/phase-15/evidence/15a/ (or p0/). All logs are git-ignored.
A later reader has only test-report.md.
Coordinator
Optional: commit short excerpts (the gate summary and the sbt totals lines).
No
N3
Info
docs/agent-runs/phase-15/prompt.md:33
The heading still says "(answers pending)" although the answers are recorded just below it.
Stale wording.
Coordinator
Change it to "(answered 2026-11-15, below)".
No
N4
Info, existing before P0
scripts/billing/budget_execution.py:611-614
If the plan JSON masks the alert blocks, the thresholds are only checked after apply. The risk is low because the config-copy pins bind main.tf with 18/20/22 and the plan hash is pinned.
It matters only on the live day.
—
In the 2026-11-17 checklist, record notifications_visible from the plan inspection in the receipt.
No
Future scope (not asked of P0):
Your 2026-11-17 live work: the Switch Role check, the pin refresh with the modify object (C2), the gate record, the plan, modify, verify-modified, and the first API readback of CostTypes.
Review of session-2-plan.md and demo-script.md (including line 223).
P40.
Experiments A–F, with their manifests, run records and raw-data hashes. Those Phase 15 checks don't apply here because P0 ran nothing live.
3. Report fields
STATUS: COMPLETE (review); verdict REQUEST-CHANGES
OWNER: code-reviewer
WORK ORDER: Phase 15, Subphase 15A, work order P0 (budget guard, offline part)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN (read-only): git status/rev-parse/diff a576878 (--stat, --numstat, full); git log on reviewed-pins.json and account_scan.py; shasum -a 256 on both P0 logs, the template, and `git diff a576878`; grep/sed reads of the wrapper, tests and records; the README's documented read-only stale-pin recompute (python3 -I, writes nothing)
TEST RESULTS: none run by the reviewer. Retained logs agree with the claims: sbt exit 0, 1567 succeeded / 0 failed / 1 canceled on JDK 17.0.20.1; check.sh --skip sbt exit 5, PARTIAL passed=6, every listed gate count present
VALIDATION RESULTS: P0 patch sha256 def2c281…d4f reproduced; log hashes 6c2f5e7e…960 and 5ec773a2…130821 match; stale=7 matches the README; template hash matches; no modify object; runbook +7/-0
ASSUMPTIONS: the plan document and the course README were not re-read in full beyond plan §§3–8; the logs are authentic local outputs
RISKS: the live modify is unverified until 2026-11-17; alerts are AWS-only and arrive 8–24 h late
MANUAL ACTION REQUIRED: the human's live modify, pin refresh, gate record and commits (later)
BLOCKED-ON OWNER: coordinator (F1); documentation-engineer (F2, recommended)
BLOCKED-ON EVIDENCE: owner-report.md:1-20 (no agent IDs or models, no report fields); phase-14-live-session.md:264 (link to an untracked draft)
NEXT GATE: records-only repair round, then recheck review
```

The reviewer's NEXT PROMPT (section 4) was followed as the coordinator's repair-round instructions; see `repairs.md`, "Subphase 15A — P0 repair round 1".

### Review 2 (recheck) — user-supplied external review (pasted by the user on 2026-11-15; sections 1–3 verbatim as pasted, with the tables flattened by the paste; section 4 followed)

```text
1. VERDICT: APPROVE for Subphase 15A, work order P0 (offline part), recheck
Every finding from review 1 is closed or deferred as agreed. The repair changed nothing except line 264 of the runbook and the Phase 15 records, and I found no regressions or new blocking findings. The P0 checks from review 1 still pass, because the code, tests and wrapper files are byte-identical to the reviewed version: every one has its 14:38–14:53 modification time, and the round-0 patch hash reproduces exactly.
2. Findings
Earlier findings:
ID
Status
Evidence
F1 (Medium, blocking)
Closed
owner-report.md:9-17 has the agent table: native IDs, Opus 5.5 at high effort, assigned paths, and handoffs. A consolidated 14-field report is at :36-53, and the agents' reports follow at :55-315 and :329-373. I checked the agents' own transcript files (read-only). All four IDs exist with the matching role, model claude-opus-5-5, effort high, and launch times 20:35 / 20:51 / 00:41 UTC. The round-1 documentation-engineer report (ab222e483909f6714) matches its transcript word for word. For the other three I confirmed the transcripts and the prompts that started them, but did not compare the full report text line by line.
F2 (Low)
Closed
phase-14-live-session.md:264 is now a code span with no link, and the file still shows 7 0 against a576878. I independently rebuilt the old line-264 text and the file's original blob id ff90717, and got the round-0 hash def2c281…76d4f again. So line 264 is the only tracked change. p0-patch-r1.diff is identical to git diff a576878 (sha ede0052f…d6fb). verify-r1.log sha matches (755f145a…38d3) and records 62 links, 0 broken, in a worktree with no untracked files.
N1 (Low)
Closed
test-report.md:5-10 labels each claim "agent-reported; log not retained" or points to a retained log. The infra-engineer's failed check.sh --only terraform run (exit 4) is now recorded (:9), so failures are no longer hidden.
N2 (Info)
Open, optional
No committed evidence excerpts. test-report.md carries the totals and log hashes. Not required.
N3 (Info)
Closed
prompt.md:33 now reads "(answered 2026-11-15, below)".
N4 (Info, existed before P0)
Deferred
Carried to the 2026-11-17 checklist (repairs.md).
Skipping the sbt rerun is justified: only Markdown changed, and check.sh doesn't read this runbook.
New findings (none blocking):
ID
Severity
Path:line
Evidence
Owner
Acceptance
Blocking
N5
Info
docs/agent-runs/phase-15/review.md:7
The heading says "reproduced verbatim", but review 1's section 4 (NEXT PROMPT) is left out and the Markdown tables were flattened by the paste. :108 mentions the prompt was followed.
Coordinator
Optional: change the heading to "sections 1–3 verbatim as pasted; section 4 followed, see repairs.md".
No
O1 (coordinator's own observation)
Low, existed before P0
scripts/billing/README.md:38
Confirmed: there is an absolute local-path link to main.tf:28, and it is also at a576878. It is broken in any other checkout and exposes your local home path.
infra-engineer
A later work order uses the relative link ../../infra/terraform/billing-bootstrap/main.tf.
No (future scope)
Future scope:
The live work on 2026-11-17: the Switch Role check, refreshing the pins plus the modify object at step 10, the gate record, the plan, modify, verify-modified with the first CostTypes readback, and N4.
O1.
Review of session-2-plan.md and demo-script.md.
P40.
Experiments A–F, with manifests, run records and raw-data hashes.
Not verified: anything live (plan, apply, readback, alert delivery); full word-for-word comparison of three of the four agent reports (one was confirmed exact).
3. Report fields
STATUS: COMPLETE (recheck); verdict APPROVE
OWNER: code-reviewer
WORK ORDER: Phase 15, Subphase 15A, work order P0 (budget guard, offline part), recheck after repair round 1
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN (read-only): git status/rev-parse/diff a576878 (--stat, --numstat, full); shasum -a 256 of `git diff a576878`, p0-patch-r1.diff, verify-r1.log; diff of the live patch vs p0-patch-r1.diff (identical); round-0 reconstruction through python3 -I string replace plus `git hash-object --stdin` (no -w) → def2c281…76d4f; stat mtimes of the 12 files; reads of the phase-15 records and scripts/billing/README.md:38; Read of the four subagent transcript files (two Bash read attempts on ~/.claude paths were refused by the PreToolUse guard as possible mutations and were not retried through Bash)
TEST RESULTS: none run by the reviewer; the P0 sbt and check.sh evidence from review 1 stands (hashes re-verified then)
VALIDATION RESULTS: patch ede0052f…d6fb verified; round-1 delta = line 264 only; runbook 7/0; F1 IDs and model/effort verified in transcripts; ab222e… report exact
ASSUMPTIONS: the transcripts under ~/.claude/projects/…/efc32638…/subagents/ are the session's genuine records
RISKS: alerts are AWS-only and arrive 8–24 h late; the live modify is unverified until 2026-11-17
MANUAL ACTION REQUIRED: "Yes, commit" from the user; the 2026-11-17 live modify by the human
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: the user's commit consent, then the human's 2026-11-17 live modify; P40 next
```

The reviewer's NEXT PROMPT (section 4) was followed by the coordinator: this verdict recorded, `repairs.md` statuses updated, commit consent requested.

## Work order 2 — P40 public semantic route and query-embedding cache

### Review 1 — user-supplied external review (pasted by the user on 2026-11-16; sections 1–4 verbatim as pasted, with the tables flattened by the paste; section 5, the NEXT PROMPT, followed)

```text
1. VERDICT: APPROVE
No blocking findings. The code in the tree is byte-identical to the tested snapshot. I compared the 15 code and script diffs file by file against p40-tracked.diff and all 12 untracked files against p40-untracked.tar. Only owner-report.md, repairs.md and test-report.md changed after the snapshot. Every claimed log sha256, test count and exit code matches the retained logs under target/phase15/p40/.

2. Acceptance table (session-2-plan row P40)
#	Check	Status	Evidence
1	Same API key as the other /v1 routes; 401 without it	Met	ApiApplication.scala:170 runs the shared Auth.authorized before any route branch. The route at :200-224 comes after it, so the rate limiter, parsing and the downstream call all run after authentication. The internal token cannot open the public route because the path is not under /internal/. Tests: PublicSemanticRouteSpec:83,105, AdversarialPublicSemanticHttpSpec:176
2	Bounded topK and question length; 400 when exceeded	Met	PublicSemanticRoute.scala:163-191. Order: body size (8,192 UTF-8 bytes), then nesting depth, then ujson.read. Only question, topK and filters are allowed. The question counts code points (1,000). topK must be a whole number from 1 to 20. Filters: at most 16, string values. Off-by-one tests (1,000/1,001 including 1,000 emoji; 8,192/8,193 bytes; topK 0/1/20/21/2.5; filters 16/17): PublicSemanticRouteSpec:170-224, Adversarial…:265
3	Rate limit with a configured per-key rate and a typed 429	Met	PublicSemanticRoute.scala:99-148, wired at ApiApplication.scala:207-215. The limiter runs after authentication and before validation, and a 429 makes no downstream call. The 429 is RATE_LIMITED, retryable, carries Retry-After, and is counted at :212. The environment settings are range-checked at :51-54 and refuse startup with exit 2. Tests: PublicSemanticRouteSpec:232-300, Adversarial…:503,606,641,671
4	Typed errors in the ApiError shape (400/401/429/503/504)	Met	Downstream errors go through the existing allowlisted mapping in RemoteServices.scala:88-110, so the downstream body is never forwarded. 502 DOWNSTREAM_FAILURE is also possible and is documented. Tests: PublicSemanticRouteSpec:370, Adversarial…:763
5	Reply no wider than the internal route	Met	PublicSemanticRoute.scala:197-215 rebuilds the reply from only hits[].{key, distance, metadata} and model, keeping at most the first topK hits. Tests: PublicSemanticRouteSpec:112, RequestNestingSpec:327, Adversarial…:695,736
6	One embed call per distinct question (cache)	Met offline	CachingEmbeddingClient.scala:111-163. Only the query client is wrapped: AwsComposition.scala:251 wraps the client built with EmbeddingPurpose.Query (AwsPorts.scala:343). Tests: SemanticCacheWiringSpec:87-150, Adversarial…:836,880. Smoke run 2: hits went from 0 to 1. Real Voyage calls through the cache are deferred to Session 2
7	No question text in logs	Met	Logs carry only the route template (ApiApplication.scala:246-248). Cache keys hold a SHA-256 only (CachingEmbeddingClient.scala:105). Tests: PublicSemanticRouteSpec:391, Adversarial…:763. The smoke question string appears 0 times in smoke-local-p40-r2.log
8	Unit and service tests for (1)-(7), plus an independent test-engineer API test	Met	Five new suites, all present in sbt-check-p40.log (1639 succeeded / 0 failed / 1 canceled; the canceled one is the existing optional packageRelease probe)
9	The offline-synthetic smoke calls the route	Met	smoke-local.sh passes --semantic offline-synthetic. Run 2 log: RESULT: PASS all 6 checks plus 2 semantic check(s), smoke-exit=0, jar 64d1d190… (matches the jar on disk)
3. Findings (none blocking)
ID	Severity	Path:line	Evidence and impact	Owner	Check	Blocking
R1	Info	CachingEmbeddingClient.scala:35,83,105; modules/rag/README.md	Accepted default (c) names the cache key as (model, input type, hash). The key actually holds provider + model.tag + SHA-256, with no input type. The input type is fixed by the one wrapped query client (AwsPorts.scala:343), which is safe and documented, but it differs from the literal default. Impact: none today. The record should name the deviation so a future document-client wrap is not cached under the same identity.	coordinator (records) / rag-engineer	6	no
R2	Low, future scope (P42 / Session 2)	AwsComposition.scala:257; plan F25	In aws mode, embedding_cache_* exist only on semantic-service /metrics, and the ALB sends every path to query-api. During R-b the “Voyage calls ≤ distinct questions per task” claim cannot be read from these counters through the ALB. P35 (offline, in-process) is unaffected. Session 2 needs another evidence source, for example Voyage usage or a recorded statement that the figure is unverified.	experiment-engineer / coordinator (P42, Session 2 runbook)	6	no
R3	Low (draft doc)	docs/runbooks/session-2-plan.md:581	Says SemanticApi.scala line 98 makes the QueryVectors call. Line 98 is the embed call; vectors.query is at line 100.	documentation-engineer	—	no
R4	Info	smoke-local-p40-r2.log (hits=0)	The offline in-process vector store is empty, so the smoke checks only the reply shape with zero hits. Projection of non-empty hits is covered by unit and independent tests. P35’s offline load is also zero-hit retrieval with no S3 Vectors latency, which the plan already notes.	—	5, 9	no
R5	Low (already S1)	scripts/smoke-local.sh --build	A stale jar gave a 404 in run 1. Before the P35 rehearsal, run sbt -batch packageServices explicitly or fix --build.	infra-engineer	9	no
Security checks that found no defect:

JSON depth pre-scan (RequestJson.scala:29-47): one loop, constant state, O(body). It handles unterminated strings, escaped quotes, a backslash at the end and brackets inside strings; ujson rejects whatever residue the scan lets through.
Parse coverage: all three request-body parses are covered. The remaining ujson.read calls read stored payloads, downstream replies, or an HMAC-verified cursor (GraphApi.scala:144-147).
422→400 on /v1/query: documented in the services README and the OpenAPI.
Token-bucket arithmetic: no overflow (at most about 1e15 units), monotonic clock, negative elapsed time ignored.
Key growth: buckets are created after authentication, so with one configured key only one bucket can exist. maxKeys 1,024 is an extra bound.
Metric labels: a closed set of route templates with a regex guard (ApiApplication.scala:26-29).
Re-serialized forward: the public limits are narrower than the internal ones (8,192 chars / 64 KiB / topK 50), so a forwarded body cannot exceed the internal bounds.
Smoke scripts: they never print the key or a free-text question; --semantic defaults to off; the rate-limit pass-through is regex- and range-checked.
Ownership: matches docs/agents.md.
Hardcoding and secrets: no hardcoded account, bucket, endpoint or model, and no secrets in the bundle (grep clean).
Future scope (not demanded here): Terraform env wiring (P41); load generator, manifest, warm-up and separate 429 reporting (P42); r_S2 measurement and zero 429s (P35); image rebuild (P15); deployed-route and real-Voyage checks (Session 2). Records-only items stay open: S2 (ClosedChannelException decision), S3 (hook, factory-engineer), S4 (disclosed slip), T2(b) and T2(c).

4. Report fields
STATUS: COMPLETE (APPROVE)
OWNER: code-reviewer (independent, read-only)
WORK ORDER: Phase 15 work order 2, P40 public semantic route + query-embedding cache (offline), review 1
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only only: git status/diff (d5e74aa), sed/grep/cat of in-scope files and records; shasum -a 256 of target/phase15/p40/*; per-file comparison of current diff and untracked files against p40-tracked.diff / p40-untracked.tar (extracted to the scratchpad); grep of sbt-check-p40.log, check-skip-sbt-p40.log and the smoke logs; secret/ID grep of the bundle. No build, test, AWS, provider or tfstate access.
TEST RESULTS: not run by the reviewer. Retained logs confirm: sbt -batch check exit 0, 1639/0/1 canceled (9 summary lines summed), tree unchanged before and after; check.sh --skip sbt exit 5, PARTIAL passed=6 skipped: sbt (scripts/tests 1078, tests/scripts 463, tests/infra 465, 0 skipped); smoke-local run 1 exit=4 (404, stale jar); run 2 package-exit=0, smoke-exit=0, jar 64d1d190… equals the jar on disk. All 7 claimed sha256 values match.
VALIDATION RESULTS: acceptance checks (1)-(9) met offline; code identical to the tested snapshot; records' agent-reported counts are labelled as such.
ASSUMPTIONS: the snapshot diff is `git diff HEAD` (16 files including prompt.md), as test-report.md states, rather than the `-- modules scripts` pathspec in the checkpoint facts; the code files are identical either way.
RISKS: R2 (cache counters not observable through the ALB in Session 2); R5 (stale-jar smoke before P35); rate limiter unverified under real load (P35).
MANUAL ACTION REQUIRED: the user's "Yes, commit" for the P40 bundle; decision S2 still pending.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: commit of P40 by Tue 2026-11-17 (cutoff Wed 2026-11-18 12:00 CST); then P41 Step 0.
```

The reviewer's NEXT PROMPT (section 5) is being followed by the coordinator: this verdict is recorded, R1–R5 are in `repairs.md`, and commit consent has been requested. P41 Step 0 starts only after the commit.

## Work order 3 — P41 request-count scaling and rate-limit env wiring

### Review 1 — code-reviewer agent `a3487e61b688909b5` (Opus 5.5, high), launched by the coordinator under the user's 2026-11-16 routing rule; verbatim

````text
## 1. VERDICT: APPROVE for P41 (offline), review 1

I found no blocking defects in the P41 code or tests. There are three non-blocking findings and four informational notes.

**Do not commit yet.** Coordinator run 2 has not finished. The standing consent ("commit right after APPROVE") should apply only after `target/phase15/p41/r1/check-skip-sbt-p41-r1.log` shows a passing `RESULT` line. If run 2 fails, this approval does not cover the failure.

What run 2 showed when I finished (partial log):
- constitution, hooks, shell and python: PASS (lines 14, 22, 53, 57).
- terraform: PASS, with 12/19/113/40/6/301 passed (lines 85-92). 301 = 272 existing + 29 P41 runs. The 3 stage-a runs are not in it, as expected for the P41-only snapshot.
- script-tests had started (line 94) with no output yet. No `RESULT` line. **Gate pending.**

What I checked: I read the frozen diff `target/phase15/p41/r1/p41-tracked.diff` (620 lines; its sha256 `100e3163…2705` matches `target/phase15/p41/r1/p41-snapshot.sha256` line 1), the two untracked test files, and the current tracked files. The current lines match the frozen diff at compute.tf 70-76 and 323-356, observability/main.tf 61-68, README 880-919, phase12b-variables.tf 431-464, main.tf 140-142 and phase12b.tf 164. `phase15-variables.tf` is gone (Glob finds only the two P41 tftest files and the out-of-scope stage-a file).

## 2. Acceptance table

| Item / accepted default | Status | Evidence |
|---|---|---|
| A second target-tracking policy, query-api only | met | `infra/terraform/modules/runtime/compute.tf:333-339`: `resource_id`/`scalable_dimension` from `aws_appautoscaling_target.service["query-api"]`; name `<prefix>-query-api-requests` |
| Metric `ALBRequestCountPerTarget` | met | compute.tf:345-346 |
| `resource_label` = "<alb arn_suffix>/<tg arn_suffix>" | met | compute.tf:347. Tested with the exact string at `tests/phase15_p41.tftest.hcl:182` and `tests/phase15_p41_runtime.tftest.hcl:99`. The owner's mutation M1 (order swapped) was reported killed |
| Exists only with the runtime deployed and the target set; no index error | met | compute.tf:334 uses `var.enabled && var.image_revision != null && target != null`, the same first two terms as `aws_lb.query` (204) and `aws_lb_target_group.query` (217). The `query-api` key in `active_services` (line 2) uses the same condition. Tests: root 203-216; module 116-130 (no image), 132-146 (disabled), 65-87 (target null) |
| Cooldowns 300/60; scale-in on | met | compute.tf:342-344 (`disable_scale_in = false`). Tests: root 190, module 103 |
| CPU policy and target 60 unchanged | met | `http_cpu` (compute.tf:309-322) is untouched in the diff. Tests check keys, target 60, metric type and cooldowns at root 159-162 and 197-200, module 75-78 and 110-113 |
| Root variables (null, or a whole number in range) | met | `phase12b-variables.tf:435-464`. Each is `number`, `nullable`, default `null`. Validation is `x == null ? true : (x >= 1 && x <= max && x == floor(x))`. Bounds: 100000 / 100000 / 1000000. The module copies are at `modules/runtime/variables.tf:182-211` |
| Root-to-module plumbing | met | `main.tf:140-142` maps the root names to `query_requests_per_target_target`, `semantic_rate_limit_per_second` and `semantic_rate_limit_burst` (deviation 3, disclosed in README:906-907 and variables.tf:178-181) |
| Env wiring: query-api, aws mode, independent, strings, not in secrets | met | compute.tf:70-76 has two separate conditional merges inside `aws_role_env["query-api"]`, using `tostring()`. Line 146 emits the role env only `if local.aws_mode`. `secrets` (line 152) is unchanged. The names and bounds match `PublicSemanticRoute.scala:42-48`, and `ServiceMains.scala:83` reads them in both modes. Tests: root 220-276 (rate only, burst only, upper bounds rendered as "100000"/"1000000", query-api only, not in `secrets` at 272-275), root 278-290 (lower bounds), module 175-193 and 195-210 (absent outside aws mode) |
| No cache-size variable | met | No `EMBEDDING_CACHE` reference in the P41 diff |
| One ALB dashboard panel: dimensions and condition | met | `modules/observability/main.tf:65-68`: RequestCountPerTarget by `TargetGroup`; HTTPCode_Target_4XX_Count by `LoadBalancer`+`TargetGroup`; period 60; Sum; y=63, which follows Neptune at y57+6 without overlap. The panel depends only on `alb_metric_dimensions != null` (`modules/runtime/outputs.tf:36-38`, plumbed at `phase12b.tf:164`). Tests: root 294-305, 307-323, 325-336 |
| Panel "within P9's 50-metric limit" | not met; pre-existing, deferred to P9 | My own count of observability/main.tf:3-72 gives 109 base metrics, 114 with Neptune, 120 with Neptune and EMR. P41 adds 2. The dashboard was over 50 before P41 (F5/P9). Disclosed at README:914-916 and in owner-report:1293. Not counted against P41 |
| Precondition (deviation 1) | met; accepted as correct | compute.tf:350-355 checks `local.load_balanced_service == "query-api"` (line 23), which is true exactly when the query-api service is attached to the target group (281-288). It does not block the Session 2 HTTPS path: the plan's 5.2 step 1 and 5.3 step 2 use `api_domain_name`, so `local.acm_validated` and `local.https_enabled` are plan-time true (`phase14b.tf:14-16`), passed in at `main.tf:147`, and give `local.https = true` (compute.tf:15). Tests: module 148-158 (refused) and 160-173 (no target, no HTTPS still plans). Not tested on the ACM path; see F3 |
| Default plan unchanged | met for the default (runtime off) | With all three null and no ALB: count 0, the merges add `{}`, and the panel list is `[]`. The owner reported 0 differing planned addresses (agent-reported). See F2 for the deployed runtime with the dashboard on |
| Tests use hand-derived values, boundaries and the precondition | met, with small gaps | Header derivations at root 5-18 and module 4-11. Boundaries 0/1/max/max+1 for all three; fractional target and rate. Missing: fractional burst, and the ACM path (F3) |
| README and tfvars.example match the code | met, with one wording nit (F2) | README:880-919 and the README:267 ECS row; `course.local.tfvars.example:166-180` are comments only, with no values |
| No hardcoded account IDs, ARNs or endpoints | met | The production code adds none. Every 12-digit match in the two test files is `111122223333` or a `…000000000001` UUID tail (mock values) |
| Ownership | met, from the records | `infra/terraform/**` was written by the infra-engineer (owner-report:1283 and 1288). The coordinator wrote only `docs/agent-runs/phase-15/**`. `check-snapshot-status.txt` lists exactly the P41 files. Authorship is not verifiable from git before the commit |
| Records honest | met, with stale lines (F1) | test-report.md:88-102 labels agent-reported counts. Run 1's FAIL is recorded at test-report.md:106-116 (exit 4, `scripts/tests` 7 failures, log sha256, and the lost per-suite log). The repair is in repairs.md:72-79 |

## 3. Findings

**F1: Low, not blocking. Owner: coordinator (`docs/agent-runs/phase-15/owner-report.md`).**
- Evidence: owner-report.md:1283 still lists `phase15-variables.tf` among the infra-engineer's assigned paths. Line 1296 still lists "`ROOT_VARIABLE_FILES` does not read `phase15-variables.tf`" as an open follow-up, but repairs.md:78 says repair 1 closed it (`tests/infra/runtime_shape_checks.py:31` reads `phase12b-variables.tf`). The infra-engineer's repair-1 final report is not reproduced; it is only summarised in test-report.md:99-102 and repairs.md:78. `docs/agent-runs/README.md:3` asks for the owning agent's final reports in owner-report.
- Impact: a reader of owner-report alone sees the pre-repair layout and an open gap that no longer exists.
- Acceptance check: add a dated "repair 1" subsection to Work order 3 with the infra-engineer's repair report verbatim, and mark line 1296 as closed by G1. Keep the original verbatim report unchanged.

**F2: Low, not blocking. Owner: infra-engineer.**
- Evidence: README.md:883-884 says "With all three `null` the plan is the same as before". Similar wording is at `phase12b-variables.tf:432-433`, `modules/runtime/variables.tf:178-179` and `course.local.tfvars.example:166-167`. But the ALB panel depends only on the ALB existing (observability/main.tf:65, phase12b.tf:164), not on these variables. So any deployed-runtime plan with `dashboard_enabled = true` now changes `aws_cloudwatch_dashboard.elasticity`'s `dashboard_body` (+2 metrics, "known after apply") even with all three null. The owner's "0 differing lines" check compared addresses, not attribute values. This matches accepted default 5, and README:909 states the panel's condition.
- Impact: the claim is accurate only for the runtime-off default. A Session 2 runtime-plan reviewer could be surprised by the dashboard update.
- Acceptance check: reword, for example: "no new resource and no new environment variable; when the ALB exists and the dashboard is on, the dashboard gains the ALB panel regardless of these variables."

**F3: Low, not blocking. Owner: infra-engineer (`infra/terraform/tests/**`).**
- Evidence: there is no refusal test for a fractional burst (for example `query_semantic_rate_limit_burst = 2.5`) at root or module. The `floor` check exists at phase12b-variables.tf:461 and modules/runtime/variables.tf:208 but is never exercised. There is also no run with the target set on the Session 2 HTTPS source (`api_domain_name` at root, or module `https_enabled = true` with `certificate_arn = null`). The existing positive runs all use a literal certificate ARN (root 110, module 43). I traced the logic by reading (compute.tf:15, 23, 352; phase14b.tf:14-16), and it passes the precondition.
- Impact: the configuration actually used in Session 2 is checked only by reading, not by a test.
- Acceptance check: add two runs: a fractional-burst refusal, and a module run with `https_enabled = true, certificate_arn = null, query_requests_per_target_target = 600` asserting one policy. This can follow P41 (for example in the elasticity bundle).

**F4: Info. Owner: P9 (infra-engineer).** The dashboard is above 50 metrics before and after P41 (109+). The reduction is P9 scope.

**F5: Info. Owner: human, Session 2.** Not live-verified:
- the TargetGroup-only `RequestCountPerTarget` dimension;
- AWS accepting the ResourceLabel;
- the deployer's coverage of the new `TargetTracking-*` alarms (`deployer/phase14_main.tf`, as cited by the owner).

**F6: Info. Owner: coordinator.** Run 2 has no `RESULT` line yet, so the gate is pending. Record its result in test-report.md before the commit.

**F7: Info. Owner: test-engineer, optional and deferred by the user (prompt.md:126).** `tests/infra/test_runtime_shape_14b.py:64-71` does not cover `query_requests[0]` or the rate-limit env names.

Future scope, not demanded here: P9 (metric reduction), P35 (values), P42, P15 (images), the pins refresh (human), and the live Session 2 checks.

## 4. Report fields

STATUS: COMPLETE

OWNER: code-reviewer (read-only)

WORK ORDER: Phase 15, Work order 3 (P41), review 1. Branch phase-15, HEAD and base cceb1f5, P41 uncommitted. Bundle: `target/phase15/p41/r1/p41-tracked.diff` (sha256 100e31634ea8b05d3834b6b86b6d28fbbd3bc758e05fb057fc189cbe43f82705) plus `infra/terraform/tests/phase15_p41.tftest.hcl` and `infra/terraform/tests/phase15_p41_runtime.tftest.hcl`.

FILES CREATED: none

FILES MODIFIED: none

COMMANDS RUN: no shell, build, test, terraform, AWS or git commands. Read/Grep/Glob only, on:
- AGENTS.md, CLAUDE.md, docs/agents.md, docs/agent-runs/README.md;
- target/phase15/p41/r1/{p41-tracked.diff, p41-snapshot.sha256, check-snapshot-status.txt, p41-untracked.txt, check-skip-sbt-p41-r1.log};
- infra/terraform/{modules/runtime/compute.tf, modules/observability/main.tf, README.md:878-920, phase14b.tf:1-43};
- both P41 tftest files;
- docs/agent-runs/phase-15/{owner-report.md:1270-1473, test-report.md:84-122, repairs.md:68-80};
- docs/runbooks/session-2-plan.md (lines 171, 243-250, 286-355);
- modules/services/.../PublicSemanticRoute.scala:38-97 and ServiceMains.scala:60-99;
- tests/infra/runtime_shape_checks.py:31 and scripts/tests/test_terraform_r1.py (grep).

No `*.local.tfvars`, state, `.env` or secret file was read.

TEST RESULTS: none run by me. Observed in the run-2 log: terraform gate PASS (301 passed for the main stack); script-tests still running. Everything else is agent-reported (labelled as such in test-report.md).

VALIDATION RESULTS: the code matches the accepted defaults except the pre-existing 50-metric item (P9). The precondition is correct and does not bind on the Session 2 ACM path. I confirmed the metric counts 109/114/116/120/122 by my own count. Only synthetic identifiers.

ASSUMPTIONS: the AWS requirements the owner cites from documentation (the target group must be attached for the ResourceLabel; the 4XX dimension sets) are taken as stated and not re-read live. Authorship comes from the records.

RISKS: run 2 could still fail in script-tests (F6). The F3 test gaps remain. The dashboard body changes on deployed-runtime plans (F2).

MANUAL ACTION REQUIRED: coordinator: confirm run 2 shows a passing `RESULT` before committing, and record it. Human: refresh the pins at the commit (expected, not a P41 defect).

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: run 2 `RESULT` line pending at `/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p41/r1/check-skip-sbt-p41-r1.log`.

NEXT GATE: run 2 passes, then the coordinator records it and this verdict in `review.md`, then commits under the standing consent. F1 is a coordinator records fix; F2 and F3 can ride with the elasticity bundle.
````

Coordinator: F1 fixed in `owner-report.md` before the commit. F2 and F3 are routed to the elasticity bundle (`repairs.md`). The commit waits for run 2's RESULT line, as the reviewer requires.

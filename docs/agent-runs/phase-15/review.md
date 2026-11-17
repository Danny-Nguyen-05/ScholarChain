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
| No hardcoded account IDs, ARNs or endpoints | met | The production code adds none. Every 12-digit match in the two test files is `[synthetic AWS-docs example account ID; redacted by the coordinator because the repository's account-ID scan rejects 12-digit literals]` or a `…[12-digit mock UUID tail, redacted by the coordinator]` (mock values) |
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


## Work order 4 — pipeline bundle (P5-P8, P17-P19 preparation, P25, P26, D1-D3) with the shared elasticity Terraform edits (P9, F2, F3)

### Review 1 — code-reviewer agent `a8da8cb63244f0cbe` (Opus 5.5, high), launched by the coordinator after the clean-snapshot gate (run 20261116T193009Z-41305); verbatim

STATUS: COMPLETE. **Verdict: APPROVE.** There are no blockers. Findings 1 to 3 are should-fix and must be routed before the Session 2 go/no-go (Wed 2026-11-18 18:00 CST). They are documentation gaps or human decisions, not code defects that could spend money.

OWNER: code-reviewer (read-only)

WORK ORDER: independent review of the Phase 15 pipeline bundle and the elasticity Terraform edits. Branch phase-15, HEAD 7a02de2, frozen diff `target/phase15/pipeline/r1/tracked.diff` and `untracked.txt`.

FILES CREATED: none
FILES MODIFIED: none

COMMANDS RUN: Read, Grep and Glob only. I made no shell, AWS, Anthropic or Voyage calls. I read no tfvars, state, `.env` or secrets.

TEST RESULTS: not run by me. I read `target/phase15/pipeline/r1/check.log`:
- `RESULT: PARTIAL passed=6 skipped: sbt` (line 122).
- tests/scripts: "479 executed, 3 skipped" (line 107). See finding 5.

VALIDATION RESULTS: checked against the user decisions in prompt.md.

What holds:
- **Step timeouts:** 225 + 900 + 900 + 225 + 1800 + 450 = 4500 s, exactly the 75-min cap.
- **Per-run estimate:** (0.315 + 0.240) × 5400/3600 = 0.8325, rounded up to 0.84. budget.py, check_manifests.py, the S manifest and emr-pricing.conf (r5 0.252/0.063) all agree.
- **Ledger:** 1.68 + 0.84 + 0.84 = 3.36 against the cap of 3.36. The cap is inclusive and `release.conf` pins 4 runs / 3.36.
- **Other release values:** ER_XMX 12g, maxLocalSampleRecords 60000 (the prep config agrees), PRESPEND floor 2, primary r5.xlarge in Terraform (validated to m5 or r5) and in pipeline check-cluster (MASTER only).
- **Runbook figures:** 19.54 / 22.98, gate 3.57 ≤ 23.00, Gate 1 2.85, credit ≥ 6.73, 0.58/h, the 5.8 h stop, no ×1.11 column, maxAuthorTeamSize 16.
- **sc-step.sh:**
  - `hadoop_run_id()` builds a correct UUID v4 (version nibble 4, variant 8–b).
  - The D2 plain path resolves to `file:///` through `HadoopIO.runPath` (HadoopIO.scala:39-45).
  - The copy-out bash globs and the awscli filters behave the same, and the copy-out manifest is checked before anything is written.
- **Concurrency:**
  - Every ledger call and counter is under one lock, rejections are re-sorted into manifest order, and duplicates are settled after all first occurrences.
  - The batcher serializes `embed` under its own lock.
  - IngestThroughputSpec and Phase15IngestBatchingSpec are real tests, not tautologies.
- **Security:** the only 12-digit literals are the synthetic `111122223333` and `000000000000`. No e-mail addresses or keys found.
- **Records:** prompt.md and repairs.md are append-only. The redaction at review.md:284 is disclosed as E3 and changes no human decision.

## Findings (most severe first)

**1. should-fix (high): recording the S actual can block the approved S retry.**
- Paths:
  - `scripts/lib/budget.py:266-280` (`ledger_totals`, the tail per cluster) and `:303`.
  - `docs/runbooks/session-2-plan.md:424-428` (step 5a comes before step 6).
- How `--record-actual` counts:
  - It measures from the cluster's `CreationDateTime`, so boot time and the operator's time writing the approval record count too.
  - It then adds a pending 900 s tail of 0.14.
  - The retry still reserves its full 0.84.
- Arithmetic: the retry is admitted only if the measured cost is at most 3.36 − 1.68 − 0.84 − 0.14 = 0.70. At 0.555/h that is about **75.6 min from cluster creation**.
- Consequence: if S fails late, for example at the Spark timeout around minute 60-75, the retry is refused (fail-closed). This is the most likely failure, since that path has never run on EMR.
- The arithmetic is right: the tail covers the up-to-15-min gap before the retry. But the two human rules ("record actuals right after each S run" and "S + one retry") conflict, and nothing discloses it.
- The project-level EMR block (3.33 h, including the 20-min cold start) is about 0.3 h looser than what the ledger leaves for Session 2 (1.68 / 0.555 = 3.03 h).
- Fix:
  - documentation-engineer: state this condition in 5.2 steps 5a and 6.
  - human: decide the order. Either reserve the retry before recording S's actual, or raise the ledger cap by about 0.15-0.20 inside the 1.93 block.
  - test-engineer: add a hand-derived test for "S times out, actual recorded, retry on the same cluster".

**2. should-fix: the P18 precondition is missing from the stage-a procedure.**
- Path: `docs/runbooks/session-2-plan.md` 5.2 step 1 (lines 416-419). "state list" appears nowhere in the runbooks.
- The user's P18 rule says stage a is planned only after `terraform state list` shows exactly the two guards; anything else means stop. owner-report.md:2032 states this precondition, but the runbook does not.
- Owner: documentation-engineer. Fix: add the command (addresses only), the expected two addresses and the stop rule.

**3. should-fix: experiments/README.md:35 contradicts budget.py.**
- The README says budget.py "reserves its own unrounded estimate (0.833 per S run, cumulative 3.35)".
- budget.py actually rounds up to the cent, so the ledger reserves 0.84 per run and reaches 3.36/3.36 with zero margin, as session-2-plan.md:256 correctly says.
- Owner: experiment-engineer. Fix: correct the sentence.

**4. note: stale text** (each fix is "update the wording"):
- `scripts/config/release.conf:236-237` still says "exactly 2 more 90-minute runs (S and L) fit … no L retry". Owner: infra-engineer.
- `release.conf:60-61` still says 22.97 / 2.03; the current figures are 22.98 / 2.02. Owner: infra-engineer.
- `scripts/README.md:315` still describes 90-min m5 runs. Owner: infra-engineer.
- `session-2-plan.md:442` still says "two full 90-minute S runs". Owner: documentation-engineer.
- The G6 comments say 0.795 × 3.25 = "2.58", but the estimate rounds up to 2.59. Locations: `infra/terraform/modules/emr/variables.tf:60`, `tests/phase15_emr_primary.tftest.hcl:270`, `infra/terraform/README.md:572`. In the same README, "3.36" should read 3.37. Owner: infra-engineer.

**5. note: the D1/D2 test was not exercised by the clean gate.**
- `tests/scripts/test_hadoop_prep_args_15.py` skips itself when the built JARs or the P6 classpath are missing. The clean snapshot has neither, so its 3 tests were most likely the 3 skipped ones. Their pass rests on owner-report.md:3509 (agent-reported).
- Owner: coordinator. Fix: name the skipped tests in test-report.md:147, or re-run the test on the built tree and record the observed result.

**6. note: the 8 GiB copy-out ceiling is sized for L.**
- `release.conf` (PIPELINE_MAX_COPYOUT_BYTES) sets 8 GiB on an L-based justification. EMR now runs S only, and the S copy-out is about 1.1 GB.
- Owner: infra-engineer, with the human. Fix: consider 2 GiB, or record why 8 GiB is kept.

**7. note: dashboard panels removed under P9.**
- `infra/terraform/tests/phase12c.tftest.hcl:118-130`: the run named `dynamodb_native_failure_and_latency_panels` now asserts that those panels are removed.
- Dropping the Phase 12C N12 panels was an agent's choice under P9.
- Owner: infra-engineer. Fix: rename the run, and get the human's acknowledgement (repairs E4).

**8. note: r5 rates added under an earlier pricing confirmation.**
- `scripts/config/emr-pricing.conf`: the new r5 rates sit under the existing `EMR_PRICING_CONFIRMED_BY_HUMAN=true`. The user's go-ahead covers updating the file.
- Owner: human. Fix: have the human restate both rates in the Session 2 approval record.

**9. note: the untracked-file count does not match.**
- test-report.md:147 says the untracked tar holds 101 files, but `untracked.txt` lists 41. I could not list the tar.

ASSUMPTIONS: The Session 1 ledger holds two reserves of 0.84 each. Who wrote which file is taken from the owner reports; git cannot show authorship before a commit. All files sit in their owners' territories.

RISKS: The EMR-only behaviour has not run live: YARN with file:// outputs, copy-out throughput from EFS within 450 s, and Spark finishing in 30 min. The final sbt check was still running and is unverified by me.

MANUAL ACTION REQUIRED: Human decision on finding 1 (record-then-retry order, or a ledger margin). Human acknowledgement of findings 7 and 8.

BLOCKED-ON OWNER: none for approval. Repairs:
- documentation-engineer: findings 1 and 2, plus the session-2-plan.md:442 wording.
- experiment-engineer: finding 3.
- infra-engineer: findings 4, 6 and 7.
- test-engineer: the scenario test in finding 1.
- coordinator: finding 5.

BLOCKED-ON EVIDENCE: the final sbt check result, and an observed (not skipped) run of test_hadoop_prep_args_15.

NEXT GATE: the final sbt check must pass. Then commit under the standing consent, and route the should-fix items before the go/no-go.


### Review 2 — pipeline repair round 1 and elasticity P42

Code-reviewer agent `a6f59b4c4d52b0826` (Opus 5.5, high), launched by the coordinator on the owners' targeted gate results (user rule 2026-11-16: the full check runs once after APPROVE); verbatim

STATUS: COMPLETE. **Verdict: APPROVE.** I found no blockers. Findings 1-4 of review 1 are resolved, and the 3.53 / 0.87 / 0.14 / 1.85 figures agree across code, tests and runbook. P42 meets the user's requirements. Two should-fix items must be routed before the Session 2 go/no-go. Neither can raise spend: the first is a disclosure gap on the money side, the second a missing runtime guard.

OWNER: code-reviewer (read-only)

WORK ORDER: independent review of the uncommitted Phase 15 tree (pipeline repair round 1 and P42) on branch phase-15, HEAD f801d28.

FILES CREATED: none
FILES MODIFIED: none

COMMANDS RUN: Read, Grep and Glob only. I had no shell tool, so I could not run `git diff HEAD`. I reviewed the current contents of every listed file and checked them against owner-report.md (4205-4370). I made no network calls and read no tfvars, state, `.env` or secrets.

TEST RESULTS: not run by me. The owner gate results in the work order are agent-reported, and I did not observe them.

VALIDATION RESULTS
- **Finding 1 resolved.**
  - Cap: release.conf:239-245 sets 3.53.
  - Runbook: session-2-plan.md:443-444 (5a/6) and the P19 draft at :325-329 state the ≤0.87 rule, about 94 min.
  - Tests: TimeoutThenRetryOnTheSameCluster (tests/scripts/test_record_actual_15.py:141-223) drives the real `--execute` / `--record-actual` paths. 5643 s gives 0.87, admitted at 3.53 inclusive, and a fifth run is refused by the count. 5700 s gives 0.88, refused at 3.54.
  - Arithmetic: 3.53 − 1.68 − 0.84 − 0.14 = 0.87, and 0.87 × 3600 / 0.555 = 5643 s ≈ 94.05 min. Correct.
- **Finding 2 resolved:** session-2-plan.md:426-430. The two addresses match main.tf:4 and phase14b-providers.tf:83. State is local (no backend block), so `state list` needs no credentials.
- **Finding 3 resolved:** experiments/README.md:38 (but see note 3).
- **Finding 4 resolved:**
  - release.conf:60-61 now says 22.98 / 2.02, and :236-237 is updated.
  - scripts/README.md:315.
  - session-2-plan.md:458.
  - 2.59 / 3.37 at variables.tf:60, phase15_emr_primary.tftest.hcl:270/274 and infra README:572.
- **Findings 6-8 also resolved:**
  - 6: release.conf:322-323 records why 8 GiB is kept.
  - 7: run renamed at phase12c.tftest.hcl:121. The old name survives only in historical evidence.
  - 8: r5 rates restated at session-2-plan.md:322-324.
- **The 3.53 cap appears consistently in:**
  - run-bounded-pipeline.sh:111;
  - scripts/README.md:315, 399, 401, 403, 409 and 489;
  - test_providers:178, test_pipeline:1097, test_phase15_pipeline_pins:314, test_d3:87/202;
  - test_cap_pins:39-61, test_prespend_floors:282 and test_experiments:255.
- **Every remaining 3.36 is either a sum of reserves (1.68 + 0.84 + 0.84) or labelled history:**
  - release.conf:235;
  - test_d3:204-210 and test_cap_pins:215;
  - test_experiments:381/450/470 and test_pipeline_refusals:268/306;
  - session-2-plan.md:256/319/1070.
  - None of these is the cap. The project figures 19.54 / 22.98, the 3.33 h = 1.93 block and spend + 3.57 ≤ 23.00 are unchanged.
- **P42 checks:**
  - The caps are constants (loadgen.py:89-92). They are enforced by `validate-manifest`, `plan` and `run` (:231-272, :376-394, :914), and check_manifests.py:433-530 requires the exact five values.
  - Warm-up: one worker, one pass, no retry (:805-843).
  - Questions file: pinned by sha256 and count, 100-200 lines, distinct (:930-942); 150 committed, provenance verified.
  - 429 handling: 429 is classified as `throttled` (:515), counted toward the phase cap (:539-548), never counted toward abort, and excluded from latency, throughput, success and error rates (:1087-1112, :1163).
  - API key: read from env only (:148-156), sent only in the header (:647-652), and the record stores only the variable's name.
  - Body and auth match the P40 contract: PublicSemanticRoute.scala:169/176 (keys question/topK, topK ≤ 20) and Bearer auth at ApiContracts.scala:140.
  - The manifest has a 1800 s quiet window.
  - Without a semantic block the semantic route is skipped (:963), so the graph 15B runs are unchanged.
- **The 71 pre-existing tests keep their meaning:** no pre-existing load-tests test uses a 429 status. The change in behaviour is disclosed in load-tests/README.md:122-123.
- **Security:** no 12-digit numbers, e-mail addresses or keys in the changed files. prompt.md and review.md are unmodified.

## Findings

**1. should-fix: the 3.33 h block's own worst case is refused by 1 cent.**
- Paths:
  - session-2-plan.md:325-329, 443-444 and 256;
  - tests/scripts/test_cap_pins_14b.py:7-8;
  - proven by scripts/tests/test_d3_emr_primary.py:297-301.
- What happens:
  - 3.53 is the exact 200-minute block, but every ledger term is rounded up.
  - The plan's 20-min cold start plus a full 75-min S makes 95 min, which records 0.87875, rounded up to 0.88.
  - 1.68 + 0.88 + 0.14 + 0.84 = 3.54, so the retry is refused.
  - In practice: if S runs its full 75 min, the time from cluster creation to S submission plus the delay before recording must be ≤ about 19 min. Measured cold start is 4-5 min (:408), so this usually fits.
- Fix:
  - documentation-engineer: state the 19-minute budget in 5a/6 and the P19 draft. Add operator steps: write record 1 as soon as the cluster ID exists, and run `--record-actual` immediately after an S failure.
  - Human: accept this, or record a few-cent rounding allowance. More than about 0.02 would push the 0.58/h block past 1.93.

**2. should-fix: `--observe-seconds` can shorten the R-b quiet window below 25 minutes.**
- Paths: load-tests/loadgen.py:342-343 and :1182.
- The help text says "never for R-b", but nothing enforces it for a non-loopback target. check_manifests checks only the committed manifest (owner-report.md:4342 discloses this).
- Owner: experiment-engineer.
- Fix: in `finish_setup`, refuse `--observe-seconds` when `target_loopback` is false (or when the result is below 1500 s), and add a test.

**3. note: experiments/README.md:38 is now inaccurate.**
- It says a longer cap "is refused by the ledger". With 0.17 of room, runs of up to 0.92 each fit (test_d3:212-216). Only check_manifests' 75-min pin refuses a longer S.
- Same file: :137 says "84 tests" but :28 says 100, and :144 still says "3-run ledger".
- Owner: experiment-engineer.

**4. note: L wording left over after L was dropped.**
- Paths:
  - test_cap_pins_14b.py:68 and :209 ("S then L", "S 0.84 + L 0.84");
  - test_pipeline_refusals.py:268-270 and :815-816;
  - session-2-plan.md:256 ("If L's manifest needs a longer runtime").
- In the P19 draft, :332-334 ("if S succeeds the next run is L") contradicts :307-308. It quotes the human verbatim, so annotate it as superseded; do not rewrite it.
- Owners: test-engineer and documentation-engineer.

**5. note: session-2-plan.md:441 is stale.**
- It still calls the D3 change "not yet reviewed or committed"; it was committed in f801d28.
- Owner: documentation-engineer.

**6. note: /readyz in the semantic mix rests on an unverified pricing claim.**
- Paths: experiments/README.md:226 and the profile note.
- /readyz is weight 1 of 44, about 4,500 calls. The claim that GetVectors probes "carry no per-request charge" was not checked against S3 Vectors pricing (no network here).
- The cost is bounded and small either way.
- Fix: the human either verifies the pricing or accepts the default as it stands (experiment-engineer).

**7. note: the byte-for-byte question reproduction test skips in a clean snapshot.**
- Path: experiments/tests/test_semantic_manifest.py:259. It needs the git-ignored slice, so the clean snapshot will skip it, as in old finding 5.
- Coordinator: record whether it actually ran in the working tree (not skipped).

**8. note: the defaults the agent chose are acceptable.**
- topK 10 is within the public limit of 20, and S3 Vectors query cost does not depend on topK.
- Weight 40 gives 90.9% semantic traffic. The cost bound treats every request as semantic, so it is conservative.

ASSUMPTIONS: The file contents I read are the uncommitted working tree; I could not see the diff itself. Authorship comes from owner-report.md. All files are within their owners' territories.

RISKS: Neither P42 nor `--record-actual` has run against AWS. The rate limit for the P35 rehearsal must be raised locally (owner-report.md:4354).

MANUAL ACTION REQUIRED: human decision on finding 1 (accept the 19-minute budget or add a rounding allowance) and on finding 6.

BLOCKED-ON OWNER: none for approval. Repairs: documentation-engineer (1, 4, 5); experiment-engineer (2, 3, 6); test-engineer (4); coordinator (7).

BLOCKED-ON EVIDENCE: the full clean-snapshot check.sh and sbt check results; an observed non-skipped run of test_semantic_manifest.py:260.

NEXT GATE: full check.sh and sbt check, then commit after the human's explicit yes. Route the should-fix items before the go/no-go.


### Review 3 — review-2 fixes and the P35 record

Code-reviewer agent `ab3c5630f6883fccc` (Opus 5.5, high), launched by the coordinator on the owners' targeted gate results after the review-2 repairs (user rule 2026-11-16: the full check runs once after APPROVE); verbatim

STATUS: COMPLETE. **Verdict: APPROVE (review 3).** Findings 1-7 from review 2 are resolved, and every P35 figure I checked matches the evidence. Nothing here blocks. The notes below are about disclosure only; none of them changes money, caps or code behaviour.

OWNER: code-reviewer (read-only)

WORK ORDER: Phase 15 review 3. Scope: the fixes made after review 2, plus the P35 record. Branch phase-15, HEAD f801d28, uncommitted working tree.

FILES CREATED: none
FILES MODIFIED: none

COMMANDS RUN: Read, Grep and Glob only. I had no shell, so I ran no `git diff` and no tests. No network. I read no tfvars, state, ~/.aws, .env or secrets.

TEST RESULTS: I did not run any. The owner results (95 / 100 / 79 OK, links 0 broken) are reported by the agents, not seen by me. For finding 7 I read target/phase15/pipeline/r1/semantic-manifest-tests.log. It shows "Ran 16 tests … OK", and the byte-for-byte test (test_semantic_manifest.py:259-268) shows "... ok", not skipped.

VALIDATION RESULTS
- **F1 resolved.** The text is at session-2-plan.md:354-362 (P19 draft), :475 (step 5, operator step a), :481 (5a, operator step b), :482 (step 6) and :257 (P25). The cap stays 3.53.
  - 95 min × 0.555/h = 0.87875, rounded up to 0.88: 1.68 + 0.88 + 0.14 + 0.84 = 3.54, refused.
  - 94 min = 0.8695, rounded up to 0.87: total 3.53, admitted.
  - The budget is 19 min, and :481 says the 94-min total is what counts.
  - prompt.md:281-287 records the decision.
- **F2 resolved.** The refusal is at loadgen.py:951-952, inside `finish_setup`. That is before `read_key` (:975), before `os.makedirs` (:986) and before any socket call. Help text is at :1184.
  - Tests at test_loadgen_semantic.py:514-560 cover: three remote URL forms with no connection and no DNS lookup; no run directory created; the key not in stderr; refusal even at 99999; loopback (127.0.0.1 and localhost) still allowed; and the committed 1800 s quiet window.
- **F3 and F6 resolved.**
  - experiments/README.md:38: the ledger no longer refuses a longer cap; check_manifests' 75-min pin does. 0.92 = 1.85 / 2 is correct.
  - :137 and :28 both say 100 tests (48 + 23 + 16 + 13).
  - :144 now says "4-run ledger".
  - :226 and plan :841 mark the GetVectors pricing as unverified.
- **F4 resolved.** Changes at test_cap_pins_14b.py:68 and :208-210, and test_pipeline_refusals.py:264-271 and :815-818, touch only wording and test names; the asserted values are unchanged. Plan :257 and the superseded note at :368-371 keep the human's text.
- **F5 resolved** (:478, "committed in `f801d28`").
- **P35 figures.** All match per-level-results.json, summary.json and metrics-after.txt.
  - Rates and CPU: 33.319 / 88.08 / 222.469 / 450.572 / 806.235 / 1,015.538 requests per second (× 60 = 1,999 / 5,285 / 13,348 / 27,034 / 48,374 / 60,932 per minute); 1-second peaks 52 / 131 / 293 / 668 / 1,262 / 1,737; CPU 99.4 / 100 / 98.8 / 98.4 / 96.5 / 95.1 %.
  - Cache: 150 misses + 180,594 hits = 180,744. That equals the sum of semantic-route requests and the `/v1/semantic/retrieve` 200 count.
  - `api_rate_limited_total` was 0 before and after. Server total 198,753 = 198,750 load requests + 3 setup calls.
  - `/readyz` calls: 4,500 observed, against the plan's 4,513 estimate.
  - Local rule: 27,034 / 2 = 13,517, so the rule allows 5,285 < T ≤ 13,517.
  - Rate limit: r_S2 = ceil(2 × 1,737 = 3,474) = 3,500, within 1-100,000. b_S2 = 7,000, within 1-1,000,000, and equal to 2 × r_S2. Terraform validation matches (phase12b-variables.tf:460, :470).
  - The sha256 values agree across COPIED.sha256, not-copied.sha256, raw.sha256 and SHA256SUMS.txt (spot-checked).
- **No key values in the evidence.** p35-run.sh.txt:8-12 generates the keys at run time, exports only their SHA-256 and passes `-e NAME` without values. run-record.json stores only a hash of the base URL. There are no 12-digit numbers or e-mail addresses in the changed files I scanned.
- **The query-api cap is 2.** The default is at phase12b-variables.tf:197, and the validation at :207 limits HTTP services to `max <= 2`. Plan :565 also sets max 2.

FINDINGS
1. **note, about how honestly the T = 3,000 ratios are stated** (documentation-engineer; session-2-plan.md:304 and :1059).
   - "Level 25 about 2.5 × T, level 50 about 5 × T" is honest as a single-task offered-rate estimate before any scale-out, which is the rule's own measure. :304 also mentions the cap of 2.
   - Two things are not said:
     - **After scale-out to the cap of 2**, level 50 still gives about 7,500 per target (2.5 × T). The policy would want about 5 tasks, so it stays pinned at the maximum through the hold, and scale-in can only follow the end of the load.
     - **Level 25 cannot trigger scale-out.** At 200 ms it reaches its 15,000 cap in about 120 s (:867), which is shorter than the plan's own estimate of about 6.5 min to scale out (:957, three one-minute datapoints). Scale-out is therefore expected during level 50 and the hold.
   - The "robust for about 50-400 ms" in prompt.md:291 holds only in a weak sense. At 400 ms, level 25 is 1.25 × T, not 2 × T. At 100 ms or less, level 5 reaches T. Do not edit prompt.md (it is append-only). The runbook does not repeat the claim, but should add one sentence on this sensitivity.
   - Fix: add those two points at :304 and :1059.
2. **note** (documentation-engineer; :841). "The 0.53 figure does not include it" overstates the gap. The 198,600 bound already counts the roughly 4,500 `/readyz` requests, each priced as a QueryVectors call. The only uncovered part is the amount by which a `/readyz` probe, which may call GetVectors on more than one index (AwsComposition.scala 267-268 and 316), costs more than one query.
3. **note** (experiment-engineer / documentation-engineer; :301). The per-phase CPU figures are interpolated from cgroup samples taken every 2 s (analyze.py:14-20), using the container clock. The warm-up (4.5 s) and baseline (6.8 s) phases span only 2-4 samples. Add "interpolated, approximate" to the wording.
4. **note** (documentation-engineer; :368-371). The agent-written "[Superseded …]" bracket sits inside the ```text block the human copies into the approval record, and it says "item 3 above" from inside item 3. Move it outside the block, or tell the human to delete it when copying.
5. **nit** (coordinator; evidence/p35/rehearsal/SHA256SUMS.txt:3). `container-id.txt` is hashed but appears in neither COPIED.sha256 nor not-copied.sha256.

ASSUMPTIONS: The files I read are the working tree. Without git I could not confirm that prompt.md only had text appended: the new sections at :281-296 sit at the end, and the earlier text I checked is unchanged, but this is **unverified**. All files are within their owners' territories.

RISKS: No live run yet backs T = 3,000 or the 200 ms estimate. If S is slow to start, the retry's rounding budget depends on the operator acting promptly.

MANUAL ACTION REQUIRED: none for approval. The human sets 3000 / 3500 / 7000 in the private tfvars.

BLOCKED-ON OWNER: none. Optional repairs: documentation-engineer (1-4), coordinator (5).

BLOCKED-ON EVIDENCE: the full clean-snapshot check.sh and `sbt check` (JDK 17) results, and a git diff showing that prompt.md only had text appended.

NEXT GATE: the full check.sh and `sbt check`, then the commit after the human's explicit yes.

Coordinator check of review 3's blocked-on evidence: `git diff HEAD --numstat` shows `docs/agent-runs/phase-15/prompt.md` 16 added, 0 deleted and `review.md` 123 added, 0 deleted at the time of this review, so both are append-only. Nit 5 fixed: `evidence/p35/rehearsal/container-id.txt` copied and `COPIED.sha256` regenerated. Notes 1-4 routed to the documentation-engineer (wording only, no figure changed); the coordinator checks them against this review before the full check.


## P0 modify incident repair (modify-20261116-01): billing wrapper fix, incident-linkage verification, kit, incident record

### Review 1 — code-reviewer agent `a0a155023aecd65d2` (Opus 5.5, high), launched by the coordinator; verbatim

STATUS: DONE. Verdict: **APPROVE**. Nothing blocks. Fix the should-fix items as listed below; the most important is to run an extended I1 before the freeze commit (finding 1).

OWNER: code-reviewer (read-only)

WORK ORDER: Independent review of the modify-20261116-01 repair: the `scripts/billing/**` working-tree diff, the offline kit `target/phase15/p0/{p0_gate.py, tests/test_p0_kit.py, p0-steps.md}` and `docs/incidents/2026-11-16-p0-budget-modify-backup-check.md`.

FILES CREATED: none
FILES MODIFIED: none

COMMANDS RUN: none. This session had only Read/Grep/Glob, no shell. I could not run `git diff HEAD`, so I reviewed the current files in full plus the owner reports. I could not read the HEAD version of `modify()` either (see 4b).

TEST RESULTS: Not re-run (no shell). I did not observe the owner-reported counts (execution 120 OK, verification 84 OK, publication 39 OK, kit 26 OK). I read the new tests instead.

VALIDATION RESULTS (observed by reading):

**The modify() fix is correct.**
- `budget_execution.py:1114-1133` keeps three checks:
  - the sorted post-apply state-file set is `[state]` or `[state, .backup]`;
  - `file_meta` (regular file, 0600, uid) on `.backup`, with a new `is_symlink()` catch;
  - `post != INITIAL` (`STATE_UNCHANGED_AFTER_APPLY`).
- The pre-apply copy must still equal INITIAL (`:1110-1113`), and the post-apply live read is unchanged (`:1146-1149`).
- Dropping the `.backup` byte-equality removes no protection that matters:
  - The state is re-verified as INITIAL under the lease right before apply (`:1108`).
  - A saved-plan apply rejects a stale prior state.
  - The live post-verify checks the outcome.
- I found no path where a bad apply passes silently.

**Cause recording is safe.**
- `failure_cause` (`:88-99`) returns only a fixed code or the exception type name.
- The public codes are unchanged (`:952`, `:1140`).
- The verifier's cause regex (`budget_verification.py:547`) accepts every value `failure_cause` can produce.

**The real incident evidence should be accepted.**
- I computed the canonical `save_json` byte counts by hand:
  - preservation receipt with exactly two artifacts (`billing.execution.tfstate`, `billing.execution.tfstate.backup`) and no `cause` key: **490 B**;
  - pre-apply receipt with the 8 keys the verifier requires (binding + sha256/bytes/equal/fsync_completed): **469 B**.
- Both match the operator's sizes exactly, so the schema, source names and lack of `cause` match `:543-554` and `:562-568`.
- Op folder:
  - The `PrivateRunner` labels (`modify-pre-*`, `modify-show`, `modify-apply`) contain no `modify-post-*` (`:534`).
  - The files are 0600 via `create_file`.
  - `modify.started` is empty.
  - The lease lock is removed in `finally`, so the `WRAPPER_ACTIVE` check passes.
- Terraform writes warnings to stdout, so the empty stderr is consistent. The `Apply complete!` line is emitted once with `-no-color`.
- The pins bind correctly:
  - recovery-000 = 92a7…/40834 = current state;
  - recovery-001 = the current `.backup`;
  - the pre-apply receipt is bound to the modify gate hash and the unchanged `modify.plan_sha256` pin.
- `reviewed-pins.json` is untouched (not in git status), and `source_freeze` has no `scripts/billing`, `docs/incidents` or `docs/runbooks` rows.

**A linkage refusal does not use up the human's attempt.**
- `verify()` runs `linkage()` before `self.op.mkdir` and before any AWS call (`budget_verification.py:282-284`). Tests assert this: `refuses()` checks no calls and no op dir (`test_budget_verification.py:922-929`).
- Mixed or unknown gates are refused (`:417-419`; tests `:981-996`). The normal path is unchanged apart from the selector (`:456`).
- The tests cover the real failure: a same-size, reversed-bytes `.backup` (`test_budget_execution.py:47`, `:1626-1641`), plus thorough refusal tests.

**Kit.**
- The incident builder matches `INCIDENT_GATE_FIELDS` and is validated by the wrapper's own `load_gate`. It reads nothing private.
- Argument mixes are refused before git and before any prompt.
- The `/dev/tty` fix is correct:
  - `buffering=0` FileIO `readline` reads one byte at a time, so later pasted lines stay queued.
  - The separate `"w"` writer avoids the seek error.
  - `rstrip("\r\n")` is right.
  - echo is restored in `finally`.
- Neither the incident record nor p0-steps.md contains a 12-digit ID or an e-mail address.

FINDINGS

1. **should-fix**: `target/phase15/p0/p0-steps.md:202-213`. Step I1 does not check everything the verifier checks before AWS. A real-evidence mismatch would only show up inside the window, and if the evidence itself differs, only a code change can fix it.
   - `ls "$RECV"` hides dotfiles, but `folder.iterdir()` (`budget_verification.py:559`) counts them. A Finder `.DS_Store` would cause a permanent `INCIDENT_BACKUP_FILE_SET`.
   - Missing: current `.backup` hash and size == `recovery-001.opaque` (`:574-579`).
   - Missing: pre-apply file == 271fe888…3f67 / 40818 (`:571`).
   - Missing: the `modify-post-*` check (`:534`).
   - Missing: `modify.started` size 0 (`:530`).
   - Missing: the lock and extra state-file scan (`:581-586`).
   - Suggested additions: `ls -A "$RECV"; ls -A "$OPDIR"`; `shasum -a 256 "$RECV/recovery-001.opaque" "$PRIMARY/billing.execution.tfstate.backup" "$RECV/pre-apply.billing.execution.tfstate"`; `stat -f%z "$OPDIR/modify.started"`; `find "$PRIMARY" \( -name '*.tfstate' -o -name '*.tfstate.*' -o -name '*.lock.info' -o -name terraform.tfstate.d \) | sed "s|$PRIMARY/||" | sort`. The last must print exactly `billing.execution.tfstate` and `billing.execution.tfstate.backup`.
   - **Have the human run this extended I1 (offline) before the frozen commit**, so any surprise can still be fixed in code without voiding the freeze. Kit edits under ignored `target/` do not affect the freeze.
   - Owner: kit writer (see finding 9).

2. **should-fix**: `p0-steps.md:196,200`. `VWIN=2026-11-17THH:MM` with "Replace `HH:MM`" implies only the time changes. If the verify runs tonight (11-16), the date must change too. Otherwise the kit refuses with `SESSION_WINDOW_NOW_OUTSIDE…`, but only after all the prompts. The text should say "replace the date and time". Owner: kit writer.

3. **should-fix**: `p0_gate.py:554-566` vs `:448-457`, `:579-592`. `check_linkage_args` only checks that the incident arguments are present.
   - These format checks run only after all hidden and visible prompts:
     - hex64 format;
     - bytes > 0;
     - not the INITIAL hash;
     - the `modify-…` and `verify-usd25-…` regexes;
     - the gate filename.
   - The kit test `test_p0_kit.py:532-552` passes answers, which confirms the order.
   - Nothing gets written, but a typo costs a full re-entry inside the window.
   - Fix: move these pure checks into `check_linkage_args`. Owner: kit writer.

4. **should-fix** (tracked file, so before the freeze commit): `docs/incidents/2026-11-16-p0-budget-modify-backup-check.md:45-61,117`.
   - **(a)** The line citations (`:48-49`, `:132-138`, `:207-229`, `:283-285`, `:888-908`, `:1093-1117`) describe the code that ran (2611cc6) but don't say so. After the fix they point elsewhere: `preserve` is now `:902-925`, the modify try block `:1115-1140`, `opaque_copy` `:221-247`, `file_meta` `:146-152`, `modify_apply_argv` `:297-299`. Label them "at commit 2611cc6".
   - **(b)** Line 61's caveat about `:1108` is moot: if `:1107` is reached, it fails deterministically. The real open alternative is a failure before `:1107`. I could not read HEAD to check whether the old file-set check (`:1100-1103`) was order-sensitive (unsorted `rglob`). If it was, `UNEXPECTED_POST_APPLY_STATE` is an equally consistent inferred cause. The current code sorts (`:1118-1121`), so the fix covers both cases. The record should state which it was.
   - Owner: incident-responder.

5. **nit**: `scripts/billing/README.md`.
   - `:117` "The state was not changed afterwards" is asserted before verification. Rephrase as "must be unchanged; the incident linkage checks it".
   - `:100` "no plan, gate, login or apply exists yet" now contradicts `:117`.
   - `:107` cites `271fe888...3be1f`, but the hash ends `…3f67`. This is probably pre-existing.
   - Owner: infra-engineer.

6. **nit**: `budget_execution.py:949,1137`. `failure_cause(error)` is evaluated inside the preservation `try`, so if it ever raised, `preserve()` would be skipped. It cannot raise in practice. Harden it only if the file changes anyway. Owner: infra-engineer.

7. **nit**: `p0-steps.md`.
   - `:235` uses the relative path `operations/$VOP/verify.receipt.json`; it should be `"$PRIMARY/operations/$VOP/verify.receipt.json"`.
   - `:9` lists the steps that contact AWS but omits I2 and I3.
   - I2 `:221` prints the STS JSON, including the account ID, to the local terminal. This is the same as step 10 and is needed for the paste, but I2 should say not to send that output.
   - Owner: kit writer.

8. **nit**: `p0_gate.py:227-251`. Echo is turned back on between STS continuation lines. A terminal that delivers a paste in chunks could echo a later chunk to the screen (screen only, nothing persisted). Optionally keep echo off for the whole STS read. Owner: kit writer.

9. **process**: The writer of `target/phase15/p0/**` is ambiguous. That path is ignored and not in the ownership map. `prompt.md:305` and the incident record (`:93`) name the coordinator, but the infra-engineer's report edited the kit. Record the assignment. Separately, the stale line refs in `docs/runbooks/phase-14-live-session.md` belong to the documentation-engineer (the infra-engineer already reported this as BLOCKED-ON).

ASSUMPTIONS:
- The operator-reported file sets, sizes and hashes are accurate.
- No `terraform` command touched the state after the incident.
- The new window is opened after the fix is committed and the checkout is clean.

RISKS:
- Real-evidence acceptance rests on my code reading plus the byte-count match; no test runs against the real files.
- Hidden files in the backup folder (finding 1) and HEAD's file-set ordering (finding 4b) are unverified.

MANUAL ACTION REQUIRED:
- The human runs the extended I1 offline before the freeze commit.
- The commit needs the user's explicit yes.

BLOCKED-ON OWNER: none for this review. Repairs route as listed: incident-responder (4), infra-engineer (5, 6), kit writer (1-3, 7, 8), documentation-engineer (runbook refs).

BLOCKED-ON EVIDENCE:
- Observed test results (no shell was available).
- The HEAD text of `budget_execution.py` around the old post-apply file-set check (4b).

NEXT GATE: Should-fix repairs (tracked docs before the freeze, kit anytime), then the extended I1 offline, then coordinator `sbt check` and the user-approved commit, then the human's new window for I2/I3.

Relevant paths:
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/budget_execution.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/budget_verification.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/tests/test_budget_execution.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/tests/test_budget_verification.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/README.md
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/VERIFICATION.md
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0_gate.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0-steps.md
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/tests/test_p0_kit.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/incidents/2026-11-16-p0-budget-modify-backup-check.md

Coordinator notes on review 1 (2026-11-16):
- Finding 4b resolved by the coordinator against HEAD 2611cc6: the old post-apply file-set check already sorted the `rglob` result (`found = sorted(...)`, compared with `sorted([state, tf_backup])`), and the preservation receipt lists only the state and its `.backup`, so `UNEXPECTED_POST_APPLY_STATE` is ruled out; `TERRAFORM_BACKUP_NOT_INITIAL` is the only consistent cause. Routed to the incident-responder with finding 4a.
- Finding 9: the coordinator assigns `target/phase15/p0/**` (ignored kit) to the infra-engineer from this point; findings 1-3, 7 and 8 go to it with findings 5 and 6.
- Finding 1 (extended I1 before the freeze): the user is offline overnight. The coordinator freezes tonight anyway; the extended I1 runs first thing on Tuesday. If it shows a difference that needs a code change, the freeze is redone on Tuesday (full check, commit, P6 S), still before Wednesday.


### Review 2 — code-reviewer agent `a0a155023aecd65d2` (Opus 5.5, high), repairs of review 1 plus the runbook edits; verbatim

STATUS: DONE. Review 2 verdict: **APPROVE**. Every review-1 repair checks out, nothing blocks, and none of the five new nits is a safety problem.

OWNER: code-reviewer (read-only)

WORK ORDER: Review 2 of the P0 modify-incident bundle. I re-checked only the repairs of review-1 findings 1-9, plus the documentation-engineer's first edits to `docs/runbooks/session-2-plan.md` and `docs/runbooks/phase-14-live-session.md`.

FILES CREATED: none
FILES MODIFIED: none

COMMANDS RUN: none. This session had only Read and Grep, no shell, so I re-ran nothing.

TEST RESULTS: The owner-reported counts (execution 121 OK, verification 84 OK, publication 39 OK, kit 32 OK) are not observed by me. I read the new tests instead: `test_budget_execution.py:1678-1684` and `test_p0_kit.py:533-566`, `:607-683` and `:685-781`.

VALIDATION RESULTS (from reading the code):

**I1 offline pre-check (`target/phase15/p0/p0-steps.md:205-238`).**
- It mirrors the verifier's local checks in `budget_verification.py:incident_linkage`:
  - **A:** backup-folder file set with `ls -A`, so dotfiles count.
  - **C:** recovery-000 = current state = 92a7…/40834; recovery-001 = current `.backup`; pre-apply copy = INITIAL/40818.
  - **D:** `modify.started` and stderr are 0 bytes; exactly one exact success line. Stripping CRs with `tr` gives the same answer as the verifier's `rstrip(b'\r')` here.
  - **F:** 0700 directories; 0600 regular files with one link and your uid. This mirrors `secure_dir`, `file_meta` and `regular`.
  - **G:** no symlink in any ancestor.
  - **H:** the `find` matches the verifier's `rglob('*')` scan:
    - the four name rules are equivalent;
    - both match dotfiles;
    - neither follows directory symlinks;
    - both include directories;
    - it covers `operations/`, `config/` and `tf-data/`.
  - **B** is stricter than the verifier: any name outside the PrivateRunner labels, or any dotfile, is flagged. The real labels (`modify-pre-budget/tags/notifications/subscribers-50/80/100`, `modify-show`, `modify-apply`) all match, so B can only raise a safe false alarm (stop and ask the coordinator), never a false pass.
- On the reported real evidence it should print `differences=0`.
- It prints only names, known hashes, sizes, counts and `stat` fields. A DIFF line echoes only those values, never file contents, the account ID or the recipient.
- It is safe to paste into an interactive zsh: the block has no `#` comments, `!` appears only inside single quotes or as `!=` (which zsh does not history-expand), and only a single `=` is used inside `[ ]`.

**Kit code (`p0_gate.py`).**
- `check_linkage_args` (`:588-632`) now holds all the pure checks, and `run()` calls it before `preflight_checkout` and before any prompt (`:639-640`). The kit test runs with no answers and with git and the loaders patched to fail.
- `hold_echo_off` (`:234-251`) keeps echo off for the whole STS read (`read_sts`, `:299`) and restores it in `finally`. `ask_secret_default` skips its own toggle while echo is held, and now turns echo off before showing the prompt. A real-pty test covers this.
- The I2 note about the STS output (`:264`), the I3 absolute path (`:272`), the AWS-contact line (`:9`) and the VWIN date wording (`:196-200`) are all fixed.

**Finding 6 (`budget_execution.py`).**
- `failure_cause` now runs in its own `try`, with fallback `"Exception"`, before the `try` around `preserve()`, in both the create path (`:948-956`) and the modify path (`:1140-1148`).
- The new test confirms preservation still runs when the cause computation raises. The public codes are unchanged.

**Finding 5 (`scripts/billing/README.md`).** All three places are fixed: `:100` (rewritten), `:107` (hash now ends `3f67`) and `:117` ("must be unchanged since the incident; the incident linkage checks it").

**Finding 4 (incident record).**
- The 2611cc6 citation convention is added (`:5`, `:45`).
- 4b is resolved (`:61-63`): at 2611cc6 the file-set check was already sorted, so `UNEXPECTED_POST_APPLY_STATE` is ruled out.

**Runbooks.**
- `phase-14-live-session.md:297` now cites `:688-694`, which is correct (the `required` set is at 688-693 and the require at 694). The step-15 incident pointer is at `:310`.
- `session-2-plan.md:47-53`, `:254`, `:259`, `:269`, `:459` and `:1017-1021` agree with `prompt.md:297-321` (P0 moved, console facts, frozen commit tonight, P15 moved to tonight, A12 after the P0 verification records) and with the incident record.
- I saw no 12-digit ID or e-mail address in the passages I read.

FINDINGS (all nits; none blocking)

1. **nit**, `docs/incidents/2026-11-16-p0-budget-modify-backup-check.md:53,91`.
   - The record says the modify try block is "now `:1115-1140`". After the finding-6 fix it is `:1119-1148`. `preserve` (`:902-925`) and the other "now" ranges are still right.
   - `:5` says current locations are "in square brackets", but the record writes them as "; now `:…`" in parentheses.
   - Owner: incident-responder.

2. **nit**, same record `:95` and `:98`. The record still lists the kit update as "coordinator | Open" and "kit by coordinator". Per finding 9 the kit is now the infra-engineer's, and the update is done. Owner: incident-responder.

3. **nit**, `target/phase15/p0/p0-steps.md:231-233`. Some verifier checks are not mirrored in I1.
   - I1 counts matching lines but does not pin the structure the verifier checks:
     - preservation receipt: key set, artifact order and `source` names (`budget_verification.py:543-554`);
     - pre-apply receipt: `operation`, `plan_sha256`, `actor_arn` and key set (`:562-568`).
   - The real receipts pass these checks: my review-1 hand computation matched the operator's 490 B and 469 B exactly. A cheap, content-free hardening is two size lines: `chk "E preservation receipt bytes" "$(siz "$PRS")" 490` and `chk "E pre-apply receipt bytes" "$(siz "$PRE")" 469`.
   - Two more pre-AWS refusals in `verify()` are also not mirrored:
     - a leftover `$PRIMARY/.billing-wrapper-active.lock` (`WRAPPER_ACTIVE`, `:281`);
     - an existing `$PRIMARY/operations/$VOP` (`mkdir` at `:284`).
   - Both refusals happen before any AWS call and do not use up the verify operation.
   - The kit lives under ignored `target/`, so editing it does not affect the freeze. Owner: infra-engineer (kit).

4. **nit**, `target/phase15/p0/p0_gate.py:630`. The variable `suffix` is assigned but never used. Owner: infra-engineer.

5. **nit**, `docs/runbooks/session-2-plan.md`.
   - `:269` says the packet-root regex is at `budget_verification.py` line 431. It is now `:446`.
   - "API readback of `CostTypes`" (`:48`, `:269`, `:459`, `:1019`) is imprecise. The verifier records `cost_scope_match`, which either the legacy `CostTypes` or the equivalent FilterExpression excluding Credit and Refund can satisfy (VERIFICATION.md:122). The console's "excluded filters" wording suggests the second. Suggested wording: "API readback of the cost scope (credits and refunds excluded)".
   - `:48` reads "The recorded API readback … is not yet recorded", which repeats itself.
   - Owner: documentation-engineer.

ASSUMPTIONS: Same as review 1: the operator-reported file sets, sizes and hashes are accurate, and the state has not changed since the incident.

RISKS: I1 has only run on synthetic trees. Its first real run (Tuesday) is the true test; any DIFF stops the run before AWS, with nothing consumed.

MANUAL ACTION REQUIRED: The commit needs the user's explicit yes. The human runs I1 offline before I2.

BLOCKED-ON OWNER: none. Optional nit repairs route as listed: incident-responder (1, 2), infra-engineer (3, 4), documentation-engineer (5).

BLOCKED-ON EVIDENCE: Observed test results, because no shell was available in this session.

NEXT GATE: Coordinator full check (A1.7), then the user-approved frozen commit, then Tuesday's I1, then I2/I3.

Coordinator note on review 2 (2026-11-16): verdict APPROVE. Nits 1, 2 (incident record) and 5 (session-2-plan.md) were applied by their owners as wording and line-number corrections and are not sent back for review; nits 3 and 4 are kit-only (`target/phase15/p0/**`, ignored, outside the frozen tree) and go to the infra-engineer. The full check (`scripts/check.sh`, A1.7, includes the sbt gate = P20) runs next on the main checkout.

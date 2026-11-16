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

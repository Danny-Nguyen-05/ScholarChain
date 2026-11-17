# Phase 15 owner reports

## Work order 1: P0 budget guard, offline part (2026-11-15)

Human decision (2026-11-15, chat): accept the five P0 defaults with the condition that the budget excludes credits and refunds (`prompt.md`, "Work order 1"). The live part (the reviewed `budget_execution.py modify`) is planned for Tue 2026-11-17 by the human; nothing live has run.

Assembled by the coordinator (the main Claude Code session) from the agents' final reports, which are reproduced verbatim below. Counts inside those reports are agent-reported; the coordinator's own runs are in [test-report.md](test-report.md).

### Agents launched

| Agent | Native ID (Claude Code) | Model / effort | Assigned paths | Handoffs |
|---|---|---|---|---|
| `infra-engineer` | `a3e8741b67a1723e6` | Opus 5.5 (`opus`), high | `infra/terraform/billing-bootstrap/**` (main.tf, tests, README), `scripts/billing/**` (wrapper, verifier, their tests, README, VERIFICATION.md); read-only: `reviewed-pins.json`, the modify template | Returned BLOCKED-ON for `tests/infra/test_billing_replan_14b.py` and `tests/infra/README.md` (test-engineer) and for `docs/runbooks/phase-14-live-session.md` and `docs/demo-script.md` (documentation-engineer). The coordinator routed them as P0-T and P0-D. |
| `test-engineer` | `aa30bd750c09c502e` | Opus 5.5 (`opus`), high | `tests/infra/test_billing_replan_14b.py`, `tests/infra/README.md` | Received P0-T from the coordinator (infra-engineer's BLOCKED-ON). Returned DONE; handed back to the coordinator for review and the full gates. |
| `documentation-engineer` | `a005d59521e097345` | Opus 5.5 (`opus`), high | `docs/runbooks/phase-14-live-session.md` (added lines only), `docs/demo-script.md` line 223 (untracked draft, outside this review) | Received P0-D from the coordinator (infra-engineer's BLOCKED-ON). Returned DONE; handed back to the coordinator. |

Launch times (UTC, 2026-11-15): infra-engineer 20:35; test-engineer and documentation-engineer 20:51, in parallel, after the infra-engineer's report. No reviewer was launched by any agent or the coordinator; the review is the user's. No agent made an AWS, Anthropic or Voyage call, read a private tfvars, state or `.env` file, or committed.

### Summary of changes

| Owner | Files | Change |
|---|---|---|
| infra-engineer | `infra/terraform/billing-bootstrap/main.tf`, `tests/budget.tftest.hcl`, `README.md` | notification set `[10, 15, 20]` to `[18, 20, 22]` (ACTUAL, ABSOLUTE_VALUE, GREATER_THAN); in-place update of the one budget; amount 25, period 2026-10-01 to 2027-01-01, cost types (credits and refunds excluded, tax included), recipient wiring and tags unchanged; six hand-written tftest checks; the README states the budget covers AWS charges only (Anthropic and Voyage in the LLM ledger and the combined total) |
| infra-engineer | `scripts/billing/budget_execution.py`, `budget_verification.py`, `tests/test_budget_execution.py`, `tests/test_budget_verification.py`, `README.md`, `VERIFICATION.md` | `USD25_SHAPE` thresholds `(18, 20, 22)` (no logic change); new refusals for a USD 25 budget still at 10/15/20 (`NOTIFICATION_THRESHOLD`, `LIVE_STATE_UNEXPECTED` before any backup or apply, `PLAN_NOTIFICATIONS`, `APPLIED_BUT_POST_VERIFY_FAILED`); README steps 11 and 16 and "Pins that become stale" updated, with a read-only pin-recompute command |
| test-engineer | `tests/infra/test_billing_replan_14b.py`, `tests/infra/README.md` | hand-written 18/20/22 expectation and a superseded-set test; the scan-coverage test replaced by an equality check against the merge base plus a controlled scratch-repository test (the old one assumed the branch differed from main) |
| documentation-engineer | `docs/runbooks/phase-14-live-session.md` | 7 added lines only: dated notes at A3 and the other 10/15/20 mentions pointing to P0; the Session 1 text is unchanged |

Not changed: `scripts/billing/modify-public-inputs.template.json` (sha256 `946352f3…0af28`); `scripts/billing/reviewed-pins.json`, which the human refreshes at modify step 10. Seven `source_freeze` rows are stale today (3 from this change, 4 from the Phase 14B live repairs), and there is no `modify` object yet, so the wrapper stops with `MODIFY_PINS_MISSING` until the human adds it.

Local-only (git-ignored) repair by the infra-engineer: one broken provider link in `infra/terraform/billing-bootstrap/.terraform` was re-pointed to the local deployer provider copy (no network; lock file unchanged). Known local-only issues outside this change: broken provider links in `infra/terraform/billing-execution/.terraform` and `infra/terraform/spikes/emr-spark/.terraform`, and `terraform fmt` flags the human's private `course.local.tfvars` (not opened). The clean-snapshot gate run is unaffected.

Ownership: each tracked file was edited only by the owner named in the table above, per `docs/agents.md` (`infra/terraform/**` and `scripts/**` infra-engineer; `tests/**` test-engineer; `docs/runbooks/**` documentation-engineer). The coordinator wrote only `docs/agent-runs/phase-15/**` records. The test-engineer reported that `docs/runbooks/phase-14-live-session.md` showed as modified while it worked; that was the documentation-engineer's parallel P0-D edit, not an unowned change.

Open: the live modify (human, 2026-11-17). Expect alert e-mails right away if AWS spend before credits already exceeds USD 18 when the alerts are created.

### Consolidated report (coordinator)

```text
STATUS: COMPLETE (offline part); live modify pending the human's 2026-11-17 run
OWNER: coordinator (assembling infra-engineer a3e8741b67a1723e6, test-engineer aa30bd750c09c502e, documentation-engineer a005d59521e097345)
WORK ORDER: docs/agent-runs/phase-15/prompt.md, "Work order 1: P0 budget guard"
FILES CREATED: none tracked (docs/agent-runs/phase-15/ records by the coordinator)
FILES MODIFIED: the 12 tracked files in the summary table above
COMMANDS RUN: per agent report below; coordinator runs in test-report.md
TEST RESULTS: sbt check exit 0 (1567/0/1 canceled); clean-snapshot check.sh --skip sbt exit 5, PARTIAL passed=6, every other gate PASS
VALIDATION RESULTS: terraform fmt/validate/test (mock) pass; live plan, apply and readback unverified
ASSUMPTIONS: the live budget is still USD 200 with 50/80/100% alerts (from the user's decision text, not a live read)
RISKS: immediate alert e-mails if AWS spend before credits already exceeds USD 18; alerts AWS-only and 8-24 h late
MANUAL ACTION REQUIRED: the human's Switch-role check, pin refresh at modify step 10, gate record and live modify on 2026-11-17
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: user-launched review, then the user's "Yes, commit"
```

### infra-engineer final report (`a3e8741b67a1723e6`, verbatim)

```text
## Where we are

The code now targets **USD 25 with actual-spend alerts at USD 18, 20 and 22**, all offline. The Terraform tests (12/12) and the three billing test suites pass. Two things are still open before your Nov 17 run:
- **A test owned by the test-engineer still expects 10/15/20.** It now fails, and it is part of the full `check.sh` run.
- **Some docs still say 10/15/20.** They are files I'm not allowed to edit.

I did not run the full `check.sh --only terraform,script-tests` (about 65 minutes). Its terraform part fails anyway, for reasons unrelated to this change (below).

---

STATUS: DONE within my files, with two BLOCKED-ON items for other owners. Nothing was committed or staged. No AWS call or STS call was made, and nothing private was read.

OWNER: infra-engineer

WORK ORDER: P0, Phase 15, branch phase-15. Human decision of 2026-11-15: USD 25, alerts at USD 18, 20 and 22.

FILES CREATED: none

FILES MODIFIED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/billing-bootstrap/main.tf
  - The alert set changed from `[10, 15, 20]` to `toset([18, 20, 22])`, and the comment cites the 2026-11-15 decision.
  - It is still one inline `dynamic "notification"` block on the same budget resource, so the change is an in-place update.
  - Amount, period, cost types (credits and refunds excluded, tax included), recipient wiring and tags are unchanged.
- /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/billing-bootstrap/tests/budget.tftest.hcl
  - The old combined check is now six separate hand-written checks:
    - exactly three alerts;
    - each one ACTUAL, ABSOLUTE_VALUE and GREATER_THAN;
    - thresholds exactly {18, 20, 22};
    - no PERCENTAGE or FORECASTED alert;
    - the set is not {10, 15, 20} and contains no 10 or 15;
    - none of 50/80/100;
    - every threshold below 25 and below the amount.
  - The amount checks (25 accepted; 200, 24, 26, 0, 400 rejected) and the credit/refund checks are kept.
- /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/billing-bootstrap/README.md
  - The intro and the Phase 14B section now say 18/20/22 and cite the 2026-11-15 decision.
  - It notes that 10/15/20 was never applied (A3 was skipped on 2026-11-11).
  - It states plainly that the budget covers **AWS charges only**: Anthropic and Voyage are tracked in the LLM ledger and the combined C11 total, and credits and refunds are excluded.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/budget_execution.py
  - `USD25_SHAPE = Shape("usd25", Decimal(25), "ABSOLUTE_VALUE", (18, 20, 22))`, plus the comment and the `modify` docstring.
  - No logic changed. Plan inspection, the live-shape check, the subscriber reads and the post-apply check all read this one constant.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/budget_verification.py — docstring only.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/tests/test_budget_execution.py
  - Expectations changed by hand to 18/20/22.
  - New refusal tests for a USD 25 budget that still has the old 10/15/20 alerts:
    - the readback check rejects it (`NOTIFICATION_THRESHOLD`);
    - it is not treated as "already at target" (`LIVE_STATE_UNEXPECTED`);
    - the modify refuses it before any backup or apply;
    - a plan showing 10/15/20 or 15/20/22 is refused (`PLAN_NOTIFICATIONS`);
    - a post-apply read showing 10/15/20 gives `APPLIED_BUT_POST_VERIFY_FAILED`.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/tests/test_budget_verification.py — hand-written 18/20/22, plus refusal cases for the old 10/15/20 set and a leftover 15.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/README.md
  - The Phase 14B text, step 11 (gate record says 18/20/22), step 16 (console shows $18, $20, $22) and "Pins that become stale" are updated.
  - It adds a read-only command that recomputes the stale pins.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/VERIFICATION.md — the Phase 14B section now says 18/20/22.
- Not changed:
  - `modify-public-inputs.template.json` holds no thresholds; its sha256 is still `946352f3a60b1d74e5c7b84fb21b06773fe8fe43dd05811ab5d9cc601660af28`, so step 3 is unchanged.
  - `reviewed-pins.json` is human-refreshed, per the README.
- Local cache only (ignored, not tracked):
  - What I did: I deleted one broken link at `infra/terraform/billing-bootstrap/.terraform/providers/.../aws/6.44.0/darwin_arm64`. It pointed to a deleted `/tmp/scholarchain-phase12b-repair1-infra` folder.
  - How it was reinstalled: the pinned provider was reinstalled from the local `infra/terraform/deployer/.terraform` copy using a scratch mirror config. That used no network and left the lock file unchanged.

COMMANDS RUN (Terraform 1.13.5 at /opt/homebrew/bin/terraform, run from infra/terraform/billing-bootstrap):
- Baseline before any edits: the three billing suites ran 113 / 62 / 39 tests, all exit 0.
- Same environment for each run: `AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null CHECKPOINT_DISABLE=1 TF_IN_AUTOMATION=1 TF_INPUT=0`.
- First pass, with a scratch data folder and local mirror: `terraform init -backend=false -input=false -lockfile=readonly` exit 0; `terraform fmt -check -recursive` exit 0; `terraform validate` exit 0 ("Success! The configuration is valid."); `terraform test` exit 0, **12 passed, 0 failed**.
- Second pass, in place (the way check.sh runs it): init exit 0, fmt exit 0, validate exit 0, test exit 0, **12 passed, 0 failed**.
- Terraform mutation check on scratch copies:
  - Alert sets tried: [10,15,20], [18,20,25], [18,20], [15,20,22], [18,20,22,24] and [50,80,100]. Field changes tried: PERCENTAGE, FORECASTED and LESS_THAN.
  - Result: each one failed exactly the intended run (11 passed, 1 failed).
- Python mutation check: with the constant put back to (10,15,20) in a scratch copy, the execution suite gave 12 failures and 11 errors, and the verification suite gave 6 failures and 3 errors.
- Final runs:
  - `python3 -I scripts/billing/tests/test_budget_execution.py` exit 0, **115 tests OK** (113 before, plus 2 new).
  - `python3 -I scripts/billing/tests/test_budget_verification.py` exit 0, **62 tests OK** (new cases were added as subtests).
  - `python3 -I scripts/billing/tests/test_publication_evidence.py` exit 0, **39 tests OK**.
- `cd tests/infra && python3 -m unittest -v test_billing_replan_14b` exit 1, 28 tests, 2 failures (see BLOCKED-ON and RISKS).
- `TERRAFORM_BIN=/opt/homebrew/bin/terraform scripts/check.sh --only terraform` exit 4 (gate FAIL, 77 s).
  - billing-bootstrap passed (12 passed); deployer, spikes/emr-spark-isolated and infra/terraform also passed (113, 40 and 272).
  - The three failures, none caused by this change:
    - `fmt -check -recursive` flags the ignored, untracked private `infra/terraform/environments/course.local.tfvars`. Terraform printed only the name; I did not open the file.
    - `init failed: infra/terraform/billing-execution`, because of the same broken `/tmp` provider link.
    - `init failed: infra/terraform/spikes/emr-spark`, same cause.
  - The gate always prints a note that init downloaded providers. In this run, the only installs attempted were for the two roots that failed.
- I did **not** run `check.sh --only terraform,script-tests`: it takes about 65 minutes, the terraform part already fails for the reasons above, and script-tests would fail on the test-engineer's out-of-date test. I ran the terraform gate plus the billing suites directly instead.
- Network: `terraform version` made one HashiCorp version check before I set `CHECKPOINT_DISABLE`. No registry download was needed for billing-bootstrap.

TEST RESULTS: as listed above. A scan of the added lines found no 12-digit number and no address other than `example.invalid`.

VALIDATION RESULTS: fmt, validate and the mock test all pass for billing-bootstrap. The plan and live behaviour are not verified; the saved plan and the verifier on Nov 17 are the proof.

ASSUMPTIONS:
- "None of 10/15/20" cannot be literal, because USD 20 is in the new set. I read it as: the set is not {10, 15, 20}, and 10 and 15 are absent.
- "The live budget was never modified" comes from your decision text, not from a live read.

RISKS:
- `tests/infra/test_billing_replan_14b.py` has a second failure, `test_the_scan_really_covers_changed_and_new_files`, that is unrelated to this change. It expects the template to differ from `main`, but `HEAD == main == a576878` and the template is unchanged since `f5490d3`.
- The Budgets alert emails measure **AWS charges only, before credits**. If AWS charges in the period are already above USD 18, 20 or 22 when the modify runs, expect alert emails right away. I did not check spend.
- During the apply, alerts are briefly deleted and recreated (already documented).

STALE PINS (`scripts/billing/reviewed-pins.json`, last refreshed in `2eb30ef` on 2026-11-10; there is still no `modify` object, so the modify stops with `MODIFY_PINS_MISSING` until you add it). Seven `source_freeze` rows are stale today:
- Made stale by this change: `infra/terraform/billing-bootstrap/main.tf`, `infra/terraform/billing-bootstrap/README.md`, `infra/terraform/billing-bootstrap/tests/budget.tftest.hcl`.
- Already stale at HEAD from the Phase 14B live repairs: `infra/terraform/modules/runtime/compute.tf`, `infra/terraform/modules/workflow/main.tf`, `tests/infra/README.md`, `tests/infra/terraform_source_guard.py`.
- Still matching: variables.tf, outputs.tf, versions.tf, .terraform.lock.hcl and billing-execution/README.md.
- Who and when: you refresh them at **step 10 (C2)**, after review and after commit C. That covers these rows, any row a later fix changes, and the new `modify` object (plan hash and bytes from step 9, the input hash from step 6, and the seven `config` rows hashed from the files at commit C).
- I wrote no hash into the pins file. To recompute at commit C, use the read-only one-line command in the README's "Pins that become stale" section; it prints the path, bytes and sha256 of each stale row and then `stale=<n>`. Today it printed `stale=7`.
- Older gates' `wrapper_files` maps are out of date.

MANUAL ACTION REQUIRED (Nov 17, compared with the existing modify procedure):
1. The procedure is the same in order. The values that change:
   - The plan check and the live checks expect 18/20/22.
   - Your step 11 gate record should say "alerts at USD 18/20/22".
   - The step 13/14 output should still show `notification_count: 3`.
   - Step 16 in the console should show $18, $20 and $22.
2. If the live budget is unexpectedly already at USD 25 with 10/15/20 alerts, the wrapper now stops with `LIVE_STATE_UNEXPECTED` before any backup or apply. Stop and report; do not work around it.
3. Recompute the stale pins at commit C (step 10). Do not copy them from this report.
4. Step 3's template hash is unchanged.
5. Please don't use the old phase-14 runbook's 10/15/20 wording (BLOCKED-ON below). `docs/runbooks/session-2-plan.md` already says 18/20/22.
6. Optional, local machine only: to clear the check.sh terraform failures, delete the broken provider links in `infra/terraform/billing-execution/.terraform` and `infra/terraform/spikes/emr-spark/.terraform`, and fix the formatting of your private `course.local.tfvars` with `terraform fmt`. I did not touch these, because they are outside this order.

BLOCKED-ON OWNER:
- test-engineer: `tests/infra/test_billing_replan_14b.py` lines 42–45 (the test name and `[10, 15, 20]` should become 18/20/22) and line 128 (the template-scan assumption fails when the branch equals main). Also `tests/infra/README.md` lines 199–200.
- documentation-engineer (needs your approval, since `docs/runbooks/**` was off-limits to me): `docs/runbooks/phase-14-live-session.md` lines 262, 292, 306, 310, 606 and 1531 say 10/15/20; `docs/demo-script.md` line 223 says "alerts at 10, 15 and 20".
- infra-engineer, in a future order: the `billing-execution` and `spikes/emr-spark` local provider caches.

BLOCKED-ON EVIDENCE: the tests/infra output above (`Lists differ: [18, 20, 22] != [10, 15, 20]`, and `'scripts/billing/modify-public-inputs.template.json' not found` in the scanned set); `git grep` hits at the lines listed; the check.sh log lines `ERROR init failed: infra/terraform/billing-execution`, `.../spikes/emr-spark` and `environments/course.local.tfvars`.

NEXT GATE: independent code review of the 9-file diff, then the test-engineer fix to `tests/infra`, then a full `check.sh --only terraform,script-tests` after the local cache repair. After that come commit C (your consent), refreshing the pins at C2, and your Nov 17 modify gate. A reviewed plan is not approval to apply.
```

### test-engineer final report (`aa30bd750c09c502e`, verbatim)

```text
STATUS: DONE. All four tasks are complete. The module run and the whole tests/infra suite both pass, and each exited 0.

OWNER: test-engineer

WORK ORDER: P0-T (Phase 15, branch phase-15). Offline only. I made no AWS call and no git add, commit, push or stash. I did not read *.local.tfvars, *.tfstate*, ~/.aws, .env, secret directories or target/phase14/private/.

FILES CREATED: none in the repository. One throwaway mutation-check script is outside it: /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/mut.py

FILES MODIFIED (only in tests/infra/**):
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/infra/test_billing_replan_14b.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/infra/README.md

What changed:
1. Task 1, alert amounts.
   - The docstring now records the 2026-11-15 decision.
   - In `BudgetPlan`, the hand-written `DECIDED_USD = [18, 20, 22]` replaces `[10, 15, 20]`. The test is renamed `test_exactly_three_actual_absolute_value_alerts_at_18_20_and_22`. It still checks ACTUAL, ABSOLUTE_VALUE, GREATER_THAN and that every alert has a recipient. Thresholds are compared as floats.
   - The check that 50/80/100/160/200 are absent is kept.
   - New test `test_the_superseded_10_15_20_set_is_gone`: the set is not [10, 15, 20], and 10 and 15 are absent. 20 is kept because the new decision includes it.
   - The credits and refunds exclusion test is unchanged.
2. Task 2, the scan coverage test. `test_the_scan_really_covers_changed_and_new_files` is replaced by two checks:
   - (a) `test_the_scan_covers_exactly_what_the_branch_adds_in_the_real_repository`. It builds the expected file set with separate git calls against the same base, `scan.base_commit()` (the merge base with main). That set is the files `git diff --numstat -z <base>` shows with added text lines (renames handled; binary and deletion-only files left out), plus the readable untracked files, minus `docs/agent-runs/phase-12/**`. It then asserts the scanned set is EQUAL to that set. The old test only checked that one file was included.
   - (b) New class `AccountScanOnAControlledRepository`. The test builds a scratch git repository in a temp directory, with git's global and system config switched off, and points `scan.REPO` at it with mock.patch. The repository has: main; a work branch with a commit after the branch point; an uncommitted edit; an untracked file; a `docs/agent-runs/phase-12/` file; an unchanged file that holds an ID; and a change to main made after the branch left it. The assertions are:
     - exactly committed.txt, uncommitted.txt and untracked/new.json are scanned;
     - main-moved.txt and unchanged.txt are not scanned;
     - the phase-12 file is excluded;
     - the findings are exactly (committed.txt, 2), (uncommitted.txt, 3) and (untracked/new.json, 1), all with category account-id-literal;
     - the planted digits never appear in repr(findings).
   - Why this approach: the old test depended on what the branch happened to change, so it broke once HEAD == main == a576878. (a) holds for any base, including a clean tree. (b) proves on a fixture the test fully controls that committed, uncommitted and untracked additions are covered, that phase-12 is excluded and that the base is the merge base. A real file can never drift out from under it.
   - Mutation check, not kept in the repository: I swapped `base_commit` to return HEAD, and 2 of the controlled-repository tests failed. Swapping it to return main's tip made 3 fail. Both wrong bases are caught.
3. Task 3, README.
   - The W3 entry now says alerts are at 18, 20, 22 (human decision 2026-11-15, replacing the never-applied 10/15/20 set; 10, 15 and 50/80/100 are asserted absent), with credits and refunds excluded.
   - I also corrected stale wording in that entry. "diff against HEAD" is now "diff against the merge base with main". The old "Limit: after commit the diff is empty" line now explains the merge-base behaviour; account_scan.py's docstring already describes the merge base.
   - A new section, "Phase 15 P0-T", at the end of the README records these changes.

COMMANDS RUN:
- `cd tests/infra && python3 -m unittest -v test_billing_replan_14b`: exit 0, "Ran 33 tests in 14.576s", OK.
- `cd /Users/danny/Documents/UIC/CS441/ScholarChain && python3 -I scripts/lib/suite_run.py --start-dir tests/infra --pattern 'test_*.py'`: exit 0, "Ran 465 tests in 894.753s", OK. Summary line: SUITE-SUMMARY ran=465 executed=465 skipped_tests=0 skipped_classes=0 failures=0 errors=0
- Mutation check: `python3 <scratchpad>/mut.py` from tests/infra. HEAD-base mutant: failures=2. main-tip mutant: failures=3.

TEST RESULTS:
- test_billing_replan_14b: 33 of 33 pass. The 4 new tests in AccountScanOnAControlledRepository and the new superseded-set test all pass.
- Whole tests/infra suite: 465 of 465 executed, 0 skipped, 0 failures, 0 errors.

VALIDATION RESULTS:
- The real `terraform plan` runs on scratch copies (BudgetPlan and BudgetVariables) passed against the infra-engineer's uncommitted main.tf: the plan shows thresholds 18/20/22.
- No broken provider cache link turned up in this run: no InfraNotReady and no missing-file errors in the suite log.

ASSUMPTIONS:
- The plan JSON threshold may be an int or a float, so I compare as floats.
- `git init -b main` is available (git 2.54.0 is installed).

RISKS:
- The real-repository equality test (a) applies the same skip rules as the scanner for untracked files: symlinks, files over MAX_BYTES and non-UTF-8 files. Those rules are the scanner's documented behaviour, so a change to them would need the test updated too.
- While I worked, `git status` started showing `docs/runbooks/phase-14-live-session.md` as modified. It was not in the starting snapshot and I did not edit it. Another agent or the human presumably changed it; the orchestrator should account for it.

MANUAL ACTION REQUIRED: none from this role. The work is uncommitted, and committing needs the human's explicit yes.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: An independent code-reviewer should look at the tests/infra diff together with the infra-engineer's billing diff. After that, the full `scripts/check.sh` / `sbt check` run (with JDK 17), then human acceptance.
```

### documentation-engineer final report (`a005d59521e097345`, verbatim)

```text
STATUS: DONE. Both files are edited and the link check passed (65 links, 0 broken). The runbook only gained lines; nothing was deleted or reworded.

OWNER: documentation-engineer

WORK ORDER: P0-D (Phase 15, branch phase-15). Offline only. Only these two files were edited:
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/phase-14-live-session.md
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/demo-script.md

FILES CREATED: none in the repository. One scratch link checker, outside the repo: /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/linkcheck.py

FILES MODIFIED:

1. /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/phase-14-live-session.md — `git diff --stat`: 7 insertions, 0 deletions. The original text is intact. The added lines (new line numbers):
   - Line 264, a quoted note at the top of A3 (followed by a blank line):
     `> **2026-11-15:** A3 was skipped on 2026-11-11 (user decision); the modify is done in Phase 15 as P0 with alerts at USD 18/20/22 instead of 10/15/20 — see [docs/runbooks/session-2-plan.md P0](session-2-plan.md) and [scripts/billing/README.md](../../scripts/billing/README.md). The original Session 1 text below (including every 10/15/20 mention in this section) is kept unchanged as the historical record.`
     This note covers the other mentions inside A3: the opening text (old line 262, now 267), the gate-record bullet (old 292), step 14's "$10, $15 and $20" (old 306) and "Tell the coordinator" (old 310).
   - Line 108, its own paragraph after the "Money rule" paragraph (old line 106, which says "alerts at USD 10, 15 and 20"):
     `2026-11-15 note: from Phase 15 P0 the AWS budget alerts are at USD 18/20/22, not 10/15/20 (see the [A3 note](#a3-budget-modify-to-usd-25-the-first-live-step)); the paragraph above is the Session 1 record.`
   - Line 611, a sub-bullet under the A3 checklist item (old 606):
     `  - 2026-11-15 note: A3 was skipped on 2026-11-11; done in Phase 15 P0 with alerts at USD 18/20/22 (see the [A3 note](#a3-budget-modify-to-usd-25-the-first-live-step)).`
   - Line 634, an indented line under the Cost Explorer / Budgets step (old 628, "alerts at 10/15/20"):
     `     - 2026-11-15 note: from Phase 15 P0 the alerts are at USD 18/20/22, not 10/15/20 (see the [A3 note](#a3-budget-modify-to-usd-25-the-first-live-step)).`
   - Line 1538, right after the E5 heading (old 1531; this also covers the USD 10/15/20 handling lines that follow):
     `- 2026-11-15 note: from Phase 15 P0 the alerts are at USD 18/20/22, not 10/15/20 (see the [A3 note](#a3-budget-modify-to-usd-25-the-first-live-step)); E5 below is the Session 1 record.`
   - Old line 1258 ("10/15/20/15 planned answers") is about answer counts, not budget alerts, so I left it without a note.

2. /Users/danny/Documents/UIC/CS441/ScholarChain/docs/demo-script.md, line 223 (untracked draft), one phrase changed:
   - Before: `... AWS budget alerts at 10, 15 and 20 are e-mails only, so our own caps did the protecting.`
   - After: `... AWS budget alerts at 18, 20 and 22 are e-mails only, so our own caps did the protecting.`

COMMANDS RUN:
- grep and sed reads of both files and of session-2-plan.md (P0 row at line 219 confirms 18/20/22 and the 2026-11-15 decision).
- Four Edit calls, then one `python3 -I` heredoc that inserted the Money-rule note and replaced the demo-script phrase. It asserted the exact original text was there before changing it.
- `git diff --stat docs/runbooks/phase-14-live-session.md` → `1 file changed, 7 insertions(+)`
- `git diff -U0 docs/runbooks/phase-14-live-session.md` → five hunks, only `+` lines.
- `grep -n "18, 20 and 22" docs/demo-script.md` → line 223.
- `which lychee markdown-link-check` → neither is installed.
- `python3 -I <scratchpad>/linkcheck.py docs/runbooks/phase-14-live-session.md docs/demo-script.md; echo "exit=$?"` → `links=65 external_skipped=0 broken=0`, `exit=0`.

TEST RESULTS: No code changed, so no tests apply. I did not run `sbt check`.

VALIDATION RESULTS: The link check passed. The scratch checker resolves every relative Markdown link outside code blocks against the file system and checks `#anchor` targets against GitHub-style heading slugs. It covered all 65 links in both files, including the new links to `session-2-plan.md`, `../../scripts/billing/README.md` and `#a3-budget-modify-to-usd-25-the-first-live-step`. There were no external links to skip. This is a local checker, not lychee or markdown-link-check, neither of which is installed.

ASSUMPTIONS:
- One note at the top of A3 is enough for the mentions inside A3 (old lines 262, 292, 306, 310), as the work order allowed.
- Old lines 106 and 628 also mention 10/15/20 but were not in the work order's line list. I gave each a one-line pointer as well, as added lines only.
- The link to session-2-plan.md points to the file, not to a P0 anchor, because P0 is a table row with no heading.

RISKS:
- In the demo script, line 223 comes right after the "Session 1 outcomes" list. A narrator may need to make clear that 18/20/22 are the Session 2 (Phase 15 P0) thresholds, not the ones that were live in Session 1.
- The demo script and session-2-plan.md are untracked drafts, so the A3 note links to an untracked file until it is committed.

MANUAL ACTION REQUIRED: Human review of the diff. No git add, commit or push was done; committing needs the human's explicit yes.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: Independent code-reviewer read of the two files. After that, a human decision on whether to commit with the rest of the Phase 15 P0 work.
```

## Work order 1: P0 repair round 1 (review 1, REQUEST-CHANGES; 2026-11-15)

Findings and their outcomes are in [repairs.md](repairs.md). The coordinator fixed F1 (this file), N1 (`test-report.md`) and N3 (`prompt.md`) in `docs/agent-runs/phase-15/**`; F2 was routed to its owner.

### Agents launched

| Agent | Native ID (Claude Code) | Model / effort | Assigned paths | Handoffs |
|---|---|---|---|---|
| `documentation-engineer` | `ab222e483909f6714` | Opus 5.5 (`opus`), high | `docs/runbooks/phase-14-live-session.md` line 264 only | Received F2 from the coordinator. Returned DONE; the coordinator ran the clean-worktree link check. |

No reviewer was launched. No AWS, Anthropic or Voyage call; nothing committed.

### documentation-engineer final report (`ab222e483909f6714`, verbatim)

```text
STATUS: DONE. F2 is fixed. Line 264 no longer links to the uncommitted draft, and the runbook diff against a576878 is still additions-only (7 added, 0 deleted).

OWNER: documentation-engineer (docs/runbooks/**)

WORK ORDER: P0 repair round 1, finding F2 (Phase 15, branch phase-15). Replace the markdown link to the untracked session-2-plan.md on line 264 of docs/runbooks/phase-14-live-session.md with a plain code-span path. No other change.

FILES CREATED: none

FILES MODIFIED: /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/phase-14-live-session.md (line 264 only)

COMMANDS RUN (all from /Users/danny/Documents/UIC/CS441/ScholarChain):
1. `git diff --numstat a576878 -- docs/runbooks/phase-14-live-session.md` before the edit → `7	0	docs/runbooks/phase-14-live-session.md`
2. `git ls-files --error-unmatch docs/runbooks/session-2-plan.md` → `error: pathspec 'docs/runbooks/session-2-plan.md' did not match any file(s) known to git`, exit=1. This confirms the target file is untracked.
3. One Edit on line 264: `see [docs/runbooks/session-2-plan.md P0](session-2-plan.md) and` → ``see `docs/runbooks/session-2-plan.md` (row P0; draft, not yet committed) and``
4. `sed -n '264p' docs/runbooks/phase-14-live-session.md` (output under VALIDATION RESULTS)
5. `git diff --numstat a576878 -- docs/runbooks/phase-14-live-session.md` → `7	0	docs/runbooks/phase-14-live-session.md`
6. `grep -n 'session-2-plan.md)' docs/runbooks/phase-14-live-session.md` → no output, exit=1
7. `grep -n 'session-2-plan' docs/runbooks/phase-14-live-session.md` → one match only, line 264, as the code span
8. `python3 -I /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/linkcheck.py docs/runbooks/phase-14-live-session.md` → `links=62 external_skipped=0 broken=0`, exit=0

TEST RESULTS: Not applicable. This is a docs-only change with no Scala, Python or shell source touched, so I did not run `sbt check`.

VALIDATION RESULTS:
- Line 264 BEFORE: `> **2026-11-15:** A3 was skipped on 2026-11-11 (user decision); the modify is done in Phase 15 as P0 with alerts at USD 18/20/22 instead of 10/15/20 — see [docs/runbooks/session-2-plan.md P0](session-2-plan.md) and [scripts/billing/README.md](../../scripts/billing/README.md). The original Session 1 text below (including every 10/15/20 mention in this section) is kept unchanged as the historical record.`
- Line 264 AFTER: ``> **2026-11-15:** A3 was skipped on 2026-11-11 (user decision); the modify is done in Phase 15 as P0 with alerts at USD 18/20/22 instead of 10/15/20 — see `docs/runbooks/session-2-plan.md` (row P0; draft, not yet committed) and [scripts/billing/README.md](../../scripts/billing/README.md). The original Session 1 text below (including every 10/15/20 mention in this section) is kept unchanged as the historical record.``
- The `[scripts/billing/README.md](../../scripts/billing/README.md)` link and the rest of the sentence are unchanged.
- numstat against a576878: `7	0` (additions-only, unchanged from before the edit).
- No markdown link points to session-2-plan.md (the grep exited 1 with no output).
- Local link check: 62 links, 0 broken. This ran in the working tree, not a clean worktree.

ASSUMPTIONS: session-2-plan.md stays uncommitted for this commit, as the work order says. The local linkcheck.py resolves relative links against the file's own directory in the working tree.

RISKS: The local link check ran in the working tree, where untracked files still exist. Only the coordinator's clean-worktree check can show that the committed tree has no broken links. If session-2-plan.md is committed later, the code span could become a link again, but that is optional.

MANUAL ACTION REQUIRED: None from this role. The coordinator runs the clean-worktree link check. Any commit needs the user's explicit approval.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: The coordinator runs the clean-worktree link check on docs/runbooks/phase-14-live-session.md, then an independent reviewer rechecks F2. A human approves any commit.
```

## Work order 2: P40 public semantic route and query-embedding cache (2026-11-15)

Human decisions: Step 0 defaults, decision A and the two additions, then Q16 and Q17 (all 2026-11-15, chat, quoted in `prompt.md`, "Work order 2"). Assembled by the coordinator from the agents' final reports, which are reproduced verbatim below (counts inside them are agent-reported; the coordinator's own runs are in [test-report.md](test-report.md), "Work order 2").

### Agents launched

| Agent | Native ID (Claude Code) | Model / effort | Assigned paths | Handoffs |
|---|---|---|---|---|
| `rag-engineer` | `a7f9a5c79c41b7e91` | Opus 5.5 (`opus`), high | `modules/rag/**`: `CachingEmbeddingClient.scala`, its spec, README | Returned the decorator API; the coordinator passed it verbatim to the service-engineer (P40-S). |
| `documentation-engineer` | `a0b1b67aacbd708aa` | Opus 5.5 (`opus`), high | `docs/runbooks/session-2-plan.md` only (untracked draft) | P40-D, then an addendum after the user's Q16/Q17 answers (resumed by SendMessage). Raised Q16 and Q17 for the user. |
| `service-engineer` | `a8eb91cfdf8a2e03d` | Opus 5.5 (`opus`), high | `modules/services/**`: route, rate limiter, cache wiring, config, OpenAPI, README, tests | Started after the rag-engineer finished (no concurrent sbt). Returned BLOCKED-ON infra-engineer (smoke, acceptance (9)), test-engineer (independent test), experiment-engineer (P42), infra-engineer (P41 env wiring). |
| `infra-engineer` | `a4055ea6deb614993` | Opus 5.5 (`opus`), high | `scripts/smoke-test.sh`, `scripts/smoke-local.sh`, `scripts/lib/smoke_client.py`, `scripts/tests/test_smoke.py`, then `scripts/README.md` | P40-I from the service-engineer's BLOCKED-ON (9). The coordinator accepted `scripts/lib/smoke_client.py` (inside `scripts/**`, outside the order's literal list) and resumed it for the README addendum. |
| `test-engineer` | `afbef4f224802cc51` | Opus 5.5 (`opus`), high | `tests/src/test/.../independent/AdversarialPublicSemantic{Fixture,HttpSpec}.scala`, `tests/README.md` | P40-T. Returned BLOCKED-ON service-engineer: deep-nested JSON gave HTTP 500 and a printed StackOverflowError. |
| `service-engineer` | `a72af9596c8a90dc4` | Opus 5.5 (`opus`), high | `modules/services/**`: `RequestJson.scala`, `RequestNestingSpec.scala`, route, `ApiContracts.scala`, `SemanticApi.scala`, `ApiApplication.scala`, README, OpenAPI | P40-S repair 1 (fresh context) for the test-engineer's defect, plus the coordinator's decision on nonblocking (a) truncate hits to topK; (b) and (c) recorded only. |

No reviewer was launched. No agent made an AWS, Anthropic or Voyage call or committed. sbt runs were sequenced so that no two agents ran sbt at once in this tree (the infra-engineer ran no sbt).

Ownership: each path was edited only by the owner named above, per `docs/agents.md` (`modules/rag/**` rag-engineer; `modules/services/**` service-engineer; `scripts/**` infra-engineer; `tests/**` test-engineer; `docs/runbooks/**` documentation-engineer). The coordinator wrote only `docs/agent-runs/phase-15/**` and git-ignored files under `target/phase15/`.

Rule slip (disclosed by the documentation-engineer, P40-D): a recursive `grep` for `SCHOLARCHAIN_SEMANTIC_INDEX` over `infra/terraform` matched lines in local `terraform.tfstate*` files, which agents must not read; the output contained an account ID. Nothing from it was used or written; the plan has no 12-digit number (coordinator grep: 0). Later briefs required `--exclude='*.tfstate*'` or explicit paths.

Follow-ups recorded, not done in P40:
- factory-engineer: the PostToolUse scalafmt hook runs sbt under Java 27, resolves the edited path against every subproject ("Failed to read ..."), starts sbt between agents' runs, and once rewrote a test file into code that did not parse (repaired by the service-engineer with the module's scalafmt). Reported by the rag-engineer, service-engineer and test-engineer.
- service-engineer (coordinator decision pending): Cask's default handler prints a `ClosedChannelException` stack trace when a reply is written after the caller closed the socket (pre-existing; seen in tests with a deliberately slow downstream).
- Pre-existing, recorded only: lower-case `bearer` gets 401 on all `/v1` routes; query-api's internal route forwards shallow non-object bodies (internal token only); downstream reply bodies are not depth-checked (the StackOverflowError backstop returns a typed 500).
- P41 (infra-engineer): Terraform env wiring of `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` / `_BURST` (query-api) and optionally `SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES` (semantic-service). P42 (experiment-engineer): semantic route in the load generator, fixed question set, required per-level limits, warm-up pass, 429s reported separately. P15: rebuild images.
- infra-engineer (coordinator observation S1 in `repairs.md`): `scripts/smoke-local.sh --build` reused a distribution built before P40, so the coordinator's first smoke run failed with a 404. It passed after `sbt -batch packageServices` (`test-report.md`, "Work order 2").
- `/v1/query` behaviour change from the repair: a body nested deeper than 32 levels now gets 400 `INVALID_REQUEST` instead of 422 `UNSUPPORTED_QUERY` (documented in the services README).

### rag-engineer final report, P40-R (`a7f9a5c79c41b7e91`, verbatim)

````text
## Summary

The P40 cache decorator is written and tested. All 17 cache tests pass, and so does the whole rag suite (228 of 228 tests, JDK 17). I changed files under `modules/rag/**` only. The full `sbt check` was not run, as instructed; the coordinator runs it.

**STATUS**
COMPLETE. Waiting for independent review. I have not approved my own work.

**OWNER**
rag-engineer

**WORK ORDER**
P40-R (Phase 15, branch phase-15): a bounded LRU cache for query embeddings in `modules/rag`. Sources: session-2-plan row P40 and finding F25, and "Work order 2" in `docs/agent-runs/phase-15/prompt.md` (cache defaults accepted by the user on 2026-11-15).

**FILES CREATED**
- `/Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/CachingEmbeddingClient.scala`
- `/Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/CachingEmbeddingClientSpec.scala`

**FILES MODIFIED**
- `/Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/README.md`: 37 lines added. The new section "Query-embedding cache: `CachingEmbeddingClient` (P40)" sits just before "### Tests" and covers purpose, identity, keying, bounds, calls, counters, what is not cached, concurrency, and the no-text-in-output rule.

Nothing outside `modules/rag` was changed. `git status` still shows `docs/agent-runs/phase-15/prompt.md` as modified and `docs/demo-script.md` and `docs/runbooks/session-2-plan.md` as untracked; all three were already like that at session start.

**COMMANDS RUN**
Every sbt run used this environment: `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`, that JDK's `bin` first on `PATH`, and `SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml`.
1. `sbt -batch "rag/testOnly edu.uic.cs441.scholarchain.rag.CachingEmbeddingClientSpec"`
   - Result: 16 passed, 1 failed.
   - The failure was a miscount in my test, not a code fault. The test expected 5 underlying calls; the code correctly made 4 (three failing calls, then one retry).
   - I changed the expectation to the exact call list `Vector(Vector("a","b"), Vector("a"), Vector("a"), Vector("a","b"))` and stats `EmbeddingCacheStats(0, 6, 0, 2, 4)`.
2. The same `testOnly` command, run three times in a loop to check the concurrency tests are stable. Each run: "Java 17.0.20.1", `Tests: succeeded 17, failed 0, canceled 0, ignored 0, pending 0`, `All tests passed.`
3. `sbt -batch rag/scalafmtCheck rag/Test/scalafmtCheck rag/test`
   - Both scalafmt checks: `[success]`.
   - rag/test: `Total number of tests run: 228`, `Suites: completed 18, aborted 0`, `Tests: succeeded 228, failed 0, canceled 0, ignored 0, pending 0`, `All tests passed.`, `[success] Total time: 4 s`.
4. `git status --short` and `git diff --stat`, run only to confirm the changes stay inside my territory.
   - A first attempt that also listed `.claude/.last-test-run` (`ls`/`stat`, read-only) was blocked by the PreToolUse hook as a "possible constitutional file mutation". I did not retry that part.

**TEST RESULTS**
The 17 tests in `CachingEmbeddingClientSpec`, all passing:
- One underlying call per distinct text across repeated calls: calls `[a],[b]`; stats (3 hits, 2 misses, 0 evictions, size 2).
- An empty call or an all-hit call makes no underlying call.
- Duplicates within one call: `embed(a,b,a,a,b)` calls the underlying client once with `[a,b]`; 3 hits, 2 misses.
- Mixed hits and misses keep input order, and only the distinct misses are sent, in order: `[c,a,d]`.
- The exact text is the key, so case and whitespace variants are separate entries.
- LRU at capacity 2: a hand-derived sequence gives calls `a,b,c,b,c` and stats (2, 5, 3, 2); after further steps, (4, 6, 4, 2).
- One call with more distinct misses than capacity returns every result and keeps the newest entries.
- A thrown exception reaches the caller as the same instance (`eq`), nothing is cached, and the next call retries.
- `EmbeddingFailure` results are returned but not cached; successes in the same response are cached.
- A short response, a long response, or a response with a null element throws a closed code and caches nothing. The text is retried next time.
- A malformed success (wrong dimension, wrong model, or NaN) is returned unchanged, and nothing from that response is cached.
- Null texts are passed through to the underlying client and never cached.
- Model and provider pass through unchanged. For a plain fake, a Bedrock `ProviderEmbeddingClient` fake, and a real `VoyageEmbeddingClient` that is constructed but never called (synthetic key), `VectorConsistency.checkClient` gives the same answer on the cache as on the raw client across 5 stored identities.
- `maxEntries` of 0, -1 or `Int.MinValue` is rejected with `invalid-embedding-cache-size`. The default is 1024.
- A sentinel question never appears in `toString`, the stats `toString`, the key fingerprints, the error message, or captured stdout/stderr. The stored key contains the SHA-256 of the sentinel instead.
- Concurrency at capacity 64: 16 threads × 200 rounds × 3 texts over 40 distinct texts.
  - Every result is correct; size is 40 with no evictions.
  - hits + misses equals the number of inputs, and the texts sent to the underlying client equal the misses.
  - Misses are between 40 and 16 × 40.
  - A sequential pass afterwards makes no underlying call.
- Concurrency at capacity 8: 12 threads × 150 rounds, plus a reader thread.
  - The reader never saw size above 8 or a counter going down.
  - hits + misses equals the inputs, texts sent equal misses, and evictions + size ≤ misses.

**VALIDATION RESULTS**
- The rag scalafmt checks passed (main and test).
- The rag tests passed (228/228).
- The full `sbt check` was not run, so the repository definition of done is unverified until the coordinator runs it.
- For this decorator, the retrieval, prompt-injection and groundedness gate amounts to the cache tests: the cache creates no evidence and does not change embeddings.
- No live or provider call was made.

**ASSUMPTIONS**
- **Input type is not in the key.** The `EmbeddingClient` interface has no query/document input type: it is fixed when the underlying client is built, and one cache wraps one client. The work order made this conditional ("if the interface distinguishes"). The key is (provider wire name + `model.tag`, SHA-256 of the exact UTF-8 text). The service should wrap the Query-type Voyage client only.
- **Misses** count the distinct texts sent to the underlying client, including calls that then fail. This is meant to match "embed calls" on `/metrics`.
- **Hits** count inputs answered without their own underlying request: a cache entry, or a repeat of a text earlier in the same successful call. If the call throws, repeats are not counted as hits.
- Racing misses for the same text are not coalesced. Each racing thread may call the underlying client once, and the later insert replaces the earlier one without evicting anything. This is documented and tested.
- A cached result is returned exactly as stored, so its `attempts` is that of the original provider call.
- A wrong-length or null-element response throws `IllegalStateException` with a closed code. `SemanticApi` already maps exceptions and non-success results to typed errors.

**RISKS**
- **Memory.** Vectors are stored as boxed floats: about 5 MB at 1,024 entries × 256 dimensions, and more with a larger configured size or dimension. The services should keep the size bounded.
- **Warm-up cost.** Without coalescing, the first round of concurrent requests for a question can call Voyage up to once per concurrent request. The P35 check "embed calls equal distinct questions" is exact only if the warm-up runs before concurrency rises, or if a small surplus is accepted.
- **Guessable hashes.** The SHA-256 key of a short, predictable question can be recovered by guessing likely questions. It is kept in memory only and never logged.
- **Formatting hook (factory-owned).**
  - The PostToolUse scalafmt hook runs under Java 27 and resolves the edited path against every subproject, so each Write/Edit reported "Failed to read .../modules/<x>/modules/rag/..." errors.
  - The root project still reformatted the file, and the module scalafmt checks pass.
  - This is a hook defect for factory-engineer, not part of this work order.

**MANUAL ACTION REQUIRED**
None for this work order. The coordinator runs the full `sbt check` and routes the code-reviewer pass for the P40 bundle.

**BLOCKED-ON OWNER**
None. Two follow-ups are needed but don't block this work:
- service-engineer: wiring, the size setting from configuration, and `/metrics` counters.
- factory-engineer, optional: the scalafmt hook path issue described under RISKS.

**BLOCKED-ON EVIDENCE**
None.

**NEXT GATE**
- service-engineer wires the cache into the semantic-service composition.
- test-engineer writes the independent API test.
- The coordinator runs the full `sbt check`.
- code-reviewer reviews the whole P40 bundle.
- The human gives "Yes, commit".

## API for the service-engineer

- Package: `edu.uic.cs441.scholarchain.rag`
- Class:
  ```scala
  final class CachingEmbeddingClient(
      underlying: EmbeddingClient,
      maxEntries: Int = CachingEmbeddingClient.DefaultMaxEntries
  ) extends ProviderEmbeddingClient
  ```
  - `require(maxEntries > 0, "invalid-embedding-cache-size")` throws `IllegalArgumentException`; a null `underlying` is also rejected.
- Members:
  - `val model: EmbeddingModel` is the same as `underlying.model`.
  - `val provider: EmbeddingProvider` is the underlying's provider, or `EmbeddingProviders.infer(model)` when the underlying is not a `ProviderEmbeddingClient`.
  - `val capacity: Int`
  - `def embed(texts: Seq[String]): Seq[EmbeddingResult]`
  - `def stats: EmbeddingCacheStats`
  - `override def toString` shows provider, model id and numbers only.
- Default-size constant: `CachingEmbeddingClient.DefaultMaxEntries: Int = 1024`
- Error codes:
  - `CachingEmbeddingClient.ResultCountMismatch = "embedding-cache-result-count-mismatch"`
  - `CachingEmbeddingClient.NullResult = "embedding-cache-null-result"`
- Stats type:
  ```scala
  final case class EmbeddingCacheStats(hits: Long, misses: Long, evictions: Long, size: Int, capacity: Int)
  ```
  - The snapshot is consistent (taken under the cache lock), and hits, misses and evictions never decrease.
  - `misses` equals the number of texts sent to the underlying client (the Voyage embed count).
- Wiring: wrap the Query-type client after it is built, for example `new CachingEmbeddingClient(queryClient, configuredSize)`. Pass the wrapped client to both `consistent(...)`/`VectorConsistency.checkClient` and `SemanticApi.fromPorts`; the check gives the same result. Do not wrap the document (ingest) client.
````

### documentation-engineer final report, P40-D and addendum (`a0b1b67aacbd708aa`, report 1 of 2, verbatim)

````text
STATUS: DONE. Edited only `/Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md`. One rule slip, reported below under RISKS: a grep matched lines in the Terraform state files. Two new open questions (Q16, Q17) need the user, because the S3 Vectors cost breaks the R-c gate on planned figures and takes R-b 0.01 over the floor at full caps.

OWNER: documentation-engineer

WORK ORDER: P40-D (Phase 15, branch phase-15). Add the S3 Vectors query cost and the Voyage bound to R-b, recompute every affected total and gate, add the fixed question set and the 429 reporting rule, record the accepted P40 defaults, and note decision A for the budget modify. Edits dated 2026-11-15.

FILES CREATED: none

FILES MODIFIED: `/Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md` (untracked draft, now 827 lines). The other working-tree changes under `modules/rag/**` and `docs/agent-runs/phase-15/prompt.md` are not mine.

COMMANDS RUN (all read-only except the file edits; no git add/commit/push/stash; no AWS, Anthropic or Voyage call):
- Reads of `docs/agent-runs/phase-15/prompt.md` and the plan.
- `cat` of `experiments/manifests/15b-ecs-scaling.json` and `load-tests/config/load-profile.v1.json`.
- `grep`/`sed` over `modules/services`, `modules/storage` and `load-tests/loadgen.py`.
- `sed -n 58,59p scripts/billing/budget_execution.py`: shows `MODIFY_RECORD_PREFIX = "docs/agent-runs/phase-14/"` and `MODIFY_PACKET_PREFIX = "docs/agent-runs/phase-14/evidence/14b/"`.
- `sed -n 431p scripts/billing/budget_verification.py`: confirmed the `budget-modify-verify-` regex.
- `python3 -I` arithmetic (results below).
- A stale-figure grep, a 12-digit and e-mail pattern grep (no matches), and a relative-link check (20 of 20 links resolve).
- `git status --short`.

TEST RESULTS: no tests apply (docs only). `sbt` was not run because no Scala inputs changed.

VALIDATION RESULTS:

Link check: all 20 relative links resolve.

Identifier check: no 12-digit number or e-mail address in the file, and no domain other than public aws.amazon.com and GitHub URLs.

**Per-query cost:**
- Vector data is 256 x 4 = 1,024 B.
- Key: about 100 B typical; upper bound 1,024 B (the assumed S3 Vectors key limit, not re-read).
- Filterable metadata: about 400 B typical; upper bound 2,048 B, from the repository's `maxFilterableBytes = 2 * 1024` (`Phase7Configs.scala:66`). `textS3Uri` is non-filterable and excluded.
- Average vector size: about 1,500 B typical, 4,096 B conservative.
- Index size: 10,000 vectors. One request queries one index (`SemanticApi.scala:98`, `SCHOLARCHAIN_SEMANTIC_INDEX`); 10,000 assumes all vectors sit in that index.
- Data processed per query: 4,096 x 10,000 = 40,960,000 B = 0.00004096 TB (TB = 10^12 B). At 0.004 per TB that is USD 0.000000164.
- Request charge: 2.50 / 10^6 = USD 0.0000025.
- **Total: USD 0.00000266 per query (2.66 per million; 2.67 used).** The typical case is 2.56 per million.
- The pricing figures are US East (N. Virginia); Ohio is not listed. This is stated in the file.

**Planned query count** (assumption, to be replaced by the P35 measurement):
- Closed-loop load generator (`loadgen.py:667`), with an assumed 200 ms per request (Session 1 p50 was 132-187 ms) and no throttling.
- Durations from the 15B manifest: 120/120/150/180 s plus a 600 s hold.
- sum(level x duration) = 43,470, so 43,470 / 0.2 = **217,350 queries = USD 0.58**.
- With the 15B per-phase caps it would be 198,600 queries (USD 0.53).

**Worst case:**
- Formula: `Q_max(r) = r x 2 x 1,500 + b x 2 = 3,000r + 2b`. This uses 2 query-api tasks at most and a 1,500 s longest load window (the 50 min elasticity step minus at least 25 quiet minutes). Cost is about 0.0080 x r USD.
- At the code default r = 50, b = 100: **150,200 queries = USD 0.40**.
- Hard backstop for any r: `max_total_requests` 300,000 per run (`loadgen.py:282,426`; 429s count toward it), so at most **300,000 queries = USD 0.80**. The backstop binds whenever r_S2 >= 100.
- The planning assumption implies r_S2 >= 250, so **the plan's cap uses 0.80**. Recompute rule in the file: `min(3,000 r_S2 + 2 b_S2, P42 per-run cap, 300,000) x 0.00000267`.

**Voyage:**
- At most 100-200 distinct questions x semantic-service task starts: about 400 calls with 2 starts, about 800 allowing two extra starts.
- At most 800 x 1,000 tokens = 0.8M tokens, which would be USD 0.016 at 0.02 per million. It is USD 0 inside the 200M free tokens.

**Totals changed (old -> new, line numbers in the new file):**
- L39 (summary) R0 + R-b: 3.07/5.68 -> 3.55/6.18; project 18.90/21.51 -> 19.38/22.01.
- L40 (summary) R0 + R-b + R-c: 4.14/7.94 -> 4.62/8.44; project 19.97/23.77 -> 20.45/24.27.
- L323 gate 1: E_b 2.11 -> 2.61; threshold 3.31 -> 2.81.
- L324 gate 1 without P34: E_b 3.06 -> 3.56; threshold 2.36 -> 1.86.
- L535-537 (new) AWS-only alert lines, planned/cap: R0 17.39/18.92; R0 + R-b 19.30/21.53 (alert 18; 18 and 20); with R-c 20.33/23.69 (18 and 20; 18, 20 and 22).
- L567 (new row): S3 Vectors 0.58 planned / 0.80 cap. This replaces the 0.10/0.30 allowance at old L553.
- L637 R0 + R-b: 3.55 / 6.18; project 19.38 / 22.01; column B 20.97/23.82 -> 21.50/24.38.
- L638 without P34 at 1.35 NCU: 3.37/6.09 -> 3.85/6.59; project 19.20/21.92 -> 19.68/22.42; B 21.30/24.27 -> 21.83/24.83.
- L639 without P34 at 1.85 NCU: 3.75/6.63 -> 4.23/7.13; project 19.58/22.46 -> 20.06/22.96; B 21.73/24.87 -> 22.26/25.43.
- L640 R-c row: B 22.15/26.32 -> 22.69/26.87.
- L653 gate 1 threshold: 3.31/2.36 -> 2.81/1.86.
- L655 planned X_spent: 2.59 -> 3.07 (R-b part 1.02 -> 1.50).
- L656 gate-2 margin: +0.14 -> -0.34.
- Without P34, X_spent: 2.79/3.04 -> 3.27/3.52.
- L670 section 6.5 cost row.
- L743 risk row.
- L763 elasticity increment: 1.43 -> 1.91.
- Unchanged: R0, the 15.83 base, S = 6.17, and gate 2's limit X_spent <= 2.73.

**Other edits:**
- L12: revision note.
- L120: pricing source row.
- L227: P0 decision A.
- L233: P35 changes: successes only, 429s per level and excluded from the rate, embed calls per task, and r_S2.
- L238: P40 accepted defaults (a)-(f).
- L240: P42 fixed question set, 429 separation and tests.
- L340: runtime override for r_S2.
- L350: measurement rule. ALB metrics include 429 replies, so the load generator's figures for successful responses are primary.
- L552: floor note.
- L572: new section 6.3a.
- L809: new section 9.3.
- L826: provenance note.

ASSUMPTIONS:
- 200 ms unsaturated latency and closed-loop throughput.
- P42 copies the 15B durations.
- The longest load window is 1,500 s.
- Burst b = 2r.
- The 10,000 vectors are treated as one queried index.
- Key at most 1,024 B (the S3 Vectors limit is from memory and was not re-read).
- TB = 10^12 B.
- The Ohio price equals N. Virginia.
- Transport retries are not counted.
- The 0.10/0.30 allowance was included in the old R-b 1.43/2.11, as old line 553 states.

RISKS:
- **Rule slip:** a recursive `grep` for `SCHOLARCHAIN_SEMANTIC_INDEX` over `infra/terraform` matched lines in `terraform.tfstate*`, which I was told not to read. The output contained an account ID. Nothing from it was used or written. It is disclosed in the plan's provenance (L826) and not repeated here.
- The planned 217,350 queries probably overstates what 0.25 vCPU tasks can serve. P35 should replace it.
- Voyage first-pass misses (up to 200 per task) depend on the paid-tier limit. At the Session 1 free-trial rate (about 3 requests/min) that pass would take about 67 min. This is in section 6.3a and the risk row.

MANUAL ACTION REQUIRED: the user must answer the two new open questions.
- **Q16:** R0 + R-b at full caps is 6.18, 0.01 over S = 6.17. Default (a) is to keep the 15B per-phase caps in P42 (198,600 queries per run, R-b cap 2.34, project 21.74, gate 1 threshold 3.08). Option (b) is to rely on gate 1 at 2.81. Option (c) is r_S2 <= 98, which may throttle level 50.
- **Q17:** R-c now fails gate 2 on planned figures (X_spent 3.07 > 2.73). Default (a) is to keep R-b as designed and expect R-c to be dropped. Option (b) is to cap semantic queries at about 90,000. Option (c) is to throttle levels 25 and 50.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none. The S3 Vectors prices rest on the coordinator's read of the pricing page, which I did not re-read.

NEXT GATE: independent review of the plan diff (arithmetic and link check), then the user's answers to Q16 and Q17. The experiment-engineer (P42) and service-engineer (P40) get the recorded requirements through the orchestrator.
````

### documentation-engineer final report, P40-D and addendum (`a0b1b67aacbd708aa`, report 2 of 2, verbatim)

````text
ADDENDUM to P40-D (Q16/Q17 follow-up)

STATUS: DONE. Your Q16 condition holds: at the 198,600-query per-level limits, the project total at caps is 21.76, at or below 22.00. The per-level limits are kept, now as required limits, and the experiment is unchanged. One small correction to the coordinator's arithmetic, and because those limits now also cap the planned count, the planned figures fell by 0.05.

OWNER: documentation-engineer

WORK ORDER: P40-D follow-up (Q16 and Q17 answered by the user, 2026-11-15, chat). Edits dated 2026-11-15.

FILES CREATED: none

FILES MODIFIED: `/Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md` (now 847 lines). Nothing else; nothing staged or committed.

COMMANDS RUN (all read-only besides the edits to the plan file):
- `sed` of `load-tests/loadgen.py` lines 619-640 and 426-431, and line 636.
- `grep -rn --exclude='*.tfstate*'` over `modules/services/src/main` and `modules/rag/src/main` for the implemented environment and metric names. Found in `PublicSemanticRoute.scala` lines 42-43 and 59 and `ApiApplication.scala` lines 77-91. Rate range 1-100,000 and defaults 50/100 confirmed at lines 44-47.
- `python3 -I` for the arithmetic and the edits.
- A stale-value grep, an identifier grep, and a link check.
- No state or secret path was touched this round.

TEST RESULTS: not applicable (docs only).

VALIDATION RESULTS:
- Links: 20 of 20 resolve.
- No 12-digit number or e-mail address in the file.
- Every remaining old value is labelled as history ("originally", "step 1", "for the record").

**Arithmetic check:**
- Requests: 198,600 x 0.0000025 = 0.4965.
- Data processed: 198,600 x 4,096 B x 10,000 / 10^12 x 0.004 = **0.0325**. The coordinator wrote 0.0326; 0.0326 is the value with the 200 warm-up requests.
- S3 Vectors total: 0.5290, carried as 0.53. With up to 200 warm-up requests: 0.4970 + 0.0326 = 0.5296, still 0.53.
- Voyage: at most 0.016, carried as 0.02.
- R-b cap: 2.61 - 0.80 + 0.53 + 0.02 = 2.36.
- R0 + R-b cap: 5.93. Project at caps: 21.76, at or below 22.00. **The coordinator's figures are confirmed.**

**Numbers changed (step-1 value -> new value, line numbers in the new file):**
- L39 summary R0 + R-b: 3.55/6.18 -> 3.50/5.93; project 19.38/22.01 -> 19.33/21.76 ("fits even at caps").
- L40 summary R-c: 4.62/8.44 -> 4.57/8.19; project 20.45/24.27 -> 20.40/24.02; planned X_spent 3.07 -> 3.02.
- L32 and L42 summary text: 3.07 -> 3.02; S3 Vectors 0.58/0.80 -> 0.53/0.53 plus Voyage 0.02.
- L323-324 gate 1: E_b 2.61 -> 2.36, threshold 2.81 -> 3.06; without P34, E_b 3.56 -> 3.31, threshold 1.86 -> 2.11.
- L325: the r_S2 recompute rule is replaced by a note that E_b does not depend on r_S2.
- L536-537 AWS-only alert lines: R0 + R-b 19.30/21.53 -> 19.25/21.26; R-c 20.33/23.69 -> 20.28/23.42. The alerts that fire are unchanged.
- L539: AWS parts 5.78/4.58/7.94 -> 5.51/4.53/7.67.
- L552 floor note: "0.01 over" -> "fits even at caps".
- L567 S3 Vectors building block: 0.58/0.80 -> 0.53/0.53.
- L568: new "Voyage cache misses" block, 0 planned / 0.02 cap.
- L604-606 (section 6.3a): planned 217,350 (0.58) -> 198,600 (0.53).
- L610-623 (section 6.3a): the worst case is now bounded by the per-level limits (198,600 plus at most 200 warm-up, 0.53). The 0.80 backstop cap is gone; the rate formula is kept for the record.
- L630 and L633: Voyage notes on the warm-up and the 0.02 line.
- L643 R0 + R-b: 3.55/6.18 -> 3.50/5.93; project 19.38/22.01 -> 19.33/21.76; B 21.50/24.38 -> 21.45/24.10; fit -> "yes, even at caps".
- L644 (1.35 NCU): 3.85/6.59 -> 3.80/6.34; 19.68/22.42 -> 19.63/22.17; B 21.83/24.83 -> 21.78/24.55.
- L645 (1.85 NCU): 4.23/7.13 -> 4.18/6.88; 20.06/22.96 -> 20.01/22.71; B 22.26/25.43 -> 22.20/25.15; threshold 1.86 -> 2.11.
- L646 R-c: 4.62/8.44 -> 4.57/8.19; 20.45/24.27 -> 20.40/24.02; B 22.69/26.87 -> 22.63/26.59.
- L658 gate 1: 2.81/1.86 -> 3.06/2.11; margin 1.24 -> 1.49.
- L660-661 gate 2: X_spent 3.07 -> 3.02 (R-b part 1.50 -> 1.45); margin -0.34 -> -0.29; without P34 3.27/3.52 -> 3.22/3.47.
- L676 section 6.5 cost row: 0.58/0.80 -> 0.53/0.53 plus Voyage 0.02.
- L749 risk row: -0.34 -> -0.29; R-c expected to be dropped.
- L769 section 8 elasticity increment: 1.91 -> 1.86.

**Non-numeric edits:**
- L18: revision note.
- L233 P35: (5) r_S2 is at least 2 x the measured peak served requests per second per query-api task at level 50, within 1-100,000, with burst 2 x r_S2, set through the two environment variables (P41 wiring); a high r_S2 does not raise cost. (6) Zero 429s at every level.
- L238 P40: implemented environment and metric names.
- L240 P42: the per-level limits 600/3,000/15,000/30,000/150,000 are REQUIRED; a warm-up pass sends each distinct question once at level 1 before the ramp (concurrent misses are not coalesced); 429s per level; tests.
- L327: gate checkbox.
- L340: runtime override.
- L350: scaling-analysis rule (served requests; ALB counts include 429s).
- L815 section 9.3: Q16 and Q17 marked answered, with the user's words and the numbers.

ASSUMPTIONS:
- The warm-up adds at most 200 requests, either inside the level-1 limit or as its own phase with max_requests of at most 200.
- R-b's 0.02 Voyage line double-counts against the session-wide 0.30 Voyage cap. This is conservative and stated in the file.
- Column B non-AWS caps are now 0.42 (0.52 with R-c).

RISKS:
- Under the 200 ms assumption, levels 25 and 50 reach their limits after about 120 s. Workers stop at a phase limit (`loadgen.py` lines 426-431 and 634-636), so the load drops to nothing for about 30 s and 60 s before the hold starts. This is noted in section 6.3a; P35 will show whether it happens.
- A semantic-service task started by scale-out begins with an empty cache under load and can make a few duplicate Voyage calls. Even the extreme case stays inside the free tokens.

MANUAL ACTION REQUIRED: none in this file. P42 (experiment-engineer) must implement the required limits and the warm-up; P41 (infra-engineer) must wire the two rate-limit environment variables.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: independent review of the plan diff, then the user's review.
````

### service-engineer final report, P40-S (`a8eb91cfdf8a2e03d`, verbatim)

````text
STATUS
DONE for everything inside modules/services. One item is BLOCKED-ON another owner: acceptance (9), the smoke script calling the route. Not committed and nothing staged. No AWS, Anthropic or Voyage call was made.

OWNER
service-engineer (modules/services/**)

WORK ORDER
P40-S (Phase 15, branch phase-15): the public `POST /v1/semantic/retrieve` route, its per-key rate limiter, and the query-embedding cache wiring. Covers session-2-plan row P40 acceptance (1)-(8), finding F25, and phase-15 prompt Work order 2 (the accepted defaults).

FILES CREATED
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/PublicSemanticRoute.scala
  - Holds `PublicSemanticLimits`, `RateLimitSettings`, `EmbeddingCacheSettings`, `TokenBucketRateLimiter` (clock can be injected), `RateDecision` and `PublicSemanticRoute` (validate the request, project the reply).
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/PublicSemanticRouteSpec.scala (19 tests)
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/SemanticCacheWiringSpec.scala (12 tests)

FILES MODIFIED (all under modules/services)
- `ApiApplication.scala`
  - New query-api route, served only when the extended API is composed (404 in unconfigured mode and on other roles).
  - Order of checks: auth with the same API key → rate limit → reject any query string → public limits → `api.semantic.retrieve` (`RemoteSemanticApi` with the internal token, or the in-process `SemanticApi` in offline mode) → project the reply.
  - On 429, the reply carries a `Retry-After` header.
  - `ServiceMetrics` gains `observeRoute`, `rateLimited`, `registerEmbeddingCache`.
  - `routeLabel` adds `/v1/semantic/retrieve` and `/internal/v1/semantic/retrieve`.
  - New constructor parameter `semanticRoute`, with a default, at the end of the list.
- `AwsComposition.scala`: `semanticRole` wraps only `ports.embedding` (the query client) in `CachingEmbeddingClient` after it is built. The wrapped client goes to both `consistent(...)` and `SemanticApi.fromPorts`, and its stats are registered on metrics. The worker's document client is untouched.
- `AwsConfig.scala`: `SemanticRoleConfig.embeddingCacheMaxEntries` (default 1024), parsed with the aws `Reader` convention.
- `OfflineComposition.scala`: the in-process semantic route uses a cached deterministic embedder and registers its stats. Nothing is registered when a remote semantic service is configured. New parameter `embeddingCacheEntries`.
- `ServiceMains.scala`
  - Rate settings are parsed in `launch` for every mode and passed through to `ApiApplication`.
  - `launchLocal` reads the cache size and decides remote vs local before building the composition, so no throwaway composition is created.
- `src/main/resources/openapi/scholarchain.v1.yaml`
  - New path `/v1/semantic/retrieve`.
  - New `PublicSemanticRequest` and `PublicSemanticResponse` schemas (`additionalProperties: false`).
  - New `RateLimited` response with a `Retry-After` header.
  - `/metrics` description updated.
- `README.md`: route table, a new "Public semantic retrieval" section (steps, limits, auth, rate limit, error mapping, cache, metrics table), env rows for semantic-service and query-api, the 429 row, and the limits paragraph.

Env variables (my choice; invalid values make startup exit 2 with a code that names only the variable):
| Variable | Default | Accepted range | Refusal code |
| --- | --- | --- | --- |
| `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` | 50 | 1..100000 | `invalid-service-configuration:SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` |
| `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST` | 100 | 1..1000000 | `invalid-service-configuration:SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST` |
| `SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES` | 1024 | 1..100000 | aws mode: `invalid-aws-configuration:SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES`; offline mode: `invalid-service-configuration:SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES` |

- A blank value counts as unset, matching AwsConfig.
- The rate variables are read in every mode and role.
- The maximum number of buckets is fixed in code at 1024. It is not an env variable.

Metric names:
- `api_route_requests_total{route="…",status="…"}`: every role; the route label comes from the closed `routeLabel` set.
- `api_rate_limited_total`: only rate-limiter 429s; downstream `THROTTLED` is not counted.
- `embedding_cache_hits_total`, `embedding_cache_misses_total` (texts sent to the underlying client, i.e. Voyage calls in aws mode), `embedding_cache_evictions_total`, `embedding_cache_size`, `embedding_cache_capacity`. These appear only where a cache is composed: semantic-service, or offline-synthetic query-api with no remote semantic service.

COMMANDS RUN
All sbt commands ran with JDK 17 (`java -version` → openjdk 17.0.20.1), with `JAVA_HOME`, `PATH` and `SBT_OPTS` set as given in the work order.
1. `sbt -batch services/Test/compile` → success.
2. `sbt -batch "services/testOnly …PublicSemanticRouteSpec …SemanticCacheWiringSpec"`:
   - First run: compile error (a wrong import in my test). Fixed.
   - Second run: 26/31 passed, 5 failed, all from errors in my tests. I had counted 5 rate-limited replies instead of 6, and called `/metrics` with the internal token instead of the API key. Both fixed.
   - Third run: exit 0, 31/31.
3. `sbt -batch services/scalafmtAll services/scalafmtCheckAll services/scalafmtSbtCheck` → reformatted 2 files; both checks `[success]`.
4. `sbt -batch services/test` → exit 0, 12 s.
5. `sbt -batch independentTests/Test/compile` → success. Compile only; I edited nothing under tests/**.
6. `sbt -batch "independentTests/testOnly …IndependentServices* …AdversarialRuntimeHttpSpec"` → exit 0. Run only.
7. OpenAPI check: `ruby -ryaml -rjson` load → 17 paths, `/v1/semantic/retrieve` present. A Python local `$ref` resolver → 115 refs, 0 unresolved.

I did not run the full `sbt check`; the coordinator runs it.

TEST RESULTS
- New suites: 31 run, 31 succeeded, 0 failed (2 suites).
- `services/test`: "Total number of tests run: 155 / Suites: completed 16, aborted 0 / Tests: succeeded 155, failed 0".
- Independent services and HTTP suites: "Total number of tests run: 51 / Suites: completed 9 / succeeded 51, failed 0".
- The logs show an expected `java.nio.channels.ClosedChannelException` stack trace from cask. It comes from the deliberately slow downstream in the 504 test: the stub writes its reply after query-api has already closed the connection on timeout. The trace has no request content.

What the tests cover (expected values worked out by hand):
- Auth: 401 in the `ApiError` shape with no key, a wrong key, a key without `Bearer`, or the internal token. No downstream call. Auth runs before the limiter.
- topK: 1 and 20 accepted; 0, 21, 2.5, `"5"` and null refused.
- Question: 1,000 code points accepted, 1,001 refused. 1,000 emoji (2,000 UTF-16 units) accepted. Blank, missing, null and non-string questions refused.
- Body: exactly 8,192 bytes accepted, 8,193 refused.
- Filters: 16 accepted, 17 refused, plus malformed shapes refused.
- Rate limit with an injected clock:
  - 100 requests pass, then a 429 `RATE_LIMITED` with `retryable` true and `Retry-After: 1`.
  - 19.999999 ms later still 429; at 20 ms exactly 1 more passes.
  - +1 s gives exactly 50; a long idle period refills only to 100.
  - An invalid body over the limit is still a 429.
  - Counters: `api_rate_limited_total 6` and per-route 200 = 251.
  - Buckets are separate per key hash, and the number of buckets stays at its bound under both eviction rules.
  - The limiter holds only the SHA-256 of the key.
- Downstream errors through a real HTTP semantic-service stub with internal-token auth: 503 `SERVICE_UNAVAILABLE`, 504 `DOWNSTREAM_TIMEOUT` (both the forwarded 504 and a real transport timeout), all retryable. A malformed downstream body is a 502.
- Response shape: exactly `{hits, model}`; each hit exactly `{key, distance, metadata}`; model exactly `{modelId, version, dimension}`. Extra downstream fields are dropped.
- Sentinel: the question never appears in the log sink, in `System.out`/`System.err`/`Console`, or in `/metrics`, across the 200, 400, 401, 429 and 503 paths. It does reach the forwarded body, as it should.
- Cache, aws composition with fake ports:
  - Questions q1, q1, q2, q1 → 2 underlying calls, and `/metrics` shows hits 2, misses 2, size 2, capacity 7.
  - With capacity 1: a, b, a, a → misses 3, hits 1, evictions 2.
  - Default capacity is 1024.
  - Failed embeddings are not cached (3 calls).
  - A provider mismatch is still refused through the cache.
  - The worker and graph roles show no cache counters, and the worker's embedder is not a `CachingEmbeddingClient`.
- Config refusals: exit 2 and stderr equal to exactly the closed code (both aws and offline codes).
- Offline-synthetic query-api over real HTTP:
  - 401 without a key, then two 200s with `model` = `{synthetic-offline-services, v1, 8}`, misses 1, hits 1.
  - Env override (rate 1/s, burst 2) gives a 429 with `Retry-After: 1`.
  - With a remote semantic service configured, query-api shows no local cache counters.

VALIDATION RESULTS
- scalafmt checks for the services module (main, test, sbt) passed.
- OpenAPI YAML parses: 17 paths, 0 unresolved refs. This checks syntax and local refs only; it is not a full OpenAPI semantic validator.
- The internal route `POST /internal/v1/semantic/retrieve` and `SemanticApiConfig` are unchanged.

ASSUMPTIONS
- The public default topK is 20, the public maximum (the internal route also defaults to its maximum). The forwarded body always sets topK explicitly, so the internal default of 50 never applies.
- "Characters" means Unicode code points, for the question and filter values. Filter values use the 1,000 limit, mirroring the internal route, which bounds filter values by its question limit.
- The rate limit is checked before validation, so invalid bodies spend tokens. A query string on the public route is a 400.
- "Per-route request counts" is a new `api_route_requests_total{route,status}` counter. Routes outside the labelled set, including the graph and evidence proxies, count as `unmatched`, matching the existing request-log labels. I did not relabel them.
- Connection refused to semantic-service stays a 502 `DOWNSTREAM_FAILURE` under the existing mapping. An open circuit is a 503 `CIRCUIT_OPEN`.
- Only one API key exists, so in practice each query-api task has one bucket. The rate limit is per task, so N tasks admit N × rate.

RISKS
- At the default 50 requests/s with a burst of 100, the P35 rehearsal at level 50 may be throttled until `r_S2` is set through the env variable.
- Concurrent misses for the same question are not coalesced (a documented decorator behaviour). The first burst of identical questions can therefore cost more than one Voyage call per question.
- `embedding_cache_*` counters are per process. Read them per semantic-service task.
- The repository's PostToolUse format hook ran sbt under Homebrew Java 27 and printed `scalafmt: Failed to read …` errors for each subproject (it builds the file path relative to every subproject). The file was still formatted through the root project. This is hook behaviour, outside my territory.

MANUAL ACTION REQUIRED
- The coordinator runs the full `sbt check`.
- `code-reviewer` does the security-focused review of the whole P40 bundle.
- Commit only after the user says "Yes, commit".
- Docker images still need rebuilding (P15).

BLOCKED-ON OWNER
1. infra-engineer: `/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/smoke-local.sh` and/or `scripts/smoke-test.sh` must call `POST /v1/semantic/retrieve` against the offline-synthetic query-api. That is acceptance (9). The script should also pass through `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` / `_BURST` for P35.
2. infra-engineer (P41): Terraform task env wiring for:
   - query-api: `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` / `_BURST` (`r_S2`);
   - semantic-service: optionally `SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES`.
   No Terraform change is needed in P40; the code defaults apply.
3. test-engineer: the independent API test under `tests/**` (P40 (8)).
4. experiment-engineer (P42): the load generator's semantic route, fixed question file, and reporting 429s separately.

BLOCKED-ON EVIDENCE
- The P40 row in docs/runbooks/session-2-plan.md assigns (9) "the offline-synthetic smoke calls the route" and the env wiring outside modules/services.
- `grep` of scripts/smoke-local.sh shows it starts only query-api in offline-synthetic mode and runs smoke-test.sh. It has no semantic-route call.
- The route itself is available in that mode, verified by the test "(9) offline-synthetic query-api serves the route and reports cache counters".

NEXT GATE
1. Coordinator: full JDK 17 `sbt check`.
2. test-engineer: independent API test.
3. code-reviewer: one security-focused review of the whole P40 bundle (target Mon 2026-11-16).
4. The user's explicit "Yes, commit" (by Tue 2026-11-17; cutoff Wed 2026-11-18 12:00 CST).
````

### infra-engineer final report, P40-I and README addendum (`a4055ea6deb614993`, report 1 of 2, verbatim)

````text
STATUS: DONE. The offline smoke now calls `POST /v1/semantic/retrieve` (P40 acceptance (9)), and `smoke-local.sh` passes the semantic rate-limit settings through to the service. All the affected script test files and shellcheck pass. I also edited one file outside the order's list: `scripts/lib/smoke_client.py`. It is inside my territory, but please confirm it (see ASSUMPTIONS 1).

OWNER: infra-engineer

WORK ORDER: P40-I (Phase 15, branch phase-15). The offline-synthetic smoke calls the new public semantic route; `smoke-local.sh` passes the rate-limit settings through; offline tests; shellcheck.

FILES CREATED: none

FILES MODIFIED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/smoke-test.sh
  - New option `--semantic MODE`, where MODE is `off`, `route` or `offline-synthetic`. The default is `off`.
  - The new checks only run when the option is given, and they run after the existing six. Their STEP markers are `smoke-semantic` and `smoke-semantic-cache`.
  - Any mode other than `off` needs the API key.
  - `offline-synthetic` refuses a target that is not loopback (exit 3) before sending any request.
  - An unknown mode is a usage error (exit 2). `semantic` is not accepted as a `--checks` name.
  - Help text and the RESULT line are updated. With the default `off`, the requests and the RESULT line are byte-identical to before.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/lib/smoke_client.py (outside the order's file list)
  - New check `semantic`: one keyed POST of the fixed question `{"question":"Synthetic fixture: semantic retrieval smoke for A","topK":5}`. It requires:
    - HTTP 200;
    - exactly the top-level keys `hits` and `model`;
    - each hit to be exactly `{key, distance, metadata}`;
    - `model` to be exactly `{modelId, version, dimension}`.
  - The same POST is then sent with no key. It must return 401 with a typed `UNAUTHORIZED` body that does not echo the key.
  - A 429 is reported with its Retry-After value.
  - New check `semantic-cache` (only after `semantic` passes): it reads `embedding_cache_hits_total` from `/metrics` (with the key), repeats the same question, and requires the counter to increase. If the counter is missing, the check fails.
  - New `validate-url --require-loopback` option.
  - The question is a constant. It is never taken from input or printed.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/smoke-local.sh
  - Runs `smoke-test.sh --url URL --semantic offline-synthetic`.
  - `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` and `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST`: when set, each is checked against `^[1-9][0-9]{0,6}$` and the service's own ranges (1..100000 and 1..1000000). A valid value is passed explicitly to the query-api environment.
  - An invalid value, including an empty one, stops the script at the inputs step with `RESULT: REFUSED step=usage` (exit 2), before the JDK check and before the service starts.
  - When unset, nothing is passed and the service's code defaults apply. The script logs which case applied.
  - Help, exit codes and the PASS RESULT detail are updated. The existing prefix "passed all smoke checks" is kept.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_smoke.py
  - The Stub gains the semantic route, `/metrics` and failure switches.
  - New class `SmokeSemanticTests` with 14 tests: default unchanged; `off`; offline-synthetic success (fixed body sent 3 times, keyed/unkeyed/keyed, `/metrics` called twice with the key, key and question never printed); route mode; a route that accepts no key fails; a 401 that echoes the key fails; 5 wrong reply shapes; cache counter not increasing; metric absent; 429 and 404; a partial run plus semantic, including the no-key refusal; non-loopback refused; bad `--semantic` values; help.
  - The fake java in `SmokeLocalTests` gains the route, `/metrics` and an env switch that stops the cache-hit counter. Three new tests: values passed through (including the upper bounds, and only the variable that was set); 14 invalid values refused with the service never started; a counter that does not increase fails with exit 4. The success and help tests were extended, including a check that both variables are absent from the service environment by default.

COMMANDS RUN (exact; all offline, no AWS/Anthropic/Voyage, no sbt, no terraform, no docker):
1. Baseline before any edit:
   - `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_smoke.py'`: Ran 31 tests, OK.
   - `cd tests/scripts && python3 -I -m unittest discover -s . -p 'test_smoke*.py'`: Ran 38 tests, OK.
2. `bash -n scripts/smoke-test.sh && bash -n scripts/smoke-local.sh`: BASH_N_OK.
3. `shellcheck -x -P SCRIPTDIR scripts/smoke-test.sh scripts/smoke-local.sh`: rc=0, no output (shellcheck 0.11.0).
4. `python3 -I -X pycache_prefix=<scratchpad> -m py_compile scripts/lib/smoke_client.py scripts/tests/test_smoke.py`: PYCOMPILE_OK.
5. `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_smoke.py'`: Ran 48 tests, OK.
6. `... -p 'test_syntax.py'` (bash -n and shellcheck across all shell files): Ran 20 tests, OK, none skipped.
7. `... -p 'test_13b_repairs.py'`: Ran 22 tests, OK.
8. `cd tests/scripts && ... -p 'test_smoke*.py'` (test-engineer suite, run only): Ran 38 tests, OK.
9. `cd tests/scripts && ... -p 'test_regression_13a.py'` (run only): Ran 20 tests, OK.
10. A scratch check of the new bash constructs under `/bin/bash` 3.2.57 (indirect `+set`, `{0,6}` regex, empty-array expansion under `set -u`): all behaved as expected. `/opt/homebrew/bin/bash` does not exist, so the test runs above also used bash 3.2.
11. `git status --short scripts tests` and `git check-ignore -q scripts/tests/__pycache__`: only the 4 files above changed under scripts/; the pycache directory is ignored.

TEST RESULTS:
- scripts/tests/test_smoke.py: 48 run, 48 OK (31 before, 17 new).
- test_syntax.py: 20 OK.
- test_13b_repairs.py: 22 OK.
- tests/scripts/test_smoke*.py: 38 OK.
- test_regression_13a.py: 20 OK.
- I did not run `smoke-local.sh` against the real service jar, and I did not run sbt, as the order instructed.

VALIDATION RESULTS: `bash -n` passes and shellcheck has zero findings on both changed scripts. The changed Python compiles. No Terraform change, so terraform fmt, validate and plan do not apply.

ASSUMPTIONS:
1. Scope: the HTTP checks for `smoke-test.sh` live in `scripts/lib/smoke_client.py`, so I added the semantic checks there rather than putting Python inside the shell script. This is within scripts/** but outside the order's literal file list, so please ratify it.
2. Mode choice: the default is `--semantic off`, which keeps the deployed-environment smoke (Phase 14 RESULT line "all 6 checks passed", and the test-engineer's `tests/scripts` assertions) unchanged. Only `smoke-local.sh` turns on `offline-synthetic`.
   - The cache-counter check is limited to loopback targets. The services README says `embedding_cache_hits_total` exists only on semantic-service and on the offline-synthetic query-api with an in-process route, not on a deployed query-api.
   - `--semantic route` exists so a deployed target can later be checked for the route without the cache assertion.
3. Invalid rate-limit values exit 2 (REFUSED step=usage), the same as the script's other input errors. I also enforced the documented upper bounds, because the service would otherwise refuse to start and the script would only report "did not become healthy".

RISKS:
1. `smoke-local.sh` still passes the caller's whole environment to the service, which was already true before this change. If the caller has set `SCHOLARCHAIN_SEMANTIC_BASE_URI` or `SCHOLARCHAIN_GRAPH_BASE_URI`, query-api would try a remote semantic service, and the cache check would fail or be meaningless. I did not change this (out of order scope); stripping those variables for the child is a possible follow-up.
2. The fakes stand in for the real query-api. Its real `/metrics` text and reply shape have only been compared against the README and OpenAPI. They are proven against the real jar only after packageServices and a real `smoke-local.sh` run.
3. The 401 check sends the request with no key, as the order specified; it does not also send an invalid key.

MANUAL ACTION REQUIRED:
1. Orchestrator or human: accept or reject the `scripts/lib/smoke_client.py` scope addition.
2. After the coordinator's sbt check and packageServices, run `scripts/smoke-local.sh` to check the new steps against the real jar (local only, no cloud).
3. `scripts/README.md` ("Smoke test" row and paragraph) does not yet describe `--semantic` or the smoke-local rate-limit variables. I own that file but it was outside this order's list, so it needs a follow-up order (or the documentation owner, if that is the orchestrator's routing).

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: Independent code review of the 4 changed files, then the coordinator's full `sbt check` (not run here), then a real local `smoke-local.sh` run against the packaged query-api.
````

### infra-engineer final report, P40-I and README addendum (`a4055ea6deb614993`, report 2 of 2, verbatim)

````text
ADDENDUM to P40-I (scripts/README.md follow-up)

STATUS: DONE. `scripts/README.md` now documents `--semantic`, the two new semantic checks, and the rate-limit pass-through in `smoke-local.sh`. The only test file that reads this README passes (22/22). No script or test code changed in this addendum.

OWNER: infra-engineer

WORK ORDER: P40-I follow-up from the coordinator (docs only): scripts/README.md "Smoke test" row and paragraph, and the smoke-local description.

FILES CREATED: none

FILES MODIFIED: /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/README.md (12 lines added, 2 removed)
- Settings and environment variables table: one new row for `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` and `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST` (used by smoke-local; passed only when set; ranges 1..100000 and 1..1000000; exit 2 otherwise).
- Subphase 13B script table:
  - `smoke-test.sh` row: shows `--semantic off|route|offline-synthetic`, the opt-in `smoke-semantic` check and the loopback-only `smoke-semantic-cache` check.
  - `smoke-local.sh` row: shows the validated rate-limit variables and the `--semantic offline-synthetic` call.
- "Smoke test" section: new paragraph on `--semantic MODE`, covering:
  - `off` is the default, so the deployed smoke and its RESULT line are unchanged.
  - The fixed synthetic body and the exact `{hits, model}` reply shape.
  - The 401 without a key, with no key echo.
  - A 429 (with its Retry-After value) or a 404 fails the check.
  - The `/metrics` `embedding_cache_hits_total` increase, and why that check needs a loopback host (non-loopback is refused with exit 3 before any request).
  - Any mode other than `off` needs the key; `semantic` is not a `--checks` name; an unknown mode exits 2.
  - The RESULT line wording.
- "Smoke test" section: new paragraph on `smoke-local.sh` and the semantic rate limit, covering:
  - It passes the two variables only when set.
  - The validation `^[1-9][0-9]{0,6}$` plus the ranges.
  - A set but invalid value, including an empty one, stops at the inputs step with `RESULT: REFUSED step=usage`, exit 2, before the JDK check and before the service starts.
  - The log lines it prints, and the code defaults (50/s, burst 100) when neither is set.
- Example block: one new line showing the P35 rehearsal override.

COMMANDS RUN (all offline; no sbt, no AWS, no state files read, no git add or commit):
1. `grep -rn 'README' tests/scripts/*.py scripts/tests/*.py | grep -E 'open\(|read_text|SRC_SCRIPTS|SCRIPTS_DIR'`: only `scripts/tests/test_13b_repairs.py` lines 99 and 161 read `scripts/README.md`.
2. `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_13b_repairs.py'`: Ran 22 tests in 41.260s, OK.
3. `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_syntax.py'`: Ran 20 tests in 6.859s, OK.
4. `git status --short scripts`: README.md, lib/smoke_client.py, smoke-local.sh, smoke-test.sh and tests/test_smoke.py are modified (the last four from the main P40-I report). `git diff --stat -- scripts/README.md`: 12 insertions, 2 deletions.

TEST RESULTS: test_13b_repairs.py 22/22 OK; test_syntax.py 20/20 OK. The main P40-I results still stand, since no code changed: test_smoke.py 48 OK; tests/scripts test_smoke*.py 38 OK; test_regression_13a.py 20 OK.

VALIDATION RESULTS: Docs only, so no shell or Terraform gate applies. No link checker was run.

ASSUMPTIONS:
1. Every behaviour described in the README matches `smoke-test.sh` and `smoke-local.sh` as changed and tested in the main P40-I report.
2. Inside the backticked flag in the markdown table, the pipe is written `\|` so it does not split the table cell (GitHub markdown table escaping).

RISKS: The README describes the real `/metrics` and route behaviour from the services README and OpenAPI. It has not been checked against the packaged jar. That happens in the real `smoke-local.sh` run after packageServices.

MANUAL ACTION REQUIRED: None for this addendum. From the main report: run `scripts/smoke-local.sh` locally after the coordinator's sbt check and packageServices.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: Independent review of the 5 changed scripts/** files, then the coordinator's full `sbt check`, then a real local `smoke-local.sh` run against the packaged query-api.
````

### test-engineer final report, P40-T (`afbef4f224802cc51`, verbatim)

````text
STATUS
BLOCKED-ON service-engineer: I found one production defect in the new public route. The P40-T suite is written and runs: 13 of 14 tests pass, and the one failing test fails because of that defect. All other P40 acceptance points I tested hold over real HTTP.

OWNER
test-engineer (tests/** only). I made no production edits.

WORK ORDER
P40-T (Phase 15, branch phase-15): an independent adversarial API test of `POST /v1/semantic/retrieve` (P40 acceptance (8)). It is checked against the published contract: modules/services/README.md "Public semantic retrieval", the OpenAPI path `/v1/semantic/retrieve`, and the user's accepted defaults of 2026-11-15.

FILES CREATED
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/src/test/scala/edu/uic/cs441/scholarchain/independent/AdversarialPublicSemanticFixture.scala (304 lines). It provides:
  - service launch through the public `ServiceBootstrap.launch(role, env, factory)` in offline-synthetic mode, with an AWS port factory that refuses and counts every call (asserted 0);
  - a loopback stub semantic-service built on `com.sun.net.httpserver` that records forwarded calls;
  - an HTTP/1.1 client, a Prometheus parser and a log4j/stdout/stderr capture.
  - The capture records application loggers (`scholarchain`, `edu.uic.cs441.scholarchain`) at every level and all other loggers at INFO, the shipped root level in modules/services/src/main/resources/logback.xml.
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/src/test/scala/edu/uic/cs441/scholarchain/independent/AdversarialPublicSemanticHttpSpec.scala (910 lines, 14 tests).
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/README.md: new short index of tests/** with the suite entry. No README documented the Scala suites before; it links to the existing tests/infra/README.md.

FILES MODIFIED
None outside the three new files. A throwaway probe, tests/src/.../P40tTmpDeepProbeSpec.scala, was created, run once and deleted. The scripts/** changes in `git status` belong to the concurrent infra-engineer, not to me.

COMMANDS RUN
All runs used JDK 17 (JAVA_HOME=/opt/homebrew/opt/openjdk@17/...) and SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml.
1. `sbt -batch "export independentTests/Test/fullClasspath"`: to find the logging binding (log4j-slf4j2-impl 2.20.0; no logback).
2. `sbt -batch "independentTests/testOnly edu.uic.cs441.scholarchain.independent.AdversarialPublicSemanticHttpSpec"`, run 4 times while I fixed test-side issues (my own arithmetic and over-strict assertions):
   - run 1: 11 passed, 2 failed;
   - run 2: 12 passed, 2 failed;
   - run 3: 12 passed, 2 failed;
   - run 4: 14 of 14 passed, but with the deep-nesting test not first.
3. `sbt -batch "independentTests/testOnly edu.uic.cs441.scholarchain.independent.P40tTmpDeepProbeSpec"`: the throwaway probe (output in TEST RESULTS; file deleted).
4. `sbt -batch "independentTests/Test/scalafmtCheck" "independentTests/testOnly ...AdversarialPublicSemanticHttpSpec"`: scalafmtCheck failed with 1 file unformatted, after my scripted edits.
5. Final: `sbt -batch "independentTests/Test/scalafmtOnly <abs path>/AdversarialPublicSemanticHttpSpec.scala" "independentTests/Test/scalafmtCheck" "independentTests/testOnly edu.uic.cs441.scholarchain.independent.AdversarialPublicSemanticHttpSpec"`
   - Result: reformatted 1 file, then "Checking 1 Scala sources" with no error; testOnly reported 13 passed, 1 failed; exit=1.
I did not run the full `sbt check`. I made no git add, commit, push or stash, and no AWS, Anthropic or Voyage call.

TEST RESULTS
Final observed run (command 5): "Tests: succeeded 13, failed 1, canceled 0, ignored 0, pending 0". Suite: AdversarialPublicSemanticHttpSpec.

FAILED (production defect, see BLOCKED-ON): "deeply nested JSON inside the 8 KiB bound is a typed 400, never a 500 or a stack trace in the logs".
- Observed: array depth 4096 (exactly 8,192 bytes) → 500 with a non-JSON body; depth 4000 → 500; filter value depth 3900 → 500; topK depth 3900 → 500.
- Object depth 1300 → 400 INVALID_REQUEST.
- Report-only probes: depths 100, 500, 1000 and 2000 → 400; depth 3000 → 500.
- 6 `java.lang.StackOverflowError` traces were printed to stdout in that run.

PASSED (13):
1. Offline query-api serves the route with exactly `{hits[{key,distance,metadata}], model{modelId,version,dimension}}`. The route returns 404 on semantic-service, on graph-service and in unconfigured mode. Semantic-service's internal route accepts the internal token and refuses the API key.
2. Authentication.
   - 14 credential variants always return 401 UNAUTHORIZED on both the public route and `/v1/jobs`: none, empty, internal token, Basic, key without scheme, upper-case key, key prefix or suffix, the SHA-256 of the key or token, X-Api-Key, cookie, `?api_key=`. None of them reached the downstream.
   - Case and whitespace variants behave the same as on `/v1/jobs`: lower-case `bearer` 401, `BEARER` 401, double space 200, trailing space 200; with two Authorization headers, only the first counts.
   - The API key on query-api's internal route gives 401; the internal token is accepted there with topK 50.
3. Exact boundaries; every accepted body is forwarded once, with only question, topK and filters, unchanged.
   - Accepted: topK 1 and 20, default 20, 1,000 code points (ASCII, é, emoji), 16 filters, an 8,192-byte body (including a multi-byte body under 8,192 characters).
   - 400 INVALID_REQUEST, nothing forwarded (45 cases): topK 21, 0, -1, -0, a 20-digit number, 1e400, string, 5.5, 20.000001, boolean, array; question empty, blank, control whitespace, 1,001 ASCII, 1,001 emoji, number, null, array, missing; 17 filters, empty key, a 1,001-code-point value, number, nested, array or string filters; unknown, model, hits, `Question` and `topk` fields; 8,193 bytes (both kinds); form encoding, empty, truncated, null, array, string or number JSON, trailing garbage; `?topK=50`, `?question=...`.
   - Duplicate keys cannot smuggle a value past a limit (last value wins; see RISKS).
   - Other methods return 4xx. The route counters on /metrics match: route 200 = ok, route 400 = bad.
4. Chunked bodies over 8,193 bytes and 70,000-byte bodies (plain and chunked) return 4xx and are never forwarded.
5. Rate limit set by env (1/s, burst 3) over real HTTP.
   - Exactly 3 replies of 200, then 429 RATE_LIMITED, retryable true, trace echoed, Retry-After whole seconds in [1,2].
   - The limiter runs before validation (invalid body or query string → 429) and after authentication (wrong key → 401; 401s consume no tokens).
   - X-Forwarded-For does not bypass it; 6 path variants all return 404.
   - 429s cause no embed lookups. After waiting Retry-After, a request gets 200.
   - /healthz, /metrics, /v1/jobs, the internal route and /v1/query never returned 429.
   - `api_rate_limited_total` = route 429 count = observed 429s; route 200 = 4; route 401 = 6.
6. Concurrent burst: 40 requests on 16 threads → exactly 5 replies of 200 and 35 of 429, matching the metrics.
7. Default limits (no override): the first 100 all return 200; admissions never exceed 100 + 50 × elapsed + 1 (observed: 104 admitted, 396 throttled in 0.084 s).
8. `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND`, `_BURST` and `SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES` set to 0, -1, a non-number or an overflow value → exit 2 with `invalid-service-configuration:<variable>`; the value is never printed.
9. Projection: a stub reply with extra fields at the top level, per hit and in model (including fields carrying the question and an internal URL) yields exactly the expected JSON. The forwarded call carries `Authorization: Bearer <internal token>` and X-Trace-Id; it never carries the API key, client headers or a query string. The forwarded body is exactly `{"question":...,"topK":2}`.
10. If the downstream returns more hits than topK (5 for topK 2), all 5 are passed through, field-projected (recorded only; see RISKS).
11. Downstream errors (observed codes):
    - 503 → 503 SERVICE_UNAVAILABLE; 504 → 504 DOWNSTREAM_TIMEOUT; a transport timeout → 504 DOWNSTREAM_TIMEOUT in under 2.4 s.
    - Downstream 429 → 429 THROTTLED with no Retry-After, and `api_rate_limited_total` stays 0.
    - Non-JSON, array, `hits` not an array, or a hit without distance → 502 DOWNSTREAM_FAILURE; downstream 401 → 502 DOWNSTREAM_AUTH_FAILURE; connection refused → 502 DOWNSTREAM_FAILURE.
    - No downstream body, URL or question in any reply.
12. In-process cache: 7 distinct questions × 5 rounds → misses 7, hits 30 (28 plus 2 that differ only in topK or filters), size 7, evictions 0, capacity 1024. 400 and 401 replies do not touch the cache.
    - LRU with `SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES=2` and the sequence q1 q2 q1 q3 q1 q2 → misses 4, hits 2, evictions 2, size 2, capacity 2.
13. Two-process topology (real offline graph-service, semantic-service and query-api): 4 questions × 3 → semantic-service misses 4 and hits 8; query-api has no cache misses; route 200 = 12.
In every test that captures logs, the question sentinel, API key and internal token were absent from the captured logs, replies, headers and /metrics. A positive control checked that the capture saw the route's own `http_request` line.

VALIDATION RESULTS
- `independentTests/Test/scalafmtCheck`: passed in the final run, after `scalafmtOnly` on my spec.
- Throwaway cold-JVM probe (P40tTmpDeepProbeSpec, deleted): 4 rounds of 5 deep bodies against a fresh offline query-api.
  - Round 1: array depths 4096, 4000 and 3000 and filter value depth 3900 → `500 Error 500: Internal Server Error` (not JSON, no traceId); object depth 1365 → 400.
  - Round 2: the three arrays → 500 again; filter value depth 3900 → 400.
  - Rounds 3-4: all 400 INVALID_REQUEST.
  - 7 StackOverflowError traces printed.
  - So the failure depends on JIT warm-up: it shows on a cold server and stops once the code is compiled.

ASSUMPTIONS
- Where the contract is silent, the suite checks only safety (no 5xx, no limit smuggling, no leak) and records what it observed:
  - topK 5.0 and 1e1 → 200 (whole numbers); topK null and filters null → 400; empty filters → 200;
  - duplicate keys: last value wins and is validated;
  - lone surrogate → 200;
  - Content-Type is not enforced (text/plain, none and form all give 200);
  - an empty query component `?` → 200.
- The "no question in logs" check uses the shipped INFO root for third-party loggers. In run 3, with all loggers at TRACE, Undertow logged a raw request path that I had deliberately put the sentinel into. That happens only at TRACE.

RISKS
- **The failing test is nondeterministic.** It fails reliably when this suite runs on its own (the deep test runs first, on a cold server). Inside the full `sbt check` JVM, where earlier suites may have warmed the JIT, it may pass even though the defect is still there; it passed in run 4 when it ran later. A pass in `sbt check` is not proof of a fix; use the testOnly command above.
- **Non-blocking findings for the service-engineer or coordinator to decide:**
  - (a) The route passes through more hits than topK when the downstream returns them. OpenAPI says "At most the forwarded topK hits"; either truncate in the route or reword the OpenAPI.
  - (b) The lower-case `bearer` scheme gets 401 on all /v1 routes, although RFC 7235 says the scheme is case-insensitive. This was already the behaviour before P40 and is consistent across routes.
  - (c) query-api's internal route forwards a non-object (deeply nested) body to semantic-service and returns 200. It needs the internal token and was there before P40.
  - (d) The same overflow also returned 500 on the existing `POST /v1/query` (runs 3 and 5), so the cause is probably shared and older than P40, but the new public route exposes it.
- **Hook problem (owner: factory-engineer).** The PostToolUse format hook runs sbt with Homebrew Java 27 instead of JDK 17. It also reports "scalafmt: Failed to read [<project>/tests/src/...]" for every project, because it resolves the file path relative to each project base. It still reformatted the target file. It ran as extra sbt processes after each of my two Write calls, before my own sbt runs, not at the same time.

MANUAL ACTION REQUIRED
None from the human for this suite. The coordinator should route the BLOCKED-ON item, then rerun this suite and the full `sbt check`.

BLOCKED-ON OWNER
service-engineer (modules/services/**).

BLOCKED-ON EVIDENCE
- Path: modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/PublicSemanticRoute.scala, `validate`, line 188: `catch { case NonFatal(_) => Left(ApiError.invalid) }`.
  - `NonFatal` does not match `StackOverflowError` (a `VirtualMachineError`). The error escapes to Cask's default handler.
  - The stack shows recursion in `ujson.Value$.transform` / `ujson.AstTransformer.transformArray`. The JVM truncates the trace at 1,024 frames, so the originating application frame is not visible.
- Reproduction: an authenticated `POST /v1/semantic/retrieve` with body `"[" * 4096 + "]" * 4096` (8,192 bytes, inside the public limit) on a freshly started offline query-api.
- Observed: HTTP 500 with the body `Error 500: Internal Server Error`: not a typed ApiError, no traceId or retryable field, no X-Trace-Id check possible. A full `java.lang.StackOverflowError` trace goes to stdout.
- This breaks P40 acceptance (2)/(4): a typed 400 is expected for a non-object body. It also breaks the README's "Logs and errors never contain ... stack traces".
- Same symptom at array depth 3000-4000 and filter or topK value depth 3900. Object depth 1300-1365 is not affected.
- Requested decision: reject excessive nesting (or a non-object top level) before any recursive transform, and/or make the route handle `StackOverflowError` as a typed 400 without printing a trace. The same probably applies to the shared /v1/query parse path (ApiContracts.scala:155).
- Regression test: AdversarialPublicSemanticHttpSpec, the "deeply nested JSON ..." test.

NEXT GATE
1. The service-engineer repairs the defect in a fresh context.
2. Rerun `sbt -batch "independentTests/testOnly edu.uic.cs441.scholarchain.independent.AdversarialPublicSemanticHttpSpec"` on JDK 17; expect 14 of 14.
3. The coordinator runs the full `sbt check`.
4. The code-reviewer reviews the whole P40 bundle, including these test files, before the user's "Yes, commit".
````

### service-engineer final report, P40-S repair 1 (`a72af9596c8a90dc4`, verbatim)

````text
STATUS: COMPLETE. The blocking defect is repaired and nonblocking finding (a) is implemented. Findings (b) and (c) are recorded only. Every requested scoped gate passed when run. I did not run the full `sbt check`, as instructed.

OWNER: service-engineer (modules/services/** only)

WORK ORDER: P40-S repair 1, Phase 15, branch phase-15. Goal: a deep JSON request body gets a typed 400 and nothing is printed, both on `POST /v1/semantic/retrieve` and on the shared /v1 request-body parse path. Plus (a) truncate hits to topK, (b) record only, (c) record or say whether it is covered.

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/RequestJson.scala — `RequestJson.MaxNestingDepth = 32` and `withinDepth(text, maxDepth = 32): Boolean`. It is one loop over the raw text with fixed state, and it does not recurse:
  - `[` and `{` outside strings open a level.
  - `]` and `}` close one.
  - A `"` starts or ends a string, and a backslash inside a string escapes the next character.
  - It returns false when depth goes above the maximum or below 0 (more closes than opens).
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/RequestNestingSpec.scala — 10 tests:
  - The 32/33 boundary for arrays, objects and mixed nesting, and brackets inside strings and escapes.
  - The JIT-independent test: a 200,000-level body is refused by the pre-scan, `QueryRequest.parse`, `PublicSemanticRoute.validate` and `SemanticApi.retrieve`. Called directly on a 1 MiB thread stack, `ujson.read(deep).obj` throws StackOverflowError, which shows the guard is needed.
  - The public route returns a typed 400 for: the reported 8,192-byte `"["*4096+"]"*4096`, arrays at 3000, objects at 1365, a filter value at 3900, topK at 3900, and question/filter/topK/arrays/objects at depth 32 and 33. No refused body reaches the downstream.
  - `/v1/query` returns typed 400 for the same kinds of body (including `constraints.topics` at 32, 33 and 3900).
  - The internal semantic route on semantic-service returns 400.
  - query-api's internal route, forwarding through RemoteSemanticApi to a real semantic-service listener, returns 400.
  - Over real HTTP on a fresh listener (the deep request sent first), with System/Console out and err captured: all three answers are typed 400 with traceId, and the output has no "StackOverflowError", "Exception" or "\tat ".
  - Backstop test: a StackOverflowError behind the route becomes a typed 500 INTERNAL_ERROR with a traceId, and nothing is printed.
  - (a) topK truncation, order kept.

FILES MODIFIED (my changes only; the files already had uncommitted P40 work from earlier today):
- .../services/PublicSemanticRoute.scala:
  - `validate` refuses bodies with `!RequestJson.withinDepth(body)` before `ujson.read`.
  - It now returns `ForwardedSemanticRequest(body, topK)` (new case class).
  - `project(reply, topK)` keeps `hits.take(topK)`.
- .../services/ApiContracts.scala: `QueryRequest.parse` checks depth before `ujson.read`, then `boundary.break(Left(ApiError.invalid))`.
- .../services/SemanticApi.scala: `retrieve` refuses bodies over the size limit or failing the depth check before `ujson.read`.
- .../services/ApiApplication.scala:
  - The public route passes `forwarded.body` downstream and projects with `forwarded.topK`.
  - `handle` gains a backstop `case _: StackOverflowError => Left(ApiError.internal)`, documented as a backstop and not the fix.
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/services/README.md:
  - Step 3 now states the nesting limit, step 4 notes the shared limit on the internal route, and step 5 states topK truncation.
  - New paragraph "Request-body nesting limit" covering the limit, the scan rules, the cause, that the rate limit still runs first, the backstop, and the 422-to-400 change below.
  - The 400 row of the status table now mentions nesting.
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/services/src/main/resources/openapi/scholarchain.v1.yaml: the requestBody descriptions for /v1/semantic/retrieve, /v1/query and /internal/v1/semantic/retrieve now state the 32-level limit and the 400. The `PublicSemanticResponse.hits` description now states truncation to the first topK. `ruby -ryaml -e 'YAML.load_file(...)'` printed "yaml ok".

COMMANDS RUN (each sbt run used the JDK 17 / SBT_OPTS exports given, from the repo root):
1. `sbt -batch "services/scalafmt" "services/Test/scalafmt" "services/testOnly ...RequestNestingSpec ...PublicSemanticRouteSpec"` — 27/28. The one failure was my test helper: `HttpRequest.Builder.headers()` with no arguments throws IllegalArgumentException.
2. `sbt -batch "services/Test/scalafmt" "services/testOnly edu.uic.cs441.scholarchain.services.RequestNestingSpec"` — 9/9 passed.
3. Negative control: temporarily set `MaxNestingDepth = 1000000` with sed, ran the RequestNestingSpec testOnly, restored it to 32 with sed (confirmed with grep: line 22 `val MaxNestingDepth = 32`). Result: "succeeded 4, failed 5". With the guard disabled:
   - The public route answered 500 to the reported body (the overflow reproduced, now caught by the backstop).
   - /v1/query answered 422 to objects-1300.
   - The 200k test failed.
   - The internal-route and HTTP tests passed under the mutant because the code was already JIT-warm by then. This is why the 200k direct test is the JIT-independent check.
4. `sbt -batch "services/scalafmt" "services/Test/scalafmt" "services/testOnly edu.uic.cs441.scholarchain.services.RequestNestingSpec"` after adding the remote internal-route test — 10/10.
5. `sbt -batch services/test` — exit 0.
6. `sbt -batch "services/scalafmtCheck" "services/Test/scalafmtCheck"` — exit 0.
7. `sbt -batch "independentTests/testOnly edu.uic.cs441.scholarchain.independent.AdversarialPublicSemanticHttpSpec"` — exit 0.
8. `sbt -batch "independentTests/testOnly edu.uic.cs441.scholarchain.independent.IndependentServices* edu.uic.cs441.scholarchain.independent.AdversarialRuntimeHttpSpec"` — exit 0.

TEST RESULTS (observed):
- services/test: "Suites: completed 17, aborted 0", "Tests: succeeded 165, failed 0, canceled 0, ignored 0, pending 0", "All tests passed."
- scalafmt checks: two "[success]" lines, no errors.
- AdversarialPublicSemanticHttpSpec: "Tests: succeeded 14, failed 0". Its first test, "deeply nested JSON inside the 8 KiB bound is a typed 400, never a 500 or a stack trace in the logs", passed. The log contains 0 occurrences of "StackOverflow".
- IndependentServices* (8 suites) + AdversarialRuntimeHttpSpec: "Suites: completed 9, aborted 0", "Tests: succeeded 51, failed 0", "All tests passed."

VALIDATION RESULTS:
- Depth limit: 32. The deepest legitimate body is 3 (/v1/query `constraints.topics`); the semantic bodies are at most 2.
- Depth is checked on the raw text before any ujson call in all three request-body parsers. So /v1/query, the public route and the internal semantic route are all fixed, and the check does not depend on the JIT.
- The rate limit on the public route still runs before validation, as the README says, so a deep body over the limit gets 429.
- Likely mechanism: on a deep Arr, `.obj` throws `ujson.Value.InvalidData`, whose message renders the whole value, which recurses. This fits the reported trace through `Value.transform` / `AstTransformer.transformArray`, but I inferred it and did not trace it in source.
- (c) The shared depth check covers query-api's internal route in both setups. With an in-process SemanticApi, it refuses before parsing. With a remote semantic-service, the raw body is forwarded, semantic-service's SemanticApi refuses it, and its 400 maps to INVALID_REQUEST. The test "query-api's internal route forwarding to a remote semantic-service: deep bodies are 400" passed. Forwarding of shallow non-object bodies on that internal-token route is unchanged (pre-existing, recorded).
- (b) Lower-case `bearer` returning 401 on /v1 routes is unchanged, as instructed (recorded).

ASSUMPTIONS:
- Applying the 32-level limit to the internal semantic route is within the coordinator's instruction ("the shared /v1 request-body parse path"; (c) "if the shared depth check now covers it, say so"). The README now says the internal route is unchanged "apart from the shared request-body nesting limit".
- The StackOverflowError backstop in `ApiApplication.handle` is acceptable as defence in depth, because the pre-scan is the actual fix.

RISKS:
1. Behaviour change: on /v1/query, a deep body (more than 32 levels) whose objects carry unknown keys now gets 400 INVALID_REQUEST instead of 422 UNSUPPORTED_QUERY. This is documented in the README.
2. Pre-existing and not changed: Cask's `DefaultHandler` (cask.main.Main.scala:125, seen in the trace) prints a `java.nio.channels.ClosedChannelException` stack trace to stdout. This happens when a listener writes a reply after the caller closed the socket, for example semantic-service answering after query-api's transport timeout. It was observed in the services/test output during PublicSemanticRouteSpec (4). It is a response-write failure, not a request-body failure, but it conflicts with the README rule that logs never contain stack traces. The fix would be in ApiServer (my territory) and needs a coordinator decision.
3. Downstream reply bodies (RemoteService parsing up to maxResultBytes) are not depth-checked. A malicious internal service could still trigger the recursion; the backstop would turn it into a typed 500 rather than a printed trace. Internal-token peers only.
4. Factory-owned hook defect: the Claude Code PostToolUse Write/Edit hook (`.claude/**`):
   - It runs sbt under Homebrew Java 27, not 17.
   - It passes a repo-relative path to `scalafmtOnly` in every subproject, so it fails with "Failed to read [.../modules/<x>/modules/services/...]" on every edit.
   - On one run its root-project format rewrote RequestNestingSpec into code that did not parse (a lambda split across `new Thread(...)` arguments). I restructured the code and reformatted with the module's own scalafmt (JDK 17); the module's scalafmtCheck passes.
   - The hook also starts sbt processes automatically, between my own sbt runs.

MANUAL ACTION REQUIRED: None for this repair. The coordinator decides on risk 2 (Cask printing traces on closed-connection writes) and routes risk 4 (the hook defect) to the factory-engineer.

BLOCKED-ON OWNER: None.

BLOCKED-ON EVIDENCE: None.

NEXT GATE: Coordinator runs the full `sbt check` (JDK 17). Then independent review by the code-reviewer of the six services files above plus README and OpenAPI, and the test-engineer reruns AdversarialPublicSemanticHttpSpec on a cold server. Human acceptance of P40-S follows. No git add/commit/push/stash was done.
````

## Work order 3: P41 request-count scaling and rate-limit env wiring (2026-11-16)

Human decisions: Step 0 "Accept defaults", the P41-D follow-up answers and the second follow-up (all 2026-11-16, chat, quoted in `prompt.md`, "Work order 3" and the sections after it). P40 was committed as `cceb1f5` and pushed on the user's "Yes please commit and push it". This section is assembled by the coordinator from the agents' final reports, which are reproduced verbatim below. Counts inside the reports are agent-reported; the coordinator's own runs are in [test-report.md](test-report.md), "Work order 3".

### Agents launched

| Agent | Native ID (Claude Code) | Model / effort | Assigned paths | Handoffs |
|---|---|---|---|---|
| `infra-engineer` | `a24c41e9a3e35a927` | Opus 5.5 (`opus`), high | `infra/terraform/**`: runtime and observability modules, root plumbing, `phase15-variables.tf`, two new `terraform test` files, README, `environments/course.local.tfvars.example` (example only) | P41-I. Returned COMPLETE with no BLOCKED-ON. Two optional test-engineer follow-ups and the stale pins for the human are listed below. |
| `documentation-engineer` | `a90efc19aef14efcf` | Opus 5.5 (`opus`), high | `docs/runbooks/session-2-plan.md` only (untracked draft) | P41-D, then two follow-ups resumed by SendMessage after the user's answers. The second follow-up was told to raise no new questions. |

The `test-engineer` was not launched. `tests/infra` passes unchanged (agent-reported: 465 OK), and its two coverage gaps are optional; the user put the time into the pipeline bundle. No reviewer was launched. No agent made an AWS, Anthropic or Voyage call or committed. No sbt was run, because there was no Scala, build or test-source change in `modules/**`.

Ownership: `infra/terraform/**` was edited by the infra-engineer and `docs/runbooks/session-2-plan.md` by the documentation-engineer, per `docs/agents.md`. The coordinator wrote only `docs/agent-runs/phase-15/**` and git-ignored files under `target/phase15/`.

Coordinator notes:
- **Rule slip (coordinator, disclosed in `prompt.md`):** a read-only grep matched one line of the private `course.local.tfvars` (the line number and `service_capacity = {`, no value). Nothing from it was used. Later greps and all briefs exclude `*.local.tfvars`.
- **Deviation for the reviewer:** the infra-engineer added a precondition that the policy requires the HTTPS-attached target group (`local.load_balanced_service == "query-api"`), beyond the work-order text. Its reason is in the report.
- **Dashboard:** P9's 50-metric limit is not enforced at HEAD, and the dashboard already has 109–120 metrics. P41 adds 2. The reduction to at most 50 belongs to P9, in the elasticity bundle.
- **Optional test-engineer follow-ups (not done):**
  - `tests/infra/test_runtime_shape_14b.py:64-71` does not cover `aws_appautoscaling_policy.query_requests[0]` or the rate-limit env names.
  - `tests/infra/runtime_shape_checks.py:31` `ROOT_VARIABLE_FILES` does not read `phase15-variables.tf`. **Closed by repair 1 (G1)**: the variables now live in `phase12b-variables.tf`, which that tuple reads, and `phase15-variables.tf` is deleted. The table's "Assigned paths" entry `phase15-variables.tf` describes the first build only.
- **Human action at the commit:** refresh `scripts/billing/reviewed-pins.json` `source_freeze`. It is stale for 14 files (7 before P41). Recompute; never copy a hash from a report.

### infra-engineer final report (verbatim)

````text
STATUS: COMPLETE. Nothing is blocked. Two follow-ups for the test-engineer are optional and listed under RISKS. The human must refresh the stale pins.

OWNER: infra-engineer

WORK ORDER: Phase 15 P41-I, Work order 3 (docs/agent-runs/phase-15/prompt.md lines 80-106, "Accept defaults" 2026-11-16). Source: session-2-plan.md rows F26 and P41, and section 5.3 step 2. Branch phase-15, HEAD cceb1f5. Terraform authoring only, all offline: no AWS call, no aws CLI, and no plan or apply against real providers.

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/phase15-variables.tf (lines 1-34). Three root variables:
  - `query_requests_per_target_target`, `query_semantic_rate_limit_per_second`, `query_semantic_rate_limit_burst`.
  - All are number, default null, nullable.
  - Validation uses the form `x == null ? true : (range && x == floor(x))`.
  - Ranges: target 1..100000, rate 1..100000, burst 1..1000000.
- /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/tests/phase15_p41.tftest.hcl (402 lines). Root level, 18 runs. It reuses the phase14b_cost mock fixture and adds mocked `arn_suffix` values for aws_lb and aws_lb_target_group.
- /Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/tests/phase15_p41_runtime.tftest.hcl (243 lines). Module level (./modules/runtime), 11 runs, `composition_verified = true`.

FILES MODIFIED:
- infra/terraform/modules/runtime/compute.tf
  - Lines 70-75: the env wiring. It is inside `local.aws_role_env["query-api"]`, so it applies in aws mode and to query-api only. Two separate conditional maps add `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND = tostring(...)` and `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST = tostring(...)`, each only when its own variable is non-null.
  - Lines 323-356: the new `aws_appautoscaling_policy.query_requests`. `http_cpu` is unchanged.
- infra/terraform/modules/runtime/variables.tf, lines 177-211: three module variables. The rate variables are named `semantic_rate_limit_per_second` and `semantic_rate_limit_burst` so that `terraform fmt` does not re-align the whole `module "runtime"` block.
- infra/terraform/modules/runtime/outputs.tf
  - Line 29: `compute_controls.request_policy = one(...)`.
  - Lines 34-38: new output `alb_metric_dimensions`. It is null while there is no ALB, otherwise `{load_balancer, target_group}` (the arn_suffix values).
- infra/terraform/modules/observability/main.tf, lines 61-68: one ALB panel, present only when `var.alb_metric_dimensions != null`.
- infra/terraform/modules/observability/variables.tf, lines 21-28: `alb_metric_dimensions`, an object, nullable, default null.
- infra/terraform/main.tf, lines 140-142: root to runtime plumbing.
- infra/terraform/phase12b.tf, line 164: `alb_metric_dimensions = module.runtime.alb_metric_dimensions`.
- infra/terraform/environments/course.local.tfvars.example, lines 166-180: commented template lines with units, ranges and "values come from P35". Only the example file was edited.
- infra/terraform/README.md
  - Line 267: the ECS row mentions the optional policy.
  - Lines 879-919: new section "Phase 15 P41". It covers the variables table, the policy, the env vars, the dashboard and the metric count.

DESIGN NOTES:
- **Policy count:** `count = var.enabled && var.image_revision != null && var.query_requests_per_target_target != null ? 1 : 0`.
  - The first two terms are exactly the count of `aws_lb.query` and `aws_lb_target_group.query`. So whenever the policy exists, `aws_lb.query[0]` and `aws_lb_target_group.query[0]` exist too.
  - With count 0 those references are never evaluated, so there is no index error. The tests cover image_revision=null, enabled=false and runtime_enabled=false.
  - The count expression is kept on one line containing "image_revision != null", because scripts/tests/test_runtime_base_apply.py derives the gating from the source text. That test passes.
- **Policy settings:**
  - Metric `ALBRequestCountPerTarget`.
  - `resource_label = "${aws_lb.query[0].arn_suffix}/${aws_lb_target_group.query[0].arn_suffix}"`.
  - Cooldowns: scale-in 300, scale-out 60. `disable_scale_in = false`.
  - The policy is on the query-api scalable target and is named `<prefix>-query-api-requests`.
- **Deviation, for the reviewer:** I added one precondition, `local.load_balanced_service == "query-api"`, which in practice means HTTPS is on. The work order's count rule is unchanged.
  - AWS documents that a ResourceLabel is accepted only when the target group is attached to the ECS service (PredefinedMetricSpecification.ResourceLabel; aws-knowledge search, 2026-11-16).
  - In this module the service is attached only with HTTPS. Without the precondition, a plan with the target set and no certificate would fail at apply instead of at plan.
  - A deployed runtime without a target and without HTTPS still plans as before (tested).
- **Two policies together:** AWS docs (target-tracking-scaling-policy-overview, "Multiple scaling policies", read 2026-11-16) confirm that it scales out when any policy asks and scales in only when all allow it. This is cited in a comment and in the README.
- **Dashboard panel:**
  - Title "ALB requests per target and target 4XX (query-api)", period 60, statistic Sum, position x0 y63, 24x6.
  - `RequestCountPerTarget` uses the TargetGroup dimension only.
  - `HTTPCode_Target_4XX_Count` uses LoadBalancer + TargetGroup. The ALB metrics doc lists no TargetGroup-only dimension set for it.
  - The null-ness of the dimensions depends only on the count, so it is known at plan time. The values themselves are known after apply, so the dashboard body is "known after apply" in the plan that creates the ALB.
- **Dashboard metric count before/after:** P9's 50-metric limit is not implemented or enforced anywhere at HEAD. F5 already notes the dashboard is "well over 50"; P9 is still pending. Counts by hand, confirmed by test assertions:
  - Before: 109 base metrics (12 task, 8 utilization, 2+1 SQS, 24 table, 3+3+3+3 publisher, 2 Step Functions, 6 conditional, 42 latency). 114 with Neptune; 120 with Neptune and EMR.
  - After: +2 when the ALB exists, so 116 with Neptune and 122 with everything.
  - I could not keep the dashboard "within 50" because it was already above 50. P41 adds only 2. The reduction belongs to P9.
- **Dropped:** a "runtime_enabled with image_revision=null" root run, because the root guard refuses that combination. The same case is covered at module level.

COMMANDS RUN:
All terraform calls went through a wrapper with the check.sh environment: `env -u AWS_PROFILE -u AWS_DEFAULT_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null TF_IN_AUTOMATION=1 TF_INPUT=0 CHECKPOINT_DISABLE=1 terraform ...`. Terraform v1.13.5, provider hashicorp/aws 6.44.0 (already installed). Commands ran in infra/terraform unless stated.

1. Baseline at HEAD, before any edit:
   - `terraform init -backend=false -input=false -lockfile=readonly`: rc 0.
   - `terraform test -no-color`: rc 0, "Success! 272 passed, 0 failed."
   - `terraform test -no-color -verbose`: rc 0. I extracted 42,633 (file, run, address) "will be created/read" lines.
2. After the changes:
   - `terraform fmt -check -recursive modules/runtime modules/observability tests`: rc 0.
   - `terraform fmt -check .` (root, non-recursive): rc 0.
   - `terraform init -backend=false -input=false -lockfile=readonly`: rc 0. It is needed so the new module test runs are registered.
   - `terraform validate`: rc 0, "Success! The configuration is valid."
   - `terraform test -no-color` (final, after all edits): rc 0, "Success! 301 passed, 0 failed." That is 272 existing plus 29 new.
3. `terraform test -no-color -verbose` after the change: rc 0, 301 passed. Comparing planned addresses of every pre-existing run with the baseline (`comm -3`) gives **0 differing lines**, so the default plan resource sets are unchanged.
4. `terraform test -no-color -verbose -filter=tests/phase14b_plan_deltas.tftest.hcl`, then `python3 -I scripts/lib/plan_deltas.py derive` on the baseline and changed logs: both rc 0, and the derivations are byte-identical (`cmp`). So scripts/config/expected-plan-deltas.json is unaffected.
5. Mutation check on a scratch copy outside the repo (state and *.local.tfvars excluded): 8 mutations, each killed by at least one P41 run.
   - M1: label order swapped.
   - M2: count ignores the target.
   - M3: scale-in disabled.
   - M4: precondition neutralised.
   - M5: burst gated on the rate.
   - M6: rate env added to every role.
   - M7: 4XX metric by TargetGroup only.
   - M8: scale-out cooldown 120.
6. Read-only Python checks:
   - `cd tests/infra && python3 -m unittest -v test_runtime_shape_14b` (offline env): "Ran 19 tests ... OK", rc 0. Run before and after the example and README edits.
   - `cd tests/infra && python3 -m unittest discover -p 'test_*.py'`: "Ran 465 tests in 869.693s OK", rc 0. This run started before the README and tfvars.example edits.
   - After those edits: `python3 -m unittest test_phase14b_grace test_w5b_w4_14b test_static_sources`: "Ran 88 tests OK", rc 0. Then `test_runtime_shape_14b` again: 19 OK.
   - `cd scripts/tests && python3 -m unittest test_runtime_base_apply test_plan_deltas`: "Ran 46 tests OK", rc 0.
7. The read-only pin recompute from scripts/billing/README.md: baseline stale=7, after stale=14.
8. aws-knowledge doc searches/reads only. No AWS API.

TEST RESULTS:
- terraform test (root): 301 passed, 0 failed. New P41 runs: 29 passed (18 root, 11 module).
- What the P41 runs assert:
  - The policy is absent by default.
  - It is absent with the target set but the runtime not deployed (root), with no image_revision (module) and with enabled=false (module).
  - It is present with the runtime deployed and the target set.
  - Label equals "app/synthetic/1234567890123456/targetgroup/synthetic/6543210987654321".
  - Metric ALBRequestCountPerTarget, no custom metric; cooldowns 300/60; disable_scale_in false; target value; query-api scalable target; policy name.
  - The CPU policies are 3 keys at target 60, ECSServiceAverageCPUUtilization, 300/60, in the default and the target-set runs.
  - Env is absent by default. Rate-only sets only PER_SECOND="250"; burst-only sets only BURST="500". Upper bounds render as "100000" and "1000000". Lower bound 1 is accepted. The values are on query-api only, never in `secrets`, and absent outside aws mode.
  - The precondition refuses a set target without HTTPS.
  - Refusals: target 0, 100001 and 1.5; rate 0, 100001 and 2.5; burst 0 and 1000001. The module also refuses a target of 1.5, rate 100001 and burst 1000001.
  - Dashboard: the panel is present with the ALB (exact metric arrays), absent without it, and there is no dashboard when dashboard_enabled=false. Total metrics are 116 with the ALB and 114 without.
- tests/infra full suite: 465 OK. test_runtime_shape_14b: 19 OK.
- scripts/tests (runtime_base_apply, plan_deltas): 46 OK.

VALIDATION RESULTS:
- fmt -check on the changed directories and root files: pass. validate: pass. Default planned address sets unchanged: 0 diff lines over 42,633. Plan deltas: identical.
- I did not run `scripts/check.sh`, as instructed. The coordinator runs it on a clean worktree.
- Deployer IAM was checked read-only, with no change needed:
  - deployer/phase14_main.tf lines 452-464 (`CloudWatchAlarmsDashboardsOfTheMainStack`: PutMetricAlarm/DeleteAlarms on `alarm:TargetTracking-*`, plus PutDashboard).
  - Lines 579-589 (`AppAutoScalingEcsServices`: PutScalingPolicy/DeleteScalingPolicy on `scalable-target/*`).
  - Lines 592-597 (DescribeScalingPolicies on `*`).
  - These are the same actions the live CPU policy used in Session 1. That they also cover the ALB-metric policy is not live-verified.
- Secret and account scan of the added lines: only the synthetic 111122223333, UUID tails and 16-digit mock suffixes. No secret, real account ID or e-mail. The tests/infra account scan passed inside the 465-test run.

ASSUMPTIONS:
- Units: the target is requests per target per minute (the ALB RequestCountPerTarget Sum over 60 s). The rate is per second, per API key, per query-api task. The burst is in requests.
- tostring() of whole numbers gives plain decimals (asserted for 1, 250, 500, 100000 and 1000000), which the service's `toLong` accepts.
- HTTPS is on in the Session 2 runtime plan (api_domain_name path), so the precondition does not bind there.

RISKS:
1. The plan that creates the ALB with dashboard_enabled=true shows the dashboard body as "known after apply", because it holds the ARN suffixes.
2. ALB RequestCountPerTarget and HTTPCode_Target_4XX_Count include 429 replies. This is noted in a code comment and the README; the plan's measurement rule already covers it.
3. The precondition is a small addition beyond the work-order text and needs reviewer acceptance.
4. The dashboard stays above 50 metrics until P9.
5. Test-engineer follow-ups, optional and not blocking because tests/infra passes unchanged:
   - tests/infra/test_runtime_shape_14b.py lines 64-71 pin the exact policy list only for module plans with the target unset. That list stays correct. It does not cover the new `aws_appautoscaling_policy.query_requests[0]` or the rate-limit env names.
   - tests/infra/runtime_shape_checks.py line 31 `ROOT_VARIABLE_FILES = ("phase12b-variables.tf", "variables.tf")` does not read the new phase15-variables.tf.
   - Owner: test-engineer (tests/infra/**), if independent coverage is wanted.

MANUAL ACTION REQUIRED:
- The human refreshes the pins after review, at the commit, recomputing them rather than copying from here. In scripts/billing/reviewed-pins.json `source_freeze`, P41 newly made these stale:
  - infra/terraform/README.md
  - infra/terraform/main.tf
  - infra/terraform/phase12b.tf
  - infra/terraform/modules/observability/main.tf
  - infra/terraform/modules/observability/variables.tf
  - infra/terraform/modules/runtime/outputs.tf
  - infra/terraform/modules/runtime/variables.tf
  - infra/terraform/modules/runtime/compute.tf (already stale at HEAD, changed again)
- Already stale at HEAD and not touched by P41: billing-bootstrap/README.md, main.tf, tests/budget.tftest.hcl; modules/workflow/main.tf; tests/infra/README.md; tests/infra/terraform_source_guard.py.
- Totals: 14 stale now, 7 at baseline. New files phase15-variables.tf and the two tftest files are not in the pin list.
- The P15 pins refresh and the P35 values follow per the plan. The new test runs need `terraform init -backend=false` once to register their modules.

BLOCKED-ON OWNER: none.

BLOCKED-ON EVIDENCE: none.

NEXT GATE: An independent code-reviewer review of the P41 diff, including the precondition deviation and the dashboard count note. Then the coordinator runs `scripts/check.sh` on a clean worktree. Then the user's "Yes, commit" (no commit, stash or review was done here). After that, the human pin refresh. Apply happens only in Session 2 under the recorded human gate.
````

### documentation-engineer reports (P41-D and two follow-ups)

The documentation-engineer's three final reports are summarised here; their full text is in this session's transcript. The plan draft is untracked and not part of the P41 commit.
- **P41-D:**
  - Recorded the P41 defaults in row P41.
  - Reworded section 5.3 step 2 to use the root variables.
  - Fixed R3: `SemanticApi.scala` embed call at line 98, `vectors.query` at line 100, both re-read at `cceb1f5`.
  - Added the R2 open item to rows P35 and P42 and to section 5.3 step 4, and removed the cache counters from the step 4 collection list.
  - Added a dated amendment-log entry and a section 10 provenance entry.
  - Checks: link check 20 links, 0 broken; ID and e-mail scan 0 matches.
- **Follow-up 1:**
  - R2 decided by the user's answer (a): the Voyage usage page, read by the human after the session with the read time.
  - Row P35 item (5) now names the root variables.
  - The section 10 entry is kept and extended.
  - Checks: 20 links, 0 broken; 0 ID or e-mail matches.
- **Follow-up 2:**
  - R2 uses the R-b load window only, with the section 6.3a caveats (up to about 4 × distinct questions from task starts, plus a few duplicate calls from a cold task); otherwise the figure is "unverified".
  - Changed lines 28, 243, 250, 362-365 and 864.
  - Checks: 20 links, 0 broken; 0 ID or e-mail matches. No new questions raised.

### infra-engineer repair 1 report (2026-11-16, verbatim; coordinator gate G1, see `repairs.md`)

````text
STATUS: COMPLETE. P41 repair 1 is fixed: the 7 `test_terraform_r1.RouteOwnershipTest` failures no longer occur. I took your preferred option and moved the three variable blocks into an existing root file. I did not touch scripts/** or any file the pipeline lanes are editing.

**Cause, confirmed.** `scripts/tests/test_terraform_r1.py` `build_fixture()` (lines 57-67) copies only the files `git ls-files infra/terraform` lists. The new root file was untracked, so it was left out of the fixture, and `main.tf` lines 140-142 then referred to variables that did not exist there.

**Files changed:**
- `/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/phase12b-variables.tf`, lines 430-464 (new): the three variable blocks and their header comment, appended unchanged from `phase15-variables.tf`.
- `/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform/phase15-variables.tf`: deleted.
- Reference updates, one line each, same line counts:
  - `infra/terraform/README.md` line 883 now points to `phase12b-variables.tf` (end of file).
  - `infra/terraform/tests/phase15_p41.tftest.hcl` line 4.
  - `infra/terraform/modules/runtime/variables.tf` line 180.
- No other file changed. The P41 file list is otherwise as in my first report.

**Commands** (all with the offline AWS env through a wrapper):

| Command | Exit | Result |
|---|---|---|
| `terraform fmt -check -recursive modules/runtime modules/observability tests` | 0 | pass |
| `terraform fmt -check .` (root) | 0 | pass |
| `terraform init -backend=false -input=false -lockfile=readonly` | 0 | — |
| `terraform validate` | 0 | "Success! The configuration is valid." |
| `terraform test -no-color` | 0 | "Success! 304 passed, 0 failed." |
| `cd scripts/tests && python3 -I -m unittest discover -s . -p 'test_terraform_*.py'` | 0 | 17 tests OK |
| same, `-p test_terraform_r1.py -v` | 0 | 10 tests OK, all 4 RouteOwnershipTest cases ok, none skipped |
| `python3 -I -m unittest discover -s . -p 'test_runtime_base_apply.py'` | 0 | 31 tests OK |
| `cd tests/infra && python3 -I -m unittest test_runtime_shape_14b` | 1 | import error, see below |
| `cd tests/infra && python3 -I -m unittest discover -s . -p 'test_runtime_shape_14b.py'` | 0 | 19 tests OK |

- **304 instead of the expected 301:** 272 existing + 18 + 11 P41 runs + 3 runs from `tests/phase15_stagea.tftest.hcl`. That file belongs to another lane and is untracked; I did not touch it.
- **Shape test import error:** `-I` removes the current directory from `sys.path`, so the module cannot be imported. That comes from the command form, not the code; the `discover` form above is the working equivalent.

**Other fixed root-file lists in scripts/tests and tests/\*\*:**
- `tests/infra/runtime_shape_checks.py:31` `ROOT_VARIABLE_FILES = ("phase12b-variables.tf", "variables.tf")`. A new root variables file would be invisible to it. The move fixes this for P41 and closes my earlier RISKS item.
- `scripts/tests/test_providers.py:150-151,163` read `phase14b-variables.tf`, `phase14b-providers.tf` and `phase12b-variables.tf` by name. These are content checks, not fixtures; a new file does not break them.
- `scripts/tests/test_terraform_r1.py:57-67` (tracked files only). Any new untracked root `.tf` that `main.tf` references breaks it until the file is committed. My untracked `tests/phase15_p41*.tftest.hcl` are harmless there, because r1 runs only `-filter=tests/phase12b.tftest.hcl`.
- `tests/infra/test_guard_phase14.py:78` uses ls-files including untracked files, so new files are safe.
- `tests/scripts/sc_support.py:458-463` copies only `environments/course.tfvars`, `modules/runtime/compute.tf` and a stub `versions.tf`. It does not depend on root variables.
- The rest are synthetic wrappers or other roots that do not read the main root's files, so they are unaffected: `tests/infra/infra_support.py:547-553`, `runtime_shape_checks.py:149-159`, `test_phase14b_grace.py` (fixtures it writes itself), and `test_billing_replan_14b.py:121` (billing-bootstrap root only).

**Pins:** `infra/terraform/phase12b-variables.tf` (reviewed-pins.json `source_freeze`, about line 435) is now also stale. It is added to the list of pins the human refreshes after review.

**Next gate:** the coordinator reruns `scripts/check.sh --skip sbt` on a clean snapshot, then code review. Nothing was committed, stashed or run with check.sh.
````

## Pipeline bundle (Session 2 prerequisites): agent reports, verbatim (2026-11-16)

Assembled by the coordinator from the agents' hand-back reports, in arrival order. The lanes were relaunched after the 23:17 CST interrupt (prompt.md "Relaunch, Neptune and P34 decisions"). Agent IDs are truncated. Earlier interrupted runs left no reports.

#### Agent report (2026-11-16T14:47:39.835Z, agent ac56b40)

**STATUS:** DONE (P21 lane D). The pinned DBLP archive was downloaded once and its SHA-256 matches the pin. The L slice is built: 48,187 works. The S ⊂ L check passed. Nothing was committed.

**OWNER:** dataset-engineer

**WORK ORDER:** Phase 15 P21 lane D relaunch (brief lane-D.txt plus the 2026-11-16 08:40 CST updates). Download approved by the human (prompt.md line 131).

**FILES CREATED** (all untracked, under datasets/** only)
- /Users/danny/Documents/UIC/CS441/ScholarChain/datasets/phase15/dblp-l-slice-manifest.v1.json — **this is the slice manifest for lane C**. sha256 ba16cf9eb42218932b4a6aa1ab7ecc64e88c6937d655c64d456f1c97471c297f
- /Users/danny/Documents/UIC/CS441/ScholarChain/datasets/phase15/SHA256SUMS — holds the archive and L XML checksums, with paths relative to the repo root
- The two drafts are now reviewed and kept: /Users/danny/Documents/UIC/CS441/ScholarChain/datasets/scripts/phase15/select_dblp_l_slice.py (sha256 627188900f3809b949c21aa53b7425f1c5319fe51c985aeb0b78d4e7a030c58f, the same value recorded in the manifest) and /Users/danny/Documents/UIC/CS441/ScholarChain/datasets/scripts/phase15/test_dblp_l_slice.py (874ab943e140fdcda93e301071593dfbc1cea6aea6c698f99fc7abc6a56425b2)
- Git-ignored files under target/, following the S convention (slice XML and archive stay out of git):
  - target/phase15-inputs/dblp-archive/dblp-2026-10-03.xml.gz
  - target/phase15-inputs/dblp-archive-acquisition-receipt.v1.json
  - target/phase15-inputs/dblp-l/dblp.xml
  - target/phase15/lanes/lane-D-progress.md, lane-D-curl-*.txt, lane-D-slice/ (logs and replay)

**FILES MODIFIED:** None that are tracked.
- Fixes to the drafts:
  - The `--acquisition-receipt` help text was wrong: a Phase 6 manifest's retrieval is a local copy and would fail the check.
  - The receipt is now checked by a new `load_receipt()` before the scan. It checks the URL, the byte count and the optional sha256 against the pin.
  - A no-op test line was removed.
  - Two tests were added. One shows that a failed nesting check writes neither the output nor the manifest. The other shows that the receipt is rejected before any scan.

**COMMANDS RUN** (from the repo root)
1. Read-only search for the archive in target/ and datasets/. The complete archive was not there. I did find an **unexplained partial file**: target/phase6-inputs/6fg-dblp/dblp-2026-10-03.xml.gz.partial, 882,900,992 bytes, written 2026-11-15 23:15:31–23:17:01 CST.
   - Its start time matches target/phase15-inputs/dblp-s-replay/started-utc.txt (2026-11-16T05:15:30Z), whose logs are empty.
   - It appears to come from a Phase 6 downloader run before the download was approved.
   - I did not use, resume or delete it.
2. `git check-ignore -v` on the target paths: all ignored by .gitignore:2 `target/`.
3. Draft tests as found: exit 0, 11 tests OK.
4. The first curl call never ran: zsh expanded the unquoted `=https` ("https not found", exit 1). No network bytes were sent.
5. The one real download:
   `/usr/bin/curl --fail --silent --show-error --proto '=https' --max-redirs 0 --max-time 1800 --max-filesize 1342177280 -H 'Accept-Encoding: identity' -o target/phase15-inputs/dblp-archive/dblp-2026-10-03.xml.gz.curl-partial -w '...' https://drops.dagstuhl.de/storage/artifacts/dblp/xml/2026/dblp-2026-10-03.xml.gz`
   - Result: exit 0, `200 1107081001 181.115080 0 <same URL>`, stderr empty.
   - The URL is the pin from datasets/phase6/dblp-slice-manifest.v1.json.
6. Verification:
   - `stat`: 1107081001 bytes (matches the pin)
   - `shasum -a 256`: 20e45961bec5610dc07b8e932ccd27a2387534cfa12c92a24289fe873aebe969 (**matches the pin**)
   - `md5 -q`: cbd329100ea1bbb2873fa2f6d414ea00 (matches the pin)
   - After verification, `mv -n` renamed the file to dblp-2026-10-03.xml.gz.
7. Slice build: `python3 -I datasets/scripts/phase15/select_dblp_l_slice.py --archive target/phase15-inputs/dblp-archive/dblp-2026-10-03.xml.gz --s-manifest datasets/phase6/dblp-slice-manifest.v1.json --s-xml target/phase6-inputs/6fg-dblp/dblp.xml --output target/phase15-inputs/dblp-l/dblp.xml --manifest datasets/phase15/dblp-l-slice-manifest.v1.json --acquisition-receipt target/phase15-inputs/dblp-archive-acquisition-receipt.v1.json` gave exit 0 in 11 s, stderr empty.
8. Replay into target/phase15/lanes/lane-D-slice/replay.xml gave exit 0. `cmp` found the bytes identical, and the selection and nestingCheck blocks are equal.
9. Separate ElementTree check: L has 48,187 unique keys and S (10,577) ⊂ L. 37,610 keys are only in L.
10. `shasum -a 256 -c datasets/phase15/SHA256SUMS`: both lines OK.

**TEST RESULTS**
- `python3 -I -m unittest discover -s datasets/scripts/phase15 -p 'test_*.py' -v`: **Ran 13, OK**, exit 0
- `python3 -I -m unittest discover -s datasets/scripts -p 'test_*.py'`: Ran 97, OK, exit 0
- Phase 6 discover: Ran 12, OK, exit 0

**VALIDATION RESULTS**
- **L slice:**
  - publicationCount 48,187; distinct exact author strings 76,623
  - XML is 27,964,881 bytes, sha256 7e62bb428a6ef34dd7961f337b6a2d42978d7c2cbf1c566c7ce83eac3b21ea34, md5 830cbe3dc5f63b50181c2fa34d6baef3
  - selectedKeysSha256 1c64baef85228e51e03af305954be099a6f77756aaa31eb8ced121cf6eaf249c
  - observedInproceedings 3,980,085, the same as S
  - Largest author list 79; 210 works have more than 16 authors and 17 have more than 32
- **Venue rule:**
  - The 8 S venues, then the longest prefix of 31 ranked candidates that keeps the total at or below 50,000 (minimum 45,000).
  - Same as S: cap 2,500 per venue, years 2005–2026, inproceedings only, archive source order.
  - 25 candidates were included. The list stopped at sigmod (2,500), which would have pushed the total over 50,000.
- **Per venue:**
  - S venues: podc 1538, disc 1058, icdcs 2500, osdi 662, sosp 666, nsdi 1257, eurosys 1329, middleware 1567
  - Added venues: usenix 1190, fast 592, socc 747, hotos 309, asplos 1667, opodis 695, spaa 1074, sss 705, sirocco 567, srds 827, dsn 2310, hpdc 1312, ppopp 1245, cluster 1685, ccgrid 2497, icpp 1834, europar 2500, ipdps 2500, sc 2500, sigcomm 2500, conext 1360, imc 1044, sigmetrics 1199, infocom 2500, mobisys 2251
- **S ⊂ L check: PASS.**
  - S rebuilt from L has 10,577 records with sha256 c25a1e1a0d517abaadf370c88b3528039c50ad8ec3790c27381a3c2e2ecde522 and keys sha 20661b72d3b3f660dbd1ad9fc06dcaa3d5e832f3c3a942b4700fe3d3d9e9add9. Both equal the committed S manifest.
  - The S XML file has 10,577 keys and none are missing from L. L is a strict superset.
- **License:** the manifest records CC0 1.0 (DBLP), with the evidence URL and the receipt embedded.
- **Sample checksums:** `(cd datasets && shasum -a 256 -c samples/SHA256SUMS)` gave 4 OK.
- **`python3 -I datasets/scripts/validate_datasets.py`: exit 1, "PyYAML is required". This gate is UNVERIFIED.** I did not install PyYAML because the download was the only network call allowed. dataset-manifest.yaml is unchanged.

**ASSUMPTIONS**
- The archive went into a new empty directory (target/phase15-inputs/dblp-archive/), not the Phase 6 default path, so it stays apart from the unexplained partial.
- "Checksum" in the approval means datasets/phase15/SHA256SUMS.
- The receipt stays in target/ and is embedded in the manifest's archiveAcquisitionReceipt.
- I added no README.

**RISKS**
- The 883 MB partial looks like a network transfer from before approval. Its cause is unconfirmed. It is still on disk, and I have not deleted it.
- The manifest's createdAt and paths are observational. The XML bytes and key hashes are deterministic.
- This is a convenience slice, biased by the venue ranking, per-venue cap and source order.

**MANUAL ACTION REQUIRED**
- Human decisions:
  1. Explain the unapproved partial download.
  2. Decide whether to delete the partial file. Deleting it is a destructive action, so it needs the human.
- Review the slice and run the validate_datasets.py gate where PyYAML is available.
- Commit when approved: the manifest, SHA256SUMS and the two phase15 scripts.

**BLOCKED-ON OWNER:** None for lane D. Lane C (experiment-engineer) builds the L input tree from datasets/phase15/dblp-l-slice-manifest.v1.json, using target/phase15-inputs/dblp-l/dblp.xml.

**BLOCKED-ON EVIDENCE:** None.

**NEXT GATE:** Independent code review of the script, tests and manifest. Manifest and license review by the human. The validate_datasets.py run is still pending.

#### Agent report (2026-11-16T14:53:56.391Z, agent af8f024)

STATUS: DONE. P26a, P26b and P38 (rag part) are implemented and the rag gate passed (exit 0, 245 of 245 tests). There is one code-level finding for P26a: the live tools had a hard 16 MiB manifest cap in code, and about 10,000 items do not fit in it. Raising config alone would not have been enough; this change raises that code cap to 64 MiB, so the human can now set 32 MiB in config.

OWNER: rag-engineer (Lane E relaunch, Phase 15)

WORK ORDER: Lane E brief at /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/briefs/lane-E.txt, with the 2026-11-16 08:40 CST updates and the coordinator's P38 note about storage `ToolLogging`. Items: P26 (a) limits, P26 (b) batching with a fake throughput figure, P38 rag tool logging. Base was HEAD 7a02de2.

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LookaheadBatchingEmbeddingClient.scala
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Phase15VectorScaleSpec.scala (5 tests, P26a)
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Phase15IngestBatchingSpec.scala (12 tests: 9 for P26b, 3 for P38)

FILES MODIFIED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingIngestMain.scala:
  - New constant `LiveEmbeddingConfig.MaxManifestBytesCeiling` = 64 MiB. It replaces the hard 16 MiB in the config check and in the manifest file read; the 16 MiB default is kept.
  - `batchingEmbedder` wraps the ports' embedder inside `run()`. `report()` gets an optional `embeddingBatch` counters object.
  - `ToolLogging.install()` is now the first statement of `main`.
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingSmokeMain.scala: manifest read uses the same ceiling; `ToolLogging.install()` first in `main`.
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/EmbeddingManifestMain.scala: the render report gains `sizeEvidence` {manifestBytes, maxManifestBytes, maxManifestItems, textBytesTotal, textBytesMax}; `ToolLogging.install()` first in `main`.
- Progress log (git-ignored): /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/lane-E-progress.md

COMMANDS RUN (each with `export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; export PATH="$JAVA_HOME/bin:$PATH"; export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"`; sbt reported Java 17.0.20.1):
1. `sbt -batch "rag/testOnly edu.uic.cs441.scholarchain.rag.Phase15VectorScaleSpec"`, several iterations:
   - with a 16 MiB limit: exit 1, `manifest-byte-limit`
   - measuring with a 64 MiB limit: exit 1 on the 16 MiB assertion; the 20,531,758 B figure comes from this run
   - final: exit 0, 5/5 passed
2. `sbt -batch "rag/testOnly edu.uic.cs441.scholarchain.rag.Phase15IngestBatchingSpec"`: exit 0, 12/12 passed.
3. `sbt -batch "rag/scalafmtCheck" "rag/Test/scalafmtCheck" "rag/test"`, first attempt: exit 1. Two files were not formatted (EmbeddingManifestMain.scala, LookaheadBatchingEmbeddingClient.scala).
4. `sbt -batch "rag/scalafmt" "rag/Test/scalafmt"`: success; 2 files reformatted.
5. `sbt -batch "rag/scalafmtCheck" "rag/Test/scalafmtCheck" "rag/test"`: exit 0; Total 245, Suites 20, succeeded 245, failed 0. Log: /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/laneE-gate.log
- No background commands are running.

TEST RESULTS: rag 245/245 passed (step 5). New suites: Phase15VectorScaleSpec 5/5, Phase15IngestBatchingSpec 12/12. The full `sbt check` was not run, as the brief says (the coordinator runs it).

VALIDATION RESULTS:

P26a limits table:

| Limit | Value | Where it applies |
|---|---|---|
| maxManifestItems | default 10,000 | render config; EmbeddingIngestConfig; live = maxVectors; approval vectorCap |
| maxManifestBytes | default 16 MiB | no code cap in render/local; live code cap was a hard 16 MiB, now 64 MiB |
| maxTextBytes | 1 MiB per item | ingest |
| chunk policy | chunkMaxCharacters 1000, overlap 100, chunkMaxCount 1000 | phase-08 template |
| maxDocumentCharacters | 1,000,000 | render |
| maxScannedRows | default 200,000 | source scan (Session 1 S had 100,769 rows) |
| maxSummaries / maxTopicNodes / maxInstitutionNodes | defaults 100 / 10 / 10 | selection |
| config file size | ≤ 65,536 B | both tools |
| Voyage request | 1,000 texts and 1,000,000 tokens per request; 32,000 tokens per text | ProviderDefaults.scala:44-50, "docs 2026-11-09" |

- Measured on synthetic data shaped like the Phase 6 producer (9,996 summaries plus 4 nodes, giving 10,000 items):
  - manifest is 20,531,758 B, about 2,053 B per item: path 1,837, community 2,148, paper 1,514, researcher 2,709, topic/institution 1,656
  - text is 1,235,746 B in total, 123 B on average (Session 1's real average was 112 B), 180 B at most
  - a worst-case 900-character paper title gives a 2,324 B item, still one chunk
  - the 16 MiB default refuses this manifest with `manifest-byte-limit`; 32 MiB fits
  - one item over 10,000 is refused with `render-document-count-bound`
- Answer to "is config enough?": for the render step, yes. For the live tools, no — the code cap had to change.

Keys the human must set in the private render config: `maxSummaries: 9996`, `maxTopicNodes: 10`, `maxInstitutionNodes: 10` (only 4 nodes exist), `maxScannedRows: 200000`, `maxManifestItems: 10000`, `maxManifestBytes: 33554432`.
- Expected split: about 2,499 per summary type plus 4 topic/institution, if each type has at least 2,499 rows. The round robin fills from the other types otherwise.
- If the real chunking gives more than one chunk per summary, lower `maxSummaries`.

Keys in the live config and approval:
- live config: `maxVectors: 10000`, `maxManifestBytes: 33554432`, `maxEmbeddingCalls` ≥ 20000 (at 2 attempts), `dollarCapUsd` ≥ 0.23 (template per-attempt 1e-5 gives 0.20 + 0.01 + 0.02), `batchSize` (see P26b)
- approval: `vectorCap` ≥ 10000, `embeddingCallCap` ≥ 20000, `dollarCapUsd` ≥ the config's
- The token bound is about 10,000 × 123 × 2 = 2.5M tokens, about USD 0.05, under the 0.30 embedding cap.

P26b batching:
- The per-item call `embedder.embed(Seq(text))` is in the storage runner (modules/storage/.../EmbeddingManifest.scala, EmbeddingManifestRunner), which is not mine to edit. So batching is a rag decorator wired into `LiveEmbeddingIngestMain.run`.
  - When asked for a text it has not sent yet, it sends that text plus the next unsent manifest texts in one call, up to `batchSize` in total.
  - Each distinct text is sent at most once; results come back exactly as the provider returned them.
- Retry and backoff are unchanged, and the Voyage client still splits by its 1,000-text and 1M-token limits. The P40 query cache was not touched.
- The batch size is the existing `batchSize` config key (1..500, default 100), which is also the S3 Vectors put size.
- Measured with fakes only (in-memory storage, fake embedder):
  - 10 ms per call, 500 items: batchSize 1 gives 65.8 / 64.8 v/s (500 calls); batchSize 100 gives 2086.2 / 2470.0 v/s (5 calls)
  - zero latency, 10,000 items, batchSize 100: 4090.2 / 4259.2 v/s (100 calls)

P38:
- The three rag mains call storage's `ToolLogging.install()` first, which selects `scholarchain/tools-logback.xml` (root INFO; org.apache.http, org.apache.hc, software.amazon.awssdk and io.netty at WARN). No rag logback resource was added, so nothing clashes with services' `logback.xml`. An operator-set `logback.configurationFile` still wins.
- Tests:
  - all three mains install the config, and an operator override is kept
  - an ingest run against fakes that emit DEBUG wire and token lines logs its INFO `embedding_ingest` event, with 0 events below INFO, 0 wire-logger events and 0 token strings
  - control: under logback's DEBUG default the same run does emit those lines

ASSUMPTIONS:
- The synthetic summaries copy the Phase 6 producer's templates, reference counts and ID formats (modules/spark Phase6FGJobs). The byte figures are estimates; the human's render-only run on the real export, using the new `sizeEvidence`, is the real check.
- I did not add a separate config key for the embedding batch size. Adding a field to `LiveEmbeddingConfig` fails to compile (Scala 3 limit on derived JSON readers for large case classes), so I reused `batchSize`.
- P38 depends on the storage-engineer's uncommitted `ToolLogging` and resource (modules/storage). This rag change has to be committed with or after that storage patch.

RISKS:
- Live throughput is unverified. Session 1's 1.63 s per vector includes about 8 sequential S3/DynamoDB calls per item inside the storage runner; batching removes only the Voyage round trip per item. Going much faster needs storage-runner concurrency, which is not in this lane.
- Batching changes the failure size and the request size:
  - a 429 or 5xx after retries now rejects a whole batch (up to `batchSize` items, recorded as rejected; a fresh run re-embeds them)
  - each request is about 12K tokens at batchSize 100. At a free-trial tokens-per-minute limit that may be refused, so the P26 (c) tier check must come first; `batchSize` can be lowered.
- Existing configs that keep `batchSize: 100` now batch embeddings without anyone editing them.
- In the report, `embeddingCalls` remains the per-item attempt sum. The real number of requests is `embeddingBatch.underlyingCalls`.
- If items were already completed by an earlier run, texts embedded ahead for them are wasted (reported as `unusedPrefetched`); the cost is bounded by one pass over the manifest.

MANUAL ACTION REQUIRED:
- Human: set the render-config and live-config/approval keys listed above.
- Human: do the P26 (c) Voyage tier check before a batched live ingest.
- Human: a render-only run on S, then check `sizeEvidence.manifestBytes` ≤ maxManifestBytes and `selectedDocuments` about 10,000.

BLOCKED-ON OWNER: none blocking. Optional, storage-engineer: concurrency or batching inside `EmbeddingManifestRunner` (modules/storage) for faster live ingest.

BLOCKED-ON EVIDENCE: P38 relies on the uncommitted storage files (modules/storage/src/main/scala/.../ToolLogging.scala, modules/storage/src/main/resources/scholarchain/tools-logback.xml). Live throughput and real manifest bytes are unverified.

NEXT GATE: coordinator runs `sbt check` (with the storage P38 patch present), then an independent code-reviewer, then the human's render-only P26 run with the keys above, then the rag commit after the storage P38 commit.

#### Agent report (2026-11-16T14:55:14.745Z, agent ab94ba7)

STATUS: DONE. All four items are finished inside `experiments/**`. `check_manifests.py --final` returns `RESULT: OK` (exit 0) against the current working tree, but only because lane A's uncommitted `release.conf` pins are in place. Against HEAD `release.conf` it returns exit 3, blocked on the P25 ledger. Nothing is committed. No AWS, network or sbt use.

OWNER: experiment-engineer (lane C, relaunch)

WORK ORDER: Phase 15, session-2 plan items P24, P1 (manifest side), P22 (prep-config side) and P21 (preparation). Brief: `.../scratchpad/briefs/lane-C.txt` plus the 08:40 CST updates. Branch phase-15, HEAD 7a02de2.

FILES CREATED:
- `/Users/danny/Documents/UIC/CS441/ScholarChain/experiments/inputs/15a/spark-emr-template.json` (sha256 `9341c162c8b05c9496685083d5a470a77f555ee24626eb4b946a439e1fd8206a`)
- `/Users/danny/Documents/UIC/CS441/ScholarChain/experiments/manifests/15a-emr-size-l.json` (sha256 `beb951e8de832dde29f5e1a9e51a1e41a0247ce2b698849e3571dc208d8ead3b`)
- `/Users/danny/Documents/UIC/CS441/ScholarChain/experiments/scripts/build_l_input.py`

FILES MODIFIED (all under `/Users/danny/Documents/UIC/CS441/ScholarChain/experiments/`):
- `inputs/15a/prep-config.json`: `maxLocalSampleRecords` 12000 -> 60000; sha256 `5330214bda284c4152a700549942b40931a64994b82b19ecdd99bcadb9f1bc57`
- `inputs/15a/config-sources.json`: adds `hadoop-config`; `spark-config-template` now points to the new template
- `manifests/15a-emr-size-{25,50,100}.json`: re-rendered with the `hadoop_config` S3 URI, a `hadoop-config` sha pin, the new template pin and new descriptions. The JAR hashes are kept as they were.
- `scripts/render_manifests.py`: renders 4 runs; hashes the 4 config files itself and refuses a `--sha` that differs from the file; adds `--keep-jar-shas` and `--l-slice-manifest`; writes PLACEHOLDER-L-* markers when the L slice is absent
- `scripts/check_manifests.py`:
  - requires the S and L manifests and the config URI form;
  - each config sha must equal its file, and `config-sources.json` must not drift;
  - `maxLocalSampleRecords` must be at least the L count plus 3;
  - the L description must state the L slice's count and sha;
  - `--final` refuses the PLACEHOLDER-L-* markers;
  - a ledger overrun is now CHECK-BLOCKED (exit 3) instead of FAILED.
- `scripts/make_dblp_subsets.py`: adds `--tree-label` (one size only) and a `tree_label` field in the subset JSON
- `tests/test_experiments.py`, `tests/test_derive_14c_inputs.py`: updated, plus 15 new tests
- `README.md`: new Session 2 S/L section, the P22 derivation, the P24 justification, the config key table and the freeze command

COMMANDS RUN (all from the repository root):
1. Baseline before any edit: `python3 -I experiments/scripts/check_manifests.py` exit 0; the same with `--final` exit 0; `python3 -I -m unittest discover -s experiments/tests` exit 0, 51 tests OK.
2. `python3 -I experiments/scripts/render_manifests.py --overwrite --keep-jar-shas` exit 0.
3. `python3 -I experiments/scripts/build_l_input.py --output-root target/phase15/lanes/lane-C-l-input-check` exit 0. Output: `L-TREE ... publications=48187 authorships=203584 distinct_author_strings=76623 dblp_sha256=7e62bb42...ea34 identical_to_slice=True` and `L-NESTING PASS (10577 S keys, all in the 48187 size-l keys)`. Re-rendering left the 4 manifests byte-identical (`shasum -c` OK). Total input is 28,014,514 bytes, under the 256 MiB limit. I did not create the default tree `target/experiment-inputs/15a/size-l`.
4. Read-only analysis of the local event-log summaries for runs f6e63b4b and f02acf56, and of the S and L XML volumes.
5. Mid-run, with HEAD's ledger pins: `check_manifests.py` exit 3, the only finding was the CHECK-BLOCKED ledger line (3.36 USD / 4 runs vs 2.52 / 3). A scratch-root run with P25 pins, `check_manifests.py --final --root <scratch>`, gave exit 0.
6. Final: `python3 -I -m unittest discover -s experiments/tests` exit 0, `Ran 66 tests ... OK`; `check_manifests.py --final` exit 0, `RESULT: OK (final: no placeholders)`; normal mode exit 0. Key lines:
   - `15A total 3.36 USD over 4 runs <= cumulative cap 3.36 USD / 4 runs`
   - `maxLocalSampleRecords=60000 >= 48190 = the L slice manifest publicationCount 48187 + 3 other-source records`
   - `15a-emr-size-l.json states the L slice (48,187 publications, sha256 7e62bb428a6e...)`

TEST RESULTS: 66/66 pass (43 + 23). The new tests cover:
- config-sha refusal in both render and check;
- the `hadoop_config` URI form;
- config file drift;
- the L slice binding the description and the sample bound;
- an L slice whose nesting check did not pass;
- the S and L manifests being required;
- `--keep-jar-shas`;
- the template differing from Phase 6 only in the shuffle partitions and the 4 path keys, with the Phase 6 file's sha unchanged;
- the template's field set matching the core contract `scholarchain.spark-analytics-config.v1.json`;
- `scripts/emr/sc-render-spark-config.py` rendering the template;
- the one-command L build end to end (synthetic data), its refusals, and `--tree-label` validation.

VALIDATION RESULTS:
- **Spark settings for the spark-engineer (P24):** one template, `spark-emr-template.json`, for both S and L. It equals the accepted 14C export config (`target/phase6-inputs/14c-runtime/spark-export.json`, sha256 `ee27421d...c1e1`) in every key except the 4 path keys, which hold `/replaced-at-run-time/<key>`. Settings to confirm:
  - `shufflePartitions` 64 for both sizes;
  - `checkpointInterval` 5;
  - `componentMaxIterations` 50, `communityMaxIterations` 20, `kCoreMaxIterations` 50;
  - `maxHops` 6, `sampledPathPairCount` 20, `pathSampleSourceCount` 32, `samplingSeed` 441;
  - `representativeWorkLimit` 5, `maxTeamWorkLimit` 20, `failOnHardInvariant` true;
  - the 6 windows unchanged.
- **Why L also uses 64:**
  - **Executors:** `spark-12-10.conf` gives 1-core, 3g executors, and `PIPELINE_MAX_EXECUTORS_PER_NODE=2` with 1 core node means 2 task slots.
  - **Data volume:** the largest S shuffle read was 865,231,386 bytes (at most 60.6 MB per task after AQE). L/S is 4.66x in bytes, so about 4.03 GB, or about 63 MB per partition at 64, under AQE's 64 MiB target. With 4 partitions that would be about 1 GB per task.
  - **Task overhead:** S at 64 partitions ran 27,344 tasks, 320 of 2,024 stages kept all 64 tasks, and summed stage time was 517 s against 277 s at 4 partitions. This overhead grows with the partition count, not the data. The Spark step gets only 36 of the 90 minutes, so scaling the value with size (about 300) would add tens of thousands of tasks on 2 slots.
  - **Loader cap:** sidecar parts are `ceil(bytes / 8 MiB)` (Phase7NeptuneExport, 16 MiB hard limit), which does not depend on `shufflePartitions`.
  - **Comparability:** S and L differ only in their data.
- **maxLocalSampleRecords = 60000.** SampleBound is one record budget per Hadoop job. The worst case is L at most 50,000 (lane D's `TARGET_MAX`; 48,187 actual) plus 3 one-line committed samples (openalex, crossref and orcid each have 1 non-blank line), which is 50,003, rounded up to 60,000. Lane A's `release.conf` now shows `PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS=60000`, so the two values match.
- **What lane A must match:**
  1. Upload key `config/hadoop-config.json` for `--hadoop-config FILE`. The manifest URI is `s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/config/hadoop-config.json` and the sha pin name is `hadoop-config`. The EMR-RENDER name should be `hadoop-config`. As of my last check, no such option exists in `scripts/` yet.
  2. The Spark template key is unchanged (`config/spark-config-template.json`); pass `experiments/inputs/15a/spark-emr-template.json` as the file.
  3. Input label `size-l` (fits LABEL_RE); with S that makes 2 input datasets.
  4. Ledger pins `EMR_MAX_LIVE_RUNS=4` and `EMR_CUMULATIVE_CAP_USD=3.36`, which are present now but uncommitted.
- **L values used:** filled from `datasets/phase15/dblp-l-slice-manifest.v1.json` (sha256 `ba16cf9e...297f`, lane D, uncommitted): 48,187 works, slice sha256 `7e62bb428a6ef34dd7961f337b6a2d42978d7c2cbf1c566c7ce83eac3b21ea34`.

ASSUMPTIONS:
- The L manifest is named `15a-emr-size-l` (a stable label instead of `<L>`), and S is the existing `15a-emr-size-100`.
- The size-25 and size-50 manifests stay. With them, the 4 manifests total 3.36 USD, which equals the P25 ledger (2 Session 1 runs plus S and L).
- AQE coalescing being active is shown by the 14B evidence (64 partitions -> 2-3 parts) and the S event log. The EMR runtime keeps the Spark 3.5 default `spark.sql.adaptive.enabled=true` because `spark-12-10.conf` does not set it. I have not observed this on EMR.
- The other three sources stay unscaled, as briefed.

RISKS:
- The L Spark step has 36 minutes (40% of 90); its time is unmeasured until P6 at L.
- Components and k-core use `require` and fail the run after 50 iterations; S needed 17 and 16, and L's diameter is unknown.
- L has 210 works with more than 16 authors against `maxAuthorTeamSize` 16 (unchanged); this needs a semantics review by the hadoop-engineer.
- If lane D changes the L slice, rerun `build_l_input.py`: it refuses an existing tree, so use a new `--output-root` or have the human remove the old one. `check_manifests.py` fails a stale L description.
- The `--final` OK depends on uncommitted lane A and lane D files.

MANUAL ACTION REQUIRED:
- Human review of the diff, and an explicit yes before committing.
- Build the real L tree with `python3 -I experiments/scripts/build_l_input.py` (the default root has no `size-l` yet).
- The upload remains a human-approved step.

BLOCKED-ON OWNER:
- infra-engineer: the `--hadoop-config` upload option writing key `config/hadoop-config.json` and EMR-RENDER name `hadoop-config`, plus committing the 60000 / 4 / 3.36 pins.
- spark-engineer: confirm the P24 settings above.
- hadoop-engineer: review the `maxLocalSampleRecords` semantics in cluster mode (P22) and the over-16-author records.

BLOCKED-ON EVIDENCE:
- `scripts/upload-emr-artifacts.sh` and `scripts/lib/upload_emr_artifacts.py` contain no `hadoop-config` string (grep at about 09:2x CST).
- `git status` shows `scripts/config/release.conf` and `datasets/phase15/` uncommitted.

NEXT GATE: an independent code-reviewer verdict on the `experiments/**` diff, then the human's review and an explicit yes for the experiment commit. After that comes the P6 local chain at S and L (local L time against the 90-minute and 36-minute caps, 0 `maxLocalSampleRecords` rejects, sidecar parts within the cap). The progress log is at `/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/lane-C-progress.md`.

#### Agent report (2026-11-16T14:58:53.861Z, agent a9d438f)

STATUS: COMPLETE. Both drafts are corrected for P34 being impossible, and your mid-task update deciding option (i) is applied in the same pass. Three open items need a decision before the P19 approval record (see RISKS 1-3).

OWNER: documentation-engineer

WORK ORDER: Phase 15, branch phase-15, HEAD 7a02de2.
- Correct the session-2 plan and the demo script for the human's decision "P34 as planned is impossible. Set min 1 / max 2.5 NCU."
- Then the coordinator's DECISION UPDATE: option (i) with conditions 1-4, floor 2, a 5.8 h Neptune hard stop, R-c dropped, column B pending the tax read, and draft P19 wording.

FILES CREATED: none in the repository. The scratch files and the git-ignored progress log are listed under COMMANDS RUN.

FILES MODIFIED (both untracked and owned by this role):
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md (865 -> 1040 lines)
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/demo-script.md (265 -> 267 lines)

COMMANDS RUN (no AWS, Anthropic or Voyage calls; no Terraform or sbt; no secrets, tfvars or state read; no commit or stash):
- Reads:
  - `wc -l`, `grep -n`, `sed -n`, `od -c` and Read on: the plan, the demo script, prompt.md lines 129-200, docs/agent-runs/README.md, repairs.md E1-E5, infra/terraform/README.md lines 958-963.
  - `grep -n` on phase12b.tf (lines 22 and 42 confirmed), tests/phase15_elasticity.tftest.hcl (max 1 refused, line 206) and the Phase 14 runbook B13/C1-C3.
- Arithmetic: `python3 -I` checks (three runs). They reproduce every coordinator figure when the rate differences are not rounded first (+0.681 planned, +1.6884 cap). Rounding-only differences: option (i) column B cap is 25.43 exact vs 25.44 from the displayed figures (25.44 used); option (iv) project cap is 20.63 exact vs 20.64.
- Edits: Edit tool, plus `python3 -I` exact-string replacement scripts that assert one match each. Section 6.4 was replaced twice from /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/s64.md and then s64b.md; section 4a came from s4a.md in the same directory.
- Progress log (git-ignored): /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/doc-neptune-progress.md, appended after each section (`git check-ignore` confirmed .gitignore:2 target/).

TEST RESULTS: not applicable (docs only). sbt was not run.

VALIDATION RESULTS:
- Link check: all 18 relative links in the plan and the demo-to-plan link resolve (`test -e`, each printed OK).
- No 12-digit literals or e-mail addresses in either file (grep printed nothing).
- Consistency grep (hit counts; demo-script.md has 0 hits for every pattern except "1 NCU": 1 hit, line 5, its history line):

| Pattern | Hits in the plan |
|---|---|
| 0.1608 | 22 |
| "1 NCU" | 13 |
| "max 1" | 7 |
| 5.93 | 12 |
| 21.76 | 7 |
| 3.06 | 3 |
| 2.73 | 8 |
| 2.26 | 5 |
| "floor 3" | 11 |
| 6.17 | 3 |
| 22.00 | 11 |

- I reviewed every remaining hit in context. Each one is one of:
  - a history or "was" line (header entries at lines 18 and 29-41, and lines 426, 494, 526, 657, 674, 681, 690, 698, 757-758, 760, 803-804, 828, 834, 840, 842, 845, 904, 928, 930, 933, 1016-1017, 1020, 1026-1027);
  - correct per-NCU-hour usage (lines 187, 259, 261, 495, 517, 638, 653, 785, 796, 847);
  - a P34-is-impossible statement (lines 153, 261, 315, 449, 648, 650);
  - the human's verbatim Q3 words (line 967) or the Q3 row label (line 978);
  - the R-c record (lines 56, 999);
  - the Nov 13 fact "scaled above 1 NCU" (line 646);
  - line 589, the 6.1 "Modeled before 0.1608 (1 NCU)" column.
- No "decision pending" text remains. Command replay: not applicable; no commands were added.

CHANGED NUMBERS:

Rate correction (P34 impossible):

| Location | Old | New |
|---|---|---|
| Neptune rate (F23, P34, 6.1a, 6.3) | 0.1608/h ceiling | planned 0.297/h; cap 0.402/h (2.5 x 0.1608 per NCU-hour) |
| R-b Neptune cost (6.4) | 0.80 / 1.13 | 1.49 / 2.81 at 7.0 h, then cap 2.33 at 5.8 h under (i) |
| R-c Neptune row (5.4, record) | 0.40 / 1.04 | 0.74 / 1.41 |
| R-c total (5.4, record) | 1.07 / 2.26 | 1.41 / 2.63 |
| R0 + R-b planned A (summary, 6.4) | 3.50 | 4.18 |
| R0 + R-b cap A | 5.93 | 7.62, then 7.14 under (i) |
| R0 + R-b project A | 19.33 / 21.76 | 20.01 / 23.45, then 20.01 / 22.97 under (i) (margin 0.03 to 23.00) |
| R0 + R-b column B | 21.45 / 24.10 | 22.20 / 25.97, then 22.20 / 25.44 under (i), pending the tax read |
| R0 + R-b fits floor (B), planned | yes | no at floor 3; yes at floor 2 |
| Low scenario, 1.35 NCU (row relabelled) | 3.80 / 6.34; 19.63 / 22.17; 21.78 / 24.55 | cap 6.08; 21.91; B 24.26 at 5.8 h (derived) |
| Former 1.85-NCU row | 4.18 / 6.88 | folded into the plan row; values kept in history |
| R0 + R-b + R-c, A | 4.57 / 8.19 | 5.59 / 10.25 (record; dropped) |
| R0 + R-b + R-c, project A | 20.40 / 24.02 | 21.42 / 26.08 (record; dropped) |
| R0 + R-b + R-c, column B | 22.63 / 26.59 | 23.76 / 28.88 (record; dropped) |
| 6.3a R-b worst case E_b | 2.36 | 4.05, then 3.57 under (i) |

Gates and checks:

| Location | Old | New |
|---|---|---|
| Gate 1 formula (5.2, 6.4) | 6.17 - E_b - 0.75 | 7.17 - E_b - 0.75 (floor 2) |
| Gate 1 threshold | 3.06 | 1.37 at floor 3, then 2.85 under (i) |
| Planned X_a | 1.57 (passed by 1.49) | 1.35, passes by 1.50 (cache load removed) |
| Pre-R-b check (new) | none | spend to date + 3.57 <= 25.00; planned 20.75 |
| Gate 2 R-c cap / limit (record) | 2.26 / X_spent <= 2.73 | 2.63 / <= 2.36 |
| Gate 2 planned X_spent | 3.02 | 3.47 |
| Gate 2 margin | -0.29 | -1.11 |
| Gate 2 R-b Neptune so far | 0.53 | 0.98 |
| Gate 2 x1.11 check (derived) | +2.16, X_spent <= 0.57 | +2.53, <= 0.20 |
| Gate 2 "without S3 Vectors" | 0.24 / 90,000 queries | 2.94 still fails |
| Gate 2 low scenario | 3.22 | 3.22 (now fails against 2.36) |

Alerts, floor, report and schedule:

| Location | Old | New |
|---|---|---|
| 6.2 alerts, R0 + R-b | 19.25 / 21.26; alerts 18 / 18 and 20 | 19.93 / 22.95, then 19.93 / 22.47 under (i); alerts 18 / 18, 20 and 22 |
| 6.2 alerts, R-c (record) | 20.28 / 23.42 | 21.30 / 25.48; alerts 18 and 20 / 18, 20 and 22 (above the 25 budget) |
| 6.2 AWS parts | 5.51; 4.53; 7.67 | 7.20, then 6.72; 5.55; 9.73 |
| Floor / S | floor 3, S = 6.17, project <= 22.00 | floor 2, S = 7.17, project <= 23.00 |
| Report table: R-b increment | 1.86 | 2.54 (derived) |
| R-b Neptune window | 7.0 h cap | planned 5.0 h, hard stop 5.8 h |
| 5.3 step 1 | neptune_max_ncu = 1 | min 1 / max 2.5 |
| Schedule (6.7) | gate 2 at 14:15 CST; R-c block 14:15-16:45; "Neptune base-apply (max 1 NCU)" | gate 2 and R-c rows removed; Neptune base-apply at min 1 / max 2.5 NCU |
| Schedule (6.7) | latest cleanup 17:15 CST | 17:15 only if Neptune was never created |
| Clock (6.7, 5.3; new) | none | T_N0 10:50 CST / 16:50Z; load 12:45 / 18:45Z; latest load 15:40 / 21:40Z; destroy target 16:20 / 22:20Z; absolute 16:38 / 22:38Z |
| demo-script line 245 | "Neptune capped at 1 NCU" | "min 1 / max 2.5 NCU, with a 5.8 h hard stop"; R-c dropped; floor 2; history line added |

Text-only changes:
- P34 row, F23, the 6.1a "Fix: P34" block and the Neptune risk rows now say "not possible".
- Q1 and Q3 notes were added after the verbatim human words, which are unchanged.
- Notes in 9.2 and 9.3; section 4a (draft P19 wording, blanks left unfilled); 5.5 teardown order; section 2 source row; section 10 provenance entry.
- 5.2 stop conditions now follow the human's verbatim P25 rule (retry S once, drop L, no L retry).

ASSUMPTIONS:
- R-b's Neptune window is 5.0 h planned and 7.0 h at cap, back-solved from the earlier 6.4 rows.
- R0's planned 1.64 excludes the R-c cache load.
- "Neptune destroy issued" means the confirmed C3 pass 1 starts. The runtime and Neptune are deleted together, because the phase12b.tf:42 precondition requires neptune_enabled while the runtime exists.
- Item 8 of the P19 draft (key rules) is conditional: that approval was given for the Q12 Anthropic run.
- The plan does not state what happens after a failed S retry. I wrote the earlier rule (stop and report, no R-b) as the conservative reading, for the human to confirm.

RISKS (could not reconcile):
1. Absolute stop: a destroy issued at T_N0 + 5 h 48 min, plus about 18 min of deletion, ends about 6.1 h after T_N0. That is inside 5.8 billed hours only if billing starts at least about 18 min after T_N0. This is not confirmed and is stated in 5.3.
2. Pre-destroy gap: a load started at 15:40 CST ends about 16:17, which leaves about 3 min before the 16:20 target. B13, the inventory, C1-C2 and the pass-1 listing must all finish before the destroy. Session 1 took about 1 h from cleanup prepare to pass 2. This is flagged in 5.5 and P19 item 5 for the coordinator and the runbook owner to confirm.
3. Column B cap 25.44 is above USD 25 (condition 1 is open), and the floor-2 margin at caps is only 0.03.
4. Not changed:
   - demo-script item-list rows 11 and 14-16 still say "live with R-c"; the history line at the top covers them;
   - the P0 row still lists "gate 2" among the cap gates;
   - the P25 coordinator check in prompt.md still says 21.76 / <= 22, but that file is not mine.

MANUAL ACTION REQUIRED:
- The human reads the Billing tax settings (condition 1).
- The human confirms what happens after a failed S retry.
- The human fills in, dates and commits the P19 record from section 4a.
- The coordinator or runbook owner confirms the timing items in RISKS 1-2.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: independent code-reviewer read of both drafts (arithmetic and consistency), then the human's review of section 6.4 and the P19 wording.

#### Agent report (2026-11-16T15:00:08.435Z, agent a093722)

STATUS: DONE, with one BLOCKED-ON. P7 (a), (b) and (c) are done and tested. P7 (d) needs a change to a frozen .tf file and is returned to the coordinator. The P18 recommendation is below; the human decides. The P2 audit found 0 call-site mismatches, and I added a regression-guard test. Nothing was committed and no stash was made. No AWS API call was made, no real state was read, and Terraform never ran against a real provider.

OWNER: infra-engineer, pipeline lane B (relaunch), Phase 15. Branch phase-15, HEAD 7a02de2.

WORK ORDER: lane-B brief (P7, P18, P2) plus the 2026-11-16 08:40 updates. Progress log: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/lane-B-progress.md (entries 0-6, including the full audit table).

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_stagea_apply_path.py (lines 1-469, 21 tests)
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_aws_cli_shapes.py (lines 1-189, 5 tests)
- infra/terraform/tests/phase15_stagea.tftest.hcl was already in the tree as the untracked draft (253 lines). I reviewed it and kept it unchanged. Its assertions are sound, and its header reference to `plan_deltas.py derive --set stagea` is now true.

FILES MODIFIED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/lib/plan_deltas.py
  - Docstring: lines 11-14 and 16-24.
  - New constants at lines 49-59: STAGEA_RUNS, RUN_SETS, RESIDUAL_STATE (the 2 guards), STAGES.
  - `derive(text, run_set)` at lines 94-106. The stage-a set drops the residual guards from the base plan.
  - `check()` at lines 126 and 139-145: an entry marked "optional" may be missing from the plan and then prints ABSENT-OPTIONAL. If it is present, its action must still match.
  - CLI `--set` and the wider `--stage` choices: lines 154-166.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/config/expected-plan-deltas.json: lines 50-280 added (+231). Three new stages, each with its own provenance block:
  - stagea-base: 171 creates.
  - stagea-emr-enable: 13 creates, identical to emr-apply.
  - rb-base: 5 Neptune creates, 1 update (`module.identity.aws_iam_role_policy.task["graph-service"]` gains 2 Neptune statements) and 13 deletes. The cluster delete is optional, so the plan reads `13 to destroy` or, once the cluster is TERMINATED, `12 to destroy`.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_plan_deltas.py: lines 47-49 (expected stage set) and 83-92 (address regex now accepts root addresses and module names with digits).

COMMANDS RUN (AWS_* unset, AWS_CONFIG_FILE and AWS_SHARED_CREDENTIALS_FILE set to /dev/null):
- Draft re-run in the shared root: `terraform -chdir=infra/terraform test -filter=tests/phase15_stagea.tftest.hcl`. It failed to load with "Module not installed". The cause is run-level `module {}` blocks in the frozen tests/phase15_elasticity_dashboard and phase15_p41_runtime files; the root was not re-initialised after they were added. I did not run init in the shared root because lane A works there in parallel.
- Instead I used a scratch copy of infra/terraform (no *.tfstate*, no *.local.tfvars, providers symlinked) with check.sh's terraform env: `init -backend=false -input=false -lockfile=readonly`, then `terraform test -no-color [-verbose] -filter=tests/phase15_stagea.tftest.hcl`. Script: /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/laneB/tftest.sh
- `python3 -I scripts/lib/plan_deltas.py derive --set stagea --verbose-output <verbose output>`
- `terraform fmt -check -diff infra/terraform/tests/phase15_stagea.tftest.hcl` (named file only).
- Offline CLI shapes: `aws <svc> <op> --generate-cli-skeleton input` and `aws <svc> <op> help` (aws-cli/2.35.4).
- Probe: real Terraform with only the built-in provider, in a scratch dir, plan only.
- `(cd scripts/tests && python3 -m unittest ...)`

TEST RESULTS:
- Draft stage-a test, scratch root: "Success! 3 passed, 0 failed", exit 0. It was re-run at 08:59 CST on a fresh copy of the current tree, including the elasticity and lane-A edits, with the same result.
- Verbose stage-a run: the three plans have 173, 186 and 178 creates. Run 3's 178 addresses equal the real Session 1 base plan exactly (target/phase14/evidence/14b/base-plan.log, 178 PLAN-ACTION lines): 0 missing, 0 extra.
- `python3 -m unittest test_plan_deltas test_stagea_apply_path test_aws_cli_shapes test_syntax test_plan test_runtime_base_apply`: Ran 146 tests in 145.0s, OK, exit 0, no skips reported. Individually: test_plan_deltas 15 OK, test_stagea_apply_path 21 OK, test_aws_cli_shapes 5 OK.
- Mutation check: a synthetic script calling `aws emr list-instance-groups` and `put-object --checksum-crc32` made the static shape test fail on both lines.

VALIDATION RESULTS:
- P7 (c): `deploy.sh --stage base-apply --skip-runtime-archive` accepts both plans on realistic states, in dry run and with --execute (fake tools). Each ends RESULT: PASS with exactly 1 apply and no `s3 cp`.
  - The EMR-only plan (13 creates).
  - The R-b plan (5 creates, 1 update, 13 or 12 deletes).
  - No new stage is needed.
- P18 proof, in three parts:
  1. Real Terraform 1.13.5: a terraform_data guard with no input that is already in the state plans as `no-op`; one missing from the state plans as `create`. A source test confirms the real guards have no `input` or `triggers_replace`, so this carries over.
  2. Fake chain against a synthetic copy of the residual state: plan.sh records the lineage and add=171, change=0, destroy=0, no_op=2. `plan_deltas check --stage stagea-base` returns IDENTICAL, and deploy.sh base-apply accepts that exact plan and receipt.
  3. Move-aside alternative (`--expect-new-state`): 173 creates, and the check returns DIFFERS with exactly 2 UNEXPECTED guard creates.
- P18 recommendation (the human decides): plan stage-a base against the residual state, with no move-aside.
  - Why: no state mutation, the lineage stays continuous, and the guards stay no-op. The reviewed list (stagea-base) assumes this.
  - Move-aside needs a human state-file operation, a new lineage and a different expected list, and gives no benefit.
  - Precondition: the human runs `terraform -chdir=infra/terraform state list` just before the plan. It must list exactly `terraform_data.configuration_guard` and `terraform_data.provider_guard`; any other address means stop and decide.
- P2 review of the three commits:
  - 7ecc572 is correct: CLI 2.35.4 rejects `emr list-instance-groups` with rc 252 "invalid choice", and the describe-cluster customization embeds InstanceGroups, InstanceFleets and BootstrapActions.
  - b6dc94d is correct: matches STEPS_SCHEMA in awscli/customizations/emr/argumentschema.py.
  - 2b2d263 is correct. One stale comment remains at infra/terraform/deployer/operator_pipeline.tf:12, which still lists "list-instance-groups".
- P2 audit table (full version in progress entry 5; every row matches):

| Call site | svc/op | Argument shape | Fake shape (what is consumed) | Match |
|---|---|---|---|---|
| plan.sh:271, deploy.sh:781, run-bounded-pipeline.sh:542, upload-slice.sh:185/194, upload-emr-artifacts.sh:260/269, cleanup.sh:518 | sts get-caller-identity | --query Account or Arn, --output text | account or ARN text | yes |
| upload-slice.sh:211, upload-emr-artifacts.sh:287 | s3api list-objects-v2 | --bucket --prefix --output json | Contents; prints nothing when empty (real empty output not verifiable offline; the consumer accepts both) | yes |
| upload-slice.sh:221, upload-emr-artifacts.sh:297 | s3api get-object-attributes | --object-attributes Checksum ObjectSize | Checksum.ChecksumSHA256 and ObjectSize | yes |
| deploy.sh:905 | s3api get-object-attributes | ObjectParts --max-parts --query text | parts rows | yes |
| upload-slice.sh:238, upload-emr-artifacts.sh:314 | s3api put-object | --checksum-algorithm SHA256 --checksum-sha256 --if-none-match '*' | validates checksum and precondition | yes |
| upload-slice.sh:257, upload-emr-artifacts.sh:333, deploy.sh:892 | s3api head-object | --checksum-mode ENABLED [--query text] | ContentLength, ChecksumSHA256 | yes |
| deploy.sh:889, archive-evidence.sh:182/185, emr/sc-step.sh:246/250/404/406, emr/bootstrap.sh:178 | s3 cp / s3 ls | flags confirmed in the help synopsis | records the copy; "Total Size" line | yes |
| deploy.sh:827, rollback.sh:244 / deploy.sh:844 / deploy.sh:973 | ecr describe-images / describe-repositories / get-login-password | --image-ids imageTag=, --query text | digest text; return code only; password | yes |
| deploy.sh:1067 / 1079 / 1091 | ecs describe-services / describe-task-definition | --services list, --query text | name<TAB>arn; image text | yes |
| run-bounded-pipeline.sh:563 / 567 / 597, 675 / 660 / 690 | emr describe-cluster / get-auto-termination-policy / add-steps / cancel-steps / describe-step | CLI shapes (CUSTOM_JAR) | matching | yes |
| cleanup.sh:388 | resourcegroupstaggingapi get-resources | --tag-filters Key=,Values= | FAKE_TAG_JSON | yes |
| billing/*.py:280-286, 880 | budgets describe-budget (--show-filter-expression), describe-notifications-for-budget, describe-subscribers-for-notification | in the skeleton | own fakes | yes |
| phase12d-spike/*, phase4-emr-smoke.sh:538 | ec2, efs, kms, emr list-clusters --active, s3api head-bucket, add-steps | in the skeleton or help | no fake | yes |

  Of these, 41 API-operation call sites were checked flag by flag against the skeletons: 41 OK. No owned script needs a fix.
- Fake fidelity gaps; none affects a value the scripts read:
  - scripts/tests/fake_tool.py exits 0 for any unknown (svc, op). The new static test closes this gap for my four scripts.
  - The fake describe-cluster has no BootstrapActions; the scripts don't read it.
  - tests/scripts/sc_support.py cancel-steps prints "{}" (the real CLI prints CancelStepsInfoList); the script uses the return code only.
  - The dry-run print at run-bounded-pipeline.sh:597 omits the `--query StepIds[0]` that the execute path uses. This is cosmetic.
- Stale pins: none from lane B. I changed no sha-pinned file.

ASSUMPTIONS:
- The residual state holds exactly the two guards. Source: Session 1 after-cleanup inventory (2026-11-15T02:07:45Z) and decision-log 01:34:05Z, where phase12b_guard was state-rm'ed.
- A TERMINATED EMR cluster is dropped from state on refresh. Basis: Session 1 F4 and the decision log.
- The expected lists come from mock-derived address sets plus hand-derived actions. They are not a live plan, and a match is not an approval.
- P34 (neptune_max_ncu = 1) changes attributes, not addresses.

RISKS:
- Drift lines on existing resources (tags_all, description) are not modelled.
- The phase15_stagea test cannot run in the shared root until that root is re-initialised for the new test modules. check.sh's terraform gate does this init itself.
- Even with depends_on, the EFS DNS name may lag after the mount target becomes available. I could not confirm this from the AWS docs. scripts/emr/bootstrap.sh:301 mounts once with no retry (lane A's file).

MANUAL ACTION REQUIRED:
- Human: decide P18 at the pipeline review, and run the `state list` precondition above before the stage-a plan.
- Coordinator or documentation-engineer: add the new stages (stagea-base, stagea-emr-enable, rb-base) and the `plan_deltas.py check --stage <stage>` commands to the runbook (session-2-plan 5.2 steps 1 and 4, 5.3 step 1) and to the infra/terraform/README "Expected plan addresses" section. That README is frozen and not mine.

BLOCKED-ON OWNER: coordinator (frozen file infra/terraform/modules/emr/main.tf, infra-engineer territory) for P7 (d). Optional follow-ups for lane A: a bounded mount retry in scripts/emr/bootstrap.sh, which changes its pin, and fixing the stale comment at deployer/operator_pipeline.tf:12. For test-engineer: making the sc_support cancel-steps output real-shaped.

BLOCKED-ON EVIDENCE: Session 1 failure S1-F2 (decision-log.md:52-53): BOOTSTRAP_FAILURE "EFS mount failed", because the mount target completed at 1m23s while the primary node bootstrapped first. Exact change: in `resource "aws_emr_cluster" "pipeline"` (modules/emr/main.tf, around lines 53-117), add

```
  # S1-F2: the bootstrap mounts the EFS staging file system; never start the nodes before its mount target exists.
  depends_on = [aws_efs_mount_target.staging]
```

This changes no plan address, so the expected deltas stay valid. Once the file is unfrozen, I will add a static test to scripts/tests asserting that the cluster block's depends_on names aws_efs_mount_target.staging.

NEXT GATE: an independent code-reviewer pass on the files above. Then the human P18 decision and the coordinator's decision on the P7 (d) .tf change. Then check.sh's terraform and script-tests gates (not run here, per the brief), followed by commits that need the human's explicit yes.

#### Agent report (2026-11-16T15:01:34.090Z, agent a1fbeaf)

STATUS: COMPLETE (read-only sign-off. Q2 OK. Q1: no Hadoop change, but the result must be disclosed. Q3: OK, with risks listed.)
OWNER: hadoop-engineer
WORK ORDER: Phase 15 read-only sign-off of the pipeline bundle (P6 context; P22 semantics review), branch phase-15 at HEAD 7a02de2 with uncommitted lane changes in the tree.
FILES CREATED: scratch only, under target/phase15/lanes/hadoop-signoff/: count.py (streaming counter) and counts.jsonl (its output). No tracked files.
FILES MODIFIED: none
COMMANDS RUN:
- `python3 -I target/phase15/lanes/hadoop-signoff/count.py target/phase6-inputs/6fg-dblp/dblp.xml target/phase15-inputs/dblp-l/dblp.xml` (exit 0)
- `shasum -a 256` on the prep config and the L and S XML. prep-config.json is 5330214b…, which matches the pin in config-sources.json and the L manifest. L dblp.xml is 7e62bb42…, which matches the L slice sha256 in the manifest. S dblp.xml is c25a1e1a….
- Plus sed/grep reads of modules/hadoop, modules/spark (read only), scripts/emr/sc-step.sh, scripts/config/release.conf, and the Phase 6 and Phase 14 evidence.
- No sbt. No network. No secrets read.
TEST RESULTS: none run (no sbt, by rule). No Hadoop behaviour change is proposed, so no Hadoop tests are needed.
VALIDATION RESULTS (observed streaming counts):
| | S (10,577) | L (48,187) |
|---|---|---|
| Element types | all inproceedings | all inproceedings |
| Max authors | 71 | 79 |
| Works with >16 / >32 / >64 authors | 63 / 5 / 1 | 210 / 17 / 3 |
| Zero-author works | 21 | 105 |
| Author mentions | 45,587 | 203,584 |
| Coauthor pairs, all works | 117,425 | 489,889 |
| Pairs from teams of 16 or fewer (emitted) | 97,801 | 426,585 |
| Pairs dropped (teams >16) | 19,624 | 63,304 (12.9%) |
| Max record size | 3,912 B | 3,912 B |
| Distinct author strings | 21,819 | 76,623 |

Q1 maxAuthorTeamSize 16. Verdict: OK to keep for Session 2; CHANGE NEEDED in the disclosure only.
- What happens: the work itself is kept. J07 emits one OVERSIZE_TEAM reject ("team N exceeds 16") and no PublicationTeam or Authorship records (DerivedRecords.scala:14-27). J08 silently emits no pairs and no reject (DerivedRecords.scala:65). Because the team limit is 16, the per-work pair limit (maxCandidatePairsPerBlock 128, DerivedRecords.scala:66-82) never fires: C(16,2) = 120.
- Records: counters OVERSIZE_TEAM and REJECTED (PrepSupport.scala:572-583); a reject in export/.../reject.
- The stats largestTeam and largestPairExpansion are taken before the filter (PrepJobs.scala:992-994 and 1031-1037), so they report the true maximum. Expect largestTeam=79 and largestPairExpansion=3081 at L. Neither means those pairs were emitted.
- J09 still writes the work, its mentions and its Hadoop AUTHORED edges (PrepJobs.scala ExportReducer, DerivedRecords.scala:569-577).
- Consistency with S: Phase 6 local S run (docs/agent-runs/phase-06/evidence/6fg/hadoop-run.txt:13-14) shows OVERSIZE_TEAM:63 and largestTeam=71, which match my counts exactly. Its SCHEMA_FAILURE:21 also equals S's 21 zero-author works; I infer the same cause but did not trace it.
- Session 1 has no Hadoop counters. EMR hadoop-prep failed after 10 s on the missing config reference (phase-14 …/b9-emr/emr-run-4.log:120; decision-log.md:70-71).
- Predicted at L (not measured): OVERSIZE_TEAM=210, largestTeam=79.
- Bias: Spark builds memberships only from DBLP team records (Phase6CJobs.scala:388-410), and its AUTHORED edges, team sizes and coauthor metrics come from those memberships (Phase6CJobs.scala:746; Phase6DEJobs.scala:113-125).
  - So works with more than 16 authors leave the analytic graph completely.
  - "Max team size" is capped at 16 (maximumCoauthorsOnOnePaper is at most 15), against a true 71 (S) and 79 (L).
  - Coauthor breadth, publication counts, components and bridges lose 63 (S) and 210 (L) works.
  - So the answer is biased, not just bounded.
- Why keep 16:
  - The per-work pair limit reuses maxCandidatePairsPerBlock.
  - Raising the team limit to T needs that value to be at least C(T,2) (3,160 for T=80). Otherwise J08 rejects pairs while J07 keeps the team, and Spark's pair-count-mismatch check fails hard (Phase6CJobs.scala:451-460 and 635-642).
  - The same value also governs ER blocking in J05/J06 (PrepJobs.scala:797-842 and 899-932), so raising it changes the ER candidates and S's comparability with Phase 6, 14C and P10.
  - The team ceiling is 64 (release.conf:325), below L's 79.
  - Late-change and freeze risk.
- Disclosure needed:
  - Benchmark and method notes should say that graph team metrics cover teams of 16 or fewer.
  - Cite largestTeam (71 / 79) and OVERSIZE_TEAM (63 / 210) from the Hadoop stats as the corpus truth.
  - Owners: experiment-engineer (experiments/README.md 16B method note, questions) and documentation-engineer (report).
- Impact on L if kept: 210 works (0.44%) excluded and 63,304 pairs (12.9%) not emitted.

Q2 maxLocalSampleRecords / SampleBound. Verdict: OK.
- One budget per pipeline launch, not per job, input or mapper.
  - Installed once on the shared conf (HadoopPrepPipeline.scala:175); the SampleReady flag stops J01 and J02 from installing it again (PrepJobs.scala:105-106 and 133-134; HadoopIO.scala:281).
  - The driver scans the inputs in order DBLP, OpenAlex, Crossref, ORCID (HadoopIO.scala:280-295) and stores one byte-offset cutoff per qualified path.
  - Each mapper rejects any record whose offset is at or past its file's cutoff (PrepJobs.scala:339-349, 445-455 and 422-440).
  - So the result does not depend on splits, mapper count or execution mode.
- Coverage: L uses 48,187 DBLP + 3 (the openalex, crossref and orcid samples, one line each) = 48,190, which leaves 11,810 headroom under 60,000. The worst case allowed by TARGET_MAX is 50,003.
- Boundary:
  - Exactly 60,000 records: all accepted (HadoopIO.scala:341; DblpInput.scala:119-131).
  - The 60,001st record in input order is rejected.
  - If DBLP alone used up the budget, the later sources would get cutoff 0, and every one of their records would be rejected (HadoopIO.scala:286-287).
- Gate caveat: these rejects are OVERSIZE_RECORD with diagnostic "maxLocalSampleRecords" (PrepJobs.scala:340-347). They count only under the generic REJECTED counter, not a dedicated one. The P6 "0 maxLocalSampleRecords rejects" check must grep export/*/reject/* for that diagnostic, not read the counters.
- Pair and record ceilings:
  - There is no global pair or reducer-output ceiling in Hadoop.
  - Per work: teams of 16 or fewer give at most 120 pairs, under the 128 limit.
  - Record bytes: maxRecordBytes is 1 MiB against a 3,912 B maximum record.
  - J04 group limit is max(256, 16×16) = 256 lines (PrepJobs.scala:627), which is per record and does not scale with L.
  - Counters are Long values in a 10-counter group.
  - Copy-out: hadoop sends counters, stats, manifest and rejects only (sc-step.sh:347-348), under an 8 GiB limit (release.conf:310).
  - Config values (1, 32, 128, 16, 1 MiB, 1 MiB, 60000) are within the ceilings (release.conf:321-327).
  - L pair estimate: 426,585 emitted pairs plus ER candidates go to EMITTED_PAIR. S had 243,321 in total, so L might be about 1.1M (extrapolated, not measured). No ceiling applies to either.

Q3 L's 4.6x size. Verdict: OK, no change needed. Risks are below.
- Memory per task is bounded by record or group, not by dataset size:
  - The team and pair mappers keep one max value each.
  - BlockReducer keeps at most 32 members.
  - JoinReducer keeps at most 256 lines.
  - ExportReducer streams its values.
  - SampleBound streams the input on the driver (two passes over 28 MB).
  - ExportCheck.unresolved, which reads whole files, has no caller in main.
- Reducer count 1: keep it for both sizes so S and L stay comparable; it is part of the config fingerprint. Raising it would not speed up J09, because all export lines for one snapshot share the key "out\t<snapshot>" (PrepJobs.scala:1088), so one reducer receives them anyway.
- Map-output compression is off (PrepJobs.scala:57). Expect more spills at the default io.sort.mb, slower but safe.
- Output volume: about 1.0 GB at S (release.conf comment), so about 4.7 GB of EFS at L (extrapolated).
- Time: local S was 37 s real. L is expected at about 3 min locally and roughly 6-12 min on EMR across 9 YARN jobs, against the hadoop-prep timeout of 20% × 90 min = 1080 s (release.conf:299; emr-run-4.log:65). This is an estimate; P6 L must measure it.

ASSUMPTIONS:
- L uses the same prep-config.json as S, with the 3 one-line samples.
- EMR uses default container memory, since PrepJobs sets none.
- The EFS mount is visible to every node (sc-step.sh require_mount).
- My count.py matches one element per line, which holds for these slice files.
RISKS:
- (a) The max-team-size bias above.
- (b) ER blocking: the 128 pair limit effectively caps blocks at 16 members (C(17,2) = 136), though maxBlock is 32. L will drop proportionally more name and initial blocks. OVERSIZE_CANDIDATE_PAIRS rejects have no dedicated counter (PrepSupport.scala:572-588). This confounds S-vs-L ER recall (entity-resolution-engineer to note).
- (c) Hadoop has never run in cluster mode on this EMR chain. Session 1 failed before any job code ran. YARN with file:// on EFS and the FileOutputCommitter renames are unproven.
- (d) The hadoop-prep timeout margin at L is not measured.
MANUAL ACTION REQUIRED:
- Human: record the decision to keep maxAuthorTeamSize 16 and accept the disclosed bias, or approve a coupled change (team limit to at least 80 and pairs-per-block to at least 3,160, plus the infra ceiling, plus ER re-evaluation). I do not recommend the change before Session 2.
- P6 at L: grep the rejects for "maxLocalSampleRecords" (expect 0) and check OVERSIZE_TEAM=210 and largestTeam=79.
BLOCKED-ON OWNER: none for Hadoop. Disclosure: experiment-engineer (experiments/README.md) and documentation-engineer (report). Optional coupled change: experiment-engineer (prep-config.json), infra-engineer (release.conf:325), entity-resolution-engineer (blocking impact).
BLOCKED-ON EVIDENCE: Expected L values (OVERSIZE_TEAM 210, largestTeam 79, zero maxLocalSampleRecords rejects, wall time) are predictions until P6 runs.
NEXT GATE: P6 local run at S and L (infra-engineer harness), then a code-reviewer verdict, then the human records the team-size decision.

#### Agent report (2026-11-16T15:06:32.079Z, agent a1fbeaf)

STATUS: COMPLETE (read-only follow-up; no edits, no sbt, offline)
OWNER: hadoop-engineer
WORK ORDER: Phase 15 follow-up. Size the human's middle option: keep the 16-author / 128-pair cap on pair records only, and emit team and authorship records for works with up to 80 authors.
FILES CREATED: none in this follow-up. The earlier scratch files under target/phase15/lanes/hadoop-signoff/ are unchanged.
FILES MODIFIED: none
COMMANDS RUN: sed and grep reads only, of modules/spark Phase6CJobs.scala, Phase6DEJobs.scala and Phase6Main.scala; modules/core HadoopPrepConfigLoader.scala; modules/entity-resolution InputLoader.scala; scripts/emr/sc-ceiling-check.py; infra/terraform/emr-step-programs.json; and the 15a Spark template's `failOnHardInvariant` value (it is `true`).
TEST RESULTS: none run (read-only).

VALIDATION RESULTS:

(2) Spark (answered first because it decides the verdict): the middle option breaks two Spark invariants, and the Spark run fails.
- Coauthor edges come from pairs; team sizes come from memberships (team records).
  - Coauthor edges: validPairs → edgeMaterial → adjacency at Phase6CJobs.scala:417-487, then arcs(edges) at Phase6DEJobs.scala:68 and 139-143 (weightedDegree, distinctCoauthorCount).
  - Team sizes: memberships are built from team records (Phase6CJobs.scala:388-410), and AUTHORED edges from memberships (Phase6CJobs.scala:746-751).
  - teamSize, totalCoauthorOccurrences and maximumCoauthorsOnOnePaper also come from memberships (Phase6DEJobs.scala:113-125).
- What a 79-author team with no pairs would cause:
  - Check 1: the pair-count check expects C(79,2) = 3081 pairs for the work and finds 0 (Phase6CJobs.scala:451-460). That is a hard violation (hardFailure=true, Phase6CJobs.scala:635-642). The template sets failOnHardInvariant true, so Phase6Main.scala:182 → failIfHardIntegrity (Phase6Main.scala:74-90) throws "hard graph invariant failed".
  - Check 2 (if check 1 were relaxed): the W_r = T_r check fails for every mapped author of the large works. Their T_r gains 78 from memberships, but W_r gains 0 from pair edges. This throw is unconditional and does not depend on failOnHardInvariant (Phase6DEJobs.scala:541-554).
- So yes: the large works would add AUTHORED edges and correct team sizes but no coauthor edges, and that is not consistent with the current graph invariants.
  - Making it consistent needs a Spark contract change (spark-engineer): exempt teams above the pair cap from check 1, and either count T_r from pairs or exclude those works from it in check 2. That change needs the cap passed into Spark config.
  - It also redefines the metrics: maximumCoauthorsOnOnePaper could be 78 while distinctCoauthorCount, from edges, omits those coauthors. That has to go into the Spark README contract (modules/spark/README.md:41-43).

(1) Code and config changes needed:

| File | Owner | Change |
|---|---|---|
| modules/hadoop/.../PrepSupport.scala:72-76, 657-668, 44 | hadoop-engineer | New ConfKeys key for the team-record limit; add it to TaskSink.limits; bump TransformationVersion |
| modules/hadoop/.../PrepJobs.scala:49, 995-996 | hadoop-engineer | Set the new key in configuration; TeamMapper passes it to DerivedRecords.teams |
| modules/hadoop/.../DerivedRecords.scala:8-27 (teams), 58-65 (pairs) | hadoop-engineer | teams uses the new limit (80); pairs keeps maxAuthorTeamSize 16 and the 128 limit. J08 for 17-80 authors needs no reject (J07 no longer rejects) and should log or count the skip so it is not silent |
| PrepJobs.scala:627 (J04 group limit) | hadoop-engineer | Review only: max(256, 16×16) = 256 lines; a 79-author group should fit (not traced) |
| modules/hadoop/README.md:39-40, src/test/** | hadoop-engineer | Update the J07/J08 rows; feature tests for 17, 79, 80 and 81 authors |
| modules/core HadoopPrepConfig.scala:27-28, HadoopPrepConfigLoader.scala:20-33, 66-67, 89-90, resources/scholarchain.hadoop-prep.v1.json | domain-engineer | Yes, this is a core contract. The loader fails closed on unknown fields (HadoopPrepConfigLoader.scala:8-10), so a new config field means a case-class field, loader field, validation, fingerprint and contract tests. The only alternative is a hard-coded Hadoop-owned limit (like IntermediateBytes, PrepSupport.scala:57-66), which leaves the value out of the config fingerprint |
| experiments/inputs/15a/prep-config.json | experiment-engineer | Add the new key = 80; re-pin its sha in config-sources.json and in the 15a manifests (size-25/50/100/l); the jar shas change too |
| scripts/emr/sc-ceiling-check.py:8-13 | infra-engineer | Add an 8th field. The pin (emr-step-programs.json:4) and terraform tests change |
| scripts/emr/sc-step.sh:265 | infra-engineer | The "exactly seven" ceilings check becomes eight |
| scripts/config/release.conf:321-327 | infra-engineer | Add a team-record ceiling of at least 80, plus the parity test against the Phase 4 smoke script |
| modules/spark Phase6CJobs.scala:451-460, Phase6DEJobs.scala:541-554, README.md:41-43, tests | spark-engineer | Contract change, as in (2) |

- The 64 ceiling (release.conf:325) bounds only the config key `maxAuthorTeamSize` (sc-ceiling-check.py:13, compared at :54-61). Today that one key governs both team records and pairs (DerivedRecords.scala:14 and 65).
- With the key split, the 64 ceiling would bound only the pair key (kept at 16). The new team key would have no ceiling until infra adds one.

(3) ER: blocking is unaffected, but ER's inputs change.
- J05 BlockMapper reads only Bibliography lines from J04 (PrepJobs.scala:757-769), not team, authorship or pair records. J06 reads J05 output.
- The ER InputLoader reads team and authorship records (InputLoader.scala:461-462). It only validates them (:487-498) and does not pass them to ResolutionInput.assemble (:505-516).
- So ER candidates and decisions do not change. Its input bytes, and so its input hash and run identity, do change. ER needs no contract change.

(4) Effort estimate (hours; estimates, not measured):
| Work | Hours |
|---|---|
| Hadoop code, feature tests, module gate | 1.5-2 |
| Core field, loader, schema resource, contract tests | 1-1.5 |
| Spark two invariants, metric semantics, README contract, known-graph tests | 3-4 |
| Infra ceiling script, sc-step, release.conf, step-program pin, terraform and script tests | 1.5-2 |
| Experiments config, sha re-pins in config-sources and 4 manifests, check_manifests | 0.5-1 |
| Jar and step-program pin refresh | 0.5 |
| Full `sbt check` per owner gate (several runs) | 1-1.5 |
| P6 re-run at S and L | 1-1.5 |
| Independent reviews (4-5 owners) | 2 |
| **Total** | **about 12-16 h** |

- A side effect: S loader dry-run counts would no longer match the 78,104 / 328,967 / 269,753 baseline, because AUTHORED edges from the 63 large works (about 1,504 S mentions) would be added.

(5) Verdict against the human's rule: fall back to keeping 16 and disclosing. The middle option fails both tests: it touches the Spark contract (two hard invariants plus metric semantics), and at about 12-16 h it costs far more than 2 h. It also changes core and infra. ER is not touched.
- Disclosure (from my first report): graph team metrics cover teams of 16 or fewer authors. The corpus maximum comes from Hadoop's pre-filter stat: largestTeam is 71 for S and 79 is expected for L. OVERSIZE_TEAM is 63 for S and 210 is expected for L.
- Disclosure owners: experiment-engineer (experiments/README.md) and documentation-engineer (report).

ASSUMPTIONS: Effort figures assume one fresh owner session per module and no review repair rounds; each repair round adds about 1-2 h.
RISKS: If the change were made anyway, S could no longer be compared with Session 1 and Phase 6 (different graph counts and Spark metric definitions), and the late change would land during the commit freeze before the Nov 19 session.
MANUAL ACTION REQUIRED: The human records the decision: keep 16 and disclose (recommended), or approve the multi-owner change as a separate work order.
BLOCKED-ON OWNER: none. If the change is approved: spark-engineer, domain-engineer, infra-engineer, experiment-engineer and hadoop-engineer.
BLOCKED-ON EVIDENCE: none
NEXT GATE: Human decision on team-size handling, then P6 at S and L under the current config.

#### Agent report (2026-11-16T15:07:14.156Z, agent a093722)

DELTA REPORT for P7 (d), lane B, infra-engineer. The change is in and its tests pass. 6 of the 7 Terraform test files that plan module.emr pass. The seventh, phase14a, fails 2 runs because of a stale pin; neither failure comes from my change.

STATUS: DONE (P7 (d)). Nothing was committed and no stash was made. No AWS call was made and no real state was read.

FILES MODIFIED:
- infra/terraform/modules/emr/main.tf, lines 116-117, inside aws_emr_cluster.pipeline after the lifecycle line: added the comment "# S1-F2: the bootstrap mounts the EFS staging file system; never start the nodes before its mount target exists." and `depends_on = [aws_efs_mount_target.staging]`.
- scripts/tests/test_stagea_apply_path.py, lines 183-212: a resource_block() helper and class EmrClusterWaitsForTheMountTargetTests with 2 tests:
  - the cluster block's depends_on names aws_efs_mount_target.staging;
  - nothing else in the cluster block references the mount target, so the depends_on is the only thing enforcing the order.

COMMANDS AND RESULTS (AWS env unset, check.sh's terraform env):
- `terraform fmt -check -diff infra/terraform/modules/emr/main.tf` (that file only): exit 0.
- Terraform test files found with grep 'module.emr|emr_config|modules/emr' over infra/terraform/tests/*.tftest.hcl: 7 files.
- Scratch-root method: init -backend=false -lockfile=readonly, then `terraform test -filter=<file>`. The scratch copy now mirrors the repository layout (scratch/repo/infra/terraform, with scripts/config and scripts/emr copied in), because phase13c reads ../../scripts/config/release.conf. Its first run in the old layout failed for that reason only.

| File | Passed | Failed | Skipped | Exit |
|---|---|---|---|---|
| phase12b | 18 | 0 | 0 | 0 |
| phase12c | 9 | 0 | 0 | 0 |
| phase13c | 37 | 0 | 0 | 0 |
| phase14b_plan_deltas | 3 | 0 | 0 | 0 |
| phase15_elasticity | 5 | 0 | 0 | 0 |
| phase15_stagea | 3 | 0 | 0 | 0 |
| phase14a | 20 | 2 | 18 | 1 |

- Python: `(cd scripts/tests && python3 -m unittest test_plan_deltas test_stagea_apply_path test_aws_cli_shapes test_syntax test_plan test_runtime_base_apply)` ran 148 tests, OK, exit 0. That is 146 before plus the 2 new tests.

STALE PIN (needs lane A or the coordinator; I may not edit the file):
- Lane A's uncommitted infra/terraform/emr-step-programs.json now pins sc-step.sh at 376b3e15d1db…. That hash is missing from infra/terraform/environments/course.local.tfvars.example, which is a frozen elasticity file. The other three program hashes are present.
- Two phase14a runs fail as a result:
  - the_tfvars_example_carries_exactly_the_manifest_hashes_for_the_four_step_programs (assertion);
  - emr_enabled_with_the_four_step_programs_of_the_example_is_accepted (phase12b_guard Finding C1 precondition).
- Fix: refresh the sc-step.sh sha256 in course.local.tfvars.example, for example by regenerating it with `python3 -I scripts/lib/pipeline.py step-manifest`. This does not depend on the depends_on change.

NOTES:
- The depends_on changes no plan address, so the expected plan deltas stay valid.
- I did not touch scripts/emr/** or the frozen elasticity files. Lane A owns the bounded mount retry in bootstrap.sh.
- Logged as entry 7 in target/phase15/lanes/lane-B-progress.md.

NEXT GATE: independent code review of the two changed files, plus the pin refresh by lane A or the coordinator.

#### Agent report (2026-11-16T15:07:49.167Z, agent ab4179f)

STATUS: COMPLETE (read-only sign-off). Q1, Q2 and Q4 are confirmed. Q3 is not confirmed: L has only a narrow, unproven margin against 36 minutes. No change to the template is needed; the go/no-go checks below are added.

OWNER: spark-engineer (read-only; no file edited)

WORK ORDER: Phase 15 P24 sign-off on experiments/inputs/15a/spark-emr-template.json (sha256 9341c162c8b05c9496685083d5a470a77f555ee24626eb4b946a439e1fd8206a), one template for S (10,577 works) and L (48,187 works).

FILES CREATED: none in the repo. Scratch evidence is in /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/spark-signoff/:
- s-jobs.json, s-job-rows.json (S event-log job timeline)
- s-graph.json, l-graph.json (per-window graph and iteration simulation)
- s-diam.json, l-diam.json (exact diameters and spread of label-propagation iteration counts)

Throwaway scripts (not in the repo): /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/ev.py and .../scratchpad/g/{graph_iters.py,diam.py}

FILES MODIFIED: none

COMMANDS RUN (all offline; python3 -I; no sbt):
- grep, sed and cat on the spark, core and hadoop sources, sc-step.sh, spark-12-10.conf, release.conf, the EMR Terraform and experiments/README.md.
- python3 -I ev.py on the S raw event log (464 MB, streamed): target/phase6-runs/14c-spark-export-capped/.event-logs/cc298dd8-.../local-1794171412928
- python3 -I inline: aggregates and a least-squares fit over event-log-summary.json of run f6e63b4b (2,024 stages).
- python3 -I graph_iters.py and diam.py on target/phase6-inputs/6fg-dblp/dblp.xml (S) and target/phase15-inputs/dblp-l/dblp.xml (L). The L file's sha256 matched 7e62bb42...ea34 (shasum).
- gzip -dc on the Phase 12D local G1 event log; read steps-final-summary.json from the 12D live attempt 5.
- python3 -I diff of the template against target/phase6-inputs/14c-runtime/spark-export.json: only the 4 path keys differ.

TEST RESULTS: no tests run (read-only lane; sbt is reserved for another agent).

VALIDATION RESULTS:
- **The graph model matches S exactly.** I modelled each window as exact DBLP author strings, keeping only works with at most 16 authors (prep-config maxAuthorTeamSize 16). Against Spark run f6e63b4b it reproduces exactly: vertices per window (20,967 / 3,908 / 4,506 / 6,637 / 11,088 / 15,651), 81,181 all-years edges, 228,715 windowed edges, components (1,045 …), largest components (17,179 …), max coreness 15, max degree 247, and **k-core 16 iterations**.
- **Component iterations depend on ID order, so I bounded them.** The simulation gives 16 against Spark's 17. The hard bound is max diameter + 1 = 21 for S (exact diameters ≤ 20).

**Q1 — 64 partitions: CONFIRMED, 64 for both S and L. Owner: experiment-engineer, no change.**
- **AQE is on, by Spark 3.5.4's default, not by any setting.**
  - `spark.sql.adaptive.*` is not set in scripts/config/spark-12-10.conf:1-38.
  - It is not set in Phase6Main.scala:101-118, which sets only `spark.sql.shuffle.partitions` (:108).
  - Terraform renders exactly that conf file (infra/terraform/tests/phase13c.tftest.hcl:167), and sc-step.sh:221-232 adds only YARN, JAVA_HOME and maxExecutors settings.
  - S proves it is active: AdaptiveSparkPlan appears in 12 plan files, and the largest shuffle stage (4177) ran 16 tasks from 64 partitions.
  - On YARN, `defaultParallelism` = max(cores, 2) = 2, the same as local[2], so the coalesce target is still min(64 MiB, total/2).
- **Memory headroom is ample even without any coalescing.**
  - A 3g heap with 1 core gives one task at a time 1,663 MB of unified memory, of which at least 832 MB is execution memory that cache cannot claim.
  - About 63 MB per partition (L ≈ 865 MB × about 4.5 ≈ 3.9–4.0 GB / 64) is roughly 130–250 MB in memory as rows. That is at least 3x headroom, and sort and aggregation spill to disk beyond it.
  - YARN fits: driver plus 2 executors at 3,456 MB each ≤ 12 GB.
- **Partition count does not change results.** `shufflePartitions` is a physical setting, excluded from the logical fingerprint (SparkAnalyticsConfig.scala:33-35, :58-79).
- **Loader sidecar parts do not depend on it.** They are sized by bytes (Phase7NeptuneExport.scala:157,162). S's largest parts are 8.47–8.55 MB, under the 16 MiB cap.

**Q2 — iteration caps: CONFIRMED, 50 / 20 / 50. Owner: experiment-engineer, no change.**
- Components and k-core fail the run if not converged (`require` at Phase6DEJobs.scala:198 and :303).
- **Components on L:** exact diameters per window are 19 / 18 / 19 / 18 / 17 / 17, so the hard bound is 20 iterations. Twelve random label orders gave 12–16. The margin to 50 is at least 30.
- **K-core on L:** the simulation (exact on S) gives **26 iterations**, up from 16; per window 26 / 18 / 20 / 16 / 20 / 15. Degeneracy stays 15, which the 16-author cap guarantees. The margin to 50 is 24. A cap of 30 would be thin, which is a reason not to lower it.
- **Community does not fail at its cap.** Hitting 20 is recorded as `converged=false` (Phase6DEJobs.scala:571). S did not converge in any of the 6 windows, so the result depends on the cap; keep 20 for both sizes.
- **Changing any cap costs comparability.** The caps are in the logical fingerprint (SparkAnalyticsConfig.scala:67-70), which feeds the run ID (Phase6Main.scala:131-141; StableIds.scala:527-534).

**Q3 — time: CHANGE NEEDED, as go/no-go checks rather than template values.**

Estimate: L's Spark step on EMR is about 28–37 minutes, central about 32. It fits 36 minutes only narrowly, and this is unproven.

*S basis (observed):*
- Wall time 304.6 s at local[2] on an Apple M5 (event-log ApplicationStart → ApplicationEnd).
- 2,024 stages, 27,344 tasks, total task run time 443.8 s, 27.1 GB of shuffle read plus write.
- Fit: run time (ms) ≈ 6.24 per task + 6.76 per shuffle MB + 44 per stage. This reproduces the 443 s.
- 320 stages always ran 64 tasks (20,480 tasks, 200.6 s of stage time). AQE cannot coalesce those.

*L scaling (from the XML model):*
- Windowed edges 3.90x, vertices 3.60x, largest component 3.82x.
- About 15% more iterations, mostly k-core (26 against 16).
- So stages about 2,330, tasks about 40,000, shuffle volume about 4.5x.
- Predicted local[2] time on the M5: about 683 s (about 11.4 minutes).

*EMR conversion:*
- Phase 12D G1 fixture: 224.1 s on EMR (live step) against 29.2 s at local[2]. That suggests about 30–40 s to start the application plus about 0.08–0.1 s per stage.
- Assumed, not measured: an m5.xlarge vCPU is 2.0–2.5x slower than an M5 core; about 0.5 minutes of EFS output; 1 core node with 2 executor slots.
- L total: start 0.7 + compute 19.6–24.5 + driver 3.2–4 + cluster overhead 3.4–7.2 + EFS about 1 ≈ 28–37 minutes.
- The same model gives S ≈ 14–20 minutes, so L ≈ 1.9–2.3x S.

*Go/no-go checks (owner: orchestrator / experiment-engineer):*
- (a) If the P6 local L Spark wall time on the M5 exceeds about 15 minutes, L is not expected to fit.
- (b) If the live S Spark step exceeds 16 minutes, L is predicted to exceed 36 minutes. Apply the P25 rule or a smaller L.

*Settings that save time without changing results:* only `shufflePartitions`. Going 64 → 32 for L saves an estimated 2–2.5 minutes (about 11,800 fewer tasks in the fixed-64-task stages). Memory stays fine at about 126 MB per partition. Values, IDs and run ID are unchanged, but the physical fingerprint changes and the S/L timing comparison is confounded. I recommend it only as a fallback if check (b) fails and it is recorded.

*Settings that change the logical config, which breaks the claim that S and L used the same algorithm settings:*
- `checkpointInterval`: no change to metric values, but it is in the logical fingerprint and run ID (SparkAnalyticsConfig.scala:70). The time effect is uncertain because longer lineage costs more planning. Do not change it.
- `componentMaxIterations`, `kCoreMaxIterations`: they change the fingerprint, and lowering them risks failure.
- These change the output values themselves: `communityMaxIterations`, `maxHops`, `sampledPathPairCount`, `pathSampleSourceCount`, `samplingSeed`, `representativeWorkLimit`, `maxTeamWorkLimit`, `windows`. Keep them identical.

**Q4 — other keys: CONFIRMED, none.** Only `hadoopRunRoot`, `entityResolutionRunRoot`, `outputRoot` and `checkpointDirectory` differ. sc-render-spark-config.py replaces exactly those four (lines 3, 18-20; called at sc-step.sh:328). The years 2005–2026 and the 16-author cap are the same for both sizes. One template with one sha256 pin is correct.

ASSUMPTIONS:
- ER on L stays about 1:1 with exact author strings, as it did on S (20,967 = 20,967).
- An m5.xlarge vCPU is 2.0–2.5x slower than an M5 core (not measured).
- G1's overhead per stage applies to L.
- L's shuffle volume is about 4.5x S (graph 3.9x times 1.15x iterations). The experiment-engineer's 4.66x is in the same range.

RISKS:
1. **The L time margin is narrow** (central about 32 of 36 minutes); see the checks in Q3.
2. **The disk may fill (unmeasured).**
   - S wrote 12.58 GB of shuffle in total, so L would write about 55 GB in total.
   - Each node has a 32 GiB gp3 data volume (phase12b-variables.tf:86).
   - How much is on disk at the peak depends on when Spark cleans old shuffle files, which I could not measure.
   - P6 at L should record the peak size of Spark's local dir. If it is above about 20 GB, `ebs_size_gb` should go to 64; the validation allows 32–128 (phase12b-variables.tf:131). That is an infra-engineer Terraform change behind the human gate.
3. **More paths will exceed `maxHops`.** On S, 48 of 120 paths exceeded 6 hops; L will likely have a higher share. That is a result, not a failure.
4. **AQE is on only by default, not pinned.** A different runtime default would silently change partition sizing. Low risk with the Spark 3.5.4 runtime pinned.

MANUAL ACTION REQUIRED: none from this lane. The orchestrator should add checks (a) and (b) and the peak-disk measurement to the P6 and live-run gates.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none. The time estimate is unverified until P6 measures L locally.

NEXT GATE: P6 local chain at S and L (infra-engineer and test-engineer), measuring the L Spark wall time, peak local shuffle disk, and that sidecar parts stay within the loader cap. Then code-reviewer on the experiment commit with the template pins.

#### Agent report (2026-11-16T15:09:21.788Z, agent a9d438f)

STATUS: COMPLETE. All five 4a review fixes are applied. The fallback for "S fails twice" works with no code change, but it is time-conditional and not blocked. Both are detailed below.

OWNER: documentation-engineer
WORK ORDER: Phase 15, the human's 4a review fixes (items 1-5) and a read-only feasibility check of the local P6 S export fallback.
FILES MODIFIED: /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md (untracked). demo-script.md is unchanged in this round.
FILES CREATED: none. The progress log was appended: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/doc-neptune-progress.md (git-ignored).

COMMANDS RUN (read-only; no AWS, Anthropic or Voyage call; no sbt or Terraform run; nothing under target/phase14/private/ read; no commit):
- `git show HEAD:` on EmbeddingManifestMain.scala, LiveEmbeddingIngestMain.scala, Phase6EmbeddingSource.scala and EmbeddingManifest.scala. I read HEAD because the working tree holds unreviewed lane drafts of the two rag mains. `git diff --stat` showed that only report fields changed there; the CLI flags did not.
- `grep -n` / `sed -n` on phase-14-live-session.md, 14c-templates.md and the render-config template.
- `ls` of the lane logs: no P6 harness exists yet.
- Edits with `python3 -I` exact-replacement scripts, each asserting a single match.
- Checks: grep for 25.00, "no R-b", the item 8 bracket and 12-digit literals.

DELTA (4a and every copy of the same rule):
1. **Item 5 (clock).** It already had the corrected clock from the previous round, so no change was needed:
   - target T_N0+5h15 (16:05 CST / 22:05Z); absolute T_N0+5h30 (16:20 / 22:20Z);
   - latest full-variant load start 14:25 / 20:25Z; latest load start of any kind 14:38 / 20:38Z;
   - pre-destroy steps start by 15:15 / 21:15Z.
   A note in 4a and the header history records that answer 1 was already met.
2. **Item 2 (credits).** New line in 4a: "AWS credit balance read: USD ____ at __:__Z … at least the Session 2 AWS cap of USD 6.72; otherwise this approval is void." 6.72 = 7.14 - 0.42. The same rule is in 5.1 (pre-session), the 6.2 condition-1 bullet and the 6.7 Wed Nov 18 row.
3. **Item 4 / pre-R-b check.** The check is now `spend to date + 3.57 <= 23.00`, was 25.00. Above 23.00, R-b is skipped unless the human records a new decision. Planned value: 20.75, margin 2.25. Changed in 4a item 4, the 5.2 gate-1 checklist (human's words quoted), 6.4 gates, 6.7 gate row, the summary at line 53, the 6.1 tax bullet, the 6.2 bullets and the risk row.
4. **Item 3 (S fails twice).** 4a item 3 now says R-b runs on vectors from the local P6 S run. New section 5.2 step 7b holds the fallback. The 5.2 stop condition marks "stop, no R-b" as superseded. The gate-1 checklist accepts "S PASS, or the 7b fallback vectors ingested by about 12:15 CST". 6.4 and the 6.7 08:30 row are updated.
5. **Item 8 (keys).** Kept; the "[Include item 8 only if…]" bracket is removed. Item 8 now names the Session 2 Voyage key (stage-a ingest and query smoke) and the Anthropic key.

FEASIBILITY VERDICT: feasible with no code change; time-conditional. Line numbers are at HEAD 7a02de2.
- **Render takes a local export.** EmbeddingManifestMain flags are `--export --work-manifest --config --manifest-output --report` (EmbeddingManifestMain.scala:15). It calls `Phase6EmbeddingSource.load(Path.of(--export))` (:61-62). Session 1 already rendered from a local export (phase-14-live-session.md:1136).
- **Required export contents.** load-manifests/s3.json (Phase6EmbeddingSource.scala:66) and load-manifests/s3vectors.json (:98); the tables semantic-summaries, nodes/type=topic and nodes/type=institution (:76). Each table is checked against its manifest (sortedRowsSha256 and other fields, :108-112), and the qualifications are read (:121). So the whole tree must be kept unmodified.
- **The export does not need to be in S3.** Each textS3Uri must start with s3://<textBucket>/<textPrefix>/versions/ (LiveEmbeddingIngestMain.scala:255). The ingest writes each chunk's text object there itself (EmbeddingManifest.scala:436). textBucket is the rag bucket and textPrefix is embedding-text (14c-templates.md:9, :24-25). upload-slice.sh (runbook :1045-1046) belongs to the graph path and is not needed.
- **Config changes.**
  - render-config.json: none (same file and P26 settings).
  - live-config.json: none.
  - ingest-approval.json: only manifestSha256 and the expiry change (runbook :1139).
  - Caps are unchanged: vectorCap 10000, concurrencyCap 2, embeddingCallCap 20000, dollarCapUsd 0.25 (14c-templates.md:74). That is the same Voyage cap.
- **Commands.** The B8.6 render, key and ingest steps (runbook :1134-1144) and the B8.7 smoke (:1150-1153) are unchanged except `EXPORT=<P6 S retention dir>/spark`. A `shasum -a 256 -c SHA256SUMS` check and a commit check come first.
- **Schema.** Identical by construction only if P6 uses the frozen session commit, the same job JAR and the same Spark template (P24). Bytes will differ (run ID, timestamps). This is not verified by comparison, because no EMR S export exists yet.
- **Report wording:** "vectors derived from the local P6 S run", with sourceRunId (EmbeddingManifestMain.scala:81), the SHA256SUMS sha256, the commit, and the two failed S runs with their logs.
- **Clock condition (estimate).** The fallback render, ingest and smoke, plus gate 1, must finish by about 12:15 CST (18:15Z). That keeps T_N0 at or before about 12:20 CST. Budget after the destroy target T_N0+5h15:
  - pass 1: 18 min 27 s (Session 1);
  - list-2 plus pass 2: about 7 min (Session 1, 02:01:09Z-02:07:45Z);
  - IAM window 2: about 45 min (6.7);
  - C5b-C9: about 15 min (estimate);
  - total: ends by the 19:00 hard stop.

  If two full 90-min S runs end at about 11:30, about 45 min remain. 10,000 vectors would then need about 5 vectors/s, against Session 1's unbatched 0.614/s. It depends on the P26 batched throughput, which has not been measured live. If the fallback does not fit, R-b is skipped unless the human decides. The two options I listed are not chosen: start the fallback ingest in parallel with the S retry, or render fewer vectors.

P6 RETENTION REQUIREMENTS (for the P6 harness brief; also added to the plan's P6 row):
- **What:** the complete Spark export directory of the P6 S run (the `--export` dir), whole and unmodified. It contains load-manifests/s3.json, load-manifests/s3vectors.json, semantic-summaries/, nodes/type=topic/, nodes/type=institution/, all other tables and _SCHOLARCHAIN_SPARK_COMPLETE.
- **Where:** git-ignored, under target/, outside target/phase14/private/, and outside anything a build `clean` removes (the build-engineer should confirm this). The proposed path is target/phase15/p6/size-S/<p6-run-id>/spark/. It is a proposal only and does not exist yet; the harness owner sets it.
- **sha manifest:**
  - SHA256SUMS in <dir>/, one line per file under spark/, relative paths, sorted;
  - a provenance file with the git commit, the job JAR sha256 (equal to the S manifest's), the Spark template sha256 (P24), the S input-tree sha256, the P6 run ID (equal to the render report's sourceRunId), and the start and end UTC;
  - the P6 render-only report of the same export.
- **Reproducibility:**
  - P6 S runs on the frozen session commit, after the P15 rebuild (the Wed Nov 18 row now says so).
  - Rerun P6 S if a later commit changes Hadoop, ER, Spark or export code or the templates.
  - Keep the directory until the Session 2 report is accepted.
  - Thursday check: `shasum -a 256 -c SHA256SUMS` exits 0, and the recorded commit equals `git rev-parse HEAD`.

TEST RESULTS: not applicable (docs only).

VALIDATION RESULTS:
- The remaining "25.00" hits are history lines (38, 42), the firm limit (294), the human's verbatim quotes (460, 863) and "was 25.00" notes (460, 889).
- The "no R-b" hits are history or superseded notes.
- No 12-digit literals. No new links were added.

ASSUMPTIONS:
- The 37/50-min load variants, the 45-min IAM window 2 and the 15-min C5b-C9 come from the plan or are estimates.
- $S2WORK is the planned stage-a B8.6 work directory, which the plan does not fix yet.

RISKS:
- The fallback probably does not fit if both S runs fail late, unless batched ingest is about 5 vectors/s or faster.
- Retention depends on a P6 harness that does not exist yet.
- Schema identity is unverified.

MANUAL ACTION REQUIRED:
- The human reads the credit balance (it must be at least 6.72).
- The human decides what happens if the fallback does not fit the clock.
- The coordinator writes the P6 harness brief with the retention requirements above.

BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: code-reviewer read of section 4a, step 7b and the P6 row; then the human signs the P19 record.

#### Agent report (2026-11-16T15:17:53.101Z, agent a7fa645)

STATUS: COMPLETE for lane A (P22, P23, P25, P1, P5, plus the coordinator add-ons P7 bootstrap retry, deployer comment and the tfvars-example hash). Some items are BLOCKED-ON other owners: 4 test-engineer tests fail on the new pins (expected), 1 frozen Terraform test still has the old hash, and 3 documentation sites are stale. Details are in the BLOCKED-ON fields below.

OWNER: infra-engineer (pipeline lane A, relaunch). Nothing was committed or stashed. No AWS call was made and no terraform plan or apply was run.

WORK ORDER: /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/briefs/lane-A.txt, with the UPDATES of 2026-11-16 08:40 and the three coordinator messages (lane C values, the P7 add-on, the pin follow-up). Progress log: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/lane-A-progress.md (git-ignored, 8 entries).

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_phase15_pipeline_pins.py: 16 tests in 3 classes (HadoopRecordCeilingTests, CopyOutTests, LedgerCapTests).
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_upload_emr_hadoop_config.py: 8 tests.

FILES MODIFIED (absolute paths under /Users/danny/Documents/UIC/CS441/ScholarChain/):
- scripts/config/release.conf
  - L190-194 (P5): exact teardown address `terraform_data.phase12b_guard` appended to CLEANUP_TEARDOWN_ADDRESS_RULES.
  - L227-233 (P25): EMR_MAX_LIVE_RUNS=4 and EMR_CUMULATIVE_CAP_USD=3.36. The comment cites docs/agent-runs/phase-15/prompt.md line 131 as the approval. The run order stays an operator rule; no script logic was added.
  - L300-306 (P23): PIPELINE_MAX_COPYOUT_BYTES=8589934592.
  - L307-312 (P22): PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS=60000.
- scripts/emr/sc-step.sh L333-408 (P23):
  - New `copyout_rules` and `copyout_keep`; `body_copy_out` rewritten.
  - Hadoop: excludes intermediate/ and export/, but keeps export/*/reject/*.
  - ER: drops subtrees, evidence.jsonl and audit-details.jsonl.
  - spark, results and config are copied whole, event logs included.
  - One filter table drives the size count, the sha256 manifest and the `aws s3 cp --exclude/--include` arguments. Uploads add `--no-follow-symlinks`.
  - The ceiling now counts the selected bytes only, not `du -sk` of whole parts.
- scripts/emr/bootstrap.sh L21-22, L41 and L300-322 (P7): bounded EFS mount retry. At most 10 attempts with `sleep 15` between them (9 sleeps, 135 s), each attempt logged (EFS and access-point IDs only), then `die 5` after the last.
- infra/terraform/emr-step-programs.json: sc-step.sh sha256 ad7258d1221344de2b065bff18dc5d21356a1fb71b52e21dc52b47e499b99ed3 -> 376b3e15d1dba05f410f9b79b8d9f1ffa0387f305dd973244ce01dc4031edeaf. Regenerated with `python3 -I scripts/lib/pipeline.py step-manifest --write`; the other three hashes are unchanged.
- infra/terraform/environments/course.local.tfvars.example L226: the same sc-step.sh hash, old -> new. This was the only line changed; the elasticity edits are intact. The bootstrap line there is a placeholder with no value.
- infra/terraform/deployer/operator_pipeline.tf L12-14: the stale list-instance-groups comment was rewritten. The file was not in the uncommitted diff (`git diff --name-only HEAD -- infra/terraform/deployer/` printed nothing).
- scripts/upload-emr-artifacts.sh L16, L34-36, L111-131 and L211 (P1): `--hadoop-config FILE`.
- scripts/lib/upload_emr_artifacts.py L20-21, L28-29, L62-63, L324-325 and L403 (P1): CONFIG_OPTIONS and CONFIG_PIPELINE entries for hadoop-config.json / hadoop-config, plus the argparse option.
- scripts/tests/test_pipeline.py: L21-22 (constant 60000); the ledger tests at about L553-597 (4-run limit, 3.36 cap, fifth run refused); the copy-out filter strings at about L950-960; L1065-1069 (50003); L1084-1085 (4 / 3.36).
- scripts/tests/test_providers.py L177; scripts/tests/test_experiment.py L261-262 (4 live runs).
- scripts/tests/test_cleanup.py: new class CleanupGuardRuleTests, L449-497.
- scripts/tests/test_emr_bootstrap.py: new class EfsMountRetryTests, L498-553.
- Note: test_pipeline.py, test_experiment.py and test_providers.py are not dedicated to my scripts. I only edited the assertions that my pin changes broke; lane B may hold overlapping edits in test_pipeline.py.

COMMANDS RUN (results observed):
- `python3 -I -m unittest discover -s scripts/tests -p <file>`, all rc 0:

| File | Tests | Result |
|---|---|---|
| test_phase15_pipeline_pins.py | 16 | OK |
| test_upload_emr_hadoop_config.py | 8 | OK |
| test_pipeline.py | 69 | OK (274 s) |
| test_cleanup.py | 57 | OK |
| test_emr_bootstrap.py | 40 | OK |
| test_upload_emr_artifacts.py | 62 | OK |
| test_c1_step_args.py | 25 | OK |
| test_syntax.py | 20 | OK |
| test_budget.py | 38 | OK |
| test_aws_cli_shapes.py | 5 | OK |
| test_providers.py | 24 | OK |
| test_experiment.py | 39 | OK |

- Read-only runs of the test-engineer suites (`-s tests/scripts`):

| File | Result |
|---|---|
| test_pipeline_bodies.py | rc 0, 31 OK |
| test_bootstrap_13c.py | rc 0, 24 OK |
| test_upload_emr_artifacts_14b.py | rc 0, 35 OK |
| test_cap_pins_14b.py | rc 1, 2 failures |
| test_prespend_floors_14b.py | rc 1, 1 failure |
| test_pipeline_dryrun.py | rc 1, 1 failure (test_hadoop_and_er_step_forms) |
| test_pipeline_refusals.py | not run; it asserts 12000 at L127, L147 and L148 (by inspection) |

- `bash -n` and `shellcheck -x -P SCRIPTDIR` on sc-step.sh, bootstrap.sh, upload-emr-artifacts.sh and cleanup.sh: rc 0.
- Terraform ran on a scratch copy (/private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/tfcopy), because the shared root fails with "Module not installed" from the untracked phase15_elasticity_dashboard test.
  - Environment: the check.sh tfenv (AWS variables unset, config and credentials set to /dev/null).
  - `init -backend=false -input=false -lockfile=readonly -plugin-dir=<repo>/infra/terraform/.terraform/providers`: rc 0, offline. No `-upgrade` was used and the shared .terraform was not touched.
  - `test -filter=tests/phase13c.tftest.hcl`: rc 0, 37 passed, 0 failed.
  - `test -filter=tests/phase14a.tftest.hcl`: before the example refresh, rc 1 with 20 passed, 2 failed, 18 skipped. After the refresh, rc 1 with 21 passed, 1 failed (`emr_enabled_with_the_four_step_programs_of_the_example_is_accepted`), 18 skipped.
- `terraform fmt -check infra/terraform/deployer/operator_pipeline.tf`: rc 0. No recursive fmt was run.

TEST RESULTS: all owned suites pass (counts above). The new tests cover:
- P22: the inclusive ceiling at 50003 and at 60000, and refusal at 60001.
- P23: the selected set equals the aws-filter set under the real awscli fnmatch semantics; the ceiling counts selected bytes only; a refused copy-out makes no aws call; symlinks are neither counted nor copied.
- P25: runs 3 and 4 are reserved and run 5 is refused; 3.37 is refused and 3.36 is admitted; 0.84 is the script's own estimate.
- P1: the dry run prints the key and sha256 and an EMR-RENDER `hadoop-config` line; the execute path uploads and verifies.
- P5: a plan deleting phase12b_guard gets a token; rogue addresses and configuration_guard / provider_guard are refused.
- P7: the mount succeeds on attempt 1, 4 or 10; when it never succeeds the bootstrap exits 5 after 10 mounts and 9 sleeps.

VALIDATION RESULTS:
- Values the experiment-engineer must mirror (they match the coordinator's lane C message):
  - `maxLocalSampleRecords: 60000`.
  - `pipeline.hadoop_config` = `s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/config/hadoop-config.json`, with `artifact_sha256["hadoop-config"]`.
  - LABEL_RE accepts `size-l`.
- P22 derivation: L is at most 50000 DBLP works (TARGET_MAX; lane D reports 48,187) plus 3 other-source records (one non-empty line in each committed sample, verified) = 50003. 60000 gives about 20% headroom.
- P23 bound: from local sizes at 10,577 works, the selection is about 1.06 GB (Spark export 592 MB, event logs 462 MB, kept Hadoop and ER files under 1 MB). Scaled linearly that is about 5.0 GB at L; 8 GiB is about 1.7 x L. Without the selection, Hadoop (1.0 GB) and ER (757 MB) would add about 1.7 GB at S.
- P5 safe default: configuration_guard and provider_guard stay UNLISTED. They hold no AWS object, lane B's stage-a deltas treat them as kept residual state, and a plan that deletes them fails closed.
- The bootstrap has no repo pin. Its new sha256 is 2d90f3bc9538a6ac02fe4ccf6a0560e92eb41c026b6032394983e7c7b3905070; it reaches the private tfvars through the upload dry run's EMR-CONFIG line.

ASSUMPTIONS:
- Output sizes scale linearly with works.
- On EMR, Phase6Main writes uncompressed event logs under the Spark output root, as it does locally.
- The loaders and the report need only the Spark export plus the Hadoop counters, stats and rejects, and the small ER top-level files.
- The L input tree's other-source files are the committed samples.

RISKS:
- Copy-out reads each selected byte twice (sha256, then upload). EFS is in elastic throughput mode, which bills reads; the cost is unverified (roughly 10 GB read at L).
- The copy-out step gets 10% of runtime (540 s at 90 min). This is not measured at L; P6 should time it.
- The EFS mount has no per-attempt timeout (no `timeout` wrapper), so one hung mount is bounded only by the node shutdown timer.
- test_cap_pins_14b encodes the Phase 14B H0 arithmetic. With a 3.36 cap it gives (11.15+1.17+2.41+0.05+0.30+3.36+1.33+0.50) x 1.11 + 0.34 = 22.84 > 22.00. That formula predates Session 1 actuals; the coordinator's §6.3/6.4 check must stand in for it, and the Session 2 pre-spend receipt must reserve against the new cap.

MANUAL ACTION REQUIRED:
- The human copies the new sc-step.sh and bootstrap sha256 values from the upload dry run into the private tfvars before Session 2.
- An independent code-reviewer runs, then the human reviews.

BLOCKED-ON OWNER:
- test-engineer: tests/scripts/test_cap_pins_14b.py (L7, L13, L29, L47, L50), test_prespend_floors_14b.py (L279, L281), test_pipeline_refusals.py (L4, L127, L133, L147, L148, L168, L248-287), test_pipeline_dryrun.py (L190), sc_support.py (L45). They need 60000 / 4 / 3.36, and the H0 arithmetic needs a new decision.
- Coordinator, since the file is frozen: infra/terraform/tests/phase14a.tftest.hcl L474, replace ad7258d1221344de2b065bff18dc5d21356a1fb71b52e21dc52b47e499b99ed3 with 376b3e15d1dba05f410f9b79b8d9f1ffa0387f305dd973244ce01dc4031edeaf.
- Lane B: scripts/run-bounded-pipeline.sh help text L94 (12000 -> 60000) and L102-103 ((3) -> (4), (2.52) -> (3.36)).
- Owner to be assigned (infra-engineer by territory, but outside my brief):
  - scripts/README.md L315, L377, L395, L399 and L487 (old caps, ceilings and copy-out text).
  - infra/terraform/deployer/README.md L382 and deployer/tests/gdeployer.tftest.hcl L236, error-message text only (list-instance-groups).
- hadoop-engineer: confirm the SampleBound semantics in cluster mode (P22).

BLOCKED-ON EVIDENCE: the failing test names and counts listed under COMMANDS RUN; the phase14a error is "Resource precondition failed" at phase12b.tf:34.

NEXT GATE:
1. The coordinator routes the BLOCKED-ON edits.
2. `scripts/check.sh` runs on a clean worktree.
3. Independent code-reviewer, then human review.
4. Pins refresh and commit (only after the human's explicit yes).
5. P6 local dry run at S and L to measure copy-out bytes and time against 8 GiB and 540 s.

#### Agent report (2026-11-16T15:21:29.132Z, agent a930d31)

STATUS: COMPLETE for the storage change. The live speed-up is BLOCKED-ON rag wiring (see BLOCKED-ON).
OWNER: storage-engineer
WORK ORDER: Phase 15, lane G (ingest throughput), branch phase-15, HEAD 7a02de2, main tree. P26 (b) storage side. Offline only; no AWS, Voyage or Anthropic calls; no commit and no stash. The P38 patch is intact.

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/IngestThroughputFixture.scala (fakes. The real RowRunLedger and RowArtifacts sit on metered MemoryRows, the real S3VectorStore uses a proxy client, the S3 text store is metered, and a lookahead-embedder emulation stands in for rag's. Every latency has its provenance labelled in the file.)
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/IngestThroughputSpec.scala (9 tests)

FILES MODIFIED:
- .../storage/EmbeddingManifest.scala:
  - New key `EmbeddingIngestConfig.ingestConcurrency` (default 1; valid range 1..16; `MaxIngestConcurrency = 16`; anything else fails with `invalid-ingest-concurrency`).
  - The runner's per-item work is split out into prepareItem, bindGroup and writeBatch.
  - With concurrency 1 the run stays sequential, with the same call order as before.
  - Above 1, group binding and item work run on bounded daemon threads. Every ledger call is serialized by one lock, vector puts are batched per index by `batchSize`, and rejections are sorted by manifest position.
- .../storage/StorageRows.scala: `RowRunLedger.recordStage` and `completeStage` reuse the stage row they already read, so each transition costs 3 DynamoDB calls instead of 4. The transaction conditions are unchanged.
- .../storage/ToolLoggingSpec.scala (P38): one-line race fix. The log list is now copied under the appender's monitor. The previous copy threw ConcurrentModificationException in storage-test-1.log.

KEY FINDING (code read, then confirmed by tests): every ledger transition rewrites the RUN root row under an optimistic revision check. Ledger calls within one run therefore cannot run concurrently. They must be serialized, and that sets the throughput floor.

PER-ITEM CALL TABLE (fresh item; observed in IngestThroughputSpec; before -> after):
| Step | Calls | Can it overlap? |
|---|---|---|
| Group binding | registry GetItem 2 + PutItem 1 | yes, concurrent across groups |
| ledger recordStage | GetItem 3->2, TransactWriteItems 1 | no, serialized (root revision) |
| Binding/complete/prepared checks | registry GetItem 3, PutItem 1 | yes |
| S3 text + prepared vector | PutObject 2 | yes |
| Embed | 1 request per batch (rag lookahead) | serialized by rag's lock; each text sent once |
| Save prepared | registry PutItem 1 | yes |
| S3VectorStore.putBatch, per document | registry PutItem 3 + GetItem 1 | yes, across batches |
| S3VectorStore.putBatch, per batch | PutVectors 1 per batchSize | already batched per index |
| Runner completion | registry PutItem 1 | yes |
| ledger completeStage | GetItem 3->2, Transact 1 | no, serialized |

- Total per fresh item: 21 -> 19 DynamoDB calls plus 2 S3 PUTs. Ledger share: 8 -> 6.
- Per unchanged item: 13 -> 11 DynamoDB calls.
- Per run: startRun, getRun, completeRun (2 PutItem, 2 Query, 3 GetItem).
- With 8 workers the storage call counts are exactly the same.

LIVE TIME FOR 10,000 ITEMS (latency fake at 1/20 scale; pause calibration 2.720 -> 2.724 ms):
- Latency assumptions:
  - L = 54.4 ms per DynamoDB or S3 call. DERIVED from Session 1 ingest-2.log (95 written + 9 unchanged in 154.52 s) and the before-change call profile. It assumes 0.30 s per single-text Voyage call, which was not measured.
  - PutVectors 141 ms. MEASURED proxy: the Session 1 query p50 in query-smoke.log.
  - Voyage 2.0 s per batch. ASSUMED.
- BEFORE (code as it stood, rag batching in place): 0.760 vectors/s, about 219 min.
- AFTER, one worker (ledger change only): 0.804-0.810 vectors/s, about 206 min.
- AFTER, 4 workers: 2.125-2.134 vectors/s, about 78 min.
- AFTER, 8 workers: 2.457-2.461 vectors/s, about 68 min. This is a linear projection from 400 items and includes start and end overheads.
- Ledger-bound floor: 3.064 vectors/s, 54.4 min.
- Sensitivity: L ranges from 46.1 to 66.8 ms if single-text Voyage latency is 0.5 s or 0 s. The 8-worker estimate then ranges from about 57 to 83 min, still under 90.

CONFIG FOR SESSION 2 (once rag wires it): `ingestConcurrency = 8`, `batchSize = 100` (unchanged), approval `concurrencyCap >= 8`. Per rag's own note, `maxManifestBytes` must be set explicitly for about 20.5 MB.

COMMANDS RUN (each `sbt -batch` ran on JDK 17.0.20.1 with JAVA_HOME and SBT_OPTS set as ordered; logs in target/phase15/lanes/lane-G/):
1. `storage/testOnly ...IngestThroughputSpec` -> exit 1, 1/2 passed (fixture text-selection bug; before-measure.log)
2. same with `-z latency` -> exit 1 (diagnostic run; before-measure-2.log)
3. same -> exit 0, 2/2, uncalibrated (before-measure-3.log)
4. same -> exit 0, 2/2, calibrated BEFORE measurement (before-measure-4.log)
5. `storage/scalafmt storage/Test/scalafmt storage/Test/compile` -> exit 0 (compile-1.log)
6. `storage/test` -> exit 1, 152/153; the failure was the ToolLoggingSpec race, now fixed (storage-test-1.log)
7. `storage/Test/scalafmt` + `testOnly IngestThroughputSpec` -> exit 1, compile error from a StorageConfig name clash (new-spec-1.log)
8. same -> exit 1, 8/9; my determinism expectation was wrong (new-spec-2.log)
9. same -> exit 0, 9/9 (new-spec-3.log)
10. GATE `storage/scalafmtCheck storage/Test/scalafmtCheck storage/test rag/test` -> exit 0 (gate-1.log)
11. Extra: `independentTests/testOnly *Embedding* *Runtime9BSemantic*` -> exit 0 (independent-1.log)

TEST RESULTS:
- Gate: both format checks passed; storage 160/160; rag 245/245.
- Extra: independent tests 40/40 in 9 suites.

VALIDATION RESULTS (all observed under 8 workers unless noted):
- Concurrency safety (300 items): 300 keys, each written once; 600 distinct S3 objects; each text embedded once; 300 ledger stages complete with 0 retries and no failures; root revision 601 = 2n+1, so no transition was lost.
- Determinism: one worker, 8 workers and 8 workers again give identical reports (except elapsed time) and identical vector payloads.
- Crash mid-run, then resume with a fresh run ID: all 300 items complete, with no re-embedding and no double write.
- Provider failure mid-run, then resume: only the 200 rejected items are embedded again.
- Caps: `manifest-item-limit` is refused with zero port calls. A client-side embedding cap of 37 gives 37 written and `embeddingCalls` 37, under both 1 and 8 workers.
- Ledger paging: default config refuses 10,000 stages; 9,999 pass; `queryPageSize` 1000 passes.

ASSUMPTIONS:
- The latencies are labelled above.
- The dollar and `maxEmbeddingCalls` caps are rag preflight bounds over the manifest. Concurrency does not change them, because each item still calls embed at most once.
- The later-duplicate branch cannot be reached after group binding (vectorKey = the group-key fields plus the ordinal). I kept it for parity with the sequential path.

RISKS:
- L is derived, not measured.
- Voyage RPM/TPM tier is still unknown (P26 c). Under concurrency the lookahead batcher may send a few extra requests (emulation: 8 -> 13 requests for 400 texts), but each text is still sent once.
- With a stateful global cap, which items succeed depends on scheduling; the counts do not.
- Rejection order is encounter order with 1 worker and manifest order above 1.
- My edits trigger a format hook that runs sbt on Homebrew Java 27 and prints subproject path errors. These are artifacts of the hook; the gate ran on JDK 17.

MANUAL ACTION REQUIRED: none in storage. After rag wires the change, the human sets the Session 2 config values above.

BLOCKED-ON OWNER: rag-engineer (modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingIngestMain.scala and LookaheadBatchingEmbeddingClient.scala)
BLOCKED-ON EVIDENCE:
(1) The new key is not reachable from the live tool, which stays sequential at about 3.4 h. Required change: add `ingestConcurrency: Int = 1` to LiveEmbeddingConfig, with `require(1 <= ingestConcurrency <= EmbeddingIngestConfig.MaxIngestConcurrency)`; pass `ingestConcurrency = ingestConcurrency` in `def ingest`; refuse in preflight when `config.ingestConcurrency > approval.concurrencyCap`; add it to the report.
(2) A clean 10,000-item run fails at `completeRun` (query-page-limit, which surfaces as `run-ledger-completion-failed`) after every vector is written, and a rerun fails the same way. This is shown by the ledger paging test. Required change: in awsPorts, `StorageConfig(config.textBucket, config.tables, retry = RetryConfig(maxAttempts = 1), queryPageSize = 1000)`.
(3) Doc only: LookaheadBatchingEmbeddingClient says "the runner calls from one thread". It can now be called from up to ingestConcurrency threads. It is safe because calls are serialized by its lock; consider a rag test with concurrent callers.

NEXT GATE: code-reviewer review of the modules/storage diff; then the rag-engineer change and rag tests; then the human sets the config and approves the Session 2 concurrencyCap.

#### Agent report (2026-11-16T15:27:16.457Z, agent af8f024)

STATUS: DONE. All three follow-up items are done. The 10,000-item `completeRun` bug is fixed and covered by a test that reproduces it. The gate passed: exit 0, rag 251/251 and storage 160/160.

OWNER: rag-engineer (Lane E follow-up after lane G's storage change)

WORK ORDER: the coordinator's follow-up: (1) `ingestConcurrency`, (2) the 10,000-item `completeRun` bug with `query-page-limit`, (3) the batcher's concurrency doc and a test with concurrent callers, then the gate.

FILES CREATED: none new in this delta.

FILES MODIFIED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingIngestMain.scala
  - (1) New field `ingestConcurrency: Int = 1` on `LiveEmbeddingConfig`:
    - checked to be between 1 and `EmbeddingIngestConfig.MaxIngestConcurrency` (16), error code `invalid-ingest-concurrency`
    - passed into `def ingest`
    - preflight refuses `ingestConcurrency > approval.concurrencyCap` with the typed reason `live-approval-ingest-concurrency-cap`
    - the live report gains an `"ingestConcurrency"` key
  - (1) The JSON reader limit you warned about did come back. Adding the field directly breaks `derives ReadWriter`. I used neither a nested sub-object nor a split config. Instead I removed `derives ReadWriter` and added a companion `implicit val readWriter = ReadWriter.join(macroR[LiveEmbeddingConfig], macroW[LiveEmbeddingConfig])`: reader and writer are derived separately, with the same field names, defaults and omission rules. A round trip is tested, and an old config without the key still reads as 1. The pre-change file is backed up at /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/LiveEmbeddingIngestMain.scala.bak
  - (2) New `LiveEmbeddingConfig.storageSettings` = `StorageConfig(textBucket, tables, retry = RetryConfig(maxAttempts = 1), queryPageSize = 1000)`, and `awsPorts` uses it. The storage API needed no other change; `maxQueryPages` stays at 100, so the ledger can read up to 100,000 rows. `validateManifest` now refuses with `live-ledger-page-capacity` when the items plus the root row would not fit.
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LookaheadBatchingEmbeddingClient.scala: (3) the class doc now covers concurrent workers. All calls run under one lock, so each text is still sent at most once, and a worker waits for a batch already in flight. Embedding requests are never concurrent with each other, while the S3 and DynamoDB work still overlaps.
- /Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Phase15IngestBatchingSpec.scala: 6 new tests, 18 in this suite now:
  - 16 concurrent threads, 1,000 texts, batch 50: each text is sent once and every vector is correct
  - `ingestConcurrency` limits, pass-through, round trip and the old-key default
  - preflight refuses `ingestConcurrency` 8 with `concurrencyCap` 4 and accepts it with 8
  - the storage settings, plus a check that the default 100 × 100 pages cannot hold 10,001 rows
  - the real `DynamoRunLedger` over a fake DynamoDB client with real query paging and conditions: 10,000 items at `ingestConcurrency` 8 finish with the run `complete`
  - control: the storage default page size gives `Left("run-ledger-completion-failed")`, which reproduces the bug
- Progress log: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/lane-E-progress.md (follow-up section appended)

COMMANDS RUN (JDK 17 with the SBT_OPTS logback file):
1. `sbt -batch "rag/compile"`, a trial of the split reader/writer: success.
2. `sbt -batch "rag/scalafmt" "rag/Test/scalafmt" "rag/testOnly edu.uic.cs441.scholarchain.rag.Phase15IngestBatchingSpec"`, first attempt: exit 1, an ambiguous `StorageConfig` import. Fixed with fully qualified names.
3. The same command again: exit 0, 18/18 passed.
4. `sbt -batch "rag/scalafmtCheck" "rag/Test/scalafmtCheck" "rag/test" "storage/test"`: exit 0. Log: /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/laneE-gate2.log

TEST RESULTS:
- rag: 251 of 251 passed, 20 suites
- storage: 160 of 160 passed, 18 suites
- both format checks passed

VALIDATION RESULTS: with the fake DynamoDB ledger that pages like the real one, 10,000 items at `ingestConcurrency` 8 ran at 4267.4 vectors/s (local fake only). Other fake figures from this run: batchSize 1 gave 78.1 v/s, batchSize 100 gave 2140.8 v/s, and 10,000 items with no fake latency gave 3476.6 v/s.

Session 2 config keys:
- live config: `"ingestConcurrency": 8`, `"batchSize": 100`, `"maxManifestBytes": 33554432`, `"maxVectors": 10000`, `"maxEmbeddingCalls"` ≥ 20000
- approval: `"concurrencyCap"` ≥ 8 (it also has to cover `maxConcurrentCalls`), `"vectorCap"` ≥ 10000, `"embeddingCallCap"` ≥ 20000
- render config (unchanged from the earlier report): `maxSummaries` 9996, `maxTopicNodes` 10, `maxInstitutionNodes` 10, `maxScannedRows` 200000, `maxManifestItems` 10000, `maxManifestBytes` 33554432

ASSUMPTIONS:
- A DynamoDB page of 1,000 ledger rows stays under the 1 MB page cap. If DynamoDB cuts pages at 1 MB instead, the reader just takes more pages, still within 100.
- The fake DynamoDB client only models what `DynamoRows` uses: get, put, transact and query with conditions.

RISKS:
- Embedding requests are serialized under the batcher's lock. At batchSize 100 that is about 100 requests for 10,000 items, which is small next to lane G's estimated 54-68 min ledger-bound run time. This is not measured live.
- The full `sbt check` was not run.
- Everything here depends on lane G's uncommitted storage changes (`ingestConcurrency`, ledger, `ToolLogging`), so it should be committed with or after them.

MANUAL ACTION REQUIRED: the human sets the config and approval keys listed above.

BLOCKED-ON OWNER: none.

BLOCKED-ON EVIDENCE: live throughput and the real ledger row sizes are unverified.

NEXT GATE: the coordinator runs `sbt check`, then the code-reviewer covers the rag and storage diffs together, then the commits go in, storage first.

#### Agent report (2026-11-16T15:36:06.878Z, agent a093722)

DELTA REPORT for the follow-up on lane A's pin changes (lane B, infra-engineer). All four items are done and the Terraform tests you asked for pass. Two test suites outside my files now fail on lane A's new values or wording; none of those failures comes from my edits. Nothing was committed and no AWS call was made.

STATUS: DONE. The two follow-ups below go to lane A and the test-engineer.

1. Pin in phase14a
- infra/terraform/tests/phase14a.tftest.hcl L474: replaced the sc-step.sh hash ad7258d1… with 376b3e15d1dba05f410f9b79b8d9f1ffa0387f305dd973244ce01dc4031edeaf. `terraform fmt -check` on that file: exit 0.
- `terraform test -filter=tests/phase14a.tftest.hcl` in the scratch root: Success! 40 passed, 0 failed, exit 0.
- You expected 22; the file actually has 40 runs. The earlier "20 passed, 2 failed, 18 skipped" counted runs skipped after the failure.
- My scratch root now mirrors the repository layout and also copies deployer/*.tf, deployer/boundaries and deployer/tests, still without state or local tfvars. phase14a reads deployer/phase14_main.tf, so the older copy could not run it. Script: /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/laneB/tftest3.sh

2. Help text in scripts/run-bounded-pipeline.sh
- L94: 12000 → 60000. L102: (3) → (4). L103: (2.52) → (3.36).
- No test under scripts/tests checks this help text.
- tests/scripts/test_pipeline_refusals.py:127 does check "maxLocalSampleRecords<=12000", but in the `PLAN: ceilings:` output line, which comes from release.conf. See the follow-ups.

3. scripts/README.md
- Edited L315, L377, L395 (two places), L399 (three places) and L487 to lane A's values:
  - 4 runs and USD 3.36, citing the approval at prompt.md line 131;
  - a 60000-record ceiling (it was 12000);
  - an 8 GiB copy-out ceiling, separate from the 256 MiB input ceiling;
  - the selective copy-out set as in sc-step.sh L333-408: hadoop without intermediate/ and without the export except its rejects, er with only its top-level files, and all of spark, results and config.
- Not on your list and still saying "three-run and USD 2.52 caps": L401 and L407. I left them; tell me if you want them changed.

4. Deployer wording
- infra/terraform/deployer/README.md L382 and deployer/tests/gdeployer.tftest.hcl L236 (error_message only): removed the list-instance-groups mention.
- `terraform fmt -check` on gdeployer: exit 0.
- `terraform test -filter=tests/gdeployer.tftest.hcl` in the scratch deployer root: Success! 13 passed, 0 failed, exit 0.

PYTHON SUITES (AWS env unset):
- scripts/tests, eight modules (test_plan_deltas, test_stagea_apply_path, test_aws_cli_shapes, test_syntax, test_plan, test_runtime_base_apply, test_pipeline, test_13c_pipeline): Ran 247, FAILED (failures=1).
- My six modules passed, 148 tests. A rerun of test_pipeline and test_13c_pipeline alone gave Ran 99, 1 failure, exit 1.
- The failure is `test_13c_pipeline.CopyOutPartialRunTests.test_a_real_find_error_still_fails_with_a_marker_and_copies_nothing`. It expects "could not build the copy-out manifest", but lane A's new selective copy-out in sc-step.sh now stops earlier with "STEP-FAIL copy-out: could not list <part>". The step still fails as it should; only the message changed.
- tests/scripts/test_pipeline_refusals.py (test-engineer's file, run read-only): 5 failures, all because of lane A's release.conf values:
  - the ceiling one-above case (value 12001 is now accepted);
  - only_the_sample_record_ceiling_differs (60000 != 12000);
  - pinned_ceiling_values (expects <=12000);
  - cumulative_total_above_the_cap (the 2.52 cap is now 3.36);
  - fourth_run_is_refused (the fourth run is now allowed).

FOLLOW-UPS (not my files):
- Lane A: update test_13c_pipeline L268 to the new message, or keep the old message in sc-step.sh.
- test-engineer: update tests/scripts/test_pipeline_refusals.py to 60000, 4 runs and 3.36.

PROGRESS LOG: target/phase15/lanes/lane-B-progress.md, entry 8.

NEXT GATE: independent code review of these edits, then a full check.sh run once lane A and the test-engineer have updated those tests.

#### Agent report (2026-11-16T15:43:57.100Z, agent a7fa645)

STATUS: COMPLETE (delta report for the coordinator's follow-up). The stale test is updated, both README lines now say 4 runs / USD 3.36, and test_pipeline and test_13c_pipeline both pass.

OWNER: infra-engineer, lane A.

WORK ORDER: coordinator follow-up after report 1: (1) the test_13c_pipeline find-failure test; (2) scripts/README.md L401 and L407.

FILES CREATED: none.

FILES MODIFIED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_13c_pipeline.py L268-270, in `CopyOutPartialRunTests.test_a_real_find_error_still_fails_with_a_marker_and_copies_nothing`.
  - It now expects `STEP-FAIL copy-out: could not list <run_root>/results`, matching the selective copy-out, which fails at the listing stage.
  - It also checks that no `copyout-manifest.sha256` is written.
  - The intent is unchanged: the step exits nonzero with a marker and makes no `s3 cp` call.
  - I chose to update the test rather than restore the old message, so sc-step.sh is unchanged (its sha256 is still 376b3e15d1db…). No pin refresh is needed in emr-step-programs.json, tfvars.example L226 or phase14a L474.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/README.md L401 and L407: "three-run and USD 2.52 caps" became "four-run and USD 3.36 caps". L401 also cites the approval at docs/agent-runs/phase-15/prompt.md line 131.

COMMANDS RUN:
- `python3 -I -m unittest discover -s scripts/tests -p 'test_13c_pipeline.py'`: rc 0, Ran 30, OK.
- `python3 -I -m unittest discover -s scripts/tests -p 'test_pipeline.py'`: rc 0, Ran 69, OK (310 s).
- `shasum -a 256 scripts/emr/sc-step.sh`: 376b3e15d1dba05f…, unchanged.
- No sbt run.

TEST RESULTS: both suites pass (above).

VALIDATION RESULTS: sc-step.sh still matches the pin in emr-step-programs.json. The earlier Terraform results stand: phase13c passes 37/37, and phase14a still fails 1 run, waiting on its frozen L474 hash.

ASSUMPTIONS: none new.

RISKS: none new. The other stale scripts/README.md lines from report 1 (L315, L377, L395, L399, L487: old caps, ceilings and copy-out text) were outside this order and are not edited.

MANUAL ACTION REQUIRED: none new.

BLOCKED-ON OWNER: unchanged from report 1:
- test-engineer: the tests/scripts pin tests.
- Coordinator: phase14a.tftest.hcl L474.
- Lane B: the run-bounded-pipeline.sh help text.
- Owner to be assigned: the remaining scripts/README.md lines and the deployer README and test messages.

BLOCKED-ON EVIDENCE: as in report 1.

NEXT GATE: the coordinator's `scripts/check.sh` and `sbt check` on a clean worktree, then independent code review and the human's review. The progress log has a matching entry: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/lane-A-progress.md.

#### Agent report (2026-11-16T16:08:22.939Z, agent a54f56f)

STATUS: COMPLETE. The pin refresh is done and the gate passed. There is one BLOCKED-ON item, and it comes from another lane, not from lane A.
OWNER: test-engineer
WORK ORDER: Phase 15 pipeline lane A pin refresh. Bring the tests under tests/scripts in line with P25, P22 and P23. Re-express H0 under the Phase 15 rule. Add a new independent copy-out test. Run tests/infra.

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts/test_copyout_selection_15.py (3 tests):
  - the copy-out ceiling pin is 8589934592 (8 GiB), and the input ceiling stays 268435456.
  - Black-box run of sc-step.sh copy-out: the body comes from the dry run of the real pipeline script and runs against the existing Harness and fakes. The fixture tree copies a real local Hadoop layout.
    - The manifest lists exactly the kept files, each with its sha256. It includes `export/snapshot=*/run=*/reject/*`, including the maxLocalSampleRecords reject file. It has no `intermediate/` file and none of the record export, match-candidate or work files.
    - The hadoop `aws s3 cp` argv selects the same set when judged by AWS CLI filter rules (last match wins, `*` matches `/`). It carries `--recursive` and `--no-follow-symlinks`.
    - The logged byte count equals the selected bytes.
  - The ceiling counts selected bytes only: ceiling = kept bytes is accepted, kept - 1 is refused before any `s3 cp`. The dropped bytes are larger than the kept bytes, and the rejects count.
  - Mutation check, run on fixture copies only (helper script /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/mutate_copyout.py). Three mutants, all KILLED (2 of 2 tests fail each): no reject include, intermediate kept, size everything.

FILES MODIFIED (old -> new):
- tests/scripts/sc_support.py L45: `"maxLocalSampleRecords": 12000` -> 60000, plus a 2-line history comment (12000 under G-MAIN; 50003 = L + 3).
- tests/scripts/test_pipeline_dryrun.py L190: `"12000 8 256 ..."` -> `"60000 8 256 4096 64 8388608 8388608"`, plus a comment.
- tests/scripts/test_prespend_floors_14b.py:
  - L279: EMR_CUMULATIVE_CAP_USD 2.52 -> 3.36, plus a comment citing prompt.md:131.
  - L281: EMR_MAX_LIVE_RUNS 3 -> 4.
- tests/scripts/test_pipeline_refusals.py:
  - L4 docstring: 3 runs / 2.52 -> 4 runs / 3.36 (history kept).
  - L127: `maxLocalSampleRecords<=12000` -> `<=60000`.
  - L141-142 docstring updated.
  - L147-148: 12000 -> 60000, plus a new check that the ceiling is >= 50003 (the largest L slice fits).
  - The boundary +1 test is driven by S.CEILINGS, so it now checks that 60000 is accepted and 60001 refused.
  - G6 class docstring L172 updated.
  - test_fourth_run_is_refused (4th refused, 3 x 0.10 in the ledger) -> test_fifth_run_is_refused: 4 x 0.10 is refused, the dry run reports it, the result contains "4", nothing is reserved.
  - test_two_recorded_runs_still_allow_a_third -> test_three_recorded_runs_still_allow_a_fourth (ledger ends with 4 reservations).
  - NEW test_session_2_s_then_l_fit_after_session_1_and_a_fifth_run_does_not. The 2 x m5.xlarge, 90-min estimate is 0.84.
    - Ledger [0.84, 0.84] -> allowed.
    - Ledger [0.84 x 3] -> 3.36 exactly, allowed.
    - Ledger [0.84 x 4] -> refused.
    - Ledger [0.84, 0.85, 0.84] -> 3.37, refused (cumulative).
  - Cumulative boundary test, old -> new:
    - default run: 0.96+0.96 / 0.96+0.97 -> 1.38+1.38 allowed / 1.38+1.39 refused.
    - old-world ledger 1.20+1.20 (refused) -> the 2.53 ledger is now allowed.
    - mid run: 1.26 / 1.27 -> 2.10 allowed / 2.11 refused.
    - big run 2.88: an empty ledger was refused, now allowed; 0.48 allowed / 0.49 refused.
- tests/scripts/test_cap_pins_14b.py:
  - Docstring L1-14 rewritten: P25 text, and the old H0 formula `(11.15+1.17+2.41+0.05+0.30+2.52+1.33+0.50) x 1.11 + 0.34 = 21.9073 <= 22.00` kept as history.
  - EMR_RUNS 3 -> 4; EMR_CAP 2.52 -> 3.36; added SESSION_1_RUNS = 2.
  - Pin "2.52" -> "3.36"; the three-runs test -> four live runs ("4").
  - NEW test: 2 runs left after Session 1; 3.36 - 1.68 = 2 x 0.84; a third Session 2 run gives 4.20 > 3.36.
  - The defined-once check now covers both keys.
  - **The H0 terms no longer match the Phase 15 plan** (a 36 h Phase 14B session plan with 0.34 spent; Session 1 has been spent since then). Re-expressing them at x1.00 gives 20.27 + 0.34 = 20.61, which guards nothing real. So H0ReceiptArithmetic was replaced by Phase15ProjectArithmetic, which uses the session-2-plan.md 6.2-6.4 figures as hand-copied constants and does not read the plan file:
    - factor 1.00; limit 25 - 2 = 23.00; spent 15.75 + 0.075 = 15.83; S = 7.17.
    - R0 + R-b cap 3.57 + 3.57 = 7.14; project at caps 22.97 <= 23.00 (margin 0.03); AWS cap 6.72.
    - The EMR block is (2 x 105 + 20) / 60 = 3.83 h x 0.50 = 1.92. The ledger allowance 3.36 - 1.68 = 1.68 fits inside both 1.92 and the R0 cap.
    - The dropped column B would give 17.56 + 1.11 x 6.72 + 0.42 = 25.44 > 25.

COMMANDS RUN (all offline, repo root):
1. `python3 -I -m unittest discover -s tests/scripts -p 'test_*.py'` before my edits (baseline): Ran 463, FAILED (failures=9), 1363.0 s. All 9 failures are the expected pin failures: cap_pins 2, dryrun 1, refusals 5 (including subtest maxLocalSampleRecords=12001), prespend 1.
2. Single-module runs after the edits, all OK:
   - test_cap_pins_14b.py: Ran 13
   - test_copyout_selection_15.py: Ran 3
   - test_pipeline_dryrun.py: Ran 16
   - test_prespend_floors_14b.py: Ran 29
   - test_pipeline_refusals.py: rc 0, Ran 59
3. `python3 -I -m unittest discover -s tests/scripts -p 'test_*.py'` after the edits: **rc 0, Ran 468, OK**, 1298.8 s.
4. `python3 -I -m unittest discover -s tests/infra -p 'test_*.py'` (15:28:03Z-15:45:10Z): **rc 1, Ran 465, FAILED (failures=1)**.
5. `python3 -I <scratchpad>/mutate_copyout.py` on fixture copies: 3 of 3 mutants killed.
6. Read-only greps, git diff and git status.

Note: the harness moved the long runs to the background after 180 s. I waited for each one to finish, and none of mine is still running.

TEST RESULTS:
- tests/scripts: 468 run, 468 passed.
- tests/infra: 465 run, 464 passed, 1 failed. The failure is test_billing_replan_14b.NoRealAccountIdIsAdded:
  - It flags lines 164 and 182 of the untracked file modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Phase15VectorScaleSpec.scala. Both are a 12-digit literal inside a "scholarchain-course-rag-<12 digits>-us-east-<n>" bucket name.
  - I did not view or record the digits.
  - No tests/infra failure is caused by lane A's pins.

VALIDATION RESULTS:
- I made no production edits. My only changes are under tests/scripts.
- No 12-digit literal was added (grep count 0).
- No AWS, Anthropic, Voyage or sbt call. No commit, no stash.
- Progress log: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/test-pins-progress.md

ASSUMPTIONS:
- The Phase 15 rule (factor 1.00, limit 23.00) replaces both the Phase 14B 22.00 limit and the "≤ USD 22" condition from P25, as the later option (i) and tax decisions say.
- The plan's 6.2-6.4 figures come from an untracked draft read on 2026-11-16.
- Session 1's ledger of 2 x 0.84 = 1.68 comes from the coordinator check in prompt.md. I did not read the ledger itself.

RISKS:
1. The human's P25 text says "Confirm the project worst case stays ≤ USD 22". Under option (i) the worst case is 22.97: inside 23.00, but above 22. Recommend the human confirm that 23.00 replaces 22.
2. PRESPEND_MIN_HEADROOM_USD is still 3 in release.conf, while the plan floor is 2. Lane A did not change this, and the test still asserts 3. Not verified against the plan's intent.
3. The Haiku shared cap stays pinned at 1.33, while the plan's cap uses Anthropic 0.10. The plan says no answers run in R0 or R-b.
4. The ER copy-out rules (`*/*/*` excluded) are not covered by my new test.

MANUAL ACTION REQUIRED: The human should confirm that 23.00 supersedes the "≤ USD 22" condition in P25.

BLOCKED-ON OWNER: rag-engineer (modules/rag/** including src/test), routed through the orchestrator.

BLOCKED-ON EVIDENCE: The tests/infra test_billing_replan_14b account-ID guard fails on lines 164 and 182 of the untracked file modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Phase15VectorScaleSpec.scala (12-digit literal, category account-id-literal). The fix is to use a non-account placeholder or build the value at run time. Then rerun `python3 -I -m unittest discover -s tests/infra -p 'test_*.py'`.

NEXT GATE: An independent code-reviewer of the tests/scripts diff and the new file. Then the bundle's `sbt check` and clean-copy check.sh, run by the coordinator (not run here because sbt was forbidden). After the rag fix, rerun tests/infra.

#### Agent report (2026-11-16T16:09:31.663Z, agent af8f024)

Fixed `/Users/danny/Documents/UIC/CS441/ScholarChain/modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Phase15VectorScaleSpec.scala` with test-only edits. The flagged bucket names at lines 166 and 184 now use `syntheticBucket` (line 20), which is built at run time from `"0" * 12` and keeps the same length. I also replaced the decimal 3.4166666666666665 (a third 12-digit run, not flagged) with `${41.0 / 12}`, which gives the same text, so the byte figures should not change.
`python3 -I -m unittest discover -s tests/infra -p 'test_billing_replan_14b.py'` passed (33 tests, OK), a grep finds no 12-digit run left, and no line is over 100 columns; I did not run sbt, so compile, scalafmt and the rag tests are still unchecked until your final gate.

#### Agent report (2026-11-16T16:17:58.923Z, agent a7fa645)

STATUS: COMPLETE for the change in my own files. The headroom floor is now 2 and my own tests pass. Lane B's test_deploy.py now has 9 failures (5 test methods) because of the new floor; it needs lane B's edits, and some test-engineer tests need edits too (listed below).

OWNER: infra-engineer, lane A.

WORK ORDER: coordinator follow-up 2. Set PRESPEND_MIN_HEADROOM_USD from 3 to 2, per the human's decision recorded in docs/agent-runs/phase-15/prompt.md L185-190 ("R-b option decision", option (i): "Update the plan to floor 2 / project ≤ 23.00").

FILES CREATED: none.

FILES MODIFIED (all under /Users/danny/Documents/UIC/CS441/ScholarChain/):
- scripts/config/release.conf L59-63: `PRESPEND_MIN_HEADROOM_USD=2`. The comment cites the decision, keeps "the floor was 3" as history, and gives the reason: at R0 + R-b caps the project total is 22.97, which leaves 2.03 USD of headroom, and a floor of 3 would refuse that.
- scripts/tests/test_pipeline.py:
  - L483: the refusal case is now 1.99 ("below the 2 USD floor").
  - L494-499: the inclusive-floor test now accepts exactly 2.
- scripts/tests/test_providers.py L179-180: expects ("24", "2").
- scripts/tests/test_syntax.py L169: expects "2".

COMMANDS RUN (all `python3 -I -m unittest discover -s scripts/tests -p <file>`; no sbt):

| File | Result |
|---|---|
| test_pipeline.py | rc 0, Ran 69, OK |
| test_syntax.py | rc 0, Ran 20, OK |
| test_providers.py | rc 0, Ran 24, OK |
| test_verify_redact.py | rc 0, Ran 16, OK |
| test_state_records.py | rc 0, Ran 21, OK |
| test_experiment.py | rc 0, Ran 39, OK |
| test_deploy.py (lane B's file, run but not edited) | rc 1, Ran 157, 9 failures in 5 methods |

TEST RESULTS: as in the table. Every test_deploy failure comes from the floor change: the tests expect the text "3.0 USD", or expect 2.99 to be refused.

VALIDATION RESULTS: I grepped scripts/** for a hard-coded floor of 3. No logic hard-codes it; deploy.sh and run-bounded-pipeline.sh both pass `${PRESPEND_MIN_HEADROOM_USD}`. Only documentation text still says 3:
- scripts/deploy.sh L85, help text "(3, pinned; …)".
- scripts/README.md L428, "USD 3 headroom".

ASSUMPTIONS: the explicit `--min-headroom 3` flags in the tests of verify.py and its helpers check the flag mechanism, not the pin, so they stay valid.

RISKS: until the BLOCKED-ON edits land, `scripts/check.sh` fails on test_deploy.py and on the tests/scripts files listed below.

MANUAL ACTION REQUIRED: none.

BLOCKED-ON OWNER:
- Lane B, file scripts/tests/test_deploy.py:
  - L551, L553 and L560: use 1.99 instead of 2.99, and expect "below the required 2.0 USD".
  - L609: the boundary value becomes 2.
  - L622 and L1724: expect "2.0 USD".
  - L1726-1734: refuse 1.99, accept 2.00, and expect "2.0 USD".
  - scripts/deploy.sh L85 help text: change "(3, pinned…)" to "(2, pinned…)".
- test-engineer, files under tests/** (not edited):
  - tests/scripts/test_prespend_floors_14b.py: L4 docstring, L115 (2.99 in the refused list), L255-256 context, L278 (`3.0` becomes `2.0`), L301-302 (the 2.99 refusal and the expected 3.0).
  - tests/scripts/test_pipeline_refusals.py: L663 ("headroom 2.99"), L685 docstring, L698-699.
  - tests/scripts/test_providers_14b.py: L137 (`D(3)` becomes `D(2)`).
- Owner to be assigned: scripts/README.md L428 ("USD 3 headroom" becomes "USD 2").

BLOCKED-ON EVIDENCE: the test_deploy.py output shows "PRESPEND-CHECK-FAILED: remaining headroom 1.00 USD is below the required 2.0 USD", where the tests expect "3.0 USD".

NEXT GATE: route the lane B and test-engineer edits, then run the coordinator's `scripts/check.sh` on a clean worktree, then review. The progress log has a matching entry (/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/lane-A-progress.md).

#### Agent report (2026-11-16T16:30:26.953Z, agent a54f56f)

STATUS: COMPLETE. The tests now expect the floor-2 pin and all four requested runs pass. The BLOCKED-ON item from my first report still stands.
OWNER: test-engineer
WORK ORDER: Phase 15 follow-up. PRESPEND_MIN_HEADROOM_USD went from 3 to 2: I confirmed `PRESPEND_MIN_HEADROOM_USD=2` at release.conf L63. Each test keeps its boundary: 1.99 is refused, 2.00 is accepted.

FILES CREATED: none in this follow-up.

FILES MODIFIED (old -> new):
- tests/scripts/test_prespend_floors_14b.py:
  - L3-4 docstring: USD 3, "2.99 refused, 3.00 accepted" -> USD 2, "1.99 refused, 2.00 accepted". The floor-3 history and the option (i) source are cited.
  - Class SpendingStagesKeepTheThreeDollarFloor -> ...TwoDollarFloor, and both test names "three" -> "two".
  - L115: refused list (2.99, 1, 0, -0.01) at floor 3.0 -> (1.99, 1, 0, -0.01) at floor 2.0.
  - L121: accepted list (3, 3.0, 3.00, 3.01, 19.99, 20.25) -> (2, 2.0, 2.00, 2.01, 2.99, 3.00, 19.99, 20.25). 2.99 was refused under the old floor of 3 and is now accepted.
  - L170: floor 3.0 -> 2.0.
  - L255-256: verify.py `--min-headroom 3` with 2.99 / 3.0 -> `--min-headroom 2` with 1.99 / 2.0.
  - L278: pin 3.0 -> 2.0.
  - L301-304: 2.99 refused / 3.00 accepted -> 1.99 refused at 2.0 / 2.00 accepted.
  - Two more sites you did not list also asserted floor 3.0: L317 and L325. Both -> 2.0.
- tests/scripts/test_pipeline_refusals.py:
  - L663: case "headroom 2.99" -> "headroom 1.99".
  - L685-687: test renamed "exactly_three" -> "exactly_two". Docstring now says floor 2, with 3 and 20 kept as history. Accepted headroom 3 -> 2.
  - L691-693: the accepted list (3.01, 19.99) -> (2.01, 2.99, 19.99).
  - L698-699: the environment-cannot-lower case uses 2.99 -> 1.99, still refused.
- tests/scripts/test_providers_14b.py:
  - L134: test name "floor_at_3" -> "floor_at_2".
  - L137: D(3) -> D(2).
  - Left as is: L70-132 and L102. They pass `--min-headroom 3` to verify.py explicitly, so they test the flag rather than the pin.

COMMANDS RUN (offline, no sbt):
- From tests/scripts: `python3 -I -c` loading `test_cap_pins_14b.Phase15ProjectArithmetic` -> rc 0, Ran 4, OK.
- `python3 -I -m unittest discover -s tests/scripts -p 'test_providers_14b.py'` -> Ran 26, OK.
- `python3 -I -m unittest discover -s tests/scripts -p 'test_prespend_floors_14b.py'` -> rc 0, Ran 29, OK (93.6 s).
- `python3 -I -m unittest discover -s tests/scripts -p 'test_pipeline_refusals.py'` -> rc 0, Ran 59, OK (521.6 s). The harness moved this run to the background; I waited for it to finish.

TEST RESULTS: 4 + 26 + 29 + 59 = 118 run, 118 passed, 0 failed.
- I did not rerun the full tests/scripts suite after this follow-up. The last full run (before it) was rc 0, Ran 468, OK.
- tests/infra was not rerun: last result Ran 465, 1 failure, from the rag file.

VALIDATION RESULTS:
- Only tests/scripts files changed: sc_support, cap_pins, dryrun, refusals, prespend_floors, providers_14b, plus the new copyout_selection_15.
- No production edits, no 12-digit literals, no commit or stash.
- The progress log is at target/phase15/lanes/test-pins-progress.md.

ASSUMPTIONS: Flag-level verify.py tests that pass `--min-headroom 3` explicitly do not depend on the pin, so they stay as they are.

RISKS: The full tests/scripts suite has not been run after this follow-up. The coordinator's gate should rerun it.

MANUAL ACTION REQUIRED: none new.

BLOCKED-ON OWNER: rag-engineer, unchanged from my first report.

BLOCKED-ON EVIDENCE: The tests/infra account-ID guard fails on lines 164 and 182 of the untracked file modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Phase15VectorScaleSpec.scala.

NEXT GATE:
1. Full `python3 -I -m unittest discover -s tests/scripts -p 'test_*.py'` rerun.
2. Code-reviewer.
3. Coordinator `sbt check`.

#### Agent report (2026-11-16T16:34:59.522Z, agent a093722)

DELTA REPORT for the headroom floor change from 3 to 2 (lane B, infra-engineer). All three items are done; test_deploy ran 157 tests OK and my other suites ran 243 tests OK. Nothing was committed, no sbt run, no AWS call.

STATUS: DONE.

Changes:
1. scripts/tests/test_deploy.py. Each test keeps its intent:
   - L551 and L553: headroom 2.99 is now 1.99, expecting "below the required 2.0 USD".
   - L556: the docstring now says floor 2 and cites the floor-2 decision.
   - L560: message changed to "2.0 USD"; the headroom of 1 is still refused.
   - L608-609, test_boundaries_pass: exactly 2 USD is accepted (docstring and value).
   - L618-623, test_pins_cannot_be_weakened_from_the_environment: you named only L622, but I also had to change the receipt headroom from 2 to 1.5. At 2 the test would pass under the new floor and no longer prove anything. At 1.5, a floor of 1 taken from the environment would accept it, and the pinned floor of 2 still refuses it ("2.0 USD"). I added a one-line comment saying this.
   - L1725: message changed to "2.0 USD".
   - L1727-1735: the test is renamed to test_the_spending_floor_is_1_99_refused_and_2_00_accepted_for_a_spending_stage; 1.99 is refused and 2.00 is accepted.
2. scripts/deploy.sh L85, help text only: "(3, pinned…" is now "(2, pinned…".
3. scripts/README.md L428: "USD 3 headroom" is now "USD 2 headroom since the human's floor-2 decision of 2026-11-16", citing docs/agent-runs/phase-15/prompt.md "R-b option decision", line 185.

Pins: deploy.sh is not pinned anywhere. It does not appear in infra/terraform/emr-step-programs.json or any scripts/config/*.json, and no test under scripts/tests or tests/ pins its sha256.

Other tests checked: test_providers.py:134-137 and test_verify_redact.py:194-195 also use 2.99 and 3.0, but they pass an explicit `--min-headroom 3` to verify.py rather than reading the config. They are not affected and I left them unchanged.

Tests (AWS env unset):
- `python3 -m unittest test_deploy`: Ran 157 tests, OK, exit 0.
- `python3 -m unittest test_plan_deltas test_stagea_apply_path test_aws_cli_shapes test_syntax test_plan test_runtime_base_apply test_providers test_runtime_rollback test_rollback`: Ran 243 tests, OK, exit 0.

Still open from my previous delta, outside my files:
- Lane A: the expected message in test_13c_pipeline.py L268.
- test-engineer: the 5 failures in tests/scripts/test_pipeline_refusals.py.
- scripts/README.md L401 and L407 still say "three-run and USD 2.52 caps"; they were not on your list.

Progress log: target/phase15/lanes/lane-B-progress.md, entry 9.

NEXT GATE: independent code review of these edits.

#### Agent report (2026-11-16T16:58:08.918Z, agent a10795d)

**STATUS:** PARTIAL. The S chain passes end to end locally, but only with 3 recorded workarounds for real defects (D1, D2, D3). Without them the EMR chain would stop at hadoop-prep. L stops at entity-resolution (D4), so L Spark was never measured and check (a) is BLOCKED. A provisional S retention exists, sealed with the render-only report.

**OWNER:** infra-engineer (Phase 15 P6).

**WORK ORDER:** P6, a local dry run of the Session 2 EMR step chain at S and L. Branch phase-15, HEAD 7a02de2 plus the dirty tree.

**FILES CREATED** (all inside my territory):
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/lib/p6_local.py: local stand-ins for the node tools. `aws` serves only `s3 ls` and `s3 cp` from a local directory, applies the awscli filter rules, and refuses everything else with exit 97. Also `hadoop` (RunJar), `yarn`, `timeout` (GNU semantics), `spark-submit`, and the SHA256SUMS/tree-sha helpers.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/p6local/bin/{aws,hadoop,yarn,timeout,spark-submit}
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/lib/p6_local_chain.py: the driver.
  - It builds the real plan through `experiment.py render/args`, `budget.py estimate` and `pipeline.py plan` with the release.conf values.
  - It runs the unchanged scripts/emr/sc-step.sh for all 6 steps, replacing only MNT, RUNTIME_DIR, JOB_JAR and JAVA_HOME_FILE.
  - The Spark runtime is a fresh copy of the pinned archive, sha-checked. The job JAR is installed where the bootstrap installs it.
  - It samples disk and JVM memory (RSS), collects the evidence, and has `--retain` and `seal` modes.
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests/test_p6_local_chain.py: 25 tests.

**FILES MODIFIED:** none tracked. scripts/emr/sc-step.sh, scripts/tests/test_13c_pipeline.py and scripts/README.md are untouched. `build_l_input.py` re-rendered the four manifests; their sha256 is identical before and after.

**COMMANDS RUN** (with JAVA_HOME = JDK 17 and SBT_OPTS = -Dlogback.configurationFile=docs/agent-runs/phase-04/xml-repair-logback.xml; sbt only after sbt-check-done.txt existed):
1. `python3 -I experiments/scripts/build_l_input.py`: exit 0, 48,187 publications, nesting PASS.
2. `sbt -batch packageEmr "export hadoop/Compile/dependencyClasspath"`: exit 0. All 4 built JAR sha256 equal the S and L manifest pins (3defe8e6, 76a1b455, e8df4ee2, 22c1928a).
3. `python3 -I scripts/lib/p6_local_chain.py run --size S|L [--workaround-hadoop-cli] [--er-xmx N] [--er-config F] [--retain] --progress target/phase15/lanes/p6-progress.md`: 7 S runs and 3 L runs; every run is in the progress log.
4. `sbt -batch "rag / Compile / runMain edu.uic.cs441.scholarchain.rag.EmbeddingManifestMain --export <R>/spark --work-manifest <R>/spark/load-manifests/s3vectors.json --config target/phase15/p6/render-config.p26-scratch.json --manifest-output target/phase15/p6/render-S/real-model-manifest.json --report target/phase15/p6/render-S/render-report.json"`: exit 0. AWS, Voyage and Anthropic environment variables were unset; I checked the code path first (it builds no embedder or client).
5. `python3 -I scripts/lib/p6_local_chain.py seal --retention-dir <R> --render-report target/phase15/p6/render-S/render-report.json`: exit 0.
6. Diagnostic: `java -Xmx10g -cp er.jar Phase5Main resolve ...` on the S Hadoop output.

**TEST RESULTS:** `python3 -I -W error::ResourceWarning -m unittest discover -s scripts/tests -p 'test_p6_local_chain.py'` ran 25 tests, OK.

**VALIDATION RESULTS:** The tables, checks and defects below. Raw evidence is in target/phase15/p6/work/<run>/evidence/summary.json and logs/.

S, primary run p6-S-20261116T164523Z, with workarounds D1, D2 and ER_XMX 12g:

| Step | Wall (s) | Exit | EMR cap (s) | Key counts |
|---|---|---|---|---|
| stage-in | 0.18 | 0 | 270 | — |
| hadoop-prep | 35.8 | 0 | 1080 | INPUT 290,343; ACCEPTED 515,309; REJECTED 1,243; OVERSIZE_BLOCK 517; **OVERSIZE_TEAM 63, largestTeam 71**; EMITTED_PAIR 243,321; SCHEMA_FAILURE 21 |
| entity-resolution | 89.7 | 0 | 1080 | 20,000 comparisons; fake/live calls 0; JVM RSS 13.9 GB |
| spark-class-origin | 2.5 | 0 | 270 | CLASS-ORIGIN-OK |
| spark-job | 373.2 | 0 | 2160 | run:b8df1ae6…; works 10,578; researchers 21,819; iterations: component 17, **kCore 16**, community 20; export 605.7 MB, 433 files |
| copy-out | 2.9 | 0 | 540 | selected 1,105,013,052 B in 465 files; copied set equals the manifest |

L:

| Step | Wall (s) | Exit | Key counts |
|---|---|---|---|
| stage-in | 0.2 | 0 | — |
| hadoop-prep | 137.2 / 131.8 / 141.3 | 0 | INPUT 1,339,112; ACCEPTED 2,330,313; REJECTED 5,075; OVERSIZE_BLOCK 1,990; **OVERSIZE_TEAM 210, largestTeam 79**; EMITTED_PAIR 1,115,108; export 2,167,467,918 B |
| entity-resolution, pinned config | 0.4 | **2** | "input byte bound exceeded" (D4) |
| entity-resolution, diagnostic config 1, 22g | 429.2 | 2 | "block membership bound exceeded" |
| entity-resolution, diagnostic config 2, 22g | 963.5 | 1 | **OutOfMemoryError** (RSS 17.9 GB) |
| class-origin, spark-job, copy-out | not reached | — | — |

Checks:
- `maxLocalSampleRecords` rejects: S 0, L 0 (grep over export/.../reject/*). **PASS.**
- OVERSIZE_TEAM / largestTeam: S 63 / 71 and L 210 / 79, as expected (maxAuthorTeamSize 16 drops these works). **PASS.**
- Sidecar parts at S: 57 CSV parts, largest 8,545,744 B against the 16 MiB cap, none over. **PASS.** Not measured at L.
- Spark iterations: S kCore 16 and component 17 against the cap of 50. **PASS.** The L value (about 26 expected) was not measured.
- Peak Spark local-dir disk at S: 3.01 to 3.41 GB, plus 0.06 GB executor work dirs; checkpoint 3.83 GB (EFS on EMR). Under 20 GB, **PASS at S**. L unmeasured, so no ebs_size_gb finding.
- Copy-out at S: 1.105 GB against 8 GiB, **PASS**. 2.9 s against the 540 s share, but that is a local copy, not an S3 upload time.
- Check (a), L Spark wall time: **BLOCKED, not measured.**
- Render-only on S: mode render-only, embeddingCalls 0, stateWritten false, sourceRunId = run:b8df1ae6-a66e-4e6e-84c7-6cb3169fd0ae (the P6 run ID). selectedDocuments 10,000 (paper, community and researcher-profile 3,292 each; path 120; topic-institution 4). sizeEvidence: manifestBytes 21,341,493 against 33,554,432; textBytesTotal 1,231,347; textBytesMax 198; scannedRows 100,769. **PASS.**

Defects found (not fixed; outside this order):
- **D1:** sc-step.sh body_hadoop_prep passes `--run-id "${RUN_ID}"`. HadoopPrepPipeline.scala:58-59 accepts only `run:<uuid v4>`, and pipeline.py's SAFE_RUN_ID forbids ':'. No run ID can satisfy both, so the EMR hadoop-prep step fails immediately.
- **D2:** `--output-root "file://${out_dir}"` breaks FsPaths.runPath (HadoopIO.scala:39-45). It becomes a relative `file:/…` path under the step's working directory, and job J03 fails with a URISyntaxException.
- **D3:** PIPELINE_ER_XMX=3g runs out of memory at S. 8g also fails; 10g passes (RSS 11.6 GB) and 12g passes. The m5.xlarge primary has 16 GiB, so this is tight.
- **D4:** The pinned er-config has maxInputBytes 1 GiB, below the 2.17 GB L export. With the bounds raised, L ER still runs out of memory at 22g after 963 s, near the 1080 s ER step cap. ER holds all input in memory. **L is not feasible on the current EMR design.**

**RETENTION (provisional):**
- Path: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p6/size-S/run:b8df1ae6-a66e-4e6e-84c7-6cb3169fd0ae/ holding spark/ (433 files, unmodified), SHA256SUMS, provenance.json and render/render-report.json (+ qualifications).
- **sha256 of SHA256SUMS: c9b3fb2d602a680fcd31c59af387e7730c5c2d313541e1496ffbc7988b2b5000.** `cd <dir> && shasum -a 256 -c SHA256SUMS` exits 0.
- Provenance: head 7a02de2 with a dirty tree (no changes under modules/core, hadoop, entity-resolution or spark); job JAR 22c1928a, equal to the S manifest; template 9341c162, equal; S input-tree sha 78bd68c6…; UTC 16:45:23Z to 16:53:48Z; the D1, D2 and D3 workarounds are recorded.
- To redo it on the frozen commit after the P15 rebuild:
  1. Repeat command 2 above (sbt packageEmr plus the classpath export), then `grep '^/.*\.jar' target/phase15/p6/build/package-emr.log | tail -1 > target/phase15/p6/build/hadoop-dependency-classpath.raw.txt`.
  2. `python3 -I scripts/lib/p6_local_chain.py run --size S --retain` (add `--workaround-hadoop-cli --er-xmx <N>` only if D1 to D3 are still unfixed).
  3. Command 4 (the render) with `<R>` set to the new directory.
  4. Command 5 (the seal).

**ASSUMPTIONS:**
- Substitutions in the local emulation: Hadoop runs on LocalJobRunner instead of YARN. Spark runs as local-cluster[2,1,3072] in client mode instead of YARN. A throwaway Spark auth secret goes in a 0600 file, is deleted after the job, and appears redacted in the event logs. The job JAR is appended after the runtime JARs, as YARN orders it. S3 and EFS are local directories.
- The render config is a scratch file (bucket name is a placeholder); the private render config was not read.

**RISKS:**
- Local timings are from the M5 laptop, not EMR.
- A root `sbt clean` would delete target/, retention included, because the build has no cleanKeepGlobs. Requirement (b), that the export survives a build clean, is therefore not met.
- Session plan 5.2 step 7b.1 runs `shasum -c <dir>/SHA256SUMS` from the repo root. With relative paths that fails; it must `cd` into the directory first.
- About 35 GB of work directories remain under target/phase15/p6/work.

**MANUAL ACTION REQUIRED:**
- The human decides whether L stays in the plan: ER memory and the ER config block it.
- The human decides the ER_XMX value.

**BLOCKED-ON OWNER:**
- D1 and D2: infra (sc-step.sh, lane A, plus the step-program pins), or hadoop-engineer if HadoopPrepMain should change instead.
- D3: infra (release.conf PIPELINE_ER_XMX), human gate.
- D4: experiment-engineer and entity-resolution-engineer (the L ER config and ER's in-memory model), human decision.
- Retention path surviving a clean: build-engineer (cleanKeepGlobs) or the human (a path outside target/).
- Step 7b wording: documentation-engineer.
- The e2e test: test-engineer.

**BLOCKED-ON EVIDENCE:** target/phase15/lanes/p6-progress.md; target/phase15/p6/work/p6-S-20261116T{155022,155228,155351,155610}Z (D1, D2, D3); p6-L-20261116T{161356,161657,162641}Z (D4); target/phase15/p6/er-heap-probe/.

**NEXT GATE:**
- Owner fixes for D1 to D4.
- Then rerun P6 S and L on the frozen commit.
- Independent code-reviewer for the harness, plus the test-engineer's e2e test.
- Human decision on L.

#### Agent report (2026-11-16T17:40:19.002Z, agent af2339e)

STATUS: DONE. Verdict SMALL. Spark ran locally at L and at S with ER bypassed, and both runs exited 0. Every output is marked "ER bypassed: identity pass-through (no cross-source resolution), local only, not the EMR path".

OWNER: experiment-engineer

WORK ORDER: Phase 15, "L, second size" (docs/agent-runs/phase-15/prompt.md:233-239). Human decision: "Second size: if Spark can run on L locally with ER bypassed …".

VERDICT SMALL. Reasons (read-only evidence):
- The Spark ER input contract is small and can be written without running ER.
  - Phase6CReaders.verifyEr (modules/spark/.../Phase6CReaders.scala:346-377) needs four things:
    - a manifest with schemaVersion scholarchain.resolution-export.v1, complete=true, files[path,bytes,sha256] and exactly 2 constraints;
    - a marker equal to sha256(manifest text)+"\n";
    - an inventory equal to the files on disk;
    - matching size and sha256 for each file.
  - requireErPrepBinding (:264-268) needs prepCompletionHash = sha256(hadoop marker + "\n" + hadoop manifest).
  - load (:575-658) reads 8 files: {researcher,work}/{accepted-links,unresolved,conflict}.jsonl and grouping-constraints.json. They must use schema scholarchain.resolution.v1, and the required fields must be non-null. Empty arrays are valid.
  - StableIds.sparkAnalyticsRunId (modules/core/.../StableIds.scala:527-545) needs runId in run:<uuid v4> form, a valid policy pattern and a 64-hex policyHash.
- Identity is already how Spark treats DBLP authors. Phase6CJobs.scala:204-211 builds the DBLP researcherId from nameText. With no links, each author string resolves to itself, non-DBLP mentions stay unmapped, and each work is its own canonical work (:295-324).
- The hard invariants do not depend on ER links: pair-count-mismatch (:635-642) and missing-graph-endpoint (:855-874).
- Nothing else in Spark reads the ER root (only Phase6Main.scala:129 and Phase6CMain.scala:141).
- No module, JAR, step program, pin or EMR file was changed. The work took about 1.5 h.

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/scripts/er_identity_bypass.py (sha 0c987ca0…)
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/scripts/run_spark_bypass.py (sha 4746096b…). This runner takes the P6 S logged Phase6Main argv and changes only the paths and the run label.
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/tests/test_er_identity_bypass.py (13 tests). They cover contract validity against the reader rules, determinism, the disclosure, and refusal of non-Hadoop input: a plain dir, a missing dir, an ER root, an incomplete marker, the wrong schema, a missing _SUCCESS, an extra part, a tampered sha, and an existing output.
- Evidence under /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p6/l-bypass/ (git-ignored):
  - er-S/run and er-L/run
  - spark-S/ and spark-L/, each with summary.json, command.json, logs/ and the spark export
  - s-real-er-collect.json
  - run-S.out and run-L.out
  - ER-BYPASSED.txt markers
- Progress log: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/l-bypass-progress.md

FILES MODIFIED: none.

COMMANDS RUN (repository root):
1. `python3 -I -W error::ResourceWarning -m unittest discover -s experiments/tests -p 'test_er_identity_bypass.py' -v` → Ran 13, OK.
2. `python3 -I -m unittest discover -s experiments/tests` → Ran 79, OK.
3. `python3 -I experiments/scripts/er_identity_bypass.py --hadoop-root target/phase15/p6/work/p6-S-20261116T164523Z/mnt/runs/p6-S-20261116T164523Z/hadoop/af8ff5af-1d09-46ef-b2f4-672bb747ba34 --out target/phase15/p6/l-bypass/er-S/run --verify-hashes` → exit 0. erRunId run:15939b46-…; prepCompletionHash 73a18cb0…, which equals the real S ER's value, so the binding is correct.
4. Same command with the L Hadoop root (…/p6-L-20261116T162641Z/…/hadoop/08bf0555-048b-4594-be41-e4e1bdd9d0d8) and --out …/er-L/run → exit 0. erRunId run:e8575fce-…
5. `python3 -I experiments/scripts/run_spark_bypass.py --label S --hadoop-root <S hadoop> --er-root target/phase15/p6/l-bypass/er-S/run --base target/phase15/p6/l-bypass/spark-S --p6-work target/phase15/p6/work/p6-S-20261116T164523Z` → exit 0.
6. The same with --label L, the L Hadoop root, er-L/run and base spark-L → exit 0.

How the Spark run reproduces P6's S step:
- Same job JAR, sha 22c1928a (checked against the pin).
- Same template, sha 9341c162 (checked), rendered by the unchanged scripts/emr/sc-render-spark-config.py.
- Same P6 spark-submit stand-in, giving local-cluster[2,1,3072] with a 3g driver.
- Only these argv values changed, as recorded in command.json "argvChangesFromP6S": the stagingDir, the config path, --name and spark.yarn.tags.

TEST RESULTS: 13/13 new tests OK. The full experiments suite is 79/79 OK.

VALIDATION RESULTS (S vs L table; Spark wall time is the end-to-end spark-submit time):
| | S, real ER (P6 p6-S-20261116T164523Z) | S, identity | L, identity |
|---|---|---|---|
| Spark exit / wall | 0 / 373.2 s (chain step) | 0 / 459.84 s | 0 / 1110.14 s |
| Stages / tasks (failed) | 2,026 / 27,403 (0) | 1,984 / 27,282 (0) | 2,000 / 32,117 (0) |
| Canonical works (source) | 10,578 (10,579) | 10,578 (10,579) | 48,188 (48,189) |
| Researchers | 21,819 | 21,819 | 76,623 |
| all-years: active researchers / edges | 20,967 / 81,181 | 20,967 / 81,181 | 74,543 / 320,690 |
| all-years: components / largest (fraction) | 1,045 / 17,179 (0.819) | same | 2,811 / 65,597 (0.880) |
| through-2009: vertices / edges | 3,908 / 8,608 | same | 15,540 / 39,672 |
| 2010-14 | 4,506 / 11,795 | same | 20,334 / 61,109 |
| 2015-19 | 6,637 / 19,326 | same | 24,321 / 79,748 |
| 2020-26 | 11,088 / 45,020 | same | 37,643 / 159,616 |
| since-2015 | 15,651 / 62,785 | same | 53,394 / 231,429 |
| Iterations: component / k-core / community | 17 / 16 / 20 (community not converged) | 17 / 16 / 20 | 15 / 26 / 20 (community not converged) |
| Hard invariants (pair mismatch, missing endpoints) | 0, 0 | 0, 0 | 0, 0 |
| Peak spark-local / checkpoint / output | 3.41 / 3.83 / 0.61 GB | 3.17 / 3.82 / 1.09 GB (sum 7.89) | 9.69 / 16.12 / 3.07 GB (sum 25.32) |
| Peak process-tree RSS | n/a | 7.59 GB | 9.08 GB |
| Sidecar CSV parts / max part (cap 16,777,216 B) | 57 / 8,545,744 | 57 / 8,506,349 | 231 / 8,565,999, 0 over cap: PASS |

- Check (a): the L local Spark wall time of 1110 s (18.5 min) is over about 15 min: YES. It is under the EMR spark step cap of 2160 s.
- Per-window vertices and edges are identical between real ER and identity at S, because real ER at S produced 0 researcher links.
- On the same harness, L/S identity is 2.41x the wall time for 4.56x the works.

ASSUMPTIONS:
- "Identity" means ER writes no links, no cannot-links, no authoritative IDs and no decisions. Spark's own DBLP-name rule then gives the identity mapping.
- Graph vertices per window means active researchers (the metrics rows per window). Edges are counted from the coauthor-edges sidecar CSV windowId column; the all-years count matches the allYearsEdges counter.
- The "components" counter in counters.json is a sum over windows, so the table uses analytics-report per window.

RISKS:
- Identity S is 87 s slower than real-ER S even though the graph is the same. The cause was not measured. Possible causes are run-to-run variance and the runner's 5 s du/ps sampler running on the same machine. The P6 figure is the sc-step wall time, so it is a different harness. Compare L only against S identity.
- Disk peaks are 5 s samples, so the true peak may be higher.
- run_spark_bypass.py has no unit tests. It was exercised only by the two runs.
- About 33 GB was added under target/phase15/p6/l-bypass (not deleted). A root `sbt clean` would remove it, as P6 already noted.
- experiments/README.md was not updated with these commands; it is already modified in the uncommitted bundle.

MANUAL ACTION REQUIRED: none to proceed. A human decision is needed on whether to cite the L identity numbers in the report, with the disclosure.

BLOCKED-ON OWNER: none.

BLOCKED-ON EVIDENCE: none.

NEXT GATE: independent code-reviewer review of the three new experiments files, and the orchestrator assembling this evidence under docs/agent-runs/phase-15/. No commit has been made, and none was requested.

#### Agent report (2026-11-16T17:52:49.995Z, agent acc922c)

STATUS: DONE (offline kit authored and tested). No AWS call, nothing tracked was edited, no commit, no stash. One limit stated plainly: the wrapper cannot run from a worktree, so steps 9-12 need the main checkout itself to be clean at the gate commit (details under RISKS).

OWNER: infra-engineer (helper kit for P0, under git-ignored target/; the wrapper itself and `scripts/billing/**` are unchanged)

WORK ORDER: Phase 15 P0. The human approved the live budget modify: USD 25 limit, alerts at USD 18/20/22, period 2026-10-01 to 2027-01-01, credits and refunds excluded, decision A. The task was to shorten the 16-step Phase 14B sequence into a safe copy-paste kit without touching the wrapper.

FILES CREATED (all ignored; `git check-ignore -v` printed `.gitignore:2:target/` for each one):
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0-steps.md (step 0 setup plus 12 steps)
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0_pins.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0_gate.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0-gate-record-draft.md
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/tests/test_p0_kit.py

FILES MODIFIED: none. `git status --porcelain | wc -l` was 93 before and 93 after.

COMMANDS RUN (all offline):
- `python3 -I -B target/phase15/p0/tests/test_p0_kit.py` → `Ran 18 tests ... OK`. The first run had 1 failure, a wrong expected count in my own test (22 shared fields, not 23). I fixed it and reran.
- A dry run of `p0_pins.py` at HEAD 7a02de2 with synthetic hashes, output to the scratchpad and then deleted → `stale=15`, `modify_object=added config_rows=7`, a valid unified diff.
- `p0_gate.py modify --commit <HEAD> ...` on the real repo → `P0_GATE_REFUSED: DIRTY_CHECKOUT`, exit 2, refused before any prompt.
- The code blocks of p0-steps.md through `zsh -n` and `bash -n` → both syntax-ok. An ast parse of the 3 .py files → ok.
- `git check-ignore -v` on the 5 deliverables.
- An offline hash comparison with the wrapper's account constant (nothing printed): the README hash `32c67ff8…bf3e` is the sha256 of the bare 12 digits. Step 2 uses that form.

TEST RESULTS (18/18 pass; synthetic temp git repo; fake account built at runtime; the real wrapper source copied read-only from HEAD):
- **Pins:** finds exactly the stale freeze row; adds the 7 modify.config rows with correct hashes and sizes; leaves the Phase 12D values untouched; reads git objects, not the dirty tree; refuses the create-plan hash, bad hex, zero bytes, and an output folder inside tracked paths; never writes reviewed-pins.json; a second run gives identical bytes.
- **Modify gate:** exactly 28 fields; the wrapper's own `load_modify_gate`, `check_checkout` and `check_modify_record` accept it; mode 0600; O_EXCL refuses to overwrite; refuses a parent folder that is not 0700.
- **Verification gate:** exactly 29 fields, equal to the wrapper's `MODIFIED_GATE_FIELDS`, and accepted by `ModifiedVerification.load_gate` and `check_checkout`; the receipt hash from the public modify log matches the canonical save_json form; a window that starts before the receipt is refused.
- **Refusals:** dirty tree (untracked or modified file) refused with zero prompts asked; wrong commit refused; ignored `__pycache__` refused; plan cross-check mismatch; STS/account mismatch (the code does not contain the account); the unpatched wrapper rejects the fake account with its own `HUMAN_IDENTITY` check; window closed or times out of order; a "no" answer writes nothing.
- **Schema and hygiene:** the 28/29-field mirrors equal the sets read from the real wrapper source; no standalone 12-digit literal in any kit file.

VALIDATION RESULTS:
- The wrapper does every check itself. `p0_gate` additionally validates each gate with the wrapper's own loader and offline checkout checks on a temporary 0700/0600 copy before the real O_EXCL write. Stdout is only the sha256.
- Account, actor ARN and STS JSON are read at hidden /dev/tty prompts. They are never in argv and never printed.
- No terraform fmt/validate/plan applies: this round has no Terraform change. The live plan is the human's step 5.
- No independent code review yet.

ASSUMPTIONS:
- The coordinator's commit C contains the reviewed billing files, and the template is unchanged (946352f3…).
- Commits C2 and C3 change only the pins file and the record.
- The user's shell is zsh. The steps avoid PIPESTATUS (bash-only; README step 13 uses it and would print an empty exit code in zsh) and avoid inline `#` comments.

Deviations from the README, none weakening a check:
- The config backup is named `config-before-modify-20261117` so it cannot collide with an existing folder. The wrapper never reads that name.
- The plan argv is byte-identical to the README (checked with diff) and runs in a `(cd "$PRIMARY/config" && …)` subshell.
- README steps 8+9 and 13+14 are merged into one block each.

RISKS:
1. **Worktree not possible for the wrapper runs.**
   - `budget_execution.py:297-298` (WRAPPER_LOCATION) and `budget_verification.py:490` (VERIFIER_LOCATION) refuse any path other than the main checkout.
   - `check_checkout` (`budget_execution.py:732-773`) runs git on that fixed folder: HEAD must equal the gate's commit, status must be empty, and the on-disk `scripts/billing` file set must equal `wrapper_files`.
   - So the dedicated worktree serves only steps 1-4 (it is a clean copy of commit C). Steps 9-12 need the main folder clean at C3.
   - Option A: commit C leaves the tree clean and nobody edits the repo until verification is done.
   - Option B, human decision: `git stash push --include-untracked -m p0-park` after step 8, then `stash pop` after step 12.
   - Moving the repo is not recommended: there are 3 linked worktrees plus the live session.
2. At HEAD, 15 `source_freeze` rows are already stale (the README listed 7 on 11-15; P40/P41 changed more). After C2, any commit that touches `infra/terraform/**` or `tests/infra/**` stops the wrapper with `SOURCE_DRIFT`, so those commits must be held until verification is done.
3. A pre-existing ignored `scripts/billing/tests/__pycache__` exists now. Step 9 removes it, and `p0_gate` refuses while it is present.
4. Gate provenance: an agent-authored script assembles the JSON, but the human types every decision and the G1 text and runs the script. The reviewer should confirm this matches "the wrapper does not draft or write this gate".
5. The kit itself is unreviewed.

MANUAL ACTION REQUIRED (human, and why):
- Browser MFA, switch role, `aws login` and STS (steps 2, 10, 12): MFA and identity can only come from the human.
- Steps 3-6: the private config refresh, typing the account, the plan, and reading the plan, because they touch private files and AWS.
- Review the pins diff and commit C2 (human-owned values).
- Write the gate record in their own words from the draft and commit C3 (human decision record).
- Pick the two one-hour windows.
- Answer the hidden and visible prompts in `p0_gate`.
- Run the apply and the verify exactly once each.
- Make the main checkout clean (option A or B).
- Remove the worktree at the end.

BLOCKED-ON OWNER: none for this authoring task. Clean-tree option A needs the coordinator. Option B needs the human.

BLOCKED-ON EVIDENCE: none.

NEXT GATE: independent `code-reviewer` (opus, high) read-only review of the 5 kit files against `budget_execution.py` and `budget_verification.py`. Then the human reads p0-steps.md and chooses option A or B before Tuesday's commit C.

FINAL STEP LIST: this is a summary. The exact copy-paste commands are in /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0-steps.md.

0. Setup: `umask 077`, set REPO/PRIMARY/BACKUPS/KIT/EV/WT/D=20261117, `mkdir -p "$EV"`.
   - Expect: no output.
1. `C=$(git -C "$REPO" rev-parse HEAD)`; `git worktree add --detach "$WT" "$C"`; `shasum` of the template.
   - Expect: C, then "Preparing worktree", then `946352f3…af28`.
   - If not: stop and send the 3 outputs.
2. Console MFA and switch role; `aws login`; STS `--query Account | tr -d '\n' | shasum -a 256`; the Arn with the account masked by sed.
   - Expect: `32c67ff8…bf3e  -` and `arn:aws:sts::<acct>:assumed-role/scholarchain-billing-deployer/scholarchain-billing-operator`.
3. `cp -Rp` the config to `$BACKUPS/config-before-modify-$D`; copy the 7 files from `$WT` with chmod 600 and cmp each; `find` the config folder.
   - Expect: backup-ok, 7 "ok" lines, exactly 7 config names.
4. `read -rs ACCT`; README render one-liner (template from `$WT`) → `INPUT_SHA`.
   - Expect: 64 hex.
5. README plan argv inside `(cd "$PRIMARY/config" && …)`.
   - Expect: `exit=2`.
6. `@` count guard; grep the plan lines into `$EV`; `PLAN_SHA`, `PLAN_BYTES` and mode, tee'd to the binding log.
   - Expect: `at_signs=0`, the "updated in-place" line and `Plan: 0 to add, 1 to change, 0 to destroy.`, `mode=600`.
7. `python3 -I -B "$KIT/p0_pins.py" --plan-sha256 … --plan-bytes … --public-input-sha256 …`; review the diff. If HEAD still equals C: cp the proposed file over the pins file, then `git commit -- scripts/billing/reviewed-pins.json` (C2).
8. Pick the window; cp the record draft to `docs/agent-runs/phase-14/budget-modify-gate-$D.md`; rewrite it and fill the blanks; grep shows none left; `git add` and `git commit -- <record>`; `C3=$(git rev-parse HEAD)`.
9. Remove `scripts/billing` `__pycache__`.
   - Expect: `git status --porcelain --untracked-files=all` is empty and HEAD equals C3.
   - If not: option A or B.
10. Inside the window: switch role; `aws login; date`; STS `--output json; date`; `GATE_SHA=$(python3 -I -B "$KIT/p0_gate.py" modify --commit "$C3" --operation modify-$D-01 --window-start 2026-11-17THH:MM --record … --plan-sha256 "$PLAN_SHA" --gate-out "$PRIMARY/approval-$D-modify.json")`.
    - Expect: 64 hex.
    - If not: `P0_GATE_REFUSED: <CODE>`; nothing was written; stop and send the code.
11. `python3 -I "$REPO/scripts/billing/budget_execution.py" modify --gate … --gate-sha256 "$GATE_SHA" --operation modify-$D-01 > "$EV/budget-modify-apply.log" 2>&1; echo "exit=$?"`; cat the log; `ls -l "$BACKUPS/modify-$D-01"`.
    - Expect: exit=0, applied true, notification_count 3, …
    - If not: never rerun; send the exit line, the log and the listing.
12. New window after step 11; tree still clean; switch role, login and STS again; `VGATE_SHA=$(… p0_gate.py verify --commit HEAD --operation verify-usd25-$D-01 --window-start … --modify-log "$EV/budget-modify-apply.log" --modify-gate-name approval-$D-modify.json --modify-gate-sha256 "$GATE_SHA" --gate-out "$PRIMARY/approval-$D-verify.json")`; `budget_verification.py verify-modified … > "$EV/budget-modify-verify.log"`.
    - Expect: exit=0, `"option": "M"`, `notification_count` 3, `cost_scope_match` true.
    - Then the optional console check and `git worktree remove "$WT"`.

#### Agent report (2026-11-16T18:06:40.861Z, agent a54f56f)

STATUS: COMPLETE. The new test passes the exact argv that sc-step.sh builds to the real Hadoop parser. That argv is accepted, and both old forms are caught. Final runs: tests/scripts 471 of 471 passed, tests/infra 465 of 465 passed.

The old `file://` output root is not rejected by the parser, though. It is accepted, and the run directory lands in the wrong place. The test asserts that misrouting, which still catches the mutant.

OWNER: test-engineer
WORK ORDER: Phase 15 P6 D1/D2. Feed the exact sc-step.sh hadoop-prep argv into the real Hadoop parser, cite the S proof run, and update the old token check in test_pipeline_dryrun.

FILES CREATED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts/test_hadoop_prep_args_15.py (3 tests). How it works:
  - **Capture:** it runs the dry-run hadoop-prep body through test_pipeline_bodies.Harness. The fake S3 serves the real built JARs (modules/hadoop/target/scala-3.3.4/hadoop-submit_3-0.1.0-SNAPSHOT.jar and hadoop-dependency-bundle_3-0.1.0-SNAPSHOT.jar) and the real experiments/inputs/15a/prep-config.json, so the body's sha256 checks pass on real files. The fake `hadoop` records the argv `jar … HadoopPrepMain …`, which is what the test checks.
  - **Replay:** the recorded argv goes unchanged to `org.apache.hadoop.util.RunJar`, which is what `hadoop jar` runs. It uses Java 17 (/opt/homebrew/opt/openjdk@17/…), the bundle named by -libjars, and the Hadoop client classpath from target/phase15/p6/build/hadoop-dependency-classpath.raw.txt.
    - Nothing is substituted: `--execution-mode cluster` stays.
    - "Accepted" means HadoopPrepMain parses, validates the config, checks the run id, resolves the root, binds the staged inputs (copies of datasets/samples) and creates the run directory before any job is submitted.
    - The test waits for that directory at exactly `<--output-root>/<uuid>`, then stops the JVM, since there is no YARN.
  - **Positive test:**
    - `--run-id` matches `run:<uuid v4>` and differs from the pipeline id.
    - `--output-root` is exactly `<run>/hadoop`, with no `://`.
    - The four inputs keep `file://`.
    - The run directory is created at `<root>/<uuid>`, with no "run id"/"output root" error and no relative `file:` directory.
  - **Mutant D1** (a fixture copy of sc-step.sh edited to `--run-id "${RUN_ID}"`): exit 1, "run id is not a version-4 run id: bp-test-run-1", nothing created.
  - **Mutant D2** (`--output-root "file://${out_dir}"`): the parser does not refuse it. The run directory is created under `<cwd>/file:/…/<uuid>`, and nothing reaches the intended root.
  - The class is skipped with a stated reason if JDK 17, the JARs or the classpath file are missing. In the final run nothing was skipped.
  - Each of the three replays was observed directly (scratch script /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/peek_replay.py):
    - current argv: stopped after the run directory was created;
    - D1: rc 1;
    - D2: directory created under `file:`.
- **Proof run**, cited in the test docstring and not re-run: target/phase15/p6/work/p6-S-20261116T171431Z/evidence/summary.json.
  - allStepsPassed true, and all 6 steps exited 0.
  - `workarounds` holds only "ER_XMX 3g -> 12g (D3)". There is no hadoop-CLI workaround: P6_WORKAROUND_HADOOP_CLI in scripts/lib/p6_local.py was not used.
  - Hadoop runId run:650ff98f-1fff-49e3-9957-a0d84c3e992a.
  - Its pins (hadoop-submit-jar 3defe8e6…, hadoop-libjars 76a1b455…) equal the sha256 of the JARs this test used. stepRunnerSha256 b79f5c1f… equals the current sc-step.sh.
  - The summary records "--execution-mode cluster -> local" as a disclosed local substitution.

FILES MODIFIED:
- tests/scripts/test_pipeline_dryrun.py L192-200: the program-wide tokens `'--run-id "${RUN_ID}"'` and `"file://"` were replaced by checks on the body_hadoop_prep slice only. It must contain `"${HADOOP_MAIN}"`, `--once`, `--execution-mode cluster`, `--run-id "${hadoop_id}"`, `--output-root "${out_dir}"` and the four `--<source> "file://` inputs. It must not contain `--run-id "${RUN_ID}"` or `--output-root "file://`. HadoopPrepMain is still checked program-wide.

COMMANDS RUN (offline; no sbt, no AWS):
- `python3 -I -m unittest discover -s tests/scripts -p 'test_hadoop_prep_args_15.py' -v` → Ran 3, OK (17.2 s).
- `python3 -I -m unittest discover -s tests/scripts -p 'test_pipeline_dryrun.py'`:
  - first run: 1 failure, a bug in my own token (HadoopPrepMain sits in the HADOOP_MAIN constant, outside the body);
  - after fixing it: Ran 16, OK.
- `python3 -I -m unittest discover -s tests/scripts -p 'test_*.py'` → **rc 0, Ran 471, OK**, 0 skipped (1385.1 s).
- `python3 -I -m unittest discover -s tests/infra -p 'test_*.py'` → **rc 0, Ran 465, OK** (1024.6 s). The earlier rag account-ID failure no longer appears.

TEST RESULTS: tests/scripts 471/471 passed; tests/infra 465/465 passed.

VALIDATION RESULTS: only tests/scripts changed. In total: 6 files modified (sc_support, cap_pins_14b, pipeline_dryrun, pipeline_refusals, prespend_floors_14b, providers_14b) and 2 created (copyout_selection_15, hadoop_prep_args_15). No production edits, no 12-digit literals, no commit or stash. The progress log is target/phase15/lanes/test-pins-progress.md.

ASSUMPTIONS:
- RunJar on Java 17 with the P6 client classpath stands in for the EMR `hadoop jar`. The classpath is environment only; the argv is untouched.
- Creating the run directory counts as "fails only after argument validation", since it happens after the run-id, root and input checks and before job submission.

RISKS:
- The test reads JARs from modules/hadoop/target, which an sbt run in this tree can rebuild. The test copies them at setup, so a rebuild mid-run is safe. In a clean checkout without a build or JDK 17 the class is skipped, not failed.
- The client classpath file is git-ignored and specific to this machine.
- D2 is detected through misrouting, not a parser refusal (described above). Making a `file:` root a hard error would be a Hadoop-module change (owner: hadoop-engineer), and I have not requested it.

MANUAL ACTION REQUIRED: none.
BLOCKED-ON OWNER: none. The earlier rag item is cleared: tests/infra now passes.
BLOCKED-ON EVIDENCE: none.
NEXT GATE: code-reviewer on the tests/scripts diff, then the coordinator's `sbt check`.

#### Agent report (2026-11-16T18:29:54.461Z, agent abebecf)

STATUS: COMPLETE. Everything in my territory is done and every gate I ran passed. Five items need other owners (see BLOCKED-ON).

OWNER: infra-engineer

WORK ORDER: Phase 15 D3, EMR primary node and run cap. Human go-ahead in docs/agent-runs/phase-15/prompt.md L271 ("S run cap and D3 go-ahead"); D3 decision at L258; coordinator checks at L260-269.

FILES CREATED:
- infra/terraform/tests/phase15_emr_primary.tftest.hcl (L1-395). 12 plan-only runs. The mock fixture is copied from phase15_stagea, so the file holds no 12-digit literal.
- scripts/tests/test_d3_emr_primary.py (L1-~480). 31 tests.
- target/phase15/lanes/d3-progress.md (progress log).

FILES MODIFIED (only the D3 parts; the other lanes' uncommitted edits in these files are untouched):
- infra/terraform/modules/emr/variables.tf
  - L26-31: `primary_instance_type = optional(string, "r5.xlarge")`.
  - L57-63: new validation, `contains(["m5.xlarge","r5.xlarge"], …)`.
  - The core pin `var.config.instance_type == "m5.xlarge"` is unchanged, so the mutation test in tests/infra still matches its text.
- infra/terraform/modules/emr/main.tf
  - L26-33: `caps.primary_instance_type`.
  - L80-81: master group `instance_type = local.cfg.primary_instance_type`.
- infra/terraform/phase12b-variables.tf (additive only)
  - L79: the new field.
  - L103-109: the same validation as the module.
- infra/terraform/environments/course.local.tfvars.example L229: one comment line.
- infra/terraform/README.md: L266 (EMR row) and L567-574 (new D3 bullet).
- scripts/lib/budget.py
  - Docstring.
  - L104-118 and L135-173: per-group estimate.
  - L198-286: `parse_ledger`, `ledger_totals`, `read_ledger`.
  - L414-622: time parsing, rate parsing, `describe_facts`, `cmd_ledger_record_actual`.
  - L671-686: parser entry for the new command.
- scripts/lib/pipeline.py
  - L19-21: docstring.
  - L431-434: plan `--primary-instance-type`.
  - L509: `config.primary_instance_type`.
  - L633: summary line.
  - L719 and L734-736: check-cluster. MASTER must be exactly the primary type; CORE and TASK exactly `--instance-type`.
  - L751: check-cluster output line.
  - L841 and L869: argparse.
- scripts/lib/experiment.py: L43-49, L69-70, L277-278, L339-345, L390. Adds an optional `pipeline.primary_instance_type`, which becomes `--primary-instance-type`.
- scripts/run-bounded-pipeline.sh
  - Help text.
  - L168-169, L187-189, L227-230: new flags and variables.
  - L256-257: `--init-ledger` now refuses the new flags.
  - L270-304: new `--record-actual` mode.
  - L333: primary type format check.
  - L362-374: per-group estimate.
  - L393-398: "estimate unavailable" message.
  - L414: plan call.
  - L465-470: G6 message.
  - L647 and L655: check-cluster.
- scripts/config/emr-pricing.conf L32-47:
  - `EMR_RATE_EC2_R5_XLARGE=0.252`, `EMR_RATE_EMR_R5_XLARGE=0.063`, `EMR_PRICING_R5_XLARGE_RETRIEVED=2026-11-16`.
  - Comments carry both source URLs, the publication date and the prompt.md citation.
  - `EMR_PRICING_CONFIRMED_BY_HUMAN` is unchanged (it was already `true`; I did not set it).
- scripts/config/release.conf L340-347: `PIPELINE_ER_XMX=12g`. The comment cites the decision, the P6 heap results (3g/8g out of memory, 10g/12g OK, sampled RSS 12.5 and 12.94 GB, coordinator's figure 13.9 GB) and the 32 GiB r5.xlarge primary.
- scripts/README.md L401: new D3 paragraph.
- scripts/tests/test_pipeline.py
  - L910: `-Xmx3g` changed to `-Xmx12g`.
  - ~L1113-1116: the pricing-rate set now includes the r5 rates and the retrieval date.

COMMANDS RUN (all offline; AWS environment variables unset; `AWS_CONFIG_FILE` and `AWS_SHARED_CREDENTIALS_FILE` set to /dev/null; no state or local tfvars read):
- Terraform scratch root at <scratchpad>/d3/repo/infra/terraform, repo-shaped, copied without *.tfstate* and *.local.tfvars:
  - `terraform init -backend=false -input=false -lockfile=readonly -plugin-dir=<repo>/infra/terraform/.terraform/providers`
  - `terraform test -no-color -filter=tests/<file>` for each file below
  - `terraform test -verbose` on phase15_stagea and phase14b_plan_deltas, then `plan_deltas.py derive --set stagea|phase14b`
  - `terraform validate`
- `terraform fmt -check -diff` on the four named .tf/.tftest.hcl files only. The new tftest was formatted through `terraform fmt -` (stdin).
- `python3 -I -m unittest discover -s scripts/tests -p <file>` and `-s tests/scripts -p <file>` (tests/scripts runs are read-only).
- `bash -n` and `shellcheck -x -P SCRIPTDIR` (0.11.0) on run-bounded-pipeline.sh and run-experiment.sh.
- `python3 -I scripts/lib/pipeline.py step-manifest --check`

TEST RESULTS:
- Terraform (final scratch run), all rc 0: phase12b 18/0, phase12c 9/0, phase13c 37/0, phase14a 40/0, phase14b_plan_deltas 3/0, phase15_stagea 3/0, phase15_elasticity 5/0, phase15_emr_primary 12/0.
- Mutation check (scratch copy only): widening the primary list to include r5.2xlarge made the test fail ("Failure! 6 passed, 1 failed, 5 skipped").
- scripts/tests, final runs, all OK:

| Module | Tests |
|---|---|
| test_d3_emr_primary | 31 |
| test_pipeline | 69 |
| test_budget | 38 |
| test_experiment | 39 |
| test_providers | 24 |
| test_p6_local_chain | 25 |
| test_phase15_pipeline_pins | 19 |
| test_syntax | 20 |
| test_c1_step_args | 25 |
| test_13c_pipeline | 30 |
| test_aws_cli_shapes | 5 |
| test_cleanup | 57 |
| test_emr_bootstrap | 40 |
| test_upload_emr_artifacts | 62 |

- Failed runs along the way:
  - The first test_pipeline run, before my test edits, had 2 failures: the `-Xmx3g` assertion and the pricing-rate set. Both were fixed.
  - The first test_d3 run had 5 failures in my own helpers (a probe estimate of 0.00 was refused; one test overwrote a manifest). Both were fixed.
- tests/scripts (read-only), all OK:

| Module | Tests |
|---|---|
| test_pipeline_refusals | 59 |
| test_cap_pins_14b | 13 |
| test_experiment | 22 |
| test_experiment_tokens_14b | 17 |
| test_llm_budget_14b | 21 |
| test_pipeline_bodies | 31 |
| test_pipeline_dryrun | 16 |
| test_pipeline_execute | 14 |
| test_pipeline_ledger_13c | 20 |

- Not run: tests/infra/test_emr_module_13c.py. It plans with the real AWS provider binary, which the work order forbids.

VALIDATION RESULTS:
- fmt -check rc 0; validate Success; shellcheck rc 0; step-manifest ok.
- No step program changed (ER_XMX is a step parameter in sc-step.sh), so no pin refresh was needed.
- Plan deltas are unchanged; expected-plan-deltas.json is NOT modified:

| Stage | Derived |
|---|---|
| stagea-base | 171 added |
| stagea-emr-enable | 13 added, 0 changed |
| rb-base | 5 added, 1 changed, 13 removed |
| emr-apply | 13 added |
| pointer-apply | 1 changed (the second expected entry is the existing hand-derived ECS service) |

- Plan sizes are 173/186/178 and 204/204/217, the same as lane B.
- In the stage-a plan 2 the master group is `instance_type = "r5.xlarge"` and the core group is `"m5.xlarge"`.

LEDGER NUMBERS:
- Per run at 75 min: (0.315 + 0.240) × 5400 s / 3600 = 0.8325, which the scripts round up to **0.84**.
- Cumulative: 1.68 (Session 1) + 0.84 (S) + 0.84 (one S retry) = **3.36 ≤ 3.36**. The run is allowed with zero margin; one more cent is refused (3.37), and a fifth run is refused (4 runs, 4.20).
- The coordinator's 3.35 is the unrounded 1.68 + 2 × 0.8325 = 3.345. With script rounding the figure is 3.36, not 3.35.
- An r5 primary at 90 min would cost 0.98 per run, and 1.68 + 0.98 + 0.98 = 3.64 is refused.
- These are proven in LedgerAt75MinutesTests and PerGroupEstimateTests.

STEP TIMEOUTS (confirmed by dry run on a synthetic S manifest, run-experiment.sh path): stage-in 225 s, hadoop-prep 900 s, ER 900 s, class-origin 225 s, spark 1800 s, copy-out 450 s (sum 4500 s). The same dry run shows `ESTIMATE-USD: 0.84`, `ER_XMX=12g` and `primary-instance-type: r5.xlarge (core and task: m5.xlarge)`.

ACTUALS COMMAND: there was no record-actual or reconcile command, so I implemented one. The runbook steps right after each S run:
1. `aws emr describe-cluster --region <r> --cluster-id <j-id> --output json > <private file>` (operator).
2. `scripts/run-bounded-pipeline.sh --record-actual --run-id <run id> --describe <file> [--as-of-utc <UTC time the file was saved>]`. `--as-of-utc` is required while the cluster is not yet terminated.

How it works:
- It is local only; the script makes no AWS call.
- It binds the run to its cluster through PIPELINE_RUNS_DIR/<run>/run-manifest.json.
- It replaces the run's reserved estimate with the measured cost: time from cluster creation (or from the end of the previous actual on the same cluster) to the end time or `--as-of-utc`, times the reviewed rate of each instance group, rounded up.
- While the cluster is not yet terminated it adds a provisional idle tail (the run's max idle timeout, 900 s). Recording again after termination replaces that tail with the real end time.
- The run count never changes.
- Output lines are `LEDGER-ACTUAL:`, `LEDGER: … cumulative_usd=X (was Y)` and, when over the cap, `LEDGER-OVER-CAP`.

MANIFEST FIELD CHANGES (experiment-engineer):
- experiments/manifests/15a-emr-size-100.json (S):
  - `budget.max_runtime_minutes` 90 → **75**.
  - Add `pipeline.primary_instance_type: "r5.xlarge"`.
  - Keep `pipeline.instance_type: "m5.xlarge"` (core).
  - Keep `max_usd` 0.84, `max_capacity` 2, `max_task_count` 0 and idle 900.
  - Update the description ("One primary and one core m5.xlarge, 90 minutes").
- experiments/scripts/check_manifests.py:
  - L86-92: g6_estimate must price the primary at its own type.
  - L239: hard-codes 90 min.
- experiments/README.md L32: "90-minute, USD 0.84 runs".
- Every manifest run on the same r5 cluster (size-l, and 25/50 if used) also needs `primary_instance_type r5.xlarge`, otherwise check-cluster refuses the cluster.

ASSUMPTIONS:
- `instance_type` keeps its meaning as the core/task type; without a primary field the primary defaults to it, so existing callers and tests are unchanged.
- The Terraform default primary is r5.xlarge, so no private tfvars edit is needed.
- `EMR_PRICING_CONFIRMED_BY_HUMAN=true` is left as is, on the basis that the go-ahead covers the r5 rates.

RISKS:
- Zero ledger margin (3.36/3.36) before actuals are recorded.
- L at 90 min with the r5 primary (0.98) does not fit after S's 0.84 estimate (3.50 > 3.36). It fits only at 75 min, or after S's recorded actual lowers the total. This needs a human decision if L stays planned.
- The actual is computed from describe-cluster creation/end times and the max of requested and running counts. It is conservative but excludes EBS and EFS.
- An m5 primary with a 12g heap is not blocked by the scripts. Terraform defaults to r5, and check-cluster enforces the manifest's primary type.

MANUAL ACTION REQUIRED:
- The human confirms the r5 rates under the pricing flag semantics.
- After each S run the operator saves the describe-cluster output and runs `--record-actual`.
- Independent code review; terraform plan/apply stay human-gated.

BLOCKED-ON OWNER: test-engineer; experiment-engineer; human (L run cap); coordinator/documentation (P19 numbers).

BLOCKED-ON EVIDENCE:
- tests/infra/emr_module_checks.py:108-111 requires the master group to be m5.xlarge. It will fail with the r5 default (found by inspection, not run).
- tests/scripts/test_cap_pins_14b.py:119-121 and 145-157 pin the old EMR block (2 × (90 + 15) + 20 min = 3.83 h × 0.50). It still passes, but the numbers are stale against 0.555/h at 75 min.
- tests/scripts/sc_support.py:145-146 and test_pipeline_refusals.py:264-268, 310-316, 726-730 still pass; they just have no r5-primary case.
- The experiments/** changes listed above.

NEXT GATE: code-reviewer review of this D3 bundle, then the experiment-engineer manifest update, the human's pricing check and commit.

#### Agent report (2026-11-16T18:57:31.581Z, agent ab94ba7)

STATUS: DONE. This is the follow-up delta (D3, S at 75 minutes, L removed from EMR). S is now a 75-minute run on an r5.xlarge primary, L has no EMR manifest, and `check_manifests` passes in both normal and `--final` modes. This only holds with lane A's uncommitted pins in place. No AWS, no sbt, no commit.

OWNER: experiment-engineer (lane C, follow-up). Before starting I checked my progress log and the files on disk: nothing from the follow-up had landed, so nothing was redone.

WORK ORDER: the coordinator's follow-up items (1) to (5), based on `docs/agent-runs/phase-15/prompt.md` from "L, second size" through "S run cap and D3 go-ahead".

FILES CREATED:
- `/Users/danny/Documents/UIC/CS441/ScholarChain/experiments/inputs/15a/size-l-local-evidence.json` (sha256 3cc87cca…dd28). Schema `scholarchain.experiment-local-evidence.v1`. Its `emr` field reads "NOT an EMR run". It holds the L slice facts (48,187 works, sha256 7e62bb42…), the P6 numbers, and the identity-bypass S/L summaries with their sha256 values and the disclosure text.

FILES MODIFIED (all under `/Users/danny/Documents/UIC/CS441/ScholarChain/experiments/`):
- `manifests/15a-emr-size-100.json` (S), new sha256 b73b8969…9423:
  - `max_runtime_minutes` 90 → 75
  - adds `pipeline.primary_instance_type` = "r5.xlarge"
  - keeps `instance_type` m5.xlarge, `max_usd` 0.84, `max_capacity` 2, `max_task_count` 0, idle 900
  - new description; config sha pins unchanged
- `manifests/15a-emr-size-25.json` and `15a-emr-size-50.json`: restored to their HEAD 7a02de2 bytes (a6ff25a3…, 0d7fe029…) as the Session 1 history. My earlier session had re-rendered them.
- `manifests/15a-emr-size-l.json`: deleted. It was my own untracked file from earlier in this session.
- `scripts/render_manifests.py`: renders only S (75 minutes, r5 primary, m5 core) and never writes the history manifests. The L placeholder and description code is removed.
- `scripts/check_manifests.py`:
  - The L86-92 estimate now prices the primary at its own type: (primary rate + (core + task) × core rate) × (runtime + idle), rounded up to the cent.
  - The hard-coded 90 at L239 is replaced: each manifest's `max_runtime_minutes` must equal its approved cap from `EMR_LEDGER` (history 90, S 75), and the failure message shows the manifest's value.
  - For S it also checks primary r5.xlarge and core m5.xlarge.
  - The ledger charges history ×1 each and S ×2 (run plus one retry).
  - Any other 15A manifest fails as "not in the EMR run set … L is local evidence only".
  - It now checks the L evidence record (it must say "NOT an EMR run" and match the L slice manifest when that exists).
- `scripts/build_l_input.py`: no longer renders manifests; it checks the evidence record instead.
- `tests/test_experiments.py`: tests rewritten and added.
- `README.md`:
  - 15A section and the S run description: 75 minutes, r5.xlarge primary plus m5.xlarge core, ER heap 12g on the primary, USD 0.84 estimate, step timeouts at 75 minutes.
  - Ledger paragraph stating the zero margin.
  - "L: local evidence only" note with the P6 numbers and an identity-bypass table (S next to L), with the disclosure.
  - Run commands now use size-100, and the test counts are updated.

COMMANDS RUN:
- `python3 -I experiments/scripts/render_manifests.py --overwrite --keep-jar-shas`: exit 0, one file rendered (S).
- `python3 -I experiments/scripts/build_l_input.py --output-root target/phase15/lanes/lane-C-l-input-check2`: exit 0. 48,187 works, byte-identical to the L slice, S ⊂ L check PASS (10,577 keys), L-EVIDENCE matches.
- `python3 -I experiments/scripts/check_manifests.py`: exit 0, `RESULT: OK`.
- `python3 -I experiments/scripts/check_manifests.py --final`: exit 0, `RESULT: OK (final: no placeholders)`. Key lines:
  - `15a-emr-size-100.json (size S run and one retry) G6 estimate 0.84 USD <= budget 0.84 USD, charged 2 x`
  - `r5.xlarge primary, m5.xlarge core, 75 minutes`
  - `15A ledger 3.36 USD over 4 runs (Session 1 history + S + one S retry) <= cumulative cap 3.36 USD / 4 runs (margin 0.00 USD, 0 runs)`
  - `size L is local evidence only`
- `python3 -I -W error::ResourceWarning -m unittest discover -s experiments/tests`: exit 0, `Ran 84 tests … OK`. That is 48 in test_experiments, 23 in derive_14c, and 13 identity-bypass tests from the l-bypass lane.

TEST RESULTS: 84/84 pass. The new or changed tests cover:
- the estimate, hand-derived: S at 75 minutes = 0.555 × 1.5 = 0.8325 → 0.84; at 90 minutes 0.97125 → 0.98; at 60 minutes 0.69375 → 0.70; history 0.84;
- S keeps the 75-minute cap and the r5/m5 types, and S is required;
- the history manifests equal their HEAD hashes;
- a `size-l` manifest is refused and not charged to the ledger;
- the ledger shows a zero margin, and the old pins (2.52 USD / 3 runs) give BLOCKED;
- a missing or wrong evidence record fails, and a stale L count fails;
- the renderer writes only S;
- the L build checks the evidence record.

VALIDATION RESULTS:
- **L option chosen: removed from the EMR run set.** There is no L manifest, the renderer cannot produce one, and `check_manifests` fails any `15a-*.json` outside history plus S. The local L evidence is kept in `inputs/15a/size-l-local-evidence.json` and the README.
- **Ledger:** 0.84 + 0.84 (history) + 0.84 + 0.84 (S and one retry) = 3.36 against the 3.36 cap and 4 runs. The margin is zero, as the README says.

ASSUMPTIONS:
- `check_manifests` rounds each run up to the cent (0.84). `budget.py` reserves its own unrounded 0.833, so its cumulative figure is 3.35. Both fit the 3.36 cap.
- The P6 L figures cite the user's statement in prompt.md and `target/phase15/lanes/p6-progress.md`. The bypass figures were read directly from the two `summary.json` files.

RISKS:
- There is no ledger headroom for any further EMR run.
- Both gates pass only because of lane A's uncommitted pins in `release.conf` (EMR_MAX_LIVE_RUNS=4, EMR_CUMULATIVE_CAP_USD=3.36, ceiling 60000, ER_XMX 12g) and the uncommitted lane D L manifest.
- The S Spark step gets 30 minutes at the 75-minute cap. The local P6 S Spark step took 373 s; there is still no EMR measurement.

MANUAL ACTION REQUIRED: human review of the diff, and an explicit yes before committing.

BLOCKED-ON OWNER: none for this delta. The upload and pipeline handling of `primary_instance_type` and `--hadoop-config` are lane A's work in `scripts/`; I did not verify them here.

BLOCKED-ON EVIDENCE: none.

NEXT GATE: independent code-reviewer verdict on `experiments/**`, then human approval. The progress log is at `/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/lane-C-progress.md` (section 7).

#### Agent report (2026-11-16T18:58:06.373Z, agent a9d438f)

STATUS: COMPLETE. The L-dropped / D3 / EMR-actuals pass is applied to both files. The project total at caps is **22.98, within the 23.00 limit (margin 0.02)**, so I did not need to stop. I checked the progress log and the plan first: none of this pass had been applied before, so no edit was applied twice.

OWNER: documentation-engineer
WORK ORDER: Phase 15 documentation pass after the human's "L, second size", D3, S-run-cap and EMR-actuals decisions (prompt.md from "L, second size" to the end).

FILES MODIFIED (both untracked):
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md (now 1117 lines)
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/demo-script.md (now 269 lines)

FILES CREATED: none in the repository. The progress log was appended: /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/lanes/doc-neptune-progress.md. Edit scripts are in the scratchpad (edit1.py, edit2.py, edit3.py).

COMMANDS RUN (no AWS, Anthropic or Voyage call; no sbt or Terraform; no commit):
- Reads: prompt.md lines 233 to the end; lane logs p6-progress.md, lane-A-p6-progress2.txt, lane-A-progress.md, l-bypass-progress.md.
- `ls` and `shasum -a 256` on the retained directory: layout is spark/, render/, provenance.json, SHA256SUMS; the SHA256SUMS sha256 is c9b3fb2d… and matches the log.
- `grep -n` on the working-tree scripts/run-bounded-pipeline.sh (lines 18, 67-70, 124-126) and scripts/lib/budget.py, which hold `--record-actual`.
- Edits with `python3 -I` exact-replacement scripts (each asserts one match). A stale-copy grep confirmed that every remaining old value is a history line. No 12-digit literals.

ROUNDING METHOD (written into section 6.4):
- The plan's EMR rate is the model rate plus about 0.02 for EBS, as in 0.48 + 0.02 = 0.50. Here 0.555 + 0.02 = 0.575, rounded up to the cent, so **0.58 per cluster-hour**.
- Each block is hours x rate, rounded to the cent.
- At the exact 0.555 rate with no EBS margin, the block would be 1.85 and the project at caps 22.90. Both ends sit inside the coordinator's range of 22.90-22.98.

CHANGED NUMBERS:

| Location | Old | New |
|---|---|---|
| EMR rate (6.1, 6.3, rates table) | 0.50 per cluster-hour (2 x m5.xlarge) | 0.58 (r5.xlarge 0.315 + m5.xlarge 0.240 = 0.555 model, plus EBS) |
| EMR cap block (6.3, P19 item 3) | 3.83 h = 1.92 (S + L, 90-min runs) | 3.33 h = 1.93 (S and its retry: 2 x (75 + 15) + 20 min; 3.333 x 0.58 = 1.933) |
| EMR planned (6.3, 5.2 duration line) | 2.05 h = 1.03 (S 0.30, L 0.55, boot and idle 0.18) | 0.96 h = 0.56 (S 0.35, boot and idle 0.21) |
| R0 planned / cap | 1.64 / 3.57 | 1.17 / 3.58 |
| R0 project | 17.47 / 19.40 | 17.00 / 19.41 |
| R0 + R-b planned / cap | 4.18 / 7.14 | 3.71 / 7.15 |
| Project, planned / caps (summary, 6.2, 6.3a, 6.4, P19 item 1) | 20.01 / 22.97 (margin 0.03) | 19.54 / 22.98 (margin 0.02) |
| Low-scenario row | 3.80 / 6.08; 19.63 / 21.91 | 3.33 / 6.09; 19.16 / 21.92 |
| E_b; gate 1 threshold | 3.57; 2.85 | unchanged (R-b has no EMR part) |
| Planned X_a | 1.35, passes by 1.50 | 0.88, passes by 1.97 (1.35 - 2.05 x 0.50 + 0.96 x 0.58) |
| X_a formula, EMR term | measured cluster-hours x 0.50 | recorded EMR actuals of the Session 2 runs (ledger cumulative minus Session 1's 1.68) |
| Pre-R-b check, planned | 15.83 + 1.35 + 3.57 = 20.75 (margin 2.25) | 15.83 + 0.88 + 3.57 = 20.28 (margin 2.72); EMR part = recorded actual |
| AWS-only alerts, R0 | 17.39 / 18.92 | 16.92 / 18.93 (alerts unchanged: none / 18) |
| AWS-only alerts, R0 + R-b | 19.93 / 22.47 | 19.46 / 22.48 (alerts unchanged: 18 / 18, 20 and 22) |
| Session 2 AWS cap for the credit check (4a item 2, 5.1, 6.2, 6.7) | 6.72 | 6.73 (7.15 - 0.42) |
| S run cap | 90 min | 75 min; step timeouts 225 / 900 / 900 / 225 / 1800 / 450 s |
| Ledger (P25 row, Q5 row, P19) | 4 x 0.84 for 90-min runs | 1.68 + 0.84 + 0.84 = 3.36 against the 3.36 cap, zero margin (3.35 unrounded) |
| Report: EMR cluster row | 2 x m5.xlarge, 90 min | r5.xlarge primary + m5.xlarge core, ER heap 12g, 75 min |
| Report: graph edges at L | estimate "about 1.5M" | measured locally with ER bypassed: 320,690 (S 81,181) |
| Report: R-b increment | 2.54 | unchanged (3.71 - 1.17) |
| R-c record row | 5.59 / 10.25 | not recomputed (record only; stated in 6.4) |

OTHER CHANGES:
- **(1) L dropped on EMR.**
  - Removed from: summary stage a, priority list, 3a rows, stage-a conclusion, 5.2 heading and steps 3, 5, 6, 7, the L stop rule, the gate-1 S line, the 6.7 Wed and 08:30 rows, two risk rows, the Q6 outcome, and the report rows (EMR scale, edges, not-evaluated).
  - Step 6 is now "S retry only if S failed". The gate-1 time stays at 10:45, because the ingest still needs that time.
  - L local evidence is reported in the plan, in P19 item 3 and in demo items 9 and 10. The ER bypass is disclosed verbatim each time.
- **(3) New 5.2 step 5a, EMR actuals.** It runs after each S run and after the retry:
  - `aws emr describe-cluster --region us-east-2 --cluster-id <j-id> --output json > <private file>`, with the operator profile;
  - then `scripts/run-bounded-pipeline.sh --record-actual --run-id <id> --describe <file> [--as-of-utc <UTC>]`.

  The human's rule is quoted. Both commands are cited as working-tree, unreviewed D3 drafts. Gate 1 and the pre-R-b check (5.2 and 6.4) now use the recorded actuals.
- **(4) P19 section 4a.** Items 1-3 now carry the new numbers: cluster rates, ER 12g, 75-min cap and step timeouts, the 1.93 block, the zero-margin ledger, actuals recording, and L dropped with its local evidence. Item 2 asks for 6.73.
- **(5) P6 row.**
  - Results: S passed all 6 steps, final run p6-S-20261116T171431Z (47 / 165 / 490 / 5 s). D1 and D2 are fixed and tested.
  - Retention path: target/phase15/p6/size-S/run:b8df1ae6-a66e-4e6e-84c7-6cb3169fd0ae/, with the sha256 above.
  - The P6 row and step 7b.1 now give `cd "<dir>" && shasum -a 256 -c SHA256SUMS`, because the paths in SHA256SUMS are relative.
  - "Do not run `sbt clean`" warning: the build has no keep rule, so a root clean would delete the retention.
- **(6) demo-script.md:**
  - The items 9 and 10 table rows, the item 9 Say/Show text and the item 10 Show text now show S on EMR plus the L local evidence.
  - "two real DBLP sizes on the same cluster" is replaced.
  - Section 4 is updated, and an amendment line is added.
- Provenance and the header history entry are updated in the plan.

TEST RESULTS: not applicable (docs only).

VALIDATION RESULTS: every remaining copy of 4.18, 7.14, 22.97, 20.01, 6.72, 1.64, 17.47 / 19.40, 19.93, 22.47 and 20.75 is a history line or a derivation input. No 12-digit literals. No new links were added.

ASSUMPTIONS:
- Planned S-only EMR hours are 0.96 h, taken from the plan's own 5.2 split (S 0.60 h + boot and idle 0.36 h).
- Stage-a hours and the schedule are unchanged.

RISKS:
- **Retention is not from the frozen commit.** It came from run p6-S-20261116T164523Z, made on the working tree with the D1/D2 workaround. Requirement (d) still needs a rerun on the frozen commit.
- **The `--record-actual` commands are unreviewed and uncommitted** (D3 infra change).
- **Margins are thin:** 0.02 on the project total and zero on the ledger.
- Demo items 9 and 10 now carry more content than their 45 s slots; the timing was not re-checked.

MANUAL ACTION REQUIRED:
- The human: decide about `sbt clean` retention (a build-engineer change or a standing "do not clean").
- P6 lane: rerun P6 S on the frozen commit.
- The human: read the credit balance (at least 6.73).

BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: code-reviewer read of 4a, 5.2 steps 5a/6/7b, 6.3-6.4 arithmetic and demo items 9-10; then the human's P19 signature.

#### Agent report (2026-11-16T19:28:37.275Z, agent a54f56f)

STATUS: COMPLETE. The D3 test work is done: r5 primary, the cap-pins block, the r5 refusal cases and the `--record-actual` black-box test. Final runs: tests/scripts 482 of 482 passed, tests/infra 468 of 468 passed.

OWNER: test-engineer
WORK ORDER: D3 follow-up (r5.xlarge primary, m5.xlarge core, ER heap 12g, S run cap 75 min). I resumed from the progress log after the interruption; nothing had been edited before it.

FILES MODIFIED:
- **tests/infra/emr_module_checks.py L92, L108-113:** the master group must be one r5.xlarge and the core group one m5.xlarge (was: both m5.xlarge). Any other type still fails the check.
- **tests/infra/test_emr_module_13c.py:**
  - `scenario_g6_bounds` now derives the r5 rate by hand: 0.252 + 0.063 = 0.315.
    - r5 primary + core + 1 task: 0.795 x 3.25 = 2.58, at or under the USD 3 per-run cap.
    - A second task node: 3.36, over the cap.
    - Primary r5.xlarge or m5.xlarge is accepted. m5.2xlarge, r5.2xlarge and r6i.xlarge are refused.
  - Three new mutations, all caught:
    - the primary-type validation relaxed;
    - the primary default reverted to m5.xlarge;
    - the master group wired to the core type. My first anchor for this one hit the caps-locals line; I scoped it to the master group with `replace_after`.
- **tests/scripts/test_cap_pins_14b.py:**
  - The old 90-min block (3.83 h x 0.50 = 1.92) is kept, labelled pre-D3 history.
  - NEW `test_d3_emr_block_…`:
    - 2 x (75 + 15) + 20 = 200 min = 3.33 h, at 0.555/h = **1.85 exactly**.
    - With the coordinator's 0.58/h margin rate the block is 1.93, rounded half-up as the plan does.
    - Project at caps (15.83 + 7.14 - 1.92 + block): 22.90 exact and 22.98 with the margin, both at or under 23.00.
    - A 90-min cap at 0.555/h would exceed 23.00.
  - NEW `test_d3_ledger_fills_the_cumulative_cap_exactly`: per run 0.555 x 1.5 = 0.8325, rounded up to 0.84. 1.68 + 0.84 + 0.84 = 3.36 against the 3.36 pin, zero margin; one cent more is over.
  - The plan's 6.4 figures (7.14 / 22.97) are still asserted as published. Once the documentation-engineer publishes the D3 rounding, those constants need a hand-copied update.
- **tests/scripts/test_pipeline_refusals.py**, five new cases in PipelineClusterRefusals:
  - r5 primary with m5 core is accepted, the estimate is 0.70 ((0.315 + 0.240) x 1.25 h), and the output shows `primary_type=r5.xlarge`.
  - An m5 primary is refused when the run states r5 ("MASTER group uses m5.xlarge, not the approved r5.xlarge").
  - An r5 core is refused with or without an r5 primary.
  - An r5 primary is refused when the run does not state it.
  - 75-min S run: the estimate is 0.84. Ledger [0.84 x 3] lets L through at 3.36. Ledger [0.84, 0.85, 0.84] gives 3.37 and is refused at g6-gate.

FILES CREATED:
- **tests/scripts/test_record_actual_15.py** (4 tests). It is black-box: a green r5 `--execute` with the fakes reserves the run and writes its manifest. The test then writes a synthetic describe-cluster JSON and runs `--record-actual`.
  - **Ended cluster, 1 h:** measured 0.56, tail 0.00, reserved estimate 0.70 replaced. Cumulative 2.38 -> 2.24, live_runs stays "3 of 4", the reserve records are unchanged, no cloud call, and the next dry run is not refused.
  - **RUNNING cluster:** refused without `--as-of-utc`. With it, measured 0.56 plus a 900 s tail of 0.14 gives 2.38.
  - **Cap boundary:** 10897 s gives 1.68 and a total of 3.36, with no marker. 10898 s gives 1.69 and 3.37, prints LEDGER-OVER-CAP, the run count stays 3, and the next dry run reports that `--execute` would be refused.
  - **Refusals leave the ledger byte-identical:** another cluster id, a group without a reviewed rate (r6i.xlarge), a run that was never reserved.

COMMANDS RUN (offline; no sbt, no AWS):
- `python3 -I -m unittest discover -s tests/infra -p 'test_emr_module_13c.py' -v`:
  - first run: Ran 37, 1 failure (my anchor bug);
  - after the fix: `-k primary` Ran 5, OK.
- `python3 -I -m unittest discover -s tests/scripts -p 'test_cap_pins_14b.py'`:
  - first run: 1 failure (I had used ROUND_UP; switched to half-up);
  - after the fix: Ran 15, OK.
- `python3 -I -m unittest discover -s tests/scripts -p 'test_pipeline_refusals.py' -k test_d3` → Ran 5, OK.
- `python3 -I -m unittest discover -s tests/scripts -p 'test_record_actual_15.py'`:
  - first run: 1 failure (my synthetic `--as-of-utc` was dated in the future; moved the times to 2026-11-15);
  - after the fix: Ran 4, OK.
- Mutation check on fixture copies only (/private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/mutate_d3.py). All 5 mutants killed:
  - check-cluster compares MASTER with the core type;
  - check-cluster accepts any core type;
  - an actual frees a run slot;
  - no over-cap marker;
  - the estimate is not replaced.
- `python3 -I -m unittest discover -s tests/scripts -p 'test_*.py'` → **rc 0, Ran 482, OK**, 0 skipped (1308.6 s).
- `python3 -I -m unittest discover -s tests/infra -p 'test_*.py'` → **rc 0, Ran 468, OK** (967.6 s).
  - test_emr_module_13c is included and ran offline: EmrModuleTree runs `terraform init -backend=false -lockfile=readonly -plugin-dir=<local providers>` with an isolated TF_DATA_DIR, so there is no registry or network access.

TEST RESULTS: tests/scripts 482/482 passed; tests/infra 468/468 passed.

VALIDATION RESULTS:
- Only tests/** changed. Modified: tests/infra/emr_module_checks.py, tests/infra/test_emr_module_13c.py, and six files in tests/scripts (sc_support, cap_pins_14b, pipeline_dryrun, pipeline_refusals, prespend_floors_14b, providers_14b). Created: copyout_selection_15, hadoop_prep_args_15, record_actual_15.
- No production edits, no 12-digit literals, no commit or stash.
- The progress log is target/phase15/lanes/test-pins-progress.md.

ASSUMPTIONS:
- The project-at-caps figures replace only the EMR block inside the plan's published 7.14. I used the coordinator's 0.58/h margin with half-up rounding, as for the old 1.915 -> 1.92 block.
- The 75-min run uses the budget.py round-up rule per run.

RISKS:
- The D3 ledger has zero margin (3.36 / 3.36).
- The plan's final D3 rounding is not yet published. When it is, the 6.4 constants (7.14 / 22.97) and the 1.93 margin block must be hand-updated.
- test_record_actual_15 uses fixed 2026-11-15 timestamps. They stay valid because the `--as-of-utc` future check only rejects times later than now.

MANUAL ACTION REQUIRED: none.
BLOCKED-ON OWNER: none.
BLOCKED-ON EVIDENCE: none.
NEXT GATE: code-reviewer on the tests/** diff, then the coordinator's `sbt check`.

#### Agent report (2026-11-16T19:30Z, agent a54f56f, test-engineer, final constants follow-up)

tests/scripts/test_cap_pins_14b.py now uses the published D3 figures: R0 cap 3.57→3.58, R0 + R-b cap 7.14→7.15, project at caps 22.97→22.98, margin 0.03→0.02, AWS cap 6.72→6.73, and a new check that the 0.58/h rate gives the 1.93 block and the 3.58 R0 cap. The pre-D3 figures (3.57, 7.14, 22.97, column B 25.44) are kept as history asserts.
Re-run, offline and without sbt: `python3 -I -m unittest discover -s tests/scripts -p 'test_cap_pins_14b.py'` → Ran 15, OK; `python3 -I -m unittest discover -s tests/scripts -p 'test_pipeline_refusals.py' -k test_d3` → Ran 5, OK.


## Pipeline repair round 1 (review 1 findings and the 3.53 ledger-cap decision), agent reports, verbatim

#### Agent report (2026-11-16T20:57:09.800Z, agent acf0957)

STATUS: DONE (both tasks complete, gates observed passing)
OWNER: experiment-engineer
WORK ORDER: Phase 15, review finding 3 plus user decision 2026-11-16 "Raise cap to 3.53"

FILES CREATED: none
FILES MODIFIED (experiments/** only):
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/README.md line 35 (Ledger paragraph)
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/tests/test_experiments.py lines 252, 255, 449, 450, 471

CHANGES (old to new):
- README:35 finding 3: the sentence "budget.py reserves its own unrounded estimate (0.833 per S run, cumulative 3.35 per the coordinator's figures in prompt.md); this check rounds each run up to the cent" is replaced. It now says budget.py also rounds the per-run estimate up to the cent, so it reserves 0.84 per S run (0.555/h x 90 min = 0.8325, rounded up to 0.84), the same as this check, and the 4-run cumulative is 3.36 in both. The 0.833 and 3.35 figures are gone.
- README:35 cap: `EMR_CUMULATIVE_CAP_USD=3.36` becomes `3.53`, with the user decision recorded (1.68 Session 1 + 1.85). Margin "USD 0.00 and 0 runs" becomes "USD 0.17 and 0 runs (3.53 - 3.36)". It also says the 0.17 cannot pay for another 0.84 run, so any further EMR run still needs a new human decision.
- test_experiments.py:252: docstring "(4 runs, 3.36 USD)" becomes "(4 runs, 3.53 USD cap)".
- test_experiments.py:255: pin_session2 pin `EMR_CUMULATIVE_CAP_USD` 3.36 becomes 3.53.
- test_experiments.py:449: comment updated to "against the 3.53 USD / 4-run P25 cap: margin 0.17 USD and 0 runs".
- test_experiments.py:450: the expected line "cumulative cap 3.36 USD / 4 runs (margin 0.00 USD, 0 runs)" becomes "cumulative cap 3.53 USD / 4 runs (margin 0.17 USD, 0 runs)".
- test_experiments.py:471: the pin restored after the 2.52 case, 3.36 becomes 3.53.

3.36 LEFT UNCHANGED, because each is the cumulative total of reserves (0.84 x 4), not the cap:
- README:35, "USD 3.36 over 4 runs" and the new "3.36 in both".
- test_experiments.py:381, "15A ledger 3.36 USD over 4 runs" (the total in the refused-manifest check).
- test_experiments.py:449, the "= 3.36" total in the comment.
- test_experiments.py:470, "CHECK-BLOCKED: 15A ledger 3.36 USD over 4 runs". The 2.52 cap in that line is the pre-P25 pin and is unchanged.

No script or manifest needed edits. check_manifests.py reads the cap from scripts/config/release.conf, and `grep -rn "3\.36" experiments` found no 3.36 in experiments/manifests, experiments/inputs or experiments/scripts. No pinned sha256 covers release.conf (config-sources.json lists only the four config files), so render_manifests.py did not need rerunning.

COMMANDS RUN:
- `grep -rn "3\.36\|3\.35\|0\.833" experiments`
- `python3 -m unittest discover experiments/tests`
- `python3 experiments/scripts/check_manifests.py`

TEST RESULTS: `python3 -m unittest discover experiments/tests` printed "Ran 84 tests in 3.128s" and "OK". This ran against the infra-engineer's already-edited scripts/config/release.conf, where line 245 reads `EMR_CUMULATIVE_CAP_USD=3.53`.

VALIDATION RESULTS: `python3 experiments/scripts/check_manifests.py` exited 0 with "RESULT: OK (placeholders allowed; run with --final before the commit freeze)". The ledger line is "CHECK-OK: 15A ledger 3.36 USD over 4 runs (Session 1 history + S + one S retry) <= cumulative cap 3.53 USD / 4 runs (margin 0.17 USD, 0 runs)". I did not run it with --final.

ASSUMPTIONS:
- The README "0.555/h x 90 min" wording follows your instruction. It is the 75-minute cap plus the 15-minute idle tail, consistent with the infra-engineer's release.conf comment at line 237.
- I did not run `scripts/lib/budget.py`. I stated its rounding on the strength of your finding.

RISKS:
- The tests depend on release.conf carrying 3.53 only through the pins the tests write themselves, so they pass either way. The live check_manifests.py run does read the real release.conf, which is already 3.53.

MANUAL ACTION REQUIRED: none
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: independent code-reviewer re-check of experiments/README.md:35 and the test edits. The human commit gate applies; I did not commit.

#### Agent report (2026-11-16T20:57:49.074Z, agent a47f343)

STATUS: COMPLETE. All six tasks are done in `docs/runbooks/session-2-plan.md`. I changed nothing in `docs/demo-script.md`. No BLOCKED-ON. The only gate I ran was my own link/PII scan, because `scripts/check.sh` has no docs link-check gate.

OWNER: documentation-engineer
WORK ORDER: Phase 15, user decision "Raise cap to 3.53" plus pipeline-bundle review 1 findings 1, 2, 4 (line 442) and 8. Branch phase-15, HEAD f801d28.

FILES CREATED: none
FILES MODIFIED: `/Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md` (uncommitted)
- `docs/demo-script.md`: I grepped it for 3.36, 3.35, 90-min and cap figures and found no stale figure.
- I did not touch `docs/agent-runs/**`.

CHANGES (line numbers are after the edit):
1. **Cap 3.36 → 3.53**
   - **P25 row, line 256.** The cap reads "2.52 → **3.53** (was 3.36 = 4 x 0.84)". The row now has the decision text and the arithmetic 3.53 = 1.68 + 3.33 h x 0.555/h = 1.85. The worst case is 1.68 + 0.84 + 0.84 = 3.36 of 3.53 before actuals. It says the project figures do not change: 19.54 / 22.98, EMR block 3.33 h = 1.93, pre-R-b check spend + 3.57 ≤ 23.00. The ledger test acceptance now reads "cumulative-cap refusal at 3.53 (was 3.36)".
   - **P19 approval-record draft (section 4a), lines 317-328.** The old text "USD 3.36 cumulative … zero margin" is replaced. It now says 3.53 (was 3.36), the 1.85 arithmetic, the 3.36-of-3.53 worst case, and that the project figures are unchanged.
   - **Section 5.** The old 3.36 text at lines 317-319 was in the 4a draft, not section 5 proper, so it is covered by the bullet above. Section 5's step 5a at line 443 now carries the cap too.
   - **Q5 row, line 1070.** It now reads "raise to 4 runs / 3.36 (was; now 3.53)" and the worst case 3.36 of 3.53. This was an extra stale place I found.
2. **Finding 1, steps 5a and 6**
   - **Step 5a, new sub-bullet at line 443.** After S's actual is recorded, the retry is admitted only if S's measured cost (from cluster creation, boot included) is ≤ 0.87. That is 3.53 − 1.68 − 0.84 − 0.14 tail, about 94 min at 0.555/h. Otherwise the retry is refused (fail-closed) and the plan goes to the step 7b fallback (P6 local S export). It also says not to edit the ledger to get around the refusal.
   - **Step 6, line 444.** It has the same condition, with the refusal routing to step 7b.
   - **4a draft, lines 324-328.** It has the same condition, so the approval record carries it.
3. **Finding 2, P18 precondition, line 426 (5.2 step 1).**
   - It runs `terraform -chdir=infra/terraform state list`, which prints addresses only. It says never to read the state file.
   - The output must be exactly `terraform_data.configuration_guard` and `terraform_data.provider_guard`. I took these from `owner-report.md` near line 2032.
   - Anything else means stop and report to the human, and do not plan. Otherwise plan stage a against the leftover state with no move-aside.
   - The user's wording is quoted verbatim.
4. **Line 442 → line 458.** "two full 90-minute S runs" now reads "two full S runs (each up to the 75-minute cap)".
5. **Finding 8, 4a draft, lines 321-323.**
   - It restates the r5.xlarge primary rate as EC2 0.252 + EMR 0.063 = 0.315/h, the m5.xlarge core rate as 0.240/h, and the cluster total as 0.555/h. It notes these sit under `emr-pricing.conf`'s human pricing confirmation.
   - The earlier "Cluster:" line was shortened so the rates appear once.
6. **Other stale items fixed:**
   - **Line 188, F19.** It still says 3.36 > 2.52, which is correct as found. I changed "Each 90-minute run" to "As found (before D3) … since D3 an S run is capped at 75 min and reserves 0.84 = 0.555/h x (75 + 15) min".
   - **Line 238, P6 results.** "Use the local L time to confirm L fits the 90-minute EMR cap" now says it is superseded: L is dropped, the S cap is 75 min, and the step timeouts sum to 4500 s.
   - **Line 990, risk table.** "the 90-minute cap stays" now says the S cap is 75 min (D3; was 90).
   - **Line 1071, Q6.** "90-minute cap" now says "EMR cap (at the time, 90 min; the S cap is now 75 min)".
   - **Intentional history left unchanged.** Line 783 (pricing "was" row) and line 1047 (cluster-size "was 2 x m5.xlarge, 90 min") keep their "was" wording. Lines 188, 256 and 317-319 keep 3.36 as the old cap or the worst case.

NUMBERS CHANGED (old → new):
- EMR ledger cap: 3.36 → 3.53 (P25 row, 4a draft, Q5, acceptance test text).
- Ledger headroom: zero margin → 3.36 of 3.53.
- New figures: retry admission threshold ≤ 0.87 and about 94 min from cluster creation (3.53 − 1.68 − 0.84 − 0.14 = 0.87; 0.87 / 0.555 = 1.568 h = 94.1 min).
- 90-min S run wording → 75-min cap (lines 188, 238, 458, 990, 1071).
- Unchanged and restated: 19.54 / 22.98, EMR block 3.33 h = 1.93, pre-R-b check spend + 3.57 ≤ 23.00, 0.555/h, 0.315/h, 0.240/h, 0.252 + 0.063.

COMMANDS RUN:
- `grep -n "3\.36\|90-min\|90 min\|90-minute"` on both files, before and after the edits.
- A one-off Python replace script in the scratchpad, `edit_docs.py`. It asserted that each target string matched exactly once.
- `grep -n "EMR_CUMULATIVE_CAP_USD=" scripts/config/release.conf`
- A `python3 -I` script that checks relative markdown links and scans for 12-digit numbers and e-mail addresses.

TEST RESULTS: not applicable.

VALIDATION RESULTS (observed):
- `release.conf:245` already reads `EMR_CUMULATIVE_CAP_USD=3.53`.
- `release.conf` line 235 still carries a "3.36 cumulative" comment. That is the infra-engineer's file, and the parallel update may still be in progress.
- The 0.84 reserve, 0.315 and 0.240 rates, and the 0.14 tail (900 s at 0.555/h) match `scripts/lib/budget.py` and the review's arithmetic. The 19.54 / 22.98, 3.33 h = 1.93, 3.57 and 23.00 figures match `docs/agent-runs/phase-15/prompt.md` and the runbook's own tables.
- Link check on both files: session-2-plan.md has 20 relative links with 0 broken, and demo-script.md has 2 with 0 broken.
- Neither file contains a 12-digit number or an e-mail address.
- `scripts/check.sh` has no docs link-check gate, so I used my own script, and its output is the only link evidence.

ASSUMPTIONS:
- The old "3.36" in the 4a draft was the "section 5" text the work order meant (lines 317-319).
- The two guard addresses are exactly `terraform_data.configuration_guard` and `terraform_data.provider_guard`, per `owner-report.md` line 2032.

RISKS:
- `budget.py` computes the retry admission, and no test of "S times out, actual recorded, retry" exists yet. That is the test-engineer's item from finding 1.
- The 94-minute figure rounds 0.87 / 0.555 = 94.05 min. The ledger's cent rounding on the measured cost could shift it by about a minute.

MANUAL ACTION REQUIRED: The human should review the new wording in 4a and 5.2 before recording the P19 approval. The 4a draft now states the retry-admission rule and the restated rates for that record.

BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none

NEXT GATE: independent review of the diff, then the human P19 approval record. The infra-engineer should also fix `release.conf:235`, which I did not touch. No commit was made.

#### Agent report (2026-11-16T21:22:55.139Z, agent ad00bea)

STATUS: DONE. Cap pins moved to 3.53 and the finding-1 scenario tests are added. Both gates pass against the release.conf that has landed (`EMR_CUMULATIVE_CAP_USD=3.53`).

OWNER: test-engineer (tests/** only; no production, scripts/ or infra/ edits)

WORK ORDER: Phase 15, branch phase-15, HEAD f801d28. User decision 2026-11-16 "Raise cap to 3.53" (1.68 Session 1 + 1.85). Review finding 1.

FILES CREATED: none

FILES MODIFIED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts/test_cap_pins_14b.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts/test_pipeline_refusals.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts/test_prespend_floors_14b.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts/test_record_actual_15.py

Task 1, 3.36 -> 3.53 in the pins and boundaries:
- test_prespend_floors_14b.py asserts `EMR_CUMULATIVE_CAP_USD == 3.53`.
- test_cap_pins_14b.py:
  - `EMR_CAP` is now 3.53, and a `SESSION_2_BLOCK` of 1.85 was added.
  - The hand derivation is 1.68 + 1.85, where 1.85 is 200 min x 0.555/h, exact. The old test claimed 4 x 0.84 equals the cap, which is no longer true.
  - The string pin is "3.53".
  - "Two more runs fit" is now `int((cap - spent) / 0.84) == 2` with `cap - spent == 1.85`.
  - The R0-block allowance is now 1.85.
  - The D3 ledger test is renamed `test_d3_ledger_leaves_a_seventeen_cent_margin_under_the_cumulative_cap` (total 3.36, margin 0.17).
- test_pipeline_refusals.py, every boundary recomputed (prior ledger sum plus estimate = 3.53 allowed, one cent more refused):
  - Default run 0.60: 1.46 + 1.47 allowed, 1.46 + 1.48 refused.
  - Mid run 1.26: 2.27 allowed, 2.28 refused.
  - Big run 2.88: 0.65 allowed, 0.66 refused.
  - S/L case: 0.84 + 1.01 + 0.84 allowed, 0.84 + 1.02 + 0.84 refused. I added an "L exactly at the cap" case.
  - The old 2.52 and 3.36 boundaries, plus one cent, are asserted allowed under 3.53.
  - D3 test renamed to `test_d3_the_75_minute_s_run_and_l_fit_under_3_53_with_a_seventeen_cent_margin`.
- test_record_actual_15.py: the over-cap test now uses 12000 s (0.555 x 12000/3600 = 1.85 exact, total 3.53, no marker) and 12001 s (1.850154 -> 1.86, total 3.54, LEDGER-OVER-CAP). The comment 3.36-2.24 became 3.53-2.24 = 1.29.

The 3.36 values I left alone:
- tests/infra/test_emr_module_13c.py:54 is "1.035 x 3.25 = 3.36375 > 3". That is a per-run cost against the per-run cap of 3, not the cumulative cap. It is unchanged and needs no change; the file has no `EMR_CUMULATIVE_CAP_USD` pin.
- In test_pipeline_refusals.py, the `3.36` in the S/L docstring, the D3 docstring and the default-ledger comments is the genuine sum 2.52 + 0.84 or Session 1 + S + L = 3.36. I kept it and added that it is at most 3.53. Other 3.36 mentions are history notes in docstrings and comments (P25 value).

TESTS ADDED, all in test_record_actual_15.py, class `TimeoutThenRetryOnTheSameCluster`. They drive the real run-bounded-pipeline.sh `--execute` and `--record-actual` code paths through budget.py, with fakes for the cloud binaries:
- `test_the_cap_and_run_limit_in_release_conf_are_the_hand_derived_ones`
  - Reads `EMR_CUMULATIVE_CAP_USD` and `EMR_MAX_LIVE_RUNS` from release.conf.
  - Asserts the cap equals 1.68 + 0.87 + 0.14 + 0.84 = 3.53 and the run limit is 4.
- `test_retry_at_exactly_the_cap_is_admitted_and_a_fifth_run_is_refused_by_the_run_limit`
  - Session 1 at 1.68 and S reserved at 0.84 (75-min plan, 0.555 x 5400/3600 = 0.8325 -> 0.84).
  - Actual recorded for a running cluster 5643 s after creation: measured 0.87, tail 0.14, cumulative 2.69, `live_runs=3 of 4`.
  - The retry (estimate 0.84) is admitted: 2.69 + 0.84 = 3.53 <= 3.53.
  - The fifth run is refused at the g6-gate with "4 live EMR runs are already recorded in the ledger (limit 4)", and the ledger file is byte-identical afterwards.
- `test_retry_one_cent_over_the_cap_is_refused_with_the_cumulative_cap_message`
  - The actual is recorded at 5700 s: measured 0.88, tail 0.14, cumulative 2.70, no LEDGER-OVER-CAP.
  - The retry is refused at the g6-gate with "cumulative estimate 3.54 USD (recorded 2.70 + this run 0.84) would exceed the cap 3.53 USD".
  - The run-limit message is absent and no reservation is added.

COMMANDS RUN (all offline, from /Users/danny/Documents/UIC/CS441/ScholarChain):
- `grep -rn "3\.36" tests`
- `python3 -m unittest test_record_actual_15`, run from tests/scripts: Ran 7 tests in 44.631s, OK
- `python3 -m unittest discover tests/scripts`
- `python3 -m unittest discover tests/infra`

TEST RESULTS (observed):
- `python3 -m unittest discover tests/scripts`: "Ran 485 tests in 1400.443s", "OK", exit 0
- `python3 -m unittest discover tests/infra`: "Ran 468 tests in 986.691s", "OK", exit 0

VALIDATION RESULTS: release.conf already had `EMR_CUMULATIVE_CAP_USD=3.53` before the gate runs, so no failures are attributable to the infra-engineer change landing late. I made no network calls and read none of the forbidden files. I wrote no new 12-digit numbers.

ASSUMPTIONS:
- The 5643 s and 5700 s timeout durations are my choice. They are the only whole-second values that give measured 0.87 and 0.88 with the 0.555/h cluster rate and a 900 s tail of 0.14.
- The scenario test is placed in test_record_actual_15.py next to the other `--record-actual` tests.

RISKS:
- The scenario test's S timeout is modelled as a still-running cluster that is recorded with `--as-of-utc` (the tail applies). A terminated cluster would carry no tail and so is not what finding 1 describes.
- The gates are slow (about 23 and 16 minutes when run in parallel).
- I did not run mutation testing; the exact-message assertions (3.54 vs 3.53, 2.69 vs 2.70) are the discriminators.

MANUAL ACTION REQUIRED: none

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: Independent code-reviewer review of the 4 test files. `sbt check` was not run, since no Scala inputs changed and the repair-round scope rule says to skip it. The human decides acceptance and commit; I made no commit.

#### Agent report (2026-11-16T22:02:12.366Z, agent ae61105)

STATUS: COMPLETE (offline; all four tasks done; all gates observed green)
OWNER: infra-engineer (scripts/**, infra/terraform/**)
WORK ORDER: Phase 15 repair round after code review (tasks 1 to 4)

FILES CREATED: none

FILES MODIFIED (all inside the infra-engineer territory)
- scripts/config/release.conf
  - ~60-61 (PRESPEND comment): 22.97 -> 22.98 and 2.03 -> 2.02 (both occurrences each).
  - ~236-245 (EMR block): the stale "exactly 2 more 90-minute runs (S and L) fit / no L retry" is replaced. It now says S and one S retry at the 75-minute cap (0.555 USD/h x 1.5 h = 0.8325 -> 0.84, no L run on EMR). A new comment records the user decision "Raise cap to 3.53", the arithmetic 1.68 + 3.33 h x 0.555 = 1.85, and the retry rule (admitted iff S measured <= 0.87).
  - `EMR_CUMULATIVE_CAP_USD` 3.36 -> 3.53. `EMR_MAX_LIVE_RUNS` stays 4 and `EMR_MAX_RUN_USD` stays 3.
  - ~323 (before `PIPELINE_MAX_COPYOUT_BYTES`): comment added. EMR now runs S only (copy-out about 1.1 GB); the 8 GiB ceiling stays as an upper bound (user-approved default; changing it would also change the reviewed pins). The value is unchanged at 8589934592.
- scripts/run-bounded-pipeline.sh line 111 (help text): "EMR_CUMULATIVE_CAP_USD (3.36)" -> (3.53).
- scripts/README.md
  - Line 315: the old text said "90 minutes, ... 4 x 0.84 = 3.36 equals the cap exactly". It now describes the 75-minute S run (0.555 x 1.5 = 0.8325 -> 0.84, r5 primary + m5 core), cap 3.53 = 1.68 + 3.33 h x 0.555, and S plus retry = 3.36.
  - Line 399: pinned cap 3.36 -> 3.53 with the decision text. Also "exceed 3.36" -> "exceed 3.53".
  - Line 401: "zero margin" text rewritten; the retry is admitted iff S measured <= 0.87.
  - Lines 403, 409, 489: 3.36 -> 3.53 (the lines 403/409 sentences, and the line 489 pin mention).
  - Remaining "3.36" mentions in the README are deliberate history or the S + retry sum.
- infra/terraform/modules/emr/variables.tf:60: G6 comment "USD 2.58" -> "USD 2.59 (2.58375 rounded up)". Checked: 0.795 x 3.25 = 2.58375.
- infra/terraform/tests/phase15_emr_primary.tftest.hcl
  - Line 270: "= 2.58 <= 3" -> "= 2.58375, USD 2.59 rounded up, <= 3".
  - Line 274: "= 3.36 > 3" -> "= 3.36375, USD 3.37 rounded up, > 3". This is the 4th-instance G6 context, and not a cap reference.
  - Both are message text only; the assertions are untouched.
- infra/terraform/README.md:572: "2.58 USD" -> "2.59 USD (2.58375 rounded up)", and "would cost 3.36 USD" -> "3.37 USD (3.36375 rounded up)". Checked: 1.035 x 3.25 = 3.36375.
- infra/terraform/tests/phase12c.tftest.hcl:118: run `dynamodb_native_failure_and_latency_panels` renamed to `dynamodb_failure_and_latency_panels_removed_by_phase15_p9`. Assertions are untouched. The old name now appears only in historical evidence files under docs/ (not mine).
- scripts/tests/test_providers.py:177-178: pin ("3","4","3.36") -> ("3","4","3.53"), comment updated.
- scripts/tests/test_pipeline.py
  - ~563: comment cap 3.36 -> 3.53 (4 x 0.50 + 1.26 = 3.26 still under the cap, so only the count refuses).
  - ~569-575, renamed `test_g6_the_cumulative_estimate_may_not_exceed_3_53`: refused ledger [1.00, 1.28] (2.28 + 1.26 = 3.54 > 3.53); allowed ledger [1.00, 1.27] (2.27 + 1.26 = 3.53, inclusive).
  - ~577-585: third-run test renamed to `..._pass_the_3_53_cap`, message cap 3.36 -> 3.53 (ledger 1.50, 1.00: 2.50 + 1.26 = 3.76 > 3.53 still refused).
  - ~595: comment 3.36 -> 3.53.
  - ~1097: pinned cap assertion "3.36" -> "3.53".
- scripts/tests/test_phase15_pipeline_pins.py (LedgerCapTests, ~266-355)
  - Header comment updated.
  - Pin ("4","3.36","3") -> ("4","3.53","3").
  - `test_the_cap_is_four_times_...` renamed `test_the_cap_is_session_1_plus_3_33_hours_at_the_s_rate`. It asserts 2 x 84 + 185 = 353 cents (1.68 + ceil(3.33 x 0.555 = 1.84815) = 1.85).
  - `test_the_cumulative_cap_refuses_above_3_53_and_admits_exactly_3_53`. The estimate 0.85 now fits (3.37 <= 3.53), so the boundary moved: check/reserve 1.02 -> 3.54 refused with "cap 3.53 USD"; check 1.01 -> 3.53 admitted; check 0.84 admitted.
  - L test (2.52 + 1.08 = 3.60) message cap 3.36 -> 3.53, still refused.
  - Runs 3 and 4 test unchanged: cumulative_usd=3.36 is still the sum of four 0.84 reservations, and the count refuses run 5.
- scripts/tests/test_d3_emr_primary.py
  - Docstring updated; the verbatim user quote of "3.36" is kept and annotated.
  - Pin ("4","3.53","900").
  - `test_s_and_one_s_retry_fit_the_3_53_cap_and_nothing_more`: S 2.52, retry 3.36, then check 4.20 refused by count and by "cap 3.53 USD".
  - New `test_the_largest_per_run_estimate_that_fits_twice_is_0_92`: 1.68 + 2 x 0.92 = 3.52 fits.
  - `test_one_cent_more_per_run_would_not_fit` reworked: 0.93 + 0.93 gives 2.61 then 3.54 > 3.53, refused. The old 0.85 + 0.84 = 3.37 would now be admitted.
  - 90-minute comment 3.64 > 3.53. Over-cap test: "exceeds the cap 3.53 USD" (total 4.19). `--record-actual` test: `cap_usd=3.53`.
  - NEW hand-derived ledger tests, `retry_after_s_measured` helper plus two tests.
    - Session 1 1.68, S reserved 0.84, S actual recorded on a WAITING cluster created 16:00Z with as_of = creation + 5640 s (17:34Z): 5640 x 0.555/3600 = 0.8695 -> 0.87; tail 900 s -> 0.14. Recorded 1.68 + 0.87 + 0.14 = 2.69; the retry 0.84 gives 3.53 <= 3.53, admitted (check rc 0, `cumulative_usd=2.69`; reserve rc 0; cumulative ("4","3.53")).
    - Same with 5700 s: 5700 x 0.555/3600 = 0.87875 -> 0.88; recorded 2.70; 2.70 + 0.84 = 3.54 > 3.53, refused with "cumulative estimate 3.54 USD (recorded 2.70 + this run 0.84) would exceed the cap 3.53 USD". A refused reservation writes nothing (cumulative stays ("3","2.70")).

EVERY NUMBER CHANGED (old -> new)
- `EMR_CUMULATIVE_CAP_USD` 3.36 -> 3.53 (release.conf, the run-bounded-pipeline.sh help, scripts/README.md 399/403/409/489, and all scripts tests above).
- release.conf PRESPEND comment 22.97 -> 22.98 and 2.03 -> 2.02.
- G6 text: 2.58 -> 2.59 (modules/emr/variables.tf:60, phase15_emr_primary.tftest.hcl:270, infra/terraform/README.md:572). 3.36 -> 3.37 (README:572 and phase15_emr_primary.tftest.hcl:274).
- Unchanged: `EMR_MAX_LIVE_RUNS` 4, `EMR_MAX_RUN_USD` 3, `PIPELINE_MAX_COPYOUT_BYTES` 8589934592 (8 GiB, comment only).
- No 12-digit number was written (scanned the diff of scripts and infra).

COMMANDS RUN and OBSERVED RESULTS
- `bash -n scripts/run-bounded-pipeline.sh` -> exit 0 (printed BASHN_OK).
- `cd infra/terraform && terraform init -backend=false -input=false` -> success. Providers were already cached; it only registered the local modules; no state touched.
- `terraform fmt -check -recursive` in infra/terraform -> exit 3. The only file listed is `environments/course.local.tfvars`, a git-ignored local file. I did not read it and did not change it; it is not mine to touch.
- `git ls-files -z '*.tf' '*.tfvars' '*.tftest.hcl' | xargs -0 terraform fmt -check` (tracked files) -> exit 0, no output. The deployer is untouched, so no separate deployer run.
- `terraform test` in infra/terraform -> "Success! 333 passed, 0 failed." (rc 0).
- `cd scripts && python3 -m unittest discover tests` (run to a file, 1820 s under heavy machine load) -> "Ran 1199 tests in 1820.375s", "OK", rc 0.
- Targeted before the full run: `python3 -m unittest test_d3_emr_primary.LedgerAt75MinutesTests ... .RecordActualTests ... .PinTests test_phase15_pipeline_pins.LedgerCapTests test_providers` -> Ran 48 tests, OK.
- tests/** assertions on 3.36: none fail. tests/scripts/test_record_actual_15.py (test-engineer) already asserts 3.53 and the 0.87/0.88 boundary. tests/infra/test_emr_module_13c.py:54 has a comment with 3.36375 only. I did not run the tests/** suite.

ASSUMPTIONS
- The cap arithmetic is from your task: 1.68 + 3.33 h x 0.555 = 1.85, so 3.53. The 0.14 tail is from `ledger_totals` and the existing 900 s tail test.
- The line 274 "3.36" in phase15_emr_primary.tftest.hcl is not a cap reference (4th instance 1.035 x 3.25 = 3.36375). I changed it to 3.37 for G6-context consistency with the README. Revert if you want it untouched.

RISKS
- The `--record-actual` boundary is inclusive and has no margin: the retry is admitted iff S measured <= 0.87 (0.0 USD spare at exactly 0.87).
- The ~30-minute `unittest discover` runtime under parallel load is a gate-time concern only.
- Existing reviewed pins/records elsewhere (docs/**, experiments/**, tests/**) that cite 3.36 are owned by other agents.

MANUAL ACTION REQUIRED: none for me. The orchestrator should confirm the docs/** records and experiments/** text reflect 3.53 (parallel owners).

BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none

NEXT GATE: independent code-reviewer re-review of the repair diff (scripts/**, infra/terraform/**); the sbt gate is not needed here (no Scala input changed). Then human approval before any live use.


## Elasticity bundle P42 (load generator semantic route and manifest), agent report, verbatim

#### Agent report (2026-11-16T21:55:10.430Z, agent a105bb6)

STATUS: COMPLETE for P42 within load-tests/** and experiments/**. All suites I ran are OK. Reviewer and coordinator gates (code-reviewer, check.sh, sbt) are NOT run by me. Nothing was sent anywhere: offline only, loopback fake servers, fake key.

OWNER: experiment-engineer
WORK ORDER: P42, load generator `semantic` route and manifest (docs/runbooks/session-2-plan.md rows P42, P35, section 6.3a). Also read the P40 route contract in PublicSemanticRoute.scala and ApiApplication.scala.

FILES CREATED
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/manifests/15b-ecs-scaling-semantic.json (hand-authored: the renderer covers 15A only and no sha pin covers 15b manifests)
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/inputs/15b/semantic-questions.txt (150 phrases, sha256 bde5f63b49e46c321dbbf958094646cf644fcef15516b6ee0e67822ccb9978af)
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/inputs/15b/semantic-questions.provenance.json
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/scripts/derive_semantic_questions.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/load-tests/tests/test_loadgen_semantic.py (20 tests)
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/tests/test_semantic_manifest.py (16 tests)

FILES MODIFIED
- /Users/danny/Documents/UIC/CS441/ScholarChain/load-tests/loadgen.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/load-tests/config/load-profile.v1.json (new `semantic` route, weight 40)
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/scripts/check_manifests.py (new `check_semantic`, called at the end of `check_15b_16b`)
- /Users/danny/Documents/UIC/CS441/ScholarChain/load-tests/README.md
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/README.md
- Not mine: `experiments/README.md` and `experiments/tests/test_experiments.py` already had uncommitted edits at the start (EMR cap 3.53). I did not touch `test_experiments.py`. I added to `experiments/README.md` on top of those edits.

WHAT WAS BUILT
- Route: a manifest with a `semantic` block enables `POST /v1/semantic/retrieve`. Header is `Authorization: Bearer <key>` (the P40 contract uses Bearer, not a custom header) plus `Content-Type: application/json`. Body is exactly `{"question","topK"}` (topK 10 in the manifest, max 20). The key is read from the env var named by `--api-key-env` and is never printed or stored (tests check output and every raw file). Raw rows keep `question_index`, never the question text. Without the block the route is neither used nor listed as dropped, so ordinary runs are unchanged.
- Weights: semantic 40 against healthz 2, readyz 1, metrics 1 (90.9% with no ID files, 74.1% with both).
- Caps (constants in loadgen.py, not raisable by flags): 600 / 3,000 / 15,000 / 30,000, and a phase named `hold...` at level 50 capped at 150,000. Total 198,600. Warm-up is at most 200. `validate-manifest`, `plan` and `run` refuse a phase above its cap, a missing max_requests, a level with no cap, a duplicate cap slot, a hold below level 50 and a total above 198,600. Lowering a cap is allowed. `check_manifests.py` additionally requires the committed manifest to carry exactly the five values.
- Warm-up: its own phase (`type: warmup`, exactly one, first, level 1, max_requests from 150 to 200). One worker sends each question once in file order, with no retry. It never mixes into the level-1 figures. The manifest uses max_requests 200 and duration 600 s (an upper bound; it ends after one pass).
- Questions file: `--questions-file` must match the manifest's pinned sha256 and count, 100-200 lines, distinct case-insensitively, each ≤1000 characters. Otherwise it is refused before sending. `--llm` is refused with a semantic manifest.
- 429 separation: counted per phase and per route as `rate_limited_429` in summary.json, summary.csv, timeline.csv (columns appended at the end), the run record (`totals` and per phase) and a console line `RATE-LIMITED-429: phase=… level=… count=… of N requests`. They count toward the phase cap, never toward the abort rules, and are excluded from latency, `throughput_rps`, `success_rps` and the error rates. Added figures: `served_requests`, `successful_requests`, `success_rps` (2xx over the phase window), `active_seconds`, `success_rps_active`, `peak_success_rps_1s`.
- Behaviour change to shared code: `throughput_rps`, p50/p95/p99 and `client_error_rate` now exclude 429 rows, and `client_error_rate` no longer counts 429. This only matters when a 429 occurs; all 71 existing loadgen tests pass unchanged.
- Extra flag `--observe-seconds N`: can only lower manifest observe windows, for local rehearsals; recorded in the run record.
- Questions provenance: derived from the Phase 6 DBLP slice (dblp-2026-10-03, 10,577 inproceedings, CC0). The source sha256 equals the one in datasets/phase6/dblp-slice-manifest.v1.json (c25a1e1a…); the script verifies it before use. It reads the git-ignored `target/phase6-inputs/6fg-dblp/dblp.xml`. The rule is 2- and 3-word title windows, document frequency ≥5, fragments and plural duplicates skipped. Per-phrase title counts are in the provenance file. A test regenerates both files byte for byte.

COMMANDS RUN (all from /Users/danny/Documents/UIC/CS441/ScholarChain)
1. `python3 -I -m unittest discover -s load-tests/tests` gave `Ran 91 tests in 67.884s` and `OK`. That is the 71 existing tests plus my 20.
2. `python3 -I -m unittest discover -s load-tests/tests -p "test_loadgen_semantic.py"` with `-W error::ResourceWarning` gave `Ran 20 tests in 18.061s` and `OK`.
3. `python3 -I -m unittest discover -s experiments/tests` gave `Ran 100 tests in 3.413s` and `OK`. That includes my `test_semantic_manifest.py`: `Ran 16 tests in 0.226s`, `OK` (run alone).
4. `python3 -I experiments/scripts/check_manifests.py` ended with `CHECK-OK: 15b-ecs-scaling-semantic.json: per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000 = 198600 requests, warm-up 200 <= 200 at level 1, quiet window 30 min, 150 fixed questions (sha256 pinned, provenance matches)` and `RESULT: OK (placeholders allowed; run with --final before the commit freeze)`.
5. `python3 -I experiments/scripts/check_manifests.py --final` ended with `RESULT: OK (final: no placeholders)`.
6. `python3 -I load-tests/loadgen.py validate-manifest` returned `RESULT: MANIFEST-OK` for both `15b-ecs-scaling-semantic.json` and `15b-ecs-scaling.json`.
7. `python3 -I load-tests/loadgen.py plan --manifest experiments/manifests/15b-ecs-scaling-semantic.json --questions-file experiments/inputs/15b/semantic-questions.txt` gave `RESULT: PLAN-OK (nothing sent)`, 7 phases, 3570 s total, `ramp_cap_total=198600 warmup_max=200`.
8. Not in my scope, run only to detect breakage from the profile edit: `python3 -I -m unittest discover -s tests/scripts -p "test_cap_pins_14b.py"` gave `Ran 15 tests`, `OK`. `-p "test_llm_budget_14b.py"` gave `Ran 21 tests`, `OK`. (My first attempt with file paths errored on my invocation, not on the code.)
9. Not run, as instructed: check.sh and sbt.

TEST RESULTS: as listed above. No failures remain. My coverage:
- Route: body and header, the key from env, a different `--api-key-env`, an unset key (nothing sent), a wrong key.
- Caps: each of the five caps exceeded, refused by validate, plan and run with nothing sent; shape refusals; lowering allowed; the 198,600 totals.
- Warm-up: once each in file order; not retried; its limits and placement.
- Questions file: pinned, distinct, required, and incompatible with `--llm`.
- 429s: counted per level; excluded from latency, throughput and success rate; an all-429 run still completes.
- Hand-derived `summarize` figures, and the committed manifest's totals.

VALIDATION RESULTS: the committed manifest carries levels 1/5/25/50 plus the hold. Per-phase caps are 600 / 3,000 / 15,000 / 30,000 / 150,000, sum 198,600, warm-up 200 (own phase, level 1, first), and a 1800 s (30 min) quiet window against the ≥25 min requirement. No 12-digit run in any new or changed file (grepped). No key value anywhere.

ASSUMPTIONS
- The warm-up is its own phase (the plan allows this), so the ramp sums to 198,600 and the total with warm-up is 198,800, the figure in section 6.3a.
- "Hold" is recognised by the phase name starting with `hold`.
- topK 10 is my choice (the public max is 20).
- Weight 40 is my choice; the plan gives no number.
- The quiet-window ≥25 min rule is enforced by check_manifests.py only, not by loadgen, so rehearsals can shorten it.
- `success_rps` uses the whole phase window as denominator, like the existing throughput. For phases that hit their cap early use `success_rps_active` and `peak_success_rps_1s`; the choice of figure for deriving the target is yours.

RISKS
- `/readyz` stays in the mix (weight 1 of 44, about 4,500 calls over 198,600 requests). It fans out to graph-service and semantic-service probes (Neptune, S3 Vectors `GetVectors`). These have no per-request charge, but they are not zero load; say if you want it removed from the semantic mix.
- `read_lines` silently skips lines starting with `#`; no phrase starts with one.
- Some phrases are 2-word fragments of longer topics (for example "large language", "congest model"). They are real title phrases; the fragment filter is a heuristic.
- Warm-up on a throttled Voyage (free-trial 3/min, plan section 6.3a) would show as 5xx. Phases are timed by the 10 s request timeout, and 20 failures in the last 40 abort the run. Confirm the paid tier first (the P26 tier check).
- Never run against the real stack; only fake servers on loopback.

MANUAL ACTION REQUIRED (none for me; for the coordinator)
- Review by code-reviewer, then the coordinator's full check.sh. I did not commit.
- P35 needs the local query-api rate limit raised: the P40 default of 50/s with burst 100 will 429 at level 50. Set `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` high (for example 100000) in the offline-synthetic container, otherwise acceptance item (6) fails.

P35 REHEARSAL COMMAND (loopback http is accepted; key in env, value never on the command line)
```
export SCHOLARCHAIN_LOAD_API_KEY=<local smoke key from the shell, never a file>
python3 -I load-tests/loadgen.py run --manifest experiments/manifests/15b-ecs-scaling-semantic.json --questions-file experiments/inputs/15b/semantic-questions.txt --run-id <rehearsal-id> --base-url http://127.0.0.1:<port> --observe-seconds 30
```
- Do not pass `--node-ids-file`, `--evidence-ids-file` or `--llm`.
- Offline plan check: same command with `plan` instead of `run`, no `--base-url`, no key.
- Output: `target/experiment-runs/15b-ecs-scaling-semantic-<run-id>/`. Per level, read `derived/summary.json` (`success_rps`, `success_rps_active`, `peak_success_rps_1s`, `rate_limited_429`, `latency_ms_2xx`) and `derived/timeline.csv` (`successful_requests` per minute, divide by task count for the per-task figure).
- Acceptance (6), zero 429s, is `rate_limited_429` equal to 0 in every phase including `warmup` (the run prints `RATE-LIMITED-429:` per phase).
- The local run takes about 20 min of load plus the shortened quiet window.

BLOCKED-ON OWNER: none.
BLOCKED-ON EVIDENCE: none. The wall-clock run is bounded by `--observe-seconds`, not blocked.
NEXT GATE: code-reviewer (read-only), then the coordinator's check.sh. Then the P35 rehearsal by me or the coordinator with the command above (it needs P40/P41 images and the raised local rate limit). The experiment commit follows the human's explicit "yes".


## Elasticity P35 local rehearsal and review-2 repairs, agent reports, verbatim

#### Agent report (2026-11-16T22:11:56.969Z, agent acb38fb)

STATUS: DONE for the rehearsal run. All six acceptance items were observed and met. I made two deviations from the work order's wording, both stated under ASSUMPTIONS. One decision for the human is flagged in RISKS: the derived target is a local-CPU-bound figure and may not fire at level 25 live.

OWNER: experiment-engineer
WORK ORDER: P35, local elasticity rehearsal (branch phase-15, HEAD f801d28, tree dirty)

FILES CREATED (all under git-ignored target/, no tracked file touched)
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/p35-rehearsal/run-1/ holds my evidence:
  - cgroup-cpu-max.txt, cgroup-cpu-samples.txt (2 s samples), container-id.txt, container-limits.txt, container-log-raw.txt
  - load-start.txt, load-end.txt, loadgen-exit.txt, loadgen-stdout.txt
  - metrics-before.txt, metrics-after.txt, per-level-results.json
  - analyze.py, p35-run.sh.txt (copy of the driver script), results-summary.md, SHA256SUMS.txt
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/experiment-runs/15b-ecs-scaling-semantic-p35-local-1/ is the loadgen output: raw/{events.jsonl, requests.jsonl, raw.sha256, run-record.json} and derived/{summary.json, summary.csv, timeline.csv}.
- Scratch progress log: /private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/progress-p35.md. The driver script is p35-run.sh in the same directory.

FILES MODIFIED: none. `git status` shows only the pre-existing changes. `docs/agent-runs/phase-15/prompt.md` and `review.md` were already modified, not by me.

COMMANDS RUN
1. `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home sbt -batch packageServices` exited 0 and was already up to date ("Total time: 1 s"). There was no `sbt clean`. The services.jar sha256 is 701c8cfe1d1d474de0434c71f1b23085cd8094c40b3362f6d040b2bb28ac0e7e. The jar contains the P40 classes.
2. `open -a Docker` (the daemon was down).
3. `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND=100000 SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST=100000 scripts/smoke-local.sh` ended with `RESULT: PASS`. All 6 checks plus the 2 semantic checks passed (route 200 with exactly {hits, model}, 401 without key, cache hits 0 to 1). Output was shown on stdout only, not saved.
4. `docker build -q -t scholarchain-local-p35/query-api:p35 .` built a local-only image from the root Dockerfile (never pushed). Its id was 882486c79758be33f80fa524c51aab23f95afbe8196cc0f07fe5237e6ddc6957.
5. The driver script (copy in p35-run.sh.txt) did the following:
   - Generated a throwaway API key and internal token in shell env vars. They were never written to a file, put on a command line or printed. The container received only their sha256, as a value-less `-e NAME` pass-through.
   - Ran `docker run -d --name scholarchain-p35-query-api --cpus 0.25 --memory 1g -p 127.0.0.1:18435:8080` with SCHOLARCHAIN_SERVICE_MODE=offline-synthetic, the rate limit at 100000 per second and burst 100000.
   - Sampled the cgroup `cpu.stat` inside the container every 2 s.
   - Scraped `/metrics` before and after the load.
   - Ran `python3 -I load-tests/loadgen.py run --manifest experiments/manifests/15b-ecs-scaling-semantic.json --questions-file experiments/inputs/15b/semantic-questions.txt --run-id p35-local-1 --base-url http://127.0.0.1:18435 --observe-seconds 30`.
6. Teardown: the container was removed with `docker rm -f` and the local image with `docker rmi`. `docker ps -a` is empty. Docker Desktop is still running because I started it. Quit it if you do not want it.

TEST RESULTS: the rehearsal is not a unit test. loadgen printed `RESULT: COMPLETED run=p35-local-1 requests=198750 llm_answers=0 reason=-`. No tests were run.

VALIDATION RESULTS (acceptance items, observed)

1. Outcome. `run-end` outcome is `completed`. The 198,750 requests are 150 warm-up plus 198,600 ramp. All 198,750 returned 200 (0 errors, error_rate 0 in every phase). The cap sums match the manifest (600 / 3,000 / 15,000 / 30,000 / 150,000).

2. Served rate per level, one task, 429s excluded (there were none):

| Phase | Level | Seconds | success_rps | Per minute (x60) | peak_success_rps_1s |
|---|---|---|---|---|---|
| warmup | 1 | 4.5 | 33.319 | 1,999 | 52 |
| baseline-1 | 1 | 6.8 | 88.08 | 5,285 | 131 |
| level-5 | 5 | 13.5 | 222.469 | 13,348 | 293 |
| level-25 | 25 | 33.3 | 450.572 | 27,034 | 668 |
| level-50 | 50 | 37.2 | 806.235 | 48,374 | 1,262 |
| hold-50 | 50 | 147.7 | 1,015.538 | 60,932 | 1,737 |

   - Derivation: the target T must satisfy T > 5,285 (level 1) and 2T <= 27,034 (level 25, the smallest of the levels that must reach 2x). That gives 5,285 < T <= 13,517.
   - **Proposed `query_requests_per_target_target` = 10,000.**
   - Check: level 1 is 5,285 (53% of T; even its peak second, 131/s = 7,860/min, is below T). Level 25 is 2.70x T, level 50 is 4.84x T, and the hold is 6.09x T. The range is within the P41 limit of 1-100,000.

3. Embed calls. `/metrics` after the run, with a before-scrape of all zeros:
   - `embedding_cache_misses_total 150`, `embedding_cache_hits_total 180594`, `embedding_cache_evictions_total 0`, `embedding_cache_size 150`, `capacity 1024`.
   - 150 misses equal the 150 distinct pinned questions (one task).
   - Hits plus misses = 180,744, which equals the server's `api_route_requests_total{route="/v1/semantic/retrieve",status="200"}` and the 180,744 semantic rows in `raw/requests.jsonl`.
   - The other server counters match loadgen: healthz 9,159 vs 9,157, readyz 4,500, metrics 4,350 vs 4,349. The healthz and metrics differences are my own probe and scrape calls.

4. query-api CPU per level, from the in-container cgroup `usage_usec`, interpolated to phase boundaries. The limit is 0.25 vCPU (cpu.max 25000 100000):

| Phase | CPU seconds | % of the 0.25 limit | Throttled-period share |
|---|---|---|---|
| warmup | 1.12 | 99.4 | 97.9% |
| baseline-1 (level 1) | 1.70 | 100.0 | 100% |
| level-5 | 3.33 | 98.8 | 100% |
| level-25 | 8.19 | 98.4 | 100% |
| level-50 | 8.98 | 96.5 | 100% |
| hold-50 | 35.12 | 95.1 | 99.9% |

   CPU is saturated at every level, including level 1.

5. Rate limit. The measured peak served rate per task at level 50 is `peak_success_rps_1s` = 1,737 (hold-50, a level-50 phase; level-50 phase 1,262). That counts all routes, which is conservative. The semantic-only peak is 1,573 (hold) and 1,150 (level-50).
   - 2 x 1,737 = 3,474.
   - **Proposed `r_S2` = 3,500 and `b_S2` = 7,000.**
   - Check: r_S2 is within 1-100,000, b_S2 is within the 1-1,000,000 burst range, and b_S2 = 2 x r_S2.
   - With these values, the cost-cap formula `min(3,000 r_S2 + 2 b_S2, per-run cap, 300,000)` is bound by the per-run cap of 198,600 queries. So r_S2 does not change the plan cost.

6. 429s. `rate_limited_429` is 0 in every phase, including warmup: 0 of 150, 600, 3,000, 15,000, 30,000 and 150,000 requests. Server `api_rate_limited_total` is 0 before and after.

**Which loadgen figure I used**
- Target (item 2): `success_rps`, the 2xx count over the phase window.
  - Each phase ended at its request cap, so the window equals the active time.
  - `success_rps_active` differs by less than 0.3% (level 25: 451.834 vs 450.572; level 50: 808.32 vs 806.235).
  - It matches what ALB RequestCountPerTarget averages per minute, and 429s are excluded (there were none).
- Level-1 safety check: I also used `peak_success_rps_1s` for the "below target at level 1" test.
- `r_S2` (item 5): `peak_success_rps_1s`, because a token bucket limits instantaneous rate.

**Caveat: no S3 Vectors latency.** Offline-synthetic has no S3 Vectors, Voyage or network latency, and the fake route returns `hits=0` (a smaller reply than live). Served rates are therefore far above live. On the other hand, the 0.25 vCPU limit plus host loadgen contention (Docker VM 3 CPUs, 3.8 GiB) bound the local rates, so the figures are a CPU-bound upper estimate and not a live prediction. `r_S2` errs toward no throttling, as the plan says.

Evidence sha256, with each file at its path under `target/p35-rehearsal/run-1/` or `target/experiment-runs/15b-ecs-scaling-semantic-p35-local-1/`. The full list is `target/p35-rehearsal/run-1/SHA256SUMS.txt`.
- raw/requests.jsonl: a66a467221c47aa6184be19112899f4dbe25ae9eac52681b1f33226a474c5bd7
- raw/events.jsonl: df63c297489dc18d93affa39127c1b3c2875749cf6b7981bf1e41f7d62a92a56
- raw/run-record.json: 5e89febd33672179b7968d2cec9d6dc07dc1ca7fed75a208cd8b1dc14f64c62b
- derived/summary.json: c33aa8ea030a50d20ce443c7ff48582eb9c5d89f947174451e8b9add18f31eac
- derived/summary.csv: 1bffce2fe6a8b215741b56302f19541ecee0d8b70e6243321b6d5cd6285932af
- derived/timeline.csv: ce672d16ee657c3090cd4669dc139c9e0777e8cc3db3a6cdc5e8814994fda3ed
- cgroup-cpu-samples.txt: 49c87715365398ed91c6ccaeddd18c2e0e5c4c949ea351c903298d1748c8d37d
- metrics-before.txt: 8ead3f0ed091a567ba6683d1440f98108a4301c4f61b25d02d24ad9c492436e7
- metrics-after.txt: dafec2d593702333bfb1749a0d38dcaef4fd4e4d52077700ed722e32c236235c
- loadgen-stdout.txt: 5efe0adbab4ac08aca31daa2c513ee46eafdfc023af58a5db3dc6738cd0a3393
- per-level-results.json: ee78f230c2ac2a5b5288f68e2b95e3503378f7be8f12eaa0d3bca107f6895dea
- results-summary.md: d135acf5bcd6229620ba6641bd0a42960061a3d1cf07cb442cf01d3108ee5a2e
- container-log-raw.txt: d94c7ff1d1b7b0101cfbd844b379ed1dfed329082eca6290395d39697e4450ea
- analyze.py: 586d859cf02dc49e2b41be020306c8d4e6c8f5972c95520896d9e52d6c222d04

The container log has no key-shaped string and no "Bearer". Its request ids are `p35-local-1-N`.

ASSUMPTIONS
- **Docker instead of smoke-local.sh for the load run.** `scripts/smoke-local.sh` starts a plain JVM (no Docker, no CPU limit), generates its own key internally and stops the service when the smoke checks end. It cannot hold a service for loadgen or apply 0.25 vCPU. I did not edit it. I ran the script once as the smoke check, then started the same distribution via the root Dockerfile image with `docker run --cpus 0.25`. The service and its env are the same as the script's, except that mine runs in the container with a 1 GiB limit (my choice, not taken from Terraform).
- **Rate limit set to 100000 / 100000.** This is a rehearsal value only.
- **CPU per level is by interpolation.** I interpolated the 2 s cgroup samples linearly to phase start and end times. The 0.25 vCPU limit is what the cgroup enforces.
- **Short phases at the caps.** Levels 1-50 ended at their request caps after 7-148 s, so their rates are from short windows. Level 1 is also JVM-cold.

RISKS
- **Local figures may not transfer live.** The local rate is CPU-bound at 1,000+ per second per task, and live rates will be far lower. Under the plan's 200 ms assumption (section 6.3a), level 25 offers about 125/s, which is 7,500/min per task. That is below T = 10,000, so request-count scale-out may not fire at level 25 live, and level 50 (about 250/s, 15,000/min) is only 1.5x T. The required local acceptance gives 5,285 < T <= 13,517. This is a human decision: accept 10,000, or choose a lower T, for example below about 7,500 and above the live level-1 rate, as a recorded experiment parameter.
- **CPU saturation.** The 0.25 vCPU limit is saturated at all levels (95-100%) in this offline run, including level 1. The CPU policy cannot be assessed from this run, and the 60% target would be exceeded everywhere here.
- **Host contention.** Loadgen runs on the host and competes with the Docker VM (3 CPUs).
- **The request-count policy itself** cannot run locally and is covered by P41's `terraform test`.
- **Evidence is under `target/`, which is git-ignored.** Copy it under `docs/agent-runs/**` via the orchestrator if it must be kept.
- **The smoke-local.sh stdout was not saved to a file.** Its result is quoted in COMMANDS RUN.

MANUAL ACTION REQUIRED
- Decide the final `query_requests_per_target_target` (10,000 is proposed; the allowed range is 5,285 < T <= 13,517 under the acceptance rule).
- Set `query_semantic_rate_limit_per_second` = 3500 and `query_semantic_rate_limit_burst` = 7000 as user-set tfvars; I did not set them.
- Quit Docker Desktop if you do not want it running.

BLOCKED-ON OWNER: none for this run. Follow-up suggestion, not blocking: if a repeatable local rehearsal wants `scripts/smoke-local.sh` to hold the service open, set a CPU limit or run in Docker, that is infra-engineer scope (`scripts/**`).
BLOCKED-ON EVIDENCE: none.
NEXT GATE: code-reviewer review of the evidence and derivations, then the human decision on T, `r_S2` and `b_S2`, which go into the user-set tfvars (P41 variables).

#### Agent report (2026-11-16T22:12:32.288Z, agent a7290f7)

STATUS: DONE. All four tasks are edited in `docs/runbooks/session-2-plan.md`. The link and scan checks pass. Nothing was committed and nothing outside this file was written except the progress log.

OWNER: documentation-engineer

WORK ORDER: Phase 15, session-2-plan.md repairs for review 2 findings 1, 4, 5 and 6, with the user decision "Accept, add steps".

FILES CREATED: none.

FILES MODIFIED:
- `/Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md`
- Progress line appended to `/private/tmp/claude-501/-Users-danny-Documents-UIC-CS441-ScholarChain/efc32638-2d79-4248-918e-efd62da545bc/scratchpad/progress-docs2.md`

The file already carried other uncommitted hunks from earlier rounds (around lines 188, 238, 313, 1022 and 1086 of the new text). I did not touch those.

CHANGES (line numbers are in the new file):
- **Finding 1, P19 draft, item 3 (lines 330-338):** inserted a "Rounding budget" paragraph after the S retry condition. It states:
  - the cap stays 3.53;
  - every term rounds up to the cent;
  - the ≤ about 19 min budget (creation to S submission plus the wait before `--record-actual`);
  - the arithmetic 95 min = 0.87875 → 0.88, and 1.68 + 0.88 + 0.14 + 0.84 = 3.54 > 3.53;
  - the cold start of 4-5 min;
  - operator steps (a) and (b).
- **Finding 1, step 5 (line 451):** appended operator step (a). Write record 1 and submit S as soon as the cluster ID exists, and pre-write record 2 only after S is submitted.
- **Finding 1, step 5a (line 457):** added a new "Rounding budget" bullet after the retry admission condition.
  - It carries the 19 min budget and the same arithmetic.
  - It adds the check that 94 min gives 0.8695 → 0.87, which gives 3.53 and just fits.
  - It adds operator step (b): run `--record-actual` immediately after an S failure, before anything else.
- **Finding 1, step 6 (line 458):** added one sentence pointing at the rounding budget and step (b). The existing 0.87 and 94 min text is unchanged.
- **Finding 1, P25 row (line 256):** also added a one-sentence rounding-budget pointer. You did not ask for this; it is easy to drop.
- **Finding 4, P25 row (line 256):**
  - Old: "If L's manifest needs a longer runtime (at most `PIPELINE_MAX_RUNTIME_MINUTES` 180), recompute the cap…"
  - New: "L is dropped on EMR (2026-11-16), so no L manifest sets a longer runtime; if a later S manifest ever needs one (at most … 180), recompute the cap…"
- **Finding 4, P19 draft (lines 344-347):** the "if S succeeds the next run is L … If L fails" sentence is verbatim from the human's P25 decision. I checked it against `docs/agent-runs/phase-15/prompt.md` line 131. I did not rewrite it. I added a bracketed note below it marking it superseded by the 2026-11-16 decision to drop L on EMR, with the second EMR run existing only as the S retry.
- **Finding 5, step 5a (line 454):**
  - Old: "…part of the D3 infra change, which is **not yet reviewed or committed**…"
  - New: "…re-read in the working tree 2026-11-16; part of the D3 infra change, committed in `f801d28` (pipeline-bundle review 1: APPROVE; the working tree carries a later one-line change to that script)…"
  - The cited lines 18, 67 and 124 of `scripts/run-bounded-pipeline.sh` still match.
- **Finding 6, section 6.3a (line 817):** added a paragraph after "What one request queries".
  - `/readyz` stays in the P42 mix as a coordinator default, not asked.
  - The mix is 40 / 2 / 1 / 1, so weight 1 of 44, which is about 4,500 calls (198,600 / 44 = 4,513).
  - The "no per-request charge" claim in `experiments/README.md` is marked unverified.
  - The cost is bounded and small. As an illustration only, billing every probe at 2.67 per million would add about USD 0.012. This is not in 0.53 and no cap changes.
  - The human may verify the pricing or accept the default.

COMMANDS RUN: `grep`, `sed`, `Read` and `git diff -U0` on the target file and the sources below. One `python3 -I` script did the link check, the scan and the arithmetic.

TEST RESULTS: not applicable. This is a docs-only change and no code gate was run.

VALIDATION RESULTS:
- **Link check:** 20 relative links in the file, 0 broken.
- **Scan:** 12-digit numbers: none. E-mail addresses: none. Key patterns: none.
- **Arithmetic, recomputed with Decimal and round-up:**
  - 95 min x 0.555/h = 0.87875 → 0.88; 1.68 + 0.88 + 0.14 + 0.84 = 3.54.
  - 94 min → 0.87; 1.68 + 0.87 + 0.14 + 0.84 = 3.53.
  - 900 s idle tail → 0.14.
  - 3.53 - 1.68 - 0.84 - 0.14 = 0.87, which is 94.05 min at 0.555/h.
- **Config check:** `scripts/config/release.conf` has `EMR_MAX_LIVE_RUNS=4`, `EMR_CUMULATIVE_CAP_USD=3.53`, `PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=900`. `scripts/lib/budget.py` quantizes every term with `ROUND_UP` to the cent (lines 101, 140, 590, 591).
- **Cold start:** section 5.0 (line 408) says 4-5 min.
- **Not verified:** `/readyz` probe pricing. No network was available and none was attempted.

ASSUMPTIONS:
- The 19 min figure comes from review 2 and the user answer. I confirmed it arithmetically as 94 - 75.
- Step 5a's `--record-actual` measures to the UTC time of the saved describe file while the cluster is still up. That comes from the existing 5a text and `--as-of-utc`.

RISKS:
- Operator steps (a) and (b) are procedure only. Nothing enforces them, and `--record-actual` has not run against AWS.
- The P19 draft is wording for the human to copy; it is not a record.

MANUAL ACTION REQUIRED:
- The human decides whether to verify `/readyz` probe pricing or accept the default (finding 6).
- The human commits after an explicit yes.

BLOCKED-ON OWNER: none.

BLOCKED-ON EVIDENCE: none for this file.

NEXT GATE: independent review of `docs/runbooks/session-2-plan.md`, then the human's explicit yes to commit.


## Review-2 repairs and P35 runbook record, agent reports, verbatim

#### Agent report (2026-11-16T22:15:27.865Z, agent a0f7927)

STATUS: DONE (one file edited, offline, nothing committed). No BLOCKED-ON.
OWNER: documentation-engineer
WORK ORDER: Phase 15, P35 results and scaling-target decision, `docs/runbooks/session-2-plan.md` only (branch phase-15, HEAD f801d28)

FILES CREATED: none in the repo. A scratch backup and edit script are in the scratchpad, outside the repo.
FILES MODIFIED: /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md. I built on your earlier uncommitted edits. My part is 35 inserted lines and 10 changed lines. `git diff --stat` for the whole file now shows 82 insertions and 25 deletions in total.

CHANGES (line numbers are in the file after my edits; old → new)
1. Line 45 (header amendment list), new bullet: the P35 result and the decision "T = 3,000 (Recommended)", pointing to the new results paragraph, with the three values. It states that all three are set by you in the private tfvars.
2. Row P35, line 268, end of the acceptance text:
   - old: "The measured per-level rates replace the 200 ms planning assumption in section 6.3a."
   - new: "Result and decision (2026-11-16): see the P35 results paragraph below this table. The measured local per-level rates did not replace the 200 ms planning assumption in section 6.3a: you set the target from the live estimate instead (T = 3000), a recorded deviation from the local rule in item (2)."
3. Row P41(b), line 274:
   - "the value comes from P35" → "...: **3000**, your decision of 2026-11-16, see the P35 results paragraph below the prerequisites table".
   - "the P40 code defaults 50 / 100 apply" → adds "(Session 2 values from P35: **3500** and **7000**)".
4. New "P35 results and decision" block, lines 286-308, directly after the prerequisites table and before section 4a. The block holds:
   - **Run:** p35-local-1, completed, 198,750 requests (150 warm-up plus 198,600), 0 errors, 0 x 429. The server's `api_rate_limited_total` was 0.
   - **Per-level table:** served per second, per minute and peak 1 s, from `per-level-results.json` and `loadgen/derived/summary.json`.

   | Level | Served per minute | Peak 1 s |
   |---|---|---|
   | warm-up (level 1) | 1,999 | 52 |
   | baseline (level 1) | 5,285 | 131 |
   | level 5 | 13,348 | 293 |
   | level 25 | 27,034 | 668 |
   | level 50 | 48,374 | 1,262 |
   | hold at 50 | 60,932 | 1,737 |

   - **Embed misses:** 150 = the 150 distinct questions. Hits are 180,594 and hits plus misses are 180,744.
   - **CPU:** saturated at 0.25 vCPU at every level (95.1 to 100.0%). The block says the CPU policy cannot be assessed from this run.
   - **Offline-synthetic caveat:** no S3 Vectors, Voyage or network latency, so the local rates do not predict live rates.
   - **The local rule:** 5,285 < T ≤ 13,517. Under the 200 ms live estimate it would probably not scale out at level 25.
   - **The decision:** `query_requests_per_target_target` = **3000**, a recorded deviation from the local rule. Live estimates per task: level 1 about 300 and level 5 about 1,500 per minute stay below T. Level 25 (about 7,500) is about 2.5 × and level 50 (about 15,000) about 5 ×. These are estimates, not measurements. Scale-out is still capped by the Terraform maximum task count (query-api max 2).
   - **The rate limit:** `query_semantic_rate_limit_per_second` = **3500** and `query_semantic_rate_limit_burst` = **7000**. This is 2 × the 1,737/s local level-50 peak, rounded up, with burst 2 ×.
   - **What P35 did not show:** AWS policy behaviour, and whether level 1 stays below T live. Locally level 1 is 5,285/min, above 3000, only because the offline task is CPU-bound.
5. Section 5.3 step 2, lines 567-568:
   - "`query_requests_per_target_target` from P35 (P41);" → "= **3000** (P41; your P35 decision of 2026-11-16, a deviation from the local rule; set by you in the private tfvars);"
   - "`...per_second` = `r_S2` and `...burst` = 2 x `r_S2`" → "= `r_S2` = **3500** and ... = `b_S2` = 2 x `r_S2` = **7000** (set by you in the private tfvars; ...)".
6. Checklist, line 537: the target, `r_S2` and `b_S2` now carry the values, the 1,737/s local peak and the observed "0 of 198,750".
7. Section 6.3a, lines 859, 862 and 868:
   - Line 859: "to be replaced by the P35 measurement" → "the P35 local measurement did not replace it ... you set the request target from this live estimate".
   - Line 862: now says `r_S2` = 3500.
   - Line 868: now says 2 × 1,737 = 3,474, so `r_S2` = 3500 and `b_S2` = 7000, and that the local peak is far above the 250/s live planning rate.
8. Section 9.3, line 1149: the observed peak, `r_S2`, `b_S2` and the 0 of 198,750 429s are added.
9. Risk row "No scale-out", line 1059: notes that the local task was CPU-saturated, so nothing is shown about the live CPU policy, and that T = 3000 gives about 2.5 × at level 25 and 5 × at level 50.
10. Section 10 provenance, line 1173: a new bullet listing the evidence files and the prompt.md section used.

NOTES FOR THE REVIEWER
- "Wednesday private config keys": the plan has no separate list. Those keys appear in the places above: row P41(b), section 5.3 step 2 and the checklist.
- The results block sits in section 4, after the prerequisites table. The header bullet and the cross-references say "section 4", not "section 3".

COMMANDS RUN
- Read-only `cat`, `sed`, `grep` and `python3` over `docs/agent-runs/phase-15/evidence/p35/rehearsal/{results-summary.md,per-level-results.json,metrics-after.txt,loadgen-stdout.txt}`, `loadgen/derived/summary.json`, the P35 report at the end of `docs/agent-runs/phase-15/owner-report.md` and the last section of `docs/agent-runs/phase-15/prompt.md`.
- A Python edit script with an exact-match assert on every replacement. All replacements applied once.
- A Python (`-I`) relative-link and pattern scan over the plan file.
- A first `sed -i` fix attempt failed (BSD sed syntax). I redid it with Python, and a follow-up `grep` found no stale "section 3" text.
- No git write, no AWS call, no Terraform or `sbt`.

TEST RESULTS: not applicable. This is a docs-only change.

VALIDATION RESULTS (observed)
- Relative-link check: 20 relative links checked, 0 broken.
- Scan for 12-digit numbers: none. E-mail scan: none. Key-pattern scan (`AKIA...`, `sk-...`): none.
- Numbers were cross-checked against `per-level-results.json`, `results-summary.md` and `metrics-after.txt`. I confirmed hits plus misses is 180,594 + 150 = 180,744, and 2 × 1,737 = 3,474, which rounds up to 3,500. The live estimates (300, 1,500, 7,500, 15,000 per minute) follow from L = 200 ms, which gives 5 requests/s per worker.
- The final scan was run before my last small "section 4" wording fix. That fix changed only section-number text, and a `grep` confirmed it applied.

ASSUMPTIONS
- The rate-limit values come from the coordinator defaults you gave, not from a new user answer.
- "98-100% of periods throttled" is taken from the throttled-period share in the evidence. It ranges from 97.9% in warm-up to 100%, so I wrote the lower bound as 98.

RISKS
- The live per-minute figures are estimates from the 200 ms assumption. The plan says so, and the new text marks them as not measured.
- The experiment-engineer's report warns that if live latency is much lower than 200 ms, level 1 could exceed T = 3000. Locally it does only because it is CPU-bound. I recorded it under "Not shown by P35".

MANUAL ACTION REQUIRED: you set the three tfvars privately (`query_requests_per_target_target` = 3000, `query_semantic_rate_limit_per_second` = 3500, `query_semantic_rate_limit_burst` = 7000). Nothing is committed. A commit needs your explicit yes.
BLOCKED-ON OWNER: none.
BLOCKED-ON EVIDENCE: none.
NEXT GATE: code-reviewer (read-only) on `docs/runbooks/session-2-plan.md`, then your commit decision.

#### Agent report (2026-11-16T22:16:09.532Z, agent aef04b8)

STATUS: DONE. Findings 2, 3 and 6 are implemented offline and all three gates pass.

OWNER: experiment-engineer (territory: load-tests/**, experiments/**)

WORK ORDER: Phase 15, branch phase-15, HEAD f801d28, code review 2 findings 2, 3 and 6.

FILES CREATED: none.

FILES MODIFIED (the working tree also carries the earlier uncommitted P42 changes in these files; only the lines below are new in this round):
- /Users/danny/Documents/UIC/CS441/ScholarChain/load-tests/loadgen.py
  - Lines 951-952, in `finish_setup`, right after `cfg["target_loopback"]` is set. When `args.observe_seconds` is not None and the target is not loopback, it raises `Refused`.
  - The run exits with rc 3 and writes `REFUSED: --observe-seconds is refused for a non-loopback target: it can shorten the 25-minute R-b quiet window, which only a local rehearsal may do; drop the flag (or point --base-url at 127.0.0.1 or localhost). Nothing was sent` to stderr.
  - The check runs before the key is read, the output directory is created, and any connection is made.
  - Help text of `--observe-seconds` (around line 1184) now says "refused unless the target is loopback, so never for R-b".
- /Users/danny/Documents/UIC/CS441/ScholarChain/load-tests/tests/test_loadgen_semantic.py
  - Lines 505-562 add four tests and the helper `run_with_flag`.
  - `test_observe_seconds_is_refused_for_a_non_loopback_target_and_nothing_is_sent`:
    - Uses three URLs: https://api.example.org, https://api.example.org:8443 and https://10.0.0.5.
    - Asserts rc 3 and the message text (it names R-b, "drop the flag" and "Nothing was sent").
    - `socket.create_connection` and `socket.getaddrinfo` are patched to fail, and the test asserts neither was called.
    - It also asserts the fake server received 0 requests, no run directory was created, and the key is absent from stderr.
  - `test_observe_seconds_is_refused_even_when_it_would_not_shorten_a_window`: the refusal also holds with `--observe-seconds 99999`.
  - `test_observe_seconds_is_still_allowed_on_127_0_0_1_and_localhost`: a full run exits 0 for both hosts and the run record shows `loopback` true and `observe_seconds_override` 0.2.
  - `test_without_the_flag_the_manifest_windows_are_unchanged`: the plan shows 1800s, and the committed manifest's observe phases are `[1800]`.
- /Users/danny/Documents/UIC/CS441/ScholarChain/experiments/README.md
  - Line 38 (finding 3a): a longer S cap is no longer "refused by the ledger". It now says runs up to 0.92 each fit the 3.53 cap with 0.17 of room, and only `check_manifests.py`'s 75-minute S pin refuses a longer S. Further EMR runs and a costlier node type are still said to be refused by the ledger.
  - Line 137 (finding 3b): "84 tests (48 + 23 + the 13 identity-bypass tests)" is now "100 tests (48 + 23 + 16 + the 13 identity-bypass tests)". It matches line 28 and the observed count.
  - Line 144 (finding 3c): "3-run ledger" is now "4-run ledger".
  - Line 226 (finding 6): "they carry no per-request charge" is replaced. It now says the S3 Vectors `GetVectors` pricing is unverified and not pinned in this repository. It says the cost is bounded and small (about 4,500 calls), and that `/readyz` stays in the semantic mix by the coordinator's recorded default.
  - I grepped `load-tests/config/load-profile.v1.json`, `load-tests/README.md` and the semantic manifest for the "no per-request charge" claim. It was not there, so those files needed no change.

COMMANDS RUN AND TEST RESULTS:
- `python3 -I -m unittest discover -s load-tests/tests`: `Ran 95 tests in 70.198s`, `OK`.
- `python3 -I -m unittest discover -s experiments/tests`: `Ran 100 tests in 3.566s`, `OK`.
- `python3 -I experiments/scripts/check_manifests.py`: `RESULT: OK (placeholders allowed; run with --final before the commit freeze)`. Every CHECK line was OK, including the semantic manifest (198600 requests, quiet window 30 min, 150 questions sha256 pinned).

VALIDATION RESULTS: the refusal is observed in the test (rc 3, no socket call, no directory). The loopback runs on 127.0.0.1 and localhost still pass. The 4,500 figure is not a new metric: it is about 1/44 of 198,600 requests (`/readyz` weight 1 against a total of 44 with no ID files), as the coordinator stated.

ASSUMPTIONS:
- The `plan` command takes no `--base-url`, so `plan --observe-seconds` is unchanged and prints the shortened window. Nothing is sent by `plan`, so the refusal applies only to `run`. The existing plan test still passes.
- The "0.92 each" figure follows from 1.68 + 2x <= 3.53, which gives x <= 0.925. Rounded down to cents it is 0.92.

RISKS:
- The `run` command refuses on any non-loopback host, including https hosts that are private rehearsal targets. That matches the instruction.

MANUAL ACTION REQUIRED: none.

BLOCKED-ON OWNER: none.

BLOCKED-ON EVIDENCE: none.

NEXT GATE: independent code review of the diff. Nothing was committed or stashed.

#### Agent report (2026-11-16T22:18:33.774Z, agent a89b35f)

STATUS: COMPLETE. Only wording changed, no assertion value changed. Both changed files pass.

OWNER: test-engineer
WORK ORDER: Phase 15 review 2, finding 4 (leftover L wording after L was dropped on EMR on 2026-11-16)

FILES CREATED: none

FILES MODIFIED (tests/** only):
1. /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts/test_cap_pins_14b.py
   - :68 docstring of test_after_session_1_exactly_two_more_runs_fit_both_caps. "(S then L, or S then one S retry)" is now "(S and its one S retry; L was dropped on EMR on 2026-11-16)".
   - :209 docstring of test_d3_ledger_leaves_a_seventeen_cent_margin_under_the_cumulative_cap. "S 0.84 + L 0.84" is now "S 0.84 + the one S retry 0.84".
2. /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts/test_pipeline_refusals.py
   - :264 test renamed from test_session_2_s_then_l_fit_after_session_1_and_a_fifth_run_does_not to test_session_2_s_and_its_retry_fit_after_session_1_and_a_fifth_run_does_not.
   - :265-272 docstring:
     - "L, or the one S retry" now says "the one S retry (L was dropped on EMR on 2026-11-16, so Session 2 is S and its retry)".
     - The boundary sentence now says "leaves the retry at 3.53" and "leaves it refused at 3.54".
     - Added one sentence: the 1.01 and 1.02 ledgers stand for a measured S overrun, not for an L run.
   - :275-279 subTest labels renamed: "L after S" to "S retry after S", "L exactly at the cap" to "S retry exactly at the cap", "L one cent over" to "S retry one cent over". The ledger values and the allowed/refused expectations are unchanged.
   - :814 test renamed from test_d3_the_75_minute_s_run_and_l_fit_under_3_53_with_a_seventeen_cent_margin to test_d3_the_75_minute_s_run_and_its_retry_fit_under_3_53_with_a_seventeen_cent_margin.
   - :815-818 docstring: "S 0.84 + L 0.84" is now "S 0.84 + the one S retry 0.84". "L is allowed" and "+ L 0.84" are now "the retry is allowed" and "retry 0.84". The 3.36, 3.53, 3.54, 0.17 and 2.69 figures are unchanged.

These files already had uncommitted edits from the repair round. The line numbers above are in the current tree.

Left as is, on purpose:
- test_pipeline_refusals.py:135 and :152 mention "L slice" and "the largest L slice must fit". This is the local 50,000-record sample slice for the 60,000 ceiling, not an EMR L run. It is correct as written.
- No test exercises an L-sized EMR run as a refusal or boundary case. The renamed boundary cases are S-retry cases, so no "kept deliberately" docstring was needed.
- docs/agent-runs/phase-15/owner-report.md:2926 and :4143 still quote the old test names. Those are historical records, and I do not own them.

COMMANDS RUN:
- grep for the old test names across the repo (excluding .git), to check that nothing else refers to them. Only owner-report.md does.
- A Python script that made the exact-match replacements, asserting that each pattern occurs once.
- `cd /Users/danny/Documents/UIC/CS441/ScholarChain/tests/scripts && python3 -m unittest -v test_cap_pins_14b test_pipeline_refusals 2>&1 | tail -15`

TEST RESULTS: `Ran 79 tests in 406.888s`, then `OK`. Only these two files were run. The run was slow (about 407 s) because the local load rehearsal was running on the machine. I piped through `tail`, so the per-test lines were not shown. The count of 79 includes the three renamed tests.

VALIDATION RESULTS: Offline only. No 12-digit numbers were added. I did not read tfvars, state, ~/.aws, .env or secrets. No commit was made.

ASSUMPTIONS: In the retry-boundary cases, the "S retry" labels fit the ledgers. The 1.01 and 1.02 entries are an overrun of the second recorded S run, which is the retry scenario.

RISKS: Anything outside tests/** that quotes the old test names will not find them. Only historical owner-report.md lines do.

MANUAL ACTION REQUIRED: none

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: Coordinator or code-reviewer confirms finding 4. The full `sbt check` runs once after APPROVE, per the user rule.


## Review-3 disclosure notes, agent report, verbatim

#### Agent report (2026-11-16T22:24:59.332Z, agent a176b1f)

STATUS: DONE (wording only; offline; no commit; nothing outside docs/runbooks/session-2-plan.md edited)
OWNER: documentation-engineer
WORK ORDER: Phase 15, review 3 disclosure notes 1-4, branch phase-15, HEAD f801d28
FILES CREATED: none
FILES MODIFIED: /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md (built on the existing uncommitted edits)

Changes, with line refs after the edit:
- Note 1, P35 results block: line 304 is unchanged, and three sub-bullets follow it at lines 305-307.
  - Line 305 (a): after scale-out to 2 tasks, level 50 still offers about 7,500 per target per minute (2.5 x T). The policy would want about 5 tasks (15,000 / 3,000). It stays pinned at the maximum of 2 through the hold, and scale-in follows only the end of the load.
  - Line 306 (b): level 25 is not expected to trigger scale-out. At 200 ms it reaches its 15,000-request cap in about 120 s (section 6.3a). That is shorter than the plan's own scale-out estimate of about 6.5 min (three one-minute datapoints plus task start; see the section 6.4 hold arithmetic). Scale-out is expected during level 50 and the hold.
  - Line 307 (c): at 400 ms, level 25 offers about 3,750 per minute per task (1.25 x T). At 100 ms or less, level 5 offers about 3,000 or more per minute and reaches T. T is unchanged at 3000.
  - The hold-arithmetic cross-reference reads section 6.4, since the paragraph at ~:957 sits under 6.4.
- Note 1, risk row (now line 1060, "No scale-out" row): the same three points are added in compact form inside the existing parenthetical.
- Note 2, line 842: "the 0.53 figure does not include it" is replaced. The new text says the 198,600 bound behind the 0.53 figure already counts the roughly 4,500 `/readyz` requests, each priced as a query call. Only the extra cost of a probe that may call `GetVectors` on more than one index is not covered, and no cap changes.
- Note 3, line 301: the CPU bullet is retitled "CPU (interpolated, approximate)". It now says the per-phase CPU figures are interpolated from 2 s cgroup samples and that the warm-up and baseline phases span only 2-4 samples.
- Note 4: the "[Superseded ...]" bracket is removed from inside the ```text block. The human's verbatim item 3 text is otherwise untouched, and the block now runs from the item 3 run rule straight into "If S fails twice...".
  - A standalone "Superseded note (outside the record wording; ...)" paragraph sits directly after the closing fence, at line 423.
  - It names the superseded run-rule sentence, refers to "item 3 of the text above" from outside the block, and cites the 2026-11-16 drop-L decision and P25.

COMMANDS RUN:
- Python text edits with exact-match asserts (each target string occurred exactly once).
- `grep -n` to confirm the new text is at the stated lines.
- A light Python scan of the file for relative links, 12-digit numbers and e-mail addresses.

TEST RESULTS: not applicable (docs only; no sbt run).

VALIDATION RESULTS (observed):
- Relative-link check on session-2-plan.md: broken links: [].
- 12-digit number scan: [].
- E-mail scan: [].
- The scan covered `](...)` markdown links only; bare path mentions were not checked.

ASSUMPTIONS:
- The 3,750 per minute figure at 400 ms is derived as 2.5 requests/s x 60 x 25 workers.
- The level 5 sensitivity at 100 ms is derived as 10 requests/s x 60 x 5 workers = 3,000 per minute (about 3,000 or more at 100 ms or less).
- Both are estimates, labelled as such in the text.

RISKS: the new figures are planning estimates, not measurements, and are labelled so. The note 4 paragraph is new text outside the human's record wording, and it is marked as not part of that wording.

MANUAL ACTION REQUIRED: independent review of the diff, then the human commits (ask before commit).
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: reviewer or human reads the five touched spots (lines 301, 305-307, 423, 842, 1060).


## P0 modify incident (2026-11-16): incident record

#### Agent report (2026-11-17T02:06:35.149Z, agent a835ecb)

STATUS: DONE (record written; offline only; nothing else edited)
OWNER: incident-responder
WORK ORDER: write docs/incidents/2026-11-16-p0-budget-modify-backup-check.md (Phase 15 P0 incident)

FILES CREATED: /Users/danny/Documents/UIC/CS441/ScholarChain/docs/incidents/2026-11-16-p0-budget-modify-backup-check.md (118 lines; sections Summary, Impact, Timeline table, Detection, Root cause, What worked, Contributing factors, Recovery and action items table, Open questions, Evidence)
FILES MODIFIED: none (docs/agent-runs/phase-15/prompt.md was already modified before I started; I did not touch it)

COMMANDS RUN: read-only grep/sed/Read on scripts/billing/budget_execution.py, scripts/billing/README.md, scripts/billing/VERIFICATION.md, scripts/billing/tests/test_budget_execution.py, docs/agent-runs/phase-14/budget-modify-gate-20261116.md, tail of docs/agent-runs/phase-15/prompt.md; then `wc -l` (118) and a grep for 12-digit numbers or e-mail patterns in the new file (no matches); `git status --short` shows only ` M docs/agent-runs/phase-15/prompt.md` and `?? docs/incidents/`.
Note: my first attempt (a Bash heredoc) was blocked by the PreToolUse hook (it matched the text "terraform apply"); I wrote the file with the Write tool instead. No effect on the repo.

TEST RESULTS: none run (documentation only; full check not run as instructed)

VALIDATION RESULTS: Code citations verified against current files:
- budget_execution.py:48-49 INITIAL_STATE_SHA256 (271fe888...3f67) and INITIAL_STATE_BYTES 40818
- :132-138 file_meta (mode 600, owner), :207-229 opaque_copy
- :283-285 modify_apply_argv (-state=)
- :888-908 preserve(), writes {"artifacts", "incident_required": True}
- :1093-1096 pre-apply copy and PRE_BACKUP_NOT_INITIAL
- :1099 exit-code check
- :1100-1103 post-apply file-set check
- :1104-1107 file_meta on .backup, then TERRAFORM_BACKUP_NOT_INITIAL hash check
- :1108-1110 post-apply copy and STATE_UNCHANGED_AFTER_APPLY
- :1111-1117 except branch, preserve(), `raise Blocked("MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED") from None`
- test_budget_execution.py:45 fake Terraform writes the backup with state.read_bytes() (byte copy), with a bad_tf_backup scenario using unrelated bytes
- README.md:110 says Terraform's .backup must equal the pre-apply state; VERIFICATION.md:102 shows verify-modified needs modify_receipt_sha256 and state_backup_sha256.
The coordinator's root-cause line numbers (about 1099-1117, line 48) are confirmed. The check is at :1107.

ASSUMPTIONS: Times and the "sanitized Terraform lines" are as given by the coordinator and are labelled "operator" in the record. Commit timestamps and hashes in the Timeline were taken from your brief (and the git log lines in the session context for the commit hashes); I did not run git log for timestamps.

RISKS / NOT VERIFIED AGAINST THE CODE (stated explicitly in the record):
1. The exact inner failure code (TERRAFORM_BACKUP_NOT_INITIAL) is an inference, not observed. The code masks it with `from None`. Other causes are ruled out by the chain in the record, except a transient copy race or hash mismatch on the state at :1108. That one is not excluded by observation alone, but it is argued unlikely because preserve() copied the same state without error.
2. That Terraform re-serializes the backup (rather than some other reason for the differing hash) is a hypothesis; state contents were not read.
3. All hashes, sizes, file lists, console values, timestamps and the gate-kit history are operator or coordinator reports. I did not and could not verify them (the private directories were not read).
4. Step 5 of the chain relies on the claim that the post-apply file-set scan at :1103 passes because recovery-000/001 are the only preserved files. preserve() uses a similar but not identical file filter (it also lists config/ paths and lock.info candidates), which is consistent with the report but is not proven.
5. The recovery items (infra-engineer fix, linkage verifier, reviewer, new gate) come from your plan; I recorded them as Open and did not assess their feasibility. Open question 3 (what hash binding replaces state_backup_sha256 in a linkage verifier) is left for the infra-engineer.

MANUAL ACTION REQUIRED: Human reviews the record; commit needs the user's explicit yes (nothing committed). Human gate (new window, new MFA session) needed for the later read-only verification run.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none for the record. Confirming the .backup re-serialization would need approved opaque-artifact inspection (not done by policy).
NEXT GATE: infra-engineer fix and tests, code-reviewer review, coordinator full check and user-approved commit, then the human's new gate for one read-only verify-modified-style run. No further apply.


## P0 modify incident (2026-11-16): wrapper fix, incident-linkage verification, kit

#### Agent report (2026-11-17T02:19:29.263Z, agent a898416)

STATUS: COMPLETE for all six work items, offline only; no AWS, Terraform, Anthropic or Voyage call. All targeted gates below were observed passing. Nothing is committed; no git stash was used.

OWNER: infra-engineer
WORK ORDER: modify-20261116-01 repair. Fix modify(), record the failure cause, add read-only incident-linkage verification, tests, kit, docs.

ROOT CAUSE (confirmed, no other failing check found)
- Failing check was `require(hash_file(tf_backup) == INITIAL_STATE_SHA256, "TERRAFORM_BACKUP_NOT_INITIAL")` in modify().
- Every other check before the post-apply copy is implied to have passed. preserve() copied the `.backup` through opaque_copy, which runs file_meta (type, mode, owner). The preservation receipt lists exactly the two artifacts, so the state-file set check passed. Exit was 0 (`Apply complete!`, no termination record).
- The preserved `.backup` hash c9460a… differs from 271fe888…, and no post-apply backup was written. That leaves only this check.
- I could not inspect the real folders.

FILES CREATED
- none (no new files; the kit and tests were edited in place).

FILES MODIFIED (line counts from `git diff --stat`, +ins/-del; the kit files are untracked, so I give total lines)
- scripts/billing/budget_execution.py: +44/-10
- scripts/billing/budget_verification.py: +109/-… (net +109 over the file)
- scripts/billing/tests/test_budget_execution.py: +90/-… (net +90)
- scripts/billing/tests/test_budget_verification.py: +373
- scripts/billing/README.md: 12 lines changed
- scripts/billing/VERIFICATION.md: +20
- target/phase15/p0/p0_gate.py (now 656 lines; was 568)
- target/phase15/p0/tests/test_p0_kit.py (now 616 lines; was 438)
- target/phase15/p0/p0-steps.md (now 242 lines; was 185)
- scripts/billing/reviewed-pins.json: NOT touched.
- `docs/incidents/` shows as untracked in git status; it is not mine.

DESIGN DECISIONS
1. modify() fix (budget_execution.py)
   - Byte-equality on Terraform's `.backup` is dropped.
   - Kept: the state-file-set check (state, or state plus `.backup`) and `file_meta` (regular, 0600, uid) on the `.backup`.
   - Small hardening: a dangling or symlinked `.backup` is now also caught through `is_symlink()`.
   - The wrapper's own pre-apply copy, still verified equal to INITIAL, stays authoritative.
   - Observed metadata `{"sha256","bytes","observed_only": true}` goes into the modify-apply receipt as `result.terraform_backup_observed` (`null` if there is no `.backup`). There is no state parsing.
2. Cause recording
   - New `failure_cause(error)` returns the Blocked code if it matches `[A-Z0-9_]{1,80}` (else "Blocked"), or the exception type name (else "Exception"). It never returns a message, path or value.
   - `preserve(backup, cause=None)` adds `"cause"` to preservation.receipt.json only when a cause is passed.
   - Both modify() and create apply() pass it; the create path was a trivial symmetric change, so I did it.
   - The public stdout codes are unchanged.
3. Incident linkage (budget_verification.py)
   - Selection is by gate field. The normal gate (no `modify_linkage`) is unchanged: 29 fields, still requires modify.receipt.json and the post-apply backup.
   - A present `modify_linkage` must equal "incident", otherwise `MODIFY_LINKAGE_UNKNOWN`.
   - The incident gate has 30 fields: the 29 minus `modify_receipt_sha256`, plus `modify_linkage` and `preservation_receipt_sha256`.
   - A gate with the incident pins but no `modify_linkage`, or with both pins, gives `VERIFICATION_GATE_SCHEMA`.
   - `ModifiedVerification.incident_linkage()` runs before the first AWS call and has no write, subprocess or Terraform call. A test pins that statically.
   - Modify gate linkage, as on the normal path: file hash, operation, option, plan, actor, account, profile, region. New: modify gate `window_start` must be before the verify `window_start` (`MODIFY_GATE_WINDOW`).
   - Incident op folder checks (`modify.started` is empty):
     - no modify-apply.receipt.json, no modify.receipt.json, no `*.termination.json`, no `modify-post-*`;
     - modify-apply.stderr exists and is empty;
     - modify-apply.stdout is read in memory only and must contain exactly one line equal to `Apply complete! Resources: 0 added, 1 changed, 0 destroyed.`. I made this required rather than optional.
   - preservation.receipt.json checks:
     - sha256 equals the gate pin;
     - keys are `artifacts` and `incident_required`, plus an optional fixed-identifier `cause`, so the real receipt (no `cause`) is accepted;
     - `incident_required` is true;
     - exactly two artifacts, in order `billing.execution.tfstate` then `billing.execution.tfstate.backup`, each `equal` and `fsync_completed` true;
     - artifact 0 hash and bytes equal the gate's `state_backup_*`.
   - Backup folder: exactly the five files pre-apply.billing.execution.tfstate, pre-apply.backup.receipt.json, preservation.receipt.json, recovery-000.opaque, recovery-001.opaque. The pre-apply receipt is bound to the gate and plan, and the pre-apply file is re-hashed to INITIAL.
   - Opaque hashes (no parsing):
     - recovery-000 equals the gate pin and the current primary state;
     - recovery-001 equals artifact 1 and the current `billing.execution.tfstate.backup`;
     - no lock file, and the only state-like files in the primary tree are the state and its `.backup`.
   - Then the same six live reads and sanitizer as the normal path, and the linkage is re-read at the end.
   - The receipt carries `stage: verify`, `option: M`, and a linkage object with `mode: "incident"`, `incident_cause_recorded` (null for the real incident), `state_unchanged_since_incident: true` and the pins.
   - DEVIATION: you asked for `"linkage": "incident"`. That key already holds an object that `verified()` and `scan()` compare, so I put `"mode": "incident"` inside it instead.
   - The scan after an incident verification works (tested).
4. Kit (p0_gate.py)
   - `verify --linkage incident` takes `--modify-operation`, `--modify-gate-name`, `--modify-gate-sha256`, `--preservation-receipt-sha256`, `--state-backup-sha256`, `--state-backup-bytes`.
   - `--modify-log` is forbidden with incident and required for normal. Mixed or missing arguments are refused before git and before any prompt (`check_linkage_args`).
   - Every incident pin is typed by the human, and the kit reads nothing from the private directories (a test checks the builder's source for read primitives).
   - The wrapper's own `ModifiedVerification.load_gate` validates the built gate.
   - The unbuffered /dev/tty reader is untouched.
   - `real_blob` in the kit tests now reads the wrapper from the working tree instead of HEAD, because HEAD lacks the incident schema until you commit. After the commit they are the same.
5. Docs
   - README: item 5 (the `.backup` rule), a "Recorded cause" paragraph, a "Live incident modify-20261116-01" paragraph, a note under step 15/16, and the line number refs (`budget_execution.py:688-694`).
   - VERIFICATION.md: new section "Incident linkage".
   - p0-steps.md: new section "Incident linkage verification (modify-20261116-01)" with steps I1 (read evidence), I2 (new window, login, STS, gate), I3 (verify), expected output and stop rules. It reuses the kit's variables, adds `OP`, `MGATE`, `VOP`, `VWIN`, and states 92a7ba42…0e6d / 40834. I also updated the stale line refs there.

COMMANDS RUN (all offline; no `scripts/check.sh`, no `sbt`)
- `cd scripts/billing && for f in tests/test_*.py; do python3 -I -B $f; done` (the check.sh way: one process per file)
- `python3 -I -B target/phase15/p0/tests/test_p0_kit.py`
- `python3 -B target/phase15/p0/tests/test_p0_kit.py`
- Before changing code: the same three billing suites, as a baseline.
- Mutation check on budget_verification.py: I disabled the stderr check and the primary-state hash check, saw 3 IncidentLinkageFeatures tests fail, then restored the file (it matches the saved original).
- `py_compile` created `scripts/billing/__pycache__`; I removed it, and `find scripts/billing -name __pycache__` is empty.

TEST RESULTS (observed)
- test_budget_execution.py: Ran 120 tests, OK (baseline 115; the old `bad_tf_backup` test was replaced by 5 tests, plus 1 create-path cause test).
- test_budget_verification.py: Ran 84 tests, OK (baseline 62; +22 `IncidentLinkageFeatures`).
- test_publication_evidence.py: Ran 39 tests, OK (unchanged).
- Kit: Ran 26 tests, OK under both `python3 -I -B` and `python3 -B` (baseline 18; +7 `IncidentGateTests`, +1 schema-mirror test).
- New execution tests:
  - the same-size/other-bytes `.backup` regression completes with both receipts, and the pre-apply backup is intact;
  - the `.backup` type/mode check gives cause `FILE_TYPE_MODE_OWNER`;
  - the cause is recorded for a non-zero Terraform exit (`APPLY_FAILED_PARTIAL_POSSIBLE`), for a non-Blocked exception (`PermissionError`, with no path leak), and for the create path.
- New verification tests:
  - happy path with six selectors, nothing mutated, no recipient leak;
  - refusals for every case you listed;
  - gate field-by-field; CLI; live-shape defects; CostTypes and filter-expression mismatches.
- NOT RUN: tests/infra/test_billing_replan_14b.py. It does not import the billing scripts; it only reads modify-public-inputs.template.json, which I did not change. It also runs Terraform on scratch trees. I did not run it, so I report it as unverified. No tests/infra or tests/scripts suite imports these scripts, so no BLOCKED-ON test-engineer.

VALIDATION RESULTS
- `py_compile` OK for budget_verification.py and budget_execution.py.
- Hygiene: the only `@` address in my diff is the reserved `.invalid` fixture. There is no 12-digit ID in the changed files, and the kit's own 12-digit hygiene test passes.

ASSUMPTIONS
- The backup folder holds exactly the five files listed, and modify-apply.stdout contains the `Apply complete!...` line exactly once. I derived both from the code and your description, not from the real files. If either is wrong the verify refuses with `INCIDENT_BACKUP_FILE_SET` or `INCIDENT_APPLY_NOT_COMPLETE` before any AWS call. Step I1 has the human check both first.
- The modify gate file is named `approval-20261116-modify.json`; the steps tell the human to substitute if not.

RISKS
- The incident gate's `wrapper_files` come from the commit, so these edits must be committed and the main checkout clean at that commit (step 9 rules). `reviewed-pins.json` needs no refresh for this change (no scripts/billing rows in `source_freeze`); any later change to a source_freeze file would give `SOURCE_DRIFT`.
- Line-number citations to budget_execution.py shifted by +14 in README and p0-steps.md; I corrected those.

MANUAL ACTION REQUIRED
- The human or coordinator commits these changes after review, with an explicit yes, and runs the kit section "Incident linkage verification" from a clean checkout at that commit.
- Never re-run `modify` for modify-20261116-01. It would refuse anyway (`STATE_NOT_INITIAL`).

BLOCKED-ON OWNER
- documentation-engineer: docs/runbooks/phase-14-live-session.md still cites `budget_execution.py:673-678` (now 688-694). It also needs an incident-linkage pointer for step 15. I did not edit it.

BLOCKED-ON EVIDENCE
- none.

NEXT GATE
- Independent code review (read-only) of the diff in scripts/billing and target/phase15/p0.
- Then human approval and commit. Then the human's own new-window gate and `verify-modified` run (kit I1 to I3), whose observed output closes step 15 for modify-20261116-01.


## P0 modify incident: review 1 repairs (incident record, runbooks)

#### Agent report (2026-11-17T02:30:39.902Z, agent a48a792)

STATUS: DONE (edits made to the owned record only; offline; no commit; no secrets or protected paths read)
OWNER: incident-responder
WORK ORDER: apply code-review finding 4 (a) and (b) from the "P0 modify incident repair ... Review 1" section of docs/agent-runs/phase-15/review.md, plus the Recovery/action items update.

FILES CREATED: none
FILES MODIFIED: /Users/danny/Documents/UIC/CS441/ScholarChain/docs/incidents/2026-11-16-p0-budget-modify-backup-check.md

CHANGED LINES (by place in the record)
1. Header (line 5): added a citation-convention sentence. Every `budget_execution.py`, `README.md`, `VERIFICATION.md` and test-file line number is the location at commit 2611cc6 (the code that ran). Working-tree locations appear as "now".
2. Impact: `VERIFICATION.md:102` and `README.md:21`/`:113` are now labelled "at 2611cc6".
3. Root cause intro: now says "at commit 2611cc6 (all line numbers in this section are at 2611cc6; 'now' marks the working-tree location after the fix)". Added "now" locations: `modify_apply_argv` :283-285 now :297-299; `preserve` :888-908 now :902-925; modify try block now :1115-1140; `opaque_copy` :207-229 now :221-247; `file_meta` :132-138 now :146-152; `:48-49` unchanged. The `:908` receipt note is now past tense ("wrote only").
4. Inference step 5 (finding 4b): the `:1108` caveat is replaced. The new text says `:1108` is moot because `:1107` fails deterministically once reached. A new paragraph says that at 2611cc6 `found = sorted(...)` (:1100) was compared with `sorted([state, tf_backup])` (:1103), so file order is irrelevant. The 490 B preservation receipt lists only `recovery-000` (state) and `recovery-001` (`.backup`), and `preserve()` scans the same file classes. `UNEXPECTED_POST_APPLY_STATE` is therefore ruled out, and `TERRAFORM_BACKUP_NOT_INITIAL` is the only cause consistent with the evidence. It is still inferred because the code masked the inner code (`from None`, :1117).
5. Why the tests missed it: test citation `:45` labelled "at 2611cc6".
6. Contributing factors: `README.md:110` labelled "at 2611cc6". The "collapses all inner codes" bullet is now past tense and notes the fix.
7. Recovery table:
   - Backup-check fix: Done and reviewed (review 1 APPROVE, should-fix items being repaired), working tree and not yet committed.
   - Inner cause in the receipt: Done and reviewed. `preserve(backup, cause)` records it via `failure_cause` (now :88-99, :902-925).
   - Incident-linkage variant of `verify-modified`: Done and reviewed.
   - Re-serialized-backup test: Done and reviewed. The scenario is `reserialized_tf_backup`, at test file :46-47 and around :1627 in the working tree.
   - Review: "Review 1 done: APPROVE with should-fix items".
   - New row: "Offline evidence check ... extended kit step I1, before the freeze commit | human architect | Pending".
   - Human gate row: now reads "one read-only incident-linkage verification run (planned Tuesday 2026-11-17); no further apply", Pending.
   - Kit update, `sbt check` and commit rows: still Open.
8. Evidence section: the "Code and documents cited" bullet and the pinned-state bullet are labelled "at 2611cc6" (the latter "unchanged now").

CITATIONS VERIFIED (all by `git show 2611cc6:<path>` with `sed -n` or `grep -n`)
- `budget_execution.py` at 2611cc6:
  - `:48-49` are the `INITIAL_STATE_SHA256` and `INITIAL_STATE_BYTES` pins.
  - `:1093-1096` is the pre-apply `opaque_copy` plus `PRE_BACKUP_NOT_INITIAL` (the require is at :1094-1095).
  - `:1099` is the apply exit-code check.
  - `:1100` is the sorted `rglob`, and `:1103` is the file-set require.
  - `:1106` is `file_meta(tf_backup)`, and `:1107` is `TERRAFORM_BACKUP_NOT_INITIAL`.
  - `:1108-1110` is the post-apply copy, with `STATE_UNCHANGED_AFTER_APPLY` at `:1109`.
  - `:1111-1117` is the except branch, with `preserve` at :1114 and the `Blocked ... from None` raise at :1117.
  - `:132-138` is `file_meta`, `:207-229` is `opaque_copy`, and `:283-285` is `modify_apply_argv`.
  - `:888-908` is `preserve`, with the receipt write at :908, and `:1074-1127` spans `modify`.
- `budget_execution.py` in the working tree:
  - `file_meta` is at :146, `opaque_copy` at :221, `modify_apply_argv` at :297-299 and `preserve` at :902.
  - `preserve` ends at :925 (`save_json` of the receipt, with the cause).
  - `modify` starts at :1091, and the try block runs from :1115 to the raise at :1140.
  - The sorted file-set check is at :1118-1121.
  - `failure_cause` is at :88-99. `INITIAL_STATE_*` is still at :48-49.
- `tests/test_budget_execution.py:45` at 2611cc6 is the byte-copy `.backup` write (`state.read_bytes()`). The re-serialized scenario is new in the working tree.
- `README.md` at 2611cc6:
  - `:21` is the preservation-branch statement, and `:110` is the "requires Terraform's own `.backup` to equal the pre-apply state" step.
  - `:113` carries the `MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED` text, and `:156` is step 15 (`verify-modified`).
- `VERIFICATION.md:102` at 2611cc6 contains `modify_receipt_sha256`, `state_backup_sha256` and `wrapper_files`. `:104` is the human sequence.
- The README and VERIFICATION citations hold at 2611cc6. Both files are modified in the working tree, so their lines may have shifted. I did not map their current locations.

COMMANDS RUN: Read of the record; `git show 2611cc6:scripts/billing/budget_execution.py | sed -n/grep -n` (several ranges); `git show 2611cc6:scripts/billing/{README.md,VERIFICATION.md,tests/test_budget_execution.py} | sed -n`; `grep -n` and `sed -n` on the working-tree `scripts/billing/budget_execution.py`, test file and `docs/agent-runs/phase-15/review.md`; two `python3 -I` string-replace scripts that edited the record. Each replacement asserted exactly one match, and all succeeded. A final grep for 12-digit numbers or `@` found only the pre-existing `grep -c '@'` plan-check text on timeline line 27.
TEST RESULTS: none run (documentation-only edit); no pass is claimed.
VALIDATION RESULTS: the citations above were checked against the git objects. No link check or other gate was run.
ASSUMPTIONS: The "reviewed, APPROVE" statuses come from the review text in `docs/agent-runs/phase-15/review.md`. I did not re-review the fix. The "planned Tuesday 2026-11-17" date follows your instruction and the earlier timeline.
RISKS: The record says "inferred" for `TERRAFORM_BACKUP_NOT_INITIAL`; no observation of the inner code exists. The record's evidence tables are unchanged and not re-verified against private artifacts.
MANUAL ACTION REQUIRED: the human's offline evidence check (kit step I1), then the read-only incident-linkage verification (Tuesday). A commit needs the user's explicit yes.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: independent re-check of finding 4 by the code-reviewer, then I1 and the human gate.

#### Agent report (2026-11-17T02:31:06.807Z, agent a915b64)

STATUS: DONE (docs edits only; link check and citation check observed; no commits)
OWNER: documentation-engineer
WORK ORDER: Edit only docs/runbooks/session-2-plan.md and docs/runbooks/phase-14-live-session.md (P0 modify on 2026-11-16, P15 and the frozen commit moved to tonight, citation fix, step 15 pointer).

FILES CREATED: none
FILES MODIFIED:
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/phase-14-live-session.md
- /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md

CHANGED SECTIONS (line numbers in the working tree after edit):
phase-14-live-session.md
- :297 (A3 modify gate bullet): `budget_execution.py:673-678` -> `:688-694`. Checked against the working tree: the `required = {` set is at 688-693 and the `GATE_SCHEMA` require is at 694, which matches the infra-engineer's range.
- :305 (step 15): the citation `budget_verification.py:33-38` is correct (MODIFIED_GATE_FIELDS at 33-38) and unchanged. These were the only `budget_execution.py:` and `budget_verification.py:` citations in the file (grep: lines 297 and 305).
- :310 (new sub-bullet under step 15): for `modify-20261116-01` the verification is the read-only incident-linkage variant (gate field `modify_linkage: incident`; VERIFICATION.md "Incident linkage"), because the 29-field gate and `modify_receipt_sha256` do not exist for it. It links to the incident record.

session-2-plan.md
- :47-53 (top status list): new "Amended 2026-11-16" entry with five bullets covering P0, P15, P20, the frozen code commit, and the schedule update (with the unchanged 3000 / 3500 / 7000 tfvars).
  - P0 bullet: modify done 2026-11-16 (moved from Nov 17). USD 25, alerts 18/20/22, custom period 2026-10-01 to 2027-01-01, credits and refunds excluded (your console check). Wrapper stopped after the successful apply, with an incident-record link. States that the API readback of `CostTypes` is not yet recorded; it is pending the Tue 2026-11-17 incident-linkage verification, preceded by the kit step I1 pre-check.
  - P15 bullet: A1.4 done; A2 `209 pinned; 0 drifted`; A1.7 pending tonight; A12 moved to Wednesday on the final HEAD after the P0 verification records are committed (B0 requires HEAD = A12 HEAD).
  - Frozen-commit bullet says "the frozen code commit (recorded in test-report.md)" with no hash invented. P6 S runs on it tonight; records-only commits may follow; images are built after the last one.
- :254 (row P15): status appended.
- :259 (row P20): status appended; the sbt gate of the post-review full check (A1.7) runs tonight.
- :269 (row P0): item (4) now says the modify was planned for Tue and done on 2026-11-16. The old sentence "P0's modify readback will be the first recorded confirmation" is replaced by a status paragraph (console check is not an API readback; readback pending; incident link; the verification's readback will be the first recorded confirmation).
- :459 (5.1 entry condition): P0 guard note updated (applied 2026-11-16; API readback recorded by the Tue verification).
- Section 6.7 schedule, :1018-1021: new "Mon Nov 16 (tonight)" row (A1.7/P20 gate, frozen code commit, P6 S on it with the SHA256SUMS keep for the step 7b fallback, records-only commits may follow). The Tue Nov 17 row is now the P0 incident-linkage verification (read-only, about 20 min, you; I1 pre-check first; records the `CostTypes` readback). The Wed Nov 18 row is now A12 images on the final HEAD (coordinator, Docker Desktop open), credit-balance read (at least USD 6.73), approval record, go/no-go at 18:00 CST. Removed from Wed because they are done or moved to tonight: P6 S, P35 rehearsal, P15 rebuild and pins, P20.

COMMANDS RUN (all offline, read-only except the two file edits via a python replace script):
- `grep -n "budget_execution.py:\|budget_verification.py:" docs/runbooks/phase-14-live-session.md`
- `cat -n scripts/billing/budget_execution.py | sed -n 688,694p`; `sed -n 30,46p scripts/billing/budget_verification.py`
- `tail -3 target/phase15/p15/a2-pin-drift.log` -> `209 pinned; 0 drifted`
- `tail -3 target/phase15/p15/a1-check-manifests.log` -> `RESULT: OK (final: no placeholders)`
- `ls` of the incident record and VERIFICATION.md (both exist, so the new relative links resolve)
- `git diff -U0 docs/runbooks | grep "^+" | grep -E "[0-9]{12}|@[a-z]+\."` -> no output (no 12-digit IDs or e-mail addresses added)
- `git status --short docs/runbooks` -> only the two assigned files modified

TEST RESULTS: none applicable (docs only).
VALIDATION RESULTS: citation check and link-target existence check pass as observed above. No full link checker or markdown renderer was run (not available in this session), so only the new links were checked by `ls`.

ASSUMPTIONS:
- The A1.4 facts "identical render hashes on two placeholder buckets" and "manifests unchanged on re-render" come from your brief. I observed only the final lines of a1-check-manifests.log and a2-pin-drift.log, not a log of the dry run itself.
- Console-check facts come from the incident record and prompt.md.
- The Tue "about 20 min" and the Wed "18:00 go/no-go" come from your brief. The plan had no earlier 18:00 go/no-go entry.

RISKS:
- The P6 row's own results text (:269 area, "not the frozen commit ... still needs a rerun") is left as is. It stays true until tonight's frozen-commit P6 S run completes; it must be updated after that run.
- The unchanged Sun Nov 15 to Tue Nov 17 schedule row overlaps the new Mon and Tue rows. I left it to keep edits minimal.
- The old "Nov 15 billing complete" confirmation remains in the Tue row because it was not stated as done.

MANUAL ACTION REQUIRED: independent review; the human or coordinator confirms the schedule wording. The frozen commit hash must be filled in by the coordinator later (test-report.md owner); nothing was invented.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: the recorded API readback of `CostTypes` for the P0 budget does not yet exist and is stated as pending. The A1.7 full check result does not exist yet (pending tonight).
NEXT GATE: code-reviewer / human evidence review of the two files, then the coordinator's A1.7 full check and frozen-commit steps (commit only with the user's explicit yes).


## P0 modify incident: review 1 repairs (billing README, failure_cause, kit)

#### Agent report (2026-11-17T02:38:05.989Z, agent a72c92f)

STATUS: DONE. All eight findings (1, 2, 3, 5, 6, 7, 8 and the process assignment 9) are repaired offline. Nothing is committed or stashed. No AWS, no private directories, no scripts/check.sh or sbt.

OWNER: infra-engineer. WORK ORDER: P0 modify incident repair, review 1 findings. I took the coordinator's assignment of `target/phase15/p0/**` (finding 9).

FILES CREATED: none.

FILES MODIFIED
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0-steps.md (findings 1, 2, 7)
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0_gate.py (findings 3, 8)
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/tests/test_p0_kit.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/README.md (finding 5)
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/budget_execution.py (finding 6)
- /Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/tests/test_budget_execution.py (finding 6 test)

I did not touch `reviewed-pins.json`, `budget_verification.py`, the verification tests or `VERIFICATION.md`. `git status` also shows `docs/runbooks/phase-14-live-session.md` and `docs/runbooks/session-2-plan.md` as modified. I did not edit them; someone else's edits (the documentation-engineer is the likely owner).

WHAT CHANGED
- **Finding 1 (I1).** I1 is now an offline script of `ok` / `DIFF` lines that ends with `I1-result: differences=N`. It prints only hashes you already know, sizes, counts and file names. It never prints state or log contents. The groups, with the expected output of each:
  - **A.** `LC_ALL=C ls -A "$RECV"`, so dotfiles count. It must be exactly the five names: `pre-apply.backup.receipt.json`, `pre-apply.billing.execution.tfstate`, `preservation.receipt.json`, `recovery-000.opaque`, `recovery-001.opaque`.
  - **B.** Op folder `ls -A`: only `modify.started` plus `modify-pre-*`, `modify-show` and `modify-apply` `.stdout`/`.stderr` names. A receipt, termination file, `modify-post-*` file or dotfile is flagged.
  - **C.** `recovery-000` and the current state both equal 92a7ba42…0e6d / 40834. `recovery-001` equals the current `.backup` in hash and size. The pre-apply state file equals 271fe888…3f67 / 40818.
  - **D.** `modify.started` is 0 bytes. `modify-apply.stderr` is 0 bytes. The `Apply complete!` line count is 1 (`grep -c -F -x`, CR stripped, count only).
  - **E.** Line counts in the two receipts, with no content printed.
    - The pre-apply receipt gives 1/1/1/1 for gate hash, initial hash, equal and fsync.
    - The preservation receipt gives incident 1, cause 0, state 1, backup 1, equal 2, fsync 2.
    - The two byte counts, 40834 and the `.backup` size, each match once.
  - **F.** Directories are 0700, files are 0600 with one link and regular, all owned by you.
  - **G.** No symlink in the path.
  - **H.** The lock and extra-state scan, `find "$PRIMARY" \( -name '*.tfstate' -o -name '*.tfstate.*' -o -name '*.lock.info' -o -name terraform.tfstate.d \) | sed | sort`. It must print exactly `billing.execution.tfstate billing.execution.tfstate.backup`.
- **I1 mirrors the verifier.** I checked it against `incident_linkage` in `budget_verification.py`.
  - The verifier's `p.primary.rglob('*')` scan covers every subfolder (`operations/`, `config/`, `tf-data/`, toolchain), and so does the `find`.
  - The verifier's three explicit lock names all end in `.lock.info`, so the same `find` covers them.
  - The mode, uid, hardlink and symlink checks mirror `secure_dir`, `file_meta` and `regular`.
- **I1 stop rule.** If any line is not `ok` or `differences` is not 0: stop; nothing has contacted AWS; send the coordinator only the `DIFF` line(s) and the `I1-result` line. It says not to edit, move, rename or delete anything in the folders (including a `.DS_Store`), and not to go on to I2. It does not suggest deleting anything.
- **Finding 2.** `VWIN` now shows `2026-11-17T09:00`. The text says to replace both the date and the time with the real start, since the run is on 2026-11-17 or later. It warns that a wrong date is refused only after all the prompts.
- **Finding 3.**
  - `check_linkage_args` in `p0_gate.py` now holds every pure argument check. It still runs before `preflight_checkout`, git and any prompt. The checks are:
    - window-start format;
    - verify operation regex, modify gate filename, `--gate-out` filename;
    - hex64 for the modify gate, preservation and state-backup hashes;
    - bytes > 0;
    - the state-backup hash is not the INITIAL hash (the kit now mirrors `INITIAL_STATE_SHA256`; a test pins it to the wrapper's value);
    - the `modify-…` operation regex and `--packet-root` scope;
    - for `modify`: operation, record scope, plan hash format, gate filename, packet scope.
  - The existing checks in the build functions stay as a second layer.
  - The test `test_malformed_incident_pins_are_refused_and_write_nothing` now has 14 cases. It runs with no answers available and with git, `load_wrapper` and `preflight_checkout` patched to fail, so any prompt or git access fails the test. It asserts zero prompts and an empty private directory.
- **Finding 7.** I3 now uses `"$PRIMARY/operations/$VOP/verify.receipt.json"`. The AWS-contact line lists I2 and I3 and says I1 does not contact AWS. I2 now says the STS JSON contains the account ID: do not send it, do not paste it into chat or a file, clear the scrollback.
- **Finding 8.**
  - Echo stays off for the whole STS read. There is a new `hold_echo_off()` context manager, exposed as `ask_secret_default.hold_echo`, which `read_sts` uses, and it restores echo in `finally`.
  - `ask_secret_default` now turns echo off before it writes the prompt, which removes a race.
  - The unbuffered binary reader and the separate writer are kept.
  - There is a real pty test: a child process pastes the STS JSON line by line, and the test asserts the account, `UserId` and `assumed-role` never appear on the terminal and that echo is restored afterwards. I checked that the test fails when echo is left on, using a mutated copy in the scratchpad.
  - There is also a test for the `hold_echo` hook, and that plain callables still work.
- **Finding 5 (`scripts/billing/README.md`).** Done in the three places you listed:
  - the `:100` "Authoring only" sentence no longer says no apply exists; it now points to the live incident;
  - the `:107` hash is now `271fe888...3f67`, matching `INITIAL_STATE_SHA256`; it was the only `3be1f` left in the billing docs and code;
  - the `:117` sentence is now "The state must be unchanged since the incident; the incident linkage checks it."
- **Finding 6.** In both preservation sites in `budget_execution.py` (create and modify), `failure_cause(error)` is computed in its own `try` with fallback `"Exception"`, before the `try` around `preserve()`. A failing cause computation can no longer skip preservation. New test `test_a_failing_cause_computation_never_skips_the_preservation`.

COMMANDS RUN AND TEST RESULTS (final run, in this order)
- `python3 -I -B scripts/billing/tests/test_budget_execution.py`: Ran 121 tests, OK (was 120).
- `python3 -I -B scripts/billing/tests/test_budget_verification.py`: Ran 84 tests, OK.
- `python3 -I -B scripts/billing/tests/test_publication_evidence.py`: Ran 39 tests, OK.
- `python3 -I -B target/phase15/p0/tests/test_p0_kit.py`: Ran 32 tests, OK (was 26; the earlier pty test failed once on a bug in my own test child, then passed three times in a row).
  - New: two pty and hook tests, plus four I1 and steps-text tests.
  - The I1 tests run the real I1 block of `p0-steps.md` in zsh against a synthetic private tree with random bytes.
  - They prove the clean case gives `differences=0`, and that a `.DS_Store`, an extra tfstate under `tf-data/`, a changed `.backup`, a `modify-post-*` file, a mode 0644 file and a missing success line each produce their own `DIFF`.
  - They also assert that I1 prints no log content.
  - The kit's existing "no twelve-digit literal" test still passes.
- `zsh -n` syntax check of the extracted I1 block: OK.
- `__pycache__`: none under `scripts/billing` (I ran the tests with `-I -B`). I also removed a stale ignored `target/phase15/p0/__pycache__`.

ASSUMPTIONS
- Op folder labels are `modify.started` plus `<label>.stdout` / `<label>.stderr` with labels `modify-pre-…`, `modify-show` and `modify-apply`. This comes from `PrivateRunner` and the incident record. If a real label differs, B flags it and the human stops (a safe false alarm; the coordinator then adjudicates).
- Your uid is the one `id -u` prints; the F lines compare against it, so they do not hard-code 501.
- The verifier's `rglob` does not follow symlinked directories, the same as plain `find`.

RISKS
- I1 was tested only on synthetic fixtures, never on the real private files, because I may not read them. If tf-data (`TF_DATA_DIR`) holds a `terraform.tfstate`, check H, like the verifier's own scan, will fail. That is a true finding the human would otherwise hit inside the window.
- The pty test needs a Unix pty and `/dev/tty` semantics (macOS here).

MANUAL ACTION REQUIRED
- The human runs the new I1 offline before I2. This is first thing Tuesday, per the coordinator note.

BLOCKED-ON OWNER: none for this work.
- The stale line references in `docs/runbooks/phase-14-live-session.md` and the incident record's line labels (4a) remain with the documentation-engineer and incident-responder respectively.

BLOCKED-ON EVIDENCE: none.

NEXT GATE: Reviewer recheck of the kit, the I1 block and the `scripts/billing` diff. Then coordinator `sbt check`, the user-approved commit, the human's offline I1, and then the I2/I3 window.

NOT DONE
- I1 checks the receipts by line counts. It does not parse their JSON, because the pre-apply receipt contains the actor ARN, which holds the account ID and must not be printed.
- No test covers a terminal that delivers a paste in arbitrary byte-sized chunks. The pty test delivers one line at a time.


## P0 modify incident: follow-up reports (I1 timing correction, review 2 nits)

#### Agent report (2026-11-17T02:31:03.690Z, agent a48a792)

STATUS: DONE (correction applied; this supersedes the I1 wording in my earlier report)
OWNER: incident-responder
WORK ORDER: coordinator correction to /Users/danny/Documents/UIC/CS441/ScholarChain/docs/incidents/2026-11-16-p0-budget-modify-backup-check.md. I1 must not be described as running "before the freeze commit".
FILES CREATED: none
FILES MODIFIED: /Users/danny/Documents/UIC/CS441/ScholarChain/docs/incidents/2026-11-16-p0-budget-modify-backup-check.md (only the recovery-table row below)

CHANGED LINE (line 98, Recovery and action items):
- Old: "Offline evidence check of the preserved artifacts (extended kit step I1), before the freeze commit | human architect (kit by coordinator) | Pending"
- New: "Offline evidence check of the preserved artifacts (extended kit step I1), Tuesday 2026-11-17, before the read-only verification. The coordinator freezes tonight; if I1 shows a difference that needs a code change, the freeze is redone on Tuesday (source: coordinator note under review 1, `docs/agent-runs/phase-15/review.md`) | human architect (kit by coordinator) | Pending"

Other sentences checked: a case-insensitive grep for "freeze" and "I1" in the record now finds only line 98, so no other sentence places I1 before the freeze. The earlier report's closing lines ("human's offline evidence check (kit step I1), then ... verification (Tuesday)" and the item 7 summary "before the freeze commit") are replaced by the wording above.

COMMANDS RUN: `grep -n -i "I1" docs/agent-runs/phase-15/review.md` and `grep -n -i "freeze|I1"` on the record; one `python3 -I` string replace (asserted exactly one match, succeeded); a final grep of the record.
VERIFICATION OF SOURCE: line 821 of `docs/agent-runs/phase-15/review.md` is the coordinator note: the extended I1 runs first thing on Tuesday, and if it shows a difference needing a code change the freeze is redone on Tuesday. Review lines 672, 746 and 795 (which say "before the freeze commit") are the reviewer's original text, superseded by that note. I did not edit review.md.
TEST RESULTS: none run (documentation-only edit).
VALIDATION RESULTS: only the grep above.
ASSUMPTIONS: none beyond the source note.
RISKS: none new. If I1 triggers a code change, the freeze, check and commit are redone on Tuesday. That decision belongs to the coordinator and the human.
MANUAL ACTION REQUIRED: the human runs the I1 offline check on Tuesday 2026-11-17, then the read-only verification. A commit needs the user's explicit yes.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: code-reviewer re-check of finding 4, then I1 on Tuesday, then the human gate.

#### Agent report (2026-11-17T02:43:07.314Z, agent a915b64)

STATUS: DONE (follow-up nit 5 applied; the original report still holds for everything else)
OWNER: documentation-engineer
WORK ORDER: Review 2 nit 5 on /Users/danny/Documents/UIC/CS441/ScholarChain/docs/runbooks/session-2-plan.md. Only this file was edited.

CHANGED LINES (session-2-plan.md, working tree):
- (a) :269 (P0 row, Decision A text): `budget_verification.py` packet-root citation `line 431` -> `line 446`. Verified with grep: the `budget-modify-verify-[A-Za-z0-9_-]{1,56}` regex is at `scripts/billing/budget_verification.py:446`.
- (b) "API readback of `CostTypes`" replaced by "API readback of the cost scope (credits and refunds excluded)" at all four places:
  - :48 (top status bullet)
  - :269 (my new P0 status paragraph)
  - :459 (5.1 entry condition)
  - :1019 (Tue Nov 17 schedule row)
- (c) :48: the repeated wording "The recorded API readback ... is not yet recorded" is now "The API readback of the cost scope (credits and refunds excluded) is not yet recorded."

Not touched: the older P0-row sentences that describe the wrapper's pinned `COST_TYPES` refusal and the Phase 12 budget's missing `CostTypes` readback. They describe code and history, not my status text, and your list named only the four status places. I did not re-read VERIFICATION.md around line 122 for this follow-up; I used the wording you supplied (the `cost_scope_match` basis is from your message).

COMMANDS RUN: `grep -n "evidence/14b/budget-modify-verify" scripts/billing/budget_verification.py` -> :446; a python replace script with exact-match assertions (each target string occurred exactly once); `grep -n "API readback"` to confirm lines 48, 269, 459, 1019.
TEST RESULTS: none applicable.
VALIDATION RESULTS: the :446 citation was checked against the working tree. No new links or IDs were added.
ASSUMPTIONS: as in the first report.
RISKS: none new.
MANUAL ACTION REQUIRED: none.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: the API readback of the cost scope for the P0 budget is still not recorded (pending the Tue 2026-11-17 verification).
NEXT GATE: independent review of the two runbook files; the coordinator's A1.7 full check and frozen commit (commit only with the user's explicit yes).

#### Agent report (2026-11-17T02:43:13.797Z, agent a48a792)

STATUS: DONE (both nits applied; this supersedes the earlier report's try-block location and kit rows)
OWNER: incident-responder
WORK ORDER: review 2 nits for /Users/danny/Documents/UIC/CS441/ScholarChain/docs/incidents/2026-11-16-p0-budget-modify-backup-check.md.
FILES CREATED: none
FILES MODIFIED: /Users/danny/Documents/UIC/CS441/ScholarChain/docs/incidents/2026-11-16-p0-budget-modify-backup-check.md (only the lines below)

CHANGED LINES
1. Line 53 (root cause, `preserve()` bullet) and line 91 (recovery table, backup-check fix): the modify try block location "now `:1115-1140`" is now "now `:1119-1148`". Verified in the working tree: `try:` at :1119 (followed by the `modify_apply_argv` apply and the `APPLY_FAILED_PARTIAL_POSSIBLE` check), and `raise Blocked("MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED") from None` at :1148. `modify()` itself now starts at :1095.
2. Line 5 (convention sentence): "current locations are given in square brackets as 'now' where relevant" is now "current locations are given after a semicolon as 'now `:<line>`' where relevant". This matches how the record writes them.
3. Line 95: now `| Update the offline P0 kit (target/phase15/p0/, untracked) for the verify gate | infra-engineer (kit assigned by the coordinator, review 1 finding 9) | Done |`. It was "coordinator | Open".
4. Line 98: "(kit by coordinator)" is now "(kit by infra-engineer)". The rest of the row (Tuesday 2026-11-17, freeze redone on Tuesday if I1 needs a code change) is unchanged.

Other "now" locations re-checked against the working tree, all still correct: `modify_apply_argv` :297-299, `preserve` :902-925 (receipt `save_json` at :925), `opaque_copy` :221, `file_meta` :146, `failure_cause` :88-99. Neither the nit nor the record needed the sorted file-set check "now" location, so I did not add it. The working tree shows it at about :1122-1125.

COMMANDS RUN: `grep -n` and `sed -n` on the working-tree `scripts/billing/budget_execution.py`, `grep -n` on the record and on `docs/agent-runs/phase-15/review.md` (finding 9 at line 783 and the coordinator assignment at line 820, and nit 2 at line 886), and one `python3 -I` string replace. Its asserts passed: two occurrences of `1115-1140`, and exactly one match each for the other strings. A final grep of the record shows the new text.
TEST RESULTS: none run (documentation-only edit).
VALIDATION RESULTS: the line numbers were checked against the working tree. Those lines belong to the uncommitted fix and may move again if the infra-engineer edits `budget_execution.py` further.
ASSUMPTIONS: the kit update is "Done" and the kit owner is the infra-engineer, per your message and review 1 finding 9. I did not independently check the kit under `target/`.
RISKS: the "now" line numbers go stale if `budget_execution.py` changes again before the commit. Recheck them after the final repair round.
MANUAL ACTION REQUIRED: unchanged. The human runs I1 on Tuesday 2026-11-17, then the read-only verification. A commit needs the user's explicit yes.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: reviewer confirmation of review 2 nits, then coordinator `sbt check` and the user-approved commit.

#### Agent report (2026-11-17T02:43:43.161Z, agent a72c92f)

STATUS: DONE for the review 2 kit nits (3) and (4). Only `target/phase15/p0/**` was touched; `scripts/billing` was not edited in this follow-up. Nothing is committed.

This is the follow-up to my earlier report. The earlier report's file list, finding repairs and billing suite counts (121 / 84 / 39) are unchanged.

FILES MODIFIED (this follow-up)
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0-steps.md
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/p0_gate.py
- /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase15/p0/tests/test_p0_kit.py

WHAT CHANGED
- **Nit 3, new I1 checks (`p0-steps.md`).** Each prints only `ok` or `DIFF`:
  - `E pre-apply receipt bytes` must be 469.
  - `E preservation receipt bytes` must be 490.
  - `F no wrapper lock file (WRAPPER_ACTIVE)`: `$PRIMARY/.billing-wrapper-active.lock` must be absent. The test is `-e` or `-L`, which mirrors the `lexists` at `budget_verification.py:281`.
  - `F verify operation folder does not exist yet`: `$PRIMARY/operations/$VOP` must be absent, mirroring the `op.mkdir` exclusivity at `:284`.
  - The explanation bullets E and F now describe these. They also say a used `VOP` name cannot be reused: pick a new one such as `verify-usd25-incident-02`, then rerun I1.
- **Nit 4.** Removed the unused `suffix` variable in `check_linkage_args` in `p0_gate.py`. The two `suffix` lines in the build functions stay; they are used.
- **Tests (`test_p0_kit.py`).**
  - The synthetic I1 runner now defines `VOP` and pins the 469 / 490 checks to the synthetic receipt sizes. The synthetic receipts are not the real byte sizes, and the test asserts the real values are present in the block before substituting.
  - The clean case still gives `differences=0`.
  - Four new mutation cases each produce their own `DIFF` line: a lock file present, the verify op folder present, a wrong preservation receipt size, and a wrong pre-apply receipt size.

COMMANDS RUN AND TEST RESULTS
- `python3 -I -B target/phase15/p0/tests/test_p0_kit.py`: Ran 32 tests, OK. Before the last test fix, one run failed because the synthetic receipts had the wrong size; that was a test-setup issue and is fixed. The test count did not change (the new cases are subtests).
- No `__pycache__` was left under `target/phase15/p0`.

ASSUMPTIONS
- The sizes 469 and 490 are the operator-reported values that review 1 recomputed by hand from the canonical encoding. The verifier itself does not check them, so a mismatch is a stop-and-report for the coordinator, not a verifier refusal.

RISKS: none new.

MANUAL ACTION REQUIRED: the human runs the updated I1 first thing Tuesday, before I2.

BLOCKED-ON OWNER / EVIDENCE: none.

NEXT GATE: coordinator full check on the main checkout, then the user-approved commit, then the human's offline I1 and the I2/I3 window.

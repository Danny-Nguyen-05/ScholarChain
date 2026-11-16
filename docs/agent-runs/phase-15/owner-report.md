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

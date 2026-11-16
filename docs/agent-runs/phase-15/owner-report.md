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

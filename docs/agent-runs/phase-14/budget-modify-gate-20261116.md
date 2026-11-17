
# Phase 14B budget modify: human gate record (Phase 15 P0)

Date: 2026-11-16 (America/Chicago)
Author and approver: Danny (human architect)

## What I approve

- One in-place update of the live AWS budget `scholarchain-project-budget` through `scripts/billing/budget_execution.py modify`, nothing else.
- Limit: USD 200 to **USD 25**. Period unchanged: 2026-10-01 to 2027-01-01 (CUSTOM).
- Alerts: exactly three ACTUAL / GREATER_THAN / ABSOLUTE_VALUE alerts at **USD 18, 20 and 22** (my decision of 2026-11-15), same private recipient (not written here), no forecast alerts.
- Cost scope unchanged: **credits and refunds excluded**, so the budget tracks spend before credits. AWS only; Anthropic and Voyage stay in the LLM ledger and the combined C11 total.
- Tags unchanged (five tags).

## Exact bindings

- Saved plan `billing.modify.tfplan`: sha256 `01c74ac90e44614c0df0aba500fed33fe94b1c49bd989ec1a1b185c02193d529`, 12637 bytes, mode 600. I read the plan summary: `# aws_budgets_budget.project[0] will be updated in-place` and `Plan: 0 to add, 1 to change, 0 to destroy.`; `grep -c '@'` printed 0.
- Rendered private inputs `approved-public-inputs.modify.tfvars.json`: sha256 `b41d8764a7bb9b5fc1a88e259c3afb234de5c6136e55a15bf8876c104c9bfdfe`.
- Pins commit (C2): `8d0e211`. Plan built from the billing-bootstrap files of commit C `a975775a321beaa82befdbc008d70f411ff0797d`.
- Operation: `modify-20261116-01`. Gate file: `approval-20261116-modify.json` in the private billing-bootstrap directory (not in Git).
- Window: 2026-11-16 19:50 to 20:50 America/Chicago (one hour at most). My login and STS check happen inside it. If it expires, I stop; I do not extend it or reuse the operation.
- Public packet root: `docs/agent-runs/phase-14/evidence/14b/budget-modify-20261116-01`.
- Prior state: sha256 `271fe888595b6d71eedb649b7cdb87686ded0b3cbb1e2b9a19f76d7575be3f67`, 40818 bytes (Phase 12D post-create state).

## Conditions I accept

- State backup: the wrapper copies the state to `$BACKUPS/modify-20261116-01/` before and after the apply. I keep these copies, the receipts and the private logs until the reviewed teardown (retention).
- No retry, import, destroy, force-unlock or rollback. Any `BLOCKED-ON` code, `APPLIED_BUT_POST_VERIFY_FAILED:*` or `MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED` means I stop and report.
- The recovery from a bad or partial modify is to fix forward to the USD 25 shape with a new reviewed plan and a new gate.
- Alerts may briefly disappear while the provider recreates them. Spend before credits is already about USD 15.75, so an alert e-mail soon after the apply is expected.
- Afterwards, a separate read-only `verify-modified` run in a new window and with a new gate.

## Not approved here

Any other resource, amount, alert set, recipient, period or cost scope; any second modify; any change to `scripts/billing/**` code; any reuse of the Phase 12 create gate (`billing-bootstrap-exception.md`), which stays unchanged.

Signed: Danny Nguyen

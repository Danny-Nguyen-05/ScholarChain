# Incident 2026-11-16: P0 budget modify applied, wrapper stopped on its backup check

Status: contained, recovery in progress. Severity: low (no unintended cloud change, no spend impact).
Owner: incident-responder (record), infra-engineer (fix). Human decisions are in `docs/agent-runs/phase-14/budget-modify-gate-20261116.md` and the last section of `docs/agent-runs/phase-15/prompt.md`; this record does not alter them.
Line citations: every `budget_execution.py:<line>`, `README.md:<line>`, `VERIFICATION.md:<line>` and test-file citation in this record is the location at commit 2611cc6 (HEAD when the incident happened, the code that ran), checked with `git show 2611cc6:<path>`. The working-tree fix moved some of them; current locations are given after a semicolon as "now `:<line>`" where relevant. Times are America/Chicago, 2026-11-16. Facts marked "operator" were observed by the human operator and reported through the coordinator; this record did not observe them. The responder read only code and tracked documents and made no cloud call.

## Summary

Phase 15 P0 modified the AWS budget `scholarchain-project-budget` in place from USD 200 (50/80/100 percent alerts) to USD 25 with three ACTUAL absolute alerts at USD 18/20/22 (credits and refunds excluded, period 2026-10-01 to 2027-01-01). The Terraform run succeeded (`Apply complete! Resources: 0 added, 1 changed, 0 destroyed.`). The wrapper `scripts/billing/budget_execution.py modify` then stopped with `MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED` (exit 2) before writing its post-apply backup and receipts. Most likely cause (inferred, see Root cause): Terraform's own `.backup` file has the same size as the pre-apply state but a different hash, so the wrapper's byte-for-byte check `TERRAFORM_BACKUP_NOT_INITIAL` failed. The live budget matches the reviewed plan; only wrapper evidence is missing.

## Impact

- Live AWS: none unintended. The operator console check at about 20:05 matched the plan (see Evidence).
- Missing evidence: `modify-apply.receipt.json`, `modify.receipt.json`, the post-apply state backup, and the recorded API readback of cost-type filters. README step 15 (`verify-modified`) needs the receipt and the post-apply backup (`scripts/billing/VERIFICATION.md:102` at 2611cc6, fields `modify_receipt_sha256`, `state_backup_sha256`), so it cannot run as written.
- Not done: no retry, rollback, import or force-unlock. Spend impact: none (operator-reported spend USD 15.75 of the new USD 25 limit).
- Escalation scope: a post-apply incident per `scripts/billing/README.md:21` and `:113` (at 2611cc6); routed to the human, who authorized the write-up and wrapper fix (prompt.md, last section).

## Timeline

| Time | Event | Source |
|---|---|---|
| 2026-11-15 | P0 modify planned for Tue 2026-11-17 | prompt.md |
| 2026-11-16 | User moved P0 to today; coordinator confirmed no billing-file change since d5e74aa, kit tests 18 OK | prompt.md |
| 17:49:33 | Commit C a975775 | git log |
| 19:36:03 | Commit C2 8d0e211 (pins) | git log |
| 19:38:39 | Commit C3 2611cc6 (human gate record) | git log |
| before 19:50 | Plan: `exit=2`, `will be updated in-place`, `Plan: 0 to add, 1 to change, 0 to destroy.`, `grep -c '@'` = 0 | operator |
| 19:50 | Window opens (19:50-20:50), operation `modify-20261116-01` | gate record |
| 19:50:37 | `aws login` (billing role) | operator |
| 19:50:43 | STS check; account hash matched the pinned value | operator |
| after 19:50:43 | Gate kit attempt 1: `P0_GATE_REFUSED: UNEXPECTED_UnsupportedOperation`, nothing written | operator |
| after attempt 1 | Coordinator fixed the offline kit `target/phase15/p0/p0_gate.py` (unbuffered binary reader, separate writer), tested in a real pty, kit tests 18 OK | coordinator |
| after fix | Attempt 2: `P0_GATE_REFUSED: STS_DOES_NOT_MATCH_ACCOUNT_AND_ACTOR`, nothing written (pasted STS JSON did not match the typed account/ARN) | operator |
| after attempt 2 | Attempt 3: gate written, GATE_SHA 7279b775...339f | operator |
| 19:57 | `budget_execution.py modify`: change applied, then `exit=2` `MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED` | operator |
| about 20:05 | Operator read-only console check: budget matches target, Healthy | operator |
| later 2026-11-16 | User approved the incident write-up and wrapper fix "tonight" | prompt.md |

## Detection

Detected by the wrapper's own fixed public failure code and exit 2, observed by the operator and reported to the coordinator. Terraform printed `Apply complete!` in the same run, so the failure was recognized as post-apply. No `*.termination.json` exists, so there was no timeout or interrupt. The operation folder holds the pre-apply journal and reads but no `modify-apply.receipt.json` and no `modify.receipt.json`.

## Root cause

Confirmed from code, `scripts/billing/budget_execution.py` at commit 2611cc6 (all line numbers in this section are at 2611cc6; "now" marks the working-tree location after the fix):

- `:48-49` (unchanged now) pin `INITIAL_STATE_SHA256 = "271fe888...3f67"` and `INITIAL_STATE_BYTES = 40818`.
- `:1093-1096`: before the apply, `opaque_copy` of the state must equal that hash and size (`PRE_BACKUP_NOT_INITIAL`); the pre-apply receipt is then written. Both artifacts exist, so this passed.
- `:1098-1099`: apply via `modify_apply_argv` (`-state=<state>`, `:283-285`; now `:297-299`); exit code 0 required.
- `:1100-1103`: the post-apply state-file set must be exactly `[state]` or `[state, state.backup]`.
- `:1104-1107`: if `.backup` exists, `file_meta` (owner, regular file, mode 600) and then `require(hash_file(tf_backup) == INITIAL_STATE_SHA256, "TERRAFORM_BACKUP_NOT_INITIAL")`.
- `:1108-1110`: only after that does it write `post-apply.billing.execution.tfstate` and its receipt.
- `:1111-1117`: any exception runs `preserve()` (`:888-908`; now `:902-925`) and re-raises the fixed `MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED` with `from None`, so the inner code is neither printed nor stored. At 2611cc6 `preserve()` wrote only `{"artifacts": ..., "incident_required": True}` (`:908`). The whole modify try block is now `:1119-1148`.

Inference chain (the inner code is not printed, so this is inference):

1. The operator reported a clean Terraform completion (`Apply complete!`, stderr empty), so `:1099` passed.
2. `preserve()` produced exactly `recovery-000` (state) and `recovery-001` (`.backup`), no lock or errored files. The post-apply scan at `:1100-1103` uses the same file classes, so the set was `[state, state.backup]` and `:1103` passed.
3. `preserve()` copied `.backup` through `opaque_copy` (`:207-229`; now `:221-247`), which calls `file_meta` with the mode 600 and owner checks (`:132-138`; now `:146-152`). That succeeded, so a mode or owner failure at `:1106` is ruled out.
4. The state hash (92a7ba42...0e6d, 40834 B) differs from 271fe888..., so `STATE_UNCHANGED_AFTER_APPLY` (`:1109`) is ruled out.
5. The `.backup` hash is c9460a0b...1cc at 40818 B, versus the pinned 271fe888... at 40818 B, so `:1107` fails with `TERRAFORM_BACKUP_NOT_INITIAL` once it is reached. A failure of the state copy at `:1108` is moot: if `:1107` is reached it fails deterministically, so `:1108` is never reached.

The one alternative that could fire before `:1107` is `UNEXPECTED_POST_APPLY_STATE` at `:1103`, if the file-set check had been order-sensitive. Resolved: at 2611cc6 the check sorted the `rglob` result (`found = sorted(...)`, `:1100`) and compared it with `sorted([state, tf_backup])` (`:1103`), so file order is irrelevant. The preservation receipt (490 B) lists only the state and its `.backup` (`recovery-000`, `recovery-001`), and `preserve()` scans the same file classes, so the set was exactly `[state, state.backup]` and `UNEXPECTED_POST_APPLY_STATE` is ruled out. `TERRAFORM_BACKUP_NOT_INITIAL` is the only cause consistent with the evidence. It is still inferred, because the code masked the inner code (`from None`, `:1117`).

Why the bytes differ: Terraform's `.backup` has the same length but a different hash, which suggests it re-serialized the prior state instead of copying bytes. That is a hypothesis. State contents were not read (policy), so it is not investigated. The wrapper's own pre-apply copy equals 271fe888..., so the original state was intact before the change.

Why the tests missed it: the unit-test fake Terraform writes the backup with `state.read_bytes()` (`scripts/billing/tests/test_budget_execution.py:45` at 2611cc6), a byte copy; its `bad_tf_backup` scenario writes unrelated bytes. No test models a re-serialized, same-length backup.

## What worked

- Offline gates refused bad input twice (kit defect, STS mismatch) with nothing written.
- Plan inspection pinned a single in-place update with no add or destroy.
- The pre-apply byte copy and receipt matched the pinned state before the change.
- The failure branch preserved the state and `.backup` under exclusive names with a receipt marked `incident_required`, and stopped all further AWS calls; no retry or rollback occurred.
- The wrapper's fixed message did not leak state contents.
- The live result was confirmed independently by the human through a read-only console check.

## Contributing factors

- The byte-for-byte `.backup` equality at `:1107` and the README statement (`scripts/billing/README.md:110` at 2611cc6) assumed Terraform copies the prior state bytes; untested against real Terraform.
- The failure branch collapsed all inner codes into one message (`:1117` at 2611cc6), and the preservation receipt did not record the inner code (fixed in the working tree, see Recovery).
- Unit tests mock Terraform with a byte-copy backup (see above).
- The date change from 11-17 to 11-16 compressed the window. An untracked `/dev/tty` defect in the coordinator's offline gate kit and an operator paste mismatch cost two gate attempts; neither caused the incident, since the wrapper stopped after a correct change.
- The README step list ends with `verify-modified`, which depends on wrapper artifacts that the failure branch does not produce.

## Recovery and action items

| Item | Owner | Status |
|---|---|---|
| Record this incident | incident-responder | Done (this file) |
| Fix the backup check in `modify()`; keep the wrapper's own pre-apply copy as pre-state evidence and still require the state to differ from the initial hash | infra-engineer | Done and reviewed (review 1 APPROVE; should-fix items being repaired). Working tree, not yet committed. Terraform's `.backup` now needs only type, mode and owner, and its hash and size are recorded as observed metadata (modify try block now `:1119-1148`) |
| Record the inner failure code in `preservation.receipt.json` (fixed enum, no contents) | infra-engineer | Done and reviewed: `preserve(backup, cause)` records a fixed code or exception type name via `failure_cause` (now `:88-99`, `:902-925`) |
| Add a read-only incident-linkage variant of `budget_verification.py verify-modified` that binds to the preserved artifacts of `modify-20261116-01` (state unchanged since the incident) and performs the live readback, with tests and docs (README, VERIFICATION.md) | infra-engineer | Done and reviewed (review 1 APPROVE; should-fix items being repaired) |
| Add a test whose fake Terraform writes a re-serialized, same-length, different-hash `.backup` | infra-engineer | Done and reviewed (regression test in `scripts/billing/tests/test_budget_execution.py`, scenario `reserialized_tf_backup`, working tree: `:46-47` and around `:1627`) |
| Update the offline P0 kit (`target/phase15/p0/`, untracked) for the verify gate | infra-engineer (kit assigned by the coordinator, review 1 finding 9) | Done |
| Review of the fix | code-reviewer | Review 1 done: APPROVE with should-fix items (this record's citation labelling, finding 4, is addressed here); other items routed to the infra-engineer, kit writer and documentation-engineer |
| Full `sbt check`, commit (commit needs explicit user yes) | coordinator | Open |
| Offline evidence check of the preserved artifacts (extended kit step I1), Tuesday 2026-11-17, before the read-only verification. The coordinator freezes tonight; if I1 shows a difference that needs a code change, the freeze is redone on Tuesday (source: coordinator note under review 1, `docs/agent-runs/phase-15/review.md`) | human architect (kit by infra-engineer) | Pending |
| New human gate, new MFA session, new window; one read-only incident-linkage verification run (planned Tuesday 2026-11-17); no further apply | human architect | Pending |

Constraints for recovery: no `modify` rerun (the live state already equals the target and the journal forbids replay), no import, destroy, force-unlock or rollback. A change to the billing file set invalidates old gate hashes, so a new gate is required.

## Open questions

1. Is the `.backup` re-serialization confirmed? Only an approved inspection of the opaque artifacts could say; not investigated here by policy.
2. The verification gate binds the billing file set (`VERIFICATION.md:102`, field `wrapper_files`); a new gate is expected after the repair. To be confirmed by the infra-engineer.
3. Should the linkage verification accept the preserved `recovery-000.opaque` as the post-apply state evidence, and what hash binding replaces `state_backup_sha256`? Decision for the infra-engineer and reviewer.
4. Is the exact inner failure code `TERRAFORM_BACKUP_NOT_INITIAL`? Inferred only; the repaired receipt will record it for future cases.

## Evidence

Paths and hashes only; contents were not read or quoted beyond the four sanitized Terraform lines listed here.

- Plan: sha256 01c74ac9...d529, 12637 bytes; plan input sha256 b41d8764...dfe; gate sha256 7279b775...339f.
- Pinned initial state sha256 271fe888...3f67, 40818 bytes (`scripts/billing/budget_execution.py:48-49` at 2611cc6; unchanged now).
- Operation folder (private, `modify-20261116-01`): `modify.started`, `modify-pre-budget`, `modify-pre-notifications`, `modify-pre-subscribers-50`, `-80`, `-100`, `modify-pre-tags`, `modify-show`, `modify-apply.stdout` (417 bytes), `modify-apply.stderr` (0 bytes). Absent: `modify-apply.receipt.json`, `modify.receipt.json`, any `*.termination.json`.
- Backup folder `$BACKUPS/modify-20261116-01/` (private): `pre-apply.backup.receipt.json` (469 B), `pre-apply.billing.execution.tfstate` (40818 B), `preservation.receipt.json` (490 B, `incident_required: true`), `recovery-000.opaque` (source state, 40834 B, sha256 92a7ba42...0e6d), `recovery-001.opaque` (source `.backup`, 40818 B, sha256 c9460a0b...1cc). Absent: post-apply backup and receipt.
- Sanitized Terraform lines (operator): `Warning: Deprecated flag: -state`; `aws_budgets_budget.project[0]: Modifying... [id=<acct>:scholarchain-project-budget]`; `aws_budgets_budget.project[0]: Modifications complete after 3s [id=<acct>:scholarchain-project-budget]`; `Apply complete! Resources: 0 added, 1 changed, 0 destroyed.`
- Console check (operator, about 20:05, read-only): budget USD 25.00; Custom 2026-10-01 to 2027-01-01; 3 alerts Actual cost > $18.00 / $20.00 / $22.00, status OK; 1 verified recipient; amount spent $15.75 (63%); excluded filters Charge type Credit, Refund; health Healthy.
- Code and documents cited (all line numbers at commit 2611cc6, the code that ran): `scripts/billing/budget_execution.py` (`:48-49`, `:132-138`, `:207-229`, `:283-285`, `:888-908`, `:1074-1127`), `scripts/billing/tests/test_budget_execution.py:45`, `scripts/billing/README.md:21,110,113,156`, `scripts/billing/VERIFICATION.md:102,104`, `docs/agent-runs/phase-14/budget-modify-gate-20261116.md`, `docs/agent-runs/phase-15/prompt.md` (last section).
- Offline kit (untracked): `target/phase15/p0/p0_gate.py`.

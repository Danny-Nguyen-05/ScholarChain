# Phase 11 human acceptance

Recorded: 2026-10-30 (America/Chicago).

## Decision and authority

**ACCEPTED BY THE HUMAN: Phase 11 (Subphases 11A, 11B and 11C including
repair round 1, batch 1), with the carried findings and open decisions
below.**

This file transcribes the user's decision; it is not an agent approving its
own work. On 2026-10-30 the user stated that they had asked their
implementation agent to write the missing human gates and it had not, and
asked: **“Can you create them for me? … Can you do that for me?”** That
instruction expressly authorizes writing this closeout record on the user's
behalf. It does not authorize a commit; the user commits it. No earlier human
decision or review record is changed.

Acceptance covers, on `phase-11` (not yet merged to `main`):

- 11A: `d80afb755c649ecc5cda60525a1a0201aceb4c03` — data-plane adversarial tests
- 11B: `2b0aee044f243f01bbb603170d09f5c507df8bb7` — runtime adversarial tests
- 11C: `649b13b9bb40b0b6218bf7f2b71ab9d541c7aafe` — review and query binding recovery

## Accepted implementation and validation

- Adversarial, contract and end-to-end tests for the data plane (11A) and the
  runtime plane (11B), the whole-repository 11C review, and the 11C repair of
  session-binding recovery (R11C-1, R11C-2) with the services README
  correction (R11C-5).
- User-supplied independent reviews, retained verbatim in [review.md](review.md):
  **APPROVE for 11A** and **APPROVE for 11B** (no blocking findings), initial
  **REQUEST_CHANGES for 11C**, then **APPROVE for 11C repair round 1, batch 1**
  (R11C-1, R11C-2 and R11C-5 closed).
- 11A full gate: 1,231 / 1,231 passed, ExposedDefect 0. Final 11C repair full
  gate: **1,253 passed / 0 failures / 0 errors / 0 skipped** in 156 reports.
  Evidence: [full-check-summary.json](evidence/11c-r1/full-check-summary.json).
  Raw logs were kept in `/tmp` only. Tests were not rerun for this closeout.

## Accepted deferrals and open decisions

The human accepts Phase 11 with these items **OPEN/nonblocking**, owners in
[repairs.md](repairs.md). Acceptance is not repair closure.

- **R11C-3 (Medium, orphan) still needs a human ownership decision:** 24
  tracked `file:/var/**` Hadoop stats/`.crc` outputs from Phase 4 commit
  `3ccd61c` (colon paths break Windows checkouts). This record does not assign
  a writer or authorize deletion.
- R11C-4 (markup-sensitive title-year key), R11C-6 (run-ledger CAS retry may
  report its own write as a conflict; downstream impact untraced), R11C-7
  (retried creation with no row returns 404) and R11C-8 (lost reply plus a
  failed reconciliation read can strand a bound QUEUED session) remain open.
  R11C-8 is a deployment-gate concern.
- Carried unchanged: F11B-3, F11B-4, 11A N3 (with the N5 disclosed limits;
  N4 continues as R11C-4), Phase 9 NB1–NB10, Phase 10
  F7/F8/F10–F17, and earlier accepted Phase 5–8 limits.
- Synthetic results do not establish live DynamoDB behavior or durable
  dispatch after process death. Raw logs are not durable across reboot.

## Closeout boundary

This decision accepts the Phase 11 test and repair scope and the disclosed
deferrals. It does not authorize merging, deleting the R11C-3 files, live
AWS/provider calls, deployment or expenditure; those keep their separate
gates. Phase 11C was the pre-deployment test gate; Phase 12 work continues on
`phase-12`.

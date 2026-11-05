# Phase 12 human-gate handoff (prepared by the coordinator; the gate itself is the human's)

The coordinator has not written, and will not write, `human-gate.md`, `commit.txt` or any approval record. This file lists what the human needs in order to decide.

## State at handoff

- **Branch:** `phase-12`. Step C evidence was committed in `2d2d224` and pushed. The spike source is at `2d38f0f`. Step D (this folder and four pointer sections) is **uncommitted** until the human asks for a commit.
- **AWS:**
  - spike state is empty, and the after-inventory is clean;
  - 5 spike KMS keys are in PendingDeletion; the last ones are due to delete about 2026-11-11;
  - the main environment was **never applied**.
- **Retained by design** (IAM only, no cost):
  - the `scholarchain-deployer` role, its permission sets and its boundary (`infra/terraform/deployer`, applied by the human);
  - the operator inline policy `scholarchain-assume-deployer`;
  - the `scholarchain-deployer-tf` profile in the human's `~/.aws/config`.
- **Removed:** `IAMFullAccess` and `scholarchain-operator-cli-login`, removed from the operator at the end of each manual window (the human reported each removal in chat).
- **Local only (git-ignored):**
  - `target/phase12d-spike-live/`: raw logs, plans, EMR logs and the collected results, with sha256 manifests;
  - the 321 MB runtime tgz under `target/phase12d-runtime-repair-20261103/`.

## Human actions before or at the gate

1. **Review Step D** in a separate session. The reviewer prompt is in chat.
2. **Reconcile Billing.** Check the actual charges against the modeled amount of about USD 5.35 or less, once the data posts (usually within 24 h). Record the figure in the gate.
3. **Confirm the manual IAM window close times in CloudTrail.** human-approval.md records them as the human's reported times: about 11:07, about 12:35 and about 13:56 CST.
4. **Accept or reject the 12-10 decision** ([decision-12-10.md](decision-12-10.md)). Its gaps G1 to G6 go to Phase 13 and 15 work orders. G1, the S3 input/output option, and G6, the EMR budget allocation, are choices for the human.
5. **Accept the carried findings** ([carried-findings.md](carried-findings.md)). Item 17 must close before Phase 14 or any other EMR cluster in us-east-2.
6. **Decide what happens to the local artifacts:** keep or delete `target/phase12d-spike-live/`, and how to retain the runtime tgz (gap G5).
7. **Optional:** re-run `scripts/phase12d-spike/inventory.sh`, read-only, after a day to confirm that the tagging-API leftovers have cleared.
8. **Write `human-gate.md` and `commit.txt`** for Phase 12.

## Phase 12 final checklist (from `../../prompt.md` §11): coordinator view, not a verdict

| Item | State |
|---|---|
| Each subphase was reviewed by a user-launched reviewer | 12A to 12C and the earlier 12D packets are recorded in `review.md` and the `../12d-*-review-record/` folders. The spike's Step A and the live repairs are recorded in `../12d-spike-offline/review-findings.md`. **Step D is pending.** |
| The Terraform tree formats and validates; providers are pinned | Recorded in 12A to 12C. 12D: provider aws 6.44.0 from the offline mirror; fmt, validate and mock tests pass |
| No unexplained destroy or replacement of stateful resources | 12C plan. Every 12D spike plan was creates only (55 to add, 0 to change, 0 to destroy) |
| IAM is scoped; runtime and deploy permissions are separate | Reviewed; open items are in carried-findings.md |
| Buckets and databases are not public; encryption is on | Yes, for the spike (KMS, TLS on EFS, encrypted gp3, private subnet) |
| Default capacity is bounded; the cost is stated | Yes |
| No secrets in source, plan summaries or evidence | The 12D spike evidence redacts the account ID: a scan of the offline, live and closeout folders finds no 12-digit numbers, and the recipient email was never printed. **However, `../../review.md` lines 1975, 2009 and 2084 contain the unredacted account ID.** They come from earlier billing-review verdicts committed in `8903ce0`. The coordinator does not rewrite recorded review text, so the human decides whether to redact it. An account ID is an identifier, not a credential. |
| Autoscaling policies for Phase 15 | 12B/12C (not 12D) |
| The plan checksum is recorded; nothing in the main environment was applied | Yes. The live actions were the 12D spike (destroyed) and the separate deployer root (IAM, retained, applied by the human) |
| The 12-10 decision is recorded with evidence | Yes, `decision-12-10.md`, pending acceptance |
| The human reviewed it, the reviewer approved, and `human-gate.md` and `commit.txt` are written | **Human** |

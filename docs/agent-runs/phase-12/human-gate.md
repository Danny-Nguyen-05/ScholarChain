# Phase 12 human acceptance

Recorded: 2026-11-05 (America/Chicago).

## Decision and authority

**ACCEPTED BY THE HUMAN: Phase 12 (Subphases 12A, 12B, 12C and 12D, including the EMR Spark feasibility spike), with the 12-10 runtime decision, carried findings and open items below.**

This file transcribes the user's decision; it is not an agent approving its own work. On 2026-11-04 the user said they wanted the agents to write these files so they could read and approve them instead of typing them out: "I want the agents write those files for me, then I just need to read it and approve". The same day the user answered the coordinator's gate questions in chat:
- accept the 12-10 decision, with gaps carried;
- keep the local files for now;
- redact the account ID in `review.md` now;
- wait for their Billing and CloudTrail checks before closing.
No earlier human decision is changed.

Approval: **"I approve the human-gate.md"** — Danny Nguyen, in chat on 2026-11-05, after reading the complete draft, including the Billing and CloudTrail checks below. The user also asked for the commits that follow.

Acceptance covers, on `phase-12` (not yet merged to `main`):

- 12A: `a83f62e` — Terraform foundation and reviewed repairs
- 12B: `3b0855b` — infrastructure and the approved KMS repair
- 12C: `5ca8406` — read-only plan, repairs and independent review
- 12D billing preparation: `8903ce0`, `4000889`
- 12D spike: `f52b981` through `2d38f0f` (source and repairs), `2d2d224` (live evidence), and the Step D closeout commit named in [commit.txt](commit.txt)

## Accepted results

- **12-10 EMR Spark runtime: ACCEPTED** as recorded in [decision-12-10.md](evidence/12d-spike-closeout/decision-12-10.md). The runtime is EMR on EC2 `emr-7.8.0`, with Hadoop as the only EMR application, plus the bootstrap-installed portable Spark 3.5.4 / Scala 2.13.14 runtime on Java 17. The EMR module and the Phase 13 and 15 Spark steps use it. Gaps G1–G6 are carried. The S3 I/O approach (G1) and the EMR budget allocation (G6) will be decided in the Phase 13 work order.
- **Live proof:** attempt 5 on 2026-11-04. The driver and executors used Scala 2.13 only (6 JVMs, 0 mentions of 2.12). G1 output matched the local baseline on 28/28 tables and 587 rows (`allExactRowsMatch=true`). Everything was destroyed, and the after-inventory was clean. See [report.md](evidence/12d-spike-closeout/report.md).
- **Main environment:** never applied. The only live actions were the destroyed 12D spike and the separate deployer root, which is IAM only and retained.
- **Reviews:** user-supplied independent reviews are recorded in [review.md](review.md) and `evidence/12d-spike-offline/review-findings.md`. The final Step D recheck was **APPROVE**.
- **Gates:** last observed at `2d38f0f`: `sbt check` 1,267 passed and 0 failed on JDK 17; deployer 29/29; spike 38/38; scripts 70 OK; guard 0 findings. No tests were re-run for this closeout.

## Cost and IAM checks (filled in by the human)

- **Billing reconciliation:** the human checked the Bills page on 2026-11-05 at 10:25 CST, for the November 2026 billing period (screenshots in chat).
  - The bill status is **Pending** (estimated).
  - The estimated grand total is **USD 0.00**. All 11 listed services show USD 0.00: Data Transfer, EC2, EFS, EMR, Glue, KMS, Secrets Manager, SNS, SQS, S3 and VPC.
  - **The highest AWS Region spend is USD 0.34 in US East (Ohio).**
  - Modeled cost was about USD 0.35 for compute and ancillary resources, plus up to USD 5 for KMS. The cap was USD 10.
  - **Conclusion:** the observed spend of USD 0.34 matches the modeled USD 0.35 and is far under the cap.
  - The difference between the USD 0.34 region figure and the USD 0.00 service totals was not investigated. It may be credits or Free Tier. The cap applies to usage regardless of credits.
  - The bill is still an estimate. Charges for the 5 KMS keys may still post while they are pending deletion.
- **CloudTrail: CONFIRMED** from the us-east-1 Event history records the human pasted in chat on 2026-11-04. Each manual IAM window was closed by `scholarchain-billing-operator`, in a console session with `mfaAuthenticated=true`. In each window, `DetachUserPolicy` (`IAMFullAccess`) and `DeleteUserPolicy` (`scholarchain-operator-cli-login`) were recorded at the same second:

  | Window | Reported (CST) | CloudTrail (UTC) | CloudTrail (CST) | Event IDs (detach / delete) |
  |---|---|---|---|---|
  | 1 | ~11:07 | 17:08:20 | 11:08:20 | `0bd7242f…` / `6a7e2ac5…` |
  | 2 | ~12:35 | 18:34:54 | 12:34:54 | `5c71bf94…` / `0e58afc9…` |
  | 3 | ~13:56 | 19:56:02 | 13:56:02 | `14147f28…` / `72d55732…` |

  All three times are within about 1 minute of the reported times. The source IP, access key IDs and account ID are left out on purpose. The opening events (the attaches) were not checked.

## Accepted deferrals and open items

The human accepts Phase 12 with these items **OPEN/nonblocking**. Acceptance is not repair closure.

- **22 carried 12D findings,** owners and close-by in [carried-findings.md](evidence/12d-spike-closeout/carried-findings.md). **Item 17 must close before Phase 14 or any other EMR cluster in us-east-2.**
- **12-10 gaps G1–G6:** S3 I/O, dynamic allocation and the shuffle service, task nodes and scaling, larger data, runtime archive retention, and the EMR budget.
- **The main EMR module** (`infra/terraform/modules/emr/main.tf`) must be changed to the proven configuration by the infra-engineer, under a Phase 13 work order.
- **Earlier Phase 12 carries** remain as recorded in [repairs.md](repairs.md). N1 is still unverified; N9 is proven in the spike root only.
- **Accepted limitations:** AES-CTR rather than AES-GCM; Hadoop/YARN RPC unencrypted inside the private subnet; the node shutdown timer is best effort; destroy needs two passes.
- **Retained resources:**
  - The `scholarchain-deployer` role, its policies and its boundary.
  - The operator inline policy `scholarchain-assume-deployer`.
  - The local `scholarchain-deployer-tf` profile.
  - 5 KMS keys in PendingDeletion, deleting by about 2026-11-11.
- **Local files kept** (human decision): `target/phase12d-spike-live/` and the runtime tgz stay until Phase 13 decides gap G5.
- **Account ID:** at the human's direction, the coordinator replaced the account ID with `<acct>` in `review.md` lines 1975, 2009 and 2084. The ID still appears 7 more times in `review.md`, where the coordinator's original scan missed it, and in 76 other tracked files from the earlier 12C and billing work (12C evidence, billing evidence, phase records and `scripts/billing`). It is also in git history. Redacting it fully would mean editing earlier evidence and rewriting history. That needs a separate human decision and is not authorized here.

## Closeout boundary

This decision accepts the Phase 12 scope and the disclosed deferrals. It does not authorize merging, any Terraform apply of the main environment, another EMR cluster, deployment or expenditure. Those keep their separate gates. Phase 13 starts only on a new prompt from the user.

# Phase 13 human acceptance

Recorded: 2026-11-06 (America/Chicago).

## Decision and authority

**ACCEPTED BY THE HUMAN: Phase 13 (Subphases 13A, 13B and 13C, including 13C repair round 1), with the open decisions and deferrals below.**

This file transcribes the user's decision; it is not an agent approving its own work. On 2026-11-06, after the reviewer's 13C repair round 1 APPROVE and the final verification, the user said in chat: "I approve the change. Can you write the human-gate and commits.txt for me. I'll read and approve it or not. After my approval you can commit and push phase 13c." This follows the Phase 12 precedent, where the user asked the agents to write these files so the user could read and approve them. No earlier human decision is changed.

Approval: **"I have read and approve the human-gate.md"** — Danny Nguyen, in chat on 2026-11-06, after reading the complete draft. The user also asked for the commits and the push that follow.

Acceptance covers, on `phase-13` (not yet merged to `main`):

- 13A: `52c2e21` — reproducible check, package, plan, deploy, rollback and cleanup scripts (Review 5 APPROVE after four repair rounds)
- 13B: `5614445` — smoke, bounded pipeline, experiment and archive scripts (Review 1 APPROVE)
- 13C: the commit named in [commit.txt](commit.txt) — main EMR module port to decision 12-10, carried-finding closure and pre-Phase-14 hardening, plus repair round 1 (Review 2 APPROVE)

## Accepted results

- **Reviews:** every subphase was reviewed by a user-launched independent reviewer; verdicts are recorded verbatim in [review.md](review.md). Final verdicts: 13A Review 5 APPROVE, 13B Review 1 APPROVE, 13C Review 2 APPROVE.
- **Final verification:** the default seven-gate `scripts/check.sh` in a clean snapshot of the working tree, JDK 17.0.20.1, 2026-11-06T22:16:29Z–23:18:03Z: exit 0, `RESULT: PASS gates=7`.
  - terraform 7 / 19 / 37 / 40 / 6 / 77 passed, 0 failed.
  - Script suites: `scripts/tests` 856, `scripts/phase12d-spike/tests` 73, billing 69 / 47 / 39, `tests/scripts` 276, `tests/infra` 128; all executed, 0 skipped, 0 failed.
  - `sbt check` 40 / 667 / 18 (+1 canceled), 0 failed.
  - Snapshot identity 5437 / 0 differing.
  - Evidence: [final-check-full-clean-snapshot.txt](evidence/13c/orchestrator/final-check-full-clean-snapshot.txt), [test-report.md](test-report.md) "Subphase 13C — final verification (after the repair round 1 APPROVE)".
- **Section 11 checklist:** every item is done except this human gate; see the table in [test-report.md](test-report.md).
- **Main EMR module** now matches decision 12-10: `emr-7.8.0`, Hadoop only, sha-verified portable Spark 3.5.4 / Scala 2.13.14 / Java 17 bootstrap, EFS staging (G1 option ii), G2 shuffle tracking, G3 task nodes and managed scaling off by default, G6 caps.
- **EMR steps** fit the 10,280-character Args limit (longest 1,043 at maximum values) through sha-pinned step programs installed by the bootstrap.
- **Carried 12D findings:** status per item in [carried-findings-status.md](evidence/13c/carried-findings-status.md). Item 17 is closed offline (live ENI tagging unverified until Phase 14).
- **No live cloud action** in Phase 13: no AWS call, no real Terraform plan, no apply, no upload, no deployment.

## Accepted deferrals and open items

The human accepts Phase 13 with these items **OPEN/nonblocking**. Acceptance is not repair closure.

- **Pending human decisions** (13A; to be decided at the start of Phase 14):
  - A2 (the pinned teardown set, [repairs.md](repairs.md)).
  - The approval-format additions: `APPROVED_RECEIPT_SHA256`, `APPROVED_ENVIRONMENT`, the `cleanup-prepare` stage, `cleanup --confirm --plan`.
  - The live Terraform state location.
- **EMR pricing:** `EMR_PRICING_CONFIRMED_BY_HUMAN` stays `false`; the pipeline refuses `--execute` until the human confirms prices.
- **Run ledger:** initialize with `scripts/run-bounded-pipeline.sh --init-ledger` before Phase 15; an absent ledger refuses live runs.
- **Phase 14 tfvars:** add the four step programs to `emr_config.extra_artifacts` in `*.local.tfvars` with the sha256 values printed by `python3 -I scripts/lib/pipeline.py step-manifest`; the Terraform guard refuses a plan without them.
- **`scripts/billing/reviewed-pins.json`:** human-pinned size/sha256 pins for `tests/infra/terraform_source_guard.py` and `tests/infra/README.md` are stale (already stale at the 13C base); refresh is the human's.
- **ER JAR packaging:** BLOCKED-ON build-engineer.
- **EMR service policy review** at the Phase 14 pre-flight.
- **Carried items still open:** 24 (unchanged by design; two-pass destroy stays the procedure), 25 (optional tightening), 16 mitigated only (IAM has no condition key on the trust document).
- **Accepted limitations:** EMR in-transit TLS off (disclosed; Spark auth, AES-CTR and IO encryption and at-rest encryption stay on); task-group gp3 throughput cannot be pinned (provider has no argument; baseline 125 MiB/s); a verify-then-exec window in the on-node step launcher on root-owned mode-755 files.
- **Live-unverified until Phase 14/15:** the bootstrap on real nodes (runtime install, Java resolution, the four step programs), the EFS mount and egress, `command-runner.jar` running the launcher, the process-group kill and EMR cancel signal, item 17 stack tags on EMR-created ENIs, G2–G4, and the 10,280-character limit itself.

## Closeout boundary

This decision accepts the Phase 13 scope and the disclosed deferrals. It does not authorize merging, any Terraform plan with real credentials or apply, any upload, deployment, EMR cluster or expenditure. Those keep their separate gates. Phase 14 starts only on a new prompt from the user.

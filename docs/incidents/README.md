# Incident records

Index of incident records in `docs/incidents/`. The incident-responder owns this directory (ownership map: `../agents.md`). A record states facts from committed evidence and marks anything the evidence does not say as "not recorded" or "not determined". Records never change a human decision; they quote it.

Conventions:

- Dates are the day the incident happened. Times inside a record are UTC, with America/Chicago in brackets where useful (CST, UTC-6, on 2026-11-18).
- Severity is the incident-responder's assessment: low (no unintended cloud change, no lasting data or spend effect), medium (evidence or a capability is incomplete), high (not used so far).
- Status is as of the record. "Open as a known limitation" means the human accepted the item on 2026-11-20 and no fix or diagnosis exists yet.
- Records use no account IDs, e-mail addresses, key values or bucket names; buckets are named by role.
- Source of the Session 2 records: `../agent-runs/phase-15/evidence/session-2/INDEX.md`, the decision log, and `../agent-runs/phase-15/human-gate.md`.
- Source of the 2026-11-25 (Phase 18 Day 2) records and notes: the coordinator's decision log and the redacted run and cleanup logs under `../agent-runs/phase-18/evidence/day2/` (see its `INDEX.md`). America/Chicago is UTC-6 on that date.

| Date | Title | Severity | Status | Record |
|---|---|---|---|---|
| 2026-11-16 | P0 budget modify applied, wrapper stopped on its backup check | low | contained, recovery in progress (as written in the record's own header) | [2026-11-16-p0-budget-modify-backup-check.md](2026-11-16-p0-budget-modify-backup-check.md) |
| 2026-11-18 | EMR spark-job step failed in its template fetch (EmrFileSystem ClassNotFoundException) | medium | resolved 2026-11-25 (Phase 18 fix verified on EMR, one run) | [2026-11-18-emr-spark-job-step-emrfilesystem.md](2026-11-18-emr-spark-job-step-emrfilesystem.md) |
| 2026-11-18 | Vectors ingest 1 rejected all 10,000 items with HTTP 401 (invalid Voyage key) | low | closed; ingest 2 wrote 10,000 | [2026-11-18-vectors-ingest-1-voyage-401.md](2026-11-18-vectors-ingest-1-voyage-401.md) |
| 2026-11-18 | Base-apply 1 stopped at the runtime-archive upload (S3 RequestTimeout) | low | closed; base-apply 2 passed | [2026-11-18-base-apply-runtime-archive-requesttimeout.md](2026-11-18-base-apply-runtime-archive-requesttimeout.md) |
| 2026-11-18 | R-b load test aborted on a 5xx burst during the elasticity run | medium | open as a known limitation; cause not diagnosed | [2026-11-18-rb-load-test-abort-5xx-burst.md](2026-11-18-rb-load-test-abort-5xx-burst.md) |
| 2026-11-18 | Deployer role-session drops and profile mix-ups during the live session | low | closed for the session; later causes not recorded | [2026-11-18-deployer-session-drops.md](2026-11-18-deployer-session-drops.md) |
| 2026-11-18 | Permission gaps in the operator and deployer profiles, met by substitute checks or the root console | low | closed for the session; kit follow-ups open | [2026-11-18-console-permission-gaps.md](2026-11-18-console-permission-gaps.md) |
| 2026-11-18 | The live kit lacked the narrow a7, b3b and c5 IAM policies | low | closed for the session; kit and runbook correction open | [2026-11-18-kit-missing-a7-b3b-c5-policies.md](2026-11-18-kit-missing-a7-b3b-c5-policies.md) |
| 2026-11-25 | EMR hadoop-prep step failed: job 2 input (job 1 output) not found on the shared mount | low | mitigated by one retry (run 5 passed); root cause open, follow-up proposed | [2026-11-25-emr-hadoop-prep-intermediate-missing.md](2026-11-25-emr-hadoop-prep-intermediate-missing.md) |

All seven Session 2 failures named in the Phase 17 work order (package 17B) have evidence and a record; none was skipped.

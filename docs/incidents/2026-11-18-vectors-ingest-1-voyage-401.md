# Incident 2026-11-18: vectors ingest 1 rejected all 10,000 items with HTTP 401 (invalid Voyage key)

Status: closed (recovered in session by ingest 2 with a new key). Severity: low (about 46 minutes lost, no vectors written, no data changed, no charge expected for 401 replies).
Owner: incident-responder (record). Human decisions are in the decision log and `../agent-runs/phase-15/human-gate.md`; this record does not alter them.
Sources and limits: written offline from the committed Session 2 evidence; no cloud or model call. Times are UTC on 2026-11-18, with America/Chicago (CST, UTC-6) in brackets where useful. "Derived" times are computed here from a tool's own completion stamp and elapsed time, not logged by the coordinator. The 2.4 MB per-item ingest-1 report is not in the repository (`../agent-runs/phase-15/evidence/session-2/INDEX.md` lists it as excluded); its summary is in the decision log. Key values were never read or recorded.

## Summary

Ingest run 1 (`run-20261118-ingest`, `LiveEmbeddingIngestMain`, model `voyage-4-lite`, 256 dimensions, 10,000 selected documents) ran 45:40 and ended with `IllegalArgumentException: live-ingestion-rejected-items` (exit 1). The report shows written 0 and rejected 10,000, every item `embedding-provider-rejected` (a Voyage non-429 4xx reply), with 10,000 embedding calls (7,915 underlying). A direct test by the human in terminal T1 returned HTTP 401 "Provided API key is invalid." for the key (length 46). The same invalid key was stored in the `voyage-api-key` secret container at block 15. Nothing was written. A new key was created, tested (HTTP 200, length 46), and ingest 2 (`run-20261118-ingest-2`) wrote 10,000 with 0 rejected.

## Timeline

| Time (UTC) [CST] | Event | Source |
|---|---|---|
| 16:15:29 [10:15:29] | Block 15: `put-secret-value` stores the human-created Voyage key in the Voyage secret container; `describe-secret` shows one AWSCURRENT version; the log shows version ids only | decision log line 24; `../agent-runs/phase-15/evidence/session-2/a-setup/b3b-provider-keys.log` |
| 17:04:31 | Block 24 render-only PASS: 10,000 documents, 0 embedding calls, no state written | decision log line 37 |
| 17:26:27 | Block 25 prep: ingest config and approval written (run id `run-20261118-ingest`; caps 10,000 items, 8 concurrency, 20,000 requests, USD 0.25); loader profile first bound to the deployer session, corrected before use | decision log line 38 |
| about 17:28 (derived) | Ingest 1 starts: completion stamp "12:13:34 PM" local (18:13:34Z, assuming CST) minus the elapsed 45:40 | `../agent-runs/phase-15/evidence/session-2/vectors/ingest.log` |
| 18:13:34 [12:13:34] (derived) | Ingest 1 ends: `live-ingestion-rejected-items`, exit 1, total 2740 s | `../agent-runs/phase-15/evidence/session-2/vectors/ingest.log` |
| 18:20:41 [12:20:41] | Coordinator entry: written 0, rejected 10,000 all `embedding-provider-rejected`, embeddingCalls 10,000 (7,915 underlying). Human test in T1: key length 46, HTTP 401 "Provided API key is invalid." The same key is in the secret (block 15). No vectors written; no Voyage charge expected for 401s | decision log line 40 |
| 18:22:28 [12:22:28] | New Voyage key created by the human (`scholarchain-session2b` in the Voyage dashboard); T1 test HTTP 200 (length 46) | decision log line 41 |
| about 18:22:40 | Ingest 2 starts under run id `run-20261118-ingest-2`; new approval written; forked JVM active (CPU about 37% versus about 3% for run 1) | decision log line 42 |
| 18:27:58 [12:27:58] | Human (root, console, private window) replaces the secret value with the working key (secret version changed 12:27:29 CST) | decision log line 43; `../agent-runs/phase-15/evidence/session-2/rb-runtime/b30-keys-check.log` |
| 19:09:03 (derived) | Ingest 2 ends: exit 0, 46:22 | `../agent-runs/phase-15/evidence/session-2/vectors/ingest-2.log` |
| 19:11:05 [13:11:05] | Block 25 PASS: written 10,000, rejected 0, conflicts 0, retried 0, 3.60 vectors per second; per index community 3,292, path 120, paper 3,292, researcher 3,292, topic-institution 4 | decision log line 44; `../agent-runs/phase-15/evidence/session-2/vectors/ingest-report-2.json` |
| 19:11:59 | Block 26 query smoke PASS: 5 of 5 samples, 7 verified pointers | decision log line 45 |
| 20:22:44 | Block 30 keys check: Voyage secret AWSCURRENT is the working key, the invalid key is AWSPREVIOUS | decision log line 55; `../agent-runs/phase-15/evidence/session-2/rb-runtime/b30-keys-check.log` |
| 22:46:11 [16:46:11] | Both Voyage keys (`scholarchain-session2b`, `scholarchain-session2`) revoked by the human | decision log line 85; `../agent-runs/phase-15/evidence/session-2/section-c/c5b-key-revocation.log` |

## Detection

The ingest tool's own failure: `live-ingestion-rejected-items` and exit 1 at the end of a 45:40 run. The coordinator then read the report counts, and the human tested the key directly and got HTTP 401. There was no earlier signal; the evidence shows no provider-side check of the key between block 15 and the start of ingest 1.

## Impact

- Time: about 46 minutes of ingest wall time, plus about 7 minutes before the diagnosis was logged.
- Data: none written (`written 0`); the vector index was not touched by ingest 1. Ingest 2 wrote the full 10,000.
- Spend: no Voyage charge expected for 401 replies (decision log). The C11 Voyage dashboard read USD 0.00 for November, with the R-b window token figure not isolable and so recorded as unverified (`../agent-runs/phase-15/evidence/session-2/c11/cost-report.log`). Ingest 2 assumed upper bound was USD 0.23 and the query smoke USD 0.0232, from the run reports (not billing figures).
- Schedule: Gate 1 still passed at 19:58:59Z, with the decision log noting 7 hours to its hard stop (line 46; `../agent-runs/phase-15/evidence/session-2/00-timeline/gate1.log`). Any effect on later timing is not recorded.
- Runtime: none. The invalid key sat in the secret from 16:15:29Z to 18:27:29Z; the runtime stack was not applied until 20:28:16Z.

## Root cause

Direct cause: the Voyage API rejected the key as invalid (HTTP 401), so every embedding request was refused.

How the key came to be invalid (mistyped, truncated, wrong or revoked key, or a paste error): not recorded. `../agent-runs/phase-15/human-gate.md` says only that an invalid key "had been pasted". Both the invalid and the working key have length 46, so a length check would not have separated them.

Contributing, from the evidence: the B3b and block 30 checks recorded only secret version ids (`../agent-runs/phase-15/evidence/session-2/a-setup/b3b-provider-keys.log`, `../agent-runs/phase-15/evidence/session-2/rb-runtime/b30-keys-check.log`); they cannot show whether the value works. Why ingest 1 ran for 45:40 before ending (that is, whether the tool stops early after repeated 4xx replies) is not recorded.

## Trace and run IDs

- Ingest 1: `run-20261118-ingest`, config sha256 prefix 3211aa88, approval sha256 prefix 38116437, report `ingest-report.json` (not in the repository).
- Ingest 2: `run-20261118-ingest-2`, approval sha256 prefix 5a06ba97, report `../agent-runs/phase-15/evidence/session-2/vectors/ingest-report-2.json`.
- Render manifest sha256 prefix df0d5028 (`../agent-runs/phase-15/evidence/session-2/vectors/render-manifest.log`); fallback export `run:ba7402d1-959a-4277-8c6e-e92878a38afa`.
- Query smoke run `run-20261118-query-smoke`.

## Recovery and the human decision behind it

The human created and tested a new key (HTTP 200), after which the coordinator started ingest 2 under a new run id with a new approval file. The decision log records no separate quoted human decision for the rerun; deviation 3 in `../agent-runs/phase-15/human-gate.md` ("ingest was re-run under a new run id after the key fix") was accepted by the human in the decision of 2026-11-20. The root-console write of the working key into the secret (18:27:58Z) is deviation 1 in `../agent-runs/phase-15/human-gate.md`, also accepted on 2026-11-20. Both Voyage keys were revoked at 22:46:11Z.

## What was not done

- No data repair and no deletion; nothing needed one.
- The ingest-1 report was not committed (size) and no per-item rejection analysis was kept in the repository.
- No provider-side key check was added to the live procedure during the session.

## Follow-ups

Proposals for the owners; none is decided.

| Item | Owner | Status |
|---|---|---|
| Add a one-request key probe (expect HTTP 200) to the live runbook between the key store step and the first ingest | documentation-engineer (runbook), infra-engineer (kit) | Proposed |
| Consider stopping an ingest after a run of consecutive non-429 4xx replies instead of finishing all items | rag-engineer | Proposed; whether the tool already has such a limit is not recorded |
| Record the cause of the bad paste, if the human remembers it | human | Not recorded |

## Evidence

- `../agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md` (lines 24, 37-45, 55, 85)
- `../agent-runs/phase-15/evidence/session-2/vectors/ingest.log`
- `../agent-runs/phase-15/evidence/session-2/vectors/ingest-2.log`
- `../agent-runs/phase-15/evidence/session-2/vectors/ingest-report-2.json`
- `../agent-runs/phase-15/evidence/session-2/vectors/render-manifest.log`
- `../agent-runs/phase-15/evidence/session-2/vectors/query-smoke.log`
- `../agent-runs/phase-15/evidence/session-2/a-setup/b3b-provider-keys.log`
- `../agent-runs/phase-15/evidence/session-2/rb-runtime/b30-keys-check.log`
- `../agent-runs/phase-15/evidence/session-2/section-c/c5b-key-revocation.log`
- `../agent-runs/phase-15/evidence/session-2/c11/cost-report.log`
- `../agent-runs/phase-15/evidence/session-2/INDEX.md` (excluded ingest-1 report)
- `../agent-runs/phase-15/human-gate.md` (Vectors, deviations 1 and 3)

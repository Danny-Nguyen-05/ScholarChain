# Phase 14 repairs

## Subphase 14A — repair round 1 (from review 1, REQUEST-CHANGES)

Source: the user-supplied external review in `review.md` (Subphase 14A, review 1). Severity, owner and acceptance checks are kept as the reviewer gave them.

| ID | Severity / blocking | Owner | Paths named by the reviewer | Acceptance check (reviewer) | Repair status |
|---|---|---|---|---|---|
| F1 | High / yes | coordinator (request); human (path); service-engineer + infra-engineer (code, as the human decides) | `approval-request-14a.md:84,89`, §1; `modules/runtime/compute.tf:58,94-96,124-127`; `ServiceMains.scala:42-44`; `phase12b-variables.tf:158-161`; `phase12b.tf:42` | A §1 row "Live service composition" marked M, with evidence and owner. Steps 8 and 10 corrected. The request never tells the human to set `runtime_composition_verified=true` before the composition is replaced and tested. `prompt.md` records the human's decision. | fixed offline (repair round 1) |
| F2 | Medium / yes | infra-engineer; test-engineer if the guard changes | `deployer/phase14_main.tf:125-139,158-166,298-361`; `deployer/README.md:108-109` | Either narrow the statements (key administration in the key policy naming the deployer role, with a negative test that a foreign tagged key or security group gains no mutation rights), or rewrite the honest-list rows exactly, pin the reachable set with a test and record a new human acceptance. | fixed (narrowed) |
| F3 | Low / no | coordinator | `approval-request-14a.md:99,105,106` | Record-template lines carry no trailing `# …` comments. | fixed |
| F4 | Low / no | coordinator | `approval-request-14a.md:159,166` | The Haiku line is no longer marked unpriced; the authored maxima include metrics (about 0.773/h, USD 18.55/day). | fixed (0.7726/h, USD 18.54/day; Haiku 4.5 reserve stated as a cap) |
| F5 | Low / no | infra-engineer | `deployer-apply-proposal.md` | A rule: on `LimitExceeded`, re-plan, expect only the remaining creates, re-apply. | fixed (proposal and deployer README) |
| F6 | Observation / no | — | runtime boundary `GetSecretValue` on `secret:*` | Note only; a possible later tightening is `secret:scholarchain-course-*` plus that naming for human-created secrets. | noted |

### User decision for repair round 1 (2026-11-07)

The user said: "fix all blocking bugs for me". The coordinator recorded it as follows:
- **F1:** option (1), a live-composition work order before the 14A commit:
  - `service-engineer` for the service code;
  - `infra-engineer` for the task environment, including passing the synthesis inference-profile ID as the model ID.
- **F2:** the reviewer's recommended narrowing:
  - key administration moves into the key policy, which names the deployer role;
  - adopted-group mutation reach is removed.

### Repair evidence (round 1)

Agent-reported results are in `owner-report.md`, "Repair round 1". The coordinator's own results are in `test-report.md`, "Repair round 1".

- **F1:**
  - `modules/services`: AwsConfig, AwsPorts, AwsComposition, ReadinessGate and LiveAdapters, with 5 new specs plus LiveGraphSnapshotSpec;
  - `modules/storage`: `NeptuneGraphReader.connect`, `DirectedGraphReader` and DirectedGraphReaderSpec;
  - `modules/runtime/compute.tf` and its variables and outputs: the per-role aws environment, gated by `runtime_composition_verified`;
  - `modules/identity/main.tf`: `ReservationInQuerySessionTableAndIndex`, `ListRagBucketPrefixes` and `HeadAbsentRagKeyAs404NotListing`;
  - approval request rows 17 and 18 and steps 8 and 10.
- **F2:**
  - `deployer/phase14_main.tf`: 5 statements removed;
  - `modules/identity/main.tf`: a 5-statement key policy;
  - `modules/network/main.tf`: `aws_default_security_group` removed;
  - D6 exception removed from `scripts/phase12d-spike/tests/test_terraform_static.py`;
  - new negative tests in the deployer and root suites and in `tests/infra` (`Phase14F2InMemory`);
  - evidence in `evidence/14a/r1/`.
- **F3 and F4:** `approval-request-14a.md` Sections 4 and 5.
- **F5:** `evidence/14a/deployer-apply-proposal.md` and the deployer README.
- **Also routed:** test-engineer updated 5 stale `tests/infra` tests.

## Subphase 14A — review 2 (repair round 1 recheck): APPROVE

These are nonblocking findings from `review.md`, review 2.

| ID | Severity | Owner | Status |
|---|---|---|---|
| N1 | Low | coordinator | fixed (docs only): the passing-snapshot line in approval-request-14a.md §7 now names `c4dbd00` and `evidence/14a/gates/check-full-r1.txt` |
| N2 | Low | coordinator + deploy-engineer | carried to 14B Step 0: before runtime-apply, the 14B record states the expected 14B smoke result. A no-data `smoke-query` stop is not a rollback trigger. |
| N3 | Low | infra-engineer (only through a routed repair and a recheck) | carried as a 14B watch item: no `health_check_grace_period_seconds`, and query-api readiness waits for both peer services |
| N4 | Observation | infra-engineer | carried: stale wording at compute.tf:105, phase12b.tf:43 and phase12b-variables.tf:161, to fix the next time these files are touched |

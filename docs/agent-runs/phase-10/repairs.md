
# Subphase 10A repair round 1

| Finding | Severity / disposition | Owner | Acceptance check |
|---|---|---|---|
| F1 | High, blocking, routed for repair | service-engineer | Retried(1,Written(s)) binds/schedules once; first200 or202 with valid job; same-body stored replay no rerun; different-body409; Retried Rejected/Unchanged reconcile without execution; module, independent10A and full JDK17 check pass. |
| F2 | Medium, nonblocking, listed only; not authorized for this repair | service-engineer | Terminal failure replay retryable:false or document/test new key required. |
| F3 | Low, nonblocking, listed only | service-engineer |202 reference reflects persisted state or documents QUEUED as accepted. |
| F4 | Low, nonblocking, listed only | service-engineer | Configuration failure exits nonzero. |
| F5 | Low, nonblocking, listed only | test-engineer / service-engineer | Test failed half-open probe reopening,429 queue-full and RESULT_TOO_LARGE. |

Only F1 is in scope. No10B work or reviewer invocation. Exact user-supplied verdict/findings in review.md and evidence/10a-repair-1/external-review.txt.

## F1 implementation/gate result (review pending)

Successful retried creation now shares the creator path; other retried results still reconcile without execution. Regression red3run/2pass/1fail reproduced503; post-fix services19/19,independent10A20/20,fullcheck1173/1173pass,exit0,JDK17. Final gate713s. Evidence: evidence/10a-repair-1/. F2–F5 untouched. Independent recheck must decide acceptance; this entry is not reviewer approval.


## Subphase 10B — approved carried findings

The user approved defaults including all F2–F5. These are implementation treatments awaiting independent10Breview, not a self-issued approval.

- F2 (Medium, service-engineer): terminal persisted failures now retryable:false; same-key replay stays terminal; documented a new key for a deliberate new run. Acceptance: queue-full429/oversize502 tests and bounded-retry/replay tests pass.
- F3 (Low, service-engineer):202reference usespersistedQUEUED/RUNNINGstate. Acceptance: RUNNING replaytestpasses.
- F4 (Low, service-engineer):mainconfigurationfailureexit2. Acceptance: allfour rebuiltDockerimages observedexit2 without requiredconfiguration.
- F5 (Low, service-engineer/test-engineer): failedhalf-open probe reopens;queuefull429;RESULT_TOO_LARGE casesadded. Acceptance: targeted-3 observed services 26/26 and independent 36/36 in six suites; the final targeted run observed 17/17 10B tests in four suites. All 37 independent 10A/10B tests ran together only within the full check's 625 independent tests; full check passed 1199/1199.
- O1 (build-engineer): allfourimages rebuiltfromcurrentapplicationJar+promptassets; imagehashes and exactpackagehashes retained.
- O2 (orchestrator): every gate records sourcehashes beforeexecution and failedattemptlogs; finalhashes and post-checkREADME-only change retained.

Evidence: evidence/10b/prior-findings.md, check-summary.json, source-files.json, *-result.json, owner reports and Docker result JSON. F1 remains CLOSED per prior externalreview; its three regressiontests pass unchanged.


## Subphase 10B repair round 1

User Step 0 answer: **F6 + F9 count corrections (Recommended)**. No human decision file was changed. Original verdict and all findings are retained verbatim in review.md and evidence/10b-repair-1/external-review.txt.

| Finding | Severity | Owner | Routing and acceptance |
| --- | --- | --- | --- |
| F6 | Medium, blocking | service-engineer; test-engineer; build-engineer | Implement request-specific graph deadline classification with no retry/breaker failure; independently verify >=4 HTTP requests, exact one call each, traced504, CLOSED gauge, readiness200 and later success; preserve real-outage trip/readiness503; rerun full JDK17 check and rebuilt four-image/eight-boot/three-main smokes. |
| F7 | Low, nonblocking | service-engineer | Carried, not authorized: at stored attempt limit go directly to DLQ without another processor call. |
| F8 | Low, nonblocking | service-engineer | Carried, not authorized: contain worker-loop adapter exceptions or reflect thread death in health. |
| F9 | Low, nonblocking | service-engineer (README); orchestrator (repairs.md) | Authorized: report observed targeted-3 36/36 in6suites and final17/17 in4suites separately;37 together only within full625. Then report new repair gates as actually observed. |
| F10 | Low, nonblocking | service-engineer; rag-engineer if hooks needed | Carried: actual synthesis/verification stage hooks and explicit indexes/template IDs. |
| F11 | Low, nonblocking | service-engineer | Carried: new route log-template labels. |
| F12 | Low, nonblocking | service-engineer | Carried: preserve graph cap/path422 codes generally. Only distinct F6 deadline code handling is in this round. |
| F13 | Low, nonblocking | service-engineer | Carried: synchronous/evidence/explain/job response examples and fuller answer schema. |
| F14 | Low, nonblocking | service-engineer | Carried: semantic environment configuration and configured prompts path. |
| F15 | Observation/future | service-engineer | Carried: internal semantic proxy surface and local fixture path/community wiring. |

Prior review confirmed F1 no regression, F2–F5 fixed, and O1/O2 closed. Preserve those behaviors. Repair results are pending at this routing checkpoint and will be appended after actual gates.

### Repair round 1 observed completion

F6 implementation and feature gates passed; independent closure is pending user-launched recheck. F9 corrected the prior targeted-count wording. Final targeted services31/31 in5suites and independent41/41 in7suites; full check1208/1208 in147suites,exit0,JDK17.0.20.1,sbt709s/wall710.548s. Four rebuilt images/eight startup cases plus three-main remote/stop-graph readiness checks passed. Original failed red gates and intentionally cancelled full attempt retained. Full-log SHA256 39aaf21ff6902af2bcde194c7e45622f207aa9338adebaaf5b04dc8b2bc6f4d3. Only README observed-count documentation changed after final check snapshot. F7,F8,F10–F15 remain unchanged. Evidence: evidence/10b-repair-1/.


## Subphase 10B repair round 2

The user-supplied recheck is retained verbatim in review.md under Subphase10B repair round1 and in evidence/10b-repair-2/external-review.txt. F9 is **CLOSED by the external recheck**. F1–F5 and O1–O2 have no regression per that review. Scope confirmation is pending at this routing checkpoint; no implementation has started.

- **F6 residual — Medium, blocking.** Owners: service-engineer (budget rule/module tests/docs), test-engineer (independent equal-budget HTTP test), build-engineer (four-image rebuild/eight startup cases/three-main smoke). A graph operation budget must be strictly below the proxy attempt deadline with deterministic cursor-stable forwarding or equivalent safe startup validation. Acceptance: real blocking GraphApi with equal default-style300ms graph/proxy budgets and no caller timeout; burst4 returns caller-traced nonretryable GRAPH_DEADLINE_EXCEEDED exactlyonce per backend execution, CLOSED before readiness, readiness200 and later normal success; refusal/no-response/unready503 still trip the breaker. Red/targeted/full JDK17 gates and consistent rebuilt Docker configuration required.
- **F16 — Low, nonblocking, future live-adapter gate.** Owner: service-engineer. A live GraphSnapshot adapter must report backend readiness instead of inheriting unconditional readiness. Acceptance: live-adapter readiness reflects unavailable/hung snapshot backend. Carried; not included in the recommended F6-only scope.
- **F7,F8,F10–F15:** carried and unchanged. Their original owners and acceptance checks remain as recorded in the external reviews and repair1 routing table.

No human decision file was written or altered. All uncommitted10B and repair1 source was retained;33 prior manifest hashes matched before implementation.

Step 0 confirmed by user: “yes fix f6 for me, since it is the blocking bug”. Proceed with F6 residual only; F7,F8,F10–F16 stay carried.

### Repair round 2 observed completion

F6 residual implementation and gates passed; independent closure awaits user-launched recheck. Deterministicconfiguredresponse reserve25percent produces graphwork3750msunderdefaulttransport5000; all4graphoperations consume forwardedbudget,including omitted/nearcap. IndependentrealGraphApi300/300 bursts passwithoneexecutioneach,tracedmarker,CLOSEDbeforehealthprobes,ready200,normalsuccess;prioroutagecases stillpass. Targeted36/36services6suites and44/44independent8suites;full1216/1216 in149suites,exit0,JDK17.0.20.1,sbt721s/wall723.581s. Full-logSHA256 8930aa7a4c872e6412011fc362a2e00b5cb5a18640b059bc9e8b8dfffe26c526. Four rebuiltimages/eightbootcases/3-mainremoteequal500mscaps+stopgraphpassed. F9CLOSED;F7,F8,F10–F16carriedunchanged. Evidence: evidence/10b-repair-2/.


## Subphase 10B repair round 2 — external recheck APPROVE

The user-supplied independent recheck APPROVED Subphase 10B after repair round 2. **F6 CLOSED (round 2)** and **F9 CLOSED (round 1)**. No blocking finding remains. F1–F5 and O1–O2 have no regression per the external review. This records the reviewer verdict, not a human phase gate. The verbatim review is retained in review.md.

### Carried inputs for Phase 11 or later

| ID | Owner | Nonblocking follow-up |
| --- | --- | --- |
| F7 | service-engineer | At the stored attempt limit, retry DLQ publication without another processor/provider call. |
| F8 | service-engineer | Contain unexpected worker-loop adapter exceptions or reflect a dead loop in health/readiness. |
| F10 | service-engineer; rag-engineer if stage hooks are needed | Observable synthesis/verification stages and explicit index/query-template audit fields. |
| F11 | service-engineer | Specific safe route labels for new/internal routes instead of unmatched. |
| F12 | service-engineer | Preserve specific graph cap/path 422 codes through the proxy. |
| F13 | service-engineer | Add response examples and a fuller declared answer shape. |
| F14 | service-engineer | Environment-driven semantic limits and configured prompt asset path. |
| F15 | service-engineer | Revisit internal semantic proxy surface and local fixture path/community reads at live composition. |
| F16 | service-engineer | Require live GraphSnapshot backend readiness reporting. |
| F17 | service-engineer / infra-engineer (Phase 12) | Configure SCHOLARCHAIN_GRAPH_TIMEOUT_MS consistently once per environment across query-api and graph-service. |
| O3 | orchestrator | Raw logs are retained in /tmp only; hashes/excerpts satisfy lean evidence, but raw logs are not durable across reboot. |

Phase 10 is ready for the user's own diff review, Subphase 10B commit on phase-10, and human-gate.md/commit.txt. Those human-owned records remain unwritten by agents. Phase 11 requires a separate explicit user prompt; no Phase 11 work is started here.

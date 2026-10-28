# Phase 11 routed defects and repairs

## Subphase 11A

STATUS: COMPLETE (11A defect accounting; external review pending)
OWNER: coordinator; future repairs routed by docs/agents.md.
WORK ORDER: Retain every exposed production defect without production edits during 11A.
FILES CREATED: evidence/11a/defects.json and this routing record.
FILES MODIFIED: No production files.
COMMANDS RUN: See evidence/11a/commands.json for exact targeted/full gates.
TEST RESULTS: Targeted 19/19; final full 1,231/1,231, zero failures/errors/skips.
VALIDATION RESULTS: Zero production defects exposed by these runs; ExposedDefect count: 0. No tag or build exclusion was necessary. A Scala indentation error in a new test was corrected by its test-engineer before successful targeted/full execution; it is not a production defect.
ASSUMPTIONS: Passing bounded tests do not prove the repository has no defects.
RISKS: Earlier-phase findings retain original owners/status; no closure or repair is inferred from 11A. Full review/production repairs belong to 11C.
MANUAL ACTION REQUIRED: User launches the 11A reviewer and returns its verdict.
BLOCKED-ON OWNER: None for current accounting; future findings route to named owners.
BLOCKED-ON EVIDENCE: External review pending.
NEXT GATE: Read-only 11A review; stop before 11B.

### Subphase 11A external review — nonblocking, no repair authorized

The user supplied APPROVE for 11A with no blocking findings. The verbatim verdict is appended in review.md. Earlier pending-review statements above are historical. No repairs were made in this recording step.

| ID | Owner | Disposition |
| --- | --- | --- |
| N1 | Coordinator | Logged; no 11A repair authorized. In 11B, report formatter rewrites explicitly or use scalafmtCheck for coordinator gates. |
| N2 | Coordinator | Logged; no 11A repair authorized. In 11B, confirm specialist writing has stopped before any gate and write each start record once immediately before launch, without rewriting it. |
| N3 | test-engineer | Logged; optional assertion/report-strengthening work, no repair authorized. |
| N4 | hadoop-engineer if confirmed; test-engineer for any resulting assertion update | Logged as an unverified 11C investigation lead concerning markup-sensitive title blocking; no investigation or repair now. |
| N5 | Coordinator | Disclosed limits accepted by the reviewer; retain the reading, model-revision, temporary-log and synthetic-fixture limitations. |

Next gate: user commits approved 11A on phase-11, then 11B Step 0. The coordinator will not commit, push, write human-owned records or begin 11B before the required commit gate.


## Subphase 11B

STATUS: COMPLETE (combined11A/11B exposed-defect accounting; independent 11B review pending)
OWNER: Coordinator; future production repairs stay with module owners.
WORK ORDER: Report exposed production defects without production changes during11B.
FILES CREATED: evidence/11b/defects.json.
FILES MODIFIED: This appended section only for defect accounting.
COMMANDS RUN: Targeted/full gates in evidence/11b/commands.json.
TEST RESULTS: Targeted 17/17; full 1248/1248; zero failures/errors/skips.
VALIDATION RESULTS: Combined11A 0 + 11B 0 = 0 exposed defects. No ExposedDefect tags, exclusions or explicit defect runs needed. The new-test Logback compile error was corrected by the test owner without build/production changes. Existing findings retain prior owner/status; no blanket closure implied.
ASSUMPTIONS: Passing synthetic cases do not establish defect absence.
RISKS: Earlier registers remain open as documented.11A N1/N2 lessons applied; N3/N4 not repaired or investigated, N5 limitations retained. Whole-repository review and repairs belong 11C.
MANUAL ACTION REQUIRED: User launches independent 11B review and returns verdict.
BLOCKED-ON OWNER: None for local accounting.
BLOCKED-ON EVIDENCE: Independent11Breview pending; live gates deferred.
NEXT GATE: Read-only 11B review; no production repairs or11Cpreparation.

### Subphase 11B external review — nonblocking, logged only

User-supplied external verdict received 2026-10-28: APPROVE, no blocking findings. The designated verdict is retained verbatim in review.md. Earlier pending-review statements are historical. No finding below was repaired, routed for implementation or independently reproduced in this recording step.

| ID | Severity | Owner | Evidence and acceptance check | Disposition |
| --- | --- | --- | --- | --- |
| F11B-1 | Medium | service-engineer; test-engineer for a reproduction if confirmed in 11C | Code-reading lead at modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala:152-156, :178-190, :114 and modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/DynamoStorage.scala:137. A body-binding update that applies its write but loses the reply can return Retried(1, Rejected("conditional-conflict")); submit may return 503 without scheduling, while same-key replay observes a bound QUEUED row and returns 202 indefinitely until TTL. N04 covers only a clean rejection. Acceptance: a fake update that applies the write then returns that retried rejection must reconcile/schedule exactly once; replay must neither strand the job nor execute it twice. | Nonblocking 11C review input; unexecuted and unconfirmed; no repair authorized now. |
| F11B-2 | Low | test-engineer | AdversarialRuntimeHttpSpec.scala:138-140 requires replay after a failed bind to return 503 again, although that response is retryable and the reservation cannot currently progress. Acceptance: assert no workflow/model call plus a non-2xx or documented status, or explicitly record the current-behavior expectation; reconsider if reservation liveness is repaired. | Nonblocking; logged only, no repair authorized now. |
| F11B-3 | Low | test-engineer for name/scope; service-engineer if error clarity changes | AdversarialRuntimeBoundarySpec.scala:77-98 calls only ServiceConfig.fromEnvironment for two required credential omissions; its name says "before composition" without exercising startup. Generic error does not name the missing key. Acceptance: align name with actual scope or exercise startup composition, and record the error-clarity decision. Any variable name in an error must omit its value. | Nonblocking; logged only, no repair authorized now. |
| F11B-4 | Info | coordinator for coverage wording; test-engineer for assertions | Category 16 maps E11 audit-persistence failure beyond the three named faults; those faults are independently covered by N10/N04/N17. AdversarialRuntimeHttpSpec.scala:76 summary.contains("3") is weak but backed by exact claim-value assertions at :71-75. Acceptance: preserve exact assertions and honest coverage mapping; no action required. | Nonblocking; logged only, no repair required. |

Carried unchanged: 11A N3/N4/N5; temporary raw-log durability; unavailable exact model revision; Phase 9 NB1–NB10; Phase 10 F7/F8/F10–F17; earlier Phase 5–10 limits. The combined exposed-test inventory remains zero: the newly reported F11B-1 lead has no executed reproduction yet. No production, build or test file changed, no human decision record was written, and no 11C work was started. Next gate: user commit of approved 11B, then 11C Step 0.

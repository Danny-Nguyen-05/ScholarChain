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


## Subphase 11C

First stop point: assembly only. No finding has been routed for implementation and no repair has run. The combined ExposedDefect inventory remains zero; F11B-1 and 11A N4 remain unconfirmed review leads. F11B-1..F11B-4 and earlier findings retain their original owners, severity and dispositions. See evidence/11c/carried-findings.md for review context. Await the user-launched whole-repository verdict before grouping/routing any blocking findings; each authorized owner batch is a separate repair stop point.


### Subphase 11C initial review — findings and repair round 1, batch 1

User-supplied REQUEST_CHANGES: R11C-1/R11C-2 are blocking and authorized for this batch. Findings are code-reading confirmations, not executed reproductions. Only the assigned service/test paths may change. R11C-5 README inclusion is pending Step 0. No ownership is inferred for R11C-3.

| ID | Severity | Owner | Blocking | Acceptance check and scope |
| --- | --- | --- | --- | --- |
| R11C-1 (F11B-1) | High | service-engineer; test-engineer independent HTTP regression | Yes | QueryService.scala:152-156,178-191,108-115; StorageRows.scala:224-241; DynamoStorage.scala:122-138; StorageRetry in S3ObjectStore.scala:36-48. A binding update applies then returns Retried(1, Rejected("conditional-conflict")); primary read must recognize the binder's revision/fingerprint/requestId/traceId and schedule exactly once. Module and independent HTTP tests require completion, stored-result same-key replay without rerun, changed-body 409. Default session TTL is None: previous “until TTL” wording understated permanent default stranding. Fix only service-owned implementation/tests, no storage edits. |
| R11C-2 (F11B-2 production) | Medium | service-engineer; test-engineer | Yes | QueryService.scala:88-103,156,178-181; AdversarialRuntimeHttpSpec.scala:117-143. After one clean bind rejection an unbound reservation must recover on same-key replay through revision-0 CAS, or reach a documented nonretryable terminal outcome. Concurrent replay binders never schedule twice; no permanently stranded retryable 503. Update the independent assertion that pins the defect. Same batch as R11C-1. |
| R11C-3 | Medium | ORPHAN — human must assign writer | No | 24 tracked file:/var/** Hadoop stats/.crc outputs from Phase 4 commit 3ccd61c; path has colon/Windows checkout issue. Acceptance: git ls-files 'file:*' empty, deletion attributed to a human-assigned owner. No assignment, deletion or ignore edit authorized in this batch. |
| R11C-4 (11A N4) | Low | hadoop-engineer; test-engineer if contract changes | No | DerivedRecords.scala:342-347,552-553, TextNorm.scala:10-17; markup/no-markup same title/year yields different title-year keys/titleEqual. Verify shared title-year key or documented decision for Learning <i>k</i>-Means vs Learning k-Means (2020). Other blocking keys can mitigate; no repair now. |
| R11C-5 | Low | service-engineer | No | Services README:104-117,289-293 must describe repaired lost-reply and unbound-reservation replay behavior accurately. Include only if Step 0 user approves. |
| R11C-6 | Low observation | storage-engineer | No | StorageRows.scala:278-293,346 run-ledger CAS retry can report own applied write as conflict; downstream impact untraced. Reconcile intended payload on primary read after retried conditional failure or document fail-closed behavior. No storage repair in batch 1. |

Carried unchanged: F11B-3 configuration-test scope/vacuous assertion/error clarity, F11B-4 coverage/summary observations, 11A N3 weak assertions, Phase 9 NB1–NB10, Phase 10 F7/F8/F10–F17, earlier accepted Phase 5–8 limits. NB1/NB3/NB8 remain confirmed nonblocking. R11C-3/4/6 and carried observations are not authorized for repair now. No human decision record or self-approval is created.

Step 0 answer: user selected “Yes, include R11C-5 (Recommended)”. Batch 1 includes R11C-1/R11C-2 and the same-owner services README correction R11C-5 only. R11C-3 remains unassigned and untouched.


### Subphase 11C repair round 1 — local disposition, independent recheck pending

| ID | Owner | Local result | Independent disposition |
| --- | --- | --- | --- |
| R11C-1 | service-engineer; test-engineer HTTP case | Applied-then-retried-conflict primary reconciliation, one dispatcher, completion/stored replay/409; red reproduced then targeted/full pass | PENDING user-launched recheck |
| R11C-2 | service-engineer; test-engineer | Clean rejection followed by revision0 replay CAS recovery; two cross-instance concurrency variants and updated HTTP expectation pass | PENDING user-launched recheck |
| R11C-5 | service-engineer; user approved Step 0 inclusion | README accurately states binding recovery and remaining already-bound process-crash limits | PENDING user-launched recheck |
| R11C-3 | ORPHAN; human assigns writer | UNTOUCHED, no ownership inferred, no deletion/ignore edit | Nonblocking, future human decision |
| R11C-4/R11C-6 and carried findings | Original owners | UNTOUCHED, no closure implied | Original nonblocking/accepted/future dispositions retained |

Final local gates: services40/runtime18 targeted58passed; full1253passed/156freshreports,0failures/errors/skips. ExposedDefect0. Evidence: evidence/11c-r1/; no independent approval or human gate inferred. Stop before any further batch/phase.


### Subphase 11C repair round 1, batch 1 — external APPROVE dispositions

The user supplied the independent read-only recheck APPROVE with no blocking findings. The complete returned text, including verdict, findings, report fields and NEXT PROMPT, is appended verbatim in review.md. This records independent review, not human phase acceptance. Earlier pending-recheck sections are historical and remain unchanged.

| ID | Severity | Owner | Independent disposition / acceptance |
| --- | --- | --- | --- |
| R11C-1 | High, formerly blocking | service-engineer; test-engineer independent HTTP regression | CLOSED — independent recheck APPROVE. Applied-write/lost-reply recovery, exact binding ownership, persisted completion, stored replay without rerun and changed-body409 verified against files and retained red/green evidence. |
| R11C-2 | Medium, formerly blocking | service-engineer; test-engineer | CLOSED — independent recheck APPROVE. Clean rejection recovers through revision0 CAS; same-ID concurrent cross-instance variants bind/run once; permanent503 expectation removed. |
| R11C-5 | Low | service-engineer | CLOSED — independent recheck APPROVE. README correctly describes winning binder, ownership token, exact reconciliation and unbound replay recovery; residual wording issue separately logged as R11C-8. |
| R11C-7 | Low, nonblocking; code-derived/unexecuted | service-engineer | LOGGED ONLY, no repair authorized. QueryService.scala:57-61,215-226 with StorageRows.scala:221 and RowCodec.map:78-86: retried creation with no row returns POST404. Acceptance: fake Retried(n,Rejected("transport-retry-exhausted")) leaving no row returns503/retryable true and zero workflow calls. Pre-existing behavior, not a regression. |
| R11C-8 | Low, nonblocking; code-derived residual double fault | service-engineer, deployment gate | LOGGED ONLY, no repair authorized. QueryService.scala:197-205 and README:301-304: applied binding/lost reply followed by transient failed reconciliation read can strand bound QUEUED indefinitely under default no TTL. Acceptance: bounded reconciliation-read retry, stale-QUEUED lease/reclaim, or README wording covering transient double fault. No durable dispatcher is claimed. |
| R11C-9 | Low, nonblocking | coordinator | SATISFIED for this recording: complete returned review text appended verbatim; earlier content preserved. Going forward retain full verdict/findings/report fields rather than summarizing the returned review. No earlier record rewritten. |
| R11C-3 | Medium, nonblocking | ORPHAN — human must assign writer | UNCHANGED; separate human ownership decision pending before removal/ignore edits. No assignment inferred. |
| R11C-4 / R11C-6 | Low / Low observation | hadoop-engineer / storage-engineer | UNCHANGED; no repair authorized; R11C-6 downstream impact remains untraced. |

Carried unchanged: F11B-3, F11B-4, 11A N3, Phase 9 NB1–NB10, Phase 10 F7/F8/F10–F17 and earlier Phase 5–8 limits. Raw logs remain only in /tmp; synthetic results do not establish live DynamoDB or durable dispatch. Reviewer unread scope and guard-blocked marker inspection remain disclosed in the verbatim review.

Recording-only step: no builds/tests, production/test/build edits, new repair batch, reviewer invocation, cloud/provider call, commit/push, human-gate.md, commit.txt or approval/ratification record. Git still shows 11C and repair uncommitted on phase-11 at 2b0aee044f243f01bbb603170d09f5c507df8bb7. Next gate: user commit, then the user's own Phase 11 human-gate/commit records; do not infer acceptance or start/prepare Phase 12.

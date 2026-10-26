# Subphase 9A routed integration repairs

These are coordinator/test findings during implementation, not an independent review verdict.

| ID | Owner | Evidence and repair | Observed status |
|---|---|---|---|
| I1 | storage-engineer | target1 testcompile: local iterator shadowed inherited method; renamed sourceIterator | final target11/11 pass |
| I2 | storage-engineer | targets2/3 fixture edges used wrong supporting work and malformed topic/venue/institution namespaces; corrected source-grounded fixture IDs/authorship and added fixture validation, production guards retained | final target11/11 pass |
| I3 | test-engineer | first independent compile missing generic wildcard Rejected[?]; fixed test type | final independent22/22 pass |
| I4 | rag-engineer | schema-valid model could drop natural filters/change metric/relabel a metric as a filter; strengthened conservative coverage and required-operation/metric checks | module/independent adversarial cases pass |
| I5 | storage-engineer | exact cache-name lookup could not discover unsuffixed homonym candidates; loader now emits base aliases preserving suffix IDs | real cache-loader test and resolver tests pass |
| I6 | rag-engineer | late model/cache returns could be accepted on early branches; injected monotonic clock and post-call deadline guards | deterministic late-response tests pass |
| I7 | domain-engineer + rag-engineer, sequential own paths | candidate omitted source coauthor truncation; added defaulted optional flag and resolver propagation | final core/RAG targets pass |
| I8 | storage-engineer | researcher context used researcher ID as coauthor-edge rowKey; changed to actual selected edge/source row IDs with assertion | final storage target pass |
| I9 | test-engineer | full check1: legacy loader test expected3 cachewrites; the approved unsuffixed alias adds a fourth immutable link. Updated first/replay counts to4 and added explicit alias identity/confidence/run/source-evidence assertions, retaining exact-suffix and external-ID checks | affected target5/5passed; full recheck831/831passed |

No external review findings have been supplied for9A. No prior human decisions were rewritten.

## Subphase 9A external review findings

User-supplied external review (initial): REQUEST-CHANGES, retained verbatim in review.md
and evidence/9a-r1/external-review.txt. User instruction: "Fix all blockings for me".
B4 is therefore FIX NOW, not deferred. No additional questions for this repair round.
Only B1–B4 are routed for repair; N1–N7 remain open/deferred without implementation.

| ID | Blocking | Owner | Acceptance check | Status |
|---|---|---|---|---|
| B1 | yes | rag-engineer; test-engineer independent tests | Every recognized metric/measure/operation grounded; configured bridge default; exact explicit/uniquely mapped/default windows; total-author conversion only explicit. Hand-derived disagreement and positive cases. | LOCALLY VERIFIED — independent recheck pending |
| B2 | yes | rag-engineer; domain-engineer contract/config gap; test-engineer | Dedicated cap counts distinct canonical IDs; many rows for one identity resolve; bounded per-candidate provenance with totals/truncation; overflow returns bounded Ambiguous with total/truncation. | LOCALLY VERIFIED — independent recheck pending |
| B3 | yes | storage-engineer + rag-engineer; test-engineer | Real artifact fake distinguishes unknown window from identity absent in a stored window; absent identity context still Resolved; absent homonym still included in Ambiguous. | LOCALLY VERIFIED — independent recheck pending |
| B4 | yes, user chose fix now | storage-engineer | Successful immutable pointer snapshot verified once and indexed; repeated reads no GET/revalidation; corruption rejected first load; no measured latency claim without measurement. | LOCALLY VERIFIED — independent recheck pending |
| N1 | no | domain-engineer, future9B contract gap | Cross-check vector-mode semantic partition against item descriptive/type before EvidenceBuilder acceptance. | OPEN/DEFERRED |
| N2 | no | user + rag-engineer, before9C representative benchmarks | Confirm strict complete authoritative metadata coverage makes most real filtered rankings Unsupported; disclose limits. | OPEN/DEFERRED |
| N3 | no | domain-engineer + rag-engineer,9C | Revisit maxInputBytes shared question/prompt/request/output bounds for synthesis context. | OPEN/DEFERRED |
| N4 | no | rag-engineer, live gate | Check injected client's actual region against configured/audited region. | OPEN/DEFERRED |
| N5 | no | rag-engineer documentation/reporting | Disclose real-loader confidence None and disagreement→None; synthetic confidence tests establish no real calibration. | OPEN/DEFERRED |
| N6 | no | rag-engineer | Versioned prompt filenames currently fixed-v1; future versions require explicit loading support. | OPEN/DEFERRED |
| N7 | no | storage-engineer, later scope | Context coauthors bounded but authored/association refs only snapshot-bounded; future ref bounds need qualification. | OPEN/DEFERRED |

Full reviewer evidence, paths/lines, impacts and detailed acceptance are retained in external-review.txt.
No9B preparation, no reviewer launch, no live call or commit is authorized in repair round1.


Repair round1 local closure evidence:140targetedpassed0failed; final full check901passed0failed,
exit0,725.07s; all34source hashes unchanged. Source delta16files; exact commands/results/hashes
under evidence/9a-r1/. B1–B4 are locally verified, not independently approved. N1–N7 remain
OPEN/DEFERRED and were not repaired. No9B work, reviewer, live call or commit occurred.


## Subphase 9A repair round 1 — external APPROVE recorded (2026-10-26)

The user-supplied read-only recheck reports B1–B4 FIXED, no new blockers, and APPROVE.
Verdict/findings/report retained verbatim in review.md and evidence/9a-r1/external-recheck.txt.
This records independent code review, not a human acceptance gate or commit.

| ID | Blocking | Owner | Acceptance / next action | Status |
|---|---|---|---|---|
| B1–B4 | formerly yes | original module owners | Independently rechecked against source and retained140targeted/901full evidence | FIXED — external APPROVE |
| N8 | no | rag-engineer | Before9C benchmarks, extend natural temporal/community grammar or use supported wording; ask whether9B workflow tests require this only after commit gate | OPEN/nonblocking |
| N9 | no | coordinator | Append dated clarification of historical opening line without rewriting prior text; note appended2026-10-26 in review.md | OPEN/nonblocking — clarification appended for recheck |

N1–N7 remain open/deferred. N1 is a domain contract gap required before9B EvidenceBuilder
acceptance; discuss in9B Step0 after the user commit gate. No9B implementation or preparation
started. Current branchphase-9 HEAD remains5fee9ffc607cf802e4aaddf4a261c21f1f232fec,
with repaired9A tree uncommitted. Agents must not commit/push; await user commit SHA.


## Subphase 9B implementation findings

| ID | Owner | Finding / acceptance | Status |
|---|---|---|---|
| 9B-I1 | domain-engineer | N1 actual-item type/descriptive partition, not ID-only; semantic numeric/graph masquerading rejected | Core targeted36pass; integrated/full gates pending |
| 9B-I2 | domain-engineer + rag-engineer | Immutable item index needs full runtime content/run/window binding for precise existing evidence types; optional marker keeps frozen legacy valid | Core targeted36pass; persistence replay tests pending |
| 9B-I3 | rag-engineer | Target1 module testcompile: unqualified fixture run shadows ScalaTest.run method | Test identifier qualified; target2 compiled |
| 9B-I4 | rag-engineer | Target2 required four-hop context4234 exceeds4096; builder/workflow fail closed but required fixture must fit defaults | OPEN — compact render empty/null envelope fields, retain essential facts; two failure cases retained |
| 9B-I5 | rag-engineer; test-engineer regression | Sequential result collection must judge actual completion time, so a fast completed later stage is not falsely timed out after waiting for another stage | OPEN — completion-time-bound await repair and independent test |

Named-candidate metric/community/temporal filters are rejected as Unsupported when exact filtered semantics are unavailable; no constraint is silently dropped. N2-N9 remain carried forward, with N8 grammar deferred9C and N9 dated clarification already appended. No external9B review received.


9B local gate progress: I4 compact context repair verified module14/14 including required four-hop persisted evidence and workflow, no budget increase or essential-fact removal. First independent gate62/63; one new temporal fixture had both-present=true but missing bridge deltas, violating the existing source contract. Test owner supplies explicit hand-derived deltas and verifies source validity; production validator retained. I5 completion-time regression passed in that gate. Canonical researcher-ID union for ranking/path bundles, validated community-cross-edge provenance, bounded cleanup within the overall deadline and closed structured stage logs are being completed before final targeted/full gate.


### Subphase 9B local closure

I1-I5 and all routed integration issues are locally verified by final135targeted/1001full passes (exit0,707.18seconds). Retained evidence covers the fixture-name compile error, required-path budget repair and corrected source-invalid temporal fixture. Completion-time race, default-budget full path, explicit ranking prefix, source-bound cross-community edges, identity retention and indexed persistence all pass. No production checks weakened. Complete commands/raw hashes in evidence/9b/.

N1 is LOCALLY FIXED, awaiting external9B review. Content-bound runtime IDs and defaulted resolvedCandidates were necessary additive evidence contract gaps; domain owner only. N2-N9 remain carried forward/nonblocking, with N5 absent-confidence disclosure and N9 append-only historical clarification recorded. N8 planner file unchanged/deferred9C. No external9B review received yet, no9C work started, no human decisions rewritten.


## Subphase 9B repair round 1

User supplied REQUEST-CHANGES and explicitly instructed "fix all blocking bugs for me".
No questions for this repair round. Only B1 is blocking/routed. Full review preserved verbatim
in review.md and evidence/9b-r1/external-review.txt with SHA256. N1 externally confirmed FIXED;
N2-N9 carried forward. No O-item implementation authorized in this repair.

| ID | Blocking | Owner | Acceptance / next action | Status |
|---|---|---|---|---|
| B1 | yes | rag-engineer + test-engineer | Exact metric approximate=false unchanged with/without P90 and consistent with ranking; separate deterministic approximate P90 item bound component/window/run/method/source; atomic admission; hand-derived module/independent tests; iteration labels and default path/ranking retained | ROUTED |
| O1 | no | rag-engineer | Scope convergence/iteration qualifiers to community-derived fields before9C verification | OPEN/log only |
| O2 | no | rag-engineer | Separate request/source lineage before9C audit orPhase10 evidence exposure | OPEN/log only |
| O3 | no | rag-engineer | Restrict resolved identities to resolvedCandidates/deterministic subjects for identity checks/audit, not similarity hits | OPEN/log only |
| O4 | no | rag-engineer | Scope named semantic retrieval to resolved candidates or disclose cross-entity context | OPEN/log only |
| O5 | no | rag-engineer | Consider disclosed list prefixes/scope deduplication for realistic atomic groups in9C or11 | OPEN/log only |
| O6 | no | rag-engineer | Consider byte-bound-aware ranking prefix selection | OPEN/log only |
| O7 | no | rag-engineer |9C benchmark wording must match shipped bounded NoPathWithinLimit behavior; ExceededMaxHops adapter path unreachable | OPEN/log only |
| O8 | no | domain-engineer | Consider text=None requirement for deterministic items | OPEN/log only |
| O9 | no | rag-engineer | Preserve path-status researcher pair in rendered context | OPEN/log only |
| O10 | no | test-engineer | Future filtered ranking test limit2 discriminates filter-before-rank | OPEN/log only |

Only B1 repair, affected targeted gates and full JDK17check are required. No9C work or reviewer launch.


### Subphase 9B repair round 1 — local gate closure

B1 LOCALLY FIXED:99targeted/1004full passed,0failed; fullcheckexit0,717.84seconds.
Exact metric evidence stays approximate=false and unchanged with optionalP90; separate deterministic
component distance-estimate approximate=true retains sourcecomponent/window/run/method/refs.
Both stay atomic under existing unchanged builder. Named/ranking exact values agree, iteration
flags retained, default4hop/ranking regressions pass. Fourrepairpaths with before/afterSHA256;
all18otherreviewed9B paths and29untouchedprior9A paths match. Externalrecheckstillpending.
O1-O10 OPEN/nonblocking/logonly, notimplemented. N1externallyconfirmedfixed; N2-N9carriedforward.
No9Cwork, commits/pushes, live/provider/cloudcalls orhumangateedits. No failedrepairbuild/testattempt.


### Subphase 9B repair round 1 — external approval recorded

The user-supplied independent recheck returned APPROVE. B1 is FIXED and externally approved;
all six acceptance checks were met, with no new blockers or regressions. The full review is
preserved verbatim in review.md and evidence/9b-r1/external-recheck.txt with its SHA-256.
The supplied next prompt ends mid-sentence; its text is preserved exactly as received.

| ID | Owner | Status | Next action |
|---|---|---|---|
| B1 | rag-engineer and test-engineer | FIXED — externally approved | No remaining 9B repair work |
| R1 | rag-engineer | OPEN / nonblocking / log only | Optional P90 sampling details and source references; do not infer missing sample values |
| R2 | coordinator | OPEN / cosmetic / log only | Use normal spacing in new evidence prose; preserve recorded human decisions and reviews |
| O1–O10 | Previously assigned owners | OPEN / nonblocking / log only | Carry forward; O1–O3 need decisions before 9C verifier/audit rely on them |

N1 remains fixed; N2–N9 remain carried forward. No optional source repair was made while
recording approval. All 22 reviewed source hashes still match. The approved 9B work remains
uncommitted at HEAD f139f9c925b4925864a2c9a33734d869a1929cd2. Wait for explicit user commit
instructions or a user-provided commit before starting 9C Step 0. No 9C preparation occurred.


## Subphase 9C implementation findings

| ID | Owner | Finding and required check | Status |
|---|---|---|---|
| 9C-I1 | storage-engineer | Initial test assumed pointer smaller than an unusually tiny envelope; actual bound is configured pointer cap and no question body in the pointer | Test corrected; storage14/14 passed in integrated target1; production unchanged |
| 9C-I2 | rag-engineer | Named G1 benchmark questions exposed global one-letter name removal corrupting other request words | Word-boundary coverage removal; positive/negative planner regressions and benchmark rerun required |
| 9C-I3 | rag-engineer | Team-size scripted target was outside admitted ranking prefix | Keep literal maximum2; select a retained exact ranking row, without inventing facts or increasing budgets |
| 9C-I4 | rag-engineer | Natural compare-community phrase still rejected in independent test | OPEN: extend approved bounded grammar and retain all constraints |
| 9C-I5 | rag-engineer | Unexpected workflow exceptions should produce a terminal audit when audit storage is available | OPEN: bounded terminal failure handling and independent test |

Initial integrated target1: storage14passed, RAG14passed1failed, independent not reached.
Independent diagnostic target1:63passed1failed, only natural community phrase; verification,
synthesis, audit workflow and trust cases otherwise passed. Exact logs/hashes/commands retained
in evidence/9c. No claim of full acceptance yet. Earlier9A/9B observations remain logged.


9C gate progress: storage14/14 and RAG72/72 passed in targeted3; independent208/209,
with all new9C83 cases and15benchmarks passing. The only failure was an old9B assertion
against legacy maxInputBytes instead of the approved independent persistedBundleBytes cap;
sourceContext increased the full stored path bundle to19,227bytes while model context stayed
within4,096. Test owner updates two byte assertions to the effective cap, retaining complete
path/context checks. A CLI regex compile error from targeted2 was corrected and retained.
Final synthesis entry guards will enforce separate question/prompt caps for scripted clients too.


9C-I6 (rag-engineer; independent test-engineer): final workflow discarded ambiguity candidates while retrieval retained them. Required candidate list must survive the terminal result and CLI, without turning alternatives into resolved audit identities. Full check 1 intentionally stopped, exit 143; targeted and full gates will be rerun after repair.


## Subphase 9C — final local validation

All implementation findings 9C-I1 through 9C-I6 are locally fixed and covered by the final gates; external review remains pending. The initial pointer-size test assumption was corrected without a storage production change. Bounded grammar/name-coverage and CLI quoting issues were repaired. Team/bridge benchmark scripts select retained ranking rows while retaining literal expected values. Unexpected workflow exceptions are audited. Separate synthesis entry byte guards are enforced. Final ambiguity results preserve both homonym candidates without selecting audit identities; reason and candidates are covered by the abstention hash.

Final targeted gate: 299 passed, zero failed; actual CLI benchmark: 15/15; full JDK 17 check: 1,131 passed, zero failed. Full check 1 was intentionally stopped with exit 143 before candidate-list repairs; full check 2 passed after the frozen-source rerun. Earlier failures, exits, excerpts and raw SHA-256 bindings remain in evidence/9c.

Approved 9C handling of N3/N8/O1/O2/O3/O4/O8/O9/R1 is described in evidence/9c/coverage-and-limitations.md. N1 stays fixed. N2/N4/N5/N6/N7 and O5/O6/O7/O10 retain disclosed limits; R1's generic evidence type remains disclosed. R2 is addressed by normal spacing in final prose, with prior human decisions/reviews unchanged. No externally approved prior finding is reopened or silently claimed fully resolved.

No live/model/cloud calls, infrastructure, commits/pushes, reviewer launch, human-gate edits or Phase 10 work. User-launched 9C review is next.


## Subphase 9C review - nonblocking findings (logged only)

User-supplied external review: APPROVE, no blocking findings. Each item below is logged; not implemented. Original decisions, approved defaults and prior findings remain unchanged.

### NB1

Status: logged; not implemented
Owner: rag-engineer; test-engineer for independent tests
path:line: modules/rag/.../ClaimVerificationAgent.scala:169-174, 186-192, 245-252
Acceptance check: A claim with an unrelated, other-subject or descriptive citation on a non-SEMANTIC claim is UNSUPPORTED, or that citation is
removed and the removal recorded. Add independent tests for both shapes.

### NB2

Status: logged; not implemented
Owner: rag-engineer; test-engineer
path:line: modules/rag/.../RuntimeAnswerWorkflow.scala:129, 204-205; tests/.../IndependentRuntime9CWorkflowSpec.scala:113-116
Acceptance check: Either return Abstained(reason, audit) when verification.abstained, or record this contract as binding for Phase 10, with a test
either way.

### NB3

Status: logged; not implemented
Owner: rag-engineer
path:line: modules/rag/.../QueryPlannerAgent.scala:285
Acceptance check: Use outputBytes, plus a test with a small question cap and a valid larger planner output.

### NB4

Status: logged; not implemented
Owner: test-engineer
path:line: tests/.../IndependentRuntime9CBenchmarkSpec.scala:10-16, 53-63; RuntimeWorkflowMain.scala:224-226
Acceptance check: Assert the ranked researchers and ranks by hand (e.g. C/D/F for distinct coauthors = 3).

### NB5

Status: logged; not implemented
Owner: rag-engineer
path:line: RuntimeOfflineFixture.scala:46; SemanticContextAgent.scala:23-24
Acceptance check: Note this in the README, or add one fused-mode benchmark or workflow case.

### NB6

Status: logged; not implemented
Owner: rag-engineer (Phase 11 may absorb this)
path:line: RuntimeAnswerWorkflow.scala:160-162, 177-179
Acceptance check: Stage outcome logs with trace and run IDs, and no payloads.

### NB7

Status: logged; not implemented
Owner: rag-engineer
path:line: modules/rag/README.md:371-444
Acceptance check: Add the observed results with a pointer to the evidence.

### NB8

Status: logged; not implemented
Owner: rag-engineer
path:line: RuntimeAnswerWorkflow.scala:58, 81
Acceptance check: Make it volatile or atomic.

### NB9

Status: logged; not implemented
Owner: rag-engineer
path:line: ClaimVerificationAgent.scala:322-331
Acceptance check: Neutral separator for sets.

### NB10

Status: logged; not implemented
Owner: rag-engineer
path:line: RuntimeRetrieval.scala:153-165
Acceptance check: Disclose it, or leave the snapshot absent when it is unknown.

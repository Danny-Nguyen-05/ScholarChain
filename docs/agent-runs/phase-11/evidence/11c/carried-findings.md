# Carried context for the independent 11C reviewer

This index preserves original owners and dispositions. It does not confirm, close, reprioritize or authorize repair of a finding. Verify each lead against current files and later dispositions. Do not treat historical OPEN/pending checkpoints as final when a later review supersedes them.

## Phase 11A

- N1/N2: formatting and start-record precision lessons applied in 11B; the historical records remain unchanged. Verify the 11B disclosure/barriers rather than retroactively rewriting 11A.
- N3 (Low, test-engineer): AdversarialDataPlaneSpec.scala:114–116 uses work-key-implied disjointness and does not compare orders downstream; AdversarialBlockingReplaySpec.scala:156–161 includes redundant hash equality and an always-true assertion; the old “independent SHA256” wording overstates independence. Optional strengthening, unmodified.
- N4 (Info, unconfirmed lead; hadoop-engineer if confirmed, test-engineer for assertion update): TextNorm.scala:9–14 and HadoopPrepSpec.scala:59 preserve title markup; DerivedRecords.scala:342–345 uses that normalized title in title-year blocks while ER normalization strips markup (ER README:341–342). Check a same-title/same-year cross-source pair with and without inline markup for a missed candidate. No reproduction or repair has run.
- N5: historical scan-level reading, unknown model revision, temporary raw logs, synthetic fixtures and earlier limits retained. See review.md for the verbatim external review.

## Phase 11B external review input (verbatim existing routing-context section)

### Subphase 11B external review — nonblocking, logged only

User-supplied external verdict received 2026-10-28: APPROVE, no blocking findings. The designated verdict is retained verbatim in review.md. Earlier pending-review statements are historical. No finding below was repaired, routed for implementation or independently reproduced in this recording step.

| ID | Severity | Owner | Evidence and acceptance check | Disposition |
| --- | --- | --- | --- | --- |
| F11B-1 | Medium | service-engineer; test-engineer for a reproduction if confirmed in 11C | Code-reading lead at modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala:152-156, :178-190, :114 and modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/DynamoStorage.scala:137. A body-binding update that applies its write but loses the reply can return Retried(1, Rejected("conditional-conflict")); submit may return 503 without scheduling, while same-key replay observes a bound QUEUED row and returns 202 indefinitely until TTL. N04 covers only a clean rejection. Acceptance: a fake update that applies the write then returns that retried rejection must reconcile/schedule exactly once; replay must neither strand the job nor execute it twice. | Nonblocking 11C review input; unexecuted and unconfirmed; no repair authorized now. |
| F11B-2 | Low | test-engineer | AdversarialRuntimeHttpSpec.scala:138-140 requires replay after a failed bind to return 503 again, although that response is retryable and the reservation cannot currently progress. Acceptance: assert no workflow/model call plus a non-2xx or documented status, or explicitly record the current-behavior expectation; reconsider if reservation liveness is repaired. | Nonblocking; logged only, no repair authorized now. |
| F11B-3 | Low | test-engineer for name/scope; service-engineer if error clarity changes | AdversarialRuntimeBoundarySpec.scala:77-98 calls only ServiceConfig.fromEnvironment for two required credential omissions; its name says "before composition" without exercising startup. Generic error does not name the missing key. Acceptance: align name with actual scope or exercise startup composition, and record the error-clarity decision. Any variable name in an error must omit its value. | Nonblocking; logged only, no repair authorized now. |
| F11B-4 | Info | coordinator for coverage wording; test-engineer for assertions | Category 16 maps E11 audit-persistence failure beyond the three named faults; those faults are independently covered by N10/N04/N17. AdversarialRuntimeHttpSpec.scala:76 summary.contains("3") is weak but backed by exact claim-value assertions at :71-75. Acceptance: preserve exact assertions and honest coverage mapping; no action required. | Nonblocking; logged only, no repair required. |

Carried unchanged: 11A N3/N4/N5; temporary raw-log durability; unavailable exact model revision; Phase 9 NB1–NB10; Phase 10 F7/F8/F10–F17; earlier Phase 5–10 limits. The combined exposed-test inventory remains zero: the newly reported F11B-1 lead has no executed reproduction yet. No production, build or test file changed, no human decision record was written, and no 11C work was started. Next gate: user commit of approved 11B, then 11C Step 0.


## Phase 9C NB1–NB10 (verbatim review extract)

Source: docs/agent-runs/phase-09/review.md. Earlier 9A/9B observations and repairs remain in that phase's review.md and repairs.md; this extract does not replace those registers.

#: NB1
Severity: Medium
path:line: modules/rag/.../ClaimVerificationAgent.scala:169-174, 186-192, 245-252
Evidence: The verifier only checks that each cited evidence ID exists in the bundle. Support comes from the filtered subset that matches subject,
window and trust, but the accepted claim keeps all its citations. So a METRIC claim citing [metric(A), semantic(A)] or [metric(A),  metric(B)]
passes as VERIFIED and still lists the unrelated or descriptive ID.
Impact: A verified number can point at semantic text (possibly containing injected instructions) or at another researcher's evidence. This weakens
the deterministic/semantic separation in the final answer and in Phase 10 GET /v1/evidence/{id}.
Owner: rag-engineer; test-engineer for independent tests
Acceptance check: A claim with an unrelated, other-subject or descriptive citation on a non-SEMANTIC claim is UNSUPPORTED, or that citation is
removed and the removal recorded. Add independent tests for both shapes.
────────────────────────────────────────
#: NB2
Severity: Medium
path:line: modules/rag/.../RuntimeAnswerWorkflow.scala:129, 204-205; tests/.../IndependentRuntime9CWorkflowSpec.scala:113-116
Evidence: When verification ends with no accepted claim (verifier rejected everything, synthesis abstained or synthesis was malformed), the workflow
returns AnswerWorkflowResult.Completed with audit.outcome == "ABSTAINED". The Abstained result type is never used in those cases, and the reason
(e.g. synthesis-invalid-output) exists only in the audit. The independent test locks in this behavior.
Impact: A Phase 10 consumer matching on Completed could present an abstention as an answer.
Owner: rag-engineer; test-engineer
Acceptance check: Either return Abstained(reason, audit) when verification.abstained, or record this contract as binding for Phase 10, with a test
either way.
────────────────────────────────────────
#: NB3
Severity: Low
path:line: modules/rag/.../QueryPlannerAgent.scala:285
Evidence: The planner's model-output JSON is limited by questionBytes, not outputBytes.
Impact: This mixes two byte limits that 9C was meant to separate (N3). If someone sets a small question cap, every valid planner output gets rejected
and the planner silently falls back to rules.
Owner: rag-engineer
Acceptance check: Use outputBytes, plus a test with a small question cap and a valid larger planner output.
────────────────────────────────────────
#: NB4
Severity: Low
path:line: tests/.../IndependentRuntime9CBenchmarkSpec.scala:10-16, 53-63; RuntimeWorkflowMain.scala:224-226
Evidence: The ranking, team and bridge cases only check that some verified row has the expected value. The scripted model proposes that same value
for every retained row.
Impact: Rank order and which researcher is on top are not asserted end to end.
Owner: test-engineer
Acceptance check: Assert the ranked researchers and ranks by hand (e.g. C/D/F for distinct coauthors = 3).
────────────────────────────────────────
#: NB5
Severity: Low
path:line: RuntimeOfflineFixture.scala:46; SemanticContextAgent.scala:23-24
Evidence: The benchmark runs in graph mode, not the default fused. In fused mode, any query naming more than one researcher always gets a
non-essential semantic Unsupported, so it reports partial-retrieval.
Impact: The default retrieval mode is not covered by the benchmark.
Owner: rag-engineer
Acceptance check: Note this in the README, or add one fused-mode benchmark or workflow case.
────────────────────────────────────────
#: NB6
Severity: Low
path:line: RuntimeAnswerWorkflow.scala:160-162, 177-179
Evidence: The synthesis, verification and audit stages write no structured logs, and traceId is just the queryId.
Impact: Plan §6.8 asks for structured logs with trace/run IDs.
Owner: rag-engineer (Phase 11 may absorb this)
Acceptance check: Stage outcome logs with trace and run IDs, and no payloads.
────────────────────────────────────────
#: NB7
Severity: Low
path:line: modules/rag/README.md:371-444
Evidence: Task 7 asks the README to record benchmark results; the 9C section describes the cases but never states the observed 15/15.
Impact: Documentation is incomplete.
Owner: rag-engineer
Acceptance check: Add the observed results with a pointer to the evidence.
────────────────────────────────────────
#: NB8
Severity: Low
path:line: RuntimeAnswerWorkflow.scala:58, 81
Evidence: The plan variable is written from the stage thread without synchronization.
Impact: After a retrieval timeout the audit may miss a plan that did exist.
Owner: rag-engineer
Acceptance check: Make it volatile or atomic.
────────────────────────────────────────
#: NB9
Severity: Low
path:line: ClaimVerificationAgent.scala:322-331
Evidence: Researchers that were not resolved by name show up as raw IDs in the answer text, and unordered coauthorIds are joined with "→".
Impact: Cosmetic and misleading in the final text.
Owner: rag-engineer
Acceptance check: Neutral separator for sets.
────────────────────────────────────────
#: NB10
Severity: Low
path:line: RuntimeRetrieval.scala:153-165
Evidence: When an item has no stored source context, datasetSnapshot falls back to the run ID (for semantic items, the embedding document's run ID).
Impact: That field holds a value of a different kind; the README only partly discloses this.
Owner: rag-engineer
Acceptance check: Disclose it, or leave the snapshot absent when it is unknown.


## Phase 10 final carried register (verbatim extract)

Source: docs/agent-runs/phase-10/repairs.md. F1–F6/F9 and O1/O2 closures remain governed by the external reviews; do not reopen or close them without current evidence.

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


## Earlier registers and disclosed limits

- Phase 4: prefix replay may have large-corpus I/O cost; use phase-04 module/report evidence.
- Phase 5: matching/scaling/IO and identity-evaluation limits remain in phase-05/{review,repairs,owner-report,test-report}.md. Labels are not blind calibrated truth: eight uncertain labels and 22 externally assisted cases without retained external evidence. Do not infer population accuracy or recall.
- Phase 6: phase-06/{review,repairs,owner-report,test-report}.md covers LPA nonconvergence, approximate P90/partition dependence, bounded buffering, metadata reuse and runtime/Scala alignment. EMR execution is deferred to Phase 15. Historical yearless-edge/consumer gates must be checked against later Phase 7 dispositions. No new closure inferred.
- Phase 7: phase-07/{review,repairs,owner-report,test-report}.md governs N4/N5/N7/N9–N16 and 7C-L1/L2/L3; N6 was externally closed. 7C-M1 has an offline repair and final local validation; use the later review/disposition evidence to establish closure, not its older OPEN row. Actual live cleanup, SDK/IAM compatibility and cost remain unverified (Phase 14C). Do not execute cleanup.
- Phase 8: phase-08/{review,repairs,owner-report,test-report}.md governs N2–N8/R2–R3/N10–N19 and accepted closures B1/N9/F1/N1/R1. Live rendering/model/vector/retrieval cost remains Phase 14C scope; authored smoke commands are not executed evidence.
- Phase 9: all earlier N/O/R observations remain governed by phase-09/repairs.md and subsequent review.md dispositions, in addition to NB1–NB10 above.
- Codex/Cursor-led orchestration remains a disclosed deviation from the course Claude workflow; required .claude artifacts are not native Codex enforcement. No instructor acceptance or human constitutional ratification is inferred from file existence.

Full prior-report paths and hashes are indexed in test-evidence.json. The inherited reading scope is active-disposition scanning, not a fresh line-by-line independent review. Current whole-repository review remains unrun. Phase 12+ infrastructure, Phase 14 live gates, Phase 15 bounded EMR/deployment and the user's final human gate are future scope; do not turn future live evidence into an offline success claim.

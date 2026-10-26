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

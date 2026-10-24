# Phase 8 routed findings

## Subphase 8A

User-approved prerequisite from Phase7: 7C-L2 runtime fence character/interpolation masking gaps routed to test-engineer before rag runtime source. Four additional regression cases; focused suite passed8/8 before production source introduction. Independent review remains pending; no prior Phase7 human record edited.

No external Phase8 verdict has been supplied. This file records implementation-time repairs and required later review, not independent approval.

Integration corrections routed to original owners during8A (not external reviewer findings):
- Storage guarded registry match: explicit fallback removes observed compile warning.
- Storage full-provenance/canonical JSON pointer and same-text first-provenance replay; aggregate SQS byte bound.
- Storage ambiguous vector success/completion-marker recovery and safe structured summary logging.
- Core/RAG codepoint excerpt consistency and exact emoji boundary tests.
- RAG client-wide concurrency semaphore and cross-call regression.
Final affected gates: core9/9, storage12/12, RAG14/14, independent23/23, all exit0. Fullcheck pending at this checkpoint. All prior human records remain unchanged.

Final full JDK17 gate passed718/718 exit0; no additional repair required. All implementation-time corrections remain subject to the user-launched8A review.

## Subphase 8A — repair round 1

User supplied external REQUEST-CHANGES review on 2026-10-24, retained verbatim in review.md. User request: "fix all blockings bugs and the N1 for me". Preserve the current uncommitted 8A implementation. No 8B, reviewer launch, cloud/provider call, commits/pushes or human-decision edits.

Step 0 question: stable-slot key (recommended) or content-addressed key with disclosure? User answer: "Use recommended stable-slot key". Approved recommendation excludes source runId so a rerun cannot bypass conflicts. Content-hashed documentId remains metadata.

| Finding | Scope/status at routing | Owner | Acceptance evidence required |
|---|---|---|---|
| F1 high, blocking: content-derived vector key bypasses conflicts for rendered text | REQUIRED repair | domain-engineer, rag-engineer, storage-engineer, test-engineer | Real renderer -> item -> runner: same slot changed text same key, conflict before any embed or new text/vector write except rejection report; unchanged skip; new model new key; chunks distinct. Additive slot wire/validation and accurate docs. |
| N1 medium: fromSummary drops filters and wraps original summary text | REQUIRED by user's explicit addition | rag-engineer; independent test-engineer | Supplied allowed identity fields preserved/validated; no/blank abstract preserves exact source summary bytes/refs/qualifications; explicit permitted abstract composition documented/tested. |
| N2 low: HTTP408/permanent and no jitter | OPEN/nonblocking, deferred | rag-engineer | Not in repair scope. |
| N3 low: serial runner embedding throughput | OPEN/nonblocking, deferred | storage-engineer | Not in repair scope. |
| N4 low: injected region and chunk/input limit alignment | OPEN/nonblocking, deferred | rag-engineer | Not in repair scope. |
| N5 low: newline field formatting | OPEN/nonblocking, deferred | rag-engineer | Not in repair scope. |
| N6 low: poison message rejects entire receive batch | OPEN/nonblocking, deferred | storage-engineer | Not in repair scope. |
| N7 info: bucket selection delegated to caller | OPEN/nonblocking, deferred | rag-engineer | Not in repair scope. |
| N8 info: original agent Markdown table interrupted | OPEN/nonblocking, deferred | coordinator | Original evidence left intact; new round gets a separate well-formed record. |

No findings are closed by implementation-agent assertion. Affected/full gate and user-launched recheck required.

Repair-round-1 local disposition: F1 and N1 implemented and locally verified, NOT independently closed. Affected11/13/18/29 and full731/731 exit0;303 frozen files unchanged. N2-N8 remain OPEN/nonblocking/deferred. See evidence/8a-r1/final-check.json, final-check-excerpt.txt, final-audit.json, repair-files.json and acceptance-matrix.md. User-launched recheck remains next gate.

### Independent recheck dispositions

The user supplied an external **APPROVE for 8A repair round 1**, retained verbatim in review.md under "Repair round 1 recheck — user-supplied external review". This supersedes the pending-independent-recheck status above; prior checkpoints remain historical evidence. Approval is not human acceptance or instructor approval.

| Finding | Independent disposition | Owner / remaining gate |
|---|---|---|
| F1: text-derived key bypassed real-renderer conflicts | FIXED, independently verified | domain/rag/storage/test owners; no further 8A repair required |
| N1: summary filters/exact text | FIXED, independently verified | rag/test owners; no further 8A repair required |
| N2–N8 | OPEN, nonblocking, deferred | Original assigned owners; unchanged |
| R1 medium: changed chunk count leaves stale/mixed groups | OPEN, nonblocking for 8A; resolve or disclose with behavior test before any 8C live ingestion | storage/rag/test owners; domain if contract needed. Ask at 8B Step 0 whether to implement group binding before local CLI runs or record a tested limitation. |
| R2 low: unchanged text/model skips metadata-only changes and keeps first filter values | OPEN, nonblocking, deferred | storage-engineer; disclosure or metadata-binding decision later |
| R3 low: filterable metadata budget checked only after embedding | OPEN, nonblocking, deferred | storage-engineer; pre-embedding budget check relevant before live ingestion |

No R1–R3 or N2–N8 repair is authorized by this recheck prompt. No implementation/test changes or new tests were run for this evidence-only recording. Next gate is the user's commit confirmation for the approved 8A + repair tree; 8B has not started. Agents do not stage, commit or push.

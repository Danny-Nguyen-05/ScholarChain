# Phase 8 work orders

## Subphase 8A

User request: “yeh since I don't have aws account yet, so if you need just tell meok. now let start phase 8a”

Source plan: /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase8.md
Snapshot: evidence/8a/phase8-plan.md

Approved Step 0 answers: all recommended defaults. Region closest to Chicago: us-east-2 (Ohio). Bedrock Titan Text Embeddings V2 via injected SDK client, model ID configured; provisional 256 dimensions/cosine; all five document types; permitted abstracts when available with deterministic paper-summary fallback and recorded selection; manifest runner plus SQS port/adapter; scoped Phase 7 7C-L2 test prerequisite repair before runtime source is introduced. User has no AWS account: no credentials, AWS setup or live/provider calls in 8A.

Approved clarifications: shared embedding interface in core to avoid storage/rag dependency cycle; Bedrock implementation in rag; identical fresh-state counters and zero additional writes on persistent replay; dollar cap is not a billing guarantee; correct plan paths in review handoff. Preserve Phase 6/7 qualifications and accepted deferrals.

No questions remain for 8A. Only 8A is authorized; do not author 8B CLI, five-query smoke suite, live command or approval template yet. Module owner tests and independent 8A interface tests are required. No reviewer, commits, pushes, AWS/provider calls or human decision edits.

Preflight: clean main at 8503e1715cbcaf043fd68213c5b08731e9de9ba7. Branch creation requested via native sandbox approval after initial permission failure.

Delegated work orders and interface handoffs are retained in evidence/8a/work-orders.md; native IDs/territories in evidence/8a/agents.md.

Exact Step 0 answer: “all recommended, also for the region use the one that is closest to chicago.”

## Subphase 8A — repair round 1

2026-10-24: user supplied independent REQUEST-CHANGES review (retained verbatim in review.md) and its repair-round work order, then explicitly requested: "fix all blockings bugs and the N1 for me". Only F1 and N1 are repair scope; N2-N8 remain nonblocking/deferred. Existing uncommitted changes are expressly retained.

The required Step 0 choice was asked and answered: "Use recommended stable-slot key". Chosen stable slot includes documentType/entityId/windowId/templateVersion/chunkPolicyVersion/chunkOrdinal/model tag and excludes source runId/text/content documentId. Content documentId stays metadata; existing StableIds formulas unchanged. No additional questions remain. All original region/model/no-account/local-only decisions persist.

Required gates: affected core/storage/RAG/independent embedding+runtime fence tests, then full JDK17 sbt check. Raw full log outside repo; SHA/size, line-numbered excerpt and counts retained under evidence/8a-r1/. End with complete recheck prompt and stop; no 8B or reviewer launch.

## User-authorized 8A commit and push

After supplying independent APPROVE for repair round 1, the user instructed: "Now I want you to commit and push it." This explicitly supersedes the earlier agent commit/push prohibition for committing the approved 8A implementation, repair and review records on phase-8 and pushing that branch to origin. It does not authorize 8B, a merge, human phase acceptance, cloud actions or repairs of deferred findings. Prior prohibition/commit-gate records remain historical checkpoints.

Pre-commit verification: all 303 source/build/test/doc contents match the retained 731-test full-gate snapshot; no code changes since that gate. Only phase-08 evidence changed afterward. Tests are not rerun for this commit-only operation.

Staged pre-commit check: source/build/test whitespace check exits 0. The whole-tree check reports 14 trailing-space notices solely in retained sbt .txt output/excerpts; those reviewed evidence bytes are intentionally preserved. No source formatting defect was reported.

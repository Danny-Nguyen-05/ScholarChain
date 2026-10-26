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

## Subphase 8B

User request: “All right, let's start Phase 8B.” Base/HEAD: 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e on phase-8, clean and pushed before work. The prior 8A external APPROVE is already retained verbatim; no duplicate review appended.

Step 0: asked whether to repair R1 chunk-group consistency before local CLI runs or document/test it as a limitation. User answer: “Repair chunk-group consistency now (recommended)”. No other open 8B decisions remain; approved Phase 8 decisions persist. N2–N8 and R2–R3 stay deferred.

Scope: R1 complete-group preflight binding; local fake CLI over completed Phase 6 G1 and bounded real export; five fixed-neighbor smoke queries and pointer/hash round trip; independent failure/dedup/replay matrix; authored but unexecuted bounded live command, disabled approval template and cleanup instructions; affected and full JDK17 gates. Only 8B; no 8C execution, reviewer, cloud/provider calls, commits/pushes, or human-decision edits. Original plan source and byte-identical snapshot are recorded in evidence/8b/preflight.json.

## Subphase 8B — repair round 1

User supplied the independent REQUEST-CHANGES review and requested: “Fix our locking bug and the N9 bug for me.” Interpreted in the supplied review context as blocking B1 plus N9. No questions for this repair round. N9a/b implementation and tests are authorized; N9c is authored as a guarded future query/latency command only, never executed.

B1: make genuine temporary G1 → CLI first/replay/fresh and source selection/rejection part of sbt check, plus exact fifth-type node-rendering unit assertions. N9: supported render-only real-model manifest; full live report fields; authored query smoke command. Separate test/RAG work orders and native IDs retained under evidence/8b-r1/. No other nonblocking repairs,8C execution, reviewer, cloud/provider calls, commits/pushes, secret reads or human-decision edits. All approved decisions persist. Required affected targets then full JDK17 check with outside-repo raw log, hashes, size, counts, excerpt and frozen audit.

## Record approved 8B recheck and prepare user commit gate

User supplied APPROVE for8B repair round1 and instructed: “don't need to fix non-blockings”. No questions for this step. Record the external verdict verbatim, independently close B1/N9, preserve F1/N1/R1 closure and all deferred findings including N15–N19. Verify source/frozen hashes and exact proposed commit inventory without builds or implementation edits. Propose a commit message and wait for explicit user commit authorization. No staging, commit/push, reviewer, source edits, temporary cleanup, live commands, human-decision edits or8C. This does not extend the earlier8A-only commit/push authorization.

## User-authorized 8B commit and push

After the independent APPROVE and exact commit proposal, the user instructed: “All right, now I want you to commit and push the change for me.” This explicitly authorizes staging and committing the proposed8B implementation, repair, review and coordinator evidence on phase-8, then pushing phase-8 to origin. It supersedes the earlier no-agent-commit/push restriction for this action only; historical pending-gate records remain checkpoints. It does not authorize8C, a merge, nonblocking repairs, cloud calls, or human/instructor acceptance. No human-owned decision record is edited.

Pre-commit verification: exact proposed144paths (20tracked+124untracked),35source hashes and346frozen contents unchanged from the passing766-test gate. Credential-pattern/path checks found no matches or runtime/credential files. No tests rerun for this commit-only operation; only this coordinator authorization note changed after verification.

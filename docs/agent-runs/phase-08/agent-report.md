<!-- Course-named copy of owner-report.md in this folder, added in Phase 17 (package 17D, docs/agent-runs/phase-17/prompt.md). The text below this note is identical to owner-report.md, which is unchanged. -->

# Phase 8 owner report

## Subphase 8A

STATUS: COMPLETE for local Subphase 8A implementation and deterministic gates. User-launched independent review remains pending.

OWNER: Coordinator /root assembling domain, build, storage, RAG and independent-test owner reports. Native IDs and exclusive paths are in evidence/8a/agents.md; separate delegated work orders are in work-orders.md.

WORK ORDER: Implement 8A only from the retained phase8-plan.md and approved prompt.md. User accepted every recommended default and the nearest Chicago region, us-east-2. User has no AWS account. No questions remained.

FILES CREATED: Additive core contracts and four wire snapshots/tests; five-type RAG renderer/chunker, fake and injected Bedrock adapter, verified semantic context/tests; storage manifest runner and fake/SQS queue adapter/tests; three independent test specs; phase08 evidence. Exact final inventory is in evidence/8a/files.json.

FILES MODIFIED: build.sbt; project/Dependencies.scala; core/storage READMEs; storage fake exports; runtime-boundary heuristic and test. No human decisions, Terraform, upstream datasets, source ID formulas or unrelated Phase7 findings changed.

COMMANDS RUN: evidence/8a/commands.md records exact commands/environment/exits. All sbt commands use JDK17. Branch creation and initial sbt startup were blocked by sandbox writes, then native approved retries succeeded; failures retained. Owners requested formatting; coordinator executed their format/test commands without authoring production code.

TEST RESULTS: Final affected core9/9, storage12/12, RAG14/14, independent23/23, all exit0. Fresh full sbt check passed 718 tests / 0 failures, exit 0 (core 153, Hadoop 64, entity-resolution 39, Spark 38, storage 44, RAG 14, independent 358, build verification 8), real 683.81 seconds. Java 17.0.20.1, sbt 1.10.7. The injected format-stage failure is the expected passing build self-test. Earlier prerequisite8/8 at0 runtime roots preceded RAG implementation; later runtime fence scanned3 sources. Structured results: affected-results.json.

VALIDATION RESULTS: Shared core embedding port avoids a dependency cycle. Keys bind chunk/profile identity, window, model ID/version/dimension. Deterministic rendering/chunk policies preserve supplied facts and refs; paper fallback is explicit. Injected Bedrock requests have bounded concurrency/retries and typed failures. Canonical ordinary-S3 JSON pointers/hash verification, completed hash/model skips, text conflicts and prepared-vector recovery are tested. SQS uses configured request/message/batch bounds and stubbed requests; structured summaries omit text.

ASSUMPTIONS: Producer/abstract permission refs are resolved by the later export composition. Source document run identity differs from fresh ingestion execution IDs. Live SDK composition must select the configured region, disable SDK transport retries, and select the pointer's ordinary-S3 bucket. Planned TitanV2/256/cosine remains provisional before immutable index provisioning.

RISKS: Real model quality, account permissions, live compatibility, actual corpus count, cost and throughput remain unverified. UTF8byte input screening is conservative, not an exact tokenizer. The source runtime fence is heuristic, not IAM proof. Completed skips retain original provenance and do not detect external vector deletion; incomplete pointer changes reject. Checkpoints are not a distributed transaction; orphan objects can remain after races/failure. SQS supports standard queues, approximate backlog and at-least-once delivery; Terraform owns DLQ/redrive. Physical writes and checkpoint-failure rejection counters may overlap, as documented.

MANUAL ACTION REQUIRED: User launches read-only reviewer, then commits approved 8A. AWS setup is not required for8A/8B. No agent commit/push/reviewer/live/provider operation or human decision edit occurred. Optional OpenAI provider, OpenSearch, extra indexes/services/CI are omitted. Five-query retrieval smoke, actual Phase6 local ingestion CLI and authored8C command/approval template remain8B; all live execution remains8C after deployment/human gate.

BLOCKED-ON OWNER: None for implementation; external reviewer/human own acceptance.

BLOCKED-ON EVIDENCE: None for local 8A completion. External verdict absent; live gates deferred.

NEXT GATE: User-launched read-only 8A review, then human commit if approved. Stop at 8A; no 8B without the next prompt.

Carry-forward live prerequisite: Phase7 7C-L3 requires runId/textHash to remain filterable in future vector indexes; storage/infra owners must preserve that in provisioning. Existing Phase6 convergence/approximation and other accepted Phase7 deferrals remain unchanged.

Final audit: all 302 frozen source/build/test/documentation hashes and mtimes unchanged during full check; tracked diff and new-source whitespace checks pass. Original plan matches retained snapshot. No protected control/human-decision/upstream data path modified. Generated test marker exists. Every launched build finished; all specialist work is complete. Branch phase-8, base and current HEAD8503e1715cbcaf043fd68213c5b08731e9de9ba7; no staging/commit/push.

Full evidence: evidence/8a/final-check.json, final-check-excerpt.txt, final-audit.json, affected-results.json and commands.md. Full raw log remains /tmp/phase8a-final-check-1.txt (1,379,298 bytes, SHA2564d4a5e7a280b7ba62eb98693294e9a572f91de19d21797105fc4c8dbd35ea13c); retained excerpt includes all sbt test/progress/error lines with original line numbers and omits repeated Hadoop/Spark warnings. The raw temp file is not a portable repository artifact. The independent reviewer prompt is retained at evidence/8a/reviewer-prompt.md.

## Subphase 8A — repair round 1

STATUS: COMPLETE implementation, affected and full deterministic gates; independent recheck pending.

OWNER: Coordinator /root assembling domain-engineer, rag-engineer, storage-engineer and test-engineer reports; exclusive territories and separate work orders in evidence/8a-r1/agents.md and work-orders.md.

WORK ORDER: User-supplied external REQUEST-CHANGES review recorded verbatim in review.md. Repair F1 and explicit user addition N1 only. User answered Step 0: "Use recommended stable-slot key", excluding source runId as recommended. Preserve all other approved local-only decisions and existing uncommitted 8A. No questions remain.

FILES CREATED: IndependentEmbeddingSlotRepairSpec.scala; evidence/8a-r1/**.

FILES MODIFIED: Seventeen implementation/test/doc paths in repair-files.json (sixteen modified, one new). Domain core contracts/wire fixtures/tests/README; RAG renderer/context/tests/README; storage metadata composition/tests/README; independent contract/storage tests. Parent phase08 prompt/review/repairs/reports appended. Existing initial evidence and human decisions retained.

COMMANDS RUN: Exact JDK17 commands in evidence/8a-r1/commands.md. Preflight phase-8, base/current HEAD8503e1715cbcaf043fd68213c5b08731e9de9ba7; original uncommitted tree expressly retained. Owners requested formatting and coordinator ran shared gates; coordinator authored no specialist production code. No failed affected attempts.

TEST RESULTS: targeted-1 exit0 core11/11 and storage13/13; targeted-2 exit0 RAG18/18 and independent29/29. Fresh full sbt check passed 731 tests / 0 failures, exit 0, real 703.88 seconds; module counts core155/Hadoop64/ER39/Spark38/storage45/RAG18/independent364/build8. Source snapshot303 files frozen for gate.

VALIDATION RESULTS: Seven UTF8-length-framed slot fields type/entity/window/template/policy/ordinal/model; text/content ID/source run excluded. Renderer emits deterministic policy and actual ordinal, content ID retained metadata, context verifies slots. Real renderer->item->runner acceptance proves changed field gives changed genuine document ID but same key, conflict before extra embed/text/vector writes except one rejection-report object; unchanged skip, new model and distinct chunks. fromSummary accepts/preserves validated caller filters; no/blank abstract exact source bytes without generated heading, explicit paper abstract composes exact summary+LF+abstract with source/permission refs.

ASSUMPTIONS: Source/permission identities remain supplied from actual producer records in future composition; tests synthetic. Slot policy binds algorithm/maxcharacters/overlap/maxchunks; template/policy/model changes intentionally create distinct namespaces, source run does not. New slot fields decode empty/-1 defaults but validation rejects until supplied; regenerate pre-repair local work records before future ingestion. No live migration needed or attempted.

RISKS: Independent recheck pending; N2-N8 unchanged/deferred (including original evidence table N8). Live service compatibility, real quality, corpus count/cost/throughput and prior accepted limitations remain unverified. All 303 frozen hashes/mtimes unchanged during full gate; whitespace checks pass.

MANUAL ACTION REQUIRED: User launches read-only recheck and commits only after approval; complete prompt retained under evidence/8a-r1/. No AWS account/setup required; no AWS/provider calls, reviewer, 8B, commits/pushes or human-decision edits.

BLOCKED-ON OWNER: None for authored repair; external reviewer/human own closure.

BLOCKED-ON EVIDENCE: None for local repair validation; independent recheck absent.

NEXT GATE: User-launched 8A repair-round-1 recheck, then human commit if approved. Implementation stopped; no 8B until next prompt.

Final evidence: evidence/8a-r1/final-check.json, final-check-excerpt.txt, final-audit.json, repair-files.json and commands.md. Expected injected checkProbeInjectFailure self-test passed; no live suite ran. All specialist work and build sessions finished. Raw log /tmp/phase8a-r1-final-check-1.txt, 1378030 bytes, SHA256 ff4baf2ed391f587d1d3cd6a6b62b7bda652943fa353874f0c8182a487104a0b; retained line-numbered excerpt is portable evidence, raw temp file is not.

## Subphase 8B

STATUS: COMPLETE for implementation and local validation; independent review pending.
OWNER: /root coordinator; domain, storage, RAG, test and build owners recorded in evidence/8b/agents.md.
WORK ORDER: User requested Phase 8B and chose “Repair chunk-group consistency now (recommended)”. Base and current HEAD 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e, branch phase-8. Only 8B authorized.
FILES CREATED: 15 source/test/fixture files, plus coordinator evidence under evidence/8b/. Exact paths and hashes: evidence/8b/source-files.json; complete tracked/untracked inventory: evidence/8b/files.json.
FILES MODIFIED: 15 existing source/build/module-documentation files, plus this report, test-report.md, prompt.md and repairs.md. No human-owned decisions edited. Exact inventory retained.
COMMANDS RUN: Required JDK17 environment and every command/failed attempt in evidence/8b/commands.md. Core target exit0; post-split storage target exit0; RAG/independent targets exit0; actual G1 producer and local G1/real acceptance exit0; direct forked CLI replay exit0. Full `/usr/bin/time -p sbt -batch check > /tmp/phase8b-final-check-1.txt 2>&1` exit0.
TEST RESULTS: Core embedding13/13; storage embedding/group19/19; RAG25/25; independent embedding/runtime fence39/39. Full756 passed,0 failed: core157, Hadoop64, ER39, Spark38, storage51, RAG25, independent374, build8. Full wall time678.84s; expected checkProbeInjectFailure is the passing build failure-path test.
VALIDATION RESULTS: R1 complete-group binding rejects changed whole text/count before payload/embedding writes; real-renderer shrink/grow and invalid membership covered. G1 producer checks10 researchers/9 canonical works/18 literal windowed edges/28 tables. G1 CLI12 written→12 unchanged/0 calls; real CLI16 written→16 unchanged/0 calls, covering all five types. Fresh counters and manifest hashes match. Every12/16 persisted text pointer/hash and qualification hash verifies. Six fixed lexical retrieval neighbors pass. Original runtime fence unchanged,5 roots/20 inspected/no findings. All254 frozen files and30 changed/new source hashes match after full gate. Live command/templates/cleanup authored but unexecuted; guard tests never construct clients.
ASSUMPTIONS: Prior Phase8 decisions persist: us-east-2, configured TitanV2/version, provisional256/cosine, five types, permitted abstract or recorded fallback, manifest+SQS, shared core client and stable slot excluding source run. User has no AWS account. G1 is explicitly synthetic direct fixture input, not an executed Hadoop/ER acquisition. The retained real export is unchanged; its convenience-slice, LPA non-convergence and approximation qualifications remain attached.
RISKS: Independent review pending. N2–N8/R2–R3 remain nonblocking/deferred; R1 is locally verified, not independently closed. Group consistency is a preflight guard, not atomic vector transactions. Old per-item state without group markers fails closed. Fake snapshots are single-writer and bounded64MiB. Selected source tables are fully checked; unrelated table bodies are not revalidated. Live compatibility, Titan quality, corpus count, latency, cost and object cleanup remain unverified. Assumed dollar bounds are not billing guarantees. Optional providers/OpenSearch/extra indexes/services/CI omitted.
MANUAL ACTION REQUIRED: User launches the supplied read-only reviewer prompt. Commit/push only after review and separate user instruction. Any future8C requires Phase14 deployment, AWS account and human-written approval/caps; do not execute it now.
BLOCKED-ON OWNER: None for completed8B implementation.
BLOCKED-ON EVIDENCE: None for local8B gates; independent review and future live8C gates remain open.
NEXT GATE: User-launched independent8B review. No reviewer launched,8B commit/push, live/provider call or next-subphase work occurred.

## Subphase 8B — repair round 1

STATUS: COMPLETE for B1/N9 implementation and local gates; independent recheck pending.
OWNER: /root coordinator; /root/rag_engineer and /root/test_engineer own assigned paths.
WORK ORDER: User supplied independent REQUEST-CHANGES and requested “Fix our locking bug and the N9 bug for me.” Interpreted as blocking B1 plus N9. No questions for this repair round. Preserve the uncommitted8B tree, prior decisions and all other deferrals; no8C execution.
FILES CREATED: Five new implementation/test files and repair evidence under evidence/8b-r1/. Exact repair delta8paths/before-after hashes: repair-files.json; cumulative35source paths: source-files.json; complete current tracked/untracked inventory: files.json.
FILES MODIFIED: Three pre-existing8B files in the repair delta (RAG README, LiveEmbeddingIngestMain, IndependentEmbedding8BGuardSpec), plus coordinator prompt/review/repairs/reports. No core/storage/build production changes or human-decision edits in this repair.
COMMANDS RUN: Exact required JDK17 environment and all attempts in evidence/8b-r1/commands.md. Targeted-1 exit0 (RAG7,focused independent11). Targeted-2 exit1 (RAG32passed1failed due expected lowercase source wire; independent stage not reached). Corrected test literal only. Targeted-3 exit0 (RAG33/33,independent41/41). Full `/usr/bin/time -p sbt -batch check > /tmp/phase8b-r1-final-check-1.txt 2>&1` exit0.
TEST RESULTS: Full766passed0failed,695.67s real: core157/Hadoop64/ER39/Spark38/storage51/RAG33/independent376/build8. The new temporary G1 suite is discovered and passes inside check; raw log lines6477/7035/7037 identify suite, actual producer and passing case. Expected checkProbeInjectFailure remains the passing build failure-path self-test.
VALIDATION RESULTS: B1 suite uses a fresh temporary computed G1 export with no retainedtarget dependency, then actual CLI12writes→12unchanged/zero calls/rejections and fresh identical counters/manifests. Every persisted pointer/object/text hash and qualifications hash verified. Non-empty cap1 rejects exact scan-limit code; cap4 selects one per four literal summary types in stable order. RAG node unit test checks exact source fields/refs/table totals17/23/filter metadata/fifth index. N9 render-only actual CLI produces valid real-model work with no embedding/state, accepted by pure live preflight. Pure report retains model ID/version/dimension, per-index written counts, rejection details/URI. Query/latency command and disabled templates are authored but unexecuted; pure bounds/quantile/pointer/operation tests and refusal-zero-factory checks pass. Original runtime fence unchanged,7roots22inspected/no findings.346frozen files,8repair hashes and35cumulative source hashes match;251prior-scope files unchanged.
ASSUMPTIONS: Prior region/model/provisionaldimension/five-types/fallback/queue/coreclient/stable-slot decisions persist. User has no AWS account. G1 is explicitly synthetic direct-input provenance, not an executed Hadoop/ER acquisition. Pure valid approvals and hypothetical reports are test fixtures, never actual human grants or live measurements.
RISKS: Independent recheck pending. Live compatibility, real expected neighbors, latency, provider quality,10,000-vector count, costs and cleanup remain unverified. Query smoke retains conservative shared manifest/resource/cost checks and separately bounded query caps. Assumed prices/overhead are operator-validated bounds, not a billing guarantee. N10–N14/N2–N8/R2–R3 remain nonblocking/deferred. F1/N1/R1 retain independently FIXED status.
MANUAL ACTION REQUIRED: User launches independent recheck with evidence/8b-r1/reviewer-prompt.md. No commit before subsequent APPROVE; no automatic commit/push afterward. Future8C requires Phase14 deployment, AWS account and actual human approval/caps/new prompt.
BLOCKED-ON OWNER: None for completed repair.
BLOCKED-ON EVIDENCE: None for local gates; independent approval and future live gates open.
NEXT GATE: User-launched read-only8B repair-round-1 recheck. No reviewer, approved live execution, provider/cloud call, commit/push or next subphase started.

## Subphase 8B — independent approval recorded / commit proposal

STATUS: COMPLETE evidence recording; awaiting explicit user commit decision.
OWNER: /root coordinator.
WORK ORDER: Record user-supplied APPROVE for8B repair round1; user says not to repair nonblocking findings. No questions for this step.
FILES CREATED: evidence/8b-r1/external-recheck.txt, external-recheck.json, post-recheck-audit.json, commit-inventory.json and commit-proposal.md.
FILES MODIFIED: review.md, repairs.md, prompt.md, this report and test-report.md; coordinator evidence only.
COMMANDS RUN: Read-only git status/rev-parse; source/frozen re-hashing; proposed-path and credential-pattern checks. Exact inventory/audit retained in the new evidence files. No build/test command, staging, commit or push.
TEST RESULTS: No rerun; independently verified prior766passed0failed remains the test evidence. All35 source hashes and346 frozen files reverified unchanged.
VALIDATION RESULTS: B1/N9 independently FIXED; F1/N1/R1 retained FIXED. N2–N8/R2–R3/N10–N19 remain OPEN/nonblocking/deferred; N15 requires future pre-8C attention, not repair in this step. Proposed inventory excludes target/runtime/credential paths and high-confidence credential patterns; no secret content printed. External review copied verbatim and SHA256 retained.
ASSUMPTIONS: Independent approval is not human acceptance/instructor approval or commit permission. Prior8A commit/push permission does not authorize this8B commit.
RISKS: Deferred findings and all live8C gates remain. No code changes in this evidence-only step.
MANUAL ACTION REQUIRED: User reviews exact commit-proposal.md/commit-inventory.json and supplies an explicit commit decision. Proposed message: Implement Phase 8B local ingestion and retrieval validation.
BLOCKED-ON OWNER: User for commit authorization only.
BLOCKED-ON EVIDENCE: None for8B implementation; live gates remain future.
NEXT GATE: Explicit user commit decision; do not stage, commit, push or start8C.

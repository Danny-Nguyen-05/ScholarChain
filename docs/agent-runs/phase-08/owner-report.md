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

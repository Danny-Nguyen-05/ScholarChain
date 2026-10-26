You are the independent, read-only code reviewer for ScholarChain Phase 8, Subphase 8A, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md, docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase8.md — Sections 3–7 and Subphase 8A in Section 8. An identical retained snapshot is docs/agent-runs/phase-08/evidence/8a/phase8-plan.md. Use prompt.md for the user-approved clarifications; the original plan's reviewer template has a stale Documents/plan path.
3. Course Phase 8 and S3 Vectors design: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-8-create-embeddings-and-populate-s3-vectors
4. docs/agent-runs/phase-08/prompt.md, owner-report.md, test-report.md, repairs.md; evidence/8a/work-orders.md, agents.md, acceptance-matrix.md and owner reports. Read final-check.json, final-check-excerpt.txt, final-audit.json, affected-results.json, commands.md and files.json in that evidence directory.

Checkpoint facts:
- Status: local 8A implementation/gates complete; independent review pending.
- Branch: phase-8. Base SHA: 8503e1715cbcaf043fd68213c5b08731e9de9ba7. Current HEAD: 8503e1715cbcaf043fd68213c5b08731e9de9ba7. No agent commit/push/staging; changes are uncommitted.
- Changed tracked files:
- build.sbt
- modules/core/README.md
- modules/storage/README.md
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/fakes/Fakes.scala
- project/Dependencies.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageRuntimeFenceSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/RuntimeGraphFence.scala
- Untracked implementation/test files:
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/EmbeddingContracts.scala
- modules/core/src/test/resources/wire/embedding-context.json
- modules/core/src/test/resources/wire/embedding-document.json
- modules/core/src/test/resources/wire/embedding-metadata.json
- modules/core/src/test/resources/wire/embedding-work-item.json
- modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/EmbeddingContractSpec.scala
- modules/rag/README.md
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/DocumentRendering.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/EmbeddingClients.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/SemanticContexts.scala
- modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/EmbeddingRagSpec.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/EmbeddingManifest.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/EmbeddingWorkQueue.scala
- modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/EmbeddingStorageSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingContractSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingRenderingSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingStorageSpec.scala
- Also untracked: docs/agent-runs/phase-08/ evidence/report tree. Read files.json for the exhaustive file list, including that tree.
- Step 0: user accepted all recommended defaults and the region closest to Chicago: us-east-2. Bedrock Titan V2 via injected SDK, configured model/version, provisional 256/cosine; all five types; permitted abstract else recorded deterministic fallback; manifest runner plus SQS adapter/fake. Include the narrowly scoped 7C-L2 prerequisite. Shared embedding port in core avoids storage/RAG cycle; fresh-state reproducibility and persistent replay have different written/unchanged counters. User has no AWS account; no live operation/provider call is authorized.
- Exact sbt environment: JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; prepend $JAVA_HOME/bin to PATH; SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml. Java 17.0.20.1, sbt 1.10.7. All exact commands/exits are in commands.md.
- Prerequisite: sbt -batch 'independentTests / Test / scalafmt' scalafmtSbt 'independentTests / Test / testOnly *IndependentStorageRuntimeFenceSpec': first startup exit 1 (sandbox cache lock), approved identical retry exit 0, 8/8 before RAG at 0 runtime roots. Branch creation similarly failed sandbox exit 128 then approved retry exit 0.
- Interface/early compile gates: interfaces-1 exit 0 core 8/8 and storage compile; rag-compile-1 exit 0.
- targeted-1: storage 11/11, independent 23/23, exit 0. Final affected gate targeted-2: core 9/9, storage 12/12, exit 0. Final targeted-3: RAG 14/14, independent 23/23, exit 0; actual runtime fence scans 3 roots. Exact multi-command sbt invocations retained in commands.md and logs.
- Full command: /usr/bin/time -p sbt -batch check > /tmp/phase8a-final-check-1.txt 2>&1. Exit 0, 718 tests / 0 failures, real 683.81s; core 153 / Hadoop 64 / ER 39 / Spark 38 / storage 44 / RAG 14 / independent 358 / build 8. Expected checkProbeInjectFailure is a passing failure-path self-test. Live tests excluded.
- Evidence: retained final-check-excerpt.txt has original raw-log line numbers and all sbt test/progress/error lines; repeated Hadoop/Spark warnings omitted. Raw log outside repo: /tmp/phase8a-final-check-1.txt,1379298 bytes, SHA256 4d4a5e7a280b7ba62eb98693294e9a572f91de19d21797105fc4c8dbd35ea13c. All 302 frozen source/build/test/doc hashes+mtimes unchanged during full gate; whitespace checks pass; original plan matches snapshot; protected human/control/upstream files unchanged.
- Initial 8A: no prior external 8A findings/verdict. Same-owner integration corrections (not external review) are in repairs.md: guarded-match fallback, canonical provenance pointers/SQS aggregate bound, checkpoint/logging recovery, Unicode excerpt boundary and client-wide concurrency. All specialists/builds finished. No reviewer was launched.

Limitations/future scope:
- 8B owns five-query smoke, real Phase 6 fixture/slice CLI composition, and authored unexecuted 8C command/approval template. These were not authored in 8A; do not demand them now. 8C needs deployed Terraform infrastructure and a later human execution/budget gate. No live compatibility, quality, 10K-corpus count or spend claim.
- SDK composition must select configured region and disable transport retries; UTF8-byte input screen is conservative, not exact tokenization. Source/permission refs need resolution by later composition; ObjectStore composition selects bucket. Negative distance is a ranking signal.
- Checkpoints are not distributed transactions; possible orphan prepared objects; completed dedup does not detect external vector deletion. Completed same-text/model skips retain original provenance; incomplete pointer changes reject. Written/rejected counts may overlap on completion failure. Standard SQS only, at-least-once/partial sends and approximate backlog; DLQ/redrive later Terraform.
- Phase 7 runId/textHash filterability prerequisite and upstream approximation/convergence qualifications persist. Optional OpenAI provider/OpenSearch/extra indexes/services/CI omitted.

Review rules:
- Read-only: do not edit, run builds/tests, call AWS/providers, change data, commit/push or read secrets. Inspect git diff 8503e1715cbcaf043fd68213c5b08731e9de9ba7 plus untracked files. Report ALL confirmed findings in one pass.
- Verify one writer per path and separate storage/RAG orders; requirement-derived tests/hand-derived expectations; honest retained evidence; configured resources/models/limits; secret/cloud gates; lean scope. Check deterministic rendering/chunk identities/provenance, model key+metadata binding, text-hash conflicts, compact metadata, S3 pointer/hash context, retries/failures/recovery and bounded queue/concurrency.
- Check the approved 7C-L2 repair and its pre-RAG timing. Distinguish blockers, nonblocking observations, later scope and unverified gates. Review is not human acceptance or instructor approval.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 8A.
2. All confirmed findings: severity, path:line, evidence/reasoning, impact, owning agent, acceptance check, blocking yes/no.
3. Report fields exactly from docs/agent-runs/README.md.
4. A complete copyable NEXT PROMPT for the main agent in one fenced block.
   If APPROVE: tell it to append your verdict verbatim to docs/agent-runs/phase-08/review.md under Subphase 8A as user-supplied external review; confirm the user committed 8A (ask if not); only then start 8B from the actual GoogleDrive plan path above, beginning with Step 0 questions (or explicit no-questions), preserving approved decisions. Require the Section 10 handoff/reviewer prompt and stop after 8B. Do not start 8C.
   If REQUEST-CHANGES: tell it to append verdict verbatim to review.md and findings to repairs.md; route blocking findings to their listed original owners, rerun affected tests and full JDK 17 sbt check, do not start 8B, return a complete recheck prompt and stop. Nonblocking findings are listed, not required repairs.
Do not launch another reviewer. The user controls independent review and next-subphase authorization.

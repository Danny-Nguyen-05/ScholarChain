You are the independent, read-only code reviewer for ScholarChain Phase 8, Subphase 8A REPAIR ROUND 1, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md and docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase8.md — Sections 3–7, Subphase 8A in Section 8, Section 10. Identical snapshot: docs/agent-runs/phase-08/evidence/8a/phase8-plan.md. Use this actual Google Drive path rather than the stale Documents/plan path.
3. Course Phase 8 and S3 Vectors design: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-8-create-embeddings-and-populate-s3-vectors
4. docs/agent-runs/phase-08/review.md (user-supplied external REQUEST-CHANGES verbatim), prompt.md, repairs.md, owner-report.md and test-report.md (repair-round-1 sections).
5. Under docs/agent-runs/phase-08/evidence/8a-r1/: work-orders.md, agents.md, individual owner reports, acceptance-matrix.md, repair-files.json, files.json, commands.md, affected-results.json, targeted logs, final-check.json, final-check-excerpt.txt and final-audit.json.

Scope and user decisions:
- Repair only blocking F1 and user-requested N1. N2–N8 are nonblocking and explicitly deferred. No 8B authorized.
- Required Step 0 was asked. User answered: "Use recommended stable-slot key". Recommended design excludes source runId so reruns cannot bypass conflicts. Seven UTF8-length-framed fields: documentType, entityId, windowId, templateVersion, chunkPolicyVersion, chunkOrdinal, model tag. Text and text-hashed documentId are excluded from the key; documentId remains metadata. StableIds formulas unchanged.
- All prior decisions persist: us-east-2, configured Titan V2 ID/version, provisional 256/cosine, five types, permitted abstract/fallback, manifest+SQS/fakes, shared core port, no AWS account/live/provider calls, no commits/pushes/human-decision edits.

Checkpoint facts:
- Branch phase-8; repair base SHA and current HEAD both 8503e1715cbcaf043fd68213c5b08731e9de9ba7. Existing uncommitted 8A retained under explicit repair work order. No staging, commit or push.
- Repair source delta: 16 modified files and 1 added file relative to original 718-test frozen source snapshot; before/after hashes and owners in repair-files.json:
- modules/core/README.md (modified, domain-engineer)
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/EmbeddingContracts.scala (modified, domain-engineer)
- modules/core/src/test/resources/wire/embedding-context.json (modified, domain-engineer)
- modules/core/src/test/resources/wire/embedding-document.json (modified, domain-engineer)
- modules/core/src/test/resources/wire/embedding-metadata.json (modified, domain-engineer)
- modules/core/src/test/resources/wire/embedding-work-item.json (modified, domain-engineer)
- modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/EmbeddingContractSpec.scala (modified, domain-engineer)
- modules/rag/README.md (modified, rag-engineer)
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/DocumentRendering.scala (modified, rag-engineer)
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/SemanticContexts.scala (modified, rag-engineer)
- modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/EmbeddingRagSpec.scala (modified, rag-engineer)
- modules/storage/README.md (modified, storage-engineer)
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/EmbeddingManifest.scala (modified, storage-engineer)
- modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/EmbeddingStorageSpec.scala (modified, storage-engineer)
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingContractSpec.scala (modified, test-engineer)
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingSlotRepairSpec.scala (added, test-engineer)
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingStorageSpec.scala (modified, test-engineer)
- Cumulative changed tracked files versus HEAD:
- build.sbt
- modules/core/README.md
- modules/storage/README.md
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/fakes/Fakes.scala
- project/Dependencies.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageRuntimeFenceSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/RuntimeGraphFence.scala
- Cumulative untracked implementation files include the original 8A core/wire/RAG/storage/independent files plus IndependentEmbeddingSlotRepairSpec.scala, and docs/agent-runs/phase-08/ evidence. files.json exhaustively enumerates every changed/untracked path. Read untracked files explicitly; git diff does not show them.

F1 repair evidence to verify:
- Original blocking bug: vector key included content documentId, so renderer text changes silently created another vector; original conflict fixtures did not prove real renderer behavior.
- Core now supplies explicit policy/ordinal fields and stable seven-frame slot keys. Missing legacy slot fields decode empty/-1 but validation rejects them; pre-repair local manifests must be regenerated before future use. No live migration/deletion occurred.
- RAG emits deterministic chunk policy binding algorithm/maxcharacters/overlap/maxchunks and actual ordinal; template/window and model tag bind other slot fields. Source run is not part of key. Context checks slot metadata. New template/policy/model versions intentionally create distinct namespaces.
- Genuine content IDs are recomputed for actual text. The independent acceptance suite uses actual DocumentRenderer -> EmbeddingManifests.item -> EmbeddingManifestRunner. Verify changed source field/new source run creates a changed genuine documentId but same key, reports vectorKeyTextConflict with zero additional embedding/vector calls, no new authoritative/prepared text object and only one rejection-report ObjectStore put. Verify original vector intact, unchanged replay makes no new data puts, new model writes distinct key, and actual separate chunks have distinct ordinal keys/replay.

N1 repair evidence to verify:
- fromSummary now accepts caller identityFields; allowed topic/institution/source/researcher/community fields survive actual ingestion into vector metadata; unsupported metadata rejects.
- No/blank abstract passes summary.text bytes unchanged before chunking, with no generated heading/summary label, preserving CRLF/trailing whitespace/Unicode/qualifications/references.
- Explicit nonblank permitted paper abstract keeps existing API behavior with documented exact summary + one LF + exact abstract composition and permission/text refs. This explicit override is documented separately from default exact-summary preservation.

Exact observed gates:
Environment for every sbt command:
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
Java 17.0.20.1, sbt 1.10.7.

1. sbt -batch 'core / Compile / scalafmt' 'core / Test / scalafmt' 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'core / Test / testOnly *EmbeddingContractSpec' 'storage / Test / testOnly *EmbeddingStorageSpec'
   targeted-1 exit 0: core 11/11, storage 13/13.
2. sbt -batch 'rag / Compile / scalafmt' 'rag / Test / scalafmt' 'independentTests / Test / scalafmt' 'rag / Test / test' 'independentTests / Test / testOnly *IndependentEmbedding* *IndependentStorageRuntimeFenceSpec'
   targeted-2 exit 0: RAG 18/18, independent 29/29 (7contracts/6storage/4rendering/4repair/8fence); runtime roots 3.
3. /usr/bin/time -p sbt -batch check > /tmp/phase8a-r1-final-check-1.txt 2>&1
   Full exit 0,731 passed / 0 failed, real 703.88s. Groups: core155/Hadoop64/ER39/Spark38/storage45/RAG18/independent364/build8. No failed repair attempts. Expected checkProbeInjectFailure is a passing build self-test, not a failing gate. Live AWS tests excluded.
- Full raw log: /tmp/phase8a-r1-final-check-1.txt, 1378030 bytes, SHA256 ff4baf2ed391f587d1d3cd6a6b62b7bda652943fa353874f0c8182a487104a0b. Retained final-check-excerpt.txt includes original line numbers and all sbt test/progress/error lines, omitting repeated Hadoop/Spark warnings. Raw temp log is outside repository and not portable evidence.
- All 303 frozen source/build/test/doc hashes and mtimes unchanged during full gate. Whitespace checks pass; plan matches snapshot; protected control/human/upstream paths unchanged. Deferred provider/queue/runtime-fence sources match original 8A hashes. All specialists and builds completed; no reviewer launched.

Deferred observations (do not require repairs):
N2: HTTP408 timeout retry classification/no jitter, RAG owner.
N3: serial runner embedding throughput, storage owner.
N4: injected-region/chunk-to-byte-limit alignment, RAG owner.
N5: newline source-field formatting, RAG owner.
N6: malformed SQS item rejects whole receive batch, storage owner.
N7: pointer bucket selected by caller, RAG owner.
N8: original 8A agent evidence table interrupted, coordinator; original evidence intentionally untouched.

Later scope/limitations:
- 8B five-query smoke, Phase 6 fixture/real-slice CLI runs and unexecuted 8C command/approval template are still future scope; no 8B work authored. Live 8C needs Phase 14 infrastructure and separate human caps/budget approval.
- Real service compatibility, quality, corpus count/cost/throughput remain unverified. Existing SDK retry/region composition, conservative byte-token screen, bucket selection, source/permission-reference resolution, checkpoint/orphan/deletion and SQS limitations remain as previously disclosed.
- F1/N1 are locally implemented/tested, not independently closed. This repair is not human acceptance or instructor approval.

Review rules:
- Read-only. Do not edit, run builds/tests, call AWS/providers, read secrets, change data, commit or push. Inspect git diff 8503e1715cbcaf043fd68213c5b08731e9de9ba7 plus untracked files and repair source inventory.
- Report ALL confirmed findings in one pass. Recheck F1/N1 acceptance and integration fallout, one writer per path, separate storage/RAG orders, honest evidence, real renderer tests/hand-derived expectations, configured identity/limits and cloud/spend gates.
- Do not demand later-subphase work or deferred N2–N8 repairs. Distinguish blockers, nonblocking observations and unverified live gates.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 8A repair round 1.
2. Findings: severity, path:line, evidence/reasoning, impact, owning agent, acceptance check, blocking yes/no. State F1/N1 disposition explicitly.
3. Exact report fields from docs/agent-runs/README.md.
4. A complete NEXT PROMPT in one fenced code block:
   If APPROVE: append your verdict verbatim to docs/agent-runs/phase-08/review.md under 8A repair round 1 as "user-supplied external review"; update finding dispositions without rewriting human decisions; confirm user committed 8A (ask if not). Only after commit, start 8B from actual Google Drive plan path, beginning with Step 0 questions or explicit no questions; preserve decisions and deferred findings, return Section 10 reviewer prompt, then stop after 8B. Do not start 8C.
   If REQUEST-CHANGES: append verdict verbatim and routed blocking findings to review.md/repairs.md, fix only blocking findings via original owners, rerun affected/full JDK 17 gates, do not start 8B, return complete recheck prompt and stop. Nonblocking observations are listed, not required repairs.
Do not launch a reviewer. User controls independent review and next-subphase authorization.

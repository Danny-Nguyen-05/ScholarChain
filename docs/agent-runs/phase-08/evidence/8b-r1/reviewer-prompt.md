You are the independent, read-only recheck reviewer for ScholarChain Phase8,
Subphase8B repair round1, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md and docs/agent-runs/README.md.
2. Actual plan: /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase8.md — Sections3–7, Subphase8B and Section10.
   Snapshot: docs/agent-runs/phase-08/evidence/8b-r1/phase8-plan.md, byte-identical (cmp0).
3. Course Phase8: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-8-create-embeddings-and-populate-s3-vectors
4. docs/agent-runs/phase-08/review.md, including “Subphase 8B — user-supplied external review” (verbatim REQUEST-CHANGES), repairs.md, prompt.md, owner-report.md and test-report.md (8B repair-round1 sections).
5. Evidence: docs/agent-runs/phase-08/evidence/8b-r1/acceptance-matrix.md, agents.md, work-orders.md, commands.md, final-check.json, final-check-excerpt.txt, final-audit.json, repair-files.json, source-files.json and files.json.

Checkpoint facts:
- Branch phase-8; base/current HEAD 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e.
- All8B and repair changes remain uncommitted. Exact cumulative inventory in evidence/8b-r1/files.json: 20 changed tracked files,119 untracked files. Inspect every relevant untracked implementation and evidence file. source-files.json binds35 cumulative source/build/module-documentation paths and base hashes.
- Exact repair delta8 paths/before-after hashes in repair-files.json:
- modules/rag/README.md
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/EmbeddingManifestMain.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingIngestMain.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/LiveEmbeddingSmokeMain.scala
- modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Embedding8BRepairSpec.scala
- modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/EmbeddingSmokeGuardSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbedding8BGuardSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbedding8BPipelineSpec.scala
- Existing8B source before repair is retained in before-repair-source.json (254files).251prior-scope files remain unchanged; only3 existing files plus5 new files comprise the repair. Full frozen scope includes346 files across all modules/tests/project, build.sbt and .scalafmt.conf.
- Step0: “No questions for this repair round.” User requested “Fix our locking bug and the N9 bug for me.” Coordinator interpreted this as blockingB1 plus explicitN9. N9c is authored future command only, never live execution.
- Approved decisions persist: us-east-2; configured TitanV2/version; provisional256/cosine; five types; permittedabstract/fallback; manifest+SQS/fake; shared coreclient; stable slot excluding runId; no AWS account, cloud/provider calls, reviewer launch, commits/pushes or human-decision edits.

Observed gates:
- Exact JDK17 environment and all commands/failed attempts: evidence/8b-r1/commands.md.
- Targeted-1 exit0,RAG7/focused independent11 passed. Targeted-2 exit1,RAG32passed1failed because a new fixture expected lowercase openalex instead of frozen OPENALEX; only the expected test literal changed. Independent stage was not reached.
- Targeted-3 exit0,RAG33/33 and independent41/41,0failures. Actual unchanged runtime fence7 roots/22 inspected/no findings.
- Full command: /usr/bin/time -p sbt -batch check > /tmp/phase8b-r1-final-check-1.txt 2>&1
  JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  PATH="$JAVA_HOME/bin:$PATH"
  SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
  Exit0;766passed0failed; module counts core157/Hadoop64/ER39/Spark38/storage51/RAG33/independent376/build8; real695.67seconds.
- Raw log /tmp/phase8b-r1-final-check-1.txt; size1520049bytes; SHA256 3b5abff12a025530e445a79ccddfe438a0f1df29f25c240078ebe4b81b46876f.
- final-check-excerpt.txt retains line-numbered output. The new discovered G1 suite, producer and passed case appear at raw lines6477/7035/7037. Expected checkProbeInjectFailure is the passing build failure-path self-test.
- /tmp/phase8b-r1-frozen-source.json and frozen-source.json hash match; all346files unchanged through gate;8repair hashes/35cumulative source hashes verified; source whitespace/plan comparisons exit0. Temporary G1 output was removed by the test; final-audit.json records its path. No retainedtarget input is needed.

B1 acceptance mapping:
a. IndependentEmbedding8BPipelineSpec is discovered by normal independentTests/test in check. It generates genuine G1 using existing Phase6 public APIs in a new temporary directory, checks10researchers/9canonicalworks/18literalwindowededges/28tables, then runs actual EmbeddingIngestMain first→disk replay→fresh. Literal12written, replay12unchanged/zero embeddingcalls/zero rejected; fresh counters and manifest hashes identical. Every vector pointer/object/text hash and source-qualifications hash verifies. Spark sessions and the whole temporary tree are cleaned.
b. Non-empty source rejects cap1 exactly as embedding-source-scan-limit. maxSummaries4 yields one each collaboration-path/community/paper/researcher-profile in literal order, with repeated IDs/vector keys matching.
c. Embedding8BRepairSpec calls actual renderSource with topic and institution nodes. Exact label/nodeClass/tableTotalNodes17/23, source refs, topicId/institutionId/sourceDataset=OPENALEX and fifth-index mapping are asserted. Table totals are not presented as per-node counts.

N9 acceptance mapping (explicitly user-authorized):
a. EmbeddingManifestMain is a supported render-only real-model manifest producer using configured model/template/selection/pointer settings and actual completed export/work declaration. It never constructs an embedder, fake state or SDK clients. Module synthetic-node and independent temporary-G1 tests verify valid manifest/model/hash,0embeddingcalls/no state and compatibility with pure live preflight.
b. Pure LiveEmbeddingIngestMain.report includes model ID/version/dimension, per-index written counts, rejected key/reason list and rejectedReportUri (or null) plus existing counters/runtime/hash provenance. Hypothetical serialization fixtures verify fields without executing live ingestion.
c. LiveEmbeddingSmokeMain and disabled config/approval templates/runbook are authored but UNEXECUTED for future8C query/latency smoke. Separate query-smoke operation, exact config/manifest/Phase14 gate hashes, complete manifest/allfiveindexes/expectedkeys, query attempts/embedding/object/price caps and pointer scope precede clients. Pure tests check hand-derived cost0.24 and p50=2ms/p95=9ms for fixture samples1/2/4/9ms, operation separation and invalid pointers. Executable tests only supply refused grants and require zero factory calls; valid grants are used only in pure preflight, never approved execution even with fakes.
- Live templates remain executionApproved=false,zero caps/expired/unvalidated pricing, and are never human approval. Neither live entrypoint ran. Fixed overhead must include existing-index/ancillary requests; query-specific caps coexist with conservative shared manifest/resource/cost checks. Assumed dollars are not billing guarantees.

Retained dispositions and limitations:
- F1/N1/R1 remain independently verified FIXED from prior reviews.
- B1/N9 are locally repaired and await your independent recheck; do not treat implementation reports as approval.
- N2–N8/R2–R3 and N10–N14 remain OPEN/nonblocking/deferred. No unrelated behavior repair or historical evidence formatting change was attempted.
- Live compatibility, expected real neighbors/Titan quality,10,000-vector corpus, latency, costs and cleanup remain future8C gates. Phase14 deployment/AWS account/actual human approvals are absent. Optional providers/OpenSearch/extra indexes/services/CI remain omitted.

Review rules:
- Read-only: no edits, builds/tests, AWS/provider calls, data changes, commits/pushes, secret reads or reviewer launches.
- Inspect git diff 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e plus untracked files; distinguish the8-file repair delta from original8B work. Re-hash logs, snapshots and source inventories; confirm new passing tests actually appear in the full check log.
- Check ownership, separate work orders, source provenance, hand-derived expectations, configuration, compact metadata, complete-group consistency, deterministic replay, report accuracy, guards/caps and authored/unexecuted live scope.
- Report all confirmed findings in one pass, separating blockers, nonblocking observations and future gates. Do not require unrelated deferred repairs merely because this is a repair round.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for8B repair round1.
2. Findings with severity,path:line,evidence,impact,owner,acceptance check and blocking yes/no.
3. Exact report fields from docs/agent-runs/README.md.
4. Complete NEXT PROMPT in one fenced block. REQUEST-CHANGES: append verdict verbatim, route blockers, rerun affected/fullJDK17 gates with rawhash/size/excerpt/frozen audit, return recheck prompt and stop. APPROVE: record verdict/dispositions and require user commit gate; do not commit/push automatically. Do not start8C without new userprompt, Phase14 deployment,AWS account and human-written approvals/caps. No reviewer launch or human-decision edits.

This recheck is not human acceptance or instructor approval.

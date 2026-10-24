# Phase 8 external reviews

## Subphase 8A

Pending user-launched independent read-only review. No external verdict has been supplied or inferred.

### Repair round 1 — user-supplied external review

The pending statement above describes the original handoff. The user supplied the following review on 2026-10-24. It is retained verbatim below; the coordinator does not endorse or rewrite the reviewer's conclusions.

ScholarChain Phase 8, Subphase 8A: independent read-only review

1. VERDICT: REQUEST-CHANGES for Subphase 8A

There is one blocking finding (F1): the vector key is built from a hash of the document text, so the "same key, different text" conflict can never happen for documents the renderer produces. Everything else checked out or is nonblocking. The evidence is honest: I re-hashed the raw log at /tmp/phase8a-final-check-1.txt, and its SHA256 (4d4a5e7a…ea13c) and size (1,379,298 bytes) match the report. The suite totals in final-check-excerpt.txt add up to 718 passed with 0 failures.

2. Findings

F1 (blocking, high): the vector key changes whenever the text changes, so text conflicts are unreachable

- Where:
  - modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/EmbeddingContracts.scala:28-29 builds the key from document.documentId.
  - modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/DocumentRendering.scala:161-167 sets documentId = StableIds.chunkOrProfileId(entity, version(window), type, ordinal, chunk).
  - modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/StableIds.scala:363-371 puts sha256(text) into that ID.
- What happens: A researcher profile, community or paper for the same entity, window, template and model whose rendered text changes (for example, a Phase 6 rerun with different counts) gets a new documentId. That means a new vector key. The runner then writes a second vector alongside the old one instead of reporting vectorKeyTextConflict.
- Why it matters:
  - The plan's binding design (§7.3 step 3, "Phase 7 rule") cannot trigger for real input.
  - The course gate "same vector key cannot silently refer to different text" holds only trivially.
  - The index silently collects stale, parallel vectors per entity and window, and retrieval can return outdated profiles.
  - This departs from Phase 7's VectorIndexes.key (type, entityId, window, model version; Phase7Configs.scala:94-102, storage README:67). The domain work order made that change, but no human approved it, and its effect on conflict detection is not disclosed.
- Supporting evidence:
  - The storage README (the "changed text for an existing key is rejected" paragraph, ~line 261) describes behaviour that rendered documents can never reach.
  - Both conflict tests build forged states that the renderer can never produce:
    - modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/EmbeddingStorageSpec.scala:140-143 copies a document with new text but keeps a documentId that still hashes "distributed graph".
    - tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentEmbeddingStorageSpec.scala:19,98 uses a fake "profile:" + "a"*64 ID.
  - EmbeddingValidation.document (EmbeddingContracts.scala:172) only checks the shape of the ID, so these documents, whose ID does not match their text, pass validation.
- Owners:
  - domain-engineer: key contract, plus an additive slot/ordinal field if one is needed.
  - rag-engineer: the renderer fills that slot.
  - storage-engineer: module tests and README.
  - test-engineer: independent conflict test.
- Acceptance check: One of these two remedies:
  - (a) Recommended: the vector key comes from a stable slot that does not depend on the text (type, entityId, window, template/chunk-policy version, ordinal, model tag; including the source run is the owner's choice and must be disclosed). documentId stays in the metadata. Tests then go through the real DocumentRenderer → EmbeddingManifests.item → runner path. They must show:
    - changed field text for the same slot gives the same key and is rejected as vectorKeyTextConflict with zero embedding calls;
    - unchanged text is skipped;
    - a new model version gives a new key;
    - distinct chunks still get distinct keys.
  - (b) Only with a user decision recorded first: keep content-addressed keys. Validation must then reject documents whose ID does not match their text, the stale/parallel-version behaviour must be disclosed in the READMEs, and a test must show what happens when text changes.
- Gates: affected tests plus the full JDK 17 sbt check.

Nonblocking observations (not required repairs)

ID: N1
Severity: Medium
Where: modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/DocumentRendering.scala:126-141
What I found: fromSummary builds RenderInput without identityFields and has no parameter for them. Phase 6 summaries therefore can't carry the topic,
institution or source-dataset metadata the course asks for. It also adds a heading and summary: around the text, while the README says the text is
preserved exactly. Should be resolved when 8B composes the Phase 6 export.
Owner: rag-engineer
────────────────────────────────────────
ID: N2
Severity: Low
Where: modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/EmbeddingClients.scala:140-145
What I found: Bedrock ModelTimeoutException (HTTP 408) is treated as permanent, so it is never retried. The backoff also has no jitter, so concurrent
retries happen at the same moments.
Owner: rag-engineer
────────────────────────────────────────
ID: N3
Severity: Low
Where: modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/EmbeddingManifest.scala:351
What I found: The runner calls embed(Seq(text)) one item at a time, so the client's concurrency limit is never used and throughput is serial.
Relevant to 8C and Phase 15.
Owner: storage-engineer
────────────────────────────────────────
ID: N4
Severity: Low
Where: EmbeddingClients.scala:42-61
What I found: BedrockEmbeddingConfig.region is never checked against the injected client's region (already disclosed). Nothing checks that chunk size
fits the 8,192-byte input screen. A larger chunk policy would make every item fail permanently.
Owner: rag-engineer
────────────────────────────────────────
ID: N5
Severity: Low
Where: DocumentRendering.scala:96,108
What I found: A field value containing a newline can produce text that looks like another name: value line in the rendered output.
Owner: rag-engineer
────────────────────────────────────────
ID: N6
Severity: Low
Where: modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/EmbeddingWorkQueue.scala:143-156
What I found: One malformed SQS message rejects the whole receive batch. The valid messages' receipts are dropped, and those messages stay invisible
until their visibility timeout ends.
Owner: storage-engineer
────────────────────────────────────────
ID: N7
Severity: Info
Where: modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/SemanticContexts.scala:66-72
What I found: The pointer check ignores the bucket name (already disclosed).
Owner: rag-engineer
────────────────────────────────────────
ID: N8
Severity: Info
Where: docs/agent-runs/phase-08/evidence/8a/agents.md:11
What I found: A paragraph is inserted between rows of the markdown table and breaks it.
Owner: coordinator

Verified and acceptable

- Ownership: separate storage and RAG work orders, one writer per path.
- Configuration: no hardcoded model, region, bucket or account in main sources.
- Metadata: model ID, version and dimension appear in the key tag and the metadata; metadata is compact, with no text, excerpts or reference arrays.
- S3 text: canonical ordinary-S3 JSON with the text hash.
- Recovery: prepared-vector checkpoint and replay.
- Logging: retry and failure records are kept in RunLedger; logs carry counts only.
- Queue limits: SQS limits of 10 entries per batch, per-message size, and 1 MiB per batch.
- Concurrency: one semaphore shared across calls.
- Tests: chunking expectations are hand-derived (I re-derived all three).
- Spend: no live or provider calls.
- Lean scope: omitted items are recorded.
- 7C-L2 runtime-fence repair: sound. The prerequisite run (prerequisite-2) finished at 19:46:50, and the RAG source files were created from 19:50:29 onward, so the repair ran before any RAG runtime code existed.
- Later scope, not demanded now: the 8B five-query smoke tests, the CLI, the end-to-end pointer round trip, and the 8C template.

3. Report

STATUS: COMPLETE (review); verdict REQUEST-CHANGES for 8A
OWNER: code-reviewer (user-launched, independent, read-only)
WORK ORDER: Phase 8 Subphase 8A review per user-supplied prompt; plan snapshot evidence/8a/phase8-plan.md (byte-identical to Google Drive plan, verified with cmp)
FILES CREATED: None
FILES MODIFIED: None
COMMANDS RUN: Read-only only: git rev-parse/status/diff 8503e17 (tracked changes); cat/wc/grep/stat of evidence and sources; cmp of plan vs snapshot (identical); shasum -a 256 and stat of /tmp/phase8a-final-check-1.txt (4d4a5e7a…ea13c, 1379298 bytes: match); WebFetch of the public course README. One grep was blocked by the guard-dangerous hook and was rerun with a narrower pattern. No builds, tests, AWS/provider calls or edits.
TEST RESULTS: Not rerun (read-only). Retained logs show core 153, Hadoop 64, ER 39, Spark 38, storage 44, RAG 14, independent 358, build 8 = 718 passed / 0 failed, exit 0; targeted gates match claims (9/12/14/23). Expected checkProbeInjectFailure present.
VALIDATION RESULTS: One blocking defect (F1: text-derived vector key makes vectorKeyTextConflict unreachable for rendered documents; conflict tests use forged ID/text-inconsistent states). Nonblocking N1–N8. Pre-RAG timing of the 7C-L2 repair confirmed by file birth times.
ASSUMPTIONS: Plan §7.3 and the Phase 7 key rule are binding unless the user records otherwise; the course README does not fix the key layout.
RISKS: Unrepaired F1 lets 8C ingestion silently accumulate stale parallel vectors per entity/window/model. Live compatibility, Titan quality, corpus count, cost and throughput remain unverified (later gates).
MANUAL ACTION REQUIRED: User chooses F1 remedy (a) or (b); user pastes the next prompt. No commit until a recheck approves.
BLOCKED-ON OWNER: domain-engineer (key contract), rag-engineer (renderer slot), storage-engineer (module tests/README), test-engineer (independent conflict test)
BLOCKED-ON EVIDENCE: F1 acceptance tests through the real renderer→item→runner path; full JDK 17 sbt check after repair
NEXT GATE: 8A repair round, then user-launched recheck review. 8B not authorized.

This review is not human acceptance and not instructor approval.

### Repair round 1 recheck — user-supplied external review

ScholarChain Phase 8, Subphase 8A, repair round 1: independent read-only recheck

1. VERDICT: APPROVE for 8A repair round 1

F1 is fixed and verified through the actual renderer → EmbeddingManifests.item → runner path. N1 is fixed as requested. I found three new nonblocking observations and no blockers. N2–N8 stay deferred.

This approval is not human acceptance or instructor approval.

2. Dispositions and findings

F1: fixed and verified (was a blocker)

- The key is now a stable slot. EmbeddingContracts.scala:32-41 length-frames seven fields: type, entity, window, template, chunk policy, ordinal and model tag. Text, documentId and runId are left out.
  - I re-derived the fixed expectation "18:researcher-profile1:e1:w1:t1:p1:09:1:m1:v1:2" by hand at IndependentEmbeddingContractSpec.scala:54.
  - Validation rejects slot fields that are missing, blank or negative (EmbeddingContracts.scala:199-201). Legacy decoding falls back to ""/-1 and then fails validation (spec lines 89-97).
- The renderer fills the slot. DocumentRendering.scala:75-83 binds the policy version to the algorithm name and all three limits. Lines 196-209 set the real ordinal. The content ID formula is unchanged.
- The conflict is now reachable. In EmbeddingManifest.scala:315-317, a binding with a different hash is rejected before any text, prepared-vector or embedding write.
  - IndependentEmbeddingSlotRepairSpec.scala:94-142 uses real rendered text (papers: 7 → 8) with a new source run. It gets a new genuine documentId, the same key, the result (0,0,1,1,0), no new embeddings or putBatch calls, exactly one graph/rejected/ object, and an unchanged original vector. Unchanged replay then performs zero writes.
  - Lines 144-170 cover a new model getting a distinct key and two real chunks getting ordinals 0 and 1 with separate keys and a clean replay.
- Storage fixtures now use genuine content IDs (EmbeddingStorageSpec.scala:15-31). Lines 156-188 show the conflict happens before embedding. Lines 101-109 show that the same text under a different source run is skipped. That was my condition 3 when you chose the remedy.
- Retrieval checks the slot. SemanticContexts.scala:31-39 verifies the slot metadata.
- The READMEs are accurate, including the new template/policy/model namespaces.

N1: fixed and verified (requested by the user)

- fromSummary now accepts identityFields, and documents() validates them (DocumentRendering.scala:137-172).
- With no abstract or a blank one, the exact summary.text bytes are kept. With a permitted abstract, the text is the exact summary, one LF, then the exact abstract, and both references are kept.
- Spec lines 197-267 check the exact CRLF and whitespace bytes and that all five filter fields reach the stored vector metadata. Unsupported or oversized fields are rejected.

New observations (all nonblocking)

R1 (Medium): a change in chunk count leaves an entity's chunk set stale or mixed, and nothing discloses this.
- Where:
  - EmbeddingManifest.scala:289-401: the runner works item by item and has no idea how many chunks an entity should have.
  - modules/storage/README.md (~line 255) and modules/rag/README.md:40-44 claim that same-slot changes never write a "parallel stale vector".
- Shrinking text: going from 2 chunks to 1 with chunk 0 unchanged skips ordinal 0. The old ordinal 1 stays retrievable, nothing is rejected, and completeRun succeeds, so the stale chunk is silent.
- Growing text with a changed prefix: ordinal 0 is rejected as a conflict, but the new ordinal 1 is embedded and written. Old and new versions end up mixed. The run is reported as rejected, so this case is not silent.
- Course gate: still met, because no key ever refers to different text. This is the group-consistency gap I raised as condition 2 when you chose option 1. The remedy you chose didn't include it, so it is not required now.
- Impact: stale or mixed chunks can show up in retrieval for multi-chunk documents. Single-chunk profiles are not affected.
- Owners: storage-engineer (group binding in the runner), domain-engineer (only if a contract field is needed), rag-engineer (the renderer emits the chunk count), test-engineer.
- Acceptance check, either:
  - an entity-group binding (type, entity, window, template, policy, model → chunk count plus whole-text hash), where any mismatch rejects the whole group before any embedding; tests through the real renderer cover both shrink and grow; or
  - a recorded disclosure plus a test that pins down the behaviour.
- Timing: resolve before any 8C live ingestion. 8B Step 0 should ask about it.

R2 (Low): metadata-only changes are skipped silently.
- Where: EmbeddingManifest.scala:320-327, confirmed by EmbeddingStorageSpec.scala:101-109.
- What happens: when the text is unchanged but identityFields or runId differ, the item counts as unchanged, and the stored filter metadata keeps the first version's values.
- Why it matters now: with N1, caller-supplied fields such as a changed communityId can reach this path. This matches the course's text-hash/model skip rule, but nothing discloses it.
- Owner: storage-engineer (README disclosure, or bind the metadata hash). Nonblocking.

R3 (Low): the metadata budget is not checked before embedding.
- Where: EmbeddingManifest.scala:342-386 against the S3 Vectors 2 KiB filterable limit (Phase7Configs.scala:65).
- What happens: the fixed keys take about 650 bytes, and the five identity fields can add up to 5×256 bytes of values. A document near the worst case pays for an embedding and saves a prepared checkpoint before the adapter rejects it with a typed error.
- Owner: storage-engineer (check the filterable budget before embedder.embed). Nonblocking, relevant to 8C.

Other checks

- Deferred items: N2–N8 are unchanged and deferred. EmbeddingClients.scala, EmbeddingWorkQueue.scala and the fence files hash to their entries in the original /tmp/phase8a-frozen-source.json, and their modification times are from Oct 23.
- Repair-file hashes: all 17 match repair-files.json, and both frozen-snapshot hashes match.
- Process: ownership was one writer per path, each owner had a separate work order, no build files changed, and there were no cloud or provider calls.

3. Report

STATUS: COMPLETE (recheck); verdict APPROVE for 8A repair round 1
OWNER: code-reviewer (user-launched, independent, read-only)
WORK ORDER: Phase 8 Subphase 8A repair round 1 recheck per user-supplied prompt; F1 + user-requested N1; N2–N8 deferred
FILES CREATED: None
FILES MODIFIED: None
COMMANDS RUN: Read-only: git rev-parse/status/diff --stat 8503e17; shasum of 17 repair files (all match repair-files.json), targeted-1/2 logs (match affected-results.json), raw log /tmp/phase8a-r1-final-check-1.txt (ff4baf2e…a0b, 1378030 bytes: match), both frozen snapshots (match); stat of deferred files; grep/read of sources, tests, READMEs, evidence. No builds, tests, AWS/provider calls or edits.
TEST RESULTS: Not rerun (read-only). Retained: targeted-1 core 11/11, storage 13/13; targeted-2 RAG 18/18, independent 29/29; full check 155/64/39/38/45/18/364/8 = 731 passed, 0 failed, [success] 702 s, exit 0; expected checkProbeInjectFailure present.
VALIDATION RESULTS: F1 FIXED (stable seven-frame slot; real renderer→item→runner conflict with zero embed/vector/text writes except rejection report; unchanged and cross-source-run skip; new-model and per-ordinal keys). N1 FIXED (identity fields reach vector metadata; exact summary bytes; explicit abstract composition). New nonblocking R1 (chunk-count change stale/mixed group), R2 (metadata-only change skipped), R3 (no filterable-budget precheck before embedding).
ASSUMPTIONS: The user's Step 0 choice was option 1 without the group-atomicity condition, so R1 is not an F1 acceptance criterion.
RISKS: R1 before multi-chunk 8C ingestion; live Titan/S3 Vectors compatibility, quality, corpus count, cost and throughput unverified; N2–N8 open.
MANUAL ACTION REQUIRED: User reviews and commits the 8A + repair-round-1 tree (agents do not commit); user decides R1 handling at 8B Step 0; user authorizes 8B.
BLOCKED-ON OWNER: None
BLOCKED-ON EVIDENCE: None for 8A. Live 8C gates remain future.
NEXT GATE: User commit of 8A, then 8B Step 0.

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

## Subphase 8B — user-supplied external review

1. VERDICT: REQUEST-CHANGES for Subphase 8B

There is one blocking finding: none of the new 8B local ingestion path has a passing-path test in sbt check, and the fifth document type's real-data path isn't covered by any test. Everything else holds up. The R1 repair is correct and well tested, the evidence verifies, and the spend gates were respected.

What I verified

- Plan and course spec: the plan snapshot matches the Drive file byte for byte (SHA256 14daa4a4…9e27). I read the course Phase 8 section, and the 8B scope matches the plan.
- Full gate log: /tmp/phase8b-final-check-1.txt is 1,381,548 bytes with SHA256 91ef6871…ea59, both as recorded. Its per-module counts are 157/64/39/38/51/25/374/8, which sum to 756 with 0 failures. It ends in [success], and the injected-failure line at 6518 is the build's expected self-test.
- File inventory: files.json matches git status exactly (19 tracked, 81 untracked). All 30 hashes, sizes and base hashes in source-files.json match the files on disk and in git.
- Frozen snapshot: all 254 files in /tmp/phase8b-frozen-source.json (SHA d6fb7eb0…e8e2) are unchanged, and nothing unsnapshotted exists in that scope. The G1/real/producer artifact inventories (22+22+6 hashes) all verify. The raw logs for replay-2, replay-3 and targeted-g1-3 also verify. The .exit files match commands.md, including the failed attempts.
- Targeted gates: the retained excerpts show core 13, storage 19, RAG 25 and independent 39. The runtime fence reports 5 roots, 20 files and no findings; the fence spec is unchanged.
- R1 repair: EmbeddingManifest.scala:288-355 builds the group key from type, entity, window, template, chunk policy and model. Ordinal, run, text and count are excluded. The registry binding holds {chunkCount, wholeTextHash}.
  - Groups must contain exactly the ordinals 0 to count−1, once each. Every member is checked for model, dimension, text size and pointer before anything is written.
  - Missing old-style group markers make the run reject that group (group-binding-missing).
  - The renderer (DocumentRendering.scala:208-210) fills in the real chunk count and the hash of the text before chunking.
  - Tests through the real renderer cover shrink and grow, as do the storage tests. Both show 0 embedding calls and only the rejection report written.
- Spend gates:
  - The live guard tests never reach the client factory.
  - The templates are disabled (executionApproved:false, zero caps).
  - No secrets were found, and no region or model ID is hardcoded in main sources.
  - Generated state lives under the ignored target/ directory.
- Ownership: the work orders are separate per owner. The administrative fake was moved out without weakening the fence: rag/src/main is a fence root, and the in-memory graph loader stays out of runtime files.
- Live cost estimate: the hand-derived figure checks out: 1 × (0.01 × 3 + 0.01) + 0.10 = 0.14.

Findings

B1 — Medium — BLOCKING. The new local CLI path and the fifth document type's real-data path aren't covered by sbt check.
- Evidence:
  - EmbeddingIngestMain.run is only tested with refused arguments (EmbeddingRetrievalSpec.scala:135-138, IndependentEmbedding8BGuardSpec.scala:66-75).
  - Phase6EmbeddingSource.load is only tested on an empty export plus two rejection cases (EmbeddingGroupStateSpec.scala:181-277).
  - The literal end-to-end checks live in IndependentEmbeddingLocalReplayMain.scala and IndependentEmbeddingG1ExportMain.scala. These are main objects run by hand through runMain, not test suites, so check never runs them.
  - The G1 export has no topic or institution nodes (LocalReplayMain:61-62). So renderSource's node rendering (EmbeddingIngestMain.scala:102-143, tableTotalNodes plus topic/institution identity fields) has no automated test at all.
- Impact: These behaviors could break without any test failing:
  - the plan's 8B "Done when" property (a rerun gives identical counters);
  - the source reader's row selection, bounds, and provenance and logical-hash rejection on non-empty rows;
  - fifth-index rendering from real data.

  This also breaks the repository rule that every behavior change has feature tests. Making it a test is cheap: the G1 export takes about 22 s and the replay about 28 s.
- Owners:
  - test-engineer (tests/**): add a suite.
  - rag-engineer (modules/rag/src/test/**): add a node-rendering test.
  - storage-engineer: only if the owners decide reader rejection cases belong in the module.
- Acceptance check:
  a. A suite in check generates the G1 export in a temporary directory, runs EmbeddingIngestMain.run first, then replays on the same state, then runs on a fresh state. It asserts the literal results: 12 written, then 12 unchanged with 0 calls, identical fresh counters and manifest hash, every pointer and hash verified, and the qualifications hash.
  b. At least one non-empty reader rejection case, either a logical-hash mismatch or the scan cap below the row count, plus a check of the bounded round-robin selection.
  c. A RAG unit test over a synthetic batch with topic and institution nodes. It asserts the exact rendered fields, source refs and topicId/institutionId/sourceDataset identity fields, and that the table total isn't presented as a per-node count.

  Rerun the affected gates and the full JDK17 sbt check.

N9 — Medium — nonblocking; must be fixed before 8C. The live command has gaps in its input and its report.
- (a) No tool produces the real-model manifest. Only the local CLI writes manifests, and it always embeds with the fake client under the configured model (EmbeddingIngestMain.scala:196). Its own comment (line 10) and the RAG README say the model ID must describe the fake. Live preflight requires item.embeddingModel == config.model (LiveEmbeddingIngestMain.scala:174). So no supported path produces a manifest that passes live preflight, even though the README says to "render for the approved real model".
- (b) The live report is incomplete. It (LiveEmbeddingIngestMain.scala:331-351) leaves out model ID/version, per-index counts, rejection reasons and rejectedReportUri. Plan §7.5 and the course require these.
- (c) Future gate, not an 8B repair: there is no authored live query/latency smoke command for 8C task 2.
- Owner: rag-engineer.
- Acceptance check: a render-only manifest mode (no embedding, no state) using the live model and pointer config, plus the missing report fields, each with tests. Before 8C.

N10 — Low — nonblocking. A group binding can't be undone, even if nothing was ever written under it.
- Evidence: the binding is registered before any embedding (EmbeddingManifest.scala:~335-350).
- Impact: If that run then fails permanently, for example through a provider error or ledger outage, the binding stays. Any later corrected text for that entity is rejected in the same template/model namespace, even though no vector exists. This is consistent with the per-item binding design, and the runbook only partly discloses it.
- Owner: storage-engineer (README disclosure).

N11 — Low — nonblocking, future gate. The four summary types carry no sourceDataset filter.
- Evidence: they are left out on purpose for mixed exports (Phase6EmbeddingSource.scala:218-226), but the course's compact metadata lists source dataset.
- Owner: storage/rag. Disclose this in the 8C metadata-schema report.

N12 — Info. Two small hardcoded values: the CLI hardcodes "cosine" (EmbeddingIngestMain.scala:186) instead of the configured metric, and the window falls back to "all-years" (Phase6EmbeddingSource.scala:202).
- Owners: rag and storage.

N13 — Info. Evidence documents have small formatting and stale-status issues:
- In evidence/8b/agents.md:9, a blank line splits the table, like N8.
- commands.md:54 and repairs.md:62 still say "pending" next to later final results.
- Owner: coordinator.

N14 — Info. The smoke-test distractors in embedding-smoke.json share no content words with their queries, so they only weakly test lexical discrimination. This is already disclosed as fake-only behavior.

F1 and N1 stay FIXED. N2–N8 and R2–R3 remain OPEN, nonblocking and deferred. I'm not reopening them. R1 is verified FIXED.

3. Report fields

STATUS: COMPLETE (review) — verdict REQUEST-CHANGES
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Phase 8 Subphase 8B independent review per user-supplied prompt; base/HEAD 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e, branch phase-8, all 8B changes uncommitted
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only git status/diff vs 3c45de7; cmp + shasum of plan snapshot vs Drive source; shasum/size of /tmp/phase8b-final-check-1.txt and /tmp/phase8b-frozen-source.json; grep of raw log test totals; python -I rehash of source-files.json (30), frozen snapshot (254), g1/real/producer artifact inventories and replay raw logs; secret/hardcode greps; WebFetch of course README Phase 8. No build, test, AWS/provider call, data change, commit or reviewer launch.
TEST RESULTS: Not run by reviewer. Retained raw log independently confirms exit-success, 756 passed/0 failed (157/64/39/38/51/25/374/8), real 678.84 s. Targeted excerpts confirm core 13, storage 19, RAG 25, independent 39.
VALIDATION RESULTS: All hashes/inventories match; R1 verified FIXED; spend gates intact; one blocker B1 (CLI/source-reader/fifth-type CLI rendering untested in sbt check); nonblocking N9–N14.
ASSUMPTIONS: Retained /tmp raw logs are the outputs of the recorded commands; the real Phase 6 export under target/ is the Phase 6 retained run.
RISKS: CLI/reader regressions undetected by check (B1); 8C live packet lacks real-model manifest producer and full §7.5 report fields (N9); live compatibility, Titan quality, ≥10,000-vector corpus (real export has 100,765 summaries), latency, cost and cleanup unverified.
MANUAL ACTION REQUIRED: User pastes the NEXT PROMPT to the main agent; no commit until a subsequent APPROVE.
BLOCKED-ON OWNER: test-engineer and rag-engineer (B1); storage-engineer optional.
BLOCKED-ON EVIDENCE: B1 acceptance check plus rerun affected and full JDK17 sbt check.
NEXT GATE: 8B repair round 1, then user-launched recheck.

4. NEXT PROMPT

You are the Phase 8 coordinator for ScholarChain in
/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-8,
base/HEAD 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e, 8B changes uncommitted.
This is Subphase 8B REPAIR ROUND 1. Do only this repair, then stop.

Plan: /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase8.md
(snapshot docs/agent-runs/phase-08/evidence/8b/phase8-plan.md). Follow AGENTS.md,
CLAUDE.md, docs/agents.md and docs/agent-runs/README.md.

Step 0: ask the user any questions (with recommended defaults) or state
"No questions for this repair round", then proceed.

(a) Append the external reviewer's 8B verdict VERBATIM to
docs/agent-runs/phase-08/review.md under "Subphase 8B — user-supplied external
review". Log B1 (blocking) and N9–N14 (nonblocking) in repairs.md with owners.
F1/N1 stay FIXED; R1 is independently verified FIXED; N2–N8 and R2–R3 stay
OPEN/deferred. Do not repair deferred or nonblocking items unless the user asks.

(b) Route B1 by ownership in separate work orders:
 - test-engineer (tests/** only): turn the existing local-acceptance
   harness into a suite that runs in `sbt check`. It must generate the G1
   export in a temp dir via existing Phase 6 APIs (no target/ dependency), run
   EmbeddingIngestMain.run first → replay on the same state → fresh state, and
   assert literal expectations: 12 written; replay 12 unchanged, 0 embedding
   calls, 0 rejected; fresh counters identical; identical manifest hashes;
   every persisted pointer/hash resolves; qualifications hash verified. Add at
   least one non-empty source-reader rejection (e.g. logical-hash mismatch or
   scan cap below row count → exact rejection code) and assert the bounded
   round-robin selection (e.g. maxSummaries=4 → one per summary type).
 - rag-engineer (modules/rag/src/test/** only): unit-test
   EmbeddingIngestMain.renderSource for a synthetic EmbeddingSourceBatch with
   topic and institution nodes. Assert exact rendered fields
   (label, nodeClass, tableTotalNodes), source references, identity fields
   (topicId/institutionId/sourceDataset), the topic-institution-summary index,
   and that the table total is not presented as a per-node count.
 - storage-engineer: only if the owners decide a reader rejection case
   belongs in modules/storage/src/test/**.
 No production code changes unless a new test exposes a defect; route any
 such defect to its owner and report it.

(c) Rerun the affected targeted suites, then the full JDK 17 gate:
 export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
 export PATH="$JAVA_HOME/bin:$PATH"
 export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
 /usr/bin/time -p sbt -batch check > /tmp/phase8b-r1-final-check-1.txt 2>&1
 Keep the raw log outside Git. Record size, SHA256, exit, per-module counts,
 a line-numbered excerpt, the source-hash inventory and the frozen-file audit
 under docs/agent-runs/phase-08/evidence/8b-r1/. Report every failed attempt.

(d) Do not start 8C. 8C requires Phase 14 deployment, an AWS account, and a
human-written approval with caps; the user currently has no AWS account.
No AWS/provider calls, no live command execution, no commits/pushes, no edits
to human-decision records, and do not launch any reviewer.

(e) End with the handoff packet and a complete recheck reviewer prompt per
plan Section 10 in one fenced block. Include base/HEAD, the exact changed and
untracked inventory, commands/exit codes/test counts, raw-log SHA/size,
evidence paths, the B1 acceptance mapping and the retained dispositions.

(f) Stop and end the turn with: "Subphase 8B repair round 1 is ready for
review. I have stopped and will not start the next subphase until I receive
the next prompt."

This review is not human acceptance or instructor approval.

## Subphase 8B repair round 1 recheck — user-supplied external review

1. VERDICT: APPROVE for Subphase 8B repair round 1

  The blocker B1 and the extra repair N9 both meet the acceptance checks I set. The new tests really run in sbt check, and the evidence re-hashes byte for byte. Neither live command was run. I found five more items, none blocking. This recheck is not human acceptance or instructor approval.

  What I verified

  - Checkpoint: branch phase-8 at HEAD 3c45de74…. git status -uall shows 20 tracked changes and 119 untracked files, matching files.json exactly.
  - Inventories:
    - All 35 entries in source-files.json match on content, size and the base-commit hash, and they are exactly the changed implementation files.
    - All 8 entries in repair-files.json match.
    - Against the earlier 254-file 8B snapshot, only the 3 declared modified files changed.
  - Frozen snapshot: /tmp/phase8b-r1-frozen-source.json has SHA 633095b1…27ce, as recorded. All 346 files are unchanged, and no file in that scope is missing from it.
  - Plan copy: cmp of the snapshot against the Drive plan exits 0.
  - Full gate log: /tmp/phase8b-r1-final-check-1.txt is 1,520,049 bytes with SHA 3b5abff1…876f, both as recorded.
    - Module counts are 157/64/39/38/51/33/376/8, which sum to 766 with 0 failures. The run ends [success] with real time 695.67 s.
    - The only [error] lines (7064–7082) are the build's expected checkProbeInjectFailure self-test.
    - All four new or changed suites appear: EmbeddingSmokeGuardSpec (line 2166), Embedding8BRepairSpec (2181), IndependentEmbedding8BGuardSpec (2938) and IndependentEmbedding8BPipelineSpec (6477). Lines 7035 and 7037 show the G1 producer output and the passing case.
  - Targeted logs: all three re-hash correctly. Run 2 failed as recorded (OPENALEX vs openalex, Embedding8BRepairSpec.scala:114, 32 passed/1 failed). Run 3 passed.
  - Temporary output: the G1 temp directory named in final-audit.json no longer exists.
  - B1:
    - (a) Full local run is now a real test. The pipeline spec builds G1 in a temp directory through existing Phase 6 jobs. It asserts the literal values 10/9/18/28, then runs the actual CLI three times: first, replay from disk, then a fresh state. It checks 12 written, then 12 unchanged with 0 calls and 0 rejected. Counters and manifest hashes match across runs. It reopens every stored object and checks hash, pointer and context. It also checks the qualifications hash.
    - (b) Source reader on real rows. A scan cap of 1 is rejected as embedding-source-scan-limit. A summary cap of 4 picks one of each summary type in a literal order, and repeated loads give the same IDs and keys.
    - (c) Topic/institution rendering. The test compares exact bytes, exact source refs, the totals 17 and 23, the topic/institution IDs with sourceDataset=OPENALEX, and the topic-institution index.
  - N9:
    - (a) Render-only manifest command. EmbeddingManifestMain builds no embedder, no saved state and no SDK client. Its output passes the pure live preflight in both the module and G1 tests.
    - (b) Live report fields. LiveEmbeddingIngestMain.scala:217-248 adds model ID, version and dimension, per-index counts, rejections, and rejectedReportUri (null when absent).
    - (c) Query smoke command. It requires a separate query-smoke approval, checked before any client is built (LiveEmbeddingSmokeMain.scala:82-90, 325-337). Pointer scope is enforced and tested. I recomputed the test expectations by hand: estimated cost $0.24, p50 = 2 ms and p95 = 9 ms. The refusal tests confirm no client factory is ever called.
    - Templates: all are disabled. The live-config template is byte-identical to the 8B one.
  - Ownership: the work orders are separate per owner. rag-engineer wrote only modules/rag/**, test-engineer only tests/**, and the coordinator only evidence. review.md holds the prior verdict verbatim (SHA ef12bb6c… matches preflight.json), and repairs.md records the dispositions correctly.

  Findings (none blocking)

  N15 — Low — nonblocking, fix before 8C. A query-smoke approval has to carry ingest-sized caps.

  - Evidence: LiveEmbeddingSmokeMain.scala:96-99 reruns the full ingest preflight using a modified copy of the approval. The approval's embeddingCallCap and dollarCapUsd must therefore cover a full manifest ingest (items × attempts, plus storage), even though the smoke only makes queries × attempts embedding calls.
  - Impact: with a manifest of 10,000 or more vectors, a person approving only a query smoke has to sign caps sized for a full ingest. Spending is still limited by the query caps. The problem is that the approval document misstates what is being authorized. The runbook (live-runbook.md:31) only partly discloses this.
  - Owner: rag-engineer.
  - Acceptance check: for operation=query-smoke, validate the manifest and resources without the ingest call/cost checks. Add a test where a large manifest with small query caps is accepted.

  N16 — Low — nonblocking. The fake local CLI accepts a real model ID.
  - Evidence: the render-only command reuses LocalEmbeddingConfig, and render-config.template.json uses the Titan model ID. Nothing stops someone passing that config to EmbeddingIngestMain, which embeds with the fake (EmbeddingIngestMain.scala:196). The comment at line 10 ("fake model ID must describe the fake") is now stale.
  - Impact: local vectors and reports could carry the Titan label. This is local only, and reports still say mode=deterministic-fake.
  - Owner: rag-engineer.
  - Acceptance check: the fake CLI rejects known real-provider model IDs, or the comment and README are corrected.

  N17 — Low — nonblocking, future test gap. Reading topic/institution rows from an export is still untested in check.
  - Evidence: G1 has no topic or institution nodes (IndependentEmbeddingLocalReplayMain.scala:60-62). The new unit test uses a hand-built batch (Embedding8BRepairSpec.scala:46-63). Reading those rows from an actual export was only exercised by hand against the retained real export.
  - Owners: test-engineer, with storage-engineer if it belongs in the module.
  - Acceptance check: a small export fixture containing node tables, read through Phase6EmbeddingSource.

  N18 — Info. A smoke refusal test leaves its temp directory behind.
  - Evidence: EmbeddingSmokeGuardSpec.scala:215 never deletes its temp directory. I found 3 leftover embedding-smoke-refusal-* directories in the temp folder. They hold only synthetic files.
  - Owner: rag-engineer.

  N19 — Info. Some acceptance flags are written as literals.
  - Evidence: in IndependentEmbeddingLocalReplayMain.scala:144-158 the acceptance.json booleans are literals.
  - Impact: they are safe, because every require above them must pass first, and the pipeline spec re-checks the stored state independently.
  - Owner: test-engineer, optional.

  Dispositions:
  - B1 and N9 are FIXED. N9c is authored but unexecuted, so live results stay a gate for 8C.
  - F1, N1 and R1 remain FIXED.
  - N2–N8, R2–R3 and N10–N14 remain OPEN, nonblocking and deferred.
  - N15–N19 are new, OPEN and nonblocking. N15 should be resolved before 8C.
  - Still unverified and left to 8C: whether the live services work end to end, retrieval quality, the 10,000-vector corpus, latency, cost and cleanup.

  3. Report fields

  STATUS: COMPLETE (recheck) — verdict APPROVE for 8B repair round 1
  OWNER: code-reviewer (user-launched, read-only)
  WORK ORDER: Phase 8 Subphase 8B repair round 1 recheck (B1 blocking + user-requested N9); base/HEAD 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e, branch phase-8, all changes uncommitted
  FILES CREATED: none
  FILES MODIFIED: none
  COMMANDS RUN: read-only git rev-parse/status -uall/diff --stat vs 3c45de7; shasum/size of /tmp/phase8b-r1-final-check-1.txt, targeted-1/2/3 logs and /tmp/phase8b-r1-frozen-source.json; python -I rehash of repair-files.json (8), source-files.json (35 incl. git base hashes), frozen snapshot (346), prior 254-file snapshot; files.json vs git status; cmp of plan snapshot; grep of raw log for suites/totals/errors; source reads; ls of temp paths. No build, test, AWS/provider call, data change, commit or reviewer launch.
  TEST RESULTS: Not run by reviewer. Raw log independently confirms exit success, 766 passed/0 failed (157/64/39/38/51/33/376/8), real 695.67 s; all four new/changed suites discovered; targeted-2 failure and targeted-3 pass confirmed from raw logs.
  VALIDATION RESULTS: All hashes/inventories match; B1 and N9 acceptance met; spend gates intact; neither live entrypoint executed; templates disabled; new nonblocking N15–N19.
  ASSUMPTIONS: Retained /tmp raw logs are outputs of the recorded commands; the plan snapshot is the governing plan.
  RISKS: Query-smoke approval semantics over-broad (N15); fake CLI accepts real model ID (N16); node-table reading untested in check (N17); all live behavior, quality, ≥10,000 corpus, latency, cost and cleanup unverified until 8C.
  MANUAL ACTION REQUIRED: User reviews the diff and decides on the commit gate; 8C requires a new prompt, Phase 14 deployment, an AWS account and human-written approvals/caps.
  BLOCKED-ON OWNER: none for 8B.
  BLOCKED-ON EVIDENCE: none for 8B; 8C live evidence is a future gate.
  NEXT GATE: Record recheck verdict, then user commit gate for 8B.

  4. NEXT PROMPT

  You are the Phase 8 coordinator for ScholarChain in
  /Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-8,
  base/HEAD 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e, all 8B work uncommitted.
  This step only records the 8B repair-round-1 recheck and prepares the user
  commit gate. Follow AGENTS.md, CLAUDE.md, docs/agents.md and
  docs/agent-runs/README.md.

  Step 0: ask the user any questions (with recommended defaults) or state
  "No questions for this step", then proceed.

  (a) Append the external recheck verdict VERBATIM to
  docs/agent-runs/phase-08/review.md under
  "Subphase 8B repair round 1 recheck — user-supplied external review"
  (APPROVE). Retain a copy at docs/agent-runs/phase-08/evidence/8b-r1/
  external-recheck.txt and record its SHA256.

  (b) Update repairs.md dispositions only (coordinator evidence):
   - B1 FIXED (independently verified). N9 FIXED; N9c authored/unexecuted,
     live results remain an 8C gate.
   - F1/N1/R1 remain FIXED. N2–N8, R2–R3, N10–N14 remain OPEN/nonblocking/
   live results remain an 8C gate.
 - F1/N1/R1 remain FIXED. N2–N8, R2–R3, N10–N14 remain OPEN/nonblocking/
   deferred.
 - Add N15 (low; query-smoke approval must carry ingest-scale caps;
   rag-engineer; resolve before 8C), N16 (low; fake CLI accepts real model
   ID / stale comment EmbeddingIngestMain.scala:10; rag-engineer),
   N17 (low; Phase6EmbeddingSource node-table read path untested in check;
   test-engineer/storage-engineer), N18 (info; EmbeddingSmokeGuardSpec
   temp dir not deleted; rag-engineer), N19 (info; literal acceptance
   booleans in IndependentEmbeddingLocalReplayMain; test-engineer) as
   OPEN/nonblocking. Do not repair any of them in this step.

(c) User commit gate: do NOT commit or push. Present the exact proposed
commit inventory (20 tracked + 119 untracked from evidence/8b-r1/files.json,
plus only the evidence files changed in this step), confirm no secrets,
target/ or /tmp artifacts are included, and propose a commit message.
Re-verify that all 35 source-files.json hashes and the 346-file frozen
snapshot still match (read-only hashing; no build needed because no source
changes are allowed in this step). Wait for the user's explicit
human-written commit decision.

(d) Do not start 8C. 8C requires a new user prompt, Phase 14 deployment,
an AWS account and actual human-written approvals/caps; the user has no AWS
account. No AWS/provider calls, no live or smoke command execution, no
source edits, no edits to human-decision records, and do not launch any
reviewer.

(e) End with the handoff packet and stop with: "Subphase 8B is recorded as
independently approved and awaits the user commit gate. I have stopped and
will not commit, push or start the next subphase until I receive the next
prompt."

This recheck is not human acceptance or instructor approval.

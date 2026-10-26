# Subphase 9A

No user-supplied external review has been received. No reviewer was launched by the coordinator.
This file records no approval or self-review verdict. The user launches the independent read-only
review after receiving the completed9A handoff; its verdict is appended verbatim only when supplied.

## Subphase 9A

user-supplied external review (initial)

Subphase 9A review: REQUEST-CHANGES

1. VERDICT: REQUEST-CHANGES

The packet is honest and the evidence checks out:
- All 31 source hashes match source-files.json.
- The SHA-256 of each raw /tmp log (targeted-all-1, check-1, check-2) matches its result JSON.
- The inventory is complete and ownership matches docs/agents.md.
- No live calls, infrastructure changes, secrets or human-gate edits were found.
- Frozen wire examples are unchanged.
- ABSTAINED is kept and decimal strings preserve exact numbers.
- The Bedrock adapter forces the named tool.
- Deadlines fit: the critical path is 22,000 ms against a 30,000 ms synchronous deadline.

Four defects block approval. Two are in the planner/resolver logic that 9A owns, one is in the storage-to-resolver contract, and one is a per-read cost problem. The fixture-scale tests don't reach any of them.

One note: the pasted prompt was cut off partway through the REQUEST-CHANGES instructions. I completed the NEXT PROMPT using the plan's Section 10 template.

2. Findings

Blocking

B1 · High · Planner metric/measure/window preservation is only enforced for distinct-coauthor rankings
- Where: modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/QueryPlannerAgent.scala:219-249, :195-204, :259
- Evidence: The only metric guard (:222-229) fires when the question contains "distinct coauthors". requiredOperations (:230-236) has no team-size entry. Schema-valid model output gets through in these cases:
  - "Which researchers have the largest team size?" with the model's {RESEARCHER_RANKING, DISTINCT_COAUTHOR_COUNT} is accepted. Every word is in the coverage vocabulary.
  - "Rank researchers by coreness", "…weighted degree" or "…publication count": the model can switch the metric.
  - "Rank bridge researchers by participation coefficient" with model rankingMeasure: null is silently defaulted to CROSS_COMMUNITY_DEGREE (:243-244). In the other direction, "strongest bridges" with a model-chosen PARTICIPATION_COEFFICIENT overrides the default the user chose in answer 6.
  - "…since 2015" with model window 2015-2019 passes, because the years {2015} are a subset of {2015, 2019} (:195-204). This drops 2020–2026. A question naming no window can be narrowed to any stored window the model picks.
  - authorCountConversion is copied from the model without checking the question (:259).
- Impact: The planner can answer a different question than the one asked. This contradicts plan §4 ("rank by the metric the question names"), user answers 6 and 9, and the rag README claims. Tests only cover the distinct-coauthor case (Runtime9ASpec.scala:173-177, IndependentRuntime9APlannerSpec.scala:138,177).
- Owner: rag-engineer (module tests); test-engineer (independent tests)
- Acceptance:
  - Each recognized metric/measure phrase maps deterministically to a required metric/measure, and a model value that disagrees is rejected (retry → fallback/Unsupported).
  - An unspecified bridge measure is forced to the configured default.
  - The window must be an explicitly named window, a uniquely mapped phrase, or the default when the question names none. "since 2015" can never become 2015-2019.
  - Conversion is true only when the question explicitly asks for total authors.
  - Hand-derived tests cover each case.
- Blocking: yes

B2 · High · Resolver candidate bound counts raw cache rows, not canonical identities
- Where: modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/ResearcherResolverAgent.scala:62-63
- Evidence: Phase6CacheLoader writes one name row per researcher node plus one per resolves_to mention edge (Phase6CacheLoader.scala:284-323). Phase 6 emits one RESOLVES_TO per author mention (Phase6CJobs.scala:737-745). 9A adds base-name alias rows for suffixed researchers (:299-304), which collect under the base name.
- Impact:
  - Any researcher with roughly 25 or more cached rows (about 24+ mentions) returns Failed("resolver-candidate-bound"), even when there is a single canonical ID.
  - The plan's own "Wei Wang" common-name case fails instead of returning Ambiguous with candidates. That breaks "abstains with the candidate list".
  - sourceIds/evidenceRefs grow with every mention.
  - G1 and the synthetic fixtures are too small to show this.
- Owner: rag-engineer. If the candidate record needs a truncation field, domain-engineer adds it as a contract gap.
- Acceptance:
  - Bound by distinct canonical IDs, using a dedicated configured cap with a stated rationale.
  - Bound the per-candidate source/evidence lists and disclose truncation.
  - When distinct IDs exceed the cap, return Ambiguous with a bounded list plus a truncation/total disclosure, never Failed.
  - Tests: one ID with more rows than the cap resolves; more distinct IDs than the cap gives a truncated Ambiguous.
- Blocking: yes

B3 · Medium-High · Resolution fails when a candidate is absent from the plan's stored window
- Where: modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/RuntimeArtifacts.scala:384-386; ResearcherResolverAgent.scala:103-104
- Evidence: researcherContext returns Rejected("unsupported-runtime-window") for a stored window when the researcher simply has no metric row there. Spark windows legitimately omit researchers; that is what TemporalChange.fromPresent/toPresent record. The resolver turns that into Failed("resolver-context-unavailable"). The resolver tests use a stub that always returns Found (Runtime9ASpec.scala:329-348).
- Impact: With artifacts composed:
  - "direct coauthors of X window 2020-2026", where X published only before 2020, fails.
  - An ambiguous name where one homonym is absent from the window fails instead of returning Ambiguous.
  - Identity resolution becomes window-dependent.
- Owner: storage-engineer (tell a non-stored window apart from a known researcher absent in a stored window); rag-engineer (absent context must never fail identity). domain-engineer only if a contract field is needed.
- Acceptance: Using the real InMemoryRuntimeArtifactStore:
  - A researcher absent from a stored window → Resolved with absent or empty context.
  - An ambiguous name with one absent homonym → Ambiguous with both candidates.
  - An unknown window is still rejected.
- Blocking: yes

B4 · Medium · Every artifact read re-fetches, re-parses and fully re-validates the whole snapshot
- Where: RuntimeArtifacts.scala:580-597, plus :460-568 and :248-262
- Evidence:
  - Each port call does a full GET of an object up to 16 MiB, parses it, re-hashes every table, and runs O(edges×supports) binding loops (:553-568).
  - association() scans every edge for each researcher inside rank.
  - The resolver calls researcherContext once per candidate inside resolverMs = 2,000 ms. 9B stages will call it repeatedly.
  - The pointer is immutable and SHA-bound, so caching the verified snapshot is safe.
- Impact: At the documented caps, deadlines will plausibly run out and turn into typed failures. This is not measured. User answer 4 limits storage work in 9B/9C to contract gaps, so 9B cannot fix this.
- Owner: storage-engineer
- Acceptance:
  - Verify once per pointer and reuse the snapshot, with precomputed indexes.
  - A test shows a second read performs no object GET or re-validation.
  - Corruption is still rejected on first load.
- Blocking: yes. If the user explicitly chooses to defer it, it becomes nonblocking.

Nonblocking (record and carry forward)

- N1 · Medium · Vector-mode check uses IDs only. RuntimeContracts.scala:255-271 checks the deterministic/semantic partition by ID only. A vector-mode bundle can list a descriptive=false metric item as "semantic" and pass validation (test at RuntimeContractSpec.scala:156-181). domain-engineer should cross-check item runtime.descriptive/evidenceType as a 9B contract gap before the EvidenceBuilder is accepted.
- N2 · Low-Medium · Filtered rankings will mostly be Unsupported on real data. RuntimeArtifacts.scala:303-307 requires association coverage for every researcher in the window. Real topic/institution/venue enrichment will rarely be complete, so filtered rankings will mostly return Unsupported outside the synthetic fixtures. This is consistent with answer 5 and documented. The user should confirm it before 9C presents filter benchmarks as representative.
- N3 · Low · maxInputBytes (16,384) does four jobs. It bounds the question, the prompt files, the total request and the output. A full 4,096-token synthesis context plus the schema will exceed it in 9C. Revisit the config there.
- N4 · Low · Region is never checked. RuntimeLlm.scala:66-72 never compares config.model.region with the injected client's region, so an audit could record a region that wasn't used. This is a live-gate item.
- N5 · Low · Confidence is only exercised on synthetic rows. The real loader writes confidence = None (Phase6CacheLoader.scala:294), and the resolver sets it to None when rows disagree (ResearcherResolverAgent.scala:107-110). Disclose this.
- N6 · Low · Prompt file names are fixed. RuntimeSchemas.scala:130-133 hard-codes the *-v1 file names. A v2 config fails closed instead of loading v2.
- N7 · Low · Some context refs are unbounded. researcherContext bounds coauthors but returns every authored and association ref (RuntimeArtifacts.scala:407-430). Only the snapshot cap bounds them.

Not verified (live or future gates)

- Bedrock model/tool/region compatibility, temperature acceptance, and live quality and injection resistance.
- 9B retrieval, evidence and workflow; 9C synthesis, verifier, audit, CLI and benchmark.
- Phase 8C stays deferred to 14C. This review doesn't accept Phase 8 as a whole.

3. Report fields

STATUS: COMPLETE (review); verdict REQUEST-CHANGES for Subphase 9A
OWNER: code-reviewer (independent, user-launched, read-only)
WORK ORDER: Phase 9 Subphase 9A initial review (pasted prompt; REQUEST-CHANGES branch
  of NEXT PROMPT completed from phase9.md Section 10 because the paste was truncated)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only only — git status/diff/rev-parse/check-ignore; cat/sed/grep/wc
  on repo, plan, prompts and evidence; diff -q plan-of-record vs Drive plan (identical);
  shasum -a 256 on /tmp/phase9a-{targeted-all-1,check-1,check-2}.log (all match recorded
  hashes); python3 -I SHA-256 check of 31 files in source-files.json (31 checked, 0 mismatch);
  secret/AWS-literal grep over changed files (no findings). No sbt, AWS, provider or git writes.
TEST RESULTS: not run by reviewer. Retained evidence consistent: targeted 70/70; check-1
  exit 1 (397/398 independent); loader repair 5/5; check-2 exit 0, 831 passed, 0 failed.
VALIDATION RESULTS: ownership OK; evidence honest; contracts additive with ABSTAINED kept;
  4 blocking defects (B1–B4), 7 nonblocking (N1–N7).
ASSUMPTIONS: real Phase 6 exports emit one RESOLVES_TO per author mention (Phase6CJobs.scala:737-745)
  and windows omit researchers without works there (spark README §temporal). B4 latency impact
  is reasoned, not measured.
RISKS: B1–B3 yield wrong-question plans or Failed instead of Ambiguous on real data; B4 may
  exhaust stage deadlines; fixture-scale tests cannot detect any of these.
MANUAL ACTION REQUIRED: user pastes NEXT PROMPT; user decides whether B4 may be deferred;
  user owns Phase 8 interim human-gate and all commits.
BLOCKED-ON OWNER: rag-engineer (B1, B2, B3 resolver part); storage-engineer (B3 store part, B4);
  test-engineer (independent tests for B1–B3); domain-engineer only if a contract field is required.
BLOCKED-ON EVIDENCE: findings B1–B4 above with path:line.
NEXT GATE: repair round 1 for B1–B4, targeted tests + full sbt check on JDK 17, then
  user-launched recheck review. No 9B work.

## Subphase 9A repair round 1

user-supplied external review

ubphase 9A repair round 1 review: APPROVE

1. VERDICT: APPROVE

All four blocking findings (B1–B4) are fixed, and I found no new blockers. The evidence checks out:
- All 34 cumulative source hashes and all 16 repair "after" hashes match the files on disk.
- The SHA-256 of /tmp/phase9a-r1-check-1.log (a0ba6005…) and of the independent-target log (7b33fd0a…) match their result records.
- The full-check module counts add up to 901, with no *** FAILED lines in the raw log. The only error lines are the expected injected-failure self-test, and the TestRunMarker ran.
- git diff --check exits 0, HEAD is still the base 5fee9ff, and the untracked inventory matches files.json.
- Ownership in delegation.md and source-audit.json follows docs/agents.md.
- The external review copy in review.md matches external-review.txt, whose SHA-256 is bound.

2. Findings

B1–B4: all fixed

B1 · FIXED · Planner grounds metric, measure, operation, window and conversion in the question
- QueryPlannerAgent.scala:46-171 now works out the question's intent without looking at the model's answer:
  - every metric phrase in the question, including largest/maximum team size, coreness, weighted degree, publication count and average coauthors;
  - bridge measures, with the default taken from config only when no measure is named;
  - repeated collaboration, mapped to JOINT_PUBLICATION_COUNT;
  - exact ordered windows and comparisons;
  - total-author conversion, only when the question asks for it.
- :331-351 rejects any model output that disagrees, so it goes to retry, then fallback, then Unsupported.
- "since 2015" can only map to a window that starts in 2015 and ends at the latest configured end year, which means since-2015. A stray year left over after the window phrases are removed is rejected.
- The fallback runs through the same decoder, so it obeys the same rules.
- Tests: each phrasing is a positive case that succeeds on the first call, paired with a substitution negative. Alternate configured defaults for the bridge measure and for the window are also tested (IndependentRuntime9ARepairPlannerSpec.scala:115-290), so a planner that returned Unsupported for everything could not pass.

B2 · FIXED · Resolver caps distinct canonical identities, not raw rows
- ResearcherResolverAgent.scala:79-81 groups rows by canonical ID before applying the cap. The cap is the new dedicated resolver.maxDistinctCandidates, separate from graphLimit, with its rationale in the core README (:309-321).
- Each provenance list is bounded, and an additive ResearcherCandidateProvenanceSummary records the totals and a truncation flag. That summary is validated (RuntimeContracts.scala:233-246, called at resolver :142).
- Overflow returns Ambiguous with totalCandidateCount and truncated set, not a failure (:148-154).
- Tests: one identity with many observations resolves; 5 identities against a cap of 2 return a truncated Ambiguous with exact counts.

B3 · FIXED · A researcher absent from a stored window no longer breaks resolution
- RuntimeArtifacts.scala:417-418: an undeclared window is still Rejected. A known researcher with no row in a stored window now returns Missing.
- The resolver treats Missing as "no context" (:109).
- Tests run against the real artifact fake:
  - an absent identity still comes back Resolved;
  - a homonym absent from the window is still included in Ambiguous;
  - an unknown window is still rejected.

B4 · FIXED · Snapshot is verified once per reader and indexed
- The verified snapshot is cached per reader instance under a lock, and only successful loads are cached (RuntimeArtifacts.scala:606-638).
- Keyed indexes replace the full-table scans (:244-283). The checks that tie edges, supports and bridges together now use maps and sets instead of nested loops (:560-590).
- Storage tests cover:
  - warm reads on all six ports making no further GET;
  - concurrent cold reads sharing one GET;
  - failures on first load (throttled, missing, corrupt) not being cached and succeeding on retry.
- No production latency was measured, and the evidence correctly says so.

New nonblocking observations

- N8 · Low · The stricter grammar rejects some natural phrasings. QueryPlannerAgent.scala:103-106,154-159:
  - Community comparison is recognized only from the literal phrases "community comparison" and "compare communities".
  - A temporal question needs the word "temporal", or "compare"/"comparison" with two windows. "How did X change from 2010-2014 to 2015-2019?" returns Unsupported.

  These fail closed, so it's a coverage gap, not a correctness bug. Before 9C writes its benchmark questions, rag-engineer should either extend the grammar (it owns this file) or match the benchmark wording to it.
- N9 · Low · Stale opening line in review.md. It still starts with "No user-supplied external review has been received", directly above the appended review. The coordinator should append a dated clarification rather than rewrite that line.
- N1–N7 stay open and deferred, as logged in repairs.md. N1 (checking that the vector-mode semantic partition matches each item's descriptive flag and type) has to be settled as a domain contract gap before the 9B EvidenceBuilder can be accepted.

Not verified (live or future gates)

- Live model, tool, region, temperature, quality and injection behaviour.
- Production artifact latency.
- Every 9B and 9C stage.
- Phase 8C stays deferred to 14C.

3. Report fields

STATUS: COMPLETE (review); verdict APPROVE for Subphase 9A repair round 1
OWNER: code-reviewer (independent, user-launched, read-only)
WORK ORDER: Phase 9 Subphase 9A repair round 1 recheck (pasted prompt)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only only — git rev-parse/branch/status/diff --check; cat/sed/grep/wc over
  evidence/9a-r1, review.md, repairs.md and repaired sources/tests; shasum -a 256 on
  /tmp/phase9a-r1-check-1.log and /tmp/phase9a-r1-independent-targeted-1.log (both match);
  python3 -I SHA-256 check of source-files.json (34/34 match) and repair-files.json (16/16 match);
  inventory comparison (match, sort-order only); grep of raw full-check log for failures (none
  beyond the expected injected probe). No sbt, AWS, provider or git writes.
TEST RESULTS: not run by reviewer. Retained: targeted core 21, storage 15, RAG 40 (after one
  test-compile failure fixed in a test helper), independent 64 = 140 passed; full check exit 0,
  901 passed, 0 failed, 725.07 s.
VALIDATION RESULTS: B1–B4 FIXED; no new blockers; N8–N9 new nonblocking; N1–N7 remain deferred.
ASSUMPTIONS: B4 is a structural improvement; latency remains unmeasured as disclosed.
RISKS: conservative planner grammar (N8); the resolver still loads every cache row for a name
  before grouping (bounded only by the cache partition); live behaviour unverified.
MANUAL ACTION REQUIRED: user commits Subphase 9A (agents must not); user owns the Phase 8
  interim human gate.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none
NEXT GATE: user commit of 9A, then Subphase 9B Step 0 questions.

### Dated clarification — 2026-10-26 (N9)

The opening statement "No user-supplied external review has been received" records the
initial pre-review state. It predates the appended initial REQUEST-CHANGES and this
repair-round-1 APPROVE. The opening and earlier review text are preserved unchanged.

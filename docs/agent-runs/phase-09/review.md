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


## Subphase 9B

user-supplied external review

Subphase 9B review: REQUEST-CHANGES

1. VERDICT: REQUEST-CHANGES

There is one blocking defect: a researcher's exact stored metrics are marked approximate on real data. Everything else in the review focus checks out. The evidence record is honest:
- Hashes: all 22 source hashes match. All 9 raw-log SHA-256 bindings match /tmp. The plan hash matches.
- Counts: the full log shows 196+64+39+38+66+88+502+8 = 1001 passed, with no *** FAILED lines. The only error is the expected injected format-stage probe, and TestRunMarker ran.
- Scope: HEAD is f139f9c. Ownership is clean, and there are no storage, build or infra changes.

2. Findings

B1 · Medium · BLOCKING · Exact metrics are flagged approximate whenever a P90 estimate exists

- Where: modules/rag/.../CollaborationMetricsAgent.scala:117-123. The test that encodes the behaviour is tests/.../IndependentRuntime9BStagesSpec.scala:116.
- What happens: when the metric record's qualifications contain a pathLengthEstimate, the agent rebinds the whole metric item with approximate = true. That item also holds exact stored values: publicationCount, distinctCoauthorCount, totalCoauthorOccurrences, weightedDegree, maximumCoauthorsOnOnePaper and coreness. approximate is a single item-level flag, so it qualifies every value in the item.
- Why it hits real data: Phase6CacheLoader.scala:349-352 writes pathLengthEstimate into every researcher's record whenever their component has an estimate. Most named-researcher lookups on real data will therefore come back approximate.
- Inconsistency: the ranking path never adds P90. The same researcher, window and run gets approximate=false in a ranking and approximate=true in a named lookup.
- Impact: this contradicts plan §7.2.3 ("returns exact stored values") and decision 6 (label only the distance P90 approximate). The ambiguity goes into immutable, content-bound evidence and into the rendered context ("approximate": true). 9C templates and the verifier would then either mislabel exact counts or have to ignore the contract flag.
- Owners: rag-engineer for production code and the module test; test-engineer for the independent test.
- Acceptance check:
  a. The exact metric item keeps approximate=false and identical exact values whether or not an estimate exists.
  b. The stored P90 is emitted unambiguously, as a separate evidence item with approximate=true, bound to its component, window, run, method and source reference. It stays deterministic and is atomic with the metric request.
  c. The named-lookup and ranking items for the same researcher, window and run agree on the exact values and on approximate=false.
  d. Hand-derived tests are updated in the module spec and in IndependentRuntime9BStagesSpec (the P90 case asserts that the metric item is not approximate and the estimate item is).
  e. No iteration-limited labeling is weakened. The default four-hop path and ranking workflows still pass.

Nonblocking observations (log only; not required in 9B)

- O1 · Medium · Convergence flags have the same scope problem. Item-level converged/iterations qualify mixed items:
  - Metric items take them from the community membership (RuntimeRetrieval.scala:192-193).
  - Temporal items take converged=forall across both windows, while also holding exact coauthor deltas (CommunityAnalystAgent.scala:153-154).
  - "Iteration-limited" therefore also covers exact P/C/T values. Either split these the same way as B1, or have the 9C verifier scope the qualifier to community-derived fields. Owner: rag-engineer.
- O2 · Medium · Mixed provenance on evidence items. Item provenance copies the caller/plan provenance (source, datasetSnapshot, retrievalDate, license, sourceUri) and overwrites only runId with the source run (RuntimeRetrieval.scala:150-155). The resulting record mixes request and source lineage. Content-bound IDs for the same stored fact also change with request provenance. Resolve before the 9C audit or the Phase 10 evidence endpoint exposes it. Owner: rag-engineer.
- O3 · Medium · bundle.researcherIds includes identities picked by semantic similarity. It unions in the subject IDs of semantic hits (EvidenceBuilderAgent.scala:120-122). A vector-mode bundle can therefore list a researcher chosen only by similarity. 9C must use resolvedCandidates plus deterministic subjects for identity checks and the audit's "resolved researcher IDs", or restrict this field. Owner: rag-engineer.
- O4 · Low-Medium · Semantic retrieval ignores resolved candidates. It filters only by window, topic and institution, with no entityId filter (SemanticContextAgent.scala:23-24). A named-researcher explanation can return other researchers' profiles. Owner: rag-engineer.
- O5 · Low-Medium · Larger atomic groups abstain at the default 4,096-byte context budget. This is disclosed:
  - A direct-coauthor result can carry up to 25 edge items, and community comparisons are similar; both abstain for realistic degrees.
  - Every ranking row repeats the full sourceRankingScope string (CollaborationMetricsAgent.scala:59, CommunityAnalystAgent.scala:63). That cuts the default G1 ranking below 10 of 10 rows.
  - Consider disclosed prefixes for lists and deduplicating the scope string. Owner: rag-engineer, in 9C or 11.
- O6 · Low · Ranking prefix ignores the byte bound. Prefix selection checks only the context bound. The persisted maxInputBytes check (EvidenceBuilderAgent.scala:130-131) can abstain on a ranking whose shorter prefix would fit, unlike the README's "largest admitted prefix".
- O7 · Low · ExceededMaxHops is unreachable with the shipped adapters. It is produced only from Rejected("exceeded-maxHops"), which neither graph adapter emits. A same-component empty search is reported as NoPathWithinLimit; Phase 6 calls that case exceeded-maxHops. This is allowed by decision 8, but 9C benchmark wording should match.
- O8 · Low · The deterministic partition admits RESEARCHER_PROFILE items with excerpt text. bundleItems (RuntimeContracts.scala:338-356) accepts RESEARCHER_PROFILE items with descriptive=false and a text excerpt. Community, bridge, temporal, path-status and direct-coauthor facts all default to RESEARCHER_PROFILE (RuntimeRetrieval.scala:130). Hardening: require deterministic items to carry text=None. Owner: domain-engineer.
- O9 · Low · Path-status items lose their researcher pair in the prompt context. Rendering drops subjects for all "path"-kind items (RuntimeRetrieval.scala:276-279), so Disconnected and NoPathWithinLimit statuses are not tied to the pair in the context. The persisted item keeps them.
- O10 · Low · The population-filter test can't tell filter-then-rank from rank-then-filter. Its limit of 25 exceeds the population (IndependentRuntime9BStagesSpec.scala:139-156). Add a filtered case with limit=2. Owner: test-engineer.
- N1 is confirmed fixed. Actual-item type, descriptive flag and payload checks are enforced; legacy runtime-less bundles are unchanged; the tests discriminate. N2–N9 remain carried forward. Nothing new is confirmed against them except the O-items above.

Not verified (live or future gates)

- Live provider, model, region and injection behaviour.
- Production latency, and adapters that ignore interruption.
- Real enrichment coverage.
- All 9C work.
- Phase 8C stays deferred to 14C.
- I did not re-fetch the course README; I relied on the plan sections and authority-reading.md.

3. Report fields

STATUS: COMPLETE (review); verdict REQUEST-CHANGES for Subphase 9B
OWNER: code-reviewer (independent, user-launched, read-only)
WORK ORDER: Phase 9 Subphase 9B review (pasted prompt)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only only — git rev-parse/status/diff f139f9c; cat/sed/grep/wc over evidence/9b,
  phase-09 reports, 9A answers/recheck, core/rag/storage/spark sources and 9B tests; python3 -I
  SHA-256 of 22 source-files.json entries (22/22 match), 9 raw /tmp logs (9/9 match), plan (match);
  grep of /tmp/phase9b-check-1.log (0 "*** FAILED"; module counts sum to 1001; expected probe only;
  TestRunMarker ran). No sbt, AWS, provider, network or git writes.
TEST RESULTS: not run by reviewer. Retained: targeted core 39 + storage 15 + RAG 15 + independent 66
  = 135 passed; full check exit 0, 1001 passed, 0 failed, 707.18 s (JDK 17.0.20.1).
VALIDATION RESULTS: B1 blocking; N1 confirmed fixed; O1–O10 nonblocking; N2–N9 carried forward.
ASSUMPTIONS: Phase 6 export provides pathLengthEstimate for most components (per Phase6CacheLoader).
RISKS: qualification-scope ambiguity (B1/O1), mixed provenance (O2), similarity-derived researcherIds (O3).
MANUAL ACTION REQUIRED: user relays the next prompt; no commit of 9B until a recheck approves.
BLOCKED-ON OWNER: rag-engineer, test-engineer (B1)
BLOCKED-ON EVIDENCE: B1 repair plus affected targets and full JDK 17 check
NEXT GATE: 9B repair round 1, then user-launched recheck

4. Next prompt

You are the ScholarChain Phase 9 coordinator in a fresh session at
/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-9, base/HEAD
f139f9c925b4925864a2c9a33734d869a1929cd2. Subphase 9B changes are uncommitted.
The independent read-only review of Subphase 9B returned REQUEST-CHANGES.

Read first: AGENTS.md, CLAUDE.md, docs/agents.md, docs/agent-runs/README.md, the plan of record
/Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase9.md
(Sections 3–8 9B, 9, 10), docs/agent-runs/phase-09/evidence/9b/ and
docs/agent-runs/phase-09/evidence/9a/user-answers.md (ten original decisions, binding).

Step 1 — Record the review. Append the reviewer's verdict verbatim (the user supplies the full text)
to docs/agent-runs/phase-09/review.md under a new heading "## Subphase 9B", marked
"user-supplied external review". Do not alter earlier text. Store an identical copy at
docs/agent-runs/phase-09/evidence/9b-r1/external-review.txt with its SHA-256. Log B1 and O1–O10 in
repairs.md under "Subphase 9B repair round 1" (B1 routed; O1–O10 logged nonblocking).

Step 2 — Repair only B1, routed by docs/agents.md:
- rag-engineer (modules/rag/** only): in CollaborationMetricsAgent, the exact metric item must keep
  approximate=false and identical exact values whether or not a pathLengthEstimate exists. Emit the
  stored P90 unambiguously as a separate deterministic evidence item with approximate=true, bound to
  componentId, window, source run, method and source reference, content-bound via
  RuntimeEvidenceIds.bind. Keep it atomic with the metric request in the builder. Named-lookup and
  ranking items for the same researcher/window/run must agree on exact values and approximate=false.
  Update the module spec with hand-derived assertions and modules/rag/README.md wording.
- test-engineer (tests/** only): update IndependentRuntime9BStagesSpec P90 case so it asserts that
  the metric item is NOT approximate and the separate estimate item IS approximate, with
  effectiveDiameterP90 4.0, method sampled-bfs, matching component/window/run. Do not weaken any
  other assertion.
- domain-engineer only if a proven contract gap appears (return BLOCKED-ON with evidence first).
Do not weaken iteration-limited labeling, N1 partition checks, budgets or existing assertions.
O1–O10 are optional; implement none unless the user asks. No 9C work.

Step 3 — Gates, serialized by the coordinator, every sbt command with:
  export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  export PATH="$JAVA_HOME/bin:$PATH"
  export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
Record java -version. Run touched-project scalafmt, then targeted:
  /usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeArtifactStorageSpec' 'rag/testOnly *Runtime9BSpec' 'independentTests/testOnly *Runtime9B* *Runtime9AEvidenceSpec'
(add core targets only if core changes), then the full
  /usr/bin/time -p sbt -batch check
and git diff --check. Retain every failed attempt honestly. Write lean evidence to
docs/agent-runs/phase-09/evidence/9b-r1/: commands, exits, counts, raw-log paths and SHA-256,
repair-files.json (before/after hashes), a refreshed cumulative source-files.json for all changed
9B source/test/module-doc paths, files.json inventory, and owner reports. Append 9B repair-round-1
sections to owner-report.md and test-report.md. Verify that previously reviewed 9A paths are unchanged.

Rules: no commits/pushes, no AWS/provider/live calls, no infrastructure, no secret reads, no
human-gate edits, no nested delegation, never launch a reviewer. Preserve all ten original decisions
and the 9B Step 0 defaults; N2–N9 stay carried forward; Phase 8C stays deferred to 14C.

Step 4 — Stop. Ensure no specialists or builds are running. Return the handoff packet and a complete
recheck reviewer prompt in one fenced block (Subphase 9B repair round 1; checkpoint facts filled
with real values; review focus: B1 fixed without regressions, unchanged other 9B behavior, evidence
honesty; return APPROVE or REQUEST-CHANGES plus the next prompt). End with:
"Subphase 9B repair round 1 is ready for review. I have stopped and will not start the next
subphase until I receive the next prompt."


## Subphase 9B repair round 1

user-supplied external review

Subphase 9B repair round 1 review: APPROVE

1. VERDICT: APPROVE

B1 is fixed and the fix holds up under every check I ran. I found no blockers and no regressions. The evidence matches what it claims:
- Hashes: all 22 cumulative source hashes match. All 4 repair before/after pairs match. The 22 "before" hashes equal the reviewed 9B source-files.json.
- 9A integrity: the 29 untouched paths from the approved 9A repair round match. The other 5 of its 34 paths are exactly the ones already changed in the initial 9B.
- Logs: both raw-log SHA-256 bindings match. The external-review copy matches its SHA-256 (a558249e…) and appears verbatim in review.md under ## Subphase 9B.
- Full check log: 196+64+39+38+66+90+503+8 = 1004 passed. There are no *** FAILED lines; the only [error] is the expected injected format-stage probe. TestRunMarker ran, real time 717.84 s.
- Scope: HEAD is f139f9c. There are 10 changed tracked files plus the 17 untracked 9B source files. Nothing touches core, storage, build or infrastructure in this round, and no Java or sbt process is running.

B1 acceptance:

1. The exact metric is no longer marked approximate. In CollaborationMetricsAgent.scala:103-109 the metric item is built once and never rebound. Both specs assert exact == baseline against a store with no estimate (Runtime9BSpec.scala:80, IndependentRuntime9BStagesSpec.scala:131). They also check approximate=false and the hand-derived A values: 3, 2, 4, 4/3, 2, 4, coreness 2.
2. Named and ranking items agree. The independent spec compares every exact field (except kind) against the ranking row for the same researcher, window and run. It also compares run, window, converged and iterations, and asserts !ranked.approximate (IndependentRuntime9BStagesSpec.scala:155-162).
3. P90 is now a separate item. It is built by make(... "distance-estimate" ..., approximate = true) at CollaborationMetricsAgent.scala:112-131 and carries the required fields:
   - component subject and componentId;
   - effectiveDiameterP90 "4.0", sampled-bfs, distanceP90Approximate=true;
   - the source window and run, which are checked against the metric record at lines 95-101;
   - two path_length_estimate source references.

   It is content-bound through RuntimeEvidenceIds.bind, and the specs check expectedId and bind idempotence. The rendered context shows approximate:true only on the estimate.
4. The pair is admitted atomically. The builder admits non-ranked deterministic items all-or-nothing, and this repair did not change the builder (EvidenceBuilderAgent.scala:56-57). The independent spec proves the exact metric alone fits the budget, then shows the pair returns Missing("essential-evidence-context-budget") with zero put calls. With enough budget, both items are persisted and resolve through the index lookup.
5. Nothing else regressed. Iteration flags on metric items, source-mismatch checks, N1 partition checks, budgets, and the four-hop and ranking workflows are all unchanged and still pass.
6. No O-item or 9C work was introduced.

2. Findings

There are no blocking findings.

- R1 · Low · Nonblocking · The P90 item leaves out its sampling details.
  - Where: CollaborationMetricsAgent.scala:119-124.
  - What: the item carries P90, method and component. It omits the stored sampleSourceCount, seed, meanDistance, reachedPairCount and context.policyVersion (metricVersion=None). It is also typed RESEARCHER_PROFILE although its subject is a component.
  - Impact: a 9C answer can say "approximate" but cannot state the sample size behind it.
  - Owner: rag-engineer, optional, alongside O8.
  - Acceptance check (if adopted): sample count and reached pairs appear as evidence values, and the source references cover them.
- R2 · Cosmetic · Nonblocking · Missing spaces in the evidence prose.
  - Where: docs/agent-runs/phase-09/repairs.md:93-123, for example "before9C", "99targeted/1004full", "fullcheckexit0", "Fourrepairpaths". The initial-9B reports had the same problem.
  - Owner: orchestrator. Only new text should be fixed; recorded human decisions stay unedited.
- Carried forward: O1–O10 stay open, nonblocking and log-only. N1 is fixed; N2–N9 stay carried forward. R1 is O1-adjacent: the exact metric item still carries the membership's converged/iterations, which is O1 and unchanged.

Not verified (live or future gates)

- Live provider, model, region and injection behaviour.
- Production latency and adapters that ignore interruption.
- Real enrichment coverage.
- How often real exports carry pathLengthEstimate.
- All 9C work; 11B suites.
- Phase 8C stays deferred to 14C.

3. Report fields

STATUS: COMPLETE (review); verdict APPROVE for Subphase 9B repair round 1
OWNER: code-reviewer (independent, user-launched, read-only)
WORK ORDER: Phase 9 Subphase 9B repair round 1 recheck (pasted prompt)
FILES CREATED: none
FILES MODIFIED: none
COMMANDS RUN: read-only — git rev-parse/branch/status/diff --stat f139f9c; cat/sed/grep over
  evidence/9b-r1, review.md, repairs.md, rag README, CollaborationMetricsAgent, RuntimeRetrieval,
  EvidenceBuilderAgent, WorkflowRunner, Runtime9BSpec, IndependentRuntime9BStagesSpec/EvidenceSpec,
  core PathLengthEstimate; python3 -I SHA-256 of source-files.json (22/22), repair-files.json (4/4),
  source-before vs 9b source-files (22/22 equal), 9a-r1 source-files (29 match + 5 known 9B
  changes), external-review.txt (match; verbatim in review.md), two /tmp raw logs (2/2); grep of
  /tmp/phase9b-r1-check-1.log (0 "*** FAILED", counts 1004, probe-only [error], TestRunMarker);
  ps for java/sbt (none). No sbt, AWS, provider, network or git writes.
TEST RESULTS: not run by reviewer. Retained: targeted exit 0, 99 passed (storage 15, RAG 17,
  independent 67), 11.66 s; full check exit 0, 1004 passed, 0 failed, 717.84 s, JDK 17.0.20.1.
VALIDATION RESULTS: B1 FIXED (acceptance 1–6 met); no blockers; R1 (Low), R2 (cosmetic) nonblocking;
  O1–O10 open log-only; N1 fixed; N2–N9 carried forward.
ASSUMPTIONS: external-review.txt is the user-supplied text; its fidelity to the pasted review was
  not independently compared beyond the hash and the verbatim append.
RISKS: O1–O3 must be handled before 9C verifier/audit rely on qualifier scope, lineage and
  researcherIds; R1 limits approximate-disclosure detail.
MANUAL ACTION REQUIRED: user decides and performs (or explicitly instructs) the 9B commit; user
  relays the next prompt.
BLOCKED-ON OWNER: none
BLOCKED-ON EVIDENCE: none for 9B; 9C base commit pending user confirmation
NEXT GATE: record approval → user-confirmed 9B commit as 9C base → 9C Step 0 questions

4. Next prompt

You are the ScholarChain Phase 9 coordinator in a fresh session at
/Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-9, base/HEAD
f139f9c925b4925864a2c9a33734d869a1929cd2. Subphase 9B and its repair round 1 are uncommitted.
The independent read-only recheck of Subphase 9B repair round 1 returned APPROVE.

Read first: AGENTS.md, CLAUDE.md, docs/agents.md, docs/agent-runs/README.md, the plan of record
/Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase9.md
(Sections 3–7, Subphase 9C in Section 8, Sections 9–10), the course Phase 9 specification,
docs/agent-runs/phase-09/{prompt,owner-report,test-report,review,repairs}.md,
evidence/9a/user-answers.md (ten original decisions, binding), evidence/9b/user-answers.md
(approved 9B defaults, binding) and evidence/9b-r1/.

Step 1 — Record the approval. Append the reviewer's verdict verbatim (the user supplies the full
text) to docs/agent-runs/phase-09/review.md under a new heading "## Subphase 9B repair round 1",
marked "user-supplied external review". Do not alter earlier text. Store an identical copy at
docs/agent-runs/phase-09/evidence/9b-r1/external-recheck.txt with its SHA-256. In repairs.md
record B1 FIXED (externally approved), log R1 (Low: P90 item omits sampleSourceCount, seed,
meanDistance, reachedPairCount, policyVersion; RESEARCHER_PROFILE type for a component subject)
and R2 (cosmetic: missing spaces in evidence prose) as OPEN/nonblocking/log only, and keep
O1–O10 OPEN/log only. Write new evidence prose with normal spacing; do not edit recorded human
decisions.

Step 2 — Commit gate. Run git status and git log -1 (read-only) and check whether the approved 9B
work (the 22 source/test/module-doc paths in evidence/9b-r1/source-files.json, the phase-09
reports and the evidence/9b and 9b-r1 packets) has been committed. If it has not, ask the user
to commit it or to give an explicit instruction for you to commit it, and STOP and wait. No agent
commit or push without explicit user instruction. Once committed, verify that the committed blobs
match the source-files.json hashes and record that commit SHA as the 9C base in
evidence/9c/preflight.json.

Step 3 — Start ONLY Subphase 9C, and only after the user's next prompt confirms the base. Begin
with one bundled set of Step 0 questions covering every open 9C decision in plan Section 8
(synthesis model and prompts, verifier and claim rules, audit record, CLI, benchmark, and how
O1–O3 and R1 affect verifier/audit scope), each with a recommended default. Then STOP and wait
for answers. Do not prepare or implement 9C before the answers arrive.

Binding constraints for all of 9C:
- Preserve all ten original decisions, the approved 9B defaults, N2–N9 carried forward,
  O1–O10 and R1–R2 as logged. Phase 8C stays deferred to 14C; no whole-Phase-8 acceptance.
- Route every edit by docs/agents.md (rag-engineer modules/rag/** and prompts/**,
  domain-engineer modules/core/**, test-engineer tests/**, coordinator evidence only).
  No nested delegation.
- The 9C verifier and audit must treat converged/iterations and approximate qualifiers per O1/R1,
  use resolvedCandidates plus deterministic subjects for identity (O3), and keep the separate
  approximate distance-estimate item approximate in claims.
- Every sbt command uses
    export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
    export PATH="$JAVA_HOME/bin:$PATH"
    export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
  with java -version recorded, targeted gates, the full /usr/bin/time -p sbt -batch check and
  git diff --check. Retain every failed attempt, raw-log paths and SHA-256 values, and source
  before/after hashes.
- No AWS, provider or live calls, infrastructure, secret reads or human-gate edits. A live smoke
  test requires separate written user approval with a dollar cap, recorded before any call.
- Never launch a reviewer.

Step 4 — After 9C gates pass, stop. Ensure no specialists or builds are running. Return the
handoff packet and a complete independent reviewer prompt for Subphase 9C in one fenced block,
with checkpoint facts filled in with real values. End with:
"Subphase 9C is ready for review. I have stopped and will not start the next subphase until I


## Subphase 9C

user-supplied external review

VERDICT: APPROVE for Subphase 9C. Nothing blocks it. There are ten nonblocking findings, listed below.

I checked every claimed result against the files and raw logs, and all of it holds:
- Inventory: HEAD and base are both 2527de0. There are 24 changed tracked files and 60 untracked files, and all 38 source SHA-256 hashes match source-files.json.
- Raw logs: all 13 /tmp log hashes match log-bindings.json.
- Full check (check-2): 207/64/39/38/80/107/588/8 passed, 0 failed, TestRunMarker ran, 780.69 s. The log was created at 18:01:18, after the last source change at 18:00:40. That change was the scalafmt step inside the final targeted run.
- Final targeted run (targeted-5): 14/74/211 passed.
- Offline CLI benchmark: 15/15 cases passed. The ambiguous case returned both homonyms, Name 0001 and Name 0002.
- New 9C tests: counted per suite from the full log: core 11, storage 14, RAG 17, independent 85. That makes 127, and 1,004 + 127 = 1,131.
- Ownership: every file is in its owner's territory. No build, services, infrastructure, constitutional, prior-review or human-gate changes, and no secrets or hardcoded cloud values in the new files.

Findings (all nonblocking)

#: NB1
Severity: Medium
path:line: modules/rag/.../ClaimVerificationAgent.scala:169-174, 186-192, 245-252
Evidence: The verifier only checks that each cited evidence ID exists in the bundle. Support comes from the filtered subset that matches subject,
window and trust, but the accepted claim keeps all its citations. So a METRIC claim citing [metric(A), semantic(A)] or [metric(A),  metric(B)]
passes as VERIFIED and still lists the unrelated or descriptive ID.
Impact: A verified number can point at semantic text (possibly containing injected instructions) or at another researcher's evidence. This weakens
the deterministic/semantic separation in the final answer and in Phase 10 GET /v1/evidence/{id}.
Owner: rag-engineer; test-engineer for independent tests
Acceptance check: A claim with an unrelated, other-subject or descriptive citation on a non-SEMANTIC claim is UNSUPPORTED, or that citation is
removed and the removal recorded. Add independent tests for both shapes.
────────────────────────────────────────
#: NB2
Severity: Medium
path:line: modules/rag/.../RuntimeAnswerWorkflow.scala:129, 204-205; tests/.../IndependentRuntime9CWorkflowSpec.scala:113-116
Evidence: When verification ends with no accepted claim (verifier rejected everything, synthesis abstained or synthesis was malformed), the workflow
returns AnswerWorkflowResult.Completed with audit.outcome == "ABSTAINED". The Abstained result type is never used in those cases, and the reason
(e.g. synthesis-invalid-output) exists only in the audit. The independent test locks in this behavior.
Impact: A Phase 10 consumer matching on Completed could present an abstention as an answer.
Owner: rag-engineer; test-engineer
Acceptance check: Either return Abstained(reason, audit) when verification.abstained, or record this contract as binding for Phase 10, with a test
either way.
────────────────────────────────────────
#: NB3
Severity: Low
path:line: modules/rag/.../QueryPlannerAgent.scala:285
Evidence: The planner's model-output JSON is limited by questionBytes, not outputBytes.
Impact: This mixes two byte limits that 9C was meant to separate (N3). If someone sets a small question cap, every valid planner output gets rejected
and the planner silently falls back to rules.
Owner: rag-engineer
Acceptance check: Use outputBytes, plus a test with a small question cap and a valid larger planner output.
────────────────────────────────────────
#: NB4
Severity: Low
path:line: tests/.../IndependentRuntime9CBenchmarkSpec.scala:10-16, 53-63; RuntimeWorkflowMain.scala:224-226
Evidence: The ranking, team and bridge cases only check that some verified row has the expected value. The scripted model proposes that same value
for every retained row.
Impact: Rank order and which researcher is on top are not asserted end to end.
Owner: test-engineer
Acceptance check: Assert the ranked researchers and ranks by hand (e.g. C/D/F for distinct coauthors = 3).
────────────────────────────────────────
#: NB5
Severity: Low
path:line: RuntimeOfflineFixture.scala:46; SemanticContextAgent.scala:23-24
Evidence: The benchmark runs in graph mode, not the default fused. In fused mode, any query naming more than one researcher always gets a
non-essential semantic Unsupported, so it reports partial-retrieval.
Impact: The default retrieval mode is not covered by the benchmark.
Owner: rag-engineer
Acceptance check: Note this in the README, or add one fused-mode benchmark or workflow case.
────────────────────────────────────────
#: NB6
Severity: Low
path:line: RuntimeAnswerWorkflow.scala:160-162, 177-179
Evidence: The synthesis, verification and audit stages write no structured logs, and traceId is just the queryId.
Impact: Plan §6.8 asks for structured logs with trace/run IDs.
Owner: rag-engineer (Phase 11 may absorb this)
Acceptance check: Stage outcome logs with trace and run IDs, and no payloads.
────────────────────────────────────────
#: NB7
Severity: Low
path:line: modules/rag/README.md:371-444
Evidence: Task 7 asks the README to record benchmark results; the 9C section describes the cases but never states the observed 15/15.
Impact: Documentation is incomplete.
Owner: rag-engineer
Acceptance check: Add the observed results with a pointer to the evidence.
────────────────────────────────────────
#: NB8
Severity: Low
path:line: RuntimeAnswerWorkflow.scala:58, 81
Evidence: The plan variable is written from the stage thread without synchronization.
Impact: After a retrieval timeout the audit may miss a plan that did exist.
Owner: rag-engineer
Acceptance check: Make it volatile or atomic.
────────────────────────────────────────
#: NB9
Severity: Low
path:line: ClaimVerificationAgent.scala:322-331
Evidence: Researchers that were not resolved by name show up as raw IDs in the answer text, and unordered coauthorIds are joined with "→".
Impact: Cosmetic and misleading in the final text.
Owner: rag-engineer
Acceptance check: Neutral separator for sets.
────────────────────────────────────────
#: NB10
Severity: Low
path:line: RuntimeRetrieval.scala:153-165
Evidence: When an item has no stored source context, datasetSnapshot falls back to the run ID (for semantic items, the embedding document's run ID).
Impact: That field holds a value of a different kind; the README only partly discloses this.
Owner: rag-engineer
Acceptance check: Disclose it, or leave the snapshot absent when it is unknown.

Unverified future gates (not 9C defects):
- Live Bedrock compatibility (model, tool, region, temperature) and the optional smoke run, which needs the user's approval and cap.
- Live answer quality and general injection resistance (broader suites are Phase 11B).
- Production latency, real enrichment coverage and real loader confidence.
- Ports that ignore interruption.
- Orphan audit objects left by a failed pointer write.
- Phase 8C, deferred to 14C.

Report fields

STATUS: COMPLETE (read-only review). VERDICT: APPROVE for Subphase 9C.
OWNER: code-reviewer (user-launched, read-only)
WORK ORDER: Independent review of Phase 9 Subphase 9C at branch phase-9, base/HEAD 2527de01252286080e6db776b9cc0199a9353e1e, uncommitted.
FILES CREATED: None.
FILES MODIFIED: None.
COMMANDS RUN: git rev-parse HEAD; git status --short [-uall]; git diff --stat/diff 2527de0 (core, rag, storage, tests, phase-09 evidence); reads of all untracked sources/tests/resources and evidence/9c/*; shasum of the plan (8c16e8ee… matches preflight); python3 -I SHA-256 re-verification of 38 sources (0 mismatches) and 13 raw logs (all OK); grep/parse of /tmp/phase9c-check-2.log, targeted-5.log, cli-benchmark-2.log (per-suite counts, 0 "*** FAILED", marker, outcomes/verdicts); secret/hardcoded-cloud-value grep (no hits). No builds, tests, provider/AWS calls, secret reads or writes.
TEST RESULTS: Not run by the reviewer. Observed retained logs: full check 1,131 passed / 0 failed (207/64/39/38/80/107/588/8), 780.69 s, TestRunMarker ran; targeted 299/0; CLI 15/15. Check 1 (exit 143) is not counted.
VALIDATION RESULTS: Ownership single-writer per path; schema-validated synthesis, one bounded retry, byte/deadline guards; deterministic verifier is the only decider; exact BigDecimal comparison; template-regenerated facts; interpretation guard; field-scoped convergence and approximate P90 with sampling details; stored-source lineage separate from request lineage; resolved/deterministic audit identities; named semantic entity filter; deterministic text=None; path-status pairs; vector mode rejects non-SEMANTIC claims; untrusted JSON delimiters; versioned prompts/schemas unchanged; immutable content-addressed audit with conditional namespaced pointer, readback, replay/conflict, fail-closed; pre-plan audits without a fabricated plan; evidence-only skips synthesis; critical path 22,000 ms ≤ 30,000 ms; ambiguity keeps both homonyms, skips synthesis, leaves resolved IDs empty. Benchmark values hand-checked against literal G1 (A-C-D-F-G = 4 hops; C=3/D=4 community sizes; B/C coauthors; D Δ=1). Ten nonblocking findings NB1-NB10.
ASSUMPTIONS: The /tmp raw logs are the originals (hashes match). The Drive plan and course README sections are as recorded in authority-reading.md.
RISKS: NB1/NB2 affect how Phase 10 will consume results; offline scripted LLM and synthetic overlays only.
MANUAL ACTION REQUIRED: User decides whether to implement any nonblocker; user authorizes or performs the 9C commit; user writes human-gate.md/commit records.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for 9C. Live gates remain unverified future gates.
NEXT GATE: Append the review, user-authorized 9C commit, Phase 9 human gate. Phase 10 next (not started).

Next prompt

You are the ScholarChain Phase 9 orchestrator in /Users/danny/Documents/UIC/CS441/ScholarChain,
branch phase-9, base/HEAD 2527de01252286080e6db776b9cc0199a9353e1e, Subphase 9C uncommitted.

The independent read-only reviewer returned VERDICT: APPROVE for Subphase 9C with no blocking
findings and ten nonblocking findings (NB1-NB10). The full reviewer output I am supplying with this
prompt is the user-supplied external review.

Do exactly this, then stop:
1. Append that complete reviewer output verbatim to docs/agent-runs/phase-09/review.md under a
   "Subphase 9C" heading, marked "user-supplied external review". Do not edit any earlier review text.
2. In docs/agent-runs/phase-09/repairs.md, add a "Subphase 9C review - nonblocking findings (logged
   only)" section listing NB1-NB10 with ID, owner, path:line and acceptance check exactly as the
   review states. Mark each "logged; not implemented". Do not implement any of them unless I
   explicitly ask in a later prompt. If I ask, route each to its native owner (rag-engineer for
   modules/rag/**, test-engineer for tests/**), one writer per path, keep all ten original decisions,
   the approved 9B defaults and the seven approved 9C defaults, rerun the affected targets and the
   full JDK 17 `sbt check` with retained evidence and hashes, and return a recheck reviewer prompt.
3. Update owner-report.md / test-report.md only to cite the APPROVE verdict and the logged
   nonblockers. No source, test, build, infrastructure or evidence-result changes, and no reruns.
   The 9C source hashes in evidence/9c/source-files.json must still match. Verify and report this.
4. Commit authorization: I have not yet authorized a 9C commit unless this message says so
   explicitly. Ask me whether to commit (and whether to push) Subphase 9C. Never commit or push
   without my explicit instruction. If I authorize it, commit only the reviewed 9C paths in
   evidence/9c/files.json plus the review/repairs/report updates from steps 1-3, and report the
   exact git output and SHA.
5. Tell me Phase 9 is ready for my human gate (human-gate.md and commit.txt are written only by
   me) and that Phase 10 is next. Do not start, plan or prepare Phase 10.

Rules: no nested delegation, no reviewer launch, no live/cloud/provider calls, no secret reads, no
infrastructure, no human-gate edits, no Phase 10 work. End the turn after step 5.

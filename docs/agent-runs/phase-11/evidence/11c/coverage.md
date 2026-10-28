# Phase 11 categories 1–20

Sources are the committed 11A/11B maps; names are preserved exactly. Counts overlap across categories.

| Category | Plane | Existing | New | Total |
| --- | --- | ---: | ---: | ---: |
| 1 | 11a | 4 | 2 | 6 |
| 2 | 11a | 0 | 2 | 2 |
| 3 | 11a | 3 | 0 | 3 |
| 4 | 11a | 1 | 1 | 2 |
| 5 | 11a | 1 | 3 | 4 |
| 6 | 11a | 4 | 0 | 4 |
| 7 | 11a | 2 | 2 | 4 |
| 8 | 11a | 4 | 3 | 7 |
| 9 | 11a | 6 | 4 | 10 |
| 10 | 11a | 1 | 1 | 2 |
| 11 | 11a | 4 | 1 | 5 |
| 12 | 11b | 3 | 2 | 5 |
| 13 | 11b | 4 | 6 | 10 |
| 14 | 11b | 2 | 3 | 5 |
| 15 | 11b | 2 | 9 | 11 |
| 16 | 11b | 2 | 3 | 5 |
| 17 | 11b | 2 | 3 | 5 |
| 18 | 11b | 4 | 3 | 7 |
| 19 | 11b | 1 | 1 | 2 |
| 20 | 11b | 1 | 1 | 2 |

Distinct selected tests: 51 existing + 32 new = 83. This is a selected requirement map, not an exhaustive test census or a guarantee of full category depth. Category 20 covers configuration parsing, not startup composition (F11B-3). Category 16 has all three named faults plus extra audit-failure coverage (F11B-4).

## Category 1

- existing: `IndependentDblpJsonSpec` — DblpSplitReader split edge keeps the record that starts before the boundary
- existing: `IndependentDblpJsonSpec` — DblpXml local entity declaration expands inline markup before parse
- existing: `IndependentDblpJsonSpec` — DblpRecords rejects malformed token and external SYSTEM entity declaration
- existing: `IndependentDblpJsonSpec` — DblpRecords preserves unicode in author and title fields
- new: `AdversarialDataPlaneSpec` — a truncated final Unicode record is marked unterminated without losing its complete predecessor
- new: `AdversarialDataPlaneSpec` — multiline Unicode titles preserve source markup and normalize whitespace deterministically

Scope: Existing malformed/entity/Unicode/split coverage reused; final truncated record and multiline title added.

## Category 2

- new: `AdversarialDataPlaneSpec` — NFC and NFD share DBLP researcher identity while original author evidence survives
- new: `AdversarialDataPlaneSpec` — Latin Cyrillic confusables and DBLP homonym suffixes stay distinct identities

Scope: Added explicit NFC/NFD equality, preserved observation evidence, confusable distinction and suffix distinction.

## Category 3

- existing: `IndependentHadoopPipelineSpec` — pipeline duplicate identical and conflicting openalex observations surface in export
- existing: `IndependentHadoopPipelineSpec` — pipeline shared doi across dblp and crossref keeps lineage in match candidate sides
- existing: `IndependentResolutionEngineSpec` — a conflicting declared DOI wins over equal preferred DOI and equal work ID

Scope: Existing pipeline duplicates/conflicts/shared DOI and classifier contradictory DOI coverage reused.

## Category 4

- existing: `IndependentResolutionFeaturesSpec` — author order uses the documented reciprocal distance rather than binary ordinal equality
- new: `AdversarialDataPlaneSpec` — reordered repeated names retain source ordinals without asserting researcher equality

Scope: Added reordered repeated common names with distinct source mentions and explicitly unresolved authorships.

## Category 5

- existing: `IndependentHadoopPipelineSpec` — pipeline block size below at and above maxCandidateBlockSize three
- new: `AdversarialBlockingReplaySpec` — blocking drains 257 distinct DOI observations and rejects the whole max-eight block
- new: `AdversarialBlockingReplaySpec` — candidate join independently rejects 257 members even when blocking was bypassed
- new: `AdversarialBlockingReplaySpec` — eight-member candidate join refuses 28 pairs against a 27-pair budget atomically

Scope: Added257-observation real jobs and independent downstream bound; exact at-limit28pair acceptance in category11 also covers boundary.

## Category 6

- existing: `Phase6CJobsSpec` — orphan graph endpoints appear as hard integrity rows and obey the failure flag
- existing: `Phase6CJobsSpec` — cross-DBLP links are counted and ambiguous non-DBLP mentions stay unresolved
- existing: `Phase6CJobsSpec` — ER unresolved and conflict decisions use explicit wire schemas and named counters
- existing: `IndependentPhase6CGraphSpec` — conflicting ORCIDs for one exact DBLP name retain identity and emit one warning

Scope: Reused real Phase6C build tests for orphan endpoints, ambiguous non-DBLP resolution and ER unresolved/conflict counters; no invented identity repair.

## Category 7

- existing: `IndependentPhase6DEGraphSpec` — empty graph and one solo publication have no edges and finite measures
- existing: `IndependentPhase6DEGraphSpec` — a yearless edge stays in all-years and a disconnected pair has no path
- new: `AdversarialGraphShapesSpec` — ring barbell and clique-pendant graphs have exact degree weighted degree components and coreness
- new: `AdversarialGraphShapesSpec` — new graph shapes yield hand-derived shortest routes and disconnected no-path evidence

Scope: Existing empty/solo reused; added four disconnected components with exact membership and no-path.

## Category 8

- existing: `IndependentPhase6DEGraphSpec` — G1 full hand-computed metrics, components and coreness
- existing: `IndependentPhase6DEGraphSpec` — G2 star, G3 K4, G4 path and isolated node have exact coreness
- existing: `IndependentPhase6DEGraphSpec` — G1 selected paths have unique shortest route, no-path status and supported hop evidence
- existing: `IndependentPhase6DEGraphSpec` — G1 bridges under the declared partition and G2 star leaves
- new: `AdversarialGraphShapesSpec` — ring barbell and clique-pendant graphs have exact degree weighted degree components and coreness
- new: `AdversarialGraphShapesSpec` — new graph shapes yield hand-derived shortest routes and disconnected no-path evidence
- new: `AdversarialGraphShapesSpec` — declared barbell and pendant partitions have exact bridge measures for every node

Scope: Added C5 ring, weighted barbell, K4with2pendants and isolate;18node full literal oracles, supported shortest paths and all-node fixed-partition bridges.

## Category 9

- existing: `IndependentDblpJsonSpec` — PrepLimits pairCount stays overflow-safe at Int.MaxValue team size
- existing: `IndependentPhase6CGraphSpec` — a cross-DBLP accepted link does not collapse two exact DBLP names
- existing: `IndependentResolutionEngineSpec` — different direct ORCIDs cannot merge through equal name and shared OpenAlex author hypothesis
- existing: `IndependentResolutionEngineSpec` — matching direct identifiers use exact path without treating work equality as author equality
- existing: `IndependentRuntime9AResolverSpec` — common name abstains with both identities even when one confidence is higher
- existing: `IndependentRuntime9AResolverSpec` — exact homonym suffix resolves its identity while the published base alias stays ambiguous
- new: `AdversarialDataPlaneSpec` — 64 repeated common-name mentions yield exactly 2016 distinct ordinal pairs
- new: `AdversarialDataPlaneSpec` — 64-author expansion one pair over budget rejects atomically without partial pairs
- new: `AdversarialDataPlaneSpec` — reordered repeated names retain source ordinals without asserting researcher equality
- new: `AdversarialDataPlaneSpec` — Latin Cyrillic confusables and DBLP homonym suffixes stay distinct identities

Scope: Large-team expansion covered by new64mention2016pair/budget cases. Existing actual ResolutionEngine tests refuse name/work equality as sufficient researcher identity and prioritize conflicting directORCID over equal names/sharedOpenAlex hypotheses. Already-committed ResearcherResolverAgent tests explicitly exercise WeiWang ambiguity with confidence0.99vs0.51 and suffix identity resolution; reused as existing evidence only, no11Bruntime implementation. New suffix/confusable canonical-ID test cross-mapped. Synthetic fixture evidence does not establish population common-name accuracy.

## Category 10

- existing: `IndependentResolutionEngineSpec` — missing evidence stays unavailable rather than zero, perfect similarity or prep sentinel
- new: `AdversarialDataPlaneSpec` — bare publication metadata never invents topics institutions abstract or profile identity

Scope: Sparse public parser missing institution/topic/abstract/profile metadata and missing ID evidence; ER unavailable features remain unavailable.

## Category 11

- existing: `IndependentHadoopPipelineSpec` — OutputGate refuses occupied output and failed pipeline run skips completion marker
- existing: `IndependentHadoopPipelineSpec` — LocalJobRunner sample replay export is logically equivalent across two run ids
- existing: `IndependentPhase6DEGraphSpec` — two runs on the same G4 graph produce identical metric, core and component rows
- existing: `IndependentPhase6SafetySpec` — output gate refuses partial mismatched and tampered runs and reuses only the identical manifest
- new: `AdversarialBlockingReplaySpec` — permuted eight-member replay retains all 28 pairs and identical sorted-row SHA256

Scope: Added byte-exact sorted output and independent SHA256 over real candidate jobs with reversed inputs; full Hadoop/Spark pipeline replay/output gate already tested.

## Category 12

- existing: `IndependentEmbeddingStorageSpec` — a bound vector key rejects changed text before embedding and records the conflict
- existing: `IndependentStorageVectorSpec` — same key and text is unchanged while a changed text hash is rejected before provider write
- existing: `IndependentRuntime9BSemanticSpec` — semantic hits embedded by a different model cannot be compared with the query vector
- new: `AdversarialRuntimeBoundarySpec` — duplicate vector result keys reject the whole semantic result before source objects become evidence
- new: `AdversarialRuntimeBoundarySpec` — stale model version in a same-dimension vector result is rejected before it can authorize evidence

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

## Category 13

- existing: `IndependentRuntime9CSynthesisSpec` — instruction-looking title remains untrusted data and cannot change verified facts
- existing: `IndependentRuntime9CSynthesisSpec` — instruction-looking abstract remains untrusted data and cannot change verified facts
- existing: `IndependentRuntime9CSynthesisSpec` — instruction-looking generated profile remains untrusted data and cannot change verified facts
- existing: `IndependentRuntime9BEvidenceSpec` — retrieved delimiter injection stays JSON data inside one untrusted block
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects an injected title instruction and malicious count while retaining source evidence
- new: `AdversarialRuntimeHttpSpec` — HTTP title injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects an injected abstract instruction and malicious count while retaining source evidence
- new: `AdversarialRuntimeHttpSpec` — HTTP abstract injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects an injected fullText instruction and malicious count while retaining source evidence
- new: `AdversarialRuntimeHttpSpec` — HTTP fullText injection reaches real retrieval and verifier and replay preserves the audited abstention

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

## Category 14

- existing: `IndependentRuntime9CSynthesisSpec` — two malformed synthesis outputs abstain and never call a model verifier
- existing: `IndependentRuntime9CVerificationSpec` — a fabricated subject cannot borrow another researcher's stored metrics
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects model fake-identity even when JSON conforms to the synthesis schema
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects model fake-citation even when JSON conforms to the synthesis schema
- new: `AdversarialRuntimeWorkflowSpec` — malformed JSON exhausts the bounded model script and persists an abstention without attempted claims

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

## Category 15

- existing: `IndependentRuntime9CVerificationSpec` — a missing evidence ID cannot authorize an otherwise correct count
- existing: `IndependentRuntime9CVerificationSpec` — wrong stored count is rejected and remains available in attempted-claim audit material
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects an injected title instruction and malicious count while retaining source evidence
- new: `AdversarialRuntimeHttpSpec` — HTTP title injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects an injected abstract instruction and malicious count while retaining source evidence
- new: `AdversarialRuntimeHttpSpec` — HTTP abstract injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects an injected fullText instruction and malicious count while retaining source evidence
- new: `AdversarialRuntimeHttpSpec` — HTTP fullText injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects model fake-identity even when JSON conforms to the synthesis schema
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects model fake-citation even when JSON conforms to the synthesis schema
- new: `AdversarialRuntimeHttpSpec` — healthy control accepts the exact stored count through the same real HTTP and runtime composition

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

## Category 16

- existing: `IndependentStorageVectorSpec` — transient throttling retries once then succeeds with the same batch and bounded attempts
- existing: `IndependentRuntime9CWorkflowSpec` — required audit persistence failure fails closed after otherwise valid synthesis
- new: `AdversarialRuntimeWorkflowSpec` — Neptune reader timeout interrupts the actual graph call and audits missing essential evidence without synthesis
- new: `AdversarialRuntimeWorkflowSpec` — vector throttle failure cannot become semantic evidence and a later healthy query recovers without stale failure state
- new: `AdversarialRuntimeHttpSpec` — Dynamo conditional body-binding conflict fails HTTP closed before any runtime execution

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

## Category 17

- existing: `IndependentServices10ASpec` — same idempotency key replays stored answer without a second workflow execution
- existing: `IndependentServices10BWorkerSpec` — duplicate queue payloads execute once across worker instances and acknowledge both receipts
- new: `AdversarialRuntimeHttpSpec` — HTTP title injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — HTTP abstract injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — HTTP fullText injection reaches real retrieval and verifier and replay preserves the audited abstention

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

## Category 18

- existing: `IndependentServices10ASpec` — missing and incorrect bearer credentials reject query and jobs before workflow
- existing: `IndependentServices10ASpec` — external bearer cannot authorize internal routes and internal token cannot authorize queries
- existing: `IndependentServices10ASpec` — malformed JSON and invalid constraint types are rejected before workflow
- existing: `IndependentServices10ASpec` — workflow downstream error and timeout preserve typed HTTP mapping with trace ID
- new: `AdversarialRuntimeHttpSpec` — HTTP title injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — HTTP abstract injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — HTTP fullText injection reaches real retrieval and verifier and replay preserves the audited abstention

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

## Category 19

- existing: `IndependentServices10ASpec` — structured request logs exclude authorization, extra headers, and malformed request content
- new: `AdversarialRuntimeHttpSpec` — synthetic config credentials header and thrown provider canaries stay absent from HTTP responses and observed logs

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

## Category 20

- existing: `ServiceFoundationSpec` — authentication domains are separate with no usable default credentials
- new: `AdversarialRuntimeBoundarySpec` — each required service credential omission fails configuration before composition without revealing supplied values

Scope: See runtime test-report and carried F11B-2/F11B-3/F11B-4 limits.

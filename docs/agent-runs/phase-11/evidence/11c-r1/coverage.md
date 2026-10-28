# Current Phase 11 coverage after repair round 1

Historical maps remain unchanged. This current map replaces the defective503 expectation and adds the lost-reply case, per test-engineer handoff. Counts overlap across categories. 51 existing +33 Phase11 cross-module new =84 distinct selected tests; four additional module regression cases are listed in the full-check summary. Total new tests since pre-Phase11 baseline:15+17+5=37.

| Category | Existing | New | Total |
| --- | ---: | ---: | ---: |
| 1 | 4 | 2 | 6 |
| 2 | 0 | 2 | 2 |
| 3 | 3 | 0 | 3 |
| 4 | 1 | 1 | 2 |
| 5 | 1 | 3 | 4 |
| 6 | 4 | 0 | 4 |
| 7 | 2 | 2 | 4 |
| 8 | 4 | 3 | 7 |
| 9 | 6 | 4 | 10 |
| 10 | 1 | 1 | 2 |
| 11 | 4 | 1 | 5 |
| 12 | 3 | 2 | 5 |
| 13 | 4 | 6 | 10 |
| 14 | 2 | 3 | 5 |
| 15 | 2 | 9 | 11 |
| 16 | 2 | 4 | 6 |
| 17 | 2 | 5 | 7 |
| 18 | 4 | 3 | 7 |
| 19 | 1 | 1 | 2 |
| 20 | 1 | 1 | 2 |

## Category 1

- existing: `IndependentDblpJsonSpec` — DblpSplitReader split edge keeps the record that starts before the boundary
- existing: `IndependentDblpJsonSpec` — DblpXml local entity declaration expands inline markup before parse
- existing: `IndependentDblpJsonSpec` — DblpRecords rejects malformed token and external SYSTEM entity declaration
- existing: `IndependentDblpJsonSpec` — DblpRecords preserves unicode in author and title fields
- new: `AdversarialDataPlaneSpec` — a truncated final Unicode record is marked unterminated without losing its complete predecessor
- new: `AdversarialDataPlaneSpec` — multiline Unicode titles preserve source markup and normalize whitespace deterministically

## Category 2

- new: `AdversarialDataPlaneSpec` — NFC and NFD share DBLP researcher identity while original author evidence survives
- new: `AdversarialDataPlaneSpec` — Latin Cyrillic confusables and DBLP homonym suffixes stay distinct identities

## Category 3

- existing: `IndependentHadoopPipelineSpec` — pipeline duplicate identical and conflicting openalex observations surface in export
- existing: `IndependentHadoopPipelineSpec` — pipeline shared doi across dblp and crossref keeps lineage in match candidate sides
- existing: `IndependentResolutionEngineSpec` — a conflicting declared DOI wins over equal preferred DOI and equal work ID

## Category 4

- existing: `IndependentResolutionFeaturesSpec` — author order uses the documented reciprocal distance rather than binary ordinal equality
- new: `AdversarialDataPlaneSpec` — reordered repeated names retain source ordinals without asserting researcher equality

## Category 5

- existing: `IndependentHadoopPipelineSpec` — pipeline block size below at and above maxCandidateBlockSize three
- new: `AdversarialBlockingReplaySpec` — blocking drains 257 distinct DOI observations and rejects the whole max-eight block
- new: `AdversarialBlockingReplaySpec` — candidate join independently rejects 257 members even when blocking was bypassed
- new: `AdversarialBlockingReplaySpec` — eight-member candidate join refuses 28 pairs against a 27-pair budget atomically

## Category 6

- existing: `Phase6CJobsSpec` — orphan graph endpoints appear as hard integrity rows and obey the failure flag
- existing: `Phase6CJobsSpec` — cross-DBLP links are counted and ambiguous non-DBLP mentions stay unresolved
- existing: `Phase6CJobsSpec` — ER unresolved and conflict decisions use explicit wire schemas and named counters
- existing: `IndependentPhase6CGraphSpec` — conflicting ORCIDs for one exact DBLP name retain identity and emit one warning

## Category 7

- existing: `IndependentPhase6DEGraphSpec` — empty graph and one solo publication have no edges and finite measures
- existing: `IndependentPhase6DEGraphSpec` — a yearless edge stays in all-years and a disconnected pair has no path
- new: `AdversarialGraphShapesSpec` — ring barbell and clique-pendant graphs have exact degree weighted degree components and coreness
- new: `AdversarialGraphShapesSpec` — new graph shapes yield hand-derived shortest routes and disconnected no-path evidence

## Category 8

- existing: `IndependentPhase6DEGraphSpec` — G1 full hand-computed metrics, components and coreness
- existing: `IndependentPhase6DEGraphSpec` — G2 star, G3 K4, G4 path and isolated node have exact coreness
- existing: `IndependentPhase6DEGraphSpec` — G1 selected paths have unique shortest route, no-path status and supported hop evidence
- existing: `IndependentPhase6DEGraphSpec` — G1 bridges under the declared partition and G2 star leaves
- new: `AdversarialGraphShapesSpec` — ring barbell and clique-pendant graphs have exact degree weighted degree components and coreness
- new: `AdversarialGraphShapesSpec` — new graph shapes yield hand-derived shortest routes and disconnected no-path evidence
- new: `AdversarialGraphShapesSpec` — declared barbell and pendant partitions have exact bridge measures for every node

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

## Category 10

- existing: `IndependentResolutionEngineSpec` — missing evidence stays unavailable rather than zero, perfect similarity or prep sentinel
- new: `AdversarialDataPlaneSpec` — bare publication metadata never invents topics institutions abstract or profile identity

## Category 11

- existing: `IndependentHadoopPipelineSpec` — OutputGate refuses occupied output and failed pipeline run skips completion marker
- existing: `IndependentHadoopPipelineSpec` — LocalJobRunner sample replay export is logically equivalent across two run ids
- existing: `IndependentPhase6DEGraphSpec` — two runs on the same G4 graph produce identical metric, core and component rows
- existing: `IndependentPhase6SafetySpec` — output gate refuses partial mismatched and tampered runs and reuses only the identical manifest
- new: `AdversarialBlockingReplaySpec` — permuted eight-member replay retains all 28 pairs and identical sorted-row SHA256

## Category 12

- existing: `IndependentEmbeddingStorageSpec` — a bound vector key rejects changed text before embedding and records the conflict
- existing: `IndependentStorageVectorSpec` — same key and text is unchanged while a changed text hash is rejected before provider write
- existing: `IndependentRuntime9BSemanticSpec` — semantic hits embedded by a different model cannot be compared with the query vector
- new: `AdversarialRuntimeBoundarySpec` — duplicate vector result keys reject the whole semantic result before source objects become evidence
- new: `AdversarialRuntimeBoundarySpec` — stale model version in a same-dimension vector result is rejected before it can authorize evidence

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

## Category 14

- existing: `IndependentRuntime9CSynthesisSpec` — two malformed synthesis outputs abstain and never call a model verifier
- existing: `IndependentRuntime9CVerificationSpec` — a fabricated subject cannot borrow another researcher's stored metrics
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects model fake-identity even when JSON conforms to the synthesis schema
- new: `AdversarialRuntimeWorkflowSpec` — full workflow rejects model fake-citation even when JSON conforms to the synthesis schema
- new: `AdversarialRuntimeWorkflowSpec` — malformed JSON exhausts the bounded model script and persists an abstention without attempted claims

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

## Category 16

- existing: `IndependentStorageVectorSpec` — transient throttling retries once then succeeds with the same batch and bounded attempts
- existing: `IndependentRuntime9CWorkflowSpec` — required audit persistence failure fails closed after otherwise valid synthesis
- new: `AdversarialRuntimeWorkflowSpec` — Neptune reader timeout interrupts the actual graph call and audits missing essential evidence without synthesis
- new: `AdversarialRuntimeWorkflowSpec` — vector throttle failure cannot become semantic evidence and a later healthy query recovers without stale failure state
- new: `AdversarialRuntimeHttpSpec` — one rejected Dynamo body bind recovers through same-key HTTP replay and executes exactly once
- new: `AdversarialRuntimeHttpSpec` — an applied Dynamo body bind with a lost reply completes through HTTP and stored replay without rerunning

## Category 17

- existing: `IndependentServices10ASpec` — same idempotency key replays stored answer without a second workflow execution
- existing: `IndependentServices10BWorkerSpec` — duplicate queue payloads execute once across worker instances and acknowledge both receipts
- new: `AdversarialRuntimeHttpSpec` — HTTP title injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — HTTP abstract injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — HTTP fullText injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — one rejected Dynamo body bind recovers through same-key HTTP replay and executes exactly once
- new: `AdversarialRuntimeHttpSpec` — an applied Dynamo body bind with a lost reply completes through HTTP and stored replay without rerunning

## Category 18

- existing: `IndependentServices10ASpec` — missing and incorrect bearer credentials reject query and jobs before workflow
- existing: `IndependentServices10ASpec` — external bearer cannot authorize internal routes and internal token cannot authorize queries
- existing: `IndependentServices10ASpec` — malformed JSON and invalid constraint types are rejected before workflow
- existing: `IndependentServices10ASpec` — workflow downstream error and timeout preserve typed HTTP mapping with trace ID
- new: `AdversarialRuntimeHttpSpec` — HTTP title injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — HTTP abstract injection reaches real retrieval and verifier and replay preserves the audited abstention
- new: `AdversarialRuntimeHttpSpec` — HTTP fullText injection reaches real retrieval and verifier and replay preserves the audited abstention

## Category 19

- existing: `IndependentServices10ASpec` — structured request logs exclude authorization, extra headers, and malformed request content
- new: `AdversarialRuntimeHttpSpec` — synthetic config credentials header and thrown provider canaries stay absent from HTTP responses and observed logs

## Category 20

- existing: `ServiceFoundationSpec` — authentication domains are separate with no usable default credentials
- new: `AdversarialRuntimeBoundarySpec` — each required service credential omission fails configuration before composition without revealing supplied values

The configuration-test scope/error-clarity observation F11B-3 remains; category16 includes extra audit-failure coverage in addition to its three required faults. This is a requirement map, not a coverage percentage.

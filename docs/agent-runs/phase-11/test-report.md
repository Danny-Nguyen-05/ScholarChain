# Phase 11 test report

## Subphase 11A

STATUS: COMPLETE (local gates passed; external review pending)

OWNER: test-engineer `/root/test_engineer_11a` authors tests and coverage content; coordinator `/root` runs final gates and assembles this report.

WORK ORDER: 11A data-plane categories 1–11 only, exact work order and Step 0 answers in prompt.md. Branch `phase-11`; base and HEAD `0c5ee89994b5b738a3490ef5e8f032fdc67327b2`. Requirement coverage without a new coverage tool; ExposedDefect retained and explicitly run if exposed; later 11C base `0349388`.

FILES CREATED: AdversarialDataPlaneSpec.scala (8), AdversarialBlockingReplaySpec.scala (4), AdversarialGraphShapesSpec.scala (3), all under tests/src/test/scala/edu/uic/cs441/scholarchain/independent/. Coordinator evidence under docs/agent-runs/phase-11/. Exact inventory evidence/11a/handoff-files.json.

FILES MODIFIED: No existing tracked file; production/build/module-local tests unchanged.

COMMANDS RUN:

All commands ran from `/Users/danny/Documents/UIC/CS441/ScholarChain`. Every sbt command used:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Exact wrappers, redirects and exits are retained in `evidence/11a/commands.json`.

| Command / attempt | Exit | Observed result |
| --- | ---: | --- |
| `java -version` | 0 | OpenJDK 17.0.20.1 |
| `git switch -c phase-11` sandbox / approved retry | 128 / 0 | Initial lock refusal, then branch created |
| `sbt -batch 'independentTests / Test / scalafmt' 'independentTests / Test / testOnly *Adversarial*'` attempt 1 | 1 | Sandbox boot-lock denial; no tests loaded |
| Same targeted command, child escalation | no process exit | Approval call aborted without execution; coordinator took over |
| Same targeted command, coordinator attempt 2 | 1 | Formatting passed; new-test Scala indentation compile error; zero tests executed |
| Same targeted command, coordinator attempt 3 | 0 | 19/19 tests in four suites; 15 new plus four existing XML adversarial cases |
| `/usr/bin/time -p sbt -batch check > /tmp/phase11a-final-check.log 2>&1` | 0 | 1,231/1,231 in 152 reports; sbt 728 s, real 730.49 s |
| `python3 docs/agent-runs/phase-11/evidence/11a/collect-evidence.py` | 0 | Fresh-report, log-count, mapped-test and source-hash checks passed |
| `git diff --check` | 0 | No tracked whitespace errors; new Scala format checks passed in full gate |

The last sparse-author cardinality assertion arrived after targeted compilation. The final full check compiled and tested that final frozen source. The nested `checkProbeInjectFailure ... injected format-stage failure` is the expected build self-test; the outer check passed and wrote the ignored success marker.


TEST RESULTS:

Final full gate: **1,231 passed, zero failed/errors/skipped, 152 fresh JUnit reports**. Targeted 19/19 in four suites comprises 15 new and four existing tests; final full gate includes the last assertion added after targeted compilation. Historical baseline 1,216/149 is explicitly preexisting evidence, not a fresh baseline run. Module totals:

| Module | Tests | Fresh reports |
| --- | ---: | ---: |
| modules/core | 207 | 17 |
| modules/hadoop | 64 | 4 |
| modules/entity-resolution | 39 | 6 |
| modules/spark | 38 | 5 |
| modules/storage | 80 | 11 |
| modules/rag | 107 | 9 |
| modules/services | 36 | 6 |
| tests | 647 | 86 |
| build-verification | 13 | 8 |

Counts by selected requirement mapping: **45 unique tests = 30 existing + 15 new**. Category counts deliberately overlap; they do not sum to the number of unique tests. This is selected, meaningful coverage, not exhaustive historic category counting. The table reuses committed resolver tests to cover common-name behavior; no runtime test was authored for 11B here.

| Category | Selected existing | Mapped new | Named tests | Gap resolution |
| --- | ---: | ---: | --- | --- |
| 1. XML parsing/framing | 4 | 2 | `IndependentDblpJsonSpec` — DblpSplitReader split edge keeps the record that starts before the boundary<br>`IndependentDblpJsonSpec` — DblpXml local entity declaration expands inline markup before parse<br>`IndependentDblpJsonSpec` — DblpRecords rejects malformed token and external SYSTEM entity declaration<br>`IndependentDblpJsonSpec` — DblpRecords preserves unicode in author and title fields<br>`AdversarialDataPlaneSpec` — a truncated final Unicode record is marked unterminated without losing its complete predecessor<br>`AdversarialDataPlaneSpec` — multiline Unicode titles preserve source markup and normalize whitespace deterministically | Existing malformed/entity/Unicode/split coverage reused; final truncated record and multiline title added. |
| 2. Unicode/confusables/homonyms | 0 | 2 | `AdversarialDataPlaneSpec` — NFC and NFD share DBLP researcher identity while original author evidence survives<br>`AdversarialDataPlaneSpec` — Latin Cyrillic confusables and DBLP homonym suffixes stay distinct identities | Added explicit NFC/NFD equality, preserved observation evidence, confusable distinction and suffix distinction. |
| 3. Duplicate/conflicting DOI | 3 | 0 | `IndependentHadoopPipelineSpec` — pipeline duplicate identical and conflicting openalex observations surface in export<br>`IndependentHadoopPipelineSpec` — pipeline shared doi across dblp and crossref keeps lineage in match candidate sides<br>`IndependentResolutionEngineSpec` — a conflicting declared DOI wins over equal preferred DOI and equal work ID | Existing pipeline duplicates/conflicts/shared DOI and classifier contradictory DOI coverage reused. |
| 4. Common names/author order | 1 | 1 | `IndependentResolutionFeaturesSpec` — author order uses the documented reciprocal distance rather than binary ordinal equality<br>`AdversarialDataPlaneSpec` — reordered repeated names retain source ordinals without asserting researcher equality | Added reordered repeated common names with distinct source mentions and explicitly unresolved authorships. |
| 5. Blocking/candidate bounds | 1 | 3 | `IndependentHadoopPipelineSpec` — pipeline block size below at and above maxCandidateBlockSize three<br>`AdversarialBlockingReplaySpec` — blocking drains 257 distinct DOI observations and rejects the whole max-eight block<br>`AdversarialBlockingReplaySpec` — candidate join independently rejects 257 members even when blocking was bypassed<br>`AdversarialBlockingReplaySpec` — eight-member candidate join refuses 28 pairs against a 27-pair budget atomically | Added real 257-observation jobs and an independent downstream bound; exact acceptance of 28 pairs in category 11 also covers the limit. |
| 6. Unresolved/conflicting endpoints | 4 | 0 | `Phase6CJobsSpec` — orphan graph endpoints appear as hard integrity rows and obey the failure flag<br>`Phase6CJobsSpec` — cross-DBLP links are counted and ambiguous non-DBLP mentions stay unresolved<br>`Phase6CJobsSpec` — ER unresolved and conflict decisions use explicit wire schemas and named counters<br>`IndependentPhase6CGraphSpec` — conflicting ORCIDs for one exact DBLP name retain identity and emit one warning | Reused real Phase 6C build tests for orphan endpoints, ambiguous non-DBLP resolution and ER unresolved/conflict counters; no invented identity repair. |
| 7. Empty/disconnected graphs | 2 | 2 | `IndependentPhase6DEGraphSpec` — empty graph and one solo publication have no edges and finite measures<br>`IndependentPhase6DEGraphSpec` — a yearless edge stays in all-years and a disconnected pair has no path<br>`AdversarialGraphShapesSpec` — ring barbell and clique-pendant graphs have exact degree weighted degree components and coreness<br>`AdversarialGraphShapesSpec` — new graph shapes yield hand-derived shortest routes and disconnected no-path evidence | Existing empty/solo reused; added four disconnected components with exact membership and no-path. |
| 8. Known graph measures | 4 | 3 | `IndependentPhase6DEGraphSpec` — G1 full hand-computed metrics, components and coreness<br>`IndependentPhase6DEGraphSpec` — G2 star, G3 K4, G4 path and isolated node have exact coreness<br>`IndependentPhase6DEGraphSpec` — G1 selected paths have unique shortest route, no-path status and supported hop evidence<br>`IndependentPhase6DEGraphSpec` — G1 bridges under the declared partition and G2 star leaves<br>`AdversarialGraphShapesSpec` — ring barbell and clique-pendant graphs have exact degree weighted degree components and coreness<br>`AdversarialGraphShapesSpec` — new graph shapes yield hand-derived shortest routes and disconnected no-path evidence<br>`AdversarialGraphShapesSpec` — declared barbell and pendant partitions have exact bridge measures for every node | Added a C5 ring, weighted barbell, K4 with two pendants and isolate; literal oracles cover all 18 nodes, supported shortest paths and bridges under a declared partition. |
| 9. Large teams/common-name resolution | 6 | 4 | `IndependentDblpJsonSpec` — PrepLimits pairCount stays overflow-safe at Int.MaxValue team size<br>`IndependentPhase6CGraphSpec` — a cross-DBLP accepted link does not collapse two exact DBLP names<br>`IndependentResolutionEngineSpec` — different direct ORCIDs cannot merge through equal name and shared OpenAlex author hypothesis<br>`IndependentResolutionEngineSpec` — matching direct identifiers use exact path without treating work equality as author equality<br>`IndependentRuntime9AResolverSpec` — common name abstains with both identities even when one confidence is higher<br>`IndependentRuntime9AResolverSpec` — exact homonym suffix resolves its identity while the published base alias stays ambiguous<br>`AdversarialDataPlaneSpec` — 64 repeated common-name mentions yield exactly 2016 distinct ordinal pairs<br>`AdversarialDataPlaneSpec` — 64-author expansion one pair over budget rejects atomically without partial pairs<br>`AdversarialDataPlaneSpec` — reordered repeated names retain source ordinals without asserting researcher equality<br>`AdversarialDataPlaneSpec` — Latin Cyrillic confusables and DBLP homonym suffixes stay distinct identities | Large-team expansion uses new 64-mention, 2,016-pair and budget cases. Existing actual ResolutionEngine tests refuse name/work equality as sufficient researcher identity and prioritize conflicting direct ORCID over equal names/shared OpenAlex hypotheses. Already-committed ResearcherResolverAgent tests explicitly exercise Wei Wang ambiguity with confidence 0.99 versus 0.51 and suffix identity resolution; reused as existing evidence only, no 11B runtime implementation. New suffix/confusable canonical-ID test cross-mapped. Synthetic fixture evidence does not establish population common-name accuracy. |
| 10. Missing metadata | 1 | 1 | `IndependentResolutionEngineSpec` — missing evidence stays unavailable rather than zero, perfect similarity or prep sentinel<br>`AdversarialDataPlaneSpec` — bare publication metadata never invents topics institutions abstract or profile identity | Sparse public parser missing institution/topic/abstract/profile metadata and missing ID evidence; ER unavailable features remain unavailable. |
| 11. Replay/output gates | 4 | 1 | `IndependentHadoopPipelineSpec` — OutputGate refuses occupied output and failed pipeline run skips completion marker<br>`IndependentHadoopPipelineSpec` — LocalJobRunner sample replay export is logically equivalent across two run ids<br>`IndependentPhase6DEGraphSpec` — two runs on the same G4 graph produce identical metric, core and component rows<br>`IndependentPhase6SafetySpec` — output gate refuses partial mismatched and tampered runs and reuses only the identical manifest<br>`AdversarialBlockingReplaySpec` — permuted eight-member replay retains all 28 pairs and identical sorted-row SHA256 | Added byte-exact sorted output and independent SHA256 over real candidate jobs with reversed inputs; full Hadoop/Spark pipeline replay/output gate already tested. |

ExposedDefect: **0**. No production defect was exposed by these runs. No new tests were tagged, skipped, ignored or quarantined; the existing live-AWS profile exclusion remains in place; no build-engineer exclusion needed and no empty defect run represented as verification. Exact empty defect inventory: evidence/11a/defects.json. Previously registered findings remain open under their original owners. Runtime categories 12–20 await 11B.

VALIDATION RESULTS:

All 45 mapped cases exist in source and in fresh JUnit reports. Nine per-group log totals sum to 1,231. All three new source hashes stayed frozen during the final check; protected 346 tracked source/config fingerprints match. No production changes. Independent expected outputs are literal mathematical/graph expectations, not captured implementation output. Mutation checks below are thought experiments, not executed production mutations:

1. Removing NFC normalization breaks successful composed/decomposed ID equality; separate text and mention checks prevent parse erasure from satisfying the test.
2. Merging confusables or dropping homonym suffixes breaks four-ID distinctness and the literal normalization expectations.
3. Dropping or duplicating a large-team pair breaks the exact 2,016 unique pairs, complete ordinal set or 63 incidences per ordinal.
4. Emitting partial overflow output or bypassing candidate bounds breaks single-reject row assertions; counters also require all 257 input rows to be consumed.
5. Confusing degree, weight and coreness fails at K1 (degree 5, core 3) or B3/B4 (degree 3, weight 5, core 2).
6. Returning a detour or unsupported hop breaks literal shortest routes, distances and work-support assertions.
7. Using weighted participation instead of documented unweighted participation produces 12/25 on the barbell bridge, rather than the required 4/9. The pendant hub separately requires 14/25.
8. Input-order dependence or dropped members breaks sorted-row equality, exact 28 pairs, seven incidences per member or the hash-sensitivity assertion.

ASSUMPTIONS: Synthetic records declare provenance; source mention ordinals differ from resolved researcher identity. Graph StableIds construct opaque lookup keys, not expected metrics. The fixed bridge partition is declared test input; all 18 node outputs are checked, including zeros. The replay digest is computed independently with standard SHA256 and accompanied by exact pair-count, completeness and hash-sensitivity assertions.

RISKS: Fixtures are synthetic and local. No live AWS/profile, paid provider, EMR, scale, throughput, cost, population identity accuracy or general injection-resistance result is claimed. Replay hashes establish observed equality for the tested candidate-stage inputs; existing pipeline/gate tests cover the broader paths. Fixed-partition bridge expectations do not establish LPA convergence or betweenness. Earlier Phase 5 calibration/evaluation and Phase 6 convergence/approximation/EMR limits remain, as do Phase 7–10 carried findings. Runtime categories 12–20 are deferred to 11B, whole-repository review and production repairs to 11C. No optional OpenSearch/index/service/CI/coverage-tool work was added.

Reading scope is disclosed in `evidence/11a/reading-ledger.json`: relevant contracts, module README sections and all earlier report files' active final/risk/disposition sections were inspected; historical bodies were not reread line-for-line. Initial large reads truncated and were followed by narrower active-disposition reads. Raw logs remain in `/tmp` and are not durable across reboot; meaningful line-numbered excerpts and raw SHA-256/byte counts are retained. Exact inherited model revision was unavailable and is not invented.

MANUAL ACTION REQUIRED: User-run external read-only review and approved commit; later runtime 11B and whole-repository 11C prompts separate. No reviewer was launched and no self-approval inferred.

BLOCKED-ON OWNER: None for current implementation and tests; reviewer/human own next acceptance.

BLOCKED-ON EVIDENCE: None for local 11A gate. Live/distributed behavior and independent approval remain unverified.

NEXT GATE: Return reviewer prompt and stop after 11A. No 11B implementation, production repair, cloud/provider call or commit/push.

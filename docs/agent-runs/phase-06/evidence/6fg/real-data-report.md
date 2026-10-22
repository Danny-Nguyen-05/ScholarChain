# Bounded local real-data results — Subphase 6F+6G

Run: `run:f02acf56-4bea-4009-adaf-b11d5afceb49`. Spark `3.5.4`, Java `17.0.20.1`. The successful first run took 180.45 seconds. All measurements below come from retained `local-run-metadata.json`, `analytics-report.json`, `local-counters.json`, and `event-log-summary.json`.

## Replay scope correction (repair round 1, F2)

The **28 logical Parquet tables and counters matched** in the observed replay.
The operational **`analytics-report.json` did not match** and is excluded from
that logical-identity claim. Distribution values below belong to the first
successful run. A structured comparison found **12 differing numeric fields**:
one approximate percentile and eleven floating-point means. For example,
`bridges[1].participationCoefficientP50P90[1]` is **0.56** versus
**0.5595567867036011**. Approximate quantile aggregation and floating-point
summation order can vary with physical partitioning. Full paths/values and both
file hashes are in [analytics-report-comparison.json](repair-1/analytics-report-comparison.json)
and the updated [replay-comparison.json](replay-comparison.json), whose
`allLogicalTablesEqual` is true and `allComparedArtifactsEqual` is false.

The distance-estimate table also uses `percentile_approx`. Its six P90 values
happened to match in this replay and are included in the observed table hashes;
that result does not prove partition invariance for other inputs. No production
algorithm, retained output, code fingerprint or run ID was changed for this
repair. Approximate reports are not exact distribution/replay guarantees.

## Inputs and limits

Pinned DBLP release 2026-10-03; 10,577 publications, 21,819 exact author strings, all eight approved venues and all years 2005–2026. This is a source-order/per-venue-capped convenience slice, not a representative estimate of DBLP or a researcher's complete publication history. The one 1,107,081,001-byte archive download took 244.720 seconds, within the approved 1.25 GiB/30-minute caps; extraction replay needed no network. Slice SHA-256: `c25a1e1a0d517abaadf370c88b3528039c50ad8ec3790c27381a3c2e2ecde522`.

The unchanged Hadoop pipeline retained its team limit of 16: 63 oversized teams and 21 authorless records are disclosed in preparation counters rather than silently truncated by acquisition. Existing local OpenAlex/Crossref/ORCID samples also flowed through the unchanged CLI; all snapshot/retrieval bindings are retained in the Hadoop and final core run manifests. ER compared its bounded 20,000 candidates with adjudication disabled (fake calls 0, live calls 0); no identity accuracy or calibration is claimed. The first ER export hit its 256 MiB output bound; retry used a 2 GiB local output bound and exported 794,017,153 bytes. Match policy, input records and model mode were unchanged.

## Graph and output counts

Counts below describe complete stored logical tables. Windowed tables sum rows across six windows; they are not counts of distinct people/edges across time. `nodes/type=work_sources` is a supplemental S3 evidence projection, not another GraphNode type.

| Dataset | Rows |
| --- | ---: |
| nodes/type=researcher | 21,819 |
| nodes/type=author_mention | 45,591 |
| nodes/type=work | 10,578 |
| nodes/type=venue | 112 |
| nodes/type=institution | 1 |
| nodes/type=topic | 3 |
| edges/type=authored | 44,083 |
| edges/type=resolves_to | 45,587 |
| edges/type=published_in | 10,579 |
| edges/type=affiliated_with | 0 |
| edges/type=has_topic | 3 |
| nodes/type=work_sources | 10,578 |
| edges/type=coauthored_with | 228,715 |
| edges/type=coauthored_with_support | 269,753 |
| metrics/type=researcher_collaboration | 62,757 |
| metrics/type=components | 62,757 |
| metrics/type=component_summaries | 3,942 |
| metrics/type=communities | 62,757 |
| metrics/type=community_summaries | 10,098 |
| metrics/type=cross_community_edges | 17,589 |
| metrics/type=bridges | 62,757 |
| metrics/type=kcore | 62,757 |
| metrics/type=temporal_changes | 32,649 |
| metrics/type=path_length_estimate | 6 |
| path-evidence | 120 |
| semantic-summaries | 100,765 |
| integrity/violations | 25 |
| integrity/rejects | 0 |

All-years coauthorship has **81,181** unique undirected edges. Identity has 21,819 researchers; all-years metrics cover 20,967 active researchers with retained authoritative team memberships. Oversized-team exclusions and enrichment-only records explain why identity and analytic populations need not be identical. Researcher IDs remain DBLP exact-name identities; ORCIDs are observed external facts, not evidence of a verified identity merge.

## Components and communities

| Window | Active researchers | Components | Largest size | Largest fraction | Singletons | Communities | Size min / median / p90 / max | LPA iterations / final changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2010-2014 | 4,506 | 429 | 2,631 | 0.58388815 | 37 | 903 | 1 / 4 / 11 / 97 | 20 / 372 |
| 2015-2019 | 6,637 | 579 | 3,965 | 0.59740847 | 61 | 1,220 | 1 / 4 / 11 / 45 | 20 / 430 |
| 2020-2026 | 11,088 | 591 | 8,431 | 0.76037157 | 62 | 1,645 | 1 / 5 / 14 / 100 | 20 / 504 |
| all-years | 20,967 | 1,045 | 17,179 | 0.81933515 | 178 | 3,097 | 1 / 4 / 14 / 209 | 20 / 1349 |
| since-2015 | 15,651 | 763 | 12,583 | 0.80397419 | 107 | 2,260 | 1 / 4 / 15 / 224 | 20 / 793 |
| through-2009 | 3,908 | 535 | 1,830 | 0.46827021 | 76 | 973 | 1 / 3 / 9 / 68 | 20 / 524 |

**Every observed window reported LPA non-convergence at 20 iterations.** Synchronous LPA swaps labels indefinitely on every isolated two-person component; final partitions are iteration-limited results, not a claim of a converged or uniquely true community structure. Per-window convergence/iteration values are persisted. Connected components converged in 17 global rounds and k-core in 16; both retain hard non-convergence guards.

## Metric distributions

P50/P90 are Spark `percentile_approx` values with accuracy 10,000. Display values are rounded; the retained JSON preserves the actual numerical results. C = distinct coauthors, T = coauthor occurrences, A = T/P, M = maximum coauthors on one paper, W = weighted degree. No combined collaboration score is introduced.

| Window | Metric | Min | Median | P90 | Max |
| --- | --- | ---: | ---: | ---: | ---: |
| 2010-2014 | C | 0 | 4 | 10 | 48 |
| 2010-2014 | T | 0 | 4 | 12 | 84 |
| 2010-2014 | A | 0 | 3.5 | 6 | 13 |
| 2010-2014 | M | 0 | 4 | 7 | 13 |
| 2010-2014 | W | 0 | 4 | 12 | 84 |
| 2010-2014 | coreness | 0 | 4 | 7 | 13 |
| 2015-2019 | C | 0 | 5 | 11 | 75 |
| 2015-2019 | T | 0 | 5 | 13 | 98 |
| 2015-2019 | A | 0 | 4 | 7 | 14 |
| 2015-2019 | M | 0 | 4 | 8 | 14 |
| 2015-2019 | W | 0 | 5 | 13 | 98 |
| 2015-2019 | coreness | 0 | 4 | 8 | 14 |
| 2020-2026 | C | 0 | 6 | 15 | 142 |
| 2020-2026 | T | 0 | 6 | 18 | 223 |
| 2020-2026 | A | 0 | 5 | 10 | 15 |
| 2020-2026 | M | 0 | 5 | 11 | 15 |
| 2020-2026 | W | 0 | 6 | 18 | 223 |
| 2020-2026 | coreness | 0 | 5 | 11 | 15 |
| all-years | C | 0 | 5 | 15 | 247 |
| all-years | T | 0 | 5 | 18 | 455 |
| all-years | A | 0 | 4 | 8.5 | 15 |
| all-years | M | 0 | 5 | 10 | 15 |
| all-years | W | 0 | 5 | 18 | 455 |
| all-years | coreness | 0 | 5 | 10 | 15 |
| since-2015 | C | 0 | 6 | 15 | 186 |
| since-2015 | T | 0 | 6 | 18 | 319 |
| since-2015 | A | 0 | 4.6 | 9 | 15 |
| since-2015 | M | 0 | 5 | 11 | 15 |
| since-2015 | W | 0 | 6 | 18 | 319 |
| since-2015 | coreness | 0 | 5 | 11 | 15 |
| through-2009 | C | 0 | 3 | 9 | 49 |
| through-2009 | T | 0 | 4 | 11 | 87 |
| through-2009 | A | 0 | 3 | 5.5 | 13 |
| through-2009 | M | 0 | 3 | 6 | 13 |
| through-2009 | W | 0 | 4 | 11 | 87 |
| through-2009 | coreness | 0 | 3 | 6 | 13 |
| 2010-2014 | participation | 0 | 0 | 0.54166667 | 0.88265306 |
| 2015-2019 | participation | 0 | 0 | 0.56 | 0.88957476 |
| 2020-2026 | participation | 0 | 0.16528926 | 0.6255144 | 0.92211579 |
| all-years | participation | 0 | 0.24489796 | 0.66666667 | 0.94455 |
| since-2015 | participation | 0 | 0.24 | 0.66666667 | 0.95640909 |
| through-2009 | participation | 0 | 0 | 0.5 | 0.89256198 |

Bridge degree/weight/communities-connected distributions are also retained in `analytics-report.json`. Participation is unweighted and partition-dependent; these measures are not betweenness or proofs of articulation.

## Paths and seeded distance estimate

The run selected K=20 deterministic pairs per window (seed 441), 120 total: 72 found within six hops, 48 exceeded maxHops, zero cross-component no-path selections and zero missing benchmark endpoints. No benchmark pairs were configured for this real run. G1 and adversarial selected-pair paths are independently tested.

The estimate chooses S=32 seeded source researchers in each largest component and performs complete distributed BFS until reachability is exhausted, independently of the selected-pair six-hop limit. It aggregates ordered distinct non-self source/target distances, not all-pairs distances. The reported P90 is empirical effective diameter, not exact diameter.

| Window | Sources | Reached ordered pairs | Mean distance | Effective P90 |
| --- | ---: | ---: | ---: | ---: |
| 2010-2014 | 32 | 84,160 | 7.14591255 | 10 |
| 2015-2019 | 32 | 126,848 | 7.22559284 | 10 |
| 2020-2026 | 32 | 269,760 | 5.87784327 | 8 |
| all-years | 32 | 549,696 | 5.62367199 | 7 |
| since-2015 | 32 | 402,624 | 5.82332648 | 8 |
| through-2009 | 32 | 58,528 | 7.00514284 | 10 |

## Integrity and source coverage

25 non-hard integrity warnings flag conflicting DBLP-observed ORCIDs without splitting exact-name researchers. Hard failures: 0; missing graph endpoints: 0; pair-count mismatches: 0; Spark malformed input lines: 0. The 25 warning rows are published under `integrity/violations`; an intentionally failed prior runtime attempt retains its own failure evidence and has no completion marker. ER decision counts read through the real export: researcher unresolved/conflict 0/0, work unresolved/conflict 1,627/12,123. These are abstention/conflict outcomes, not accuracy measurements. Enrichment-only coauthorship works excluded: 1; unresolved Spark mention mappings: 4; works beyond the last bounded year: 0. All five bounded-window yearless-work counts are 0 for this dated slice.

## Spark stages and output paths

The original event summary contains 2,004 executed stage attempts, 5,237 task completions, 0 failed tasks. Sum of per-stage partition counts: 5,237; maximum partitions in one stage: 55. Shuffle read: 12,020,965,863 bytes / 120,211,169 records. Shuffle write: 10,107,558,658 bytes / 101,023,634 records. `durationMs` is summed task elapsed time (277,478 ms), not stage wall time; executor runtime sums to 264,378 ms. Full per-stage values are in `event-log-summary.json`.

First completed output: `target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49`. The four load-manifest arrays, core manifest, metadata, counters, plans, event summary and analytics report exist under that root. Pre-checkpoint algorithm plans and export plans are saved; rendered plan strings are capped at 65,536 characters to bound driver memory, so complex plans may be visibly truncated. Physical timing, part names and plan text are excluded from logical replay equality.

The replay uses a fresh output/checkpoint root and two shuffle partitions instead of four. Its completion and every-table hash comparison are recorded separately in `replay-comparison.json` after execution. No AWS, store load, embeddings, live LLM or EMR runtime is claimed. EMR remains deferred to Phases 13/15.

## Completed replay

The second fresh run completed in **158.07 seconds**, exit **0**, using two
shuffle partitions. Both runs have `run:f02acf56-4bea-4009-adaf-b11d5afceb49`
and identical compiled code/logical config identities. All **28/28** table row
counts/content hashes and the full counter arrays match. Completion hashes
verify on both roots. The four load-manifest files are byte-identical, with
13 Neptune, 11 DynamoDB, 1 S3 Vectors and 28 S3 dataset proposals. Every listed
Parquet directory exists; physical part-file counts differ (153 versus 136),
as allowed. There are 37 saved plan files per run. These observations are
retained in `replay-comparison.json` and `manifest-file-audit.json`.


## Stage DAG evidence (repair round 1, F1)

The original production event summarizer omitted stage names and parent IDs.
That gap is supplemented from the retained successful raw event log without
changing production code or rerunning Spark:

- [Complete stage DAG](repair-1/stage-dag.json): stage ID/attempt, name, parent
  IDs, partition count and per-stage task, duration and shuffle totals.
- [Stage DAG overview and actual subgraph](repair-1/stage-dag.md).

There are **5,667 stage IDs** and **4,532 parent edges**, including **3,663
referenced ancestor stages without task events**. Every stage name and partition
count is present; every parent resolves and the graph is acyclic. Totals for all
**2,004 executed attempts** exactly match the original retained stage summary:
5,237 tasks, zero failed tasks, 12,020,965,863 shuffle-read bytes and
10,107,558,658 shuffle-write bytes. The complete DAG includes skipped/referenced
ancestor stages rather than treating all references as newly executed work.
The artifact records raw log path/size/SHA-256 and the derivation method.

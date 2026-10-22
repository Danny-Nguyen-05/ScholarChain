# Phase 6 routed findings and repairs

## Subphase 6A — repair round 1

The user supplied a read-only external `REQUEST-CHANGES` review, retained in `review.md`, then instructed: **"Fix F1, F2, F3 please"**. The user separately approved one minimal independent SparkSession startup probe under `tests/**`. This round is limited to those three findings. No reviewer was launched by the coordinator.

| Finding | Reviewer status and owner | Round 1 disposition |
|---|---|---|
| F1: `independentTests` cannot start Spark on JDK 17; classpath claim lacks retained proof | High, blocking. `build-engineer` for `build.sbt`/`project/**`; `test-engineer` for approved probe under `tests/**`; coordinator for evidence | **Repaired, pending external recheck.** The build owner applied shared fork/JDK 17 options and repository-root working directory. The independent probe passed; the full independent suite passed 234/234 and the full gate passed 474/474. `repair-1/independent-classpath-proof.txt` shows fork, options, Spark SQL 3.5.4 and scala-reflect 2.13.14. |
| F2: duplicate SLF4J providers and Logback bundled in job JAR | Medium, nonblocking; `build-engineer` | **Repaired, pending external recheck.** The build owner removed direct Logback from Spark test projects, added a shared WARN-level log4j2 test resource, excluded Logback from Spark packaging and added a package rejection test. The final check has no SLF4J duplicate-provider warning or DEBUG lines. The rebuilt 4,798-entry JAR listing has no Spark/Hadoop/Logback/provider paths. |
| F3: packaged Scala library patch version versus a prospective Spark Scala-2.13 runtime | Medium, nonblocking 6H feasibility; `infra-engineer` research, `build-engineer` packaging context, coordinator memo | **Research and 6H validation plan completed, pending external recheck.** `emr-compatibility.md` and `repair-1/f3-research.md` distinguish Spark's upstream 2.13.8 build profile from the local job JAR's 2.13.14. Official Scala policy says the patch difference alone is not proof of incompatibility. Inventory, alignment, class-origin and bounded-runtime checks remain a 6H gate. |
| F4: wrong-JDK evidence predates final tree | Low, nonblocking; `build-engineer`/coordinator | **Deferred by the user's F1–F3 scope.** Existing guard evidence remains dated; rerun if later requested or required for release. |
| F5: plan hash and model/tool provenance | Low, nonblocking; coordinator | **Deferred by the user's F1–F3 scope.** Reviewer-observed plan hash is recorded in the review; no new provenance claim is invented. |
| F6: packaging lacks Java 17 guard | Low, nonblocking; `build-engineer` | **Deferred by the user's F1–F3 scope.** Packaging risk remains for a later build-owned repair before release. |
| F7: 6C shared Spark harness settings | Informational future scope; `spark-engineer` | **Future 6C scope.** No 6A smoke-spec change. |
| F8: "Spark classes" wording | Informational; `build-engineer` | **Deferred by the user's F1–F3 scope.** |
| F9: evidence size | Informational; coordinator | **Deferred.** Keep the full existing final-gate log; repair output will be retained lean where possible. |

Starting repair state: branch `phase-6`, HEAD/base `03493882399e9020e6892c9f97e0ec8919365215`; previous 6A changes uncommitted. The user explicitly asked for this repair round, so work proceeds on the same tree without implying prior approval or a commit.

## External recheck disposition

The user-supplied external reviewer returned **APPROVE** for 6A repair round 1. F1 and F2 are closed with runtime/package evidence; F3 is closed as research while the 6H runtime check remains open. F4–F6 and F8 remain nonblocking/deferred, F7 is 6C scope, and F9 is mostly resolved by reduced logs. The reviewer added R1 (low, nonblocking): two report statements overstated the filtered evidence. The coordinator reworded those statements in `owner-report.md` and `test-report.md` as an editorial evidence correction after review; no implementation, test or package artifact changed. The next gate is the user's 6A commit, then a separate 6B prompt.

## Subphase 6B — repair round 1

The complete user-supplied independent `REQUEST-CHANGES` review is retained in `review.md`. The user instructed **"Fix F1, F2, F3, F4 for me"** and selected **"yes, use chunkOrProfileId"** for F2. This round is limited to F1–F4 implementation; F5–F8 remain named future items. Branch and base/current HEAD are `phase-6` and `bc1e4a17fc879b7aac254b28d83e78dbdd34e367`; the 6B tree remains uncommitted.

| Finding | Severity, owner and blocking status | Round 1 disposition and evidence |
|---|---|---|
| F1: `ResearcherMetricsDetail` check omits frozen metric invariants and max-team work/tie rules | High, **blocking**; `domain-engineer`, `modules/core/**` | **Repaired, pending external recheck.** `SparkAnalyticsValidation.check` mirrors the frozen C/T/M, zero, average tolerance, P×M and coreness checks, and enforces the new work/tie rules. A negative case covers each rule in `SparkAnalyticsContractSpec`; targeted 11/11 and full 485/485 passed in `evidence/6b/repair-1/`. |
| F2: summary ID formula and docs disagree; window is absent from example ID | Medium, **blocking**; `domain-engineer` for core and `spark-engineer` for `modules/spark/README.md` | **Repaired, pending external recheck.** `StableIds.sparkSemanticSummaryId` calls `chunkOrProfileId` with `sourceVersion` formed from policy and window. The validator accepts only this form, the example snapshot was regenerated, both READMEs agree, and a test proves identical text in two windows yields different IDs. |
| F3: missing ID, config-window and G1 J/no-path feature cases | Medium, **blocking**; `domain-engineer`, `modules/core/**` | **Repaired, pending external recheck.** Tests cover NFC equivalence; malformed DBLP IDs; unknown analytics kind; duplicate, reversed, overlapping, gapped and open-middle windows; duplicate comparison order; invalid endpoint kind; G1 J's solo metric/singleton component; and A-to-H no-path evidence. Targeted 11/11 and full 485/485 passed. |
| F4: Spark edge IDs cannot be cited through `EvidenceItem`; new edge ID deviates from plan | Medium, **nonblocking**, user requested repair; `domain-engineer` for additive locator acceptance/test, coordinator for deviation record | **Repaired for citation compatibility, pending external recheck.** `StableIds.nonTextEvidenceId` and `DomainValidation.check(EvidenceItem)` accept `spark-coauthor-edge:` as an edge locator, with positive and negative tests. The `SparkCoauthorEdge` ID binds a window ID to support unbounded all-years and yearless works; this is an intentional additive deviation from plan §7.3's `coauthorEdgeId` instruction. Frozen `CoauthorEdge` and ID formula remain untouched. The yearless edge's Neptune `GraphEdge`/`CoauthorshipProperties` mapping still needs a domain/storage design before Phase 7 loading, with `storage-engineer` as downstream owner and domain contract support as needed. |
| F5: other single-record invariants | Low, **nonblocking**; `domain-engineer` | **Deferred by user's F1–F4 scope.** Domain-owned contract hardening is due before the relevant 6D–6E producers rely on these checks; no F5 success is claimed in this repair. |
| F6: window labels are not bound to numeric bounds | Low, **nonblocking**; `domain-engineer` | **Deferred by user's F1–F4 scope; rescheduled to 6C after external recheck R2.** Resolve label/bounds identity or document the cross-run limitation during 6C Step 0, before Job 2 emits window-bound edge IDs. |
| F7: deterministic run ID and logical fingerprint scope | Low, **nonblocking**; `domain-engineer` and user for fingerprint-scope decision | **Deferred by user's F1–F4 scope; rescheduled to 6C after external recheck R2.** During 6C Step 0, ask which config fields belong to the logical fingerprint, then define/test a deterministic valid run ID before the 6C run-manifest builder uses it. Current 6B README claim is a proposal, not an observed implementation. |
| F8: load-manifest target details, yearless window scaladoc and post-2026 exclusion | Informational, **nonblocking**; `storage-engineer` for Phase 7 mapping, `domain-engineer` for scaladoc on demand, `spark-engineer` for 6C counter | **Future scope.** Node-table load-manifest/target mapping goes to Phase 7; 6C should count 2027 works excluded from bounded windows. No F8 implementation in this round. |

## Subphase 6B external recheck disposition

The user-supplied independent reviewer returned **APPROVE** for repair round 1; its complete report is appended verbatim in `review.md`. F1–F3 are closed, and F4 is closed for citation compatibility. F5 remains due before 6D–6E producers depend on those checks; F8 remains future scope. This approval is the reviewer's finding, not a recorded human commit or permission to start 6C.

| Finding | Owner and status | Updated gate |
|---|---|---|
| F6: window-label/bounds identity | `domain-engineer`; deferred and nonblocking for 6B | **6C Step 0 and implementation.** Decide whether to bind numeric bounds into new IDs or validate label-to-bounds consistency before Job 2 emits window-bound edge IDs. Deliver any core helper before `spark-engineer` consumes it. |
| F7: deterministic run ID and logical fingerprint scope | `domain-engineer` for helper; user for fingerprint decision; deferred and nonblocking for 6B | **6C Step 0 and implementation.** Ask which config fields define the logical input fingerprint; implement and test a deterministic valid run ID before the 6C run-manifest builder uses it. |
| R1: `SemanticSummary.entityId` is only checked for nonblank content | Low, nonblocking; `domain-engineer` | Fold summary-type-specific researcher, community, path-evidence and work ID validation into F5 hardening before 6F Job 10 emits summaries. |
| R2: F6/F7 were scheduled too late | Low, nonblocking; coordinator for schedule; `domain-engineer` and user for decisions and helper | **Resolved as scheduling correction.** F6 and F7 are now 6C Step 0/implementation gates as recorded above. |

### Subphase 6C disposition of prior 6B findings

| Finding | Owner and disposition | Evidence and remaining gate |
| --- | --- | --- |
| F6: window-label/bounds identity | `domain-engineer`; **closed in 6C** by the user's choice to bind both numeric bounds and label into new Spark coauthor edge IDs. | `StableIds.sparkCoauthorEdgeId`, core wire snapshots and `SparkAnalyticsContractSpec`; the final JDK 17 `evidence/6c/final-check.txt` has core 142/142. Frozen older ID formulas remain unchanged. |
| F7: deterministic run ID and fingerprint scope | `domain-engineer`; **closed in 6C** by the user's logical-fingerprint choice. | `SparkAnalyticsConfig.logicalFingerprint`, `StableIds.sparkAnalyticsRunId`, core tests, and `evidence/6c/local-run-manifest.json`. The final smoke reused the same logical run ID with a different output root. |
| F5 and recheck R1: additional record invariants and semantic-summary entity-kind validation | `domain-engineer`; **still deferred** to the producer gates before 6D–6F, as applicable. | Neither was changed in 6C. The 6D/6E metric and path producers must not rely on missing F5 rules; Job 10 in 6F must close R1. |
| F8: untyped target mapping and future-date count | `storage-engineer` for Phase 7 mapping, `spark-engineer` for 6C future-date behavior. | The 6C module and independent tests cover a 2027-dated DBLP work in all-years only. Target mapping remains a Phase 7 proposal. |

## Subphase 6C — repair round 1

The user supplied an independent read-only `REQUEST-CHANGES` review and asked to fix all blocking bugs. The review was delivered in two messages and is retained in `review.md`. This round addresses F1–F5 only. Branch `phase-6`, base/HEAD `01d204b531d3fc72a5c49f884980a5c7c8926b18`; the 6C tree remains uncommitted. No reviewer is launched by the coordinator.

| Finding | Severity and owner | Disposition and acceptance evidence |
| --- | --- | --- |
| F1: all DBLP team observations in a canonical group are selected rather than the rank-1 authoritative observation | High, **blocking**; `spark-engineer` for `modules/spark/**`, `test-engineer` for `tests/**` independent case | **Repaired, pending external recheck.** Memberships and pairs use only the selected authoritative observation; a dropped-observation counter was added. Module 14/14, independent 6/6 and full 507/507 passed on the final tree. |
| F2: conflicting DBLP-observed ORCIDs are not reported | Medium, **blocking**; `spark-engineer`, `test-engineer` for independent case | **Repaired, pending external recheck.** One non-hard integrity row and counter per conflicting name group, preserving its researcher ID; module and independent cases passed. |
| F3: missing graph endpoints disappear when the hard-invariant flag is off | Medium, **blocking**; `spark-engineer` | **Repaired, pending external recheck.** Missing endpoints produce hard-failure integrity rows and a counter with the flag off; the flag-on path throws. Both module paths passed. Persisting an aborted run before the exception remains a 6F gate. |
| F4: ER unresolved and conflict exports are not read or counted | Medium, **blocking**; `spark-engineer` | **Repaired, pending external recheck.** Both outputs for each entity type use explicit schemas and the reject path. Fresh real-data smoke counters were 6/0 researcher unresolved/conflict and 0/3 work unresolved/conflict. |
| F5: required 6C module feature cases and literal G1 table are absent | Medium, **blocking**; `spark-engineer` | **Repaired, pending external recheck.** The 14/14 module suite covers all reviewer-listed grouping, marker, inventory/hash and literal 18-edge G1 cases; full gate passed. |

At the start of this repair round, the supplied review fragment referred to nonblocking N findings without their descriptions, so no disposition was then invented. The later approval supplied their text; the register below now routes them.

### External repair-round recheck and completion work

The user supplied an external recheck report showing F1–F5 source changes and substantive tests, but withholding approval on two blocking points. The user asked to fix all those blockers. The supplied recheck report is appended in `review.md`; it did not include the full text of any other observations, including its reference to R1-5.

| Recheck finding | Owner and status | Completion check |
| --- | --- | --- |
| R1-1: missing or stale repair evidence after later Readers/Main/module-spec edits | **Blocking**; `spark-engineer` for module targeted run and `coordinator` for retained evidence, smoke, full gate and reports | **Closed locally, pending external recheck.** Final-tree module 14/14 and independent 6/6 targeted tests, fresh real-data smoke and bounded Parquet counter probe passed. Full JDK 17 check exited 0, **507/507**; `git diff --check` exited 0. Logs, 253,775-byte full-gate SHA-256 `6c0fdf7494269c2ccb71a8cdbee35cb36b4c574b4d3d34928e2e37352c5a7773`, smoke manifest and exact counter output are in `evidence/6c/repair-1/`; `owner-report.md` and `test-report.md` now report this round. |
| R1-2: run ID reused after a semantic change to the canonical graph | **Blocking**; `spark-engineer`, `modules/spark/**` | **Closed locally, pending external recheck.** `Phase6CMain.codeVersion` is `spark-phase6c-jobs1-2-v2`; the module test rejects the v1 reuse manifest. Fresh smoke emitted `run:d56e56d9-de03-4862-bc66-46fd5ad27b75`, different from prior `run:50e1fc99-a22c-4993-9525-7772e6af1fac`. |

The full recheck identifies R1-3 and R1-4 as low/nonblocking and R1-5 as a process observation. The user's final instruction limited implementation work to blocking bugs. The external approval subsequently supplied the N1–N9 and "Later gates" text; it is appended verbatim in `review.md` and routed below.

### Approved 6C recheck and future register

The user-supplied external reviewer **APPROVED** 6C repair round 1. F1–F5 and R1-1/R1-2 are closed for 6C with final-tree tests and smoke evidence in `evidence/6c/repair-1/`. This is a reviewer verdict, not a user commit. Branch `phase-6` remains at HEAD `01d204b531d3fc72a5c49f884980a5c7c8926b18` with uncommitted 6C work; the next gate is the user's commit before 6D Step 0.

| Finding | Owner | Nonblocking disposition and gate |
| --- | --- | --- |
| R1-3 / N2: README overstates representative authority; selection infers DOI authority from `doi` instead of `work:doi:` ID and ignores `representativePolicyVersion` | `spark-engineer` | Open. Correct selection or wording before the 6F documentation pass; raise at 6D Step 0 if the 6D producer consumes this representative choice. |
| R1-4: ORCID conflict filter trims but distinct count does not | `spark-engineer` | Open. Normalize consistently before 6F integrity output. |
| R1-5: original nonblocking and later-gate review text was absent | Coordinator | **Closed as evidence recording.** The reviewer supplied those sections in the approval report, now retained verbatim in `review.md` and registered here. No implementation change was inferred. |
| R2-1: local counter probe scripts under docs are not portable tools | Coordinator for evidence; Spark or scripts owner for a later replacement | Open, accepted local evidence. By 6F, use a Spark-module test or a properly owned `scripts/**` tool if replayable counter inspection is needed. |
| N1: hand-maintained `codeVersion` can miss a future semantic change | `spark-engineer` with build owner if a JAR hash is used | Open. Bind a build/git identity before the 6F/6G determinism replay; the v2 bump closed only this specific changed-output collision. |
| N3: null-endpoint accepted links and graph edges lacking evidence work are dropped without counters | `spark-engineer` | Open. Add named counters before final 6F integrity/load output. |
| N4: counter names/meanings disagree; year-exclusion counters repeat; post-2026 threshold is hardcoded | `spark-engineer` | Open. Correct or document before 6D consumes these counters; raise in 6D Step 0. |
| N5: plans are formatted after eager checkpoints | `spark-engineer` | Open. Capture pre-checkpoint plans in 6F. |
| N6: SparkListener instrumentation is acceptable; durable event log/summarizer remains | `spark-engineer` / coordinator evidence | Observation; 6F event-log gate. |
| N7: UDF reason absent from README and `phase6Context` could use literals | `spark-engineer` | Open, low; address in the 6F documentation pass. |
| N8: domain-v1 labels are used for graph tables and a non-Researcher-shaped researcher node table | `domain-engineer` for contract, `spark-engineer` for layout | Open. Resolve with 6F table/load-manifest layout before consumers rely on schema labels. |
| N9: coordinator ran scalafmt on Spark-owned files in original 6C work | Coordinator / `spark-engineer` | Process observation; disclosed and owner-confirmed. No further 6C action. |

Later gates retained from the reviewer: prior 6B F5/recheck-R1 domain hardening before 6D–6F producers; 6F Job 11 layout, hashes, load manifests, hard-failure persistence and event-log summary; Phase 7 yearless Neptune mapping; 6H Java 17 packaging guard and live EMR compatibility. No cloud result is claimed in 6C.

## Subphase 6D+6E prerequisite and deferred-item disposition

The user committed 6C as `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4` and requested the merged 6D+6E implementation under the shortened plan. The following dispositions extend the historical register without rewriting prior review or human decisions.

| Item | Owner | 6D+6E disposition |
| --- | --- | --- |
| Prior 6B F5: bridge/community/path/config local invariants | `domain-engineer` | Implemented under `modules/core/**` with negative feature cases: cross-community weight versus degree, zero-cross-degree participation, community convergence and changed-count agreement, cross-edge weight versus count, found-path max hops/distinct endpoints/no repeated node, window-label syntax, and DBLP benchmark names resolving to one ID. Targeted contract suite passed 14/14; final full-gate evidence is reported in the 6D+6E reports. No wire field or ID formula changed. |
| Prior 6B recheck R1: semantic-summary entity-kind validation | `domain-engineer` | Still assigned before Job 10 in 6F+6G; this run emits no semantic summaries. |
| 6C N4: diagnostic counter names and meanings | `spark-engineer` | The new jobs consume 6C memberships, edges and support, not its diagnostic counters. The 6DE README explicitly states this boundary. Renaming or revising 6C counters remains the 6F+6G final-output gate; no 6C run identity or output is changed in this run. |
| 6C N2/R1-3, R1-4, N1/N3/N5/N7/N8 and R2-1 | Assigned owners in the 6C register | Remain the named 6F+6G documentation, identity, integrity, layout or evidence gates. 6D+6E extends the committed canonical tables without rewriting jobs 1–2. |
| S-source sampled mean distance/effective diameter | `spark-engineer`; user-approved scope choice | Deferred under the user's 6DE-3 answer to prioritize selected-pair BFS. `pathLengthEstimates` is an empty typed table; no sampled-distance result is claimed. Seeded K-pair selection and selected-pair BFS are implemented and tested. |
| Optional sampled betweenness | User decision | Omitted as requested in 6E-2. The required partition-dependent bridge measures are implemented. |
| 6H EMR work | Later phase owners | The updated plan defers the script to Phase 13 and the live run to Phase 15. Phase 6 retains that gate as open; no cloud compatibility result is claimed. |

During coordinator implementation checks, the first BFS draft was found to order entire routes when §7.6 requires the smallest immediate predecessor. The Spark owner changed the candidate ordering to predecessor first and full route second, and added a module fixture where the choices disagree. The independent test owner added a separately authored fixture for the same rule. The repaired targeted suites passed 9/9 and 10/10 (`module-predecessor-targeted.txt` and `independent-predecessor-targeted.txt`). The earlier full check was stopped as superseded (exit 143, retained as `superseded-check.txt`); it is not reported as a passing gate. The final full check runs only on the corrected tree.

Final corrected-tree gate: JDK 17 `sbt -batch check` exited **0**, **527 passed / 0 failed** (143/64/39/24/250/7), real **567.12 s**. `evidence/6de/final-check.txt` is **285,463 bytes**, SHA-256 `bd8b9a28348839769b5410364c3f7893fe37bb1c871eac27d7595fba75dbca34`. `git diff --check` exited 0. These are implementation validation results; external 6D+6E review is still pending.

## Subphase 6D+6E — repair round 1 (external F1–F3)

The complete user-supplied external `REQUEST-CHANGES` review is retained in `review.md`, including N1–N9 and future gates. The user requested **all blocking fixes**. Existing Step 0 choices remain binding; the resource is corrected to those choices rather than changing the decision. Base/HEAD remains `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4` on `phase-6`, preserving the uncommitted implementation.

| Finding | Owner and blocking status | Repair round 1 disposition |
| --- | --- | --- |
| F1: shipped config retains 100/100/K32 instead of approved 50/50/K20 | High, blocking; `domain-engineer` resource/core test, `spark-engineer` README | **Repaired, external recheck pending.** Full gate 528/528, exit 0. The shipped resource is CC50/k-core50/checkpoint5/community20/maxHops6/K20/S32/seed441. The core test asserts every value and both fingerprint changes; targeted 14/14 (`repair-1/core-targeted.txt`). README identifies the actual resource and preserves historical 6C output/run IDs. |
| F2: LPA non-convergence lacks feature evidence; README claims nonexistent coverage | Medium, blocking; `spark-engineer` | **Repaired, external recheck pending.** Full gate 528/528, exit 0. The two-person weight-1 fixture runs three iterations, checks every membership/summary is non-converged, summary changed count 2, counters 0/2, and parses actual output rows into core records accepted by validation. `CommunityMembership` has no changed-count field; its existing fields are preserved. Module targeted 10/10 (`repair-1/module-targeted.txt`); README names this exact fixture. |
| F3: report claims both suites cover G1–G4 | Low accuracy, blocking; coordinator | Corrected the inaccurate original report sentence. G1–G4 literal coverage is assigned to the independent suite; module fixtures are A–E, triangle, route ties, ties/caps, sampling and the new oscillating pair. No module G1–G4 claim remains. |

Fingerprint evidence refers to the checked-in example loaded through the core serializer, not to the separate historical 6C smoke config. Full fingerprint changes from `a75347c8ea36964d5144e09a19f8cb76f9de08128868e76f6fad4f8db77b8169` to `8f6fd8b7b5596ece608424278b10b23f61317562d989a6a40d07fad109cd643e`; logical fingerprint changes from `49316f88beb239b6d654b9df77814be759a10f20c7209894e3dc63fbab9cc624` to `f03c79505357ca9795894569c3f7cbf0f67e9d18c864eab9de895bb4a85159f3`. Future runs using the new logical settings bind different deterministic run identity. Existing smoke manifests and IDs are unchanged historical evidence.

| Nonblocking observation | Owner | Disposition / future gate |
| --- | --- | --- |
| 6DE N1: found BFS pairs keep other frontiers; full paths/checkpoint each hop | `spark-engineer` | Deferred by blocking-only scope; optimize and align checkpoint documentation before the 6F+6G real-data run. |
| 6DE N2: reported LPA iterations is global loop count | `spark-engineer` | Fix or document before 6F+6G reporting; nonblocking for this repair. |
| 6DE N3: LPA cache timing can rebuild prior iterations | `spark-engineer` | Performance repair before 6F+6G real-data execution. |
| 6DE N4: inferred nested context field order may differ | `spark-engineer`, core owner if shared contract support is needed | Plausible/unexecuted observation retained as such. Use an explicit shared schema before final manifests/schema hashes in 6F+6G. |
| 6DE N5: missing endpoints share no-path status; sampled counter precedes benchmark dedup | `spark-engineer` | Add missing-endpoint counter and document counter meaning in 6F+6G. |
| 6DE N6: replay omits paths/sampling/LPA/bridges | `test-engineer` / `spark-engineer` | 6F+6G full per-table replay-hash gate. |
| 6DE N7: no DE row-to-core validation tests | `spark-engineer` / `test-engineer` | Partially addressed by F2 for actual community membership/summary rows. Broader output/export record validation remains 6F+6G. |
| 6DE N8: design README differs from implementation in details | `spark-engineer` | Final README and physical-plan pass in 6F+6G. |
| 6DE N9: coordinator executed owner-file formatter | Coordinator | Process note retained. In this round the Spark owner's sandbox command failed before compilation; coordinator executed the owner's supplied formatter/check/test command on owner-authored code. |

Future gates from this review: implement sampled path-length/diameter estimation in 6F+6G or obtain an explicit human acceptance of that deviation in the 6I human gate; the original round did not retain a rationale for why it was not a small addition, and no retrospective rationale is invented here. Report LPA oscillation/non-convergence on real-data windows. Publishing, durable event-log summarization, hard-failure persistence, bounded-window metrics, real-data run and complete replay remain 6F+6G. Prior 6C findings and summary entity validation keep their named owners; EMR script/live work remains in Phases 13/15.

Final repair gate: JDK 17 `sbt -batch check` exited **0**, **528 passed / 0 failed** (143/64/39/25/250/7), real **563.44 s**. `repair-1/final-check.txt` is **286,117 bytes**, SHA-256 `18d9858bc70337879054a388868dede84e19b2f568f12b2e5e50d2d1c833112f`. Core targeted 14/14, Spark targeted 10/10, diff check exit 0. No external approval is claimed.


### External 6D+6E repair-round-1 approval disposition

The user-supplied independent reviewer returned **APPROVE**. Its complete report and NEXT PROMPT are appended verbatim in `review.md`. F1, F2 and F3 are **closed by external recheck**: shipped defaults and fingerprint assertions match the approved choices; the oscillating pair passes through actual core parse/validation and counter assertions; coverage wording is accurate. The reviewer verified the retained 528/0 gate and reported no new blocker. N1–N9 and all later gates remain registered above. This is an external reviewer verdict, not an agent acceptance or a user commit.

| Observation | Owner | Gate / disposition |
| --- | --- | --- |
| R1-O1: two-person components oscillate under synchronous LPA, affecting real-window convergence | `spark-engineer` | Nonblocking for 6D+6E. During 6F+6G, state this consequence in the README and actual real-data report; report observed convergence per window rather than implying convergence is usual. |

Commit check after approval: branch `phase-6` still has HEAD `8d5b9d48b2fbc1f03e13f3eabdef1bfa373969d4` and the approved 6D+6E source/evidence is uncommitted. The supplied NEXT PROMPT and plan require the user's commit before 6F+6G starts. No 6F+6G base or preflight is recorded yet; no next-subphase work has begun.

## Subphase 6F+6G — carried findings and implementation repairs

The user subsequently committed the approved 6D+6E tree as
`6ae7378cbef90a176fd1faecae0dee0615eba9e3`, confirmed "done," and approved all
six 6F+6G Step 0 answers in `prompt.md`. That commit is this subphase's base and
unchanged HEAD. Historical decisions and reviewer reports above are preserved.
The table below records implementation dispositions, not independent approval.
Final stable-tree gate evidence is reported in the 6F+6G test report.

| Prior item | Owner | 6F+6G disposition and evidence |
| --- | --- | --- |
| 6B recheck R1: summary entity kinds | `domain-engineer` | Implemented: researcher/community/path/work IDs must match summary type. Positive and wrong-kind/malformed feature tests; `core-targeted.txt` 15/15. No frozen wire or ID formula changed. |
| 6C N1: hand-maintained code version | `spark-engineer` | Full CLI fingerprints Spark/core compiled production class bytes or code-source JAR bytes. Both successful runs bind code `a6719cbb892e795e3b4e20be99c70c1c74c1ee8ce95887e8c418d9aeb3672971`. Class-directory versus packaged-JAR fingerprints differ; cross-artifact equivalence remains unverified. Historical 6C outputs remain unchanged. |
| 6C N2/R1-3: representative authority | `spark-engineer` | Selection uses work-ID authority, including a DOI work with an absent nullable DOI column; module feature test passes. README documents one deterministic ordered rule. `representativePolicyVersion` is a provenance/fingerprint tag for that rule, not an implemented alternate-policy dispatch mechanism. |
| 6C R1-4: inconsistent ORCID trimming | `spark-engineer` | Aggregation and conflict counting both use trimmed ORCID values; module test proves whitespace alone does not create a conflict. Researcher GraphNodes preserve normalized observed ORCIDs as sorted `orcid.N` NamedText properties without changing identity. |
| 6C N3: silently dropped rows | `spark-engineer` | Explicit null-endpoint accepted-link counters and missing-evidence-work graph-edge counter; reader keeps null links until accounting. Real counts are all zero. |
| 6C N4: diagnostic meanings | `spark-engineer` | Group and link/mention counts are distinguished; yearless canonical DBLP works include solos, counted for every bounded window; last-year threshold derives from config. Module tests pin two blocked groups/three affected links and yearless solo coverage. Real named counters retained in `local-counters.json`. |
| 6C N5/N6: post-checkpoint plans and transient listener | `spark-engineer` | `Phase6Plans` captures algorithm plans before checkpoints; actual durable JSON events feed `Phase6EventLog`. Plan text is capped at 65,536 characters and may be truncated. Real stage summary and exact synthetic event tests retained. |
| 6C N7: UDF/context explanation | `spark-engineer` | Shared explicit context schema and literal construction; README explains Java UDF calls to core IDs/validators. No encoder/RDD/GraphX API added. |
| 6C N8: schema labels/layout | `spark-engineer` | Graph tables are actual domain `GraphNode`/`GraphEdge` rows, executor-validated. Supplemental `work_sources` is a documented Spark source projection, excluded from Neptune. All applicable exported analytics records parse/validate in independent tests. |
| 6C R2-1: local docs probe portability | `spark-engineer` / coordinator | Current counter inspection and real-data distributions use the Spark-module report helper and module/independent tests. Old 6C local scripts remain historical evidence. Current command JSON/classpath snapshots are explicitly local evidence, not portable tools. |
| 6DE N1: found-pair BFS cost/checkpoints | `spark-engineer` | Stops the entire pair after finding the target; frontier/visited checkpoint at configured interval. Small selected-path metadata checkpoints each hop to cut recursive stop-gate lineage. New three-window chain crosses interval 5 with K20 and six-hop evidence. |
| 6DE N2: LPA global iteration count | `spark-engineer` | Per-window first convergence/iteration state; module fixture distinguishes isolated and oscillating windows. |
| 6DE N3: LPA cache order | `spark-engineer` | Materialize next labels before releasing previous labels; measured bounded run/replay succeed. |
| 6DE N4: context struct order | `spark-engineer` | One explicit `Phase6Context` StructType across C/DE/FG; schema assertion plus exported record parsing. |
| 6DE N5: endpoint/sample counters | `spark-engineer` | Missing benchmark endpoints counted; seeded-pair count means new sampled pairs after benchmark deduplication. Independent G1 test pins missing endpoint count. Real run has no benchmarks and zero missing endpoints. |
| 6DE N6: partial replay | `test-engineer` / coordinator | Independent actual 28-table exports/rereads at 4 versus 2 partitions match; both fresh real-data runs also match every table count/hash and counter array (`replay-comparison.json`). |
| 6DE N7: output/core contract coverage | `spark-engineer` / `test-engineer` | Every applicable published record is executor-validated and independently parsed. Source projections and rejects use their documented explicit schemas. Counter rows are core-validated in independent tests. |
| 6DE N8: README drift | `spark-engineer` | Per-job README updated for actual algorithms/layout/cache/checkpoint/counters. Unimplemented per-job counters are not claimed; entry/exit counts remain derivable from flags. |
| 6C/6DE N9: coordinator formatter execution | Coordinator | Disclosed: coordinator executed owner-requested formatter/target commands while holding shared sbt slot; named owners authored all source/test changes. No ownership reassignment is claimed. |
| R1-O1: real LPA non-convergence | `spark-engineer` / coordinator | README and `real-data-report.md` state isolated pairs oscillate. Every observed real window reported non-convergence at iteration 20; exact changed counts are retained. |
| Required sampled path-length/diameter estimate | `spark-engineer` / `test-engineer` | Implemented as S32 seeded sources in each largest component, complete BFS and empirical distance P90. Exact chain expectation 4/3 and P90 2; real estimates for all six windows are reported. No deviation acceptance is requested. |

### Issues discovered and repaired during implementation

| Issue | Owner | Observed failure and disposition |
| --- | --- | --- |
| Dataset adjacent XML records | `dataset-engineer` | Initial extraction failed after successful bounded download. Bounded tag scanner and chunk/adjacent-record regressions fixed it; 12/12 tests and actual byte-identical slice replay. |
| Spark constructor compile argument | `spark-engineer` | Initial missing `DatasetSnapshotRef` argument failed compilation; corrected compile passes. Both logs retained. |
| Test JSON nulls / macOS temp symlink / mutable Seq cast | Module and independent test owners | Initial setup failures retained; corrected explicit-null JSON, real temp path and `Row.getSeq` access preserve substantive assertions. |
| Deep plan-string memory exhaustion | `spark-engineer` / `test-engineer` | Initial independent suite exhausted its fixed 2 GiB heap in plan rendering; Hadoop then failed secondarily. Bounded plan/history retention and materialized found-path metadata fixed it without a test heap increase. Corrected independent 13/13 then final gates cover the fix. |
| ER export byte bound | Coordinator, existing ER CLI unchanged | 256 MiB output bound refused export, exit 2. Only ignored runtime bound raised to 2 GiB; retry succeeds with zero model calls. No policy or ER source change. |
| Spark 3.5.4 inferred Union constraint checkpoint error | `spark-engineer` | Initial real run failed, exit 1, stack retained in `spark-first-checkpoint-error.json`. Optimizer-only inferred constraint propagation is disabled for analytics/lazy publication; explicit application invariants remain. Multiwindow six-hop regression passes; fresh first/replay runs exit 0 with new compiled-code-derived run identity. Diagnosis is source-supported inference, not an upstream-ticket claim. |
| New literal-count assertion expected JSON number | `test-engineer` | Combined target module 33/33, independent 12/13, exit 1. Operational sidecar Long values are strings; assertion now decodes that representation. Corrected tiny pipeline passes 1/1 (`pipeline-final-targeted.txt`), with full gate to cover all assertions together. |

Remaining limitations: reuse authenticates bound manifests/metadata and identity,
but does not rehash existing Parquet files after completion; fixed 256-shard row
hashing retains each shard's sorted JSON on executors and is measured only at the
bounded slice scale; summary/source and integrity layout additions are explicit;
distance estimates cover sampled sources in largest components, not exact graph
diameter. Neptune yearless mapping remains a Phase 7 decision. Packaging JDK guard
and live Scala/EMR runtime alignment remain later release/Phases 13–15 gates. No
cloud compatibility or storage loading is claimed.


### Final 6F+6G gate and stop

All latest assertions pass in the stable-tree full gate: **551/551**, exit 0,
144/64/39/34/263/7; real **692.82 s**. Full unfiltered log **1,358,948 bytes**,
SHA-256 `6f48042efe332864661f5d8a73dfa8565fd257db53ff3bcc97371b724919844c`.
The 27 implementation/config/test/manifest files did not change during the gate;
post-gate compiled fingerprint equals both successful real-data runs. Both fresh
runs match all 28 table hashes/counts and counters. The corrected new sidecar-count
assertion also passed a separate tiny pipeline target before the full check.
`git diff --check` exits 0. No independent approval is claimed. No commit, push,
reviewer launch, AWS/live model call or 6I work occurred. Next gate: user's
independent read-only review.


## Subphase 6F+6G repair round 1 — external F1–F12

The complete user-supplied REQUEST-CHANGES review and next prompt are retained
verbatim in `review.md` and `evidence/6fg/repair-1/external-review.txt`.
Base/unchanged HEAD `6ae7378cbef90a176fd1faecae0dee0615eba9e3`, branch `phase-6`.
The user subsequently narrowed scope to **"only fix the blockings bugs"** in
response to the F11 retention question. This round therefore fixes **F1–F3 only**.
Optional README edits made before that reply were reversed by the Spark owner;
its hash again exactly matches the original stable snapshot. Existing evidence
was not trimmed or removed. No production Scala, IDs, algorithms, manifests or
retained output are changed. Full-gate results are appended after completion.

| Finding | Blocking / owner | Repair-round disposition and evidence |
| --- | --- | --- |
| F1: missing stage DAG | Blocking; coordinator | Evidence-only derivation from retained successful raw event log; `repair-1/stage-dag.json` / `.md` record names, parent IDs, partitions, task/shuffle totals. 5,667 stage IDs / 4,532 edges; 2,004 executed totals match the original summary, no missing parents/cycles. Real-data report states production summarizer gap and links artifacts. No Spark rerun/code change. |
| F2: operational analytics report differs | Blocking; coordinator (evidence route) | `replay-comparison.json` now explicitly compares reports: logical tables equal, all compared artifacts not equal. `repair-1/analytics-report-comparison.json` lists 12 numeric differences (one approximate percentile, eleven means), hashes, physical-order explanation and latent estimate-P90 caveat. Real-data report labels first-run distributions and scope; outputs/code/run identity remain unchanged. |
| F3: parenless actions evade scanner | Blocking; test-engineer | Only `IndependentPhase6SafetySpec.scala` changed. Reusable scanner catches 11 driver method names with/without parentheses, adds isEmpty/reduce, and has three synthetic self-tests for forbidden forms, boundaries, comments/strings and narrowly audited metadata receivers. Safety target 7/7, exit 0; full stable-tree gate required below. |
| F4: retry of incomplete same-ID output | Nonblocking; spark-engineer | Deferred under user blocking-only scope. No automatic cleanup or changed retry semantics; preserve failed evidence and require a separate operator decision before any destructive cleanup. |
| F5: thin summaries / unmarked long-title truncation | Nonblocking; spark-engineer | Deferred. Needs source/template and long-title feature tests; current code/output intentionally unchanged. Route before Phase 8 embedding consumers. |
| F6: tie winner not observable | Nonblocking; spark/domain owners | Deferred. Current TemporalChange exposes actual current community and overlap score, not separate matched-community ID. README repair is outside narrowed scope; future wording/contract gate remains. |
| F7: kcore duplicates collaboration dataset | Nonblocking; spark/storage owners | Deferred to Phase 7 loader validation/deduplication. Both logical datasets and proposals remain unchanged. |
| F8: loose target mapping proposals | Nonblocking; spark/storage owners | Deferred to Phase 7. Support keys need edgeId+workId, while current proposed idProperty=edgeId is not unique; DynamoDB key/run-state proposal remains unimplemented free text. No store writes were performed. |
| F9: unproven per-component LPA attribution / Spark cause comment | Nonblocking; spark owner, coordinator reporting | Deferred under narrowed scope. No per-component pair count or convergence evidence was added; the observation must not be treated as measured causal attribution. No source-comment change. |
| F10: shared-session optimizer setting / unmeasured cost | Nonblocking; spark owner | Deferred. Production still sets constraintPropagation=false on caller session; metadata lacks an explicit field and no A/B cost measurement exists. Existing compiled-code fingerprint remains unchanged. |
| F11: evidence size | Nonblocking; human decision | Asked with actual pre-repair inventory: 68 files / 4,325,261 bytes; full gate 1,358,948; two summaries 848,446. User replied blocking-only, so no retention cleanup or inferred approval of a retention policy. Required DAG/new gate evidence is added; originals preserved. |
| F12: duplicate counters / formatter attribution / Python gate | Nonblocking; owners/coordinator | Deferred. Counter aliases remain; coordinator formatter execution is disclosed; Python 12/12 remains separate from sbt counts. No build ownership change. |


### Repair round 1 final gate

F1–F3 are repaired and locally validated, **pending external recheck**. Safety7/7;
full JDK17 check **554/554**, exit0, counts144/64/39/34/266/7, real676.42s.
Log1,358,928bytes, SHA-256 `3e6654835296bab3be44efbdf0cd31c205dd4b34ff87b98848a4ba16623c5236`. All27repair snapshot files unchanged during
the gate; only SafetySpec differs from the original reviewed source snapshot.
Production fingerprint and retained run ID unchanged. Diff check0, HEADunchanged.
F4–F12 remain deferred under the user's blocking-only answer. No optional README
or retention changes remain; no real-data rerun, commit, push, reviewer or6I.

## Subphase 6I — authoritative close-out carry-forward register

The user-supplied external recheck **APPROVED 6F+6G repair round 1**. Its complete
verdict is already retained verbatim under its own heading in `review.md`.
F1 (stage DAG), F2 (honest replay/report scope), and F3 (source fence) are closed
by that reviewer. The user committed the approved tree as
`d1afc7f6698965ddbe010621b277b10e655d25ff`. Historical "pending" wording above
records the state of earlier rounds and is superseded by this dated disposition.
This is not the pending comprehensive whole-Phase-6 review or human acceptance.

No new implementation is authorized in evidence-only 6I. Prior user scope
"only fix the blockings bugs" is preserved. None of F4–F12 is silently closed:

| Finding | Status and named owner | Downstream gate / practical limit |
| --- | --- | --- |
| 6FG F4: same-ID failed-run retry | OPEN / deferred; spark-engineer; operator controls cleanup | Before operational retry/runbook use: same config/code refuses incomplete output. Inspect and preserve failure evidence; any destructive cleanup requires its own human decision. No cleanup performed here. |
| 6FG F5: thin summaries; title truncation lacks a marker | OPEN / deferred; spark-engineer | Before Phase 8 embedding consumers: improve source-grounded context and test long titles. Current 900-character title bound is unchanged. |
| 6FG F6: continuity tie winner not exposed | OPEN / deferred; spark-engineer, domain-engineer if a field is added | Before consumers infer a matched community: actual community and overlap are present, selected tie winner is not observable. Clarify documentation or route an additive contract change. |
| 6FG F7: duplicated kcore/collaboration table | OPEN / deferred; storage-engineer with spark-engineer | Phase 7 loader design must avoid unintended duplicate storage of the same rows. Current proposals preserve both tables. |
| 6FG F8: target key proposals | OPEN / deferred; storage-engineer with domain/spark support | Phase 7 before loading: support rows need a unique composite key (edgeId alone is not unique); DynamoDB free-text key proposal is not an implemented schema. No stores loaded. |
| 6FG F9: LPA causal attribution / optimizer-cause wording | OPEN / deferred; spark-engineer; coordinator for future reporting | Before stronger scientific/causal claims: observed final changes and non-convergence are known; per-component causes/counts were not measured. Pair oscillation is a fixture property, not proof explaining all real changes. Spark diagnosis is an inference. |
| 6FG F10: caller-session constraint setting | OPEN / deferred; spark-engineer | Before operational/session reuse: constraintPropagation=false is applied to the caller session, not explicitly recorded in run metadata; A/B performance cost not measured. No fix or measurement claimed. |
| 6FG F11: evidence volume | OPEN / deferred; human retention decision, coordinator executes approved scope | No trimming/deletion inferred from blocking-only reply. Existing gates/DAG retained; fresh 6I full log adds evidence. |
| 6FG F12: counter aliases, formatting process, Python gate | OPEN / deferred; spark-engineer, dataset-engineer, build-engineer as applicable; coordinator attribution | Counter aliases unchanged; prior coordinator formatting disclosed. Historical dataset Python 12/12 is separate from sbt counts; it was not rerun in 6I. Build changes require build owner. |
| 6FG recheck: scanner blind spots | OPEN / nonblocking; test-engineer | Next source-fence hardening: .tail/.toJavaRDD/.javaRDD/.toRdd and code in interpolated strings are not reliably detected. Textual scan is not a parser/type checker. No current violation was reported by the external reviewer. |
| 6FG recheck: empty handoff path | CLOSED; coordinator | Corrected before the approved 6FG commit: `evidence/6fg/repair-1/handoff.md` names its evidence directory. No new 6I edit required. |
| 6FG recheck: evidence size | OPEN / nonblocking; human | Same retention decision as F11; approval is not approval of a new cleanup policy. |
| 6A F4: wrong-JDK evidence stale | OPEN / deferred; build-engineer and coordinator | Refresh on release tree before packaging/deployment. Fresh JDK 17 check proves the supported-JDK path only; it does not refresh the wrong-JDK log. |
| 6A F6: packaging not JDK-guarded | OPEN / deferred; build-engineer | Before release packaging / Phase 13–15 deployment. No package rebuilt in 6I, and no guard fix claimed. |
| 6A F8: packaging wording | OPEN / informational; build-engineer | Future build documentation cleanup, not a release/runtime verification. |
| EMR runtime / Scala alignment | OPEN; infra-engineer (Phase 13), deploy-engineer (Phase 15), build-engineer for package | **Bounded EMR Spark run: OPEN — deferred to Phase 15 by user decision.** Compatibility research is not a live test. Script in Phase 13, bounded driver/executor class-origin and DataFrame/Parquet check under human budget/deployment gate in Phase 15. |
| Yearless coauthor edge mapping | OPEN; storage-engineer with domain-engineer | Phase 7 before Neptune loading. Frozen CoauthorshipProperties requires numeric years; no invented dates or live store compatibility claim. |
| Comprehensive APPROVE / human close-out | PENDING; user-launched independent reviewer, then human architect | Whole diff from `03493882399e9020e6892c9f97e0ec8919365215` including untracked files; then human-owned `human-gate.md` and `commit.txt`. Subphase approvals do not close these gates. |

Current provenance is recorded in `evidence/6i/preflight.md` and `.json` (plan hash,
Codex tool, observable model identity, unavailable exact model build). It does not
retroactively invent the missing 6A model or command evidence. Reuse remains
metadata-only; 256-shard hashing is measured at the bounded slice scale; reports
and sampled P90 can vary with physical aggregation; cross-JAR/EMR determinism is
unverified. Prior resolved 6B/6C/6DE items retain the later 6FG evidence above.

### 6I final validation and additional evidence observation

Fresh JDK 17 `sbt -batch check`: **554/554**, exit 0, real 675.13s;
log 1,359,860bytes, SHA-256 `e2bf289d11f6f2e4ff8e714d3fc4b9b56b16ea7ed59007abd00d5fe73d9d7367`.
All 68 implementation artifacts (hashes/mtimes) and 27 approved snapshot hashes
unchanged. No source repair required. Current tracked whitespace check exits 0;
whole-phase non-evidence check exits 0. The broader cumulative check exits 2 for
trailing whitespace in preserved historical raw logs only. This is an evidence
format observation, not a new production failure; originals remain unchanged.
`evidence/6i/diff-check.txt` retains the diagnostic. No user retention/cleanup
choice is inferred. Comprehensive whole-phase review and human records remain
pending; F4–F12 and the routed later gates above stay open/deferred.

## Subphase 6I — comprehensive review disposition (2026-10-22)

**Comprehensive APPROVE: RECEIVED** from the independent, user-launched reviewer
for 6I and the whole Phase 6 **local implementation**, with no blocking findings.
Full verdict, observations, report fields and next prompt are retained verbatim
in `review.md`. This supersedes earlier pending-review status, not prior human
decisions. **Human close-out: PENDING**; bounded EMR remains OPEN.

No implementation changes or new test/runtime execution in this disposition round.
The existing 554/0 gate remains the observed implementation gate. 6FG F4–F12,
scanner blind spots, 6A F4/F6/F8, EMR/Scala alignment and yearless Neptune mapping
remain **OPEN and unchanged** in the preceding carry-forward register.

| Whole-phase finding | Status / named owner | Next gate / acceptance |
| --- | --- | --- |
| N1: LPA oscillation beyond isolated pairs | OPEN, nonblocking; spark-engineer (rule/measurement), coordinator (wording) | Before Phase 7–9 consumers: either validate a converging rule on pairs/bipartite/real windows, or add per-component non-convergence counts and require consumers to display `Converged: false` rather than present iteration-limited partitions/derived bridges as converged results. Odd real changed counts show pairs cannot explain all non-convergence. No rule change or consumer implementation claimed here. |
| N2: distance P90 uses percentile_approx | OPEN, nonblocking; spark-engineer | Before strengthening partition-invariant logical-table claims: exact P90 with differing-partition tests, or an explicit approximate label. A production change requires a new fingerprint, full gate and fresh real run/replay. Existing replay equality is observational only. |
| N3: zero real Researcher ER decisions insufficiently explicit | OPEN, nonblocking; coordinator | Clarify real-data-report.md and traceability J1 with all-zero Researcher decisions; Work accepted 1/conflict 12,123/unresolved 1,627 and the five zero branch counters. A short 6I owner-report clarification is added below the existing packet; full requested report/J1 changes remain open. Identity merging/constraints are fixture/tiny-pipeline evidence, not exercised by this real slice. |
| N4: Job 1/9/10 README drifts from execution | OPEN, nonblocking; spark-engineer | Next Spark documentation pass before consumers rely on the per-job physical account: reflect actual repartitions, joins and approximately 20 cached tables; remove prospective `will own` wording. No Spark-owned README edit in this coordinator-only round. |
| N5: driver caps are call-site literals | OPEN, nonblocking; spark-engineer | Next bounded-action configuration pass: name caps as constants or config; current 10,000/256 bounds are explicit literals rather than the plan's config limits. No current-scale overflow claimed. Feature tests/regate if behavior changes. |
| N6: Phase6Plans global destination is not thread-safe | OPEN, nonblocking; spark-engineer | Before parallel suites or concurrent pipeline use: pass the destination explicitly and test isolation. No change to current sequential execution. |
| N7: commit-title attribution / evidence retention | OPEN, informational; human | Human close-out retention decision: about 15.9 MB evidence, three approximately 1.36 MB gate logs; 188 whitespace hits in 17 raw logs. Role-labelled commit titles aggregate several owners but path ownership was verified intact. No trimming, title rewriting or inferred retention approval. |

Human must decide acceptance of the local implementation, the course work-order
EMR deferral (script Phase 13/run Phase 15), the unselected Scala-compatible
runtime's schedule/cost risk, the Codex/Cursor workflow deviation without claimed
instructor approval, retention, and this open register. The coordinator must not
write `human-gate.md`, `commit.txt` or `accepted-commit.md`, commit/push or start
Phase 7. Comprehensive APPROVE is received; human close-out is the next gate.

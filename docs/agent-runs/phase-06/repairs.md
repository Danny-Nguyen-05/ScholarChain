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

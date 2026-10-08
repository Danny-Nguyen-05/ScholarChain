# Phase 4 repairs

## Review round 1

STATUS: REQUEST-CHANGES from code-reviewer `01851f5f-3af4-47c8-ac27-44e7f786298e`. Six findings block Phase 4. Optional notes in `review.md` are not part of this repair pass.

Routed:

1. `hadoop-engineer` — UTF-8 DBLP record bytes, drop duplicates and conflicts from team/pair/export inputs, do not resolve `s3://` output roots as local paths, separate block-pair stats from coauthor pair expansion.
2. `domain-engineer` — allow `RunManifest.configSchemaVersion` to name `scholarchain.hadoop-prep.v1` without accepting that document as `ScholarChainConfig`.
3. `infra-engineer` — pass `--output-root` through the EMR step once the main accepts it, and refuse a dry-run whose local config `outputRoot` disagrees with `--output-prefix`.

`test-engineer` updates independent assertions after those production repairs. The orchestrator reruns `sbt check` and then starts a fresh read-only review.

## Repair implementation

The six blocking repairs were implemented. `RunManifest.configSchemaVersion` for this pipeline is `scholarchain.hadoop-prep.v1`. The fallback to `scholarchain.config.v1` was removed. EMR dry-run arguments include `--output-root`.

Orchestrator gate after those edits, 2026-10-06 15:13:33 local: `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home sbt -batch check` exit 0 in 84 seconds on Java 17.0.20.1 and sbt 1.10.7. Counts: 93 passed, Hadoop module 12 passed, independent 17 passed, build-verification 2 passed. A fresh read-only recheck follows. This note does not accept the phase.

## Recheck

The recheck cleared findings 1, 3, 4, 5, and 6. Finding 2 stays open. `hadoop-engineer` must not treat a work and its institution from one observation as a conflict, and must not export a topic that appears on only one of two same-key observations. `test-engineer` adds coverage after that repair.

`hadoop-engineer` reported the join rule repaired. `hadoop/test` exit 0, 15 tests passed, 108 seconds. `test-engineer` is adding the independent institution and one-sided-topic assertions. Full `sbt check` waits for that.

## Independent comprehensive review repairs

STATUS: repairs implemented after the 2026-10-06 REQUEST-CHANGES with 19 blocking findings. Human acceptance is not recorded.

Routed and written:

- `domain-engineer` added `prep-features-v2`, `MentionAffiliation`, and required `executionMode` `local` or `cluster`.
- `dataset-engineer` added `datasets/acquisition-index.v1.json`. Sample bytes were not changed.
- `build-engineer` added `hadoopDependencyBundle`. The first bundle omitted `core` classes. The 2026-10-07 09:58:50 run failed with `Bundle missing expected core module entries`. The follow-up merged `core`'s packaged jar. `sbt -batch hadoopDependencyBundle` then exited 0 and logged `Verified non-Hadoop dependency bundle`. A later jar listing counted core 468, Hadoop module classes 0, `org/apache/hadoop` 0, upickle/ujson 453, scala 3549.
- `hadoop-engineer` repaired the Hadoop findings, then kept remote inputs as Hadoop paths, then made launch-cap reject order follow the file byte offset.
- `test-engineer` gave independent runs fresh directories and run ids, updated `Element` and `executionMode`, and stopped requiring an oversize DOI block to erase a separate in-limit `initial:` candidate.
- `infra-engineer` required `-libjars`, `--execution-mode cluster`, and the acquisition snapshot ids. Dry-run only. No EMR step was submitted.

Failed gates in this pass, each repaired before the final check: `build.sbt` scalafmt; `IndependentDblpJsonSpec` tuple unpack; `HadoopPrepReviewSpec` launch-cap part order; `IndependentHadoopPipelineSpec` empty-candidate assertion; the first dependency bundle missing `core`.

The final `sbt -batch check` after the bundle fix exited 0 at 2026-10-07 10:05:28 local, 285 seconds. Counts: core 96, Hadoop 28, independent 20, build-verification 2. The injected format-stage failure is the expected probe and its parent test passed. This note does not accept the phase.


## Four remaining XML repairs — 2026-10-07

STATUS: COMPLETE — final independent recheck APPROVE; human acceptance pending.

OWNER: `hadoop-engineer` for production/module tests, `test-engineer` for independent tests, coordinator for execution/evidence. Review by fresh read-only `/root/xml_repair_reviewer`.

WORK ORDER: Repair all four latest findings in `review.md:347` together.

| Finding | Repair | Observed feature coverage |
| --- | --- | --- |
| Unbounded opening-name buffering | 256-byte retention cap, full count, bounded oversize envelope, draining | nextOpen, InputFormat, launch scan, job reject, following work |
| CDATA reference interpretation | Literal CDATA plus active-reference segments, shared output bound | Title/author ampersands and reference-shaped literals, combined limit |
| Lost single-quoted/closing-whitespace evidence | Both quote forms and matching closing boundaries | Key/ORCID retention, valid whitespace, invalid identifier reject |
| Accepted malformed closes | Malformed flag through framer/envelope/mapper/direct parser; root recovery | Eight independent malformed variants and actual LocalJobRunner rejects |

FILES CREATED / MODIFIED: Listed in current `owner-report.md` and `test-report.md` sections. No sample, packaging, EMR script, constitution, or human decision changes in this repair pass.

COMMANDS RUN / TEST RESULTS: Exact replay commands and failed attempts in current `test-report.md`; 21 new targeted tests pass, full gate 185 tests pass. Packaging verification and two fresh equivalent sample runs exit 0. Script syntax/dry-run and sample checksums pass.

VALIDATION RESULTS: Final independent review appended to `review.md`. Compact manifests, nine job completions per run, counters, stats, and actual representative records retained in `xml-repair-sample-evidence.json`; raw gate output in `xml-repair-full-gate.txt`.

ASSUMPTIONS: Local execution authorized; EMR authoring-only.

RISKS: AWS remains unrun; scoped review does not prove exhaustive correctness.

MANUAL ACTION REQUIRED: Human Phase 4 decision after review of the complete diff.

BLOCKED-ON OWNER: None for the four routed implementation findings.

BLOCKED-ON EVIDENCE: None in the independent review scope.

NEXT GATE: Human Phase 4 acceptance. No commit/push or Phase 5 work.


## Fresh comprehensive review routing — 2026-10-07

STATUS: BLOCKED-ON — REQUEST-CHANGES; seven blockers from fresh reviewer `/root/phase4_comprehensive_reviewer`. This turn reviewed and recorded findings; no implementation repair was performed.

OWNER: Coordinator; required writers listed below.

WORK ORDER: User requested a fresh comprehensive code review. Full findings, source lines, reproducers, and evidence appear in the latest section of `review.md`.

| Finding | Required owner | Supporting owner |
| --- | --- | --- |
| Intermediate normalized-record overflow silently drops works | hadoop-engineer | domain-engineer if new config contract; test-engineer |
| XML splits lose comment/CDATA context | hadoop-engineer | test-engineer |
| Source identifiers/work-reference relationships discarded | domain-engineer and hadoop-engineer, disjoint contract/implementation paths | test-engineer |
| Self-closing author drops position | hadoop-engineer | test-engineer |
| Damaged output trusted on reuse | hadoop-engineer | test-engineer |
| Driver filesystem configuration drops caller settings | hadoop-engineer | test-engineer |
| Smoke execution ceiling unenforced | infra-engineer | domain/hadoop-engineer for validation contract; test-engineer |

FILES CREATED: None by reviewer.

FILES MODIFIED: Coordinator evidence reports only.

COMMANDS RUN / VALIDATION RESULTS: Read-only review and retained-artifact analysis; no source/test execution. 90 reviewed source/contract fingerprints unchanged. Existing 185 passing tests and two equivalent runs remain observed evidence of their covered sample behavior.

TEST RESULTS: No new tests executed. New triggers remain uncovered.

ASSUMPTIONS: Local execution authorized; EMR authoring only.

RISKS: Static reproducers not executed; AWS remains unrun.

MANUAL ACTION REQUIRED: Owner repairs together, feature/independent tests, full gate and fresh replay, then fresh independent review. Human acceptance still pending.

BLOCKED-ON OWNER: hadoop-engineer, domain-engineer, infra-engineer; supporting test-engineer.

BLOCKED-ON EVIDENCE: Seven confirmed blockers in latest `review.md` section.

NEXT GATE: Owner repairs and observed gates, then independent review. Do not begin Phase 5.


## Seven-blocker repair recheck routing — 2026-10-07

STATUS: BLOCKED-ON — fresh REQUEST-CHANGES, two remaining evidence-preservation categories.

OWNER: Coordinator; hadoop-engineer for implementation, test-engineer for independent regressions, domain-engineer if additive contracts needed.

WORK ORDER: User requested another independent check. No source repairs performed in this review turn.

1. Intermediate overflow now emits explicit rejects, but source/snapshot and a unique file/record locator are lost. Preserve bounded lineage and test valid source expansion through final rejects.
2. Preserve both OpenAlex top-level DOI and ids.doi disagreement/validation evidence, and all DBLP nonidentifier electronic-edition links. Add independent retention/conflicting-observation tests.

FILES CREATED / MODIFIED: Coordinator review/test evidence only.

COMMANDS RUN / TEST RESULTS: Current 202 passing tests and two fresh equal runs inspected; packaging rebuilt and verified; script syntax/dry-run passed. Exact evidence/provenance in latest review/test sections.

VALIDATION RESULTS: Six prior blocker cases closed; intermediate overflow partial closure. Institution/ORCID cited evidence now retained; broader bibliographic gaps remain. 91 source/contract files unchanged during review.

ASSUMPTIONS: Local execution authorized; no Phase 5 scope.

RISKS: Static new reproducers unexecuted; AWS unrun. XML prefix replay performance and thin-JAR documentation are nonblocking notes.

MANUAL ACTION REQUIRED: Owner repairs together, feature/independent coverage, relevant gates, then fresh review.

BLOCKED-ON OWNER: hadoop-engineer; supporting domain-engineer/test-engineer.

BLOCKED-ON EVIDENCE: Latest review findings 1–2.

NEXT GATE: Repairs and observed verification, independent review, human acceptance.


## Two evidence-preservation blocker repairs — 2026-10-07

STATUS: IN PROGRESS. User explicitly requested subagents to fix the latest findings at review.md:657.

OWNER: Coordinator routes named artifact roles. Existing worker `/root/hadoop_engineer` received separate domain-engineer work order for the minimal shared contract under modules/core/**, followed by hadoop-engineer implementation under modules/hadoop/**; one writer per class. `/root/test_engineer` owns independent tests/**. `/root/phase4_seven_blocker_reviewer` remains read-only and independent. Native inherited models; historical Cursor assignments unavailable.

WORK ORDER: Preserve bounded intermediate overflow source/snapshot and qualified unique locator through final reject export. Preserve and validate both OpenAlex DOI fields and all ordered DBLP ee/url evidence without changing preferred identity policy. Add feature and independent end-to-end tests, run sbt check, rebuild packaging, run two fresh samples and obtain independent recheck.

ROUTING LIMITATION: Creating a separate domain worker returned `agent thread limit reached`; no source changes resulted from failed launches. No prior domain worker exists in this native tree. The existing implementation worker received the separate domain role for narrowly scoped shared contracts; test and review workers stay separate. A new reviewer thread may likewise be unavailable; retain read-only independence and disclose reviewer context reuse if required.

FILES CREATED / MODIFIED: Pending implementation reports. Existing dirty tree preserved.
COMMANDS RUN: Read-only source/review inspection; agent routing. No test executions yet in this repair pass.
TEST RESULTS: Pending. Earlier 202-pass gate is historical until rerun.
VALIDATION RESULTS: Pending.
ASSUMPTIONS: Local tests/build/sample execution authorized; no AWS actions.
RISKS: Gate/review pending; XML prefix replay performance limitation remains.
MANUAL ACTION REQUIRED: Human Phase 4 acceptance after complete review.
BLOCKED-ON OWNER: Implementation/test owners in progress.
BLOCKED-ON EVIDENCE: Fresh passing gate and independent recheck.
NEXT GATE: Source-ready reports, deterministic gates, independent review. No commits, pushes, cloud actions or Phase 5.


### Read-only reviewer found framing regression during verification

STATUS: REQUEST-CHANGES during repair verification.
OWNER: Hadoop engineer.
EVIDENCE: PrepSupport TaskSink.emit frames every callback key; PrepJobs ExportReducer unresolved abstract-reference callback writes that key directly to final partition. A work with missing abstract text can therefore generate a control-suffixed reject partition.
REPAIR ORDER: Strip private intermediate framing at the final-export callback and add actual J09 missing-reference partition regression. Coordinator canceled the initial full gate; retained partial log as evidence-repair-interrupted-gate.txt. Full gate/package/samples must rerun after repair. Reviewer remains read-only.


### Read-only reviewer found overflow comparison regression

STATUS: REQUEST-CHANGES during verification.
OWNER: Hadoop engineer; independent test engineer.
EVIDENCE: Generated overflow reject locator binds a qualified intermediate file in a run-specific directory. LogicalRecords normalizes exact run IDs but leaves UUIDs in these locators and long-path hashes. Two equivalent overflow runs can compare unequal.
REPAIR ORDER: Keep exported locators intact; compare a bounded stable identity for recognized generated files that excludes only processing-run metadata and retains genuine source root, part, source key and snapshot. Cover long qualified paths and long native keys. Add real two-fresh-run valid600k-title overflow equivalence, including independent coverage. Second full-gate attempt canceled and retained; final gate must rerun after source freeze.


### Observed high cached-core packaging blocker

STATUS: REQUEST-CHANGES.
OWNER: Build-engineer (separate narrow work order to existing implementation worker, sole writer build.sbt/project/**).
EVIDENCE: Current core JAR WorkRecord.class has additive fields; cached dependency/embedded submit bundle retains older constructor. Exact hashes/byte sizes in owner report.
REPAIR ORDER: Replace old core entries during every overlay, remove deleted owned entries, verify current core entry content, test two successive core versions against cached bundle, rebuild and rerun complete gate. Module/domain source remains frozen. Reviewer read-only.


## Final closure — 2026-10-07

STATUS: COMPLETE — two latest source-evidence categories and subsequent export/comparison/cached-core defects repaired. Independent final review APPROVE; human acceptance pending.
OWNER: Domain/Hadoop/build disjoint work orders performed by existing implementation worker; independent test-engineer; read-only code-reviewer; coordinator evidence. New native threads unavailable, so roles reused with unique writers and independent review preserved.
WORK ORDER: User requested subagents fix remaining blockers; user `continue` resumed final verification.
FILES CREATED / MODIFIED: Exact source/build/test files in owner report; final coordinator logs/artifacts/review/test/repair reports. Samples, human decisions and constitutional files unchanged by this repair pass.
COMMANDS RUN / TEST RESULTS: Exact commands in test-report.md. Final220tests pass (99core,64Hadoop,53independent,4build), packaging exactcoreverification and two fresh sampleequivalence pass. Two interrupted and one stale-packaging historical gate retained separately.
VALIDATION RESULTS: Finalreview.md APPROVE; all478currentcore bytes match bundle and exactlyoneembeddedbundle. source/config92fingerprints unchanged. Synthetic overflowtwo-run and sourceevidenceperturbation regressions pass.
ASSUMPTIONS: Localexecutiononly; no constitutional ratification inferred.
RISKS: XMLprefix replay performance, AWS/largecorpus execution unverified; reviewer reusedcontext disclosed.
MANUAL ACTION REQUIRED: Human Phase4 complete-diff review and acceptance.
BLOCKED-ON OWNER / EVIDENCE: None for reviewed implementation.
NEXT GATE: Human Phase4 decision. No commit/push/deployment/Phase5.

## Human acceptance recorded — 2026-10-07

STATUS: COMPLETE — the human accepted Phase 4 with the statement `human accept`. The exact decision is transcribed in [human-gate.md](human-gate.md); the existing implementation SHA is recorded in [accepted-commit.md](accepted-commit.md). All 92 reviewed source/config hashes still match the final 220-test gate. No new commit, push, AWS execution or Phase 5 work was performed while recording acceptance.

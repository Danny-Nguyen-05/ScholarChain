# Phase 4 owner report

Current status: source-evidence and cached-core packaging repairs complete; final frozen gate passes 220 tests, exact core content verification and two fresh equivalent sample runs. Independent final reviewer APPROVE; human Phase4 acceptance pending. Latest review section is authoritative for current status; older findings/results remain historical.

STATUS: COMPLETE — implementation, local gates and independent review complete; human Phase4 acceptance pending.

OWNER: Phase 4 orchestrator, assembling reports from the named owners. Human acceptance is not recorded.

WORK ORDER: `docs/agent-runs/phase-04/prompt.md`

## Roles and models

- `domain-engineer`: Grok 4.7 High (`d0412dab-c8e4-432f-8d6d-df5e3be93966`)
- `build-engineer`: Composer 2.5 Fast (`1d63d291-69f7-4119-8179-8421be1f50cd`, launch repair `947d5b4f-2334-4493-8bea-a19d9cd30c12`)
- `hadoop-engineer`: Grok 4.7 High (`d05674d9-0f25-48b4-a2ba-874bea523a56`). An earlier run (`9ea194e2-c160-48ba-a6b5-41134ce79553`) stalled while reading and wrote no Scala. It was abandoned.
- `test-engineer`: Composer 2.5 Fast (`062db29c-d00f-4b68-af40-1d0fffc978db`)
- `infra-engineer`: Composer 2.5 Fast (`4dad23e9-e777-4e18-bda6-5cc2e9906203`)
- `code-reviewer`: Grok 4.7 High, fresh contexts `01851f5f-3af4-47c8-ac27-44e7f786298e` (REQUEST-CHANGES), `06ae43f6-cc37-49fe-9c3c-be851eea9d4f` (REQUEST-CHANGES, one join blocker), `df4a1ef1-cb0d-4748-aab9-5fc12487ee02` (APPROVE)

`dataset-engineer` was not used.

## Files and owners

`domain-engineer` (`modules/core/**`): `HadoopPrepConfig.scala`, `HadoopPrepConfigLoader.scala`, `scholarchain.hadoop-prep.v1.json`, `Phase4ContractSpec.scala`, and edits to `Records.scala`, `Enums.scala`, `DomainValidation.scala`, `StableIds.scala`, `SchemaVersions.scala`, `README.md`.

`build-engineer`: `build.sbt`, `project/ScholarChainBuild.scala`, `project/HadoopPackaging.md`.

`hadoop-engineer` (`modules/hadoop/**`): `DblpInput.scala`, `DblpExtract.scala`, `JsonSources.scala`, `DerivedRecords.scala`, `PrepJobs.scala`, `PrepSupport.scala`, `HadoopPrepPipeline.scala`, `HadoopPrepMain.scala`, `HadoopPrepSpec.scala`, `README.md`.

`test-engineer` (`tests/**`): `IndependentTestSupport.scala`, `IndependentDblpJsonSpec.scala`, `IndependentHadoopPipelineSpec.scala`.

`infra-engineer` (`scripts/**`): `phase4-emr-smoke.sh`, `README.md`.

Orchestrator: `docs/agent-runs/phase-04/`.

## Job graph

J01 DblpExtract and J02 SourceNormalize feed J03 ExactIdentifierIndex. J04 ExactIdentifierJoin reads J01, J02, and J03 and is the input to J05 BlockingKey, J06 CandidateJoin, J07 PublicationTeam, J08 CoauthorPairExpansion, and J09 GraphCandidateExport. Each stage is a LocalJobRunner MapReduce job. Pass-through reducers are used where no aggregation is required. J05 and J04 reducers group by identifier. J08 does not use a combiner. The sample config sets `reducerCount` 1 and `compressionCodec` `none`.

## Replay

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
sbt -batch check
sbt -batch "hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"
```

The main class is `edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain`. `--once` runs a single pass. `--output-root` overrides the config output root. The thin JAR is `modules/hadoop/target/scala-3.3.4/hadoop_3-0.1.0-SNAPSHOT.jar` and does not contain Hadoop classes. `hadoop-client` 3.3.6 stays `Provided`.

## Final sample runs

Observed 2026-10-06 after the join repair. `sbt -batch "hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"` exit 0.

- `target/phase4-runs/9059f9e5-fe1c-4b68-8223-6ed5d4bde7cd`
- `target/phase4-runs/25aed095-7157-42f4-90be-1c7549c9b2bd`

Both `reused=false`. `logicalRecordsEqual=true`. Counters on each run: INPUT 123, ACCEPTED 135, REJECTED 1, DUPLICATE 1, CONFLICT 0, OVERSIZE_BLOCK 0, OVERSIZE_TEAM 0, EMITTED_PAIR 11, MISSING_KEY 0, SCHEMA_FAILURE 0. Largest team 2. Largest coauthor pair expansion 1. Largest block 4. J05 recorded `largestBlockPairs=6` separately. The completion marker `_SCHOLARCHAIN_COMPLETE` is present. `run-manifest.json` uses `configSchemaVersion` `scholarchain.hadoop-prep.v1`.

Export counts from the first run: 5 works, 5 teams, 10 authorships, 5 pairs, 6 match candidates, 1 institution, 5 venues, 3 topics, 1 ORCID profile, 16 ORCID activities, 1 reject (`DUPLICATE_IDENTICAL_OBSERVATION` for OpenAlex `W4254447616`, excerpt `01x8rc503`).

An OpenAlex work for DOI `10.1007/978-3-642-31674-6_1` is `work:doi:10.1007/978-3-642-31674-6_1`, title `Machine Mentality?`, year 2012, source record `W4254447616`. Its team has two mentions. The pair keeps ordinals 1 and 2 with those mention ids. The institution is `institution:ror:01x8rc503` with Ringgold null.

## Failed attempts

The first Hadoop agent wrote nothing. `hadoopRunMain` originally returned success while the main threw `NoClassDefFoundError: org/apache/hadoop/conf/Configuration` because sbt 1.10.7 background `runMain` ignored the Runtime fork settings. The build owner replaced that with foreground `Compile / fgRunMain`. Two independent tests failed on wrong assertions and were corrected by `test-engineer`. `sbt check` also failed once on scalafmt and once on `OrcidActivityRecord.doi` before `observedDoi`.

## Remaining

No blocking code findings after the final review. Optional: `observationConflict` would miss a case where one observation repeats an identical side payload a multiple of the copy count and the other omits it. `PrepJobs.configuration` still sets the framework name to `local`, so an EMR step would run LocalJobRunner until that is changed. AWS execution of `scripts/phase4-emr-smoke.sh` is unverified. `shellcheck` is not installed.

MANUAL ACTION REQUIRED: Human acceptance. No commit or push was made.

BLOCKED-ON OWNER: none

NEXT GATE: Human review. Do not begin Phase 5.


## Four XML repair gate — 2026-10-07

STATUS: COMPLETE — routed implementation and local gates complete. Independent reviewer APPROVE; human Phase 4 acceptance remains pending.

OWNER: Coordinator assembling `hadoop-engineer`, `test-engineer`, and independent `code-reviewer` reports. Production/module tests: `/root/hadoop_engineer`; independent tests: `/root/test_engineer`; read-only review: `/root/xml_repair_reviewer`; evidence: `/root`.

WORK ORDER: Four remaining XML blockers from `review.md:347`, routed together under the Phase 4 ownership map. This Codex session used native inherited agents; historical Cursor model assignments were not available. No constitutional ratification is inferred.

FILES CREATED: Module `DblpXmlRegressionSpec.scala`; independent `IndependentDblpXmlRepairSpec.scala`; retained `xml-repair-*.txt`, `xml-repair-logback.xml`, and `xml-repair-sample-evidence.json` in this evidence directory.

FILES MODIFIED: Hadoop `DblpInput.scala`, `DblpExtract.scala`, `HadoopIO.scala`, `PrepJobs.scala`; coordinator evidence reports. Earlier working-tree changes were preserved.

- Opening names retain at most 256 bytes, count all consumed bytes, drain oversized input, and produce bounded reject diagnostics. Record reading and launch scanning receive the full count.
- XML field extraction retains CDATA boundaries until expansion, copies literal CDATA, and expands references only in active segments under a combined output bound.
- Both attribute quotation forms and valid closing-tag whitespace preserve source keys and supplied author ORCID evidence.
- Closing-name mismatches and illegal closing-tag content carry an explicit malformed flag into reader envelopes, mapper rejection, and direct parsing. Root-close recovery preserves subsequent publications.

COMMANDS RUN / TEST RESULTS: Exact commands, failed attempts, and fresh results appear in `test-report.md` below its matching current section. Final targeted tests: 4 module + 17 independent passed. Full `sbt check`: 185 tests passed, zero failures; packaging and two-run replay succeeded, combined process exit 0.

VALIDATION RESULTS: Fresh sample runs `c262d529-8693-4d5a-afe8-e5caf8e3d709` and `029ab928-55d5-4f9a-894f-33b3f42a9587` both `reused=false`, `logicalRecordsEqual=true`. Nine successful job outputs per run. Both counters: INPUT 193, ACCEPTED 239, REJECTED 0, DUPLICATE 0, CONFLICT 0, EMITTED_PAIR 45. Both export 5 works, 10 author mentions, 5 teams, 10 authorships, 5 pairs, and 40 match candidates. Manifests, export counts, actual DBLP representative records, and task-statistics contents are retained in `xml-repair-sample-evidence.json`. Full stdout is retained in `xml-repair-full-gate.txt`.

ASSUMPTIONS: LocalJobRunner and bounded samples authorized. Final identity decisions remain outside Phase 4.

RISKS: Tests and review cover routed cases and affected paths, not exhaustive XML correctness. AWS/EMR execution remains unrun; shellcheck was not run.

MANUAL ACTION REQUIRED: Human architect reviews the complete diff and records the Phase 4 decision. No commit, push, deployment, or Phase 5 work performed.

BLOCKED-ON OWNER: None for these implementation repairs.

BLOCKED-ON EVIDENCE: None in the independent review scope.

NEXT GATE: Human Phase 4 acceptance after independent APPROVE; human decision files remain untouched.


## Two evidence-preservation blocker repairs — 2026-10-07

STATUS: IN PROGRESS — source ready; all 12 new targeted tests passed; full verification/review pending.
OWNER: Coordinator assembling separate domain-engineer and hadoop-engineer work orders executed by `/root/hadoop_engineer`, independent test-engineer `/root/test_engineer`, and read-only reviewer `/root/phase4_seven_blocker_reviewer`. Native inherited models; historical Cursor assignments unavailable.
WORK ORDER: User requested subagents fix latest two categories in review.md:657. Agent-thread limit prevented a separate domain worker; one existing implementation worker received disjoint contract and Hadoop roles. Reviewer remains independent; fresh inspection uses reused reviewer context due to thread limit.
FILES CREATED: Core WorkSourceEvidenceSpec.scala; Hadoop SourceEvidenceRegressionSpec.scala; independent IndependentPhase4EvidenceSpec.scala; evidence-repair-*.txt logs.
FILES MODIFIED: Core Records.scala and DomainValidation.scala. Hadoop README.md, DblpInput.scala, HadoopPrepMain.scala, DblpExtract.scala, JsonSources.scala, PrepSupport.scala, HadoopIO.scala, PrepJobs.scala, HadoopPrepPipeline.scala. Coordinator evidence reports. Existing changes preserved.
VALIDATION RESULTS: Bounded private intermediate keys preserve source/snapshot before large JSON; overflow sentinels keep qualified part-file offsets plus bounded native record reference. All persisted output paths audited by owner. Overlong snapshots fail before launch (1024 UTF-8 byte budget). OpenAlex retains both raw DOI observations with field roles and validates both; DBLP retains repeated ee/url links, grouped by role with within-role order. Preferred identity policy remains separate. Transformation version is hadoop-prep-j01-j09-v2-source-evidence.
COMMANDS RUN / TEST RESULTS: See current section of test-report.md. Core targeted 2 pass; Hadoop targeted 5 pass; independent end-to-end targeted 5 pass; full gate running. Owner observed git diff --check exit 0.
ASSUMPTIONS: Local execution authorized; no constitutional ratification inferred.
RISKS: Legacy unprefixed injected rows cannot supply unavailable lineage; XML prefix replay cost remains. AWS execution unverified.
MANUAL ACTION REQUIRED: Human Phase 4 acceptance after final gate and independent review.
BLOCKED-ON OWNER: None for source implementation.
BLOCKED-ON EVIDENCE: Full gate, packaging, two fresh samples, independent verdict.
NEXT GATE: Complete local verification and read-only review. No commits/push/cloud/Phase 5.


### Additional comparison repairs within evidence-preservation scope

OWNER: Hadoop engineer, independent test engineer; reviewer remains read-only.
FILES MODIFIED: Hadoop PrepSupport.scala, HadoopIO.scala, SourceEvidenceRegressionSpec.scala, README.md; independent IndependentPhase4EvidenceSpec.scala. Earlier callback fix in PrepJobs.scala retained.
VALIDATION RESULTS: Stable processing-file SHA canonicalizes only terminal own-run UUID/intermediate/j01–j08/part path before hashing, preserving genuine root, part identity, byte offset and full bounded native record reference. Real exported locator retains actual file display/hash; only logical comparison excludes generated run component. Metadata beyond source bounds is explicit. Unknown-lineage locators remain exact. Key-aware comparison preserves source values exactly equal to runId. Transformation version is now hadoop-prep-j01-j09-v3-stable-overflow-lineage. Module suite has 9 feature tests; independent suite has 5 end-to-end tests including two fresh overflow runs and negative source evidence comparisons.
TEST RESULTS: Targeted module 9 pass and independent 5 pass; core 2 pass. Full frozen gate/package/samples running. Two previous full attempts were deliberately interrupted when independent review found adjacent framing/comparison defects; raw partial logs retained, never claimed as passes.
RISKS: Fresh independent inspection uses the existing read-only reviewer context because new native threads are unavailable. AWS unverified; XML prefix replay cost remains.
NEXT GATE: Full current deterministic result, packaging, samples, final reviewer verdict, human Phase 4 acceptance.


### Final artifact recheck found stale core packaging

STATUS: REQUEST-CHANGES — high packaging blocker observed after local gate.
OWNER: Separate build-engineer work order routed to existing `/root/hadoop_engineer` worker because native new-thread capacity is exhausted. Sole writer build.sbt/project/**; module/domain sources remain frozen. Independent test/review roles remain separate.
EVIDENCE: Current compiled and packaged core WorkRecord.class SHA256 2d4499e38b59488b4bb47aa6b12a682376d0fdad6887624e0e15c0ede4c1125e, 14386 bytes, contains observedIdentifiers/sourceLinks. Dependency bundle and embedded submit bundle contain stale class SHA256 366dace088ff997fb0b62cd3d88da0dbf10d3b6e7d50cca7c595720c58eca485, 12642 bytes, missing those fields. Previous packaging task checks passed namespace presence and embedded-external equality; those checks did not prove equality with current core.
CAUSE: ScholarChainBuild.mergeCoreJarIntoBundle copied cached bundle entries first and skipped duplicate current-core names. The cached assembly output already contained previously overlaid core classes, so subsequent packages kept the old class constructor.
REPAIR ORDER: Prefer every current core entry, remove deleted stale core namespace/owned entries, and verify exact current-core entry bytes/content. Add a cached successive-core overlay regression and stale verification failure coverage. Rebuild and independently compare core classes/embedded bundle; rerun full current build gate. Regeneration alone cannot close this repeatable defect.
TEST RESULTS: Local218 tests and fresh sample equivalence remain observed passing results for that earlier build. Final phase/package acceptance pending repair.
NEXT GATE: Build source-ready, targeted regression, frozen full gate/package/samples, independent artifact recheck. No commit/cloud/Phase5.


### Cached-core packaging repair implementation

STATUS: SOURCE-READY; targeted tests and repeated packaging pass; full220-test gate running.
OWNER: Separate build-engineer work order performed by existing implementation worker. Native thread limit prevented a separate worker; unique writer for build.sbt/project/**. Module/domain source remains frozen; reviewer/test roles stay independent.
FILES CREATED: project/HadoopBundleMerge.scala; project/verification/src/test/scala/scholarchain/build/HadoopBundleMergeSpec.scala.
FILES MODIFIED: build.sbt and project/ScholarChainBuild.scala.
VALIDATION RESULTS: Shared Scala2.12/Scala3 helper overlays current core first, removes cached core namespace and prior owned entries, tracks owned resources, verifies all current entry size/SHA and exact namespace/inventory before atomic replacement with fallback. Feature tests verify cachedv1→v2 updates/deletedclass+resource removal/preserveddependencies/repeatability and stale-content/extra-core rejection.
COMMANDS RUN / TEST RESULTS: Owner git diff --check exit0, no sbt. Root targeted build regressions2pass and repeated cached hadoopSubmitJar2times exit0. Independent standard-library ZIP inspection finds all478 current core entries byte-identical in resulting bundle, no stale core extras, and exactly one matching embeddedbundle. WorkRecord.class current SHA2d4499e38b59488b4bb47aa6b12a682376d0fdad6887624e0e15c0ede4c1125e,14386bytes everywhere. Byte-check JSON retained.
RISKS: Final full build gate/review pending; AWS unverified.
NEXT GATE: Frozen92-path source/config gate, packaging, two fresh samples, independent final artifact verdict, human acceptance.


### Final post-packaging local verification

STATUS: COMPLETE for implementation and local gates; independent final verdict pending.
OWNER: Coordinator assembling separate domain/Hadoop/build work orders performed by existing implementation worker, independent test owner, and read-only reviewer.
COMMANDS RUN / TEST RESULTS: Exact replay/raw evidence in finaltestreport. Fullgateexit0 at22:19:10/399sec with220passes (core99,Hadoop64,independent53,build4), zero failures/errors/skips. Packaging22:19:11/1sec verifies all478 current core entries and one matching nestedbundle; two fresh sample runs22:19:32/21sec compare equivalent and are not reused.92source/config fingerprints unchanged.
VALIDATION RESULTS: All cited source-evidence defects and observed stale-core cache mechanism repaired. Negative evidence comparisons and actualJ09 reject partition regressions pass; two successive cached core overlays retain current bytes and remove obsolete entries. Prior218pass/stale-package evidence remains explicitly pre-fix.
RISKS: AWS unrun; XMLprefix replay performance limitation. No human ratification/phase acceptance inferred; reviewer context reused due native thread limit.
MANUAL ACTION REQUIRED: Human Phase4 decision after independent final verdict.
BLOCKED-ON OWNER: None for implementation.
BLOCKED-ON EVIDENCE: Formal final verdict pending.
NEXT GATE: Final independent report, then human decision.


### Final independent verdict

STATUS: COMPLETE for implementation, local verification and independent review.
OWNER: Coordinator assembling independent read-only reviewer report.
VALIDATION RESULTS: Final reviewer APPROVE, no remaining blocking findings in inspected scope. Independent artifact recheck confirms current core equality, stable source fingerprints and all220tests/sample gates. Full findings/resolution matrix in latest review.md section.
MANUAL ACTION REQUIRED: Human Phase4 review/acceptance.
BLOCKED-ON OWNER / EVIDENCE: None for reviewed implementation.
NEXT GATE: Human decision; no commit/push/cloud/Phase5 performed.

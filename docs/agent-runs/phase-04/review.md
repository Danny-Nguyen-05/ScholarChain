# Phase 4 review

STATUS: REQUEST-CHANGES

OWNER: code-reviewer, Grok 4.7 High, fresh context (`01851f5f-3af4-47c8-ac27-44e7f786298e`). No files were edited.

WORK ORDER: `docs/agent-runs/phase-04/prompt.md`. Base commit named by the orchestrator: `742aa0f209284eed257b8d070a40f8136b0fb543`. This review does not accept the phase.

FILES CREATED: Not classified. This review did not run `git status` or `git diff`.

FILES MODIFIED: Not classified against `742aa0f`.

COMMANDS RUN: None. No `git`, `sbt`, `shellcheck`, dataset, or EMR command was executed by the reviewer.

TEST RESULTS: Not observed by this reviewer. The orchestrator's `sbt -batch check` exit 0 was not rerun here.

VALIDATION RESULTS: Read-only inspection of the implementation and of run `target/phase4-runs/6cda1215-dff0-4e50-9356-e2bb9bdcad1c`. That directory contains `_SCHOLARCHAIN_COMPLETE`, counter totals INPUT 81, ACCEPTED 135, REJECTED 1, DUPLICATE 1, CONFLICT 0, EMITTED_PAIR 11, nine intermediate job outputs, and Spark-style JSON partitions. J05 stats record `largestBlock=4` and `largestPairExpansion=6`. Both J08 attempt stats record `largestPairExpansion=1`. `run-manifest.json` sets `configSchemaVersion` to `scholarchain.config.v1` while the fingerprint matches the hadoop-prep fingerprint note.

ASSUMPTIONS: LocalJobRunner is an acceptable local execution mode. Orchestrator-reported gates were not re-executed. Ownership was not verified from a diff. Sample immutability was not verified with git.

RISKS: `PrepJobs.configuration` sets `mapreduce.framework.name` to `local`, so an EMR step would still run LocalJobRunner on the master. The DBLP header scan stops at 65536 bytes. `maxLocalSampleRecords` is counted per map task.

MANUAL ACTION REQUIRED: Human acceptance is not recorded. Do not start Phase 5 from this verdict.

BLOCKED-ON OWNER: none for completing this review. Repairs go to the named owners.

BLOCKED-ON EVIDENCE: `git status` and `git diff` were not run by the reviewer. `sbt check`, checksums, shellcheck, and EMR were not run by the reviewer.

NEXT GATE: Repair the blocking findings, rerun `sbt check` and the two-run sample comparison, then a fresh read-only review.

## Blocking findings

1. High. Blocks Phase 4. Owner: `hadoop-engineer`. `DblpInput.scala:103` and `:134`. `readElement` and `readName` decode bytes with `b.toChar`. The header scan decodes UTF-8. A title containing `机器学习` is corrupted on the MapReduce path. `HadoopPrepSpec` preserves that text only by parsing an already-decoded string.

2. High. Blocks Phase 4. Owner: `hadoop-engineer`. `HadoopPrepPipeline.scala:90-96` and `PrepJobs.scala:419-458`. J07, J08, and J09 read J01/J02 outputs. J04 duplicate and conflict decisions stay on index rows. Run `6cda1215-dff0-4e50-9356-e2bb9bdcad1c` still exports both identical OpenAlex institution lines for `institution:ror:01x8rc503` after J04 wrote a `DUPLICATE_IDENTICAL_OBSERVATION` reject. A field present on only one of two conflicting payloads can still be emitted.

3. High. Blocks Phase 4. Owner: `hadoop-engineer`. `HadoopPrepPipeline.scala:53-54`. `Path.of(request.config.outputRoot).toAbsolutePath` is a local path. A loader-accepted `s3://phase4-bucket/out` is resolved under the process working directory.

4. High. Blocks Phase 4. Owner: `infra-engineer`. `scripts/phase4-emr-smoke.sh:129` and `:163-179`. `--output-prefix` is required and printed, and `build_steps_json` never puts it in the `hadoop jar` arguments.

5. Medium. Blocks Phase 4. Owner: `hadoop-engineer`. `PrepJobs.scala:514-524`, `PrepSupport.scala:524-541`, and `HadoopPrepPipeline.scala:195-196`. J05 stores block pair count `n*(n-1)/2` under `largestPairExpansion` (6 for a block of 4). J08 stores coauthor expansion under the same key (1 in the sample run). `StatsFiles.max` keeps 6, so the driver reports the block figure as pair expansion.

6. Medium. Blocks Phase 4. Owners: `domain-engineer`, then `hadoop-engineer`. `DomainValidation.scala:594-598` and `HadoopPrepPipeline.scala:162-166`. `RunManifest.configSchemaVersion` must be `scholarchain.config.v1`, so the pipeline stores the Hadoop-prep fingerprint under that schema name. The observed manifest shows that pair.

## Recheck after the six repairs

STATUS: REQUEST-CHANGES

OWNER: code-reviewer, Grok 4.7 High, fresh recheck (`06ae43f6-cc37-49fe-9c3c-be851eea9d4f`). No files were edited. `git status --short`, `git diff --name-status 742aa0f`, and `git ls-files --others --exclude-standard` exited 0. `sbt` was not rerun.

Findings 1, 3, 4, 5, and 6 are cleared in the current source. Finding 2 is not.

High. Blocks Phase 4. Owner: `hadoop-engineer`. `PrepJobs.scala:454` treats any distinct index-row `payloadHash` in one source, sourceRecordId, and snapshot group as a conflict. A work and its institution from one observation share that provenance and have different hashes, so the conflict branch writes no payload. `datasets/samples/openalex/works.jsonl` line 1 has an institution, so that work does not survive. The same reducer still emits a topic that appears on only one of two observations whose work JSON matches, and `ExportReducer` turns it into a `HasTopic` edge (`PrepJobs.scala:495-497` and `:877-883`). The 15:13 `sbt check` fixtures omit institutions, so exit 0 does not cover this.

NEXT GATE: `hadoop-engineer` repairs the J04 rule, `test-engineer` covers an institution-bearing survivor and a one-sided topic, the orchestrator reruns `sbt check`, then a fresh read-only review.

## Optional, not in this repair pass

- `PrepJobs.scala:24` forces LocalJobRunner for every launch, including EMR.
- `maxLocalSampleRecords` is applied per map task and uses `OversizeRecord`.
- `DerivedRecords.scala:65` returns no pair-stage reject when the team is already over the team limit.
- `PrepJobs.scala:600` drops an oversize candidate block with an empty reducer body after J05 already rejected it.
- A `PUBLIC` doctype is not flagged as unsafe. The custom reader does not fetch it.
- The Hadoop README does not state that no combiner is set.
- Crossref keeps the first date among several date fields. Cross-source years stay separate.

## Final join recheck

STATUS: APPROVE

OWNER: code-reviewer, Grok 4.7 High, fresh recheck (`df4a1ef1-cb0d-4748-aab9-5fc12487ee02`). No files were edited. No `git`, `sbt`, shellcheck, dataset, or EMR command was run by this reviewer.

WORK ORDER: Recheck the remaining `JoinReducer` blocker after the institution and one-sided-topic repair.

TEST RESULTS: Not rerun by the reviewer. Orchestrator-reported `sbt -batch check` exit 0 at 2026-10-06 15:30:34 local, 111 seconds, counts 93, Hadoop 15, independent 19, build-verification 2.

VALIDATION RESULTS: The join blocker is closed. One observation that emits a work plus an institution, venue, or topic is not a conflict. Two identical copies keep one survivor. Two observations with the same source, source record, and snapshot whose work or enrichment differs drop both sides, including a one-sided topic. Findings 1, 3, 4, 5, and 6 were spot-checked and no regression was seen.

RISKS: None that block Phase 4. `observationConflict` would miss a difference only if one observation repeated an identical side payload a multiple of the copy count and the other omitted it. That case is outside the repaired blocker.

MANUAL ACTION REQUIRED: Human acceptance is not recorded. Do not write `human-gate.md` or `accepted-commit.md` from this review. Do not begin Phase 5.

BLOCKED-ON OWNER: none

NEXT GATE: Human acceptance of Phase 4.

## Independent comprehensive Codex review — 2026-10-06

VERDICT: **REQUEST-CHANGES**

STATUS: COMPLETE (review completed; implementation is not accepted)

OWNER: Independent read-only `code-reviewer`, task `/root/phase4_independent_review`; report assembled by the coordinator.

WORK ORDER: Phase 4 work order and the human's request for an independent code review. Base: `742aa0f209284eed257b8d070a40f8136b0fb543`. Reviewed tracked changes and untracked implementation, tests, and reports.

FILES CREATED: none by the reviewer.

FILES MODIFIED: none by the reviewer. The coordinator appended this section to preserve the returned findings; prior reviews remain historical evidence.

COMMANDS RUN: Read-only git status/diff/untracked inventory, file searches and source reads, retained-log and sample-output inspection. Reviewed the course README's Phase 4 and Detailed Hadoop requirements. No builds, tests, scripts, AWS operations, or implementation edits were performed in this review.

TEST RESULTS: No fresh execution. `/tmp/scholarchain-check3.log` records 93 core, 15 Hadoop, 19 independent, and 2 build-verification tests passing (129 total), genuine LocalJobRunner completions, and successful `sbt check` after 111 seconds at 2026-10-06 15:30:34 local. The independent suite completed in 167 milliseconds with reused output; see finding 11. Dataset/checksum and script syntax/dry-run results remain prior-owner observations.

VALIDATION RESULTS: REQUEST-CHANGES. Retained sample outputs contain nine intermediate `_SUCCESS` markers, export success, manifest, completion marker, counters, and partitioned records. Reused Phase 3 records remain additive, and team/authorship/pair construction uses contextual validation and preserves endpoint ordinals. These checks do not clear the findings below.

ASSUMPTIONS: LocalJobRunner is authorized for local gates. Actual EMR/AWS execution is outside the work order. Missing live execution, human acceptance, and an accepted Phase 4 commit are not defects.

RISKS: Small samples and existing passing tests do not establish general XML correctness, non-exact candidate generation, resource bounds, fresh independent execution, processing-identity reuse, or cluster launch compatibility.

MANUAL ACTION REQUIRED: Route repairs to the listed owners. Human acceptance follows repaired gates and independent review; this report grants no deployment or Phase 5 approval.

BLOCKED-ON OWNER: hadoop-engineer, build-engineer, test-engineer, domain-engineer, and infra-engineer as assigned below; consult dataset-engineer for authoritative acquisition metadata.

BLOCKED-ON EVIDENCE: The 19 blocking findings below. Reproducers are static reasoning examples, not executed probes.

NEXT GATE: Repair blocking findings together; execute `sbt check` with fresh independent job outputs, bounded four-source pipeline twice, packaging verification, and script syntax/dry-run validation. Retain evidence and obtain a fresh review.

### Blocking findings

Path abbreviations below: Hadoop files are under `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/`; independent test files are under `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/`. All line numbers refer to this reviewed working tree.

1. **High: Required researcher/bibliographic blocking and features are absent.** Owner: hadoop-engineer; domain-engineer for necessary shared-contract extensions. `DerivedRecords.scala:301`, `PrepJobs.scala:554`, `DerivedRecords.scala:318`. Only exact work identifiers generate blocks. ORCID/OpenAlex author indexes are ignored; features are block size, exact equality, and work-ID presence/equality. Same title/year/authors without a shared exact identifier produces no candidate. Implement name/initial/title/year/venue/affiliation/coauthor blocks, fallback keys, and deterministic bibliographic features.

2. **High: The authored EMR command cannot process S3 paths.** Owners: hadoop-engineer and infra-engineer. `HadoopPrepMain.scala:28`, `HadoopPrepPipeline.scala:42` and `:69`, `PrepJobs.scala:24`, `PrepSupport.scala:517`, `scripts/phase4-emr-smoke.sh:185`. Inputs use local NIO paths and `Files.isRegularFile`; every remote output root returns `Left`, even with a Hadoop filesystem. Jobs force LocalJobRunner and statistics use local files. The script passes S3 inputs/output. Provide compatible Hadoop filesystem operations and explicit local/cluster execution; no live AWS run is needed to establish this defect.

3. **High: Cluster packaging omits application dependencies.** Owners: build-engineer, then infra-engineer. `build.sbt:28` and `:179`, `project/HadoopPackaging.md:10` and `:67`, `scripts/phase4-emr-smoke.sh:186`. The submitted thin module JAR contains neither core nor Scala 3/uPickle/ujson dependencies, and the command supplies no dependency bundle/classpath. Cluster Hadoop does not supply those libraries. Preserve Hadoop Provided scope and distribute verified non-Hadoop dependencies.

4. **High: XML entities reject valid text or turn character data into markup.** Owner: hadoop-engineer. `DblpExtract.scala:55` and `:97`. Repeated expansion turns `<title>A &amp; B</title>` into a bare ampersand and then rejects it; `&#38;` behaves similarly. Escaped tag-looking text becomes markup before string-based child extraction. Resolve entities while preserving character-data boundaries.

5. **High: DBLP framing/parsing does not validate XML boundaries or well-formedness.** Owner: hadoop-engineer. `DblpInput.scala:70`, `:102`, and `:111`; `DblpExtract.scala:254`. Comment/declaration tags can be recognized as records; closing-tag text in comments/CDATA can end one. EOF does not mark a record unterminated. A truncated article with author/title but no root close can be accepted. Self-closing records may consume later records; unknown top-level elements disappear. Use XML-aware framing and validation with explicit rejects.

6. **High: Reducer limits apply after unbounded allocation.** Owner: hadoop-engineer. `PrepJobs.scala:446`, `:591`, and `:666`. J04/J05/J06 materialize entire groups before checking limits, so huge exact-ID groups or repeated observations can exhaust memory before rejection. Retain bounded state, count/drain excess records, and emit explicit outcomes.

7. **High: Sparse abstract positions permit enormous expansion.** Owner: hadoop-engineer. `JsonSources.scala:1005` and `:1012`. `{"x":[2147483647]}` passes the position check but iterates billions of slots. Record byte limits do not bound reconstructed text. Validate positions, density, and output size before expansion and retain rejects.

8. **High: Successful pipeline execution collects the full export in driver memory.** Owner: hadoop-engineer. `PrepJobs.scala:925`, `HadoopPrepPipeline.scala:237`, `PrepSupport.scala:472`. Reference checking and representative extraction read all works/text/export records into buffers, including `--once`. Keep validation distributed and sample extraction bounded; full comparison belongs only in an explicitly bounded verification path.

9. **High: Flattened observations yield incorrect duplicate/conflict decisions.** Owner: hadoop-engineer. `PrepJobs.scala:482` and `:524`, `JsonSources.scala:809`. One observation may repeat an institution through several authors; the retained single OpenAlex input incorrectly produces a duplicate-observation reject for ROR `01x8rc503`. Side-record divisibility cannot detect complete observation agreement: two copies on one side and none on the other can pass. ORCID activity paths are deduplicated before contradictory payloads reach conflict accounting. Carry input-observation boundaries and compare complete observations.

10. **High: Output reuse verifies neither full processing identity nor required outputs.** Owner: hadoop-engineer. `PrepSupport.scala:426`, `HadoopPrepPipeline.scala:56` and `:223`. Matching ignores run ID, source snapshots, schema/transformation versions, and manifest/export existence. Changed snapshot requests can reuse old results; deleting exports but leaving the marker can still return success. Bind identity and verify required artifacts before reuse.

11. **High: Independent tests can pass using stale outputs.** Owner: test-engineer. `IndependentTestSupport.scala:24`, `IndependentHadoopPipelineSpec.scala:54` and `:450`. Fixed directories and run UUIDs reuse completed runs instead of exercising current mapper/reducer code. The final log's 19 independent tests finish in 167 milliseconds without fresh independent job completions. Use fresh output/run identities and assert `reused=false`, except in dedicated reuse tests.

12. **High: Snapshot provenance is fixed independently of source acquisition.** Owner: hadoop-engineer; consult dataset-engineer. `HadoopPrepPipeline.scala:33`, `HadoopPrepMain.scala:38`, `datasets/dataset-manifest.yaml`. Enrichment sources are labeled `*-sample-2026-10-03`, while accepted inputs are API records retrieved October 5 without pinned October 3 bulk snapshots. Overrides still receive those labels and omit retrieval dates. Require/load truthful acquisition metadata and bind it into processing identity.

13. **High: Crossref drops available affiliations and abstracts.** Owner: hadoop-engineer; domain-engineer for a necessary evidence-contract addition. `JsonSources.scala:448` and `:528`. Authors' affiliations are not retained, and abstract references are always absent with no emitted text document even when an abstract exists. Preserve observed affiliations without inventing institution identity and emit a reproducible abstract reference/content when supplied.

14. **High: Standalone author-mention export is missing.** Owner: hadoop-engineer. `PrepSupport.scala:70` and `:90`, `PrepJobs.scala:888`. No author-mention kind/case/partition exists; mentions remain nested in works. Emit the existing AuthorMention contract in source snapshot/run partitions for downstream resolution.

15. **Medium: Invalid optional identifiers and failed enrichment vanish.** Owner: hadoop-engineer. `JsonSources.scala:822`, `:904`, and `:935`. Malformed ORCID work DOI becomes `None`; malformed ROR can be dropped/fallback used; failed validation is discarded through `Either.foreach`. Retain explicit invalid-identifier/schema rejects rather than silently removing supplied evidence.

16. **Medium: The local sample cap is per mapper and changes with splitting.** Owner: hadoop-engineer; infra-engineer for the smoke contract. `PrepJobs.scala:229` and `:309`. One split with cap one accepts one record; three splits can accept three. The cap does not bound the launch and changes logical output for the same input. Establish a deterministic launch-level bounded-input policy.

17. **Medium: JSON byte limits run after complete-line allocation.** Owner: hadoop-engineer. `PrepJobs.scala:81` and `:312`. Ordinary TextInputFormat allocates the whole line and the mapper creates a String before checking maxRecordBytes. Oversized JSON can exhaust memory first. Bound reading and drain excess bytes while retaining a diagnostic reject.

18. **Medium: The intermediate compression option only compresses shuffle.** Owner: hadoop-engineer. `PrepJobs.scala:39`. No intermediate FileOutputFormat compression/codec is enabled, so J01–J08 files stay uncompressed even with the option enabled. Implement/document the enabled path and verify downstream reading; the sample's `none` setting does not cover it.

19. **Medium: Effective configuration overrides bypass validation.** Owner: hadoop-engineer. `HadoopPrepMain.scala:24` and `:84`, `HadoopPrepPipeline.scala:40`. `--output-root` is copied after validation; public Request configs are not validated at execution. Empty/unresolved roots or invalid programmatic limits can reach jobs. Validate final effective configuration before output claim or launch.

### Nonblocking findings

- **Low: Stale/incomplete Hadoop launch and job-contract documentation.** Owner: hadoop-engineer. `modules/hadoop/README.md:66` describes the repaired alias as the old background task; `:14` shows stale stage routing; `:31` claims work-ID keys although TaskSink writes record-kind keys. Correct these and complete per-job partitioner/combiner/reducer/compression/reject/prefix/fixture descriptions.
- **Low: Missing institution name becomes invented source display text.** Owner: hadoop-engineer. `JsonSources.scala:903` substitutes `institution`. Preserve absence or reject missing required data instead of emitting that label as an observation.
- **Low: Index exports use the derived snapshot partition.** Owner: hadoop-engineer. `PrepJobs.scala:829` examines top-level fields, while `IndexRow` nests snapshot/provenance under `entry` (`PrepSupport.scala:166`). Handle the wrapper or export the shared entry contract.
- **Low: Evidence is mostly summaries and ephemeral paths.** Owner: coordinator. Current owner/test reports cite ignored run directories and a `/tmp` log without compact full candidate/team/pair/reject JSON or job-completion excerpts in the phase directory. Preserve actual representative evidence and fresh independent execution after repairs.

This review reports all confirmed findings from its inspection. It does not guarantee that no further defects exist. The earlier APPROVE was a narrower join recheck and is superseded for readiness by this comprehensive verdict.

## Recheck after the 19-finding repairs — 2026-10-07

STATUS: REQUEST-CHANGES

OWNER: code-reviewer, Grok 4.7 High, fresh context (`a672b169-c0b7-40b5-ad43-b718652f95a4`). No files were edited. No `sbt`, git, AWS, or download command was run.

WORK ORDER: Recheck the 19 blocking findings after the repairs recorded in `repairs.md`. Base `742aa0f209284eed257b8d070a40f8136b0fb543`.

TEST RESULTS: Not rerun here. Orchestrator-reported `sbt -batch check` exit 0 at 2026-10-07 10:05:28 local, 285 seconds, core 96, Hadoop 28, independent 20, build-verification 2. Two sample runs `logicalRecordsEqual=true`, both `reused=false`, counters INPUT 193, ACCEPTED 239, REJECTED 0, EMITTED_PAIR 45.

VALIDATION RESULTS: Findings 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, and 19 are cleared in the current source. Findings 2, 15, and 16 remain blocking. The four earlier low notes are not still present, except that phase evidence still cites gitignored run directories without compact export JSON. That evidence gap does not block Phase 4.

MANUAL ACTION REQUIRED: Route findings 2, 15, and 16 to `hadoop-engineer`. Do not write `human-gate.md`. Do not begin Phase 5.

NEXT GATE: Repair the three findings, rerun `sbt check`, the two-run sample comparison, packaging verification, and the EMR dry-run, then a fresh read-only review.

### Still blocking

2. **High.** `HadoopPrepPipeline.resolveOutput` (`HadoopPrepPipeline.scala:76-81`) returns `Left` for every `s3`, `s3a`, `s3n`, and `hdfs` root. `execute` stops before `FileOutputFormat`. Job outputs remain `java.nio.file.Path`. `scripts/phase4-emr-smoke.sh` passes the S3 prefix as `--output-root`, so the authored cluster command cannot write its output. Cluster mode itself does not force LocalJobRunner, and remote inputs already use Hadoop paths.

15. **Medium.** A malformed OpenAlex institution id is discarded when ROR parses (`JsonSources.scala:1191-1206`). A venue id that fails `parseVenueId` is omitted (`JsonSources.scala:1296-1297`). A topic id that fails `topicIdFromOpenAlex` is omitted (`JsonSources.scala:1318-1325`). `DomainValidation.check(graph).foreach` writes only the `Right` edge (`PrepJobs.scala:1043-1046` and `:1051-1054`).

16. **Medium.** Sample cutoff lookup keeps the last path whose name is `works.jsonl` (`HadoopIO.scala:272-286`). The committed OpenAlex and Crossref samples are both named `works.jsonl`, so one mapper can apply the other file's cutoff.

## User-supplied recheck of findings 2, 15, and 16

STATUS: REQUEST-CHANGES

OWNER: code-reviewer. Read-only. No files edited. No sbt, AWS, or commit. The user supplied this verdict after their own review.

VALIDATION RESULTS: Findings 15 and 16 are cleared. Finding 2 remains blocking. Findings 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, and 19 showed no regression. `tests/` matches the current `Request`, `Result.directory`, and `OutputGate.claim` signatures by inspection. Compilation was not run.

2. **Still blocking. High.** `resolveOutput` now keeps remote schemes as Hadoop paths. `HadoopPrepPipeline.scala:245` still returns `Left` after a successful remote write and completion marker because `Result.directory` requires a local `java.nio.file.Path`. Line 75 returns `Left` for remote reuse. The EMR script still passes the S3 prefix as `--output-root`. A missing local S3 implementation does not justify those unconditional failure branches. Owner: `hadoop-engineer`.

NEXT GATE: Repair remote success and reuse. Human acceptance is not recorded. Do not begin Phase 5.

## User-supplied recheck of remote success

STATUS: REQUEST-CHANGES

OWNER: code-reviewer. Read-only. No files edited. No sbt, AWS, or commit. The user supplied this verdict.

VALIDATION RESULTS: Finding 2 is cleared for remote execution and reuse. `RemoteOutputPath` is a non-local carrier. Findings 1 and 3 through 19 showed no regression. `tests/` still matches `Result.directory` by inspection.

**Still blocking. High.** Local export comparison can report false equality. `Result.outputLocation` for a local run is a `file:/…` URI with one slash. `FsPaths.file` (`HadoopIO.scala:29`) treats only `://` as a URI, so `Path.of("file:/…")` becomes a literal path under a `file:` directory. `HadoopPrepMain.exportDigest` (`HadoopPrepMain.scala:141`) uses that conversion and returns `"0"` when the wrong location is absent. Two successful local runs can print `logicalRecordsEqual=true` without reading either export. Owner: `hadoop-engineer`.

Required repair: preserve `file:` URIs when reconstructing Hadoop paths, fail the comparison when an export is missing, and add local comparison tests for different exports and a missing export.

NEXT GATE: Repair and test the comparison. Human acceptance is not recorded. Do not begin Phase 5.

## User-supplied recheck of the local digest

STATUS: REQUEST-CHANGES

OWNER: code-reviewer. Read-only. No files edited. No sbt, AWS, or commit. The user supplied this verdict.

VALIDATION RESULTS: The `file:/…` reconstruction and the missing-export `None` comparison are cleared. Finding 2 remains cleared for remote success and reuse. Findings 1 and 3 through 19 showed no regression. `tests/` still matches the current signatures by inspection.

**Still blocking. High.** `HadoopPrepMain.exportDigest` XORs record hashes and appends the record count (`HadoopPrepMain.scala:182`). Exports `[A, A]` and `[B, B]` both become count 2 and an all-zero mix, so `logicalRecordsEqual=true` can certify different exports. This is XOR cancellation, not a SHA-256 collision. Owner: `hadoop-engineer`.

Required repair: an order-independent comparison that preserves duplicate multiplicity and stays bounded in memory. Add a regression test comparing `[A, A]` with `[B, B]`.

NEXT GATE: Repair the digest, then fresh checks and a read-only review. Human acceptance is not recorded. Do not begin Phase 5.

## Fresh independent repaired Phase 4 review — 2026-10-07

VERDICT: **REQUEST-CHANGES**

STATUS: COMPLETE — review completed; Phase 4 is not ready for acceptance.

OWNER: Independent read-only `code-reviewer`, task `/root/phase4_repaired_code_review`. The coordinator assembled this section. This review covers Phase 4.

WORK ORDER: Repaired Phase 4 against base `742aa0f209284eed257b8d070a40f8136b0fb543`, all 19 prior comprehensive findings, and subsequent remote-output, file-URI, and digest repairs.

FILES CREATED: None by the reviewer. Inspected both tracked changes and untracked implementation/tests/evidence. Historical `file:/.../stats` artifacts were inventoried; their existence alone is not a finding against current source.

FILES MODIFIED: None by the reviewer. Coordinator appended this report; no implementation changes were made during this review.

COMMANDS RUN: Read-only git status/diff/untracked inventory, searches, source/document/log reads, file timestamps, and JAR archive listings. Consulted the course Phase 4 requirements and Apache Hadoop 3.3.6 RunJar source. No builds, tests, project scripts, AWS operations, or edits by the reviewer.

TEST RESULTS:

- Retained `/tmp/scholarchain-check7.log` records successful full check at 2026-10-07 10:05:28: 96 core + 28 Hadoop + 20 independent + 2 build tests = **146 passing**. Independent execution took 2m23s, clearing the earlier stale-output test problem.
- Retained `modules/hadoop/target/test-reports/TEST-edu.uic.cs441.scholarchain.hadoop.HadoopPrepReviewSpec.xml` records **23 tests, zero failures/errors**, timestamp 2026-10-07T11:10:20. It covers file-URI/missing-export comparison and duplicate-multiplicity regressions, and postdates HadoopPrepMain's 11:10:06 modification.
- The full gate and retained two-run sample execution predate the latest URI/digest repairs. Fresh full-check and two-run evidence covering the final tree remain pending. The targeted tests passed; no fresh test execution was performed by this reviewer.

VALIDATION RESULTS: **Five confirmed blocking findings**, below. Most previous findings are resolved; the matrix records their dispositions. Static reproducers are reasoning examples, not executed probes.

### Remaining blocking findings

Hadoop filenames below are under `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/`. Lines refer to this reviewed working tree.

1. **High — Dependency bundle is neither bootstrapped for the driver nor distributed to tasks.** Blocks Phase 4. Locations: `HadoopPrepMain.scala:21`, `PrepJobs.scala:24`, `scripts/phase4-emr-smoke.sh:203`, `project/HadoopPackaging.md:90`.

   The invocation passes `-libjars` after the Scala main, but main never parses it. No GenericOptionsParser, ToolRunner, or tmpjars handling exists; jobs construct fresh Configuration. Hadoop RunJar loads the submitted JAR/classes/lib entries and forwards remaining arguments verbatim, without interpreting `-libjars`. A Hadoop installation without Scala/core/JSON application dependencies cannot bootstrap this main. Independently placing libraries on the driver classpath still leaves no authored task dependency-distribution mechanism. The bundle archive now correctly includes core/Scala/JSON dependencies, but its existence does not fix loading. Primary evidence: [Hadoop 3.3.6 RunJar source](https://raw.githubusercontent.com/apache/hadoop/rel/release-3.3.6/hadoop-common-project/hadoop-common/src/main/java/org/apache/hadoop/util/RunJar.java).

   Impact: driver class-loading failure or missing dependencies in task containers. Owners: build-engineer for executable bootstrap/packaging, hadoop-engineer for dependency configuration propagation, infra-engineer for matching submission. Preserve Hadoop Provided scope.

2. **High — Remote JAR/config URIs are advertised but passed to local APIs without localization.** Blocks Phase 4. Locations: `scripts/phase4-emr-smoke.sh:31`, `:157`, `:205`, `:215`; `HadoopPrepMain.scala:21`; `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/HadoopPrepConfigLoader.scala:38`.

   The script accepts cluster-visible S3/HDFS paths and passes them directly. `--jar s3://bucket/jobs/job.jar` reaches RunJar's local java.io.File path. `--config s3://bucket/config/prep.json` reaches Path.of and Files.isRegularFile, so it is treated as a missing local file; HDFS config has the same problem. Correct remote data input/output support does not fix these artifact/config paths.

   Impact: supported-looking commands cannot execute even after dependency loading is repaired. Owners: infra-engineer to localize artifacts/config or explicitly require validated local driver paths; hadoop-engineer if main supports remote config. Consult domain-engineer for shared-loader changes.

3. **High — Normal upstream DBLP SYSTEM DOCTYPE rejects every publication.** Blocks Phase 4. Locations: `DblpExtract.scala:28` and `:32`, `PrepJobs.scala:357`, `datasets/schemas/dblp-xml.md:3`.

   `DblpXml.header("<!DOCTYPE dblp SYSTEM \"dblp-2023-06-28.dtd\">")` sets unsafe external-DTD metadata. J01 consequently rejects each record as UNSAFE_ENTITY. The source schema identifies that declaration as the upstream DBLP format; no approved local DTD/entity-catalogue resolution exists in the Hadoop code. The self-contained committed sample passes while the selected upstream dump cannot be processed.

   Owner: hadoop-engineer, with dataset-engineer for vetted catalogue/resource provenance. Support approved local declarations/catalogue while preventing arbitrary network retrieval or file access.

4. **High — Field extraction still interprets comments/CDATA as publication elements.** Blocks Phase 4; prior finding 5 is partially repaired. Locations: `DblpExtract.scala:134`, `:175`, `:648`.

   Static reproducer:

   ```xml
   <article key="conf/review/Comment1">
     <!-- <title>Fake</title><author>Fake Author</author> -->
     <title>Real</title><author>Real Author</author>
   </article>
   ```

   `children(xml, "title")` substring-scans the comment and selects Fake first; `authorElements` finds the commented author and emits both authors. Tag-shaped CDATA has the same issue. Framing repairs preserve the whole record but do not make field extraction XML-aware. Existing comment/CDATA tests focus on closing-tag framing rather than metadata extraction.

   Impact: invented titles/authors contaminate mentions, positions, teams, pairs, blocking, and export. Owner: hadoop-engineer for bounded XML-aware extraction; test-engineer for independent adversarial coverage.

5. **High — Oversize XML still allocates unbounded nesting and tag-name state.** Blocks Phase 4. Locations: `DblpInput.scala:151`, `:152`, `:221`, `:226`.

   `readElement` stops retaining record bytes after maxRecordBytes but continues appending every nested tag name to openNames. An oversize record containing arbitrarily many nested `<i>` elements grows that buffer until closes/EOF. nameBuf also receives name bytes independently of the byte cap. Draining oversized XML therefore remains unbounded in memory.

   Impact: mapper memory exhaustion before an explicit reject. Owner: hadoop-engineer to bound nesting/name state and drain without further unbounded allocation; test-engineer for independent resource-bound coverage.

### Prior 19-finding resolution matrix

| Prior finding | Disposition | Evidence |
| --- | --- | --- |
| 1. Missing blocking/features | Closed for reported omission | DerivedRecords:325 adds name/initial/title-year/venue/affiliation/coauthor keys; :506 adds features. |
| 2. Remote paths/forced local framework | Partially closed | Hadoop paths, YARN mode, remote success/reuse and statistics are repaired; current launch findings 1–2 remain. |
| 3. Missing cluster dependencies | Partially closed | Correct bundle exists; current finding 1 remains. |
| 4. Ampersand/entity re-expansion | Closed | Literal replacements not recursively reparsed; targeted tests pass. Field extraction is separate current finding 4. |
| 5. XML boundaries/well-formedness | Partially closed | Framing tracks comments/CDATA, self-closing and unterminated records; field extraction remains current finding 4. |
| 6. Unbounded reducer groups | Closed for reported reducers | J04/J05/J06 retain bounded groups and drain excess. XML state is separate current finding 5. |
| 7. Sparse abstract expansion | Closed | JsonSources:1386 bounds positions/span/reconstructed size before allocation. |
| 8. Driver collects full export | Closed | Distributed reference checks, bounded representatives, streaming comparison. |
| 9. Duplicate/conflict observation boundaries | Closed | Instance grouping and complete-observation comparison; repeated institutions no longer count as duplicate observations. |
| 10. Incomplete reuse identity/artifacts | Closed for reported cases | Run/config/checksum/snapshot/retrieval/schema/transformation identity and recorded manifest/partitions checked. |
| 11. Stale independent tests | Closed | Fresh directories/IDs, reused=false assertions, retained 2m23s independent execution. |
| 12. Incorrect snapshot provenance | Closed | Acquisition index binds samples; overrides require snapshot/retrieval metadata. |
| 13. Crossref affiliation/abstract loss | Closed | Mention affiliations and emitted abstract/reference with targeted coverage. |
| 14. Missing standalone mentions | Closed | J09 emits AuthorMention at PrepJobs:1099. |
| 15. Identifier/schema evidence discarded | Closed for reported cases | Explicit invalid identifier/enrichment and graph schema rejects with targeted coverage. |
| 16. Split-dependent cap/basename collisions | Closed | Launch-wide cutoffs and qualified-URI lookup; split/shared-basename regressions. |
| 17. JSON allocation before byte cap | Closed | BoundedLineRecordReader retains bounded bytes and drains overflow. |
| 18. Intermediate compression | Closed | J01–J08 FileOutputFormat compression and downstream regression. |
| 19. Unvalidated overrides | Closed | Effective config validated at execution before output claim/launch. |

Subsequent remote success/reuse repairs, file:/ reconstruction, missing-export equality, and XOR duplicate cancellation are closed. Current comparison adds unsigned SHA-256 integers and retains record count; the fresh targeted report covers duplicate multiplicity and order.

### Evidence and nonblocking notes

- `/tmp/scholarchain-sample-run.log` records a9835bef-fbe4-448f-b5b7-da005025cadd and 0fff2513-640b-4b46-ac04-3b854ce45071, both reused=false with logical equality and reported counters. These runs predate the final digest implementation.
- `/tmp/scholarchain-bundle.log` retains the initial missing-core failure, not the successful follow-up. Current archive inspection supports the repaired contents; do not describe the failed log as successful evidence.
- AWS remains unverified and appropriately unexecuted. No live run is needed to establish the static launch defects. Human acceptance/accepted commit remain appropriately absent.
- Nonblocking: modules/hadoop/README.md still describes J07/J08 grouping by work ID although mapper sink writes record-kind keys. Owner: hadoop-engineer.
- Nonblocking: retain compact actual records/job evidence and identify the final gate; historical summaries still describe superseded behavior and point to ephemeral/ignored evidence. Owner: coordinator.

ASSUMPTIONS: LocalJobRunner authorized; EMR authoring-only. Executable cluster compatibility remains required. Final identity decisions are outside Phase 4.

RISKS: Bounded samples and targeted tests do not cover the confirmed bootstrap, artifact/config localization, upstream DTD, XML field extraction, or XML allocation defects.

MANUAL ACTION REQUIRED: Route five findings to owners. After repairs retain fresh full sbt check, two fresh equivalent sample runs, packaging/bootstrap verification, and script dry-run evidence. No AWS submission is requested.

BLOCKED-ON OWNER: hadoop-engineer, build-engineer, infra-engineer; supporting dataset/test work above.

BLOCKED-ON EVIDENCE: Five static defects and final full-gate/two-run evidence predating latest changes despite fresh targeted tests.

NEXT GATE: Owner repairs and observed gates, then fresh independent review. Human acceptance follows APPROVE. Do not begin Phase 5.

## Independent recheck of the five repairs — 2026-10-07

VERDICT: **REQUEST-CHANGES**

STATUS: COMPLETE — review completed; four confirmed XML correctness findings block Phase 4.

OWNER: Independent read-only `code-reviewer`, task `/root/phase4_five_repairs_review`. Coordinator assembled this report.

WORK ORDER: Recheck the latest five blockers and affected prior findings against base `742aa0f209284eed257b8d070a40f8136b0fb543`, including tracked and untracked implementation and tests.

FILES CREATED: None by the reviewer.

FILES MODIFIED: None by the reviewer. Coordinator appended this evidence; implementation remained unchanged.

COMMANDS RUN: Read-only git status/diff, searches, source/document reads, inventory and timestamps. An initial document read used the workspace parent and was repeated in the repository. No builds, tests, scripts, downloads, AWS actions or writes by the reviewer. Coordinator additionally inspected the submit/bundle ZIP archives and retained JUnit evidence without executing application code or modifying files.

TEST RESULTS: **164 retained fresh tests passing**, zero failures/errors: core 96, Hadoop 42, independent 24, build verification 2. Reports at 13:07–13:11 October 7 postdate reviewed repairs. `.claude/.last-test-run` records success=true and timestamp 1791396708879 (13:11:48 local). The independent sample replay passed in 20.039 seconds; its source asserts two successful fresh runs, reused=false, author-mention exports and logical equivalence. This supports fresh full-gate and two-run evidence. No fresh standalone HadoopPrepMain stdout log was located; no test was rerun by the reviewer or coordinator.

VALIDATION RESULTS: Packaging/bootstrap, dependency distribution, artifact/config localization and approved DTD support are repaired. The covered metadata-injection and internal nesting/name cases are repaired. Four remaining static defects follow; reproducers were not executed in this review.

### Remaining blocking findings

Hadoop filenames below are under `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/`. Lines refer to the reviewed working tree.

1. **High — Opening-name scanning remains unbounded before record limits apply.** `DblpInput.scala:352–365`, especially `:359`. `classify` appends every opening-name byte to a ByteArrayOutputStream and creates the full string in nextOpen before readElement applies its limits. `<dblp><` followed by an arbitrarily long name can exhaust driver/mapper memory through SampleBound.scanXml or the record reader, despite maxRecordBytes/MaxStoredTagNameBytes. Existing name-limit tests exercise inner names after supplying the root name. Bound opener retention and diagnostics, drain oversized names without full allocation, and preserve an explicit reject. Test through nextOpen/actual InputFormat and launch scanning.

2. **Medium — Literal CDATA is incorrectly treated as entity-reference syntax.** `DblpExtract.scala:230`, `:312–320`, `:557–565`, `:732`. characterData removes CDATA boundaries before callers invoke expand. Valid `<title><![CDATA[A & B]]></title>` becomes bare `A & B` and is rejected as MALFORMED_RECORD. `<title><![CDATA[A &amp; B]]></title>` changes literal `A &amp; B` into `A & B`. Author text has the same path. Preserve CDATA literally, expand references only in segments where XML references are active, and bound the combined result. Cover title and author fields with bare ampersands and entity-shaped literal content.

3. **Medium — Valid quote/closing-tag syntax drops identifiers or rejects valid records.** `DblpExtract.scala:415–421`, `:900–904`. attributeValue only recognizes double quotes. Single-quoted publication keys are treated as missing; `<author orcid='0000-0002-4414-6920'>Ada</author>` can be accepted while losing its supplied ORCID. Separately, elements recognizes `</author >` but innerText requires exact `</author>`, producing a blank-author reject for valid whitespace. Support both XML quotation forms and recognized closing boundaries. Cover single-quoted keys/ORCIDs and closing whitespace.

4. **Medium — Mismatched closing tags can become accepted works.** `DblpInput.scala:275–283`; `DblpExtract.scala:505` and subsequent build extraction. An unmatched close returns the framer to State.Text without a malformed flag. `<article key="conf/review/BadClose"><title>T</title></bogus></article>` reaches a matching final article close and field extraction can emit a work. No separate well-formedness validation rejects it. Preserve malformed framing and/or validate bounded XML before accepting fields, retaining external-entity restrictions. Cover unmatched/mismatched closes and explicit malformed outcomes.

**Owners for all four:** hadoop-engineer for implementation/module tests; test-engineer for independent coverage. **All four block Phase 4.** Route together rather than one finding per repair pass.

### Five-repair resolution

| Previous blocker | Current disposition |
| --- | --- |
| Driver bootstrap/task dependencies | Closed: submit JAR embeds bundle at lib/, GenericOptionsParser handles generic options, Request.hadoopConf reaches copied job configuration and preserves tmpjars. |
| Remote artifact/config localization | Closed: master-side step localizes JAR/bundle/config and supplies local driver paths plus bundle classpath. |
| Approved DBLP SYSTEM DTD/catalogue | Closed for supported approved catalogue: classpath declarations, restricted basenames, no external URL/file resolution; fresh entity tests pass. |
| Comment/CDATA metadata injection | Reported injection closed: element lookup skips those constructs. Literal CDATA semantics remain finding 2. |
| Nesting/name allocation | readElement limits repaired; opener scanning remains finding 1. |

Current archive inspection confirms main class/catalogue and exactly one nested dependency bundle in the submit JAR. Nested bytes match the external bundle; it includes core/Scala/uPickle/ujson and excludes Hadoop module and org/apache/hadoop classes. AWS/cluster execution remains unrun, as authorized.

No regression found in affected prior repairs for blocking/features, remote success/reuse, reducer/abstract bounds, streaming export, observation/reuse identity, fresh independent runs, acquisition metadata, Crossref evidence, standalone mentions, qualified sample cutoffs, bounded JSON reading, compression or effective-config validation. Ordinary ampersand/numeric-reference expansion remains repaired; CDATA is an adjacent gap. Prior well-formedness finding remains partially open through finding 4; supplied DBLP ORCID retention remains open through finding 3 despite repaired JSON identifier rejects.

ASSUMPTIONS: LocalJobRunner authorized; EMR authoring-only; final identity decisions outside Phase 4. Absence of live AWS execution is not a finding.

RISKS: Passing bounded samples/adversarial tests do not cover these four reproducers. This review reports confirmed findings, not an exhaustive proof of correctness.

MANUAL ACTION REQUIRED: Route four repairs together; add feature and independent regressions, rerun gates, then obtain independent review. Human acceptance remains unrecorded.

BLOCKED-ON OWNER: hadoop-engineer, with test-engineer for independent coverage.

BLOCKED-ON EVIDENCE: Four source defects above.

NEXT GATE: Repair all four; retain successful sbt check, fresh two-run equivalence and packaging/script validation; then independent review. Do not begin Phase 5.

Nonblocking: owner/test reports still contain historical superseded contracts/counts. This section records the fresh 164-test evidence and repaired packaging/localization contract; incorporate final accepted evidence into those reports after repairs. Documentation refresh alone does not block this phase.

## Independent final recheck of the four XML repairs — 2026-10-07

VERDICT: **APPROVE for the routed XML repairs and completed local gates.** No remaining blocking finding identified. Human Phase 4 acceptance remains pending.

STATUS: COMPLETE.

OWNER: Independent read-only `code-reviewer`, `/root/xml_repair_reviewer`. Coordinator assembled the returned report without changing implementation.

WORK ORDER: Recheck the four XML blockers from this file's prior section at line 347 onward, final regression repairs, and affected packaging/EMR behavior.

FILES CREATED / MODIFIED: None by reviewer. Coordinator appended this report.

### Final code assessment

Hadoop filenames are under `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/`.

| Recorded finding | Final disposition |
| --- | --- |
| Unbounded opening-name allocation | Closed. `DblpInput.scala:376–392` bounds retained name bytes while counting the full name; `:160–173` propagates that count into oversize framing. Actual InputFormat and launch-scanning regressions pass. |
| Literal CDATA interpreted as references | Closed. `DblpExtract.scala:337–367` preserves literal CDATA and shares the expansion budget with active text. Title, ordinary-field, and author extraction use this path (`:636–650`, `:706–714`, `:811`). |
| Single quotes / closing whitespace | Closed. Attribute extraction supports both quote forms (`DblpExtract.scala:437–460`); author inner markup uses the matching-boundary helper (`:979–980`). Tests retain supplied ORCID and reject an invalid one. |
| Mismatched closing tags accepted | Closed for routed cases. Framing records malformed closes and preserves following-record recovery (`DblpInput.scala:277–307`). Envelope, mapper, and direct parser propagate explicit rejection (`:566`; `PrepJobs.scala:338–348`; `DblpExtract.scala:557–583`). |

An earlier static precheck in this repair pass found a blocking independent-test assertion expecting standalone AuthorMention records from direct parsing. This is closed: `IndependentDblpXmlRepairSpec.scala:117–118` now checks `work.authors`. Envelope byte assertions match string serialization, and shortened synthetic publication keys ensure CDATA overflow fixtures reach the intended title-expansion branch.

Packaging and EMR fixes remain intact. Direct archive inspection confirmed exactly one nested dependency bundle, byte equality with the external bundle, correct main class/catalogue, required core/Scala/uPickle/ujson packages, and zero nested Apache Hadoop or Hadoop-module entries. Generic-option configuration propagation and master-side artifact/config localization remain present.

COMMANDS RUN: Read-only source/log reads, git inspection, searches, SHA-256 checks, and Python standard-library inspection of ZIP archives and retained run paths. No builds, tests, scripts, writes, downloads, or cloud operations executed by reviewer.

TEST RESULTS: Reviewer inspected retained evidence:

- Targeted final log: **4 module + 17 independent tests passed**.
- Full gate: **185 tests passed** — core 96, Hadoop 46, independent 41, build verification 2; zero failed tests. The expected injected child failure was validated by its passing parent test.
- `sbt check` succeeded at **15:22:42**, taking 287 seconds; marker records `success=true`, timestamp `1791404562667`.
- Packaging succeeded at **15:22:43**.
- `HadoopPrepMain` succeeded at **15:23:04**, taking 21 seconds.
- Coordinator observed combined process **exit 0**.

Reviewed execution command:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/tmp/scholarchain-logback-warn.xml sbt -batch check hadoopSubmitJar 'hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain' > docs/agent-runs/phase-04/xml-repair-full-gate.txt 2>&1
```

VALIDATION RESULTS: Both retained runs were fresh (`reused=false`), with `logicalRecordsEqual=true`:

```text
c262d529-8693-4d5a-afe8-e5caf8e3d709
029ab928-55d5-4f9a-894f-33b3f42a9587
```

Each has a completion marker, run manifest, and three author-mention export partitions. Both reported INPUT 193, ACCEPTED 239, REJECTED 0, DUPLICATE 0, CONFLICT 0, EMITTED_PAIR 45; largest team 2, pair expansion 1, block 4. Retained EMR dry-run output confirms localization and no submission; coordinator reported `bash -n` exit 0 and all four sample checksums OK. Coordinator additionally consolidated actual manifests, export counts/representative records and nine job completion markers per run into `xml-repair-sample-evidence.json`.

Final source/test fingerprints remained unchanged throughout the recheck:

```text
DblpInput.scala                 e3ae4c518a611f12096c59b86f85c392321733c9f220aae5e8628e28ec9a6fef
DblpExtract.scala               1f0fedebc42e5377eaa7334444f4e6469de4e88e8cd5a547eaaa56589f05c932
PrepJobs.scala                  0525b1be83d3c68e1454f936e81e8090a399547aae748e72e326ff87b5c752ac
DblpXmlRegressionSpec.scala     c105a4e79ea037f97d73169e29c244444e3f6f59684ef66a32dd3ccdf6c15ebd
IndependentDblpXmlRepairSpec    9db455d1469b84853ff42402ca78df7aa52b613827ecc645b8e582da03b21a9b
```

ASSUMPTIONS: Local execution authorized; EMR authoring only.

RISKS: Review covers routed defects and affected paths, not exhaustive XML correctness. Live EMR/AWS execution remains unrun.

MANUAL ACTION REQUIRED: Human architect reviews the complete diff and records the Phase 4 decision. Coordinator's evidence consolidation is complete.

BLOCKED-ON OWNER: None for the routed repairs.

BLOCKED-ON EVIDENCE: No implementation blocker remains in this review scope.

NEXT GATE: Human Phase 4 acceptance. This review does not ratify control files or authorize Phase 5.

## Fresh comprehensive Phase 4 review — 2026-10-07

VERDICT: **REQUEST-CHANGES**

STATUS: COMPLETE — broad independent review completed. Seven confirmed findings block Phase 4.

OWNER: Independent read-only `code-reviewer`, `/root/phase4_comprehensive_reviewer`, native inherited model. Historical Cursor/Grok assignments were unavailable. Coordinator assembled this returned report.

WORK ORDER: User requested a fresh code review checking whether everything is good. Review the complete tracked and untracked Phase 4 implementation against base `742aa0f209284eed257b8d070a40f8136b0fb543`, the Phase 4 work order, and the authoritative course specification. This review is broader than the preceding four-XML-repair recheck.

FILES CREATED: None by reviewer.

FILES MODIFIED: None by reviewer. Coordinator appended evidence and updated phase status; implementation and human decisions stayed unchanged.

### Blocking findings

Hadoop source paths below are relative to `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/`.

1. **High — Valid source records disappear when normalized intermediate JSON exceeds the source limit. Blocks Phase 4.**

   Locations: `PrepJobs.scala:265`; `HadoopIO.scala:398`, `:437–445`; downstream dispatch at `PrepJobs.scala:487`, `:522`, `:968`.

   J03–J09 use `BoundedLineInputFormat` with the same `maxRecordBytes` used for raw source records. Domain serialization adds identifiers, repeated provenance, and other fields, so accepted source records can produce intermediate lines larger than that limit. The reader replaces these lines with `\u0000OVERSIZE\t...`. Downstream mappers dispatch only recognized kinds and ignore this sentinel. They emit no reject and do not fail the job.

   **Observed artifact evidence:** the three committed DBLP source records occupy **431, 439, and 465 UTF-8 bytes**. Their retained J01 work lines occupy **2392, 2389, and 2521 bytes**. Their venue/enrichment lines occupy only **535–776 bytes**.

   **Static reproducer, not executed:** run the four committed samples with valid `maxRecordBytes=1024`. J01 accepts the DBLP works; later stages discard those work lines while smaller enrichment and reject records continue. A run can therefore complete with missing accepted works. The default 1 MiB sample gate does not exercise this path.

   Required owner: `hadoop-engineer`; supporting `domain-engineer` if a separate intermediate limit requires a config contract; `test-engineer` for independent end-to-end coverage. Provide a bounded intermediate representation/limit and explicit handling of every overflow. Test source-to-domain expansion and reject survival across later jobs.

2. **High — Arbitrary XML split starts can turn comment or CDATA content into fabricated publications. Blocks Phase 4.**

   Locations: `DblpInput.scala:531–535`, `:130–143`.

   The uncompressed reader seeks directly to the split start and initializes a fresh scanner without the preceding XML lexical context. `nextOpen` treats the next `<article...>` as a record even when that text is inside a comment or CDATA section that began before the split.

   **Static reproducer, not executed:** use valid XML containing:

   ```xml
   <dblp><!-- padding
   <article key="conf/review/Fake"><title>Fake</title></article>
   --><article key="conf/review/Real"><title>Real</title></article></dblp>
   ```

   Set a `FileSplit` start inside the comment, before the fake article. The first split skips the comment; the second can emit the fake article. The equivalent CDATA case also loses its literal-text context. This violates complete top-level synchronization and makes output depend on split placement.

   Required owner: `hadoop-engineer`; `test-engineer` for independent actual-InputFormat comparisons between unsplit and adversarially split inputs. Current comment/CDATA tests start at whole-record boundaries; current split tests cover ordinary publication fields.

3. **Medium — Source identifiers and work-reference relationships are discarded during normalization. Blocks Phase 4.**

   Locations: `JsonSources.scala:1194–1212`, `:1243–1264`, `:1057–1075`, `:1014–1029`; core `Records.scala:449–467`.

   OpenAlex institution normalization chooses ROR over the native OpenAlex institution ID and retains no separate native-ID observation. ORCID activity normalization keeps only the first DOI; it has no output field for other declared work identifiers or their relationships.

   **Observed sample/artifact evidence:**

   - The committed OpenAlex sample contains `https://openalex.org/I79516672` with ROR `01x8rc503`. The emitted institution/link records preserve ROR, but `I79516672` is absent from the retained export.
   - The committed ORCID sample contains self identifiers `24870415` and `7279939` under `other-id`, plus ISBN/ISSN references with `part-of` relationships. The two self identifiers and `external-id-relationship` are absent from the retained export.
   - `externalDoi` uses `.find` and never examines relationship metadata or additional identifiers.

   This contradicts required source-specific identifier and ORCID work-reference preservation. Observations differing only in a discarded identifier can normalize identically.

   Required owners: `domain-engineer` for additive evidence contracts; `hadoop-engineer` for normalization/indexing; `test-engineer` for independent retention and conflict coverage. Preserve observed namespaces, values, and relationships separately from preferred IDs.

4. **Medium — Self-closing author elements disappear and shift following author positions. Blocks Phase 4.**

   Locations: `DblpExtract.scala:286`, `:783–785`, `:976–977`.

   `DblpXml.elements` skips self-closing elements. Because author extraction uses that helper, `<author/>` disappears before the blank-author check runs.

   **Static reproducer, not executed:**

   ```xml
   <article key="conf/review/A"><author/><author>Ada</author><title>T</title></article>
   ```

   The record can be accepted with Ada at ordinal 1. The source's first author position is silently lost. A paired empty `<author></author>` instead reaches an explicit missing-field reject.

   Required owner: `hadoop-engineer`; `test-engineer` for independent coverage. Treat self-closing authors consistently with empty paired authors, without renumbering an incomplete source team as complete.

5. **Medium — Reuse accepts damaged export files as completed output. Blocks Phase 4.**

   Locations: `PrepSupport.scala:516–537`, `:615–629`; `HadoopPrepPipeline.scala:74–75`.

   Completion metadata records partition directories rather than export file identities. `partitionsPresent` accepts any nonmetadata file in each directory. It checks neither recorded lengths/content nor the complete expected file set.

   **Static reproducer, not executed:** complete a run, truncate an export part file to zero bytes while leaving the marker and manifest unchanged, then submit the identical request. The partition check still succeeds and `execute` returns `reused=true`. Lost rows are trusted as complete. Current reuse coverage checks an unchanged run and whole missing partitions, not changed part-file contents.

   Required owner: `hadoop-engineer`; `test-engineer` for independent corruption/missing-file regressions. Bind completion to expected export artifacts and verify that binding before reuse.

6. **Medium — Caller Hadoop filesystem settings do not reach driver metadata operations. Blocks Phase 4.**

   Locations: `HadoopPrepPipeline.scala:64`, `:166`; `HadoopIO.scala:63–70`; `PrepSupport.scala:488`, `:509`, `:543`, `:686`; `HadoopPrepMain.scala:201`.

   `GenericOptionsParser` creates the caller configuration and `Request.hadoopConf` reaches job configuration at `HadoopPrepPipeline.scala:159`. However, filesystem validation, input binding, output claims, manifests, statistics, reuse, and export comparison construct fresh configurations through `FsIO.configuration()`.

   **Static reproducer, not executed:** in a fresh test process, set `fs.s3.impl` to the existing `MemoryS3FileSystem` fixture on `Request.hadoopConf`, without `FsIO.withSettings`, and request an S3 output root. Filesystem validation uses another configuration and fails before job launch. Caller `-D` filesystem/endpoint settings are likewise unavailable to these driver operations. The current remote test uses the separate thread-local test hook, masking this omission.

   Required owner: `hadoop-engineer`; `test-engineer` for independent configuration propagation coverage. Pass the effective immutable Hadoop configuration through driver and task filesystem helpers.

7. **Medium — The smoke script does not enforce a smoke execution ceiling. Blocks Phase 4's script requirement.**

   Locations: `scripts/phase4-emr-smoke.sh:245–261`; `HadoopPrepConfigLoader.scala:59–66`.

   The generated cluster command localizes the supplied config and launches it directly. It checks no upper sample, reducer, block, or pair limits. The loader requires positive values but accepts operationally enormous values. A config requesting a billion reducers/sample records is therefore accepted by this script's validation path.

   This is a static requirement gap against the explicit bounded-smoke work order. The nine-job graph and `--once` bound pipeline repetitions; they do not establish a smoke resource ceiling.

   Required owner: `infra-engineer`, coordinating any shared validation contract with `domain-engineer`/`hadoop-engineer`. Validate an explicit smoke budget after remote config localization and before launching Hadoop. Add local rejection coverage. No AWS execution is needed for that repair.

### Evidence assessment

TEST RESULTS: No tests or builds executed by this reviewer. The retained full-gate log reports **185 passing tests**: core 96, Hadoop 46, independent 41, build verification 2. The nested injected failure is the expected passing failure-path probe.

VALIDATION RESULTS:

- Both retained standalone runs are fresh (`reused=false`) and report `logicalRecordsEqual=true`.
- Read-only inspection independently confirmed nine job `_SUCCESS` outputs per run.
- Actual nonempty export-record counts match the compact evidence for both runs: 5 works, 10 mentions, 5 teams, 10 authorships, 5 pairs, 40 candidates, and the recorded enrichment/profile/activity counts.
- All four sample SHA-256 hashes match the acquisition index. No tracked sample changes appear against the base.
- Submit archive inspection confirmed exactly one nested dependency bundle, byte equality with the external bundle, the main class and entity catalogue, required core/Scala/uPickle/ujson contents, and no nested Hadoop or Hadoop-module classes.
- Module and dataset entity catalogues match byte-for-byte.
- The previously routed four XML repairs remain present. These findings concern adjacent or broader behavior; they do not reverse those specific closures.

Passing evidence establishes the retained bounded sample behavior, not correctness for the new triggers. Fresh directory/run-ID assertions prevent the independent integration suite from merely reusing old results.

Nonblocking documentation drift: `modules/hadoop/README.md:44` describes `identifier-index`, `enrichment-link`, and `text-document` output kinds, while current `Kinds` and actual exports use `index`, `enrichment`, and `text`. Required owner: `hadoop-engineer`.

### Review provenance and limitations

COMMANDS RUN: Read-only shell inspection through the review tool transcript, including:

```sh
pwd && git status --short && cat AGENTS.md && cat docs/agents.md && cat docs/agent-runs/README.md && cat docs/agent-runs/phase-04/prompt.md
rg --files modules/core modules/hadoop tests project datasets/schemas/dblp docs/agent-runs/phase-04 scripts | sort
git diff --stat 742aa0f209284eed257b8d070a40f8136b0fb543
git diff --name-only 742aa0f209284eed257b8d070a40f8136b0fb543 -- datasets/samples
tail -n 90 docs/agent-runs/phase-04/xml-repair-full-gate.txt
rg -n '^## Phase 4' /tmp/scholarchain-phase4-course-readme.md
sed -n '1107,1145p' /tmp/scholarchain-phase4-course-readme.md
sed -n '2120,2270p' /tmp/scholarchain-phase4-course-readme.md
```

Additional exact `cat`, `sed`, `nl`, `rg`, and read-only `git diff` invocations are retained in this review's tool transcript. They inspect all nine Hadoop production files, additive/modified core contracts, build/packaging files, module and independent tests, dataset metadata/catalogues, the EMR script, and phase reports.

Bounded Python standard-library inspection, also retained exactly in the transcript, read only the known samples, two named retained run directories, course snapshot, and known packaging archives. It calculated hashes, source/intermediate sizes, export counts, identifier retention, and ZIP contents. An initial count comparison included empty top-level output files; a follow-up excluded empty files and confirmed both evidence counts.

Course provenance: coordinator-provided complete public [course README](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md) snapshot `/tmp/scholarchain-phase4-course-readme.md`, fetched October 7, 2026. Independently calculated SHA-256:

```text
6a0eddaddbb91435198ec868699ca99aec22ae8ee5ff515b6f7b34f18e362695
```

Coordinator fetched that snapshot with:

```sh
curl --fail --location --max-time 30 https://raw.githubusercontent.com/0x1DOCD00D/ScholarChain/main/README.md -o /tmp/scholarchain-phase4-course-readme.md
```

Initial sandbox network attempt failed DNS resolution; approved retry exited 0. Coordinator also compared fingerprints for 90 source/contract files before and after review: none changed. `git diff --check` exited 0. No new gate or source execution is claimed.

ASSUMPTIONS: LocalJobRunner authorized. EMR authoring authorized; live submission outside this review. Final identity decisions belong to later phases.

RISKS: Static reproducers were not executed. No live cluster compatibility claim is made. Reviewer performed no network/cloud actions, builds, scripts, subagents, or secret/credential reads. Broad inspection is not exhaustive proof of correctness.

MANUAL ACTION REQUIRED: Route all findings together to their owners, add independent feature coverage, rerun `sbt check` and two fresh equivalent sample runs, retain repaired packaging/script evidence, then obtain a fresh independent review.

BLOCKED-ON OWNER: `hadoop-engineer`, `domain-engineer`, `infra-engineer`; supporting `test-engineer`.

BLOCKED-ON EVIDENCE: Seven confirmed implementation/requirement findings above.

NEXT GATE: Owner repairs and observed gates, followed by independent review. Human Phase 4 acceptance remains pending; this report does not authorize Phase 5.

## Fresh recheck after the seven-blocker repairs — 2026-10-07

VERDICT: **REQUEST-CHANGES**

STATUS: COMPLETE.

OWNER: Independent read-only `code-reviewer`, `/root/phase4_seven_blocker_reviewer`, native inherited model. Historical Cursor model assignments were unavailable. Coordinator assembled the returned report.

WORK ORDER: User requested another check whether everything is good. Recheck the seven findings from the preceding comprehensive review and broadly inspect the complete tracked/untracked Phase 4 implementation against base `742aa0f209284eed257b8d070a40f8136b0fb543`, the Phase 4 prompt, and the supplied course README snapshot.

FILES CREATED: None by reviewer.

FILES MODIFIED: None by reviewer. Coordinator retained evidence and appended reports. No implementation or human decisions were changed during this recheck.

Original repair mechanisms are present and the fresh deterministic gate passes. Two blocking categories remain: overflow lineage and discarded bibliographic source evidence.

### Blocking findings

**1. Medium — Intermediate overflow rejects lose source, snapshot, and a unique source locator. Blocks Phase 4.**

Locations:

- `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/PrepSupport.scala:248–278`
- `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/HadoopIO.scala:443–450`
- `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/PrepJobs.scala:515–517`, `:570–572`, `:1058–1066`

The earlier silent-drop defect is repaired: intermediate overflow produces an `OVERSIZE_RECORD` reject. However, `OverflowLines.record` and `emit` explicitly supply `source=None` and `datasetSnapshot=None`. Mapper callers supply only the intermediate byte offset as locator. The sentinel contains a short preview rather than source metadata or its containing file path.

**Static reproducer, not executed:** set source `maxRecordBytes=1048576`; supply a valid DBLP article with a 600,000-character ordinary title. Its XML fits the limit, while the normalized work repeats the title in `title` and `normalizedTitle`, exceeding the 1 MiB intermediate cap. Its overflow rejects have null source/snapshot and a bare offset. The same offset can occur in multiple intermediate part files. Because provenance follows the long title in the JSON, the bounded preview cannot recover the snapshot. The committed sample config's `maxXmlEntityExpansion=1048576` also permits this ordinary title.

This violates the prompt's requirement that rejects retain source locator and snapshot, and prevents reliably tracing overflow to the rejected observation. The new module overflow test at `HadoopPrepReviewSpec.scala:568` injects a malformed oversized `work` line and checks only that a reason code survives; it does not check lineage for an expanded valid source record.

Required owner: `hadoop-engineer`; supporting `test-engineer`. Preserve bounded source identity and file location before draining, then test valid source-to-domain expansion through final reject export.

**2. Medium — Bibliographic normalization still discards declared source links and identifier disagreements. Blocks Phase 4.**

Two concrete cases share the missing source-evidence preservation requirement.

**OpenAlex DOI disagreement**

Locations:

- `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/JsonSources.scala:152–171`, `:324–340`
- Downstream duplicate comparison: `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/PrepJobs.scala:672–687`

A valid top-level `doi` prevents examination of `ids.doi`. The second value is neither retained nor validated.

**Static reproducer, not executed:**

```json
{"id":"W2741800001","title":"T","doi":"10.1000/a","ids":{"doi":"10.1000/b"}}
```

Change only `ids.doi` to `10.1000/c`. Both observations normalize identically. Together, J04 classifies them as identical duplicates instead of preserving differing declared evidence. A malformed `ids.doi` is likewise unnoticed when the top-level DOI is valid. The prompt requires preserving work identifiers and disagreements; retaining the native work key does not preserve this second DOI observation.

**DBLP electronic-edition links**

Locations:

- `modules/hadoop/src/main/scala/edu/uic/cs441/scholarchain/hadoop/DblpExtract.scala:720–725`, `:758`, `:863–904`

The extractor reads `ee` values only to select the first DOI and first arXiv ID. `externalUrl` comes exclusively from the first `url`. Ordinary electronic-edition links are never emitted.

**Static reproducer, not executed:**

```xml
<article key="conf/review/Links">
  <author>Ada</author><title>T</title>
  <ee>https://publisher.example/paper</ee>
  <ee>https://repository.example/paper</ee>
</article>
```

The accepted work has `externalUrl=None`; neither supplied link survives in any emitted record. Phase 4 extraction requirements include `ee` links and URLs.

Required owners: `hadoop-engineer`; `domain-engineer` if an additive shared evidence contract is needed; supporting `test-engineer`. Preserve declared links and identifier observations separately from preferred IDs. Add independent retention and conflicting-observation tests.

### Seven-finding resolution matrix

| Prior blocker | Assessment | Evidence |
| --- | --- | --- |
| Intermediate oversize silent loss | **Partial closure.** Explicit rejects now survive; finding 1 retains the lineage blocker. | Intermediate caps and overflow handling in J03–J09; independent 1024-byte source-cap test |
| Arbitrary XML split comment/CDATA injection | **Resolved for the cited correctness defect.** | `DblpInput.scala:135–145`, `:550–559` replay preceding lexical context; actual split tests cover comments, CDATA, and processing instructions |
| OpenAlex institution and ORCID work-reference loss | **Resolved for the cited fields.** Broader preservation still has finding 2. | Additive `observedSourceIds` and `workReferences`; institution indexing; independent committed-sample retention assertions |
| Self-closing author positions | **Resolved.** | `DblpExtract.scala:286–300` retains self-closing elements; blank author rejects the whole observation |
| Corrupted export reuse | **Resolved for cited corruption.** | `PrepSupport.scala:680–687`, `:762–787` compare complete export path/length/SHA-256 sets; module/independent truncation tests |
| Caller Hadoop filesystem configuration | **Resolved in inspected production path.** | `HadoopPrepPipeline.scala:64` copies request configuration; it flows through driver metadata, jobs and result reads; independent configuration test |
| Bounded EMR smoke ceilings | **Resolved in authored validation. AWS remains unverified.** | Seven inclusive ceilings checked locally and after localization before launch; observed syntax/dry-run success |

### Nonblocking notes

- Every uncompressed XML split now scans from byte zero. `DblpInput.scala:550–559` and `firstAtOrAfter` imply cumulative prefix I/O approximately `N × splits / 2` for evenly sized splits. This is a substantial large-corpus performance limitation, not a reversal of lexical correctness repair. `DblpInput.scala:13` still inaccurately promises only one-record overlap. Owner: `hadoop-engineer`.
- `modules/hadoop/README.md:10` and `HadoopPrepMain.scala:7` still advertise a thin-JAR launch. The verified packaging contract requires the submit JAR with `lib/<bundle>`. Owner: `hadoop-engineer`.

### Observed gates and artifact evidence

TEST RESULTS: Reviewer executed no tests/builds. Read-only inspection of `/tmp/scholarchain-check10.log` confirms **202 passing tests**: core 97, Hadoop 55, independent 48, build verification 2; zero failures. Gate stdout ends successfully October 7, 2026, 18:14:23, 340 seconds. Nested injected failure is the expected failure-path probe. Generated marker: `success=true`, timestamp `1791414863422`. Coordinator retained sbt status/test lines as `seven-blocker-recheck-test-summary.txt`, with full-log hash and JUnit details in `seven-blocker-recheck-evidence.json`; these prior test executions were not rerun during this review.

VALIDATION RESULTS:

- `/tmp/scholarchain-sample10.log` reports two fresh runs, both `reused=false`, `logicalRecordsEqual=true`: `e9fd8b3b-2af3-4b65-909a-be0c8e4dee6b` and `335c5a33-489b-4056-8ece-b3d8863eaef9`. Sample stdout ends successfully 18:14:58, 21 seconds; copied to `seven-blocker-recheck-sample.txt`.
- Reviewer independently confirmed eight intermediate job success files plus export success in each run.
- Matching export counts: 5 works, 10 mentions, 5 teams, 10 authorships, 5 pairs, 40 candidates, 27 identifier entries, 18 graph edges, 10 enrichment links, 5 venues, 2 institutions, 3 topics, 1 ORCID profile, 16 activities. Each run reports INPUT 195, ACCEPTED 242, REJECTED 0, EMITTED_PAIR 45; counters/manifests retained in `seven-blocker-recheck-evidence.json`.
- All four sample hashes match acquisition metadata; no tracked sample changes against base. Dataset/module entity catalogues match byte-for-byte.
- Coordinator rebuilt previously stale generated archives. Packaging process exited 0; success 20:54:57, one second. Reviewer inspected current archive: one lib bundle equal to external bytes, main/catalogue present, current Institution/OrcidWorkReference/OrcidActivityRecord and Scala/uPickle/ujson classes, no Hadoop/Hadoop-module classes in bundle. Output retained in `seven-blocker-recheck-packaging.txt`.
- Coordinator observed `bash -n` and remote-config placeholder dry-run exit 0. Reviewer inspected retained dry-run; ceiling check precedes Hadoop launch. Output: `seven-blocker-recheck-emr-dry-run.txt`. No AWS invocation.
- Coordinator compared 91 source/contract fingerprints before and after review: unchanged. No source timestamp was newer than the gate marker. `git diff --check` exit 0.
- Passing evidence does not exercise the static reproducers above.

COMMANDS RUN: Reviewer read-only `pwd`, `git status --short`, `git diff`, `cat`, `sed`, `nl`, `wc`, and `rg`, recorded exactly in the tool transcript. Evidence-summary commands included:

```sh
rg -n '^\[info\] (Total number of tests run|Tests: succeeded|All tests passed)|^\[success\]' /tmp/scholarchain-check10.log
rg -n 'runDirectory=|runId=|reused=|counters=|logicalRecordsEqual=|Total time:' /tmp/scholarchain-sample10.log
git diff --name-only 742aa0f209284eed257b8d070a40f8136b0fb543 -- datasets/samples
```

Two bounded, read-only Python standard-library inspections calculated sample/course hashes, catalogue equality, named-run job/export counts, and ZIP contents; exact programs are in the review tool transcript. No source programs/repository scripts/builds/tests executed by reviewer.

Coordinator additionally executed:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch hadoopSubmitJar > docs/agent-runs/phase-04/seven-blocker-recheck-packaging.txt 2>&1
bash -n scripts/phase4-emr-smoke.sh
bash scripts/phase4-emr-smoke.sh --dry-run --cluster-id j-PHASE4-PLACEHOLDER --region us-east-1 --input-prefix s3://phase4-placeholder/input --output-prefix s3://phase4-placeholder/output --jar s3://phase4-placeholder/artifacts/hadoop-submit_3-0.1.0-SNAPSHOT.jar --libjars s3://phase4-placeholder/artifacts/hadoop-dependency-bundle_3-0.1.0-SNAPSHOT.jar --config s3://phase4-placeholder/artifacts/prep.json > docs/agent-runs/phase-04/seven-blocker-recheck-emr-dry-run.txt 2>&1
git diff --check
```

Coordinator inspected and retained existing stdout/JUnit/run artifacts with read-only Python extraction; original full test/sample shell environment and process exit values were not observed in this turn. Their terminal success lines and generated evidence were observed. An initial broad temporary-file inventory touched an unrelated sandbox-protected daemon entry and was repeated filtering known ScholarChain evidence names first; no daemon contents were read.

Course provenance: supplied complete [course README](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md) snapshot `/tmp/scholarchain-phase4-course-readme.md`; independently confirmed SHA-256 `6a0eddaddbb91435198ec868699ca99aec22ae8ee5ff515b6f7b34f18e362695`.

ASSUMPTIONS: LocalJobRunner authorized; final identity decisions remain outside Phase 4.

RISKS: Static reproducers unexecuted. Broad review covers sources/contracts/tests/resources/build/datasets/smoke authoring, not exhaustive proof. No reviewer network/cloud actions, secret reads, edits, commits, or subagents. AWS remains unrun.

MANUAL ACTION REQUIRED: Route both remaining categories to owners, add independent feature coverage, rerun relevant gates, and obtain fresh independent review.

BLOCKED-ON OWNER: `hadoop-engineer`, supporting `domain-engineer` and `test-engineer`.

BLOCKED-ON EVIDENCE: Findings 1 and 2 above.

NEXT GATE: Repairs, observed verification and independent review. Human Phase 4 acceptance pending; no Phase 5 authorization.


## Evidence-preservation repair artifact recheck — 2026-10-07

VERDICT: **REQUEST-CHANGES**
STATUS: COMPLETE for the pre-packaging-fix tree.
OWNER: Independent read-only `/root/phase4_seven_blocker_reviewer`, native inherited model, fresh inspection in reused context due native thread limit. Coordinator assembled report.
WORK ORDER: Recheck two latest source-evidence categories and all earlier cited closures, including final artifact content.
FILES CREATED / MODIFIED: None by reviewer.

The two source-evidence categories at review.md:657 are closed for the cited defects. Bounded lineage precedes oversized JSON; rejects retain source, snapshot and qualified unique file/offset/native reference. OpenAlex validates/retains both DOI roles; DBLP preserves all nonblank decoded ee/url links, repetitions and within-role order. Adjacent export framing and overflow logical-comparison regressions were independently identified and repaired. Exact run-shaped source values remain literal; v3 transformation binds reuse identity. Seven earlier cited mechanisms remain repaired.

### High — Cached dependency bundle retains obsolete core classes. Blocks Phase4.

Required owner: build-engineer. Original locations project/ScholarChainBuild.scala:100,112,116,155. Copying cached bundle first and skipping duplicate names keeps old core bytes when assembly is up to date; namespace-presence verification misses content mismatch.

Observed final artifacts: current compiled/core-JAR WorkRecord.class SHA2562d4499e38b59488b4bb47aa6b12a682376d0fdad6887624e0e15c0ede4c1125e,14386bytes, has observedIdentifiers/sourceLinks. External dependency and embedded submit bundle contain SHA256366dace088ff997fb0b62cd3d88da0dbf10d3b6e7d50cca7c595720c58eca485,12642bytes, missing fields. Hadoop compiled against the new constructor can fail distributed linkage/serialization. Local classpath execution does not validate this submit artifact.

Required repair: current core entries own all collisions; obsolete core classes/owned resources removed; verify current artifact bytes. Do not merely delete generated archives. Coordinator routed a separate build-engineer work order to the existing implementation worker; review stays read-only.

TEST RESULTS: Pre-packaging gate had218passes (core99,Hadoop64,independent53,build2), zero failures/errors/skips, check21:59:01/397sec; packaging task21:59:02/1sec reported success but missed stale bytes. Two fresh samples21:59:22/21sec report reused=false/logicalRecordsEqual=true, nine successful job outputs each. IDs5713df68-5b95-4082-9077-1975681ba357 and82bab667-6068-4f29-9921-09364f48933f.
VALIDATION RESULTS: Sample exports/markers/counters match;34parts each match lengths/SHA. Reviewer54source/contract SHA+mtime fingerprints unchanged through that gate; coordinator90-path snapshot unchanged. Exactly one nestedbundle matchesexternal, but neither matchescurrentcore. Raw historical evidence now named evidence-repair-pre-packaging-gate.txt, evidence-repair-pre-packaging-artifacts.json and evidence-repair-pre-packaging-summary.txt. Two deliberate interrupted attempts remain separately unsuccessful.
COMMANDS RUN: Read-only rg/sed/nl/gitstatus/gitdiff--check and bounded Python source/XML/ZIP/artifact inspection. Reviewer ran no repository programs/builds/tests/cloud/subagents and edited no files. Exact commands retained in tool transcript; coordinator gate commands/results in test-report.md.
ASSUMPTIONS: Native role/model deviation disclosed; no constitutional ratification inferred.
RISKS: XML prefix replay performance remains documented; AWS/large-corpus/deployed execution unverified. Historical untracked file:/ stats artifacts untouched.
MANUAL ACTION REQUIRED: Repair packaging, obtain independent artifact recheck, then human Phase4 decision.
BLOCKED-ON OWNER: Build-engineer.
BLOCKED-ON EVIDENCE: Current core byte equality in rebuilt submit/dependency archive.
NEXT GATE: Post-repair frozen full gate and final independent verdict. No phase acceptance or Phase5 authorization.


## Final source-evidence and cached-core repair recheck — 2026-10-07

VERDICT: **APPROVE**

STATUS: COMPLETE.
OWNER: Independent read-only code-reviewer `/root/phase4_seven_blocker_reviewer`, inherited native model. Fresh source/artifact inspection used reused review context because new native threads were unavailable. Historical Cursor model assignments unavailable. Coordinator assembled returned report.
WORK ORDER: Recheck two source-evidence blocker categories, adjacent regressions, prior seven closures and observed cached-bundle defect against current frozen Phase4 implementation.
FILES CREATED / MODIFIED: None by reviewer.
BLOCKING FINDINGS: None remaining in reviewed scope.

Source-evidence and packaging repairs are complete. Approval covers inspected local implementation and artifacts; human Phase4 acceptance is a separate gate.

| Finding | Resolution and evidence |
| --- | --- |
| Intermediate overflow lineage | Closed. PrepSupport.scala:205,232,250,288 and HadoopIO.scala:451 retain bounded source/snapshot/native metadata and qualified containing-file identity before draining large payloads. HadoopPrepPipeline.scala:60 rejects excessive snapshot metadata before launch. Feature/independent tests cover valid source expansion, multiple files and final reject export. |
| Discarded bibliographic evidence | Closed. JsonSources.scala:152,356 preserve/validate both raw OpenAlex DOI roles; DblpExtract.scala:909 retains every decoded nonblank ee/url value with field and within-field order, including repetitions. Records.scala:61 defaulted additive fields preserve old wire compatibility; DomainValidation.scala:65 validates source observations. Independent retention/malformed-secondary/conflict tests pass. |
| Missing-reference export framing | Closed. PrepJobs.scala:1185 strips private framing before final output kind. ActualJ09 test checks normal reject partition, schema failure and missing reference. |
| Fresh overflow determinism | Closed. PrepSupport.scala:274,308,1010 exclude only generated processing metadata and preserve source/snapshot/native identity/genuine root/part/offset. Exact run-shaped source values remain literal. Two fresh overflow pipelines compare equal while source-evidence perturbations compare unequal. v3 transformation binds reuse identity at PrepSupport.scala:856. |
| Cached stale core bundle | Closed. HadoopBundleMerge.scala:37,57,76,103,115,119 replaces cached core, removes deleted owned entries and verifies namespace/size/SHA/inventory before replacement. Two feature tests exercise cached successive versions, deleted class/resource removal and stale-content rejection. |

| Prior blocker | Current assessment |
| --- | --- |
| Intermediate oversize silent loss | Closed, including lineage gap |
| Arbitrary split comment/CDATA injection | Closed for cited correctness defect |
| OpenAlex institution / ORCID work references | Closed for cited identifiers and relationships |
| Self-closing author positions | Closed |
| Corrupted export reuse | Closed for cited corruption |
| Caller Hadoop filesystem configuration | Closed in inspected production paths |
| Bounded EMR smoke ceilings | Closed in authored validation; AWS unverified |

TEST RESULTS: Reviewer executed no builds/tests. Independent inspection of current stdout/JUnit confirms **220 passing tests**: core99,Hadoop64,independent53,build4; zero failures/errors/skips. Frozencheck22:19:10/399sec; packaging22:19:11/1sec; freshsamples22:19:32/21sec. Coordinator command exit0. Expected nested format-failure probe is successful failure-path coverage.

VALIDATION RESULTS:

- Two fresh runs reused=false and logicalRecordsEqual=true: fda6168a-d4e6-4c20-bf73-42a1c3724f7f and ccd26111-d26d-4783-bc0f-e7106e4e617d.
- Independently verified9jobsuccess outputs per run, completion metadata and all34 export-part lengths/SHA per run; markers identify hadoop-prep-j01-j09-v3-stable-overflow-lineage.
- Matching export counts:5works,10mentions,5teams,10authorships,5pairs,40candidates,27index,18edges,10enrichment,5venues,2institutions,3topics,1ORCIDprofile,16activities. Each reportsINPUT195,ACCEPTED242,REJECTED0,EMITTED_PAIR45.
- Independently compared all478current core-JAR entries byte-for-byte with externalbundle: zero mismatches, zero extra core entries, exact ownershipinventory. Submit embeds exactly1bundle byte-identical to external.
- WorkRecord.class14386bytes, SHA2562d4499e38b59488b4bb47aa6b12a682376d0fdad6887624e0e15c0ede4c1125e with both evidence fields present. Bundlecore474,Scala3549,upickle346,ujson107; Hadoopmodule0/clusterHadoop0.
- Both cached build regression tests and two consecutive cached packaging invocations pass.
- Reviewer60source/contract SHA+mtime fingerprints unchanged during finalgate; coordinator92-path snapshot unchanged. Final logSHA matches artifact evidence. git diff --check passed.
- Interrupted attempts and prior218-pass/stale-package gate remain historical and are excluded from final completion evidence.

COMMANDS RUN: Reviewer read-only git/rg/sed/nl and bounded Python standard-library source/hash/JUnit/manifest/export/ZIP inspection. Exact invocations in tool transcript. No repository programs/builds/tests/cloud/subagents or edits by reviewer. Coordinator command:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml sbt -batch check hadoopSubmitJar 'hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain' > docs/agent-runs/phase-04/evidence-repair-full-gate.txt 2>&1
```

EVIDENCE: evidence-repair-full-gate.txt, evidence-repair-artifacts.json, evidence-repair-gate-summary.txt, evidence-repair-packaging-targeted.txt and evidence-repair-packaging-byte-check.json.
ASSUMPTIONS / RISKS: XMLsplitprefix replay keeps documented large-corpus I/O cost. Large-corpus performance, AWS/deployed execution unverified. Historical untracked file:/ stats files predate repairs and were untouched. No cross-tool equivalence, instructor approval, constitutional ratification or human acceptance inferred.
MANUAL ACTION REQUIRED: Human Phase4 review/decision.
BLOCKED-ON OWNER / EVIDENCE: None for reviewed implementation.
NEXT GATE: Human Phase4 acceptance; no Phase5 authorization.

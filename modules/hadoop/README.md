# Hadoop preparation

Nine MapReduce jobs turn DBLP XML and OpenAlex, Crossref, and ORCID JSONL into domain records. The driver submits jobs and writes `run-manifest.json` and `_SCHOLARCHAIN_COMPLETE` only after every job succeeds. It does not buffer the export. `executionMode` `local` may set `mapreduce.framework.name` to `local`. `cluster` sets `yarn` and does not set LocalJobRunner.

`outputRoot` comes from `HadoopPrepConfigLoader`, then from CLI overrides. `HadoopPrepPipeline.execute` validates that effective config before any output claim or job launch. A failed config does not launch a job. The committed sample uses `reducerCount` 1, `compressionCodec` `none`, and `executionMode` `local`.

Cluster launch, after the build engineer packages the jars, is:

```text
hadoop jar <submit-jar> edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain -libjars <bundle>
```

The submit JAR embeds the dependency bundle under `lib/` for driver bootstrap; `-libjars` distributes the external matching bundle to workers. Uncompressed XML splits replay the preceding file prefix to recover comment, CDATA, and processing-instruction context. For evenly sized splits this can cost approximately half the file length per split in aggregate; gzip remains one split.

## Job graph

```text
J01 DblpExtract ─────────────┐
                             ├─> J03 ExactIdentifierIndex ─> J04 ExactIdentifierJoin
J02 SourceNormalize ─────────┘                                     │
                                                                   ├─> J05 BlockingKey ─> J06 CandidateJoin
                                                                   ├─> J07 PublicationTeam
                                                                   ├─> J08 CoauthorPairExpansion
                                                                   └─> J09 GraphCandidateExport
```

J04 compares complete input observations. One observation that also emits an institution, venue, topic, or a repeated affiliation is not a conflict. Two identical copies keep one survivor. Two observations with the same source, source record, and snapshot whose work or enrichment differs drop both sides. J05 fans bibliographic block keys from that survivor. J06 emits `MatchCandidate` rows for pairs that share a block. Fallback keys do not pair unrelated records. J09 reads the surviving and derived outputs.

Every job uses Hadoop's default `HashPartitioner`. None of the jobs set a combiner: block size, observation identity, and pair expansion are not safe partial aggregates. `reducerCount` is the configured reduce-task count. Sample compression is `none`. When `intermediateCompressionEnabled` is true, J01–J08 set `FileOutputFormat` compression to the configured codec and later jobs read those compressed part files through the input format. Shuffle compression is left off. J09 export stays uncompressed.

| Job | Reducer | Rejects | Output prefix | Fixture |
| --- | --- | --- | --- | --- |
| J01 DblpExtract | `PassReducer` | malformed, unterminated, unsafe entity, oversize, unknown element, sample cap | `intermediate/j01` | `datasets/samples/dblp/linked-records.xml` |
| J02 SourceNormalize | `PassReducer` | malformed JSON, invalid identifier, oversize line, sparse abstract, sample cap | `intermediate/j02` | `datasets/samples/{openalex,crossref,orcid}/*.jsonl` |
| J03 ExactIdentifierIndex | `PassReducer` | schema failure on an index row | `intermediate/j03` | J01 and J02 output |
| J04 ExactIdentifierJoin | `JoinReducer` | duplicate observation, conflicting observation, oversize group | `intermediate/j04` | J01–J03 output |
| J05 BlockingKey | `BlockReducer` | `OVERSIZE_BLOCK`, `OVERSIZE_CANDIDATE_PAIRS` | `intermediate/j05` | J04 bibliography rows |
| J06 CandidateJoin | `CandidateReducer` | same oversize codes; fallback keys emit nothing | `intermediate/j06` | J05 block members |
| J07 PublicationTeam | `PassReducer` | `OVERSIZE_TEAM` is emitted by the mapper | `intermediate/j07` | J04 works |
| J08 CoauthorPairExpansion | `PassReducer` | a team above `maxAuthorTeamSize` yields no pairs and one `OVERSIZE_TEAM` reject (stage `COAUTHOR_PAIR`, work id and team size in the excerpt) counted as `OVERSIZE_TEAM_PAIR_STEP`; an expansion above the pair limit yields `OVERSIZE_CANDIDATE_PAIRS` | `intermediate/j08` | J04 works |
| J09 GraphCandidateExport | `ExportReducer` | unresolved `abstractTextRef` | `export/snapshot=<snapshot>/run=<uuid>/<kind>/` | J04–J08 output |

Map output keys are record kinds (`work`, `index`, `reject`, …), with an observation-instance suffix on J01–J03 lines. J04 groups by `source`, source record, and snapshot. J05 and J06 group by the block key (`exact:`, `name:`, `initial:`, `title-year:`, `venue:`, `affiliation:`, `coauthor:`, or `fallback:`). J07 and J08 group by record kind (`team`, `authorship`, `pair`, `reject`). J09 groups by snapshot or text-reference id. Values are domain JSON.

J09 kind directories include `work`, `author-mention`, `institution`, `mention-affiliation`, `venue`, `enrichment`, `text`, `orcid-profile`, `orcid-activity`, `index`, `match-candidate`, `graph-edge`, and `reject`. `author-mention` is the `AuthorMention` JSON contract, not only the nested `authors` array. `index` is an `IdentifierIndexEntry` with top-level `datasetSnapshot`. Bibliography rows stay intermediate and are not exported.

`maxLocalSampleRecords` is one launch-level bound over the inputs in order DBLP, OpenAlex, Crossref, ORCID. The same cap and the same file accept the same prefix under one split or many. Excess input is `OVERSIZE_RECORD` with diagnostic `maxLocalSampleRecords`. `maxRecordBytes` is applied before a JSON line becomes a `String`; the excess is drained to the next newline.

Intermediate keys carry a bounded private lineage prefix before domain JSON. J03–J09 remove the prefix when interpreting record kinds and retain its source/snapshot and qualified part-file offset when an oversized line becomes a reject. Record identities beyond the fixed metadata field budget carry a SHA-256 reference. Snapshot identifiers over 1024 UTF-8 bytes fail validation before a job launches; they are never truncated. An envelope exceeding the fixed metadata budget fails rather than fabricating lineage. Legacy injected lines without this prefix still get a qualified file/offset reject, with source identity absent when it is unavailable.

OpenAlex work records retain both declared DOI fields in `observedIdentifiers` (`openalex.doi` and `openalex.ids.doi`) using their raw values; both are validated and a disagreement does not replace the preferred DOI. DBLP work `sourceLinks` preserves every nonblank decoded `ee` and `url`, including repetitions, grouped by field and preserving order within each field.

## Blocking

Candidates use `featurePolicyVersion` `prep-features-v2`. Features are the closed sorted names in `PreparationFeatures.names`. `exact_shared_identifier` is 1 only for an `exact:` block. `same_work_id` is 1 only when both sides already have the same validated work id. It is not a merge and not a `MatchDecision`. The same title, year, and authors can produce a candidate without a shared DOI. Block size and pair count use the existing oversize reject codes. A block over the limit is rejected whole.

## Provenance

`datasets/acquisition-index.v1.json` is authoritative for the four committed samples:

| Source | Snapshot id | Retrieval date |
| --- | --- | --- |
| dblp | `dblp-2026-10-03` | `2026-10-05` |
| openalex | `openalex-rest-2026-10-05` | `2026-10-05` |
| crossref | `crossref-rest-2026-10-05` | `2026-10-05` |
| orcid | `orcid-public-api-2026-10-05` | `2026-10-05` |

A path that is not that source's committed sample needs `--<source>-snapshot` and `--<source>-retrieval`. The sample label is not applied silently. Checksums are streamed. The run manifest and completion marker store snapshot id, retrieval date, and checksum with the config fingerprint, schema versions, and export partitions.

## Output reuse

The driver never recursively deletes an output directory. Reuse requires `_SCHOLARCHAIN_COMPLETE`, `run-manifest.json`, and every export partition named by the marker. Each non-metadata export file is also bound by its relative path, byte length, and SHA-256. A truncated or missing part does not reuse. Run id, snapshot ids, retrieval dates, checksums, schema and transformation versions, and the config fingerprint must match. A changed snapshot does not reuse old results. A marker whose export files are gone is not success. Partial output is not marked successful.

The transformation version `hadoop-prep-j01-j09-v3-stable-overflow-lineage` is unchanged by the 2026-11-26 J08 change, so it covers both the output before that date and the output after it. From 2026-11-26 J08 adds an `OVERSIZE_TEAM` reject with stage `COAUTHOR_PAIR` and the `OVERSIZE_TEAM_PAIR_STEP` counter for each team above `maxAuthorTeamSize`; the emitted pairs are unchanged. Reuse is keyed by run id: a run with a fresh run id does not reuse output written before the change; passing an existing `--run-id` would reuse it.

`s3://`, `s3a://`, and `s3n://` output roots stay `org.apache.hadoop.fs.Path` values. This module does not create them as `java.nio` directories under the working directory and does not call AWS.

Fresh-run logical comparison excludes the processing invocation UUID only from recognized intermediate-overflow locations. Exported rejects retain a bounded original location display and its complete SHA-256, plus a companion SHA-256 of the qualified file path with only the terminal `<run UUID>/intermediate/j01`–`j08` processing component canonicalized. Comparison uses the companion together with the part-file offset and native source-record reference. Genuine output roots, part identities, offsets, source record values/digests, sources and snapshots remain significant. Raw source-file locators and unknown-lineage rejects receive no location normalization.

Other invocation normalization applies only to processing `runId` fields on exported records, provenance objects, and wrapped identifier-index entries. A source title, link, observed identifier, snapshot, or native locator remains literal even when its complete value equals the invocation's `run:<UUID>` string.

## Replay

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
sbt -batch "hadoop/test"
sbt -batch "hadoop/hadoopLocalClasspath"
java -cp "<Compile/fullClasspath>" edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain --once
```

The main class loads `modules/core/src/main/resources/scholarchain.hadoop-prep.v1.json`. With no path overrides it runs the four committed samples. Optional arguments are `--config`, `--once`, `--run-id`, `--output-root`, `--execution-mode`, `--dblp`, `--openalex`, `--crossref`, `--orcid`, and the matching `--<flag>-snapshot` and `--<flag>-retrieval` pair when a path is overridden. Two runs compare a streaming export digest. `--once` does not.

Counters in `counter-summary.json` are sums across the nine jobs: `INPUT`, `ACCEPTED`, `REJECTED`, `DUPLICATE`, `CONFLICT`, `OVERSIZE_BLOCK`, `OVERSIZE_TEAM`, `OVERSIZE_TEAM_PAIR_STEP`, `EMITTED_PAIR`, `MISSING_KEY`, and `SCHEMA_FAILURE`.

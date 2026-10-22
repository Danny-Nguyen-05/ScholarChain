# Subphase 6F+6G command record

Repository: `/Users/danny/Documents/UIC/CS441/ScholarChain`; branch `phase-6`;
base/HEAD `6ae7378cbef90a176fd1faecae0dee0615eba9e3`.

Every sbt/Spark invocation used:

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

## Dataset owner

```sh
python3 datasets/scripts/phase6/acquire_dblp_slice.py
python3 datasets/scripts/phase6/test_dblp_slice.py
python3 datasets/scripts/phase6/acquire_dblp_slice.py --acquisition-receipt datasets/phase6/dblp-archive-acquisition.v1.json
python3 datasets/scripts/phase6/acquire_dblp_slice.py --output target/phase6-inputs/6fg-dblp/dblp-replay.xml --manifest target/phase6-inputs/6fg-dblp/dblp-replay-manifest.v1.json --acquisition-receipt datasets/phase6/dblp-archive-acquisition.v1.json
cmp target/phase6-inputs/6fg-dblp/dblp.xml target/phase6-inputs/6fg-dblp/dblp-replay.xml
```

The first command downloaded and verified the archive, then failed during initial
line-based extraction. The corrected bounded tag scanner, its 12 passing Python
tests, successful extraction and identical replay used the retained archive with
zero further network. See the six `dataset-*.txt` logs and dataset manifests.

## Core and Spark compilation / targeted tests

The domain owner ran the contract target, **15/15**, exit 0 (`core-targeted.txt`).
The Spark owner ran `sbt -batch 'sparkAnalytics/compile'`: the first attempt failed
on a missing `DatasetSnapshotRef` constructor argument; the corrected attempt
passed (`spark-initial-compile-failure.txt`, `spark-intermediate-compile.txt`).

```sh
sbt -batch 'independentTests/Test/scalafmt' 'independentTests/Test/compile'
sbt -batch 'independentTests/testOnly *IndependentPhase6FGSpec *IndependentPhase6SafetySpec *IndependentPhase6PipelineSpec'
sbt -batch 'independentTests/Test/scalafmt' 'independentTests/testOnly *IndependentPhase6FGSpec *IndependentPhase6SafetySpec *IndependentPhase6PipelineSpec'
sbt -batch 'sparkAnalytics/Compile/scalafmt' 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/testOnly *Phase6FGJobsSpec *Phase6CJobsSpec *Phase6DEJobsSpec'
sbt -batch 'sparkAnalytics/Compile/scalafmt' 'sparkAnalytics/Test/scalafmt' 'independentTests/Test/scalafmt' 'sparkAnalytics/testOnly *Phase6FGJobsSpec *Phase6CJobsSpec *Phase6DEJobsSpec' 'independentTests/testOnly *IndependentPhase6FGSpec *IndependentPhase6SafetySpec *IndependentPhase6PipelineSpec'
sbt -batch 'independentTests/Test/scalafmt' 'independentTests/testOnly *IndependentPhase6PipelineSpec'
```

The coordinator executed the owners' requested formatter/target commands when
holding the shared sbt slot. All source/test logic remains authored by its named
owner. The log/result sequence is:

| Log | Observed result |
| --- | --- |
| `independent-initial-compile.txt` | Format/compile exit 0 |
| `independent-initial-setup-failures.txt` | 10 passed / 3 failed, exit 1: explicit-null serialization and macOS temp symlink setup |
| `independent-plan-memory-failure.txt` | 11 passed / 1 failed / 1 suite aborted, exit 1: plan rendering exhausted the unchanged 2 GiB heap, then Hadoop failed from the exhausted heap |
| `independent-targeted.txt` | Corrected 13/13, exit 0; before final counter/layout/count assertions |
| `module-initial-test-failures.txt` | 29/32, exit 1: JSON null setup, revised counter meaning, mutable collection cast |
| `module-before-real-fix-passed.txt` | Corrected 32/32, exit 0 |
| `final-targeted.txt` | Latest module 33/33; independent 12/13; combined exit 1 solely because a new sidecar-count assertion expected a JSON number instead of the exact Long string |
| `pipeline-final-targeted.txt` | Corrected literal-count assertion; tiny pipeline 1/1, exit 0, real 52.35 s |

The source plan/retention limits and bounded found-path lineage resolved the heap
issue without increasing the fixed test heap. The final full gate covers all
latest assertions together; successful earlier targets are not substituted for it.

## Unchanged Hadoop and ER CLIs

```sh
/usr/bin/time -p sbt -batch 'hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain --config target/phase6-inputs/6fg-runtime/hadoop-config.json --once --dblp target/phase6-inputs/6fg-dblp/dblp.xml --dblp-snapshot dblp-2026-10-03 --dblp-retrieval 2026-10-22'
/usr/bin/time -p sbt -J-Xmx8G -batch 'entityResolution/runMain edu.uic.cs441.scholarchain.entityresolution.Phase5Main resolve --input target/phase6-runs/6fg-hadoop/992f0c54-0d6e-4c63-9177-84b946a18928 --policy modules/entity-resolution/src/main/resources/phase5-policy.v1.json --config target/phase6-inputs/6fg-runtime/er-config.json --llm-mode disabled --output target/phase6-runs/6fg-er-disabled'
```

Hadoop: exit 0, real 37.38 s. Its local record bound is 20,010 and its team limit
remains 16. Existing source samples and policies are unchanged. The 8 GiB ER heap
is for the bounded 466,444,898-byte prepared export, not the Spark test heap.
First ER attempt: exit 2, real 101.55 s, output-byte bound exceeded; no completed
export was published. Retry changed only the ignored runtime output-byte limit
from 256 MiB to 2 GiB: exit 0, real 97.23 s, 20,000 comparisons, zero fake/live
calls. Retained configs/bindings/manifests show the exact inputs and bounds.

## Full Spark CLI and replay

The coordinator invoked the compiled `Phase6Main` directly with the cached
`sparkAnalytics/Test/fullClasspath`, Java 17, a 4 GiB heap and the same 15 module
opens as `ScholarChainBuild.sparkTestJavaOptions`. This avoids competing sbt
launches while owners' tests run. Exact argument arrays and environment are in:

- `spark-initial-real-command.json`: first failed attempt; 83.61 s, exit 1.
- `spark-first-command.json`: repaired full run; 180.45 s, exit 0.
- `spark-replay-command.json`: fresh full recomputation; 158.07 s, exit 0.
- `spark-runtime-classpath.txt`: observed local classpath used by the CLI.

The JSON command records are evidence, not portable scripts. Rebuild and export
the current test classpath on another workstation; absolute cache paths in this
local snapshot will differ. The README also gives the sbt `Test/runMain` entry
point. Both successful runs used identical logical config and compiled artifacts;
output/checkpoint roots and shuffle partitions (4 versus 2) differed.

The initial run's SQL error and typed failure evidence are retained. Its Spark
3.5.4 union/checkpoint inferred-constraint error was repaired with an explicit
optimizer compatibility setting and a multiwindow six-hop regression. It has no
completion marker. `spark-checkpoint-diagnosis.md` distinguishes the observed
stack from the source-based diagnosis.

The coordinator verified both success markers, existing Parquet paths for all 28
datasets, matching row counts/content hashes for every table, equal counters and
equal logical run/code identity. `replay-comparison.json` records the comparison.
These hashes are computed by each fresh pipeline; actual Parquet reread/hash
equality is separately exercised for every table in module and independent tests.

## Final gate

```sh
/usr/bin/time -p sbt -batch check
git diff --check
```

The full check was started only after both successful real-data runs and the
comparison, on the stable implementation tree. Its complete log is
`final-check.txt`; final counts, exit code, timing, size and SHA-256 are recorded in
`final-gate-metadata.json` when it completes. Source snapshots prove which tree
was checked. No commit, push, reviewer, AWS, store load or live LLM was launched.

## Evidence retention and inspection corrections

Listed intermediate test logs are explicitly labeled excerpts: repeated timestamped
Spark WARN lines were removed, while commands/results and failure traces remain.
`intermediate-log-retention.json` records original/retained sizes and SHA-256 hashes;
full originals remain ignored under `target/phase6-inputs/6fg-runtime/full-intermediate-logs/`.
The complete final gate and real-data CLI logs are retained unfiltered. The
classpath export is also unfiltered. This reduces intermediate logs from 2,504,189
to 120,577 bytes without substituting an excerpt for the final gate.

Two coordinator read-only inspection snippets initially failed: one treated a
Hadoop `file:` URI as a literal filesystem path; another guessed LoadManifest
field names as `dataset`/`contentHash` rather than the actual core fields
`logicalDataset`/`sortedRowsSha256`. Both were corrected from the retained
manifest/contract. These were inspection errors, not pipeline/test passes or
implementation defects. The corrected filesystem/manifest audit is retained in
`manifest-file-audit.json`; it distinguishes metadata consistency from Parquet
row/hash rereads exercised by the module and independent suites.

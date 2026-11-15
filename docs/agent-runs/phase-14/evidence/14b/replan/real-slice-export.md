# Real-slice Spark export with Neptune openCypher sidecar (14C prerequisite, decision 3)

Owner: spark-engineer. Date: 2026-11-08. Local only: no AWS, EMR or network use. Data under `target/` is not committed.

## Result

- New run directory: `target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76`
- It has `neptune-opencypher-csv/data/{nodes,graph-edges,coauthor-edges}` and `load-manifests/neptune-opencypher-csv.json`.
- `StorageLoadMain --dry-run` (no AWS client) printed `runId=run:f6e63b4b-d542-4a32-930c-f21f002cba76 mode=dry-run nodes=78104 edges=328967 support=269753`, then `PLAN: cacheWrites=166088 cacheUnchanged=0`. sbt exit 0 after 19 min 57 s.
- Old run `6fg-spark-first-v2/run:f02acf56-...` was neither modified nor deleted.

## Inputs (unchanged from Phase 6)

- Hadoop run: `target/phase6-runs/6fg-hadoop/992f0c54-0d6e-4c63-9177-84b946a18928` (same `hadoopRunId` as the old run).
- ER run: `target/phase6-runs/6fg-er-disabled` (`run:d6a8a044-7650-4fe9-87a3-0b8b7554d2b1`, same as the old run).
- Config derived from `target/phase6-inputs/6fg-runtime/spark-first.json`: `outputRoot`, `checkpointDirectory` changed, `shufflePartitions` 4 -> 64. `logicalConfigFingerprint` is identical to the old run (`f03c7950...`); `physicalConfigFingerprint` differs (`94109318...` vs `84bfa255...`).
- Config file: `target/phase6-inputs/14c-runtime/spark-export.json` (ignored runtime input).

## Exact commands

```
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
# AWS neutralized on every command: env -u AWS_PROFILE AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null
sbt -batch "sparkAnalytics/Test/compile" "export sparkAnalytics/Test/fullClasspath"      # classpath for the direct launch
java -Xmx4g -Dspark.ui.enabled=false -Djava.net.preferIPv4Stack=true <15 --add-opens as ScholarChainBuild.sparkTestJavaOptions> \
  -cp <sparkAnalytics Test fullClasspath> edu.uic.cs441.scholarchain.spark.Phase6Main target/phase6-inputs/14c-runtime/spark-export.json
sbt -J-Xmx4g -batch "storage/runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --manifest target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76 --config target/phase6-inputs/14c-runtime/storage-validate.json --dry-run"
```

The direct `java` launch (4 GiB heap, as Phase 6 did in `docs/agent-runs/phase-06/evidence/6fg/spark-first-command.json`) is used because the sbt-forked test JVM is 2 GiB. Phase6Main took 306.9 s (real), exit 0.

## Provenance of the run

- Git HEAD: `e2f0b01ce9670c11ef9c4b3706bb52569f960a1d`. The tree was dirty: this change to `modules/spark` (uncommitted), plus other owners' uncommitted work in infra, scripts, docs and `modules/storage`. The Spark classes used were compiled from the working tree.
- `codeVersion` (run-metadata) `b6d030eb...` vs the old run's `a6719cbb...`, so the run id changed (`f02acf56` -> `f6e63b4b`).
- A first run, `target/phase6-runs/14c-spark-export/run:d70b9b61-c27c-4431-8514-2e0eac93684d`, used the unmodified exporter. It is superseded and should not be used: its CSV parts were 2/2/3 files of 43/67/124 MB (max), far above the cap.

## Counts (all identical to the old run)

| Table | New | Old |
|---|---|---|
| nodes researcher | 21,819 | 21,819 |
| nodes author_mention | 45,591 | 45,591 |
| nodes work | 10,578 | 10,578 |
| nodes venue | 112 | 112 |
| nodes institution | 1 | 1 |
| nodes topic | 3 | 3 |
| **graph nodes total** | **78,104** | 78,104 |
| edges authored | 44,083 | 44,083 |
| edges resolves_to | 45,587 | 45,587 |
| edges published_in | 10,579 | 10,579 |
| edges affiliated_with | 0 | 0 |
| edges has_topic | 3 | 3 |
| **graph edges total** | **100,252** | 100,252 |
| edges coauthored_with | 228,715 | 228,715 |
| coauthored_with_support (Parquet) | 269,753 | 269,753 |
| nodes work_sources (Parquet, not a graph node) | 10,578 | 10,578 |

Sidecar dataset row counts: nodes 78,104; graph-edges 100,252; coauthor-edges 228,715. All 28 `run-metadata.json` table row counts equal the old run's. Storage validator edge count 328,967 = 100,252 + 228,715.

Difference: every table's `contentHash` differs from the old run. I did not isolate the cause; the likely cause is that the rows carry `runId`, which changed with `codeVersion`. Row counts, input run ids and the logical config fingerprint are identical. Treat as an inference, not a verified result.

## CSV part sizes (limit 16 MiB per uploaded file)

Cause of the original overage: `Phase7NeptuneExport.publish` wrote `repartition(col(":ID"))`, so part count came from `spark.sql.shuffle.partitions` plus AQE coalescing (2-3 parts of 43-124 MB). Changing `shufflePartitions` alone would not have fixed it.

Fix (`modules/spark/.../Phase7NeptuneExport.scala`): part count = ceil(encoded CSV bytes / 8 MiB target), computed per dataset by one extra aggregate; `repartition(n, ":ID")` (an explicit count is not coalesced); after writing, any part above 16 MiB fails publication. `shufflePartitions` 64 is not required for this.

| Dataset | Parts | Total bytes | Largest part | Smallest part |
|---|---|---|---|---|
| nodes | 11 | 86,454,089 | 7,958,347 (7.59 MiB) | 7,707,910 |
| graph-edges | 16 | 132,614,953 | 8,460,397 (8.07 MiB) | 8,105,141 |
| coauthor-edges | 30 | 248,119,844 | 8,545,744 (8.15 MiB) | 8,067,965 |
| **CSV total** | 57 | **467,188,886** | | |
| support Parquet | 2 | 18,489,966 | 9,255,371 (8.83 MiB) | 9,234,595 |

The validator re-splits node CSV into enriched parts of at most 8 MiB before upload (node parts above are the source files; they are not uploaded as-is). Edge parts and the support Parquet are uploaded as written, all under 16 MiB.

Hashes: every CSV part and manifest, plus the two support Parquet parts, is in `real-slice-export.sha256` (format `sha256  bytes  path relative to the run directory`, 67 lines).

## Tests

`sbt -batch "sparkAnalytics/test"` (JDK 17): 53 passed, 0 failed, 6 suites, exit 0. The project id is `sparkAnalytics` (`spark/test` is not an sbt project). Three tests were added to `Phase7NeptuneExportSpec` (size-driven part split with one header per part and every ID once; default targets give one part for the small fixture; a part above the maximum aborts and an inverted target is rejected).

## Limits

- Offline validation only; it does not show Neptune accepts the files.
- The 16 MiB bound was checked against `NeptuneLoaderConfig.maxUploadBytes` (default) by reading the code and the observed file sizes; the upload step itself was not run.
- Storage code was being edited by another owner during the validation run (`StorageLoadMain.scala` and others showed as modified); the dry-run used whatever sbt compiled at 14:55-15:23.

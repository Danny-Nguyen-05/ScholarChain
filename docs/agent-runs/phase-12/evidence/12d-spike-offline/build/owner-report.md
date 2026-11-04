# Phase 12D Step A offline spike, build-engineer owner report

STATUS: COMPLETE for the offline scope, with one finding that changes the security config.
AES-CTR with `spark.network.crypto.authEngineVersion=2` passes the probe but FAILED the G1 pipeline twice (exit 1).
`authEngineVersion=1` (also AES-CTR, cipher left unset) passed the probe, the G1 pipeline (twice) and the baseline comparison (28/28 tables exact, twice).
No AWS call, no network download, no credential, environment-file, state or variable-file read, no source/build edit, no git commit. All writes are under `target/phase12d-spike-offline/` (gitignored, verified with `git check-ignore`).
Everything below is observed on one macOS arm64 laptop (Darwin 25.6.0) with `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home` (OpenJDK 17.0.20.1). This is not EMR/YARN proof.

## Task 1 preserve

Copied all 12 regular files plus the small `bytecode/`, `classes/`, `java/` directories (24 files total, nothing skipped) from `/tmp/scholarchain-phase12d-runtime-repair-build-20261103/` to `preserved-repair-probe/`.
`diff -r` of source against copy: identical. The /tmp directory was only read. Manifest: `preserved-repair-probe-manifest.json` (24 entries, path/bytes/sha256).

## Task 2 runtime verification (`runtime-verification.json`, script `scripts/verify-runtime.py`, `python3 -I`, exit 0)

- tgz sha256 `789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5` matches. Re-checked with `shasum -a 256` at the end: unchanged.
- Member count 378 (all regular files), 255 jars, single top dir `scholarchain-runtime`.
- Job JAR member `scholarchain-runtime/application/scholarchain-job.jar`: mode 0644, sha256 `d52f11ebad5ec9e1ffdd1910d562023e934ce7ab62e7c74a5ffd650f8951b86b` matches.
- Jars: `scala-library-2.13.14.jar`, `scala-reflect-2.13.14.jar`, `scala-collection-compat_2.13-2.7.0.jar`, `scala-parallel-collections_2.13-1.0.4.jar`, `scala-parser-combinators_2.13-2.3.0.jar`, `scala-xml_2.13-2.1.0.jar`, `spark-core_2.13-3.5.4.jar`.
- No `scala3-*` jar exists in the runtime. The `scala3-library` component in the probe JSON (`scala.deriving.Mirror`) resolves to `scholarchain-job.jar`, which bundles those classes.
- Zero jars containing `_2.12`; zero `scala-library-2.12.*`. Both assertions true.

## Task 3 security config (`spark-security.conf`, exactly the five requested lines)

```
spark.authenticate true
spark.network.crypto.enabled true
spark.network.crypto.authEngineVersion 2
spark.network.crypto.saslFallback false
spark.io.encryption.enabled true
```
`spark.network.crypto.cipher` is not set (Spark default AES/CTR/NoPadding). Fallback file `conf/spark-security-authv1.conf` is identical except `authEngineVersion 1`. Both are passed with `spark-submit --properties-file` (the extracted runtime has no `conf/spark-defaults.conf`, only the template).

Secret handling: a random 256-bit hex secret is generated per run in `scripts/run-stage.py`. Supplying `_SPARK_AUTH_SECRET` in the environment alone was not enough for the driver (attempt 1 failed with "A secret key must be specified via the spark.authenticate.secret config", exit 2). It is therefore supplied as env `_SPARK_AUTH_SECRET` (inherited by the executor JVMs) plus `-Dspark.authenticate.secret=<secret>` in `SPARK_SUBMIT_OPTS` for the driver JVM. It is never written to a file; the recorded commands show `<redacted>`.
After every run the runner scanned the driver stdout/stderr, executor stdout/stderr and every non-gz file in the run directory for the secret string: 0 occurrences in all runs (`secret_occurrences_in_run_files` in each `result.json`). Limitation: the secret is visible in `ps` output for the duration of a run to local users.
On YARN, Spark generates the secret per application; do not pass a secret there.

## Task 4 runs (all `local-cluster[2,1,1024]` unless stated, timeout 600 s, driver memory 2g, exact commands in `run/<name>/command.json`)

Common conf (from the reviewed commands): `spark.ui.enabled=false`, `spark.driver.host=127.0.0.1`, `spark.driver.bindAddress=127.0.0.1`, `spark.hadoop.fs.defaultFS=file:///`, `spark.task.maxFailures=1`, `spark.yarn.populateHadoopClasspath=false`, `spark.dynamicAllocation.enabled=false`, `spark.shuffle.service.enabled=false`, `spark.executor.cores=1`, `spark.cores.max=2`, `spark.rpc.netty.dispatcher.numThreads=2`, `spark.deploy.maxExecutorRetries=0`, `spark.executor.memory=512m` (probe) or `1g` (pipeline), `-Dlog4j.configurationFile=conf/log4j2-security-debug.properties` (copy of the reviewed debug log4j file plus an `org.apache.spark.network.sasl` debug logger) on driver and executors. Env as in the reviewed commands (`SPARK_LOCAL_IP=127.0.0.1`, `AWS_EC2_METADATA_DISABLED=true`, `SPARK_SUBMIT_OPTS=-Djava.net.preferIPv4Stack=true`, `SPARK_SCALA_VERSION=2.13`).
Command shape: `<runtime>/bin/spark-submit --master local-cluster[2,1,1024] --driver-memory 2g --class <main> --properties-file <security conf> --conf ... <runtime>/application/scholarchain-job.jar <args>` run through `python3 -I scripts/run-stage.py <name> <probe|pipeline|compare> <v2|v1|none|file:path> [--classload] [--exec-mem 1g]`.

| Run dir | What | Security | Exit | Seconds |
|---|---|---|---|---|
| a-probe-v2 | probe distributed | authEngineVersion 2 | 0 | 2.3 |
| a-probe-v1 | probe distributed | authEngineVersion 1 | 0 | 2.4 |
| b-g1-pipeline-v2 | Phase6Main G1 | authEngineVersion 2 | 1 | 38.5 |
| b-g1-pipeline-v2-rerun | Phase6Main G1 | authEngineVersion 2 | 1 | 45.9 |
| b-g1-pipeline-v1 | Phase6Main G1 | authEngineVersion 1 | 0 | 48.8 |
| b-g1-pipeline-v1-run2 | Phase6Main G1 | authEngineVersion 1 | 0 | 46.7 |
| b-compare-v1 | compare vs baseline (`local[2]`) on b-g1-pipeline-v1 output | v1 conf | 0 | 14.8 |
| b-compare-v1-run2 | compare on b-g1-pipeline-v1-run2 output | v1 conf | 0 | 11.7 |
| c-classload-probe-v1 | probe + `-Xlog:class+load=info` | v1 | 0 | 2.4 |
| c-classload-probe-v2 | probe + `-Xlog:class+load=info` | v2 | 0 | 2.5 |
| x-control-g1-nosec | G1 control, no security conf | none | 0 | 44.3 |
| x-diag-no-ioenc | G1 diag: auth + network crypto v2, no io encryption | custom | 0 | 45.1 |
| x-diag-ioenc-only | G1 diag: `spark.authenticate` + `spark.io.encryption.enabled` only | custom | 0 | 46.2 |

Earlier failed or superseded attempts are kept: `_attempt0-...` (probe, exit 2: missing shared dir, my runner bug), `_attempt1-...` (exit 2: secret via env only was rejected by the driver), `_attempt2-...` (probe exit 0, executor logs gathered by hand because local-cluster writes executor logs to `<runtime>/work`, which the runner now moves into the run dir).

### 4a probe (a-probe-v2 and a-probe-v1)
- `driverToTaskAndBackVerified=true`, `externalExecutorVerified=true`, `distributedRequired=true`, `cloudCompatibilityVerified=false` (the probe itself never claims cloud compatibility). The probe performs one task, so `taskProcesses` lists a single executor JVM (different pid from the driver). Both executor JVMs (ids 0 and 1) started and authenticated; in the G1 pipeline both ran tasks (about 1000 and 970 `Finished task` lines).
- Driver and executor-task library origins: `org.apache.spark.SparkContext` from `.../run/ex1/scholarchain-runtime/jars/spark-core_2.13-3.5.4.jar` (runtime version 3.5.4), `scala.Option` from `scala-library-2.13.14.jar` (2.13.14), `scala.reflect.api.Universe` from `scala-reflect-2.13.14.jar`, `scala.deriving.Mirror` from `scholarchain-job.jar`. No 2.12 anywhere.
- The DataFrame/Parquet roundtrip: the probe exits 0 only on success and the result JSON has `driverToTaskAndBackVerified: true`. I did not inspect a separate field named "parquet", so this is stated as "probe exit 0 and verified flags true".
- Encryption/auth evidence (patterns: `SecurityManager: authentication enabled`, `AuthRpcHandler`, `-Dspark.network.crypto`; see `analysis.json` keys `auth-*`):
  - Driver stderr, a-probe-v2: 6 lines `INFO spark.SecurityManager: SecurityManager: authentication enabled; ui acls disabled; ...`, 12 lines `DEBUG crypto.AuthRpcHandler: Received new auth challenge for client /127.0.0.1:<port>.` and 12 lines `DEBUG crypto.AuthRpcHandler: Authorization successful for client /127.0.0.1:<port>.` (`crypto.AuthRpcHandler` is the Spark AES key-exchange auth path, used when `spark.network.crypto.enabled=true`).
  - Each executor stderr: 2 `authentication enabled` lines, and the logged `Spark Executor Command` contains `-Dspark.authenticate=true -Dspark.network.crypto.authEngineVersion=2 -Dspark.network.crypto.enabled=true -Dspark.network.crypto.saslFallback=false`. a-probe-v1 shows `authEngineVersion=1`.
  - No log line names the cipher or `spark.io.encryption`; the cipher is inferred from the default. I did not run a negative control (wrong secret) and there was no packet capture, so "traffic is encrypted" is inferred from the enabled flags and the auth handler lines.

### 4b G1 pipeline and comparison
- authEngineVersion 2: both runs died with exit 1 in a `ShuffleMapStage ... count at BoundedActions.scala:25` task (stage 2049, then stage 2683). Executor error: `java.io.IOException: java.lang.ArrayIndexOutOfBoundsException: Index 0 out of bounds for length 0` from `TorrentBroadcast.readBlocks(TorrentBroadcast.scala:206)` via `ReliableCheckpointRDD.readCheckpointFile`, right after the log line `Read broadcast_N_piece0 from the disk of a same host executor is successful`. I did not find the root cause. Controls: no security conf (x-control-g1-nosec), network crypto v2 without io encryption (x-diag-no-ioenc), and io encryption without network crypto (x-diag-ioenc-only) each passed once. So the failure appeared only with the full `spark-security.conf` (2 of 2 runs); sample sizes are small.
- authEngineVersion 1 (full five-line config except version): b-g1-pipeline-v1 and b-g1-pipeline-v1-run2 exited 0 (2 of 2).
- Comparison against `target/phase12d-readiness-20261103/baseline/g1-a-attempt2/run:2047866e-0b89-4047-9a31-dccb2515c68d`: both comparisons report `tablesCompared=28`, `allExactRowsMatch=true`, 28 of 28 tables `exactSchemaAndRowsMatch=true`, `provenanceNormalization=none`, and the same `runId`, `codeVersion`, `hadoopManifestHash`, `entityResolutionManifestHash` as the baseline. Total rows across tables 587. The comparison result also says `cloudCompatibilityVerified=false`.
- Inputs: `g1-upstream-inputs.tgz` (sha256 `e05931ab0eec2fc66b1a0d0ab33e5b4c070faf81afcb66fc00208287b85ab558`, matches the stated value, 85 members) extracted with Python `tarfile` into `run/ex1/g1/g1`. Config `conf/spark-g1-spike.json` is the reviewed `relocated-g1-config.json` with four paths changed; the runner renders a per-run copy with fresh output and checkpoint dirs.
- Warning observed in all local-cluster pipeline runs: `Spark is not running in local mode, therefore the checkpoint directory must not be on the local filesystem`. On EMR the checkpoint directory in the config must be on a shared filesystem (HDFS or S3 path), not a node-local path.

### 4c class-load proof (c-classload-probe-v1 and v2)
- Grep pattern: `\[class,load\] (scala\.Predef\$|scala\.collection\.immutable\.List|org\.apache\.spark\.SparkContext) source: ` (the Predef class that loads is `scala.Predef$`; plain `scala.Predef` never appears as its own load line).
- JVM unified logging goes to stdout by default, so the evidence is in driver stdout and in each executor's `stdout` file under `<SPARK_HOME>/work/app-*/<id>/` (not under `SPARK_WORKER_DIR`).
- v1 run matched lines, driver: `org.apache.spark.SparkContext source: file:<RT>/jars/spark-core_2.13-3.5.4.jar`, `scala.collection.immutable.List source: file:<RT>/jars/scala-library-2.13.14.jar`, `scala.Predef$ source: file:<RT>/jars/scala-library-2.13.14.jar`. Executors 0 and 1: the same three classes from the same jars (3 matched lines each). The v2 class-load run gives the same result. Full matched lines are in `analysis.json`.
- Counts: 0 class-load lines mentioning `2.12` in driver or either executor. Zero `scala.*` classes loaded from a file source other than the 2.13.14 scala-library/scala-reflect jars, the other 2.13 Scala jars, or the job jar.
- Log volume: probe with class-load logging: 24,220 lines, 4,116,158 raw bytes, 259,878 gzip bytes (driver stdout 9,979 lines; executors 7,369 and 6,478 lines). Pipeline (G1) with debug security logging and no class-load logging: about 85,700 lines, 9.9 MB raw, 0.70 MB gzip. Class-load logging on the pipeline was not measured; expect it to add several MB per JVM.

## Cleanup
No Spark JVMs remain (`pgrep -fl java` returned nothing after the last run; each runner invocation also sends SIGKILL to its process group). The extracted runtime is `run/ex1/scholarchain-runtime` (the runtime `work/` directory is empty after the runner moved executor logs, with job-jar copies deleted).

## What the infra owner must match on EMR
- Conf keys: `spark.authenticate=true`, `spark.network.crypto.enabled=true`, `spark.network.crypto.saslFallback=false`, `spark.io.encryption.enabled=true`, and `spark.network.crypto.authEngineVersion=1` (proven here; `2` failed the G1 pipeline twice locally). Leave `spark.network.crypto.cipher` unset. Do not set `spark.authenticate.secret` on YARN. The Spark 3.5 default of `authEngineVersion` is 1 (from my knowledge of Spark, not observed here), so set it explicitly. EMR/YARN-side settings are not covered by this test.
- JAVA_HOME: the tested runtime ran on JDK 17.0.20.1. The cluster must run Java 17 for driver and executors (set JAVA_HOME for Spark in the cluster's spark-env settings; EMR's default JVM may differ). The runtime's `bin/spark-submit` needs `SPARK_HOME` and `SPARK_SCALA_VERSION=2.13`.
- Class-load grep: pattern above, applied to driver stdout and every executor container `stdout` (YARN container logs); also grep for `_2.12` expecting 0. Expected sources: `scala-library-2.13.14.jar`, `spark-core_2.13-3.5.4.jar`. On YARN these jars sit in a different path than here, so match on jar file names, not full paths.
- Add `-Xlog:class+load=info` to `spark.driver.extraJavaOptions` and `spark.executor.extraJavaOptions`. A file target (`-Xlog:class+load=info:file=<path>`) was not tested here.
- Log volume to size cloud logs: see 4c, about 4 MB raw for a trivial probe with class-load logging and about 10 MB raw for the G1 pipeline with debug logging on three JVMs.
- Checkpoint directory must not be node-local (see warning above).

## Limitations
- `local-cluster` on one Mac is not YARN or EMR proof. Hadoop/YARN RPC and HDFS/shuffle-service encryption were not covered. All traffic here is loopback.
- The G1 failure with `authEngineVersion=2` was not root-caused and may be specific to `local-cluster` (executors read broadcast pieces from the disk of a same-host executor). It is unknown whether it reproduces on YARN. Treat v2 as unproven.
- The probe uses one task and so one executor process; "two executor JVMs" is shown by the worker logs (executors 0 and 1 both started and authenticated) and by task counts in the pipeline run, not by the probe JSON.
- Encryption is evidenced by configuration, authentication logs and the auth handler path, not by a packet capture or negative test.
- The auth secret appears in the `ps` command line of the local driver JVM while running (not in any file or log).

## Files and hashes
Top-level: `spark-security.conf`, `conf/spark-security-authv1.conf`, `conf/log4j2-security-debug.properties`, `conf/spark-g1-spike.json`, `conf/diag-*.conf`, `scripts/{verify-runtime,run-stage,analyze}.py`, `runtime-verification.json`, `preserved-repair-probe-manifest.json`, `analysis.json`, `owner-report.md`, `manifest.json`.
`manifest.json` lists the sha256 of every file I produced, except the extracted runtime tree, extracted G1 inputs, raw (uncompressed) driver/executor logs, pipeline output datasets, checkpoints and probe shared dirs. Raw log hashes are recorded in each `run/*/result.json` together with the gzip copies' hashes.

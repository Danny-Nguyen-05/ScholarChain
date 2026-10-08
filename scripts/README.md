# ScholarChain scripts

## `phase4-emr-smoke.sh`

Bounded EMR smoke for `HadoopPrepMain`: one `--once` run with `--execution-mode cluster` over the four sample paths under an existing S3 input prefix. Hadoop stays **Provided** on the cluster. The step does not ship a Hadoop client JAR.

The step uses `command-runner.jar` and `bash -c` on the cluster master. The job JAR is `hadoop-submit_*.jar` (module classes plus `lib/<dependency-bundle>.jar` for RunJar). Do not submit the thin JAR alone. Before `hadoop jar`, the step localizes that submit JAR, the dependency bundle, and the prep config into a fresh work directory under `${TMPDIR:-/tmp}`:

- `s3://`, `s3a://`, `s3n://`, and `hdfs://` sources are copied with `hadoop fs -copyToLocal`.
- Any other path is copied with `cp` when it is already a regular file on the master.

The driver exports `HADOOP_CLASSPATH` to the localized bundle. Tasks receive that same localized bundle through `-libjars` on the application arguments. `--config` is the localized local file, never the original remote URI. Dataset inputs (`--dblp`, `--openalex`, `--crossref`, `--orcid`) and `--output-root` stay remote `s3://` URIs. Sample data is not copied onto the master.

Required inputs (no defaults): EMR cluster id, AWS region, S3 input prefix, S3 output prefix (`s3://bucket/non-empty-key`), submit JAR (`SCHOLARCHAIN_HADOOP_SUBMIT_JAR` or `--jar`; `hadoop-submit_*.jar`), dependency bundle path (`SCHOLARCHAIN_HADOOP_DEPENDENCY_BUNDLE` or `--libjars`), and prep config path. `SCHOLARCHAIN_HADOOP_THIN_JAR` is a deprecated alias for the submit JAR value. Jar, bundle, and config may be cluster-visible remote URIs or master-local paths.

The step passes `--output-root` from `--output-prefix` (overrides config `outputRoot` on the cluster) and fixed snapshot/retrieval metadata for the overridden S3 sample paths. `maxLocalSampleRecords` in the prep config is documented in `--help` as a launch-level bound for the whole step, not a per-mapper cap.

The step also enforces an inclusive smoke ceiling on the prep config. A local regular `--config` file is checked before the EMR step is built; failure exits non-zero and does not print `aws emr add-steps`. The cluster `bash -c` body runs the same check after `copyToLocal` and before `hadoop jar`, so a remote config is checked on the master. Each ceiling field must be present as a JSON number. Missing or non-numeric fields fail closed. The master needs `python3` for that localized check. The loader's positive-value check still applies when the job starts.

- `maxLocalSampleRecords` <= 1000
- `reducerCount` <= 8
- `maxCandidateBlockSize` <= 256
- `maxCandidatePairsPerBlock` <= 4096
- `maxAuthorTeamSize` <= 64
- `maxRecordBytes` <= 8388608
- `maxXmlEntityExpansion` <= 8388608

The committed `scholarchain.hadoop-prep.v1.json` profile is inside this ceiling.

Default behavior is **dry-run**: it prints the exact `aws emr add-steps` command and exits without submitting a step and without invoking `hadoop` or `aws`. Pass `--execute` only after human approval.

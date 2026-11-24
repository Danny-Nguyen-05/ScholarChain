# Phase 18 work order: EMR Spark template-fetch fix (Day 1, offline)

Drafted: 2026-11-24 (America/Chicago), by the coordinator. Branch `phase-18` from `main` at `ad86b07` (tag `v1.0-final`). `main` and the tag are not changed by this phase until the human decides.

## Goal

Fix the open incident `docs/incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md`: the EMR `spark-job` step failed in its template fetch (`hadoop fs -copyToLocal`, `ClassNotFoundException com.amazon.ws.emr.hadoop.fs.EmrFileSystem`, exit 255) before Spark started. Day 1 is offline only: no AWS call, no Terraform apply, no deployment, no model call.

## Diagnosis basis (coordinator, from the committed script and the incident record; the private step stderr was not read)

In `scripts/emr/sc-step.sh`, `body_spark_job` calls `spark_env` (which runs `require_mount` and `resolve_java`, exports `SPARK_HOME`, `SPARK_CONF_DIR`, `SPARK_SCALA_VERSION`, `HADOOP_CONF_DIR`, `YARN_CONF_DIR`, `PATH`, unsets `CLASSPATH`, `SPARK_DIST_CLASSPATH`, `HADOOP_CLASSPATH`, `SPARK_CLASSPATH`, and checks the job-jar sha256) and only then calls `localize`, whose `s3://` branch runs the stock EMR `hadoop fs -copyToLocal`. On the same cluster, the S3 fetches of `hadoop-prep` and `entity-resolution` succeeded; both ran `localize` before any such environment change (entity-resolution after `resolve_java` only). The `spark-job` template fetch is the only S3 `localize` that runs after `spark_env`. Hypothesis: the portable-runtime environment breaks the stock Hadoop client's EMRFS classpath. This is a hypothesis; only a live run can confirm it.

## Packages

| Package | Owner | Scope |
|---|---|---|
| 18A | infra-engineer | `scripts/emr/sc-step.sh`: the `spark-job` template fetch must run in the stock EMR environment, not after `spark_env`. Update any sha256 pin of the file and the offline tests under `scripts/tests/**`; add a regression test that fails on the old order. |
| 18B (only if needed) | test-engineer | `tests/scripts/**` tests that pin the old order or the old sha256. |
| Review | code-reviewer | Read-only verdict on the diff and tests. |

## Gates

Offline script tests, `sbt check`, review APPROVE, then `scripts/check.sh` full check. Then the human approves the fix. Any live EMR run (Day 2) needs the official extension, a reviewed Terraform plan, the human's approval recorded here, and a human decision on the EMR run cap.

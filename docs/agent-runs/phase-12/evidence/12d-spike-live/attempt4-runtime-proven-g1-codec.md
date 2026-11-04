# Attempt 4: Scala 2.13 runtime proven on EMR; G1 failed on the LZO codec (2026-11-04)

Authority: human-approval.md Amendment 3 (14:12 CST, window until 17:30). All times are CST. The account ID and bucket name are redacted. Raw outputs are in `target/phase12d-spike-live/` (git-ignored, sha256 manifest), including 112 EMR log files under `attempt4-emr-logs/` and the verified `collected/` results, all downloaded before the destroy.

1. **14:32 Preflight and plan** (deploy-engineer): `state list` empty; `Plan: 55 to add, 0 to change, 0 to destroy`; sha256 `d0a92e4374eaaa20694d8c7df5598f956e69491d24f39e0eeaf1c1cce8815f75`. The plan rule passed (the same 55 addresses and an equal shape). Code at commit `bf685ff`.
2. **Apply, run by the human:** "Apply complete! Resources: 55 added, 0 changed, 0 destroyed." The `shape` output equals the approval.
3. **Cluster `j-…Y19XI7VPZN7`:**
   - Created 14:37:10, ready 14:41:26 (bootstrap, EFS mount and Java resolution succeeded), ended 14:44:11.
   - Total 7 min 1 s; NormalizedInstanceHours 16 (two m5.xlarge).
   - Final state `TERMINATED`, "Steps completed with errors". Auto-termination after the steps worked as designed.
   - Spark reported Java `/usr/lib/jvm/java-17-amazon-corretto.x86_64`, version 17.0.21.

| Step | State | Time |
|---|---|---|
| probe (Phase12Readiness, YARN cluster mode) | COMPLETED; YARN final status SUCCEEDED | 14:41:30–14:41:50 |
| g1 (Phase6Main) | FAILED, exit 1 | 14:41:55–14:42:13 |
| collect | COMPLETED | 14:42:18–14:42:22 |

4. **Results:** `collect-evidence.sh` exit 0. The results tarball sha256 `7af8c4f4b4305e3d5936d7f50fce88695328e4fcf6f96e8dd800f81d30272647` verified, and the extracted files match the on-node manifest.

## Runtime proof (12-10 core question): passed

- **Probe JSON** (`results/probe-distributed.json`):
  - Driver (pid 7549) and a separate executor JVM (pid 7684, executor 2) on the core node.
  - Both loaded `org.apache.spark.SparkContext` from `/opt/scholarchain-runtime/jars/spark-core_2.13-3.5.4.jar`, `scala.Option` from `scala-library-2.13.14.jar` and scala-reflect from `scala-reflect-2.13.14.jar`. The Scala 3 library came from the job JAR.
  - `driverToTaskAndBackVerified=true`, `externalExecutorVerified=true`.
  - The probe's own `cloudCompatibilityVerified=false` is a fixed field of the probe, not a result.
- **Class-load logs:** `-Xlog:class+load` in all 6 YARN container stdout files (3 JVMs per application, for both applications). Every JVM loaded `scala.Predef$` and `scala.collection.immutable.List` from `scala-library-2.13.14.jar`, and `SparkContext` from `spark-core_2.13-3.5.4.jar`. There are **0 matches for Scala 2.12** in any container log.
- **Security config in effect:** Spark authentication plus AES-CTR network crypto (`authEngineVersion` 1) and IO encryption, as disclosed.
- **Not separately recorded:** a Parquet/DataFrame roundtrip field is not in the probe JSON. The probe succeeded, but this item is unverified as a distinct check.

## G1 job: failed, so the output comparison did not run

- The driver/AM stderr and the Spark event log show `java.lang.IllegalArgumentException: Compression codec com.hadoop.compression.lzo.LzoCodec not found`. The failure came from `CompressionCodecFactory.getCodecClasses`, reached through `JsonFileFormat.isSplitable` while G1 read its JSON inputs (`Phase6CReaders.scala:407`).
- **Interpretation:** EMR's node Hadoop configuration (`io.compression.codecs`) names the LZO codec, which the portable runtime does not ship. This is an infrastructure configuration issue, not an application or Scala issue.
- **Candidate fix:** set `spark.hadoop.io.compression.codecs` in the spike's Spark defaults to the standard Hadoop codecs, excluding LZO. Not yet tested.
- No G1 output was produced, so the 28-table baseline comparison (`allExactRowsMatch`) was **not observed on EMR**.

## Destroy

Run by the human: the first pass failed only on `aws_eip.nat`, the known `DisassociateAddress` issue (item 24). The second pass reported "Destroy complete! Resources: 1 destroyed." **14:51 After-inventory** (deploy-engineer, read-only):
- `state list` is empty, and `inventory.sh` exited 0 with `clean: true` and no billable resources remaining.
- Expected-retained: 4 KMS keys in PendingDeletion.
- Tagging-API residue: 26 security-group-rule ARNs and 3 vpc-endpoint ARNs. Direct describes find none of them.
- Bucket: 404. No clusters are active.
- Tagged instances are all terminated; NAT gateways show as deleted; there are no EIPs, VPCs, volumes or EFS left.

**Codec confirmation:** the G1 application's Spark event log ("Hadoop Properties") shows `io.compression.codecs = …GzipCodec,…DefaultCodec,…BZip2Codec,…SnappyCodec,com.hadoop.compression.lzo.LzoCodec,com.hadoop.compression.lzo.LzopCodec`. The job overrides only `spark.hadoop.fs.defaultFS`, and no runtime classpath entry contains LZO. EMR's provisioning logs show `hadoop-lzo` installed with `hadoop_lzo_codec: true`.

## Cost

The cluster used 16 normalized instance-hours. EMR bills per second, so two m5.xlarge for about 7 min of EC2 plus the EMR surcharge comes to about USD 0.06. Add the NAT gateway and EIP for about 20 min, EFS, S3 and the KMS key allowance. Attempt 4 is under about USD 0.30 plus KMS.

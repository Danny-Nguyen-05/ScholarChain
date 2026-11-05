# 12-10 EMR Spark runtime decision (for the 12B/12C EMR module and the Phase 13 and 15 Spark steps)

**Recorded by:** the coordinator, 2026-11-04.
**Basis:** the plan's 12D rule, "test candidates in this order and stop at the first that works". Candidate (a) worked live in attempt 5, so this record follows from that rule and from the evidence. It is not a new choice by an agent.
**Status:** it becomes the project's decision when the human accepts it at the Phase 12 gate. This file is not a human decision record.

## Decision

Use **EMR on EC2** with a **bootstrap-installed portable Spark 3.5.4 / Scala 2.13.14 runtime on Java 17**. Do not use EMR's own Spark, which is built for Scala 2.12.

### Proven configuration to carry forward

| Item | Proven value | Source |
|---|---|---|
| Release | `emr-7.8.0` | spike `emr.tf` |
| EMR applications | **`["Hadoop"]` only**. The stock Spark 3.5.4-amzn / Scala 2.12 is not installed. | spike `emr.tf` |
| Runtime archive | `scholarchain-spark3.5.4-scala2.13.14-java17-runtime.tgz`, sha256 `789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5`. It contains 378 files and 255 JARs, with no `_2.12` JAR. It is installed at `/opt/scholarchain-runtime`. | `../12d-spike-offline/build/runtime-verification.json`; build provenance in `../12d-portable-runtime/` |
| Job JAR | sha256 `d52f11ebad5ec9e1ffdd1910d562023e934ce7ab62e7c74a5ffd650f8951b86b`, the Phase 6 CLI, unchanged | same |
| Classpath | `spark.yarn.jars=local:/opt/scholarchain-runtime/jars/*` and `spark.yarn.populateHadoopClasspath=false` | spike `main.tf` |
| Java | Java 17 is resolved on each node at bootstrap; the actual path was `/usr/lib/jvm/java-17-amazon-corretto.x86_64`, version 17.0.21. The resolved path is written to the AM and executor `JAVA_HOME`. **Do not hard-code the path.** | `scripts/phase12d-spike/emr/bootstrap.sh:134-151` |
| Hadoop codecs | `spark.hadoop.io.compression.codecs` set to the Gzip, Default, BZip2 and Snappy codecs only. EMR's node configuration lists LZO, which the runtime does not ship. | spike `main.tf:60` |
| Spark security | `spark.authenticate`, network crypto with the default AES-CTR cipher, `authEngineVersion=1`, `saslFallback=false`, and IO encryption | spike `main.tf` |
| Deploy mode | YARN cluster mode (`--master yarn --deploy-mode cluster`) | spike `emr.tf:51,59` |
| Teardown | Destroy needs **two passes**, because of the `aws_eip.nat` `DisassociateAddress` 403 (item 24) | live attempts 2 to 5 |

### Rejected or not tested

- **Stock EMR Spark** (Scala 2.12.18 on EMR 7.8): incompatible with the Scala 3 build, which uses `spark-sql_2.13`. See `../../../phase-06/evidence/6a/emr-compatibility.md`.
- **EMR Serverless custom image:** not tested; it was made unavailable by the human's decision and was not needed.
- **EMR on EKS custom image:** not tested and not needed.
- **AES-GCM network crypto:** not used. Two bounded local tests failed (`../12d-portable-runtime/`), and the cause is unknown. This is a disclosed limitation.

## What the main EMR module must change (owner: infra-engineer, routed in Phase 13; nothing is edited here)

The 12B/12C module `infra/terraform/modules/emr/main.tf` does not yet match the proven configuration:

1. `main.tf:19` installs `applications = ["Hadoop", "Spark"]`. Change it to Hadoop only, or prove that the stock Spark install cannot leak onto the classpath.
2. `main.tf:46-50` has a single bootstrap action that takes `runtime_reference`. It must install the runtime, verify its hash, resolve Java 17 and write the Spark defaults in the table above, as the spike's bootstrap does.
3. `main.tf:5-12` turns on EMR in-transit TLS with a PEM certificate. **That combination with the custom runtime is untested.** The spike instead used Spark-native authentication and AES-CTR, with Hadoop and YARN RPC unencrypted. Prove the combination before relying on it, or disclose the gap.
4. Carried item 17 must close before this module, or any other EMR cluster in us-east-2, is applied (`main.tf:52` sets the EMR-managed tag).

## Open questions this spike did not answer (Phase 13 and 15 must prove them; the agent makes no choice)

| # | Gap | Why it matters | Options (each needs a build or infra change, a test, review and the human gate) |
|---|---|---|---|
| G1 | **S3 input and output.** The runtime has no S3 filesystem: EMRFS is excluded by `populateHadoopClasspath=false`, and there is no `hadoop-aws`. The spike staged data on EFS (`file:///`) and copied to and from S3 in its bootstrap and collect steps. | Phase 13 reads its inputs from S3 and writes its outputs there. Carried item N1, the EMRFS delete and commit permissions, also stays unverified. | (i) Add `hadoop-aws` matching the runtime's Hadoop 3.3.4 client, plus its AWS SDK bundle, and use `s3a://`. That needs a new runtime build and hash, plus a live check. (ii) Keep EFS staging with explicit S3 copy steps, as the spike did. (iii) Bring EMRFS onto the runtime classpath. This is the riskiest option, because it reintroduces EMR's Hadoop classpath. |
| G2 | **Dynamic allocation and the shuffle service.** The spike ran with both off. A Hadoop-only cluster has no Spark YARN shuffle auxiliary service. | Phase 15 elasticity needs executors to scale with task nodes. | (i) `spark.dynamicAllocation.shuffleTracking.enabled=true`, which needs no external shuffle service. (ii) Install a `spark-3.5.4-yarn-shuffle` JAR as a NodeManager auxiliary service through bootstrap or configuration. The runtime does not contain one today: it has only `spark-network-shuffle_2.13-3.5.4.jar`, so the JAR would have to be added from the official distribution and hashed. |
| G3 | **Task nodes and managed scaling.** The bootstrap must run on every new node, and the same-AMI Java resolution is assumed. | Phase 15 | Prove with one scale-out and scale-in event. |
| G4 | **Larger data than G1.** | Phase 13 and 15 | Size the cluster from a bounded run. |
| G5 | **Runtime archive retention.** The tgz is a 321 MB git-ignored local artifact. | Reproducibility in later phases | Store it in a project bucket with its hash, or rebuild it with the `../12d-portable-runtime/` scripts. |
| G6 | **Budget.** The USD 15 all-EMR reserve funded this spike, which was modeled at about USD 5.35 or less. | Later EMR runs need a new allocation decision (`../../repairs.md:187`). | Human decision after the Billing reconciliation |

## Live evidence

[../12d-spike-live/attempt5-success.md](../12d-spike-live/attempt5-success.md), with proof files in [../12d-spike-live/attempt5-proof/](../12d-spike-live/attempt5-proof/). The earlier attempts' root causes are in `attempt1` to `attempt4` in that folder.

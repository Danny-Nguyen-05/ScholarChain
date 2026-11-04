# Isolated EMR spike (Phase 12D Step A, authored offline)

One-shot Terraform root that builds a throw-away, fully isolated environment, runs a distributed Spark probe and the G1 pipeline on a portable Spark 3.5.4 / Scala 2.13 / Java 17 runtime on EMR 7.8.0, copies the results to S3, and ends. It supersedes the zero-resource proposal root `../emr-spark/`, which is unchanged.

**Status: authored and mock-tested only.** No plan against AWS, no apply, no AWS call has been made. The human applies the `../../deployer` root first; a deploy-engineer runs this root only after the recorded human gate.

## Exact shape (every item is pinned by a variable validation that rejects any change)

| Item | Value |
|---|---|
| Region / AZ | `us-east-2` / one AZ (default `us-east-2a`) for both subnets, the EFS mount target and both nodes |
| Release | `emr-7.8.0`, applications `["Hadoop"]` only (no stock Spark) |
| Nodes | 1 primary + 1 core `m5.xlarge`; no task nodes, no Spot, no instance fleets, no autoscaling or managed scaling |
| Volumes | root 32 GiB gp3 (`ebs_root_volume_size`) plus exactly one 32 GiB gp3 data volume per instance (3000 IOPS, 125 MiB/s): 4 volumes, 128 GiB |
| Lifetime | `max_cluster_minutes` <= 120 (default 120); `cap_usd = 10`; one attempt (`max_attempts = 1`) |
| Steps | `probe` (CONTINUE), `g1` (CONTINUE), `collect` (TERMINATE_CLUSTER), `step_concurrency_level = 1` |
| Termination | `keep_job_flow_alive_when_no_steps = false`, `termination_protection = false`, `unhealthy_node_replacement = false`, `auto_termination_policy.idle_timeout = 900` |

Required variables: `account_id`, `owner`, `expiration_date` (`YYYY-MM-DD`, calendar-validated), `permissions_boundary_arn` and `deployer_role_arn` (both from the deployer root outputs), `runtime_tgz_path`, `inputs_tgz_path`, `g1_config_template_path`. The expected sha256 values are variable defaults (runtime `789a9684...de5`, job JAR `d52f11eb...b86b`, G1 inputs `e05931ab...b558`); `filesha256(path)` is checked in a variable validation, so **the plan fails on any mismatch or missing file**. `yarn-jars.zip` is not used. See `terraform.tfvars.example`.

Provider `default_tags` on every taggable resource: `course`, `project`, `environment = spike`, `owner`, `expiration`, `scholarchain:stack = spike-emr`, and `for-use-with-amazon-emr-managed-policies = true` (required by the `AmazonEMRServicePolicy_v2` conditions on subnets, security groups and the VPC, and propagated to nodes).

## Resources

* **Network** (`network.tf`, `security_groups.tf`): dedicated VPC `10.42.0.0/16`; private subnet (nodes and EFS mount target) and public subnet (NAT gateway and EIP only); internet gateway; two route tables; S3 gateway endpoint on the private route table (default full-access policy; narrowing it would require enumerating the EMR and Amazon Linux repository buckets); no public IPs on nodes (`map_public_ip_on_launch = false` on both subnets), no key pair, no SSH ingress, no public UI (`spark.ui.enabled=false`). Custom EMR-managed primary, core and service-access security groups following the private-subnet rule tables (service access accepts TCP 9443 from the primary group and sends 8443 to primary and core), plus an EFS group that accepts TCP 2049 only from the primary and core groups. The VPC default security group is deliberately **not** managed (adopting it would need unscopable deployer rights); it keeps the AWS default rules and nothing in this root attaches to it. The groups use `revoke_rules_on_delete` because EMR adds cross-referencing rules that otherwise block deletion.
* **KMS** (`kms.tf`): one CMK, no rotation, `deletion_window_in_days = 7`. The key policy is a literal with enumerated actions naming only the account root (administration for the human), the **deployer role** (variable `deployer_role_arn`: key administration, plus use via S3 and EFS only), the EMR service role (EBS and local-disk grants) and the instance role.
* **EMR security configuration** (`emr.tf`): at-rest local-disk and EBS encryption with the CMK, S3 SSE-KMS; **in-transit encryption is off**.
* **S3** (`s3.tf`): one bucket `scholarchain-spike-emr-<account>-<region>`, `force_destroy = true`, public access blocked, `BucketOwnerEnforced`, TLS-only deny policy, default SSE-KMS with bucket key, no versioning, no lifecycle. Seven `aws_s3_object`s: runtime tarball, G1 inputs tarball, `bootstrap.sh`, `run-step.sh`, `collect-results.sh`, rendered G1 config, `spark-defaults.conf`. `log_uri` is `s3://<bucket>/emr-logs/`.
* **EFS** (`efs.tf`): encrypted with the CMK, General Purpose, Elastic throughput, backup policy explicitly `DISABLED`, one mount target in the private subnet, one access point enforcing POSIX uid/gid 1500 and root `/scholarchain-spike`, file-system policy that denies non-TLS and allows only the instance role through that access point. Mounted at `/mnt/scholarchain` on both nodes with `amazon-efs-utils` (`-o tls,iam,accesspoint=...`).
* **IAM** (`iam.tf`): EMR service role (`AmazonEMRServicePolicy_v2` plus an inline `iam:PassRole` for the instance role, which the managed policy only allows for `EMR_EC2_DefaultRole`), EC2 instance role and profile. All names start `scholarchain-spike-emr-` and both roles carry `permissions_boundary_arn`. The instance role may do only: `s3:GetObject` on `staging/*`, `s3:PutObject` and `s3:AbortMultipartUpload` on `results/*` and `emr-logs/*`, `s3:ListBucket` for those three prefixes, KMS data-key actions on the spike key, EFS `ClientMount`/`ClientWrite` on this file system through this access point, and `elasticmapreduce:Get/Put/RemoveAutoTerminationPolicy` on stack-tagged clusters in us-east-2 (AWS re:Post: without these on the instance profile the cluster stays active after the idle timeout, https://repost.aws/knowledge-center/emr-troubleshoot-cluster-termination). No `*` resource appears in that policy (a mock test checks this). `s3:AbortMultipartUpload` goes beyond the literal Get/Put/List list; it only lets a failed multipart upload clean itself up.
* **Cluster** (`emr.tf`): as in the table above.

## Cluster software and Spark settings

The bootstrap action runs on every node: it installs the runtime into `/opt/scholarchain-runtime` (sha256-verified, job JAR sha256 re-verified), installs `spark-defaults.conf` into the runtime's `conf/`, installs the step scripts into `/opt/scholarchain-spike/bin`, checks `JAVA_HOME` is Java 17, installs `amazon-efs-utils` and mounts the access point. On the primary only it creates the working directories on EFS, extracts the G1 inputs to `/mnt/scholarchain/inputs/g1/...` and fetches the rendered G1 config to `/mnt/scholarchain/config/`.

Spark settings (all in the generated `spark-defaults.conf`, printed by `terraform output spark_defaults`):

* `spark.yarn.jars=local:/opt/scholarchain-runtime/jars/*`, application JAR `local:/opt/scholarchain-runtime/application/scholarchain-job.jar`, `spark.yarn.populateHadoopClasspath=false`, `spark.hadoop.fs.defaultFS=file:///`. No ambient `CLASSPATH` or `SPARK_DIST_CLASSPATH`, no stock EMR Spark: `run-step.sh` unsets them and sets `SPARK_HOME` to the custom runtime.
* **`spark.yarn.stagingDir=file:///mnt/scholarchain/staging`.** With `fs.defaultFS=file:///` the default staging directory would sit on the primary's local disk, which the ApplicationMaster on the core node cannot localize. EFS is mounted at the same path on both nodes, so both can read it. The alternative, an explicit `hdfs://` path, would reintroduce HDFS and the Hadoop 3.3.4 client versus EMR 3.4.1 server question for no benefit.
* **Java 17 is detected on each node at bootstrap time, not hard-coded.** Live attempt 3 showed the documented path `/usr/lib/jvm/java-17-amazon-corretto` (from AWS re:Post) does not exist on EMR 7.8.0: the controller runs `JAVA_HOME=/etc/alternatives/jre` and `/usr/lib/jvm/jre-17/bin/java`. The bootstrap tries, in order, an explicit `--java-home` (not passed by Terraform), `/usr/lib/jvm/jre-17`, `/usr/lib/jvm/java-17-amazon-corretto`, `...corretto.x86_64`, the `readlink -f` of `/etc/alternatives/jre`, and the Java found on `PATH`; it accepts the first whose `bin/java -version` reports major 17, otherwise exits 4 listing the candidates. The result is written to `/opt/scholarchain-spike/java-home` and logged, appended to the node-local `spark-defaults.conf` as `spark.yarn.appMasterEnv.JAVA_HOME` and `spark.executorEnv.JAVA_HOME`, and read by `run-step.sh`. The generated `spark_defaults` therefore contain no `JAVA_HOME`. Assumption: both nodes use the same AMI, so the path resolved on the primary (whose defaults the client sends) is valid on the core node where the AM and executors run.
* `spark.executor.instances=2`, `spark.executor.cores=1`, `spark.executor.memory=3g`, `spark.driver.memory=3g`, `spark.task.maxFailures=1`, `spark.yarn.maxAppAttempts=1`, dynamic allocation and shuffle service off. Sizing: the single core node runs the driver/AM and two executors as separate JVMs; with default overhead that is about 3 x 3.4 GiB, below the roughly 12 GiB YARN memory of an `m5.xlarge`. This sizing is an estimate, not a measurement.
* Security: `spark.authenticate=true`, `spark.network.crypto.enabled=true`, **`spark.network.crypto.authEngineVersion=1`**, `spark.network.crypto.saslFallback=false`, `spark.io.encryption.enabled=true`. No cipher is set (default AES-CTR) and no `spark.authenticate.secret` (YARN generates a per-application secret). **Disclosure:** the build-engineer observed locally that `authEngineVersion=2` with I/O encryption failed the G1 pipeline twice (`ArrayIndexOutOfBounds` in `TorrentBroadcast.readBlocks` during the checkpoint read), while version 1 passed the probe and the G1 pipeline with 28/28 tables exact against the baseline. AES-GCM is not used (earlier probe failure; that work was stopped by human decision).
* Class-origin evidence: `-Xlog:class+load=info` on driver and executors. Grep pattern for container stdout: `\[class,load\] (scala\.Predef\$|scala\.collection\.immutable\.List|org\.apache\.spark\.SparkContext) source: `. Build-engineer volume estimate: probe about 4 MB raw, G1 about 10 MB raw (with debug security logging; treat as an upper bound).

The rendered G1 config is the tracked `relocated-g1-config.json` with only the path prefix `/private/tmp/sc-runtime-test-20261103` replaced by `/mnt/scholarchain`; a mock test compares every other field against the template. The checkpoint directory therefore lives on EFS (`/mnt/scholarchain/checkpoints/g1-portable`).

## Termination layers

1. **Steps then terminate.** `keep_job_flow_alive_when_no_steps = false`: when the last step ends the cluster ends.
2. **`TERMINATE_CLUSTER` on step failure.** The `collect` step terminates the cluster if it fails. `probe` and `g1` use `CONTINUE` so a failed G1 still lets `collect` copy whatever exists. Every step is bounded by `timeout` (1200 s, 3000 s, 600 s; `run-step.sh` adds a 60 s kill-after), and a precondition requires the three timeouts plus the startup allowance and a 10 minute margin to fit inside `max_cluster_minutes`.
3. **Node shutdown timer.** The first action of `bootstrap.sh`, before any download, is `sudo shutdown -h +N`, with `N = max_cluster_minutes - minutes already up - startup allowance (5)`, at least 1. If the timer cannot be armed the bootstrap fails. See the semantics below: this layer is best-effort.
4. **EMR auto-termination.** `auto_termination_policy.idle_timeout = 900` seconds (above the 600 s collect timeout so a running non-YARN collect step is not judged idle). EMR documents its idle criteria, including "no pending steps"; the metrics collector needs outbound access, which the NAT provides, and **the instance profile needs `elasticmapreduce:Get/Put/RemoveAutoTerminationPolicy`** (granted here and in the boundary; per AWS re:Post https://repost.aws/knowledge-center/emr-troubleshoot-cluster-termination the cluster otherwise stays up after the timeout). Source: <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-auto-termination-policy.html>.

The guarantee is the same-session `terraform destroy` followed by `scripts/phase12d-spike/inventory.sh`. None of the four layers deletes the NAT gateway, EIP, EFS, bucket or key.

### Shutdown-timer semantics

*Question:* does `shutdown -h` on an EMR primary or core node end the EC2 instance and the cluster, or leave a stopped node that keeps billing, or trigger a replacement?

*Findings from AWS documentation (consulted 2026-11-03):*

* EC2 does not terminate on an OS shutdown unless told to. "By default, when you initiate a shutdown from an Amazon EBS backed instance ... the instance stops." The `InstanceInitiatedShutdownBehavior` attribute chooses `stop` or `terminate` and applies only to a shutdown from the OS. "The halt command doesn't initiate a shutdown", so the timer uses `shutdown`, not `halt`. <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_ChangingInstanceInitiatedShutdownBehavior.html>
* No document found says what value EMR sets for that attribute on the instances it launches. The node therefore probably *stops* rather than terminates, which is not established.
* EMR treats a stopped primary as fatal. "When the Amazon EMR cluster primary node stops for any reason, the cluster terminates", and "stopping the Amazon EMR primary or all core nodes leads to cluster termination". <https://repost.aws/knowledge-center/emr-cluster-terminated-unexpectedly> With one core node, a stopped core is "all core nodes". With termination protection off (as here), cluster termination follows. "When Amazon EMR shuts down your cluster, all Amazon EC2 instances in the cluster shut down" (<https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-termination.html>), but that page does not say stopped instances are terminated rather than left stopped.
* Not established by any document found: how quickly EMR detects a stopped node, whether EMR then *terminates* (rather than leaves stopped) the instance and its EBS volumes, and whether `unhealthy_node_replacement` (off here) changes the core case.

*Conclusion:* the documentation supports "`shutdown -h` on the primary or the only core node leads to EMR terminating the cluster" but does not establish the timing, or that every instance and EBS volume is deleted. **The timer is best-effort. The other layers and, above all, the same-session `terraform destroy` plus the inventory are the guarantees.**

## Disclosed limitations

* **No in-transit TLS for Hadoop/YARN RPC** inside the single private subnet (human decision to drop the PEM/TLS artifacts). Spark's own RPC is authenticated and AES-CTR encrypted, but YARN RPC and ResourceManager/NodeManager traffic are not; Spark's per-application secret distribution relies on YARN RPC protection (Apache Spark security documentation). The security configuration has `EnableInTransitEncryption = false`.
* AES-GCM and `authEngineVersion=2` are not used (see above).
* **Hadoop client mismatch:** the portable runtime carries Hadoop 3.3.4 client libraries while EMR 7.8.0 runs Hadoop 3.4.1 / YARN. Compatibility is exactly what the probe tests; it is not established.
* Single core node: driver/AM and both executors share one host (separate JVMs), so the probe proves cross-JVM but not cross-host executor behaviour. The primary only runs the client and the ResourceManager.
* The S3 gateway endpoint uses the default policy.
* `aws_emr_cluster` quirks: the provider waits for `RUNNING` or `WAITING`. A transient cluster that reaches `TERMINATING` before the provider polls it can make `apply` report an error although the cluster ran. Steps are `ForceNew` in the provider, hence `ignore_changes = [step]`; the cluster is single-use.
* The default security group is left unmanaged with the AWS default rules (human decision); it carries no spike tags and is deleted with the VPC.
* The service-linked roles for EMR cleanup and EFS must exist or be creatable.
* The bootstrap installs `amazon-efs-utils` with `dnf` through the NAT; a repository outage fails the bootstrap and ends the attempt.

## S3 request model

`scripts/phase12d-spike/request_bound.py` computes the per-attempt upper bound from `scripts/phase12d-spike/request-manifest.json` and fails if a staged object is added to Terraform without updating the manifest. The provider uploads through the AWS SDK for Go v2 s3 manager (symbols `feature/s3/manager.Uploader.Upload` and `internal/service/s3.resourceObjectUpload` seen with `strings` on the provider binary), whose default part size is 5 MiB (the SDK default, not read from the binary). The bound therefore uses 5 MiB parts for Terraform uploads, 8 MiB (AWS CLI default) for node downloads and the collect upload, a retry multiplier of 3, and a stated, unverified assumption for the EMR log pusher. Run the script for the numbers.

## Cost drivers that outlast the cluster (no prices given here)

Quantities that keep accruing per unit of time if the teardown is skipped or partial: NAT gateway hours plus its EIP hours (a public IPv4 address is charged per hour), EFS storage per GB-month (Elastic throughput also bills reads and writes), S3 storage and requests, the KMS key per month while not in `PendingDeletion` (the inventory reports a `PendingDeletion` key as expected-retained), and any EBS volume or instance left stopped by the node timer. The coordinator prices these.

## Commands for the later gated session (placeholders only, none run now)

```
export AWS_REGION=us-east-2
scripts/phase12d-spike/preflight.sh --account <ACCOUNT_ID> --role scholarchain-deployer
terraform -chdir=infra/terraform/spikes/emr-spark-isolated init
terraform -chdir=infra/terraform/spikes/emr-spark-isolated plan -var-file=<PRIVATE_TFVARS> -out=<PLAN_FILE>
#   the human reviews the plan and records approval; a reviewed plan is not approval to apply
<apply the reviewed plan file, under the recorded gate>
aws emr describe-cluster --cluster-id <CLUSTER_ID> --query Cluster.Status.State   # bounded repeats; one 'aws emr wait cluster-terminated' call polls for about 30 minutes at most
scripts/phase12d-spike/collect-evidence.sh --bucket <BUCKET> --dest <EVIDENCE_DIR>
<destroy the same root with the same variables, in the same session>
scripts/phase12d-spike/inventory.sh --account <ACCOUNT_ID> --out <INVENTORY_JSON>
```

Evidence must be collected **before** the destroy, which force-deletes the bucket.

## Offline verification

```
export TF_CLI_CONFIG_FILE=<offline mirror tfrc>
export TF_DATA_DIR=<scratch dir>
R=infra/terraform/spikes/emr-spark-isolated
terraform -chdir=$R init -backend=false
terraform -chdir=$R fmt -check -recursive
terraform -chdir=$R validate
terraform -chdir=$R test        # mock_provider only
```

`tests/fixtures/*.bin` are tiny stand-ins so the checksum validation can run without the 321 MB runtime; they are not the runtime. The lock file pins `hashicorp/aws 6.44.0` with the offline mirror's darwin_arm64 hash only.

## Documentation relied on

* <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-man-sec-groups.html> (private-subnet managed security group rules)
* <https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonEMRServicePolicy_v2.html> and <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-managed-iam-policies.html> (tag requirement, PassRole limited to `EMR_EC2_DefaultRole`)
* <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-encryption-enable.html> (KMS permissions for the service and instance roles)
* <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-auto-termination-policy.html>
* <https://repost.aws/knowledge-center/emr-spark-classnotfoundexception> (Java 17 notes; its Corretto path proved wrong on EMR 7.8.0 in live attempt 3)
* <https://repost.aws/knowledge-center/emr-cluster-terminated-unexpectedly>, <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_ChangingInstanceInitiatedShutdownBehavior.html>, <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-termination.html> (shutdown semantics)

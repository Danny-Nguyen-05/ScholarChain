variable "name_prefix" { type = string }

# Decision 12-10 (EMR emr-7.8.0, applications ["Hadoop"] only, portable Spark 3.5.4 / Scala 2.13.14 runtime on Java 17),
# 13C TLS decision (in-transit TLS off, at-rest encryption on), G2 (shuffle tracking), G3 (task nodes and managed scaling
# off by default), G5 (runtime archive read from an S3 URI with a pinned sha256). Values come from tfvars; every bound
# below is validated. The G6 bounds mirror scripts/config/release.conf and emr-pricing.conf and are cross-checked by
# tests/phase13c.tftest.hcl, so a cap cannot drift above USD 3 per run.
variable "config" {
  type = object({
    enabled           = optional(bool, false)
    release_label     = optional(string, "emr-7.8.0")
    runtime_reference = optional(string)
    runtime_verified  = optional(bool, false)

    # Bootstrap action (scripts/emr/bootstrap.sh), uploaded by a human in Phase 14.
    bootstrap_uri    = optional(string)
    bootstrap_sha256 = optional(string)
    # G5: the portable runtime archive, uploaded by a human in Phase 14; the bootstrap verifies the hash before extracting.
    runtime_archive_uri    = optional(string)
    runtime_archive_sha256 = optional(string, "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5")
    job_jar_uri            = optional(string)
    job_jar_sha256         = optional(string)
    # Step scripts and config the bootstrap verifies and installs (item 8). dest must be under an allowed directory.
    extra_artifacts = optional(list(object({ uri = string, sha256 = string, dest = string })), [])

    # instance_type is the core (and task) node type. The primary (master) node has its own type: Phase 15 D3 (human decision,
    # docs/agent-runs/phase-15/prompt.md, "D3 decision" and "S run cap and D3 go-ahead", 2026-11-16): r5.xlarge (32 GiB, 4 vCPU),
    # because the entity-resolution step is a single JVM on the PRIMARY node (scripts/emr/sc-step.sh) that needs a 12g heap
    # (P6: 8g OOM, RSS 13.9 GB at 12g), which a 16 GiB m5.xlarge primary cannot hold with headroom. Spark executors run on core.
    instance_type         = optional(string, "m5.xlarge")
    primary_instance_type = optional(string, "r5.xlarge")
    # G3: task nodes and managed scaling are OFF unless tfvars turn them on, within the caps below.
    max_task_nodes               = optional(number, 0)
    task_node_count              = optional(number, 0)
    managed_scaling_enabled      = optional(bool, false)
    managed_scaling_max_capacity = optional(number, 1)

    idle_timeout_seconds      = optional(number, 900)
    node_deadline_minutes     = optional(number, 240)
    startup_allowance_minutes = optional(number, 5)
    ebs_size_gb               = optional(number, 32)
    ebs_iops                  = optional(number, 3000)
    ebs_throughput            = optional(number, 125)
    # Value of the scholarchain:stack tag that propagates to every instance and ENI (carried item 17).
    stack_tag_value = optional(string, "main-emr")
  })
  default = {}

  validation {
    condition     = var.config.release_label == "emr-7.8.0"
    error_message = "Decision 12-10 is proven only on emr-7.8.0; the release label is pinned."
  }
  validation {
    condition     = var.config.instance_type == "m5.xlarge"
    error_message = "Only m5.xlarge keeps the smallest cluster (primary + core) inside the USD 3 per-run cap at the maximum runtime plus idle tail (G6); m5.2xlarge would not."
  }
  validation {
    # D3: exactly the reviewed pair. Primary m5.xlarge or r5.xlarge; the core (and task) type stays pinned to m5.xlarge above.
    # G6 at r5.xlarge: the largest allowed cluster (r5 primary 0.315 + core and one task m5 0.240 each, USD per hour) costs
    # 0.795 x (180 min + 900 s) = USD 2.58, inside the USD 3 per-run cap; tests/phase15_emr_primary.tftest.hcl derives it.
    condition     = contains(["m5.xlarge", "r5.xlarge"], var.config.primary_instance_type)
    error_message = "D3: the primary instance type must be r5.xlarge (the reviewed default) or m5.xlarge; no other type has a reviewed rate and cap check."
  }
  validation {
    condition     = floor(var.config.max_task_nodes) == var.config.max_task_nodes && var.config.max_task_nodes >= 0 && var.config.max_task_nodes <= 1
    error_message = "G3/G6: at most one task node. Two would make four m5.xlarge instances, which cost USD 3.12 at 180 minutes plus the 900 s idle tail, above the USD 3 per-run cap."
  }
  validation {
    condition     = floor(var.config.task_node_count) == var.config.task_node_count && var.config.task_node_count >= 0 && var.config.task_node_count <= var.config.max_task_nodes
    error_message = "task_node_count must be a whole number from 0 to max_task_nodes (default 0)."
  }
  validation {
    condition     = !var.config.managed_scaling_enabled || var.config.max_task_nodes > 0
    error_message = "Managed scaling needs max_task_nodes > 0; with no task nodes there is nothing to scale."
  }
  validation {
    condition     = floor(var.config.managed_scaling_max_capacity) == var.config.managed_scaling_max_capacity && var.config.managed_scaling_max_capacity >= 1 && var.config.managed_scaling_max_capacity <= 1 + var.config.max_task_nodes
    error_message = "managed_scaling_max_capacity counts core plus task instances: 1 to 1 + max_task_nodes."
  }
  validation {
    condition     = floor(var.config.idle_timeout_seconds) == var.config.idle_timeout_seconds && var.config.idle_timeout_seconds >= 60 && var.config.idle_timeout_seconds <= 900
    error_message = "Auto-termination idle timeout must be 60 to 900 s (carried finding B3; the same cap as PIPELINE_MAX_IDLE_TIMEOUT_SECONDS)."
  }
  validation {
    condition     = floor(var.config.node_deadline_minutes) == var.config.node_deadline_minutes && var.config.node_deadline_minutes >= 60 && var.config.node_deadline_minutes <= 240
    error_message = "The node shutdown deadline is 60 to 240 minutes (best effort; four hours of three m5.xlarge nodes is USD 2.88)."
  }
  validation {
    condition     = floor(var.config.startup_allowance_minutes) == var.config.startup_allowance_minutes && var.config.startup_allowance_minutes >= 1 && var.config.startup_allowance_minutes <= 20
    error_message = "startup_allowance_minutes must be 1 to 20."
  }
  validation {
    condition     = var.config.ebs_size_gb >= 32 && var.config.ebs_size_gb <= 128 && var.config.ebs_iops == 3000 && var.config.ebs_throughput == 125
    error_message = "EBS is gp3 32-128 GiB at the baseline 3000 IOPS and 125 MiB/s (no provisioned performance surcharge)."
  }
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,39}$", var.config.stack_tag_value))
    error_message = "stack_tag_value must be 3-40 lowercase letters, digits or hyphens."
  }
  validation {
    condition     = alltrue([for h in [var.config.bootstrap_sha256, var.config.runtime_archive_sha256, var.config.job_jar_sha256] : h == null || can(regex("^[0-9a-f]{64}$", h))]) && alltrue([for a in var.config.extra_artifacts : can(regex("^[0-9a-f]{64}$", a.sha256))])
    error_message = "Every sha256 must be 64 lowercase hex characters."
  }
  validation {
    condition     = var.config.runtime_archive_sha256 == "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5"
    error_message = "Carried finding C2: the runtime archive sha256 must equal the decision 12-10 pin (RUNTIME_ARCHIVE_EXPECTED_SHA256 in scripts/config/release.conf). A different hash would install a different runtime; the class-origin check would only notice at run time, after spend."
  }
  validation {
    condition     = alltrue([for u in concat([for x in [var.config.bootstrap_uri, var.config.runtime_archive_uri, var.config.job_jar_uri] : x if x != null], [for a in var.config.extra_artifacts : a.uri]) : can(regex("^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]/[A-Za-z0-9._/=+@-]+$", u))])
    error_message = "Every artifact reference must be a plain s3://bucket/key URI."
  }
  validation {
    condition     = alltrue([for a in var.config.extra_artifacts : can(regex("^/(opt/scholarchain-runtime|opt/scholarchain-spike/bin|mnt/scholarchain/config)/[A-Za-z0-9_.+/-]+$", a.dest)) && !strcontains(a.dest, "..") && !strcontains(a.dest, "//")])
    error_message = "extra_artifacts dest must be under /opt/scholarchain-runtime/, /opt/scholarchain-spike/bin/ or /mnt/scholarchain/config/ (no '..')."
  }
}

# Paths on the nodes: exactly the pinned values of scripts/config/release.conf (PIPELINE_RUNTIME_DIR, PIPELINE_JOB_JAR_PATH,
# PIPELINE_JAVA_HOME_FILE, PIPELINE_EFS_MOUNT, PIPELINE_STEP_BIN_DIR, the directory of the installed EMR step programs). tests/phase13c.tftest.hcl compares them with that file.
variable "node_paths" {
  type = object({
    runtime_dir    = optional(string, "/opt/scholarchain-runtime")
    job_jar_path   = optional(string, "/opt/scholarchain-runtime/application/scholarchain-job.jar")
    java_home_file = optional(string, "/opt/scholarchain-spike/java-home")
    step_bin_dir   = optional(string, "/opt/scholarchain-spike/bin")
    efs_mount      = optional(string, "/mnt/scholarchain")
    efs_root_dir   = optional(string, "/scholarchain-emr")
    efs_uid        = optional(number, 1500)
    efs_gid        = optional(number, 1500)
  })
  default = {}
  validation {
    condition     = alltrue([for p in [var.node_paths.runtime_dir, var.node_paths.job_jar_path, var.node_paths.java_home_file, var.node_paths.step_bin_dir, var.node_paths.efs_mount, var.node_paths.efs_root_dir] : can(regex("^/[A-Za-z0-9_.+/-]+$", p)) && !strcontains(p, "..")]) && startswith(var.node_paths.job_jar_path, "${var.node_paths.runtime_dir}/")
    error_message = "Node paths must be absolute plain paths without '..', and the job jar must lie under the runtime directory."
  }
}

# Decision 12-10 Spark settings, rendered into the node-local spark-defaults.conf by the bootstrap. The reviewed copy the
# scripts read is scripts/config/spark-12-10.conf; tests/phase13c.tftest.hcl FAILS when the two differ. JAVA_HOME entries are
# NOT here: the bootstrap resolves Java 17 on each node. Run-specific keys (yarn tags, staging dir, max executors) are set by
# the pipeline step.
variable "spark_defaults" {
  type = map(string)
  default = {
    # Classpath: the custom runtime only, never the stock EMR Spark or Hadoop classpath.
    "spark.yarn.jars"                    = "local:/opt/scholarchain-runtime/jars/*"
    "spark.yarn.populateHadoopClasspath" = "false"
    # G1 option (ii): no S3 filesystem in the runtime, so the default file system is the local/EFS path.
    "spark.hadoop.fs.defaultFS" = "file:///"
    # EMR's node configuration lists the LZO codecs, which the runtime does not ship (live attempt 4).
    "spark.hadoop.io.compression.codecs" = "org.apache.hadoop.io.compress.GzipCodec,org.apache.hadoop.io.compress.DefaultCodec,org.apache.hadoop.io.compress.BZip2Codec,org.apache.hadoop.io.compress.SnappyCodec"
    # Spark authentication, AES-CTR network encryption (authEngineVersion=1; AES-GCM is not used) and IO encryption.
    "spark.authenticate"                     = "true"
    "spark.network.crypto.enabled"           = "true"
    "spark.network.crypto.authEngineVersion" = "1"
    "spark.network.crypto.saslFallback"      = "false"
    "spark.io.encryption.enabled"            = "true"
    # G2: a Hadoop-only cluster has no Spark shuffle service, so dynamic allocation tracks shuffle files instead.
    "spark.dynamicAllocation.enabled"                 = "true"
    "spark.dynamicAllocation.shuffleTracking.enabled" = "true"
    "spark.shuffle.service.enabled"                   = "false"
    "spark.dynamicAllocation.minExecutors"            = "1"
    # Executor and driver sizing proven on m5.xlarge in the spike.
    "spark.executor.cores"  = "1"
    "spark.executor.memory" = "3g"
    "spark.driver.cores"    = "1"
    "spark.driver.memory"   = "3g"
    # Bounded, predictable failure behaviour.
    "spark.task.maxFailures"    = "1"
    "spark.yarn.maxAppAttempts" = "1"
    "spark.ui.enabled"          = "false"
    # Class-origin evidence in the driver and executor stdout.
    "spark.driver.extraJavaOptions"   = "-Xlog:class+load=info"
    "spark.executor.extraJavaOptions" = "-Xlog:class+load=info"
  }
  validation {
    condition = alltrue([for k, v in {
      "spark.yarn.jars"                                 = "local:${var.node_paths.runtime_dir}/jars/*"
      "spark.yarn.populateHadoopClasspath"              = "false"
      "spark.hadoop.fs.defaultFS"                       = "file:///"
      "spark.authenticate"                              = "true"
      "spark.network.crypto.enabled"                    = "true"
      "spark.network.crypto.authEngineVersion"          = "1"
      "spark.network.crypto.saslFallback"               = "false"
      "spark.io.encryption.enabled"                     = "true"
      "spark.dynamicAllocation.enabled"                 = "true"
      "spark.dynamicAllocation.shuffleTracking.enabled" = "true"
      "spark.shuffle.service.enabled"                   = "false"
    } : lookup(var.spark_defaults, k, null) == v])
    error_message = "Decision 12-10 requires: yarn.jars on the local runtime, populateHadoopClasspath=false, defaultFS file:///, spark.authenticate, AES-CTR (authEngineVersion=1, no SASL fallback), IO encryption and G2 shuffle tracking without an external shuffle service."
  }
  validation {
    condition     = !strcontains(lower(lookup(var.spark_defaults, "spark.hadoop.io.compression.codecs", "lzo")), "lzo") && contains(keys(var.spark_defaults), "spark.hadoop.io.compression.codecs")
    error_message = "The codec list must be set and must not name an LZO codec."
  }
  validation {
    condition     = alltrue([for k in keys(var.spark_defaults) : !contains(["spark.yarn.appMasterEnv.JAVA_HOME", "spark.executorEnv.JAVA_HOME", "spark.yarn.stagingDir", "spark.yarn.tags", "spark.dynamicAllocation.maxExecutors"], k) && startswith(k, "spark.") && !can(regex("[\\s=:]", k))])
    error_message = "JAVA_HOME (resolved on each node), the staging directory, the YARN tags and maxExecutors are set outside this map; keys must be plain spark.* names."
  }
  validation {
    condition     = alltrue([for k, v in var.spark_defaults : can(regex("^[^\\r\\n\\\\]+$", v))])
    error_message = "Spark values must be single-line and hold no backslash (a properties line continuation)."
  }
}

variable "kms_key_arn" { type = string }
variable "log_bucket" { type = string }
variable "artifacts_bucket" {
  type        = string
  description = "Name of the project artifacts bucket. Every artifact URI must lie in it: the EMR instance role reads exactly that bucket (identity module emr_data policy). The root guard (terraform_data.phase12b_guard) enforces that every artifact URI starts with s3://<this bucket>/ (a module-level check would fire twice and cannot be expected by a test)."
}
variable "aws_region" { type = string }
variable "aws_account_id" { type = string }
variable "vpc_id" { type = string }
variable "subnet_id" { type = string }
variable "security_group_id" { type = string }
variable "service_access_group_id" { type = string }
variable "instance_profile_arn" { type = string }
variable "instance_role_arn" { type = string }
variable "instance_role_name" { type = string }
variable "service_role_arn" { type = string }
variable "tags" { type = map(string) }

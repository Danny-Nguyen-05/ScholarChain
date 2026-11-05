provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = local.default_tags
  }
}

locals {
  default_tags = {
    course                                     = var.course
    project                                    = "ScholarChain"
    environment                                = "spike"
    owner                                      = var.owner
    expiration                                 = var.expiration_date
    "scholarchain:stack"                       = "spike-emr"
    "for-use-with-amazon-emr-managed-policies" = "true"
  }

  prefix      = "scholarchain-spike-emr"
  bucket_name = "${local.prefix}-${var.account_id}-${var.region}"

  # Paths on the nodes.
  mnt          = "/mnt/scholarchain"
  runtime_dir  = "/opt/scholarchain-runtime"
  spike_bin    = "/opt/scholarchain-spike/bin"
  job_jar      = "${local.runtime_dir}/application/scholarchain-job.jar"
  spark_submit = "${local.runtime_dir}/bin/spark-submit"

  # Dedicated POSIX identity enforced by the EFS access point.
  efs_uid      = 1500
  efs_gid      = 1500
  efs_root_dir = "/scholarchain-spike"

  # Object keys in the spike bucket.
  key_runtime       = "staging/runtime/scholarchain-runtime.tgz"
  key_inputs        = "staging/inputs/g1-upstream-inputs.tgz"
  key_bootstrap     = "staging/bootstrap/bootstrap.sh"
  key_run_step      = "staging/bin/run-step.sh"
  key_collect       = "staging/bin/collect-results.sh"
  key_g1_config     = "staging/config/spark-g1-portable.json"
  key_spark_default = "staging/config/spark-defaults.conf"

  scripts_dir = "${path.module}/../../../../scripts/phase12d-spike/emr"

  # Relocated G1 config: only the path prefix is rewritten.
  g1_config_rendered = replace(file(var.g1_config_template_path), var.g1_config_source_prefix, local.mnt)

  # Spark defaults placed in $SPARK_HOME/conf/spark-defaults.conf on every node.
  spark_defaults = {
    # Custom runtime, no stock EMR Spark/Hadoop classpath.
    "spark.yarn.jars"                    = "local:${local.runtime_dir}/jars/*"
    "spark.yarn.populateHadoopClasspath" = "false"
    "spark.hadoop.fs.defaultFS"          = "file:///"
    # The EMR node's Hadoop conf lists com.hadoop.compression.lzo.LzoCodec/LzopCodec, which the
    # portable runtime (intentionally) does not contain: the G1 step failed in
    # CompressionCodecFactory with "Compression codec ... LzoCodec not found" (live attempt 4).
    # Override with the four codecs that ARE in hadoop-client-api-3.3.4.jar.
    "spark.hadoop.io.compression.codecs" = "org.apache.hadoop.io.compress.GzipCodec,org.apache.hadoop.io.compress.DefaultCodec,org.apache.hadoop.io.compress.BZip2Codec,org.apache.hadoop.io.compress.SnappyCodec"
    # With fs.defaultFS=file:/// the default staging dir would sit on the
    # primary's local disk, which the ApplicationMaster on the core node cannot
    # localize. EFS is mounted at the same path on both nodes.
    "spark.yarn.stagingDir" = "file://${local.mnt}/staging"
    # spark.yarn.appMasterEnv.JAVA_HOME and spark.executorEnv.JAVA_HOME are NOT set here: the
    # bootstrap resolves Java 17 on each node and appends them to the node-local file.
    "spark.executor.instances"        = "2"
    "spark.executor.cores"            = "1"
    "spark.executor.memory"           = "3g"
    "spark.driver.cores"              = "1"
    "spark.driver.memory"             = "3g"
    "spark.dynamicAllocation.enabled" = "false"
    "spark.shuffle.service.enabled"   = "false"
    "spark.task.maxFailures"          = "1"
    "spark.yarn.maxAppAttempts"       = "1"
    "spark.ui.enabled"                = "false"
    # AES-CTR network crypto (default cipher, cipher key unset). AES-GCM is not used.
    # authEngineVersion=1 per the build-engineer's local runs: version 2 with
    # io encryption failed the G1 pipeline twice (ArrayIndexOutOfBounds in
    # TorrentBroadcast.readBlocks during checkpoint read); version 1 passed the
    # probe and G1 with 28/28 tables exact. spark.authenticate.secret is NOT set:
    # YARN generates a per-application secret.
    "spark.authenticate"                     = "true"
    "spark.network.crypto.enabled"           = "true"
    "spark.network.crypto.authEngineVersion" = "1"
    "spark.network.crypto.saslFallback"      = "false"
    "spark.io.encryption.enabled"            = "true"
    # Class-origin evidence in driver and executor stdout.
    "spark.driver.extraJavaOptions"   = "-Xlog:class+load=info"
    "spark.executor.extraJavaOptions" = "-Xlog:class+load=info"
  }
  spark_defaults_text = "${join("\n", [for k in sort(keys(local.spark_defaults)) : "${k} ${local.spark_defaults[k]}"])}\n"

  step_budget_seconds = var.probe_timeout_seconds + var.g1_timeout_seconds + var.collect_timeout_seconds
  # Minutes the shutdown timer leaves after startup; steps must fit inside it
  # with a 10 minute margin for staging, bootstrap and teardown.
  usable_seconds = (var.max_cluster_minutes - var.startup_allowance_minutes - 10) * 60
}

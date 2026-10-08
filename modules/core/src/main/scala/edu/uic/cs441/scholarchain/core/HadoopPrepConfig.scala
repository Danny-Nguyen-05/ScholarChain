package edu.uic.cs441.scholarchain.core

import upickle.default.ReadWriter

/** Limits for Hadoop preparation. No field has a compiled-in default. This is not a
  * [[ScholarChainConfig]] and does not carry a bucket, endpoint, or account id.
  *
  * `executionMode` is required. The closed wire values are `local` and `cluster`. A missing field
  * fails [[HadoopPrepConfigLoader]]. `local` may use LocalJobRunner. `cluster` must not set
  * `mapreduce.framework.name` to `local`.
  *
  * `maxLocalSampleRecords` is a launch-level bound on accepted input records across the whole
  * launch, not a per-mapper cap. `maxRecordBytes` bounds a record before its full text is
  * materialized. `intermediateCompressionEnabled` means intermediate `FileOutputFormat`
  * compression, not only shuffle compression. `compressionCodec` is `none` when that compression is
  * disabled, and another codec name when it is enabled.
  *
  * `outputRoot` is a caller-supplied local path or an `s3`, `s3a`, or `s3n` URI with a non-empty
  * bucket and key prefix. A bare AWS hostname or endpoint is rejected.
  */
final case class HadoopPrepConfig(
    configSchemaVersion: String,
    maxRecordBytes: Long,
    maxXmlEntityExpansion: Long,
    reducerCount: Int,
    maxCandidateBlockSize: Int,
    maxCandidatePairsPerBlock: Int,
    maxAuthorTeamSize: Int,
    maxLocalSampleRecords: Int,
    outputRoot: String,
    compressionCodec: String,
    intermediateCompressionEnabled: Boolean,
    executionMode: HadoopExecutionMode
) derives ReadWriter {
  def canonicalJson: String = CoreJson.compact(this)

  def fingerprint: String = StableIds.sha256Hex(canonicalJson)
}

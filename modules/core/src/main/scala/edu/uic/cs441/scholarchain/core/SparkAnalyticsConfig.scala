package edu.uic.cs441.scholarchain.core

import upickle.default.ReadWriter

/** Caller-supplied roots and deterministic algorithm settings for one Phase 6 run. */
final case class SparkAnalyticsConfig(
    configSchemaVersion: String,
    hadoopRunRoot: String,
    entityResolutionRunRoot: String,
    outputRoot: String,
    windows: Vector[SparkWindow],
    identityPolicyVersion: String,
    representativePolicyVersion: String,
    graphPolicyVersion: String,
    componentMaxIterations: Int,
    communityMaxIterations: Int,
    kCoreMaxIterations: Int,
    checkpointInterval: Int,
    checkpointDirectory: String,
    maxHops: Int,
    benchmarkPairs: Vector[BenchmarkPair],
    sampledPathPairCount: Int,
    pathSampleSourceCount: Int,
    samplingSeed: Long,
    representativeWorkLimit: Int,
    maxTeamWorkLimit: Int,
    shufflePartitions: Int,
    failOnHardInvariant: Boolean
) derives ReadWriter {
  def canonicalJson: String = CoreJson.compact(this)
  def fingerprint: String = StableIds.sha256Hex(canonicalJson)
}

/** Each endpoint is either a researcher ID or an exact DBLP author name. */
final case class BenchmarkPair(
    left: String,
    right: String,
    endpointKind: String
) derives ReadWriter

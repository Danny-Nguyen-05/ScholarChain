package edu.uic.cs441.scholarchain.core

import java.nio.file.{Files, Path}
import scala.collection.mutable.ArrayBuffer

object SparkAnalyticsConfigLoader {
  private val topFields: Set[String] = Set(
    "configSchemaVersion",
    "hadoopRunRoot",
    "entityResolutionRunRoot",
    "outputRoot",
    "windows",
    "identityPolicyVersion",
    "representativePolicyVersion",
    "graphPolicyVersion",
    "componentMaxIterations",
    "communityMaxIterations",
    "kCoreMaxIterations",
    "checkpointInterval",
    "checkpointDirectory",
    "maxHops",
    "benchmarkPairs",
    "sampledPathPairCount",
    "pathSampleSourceCount",
    "samplingSeed",
    "representativeWorkLimit",
    "maxTeamWorkLimit",
    "shufflePartitions",
    "failOnHardInvariant"
  )
  private val windowFields: Set[String] =
    Set("windowId", "startYear", "endYear", "comparisonOrder")
  private val pairFields: Set[String] = Set("left", "right", "endpointKind")

  def load(path: Path): Either[ConfigError, SparkAnalyticsConfig] =
    if (!Files.isRegularFile(path)) Left(ConfigError(Vector(s"config file not found: $path")))
    else loadText(Files.readString(path))

  def loadText(text: String): Either[ConfigError, SparkAnalyticsConfig] =
    checkShape(text).flatMap(_ =>
      CoreJson
        .parse[SparkAnalyticsConfig](text)
        .left
        .map(error => ConfigError(Vector(s"Spark config JSON parse failed: ${error.message}")))
        .flatMap(validate)
    )

  private def checkShape(text: String): Either[ConfigError, Unit] = {
    val parsed =
      try Right(ujson.read(text))
      catch {
        case error: Throwable =>
          Left(ConfigError(Vector(s"Spark config JSON parse failed: ${error.getMessage}")))
      }
    parsed.flatMap {
      case obj: ujson.Obj =>
        val errors = ArrayBuffer.empty[String]
        obj.value.keys.filterNot(topFields).foreach(key => errors += s"unsupported field: $key")
        def nested(name: String, fields: Set[String]): Unit =
          obj.value.get(name) match {
            case Some(arr: ujson.Arr) =>
              arr.value.foreach {
                case child: ujson.Obj =>
                  child.value.keys
                    .filterNot(fields)
                    .foreach(key => errors += s"unsupported field: $name.$key")
                case _ => () // Typed decoding reports the shape error.
              }
            case _ => ()
          }
        nested("windows", windowFields)
        nested("benchmarkPairs", pairFields)
        if (errors.nonEmpty) Left(ConfigError(errors.toVector)) else Right(())
      case _ => Left(ConfigError(Vector("Spark config root must be a JSON object")))
    }
  }

  def validate(config: SparkAnalyticsConfig): Either[ConfigError, SparkAnalyticsConfig] = {
    val errors = ArrayBuffer.empty[String]
    if (!SchemaVersions.supportedSparkAnalyticsConfig.contains(config.configSchemaVersion))
      errors += s"unsupported Spark config schema version: ${config.configSchemaVersion}"
    Vector(
      "hadoopRunRoot" -> config.hadoopRunRoot,
      "entityResolutionRunRoot" -> config.entityResolutionRunRoot,
      "outputRoot" -> config.outputRoot,
      "checkpointDirectory" -> config.checkpointDirectory
    ).foreach { case (field, path) =>
      if (
        path.trim.isEmpty || path != path.trim || path.exists(ch => ch == '\n' || ch == '\r') ||
        path.contains("${") || path.toLowerCase(java.util.Locale.ROOT).contains("amazonaws.com")
      )
        errors += s"$field must be a non-blank single-line path"
    }
    Vector(
      "identityPolicyVersion" -> config.identityPolicyVersion,
      "representativePolicyVersion" -> config.representativePolicyVersion,
      "graphPolicyVersion" -> config.graphPolicyVersion
    ).foreach { case (field, value) =>
      if (!value.matches("[a-z0-9][a-z0-9._-]{0,63}")) errors += s"$field is invalid"
    }
    Vector(
      "componentMaxIterations" -> config.componentMaxIterations,
      "communityMaxIterations" -> config.communityMaxIterations,
      "kCoreMaxIterations" -> config.kCoreMaxIterations,
      "checkpointInterval" -> config.checkpointInterval,
      "maxHops" -> config.maxHops,
      "pathSampleSourceCount" -> config.pathSampleSourceCount,
      "representativeWorkLimit" -> config.representativeWorkLimit,
      "maxTeamWorkLimit" -> config.maxTeamWorkLimit,
      "shufflePartitions" -> config.shufflePartitions
    ).foreach { case (field, value) =>
      if (value < 1) errors += s"$field must be >= 1"
    }
    if (config.sampledPathPairCount < 0) errors += "sampledPathPairCount must be >= 0"
    if (config.windows.isEmpty) errors += "windows must be nonempty"
    if (config.windows.map(_.windowId).distinct.size != config.windows.size)
      errors += "windowId values must be unique"
    config.windows.foreach { window =>
      if (!window.windowId.matches("[a-z0-9][a-z0-9._-]*"))
        errors += s"invalid windowId: ${window.windowId}"
      window.startYear.foreach(year =>
        if (year < 1 || year > 9999) errors += "window year outside 1..9999"
      )
      window.endYear.foreach(year =>
        if (year < 1 || year > 9999) errors += "window year outside 1..9999"
      )
      if (window.startYear.zip(window.endYear).exists((start, end) => start > end))
        errors += s"reversed window: ${window.windowId}"
      if (window.comparisonOrder.exists(_ < 0)) errors += "comparisonOrder must be >= 0"
    }
    val comparison = config.windows.filter(_.comparisonOrder.nonEmpty).sortBy(_.comparisonOrder.get)
    if (comparison.map(_.comparisonOrder).distinct.size != comparison.size)
      errors += "comparisonOrder values must be unique"
    comparison.sliding(2).foreach {
      case Vector(left, right) =>
        if (
          left.endYear.isEmpty || right.startYear.isEmpty ||
          left.endYear.get.toLong + 1L != right.startYear.get.toLong
        )
          errors += "comparison windows must be consecutive and non-overlapping"
      case _ => ()
    }
    config.benchmarkPairs.foreach { pair =>
      if (
        !Set("researcher-id", "dblp-name").contains(pair.endpointKind) ||
        pair.left.trim.isEmpty || pair.right.trim.isEmpty || pair.left == pair.right
      )
        errors += "benchmark pair has invalid endpoints or endpointKind"
      if (pair.endpointKind == "researcher-id") {
        if (
          StableIds.parseResearcherId(pair.left).isLeft ||
          StableIds.parseResearcherId(pair.right).isLeft
        )
          errors += "benchmark pair researcher IDs are malformed"
      } else if (pair.endpointKind == "dblp-name") {
        val leftId = StableIds.researcherIdFromDblpName(config.identityPolicyVersion, pair.left)
        val rightId = StableIds.researcherIdFromDblpName(config.identityPolicyVersion, pair.right)
        if (leftId.isLeft || rightId.isLeft)
          errors += "benchmark pair DBLP names are malformed"
        else if (leftId == rightId)
          errors += "benchmark pair DBLP names resolve to the same researcher"
      }
    }
    if (errors.nonEmpty) Left(ConfigError(errors.toVector)) else Right(config)
  }
}

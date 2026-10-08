package edu.uic.cs441.scholarchain.core

import java.nio.file.{Files, Path}

import scala.collection.mutable.ArrayBuffer
import scala.util.matching.Regex

/** Loads [[HadoopPrepConfig]] from a JSON object. Missing limits, a missing `executionMode`,
  * non-positive limits, an execution mode other than `local` or `cluster`, and unknown fields fail
  * closed. There is no environment substitution and no compiled-in bucket, endpoint, account,
  * numeric, or execution-mode default. A caller may supply an `s3`, `s3a`, or `s3n` output root
  * when it has a non-empty bucket and key prefix. A bare AWS hostname or endpoint does not. A job
  * must not launch from a `Left` result.
  */
object HadoopPrepConfigLoader {
  private val Placeholder: Regex = "\\$\\{([A-Z][A-Z0-9_]*)\\}".r
  private val CallerS3Root: Regex = "^(?i)(?:s3|s3a|s3n)://([^/\\s]+)/(\\S+)$".r
  private val ExactJsonInteger: Double = (1L << 53).toDouble

  val fields: Vector[String] = Vector(
    "configSchemaVersion",
    "maxRecordBytes",
    "maxXmlEntityExpansion",
    "reducerCount",
    "maxCandidateBlockSize",
    "maxCandidatePairsPerBlock",
    "maxAuthorTeamSize",
    "maxLocalSampleRecords",
    "outputRoot",
    "compressionCodec",
    "intermediateCompressionEnabled",
    "executionMode"
  )

  def load(path: Path): Either[ConfigError, HadoopPrepConfig] =
    if (!Files.isRegularFile(path))
      Left(ConfigError(Vector(s"config file not found: $path")))
    else loadText(Files.readString(path))

  def loadText(text: String): Either[ConfigError, HadoopPrepConfig] = {
    val trimmed = text.trim
    if (!trimmed.startsWith("{"))
      Left(ConfigError(Vector("hadoop prep config must be a JSON object")))
    else {
      val parsed =
        try Right(ujson.read(trimmed))
        catch {
          case error: Throwable =>
            Left(ConfigError(Vector(s"config JSON parse failed: ${error.getMessage}")))
        }
      parsed.flatMap {
        case obj: ujson.Obj => decode(obj)
        case _ => Left(ConfigError(Vector("hadoop prep config root must be a JSON object")))
      }
    }
  }

  def validate(config: HadoopPrepConfig): Either[ConfigError, HadoopPrepConfig] = {
    val errors = ArrayBuffer.empty[String]
    if (!SchemaVersions.supportedHadoopPrep.contains(config.configSchemaVersion))
      errors += s"unsupported hadoop prep schema version: ${config.configSchemaVersion}"
    requirePositiveLong(config.maxRecordBytes, "maxRecordBytes", errors)
    requirePositiveLong(config.maxXmlEntityExpansion, "maxXmlEntityExpansion", errors)
    requirePositiveInt(config.reducerCount, "reducerCount", errors)
    requirePositiveInt(config.maxCandidateBlockSize, "maxCandidateBlockSize", errors)
    requirePositiveInt(config.maxCandidatePairsPerBlock, "maxCandidatePairsPerBlock", errors)
    requirePositiveInt(config.maxAuthorTeamSize, "maxAuthorTeamSize", errors)
    requirePositiveInt(config.maxLocalSampleRecords, "maxLocalSampleRecords", errors)
    requireOutputRoot(config.outputRoot, errors)
    requireCodec(config.compressionCodec, config.intermediateCompressionEnabled, errors)
    requireExecutionMode(config.executionMode, errors)
    if (errors.isEmpty) Right(config) else Left(ConfigError(errors.toVector))
  }

  private def decode(root: ujson.Obj): Either[ConfigError, HadoopPrepConfig] = {
    val errors = ArrayBuffer.empty[String]
    root.value.keys.filterNot(fields.toSet.contains).foreach { key =>
      errors += s"unsupported field: $key"
    }
    val schema = string(root, "configSchemaVersion", errors)
    if (!SchemaVersions.supportedHadoopPrep.contains(schema))
      errors += s"unsupported hadoop prep schema version: $schema"
    val config = HadoopPrepConfig(
      schema,
      positiveLong(root, "maxRecordBytes", errors),
      positiveLong(root, "maxXmlEntityExpansion", errors),
      positiveInt(root, "reducerCount", errors),
      positiveInt(root, "maxCandidateBlockSize", errors),
      positiveInt(root, "maxCandidatePairsPerBlock", errors),
      positiveInt(root, "maxAuthorTeamSize", errors),
      positiveInt(root, "maxLocalSampleRecords", errors),
      outputRoot(root, errors),
      codec(root, errors),
      flag(root, "intermediateCompressionEnabled", errors),
      executionMode(root, errors)
    )
    val codecErrors = ArrayBuffer.empty[String]
    requireCodec(config.compressionCodec, config.intermediateCompressionEnabled, codecErrors)
    val found = errors.toVector ++ codecErrors.toVector
    if (found.nonEmpty) Left(ConfigError(found)) else Right(config)
  }

  private def requirePositiveLong(value: Long, field: String, errors: ArrayBuffer[String]): Unit =
    if (value < 1) errors += s"$field must be a positive integer"

  private def requirePositiveInt(value: Int, field: String, errors: ArrayBuffer[String]): Unit =
    if (value < 1) errors += s"$field must be a positive integer"

  private def requireOutputRoot(value: String, errors: ArrayBuffer[String]): Unit = {
    if (value.trim.isEmpty || value != value.trim)
      errors += "outputRoot must be a non-blank caller-supplied path"
    else if (value.exists(ch => ch == '\n' || ch == '\r'))
      errors += "outputRoot must be a single-line path"
    else if (Placeholder.findFirstIn(value).nonEmpty)
      errors += "outputRoot must not contain an unresolved placeholder"
    else if (incompleteS3Root(value))
      errors += "outputRoot s3 URI must include a non-empty bucket and key prefix"
    else if (awsEndpointOrHostname(value))
      errors += "outputRoot must not be an AWS endpoint or hostname"
  }

  private def requireCodec(
      codec: String,
      enabled: Boolean,
      errors: ArrayBuffer[String]
  ): Unit = {
    if (codec.trim.isEmpty || codec != codec.trim || codec.exists(ch => ch == '\n' || ch == '\r'))
      errors += "compressionCodec must be a non-blank single-line name"
    else if (codec.contains("://") || awsEndpointOrHostname(codec))
      errors += "compressionCodec must not be a URI"
    else if (!enabled && codec != "none")
      errors += "compressionCodec must be none when intermediate compression is disabled"
    else if (enabled && (codec == "none" || codec.length > 200))
      errors += "compressionCodec must name a codec when intermediate compression is enabled"
  }

  private def incompleteS3Root(value: String): Boolean = {
    val lower = value.toLowerCase(java.util.Locale.ROOT)
    val s3Scheme =
      lower.startsWith("s3://") || lower.startsWith("s3a://") || lower.startsWith("s3n://")
    s3Scheme && CallerS3Root.findFirstIn(value).isEmpty
  }

  /** A hostname or `http`/`https` URL whose host is `amazonaws.com`. An `s3://` bucket URI is not
    * an endpoint.
    */
  private def awsEndpointOrHostname(value: String): Boolean = {
    val lower = value.toLowerCase(java.util.Locale.ROOT)
    val withoutScheme =
      if (lower.startsWith("http://") || lower.startsWith("https://"))
        lower.drop(lower.indexOf("://") + 3)
      else lower
    val host = withoutScheme.takeWhile(ch => ch != '/' && ch != '?' && ch != '#')
    host == "amazonaws.com" || host.endsWith(".amazonaws.com")
  }

  private def string(obj: ujson.Obj, name: String, errors: ArrayBuffer[String]): String =
    obj.value.get(name) match {
      case Some(ujson.Str(value)) if value.trim.nonEmpty => value
      case Some(ujson.Str(_)) =>
        errors += s"$name must be non-blank"
        ""
      case Some(other) =>
        errors += s"$name must be a string, found $other"
        ""
      case None =>
        errors += s"missing $name"
        ""
    }

  private def outputRoot(obj: ujson.Obj, errors: ArrayBuffer[String]): String = {
    val value = string(obj, "outputRoot", errors)
    if (value.nonEmpty) requireOutputRoot(value, errors)
    value
  }

  private def codec(obj: ujson.Obj, errors: ArrayBuffer[String]): String =
    string(obj, "compressionCodec", errors)

  private def requireExecutionMode(mode: HadoopExecutionMode, errors: ArrayBuffer[String]): Unit =
    if (!HadoopExecutionMode.wires.contains(mode.wire))
      errors += s"unsupported executionMode: ${mode.wire}"

  /** Missing and unknown modes fail closed. [[HadoopExecutionMode.Local]] below is only a stand-in
    * so the case class can be built after an error has already been recorded. It is not a default
    * for a successful load.
    */
  private def executionMode(obj: ujson.Obj, errors: ArrayBuffer[String]): HadoopExecutionMode =
    obj.value.get("executionMode") match {
      case Some(ujson.Str(value)) =>
        HadoopExecutionMode.values.find(_.wire == value) match {
          case Some(mode) => mode
          case None =>
            errors += s"unsupported executionMode: $value"
            HadoopExecutionMode.Local
        }
      case Some(other) =>
        errors += s"executionMode must be a string, found $other"
        HadoopExecutionMode.Local
      case None =>
        errors += "missing executionMode"
        HadoopExecutionMode.Local
    }

  private def flag(obj: ujson.Obj, name: String, errors: ArrayBuffer[String]): Boolean =
    obj.value.get(name) match {
      case Some(bool: ujson.Bool) => bool.value
      case Some(other) =>
        errors += s"$name must be a boolean, found $other"
        false
      case None =>
        errors += s"missing $name"
        false
    }

  private def positiveLong(obj: ujson.Obj, name: String, errors: ArrayBuffer[String]): Long =
    obj.value.get(name) match {
      case Some(ujson.Num(value)) if value.isWhole && value >= 1.0 && value <= ExactJsonInteger =>
        value.toLong
      case Some(ujson.Num(_)) =>
        errors += s"$name must be a positive integer"
        0L
      case Some(other) =>
        errors += s"$name must be a positive integer, found $other"
        0L
      case None =>
        errors += s"missing $name"
        0L
    }

  private def positiveInt(obj: ujson.Obj, name: String, errors: ArrayBuffer[String]): Int =
    obj.value.get(name) match {
      case Some(ujson.Num(value))
          if value.isWhole && value >= 1.0 && value <= Int.MaxValue.toDouble =>
        value.toInt
      case Some(ujson.Num(_)) =>
        errors += s"$name must be a positive integer"
        0
      case Some(other) =>
        errors += s"$name must be a positive integer, found $other"
        0
      case None =>
        errors += s"missing $name"
        0
    }
}

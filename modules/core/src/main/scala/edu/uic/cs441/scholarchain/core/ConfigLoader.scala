package edu.uic.cs441.scholarchain.core

import java.nio.file.{Files, Path}

import scala.collection.mutable.Builder
import scala.util.matching.Regex

/** Configuration precedence, highest first:
  *   1. Direct `SCHOLARCHAIN_*` environment overrides listed in `Overrides`. Bridge parameters use
  *      `SCHOLARCHAIN_GRAPH_BRIDGE_PARAM_<NAME>`, and the suffix is the parameter name. 2.
  *      `${ENV_NAME}` placeholders in file strings. `ENV_NAME` matches `[A-Z][A-Z0-9_]*`. 3.
  *      Literal values in the versioned configuration file. 4. No compiled-in AWS account id,
  *      bucket, endpoint, threshold, model id, graph window, or bridge parameter. A missing
  *      required value is a load error.
  *
  * The file is JSON. JSON is valid HOCON, and ujson reads that JSON profile. YAML and non-JSON
  * HOCON syntax are rejected. The versioned .conf resource contains only this JSON subset. This
  * loader does not implement general HOCON substitutions, includes, or YAML parsing.
  *
  * `.env` files, JVM system properties, and remote parameter stores are not read. `loadConfigured`
  * takes the file path from `SCHOLARCHAIN_CONFIG`.
  */
object ConfigLoader {
  private type ErrorLog = Builder[String, Vector[String]]

  private val Placeholder: Regex = "\\$\\{([A-Z][A-Z0-9_]*)\\}".r
  private val AccountId: Regex = "^[0-9]{12}$".r

  final case class Override(path: Vector[String], env: String, kind: ValueKind)

  enum ValueKind {
    case Text
    case WholeNumber
    case Decimal
    case OptionalAccount
  }

  val Overrides: Vector[Override] = Vector(
    Override(
      Vector("application", "environment"),
      "SCHOLARCHAIN_APPLICATION_ENVIRONMENT",
      ValueKind.Text
    ),
    Override(Vector("application", "region"), "SCHOLARCHAIN_APPLICATION_REGION", ValueKind.Text),
    Override(
      Vector("application", "awsAccountId"),
      "SCHOLARCHAIN_APPLICATION_AWS_ACCOUNT_ID",
      ValueKind.OptionalAccount
    ),
    Override(Vector("storage", "rawBucket"), "SCHOLARCHAIN_STORAGE_RAW_BUCKET", ValueKind.Text),
    Override(
      Vector("storage", "curatedBucket"),
      "SCHOLARCHAIN_STORAGE_CURATED_BUCKET",
      ValueKind.Text
    ),
    Override(Vector("storage", "graphBucket"), "SCHOLARCHAIN_STORAGE_GRAPH_BUCKET", ValueKind.Text),
    Override(Vector("storage", "ragBucket"), "SCHOLARCHAIN_STORAGE_RAG_BUCKET", ValueKind.Text),
    Override(Vector("neptune", "endpoint"), "SCHOLARCHAIN_NEPTUNE_ENDPOINT", ValueKind.Text),
    Override(Vector("neptune", "port"), "SCHOLARCHAIN_NEPTUNE_PORT", ValueKind.WholeNumber),
    Override(
      Vector("neptune", "queryTimeoutMs"),
      "SCHOLARCHAIN_NEPTUNE_QUERY_TIMEOUT_MS",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("s3Vectors", "vectorBucket"),
      "SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET",
      ValueKind.Text
    ),
    Override(
      Vector("s3Vectors", "indexes", "researchers"),
      "SCHOLARCHAIN_S3_VECTORS_INDEX_RESEARCHERS",
      ValueKind.Text
    ),
    Override(
      Vector("s3Vectors", "indexes", "communities"),
      "SCHOLARCHAIN_S3_VECTORS_INDEX_COMMUNITIES",
      ValueKind.Text
    ),
    Override(
      Vector("s3Vectors", "indexes", "abstracts"),
      "SCHOLARCHAIN_S3_VECTORS_INDEX_ABSTRACTS",
      ValueKind.Text
    ),
    Override(
      Vector("s3Vectors", "indexes", "paths"),
      "SCHOLARCHAIN_S3_VECTORS_INDEX_PATHS",
      ValueKind.Text
    ),
    Override(
      Vector("s3Vectors", "indexes", "topicInstitutions"),
      "SCHOLARCHAIN_S3_VECTORS_INDEX_TOPIC_INSTITUTIONS",
      ValueKind.Text
    ),
    Override(
      Vector("entityResolution", "policyVersion"),
      "SCHOLARCHAIN_ENTITY_RESOLUTION_POLICY_VERSION",
      ValueKind.Text
    ),
    Override(
      Vector("entityResolution", "acceptThreshold"),
      "SCHOLARCHAIN_ENTITY_RESOLUTION_ACCEPT_THRESHOLD",
      ValueKind.Decimal
    ),
    Override(
      Vector("entityResolution", "rejectThreshold"),
      "SCHOLARCHAIN_ENTITY_RESOLUTION_REJECT_THRESHOLD",
      ValueKind.Decimal
    ),
    Override(
      Vector("entityResolution", "llmBandMin"),
      "SCHOLARCHAIN_ENTITY_RESOLUTION_LLM_BAND_MIN",
      ValueKind.Decimal
    ),
    Override(
      Vector("entityResolution", "llmBandMax"),
      "SCHOLARCHAIN_ENTITY_RESOLUTION_LLM_BAND_MAX",
      ValueKind.Decimal
    ),
    Override(
      Vector("graph", "windowStartYear"),
      "SCHOLARCHAIN_GRAPH_WINDOW_START_YEAR",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("graph", "windowEndYear"),
      "SCHOLARCHAIN_GRAPH_WINDOW_END_YEAR",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("graph", "bridgeAlgorithm"),
      "SCHOLARCHAIN_GRAPH_BRIDGE_ALGORITHM",
      ValueKind.Text
    ),
    Override(
      Vector("retrieval", "graphLimit"),
      "SCHOLARCHAIN_RETRIEVAL_GRAPH_LIMIT",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("retrieval", "vectorLimit"),
      "SCHOLARCHAIN_RETRIEVAL_VECTOR_LIMIT",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("retrieval", "contextTokenBudget"),
      "SCHOLARCHAIN_RETRIEVAL_CONTEXT_TOKEN_BUDGET",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("retrieval", "fusionPolicyVersion"),
      "SCHOLARCHAIN_RETRIEVAL_FUSION_POLICY_VERSION",
      ValueKind.Text
    ),
    Override(
      Vector("retrieval", "maxPathDepth"),
      "SCHOLARCHAIN_RETRIEVAL_MAX_PATH_DEPTH",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("models", "embeddingModel"),
      "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL",
      ValueKind.Text
    ),
    Override(
      Vector("models", "synthesisModel"),
      "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL",
      ValueKind.Text
    ),
    Override(
      Vector("models", "verificationModel"),
      "SCHOLARCHAIN_MODELS_VERIFICATION_MODEL",
      ValueKind.Text
    ),
    Override(
      Vector("operations", "synchronousDeadlineMs"),
      "SCHOLARCHAIN_OPERATIONS_SYNCHRONOUS_DEADLINE_MS",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("operations", "maxWorkflowRetries"),
      "SCHOLARCHAIN_OPERATIONS_MAX_WORKFLOW_RETRIES",
      ValueKind.WholeNumber
    ),
    Override(
      Vector("operations", "maxConcurrentLlmCalls"),
      "SCHOLARCHAIN_OPERATIONS_MAX_CONCURRENT_LLM_CALLS",
      ValueKind.WholeNumber
    )
  )

  def loadConfigured(
      env: Map[String, String] = sys.env
  ): Either[ConfigError, ScholarChainConfig] =
    env.get("SCHOLARCHAIN_CONFIG") match {
      case Some(path) if path.trim.nonEmpty => load(Path.of(path), env)
      case _ =>
        Left(ConfigError(Vector("SCHOLARCHAIN_CONFIG is required and must point at a config file")))
    }

  def load(path: Path, env: Map[String, String]): Either[ConfigError, ScholarChainConfig] =
    if (!Files.isRegularFile(path))
      Left(ConfigError(Vector(s"config file not found: $path")))
    else loadText(Files.readString(path), env)

  def loadText(text: String, env: Map[String, String]): Either[ConfigError, ScholarChainConfig] = {
    val trimmed = text.trim
    if (!trimmed.startsWith("{"))
      Left(ConfigError(Vector(unsupportedDocument)))
    else {
      val parsed =
        try Right(ujson.read(trimmed))
        catch {
          case error: Throwable =>
            Left(ConfigError(Vector(s"config JSON parse failed: ${error.getMessage}")))
        }
      parsed.flatMap {
        case obj: ujson.Obj => decode(obj, env)
        case _              => Left(ConfigError(Vector("config root must be a JSON object")))
      }
    }
  }

  private def decode(
      root: ujson.Obj,
      env: Map[String, String]
  ): Either[ConfigError, ScholarChainConfig] = {
    val expanded = expand(root, env) match {
      case obj: ujson.Obj => obj
      case _              => root
    }
    val overrideErrors = applyOverrides(expanded, env)
    val leftover = collectPlaceholders(expanded)
    val errors = overrideErrors ++ leftover.map(name => s"unresolved placeholder: $name")
    if (errors.nonEmpty) Left(ConfigError(errors))
    else readConfig(expanded)
  }

  private def expand(value: ujson.Value, env: Map[String, String]): ujson.Value =
    value match {
      case obj: ujson.Obj =>
        val copy = ujson.Obj()
        obj.value.foreach { case (key, child) =>
          copy(key) = expand(child, env)
        }
        copy
      case arr: ujson.Arr =>
        val copy = ujson.Arr()
        arr.value.foreach(child => copy.value += expand(child, env))
        copy
      case ujson.Str(text) =>
        ujson.Str(
          Placeholder.replaceAllIn(
            text,
            matcher =>
              env.get(matcher.group(1)) match {
                case Some(replacement) =>
                  java.util.regex.Matcher.quoteReplacement(replacement)
                case None => matcher.matched
              }
          )
        )
      case other => other
    }

  private def applyOverrides(root: ujson.Obj, env: Map[String, String]): Vector[String] = {
    val errors = Vector.newBuilder[String]
    Overrides.foreach { spec =>
      env.get(spec.env).foreach { raw =>
        setPath(root, spec.path, raw, spec.kind).left.foreach(errors += _)
      }
    }
    bridgeOverrides(env).foreach { case (name, raw) =>
      val graph = ensureObject(root, "graph")
      val params = graph.value.get("bridgeParameters") match {
        case Some(obj: ujson.Obj) => obj
        case _ =>
          val created = ujson.Obj()
          graph("bridgeParameters") = created
          created
      }
      params(name) = ujson.Str(raw)
    }
    errors.result()
  }

  private def bridgeOverrides(env: Map[String, String]): Vector[(String, String)] =
    env.iterator.collect {
      case (key, value) if key.startsWith("SCHOLARCHAIN_GRAPH_BRIDGE_PARAM_") =>
        key.stripPrefix("SCHOLARCHAIN_GRAPH_BRIDGE_PARAM_") -> value
    }.toVector

  private def setPath(
      root: ujson.Obj,
      path: Vector[String],
      raw: String,
      kind: ValueKind
  ): Either[String, Unit] = {
    val parents = path.dropRight(1)
    val leaf = path.last
    val parent = parents.foldLeft[Either[String, ujson.Obj]](Right(root)) { (acc, name) =>
      acc.flatMap { obj =>
        obj.value.get(name) match {
          case Some(child: ujson.Obj) => Right(child)
          case Some(_)                => Left(s"${parents.mkString(".")} is not an object")
          case None =>
            val created = ujson.Obj()
            obj(name) = created
            Right(created)
        }
      }
    }
    parent.flatMap { obj =>
      kind match {
        case ValueKind.OptionalAccount if raw.trim.isEmpty =>
          obj(leaf) = ujson.Null
          Right(())
        case ValueKind.Text | ValueKind.OptionalAccount =>
          obj(leaf) = ujson.Str(raw)
          Right(())
        case ValueKind.WholeNumber =>
          parseWhole(raw, path.mkString(".")) match {
            case Right(number) =>
              obj(leaf) = ujson.Num(number.toDouble)
              Right(())
            case Left(message) => Left(message)
          }
        case ValueKind.Decimal =>
          parseDecimal(raw, path.mkString(".")) match {
            case Right(number) =>
              obj(leaf) = ujson.Num(number)
              Right(())
            case Left(message) => Left(message)
          }
      }
    }
  }

  private def ensureObject(root: ujson.Obj, name: String): ujson.Obj =
    root.value.get(name) match {
      case Some(obj: ujson.Obj) => obj
      case _ =>
        val created = ujson.Obj()
        root(name) = created
        created
    }

  private def collectPlaceholders(value: ujson.Value): Vector[String] =
    value match {
      case obj: ujson.Obj => obj.value.values.iterator.flatMap(collectPlaceholders).toVector
      case arr: ujson.Arr => arr.value.iterator.flatMap(collectPlaceholders).toVector
      case str: ujson.Str => Placeholder.findAllMatchIn(str.value).map(_.group(1)).toVector
      case _              => Vector.empty
    }

  private def readConfig(root: ujson.Obj): Either[ConfigError, ScholarChainConfig] = {
    val errors = Vector.newBuilder[String]
    val schema = string(root, Vector("configSchemaVersion"), errors)
    if (!SchemaVersions.supportedConfig.contains(schema))
      errors += s"unsupported config schema version: $schema"
    val application = readApplication(child(root, "application", errors), errors)
    val storage = readStorage(child(root, "storage", errors), errors)
    val neptune = readNeptune(child(root, "neptune", errors), errors)
    val vectors = readVectors(child(root, "s3Vectors", errors), errors)
    val entity = readEntity(child(root, "entityResolution", errors), errors)
    val graph = readGraph(child(root, "graph", errors), errors)
    val retrieval = readRetrieval(child(root, "retrieval", errors), errors)
    val models = readModels(child(root, "models", errors), errors)
    val operations = readOperations(child(root, "operations", errors), errors)
    val found = errors.result()
    if (found.nonEmpty) Left(ConfigError(found))
    else
      Right(
        ScholarChainConfig(
          schema,
          application,
          storage,
          neptune,
          vectors,
          entity,
          graph,
          retrieval,
          models,
          operations
        )
      )
  }

  private def readApplication(
      obj: ujson.Obj,
      errors: ErrorLog
  ): ApplicationConfig = {
    val account = obj.value.get("awsAccountId") match {
      case None | Some(ujson.Null)                            => None
      case Some(ujson.Str(value)) if AccountId.matches(value) => Some(value)
      case Some(other) =>
        errors += s"application.awsAccountId must be a 12-digit string or null, found $other"
        None
    }
    ApplicationConfig(
      string(obj, Vector("environment"), errors),
      string(obj, Vector("region"), errors),
      account
    )
  }

  private def readStorage(obj: ujson.Obj, errors: ErrorLog): StorageConfig =
    StorageConfig(
      string(obj, Vector("rawBucket"), errors),
      string(obj, Vector("curatedBucket"), errors),
      string(obj, Vector("graphBucket"), errors),
      string(obj, Vector("ragBucket"), errors)
    )

  private def readNeptune(obj: ujson.Obj, errors: ErrorLog): NeptuneConfig = {
    val port = whole(obj, Vector("port"), errors)
    val timeout = whole(obj, Vector("queryTimeoutMs"), errors)
    if (port < 1 || port > 65535) errors += "neptune.port must be in 1..65535"
    if (timeout < 1) errors += "neptune.queryTimeoutMs must be >= 1"
    NeptuneConfig(string(obj, Vector("endpoint"), errors), port, timeout)
  }

  private def readVectors(obj: ujson.Obj, errors: ErrorLog): S3VectorsConfig = {
    val indexes = child(obj, "indexes", errors)
    S3VectorsConfig(
      string(obj, Vector("vectorBucket"), errors),
      VectorIndexConfig(
        string(indexes, Vector("researchers"), errors),
        string(indexes, Vector("communities"), errors),
        string(indexes, Vector("abstracts"), errors),
        string(indexes, Vector("paths"), errors),
        string(indexes, Vector("topicInstitutions"), errors)
      )
    )
  }

  private def readEntity(
      obj: ujson.Obj,
      errors: ErrorLog
  ): EntityResolutionConfig = {
    val accept = decimal(obj, Vector("acceptThreshold"), errors)
    val reject = decimal(obj, Vector("rejectThreshold"), errors)
    val bandMin = decimal(obj, Vector("llmBandMin"), errors)
    val bandMax = decimal(obj, Vector("llmBandMax"), errors)
    Seq(accept, reject, bandMin, bandMax).foreach { value =>
      if (!java.lang.Double.isFinite(value) || value < 0.0 || value > 1.0)
        errors += "entity-resolution thresholds must be finite and in [0, 1]"
    }
    if (reject > accept) errors += "rejectThreshold must be <= acceptThreshold"
    if (bandMin > bandMax) errors += "llmBandMin must be <= llmBandMax"
    EntityResolutionConfig(
      string(obj, Vector("policyVersion"), errors),
      accept,
      reject,
      bandMin,
      bandMax
    )
  }

  private def readGraph(obj: ujson.Obj, errors: ErrorLog): GraphConfig = {
    val start = whole(obj, Vector("windowStartYear"), errors)
    val end = whole(obj, Vector("windowEndYear"), errors)
    if (start < 1 || start > 9999)
      errors += s"graph.windowStartYear is outside 1..9999"
    if (end < 1 || end > 9999)
      errors += s"graph.windowEndYear is outside 1..9999"
    if (start > end)
      errors += s"graph window start $start exceeds end $end"
    val parameters = obj.value.get("bridgeParameters") match {
      case None | Some(ujson.Null) => Vector.empty
      case Some(params: ujson.Obj) =>
        params.value.toVector.sortBy(_._1).map {
          case (key, ujson.Str(value)) => NamedText(key, value)
          case (key, other) =>
            errors += s"graph.bridgeParameters.$key must be a string, found $other"
            NamedText(key, "")
        }
      case Some(other) =>
        errors += s"graph.bridgeParameters must be an object, found $other"
        Vector.empty
    }
    GraphConfig(
      start,
      end,
      string(obj, Vector("bridgeAlgorithm"), errors),
      parameters
    )
  }

  private def readRetrieval(obj: ujson.Obj, errors: ErrorLog): RetrievalConfig = {
    val graphLimit = whole(obj, Vector("graphLimit"), errors)
    val vectorLimit = whole(obj, Vector("vectorLimit"), errors)
    val budget = whole(obj, Vector("contextTokenBudget"), errors)
    val depth = whole(obj, Vector("maxPathDepth"), errors)
    if (graphLimit < 1 || vectorLimit < 1 || budget < 1 || depth < 1)
      errors += "retrieval limits must be >= 1"
    RetrievalConfig(
      graphLimit,
      vectorLimit,
      budget,
      string(obj, Vector("fusionPolicyVersion"), errors),
      depth
    )
  }

  private def readModels(obj: ujson.Obj, errors: ErrorLog): ModelsConfig =
    ModelsConfig(
      string(obj, Vector("embeddingModel"), errors),
      string(obj, Vector("synthesisModel"), errors),
      string(obj, Vector("verificationModel"), errors)
    )

  private def readOperations(
      obj: ujson.Obj,
      errors: ErrorLog
  ): OperationsConfig = {
    val deadline = whole(obj, Vector("synchronousDeadlineMs"), errors)
    val retries = whole(obj, Vector("maxWorkflowRetries"), errors)
    val concurrent = whole(obj, Vector("maxConcurrentLlmCalls"), errors)
    if (deadline < 1) errors += "operations.synchronousDeadlineMs must be >= 1"
    if (retries < 0) errors += "operations.maxWorkflowRetries must be >= 0"
    if (concurrent < 1) errors += "operations.maxConcurrentLlmCalls must be >= 1"
    OperationsConfig(deadline, retries, concurrent)
  }

  private def child(
      obj: ujson.Obj,
      name: String,
      errors: ErrorLog
  ): ujson.Obj =
    obj.value.get(name) match {
      case Some(childObj: ujson.Obj) => childObj
      case Some(other) =>
        errors += s"$name must be an object, found $other"
        ujson.Obj()
      case None =>
        errors += s"missing object: $name"
        ujson.Obj()
    }

  private def string(
      obj: ujson.Obj,
      path: Vector[String],
      errors: ErrorLog
  ): String =
    lookup(obj, path) match {
      case Some(ujson.Str(value)) if value.trim.nonEmpty => value
      case Some(ujson.Str(_)) =>
        errors += s"${path.mkString(".")} must be non-blank"
        ""
      case Some(other) =>
        errors += s"${path.mkString(".")} must be a string, found $other"
        ""
      case None =>
        errors += s"missing ${path.mkString(".")}"
        ""
    }

  private def whole(
      obj: ujson.Obj,
      path: Vector[String],
      errors: ErrorLog
  ): Int =
    lookup(obj, path) match {
      case Some(ujson.Num(value))
          if value.isWhole && value <= Int.MaxValue && value >= Int.MinValue =>
        value.toInt
      case Some(other) =>
        errors += s"${path.mkString(".")} must be an integer, found $other"
        0
      case None =>
        errors += s"missing ${path.mkString(".")}"
        0
    }

  private def decimal(
      obj: ujson.Obj,
      path: Vector[String],
      errors: ErrorLog
  ): Double =
    lookup(obj, path) match {
      case Some(ujson.Num(value)) => value
      case Some(other) =>
        errors += s"${path.mkString(".")} must be a number, found $other"
        Double.NaN
      case None =>
        errors += s"missing ${path.mkString(".")}"
        Double.NaN
    }

  private def lookup(obj: ujson.Obj, path: Vector[String]): Option[ujson.Value] =
    path match {
      case Vector(name) => obj.value.get(name)
      case _            => None
    }

  private def parseWhole(raw: String, field: String): Either[String, Int] =
    scala.util
      .Try(Integer.parseInt(raw))
      .toEither
      .left
      .map(_ => s"$field override is not an integer")

  private def parseDecimal(raw: String, field: String): Either[String, Double] =
    scala.util
      .Try(java.lang.Double.parseDouble(raw))
      .toEither
      .left
      .map(_ => s"$field override is not a number")

  private val unsupportedDocument: String =
    "configuration file must be a JSON object, which is the JSON profile of HOCON. " +
      "YAML and non-JSON HOCON syntax are unsupported by this loader."
}

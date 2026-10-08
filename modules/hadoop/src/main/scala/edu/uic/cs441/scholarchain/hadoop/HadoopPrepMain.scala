package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*

import java.nio.file.Path

/** Local or cluster driver. `hadoop/hadoopLocalClasspath` or `hadoop jar <submit-jar> <this main>
  * -libjars <bundle>` supplies the runtime. The submit JAR embeds its driver dependency bundle. A
  * failed config never launches a job.
  */
object HadoopPrepMain {
  final case class Launch(
      configuration: org.apache.hadoop.conf.Configuration,
      args: Array[String]
  )

  val DefaultConfigPath: String =
    "modules/core/src/main/resources/scholarchain.hadoop-prep.v1.json"

  /** Hadoop generic options, including `-libjars`, are removed from the application args. `tmpjars`
    * stays on the returned configuration.
    */
  def parseLaunch(args: Array[String]): Launch = {
    val parser = new org.apache.hadoop.util.GenericOptionsParser(
      new org.apache.hadoop.conf.Configuration(),
      args
    )
    Launch(parser.getConfiguration(), parser.getRemainingArgs())
  }

  /** Infra localizes `s3://`, `s3a://`, `s3n://`, and `hdfs://` configs before `main`. */
  def requireLocalConfig(path: String): Either[String, String] = {
    val prefixes = Array("s3://", "s3a://", "s3n://", "hdfs://")
    val remote = prefixes.find(prefix => path.regionMatches(true, 0, prefix, 0, prefix.length))
    remote match {
      case Some(prefix) =>
        Left(
          s"config must be a local regular file after localization; $path starts with $prefix. " +
            "Localize s3://, s3a://, s3n://, and hdfs:// configs before invoking main."
        )
      case None => Right(path)
    }
  }

  def main(args: Array[String]): Unit = {
    val launch = parseLaunch(args)
    val appArgs = launch.args
    val configPath = option(appArgs, "--config").getOrElse(DefaultConfigPath)
    val localPath = requireLocalConfig(configPath) match {
      case Left(message) =>
        System.err.println(message)
        sys.exit(2)
      case Right(path) => path
    }
    try
      org.apache.log4j.Logger
        .getLogger("org.apache.hadoop")
        .setLevel(org.apache.log4j.Level.WARN)
    catch { case _: Throwable => () }
    val prepared = HadoopPrepConfigLoader.load(Path.of(localPath)).flatMap { loaded =>
      overridden(loaded, appArgs)
    }
    prepared match {
      case Left(message) =>
        System.err.println(message)
        sys.exit(2)
      case Right((config, snapshots, retrievalDates, paths)) =>
        val requestBase = HadoopPrepPipeline.Request(
          config,
          paths(SourceType.Dblp),
          paths(SourceType.OpenAlex),
          paths(SourceType.Crossref),
          paths(SourceType.Orcid),
          snapshots,
          HadoopPrepPipeline.newRunId(),
          retrievalDates = retrievalDates,
          hadoopConf = launch.configuration
        )
        val runs = if (appArgs.contains("--once")) 1 else 2
        val results = (1 to runs).map { index =>
          val request =
            if (index == 1 && option(appArgs, "--run-id").nonEmpty)
              requestBase.copy(runId = option(appArgs, "--run-id").get)
            else requestBase.copy(runId = HadoopPrepPipeline.newRunId())
          HadoopPrepPipeline.execute(request)
        }
        results.zipWithIndex.foreach { case (result, index) =>
          result match {
            case Left(message) =>
              System.err.println(s"run ${index + 1} failed: $message")
            case Right(value) =>
              println(s"runDirectory=${value.outputLocation}")
              println(s"runId=${value.runId}")
              println(s"reused=${value.reused}")
              println(
                "counters=" + PrepCounters.All
                  .map(name => s"$name:${value.counters.getOrElse(name, 0L)}")
                  .mkString(",")
              )
              println(s"largestTeam=${value.largestTeam}")
              println(s"largestPairExpansion=${value.largestPairExpansion}")
              println(s"largestBlock=${value.largestBlock}")
              value.representative.foreach(line => println("representative=" + line))
          }
        }
        if (results.exists(_.isLeft)) sys.exit(1)
        if (runs == 2) {
          val first = results(0).toOption.get
          val second = results(1).toOption.get
          val same = logicalRecordsEqual(
            first.outputLocation,
            first.runId,
            second.outputLocation,
            second.runId,
            launch.configuration
          )
          println(s"logicalRecordsEqual=$same")
          if (!same) sys.exit(1)
        }
    }
  }

  def withOutputRoot(config: HadoopPrepConfig, args: Array[String]): HadoopPrepConfig =
    option(args, "--output-root").map(root => config.copy(outputRoot = root)).getOrElse(config)

  /** CLI overrides are applied before [[HadoopPrepPipeline.execute]] validates the config. */
  def overridden(
      loaded: HadoopPrepConfig,
      args: Array[String]
  ): Either[
    String,
    (HadoopPrepConfig, Map[SourceType, String], Map[SourceType, String], Map[SourceType, String])
  ] = {
    val mode = option(args, "--execution-mode") match {
      case None => Right(loaded.executionMode)
      case Some(value) =>
        HadoopExecutionMode.values
          .find(_.wire == value)
          .toRight(s"invalid execution mode: $value")
    }
    val defaults = Map(
      SourceType.Dblp -> "datasets/samples/dblp/linked-records.xml",
      SourceType.OpenAlex -> "datasets/samples/openalex/works.jsonl",
      SourceType.Crossref -> "datasets/samples/crossref/works.jsonl",
      SourceType.Orcid -> "datasets/samples/orcid/records.jsonl"
    )
    val flags = Map(
      SourceType.Dblp -> "--dblp",
      SourceType.OpenAlex -> "--openalex",
      SourceType.Crossref -> "--crossref",
      SourceType.Orcid -> "--orcid"
    )
    val missing = flags.flatMap { case (source, flag) =>
      option(args, flag).flatMap { _ =>
        val snapshot = option(args, flag + "-snapshot")
        val retrieval = option(args, flag + "-retrieval")
        if (snapshot.exists(_.nonEmpty) && retrieval.exists(_.nonEmpty)) None
        else Some(s"$flag requires $flag-snapshot and $flag-retrieval")
      }
    }
    mode.flatMap { execution =>
      if (missing.nonEmpty) Left(missing.mkString("; "))
      else {
        val config = withOutputRoot(loaded, args).copy(executionMode = execution)
        val snapshots = flags.map { case (source, flag) =>
          source -> option(args, flag + "-snapshot").getOrElse(
            HadoopPrepPipeline.DefaultSnapshots(source)
          )
        }
        val retrievals = flags.map { case (source, flag) =>
          source -> option(args, flag + "-retrieval").getOrElse(
            HadoopPrepPipeline.DefaultRetrievalDates(source)
          )
        }
        val paths = flags.map { case (source, flag) =>
          source -> option(args, flag).getOrElse(defaults(source))
        }
        Right((config, snapshots, retrievals, paths))
      }
    }
  }

  /** Both exports must be readable. A missing export is not an empty digest and does not equal
    * another missing export.
    */
  def logicalRecordsEqual(
      left: String,
      leftRun: String,
      right: String,
      rightRun: String
  ): Boolean =
    logicalRecordsEqual(left, leftRun, right, rightRun, FsIO.configuration())

  def logicalRecordsEqual(
      left: String,
      leftRun: String,
      right: String,
      rightRun: String,
      conf: org.apache.hadoop.conf.Configuration
  ): Boolean =
    (exportDigest(left, leftRun, conf), exportDigest(right, rightRun, conf)) match {
      case (Some(leftDigest), Some(rightDigest)) => leftDigest == rightDigest
      case _                                     => false
    }

  /** Order-independent digest of export JSON. Each record SHA-256 is added as an unsigned 256-bit
    * integer, and the record count is kept, so duplicate lines do not cancel. `None` when the
    * export location cannot be read.
    */
  def exportDigest(location: String, runId: String): Option[String] =
    exportDigest(location, runId, FsIO.configuration())

  def exportDigest(
      location: String,
      runId: String,
      conf: org.apache.hadoop.conf.Configuration
  ): Option[String] = {
    val root = new org.apache.hadoop.fs.Path(FsPaths.file(location), "export")
    try
      if (!FsIO.exists(root, conf)) None
      else {
        var sum = java.math.BigInteger.ZERO
        var count = 0
        FsIO.listFiles(root, conf).foreach { file =>
          val name = file.getName
          if (!name.startsWith("_") && !name.startsWith(".") && !name.endsWith(".crc")) {
            val in = file.getFileSystem(conf).open(file)
            val reader = new java.io.BufferedReader(
              new java.io.InputStreamReader(in, java.nio.charset.StandardCharsets.UTF_8)
            )
            try {
              var line = reader.readLine()
              while (line != null) {
                val trimmed = line.trim
                if (trimmed.startsWith("{")) {
                  val hash = java.util.HexFormat
                    .of()
                    .parseHex(StableIds.sha256Hex(LogicalRecords.normalize(trimmed, runId)))
                  sum = sum.add(new java.math.BigInteger(1, hash))
                  count += 1
                }
                line = reader.readLine()
              }
            } finally reader.close()
          }
        }
        Some(count.toString + ":" + sum.toString(16))
      }
    catch { case _: Exception => None }
  }

  private def option(args: Array[String], name: String): Option[String] = {
    val index = args.indexOf(name)
    if (index >= 0 && index + 1 < args.length) Some(args(index + 1)) else None
  }
}

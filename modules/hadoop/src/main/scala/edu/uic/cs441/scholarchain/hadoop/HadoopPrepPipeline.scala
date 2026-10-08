package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*

import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.{Path => HPath}

import java.nio.file.{LinkOption, Path, WatchEvent, WatchKey, WatchService}
import java.util.UUID
import scala.collection.mutable.ArrayBuffer

object HadoopPrepPipeline {
  final case class Request(
      config: HadoopPrepConfig,
      dblp: String,
      openAlex: String,
      crossref: String,
      orcid: String,
      snapshots: Map[SourceType, String],
      runId: String,
      splitMax: Option[Long] = None,
      failJob: Option[String] = None,
      retrievalDates: Map[SourceType, String] = Map.empty,
      hadoopConf: Configuration = new Configuration()
  )

  /** Acquisition-index snapshot ids. These label only the committed sample paths. */
  val DefaultSnapshots: Map[SourceType, String] = Map(
    SourceType.Dblp -> "dblp-2026-10-03",
    SourceType.OpenAlex -> "openalex-rest-2026-10-05",
    SourceType.Crossref -> "crossref-rest-2026-10-05",
    SourceType.Orcid -> "orcid-public-api-2026-10-05"
  )

  val DefaultRetrievalDates: Map[SourceType, String] = Map(
    SourceType.Dblp -> "2026-10-05",
    SourceType.OpenAlex -> "2026-10-05",
    SourceType.Crossref -> "2026-10-05",
    SourceType.Orcid -> "2026-10-05"
  )

  final case class Result(
      runId: String,
      directory: Path,
      reused: Boolean,
      counters: Map[String, Long],
      largestTeam: Long,
      largestPairExpansion: Long,
      largestBlock: Long,
      representative: Vector[String],
      outputLocation: String
  )

  def execute(request: Request): Either[String, Result] =
    HadoopPrepConfigLoader.validate(request.config) match {
      case Left(error) => Left(error.messages.mkString("; "))
      case Right(config) =>
        if (StableIds.parseRunId(request.runId).isLeft)
          Left(s"run id is not a version-4 run id: ${request.runId}")
        else if (request.snapshots.values.exists(value => !Lineage.snapshotFits(value)))
          Left(
            s"dataset snapshot exceeds bounded lineage metadata limit ${Lineage.MaxSnapshotBytes} UTF-8 bytes"
          )
        else
          resolveOutput(config.outputRoot, request.runId) match {
            case Left(message) => Left(message)
            case Right(directory) =>
              val fsConf = FsIO.configuration(request.hadoopConf)
              requireFilesystem(directory, fsConf) match {
                case Left(message) => Left(message)
                case Right(_) =>
                  bindInputs(request, fsConf) match {
                    case Left(message) => Left(message)
                    case Right(bound) =>
                      val identity = outputIdentity(request.runId, config, bound, Vector.empty)
                      OutputGate.claim(directory, identity, fsConf) match {
                        case OutputGate.Refuse(message) => Left(message)
                        case OutputGate.Reuse =>
                          Right(readExisting(request.runId, directory, fsConf))
                        case OutputGate.Proceed =>
                          runJobs(request.copy(config = config), directory, bound, fsConf)
                      }
                  }
              }
          }
    }

  /** Remote roots stay Hadoop paths. They are not converted with `java.nio.file.Path` and no local
    * directory is created for them. A missing filesystem implementation is reported by
    * [[requireFilesystem]], not by this method.
    */
  def resolveOutput(outputRoot: String, runId: String): Either[String, HPath] = {
    val spec = outputRoot.trim
    if (spec.isEmpty || spec == "." || spec == ".." || spec.split('/').contains(".."))
      Left(s"output root is empty or unresolved: $outputRoot")
    else Right(FsPaths.runPath(spec, runId))
  }

  /** Asks the Hadoop `FileSystem` for this path. Does not create a directory. */
  private def requireFilesystem(
      path: HPath,
      conf: org.apache.hadoop.conf.Configuration
  ): Either[String, Unit] =
    try {
      val _ = path.getFileSystem(conf)
      Right(())
    } catch {
      case error: Exception =>
        Left(
          s"${path.toString} requires a Hadoop FileSystem implementation: ${Option(error.getMessage).getOrElse(error.toString)}"
        )
    }

  private def asLocalDirectory(path: HPath): Option[Path] = {
    val scheme = Option(path.toUri.getScheme).map(_.toLowerCase(java.util.Locale.ROOT))
    scheme match {
      case None | Some("file") => Some(FsPaths.local(path))
      case _                   => None
    }
  }

  private def bindInputs(
      request: Request,
      conf: org.apache.hadoop.conf.Configuration
  ): Either[String, Map[SourceType, (String, String, String)]] = {
    val sources = Seq(
      SourceType.Dblp -> request.dblp,
      SourceType.OpenAlex -> request.openAlex,
      SourceType.Crossref -> request.crossref,
      SourceType.Orcid -> request.orcid
    )
    val bound = sources.map { case (source, path) =>
      source -> Acquisition.bind(source, path, request.snapshots, request.retrievalDates, conf)
    }
    val failed = bound.collect { case (source, Left(message)) => s"${source.wire}: $message" }
    if (failed.nonEmpty) Left(failed.mkString("; "))
    else Right(bound.collect { case (source, Right(value)) => source -> value }.toMap)
  }

  private[hadoop] def outputIdentity(
      runId: String,
      config: HadoopPrepConfig,
      bound: Map[SourceType, (String, String, String)],
      partitions: Vector[String]
  ): OutputIdentity =
    OutputIdentity(
      runId,
      config.fingerprint,
      bound.map { case (source, (_, _, hash)) => source.wire -> hash },
      bound.map { case (source, (snapshot, _, _)) => source.wire -> snapshot },
      bound.map { case (source, (_, retrieval, _)) => source.wire -> retrieval },
      partitions
    )

  def directoryName(runId: String): String = runId.stripPrefix("run:")

  private def runJobs(
      request: Request,
      directory: HPath,
      bound: Map[SourceType, (String, String, String)],
      fsConf: Configuration
  ): Either[String, Result] = {
    val snapshots = bound.map { case (source, (snapshot, _, _)) => source -> snapshot }
    val conf = PrepJobs.configuration(request.config, request.runId, snapshots, fsConf)
    request.failJob.foreach(name => conf.set(ConfKeys.FailJob, name))
    conf.set(ConfKeys.RetrievalDblp, bound(SourceType.Dblp)._2)
    conf.set(ConfKeys.RetrievalOpenAlex, bound(SourceType.OpenAlex)._2)
    conf.set(ConfKeys.RetrievalCrossref, bound(SourceType.Crossref)._2)
    conf.set(ConfKeys.RetrievalOrcid, bound(SourceType.Orcid)._2)
    val stats = new HPath(directory, "stats")
    FsIO.mkdirs(stats, fsConf)
    conf.set(ConfKeys.StatsDir, stats.toString)
    val inputs =
      Seq(request.dblp, request.openAlex, request.crossref, request.orcid).map(FsPaths.file)
    SampleBound.install(conf, inputs)
    val intermediate = new HPath(directory, "intermediate")
    val dirs =
      Vector("j01", "j02", "j03", "j04", "j05", "j06", "j07", "j08").map(name =>
        new HPath(intermediate, name)
      )
    val exported = new HPath(directory, "export")
    try {
      val jobs = Seq(
        "J01" -> PrepJobs.dblp(conf, request.dblp, dirs(0), request.splitMax),
        "J02" -> PrepJobs
          .normalize(conf, request.openAlex, request.crossref, request.orcid, dirs(1)),
        "J03" -> PrepJobs.index(conf, Seq(dirs(0), dirs(1)), dirs(2)),
        "J04" -> PrepJobs.join(conf, Seq(dirs(0), dirs(1), dirs(2)), dirs(3)),
        "J05" -> PrepJobs.block(conf, dirs(3), dirs(4)),
        "J06" -> PrepJobs.candidates(conf, dirs(4), dirs(5)),
        "J07" -> PrepJobs.teams(conf, Seq(dirs(3)), dirs(6)),
        "J08" -> PrepJobs.pairExpansion(conf, Seq(dirs(3)), dirs(7)),
        "J09" -> PrepJobs.exportJob(
          conf,
          Seq(dirs(3), dirs(4), dirs(5), dirs(6), dirs(7)),
          exported
        )
      )
      val totals = PrepCounters.All.map(_ -> 0L).to(scala.collection.mutable.LinkedHashMap)
      jobs.foreach { case (name, job) =>
        PrepJobs.run(name, job)
        PrepJobs.counters(job).foreach { case (counter, value) =>
          totals.update(counter, totals(counter) + value)
        }
      }
      val manifest = buildManifest(request, bound)
      DomainValidation.check(manifest) match {
        case Left(errors) =>
          Left(errors.map(_.message).mkString("; "))
        case Right(valid) =>
          FsIO.writeUtf8(
            new HPath(directory, "run-manifest.json"),
            CoreJson.pretty(valid),
            fsConf
          )
          val counters = totals.toMap
          FsIO.writeUtf8(
            new HPath(directory, "counter-summary.json"),
            ujson.write(
              ujson.Obj.from(counters.map { case (key, value) =>
                key -> ujson.Num(value.toDouble)
              }),
              indent = 2
            ),
            fsConf
          )
          val partitions = OutputGate.listPartitions(exported, fsConf)
          if (partitions.isEmpty)
            Left("export produced no partitions; completion marker was not written")
          else {
            OutputGate.write(
              directory,
              outputIdentity(request.runId, request.config, bound, partitions),
              fsConf
            )
            Right(completeResult(directory, request.runId, reused = false, counters, fsConf))
          }
      }
    } catch {
      case error: IllegalStateException =>
        Left(Option(error.getMessage).getOrElse(error.toString))
    }
  }

  private[hadoop] def buildManifest(
      request: Request,
      bound: Map[SourceType, (String, String, String)]
  ): RunManifest = {
    val notes = Vector(
      s"hadoopPrepSchema=${SchemaVersions.hadoopPrep}",
      s"hadoopPrepFingerprint=${request.config.fingerprint}",
      s"transformationVersion=${PrepLimits.TransformationVersion}",
      s"domainSchema=${SchemaVersions.domain}"
    ) ++ bound.toVector.sortBy(_._1.wire).map { case (source, (_, _, hash)) =>
      s"inputChecksum:${source.wire}=$hash"
    }
    val snapshots =
      bound.toVector.sortBy(_._1.wire).map { case (source, (snapshot, retrieval, _)) =>
        DatasetSnapshotRef(source, snapshot, Some(retrieval))
      }
    RunManifest(
      request.runId,
      SchemaVersions.domain,
      "hadoop-prep",
      snapshots,
      SchemaVersions.hadoopPrep,
      request.config.fingerprint,
      ProvenanceFactory(
        SourceType.ScholarChain,
        request.runId,
        None,
        PrepLimits.DerivedSnapshot,
        request.runId,
        notes
      )
    )
  }

  private def readExisting(runId: String, directory: HPath, conf: Configuration): Result =
    completeResult(
      directory,
      runId,
      reused = true,
      readCounters(new HPath(directory, "counter-summary.json"), conf),
      conf
    )

  /** Local success keeps a real directory. Remote success keeps the Hadoop URI and does not invent
    * a local path.
    */
  private[hadoop] def completeResult(
      directory: HPath,
      runId: String,
      reused: Boolean,
      counters: Map[String, Long],
      conf: Configuration = FsIO.configuration()
  ): Result = {
    val stats = new HPath(directory, "stats")
    val exported = new HPath(directory, "export")
    val localDirectory =
      asLocalDirectory(directory).getOrElse(new RemoteOutputPath(directory.toString))
    Result(
      runId,
      localDirectory,
      reused,
      PrepCounters.All.map(name => name -> counters.getOrElse(name, 0L)).toMap,
      StatsFiles.max(stats.toString, "largestTeam", conf),
      StatsFiles.max(stats.toString, "largestPairExpansion", conf),
      StatsFiles.max(stats.toString, "largestBlock", conf),
      representative(exported, conf),
      directory.toString
    )
  }

  private def readCounters(path: HPath, conf: Configuration): Map[String, Long] = {
    if (!FsIO.isFile(path, conf)) Map.empty
    else {
      ujson
        .read(FsIO.readUtf8(path, conf))
        .obj
        .value
        .flatMap {
          case (key, ujson.Num(value)) => Some(key -> value.toLong)
          case _                       => None
        }
        .toMap
    }
  }

  /** Bounded sample. Stops after eight matches or 64 scanned lines. */
  def representative(exported: Path): Vector[String] =
    representative(new HPath(exported.toUri), FsIO.configuration())

  def representative(exported: HPath): Vector[String] =
    representative(exported, FsIO.configuration())

  def representative(exported: HPath, conf: Configuration): Vector[String] = {
    val root = exported
    if (!FsIO.exists(root, conf)) Vector.empty
    else {
      val wanted = Set(
        "\"workId\"",
        "\"candidateId\"",
        "\"teamSize\"",
        "\"leftMentionId\"",
        "\"orcid\"",
        "\"reasonCode\""
      )
      val picked = ArrayBuffer.empty[String]
      val files = FsIO.listFiles(root, conf).iterator
      var scanned = 0
      while (files.hasNext && picked.size < 8 && scanned < 64) {
        val file = files.next()
        val name = file.getName
        if (!name.startsWith("_") && !name.startsWith(".") && !name.endsWith(".crc")) {
          val in = file.getFileSystem(conf).open(file)
          val reader = new java.io.BufferedReader(
            new java.io.InputStreamReader(in, java.nio.charset.StandardCharsets.UTF_8)
          )
          try {
            var line = reader.readLine()
            while (line != null && picked.size < 8 && scanned < 64) {
              scanned += 1
              if (wanted.exists(line.contains)) picked += line.take(500)
              line = reader.readLine()
            }
          } finally reader.close()
        }
      }
      picked.toVector
    }
  }

  def newRunId(): String =
    StableIds.newRunId(UUID.randomUUID()) match {
      case Right(id)   => id
      case Left(error) => throw new IllegalStateException(error.message)
    }
}

/** Carries a remote Hadoop URI without creating a local directory. */
private[hadoop] final class RemoteOutputPath(private val location: String) extends Path {
  private val uri = java.net.URI.create(location)

  override def getFileSystem: java.nio.file.FileSystem =
    throw new UnsupportedOperationException(location)
  override def isAbsolute: Boolean = true
  override def getRoot: Path = null
  override def getFileName: Path = null
  override def getParent: Path = null
  override def getNameCount: Int = 0
  override def getName(index: Int): Path = null
  override def subpath(beginIndex: Int, endIndex: Int): Path = this
  override def startsWith(other: Path): Boolean = false
  override def startsWith(other: String): Boolean = location.startsWith(other)
  override def endsWith(other: Path): Boolean = false
  override def endsWith(other: String): Boolean = location.endsWith(other)
  override def normalize(): Path = this
  override def resolve(other: Path): Path = resolve(other.toString)
  override def resolve(other: String): Path = {
    val base = if (location.endsWith("/")) location.dropRight(1) else location
    val child = if (other.startsWith("/")) other.drop(1) else other
    new RemoteOutputPath(s"$base/$child")
  }
  override def relativize(other: Path): Path = this
  override def toUri: java.net.URI = uri
  override def toAbsolutePath: Path = this
  override def toRealPath(options: LinkOption*): Path = this
  override def toFile: java.io.File = throw new UnsupportedOperationException(location)
  override def register(
      watcher: WatchService,
      events: Array[WatchEvent.Kind[?]],
      modifiers: WatchEvent.Modifier*
  ): WatchKey = throw new UnsupportedOperationException(location)
  override def iterator(): java.util.Iterator[Path] = java.util.Collections.emptyIterator()
  override def compareTo(other: Path): Int = location.compareTo(other.toString)
  override def toString: String = location
  override def equals(other: Any): Boolean = other match {
    case path: Path => path.toString == location
    case _          => false
  }
  override def hashCode: Int = location.hashCode
}

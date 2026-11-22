package edu.uic.cs441.scholarchain.storage

import java.nio.file.{Files, Path}

/** Offline smoke run: loads a completed Phase 6 Spark export into the local in-memory stores and
  * prints what was loaded, how long it took and the live heap afterwards. It reads local files only
  * and never calls a provider.
  *
  * Usage: `LocalExportMain <exportDir> [--include-list <file>] [--no-verify] [--validate-csv]`
  */
object LocalExportMain {
  private def heapMiB(): Long = {
    System.gc(); System.gc()
    val r = Runtime.getRuntime
    (r.totalMemory() - r.freeMemory()) / (1024 * 1024)
  }

  def main(args: Array[String]): Unit = run(args.toVector) match {
    case Right(text) => println(text)
    case Left(text)  => System.err.println(text); sys.exit(1)
  }

  def run(args: Vector[String]): Either[String, String] = {
    val usage =
      "usage: LocalExportMain <exportDir> [--include-list <file>] [--no-verify] [--validate-csv]"
    val known = Set("--include-list", "--no-verify", "--validate-csv")
    val dir = args.headOption.filterNot(_.startsWith("--")).toRight(usage)
    val flags = args.drop(1)
    val unknown = flags.zipWithIndex.collect {
      case (f, n) if f.startsWith("--") && !known(f)                                      => f
      case (f, n) if !f.startsWith("--") && !flags.lift(n - 1).contains("--include-list") => f
    }
    val includeFile = flags.indexOf("--include-list") match {
      case -1 => Right(None)
      case n  => flags.lift(n + 1).toRight(usage).map(p => Some(Path.of(p)))
    }
    for {
      d <- dir
      _ <- Either.cond(
        unknown.isEmpty,
        (),
        "unknown argument: " + unknown.mkString(" ") + "\n" + usage
      )
      inc <- includeFile
      scope <- inc match {
        case None => Right(RuntimeArtifactScope.WholeExport)
        case Some(p) =>
          for {
            size <- scala.util
              .Try(Files.size(p))
              .toEither
              .left
              .map(_ => "include-list unreadable")
            _ <- Either.cond(
              size <= IncludeList.maxBytes,
              (),
              "include-list refused: include-list-too-large"
            )
            parsed <- IncludeList
              .parse(Files.readAllBytes(p))
              .left
              .map(c => "include-list refused: " + c)
          } yield RuntimeArtifactScope.IncludeIds(parsed)
      }
      options = LocalExportOptions(
        artifactScope = scope,
        verifySourceHashes = !flags.contains("--no-verify"),
        validateNeptuneCsv = flags.contains("--validate-csv"),
        progress = line => System.err.println("[local-export] " + line)
      )
      stores <- LocalExportStores
        .load(Path.of(d), options)
        .left
        .map(e => s"local export refused: code=${e.code} part=${e.part} detail=${e.detail}")
    } yield {
      val heap = heapMiB()
      val c = stores.counts
      // A few warm reads, timed, so the cost of a query against the loaded stores is visible.
      def timed[A](label: String)(f: => A): String = {
        val t = System.nanoTime(); val r = f
        s"$label: ${(System.nanoTime() - t) / 1000000L} ms -> $r"
      }
      val probes = StorageResult
        .value(
          stores.runtimeArtifacts.rank(
            "all-years",
            edu.uic.cs441.scholarchain.core.RuntimeRankingMetric.DistinctCoauthorCount,
            edu.uic.cs441.scholarchain.core.RuntimePopulationFilter(),
            100
          )
        )
        .toVector
        .flatMap { page =>
          val ids = page.items.map(_.metric.researcherId)
          if (ids.isEmpty) Vector("probe: the all-years ranking is empty")
          else {
            val from = ids.head
            val to = ids.last
            Vector(
              s"probe population(all-years)=${page.populationCount} top=$from",
              timed("probe rank top100") {
                stores.runtimeArtifacts
                  .rank(
                    "all-years",
                    edu.uic.cs441.scholarchain.core.RuntimeRankingMetric.DistinctCoauthorCount,
                    edu.uic.cs441.scholarchain.core.RuntimePopulationFilter(),
                    100
                  )
                  .getClass
                  .getSimpleName
              },
              timed("probe directedEdges both limit 100") {
                StorageResult
                  .value(
                    stores.graphReader
                      .directedEdges(from, "all-years", EdgeDirection.Both, Set.empty, 100, None)
                  )
                  .map(_.items.size)
              },
              timed("probe shortestPaths top1->top100 depth 6") {
                StorageResult
                  .value(stores.graphReader.shortestPaths(from, to, 6, "all-years", 10))
                  .map(_.map(_.nodeIds.size))
              },
              timed("probe researcherContext") {
                stores.runtimeArtifacts
                  .researcherContext(from, "all-years", 100)
                  .getClass
                  .getSimpleName
              },
              timed("probe metrics.get") {
                stores.metrics.get(from, "all-years").getClass.getSimpleName
              }
            )
          }
        }
      def line(m: Map[String, Long]) = m.toVector.sortBy(_._1).map((k, v) => s"$k=$v").mkString(" ")
      Vector(
        s"runId=${stores.runId}",
        s"loadMillis=${stores.loadMillis}",
        s"liveHeapMiBAfterGc=$heap maxHeapMiB=${Runtime.getRuntime.maxMemory() / (1024 * 1024)}",
        s"artifactScope=${stores.provenance.artifactScope}",
        s"artifactPointer=${stores.artifactPointer}",
        s"nodes: ${line(c.nodesByClass)}",
        s"edges: ${line(c.edgesByType)}",
        s"coauthorEdgesByWindow: ${line(c.coauthorEdgesByWindow)}",
        s"coauthorSupportRows=${c.coauthorSupportRows} metricRows=${c.metricRows} " +
          s"communityMembershipRows=${c.communityMembershipRows} bridgeRows=${c.bridgeRows} " +
          s"temporalChangeRows=${c.temporalChangeRows} communitySummaryRows=${c.communitySummaryRows}",
        s"sourceRowsRead=${c.sourceRowsRead} cacheRowsWritten=${c.cacheWritten} cacheRejected=${c.cacheRejected}",
        s"fileSha256: ${stores.provenance.fileSha256.toVector.sortBy(_._1).map((k, v) => s"$k=$v").mkString(" ")}",
        s"neptuneCsv=${stores.provenance.neptuneCsv}"
      ).++(probes).mkString("\n")
    }
  }
}

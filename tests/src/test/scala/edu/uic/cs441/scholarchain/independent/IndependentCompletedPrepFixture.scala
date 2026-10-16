package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}

/** Minimal synthetic Phase 4 framing written from its documented contract, not a production reader.
  */
private[independent] object IndependentCompletedPrepFixture {
  import IndependentResolutionFixtures.*
  val digest: String = "b" * 64
  val runToken: String = runId.stripPrefix("run:")

  def create(works: Vector[WorkRecord], candidates: Vector[MatchCandidate] = Vector.empty): Path = {
    val dir = Files.createTempDirectory("scholarchain-independent-prep-").toRealPath()
    val records =
      works.groupBy(_.provenance.datasetSnapshot).toVector.flatMap { case (snap, values) =>
        Vector(
          s"snapshot=$snap/run=$runToken/work" -> values.map(CoreJson.compact(_)),
          s"snapshot=$snap/run=$runToken/author-mention" -> values
            .flatMap(_.authors)
            .map(CoreJson.compact(_))
        )
      } ++ (if (candidates.nonEmpty)
              Vector(
                s"snapshot=hadoop-prep/run=$runToken/match-candidate" -> candidates.map(
                  CoreJson.compact(_)
                )
              )
            else Vector.empty)
    records.foreach { case (part, lines) =>
      val out = dir.resolve("export").resolve(part).resolve("part-r-00000")
      Files.createDirectories(out.getParent)
      Files.writeString(out, lines.mkString("", "\n", if (lines.nonEmpty) "\n" else ""), UTF_8)
    }
    Files.createDirectories(dir.resolve("export"))
    Files.write(dir.resolve("export/part-r-00000"), Array.emptyByteArray)
    Files.write(dir.resolve("export/_SUCCESS"), Array.emptyByteArray)
    (1 to 8).foreach { i =>
      val stage = dir.resolve(f"intermediate/j$i%02d")
      Files.createDirectories(stage)
      Files.write(stage.resolve("_SUCCESS"), Array.emptyByteArray)
    }
    val snapshots = works
      .map(w => (w.source, w.provenance.datasetSnapshot, w.provenance.retrievalDate))
      .distinct
      .sortBy(_._1.wire)
    val manifestProvenance = provenance(SourceType.ScholarChain, runId, "hadoop-prep").copy(
      uncertaintyNotes =
        Vector("transformationVersion=hadoop-prep-j01-j09-v3-stable-overflow-lineage") ++
          snapshots.map((s, _, _) => s"inputChecksum:${s.wire}=$digest")
    )
    val manifest = RunManifest(
      runId,
      SchemaVersions.domain,
      "hadoop-prep",
      snapshots.map((s, snap, date) => DatasetSnapshotRef(s, snap, date)),
      "scholarchain.hadoop-prep.v1",
      digest,
      manifestProvenance
    )
    Files.writeString(dir.resolve("run-manifest.json"), CoreJson.compact(manifest), UTF_8)
    val marker = ujson.Obj(
      "complete" -> true,
      "runId" -> runId,
      "configFingerprint" -> digest,
      "inputChecksums" -> ujson.Obj.from(snapshots.map((s, _, _) => s.wire -> ujson.Str(digest))),
      "snapshots" -> ujson.Obj.from(snapshots.map((s, snap, _) => s.wire -> ujson.Str(snap))),
      "retrievalDates" -> ujson.Obj.from(
        snapshots.map((s, _, date) => s.wire -> date.fold[ujson.Value](ujson.Null)(ujson.Str(_)))
      ),
      "partitions" -> ujson.Arr.from(records.map(_._1).sorted),
      "exportParts" -> ujson.Arr(),
      "schemaVersion" -> SchemaVersions.domain,
      "hadoopPrepSchema" -> "scholarchain.hadoop-prep.v1",
      "transformationVersion" -> "hadoop-prep-j01-j09-v3-stable-overflow-lineage"
    )
    Files.writeString(dir.resolve("_SCHOLARCHAIN_COMPLETE"), marker.render(), UTF_8)
    refreshParts(dir)
    dir
  }

  def marker(dir: Path): ujson.Value =
    ujson.read(Files.readString(dir.resolve("_SCHOLARCHAIN_COMPLETE"), UTF_8))
  def saveMarker(dir: Path, value: ujson.Value): Unit = {
    Files.writeString(dir.resolve("_SCHOLARCHAIN_COMPLETE"), value.render(), UTF_8)
    ()
  }

  /** Rebind valid bytes when a test is targeting schema/context rather than digest validation. */
  def refreshParts(dir: Path): Unit = {
    val stream = Files.walk(dir.resolve("export"))
    val parts =
      try {
        import scala.jdk.CollectionConverters.*
        stream
          .iterator()
          .asScala
          .filter(p => Files.isRegularFile(p) && p.getFileName.toString.startsWith("part-"))
          .toVector
          .sortBy(_.toString)
          .map { p =>
            val bytes = Files.readAllBytes(p)
            val sha = java.security.MessageDigest
              .getInstance("SHA-256")
              .digest(bytes)
              .map(b => f"${b & 0xff}%02x")
              .mkString
            ujson.Obj(
              "path" -> dir.resolve("export").relativize(p).toString,
              "bytes" -> bytes.length,
              "sha256" -> sha
            )
          }
      } finally stream.close()
    val value = marker(dir)
    value("exportParts") = ujson.Arr.from(parts)
    saveMarker(dir, value)
  }
}

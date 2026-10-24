package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8

/** Explicit read-only retained-export probe. It binds production manifest metadata and reads at
  * most one Parquet row from each selected table; it does not load caches or create any files.
  */
object Phase7ManifestSmokeMain {
  def main(args: Array[String]): Unit = {
    require(args.length == 1, "expected completed local Phase 6 export root")
    val root = Path.of(args(0)).toRealPath()
    val manifestPath = root.resolve("load-manifests/s3.json")
    require(Files.size(manifestPath) <= 4 * 1024 * 1024, "manifest exceeds probe metadata bound")
    val manifests = CoreJson
      .parse[Vector[LoadManifest]](Files.readString(manifestPath, UTF_8))
      .toOption
      .getOrElse(throw new IllegalArgumentException("invalid source manifest"))
    val names =
      Vector("nodes/type=researcher", "metrics/type=researcher_collaboration", "metrics/type=kcore")
    val reader = new LocalParquetManifestReader(root)
    names.foreach { name =>
      val manifest = manifests
        .find(_.logicalDataset == name)
        .getOrElse(throw new IllegalArgumentException("missing selected source dataset"))
      require(
        StorageResult.successful(reader.qualifications(manifest.context.runId)),
        "source completion binding failed"
      )
      val rows = StorageResult
        .value(reader.open(manifest))
        .getOrElse(throw new IllegalArgumentException("source metadata binding failed"))
      var sampled = 0
      try {
        if (rows.hasNext) { rows.next(); sampled = 1 }
        require(
          sampled == 0 && manifest.rowCount == 0 || sampled == 1 && manifest.rowCount > 0,
          "source sample contradicts metadata count"
        )
      } finally rows.close()
      println(
        s"dataset=$name metadataRows=${manifest.rowCount} sampledRows=$sampled metadataBinding=verified"
      )
    }
    println(
      "Read-only manifest binding and bounded Parquet smoke passed; full row counts and content hashes were not recomputed."
    )
  }
}

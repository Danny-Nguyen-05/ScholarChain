package scholarchain.build

import java.io.{File, FileInputStream}
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, StandardCopyOption}
import java.security.MessageDigest

/** Deterministic inventory of the EMR job artifacts built locally (nothing is uploaded).
  *
  * The file holds only facts derived from the artifacts and the version ledger: no clock, host,
  * user or absolute path. Paths are relative to the repository root with `/` separators, entries
  * are sorted by role, and keys are in a fixed order, so the same artifact bytes always yield the
  * same manifest bytes.
  */
object EmrArtifactManifest {
  val Schema = "scholarchain.emr-artifact-manifest.v1"

  /** @param role
    *   stable role name the pipeline refers to (`--er-jar` is `entity-resolution-job-jar`)
    * @param mainClass
    *   main class the EMR step launches, when the artifact is launched directly
    * @param byteReproducible
    *   whether two builds from the same sources are byte-identical
    */
  final case class Artifact(
      role: String,
      file: File,
      mainClass: Option[String],
      byteReproducible: Boolean
  )

  final case class Targets(
      emrRelease: String,
      scala: String,
      sparkRuntime: String,
      sparkScalaBinary: String,
      hadoopClient: String
  )

  def sha256Hex(file: File): String = {
    val digest = MessageDigest.getInstance("SHA-256")
    val input = new FileInputStream(file)
    try {
      val buffer = new Array[Byte](8192)
      var n = input.read(buffer)
      while (n >= 0) {
        if (n > 0) digest.update(buffer, 0, n)
        n = input.read(buffer)
      }
    } finally input.close()
    digest.digest().map(b => f"${b & 0xff}%02x").mkString
  }

  def render(
      repoRoot: File,
      version: String,
      targets: Targets,
      artifacts: Seq[Artifact]
  ): String = {
    require(artifacts.map(_.role).distinct.size == artifacts.size, "duplicate artifact role")
    val root = repoRoot.getCanonicalFile.toPath
    val entries = artifacts.sortBy(_.role).map { artifact =>
      require(artifact.file.isFile, s"EMR artifact missing: ${artifact.file.getAbsolutePath}")
      val path = root.relativize(artifact.file.getCanonicalFile.toPath)
      require(!path.startsWith(".."), s"artifact is outside the repository: ${artifact.file}")
      val relative = path.toString.replace(File.separatorChar, '/')
      val main = artifact.mainClass.map(m => s"""      "mainClass": ${quote(m)},\n""").getOrElse("")
      s"""    {
         |      "role": ${quote(artifact.role)},
         |      "path": ${quote(relative)},
         |      "bytes": ${artifact.file.length()},
         |      "sha256": ${quote(sha256Hex(artifact.file))},
         |$main      "byteReproducible": ${artifact.byteReproducible}
         |    }""".stripMargin
    }
    s"""{
       |  "schema": ${quote(Schema)},
       |  "projectVersion": ${quote(version)},
       |  "targets": {
       |    "emrRelease": ${quote(targets.emrRelease)},
       |    "scala": ${quote(targets.scala)},
       |    "sparkRuntime": ${quote(targets.sparkRuntime)},
       |    "sparkScalaBinary": ${quote(targets.sparkScalaBinary)},
       |    "hadoopClient": ${quote(targets.hadoopClient)}
       |  },
       |  "artifacts": [
       |${entries.mkString(",\n")}
       |  ]
       |}
       |""".stripMargin
  }

  def write(
      repoRoot: File,
      version: String,
      targets: Targets,
      artifacts: Seq[Artifact],
      output: File
  ): File = {
    val text = render(repoRoot, version, targets, artifacts)
    val parent = output.getAbsoluteFile.getParentFile
    require(parent.isDirectory || parent.mkdirs(), s"cannot create ${parent.getAbsolutePath}")
    val temp = Files.createTempFile(parent.toPath, "emr-artifact-manifest-", ".json.part")
    try {
      Files.write(temp, text.getBytes(StandardCharsets.UTF_8))
      Files.move(temp, output.toPath, StandardCopyOption.REPLACE_EXISTING)
    } finally Files.deleteIfExists(temp)
    output
  }

  private def quote(value: String): String = {
    val builder = new StringBuilder("\"")
    value.foreach {
      case '"'          => builder.append("\\\"")
      case '\\'         => builder.append("\\\\")
      case '\n'         => builder.append("\\n")
      case '\r'         => builder.append("\\r")
      case '\t'         => builder.append("\\t")
      case c if c < ' ' => builder.append(f"\\u${c.toInt}%04x")
      case c            => builder.append(c)
    }
    builder.append('"').toString
  }
}

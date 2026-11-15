package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.time.Duration
import software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.s3.S3Client
import upickle.default.read
import StorageResult.*

/** Producer for the bounded runtime artifact that the services read through
  * SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY / _SHA256 / _SOURCE_RUN_ID. Default mode is entirely local: it
  * verifies a completed Phase 6 export, selects the bounded subset (see [[RuntimeArtifactSubset]]),
  * and writes the artifact, a selection report and a pointer file. `--execute-aws` additionally
  * uploads the identical bytes with the explicit profile.
  */
object RuntimeArtifactMain {
  final case class Deps(
      reader: Path => ManifestRowReader = root => new LocalParquetManifestReader(root),
      objects: (String, String, String) => (ObjectStore, AutoCloseable) = awsObjects
  )

  private def awsObjects(
      profile: String,
      region: String,
      bucket: String
  ): (ObjectStore, AutoCloseable) = {
    val credentials = ProfileCredentialsProvider.builder().profileName(profile).build()
    val client = S3Client
      .builder()
      .region(Region.of(region))
      .credentialsProvider(credentials)
      .overrideConfiguration(
        ClientOverrideConfiguration
          .builder()
          .apiCallTimeout(Duration.ofSeconds(120))
          .apiCallAttemptTimeout(Duration.ofSeconds(60))
          .build()
      )
      .build()
    // S3ObjectStore never touches the table names; they exist only to satisfy the config type.
    val unused = DynamoTables(
      "unused-runs",
      "unused-links",
      "unused-sessions",
      "unused-evidence",
      "unused-artifacts",
      "unused-metrics",
      "unused-idempotency"
    )
    (
      new S3ObjectStore(client, edu.uic.cs441.scholarchain.storage.StorageConfig(bucket, unused)),
      new AutoCloseable {
        def close(): Unit = { client.close(); credentials.close() }
      }
    )
  }

  val usage: String =
    """RuntimeArtifactMain --source DIR --include-ids FILE --out-dir DIR [options]
      |  --source DIR            completed local Phase 6 export (contains load-manifests/s3.json)
      |  --include-ids FILE      entity IDs (researcher:... or work:...) that must be answerable
      |  --out-dir DIR           receives runtime-artifact.json, selection-report.json, pointer json
      |  --degree-window ID      window for the degree fill ordering (default all-years)
      |  --run-prefix RUN         operator run folder (^run-[a-z0-9][a-z0-9-]{1,27}$); the key becomes
      |                           runtime-artifacts/RUN/versions/<run>/runtime-subset-<sha256>.json,
      |                           the only prefix the operator loader may create. Required with --execute-aws
      |                           unless --key-prefix or --key is given
      |  --key-prefix P | --key K  object key; default <prefix>/versions/<run>/runtime-subset-<sha256>.json
      |  --max-source-rows N     reader bound (default 3000000)
      |  --execute-aws --profile P --bucket B --region R   also upload (otherwise local only)""".stripMargin

  private val valueOptions = Set(
    "--source",
    "--include-ids",
    "--out-dir",
    "--degree-window",
    "--run-prefix",
    "--key-prefix",
    "--key",
    "--max-source-rows",
    "--profile",
    "--bucket",
    "--region"
  )

  /** Fixed top-level folder of the runtime artifact; the operator loader's create-only PutObject
    * grant is scoped to `runtime-artifacts/<run_prefix>/`.
    */
  val artifactFolder: String = "runtime-artifacts"
  val runPrefixPattern: String = "^run-[a-z0-9][a-z0-9-]{1,27}$"
  def validRunPrefix(runPrefix: String): Boolean = runPrefix.matches(runPrefixPattern)

  /** The default upload key for a run prefix:
    * `runtime-artifacts/<runPrefix>/versions/<run>/<file>`. The `/versions/` segment is required by
    * the object store's immutable-key rule.
    */
  def artifactKey(runPrefix: String, sourceRunId: String, sha256: String): String = {
    require(validRunPrefix(runPrefix), "invalid run prefix")
    val run = sourceRunId.replaceAll("[^A-Za-z0-9._-]", "-")
    s"$artifactFolder/$runPrefix/versions/$run/runtime-subset-$sha256.json"
  }

  private val safeKey = "[A-Za-z0-9._=/-]{1,900}".r
  private def validKey(key: String): Boolean =
    safeKey.matches(key) && key.contains("/versions/") && !key.startsWith("/") &&
      !key.contains("//") && !key.split('/').contains("..") && !key.split('/').contains(".")
  private def validPrefix(prefix: String): Boolean =
    safeKey.matches(prefix) && !prefix.startsWith("/") && !prefix.endsWith("/") &&
      !prefix
        .contains("//") && !prefix.split('/').contains("..") && !prefix.split('/').contains(".")

  private def writeOnce(path: Path, bytes: Array[Byte]): Unit = {
    if (Files.exists(path) && !java.util.Arrays.equals(Files.readAllBytes(path), bytes))
      throw new IllegalArgumentException("existing output differs")
    if (!Files.exists(path)) Files.write(path, bytes)
  }

  private final class Refusal(message: String) extends RuntimeException(message)
  private def refuse(message: String): Nothing = throw new Refusal(message)

  def run(args: Vector[String], out: String => Unit = println, deps: Deps = Deps()): Int = {
    var closeable: Option[AutoCloseable] = None
    try {
      if (args == Vector("--help")) { out(usage); return 0 }
      val values = scala.collection.mutable.Map.empty[String, String]
      var execute = false
      var i = 0
      while (i < args.size) {
        val arg = args(i)
        if (arg == "--execute-aws") {
          if (execute) throw new IllegalArgumentException("duplicate flag")
          execute = true; i += 1
        } else {
          if (!valueOptions(arg) || i + 1 >= args.size || values.contains(arg))
            throw new IllegalArgumentException("invalid arguments")
          values(arg) = args(i + 1); i += 2
        }
      }
      def required(name: String): String =
        values.get(name).filter(_.nonEmpty).getOrElse(throw new IllegalArgumentException(name))
      val awsOptions = Vector("--profile", "--bucket", "--region")
      if (execute && awsOptions.exists(o => !values.get(o).exists(_.trim.nonEmpty)))
        refuse("--execute-aws requires --profile, --bucket and --region.")
      if (!execute && awsOptions.exists(values.contains))
        refuse("--profile, --bucket and --region require --execute-aws.")
      if (Vector("--run-prefix", "--key-prefix", "--key").count(values.contains) > 1)
        refuse("--run-prefix, --key-prefix and --key are mutually exclusive.")
      if (values.get("--run-prefix").exists(p => !validRunPrefix(p)))
        refuse(s"--run-prefix must match $runPrefixPattern.")
      if (execute && !Vector("--run-prefix", "--key-prefix", "--key").exists(values.contains))
        refuse(
          "--execute-aws requires --run-prefix (the operator loader may only create keys under runtime-artifacts/<run-prefix>/)."
        )
      if (values.get("--key").exists(k => !validKey(k)))
        refuse("--key must contain /versions/ and be a safe S3 key.")
      if (values.get("--key-prefix").exists(p => !validPrefix(p)))
        refuse("--key-prefix is not a safe S3 key prefix.")
      val degreeWindow = values.getOrElse("--degree-window", "all-years")
      if (!degreeWindow.matches("[A-Za-z0-9._-]{1,64}"))
        refuse("--degree-window is not a valid window ID.")
      val maxSourceRows = values.get("--max-source-rows") match {
        case None => 3000000L
        case Some(v) =>
          v.toLongOption
            .filter(n => n >= 1 && n <= 20000000L)
            .getOrElse(refuse("--max-source-rows must be an integer from 1 to 20000000."))
      }
      val source = Path.of(required("--source")).toRealPath()
      val outDir = Path.of(required("--out-dir")).toAbsolutePath.normalize()
      val includePath = Path.of(required("--include-ids")).toRealPath()
      if (Files.size(includePath) > IncludeList.maxBytes) refuse("include list is too large.")
      val include = IncludeList.parse(Files.readAllBytes(includePath)) match {
        case Right(list) => list
        case Left(code)  => refuse(s"$code.")
      }
      val manifestPath = source.resolve("load-manifests/s3.json").toRealPath()
      if (!manifestPath.startsWith(source) || Files.size(manifestPath) > 4 * 1024 * 1024)
        throw new IllegalArgumentException("source manifest")
      val manifests = read[Vector[LoadManifest]](Files.readString(manifestPath, UTF_8))

      val outcome = RuntimeArtifactSubset.build(
        manifests,
        deps.reader(source),
        include,
        degreeWindow = degreeWindow,
        maxSourceRows = maxSourceRows
      )
      Files.createDirectories(outDir)
      outcome.result match {
        case Left(refusal) =>
          writeOnce(outDir.resolve("selection-report.json"), pretty(outcome.report))
          out(
            s"REFUSED: ${refusal.code}${if (refusal.detail.nonEmpty) ": " + refusal.detail else ""}"
          )
          out(s"REPORT: ${outDir.resolve("selection-report.json")}")
          1
        case Right(artifact) =>
          val key = values.getOrElse(
            "--key",
            values.get("--run-prefix") match {
              case Some(runPrefix) => artifactKey(runPrefix, artifact.runId, artifact.sha256)
              case None =>
                val prefix = values.getOrElse("--key-prefix", artifactFolder)
                val run = artifact.runId.replaceAll("[^A-Za-z0-9._-]", "-")
                s"$prefix/versions/$run/runtime-subset-${artifact.sha256}.json"
            }
          )
          val pointer = RuntimeArtifactPointer(key, artifact.sha256, artifact.runId)
          outcome.report("pointer") = ujson.read(upickle.default.write(pointer))
          val artifactPath = outDir.resolve("runtime-artifact.json")
          writeOnce(artifactPath, artifact.bytes)
          writeOnce(outDir.resolve("selection-report.json"), pretty(outcome.report))
          writeOnce(
            outDir.resolve("runtime-artifact-pointer.json"),
            pretty(ujson.read(upickle.default.write(pointer)))
          )
          val selected = outcome.report("selected")
          val entities = outcome.report("entities")
          out(
            s"SELECTION: rows=${selected("totalRows").num.toLong} bytes=${selected("artifactBytes").num.toLong} " +
              s"researchers=${entities("includedResearchers").num.toLong} " +
              s"(include-list=${entities("fromIncludeList").num.toLong} fill=${entities("fromDegreeFill").num.toLong}) " +
              s"includeListSha256=${include.fileSha256}"
          )
          out(s"ARTIFACT: $artifactPath")
          out(s"REPORT: ${outDir.resolve("selection-report.json")}")
          out(s"SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY=${pointer.key}")
          out(s"SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256=${pointer.sha256}")
          out(s"SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID=${pointer.sourceRunId}")
          values.get("--bucket").foreach(b => out(s"SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET=$b"))
          if (!execute) {
            out("UPLOAD: skipped (local only; add --execute-aws --profile --bucket --region)")
            0
          } else {
            val (objects, resource) =
              deps.objects(values("--profile"), values("--region"), values("--bucket"))
            closeable = Some(resource)
            val bytes = artifact.bytes.toVector
            val put = objects.put(key, bytes, "application/json", Map.empty)
            put match {
              case r if StorageResult.successful(r) =>
                val head = StorageResult.value(objects.head(key))
                if (head.exists(h => h.sha256 == artifact.sha256 && h.size == bytes.size.toLong)) {
                  val state = if (r.isInstanceOf[Unchanged[?]]) "unchanged" else "written"
                  out(s"UPLOAD: $state s3://${values("--bucket")}/$key sha256=${artifact.sha256}")
                  0
                } else {
                  out("FAILED: upload verification (head) did not match the local artifact."); 1
                }
              case Rejected(code) => out(s"FAILED: upload rejected; reason=$code"); 1
              case _              => out("FAILED: upload rejected."); 1
            }
          }
      }
    } catch {
      case r: Refusal   => out("REFUSED: " + r.getMessage); 2
      case _: Exception => out("REFUSED: invalid arguments, configuration or source data."); 2
    } finally
      closeable.foreach(c =>
        try c.close()
        catch { case _: Exception => () }
      )
  }

  private def pretty(value: ujson.Value): Array[Byte] =
    (ujson.write(value, indent = 2) + "\n").getBytes(UTF_8)

  def main(args: Array[String]): Unit = {
    val result = run(args.toVector)
    if (result != 0)
      throw new IllegalStateException("RuntimeArtifactMain failed with exit code " + result)
  }
}

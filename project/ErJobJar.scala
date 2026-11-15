package scholarchain.build

import java.io.{BufferedOutputStream, ByteArrayOutputStream, File, FileOutputStream}
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, StandardCopyOption}
import java.time.LocalDateTime
import java.util.jar.JarFile
import java.util.zip.{ZipEntry, ZipOutputStream}
import scala.collection.mutable
import scala.jdk.CollectionConverters._

/** Fixed entry metadata shared by every JAR this build writes itself. `setTimeLocal` stores the DOS
  * local time field directly, so the bytes do not depend on the build machine's time zone or clock.
  */
object ReproducibleJar {
  val EntryTime: LocalDateTime = LocalDateTime.of(2010, 1, 1, 0, 0, 0)

  def entry(name: String): ZipEntry = {
    val next = new ZipEntry(name)
    next.setTimeLocal(EntryTime)
    next
  }
}

/** Entity-resolution job JAR for the EMR `entity-resolution` step.
  *
  * The step runs `java -Xmx.. -cp er.jar edu.uic.cs441.scholarchain.entityresolution.Phase5Main
  * resolve ...` as one JVM on the primary node (scripts/emr/sc-step.sh), so this JAR is the whole
  * classpath: the entity-resolution classes and resources, the core classes, and the Scala 3
  * runtime libraries (scala3-library_3, scala-library 2.13, upickle). It must never carry classes
  * that EMR or the portable runtime provides: Hadoop, Spark, and a logging provider.
  *
  * Reproducibility: entries are sorted by name, carry a fixed local timestamp and no extra fields,
  * the manifest is written by hand (JarOutputStream stamps the current time), and the only inputs
  * are the project JARs (sbt fixes their timestamps) and the resolved dependency JARs sorted by
  * file name. Two builds from the same sources with the same JDK produce byte-identical output; a
  * different JDK/zlib build can legitimately deflate differently.
  */
object ErJobJar {
  val MainClass = "edu.uic.cs441.scholarchain.entityresolution.Phase5Main"
  val ResourcePrefixes: Seq[String] = Seq("edu/uic/cs441/scholarchain/")

  val forbiddenPrefixes: Seq[String] = Seq(
    "org/apache/spark/",
    "org/apache/hadoop/",
    "ch/qos/logback/"
  )
  val forbiddenService = "META-INF/services/org.slf4j.spi.SLF4JServiceProvider"

  private val ManifestName = JarFile.MANIFEST_NAME
  private val ServicesPrefix = "META-INF/services/"

  def forbidden(name: String): Boolean =
    forbiddenPrefixes.exists(name.startsWith) || name == forbiddenService

  /** Entries that are metadata of one source JAR and cannot be merged meaningfully. */
  private def dropped(name: String): Boolean =
    name == ManifestName ||
      name == "module-info.class" ||
      (name.startsWith("META-INF/") && !name.startsWith(ServicesPrefix))

  def write(projectJars: Seq[File], dependencyJars: Seq[File], output: File): Unit = {
    require(projectJars.nonEmpty, "ER job JAR needs the entity-resolution and core JARs")
    val parent = output.getAbsoluteFile.getParentFile
    require(parent.isDirectory || parent.mkdirs(), s"cannot create ${parent.getAbsolutePath}")
    val temp = Files.createTempFile(parent.toPath, "er-job-", ".jar.part")
    try {
      val ordered = projectJars ++ dependencyJars.sortBy(_.getName)
      val content = mutable.TreeMap.empty[String, Array[Byte]]
      val services = mutable.TreeMap.empty[String, ByteArrayOutputStream]
      ordered.foreach { file =>
        val jar = new JarFile(file)
        try
          jar.entries().asScala.foreach { entry =>
            val name = entry.getName
            if (!entry.isDirectory && !dropped(name) && !name.startsWith("META-INF/versions/")) {
              require(
                !forbidden(name),
                s"ER job JAR would contain runtime-provided or conflicting entry: $name " +
                  s"(from ${file.getName})"
              )
              val bytes = {
                val input = jar.getInputStream(entry)
                try input.readAllBytes()
                finally input.close()
              }
              if (name.startsWith(ServicesPrefix)) {
                val buffer = services.getOrElseUpdate(name, new ByteArrayOutputStream())
                buffer.write(bytes)
                if (bytes.nonEmpty && bytes.last != '\n') buffer.write('\n')
              } else
                content.get(name) match {
                  case None => content(name) = bytes
                  case Some(previous) =>
                    require(
                      java.util.Arrays.equals(previous, bytes),
                      s"ER job JAR has conflicting duplicate entry $name (second copy from " +
                        s"${file.getName})"
                    )
                }
            }
          }
        finally jar.close()
      }
      services.foreach { case (name, buffer) => content(name) = buffer.toByteArray }

      val out = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(temp.toFile)))
      try {
        out.putNextEntry(ReproducibleJar.entry(ManifestName))
        out.write(manifestBytes)
        out.closeEntry()
        content.foreach { case (name, bytes) =>
          out.putNextEntry(ReproducibleJar.entry(name))
          out.write(bytes)
          out.closeEntry()
        }
      } finally out.close()

      verify(temp.toFile, projectJars)
      Files.move(temp, output.toPath, StandardCopyOption.REPLACE_EXISTING)
    } finally Files.deleteIfExists(temp)
  }

  private def manifestBytes: Array[Byte] =
    ("Manifest-Version: 1.0\r\n" + s"Main-Class: $MainClass\r\n\r\n")
      .getBytes(StandardCharsets.UTF_8)

  /** Fails unless the output is a complete, standalone ER job JAR. */
  def verify(output: File, projectJars: Seq[File]): Unit = {
    val result = new JarFile(output)
    val sources = projectJars.map(new JarFile(_))
    try {
      val names = result.entries().asScala.map(_.getName).toVector
      names.foreach { name =>
        require(
          !forbidden(name),
          s"ER job JAR contains runtime-provided or conflicting entry: $name"
        )
      }
      require(names.headOption.contains(ManifestName), "ER job JAR manifest must be first")
      require(names.distinct.size == names.size, "ER job JAR has duplicate entries")
      val mainEntry = MainClass.replace('.', '/') + ".class"
      require(names.contains(mainEntry), s"ER job JAR missing main class entry $mainEntry")
      val manifest = result.getManifest
      require(
        manifest != null && manifest.getMainAttributes.getValue("Main-Class") == MainClass,
        s"ER job JAR manifest Main-Class must be $MainClass"
      )
      Seq(
        "edu/uic/cs441/scholarchain/core/" -> "core module",
        "edu/uic/cs441/scholarchain/entityresolution/" -> "entity-resolution module",
        "scala/" -> "Scala library",
        "upickle/" -> "upickle"
      ).foreach { case (prefix, label) =>
        require(names.exists(_.startsWith(prefix)), s"ER job JAR missing $label entries ($prefix)")
      }
      require(
        names.contains("phase5-config.v1.json"),
        "ER job JAR missing entity-resolution resource phase5-config.v1.json"
      )
      sources.foreach { source =>
        source.entries().asScala.foreach { entry =>
          val name = entry.getName
          if (!entry.isDirectory && !dropped(name) && !name.startsWith(ServicesPrefix)) {
            val packed = result.getJarEntry(name)
            require(packed != null, s"ER job JAR missing project entry: $name")
            val expected = source.getInputStream(entry)
            val actual = result.getInputStream(packed)
            try
              require(
                java.util.Arrays.equals(expected.readAllBytes(), actual.readAllBytes()),
                s"ER job JAR has stale project entry: $name"
              )
            finally {
              expected.close()
              actual.close()
            }
          }
        }
      }
    } finally {
      sources.foreach(_.close())
      result.close()
    }
  }
}

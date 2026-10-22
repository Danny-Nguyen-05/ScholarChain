package scholarchain.build

import java.io.{BufferedOutputStream, File, FileOutputStream}
import java.nio.file.{Files, StandardCopyOption}
import java.util.jar.{JarEntry, JarFile, JarOutputStream}
import scala.collection.mutable

/** Packages the current project classes over the dependency assembly. The dependency assembly cache
  * may be reused, but this final JAR is rebuilt and checked against both current thin JARs.
  */
object SparkJobJar {
  private val forbiddenPrefixes =
    Seq("org/apache/spark/", "org/apache/hadoop/", "ch/qos/logback/")
  private val forbiddenService = "META-INF/services/org.slf4j.spi.SLF4JServiceProvider"

  private def forbidden(name: String): Boolean =
    forbiddenPrefixes.exists(name.startsWith) || name == forbiddenService

  def write(dependencies: File, core: File, spark: File, output: File): Unit = {
    val parent = output.getAbsoluteFile.getParentFile
    require(parent.isDirectory || parent.mkdirs(), s"cannot create ${parent.getAbsolutePath}")
    val temp = Files.createTempFile(parent.toPath, "spark-job-", ".jar.part")
    try {
      val jars = Seq(core, spark, dependencies).map(new JarFile(_))
      try {
        val out = new JarOutputStream(new BufferedOutputStream(new FileOutputStream(temp.toFile)))
        try {
          val written = mutable.Set.empty[String]
          jars.foreach { jar =>
            val entries = jar.entries()
            while (entries.hasMoreElements) {
              val entry = entries.nextElement()
              val name = entry.getName
              if (!entry.isDirectory && !written(name) && !signature(name)) {
                require(
                  !forbidden(name),
                  s"Spark job JAR contains runtime-provided or conflicting logging entry: $name"
                )
                written += name
                val next = new JarEntry(name)
                next.setTime(0L)
                out.putNextEntry(next)
                val input = jar.getInputStream(entry)
                try input.transferTo(out)
                finally {
                  input.close()
                  out.closeEntry()
                }
              }
            }
          }
        } finally out.close()
      } finally jars.foreach(_.close())
      verify(temp.toFile, core, spark)
      Files.move(temp, output.toPath, StandardCopyOption.REPLACE_EXISTING)
    } finally Files.deleteIfExists(temp)
  }

  def verify(output: File, core: File, spark: File): Unit = {
    val result = new JarFile(output)
    val sources = Seq(core, spark).map(new JarFile(_))
    try {
      val names = result.entries()
      while (names.hasMoreElements) {
        val name = names.nextElement().getName
        require(
          !forbidden(name),
          s"Spark job JAR contains runtime-provided or conflicting logging entry: $name"
        )
      }
      sources.foreach { source =>
        val entries = source.entries()
        while (entries.hasMoreElements) {
          val entry = entries.nextElement()
          if (!entry.isDirectory && !signature(entry.getName)) {
            val packed = result.getJarEntry(entry.getName)
            require(packed != null, s"Spark job JAR missing project entry: ${entry.getName}")
            val expected = source.getInputStream(entry)
            val actual = result.getInputStream(packed)
            try
              require(
                java.util.Arrays.equals(expected.readAllBytes(), actual.readAllBytes()),
                s"Spark job JAR has stale project entry: ${entry.getName}"
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

  private def signature(name: String): Boolean =
    name == JarFile.MANIFEST_NAME || name.startsWith("META-INF/") &&
      (name.endsWith(".SF") || name.endsWith(".DSA") || name.endsWith(".RSA"))
}

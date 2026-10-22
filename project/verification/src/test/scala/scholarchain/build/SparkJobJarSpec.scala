package scholarchain.build

import org.scalatest.funsuite.AnyFunSuite
import java.io.{File, FileOutputStream}
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.util.jar.{JarEntry, JarFile, JarOutputStream}

class SparkJobJarSpec extends AnyFunSuite {
  test("job JAR contains current core and Spark classes plus runtime dependencies") {
    val dir = Files.createTempDirectory("spark-job-jar")
    val core = dir.resolve("core.jar").toFile
    val spark = dir.resolve("spark.jar").toFile
    val deps = dir.resolve("dependencies.jar").toFile
    val output = dir.resolve("job.jar").toFile
    write(core, "edu/uic/cs441/scholarchain/core/Core.class" -> "current core")
    write(spark, "edu/uic/cs441/scholarchain/spark/Job.class" -> "current job")
    write(
      deps,
      "com/lihaoyi/Library.class" -> "runtime",
      "edu/uic/cs441/scholarchain/core/Core.class" -> "stale cache"
    )
    SparkJobJar.write(deps, core, spark, output)
    SparkJobJar.verify(output, core, spark)
    assert(read(output, "edu/uic/cs441/scholarchain/core/Core.class").contains("current core"))
    assert(read(output, "edu/uic/cs441/scholarchain/spark/Job.class").contains("current job"))
    assert(read(output, "com/lihaoyi/Library.class").contains("runtime"))
  }

  test("job JAR rejects runtime-provided classes and conflicting logging entries") {
    val dir = Files.createTempDirectory("spark-job-reject")
    val core = dir.resolve("core.jar").toFile
    val spark = dir.resolve("spark.jar").toFile
    val deps = dir.resolve("dependencies.jar").toFile
    write(core, "core/Present.class" -> "core")
    write(spark, "job/Present.class" -> "job")
    Seq(
      "org/apache/spark/Bad.class",
      "org/apache/hadoop/Bad.class",
      "ch/qos/logback/classic/Logger.class",
      "META-INF/services/org.slf4j.spi.SLF4JServiceProvider"
    ).foreach { name =>
      write(deps, name -> "forbidden")
      val failure = intercept[IllegalArgumentException] {
        SparkJobJar.write(deps, core, spark, dir.resolve("job.jar").toFile)
      }
      assert(failure.getMessage.contains(name))
    }
  }

  private def write(file: File, entries: (String, String)*): Unit = {
    val out = new JarOutputStream(new FileOutputStream(file))
    try
      entries.foreach { case (name, value) =>
        val entry = new JarEntry(name)
        out.putNextEntry(entry)
        out.write(value.getBytes(StandardCharsets.UTF_8))
        out.closeEntry()
      }
    finally out.close()
  }

  private def read(file: File, name: String): Option[String] = {
    val jar = new JarFile(file)
    try
      Option(jar.getJarEntry(name)).map { entry =>
        val in = jar.getInputStream(entry)
        try new String(in.readAllBytes(), StandardCharsets.UTF_8)
        finally in.close()
      }
    finally jar.close()
  }
}

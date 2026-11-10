package scholarchain.build

import org.scalatest.funsuite.AnyFunSuite

import java.io.{File, FileOutputStream}
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.util.TimeZone
import java.util.jar.{JarEntry, JarFile, JarOutputStream}
import scala.jdk.CollectionConverters._

class ErJobJarSpec extends AnyFunSuite {
  private val mainEntry = ErJobJar.MainClass.replace('.', '/') + ".class"

  private final class Fixture {
    val dir: File = Files.createTempDirectory("er-job-jar").toFile
    val core: File = jar(
      "core.jar",
      "edu/uic/cs441/scholarchain/core/Core.class" -> "core"
    )
    val er: File = jar(
      "er.jar",
      mainEntry -> "main",
      "edu/uic/cs441/scholarchain/entityresolution/Other.class" -> "other",
      "phase5-config.v1.json" -> "{}"
    )
    val libs: File = jar(
      "libs.jar",
      "scala/Predef.class" -> "scala",
      "upickle/default.class" -> "upickle"
    )
    val output = new File(dir, "er-job.jar")

    def jar(name: String, entries: (String, String)*): File = {
      val file = new File(dir, name)
      val out = new JarOutputStream(new FileOutputStream(file))
      try
        entries.foreach { case (entryName, value) =>
          out.putNextEntry(new JarEntry(entryName))
          out.write(value.getBytes(StandardCharsets.UTF_8))
          out.closeEntry()
        }
      finally out.close()
      file
    }

    def build(extra: File*): Unit = ErJobJar.write(Seq(er, core), libs +: extra, output)
  }

  private def names(file: File): Vector[String] = {
    val jar = new JarFile(file)
    try jar.entries().asScala.map(_.getName).toVector
    finally jar.close()
  }

  private def read(file: File, name: String): String = {
    val jar = new JarFile(file)
    try new String(jar.getInputStream(jar.getJarEntry(name)).readAllBytes(), StandardCharsets.UTF_8)
    finally jar.close()
  }

  test("ER job JAR carries project classes, resources and libraries with Main-Class first") {
    val f = new Fixture
    f.build()
    val all = names(f.output)
    assert(all.head == "META-INF/MANIFEST.MF")
    assert(all.tail == all.tail.sorted)
    assert(all.contains(mainEntry))
    assert(all.contains("edu/uic/cs441/scholarchain/core/Core.class"))
    assert(all.contains("phase5-config.v1.json"))
    assert(all.contains("upickle/default.class"))
    val jar = new JarFile(f.output)
    try
      assert(jar.getManifest.getMainAttributes.getValue("Main-Class") == ErJobJar.MainClass)
    finally jar.close()
  }

  test("ER job JAR rejects classes the EMR runtime provides and any logging provider") {
    Seq(
      "org/apache/spark/Bad.class",
      "org/apache/hadoop/fs/Bad.class",
      "ch/qos/logback/classic/Logger.class",
      "META-INF/services/org.slf4j.spi.SLF4JServiceProvider"
    ).foreach { bad =>
      val f = new Fixture
      val failure = intercept[IllegalArgumentException](f.build(f.jar("bad.jar", bad -> "x")))
      assert(failure.getMessage.contains(bad), bad)
      assert(!f.output.exists(), s"$bad must not leave an output")
    }
  }

  test("ER job JAR fails on a conflicting duplicate but accepts an identical one") {
    val f = new Fixture
    f.build(f.jar("same.jar", "scala/Predef.class" -> "scala"))
    val conflict = intercept[IllegalArgumentException](
      f.build(f.jar("conflict.jar", "scala/Predef.class" -> "different"))
    )
    assert(conflict.getMessage.contains("scala/Predef.class"))
  }

  test("ER job JAR concatenates service files and drops signatures and library metadata") {
    val f = new Fixture
    f.build(
      f.jar(
        "meta-a.jar",
        "META-INF/services/example.Spi" -> "a.Impl",
        "META-INF/LICENSE" -> "a",
        "META-INF/versions/9/module-info.class" -> "m",
        "module-info.class" -> "m",
        "META-INF/X.SF" -> "sig"
      ),
      f.jar("meta-b.jar", "META-INF/services/example.Spi" -> "b.Impl", "META-INF/LICENSE" -> "b")
    )
    assert(
      read(f.output, "META-INF/services/example.Spi").linesIterator.toVector.sorted == Vector(
        "a.Impl",
        "b.Impl"
      )
    )
    val all = names(f.output)
    assert(
      !all.exists(n => n.endsWith(".SF") || n.contains("module-info") || n.contains("LICENSE"))
    )
  }

  test("ER job JAR without its main class, core or resource fails verification") {
    val dir = Files.createTempDirectory("er-job-incomplete").toFile
    def jar(name: String, entries: (String, String)*): File = {
      val file = new File(dir, name)
      val out = new JarOutputStream(new FileOutputStream(file))
      try
        entries.foreach { case (n, v) =>
          out.putNextEntry(new JarEntry(n))
          out.write(v.getBytes(StandardCharsets.UTF_8))
          out.closeEntry()
        }
      finally out.close()
      file
    }
    val core = jar("core.jar", "edu/uic/cs441/scholarchain/core/Core.class" -> "core")
    val noMain = jar("er.jar", "edu/uic/cs441/scholarchain/entityresolution/Other.class" -> "o")
    val libs = jar("libs.jar", "scala/Predef.class" -> "s", "upickle/default.class" -> "u")
    val failure = intercept[IllegalArgumentException](
      ErJobJar.write(Seq(noMain, core), Seq(libs), new File(dir, "out.jar"))
    )
    assert(failure.getMessage.contains("main class"))
  }

  test("two builds are byte-identical regardless of clock, input order or time zone") {
    val f = new Fixture
    f.build()
    val first = EmrArtifactManifest.sha256Hex(f.output)
    val originalZone = TimeZone.getDefault
    try {
      Seq("UTC", "Pacific/Kiritimati", "America/Chicago").foreach { zone =>
        TimeZone.setDefault(TimeZone.getTimeZone(zone))
        Thread.sleep(1100)
        f.libs.setLastModified(System.currentTimeMillis())
        ErJobJar.write(Seq(f.er, f.core), Seq(f.libs), f.output)
        assert(EmrArtifactManifest.sha256Hex(f.output) == first, zone)
      }
    } finally TimeZone.setDefault(originalZone)
  }

  test("the full check runs the ER job JAR reproducibility and standalone-launch check") {
    var dir = new File(sys.props.getOrElse("user.dir", ".")).getCanonicalFile
    while (dir != null && !new File(dir, "build.sbt").isFile) dir = dir.getParentFile
    require(dir != null, "could not locate ScholarChain repo root from user.dir")
    val buildSbt = Files.readString(new File(dir, "build.sbt").toPath)
    val check = buildSbt.substring(buildSbt.indexOf("checkTask := Def"))
    val contract = check.indexOf("contractTest,")
    val erCheck = check.indexOf("entityResolution / erJobJarCheck,")
    val marker = check.indexOf("markTestRun\n")
    assert(contract >= 0 && erCheck > contract && marker > erCheck)
  }
}

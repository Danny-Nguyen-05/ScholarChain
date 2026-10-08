package scholarchain.build

import org.scalatest.funsuite.AnyFunSuite

import java.io.{File, FileOutputStream}
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.util.jar.{JarEntry, JarFile, JarOutputStream}

class HadoopBundleMergeSpec extends AnyFunSuite {
  private val work = HadoopBundleMerge.CorePrefix + "WorkRecord.class"
  private val deleted = HadoopBundleMerge.CorePrefix + "Deleted.class"
  private val added = HadoopBundleMerge.CorePrefix + "Added.class"

  test("a cached dependency assembly uses current core bytes and removes deleted core ownership") {
    val directory = Files.createTempDirectory("current-core-overlay")
    val bundle = directory.resolve("cached-bundle.jar").toFile
    val firstCore = directory.resolve("core-v1.jar").toFile
    val secondCore = directory.resolve("core-v2.jar").toFile
    write(
      bundle,
      Vector(
        "scala/External.class" -> "dependency",
        work -> "stale assembly",
        deleted -> "stale class"
      )
    )
    write(
      firstCore,
      Vector(
        work -> "core v1",
        deleted -> "deleted in v2",
        "core-settings.json" -> "old resource",
        "removed-settings.json" -> "remove in v2"
      )
    )
    HadoopBundleMerge.merge(bundle, firstCore)
    HadoopBundleMerge.verify(bundle, firstCore)
    assert(read(bundle, work).contains("core v1"))
    write(
      secondCore,
      Vector(
        work -> "core v2 has observedIdentifiers/sourceLinks",
        added -> "new class",
        "core-settings.json" -> "new resource"
      )
    )
    // Reuse the already-overlaid cached assembly, exactly as the sbt assembly task does.
    HadoopBundleMerge.merge(bundle, secondCore)
    HadoopBundleMerge.verify(bundle, secondCore)
    assert(read(bundle, work).contains("core v2 has observedIdentifiers/sourceLinks"))
    assert(read(bundle, added).contains("new class"))
    assert(read(bundle, "core-settings.json").contains("new resource"))
    assert(read(bundle, deleted).isEmpty)
    assert(read(bundle, "removed-settings.json").isEmpty)
    assert(read(bundle, "scala/External.class").contains("dependency"))
    val before = Files.readAllBytes(bundle.toPath).toVector
    HadoopBundleMerge.merge(bundle, secondCore)
    assert(Files.readAllBytes(bundle.toPath).toVector == before)
  }

  test("verification rejects stale current classes and extra removed core classes") {
    val directory = Files.createTempDirectory("verify-core-overlay")
    val core = directory.resolve("current-core.jar").toFile
    val stale = directory.resolve("stale-bundle.jar").toFile
    write(core, Vector(work -> "current bytes"))
    write(stale, Vector(work -> "stale bytes"))
    val mismatched = intercept[IllegalArgumentException](HadoopBundleMerge.verify(stale, core))
    assert(mismatched.getMessage.contains("differs from current core entry"))
    write(stale, Vector(work -> "current bytes", deleted -> "removed bytes"))
    val extra = intercept[IllegalArgumentException](HadoopBundleMerge.verify(stale, core))
    assert(extra.getMessage.contains("core namespace differs"))
  }

  private def write(file: File, entries: Vector[(String, String)]): Unit = {
    val out = new JarOutputStream(new FileOutputStream(file))
    try
      entries.foreach { case (name, body) =>
        val entry = new JarEntry(name)
        entry.setTime(0L)
        out.putNextEntry(entry)
        out.write(body.getBytes(StandardCharsets.UTF_8))
        out.closeEntry()
      }
    finally out.close()
  }

  private def read(file: File, name: String): Option[String] = {
    val jar = new JarFile(file)
    try
      Option(jar.getJarEntry(name)).map { entry =>
        val input = jar.getInputStream(entry)
        try new String(input.readAllBytes(), StandardCharsets.UTF_8)
        finally input.close()
      }
    finally jar.close()
  }
}

package scholarchain.build

import java.io.File
import java.nio.file.Files
import java.util.jar.{JarEntry, JarOutputStream}
import org.scalatest.funsuite.AnyFunSuite

class ServiceDistributionSpec extends AnyFunSuite {
  private def jar(file: File, entries: Seq[String]): File = {
    Files.createDirectories(file.toPath.getParent)
    val stream = new JarOutputStream(Files.newOutputStream(file.toPath))
    try
      entries.foreach { name =>
        stream.putNextEntry(new JarEntry(name))
        stream.write(Array[Byte](1, 2, 3))
        stream.closeEntry()
      }
    finally stream.close()
    file
  }

  private def application(root: File): File = jar(
    new File(root, "app.jar"),
    ServiceDistribution.artifacts.map(_._2.replace('.', '/') + ".class")
  )

  test(
    "distribution retains all four mains and exact dependency bytes, replacing stale libraries"
  ) {
    val root = Files.createTempDirectory("service-distribution-test").toFile
    val app = application(root)
    val dependency = jar(new File(root, "runtime.jar"), Seq("META-INF/services/example"))
    val output = new File(root, "out")
    ServiceDistribution.write(app, Seq(dependency, dependency), output)
    assert(
      Files
        .readAllBytes(new File(output, "services.jar").toPath)
        .sameElements(Files.readAllBytes(app.toPath))
    )
    assert(
      Files
        .readAllBytes(new File(output, "lib/runtime.jar").toPath)
        .sameElements(Files.readAllBytes(dependency.toPath))
    )
    val replacement = jar(new File(root, "replacement.jar"), Seq("new.class"))
    ServiceDistribution.write(app, Seq(replacement), output)
    assert(new File(output, "lib").list().toSet == Set("replacement.jar"))
    assert(
      ServiceDistribution.artifacts.map(_._1).toSet == Set(
        "query-api",
        "graph-service",
        "semantic-service",
        "embedding-worker"
      )
    )
  }

  test("missing entry point is rejected before writing output") {
    val root = Files.createTempDirectory("service-missing-main-test").toFile
    val app = jar(new File(root, "app.jar"), Seq("other.class"))
    val output = new File(root, "out")
    val error = intercept[IllegalArgumentException](ServiceDistribution.write(app, Nil, output))
    assert(error.getMessage.contains("Missing artifact main class"))
    assert(!output.exists())
  }

  test("colliding dependency names cannot silently overwrite a runtime library") {
    val root = Files.createTempDirectory("service-collision-test").toFile
    val app = application(root)
    val one = jar(new File(root, "one/dependency.jar"), Seq("one.class"))
    val two = jar(new File(root, "two/dependency.jar"), Seq("two.class"))
    val output = new File(root, "out")
    val error =
      intercept[IllegalArgumentException](ServiceDistribution.write(app, Seq(one, two), output))
    assert(error.getMessage.contains("names collide"))
    assert(!output.exists())
  }

  test("runtime assets retain nested paths and exact bytes while replacing stale assets") {
    val root = Files.createTempDirectory("service-assets-test")
    val source = root.resolve("source")
    val runtime = source.resolve("runtime/nested/synthesis.md")
    val schema = source.resolve("schemas/answer.json")
    Files.createDirectories(runtime.getParent)
    Files.createDirectories(schema.getParent)
    Files.write(runtime, Array[Byte](0, 10, 13, 127, -1))
    Files.write(schema, "{\"type\":\"object\"}".getBytes("UTF-8"))
    Files.write(source.resolve("unrelated.txt"), "excluded".getBytes("UTF-8"))
    val output = root.resolve("distribution")
    Files.createDirectories(output.resolve("prompts/runtime"))
    Files.write(output.resolve("prompts/runtime/stale.md"), Array[Byte](1))
    Files.write(output.resolve("services.jar"), Array[Byte](2))
    ServiceDistribution.writePromptAssets(source.toFile, output.toFile)
    assert(
      Files
        .readAllBytes(output.resolve("prompts/runtime/nested/synthesis.md"))
        .sameElements(Array[Byte](0, 10, 13, 127, -1))
    )
    assert(
      new String(Files.readAllBytes(output.resolve("prompts/schemas/answer.json")), "UTF-8") ==
        "{\"type\":\"object\"}"
    )
    assert(!Files.exists(output.resolve("prompts/runtime/stale.md")))
    assert(!Files.exists(output.resolve("prompts/unrelated.txt")))
    assert(Files.readAllBytes(output.resolve("services.jar")).sameElements(Array[Byte](2)))
  }

  test("missing prompt trees and symlinked assets are rejected") {
    val root = Files.createTempDirectory("service-assets-invalid-test")
    val source = root.resolve("source")
    Files.createDirectories(source.resolve("runtime"))
    Files.write(source.resolve("runtime/synthesis.md"), Array[Byte](1))
    val output = root.resolve("distribution")
    val missing = intercept[IllegalArgumentException](
      ServiceDistribution.writePromptAssets(source.toFile, output.toFile)
    )
    assert(missing.getMessage.contains("Missing runtime asset directory"))
    assert(!Files.exists(output))
    Files.createDirectories(source.resolve("schemas"))
    Files.createSymbolicLink(
      source.resolve("schemas/answer.json"),
      source.resolve("runtime/synthesis.md")
    )
    val linked = intercept[IllegalArgumentException](
      ServiceDistribution.writePromptAssets(source.toFile, output.toFile)
    )
    assert(linked.getMessage.contains("symlink"))
    assert(!Files.exists(output))
  }
}

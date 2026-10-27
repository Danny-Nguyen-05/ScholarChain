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
}

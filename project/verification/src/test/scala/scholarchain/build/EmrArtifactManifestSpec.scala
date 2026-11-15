package scholarchain.build

import org.scalatest.funsuite.AnyFunSuite

import java.io.File
import java.nio.charset.StandardCharsets
import java.nio.file.Files

class EmrArtifactManifestSpec extends AnyFunSuite {
  private val targets = EmrArtifactManifest.Targets("emr-7.8.0", "3.3.4", "3.5.4", "2.13", "3.3.6")

  private def fixture(): (File, Seq[EmrArtifactManifest.Artifact]) = {
    val root = Files.createTempDirectory("emr-manifest").toFile
    def artifact(role: String, name: String, body: String, main: Option[String]) = {
      val file = new File(root, s"modules/$name/target/$name.jar")
      file.getParentFile.mkdirs()
      Files.write(file.toPath, body.getBytes(StandardCharsets.UTF_8))
      EmrArtifactManifest.Artifact(role, file, main, byteReproducible = true)
    }
    (
      root,
      Seq(
        artifact("spark-job-jar", "spark", "spark bytes", Some("a.Spark")),
        artifact("entity-resolution-job-jar", "er", "abc", Some("a.Er")),
        artifact("hadoop-dependency-bundle", "bundle", "", None)
      )
    )
  }

  test("manifest lists role, relative path, bytes and sha256 sorted by role") {
    val (root, artifacts) = fixture()
    val text = EmrArtifactManifest.render(root, "0.1.0-SNAPSHOT", targets, artifacts)
    assert(text.contains(""""schema": "scholarchain.emr-artifact-manifest.v1""""))
    assert(text.contains(""""path": "modules/er/target/er.jar""""))
    assert(text.contains(""""bytes": 3,"""))
    // sha256("abc") and sha256("") are well-known vectors
    assert(text.contains("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"))
    assert(text.contains("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"))
    val roles = """"role": "([^"]+)"""".r.findAllMatchIn(text).map(_.group(1)).toVector
    assert(
      roles == Vector("entity-resolution-job-jar", "hadoop-dependency-bundle", "spark-job-jar")
    )
    assert(!text.contains(root.getCanonicalPath), "no absolute path may leak into the manifest")
    assert(!text.contains(root.getAbsolutePath))
  }

  test("manifest bytes depend only on artifact bytes, not on input order or write time") {
    val (root, artifacts) = fixture()
    val a = new File(root, "target/a.json")
    val b = new File(root, "target/b.json")
    EmrArtifactManifest.write(root, "v", targets, artifacts, a)
    Thread.sleep(1100)
    EmrArtifactManifest.write(root, "v", targets, artifacts.reverse, b)
    assert(Files.readAllBytes(a.toPath).sameElements(Files.readAllBytes(b.toPath)))
  }

  test("manifest rejects a missing artifact, a duplicate role and an outside path") {
    val (root, artifacts) = fixture()
    val missing = artifacts.head.copy(file = new File(root, "missing.jar"))
    intercept[IllegalArgumentException](
      EmrArtifactManifest.render(root, "v", targets, Seq(missing))
    )
    intercept[IllegalArgumentException](
      EmrArtifactManifest.render(root, "v", targets, artifacts :+ artifacts.head)
    )
    val outside = Files.createTempFile("outside", ".jar").toFile
    intercept[IllegalArgumentException](
      EmrArtifactManifest.render(root, "v", targets, Seq(artifacts.head.copy(file = outside)))
    )
  }
}

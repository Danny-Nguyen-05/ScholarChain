package scholarchain.build

import org.scalatest.funsuite.AnyFunSuite

import java.io.File
import java.nio.file.Files
import scala.sys.process._

/** Requirement (Phase 6 review 6A F6): packaging must fail fast, before producing an artifact,
  * whenever the sbt JVM is not Java 17. The same guard (`checkJava17`, backed by [[Java17Guard]])
  * protects `check` and every packaging entry point.
  */
class PackagingJava17GuardSpec extends AnyFunSuite {
  private val repoRoot = locateRepoRoot()
  private val buildSbt = Files.readString(new File(repoRoot, "build.sbt").toPath)
  private val buildScala =
    Files.readString(new File(repoRoot, "project/ScholarChainBuild.scala").toPath)

  test("the shared guard rejects every specification version except exactly 17") {
    Seq("8", "1.8", "11", "21", "25", "27", "", "17.0.1", " 17").foreach { version =>
      val failure = intercept[IllegalArgumentException](Java17Guard.requireJava17(version))
      assert(failure.getMessage.contains("requires Java 17"), version)
      assert(failure.getMessage.contains(s"found Java $version"), version)
      assert(failure.getMessage.contains("JAVA_HOME"), version)
    }
    Java17Guard.requireJava17("17")
  }

  test("checkJava17 is defined once, build-wide, from the shared guard") {
    assert(buildSbt.contains("ThisBuild / checkJava17 :="))
    assert(
      buildSbt.contains("Java17Guard.requireJava17(sys.props(\"java.specification.version\"))")
    )
    assert("""(?m)^\s*checkJava17 :=""".r.findFirstIn(buildSbt).isEmpty)
    assert("requirement failed|requires Java 17".r.findFirstIn(buildSbt + buildScala).isEmpty)
  }

  test("each packaging task body runs checkJava17 before it builds anything") {
    Seq(
      (buildScala, "serviceDistribution :="),
      (buildScala, "sparkJobJar :="),
      (buildScala, "erJobJar :="),
      (buildSbt, "emrArtifactManifest :="),
      (buildScala, "hadoopDependencyBundle :="),
      (buildScala, "hadoopSubmitJar :="),
      (buildSbt, "dockerLocalImage :=")
    ).foreach { case (source, header) =>
      val index = source.indexOf(header)
      assert(index >= 0, s"missing $header")
      val body = source.substring(index + header.length).linesIterator.take(3).mkString("\n")
      assert(
        body.contains("checkJava17.value"),
        s"$header must call checkJava17.value in its first statements"
      )
    }
  }

  test("assembly entry points and module jars depend on checkJava17") {
    Seq(
      "assembly := assembly.dependsOn(checkJava17)",
      "assemblyPackageDependency := assemblyPackageDependency.dependsOn(checkJava17)",
      "Compile / packageBin := (Compile / packageBin).dependsOn(checkJava17)"
    ).foreach(setting => assert(buildScala.contains(setting), setting))
    Seq("sparkJobJarSettings", "hadoopDependencyBundleSettings").foreach { definition =>
      val pattern = s"""(?s)def $definition.*?\\) \\+\\+ assemblyJava17GuardSettings""".r
      assert(pattern.findFirstIn(buildScala).isDefined, definition)
    }
    assert(buildScala.contains("commonSettings: Seq[Setting[_]] = packageJava17GuardSettings"))
  }

  test(
    "packaging aliases start with the guard and packageRelease builds the release and EMR artifacts"
  ) {
    val jobs = alias("packageJobs")
    val release = alias("packageRelease")
    Seq(jobs, release).foreach(value => assert(value.startsWith(";checkJava17;"), value))
    val steps = release.split(';').map(_.trim).filter(_.nonEmpty).toVector
    assert(
      steps == Vector(
        "checkJava17",
        "hadoop/hadoopSubmitJar",
        "hadoop/hadoopDependencyBundle",
        "sparkAnalytics/sparkJobJar",
        "entityResolution/erJobJar",
        "services/serviceDistribution",
        "emrArtifactManifest"
      )
    )
    val emr = alias("packageEmr")
    assert(emr.startsWith(";checkJava17;"), emr)
    assert(
      emr.split(';').map(_.trim).filter(_.nonEmpty).toVector == Vector(
        "checkJava17",
        "hadoop/hadoopSubmitJar",
        "hadoop/hadoopDependencyBundle",
        "sparkAnalytics/sparkJobJar",
        "entityResolution/erJobJar",
        "emrArtifactManifest"
      )
    )
    assert(!release.toLowerCase.contains("docker"))
  }

  test(
    "packageRelease under a non-17 JVM fails fast with the guard message (optional live probe)"
  ) {
    val nonSeventeen = sys.env.get("SCHOLARCHAIN_NON17_JAVA_HOME").filter(_.nonEmpty)
    assume(
      nonSeventeen.isDefined,
      "set SCHOLARCHAIN_NON17_JAVA_HOME to a non-17 JDK to run this probe"
    )
    val javaHome = nonSeventeen.get
    val output = new StringBuilder
    val logger = ProcessLogger(line => output.append(line).append('\n'))
    val exit = Process(
      Seq("sbt", "-batch", "packageRelease"),
      repoRoot,
      "JAVA_HOME" -> javaHome,
      "PATH" -> s"$javaHome/bin${File.pathSeparator}${sys.env.getOrElse("PATH", "")}"
    ).!(logger)
    assert(exit != 0, output.toString)
    assert(output.toString.contains("requires Java 17"), output.toString)
  }

  private def alias(name: String): String = {
    val start = buildSbt.indexOf(s"\"$name\"")
    assert(start >= 0, s"missing alias $name")
    val end = buildSbt.indexOf("\n)", start)
    val block = buildSbt.substring(start + name.length + 2, end)
    "\"([^\"]*)\"".r.findAllMatchIn(block).map(_.group(1)).mkString
  }

  private def locateRepoRoot(): File = {
    var dir = new File(sys.props.getOrElse("user.dir", ".")).getCanonicalFile
    while (dir != null && !new File(dir, "build.sbt").isFile)
      dir = dir.getParentFile
    require(dir != null, "could not locate ScholarChain repo root from user.dir")
    dir
  }
}

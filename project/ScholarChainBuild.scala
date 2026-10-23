import sbt._
import sbt.Keys._
import sbt.librarymanagement.ModuleID
import sbtassembly.AssemblyPlugin.autoImport._
import sbtassembly.{MergeStrategy, PathList}

import java.io.{BufferedOutputStream, File, FileInputStream, FileOutputStream}
import java.security.MessageDigest
import java.util.jar.{JarEntry, JarFile, JarOutputStream, Manifest}
import scala.jdk.CollectionConverters._
import sbt.io.IO
import scholarchain.build.{HadoopBundleMerge, SparkJobJar}

object ScholarChainBuild {
  val markTestRun = taskKey[Unit]("Write .claude/.last-test-run after required checks succeed")
  val contractTest = taskKey[Unit]("AWS-free contract tests")
  val checkTask = taskKey[Unit]("Format check, compile, test, contract tests, markTestRun")
  val checkProbeInjectFailure =
    taskKey[Unit]("No-op unless -Dscholarchain.checkProbe.fail=true (check failure-path probe)")
  val checkJava17 = taskKey[Unit]("Fail check unless the sbt JVM is Java 17")
  val dockerLocalImage = taskKey[Unit]("Build the local services container image")
  val hadoopLocalClasspath =
    taskKey[Unit]("Print hadoop Compile/fullClasspath (includes Provided hadoop-client)")
  val hadoopRunMain =
    inputKey[Unit](
      "Foreground runMain on Compile/fullClasspath (includes Provided hadoop-client)"
    )
  val hadoopDependencyBundle =
    taskKey[File](
      "Fat JAR of core and non-Hadoop runtime libraries for EMR -libjars (excludes hadoop module classes and Apache Hadoop)"
    )
  val hadoopSubmitJar =
    taskKey[File](
      "Thin Hadoop JAR plus lib/<dependency bundle> for RunJar's driver classpath"
    )
  val sparkJobJar =
    taskKey[File]("EMR Spark job JAR with Spark classes, core and non-Spark runtime libraries")
  val AwsIntegration = config("awsIntegration").extend(Test)
  val requireAwsIntegration = taskKey[Unit]("Require explicit AWS live-test opt-in and profile")

  val awsIntegrationSettings: Seq[Setting[_]] =
    inConfig(AwsIntegration)(Defaults.testSettings) ++ Seq(
      AwsIntegration / scalaSource := (Test / scalaSource).value,
      AwsIntegration / javaSource := (Test / javaSource).value,
      AwsIntegration / resourceDirectory := (Test / resourceDirectory).value,
      AwsIntegration / fork := true,
      AwsIntegration / parallelExecution := false,
      AwsIntegration / testOptions := Seq(
        Tests.Argument(TestFrameworks.ScalaTest, "-n", scholarchain.build.AwsIntegrationPolicy.tag)
      ),
      AwsIntegration / requireAwsIntegration :=
        scholarchain.build.AwsIntegrationPolicy.requireEnabled(sys.env),
      // The test loader is shared by test, testOnly, testQuick and executeTests.
      // Gate it as well as the public entry points so selection cannot bypass opt-in.
      AwsIntegration / testLoader := (AwsIntegration / testLoader)
        .dependsOn(AwsIntegration / requireAwsIntegration)
        .value,
      AwsIntegration / test := (AwsIntegration / test)
        .dependsOn(AwsIntegration / requireAwsIntegration)
        .value,
      AwsIntegration / testOnly := (AwsIntegration / testOnly)
        .dependsOn(AwsIntegration / requireAwsIntegration)
        .evaluated,
      AwsIntegration / testQuick := (AwsIntegration / testQuick)
        .dependsOn(AwsIntegration / requireAwsIntegration)
        .evaluated
    )

  val sparkTestJavaOptions: Seq[String] = Seq(
    "-Xmx2g",
    "-Dspark.ui.enabled=false",
    "-Djava.net.preferIPv4Stack=true"
  ) ++ Seq(
    "java.base/java.lang",
    "java.base/java.lang.invoke",
    "java.base/java.lang.reflect",
    "java.base/java.io",
    "java.base/java.net",
    "java.base/java.nio",
    "java.base/java.util",
    "java.base/java.util.concurrent",
    "java.base/java.util.concurrent.atomic",
    "java.base/jdk.internal.ref",
    "java.base/sun.nio.ch",
    "java.base/sun.nio.cs",
    "java.base/sun.security.action",
    "java.base/sun.util.calendar",
    "java.security.jgss/sun.security.krb5"
  ).map(module => s"--add-opens=$module=ALL-UNNAMED")

  private val sparkMavenOrg = "org.apache.spark"

  private def isRuntimeProvided(moduleId: ModuleID): Boolean =
    Seq(hadoopMavenOrg, sparkMavenOrg, "ch.qos.logback").exists(org =>
      moduleId.organization == org || moduleId.organization.startsWith(s"$org.")
    )

  private def isRuntimeProvidedJar(name: String): Boolean = {
    val lower = name.toLowerCase(java.util.Locale.ROOT)
    lower.startsWith("hadoop-") || lower.startsWith("spark-") || lower.startsWith("logback-")
  }

  def sparkJobJarSettings(coreProject: ProjectReference): Seq[Setting[_]] = Seq(
    assemblyPackageDependency / assemblyJarName :=
      s"spark-dependency-bundle_${scalaBinaryVersion.value}-${version.value}.jar",
    assemblyPackageDependency / assemblyOutputPath :=
      (assembly / target).value / (assemblyPackageDependency / assemblyJarName).value,
    assemblyMergeStrategy := {
      case PathList("META-INF", "MANIFEST.MF") => MergeStrategy.discard
      case PathList("META-INF", "services", "org.slf4j.spi.SLF4JServiceProvider") =>
        MergeStrategy.discard
      case PathList("META-INF", "services", _*) => MergeStrategy.concat
      case PathList("META-INF", _*)             => MergeStrategy.discard
      case "module-info.class"                  => MergeStrategy.discard
      case x if x.endsWith(".proto")            => MergeStrategy.first
      case x                                    => MergeStrategy.first
    },
    assemblyPackageDependency / assemblyExcludedJars := {
      (assembly / fullClasspath).value.filter { entry =>
        entry.get(moduleID.key).exists(isRuntimeProvided) ||
        isRuntimeProvidedJar(entry.data.getName)
      }
    },
    sparkJobJar := {
      val coreJar = (coreProject / Compile / packageBin).value
      val sparkJar = (Compile / packageBin).value
      val bundle = assemblyPackageDependency.value
      val output =
        (Compile / target).value / s"spark-job_${scalaBinaryVersion.value}-${version.value}.jar"
      SparkJobJar.write(bundle, coreJar, sparkJar, output)
      streams.value.log.info(s"Verified Spark job JAR: ${output.getAbsolutePath}")
      output
    }
  )

  private val hadoopMavenOrg = "org.apache.hadoop"
  private val submitJarForbiddenLibMarkers = Vector(
    "org/apache/hadoop/",
    "edu/uic/cs441/scholarchain/hadoop/"
  )

  private def isHadoopMavenModule(moduleId: ModuleID): Boolean =
    moduleId.organization == hadoopMavenOrg ||
      moduleId.organization.startsWith(s"$hadoopMavenOrg.")

  private def isHadoopArtifactFileName(name: String): Boolean = {
    val lower = name.toLowerCase(java.util.Locale.ROOT)
    lower.startsWith("hadoop-") ||
    lower.contains(s"${java.io.File.separator}org.apache.hadoop${java.io.File.separator}")
  }

  def hadoopDependencyBundleSettings(coreProject: ProjectReference): Seq[Setting[_]] = Seq(
    assemblyPackageDependency / assemblyJarName :=
      s"hadoop-dependency-bundle_${scalaBinaryVersion.value}-${version.value}.jar",
    assemblyPackageDependency / assemblyOutputPath :=
      (assembly / target).value / (assemblyPackageDependency / assemblyJarName).value,
    assemblyMergeStrategy := {
      case PathList("META-INF", "MANIFEST.MF")  => MergeStrategy.discard
      case PathList("META-INF", "services", _*) => MergeStrategy.concat
      case PathList("META-INF", _*)             => MergeStrategy.discard
      case "module-info.class"                  => MergeStrategy.discard
      case x if x.endsWith(".proto")            => MergeStrategy.first
      case x                                    => MergeStrategy.first
    },
    assemblyPackageDependency / assemblyExcludedJars := {
      (assembly / fullClasspath).value.filter { entry =>
        entry.get(moduleID.key).exists(isHadoopMavenModule) ||
        isHadoopArtifactFileName(entry.data.getName)
      }
    },
    hadoopDependencyBundle := {
      val coreJar = (coreProject / Compile / packageBin).value
      val _ = assemblyPackageDependency.value
      val bundle = (assemblyPackageDependency / assemblyOutputPath).value
      mergeCoreJarIntoBundle(bundle, coreJar, streams.value.log)
      verifyHadoopDependencyBundle(bundle, coreJar, streams.value.log)
      bundle
    },
    hadoopSubmitJar := {
      val thinJar = (Compile / packageBin).value
      val bundle = hadoopDependencyBundle.value
      val submitName =
        s"hadoop-submit_${scalaBinaryVersion.value}-${version.value}.jar"
      val out = thinJar.getParentFile / submitName
      writeHadoopSubmitJar(thinJar, bundle, out, streams.value.log)
      out
    }
  )

  private def mergeCoreJarIntoBundle(bundle: File, coreJar: File, log: sbt.util.Logger): Unit = {
    HadoopBundleMerge.merge(bundle, coreJar)
    log.info(s"Merged core module JAR into dependency bundle: ${coreJar.getName}")
  }

  private def verifyHadoopDependencyBundle(
      bundle: File,
      coreJar: File,
      log: sbt.util.Logger
  ): Unit = {
    if (!bundle.isFile)
      sys.error(s"hadoop dependency bundle missing: ${bundle.getAbsolutePath}")

    HadoopBundleMerge.verify(bundle, coreJar)
    val jar = new JarFile(bundle)
    try {
      val entries = jar.entries().asScala.map(_.getName).toVector
      val hadoopClasses = entries.filter(_.startsWith("org/apache/hadoop/"))
      if (hadoopClasses.nonEmpty) {
        val sample = hadoopClasses.take(5).mkString(", ")
        sys.error(
          s"Bundle must not contain org.apache.hadoop classes (found $sample); check assemblyExcludedJars"
        )
      }

      val hadoopModuleClasses =
        entries.filter(_.startsWith("edu/uic/cs441/scholarchain/hadoop/"))
      if (hadoopModuleClasses.nonEmpty) {
        val sample = hadoopModuleClasses.take(5).mkString(", ")
        sys.error(
          s"Bundle must not contain hadoop module classes (found $sample); use assemblyPackageDependency and keep hadoop classes in the thin JAR"
        )
      }

      def requirePrefix(prefix: String, label: String): Unit =
        if (!entries.exists(_.startsWith(prefix)))
          sys.error(s"Bundle missing expected $label entries under $prefix")

      requirePrefix("edu/uic/cs441/scholarchain/core/", "core module")
      requirePrefix("scala/", "Scala library")

      val hasUpickle =
        entries.exists(e => e.startsWith("upickle/") || e.startsWith("ujson/"))
      if (!hasUpickle)
        sys.error("Bundle missing expected upickle/ujson library entries")

      log.info(s"Verified non-Hadoop dependency bundle: ${bundle.getAbsolutePath}")
    } finally jar.close()
  }

  private def writeHadoopSubmitJar(
      thinJar: File,
      bundle: File,
      out: File,
      log: sbt.util.Logger
  ): Unit = {
    if (!bundle.isFile)
      sys.error(s"hadoop dependency bundle missing: ${bundle.getAbsolutePath}")
    verifyThinJarStaysThin(thinJar)
    val parent = out.getParentFile
    if (parent == null || (!parent.isDirectory && !parent.mkdirs()))
      sys.error(s"cannot create submit JAR directory for ${out.getAbsolutePath}")

    val libEntryName = s"lib/${bundle.getName}"
    val tmp = File.createTempFile("hadoop-submit-", ".jar.part", parent)
    tmp.deleteOnExit()
    try {
      copyThinJarWithLibBundle(thinJar, bundle, tmp, libEntryName)
      verifyHadoopSubmitJar(tmp, thinJar, bundle, libEntryName)
      IO.delete(out)
      IO.move(tmp, out)
    } catch {
      case e: Throwable =>
        IO.delete(tmp)
        throw e
    }
    log.info(s"Verified Hadoop submit JAR: ${out.getAbsolutePath}")
    log.info(s"RunJar lib entry: $libEntryName")
  }

  private def verifyThinJarStaysThin(thinJar: File): Unit = {
    if (!thinJar.isFile)
      sys.error(s"thin Hadoop JAR missing: ${thinJar.getAbsolutePath}")
    val jar = new JarFile(thinJar)
    try {
      val names = jar.entries().asScala.map(_.getName).toVector
      val libEntries = names.filter(name => name == "lib" || name.startsWith("lib/"))
      if (libEntries.nonEmpty) {
        val sample = libEntries.take(5).mkString(", ")
        sys.error(s"thin JAR must stay thin and not embed lib/ (found $sample)")
      }
      val hadoopClasses = names.filter(_.contains("org/apache/hadoop/"))
      if (hadoopClasses.nonEmpty) {
        val sample = hadoopClasses.take(5).mkString(", ")
        sys.error(s"thin JAR must not contain org.apache.hadoop classes (found $sample)")
      }
    } finally jar.close()
  }

  private def copyThinJarWithLibBundle(
      thinJar: File,
      bundle: File,
      dest: File,
      libEntryName: String
  ): Unit = {
    val thin = new JarFile(thinJar)
    try {
      val manifest = Option(thin.getManifest).getOrElse(new Manifest())
      val jarOut =
        new JarOutputStream(new BufferedOutputStream(new FileOutputStream(dest)), manifest)
      try {
        val written = scala.collection.mutable.Set.empty[String]
        written += JarFile.MANIFEST_NAME
        thin.entries().asScala.foreach { entry =>
          if (!entry.isDirectory) {
            val name = entry.getName
            if (name == JarFile.MANIFEST_NAME || written.contains(name)) ()
            else {
              written += name
              jarOut.putNextEntry(new JarEntry(name))
              val input = thin.getInputStream(entry)
              try IO.transfer(input, jarOut)
              finally {
                input.close()
                jarOut.closeEntry()
              }
            }
          }
        }
        if (written.contains(libEntryName))
          sys.error(s"thin JAR already contains $libEntryName")
        jarOut.putNextEntry(new JarEntry(libEntryName))
        try IO.transfer(bundle, jarOut)
        finally jarOut.closeEntry()
      } finally jarOut.close()
    } finally thin.close()
  }

  private def verifyHadoopSubmitJar(
      submit: File,
      thinJar: File,
      bundle: File,
      libEntryName: String
  ): Unit = {
    val thinNames = fileEntryNames(thinJar).toSet
    val submitNames = fileEntryNames(submit).toSet
    val expected = thinNames + libEntryName
    if (submitNames != expected) {
      val missing = expected.diff(submitNames).take(5).mkString(", ")
      val extra = submitNames.diff(expected).take(5).mkString(", ")
      sys.error(
        s"submit JAR must be the thin JAR plus $libEntryName; missing [$missing]; extra [$extra]"
      )
    }

    val libNames = submitNames.filter(_.startsWith("lib/"))
    if (libNames.isEmpty)
      sys.error(s"submit JAR has no lib/ entry: ${submit.getAbsolutePath}")
    if (libNames != Set(libEntryName)) {
      val found = libNames.mkString(", ")
      sys.error(s"submit JAR lib/ must contain exactly the dependency bundle, found $found")
    }
    rejectForbiddenLibPath(libEntryName, s"submit JAR entry $libEntryName")

    val extracted = extractLibEntry(submit, libEntryName)
    try {
      if (sha256Hex(extracted) != sha256Hex(bundle))
        sys.error(
          s"$libEntryName bytes do not match the verified dependency bundle " +
            bundle.getAbsolutePath
        )
      rejectForbiddenEntriesInNestedJar(extracted, libEntryName)
    } finally IO.delete(extracted)
  }

  private def fileEntryNames(jarFile: File): Vector[String] = {
    val jar = new JarFile(jarFile)
    try jar.entries().asScala.filterNot(_.isDirectory).map(_.getName).toVector
    finally jar.close()
  }

  private def extractLibEntry(submit: File, libEntryName: String): File = {
    val jar = new JarFile(submit)
    try {
      val entry = jar.getJarEntry(libEntryName)
      if (entry == null || entry.isDirectory)
        sys.error(s"submit JAR is missing file entry $libEntryName")
      val extracted = File.createTempFile("hadoop-submit-lib-", ".jar")
      extracted.deleteOnExit()
      val input = jar.getInputStream(entry)
      val output = new BufferedOutputStream(new FileOutputStream(extracted))
      try IO.transfer(input, output)
      finally {
        output.close()
        input.close()
      }
      extracted
    } finally jar.close()
  }

  private def rejectForbiddenEntriesInNestedJar(nestedJar: File, label: String): Unit = {
    val jar = new JarFile(nestedJar)
    try {
      var sawEntry = false
      jar.entries().asScala.foreach { entry =>
        sawEntry = true
        rejectForbiddenLibPath(entry.getName, s"$label entry ${entry.getName}")
      }
      if (!sawEntry) sys.error(s"$label has no zip entries")
    } finally jar.close()
  }

  private def rejectForbiddenLibPath(name: String, label: String): Unit =
    submitJarForbiddenLibMarkers.find(name.contains).foreach { marker =>
      sys.error(
        s"$label contains '$marker'; do not shade Hadoop or put hadoop module classes under lib/"
      )
    }

  private def sha256Hex(file: File): String = {
    val digest = MessageDigest.getInstance("SHA-256")
    val input = new FileInputStream(file)
    try {
      val buf = new Array[Byte](8192)
      var n = input.read(buf)
      while (n >= 0) {
        if (n > 0) digest.update(buf, 0, n)
        n = input.read(buf)
      }
    } finally input.close()
    digest.digest().map(b => f"${b & 0xff}%02x").mkString
  }

  lazy val commonSettings: Seq[Setting[_]] = Seq(
    scalaVersion := Versions.scala3,
    scalacOptions ++= Seq("-deprecation", "-feature"),
    libraryDependencies ++= Seq(
      Dependencies.upickleLib,
      Dependencies.slf4jApi,
      Dependencies.logbackClassic,
      Dependencies.scalaTestLib
    ),
    Test / parallelExecution := false,
    Test / testOptions += Tests.Argument(
      TestFrameworks.ScalaTest,
      "-l",
      scholarchain.build.AwsIntegrationPolicy.tag
    )
  )

  def moduleSettings(extra: Seq[ModuleID] = Nil): Seq[Setting[_]] =
    commonSettings ++ Seq(libraryDependencies ++= extra)

  val sparkTestSettings: Seq[Setting[_]] = Seq(
    libraryDependencies -= Dependencies.logbackClassic,
    Test / fork := true,
    Test / javaOptions ++= sparkTestJavaOptions,
    Test / baseDirectory := (ThisBuild / baseDirectory).value,
    Test / unmanagedResourceDirectories +=
      (ThisBuild / baseDirectory).value / "project" / "spark-test-resources"
  )
}

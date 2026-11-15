import ScholarChainBuild._
import sbt.Keys._
import sbtassembly.AssemblyPlugin
import scholarchain.build.{EmrArtifactManifest, ErJobJar, ServiceDistribution}

ThisBuild / organization := "edu.uic.cs441.scholarchain"
ThisBuild / version := "0.1.0-SNAPSHOT"
// One guard for check and for every packaging task (resolved by delegation in all projects).
ThisBuild / checkJava17 :=
  scholarchain.build.Java17Guard.requireJava17(sys.props("java.specification.version"))

lazy val buildVerification =
  project
    .in(file("build-verification"))
    .configs(AwsIntegration)
    .settings(
      name := "build-verification",
      ScholarChainBuild.commonSettings,
      ScholarChainBuild.awsIntegrationSettings,
      publish / skip := true,
      Compile / scalaSource :=
        (ThisBuild / baseDirectory).value / "project/verification/src/main/scala",
      Compile / unmanagedSources +=
        (ThisBuild / baseDirectory).value / "project/HadoopBundleMerge.scala",
      Compile / unmanagedSources +=
        (ThisBuild / baseDirectory).value / "project/SparkJobJar.scala",
      Compile / unmanagedSources +=
        (ThisBuild / baseDirectory).value / "project/ErJobJar.scala",
      Compile / unmanagedSources +=
        (ThisBuild / baseDirectory).value / "project/EmrArtifactManifest.scala",
      Compile / unmanagedSources +=
        (ThisBuild / baseDirectory).value / "project/Java17Guard.scala",
      Compile / unmanagedSources +=
        (ThisBuild / baseDirectory).value / "project/AwsIntegrationPolicy.scala",
      Compile / unmanagedSources +=
        (ThisBuild / baseDirectory).value / "project/ServiceDistribution.scala",
      Test / scalaSource :=
        (ThisBuild / baseDirectory).value / "project/verification/src/test/scala"
    )

lazy val core =
  project
    .in(file("modules/core"))
    .settings(ScholarChainBuild.moduleSettings(), name := "core")

lazy val hadoop =
  project
    .in(file("modules/hadoop"))
    .enablePlugins(AssemblyPlugin)
    .dependsOn(core)
    .settings(
      ScholarChainBuild.moduleSettings(Seq(Dependencies.hadoopClientLib)),
      ScholarChainBuild.hadoopDependencyBundleSettings(core),
      name := "hadoop",
      Compile / run / fork := true,
      Compile / run / baseDirectory := (ThisBuild / baseDirectory).value,
      ScholarChainBuild.hadoopRunMain := (Compile / fgRunMain).evaluated,
      ScholarChainBuild.hadoopLocalClasspath := {
        val cp = (Compile / fullClasspath).value
        val line = cp.files.map(_.getAbsolutePath).mkString(java.io.File.pathSeparator)
        streams.value.log.info(line)
      }
    )

lazy val independentTests =
  project
    .in(file("tests"))
    .dependsOn(core, hadoop, entityResolution, sparkAnalytics, storage, rag, services)
    .settings(
      ScholarChainBuild.moduleSettings(
        Seq(Dependencies.hadoopClientLib, Dependencies.sparkSql, Dependencies.sparkScalaReflectLib)
      ),
      ScholarChainBuild.sparkTestSettings,
      name := "independentTests",
      publish / skip := true
    )

lazy val entityResolution =
  project
    .in(file("modules/entity-resolution"))
    .dependsOn(core)
    .settings(
      ScholarChainBuild.moduleSettings(),
      ScholarChainBuild.erJobJarSettings(core),
      name := "entityResolution"
    )

lazy val sparkAnalytics =
  project
    .in(file("modules/spark"))
    .dependsOn(core)
    .enablePlugins(AssemblyPlugin)
    .settings(
      ScholarChainBuild.moduleSettings(
        Seq(Dependencies.sparkSql, Dependencies.sparkScalaReflectLib)
      ),
      ScholarChainBuild.sparkJobJarSettings(core),
      ScholarChainBuild.sparkTestSettings,
      name := "sparkAnalytics"
    )

lazy val storage =
  project
    .in(file("modules/storage"))
    .configs(AwsIntegration)
    .dependsOn(core)
    .settings(
      ScholarChainBuild.moduleSettings(
        Seq(
          Dependencies.awsS3,
          Dependencies.awsDynamoDb,
          Dependencies.awsNeptuneData,
          Dependencies.awsS3Vectors,
          Dependencies.awsSqs,
          Dependencies.parquetHadoop,
          Dependencies.storageHadoopClient
        )
      ),
      ScholarChainBuild.awsIntegrationSettings,
      name := "storage"
    )

lazy val rag =
  project
    .in(file("modules/rag"))
    .dependsOn(core, storage)
    .settings(
      ScholarChainBuild.moduleSettings(Seq(Dependencies.awsBedrockRuntime)),
      name := "rag",
      Compile / run / fork := true,
      Compile / run / baseDirectory := (ThisBuild / baseDirectory).value,
      Compile / run / javaOptions ++= sys.props
        .get("logback.configurationFile")
        .map(path => s"-Dlogback.configurationFile=$path")
        .toSeq
    )

lazy val services =
  project
    .in(file("modules/services"))
    .dependsOn(core, rag, storage)
    .settings(
      ScholarChainBuild.moduleSettings(Seq(Dependencies.caskLib)),
      ScholarChainBuild.serviceDistributionSettings(core, rag, storage),
      name := "services"
    )

lazy val applicationModules =
  Seq(
    core,
    hadoop,
    entityResolution,
    sparkAnalytics,
    storage,
    rag,
    services,
    buildVerification,
    independentTests
  )

lazy val root =
  project
    .in(file("."))
    .aggregate(applicationModules.map(_.project): _*)
    .settings(
      publish / skip := true,
      emrArtifactManifest := {
        checkJava17.value
        val submit = (hadoop / hadoopSubmitJar).value
        val bundle = (hadoop / hadoopDependencyBundle).value
        val er = (entityResolution / erJobJar).value
        val spark = (sparkAnalytics / sparkJobJar).value
        val repoRoot = (ThisBuild / baseDirectory).value
        EmrArtifactManifest.write(
          repoRoot,
          (ThisBuild / version).value,
          EmrArtifactManifest.Targets(
            emrRelease = "emr-7.8.0",
            scala = Versions.scala3,
            sparkRuntime = Versions.spark,
            sparkScalaBinary = Versions.sparkScalaBinary,
            hadoopClient = Versions.hadoopClient
          ),
          Seq(
            EmrArtifactManifest.Artifact(
              "hadoop-dependency-bundle",
              bundle,
              None,
              byteReproducible = true
            ),
            EmrArtifactManifest.Artifact(
              "hadoop-submit-jar",
              submit,
              Some("edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"),
              byteReproducible = true
            ),
            EmrArtifactManifest.Artifact(
              "entity-resolution-job-jar",
              er,
              Some(ErJobJar.MainClass),
              byteReproducible = true
            ),
            EmrArtifactManifest.Artifact(
              "spark-job-jar",
              spark,
              Some("edu.uic.cs441.scholarchain.spark.Phase6Main"),
              byteReproducible = true
            )
          ),
          repoRoot / "target" / "emr-artifacts" / "emr-artifact-manifest.json"
        )
      },
      markTestRun := Def.taskDyn {
        val repoRoot = (ThisBuild / baseDirectory).value.getAbsolutePath
        (buildVerification / Compile / runMain)
          .toTask(s" scholarchain.build.TestRunMarker $repoRoot")
      }.value,
      checkProbeInjectFailure := {
        if (sys.props.get("scholarchain.checkProbe.fail").contains("true"))
          sys.error("scholarchain check probe: injected format-stage failure")
      },
      contractTest := Def.taskDyn {
        if (sys.props.get("scholarchain.checkProbe.fail").contains("true"))
          Def.task(())
        else
          (buildVerification / Test / test)
      }.value,
      checkTask := Def
        .sequential(
          Def.sequential(
            checkJava17,
            checkProbeInjectFailure,
            core / Compile / scalafmtCheck,
            core / Test / scalafmtCheck,
            hadoop / Compile / scalafmtCheck,
            hadoop / Test / scalafmtCheck,
            entityResolution / Compile / scalafmtCheck,
            entityResolution / Test / scalafmtCheck,
            sparkAnalytics / Compile / scalafmtCheck,
            sparkAnalytics / Test / scalafmtCheck,
            storage / Compile / scalafmtCheck,
            storage / Test / scalafmtCheck,
            rag / Compile / scalafmtCheck,
            rag / Test / scalafmtCheck,
            services / Compile / scalafmtCheck,
            services / Test / scalafmtCheck,
            buildVerification / Compile / scalafmtCheck,
            buildVerification / Test / scalafmtCheck,
            independentTests / Compile / scalafmtCheck,
            independentTests / Test / scalafmtCheck,
            Compile / scalafmtSbtCheck
          ),
          Def.sequential(
            core / Test / Keys.compile,
            hadoop / Test / Keys.compile,
            entityResolution / Test / Keys.compile,
            sparkAnalytics / Test / Keys.compile,
            storage / Test / Keys.compile,
            rag / Test / Keys.compile,
            services / Test / Keys.compile,
            buildVerification / Test / Keys.compile,
            independentTests / Test / Keys.compile
          ),
          Def.sequential(
            core / Test / test,
            hadoop / Test / test,
            entityResolution / Test / test,
            sparkAnalytics / Test / test,
            storage / Test / test,
            rag / Test / test,
            services / Test / test,
            independentTests / Test / test
          ),
          contractTest,
          entityResolution / erJobJarCheck,
          markTestRun
        )
        .value,
      dockerLocalImage := {
        checkJava17.value
        val _ = (services / serviceDistribution).value
        import sys.process._
        ServiceDistribution.artifacts.foreach { case (artifact, mainClass) =>
          val exit = Process(
            Seq(
              "docker",
              "build",
              "-f",
              "Dockerfile",
              "--build-arg",
              s"MAIN_CLASS=$mainClass",
              "-t",
              s"scholarchain-$artifact:local",
              "."
            ),
            baseDirectory.value
          ).!
          if (exit != 0) sys.error(s"docker build for $artifact failed with exit code $exit")
        }
      }
    )

addCommandAlias("fmt", ";all scalafmtAll; scalafmtSbt")
addCommandAlias("check", "checkTask")
// Every packaging alias starts with checkJava17 so a non-17 sbt JVM fails before any artifact is
// produced; the packaging tasks also depend on the same guard when invoked directly.
addCommandAlias(
  "packageJobs",
  ";checkJava17; hadoop/package; hadoop/hadoopDependencyBundle; sparkAnalytics/sparkJobJar"
)
addCommandAlias(
  "packageRelease",
  ";checkJava17; hadoop/hadoopSubmitJar; hadoop/hadoopDependencyBundle; " +
    "sparkAnalytics/sparkJobJar; entityResolution/erJobJar; services/serviceDistribution; " +
    "emrArtifactManifest"
)
// Offline EMR artifacts only (no service distribution): the four job JARs plus their manifest at
// target/emr-artifacts/emr-artifact-manifest.json. Builds locally; uploads nothing.
addCommandAlias(
  "packageEmr",
  ";checkJava17; hadoop/hadoopSubmitJar; hadoop/hadoopDependencyBundle; " +
    "sparkAnalytics/sparkJobJar; entityResolution/erJobJar; emrArtifactManifest"
)
addCommandAlias("sparkJobJar", "sparkAnalytics/sparkJobJar")
addCommandAlias("erJobJar", "entityResolution/erJobJar")
addCommandAlias("dockerLocal", "dockerLocalImage")
addCommandAlias("packageServices", "services/serviceDistribution")
addCommandAlias("hadoopLocalClasspath", "hadoop/hadoopLocalClasspath")
addCommandAlias("hadoopRunMain", "hadoop/hadoopRunMain")
addCommandAlias("hadoopDependencyBundle", "hadoop/hadoopDependencyBundle")
addCommandAlias("hadoopSubmitJar", "hadoop/hadoopSubmitJar")

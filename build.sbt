import ScholarChainBuild._
import sbt.Keys._
import sbtassembly.AssemblyPlugin

ThisBuild / organization := "edu.uic.cs441.scholarchain"
ThisBuild / version := "0.1.0-SNAPSHOT"

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
        (ThisBuild / baseDirectory).value / "project/Java17Guard.scala",
      Compile / unmanagedSources +=
        (ThisBuild / baseDirectory).value / "project/AwsIntegrationPolicy.scala",
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
    .dependsOn(core, hadoop, entityResolution, sparkAnalytics, storage, rag)
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
    .settings(ScholarChainBuild.moduleSettings(), name := "entityResolution")

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
    .dependsOn(core, rag, storage, sparkAnalytics)
    .settings(ScholarChainBuild.moduleSettings(), name := "services")

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
      markTestRun := Def.taskDyn {
        val repoRoot = (ThisBuild / baseDirectory).value.getAbsolutePath
        (buildVerification / Compile / runMain)
          .toTask(s" scholarchain.build.TestRunMarker $repoRoot")
      }.value,
      checkProbeInjectFailure := {
        if (sys.props.get("scholarchain.checkProbe.fail").contains("true"))
          sys.error("scholarchain check probe: injected format-stage failure")
      },
      checkJava17 :=
        scholarchain.build.Java17Guard.requireJava17(sys.props("java.specification.version")),
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
          markTestRun
        )
        .value,
      dockerLocalImage := {
        val _ = (services / Compile / Keys.`package`).value
        import sys.process._
        val exit =
          s"docker build -f ${baseDirectory.value / "Dockerfile"} -t scholarchain-local:latest .".!
        if (exit != 0) sys.error(s"docker build failed with exit code $exit")
      }
    )

addCommandAlias("fmt", ";all scalafmtAll; scalafmtSbt")
addCommandAlias("check", "checkTask")
addCommandAlias(
  "packageJobs",
  ";hadoop/package; hadoop/hadoopDependencyBundle; sparkAnalytics/sparkJobJar"
)
addCommandAlias("sparkJobJar", "sparkAnalytics/sparkJobJar")
addCommandAlias("dockerLocal", "dockerLocalImage")
addCommandAlias("hadoopLocalClasspath", "hadoop/hadoopLocalClasspath")
addCommandAlias("hadoopRunMain", "hadoop/hadoopRunMain")
addCommandAlias("hadoopDependencyBundle", "hadoop/hadoopDependencyBundle")
addCommandAlias("hadoopSubmitJar", "hadoop/hadoopSubmitJar")

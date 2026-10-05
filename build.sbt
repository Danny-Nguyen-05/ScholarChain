import ScholarChainBuild._
import sbt.Keys._

ThisBuild / organization := "edu.uic.cs441.scholarchain"
ThisBuild / version := "0.1.0-SNAPSHOT"

lazy val buildVerification =
  project
    .in(file("build-verification"))
    .settings(
      name := "build-verification",
      ScholarChainBuild.commonSettings,
      publish / skip := true,
      Compile / scalaSource :=
        (ThisBuild / baseDirectory).value / "project/verification/src/main/scala",
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
    .dependsOn(core)
    .settings(
      ScholarChainBuild.moduleSettings(Seq(Dependencies.hadoopClientLib)),
      name := "hadoop"
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
    .settings(
      ScholarChainBuild.moduleSettings(Seq(Dependencies.sparkSql)),
      name := "sparkAnalytics"
    )

lazy val storage =
  project
    .in(file("modules/storage"))
    .dependsOn(core)
    .settings(ScholarChainBuild.moduleSettings(), name := "storage")

lazy val rag =
  project
    .in(file("modules/rag"))
    .dependsOn(core, storage)
    .settings(ScholarChainBuild.moduleSettings(), name := "rag")

lazy val services =
  project
    .in(file("modules/services"))
    .dependsOn(core, rag, storage, sparkAnalytics)
    .settings(ScholarChainBuild.moduleSettings(), name := "services")

lazy val applicationModules =
  Seq(core, hadoop, entityResolution, sparkAnalytics, storage, rag, services, buildVerification)

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
      contractTest := Def.taskDyn {
        if (sys.props.get("scholarchain.checkProbe.fail").contains("true"))
          Def.task(())
        else
          (buildVerification / Test / test)
      }.value,
      checkTask := Def
        .sequential(
          Def.sequential(
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
            buildVerification / Test / Keys.compile
          ),
          Def.sequential(
            core / Test / test,
            hadoop / Test / test,
            entityResolution / Test / test,
            sparkAnalytics / Test / test,
            storage / Test / test,
            rag / Test / test,
            services / Test / test
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
addCommandAlias("packageJobs", ";hadoop/package; sparkAnalytics/package")
addCommandAlias("dockerLocal", "dockerLocalImage")

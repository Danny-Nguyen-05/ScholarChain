import sbt._
import sbt.Keys._

object ScholarChainBuild {
  val markTestRun = taskKey[Unit]("Write .claude/.last-test-run after required checks succeed")
  val contractTest = taskKey[Unit]("AWS-free contract tests")
  val checkTask = taskKey[Unit]("Format check, compile, test, contract tests, markTestRun")
  val checkProbeInjectFailure =
    taskKey[Unit]("No-op unless -Dscholarchain.checkProbe.fail=true (check failure-path probe)")
  val dockerLocalImage = taskKey[Unit]("Build the local services container image")

  lazy val commonSettings: Seq[Setting[_]] = Seq(
    scalaVersion := Versions.scala3,
    scalacOptions ++= Seq("-deprecation", "-feature"),
    libraryDependencies ++= Seq(
      Dependencies.upickleLib,
      Dependencies.slf4jApi,
      Dependencies.logbackClassic,
      Dependencies.scalaTestLib
    ),
    Test / parallelExecution := false
  )

  def moduleSettings(extra: Seq[ModuleID] = Nil): Seq[Setting[_]] =
    commonSettings ++ Seq(libraryDependencies ++= extra)
}

import sbt._

object Dependencies {
  import Versions._

  val upickleLib = "com.lihaoyi" %% "upickle" % upickle

  val scalaTestLib = "org.scalatest" %% "scalatest" % scalaTest % Test

  val slf4jApi = "org.slf4j" % "slf4j-api" % slf4j
  val logbackClassic = "ch.qos.logback" % "logback-classic" % logback % Runtime

  val hadoopClientLib = "org.apache.hadoop" % "hadoop-client" % hadoopClient % Provided

  // Excludes (Spark 2.13 artifacts vs Scala 3.3.4): org.scala-lang stdlib/reflection jars;
  // org.scala-lang.modules:scala-xml_2.13 triggers sbt cross-version suffix conflicts with _3.
  val sparkSql =
    ("org.apache.spark" % s"spark-sql_$sparkScalaBinary" % spark % Provided)
      .exclude("org.scala-lang", "scala-library")
      .exclude("org.scala-lang", "scala-reflect")
      .exclude("org.scala-lang.modules", s"scala-xml_$sparkScalaBinary")
}

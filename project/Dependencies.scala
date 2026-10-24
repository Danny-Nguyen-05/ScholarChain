import sbt._

object Dependencies {
  import Versions._

  val upickleLib = "com.lihaoyi" %% "upickle" % upickle

  val scalaTestLib = "org.scalatest" %% "scalatest" % scalaTest % Test

  val slf4jApi = "org.slf4j" % "slf4j-api" % slf4j
  val logbackClassic = "ch.qos.logback" % "logback-classic" % logback % Runtime

  val hadoopClientLib = "org.apache.hadoop" % "hadoop-client" % hadoopClient % Provided

  val awsS3 = "software.amazon.awssdk" % "s3" % awsSdk
  val awsDynamoDb = "software.amazon.awssdk" % "dynamodb" % awsSdk
  val awsNeptuneData = "software.amazon.awssdk" % "neptunedata" % awsSdk
  val awsS3Vectors = "software.amazon.awssdk" % "s3vectors" % awsSdk
  val awsSqs = "software.amazon.awssdk" % "sqs" % awsSdk
  val awsBedrockRuntime = "software.amazon.awssdk" % "bedrockruntime" % awsSdk
  val parquetHadoop = "org.apache.parquet" % "parquet-hadoop" % parquet
  // Local Parquet ingestion runs without Spark or a cluster-provided Hadoop runtime.
  val storageHadoopClient =
    ("org.apache.hadoop" % "hadoop-client" % hadoopClient)
      .exclude("org.slf4j", "slf4j-reload4j")

  // SparkSession's compiled signatures refer to Scala 2.13 TypeTag even when using
  // the Java-friendly DataFrame API. Keep reflection on the compile/test classpath.
  val sparkScalaReflectLib =
    "org.scala-lang" % "scala-reflect" % sparkScalaReflect % Provided

  // Excludes Spark's transitive Scala stdlib/reflection versions in favor of the
  // Scala 3 stdlib and the explicit matching scala-reflect dependency above;
  // org.scala-lang.modules:scala-xml_2.13 triggers sbt cross-version suffix conflicts with _3.
  val sparkSql =
    ("org.apache.spark" % s"spark-sql_$sparkScalaBinary" % spark % Provided)
      .exclude("org.scala-lang", "scala-library")
      .exclude("org.scala-lang", "scala-reflect")
      .exclude("org.scala-lang.modules", s"scala-xml_$sparkScalaBinary")
}

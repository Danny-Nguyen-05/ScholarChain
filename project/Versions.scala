object Versions {
  val scala3 = "3.3.4"

  val sbtVersion = "1.10.7"

  val sbtScalafmt = "2.5.2"
  val sbtAssembly = "2.3.0"
  val scalafmtCore = "3.8.3"

  val upickle = "4.0.2"
  val scalaTest = "3.2.19"

  val slf4j = "2.0.16"
  val logback = "1.5.15"

  val hadoopClient = "3.3.6"

  // AWS's latest published release verified 2026-10-22:
  // https://github.com/aws/aws-sdk-java-v2/releases/tag/2.56.0 (2026-10-14).
  val awsSdk = "2.56.0"

  // Match Phase 6 / Spark 3.5.4's Parquet format implementation.
  // https://github.com/apache/spark/blob/v3.5.4/pom.xml
  val parquet = "1.13.1"

  // Spark 3.5.4 is published on Maven Central only as Scala 2.13 artifacts (e.g.
  // org.apache.spark:spark-sql_2.13:3.5.4). There is no Spark 3.5 artifact cross-built for
  // Scala 3.3.x. sparkAnalytics must compile against Spark's Java and Dataset/DataFrame entry
  // points (org.apache.spark.sql.*) and must not call Spark's Scala 2.13 RDD/Dataset APIs.
  // Dependencies.scala keeps spark-sql_2.13 on the Provided classpath with full Java/transitive
  // deps; Spark's Scala stdlib/reflection versions and scala-xml_2.13 are excluded where they
  // break Scala 3 resolution. scala-reflect is added explicitly at the Scala 3 stdlib version.
  val spark = "3.5.4"
  val sparkScalaBinary = "2.13"
  // Matches the scala-library dependency of scala3-library_3 3.3.4.
  val sparkScalaReflect = "2.13.14"
}

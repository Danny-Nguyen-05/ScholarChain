package edu.uic.cs441.scholarchain.independent

import org.apache.spark.sql.SparkSession
import org.scalatest.funsuite.AnyFunSuite

class IndependentSparkSessionSpec extends AnyFunSuite {
  test("independent test JVM can start and stop local Spark on Java 17") {
    val spark = SparkSession
      .builder()
      .appName("ScholarChain independent Spark startup")
      .master("local[1]")
      .config("spark.ui.enabled", "false")
      .getOrCreate()

    try {
      assert(spark.range(3L).filter("id > 0").count() == 2L)
    } finally {
      spark.stop()
    }
  }
}

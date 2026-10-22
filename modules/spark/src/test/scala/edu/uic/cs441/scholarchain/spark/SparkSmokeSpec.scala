package edu.uic.cs441.scholarchain.spark

import java.nio.file.{Files, Path}
import java.util.Arrays

import org.apache.spark.api.java.JavaSparkContext
import org.apache.spark.sql.{Row, RowFactory, SparkSession}
import org.apache.spark.sql.functions.{col, count, row_number}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.types.{DataTypes, StructType}
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

import scala.jdk.CollectionConverters.*

class SparkSmokeSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var spark: SparkSession = _
  private var temporaryRoot: Path = _

  override protected def beforeAll(): Unit = {
    super.beforeAll()
    temporaryRoot = Files.createTempDirectory("scholarchain-spark-smoke-")
    spark = SparkSession
      .builder()
      .appName("ScholarChain Spark smoke spec")
      .master("local[2]")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "2")
      .getOrCreate()
    JavaSparkContext
      .fromSparkContext(spark.sparkContext)
      .setCheckpointDir(temporaryRoot.resolve("checkpoints").toString)
  }

  override protected def afterAll(): Unit = {
    try {
      if (spark != null) spark.stop()
    } finally {
      if (temporaryRoot != null) {
        val paths = Files.walk(temporaryRoot)
        try paths.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists(_))
        finally paths.close()
      }
      super.afterAll()
    }
  }

  test("five explicit rows survive join, aggregation, window, Parquet and checkpoint") {
    val schema = new StructType()
      .add("researcher", DataTypes.StringType, false)
      .add("collaborator", DataTypes.StringType, false)
      .add("year", DataTypes.IntegerType, false)
    val rows = Arrays.asList[Row](
      RowFactory.create("alice", "bob", Int.box(2020)),
      RowFactory.create("alice", "carol", Int.box(2021)),
      RowFactory.create("bob", "carol", Int.box(2022)),
      RowFactory.create("alice", "bob", Int.box(2023)),
      RowFactory.create("dana", "alice", Int.box(2024))
    )
    val events = spark.createDataFrame(rows, schema)
    assert(events.count() == 5L)

    val frequencies = events.groupBy("researcher").agg(count("*").as("event_count"))
    val order = Window.partitionBy("researcher").orderBy(col("year"), col("collaborator"))
    val ranked = events
      .join(frequencies, "researcher")
      .withColumn("event_rank", row_number().over(order))

    def tuples(data: org.apache.spark.sql.Dataset[Row]): Vector[(String, String, Int, Long, Int)] =
      data
        .collect()
        .toVector
        .map { row =>
          (
            row.getAs[String]("researcher"),
            row.getAs[String]("collaborator"),
            row.getAs[Int]("year"),
            row.getAs[Long]("event_count"),
            row.getAs[Int]("event_rank")
          )
        }
        .sortBy(row => (row._1, row._3))

    val expected = Vector(
      ("alice", "bob", 2020, 3L, 1),
      ("alice", "carol", 2021, 3L, 2),
      ("alice", "bob", 2023, 3L, 3),
      ("bob", "carol", 2022, 1L, 1),
      ("dana", "alice", 2024, 1L, 1)
    )
    assert(tuples(ranked) == expected)

    val parquetPath = temporaryRoot.resolve("ranked.parquet").toString
    ranked.write.parquet(parquetPath)
    assert(tuples(spark.read.schema(ranked.schema).parquet(parquetPath)) == expected)

    val checkpointed = ranked.checkpoint()
    assert(tuples(checkpointed) == expected)
  }
}

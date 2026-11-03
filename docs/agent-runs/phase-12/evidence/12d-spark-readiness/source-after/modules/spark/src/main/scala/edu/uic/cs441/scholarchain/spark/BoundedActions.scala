package edu.uic.cs441.scholarchain.spark

import org.apache.spark.sql.{DataFrame, Row}
import org.apache.spark.api.java.JavaRDD
import scala.jdk.CollectionConverters.*

/** The only production entry point for driver-side DataFrame actions. Graph tables remain
  * distributed.
  */
object BoundedActions {

  /** A small operational Java API result, with an extra sentinel row to reject truncation. */
  def cappedJava[A](values: JavaRDD[A], limit: Int): Vector[A] = {
    require(
      limit > 0 && limit < Int.MaxValue,
      "positive non-overflowing driver result limit required"
    )
    val rows = values.take(limit + 1).asScala.toVector
    require(rows.size <= limit, s"driver result exceeds limit $limit")
    rows
  }

  def count(table: DataFrame): Long = table.count()

  def exists(table: DataFrame): Boolean = table.limit(1).count() != 0L

  def scalarLong(table: DataFrame, field: String): Long = {
    val rows = table.limit(2).collect()
    require(rows.length == 1, s"expected one aggregate row for $field")
    rows(0).getAs[Long](field)
  }

  def capped(table: DataFrame, limit: Int): Vector[Row] = {
    require(limit > 0, "positive driver result limit required")
    table.limit(limit + 1).collect().toVector match {
      case rows if rows.size <= limit => rows
      case _ => throw new IllegalArgumentException(s"driver result exceeds limit $limit")
    }
  }
}

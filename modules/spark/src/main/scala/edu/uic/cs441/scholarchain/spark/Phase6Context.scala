package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import org.apache.spark.sql.{DataFrame, Column}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.*

/** One ordered wire schema shared by every job. Option values use the JSON null wire form. */
object Phase6Context {
  val lineageSchema: StructType = new StructType()
    .add("hadoopRunId", StringType)
    .add("hadoopSnapshot", StringType)
    .add("entityResolutionRunId", StringType)
    .add("entityResolutionPolicyVersion", StringType)
    .add("entityResolutionPolicyHash", StringType)
    .add("sourceWorkIds", ArrayType(StringType))
    .add("sourceMentionIds", ArrayType(StringType))
  val schema: StructType = new StructType()
    .add("schemaVersion", StringType)
    .add("runId", StringType)
    .add("windowId", StringType)
    .add("lineage", lineageSchema)
  def add(df: DataFrame, lineage: SparkLineage, runId: String, window: Column): DataFrame =
    df.withColumn(
      "context",
      struct(
        lit(SchemaVersions.sparkAnalytics).as("schemaVersion"),
        lit(runId).as("runId"),
        window.as("windowId"),
        from_json(lit(CoreJson.compact(lineage)), lineageSchema).as("lineage")
      )
    )
}

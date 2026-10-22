package edu.uic.cs441.scholarchain.spark
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions.*

/** Small report over persisted Parquet; every graph-size operation remains a distributed aggregate.
  */
object Phase6Report {
  def write(spark: SparkSession, root: Path): ujson.Value = {
    def read(name: String) = spark.read.parquet(root.resolve(name).toString)
    def rows(df: DataFrame) =
      ujson.Arr.from(BoundedActions.capped(df, 10000).map(r => ujson.read(r.json)))
    def distributions(df: DataFrame, fields: Seq[String]): DataFrame = {
      val expressions = Seq(count("*").as("rows")) ++ fields.flatMap { f =>
        Seq(
          min(f).as(f + "Min"),
          avg(f).as(f + "Mean"),
          expr(s"percentile_approx($f,array(0.5,0.9),10000)").as(f + "P50P90"),
          max(f).as(f + "Max")
        )
      }
      df.groupBy("window").agg(expressions.head, expressions.tail*).orderBy("window")
    }
    val report = ujson.Obj(
      "metrics" -> rows(
        distributions(
          read("metrics/type=researcher_collaboration"),
          Seq(
            "publicationCount",
            "distinctCoauthorCount",
            "totalCoauthorOccurrences",
            "averageCoauthorsPerPaper",
            "maximumCoauthorsOnOnePaper",
            "weightedDegree",
            "coreness"
          )
        )
      ),
      "components" -> rows(
        read("metrics/type=component_summaries")
          .groupBy("window")
          .agg(
            count("*").as("components"),
            max("size").as("largestSize"),
            max("largestComponentFraction").as("largestFraction"),
            max("singletonCount").as("singletons")
          )
          .orderBy("window")
      ),
      "communities" -> rows(
        distributions(
          read("metrics/type=community_summaries"),
          Seq("size", "iterations", "finalChangedCount")
        )
      ),
      "communityConvergence" -> rows(
        read("metrics/type=community_summaries")
          .groupBy("window")
          .agg(
            min(col("converged").cast("int")).as("allConverged"),
            max("iterations").as("iterations"),
            max("finalChangedCount").as("finalChangedCount")
          )
          .orderBy("window")
      ),
      "bridges" -> rows(
        distributions(
          read("metrics/type=bridges"),
          Seq(
            "crossCommunityDegree",
            "crossCommunityWeight",
            "communitiesConnected",
            "participationCoefficient"
          )
        )
      ),
      "paths" -> rows(
        read("path-evidence")
          .groupBy("window", "status")
          .agg(count("*").as("pairs"), max("hopCount").as("maxFoundHopCount"))
          .orderBy("window", "status")
      ),
      "distanceEstimates" -> rows(
        read("metrics/type=path_length_estimate").orderBy("window", "componentId")
      ),
      "limitations" -> ujson.Arr(
        "Synchronous LPA oscillates on every isolated two-person component; non-convergence is disclosed per window.",
        "Distances estimate only the largest component using seeded sampled sources; P90 is empirical, not exact diameter.",
        "Bridge measures depend on the final LPA partition and degree; no sampled betweenness.",
        "This is a bounded local run; EMR runtime validation remains deferred."
      )
    )
    Files.writeString(root.resolve("analytics-report.json"), report.render() + "\n", UTF_8)
    report
  }
}

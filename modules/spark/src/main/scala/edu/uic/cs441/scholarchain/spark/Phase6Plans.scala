package edu.uic.cs441.scholarchain.spark
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.execution.ExplainMode

/** Capture before eager checkpoints replace algorithm plans with ExistingRDD scans. */
object Phase6Plans {
  private var destination: Option[Path] = None
  def start(path: Path): Unit = { Files.createDirectories(path); destination = Some(path) }
  def stop(): Unit = { destination = None }
  def record(name: String, table: DataFrame): DataFrame = {
    destination.foreach { root =>
      Files.writeString(
        root.resolve(name + "-before-checkpoint.txt"),
        table.queryExecution.explainString(ExplainMode.fromString("formatted")) + "\n",
        UTF_8
      )
    }; table
  }
}

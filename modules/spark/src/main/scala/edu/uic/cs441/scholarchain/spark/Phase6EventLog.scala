package edu.uic.cs441.scholarchain.spark

import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.jdk.CollectionConverters.*
import scala.collection.mutable

/** Streaming parser of Spark's JSON event files. Retains only per-stage numerical aggregates. */
object Phase6EventLog {
  def summarize(directory: Path): ujson.Value = {
    val stages = mutable.Map.empty[(Int, Int), ujson.Obj]
    def number(v: ujson.Value, key: String): Double =
      v.objOpt.flatMap(_.get(key)).flatMap(_.numOpt).getOrElse(0.0)
    def stage(id: Int, attempt: Int): ujson.Obj = stages.getOrElseUpdate(
      (id, attempt),
      ujson.Obj(
        "stageId" -> id,
        "attemptId" -> attempt,
        "tasks" -> 0,
        "failedTasks" -> 0,
        "durationMs" -> 0,
        "executorRunTimeMs" -> 0,
        "shuffleReadBytes" -> 0,
        "shuffleReadRecords" -> 0,
        "shuffleWriteBytes" -> 0,
        "shuffleWriteRecords" -> 0,
        "partitionCount" -> 0
      )
    )
    if (Files.exists(directory)) {
      val paths = Files.walk(directory)
      try
        paths
          .iterator()
          .asScala
          .filter(p =>
            Files.isRegularFile(p) && !p.getFileName.toString
              .startsWith(".") && !p.getFileName.toString.startsWith("appstatus")
          )
          .foreach { path =>
            val reader = Files.newBufferedReader(path, UTF_8)
            try {
              var line = reader.readLine()
              while (line != null) {
                if (line.nonEmpty) {
                  val event = ujson.read(line)
                  event.obj.get("Event").flatMap(_.strOpt).getOrElse("") match {
                    case "SparkListenerTaskEnd" =>
                      val s = stage(
                        number(event, "Stage ID").toInt,
                        number(event, "Stage Attempt ID").toInt
                      )
                      val info = event.obj.getOrElse("Task Info", ujson.Obj());
                      val metrics = event.obj.getOrElse("Task Metrics", ujson.Obj())
                      def add(key: String, value: Double): Unit = s(key) = s(key).num + value
                      add("tasks", 1);
                      add("durationMs", number(info, "Finish Time") - number(info, "Launch Time"))
                      add("executorRunTimeMs", number(metrics, "Executor Run Time"))
                      val reason = event.obj.getOrElse("Task End Reason", ujson.Obj())
                      if (
                        reason.objOpt
                          .flatMap(_.get("Reason"))
                          .flatMap(_.strOpt)
                          .getOrElse("") != "Success"
                      ) add("failedTasks", 1)
                      val read = metrics.obj.getOrElse("Shuffle Read Metrics", ujson.Obj())
                      add(
                        "shuffleReadBytes",
                        number(read, "Remote Bytes Read") + number(read, "Local Bytes Read")
                      ); add("shuffleReadRecords", number(read, "Total Records Read"))
                      val write = metrics.obj.getOrElse("Shuffle Write Metrics", ujson.Obj())
                      add("shuffleWriteBytes", number(write, "Shuffle Bytes Written"));
                      add("shuffleWriteRecords", number(write, "Shuffle Records Written"))
                    case "SparkListenerStageCompleted" =>
                      val info = event("Stage Info");
                      val s = stage(
                        number(info, "Stage ID").toInt,
                        number(info, "Stage Attempt ID").toInt
                      )
                      s("partitionCount") = number(info, "Number of Tasks")
                    case _ => ()
                  }
                }
                line = reader.readLine()
              }
            } finally reader.close()
          }
      finally paths.close()
    }
    ujson.Obj(
      "source" -> "Spark JSON event log",
      "stages" -> ujson.Arr.from(stages.toVector.sortBy(_._1).map(_._2))
    )
  }
  def main(args: Array[String]): Unit = {
    require(args.length == 2, "usage: Phase6EventLog <event-directory> <summary.json>");
    Files.writeString(Path.of(args(1)), summarize(Path.of(args(0))).render() + "\n", UTF_8)
  }
}

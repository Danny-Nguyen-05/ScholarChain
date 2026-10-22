# Independent G1 initial targeted failure

Owner: `test-engineer` `/root/test_6c`. This is the owner's reported direct tool output, not a retained raw sbt log. The coordinator did not rerun or independently observe this first attempt.

Command: JDK 17 `sbt -batch 'independentTests/testOnly *IndependentPhase6CGraphSpec'`.

Result: exit 1. The tests compiled, then the suite aborted before assertions: `IndependentPhase6CGraphSpec *** ABORTED ***`; `java.lang.OutOfMemoryError: Java heap space` at `org.apache.spark.sql.catalyst.util.StringConcat.toString(StringUtils.scala:62)`, called by `org.apache.spark.sql.execution.adaptive.AdaptiveSparkPlanExec.onUpdatePlan(AdaptiveSparkPlanExec.scala:780)`. `Total number of tests run: 0`; suites completed 0, aborted 1; `sbt.TestsFailedException`; total time 22 seconds. Forked test heap remained `-Xmx2g`.

The owner routed this to the Spark engineer as a production query-lineage/materialization issue. No passing test or repaired result is claimed here.

## Second targeted attempt (owner-reported, direct output)

After the Spark owner added eager checkpoints, the G1 and cross-DBLP tests passed. The third work cannot-link test then spent more than 75 seconds repeating `TaskMemoryManager` allocation warnings for 33,554,416-byte requests. The test owner canceled sbt; exit 1. This output was not redirected to a retained raw log. The owner suspects cached DataFrames from repeated builds in one SparkSession and is isolating fixture sessions. The Spark owner is auditing cache lifecycle. A complete targeted pass is still pending.

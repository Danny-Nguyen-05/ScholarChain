# Spark checkpoint failure observed during the bounded run

The first real-data CLI attempt failed with exit 1 after 83.61 seconds. Spark SQL execution 282 records `NoSuchElementException: key not found: windowId#102242` in `Union.rewriteConstraints`, then `LogicalRDD.rewriteStatsAndConstraints`, then `Dataset.checkpoint`, called by `Phase6DEJobs.selectedPaths` at the found-path union checkpoint. The complete retained stack is in `spark-first-checkpoint-error.json`. The failed run has typed integrity evidence and no completion marker.

The diagnosis is that Spark 3.5.4 propagates a stale attribute constraint while rewriting this iterative union/checkpoint plan. This is an inference from the observed stack, not a claim that an upstream issue has been confirmed. Primary sources consulted read-only on 2026-10-22:

- [Spark 3.5.4 SQLConf](https://raw.githubusercontent.com/apache/spark/v3.5.4/sql/catalyst/src/main/scala/org/apache/spark/sql/internal/SQLConf.scala), lines 818–826: `spark.sql.constraintPropagation.enabled` controls optimizer constraint inference/propagation.
- [Spark 3.5.4 QueryPlanConstraints](https://raw.githubusercontent.com/apache/spark/v3.5.4/sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/plans/logical/QueryPlanConstraints.scala), lines 29–39: disabling it uses an empty inferred-constraint set.

The Spark owner is applying this optimizer compatibility setting for the analytics pipeline, while retaining explicit application invariants and adding a multiwindow, six-hop regression. Final completion is demonstrated separately by fresh targeted tests, the real-data run/replay and the stable-tree full gate.

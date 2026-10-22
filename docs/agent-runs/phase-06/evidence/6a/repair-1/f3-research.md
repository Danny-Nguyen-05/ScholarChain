# F3 research evidence — 6A repair round 1

Owner: `infra-engineer`, native task `/root/infra_6a_r1`; read-only research, no AWS account call and no file authoring by that role. The coordinator assembled the finding into `../emr-compatibility.md`.

- Upstream source inspected: [Apache Spark v3.5.4 `pom.xml` Scala-2.13 profile](https://raw.githubusercontent.com/apache/spark/v3.5.4/pom.xml#L3625-L3630). It sets `scala.version` to `2.13.8` for that profile. This describes an upstream build profile, not an inventoried EMR custom runtime.
- Local command observed by coordinator: `unzip -p modules/spark/target/spark-job_3-0.1.0-SNAPSHOT.jar library.properties | head -15`, exit 0. It printed `maven.version.number=2.13.14` and `version.number=2.13.14` from the 6A JAR.
- The [Scala binary compatibility policy](https://docs.scala-lang.org/overviews/core/binary-compatibility-of-scala-releases.html) states both backward and forward binary compatibility among Scala 2.13 patch releases through 2.13.18, with exclusions for experimental/internal APIs and generated code. The reviewer-stated patch mismatch is a runtime validation risk, not proof of failure.
- The [Spark 3.5 configuration reference](https://spark.apache.org/docs/3.5.7/configuration.html#runtime-environment) marks `spark.driver.userClassPathFirst` and `spark.executor.userClassPathFirst` experimental; both default to false. No classpath override, shading, custom distribution, or EMR run was attempted.

Next gate: after a human selects and approves a bounded 6H runtime, inventory driver/executor Scala JAR versions and class origins, align the job package to the selected distribution or validate the exact patch pair, and run a bounded startup/DataFrame/Parquet task.

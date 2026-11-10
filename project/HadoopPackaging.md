# Hadoop module packaging and launch contract

ScholarChain ships a **thin** Hadoop application JAR from the `hadoop` sbt project, a **verified non-Hadoop dependency bundle**, and a **RunJar submit JAR** that nests that bundle at `lib/<bundle file name>`. Apache Hadoop itself is **not** embedded: the cluster (or local Compile classpath) supplies `hadoop-client` and related `org.apache.hadoop.*` libraries. Do not shade `org.apache.hadoop.**` or `hadoop-client` into the thin JAR, the dependency bundle, or the submit JAR.

## Dependency scope (sbt)

- `Dependencies.hadoopClientLib` is `Provided` (see `project/Dependencies.scala`).
- **Compile** and **Test** classpaths include `hadoop-client`.
- **Runtime** / **fullClasspath** for packaging and default `java -jar` flows **exclude** `Provided` dependencies.
- `hadoop / Compile / package` produces a thin JAR containing only this module’s compiled classes (plus manifest), not shaded Hadoop libraries and not the dependency bundle.

## Local runs (Hadoop classes required)

Use the **Compile** full classpath (includes `Provided`), not Runtime. Do **not** point local runs at the thin JAR alone.

| Command | Purpose |
|--------|---------|
| `sbt -batch hadoopLocalClasspath` | Prints the hadoop `Compile / fullClasspath` path list (alias for `hadoop/hadoopLocalClasspath`). |
| `sbt -batch hadoopRunMain <mainClass> <args>*` | Alias for `hadoop/hadoopRunMain`, which runs `Compile / fgRunMain` (foreground) on `Compile / fullClasspath` with `Compile / run / fork := true` and `Compile / run / baseDirectory` set to the repository root (so default config and sample dataset paths resolve). sbt 1.10’s default `Compile / runMain` uses background `bgRunMain` and `Runtime / fullClasspathAsJars`, which omits Provided `hadoop-client`; do not use `hadoop/runMain` for local Hadoop mains. `Runtime / fullClasspath` is unchanged so packaging stays thin. |

Recommended JDK for local verification (when installed on macOS Homebrew):

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
```

Example:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
  sbt -batch hadoopRunMain edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain --once
```

Local job outputs and scratch data should live under `target/phase4-runs/` (ignored via repository `target/` rule).

## Thin JAR, dependency bundle, and submit JAR

Build the cluster driver artifact (this also builds the thin JAR and the dependency bundle):

```bash
sbt -batch hadoopSubmitJar
```

The thin JAR and bundle can still be built on their own:

```bash
sbt -batch hadoop/package hadoopDependencyBundle
```

Or via the aggregate alias (also packages Spark; this alias does not build the submit JAR):

```bash
sbt -batch packageJobs
```

### Java 17 guard and release alias

Every packaging task (module `package`/`packageBin`, `assembly`, `hadoopDependencyBundle`, `hadoopSubmitJar`, `sparkJobJar`, `serviceDistribution`, `dockerLocalImage`) and the `packageJobs` and `packageRelease` aliases run `checkJava17` first, so a non-Java-17 sbt JVM fails with the `Java17Guard` message before any artifact is written. `packageRelease` builds the hadoop submit JAR, the hadoop dependency bundle, the Spark job JAR, the entity-resolution job JAR, the service distribution and the EMR artifact manifest (no Docker images):

```bash
sbt -batch packageRelease
```

### EMR job artifacts: entity-resolution JAR and manifest (offline, Phase 15)

`sbt -batch packageEmr` (also part of `packageRelease`) builds, locally and without any upload or AWS call, the four artifacts the EMR pipeline uses and writes `target/emr-artifacts/emr-artifact-manifest.json` (git-ignored `target/`): role, repository-relative path, bytes, sha256 and main class for each, plus the target versions from the ledger (`emr-7.8.0`, Scala 3.3.4, Spark 3.5.4 / Scala 2.13, hadoop-client 3.3.6). The manifest contains no clock, host or absolute path, so identical artifact bytes give an identical manifest.

| Manifest role | Path | Launched as |
|---|---|---|
| `hadoop-submit-jar` | `modules/hadoop/target/scala-3.3.4/hadoop-submit_3-<version>.jar` | `hadoop jar` with `HadoopPrepMain` |
| `hadoop-dependency-bundle` | `modules/hadoop/target/scala-3.3.4/hadoop-dependency-bundle_3-<version>.jar` | `-libjars` |
| `entity-resolution-job-jar` | `modules/entity-resolution/target/er-job_3-<version>.jar` | `java -cp er-job.jar ...entityresolution.Phase5Main resolve ...` |
| `spark-job-jar` | `modules/spark/target/spark-job_3-<version>.jar` | `spark-submit` with `Phase6Main` |

Task `entityResolution/erJobJar` writes the ER job JAR. The EMR `entity-resolution` step puts this one JAR alone on the classpath of a single JVM on the primary node (`scripts/emr/sc-step.sh`), so it carries the entity-resolution and core classes and resources plus every runtime library (scala3-library_3, scala-library 2.13, upickle, slf4j-api) and the manifest `Main-Class`. It carries no `org.apache.hadoop`, `org.apache.spark`, logback class or SLF4J provider service. Metadata that cannot be merged (`META-INF/*` other than `services/`, `module-info.class`, signatures, multi-release entries) is dropped; service files are concatenated; a conflicting duplicate entry fails the build.

`entityResolution/erJobJarCheck` runs inside `sbt check`: it builds the JAR a second time and fails unless the sha256 matches, and it runs `java -cp er-job.jar ...Phase5Main --help` on a bare classpath, which is exactly the EMR launch shape.

**Reproducibility.** The ER JAR, the Hadoop dependency bundle, the Hadoop submit JAR and the Spark job JAR were rebuilt from scratch (JARs deleted, assembly caches rebuilt) and produced the same sha256 on the same JDK 17. The submit JAR was previously not byte-reproducible because `JarOutputStream` stamped its manifest entry with the current time; entries now use the fixed local time 2010-01-01 00:00:00. Reproducibility holds for the same sources, ledger versions and JDK build; a different JDK or zlib build may deflate differently, so compare hashes only between builds from one toolchain.

### Thin Hadoop module JAR

Path pattern (`scalaBinaryVersion` and `version` follow `ThisBuild / scalaVersion` and `ThisBuild / version`):

```text
modules/hadoop/target/scala-3.3.4/hadoop_3-<version>.jar
```

Example with current defaults: `modules/hadoop/target/scala-3.3.4/hadoop_3-0.1.0-SNAPSHOT.jar`.

**Includes:** compiled `hadoop` module classes and manifest (main class when set).

**Excludes:** `org.apache.hadoop.*`, all Hadoop transitive Maven artifacts, Provided `hadoop-client`, an embedded `lib/` entry, the `core` module, Scala 3, uPickle/ujson, and other runtime libraries (those belong in the bundle). `hadoop/Compile/package` stays thin.

### Verified non-Hadoop dependency bundle

Task: `hadoopDependencyBundle` (alias: `sbt -batch hadoopDependencyBundle`).

Path pattern:

```text
modules/hadoop/target/scala-3.3.4/hadoop-dependency-bundle_3-<version>.jar
```

Example: `modules/hadoop/target/scala-3.3.4/hadoop-dependency-bundle_3-0.1.0-SNAPSHOT.jar`.

**Includes:** compiled **`core`** module classes; **Scala 3** runtime (`scala3-library` and required Scala runtime pieces); **uPickle**, **ujson**, and their non-Hadoop transitive dependencies; shared runtime logging deps from module settings (for example `slf4j-api`, `logback-classic`).

**Excludes:** compiled **`hadoop`** module classes (they remain in the thin JAR only); every `org.apache.hadoop` Maven module and Hadoop transitive artifact; Provided **`hadoop-client`** (must not be shaded into this JAR or the thin JAR).

The task runs `assemblyPackageDependency` and fails the build if the output JAR contains `org/apache/hadoop/**` or `edu/uic/cs441/scholarchain/hadoop/**`, or if expected `core`/Scala/uPickle content is missing.

### RunJar submit JAR

Task: `hadoopSubmitJar` (alias: `sbt -batch hadoopSubmitJar`).

Depends on `hadoop/Compile/packageBin` and `hadoopDependencyBundle`.

Path pattern (directory is the hadoop module `crossTarget`, same directory as the thin JAR; the file name uses `scalaBinaryVersion` and `version`):

```text
modules/hadoop/target/scala-3.3.4/hadoop-submit_3-<version>.jar
```

Example: `modules/hadoop/target/scala-3.3.4/hadoop-submit_3-0.1.0-SNAPSHOT.jar`.

The file is the thin JAR plus exactly one extra zip entry, `lib/hadoop-dependency-bundle_3-<version>.jar`, whose bytes are the verified dependency bundle. Class files are not unpacked or merged. Hadoop module classes stay at the JAR root; they are not placed under `lib/`.

The task fails if the bundle file is missing, if `lib/` is absent in the submit JAR, or if any entry under `lib/` contains `org/apache/hadoop/` or `edu/uic/cs441/scholarchain/hadoop/`.

## Why `java -jar` on either artifact is not valid

`java -jar` on the thin JAR or the submit JAR is invalid. `java -jar` uses the JAR manifest **Class-Path** and the **Runtime** classpath. It does not apply RunJar’s `lib/*.jar` driver bootstrap. `Provided` dependencies are intentionally absent from Runtime, and the thin JAR does not embed `core`, Scala 3, uPickle, or Hadoop. Launching either artifact with `java -jar` fails with `NoClassDefFoundError` even though `sbt hadoop/compile` succeeds.

Use `hadoopRunMain`, a custom `java -cp` built from `hadoopLocalClasspath` output, or the cluster `hadoop jar` shape below.

## EMR / cluster launch

The cluster distribution supplies Hadoop (`hadoop-client` stays `Provided` and is not shaded). Cluster launch has two halves.

### Driver bootstrap

Submit `hadoop-submit_*.jar`. Apache Hadoop 3.3.6 `org.apache.hadoop.util.RunJar` puts the submitted JAR and its `lib/*.jar` entries on the driver classpath before `main`. It does not interpret `-libjars`.

`HADOOP_CLASSPATH` may also point at the same dependency bundle. That is not a substitute for task distribution.

### Task distribution

The application parses `-libjars <bundle>` via Hadoop `GenericOptionsParser` into `tmpjars`. Passing `-libjars` only on the shell without the application reading it does nothing, because RunJar forwards those args verbatim.

```bash
hadoop jar /path/on/cluster/hadoop-submit_3-<version>.jar \
  edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain \
  -libjars /path/on/cluster/hadoop-dependency-bundle_3-<version>.jar \
  --once \
  [other application args...]
```

Repository-relative example (local paths; infra scripts should use cluster-visible URIs):

```bash
hadoop jar modules/hadoop/target/scala-3.3.4/hadoop-submit_3-0.1.0-SNAPSHOT.jar \
  edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain \
  -libjars modules/hadoop/target/scala-3.3.4/hadoop-dependency-bundle_3-0.1.0-SNAPSHOT.jar \
  --once
```

Do **not** add a shaded `hadoop-client` JAR. Do **not** submit the thin JAR alone: RunJar would not see `lib/*.jar` on the driver classpath.

Infra-owned scripts (for example `scripts/phase4-emr-smoke.sh`) should submit `hadoop-submit_*.jar` and still pass `-libjars` with the bundle so the application can register `tmpjars`.

package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.time.Instant
import org.scalatest.funsuite.AnyFunSuite
import scala.collection.mutable
import software.amazon.awssdk.auth.credentials.{
  AwsBasicCredentials,
  AwsCredentials,
  AwsCredentialsProvider,
  AwsSessionCredentials
}

class StorageLoadMainOptionsSpec extends AnyFunSuite {
  private val key = "AKIASYNTHETICKEYID00"
  private val secret = "synthetic-secret-value-never-printed"

  test("loader budget defaults are unchanged and overrides derive the missing half") {
    assert(StorageLoadMain.loaderBudget(None, None) == Right(None))
    assert(StorageLoadMain.loaderBudget(Some("1800"), None) == Right(Some((1800000L, 1800))))
    // A short timeout never lowers the poll count below the unchanged default of 300.
    assert(StorageLoadMain.loaderBudget(Some("30"), None) == Right(Some((30000L, 300))))
    assert(StorageLoadMain.loaderBudget(None, Some("900")) == Right(Some((900000L, 900))))
    // A small poll count never lowers the timeout below the unchanged default of 300 s.
    assert(StorageLoadMain.loaderBudget(None, Some("10")) == Right(Some((300000L, 10))))
    assert(StorageLoadMain.loaderBudget(Some("600"), Some("50")) == Right(Some((600000L, 50))))
    assert(
      StorageLoadMain.loaderBudget(Some("14400"), Some("20000")) == Right(Some((14400000L, 20000)))
    )
    assert(StorageLoadMain.loaderBudget(Some("1"), Some("1")) == Right(Some((1000L, 1))))
  }

  test("loader budget rejects out-of-range and non-numeric values") {
    Vector("0", "-1", "14401", "abc", "1.5", "").foreach { v =>
      assert(StorageLoadMain.loaderBudget(Some(v), None).isLeft, v)
    }
    Vector("0", "-5", "20001", "x", "2.0", "").foreach { v =>
      assert(StorageLoadMain.loaderBudget(None, Some(v)).isLeft, v)
    }
    assert(StorageLoadMain.loaderBudget(Some("60"), Some("0")).isLeft)
    assert(StorageLoadMain.loaderBudget(Some("0"), Some("60")).isLeft)
  }

  private def run(args: Vector[String]): (Int, Vector[String]) = {
    val lines = mutable.Buffer.empty[String]
    val code = StorageLoadMain.run(args, lines += _)
    (code, lines.toVector)
  }

  test("loader timeout options are refused for invalid values and for the default dry-run") {
    val root = Files.createTempDirectory("storage-load-options-")
    try {
      val config = root.resolve("config.json")
      Files.writeString(
        config,
        """{"schemaVersion":"scholarchain.storage-load.v1","environment":"local"}""",
        UTF_8
      )
      val base = Vector("--manifest", root.toString, "--config", config.toString)
      val invalid = run(base ++ Vector("--execute-fake", "--load-timeout-seconds", "0"))
      assert(invalid._1 == 2 && invalid._2.exists(_.contains("--load-timeout-seconds")))
      val polls = run(base ++ Vector("--execute-fake", "--load-max-polls", "20001"))
      assert(polls._1 == 2 && polls._2.exists(_.contains("--load-max-polls")))
      val dry = run(base ++ Vector("--load-timeout-seconds", "900"))
      assert(dry._1 == 2 && dry._2.exists(_.contains("loader timeout options require")))
      val dryPolls = run(base ++ Vector("--dry-run", "--load-max-polls", "900"))
      assert(dryPolls._1 == 2)
      val twice = run(
        base ++ Vector("--execute-fake", "--load-max-polls", "1", "--load-max-polls", "2")
      )
      assert(twice._1 == 2)
    } finally {
      Files.deleteIfExists(root.resolve("config.json"))
      Files.deleteIfExists(root)
    }
  }

  private def provider(credentials: => AwsCredentials): AwsCredentialsProvider =
    new AwsCredentialsProvider { def resolveCredentials(): AwsCredentials = credentials }

  private def check(args: Vector[String], credentials: => AwsCredentials) = {
    val requested = mutable.Buffer.empty[String]
    val lines = mutable.Buffer.empty[String]
    val code = StorageLoadMain.run(
      args,
      lines += _,
      profile => { requested += profile; provider(credentials) }
    )
    (code, lines.toVector, requested.toVector)
  }

  test("--check-credentials resolves only the named profile and never prints key material") {
    val session = AwsSessionCredentials
      .builder()
      .accessKeyId(key)
      .secretAccessKey(secret)
      .sessionToken("synthetic-token-never-printed")
      .expirationTime(Instant.parse("2026-11-09T01:02:03Z"))
      .build()
    val (code, lines, requested) =
      check(Vector("--check-credentials", "--profile", "operator"), session)
    assert(code == 0 && requested == Vector("operator"))
    assert(
      lines == Vector(
        "CREDENTIALS-RESOLVED: profile=operator sessionToken=true expiresAt=2026-11-09T01:02:03Z"
      )
    )
    val plain = check(
      Vector("--profile", "static", "--check-credentials"),
      AwsBasicCredentials.create(key, secret)
    )
    assert(
      plain._1 == 0 && plain._2 == Vector(
        "CREDENTIALS-RESOLVED: profile=static sessionToken=false expiresAt=unknown"
      )
    )
    Vector(lines, plain._2).flatten.foreach { l =>
      assert(!l.contains(key) && !l.contains(secret) && !l.contains("token-never"))
    }
  }

  test("--check-credentials reports failure by class only and rejects every other option") {
    val failed = check(
      Vector("--check-credentials", "--profile", "broken"),
      throw new IllegalStateException(s"profile file mentions $secret")
    )
    assert(failed._1 == 1)
    assert(failed._2 == Vector("CREDENTIALS-FAILED: profile=broken reason=IllegalStateException"))
    assert(!failed._2.exists(_.contains(secret)))
    val sdk = check(
      Vector("--check-credentials", "--profile", "role"),
      throw software.amazon.awssdk.core.exception.SdkClientException.create("sts module missing")
    )
    assert(sdk._1 == 1 && sdk._2.head.endsWith("reason=SdkClientException"))
    Vector(
      Vector("--check-credentials"),
      Vector("--check-credentials", "--profile", ""),
      Vector("--check-credentials", "--profile", "p", "--execute-aws"),
      Vector("--check-credentials", "--profile", "p", "--manifest", "/tmp"),
      Vector("--check-credentials", "--profile", "p", "--load-max-polls", "5")
    ).foreach { args =>
      val (code, lines, requested) = check(args, AwsBasicCredentials.create(key, secret))
      assert(code == 2 && requested.isEmpty, args.toString)
      assert(lines.forall(_.startsWith("REFUSED:")))
    }
    val duplicate = check(
      Vector("--check-credentials", "--check-credentials", "--profile", "p"),
      AwsBasicCredentials.create(key, secret)
    )
    assert(duplicate._1 == 2 && duplicate._3.isEmpty)
  }

  // Smallest export the real validator accepts: a completed run with empty node, edge and support
  // tables. With `rejectingCache` an extra, undeclared kcore manifest makes the cache loader (and
  // only the cache loader) reject, so a graph-only success proves that the cache step never ran.
  private def exportFixture(root: Path, rejectingCache: Boolean): Path = {
    val run = "run:00000000-0000-4000-8000-0000000000aa"
    val lineage =
      SparkLineage(run, "fixture-snapshot", run, "fixture-er", "a" * 64, Vector.empty, Vector.empty)
    val context = SparkRecordContext(SchemaVersions.sparkAnalytics, run, None, lineage)
    val emptyHash = StableIds.sha256Hex("sha256-fixed-256-shard-sorted-row-json-merkle-v1\n")
    val support = "edges/type=coauthored_with_support"
    def manifest(name: String, keys: Vector[String]) = LoadManifest(
      context,
      "s3",
      name,
      Vector(name),
      "parquet",
      0,
      keys,
      Vector.empty,
      emptyHash,
      Vector("all-years"),
      "storage-engineer",
      Vector.empty
    )
    val manifests = Vector(manifest(support, Vector("edgeId", "workId"))) ++
      (if (rejectingCache) Vector(manifest("metrics/type=kcore", Vector("researcherId")))
       else Vector.empty)
    Files.createDirectories(root.resolve("load-manifests"))
    Files.createDirectories(root.resolve(support))
    Vector("nodes", "graph-edges", "coauthor-edges").foreach(d =>
      Files.createDirectories(root.resolve("neptune-opencypher-csv/data/" + d))
    )
    Files.writeString(
      root.resolve("load-manifests/s3.json"),
      upickle.default.write(manifests),
      UTF_8
    )
    val csv = Vector(":ID", ":LABEL")
    val sidecar = ujson.Obj(
      "schemaVersion" -> "scholarchain.neptune-opencypher-export.v1",
      "runId" -> run,
      "format" -> "opencypher",
      "userProvidedEdgeIds" -> true,
      "loaderPrefix" -> "neptune-opencypher-csv/data",
      "contentHashMethod" -> "sha256-fixed-256-shard-sorted-row-json-merkle-v1",
      "supportTable" -> ujson.Obj("path" -> support, "keyColumns" -> ujson.Arr("edgeId", "workId")),
      "sourceTables" -> ujson.Arr(
        ujson.Obj(
          "path" -> support,
          "rowCount" -> 0L,
          "contentHash" -> emptyHash,
          "keyColumns" -> ujson.Arr("edgeId", "workId")
        )
      ),
      "datasets" -> ujson.Arr.from(
        Vector("nodes", "graph-edges", "coauthor-edges").map(d =>
          ujson.Obj(
            "path" -> ("neptune-opencypher-csv/data/" + d),
            "columns" -> ujson.Arr.from(csv),
            "rowCount" -> 0L,
            "contentHash" -> emptyHash
          )
        )
      )
    )
    Files.writeString(
      root.resolve("load-manifests/neptune-opencypher-csv.json"),
      sidecar.render(),
      UTF_8
    )
    val runJson = ujson.Obj("runId" -> run).render() + "\n"
    val meta = ujson
      .Obj(
        "runId" -> run,
        "hadoopRunId" -> run,
        "entityResolutionRunId" -> run,
        "entityResolutionPolicyVersion" -> lineage.entityResolutionPolicyVersion,
        "entityResolutionPolicyHash" -> lineage.entityResolutionPolicyHash,
        "tables" -> ujson.Arr(
          ujson.Obj(
            "dataset" -> support,
            "path" -> support,
            "rowCount" -> 0L,
            "contentHash" -> emptyHash
          )
        )
      )
      .render() + "\n"
    Files.writeString(root.resolve("run-manifest.json"), runJson, UTF_8)
    Files.writeString(root.resolve("run-metadata.json"), meta, UTF_8)
    Files.writeString(root.resolve("counters.json"), "[]", UTF_8)
    Files.writeString(
      root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
      StableIds.sha256Hex(runJson + "\n" + meta) + "\n",
      UTF_8
    )
    val config = root.resolve("storage-load-config.json")
    Files.writeString(
      config,
      ujson
        .Obj(
          "schemaVersion" -> "scholarchain.storage-load.v1",
          "environment" -> "local",
          "region" -> "us-east-1",
          "bucket" -> "fixture-bucket",
          "graphPrefix" -> "graph",
          "tables" -> ujson.read(
            upickle.default.write(
              DynamoTables(
                "runs",
                "links",
                "sessions",
                "evidence",
                "artifacts",
                "metrics",
                "idempotency"
              )
            )
          ),
          "neptune" -> ujson
            .Obj("iamRoleArn" -> "fixture-role", "endpoint" -> "https://fixture.invalid:8182")
        )
        .render(),
      UTF_8
    )
    config
  }

  private def withFixture(rejectingCache: Boolean)(f: (Vector[String], Path) => Unit): Unit = {
    val root = Files.createTempDirectory("storage-load-graph-only-")
    try {
      val config = exportFixture(root, rejectingCache)
      f(Vector("--manifest", root.toString, "--config", config.toString), root)
    } finally ExportFiles.deleteTree(root)
  }

  test("normal fake execution still runs the cache step and prints the unchanged COMPLETE line") {
    withFixture(rejectingCache = false) { (base, _) =>
      val (code, lines) = run(base :+ "--execute-fake")
      assert(code == 0, lines.mkString("\n"))
      assert(lines.exists(_.contains("mode=fake nodes=0 edges=0 support=0")))
      assert(lines.last == "COMPLETE: cacheWritten=0 cacheUnchanged=0 graphState=LOAD_COMPLETED")
    }
  }

  test("normal paths still reject through the cache loader, which graph-only must not invoke") {
    withFixture(rejectingCache = true) { (base, _) =>
      val fake = run(base :+ "--execute-fake")
      assert(fake._1 == 1 && fake._2.last.startsWith("FAILED: cache loading rejected; reason="))
      val dry = run(base)
      assert(dry._1 == 1 && dry._2.last.startsWith("FAILED: cache source validation rejected"))
    }
  }

  test("--graph-only with --execute-fake skips the cache loader and submits the graph load") {
    withFixture(rejectingCache = true) { (base, _) =>
      val (code, lines) = run(base ++ Vector("--execute-fake", "--graph-only"))
      assert(code == 0, lines.mkString("\n"))
      assert(lines.exists(_.contains("mode=fake nodes=0 edges=0 support=0")))
      assert(lines.last == "COMPLETE: cacheSkipped=true graphState=LOAD_COMPLETED")
      assert(!lines.exists(l => l.contains("cacheWritten=") || l.startsWith("FAILED:")))
      val withBudget =
        run(base ++ Vector("--graph-only", "--execute-fake", "--load-timeout-seconds", "900"))
      assert(withBudget._1 == 0)
      assert(withBudget._2.contains("loader: timeoutMillis=900000 maxPolls=900 (override)"))
      assert(withBudget._2.last == "COMPLETE: cacheSkipped=true graphState=LOAD_COMPLETED")
    }
  }

  test("--graph-only dry run prints the graph-only plan, no cache plan and performs no calls") {
    withFixture(rejectingCache = true) { (base, _) =>
      Vector(base :+ "--graph-only", base ++ Vector("--dry-run", "--graph-only")).foreach { args =>
        val (code, lines) = run(args)
        assert(code == 0, lines.mkString("\n"))
        assert(
          lines.head.startsWith("runId=run:00000000-0000-4000-8000-0000000000aa mode=dry-run ")
        )
        assert(
          lines.contains(
            "PLAN: graph-only; cache step skipped (caches must already be loaded for this run)"
          )
        )
        assert(lines.exists(l => l.startsWith("PLAN:") && l.contains("submit and poll Neptune")))
        assert(!lines.exists(l => l.contains("cacheWrites=") || l.contains("cacheUnchanged=")))
        assert(!lines.exists(_.startsWith("COMPLETE:")))
      }
    }
  }

  test(
    "--graph-only is refused with --check-credentials, when duplicated and where AWS rules apply"
  ) {
    withFixture(rejectingCache = false) { (base, _) =>
      val refused = Vector(
        Vector("--check-credentials", "--profile", "p", "--graph-only"),
        Vector("--graph-only", "--check-credentials", "--profile", "p"),
        base ++ Vector("--execute-fake", "--graph-only", "--graph-only"),
        base ++ Vector("--execute-fake", "--execute-aws", "--graph-only"),
        base ++ Vector("--graph-only", "--profile", "p"),
        base ++ Vector("--graph-only", "--load-timeout-seconds", "900"),
        base ++ Vector("--execute-aws", "--graph-only", "--environment", "local")
      )
      refused.foreach { args =>
        val requested = mutable.Buffer.empty[String]
        val lines = mutable.Buffer.empty[String]
        val code = StorageLoadMain.run(
          args,
          lines += _,
          p => { requested += p; provider(AwsBasicCredentials.create(key, secret)) }
        )
        assert(code == 2, args.toString)
        assert(lines.nonEmpty && lines.forall(_.startsWith("REFUSED:")), args.toString)
        assert(requested.isEmpty && !lines.exists(_.contains("mode=aws")), args.toString)
      }
    }
  }
}

package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite
import scala.collection.mutable
import StorageResult.*
import SubsetFixture.*

class RuntimeArtifactMainSpec extends AnyFunSuite {
  private final class Env {
    val root: Path = Files.createTempDirectory("runtime-artifact-main-")
    val source: Path = Files.createDirectories(root.resolve("export/load-manifests")).getParent
    Files.writeString(
      source.resolve("load-manifests/s3.json"),
      upickle.default.write(manifests()),
      UTF_8
    )
    val include: Path = root.resolve("include.txt")
    Files.writeString(include, s"# smoke\n$e\n", UTF_8)
    val out: Path = root.resolve("out")
    val objects = new InMemoryObjectStore
    val requested = mutable.Buffer.empty[(String, String, String)]
    val deps: RuntimeArtifactMain.Deps = RuntimeArtifactMain.Deps(
      reader = _ => new Reader(SubsetFixture.source),
      objects = (profile, region, bucket) => {
        requested += ((profile, region, bucket))
        (objects, new AutoCloseable { def close(): Unit = () })
      }
    )
    def base: Vector[String] = Vector(
      "--source",
      source.toString,
      "--include-ids",
      include.toString,
      "--out-dir",
      out.toString
    )
    def run(extra: Vector[String] = Vector.empty, args: Option[Vector[String]] = None) = {
      val lines = mutable.Buffer.empty[String]
      val code = RuntimeArtifactMain.run(args.getOrElse(base ++ extra), lines += _, deps)
      (code, lines.toVector)
    }
    def cleanup(): Unit = {
      Files.walk(root).sorted(java.util.Comparator.reverseOrder()).forEach(p => Files.delete(p))
    }
  }
  private def withEnv(body: Env => Unit): Unit = {
    val env = new Env
    try body(env)
    finally env.cleanup()
  }
  private def sha256(path: Path): String =
    StorageKeys.sha256(Files.readAllBytes(path).toVector)
  private def line(lines: Vector[String], prefix: String): String =
    lines.find(_.startsWith(prefix)).getOrElse(fail(s"missing $prefix in ${lines.mkString("\n")}"))

  test("local mode writes the artifact, report and pointer and prints the three service values") {
    withEnv { env =>
      val (code, lines) = env.run()
      assert(code == 0, lines.mkString("\n"))
      val artifact = env.out.resolve("runtime-artifact.json")
      val digest = sha256(artifact)
      assert(
        line(lines, "SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256=") ==
          "SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256=" + digest
      )
      assert(line(lines, "SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID=").endsWith("=" + runId))
      val key = line(lines, "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY=").stripPrefix(
        "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY="
      )
      assert(
        key == s"runtime-artifacts/versions/${runId.replace(':', '-')}/runtime-subset-$digest.json"
      )
      assert(line(lines, "SELECTION:").contains("rows=61"))
      assert(line(lines, "UPLOAD:").contains("skipped"))
      assert(env.requested.isEmpty && env.objects.writeOrder.isEmpty)
      val pointer = ujson.read(Files.readString(env.out.resolve("runtime-artifact-pointer.json")))
      assert(pointer("key").str == key && pointer("sha256").str == digest)
      assert(pointer("sourceRunId").str == runId)
      val report = ujson.read(Files.readString(env.out.resolve("selection-report.json")))
      assert(report("status").str == "written" && report("pointer")("sha256").str == digest)
      assert(report("includeList")("fileSha256").str == sha256(env.include))
      // The bytes load through the same reader the services use.
      val objects = new InMemoryObjectStore
      objects.put(key, Files.readAllBytes(artifact).toVector, "application/json", Map.empty)
      val reader =
        new ObjectStoreRuntimeArtifactStore(objects, RuntimeArtifactPointer(key, digest, runId))
      assert(
        StorageResult.value(reader.researcherContext(e, "all-years", 5)).get.coauthorIds == Vector(
          f
        )
      )
    }
  }

  test("rerunning is idempotent and a differing existing output is refused") {
    withEnv { env =>
      val first = env.run()
      val before = Files.readAllBytes(env.out.resolve("runtime-artifact.json")).toVector
      val second = env.run()
      assert(first == second && first._1 == 0)
      assert(Files.readAllBytes(env.out.resolve("runtime-artifact.json")).toVector == before)
      Files.writeString(env.out.resolve("selection-report.json"), "tampered", UTF_8)
      val (code, lines) = env.run()
      assert(code == 2 && lines.exists(_.startsWith("REFUSED:")))
    }
  }

  test("a custom key and prefix are honored and unsafe ones refused") {
    withEnv { env =>
      val (code, lines) = env.run(Vector("--key", "custom/versions/run-1/snapshot.json"))
      assert(code == 0)
      assert(
        line(lines, "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY=").endsWith(
          "=custom/versions/run-1/snapshot.json"
        )
      )
    }
    withEnv { env =>
      val prefixed = env.run(Vector("--key-prefix", "team/artifacts"))
      assert(
        prefixed._1 == 0 && line(prefixed._2, "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY=").contains(
          "=team/artifacts/versions/"
        )
      )
    }
    Vector(
      Vector("--key", "no-version-segment/snapshot.json"),
      Vector("--key", "/abs/versions/x.json"),
      Vector("--key", "a/../versions/x.json"),
      Vector("--key", "a/versions/x y.json"),
      Vector("--key-prefix", "../escape"),
      Vector("--key-prefix", "/abs"),
      Vector("--key", "a/versions/x.json", "--key-prefix", "p")
    ).foreach { extra =>
      withEnv { env =>
        val (code, lines) = env.run(extra)
        assert(code == 2 && lines.exists(_.startsWith("REFUSED:")), extra.toString)
        assert(!Files.exists(env.out.resolve("runtime-artifact.json")))
      }
    }
  }

  test("--run-prefix derives runtime-artifacts/<run_prefix>/... and prints no bucket when local") {
    withEnv { env =>
      val (code, lines) = env.run(Vector("--run-prefix", "run-20261115"))
      assert(code == 0, lines.mkString("\n"))
      val digest = sha256(env.out.resolve("runtime-artifact.json"))
      assert(
        line(lines, "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY=") ==
          s"SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY=runtime-artifacts/run-20261115/versions/${runId.replace(':', '-')}/runtime-subset-$digest.json"
      )
      assert(!lines.exists(_.startsWith("SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET=")))
    }
  }

  test("the run prefix pattern accepts its boundaries and refuses everything else") {
    // 'run-' + 2..28 characters: first [a-z0-9], then 1..27 of [a-z0-9-]; total 6..32 characters.
    assert(RuntimeArtifactMain.validRunPrefix("run-ab"))
    assert(RuntimeArtifactMain.validRunPrefix("run-" + "a" * 28))
    assert(!RuntimeArtifactMain.validRunPrefix("run-a"))
    assert(!RuntimeArtifactMain.validRunPrefix("run-" + "a" * 29))
    Vector(
      "run-",
      "run--a",
      "run-A1",
      "run-a_b",
      "Run-ab",
      "run-a/b",
      "run-a/../b",
      "/run-ab",
      "run-ab/",
      "run-ab\n",
      "runtime-artifacts",
      ""
    ).foreach { bad =>
      assert(!RuntimeArtifactMain.validRunPrefix(bad), bad)
    }
    assert(RuntimeArtifactMain.validRunPrefix("run-a-b-9"))
    intercept[IllegalArgumentException](RuntimeArtifactMain.artifactKey("bad", "r", "s"))
    assert(
      RuntimeArtifactMain.artifactKey("run-ab", "a:b", "f" * 64) ==
        "runtime-artifacts/run-ab/versions/a-b/runtime-subset-" + "f" * 64 + ".json"
    )
  }

  test("--run-prefix is validated, exclusive with the other key flags, and required to upload") {
    Vector(
      Vector("--run-prefix", "run-a"),
      Vector("--run-prefix", "Run-ab"),
      Vector("--run-prefix", "run-ab/../x"),
      Vector("--run-prefix", "run-ab", "--key-prefix", "p"),
      Vector("--run-prefix", "run-ab", "--key", "a/versions/x.json"),
      Vector("--run-prefix", "run-ab", "--run-prefix", "run-cd"),
      Vector("--execute-aws", "--profile", "p", "--bucket", "b", "--region", "r")
    ).foreach { extra =>
      withEnv { env =>
        val (code, lines) = env.run(extra)
        assert(code == 2 && lines.exists(_.startsWith("REFUSED:")), extra.toString)
        assert(!Files.exists(env.out.resolve("runtime-artifact.json")))
        assert(env.requested.isEmpty && env.objects.writeOrder.isEmpty)
      }
    }
  }

  test(
    "AWS upload needs an explicit flag plus profile, bucket and region, and uploads identical bytes"
  ) {
    withEnv { env =>
      val aws = Vector(
        "--run-prefix",
        "run-20261115",
        "--execute-aws",
        "--profile",
        "operator",
        "--bucket",
        "artifacts-bucket",
        "--region",
        "us-east-2"
      )
      val (code, lines) = env.run(aws)
      assert(code == 0, lines.mkString("\n"))
      assert(env.requested == mutable.Buffer(("operator", "us-east-2", "artifacts-bucket")))
      val key = line(lines, "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY=").stripPrefix(
        "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY="
      )
      val stored = StorageResult.value(env.objects.get(key)).get
      assert(stored.bytes == Files.readAllBytes(env.out.resolve("runtime-artifact.json")).toVector)
      assert(
        key == s"runtime-artifacts/run-20261115/versions/${runId.replace(':', '-')}/runtime-subset-${sha256(env.out.resolve("runtime-artifact.json"))}.json"
      )
      assert(
        line(
          lines,
          "SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET="
        ) == "SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET=artifacts-bucket"
      )
      assert(line(lines, "UPLOAD:").startsWith("UPLOAD: written s3://artifacts-bucket/" + key))
      val again = env.run(aws)
      assert(again._1 == 0 && line(again._2, "UPLOAD:").startsWith("UPLOAD: unchanged"))
    }
  }

  test("an upload conflict or rejection is a failure, not a success") {
    withEnv { env =>
      val rejecting = new ObjectStore {
        def put(
            key: String,
            bytes: Vector[Byte],
            contentType: String,
            metadata: Map[String, String]
        ) =
          Rejected("immutable-conflict")
        def get(key: String) = Missing
        def head(key: String) = Missing
      }
      val deps = env.deps.copy(objects =
        (_, _, _) => (rejecting, new AutoCloseable { def close(): Unit = () })
      )
      val lines = mutable.Buffer.empty[String]
      val code = RuntimeArtifactMain.run(
        env.base ++ Vector(
          "--run-prefix",
          "run-11",
          "--execute-aws",
          "--profile",
          "p",
          "--bucket",
          "b",
          "--region",
          "r"
        ),
        lines += _,
        deps
      )
      assert(code == 1 && lines.exists(_.contains("immutable-conflict")))
    }
  }

  test("argument validation refuses before reading the source or creating the output") {
    withEnv { env =>
      val cases = Vector(
        Vector.empty[String],
        env.base.take(4),
        env.base :+ "--bogus",
        env.base ++ Vector("--degree-window", "bad window"),
        env.base ++ Vector("--max-source-rows", "0"),
        env.base ++ Vector("--max-source-rows", "20000001"),
        env.base ++ Vector("--max-source-rows", "many"),
        env.base ++ Vector("--profile", "p"),
        env.base ++ Vector("--bucket", "b"),
        env.base ++ Vector("--execute-aws"),
        env.base ++ Vector("--execute-aws", "--profile", "p", "--bucket", "b"),
        env.base ++ Vector(
          "--execute-aws",
          "--execute-aws",
          "--profile",
          "p",
          "--bucket",
          "b",
          "--region",
          "r"
        ),
        env.base ++ Vector("--out-dir", "again")
      )
      cases.foreach { arguments =>
        val (code, lines) = env.run(args = Some(arguments))
        assert(code == 2 && lines.exists(_.startsWith("REFUSED:")), arguments.toString)
      }
      assert(env.requested.isEmpty && !Files.exists(env.out))
    }
  }

  test("an empty or malformed include list is refused with a stated reason") {
    withEnv { env =>
      Files.writeString(env.include, "# nothing\n", UTF_8)
      val empty = env.run()
      assert(empty._1 == 2 && empty._2.contains("REFUSED: include-list-empty."))
      Files.writeString(env.include, "not-an-id\n", UTF_8)
      val bad = env.run()
      assert(bad._1 == 2 && bad._2.contains("REFUSED: include-list-invalid-id."))
    }
  }

  test("a selection refusal exits 1, writes the report with the refusal and no artifact") {
    withEnv { env =>
      Files.writeString(env.include, unknownResearcher + "\n", UTF_8)
      val (code, lines) = env.run()
      assert(code == 1 && lines.exists(_.startsWith("REFUSED: include-id-not-found")))
      assert(!Files.exists(env.out.resolve("runtime-artifact.json")))
      val report = ujson.read(Files.readString(env.out.resolve("selection-report.json")))
      assert(
        report("status").str == "refused" && report("refusal")("code").str == "include-id-not-found"
      )
      val uploads =
        env.run(
          Vector(
            "--run-prefix",
            "run-11",
            "--execute-aws",
            "--profile",
            "p",
            "--bucket",
            "b",
            "--region",
            "r"
          )
        )
      assert(uploads._1 == 1 && env.requested.isEmpty && env.objects.writeOrder.isEmpty)
    }
  }

  test("--help prints usage and exits 0") {
    val lines = mutable.Buffer.empty[String]
    assert(RuntimeArtifactMain.run(Vector("--help"), lines += _) == 0)
    assert(lines.exists(_.contains("--include-ids")) && lines.exists(_.contains("--execute-aws")))
  }
}

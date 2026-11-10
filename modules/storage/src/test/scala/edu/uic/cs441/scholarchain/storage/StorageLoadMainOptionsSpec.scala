package edu.uic.cs441.scholarchain.storage

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.Files
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
}

package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.hadoop.*
import org.apache.hadoop.mapreduce.Job
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.security.MessageDigest
import scala.jdk.CollectionConverters.*

/** Real local Hadoop jobs with synthetic source-bound observations; no remote adapters. */
class AdversarialBlockingReplaySpec extends AnyFunSuite {
  import IndependentTestSupport.*

  private val blockKey = "exact:doi:10.1000/adversarial.large-block"
  private def profile(i: Int): Bibliography = Bibliography(
    SourceType.Dblp,
    s"conf/adversarial/block-$i",
    "synthetic-adversarial-v1",
    Some(StableIds.workIdFromDblpKey(s"conf/adversarial/block-$i").toOption.get),
    "",
    None,
    "",
    Vector.empty,
    Vector.empty,
    Vector.empty,
    Vector.empty,
    Vector(blockKey)
  )

  private def withRoot(run: Path => Unit): Unit = {
    val root = Files.createTempDirectory("scholarchain-adversarial-block-")
    try run(root)
    finally {
      val walk = Files.walk(root)
      try walk.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists)
      finally walk.close()
    }
  }

  private def execute(
      root: Path,
      label: String,
      members: Vector[Bibliography],
      candidate: Boolean,
      pairLimit: Int
  ): (Vector[(String, String)], Job) = {
    val input = root.resolve(s"$label.jsonl")
    val lines = members.map { p =>
      if (candidate)
        Lines.pack(Kinds.BlockMember, CoreJson.compact(DerivedRecords.member(p, blockKey)))
      else Lines.pack(Kinds.Bibliography, CoreJson.compact(p))
    }
    Files.writeString(input, lines.mkString("", "\n", "\n"), UTF_8)
    val output = root.resolve(s"out-$label")
    val conf = PrepJobs.configuration(
      prepConfig(root, team = 64, block = 8, pairs = pairLimit).copy(maxLocalSampleRecords = 512),
      runId,
      independentSnapshots
    )
    val job =
      if (candidate) PrepJobs.candidates(conf, input, output)
      else PrepJobs.block(conf, input, output)
    PrepJobs.run(s"adversarial-$label", job)
    val walk = Files.walk(output)
    val records =
      try
        walk
          .iterator()
          .asScala
          .filter(p => Files.isRegularFile(p) && p.getFileName.toString.startsWith("part-"))
          .toVector
          .flatMap { path =>
            Files.readAllLines(path, UTF_8).asScala.flatMap(Lines.unpack).toVector
          }
      finally walk.close()
    (records, job)
  }

  private def assertOnlyReject(
      records: Vector[(String, String)],
      reason: RejectReasonCode
  ): Unit = {
    assert(records.size == 1)
    assert(records.head._1 == Kinds.Reject)
    assert(CoreJson.parse[RejectRecord](records.head._2).toOption.get.reasonCode == reason)
  }

  test("blocking drains 257 distinct DOI observations and rejects the whole max-eight block") {
    withRoot { root =>
      val (records, job) = execute(
        root,
        "large-block",
        (1 to 257).map(profile).toVector,
        candidate = false,
        pairLimit = 28
      )
      assertOnlyReject(records, RejectReasonCode.OversizeBlock)
      assert(job.getCounters.findCounter(PrepCounters.Group, PrepCounters.Input).getValue == 257L)
      assert(
        job.getCounters.findCounter(PrepCounters.Group, PrepCounters.OversizeBlock).getValue == 1L
      )
    }
  }

  test("candidate join independently rejects 257 members even when blocking was bypassed") {
    withRoot { root =>
      val (records, job) = execute(
        root,
        "large-candidates",
        (1 to 257).map(profile).toVector,
        candidate = true,
        pairLimit = 28
      )
      assertOnlyReject(records, RejectReasonCode.OversizeBlock)
      assert(
        job.getCounters.findCounter(PrepCounters.Group, PrepCounters.EmittedPair).getValue == 0L
      )
    }
  }

  test("eight-member candidate join refuses 28 pairs against a 27-pair budget atomically") {
    withRoot { root =>
      val (records, _) = execute(
        root,
        "pair-budget",
        (1 to 8).map(profile).toVector,
        candidate = true,
        pairLimit = 27
      )
      assertOnlyReject(records, RejectReasonCode.OversizeCandidatePairs)
    }
  }

  test("permuted eight-member replay retains all 28 pairs and identical sorted-row SHA256") {
    withRoot { root =>
      val members = (1 to 8).map(profile).toVector
      val (first, _) = execute(root, "forward", members, candidate = true, pairLimit = 28)
      val (second, _) = execute(root, "reverse", members.reverse, candidate = true, pairLimit = 28)
      def pairs(records: Vector[(String, String)]) = records.map { case (kind, json) =>
        assert(kind == Kinds.MatchCandidate)
        CoreJson.parse[MatchCandidate](json).toOption.get
      }
      val result = pairs(first)
      assert(result.size == 28 && pairs(second).size == 28)
      val sourcePairs = result.map(c => Set(c.left.sourceRecordId, c.right.sourceRecordId))
      assert(sourcePairs.distinct.size == 28)
      assert(sourcePairs.forall(_.size == 2))
      assert(members.forall(m => sourcePairs.count(_.contains(m.sourceRecordId)) == 7))
      assert(result.forall(_.blockKey == blockKey))
      val rows1 = first.map(_._2).sorted
      val rows2 = second.map(_._2).sorted
      assert(rows1 == rows2)
      def hash(rows: Vector[String]): Vector[Byte] = MessageDigest
        .getInstance("SHA-256")
        .digest(rows.mkString("", "\n", "\n").getBytes(UTF_8))
        .toVector
      assert(hash(rows1) == hash(rows2))
      assert(hash(rows1) != hash(rows1.drop(1)))
    }
  }
}

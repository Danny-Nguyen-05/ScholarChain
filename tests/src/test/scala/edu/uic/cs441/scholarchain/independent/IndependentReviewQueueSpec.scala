package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

/** Independent queue tests use synthetic observations, never labels or matcher predictions. */
class IndependentReviewQueueSpec extends AnyFunSuite {
  import IndependentReviewFixtures.*

  test("review allocation is exactly forty development, two hundred held out and sixty reserves") {
    val result = artifacts()
    val tasks = result.queue.tasks
    assert(tasks.size == 300)
    assert(tasks.count(t => t.partition == "development" && t.role == "initial") == 40)
    assert(tasks.count(t => t.partition == "held-out" && t.role == "initial") == 200)
    assert(tasks.count(t => t.partition == "development" && t.role == "reserve") == 10)
    assert(tasks.count(t => t.partition == "held-out" && t.role == "reserve") == 50)
    assert(tasks.map(_.pair.pairId).distinct.size == 300)
    assert(ReviewQueue.validate(result.queue, result.split).isRight)
  }

  test(
    "selection and assignments replay deterministically and contain no predictions or suggested labels"
  ) {
    val population = isolated(640)
    val first = ReviewQueue
      .build(population.input, population.candidates, ReviewSampling.standard, binding(population))
      .toOption
      .get
    val second = ReviewQueue
      .build(population.input, population.candidates, ReviewSampling.standard, binding(population))
      .toOption
      .get
    assert(first == second)
    val json = ujson.read(write(first.queue))
    def keys(value: ujson.Value): Set[String] = value match {
      case obj: ujson.Obj   => obj.obj.keySet.toSet ++ obj.obj.values.flatMap(keys)
      case array: ujson.Arr => array.arr.flatMap(keys).toSet
      case _                => Set.empty
    }
    val forbidden = Set(
      "score",
      "outcome",
      "prediction",
      "suggestedLabel",
      "decisionPath",
      "adjudication",
      "label"
    )
    assert(keys(json).intersect(forbidden).isEmpty)
    assert(first.split.residualRisks.nonEmpty)
  }

  test(
    "candidate duplicates and altered source or candidate bindings cannot create a review queue"
  ) {
    val population = isolated(40)
    val sampling = ReviewSampling.standard.copy(
      development = 2,
      heldOut = 4,
      developmentReserve = 0,
      heldOutReserve = 0
    )
    val duplicate = population.candidates.copy(pairs =
      population.candidates.pairs :+ population.candidates.pairs.head
    )
    val dupPopulation = population.copy(candidates = duplicate)
    assert(ReviewQueue.build(population.input, duplicate, sampling, binding(dupPopulation)).isLeft)
    assert(
      ReviewQueue
        .build(
          population.input,
          population.candidates,
          sampling,
          binding(population).copy(inputEvidenceHash = "0" * 64)
        )
        .isLeft
    )
    assert(
      ReviewQueue
        .build(
          population.input,
          population.candidates,
          sampling,
          binding(population).copy(candidatePopulationHash = "0" * 64)
        )
        .isLeft
    )
  }

  test("infeasible population reports a failure instead of silently reducing the human target") {
    val population = isolated(20)
    val result = ReviewQueue.build(
      population.input,
      population.candidates,
      ReviewSampling.standard,
      binding(population)
    )
    assert(result.isLeft)
  }

  test("queue parser rejects unknown keys and any evidence or queue identity mutation") {
    val result = artifacts(
      40,
      ReviewSampling.standard
        .copy(development = 2, heldOut = 4, developmentReserve = 0, heldOutReserve = 0)
    )
    val original = ujson.read(write(result.queue))
    assert(ReviewQueue.parseQueue(original.render()).isRight)
    val unknown = mutate(original)(_("suggestedLabel") = "same")
    val wrongQueue = mutate(original)(_("queueHash") = "0" * 64)
    val wrongEvidence = mutate(original)(_("tasks")(0)("evidenceHash") = "0" * 64)
    val nestedUnknown = mutate(original)(_("tasks")(0)("score") = 1.0)
    Vector(unknown, wrongQueue, wrongEvidence, nestedUnknown).foreach(v =>
      assert(ReviewQueue.parseQueue(v.render()).isLeft)
    )
  }
  test(
    "negative candidate edges never make one leakage group while shared publications and IDs stay together"
  ) {
    import IndependentResolutionFixtures.*
    val original = isolated(40)
    val first = original.input.works.head
    val third = original.input.works(2)
    val alias = work(
      "conf/independent/review/known-doi-copy",
      title = "Independent copy title",
      doi = first.doi
    )
    val in = ResolutionInput
      .create(original.input.works :+ alias, Vector.empty, Vector.empty, Vector.empty)
      .toOption
      .get
    def direct(a: ResolutionEndpoint, b: ResolutionEndpoint): DerivedPair = {
      val p = pair(a, b)
      DerivedPair(p, Vector.empty, (in.refs(a) ++ in.refs(b)).distinct.sorted)
    }
    val population = Population(
      in,
      original.candidates.copy(pairs =
        original.candidates.pairs ++ Vector(
          direct(endpoint(first), endpoint(third)),
          direct(endpoint(alias), endpoint(third)),
          direct(mention(first), mention(third))
        )
      )
    )
    val sampling = ReviewSampling.standard.copy(
      development = 2,
      heldOut = 4,
      developmentReserve = 0,
      heldOutReserve = 0
    )
    val built = ReviewQueue.build(in, population.candidates, sampling, binding(population))
    assert(built.isRight, built.toString)
    val result = built.toOption.get
    // Eighty independent publications remain eighty groups. Negative comparison edges must not union them.
    // The alias DOI and each author mention belong to the existing publication/identity component.
    assert(result.split.groups.size == 80)
    val groups = ujson.read(write(result.split))("groups").arr.toVector
    def groupFor(e: ResolutionEndpoint): String = groups
      .find(_("endpointIds").arr.exists(_.str == ResolutionIds.endpointId(e)))
      .get("groupId")
      .str
    assert(groupFor(endpoint(first)) != groupFor(endpoint(third)))
    assert(groupFor(endpoint(first)) == groupFor(endpoint(alias)))
    assert(groupFor(endpoint(first)) == groupFor(mention(first)))
    val partitions = result.queue.tasks.flatMap { t =>
      Vector(t.pair.left, t.pair.right).map(e => ResolutionIds.endpointId(e) -> t.partition)
    }
    assert(partitions.groupMap(_._1)(_._2).values.forall(_.distinct.size == 1))
  }

  test(
    "development retains both entities when disjoint work pairs have lower degree than researcher groups"
  ) {
    import IndependentResolutionFixtures.*
    val base = isolated(100)
    val extra = (0 until 12).toVector.map { i =>
      work(
        s"conf/independent/review/researcher-rich-$i",
        title = s"Researcher-rich synthetic title $i",
        names = Vector("Casey Independent")
      )
    }
    val input = ResolutionInput
      .create(base.input.works ++ extra, Vector.empty, Vector.empty, Vector.empty)
      .toOption
      .get
    val researcherPairs = extra.indices.toVector.flatMap { i =>
      ((i + 1) until extra.size).map { j =>
        val p = pair(mention(extra(i)), mention(extra(j)))
        DerivedPair(p, Vector.empty, (input.refs(p.left) ++ input.refs(p.right)).distinct.sorted)
      }
    }
    val population =
      Population(input, base.candidates.copy(pairs = base.candidates.pairs ++ researcherPairs))
    val sampling = ReviewSampling.standard.copy(
      development = 20,
      heldOut = 40,
      developmentReserve = 0,
      heldOutReserve = 0
    )
    val built = ReviewQueue.build(input, population.candidates, sampling, binding(population))
    assert(built.isRight, built.toString)
    val tasks = built.toOption.get.queue.tasks
    Vector("development", "held-out").foreach { partition =>
      val kinds = tasks
        .filter(t => t.partition == partition && t.role == "initial")
        .map(_.pair.entityType)
        .toSet
      assert(
        kinds == Set(ResolutionEntityType.Work, ResolutionEntityType.Researcher),
        s"$partition lost feasible entity coverage: $kinds"
      )
    }
  }

}
